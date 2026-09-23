# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import email.utils
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import yaml

from .cleaning import stable_id
from .config import PROJECT_ROOT
from .database_pilot import (
    EXPORT_QUERIES as PILOT_EXPORT_QUERIES,
)
from .database_pilot import (
    SCHEMA_SQL as PILOT_SCHEMA_SQL,
)
from .database_pilot import (
    ingest_pilot_bundle,
    load_pilot_bundle,
)

ENUMERATION_COLUMNS = [
    "source_id",
    "external_id",
    "raw_url",
    "canonical_url",
    "title",
    "document_type",
    "search_document_type",
    "verified_document_type",
    "organisation_ids",
    "organisation_names",
    "emphasised_organisation_ids",
    "first_published_at",
    "updated_at",
    "query_partition_id",
    "batch_id",
    "retrieved_at",
    "record_status",
    "metadata_path",
    "metadata_sha256",
    "attachment_count",
    "withdrawn_status",
]

FETCH_COLUMNS = [
    "batch_id",
    "content_object_id",
    "object_kind",
    "external_content_id",
    "parent_external_ids",
    "request_url",
    "final_url",
    "retrieved_at",
    "status_code",
    "mime_type",
    "declared_mime_type",
    "declared_file_size",
    "declared_page_count",
    "content_sha256",
    "raw_path",
    "fetch_version",
    "parse_version",
    "public_access_status",
    "collection_status",
    "research_processing_status",
    "redistribution_status",
    "ethics_status",
    "failure_reason",
]

FETCH_FAILURE_STATUSES = {"failed", "not_found", "access_denied", "rate_limited"}

MIGRATION_SQL = """
CREATE TABLE IF NOT EXISTS query_partitions (
    query_partition_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    query_url VARCHAR NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    page_count INTEGER NOT NULL,
    initial_total INTEGER NOT NULL,
    returned_count INTEGER NOT NULL,
    unique_count INTEGER NOT NULL,
    recheck_total INTEGER,
    status VARCHAR NOT NULL,
    status_reason VARCHAR NOT NULL,
    raw_response_paths_json VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS enumeration_records (
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    query_partition_id VARCHAR NOT NULL REFERENCES query_partitions(query_partition_id),
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    raw_record_id VARCHAR NOT NULL REFERENCES raw_records(raw_record_id),
    retrieved_at TIMESTAMPTZ NOT NULL,
    record_status VARCHAR NOT NULL,
    metadata_path VARCHAR NOT NULL,
    metadata_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (batch_id, document_id)
);

CREATE TABLE IF NOT EXISTS content_objects (
    content_object_id VARCHAR PRIMARY KEY,
    object_kind VARCHAR NOT NULL CHECK (object_kind IN ('webpage', 'attachment')),
    external_content_id VARCHAR,
    canonical_url VARCHAR NOT NULL,
    declared_mime_type VARCHAR,
    declared_file_size BIGINT,
    declared_page_count INTEGER,
    public_access_status VARCHAR NOT NULL,
    rights_status VARCHAR NOT NULL,
    ethics_status VARCHAR NOT NULL,
    UNIQUE (object_kind, canonical_url)
);

CREATE TABLE IF NOT EXISTS document_content_objects (
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    content_object_id VARCHAR NOT NULL REFERENCES content_objects(content_object_id),
    relationship_type VARCHAR NOT NULL CHECK (relationship_type IN ('landing_page', 'attachment')),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    PRIMARY KEY (document_id, content_object_id)
);

CREATE TABLE IF NOT EXISTS content_fetches (
    fetch_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    content_object_id VARCHAR NOT NULL REFERENCES content_objects(content_object_id),
    request_url VARCHAR NOT NULL,
    final_url VARCHAR,
    retrieved_at TIMESTAMPTZ,
    status_code INTEGER,
    mime_type VARCHAR,
    content_sha256 VARCHAR,
    raw_path VARCHAR,
    fetch_version VARCHAR NOT NULL,
    collection_status VARCHAR NOT NULL,
    research_processing_status VARCHAR NOT NULL,
    redistribution_status VARCHAR NOT NULL,
    failure_reason VARCHAR NOT NULL,
    UNIQUE (batch_id, content_object_id)
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    extraction_run_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    extractor_version VARCHAR NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    input_content_count INTEGER NOT NULL,
    output_segment_count INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    status_reason VARCHAR NOT NULL
);
"""

CORE_STORAGE_SQL = """
ALTER TABLE content_objects ADD COLUMN title VARCHAR DEFAULT '';
ALTER TABLE content_objects ADD COLUMN acquisition_status VARCHAR DEFAULT 'not_attempted';
ALTER TABLE content_objects ADD COLUMN identity_metadata_json VARCHAR DEFAULT '{}';

CREATE TABLE content_versions (
    content_version_id VARCHAR PRIMARY KEY,
    content_object_id VARCHAR NOT NULL REFERENCES content_objects(content_object_id),
    content_sha256 VARCHAR NOT NULL,
    resolved_url VARCHAR NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    status_code INTEGER NOT NULL CHECK (status_code >= 200 AND status_code < 300),
    mime_type VARCHAR NOT NULL,
    byte_size BIGINT,
    raw_path VARCHAR NOT NULL,
    storage_sha256 VARCHAR NOT NULL,
    first_fetch_id VARCHAR NOT NULL,
    version_status VARCHAR NOT NULL CHECK (version_status IN ('saved', 'verified')),
    UNIQUE (content_object_id, content_sha256)
);

CREATE TABLE core_content_fetches (
    fetch_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    content_object_id VARCHAR NOT NULL REFERENCES content_objects(content_object_id),
    content_version_id VARCHAR REFERENCES content_versions(content_version_id),
    request_url VARCHAR NOT NULL,
    final_url VARCHAR,
    retrieved_at TIMESTAMPTZ,
    status_code INTEGER,
    mime_type VARCHAR,
    content_sha256 VARCHAR,
    raw_path VARCHAR,
    fetch_version VARCHAR NOT NULL,
    collection_status VARCHAR NOT NULL,
    research_processing_status VARCHAR NOT NULL,
    redistribution_status VARCHAR NOT NULL,
    failure_reason VARCHAR NOT NULL,
    UNIQUE (batch_id, content_object_id)
);

CREATE TABLE schema_migrations (
    migration_id VARCHAR PRIMARY KEY,
    source_schema_version VARCHAR NOT NULL,
    target_schema_version VARCHAR NOT NULL,
    source_database_path VARCHAR NOT NULL,
    source_database_sha256 VARCHAR NOT NULL,
    decision_record_path VARCHAR NOT NULL,
    migrated_at TIMESTAMPTZ NOT NULL,
    status VARCHAR NOT NULL
);
"""

CORE_TEXT_STORAGE_SQL = """
CREATE TABLE text_segments (
    segment_id VARCHAR PRIMARY KEY,
    content_version_id VARCHAR NOT NULL REFERENCES content_versions(content_version_id),
    extraction_run_id VARCHAR NOT NULL REFERENCES extraction_runs(extraction_run_id),
    parent_segment_id VARCHAR REFERENCES text_segments(segment_id),
    representation_kind VARCHAR NOT NULL CHECK (
        representation_kind IN ('source_extracted', 'cleaned', 'derived')
    ),
    segment_kind VARCHAR NOT NULL CHECK (
        segment_kind IN ('paragraph', 'post_body', 'comment_body', 'quoted_block', 'unknown')
    ),
    segment_order INTEGER NOT NULL CHECK (segment_order >= 0),
    heading VARCHAR,
    segment_text VARCHAR NOT NULL,
    locator VARCHAR NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    text_sha256 VARCHAR NOT NULL,
    permission_status VARCHAR NOT NULL,
    research_sample BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (content_version_id, extraction_run_id, representation_kind, segment_order)
);

CREATE TABLE voice_attributions (
    attribution_id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    segment_id VARCHAR REFERENCES text_segments(segment_id),
    actor_name VARCHAR,
    attribution_role VARCHAR NOT NULL CHECK (
        attribution_role IN ('quoted_speaker', 'emotion_holder', 'reported_actor', 'unknown')
    ),
    evidence_locator VARCHAR,
    status VARCHAR NOT NULL CHECK (status IN ('confirmed', 'pending', 'unknown'))
);
"""

ACQUISITION_AUDIT_SQL = """
CREATE TABLE IF NOT EXISTS acquisition_authorizations (
    authorization_id VARCHAR PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL,
    actor VARCHAR NOT NULL,
    authorization_text VARCHAR NOT NULL,
    supervisor_statement_basis VARCHAR NOT NULL,
    supervisor_statement_text VARCHAR NOT NULL,
    project_authorization_status VARCHAR NOT NULL,
    institutional_ethics_status VARCHAR NOT NULL,
    allowed_use VARCHAR NOT NULL,
    redistribution_status VARCHAR NOT NULL,
    scope_json VARCHAR NOT NULL,
    source_thread_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS acquisition_runs (
    run_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    authorization_id VARCHAR NOT NULL REFERENCES acquisition_authorizations(authorization_id),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    phase VARCHAR NOT NULL,
    script_version VARCHAR NOT NULL,
    command_line VARCHAR NOT NULL,
    input_manifest_path VARCHAR NOT NULL,
    input_manifest_sha256 VARCHAR NOT NULL,
    output_database_path VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    attempted_count INTEGER NOT NULL,
    successful_download_count INTEGER NOT NULL,
    successful_extraction_count INTEGER NOT NULL,
    failure_count INTEGER NOT NULL,
    result_json VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS acquisition_object_statuses (
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    content_object_id VARCHAR NOT NULL REFERENCES content_objects(content_object_id),
    fetch_id VARCHAR NOT NULL REFERENCES content_fetches(fetch_id),
    content_version_id VARCHAR REFERENCES content_versions(content_version_id),
    object_kind VARCHAR NOT NULL,
    declared_mime_type VARCHAR,
    actual_mime_type VARCHAR,
    actual_format VARCHAR,
    attempt_count INTEGER NOT NULL,
    redirected BOOLEAN NOT NULL,
    download_status VARCHAR NOT NULL,
    validation_status VARCHAR NOT NULL,
    extraction_status VARCHAR NOT NULL,
    extraction_reason VARCHAR NOT NULL,
    byte_size BIGINT,
    content_sha256 VARCHAR,
    raw_path VARCHAR,
    segment_count INTEGER NOT NULL,
    checkpoint_path VARCHAR NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (batch_id, content_object_id)
);

CREATE TABLE IF NOT EXISTS acquisition_events (
    event_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES acquisition_runs(run_id),
    content_object_id VARCHAR NOT NULL REFERENCES content_objects(content_object_id),
    event_at TIMESTAMPTZ NOT NULL,
    stage VARCHAR NOT NULL,
    outcome VARCHAR NOT NULL,
    details_json VARCHAR NOT NULL
);
"""

NEW_EXPORT_QUERIES: dict[str, str] = {
    "query_partitions": "SELECT * FROM query_partitions ORDER BY window_start, query_partition_id",
    "enumeration_records": (
        "SELECT * FROM enumeration_records ORDER BY query_partition_id, document_id"
    ),
    "content_objects": "SELECT * FROM content_objects ORDER BY object_kind, canonical_url",
    "document_content_objects": (
        "SELECT * FROM document_content_objects ORDER BY document_id, relationship_type, ordinal"
    ),
    "content_fetches": (
        "SELECT * FROM content_fetches ORDER BY content_object_id, fetch_id"
    ),
    "extraction_runs": "SELECT * FROM extraction_runs ORDER BY extraction_run_id",
}

CORE_EXPORT_QUERIES: dict[str, str] = {
    "content_objects": "SELECT * FROM content_objects ORDER BY object_kind, canonical_url",
    "content_versions": (
        "SELECT * FROM content_versions ORDER BY content_object_id, retrieved_at, content_version_id"
    ),
    "content_fetches": "SELECT * FROM content_fetches ORDER BY content_object_id, fetch_id",
    "text_segments": (
        "SELECT * FROM text_segments ORDER BY content_version_id, extraction_run_id, "
        "representation_kind, segment_order, segment_id"
    ),
    "voice_attributions": "SELECT * FROM voice_attributions ORDER BY attribution_id",
    "schema_migrations": "SELECT * FROM schema_migrations ORDER BY migration_id",
    "institution_counting": (
        "SELECT o.organisation_id, o.organisation_name, COUNT(*) AS linked_document_count, "
        "SUM(CAST(r.full_count_weight AS DECIMAL(38, 18))) AS full_count, "
        "SUM(CAST(r.fractional_count_weight AS DECIMAL(38, 18))) AS fractional_count "
        "FROM document_organisations r JOIN organisations o USING (organisation_id) "
        "GROUP BY o.organisation_id, o.organisation_name "
        "ORDER BY o.organisation_name, o.organisation_id"
    ),
}


@dataclass(frozen=True)
class HttpResult:
    request_url: str
    final_url: str
    retrieved_at: str
    status_code: int
    mime_type: str
    body: bytes
    headers: dict[str, str]
    attempts: int
    error: str = ""


class HttpClient:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.user_agent = str(settings["user_agent"])
        self.timeout = float(settings["timeout_seconds"])
        self.retries = int(settings["retries"])
        self.backoff = float(settings["backoff_seconds"])
        self.minimum_interval = float(settings["minimum_interval_seconds"])
        self._lock = threading.Lock()
        self._last_request = 0.0

    def _pace(self) -> None:
        with self._lock:
            wait = self.minimum_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    @staticmethod
    def _retry_after(headers: Any) -> float | None:
        value = headers.get("Retry-After") if headers else None
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(value)
            if parsed is None:
                return None
            return max(0.0, (parsed - datetime.now(UTC)).total_seconds())

    def get(self, url: str) -> HttpResult:
        last_error = ""
        for attempt in range(1, self.retries + 2):
            self._pace()
            request = urllib.request.Request(
                url,
                headers={"User-Agent": self.user_agent, "Accept": "application/json,*/*;q=0.8"},
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read()
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    return HttpResult(
                        request_url=url,
                        final_url=response.geturl(),
                        retrieved_at=utc_now(),
                        status_code=int(response.status),
                        mime_type=response.headers.get_content_type(),
                        body=body,
                        headers=headers,
                        attempts=attempt,
                    )
            except urllib.error.HTTPError as exc:
                body = exc.read()
                headers = {key.lower(): value for key, value in exc.headers.items()}
                last_error = f"HTTP {exc.code}: {exc.reason}"
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt > self.retries:
                    return HttpResult(
                        request_url=url,
                        final_url=exc.geturl(),
                        retrieved_at=utc_now(),
                        status_code=int(exc.code),
                        mime_type=exc.headers.get_content_type(),
                        body=body,
                        headers=headers,
                        attempts=attempt,
                        error=last_error,
                    )
                delay = self._retry_after(exc.headers)
                time.sleep(delay if delay is not None else self.backoff * (2 ** (attempt - 1)))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt > self.retries:
                    return HttpResult(
                        request_url=url,
                        final_url=url,
                        retrieved_at=utc_now(),
                        status_code=0,
                        mime_type="",
                        body=b"",
                        headers={},
                        attempts=attempt,
                        error=last_error,
                    )
                time.sleep(self.backoff * (2 ** (attempt - 1)))
        raise RuntimeError(last_error)

    def get_json(self, url: str) -> tuple[HttpResult, dict[str, Any] | None]:
        result = self.get(url)
        if result.status_code != 200:
            return result, None
        try:
            payload = json.loads(result.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return (
                HttpResult(**{**result.__dict__, "error": f"invalid_json: {exc}"}),
                None,
            )
        if not isinstance(payload, dict):
            return (
                HttpResult(**{**result.__dict__, "error": "JSON response is not an object"}),
                None,
            )
        return result, payload


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = resolve_path(path)
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Expected mapping in {config_path}")
    config["_config_path"] = str(config_path)
    return config


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_csv_atomic(path: Path, columns: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_year_partitions(start: date, end: date) -> list[tuple[str, date, date]]:
    if end < start:
        raise ValueError("end date precedes start date")
    rows: list[tuple[str, date, date]] = []
    for year in range(start.year, end.year + 1):
        partition_start = max(start, date(year, 1, 1))
        partition_end = min(end, date(year, 12, 31))
        rows.append((f"year_{year}", partition_start, partition_end))
    return rows


def search_url(
    config: dict[str, Any], partition_start: date, partition_end: date, *, start: int, count: int
) -> str:
    source = config["source"]
    params = {
        "filter_organisations": source["organisation_slug"],
        "filter_content_store_document_type": source["document_type"],
        f"filter_{source['date_filter_field']}": (
            f"from:{partition_start.isoformat()},to:{partition_end.isoformat()}"
        ),
        "count": str(count),
        "start": str(start),
        "order": "public_timestamp",
    }
    return str(source["search_api"]) + "?" + urllib.parse.urlencode(params)


def project_content_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    raw_details = payload.get("details")
    details: dict[str, Any] = raw_details if isinstance(raw_details, dict) else {}
    raw_links = payload.get("links")
    links: dict[str, Any] = raw_links if isinstance(raw_links, dict) else {}
    organisations: list[dict[str, Any]] = []
    for organisation in links.get("organisations") or []:
        if not isinstance(organisation, dict):
            continue
        organisations.append(
            {
                "content_id": organisation.get("content_id"),
                "title": organisation.get("title"),
                "base_path": organisation.get("base_path"),
                "document_type": organisation.get("document_type"),
                "withdrawn": organisation.get("withdrawn"),
            }
        )
    attachments: list[dict[str, Any]] = []
    for position, attachment in enumerate(details.get("attachments") or []):
        if not isinstance(attachment, dict):
            continue
        attachments.append(
            {
                "ordinal": position,
                "id": attachment.get("id"),
                "title": attachment.get("title"),
                "url": attachment.get("url"),
                "attachment_type": attachment.get("attachment_type"),
                "content_type": attachment.get("content_type"),
                "file_size": attachment.get("file_size"),
                "filename": attachment.get("filename"),
                "number_of_pages": attachment.get("number_of_pages"),
                "accessible": attachment.get("accessible"),
                "isbn": attachment.get("isbn"),
                "unique_reference": attachment.get("unique_reference"),
                "assets": attachment.get("assets") or [],
            }
        )
    keep_top_level = [
        "analytics_identifier",
        "base_path",
        "content_id",
        "description",
        "document_type",
        "first_published_at",
        "locale",
        "phase",
        "public_updated_at",
        "publishing_app",
        "rendering_app",
        "schema_name",
        "title",
        "updated_at",
        "withdrawn_notice",
    ]
    projected = {key: payload.get(key) for key in keep_top_level}
    projected.update(
        {
            "organisations": organisations,
            "primary_publishing_organisations": [
                item.get("content_id")
                for item in links.get("primary_publishing_organisation") or []
                if isinstance(item, dict)
            ],
            "original_primary_publishing_organisations": [
                item.get("content_id")
                for item in links.get("original_primary_publishing_organisation") or []
                if isinstance(item, dict)
            ],
            "emphasised_organisation_ids": details.get("emphasised_organisations") or [],
            "attachments": attachments,
            "change_history": details.get("change_history") or [],
            "first_public_at": details.get("first_public_at"),
            "political": details.get("political"),
            "projection_policy": {
                "version": "govuk_content_metadata_projection_v1",
                "omitted_top_level_fields": sorted(set(payload) - set(keep_top_level) - {"links", "details"}),
                "omitted_detail_fields": sorted(
                    set(details)
                    - {
                        "attachments",
                        "change_history",
                        "emphasised_organisations",
                        "first_public_at",
                        "political",
                    }
                ),
                "body_persisted": False,
            },
        }
    )
    return projected


def _response_wrapper(result: HttpResult, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": {
            "url": result.request_url,
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "status_code": result.status_code,
            "mime_type": result.mime_type,
            "attempts": result.attempts,
        },
        "response": payload,
    }


def _load_checkpoint(path: Path, expected_url: str) -> tuple[dict[str, Any], str] | None:
    if not path.exists():
        return None
    try:
        wrapper = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    request = wrapper.get("request") or {}
    payload = wrapper.get("response")
    if request.get("url") != expected_url or request.get("status_code") != 200:
        return None
    if not isinstance(payload, dict):
        return None
    return wrapper, str(request.get("retrieved_at") or "")


def _fetch_json_checkpoint(
    client: HttpClient, url: str, path: Path, *, resume: bool
) -> tuple[dict[str, Any] | None, HttpResult | None, str]:
    if resume:
        checkpoint = _load_checkpoint(path, url)
        if checkpoint is not None:
            wrapper, retrieved_at = checkpoint
            return wrapper["response"], None, retrieved_at
    result, payload = client.get_json(url)
    if payload is None:
        return None, result, result.retrieved_at
    write_json_atomic(path, _response_wrapper(result, payload))
    return payload, result, result.retrieved_at


def _metadata_checkpoint_path(root: Path, link: str) -> Path:
    return root / "raw/content_metadata" / f"{sha256_bytes(link.encode('utf-8'))[:24]}.json"


def _fetch_metadata_record(
    client: HttpClient,
    config: dict[str, Any],
    root: Path,
    item: dict[str, Any],
    *,
    resume: bool,
) -> dict[str, Any]:
    search_record = item["search_record"]
    link = str(search_record.get("link") or search_record.get("_id") or "")
    content_url = str(config["source"]["content_api_base"]) + link
    checkpoint_path = _metadata_checkpoint_path(root, link)
    if resume and checkpoint_path.exists():
        try:
            wrapper = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            wrapper = None
        if (
            isinstance(wrapper, dict)
            and (wrapper.get("request") or {}).get("url") == content_url
            and (wrapper.get("request") or {}).get("status_code") == 200
            and isinstance(wrapper.get("metadata_projection"), dict)
        ):
            return {
                **item,
                "projection": wrapper["metadata_projection"],
                "metadata_path": relative_path(checkpoint_path),
                "metadata_sha256": sha256_file(checkpoint_path),
                "retrieved_at": (wrapper.get("request") or {}).get("retrieved_at", ""),
                "metadata_status": "metadata_verified_resume",
                "metadata_error": "",
            }
    result, payload = client.get_json(content_url)
    if payload is None:
        return {
            **item,
            "projection": None,
            "metadata_path": "",
            "metadata_sha256": "",
            "retrieved_at": result.retrieved_at,
            "metadata_status": "metadata_failed",
            "metadata_error": result.error or f"HTTP {result.status_code}",
        }
    projection = project_content_metadata(payload)
    wrapper = {
        "request": {
            "url": result.request_url,
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "status_code": result.status_code,
            "mime_type": result.mime_type,
            "attempts": result.attempts,
        },
        "metadata_projection": projection,
    }
    write_json_atomic(checkpoint_path, wrapper)
    return {
        **item,
        "projection": projection,
        "metadata_path": relative_path(checkpoint_path),
        "metadata_sha256": sha256_file(checkpoint_path),
        "retrieved_at": result.retrieved_at,
        "metadata_status": "metadata_verified",
        "metadata_error": "",
    }


def _manifest_row(config: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    projection = item.get("projection")
    search_record = item["search_record"]
    link = str(search_record.get("link") or search_record.get("_id") or "")
    if not isinstance(projection, dict):
        return {
            "source_id": stable_id("src", "policy", config["source"]["name"]),
            "external_id": str(search_record.get("content_id") or ""),
            "raw_url": str(config["source"]["canonical_base"]) + link,
            "canonical_url": str(config["source"]["canonical_base"]) + link,
            "title": str(search_record.get("title") or ""),
            "document_type": str(config["source"]["document_type"]),
            "search_document_type": str(
                search_record.get("format") or config["source"]["document_type"]
            ),
            "verified_document_type": "",
            "organisation_ids": json.dumps([], ensure_ascii=False),
            "organisation_names": json.dumps([], ensure_ascii=False),
            "emphasised_organisation_ids": json.dumps([], ensure_ascii=False),
            "first_published_at": "",
            "updated_at": "",
            "query_partition_id": item["partition_id"],
            "batch_id": config["batch_id"],
            "retrieved_at": item.get("retrieved_at", ""),
            "record_status": item.get("metadata_status", "metadata_failed"),
            "metadata_path": item.get("metadata_path", ""),
            "metadata_sha256": item.get("metadata_sha256", ""),
            "attachment_count": 0,
            "withdrawn_status": "unknown",
        }
    organisations = projection.get("organisations") or []
    first_published = str(projection.get("first_published_at") or "")
    record_status = "metadata_verified"
    try:
        published_date = date.fromisoformat(first_published[:10])
    except ValueError:
        record_status = "invalid_first_published_at"
    else:
        if not (item["partition_start"] <= published_date <= item["partition_end"]):
            record_status = "date_outside_partition"
    if projection.get("document_type") != config["source"]["document_type"]:
        record_status = "metadata_verified_type_drift"
    organisation_ids = [str(org.get("content_id") or "") for org in organisations]
    if config["source"]["organisation_content_id"] not in organisation_ids:
        record_status = "organisation_filter_mismatch"
    base_path = str(projection.get("base_path") or link)
    return {
        "source_id": stable_id("src", "policy", config["source"]["name"]),
        "external_id": str(projection.get("content_id") or ""),
        "raw_url": str(config["source"]["canonical_base"]) + link,
        "canonical_url": str(config["source"]["canonical_base"]) + base_path,
        "title": str(projection.get("title") or search_record.get("title") or ""),
        "document_type": str(projection.get("document_type") or ""),
        "search_document_type": str(
            search_record.get("format") or config["source"]["document_type"]
        ),
        "verified_document_type": str(projection.get("document_type") or ""),
        "organisation_ids": json.dumps(organisation_ids, ensure_ascii=False),
        "organisation_names": json.dumps(
            [str(org.get("title") or "") for org in organisations], ensure_ascii=False
        ),
        "emphasised_organisation_ids": json.dumps(
            projection.get("emphasised_organisation_ids") or [], ensure_ascii=False
        ),
        "first_published_at": first_published,
        "updated_at": str(projection.get("public_updated_at") or ""),
        "query_partition_id": item["partition_id"],
        "batch_id": config["batch_id"],
        "retrieved_at": item.get("retrieved_at", ""),
        "record_status": record_status,
        "metadata_path": item.get("metadata_path", ""),
        "metadata_sha256": item.get("metadata_sha256", ""),
        "attachment_count": len(projection.get("attachments") or []),
        "withdrawn_status": "withdrawn" if projection.get("withdrawn_notice") else "not_withdrawn",
    }


def _file_index(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_root = root / "raw"
    if not raw_root.exists():
        return rows
    for path in sorted(item for item in raw_root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if str(relative).startswith("raw/search/"):
            kind = "search_api_response"
        elif str(relative).startswith("raw/search_recheck/"):
            kind = "search_api_recheck_response"
        elif str(relative).startswith("raw/content_metadata/"):
            kind = "content_api_metadata_projection"
        elif str(relative).startswith("raw/fetch_checkpoints/"):
            kind = "content_fetch_checkpoint"
        else:
            kind = "downloaded_content"
        rows.append(
            {
                "artifact_kind": kind,
                "path": relative_path(path),
                "byte_size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def run_enumeration(
    config: dict[str, Any], *, resume: bool, smoke: bool, limit: int | None
) -> dict[str, Any]:
    formal_root = resolve_path(config["paths"]["work_package"])
    root = formal_root / "_smoke" if smoke else formal_root
    root.mkdir(parents=True, exist_ok=True)
    client = HttpClient(config["http"])
    scope = config["scope"]
    partitions = build_year_partitions(
        date.fromisoformat(str(scope["start_date"])), date.fromisoformat(str(scope["end_date"]))
    )
    page_size = int(scope["page_size"])
    search_items: list[dict[str, Any]] = []
    partition_rows: list[dict[str, Any]] = []
    global_remaining = limit

    for partition_id, partition_start, partition_end in partitions:
        if global_remaining is not None and global_remaining <= 0:
            break
        started_at = utc_now()
        page_start = 0
        page_count = 0
        initial_total: int | None = None
        raw_paths: list[str] = []
        partition_results: list[dict[str, Any]] = []
        error = ""
        while True:
            url = search_url(
                config, partition_start, partition_end, start=page_start, count=page_size
            )
            checkpoint_path = root / "raw/search" / partition_id / f"page_{page_start:06d}.json"
            payload, result, retrieved_at = _fetch_json_checkpoint(
                client, url, checkpoint_path, resume=resume
            )
            if payload is None:
                error = result.error if result else "unknown_search_failure"
                break
            raw_paths.append(relative_path(checkpoint_path))
            page_count += 1
            total = int(payload.get("total", -1))
            if initial_total is None:
                initial_total = total
            elif total != initial_total:
                error = f"total drifted during pagination: {initial_total} -> {total}"
                break
            results = payload.get("results")
            if not isinstance(results, list):
                error = "results is not a list"
                break
            for record in results:
                if not isinstance(record, dict):
                    continue
                partition_results.append(record)
                search_items.append(
                    {
                        "partition_id": partition_id,
                        "partition_start": partition_start,
                        "partition_end": partition_end,
                        "search_record": record,
                        "search_retrieved_at": retrieved_at,
                    }
                )
                if global_remaining is not None:
                    global_remaining -= 1
                    if global_remaining <= 0:
                        break
            if global_remaining is not None and global_remaining <= 0:
                break
            page_start += len(results)
            if page_start >= total:
                break
            if not results:
                error = f"empty page before total at start={page_start}"
                break

        partition_rows.append(
            {
                "query_partition_id": partition_id,
                "window_start": partition_start.isoformat(),
                "window_end": partition_end.isoformat(),
                "query_url": search_url(
                    config, partition_start, partition_end, start=0, count=page_size
                ),
                "started_at": started_at,
                "finished_at": utc_now(),
                "page_count": page_count,
                "initial_total": initial_total if initial_total is not None else -1,
                "returned_count": len(partition_results),
                "unique_count": len(
                    {
                        str(item.get("link") or item.get("_id") or "")
                        for item in partition_results
                    }
                ),
                "recheck_total": "",
                "status": "partial" if error or smoke else "enumerated_pending_metadata",
                "status_reason": error or ("smoke limit" if smoke else "search pages collected"),
                "raw_response_paths_json": json.dumps(raw_paths, ensure_ascii=False),
            }
        )

    workers = int(config["http"]["workers"])
    metadata_items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _fetch_metadata_record, client, config, root, item, resume=resume
            )
            for item in search_items
        ]
        for future in as_completed(futures):
            metadata_items.append(future.result())
    metadata_items.sort(
        key=lambda item: (
            item["partition_id"],
            str((item.get("projection") or {}).get("first_published_at") or ""),
            str((item.get("projection") or {}).get("content_id") or ""),
        )
    )
    manifest_rows = [_manifest_row(config, item) for item in metadata_items]

    external_counts = Counter(row["external_id"] for row in manifest_rows if row["external_id"])
    duplicated_ids = {value for value, count in external_counts.items() if count > 1}
    for row in manifest_rows:
        if row["external_id"] in duplicated_ids:
            row["record_status"] = "duplicate_external_id_across_partitions"

    by_partition = defaultdict(list)
    for row in manifest_rows:
        by_partition[row["query_partition_id"]].append(row)

    if not smoke:
        timestamp_token = utc_now().replace(":", "").replace("-", "")
        for partition, partition_start, partition_end in partitions:
            url = search_url(config, partition_start, partition_end, start=0, count=0)
            recheck_path = (
                root / "raw/search_recheck" / partition / f"recheck_{timestamp_token}.json"
            )
            payload, result, _ = _fetch_json_checkpoint(client, url, recheck_path, resume=False)
            partition_row = next(
                row for row in partition_rows if row["query_partition_id"] == partition
            )
            if payload is None:
                partition_row["status"] = "partial"
                partition_row["status_reason"] = (
                    f"total recheck failed: {result.error if result else 'unknown'}"
                )
                continue
            recheck_total = int(payload.get("total", -1))
            partition_row["recheck_total"] = recheck_total
            partition_row["raw_response_paths_json"] = json.dumps(
                json.loads(partition_row["raw_response_paths_json"])
                + [relative_path(recheck_path)],
                ensure_ascii=False,
            )
            record_rows = by_partition.get(partition, [])
            allowed_record_statuses = {
                "metadata_verified",
                "metadata_verified_type_drift",
            }
            bad_records = [
                row
                for row in record_rows
                if row["record_status"] not in allowed_record_statuses
            ]
            complete = (
                not bad_records
                and int(partition_row["initial_total"]) == int(partition_row["returned_count"])
                and int(partition_row["returned_count"]) == len(record_rows)
                and recheck_total == int(partition_row["initial_total"])
                and int(partition_row["initial_total"]) < int(scope["maximum_api_count"])
            )
            partition_row["status"] = "complete_as_visible" if complete else "partial"
            if complete:
                partition_row["status_reason"] = (
                    "pagination returned API total; key metadata verified; end total unchanged"
                )
            else:
                partition_row["status_reason"] = (
                    f"initial={partition_row['initial_total']}; returned={partition_row['returned_count']}; "
                    f"metadata_rows={len(record_rows)}; bad_metadata={len(bad_records)}; "
                    f"recheck={recheck_total}"
                )

    write_csv_atomic(root / "enumeration_manifest.csv", ENUMERATION_COLUMNS, manifest_rows)
    partition_columns = [
        "query_partition_id",
        "window_start",
        "window_end",
        "query_url",
        "started_at",
        "finished_at",
        "page_count",
        "initial_total",
        "returned_count",
        "unique_count",
        "recheck_total",
        "status",
        "status_reason",
        "raw_response_paths_json",
    ]
    write_csv_atomic(root / "query_partitions.csv", partition_columns, partition_rows)
    file_index = _file_index(root)
    write_csv_atomic(
        root / "content_file_index.csv",
        ["artifact_kind", "path", "byte_size", "sha256"],
        file_index,
    )
    summary = {
        "batch_id": config["batch_id"],
        "run_kind": "smoke" if smoke else "formal",
        "generated_at": utc_now(),
        "partition_count": len(partition_rows),
        "complete_partition_count": sum(
            row["status"] == "complete_as_visible" for row in partition_rows
        ),
        "api_total_sum": sum(max(0, int(row["initial_total"])) for row in partition_rows),
        "manifest_rows": len(manifest_rows),
        "unique_external_ids": len(external_counts),
        "duplicate_external_ids": sorted(duplicated_ids),
        "record_status_counts": dict(Counter(row["record_status"] for row in manifest_rows)),
        "attachment_links": sum(int(row["attachment_count"]) for row in manifest_rows),
        "body_persisted_count": 0,
    }
    write_json_atomic(root / "enumeration_summary.json", summary)
    return summary


def _load_projection(path_value: str) -> dict[str, Any]:
    wrapper = json.loads(resolve_path(path_value).read_text(encoding="utf-8"))
    projection = wrapper.get("metadata_projection")
    if not isinstance(projection, dict):
        raise ValueError(f"Missing metadata_projection in {path_value}")
    return projection


def build_content_objects(
    config: dict[str, Any], manifest_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    objects: dict[str, dict[str, Any]] = {}
    for row in manifest_rows:
        external_id = row["external_id"]
        web_url = row["canonical_url"]
        web_id = stable_id("cnt", "webpage", web_url)
        web = objects.setdefault(
            web_id,
            {
                "content_object_id": web_id,
                "object_kind": "webpage",
                "external_content_id": external_id,
                "parent_external_ids": [],
                "request_url": web_url,
                "title": row.get("title", ""),
                "observed_titles": [row.get("title", "")],
                "declared_mime_type": "text/html",
                "declared_file_size": "",
                "declared_page_count": "",
                "relations": [],
            },
        )
        web["parent_external_ids"].append(external_id)
        web["relations"].append({"parent_external_id": external_id, "ordinal": 0})
        if not row.get("metadata_path"):
            continue
        projection = _load_projection(row["metadata_path"])
        for position, attachment in enumerate(projection.get("attachments") or []):
            url = str(attachment.get("url") or "")
            if not url:
                continue
            object_id = stable_id("cnt", "attachment", url)
            content_object = objects.setdefault(
                object_id,
                {
                    "content_object_id": object_id,
                    "object_kind": "attachment",
                    "external_content_id": str(attachment.get("id") or ""),
                    "parent_external_ids": [],
                    "request_url": url,
                    "title": str(attachment.get("title") or ""),
                    "observed_titles": [],
                    "declared_mime_type": str(attachment.get("content_type") or ""),
                    "declared_file_size": attachment.get("file_size") or "",
                    "declared_page_count": attachment.get("number_of_pages") or "",
                    "relations": [],
                },
            )
            attachment_title = str(attachment.get("title") or "")
            if attachment_title and not content_object["title"]:
                content_object["title"] = attachment_title
            if attachment_title and attachment_title not in content_object["observed_titles"]:
                content_object["observed_titles"].append(attachment_title)
            content_object["parent_external_ids"].append(external_id)
            content_object["relations"].append(
                {"parent_external_id": external_id, "ordinal": position}
            )
    return sorted(objects.values(), key=lambda row: (row["object_kind"], row["request_url"]))


def _validate_download(result: HttpResult, declared_mime: str) -> str:
    if result.status_code != 200:
        return result.error or f"HTTP {result.status_code}"
    mime = result.mime_type.lower()
    declared = declared_mime.lower()
    if "pdf" in declared and not result.body.startswith(b"%PDF-"):
        return "declared PDF did not have a PDF file signature"
    if "html" in declared or mime == "text/html":
        lowered = result.body[:20000].lower()
        if b"<main" not in lowered:
            return "HTML did not contain a main content element; possible shell/error page"
        if b"access denied" in lowered or b"forbidden" in lowered:
            return "HTML resembles an access-denied page"
    return ""


def run_fetch(config: dict[str, Any], *, resume: bool, smoke: bool, limit: int | None) -> dict[str, Any]:
    formal_root = resolve_path(config["paths"]["work_package"])
    root = formal_root / "_smoke" if smoke else formal_root
    manifest_path = root / "enumeration_manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Run enum first: {manifest_path}")
    manifest_rows = read_csv(manifest_path)
    objects = build_content_objects(config, manifest_rows)
    if limit is not None:
        objects = objects[:limit]
    policy = config["content_fetch"]
    enabled = bool(policy["enabled"])
    if enabled and str(policy["ethics_status"]) not in {"approved", "exempt", "not_applicable"}:
        raise ValueError("content_fetch.enabled requires a documented non-pending ethics status")
    previous: dict[str, dict[str, str]] = {}
    output_path = root / "fetch_manifest.csv"
    if resume and output_path.exists():
        previous = {row["content_object_id"]: row for row in read_csv(output_path)}
    checkpoint_root = root / "raw/fetch_checkpoints"
    if resume and checkpoint_root.exists():
        for checkpoint_path in sorted(checkpoint_root.glob("*.json")):
            payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint_row = payload.get("fetch_row")
            if isinstance(checkpoint_row, dict) and checkpoint_row.get("content_object_id"):
                previous[str(checkpoint_row["content_object_id"])] = {
                    str(key): value for key, value in checkpoint_row.items()
                }
    client = HttpClient(config["http"])
    fetch_version = "govuk_content_fetch_v1"
    parse_version = "not_run"
    rows: list[dict[str, Any]] = []

    def record(row: dict[str, Any]) -> None:
        rows.append(row)
        if enabled:
            checkpoint_path = checkpoint_root / f"{row['content_object_id']}.json"
            write_json_atomic(checkpoint_path, {"fetch_row": row})

    for content_object in objects:
        prior = previous.get(content_object["content_object_id"])
        if prior and prior.get("collection_status") == "success" and prior.get("raw_path"):
            raw_path = resolve_path(prior["raw_path"])
            if raw_path.exists() and sha256_file(raw_path) == prior.get("content_sha256"):
                record(prior)
                continue
        base_row = {
            "batch_id": config["batch_id"],
            "content_object_id": content_object["content_object_id"],
            "object_kind": content_object["object_kind"],
            "external_content_id": content_object["external_content_id"],
            "parent_external_ids": json.dumps(
                sorted(set(content_object["parent_external_ids"])), ensure_ascii=False
            ),
            "request_url": content_object["request_url"],
            "final_url": "",
            "retrieved_at": "",
            "status_code": "",
            "mime_type": "",
            "declared_mime_type": content_object["declared_mime_type"],
            "declared_file_size": content_object["declared_file_size"],
            "declared_page_count": content_object["declared_page_count"],
            "content_sha256": "",
            "raw_path": "",
            "fetch_version": fetch_version,
            "parse_version": parse_version,
            "public_access_status": policy["public_access_status"],
            "collection_status": policy["collection_status"],
            "research_processing_status": policy["research_processing_status"],
            "redistribution_status": policy["redistribution_status"],
            "ethics_status": policy["ethics_status"],
            "failure_reason": policy["rights_basis"],
        }
        if not enabled:
            record(base_row)
            continue
        result = client.get(content_object["request_url"])
        failure = _validate_download(result, content_object["declared_mime_type"])
        base_row.update(
            {
                "final_url": result.final_url,
                "retrieved_at": result.retrieved_at,
                "status_code": result.status_code,
                "mime_type": result.mime_type,
            }
        )
        if failure:
            base_row["collection_status"] = (
                "not_found" if result.status_code == 404 else "access_denied"
                if result.status_code == 403
                else "rate_limited"
                if result.status_code == 429
                else "failed"
            )
            base_row["failure_reason"] = failure
            record(base_row)
            continue
        extension = ".pdf" if result.body.startswith(b"%PDF-") else ".html"
        raw_path = root / "raw/content" / f"{content_object['content_object_id']}{extension}"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = raw_path.with_suffix(raw_path.suffix + ".tmp")
        temporary.write_bytes(result.body)
        os.replace(temporary, raw_path)
        base_row.update(
            {
                "content_sha256": sha256_file(raw_path),
                "raw_path": relative_path(raw_path),
                "collection_status": "success",
                "failure_reason": "",
            }
        )
        record(base_row)

    write_csv_atomic(output_path, FETCH_COLUMNS, rows)
    successes = [row for row in rows if row["collection_status"] == "success"]
    failures = [row for row in rows if row["collection_status"] in FETCH_FAILURE_STATUSES]
    skipped = [row for row in rows if str(row["collection_status"]).startswith("skipped")]
    pending = [
        row
        for row in rows
        if row not in successes and row not in failures and row not in skipped
    ]
    failed_or_pending = [row for row in rows if row["collection_status"] != "success"]
    write_csv_atomic(root / "success_records.csv", FETCH_COLUMNS, successes)
    write_csv_atomic(root / "failed_records.csv", FETCH_COLUMNS, failures)
    write_csv_atomic(root / "skipped_records.csv", FETCH_COLUMNS, skipped)
    write_csv_atomic(root / "pending_records.csv", FETCH_COLUMNS, pending)
    write_csv_atomic(
        root / "failed_or_pending_records.csv", FETCH_COLUMNS, failed_or_pending
    )
    file_index = _file_index(root)
    write_csv_atomic(
        root / "content_file_index.csv",
        ["artifact_kind", "path", "byte_size", "sha256"],
        file_index,
    )
    summary = {
        "generated_at": utc_now(),
        "content_objects": len(rows),
        "webpages": sum(row["object_kind"] == "webpage" for row in rows),
        "attachments": sum(row["object_kind"] == "attachment" for row in rows),
        "successful": sum(row["collection_status"] == "success" for row in rows),
        "failed": len(failures),
        "skipped": len(skipped),
        "pending": len(pending),
        "failed_or_pending": len(failed_or_pending),
        "status_counts": dict(Counter(row["collection_status"] for row in rows)),
    }
    write_json_atomic(root / "fetch_summary.json", summary)
    return summary


def run_verification(config: dict[str, Any]) -> dict[str, Any]:
    root = resolve_path(config["paths"]["work_package"])
    partitions = read_csv(root / "query_partitions.csv")
    manifest = read_csv(root / "enumeration_manifest.csv")
    fetches = read_csv(root / "fetch_manifest.csv")
    pending = read_csv(root / "failed_or_pending_records.csv")
    successes = read_csv(root / "success_records.csv")
    failures = read_csv(root / "failed_records.csv")
    skipped = read_csv(root / "skipped_records.csv")
    pending_only = read_csv(root / "pending_records.csv")
    file_index = read_csv(root / "content_file_index.csv")
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any, expected: Any, note: str) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "observed": observed,
                "expected": expected,
                "note": note,
            }
        )

    expected_partitions = len(
        build_year_partitions(
            date.fromisoformat(str(config["scope"]["start_date"])),
            date.fromisoformat(str(config["scope"]["end_date"])),
        )
    )
    check(
        "partition_count",
        len(partitions) == expected_partitions,
        len(partitions),
        expected_partitions,
        "Every calendar-year partition is present.",
    )
    incomplete = [row["query_partition_id"] for row in partitions if row["status"] != "complete_as_visible"]
    check(
        "partition_status",
        not incomplete,
        incomplete,
        [],
        "All partitions met pagination, metadata and end-total checks.",
    )
    total_sum = sum(int(row["initial_total"]) for row in partitions)
    check(
        "api_total_matches_manifest",
        total_sum == len(manifest),
        {"api_total": total_sum, "manifest": len(manifest)},
        "equal",
        "Partition totals reconcile to manifest rows.",
    )
    external_ids = [row["external_id"] for row in manifest]
    check(
        "unique_external_ids",
        len(external_ids) == len(set(external_ids)) and "" not in external_ids,
        len(set(external_ids)),
        len(external_ids),
        "GOV.UK content_id is complete and unique across partitions.",
    )
    allowed_record_statuses = {"metadata_verified", "metadata_verified_type_drift"}
    bad_records = [
        row["external_id"]
        for row in manifest
        if row["record_status"] not in allowed_record_statuses
    ]
    check(
        "metadata_record_status",
        not bad_records,
        bad_records,
        [],
        "All key dates, types and DEFRA organisation links were rechecked in Content API metadata.",
    )
    start_date = date.fromisoformat(str(config["scope"]["start_date"]))
    end_date = date.fromisoformat(str(config["scope"]["end_date"]))
    out_of_range = []
    for row in manifest:
        try:
            observed_date = date.fromisoformat(row["first_published_at"][:10])
        except ValueError:
            out_of_range.append(row["external_id"])
            continue
        if not start_date <= observed_date <= end_date:
            out_of_range.append(row["external_id"])
    check(
        "date_boundaries",
        not out_of_range,
        out_of_range,
        [],
        "Content API first_published_at falls inside the batch boundary.",
    )
    missing_metadata = []
    for row in manifest:
        path = resolve_path(row["metadata_path"])
        if not path.exists() or sha256_file(path) != row["metadata_sha256"]:
            missing_metadata.append(row["external_id"])
    check(
        "metadata_hashes",
        not missing_metadata,
        missing_metadata,
        [],
        "Every manifest row traces to a saved, checksum-matched metadata projection.",
    )
    missing_files = []
    for row in file_index:
        path = resolve_path(row["path"])
        if not path.exists() or sha256_file(path) != row["sha256"]:
            missing_files.append(row["path"])
    check(
        "raw_file_index",
        not missing_files,
        missing_files,
        [],
        "Indexed raw/search and metadata evidence files exist and match hashes.",
    )
    webpage_count = sum(row["object_kind"] == "webpage" for row in fetches)
    check(
        "webpage_parent_coverage",
        webpage_count == len(manifest),
        webpage_count,
        len(manifest),
        "Every enumerated document has a landing-page content object.",
    )
    non_success = [row for row in fetches if row["collection_status"] != "success"]
    check(
        "failure_pending_manifest_complete",
        len(non_success) == len(pending),
        len(pending),
        len(non_success),
        "Every failed, blocked or pending content object is exported explicitly.",
    )
    classified_ids = [
        row["content_object_id"]
        for subset in (successes, failures, skipped, pending_only)
        for row in subset
    ]
    fetch_ids = [row["content_object_id"] for row in fetches]
    check(
        "fetch_outcome_exports_partition_manifest",
        len(classified_ids) == len(set(classified_ids))
        and sorted(classified_ids) == sorted(fetch_ids),
        {
            "success": len(successes),
            "failed": len(failures),
            "skipped": len(skipped),
            "pending": len(pending_only),
        },
        {"classified_once": len(fetches)},
        "Success, failed, skipped and pending exports partition the fetch manifest exactly once.",
    )
    if not bool(config["content_fetch"]["enabled"]):
        unexpected_success = [row["content_object_id"] for row in fetches if row["collection_status"] == "success"]
        check(
            "content_gate_enforced",
            not unexpected_success,
            unexpected_success,
            [],
            "No body or attachment bytes were downloaded while the gate is pending.",
        )
    verification = {
        "generated_at": utc_now(),
        "batch_id": config["batch_id"],
        "passed": all(item["passed"] for item in checks),
        "batch_status": "partial" if any(row["collection_status"] != "success" for row in fetches) else "complete",
        "enumeration_status": "complete_as_visible" if not incomplete else "partial",
        "content_status": "blocked" if not bool(config["content_fetch"]["enabled"]) else "mixed",
        "checks": checks,
        "counts": {
            "partitions": len(partitions),
            "unique_documents": len(manifest),
            "webpages": webpage_count,
            "attachments": sum(row["object_kind"] == "attachment" for row in fetches),
            "successful_content": sum(row["collection_status"] == "success" for row in fetches),
        },
    }
    write_json_atomic(root / "verification.json", verification)
    if not verification["passed"]:
        raise RuntimeError("Government batch verification failed; inspect verification.json")
    return verification


def _register_rule(
    connection: duckdb.DuckDBPyConnection, version: str, rules: dict[str, Any]
) -> str:
    payload = canonical_json(rules)
    digest = sha256_bytes(payload.encode("utf-8"))
    existing = connection.execute(
        "SELECT rule_sha256 FROM normalisation_rules WHERE rule_version = ?", [version]
    ).fetchone()
    if existing and existing[0] != digest:
        raise ValueError(f"Normalisation rule {version} changed without a new version")
    connection.execute(
        "INSERT INTO normalisation_rules VALUES (?, ?, ?, 'active') ON CONFLICT DO NOTHING",
        [version, digest, payload],
    )
    return digest


def _scalar_int(
    connection: duckdb.DuckDBPyConnection, query: str, parameters: Sequence[Any] | None = None
) -> int:
    row = connection.execute(query, parameters or []).fetchone()
    if row is None:
        raise RuntimeError(f"Expected one scalar result for query: {query}")
    return int(row[0])


def _table_counts(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    tables = [
        "sources",
        "collection_batches",
        "coverage_records",
        "query_partitions",
        "raw_records",
        "documents",
        "document_versions",
        "document_version_raw_links",
        "enumeration_records",
        "organisations",
        "document_organisations",
        "content_objects",
        "document_content_objects",
        "content_fetches",
        "extraction_runs",
        "text_segments",
    ]
    return {
        table: _scalar_int(connection, f"SELECT COUNT(*) FROM {table}") for table in tables
    }


def _query_payload(connection: duckdb.DuckDBPyConnection, query: str) -> dict[str, Any]:
    connection.execute("SET TimeZone = 'UTC'")
    cursor = connection.execute(query)
    columns = [column[0] for column in cursor.description]
    rows = []
    for row in cursor.fetchall():
        rows.append(
            [
                (
                    value.isoformat()
                    if isinstance(value, (date, datetime))
                    else str(value)
                    if isinstance(value, Decimal)
                    else value
                )
                for value in row
            ]
        )
    return {"columns": columns, "rows": rows}


def logical_fingerprint(connection: duckdb.DuckDBPyConnection) -> str:
    queries = {**PILOT_EXPORT_QUERIES, **NEW_EXPORT_QUERIES}
    payload = {name: _query_payload(connection, query) for name, query in queries.items()}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def _core_export_queries() -> dict[str, str]:
    return {**PILOT_EXPORT_QUERIES, **NEW_EXPORT_QUERIES, **CORE_EXPORT_QUERIES}


def core_logical_fingerprint(connection: duckdb.DuckDBPyConnection) -> str:
    payload = {
        name: _query_payload(connection, query)
        for name, query in _core_export_queries().items()
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def core_logical_fingerprint_parts(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, str]:
    return {
        name: sha256_bytes(canonical_json(_query_payload(connection, query)).encode("utf-8"))
        for name, query in _core_export_queries().items()
    }


def _upgrade_to_core_storage(connection: duckdb.DuckDBPyConnection) -> None:
    """Replace the legacy body interface in a new database, never in the frozen source."""
    connection.execute(CORE_STORAGE_SQL)
    connection.execute("DROP TABLE voice_attributions")
    connection.execute("DROP TABLE text_segments")
    connection.execute("DROP TABLE content_fetches")
    connection.execute("ALTER TABLE core_content_fetches RENAME TO content_fetches")
    connection.execute(CORE_TEXT_STORAGE_SQL)


def content_version_from_fetch(fetch: dict[str, Any]) -> dict[str, Any] | None:
    """Return a saved-version record only for a complete, successful fetch."""
    if fetch.get("collection_status") != "success":
        return None
    required = [
        "content_object_id",
        "final_url",
        "retrieved_at",
        "status_code",
        "mime_type",
        "content_sha256",
        "raw_path",
        "fetch_id",
    ]
    missing = [name for name in required if fetch.get(name) in {None, ""}]
    if missing:
        raise ValueError(
            "Successful fetch cannot establish a content version; missing "
            + ", ".join(missing)
        )
    status_code = int(fetch["status_code"])
    if not 200 <= status_code < 300:
        raise ValueError("Successful fetch must have a 2xx status code")
    content_sha = str(fetch["content_sha256"])
    if len(content_sha) != 64:
        raise ValueError("Successful fetch must have a SHA-256 content hash")
    return {
        "content_version_id": stable_id(
            "cntv", str(fetch["content_object_id"]), content_sha
        ),
        "content_object_id": str(fetch["content_object_id"]),
        "content_sha256": content_sha,
        "resolved_url": str(fetch["final_url"]),
        "retrieved_at": fetch["retrieved_at"],
        "status_code": status_code,
        "mime_type": str(fetch["mime_type"]),
        "raw_path": str(fetch["raw_path"]),
        "storage_sha256": content_sha,
        "first_fetch_id": str(fetch["fetch_id"]),
    }


CORE_COPY_TABLES = [
    "schema_versions",
    "normalisation_rules",
    "sources",
    "collection_batches",
    "coverage_records",
    "raw_records",
    "documents",
    "document_versions",
    "document_version_raw_links",
    "organisations",
    "document_organisations",
    "document_relationships",
    "query_partitions",
    "enumeration_records",
    "extraction_runs",
]


def _attach_read_only(
    connection: duckdb.DuckDBPyConnection, source_database: Path
) -> None:
    escaped = str(source_database.resolve()).replace("'", "''")
    connection.execute(f"ATTACH '{escaped}' AS frozen_source (READ_ONLY)")


def _source_rows(
    connection: duckdb.DuckDBPyConnection, query: str
) -> list[dict[str, Any]]:
    cursor = connection.execute(query)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _initialise_core_database(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(PILOT_SCHEMA_SQL)
    connection.execute(MIGRATION_SQL)
    _upgrade_to_core_storage(connection)


def _populate_core_database(
    connection: duckdb.DuckDBPyConnection,
    config: dict[str, Any],
    source_database: Path,
    source_database_sha256: str,
) -> None:
    attached = connection.execute(
        "SELECT COUNT(*) FROM duckdb_databases() WHERE database_name = 'frozen_source'"
    ).fetchone()
    if not attached or not attached[0]:
        _attach_read_only(connection, source_database)
    legacy_segments = _scalar_int(
        connection, "SELECT COUNT(*) FROM frozen_source.text_segments"
    )
    legacy_attributions = _scalar_int(
        connection, "SELECT COUNT(*) FROM frozen_source.voice_attributions"
    )
    if legacy_segments or legacy_attributions:
        raise RuntimeError(
            "Frozen source has legacy text rows that cannot be assigned to an exact "
            "content version without additional evidence"
        )
    for table in CORE_COPY_TABLES:
        connection.execute(
            f"INSERT OR IGNORE INTO {table} SELECT * FROM frozen_source.{table}"
        )

    manifest_path = resolve_path(config["paths"]["frozen_manifest"])
    manifest = read_csv(manifest_path)
    projected_objects = {
        item["content_object_id"]: item for item in build_content_objects(config, manifest)
    }
    source_object_ids = {
        row[0]
        for row in connection.execute(
            "SELECT content_object_id FROM frozen_source.content_objects"
        ).fetchall()
    }
    if source_object_ids != set(projected_objects):
        raise RuntimeError(
            "Frozen content-object identities differ from the frozen manifest projection"
        )
    latest_status = {
        row[0]: row[1]
        for row in connection.execute(
            """
            SELECT content_object_id, collection_status
            FROM frozen_source.content_fetches
            ORDER BY retrieved_at NULLS FIRST, fetch_id
            """
        ).fetchall()
    }
    source_objects = _source_rows(
        connection,
        "SELECT * FROM frozen_source.content_objects ORDER BY content_object_id",
    )
    for row in source_objects:
        projected = projected_objects[str(row["content_object_id"])]
        identity_metadata = {
            "parent_external_ids": sorted(set(projected["parent_external_ids"])),
            "observed_titles": projected["observed_titles"],
            "external_content_id": projected["external_content_id"] or None,
        }
        connection.execute(
            """
            INSERT INTO content_objects (
                content_object_id, object_kind, external_content_id, canonical_url,
                declared_mime_type, declared_file_size, declared_page_count,
                public_access_status, rights_status, ethics_status, title,
                acquisition_status, identity_metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (content_object_id) DO NOTHING
            """,
            [
                row["content_object_id"],
                row["object_kind"],
                row["external_content_id"],
                row["canonical_url"],
                row["declared_mime_type"],
                row["declared_file_size"],
                row["declared_page_count"],
                row["public_access_status"],
                row["rights_status"],
                row["ethics_status"],
                projected["title"],
                latest_status.get(str(row["content_object_id"]), "not_attempted"),
                canonical_json(identity_metadata),
            ],
        )
    connection.execute(
        """
        INSERT OR IGNORE INTO document_content_objects
        SELECT * FROM frozen_source.document_content_objects
        """
    )

    source_fetches = _source_rows(
        connection,
        "SELECT * FROM frozen_source.content_fetches ORDER BY content_object_id, fetch_id",
    )
    for fetch in source_fetches:
        version = content_version_from_fetch(fetch)
        version_id = None
        if version is not None:
            raw_path = resolve_path(version["raw_path"])
            if not raw_path.is_file():
                raise RuntimeError(f"Saved content file is missing: {raw_path}")
            actual_sha = sha256_file(raw_path)
            if actual_sha != version["content_sha256"]:
                raise RuntimeError(f"Saved content hash mismatch: {raw_path}")
            version_id = version["content_version_id"]
            connection.execute(
                """
                INSERT INTO content_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (content_object_id, content_sha256) DO NOTHING
                """,
                [
                    version_id,
                    version["content_object_id"],
                    version["content_sha256"],
                    version["resolved_url"],
                    version["retrieved_at"],
                    version["status_code"],
                    version["mime_type"],
                    raw_path.stat().st_size,
                    version["raw_path"],
                    actual_sha,
                    version["first_fetch_id"],
                    "verified",
                ],
            )
        connection.execute(
            """
            INSERT INTO content_fetches VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            ) ON CONFLICT (fetch_id) DO NOTHING
            """,
            [
                fetch["fetch_id"],
                fetch["batch_id"],
                fetch["content_object_id"],
                version_id,
                fetch["request_url"],
                fetch["final_url"],
                fetch["retrieved_at"],
                fetch["status_code"],
                fetch["mime_type"],
                fetch["content_sha256"],
                fetch["raw_path"],
                fetch["fetch_version"],
                fetch["collection_status"],
                fetch["research_processing_status"],
                fetch["redistribution_status"],
                fetch["failure_reason"],
            ],
        )

    recorded_at = datetime.fromisoformat(
        str(config["migration_recorded_at"]).replace("Z", "+00:00")
    )
    connection.execute(
        "INSERT INTO schema_versions VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
        [
            config["schema_version"],
            recorded_at,
            "Implement approved document/content-object/content-version/text-segment storage boundaries",
        ],
    )
    _register_rule(
        connection,
        str(config["content_object_rule_version"]),
        {
            "source": "frozen GOV.UK metadata projection",
            "identity": "stable object ID from object kind and canonical URL",
            "title": "landing-page title or attachment title retained from the frozen projection",
            "shared_attachment": "one object with all parent publication associations",
            "version_gate": "only successful 2xx fetches with saved bytes and a verified SHA-256 establish a content version",
        },
    )
    migration_id = stable_id(
        "mig", source_database_sha256, str(config["schema_version"])
    )
    connection.execute(
        """
        INSERT INTO schema_migrations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (migration_id) DO NOTHING
        """,
        [
            migration_id,
            config["source_schema_version"],
            config["schema_version"],
            relative_path(source_database),
            source_database_sha256,
            config["decision_record"],
            recorded_at,
            "passed",
        ],
    )


def _core_table_counts(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    tables = [
        row[0]
        for row in connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_catalog = current_database()
              AND table_schema = 'main'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()
    ]
    return {
        table: _scalar_int(connection, f"SELECT COUNT(*) FROM {table}")
        for table in tables
    }


def _core_validation(
    connection: duckdb.DuckDBPyConnection, config: dict[str, Any]
) -> dict[str, bool]:
    expected = config["expected_counts"]

    def scalar(query: str) -> int:
        return _scalar_int(connection, query)

    segment_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info('text_segments')").fetchall()
    }
    return {
        "documents_preserved": scalar("SELECT COUNT(*) FROM documents")
        == int(expected["documents"]),
        "webpages_preserved": scalar(
            "SELECT COUNT(*) FROM content_objects WHERE object_kind = 'webpage'"
        )
        == int(expected["webpages"]),
        "attachments_preserved": scalar(
            "SELECT COUNT(*) FROM content_objects WHERE object_kind = 'attachment'"
        )
        == int(expected["attachments"]),
        "attachment_relations_preserved": scalar(
            "SELECT COUNT(*) FROM document_content_objects WHERE relationship_type = 'attachment'"
        )
        == int(expected["attachment_relations"]),
        "organisations_preserved": scalar("SELECT COUNT(*) FROM organisations")
        == int(expected["organisations"]),
        "document_organisation_relations_preserved": scalar(
            "SELECT COUNT(*) FROM document_organisations"
        )
        == int(expected["document_organisation_relations"]),
        "shared_attachments_preserved": scalar(
            """
            SELECT COUNT(*) FROM (
                SELECT content_object_id
                FROM document_content_objects
                WHERE relationship_type = 'attachment'
                GROUP BY content_object_id
                HAVING COUNT(*) > 1
            )
            """
        )
        == int(expected["shared_attachments"]),
        "document_content_foreign_keys_resolve": scalar(
            """
            SELECT COUNT(*) FROM document_content_objects x
            LEFT JOIN documents d USING (document_id)
            LEFT JOIN content_objects c USING (content_object_id)
            WHERE d.document_id IS NULL OR c.content_object_id IS NULL
            """
        )
        == 0,
        "content_version_foreign_keys_resolve": scalar(
            """
            SELECT COUNT(*) FROM content_versions v
            LEFT JOIN content_objects c USING (content_object_id)
            WHERE c.content_object_id IS NULL
            """
        )
        == 0,
        "fetch_version_foreign_keys_resolve": scalar(
            """
            SELECT COUNT(*) FROM content_fetches f
            LEFT JOIN content_versions v USING (content_version_id)
            WHERE f.content_version_id IS NOT NULL AND v.content_version_id IS NULL
            """
        )
        == 0,
        "blocked_or_failed_fetches_have_no_version": scalar(
            """
            SELECT COUNT(*) FROM content_fetches
            WHERE collection_status <> 'success' AND content_version_id IS NOT NULL
            """
        )
        == 0,
        "successful_fetches_have_version": scalar(
            """
            SELECT COUNT(*) FROM content_fetches
            WHERE collection_status = 'success' AND content_version_id IS NULL
            """
        )
        == 0,
        "content_versions_are_deduplicated": scalar(
            """
            SELECT COUNT(*) FROM (
                SELECT content_object_id, content_sha256
                FROM content_versions
                GROUP BY content_object_id, content_sha256
                HAVING COUNT(*) > 1
            )
            """
        )
        == 0,
        "segments_reference_exact_versions": scalar(
            """
            SELECT COUNT(*) FROM text_segments s
            LEFT JOIN content_versions v USING (content_version_id)
            LEFT JOIN extraction_runs e USING (extraction_run_id)
            WHERE v.content_version_id IS NULL OR e.extraction_run_id IS NULL
            """
        )
        == 0,
        "segment_interface_is_version_based": (
            "content_version_id" in segment_columns and "document_id" not in segment_columns
        ),
        "current_blocked_batch_has_no_content_versions": scalar(
            "SELECT COUNT(*) FROM content_versions"
        )
        == 0,
        "current_blocked_batch_has_no_segments": scalar(
            "SELECT COUNT(*) FROM text_segments"
        )
        == 0,
    }


def _export_core_database(
    connection: duckdb.DuckDBPyConnection, directory: Path
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Any] = {}
    for name, query in _core_export_queries().items():
        payload = _query_payload(connection, query)
        path = directory / f"{name}.csv"
        rows = [dict(zip(payload["columns"], row, strict=True)) for row in payload["rows"]]
        write_csv_atomic(path, payload["columns"], rows)
        outputs[path.name] = {"rows": len(rows), "sha256": sha256_file(path)}
    return outputs


def run_core_migration(config: dict[str, Any]) -> dict[str, Any]:
    root = resolve_path(config["paths"]["work_package"])
    root.mkdir(parents=True, exist_ok=True)
    source_database = resolve_path(config["paths"]["frozen_database"])
    destination = resolve_path(config["paths"]["database"])
    if source_database.resolve() == destination.resolve():
        raise ValueError("Core migration destination must not be the frozen database")
    freeze = json.loads(
        resolve_path(config["paths"]["freeze_record"]).read_text(encoding="utf-8")
    )
    source_sha_before = sha256_file(source_database)
    expected_source_sha = str(freeze["sha256"][source_database.name])
    if source_sha_before != expected_source_sha:
        raise RuntimeError("Frozen source database hash does not match batch_freeze.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="core_migration_", dir=destination.parent) as temporary:
        temp_root = Path(temporary)
        first_db = temp_root / "first.duckdb"
        second_db = temp_root / "second.duckdb"
        with duckdb.connect(str(first_db)) as connection:
            _initialise_core_database(connection)
            _populate_core_database(
                connection, config, source_database, source_sha_before
            )
            counts_before = _core_table_counts(connection)
            _populate_core_database(
                connection, config, source_database, source_sha_before
            )
            counts_after = _core_table_counts(connection)
            first_fingerprint = core_logical_fingerprint(connection)
            first_fingerprint_parts = core_logical_fingerprint_parts(connection)
        with duckdb.connect(str(second_db)) as connection:
            _initialise_core_database(connection)
            _populate_core_database(
                connection, config, source_database, source_sha_before
            )
            second_fingerprint = core_logical_fingerprint(connection)
            second_fingerprint_parts = core_logical_fingerprint_parts(connection)
            final_counts = _core_table_counts(connection)
        idempotent = counts_before == counts_after
        reproducible = first_fingerprint == second_fingerprint
        if not idempotent or not reproducible:
            changed_counts = {
                table: (counts_before.get(table), counts_after.get(table))
                for table in sorted(set(counts_before) | set(counts_after))
                if counts_before.get(table) != counts_after.get(table)
            }
            changed_fingerprint_parts = {
                name: (first_fingerprint_parts.get(name), second_fingerprint_parts.get(name))
                for name in sorted(
                    set(first_fingerprint_parts) | set(second_fingerprint_parts)
                )
                if first_fingerprint_parts.get(name) != second_fingerprint_parts.get(name)
            }
            raise RuntimeError(
                "Core migration idempotence or clean rebuild failed: "
                f"idempotent={idempotent}, reproducible={reproducible}, "
                f"changed_counts={changed_counts}, "
                f"changed_fingerprint_parts={changed_fingerprint_parts}, "
                f"fingerprints=({first_fingerprint}, {second_fingerprint})"
            )
        os.replace(second_db, destination)
    source_sha_after = sha256_file(source_database)
    with duckdb.connect(str(destination), read_only=True) as connection:
        relationship_checks = _core_validation(connection, config)
        exports = _export_core_database(
            connection, resolve_path(config["paths"]["exports"])
        )
        _export_dictionary(connection, root / "data_dictionary.csv")
    checks = {
        "frozen_source_hash_preserved": source_sha_before == source_sha_after,
        "duplicate_ingest_idempotent": idempotent,
        "offline_clean_rebuild_reproducible": reproducible,
        **relationship_checks,
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "generated_at": utc_now(),
        "source_database": relative_path(source_database),
        "source_database_sha256_before": source_sha_before,
        "source_database_sha256_after": source_sha_after,
        "database": relative_path(destination),
        "database_sha256": sha256_file(destination),
        "source_schema_version": config["source_schema_version"],
        "schema_version": config["schema_version"],
        "document_normalisation_rule_version": config["normalisation_rule_version"],
        "content_object_rule_version": config["content_object_rule_version"],
        "counts": final_counts,
        "checks": checks,
        "logical_fingerprint": second_fingerprint,
        "exports": exports,
        "body_collection_status": "blocked",
        "successful_body_fetches": 0,
    }
    write_json_atomic(root / "migration_verification.json", result)
    if result["status"] != "passed":
        raise RuntimeError("Core storage migration verification failed")
    return result


def run_core_verification(config: dict[str, Any]) -> dict[str, Any]:
    root = resolve_path(config["paths"]["work_package"])
    source_database = resolve_path(config["paths"]["frozen_database"])
    destination = resolve_path(config["paths"]["database"])
    freeze = json.loads(
        resolve_path(config["paths"]["freeze_record"]).read_text(encoding="utf-8")
    )
    source_sha = sha256_file(source_database)
    with duckdb.connect(str(destination), read_only=True) as connection:
        checks = {
            "frozen_source_hash_matches_freeze_record": source_sha
            == str(freeze["sha256"][source_database.name]),
            **_core_validation(connection, config),
        }
        counts = _core_table_counts(connection)
        fingerprint = core_logical_fingerprint(connection)
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "generated_at": utc_now(),
        "database": relative_path(destination),
        "database_sha256": sha256_file(destination),
        "logical_fingerprint": fingerprint,
        "counts": counts,
        "checks": checks,
        "body_collection_status": "blocked",
    }
    write_json_atomic(root / "verification.json", result)
    if result["status"] != "passed":
        raise RuntimeError("Core storage verification failed")
    return result


def _create_batch_base(
    connection: duckdb.DuckDBPyConnection, config: dict[str, Any], root: Path
) -> tuple[str, str]:
    connection.execute(PILOT_SCHEMA_SQL)
    connection.execute(MIGRATION_SQL)
    recorded_at = datetime.fromisoformat(
        json.loads((root / "enumeration_summary.json").read_text(encoding="utf-8"))[
            "generated_at"
        ].replace("Z", "+00:00")
    )
    connection.execute(
        "INSERT INTO schema_versions VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
        [
            config["schema_version"],
            recorded_at,
            "Add query partitions, enumeration lineage, webpage/attachment content objects, fetch states and extraction runs",
        ],
    )
    rules = {
        "identity": "GOV.UK content_id within the existing policy source",
        "date": "Content API first_published_at; update kept separately",
        "partition": "non-overlapping inclusive UTC calendar years",
        "organisation": "all GOV.UK organisation links retained; emphasis is not silently treated as lead",
        "body_gate": config["content_fetch"],
        "metadata_projection": "govuk_content_metadata_projection_v1; body and rendered documents omitted",
    }
    rule_sha = _register_rule(connection, config["normalisation_rule_version"], rules)
    source_id = stable_id("src", "policy", config["source"]["name"])
    connection.execute(
        """
        INSERT INTO sources VALUES (?, ?, 'policy', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (source_id) DO NOTHING
        """,
        [
            source_id,
            config["source"]["name"],
            "government_policy_source",
            config["source"]["document_type"],
            "GOV.UK Search API enumeration; Content API record verification",
            (
                "Search API query set tagged to DEFRA and filtered as policy_paper, "
                f"{config['scope']['start_date']}..{config['scope']['end_date']} inclusive"
            ),
            "ogl_general_terms_recorded_item_exceptions_pending",
            config["content_fetch"]["rights_basis"],
            config["content_fetch"]["ethics_status"],
            "No verifiable UQ approval or exemption was found; body processing is blocked.",
            canonical_json(
                [
                    "https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html",
                    "https://docs.publishing.service.gov.uk/repos/content-store/content-store-api.html",
                    "https://www.gov.uk/help/terms-conditions",
                    "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
                ]
            ),
            "work_packages/M1_source_access/04_government_corpus_batch/config.yaml",
        ],
    )
    return source_id, rule_sha


def _ingest_formal_batch(
    connection: duckdb.DuckDBPyConnection, config: dict[str, Any], root: Path
) -> None:
    source_id, rule_sha = _create_batch_base(connection, config, root)
    manifest = read_csv(root / "enumeration_manifest.csv")
    partitions = read_csv(root / "query_partitions.csv")
    fetches = read_csv(root / "fetch_manifest.csv")
    verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
    batch_id = str(config["batch_id"])
    enumeration_summary = json.loads(
        (root / "enumeration_summary.json").read_text(encoding="utf-8")
    )
    accessed_at = datetime.fromisoformat(
        enumeration_summary["generated_at"].replace("Z", "+00:00")
    )
    query_conditions = {
        "organisation_slug": config["source"]["organisation_slug"],
        "organisation_content_id": config["source"]["organisation_content_id"],
        "content_store_document_type": config["source"]["document_type"],
        "date_field": config["source"]["date_filter_field"],
        "window_start": str(config["scope"]["start_date"]),
        "window_end": str(config["scope"]["end_date"]),
        "inclusive": True,
        "topic_independent": True,
    }
    content_index_path = root / "content_file_index.csv"
    manifest_path = root / "enumeration_manifest.csv"
    connection.execute(
        """
        INSERT INTO collection_batches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (batch_id) DO NOTHING
        """,
        [
            batch_id,
            source_id,
            accessed_at,
            str(config["source"]["search_api"]),
            canonical_json(query_conditions),
            date.fromisoformat(str(config["scope"]["start_date"])),
            date.fromisoformat(str(config["scope"]["end_date"])),
            config["source"]["date_filter_field"],
            canonical_json(
                {
                    "partition": "calendar_year",
                    "page_size": config["scope"]["page_size"],
                    "partitions": len(partitions),
                }
            ),
            sum(int(row["initial_total"]) for row in partitions),
            len(manifest),
            verification["enumeration_status"],
            "All annual partition totals, pages, projected metadata and end-total checks passed.",
            relative_path(content_index_path),
            sha256_file(content_index_path),
            relative_path(manifest_path),
            sha256_file(manifest_path),
            True,
        ],
    )
    coverage_id = stable_id("cov", batch_id, "document")
    connection.execute(
        """
        INSERT INTO coverage_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (coverage_id) DO NOTHING
        """,
        [
            coverage_id,
            batch_id,
            "unique GOV.UK publication landing-page document",
            len(manifest),
            (
                f"Search API-returned GOV.UK/DEFRA-tagged policy_paper set, {config['scope']['start_date']}.."
                f"{config['scope']['end_date']} inclusive"
            ),
            "Complete topic-independent enumeration inside the recorded query; content_id deduplication.",
            "Not all DEFRA output, not all UK policy, not all predecessor archives, and not a body denominator.",
            verification["enumeration_status"],
            "unresolved_historical_channel_coverage",
            "Early empty years and legacy migration cannot establish absence of policy or continuous archive coverage.",
        ],
    )
    for partition in partitions:
        connection.execute(
            """
            INSERT INTO query_partitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (query_partition_id) DO NOTHING
            """,
            [
                partition["query_partition_id"],
                batch_id,
                date.fromisoformat(partition["window_start"]),
                date.fromisoformat(partition["window_end"]),
                partition["query_url"],
                datetime.fromisoformat(partition["started_at"].replace("Z", "+00:00")),
                datetime.fromisoformat(partition["finished_at"].replace("Z", "+00:00")),
                int(partition["page_count"]),
                int(partition["initial_total"]),
                int(partition["returned_count"]),
                int(partition["unique_count"]),
                int(partition["recheck_total"]) if partition["recheck_total"] else None,
                partition["status"],
                partition["status_reason"],
                partition["raw_response_paths_json"],
            ],
        )

    doc_ids: dict[str, str] = {}
    for row in manifest:
        projection = _load_projection(row["metadata_path"])
        raw_json = canonical_json(projection)
        raw_sha = sha256_bytes(raw_json.encode("utf-8"))
        external_id = row["external_id"]
        raw_id = stable_id("raw", batch_id, external_id, raw_sha)
        document_id = stable_id("doc", source_id, external_id)
        doc_ids[external_id] = document_id
        publication_timestamp = datetime.fromisoformat(
            row["first_published_at"].replace("Z", "+00:00")
        )
        updated_timestamp = (
            datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
            if row["updated_at"]
            else None
        )
        connection.execute(
            """
            INSERT INTO raw_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (raw_record_id) DO NOTHING
            """,
            [
                raw_id,
                batch_id,
                source_id,
                external_id,
                raw_json,
                raw_sha,
                datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00")),
                row["metadata_path"],
                row["record_status"],
            ],
        )
        normalised = {
            "document_id": document_id,
            "source_id": source_id,
            "external_id": external_id,
            "canonical_url": row["canonical_url"],
            "raw_url": row["raw_url"],
            "title": row["title"],
            "language": str(projection.get("locale") or "unknown"),
            "publication_timestamp": row["first_published_at"],
            "updated_timestamp": row["updated_at"] or None,
            "publisher_role": "policy",
            "content_type": row["document_type"],
            "body_status": config["content_fetch"]["collection_status"],
            "attachment_count": int(row["attachment_count"]),
            "withdrawn_status": row["withdrawn_status"],
        }
        normalised_json = canonical_json(normalised)
        normalised_sha = sha256_bytes(normalised_json.encode("utf-8"))
        version_id = stable_id(
            "docv",
            document_id,
            raw_sha,
            config["normalisation_rule_version"],
            rule_sha,
        )
        document_exists = connection.execute(
            "SELECT 1 FROM documents WHERE document_id = ?", [document_id]
        ).fetchone()
        if not document_exists:
            connection.execute(
                """
            INSERT INTO documents (
                document_id, source_id, external_id, canonical_url, title, language,
                publication_date, publication_timestamp, publication_date_basis,
                updated_timestamp, collected_at, publisher_role, content_type, unit_type,
                parent_document_id, interaction_type, body_status, body_status_reason,
                deduplication_status, source_overlap_status, licence_status, ethics_status,
                ethics_reason, research_sample
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'document', NULL, 'original',
                      ?, ?, ?, ?, ?, ?, ?, TRUE)
            ON CONFLICT (document_id) DO NOTHING
            """,
                [
                    document_id,
                    source_id,
                    external_id,
                    row["canonical_url"],
                    row["title"],
                    str(projection.get("locale") or "unknown"),
                    date.fromisoformat(row["first_published_at"][:10]),
                    publication_timestamp,
                    "GOV.UK Content API first_published_at",
                    updated_timestamp,
                    datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00")),
                    "policy",
                    row["document_type"],
                    config["content_fetch"]["collection_status"],
                    "Body and attachment bytes are blocked pending a documented UQ route and item-level rights review.",
                    "content_id_unique_across_formal_manifest",
                    "unknown_not_checked_without_second_source",
                    "ogl_general_terms_recorded_item_exceptions_pending",
                    config["content_fetch"]["ethics_status"],
                    "Metadata research record retained; substantive body processing remains blocked.",
                ],
            )
        connection.execute(
            "UPDATE document_versions SET is_current = false WHERE document_id = ? AND document_version_id <> ?",
            [document_id, version_id],
        )
        connection.execute(
            """
            INSERT INTO document_versions VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
            ON CONFLICT (document_version_id) DO UPDATE SET is_current = TRUE
            """,
            [
                version_id,
                document_id,
                config["normalisation_rule_version"],
                raw_sha,
                normalised_json,
                normalised_sha,
                datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00")),
            ],
        )
        connection.execute(
            "INSERT INTO document_version_raw_links VALUES (?, ?) ON CONFLICT DO NOTHING",
            [version_id, raw_id],
        )
        connection.execute(
            """
            INSERT INTO enumeration_records VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (batch_id, document_id) DO NOTHING
            """,
            [
                batch_id,
                row["query_partition_id"],
                document_id,
                raw_id,
                datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00")),
                row["record_status"],
                row["metadata_path"],
                row["metadata_sha256"],
            ],
        )
        connection.execute("DELETE FROM document_organisations WHERE document_id = ?", [document_id])
        organisations = projection.get("organisations") or []
        emphasised = set(projection.get("emphasised_organisation_ids") or [])
        fractional = 1.0 / len(organisations)
        for organisation in organisations:
            organisation_external_id = str(organisation.get("content_id") or "")
            organisation_id = stable_id("org", "govuk", organisation_external_id)
            connection.execute(
                """
                INSERT INTO organisations VALUES (?, ?, ?, ?)
                ON CONFLICT (organisation_id) DO UPDATE SET
                    organisation_name = excluded.organisation_name,
                    canonical_url = excluded.canonical_url
                """,
                [
                    organisation_id,
                    organisation_external_id,
                    str(organisation.get("title") or ""),
                    str(config["source"]["canonical_base"])
                    + str(organisation.get("base_path") or ""),
                ],
            )
            association = (
                "govuk_tagged_emphasised_organisation"
                if organisation_external_id in emphasised
                else "govuk_tagged_organisation"
            )
            connection.execute(
                """
                INSERT INTO document_organisations VALUES (?, ?, ?, 'unknown', 1.0, ?, ?)
                """,
                [
                    document_id,
                    organisation_id,
                    association,
                    fractional,
                    "full_and_fractional_weights_available; lead interpretation awaiting review",
                ],
            )

    objects = build_content_objects(config, manifest)
    object_by_id = {row["content_object_id"]: row for row in objects}
    for fetch in fetches:
        content_object = object_by_id[fetch["content_object_id"]]
        connection.execute(
            """
            INSERT INTO content_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (content_object_id) DO NOTHING
            """,
            [
                fetch["content_object_id"],
                fetch["object_kind"],
                fetch["external_content_id"] or None,
                fetch["request_url"],
                fetch["declared_mime_type"] or None,
                int(fetch["declared_file_size"]) if fetch["declared_file_size"] else None,
                int(fetch["declared_page_count"]) if fetch["declared_page_count"] else None,
                fetch["public_access_status"],
                fetch["redistribution_status"],
                fetch["ethics_status"],
            ],
        )
        for relation in content_object["relations"]:
            relationship_type = "landing_page" if fetch["object_kind"] == "webpage" else "attachment"
            connection.execute(
                """
                INSERT INTO document_content_objects VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                [
                    doc_ids[relation["parent_external_id"]],
                    fetch["content_object_id"],
                    relationship_type,
                    int(relation["ordinal"]),
                ],
            )
        fetch_id = stable_id("fet", batch_id, fetch["content_object_id"])
        connection.execute(
            """
            INSERT INTO content_fetches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (fetch_id) DO NOTHING
            """,
            [
                fetch_id,
                batch_id,
                fetch["content_object_id"],
                fetch["request_url"],
                fetch["final_url"] or None,
                datetime.fromisoformat(fetch["retrieved_at"].replace("Z", "+00:00"))
                if fetch["retrieved_at"]
                else None,
                int(fetch["status_code"]) if fetch["status_code"] else None,
                fetch["mime_type"] or None,
                fetch["content_sha256"] or None,
                fetch["raw_path"] or None,
                fetch["fetch_version"],
                fetch["collection_status"],
                fetch["research_processing_status"],
                fetch["redistribution_status"],
                fetch["failure_reason"],
            ],
        )
    extraction_id = stable_id("ext", batch_id, "govuk_text_extractor_not_run_v1")
    connection.execute(
        """
        INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
        ON CONFLICT (extraction_run_id) DO NOTHING
        """,
        [
            extraction_id,
            batch_id,
            "govuk_text_extractor_not_run_v1",
            accessed_at,
            accessed_at,
            "blocked",
            "No content bytes were collected because the ethics/research-processing gate is pending.",
        ],
    )
    # Append the original nine-record pilot after the formal current documents exist. The pilot
    # importer therefore retains its batch/raw/version evidence without replacing current rows.
    feasibility = resolve_path(config["paths"]["feasibility_input"])
    pilot_bundle = load_pilot_bundle(feasibility)
    ingest_pilot_bundle(connection, pilot_bundle, project_root=PROJECT_ROOT)
    connection.execute("UPDATE document_versions SET is_current = false")
    connection.execute(
        "UPDATE document_versions SET is_current = true WHERE normalisation_rule_version = ?",
        [config["normalisation_rule_version"]],
    )


def _export_all(connection: duckdb.DuckDBPyConnection, directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, query in {**PILOT_EXPORT_QUERIES, **NEW_EXPORT_QUERIES}.items():
        payload = _query_payload(connection, query)
        path = directory / f"{name}.csv"
        rows = [dict(zip(payload["columns"], row, strict=True)) for row in payload["rows"]]
        write_csv_atomic(path, payload["columns"], rows)
        outputs[path.name] = {"rows": len(rows), "sha256": sha256_file(path)}
    return outputs


def _export_dictionary(connection: duckdb.DuckDBPyConnection, path: Path) -> None:
    rows = connection.execute(
        """
        SELECT table_name, column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'main'
        ORDER BY table_name, ordinal_position
        """
    ).fetchall()
    purposes = {
        "query_partitions": "年度查询分区、分页、total 漂移和原始响应证据。",
        "enumeration_records": "正式 manifest 记录到文档、原始记录和分区的追溯边。",
        "content_objects": "网页与附件的稳定逻辑身份、标题、获取、权利和伦理状态。",
        "document_content_objects": "文档到 landing page/附件的多对多父关系。",
        "content_fetches": "每个内容对象在本批次的成功、失败、跳过或 blocked 状态。",
        "content_versions": "仅由成功保存且哈希核验的原始字节建立的不可变内容版本。",
        "extraction_runs": "文本提取运行及 blocked/failed/success 结果。",
        "text_segments": "指向具体内容版本和提取运行的段落；当前 gate 下为空。",
        "schema_migrations": "冻结源库到新工作库的迁移证据和批准记录引用。",
    }
    output = []
    for table, column, data_type, nullable, _ in rows:
        output.append(
            {
                "table_name": table,
                "table_purpose": purposes.get(table, "沿用 M1.2 临时 schema；定义见 03_database_pilot/data_dictionary.csv。"),
                "field_name": column,
                "duckdb_type": data_type,
                "nullable": nullable,
                "definition": f"{table}.{column}；保留来源语义，不以猜测补缺。",
            }
        )
    write_csv_atomic(
        path,
        ["table_name", "table_purpose", "field_name", "duckdb_type", "nullable", "definition"],
        output,
    )


def run_ingest(config: dict[str, Any]) -> dict[str, Any]:
    root = resolve_path(config["paths"]["work_package"])
    verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
    if not verification.get("passed"):
        raise RuntimeError("verify must pass before ingest")
    destination = resolve_path(config["paths"]["database"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gov_batch_", dir=destination.parent) as temporary:
        temp_root = Path(temporary)
        first_db = temp_root / "first.duckdb"
        second_db = temp_root / "second.duckdb"
        with duckdb.connect(str(first_db)) as connection:
            _ingest_formal_batch(connection, config, root)
            counts_before = _table_counts(connection)
            _ingest_formal_batch(connection, config, root)
            counts_after = _table_counts(connection)
            first_fingerprint = logical_fingerprint(connection)
        with duckdb.connect(str(second_db)) as connection:
            _ingest_formal_batch(connection, config, root)
            second_fingerprint = logical_fingerprint(connection)
            final_counts = _table_counts(connection)
        idempotent = counts_before == counts_after
        reproducible = first_fingerprint == second_fingerprint
        if not idempotent or not reproducible:
            raise RuntimeError("Idempotent or clean-rebuild database check failed")
        os.replace(second_db, destination)
    with duckdb.connect(str(destination), read_only=True) as connection:
        exports = _export_all(connection, resolve_path(config["paths"]["exports"]))
        _export_dictionary(connection, root / "data_dictionary.csv")
        document_count = _scalar_int(connection, "SELECT COUNT(*) FROM documents")
        manifest_count = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM enumeration_records WHERE batch_id = ?",
            [config["batch_id"]],
        )
        current_versions = _scalar_int(
            connection, "SELECT COUNT(*) FROM document_versions WHERE is_current"
        )
        traceable = _scalar_int(
            connection,
            """
            SELECT COUNT(DISTINCT document_id) FROM enumeration_records
            WHERE batch_id = ? AND metadata_path <> '' AND metadata_sha256 <> ''
            """,
            [config["batch_id"]],
        )
    expected = verification["counts"]["unique_documents"]
    checks = {
        "manifest_database_match": manifest_count == expected,
        "unique_documents_match": document_count == expected,
        "one_current_version_per_document": current_versions == document_count,
        "formal_records_traceable": traceable == expected,
        "idempotent_counts": idempotent,
        "clean_rebuild_fingerprint": reproducible,
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "generated_at": utc_now(),
        "database": relative_path(destination),
        "database_sha256": sha256_file(destination),
        "schema_version": config["schema_version"],
        "normalisation_rule_version": config["normalisation_rule_version"],
        "counts": final_counts,
        "checks": checks,
        "logical_fingerprint": second_fingerprint,
        "exports": exports,
        "data_dictionary_sha256": sha256_file(root / "data_dictionary.csv"),
    }
    write_json_atomic(root / "rebuild_manifest.json", result)
    if result["status"] != "passed":
        raise RuntimeError("Database ingest validation failed")
    return result


def _write_schema_decisions(root: Path, schema_version: str) -> None:
    rows = [
        {
            "decision_id": "GOV-001",
            "question": "正式政府批次的稳定文档身份使用什么键？",
            "recommended_option": "使用 GOV.UK content_id；URL 作为可变定位与重复核验字段。",
            "user_decision": "content_id 已作为当前实现键",
            "rationale": "本批次观察到 URL/路径与版本是不同概念；content_id 跨版本更稳定。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "documents、raw_records、document_versions；无需迁移。",
            "status": "implemented",
        },
        {
            "decision_id": "GOV-002",
            "question": "网页 landing page 与每个附件应否作为独立分析单位？",
            "recommended_option": "文档是来源分母；网页和附件是独立内容对象；文本分析先在内容对象内提取，再汇总到文档。",
            "user_decision": "",
            "rationale": "真实记录存在零个、一个或多个附件，网页可能只是附件简介；合并会丢失版本和权利边界。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "content_objects、document_content_objects、未来 text_segments。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-003",
            "question": "policy_paper、news_story、speech 和 parliamentary material 是否进入同一 attention 分母？",
            "recommended_option": "按 genre 分层；只有在研究问题明确且覆盖可比时再加权合并。",
            "user_decision": "",
            "rationale": "本批次只验证 policy_paper；其他类型的生产频率和历史迁移不同。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "sources/content_type/coverage_records；新增批次而非改写本批次。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-004",
            "question": "时间分析使用首次发表还是更新时间？",
            "recommended_option": "来源注意力按 first_published_at 分箱；updated_at 与版本事件单独保留。",
            "user_decision": "",
            "rationale": "真实记录中两者可跨月/跨年；用更新时间替代首次发表会移动文档。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "documents 日期字段已分离；后续派生表需固定分箱规则。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-005",
            "question": "DEFRA 前身机构和旧档案是否并入当前机构历史序列？",
            "recommended_option": "先作为独立 source-era strata；只有核验迁移规则和重叠后才建立可汇总映射。",
            "user_decision": "",
            "rationale": "DEFRA 当前标签可回指早期材料，但不证明前身机构全部材料都被回填。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "新增 source_eras/organisation_successions（若批准）；本批次不改写。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-006",
            "question": "缺失或受阻正文是否仍计入 attention 分母？",
            "recommended_option": "枚举完整的文档仍计入来源发布分母；文本相似度/情绪样本另报可用正文覆盖并做缺失敏感性检查。",
            "user_decision": "",
            "rationale": "删除无正文记录会把获取成功率误当作政策发布率。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "coverage_records 与未来分析样本标志；无需删除文档。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-007",
            "question": "什么集合可作为政策 attention 分母？",
            "recommended_option": "本批次只能作为 DEFRA-tagged policy_paper 内部的文档分母；不能外推到 DEFRA 全部发布或英国政府。",
            "user_decision": "",
            "rationale": "查询排除了其他类型、机构与可能未迁移的旧档案。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "coverage_records；扩大分母需新增完整、独立枚举批次。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-008",
            "question": "多机构文档按完整、emphasised-only 还是分数方式计数？",
            "recommended_option": "唯一文档总体计一次；分机构展示同时提供完整计数和分数计数，emphasised 只作来源字段，不直接等同 lead。",
            "user_decision": "",
            "rationale": "本批次出现多机构和强调机构差异，直接相加会膨胀总分母。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "document_organisations；当前两种权重已可逆保存。",
            "status": "awaiting_review",
        },
        {
            "decision_id": "GOV-009",
            "question": "新闻小样本到来后哪些政府字段进入共同 schema？",
            "recommended_option": "只共享 source/document/content-object/version/date/provenance 核心；出版角色、genre、byline/quoted speaker 保持来源特定字段。",
            "user_decision": "",
            "rationale": "没有新闻实样本前统一全部字段会提前抹平来源差异。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "取得 Guardian 等新闻小样本后提出 v3 迁移；当前仅 proposed。",
            "status": "proposed",
        },
        {
            "decision_id": "GOV-010",
            "question": "Search API 枚举时为 policy_paper、但 Content API 当前类型已变化的记录如何进入分母？",
            "recommended_option": "同时保留 search_document_type 与 verified_document_type；查询时点分母按 Search 命中纳入，按当前 genre 分析时另做排除该记录的敏感性结果。",
            "user_decision": "",
            "rationale": "本批次实际出现 1 条 policy_paper → guidance 类型漂移；静默覆盖任一字段都会丢失查询条件或当前来源状态。",
            "reviewer": "Dai Pan (planned)",
            "review_date": "",
            "schema_version": schema_version,
            "affected_data_or_migration": "enumeration_manifest 已保留双字段；后续文档类型历史若需要可新增 type_observations，不改写原始记录。",
            "status": "awaiting_review",
        },
    ]
    write_csv_atomic(
        root / "schema_decisions.csv",
        [
            "decision_id",
            "question",
            "recommended_option",
            "user_decision",
            "rationale",
            "reviewer",
            "review_date",
            "schema_version",
            "affected_data_or_migration",
            "status",
        ],
        rows,
    )


def run_report(config: dict[str, Any]) -> dict[str, Any]:
    root = resolve_path(config["paths"]["work_package"])
    database = resolve_path(config["paths"]["database"])
    verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
    rebuild = json.loads((root / "rebuild_manifest.json").read_text(encoding="utf-8"))
    cross_run_path = root / "cross_run_rebuild_check.json"
    cross_run = (
        json.loads(cross_run_path.read_text(encoding="utf-8")) if cross_run_path.exists() else None
    )
    freeze_path = root / "batch_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8")) if freeze_path.exists() else None
    partitions = read_csv(root / "query_partitions.csv")
    manifest = read_csv(root / "enumeration_manifest.csv")
    fetches = read_csv(root / "fetch_manifest.csv")
    with duckdb.connect(str(database), read_only=True) as connection:
        unique_documents = _scalar_int(connection, "SELECT COUNT(*) FROM documents")
        organisation_links = _scalar_int(
            connection, "SELECT COUNT(*) FROM document_organisations"
        )
        organisation_count = _scalar_int(connection, "SELECT COUNT(*) FROM organisations")
        multi_org = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM (SELECT document_id FROM document_organisations GROUP BY document_id HAVING COUNT(*) > 1)",
        )
        weight_row = connection.execute(
            "SELECT SUM(full_count_weight), SUM(fractional_count_weight) FROM document_organisations"
        ).fetchone()
        if weight_row is None:
            raise RuntimeError("Expected institution counting weights")
        full_sum, fractional_sum = weight_row
        attachment_objects = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM content_objects WHERE object_kind='attachment'",
        )
        attachment_links = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM document_content_objects WHERE relationship_type='attachment'",
        )
        shared_attachments = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM (
                SELECT content_object_id FROM document_content_objects
                WHERE relationship_type='attachment' GROUP BY content_object_id HAVING COUNT(*) > 1
            )
            """,
        )
        updated_later = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM documents WHERE updated_timestamp > publication_timestamp",
        )
        withdrawn = sum(row["withdrawn_status"] == "withdrawn" for row in manifest)
        successful_content = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM content_fetches WHERE collection_status='success'",
        )
        segments = _scalar_int(connection, "SELECT COUNT(*) FROM text_segments")
        earliest = connection.execute(
            "SELECT external_id, title, publication_date FROM documents ORDER BY publication_date, external_id LIMIT 1"
        ).fetchone()
        latest = connection.execute(
            "SELECT external_id, title, publication_date FROM documents ORDER BY publication_date DESC, external_id LIMIT 1"
        ).fetchone()
        most_org = connection.execute(
            """
            SELECT d.external_id, d.title, COUNT(*) AS n
            FROM documents d JOIN document_organisations USING (document_id)
            GROUP BY d.external_id, d.title ORDER BY n DESC, d.external_id LIMIT 1
            """
        ).fetchone()
        most_attachments = connection.execute(
            """
            SELECT d.external_id, d.title, COUNT(*) AS n
            FROM documents d JOIN document_content_objects x USING (document_id)
            WHERE x.relationship_type='attachment'
            GROUP BY d.external_id, d.title ORDER BY n DESC, d.external_id LIMIT 1
            """
        ).fetchone()
        if earliest is None or latest is None or most_org is None:
            raise RuntimeError("Expected at least one enumerated document with organisation links")

    nonzero_years = [
        int(row["window_start"][:4]) for row in partitions if int(row["initial_total"]) > 0
    ]
    zero_years = [int(row["window_start"][:4]) for row in partitions if int(row["initial_total"]) == 0]
    observation_started = str(config["scope"]["observation_started_at"])
    observation_cutoff = str(config["scope"]["observation_cutoff_at"])
    status_counts = Counter(row["collection_status"] for row in fetches)
    webpage_objects = sum(row["object_kind"] == "webpage" for row in fetches)
    type_drifts = [row for row in manifest if row["record_status"] == "metadata_verified_type_drift"]
    data_quality_lines = [
        "# 政府批次数据质量报告",
        "",
        f"**验收：{'PASS' if verification['passed'] and rebuild['status'] == 'passed' else 'FAIL'}。** "
        "PASS 表示限定元数据枚举、追溯和离线重建满足本批次标准；正文与附件字节仍为 blocked。",
        "",
        "## 自动检查",
        "",
        "| 检查 | 观察值 | 期望 | 结果 |",
        "|---|---|---|---|",
    ]
    for item in verification["checks"]:
        data_quality_lines.append(
            f"| `{item['name']}` | {json.dumps(item['observed'], ensure_ascii=False)} | "
            f"{json.dumps(item['expected'], ensure_ascii=False)} | {'PASS' if item['passed'] else 'FAIL'} |"
        )
    data_quality_lines.extend(
        [
            "",
            "## 数据库与计数检查",
            "",
            f"- manifest / 数据库唯一文档：{len(manifest)} / {unique_documents}。",
            f"- 机构实体 / 关系：{organisation_count} / {organisation_links}；多机构文档 {multi_org}。",
            f"- 完整计数权重和 / 分数权重和：{float(full_sum):.1f} / {float(fractional_sum):.1f}。",
            f"- 网页内容对象 / 唯一附件对象 / 附件父关系：{webpage_objects} / {attachment_objects} / {attachment_links}。",
            f"- 成功内容 / 真实段落 / 可向量化段落：{successful_content} / {segments} / 0。",
            f"- 重复导入计数不变：{'PASS' if rebuild['checks']['idempotent_counts'] else 'FAIL'}。",
            f"- 干净离线重建指纹一致：{'PASS' if rebuild['checks']['clean_rebuild_fingerprint'] else 'FAIL'}。",
            (
                f"- 跨运行逻辑指纹一致（验证时间变化后）：{'PASS' if cross_run and cross_run['passed'] else 'NOT RUN'}；"
                "DuckDB 物理文件 SHA 按每次构建单独记录，不作为逻辑等价判断。"
            ),
            "",
            "## 明确限制",
            "",
            "- Search API 没有不可变快照；结论是记录查询时点的可见集合。",
            f"- 实际观察窗口为 {observation_started} 至 {observation_cutoff}；日期过滤到 2026-09-21 不代表观察到当日 23:59:59。",
            f"- Search/API 类型复核出现 {len(type_drifts)} 条漂移；manifest 同时保留查询类型与当前 Content API 类型。",
            "- 早期零年份和当前最早记录不能证明来源历史起点或当年无政策。",
            "- 伦理状态保持 pending；没有把 OGL、公开可访问或元数据成功误写成研究审批。",
            "- 正文、附件下载、文本提取和向量化均未发生；它们是 blocked，不是空字符串或成功。",
            "",
        ]
    )
    (root / "data_quality_report.md").write_text("\n".join(data_quality_lines), encoding="utf-8")

    coverage_lines = [
        "# GOV.UK / DEFRA 批次覆盖报告",
        "",
        "## 结论",
        "",
        f"枚举状态为 **{verification['enumeration_status']}**：通过 Search API 的 39 个年度分区得到 {len(manifest)} 个唯一文档，"
        "每个分区的分页返回量与 Search API total 对齐；Content API 仅用于单条关键元数据核验，结束 total 复查无数量漂移。",
        "",
        f"内容状态为 **{verification['content_status']}**：{webpage_objects} 个网页和 {attachment_objects} 个唯一附件对象已枚举，"
        f"成功正文/附件字节 {successful_content}，提取文本 {segments}。这不是全文语料库。",
        "",
        "## 四层覆盖",
        "",
        "| 层级 | 分子 / 分母 | 状态 | 可解释性 |",
        "|---|---:|---|---|",
        f"| 枚举 | {len(manifest)} / {len(manifest)} 文档 | complete_as_visible | 只限 Search API 在查询时点返回的 GOV.UK、DEFRA 标签、policy_paper 条件集 |",
        f"| 内容获取 | {successful_content} / {len(fetches)} 内容对象 | blocked | 伦理/研究处理路线 pending；非技术失败 |",
        f"| 文本提取 | {segments} / {len(fetches)} 内容对象 | blocked | 没有输入字节，不运行提取 |",
        f"| 后续文本分析可用 | 0 / {len(manifest)} 文档 | not_ready | 不能进行相似度、情绪或时间序列 |",
        "",
        "## 机构、年份与内容对象",
        "",
        "- 发现接口：GOV.UK Search API；机构筛选为含 DEFRA 标签；查询类型 `policy_paper`。Content API 不承担全量发现。",
        f"- 实际动态索引观察窗口：{observation_started} 至 {observation_cutoff}（UTC）。",
        f"- 日期目标：1988–2026-09-21；非空年份 {min(nonzero_years)}–{max(nonzero_years)}，共 {len(nonzero_years)} 年。",
        f"- 实际最早 / 最晚首次发表日期：{earliest[2]} / {latest[2]}；两者只是本次查询命中的边界，不是历史覆盖起止。",
        f"- 查询为零的年份：{', '.join(map(str, zero_years))}。这些是“查询完整且可见结果为 0”，但历史档案接入仍 unresolved。",
        f"- 唯一文档 {unique_documents}；机构关系 {organisation_links}；多机构文档 {multi_org}。",
        f"- 网页 {webpage_objects}；唯一附件 {attachment_objects}；附件关系 {attachment_links}；跨页面共享附件 {shared_attachments}。",
        f"- 首次发表后仍有更新的文档 {updated_later}；撤稿标记 {withdrawn}。",
        f"- 类型漂移 {len(type_drifts)}：Search 命中时属于 `policy_paper`，单条核验时当前类型不同；记录仍保留在查询时点分母并单独标记。",
        "",
        "## 年度 Search API 返回分布",
        "",
        "| 年份 | 唯一记录 | 年份 | 唯一记录 | 年份 | 唯一记录 |",
        "|---:|---:|---:|---:|---:|---:|",
        *[
            "| "
            + " | ".join(
                [
                    value
                    for offset in range(3)
                    for value in (
                        str(int(partitions[index + offset]["window_start"][:4])),
                        str(int(partitions[index + offset]["initial_total"])),
                    )
                ]
            )
            + " |"
            for index in range(0, 39, 3)
        ],
        "",
        "## 能支持与不能支持",
        "",
        "能支持：限定来源内的文档发布分母、年份/机构/附件结构审计、缺失正文覆盖评估、后续从相同 manifest 恢复。",
        "",
        "不能支持：DEFRA 全部发布、英国全部政府政策、气候主题比例、1988 年以来连续官方档案、正文语义或跨政府—媒体比较。",
        "",
    ]
    (root / "coverage_report.md").write_text("\n".join(coverage_lines), encoding="utf-8")

    schema_lines = [
        "# Dai Pan schema review：基于正式政府批次的审阅材料",
        "",
        "## 当前数据流",
        "",
        "`Search API 年度分区 → 原始分页响应 → Content API 元数据投影 → enumeration_manifest → "
        "网页/附件内容对象与 fetch 状态 → 原始记录/文档版本 → DuckDB → CSV/覆盖报告`。",
        "",
        "文档是来源发布分母；机构和内容对象都是多对多关系。正文提取属于内容版本下游，当前因 gate blocked，"
        "没有伪造 `text_segments`。旧 9 条试点作为独立 batch/raw evidence 保留，正式批次新增版本而非覆盖旧证据。",
        "",
        "## 核心字段为什么存在",
        "",
        "| 对象 / 字段 | 需要它的原因 | 本批次证据 |",
        "|---|---|---|",
        f"| `batch_id` / `query_partition_id` | 把动态索引观察固定到范围、时点和页 | {len(partitions)} 个年度分区；结束 total 复查 |",
        "| `external_id` (`content_id`) | 跨路径/版本的稳定身份 | manifest 内唯一；URL 单独保存 |",
        f"| 首次发表 / 更新 / 获取时间 | 避免把更新移成新发布 | {updated_later} 条更新时间晚于首次发表 |",
        f"| 文档—机构关系 | 不把共同发布膨胀成新文档 | {multi_org} 个多机构文档、{organisation_links} 条关系 |",
        f"| content object / parent relation | 网页、多个附件和共享附件需分别追溯 | {attachment_objects} 个附件对象、{attachment_links} 条关系 |",
        "| body/rights/ethics 状态 | 公开、可抓、可研究、可再发布不是同一状态 | 当前所有正文对象明确 blocked/pending |",
        "| raw/version/hash | 动态来源可更新；必须恢复旧观察 | 旧试点与正式批次 raw records 均保留 |",
        "",
        "## 真实常见与异常记录",
        "",
        f"- 最早可见记录：`{earliest[0]}`，{earliest[2]}，{earliest[1]}。它只说明当前索引最早命中，不是 DEFRA 历史起点。",
        f"- 机构最多记录：`{most_org[0]}`，{most_org[2]} 个机构，{most_org[1]}。",
        (
            f"- 附件最多记录：`{most_attachments[0]}`，{most_attachments[2]} 个附件，{most_attachments[1]}。"
            if most_attachments
            else "- 本批次没有附件记录。"
        ),
        f"- {updated_later} 条的更新时间晚于首次发表；两种时间不能互相代填。",
        f"- 唯一附件与父关系相差 {attachment_links - attachment_objects}；共享附件对象 {shared_attachments}，说明附件身份和父关系必须分表。",
        (
            f"- 类型漂移记录：`{type_drifts[0]['external_id']}`，{type_drifts[0]['title']}；"
            f"Search 类型 `{type_drifts[0]['search_document_type']}`，当前 Content API 类型 `{type_drifts[0]['verified_document_type']}`。"
            if type_drifts
            else "- 本批次未观察到 Search / Content API 类型漂移。"
        ),
        f"- {withdrawn} 条有撤稿标记；撤稿状态不能用 404 或空正文代替。",
        "",
        "## 已由数据支持的设计",
        "",
        "- `content_id` 去重、URL 单独保留；文档和机构多对多；首次发表与更新时间分离。",
        "- 年度分区、原始响应索引和查询时点是必要 provenance，而不是运行日志装饰。",
        "- 网页/附件作为内容对象、文档作为来源分母；blocked/failed/not_attempted/success 必须分开。",
        "- 元数据版本和内容版本不能合并：本批次只有前者，不能据此声称全文版本已保存。",
        "",
        "## Dai 需要决定",
        "",
        "简版真实例子、推荐方案与研究影响见 `schema_review_brief.md`；完整迁移影响见 `schema_decisions.csv`。"
        "优先审阅 GOV-002 至 GOV-008 及 GOV-010。"
        "普通的 ID、哈希、checkpoint、HTTP 重试和 CSV 导出已经实现，不推给研究判断。",
        "",
        "## 新闻小样本后的调整边界",
        "",
        "先用与本批次共同窗口相交的少量 Guardian/其他获准新闻记录验证：publication/update 日期、article/body 关系、"
        "byline、quoted speaker、修订/更正、转载和许可状态。然后只把已被两类真实数据支持的 source/document/content-object/version/provenance "
        "字段提升为共同 v3；新闻出版角色保持 media，被引部长仍是 attribution，而不是 publisher role。",
        "",
    ]
    (root / "schema_review.md").write_text("\n".join(schema_lines), encoding="utf-8")
    _write_schema_decisions(root, str(config["schema_version"]))

    progress_lines = [
        "# GOV.UK / DEFRA 政府批次进度报告",
        "",
        "## 实际完成",
        "",
        f"- 完成 GOV.UK、DEFRA 标签、`policy_paper`、1988-01-01..2026-09-21 的 39 个年度分区枚举；唯一文档 {len(manifest)}。",
        f"- 实际 Search API 观察窗口为 {observation_started}..{observation_cutoff}（UTC）；未把日期过滤上界误写成全天快照。",
        f"- 保存必要 Search API 原始响应、{len(manifest)} 个不含正文的 Content API 元数据投影、哈希和 checkpoint。",
        f"- Content API 复核发现 {len(type_drifts)} 条文档类型漂移；查询类型与当前类型均已保留，没有静默剔除。",
        f"- 枚举网页 {webpage_objects}、唯一附件 {attachment_objects}、附件父关系 {attachment_links}；下载正文/附件 0。",
        f"- 入库文档 {unique_documents}、机构 {organisation_count}、机构关系 {organisation_links}；旧 9 条试点 evidence 未覆盖。",
        "- 完成重复导入、离线干净重建、manifest/SQL/导出一致性和失败清单检查。",
        "",
        "## 冻结交付状态",
        "",
        f"- 元数据枚举：`complete`（内部验证标签 `{verification['enumeration_status']}`），仅限已记录 Search API 查询集合。",
        f"- 规范化入库与恢复验证：`{rebuild['status']}`；规则版本 `{config['normalisation_rule_version']}`，两次离线重建逻辑指纹一致。",
        "- schema review 材料：`prepared / awaiting Dai review`。",
        "- 正文采集：`blocked`；依据与待确认问题见 `body_collection_gate_review.md`。",
        "- 整体全文语料目标：`incomplete`；没有把元数据完成等同全文完成。",
        f"- 批次冻结：`{'true' if freeze and freeze.get('frozen') else 'false'}`；后续获准正文应另开恢复批次，不改写本冻结证据。",
        "",
        "## 吞吐量与恢复",
        "",
        "年度页与逐条元数据按原子文件 checkpoint；`enum --resume` 只补失败/缺失文件，结束仍复查 total。"
        "数据库可只用已保存 raw/manifest 和旧试点证据离线重建。",
        (
            "验证时间变化后两次独立重建的逻辑指纹一致；物理 DuckDB SHA 分别保存，"
            "不要求字节级布局相同。"
            if cross_run and cross_run["passed"]
            else "跨运行逻辑指纹检查尚未记录。"
        ),
        "",
        "## 下一步",
        "",
        "1. Dai 按 `schema_decisions.csv` 回复 GOV-002..GOV-008 与 GOV-010。",
        "2. 由适当 UQ 路线明确正文研究处理状态，并逐件处理附件例外；若允许，先运行最多 3 条 smoke fetch/extraction 验证。",
        "3. 取得新闻小样本后，以实际异常记录设计跨来源 v3，不提前统一。",
        "",
    ]
    (root / "progress_report.md").write_text("\n".join(progress_lines), encoding="utf-8")
    result = {
        "generated_at": utc_now(),
        "unique_documents": unique_documents,
        "organisation_links": organisation_links,
        "webpages": webpage_objects,
        "unique_attachments": attachment_objects,
        "successful_content": successful_content,
        "text_segments": segments,
        "enumeration_status": verification["enumeration_status"],
        "batch_status": verification["batch_status"],
        "fetch_status_counts": dict(status_counts),
        "document_type_drifts": len(type_drifts),
        "cross_run_rebuild_passed": bool(cross_run and cross_run["passed"]),
        "metadata_enumeration_status": "complete",
        "normalisation_ingest_recovery_status": rebuild["status"],
        "schema_review_status": "prepared_awaiting_dai_review",
        "body_collection_status": "blocked",
        "fulltext_corpus_status": "incomplete",
        "batch_frozen": bool(freeze and freeze.get("frozen")),
    }
    write_json_atomic(root / "report_summary.json", result)
    return result


ACQUISITION_SCRIPT_VERSION = "govuk_content_acquisition_v1"
EXTRACTOR_VERSION = "govuk_source_text_extractor_v1"
PDF_EXTRACTION_LOCK = threading.Lock()


def _normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _url_extension(url: str) -> str:
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ""


def _detect_content_format(
    body: bytes, mime_type: str, declared_mime_type: str, final_url: str
) -> str:
    prefix = body[:4096].lstrip().lower()
    mime = mime_type.lower().split(";", 1)[0].strip()
    declared = declared_mime_type.lower().split(";", 1)[0].strip()
    extension = _url_extension(final_url)
    if body.startswith(b"%PDF-"):
        return "pdf"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if body.startswith((b"\xff\xd8\xff", b"II*\x00", b"MM\x00*")):
        return "image"
    if prefix.startswith((b"<!doctype html", b"<html", b"<main")) or b"<html" in prefix:
        return "html"
    if zipfile.is_zipfile(io.BytesIO(body)):
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                names = set(archive.namelist())
                if "word/document.xml" in names:
                    return "docx"
                if any(name.startswith("ppt/slides/slide") for name in names):
                    return "pptx"
                if "content.xml" in names:
                    package_mime = ""
                    if "mimetype" in names:
                        package_mime = archive.read("mimetype").decode("ascii", "ignore")
                    if "spreadsheet" in package_mime or "spreadsheet" in declared:
                        return "ods"
                    if "text" in package_mime or "opendocument.text" in declared:
                        return "odt"
        except (OSError, zipfile.BadZipFile):
            pass
        return "zip"
    if body.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        if extension == ".xls" or "excel" in declared or "spreadsheet" in declared:
            return "xls"
        return "ole"
    if extension in {".csv", ".tsv"} or mime in {"text/csv", "text/tab-separated-values"}:
        return "csv"
    if extension in {".txt", ".md"} or mime.startswith("text/plain"):
        return "text"
    if extension in {".htm", ".html", ".aspx", ".php"} or mime == "text/html":
        return "html"
    return "binary"


def _format_extension(content_format: str, final_url: str) -> str:
    preferred = {
        "pdf": ".pdf",
        "html": ".html",
        "docx": ".docx",
        "pptx": ".pptx",
        "odt": ".odt",
        "ods": ".ods",
        "csv": ".csv",
        "text": ".txt",
        "xls": ".xls",
        "zip": ".zip",
        "png": ".png",
        "image": _url_extension(final_url) or ".img",
        "ole": _url_extension(final_url) or ".ole",
        "binary": _url_extension(final_url) or ".bin",
    }
    return preferred[content_format]


def _declared_format_family(value: str) -> str:
    lowered = value.lower()
    if not lowered or lowered == "application/octet-stream":
        return ""
    if "pdf" in lowered:
        return "pdf"
    if "html" in lowered:
        return "html"
    if "opendocument.text" in lowered:
        return "odt"
    if "opendocument.spreadsheet" in lowered:
        return "ods"
    if "presentation" in lowered or "powerpoint" in lowered:
        return "pptx"
    if "spreadsheetml" in lowered:
        return "xlsx"
    if "excel" in lowered:
        return "xls"
    if "csv" in lowered:
        return "csv"
    if lowered.startswith("image/"):
        return "image"
    if lowered.startswith("text/"):
        return "text"
    if "zip" in lowered:
        return "zip"
    return ""


def _validation_status(declared_mime: str, actual_format: str) -> str:
    declared_family = _declared_format_family(declared_mime)
    actual_family = "image" if actual_format in {"png", "image"} else actual_format
    compatible = {
        ("text", "csv"),
        ("text", "html"),
        ("xlsx", "zip"),
        ("xls", "ole"),
    }
    if declared_family and declared_family != actual_family and (
        declared_family,
        actual_family,
    ) not in compatible:
        return "mime_mismatch"
    return "validated"


def _validate_acquisition_download(
    result: HttpResult, object_kind: str, declared_mime: str, actual_format: str
) -> tuple[str, str]:
    if result.status_code == 403:
        return "access_denied", result.error or "HTTP 403"
    if result.status_code == 404:
        return "not_found", result.error or "HTTP 404"
    if result.status_code == 429:
        return "rate_limited", result.error or "HTTP 429"
    if not 200 <= result.status_code < 300:
        return "failed_http", result.error or f"HTTP {result.status_code}"
    if not result.body:
        return "empty_response", "2xx response had no content bytes"
    # Error banners can be rendered late in large client-side HTML documents,
    # so validate the full saved response rather than only an initial prefix.
    lowered = result.body.lower()
    error_markers = [
        b"<title>access denied",
        b"<title>forbidden",
        b"the requested page could not be found",
        b"error 404",
        b"404 - page not found",
        b"sorry, we can't find the page you're looking for",
        b"request blocked",
    ]
    if actual_format == "html" and any(marker in lowered for marker in error_markers):
        return "error_page", "2xx HTML response resembled an access/error page"
    if "pdf" in declared_mime.lower() and actual_format != "pdf":
        return "mime_mismatch", "declared PDF did not have a PDF signature"
    if object_kind == "webpage" and actual_format != "html":
        return "mime_mismatch", "landing page response was not HTML"
    return "success", ""


def _decode_text(body: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "windows-1252", "latin-1"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", "replace")


def _extract_html(body: bytes) -> list[dict[str, Any]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(body, "html.parser")
    for element in soup.select(
        "nav, footer, script, style, noscript, template, dialog, "
        ".gem-c-cookie-banner, .govuk-cookie-banner, [aria-label='Cookie banner']"
    ):
        element.decompose()
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article")
    if main is None:
        main = soup.find(id="content") or soup.find(id="main")
    if main is None:
        refresh = soup.find(
            "meta",
            attrs={"http-equiv": lambda value: value and value.lower() == "refresh"},
        )
        if refresh is not None:
            main = soup.body
    if main is None:
        raise ValueError("main_content_not_found")
    segments: list[dict[str, Any]] = []
    seen: set[str] = set()
    title = _normalise_space(soup.title.get_text(" ", strip=True)) if soup.title else ""
    if title:
        seen.add(title)
        segments.append(
            {"segment_kind": "paragraph", "text": title, "locator": "html:title", "heading": title}
        )
    current_heading = title or None
    counters: Counter[str] = Counter()
    for element in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote"]):
        if element.find_parent(["nav", "footer", "aside"]):
            continue
        text = _normalise_space(element.get_text(" ", strip=True))
        if not text or text in seen:
            continue
        seen.add(text)
        tag = element.name.lower()
        counters[tag] += 1
        if tag.startswith("h"):
            current_heading = text
        segments.append(
            {
                "segment_kind": "quoted_block" if tag == "blockquote" else "paragraph",
                "text": text,
                "locator": f"main:{tag}[{counters[tag]}]",
                "heading": current_heading,
            }
        )
    if not segments:
        raise ValueError("main_content_empty")
    return segments


def _extract_pdf(body: bytes) -> list[dict[str, Any]]:
    import pypdfium2 as pdfium

    segments: list[dict[str, Any]] = []
    # PDFium is fast but its native document lifecycle is not safe to exercise
    # concurrently from this process. Downloads remain concurrent; page-text
    # extraction is deliberately serialized.
    with PDF_EXTRACTION_LOCK:
        pdf = pdfium.PdfDocument(body)
        try:
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                text_page = page.get_textpage()
                try:
                    text = text_page.get_text_range() or ""
                finally:
                    text_page.close()
                    page.close()
                block_number = 0
                for line in text.splitlines():
                    value = _normalise_space(line)
                    if not value:
                        continue
                    block_number += 1
                    segments.append(
                        {
                            "segment_kind": "unknown",
                            "text": value,
                            "locator": f"page={page_index + 1};block={block_number}",
                            "heading": None,
                        }
                    )
        finally:
            pdf.close()
    return segments


def _xml_text(element: ET.Element) -> str:
    return _normalise_space(" ".join(value for value in element.itertext() if value))


def _extract_office_zip(body: bytes, content_format: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        if content_format == "docx":
            root = ET.fromstring(archive.read("word/document.xml"))
            for index, element in enumerate(root.findall(".//{*}p"), start=1):
                text = _xml_text(element)
                if text:
                    segments.append({"segment_kind": "paragraph", "text": text, "locator": f"paragraph={index}", "heading": None})
        elif content_format == "pptx":
            slide_names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda value: int(re.search(r"(\d+)", Path(value).stem).group(1)),
            )
            for slide_number, name in enumerate(slide_names, start=1):
                root = ET.fromstring(archive.read(name))
                for block_number, element in enumerate(root.findall(".//{*}p"), start=1):
                    text = _xml_text(element)
                    if text:
                        segments.append({"segment_kind": "unknown", "text": text, "locator": f"slide={slide_number};block={block_number}", "heading": None})
        else:
            root = ET.fromstring(archive.read("content.xml"))
            if content_format == "odt":
                elements = root.findall(".//{*}h") + root.findall(".//{*}p")
                for index, element in enumerate(elements, start=1):
                    text = _xml_text(element)
                    if text:
                        segments.append({"segment_kind": "paragraph", "text": text, "locator": f"block={index}", "heading": None})
            else:
                for row_number, row in enumerate(root.findall(".//{*}table-row"), start=1):
                    cells = [_xml_text(cell) for cell in row.findall("./{*}table-cell")]
                    text = _normalise_space(" | ".join(value for value in cells if value))
                    if text:
                        segments.append({"segment_kind": "unknown", "text": text, "locator": f"row={row_number}", "heading": None})
    return segments


def _extract_csv(body: bytes) -> list[dict[str, Any]]:
    text = _decode_text(body)
    dialect = csv.excel_tab if "\t" in text[:4096] and "," not in text[:4096] else csv.excel
    output = []
    for row_number, row in enumerate(csv.reader(io.StringIO(text), dialect=dialect), start=1):
        value = _normalise_space(" | ".join(row))
        if value:
            output.append({"segment_kind": "unknown", "text": value, "locator": f"row={row_number}", "heading": None})
    return output


def _extract_source_text(body: bytes, content_format: str) -> tuple[str, str, list[dict[str, Any]]]:
    try:
        if content_format == "html":
            segments = _extract_html(body)
        elif content_format == "pdf":
            segments = _extract_pdf(body)
            if not segments:
                return "needs_ocr", "PDF contained no readable text; OCR was not attempted", []
        elif content_format in {"docx", "pptx", "odt", "ods"}:
            segments = _extract_office_zip(body, content_format)
        elif content_format == "csv":
            segments = _extract_csv(body)
        elif content_format == "text":
            segments = [
                {"segment_kind": "paragraph", "text": value, "locator": f"line={index}", "heading": None}
                for index, line in enumerate(_decode_text(body).splitlines(), start=1)
                if (value := _normalise_space(line))
            ]
        elif content_format in {"png", "image"}:
            return "needs_ocr", "Image content requires OCR; OCR was not attempted", []
        else:
            return "unsupported_format", f"No extractor for detected format {content_format}", []
        if not segments:
            return "extraction_failed", "Extractor returned no non-empty text blocks", []
        return "success", "source text extracted without semantic cleaning", segments
    except Exception as exc:  # per-object failures must not stop the batch
        return "extraction_failed", f"{type(exc).__name__}: {exc}", []


def _acquisition_paths(config: dict[str, Any]) -> tuple[Path, Path, Path]:
    root = resolve_path(config["paths"]["work_package"])
    database = resolve_path(config["paths"]["database"])
    manifest = resolve_path(config["paths"]["frozen_manifest"])
    return root, database, manifest


def _initialise_acquisition_workspace(config: dict[str, Any]) -> dict[str, Any]:
    root, database, manifest = _acquisition_paths(config)
    root.mkdir(parents=True, exist_ok=True)
    source_database = resolve_path(config["paths"]["source_database"])
    source_sha = sha256_file(source_database)
    expected_sha = str(config["source_database_sha256"])
    if source_sha != expected_sha:
        raise RuntimeError(
            f"05 source database hash changed: expected {expected_sha}, observed {source_sha}"
        )
    if sha256_file(manifest) != str(config["frozen_manifest_sha256"]):
        raise RuntimeError("Frozen enumeration manifest hash changed")
    if not database.exists():
        database.parent.mkdir(parents=True, exist_ok=True)
        temporary = database.with_suffix(database.suffix + ".tmp")
        shutil.copy2(source_database, temporary)
        os.replace(temporary, database)
    authorization = config["authorization"]
    recorded_at = datetime.fromisoformat(str(authorization["recorded_at"]).replace("Z", "+00:00"))
    authorization_id = stable_id(
        "auth", str(authorization["recorded_at"]), str(authorization["authorization_text"])
    )
    batch_id = str(config["acquisition_batch_id"])
    with duckdb.connect(str(database)) as connection:
        connection.execute(ACQUISITION_AUDIT_SQL)
        connection.execute(
            """
            UPDATE acquisition_runs
            SET status = 'interrupted_abnormally',
                finished_at = COALESCE(finished_at, current_timestamp),
                result_json = CASE
                    WHEN result_json = '{}' THEN '{"reason":"process ended before run finalization"}'
                    ELSE result_json
                END
            WHERE status = 'running'
            """
        )
        source_row = connection.execute(
            "SELECT source_id FROM collection_batches WHERE batch_id = ?",
            [config["frozen_batch_id"]],
        ).fetchone()
        if source_row is None:
            raise RuntimeError("Frozen enumeration batch is absent from the 05 source database")
        connection.execute(
            """
            INSERT INTO collection_batches (
                batch_id, source_id, accessed_at, query_url, query_conditions_json,
                window_start, window_end, date_filter_field, pagination_json,
                reported_total, returned_count, completeness_status, completeness_reason,
                search_snapshot_path, search_snapshot_sha256, metadata_snapshot_path,
                metadata_snapshot_sha256, research_sample
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (batch_id) DO NOTHING
            """,
            [
                batch_id,
                source_row[0],
                recorded_at,
                str(config["paths"]["frozen_manifest"]),
                canonical_json({
                    "mode": "content_acquisition_from_frozen_manifest",
                    "frozen_batch_id": config["frozen_batch_id"],
                    "content_objects": int(config["expected_counts"]["content_objects"]),
                }),
                config["scope"]["start_date"],
                config["scope"]["end_date"],
                "frozen_manifest_no_reenumeration",
                canonical_json({"resume": "per-object atomic checkpoint", "workers": config["http"]["workers"]}),
                int(config["expected_counts"]["content_objects"]),
                0,
                "acquisition_running",
                "Current accessible versions are being attempted from the frozen 3,025-object list.",
                str(config["paths"]["frozen_manifest"]),
                str(config["frozen_manifest_sha256"]),
                str(config["paths"]["frozen_manifest"]),
                str(config["frozen_manifest_sha256"]),
                True,
            ],
        )
        connection.execute(
            """
            INSERT INTO acquisition_authorizations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (authorization_id) DO NOTHING
            """,
            [
                authorization_id,
                recorded_at,
                authorization["actor"],
                authorization["authorization_text"],
                authorization["supervisor_statement_basis"],
                authorization["supervisor_statement_text"],
                authorization["project_authorization_status"],
                authorization["institutional_ethics_status"],
                authorization["allowed_use"],
                authorization["redistribution_status"],
                canonical_json(authorization["scope"]),
                authorization["source_thread_id"],
            ],
        )
        extraction_run_id = stable_id("ext", batch_id, EXTRACTOR_VERSION)
        connection.execute(
            """
            INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
            ON CONFLICT (extraction_run_id) DO NOTHING
            """,
            [
                extraction_run_id,
                batch_id,
                EXTRACTOR_VERSION,
                recorded_at,
                recorded_at,
                "running",
                "Source extraction only; no semantic cleaning, vectorisation or analysis.",
            ],
        )
    write_json_atomic(
        root / "authorization_record.json",
        {
            "authorization_id": authorization_id,
            **{
                key: value.isoformat() if isinstance(value, datetime) else value
                for key, value in authorization.items()
            },
            "recording_note": (
                "Project collection authorization and institutional ethics status are separate. "
                "The supervisor statement is Dai's report and is not recorded as UQ HREC approval or exemption."
            ),
        },
    )
    return {
        "authorization_id": authorization_id,
        "extraction_run_id": extraction_run_id,
        "database": database,
        "root": root,
        "manifest": manifest,
    }


def _load_acquisition_objects(database: Path) -> list[dict[str, Any]]:
    with duckdb.connect(str(database), read_only=True) as connection:
        cursor = connection.execute(
            """
            SELECT content_object_id, object_kind, external_content_id, canonical_url,
                   declared_mime_type, declared_file_size, declared_page_count, title
            FROM content_objects
            ORDER BY CASE WHEN object_kind = 'webpage' THEN 0 ELSE 1 END,
                     canonical_url, content_object_id
            """
        )
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _select_smoke_objects(database: Path, publication_limit: int) -> tuple[list[str], list[str]]:
    with duckdb.connect(str(database), read_only=True) as connection:
        documents = connection.execute(
            """
            SELECT d.document_id
            FROM documents d
            JOIN document_content_objects x USING (document_id)
            JOIN content_objects c USING (content_object_id)
            GROUP BY d.document_id, d.publication_date
            HAVING COUNT(*) FILTER (WHERE x.relationship_type = 'attachment') = 1
               AND COUNT(*) FILTER (
                   WHERE x.relationship_type = 'attachment'
                     AND lower(COALESCE(c.declared_mime_type, '')) LIKE '%pdf%'
                     AND COALESCE(c.declared_file_size, 0) BETWEEN 1000 AND 10000000
               ) = 1
            ORDER BY d.publication_date DESC, d.document_id
            LIMIT ?
            """,
            [publication_limit],
        ).fetchall()
        document_ids = [row[0] for row in documents]
        if not document_ids:
            raise RuntimeError("No frozen publication with a webpage and manageable PDF was found")
        placeholders = ",".join("?" for _ in document_ids)
        object_ids = [
            row[0]
            for row in connection.execute(
                f"""
                SELECT DISTINCT x.content_object_id
                FROM document_content_objects x
                JOIN content_objects c USING (content_object_id)
                WHERE x.document_id IN ({placeholders})
                ORDER BY x.content_object_id
                """,
                document_ids,
            ).fetchall()
        ]
    return document_ids, object_ids


def _checkpoint_payload_is_valid(payload: dict[str, Any]) -> bool:
    if payload.get("download_status") not in {"success", "error_page"} or not payload.get(
        "raw_path"
    ):
        return False
    raw_path = resolve_path(str(payload["raw_path"]))
    return raw_path.is_file() and sha256_file(raw_path) == payload.get("content_sha256")


def _acquire_one_object(
    content_object: dict[str, Any],
    config: dict[str, Any],
    client: HttpClient,
    checkpoint_root: Path,
    raw_root: Path,
    *,
    force_network: bool = False,
    request_url_override: str | None = None,
    retry_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    object_id = str(content_object["content_object_id"])
    checkpoint_path = checkpoint_root / f"{object_id}.json"
    body: bytes | None = None
    checkpoint: dict[str, Any] | None = None
    if checkpoint_path.exists() and not force_network:
        try:
            loaded = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and _checkpoint_payload_is_valid(loaded):
                checkpoint = loaded
                body = resolve_path(str(loaded["raw_path"])).read_bytes()
        except (OSError, json.JSONDecodeError):
            checkpoint = None
    if checkpoint is not None and body is not None:
        saved_result = HttpResult(
            request_url=str(checkpoint["request_url"]),
            final_url=str(checkpoint["final_url"]),
            retrieved_at=str(checkpoint["retrieved_at"]),
            status_code=int(checkpoint["status_code"]),
            mime_type=str(checkpoint.get("actual_mime_type") or ""),
            body=body,
            headers={},
            attempts=int(checkpoint.get("attempt_count") or 0),
        )
        download_status, failure_reason = _validate_acquisition_download(
            saved_result,
            str(content_object["object_kind"]),
            str(content_object.get("declared_mime_type") or ""),
            str(checkpoint["actual_format"]),
        )
        checkpoint["download_status"] = download_status
        checkpoint["failure_reason"] = failure_reason
        checkpoint["validation_status"] = (
            "error_page"
            if download_status == "error_page"
            else _validation_status(
                str(content_object.get("declared_mime_type") or ""),
                str(checkpoint["actual_format"]),
            )
        )
        if download_status not in {"success", "error_page"}:
            checkpoint.pop("content_version_id", None)
            checkpoint["byte_size"] = 0
            checkpoint["content_sha256"] = ""
            checkpoint["raw_path"] = ""
            body = None
            write_json_atomic(checkpoint_path, checkpoint)
    if checkpoint is None:
        canonical_url = str(content_object["canonical_url"])
        request_url = request_url_override or urllib.parse.urljoin(
            str(config.get("source_base_url", "https://www.gov.uk")), canonical_url
        )
        try:
            result = client.get(request_url)
        except Exception as exc:  # malformed/unsupported URLs are per-object failures
            result = HttpResult(
                request_url=request_url,
                final_url=request_url,
                retrieved_at=utc_now(),
                status_code=0,
                mime_type="",
                body=b"",
                headers={},
                attempts=0,
                error=f"{type(exc).__name__}: {exc}",
            )
        actual_format = _detect_content_format(
            result.body,
            result.mime_type,
            str(content_object.get("declared_mime_type") or ""),
            result.final_url,
        )
        download_status, failure_reason = _validate_acquisition_download(
            result,
            str(content_object["object_kind"]),
            str(content_object.get("declared_mime_type") or ""),
            actual_format,
        )
        validation_status = (
            "error_page"
            if download_status == "error_page"
            else _validation_status(
                str(content_object.get("declared_mime_type") or ""), actual_format
            )
        )
        checkpoint = {
            "content_object_id": object_id,
            "object_kind": content_object["object_kind"],
            "request_url": request_url,
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "status_code": result.status_code,
            "actual_mime_type": result.mime_type,
            "declared_mime_type": content_object.get("declared_mime_type") or "",
            "actual_format": actual_format,
            "attempt_count": result.attempts,
            "redirected": result.final_url != request_url,
            "download_status": download_status,
            "validation_status": validation_status,
            "failure_reason": failure_reason,
            "byte_size": 0,
            "content_sha256": "",
            "raw_path": "",
            "checkpoint_path": relative_path(checkpoint_path),
            "canonical_url": canonical_url,
            "retry_metadata": retry_metadata or {},
        }
        if download_status in {"success", "error_page"}:
            content_sha = sha256_bytes(result.body)
            version_id = stable_id("cntv", object_id, content_sha)
            extension = _format_extension(actual_format, result.final_url)
            raw_path = raw_root / object_id / f"{version_id}{extension}"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            if not raw_path.exists() or sha256_file(raw_path) != content_sha:
                temporary = raw_path.with_suffix(raw_path.suffix + ".tmp")
                temporary.write_bytes(result.body)
                os.replace(temporary, raw_path)
            if sha256_file(raw_path) != content_sha:
                raise RuntimeError(f"Atomic storage hash mismatch for {object_id}")
            checkpoint.update(
                {
                    "content_version_id": version_id,
                    "byte_size": len(result.body),
                    "content_sha256": content_sha,
                    "raw_path": relative_path(raw_path),
                }
            )
            body = result.body
        write_json_atomic(checkpoint_path, checkpoint)
    if checkpoint["download_status"] == "error_page":
        extraction_status = "error_page"
        extraction_reason = str(checkpoint.get("failure_reason") or "HTTP error page")
        segments = []
    elif checkpoint["download_status"] == "success" and body is not None:
        extraction_status, extraction_reason, segments = _extract_source_text(
            body, str(checkpoint["actual_format"])
        )
    else:
        extraction_status = "not_attempted_download_failed"
        extraction_reason = str(checkpoint.get("failure_reason") or "download failed")
        segments = []
    return {
        **checkpoint,
        "extraction_status": extraction_status,
        "extraction_reason": extraction_reason,
        "segments": segments,
    }


def _persist_acquisition_result(
    connection: duckdb.DuckDBPyConnection,
    config: dict[str, Any],
    run_id: str,
    extraction_run_id: str,
    result: dict[str, Any],
) -> None:
    batch_id = str(config["acquisition_batch_id"])
    object_id = str(result["content_object_id"])
    # The schema keeps one current fetch row per batch/object. Immutable attempt
    # and address history is recorded in acquisition_events, while any saved byte
    # versions remain immutable in content_versions.
    fetch_id = stable_id("fet", batch_id, object_id)
    retrieved_at = datetime.fromisoformat(str(result["retrieved_at"]).replace("Z", "+00:00"))
    content_version_id = result.get("content_version_id") or None
    # DuckDB's current foreign-key implementation cannot replace a referenced
    # primary-key row inside the same transaction.  Remove only the replaceable
    # latest-state edge and its replaceable current fetch. Immutable byte versions
    # and acquisition-event history remain in place.
    connection.execute(
        "DELETE FROM acquisition_object_statuses WHERE batch_id = ? AND content_object_id = ?",
        [batch_id, object_id],
    )
    connection.execute("DELETE FROM content_fetches WHERE fetch_id = ?", [fetch_id])
    connection.execute("BEGIN TRANSACTION")
    try:
        if content_version_id:
            connection.execute(
                """
                INSERT INTO content_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (content_object_id, content_sha256) DO NOTHING
                """,
                [
                    content_version_id,
                    object_id,
                    result["content_sha256"],
                    result["final_url"],
                    retrieved_at,
                    int(result["status_code"]),
                    result["actual_mime_type"] or "application/octet-stream",
                    int(result["byte_size"]),
                    result["raw_path"],
                    result["content_sha256"],
                    fetch_id,
                    "saved" if result["download_status"] == "error_page" else "verified",
                ],
            )
        connection.execute(
            """
            INSERT INTO content_fetches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                fetch_id,
                batch_id,
                object_id,
                content_version_id,
                result["request_url"],
                result.get("final_url") or None,
                retrieved_at,
                int(result["status_code"]) if result.get("status_code") else None,
                result.get("actual_mime_type") or None,
                result.get("content_sha256") or None,
                result.get("raw_path") or None,
                ACQUISITION_SCRIPT_VERSION,
                result["download_status"],
                result["extraction_status"],
                "internal_only_not_cleared_for_redistribution",
                result.get("failure_reason") or "",
            ],
        )
        if content_version_id:
            connection.execute(
                "DELETE FROM text_segments WHERE content_version_id = ? AND extraction_run_id = ?",
                [content_version_id, extraction_run_id],
            )
            segment_rows = []
            for index, segment in enumerate(result["segments"]):
                text = str(segment["text"])
                text_sha = sha256_bytes(text.encode("utf-8"))
                segment_id = stable_id(
                    "seg", content_version_id, extraction_run_id, str(index), text_sha
                )
                segment_rows.append(
                    {
                        "segment_id": segment_id,
                        "content_version_id": content_version_id,
                        "extraction_run_id": extraction_run_id,
                        "parent_segment_id": None,
                        "representation_kind": "source_extracted",
                        "segment_kind": segment["segment_kind"],
                        "segment_order": index,
                        "heading": segment.get("heading"),
                        "segment_text": text,
                        "locator": segment["locator"],
                        "start_char": None,
                        "end_char": None,
                        "text_sha256": text_sha,
                        "permission_status": (
                            "project_authorized_internal_use_institutional_ethics_not_asserted"
                        ),
                        "research_sample": True,
                        "created_at": retrieved_at,
                    }
                )
            if segment_rows:
                import pyarrow as pa

                segment_batch = pa.Table.from_pylist(segment_rows)
                connection.register("_acquisition_segment_batch", segment_batch)
                try:
                    connection.execute(
                        """
                        INSERT INTO text_segments (
                            segment_id, content_version_id, extraction_run_id,
                            parent_segment_id, representation_kind, segment_kind,
                            segment_order, heading, segment_text, locator, start_char,
                            end_char, text_sha256, permission_status, research_sample,
                            created_at
                        )
                        SELECT segment_id, content_version_id, extraction_run_id,
                               CAST(parent_segment_id AS VARCHAR), representation_kind,
                               segment_kind, segment_order, heading, segment_text, locator,
                               CAST(start_char AS INTEGER), CAST(end_char AS INTEGER),
                               text_sha256, permission_status, research_sample, created_at
                        FROM _acquisition_segment_batch
                        """
                    )
                finally:
                    connection.unregister("_acquisition_segment_batch")
        connection.execute(
            """
            INSERT INTO acquisition_object_statuses VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            ) ON CONFLICT (batch_id, content_object_id) DO UPDATE SET
                fetch_id = excluded.fetch_id,
                content_version_id = excluded.content_version_id,
                actual_mime_type = excluded.actual_mime_type,
                actual_format = excluded.actual_format,
                attempt_count = excluded.attempt_count,
                redirected = excluded.redirected,
                download_status = excluded.download_status,
                validation_status = excluded.validation_status,
                extraction_status = excluded.extraction_status,
                extraction_reason = excluded.extraction_reason,
                byte_size = excluded.byte_size,
                content_sha256 = excluded.content_sha256,
                raw_path = excluded.raw_path,
                segment_count = excluded.segment_count,
                checkpoint_path = excluded.checkpoint_path,
                updated_at = excluded.updated_at
            """,
            [
                batch_id,
                object_id,
                fetch_id,
                content_version_id,
                result["object_kind"],
                result.get("declared_mime_type") or None,
                result.get("actual_mime_type") or None,
                result.get("actual_format") or None,
                int(result.get("attempt_count") or 0),
                bool(result.get("redirected")),
                result["download_status"],
                result["validation_status"],
                result["extraction_status"],
                result["extraction_reason"],
                int(result.get("byte_size") or 0) or None,
                result.get("content_sha256") or None,
                result.get("raw_path") or None,
                len(result["segments"]),
                result["checkpoint_path"],
                retrieved_at,
            ],
        )
        connection.execute(
            "UPDATE content_objects SET acquisition_status = ? WHERE content_object_id = ?",
            [
                result["extraction_status"]
                if result["download_status"] == "success"
                else result["download_status"],
                object_id,
            ],
        )
        event_id = stable_id("evt", run_id, object_id, str(result["retrieved_at"]))
        connection.execute(
            """
            INSERT INTO acquisition_events VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id) DO NOTHING
            """,
            [
                event_id,
                run_id,
                object_id,
                retrieved_at,
                "download_and_extract",
                result["download_status"],
                canonical_json(
                    {
                        "request_url": result["request_url"],
                        "final_url": result.get("final_url"),
                        "status_code": result.get("status_code"),
                        "attempt_count": result.get("attempt_count"),
                        "validation_status": result["validation_status"],
                        "extraction_status": result["extraction_status"],
                        "segment_count": len(result["segments"]),
                        "canonical_url": result.get("canonical_url"),
                        "retry_metadata": result.get("retry_metadata") or {},
                    }
                ),
            ],
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def _phase_counts(connection: duckdb.DuckDBPyConnection, batch_id: str) -> dict[str, int]:
    row = connection.execute(
        """
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE download_status = 'success'),
               COUNT(*) FILTER (WHERE extraction_status = 'success'),
               COUNT(*) FILTER (WHERE download_status <> 'success'),
               COALESCE(SUM(segment_count), 0),
               COUNT(*) FILTER (WHERE extraction_status = 'needs_ocr'),
               COUNT(*) FILTER (WHERE extraction_status = 'unsupported_format')
        FROM acquisition_object_statuses WHERE batch_id = ?
        """,
        [batch_id],
    ).fetchone()
    keys = ["attempted", "downloaded", "extracted", "failed", "segments", "needs_ocr", "unsupported"]
    return dict(zip(keys, (int(value) for value in row), strict=True))


def _run_acquisition_phase(
    config: dict[str, Any],
    context: dict[str, Any],
    objects: list[dict[str, Any]],
    phase: str,
    *,
    retry_all_selected: bool = False,
    force_network: bool = False,
    url_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    database = context["database"]
    root = context["root"]
    batch_id = str(config["acquisition_batch_id"])
    started = utc_now()
    run_id = stable_id("run", batch_id, phase, started)
    command_line = f"{phase} --config {config['_config_path']}"
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            INSERT INTO acquisition_runs VALUES (
                ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, 'running', 0, 0, 0, 0, '{}'
            )
            """,
            [
                run_id,
                batch_id,
                context["authorization_id"],
                datetime.fromisoformat(started.replace("Z", "+00:00")),
                phase,
                ACQUISITION_SCRIPT_VERSION,
                command_line,
                relative_path(context["manifest"]),
                sha256_file(context["manifest"]),
                relative_path(database),
            ],
        )
        already_final = {
            row[0]
            for row in connection.execute(
                """
                SELECT content_object_id FROM acquisition_object_statuses
                WHERE batch_id = ? AND (
                    (download_status = 'success'
                     AND extraction_status IN ('success','needs_ocr','unsupported_format'))
                    OR (download_status = 'error_page' AND extraction_status = 'error_page')
                )
                """,
                [batch_id],
            ).fetchall()
        }
    pending_objects = (
        objects
        if retry_all_selected
        else [
            item for item in objects if str(item["content_object_id"]) not in already_final
        ]
    )
    client = HttpClient(config["http"])
    checkpoint_root = root / "checkpoints"
    raw_root = root / "raw" / "content"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    completed = 0
    try:
        with duckdb.connect(str(database)) as connection:
            with ThreadPoolExecutor(max_workers=int(config["http"]["workers"])) as executor:
                futures = {
                    executor.submit(
                        _acquire_one_object,
                        item,
                        config,
                        client,
                        checkpoint_root,
                        raw_root,
                        force_network=force_network,
                        request_url_override=(url_overrides or {})
                        .get(str(item["content_object_id"]), {})
                        .get("new_url"),
                        retry_metadata=(url_overrides or {}).get(
                            str(item["content_object_id"]), {}
                        ),
                    ): item
                    for item in pending_objects
                }
                for future in as_completed(futures):
                    result = future.result()
                    _persist_acquisition_result(
                        connection,
                        config,
                        run_id,
                        context["extraction_run_id"],
                        result,
                    )
                    completed += 1
                    result_for_checkpoint = {key: value for key, value in result.items() if key != "segments"}
                    result_for_checkpoint["segment_count"] = len(result["segments"])
                    result_for_checkpoint["database_committed"] = True
                    write_json_atomic(resolve_path(result["checkpoint_path"]), result_for_checkpoint)
                    if completed == 1 or completed % int(config["progress_every"]) == 0 or completed == len(pending_objects):
                        counts = _phase_counts(connection, batch_id)
                        print(
                            f"[{phase}] attempted={counts['attempted']}/{config['expected_counts']['content_objects']} "
                            f"downloaded={counts['downloaded']} extracted={counts['extracted']} "
                            f"failed={counts['failed']} segments={counts['segments']} "
                            f"needs_ocr={counts['needs_ocr']} unsupported={counts['unsupported']}",
                            flush=True,
                        )
            counts = _phase_counts(connection, batch_id)
            finished = datetime.now(UTC)
            connection.execute(
                """
                UPDATE acquisition_runs SET finished_at = ?, status = 'completed',
                    attempted_count = ?, successful_download_count = ?,
                    successful_extraction_count = ?, failure_count = ?, result_json = ?
                WHERE run_id = ?
                """,
                [
                    finished,
                    completed,
                    counts["downloaded"],
                    counts["extracted"],
                    counts["failed"],
                    canonical_json(counts),
                    run_id,
                ],
            )
        return counts
    except BaseException as exc:
        with duckdb.connect(str(database)) as connection:
            connection.execute(
                "UPDATE acquisition_runs SET finished_at=?, status=?, result_json=? WHERE run_id=?",
                [datetime.now(UTC), "interrupted", canonical_json({"error": f"{type(exc).__name__}: {exc}", "completed": completed}), run_id],
            )
        raise


def _smoke_passed(database: Path, batch_id: str, object_ids: list[str]) -> dict[str, Any]:
    placeholders = ",".join("?" for _ in object_ids)
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            f"""
            SELECT object_kind, actual_format, download_status, extraction_status,
                   raw_path, content_sha256, segment_count
            FROM acquisition_object_statuses
            WHERE batch_id = ? AND content_object_id IN ({placeholders})
            """,
            [batch_id, *object_ids],
        ).fetchall()
    hashes_ok = all(
        raw_path and resolve_path(raw_path).is_file() and sha256_file(resolve_path(raw_path)) == content_sha
        for _, _, download, _, raw_path, content_sha, _ in rows
        if download == "success"
    )
    passed = (
        len(rows) == len(object_ids)
        and all(row[2] == "success" for row in rows)
        and any(row[0] == "webpage" and row[3] == "success" and row[6] > 0 for row in rows)
        and any(row[1] == "pdf" and row[3] == "success" and row[6] > 0 for row in rows)
        and hashes_ok
    )
    return {"passed": passed, "target_count": len(object_ids), "observed_count": len(rows), "hashes_ok": hashes_ok}


def _refresh_acquisition_exports(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    root = context["root"]
    database = context["database"]
    batch_id = str(config["acquisition_batch_id"])
    export_dir = root / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    queries = {
        "fetch_manifest": """
            SELECT f.*, s.object_kind, s.declared_mime_type, s.actual_mime_type,
                   s.actual_format, s.attempt_count, s.redirected, s.validation_status,
                   s.extraction_status, s.extraction_reason, s.byte_size, s.segment_count,
                   s.checkpoint_path
            FROM content_fetches f JOIN acquisition_object_statuses s ON s.fetch_id=f.fetch_id
            WHERE f.batch_id = ? ORDER BY s.object_kind, f.content_object_id
        """,
        "failure_manifest": """
            SELECT * FROM acquisition_object_statuses
            WHERE batch_id = ?
              AND (download_status <> 'success' OR extraction_status <> 'success')
            ORDER BY download_status, content_object_id
        """,
        "extraction_status": """
            SELECT * FROM acquisition_object_statuses
            WHERE batch_id = ? ORDER BY extraction_status, content_object_id
        """,
        "content_versions": """
            SELECT v.* FROM content_versions v
            WHERE v.content_object_id IN (
                SELECT content_object_id FROM acquisition_object_statuses WHERE batch_id = ?
            ) ORDER BY v.content_object_id, v.retrieved_at
        """,
        "acquisition_runs": "SELECT * FROM acquisition_runs WHERE batch_id = ? ORDER BY started_at, run_id",
        "authorization": "SELECT * FROM acquisition_authorizations ORDER BY recorded_at, authorization_id",
    }
    outputs = {}
    with duckdb.connect(str(database), read_only=True) as connection:
        for name, query in queries.items():
            cursor = connection.execute(query, [batch_id] if "authorizations" not in query else [])
            columns = [item[0] for item in cursor.description]
            rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            path = export_dir / f"{name}.csv"
            write_csv_atomic(path, columns, rows)
            outputs[name] = {"rows": len(rows), "sha256": sha256_file(path)}
    return outputs


def _acquisition_verification(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    root = context["root"]
    database = context["database"]
    batch_id = str(config["acquisition_batch_id"])
    expected = int(config["expected_counts"]["content_objects"])
    with duckdb.connect(str(database), read_only=True) as connection:
        counts = _phase_counts(connection, batch_id)
        relation_count = _scalar_int(connection, "SELECT COUNT(*) FROM document_content_objects")
        shared_relations = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM (
                SELECT content_object_id FROM document_content_objects
                WHERE relationship_type='attachment'
                GROUP BY content_object_id HAVING COUNT(*) > 1
            )
            """,
        )
        fetch_version_missing = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM content_fetches f
            JOIN acquisition_object_statuses s USING (batch_id, content_object_id)
            WHERE f.batch_id=? AND f.collection_status='success'
              AND (f.content_version_id IS NULL OR s.content_version_id IS NULL)
            """,
            [batch_id],
        )
        status_version_missing = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM acquisition_object_statuses s
            LEFT JOIN content_versions v USING (content_version_id)
            WHERE s.batch_id=? AND s.content_version_id IS NOT NULL
              AND v.content_version_id IS NULL
            """,
            [batch_id],
        )
        orphan_acquisition_versions = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM content_versions v
            LEFT JOIN content_objects o USING (content_object_id)
            WHERE o.content_object_id IS NULL
            """,
        )
        orphan_segments = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM text_segments s
            LEFT JOIN content_versions v USING (content_version_id)
            LEFT JOIN extraction_runs e USING (extraction_run_id)
            WHERE v.content_version_id IS NULL OR e.extraction_run_id IS NULL
            """,
        )
        local_rows = connection.execute(
            """
            SELECT content_object_id, raw_path, content_sha256
            FROM acquisition_object_statuses
            WHERE batch_id=? AND content_version_id IS NOT NULL
            """,
            [batch_id],
        ).fetchall()
        current_status_count = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM acquisition_object_statuses WHERE batch_id=?",
            [batch_id],
        )
        distinct_current_status_objects = _scalar_int(
            connection,
            "SELECT COUNT(DISTINCT content_object_id) FROM acquisition_object_statuses WHERE batch_id=?",
            [batch_id],
        )
        missing_current_fetches = _scalar_int(
            connection,
            """
            SELECT COUNT(*) FROM acquisition_object_statuses s
            LEFT JOIN content_fetches f ON f.fetch_id=s.fetch_id
            WHERE s.batch_id=? AND f.fetch_id IS NULL
            """,
            [batch_id],
        )
        segment_count = _scalar_int(
            connection,
            "SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?",
            [context["extraction_run_id"]],
        )
        last_full_run = connection.execute(
            """
            SELECT attempted_count FROM acquisition_runs
            WHERE batch_id=? AND phase='full' AND status='completed'
            ORDER BY started_at DESC, run_id DESC LIMIT 1
            """,
            [batch_id],
        ).fetchone()
        last_resume_attempted = int(last_full_run[0]) if last_full_run else expected
    bad_files = [
        object_id
        for object_id, raw_path, content_sha in local_rows
        if not raw_path
        or not resolve_path(raw_path).is_file()
        or sha256_file(resolve_path(raw_path)) != content_sha
    ]
    original_hashes = {
        "04_database": sha256_file(resolve_path(config["paths"]["frozen_database"])),
        "04_manifest": sha256_file(context["manifest"]),
        "05_database": sha256_file(resolve_path(config["paths"]["source_database"])),
    }
    checks = {
        "all_frozen_objects_attempted": counts["attempted"] == expected,
        "one_current_status_per_object_in_acquisition_batch": (
            current_status_count == expected
            and distinct_current_status_objects == expected
        ),
        "current_statuses_link_fetch_history": missing_current_fetches == 0,
        "successful_files_exist_and_hash_match": not bad_files,
        "successful_fetches_link_content_versions": fetch_version_missing == 0,
        "saved_statuses_link_content_versions": status_version_missing == 0,
        "historical_content_versions_link_objects": orphan_acquisition_versions == 0,
        "segments_trace_to_version_and_extraction_run": orphan_segments == 0,
        "segment_count_matches_status_sum": segment_count == counts["segments"],
        "document_content_relations_preserved": relation_count == int(config["expected_counts"]["document_content_relations"]),
        "shared_attachment_relations_preserved": shared_relations == int(config["expected_counts"]["shared_attachments"]),
        "04_database_unchanged": original_hashes["04_database"] == config["frozen_database_sha256"],
        "04_manifest_unchanged": original_hashes["04_manifest"] == config["frozen_manifest_sha256"],
        "05_database_unchanged": original_hashes["05_database"] == config["source_database_sha256"],
        "resume_skipped_completed_objects": 0 < last_resume_attempted < expected,
    }
    verification = {
        "generated_at": utc_now(),
        "passed": all(checks.values()),
        "checks": checks,
        "counts": counts,
        "bad_file_content_object_ids": bad_files,
        "original_hashes": original_hashes,
        "last_resume_attempted_count": last_resume_attempted,
        "scope_note": "All attempted means the frozen 3,025-object list, not all UK government policy.",
    }
    write_json_atomic(root / "verification.json", verification)
    return verification


def _write_acquisition_reports(
    config: dict[str, Any], context: dict[str, Any], verification: dict[str, Any], exports: dict[str, Any]
) -> None:
    root = context["root"]
    counts = verification["counts"]
    with duckdb.connect(str(context["database"]), read_only=True) as connection:
        download_statuses = connection.execute(
            "SELECT download_status, COUNT(*) FROM acquisition_object_statuses WHERE batch_id=? GROUP BY 1 ORDER BY 1",
            [config["acquisition_batch_id"]],
        ).fetchall()
        extraction_statuses = connection.execute(
            "SELECT extraction_status, COUNT(*) FROM acquisition_object_statuses WHERE batch_id=? GROUP BY 1 ORDER BY 1",
            [config["acquisition_batch_id"]],
        ).fetchall()
        webpage_success = _scalar_int(connection, "SELECT COUNT(*) FROM acquisition_object_statuses WHERE batch_id=? AND object_kind='webpage' AND download_status='success'", [config["acquisition_batch_id"]])
        attachment_success = _scalar_int(connection, "SELECT COUNT(*) FROM acquisition_object_statuses WHERE batch_id=? AND object_kind='attachment' AND download_status='success'", [config["acquisition_batch_id"]])
    status_table = "\n".join(f"| `{name}` | {count} |" for name, count in download_statuses)
    extraction_table = "\n".join(f"| `{name}` | {count} |" for name, count in extraction_statuses)
    report = f"""# Government content acquisition quality report

Generated: {utc_now()}

## Scope and authorization boundary

This work package attempts the frozen 1,020 publication webpages and 2,005 unique
attachments (3,025 content objects). It does not re-enumerate sources and does not
claim coverage of all UK government policy.

Dai explicitly authorized internal project downloading, storage and source-text
extraction. The statement that the supervisor has given a green light is recorded
as Dai's report. No UQ HREC approval, exemption or not-applicable determination is
asserted. Raw full text is not cleared for public redistribution.

## Results

- Attempted: {counts['attempted']} / {config['expected_counts']['content_objects']}.
- Webpages downloaded: {webpage_success} / {config['expected_counts']['webpages']}.
- Attachments downloaded: {attachment_success} / {config['expected_counts']['attachments']}.
- Download failures: {counts['failed']}.
- Objects with successful text extraction: {counts['extracted']}.
- Source text segments/blocks: {counts['segments']}.
- `needs_ocr`: {counts['needs_ocr']}; `unsupported_format`: {counts['unsupported']}.
- Recovery audit attempted only {verification['last_resume_attempted_count']} non-final objects;
  completed objects were skipped from network retrieval.

### Download states

| State | Objects |
|---|---:|
{status_table}

### Extraction states

| State | Objects |
|---|---:|
{extraction_table}

## Verification

Overall: **{'PASS' if verification['passed'] else 'FAIL'}**.

""" + "\n".join(
        f"- {'PASS' if passed else 'FAIL'} — `{name}`" for name, passed in verification["checks"].items()
    ) + "\n\nPDF locators identify page and extracted text block; blocks are not asserted to be natural paragraphs.\n"
    (root / "data_quality_report.md").write_text(report, encoding="utf-8")
    summary = f"""# Government content acquisition summary

The frozen 3,025-object list was {'fully attempted' if counts['attempted'] == config['expected_counts']['content_objects'] else 'not fully attempted'}.
Successful downloads: {counts['downloaded']}; successful text extractions: {counts['extracted']}.
Failures and non-extractable records are itemised in `exports/failure_manifest.csv`
and `exports/extraction_status.csv`. Current-access versions only are claimed;
retrieval time is not used as publication time.

## Recovery command

```bash
.venv/bin/python -m fear_temperature.government_collection acquire \\
  --config work_packages/M1_source_access/06_government_content_acquisition/config.yaml \\
  --resume
```

The command validates 04/05 hashes, skips hash-verified successful objects, and
retries incomplete or failed objects. It does not re-enumerate the source.
"""
    (root / "README.md").write_text(summary, encoding="utf-8")
    write_json_atomic(
        root / "acquisition_summary.json",
        {
            "generated_at": utc_now(),
            "counts": counts,
            "verification_passed": verification["passed"],
            "exports": exports,
            "full_frozen_list_attempted": counts["attempted"] == config["expected_counts"]["content_objects"],
            "all_downloads_successful": counts["failed"] == 0,
        },
    )


def run_acquisition(config: dict[str, Any], *, resume: bool, smoke_only: bool) -> dict[str, Any]:
    del resume  # successful rows and hash-verified checkpoints are always resumed safely
    context = _initialise_acquisition_workspace(config)
    objects = _load_acquisition_objects(context["database"])
    expected = int(config["expected_counts"]["content_objects"])
    if len(objects) != expected:
        raise RuntimeError(f"Expected {expected} frozen content objects, found {len(objects)}")
    document_ids, smoke_ids = _select_smoke_objects(
        context["database"], int(config["smoke_publication_limit"])
    )
    object_by_id = {str(item["content_object_id"]): item for item in objects}
    smoke_objects = [object_by_id[object_id] for object_id in smoke_ids]
    write_json_atomic(
        context["root"] / "smoke_selection.json",
        {"document_ids": document_ids, "content_object_ids": smoke_ids, "selected_at": utc_now()},
    )
    _run_acquisition_phase(config, context, smoke_objects, "smoke")
    smoke = _smoke_passed(context["database"], config["acquisition_batch_id"], smoke_ids)
    write_json_atomic(context["root"] / "smoke_verification.json", smoke)
    if not smoke["passed"]:
        raise RuntimeError("Real webpage/PDF smoke acquisition did not pass; inspect smoke_verification.json")
    if not smoke_only:
        _run_acquisition_phase(config, context, objects, "full")
    exports = _refresh_acquisition_exports(config, context)
    verification = _acquisition_verification(config, context)
    with duckdb.connect(str(context["database"])) as connection:
        counts = verification["counts"]
        connection.execute(
            """
            UPDATE collection_batches SET returned_count=?, completeness_status=?, completeness_reason=?
            WHERE batch_id=?
            """,
            [
                counts["attempted"],
                "all_frozen_objects_attempted" if counts["attempted"] == expected else "partial",
                f"{counts['downloaded']} downloads succeeded; {counts['failed']} failed; success and attempt are reported separately.",
                config["acquisition_batch_id"],
            ],
        )
        connection.execute(
            """
            UPDATE extraction_runs SET finished_at=?, input_content_count=?, output_segment_count=?,
                status=?, status_reason=? WHERE extraction_run_id=?
            """,
            [
                datetime.now(UTC),
                counts["downloaded"],
                counts["segments"],
                "completed" if counts["attempted"] == expected else "partial",
                "Source extraction only; download and extraction outcomes remain distinct.",
                context["extraction_run_id"],
            ],
        )
    _write_acquisition_reports(config, context, verification, exports)
    if not smoke_only and not verification["passed"]:
        raise RuntimeError("Acquisition verification failed; inspect 06 verification.json")
    return {
        "smoke": smoke,
        "verification": verification,
        "exports": exports,
        "database": relative_path(context["database"]),
    }


def run_download_exception_retry(
    config: dict[str, Any], *, url_overrides_json: Path | None = None
) -> dict[str, Any]:
    """Retry only current download exceptions in the frozen acquisition batch.

    With no mapping, every current download exception is retried once at its
    canonical URL.  With a mapping, only the named still-failed objects are
    retried using the reviewed official replacement URL.  Successful objects
    and downloaded extraction exceptions are never selected.
    """

    context = _initialise_acquisition_workspace(config)
    batch_id = str(config["acquisition_batch_id"])
    all_objects = {
        str(item["content_object_id"]): item
        for item in _load_acquisition_objects(context["database"])
    }
    with duckdb.connect(str(context["database"]), read_only=True) as connection:
        before_rows = connection.execute(
            """
            SELECT o.content_object_id,
                   COALESCE(s.download_status, f.collection_status, 'missing_status'),
                   COALESCE(s.extraction_status, f.research_processing_status, 'missing_status'),
                   COALESCE(s.updated_at, f.retrieved_at),
                   COALESCE(s.fetch_id, f.fetch_id, '')
            FROM content_objects o
            LEFT JOIN acquisition_object_statuses s
              ON s.content_object_id=o.content_object_id AND s.batch_id=?
            LEFT JOIN content_fetches f
              ON f.content_object_id=o.content_object_id AND f.batch_id=?
            WHERE s.content_object_id IS NULL OR s.download_status <> 'success'
            ORDER BY o.content_object_id
            """,
            [batch_id, batch_id],
        ).fetchall()
    before = {
        str(row[0]): {
            "download_status": str(row[1]),
            "extraction_status": str(row[2]),
            "updated_at": row[3].isoformat() if row[3] is not None else None,
            "fetch_id": str(row[4]),
        }
        for row in before_rows
    }

    overrides: dict[str, dict[str, Any]] = {}
    phase = "download_exception_retry_original_url"
    if url_overrides_json is not None:
        loaded = json.loads(url_overrides_json.read_text(encoding="utf-8"))
        raw_items = loaded.get("overrides", loaded) if isinstance(loaded, dict) else loaded
        if isinstance(raw_items, list):
            raw_items = {
                str(item["content_object_id"]): item
                for item in raw_items
                if isinstance(item, dict) and item.get("content_object_id")
            }
        if not isinstance(raw_items, dict):
            raise ValueError("URL override file must contain an object mapping or list")
        for object_id, metadata in raw_items.items():
            if not isinstance(metadata, dict):
                raise ValueError(f"Override metadata for {object_id} must be an object")
            new_url = str(metadata.get("new_url") or "")
            parsed = urllib.parse.urlsplit(new_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Override for {object_id} is not an absolute HTTP(S) URL")
            if not metadata.get("discovery_evidence") or not metadata.get("identity_basis"):
                raise ValueError(
                    f"Override for {object_id} requires discovery_evidence and identity_basis"
                )
            if object_id not in before:
                raise ValueError(f"Override target {object_id} is not a current download exception")
            overrides[str(object_id)] = dict(metadata)
        phase = "download_exception_retry_official_replacement"

    selected_ids = sorted(overrides) if overrides else sorted(before)
    selected = [all_objects[object_id] for object_id in selected_ids]
    if not selected:
        return {
            "phase": phase,
            "selected_count": 0,
            "before_download_exceptions": before,
            "after_download_exceptions": before,
            "message": "No current download exceptions matched the requested retry.",
        }
    _run_acquisition_phase(
        config,
        context,
        selected,
        phase,
        retry_all_selected=True,
        force_network=True,
        url_overrides=overrides,
    )
    exports = _refresh_acquisition_exports(config, context)
    verification = _acquisition_verification(config, context)
    _write_acquisition_reports(config, context, verification, exports)
    with duckdb.connect(str(context["database"]), read_only=True) as connection:
        after_rows = connection.execute(
            """
            SELECT content_object_id, download_status, extraction_status,
                   updated_at, fetch_id
            FROM acquisition_object_statuses
            WHERE batch_id=? AND download_status <> 'success'
            ORDER BY content_object_id
            """,
            [batch_id],
        ).fetchall()
    after = {
        str(row[0]): {
            "download_status": str(row[1]),
            "extraction_status": str(row[2]),
            "updated_at": row[3].isoformat(),
            "fetch_id": str(row[4]),
        }
        for row in after_rows
    }
    return {
        "phase": phase,
        "selected_count": len(selected),
        "selected_content_object_ids": selected_ids,
        "before_download_exceptions": before,
        "after_download_exceptions": after,
        "recovered_content_object_ids": sorted(set(before) - set(after)),
        "verification_passed": verification["passed"],
        "database": relative_path(context["database"]),
    }


def run_acquisition_verification(config: dict[str, Any]) -> dict[str, Any]:
    context = _initialise_acquisition_workspace(config)
    exports = _refresh_acquisition_exports(config, context)
    verification = _acquisition_verification(config, context)
    _write_acquisition_reports(config, context, verification, exports)
    if not verification["passed"]:
        raise RuntimeError("Acquisition verification failed")
    return verification


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recoverable GOV.UK government corpus batch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in [
        "enum",
        "fetch",
        "verify",
        "ingest",
        "report",
        "migrate-core",
        "verify-core",
        "acquire",
        "retry-download-exceptions",
        "verify-acquisition",
    ]:
        child = subparsers.add_parser(command)
        child.add_argument("--config", type=Path, required=True)
        if command in {"enum", "fetch"}:
            child.add_argument("--resume", action="store_true")
            child.add_argument("--smoke", action="store_true")
            child.add_argument("--limit", type=int)
        if command == "acquire":
            child.add_argument("--resume", action="store_true")
            child.add_argument("--smoke-only", action="store_true")
        if command == "retry-download-exceptions":
            child.add_argument("--url-overrides-json", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.command == "enum":
        result = run_enumeration(
            config, resume=args.resume, smoke=args.smoke, limit=args.limit
        )
    elif args.command == "fetch":
        result = run_fetch(config, resume=args.resume, smoke=args.smoke, limit=args.limit)
    elif args.command == "verify":
        result = run_verification(config)
    elif args.command == "ingest":
        result = run_ingest(config)
    elif args.command == "migrate-core":
        result = run_core_migration(config)
    elif args.command == "verify-core":
        result = run_core_verification(config)
    elif args.command == "acquire":
        result = run_acquisition(
            config, resume=args.resume, smoke_only=args.smoke_only
        )
    elif args.command == "retry-download-exceptions":
        result = run_download_exception_retry(
            config, url_overrides_json=args.url_overrides_json
        )
    elif args.command == "verify-acquisition":
        result = run_acquisition_verification(config)
    else:
        result = run_report(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
