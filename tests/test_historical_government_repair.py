from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "work_packages/M1_source_access/07_historical_government_acquisition/"
    "historical_government_acquisition.py"
)
SPEC = importlib.util.spec_from_file_location("historical_government_acquisition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _detail(items: list[dict[str, object]], navigator: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "Overview": {
            "Id": 40,
            "ExtId": "example-answer",
            "Title": "Example",
            "Date": "2007-03-19T00:00:00",
            "Location": "Written Answers",
            "VolumeNo": 458,
        },
        "Navigator": navigator
        or [
            {"Id": 10, "ParentId": None, "Title": "Written Answers", "HRSTag": None},
            {"Id": 30, "ParentId": 10, "Title": "Trade and Industry", "HRSTag": "hs_6bDepartment"},
            {"Id": 40, "ParentId": 30, "ExternalId": "example-answer", "Title": "Example", "HRSTag": "hs_8Question"},
        ],
        "Items": items,
    }


def test_nested_department_uses_nearest_parent() -> None:
    detail = _detail(
        [],
        [
            {"Id": 10, "ParentId": None, "Title": "Written Answers", "HRSTag": None},
            {"Id": 20, "ParentId": 10, "Title": "International Development", "HRSTag": "hs_6bDepartment"},
            {"Id": 30, "ParentId": 20, "Title": "Environment, Food and Rural Affairs", "HRSTag": "hs_6bDepartment"},
            {"Id": 40, "ParentId": 30, "ExternalId": "example-answer", "Title": "Example", "HRSTag": "hs_8Question"},
        ],
    )
    assert MODULE._hansard_department(detail) == "ENVIRONMENT, FOOD AND RURAL AFFAIRS"


def test_structured_numbered_question_and_continuation_stay_context() -> None:
    detail = _detail(
        [
            {
                "ItemType": "Contribution",
                "ExternalId": "q1",
                "ItemId": 1,
                "AttributedTo": "Tony Baldry",
                "HRSTag": "Question",
                "Value": "<Question><QuestionText>(1) To ask the Secretary of State what estimate he has made;</QuestionText></Question>",
            },
            {
                "ItemType": "Contribution",
                "ItemId": 2,
                "AttributedTo": None,
                "HRSTag": "ERR_Question",
                "Value": "(2) what further estimate he has made.",
            },
            {
                "ItemType": "Contribution",
                "ExternalId": "a1",
                "ItemId": 3,
                "AttributedTo": "Jim Fitzpatrick",
                "HRSTag": "hs_Para",
                "Value": "The Department has published its estimate.",
            },
        ]
    )
    record = MODULE._hansard_detail_record(detail, "TRADE AND INDUSTRY")
    assert record is not None
    assert [value["paragraph_id"] for value in record["questions"]] == ["q1", "2"]
    assert record["questions"][1]["speaker"] == "Tony Baldry"
    assert [value["paragraph_id"] for value in record["responses"]] == ["a1"]


def test_embedded_question_speaker_prefix_is_recovered() -> None:
    detail = _detail(
        [
            {
                "ItemType": "Contribution",
                "ExternalId": "q1",
                "ItemId": 1,
                "AttributedTo": "",
                "HRSTag": "Question",
                "Value": "<Question><strong>Adam Afriyie:</strong> To ask the Secretary of State what steps he will take. <QuestionText></QuestionText></Question>",
            },
            {
                "ItemType": "Contribution",
                "ExternalId": "a1",
                "ItemId": 2,
                "AttributedTo": "Barry Gardiner",
                "HRSTag": "hs_Para",
                "Value": "The Department will take the stated steps.",
            },
        ]
    )
    record = MODULE._hansard_detail_record(detail, "ENVIRONMENT, FOOD AND RURAL AFFAIRS")
    assert record is not None
    assert record["questions"][0]["speaker"] == "Adam Afriyie"
    assert record["questions"][0]["text"].startswith("To ask")
    assert record["government_respondent"] == "Barry Gardiner"


def test_mixed_question_wrapper_is_not_assigned_as_ministerial_response() -> None:
    detail = _detail(
        [
            {
                "ItemType": "Contribution",
                "ExternalId": "q1",
                "ItemId": 1,
                "AttributedTo": "Mr. Davidson",
                "HRSTag": "Question",
                "Value": (
                    "<Question><QuestionText>To ask the Secretary of State when meetings took place.</QuestionText>"
                    "Pursuant to the earlier answer, the recorded date was incorrect.</Question>"
                ),
            }
        ]
    )
    assert MODULE._hansard_detail_record(detail, "ENVIRONMENT, FOOD AND RURAL AFFAIRS") is None
