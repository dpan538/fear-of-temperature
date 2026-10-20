"""Resumable official metadata + bounded excerpts. No persistent full-text cache.

Only source-native records match the matrix; pages/queries never inflate row counts.
OAI datestamps and CKAN timestamps are not substituted for publication dates.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import fcntl
import hashlib
import html
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

import adapters
import official_pages

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_OUTPUT = ROOT / "work_packages/official_voice_20261020"
MATRIX = json.loads((HERE / "query_matrix.json").read_text())
COLLECTION_MATRIX = json.loads((HERE / "query_matrix_extended.json").read_text())
BASELINE_TERMS = {term for terms in MATRIX["dimensions"].values() for term in terms}
EXTENDED_TERMS = {term for terms in COLLECTION_MATRIX["dimensions"].values() for term in terms}
REGISTRY = json.loads((HERE / "SOURCE_REGISTRY.json").read_text())
START, END = MATRIX["publication_interval"]
NS = {"o": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/"}
LOG = logging.getLogger("official_voice")


def now():
    return datetime.now(UTC).isoformat(timespec="seconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encode(value).encode()).hexdigest()


@contextmanager
def atomic_text(path):
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", newline="") as handle:
        yield handle
    temporary.replace(path)


def write_json(path, value):
    with atomic_text(path) as handle:
        handle.write(encode(value) + "\n")


def words(text):
    return html.unescape(re.sub(r"<[^>]*>", " ", text or ""))


def pattern(term):
    parts = re.split(r"[\s-]+", term)
    plural = r"(?:es)?" if parts[-1] == "gas" else r"s?"
    return re.compile(
        r"\b" + r"[\s\-\u2010-\u2014]+".join(map(re.escape, parts)) + plural + r"\b", re.I
    )


PATTERNS = [
    (dimension, term, pattern(term))
    for dimension, terms in COLLECTION_MATRIX["dimensions"].items()
    for term in terms
]


def matches(text):
    value = text or ""
    lower = value.casefold()
    # C substring prechecks avoid 26 regex scans of every unrelated paragraph.
    # The final regex still decides the exact phrase/offset; recall is unchanged.
    return [
        (dimension, term, match.start(), match.end())
        for dimension, term, pat in PATTERNS
        if term.split()[0].split("-")[0] in lower and (match := pat.search(value))
    ]


def snippet(text, hits):
    """At most 500 Unicode characters, preserving a verbatim locator into supplied text."""
    if not text or not hits:
        return None, None
    center = min(hit[2] for hit in hits)
    start = max(0, center - 180)
    end = min(len(text), start + 500)
    return text[start:end], f"supplied_text_characters:{start}:{end}; zero-based end-exclusive"


def publication(value, basis="source publication field", january_placeholder=False):
    raw = str(value or "").strip()
    result = dict(
        publication_date=None,
        publication_date_raw=raw or None,
        publication_start=None,
        publication_end=None,
        date_granularity="unknown",
        date_basis=basis,
        date_status="pending_publication_date",
        publication_month=None,
    )
    found = re.fullmatch(r"(\d{4})(?:-(\d{2})(?:-(\d{2})(?:T.*)?)?)?", raw)
    if not found:
        return result
    year, month, day = (int(x) if x else None for x in found.groups())
    if january_placeholder and month == 1 and day == 1:
        month = day = None
        result["date_basis"] += "; January-01 may encode year-only: conservatively year precision"
    try:
        lower = date(year, month or 1, day or 1)
        upper = (
            lower
            if day
            else date(year, month, calendar.monthrange(year, month)[1])
            if month
            else date(year, 12, 31)
        )
    except ValueError:
        result["date_status"] = "invalid_source_date"
        return result
    result.update(
        publication_start=lower.isoformat(),
        publication_end=upper.isoformat(),
        date_granularity="day" if day else "month" if month else "year",
    )
    if day:
        result["publication_date"] = lower.isoformat()
    if month:
        result["publication_month"] = lower.strftime("%Y-%m")
    result["date_status"] = (
        "inside_fixed_interval"
        if lower.isoformat() >= START and upper.isoformat() <= END
        else "outside_fixed_interval"
        if upper.isoformat() < START or lower.isoformat() > END
        else "pending_boundary_precision"
    )
    return result


def capacity(path, operation_bytes):
    """Dai removed the 15-GiB floor. Reserve only space for this actual operation."""
    path.mkdir(parents=True, exist_ok=True)
    available = shutil.disk_usage(path).free
    # Response + SQLite transaction/journal allowance; no fixed free-space floor.
    required = operation_bytes * 3 + 1024 * 1024
    if available < required:
        raise RuntimeError(f"capacity_paused: available={available}, operation_required={required}")


class Store:
    def __init__(self, output=DEFAULT_OUTPUT):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.output / "official_voice.sqlite", timeout=60)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((HERE / "schema.sqlite.sql").read_text())
        existing = {r[1] for r in self.db.execute("PRAGMA table_info(source_documents)")}
        for column, ddl in [
            ("query_match_basis", "TEXT NOT NULL DEFAULT 'supplied_text_or_title'"),
            ("source_context_json", "TEXT NOT NULL DEFAULT '{}'"),
        ]:
            if column not in existing:
                self.db.execute(f"ALTER TABLE source_documents ADD COLUMN {column} {ddl}")
        self.db.execute("PRAGMA journal_mode=WAL")

    def job(self, job_id, source, state, cursor=None, detail=None):
        self.db.execute(
            "INSERT INTO ingest_jobs VALUES(?,?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET "
            "state=excluded.state,cursor=excluded.cursor,detail=excluded.detail,"
            "updated_at=excluded.updated_at",
            (job_id, source, state, encode(cursor), detail, now()),
        )
        self.db.commit()

    def cursor(self, job_id):
        row = self.db.execute("SELECT * FROM ingest_jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def save(
        self,
        source,
        native,
        title,
        text,
        date_value,
        url,
        *,
        tier,
        unit,
        version="live",
        speaker=None,
        role="unresolved",
        role_evidence=None,
        basis="source publication field",
        parent=None,
        excerpt_kind="metadata",
        extra=None,
        january_placeholder=False,
        provider_terms=None,
        persistent_id=None,
    ):
        supplied_text = words(text)
        hits = matches(supplied_text)
        title_hits = matches(title or "")
        if not hits and not title_hits and not provider_terms:
            return 0
        excerpt, locator = snippet(supplied_text, hits)
        if excerpt is None and title_hits:
            excerpt, locator = snippet(title or "", title_hits)
            excerpt_kind = "title_only"
            locator = "title:" + locator
        terms = sorted({h[1] for h in hits + title_hits} | set(provider_terms or []))
        dimensions = sorted(
            {h[0] for h in hits + title_hits}
            | {
                d
                for d, ts in COLLECTION_MATRIX["dimensions"].items()
                if set(ts) & set(provider_terms or [])
            }
        )
        doc_id = digest([source, str(native)])
        old = self.db.execute("SELECT * FROM source_documents WHERE doc_id=?", (doc_id,)).fetchone()
        metadata = dict(
            native_id=str(native),
            title=title,
            publication=date_value,
            url=url,
            speaker=speaker,
            version=version,
            extra=extra,
            excerpt=excerpt,
        )
        metadata_hash = digest(metadata)
        history = json.loads(old["metadata_version_history"]) if old else []
        if old and old["source_metadata_hash"] != metadata_hash:
            # Preserve prior compact metadata/excerpt, never prior complete originals.
            history.append({k: v for k, v in dict(old).items() if k != "metadata_version_history"})
        if old:
            dimensions = sorted(set(dimensions) | set(json.loads(old["query_dimensions"])))
        record = dict(
            doc_id=doc_id,
            source_channel=source,
            institutional_tier=tier,
            native_id=str(native),
            native_unit=unit,
            source_version=version,
            parent_native_id=str(parent) if parent is not None else None,
            title=title or None,
            author_speaker=speaker,
            voice_role=role,
            role_evidence=role_evidence,
            url_source=url,
            doi_or_handle=persistent_id,
            query_match_basis="supplied_text_or_title"
            if hits or title_hits
            else "provider_search_hit_local_phrase_unconfirmed",
            query_matched=encode(
                sorted(set(terms) | set(json.loads(old["query_matched"]) if old else []))
            ),
            query_dimensions=encode(dimensions),
            excerpt_text=excerpt,
            excerpt_kind=excerpt_kind,
            excerpt_locator=locator,
            text_readability="excerpt_observed" if excerpt else "metadata_only",
            research_use_status="unknown",
            related_work_ids=encode([]),
            source_context_json=encode(
                {**(extra or {}), "query_matrix_run": COLLECTION_MATRIX["version"]}
            ),
            source_metadata_hash=metadata_hash,
            metadata_version_history=encode(history),
            retrieved_at=now(),
            created_at=old["created_at"] if old else now(),
        )
        record.update(publication(date_value, basis, january_placeholder))
        if source == "hansard_federal_rapid" and str(parent) in {"2146", "4891"}:
            record["date_status"] = "pending_source_date_conflict"
            record["publication_month"] = None
            record["date_basis"] += "; known session-date/original-URL conflict; unresolved"
        columns = list(record)
        self.db.execute(
            f"INSERT INTO source_documents ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)}) ON CONFLICT(doc_id) DO UPDATE SET "
            + ",".join(f"{k}=excluded.{k}" for k in columns if k not in {"doc_id", "created_at"}),
            list(record.values()),
        )
        return 1

    def page(self, job, source, key, url, body, observed, saved, cursor):
        self.db.execute(
            "INSERT OR REPLACE INTO ingest_pages VALUES(?,?,?,?,?,?,?,?,?)",
            (job, str(key), source, url, digest(body), observed, saved, encode(cursor), now()),
        )
        self.db.commit()
        if self.db.execute("SELECT count(*) FROM ingest_pages").fetchone()[0] % 50 == 0:
            audit(self, log_warnings=False)
        LOG.info(
            "%s page=%s observed=%d matches=%d next=%s",
            source,
            key,
            observed,
            saved,
            "yes" if cursor is not None else "no",
        )


class Client:
    def __init__(self, output=DEFAULT_OUTPUT, pause=0.3):
        self.output = Path(output)
        self.pause = pause

    def get(self, url, headers=None, max_bytes=16 * 1024 * 1024):
        capacity(self.output, max_bytes)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "FearTemperatureResearch/1.0 (official metadata and excerpts)",
                **(headers or {}),
            },
        )
        for attempt in range(3):
            try:
                time.sleep(self.pause)
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = response.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        raise RuntimeError(
                            "response_operation_too_large; pending, "
                            "never treated as an exhausted page"
                        )
                    return body
            except urllib.error.HTTPError as exc:
                if exc.code in {401, 403, 404}:
                    raise
                if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                    raise
                retry = exc.headers.get("Retry-After", "")
                time.sleep(min(30, int(retry) if retry.isdigit() else 2 ** (attempt + 1)))
        raise RuntimeError("request did not complete")


def collect_uq(store, client):
    source, endpoint = "uq_espace", "https://espace.library.uq.edu.au/v2/oai"
    # Harvest modification history through retrieval, then filter publication dates.
    # OAI from/until MUST NOT be used as publication-date filters.
    job = "uq_oai_all_publication_inventory_v2_extended33"
    previous = store.cursor(job)
    if previous and previous["state"] == "exhausted":
        return
    cursor = json.loads(previous["cursor"]) if previous else None
    seen = set()
    page_number = store.db.execute(
        "SELECT count(*) FROM ingest_pages WHERE job_id=?", (job,)
    ).fetchone()[0]
    while True:
        if cursor in seen:
            raise RuntimeError("OAI repeated resumption token; incomplete")
        seen.add(cursor)
        params = (
            {"verb": "ListRecords", "resumptionToken": cursor}
            if cursor
            else {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
        )
        url = endpoint + "?" + urllib.parse.urlencode(params)
        body = client.get(url)
        root = ET.fromstring(body)
        error = root.find("o:error", NS)
        if error is not None:
            raise RuntimeError(f"OAI {error.get('code')}: {error.text}")
        records = root.findall("o:ListRecords/o:record", NS)
        token = root.find("o:ListRecords/o:resumptionToken", NS)
        next_cursor = (token.text or "").strip() if token is not None else ""
        saved = 0
        for record in records:
            header = record.find("o:header", NS)
            if header is None or header.get("status") == "deleted":
                continue
            fields = {}
            for child in record.findall("o:metadata/*/*", NS):
                fields.setdefault(child.tag.rsplit("}", 1)[-1], []).append(child.text or "")
            identifiers = fields.get("identifier", [])
            url_source = next(
                (v for v in identifiers if v.startswith("https://espace.library.uq.edu.au/view/")),
                endpoint,
            )
            dates = fields.get("date", [])
            date_value = dates[0] if len(set(dates)) == 1 else None
            saved += store.save(
                source,
                header.findtext("o:identifier", namespaces=NS),
                " | ".join(fields.get("title", [])),
                "\n".join(fields.get("description", []) + fields.get("subject", [])),
                date_value,
                url_source,
                tier="academic_uq",
                unit="publication_metadata",
                speaker="; ".join(fields.get("creator", [])),
                role="academic_authored_output_not_institutional_position_verified",
                role_evidence="UQ repository membership; author and institutional "
                "endorsement are separate",
                basis="repository dc:date; source-reported publication date, "
                "original verification pending",
                excerpt_kind="abstract_or_subject_metadata",
                january_placeholder=True,
                extra={
                    "identifiers": identifiers,
                    "relations": fields.get("relation", []),
                    "date_values": dates,
                    "types": fields.get("type", []),
                    "oai_datestamp": header.findtext("o:datestamp", namespaces=NS),
                },
            )
        page_number += 1
        store.page(job, source, page_number, url, body, len(records), saved, next_cursor or None)
        store.job(
            job,
            source,
            "running" if next_cursor else "exhausted",
            next_cursor or None,
            "All returned pages traversed only when exhausted; "
            "OAI updates are not publication dates",
        )
        if not next_cursor:
            return
        if not records:
            raise RuntimeError("OAI empty page with continuation token; incomplete")
        cursor = next_cursor


def ckan_page(payload, offset):
    if payload.get("success") is not True:
        raise RuntimeError("CKAN success=false")
    result = payload["result"]
    rows, total = result["results"], int(result["count"])
    if not rows and offset < total:
        raise RuntimeError("CKAN empty page before advertised total; incomplete")
    next_offset = offset + len(rows)
    # The advertised count is diagnostic. Request the terminal empty page too.
    return rows, next_offset if rows else None, total


def collect_qld(store, client):
    source = "qld_opendata"
    endpoint = "https://www.data.qld.gov.au/api/3/action/package_search"
    for _dimension, terms in COLLECTION_MATRIX["dimensions"].items():
        for term in terms:
            job = "qld:v2_until_empty:" + term
            previous = store.cursor(job)
            if previous and previous["state"] == "exhausted":
                continue
            offset = json.loads(previous["cursor"]) if previous else 0
            offset = offset or 0
            seen = set()
            while True:
                params = {"q": '"' + term + '"', "rows": 100, "start": offset, "sort": "id asc"}
                url = endpoint + "?" + urllib.parse.urlencode(params)
                body = client.get(url)
                records, next_offset, total = ckan_page(json.loads(body), offset)
                signature = digest([r["id"] for r in records])
                if records and signature in seen:
                    raise RuntimeError("CKAN repeated page IDs; incomplete")
                seen.add(signature)
                saved = 0
                for record in records:
                    # Catalogue creation/modification is not original publication.
                    extras = {e["key"]: e["value"] for e in record.get("extras", [])}
                    issued = (
                        extras.get("issued")
                        or extras.get("publication_date")
                        or record.get("issued")
                    )
                    saved += store.save(
                        source,
                        record["id"],
                        record.get("title"),
                        record.get("notes", ""),
                        issued,
                        "https://www.data.qld.gov.au/dataset/" + record["name"],
                        tier="state_qld",
                        unit="dataset_catalogue_metadata",
                        speaker=(record.get("organization") or {}).get("title"),
                        role="government_dataset_catalogue",
                        basis="explicit issued/publication field only; "
                        "catalogue timestamps not substituted",
                        excerpt_kind="dataset_description",
                        provider_terms=[term],
                        extra={
                            "resources": [
                                {
                                    "id": r.get("id"),
                                    "name": r.get("name"),
                                    "url": r.get("url"),
                                    "format": r.get("format"),
                                }
                                for r in record.get("resources", [])
                            ],
                            "metadata_created": record.get("metadata_created"),
                            "metadata_modified": record.get("metadata_modified"),
                            "license_id": record.get("license_id"),
                        },
                    )
                store.page(job, source, offset, url, body, len(records), saved, next_offset)
                store.job(
                    job,
                    source,
                    "running" if next_offset is not None else "exhausted",
                    next_offset,
                    f"advertised_total={total}; no publication-date search field confirmed; "
                    "local strict interval",
                )
                if next_offset is None:
                    break
                offset = next_offset


def months():
    y, m = 1988, 1
    while (y, m) <= (2026, 9):
        yield f"{y:04}-{m:02}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def matrix_membership(terms):
    terms = set(terms)
    baseline = bool(terms & BASELINE_TERMS)
    extended = bool(terms & EXTENDED_TERMS)
    return {
        "baseline26": baseline,
        "extended33_union": extended,
        "extended_only": extended and not baseline,
    }


def audit(store, report_dir=None, log_warnings=True):
    # All distribution queries share one SQLite read snapshot while workers append.
    owns_snapshot = not store.db.in_transaction
    if owns_snapshot:
        store.db.execute("BEGIN")
    try:
        return _audit_snapshot(store, report_dir, log_warnings)
    finally:
        if owns_snapshot:
            store.db.rollback()  # End a read-only transaction; no acquired rows removed.


def _audit_snapshot(store, report_dir=None, log_warnings=True):
    destination = Path(report_dir or store.output)
    destination.mkdir(parents=True, exist_ok=True)
    rows = list(
        store.db.execute(
            "SELECT source_channel,native_unit,date_status,publication_month,count(*) n "
            "FROM source_documents GROUP BY 1,2,3,4"
        )
    )
    # Actual continuation tokens stay in the local SQLite control table.
    states = [
        {k: v for k, v in dict(r).items() if k != "cursor"}
        for r in store.db.execute("SELECT * FROM ingest_jobs ORDER BY job_id")
    ]
    inside = sum(r["n"] for r in rows if r["date_status"] == "inside_fixed_interval")
    hansard = sum(
        r["n"]
        for r in rows
        if r["date_status"] == "inside_fixed_interval" and "hansard" in r["source_channel"]
    )
    item_rows = sum(
        r["n"]
        for r in rows
        if r["date_status"] == "inside_fixed_interval"
        and r["native_unit"] != "dataset_catalogue_metadata"
    )
    source_counts = [
        dict(r)
        for r in store.db.execute(
            "SELECT source_channel,native_unit,date_status,count(*) n "
            "FROM source_documents GROUP BY 1,2,3"
        )
    ]
    by_month = {
        m: sum(
            r["n"]
            for r in rows
            if r["publication_month"] == m and r["date_status"] == "inside_fixed_interval"
        )
        for m in months()
    }
    zero = [m for m, n in by_month.items() if not n]
    comparison = {name: 0 for name in ["baseline26", "extended33_union", "extended_only"]}
    comparison_by_source = {}
    comparison_by_month = {m: dict(comparison) for m in months()}
    for record in store.db.execute(
        "SELECT source_channel,query_matched,publication_month "
        "FROM source_documents "
        "WHERE date_status='inside_fixed_interval'"
    ):
        membership = matrix_membership(json.loads(record["query_matched"]))
        channel_counts = comparison_by_source.setdefault(
            record["source_channel"], {name: 0 for name in comparison}
        )
        for name, yes in membership.items():
            comparison[name] += int(yes)
            channel_counts[name] += int(yes)
            if record["publication_month"] in comparison_by_month:
                comparison_by_month[record["publication_month"]][name] += int(yes)
    # Actual re-check of persisted source-native records, separate from aggregate query.
    exhaustion = exhaustion_summary(store)
    rechecks = []
    for month in zero:
        recount = store.db.execute(
            "SELECT count(*) FROM source_documents WHERE publication_month=? "
            "AND date_status='inside_fixed_interval'",
            (month,),
        ).fetchone()[0]
        rechecks.append(
            {
                "month": month,
                "recount": recount,
                "action": (
                    "saved native records recounted after all available source enumerations "
                    "reached terminal pages; full OAI scan checks publication months locally; "
                    "blocked/unconfigured routes remain pending"
                    if exhaustion["all_available_sources_complete"]
                    else "saved_record_recount_completed; native endpoint/month "
                    "requery pending where unavailable or source scan incomplete"
                ),
                "interpretation": "no observed dated matching record; "
                "not absence of official speech",
            }
        )
    warnings = []
    if zero:
        warnings.append(
            f"LogWarning: {len(zero)} zero-observed months; saved rows rechecked; "
            + (
                "all available source enumerations terminal; blocked routes still pending"
                if exhaustion["all_available_sources_complete"]
                else "endpoint-level checks remain pending until accessible sources complete"
            )
        )
    summary = {
        "updated_at": now(),
        "publication_interval": [START, END],
        "september_2026_partial": True,
        "query_matrix_versions": [MATRIX["version"], COLLECTION_MATRIX["version"]],
        "matrix_comparison_in_interval_unique_ids": comparison,
        "matrix_comparison_by_source": comparison_by_source,
        "matrix_comparison_status": "observed metadata union; consult exhaustion_status; "
        "baseline is a subset of extended and their totals must not be added",
        "historical_baseline_prefix": "BASELINE_CHECKPOINT.json; not final comparison",
        "unique_matching_metadata_rows_all_date_states": sum(r["n"] for r in rows),
        "unique_in_interval_metadata_rows": inside,
        "unique_in_interval_item_metadata_rows_excluding_dataset_catalogues": item_rows,
        "hansard_in_interval_native_rows": hansard,
        "counts_by_native_unit_and_date_state": source_counts,
        "source_module_registry": REGISTRY,
        **exhaustion,
        "source_jobs": states,
        "zero_observed_months": zero,
        "warnings": warnings,
        "claims_count": store.db.execute("SELECT count(*) FROM event_claims").fetchone()[0],
        "calendar_validated": False,
        "storage": "metadata and <=500-character excerpts; no full source bodies",
        "fixed_15GiB_floor": "removed by Dai 2026-10-20; actual-operation capacity checks remain",
    }
    write_json(destination / "STATUS.json", summary)
    with atomic_text(destination / "monthly_counts.csv") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["publication_month", "unique_observed_matching_metadata_rows", "interpretation"]
        )
        writer.writerows(
            (m, n, "partial_month" if m == "2026-09" else "observed_not_population_total")
            for m, n in by_month.items()
        )
    module_for = {s["channel"]: s["module"] for s in REGISTRY["sources"]}
    with atomic_text(destination / "monthly_module_counts.csv") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "publication_month",
                "module_1_parliament",
                "module_2_science",
                "module_3_trove",
                "module_4_repositories",
                "module_5_qld",
                "total_observed_matching_metadata",
                "availability_interpretation",
            ]
        )
        for month in months():
            counts = [
                sum(
                    r["n"]
                    for r in rows
                    if r["publication_month"] == month
                    and r["date_status"] == "inside_fixed_interval"
                    and module_for.get(r["source_channel"]) == module
                )
                for module in range(1, 6)
            ]
            writer.writerow(
                [
                    month,
                    *counts,
                    sum(counts),
                    "source scans/pending routes differ; zero is not absence",
                ]
            )
    write_json(destination / "zero_month_rechecks.json", rechecks)
    with atomic_text(destination / "monthly_matrix_counts.csv") as handle:
        writer = csv.writer(handle)
        writer.writerow(["publication_month", *comparison])
        for month, values in comparison_by_month.items():
            writer.writerow([month, *values.values()])
    if log_warnings:
        for warning in warnings:
            LOG.warning(warning)
    return summary


COLLECTORS = {"uq_espace": collect_uq, "qld_opendata": collect_qld}

adapters.core = sys.modules[__name__]
COLLECTORS.update(adapters.COLLECTORS)
official_pages.core = sys.modules[__name__]
COLLECTORS.update(official_pages.COLLECTORS)


def exhaustion_summary(store):
    jobs = {r["job_id"]: dict(r) for r in store.db.execute("SELECT * FROM ingest_jobs")}
    result = {}
    for entry in REGISTRY["sources"]:
        channel = entry["channel"]
        state = jobs.get("source_status:" + channel, {}).get("state")
        result[channel] = (
            "COMPLETED_LAST_PAGE"
            if state == "exhausted"
            else "PENDING_CREDENTIALS"
            if state == "pending_credentials"
            else "RUNNING"
            if state == "running"
            else "BLOCKED_OR_PENDING"
            if state
            else "PENDING_ADAPTER"
            if not entry.get("adapter")
            else "NOT_STARTED"
        )
    available = [
        s["channel"] for s in REGISTRY["sources"] if s.get("adapter") and s["channel"] != "trove"
    ]
    available_complete = all(result[s] == "COMPLETED_LAST_PAGE" for s in available)
    all_complete = all(v == "COMPLETED_LAST_PAGE" for v in result.values())
    return {
        "exhaustion_status": result,
        "page_traversal_complete": {k: v == "COMPLETED_LAST_PAGE" for k, v in result.items()},
        "all_available_sources_complete": available_complete,
        "all_sources_complete": all_complete,
        "all_five_modules_complete": all_complete,
        "completion_scope": "registered named routes; completion never inferred from record counts",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "audit", "export"])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source", choices=list(COLLECTORS))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    store = Store(args.output)
    if args.command == "collect":
        if not args.source:
            parser.error("collect requires --source")
        source_lock = (args.output / (args.source + ".writer.lock")).open("a")
        try:
            fcntl.flock(source_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            LOG.error(
                "A writer for this source/output is already active; no second collector started"
            )
            return 3
        try:
            store.job("source_status:" + args.source, args.source, "running")
            state = COLLECTORS[args.source](store, Client(args.output))
            store.job("source_status:" + args.source, args.source, state or "exhausted")
        except Exception as exc:
            LOG.exception("source paused; incomplete pagination is never exhaustion")
            store.job(
                "source_status:" + args.source, args.source, "blocked_or_paused", detail=str(exc)
            )
            audit(store)
            return 2
    if args.command == "export":
        completion = exhaustion_summary(store)
        if not completion["all_sources_complete"]:
            LOG.error("Formal export withheld: requested all_sources_complete condition is not met")
            audit(store)
            return 4
        export_started = now()
        export_count = 0
        export_matrices = {"baseline26": 0, "extended33_union": 0, "extended_only": 0}
        export_hash = hashlib.sha256()
        store.db.execute("BEGIN")
        with atomic_text(args.output / "source_documents.jsonl") as handle:
            for row in store.db.execute(
                "SELECT * FROM source_documents WHERE date_status='inside_fixed_interval' "
                "ORDER BY doc_id"
            ):
                value = dict(row)
                for field in [
                    "query_matched",
                    "query_dimensions",
                    "related_work_ids",
                    "source_context_json",
                    "metadata_version_history",
                ]:
                    value[field] = json.loads(value[field])
                value["matrix_membership"] = matrix_membership(value["query_matched"])
                line = encode(value) + "\n"
                handle.write(line)
                export_hash.update(line.encode())
                export_count += 1
                for name, yes in value["matrix_membership"].items():
                    export_matrices[name] += int(yes)
        claim_count = 0
        with atomic_text(args.output / "event_claims.jsonl") as handle:
            for row in store.db.execute("SELECT * FROM event_claims ORDER BY event_id"):
                handle.write(encode(dict(row)) + "\n")
                claim_count += 1
        store.db.rollback()
        manifest = {
            "started_at": export_started,
            "finished_at": now(),
            "publication_interval": [START, END],
            "source_document_rows": export_count,
            "event_claim_rows": claim_count,
            "matrix_counts": export_matrices,
            "source_documents_sha256": export_hash.hexdigest(),
            "consistency": "single SQLite read snapshot; live STATUS may be newer",
            "full_source_bodies_retained": False,
        }
        write_json(args.output / "EXPORT_MANIFEST.json", manifest)
    audit(store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
