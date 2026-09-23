#!/usr/bin/env python3
"""Build coverage tables, restrained academic figures, Markdown and HTML reports."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import textwrap
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
REPORTS = HERE / "reports"
MANIFESTS = HERE / "manifests"
DB = PROJECT_ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
CUTOFF = date(2026, 9, 21)
YEARS = list(range(1988, 2027))
SERIES = ["policy_document", "ministerial_written_answer", "ministerial_written_statement"]
LABELS = {
    "policy_document": "Policy-source publication records",
    "ministerial_written_answer": "Ministerial written answers",
    "ministerial_written_statement": "Ministerial written statements",
}
COLORS = {
    "policy_document": "#24495F",
    "ministerial_written_answer": "#C57A43",
    "ministerial_written_statement": "#6F7D4C",
}
BASELINE_DOCUMENTS = 1020
BASELINE_PRE2010 = 55
FROZEN_HASHES = {
    "04_database": (
        PROJECT_ROOT / "work_packages/M1_source_access/04_government_corpus_batch/fear_temperature_government_batch.duckdb",
        "16690bc540f8194cc2bf8ec1cba3794fb9745d0986e0dae2643306d6cb48c396",
    ),
    "04_manifest": (
        PROJECT_ROOT / "work_packages/M1_source_access/04_government_corpus_batch/enumeration_manifest.csv",
        "1340e85a841ebb1ab261d7160abdc8474a302d39bfca97cb488be4388150e786",
    ),
    "05_database": (
        PROJECT_ROOT / "work_packages/M1_source_access/05_core_content_storage/fear_temperature_core_storage.duckdb",
        "5aa96f0f52fb499253853e62adecf0b307eee5f39b9d31e74141bae07fd0bf91",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(rows[0]) if rows else []
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def series_sql() -> str:
    return """
        CASE
          WHEN d.content_type='ministerial_written_answer' THEN 'ministerial_written_answer'
          WHEN d.content_type='ministerial_written_statement' THEN 'ministerial_written_statement'
          WHEN s.source_name LIKE 'GOV.UK%' THEN 'policy_document'
          ELSE 'other'
        END
    """


def collect_distributions(connection: duckdb.DuckDBPyConnection) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    annual_values = {
        (int(year), str(series)): int(count)
        for year, series, count in connection.execute(
            f"""
            SELECT year(d.publication_date) AS year, {series_sql()} AS series, COUNT(*)
            FROM documents d JOIN sources s USING(source_id)
            WHERE d.publication_date BETWEEN DATE '1988-01-01' AND DATE '2026-09-21'
            GROUP BY 1,2
            """
        ).fetchall()
        if str(series) in SERIES
    }
    annual = []
    for year in YEARS:
        row: dict[str, Any] = {
            "year": year,
            "coverage_note": "partial study start" if year == 1988 else "partial through 2026-09-21" if year == 2026 else "full calendar-year window",
        }
        for series in SERIES:
            row[series] = annual_values.get((year, series), 0)
        row["all_three_series"] = sum(row[series] for series in SERIES)
        annual.append(row)
    quarter_values = {
        (int(year), int(quarter), str(series)): int(count)
        for year, quarter, series, count in connection.execute(
            f"""
            SELECT year(d.publication_date), quarter(d.publication_date), {series_sql()} AS series, COUNT(*)
            FROM documents d JOIN sources s USING(source_id)
            WHERE d.publication_date BETWEEN DATE '1988-01-01' AND DATE '2026-09-21'
            GROUP BY 1,2,3
            """
        ).fetchall()
        if str(series) in SERIES
    }
    quarterly = []
    for year in YEARS:
        for quarter in range(1, 5):
            if year == 1988:
                quarter_note = "partial study-start year"
            elif year == 2026 and quarter == 3:
                quarter_note = "partial quarter through 2026-09-21"
            elif year == 2026 and quarter == 4:
                quarter_note = "outside acquisition cutoff; zero by design"
            elif year == 2026:
                quarter_note = "full quarter within the partial 2026 study year"
            else:
                quarter_note = "full quarter window"
            row = {
                "year": year,
                "quarter": f"Q{quarter}",
                "coverage_note": quarter_note,
            }
            for series in SERIES:
                row[series] = quarter_values.get((year, quarter, series), 0)
            row["all_three_series"] = sum(row[series] for series in SERIES)
            quarterly.append(row)
    return annual, quarterly


def source_year_progress_rows(connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Reconcile frozen record targets with object-level acquisition by year.

    Record targets and content objects are separate denominators.  A policy
    webpage can have multiple attachments and an attachment can be associated
    with more than one publication, so policy object counts are year-association
    counts and must not be summed as unique cross-year objects.
    """
    target_specs = [
        ("GOV.UK historical policy", MANIFESTS / "policy_manifest.csv", "policy_document"),
        ("Historic Hansard bulk XML", MANIFESTS / "historic_record_manifest.csv", None),
        ("Hansard API 2005–2010", MANIFESTS / "hansard_statement_manifest.csv", None),
        ("Hansard API 2005–2010", MANIFESTS / "hansard_answer_target_manifest.csv", None),
        ("Commons archive/API 2010–2014 gap backfill", MANIFESTS / "hansard_gap_archive_answer_manifest.csv", None),
        ("Commons archive/API 2010–2014 gap backfill", MANIFESTS / "hansard_gap_statement_manifest.csv", None),
        ("Questions/Statements API 2014–2026", MANIFESTS / "modern_record_manifest.csv", None),
    ]
    values: dict[tuple[str, str, int], dict[str, Any]] = {}

    def ensure(source: str, series: str, year: int) -> dict[str, Any]:
        key = (source, series, year)
        return values.setdefault(
            key,
            {
                "source_tranche": source,
                "series": series,
                "year": year,
                "enumerated_records": 0,
                "already_in_06_records": 0,
                "net_new_record_targets": 0,
                "ingested_records": 0,
                "attempted_content_objects": 0,
                "downloaded_content_objects": 0,
                "extracted_content_objects": 0,
                "confirmed_target_exceptions": 0,
                "count_basis": "records and content objects are separate denominators",
            },
        )

    for source, path, fixed_series in target_specs:
        for row in read_csv(path):
            if not row.get("year"):
                continue
            year = int(row["year"])
            series = fixed_series or row.get("genre") or "unknown"
            value = ensure(source, series, year)
            value["enumerated_records"] += 1
            existing = str(row.get("existing_document", "")).lower() == "true"
            value["already_in_06_records"] += int(existing)
            value["net_new_record_targets"] += int(not existing)

    batch_labels = {
        "govuk_historical_policy_1988_2009_20260921_v1": "GOV.UK historical policy",
        "commons_historic_hansard_1988_2004_20260921_v1": "Historic Hansard bulk XML",
        "commons_hansard_api_2005_20100430_20260921_v1": "Hansard API 2005–2010",
        "commons_hansard_api_20100501_20140911_20260921_v1": "Commons archive/API 2010–2014 gap backfill",
        "commons_questions_statements_20140912_20260921_v1": "Questions/Statements API 2014–2026",
    }
    for batch_id, year, content_type, documents, objects, downloaded, extracted in connection.execute(
        """
        SELECT e.batch_id, year(d.publication_date), d.content_type,
               COUNT(DISTINCT e.document_id),
               COUNT(DISTINCT dc.content_object_id),
               COUNT(DISTINCT CASE WHEN a.download_status='success' THEN dc.content_object_id END),
               COUNT(DISTINCT CASE WHEN a.extraction_status='success' THEN dc.content_object_id END)
        FROM enumeration_records e
        JOIN documents d USING(document_id)
        LEFT JOIN document_content_objects dc USING(document_id)
        LEFT JOIN acquisition_object_statuses a
          ON a.batch_id=e.batch_id AND a.content_object_id=dc.content_object_id
        WHERE e.batch_id IN (
          'govuk_historical_policy_1988_2009_20260921_v1',
          'commons_historic_hansard_1988_2004_20260921_v1',
          'commons_hansard_api_2005_20100430_20260921_v1',
          'commons_hansard_api_20100501_20140911_20260921_v1',
          'commons_questions_statements_20140912_20260921_v1')
        GROUP BY 1,2,3
        """
    ).fetchall():
        source = batch_labels[str(batch_id)]
        series = "policy_document" if str(content_type) == "policy_paper" else str(content_type)
        value = ensure(source, series, int(year))
        value["ingested_records"] = int(documents)
        value["attempted_content_objects"] = int(objects)
        value["downloaded_content_objects"] = int(downloaded)
        value["extracted_content_objects"] = int(extracted)
        if source == "GOV.UK historical policy":
            value["count_basis"] = "record targets; policy object counts are within-year associations and may repeat across years"
        elif source == "Historic Hansard bulk XML":
            value["count_basis"] = "derived records linked to downloaded archive-volume content objects; a volume may be associated with records in more than one year"
        elif source == "Commons archive/API 2010–2014 gap backfill":
            value["count_basis"] = "archive-derived answer records may share an official daily HTML page; API statement details are one object per record"
        elif source == "Questions/Statements API 2014–2026":
            value["count_basis"] = "records are derived by official ID from complete-text API list responses; many records share one downloaded JSON parent page"
        else:
            value["count_basis"] = "one official detail content object per record target"

    for row in read_csv(MANIFESTS / "hansard_answer_acquisition_status.csv"):
        if row.get("download_status") != "success":
            ensure("Hansard API 2005–2010", "ministerial_written_answer", int(row["year"]))["confirmed_target_exceptions"] += 1
    for row in read_csv(MANIFESTS / "hansard_gap_answer_acquisition_status.csv"):
        if row.get("download_status") != "success":
            ensure("Commons archive/API 2010–2014 gap backfill", "ministerial_written_answer", int(row["year"]))["confirmed_target_exceptions"] += 1
    for row in read_csv(MANIFESTS / "hansard_gap_statement_acquisition_status.csv"):
        if row.get("download_status") != "success":
            ensure("Commons archive/API 2010–2014 gap backfill", "ministerial_written_statement", int(row["year"]))["confirmed_target_exceptions"] += 1
    for row in read_csv(MANIFESTS / "hansard_gap_archive_page_acquisition_status.csv"):
        if row.get("download_status") != "success":
            ensure("Commons archive/API 2010–2014 gap backfill", "ministerial_written_answer", int(row["date"][:4]))["confirmed_target_exceptions"] += 1
    for row in read_csv(MANIFESTS / "modern_acquisition_status.csv"):
        if row.get("download_status") != "success":
            ensure("Questions/Statements API 2014–2026", row["genre"], int(row["year"]))["confirmed_target_exceptions"] += 1
    return sorted(values.values(), key=lambda row: (row["source_tranche"], int(row["year"]), row["series"]))


def progress_rows(connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    policy_enum = read_json(MANIFESTS / "policy_enumeration_summary.json", {})
    policy_acq = read_json(MANIFESTS / "policy_acquisition_summary.json", {})
    volume = read_json(MANIFESTS / "historic_volume_acquisition_summary.json", {})
    historic = read_json(MANIFESTS / "historic_record_enumeration_summary.json", {})
    hansard_candidates = read_json(MANIFESTS / "hansard_candidate_summary.json", {})
    hansard_statements = read_json(
        MANIFESTS / "hansard_statement_summary.json",
        read_json(MANIFESTS / "hansard_record_summary.json", {}),
    )
    hansard_answers = read_json(MANIFESTS / "hansard_answer_summary.json", {})
    gap_answers = read_json(MANIFESTS / "hansard_gap_answer_summary.json", read_json(MANIFESTS / "hansard_gap_answer_enumeration_summary.json", {}))
    gap_statement_candidates = read_json(MANIFESTS / "hansard_gap_statement_candidate_summary.json", {})
    gap_statements = read_json(MANIFESTS / "hansard_gap_statement_summary.json", {})
    gap_archive = read_json(MANIFESTS / "hansard_gap_archive_answer_summary.json", {})
    historic_revision = read_json(REPORTS / "historic_manifest_revision.json", {})
    historic_repair = read_json(REPORTS / "historic_parser_artifact_repair.json", {})
    modern_enum = read_json(MANIFESTS / "modern_record_enumeration_summary.json", {})
    modern_acq = read_json(MANIFESTS / "modern_acquisition_summary.json", {})
    batches = {
        str(batch): {"documents": int(documents), "objects": int(objects), "downloaded": int(downloaded), "extracted": int(extracted)}
        for batch, documents, objects, downloaded, extracted in connection.execute(
            """
            SELECT b.batch_id,
                   COUNT(DISTINCT r.document_id),
                   COUNT(DISTINCT a.content_object_id),
                   COUNT(DISTINCT CASE WHEN a.download_status='success' THEN a.content_object_id END),
                   COUNT(DISTINCT CASE WHEN a.extraction_status='success' THEN a.content_object_id END)
            FROM collection_batches b
            LEFT JOIN enumeration_records r USING(batch_id)
            LEFT JOIN acquisition_object_statuses a USING(batch_id)
            WHERE b.batch_id IN (
              'govuk_historical_policy_1988_2009_20260921_v1',
              'commons_historic_hansard_1988_2004_20260921_v1',
              'commons_hansard_api_2005_20100430_20260921_v1',
              'commons_hansard_api_20100501_20140911_20260921_v1',
              'commons_questions_statements_20140912_20260921_v1')
            GROUP BY b.batch_id
            """
        ).fetchall()
    }

    def batch_value(batch: str, key: str) -> int:
        return batches.get(batch, {}).get(key, 0)

    policy_extraction_deferred = max(
        0,
        int(policy_acq.get("downloaded", 0))
        - batch_value("govuk_historical_policy_1988_2009_20260921_v1", "extracted"),
    )
    rows = [
        {
            "source_tranche": "GOV.UK historical policy",
            "series": "policy_document",
            "enumerated_targets": policy_enum.get("unique_records", 0),
            "already_in_06": policy_enum.get("existing_records", 0),
            "net_new_expected": policy_enum.get("net_new_records", 0),
            "content_objects_expected": policy_acq.get("target_objects", 0),
            "attempted_objects": policy_acq.get("attempted", 0),
            "downloaded_objects": policy_acq.get("downloaded", 0),
            "extracted_objects": batch_value("govuk_historical_policy_1988_2009_20260921_v1", "extracted"),
            "failed_or_deferred_objects": int(policy_acq.get("failed", 0)) + policy_extraction_deferred,
            "ingested_records": batch_value("govuk_historical_policy_1988_2009_20260921_v1", "documents"),
            "completeness_note": f"Complete as visible within four verified GOV.UK organisation tags. All 84 content objects downloaded; {policy_extraction_deferred} scanned PDFs remain needs_ocr. UKGWA official site routes were identified, but policy-index enumeration was blocked by the shared human-verification gate; UK DoE/DETR/MAFF routes remain unresolved.",
        },
        {
            "source_tranche": "Historic Hansard bulk XML",
            "series": "answers + statements",
            "enumerated_targets": historic.get("enumerated_targets", 0),
            "already_in_06": 0,
            "net_new_expected": historic.get("enumerated_targets", 0),
            "content_objects_expected": volume.get("target_objects", volume.get("enumerated_targets", 320)),
            "attempted_objects": volume.get("attempted", 0),
            "downloaded_objects": volume.get("downloaded", 0),
            "extracted_objects": batch_value("commons_historic_hansard_1988_2004_20260921_v1", "extracted"),
            "failed_or_deferred_objects": volume.get("failed", 0),
            "ingested_records": batch_value("commons_historic_hansard_1988_2004_20260921_v1", "documents"),
            "completeness_note": f"319/320 bulk XML targets valid; volume 200 unavailable as valid ZIP; {historic.get('duplicates_removed', 0)} duplicate source contributions removed.",
        },
        {
            "source_tranche": "Hansard API 2005–2010",
            "series": "answers + statements",
            "enumerated_targets": hansard_answers.get("eligible_answer_sections", 0) + hansard_statements.get("eligible_records", 0),
            "already_in_06": hansard_answers.get("existing_records", 0) + hansard_statements.get("existing_records", 0),
            "net_new_expected": hansard_answers.get("net_new_records", 0) + hansard_statements.get("net_new_records", 0),
            "content_objects_expected": hansard_answers.get("eligible_answer_sections", 0) + hansard_statements.get("eligible_records", 0),
            "attempted_objects": hansard_candidates.get("unique_candidate_debates", 0) + hansard_answers.get("attempted", 0),
            "downloaded_objects": hansard_statements.get("candidate_downloaded", 0) + hansard_answers.get("downloaded", 0),
            "extracted_objects": batch_value("commons_hansard_api_2005_20100430_20260921_v1", "extracted"),
            "failed_or_deferred_objects": hansard_statements.get("candidate_failed", 0) + hansard_answers.get("failed", 0) + hansard_answers.get("tree_failed", 0),
            "ingested_records": batch_value("commons_hansard_api_2005_20100430_20260921_v1", "documents"),
            "completeness_note": "Statements verified from detail navigation; answers enumerated from daily official department trees and full detail retains paired question/context.",
        },
        {
            "source_tranche": "Commons archive/API 2010–2014 gap backfill",
            "series": "answers + statements",
            "enumerated_targets": gap_answers.get("eligible_answer_sections", 0) + gap_statements.get("eligible_statements", 0),
            "already_in_06": gap_answers.get("existing_records", 0) + gap_statements.get("existing_records", 0),
            "net_new_expected": gap_answers.get("net_new_records", 0) + gap_statements.get("net_new_records", 0),
            "content_objects_expected": gap_archive.get("unique_target_text_pages", 0) + gap_statement_candidates.get("unique_candidate_debates", 0),
            "attempted_objects": gap_archive.get("attempted_text_pages", 0) + gap_statements.get("candidate_targets", 0),
            "downloaded_objects": gap_archive.get("downloaded_text_pages", 0) + gap_statements.get("candidate_downloaded", 0),
            "extracted_objects": batch_value("commons_hansard_api_20100501_20140911_20260921_v1", "extracted"),
            "failed_or_deferred_objects": gap_archive.get("failed_indexes", 0) + gap_archive.get("failed_text_pages", 0) + gap_statements.get("candidate_failed", 0),
            "ingested_records": batch_value("commons_hansard_api_20100501_20140911_20260921_v1", "documents"),
            "completeness_note": f"Current Hansard daily-answer trees are empty after April 2010. Archive coverage is partial: {gap_archive.get('successful_indexes', 0)}/{gap_archive.get('sitting_day_index_targets', 0)} indexes and {gap_archive.get('downloaded_text_pages', 0)}/{gap_archive.get('unique_target_text_pages', 0)} frozen text pages succeeded; {gap_archive.get('unprocessed_text_pages', 0)} text pages remained unrequested after the dynamic throttle stop. Record targets are frozen only for parsed pages, so the missing-page record denominator is unknown.",
        },
        {
            "source_tranche": "Questions/Statements API 2014–2026",
            "series": "answers + statements",
            "enumerated_targets": modern_enum.get("enumerated_targets", 0),
            "already_in_06": modern_enum.get("existing_records", 0),
            "net_new_expected": modern_enum.get("net_new_records", 0),
            "content_objects_expected": modern_acq.get("parent_list_page_targets", 0),
            "attempted_objects": modern_acq.get("parent_http_requests_reused", 0),
            "downloaded_objects": modern_acq.get("parent_list_pages_downloaded", 0),
            "extracted_objects": batch_value("commons_questions_statements_20140912_20260921_v1", "extracted"),
            "failed_or_deferred_objects": modern_acq.get("failed_records", 0),
            "ingested_records": batch_value("commons_questions_statements_20140912_20260921_v1", "documents"),
            "completeness_note": "Body/year/genre API partitions; complete text is present in 174 verified list responses and per-record JSON is explicitly derived by official ID, not represented as 65,988 fictitious HTTP responses. 2026 is partial through cutoff.",
        },
    ]
    acquired_records = {
        "GOV.UK historical policy": int(policy_enum.get("net_new_records", 0)) if policy_acq.get("failed", 0) == 0 else max(0, int(policy_enum.get("net_new_records", 0)) - int(policy_acq.get("failed", 0))),
        "Historic Hansard bulk XML": int(historic.get("enumerated_targets", 0)),
        "Hansard API 2005–2010": len(read_csv(MANIFESTS / "hansard_record_manifest.csv")),
        "Commons archive/API 2010–2014 gap backfill": len(read_csv(MANIFESTS / "hansard_gap_record_manifest.csv")),
        "Questions/Statements API 2014–2026": int(modern_acq.get("derived_records_parsed", 0)),
    }
    frozen_records = {
        "GOV.UK historical policy": int(policy_enum.get("net_new_records", 0)),
        "Historic Hansard bulk XML": int(historic.get("enumerated_targets", 0)),
        "Hansard API 2005–2010": int(hansard_answers.get("net_new_records", 0)) + int(hansard_statements.get("net_new_records", 0)),
        "Commons archive/API 2010–2014 gap backfill": int(gap_answers.get("net_new_records", 0)) + int(gap_statements.get("net_new_records", 0)),
        "Questions/Statements API 2014–2026": int(modern_enum.get("net_new_records", 0)),
    }
    for row in rows:
        source = row["source_tranche"]
        row["frozen_target_records"] = frozen_records[source]
        row["original_text_acquired_records"] = acquired_records[source]
        row["parsed_records"] = acquired_records[source]
        row["formally_committed_records"] = int(row["ingested_records"])
        row["failed_or_retry_objects"] = int(row["failed_or_deferred_objects"])
        row["failed_target_records"] = (
            int(hansard_answers.get("failed", 0))
            if source == "Hansard API 2005–2010"
            else 0
        )
        row["not_yet_processed_records"] = max(
            0,
            frozen_records[source]
            - acquired_records[source]
            - row["failed_target_records"],
        )
        row["unprocessed_content_objects"] = int(gap_archive.get("unprocessed_text_pages", 0)) if source == "Commons archive/API 2010–2014 gap backfill" else 0
    return rows


def department_register() -> list[dict[str, Any]]:
    return [
        {"period": "1988–1992", "official_label_or_body": "ENERGY", "series": "Commons answers", "mapping_status": "verified official XML group", "scope_note": "Energy department."},
        {"period": "1988–1997", "official_label_or_body": "ENVIRONMENT", "series": "Commons answers", "mapping_status": "verified official XML group", "scope_note": "UK department group; not Northern Ireland DoE."},
        {"period": "1988–2001", "official_label_or_body": "AGRICULTURE, FISHERIES AND FOOD", "series": "Commons answers", "mapping_status": "verified official XML group", "scope_note": "MAFF predecessor remit."},
        {"period": "1988–2007", "official_label_or_body": "TRADE AND INDUSTRY", "series": "policy + Commons", "mapping_status": "verified GOV.UK ID / official Hansard label", "scope_note": "Broad DTI material; not all records are climate-specific."},
        {"period": "1997–2001", "official_label_or_body": "ENVIRONMENT, TRANSPORT AND THE REGIONS", "series": "Commons answers", "mapping_status": "verified official XML group", "scope_note": "Mixed environment/transport/regional remit."},
        {"period": "2001–2026", "official_label_or_body": "Department for Environment, Food and Rural Affairs", "series": "policy + Commons", "mapping_status": "verified official labels/body 13", "scope_note": "DEFRA lineage; current API starts 2014-09-12."},
        {"period": "2007–2009", "official_label_or_body": "Business, Enterprise and Regulatory Reform", "series": "policy + Commons", "mapping_status": "verified GOV.UK ID / Hansard label", "scope_note": "Broad business mixture explicitly retained."},
        {"period": "2008–2016", "official_label_or_body": "Department of Energy and Climate Change", "series": "policy + Commons", "mapping_status": "verified GOV.UK ID / body 63", "scope_note": "2005–2010 Hansard overlap and 2014–2016 API."},
        {"period": "2016–2023", "official_label_or_body": "Department for Business, Energy and Industrial Strategy", "series": "Commons", "mapping_status": "verified body 201", "scope_note": "Broad business/energy mixture; no topic filtering."},
        {"period": "2020–2022", "official_label_or_body": "COP26", "series": "Commons", "mapping_status": "verified body 210", "scope_note": "Time-limited climate body."},
        {"period": "2023–cutoff", "official_label_or_body": "Department for Energy Security and Net Zero", "series": "Commons", "mapping_status": "verified body 215", "scope_note": "2026 partial through cutoff."},
        {"period": "pre-2001 policy", "official_label_or_body": "UK DoE / MAFF GOV.UK policy index", "series": "policy", "mapping_status": "unresolved route", "scope_note": "No verified searchable UK organisation identifier; NI DoE not substituted."},
    ]


def exception_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(MANIFESTS / "policy_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "GOV.UK policy", "target": row.get("request_url"), "stage": "download", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "historic_volume_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Historic Hansard XML", "target": row.get("zip_name"), "stage": "download/validation", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_candidate_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Hansard API", "target": row.get("detail_url"), "stage": "detail download", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_answer_calendar_status.csv"):
        if row.get("status") != "success":
            rows.append({"source": "Hansard WrittenAnswers", "target": f"year={row.get('year')};month={row.get('month')}", "stage": "sitting-calendar enumeration", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_answer_tree_status.csv"):
        if row.get("status") != "success":
            rows.append({"source": "Hansard WrittenAnswers", "target": row.get("date"), "stage": "daily department-tree enumeration", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_answer_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Hansard WrittenAnswers", "target": row.get("detail_url"), "stage": "answer detail", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_answer_calendar_status.csv"):
        if row.get("status") != "success":
            rows.append({"source": "Hansard gap backfill", "target": f"year={row.get('year')};month={row.get('month')}", "stage": "sitting-calendar enumeration", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_answer_tree_status.csv"):
        if row.get("status") != "success":
            rows.append({"source": "Hansard gap backfill", "target": row.get("date"), "stage": "daily department-tree enumeration", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_answer_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Hansard gap backfill", "target": row.get("detail_url"), "stage": "answer detail", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_statement_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Hansard gap backfill", "target": row.get("detail_url"), "stage": "statement-candidate detail", "reason": row.get("failure_reason")})
    statement_failure_audit = {
        row.get("candidate_id"): row
        for row in read_csv(MANIFESTS / "hansard_gap_statement_failure_scope_audit.csv")
    }
    for row in read_csv(MANIFESTS / "hansard_gap_written_acquisition_status.csv"):
        if row.get("download_status") != "success":
            audit = statement_failure_audit.get(row.get("candidate_id"), {})
            resolution = audit.get("scope_resolution") or "not_yet_scope_resolved"
            rows.append({"source": "Hansard gap Written candidates", "target": row.get("detail_url"), "stage": "candidate detail and official-index scope audit", "reason": f"{row.get('failure_reason')}; {resolution}"})
    for row in read_csv(MANIFESTS / "hansard_gap_archive_index_status.csv"):
        if row.get("status") != "success":
            rows.append({"source": "Commons publications archive", "target": row.get("date"), "stage": "dated written-answer index", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_archive_page_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Commons publications archive", "target": row.get("request_url"), "stage": "written-answer HTML", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_archive_unprocessed_page_targets.csv"):
        rows.append({"source": "Commons publications archive", "target": row.get("page_url"), "stage": "written-answer HTML not requested before throttle stop", "reason": row.get("reason")})
    for row in read_csv(MANIFESTS / "hansard_gap_archive_parse_errors.csv"):
        rows.append({"source": "Commons publications archive", "target": row.get("page_url"), "stage": "derived question/answer parsing", "reason": row.get("error")})
    for row in read_csv(MANIFESTS / "modern_acquisition_status.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Questions/Statements API", "target": row.get("external_id"), "stage": "list-parent derivation", "reason": row.get("failure_reason")})
    for row in read_csv(MANIFESTS / "modern_detail_request_status_preserved.csv"):
        if row.get("download_status") != "success":
            rows.append({"source": "Questions/Statements API diagnostic", "target": row.get("detail_url"), "stage": "stopped redundant per-record detail path", "reason": f"{row.get('failure_reason')}; complete text retained in verified list parent"})
    for row in read_csv(MANIFESTS / "ukgwa_route_manifest.csv"):
        if row.get("enumeration_status") != "complete":
            rows.append(
                {
                    "source": "UK Government Web Archive",
                    "target": row.get("timeline_url") or row.get("department"),
                    "stage": "bounded policy-index route enumeration",
                    "reason": row.get("reason"),
                }
            )
    gap_summary = read_json(MANIFESTS / "hansard_gap_record_summary.json", {})
    gap_answers = read_json(MANIFESTS / "hansard_gap_answer_summary.json", {})
    gap_candidates = read_json(MANIFESTS / "hansard_gap_statement_candidate_summary.json", {})
    gap_statements = read_json(MANIFESTS / "hansard_gap_statement_summary.json", {})
    gap_archive = read_json(MANIFESTS / "hansard_gap_archive_answer_summary.json", {})
    gap_complete = bool(
        gap_summary
        and gap_archive.get("successful_indexes") == gap_archive.get("sitting_day_index_targets")
        and gap_archive.get("downloaded_text_pages") == gap_archive.get("unique_target_text_pages")
        and gap_archive.get("parse_errors") == 0
        and gap_candidates.get("complete_partitions") == gap_candidates.get("partitions")
        and gap_statements.get("candidate_downloaded") == gap_statements.get("candidate_targets")
    )
    if not gap_complete:
        rows.append({"source": "Commons ministerial series", "target": "2010-05-01..2014-09-11", "stage": "bounded official backfill", "reason": "One or more dated index, archive-page, parser, or statement-detail partitions remain unavailable or unprocessed; interval is not claimed as continuous coverage."})
    rows.append({"source": "GOV.UK historical policy", "target": "UK DoE / MAFF", "stage": "organisation route", "reason": "Verified searchable UK organisation identifier/index unavailable; Northern Ireland DoE was not substituted."})
    return rows


def configure_plotting() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.2,
            "axes.titlesize": 8.5,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.2,
            "ytick.labelsize": 6.2,
            "legend.fontsize": 6.5,
            "figure.titlesize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def save_figure(fig: plt.Figure, stem: str, data_payload: Any) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_box = fig.bbox
    outside = []
    for artist in fig.findobj(mpl.text.Text):
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        box = artist.get_window_extent(renderer=renderer)
        if box.x0 < figure_box.x0 - 1 or box.x1 > figure_box.x1 + 1 or box.y0 < figure_box.y0 - 1 or box.y1 > figure_box.y1 + 1:
            outside.append(artist.get_text())
    data_fingerprint = hashlib.sha256(json.dumps(data_payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    for extension in ("svg", "pdf", "png"):
        path = REPORTS / f"{stem}.{extension}"
        fig.savefig(path, dpi=220 if extension == "png" else None, facecolor="white")
    write_json(
        REPORTS / f"{stem}.qa.json",
        {
            "figure_contract": {
                "conclusion": "Historical expansion materially increases pre-2010 coverage while source regimes remain discontinuous.",
                "comparison": "annual or quarterly counts by independent series",
                "data_source": "existing 06 DuckDB after incremental ingestion",
                "graphic_form": "aligned small multiples / restrained bars",
                "backend": "Python matplotlib",
                "width_mm": 183,
                "minimum_font_pt": 6.2,
                "exports": ["SVG", "PDF", "PNG"],
            },
            "data_sha256": data_fingerprint,
            "text_outside_figure": outside,
            "collision_audit_passed": not outside,
            "editable_text_svg": True,
        },
    )
    plt.close(fig)


def build_figures(annual: list[dict[str, Any]], quarterly: list[dict[str, Any]], before_after: list[dict[str, Any]]) -> None:
    configure_plotting()
    x = np.array(YEARS)
    fig, axes = plt.subplots(3, 1, figsize=(7.205, 5.9), sharex=True)
    for axis, series in zip(axes, SERIES, strict=True):
        y = np.array([int(row[series]) for row in annual])
        axis.bar(x, y, width=0.82, color=COLORS[series], linewidth=0)
        axis.set_title(LABELS[series], loc="left", fontweight="bold")
        axis.set_ylabel("Records")
        axis.axvspan(1987.5, 1988.5, color="#D9D9D9", alpha=0.35, zorder=-1)
        axis.axvspan(2025.5, 2026.5, color="#D9D9D9", alpha=0.35, zorder=-1)
        axis.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=4, integer=True))
        axis.spines["left"].set_color("#777777")
        axis.spines["bottom"].set_color("#777777")
    axes[-1].set_xticks(list(range(1988, 2027, 3)))
    axes[-1].tick_params(axis="x", rotation=45)
    axes[-1].set_xlabel("Parliamentary/publication year")
    fig.suptitle("Annual records by independent government-text series", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.012, textwrap.fill("Counts are records, not speeches of all government or complete policy coverage. 1988 and 2026 are partial study years; cutoff 21 Sep 2026.", 150), fontsize=6.2, color="#555555")
    fig.tight_layout(rect=[0.03, 0.08, 0.99, 0.95])
    save_figure(fig, "annual_series_distribution", annual)

    fig, axes = plt.subplots(3, 1, figsize=(7.205, 4.7), sharex=True)
    quarter_labels = [f"{row['year']}-{row['quarter']}" for row in quarterly]
    qx = np.arange(len(quarter_labels))
    for axis, series in zip(axes, SERIES, strict=True):
        y = np.array([int(row[series]) for row in quarterly])
        axis.plot(qx, y, color=COLORS[series], linewidth=0.9)
        axis.fill_between(qx, y, color=COLORS[series], alpha=0.2)
        axis.set_title(LABELS[series], loc="left", fontweight="bold")
        axis.set_ylabel("Records")
        axis.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=3, integer=True))
    tick_positions = [index for index, label in enumerate(quarter_labels) if label.endswith("Q1") and int(label[:4]) % 3 == 0]
    axes[-1].set_xticks(tick_positions, [quarter_labels[index][:4] for index in tick_positions], rotation=45)
    axes[-1].set_xlabel("Year (quarterly observations)")
    fig.suptitle("Quarterly distribution by independent series", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.012, textwrap.fill("Zero means no observation in this collected source set, not no government activity. 2026 Q3 ends on 21 Sep; Q4 is outside the cutoff.", 150), fontsize=6.2, color="#555555")
    fig.tight_layout(rect=[0.03, 0.09, 0.99, 0.94])
    save_figure(fig, "quarterly_series_distribution", quarterly)

    fig, axes = plt.subplots(1, 3, figsize=(7.205, 2.9))
    for axis, row in zip(axes, before_after, strict=True):
        values = [int(row["before"]), int(row["after"])]
        bars = axis.barh([0, 1], values, color=["#A8B4BB", "#24495F"], height=0.55)
        axis.set_yticks([0, 1], ["Before", "After"])
        axis.invert_yaxis()
        axis.set_title(row["measure"], loc="left", fontweight="bold", fontsize=7.4)
        axis.set_xlabel("Records")
        axis.xaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=4, integer=True, prune="upper"))
        axis.ticklabel_format(axis="x", style="plain", useOffset=False)
        maximum = max(values) or 1
        axis.set_xlim(0, maximum * 1.22)
        for bar, value in zip(bars, values, strict=True):
            axis.text(max(value, maximum * 0.015) + maximum * 0.025, bar.get_y() + bar.get_height() / 2, f"{value:,}", va="center", fontsize=6.4)
    fig.suptitle("Pre-2010 corpus before and after the bounded backfill", x=0.01, ha="left", fontweight="bold")
    fig.text(0.01, 0.042, textwrap.fill("Each panel has its own scale. Series remain analytically separate; ministerial answers/statements are not policy papers. Volume 200 and channel gaps remain explicit.", 115), fontsize=6.2, color="#555555")
    fig.tight_layout(rect=[0.03, 0.20, 0.99, 0.90], w_pad=2.0)
    save_figure(fig, "pre2010_before_after", before_after)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def build_reports() -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(DB), read_only=True)
    annual, quarterly = collect_distributions(connection)
    progress = progress_rows(connection)
    source_year_progress = source_year_progress_rows(connection)
    departments = department_register()
    exceptions = exception_rows()
    for canonical_url, extraction_status, extraction_reason in connection.execute(
        """
        SELECT c.canonical_url, a.extraction_status, a.extraction_reason
        FROM acquisition_object_statuses a
        JOIN content_objects c USING(content_object_id)
        WHERE a.batch_id='govuk_historical_policy_1988_2009_20260921_v1'
          AND a.download_status='success'
          AND a.extraction_status<>'success'
        ORDER BY c.canonical_url
        """
    ).fetchall():
        exceptions.append(
            {
                "source": "GOV.UK historical policy",
                "target": canonical_url,
                "stage": "downloaded attachment extraction",
                "reason": f"{extraction_status}: {extraction_reason}",
            }
        )
    historic_revision = read_json(REPORTS / "historic_manifest_revision.json", {})
    historic_repair = read_json(REPORTS / "historic_parser_artifact_repair.json", {})
    gap_answers = read_json(MANIFESTS / "hansard_gap_answer_summary.json", {})
    gap_candidates = read_json(MANIFESTS / "hansard_gap_statement_candidate_summary.json", {})
    gap_statements = read_json(MANIFESTS / "hansard_gap_statement_summary.json", {})
    gap_archive = read_json(MANIFESTS / "hansard_gap_archive_answer_summary.json", {})
    gap_complete = bool(
        read_json(MANIFESTS / "hansard_gap_record_summary.json", {})
        and gap_archive.get("successful_indexes") == gap_archive.get("sitting_day_index_targets")
        and gap_archive.get("downloaded_text_pages") == gap_archive.get("unique_target_text_pages")
        and gap_archive.get("parse_errors") == 0
        and gap_candidates.get("complete_partitions") == gap_candidates.get("partitions")
        and gap_statements.get("candidate_downloaded") == gap_statements.get("candidate_targets")
    )
    gap_interpretation = (
        "The official Commons sitting-day indexes and linked publications-archive answer pages, together with the Written statement detail partitions, completed for 2010-05-01 through 2014-09-11 within the approved DEFRA/DECC scope. This closes the observed channel break only for those exact source partitions; it is not a census of all departments or climate-only speech."
        if gap_complete
        else f"The interval 2010-05-01 through 2014-09-11 remains a documented partial channel gap: {gap_archive.get('successful_indexes', 0)}/{gap_archive.get('sitting_day_index_targets', 0)} dated indexes were verified, {gap_archive.get('downloaded_text_pages', 0)}/{gap_archive.get('unique_target_text_pages', 0)} frozen answer pages were acquired, {gap_archive.get('failed_text_pages', 0)} page requests failed and {gap_archive.get('unprocessed_text_pages', 0)} pages were left unrequested after the dynamic throttle stop. Missing observations are not interpreted as zero speech."
    )
    current_policy_pre2010 = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM documents d JOIN sources s USING(source_id)
            WHERE s.source_name LIKE 'GOV.UK%' AND d.publication_date < DATE '2010-01-01'
            """
        ).fetchone()[0]
    )
    answers_pre2010 = int(connection.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_answer' AND publication_date < DATE '2010-01-01'").fetchone()[0])
    statements_pre2010 = int(connection.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_statement' AND publication_date < DATE '2010-01-01'").fetchone()[0])
    before_after = [
        {"measure": "Policy-source records", "before": BASELINE_PRE2010, "after": current_policy_pre2010, "change": current_policy_pre2010 - BASELINE_PRE2010},
        {"measure": "Ministerial answers", "before": 0, "after": answers_pre2010, "change": answers_pre2010},
        {"measure": "Ministerial statements", "before": 0, "after": statements_pre2010, "change": statements_pre2010},
    ]
    write_csv(REPORTS / "annual_distribution.csv", annual)
    write_csv(REPORTS / "quarterly_distribution.csv", quarterly)
    write_csv(REPORTS / "source_progress.csv", progress)
    write_csv(REPORTS / "source_year_progress.csv", source_year_progress)
    write_csv(REPORTS / "department_genre_register.csv", departments)
    write_csv(REPORTS / "exceptions_and_gaps.csv", exceptions)
    write_csv(REPORTS / "pre2010_before_after.csv", before_after)
    build_figures(annual, quarterly, before_after)

    series_totals = {
        series: int(connection.execute(
            f"SELECT COUNT(*) FROM documents d JOIN sources s USING(source_id) WHERE {series_sql()}=?", [series]
        ).fetchone()[0])
        for series in SERIES
    }
    missing_dates = int(connection.execute("SELECT COUNT(*) FROM documents WHERE publication_date IS NULL").fetchone()[0])
    question_segments = int(connection.execute("SELECT COUNT(*) FROM text_segments WHERE heading LIKE 'Question/context%'").fetchone()[0])
    response_segments = int(connection.execute("SELECT COUNT(*) FROM text_segments WHERE heading IN ('Government response','Ministerial written statement')").fetchone()[0])
    frozen_checks = []
    for name, (path, expected) in FROZEN_HASHES.items():
        observed = sha256_file(path) if path.exists() else "missing"
        frozen_checks.append({"artifact": name, "path": str(path.relative_to(PROJECT_ROOT)), "expected_sha256": expected, "observed_sha256": observed, "passed": observed == expected})
    db_checks = {
        "source_external_duplicates": int(connection.execute("SELECT COUNT(*) FROM (SELECT source_id, external_id FROM documents GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]),
        "canonical_url_duplicates": int(connection.execute("SELECT COUNT(*) FROM (SELECT canonical_url FROM documents GROUP BY 1 HAVING COUNT(*)>1)").fetchone()[0]),
        "orphan_segments": int(connection.execute("SELECT COUNT(*) FROM text_segments t LEFT JOIN content_versions v USING(content_version_id) WHERE v.content_version_id IS NULL").fetchone()[0]),
        "orphan_voice": int(connection.execute("SELECT COUNT(*) FROM voice_attributions a LEFT JOIN documents d USING(document_id) WHERE d.document_id IS NULL").fetchone()[0]),
        "historic_raw_records_not_marked_derived": int(connection.execute("SELECT COUNT(*) FROM raw_records WHERE batch_id='commons_historic_hansard_1988_2004_20260921_v1' AND validation_status NOT LIKE 'derived_record_from_official_bulk_xml%'").fetchone()[0]),
        "historic_content_objects_not_zip_xml": int(connection.execute("SELECT COUNT(*) FROM acquisition_object_statuses WHERE batch_id='commons_historic_hansard_1988_2004_20260921_v1' AND actual_format<>'zip_xml'").fetchone()[0]),
        "archive_answer_raw_records_not_marked_derived": int(connection.execute("SELECT COUNT(*) FROM raw_records WHERE batch_id='commons_hansard_api_20100501_20140911_20260921_v1' AND external_id LIKE 'publications_hansard:%' AND validation_status NOT LIKE 'derived_record_from_official_archive_html%'").fetchone()[0]),
        "archive_parent_objects_not_html": int(connection.execute("SELECT COUNT(*) FROM acquisition_object_statuses a JOIN content_objects c USING(content_object_id) WHERE a.batch_id='commons_hansard_api_20100501_20140911_20260921_v1' AND c.canonical_url LIKE 'https://publications.parliament.uk/%' AND a.actual_format<>'html'").fetchone()[0]),
        "archive_derived_record_count_mismatch": abs(int(connection.execute("SELECT COUNT(*) FROM raw_records WHERE batch_id='commons_hansard_api_20100501_20140911_20260921_v1' AND external_id LIKE 'publications_hansard:%'").fetchone()[0]) - len(read_csv(MANIFESTS / "hansard_gap_archive_answer_manifest.csv"))),
        "modern_raw_records_not_marked_derived": int(connection.execute("SELECT COUNT(*) FROM raw_records WHERE batch_id='commons_questions_statements_20140912_20260921_v1' AND validation_status NOT LIKE 'derived_record_from_official_api_list_response%'").fetchone()[0]),
        "modern_parent_objects_not_json": int(connection.execute("SELECT COUNT(*) FROM acquisition_object_statuses WHERE batch_id='commons_questions_statements_20140912_20260921_v1' AND actual_format<>'json'").fetchone()[0]),
        "modern_derived_record_count_mismatch": abs(int(connection.execute("SELECT COUNT(*) FROM raw_records WHERE batch_id='commons_questions_statements_20140912_20260921_v1'").fetchone()[0]) - len(read_csv(MANIFESTS / "modern_acquisition_status.csv"))),
        "successful_parliament_fetches_without_http_200": int(connection.execute("SELECT COUNT(*) FROM content_fetches WHERE batch_id IN ('commons_hansard_api_2005_20100430_20260921_v1','commons_hansard_api_20100501_20140911_20260921_v1','commons_questions_statements_20140912_20260921_v1') AND collection_status='success' AND status_code<>200").fetchone()[0]),
    }
    csv_annual_totals = {series: sum(int(row[series]) for row in annual) for series in SERIES}
    quarterly_matches_annual = all(
        sum(int(row[series]) for row in quarterly if int(row["year"]) == year)
        == int(next(value for value in annual if value["year"] == year)[series])
        for year in YEARS
        for series in SERIES
    )
    checks = {
        "generated_at": date.today().isoformat(),
        "series_totals_database": series_totals,
        "series_totals_annual_csv": csv_annual_totals,
        "annual_csv_matches_database": series_totals == csv_annual_totals,
        "quarterly_matches_annual": quarterly_matches_annual,
        "database_checks": db_checks,
        "frozen_artifacts": frozen_checks,
        "passed": series_totals == csv_annual_totals and quarterly_matches_annual and all(value == 0 for value in db_checks.values()) and all(row["passed"] for row in frozen_checks),
    }
    write_json(REPORTS / "final_integrity_checks.json", checks)
    connection.close()

    progress_md = markdown_table(
        ["Source/tranche", "Series", "Enumerated target", "Already in 06", "Net-new target", "Original acquired", "Parsed", "Formally committed", "Failed target records", "Failed/retry objects", "Unprocessed records", "Unprocessed content objects"],
        [[row["source_tranche"], row["series"], row["enumerated_targets"], row["already_in_06"], row["net_new_expected"], row["original_text_acquired_records"], row["parsed_records"], row["formally_committed_records"], row["failed_target_records"], row["failed_or_retry_objects"], row["not_yet_processed_records"], row["unprocessed_content_objects"]] for row in progress],
    )
    before_md = markdown_table(["Series", "Before", "After", "Change"], [[row["measure"], row["before"], row["after"], row["change"]] for row in before_after])
    report = f"""# Historical UK government acquisition: final acceptance

Cutoff: **2026-09-21**. Database: `{DB.relative_to(PROJECT_ROOT)}`. This task adds bounded historical policies and an independent House of Commons ministerial written-answer/statement series. It does not modify the proposal, clean the corpus, vectorise text, or run model analysis.

## Outcome

- Policy-source publication records now total **{series_totals['policy_document']:,}**; pre-2010 policy-source records increased from **{BASELINE_PRE2010:,}** to **{current_policy_pre2010:,}**. The original Search-API `policy_paper` / current Content-API type mismatch remains recorded rather than being recast.
- Ministerial written answers total **{series_totals['ministerial_written_answer']:,}**; written statements total **{series_totals['ministerial_written_statement']:,}**. They remain separate document types and denominators.
- Question/context segments retained separately: **{question_segments:,}**. Government-response/statement segments: **{response_segments:,}**. A question is never counted as a government response.
- Missing publication/parliamentary dates across the whole database: **{missing_dates:,}**; these are not reassigned from retrieval dates.
- The corrected Historic Hansard parser revised the frozen record manifest from **{int(historic_revision.get('previous_frozen_target_records', 0)):,}** to **{int(historic_revision.get('revised_frozen_target_records', 0)):,}** records. It excluded **{int(historic_repair.get('excluded_documents', 0)):,}** task-created parser artifacts transactionally while retaining their raw evidence; no second full temporary smoke ingestion was run.

{before_md}

## Source-specific progress

{progress_md}

Detailed status and denominator notes are in `source_progress.csv`. Object counts and record counts are deliberately not added together.
The year-level reconciliation is in `source_year_progress.csv`; policy object values there are within-year association counts and are not a cross-year unique-object total.

## Coverage interpretation

The policy backfill is complete only within the verified GOV.UK DTI, DECC, BERR and DETR organisation-tag query. DETR returned zero; no verified searchable UK DoE or MAFF GOV.UK organisation route was invented, and Northern Ireland DoE was not substituted. The official UK Government Web Archive A–Z index confirmed DTI, BERR, DECC and Defra site routes, but the first bounded DTI timeline request returned an AWS WAF human-verification page. The collector did not bypass that control or repeat the same blocked service for the other routes, so no archive-policy denominator or archive records are claimed.

Policy dates use official `first_published_at`. Downloaded GOV.UK pages and attachments are the versions available at this acquisition time; where `updated_at` is later, the current text is not assumed to reproduce the wording of the first-published version.

Historic Commons XML provides department-group enumeration for 1988–2004. Standalone written statements appear only where the archive supplies that category; the series is not backfilled before the category exists. For 2005–April 2010, official sitting calendars and daily section trees establish department-specific answer-section targets before detail acquisition. The current Hansard service explicitly does not expose post-April-2010 written-answer data, so the gap tranche uses the official dated publications archive: each sitting-day index freezes exact DEFRA/DECC links, the linked HTML is the downloaded parent evidence, and per-answer JSON is explicitly marked as derived rather than as a fictitious HTTP response. The record unit can contain multiple question or response segments. The modern Questions and Statements API begins in September 2014. Its 174 frozen list responses contain complete question/answer or statement fields for all 65,988 official IDs; per-record JSON is derived from those parents and no per-record HTTP 200 is invented. A stopped 1,000-record detail-path diagnostic is retained separately and does not define formal progress. {gap_interpretation}

BEIS, DTI and BERR are broad business departments. Their all-topic departmental records are preserved as enumerated; they must not be described as a climate-only sample without a later, separately governed selection stage.

## Distribution and use boundaries

![Annual distribution](annual_series_distribution.png)

![Quarterly distribution](quarterly_series_distribution.png)

The annual and quarterly CSVs contain zero rows for unobserved periods. Zero means “not observed in these collected official source partitions”, not “no government discourse”. 1988 is a partial study-start year and 2026 ends on 21 September.

Recommended provisional use: analyse policy documents, ministerial answers and ministerial statements as three independent series; restrict time comparisons to periods with demonstrable source continuity; retain explicit source-regime indicators; and do not claim a continuous 1988–2026 census or climate/fear selection. Do not impute unavailable source partitions or the invalid Historic Hansard volume 200.

## Residual issues

See `exceptions_and_gaps.csv`. The principal residuals are four downloaded historical-policy PDFs marked `needs_ocr`, the invalid official volume-200 download, failed statement/detail/archive-index or archive-page requests, unresolved UK DoE/MAFF policy indexes, and the explicitly incomplete 2010–2014 source partitions.

## Integrity acceptance

- Annual CSV totals match database series totals: **{checks['annual_csv_matches_database']}**.
- Quarterly rows reconcile to annual rows: **{checks['quarterly_matches_annual']}**.
- Duplicate/orphan checks: `{json.dumps(db_checks, ensure_ascii=False)}`.
- Frozen 04/05 artefacts unchanged: **{all(row['passed'] for row in frozen_checks)}**.
- Overall acceptance passed: **{checks['passed']}**.
"""
    (REPORTS / "historical_government_acquisition_report.md").write_text(report, encoding="utf-8")
    cards = "".join(
        f"<div class='card'><span>{html.escape(LABELS[key])}</span><strong>{value:,}</strong></div>"
        for key, value in series_totals.items()
    )
    progress_html = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row[key]))}</td>" for key in ["source_tranche", "series", "enumerated_targets", "already_in_06", "net_new_expected", "original_text_acquired_records", "parsed_records", "formally_committed_records", "failed_target_records", "failed_or_retry_objects", "not_yet_processed_records", "unprocessed_content_objects"]) + "</tr>"
        for row in progress
    )
    page = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Historical government acquisition</title><style>
body{{font:15px/1.55 system-ui,-apple-system,sans-serif;color:#20303a;background:#f5f6f3;margin:0}}main{{max-width:1120px;margin:auto;padding:32px}}h1{{font-size:28px;margin-bottom:6px}}h2{{margin-top:34px;border-bottom:1px solid #ccd3d4;padding-bottom:6px}}.meta{{color:#5d6a70}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}}.card{{background:white;border:1px solid #d7ddde;padding:16px;border-radius:4px}}.card span{{display:block;color:#5d6a70}}.card strong{{font-size:28px;color:#24495F}}table{{border-collapse:collapse;width:100%;background:white;font-size:13px}}th,td{{border:1px solid #d7ddde;padding:7px;text-align:right}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}img{{width:100%;background:white;border:1px solid #d7ddde;margin:10px 0}}.warn{{border-left:4px solid #C57A43;background:#fff;padding:12px 16px}}code{{background:#e8ebea;padding:2px 4px}}@media(max-width:760px){{.cards{{grid-template-columns:1fr}}main{{padding:18px;overflow-x:auto}}}}</style></head><body><main>
<h1>Historical UK government acquisition</h1><p class='meta'>Final acceptance · cutoff 21 Sep 2026 · existing 06 DuckDB</p><div class='cards'>{cards}</div>
<h2>Pre-2010 change</h2><img src='pre2010_before_after.svg' alt='Pre-2010 before and after record counts'>
<h2>Source progress</h2><table><thead><tr><th>Source</th><th>Series</th><th>Enumerated target</th><th>Already in 06</th><th>Net-new target</th><th>Original acquired</th><th>Parsed</th><th>Formally committed</th><th>Failed target records</th><th>Failed/retry objects</th><th>Unprocessed records</th><th>Unprocessed content objects</th></tr></thead><tbody>{progress_html}</tbody></table>
<h2>Time distribution</h2><img src='annual_series_distribution.svg' alt='Annual records by series'><img src='quarterly_series_distribution.svg' alt='Quarterly records by series'>
<h2>Boundary</h2><p class='warn'>The three series remain separate. Zero observations are not evidence of zero government activity. 1988 and 2026 are partial study years. {html.escape(gap_interpretation)} DTI/BERR/BEIS contain broader business material.</p>
<p>Full methods, residual issues, denominator notes and acceptance checks: <a href='historical_government_acquisition_report.md'>Markdown report</a>, <a href='final_integrity_checks.json'>integrity JSON</a>, <a href='source_progress.csv'>progress CSV</a>, <a href='exceptions_and_gaps.csv'>exceptions CSV</a>.</p>
</main></body></html>"""
    (REPORTS / "index.html").write_text(page, encoding="utf-8")
    result = {"generated_at": date.today().isoformat(), "series_totals": series_totals, "pre2010": {"policy": current_policy_pre2010, "answers": answers_pre2010, "statements": statements_pre2010}, "integrity_passed": checks["passed"]}
    write_json(REPORTS / "report_summary.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(build_reports(), ensure_ascii=False, indent=2))
