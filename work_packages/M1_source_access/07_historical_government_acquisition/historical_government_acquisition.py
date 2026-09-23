#!/usr/bin/env python3
"""Bounded historical UK government acquisition into the existing 06 DuckDB.

The script is intentionally checkpointed by source.  Enumeration manifests are
written before per-record acquisition, and re-running any phase reuses verified
raw files.  It does not perform semantic cleaning, vectorisation, or modelling.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import html
import json
import os
import re
import shutil
import sys
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urldefrag, urlencode, urljoin

import duckdb
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = (
    PROJECT_ROOT
    / "work_packages/M1_source_access/06_government_content_acquisition/"
    "fear_temperature_government_content.duckdb"
)
DB_PATH = Path(os.environ.get("HISTORICAL_ACQUISITION_DB_PATH", str(DEFAULT_DB_PATH))).resolve()
RAW_ROOT = WORK_ROOT / "raw"
MANIFEST_ROOT = WORK_ROOT / "manifests"
CHECKPOINT_ROOT = WORK_ROOT / "checkpoints"
REPORT_ROOT = Path(os.environ.get("HISTORICAL_ACQUISITION_REPORT_ROOT", str(WORK_ROOT / "reports"))).resolve()
BACKUP_ROOT = Path(os.environ.get("HISTORICAL_ACQUISITION_BACKUP_ROOT", str(WORK_ROOT / "recovery"))).resolve()

CUTOFF = date(2026, 9, 21)
POLICY_START = date(1988, 1, 1)
POLICY_END = date(2009, 12, 31)
MINISTER_START = date(1988, 1, 1)
HANSARD_GAP_START = date(2010, 5, 1)
HANSARD_GAP_END = date(2014, 9, 11)
PUBLICATIONS_ARCHIVE = "https://publications.parliament.uk"

SCRIPT_VERSION = "historical_government_acquisition_v1"
NORMALISATION_RULE_VERSION = "historical_government_records_v1"
EXTRACTOR_VERSION = "source_structure_extractor_v1"

USER_AGENT = "fear-of-temperature-research/1.0 (bounded academic collection; contact: local)"
NETWORK_WORKERS = 6
DETAIL_WORKERS = 8
# Worker count accelerates local cache validation only.  BoundedClient owns a
# single lock and paces all network starts at the aggregate interval below.
HANSARD_ANSWER_DETAIL_WORKERS = 8
MODERN_DETAIL_WORKERS = 8
MODERN_ACQUIRE_BLOCK_SIZE = 1000
REQUEST_TIMEOUT = 120
PARLIAMENT_INGEST_CHUNK_SIZE = 1000
# Policy attachments include two unusually large PDFs; one publication per
# transaction keeps extraction memory bounded without changing record identity.
POLICY_INGEST_CHUNK_SIZE = 1
# Early committed Historic Hansard segments used low, volume-local cumulative
# orders.  Parser repair legitimately expanded/reordered the later manifest, so
# resumed rows use a separate deterministic namespace rather than colliding
# with already committed low orders.
HISTORIC_REPAIRED_SEGMENT_ORDER_BASE = 1_000_000

GOVUK_POLICY_ORGS: dict[str, dict[str, str]] = {
    "department-of-trade-and-industry": {
        "name": "Department of Trade and Industry",
        "content_id": "fc490b59-de8a-4fa8-b5cc-4d9de65b329b",
        "status": "verified_govuk_content_api",
    },
    "department-of-energy-climate-change": {
        "name": "Department of Energy & Climate Change",
        "content_id": "d65d4203-01f5-4920-a3b1-f614bfd8e83e",
        "status": "verified_govuk_content_api",
    },
    "department-for-business-enterprise-and-regulatory-reform": {
        "name": "Department for Business, Enterprise and Regulatory Reform",
        "content_id": "a3773e86-b0b1-4c96-b1f4-5fff487cca39",
        "status": "verified_govuk_content_api",
    },
    "department-of-the-environment-transport-and-the-regions": {
        "name": "Department of the Environment, Transport and the Regions",
        "content_id": "971eb79c-9236-47ff-9af1-b32c835a88fc",
        "status": "verified_govuk_content_api",
    },
}

# Exact official department/group labels.  Broad DTI/BERR/BEIS mixtures are
# retained and explicitly flagged in the register/report instead of silently
# treated as a constant environmental remit.
HISTORIC_DEPARTMENT_LABELS = {
    "ENERGY",
    "ENVIRONMENT",
    "ENVIRONMENT, FOOD AND RURAL AFFAIRS",
    "ENVIRONMENT, TRANSPORT AND THE REGIONS",
    "TRADE AND INDUSTRY",
    "AGRICULTURE, FISHERIES AND FOOD",
    "BUSINESS, ENTERPRISE AND REGULATORY REFORM",
    "ENERGY AND CLIMATE CHANGE",
}
HANSARD_GAP_DEPARTMENT_LABELS = {
    "ENVIRONMENT, FOOD AND RURAL AFFAIRS",
    "ENERGY AND CLIMATE CHANGE",
}

MODERN_BODIES: dict[int, dict[str, Any]] = {
    13: {
        "name": "Department for Environment, Food and Rural Affairs",
        "start": date(2014, 9, 12),
        "end": CUTOFF,
        "scope_note": "environment/food/rural-affairs department",
    },
    63: {
        "name": "Department for Energy and Climate Change",
        "start": date(2014, 9, 12),
        "end": date(2016, 7, 13),
        "scope_note": "energy and climate department",
    },
    201: {
        "name": "Department for Business, Energy and Industrial Strategy",
        "start": date(2016, 7, 14),
        "end": date(2023, 2, 6),
        "scope_note": "broad business department; energy/climate remit mixed with non-energy business functions",
    },
    210: {
        "name": "COP26",
        "start": date(2020, 1, 1),
        "end": date(2022, 12, 31),
        "scope_note": "time-limited COP26 answering body",
    },
    215: {
        "name": "Department for Energy Security and Net Zero",
        "start": date(2023, 2, 7),
        "end": CUTOFF,
        "scope_note": "energy security and net-zero department",
    },
}

ARCHIVE_SERIES_PATH = (
    "The_Official_Report,_House_of_Commons_(6th_Series)_Vol_1_(March_1981)_to_2004"
)
ARCHIVE_BASE = "https://www.hansard-archive.parliament.uk/"
HISTORIC_API = "https://api.parliament.uk/historic-hansard"
HANSARD_API = "https://hansard-api.parliament.uk"
QUESTIONS_API = "https://questions-statements-api.parliament.uk/api"


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: object) -> str:
    joined = "\x1f".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(joined.encode('utf-8')).hexdigest()[:20]}"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str] | None = None) -> None:
    materialised = list(rows)
    if columns is None:
        columns = list(materialised[0]) if materialised else []
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialised)
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def normalise_label(value: str) -> str:
    return normalise_space(value).upper().strip(" .:")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def parse_official_date(text: str, attribute: str | None = None) -> date | None:
    cleaned = normalise_space(text)
    for candidate in (cleaned, attribute or ""):
        if not candidate:
            continue
        try:
            return date_parser.parse(candidate, dayfirst=True, fuzzy=True).date()
        except (ValueError, OverflowError):
            continue
    return None


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    mime: str
    body: bytes
    retrieved_at: str
    attempts: int
    error: str = ""


class RateLimitDeferred(RuntimeError):
    """Raised when an official service asks the collector to retry much later."""

    def __init__(
        self,
        retry_after_seconds: float,
        *,
        requested: bool = False,
        request_url: str = "",
        final_url: str = "",
        retrieved_at: str = "",
        mime: str = "",
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        self.requested = requested
        self.request_url = request_url
        self.final_url = final_url
        self.retrieved_at = retrieved_at
        self.mime = mime
        super().__init__(f"official_rate_limit_retry_after={retry_after_seconds:.0f}s")


class BoundedClient:
    def __init__(self, minimum_interval: float = 0.12, retries: int = 2) -> None:
        self.minimum_interval = minimum_interval
        self.retries = retries
        self._lock = threading.Lock()
        self._last = 0.0
        self._deferred_until = 0.0
        self._local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,*/*;q=0.8"})
            self._local.session = session
        return session

    def _pace(self) -> None:
        with self._lock:
            wait = self.minimum_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def get(self, url: str) -> FetchResult:
        last_error = ""
        for attempt in range(1, self.retries + 2):
            with self._lock:
                remaining = self._deferred_until - time.monotonic()
            if remaining > 0:
                raise RateLimitDeferred(remaining, requested=False, request_url=url)
            self._pace()
            try:
                response = self._session().get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                body = response.content
                mime = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    last_error = f"HTTP {response.status_code}"
                    if attempt <= self.retries:
                        if response.status_code == 429:
                            retry_after = response.headers.get("Retry-After", "")
                            try:
                                retry_seconds = float(retry_after)
                            except ValueError:
                                retry_seconds = 20.0 * attempt
                            previous_interval = self.minimum_interval
                            with self._lock:
                                self.minimum_interval = min(5.0, max(0.5, self.minimum_interval * 2.0))
                            with self._lock:
                                REPORT_ROOT.mkdir(parents=True, exist_ok=True)
                                with (REPORT_ROOT / "rate_limit_events.jsonl").open("a", encoding="utf-8") as handle:
                                    handle.write(
                                        canonical_json(
                                            {
                                                "observed_at": now_iso(),
                                                "url": url,
                                                "status": 429,
                                                "retry_after_seconds": retry_seconds,
                                                "previous_minimum_interval_seconds": previous_interval,
                                                "new_minimum_interval_seconds": self.minimum_interval,
                                            }
                                        )
                                        + "\n"
                                    )
                            if retry_seconds > 60:
                                with self._lock:
                                    self._deferred_until = max(
                                        self._deferred_until,
                                        time.monotonic() + retry_seconds,
                                    )
                                raise RateLimitDeferred(
                                    retry_seconds,
                                    requested=True,
                                    request_url=url,
                                    final_url=str(response.url),
                                    retrieved_at=now_iso(),
                                    mime=mime,
                                )
                            time.sleep(max(10.0, retry_seconds))
                        else:
                            time.sleep(min(8.0, 1.5 * (2 ** (attempt - 1))))
                        continue
                return FetchResult(
                    url=url,
                    final_url=str(response.url),
                    status=int(response.status_code),
                    mime=mime,
                    body=body,
                    retrieved_at=now_iso(),
                    attempts=attempt,
                    error="" if response.ok else f"HTTP {response.status_code}",
                )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt <= self.retries:
                    time.sleep(min(8.0, 1.5 * (2 ** (attempt - 1))))
                    continue
        return FetchResult(url, url, 0, "", b"", now_iso(), self.retries + 1, last_error)

    def get_json(self, url: str) -> tuple[FetchResult, dict[str, Any] | None]:
        result = self.get(url)
        if result.status != 200:
            return result, None
        try:
            value = json.loads(result.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            result.error = f"invalid_json: {exc}"
            return result, None
        return result, value if isinstance(value, dict) else None


def fetch_to_path(client: BoundedClient, url: str, path: Path, *, resume: bool = True) -> FetchResult:
    meta_path = path.with_suffix(path.suffix + ".fetch.json")
    if resume and path.exists() and meta_path.exists():
        meta = read_json(meta_path)
        if meta.get("url") == url and meta.get("sha256") == sha256_file(path):
            return FetchResult(
                url=url,
                final_url=str(meta.get("final_url") or url),
                status=int(meta.get("status") or 200),
                mime=str(meta.get("mime") or ""),
                body=path.read_bytes(),
                retrieved_at=str(meta.get("retrieved_at") or ""),
                attempts=int(meta.get("attempts") or 1),
                error=str(meta.get("error") or ""),
            )
    result = client.get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    if result.status == 200:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(result.body)
        os.replace(temporary, path)
    write_json(
        meta_path,
        {
            "url": url,
            "final_url": result.final_url,
            "status": result.status,
            "mime": result.mime,
            "retrieved_at": result.retrieved_at,
            "attempts": result.attempts,
            "error": result.error,
            "sha256": sha256_file(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
        },
    )
    return result


def _existing_identity_sets(database_path: Path | None = None) -> tuple[set[str], set[str], set[str]]:
    """Read identities from the requested database snapshot.

    A recovery snapshot may be used only for network-only enumeration while
    the authoritative database has its single writer.  Formal ingestion always
    rechecks the live 06 database before inserting any record.
    """
    with duckdb.connect(str(database_path or DB_PATH), read_only=True) as connection:
        rows = connection.execute("SELECT external_id, canonical_url, document_id FROM documents").fetchall()
    return ({str(row[0]) for row in rows}, {str(row[1]) for row in rows}, {str(row[2]) for row in rows})


def _enumeration_identity_snapshot() -> Path:
    snapshots = sorted(BACKUP_ROOT.glob("fear_temperature_government_content.before_historical.*.duckdb"))
    return snapshots[0] if snapshots else DB_PATH


def _govuk_search_url(slug: str, year: int, start: int, count: int) -> str:
    params = {
        "filter_organisations": slug,
        "filter_content_store_document_type": "policy_paper",
        "filter_first_published_at": f"from:{year}-01-01,to:{year}-12-31",
        "count": str(count),
        "start": str(start),
        "order": "public_timestamp",
    }
    return "https://www.gov.uk/api/search.json?" + urlencode(params)


def enumerate_policy(*, resume: bool = True) -> dict[str, Any]:
    """Freeze topic-independent GOV.UK historic policy targets by org/year."""
    client = BoundedClient(minimum_interval=0.15)
    existing_external, existing_urls, _ = _existing_identity_sets()
    rows: list[dict[str, Any]] = []
    partitions: list[dict[str, Any]] = []
    seen_external: set[str] = set()
    for slug, org in GOVUK_POLICY_ORGS.items():
        for year in range(POLICY_START.year, POLICY_END.year + 1):
            partition_id = f"policy_{slug}_{year}"
            started = now_iso()
            page_start = 0
            initial_total: int | None = None
            raw_paths: list[str] = []
            returned = 0
            error = ""
            while True:
                url = _govuk_search_url(slug, year, page_start, 100)
                path = RAW_ROOT / "govuk_search" / slug / str(year) / f"page_{page_start:06d}.json"
                result = fetch_to_path(client, url, path, resume=resume)
                if result.status != 200 or not path.exists():
                    error = result.error or f"HTTP {result.status}"
                    break
                payload = read_json(path)
                total = int(payload.get("total", -1))
                initial_total = total if initial_total is None else initial_total
                if total != initial_total:
                    error = f"total_drift:{initial_total}->{total}"
                    break
                results = payload.get("results") or []
                if not isinstance(results, list):
                    error = "results_not_list"
                    break
                raw_paths.append(rel(path))
                returned += len(results)
                for item in results:
                    link = str(item.get("link") or item.get("_id") or "")
                    if not link:
                        continue
                    content_url = "https://www.gov.uk/api/content" + link
                    metadata_path = RAW_ROOT / "govuk_content" / f"{sha256_bytes(link.encode())[:24]}.json"
                    meta_result = fetch_to_path(client, content_url, metadata_path, resume=resume)
                    if meta_result.status != 200 or not metadata_path.exists():
                        rows.append(
                            {
                                "partition_id": partition_id,
                                "organisation_slug": slug,
                                "organisation_name": org["name"],
                                "organisation_content_id": org["content_id"],
                                "year": year,
                                "external_id": "",
                                "canonical_url": urljoin("https://www.gov.uk", link),
                                "title": str(item.get("title") or ""),
                                "first_published_at": "",
                                "updated_at": "",
                                "document_type": str(item.get("content_store_document_type") or item.get("format") or ""),
                                "metadata_path": rel(metadata_path),
                                "metadata_sha256": "",
                                "retrieved_at": meta_result.retrieved_at,
                                "attachment_count": 0,
                                "identity_status": "metadata_fetch_failed",
                                "existing_document": False,
                                "failure_reason": meta_result.error,
                            }
                        )
                        continue
                    metadata = read_json(metadata_path)
                    external_id = str(metadata.get("content_id") or item.get("content_id") or "")
                    canonical_url = urljoin("https://www.gov.uk", str(metadata.get("base_path") or link))
                    first_published = str(metadata.get("first_published_at") or (metadata.get("details") or {}).get("first_public_at") or "")
                    org_ids = {
                        str(value.get("content_id") or "")
                        for value in (metadata.get("links") or {}).get("organisations") or []
                        if isinstance(value, dict)
                    }
                    identity_status = "verified"
                    failure_reason = ""
                    if org["content_id"] not in org_ids:
                        identity_status = "organisation_link_not_confirmed"
                        failure_reason = "Content API organisation links did not contain the enumerated organisation ID"
                    if not first_published.startswith(str(year)):
                        identity_status = "date_filter_mismatch"
                        failure_reason = f"first_published_at={first_published}"
                    duplicate = external_id in seen_external
                    if duplicate:
                        identity_status = "duplicate_across_partitions"
                    seen_external.add(external_id)
                    attachments = (metadata.get("details") or {}).get("attachments") or []
                    rows.append(
                        {
                            "partition_id": partition_id,
                            "organisation_slug": slug,
                            "organisation_name": org["name"],
                            "organisation_content_id": org["content_id"],
                            "year": year,
                            "external_id": external_id,
                            "canonical_url": canonical_url,
                            "title": str(metadata.get("title") or item.get("title") or ""),
                            "first_published_at": first_published,
                            "updated_at": str(metadata.get("public_updated_at") or metadata.get("updated_at") or ""),
                            "document_type": str(metadata.get("document_type") or ""),
                            "metadata_path": rel(metadata_path),
                            "metadata_sha256": sha256_file(metadata_path),
                            "retrieved_at": meta_result.retrieved_at,
                            "attachment_count": len(attachments),
                            "identity_status": identity_status,
                            "existing_document": external_id in existing_external or canonical_url in existing_urls,
                            "failure_reason": failure_reason,
                        }
                    )
                page_start += len(results)
                if page_start >= total or not results:
                    break
            partitions.append(
                {
                    "partition_id": partition_id,
                    "source": "govuk_search_api",
                    "genre": "policy_paper",
                    "department": org["name"],
                    "year": year,
                    "window_start": f"{year}-01-01",
                    "window_end": f"{year}-12-31",
                    "query_url": _govuk_search_url(slug, year, 0, 100),
                    "initial_total": initial_total if initial_total is not None else -1,
                    "returned_count": returned,
                    "unique_count": len({row["external_id"] for row in rows if row["partition_id"] == partition_id and row["external_id"]}),
                    "status": "complete_as_visible" if not error and returned == (initial_total or 0) else "partial",
                    "status_reason": error or "Search API pages and Content API identities saved",
                    "started_at": started,
                    "finished_at": now_iso(),
                    "raw_paths_json": json.dumps(raw_paths, ensure_ascii=False),
                }
            )
    columns = [
        "partition_id", "organisation_slug", "organisation_name", "organisation_content_id",
        "year", "external_id", "canonical_url", "title", "first_published_at", "updated_at",
        "document_type", "metadata_path", "metadata_sha256", "retrieved_at", "attachment_count",
        "identity_status", "existing_document", "failure_reason",
    ]
    write_csv(MANIFEST_ROOT / "policy_manifest.csv", rows, columns)
    write_csv(MANIFEST_ROOT / "policy_partitions.csv", partitions)
    summary = {
        "generated_at": now_iso(),
        "partitions": len(partitions),
        "complete_partitions": sum(row["status"] == "complete_as_visible" for row in partitions),
        "enumerated_records": sum(bool(row["external_id"]) for row in rows),
        "unique_records": len({row["external_id"] for row in rows if row["external_id"]}),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" or row["existing_document"] is True for row in rows),
        "net_new_records": sum(bool(row["external_id"]) and not row["existing_document"] for row in rows),
        "by_organisation": dict(Counter(row["organisation_name"] for row in rows if row["external_id"])),
        "identity_statuses": dict(Counter(row["identity_status"] for row in rows)),
    }
    write_json(MANIFEST_ROOT / "policy_enumeration_summary.json", summary)
    return summary


def acquire_policy(*, resume: bool = True) -> dict[str, Any]:
    """Download landing pages and attachments only for frozen net-new policy rows."""
    client = BoundedClient(minimum_interval=0.16)
    rows = read_csv(MANIFEST_ROOT / "policy_manifest.csv")
    targets: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row.get("external_id") or row.get("identity_status") not in {"verified", "duplicate_across_partitions"}:
            continue
        if str(row.get("existing_document", "")).lower() == "true":
            continue
        metadata = read_json(PROJECT_ROOT / row["metadata_path"])
        objects = [
            {
                "object_kind": "webpage",
                "url": row["canonical_url"],
                "title": row["title"],
                "declared_mime_type": "text/html",
                "parent_external_id": row["external_id"],
                "ordinal": 0,
            }
        ]
        for ordinal, attachment in enumerate((metadata.get("details") or {}).get("attachments") or [], start=1):
            if not isinstance(attachment, dict) or not attachment.get("url"):
                continue
            objects.append(
                {
                    "object_kind": "attachment",
                    "url": str(attachment["url"]),
                    "title": str(attachment.get("title") or attachment.get("filename") or ""),
                    "declared_mime_type": str(attachment.get("content_type") or ""),
                    "parent_external_id": row["external_id"],
                    "ordinal": ordinal,
                    "external_content_id": str(attachment.get("id") or ""),
                    "declared_file_size": attachment.get("file_size") or "",
                    "declared_page_count": attachment.get("number_of_pages") or "",
                }
            )
        for target in objects:
            object_id = stable_id("cnt", target["object_kind"], target["url"])
            target["content_object_id"] = object_id
            if object_id not in targets:
                target["relations_json"] = json.dumps(
                    [{"parent_external_id": target["parent_external_id"], "ordinal": target["ordinal"]}],
                    ensure_ascii=False,
                )
                targets[object_id] = target
            else:
                relations = json.loads(targets[object_id]["relations_json"])
                relation = {"parent_external_id": target["parent_external_id"], "ordinal": target["ordinal"]}
                if relation not in relations:
                    relations.append(relation)
                targets[object_id]["relations_json"] = json.dumps(relations, ensure_ascii=False)
    frozen_rows = sorted(targets.values(), key=lambda value: (value["parent_external_id"], value["ordinal"], value["url"]))
    write_csv(MANIFEST_ROOT / "policy_object_manifest.csv", frozen_rows)

    def fetch_one(target: dict[str, Any]) -> dict[str, Any]:
        suffix = Path(target["url"].split("?", 1)[0]).suffix.lower()
        if not suffix or len(suffix) > 8:
            suffix = ".html" if target["object_kind"] == "webpage" else ".bin"
        path = RAW_ROOT / "policy_content" / f"{target['content_object_id']}{suffix}"
        result = fetch_to_path(client, target["url"], path, resume=resume)
        error = result.error
        validation = "not_downloaded"
        if result.status == 200 and path.exists():
            body = path.read_bytes()
            validation = "valid_signature"
            if "pdf" in str(target.get("declared_mime_type", "")).lower() and not body.startswith(b"%PDF-"):
                error = "declared_pdf_signature_missing"
                validation = "error_page_or_wrong_format"
            elif (result.mime == "text/html" or target["object_kind"] == "webpage") and b"<html" not in body[:5000].lower():
                error = "html_signature_missing"
                validation = "wrong_format"
        return {
            **target,
            "request_url": target["url"],
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "status_code": result.status,
            "mime_type": result.mime,
            "attempt_count": result.attempts,
            "download_status": "success" if result.status == 200 and not error else "failed",
            "validation_status": validation,
            "failure_reason": error,
            "raw_path": rel(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
            "content_sha256": sha256_file(path) if path.exists() else "",
        }

    statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=NETWORK_WORKERS) as executor:
        futures = [executor.submit(fetch_one, target) for target in frozen_rows]
        for future in as_completed(futures):
            statuses.append(future.result())
    statuses.sort(key=lambda value: (value["parent_external_id"], int(value["ordinal"]), value["content_object_id"]))
    write_csv(MANIFEST_ROOT / "policy_acquisition_status.csv", statuses)
    summary = {
        "generated_at": now_iso(),
        "target_objects": len(statuses),
        "attempted": len(statuses),
        "downloaded": sum(row["download_status"] == "success" for row in statuses),
        "failed": sum(row["download_status"] != "success" for row in statuses),
        "webpages": sum(row["object_kind"] == "webpage" for row in statuses),
        "attachments": sum(row["object_kind"] == "attachment" for row in statuses),
    }
    write_json(MANIFEST_ROOT / "policy_acquisition_summary.json", summary)
    return summary


def _parse_volume_index(body: bytes) -> list[dict[str, Any]]:
    soup = BeautifulSoup(body, "html.parser")
    rows: list[dict[str, Any]] = []
    for tr in soup.select("tr.volume-info"):
        link_cell = tr.select_one("td.volume-link")
        start_cell = tr.select_one("td.start-date")
        end_cell = tr.select_one("td.end-date")
        success_cell = tr.select_one("td.percent-success")
        if not link_cell or not start_cell or not end_cell:
            continue
        link_text = link_cell.get_text(" ", strip=True)
        match = re.search(r"Volume\s+(\d+)", link_text)
        if not match:
            continue
        start = parse_official_date(start_cell.get_text(" ", strip=True))
        end = parse_official_date(end_cell.get_text(" ", strip=True))
        if not start or not end or end < MINISTER_START or start > date(2004, 12, 31):
            continue
        volume = int(match.group(1))
        part_match = re.search(r"Part\s+(\d+)", link_text, flags=re.IGNORECASE)
        part = int(part_match.group(1)) if part_match else 0
        zip_name = f"S6CV{volume:04d}P{part}.zip"
        series_path = quote(ARCHIVE_SERIES_PATH, safe="(),_")
        rows.append(
            {
                "volume": volume,
                "part": part,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "historic_api_status": normalise_space(success_cell.get_text(" ", strip=True)) if success_cell else "",
                "zip_name": zip_name,
                "download_url": f"{ARCHIVE_BASE}{series_path}/{zip_name}",
                "partition_years": ";".join(str(year) for year in range(max(1988, start.year), min(2004, end.year) + 1)),
            }
        )
    return rows


def enumerate_historic_volumes(*, resume: bool = True) -> dict[str, Any]:
    """Freeze official Commons Sixth Series volumes overlapping 1988–2004."""
    client = BoundedClient(minimum_interval=0.2)
    url = f"{HISTORIC_API}/volumes/6C/index.html"
    path = RAW_ROOT / "historic_hansard" / "volume_index_6C.html"
    result = fetch_to_path(client, url, path, resume=resume)
    if result.status != 200:
        raise RuntimeError(f"Historic Hansard volume index failed: {result.error}")
    rows = _parse_volume_index(path.read_bytes())
    write_csv(MANIFEST_ROOT / "historic_volume_manifest.csv", rows)
    summary = {
        "generated_at": now_iso(),
        "source": url,
        "first_volume": min((row["volume"] for row in rows), default=None),
        "last_volume": max((row["volume"] for row in rows), default=None),
        "target_volumes": len(rows),
        "window_start": min((row["start_date"] for row in rows), default=""),
        "window_end": max((row["end_date"] for row in rows), default=""),
        "note": "Volume manifest is frozen before bulk XML download; inner answer/statement targets are frozen after parsing the official bulk enumeration source.",
    }
    write_json(MANIFEST_ROOT / "historic_volume_summary.json", summary)
    return summary


def acquire_historic_volumes(*, resume: bool = True) -> dict[str, Any]:
    """Download each frozen official XML zip with bounded concurrency."""
    client = BoundedClient(minimum_interval=0.18)
    volumes = read_csv(MANIFEST_ROOT / "historic_volume_manifest.csv")

    def fetch_volume(row: dict[str, str]) -> dict[str, Any]:
        path = RAW_ROOT / "historic_hansard" / "volumes" / row["zip_name"]
        result = fetch_to_path(client, row["download_url"], path, resume=resume)
        validation = "not_downloaded"
        error = result.error
        if result.status == 200 and path.exists():
            try:
                with zipfile.ZipFile(path) as archive:
                    bad = archive.testzip()
                    names = archive.namelist()
                if bad:
                    validation = "zip_crc_failed"
                    error = f"CRC failure: {bad}"
                elif not any(name.lower().endswith(".xml") for name in names):
                    validation = "zip_without_xml"
                    error = "No XML member in archive"
                else:
                    validation = "valid_zip_xml"
            except zipfile.BadZipFile as exc:
                validation = "invalid_zip"
                error = str(exc)
        return {
            **row,
            "status_code": result.status,
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "attempt_count": result.attempts,
            "download_status": "success" if validation == "valid_zip_xml" else "failed",
            "validation_status": validation,
            "failure_reason": error,
            "raw_path": rel(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
            "sha256": sha256_file(path) if path.exists() else "",
        }

    statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=NETWORK_WORKERS) as executor:
        futures = [executor.submit(fetch_volume, row) for row in volumes]
        for future in as_completed(futures):
            statuses.append(future.result())
    statuses.sort(key=lambda row: int(row["volume"]))
    write_csv(MANIFEST_ROOT / "historic_volume_acquisition_status.csv", statuses)
    summary = {
        "generated_at": now_iso(),
        "target_volumes": len(statuses),
        "attempted": len(statuses),
        "downloaded": sum(row["download_status"] == "success" for row in statuses),
        "failed": sum(row["download_status"] != "success" for row in statuses),
        "downloaded_bytes": sum(int(row["byte_size"]) for row in statuses if row["download_status"] == "success"),
    }
    write_json(MANIFEST_ROOT / "historic_volume_acquisition_summary.json", summary)
    return summary


def _xml_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return normalise_space(" ".join(value for value in element.itertext() if value))


def _paragraph_parts(paragraph: ET.Element) -> tuple[str, str, str]:
    speaker_element = paragraph.find("./member")
    speaker = _xml_text(speaker_element)
    full = _xml_text(paragraph)
    body = full
    if speaker:
        # In several bulk-XML vintages the paragraph's leading text contains a
        # numbered-question prefix before the nested <member> value, e.g.
        # "1. Ms Abbott : To ask ...".  Strip only that anchored prefix so the
        # question detector sees the official "To ask" opening without using a
        # loose anywhere-in-text match that would misclassify ministerial prose.
        prefix = re.compile(
            rf"^\s*(?:\d+\.\s*)?(?:\[[^\]]+\]\s*)?{re.escape(speaker)}\s*[:;—-]*\s*",
            flags=re.IGNORECASE,
        )
        match = prefix.match(full)
        if match:
            body = full[match.end():]
    return speaker, body, str(paragraph.get("id") or "")


def _is_question(body: str) -> bool:
    value = normalise_space(body).lower()
    # Official written questions begin with “To ask …”.  Matching the phrase
    # anywhere misclassifies ministerial replies such as “the need to ask all
    # directorates” as questions.
    return bool(re.match(r"^(?:\d+\.\s*)?(?:\[[^\]]+\]\s*)?to ask\b", value))


def _answer_records(section: ET.Element) -> list[dict[str, Any]]:
    title = _xml_text(section.find("./title")) or "Untitled written answer"
    body = section.find("./body")
    if body is None:
        body = section
    records: list[dict[str, Any]] = []
    questions: list[dict[str, str]] = []
    responses: list[dict[str, str]] = []

    def flush() -> None:
        nonlocal questions, responses
        if responses:
            records.append({"title": title, "questions": questions, "responses": responses})
        questions = []
        responses = []

    for paragraph in body.findall(".//p"):
        speaker, text, paragraph_id = _paragraph_parts(paragraph)
        if not text:
            continue
        value = {"speaker": speaker, "text": text, "paragraph_id": paragraph_id}
        if speaker and _is_question(text):
            if responses:
                flush()
            questions.append(value)
        elif speaker:
            if responses and not questions:
                responses.append(value)
            elif responses:
                responses.append(value)
            else:
                responses = [value]
        else:
            if responses:
                responses.append(value)
            elif questions:
                questions.append(value)
    flush()
    return records


def _statement_records(section: ET.Element) -> list[dict[str, Any]]:
    title = _xml_text(section.find("./title")) or "Untitled written statement"
    body = section.find("./body")
    if body is None:
        body = section
    responses: list[dict[str, str]] = []
    for paragraph in body.findall(".//p"):
        speaker, text, paragraph_id = _paragraph_parts(paragraph)
        if text:
            responses.append({"speaker": speaker, "text": text, "paragraph_id": paragraph_id})
    return [{"title": title, "questions": [], "responses": responses}] if responses else []


def _record_identity(record: dict[str, Any], *, genre: str, sitting_date: date, department: str) -> tuple[str, str]:
    response_ids = [value["paragraph_id"] for value in record["responses"] if value.get("paragraph_id")]
    question_ids = [value["paragraph_id"] for value in record["questions"] if value.get("paragraph_id")]
    if response_ids or question_ids:
        external_id = (response_ids or question_ids)[0]
    else:
        # Some later bulk-XML volumes omit paragraph IDs.  Date/department/
        # title alone is not unique: one department can publish several same-
        # titled answers on the same day.  Include the source text fingerprint
        # so those records do not overwrite one another, while exact repeated
        # records across overlapping official volumes still deduplicate.
        record_fingerprint = sha256_bytes(
            canonical_json(
                {
                    "title": record["title"],
                    "questions": record["questions"],
                    "responses": record["responses"],
                }
            ).encode()
        )
        external_id = stable_id("historic", sitting_date, department, genre, record["title"], record_fingerprint)
    root = "written-answers" if genre == "ministerial_written_answer" else "written-statements"
    canonical = (
        f"{HISTORIC_API}/{root}/{sitting_date.year}/{sitting_date.strftime('%b').lower()}/"
        f"{sitting_date.day:02d}/{slugify(record['title'])}#{external_id}"
    )
    return external_id, canonical


def enumerate_historic_records() -> dict[str, Any]:
    """Parse downloaded XML and freeze related department answer/statement targets."""
    status_rows = read_csv(MANIFEST_ROOT / "historic_volume_acquisition_status.csv")
    existing_external, existing_urls, _ = _existing_identity_sets()
    manifest: list[dict[str, Any]] = []
    partitions: dict[tuple[int, str, str], dict[str, Any]] = {}
    parse_errors: list[dict[str, Any]] = []
    seen_identities: dict[tuple[str, str], str] = {}
    duplicate_count = 0
    record_root = RAW_ROOT / "historic_hansard" / "records"
    for status in status_rows:
        if status.get("download_status") != "success":
            continue
        zip_path = PROJECT_ROOT / status["raw_path"]
        try:
            with zipfile.ZipFile(zip_path) as archive:
                xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
                for xml_name in xml_names:
                    root = ET.fromstring(archive.read(xml_name))
                    for container_tag, genre, parser in [
                        ("writtenanswers", "ministerial_written_answer", _answer_records),
                        ("writtenstatements", "ministerial_written_statement", _statement_records),
                    ]:
                        for container in root.findall(f".//{container_tag}"):
                            date_element = container.find("./date")
                            sitting_date = parse_official_date(
                                _xml_text(date_element),
                                date_element.get("format") if date_element is not None else None,
                            )
                            if not sitting_date or not date(1988, 1, 1) <= sitting_date <= date(2004, 12, 31):
                                continue
                            # The XML schema changes over time: early volumes use
                            # <group><title>DEPARTMENT</title> while later volumes
                            # use a top-level <section> for the department.
                            department_containers = list(container.findall("./group")) + list(container.findall("./section"))
                            for group in department_containers:
                                department = normalise_label(_xml_text(group.find("./title")))
                                if department not in HISTORIC_DEPARTMENT_LABELS:
                                    continue
                                key = (sitting_date.year, genre, department)
                                partition = partitions.setdefault(
                                    key,
                                    {
                                        "partition_id": stable_id("part", "historic_xml", sitting_date.year, genre, department),
                                        "source": "uk_parliament_official_report_bulk_xml",
                                        "genre": genre,
                                        "department": department,
                                        "year": sitting_date.year,
                                        "window_start": f"{sitting_date.year}-01-01",
                                        "window_end": f"{sitting_date.year}-12-31",
                                        "enumerated_targets": 0,
                                        "existing_records": 0,
                                        "net_new_records": 0,
                                        "status": "complete_within_downloaded_official_volumes",
                                        "status_reason": "Exact official department groups parsed from every successfully downloaded overlapping volume",
                                        "source_paths": set(),
                                    },
                                )
                                partition["source_paths"].add(status["raw_path"])
                                for section in group.findall("./section"):
                                    for record in parser(section):
                                        if not record["responses"]:
                                            continue
                                        external_id, canonical_url = _record_identity(
                                            record, genre=genre, sitting_date=sitting_date, department=department
                                        )
                                        payload = {
                                            "external_id": external_id,
                                            "genre": genre,
                                            "house": "Commons",
                                            "sitting_date": sitting_date.isoformat(),
                                            "department": department,
                                            "title": record["title"],
                                            "questions": record["questions"],
                                            "responses": record["responses"],
                                            "volume": int(status["volume"]),
                                            "source_zip": status["raw_path"],
                                            "source_zip_sha256": status["sha256"],
                                            "canonical_url": canonical_url,
                                            "source_category": container_tag,
                                        }
                                        identity_key = (genre, external_id)
                                        identity_fingerprint = sha256_bytes(
                                            canonical_json(
                                                {
                                                    "sitting_date": payload["sitting_date"],
                                                    "department": payload["department"],
                                                    "title": payload["title"],
                                                    "questions": payload["questions"],
                                                    "responses": payload["responses"],
                                                }
                                            ).encode()
                                        )
                                        if identity_key in seen_identities:
                                            duplicate_count += 1
                                            if seen_identities[identity_key] != identity_fingerprint:
                                                parse_errors.append(
                                                    {
                                                        "volume": status["volume"],
                                                        "path": status["raw_path"],
                                                        "error": f"official_identity_content_conflict:{genre}:{external_id}",
                                                    }
                                                )
                                            continue
                                        seen_identities[identity_key] = identity_fingerprint
                                        record_path = record_root / str(sitting_date.year) / genre / f"{external_id}.json"
                                        write_json(record_path, payload)
                                        confirmed_speaker = next(
                                            (value["speaker"] for value in record["responses"] if value.get("speaker")), ""
                                        )
                                        existing = external_id in existing_external or canonical_url in existing_urls
                                        manifest.append(
                                            {
                                                "partition_id": partition["partition_id"],
                                                "source": "historic_hansard_bulk_xml",
                                                "genre": genre,
                                                "year": sitting_date.year,
                                                "date": sitting_date.isoformat(),
                                                "department": department,
                                                "external_id": external_id,
                                                "canonical_url": canonical_url,
                                                "title": record["title"],
                                                "government_respondent": confirmed_speaker,
                                                "question_count": len(record["questions"]),
                                                "response_segment_count": len(record["responses"]),
                                                "attribution_status": "confirmed" if confirmed_speaker else "pending",
                                                "record_path": rel(record_path),
                                                "record_sha256": sha256_file(record_path),
                                                "source_zip_path": status["raw_path"],
                                                "source_zip_sha256": status["sha256"],
                                                "volume": status["volume"],
                                                "existing_document": existing,
                                                "identity_status": "official_paragraph_id" if external_id.startswith("S6CV") else "derived_missing_paragraph_id",
                                            }
                                        )
                                        partition["enumerated_targets"] += 1
                                        partition["existing_records"] += int(existing)
                                        partition["net_new_records"] += int(not existing)
        except (zipfile.BadZipFile, ET.ParseError, OSError) as exc:
            parse_errors.append({"volume": status["volume"], "path": status["raw_path"], "error": f"{type(exc).__name__}: {exc}"})
    manifest = sorted(manifest, key=lambda row: (row["date"], row["genre"], row["department"], row["external_id"]))
    partition_rows = []
    for value in sorted(partitions.values(), key=lambda row: (row["year"], row["genre"], row["department"])):
        value = dict(value)
        value["source_paths_json"] = json.dumps(sorted(value.pop("source_paths")), ensure_ascii=False)
        partition_rows.append(value)
    write_csv(MANIFEST_ROOT / "historic_record_manifest.csv", manifest)
    write_csv(MANIFEST_ROOT / "historic_record_partitions.csv", partition_rows)
    write_csv(MANIFEST_ROOT / "historic_record_parse_errors.csv", parse_errors, ["volume", "path", "error"])
    summary = {
        "generated_at": now_iso(),
        "partitions": len(partition_rows),
        "enumerated_targets": len(manifest),
        "answers": sum(row["genre"] == "ministerial_written_answer" for row in manifest),
        "statements": sum(row["genre"] == "ministerial_written_statement" for row in manifest),
        "confirmed_attribution": sum(row["attribution_status"] == "confirmed" for row in manifest),
        "pending_attribution": sum(row["attribution_status"] != "confirmed" for row in manifest),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" or row["existing_document"] is True for row in manifest),
        "net_new_records": sum(not (str(row["existing_document"]).lower() == "true" or row["existing_document"] is True) for row in manifest),
        "duplicates_removed": duplicate_count,
        "parse_errors": len(parse_errors),
        "by_department": dict(Counter(row["department"] for row in manifest)),
        "by_year": dict(Counter(str(row["year"]) for row in manifest)),
    }
    write_json(MANIFEST_ROOT / "historic_record_enumeration_summary.json", summary)
    return summary


def _hansard_written_search_url(year: int, skip: int, take: int) -> str:
    end = date(year, 12, 31)
    if year == 2010:
        end = date(2010, 4, 30)
    params = {
        "queryParameters.house": "Commons",
        "queryParameters.startDate": f"{year}-01-01",
        "queryParameters.endDate": end.isoformat(),
        "queryParameters.skip": str(skip),
        "queryParameters.take": str(take),
        "queryParameters.orderBy": "SittingDateAsc",
    }
    return f"{HANSARD_API}/search/contributions/Written.json?{urlencode(params)}"


def enumerate_hansard_candidates(*, resume: bool = True) -> dict[str, Any]:
    """Freeze all Commons Written contribution candidates for 2005–Apr 2010."""
    client = BoundedClient(minimum_interval=0.16)
    candidates: dict[str, dict[str, Any]] = {}
    partitions: list[dict[str, Any]] = []
    for year in range(2005, 2011):
        skip = 0
        take = 100
        total: int | None = None
        returned = 0
        raw_paths: list[str] = []
        error = ""
        while True:
            url = _hansard_written_search_url(year, skip, take)
            path = RAW_ROOT / "hansard_api" / "search" / str(year) / f"page_{skip:06d}.json"
            result = fetch_to_path(client, url, path, resume=resume)
            if result.status != 200 or not path.exists():
                error = result.error or f"HTTP {result.status}"
                break
            payload = read_json(path)
            if payload.get("Message") and not payload.get("Results"):
                error = f"api_error_payload:{payload.get('Message')}"
                break
            observed_total = int(payload.get("TotalResultCount", -1))
            total = observed_total if total is None else total
            if observed_total != total:
                error = f"total_drift:{total}->{observed_total}"
                break
            results = payload.get("Results") or []
            if not isinstance(results, list):
                error = "results_not_list"
                break
            raw_paths.append(rel(path))
            returned += len(results)
            for item in results:
                ext_id = str(item.get("DebateSectionExtId") or "")
                if not ext_id:
                    continue
                value = candidates.setdefault(
                    ext_id,
                    {
                        "candidate_id": ext_id,
                        "year": year,
                        "date": str(item.get("SittingDate") or "")[:10],
                        "section": str(item.get("Section") or ""),
                        "title": normalise_space(str(item.get("DebateSection") or "")),
                        "house": str(item.get("House") or ""),
                        "first_attributed_to": normalise_space(str(item.get("AttributedTo") or "")),
                        "search_result_contributions": 0,
                        "search_paths": [],
                    },
                )
                value["search_result_contributions"] += 1
                if rel(path) not in value["search_paths"]:
                    value["search_paths"].append(rel(path))
            skip += len(results)
            if skip >= observed_total or not results:
                break
        partitions.append(
            {
                "partition_id": f"hansard_written_candidates_{year}",
                "source": "hansard_search_api",
                "genre": "written_candidates",
                "department": "unresolved_until_detail_navigation",
                "year": year,
                "window_start": f"{year}-01-01",
                "window_end": (date(2010, 4, 30) if year == 2010 else date(year, 12, 31)).isoformat(),
                "query_url": _hansard_written_search_url(year, 0, take),
                "initial_total": total if total is not None else -1,
                "returned_count": returned,
                "unique_candidate_debates": sum(value["year"] == year for value in candidates.values()),
                "status": "complete_as_visible" if not error and returned == (total or 0) else "partial",
                "status_reason": error or "All Commons Written contribution pages returned; unique debate sections frozen before detail retrieval",
                "raw_paths_json": json.dumps(raw_paths, ensure_ascii=False),
            }
        )
    candidate_rows = []
    for value in sorted(candidates.values(), key=lambda row: (row["date"], row["candidate_id"])):
        value = dict(value)
        value["search_paths_json"] = json.dumps(value.pop("search_paths"), ensure_ascii=False)
        value["detail_url"] = f"{HANSARD_API}/debates/debate/{value['candidate_id']}.json"
        candidate_rows.append(value)
    write_csv(MANIFEST_ROOT / "hansard_candidate_manifest.csv", candidate_rows)
    write_csv(MANIFEST_ROOT / "hansard_candidate_partitions.csv", partitions)
    summary = {
        "generated_at": now_iso(),
        "contribution_results": sum(int(row["returned_count"]) for row in partitions),
        "unique_candidate_debates": len(candidate_rows),
        "complete_partitions": sum(row["status"] == "complete_as_visible" for row in partitions),
        "partitions": len(partitions),
    }
    write_json(MANIFEST_ROOT / "hansard_candidate_summary.json", summary)
    return summary


def _hansard_department(detail: dict[str, Any]) -> str:
    navigator = detail.get("Navigator") or []
    # The API occasionally returns more than one department node in a nested
    # navigator (notably the 2006-05-22 written-answer tree).  The first node
    # is then a structural ancestor, not the answering department.  Resolve
    # the actual debate item and walk its ParentId chain so the nearest valid
    # department ancestor wins.
    by_id = {
        int(item["Id"]): item
        for item in navigator
        if item.get("Id") is not None
    }
    overview = detail.get("Overview") or {}
    target: dict[str, Any] | None = None
    overview_id = overview.get("Id")
    if overview_id is not None:
        target = by_id.get(int(overview_id))
    if target is None and overview.get("ExtId"):
        target = next(
            (
                item
                for item in navigator
                if str(item.get("ExternalId") or "") == str(overview.get("ExtId"))
            ),
            None,
        )
    seen: set[int] = set()
    current = target
    while current is not None and current.get("ParentId") is not None:
        parent_id = int(current["ParentId"])
        if parent_id in seen:
            break
        seen.add(parent_id)
        parent = by_id.get(parent_id)
        if parent is None:
            break
        if str(parent.get("HRSTag") or "").lower() == "hs_6bdepartment":
            return normalise_label(str(parent.get("Title") or ""))
        current = parent
    departments = [
        item
        for item in navigator
        if str(item.get("HRSTag") or "").lower() == "hs_6bdepartment"
    ]
    if len(departments) == 1:
        return normalise_label(str(departments[0].get("Title") or ""))
    if len(navigator) >= 2:
        fallback = navigator[-2]
        if str(fallback.get("HRSTag") or "").lower() == "hs_6bdepartment":
            return normalise_label(str(fallback.get("Title") or ""))
    return ""


def _hansard_question_value(item: dict[str, Any]) -> tuple[bool, str, str]:
    """Return structured question role, text and speaker without guessing.

    Hansard's ``Question`` and ``ERR_Question`` tags are authoritative even
    when numbering or an embedded ``<strong>Speaker:</strong>`` prefix means
    the normalized text does not literally start with ``To ask``.  A populated
    ``QuestionText`` element is preferred so malformed wrappers containing
    trailing correction/answer prose are not silently attributed as question
    context.  Continuations inherit only the previous questioner's displayed
    name in the caller; they never become government responses.
    """
    raw_value = str(item.get("Value") or "")
    soup = BeautifulSoup(raw_value, "html.parser")
    full_text = normalise_space(soup.get_text(" ", strip=True))
    tag = str(item.get("HRSTag") or "").lower()
    structured = tag in {"question", "err_question"}
    question_text = ""
    if structured:
        question_node = soup.find(lambda value: value.name and value.name.lower() == "questiontext")
        if question_node is not None:
            question_text = normalise_space(question_node.get_text(" ", strip=True))
        if not question_text:
            question_text = full_text
    speaker = normalise_space(str(item.get("AttributedTo") or ""))
    if structured and not speaker:
        strong = soup.find("strong")
        if strong is not None:
            speaker = normalise_space(strong.get_text(" ", strip=True)).rstrip(":")
            prefix = re.compile(rf"^\s*{re.escape(speaker)}\s*:\s*", flags=re.IGNORECASE)
            question_text = prefix.sub("", question_text, count=1)
    return structured, question_text or full_text, speaker


def _hansard_detail_record(detail: dict[str, Any], department: str) -> dict[str, Any] | None:
    overview = detail.get("Overview") or {}
    location = normalise_label(str(overview.get("Location") or ""))
    if "WRITTEN ANSWER" in location:
        genre = "ministerial_written_answer"
    elif "WRITTEN STATEMENT" in location:
        genre = "ministerial_written_statement"
    else:
        return None
    questions: list[dict[str, str]] = []
    responses: list[dict[str, str]] = []
    previous_question_speaker = ""
    for item in detail.get("Items") or []:
        if item.get("ItemType") != "Contribution":
            continue
        structured_question, structured_text, structured_speaker = _hansard_question_value(item)
        raw_value = str(item.get("Value") or "")
        text = structured_text or normalise_space(BeautifulSoup(raw_value, "html.parser").get_text(" ", strip=True))
        if not text:
            continue
        speaker = structured_speaker or normalise_space(str(item.get("AttributedTo") or ""))
        if structured_question and str(item.get("HRSTag") or "").lower() == "err_question" and not speaker:
            speaker = previous_question_speaker
        value = {
            "speaker": speaker,
            "text": text,
            "paragraph_id": str(item.get("ExternalId") or item.get("ItemId") or ""),
            "uin": str(item.get("UIN") or ""),
            "source_tag": str(item.get("HRSTag") or ""),
        }
        if genre == "ministerial_written_answer" and (structured_question or _is_question(text)):
            questions.append(value)
            if speaker:
                previous_question_speaker = speaker
        else:
            responses.append(value)
    if not responses:
        return None
    sitting = str(overview.get("Date") or "")[:10]
    external_id = str(overview.get("ExtId") or "")
    house_segment = "Commons"
    root = "written-answers" if genre == "ministerial_written_answer" else "written-statements"
    canonical = (
        f"https://hansard.parliament.uk/{house_segment}/{sitting}/"
        f"{root}/{external_id}/{slugify(str(overview.get('Title') or 'untitled'))}"
    )
    respondent = next((value["speaker"] for value in responses if value["speaker"]), "")
    return {
        "external_id": external_id,
        "genre": genre,
        "house": "Commons",
        "sitting_date": sitting,
        "department": department,
        "title": normalise_space(str(overview.get("Title") or "")),
        "questions": questions,
        "responses": responses,
        "volume": overview.get("VolumeNo"),
        "canonical_url": canonical,
        "government_respondent": respondent,
        "attribution_status": "confirmed" if respondent else "pending",
        "source_category": str(overview.get("Location") or ""),
        "content_last_updated": str(overview.get("ContentLastUpdated") or ""),
    }


def acquire_hansard_details(*, resume: bool = True) -> dict[str, Any]:
    """Retrieve candidate details, verify department navigation, and freeze eligible targets."""
    client = BoundedClient(minimum_interval=0.1)
    candidates = read_csv(MANIFEST_ROOT / "hansard_candidate_manifest.csv")
    existing_external, existing_urls, _ = _existing_identity_sets()

    def fetch_candidate(candidate: dict[str, str]) -> dict[str, Any]:
        path = RAW_ROOT / "hansard_api" / "details" / str(candidate["year"]) / f"{candidate['candidate_id']}.json"
        result = fetch_to_path(client, candidate["detail_url"], path, resume=resume)
        output: dict[str, Any] = {
            **candidate,
            "status_code": result.status,
            "attempt_count": result.attempts,
            "retrieved_at": result.retrieved_at,
            "download_status": "success" if result.status == 200 and path.exists() else "failed",
            "failure_reason": result.error,
            "detail_path": rel(path) if path.exists() else "",
            "detail_sha256": sha256_file(path) if path.exists() else "",
            "department": "",
            "eligible": False,
        }
        if result.status == 200 and path.exists():
            detail = read_json(path)
            department = _hansard_department(detail)
            output["department"] = department
            output["eligible"] = department in HISTORIC_DEPARTMENT_LABELS
        return output

    statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        futures = [executor.submit(fetch_candidate, candidate) for candidate in candidates]
        for future in as_completed(futures):
            statuses.append(future.result())
    statuses.sort(key=lambda row: (row["date"], row["candidate_id"]))
    write_csv(MANIFEST_ROOT / "hansard_candidate_acquisition_status.csv", statuses)

    manifest: list[dict[str, Any]] = []
    for status in statuses:
        if str(status.get("eligible", "")).lower() != "true" or status.get("download_status") != "success":
            continue
        detail = read_json(PROJECT_ROOT / status["detail_path"])
        record = _hansard_detail_record(detail, status["department"])
        if not record:
            continue
        external_id = record["external_id"]
        canonical_url = record["canonical_url"]
        manifest.append(
            {
                "partition_id": stable_id("part", "hansard_api", record["sitting_date"][:4], record["genre"], record["department"]),
                "source": "hansard_api",
                "genre": record["genre"],
                "year": int(record["sitting_date"][:4]),
                "date": record["sitting_date"],
                "department": record["department"],
                "external_id": external_id,
                "canonical_url": canonical_url,
                "title": record["title"],
                "government_respondent": record["government_respondent"],
                "question_count": len(record["questions"]),
                "response_segment_count": len(record["responses"]),
                "attribution_status": record["attribution_status"],
                "record_path": status["detail_path"],
                "record_sha256": status["detail_sha256"],
                "volume": record.get("volume") or "",
                "updated_at": record.get("content_last_updated") or "",
                "existing_document": external_id in existing_external or canonical_url in existing_urls,
                "identity_status": "official_debate_section_ext_id",
            }
        )
    manifest.sort(key=lambda row: (row["date"], row["genre"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_statement_manifest.csv", manifest)
    write_csv(MANIFEST_ROOT / "hansard_record_manifest.csv", manifest)
    partitions: dict[tuple[int, str, str], dict[str, Any]] = {}
    for row in manifest:
        key = (int(row["year"]), row["genre"], row["department"])
        value = partitions.setdefault(
            key,
            {
                "partition_id": row["partition_id"],
                "source": "hansard_api",
                "genre": row["genre"],
                "department": row["department"],
                "year": row["year"],
                "window_start": f"{row['year']}-01-01",
                "window_end": "2010-04-30" if int(row["year"]) == 2010 else f"{row['year']}-12-31",
                "enumerated_targets": 0,
                "existing_records": 0,
                "net_new_records": 0,
                "status": "complete_within_official_written_candidate_index",
                "status_reason": "All Written candidate debates enumerated; eligibility verified from official department navigator",
            },
        )
        value["enumerated_targets"] += 1
        existing = str(row["existing_document"]).lower() == "true" or row["existing_document"] is True
        value["existing_records"] += int(existing)
        value["net_new_records"] += int(not existing)
    partition_values = sorted(partitions.values(), key=lambda row: (int(row["year"]), row["genre"], row["department"]))
    write_csv(MANIFEST_ROOT / "hansard_statement_partitions.csv", partition_values)
    write_csv(MANIFEST_ROOT / "hansard_record_partitions.csv", partition_values)
    summary = {
        "generated_at": now_iso(),
        "candidate_targets": len(statuses),
        "candidate_downloaded": sum(row["download_status"] == "success" for row in statuses),
        "candidate_failed": sum(row["download_status"] != "success" for row in statuses),
        "eligible_records": len(manifest),
        "answers": sum(row["genre"] == "ministerial_written_answer" for row in manifest),
        "statements": sum(row["genre"] == "ministerial_written_statement" for row in manifest),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" or row["existing_document"] is True for row in manifest),
        "net_new_records": sum(not (str(row["existing_document"]).lower() == "true" or row["existing_document"] is True) for row in manifest),
        "by_department": dict(Counter(row["department"] for row in manifest)),
    }
    write_json(MANIFEST_ROOT / "hansard_record_summary.json", summary)
    return summary


def _hansard_answer_search_url(year: int, skip: int, take: int = 100) -> str:
    end = date(2010, 4, 30) if year == 2010 else date(year, 12, 31)
    params = {
        "queryParameters.house": "Commons",
        "queryParameters.startDate": f"{year}-01-01",
        "queryParameters.endDate": end.isoformat(),
        "queryParameters.skip": str(skip),
        "queryParameters.take": str(take),
        "queryParameters.orderBy": "SittingDateAsc",
    }
    return f"{HANSARD_API}/search/contributions/WrittenAnswers.json?{urlencode(params)}"


def enumerate_hansard_answer_response_index(*, resume: bool = True) -> dict[str, Any]:
    """Diagnostic fallback: scan the 2005–Apr 2010 response contribution index.

    The search result supplies the complete response text and official department
    section but not the paired question.  Question context is therefore recorded
    as unavailable in this channel rather than reconstructed or fabricated.
    """
    # This endpoint has a hard 100-row page limit and sometimes returns an
    # HTTP-200 JSON error object under load.  Use modest concurrency and retry
    # based on response structure, not the status code alone.
    client = BoundedClient(minimum_interval=0.12)
    existing_external, existing_urls, _ = _existing_identity_sets()
    page_targets: list[tuple[int, int, str, Path]] = []
    year_totals: dict[int, int] = {}
    first_paths: dict[int, str] = {}

    def acquire_answer_page(
        url: str,
        path: Path,
        expected_total: int | None,
    ) -> tuple[FetchResult, dict[str, Any] | None, int, str]:
        """Acquire one page with bounded retries for HTTP-200 error payloads."""
        total_attempts = 0
        last_result = FetchResult(url, url, 0, "", b"", now_iso(), 0, "not_attempted")
        last_failure = "not_attempted"
        for content_attempt in range(1, 5):
            # Invalid cached payloads are failed responses, not checkpoints.
            if path.exists():
                try:
                    cached = read_json(path)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    cached = None
                cached_total = int(cached.get("TotalResultCount", -1)) if isinstance(cached, dict) else -1
                cached_valid = (
                    isinstance(cached, dict)
                    and not cached.get("Message")
                    and isinstance(cached.get("Results"), list)
                    and cached_total >= 0
                    and (expected_total is None or cached_total == expected_total)
                )
                if not cached_valid:
                    path.unlink(missing_ok=True)
            last_result = fetch_to_path(client, url, path, resume=resume and content_attempt == 1)
            total_attempts += last_result.attempts
            payload: dict[str, Any] | None = None
            if last_result.status == 200 and path.exists():
                try:
                    payload = read_json(path)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    last_failure = f"invalid_json:{exc}"
                if isinstance(payload, dict):
                    observed_total = int(payload.get("TotalResultCount", -1))
                    if (
                        not payload.get("Message")
                        and isinstance(payload.get("Results"), list)
                        and observed_total >= 0
                        and (expected_total is None or observed_total == expected_total)
                    ):
                        return last_result, payload, total_attempts, ""
                    last_failure = (
                        f"api_error_payload:{payload.get('Message')}"
                        if payload.get("Message")
                        else f"total_drift:{expected_total}->{observed_total}"
                    )
            else:
                last_failure = last_result.error or f"HTTP {last_result.status}"
            path.unlink(missing_ok=True)
            if content_attempt < 4:
                time.sleep(min(6.0, 0.75 * (2 ** (content_attempt - 1))))
        return last_result, None, total_attempts, last_failure

    for year in range(2005, 2011):
        url = _hansard_answer_search_url(year, 0, 100)
        path = RAW_ROOT / "hansard_api" / "written_answers" / str(year) / "page_000000.json"
        result, payload, _, _ = acquire_answer_page(url, path, None)
        if result.status != 200 or payload is None:
            year_totals[year] = -1
            continue
        total = int(payload.get("TotalResultCount", -1))
        year_totals[year] = total
        first_paths[year] = rel(path)
        for skip in range(100, max(0, total), 100):
            target_path = RAW_ROOT / "hansard_api" / "written_answers" / str(year) / f"page_{skip:06d}.json"
            page_targets.append((year, skip, _hansard_answer_search_url(year, skip, 100), target_path))

    def fetch_page(target: tuple[int, int, str, Path]) -> dict[str, Any]:
        year, skip, url, path = target
        result, payload, attempts, failure = acquire_answer_page(url, path, year_totals.get(year))
        valid = payload is not None
        returned = len(payload.get("Results") or []) if payload else 0
        total = int(payload.get("TotalResultCount", -1)) if payload else -1
        return {
            "year": year,
            "skip": skip,
            "path": rel(path) if path.exists() else "",
            "status_code": result.status,
            "attempt_count": attempts,
            "returned": returned,
            "observed_total": total,
            "status": "success" if valid else "failed",
            "failure_reason": failure,
        }

    page_statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_page, target) for target in page_targets]
        for future in as_completed(futures):
            page_statuses.append(future.result())
    # First pages were obtained before the page target was frozen.
    for year, total in year_totals.items():
        if total < 0:
            page_statuses.append({"year": year, "skip": 0, "path": "", "status_code": 0, "attempt_count": 0, "returned": 0, "observed_total": total, "status": "failed", "failure_reason": "first_page_failed"})
        else:
            payload = read_json(PROJECT_ROOT / first_paths[year])
            page_statuses.append({"year": year, "skip": 0, "path": first_paths[year], "status_code": 200, "attempt_count": 1, "returned": len(payload.get("Results") or []), "observed_total": total, "status": "success", "failure_reason": ""})
    page_statuses.sort(key=lambda row: (int(row["year"]), int(row["skip"])))
    write_csv(MANIFEST_ROOT / "hansard_answer_page_status.csv", page_statuses)

    manifest: list[dict[str, Any]] = []
    partitions: dict[tuple[int, str], dict[str, Any]] = {}
    record_root = RAW_ROOT / "hansard_api" / "written_answer_records"
    for status in page_statuses:
        if status["status"] != "success" or not status["path"]:
            continue
        payload = read_json(PROJECT_ROOT / status["path"])
        for item in payload.get("Results") or []:
            department = normalise_label(str(item.get("HansardSection") or ""))
            if department not in HISTORIC_DEPARTMENT_LABELS:
                continue
            external_id = str(item.get("ContributionExtId") or item.get("ItemId") or "")
            if not external_id:
                continue
            sitting_date = str(item.get("SittingDate") or "")[:10]
            debate_ext = str(item.get("DebateSectionExtId") or "")
            title = normalise_space(str(item.get("DebateSection") or "Written Questions: Government Responses"))
            response_text = normalise_space(BeautifulSoup(str(item.get("ContributionTextFull") or item.get("ContributionText") or ""), "html.parser").get_text(" ", strip=True))
            speaker = normalise_space(str(item.get("AttributedTo") or item.get("MemberName") or ""))
            canonical = f"https://hansard.parliament.uk/Commons/{sitting_date}/written-answers/{debate_ext}#{external_id}"
            record = {
                "external_id": external_id,
                "genre": "ministerial_written_answer",
                "house": "Commons",
                "sitting_date": sitting_date,
                "department": department,
                "title": title,
                "questions": [],
                "question_context_status": "unavailable_in_hansard_search_response_index",
                "responses": [{"speaker": speaker, "text": response_text, "paragraph_id": external_id}],
                "canonical_url": canonical,
                "government_respondent": speaker,
                "attribution_status": "confirmed" if speaker else "pending",
                "source_category": str(item.get("Section") or "Written Answers"),
                "source_page": status["path"],
                "source_page_sha256": sha256_file(PROJECT_ROOT / status["path"]),
            }
            record_path = record_root / sitting_date[:4] / f"{external_id}.json"
            write_json(record_path, record)
            existing = external_id in existing_external or canonical in existing_urls
            partition_id = stable_id("part", "hansard_api_written_answers", sitting_date[:4], department)
            manifest.append(
                {
                    "partition_id": partition_id,
                    "source": "hansard_api_written_answers",
                    "genre": "ministerial_written_answer",
                    "year": int(sitting_date[:4]),
                    "date": sitting_date,
                    "department": department,
                    "external_id": external_id,
                    "canonical_url": canonical,
                    "title": title,
                    "government_respondent": speaker,
                    "question_count": 0,
                    "response_segment_count": 1,
                    "attribution_status": "confirmed" if speaker else "pending",
                    "record_path": rel(record_path),
                    "record_sha256": sha256_file(record_path),
                    "volume": "",
                    "updated_at": "",
                    "existing_document": existing,
                    "identity_status": "official_contribution_ext_id_question_context_unavailable",
                }
            )
            key = (int(sitting_date[:4]), department)
            value = partitions.setdefault(
                key,
                {
                    "partition_id": partition_id,
                    "source": "hansard_api_written_answers",
                    "genre": "ministerial_written_answer",
                    "department": department,
                    "year": int(sitting_date[:4]),
                    "window_start": f"{sitting_date[:4]}-01-01",
                    "window_end": "2010-04-30" if sitting_date.startswith("2010") else f"{sitting_date[:4]}-12-31",
                    "enumerated_targets": 0,
                    "existing_records": 0,
                    "net_new_records": 0,
                    "status": "complete_response_index_question_context_unavailable",
                    "status_reason": "All official WrittenAnswers response pages enumerated; exact HansardSection filter; paired question not exposed in this response index.",
                },
            )
            value["enumerated_targets"] += 1
            value["existing_records"] += int(existing)
            value["net_new_records"] += int(not existing)
    # Deduplicate response contributions, then merge the independently acquired statement series.
    answer_unique = {(row["genre"], row["external_id"]): row for row in manifest}
    answers = sorted(answer_unique.values(), key=lambda row: (row["date"], row["department"], row["external_id"]))
    statements = read_csv(MANIFEST_ROOT / "hansard_statement_manifest.csv")
    combined = sorted(statements + answers, key=lambda row: (row["date"], row["genre"], row["department"], row["external_id"]))
    statement_partitions = read_csv(MANIFEST_ROOT / "hansard_statement_partitions.csv")
    answer_partitions = sorted(partitions.values(), key=lambda row: (int(row["year"]), row["department"]))
    write_csv(MANIFEST_ROOT / "hansard_answer_manifest.csv", answers)
    write_csv(MANIFEST_ROOT / "hansard_answer_partitions.csv", answer_partitions)
    write_csv(MANIFEST_ROOT / "hansard_record_manifest.csv", combined)
    write_csv(MANIFEST_ROOT / "hansard_record_partitions.csv", statement_partitions + answer_partitions)
    failed_pages = [row for row in page_statuses if row["status"] != "success"]
    summary = {
        "generated_at": now_iso(),
        "source_response_targets": sum(max(0, total) for total in year_totals.values()),
        "page_targets": len(page_statuses),
        "successful_pages": len(page_statuses) - len(failed_pages),
        "failed_pages": len(failed_pages),
        "eligible_answers": len(answers),
        "paired_question_context_available": 0,
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in answers),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in answers),
        "by_department": dict(Counter(row["department"] for row in answers)),
        "year_source_totals": {str(year): total for year, total in year_totals.items()},
    }
    write_json(MANIFEST_ROOT / "hansard_answer_summary.json", summary)
    return summary


def _fetch_valid_json_payload(
    client: BoundedClient,
    url: str,
    path: Path,
    validator: Any,
    *,
    resume: bool,
    content_attempts: int = 3,
) -> tuple[FetchResult, Any, int, str]:
    """Fetch JSON with bounded retries for APIs that return error JSON as HTTP 200."""
    total_attempts = 0
    last_result = FetchResult(url, url, 0, "", b"", now_iso(), 0, "not_attempted")
    last_error = "not_attempted"
    for content_attempt in range(1, content_attempts + 1):
        if path.exists():
            try:
                cached_payload = read_json(path)
            except (json.JSONDecodeError, UnicodeDecodeError):
                cached_payload = None
            if not validator(cached_payload):
                path.unlink(missing_ok=True)
        last_result = fetch_to_path(client, url, path, resume=resume and content_attempt == 1)
        total_attempts += last_result.attempts
        payload = None
        if last_result.status == 200 and path.exists():
            try:
                payload = read_json(path)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                last_error = f"invalid_json:{exc}"
            if validator(payload):
                return last_result, payload, total_attempts, ""
            if isinstance(payload, dict) and payload.get("Message"):
                last_error = f"api_error_payload:{payload.get('Message')}"
            else:
                last_error = "unexpected_json_structure"
        else:
            last_error = last_result.error or f"HTTP {last_result.status}"
        path.unlink(missing_ok=True)
        if content_attempt < content_attempts:
            time.sleep(min(6.0, 0.75 * (2 ** (content_attempt - 1))))
    return last_result, None, total_attempts, last_error


def _hansard_calendar_url(year: int, month: int) -> str:
    return f"{HANSARD_API}/overview/calendar.json?{urlencode({'year': year, 'month': month, 'house': 'Commons'})}"


def _hansard_answer_tree_url(sitting_date: str) -> str:
    params = {"section": "Writtens", "date": sitting_date, "house": "Commons", "groupByOwner": "true"}
    return f"{HANSARD_API}/overview/sectiontrees.json?{urlencode(params)}"


def enumerate_hansard_answers(*, resume: bool = True) -> dict[str, Any]:
    """Freeze 2005–Apr 2010 answer-section targets from daily official trees.

    The documented contribution search department parameter is ignored by the
    service for this record type.  Daily section trees expose explicit
    department nodes and direct question-section children, producing a smaller,
    auditable denominator before any target detail is downloaded.
    """
    client = BoundedClient(minimum_interval=0.14)
    existing_external, existing_urls, _ = _existing_identity_sets()
    calendar_targets: list[tuple[int, int, str, Path]] = []
    for year in range(2005, 2011):
        last_month = 4 if year == 2010 else 12
        for month in range(1, last_month + 1):
            url = _hansard_calendar_url(year, month)
            path = RAW_ROOT / "hansard_api" / "written_answer_calendars" / str(year) / f"month_{month:02d}.json"
            calendar_targets.append((year, month, url, path))

    def fetch_calendar(target: tuple[int, int, str, Path]) -> dict[str, Any]:
        year, month, url, path = target
        result, payload, attempts, failure = _fetch_valid_json_payload(
            client, url, path, lambda value: isinstance(value, list), resume=resume
        )
        dates = [] if payload is None else sorted(
            {
                str(item.get("ItemDate") or "")[:10]
                for item in payload
                if isinstance(item, dict) and str(item.get("House") or "").lower() == "commons"
            }
        )
        dates = [value for value in dates if value and value <= CUTOFF.isoformat()]
        return {
            "year": year,
            "month": month,
            "query_url": url,
            "path": rel(path) if path.exists() else "",
            "status_code": result.status,
            "attempt_count": attempts,
            "sitting_days": len(dates),
            "dates_json": json.dumps(dates, ensure_ascii=False),
            "status": "success" if payload is not None else "failed",
            "failure_reason": failure,
        }

    calendar_statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_calendar, target) for target in calendar_targets]
        for future in as_completed(futures):
            calendar_statuses.append(future.result())
    calendar_statuses.sort(key=lambda row: (int(row["year"]), int(row["month"])))
    write_csv(MANIFEST_ROOT / "hansard_answer_calendar_status.csv", calendar_statuses)
    sitting_dates = sorted(
        {
            value
            for row in calendar_statuses
            if row["status"] == "success"
            for value in json.loads(row["dates_json"])
            if "2005-01-01" <= value <= "2010-04-30"
        }
    )

    tree_targets = [
        (
            sitting_date,
            _hansard_answer_tree_url(sitting_date),
            RAW_ROOT / "hansard_api" / "written_answer_trees" / sitting_date[:4] / f"{sitting_date}.json",
        )
        for sitting_date in sitting_dates
    ]

    def fetch_tree(target: tuple[str, str, Path]) -> dict[str, Any]:
        sitting_date, url, path = target
        result, payload, attempts, failure = _fetch_valid_json_payload(
            client, url, path, lambda value: isinstance(value, list), resume=resume
        )
        return {
            "date": sitting_date,
            "year": int(sitting_date[:4]),
            "query_url": url,
            "path": rel(path) if path.exists() else "",
            "path_sha256": sha256_file(path) if path.exists() else "",
            "status_code": result.status,
            "attempt_count": attempts,
            "status": "success" if payload is not None else "failed",
            "failure_reason": failure,
        }

    tree_statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_tree, target) for target in tree_targets]
        for future in as_completed(futures):
            tree_statuses.append(future.result())
    tree_statuses.sort(key=lambda row: row["date"])
    write_csv(MANIFEST_ROOT / "hansard_answer_tree_status.csv", tree_statuses)

    target_rows: list[dict[str, Any]] = []
    for status in tree_statuses:
        if status["status"] != "success" or not status["path"]:
            continue
        payload = read_json(PROJECT_ROOT / status["path"])
        for section in payload:
            items = section.get("SectionTreeItems") or [] if isinstance(section, dict) else []
            departments = {
                int(item["Id"]): normalise_label(str(item.get("Title") or ""))
                for item in items
                if str(item.get("HRSTag") or "").lower().endswith("department")
                and normalise_label(str(item.get("Title") or "")) in HISTORIC_DEPARTMENT_LABELS
            }
            for item in items:
                parent_id = item.get("ParentId")
                external_id = str(item.get("ExternalId") or "")
                if parent_id not in departments or not external_id:
                    continue
                if "question" not in str(item.get("HRSTag") or "").lower():
                    continue
                department = departments[int(parent_id)]
                title = normalise_space(str(item.get("Title") or "Untitled written answer"))
                sitting_date = status["date"]
                canonical = (
                    f"https://hansard.parliament.uk/Commons/{sitting_date}/written-answers/"
                    f"{external_id}/{slugify(title)}"
                )
                target_rows.append(
                    {
                        "partition_id": stable_id("part", "hansard_api_answer_tree", sitting_date[:4], department),
                        "source": "hansard_api_daily_answer_tree",
                        "genre": "ministerial_written_answer",
                        "year": int(sitting_date[:4]),
                        "date": sitting_date,
                        "department": department,
                        "external_id": external_id,
                        "canonical_url": canonical,
                        "title": title,
                        "detail_url": f"{HANSARD_API}/debates/debate/{external_id}.json",
                        "tree_path": status["path"],
                        "tree_sha256": status["path_sha256"],
                        "existing_document": external_id in existing_external or canonical in existing_urls,
                        "identity_status": "official_daily_tree_department_and_debate_section_ext_id",
                    }
                )
    unique_targets: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for row in target_rows:
        if row["external_id"] in unique_targets:
            duplicates += 1
            continue
        unique_targets[row["external_id"]] = row
    target_rows = sorted(unique_targets.values(), key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_answer_target_manifest.csv", target_rows)

    partitions: dict[tuple[int, str], dict[str, Any]] = {}
    for row in target_rows:
        key = (int(row["year"]), row["department"])
        value = partitions.setdefault(
            key,
            {
                "partition_id": row["partition_id"],
                "source": "hansard_api_daily_answer_tree",
                "genre": "ministerial_written_answer",
                "department": row["department"],
                "year": row["year"],
                "window_start": f"{row['year']}-01-01",
                "window_end": "2010-04-30" if int(row["year"]) == 2010 else f"{row['year']}-12-31",
                "enumerated_targets": 0,
                "existing_records": 0,
                "net_new_records": 0,
                "status": "complete_within_successful_daily_section_trees",
                "status_reason": "Exact official department nodes and their direct written-question section children.",
            },
        )
        value["enumerated_targets"] += 1
        existing = str(row["existing_document"]).lower() == "true" or row["existing_document"] is True
        value["existing_records"] += int(existing)
        value["net_new_records"] += int(not existing)
    partition_values = sorted(partitions.values(), key=lambda row: (int(row["year"]), row["department"]))
    write_csv(MANIFEST_ROOT / "hansard_answer_partitions.csv", partition_values)
    summary = {
        "generated_at": now_iso(),
        "calendar_month_targets": len(calendar_targets),
        "calendar_months_successful": sum(row["status"] == "success" for row in calendar_statuses),
        "sitting_days": len(sitting_dates),
        "tree_targets": len(tree_targets),
        "tree_downloaded": sum(row["status"] == "success" for row in tree_statuses),
        "tree_failed": sum(row["status"] != "success" for row in tree_statuses),
        "eligible_answer_sections": len(target_rows),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in target_rows),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in target_rows),
        "duplicates_removed": duplicates,
        "by_department": dict(Counter(row["department"] for row in target_rows)),
        "by_year": dict(Counter(str(row["year"]) for row in target_rows)),
        "unit": "official written-answer debate/question section",
        "question_context_plan": "full question and response retained from official debate detail",
    }
    write_json(MANIFEST_ROOT / "hansard_answer_enumeration_summary.json", summary)
    return summary


def acquire_hansard_answer_details(*, resume: bool = True) -> dict[str, Any]:
    """Retrieve and verify every frozen 2005–Apr 2010 answer-section detail."""
    client = BoundedClient(minimum_interval=0.5)
    targets = [
        row
        for row in read_csv(MANIFEST_ROOT / "hansard_answer_target_manifest.csv")
        if str(row.get("existing_document", "")).lower() != "true"
    ]
    def fetch_answer(row: dict[str, str]) -> dict[str, Any]:
        path = RAW_ROOT / "hansard_api" / "written_answer_details" / row["year"] / f"{row['external_id']}.json"

        def validator(value: Any) -> bool:
            return (
                isinstance(value, dict)
                and isinstance(value.get("Overview"), dict)
                and str(value["Overview"].get("ExtId") or "") == row["external_id"]
                and isinstance(value.get("Items"), list)
            )

        result, payload, attempts, failure = _fetch_valid_json_payload(
            client, row["detail_url"], path, validator, resume=resume
        )
        department = _hansard_department(payload) if payload is not None else ""
        record = _hansard_detail_record(payload, department) if payload is not None else None
        valid = bool(
            record
            and department == row["department"]
            and record["genre"] == "ministerial_written_answer"
            and record.get("questions")
            and record.get("responses")
        )
        if payload is not None and not valid:
            failure = (
                f"detail_validation_failed:department={department};"
                f"questions={len(record.get('questions') or []) if record else 0};"
                f"responses={len(record.get('responses') or []) if record else 0}"
            )
        return {
            **row,
            "status_code": result.status,
            "attempt_count": attempts,
            "retrieved_at": result.retrieved_at,
            "download_status": "success" if valid else "failed",
            "validation_status": "full_question_response_and_department_verified" if valid else "invalid_or_incomplete_detail",
            "failure_reason": failure,
            "record_path": rel(path) if path.exists() else "",
            "record_sha256": sha256_file(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
        }

    statuses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=HANSARD_ANSWER_DETAIL_WORKERS) as executor:
        futures = [executor.submit(fetch_answer, row) for row in targets]
        for future in as_completed(futures):
            statuses.append(future.result())
    statuses.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_answer_acquisition_status.csv", statuses)

    manifest: list[dict[str, Any]] = []
    for status in statuses:
        if status["download_status"] != "success":
            continue
        detail = read_json(PROJECT_ROOT / status["record_path"])
        record = _hansard_detail_record(detail, status["department"])
        if record is None:
            continue
        external_id = record["external_id"]
        canonical = record["canonical_url"]
        manifest.append(
            {
                "partition_id": status["partition_id"],
                "source": "hansard_api_daily_answer_tree",
                "genre": "ministerial_written_answer",
                "year": int(record["sitting_date"][:4]),
                "date": record["sitting_date"],
                "department": record["department"],
                "external_id": external_id,
                "canonical_url": canonical,
                "title": record["title"],
                "government_respondent": record["government_respondent"],
                "question_count": len(record["questions"]),
                "response_segment_count": len(record["responses"]),
                "attribution_status": record["attribution_status"],
                "record_path": status["record_path"],
                "record_sha256": status["record_sha256"],
                "volume": record.get("volume") or "",
                "updated_at": record.get("content_last_updated") or "",
                "existing_document": str(status.get("existing_document", "")).lower() == "true",
                "identity_status": "official_daily_tree_and_debate_section_ext_id",
            }
        )
    manifest.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_answer_manifest.csv", manifest)

    statements = read_csv(MANIFEST_ROOT / "hansard_statement_manifest.csv")
    statement_partitions = read_csv(MANIFEST_ROOT / "hansard_statement_partitions.csv")
    answer_partitions = read_csv(MANIFEST_ROOT / "hansard_answer_partitions.csv")
    combined = sorted(statements + manifest, key=lambda row: (row["date"], row["genre"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_record_manifest.csv", combined)
    write_csv(MANIFEST_ROOT / "hansard_record_partitions.csv", statement_partitions + answer_partitions)
    statement_summary_path = MANIFEST_ROOT / "hansard_statement_summary.json"
    if not statement_summary_path.exists() and (MANIFEST_ROOT / "hansard_record_summary.json").exists():
        write_json(statement_summary_path, read_json(MANIFEST_ROOT / "hansard_record_summary.json"))

    failed = [row for row in statuses if row["download_status"] != "success"]
    summary = {
        **read_json(MANIFEST_ROOT / "hansard_answer_enumeration_summary.json"),
        "generated_at": now_iso(),
        "target_objects": len(targets),
        "attempted": len(statuses),
        "downloaded": len(statuses) - len(failed),
        "failed": len(failed),
        "eligible_answers": len(manifest),
        "paired_question_context_available": sum(int(row["question_count"]) > 0 for row in manifest),
        "existing_records_after_validation": sum(str(row["existing_document"]).lower() == "true" for row in manifest),
        "net_new_records_after_validation": sum(str(row["existing_document"]).lower() != "true" for row in manifest),
        "by_department_after_validation": dict(Counter(row["department"] for row in manifest)),
    }
    write_json(MANIFEST_ROOT / "hansard_answer_summary.json", summary)
    write_json(
        MANIFEST_ROOT / "hansard_record_summary.json",
        {
            "generated_at": now_iso(),
            "eligible_records": len(combined),
            "answers": len(manifest),
            "statements": len(statements),
            "existing_records": sum(str(row.get("existing_document", "")).lower() == "true" for row in combined),
            "net_new_records": sum(str(row.get("existing_document", "")).lower() != "true" for row in combined),
            "by_department": dict(Counter(row["department"] for row in combined)),
        },
    )
    return summary


def _combine_hansard_gap_manifests() -> None:
    api_answers = read_csv(MANIFEST_ROOT / "hansard_gap_answer_manifest.csv")
    archive_answers = read_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_manifest.csv")
    answer_index: dict[str, dict[str, str]] = {}
    for row in api_answers + archive_answers:
        answer_index.setdefault(row.get("external_id", ""), row)
    answers = sorted(
        (row for external_id, row in answer_index.items() if external_id),
        key=lambda row: (row["date"], row["department"], row["external_id"]),
    )
    statements = read_csv(MANIFEST_ROOT / "hansard_gap_statement_manifest.csv")
    combined = sorted(answers + statements, key=lambda row: (row["date"], row["genre"], row["department"], row["external_id"]))
    # Statements and archive-derived answers do not have identical provenance
    # columns.  Preserve the union explicitly: choosing the first row's fields
    # would silently discard the archive parent request/locator evidence when a
    # statement happens to sort first.
    combined_columns = list(
        dict.fromkeys(
            key
            for row in statements + answers
            for key in row
        )
    )
    partitions = (
        read_csv(MANIFEST_ROOT / "hansard_gap_answer_partitions.csv")
        + read_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_partitions.csv")
        + read_csv(MANIFEST_ROOT / "hansard_gap_statement_partitions.csv")
    )
    write_csv(MANIFEST_ROOT / "hansard_gap_record_manifest.csv", combined, combined_columns)
    write_csv(MANIFEST_ROOT / "hansard_gap_record_partitions.csv", partitions)
    write_json(
        MANIFEST_ROOT / "hansard_gap_record_summary.json",
        {
            "generated_at": now_iso(),
            "eligible_records": len(combined),
            "answers": len(answers),
            "statements": len(statements),
            "existing_records": sum(str(row.get("existing_document", "")).lower() == "true" for row in combined),
            "net_new_records": sum(str(row.get("existing_document", "")).lower() != "true" for row in combined),
            "by_department": dict(Counter(row["department"] for row in combined)),
        },
    )


def probe_hansard_gap_publications_archive() -> dict[str, Any]:
    """Record a bounded, non-bypassing access check for the official archive.

    The current Hansard API explicitly has no written-answer data after April
    2010, while the official publications archive exposes dated Commons answer
    pages for the gap.  Direct scripted requests are checked only against a
    small set of already-identified pages.  A Cloudflare challenge or other
    access restriction is preserved as failure evidence and stops expansion;
    no CAPTCHA, browser-cookie transfer, or access-control workaround is used.
    """
    probes = [
        ("2010-12-01", "https://publications.parliament.uk/pa/cm201011/cmhansrd/cm101201/text/101201w0001.htm"),
        ("2012-01-10", "https://publications.parliament.uk/pa/cm201212/cmhansrd/cm120110/text/120110w0006.htm"),
        ("2013-11-04", "https://publications.parliament.uk/pa/cm201314/cmhansrd/cm131104/text/131104w0001.htm"),
        ("2014-06-12", "https://publications.parliament.uk/pa/cm201415/cmhansrd/cm140612/index/140612-x.htm"),
        ("2014-09-01", "https://publications.parliament.uk/pa/cm201415/cmhansrd/cm140901/index/140901-x.htm"),
    ]
    client = BoundedClient(minimum_interval=0.75, retries=0)
    rows: list[dict[str, Any]] = []
    for sitting_date, url in probes:
        result = client.get(url)
        body_text = result.body.decode("utf-8", errors="replace")
        marker = ""
        if "cf-mitigated" in body_text.lower() or "cloudflare" in body_text.lower():
            marker = "cloudflare_challenge_or_access_restriction"
        elif result.status == 200 and "written answers" in body_text.lower():
            marker = "official_written_answer_page"
        elif result.status == 200:
            marker = "http_200_content_not_validated_as_written_answer_page"
        else:
            marker = f"http_{result.status}_response"
        evidence_path = RAW_ROOT / "hansard_publications_gap" / "access_probes" / sitting_date[:4] / f"{sitting_date}.{result.status or 'network'}.html"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        if result.body:
            temporary = evidence_path.with_suffix(evidence_path.suffix + ".tmp")
            temporary.write_bytes(result.body)
            os.replace(temporary, evidence_path)
        rows.append(
            {
                "sitting_date": sitting_date,
                "request_url": url,
                "final_url": result.final_url,
                "retrieved_at": result.retrieved_at,
                "status_code": result.status,
                "mime_type": result.mime,
                "attempt_count": result.attempts,
                "response_marker": marker,
                "response_path": rel(evidence_path) if evidence_path.exists() else "",
                "response_sha256": sha256_file(evidence_path) if evidence_path.exists() else "",
                "response_byte_size": evidence_path.stat().st_size if evidence_path.exists() else 0,
                "admission_status": "candidate_route_only_not_acquired" if result.status != 200 or marker != "official_written_answer_page" else "readable_probe_only_not_enumerated",
                "failure_reason": result.error or (marker if marker != "official_written_answer_page" else ""),
            }
        )
    write_csv(MANIFEST_ROOT / "hansard_gap_publications_archive_access_status.csv", rows)
    readable = sum(row["admission_status"] == "readable_probe_only_not_enumerated" for row in rows)
    restricted = sum("challenge_or_access_restriction" in row["response_marker"] for row in rows)
    summary = {
        "generated_at": now_iso(),
        "gap_start": HANSARD_GAP_START.isoformat(),
        "gap_end": HANSARD_GAP_END.isoformat(),
        "official_route": "publications.parliament.uk dated Commons Hansard Written Answers pages",
        "probe_targets": len(rows),
        "readable_direct_probes": readable,
        "restricted_direct_probes": restricted,
        "status": "route_identified_but_bulk_acquisition_not_available_without_access_control_workaround" if readable == 0 else "route_probe_readable_but_full_partitions_not_enumerated",
        "action": "proceed_to_bounded_daily_index_enumeration" if readable else "retain_explicit_answer_gap_and_do_not_bypass_access_controls",
        "browser_observation": "A normal browser could render at least the 2010-12-01 official page; this does not supply a per-record scripted fetch status or a complete denominator and is not counted as acquired text.",
    }
    write_json(MANIFEST_ROOT / "hansard_gap_publications_archive_access_summary.json", summary)
    return summary


def _archive_session_candidates(sitting_date: date) -> list[str]:
    """Return bounded official archive directory candidates in priority order."""
    if sitting_date < date(2012, 1, 1):
        primary = "cm201011"
    elif sitting_date < date(2012, 5, 9):
        primary = "cm201212"
    elif sitting_date < date(2013, 5, 8):
        primary = "cm201213"
    elif sitting_date < date(2014, 6, 4):
        primary = "cm201314"
    else:
        primary = "cm201415"
    generic = f"cm{sitting_date.year}{str(sitting_date.year + 1)[-2:]}"
    values = [primary, generic, "cm201011", "cm201012", "cm201212", "cm201213", "cm201314", "cm201415"]
    return list(dict.fromkeys(values))


def _archive_index_url(session: str, sitting_date: date) -> str:
    stamp = sitting_date.strftime("%y%m%d")
    return f"{PUBLICATIONS_ARCHIVE}/pa/{session}/cmhansrd/cm{stamp}/index/{stamp}-x.htm"


def _archive_daily_index_url(session: str, sitting_date: date) -> str:
    """Return the comprehensive daily index used when no dedicated WA index exists."""
    stamp = sitting_date.strftime("%y%m%d")
    return f"{PUBLICATIONS_ARCHIVE}/pa/{session}/cmhansrd/cm{stamp}/indexes/dx{stamp}.html"


def _archive_index_classification(body: bytes) -> str:
    if not body:
        return "invalid"
    soup = BeautifulSoup(body, "html.parser")
    title = normalise_label(soup.title.get_text(" ", strip=True) if soup.title else "")
    body_label = normalise_label(soup.get_text(" ", strip=True))
    dedicated = "WRITTEN ANSWERS INDEX" in title or "HOUSE OF COMMONS WRITTEN ANSWERS" in body_label
    if dedicated:
        return "dedicated_written_answers"
    text_links = soup.find_all(
        "a",
        href=lambda value: bool(value and ("/text/" in str(value) or re.search(r"[ws]\d{4}\.htm", str(value), flags=re.IGNORECASE))),
    )
    daily = bool(text_links) and (
        "ORAL ANSWERS" in body_label
        or "WRITTEN MINISTERIAL STATEMENTS" in body_label
        or "DAILY HANSARD INDEX" in body_label
        or "INDEX TO HOUSE OF COMMONS HANSARD" in body_label
    )
    if daily:
        return "comprehensive_daily_with_written_answers" if "WRITTEN ANSWERS" in body_label else "comprehensive_daily_no_written_answers"
    return "invalid"


def _valid_archive_index(body: bytes) -> bool:
    return _archive_index_classification(body) != "invalid"


def _archive_retry_session_candidates(sitting_date: date) -> list[str]:
    """Return only historically plausible folders for one bounded failed-date retry."""
    if sitting_date < date(2012, 1, 1):
        return ["cm201011", "cm201012"]
    if sitting_date < date(2012, 5, 9):
        return ["cm201212"]
    if sitting_date < date(2013, 5, 8):
        return ["cm201213"]
    if sitting_date < date(2014, 6, 4):
        return ["cm201314"]
    return ["cm201415"]


def _fetch_archive_url(client: BoundedClient, url: str, path: Path, *, resume: bool) -> FetchResult:
    """Reuse a successful bounded access probe before issuing a new request."""
    if resume and not path.exists():
        probe = next(
            (
                row
                for row in read_csv(MANIFEST_ROOT / "hansard_gap_publications_archive_access_status.csv")
                if row.get("request_url") == url
                and int(row.get("status_code") or 0) == 200
                and row.get("response_path")
            ),
            None,
        )
        if probe:
            source = PROJECT_ROOT / probe["response_path"]
            if source.exists() and sha256_file(source) == probe.get("response_sha256"):
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, path)
                write_json(
                    path.with_suffix(path.suffix + ".fetch.json"),
                    {
                        "url": url,
                        "final_url": probe.get("final_url") or url,
                        "status": 200,
                        "mime": probe.get("mime_type") or "text/html",
                        "retrieved_at": probe.get("retrieved_at") or "",
                        "attempts": int(probe.get("attempt_count") or 1),
                        "error": "",
                        "sha256": probe["response_sha256"],
                        "byte_size": int(probe.get("response_byte_size") or source.stat().st_size),
                        "reused_from_bounded_access_probe": probe["response_path"],
                    },
                )
    return fetch_to_path(client, url, path, resume=resume)


def _archive_index_department_links(body: bytes, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(body, "html.parser")
    rows: list[dict[str, str]] = []

    def append_links(department: str, values: Iterable[Any]) -> None:
        for value in values:
            for link in value.find_all("a", href=True):
                href = str(link.get("href") or "")
                if "/text/" not in href and not re.search(r"w\d{4}\.htm", href, flags=re.IGNORECASE):
                    continue
                absolute = urljoin(base_url, href)
                page_url, fragment = urldefrag(absolute)
                rows.append(
                    {
                        "department": department,
                        "page_url": page_url,
                        "fragment": fragment,
                        "index_label": normalise_space(link.get_text(" ", strip=True)),
                    }
                )

    # Dedicated written-answer indexes use exact department h3 headings.
    for heading in soup.find_all("h3"):
        department = normalise_label(heading.get_text(" ", strip=True))
        if department not in HANSARD_GAP_DEPARTMENT_LABELS:
            continue
        candidates = [heading]
        for sibling in heading.next_siblings:
            if getattr(sibling, "name", None) == "h3":
                break
            if getattr(sibling, "name", None):
                candidates.append(sibling)
        append_links(department, candidates)

    # Comprehensive daily indexes contain several business sections.  Start only
    # after the explicit Written Answers row; an earlier identical department can
    # belong to Written Ministerial Statements and must not be attributed here.
    table_rows = soup.find_all("tr")
    written_answers_started = False
    active_department = ""
    for table_row in table_rows:
        row_label = normalise_label(table_row.get_text(" ", strip=True))
        if re.match(r"^WRITTEN ANSWERS\b", row_label):
            written_answers_started = True
            active_department = ""
            continue
        if not written_answers_started:
            continue
        bold_labels = [
            normalise_label(value.get_text(" ", strip=True))
            for value in table_row.find_all(["b", "strong"])
            if normalise_label(value.get_text(" ", strip=True))
        ]
        if bold_labels:
            active_department = bold_labels[0] if bold_labels[0] in HANSARD_GAP_DEPARTMENT_LABELS else ""
        if active_department:
            append_links(active_department, [table_row])

    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        unique[(row["department"], row["page_url"], row["fragment"])] = row
    return sorted(unique.values(), key=lambda row: (row["department"], row["page_url"], row["fragment"]))


def enumerate_hansard_gap_archive_answers(*, resume: bool = True) -> dict[str, Any]:
    """Freeze dated official publications-archive pages for gap-period answers."""
    calendar_rows = read_csv(MANIFEST_ROOT / "hansard_gap_answer_calendar_status.csv")
    prior_status_rows = read_csv(MANIFEST_ROOT / "hansard_gap_archive_index_status.csv") if resume else []
    prior_status_by_date = {row.get("date", ""): row for row in prior_status_rows}
    prior_attempt_rows = read_csv(MANIFEST_ROOT / "hansard_gap_archive_index_attempts.csv") if resume else []
    bounded_failed_date_retry = bool(prior_status_rows)
    sitting_dates = sorted(
        {
            value
            for row in calendar_rows
            if row.get("status") == "success"
            for value in json.loads(row.get("dates_json") or "[]")
            if HANSARD_GAP_START.isoformat() <= value <= HANSARD_GAP_END.isoformat()
        }
    )
    if not sitting_dates:
        raise RuntimeError("No successful official Commons sitting-day calendar available for archive enumeration")
    client = BoundedClient(minimum_interval=2.0 if bounded_failed_date_retry else 0.75)

    def fetch_index(value: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
        sitting = date.fromisoformat(value)
        path = RAW_ROOT / "hansard_publications_gap" / "indexes" / value[:4] / f"{value}.html"
        attempts: list[dict[str, Any]] = []
        links: list[dict[str, str]] = []
        success_result: FetchResult | None = None
        successful_url = ""
        success_classification = ""
        meta_path = path.with_suffix(path.suffix + ".fetch.json")
        if resume and path.exists() and meta_path.exists() and _valid_archive_index(path.read_bytes()):
            meta = read_json(meta_path)
            success_classification = _archive_index_classification(path.read_bytes())
            successful_url = str(meta.get("url") or meta.get("final_url") or "")
            success_result = FetchResult(
                successful_url,
                str(meta.get("final_url") or successful_url),
                int(meta.get("status") or 200),
                str(meta.get("mime") or "text/html"),
                path.read_bytes(),
                str(meta.get("retrieved_at") or ""),
                int(meta.get("attempts") or 1),
                str(meta.get("error") or ""),
            )
            attempts.append(
                {
                    "date": value,
                    "session_candidate": "verified_cached_success",
                    "route_kind": "verified_cached_success",
                    "attempt_phase": "cache_reuse_no_request",
                    "request_url": successful_url,
                    "final_url": success_result.final_url,
                    "retrieved_at": success_result.retrieved_at,
                    "status_code": success_result.status,
                    "mime_type": success_result.mime,
                    "attempt_count": 0,
                    "validation_status": f"{success_classification}_reused_without_request",
                    "failure_reason": "",
                }
            )
            links = _archive_index_department_links(path.read_bytes(), success_result.final_url or successful_url)
        sessions = (
            _archive_retry_session_candidates(sitting)
            if bounded_failed_date_retry and prior_status_by_date.get(value, {}).get("status") != "success"
            else _archive_session_candidates(sitting)
        )
        for session in sessions:
            if success_result is not None:
                break
            route_urls = [
                ("dedicated_written_answers", _archive_index_url(session, sitting)),
                ("comprehensive_daily_index", _archive_daily_index_url(session, sitting)),
            ]
            for route_kind, url in route_urls:
                result = _fetch_archive_url(client, url, path, resume=resume)
                classification = _archive_index_classification(path.read_bytes()) if result.status == 200 and path.exists() else "invalid"
                valid = result.status == 200 and classification != "invalid"
                attempts.append(
                    {
                        "date": value,
                        "session_candidate": session,
                        "route_kind": route_kind,
                        "attempt_phase": "bounded_failed_date_retry" if bounded_failed_date_retry else "initial_enumeration",
                        "request_url": url,
                        "final_url": result.final_url,
                        "retrieved_at": result.retrieved_at,
                        "status_code": result.status,
                        "mime_type": result.mime,
                        "attempt_count": result.attempts,
                        "validation_status": classification if valid else "not_valid_official_hansard_index",
                        "failure_reason": "" if valid else (result.error or "unexpected_html_content"),
                    }
                )
                if valid:
                    success_result = result
                    successful_url = url
                    success_classification = classification
                    links = _archive_index_department_links(path.read_bytes(), result.final_url or url)
                    break
                path.unlink(missing_ok=True)
            if success_result is not None:
                break
        status = {
            "date": value,
            "year": int(value[:4]),
            "request_url": successful_url or (attempts[-1]["request_url"] if attempts else ""),
            "final_url": success_result.final_url if success_result else (attempts[-1]["final_url"] if attempts else ""),
            "retrieved_at": success_result.retrieved_at if success_result else (attempts[-1]["retrieved_at"] if attempts else ""),
            "status_code": success_result.status if success_result else (attempts[-1]["status_code"] if attempts else 0),
            "mime_type": success_result.mime if success_result else (attempts[-1]["mime_type"] if attempts else ""),
            "index_path": rel(path) if path.exists() else "",
            "index_sha256": sha256_file(path) if path.exists() else "",
            "target_department_links": len(links),
            "target_text_pages": len({row["page_url"] for row in links}),
            "index_classification": success_classification,
            "confirmed_no_written_answers": success_classification == "comprehensive_daily_no_written_answers",
            "status": "success" if success_result else "failed",
            "failure_reason": "" if success_result else (attempts[-1]["failure_reason"] if attempts else "not_attempted"),
        }
        return status, attempts, links

    results: list[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for future in as_completed([executor.submit(fetch_index, value) for value in sitting_dates]):
            results.append(future.result())
    results.sort(key=lambda value: value[0]["date"])
    statuses = [value[0] for value in results]
    new_attempts = [row for value in results for row in value[1] if row.get("session_candidate") != "verified_cached_success"]
    if prior_attempt_rows:
        for row in prior_attempt_rows:
            row.setdefault("attempt_phase", "initial_enumeration")
    attempts = prior_attempt_rows + new_attempts
    attempts.sort(key=lambda row: (row["date"], row.get("attempt_phase", ""), row["session_candidate"], row.get("route_kind", "")))
    target_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for status, _, links in results:
        for link in links:
            key = (status["date"], link["department"], link["page_url"])
            target = target_groups.setdefault(
                key,
                {
                    "date": status["date"],
                    "year": status["year"],
                    "department": link["department"],
                    "page_url": link["page_url"],
                    "index_path": status["index_path"],
                    "index_sha256": status["index_sha256"],
                    "fragments": set(),
                    "index_labels": set(),
                },
            )
            if link["fragment"]:
                target["fragments"].add(link["fragment"])
            if link["index_label"]:
                target["index_labels"].add(link["index_label"])
    targets: list[dict[str, Any]] = []
    for target in target_groups.values():
        target = dict(target)
        target["page_target_id"] = stable_id("pgt", target["date"], target["department"], target["page_url"])
        target["fragments_json"] = json.dumps(sorted(target.pop("fragments")), ensure_ascii=False)
        target["index_labels_json"] = json.dumps(sorted(target.pop("index_labels")), ensure_ascii=False)
        targets.append(target)
    targets.sort(key=lambda row: (row["date"], row["department"], row["page_url"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_index_status.csv", statuses)
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_index_attempts.csv", attempts)
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_page_target_manifest.csv", targets)
    summary = {
        "generated_at": now_iso(),
        "sitting_day_index_targets": len(sitting_dates),
        "successful_indexes": sum(row["status"] == "success" for row in statuses),
        "failed_indexes": sum(row["status"] != "success" for row in statuses),
        "confirmed_no_written_answers_indexes": sum(str(row.get("confirmed_no_written_answers", "")).lower() == "true" for row in statuses),
        "indexes_with_target_department_links": sum(int(row.get("target_department_links") or 0) > 0 for row in statuses),
        "target_page_department_assignments": len(targets),
        "unique_target_text_pages": len({row["page_url"] for row in targets}),
        "by_department_page_assignments": dict(Counter(row["department"] for row in targets)),
        "status": "complete_official_sitting_day_index_enumeration" if all(row["status"] == "success" for row in statuses) else "partial_index_enumeration",
        "unit": "official dated archive text page assigned to an approved department; not yet a written-answer record",
    }
    write_json(MANIFEST_ROOT / "hansard_gap_archive_enumeration_summary.json", summary)
    return summary


def _archive_node_locator(node: Any, fallback: str) -> str:
    names = [str(value.get("name") or value.get("id") or "") for value in node.find_all("a")]
    names = [value for value in names if value]
    preferred = next((value for value in names if re.search(r"_wqn\d+$", value, flags=re.IGNORECASE)), "")
    return preferred or next((value for value in names if re.match(r"^(?:qn|st|stpa|qnpa)_", value, flags=re.IGNORECASE)), "") or next((value for value in names if len(value) >= 8), "") or fallback


def _archive_node_text(node: Any) -> tuple[str, str]:
    text = normalise_space(node.get_text(" ", strip=True))
    speaker_node = node.find(["b", "strong"])
    speaker = normalise_space(speaker_node.get_text(" ", strip=True)).rstrip(":") if speaker_node else ""
    body = text
    if speaker:
        match = re.match(rf"^\s*{re.escape(speaker)}\s*:\s*", text, flags=re.IGNORECASE)
        if match:
            body = text[match.end():]
    return speaker, normalise_space(body)


def _archive_heading_fragments(heading: Any) -> set[str]:
    fragments: set[str] = set()
    for link in heading.find_all("a"):
        if link.get("name"):
            fragments.add(str(link["name"]))
        if link.get("id"):
            fragments.add(str(link["id"]))
        if link.get("href"):
            _, fragment = urldefrag(str(link["href"]))
            if fragment:
                fragments.add(fragment)
    for sibling in heading.previous_siblings:
        if not getattr(sibling, "name", None):
            continue
        if sibling.name != "a":
            break
        if sibling.get("name"):
            fragments.add(str(sibling["name"]))
        if sibling.get("id"):
            fragments.add(str(sibling["id"]))
    return fragments


def _archive_topic_records(
    heading: Any,
    *,
    sitting_date: str,
    department: str,
    page_url: str,
    page_path: str,
    page_sha256: str,
) -> list[dict[str, Any]]:
    title = normalise_space(heading.get_text(" ", strip=True)) or "Untitled written answer"
    nodes: list[Any] = []
    for sibling in heading.next_siblings:
        if getattr(sibling, "name", None) == "h3":
            break
        if getattr(sibling, "name", None) in {"p", "table", "ul", "ol", "blockquote"}:
            nodes.append(sibling)
    groups: list[dict[str, Any]] = []
    questions: list[dict[str, str]] = []
    responses: list[dict[str, str]] = []
    response_speaker = ""

    def flush() -> None:
        nonlocal questions, responses, response_speaker
        if responses:
            groups.append(
                {
                    "questions": questions,
                    "responses": responses,
                    "government_respondent": response_speaker,
                }
            )
        questions = []
        responses = []
        response_speaker = ""

    for node_index, node in enumerate(nodes):
        speaker, body = _archive_node_text(node)
        if node.name != "p":
            speaker = ""
        if not body or re.match(r"^\d{1,2}\s+\w+\s+20\d{2}\s*:\s*Column\s+\w+$", body, flags=re.IGNORECASE):
            continue
        locator = _archive_node_locator(node, f"node:{node_index}")
        anchor_names = {
            str(value.get("name") or value.get("id") or "")
            for value in node.find_all("a")
            if value.get("name") or value.get("id")
        }
        question_start = _is_question(body) or any(
            re.match(r"^qn_\d+$", value, flags=re.IGNORECASE) or re.search(r"_wqn\d+$", value, flags=re.IGNORECASE)
            for value in anchor_names
        )
        question_continuation = bool(questions and not responses) and (
            bool(re.match(r"^\(\d+\)\s+", body))
            or any(re.match(r"^qnpa_", value, flags=re.IGNORECASE) for value in anchor_names)
        )
        if question_start:
            if responses:
                flush()
            questions.append({"speaker": speaker, "text": body, "paragraph_id": locator})
            continue
        if question_continuation:
            questions.append({"speaker": speaker, "text": body, "paragraph_id": locator})
            continue
        if not questions and not responses:
            # A topic can continue from the preceding archive page.  Preserve
            # the response as a record with explicitly absent question context
            # rather than assigning text to a fabricated question.
            if not speaker and node.name not in {"table", "ul", "ol", "blockquote"}:
                continue
        if speaker and not response_speaker:
            response_speaker = speaker
        responses.append(
            {
                "speaker": speaker or response_speaker,
                "text": body,
                "paragraph_id": locator,
            }
        )
    flush()
    records: list[dict[str, Any]] = []
    heading_fragments = _archive_heading_fragments(heading)
    for group_index, group in enumerate(groups):
        question_locators = [value["paragraph_id"] for value in group["questions"] if value.get("paragraph_id")]
        official_locator = question_locators[0] if question_locators else next(iter(sorted(heading_fragments)), "")
        if not official_locator:
            official_locator = sha256_bytes(
                canonical_json({"date": sitting_date, "department": department, "title": title, "group": group}).encode()
            )[:20]
        external_id = f"publications_hansard:{sitting_date}:{official_locator}:{group_index}"
        canonical = f"{page_url}#{official_locator}"
        records.append(
            {
                "external_id": external_id,
                "genre": "ministerial_written_answer",
                "house": "Commons",
                "sitting_date": sitting_date,
                "department": department,
                "title": title,
                "questions": group["questions"],
                "responses": group["responses"],
                "canonical_url": canonical,
                "government_respondent": group["government_respondent"],
                "attribution_status": "confirmed" if group["government_respondent"] else "pending",
                "source_category": "Commons Written Answers to Questions",
                "source_anchor": official_locator,
                "source_html_path": page_path,
                "source_html_sha256": page_sha256,
                "question_context_status": "available" if group["questions"] else "continued_from_previous_archive_page_not_available_in_this_record",
            }
        )
    return records


def _archive_records_from_page(
    path: Path,
    *,
    sitting_date: str,
    page_url: str,
    department_fragments: dict[str, set[str]],
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    main = soup.select_one("#maincontent1") or soup.select_one("#maincontent") or soup.body
    if main is None:
        return []
    assigned_departments = set(department_fragments)
    fragment_department = {fragment: department for department, fragments in department_fragments.items() for fragment in fragments}
    records: list[dict[str, Any]] = []
    headings = main.find_all("h3")
    first_department_heading = next(
        (heading for heading in headings if any("dpthd" in value.lower() for value in _archive_heading_fragments(heading))),
        None,
    )
    prefix_fragments: set[str] = set()
    if first_department_heading is not None:
        for element in main.find_all(["a", "h3"]):
            if element is first_department_heading:
                break
            if element.name == "a":
                if element.get("name"):
                    prefix_fragments.add(str(element["name"]))
                if element.get("id"):
                    prefix_fragments.add(str(element["id"]))
    prefix_departments = {
        department
        for department, fragments in department_fragments.items()
        if fragments & prefix_fragments
    }
    active_department = (
        next(iter(prefix_departments))
        if len(prefix_departments) == 1
        else (next(iter(assigned_departments)) if first_department_heading is None and len(assigned_departments) == 1 else "")
    )
    for heading in headings:
        title_label = normalise_label(heading.get_text(" ", strip=True))
        fragments = _archive_heading_fragments(heading)
        is_department_heading = any("dpthd" in value.lower() for value in fragments)
        if title_label in assigned_departments:
            active_department = title_label
            continue
        if is_department_heading:
            active_department = ""
            continue
        matched_departments = {fragment_department[value] for value in fragments if value in fragment_department}
        if title_label in HANSARD_GAP_DEPARTMENT_LABELS:
            continue
        department = active_department
        if not department and len(matched_departments) == 1:
            department = next(iter(matched_departments))
        if not department:
            continue
        records.extend(
            _archive_topic_records(
                heading,
                sitting_date=sitting_date,
                department=department,
                page_url=page_url,
                page_path=rel(path),
                page_sha256=sha256_file(path),
            )
        )
    return records


def acquire_hansard_gap_archive_answers(*, resume: bool = True) -> dict[str, Any]:
    """Acquire and parse the frozen official archive pages for gap answers."""
    targets = read_csv(MANIFEST_ROOT / "hansard_gap_archive_page_target_manifest.csv")
    if not targets:
        raise RuntimeError("Archive page targets have not been enumerated")
    # The first bounded pass showed a high 403 rate at 0.75 seconds despite no
    # 429.  Resume at a materially lower aggregate rate and checkpoint each
    # bounded page block; verified successes are reused from their fetch files.
    client = BoundedClient(minimum_interval=2.0)
    page_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in targets:
        page_groups[(row["date"], row["page_url"])].append(row)

    def fetch_page(key: tuple[str, str]) -> dict[str, Any]:
        sitting_date, url = key
        filename = Path(urldefrag(url)[0]).name
        path = RAW_ROOT / "hansard_publications_gap" / "text" / sitting_date[:4] / sitting_date / filename
        result = _fetch_archive_url(client, url, path, resume=resume)
        valid = bool(
            result.status == 200
            and path.exists()
            and "WRITTEN ANSWERS" in normalise_label(BeautifulSoup(path.read_bytes(), "html.parser").get_text(" ", strip=True)[:5000])
        )
        meta_path = path.with_suffix(path.suffix + ".fetch.json")
        return {
            "date": sitting_date,
            "request_url": url,
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "status_code": result.status,
            "mime_type": result.mime,
            "attempt_count": result.attempts,
            "download_status": "success" if valid else "failed",
            "validation_status": "official_written_answer_html" if valid else "invalid_or_unavailable_html",
            "failure_reason": "" if valid else (result.error or "unexpected_html_content"),
            "raw_path": rel(path) if path.exists() else "",
            "raw_sha256": sha256_file(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
            "fetch_meta_path": rel(meta_path) if meta_path.exists() else "",
            "departments_json": json.dumps(sorted({row["department"] for row in page_groups[key]}), ensure_ascii=False),
        }

    statuses: list[dict[str, Any]] = []
    page_keys = sorted(page_groups)
    page_block_size = 200
    for block_offset in range(0, len(page_keys), page_block_size):
        block = page_keys[block_offset : block_offset + page_block_size]
        with ThreadPoolExecutor(max_workers=2) as executor:
            for future in as_completed([executor.submit(fetch_page, key) for key in block]):
                statuses.append(future.result())
        statuses.sort(key=lambda row: (row["date"], row["request_url"]))
        write_csv(MANIFEST_ROOT / "hansard_gap_archive_page_acquisition_status.csv", statuses)
        write_json(
            CHECKPOINT_ROOT / "hansard_gap_archive_pages.json",
            {
                "generated_at": now_iso(),
                "frozen_unique_text_pages": len(page_keys),
                "status_rows": len(statuses),
                "downloaded_pages": sum(row["download_status"] == "success" for row in statuses),
                "failed_pages": sum(row["download_status"] != "success" for row in statuses),
                "next_offset": block_offset + len(block),
                "block_size": page_block_size,
                "minimum_request_interval_seconds": client.minimum_interval,
            },
        )
        print(
            f"[{now_iso()}] FETCH CHECKPOINT archive_pages status_rows={len(statuses)}/{len(page_keys)} "
            f"downloaded={sum(row['download_status'] == 'success' for row in statuses)} "
            f"failed={sum(row['download_status'] != 'success' for row in statuses)}",
            flush=True,
        )
    status_index = {(row["date"], row["request_url"]): row for row in statuses}
    existing_external, existing_urls, _ = _existing_identity_sets(_enumeration_identity_snapshot())
    manifest: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for key, assignments in sorted(page_groups.items()):
        status = status_index.get(key)
        if not status or status["download_status"] != "success":
            continue
        fragments: dict[str, set[str]] = defaultdict(set)
        for row in assignments:
            fragments[row["department"]].update(json.loads(row.get("fragments_json") or "[]"))
        try:
            page_records = _archive_records_from_page(
                PROJECT_ROOT / status["raw_path"],
                sitting_date=status["date"],
                page_url=status["final_url"] or status["request_url"],
                department_fragments=fragments,
            )
        except Exception as exc:
            parse_errors.append({"date": status["date"], "page_url": status["request_url"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        for record in page_records:
            fingerprint = sha256_bytes(canonical_json(record).encode())
            if record["external_id"] in seen:
                if seen[record["external_id"]] != fingerprint:
                    parse_errors.append({"date": status["date"], "page_url": status["request_url"], "error": f"identity_content_conflict:{record['external_id']}"})
                continue
            seen[record["external_id"]] = fingerprint
            record_path = RAW_ROOT / "hansard_publications_gap" / "derived_records" / record["sitting_date"][:4] / f"{stable_id('hwa', record['external_id'])}.json"
            write_json(record_path, record)
            existing = record["external_id"] in existing_external or record["canonical_url"] in existing_urls
            manifest.append(
                {
                    "partition_id": stable_id("part", "hansard_publications_archive", record["sitting_date"][:4], record["department"]),
                    "source": "official_publications_archive_written_answers",
                    "genre": "ministerial_written_answer",
                    "year": int(record["sitting_date"][:4]),
                    "date": record["sitting_date"],
                    "department": record["department"],
                    "external_id": record["external_id"],
                    "canonical_url": record["canonical_url"],
                    "title": record["title"],
                    "government_respondent": record["government_respondent"],
                    "question_count": len(record["questions"]),
                    "response_segment_count": len(record["responses"]),
                    "attribution_status": record["attribution_status"],
                    "record_path": rel(record_path),
                    "record_sha256": sha256_file(record_path),
                    "parent_raw_path": status["raw_path"],
                    "parent_raw_sha256": status["raw_sha256"],
                    "parent_fetch_meta_path": status["fetch_meta_path"],
                    "parent_request_url": status["request_url"],
                    "parent_final_url": status["final_url"],
                    "parent_retrieved_at": status["retrieved_at"],
                    "parent_status_code": status["status_code"],
                    "parent_mime_type": status["mime_type"],
                    "source_anchor": record["source_anchor"],
                    "existing_document": existing,
                    "identity_status": "official_archive_page_and_question_anchor",
                    "record_is_derived": True,
                }
            )
    manifest.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_manifest.csv", manifest)
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_parse_errors.csv", parse_errors, ["date", "page_url", "error"])
    enumeration_summary = read_json(MANIFEST_ROOT / "hansard_gap_archive_enumeration_summary.json")
    archive_complete = bool(
        enumeration_summary.get("successful_indexes") == enumeration_summary.get("sitting_day_index_targets")
        and all(row["download_status"] == "success" for row in statuses)
        and not parse_errors
    )
    partitions: dict[tuple[int, str], dict[str, Any]] = {}
    for row in manifest:
        key = (int(row["year"]), row["department"])
        value = partitions.setdefault(
            key,
            {
                "partition_id": row["partition_id"],
                "source": row["source"],
                "genre": row["genre"],
                "department": row["department"],
                "year": row["year"],
                "window_start": max(HANSARD_GAP_START, date(int(row["year"]), 1, 1)).isoformat(),
                "window_end": min(HANSARD_GAP_END, date(int(row["year"]), 12, 31)).isoformat(),
                "enumerated_targets": 0,
                "existing_records": 0,
                "net_new_records": 0,
                "status": "complete_official_daily_indexes_and_text_pages" if archive_complete else "partial",
                "status_reason": "Official sitting-day index, exact DEFRA/DECC department links, and question/response anchors preserved." if archive_complete else "One or more official date indexes, linked HTML pages, or parser checks remain incomplete; no continuous-coverage claim.",
            },
        )
        value["enumerated_targets"] += 1
        value["existing_records"] += int(str(row["existing_document"]).lower() == "true")
        value["net_new_records"] += int(str(row["existing_document"]).lower() != "true")
    partition_rows = sorted(partitions.values(), key=lambda row: (int(row["year"]), row["department"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_partitions.csv", partition_rows)
    _combine_hansard_gap_manifests()
    summary = {
        **enumeration_summary,
        "generated_at": now_iso(),
        "attempted_text_pages": len(statuses),
        "downloaded_text_pages": sum(row["download_status"] == "success" for row in statuses),
        "failed_text_pages": sum(row["download_status"] != "success" for row in statuses),
        "unprocessed_text_pages": 0,
        "eligible_answers": len(manifest),
        "confirmed_attribution": sum(row["attribution_status"] == "confirmed" for row in manifest),
        "pending_attribution": sum(row["attribution_status"] != "confirmed" for row in manifest),
        "with_question_context": sum(int(row["question_count"]) > 0 for row in manifest),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in manifest),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in manifest),
        "parse_errors": len(parse_errors),
        "by_department": dict(Counter(row["department"] for row in manifest)),
        "by_year": dict(Counter(str(row["year"]) for row in manifest)),
        "raw_html_is_parent_evidence": True,
        "derived_record_json_is_not_a_separate_http_response": True,
    }
    write_json(MANIFEST_ROOT / "hansard_gap_archive_answer_summary.json", summary)
    combined_answers = read_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_manifest.csv") + read_csv(MANIFEST_ROOT / "hansard_gap_answer_manifest.csv")
    answer_summary = {
        **read_json(MANIFEST_ROOT / "hansard_gap_answer_enumeration_summary.json"),
        "generated_at": now_iso(),
        "discovery_route": "official_publications_archive_daily_indexes_and_exact_department_links_plus_hansard_api_written_candidate_checks",
        "daily_tree_observation": "638/638 successful post-April-2010 Writtens tree responses were empty; not interpreted as zero records",
        "eligible_answer_sections": len(combined_answers),
        "target_objects": len(combined_answers),
        "attempted": len(combined_answers),
        "downloaded": len(combined_answers),
        "failed": int(summary["failed_text_pages"]) + int(summary["unprocessed_text_pages"]),
        "existing_records": sum(str(row.get("existing_document", "")).lower() == "true" for row in combined_answers),
        "net_new_records": sum(str(row.get("existing_document", "")).lower() != "true" for row in combined_answers),
        "by_department": dict(Counter(row["department"] for row in combined_answers)),
        "coverage_status": summary["status"],
    }
    write_json(MANIFEST_ROOT / "hansard_gap_answer_summary.json", answer_summary)
    return summary


def parse_hansard_gap_archive_downloads() -> dict[str, Any]:
    """Parse only saved successful archive pages; never issue a network request."""
    targets = read_csv(MANIFEST_ROOT / "hansard_gap_archive_page_target_manifest.csv")
    statuses = read_csv(MANIFEST_ROOT / "hansard_gap_archive_page_acquisition_status.csv")
    if not targets or not statuses:
        raise RuntimeError("Archive targets or completed page-status checkpoint is unavailable")
    page_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in targets:
        page_groups[(row["date"], row["page_url"])].append(row)
    # Safely reconcile any fully written fetch evidence completed after the
    # last 200-page checkpoint but before the dynamic throttle stop.  This is
    # local-only and never turns an absent request into an attempted request.
    status_index = {(row["date"], row["request_url"]): row for row in statuses}
    for key in sorted(page_groups):
        if key in status_index:
            continue
        sitting_date, url = key
        filename = Path(urldefrag(url)[0]).name
        path = RAW_ROOT / "hansard_publications_gap" / "text" / sitting_date[:4] / sitting_date / filename
        meta_path = path.with_suffix(path.suffix + ".fetch.json")
        if not meta_path.is_file():
            continue
        meta = read_json(meta_path)
        valid = bool(
            int(meta.get("status") or 0) == 200
            and path.is_file()
            and meta.get("sha256") == sha256_file(path)
            and "WRITTEN ANSWERS" in normalise_label(BeautifulSoup(path.read_bytes(), "html.parser").get_text(" ", strip=True)[:5000])
        )
        row = {
            "date": sitting_date,
            "request_url": url,
            "final_url": str(meta.get("final_url") or url),
            "retrieved_at": str(meta.get("retrieved_at") or ""),
            "status_code": int(meta.get("status") or 0),
            "mime_type": str(meta.get("mime") or ""),
            "attempt_count": int(meta.get("attempts") or 1),
            "download_status": "success" if valid else "failed",
            "validation_status": "official_written_answer_html" if valid else "invalid_or_unavailable_html",
            "failure_reason": "" if valid else str(meta.get("error") or "unexpected_html_content"),
            "raw_path": rel(path) if path.is_file() else "",
            "raw_sha256": sha256_file(path) if path.is_file() else "",
            "byte_size": path.stat().st_size if path.is_file() else 0,
            "fetch_meta_path": rel(meta_path),
            "departments_json": json.dumps(sorted({value["department"] for value in page_groups[key]}), ensure_ascii=False),
            "reconciled_after_throttle_stop": True,
        }
        statuses.append(row)
        status_index[key] = row
    statuses.sort(key=lambda row: (row["date"], row["request_url"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_page_acquisition_status.csv", statuses)
    existing_external, existing_urls, _ = _existing_identity_sets(_enumeration_identity_snapshot())
    manifest: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for key, assignments in sorted(page_groups.items()):
        status = status_index.get(key)
        if not status or status["download_status"] != "success":
            continue
        raw_path = PROJECT_ROOT / status["raw_path"]
        if not raw_path.is_file() or sha256_file(raw_path) != status["raw_sha256"]:
            parse_errors.append({"date": status["date"], "page_url": status["request_url"], "error": "saved_parent_missing_or_hash_mismatch"})
            continue
        fragments: dict[str, set[str]] = defaultdict(set)
        for row in assignments:
            fragments[row["department"]].update(json.loads(row.get("fragments_json") or "[]"))
        try:
            page_records = _archive_records_from_page(
                raw_path,
                sitting_date=status["date"],
                page_url=status["final_url"] or status["request_url"],
                department_fragments=fragments,
            )
        except Exception as exc:
            parse_errors.append({"date": status["date"], "page_url": status["request_url"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not page_records:
            parse_errors.append({"date": status["date"], "page_url": status["request_url"], "error": "no_records_parsed_for_target_department_page"})
            continue
        for record in page_records:
            fingerprint = sha256_bytes(canonical_json(record).encode())
            if record["external_id"] in seen:
                if seen[record["external_id"]] != fingerprint:
                    parse_errors.append({"date": status["date"], "page_url": status["request_url"], "error": f"identity_content_conflict:{record['external_id']}"})
                continue
            seen[record["external_id"]] = fingerprint
            record_path = RAW_ROOT / "hansard_publications_gap" / "derived_records" / record["sitting_date"][:4] / f"{stable_id('hwa', record['external_id'])}.json"
            write_json(record_path, record)
            existing = record["external_id"] in existing_external or record["canonical_url"] in existing_urls
            manifest.append(
                {
                    "partition_id": stable_id("part", "hansard_publications_archive", record["sitting_date"][:4], record["department"]),
                    "source": "official_publications_archive_written_answers",
                    "genre": "ministerial_written_answer",
                    "year": int(record["sitting_date"][:4]),
                    "date": record["sitting_date"],
                    "department": record["department"],
                    "external_id": record["external_id"],
                    "canonical_url": record["canonical_url"],
                    "title": record["title"],
                    "government_respondent": record["government_respondent"],
                    "question_count": len(record["questions"]),
                    "response_segment_count": len(record["responses"]),
                    "attribution_status": record["attribution_status"],
                    "record_path": rel(record_path),
                    "record_sha256": sha256_file(record_path),
                    "parent_raw_path": status["raw_path"],
                    "parent_raw_sha256": status["raw_sha256"],
                    "parent_fetch_meta_path": status["fetch_meta_path"],
                    "parent_request_url": status["request_url"],
                    "parent_final_url": status["final_url"],
                    "parent_retrieved_at": status["retrieved_at"],
                    "parent_status_code": status["status_code"],
                    "parent_mime_type": status["mime_type"],
                    "source_anchor": record["source_anchor"],
                    "existing_document": existing,
                    "identity_status": "official_archive_page_and_question_anchor",
                    "record_is_derived": True,
                }
            )
    manifest.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_manifest.csv", manifest)
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_parse_errors.csv", parse_errors, ["date", "page_url", "error"])
    enumeration_summary = read_json(MANIFEST_ROOT / "hansard_gap_archive_enumeration_summary.json")
    archive_complete = bool(
        enumeration_summary.get("successful_indexes") == enumeration_summary.get("sitting_day_index_targets")
        and len(statuses) == len(page_groups)
        and all(row["download_status"] == "success" for row in statuses)
        and not parse_errors
    )
    partitions: dict[tuple[int, str], dict[str, Any]] = {}
    for row in manifest:
        key = (int(row["year"]), row["department"])
        value = partitions.setdefault(
            key,
            {
                "partition_id": row["partition_id"], "source": row["source"], "genre": row["genre"],
                "department": row["department"], "year": row["year"],
                "window_start": max(HANSARD_GAP_START, date(int(row["year"]), 1, 1)).isoformat(),
                "window_end": min(HANSARD_GAP_END, date(int(row["year"]), 12, 31)).isoformat(),
                "enumerated_targets": 0, "existing_records": 0, "net_new_records": 0,
                "status": "complete_official_daily_indexes_and_text_pages" if archive_complete else "partial",
                "status_reason": "Official sitting-day index, exact DEFRA/DECC department sections, and question/response anchors preserved." if archive_complete else "One or more official date indexes, linked HTML pages, or parser checks remain incomplete; no continuous-coverage claim.",
            },
        )
        value["enumerated_targets"] += 1
        value["existing_records"] += int(str(row["existing_document"]).lower() == "true")
        value["net_new_records"] += int(str(row["existing_document"]).lower() != "true")
    write_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_partitions.csv", sorted(partitions.values(), key=lambda row: (int(row["year"]), row["department"])))
    _combine_hansard_gap_manifests()
    summary = {
        **enumeration_summary,
        "generated_at": now_iso(),
        "attempted_text_pages": len(statuses),
        "downloaded_text_pages": sum(row["download_status"] == "success" for row in statuses),
        "failed_text_pages": sum(row["download_status"] != "success" for row in statuses),
        "unprocessed_text_pages": len(page_groups) - len(statuses),
        "eligible_answers": len(manifest),
        "confirmed_attribution": sum(row["attribution_status"] == "confirmed" for row in manifest),
        "pending_attribution": sum(row["attribution_status"] != "confirmed" for row in manifest),
        "with_question_context": sum(int(row["question_count"]) > 0 for row in manifest),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in manifest),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in manifest),
        "parse_errors": len(parse_errors),
        "by_department": dict(Counter(row["department"] for row in manifest)),
        "by_year": dict(Counter(str(row["year"]) for row in manifest)),
        "raw_html_is_parent_evidence": True,
        "derived_record_json_is_not_a_separate_http_response": True,
        "network_requests_in_this_phase": 0,
        "status": "complete" if archive_complete else "partial_with_explicit_gaps",
    }
    write_json(MANIFEST_ROOT / "hansard_gap_archive_answer_summary.json", summary)
    combined_answers = read_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_manifest.csv") + read_csv(MANIFEST_ROOT / "hansard_gap_answer_manifest.csv")
    answer_summary = {
        **read_json(MANIFEST_ROOT / "hansard_gap_answer_enumeration_summary.json"),
        "generated_at": now_iso(),
        "discovery_route": "official_publications_archive_daily_indexes_and_exact_department_sections_plus_hansard_api_written_candidate_checks",
        "daily_tree_observation": "638/638 successful post-April-2010 Writtens tree responses were empty; not interpreted as zero records",
        "eligible_answer_sections": len(combined_answers),
        "target_objects": len(combined_answers),
        "attempted": len(combined_answers),
        "downloaded": len(combined_answers),
        "failed": int(summary["failed_text_pages"]) + int(summary["unprocessed_text_pages"]),
        "existing_records": sum(str(row.get("existing_document", "")).lower() == "true" for row in combined_answers),
        "net_new_records": sum(str(row.get("existing_document", "")).lower() != "true" for row in combined_answers),
        "by_department": dict(Counter(row["department"] for row in combined_answers)),
        "coverage_status": summary["status"],
    }
    write_json(MANIFEST_ROOT / "hansard_gap_answer_summary.json", answer_summary)
    return summary


def enumerate_hansard_gap_answers(*, resume: bool = True) -> dict[str, Any]:
    """Freeze DEFRA/DECC Commons written-answer targets for the 2010–2014 gap."""
    client = BoundedClient(minimum_interval=0.5)
    existing_external, existing_urls, _ = _existing_identity_sets(_enumeration_identity_snapshot())
    calendar_targets: list[tuple[int, int, str, Path]] = []
    cursor = date(HANSARD_GAP_START.year, HANSARD_GAP_START.month, 1)
    while cursor <= HANSARD_GAP_END:
        url = _hansard_calendar_url(cursor.year, cursor.month)
        path = RAW_ROOT / "hansard_api_gap" / "calendars" / str(cursor.year) / f"month_{cursor.month:02d}.json"
        calendar_targets.append((cursor.year, cursor.month, url, path))
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)

    def fetch_calendar(target: tuple[int, int, str, Path]) -> dict[str, Any]:
        year, month, url, path = target
        result, payload, attempts, failure = _fetch_valid_json_payload(client, url, path, lambda value: isinstance(value, list), resume=resume)
        dates = [] if payload is None else sorted(
            {
                str(item.get("ItemDate") or "")[:10]
                for item in payload
                if isinstance(item, dict) and str(item.get("House") or "").lower() == "commons"
            }
        )
        dates = [value for value in dates if HANSARD_GAP_START.isoformat() <= value <= HANSARD_GAP_END.isoformat()]
        return {
            "year": year,
            "month": month,
            "query_url": url,
            "path": rel(path) if path.exists() else "",
            "status_code": result.status,
            "attempt_count": attempts,
            "sitting_days": len(dates),
            "dates_json": json.dumps(dates, ensure_ascii=False),
            "status": "success" if payload is not None else "failed",
            "failure_reason": failure,
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        calendar_statuses = [future.result() for future in as_completed([executor.submit(fetch_calendar, target) for target in calendar_targets])]
    calendar_statuses.sort(key=lambda row: (int(row["year"]), int(row["month"])))
    write_csv(MANIFEST_ROOT / "hansard_gap_answer_calendar_status.csv", calendar_statuses)
    sitting_dates = sorted(
        value
        for row in calendar_statuses
        if row["status"] == "success"
        for value in json.loads(row["dates_json"])
    )

    def fetch_tree(sitting_date: str) -> dict[str, Any]:
        url = _hansard_answer_tree_url(sitting_date)
        path = RAW_ROOT / "hansard_api_gap" / "answer_trees" / sitting_date[:4] / f"{sitting_date}.json"
        result, payload, attempts, failure = _fetch_valid_json_payload(client, url, path, lambda value: isinstance(value, list), resume=resume)
        return {
            "date": sitting_date,
            "year": int(sitting_date[:4]),
            "query_url": url,
            "path": rel(path) if path.exists() else "",
            "path_sha256": sha256_file(path) if path.exists() else "",
            "status_code": result.status,
            "attempt_count": attempts,
            "status": "success" if payload is not None else "failed",
            "failure_reason": failure,
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        tree_statuses = [future.result() for future in as_completed([executor.submit(fetch_tree, value) for value in sitting_dates])]
    tree_statuses.sort(key=lambda row: row["date"])
    write_csv(MANIFEST_ROOT / "hansard_gap_answer_tree_status.csv", tree_statuses)
    targets: list[dict[str, Any]] = []
    for status in tree_statuses:
        if status["status"] != "success" or not status["path"]:
            continue
        for section in read_json(PROJECT_ROOT / status["path"]):
            items = section.get("SectionTreeItems") or [] if isinstance(section, dict) else []
            departments = {
                int(item["Id"]): normalise_label(str(item.get("Title") or ""))
                for item in items
                if str(item.get("HRSTag") or "").lower().endswith("department")
                and normalise_label(str(item.get("Title") or "")) in HANSARD_GAP_DEPARTMENT_LABELS
            }
            for item in items:
                external_id = str(item.get("ExternalId") or "")
                if item.get("ParentId") not in departments or not external_id or "question" not in str(item.get("HRSTag") or "").lower():
                    continue
                department = departments[int(item["ParentId"])]
                title = normalise_space(str(item.get("Title") or "Untitled written answer"))
                sitting_date = status["date"]
                canonical = f"https://hansard.parliament.uk/Commons/{sitting_date}/written-answers/{external_id}/{slugify(title)}"
                targets.append(
                    {
                        "partition_id": stable_id("part", "hansard_gap_answer_tree", sitting_date[:4], department),
                        "source": "hansard_api_daily_answer_tree",
                        "genre": "ministerial_written_answer",
                        "year": int(sitting_date[:4]),
                        "date": sitting_date,
                        "department": department,
                        "external_id": external_id,
                        "canonical_url": canonical,
                        "title": title,
                        "detail_url": f"{HANSARD_API}/debates/debate/{external_id}.json",
                        "tree_path": status["path"],
                        "tree_sha256": status["path_sha256"],
                        "existing_document": external_id in existing_external or canonical in existing_urls,
                        "identity_status": "official_daily_tree_department_and_debate_section_ext_id",
                    }
                )
    unique = {row["external_id"]: row for row in targets}
    targets = sorted(unique.values(), key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_answer_target_manifest.csv", targets)
    partitions: dict[tuple[int, str], dict[str, Any]] = {}
    for row in targets:
        key = (int(row["year"]), row["department"])
        value = partitions.setdefault(
            key,
            {
                "partition_id": row["partition_id"],
                "source": row["source"],
                "genre": row["genre"],
                "department": row["department"],
                "year": row["year"],
                "window_start": max(HANSARD_GAP_START, date(int(row["year"]), 1, 1)).isoformat(),
                "window_end": min(HANSARD_GAP_END, date(int(row["year"]), 12, 31)).isoformat(),
                "enumerated_targets": 0,
                "existing_records": 0,
                "net_new_records": 0,
                "status": "complete_within_successful_daily_section_trees",
                "status_reason": "Exact DEFRA/DECC department nodes and direct written-question children.",
            },
        )
        value["enumerated_targets"] += 1
        existing = str(row["existing_document"]).lower() == "true"
        value["existing_records"] += int(existing)
        value["net_new_records"] += int(not existing)
    partition_rows = sorted(partitions.values(), key=lambda row: (int(row["year"]), row["department"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_answer_partitions.csv", partition_rows)
    summary = {
        "generated_at": now_iso(),
        "calendar_month_targets": len(calendar_targets),
        "calendar_months_successful": sum(row["status"] == "success" for row in calendar_statuses),
        "sitting_days": len(sitting_dates),
        "tree_targets": len(tree_statuses),
        "tree_downloaded": sum(row["status"] == "success" for row in tree_statuses),
        "tree_failed": sum(row["status"] != "success" for row in tree_statuses),
        "eligible_answer_sections": len(targets),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in targets),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in targets),
        "by_department": dict(Counter(row["department"] for row in targets)),
        "by_year": dict(Counter(str(row["year"]) for row in targets)),
        "unit": "official written-answer debate/question section",
    }
    write_json(MANIFEST_ROOT / "hansard_gap_answer_enumeration_summary.json", summary)
    return summary


def acquire_hansard_gap_answer_details(*, resume: bool = True) -> dict[str, Any]:
    """Acquire full question/response details for frozen 2010–2014 gap answers."""
    client = BoundedClient(minimum_interval=0.5)
    targets = [row for row in read_csv(MANIFEST_ROOT / "hansard_gap_answer_target_manifest.csv") if str(row.get("existing_document", "")).lower() != "true"]

    def fetch_answer(row: dict[str, str]) -> dict[str, Any]:
        path = RAW_ROOT / "hansard_api_gap" / "answer_details" / row["year"] / f"{row['external_id']}.json"

        def validator(value: Any) -> bool:
            return (
                isinstance(value, dict)
                and isinstance(value.get("Overview"), dict)
                and str(value["Overview"].get("ExtId") or "") == row["external_id"]
                and isinstance(value.get("Items"), list)
            )

        result, payload, attempts, failure = _fetch_valid_json_payload(client, row["detail_url"], path, validator, resume=resume)
        department = _hansard_department(payload) if payload is not None else ""
        record = _hansard_detail_record(payload, department) if payload is not None else None
        valid = bool(record and department == row["department"] and record["genre"] == "ministerial_written_answer" and record.get("questions") and record.get("responses"))
        if payload is not None and not valid:
            failure = "detail_validation_failed"
        return {
            **row,
            "status_code": result.status,
            "attempt_count": attempts,
            "retrieved_at": result.retrieved_at,
            "download_status": "success" if valid else "failed",
            "validation_status": "full_question_response_and_department_verified" if valid else "invalid_or_incomplete_detail",
            "failure_reason": failure,
            "record_path": rel(path) if path.exists() else "",
            "record_sha256": sha256_file(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = [future.result() for future in as_completed([executor.submit(fetch_answer, row) for row in targets])]
    statuses.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_answer_acquisition_status.csv", statuses)
    manifest = []
    for status in statuses:
        if status["download_status"] != "success":
            continue
        record = _hansard_detail_record(read_json(PROJECT_ROOT / status["record_path"]), status["department"])
        if record is None:
            continue
        manifest.append(
            {
                "partition_id": status["partition_id"], "source": status["source"], "genre": record["genre"],
                "year": int(record["sitting_date"][:4]), "date": record["sitting_date"], "department": record["department"],
                "external_id": record["external_id"], "canonical_url": record["canonical_url"], "title": record["title"],
                "government_respondent": record["government_respondent"], "question_count": len(record["questions"]),
                "response_segment_count": len(record["responses"]), "attribution_status": record["attribution_status"],
                "record_path": status["record_path"], "record_sha256": status["record_sha256"], "volume": record.get("volume") or "",
                "updated_at": record.get("content_last_updated") or "", "existing_document": status["existing_document"],
                "identity_status": status["identity_status"],
            }
        )
    manifest.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_answer_manifest.csv", manifest)
    _combine_hansard_gap_manifests()
    summary = {
        **read_json(MANIFEST_ROOT / "hansard_gap_answer_enumeration_summary.json"),
        "generated_at": now_iso(), "target_objects": len(targets), "attempted": len(statuses),
        "downloaded": sum(row["download_status"] == "success" for row in statuses),
        "failed": sum(row["download_status"] != "success" for row in statuses), "eligible_answers": len(manifest),
    }
    write_json(MANIFEST_ROOT / "hansard_gap_answer_summary.json", summary)
    return summary


def _hansard_gap_written_search_url(year: int, skip: int, take: int = 100) -> str:
    start = max(HANSARD_GAP_START, date(year, 1, 1))
    end = min(HANSARD_GAP_END, date(year, 12, 31))
    params = {
        "queryParameters.house": "Commons",
        "queryParameters.startDate": start.isoformat(),
        "queryParameters.endDate": end.isoformat(),
        "queryParameters.skip": str(skip),
        "queryParameters.take": str(take),
        "queryParameters.orderBy": "SittingDateAsc",
    }
    return f"{HANSARD_API}/search/contributions/Written.json?{urlencode(params)}"


def enumerate_hansard_gap_statement_candidates(*, resume: bool = True) -> dict[str, Any]:
    """Freeze all official Written debate candidates in the uncovered interval."""
    client = BoundedClient(minimum_interval=0.5)
    candidates: dict[str, dict[str, Any]] = {}
    partitions = []
    for year in range(HANSARD_GAP_START.year, HANSARD_GAP_END.year + 1):
        skip = 0
        total: int | None = None
        returned = 0
        raw_paths: list[str] = []
        error = ""
        while True:
            url = _hansard_gap_written_search_url(year, skip)
            path = RAW_ROOT / "hansard_api_gap" / "statement_search" / str(year) / f"page_{skip:06d}.json"
            result, payload, _, failure = _fetch_valid_json_payload(
                client,
                url,
                path,
                lambda value: isinstance(value, dict) and isinstance(value.get("Results"), list) and not value.get("Message"),
                resume=resume,
            )
            if result.status != 200 or payload is None:
                error = failure or result.error or f"HTTP {result.status}"
                break
            observed_total = int(payload.get("TotalResultCount", -1))
            total = observed_total if total is None else total
            if observed_total != total:
                error = f"total_drift:{total}->{observed_total}"
                break
            results = payload.get("Results") or []
            raw_paths.append(rel(path))
            returned += len(results)
            for item in results:
                external_id = str(item.get("DebateSectionExtId") or "")
                if not external_id:
                    continue
                value = candidates.setdefault(
                    external_id,
                    {
                        "candidate_id": external_id,
                        "year": year,
                        "date": str(item.get("SittingDate") or "")[:10],
                        "section": str(item.get("Section") or ""),
                        "title": normalise_space(str(item.get("DebateSection") or "")),
                        "house": str(item.get("House") or ""),
                        "first_attributed_to": normalise_space(str(item.get("AttributedTo") or "")),
                        "search_result_contributions": 0,
                        "search_paths": [],
                    },
                )
                value["search_result_contributions"] += 1
                if rel(path) not in value["search_paths"]:
                    value["search_paths"].append(rel(path))
            skip += len(results)
            if skip >= observed_total or not results:
                break
        start = max(HANSARD_GAP_START, date(year, 1, 1))
        end = min(HANSARD_GAP_END, date(year, 12, 31))
        partitions.append(
            {
                "partition_id": f"hansard_gap_written_candidates_{year}",
                "source": "hansard_search_api",
                "genre": "written_candidates",
                "department": "unresolved_until_detail_navigation",
                "year": year,
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
                "query_url": _hansard_gap_written_search_url(year, 0),
                "initial_total": total if total is not None else -1,
                "returned_count": returned,
                "unique_candidate_debates": sum(value["year"] == year for value in candidates.values()),
                "status": "complete_as_visible" if not error and returned == (total or 0) else "partial",
                "status_reason": error or "All Commons Written candidate pages returned; department and genre verified from detail.",
                "raw_paths_json": json.dumps(raw_paths, ensure_ascii=False),
            }
        )
    rows = []
    for value in sorted(candidates.values(), key=lambda row: (row["date"], row["candidate_id"])):
        value = dict(value)
        value["search_paths_json"] = json.dumps(value.pop("search_paths"), ensure_ascii=False)
        value["detail_url"] = f"{HANSARD_API}/debates/debate/{value['candidate_id']}.json"
        rows.append(value)
    write_csv(MANIFEST_ROOT / "hansard_gap_statement_candidate_manifest.csv", rows)
    write_csv(MANIFEST_ROOT / "hansard_gap_statement_candidate_partitions.csv", partitions)
    summary = {
        "generated_at": now_iso(),
        "contribution_results": sum(max(0, int(row["returned_count"])) for row in partitions),
        "unique_candidate_debates": len(rows),
        "complete_partitions": sum(row["status"] == "complete_as_visible" for row in partitions),
        "partitions": len(partitions),
    }
    write_json(MANIFEST_ROOT / "hansard_gap_statement_candidate_summary.json", summary)
    return summary


def acquire_hansard_gap_statement_details(*, resume: bool = True) -> dict[str, Any]:
    """Acquire gap-period Written candidates and split verified answers/statements.

    Post-April-2010 daily Writtens trees return successful but empty arrays.
    The official Written contribution date search remains available, so its
    deduplicated debate-section IDs form the discovery denominator.  Department
    and genre are then verified from each official detail before admission.
    """
    client = BoundedClient(minimum_interval=0.5)
    candidates = read_csv(MANIFEST_ROOT / "hansard_gap_statement_candidate_manifest.csv")
    existing_external, existing_urls, _ = _existing_identity_sets(_enumeration_identity_snapshot())

    def fetch_candidate(candidate: dict[str, str]) -> dict[str, Any]:
        path = RAW_ROOT / "hansard_api_gap" / "written_details" / candidate["year"] / f"{candidate['candidate_id']}.json"
        result, payload, attempts, failure = _fetch_valid_json_payload(
            client,
            candidate["detail_url"],
            path,
            lambda value: isinstance(value, dict) and isinstance(value.get("Overview"), dict) and isinstance(value.get("Items"), list),
            resume=resume,
        )
        department = _hansard_department(payload) if payload is not None else ""
        record = _hansard_detail_record(payload, department) if payload is not None else None
        genre = record["genre"] if record else ""
        eligible = bool(record and department in HANSARD_GAP_DEPARTMENT_LABELS and genre in {"ministerial_written_answer", "ministerial_written_statement"})
        return {
            **candidate,
            "status_code": result.status,
            "attempt_count": attempts,
            "retrieved_at": result.retrieved_at,
            "download_status": "success" if payload is not None else "failed",
            "failure_reason": failure,
            "detail_path": rel(path) if path.exists() else "",
            "detail_sha256": sha256_file(path) if path.exists() else "",
            "department": department,
            "record_genre": genre,
            "eligible": eligible,
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = [future.result() for future in as_completed([executor.submit(fetch_candidate, row) for row in candidates])]
    statuses.sort(key=lambda row: (row["date"], row["candidate_id"]))
    write_csv(MANIFEST_ROOT / "hansard_gap_written_acquisition_status.csv", statuses)
    manifests: dict[str, list[dict[str, Any]]] = {
        "ministerial_written_answer": [],
        "ministerial_written_statement": [],
    }
    for status in statuses:
        if not status["eligible"] or status["download_status"] != "success":
            continue
        record = _hansard_detail_record(read_json(PROJECT_ROOT / status["detail_path"]), status["department"])
        if record is None:
            continue
        external_id = record["external_id"]
        canonical = record["canonical_url"]
        genre = record["genre"]
        manifests[genre].append(
            {
                "partition_id": stable_id("part", "hansard_gap_written", genre, record["sitting_date"][:4], record["department"]),
                "source": "hansard_api_written_candidate_detail",
                "genre": genre,
                "year": int(record["sitting_date"][:4]),
                "date": record["sitting_date"],
                "department": record["department"],
                "external_id": external_id,
                "canonical_url": canonical,
                "title": record["title"],
                "government_respondent": record["government_respondent"],
                "question_count": len(record["questions"]),
                "response_segment_count": len(record["responses"]),
                "attribution_status": record["attribution_status"],
                "record_path": status["detail_path"],
                "record_sha256": status["detail_sha256"],
                "volume": record.get("volume") or "",
                "updated_at": record.get("content_last_updated") or "",
                "existing_document": external_id in existing_external or canonical in existing_urls,
                "identity_status": "official_debate_section_ext_id",
            }
        )
    for values in manifests.values():
        values.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))

    def write_genre_outputs(genre: str, prefix: str) -> list[dict[str, Any]]:
        manifest = manifests[genre]
        write_csv(MANIFEST_ROOT / f"hansard_gap_{prefix}_manifest.csv", manifest)
        genre_statuses = [row for row in statuses if row.get("record_genre") == genre and row.get("department") in HANSARD_GAP_DEPARTMENT_LABELS]
        write_csv(MANIFEST_ROOT / f"hansard_gap_{prefix}_acquisition_status.csv", genre_statuses)
        partitions: dict[tuple[int, str], dict[str, Any]] = {}
        for row in manifest:
            key = (int(row["year"]), row["department"])
            value = partitions.setdefault(
                key,
                {
                    "partition_id": row["partition_id"], "source": row["source"], "genre": genre,
                    "department": row["department"], "year": row["year"],
                    "window_start": max(HANSARD_GAP_START, date(int(row["year"]), 1, 1)).isoformat(),
                    "window_end": min(HANSARD_GAP_END, date(int(row["year"]), 12, 31)).isoformat(),
                    "enumerated_targets": 0, "existing_records": 0, "net_new_records": 0,
                    "status": "complete_within_verified_written_candidates",
                    "status_reason": "Exact DEFRA/DECC department and genre verified from official debate detail after date-bounded Written candidate enumeration.",
                },
            )
            value["enumerated_targets"] += 1
            existing = str(row["existing_document"]).lower() == "true"
            value["existing_records"] += int(existing)
            value["net_new_records"] += int(not existing)
        partition_rows = sorted(partitions.values(), key=lambda row: (int(row["year"]), row["department"]))
        write_csv(MANIFEST_ROOT / f"hansard_gap_{prefix}_partitions.csv", partition_rows)
        return partition_rows

    write_genre_outputs("ministerial_written_answer", "answer")
    write_genre_outputs("ministerial_written_statement", "statement")
    _combine_hansard_gap_manifests()
    answer_manifest = manifests["ministerial_written_answer"]
    statement_manifest = manifests["ministerial_written_statement"]
    candidate_failed = sum(row["download_status"] != "success" for row in statuses)
    prior_answer = read_json(MANIFEST_ROOT / "hansard_gap_answer_enumeration_summary.json")
    answer_summary = {
        **prior_answer,
        "generated_at": now_iso(),
        "discovery_route": "official_date_bounded_written_contribution_candidates_then_detail_verified",
        "daily_tree_observation": "638/638 successful post-April-2010 Writtens tree responses were empty; not interpreted as zero records",
        "eligible_answer_sections": len(answer_manifest),
        "target_objects": len(answer_manifest),
        "attempted": len(answer_manifest),
        "downloaded": len(answer_manifest),
        "failed": 0,
        "unclassified_candidate_failures": candidate_failed,
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in answer_manifest),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in answer_manifest),
        "by_department": dict(Counter(row["department"] for row in answer_manifest)),
        "by_year": dict(Counter(str(row["year"]) for row in answer_manifest)),
        "paired_question_context_available": sum(int(row["question_count"]) > 0 for row in answer_manifest),
    }
    write_json(MANIFEST_ROOT / "hansard_gap_answer_summary.json", answer_summary)
    summary = {
        "generated_at": now_iso(), "candidate_targets": len(candidates),
        "candidate_downloaded": sum(row["download_status"] == "success" for row in statuses),
        "candidate_failed": candidate_failed,
        "eligible_statements": len(statement_manifest),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" for row in statement_manifest),
        "net_new_records": sum(str(row["existing_document"]).lower() != "true" for row in statement_manifest),
        "by_department": dict(Counter(row["department"] for row in statement_manifest)),
    }
    write_json(MANIFEST_ROOT / "hansard_gap_statement_summary.json", summary)
    return summary


def audit_hansard_gap_statement_failures(*, resume: bool = True) -> dict[str, Any]:
    """Boundedly classify failed Written candidates against the official daily index."""
    failed = [
        row
        for row in read_csv(MANIFEST_ROOT / "hansard_gap_written_acquisition_status.csv")
        if row.get("download_status") != "success"
    ]
    client = BoundedClient(minimum_interval=2.0, retries=1)
    rows: list[dict[str, Any]] = []
    for candidate in failed:
        sitting = date.fromisoformat(candidate["date"])
        path = RAW_ROOT / "hansard_publications_gap" / "statement_failure_audit" / candidate["year"] / f"{candidate['date']}.html"
        result: FetchResult | None = None
        request_url = ""
        classification = "invalid"
        for session in _archive_retry_session_candidates(sitting):
            request_url = _archive_daily_index_url(session, sitting)
            value = _fetch_archive_url(client, request_url, path, resume=resume)
            observed = _archive_index_classification(path.read_bytes()) if value.status == 200 and path.exists() else "invalid"
            if observed.startswith("comprehensive_daily"):
                result = value
                classification = observed
                break
            path.unlink(missing_ok=True)
            result = value
        target_departments: list[str] = []
        all_wms_departments: list[str] = []
        if path.exists() and classification.startswith("comprehensive_daily"):
            soup = BeautifulSoup(path.read_bytes(), "html.parser")
            in_statements = False
            for table_row in soup.find_all("tr"):
                label = normalise_label(table_row.get_text(" ", strip=True))
                if re.match(r"^WRITTEN MINISTERIAL STATEMENTS\b", label):
                    in_statements = True
                    continue
                if in_statements and re.match(r"^(?:PETITION|WRITTEN ANSWERS)\b", label):
                    break
                if not in_statements:
                    continue
                bold = [normalise_label(value.get_text(" ", strip=True)) for value in table_row.find_all(["b", "strong"])]
                if bold and bold[0]:
                    all_wms_departments.append(bold[0])
            target_departments = sorted(set(all_wms_departments) & HANSARD_GAP_DEPARTMENT_LABELS)
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "date": candidate["date"],
                "candidate_title": candidate.get("title") or "",
                "first_attributed_to": candidate.get("first_attributed_to") or "",
                "request_url": request_url,
                "final_url": result.final_url if result else "",
                "retrieved_at": result.retrieved_at if result else "",
                "status_code": result.status if result else 0,
                "mime_type": result.mime if result else "",
                "index_classification": classification,
                "raw_path": rel(path) if path.exists() else "",
                "raw_sha256": sha256_file(path) if path.exists() else "",
                "wms_departments_json": json.dumps(sorted(set(all_wms_departments)), ensure_ascii=False),
                "approved_target_departments_json": json.dumps(target_departments, ensure_ascii=False),
                "scope_resolution": "outside_approved_department_scope" if classification.startswith("comprehensive_daily") and not target_departments else "unresolved_possible_target_scope",
                "failure_reason": "" if classification.startswith("comprehensive_daily") else (result.error if result else "not_attempted"),
            }
        )
    write_csv(MANIFEST_ROOT / "hansard_gap_statement_failure_scope_audit.csv", rows)
    summary = {
        "generated_at": now_iso(),
        "failed_written_candidates_audited": len(rows),
        "official_daily_indexes_acquired": sum(row["index_classification"].startswith("comprehensive_daily") for row in rows),
        "resolved_outside_approved_department_scope": sum(row["scope_resolution"] == "outside_approved_department_scope" for row in rows),
        "unresolved_possible_target_scope": sum(row["scope_resolution"] != "outside_approved_department_scope" for row in rows),
    }
    write_json(MANIFEST_ROOT / "hansard_gap_statement_failure_scope_audit_summary.json", summary)
    return summary


def _modern_partition_bounds(body: dict[str, Any], year: int) -> tuple[date, date] | None:
    start = max(body["start"], date(year, 1, 1))
    end = min(body["end"], date(year, 12, 31), CUTOFF)
    return (start, end) if start <= end else None


def _modern_list_url(genre: str, body_id: int, start: date, end: date, skip: int, take: int) -> str:
    if genre == "ministerial_written_answer":
        endpoint = f"{QUESTIONS_API}/writtenquestions/questions"
        params = {
            "house": "Commons",
            "answeredWhenFrom": start.isoformat(),
            "answeredWhenTo": end.isoformat(),
            "answeringBodies": str(body_id),
            "sessionStatus": "Any",
            "skip": str(skip),
            "take": str(take),
        }
    else:
        endpoint = f"{QUESTIONS_API}/writtenstatements/statements"
        params = {
            "house": "Commons",
            "madeWhenFrom": start.isoformat(),
            "madeWhenTo": end.isoformat(),
            "answeringBodies": str(body_id),
            "sessionStatus": "Any",
            "skip": str(skip),
            "take": str(take),
        }
    return f"{endpoint}?{urlencode(params)}"


def _modern_identity(genre: str, value: dict[str, Any]) -> tuple[str, str, str, str]:
    if genre == "ministerial_written_answer":
        observed_date = str(value.get("dateAnswered") or value.get("dateTabled") or "")[:10]
        external_id = f"written_question:{value.get('id')}"
        title = str(value.get("heading") or value.get("uin") or external_id)
        canonical = f"https://questions-statements.parliament.uk/written-questions/detail/{observed_date}/{value.get('uin')}"
    else:
        observed_date = str(value.get("dateMade") or "")[:10]
        external_id = f"written_statement:{value.get('id')}"
        title = str(value.get("title") or value.get("uin") or external_id)
        canonical = f"https://questions-statements.parliament.uk/written-statements/detail/{observed_date}/{value.get('uin')}"
    return external_id, canonical, observed_date, normalise_space(title)


def enumerate_modern_records(*, resume: bool = True) -> dict[str, Any]:
    """Freeze annual/body/genre targets from the official Questions and Statements API."""
    client = BoundedClient(minimum_interval=0.13)
    existing_external, existing_urls, _ = _existing_identity_sets()
    manifest: list[dict[str, Any]] = []
    partitions: list[dict[str, Any]] = []
    genres = ["ministerial_written_answer", "ministerial_written_statement"]
    for body_id, body in MODERN_BODIES.items():
        for year in range(body["start"].year, body["end"].year + 1):
            bounds = _modern_partition_bounds(body, year)
            if bounds is None:
                continue
            start, end = bounds
            for genre in genres:
                partition_id = stable_id("part", "questions_statements_api", body_id, year, genre)
                skip = 0
                take = 500
                total: int | None = None
                returned = 0
                raw_paths: list[str] = []
                error = ""
                while True:
                    url = _modern_list_url(genre, body_id, start, end, skip, take)
                    short_genre = "answers" if genre.endswith("answer") else "statements"
                    path = RAW_ROOT / "questions_statements_api" / "lists" / short_genre / str(body_id) / str(year) / f"page_{skip:06d}.json"
                    result = fetch_to_path(client, url, path, resume=resume)
                    if result.status != 200 or not path.exists():
                        error = result.error or f"HTTP {result.status}"
                        break
                    payload = read_json(path)
                    observed_total = int(payload.get("totalResults", -1))
                    total = observed_total if total is None else total
                    if observed_total != total:
                        error = f"total_drift:{total}->{observed_total}"
                        break
                    results = payload.get("results") or []
                    if not isinstance(results, list):
                        error = "results_not_list"
                        break
                    raw_paths.append(rel(path))
                    returned += len(results)
                    for wrapper in results:
                        value = wrapper.get("value") if isinstance(wrapper, dict) else None
                        if not isinstance(value, dict):
                            continue
                        observed_body_id = value.get("answeringBodyId")
                        if observed_body_id is None or int(observed_body_id) != body_id:
                            error = f"answering_body_mismatch:requested={body_id};observed={observed_body_id}"
                            continue
                        external_id, canonical, observed_date, title = _modern_identity(genre, value)
                        links = wrapper.get("links") or []
                        self_href = next((str(link.get("href")) for link in links if link.get("rel") == "self"), "")
                        route_id = self_href.rstrip("/").rsplit("/", 1)[-1] if self_href else str(value.get("id") or "")
                        endpoint_root = "writtenquestions/questions" if genre.endswith("answer") else "writtenstatements/statements"
                        detail_url = f"{QUESTIONS_API}/{endpoint_root}/{route_id}?expandMember=true&sessionStatus=Any"
                        manifest.append(
                            {
                                "partition_id": partition_id,
                                "source": "questions_statements_api",
                                "genre": genre,
                                "year": year,
                                "date": observed_date,
                                "department_id": body_id,
                                "department": body["name"],
                                "scope_note": body["scope_note"],
                                "external_id": external_id,
                                "source_record_id": value.get("id"),
                                "api_route_id": route_id,
                                "uin": str(value.get("uin") or ""),
                                "canonical_url": canonical,
                                "title": title,
                                "detail_url": detail_url,
                                "list_path": rel(path),
                                "list_sha256": sha256_file(path),
                                "existing_document": external_id in existing_external or canonical in existing_urls,
                                "identity_status": "official_api_id_and_uin",
                            }
                        )
                    skip += len(results)
                    if skip >= observed_total or not results:
                        break
                partitions.append(
                    {
                        "partition_id": partition_id,
                        "source": "questions_statements_api",
                        "genre": genre,
                        "department_id": body_id,
                        "department": body["name"],
                        "scope_note": body["scope_note"],
                        "year": year,
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "query_url": _modern_list_url(genre, body_id, start, end, 0, take),
                        "initial_total": total if total is not None else -1,
                        "returned_count": returned,
                        "unique_count": returned,
                        "status": "complete_as_visible" if not error and returned == (total or 0) else "partial",
                        "status_reason": error or "All department/year/genre pages returned from the official API",
                        "raw_paths_json": json.dumps(raw_paths, ensure_ascii=False),
                    }
                )
    # Each API record belongs to one answering body.  Deduplicate defensively by genre/source ID.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates = 0
    for row in manifest:
        key = (row["genre"], str(row["source_record_id"]))
        if key in unique:
            duplicates += 1
            continue
        unique[key] = row
    manifest = sorted(unique.values(), key=lambda row: (row["date"], row["genre"], int(row["department_id"]), str(row["source_record_id"])))
    write_csv(MANIFEST_ROOT / "modern_record_manifest.csv", manifest)
    write_csv(MANIFEST_ROOT / "modern_record_partitions.csv", partitions)
    summary = {
        "generated_at": now_iso(),
        "partitions": len(partitions),
        "complete_partitions": sum(row["status"] == "complete_as_visible" for row in partitions),
        "enumerated_targets": len(manifest),
        "answers": sum(row["genre"] == "ministerial_written_answer" for row in manifest),
        "statements": sum(row["genre"] == "ministerial_written_statement" for row in manifest),
        "existing_records": sum(str(row["existing_document"]).lower() == "true" or row["existing_document"] is True for row in manifest),
        "net_new_records": sum(not (str(row["existing_document"]).lower() == "true" or row["existing_document"] is True) for row in manifest),
        "duplicates_removed": duplicates,
        "by_department": dict(Counter(row["department"] for row in manifest)),
    }
    write_json(MANIFEST_ROOT / "modern_record_enumeration_summary.json", summary)
    return summary


def acquire_modern_details(*, resume: bool = True) -> dict[str, Any]:
    """Retrieve full text for every frozen modern API target."""
    client = BoundedClient(minimum_interval=0.5)
    manifest = read_csv(MANIFEST_ROOT / "modern_record_manifest.csv")
    targets = [row for row in manifest if str(row.get("existing_document", "")).lower() != "true"]

    # Resume from terminal successes only.  A status row is accepted as a
    # success checkpoint only when its saved body still exists and matches the
    # recorded digest; every other target remains eligible for a real retry.
    prior_successes: dict[str, dict[str, Any]] = {}
    if resume:
        for row in read_csv(MANIFEST_ROOT / "modern_acquisition_status.csv"):
            record_path = PROJECT_ROOT / str(row.get("record_path") or "")
            if (
                row.get("download_status") == "success"
                and record_path.is_file()
                and row.get("record_sha256")
                and sha256_file(record_path) == row.get("record_sha256")
            ):
                prior_successes[row["external_id"]] = row
    pending_targets = [row for row in targets if row["external_id"] not in prior_successes]

    def fetch_detail(row: dict[str, str]) -> dict[str, Any]:
        short_genre = "answers" if row["genre"].endswith("answer") else "statements"
        path = RAW_ROOT / "questions_statements_api" / "details" / short_genre / str(row["year"]) / f"{row['source_record_id']}.json"
        result = fetch_to_path(client, row["detail_url"], path, resume=resume)
        valid = False
        failure = result.error
        if result.status == 200 and path.exists():
            try:
                payload = read_json(path)
                value = payload.get("value") if isinstance(payload, dict) else None
                value = value if isinstance(value, dict) else payload
                if row["genre"].endswith("answer"):
                    valid = bool(value.get("questionText") and value.get("answerText"))
                    if not valid:
                        failure = "full_question_or_answer_missing"
                else:
                    valid = bool(value.get("text"))
                    if not valid:
                        failure = "full_statement_text_missing"
            except (json.JSONDecodeError, AttributeError) as exc:
                failure = f"invalid_detail_json:{exc}"
        return {
            **row,
            "status_code": result.status,
            "attempt_count": result.attempts,
            "retrieved_at": result.retrieved_at,
            "download_status": "success" if valid else "failed",
            "validation_status": "full_text_present" if valid else "invalid_or_missing_full_text",
            "failure_reason": failure,
            "record_path": rel(path) if path.exists() else "",
            "record_sha256": sha256_file(path) if path.exists() else "",
            "byte_size": path.stat().st_size if path.exists() else 0,
        }

    statuses_by_external_id: dict[str, dict[str, Any]] = dict(prior_successes)
    cooldown_deferred = False
    for block_offset in range(0, len(pending_targets), MODERN_ACQUIRE_BLOCK_SIZE):
        block = pending_targets[block_offset : block_offset + MODERN_ACQUIRE_BLOCK_SIZE]
        with ThreadPoolExecutor(max_workers=MODERN_DETAIL_WORKERS) as executor:
            future_rows = {executor.submit(fetch_detail, row): row for row in block}
            for future in as_completed(future_rows):
                row = future_rows[future]
                try:
                    status = future.result()
                except RateLimitDeferred as exc:
                    status = {
                        **row,
                        "status_code": 429 if exc.requested else 0,
                        "attempt_count": 1 if exc.requested else 0,
                        "retrieved_at": exc.retrieved_at,
                        "download_status": "deferred_after_429" if exc.requested else "deferred_not_requested",
                        "validation_status": "rate_limit_cooldown",
                        "failure_reason": f"Retry-After deferred for {exc.retry_after_seconds:.1f} seconds; resume after cooldown",
                        "record_path": "",
                        "record_sha256": "",
                        "byte_size": 0,
                        "request_url": exc.request_url,
                        "final_url": exc.final_url,
                        "mime_type": exc.mime,
                    }
                    cooldown_deferred = True
                statuses_by_external_id[row["external_id"]] = status
        statuses = sorted(statuses_by_external_id.values(), key=lambda row: (row["date"], row["genre"], row["external_id"]))
        write_csv(MANIFEST_ROOT / "modern_acquisition_status.csv", statuses)
        requested_targets = sum(int(row.get("status_code") or 0) > 0 for row in statuses)
        not_requested_due_to_cooldown = sum(row.get("download_status") == "deferred_not_requested" for row in statuses)
        write_json(
            CHECKPOINT_ROOT / "modern_acquisition.json",
            {
                "generated_at": now_iso(),
                "frozen_targets": len(targets),
                "status_rows": len(statuses),
                "requested_targets": requested_targets,
                "successful_downloads": sum(row["download_status"] == "success" for row in statuses),
                "failed_after_request": sum(
                    row["download_status"] not in {"success", "deferred_not_requested"}
                    for row in statuses
                ),
                "not_requested_due_to_cooldown": not_requested_due_to_cooldown,
                "untouched_targets": len(targets) - len(statuses),
                "pending_target_offset": block_offset + len(block),
                "block_size": MODERN_ACQUIRE_BLOCK_SIZE,
                "status_manifest": rel(MANIFEST_ROOT / "modern_acquisition_status.csv"),
                "stopped_for_cooldown": cooldown_deferred,
            },
        )
        print(
            f"[{now_iso()}] FETCH CHECKPOINT modern status_rows={len(statuses)}/{len(targets)} "
            f"requested={requested_targets} downloaded={sum(row['download_status'] == 'success' for row in statuses)} "
            f"deferred_not_requested={not_requested_due_to_cooldown}",
            flush=True,
        )
        if cooldown_deferred:
            break
    statuses = sorted(statuses_by_external_id.values(), key=lambda row: (row["date"], row["genre"], row["external_id"]))
    summary = {
        "generated_at": now_iso(),
        "target_objects": len(targets),
        "attempted": sum(int(row.get("status_code") or 0) > 0 for row in statuses),
        "downloaded": sum(row["download_status"] == "success" for row in statuses),
        "failed": sum(
            row["download_status"] not in {"success", "deferred_not_requested"}
            for row in statuses
        ),
        "deferred_not_requested": sum(row["download_status"] == "deferred_not_requested" for row in statuses),
        "unprocessed": len(targets) - len(statuses),
        "status": "paused_for_official_cooldown" if cooldown_deferred else "complete",
        "downloaded_bytes": sum(int(row["byte_size"]) for row in statuses if row["download_status"] == "success"),
        "answers_downloaded": sum(row["genre"] == "ministerial_written_answer" and row["download_status"] == "success" for row in statuses),
        "statements_downloaded": sum(row["genre"] == "ministerial_written_statement" and row["download_status"] == "success" for row in statuses),
    }
    write_json(MANIFEST_ROOT / "modern_acquisition_summary.json", summary)
    return summary


def materialize_modern_from_list_pages(*, resume: bool = True) -> dict[str, Any]:
    """Materialise records from already-fetched official list responses.

    The Questions and Statements list endpoint returns the complete question,
    answer, and statement fields.  Each per-record JSON below is therefore a
    derived locator-friendly record, not a fabricated per-record HTTP response.
    """
    manifest = read_csv(MANIFEST_ROOT / "modern_record_manifest.csv")
    status_path = MANIFEST_ROOT / "modern_acquisition_status.csv"
    preserved_detail_path = MANIFEST_ROOT / "modern_detail_request_status_preserved.csv"
    prior_rows = read_csv(status_path)
    detail_rows = [row for row in prior_rows if not row.get("parent_raw_path")]
    if detail_rows and not preserved_detail_path.exists():
        write_csv(preserved_detail_path, detail_rows)
        write_json(
            REPORT_ROOT / "modern_detail_request_stop_record.json",
            {
                "recorded_at": now_iso(),
                "reason": "Official frozen list responses already contain complete text for every enumerated record; redundant per-record detail acquisition was stopped after its first checkpoint.",
                "frozen_target_records": len(manifest),
                "preserved_detail_request_status_rows": len(detail_rows),
                "preserved_successful_detail_responses": sum(row.get("download_status") == "success" for row in detail_rows),
                "preserved_failed_detail_responses": sum(row.get("download_status") != "success" for row in detail_rows),
                "preserved_status_manifest": rel(preserved_detail_path),
                "formal_database_rows_affected": 0,
            },
        )

    completed: dict[str, dict[str, Any]] = {}
    if resume:
        for row in prior_rows:
            record_path = PROJECT_ROOT / str(row.get("record_path") or "")
            if (
                row.get("record_is_derived", "").lower() == "true"
                and row.get("download_status") == "success"
                and record_path.is_file()
                and row.get("record_sha256")
                and sha256_file(record_path) == row.get("record_sha256")
            ):
                completed[row["external_id"]] = row

    parent_cache: dict[str, tuple[dict[str, Any], dict[str, dict[str, Any]]]] = {}

    def parent_payload(row: dict[str, str]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        raw_path = row["list_path"]
        if raw_path in parent_cache:
            return parent_cache[raw_path]
        path = PROJECT_ROOT / raw_path
        meta_path = path.with_suffix(path.suffix + ".fetch.json")
        if not path.is_file() or not meta_path.is_file():
            raise FileNotFoundError(f"Missing official list parent or fetch metadata: {raw_path}")
        meta = read_json(meta_path)
        if int(meta.get("status") or 0) != 200 or meta.get("sha256") != sha256_file(path):
            raise ValueError(f"Unverified official list parent: {raw_path}")
        payload = read_json(path)
        values = {
            str(wrapper.get("value", {}).get("id")): wrapper.get("value", {})
            for wrapper in payload.get("results") or []
            if isinstance(wrapper, dict) and isinstance(wrapper.get("value"), dict)
        }
        parent_cache[raw_path] = (meta, values)
        return parent_cache[raw_path]

    pending = [row for row in manifest if row["external_id"] not in completed]
    statuses_by_external_id: dict[str, dict[str, Any]] = dict(completed)
    failures: list[dict[str, Any]] = []
    for block_offset in range(0, len(pending), MODERN_ACQUIRE_BLOCK_SIZE):
        block = pending[block_offset : block_offset + MODERN_ACQUIRE_BLOCK_SIZE]
        for row in block:
            meta, values = parent_payload(row)
            value = values.get(str(row["source_record_id"]))
            full_text = bool(value and (
                value.get("questionText") and value.get("answerText")
                if row["genre"] == "ministerial_written_answer"
                else value.get("text")
            ))
            if not full_text:
                failures.append(
                    {
                        "external_id": row["external_id"],
                        "source_record_id": row["source_record_id"],
                        "parent_raw_path": row["list_path"],
                        "failure_reason": "official_id_missing_or_required_full_text_absent",
                    }
                )
                continue
            derived_path = RAW_ROOT / "questions_statements_api" / "derived_records" / row["genre"] / row["year"] / f"{stable_id('mrec', row['external_id'])}.json"
            wrapper = {
                "value": value,
                "_derived_record": {
                    "record_is_derived": True,
                    "not_an_independent_http_response": True,
                    "parent_raw_path": row["list_path"],
                    "parent_raw_sha256": meta["sha256"],
                    "parent_request_url": meta["url"],
                    "source_record_id": row["source_record_id"],
                    "source_locator": f"results.value.id={row['source_record_id']}",
                },
            }
            write_json(derived_path, wrapper)
            parent_path = PROJECT_ROOT / row["list_path"]
            parent_meta_path = parent_path.with_suffix(parent_path.suffix + ".fetch.json")
            status = {
                **row,
                # Blank per-record status is intentional: no per-record HTTP
                # request is claimed.  Parent request evidence follows below.
                "status_code": "",
                "attempt_count": 0,
                "retrieved_at": meta.get("retrieved_at") or "",
                "download_status": "success",
                "validation_status": "full_text_present_in_verified_official_list_parent",
                "failure_reason": "",
                "record_path": rel(derived_path),
                "record_sha256": sha256_file(derived_path),
                "byte_size": derived_path.stat().st_size,
                "record_is_derived": True,
                "source_locator": f"results.value.id={row['source_record_id']}",
                "parent_raw_path": row["list_path"],
                "parent_raw_sha256": meta["sha256"],
                "parent_fetch_meta_path": rel(parent_meta_path),
                "parent_request_url": meta["url"],
                "parent_final_url": meta.get("final_url") or meta["url"],
                "parent_retrieved_at": meta.get("retrieved_at") or "",
                "parent_status_code": int(meta["status"]),
                "parent_mime_type": meta.get("mime") or "application/json",
                "parent_byte_size": int(meta.get("byte_size") or parent_path.stat().st_size),
            }
            statuses_by_external_id[row["external_id"]] = status
        statuses = sorted(statuses_by_external_id.values(), key=lambda row: (row["date"], row["genre"], row["external_id"]))
        write_csv(status_path, statuses)
        write_json(
            CHECKPOINT_ROOT / "modern_list_derivation.json",
            {
                "generated_at": now_iso(),
                "frozen_target_records": len(manifest),
                "derived_records_committed_to_status_manifest": len(statuses),
                "failed_records": len(failures),
                "unprocessed_records": len(manifest) - len(statuses) - len(failures),
                "block_size": MODERN_ACQUIRE_BLOCK_SIZE,
                "status_manifest": rel(status_path),
            },
        )
        print(
            f"[{now_iso()}] DERIVATION CHECKPOINT modern records={len(statuses)}/{len(manifest)} failures={len(failures)}",
            flush=True,
        )
    write_csv(
        MANIFEST_ROOT / "modern_list_derivation_failures.csv",
        failures,
        ["external_id", "source_record_id", "parent_raw_path", "failure_reason"],
    )
    parent_paths = {row["list_path"] for row in manifest}
    summary = {
        "generated_at": now_iso(),
        "frozen_target_records": len(manifest),
        "parent_list_page_targets": len(parent_paths),
        "parent_list_pages_downloaded": len(parent_paths),
        "parent_http_requests_reused": len(parent_paths),
        "per_record_http_requests_claimed": 0,
        "records_found_in_parent_responses": len(statuses_by_external_id),
        "derived_records_parsed": len(statuses_by_external_id),
        "failed_records": len(failures),
        "unprocessed_records": len(manifest) - len(statuses_by_external_id) - len(failures),
        "answers_parsed": sum(row["genre"] == "ministerial_written_answer" for row in statuses_by_external_id.values()),
        "statements_parsed": sum(row["genre"] == "ministerial_written_statement" for row in statuses_by_external_id.values()),
        "preserved_detail_request_status_rows": len(detail_rows),
        "derived_record_json_is_not_a_separate_http_response": True,
        "status": "complete" if len(statuses_by_external_id) == len(manifest) and not failures else "partial",
    }
    write_json(MANIFEST_ROOT / "modern_acquisition_summary.json", summary)
    return summary


def _source_definitions() -> dict[str, dict[str, str]]:
    return {
        "policy": {
            "source_id": stable_id("src", "policy", "GOV.UK historical environment climate energy policy papers"),
            "source_name": "GOV.UK — historical environment/climate/energy policy papers",
            "raw_role_label": "government_policy_source_historical_departments",
            "content_type": "policy_paper",
            "access_method": "GOV.UK Search API, Content API, publication pages and attachments",
            "actual_coverage": "DTI, DECC, BERR and DETR-tagged policy_paper records first published 1988-01-01..2009-12-31",
            "docs": [
                "https://www.gov.uk/api/search.json",
                "https://www.gov.uk/api/content",
                "https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html",
            ],
        },
        "historic": {
            "source_id": stable_id("src", "policy", "UK Parliament Historic Hansard Commons written answers statements XML"),
            "source_name": "UK Parliament Historic Hansard — Commons written answers/statements",
            "raw_role_label": "ministerial_parliamentary_record",
            "content_type": "ministerial_written_record",
            "access_method": "Official Report Commons Sixth Series bulk XML and Historic Hansard locators",
            "actual_coverage": "Exact approved department groups in successfully downloaded volumes overlapping 1988-01-01..2004-12-31",
            "docs": [
                "https://api.parliament.uk/historic-hansard/",
                "https://www.hansard-archive.parliament.uk/",
            ],
        },
        "hansard": {
            "source_id": stable_id("src", "policy", "UK Parliament Hansard API Commons written answers statements"),
            "source_name": "UK Parliament Hansard and publications archive — Commons written answers/statements",
            "raw_role_label": "ministerial_parliamentary_record",
            "content_type": "ministerial_written_record",
            "access_method": "Official Hansard API calendars/trees/details plus dated Commons publications-archive indexes and HTML",
            "actual_coverage": "Approved department labels across the recorded 2005-01-01..2014-09-11 API/archive partitions",
            "docs": [
                "https://hansard-api.parliament.uk/swagger/ui/index",
                "https://hansard.parliament.uk/search/WrittenAnswers",
                "https://publications.parliament.uk/pa/cm/cmhansrd.htm",
            ],
        },
        "hansard_gap": {
            "source_id": stable_id("src", "policy", "UK Parliament Hansard API Commons written answers statements"),
            "source_name": "UK Parliament Hansard and publications archive — Commons written answers/statements",
            "raw_role_label": "ministerial_parliamentary_record",
            "content_type": "ministerial_written_record",
            "access_method": "Official Hansard API statement details plus dated Commons publications-archive indexes and written-answer HTML",
            "actual_coverage": "Approved department labels across the recorded 2005-01-01..2014-09-11 API/archive partitions",
            "docs": [
                "https://hansard-api.parliament.uk/swagger/ui/index",
                "https://hansard.parliament.uk/search/WrittenAnswers",
                "https://publications.parliament.uk/pa/cm/cmhansrd.htm",
            ],
        },
        "modern": {
            "source_id": stable_id("src", "policy", "UK Parliament Questions and Statements API relevant answering bodies"),
            "source_name": "UK Parliament Questions and Statements API — relevant Commons answering bodies",
            "raw_role_label": "ministerial_parliamentary_record",
            "content_type": "ministerial_written_record",
            "access_method": "Official complete-text Written Questions and Written Statements API list responses by answering body/year/genre; per-record JSON derived by official ID",
            "actual_coverage": "Commons records for DEFRA, DECC, BEIS, COP26 and DESNZ within documented body lifetimes, 2014-09-12..2026-09-21",
            "docs": [
                "https://questions-statements-api.parliament.uk/index.html",
                "https://api.parliament.uk/written-answers/answering-bodies",
            ],
        },
    }


BATCHES = {
    "policy": "govuk_historical_policy_1988_2009_20260921_v1",
    "historic": "commons_historic_hansard_1988_2004_20260921_v1",
    "hansard": "commons_hansard_api_2005_20100430_20260921_v1",
    "hansard_gap": "commons_hansard_api_20100501_20140911_20260921_v1",
    "modern": "commons_questions_statements_20140912_20260921_v1",
}


def _insert_source(connection: duckdb.DuckDBPyConnection, definition: dict[str, str]) -> None:
    connection.execute(
        """
        INSERT INTO sources VALUES (?, ?, 'policy', ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        ON CONFLICT (source_id) DO UPDATE SET
          source_name=excluded.source_name,
          raw_role_label=excluded.raw_role_label,
          content_type=excluded.content_type,
          access_method=excluded.access_method,
          actual_coverage=excluded.actual_coverage,
          source_documentation_urls=excluded.source_documentation_urls,
          local_source_register_path=excluded.local_source_register_path
        """,
        [
            definition["source_id"],
            definition["source_name"],
            definition["raw_role_label"],
            definition["content_type"],
            definition["access_method"],
            definition["actual_coverage"],
            "official_open_licence_terms_item_exceptions_not_reassessed",
            "Official source terms recorded; item-level exceptions remain possible and raw text is internal only.",
            "Project collection is authorised; no institutional ethics approval/exemption is asserted by this task.",
            canonical_json(definition["docs"]),
            rel(Path(__file__)),
        ],
    )


def _normalisation_rule(connection: duckdb.DuckDBPyConnection) -> str:
    rules = {
        "identity": "Official source ID, then exact official URL; no title-only merge",
        "voice": "Question/context and government response are separate source-extracted segments",
        "dates": "Parliamentary sitting/answer/statement date retained; retrieval/update dates do not replace it",
        "cleaning": "Structure-preserving HTML-to-text extraction and whitespace normalisation only",
        "version": SCRIPT_VERSION,
    }
    payload = canonical_json(rules)
    digest = sha256_bytes(payload.encode())
    row = connection.execute(
        "SELECT rule_sha256 FROM normalisation_rules WHERE rule_version = ?", [NORMALISATION_RULE_VERSION]
    ).fetchone()
    if row and row[0] != digest:
        raise RuntimeError("Normalisation rule changed without a version change")
    connection.execute(
        "INSERT INTO normalisation_rules VALUES (?, ?, ?, 'active') ON CONFLICT DO NOTHING",
        [NORMALISATION_RULE_VERSION, digest, payload],
    )
    return digest


def _new_authorization(connection: duckdb.DuckDBPyConnection) -> str:
    recorded_at = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
    authorization_text = (
        "Dai 已批准补充相关部门历史政策，并纳入独立的部长答复／声明系列；直接推进真实枚举、抓取和入库。"
    )
    authorization_id = stable_id("auth", recorded_at.isoformat(), authorization_text)
    connection.execute(
        """
        INSERT INTO acquisition_authorizations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (authorization_id) DO NOTHING
        """,
        [
            authorization_id,
            recorded_at,
            "Dai Pan",
            authorization_text,
            "Dai direct instruction and approved decision record",
            "docs/decisions/2026-09-21-historical-policy-and-ministerial-series.md",
            "authorized_for_bounded_collection_storage_and_source_text_extraction",
            "not_asserted_no_uq_hrec_approval_or_exemption_recorded",
            "internal_project_collection_storage_and_source_text_extraction_only",
            "raw_full_text_not_authorized_for_public_redistribution",
            canonical_json(
                {
                    "policy": "1988-01-01..2009-12-31 related UK departments",
                    "ministerial": "Commons written answers/statements 1988-01-01..2026-09-21",
                    "excluded": ["proposal edits", "cleaning", "vectorization", "models", "Lords", "oral debates"],
                }
            ),
            "01a0c28b-466f-7a23-b28c-0d66628f6a28",
        ],
    )
    return authorization_id


def _batch_manifest(source_key: str) -> Path:
    return {
        "policy": MANIFEST_ROOT / "policy_manifest.csv",
        "historic": MANIFEST_ROOT / "historic_record_manifest.csv",
        "hansard": MANIFEST_ROOT / "hansard_record_manifest.csv",
        "hansard_gap": MANIFEST_ROOT / "hansard_gap_record_manifest.csv",
        "modern": MANIFEST_ROOT / "modern_record_manifest.csv",
    }[source_key]


def _batch_partitions(source_key: str) -> list[dict[str, str]]:
    path = {
        "policy": MANIFEST_ROOT / "policy_partitions.csv",
        "historic": MANIFEST_ROOT / "historic_record_partitions.csv",
        "hansard": MANIFEST_ROOT / "hansard_record_partitions.csv",
        "hansard_gap": MANIFEST_ROOT / "hansard_gap_record_partitions.csv",
        "modern": MANIFEST_ROOT / "modern_record_partitions.csv",
    }[source_key]
    return read_csv(path)


def _new_manifest_rows(source_key: str) -> list[dict[str, str]]:
    rows = read_csv(_batch_manifest(source_key))
    output = []
    seen: set[str] = set()
    for row in rows:
        external_id = row.get("external_id", "")
        if not external_id or str(row.get("existing_document", "")).lower() == "true" or external_id in seen:
            continue
        if source_key == "policy" and row.get("identity_status") not in {"verified", "duplicate_across_partitions"}:
            continue
        seen.add(external_id)
        output.append(row)
    return output


def _ensure_batch(
    connection: duckdb.DuckDBPyConnection,
    source_key: str,
    source_id: str,
    record_count: int,
) -> None:
    manifest = _batch_manifest(source_key)
    partitions = _batch_partitions(source_key)
    batch_id = BATCHES[source_key]
    bounds = {
        "policy": (POLICY_START, POLICY_END, "first_published_at"),
        "historic": (date(1988, 1, 1), date(2004, 12, 31), "parliamentary_sitting_date"),
        "hansard": (date(2005, 1, 1), date(2010, 4, 30), "parliamentary_sitting_date"),
        "hansard_gap": (HANSARD_GAP_START, HANSARD_GAP_END, "parliamentary_sitting_date"),
        "modern": (date(2014, 9, 12), CUTOFF, "date_answered_or_statement_made"),
    }[source_key]
    reported = sum(max(0, int(row.get("initial_total") or row.get("enumerated_targets") or 0)) for row in partitions)
    complete = all(row.get("status", "").startswith("complete") for row in partitions) if partitions else False
    connection.execute(
        """
        INSERT INTO collection_batches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (batch_id) DO NOTHING
        """,
        [
            batch_id,
            source_id,
            datetime.now(UTC),
            str(partitions[0].get("query_url") or partitions[0].get("source") or "official frozen manifest") if partitions else "official frozen manifest",
            canonical_json({"source_key": source_key, "topic_independent_within_department": True, "script_version": SCRIPT_VERSION}),
            bounds[0],
            bounds[1],
            bounds[2],
            canonical_json({"partition": "source_year_genre_department", "partition_count": len(partitions)}),
            reported,
            record_count,
            "complete_as_visible" if complete else "partial",
            "Frozen source-specific partitions; returned_count is net-new records admitted to this batch.",
            rel(manifest),
            sha256_file(manifest),
            rel(manifest),
            sha256_file(manifest),
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
            "unique publication or ministerial written record",
            reported,
            _source_definitions()[source_key]["actual_coverage"],
            "All records within each recorded official department/year/genre partition; stable official ID deduplication.",
            "This denominator is source-partition coverage, not all UK government discourse; documented source gaps remain.",
            "complete_as_visible" if complete else "partial",
            "source_regime_specific",
            "Historical and modern source regimes overlap or leave gaps; absence of observations is not absence of government speech.",
        ],
    )


def _ensure_query_partitions(connection: duckdb.DuckDBPyConnection, source_key: str) -> None:
    batch_id = BATCHES[source_key]
    for row in _batch_partitions(source_key):
        partition_id = row["partition_id"]
        initial = int(row.get("initial_total") or row.get("enumerated_targets") or 0)
        returned = int(row.get("returned_count") or row.get("enumerated_targets") or 0)
        unique_count = int(row.get("unique_count") or row.get("unique_candidate_debates") or row.get("enumerated_targets") or returned)
        raw_paths = row.get("raw_paths_json") or row.get("source_paths_json") or "[]"
        connection.execute(
            """
            INSERT INTO query_partitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (query_partition_id) DO NOTHING
            """,
            [
                partition_id,
                batch_id,
                date.fromisoformat(row["window_start"]),
                date.fromisoformat(row["window_end"]),
                row.get("query_url") or row.get("source") or "official manifest partition",
                datetime.now(UTC),
                datetime.now(UTC),
                max(1, len(json.loads(raw_paths)) if raw_paths.startswith("[") else 1),
                initial,
                returned,
                unique_count,
                initial,
                row.get("status") or "complete_as_visible",
                row.get("status_reason") or "Frozen source partition",
                raw_paths,
            ],
        )


def _html_segments(value: str) -> list[str]:
    soup = BeautifulSoup(value or "", "html.parser")
    blocks = [normalise_space(element.get_text(" ", strip=True)) for element in soup.find_all(["p", "li", "blockquote"])]
    blocks = [block for block in blocks if block]
    if blocks:
        return blocks
    plain = normalise_space(soup.get_text(" ", strip=True))
    return [plain] if plain else []


def _member_display(value: Any, fallback: str = "") -> str:
    if isinstance(value, dict):
        inner = value.get("value") if isinstance(value.get("value"), dict) else value
        for key in ("nameDisplayAs", "nameFullTitle", "nameListAs", "name"):
            if inner.get(key):
                return normalise_space(str(inner[key]))
    return normalise_space(fallback)


def _load_parliament_record(source_key: str, row: dict[str, str]) -> dict[str, Any]:
    path = PROJECT_ROOT / row["record_path"]
    payload = read_json(path)
    # Targeted repairs may derive a fully structured record from an official
    # list/search response when a section-detail route is broken.  The record
    # remains linked to that parent response; accepting the explicit structure
    # here avoids pretending that the derived JSON was itself downloaded.
    if payload.get("genre") and payload.get("responses") is not None:
        return payload
    if source_key == "historic":
        return payload
    if source_key in {"hansard", "hansard_gap"}:
        record = _hansard_detail_record(payload, row["department"])
        if record is None:
            raise ValueError(f"Could not parse Hansard record {row['external_id']}")
        return record
    value = payload.get("value") if isinstance(payload.get("value"), dict) else payload
    if row["genre"] == "ministerial_written_answer":
        questioner = _member_display(value.get("askingMember"), f"member_id={value.get('askingMemberId')}")
        respondent = _member_display(value.get("answeringMember"), f"member_id={value.get('answeringMemberId')}")
        return {
            "external_id": row["external_id"],
            "genre": row["genre"],
            "house": "Commons",
            "sitting_date": str(value.get("dateAnswered") or row["date"])[:10],
            "department": str(value.get("answeringBodyName") or row["department"]),
            "title": normalise_space(str(value.get("heading") or row["title"])),
            "questions": [{"speaker": questioner, "text": normalise_space(str(value.get("questionText") or "")), "paragraph_id": f"question:{value.get('id')}"}],
            "responses": [
                {"speaker": respondent, "text": text, "paragraph_id": f"answer:{value.get('id')}:{index}"}
                for index, text in enumerate(_html_segments(str(value.get("answerText") or "")), start=1)
            ],
            "canonical_url": row["canonical_url"],
            "government_respondent": respondent,
            "attribution_status": "confirmed" if respondent else "pending",
            "uin": str(value.get("uin") or row.get("uin") or ""),
            "source_category": "Written Question and Answer",
        }
    respondent = _member_display(value.get("member"), str(value.get("memberRole") or ""))
    return {
        "external_id": row["external_id"],
        "genre": row["genre"],
        "house": "Commons",
        "sitting_date": str(value.get("dateMade") or row["date"])[:10],
        "department": str(value.get("answeringBodyName") or row["department"]),
        "title": normalise_space(str(value.get("title") or row["title"])),
        "questions": [],
        "responses": [
            {"speaker": respondent, "text": text, "paragraph_id": f"statement:{value.get('id')}:{index}"}
            for index, text in enumerate(_html_segments(str(value.get("text") or "")), start=1)
        ],
        "canonical_url": row["canonical_url"],
        "government_respondent": respondent,
        "attribution_status": "confirmed" if respondent else "pending",
        "uin": str(value.get("uin") or row.get("uin") or ""),
        "source_category": "Written Ministerial Statement",
    }


def _prepare_policy_rows(
    source_id: str,
    batch_id: str,
    extraction_run_id: str,
    source_rows: list[dict[str, str]],
    acquisition_statuses: list[dict[str, str]],
) -> dict[str, list[tuple[Any, ...]]]:
    from fear_temperature.government_collection import _detect_content_format, _extract_source_text

    manifest_rows = {row["external_id"]: row for row in source_rows}
    rows: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    document_ids: dict[str, str] = {}
    organisation_ids: dict[str, str] = {}
    for external_id, row in manifest_rows.items():
        metadata_path = PROJECT_ROOT / row["metadata_path"]
        metadata = read_json(metadata_path)
        metadata_fetch_path = metadata_path.with_suffix(metadata_path.suffix + ".fetch.json")
        metadata_fetch = read_json(metadata_fetch_path) if metadata_fetch_path.exists() else {}
        acquired_at = (
            datetime.fromisoformat(str(metadata_fetch["retrieved_at"]).replace("Z", "+00:00"))
            if metadata_fetch.get("retrieved_at")
            else datetime.fromtimestamp(metadata_path.stat().st_mtime, UTC)
        )
        normalised_at = datetime.now(UTC)
        raw_json = canonical_json(metadata)
        raw_sha = sha256_bytes(raw_json.encode())
        raw_id = stable_id("raw", batch_id, external_id, raw_sha)
        document_id = stable_id("doc", source_id, external_id)
        document_ids[external_id] = document_id
        publication_timestamp = datetime.fromisoformat(row["first_published_at"].replace("Z", "+00:00"))
        updated_timestamp = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")) if row.get("updated_at") else None
        rows["raw_records"].append((raw_id, batch_id, source_id, external_id, raw_json, raw_sha, acquired_at, row["metadata_path"], row["identity_status"]))
        rows["documents"].append(
            (
                document_id, source_id, external_id, row["canonical_url"], row["title"], str(metadata.get("locale") or "en"),
                publication_timestamp.date(), publication_timestamp, "GOV.UK Content API first_published_at",
                updated_timestamp, acquired_at, "policy", "policy_paper", "document", None, "original",
                "downloaded_pending_extraction", "Net-new historical policy objects acquired from frozen manifest",
                "official_content_id_and_url", "checked_against_existing_06_database",
                "official_open_licence_terms_item_exceptions_not_reassessed", "pending",
                "Project-authorised internal research; institutional ethics status not asserted", True,
            )
        )
        normalised = {
            "external_id": external_id,
            "title": row["title"],
            "canonical_url": row["canonical_url"],
            "first_published_at": row["first_published_at"],
            "updated_at": row.get("updated_at") or None,
            "organisations": [value.get("content_id") for value in (metadata.get("links") or {}).get("organisations") or []],
        }
        normalised_json = canonical_json(normalised)
        version_id = stable_id("docv", document_id, raw_sha, NORMALISATION_RULE_VERSION)
        rows["document_versions"].append((version_id, document_id, NORMALISATION_RULE_VERSION, raw_sha, normalised_json, sha256_bytes(normalised_json.encode()), normalised_at, True))
        rows["document_version_raw_links"].append((version_id, raw_id))
        rows["enumeration_records"].append((batch_id, row["partition_id"], document_id, raw_id, acquired_at, row["identity_status"], row["metadata_path"], row["metadata_sha256"]))
        organisations = (metadata.get("links") or {}).get("organisations") or []
        fraction = 1.0 / len(organisations) if organisations else 1.0
        for org in organisations:
            org_external = str(org.get("content_id") or org.get("base_path") or org.get("title") or "unknown")
            org_id = stable_id("org", "govuk", org_external)
            organisation_ids[org_external] = org_id
            rows["organisations"].append((org_id, org_external, str(org.get("title") or ""), urljoin("https://www.gov.uk", str(org.get("base_path") or ""))))
            rows["document_organisations"].append((document_id, org_id, "govuk_tagged_organisation", "unknown", 1.0, fraction, "official_content_api_link"))

    for status in acquisition_statuses:
        object_id = status["content_object_id"]
        relations = json.loads(status.get("relations_json") or "[]")
        if not any(relation.get("parent_external_id") in manifest_rows for relation in relations):
            continue
        rows["content_objects"].append(
            (
                object_id, status["object_kind"], status.get("external_content_id") or None, status["request_url"],
                status.get("declared_mime_type") or None, int(status["declared_file_size"]) if status.get("declared_file_size") else None,
                int(status["declared_page_count"]) if status.get("declared_page_count") else None,
                "public", "internal_only_not_cleared_for_redistribution", "pending", status.get("title") or "",
                status["download_status"], canonical_json({"source": "govuk", "relations": relations}),
            )
        )
        for relation in relations:
            parent_id = document_ids.get(relation["parent_external_id"])
            if parent_id:
                rows["document_content_objects"].append((parent_id, object_id, "landing_page" if status["object_kind"] == "webpage" else "attachment", int(relation["ordinal"])))
        fetch_id = stable_id("fet", batch_id, object_id)
        retrieved_at = datetime.fromisoformat(status["retrieved_at"].replace("Z", "+00:00"))
        content_version_id = None
        extraction_status = "not_attempted_download_failed"
        extraction_reason = status.get("failure_reason") or "download failed"
        segments: list[dict[str, Any]] = []
        actual_format = ""
        if status["download_status"] == "success" and status.get("raw_path"):
            body = (PROJECT_ROOT / status["raw_path"]).read_bytes()
            actual_format = _detect_content_format(body, status.get("mime_type") or "", status.get("declared_mime_type") or "", status.get("final_url") or status["request_url"])
            extraction_status, extraction_reason, segments = _extract_source_text(body, actual_format)
            content_sha = status["content_sha256"]
            content_version_id = stable_id("cntv", object_id, content_sha)
            rows["content_versions"].append(
                (content_version_id, object_id, content_sha, status.get("final_url") or status["request_url"], retrieved_at,
                 int(status["status_code"]), status.get("mime_type") or "application/octet-stream", int(status["byte_size"]),
                 status["raw_path"], content_sha, fetch_id, "verified")
            )
            for index, segment in enumerate(segments):
                text = str(segment["text"])
                text_sha = sha256_bytes(text.encode())
                segment_id = stable_id("seg", content_version_id, extraction_run_id, index, text_sha)
                rows["text_segments"].append(
                    (segment_id, content_version_id, extraction_run_id, None, "source_extracted", segment.get("segment_kind") or "unknown", index,
                     segment.get("heading"), text, segment.get("locator") or f"segment={index}", None, None, text_sha,
                     "project_authorized_internal_use_institutional_ethics_not_asserted", True, retrieved_at)
                )
        rows["content_fetches"].append(
            (fetch_id, batch_id, object_id, content_version_id, status["request_url"], status.get("final_url") or None, retrieved_at,
             int(status["status_code"]) if status.get("status_code") else None, status.get("mime_type") or None,
             status.get("content_sha256") or None, status.get("raw_path") or None, SCRIPT_VERSION, status["download_status"],
             extraction_status, "internal_only_not_cleared_for_redistribution", status.get("failure_reason") or "")
        )
        rows["acquisition_statuses"].append(
            (batch_id, object_id, fetch_id, content_version_id, status["object_kind"], status.get("declared_mime_type") or None,
             status.get("mime_type") or None, actual_format or None, int(status.get("attempt_count") or 1),
             status.get("request_url") != status.get("final_url"), status["download_status"], status["validation_status"],
             extraction_status, extraction_reason, int(status.get("byte_size") or 0), status.get("content_sha256") or None,
             status.get("raw_path") or None, len(segments), str((PROJECT_ROOT / status["raw_path"]).with_suffix(".checkpoint.json")) if status.get("raw_path") else "",
             retrieved_at)
        )
    return rows


def _parliament_source_rows(source_key: str) -> list[dict[str, str]]:
    if source_key == "modern":
        statuses = [row for row in read_csv(MANIFEST_ROOT / "modern_acquisition_status.csv") if row.get("download_status") == "success"]
        manifest_index = {row["external_id"]: row for row in _new_manifest_rows(source_key)}
        return [{**manifest_index[row["external_id"]], **row} for row in statuses if row["external_id"] in manifest_index]
    return _new_manifest_rows(source_key)


def _historic_volume_context() -> dict[str, dict[str, Any]]:
    statuses = {
        row["raw_path"]: row
        for row in read_csv(MANIFEST_ROOT / "historic_volume_acquisition_status.csv")
        if row.get("download_status") == "success" and row.get("raw_path")
    }
    segment_counts: Counter[str] = Counter()
    record_offsets: dict[str, dict[str, int]] = defaultdict(dict)
    for row in read_csv(MANIFEST_ROOT / "historic_record_manifest.csv"):
        path = row["source_zip_path"]
        record_offsets[path][row["external_id"]] = HISTORIC_REPAIRED_SEGMENT_ORDER_BASE + segment_counts[path]
        segment_counts[path] += int(row.get("question_count") or 0) + int(row.get("response_segment_count") or 0)
    return {
        path: {"fetch": status, "segment_count": segment_counts[path], "record_offsets": record_offsets[path]}
        for path, status in statuses.items()
    }


def _derived_html_context() -> dict[str, dict[str, Any]]:
    """Deterministic per-parent offsets for archive-derived answer records."""
    segment_counts: Counter[str] = Counter()
    record_offsets: dict[str, dict[str, int]] = defaultdict(dict)
    rows = read_csv(MANIFEST_ROOT / "hansard_gap_archive_answer_manifest.csv")
    for row in rows:
        parent_path = row.get("parent_raw_path") or ""
        if not parent_path:
            continue
        record_offsets[parent_path][row["external_id"]] = segment_counts[parent_path]
        segment_counts[parent_path] += int(row.get("question_count") or 0) + int(row.get("response_segment_count") or 0)
    return {
        path: {"segment_count": segment_counts[path], "record_offsets": record_offsets[path]}
        for path in record_offsets
    }


def _derived_list_context() -> dict[str, dict[str, Any]]:
    """Deterministic per-parent offsets for list-response-derived modern records."""
    segment_counts: Counter[str] = Counter()
    record_offsets: dict[str, dict[str, int]] = defaultdict(dict)
    for row in read_csv(MANIFEST_ROOT / "modern_acquisition_status.csv"):
        parent_path = row.get("parent_raw_path") or ""
        if row.get("download_status") != "success" or not parent_path:
            continue
        record = _load_parliament_record("modern", row)
        record_offsets[parent_path][row["external_id"]] = segment_counts[parent_path]
        segment_counts[parent_path] += len(record.get("questions") or []) + len(record.get("responses") or [])
    return {
        path: {"segment_count": segment_counts[path], "record_offsets": record_offsets[path]}
        for path in record_offsets
    }


def _prepare_parliament_rows(
    source_key: str,
    source_id: str,
    batch_id: str,
    extraction_run_id: str,
    source_rows: list[dict[str, str]],
    historic_context: dict[str, dict[str, Any]] | None = None,
) -> dict[str, list[tuple[Any, ...]]]:
    rows: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    organisation_seen: set[str] = set()
    for row in source_rows:
        record = _load_parliament_record(source_key, row)
        if not record.get("responses"):
            continue
        external_id = row["external_id"]
        document_id = stable_id("doc", source_id, external_id)
        raw_path = PROJECT_ROOT / row["record_path"]
        raw_sha = sha256_file(raw_path)
        raw_payload = raw_path.read_text(encoding="utf-8")
        fetch_meta_path = raw_path.with_suffix(raw_path.suffix + ".fetch.json")
        fetch_meta = read_json(fetch_meta_path) if source_key != "historic" and fetch_meta_path.exists() else {}
        derived_list = bool(
            row.get("storage_mode") == "derived_list"
            or (source_key == "modern" and row.get("parent_raw_path"))
        )
        derived_html = bool(
            source_key == "hansard_gap"
            and row.get("parent_raw_path")
            and not derived_list
        )
        if source_key == "historic":
            acquired_at = datetime.fromtimestamp(raw_path.stat().st_mtime, UTC)
            raw_validation = f"derived_record_from_official_bulk_xml;source_zip={row['source_zip_path']};locator={external_id}"
        elif derived_html:
            acquired_at = datetime.fromisoformat(str(row["parent_retrieved_at"]).replace("Z", "+00:00"))
            raw_validation = (
                f"derived_record_from_official_archive_html;source_html={row['parent_raw_path']};"
                f"locator={row.get('source_anchor') or external_id};derived_json_not_http_response"
            )
        elif derived_list:
            acquired_at = datetime.fromisoformat(str(row["parent_retrieved_at"]).replace("Z", "+00:00"))
            raw_validation = (
                f"derived_record_from_official_api_list_response;source_json={row['parent_raw_path']};"
                f"locator={row.get('source_locator') or external_id};derived_json_not_http_response"
            )
        else:
            acquired_at = (
                datetime.fromisoformat(str(fetch_meta["retrieved_at"]).replace("Z", "+00:00"))
                if fetch_meta.get("retrieved_at")
                else datetime.fromtimestamp(raw_path.stat().st_mtime, UTC)
            )
            raw_validation = row.get("identity_status") or "official_id"
        normalised_at = datetime.now(UTC)
        raw_id = stable_id("raw", batch_id, external_id, raw_sha)
        publication_date = date.fromisoformat(record["sitting_date"])
        publication_timestamp = datetime.combine(publication_date, datetime.min.time(), tzinfo=UTC)
        updated_timestamp = None
        if row.get("updated_at"):
            try:
                updated_timestamp = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
            except ValueError:
                updated_timestamp = None
        rows["raw_records"].append((raw_id, batch_id, source_id, external_id, raw_payload, raw_sha, acquired_at, row["record_path"], raw_validation))
        rows["documents"].append(
            (
                document_id, source_id, external_id, row["canonical_url"], record["title"], "en", publication_date,
                publication_timestamp, "official parliamentary date", updated_timestamp, acquired_at, "policy", row["genre"],
                "document", None, "question_response" if row["genre"].endswith("answer") else "ministerial_statement",
                "downloaded_and_extracted", "Official source record with question/context separated from government response",
                row.get("identity_status") or "official_id", "checked_against_existing_06_database",
                "open_parliament_licence_internal_research", "pending",
                "Project-authorised internal research; institutional ethics status not asserted", True,
            )
        )
        normalised = {
            "external_id": external_id,
            "canonical_url": row["canonical_url"],
            "title": record["title"],
            "date": record["sitting_date"],
            "department": record["department"],
            "genre": row["genre"],
            "government_respondent": record.get("government_respondent") or "",
            "uin": record.get("uin") or row.get("uin") or "",
        }
        normalised_json = canonical_json(normalised)
        version_id = stable_id("docv", document_id, raw_sha, NORMALISATION_RULE_VERSION)
        rows["document_versions"].append((version_id, document_id, NORMALISATION_RULE_VERSION, raw_sha, normalised_json, sha256_bytes(normalised_json.encode()), normalised_at, True))
        rows["document_version_raw_links"].append((version_id, raw_id))
        rows["enumeration_records"].append((batch_id, row["partition_id"], document_id, raw_id, acquired_at, raw_validation, row["record_path"], raw_sha))
        department = record["department"] or row["department"]
        org_external = f"uk_parliament_department:{normalise_label(department)}"
        org_id = stable_id("org", org_external)
        if org_external not in organisation_seen:
            rows["organisations"].append((org_id, org_external, department, row["canonical_url"]))
            organisation_seen.add(org_external)
        rows["document_organisations"].append((document_id, org_id, "official_answering_department_or_hansard_group", "confirmed", 1.0, 1.0, "official_source_label"))

        if source_key == "historic":
            source_zip_path = row["source_zip_path"]
            context = (historic_context or {}).get(source_zip_path)
            if context is None:
                raise ValueError(f"Missing successful parent-volume evidence for {external_id}: {source_zip_path}")
            evidence = context["fetch"]
            request_url = evidence["download_url"]
            final_url = evidence.get("final_url") or request_url
            retrieved_at = datetime.fromisoformat(evidence["retrieved_at"].replace("Z", "+00:00"))
            status_code = int(evidence["status_code"])
            mime_type = "application/zip"
            content_sha = evidence["sha256"]
            content_raw_path = evidence["raw_path"]
            content_size = int(evidence["byte_size"])
            # The inherited 06 schema constrains object_kind to webpage or
            # attachment.  Preserve the more specific archive-volume role in
            # identity metadata and the document-content relation.
            object_kind = "attachment"
            external_content_id = evidence["zip_name"]
            object_title = f"Historic Hansard volume {evidence['volume']} part {evidence['part']}"
            object_id = stable_id("cnt", object_kind, final_url)
            relation_role = "attachment"
            validation_status = "valid_zip_xml_parent_of_derived_record"
            actual_format = "zip_xml"
            attempt_count = int(evidence.get("attempt_count") or 1)
            redirected = request_url != final_url
            object_segment_count = int(context["segment_count"])
            checkpoint_path = row["record_path"]
        elif derived_html:
            parent_raw_path = row["parent_raw_path"]
            context = (historic_context or {}).get(parent_raw_path)
            if context is None:
                raise ValueError(f"Missing archive-parent offset context for {external_id}: {parent_raw_path}")
            parent_fetch_meta_path = PROJECT_ROOT / row["parent_fetch_meta_path"]
            parent_fetch = read_json(parent_fetch_meta_path)
            request_url = str(parent_fetch.get("url") or row["parent_request_url"])
            final_url = str(parent_fetch.get("final_url") or row.get("parent_final_url") or request_url)
            retrieved_at = datetime.fromisoformat(str(parent_fetch["retrieved_at"]).replace("Z", "+00:00"))
            status_code = int(parent_fetch.get("status") or row.get("parent_status_code") or 0)
            mime_type = str(parent_fetch.get("mime") or row.get("parent_mime_type") or "text/html")
            content_sha = row["parent_raw_sha256"]
            content_raw_path = parent_raw_path
            content_size = int(parent_fetch.get("byte_size") or (PROJECT_ROOT / parent_raw_path).stat().st_size)
            object_kind = "webpage"
            external_content_id = Path(urldefrag(final_url)[0]).name
            object_title = f"Commons Written Answers archive page {record['sitting_date']}"
            object_id = stable_id("cnt", object_kind, final_url)
            relation_role = "landing_page"
            validation_status = "valid_official_html_parent_of_derived_record"
            actual_format = "html"
            attempt_count = int(parent_fetch.get("attempts") or 1)
            redirected = request_url != final_url
            object_segment_count = int(context["segment_count"])
            checkpoint_path = row["parent_fetch_meta_path"]
        elif derived_list:
            parent_raw_path = row["parent_raw_path"]
            context = (historic_context or {}).get(parent_raw_path)
            if context is None:
                raise ValueError(f"Missing list-parent offset context for {external_id}: {parent_raw_path}")
            parent_fetch_meta_path = PROJECT_ROOT / row["parent_fetch_meta_path"]
            parent_fetch = read_json(parent_fetch_meta_path)
            request_url = str(parent_fetch.get("url") or row["parent_request_url"])
            final_url = str(parent_fetch.get("final_url") or row.get("parent_final_url") or request_url)
            retrieved_at = datetime.fromisoformat(str(parent_fetch["retrieved_at"]).replace("Z", "+00:00"))
            status_code = int(parent_fetch.get("status") or row.get("parent_status_code") or 0)
            mime_type = str(parent_fetch.get("mime") or row.get("parent_mime_type") or "application/json")
            content_sha = row["parent_raw_sha256"]
            content_raw_path = parent_raw_path
            content_size = int(parent_fetch.get("byte_size") or (PROJECT_ROOT / parent_raw_path).stat().st_size)
            object_kind = "webpage"
            external_content_id = stable_id("api-list", request_url)
            object_title = f"Questions and Statements API list response {row['department']} {row['year']}"
            object_id = stable_id("cnt", object_kind, final_url)
            relation_role = "landing_page"
            validation_status = "valid_official_json_list_parent_of_derived_record"
            actual_format = "json"
            attempt_count = int(parent_fetch.get("attempts") or 1)
            redirected = request_url != final_url
            object_segment_count = int(context["segment_count"])
            checkpoint_path = row["parent_fetch_meta_path"]
        else:
            request_url = str(fetch_meta.get("url") or row.get("detail_url") or row["canonical_url"])
            final_url = str(fetch_meta.get("final_url") or request_url)
            retrieved_at = acquired_at
            status_code = int(fetch_meta.get("status") or 0)
            mime_type = str(fetch_meta.get("mime") or "application/json")
            content_sha = raw_sha
            content_raw_path = row["record_path"]
            content_size = int(fetch_meta.get("byte_size") or raw_path.stat().st_size)
            object_kind = "webpage"
            external_content_id = external_id
            object_title = record["title"]
            object_id = stable_id("cnt", object_kind, row["canonical_url"])
            relation_role = "landing_page"
            validation_status = "official_detail_response_with_full_text"
            actual_format = "json"
            attempt_count = int(fetch_meta.get("attempts") or 1)
            redirected = request_url != final_url
            object_segment_count = 0
            checkpoint_path = str(fetch_meta_path.relative_to(PROJECT_ROOT)) if fetch_meta_path.exists() else row["record_path"]
        rows["content_objects"].append(
            (object_id, object_kind, external_content_id, final_url, mime_type,
             content_size, None, "public", "internal_only_not_cleared_for_redistribution", "pending",
             object_title, "success", canonical_json({"source_key": source_key, "department": department, "genre": row["genre"], "record_is_derived": source_key == "historic" or derived_html or derived_list}))
        )
        rows["document_content_objects"].append((document_id, object_id, relation_role, 0))
        fetch_id = stable_id("fet", batch_id, object_id)
        content_version_id = stable_id("cntv", object_id, content_sha)
        rows["content_versions"].append(
            (content_version_id, object_id, content_sha, final_url, retrieved_at, status_code,
             mime_type, content_size, content_raw_path, content_sha, fetch_id, "verified")
        )
        rows["content_fetches"].append(
            (fetch_id, batch_id, object_id, content_version_id, request_url, final_url, retrieved_at, status_code,
             mime_type, content_sha, content_raw_path, SCRIPT_VERSION,
             "success", "success", "internal_only_not_cleared_for_redistribution", "")
        )
        segment_order = int(context["record_offsets"][external_id]) if source_key == "historic" or derived_html or derived_list else 0
        for role, values in (("question_context", record.get("questions") or []), ("government_response", record.get("responses") or [])):
            for value in values:
                text = normalise_space(str(value.get("text") or ""))
                if not text:
                    continue
                text_sha = sha256_bytes(text.encode())
                segment_id = stable_id("seg", content_version_id, extraction_run_id, document_id, segment_order, text_sha)
                locator = (
                    f"role={role};source_id={value.get('paragraph_id') or segment_order};"
                    f"speaker={normalise_space(str(value.get('speaker') or 'unknown'))}"
                )
                heading = "Question/context — excluded from government-response counts" if role == "question_context" else (
                    "Ministerial written statement" if row["genre"].endswith("statement") else "Government response"
                )
                rows["text_segments"].append(
                    (segment_id, content_version_id, extraction_run_id, None, "source_extracted", "paragraph", segment_order,
                     heading, text, locator, None, None, text_sha,
                     "project_authorized_internal_use_institutional_ethics_not_asserted", True, normalised_at)
                )
                speaker = normalise_space(str(value.get("speaker") or "")) or None
                rows["voice_attributions"].append(
                    (stable_id("att", document_id, segment_id, role), document_id, segment_id, speaker, "quoted_speaker", locator,
                     "confirmed" if speaker else "pending")
                )
                segment_order += 1
        rows["acquisition_statuses"].append(
            (batch_id, object_id, fetch_id, content_version_id, object_kind, mime_type,
             mime_type, actual_format, attempt_count, redirected, "success", validation_status, "success",
             "Question/context and government response extracted into separate source segments", content_size, content_sha,
             content_raw_path, object_segment_count or segment_order, checkpoint_path, normalised_at)
        )
    return rows


def _execute_many(connection: duckdb.DuckDBPyConnection, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        connection.executemany(sql, rows)


def _dedupe_by(rows: list[tuple[Any, ...]], indexes: tuple[int, ...]) -> list[tuple[Any, ...]]:
    output: list[tuple[Any, ...]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = tuple(row[index] for index in indexes)
        if key not in seen:
            seen.add(key)
            output.append(row)
    return output


def _bulk_insert(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    rows: list[tuple[Any, ...]],
    conflict_sql: str = "ON CONFLICT DO NOTHING",
) -> None:
    if not rows:
        return
    columns = [str(row[0]) for row in connection.execute(f"DESCRIBE {table}").fetchall()]
    frame = pd.DataFrame.from_records(rows, columns=columns)
    view_name = f"_bounded_chunk_{table}"
    connection.register(view_name, frame)
    try:
        connection.execute(f"INSERT INTO {table} SELECT * FROM {view_name} {conflict_sql}")
    finally:
        connection.unregister(view_name)


def _insert_prepared_chunk(connection: duckdb.DuckDBPyConnection, prepared: dict[str, list[tuple[Any, ...]]]) -> None:
    """Insert one bounded chunk in foreign-key dependency order."""
    _bulk_insert(connection, "raw_records", prepared["raw_records"])
    _bulk_insert(connection, "documents", prepared["documents"])
    _bulk_insert(connection, "document_versions", prepared["document_versions"])
    _bulk_insert(connection, "document_version_raw_links", prepared["document_version_raw_links"])
    _bulk_insert(connection, "enumeration_records", prepared["enumeration_records"])
    _bulk_insert(connection, "organisations", _dedupe_by(prepared["organisations"], (0,)))
    _bulk_insert(connection, "document_organisations", prepared["document_organisations"])
    _bulk_insert(
        connection,
        "content_objects",
        _dedupe_by(prepared["content_objects"], (0,)),
        "ON CONFLICT (content_object_id) DO UPDATE SET acquisition_status = excluded.acquisition_status",
    )
    _bulk_insert(connection, "document_content_objects", prepared["document_content_objects"])
    _bulk_insert(connection, "content_versions", _dedupe_by(prepared["content_versions"], (0,)))
    _bulk_insert(connection, "content_fetches", _dedupe_by(prepared["content_fetches"], (0,)))
    _bulk_insert(connection, "text_segments", prepared["text_segments"])
    _bulk_insert(connection, "voice_attributions", prepared["voice_attributions"])
    _bulk_insert(connection, "acquisition_object_statuses", _dedupe_by(prepared["acquisition_statuses"], (0, 1)))


def _write_ingestion_progress(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    policy_enum = read_json(MANIFEST_ROOT / "policy_enumeration_summary.json")
    historic_enum = read_json(MANIFEST_ROOT / "historic_record_enumeration_summary.json")
    hansard_answer = read_json(MANIFEST_ROOT / "hansard_answer_enumeration_summary.json")
    modern_enum = read_json(MANIFEST_ROOT / "modern_record_enumeration_summary.json")
    hansard_statements = read_csv(MANIFEST_ROOT / "hansard_statement_manifest.csv")
    hansard_manifest = read_csv(MANIFEST_ROOT / "hansard_record_manifest.csv")
    hansard_answer_status = read_csv(MANIFEST_ROOT / "hansard_answer_acquisition_status.csv")
    gap_answer_summary_path = MANIFEST_ROOT / "hansard_gap_answer_summary.json"
    gap_answer_fallback_path = MANIFEST_ROOT / "hansard_gap_answer_enumeration_summary.json"
    gap_answer_summary = read_json(gap_answer_summary_path) if gap_answer_summary_path.exists() else (read_json(gap_answer_fallback_path) if gap_answer_fallback_path.exists() else {})
    gap_statement_summary_path = MANIFEST_ROOT / "hansard_gap_statement_summary.json"
    gap_statement_summary = read_json(gap_statement_summary_path) if gap_statement_summary_path.exists() else {}
    gap_manifest = read_csv(MANIFEST_ROOT / "hansard_gap_record_manifest.csv")
    gap_answer_status = read_csv(MANIFEST_ROOT / "hansard_gap_answer_acquisition_status.csv")
    gap_statement_status = read_csv(MANIFEST_ROOT / "hansard_gap_statement_acquisition_status.csv")
    gap_written_status = read_csv(MANIFEST_ROOT / "hansard_gap_written_acquisition_status.csv")
    gap_archive_summary = read_json(MANIFEST_ROOT / "hansard_gap_archive_answer_summary.json") if (MANIFEST_ROOT / "hansard_gap_archive_answer_summary.json").exists() else {}
    modern_status = read_csv(MANIFEST_ROOT / "modern_acquisition_status.csv")
    source_specs = {
        "policy": {
            "frozen_target_records": int(policy_enum.get("net_new_records", 0)),
            "original_text_acquired_records": int(policy_enum.get("net_new_records", 0)),
            "parsed_records": int(policy_enum.get("net_new_records", 0)),
            "failed_or_retry_objects": int(read_json(MANIFEST_ROOT / "policy_acquisition_summary.json").get("failed", 0)),
        },
        "historic": {
            "frozen_target_records": int(historic_enum.get("enumerated_targets", 0)),
            "original_text_acquired_records": int(historic_enum.get("enumerated_targets", 0)),
            "parsed_records": int(historic_enum.get("enumerated_targets", 0)),
            "failed_or_retry_objects": int(read_json(MANIFEST_ROOT / "historic_volume_acquisition_summary.json").get("failed", 0)),
        },
        "hansard": {
            "frozen_target_records": int(hansard_answer.get("net_new_records", 0)) + len(hansard_statements),
            "original_text_acquired_records": len(hansard_manifest),
            "parsed_records": len(hansard_manifest),
            "failed_or_retry_objects": sum(row.get("download_status") != "success" for row in read_csv(MANIFEST_ROOT / "hansard_candidate_acquisition_status.csv")) + sum(row.get("download_status") != "success" for row in hansard_answer_status),
            "failed_target_records": sum(row.get("download_status") != "success" for row in hansard_answer_status),
        },
        "hansard_gap": {
            "frozen_target_records": int(gap_answer_summary.get("net_new_records", gap_answer_summary.get("target_records", 0))) + int(gap_statement_summary.get("net_new_records", gap_statement_summary.get("eligible_statements", 0))),
            "original_text_acquired_records": len(gap_manifest),
            "parsed_records": len(gap_manifest),
            "failed_or_retry_objects": (
                (sum(row.get("download_status") != "success" for row in gap_written_status) if gap_written_status else sum(row.get("download_status") != "success" for row in gap_answer_status) + sum(row.get("download_status") != "success" for row in gap_statement_status))
                + int(gap_archive_summary.get("failed_indexes", 0))
                + int(gap_archive_summary.get("failed_text_pages", 0))
            ),
            "unprocessed_source_objects": int(gap_archive_summary.get("unprocessed_text_pages", 0)),
        },
        "modern": {
            "frozen_target_records": int(modern_enum.get("net_new_records", 0)),
            "original_text_acquired_records": sum(row.get("download_status") == "success" for row in modern_status),
            "parsed_records": sum(row.get("download_status") == "success" for row in modern_status),
            "failed_or_retry_objects": sum(row.get("download_status") != "success" for row in modern_status),
        },
    }
    rows = []
    for source_key, values in source_specs.items():
        batch_id = BATCHES[source_key]
        committed = int(connection.execute("SELECT COUNT(*) FROM enumeration_records WHERE batch_id=?", [batch_id]).fetchone()[0])
        values = {**values, "source_key": source_key, "batch_id": batch_id, "formally_committed_records": committed}
        values.setdefault("unprocessed_source_objects", 0)
        values.setdefault("failed_target_records", 0)
        values["not_yet_processed_records"] = max(
            0,
            values["frozen_target_records"]
            - values["original_text_acquired_records"]
            - values["failed_target_records"],
        )
        rows.append(values)
    payload = {"generated_at": now_iso(), "database": str(DB_PATH), "sources": rows}
    write_json(REPORT_ROOT / "formal_ingestion_progress.json", payload)
    return payload


def repair_historic_parser_artifacts() -> dict[str, Any]:
    """Remove only task-created historic identities absent after parser repair.

    Raw ZIPs and derived JSON remain on disk as audit evidence.  Shared archive
    content objects/versions are retained; only the unreproducible document
    identities and their document-specific segments are removed transactionally.
    """
    manifest_ids = {row["external_id"] for row in read_csv(MANIFEST_ROOT / "historic_record_manifest.csv")}
    source_id = _source_definitions()["historic"]["source_id"]
    batch_id = BATCHES["historic"]
    with duckdb.connect(str(DB_PATH)) as connection:
        rows = connection.execute(
            """
            SELECT d.document_id, d.external_id, d.publication_date, d.title,
                   COUNT(DISTINCT a.segment_id) AS segment_count
            FROM documents d
            JOIN enumeration_records e USING(document_id)
            LEFT JOIN voice_attributions a USING(document_id)
            WHERE e.batch_id=? AND d.source_id=?
            GROUP BY 1,2,3,4
            ORDER BY d.publication_date, d.external_id
            """,
            [batch_id, source_id],
        ).fetchall()
        excluded = [row for row in rows if str(row[1]) not in manifest_ids]
        if len(excluded) > 100:
            raise RuntimeError(f"Refusing parser-artifact repair with unexpectedly broad scope: {len(excluded)} documents")
        evidence_rows = [
            {
                "document_id": row[0],
                "external_id": row[1],
                "publication_date": row[2].isoformat() if row[2] else "",
                "title": row[3],
                "segment_count": int(row[4]),
                "reason": "unreproducible_after_numbered_question_prefix_and_content_identity_repair",
                "raw_evidence_retained": True,
            }
            for row in excluded
        ]
        write_csv(REPORT_ROOT / "historic_parser_artifact_exclusions.csv", evidence_rows)
        if not excluded:
            result = {"generated_at": now_iso(), "excluded_documents": 0, "excluded_segments": 0, "status": "no_action_needed"}
            write_json(REPORT_ROOT / "historic_parser_artifact_repair.json", result)
            return result
        document_frame = pd.DataFrame({"document_id": [str(row[0]) for row in excluded]})
        connection.register("_historic_parser_artifact_docs", document_frame)
        excluded_segment_count = int(
            connection.execute(
                "SELECT COUNT(DISTINCT segment_id) FROM voice_attributions WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"
            ).fetchone()[0]
        )
        connection.execute(
            "CREATE TEMP TABLE _historic_parser_artifact_segments AS SELECT DISTINCT segment_id FROM voice_attributions WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"
        )
        connection.execute(
            "CREATE TEMP TABLE _historic_parser_artifact_versions AS SELECT document_version_id FROM document_versions WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"
        )
        connection.execute(
            "CREATE TEMP TABLE _historic_parser_artifact_raw AS SELECT DISTINCT raw_record_id FROM enumeration_records WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"
        )
        # DuckDB does not always re-evaluate a just-deleted referencing row for
        # a second FK delete in the same transaction.  Commit each bounded FK
        # layer, preserving the exact target tables above so a rerun continues
        # only the remaining layers rather than broadening the repair.
        deletion_stages = [
            ("voice_attributions", "DELETE FROM voice_attributions WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"),
            ("text_segments", "DELETE FROM text_segments WHERE segment_id IN (SELECT segment_id FROM _historic_parser_artifact_segments)"),
            ("document_content_objects", "DELETE FROM document_content_objects WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"),
            ("document_organisations", "DELETE FROM document_organisations WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"),
            ("document_version_raw_links", "DELETE FROM document_version_raw_links WHERE document_version_id IN (SELECT document_version_id FROM _historic_parser_artifact_versions)"),
            ("document_versions", "DELETE FROM document_versions WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"),
            ("enumeration_records", "DELETE FROM enumeration_records WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"),
            ("raw_records", "DELETE FROM raw_records WHERE raw_record_id IN (SELECT raw_record_id FROM _historic_parser_artifact_raw)"),
            ("documents", "DELETE FROM documents WHERE document_id IN (SELECT document_id FROM _historic_parser_artifact_docs)"),
        ]
        committed_stages = []
        for stage, statement in deletion_stages:
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute(statement)
                connection.execute("COMMIT")
                committed_stages.append(stage)
            except Exception:
                connection.execute("ROLLBACK")
                write_json(
                    REPORT_ROOT / "historic_parser_artifact_repair.partial.json",
                    {"generated_at": now_iso(), "committed_stages": committed_stages, "failed_stage": stage},
                )
                raise
        extraction_run_id = stable_id("ext", batch_id, EXTRACTOR_VERSION)
        output_segments = int(connection.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [extraction_run_id]).fetchone()[0])
        connection.execute(
            "UPDATE extraction_runs SET output_segment_count=?, finished_at=?, status_reason=? WHERE extraction_run_id=?",
            [output_segments, datetime.now(UTC), "Task-created parser artifacts excluded after bounded provenance repair; raw evidence retained.", extraction_run_id],
        )
        _write_ingestion_progress(connection)
    result = {
        "generated_at": now_iso(),
        "excluded_documents": len(excluded),
        "excluded_segments": excluded_segment_count,
        "raw_evidence_retained": True,
        "shared_volume_objects_retained": True,
        "transaction_committed": True,
        "committed_fk_stages": committed_stages,
    }
    write_json(REPORT_ROOT / "historic_parser_artifact_repair.json", result)
    return result


def finalize_historic_manifest_baseline() -> dict[str, Any]:
    """Restore pre-batch existing/new semantics after the bounded manifest revision."""
    manifest_path = MANIFEST_ROOT / "historic_record_manifest.csv"
    partition_path = MANIFEST_ROOT / "historic_record_partitions.csv"
    summary_path = MANIFEST_ROOT / "historic_record_enumeration_summary.json"
    rows = read_csv(manifest_path)
    for row in rows:
        row["existing_document"] = False
    write_csv(manifest_path, rows)
    partition_counts = Counter(row["partition_id"] for row in rows)
    partitions = read_csv(partition_path)
    for row in partitions:
        count = int(partition_counts.get(row["partition_id"], 0))
        row["enumerated_targets"] = count
        row["existing_records"] = 0
        row["net_new_records"] = count
    write_csv(partition_path, partitions)
    summary = read_json(summary_path)
    summary["generated_at"] = now_iso()
    summary["enumerated_targets"] = len(rows)
    summary["existing_records"] = 0
    summary["net_new_records"] = len(rows)
    summary["baseline_semantics"] = "No Historic Hansard record existed before this acquisition batch; in-batch committed rows are not pre-existing records."
    write_json(summary_path, summary)
    manifest_sha = sha256_file(manifest_path)
    batch_id = BATCHES["historic"]
    extraction_run_id = stable_id("ext", batch_id, EXTRACTOR_VERSION)
    with duckdb.connect(str(DB_PATH)) as connection:
        committed = int(connection.execute("SELECT COUNT(*) FROM enumeration_records WHERE batch_id=?", [batch_id]).fetchone()[0])
        if committed != len(rows):
            raise RuntimeError(f"Historic finalization requires all manifest rows committed: committed={committed}, manifest={len(rows)}")
        connection.execute(
            """
            UPDATE collection_batches
            SET reported_total=?, returned_count=?, completeness_status='complete_as_visible_with_documented_volume_exception',
                completeness_reason=?, search_snapshot_path=?, search_snapshot_sha256=?,
                metadata_snapshot_path=?, metadata_snapshot_sha256=?
            WHERE batch_id=?
            """,
            [
                len(rows), len(rows),
                "All records parsed from 319 valid official bulk XML targets committed; official volume 200 remained an invalid error-page ZIP.",
                rel(manifest_path), manifest_sha, rel(manifest_path), manifest_sha, batch_id,
            ],
        )
        connection.execute(
            "UPDATE coverage_records SET denominator_value=?, completeness_status='complete_as_visible_with_documented_volume_exception' WHERE batch_id=?",
            [len(rows), batch_id],
        )
        output_segments = int(connection.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [extraction_run_id]).fetchone()[0])
        connection.execute(
            "UPDATE extraction_runs SET finished_at=?, input_content_count=?, output_segment_count=?, status='complete', status_reason=? WHERE extraction_run_id=?",
            [datetime.now(UTC), 319, output_segments, "All revised manifest records committed in bounded chunks; one invalid official volume remains documented.", extraction_run_id],
        )
        run_id = stable_id("run", batch_id, SCRIPT_VERSION)
        connection.execute(
            "UPDATE acquisition_runs SET finished_at=?, input_manifest_path=?, input_manifest_sha256=?, status='complete_with_documented_exception', result_json=? WHERE run_id=?",
            [datetime.now(UTC), rel(manifest_path), manifest_sha, canonical_json({"committed_records": committed, "manifest_records": len(rows), "valid_parent_volumes": 319, "invalid_parent_volumes": 1, "parser_artifacts_excluded": 16}), run_id],
        )
        progress = _write_ingestion_progress(connection)
    result = {
        "generated_at": now_iso(),
        "manifest_records": len(rows),
        "formally_committed_records": committed,
        "existing_before_batch": 0,
        "net_new_records": len(rows),
        "manifest_sha256": manifest_sha,
        "progress": progress,
    }
    write_json(REPORT_ROOT / "historic_manifest_finalization.json", result)
    return result


def ingest_all(
    *,
    source_keys: list[str] | None = None,
    max_chunks: int | None = None,
) -> dict[str, Any]:
    """Ingest acquired records into 06 in bounded, committed, resumable chunks."""
    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    before_sha = sha256_file(DB_PATH)
    existing_backups = sorted(BACKUP_ROOT.glob("fear_temperature_government_content.before_historical.*.duckdb"))
    backup_path = existing_backups[0] if existing_backups else BACKUP_ROOT / f"fear_temperature_government_content.before_historical.{before_sha[:12]}.duckdb"
    if not existing_backups:
        shutil.copy2(DB_PATH, backup_path)
    source_defs = _source_definitions()
    selected_sources = source_keys or ["policy", "historic", "hansard", "hansard_gap", "modern"]
    invalid_sources = sorted(set(selected_sources) - set(source_defs))
    if invalid_sources:
        raise ValueError(f"Unknown source keys: {invalid_sources}")
    before_counts: dict[str, int]
    with duckdb.connect(str(DB_PATH)) as connection:
        before_counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ["documents", "content_objects", "content_versions", "text_segments", "voice_attributions"]
        }
        authorization_id = _new_authorization(connection)
        _normalisation_rule(connection)
        for definition in source_defs.values():
            _insert_source(connection, definition)
        committed_chunks = 0
        source_contexts: dict[str, dict[str, dict[str, Any]]] = {}
        if "historic" in selected_sources:
            source_contexts["historic"] = _historic_volume_context()
        if "hansard_gap" in selected_sources:
            source_contexts["hansard_gap"] = _derived_html_context()
        if "modern" in selected_sources:
            source_contexts["modern"] = _derived_list_context()
        policy_statuses = read_csv(MANIFEST_ROOT / "policy_acquisition_status.csv")
        for source_key in selected_sources:
            source_id = source_defs[source_key]["source_id"]
            batch_id = BATCHES[source_key]
            extraction_run_id = stable_id("ext", batch_id, EXTRACTOR_VERSION)
            frozen_rows = _new_manifest_rows(source_key)
            existing_external = {
                str(value[0]) for value in connection.execute("SELECT external_id FROM documents WHERE source_id=?", [source_id]).fetchall()
            }
            pending_rows = [row for row in frozen_rows if row["external_id"] not in existing_external]
            if source_key == "modern":
                successful = {
                    row["external_id"]: row
                    for row in read_csv(MANIFEST_ROOT / "modern_acquisition_status.csv")
                    if row.get("download_status") == "success"
                }
                pending_rows = [{**row, **successful[row["external_id"]]} for row in pending_rows if row["external_id"] in successful]
            _ensure_batch(connection, source_key, source_id, len(frozen_rows))
            _ensure_query_partitions(connection, source_key)
            connection.execute(
                "INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [extraction_run_id, batch_id, EXTRACTOR_VERSION, datetime.now(UTC), datetime.now(UTC), 0, 0, "partial",
                 "Bounded chunk ingestion; source text retained without semantic cleaning."],
            )
            chunk_size = POLICY_INGEST_CHUNK_SIZE if source_key == "policy" else PARLIAMENT_INGEST_CHUNK_SIZE
            for offset in range(0, len(pending_rows), chunk_size):
                if max_chunks is not None and committed_chunks >= max_chunks:
                    break
                chunk_rows = pending_rows[offset : offset + chunk_size]
                prepared = (
                    _prepare_policy_rows(source_id, batch_id, extraction_run_id, chunk_rows, policy_statuses)
                    if source_key == "policy"
                    else _prepare_parliament_rows(
                        source_key,
                        source_id,
                        batch_id,
                        extraction_run_id,
                        chunk_rows,
                        source_contexts.get(source_key),
                    )
                )
                count_tables = ["documents", "content_objects", "content_versions", "text_segments", "voice_attributions"]
                chunk_before = {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in count_tables}
                connection.execute("BEGIN TRANSACTION")
                try:
                    _insert_prepared_chunk(connection, prepared)
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
                committed_at = now_iso()
                chunk_after = {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in count_tables}
                external_ids = [row["external_id"] for row in chunk_rows]
                chunk_sha = sha256_bytes(canonical_json(external_ids).encode())
                checkpoint_path = REPORT_ROOT / "ingestion_checkpoints" / source_key / f"chunk_{offset:06d}_{offset + len(chunk_rows) - 1:06d}_{chunk_sha[:12]}.json"
                write_json(
                    checkpoint_path,
                    {
                        "source_key": source_key,
                        "batch_id": batch_id,
                        "chunk_offset": offset,
                        "source_record_count": len(chunk_rows),
                        "source_record_ids_sha256": chunk_sha,
                        "first_external_id": external_ids[0],
                        "last_external_id": external_ids[-1],
                        "prepared_row_counts": {key: len(value) for key, value in prepared.items()},
                        "new_rows_added": {table: chunk_after[table] - chunk_before[table] for table in count_tables},
                        "committed_at": committed_at,
                        "database": str(DB_PATH),
                    },
                )
                input_count = int(connection.execute("SELECT COUNT(*) FROM acquisition_object_statuses WHERE batch_id=?", [batch_id]).fetchone()[0])
                output_count = int(connection.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [extraction_run_id]).fetchone()[0])
                connection.execute(
                    "UPDATE extraction_runs SET finished_at=?, input_content_count=?, output_segment_count=?, status='partial', status_reason=? WHERE extraction_run_id=?",
                    [datetime.now(UTC), input_count, output_count, "Committed bounded chunks; source may still have unacquired or uncommitted targets.", extraction_run_id],
                )
                manifest = _batch_manifest(source_key)
                run_id = stable_id("run", batch_id, SCRIPT_VERSION)
                committed_records = int(connection.execute("SELECT COUNT(*) FROM enumeration_records WHERE batch_id=?", [batch_id]).fetchone()[0])
                connection.execute(
                    """INSERT INTO acquisition_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (run_id) DO UPDATE SET finished_at=excluded.finished_at, status=excluded.status,
                    attempted_count=excluded.attempted_count, successful_download_count=excluded.successful_download_count,
                    successful_extraction_count=excluded.successful_extraction_count, failure_count=excluded.failure_count,
                    result_json=excluded.result_json""",
                    [run_id, batch_id, authorization_id, datetime.now(UTC), datetime.now(UTC), "bounded_chunk_ingest",
                     SCRIPT_VERSION, f"{sys.executable} {rel(Path(__file__))} ingest --source {source_key}", rel(manifest), sha256_file(manifest),
                     str(DB_PATH), "partial", input_count, input_count, input_count, 0,
                     canonical_json({"committed_records": committed_records, "last_checkpoint": str(checkpoint_path), "segments": output_count})],
                )
                _write_ingestion_progress(connection)
                committed_chunks += 1
                print(
                    f"[{committed_at}] COMMIT {source_key} chunk={committed_chunks} "
                    f"records={len(chunk_rows)} new_documents={chunk_after['documents'] - chunk_before['documents']} "
                    f"new_segments={chunk_after['text_segments'] - chunk_before['text_segments']} checkpoint={checkpoint_path}",
                    flush=True,
                )
                del prepared
                gc.collect()
            if max_chunks is not None and committed_chunks >= max_chunks:
                break
        after_counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in before_counts
        }
        duplicate_checks = {
            "document_source_external_duplicates": int(connection.execute("SELECT COUNT(*) FROM (SELECT source_id, external_id FROM documents GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]),
            "document_canonical_url_duplicates": int(connection.execute("SELECT COUNT(*) FROM (SELECT canonical_url FROM documents GROUP BY 1 HAVING COUNT(*)>1)").fetchone()[0]),
            "content_object_url_duplicates": int(connection.execute("SELECT COUNT(*) FROM (SELECT object_kind, canonical_url FROM content_objects GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]),
            "orphan_segments": int(connection.execute("SELECT COUNT(*) FROM text_segments s LEFT JOIN content_versions v USING(content_version_id) WHERE v.content_version_id IS NULL").fetchone()[0]),
            "orphan_voice_attributions": int(connection.execute("SELECT COUNT(*) FROM voice_attributions a LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL").fetchone()[0]),
        }
    result = {
        "generated_at": now_iso(),
        "database": str(DB_PATH),
        "database_before_sha256": before_sha,
        "database_after_sha256": sha256_file(DB_PATH),
        "recovery_backup": str(backup_path),
        "recovery_backup_sha256": sha256_file(backup_path),
        "before_counts": before_counts,
        "after_counts": after_counts,
        "added_counts": {key: after_counts[key] - before_counts[key] for key in before_counts},
        "duplicate_and_link_checks": duplicate_checks,
        "passed": all(value == 0 for value in duplicate_checks.values()),
    }
    write_json(REPORT_ROOT / "ingestion_result.json", result)
    return result


def _run_phase(name: str, function: Any, **kwargs: Any) -> dict[str, Any]:
    print(f"[{now_iso()}] START {name}", flush=True)
    result = function(**kwargs)
    print(f"[{now_iso()}] DONE  {name}: {json.dumps(result, ensure_ascii=False)}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=[
            "enumerate-policy",
            "acquire-policy",
            "enumerate-historic-volumes",
            "acquire-historic-volumes",
            "enumerate-historic-records",
            "enumerate-hansard-candidates",
            "acquire-hansard-details",
            "enumerate-hansard-answers",
            "acquire-hansard-answer-details",
            "enumerate-hansard-gap-answers",
            "probe-hansard-gap-publications-archive",
            "enumerate-hansard-gap-archive-answers",
            "acquire-hansard-gap-archive-answers",
            "parse-hansard-gap-archive-downloads",
            "acquire-hansard-gap-answer-details",
            "enumerate-hansard-gap-statements",
            "acquire-hansard-gap-statement-details",
            "audit-hansard-gap-statement-failures",
            "enumerate-modern",
            "acquire-modern",
            "repair-historic-parser-artifacts",
            "finalize-historic-manifest",
            "ingest",
            "all",
        ],
    )
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument(
        "--source",
        action="append",
        choices=["policy", "historic", "hansard", "hansard_gap", "modern"],
        help="For the ingest phase, process only the named source; may be repeated.",
    )
    parser.add_argument("--max-chunks", type=int, help="For bounded real-record validation, stop after this many committed chunks.")
    args = parser.parse_args()
    resume = not args.no_resume
    phases: list[tuple[str, Any, dict[str, Any]]] = [
        ("enumerate-policy", enumerate_policy, {"resume": resume}),
        ("acquire-policy", acquire_policy, {"resume": resume}),
        ("enumerate-historic-volumes", enumerate_historic_volumes, {"resume": resume}),
        ("acquire-historic-volumes", acquire_historic_volumes, {"resume": resume}),
        ("enumerate-historic-records", enumerate_historic_records, {}),
        ("enumerate-hansard-candidates", enumerate_hansard_candidates, {"resume": resume}),
        ("acquire-hansard-details", acquire_hansard_details, {"resume": resume}),
        ("enumerate-hansard-answers", enumerate_hansard_answers, {"resume": resume}),
        ("acquire-hansard-answer-details", acquire_hansard_answer_details, {"resume": resume}),
        ("enumerate-hansard-gap-answers", enumerate_hansard_gap_answers, {"resume": resume}),
        ("probe-hansard-gap-publications-archive", probe_hansard_gap_publications_archive, {}),
        ("enumerate-hansard-gap-archive-answers", enumerate_hansard_gap_archive_answers, {"resume": resume}),
        ("acquire-hansard-gap-archive-answers", acquire_hansard_gap_archive_answers, {"resume": resume}),
        ("parse-hansard-gap-archive-downloads", parse_hansard_gap_archive_downloads, {}),
        ("acquire-hansard-gap-answer-details", acquire_hansard_gap_answer_details, {"resume": resume}),
        ("enumerate-hansard-gap-statements", enumerate_hansard_gap_statement_candidates, {"resume": resume}),
        ("acquire-hansard-gap-statement-details", acquire_hansard_gap_statement_details, {"resume": resume}),
        ("audit-hansard-gap-statement-failures", audit_hansard_gap_statement_failures, {"resume": resume}),
        ("enumerate-modern", enumerate_modern_records, {"resume": resume}),
        ("acquire-modern", materialize_modern_from_list_pages, {"resume": resume}),
        ("repair-historic-parser-artifacts", repair_historic_parser_artifacts, {}),
        ("finalize-historic-manifest", finalize_historic_manifest_baseline, {}),
        ("ingest", ingest_all, {"source_keys": args.source, "max_chunks": args.max_chunks}),
    ]
    if args.phase == "all":
        for name, function, kwargs in phases:
            _run_phase(name, function, **kwargs)
    else:
        name, function, kwargs = next(value for value in phases if value[0] == args.phase)
        _run_phase(name, function, **kwargs)


if __name__ == "__main__":
    main()
