# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import email.utils
import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, date, datetime
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
                    "declared_mime_type": str(attachment.get("content_type") or ""),
                    "declared_file_size": attachment.get("file_size") or "",
                    "declared_page_count": attachment.get("number_of_pages") or "",
                    "relations": [],
                },
            )
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
                value.isoformat() if isinstance(value, (date, datetime)) else value
                for value in row
            ]
        )
    return {"columns": columns, "rows": rows}


def logical_fingerprint(connection: duckdb.DuckDBPyConnection) -> str:
    queries = {**PILOT_EXPORT_QUERIES, **NEW_EXPORT_QUERIES}
    payload = {name: _query_payload(connection, query) for name, query in queries.items()}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


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
        "content_objects": "网页与附件的独立内容对象、权利和伦理状态。",
        "document_content_objects": "文档到 landing page/附件的多对多父关系。",
        "content_fetches": "每个内容对象在本批次的成功、失败、跳过或 blocked 状态。",
        "extraction_runs": "文本提取运行及 blocked/failed/success 结果。",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recoverable GOV.UK government corpus batch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["enum", "fetch", "verify", "ingest", "report"]:
        child = subparsers.add_parser(command)
        child.add_argument("--config", type=Path, required=True)
        if command in {"enum", "fetch"}:
            child.add_argument("--resume", action="store_true")
            child.add_argument("--smoke", action="store_true")
            child.add_argument("--limit", type=int)
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
    else:
        result = run_report(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
