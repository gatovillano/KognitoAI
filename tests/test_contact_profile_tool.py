import pytest
from pydantic import ValidationError

from skills.profile_and_tasks_skill.scripts.contact_profile_tool import ContactProfileToolInput


def test_contact_profile_tool_coerces_numeric_phone_to_string():
    payload = ContactProfileToolInput(action="create_profile", name="Ana", phone=56912345678)

    assert payload.phone == "56912345678"


def test_contact_profile_tool_trims_phone_string():
    payload = ContactProfileToolInput(action="update_profile", name="Ana", phone="  +56 9 1234 5678  ")

    assert payload.phone == "+56 9 1234 5678"


def test_contact_profile_tool_rejects_non_scalar_phone():
    with pytest.raises(ValidationError):
        ContactProfileToolInput(action="create_profile", name="Ana", phone={"number": "56912345678"})
