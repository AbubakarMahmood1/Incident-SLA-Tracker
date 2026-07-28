import unicodedata
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain import IncidentPriority
from app.schemas import IncidentAssign, IncidentCreate, UserSummary


def test_incident_text_is_trimmed_and_normalized() -> None:
    decomposed = "Cafe\u0301"
    model = IncidentCreate(
        title=f"  {decomposed} outage  ",
        description="  service is unavailable  ",
        priority=IncidentPriority.HIGH,
    )
    assert model.title == unicodedata.normalize("NFC", f"{decomposed} outage")
    assert model.description == "service is unavailable"


@pytest.mark.parametrize("value", ["", "   ", "hello\nworld\x00"])
def test_incident_title_rejects_blank_or_control_content(value: str) -> None:
    with pytest.raises(ValidationError):
        IncidentCreate(
            title=value,
            description="valid",
            priority=IncidentPriority.LOW,
        )


def test_description_is_bounded() -> None:
    with pytest.raises(ValidationError):
        IncidentCreate(
            title="valid",
            description="x" * 10001,
            priority=IncidentPriority.LOW,
        )


def test_assignment_requires_uuid() -> None:
    assert IncidentAssign(assignee_id=uuid4()).assignee_id
    with pytest.raises(ValidationError):
        IncidentAssign(assignee_id="not-a-uuid")


def test_command_schemas_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        IncidentCreate.model_validate(
            {
                "title": "valid",
                "description": "valid",
                "priority": "low",
                "status": "resolved",
            }
        )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        IncidentAssign.model_validate({"assignee_id": str(uuid4()), "unexpected": True})


def test_public_user_summary_omits_email_and_administrator_status() -> None:
    summary = UserSummary.model_validate(
        SimpleNamespace(
            id=uuid4(),
            username="operator",
            display_name="Operator",
            email="private@example.com",
            is_admin=True,
        )
    )
    assert set(summary.model_dump()) == {"id", "username", "display_name"}
