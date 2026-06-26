from types import SimpleNamespace

from skills.data_and_forms_skill.scripts.get_form_responses_tool import GetFormResponsesTool


def test_get_form_responses_tool_formats_list_answers():
    tool = GetFormResponsesTool(account_id="00000000-0000-0000-0000-000000000001")
    response = SimpleNamespace(
        id="response-1",
        submitted_at=SimpleNamespace(strftime=lambda fmt: "2026-06-03 18:28"),
        answers=[
            {"field_id": "nombre", "value": "Ana"},
            {"field_id": "edad", "value": 31},
        ],
    )

    formatted = tool._format_single_response(response)

    assert "• nombre: Ana" in formatted
    assert "• edad: 31" in formatted


def test_get_form_responses_tool_formats_dict_answers():
    tool = GetFormResponsesTool(account_id="00000000-0000-0000-0000-000000000001")
    response = SimpleNamespace(
        id="response-2",
        submitted_at=SimpleNamespace(strftime=lambda fmt: "2026-06-03 18:28"),
        answers={"nombre": "Ana", "edad": 31},
    )

    formatted = tool._format_single_response(response)

    assert "• nombre: Ana" in formatted
    assert "• edad: 31" in formatted
