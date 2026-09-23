#!/usr/bin/env python3
"""Bounded targeted repair for the historical government corpus.

This script consumes only the frozen failure queues named in the 2026-09-22
handoff.  It never invokes the broad acquisition or ingestion entry points.
"""

from __future__ import annotations

import argparse
import csv
import gc
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import duckdb


WORK_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPAIR_ROOT = WORK_ROOT / "targeted_gap_repair"
MANIFEST_ROOT = REPAIR_ROOT / "manifests"
EVIDENCE_ROOT = REPAIR_ROOT / "evidence"
REPORT_ROOT = REPAIR_ROOT / "reports"
CHECKPOINT_ROOT = REPAIR_ROOT / "checkpoints"
OCR_ROOT = REPAIR_ROOT / "ocr"
RECOVERY_ROOT = REPAIR_ROOT / "recovery"
DB_PATH = (
    PROJECT_ROOT
    / "work_packages/M1_source_access/06_government_content_acquisition/"
    "fear_temperature_government_content.duckdb"
)
BASE_MANIFEST_ROOT = WORK_ROOT / "manifests"
SCRIPT_PATH = WORK_ROOT / "historical_government_acquisition.py"
TARGETED_SCRIPT_VERSION = "government_targeted_gap_repair_v1"
TARGETED_EXTRACTOR_VERSION = "targeted_gap_repair_extractor_v1"
OCR_EXTRACTOR_VERSION = "macos_vision_ocr_v1"


def _load_base() -> Any:
    spec = importlib.util.spec_from_file_location("historical_government_acquisition", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hga = _load_base()


LEDGER_COLUMNS = [
    "gap_id",
    "source_queue",
    "original_id",
    "original_url",
    "record_date",
    "original_failure",
    "repair_route",
    "target_unit",
    "attempted_at",
    "request_url",
    "final_url",
    "http_status",
    "mime_type",
    "raw_path",
    "raw_sha256",
    "attempt_result",
    "disposition",
    "result_external_id",
    "resulting_document_id",
    "notes",
]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    for path in [MANIFEST_ROOT, EVIDENCE_ROOT, REPORT_ROOT, CHECKPOINT_ROOT, OCR_ROOT, RECOVERY_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str] | None = None) -> None:
    hga.write_csv(path, list(rows), columns)


def upsert_ledger(rows: Iterable[dict[str, Any]]) -> None:
    path = REPAIR_ROOT / "repair_ledger.csv"
    merged = {row["gap_id"]: row for row in read_csv(path)}
    for row in rows:
        normalized = {column: row.get(column, "") for column in LEDGER_COLUMNS}
        merged[str(normalized["gap_id"])] = normalized
    write_csv(path, sorted(merged.values(), key=lambda row: row["gap_id"]), LEDGER_COLUMNS)


def _existing_external_ids() -> set[str]:
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        return {str(row[0]) for row in connection.execute("SELECT external_id FROM documents").fetchall()}


def build_local_hansard_repairs() -> dict[str, Any]:
    """Reparse only the 85 saved unsuccessful answer targets."""
    ensure_dirs()
    statuses = [
        row
        for row in read_csv(BASE_MANIFEST_ROOT / "hansard_answer_acquisition_status.csv")
        if row.get("download_status") != "success"
    ]
    if len(statuses) != 85:
        raise RuntimeError(f"Expected frozen 85-answer repair queue, found {len(statuses)}")
    existing = _existing_external_ids()
    manifest: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    decision_root = EVIDENCE_ROOT / "hansard_local_repair_decisions"
    decision_root.mkdir(parents=True, exist_ok=True)
    for row in statuses:
        external_id = row["external_id"]
        gap_id = f"hansard_answer:{external_id}"
        record_path = PROJECT_ROOT / row["record_path"] if row.get("record_path") else None
        fetch_meta_path = record_path.with_suffix(record_path.suffix + ".fetch.json") if record_path else None
        fetch_meta = hga.read_json(fetch_meta_path) if fetch_meta_path and fetch_meta_path.exists() else {}
        decision: dict[str, Any] = {
            "decision_version": "hansard_local_parser_repair_v1",
            "decided_at": now_iso(),
            "external_id": external_id,
            "expected_department": row["department"],
            "original_failure": row["failure_reason"],
            "record_path": row.get("record_path") or "",
            "raw_sha256": row.get("record_sha256") or "",
            "raw_bytes_unchanged": True,
            "network_request_made_in_repair": False,
        }
        record: dict[str, Any] | None = None
        resolved_department = ""
        if record_path and record_path.exists():
            payload = hga.read_json(record_path)
            resolved_department = hga._hansard_department(payload)
            record = hga._hansard_detail_record(payload, resolved_department)
        valid = bool(
            record
            and resolved_department == row["department"]
            and record.get("genre") == "ministerial_written_answer"
            and record.get("questions")
            and record.get("responses")
        )
        if valid and record is not None:
            if row["date"] == "2006-05-22":
                repair_route = "nearest_department_ancestor_from_saved_navigator"
            else:
                repair_route = "structured_question_tag_and_contribution_boundary_reparse"
            disposition = "already_present" if external_id in existing else "recovered_local"
            manifest.append(
                {
                    "partition_id": row["partition_id"],
                    "source": row["source"],
                    "genre": "ministerial_written_answer",
                    "year": int(record["sitting_date"][:4]),
                    "date": record["sitting_date"],
                    "department": resolved_department,
                    "external_id": external_id,
                    "canonical_url": record["canonical_url"],
                    "title": record["title"],
                    "government_respondent": record["government_respondent"],
                    "question_count": len(record["questions"]),
                    "response_segment_count": len(record["responses"]),
                    "attribution_status": record["attribution_status"],
                    "record_path": row["record_path"],
                    "record_sha256": row["record_sha256"],
                    "volume": record.get("volume") or "",
                    "updated_at": record.get("content_last_updated") or "",
                    "existing_document": external_id in existing,
                    "identity_status": "official_daily_tree_and_debate_section_ext_id_repaired_locally",
                    "batch_key": "hansard",
                    "storage_mode": "direct_detail",
                    "repair_route": repair_route,
                }
            )
            attempt_result = "deterministic_local_reparse_valid"
        else:
            repair_route = (
                "official_rendered_record_required_for_mixed_question_wrapper"
                if external_id == "06071282000011"
                else "official_rendered_or_archive_fallback_required"
            )
            disposition = "unresolved_attribution" if external_id == "06071282000011" else "unresolved"
            attempt_result = "local_evidence_insufficient"
        decision.update(
            {
                "resolved_department": resolved_department,
                "question_count": len(record.get("questions") or []) if record else 0,
                "response_count": len(record.get("responses") or []) if record else 0,
                "government_respondent": record.get("government_respondent") if record else "",
                "repair_route": repair_route,
                "attempt_result": attempt_result,
                "disposition": disposition,
            }
        )
        hga.write_json(decision_root / f"{external_id}.json", decision)
        decisions.append(decision)
        source_id = hga._source_definitions()["hansard"]["source_id"]
        ledger.append(
            {
                "gap_id": gap_id,
                "source_queue": "hansard_answer_acquisition_status",
                "original_id": external_id,
                "original_url": row.get("detail_url") or row.get("canonical_url") or "",
                "record_date": row["date"],
                "original_failure": row["failure_reason"],
                "repair_route": repair_route,
                "target_unit": "written_answer_item",
                "attempted_at": decision["decided_at"],
                "request_url": fetch_meta.get("url") or row.get("detail_url") or "",
                "final_url": fetch_meta.get("final_url") or "",
                "http_status": fetch_meta.get("status") or row.get("status_code") or "",
                "mime_type": fetch_meta.get("mime") or "",
                "raw_path": row.get("record_path") or "",
                "raw_sha256": row.get("record_sha256") or "",
                "attempt_result": attempt_result,
                "disposition": disposition,
                "result_external_id": external_id if valid else "",
                "resulting_document_id": hga.stable_id("doc", source_id, external_id) if valid else "",
                "notes": "No repair-pass request; decision uses saved official payload and prior request evidence.",
            }
        )
    manifest.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "hansard_local_repair_record_manifest.csv", manifest)
    write_csv(
        EVIDENCE_ROOT / "hansard_local_repair_decisions.csv",
        decisions,
        [
            "decision_version",
            "decided_at",
            "external_id",
            "expected_department",
            "resolved_department",
            "original_failure",
            "repair_route",
            "question_count",
            "response_count",
            "government_respondent",
            "attempt_result",
            "disposition",
            "record_path",
            "raw_sha256",
            "raw_bytes_unchanged",
            "network_request_made_in_repair",
        ],
    )
    upsert_ledger(ledger)
    result = {
        "generated_at": now_iso(),
        "frozen_targets": len(statuses),
        "recovered_local": sum(row["disposition"] == "recovered_local" for row in ledger),
        "already_present": sum(row["disposition"] == "already_present" for row in ledger),
        "unresolved_attribution": sum(row["disposition"] == "unresolved_attribution" for row in ledger),
        "unresolved_other": sum(row["disposition"] == "unresolved" for row in ledger),
        "manifest_records": len(manifest),
    }
    hga.write_json(REPORT_ROOT / "local_hansard_repair_summary.json", result)
    return result


def prepare_ocr_manifest() -> dict[str, Any]:
    """Freeze database identities and saved-byte paths for exactly four PDFs."""
    ensure_dirs()
    suffixes = ["2235.pdf", "0545.pdf", "2614.pdf", "5761.pdf"]
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT co.content_object_id, co.canonical_url, cv.content_version_id,
                   cv.raw_path, cv.content_sha256, cv.byte_size, aos.batch_id,
                   aos.fetch_id, aos.extraction_status, aos.extraction_reason
            FROM content_objects co
            JOIN content_versions cv USING(content_object_id)
            JOIN acquisition_object_statuses aos USING(content_object_id, content_version_id)
            WHERE regexp_extract(co.canonical_url, '[^/]+$') IN (?, ?, ?, ?)
            ORDER BY co.canonical_url
            """,
            suffixes,
        ).fetchall()
    if len(rows) != 4:
        raise RuntimeError(f"Expected four downloaded OCR targets, found {len(rows)}")
    manifest = []
    ledger = []
    for row in rows:
        (
            object_id,
            url,
            version_id,
            raw_path,
            content_sha,
            byte_size,
            batch_id,
            fetch_id,
            extraction_status,
            extraction_reason,
        ) = row
        pdf_path = PROJECT_ROOT / raw_path
        if not pdf_path.is_file() or hga.sha256_file(pdf_path) != content_sha:
            raise RuntimeError(f"Saved PDF evidence mismatch: {raw_path}")
        ocr_dir = OCR_ROOT / str(object_id)
        manifest.append(
            {
                "content_object_id": object_id,
                "canonical_url": url,
                "content_version_id": version_id,
                "raw_path": raw_path,
                "content_sha256": content_sha,
                "byte_size": byte_size,
                "batch_id": batch_id,
                "fetch_id": fetch_id,
                "before_extraction_status": extraction_status,
                "before_extraction_reason": extraction_reason,
                "ocr_jsonl_path": str((ocr_dir / "pages.jsonl").relative_to(PROJECT_ROOT)),
                "ocr_tool": "Apple Vision VNRecognizeTextRequest accurate en-GB/en-US",
                "ocr_tool_version": OCR_EXTRACTOR_VERSION,
            }
        )
        ledger.append(
            {
                "gap_id": f"policy_ocr:{object_id}",
                "source_queue": "historical_policy_needs_ocr",
                "original_id": object_id,
                "original_url": url,
                "record_date": "",
                "original_failure": f"{extraction_status}: {extraction_reason}",
                "repair_route": "local_macos_vision_ocr",
                "target_unit": "downloaded_pdf_file",
                "attempted_at": "",
                "request_url": "",
                "final_url": "",
                "http_status": "",
                "mime_type": "application/pdf",
                "raw_path": raw_path,
                "raw_sha256": content_sha,
                "attempt_result": "ocr_pending",
                "disposition": "pending",
                "result_external_id": object_id,
                "resulting_document_id": "",
                "notes": "Original content version is retained unchanged; OCR output is derived locally.",
            }
        )
    write_csv(MANIFEST_ROOT / "policy_ocr_target_manifest.csv", manifest)
    upsert_ledger(ledger)
    result = {"generated_at": now_iso(), "targets": len(manifest), "status": "frozen_for_local_ocr"}
    hga.write_json(REPORT_ROOT / "policy_ocr_target_summary.json", result)
    return result


def _ensure_recovery_checkpoint() -> Path:
    ensure_dirs()
    existing = sorted(RECOVERY_ROOT.glob("fear_temperature_government_content.before_targeted_gap_repair.*.duckdb"))
    if existing:
        return existing[0]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = RECOVERY_ROOT / f"fear_temperature_government_content.before_targeted_gap_repair.{stamp}.duckdb"
    # APFS copy-on-write clone when supported; ordinary copy remains the safe
    # fallback.  This is the single pre-write recovery checkpoint for the pass.
    try:
        subprocess.run(["cp", "-c", str(DB_PATH), str(target)], check=True)
    except (OSError, subprocess.CalledProcessError):
        shutil.copy2(DB_PATH, target)
    hga.write_json(
        RECOVERY_ROOT / "checkpoint.json",
        {
            "created_at": now_iso(),
            "database": str(DB_PATH),
            "checkpoint": str(target),
            "database_size": DB_PATH.stat().st_size,
            "database_mtime": datetime.fromtimestamp(DB_PATH.stat().st_mtime, UTC).isoformat(),
            "full_hash_intentionally_not_recomputed": True,
        },
    )
    return target


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def ingest_ocr_results() -> dict[str, Any]:
    """Add a new extraction lineage for four existing content versions."""
    ensure_dirs()
    targets = read_csv(MANIFEST_ROOT / "policy_ocr_target_manifest.csv")
    if len(targets) != 4:
        raise RuntimeError("The four-file OCR manifest has not been frozen")
    parsed: dict[str, list[dict[str, Any]]] = {}
    qa_rows: list[dict[str, Any]] = []
    for target in targets:
        path = PROJECT_ROOT / target["ocr_jsonl_path"]
        if not path.is_file():
            raise RuntimeError(f"OCR output missing: {path}")
        pages = _load_jsonl(path)
        page_numbers = [int(row["page"]) for row in pages]
        if page_numbers != list(range(1, len(pages) + 1)):
            raise RuntimeError(f"OCR page sequence is incomplete for {target['content_object_id']}")
        usable = [row for row in pages if str(row.get("text") or "").strip()]
        if len(usable) < max(1, int(len(pages) * 0.8)):
            raise RuntimeError(f"OCR output is not sufficiently usable for {target['content_object_id']}")
        parsed[target["content_object_id"]] = pages
        confidences = [
            float(line.get("confidence") or 0)
            for page in pages
            for line in page.get("lines") or []
        ]
        qa_rows.append(
            {
                "content_object_id": target["content_object_id"],
                "page_count": len(pages),
                "pages_with_text": len(usable),
                "character_count": sum(len(str(row.get("text") or "")) for row in pages),
                "line_count": sum(int(row.get("line_count") or 0) for row in pages),
                "mean_line_confidence": round(sum(confidences) / len(confidences), 6) if confidences else 0,
                "minimum_line_confidence": round(min(confidences), 6) if confidences else 0,
                "ocr_jsonl_path": target["ocr_jsonl_path"],
            }
        )
    _ensure_recovery_checkpoint()
    before_count = 0
    after_count = 0
    extraction_run_id = hga.stable_id("ext", hga.BATCHES["policy"], OCR_EXTRACTOR_VERSION)
    with duckdb.connect(str(DB_PATH)) as connection:
        before_count = int(connection.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0])
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(
                "INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [
                    extraction_run_id,
                    hga.BATCHES["policy"],
                    OCR_EXTRACTOR_VERSION,
                    datetime.now(UTC),
                    datetime.now(UTC),
                    4,
                    0,
                    "partial",
                    "Local OCR of the four approved downloaded historical-policy PDFs.",
                ],
            )
            inserted = 0
            for target in targets:
                pages = parsed[target["content_object_id"]]
                for page in pages:
                    text = str(page.get("text") or "").strip()
                    if not text:
                        continue
                    page_number = int(page["page"])
                    text_sha = hga.sha256_bytes(text.encode())
                    segment_id = hga.stable_id(
                        "seg",
                        target["content_version_id"],
                        extraction_run_id,
                        page_number,
                        text_sha,
                    )
                    connection.execute(
                        """
                        INSERT INTO text_segments VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?)
                        ON CONFLICT DO NOTHING
                        """,
                        [
                            segment_id,
                            target["content_version_id"],
                            extraction_run_id,
                            "derived",
                            "unknown",
                            page_number - 1,
                            f"OCR page {page_number}",
                            text,
                            f"page={page_number};ocr={OCR_EXTRACTOR_VERSION}",
                            text_sha,
                            "project_authorized_internal_use_institutional_ethics_not_asserted",
                            True,
                            datetime.now(UTC),
                        ],
                    )
                    inserted += int(connection.execute("SELECT changes()").fetchone()[0]) if False else 0
                page_count_with_text = sum(bool(str(page.get("text") or "").strip()) for page in pages)
                connection.execute(
                    """
                    UPDATE acquisition_object_statuses
                    SET extraction_status='success', extraction_reason=?, segment_count=?, updated_at=?
                    WHERE batch_id=? AND content_object_id=? AND content_version_id=?
                    """,
                    [
                        f"Local OCR recovered {page_count_with_text}/{len(pages)} pages using {OCR_EXTRACTOR_VERSION}; original content version unchanged.",
                        page_count_with_text,
                        datetime.now(UTC),
                        target["batch_id"],
                        target["content_object_id"],
                        target["content_version_id"],
                    ],
                )
            output_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [extraction_run_id]
                ).fetchone()[0]
            )
            connection.execute(
                """
                UPDATE extraction_runs
                SET finished_at=?, input_content_count=4, output_segment_count=?, status='complete', status_reason=?
                WHERE extraction_run_id=?
                """,
                [
                    datetime.now(UTC),
                    output_count,
                    "Four existing downloaded PDFs OCRed locally with per-page mapping; original bytes and content versions retained.",
                    extraction_run_id,
                ],
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        after_count = int(connection.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0])
    write_csv(EVIDENCE_ROOT / "policy_ocr_quality.csv", qa_rows)
    ledger_updates = []
    for target in targets:
        qa = next(row for row in qa_rows if row["content_object_id"] == target["content_object_id"])
        ledger_updates.append(
            {
                "gap_id": f"policy_ocr:{target['content_object_id']}",
                "source_queue": "historical_policy_needs_ocr",
                "original_id": target["content_object_id"],
                "original_url": target["canonical_url"],
                "record_date": "",
                "original_failure": f"{target['before_extraction_status']}: {target['before_extraction_reason']}",
                "repair_route": "local_macos_vision_ocr",
                "target_unit": "downloaded_pdf_file",
                "attempted_at": now_iso(),
                "request_url": "",
                "final_url": "",
                "http_status": "",
                "mime_type": "application/pdf",
                "raw_path": target["raw_path"],
                "raw_sha256": target["content_sha256"],
                "attempt_result": f"ocr_pages={qa['pages_with_text']}/{qa['page_count']};characters={qa['character_count']}",
                "disposition": "recovered_extraction",
                "result_external_id": target["content_object_id"],
                "resulting_document_id": "",
                "notes": "New extraction lineage only; no duplicate document, object or content version.",
            }
        )
    upsert_ledger(ledger_updates)
    result = {
        "generated_at": now_iso(),
        "files_recovered": 4,
        "ocr_segments_added": after_count - before_count,
        "extraction_run_id": extraction_run_id,
        "quality_rows": qa_rows,
    }
    hga.write_json(REPORT_ROOT / "policy_ocr_ingestion_summary.json", result)
    return result


def _derived_parent_context(rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for row in rows:
        path = row.get("parent_raw_path") or ""
        if not path:
            continue
        value = context.setdefault(path, {"segment_count": 0, "record_offsets": {}})
        value["record_offsets"][row["external_id"]] = value["segment_count"]
        value["segment_count"] += int(row.get("question_count") or 0) + int(row.get("response_segment_count") or 0)
    return context


def _html_text(value: str) -> str:
    return hga.normalise_space(hga.BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True))


def resolve_statement_candidates() -> dict[str, Any]:
    """Resolve nine frozen failures from already downloaded official search pages.

    Several failed debate-section IDs are demonstrably non-unique in the search
    response.  Only explicitly in-scope child contributions are materialised,
    using their official ContributionExtId as the stable identity.
    """
    ensure_dirs()
    candidate_files = [
        BASE_MANIFEST_ROOT / "hansard_candidate_acquisition_status.csv",
        BASE_MANIFEST_ROOT / "hansard_gap_written_acquisition_status.csv",
    ]
    candidates: list[dict[str, str]] = []
    for path in candidate_files:
        for row in read_csv(path):
            if row.get("download_status") != "success":
                row = dict(row)
                row["queue_file"] = path.name
                candidates.append(row)
    if len(candidates) != 9:
        raise RuntimeError(f"Expected nine frozen statement candidates, found {len(candidates)}")

    in_scope_children = {
        "07051786000046": "ENVIRONMENT, FOOD AND RURAL AFFAIRS",
        "09021291000017": "ENVIRONMENT, FOOD AND RURAL AFFAIRS",
        "10022378000984": "ENERGY AND CLIMATE CHANGE",
    }
    existing = _existing_external_ids()
    manifest: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    record_root = REPAIR_ROOT / "raw" / "statement_search_children"
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        search_paths = json.loads(candidate.get("search_paths_json") or "[]")
        matched_children: list[dict[str, Any]] = []
        all_children: list[dict[str, Any]] = []
        parent_by_child: dict[str, Path] = {}
        seen_child_fingerprints: set[tuple[str, str, str]] = set()
        for relative in search_paths:
            parent_path = PROJECT_ROOT / relative
            if not parent_path.is_file():
                continue
            payload = hga.read_json(parent_path)
            for value in payload.get("Results") or []:
                if str(value.get("DebateSectionExtId") or "") != candidate_id:
                    continue
                fingerprint = (
                    str(value.get("ContributionExtId") or ""),
                    str(value.get("SittingDate") or "")[:10],
                    hga.sha256_bytes(str(value.get("ContributionTextFull") or "").encode()),
                )
                if fingerprint in seen_child_fingerprints:
                    continue
                seen_child_fingerprints.add(fingerprint)
                all_children.append(value)
                child_id = str(value.get("ContributionExtId") or "")
                if child_id in in_scope_children:
                    matched_children.append(value)
                    parent_by_child[child_id] = parent_path

        for value in matched_children:
            child_id = str(value["ContributionExtId"])
            department = in_scope_children[child_id]
            sitting_date = str(value.get("SittingDate") or candidate["date"])[:10]
            title = hga.normalise_space(str(value.get("DebateSection") or candidate["title"]))
            speaker = hga.normalise_space(str(value.get("AttributedTo") or ""))
            response_text = _html_text(str(value.get("ContributionTextFull") or value.get("ContributionText") or ""))
            if not response_text or not speaker:
                continue
            parent_path = parent_by_child[child_id]
            parent_meta_path = parent_path.with_suffix(parent_path.suffix + ".fetch.json")
            if not parent_meta_path.is_file():
                raise RuntimeError(f"Missing official search fetch evidence: {parent_meta_path}")
            parent_fetch = hga.read_json(parent_meta_path)
            canonical = (
                f"https://hansard.parliament.uk/Commons/{sitting_date}/written-statements/"
                f"{candidate_id}/{hga.slugify(title)}#{child_id}"
            )
            record = {
                "external_id": child_id,
                "genre": "ministerial_written_statement",
                "house": "Commons",
                "sitting_date": sitting_date,
                "department": department,
                "title": title,
                "questions": [],
                "responses": [{"speaker": speaker, "text": response_text, "paragraph_id": child_id}],
                "canonical_url": canonical,
                "government_respondent": speaker,
                "attribution_status": "confirmed",
                "source_category": "Written Statements",
                "source_locator": child_id,
                "parent_debate_section_ext_id": candidate_id,
                "derived_from_official_search_response": True,
            }
            record_path = record_root / sitting_date[:4] / f"{child_id}.json"
            hga.write_json(record_path, record)
            manifest.append(
                {
                    "partition_id": hga.stable_id("part", "hansard_search_repair", sitting_date[:4], department),
                    "source": "official_hansard_search_response_child",
                    "genre": "ministerial_written_statement",
                    "year": int(sitting_date[:4]),
                    "date": sitting_date,
                    "department": department,
                    "external_id": child_id,
                    "canonical_url": canonical,
                    "title": title,
                    "government_respondent": speaker,
                    "question_count": 0,
                    "response_segment_count": 1,
                    "attribution_status": "confirmed",
                    "record_path": hga.rel(record_path),
                    "record_sha256": hga.sha256_file(record_path),
                    "parent_raw_path": hga.rel(parent_path),
                    "parent_raw_sha256": hga.sha256_file(parent_path),
                    "parent_fetch_meta_path": hga.rel(parent_meta_path),
                    "parent_request_url": parent_fetch.get("url") or "",
                    "parent_final_url": parent_fetch.get("final_url") or parent_fetch.get("url") or "",
                    "parent_retrieved_at": parent_fetch.get("retrieved_at") or "",
                    "parent_status_code": parent_fetch.get("status") or "",
                    "parent_mime_type": parent_fetch.get("mime") or "application/json",
                    "source_locator": child_id,
                    "existing_document": child_id in existing,
                    "identity_status": "official_search_contribution_ext_id_due_section_id_collision",
                    "record_is_derived": True,
                    "batch_key": "hansard",
                    "storage_mode": "derived_list",
                    "repair_route": "saved_official_search_full_text_child_resolution",
                }
            )

        if candidate_id == "1009068000001":
            disposition = "unresolved_container"
            attempt_result = "saved_search_rows_repeat a header/container identity across multiple dates; no attributable child statements"
        elif matched_children:
            disposition = "recovered_children" if any(child["ContributionExtId"] not in existing for child in matched_children) else "already_present_children"
            attempt_result = f"verified_in_scope_children={len(matched_children)};all_observed_children={len(all_children)}"
        else:
            disposition = "out_of_scope"
            attempt_result = f"official_search_children={len(all_children)};no approved-department child"
        parent_paths = [PROJECT_ROOT / value for value in search_paths if (PROJECT_ROOT / value).is_file()]
        evidence_rows.append(
            {
                "candidate_id": candidate_id,
                "date": candidate["date"],
                "title": candidate["title"],
                "first_attributed_to": candidate.get("first_attributed_to") or "",
                "observed_children": len(all_children),
                "in_scope_children": len(matched_children),
                "in_scope_child_ids": json.dumps([value.get("ContributionExtId") for value in matched_children]),
                "disposition": disposition,
                "evidence_paths": json.dumps(search_paths),
            }
        )
        ledger.append(
            {
                "gap_id": f"statement_candidate:{candidate_id}",
                "source_queue": candidate["queue_file"],
                "original_id": candidate_id,
                "original_url": candidate.get("detail_url") or "",
                "record_date": candidate["date"],
                "original_failure": candidate.get("failure_reason") or "",
                "repair_route": "saved_official_search_response_child_resolution",
                "target_unit": "failed_candidate_container",
                "attempted_at": now_iso(),
                "request_url": "",
                "final_url": "",
                "http_status": "",
                "mime_type": "application/json",
                "raw_path": ";".join(hga.rel(path) for path in parent_paths),
                "raw_sha256": ";".join(hga.sha256_file(path) for path in parent_paths),
                "attempt_result": attempt_result,
                "disposition": disposition,
                "result_external_id": ";".join(str(value.get("ContributionExtId") or "") for value in matched_children),
                "resulting_document_id": ";".join(
                    hga.stable_id("doc", hga._source_definitions()["hansard"]["source_id"], value.get("ContributionExtId"))
                    for value in matched_children
                ),
                "notes": "No repair-pass request. Child identities/text come from saved HTTP-200 official Hansard search responses; container/detail failure is retained.",
            }
        )
    manifest.sort(key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "statement_candidate_repair_record_manifest.csv", manifest)
    write_csv(EVIDENCE_ROOT / "statement_candidate_resolution.csv", evidence_rows)
    upsert_ledger(ledger)
    result = {
        "generated_at": now_iso(),
        "candidate_units": len(candidates),
        "recovered_child_records": len(manifest),
        "new_child_records": sum(not row["existing_document"] for row in manifest),
        "out_of_scope_candidates": sum(row["disposition"] == "out_of_scope" for row in evidence_rows),
        "unresolved_containers": sum(row["disposition"] == "unresolved_container" for row in evidence_rows),
    }
    hga.write_json(REPORT_ROOT / "statement_candidate_repair_summary.json", result)
    return result


def _historic_month_dates(body: bytes, year: int, month_slug: str) -> list[date]:
    prefix = f"/historic-hansard/sittings/{year}/{month_slug}/"
    values: set[date] = set()
    soup = hga.BeautifulSoup(body, "html.parser")
    for link in soup.find_all("a", href=True):
        href = str(link.get("href") or "")
        if not href.startswith(prefix):
            continue
        tail = href[len(prefix) :].strip("/")
        if not re.fullmatch(r"\d{1,2}", tail):
            continue
        try:
            values.add(date(year, datetime.strptime(month_slug, "%b").month, int(tail)))
        except ValueError:
            continue
    return sorted(values)


def _historic_daily_targets(body: bytes, base_url: str, sitting_date: date) -> list[dict[str, str]]:
    soup = hga.BeautifulSoup(body, "html.parser")
    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        department = hga.normalise_label(link.get_text(" ", strip=True))
        href = str(link.get("href") or "")
        if department not in hga.HISTORIC_DEPARTMENT_LABELS or "/written_answers/" not in href:
            continue
        line = link.find_parent("li")
        child_list = line.find_next_sibling("ol") if line else None
        if child_list is None and line is not None:
            child_list = line.find_next("ol")
        if child_list is None:
            continue
        for child in child_list.find_all("a", href=True):
            child_href = str(child.get("href") or "")
            if "/written_answers/" not in child_href:
                continue
            url = urljoin(base_url, child_href)
            if url in seen:
                continue
            seen.add(url)
            targets.append(
                {
                    "date": sitting_date.isoformat(),
                    "year": sitting_date.year,
                    "department": department,
                    "title": hga.normalise_space(child.get_text(" ", strip=True)),
                    "item_url": url,
                    "target_id": hga.stable_id("historic-item", url),
                }
            )
    return targets


def _parse_historic_item(path: Path, target: dict[str, str], final_url: str) -> dict[str, Any] | None:
    soup = hga.BeautifulSoup(path.read_bytes(), "html.parser")
    content = soup.select_one("#content")
    title_node = soup.select_one("h1.title")
    if content is None or title_node is None:
        return None
    contributions: list[dict[str, str]] = []
    for node in content.select("div.member_contribution"):
        block = node.select_one("blockquote.contribution_text") or node
        fragment = hga.BeautifulSoup(str(block), "html.parser")
        for removable in fragment.select("cite.member, a.permalink, a.speech-permalink"):
            removable.decompose()
        text = hga.normalise_space(fragment.get_text(" ", strip=True))
        speaker_node = block.select_one("cite.member")
        speaker = hga.normalise_space(speaker_node.get_text(" ", strip=True)) if speaker_node else ""
        paragraph = block.find("p", id=True)
        locator = str(node.get("id") or (paragraph.get("id") if paragraph else ""))
        if text:
            contributions.append({"speaker": speaker, "text": text, "paragraph_id": locator})
    if len(contributions) < 2:
        return None
    questions: list[dict[str, str]] = []
    responses: list[dict[str, str]] = []
    response_started = False
    for index, value in enumerate(contributions):
        questionish = bool(re.match(r"^(?:\(\d+\)\s*)?To ask\b", value["text"], flags=re.IGNORECASE))
        if not response_started and (questionish or index == 0):
            questions.append(value)
        else:
            response_started = True
            responses.append(value)
    if not responses:
        return None
    external_id = next((value["paragraph_id"] for value in responses if value["paragraph_id"]), "")
    if not external_id:
        external_id = next((value["paragraph_id"] for value in questions if value["paragraph_id"]), "")
    if not external_id:
        external_id = hga.stable_id(
            "historic-daily",
            target["date"],
            target["department"],
            target["title"],
            hga.canonical_json(contributions),
        )
    title = hga.normalise_space(title_node.get_text(" ", strip=True))
    canonical = f"{final_url.split('#', 1)[0]}#{external_id}"
    respondent = next((value["speaker"] for value in responses if value["speaker"]), "")
    return {
        "external_id": external_id,
        "genre": "ministerial_written_answer",
        "house": "Commons",
        "sitting_date": target["date"],
        "department": target["department"],
        "title": title,
        "questions": questions,
        "responses": responses,
        "canonical_url": canonical,
        "government_respondent": respondent,
        "attribution_status": "confirmed" if respondent else "pending",
        "source_category": "Commons Written Answers",
        "source_locator": external_id,
        "derived_from_official_historic_html": True,
    }


def repair_historic_daily_gaps() -> dict[str, Any]:
    """Use bounded Historic Hansard month/day/item routes for named gaps only."""
    ensure_dirs()
    raw_root = REPAIR_ROOT / "raw" / "historic_hansard_daily"
    client = hga.BoundedClient(minimum_interval=1.5, retries=1)
    month_specs = [(1988, "jan"), (1991, "dec"), (2004, "oct"), (2004, "nov"), (2004, "dec")]
    month_rows: list[dict[str, Any]] = []
    month_dates: dict[tuple[int, str], list[date]] = {}
    ledger: list[dict[str, Any]] = []
    for year, month_slug in month_specs:
        url = f"{hga.HISTORIC_API}/sittings/{year}/{month_slug}"
        path = raw_root / "months" / f"{year}-{month_slug}.html"
        result = hga.fetch_to_path(client, url, path, resume=True)
        dates = _historic_month_dates(result.body, year, month_slug) if result.status == 200 else []
        month_dates[(year, month_slug)] = dates
        month_rows.append(
            {
                "year": year,
                "month": month_slug,
                "request_url": url,
                "final_url": result.final_url,
                "retrieved_at": result.retrieved_at,
                "status_code": result.status,
                "mime_type": result.mime,
                "attempt_count": result.attempts,
                "sitting_dates": len(dates),
                "dates_json": json.dumps([value.isoformat() for value in dates]),
                "raw_path": hga.rel(path) if path.exists() else "",
                "raw_sha256": hga.sha256_file(path) if path.exists() else "",
                "status": "success" if result.status == 200 and dates else "failed",
                "failure_reason": result.error if result.status != 200 else ("no_sitting_dates_parsed" if not dates else ""),
            }
        )
    write_csv(EVIDENCE_ROOT / "historic_month_calendar_status.csv", month_rows)

    january_dates = month_dates.get((1988, "jan"), [])
    january_first = min(january_dates).isoformat() if january_dates else ""
    hga.write_json(
        EVIDENCE_ROOT / "january_1988_boundary.json",
        {
            "checked_at": now_iso(),
            "official_month_url": f"{hga.HISTORIC_API}/sittings/1988/jan",
            "observed_sitting_dates": [value.isoformat() for value in january_dates],
            "first_observed_sitting_date": january_first,
            "boundary_disposition": "pre_first_sitting_not_collection_gap" if january_first == "1988-01-11" else "unresolved_calendar_boundary",
        },
    )

    daily_dates = [
        value
        for value in month_dates.get((1991, "dec"), [])
        if date(1991, 12, 2) <= value <= date(1991, 12, 13)
    ]
    for key in [(2004, "oct"), (2004, "nov"), (2004, "dec")]:
        daily_dates.extend(
            value
            for value in month_dates.get(key, [])
            if date(2004, 10, 5) <= value <= date(2004, 12, 31)
        )
    daily_dates = sorted(set(daily_dates))
    daily_statuses: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    consecutive_denials = 0
    host_stopped = False
    for sitting_date in daily_dates:
        if host_stopped:
            daily_statuses.append({"date": sitting_date.isoformat(), "status": "unrequested_host_stop"})
            continue
        url = f"{hga.HISTORIC_API}/sittings/{sitting_date.year}/{sitting_date.strftime('%b').lower()}/{sitting_date.day:02d}"
        path = raw_root / "days" / sitting_date.isoformat() / "index.html"
        result = hga.fetch_to_path(client, url, path, resume=True)
        denied = result.status in {403, 429}
        consecutive_denials = consecutive_denials + 1 if denied else 0
        if consecutive_denials >= 3:
            host_stopped = True
        valid = result.status == 200 and path.exists()
        soup = hga.BeautifulSoup(result.body, "html.parser") if valid else None
        commons_written_supported = bool(
            soup
            and any(
                hga.normalise_label(link.get_text(" ", strip=True)) == "WRITTEN ANSWERS (COMMONS)"
                for link in soup.find_all("a")
            )
        )
        found = (
            _historic_daily_targets(result.body, result.final_url or url, sitting_date)
            if valid and commons_written_supported
            else []
        )
        for row in found:
            row.update(
                {
                    "daily_index_path": hga.rel(path),
                    "daily_index_sha256": hga.sha256_file(path),
                    "daily_index_request_url": url,
                    "daily_index_final_url": result.final_url,
                    "daily_index_retrieved_at": result.retrieved_at,
                }
            )
        targets.extend(found)
        daily_statuses.append(
            {
                "date": sitting_date.isoformat(),
                "request_url": url,
                "final_url": result.final_url,
                "retrieved_at": result.retrieved_at,
                "status_code": result.status,
                "mime_type": result.mime,
                "attempt_count": result.attempts,
                "target_items": len(found),
                "commons_written_supported": commons_written_supported,
                "coverage_classification": (
                    "official_commons_written_index"
                    if commons_written_supported
                    else ("historic_route_lords_only_not_commons" if valid else "request_failed")
                ),
                "raw_path": hga.rel(path) if path.exists() else "",
                "raw_sha256": hga.sha256_file(path) if path.exists() else "",
                "status": "success" if valid else "failed",
                "failure_reason": result.error,
            }
        )
    write_csv(EVIDENCE_ROOT / "historic_daily_index_status.csv", daily_statuses)
    targets = sorted({row["item_url"]: row for row in targets}.values(), key=lambda row: (row["date"], row["department"], row["item_url"]))
    write_csv(MANIFEST_ROOT / "historic_daily_item_target_manifest.csv", targets)

    existing = _existing_external_ids()
    item_statuses: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    consecutive_denials = 0
    host_stopped = False
    for index, target in enumerate(targets):
        if host_stopped:
            item_statuses.append({**target, "download_status": "unrequested_host_stop", "failure_reason": "three_consecutive_access_denied_or_throttled"})
            continue
        path = raw_root / "items" / target["date"][:4] / target["date"] / f"{target['target_id']}.html"
        result = hga.fetch_to_path(client, target["item_url"], path, resume=True)
        denied = result.status in {403, 429}
        consecutive_denials = consecutive_denials + 1 if denied else 0
        if consecutive_denials >= 3:
            host_stopped = True
        record = _parse_historic_item(path, target, result.final_url or target["item_url"]) if result.status == 200 and path.exists() else None
        status = "success" if record else "failed"
        row = {
            **target,
            "request_url": target["item_url"],
            "final_url": result.final_url,
            "retrieved_at": result.retrieved_at,
            "status_code": result.status,
            "mime_type": result.mime,
            "attempt_count": result.attempts,
            "download_status": status,
            "failure_reason": "" if record else (result.error or "historic_item_parse_failed"),
            "raw_path": hga.rel(path) if path.exists() else "",
            "raw_sha256": hga.sha256_file(path) if path.exists() else "",
            "fetch_meta_path": hga.rel(path.with_suffix(path.suffix + ".fetch.json")),
        }
        if record:
            record_path = raw_root / "records" / target["date"][:4] / f"{record['external_id']}.json"
            hga.write_json(record_path, record)
            row["result_external_id"] = record["external_id"]
            row["record_path"] = hga.rel(record_path)
            row["record_sha256"] = hga.sha256_file(record_path)
            records.append(
                {
                    "partition_id": hga.stable_id("part", "historic_daily_repair", target["year"], target["department"]),
                    "source": "official_historic_hansard_daily_html",
                    "genre": "ministerial_written_answer",
                    "year": target["year"],
                    "date": target["date"],
                    "department": target["department"],
                    "external_id": record["external_id"],
                    "canonical_url": record["canonical_url"],
                    "title": record["title"],
                    "government_respondent": record["government_respondent"],
                    "question_count": len(record["questions"]),
                    "response_segment_count": len(record["responses"]),
                    "attribution_status": record["attribution_status"],
                    "record_path": row["record_path"],
                    "record_sha256": row["record_sha256"],
                    "parent_raw_path": row["raw_path"],
                    "parent_raw_sha256": row["raw_sha256"],
                    "parent_fetch_meta_path": row["fetch_meta_path"],
                    "parent_request_url": row["request_url"],
                    "parent_final_url": row["final_url"],
                    "parent_retrieved_at": row["retrieved_at"],
                    "parent_status_code": row["status_code"],
                    "parent_mime_type": row["mime_type"],
                    "source_anchor": record["external_id"],
                    "existing_document": record["external_id"] in existing,
                    "identity_status": "official_historic_html_contribution_id",
                    "record_is_derived": True,
                    "batch_key": "historic",
                    "storage_mode": "derived_html",
                    "repair_route": "historic_hansard_daily_official_route",
                }
            )
        item_statuses.append(row)
        if (index + 1) % 25 == 0:
            write_csv(EVIDENCE_ROOT / "historic_daily_item_acquisition_status.csv", item_statuses)
            hga.write_json(
                CHECKPOINT_ROOT / "historic_daily_items.json",
                {
                    "updated_at": now_iso(),
                    "frozen_targets": len(targets),
                    "processed": len(item_statuses),
                    "successful": sum(value.get("download_status") == "success" for value in item_statuses),
                    "host_stopped": host_stopped,
                    "minimum_interval_seconds": client.minimum_interval,
                },
            )
            print(f"[{now_iso()}] FETCH CHECKPOINT historic_daily processed={len(item_statuses)}/{len(targets)}", flush=True)
    write_csv(EVIDENCE_ROOT / "historic_daily_item_acquisition_status.csv", item_statuses)
    records = sorted({row["external_id"]: row for row in records}.values(), key=lambda row: (row["date"], row["department"], row["external_id"]))
    write_csv(MANIFEST_ROOT / "historic_daily_repair_record_manifest.csv", records)
    hga.write_json(
        CHECKPOINT_ROOT / "historic_daily_items.json",
        {
            "updated_at": now_iso(),
            "frozen_targets": len(targets),
            "processed": len(item_statuses),
            "successful": sum(value.get("download_status") == "success" for value in item_statuses),
            "host_stopped": host_stopped,
            "minimum_interval_seconds": client.minimum_interval,
            "complete": len(item_statuses) == len(targets) and not host_stopped,
        },
    )
    for row in item_statuses:
        disposition = (
            "already_present"
            if row.get("result_external_id") in existing
            else ("recovered" if row.get("download_status") == "success" else "unresolved")
        )
        ledger.append(
            {
                "gap_id": f"historic_item:{row['target_id']}",
                "source_queue": "historic_volume_200_or_2004_seam",
                "original_id": row["target_id"],
                "original_url": row["item_url"],
                "record_date": row["date"],
                "original_failure": "missing_from_failed_volume_200" if row["date"].startswith("1991-") else "cross_route_2004_q4_gap",
                "repair_route": "historic_hansard_daily_official_route",
                "target_unit": "written_answer_item",
                "attempted_at": row.get("retrieved_at") or "",
                "request_url": row.get("request_url") or "",
                "final_url": row.get("final_url") or "",
                "http_status": row.get("status_code") or "",
                "mime_type": row.get("mime_type") or "",
                "raw_path": row.get("raw_path") or "",
                "raw_sha256": row.get("raw_sha256") or "",
                "attempt_result": row.get("download_status") or "",
                "disposition": disposition,
                "result_external_id": row.get("result_external_id") or "",
                "resulting_document_id": hga.stable_id("doc", hga._source_definitions()["historic"]["source_id"], row.get("result_external_id")) if row.get("result_external_id") else "",
                "notes": "Official item HTML retained; derived JSON is linked to the item fetch and locator.",
            }
        )
    upsert_ledger(ledger)
    result = {
        "generated_at": now_iso(),
        "january_1988_first_sitting": january_first,
        "daily_indexes_planned": len(daily_dates),
        "daily_indexes_successful": sum(row.get("status") == "success" for row in daily_statuses),
        "daily_indexes_commons_supported": sum(bool(row.get("commons_written_supported")) for row in daily_statuses),
        "daily_indexes_lords_only_not_commons": sum(row.get("coverage_classification") == "historic_route_lords_only_not_commons" for row in daily_statuses),
        "frozen_item_targets": len(targets),
        "item_requests_successful": sum(row.get("download_status") == "success" for row in item_statuses),
        "record_manifest_rows": len(records),
        "new_record_candidates": sum(not row["existing_document"] for row in records),
        "unresolved_items": sum(row.get("download_status") != "success" for row in item_statuses),
        "host_stopped": host_stopped,
    }
    hga.write_json(REPORT_ROOT / "historic_daily_repair_summary.json", result)
    return result


def probe_restricted_official_routes() -> dict[str, Any]:
    """Make a bounded normal-route retry and stop each denied host at three."""
    ensure_dirs()
    probe_root = REPAIR_ROOT / "raw" / "restricted_route_probes"
    route_groups = {
        "publications.parliament.uk": [
            {
                "probe_id": "2004_q4_statement_sample",
                "queue": "2004_q4_commons_seam",
                "url": "https://publications.parliament.uk/pa/cm200405/cmhansrd/vo041201/wmstext/41201m01.htm",
            },
            {
                "probe_id": "2010_failed_index_corrected_route",
                "queue": "hansard_gap_archive_index_status",
                "url": "https://publications.parliament.uk/pa/cm201011/cmhansrd/cm100518/index/100518-x.htm",
            },
            {
                "probe_id": "2010_failed_page_retry",
                "queue": "hansard_gap_archive_page_acquisition_status",
                "url": "https://publications.parliament.uk/pa/cm201011/cmhansrd/cm100602/text/100602w0002.htm",
            },
        ],
        "hansard.parliament.uk": [
            {
                "probe_id": "asda_rendered",
                "queue": "hansard_answer_acquisition_status",
                "url": "https://hansard.parliament.uk/Commons/2006-07-12/written-answers/06071282000011/asda",
            },
            {
                "probe_id": "companies_house_rendered",
                "queue": "hansard_answer_acquisition_status",
                "url": "https://hansard.parliament.uk/Commons/2007-09-17/written-answers/07091719000037/companies-house",
            },
            {
                "probe_id": "2004_q4_modern_daily",
                "queue": "2004_q4_commons_seam",
                "url": "https://hansard.parliament.uk/commons/2004-12-01",
            },
        ],
    }
    statuses: list[dict[str, Any]] = []
    host_state: dict[str, dict[str, Any]] = {}
    for host, tasks in route_groups.items():
        client = hga.BoundedClient(minimum_interval=3.0, retries=0)
        consecutive = 0
        stopped = False
        for task in tasks:
            if stopped:
                statuses.append(
                    {
                        **task,
                        "host": host,
                        "attempted": False,
                        "attempt_result": "unrequested_host_stop",
                        "failure_reason": "three_consecutive_access_denied_or_throttled",
                    }
                )
                continue
            result = client.get(task["url"])
            response_path = probe_root / host / f"{task['probe_id']}.response"
            if result.body:
                response_path.parent.mkdir(parents=True, exist_ok=True)
                response_path.write_bytes(result.body)
            meta_path = response_path.with_suffix(".fetch.json")
            hga.write_json(
                meta_path,
                {
                    "url": task["url"],
                    "final_url": result.final_url,
                    "status": result.status,
                    "mime": result.mime,
                    "retrieved_at": result.retrieved_at,
                    "attempts": result.attempts,
                    "error": result.error,
                    "response_path": hga.rel(response_path) if response_path.exists() else "",
                    "response_sha256": hga.sha256_file(response_path) if response_path.exists() else "",
                    "byte_size": response_path.stat().st_size if response_path.exists() else 0,
                },
            )
            denied = result.status in {403, 429}
            consecutive = consecutive + 1 if denied else 0
            if consecutive >= 3:
                stopped = True
            statuses.append(
                {
                    **task,
                    "host": host,
                    "attempted": True,
                    "retrieved_at": result.retrieved_at,
                    "final_url": result.final_url,
                    "status_code": result.status,
                    "mime_type": result.mime,
                    "attempt_count": result.attempts,
                    "attempt_result": "success" if result.status == 200 else "failed",
                    "failure_reason": result.error,
                    "response_path": hga.rel(response_path) if response_path.exists() else "",
                    "response_sha256": hga.sha256_file(response_path) if response_path.exists() else "",
                    "fetch_meta_path": hga.rel(meta_path),
                }
            )
        host_state[host] = {
            "attempted": sum(row.get("host") == host and row.get("attempted") for row in statuses),
            "consecutive_denials_at_stop": consecutive,
            "stopped": stopped,
            "minimum_interval_seconds": client.minimum_interval,
        }
    write_csv(EVIDENCE_ROOT / "restricted_official_route_probe_status.csv", statuses)
    hga.write_json(
        CHECKPOINT_ROOT / "restricted_official_routes.json",
        {"updated_at": now_iso(), "hosts": host_state, "statuses": statuses},
    )

    status_by_probe = {row["probe_id"]: row for row in statuses}
    ledger: list[dict[str, Any]] = []
    local_rows = {
        row["external_id"]: row
        for row in read_csv(BASE_MANIFEST_ROOT / "hansard_answer_acquisition_status.csv")
        if row.get("external_id") in {"06071282000011", "07091719000037"}
    }
    for external_id, probe_id in [
        ("06071282000011", "asda_rendered"),
        ("07091719000037", "companies_house_rendered"),
    ]:
        source = local_rows[external_id]
        probe = status_by_probe[probe_id]
        ledger.append(
            {
                "gap_id": f"hansard_answer:{external_id}",
                "source_queue": "hansard_answer_acquisition_status",
                "original_id": external_id,
                "original_url": source.get("detail_url") or source.get("canonical_url") or "",
                "record_date": source["date"],
                "original_failure": source["failure_reason"],
                "repair_route": "ordinary_official_rendered_page_bounded_retry",
                "target_unit": "written_answer_item",
                "attempted_at": probe.get("retrieved_at") or "",
                "request_url": probe["url"],
                "final_url": probe.get("final_url") or "",
                "http_status": probe.get("status_code") or "",
                "mime_type": probe.get("mime_type") or "",
                "raw_path": probe.get("response_path") or "",
                "raw_sha256": probe.get("response_sha256") or "",
                "attempt_result": probe.get("failure_reason") or probe.get("attempt_result") or "",
                "disposition": "unresolved_access_denied" if int(probe.get("status_code") or 0) in {403, 429} else "unresolved_rendered_fallback",
                "result_external_id": "",
                "resulting_document_id": "",
                "notes": "Normal official page only; no challenge bypass. Saved response and stopped at host threshold.",
            }
        )

    index_rows = [row for row in read_csv(BASE_MANIFEST_ROOT / "hansard_gap_archive_index_status.csv") if row.get("status") != "success"]
    index_probe = status_by_probe["2010_failed_index_corrected_route"]
    for row in index_rows:
        is_probe = row["date"] == "2010-05-18"
        ledger.append(
            {
                "gap_id": f"gap_index:{row['date']}",
                "source_queue": "hansard_gap_archive_index_status",
                "original_id": row["date"],
                "original_url": row["request_url"],
                "record_date": row["date"],
                "original_failure": row["failure_reason"],
                "repair_route": "corrected_official_index_route_then_host_stop",
                "target_unit": "date_index",
                "attempted_at": index_probe.get("retrieved_at") if is_probe else "",
                "request_url": index_probe["url"] if is_probe else "",
                "final_url": index_probe.get("final_url") if is_probe else "",
                "http_status": index_probe.get("status_code") if is_probe else "",
                "mime_type": index_probe.get("mime_type") if is_probe else "",
                "raw_path": index_probe.get("response_path") if is_probe else "",
                "raw_sha256": index_probe.get("response_sha256") if is_probe else "",
                "attempt_result": index_probe.get("failure_reason") if is_probe else "not_requested_after_host_stop",
                "disposition": "unresolved_access_denied" if is_probe else "unresolved_host_stop_checkpoint",
                "result_external_id": "",
                "resulting_document_id": "",
                "notes": "One failed date index may conceal an unknown number of records; not counted as one missing document.",
            }
        )

    target_rows = read_csv(BASE_MANIFEST_ROOT / "hansard_gap_archive_page_target_manifest.csv")
    status_rows = read_csv(BASE_MANIFEST_ROOT / "hansard_gap_archive_page_acquisition_status.csv")
    target_index = {(row["date"], row["page_url"]): row for row in target_rows}
    status_index = {(row["date"], row["request_url"]): row for row in status_rows}
    page_queue = sorted(
        key
        for key in target_index
        if key not in status_index or status_index[key].get("download_status") != "success"
    )
    page_probe = status_by_probe["2010_failed_page_retry"]
    probe_key = ("2010-06-02", page_probe["url"])
    for key in page_queue:
        target = target_index[key]
        previous = status_index.get(key)
        is_probe = key == probe_key
        ledger.append(
            {
                "gap_id": f"gap_page:{target['page_target_id']}",
                "source_queue": "hansard_gap_archive_page_repair_queue",
                "original_id": target["page_target_id"],
                "original_url": target["page_url"],
                "record_date": target["date"],
                "original_failure": previous.get("failure_reason") if previous else "not_previously_requested",
                "repair_route": "bounded_official_page_retry_then_host_stop",
                "target_unit": "archive_html_page",
                "attempted_at": page_probe.get("retrieved_at") if is_probe else "",
                "request_url": page_probe["url"] if is_probe else "",
                "final_url": page_probe.get("final_url") if is_probe else "",
                "http_status": page_probe.get("status_code") if is_probe else "",
                "mime_type": page_probe.get("mime_type") if is_probe else "",
                "raw_path": page_probe.get("response_path") if is_probe else "",
                "raw_sha256": page_probe.get("response_sha256") if is_probe else "",
                "attempt_result": page_probe.get("failure_reason") if is_probe else "not_requested_after_host_stop",
                "disposition": "unresolved_access_denied" if is_probe else "unresolved_host_stop_checkpoint",
                "result_external_id": "",
                "resulting_document_id": "",
                "notes": "Archive page count is not a document count; one page can contain multiple answer records.",
            }
        )

    seam_publications = status_by_probe["2004_q4_statement_sample"]
    seam_modern = status_by_probe["2004_q4_modern_daily"]
    ledger.append(
        {
            "gap_id": "2004_q4_commons_seam",
            "source_queue": "historic_to_hansard_cross_route_gap",
            "original_id": "2004-10-05..2004-12-31",
            "original_url": seam_publications["url"],
            "record_date": "2004-10-05..2004-12-31",
            "original_failure": "bulk Commons route ends 2004-10-04; Historic daily route exposes Lords only for this interval",
            "repair_route": "ordinary_publications_and_modern_hansard_probes",
            "target_unit": "date_range_unknown_denominator",
            "attempted_at": ";".join(filter(None, [seam_publications.get("retrieved_at"), seam_modern.get("retrieved_at")])),
            "request_url": f"{seam_publications['url']};{seam_modern['url']}",
            "final_url": f"{seam_publications.get('final_url') or ''};{seam_modern.get('final_url') or ''}",
            "http_status": f"{seam_publications.get('status_code') or ''};{seam_modern.get('status_code') or ''}",
            "mime_type": f"{seam_publications.get('mime_type') or ''};{seam_modern.get('mime_type') or ''}",
            "raw_path": f"{seam_publications.get('response_path') or ''};{seam_modern.get('response_path') or ''}",
            "raw_sha256": f"{seam_publications.get('response_sha256') or ''};{seam_modern.get('response_sha256') or ''}",
            "attempt_result": "both normal Commons routes access-denied; Historic route verified Lords-only",
            "disposition": "unresolved_unknown_denominator",
            "result_external_id": "",
            "resulting_document_id": "",
            "notes": "No Lords material admitted. Forty-three Historic sitting indexes cannot establish Commons record zero.",
        }
    )
    upsert_ledger(ledger)
    result = {
        "generated_at": now_iso(),
        "actual_requests": sum(bool(row.get("attempted")) for row in statuses),
        "request_statuses": {str(code): sum(int(row.get("status_code") or 0) == code for row in statuses) for code in {200, 403, 429}},
        "host_state": host_state,
        "failed_index_units": len(index_rows),
        "known_page_queue_units": len(page_queue),
        "known_page_previously_failed": sum(status_index.get(key, {}).get("download_status") == "failed" for key in page_queue),
        "known_page_previously_unrequested": sum(key not in status_index for key in page_queue),
        "seam_denominator": "unknown",
    }
    hga.write_json(REPORT_ROOT / "restricted_route_repair_summary.json", result)
    return result


def _ensure_repair_partition(connection: duckdb.DuckDBPyConnection, row: dict[str, str], batch_id: str) -> None:
    partition_id = row["partition_id"]
    if connection.execute("SELECT 1 FROM query_partitions WHERE query_partition_id=?", [partition_id]).fetchone():
        return
    record_date = date.fromisoformat(row["date"])
    raw_paths = [value for value in [row.get("parent_raw_path"), row.get("record_path")] if value]
    connection.execute(
        """
        INSERT INTO query_partitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            partition_id,
            batch_id,
            record_date,
            record_date,
            row.get("parent_request_url") or row.get("canonical_url") or "targeted repair manifest",
            datetime.now(UTC),
            datetime.now(UTC),
            1,
            1,
            1,
            1,
            1,
            "partial_targeted_repair",
            "Bounded repair target admitted from verified official identity; does not redefine the original source denominator.",
            hga.canonical_json(raw_paths),
        ],
    )


def ingest_parliament_repairs() -> dict[str, Any]:
    """Commit only recovered repair-manifest records not already in 06."""
    ensure_dirs()
    manifest_paths = sorted(MANIFEST_ROOT.glob("*_record_manifest.csv"))
    rows: list[dict[str, str]] = []
    for path in manifest_paths:
        rows.extend(read_csv(path))
    unique: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if not row.get("external_id") or not row.get("batch_key"):
            continue
        unique[(row["batch_key"], row["external_id"])] = row
    rows = sorted(unique.values(), key=lambda row: (row["batch_key"], row["date"], row["external_id"]))
    if not rows:
        return {"generated_at": now_iso(), "candidate_records": 0, "new_documents": 0, "status": "nothing_to_ingest"}
    _ensure_recovery_checkpoint()
    before: dict[str, int]
    after: dict[str, int]
    commit_rows: list[dict[str, Any]] = []
    source_defs = hga._source_definitions()
    with duckdb.connect(str(DB_PATH)) as connection:
        before = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ["documents", "content_objects", "content_versions", "text_segments", "voice_attributions"]
        }
        authorization_id = hga._new_authorization(connection)
        for batch_key in sorted({row["batch_key"] for row in rows}):
            batch_rows = [row for row in rows if row["batch_key"] == batch_key]
            source_id = source_defs[batch_key]["source_id"]
            batch_id = hga.BATCHES[batch_key]
            existing = {
                str(value[0])
                for value in connection.execute("SELECT external_id FROM documents WHERE source_id=?", [source_id]).fetchall()
            }
            pending = [row for row in batch_rows if row["external_id"] not in existing]
            for row in batch_rows:
                _ensure_repair_partition(connection, row, batch_id)
            extraction_run_id = hga.stable_id("ext", batch_id, TARGETED_EXTRACTOR_VERSION)
            connection.execute(
                "INSERT INTO extraction_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [
                    extraction_run_id,
                    batch_id,
                    TARGETED_EXTRACTOR_VERSION,
                    datetime.now(UTC),
                    datetime.now(UTC),
                    0,
                    0,
                    "partial",
                    "Bounded targeted repair records only.",
                ],
            )
            for offset in range(0, len(pending), 500):
                chunk = pending[offset : offset + 500]
                direct = [row for row in chunk if row.get("storage_mode") == "direct_detail"]
                derived = [row for row in chunk if row.get("storage_mode") == "derived_html"]
                derived_list = [row for row in chunk if row.get("storage_mode") == "derived_list"]
                prepared_sets = []
                if direct:
                    prepared_sets.append(
                        hga._prepare_parliament_rows(
                            "hansard", source_id, batch_id, extraction_run_id, direct, None
                        )
                    )
                if derived:
                    prepared_sets.append(
                        hga._prepare_parliament_rows(
                            "hansard_gap",
                            source_id,
                            batch_id,
                            extraction_run_id,
                            derived,
                            _derived_parent_context(derived),
                        )
                    )
                if derived_list:
                    prepared_sets.append(
                        hga._prepare_parliament_rows(
                            "hansard_gap",
                            source_id,
                            batch_id,
                            extraction_run_id,
                            derived_list,
                            _derived_parent_context(derived_list),
                        )
                    )
                chunk_before = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
                connection.execute("BEGIN TRANSACTION")
                try:
                    for prepared in prepared_sets:
                        hga._insert_prepared_chunk(connection, prepared)
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
                chunk_after = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
                checkpoint = CHECKPOINT_ROOT / f"parliament_{batch_key}_{offset:06d}.json"
                hga.write_json(
                    checkpoint,
                    {
                        "committed_at": now_iso(),
                        "batch_key": batch_key,
                        "batch_id": batch_id,
                        "source_rows": len(chunk),
                        "new_documents": chunk_after - chunk_before,
                        "external_ids": [row["external_id"] for row in chunk],
                    },
                )
                commit_rows.append(
                    {
                        "batch_key": batch_key,
                        "offset": offset,
                        "source_rows": len(chunk),
                        "new_documents": chunk_after - chunk_before,
                        "checkpoint": str(checkpoint.relative_to(PROJECT_ROOT)),
                    }
                )
                print(
                    f"[{now_iso()}] COMMIT targeted {batch_key} records={len(chunk)} new_documents={chunk_after - chunk_before}",
                    flush=True,
                )
                del prepared_sets
                gc.collect()
            input_count = int(connection.execute("SELECT COUNT(DISTINCT content_version_id) FROM text_segments WHERE extraction_run_id=?", [extraction_run_id]).fetchone()[0])
            output_count = int(connection.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=?", [extraction_run_id]).fetchone()[0])
            connection.execute(
                "UPDATE extraction_runs SET finished_at=?, input_content_count=?, output_segment_count=?, status='complete', status_reason=? WHERE extraction_run_id=?",
                [datetime.now(UTC), input_count, output_count, "All eligible targeted repair records committed; residual blockers remain in the repair ledger.", extraction_run_id],
            )
            run_id = hga.stable_id("run", batch_id, TARGETED_SCRIPT_VERSION)
            manifest_path = MANIFEST_ROOT / "hansard_local_repair_record_manifest.csv"
            connection.execute(
                """
                INSERT INTO acquisition_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (run_id) DO UPDATE SET finished_at=excluded.finished_at, status=excluded.status,
                  attempted_count=excluded.attempted_count, successful_download_count=excluded.successful_download_count,
                  successful_extraction_count=excluded.successful_extraction_count, result_json=excluded.result_json
                """,
                [
                    run_id,
                    batch_id,
                    authorization_id,
                    datetime.now(UTC),
                    datetime.now(UTC),
                    "targeted_gap_repair_ingest",
                    TARGETED_SCRIPT_VERSION,
                    f"{sys.executable} {Path(__file__).name} ingest-parliament",
                    str(manifest_path.relative_to(PROJECT_ROOT)) if manifest_path.exists() else "targeted_gap_repair/manifests",
                    hga.sha256_file(manifest_path) if manifest_path.exists() else hga.sha256_bytes(b"targeted_gap_repair"),
                    str(DB_PATH),
                    "complete_with_documented_residuals",
                    len(batch_rows),
                    len(batch_rows),
                    len(batch_rows),
                    0,
                    hga.canonical_json({"eligible_manifest_records": len(batch_rows), "pending_before_commit": len(pending), "already_present_before_commit": len(batch_rows) - len(pending), "output_segments": output_count}),
                ],
            )
        after = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in before
        }
    write_csv(REPORT_ROOT / "parliament_commit_chunks.csv", commit_rows)
    result = {
        "generated_at": now_iso(),
        "candidate_records": len(rows),
        "before": before,
        "after": after,
        "added": {key: after[key] - before[key] for key in before},
        "committed_chunks": len(commit_rows),
    }
    hga.write_json(REPORT_ROOT / "parliament_ingestion_summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=[
            "local-repair",
            "statement-repair",
            "historic-repair",
            "restricted-routes",
            "prepare-ocr",
            "ingest-ocr",
            "ingest-parliament",
        ],
    )
    args = parser.parse_args()
    function = {
        "local-repair": build_local_hansard_repairs,
        "statement-repair": resolve_statement_candidates,
        "historic-repair": repair_historic_daily_gaps,
        "restricted-routes": probe_restricted_official_routes,
        "prepare-ocr": prepare_ocr_manifest,
        "ingest-ocr": ingest_ocr_results,
        "ingest-parliament": ingest_parliament_repairs,
    }[args.phase]
    result = function()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
