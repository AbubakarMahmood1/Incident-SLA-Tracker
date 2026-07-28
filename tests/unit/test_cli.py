import io
import sys

import pytest
from pydantic import ValidationError

from app.cli import UserProvisionInput, read_password

BASE = {
    "username": "  Alice.Operator  ",
    "email": "ALICE@example.com",
    "display_name": "  Alice Operator  ",
    "password": "correct horse battery staple",
}


def test_user_provision_input_normalizes_owner_controlled_identity() -> None:
    command = UserProvisionInput(**BASE)
    assert command.username == "alice.operator"
    assert command.email == "alice@example.com"
    assert command.display_name == "Alice Operator"
    assert not command.admin


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("username", "a" * 101),
        ("username", "operator\nadmin"),
        ("email", "not-an-email"),
        ("display_name", "   "),
        ("display_name", "Operator\u0000Name"),
        ("password", "too-short"),
    ],
)
def test_user_provision_input_rejects_invalid_values(field: str, value: str) -> None:
    payload = {**BASE, field: value}
    with pytest.raises(ValidationError):
        UserProvisionInput(**payload)


def test_password_can_be_read_from_stdin_without_an_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("correct horse battery staple\n"))
    assert read_password(from_stdin=True) == "correct horse battery staple"


def test_password_prompt_requires_matching_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(["correct horse battery staple", "different password value"])
    monkeypatch.setattr("getpass.getpass", lambda _: next(values))
    with pytest.raises(ValueError, match="confirmation"):
        read_password(from_stdin=False)
