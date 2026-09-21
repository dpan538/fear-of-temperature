from __future__ import annotations

import io
import json
import urllib.error
from datetime import date
from email.message import Message
from pathlib import Path

import pytest

from fear_temperature.government_collection import (
    HttpClient,
    HttpResult,
    _validate_download,
    build_content_objects,
    build_year_partitions,
    project_content_metadata,
)


class _FakeResponse:
    def __init__(self, *, url: str, body: bytes, mime_type: str = "application/json") -> None:
        self.status = 200
        self._url = url
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = mime_type

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url


def _http_settings(*, retries: int = 1) -> dict[str, object]:
    return {
        "user_agent": "test-agent",
        "timeout_seconds": 1,
        "retries": retries,
        "backoff_seconds": 0,
        "minimum_interval_seconds": 0,
    }


def test_year_partitions_are_non_overlapping_and_preserve_boundaries() -> None:
    partitions = build_year_partitions(date(1988, 3, 4), date(1990, 9, 21))

    assert partitions == [
        ("year_1988", date(1988, 3, 4), date(1988, 12, 31)),
        ("year_1989", date(1989, 1, 1), date(1989, 12, 31)),
        ("year_1990", date(1990, 1, 1), date(1990, 9, 21)),
    ]
    assert all(
        left[2] < right[1] for left, right in zip(partitions, partitions[1:], strict=False)
    )


def test_metadata_projection_retains_attachment_identity_but_omits_body() -> None:
    payload = {
        "content_id": "doc-1",
        "base_path": "/government/publications/example",
        "title": "Example",
        "document_type": "policy_paper",
        "schema_name": "publication",
        "first_published_at": "2001-01-01T00:00:00Z",
        "public_updated_at": "2001-02-01T00:00:00Z",
        "links": {
            "organisations": [
                {
                    "content_id": "org-1",
                    "title": "Department",
                    "base_path": "/government/organisations/department",
                }
            ]
        },
        "details": {
            "body": "<p>Substantive text that must not be persisted.</p>",
            "documents": ["<section>Rendered attachment markup</section>"],
            "attachments": [
                {
                    "id": "att-1",
                    "url": "https://assets.example/a.pdf",
                    "title": "Attachment",
                    "content_type": "application/pdf",
                    "file_size": 123,
                }
            ],
            "emphasised_organisations": ["org-1"],
        },
    }

    projected = project_content_metadata(payload)

    assert "body" not in projected
    assert "documents" not in projected
    assert "Substantive text" not in json.dumps(projected)
    assert projected["attachments"][0]["id"] == "att-1"
    assert projected["emphasised_organisation_ids"] == ["org-1"]
    assert projected["projection_policy"]["body_persisted"] is False


def test_shared_attachment_is_one_object_with_two_parent_relations(tmp_path: Path) -> None:
    projection_path_1 = tmp_path / "one.json"
    projection_path_2 = tmp_path / "two.json"
    shared_attachment = {
        "id": "attachment-1",
        "url": "https://assets.example/shared.pdf",
        "content_type": "application/pdf",
        "file_size": 456,
        "number_of_pages": 8,
    }
    for path in (projection_path_1, projection_path_2):
        path.write_text(
            json.dumps({"metadata_projection": {"attachments": [shared_attachment]}}),
            encoding="utf-8",
        )
    manifest = [
        {
            "external_id": "doc-1",
            "canonical_url": "https://www.gov.uk/doc-1",
            "metadata_path": str(projection_path_1),
        },
        {
            "external_id": "doc-2",
            "canonical_url": "https://www.gov.uk/doc-2",
            "metadata_path": str(projection_path_2),
        },
    ]

    objects = build_content_objects({"content_fetch": {}}, manifest)
    attachments = [item for item in objects if item["object_kind"] == "attachment"]

    assert len(attachments) == 1
    assert set(attachments[0]["parent_external_ids"]) == {"doc-1", "doc-2"}
    assert len(attachments[0]["relations"]) == 2


def test_http_client_honours_retry_after_and_records_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://example.test/start"
    headers = Message()
    headers["Content-Type"] = "application/json"
    headers["Retry-After"] = "0"
    responses: list[object] = [
        urllib.error.HTTPError(url, 429, "Too Many Requests", headers, io.BytesIO(b"busy")),
        _FakeResponse(url="https://example.test/final", body=b"{}"),
    ]
    sleeps: list[float] = []

    def next_response(*_args: object, **_kwargs: object) -> object:
        response = responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    monkeypatch.setattr(
        "fear_temperature.government_collection.urllib.request.urlopen", next_response
    )
    monkeypatch.setattr("fear_temperature.government_collection.time.sleep", sleeps.append)

    result = HttpClient(_http_settings()).get(url)

    assert result.status_code == 200
    assert result.attempts == 2
    assert result.final_url == "https://example.test/final"
    assert sleeps == [0.0]


@pytest.mark.parametrize("status", [403, 404])
def test_http_client_does_not_retry_terminal_http_statuses(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    url = "https://example.test/item"
    headers = Message()
    headers["Content-Type"] = "text/html"
    error = urllib.error.HTTPError(url, status, "terminal", headers, io.BytesIO(b"error"))
    calls = 0

    def raise_error(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise error

    monkeypatch.setattr(
        "fear_temperature.government_collection.urllib.request.urlopen", raise_error
    )

    result = HttpClient(_http_settings(retries=3)).get(url)

    assert result.status_code == status
    assert result.attempts == 1
    assert calls == 1


def test_download_validation_rejects_error_shells_and_fake_pdfs() -> None:
    html = HttpResult(
        request_url="https://example.test",
        final_url="https://example.test",
        retrieved_at="2026-09-21T00:00:00Z",
        status_code=200,
        mime_type="text/html",
        body=b"<html><main>Access denied</main></html>",
        headers={},
        attempts=1,
    )
    fake_pdf = HttpResult(**{**html.__dict__, "mime_type": "application/pdf", "body": b"HTML"})

    assert _validate_download(html, "text/html") == "HTML resembles an access-denied page"
    assert _validate_download(fake_pdf, "application/pdf") == (
        "declared PDF did not have a PDF file signature"
    )
