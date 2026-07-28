import smtplib
import socketserver
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from app.config import Settings
from app.services.outbox_service import OutboxEnvelope, SMTPTransport


@dataclass
class _SMTPState:
    commands: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


class _SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        state = self.server.state
        self.wfile.write(b"220 localhost ESMTP ready\r\n")
        message_lines: list[str] = []
        receiving_data = False
        while line := self.rfile.readline():
            value = line.decode("utf-8", errors="replace").rstrip("\r\n")
            if receiving_data:
                if value == ".":
                    state.messages.append("\n".join(message_lines))
                    message_lines.clear()
                    receiving_data = False
                    self.wfile.write(b"250 2.0.0 accepted\r\n")
                else:
                    message_lines.append(value)
                continue

            state.commands.append(value)
            command = value.split(" ", 1)[0].upper()
            if command in {"EHLO", "HELO"}:
                self.wfile.write(b"250-localhost\r\n250 STARTTLS\r\n")
            elif command == "STARTTLS":
                self.wfile.write(b"454 4.7.0 TLS unavailable\r\n")
            elif command in {"MAIL", "RCPT"}:
                self.wfile.write(b"250 2.1.0 accepted\r\n")
            elif command == "DATA":
                receiving_data = True
                self.wfile.write(b"354 end with <CRLF>.<CRLF>\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 2.0.0 closing\r\n")
                return
            else:
                self.wfile.write(b"250 2.0.0 accepted\r\n")


class _SMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, state: _SMTPState) -> None:
        super().__init__(("127.0.0.1", 0), _SMTPHandler)
        self.state = state


@contextmanager
def smtp_server() -> Iterator[tuple[_SMTPState, int]]:
    state = _SMTPState()
    server = _SMTPServer(state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def settings(port: int, *, starttls: bool) -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="x" * 40,
        outbox_transport="smtp",
        smtp_host="127.0.0.1",
        smtp_port=port,
        smtp_starttls=starttls,
        smtp_from="ledger@example.com",
    )


def envelope() -> OutboxEnvelope:
    return OutboxEnvelope(
        id=uuid4(),
        deduplication_key="incident:abc:sla:response:breach",
        topic="sla.breached",
        recipient="recipient@example.com",
        payload={
            "incident_id": "abc",
            "title": "Controlled SMTP delivery",
            "objective": "response",
        },
        attempt=1,
    )


@pytest.mark.asyncio
async def test_smtp_transport_submits_message_to_controlled_server() -> None:
    with smtp_server() as (state, port):
        await SMTPTransport(settings(port, starttls=False)).send(envelope())

    assert any(command.upper().startswith("MAIL FROM:") for command in state.commands)
    assert any(command.upper().startswith("RCPT TO:") for command in state.commands)
    assert len(state.messages) == 1
    assert "X-Idempotency-Key: incident:abc:sla:response:breach" in state.messages[0]
    assert "Controlled SMTP delivery" in state.messages[0]


@pytest.mark.asyncio
async def test_smtp_transport_does_not_fall_back_to_plaintext_when_starttls_fails() -> None:
    with (
        smtp_server() as (state, port),
        pytest.raises(smtplib.SMTPResponseException) as error,
    ):
        await SMTPTransport(settings(port, starttls=True)).send(envelope())

    assert error.value.smtp_code == 454
    assert any(command.upper() == "STARTTLS" for command in state.commands)
    assert not any(command.upper().startswith("MAIL FROM:") for command in state.commands)
    assert not state.messages
