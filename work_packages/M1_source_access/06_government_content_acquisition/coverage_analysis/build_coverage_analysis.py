from __future__ import annotations

import csv
import hashlib
import html
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle


HERE = Path(__file__).resolve().parent
WORK_PACKAGE = HERE.parent
PROJECT_ROOT = HERE.parents[3]
DATABASE = WORK_PACKAGE / "fear_temperature_government_content.duckdb"
CONFIG_PATH = WORK_PACKAGE / "config.yaml"
OVERRIDES_PATH = HERE / "retry_url_overrides.json"
BATCH_ID = "govuk_defra_policy_paper_content_20260921_v1"
CUTOFF = date(2026, 9, 21)
YEARS = list(range(1988, 2027))
MONTHS = list(range(1, 13))
BASELINE = {
    "documents": 1020,
    "webpages": 1020,
    "attachments": 2005,
    "content_objects": 3025,
    "attempted": 3025,
    "downloaded": 3016,
    "extracted": 2995,
    "download_exceptions": 9,
    "downloaded_extraction_exceptions": 21,
    "segments": 2_853_343,
}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percent(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 6) if denominator else None


def fmt_percent(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}%"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))["overrides"]
    connection = duckdb.connect(str(DATABASE), read_only=True)

    documents = [
        dict(zip([column[0] for column in cursor.description], row, strict=True))
        for cursor in [
            connection.execute(
                """
                SELECT document_id, title, canonical_url, publication_date,
                       publication_timestamp, updated_timestamp, collected_at,
                       content_type
                FROM documents ORDER BY document_id
                """
            )
        ]
        for row in cursor.fetchall()
    ]
    relations_cursor = connection.execute(
        """
        SELECT x.document_id, x.content_object_id, x.relationship_type,
               o.object_kind, o.title AS object_title, o.canonical_url,
               s.download_status, s.extraction_status, s.actual_format,
               s.content_version_id, s.segment_count
        FROM document_content_objects x
        JOIN content_objects o USING (content_object_id)
        JOIN acquisition_object_statuses s USING (content_object_id)
        WHERE s.batch_id=?
        ORDER BY x.document_id, x.ordinal, x.content_object_id
        """,
        [BATCH_ID],
    )
    relation_columns = [column[0] for column in relations_cursor.description]
    relations = [
        dict(zip(relation_columns, row, strict=True)) for row in relations_cursor.fetchall()
    ]
    stats_cursor = connection.execute(
        """
        SELECT s.content_object_id,
               COUNT(t.segment_id) AS extracted_segments,
               COALESCE(SUM(length(t.segment_text)), 0) AS extracted_characters
        FROM acquisition_object_statuses s
        LEFT JOIN text_segments t ON t.content_version_id=s.content_version_id
             AND t.representation_kind='source_extracted'
        WHERE s.batch_id=?
        GROUP BY s.content_object_id
        """,
        [BATCH_ID],
    )
    object_stats = {
        str(row[0]): {"segments": int(row[1]), "characters": int(row[2])}
        for row in stats_cursor.fetchall()
    }
    relations_by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation in relations:
        relations_by_document[str(relation["document_id"])].append(relation)

    valid_documents = [item for item in documents if item["publication_date"] is not None]
    missing_date_documents = [item for item in documents if item["publication_date"] is None]
    annual_rows: list[dict[str, Any]] = []
    for year in YEARS:
        year_documents = [
            item for item in valid_documents if item["publication_date"].year == year
        ]
        year_object_ids: dict[str, set[str]] = {"webpage": set(), "attachment": set()}
        metrics = Counter()
        for document in year_documents:
            linked = relations_by_document[str(document["document_id"])]
            webpages = [item for item in linked if item["relationship_type"] == "landing_page"]
            attachments = [item for item in linked if item["relationship_type"] == "attachment"]
            for item in linked:
                year_object_ids[str(item["object_kind"])].add(str(item["content_object_id"]))
            if attachments:
                metrics["records_with_attachment"] += 1
                attachment_successes = sum(
                    item["extraction_status"] == "success" for item in attachments
                )
                if attachment_successes == len(attachments):
                    metrics["attachment_all_extract_success_records"] += 1
                elif attachment_successes:
                    metrics["attachment_partial_extract_success_records"] += 1
                else:
                    metrics["attachment_no_extract_success_records"] += 1
            if any(item["download_status"] == "success" for item in linked):
                metrics["records_any_download_success"] += 1
            if any(item["download_status"] == "success" for item in webpages):
                metrics["records_webpage_download_success"] += 1
            if any(item["download_status"] == "success" for item in attachments):
                metrics["records_attachment_download_success"] += 1
            if any(item["extraction_status"] == "success" for item in linked):
                metrics["records_any_extract_success"] += 1
            if any(item["extraction_status"] == "success" for item in webpages):
                metrics["records_webpage_extract_success"] += 1
            if any(item["extraction_status"] == "success" for item in attachments):
                metrics["records_attachment_extract_success"] += 1
        webpage_chars = sum(
            object_stats[object_id]["characters"] for object_id in year_object_ids["webpage"]
        )
        attachment_chars = sum(
            object_stats[object_id]["characters"]
            for object_id in year_object_ids["attachment"]
        )
        webpage_segments = sum(
            object_stats[object_id]["segments"] for object_id in year_object_ids["webpage"]
        )
        attachment_segments = sum(
            object_stats[object_id]["segments"]
            for object_id in year_object_ids["attachment"]
        )
        attachment_denominator = metrics["records_with_attachment"]
        annual_rows.append(
            {
                "period_type": "calendar_year",
                "year": year,
                "cutoff_status": (
                    "partial_year_to_2026-09-21"
                    if year == 2026
                    else "full_calendar_year_within_frozen_query_range"
                ),
                "publication_records": len(year_documents),
                "record_share_fraction": round(len(year_documents) / len(documents), 9),
                "record_share_percent": percent(len(year_documents), len(documents)),
                "records_with_attachment": attachment_denominator,
                "records_any_download_success": metrics["records_any_download_success"],
                "records_webpage_download_success": metrics[
                    "records_webpage_download_success"
                ],
                "records_attachment_download_success": metrics[
                    "records_attachment_download_success"
                ],
                "records_any_extract_success": metrics["records_any_extract_success"],
                "records_webpage_extract_success": metrics[
                    "records_webpage_extract_success"
                ],
                "records_attachment_extract_success": metrics[
                    "records_attachment_extract_success"
                ],
                "attachment_all_extract_success_records": metrics[
                    "attachment_all_extract_success_records"
                ],
                "attachment_partial_extract_success_records": metrics[
                    "attachment_partial_extract_success_records"
                ],
                "attachment_no_extract_success_records": metrics[
                    "attachment_no_extract_success_records"
                ],
                "attachment_all_success_percent_of_records_with_attachment": percent(
                    metrics["attachment_all_extract_success_records"], attachment_denominator
                ),
                "attachment_partial_success_percent_of_records_with_attachment": percent(
                    metrics["attachment_partial_extract_success_records"],
                    attachment_denominator,
                ),
                "attachment_no_success_percent_of_records_with_attachment": percent(
                    metrics["attachment_no_extract_success_records"], attachment_denominator
                ),
                "webpage_extracted_characters": webpage_chars,
                "attachment_extracted_characters_parent_year_association": attachment_chars,
                "webpage_extracted_segments": webpage_segments,
                "attachment_extracted_segments_parent_year_association": attachment_segments,
                "date_note": "UTC calendar date of first_published_at",
            }
        )
    annual_rows.append(
        {
            key: (
                "missing_date"
                if key == "period_type"
                else ""
                if key in {"year", "cutoff_status"}
                else len(missing_date_documents)
                if key == "publication_records"
                else 0
            )
            for key in annual_rows[0]
        }
    )
    annual_rows[-1]["date_note"] = (
        "Records without a verifiable first_published_at; kept separate from zero-return years"
    )
    annual_fields = list(annual_rows[0])
    write_csv(HERE / "annual_distribution.csv", annual_rows, annual_fields)

    decade_specs = [
        ("1988-1989", 1988, 1989, "partial_opening_decade"),
        ("1990-1999", 1990, 1999, "complete_calendar_decade"),
        ("2000-2009", 2000, 2009, "complete_calendar_decade"),
        ("2010-2019", 2010, 2019, "complete_calendar_decade"),
        ("2020-2026-09-21", 2020, 2026, "partial_closing_decade_to_cutoff"),
    ]
    count_fields = [
        "publication_records",
        "records_with_attachment",
        "records_any_download_success",
        "records_webpage_download_success",
        "records_attachment_download_success",
        "records_any_extract_success",
        "records_webpage_extract_success",
        "records_attachment_extract_success",
        "attachment_all_extract_success_records",
        "attachment_partial_extract_success_records",
        "attachment_no_extract_success_records",
        "webpage_extracted_characters",
        "attachment_extracted_characters_parent_year_association",
        "webpage_extracted_segments",
        "attachment_extracted_segments_parent_year_association",
    ]
    decade_rows: list[dict[str, Any]] = []
    year_rows = [row for row in annual_rows if row["period_type"] == "calendar_year"]
    for label, start_year, end_year, boundary_status in decade_specs:
        selected = [row for row in year_rows if start_year <= int(row["year"]) <= end_year]
        decade = {
            "period_type": "decade_group",
            "period_label": label,
            "start_year": start_year,
            "end_year": end_year,
            "boundary_status": boundary_status,
            "years_included": end_year - start_year + 1,
        }
        for field in count_fields:
            decade[field] = sum(int(row[field]) for row in selected)
        decade["record_share_fraction"] = round(
            decade["publication_records"] / len(documents), 9
        )
        decade["record_share_percent"] = percent(
            decade["publication_records"], len(documents)
        )
        denominator = decade["records_with_attachment"]
        decade["attachment_all_success_percent_of_records_with_attachment"] = percent(
            decade["attachment_all_extract_success_records"], denominator
        )
        decade[
            "attachment_partial_success_percent_of_records_with_attachment"
        ] = percent(decade["attachment_partial_extract_success_records"], denominator)
        decade["attachment_no_success_percent_of_records_with_attachment"] = percent(
            decade["attachment_no_extract_success_records"], denominator
        )
        decade["date_note"] = (
            "Sum of annual parent-year association counts; shared attachments may recur across years"
        )
        decade_rows.append(decade)
    missing_decade = {field: 0 for field in decade_rows[0]}
    missing_decade.update(
        {
            "period_type": "missing_date",
            "period_label": "MISSING_DATE",
            "start_year": "",
            "end_year": "",
            "boundary_status": "kept_separate",
            "years_included": 0,
            "publication_records": len(missing_date_documents),
            "date_note": "Records without a verifiable first_published_at",
        }
    )
    decade_rows.append(missing_decade)
    decade_fields = list(decade_rows[0])
    write_csv(HERE / "decade_distribution.csv", decade_rows, decade_fields)

    month_counts = Counter(
        (item["publication_date"].year, item["publication_date"].month)
        for item in valid_documents
    )
    year_month_rows: list[dict[str, Any]] = []
    for year in YEARS:
        for month in MONTHS:
            if year == 2026 and month > 9:
                window_status = "outside_frozen_query_after_cutoff"
            elif year == 2026 and month == 9:
                window_status = "partial_month_to_2026-09-21"
            else:
                window_status = "full_calendar_month_within_query_range"
            year_month_rows.append(
                {
                    "year": year,
                    "month": month,
                    "publication_records": int(month_counts[(year, month)]),
                    "window_status": window_status,
                    "date_field": "first_published_at_utc_calendar_date",
                }
            )
    year_month_rows.append(
        {
            "year": "",
            "month": "",
            "publication_records": len(missing_date_documents),
            "window_status": "missing_first_published_at",
            "date_field": "kept_separate",
        }
    )
    write_csv(HERE / "year_month_counts.csv", year_month_rows, list(year_month_rows[0]))

    status_cursor = connection.execute(
        """
        SELECT object_kind, download_status, extraction_status, COUNT(*) AS object_count
        FROM acquisition_object_statuses WHERE batch_id=?
        GROUP BY ALL ORDER BY object_kind, download_status, extraction_status
        """,
        [BATCH_ID],
    )
    status_rows = status_cursor.fetchall()
    object_counts = connection.execute(
        """
        SELECT COUNT(*) AS attempted,
               COUNT(*) FILTER (WHERE download_status='success') AS downloaded,
               COUNT(*) FILTER (WHERE extraction_status='success') AS extracted,
               COUNT(*) FILTER (WHERE download_status<>'success') AS download_exceptions,
               COUNT(*) FILTER (
                   WHERE download_status='success' AND extraction_status<>'success'
               ) AS downloaded_extraction_exceptions,
               SUM(segment_count) AS segments
        FROM acquisition_object_statuses WHERE batch_id=?
        """,
        [BATCH_ID],
    ).fetchone()
    final_counts = dict(
        zip(
            [
                "attempted",
                "downloaded",
                "extracted",
                "download_exceptions",
                "downloaded_extraction_exceptions",
                "segments",
            ],
            (int(value) for value in object_counts),
            strict=True,
        )
    )
    kind_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT object_kind, COUNT(*) FROM content_objects GROUP BY 1"
        ).fetchall()
    }
    kind_downloads = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            """
            SELECT object_kind, COUNT(*) FILTER (WHERE download_status='success')
            FROM acquisition_object_statuses WHERE batch_id=? GROUP BY 1
            """,
            [BATCH_ID],
        ).fetchall()
    }
    kind_extractions = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            """
            SELECT object_kind, COUNT(*) FILTER (WHERE extraction_status='success')
            FROM acquisition_object_statuses WHERE batch_id=? GROUP BY 1
            """,
            [BATCH_ID],
        ).fetchall()
    }
    attachment_total_records = sum(
        int(row["records_with_attachment"]) for row in year_rows
    )
    attachment_all_records = sum(
        int(row["attachment_all_extract_success_records"]) for row in year_rows
    )
    attachment_partial_records = sum(
        int(row["attachment_partial_extract_success_records"]) for row in year_rows
    )
    attachment_none_records = sum(
        int(row["attachment_no_extract_success_records"]) for row in year_rows
    )
    coverage_rows = [
        {
            "metric_group": "frozen_list",
            "metric": "Frozen-list attempt completion",
            "object_scope": "all objects",
            "numerator": final_counts["attempted"],
            "denominator": BASELINE["content_objects"],
            "percent": percent(final_counts["attempted"], BASELINE["content_objects"]),
            "interpretation": "Attempted within the frozen 3,025-object list",
        },
        {
            "metric_group": "download",
            "metric": "Download success",
            "object_scope": "all objects",
            "numerator": final_counts["downloaded"],
            "denominator": BASELINE["content_objects"],
            "percent": percent(final_counts["downloaded"], BASELINE["content_objects"]),
            "interpretation": "Current object download state after bounded retry",
        },
        {
            "metric_group": "download",
            "metric": "Download success",
            "object_scope": "webpages",
            "numerator": kind_downloads["webpage"],
            "denominator": kind_counts["webpage"],
            "percent": percent(kind_downloads["webpage"], kind_counts["webpage"]),
            "interpretation": "Webpage objects only",
        },
        {
            "metric_group": "download",
            "metric": "Download success",
            "object_scope": "attachments",
            "numerator": kind_downloads["attachment"],
            "denominator": kind_counts["attachment"],
            "percent": percent(kind_downloads["attachment"], kind_counts["attachment"]),
            "interpretation": "Unique attachment objects only",
        },
        {
            "metric_group": "extraction_given_download",
            "metric": "Extraction success among downloaded objects",
            "object_scope": "all objects",
            "numerator": final_counts["extracted"],
            "denominator": final_counts["downloaded"],
            "percent": percent(final_counts["extracted"], final_counts["downloaded"]),
            "interpretation": "Successful source-text extraction, not full-text completeness",
        },
        {
            "metric_group": "extraction_given_download",
            "metric": "Extraction success among downloaded objects",
            "object_scope": "webpages",
            "numerator": kind_extractions["webpage"],
            "denominator": kind_downloads["webpage"],
            "percent": percent(kind_extractions["webpage"], kind_downloads["webpage"]),
            "interpretation": "Webpage objects only",
        },
        {
            "metric_group": "extraction_given_download",
            "metric": "Extraction success among downloaded objects",
            "object_scope": "attachments",
            "numerator": kind_extractions["attachment"],
            "denominator": kind_downloads["attachment"],
            "percent": percent(kind_extractions["attachment"], kind_downloads["attachment"]),
            "interpretation": "Unique attachment objects only",
        },
        {
            "metric_group": "target_text_availability",
            "metric": "Target-object text availability",
            "object_scope": "all objects",
            "numerator": final_counts["extracted"],
            "denominator": BASELINE["content_objects"],
            "percent": percent(final_counts["extracted"], BASELINE["content_objects"]),
            "interpretation": "Successful extraction divided by all target objects",
        },
        {
            "metric_group": "target_text_availability",
            "metric": "Target-object text availability",
            "object_scope": "webpages",
            "numerator": kind_extractions["webpage"],
            "denominator": kind_counts["webpage"],
            "percent": percent(kind_extractions["webpage"], kind_counts["webpage"]),
            "interpretation": "Webpage objects only",
        },
        {
            "metric_group": "target_text_availability",
            "metric": "Target-object text availability",
            "object_scope": "attachments",
            "numerator": kind_extractions["attachment"],
            "denominator": kind_counts["attachment"],
            "percent": percent(kind_extractions["attachment"], kind_counts["attachment"]),
            "interpretation": "Unique attachment objects only",
        },
        {
            "metric_group": "publication_attachment_text",
            "metric": "All linked attachments extracted",
            "object_scope": "publication records with attachments",
            "numerator": attachment_all_records,
            "denominator": attachment_total_records,
            "percent": percent(attachment_all_records, attachment_total_records),
            "interpretation": "Mutually exclusive record-level state",
        },
        {
            "metric_group": "publication_attachment_text",
            "metric": "Some but not all linked attachments extracted",
            "object_scope": "publication records with attachments",
            "numerator": attachment_partial_records,
            "denominator": attachment_total_records,
            "percent": percent(attachment_partial_records, attachment_total_records),
            "interpretation": "Mutually exclusive record-level state",
        },
        {
            "metric_group": "publication_attachment_text",
            "metric": "No linked attachment extracted",
            "object_scope": "publication records with attachments",
            "numerator": attachment_none_records,
            "denominator": attachment_total_records,
            "percent": percent(attachment_none_records, attachment_total_records),
            "interpretation": "Mutually exclusive record-level state",
        },
    ]
    write_csv(HERE / "coverage_metrics.csv", coverage_rows, list(coverage_rows[0]))

    latest_original_run = connection.execute(
        """
        SELECT run_id, started_at, finished_at FROM acquisition_runs
        WHERE phase='download_exception_retry_original_url' AND status='completed'
          AND attempted_count=9
        ORDER BY started_at DESC LIMIT 1
        """
    ).fetchone()
    replacement_run = connection.execute(
        """
        SELECT run_id, started_at, finished_at FROM acquisition_runs
        WHERE phase='download_exception_retry_official_replacement' AND status='completed'
        ORDER BY started_at DESC LIMIT 1
        """
    ).fetchone()
    original_events = {
        str(row[0]): json.loads(row[1])
        for row in connection.execute(
            "SELECT content_object_id, details_json FROM acquisition_events WHERE run_id=?",
            [latest_original_run[0]],
        ).fetchall()
    }
    replacement_events = {
        str(row[0]): json.loads(row[1])
        for row in connection.execute(
            "SELECT content_object_id, details_json FROM acquisition_events WHERE run_id=?",
            [replacement_run[0]],
        ).fetchall()
    }
    retry_cursor = connection.execute(
        """
        SELECT s.content_object_id, o.title, o.canonical_url,
               s.download_status, s.extraction_status, s.extraction_reason,
               s.segment_count, s.content_sha256, s.raw_path,
               f.request_url, f.final_url, f.status_code, f.retrieved_at
        FROM acquisition_object_statuses s
        JOIN content_objects o USING (content_object_id)
        JOIN content_fetches f ON f.fetch_id=s.fetch_id
        WHERE s.batch_id=? AND s.content_object_id IN (
            SELECT content_object_id FROM acquisition_events WHERE run_id=?
        )
        ORDER BY s.content_object_id
        """,
        [BATCH_ID, replacement_run[0]],
    )
    retry_columns = [column[0] for column in retry_cursor.description]
    current_retry_rows = [
        dict(zip(retry_columns, row, strict=True)) for row in retry_cursor.fetchall()
    ]
    initial_error_page_id = "cnt_9fffa8707949d2e58a6e"
    retry_rows: list[dict[str, Any]] = []
    for item in current_retry_rows:
        object_id = str(item["content_object_id"])
        original_event = original_events[object_id]
        replacement_event = replacement_events[object_id]
        mapping = overrides[object_id]
        retry_rows.append(
            {
                "content_object_id": object_id,
                "title": item["title"],
                "baseline_download_status": (
                    "error_page_http_200"
                    if object_id == initial_error_page_id
                    else "access_denied_http_403"
                ),
                "original_url": item["canonical_url"],
                "original_retry_at": latest_original_run[1].isoformat(),
                "original_retry_status_code": original_event.get("status_code"),
                "original_retry_download_status": (
                    "error_page"
                    if original_event.get("status_code") == 200
                    and object_id == initial_error_page_id
                    else "access_denied"
                ),
                "replacement_url": mapping["new_url"],
                "replacement_discovery_evidence": mapping["discovery_evidence"],
                "replacement_identity_basis": mapping["identity_basis"],
                "replacement_retry_at": replacement_run[1].isoformat(),
                "replacement_status_code": replacement_event.get("status_code"),
                "final_download_status": item["download_status"],
                "final_extraction_status": item["extraction_status"],
                "final_failure_reason": (
                    item["extraction_reason"]
                    if item["download_status"] != "success"
                    else ""
                ),
                "recovered": item["download_status"] == "success",
                "final_url": item["final_url"],
                "retrieved_at": item["retrieved_at"].isoformat(),
                "content_sha256": item["content_sha256"] or "",
                "raw_path": item["raw_path"] or "",
                "segment_count": int(item["segment_count"]),
            }
        )
    write_csv(HERE / "retry_results.csv", retry_rows, list(retry_rows[0]))

    decade_plot_rows = [row for row in decade_rows if row["period_type"] == "decade_group"]
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8,
            "axes.titlesize": 11,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    palette = {
        "primary": "#3F6278",
        "primary_light": "#86A5B7",
        "accent": "#B07D46",
        "neutral": "#D9DEE1",
        "text": "#26343D",
        "grid": "#DCE2E5",
    }

    def save_figure(fig: mpl.figure.Figure, stem: str) -> None:
        fig.savefig(HERE / f"{stem}.png", facecolor="white", dpi=300)
        fig.savefig(HERE / f"{stem}.pdf", facecolor="white")
        fig.savefig(HERE / f"{stem}.svg", facecolor="white")
        plt.close(fig)

    annual_values = [int(row["publication_records"]) for row in year_rows]
    fig, ax = plt.subplots(figsize=(7.2, 3.85))
    fig.subplots_adjust(left=0.085, right=0.99, top=0.84, bottom=0.24)
    colors = [palette["accent"] if year == 2026 else palette["primary"] for year in YEARS]
    ax.bar(YEARS, annual_values, width=0.82, color=colors, edgecolor="none")
    ax.set_title("Observed DEFRA-labelled policy-paper records by first publication year")
    ax.set_xlabel("Year of first_published_at (UTC calendar date)")
    ax.set_ylabel("Publication records")
    ax.set_xlim(1987.2, 2026.8)
    ax.set_ylim(0, max(annual_values) * 1.16)
    ax.set_xticks(list(range(1988, 2027, 2)))
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_rotation_mode("anchor")
        label.set_horizontalalignment("right")
    peak_index = int(np.argmax(annual_values))
    ax.text(
        YEARS[peak_index],
        annual_values[peak_index] + 3,
        str(annual_values[peak_index]),
        ha="center",
        va="bottom",
        fontsize=7,
        color=palette["text"],
    )
    ax.text(
        2026,
        annual_values[-1] + 3,
        f"{annual_values[-1]}*",
        ha="center",
        va="bottom",
        fontsize=7,
        color=palette["accent"],
    )
    fig.text(
        0.085,
        0.035,
        "Frozen GOV.UK Search API batch; 0 means no record observed in this source set, not no government policy.\n"
        "*2026 is partial to 21 Sep; missing first_published_at: 0.",
        ha="left",
        va="bottom",
        fontsize=7,
        color=palette["text"],
    )
    save_figure(fig, "annual_publication_records")

    fig, ax = plt.subplots(figsize=(7.2, 3.45))
    fig.subplots_adjust(left=0.19, right=0.97, top=0.82, bottom=0.22)
    decade_labels = [str(row["period_label"]) for row in decade_plot_rows]
    decade_counts = [int(row["publication_records"]) for row in decade_plot_rows]
    decade_colors = [
        palette["primary_light"] if index in {0, 4} else palette["primary"]
        for index in range(len(decade_plot_rows))
    ]
    y_positions = np.arange(len(decade_labels))
    bars = ax.barh(y_positions, decade_counts, color=decade_colors, height=0.62)
    ax.set_yticks(y_positions, decade_labels)
    ax.invert_yaxis()
    ax.set_xlabel("Publication records")
    ax.set_title("Batch composition by decade group")
    for bar, row in zip(bars, decade_plot_rows, strict=True):
        ax.text(
            bar.get_width() + 7,
            bar.get_y() + bar.get_height() / 2,
            f"{int(row['publication_records'])} ({float(row['record_share_percent']):.1f}%)",
            va="center",
            ha="left",
            fontsize=7,
            color=palette["text"],
        )
    ax.set_xlim(0, max(decade_counts) * 1.28)
    fig.text(
        0.19,
        0.035,
        "Opening group begins in 1988; closing group ends at the 21 Sep 2026 batch cutoff. "
        "Shares describe this frozen batch only.",
        ha="left",
        va="bottom",
        fontsize=7,
        color=palette["text"],
    )
    save_figure(fig, "decade_composition")

    matrix = np.zeros((len(YEARS), len(MONTHS)), dtype=float)
    for row_index, year in enumerate(YEARS):
        for column_index, month in enumerate(MONTHS):
            matrix[row_index, column_index] = month_counts[(year, month)]
    matrix[-1, 9:] = np.nan
    heatmap_colors = LinearSegmentedColormap.from_list(
        "academic_blue", ["#F3F5F4", "#B7CBD6", "#3F6278", "#213D50"]
    )
    heatmap_colors.set_bad("#D5D7D8")
    fig, ax = plt.subplots(figsize=(7.2, 8.45))
    fig.subplots_adjust(left=0.12, right=0.88, top=0.93, bottom=0.10)
    image = ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap=heatmap_colors)
    ax.set_title("Year × month distribution of observed publication records")
    ax.set_xlabel("Month")
    ax.set_ylabel("Year of first_published_at")
    ax.set_xticks(np.arange(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    tick_indices = list(range(0, len(YEARS), 2))
    if tick_indices[-1] != len(YEARS) - 1:
        tick_indices.append(len(YEARS) - 1)
    ax.set_yticks(tick_indices, [YEARS[index] for index in tick_indices])
    ax.set_xticks(np.arange(-0.5, 12, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(YEARS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.35)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.add_patch(
        Rectangle(
            (8 - 0.5, len(YEARS) - 1 - 0.5),
            1,
            1,
            fill=False,
            edgecolor=palette["accent"],
            linewidth=1.4,
        )
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.028, pad=0.025)
    colorbar.set_label("Publication records per month", fontsize=8)
    colorbar.ax.tick_params(labelsize=7)
    fig.text(
        0.12,
        0.025,
        "Grey: outside the frozen window (Oct-Dec 2026). Orange outline: partial Sep 2026.\n"
        "Pale in-scope cells with 0 are no observed record, not evidence of policy absence; missing dates: 0.",
        ha="left",
        va="bottom",
        fontsize=7,
        color=palette["text"],
    )
    save_figure(fig, "year_month_heatmap")

    first_observed_year = min(item["publication_date"].year for item in valid_documents)
    peak_year_row = max(year_rows, key=lambda row: int(row["publication_records"]))
    updated_count, maximum_update_gap = connection.execute(
        """
        SELECT COUNT(*) FILTER (WHERE updated_timestamp > publication_timestamp),
               MAX(date_diff('day', publication_timestamp, updated_timestamp))
        FROM documents
        """
    ).fetchone()
    type_drift = connection.execute(
        """
        SELECT document_id, title, content_type, canonical_url
        FROM documents WHERE content_type <> 'policy_paper'
        """
    ).fetchall()
    shared_attachment = connection.execute(
        """
        SELECT x.content_object_id,
               string_agg(CAST(year(d.publication_date) AS VARCHAR), ', ' ORDER BY d.publication_date),
               COUNT(*)
        FROM document_content_objects x JOIN documents d USING (document_id)
        WHERE x.relationship_type='attachment'
        GROUP BY x.content_object_id HAVING COUNT(*) > 1
        """
    ).fetchone()
    recovered_rows = [row for row in retry_rows if row["recovered"]]
    remaining_rows = [row for row in retry_rows if not row["recovered"]]

    pre_post_rows = [
        ["发布记录", "1,020", "1,020", "0"],
        ["网页目标", "1,020", "1,020", "0"],
        ["唯一附件目标", "2,005", "2,005", "0"],
        ["内容对象目标／已尝试", "3,025 / 3,025", "3,025 / 3,025", "0"],
        ["下载成功", f"{BASELINE['downloaded']:,}", f"{final_counts['downloaded']:,}", f"+{final_counts['downloaded'] - BASELINE['downloaded']}"],
        ["提取成功", f"{BASELINE['extracted']:,}", f"{final_counts['extracted']:,}", f"+{final_counts['extracted'] - BASELINE['extracted']}"],
        ["下载异常", str(BASELINE["download_exceptions"]), str(final_counts["download_exceptions"]), f"-{BASELINE['download_exceptions'] - final_counts['download_exceptions']}"],
        ["已下载但提取异常", str(BASELINE["downloaded_extraction_exceptions"]), str(final_counts["downloaded_extraction_exceptions"]), "0"],
        ["提取片段（非自然段／非独立观察）", f"{BASELINE['segments']:,}", f"{final_counts['segments']:,}", f"+{final_counts['segments'] - BASELINE['segments']:,}"],
    ]
    coverage_display_rows = [
        [
            row["metric"],
            row["object_scope"],
            f"{row['numerator']:,} / {row['denominator']:,}",
            fmt_percent(row["percent"]),
        ]
        for row in coverage_rows
    ]
    retry_display_rows = [
        [
            row["content_object_id"],
            row["title"],
            "已恢复" if row["recovered"] else "未解决，停止重试",
            str(row["replacement_status_code"] or "DNS/连接失败"),
            row["final_extraction_status"],
        ]
        for row in retry_rows
    ]
    decade_display_rows = [
        [
            row["period_label"],
            f"{int(row['publication_records']):,}",
            fmt_percent(float(row["record_share_percent"])),
            row["boundary_status"],
        ]
        for row in decade_plot_rows
    ]
    gap_rows = [
        [
            "国家与地区",
            "核心优先英语文本，涉及美国、欧洲、澳大利亚、新西兰；更广地域待验证试点。",
            "英国 GOV.UK 已有一个可审计的真实批次。",
            "美国、欧洲其他国家、澳大利亚、新西兰政府层均未由本批覆盖。",
            "不能把当前批次外推为英语国家政府话语；跨国比较尚不可做。",
        ],
        [
            "发布机构",
            "GOV.UK 为首要政策来源，要求按机构／类型／月份保留分母。",
            "冻结清单按 GOV.UK 当前 DEFRA 机构标签形成。",
            "不是 DEFRA 全部发布，也不是 GOV.UK 全部部门或英国政府整体。",
            "机构职能造成的基准差异尚不能与其他机构合并。",
        ],
        [
            "文档类型",
            "政策层需按文种分层，不能默认政策、议会、新闻稿、科学评估共享分母。",
            "Search API 查询类型固定为 policy_paper。",
            f"当前 Content API 类型为 policy_paper 1,019 条、guidance 1 条；议会、新闻稿等未覆盖。",
            "保留类型漂移记录；不得把本批称为 DEFRA 全文种样本。",
        ],
        [
            "1988 起点及实际观察年份",
            "目标从 1988-01 开始，但不保证连续分析覆盖。",
            f"逐年网格完整保留 1988-2026；最早观察记录为 {first_observed_year}。",
            "1988-1996 为零返回，1997 前没有观察记录；这不是历史档案完整性证明。",
            "1997-2010 仅作稀疏历史语境；不能据此识别 1988 前后变化。",
        ],
        [
            "月度／季度数量分布",
            "政策来源可考虑季度，但共同 VAR/CCF 需其他来源同步聚合。",
            "已提供年×月真实分布和年度／年代构成。",
            "未验证稳定月度密度、季节性、结构突变或与其他角色的共同窗口。",
            "本轮仅做构成描述；不提前宣称时间序列可行。",
        ],
        [
            "正文和附件可得性",
            "政策正文、附件和长报告需保留父子关系与分母。",
            f"网页 {kind_extractions['webpage']:,}/{kind_counts['webpage']:,} 提取成功；附件 {kind_extractions['attachment']:,}/{kind_counts['attachment']:,}。",
            f"仍有 {final_counts['download_exceptions']} 个下载异常和 {final_counts['downloaded_extraction_exceptions']} 个已下载提取异常；网页成功不等于附件政策全文到手。",
            "后续文本处理需按网页摘要、附件正文和附件格式分别选择。",
        ],
        [
            "历史版本与更新时间",
            "要求版本化、可追溯语料，并区分首次发布与更新。",
            f"保留 first_published_at、updated_at、retrieved_at；{int(updated_count)} 条的更新时间晚于首次发布。",
            f"最大首发—更新时间间隔为 {int(maximum_update_gap):,} 天；只保存了本次获取时可见版本及少量错误页历史，不是完整版本档案。",
            "日期分布仍按首次发布日期；当前正文可能不是首次发表时原文。",
        ],
        [
            "与新闻、公众层共同窗口",
            "初始来源为 GOV.UK、Guardian、Reddit 申请路线；共同覆盖确认后再定窗口。",
            "政府批次内部时间构成已明确。",
            "Guardian 与公众来源的可用月份、分母和权限仍未冻结。",
            "保留共同窗口未定状态，不做跨角色领先／滞后分析。",
        ],
    ]
    source_links = "\n".join(
        f"- `{object_id}`：原地址 <{item['original_url']}>；替代地址 <{item['new_url']}>；依据：{item['identity_basis']}"
        for object_id, item in overrides.items()
    )
    report = f"""# 06 批次政府语料范围、数量与覆盖率评估

生成时间：2026-09-21（Australia/Brisbane）  
冻结查询截止日：2026-09-21  
主时间字段：`first_published_at`（数据库 `documents.publication_timestamp`／其 UTC 日历日期）；`updated_at` 与获取时间仅作版本和获取证据，不替代首次发布日期。

## 结论摘要

本轮只对 9 个下载异常进行了受限处理，没有重新枚举来源、没有重下成功对象、没有对 21 个已下载提取异常做全量重处理。原地址的实际网络重试仍得到 8 个 HTTP 403 和 1 个 HTTP 200 错误页；经原发布页／机构官网核验同一文件后，9 个替代地址中恢复 5 个。最终下载成功 {final_counts['downloaded']:,}/{BASELINE['content_objects']:,}，提取成功 {final_counts['extracted']:,}/{BASELINE['content_objects']:,}；剩余 4 个下载异常与 21 个已下载提取异常继续分开报告。

当前语料的准确范围是：

> 本次冻结查询中，GOV.UK 当前 DEFRA 机构标签下、符合 Search API `policy_paper` 条件的发布记录及其关联内容。

这不等于 DEFRA 所有类型发布、英国全部政府话语、英语国家政府话语、连续完整的 1988 年以来政策档案，也不等于已筛选出的气候或升温恐惧语料。

## 1. 异常重试与前后状态

{markdown_table(['项目', '本轮前', '本轮后', '变化'], pre_post_rows)}

原链接网络重试的远端结果与基线一致。执行审计中另保留了一次受限运行环境的 DNS 失败记录（未到达远端）以及一次在写回前中断、`attempted_count=0` 的实现故障记录；二者不计为对象的远端重试。最终状态已恢复为 3,025 个对象各一条当前状态，数据库核验通过。

{markdown_table(['对象 ID', '对象标题', '最终状态', '替代地址响应', '提取状态'], retry_display_rows)}

已恢复 5 个对象：National Grid Gas、两份 OECD 报告、Thames Water、Historic England／English Heritage Trust。剩余 4 个对象为 National Grid Electricity Transmission、Portsmouth Water、Anglian Water、Birmingham Airport；前三者替代地址仍返回 403，Birmingham Airport 官方媒体域名在实际获取环境中无法解析。按任务边界停止继续重试，没有绕过访问限制。

成功获取后的 5 个对象均被识别为 PDF 并完成源文本提取，新增 {final_counts['segments'] - BASELINE['segments']:,} 个提取片段。片段是提取器的 PDF 行／块等技术单元，不是自然段数或独立观察数。

### 地址变更证据

{source_links}

逐对象状态、哈希、保存路径和证据详见 [`retry_results.csv`](retry_results.csv)；审核过的映射见 [`retry_url_overrides.json`](retry_url_overrides.json)。

## 2. 时间分布

所有 1,020 条发布记录都有可核验的 `first_published_at`；缺失日期 0 条。逐年表固定列出 1988-2026，因此零返回年份不会从图表消失。最早观察年份为 {first_observed_year}；1988-1996 没有观察记录。查询零返回只表示本次来源集合未观察到记录，不表示该年不存在政府政策。

年度峰值为 {int(peak_year_row['year'])} 年 {int(peak_year_row['publication_records'])} 条。2026 年有 {annual_values[-1]} 条，但只覆盖到 9 月 21 日。年代构成为：

{markdown_table(['年代组', '发布记录', '批次内部占比', '边界'], decade_display_rows)}

一个共享附件 `{shared_attachment[0]}` 同时关联 {shared_attachment[2]} 条父发布记录，父年份为 {shared_attachment[1]}。年度和年代 CSV 的附件字符数／片段数采用“年份内去重对象、跨父年份可重复出现”的关联口径；跨年相加不能称为唯一附件总量。附件没有可核验独立发布日期时，没有把父文档日期写成附件自身发布日期。

图表：[`年度发布记录`](annual_publication_records.png) · [`年代构成`](decade_composition.png) · [`年×月热图`](year_month_heatmap.png)。源数值见 [`annual_distribution.csv`](annual_distribution.csv)、[`decade_distribution.csv`](decade_distribution.csv)、[`year_month_counts.csv`](year_month_counts.csv)。

## 3. 当前可以计算的覆盖率

{markdown_table(['指标', '对象／记录口径', '分子 / 分母', '结果'], coverage_display_rows)}

“至少提取到一个对象”只说明发布记录存在可用文本。由于 1,020 个网页都成功提取，该指标对发布记录为 100%，但不能称为政策全文完整率：网页可能只有摘要、说明和附件链接，正文主要价值可能位于附件。

有附件的发布记录共 {attachment_total_records:,} 条，其中附件全部提取成功 {attachment_all_records:,} 条、部分成功 {attachment_partial_records:,} 条、全部未成功 {attachment_none_records:,} 条，三类互斥。配套可机读分子／分母见 [`coverage_metrics.csv`](coverage_metrics.csv)。

## 4. 当前不能计算的覆盖率

缺少独立、可靠总体分母，以下比例不计算：

- 英国政府整体覆盖率；
- DEFRA 历史政策完整率；
- proposal 所有目标国家政府语料覆盖率；
- 气候政策占比或恐惧表达占比。

年度记录占比仅是这个冻结批次内部的时间构成，不是某年政府话语覆盖率。当前 Search API 的查询类型与 Content API 当前类型也不完全一致：1,019 条当前类型为 `policy_paper`，1 条为 `guidance`（`{type_drift[0][1]}`，对象 `{type_drift[0][0]}`）；该漂移被保留，没有静默改写。

## 5. 与 proposal 原计划的差距

{markdown_table(['原计划维度', '当前证据', '已满足部分', '未覆盖部分', '对后续工作的影响'], gap_rows)}

特别需要注意版本解释：{int(updated_count)} 条记录的 `updated_at` 晚于 `first_published_at`，最长间隔 {int(maximum_update_gap):,} 天。年度分布按首次发布日期保留，但本次下载的是截止日可见内容，可能包含后来替换或更新的正文／附件，不能自动视为首次发表时的原文。

## 6. 暂定政府层使用范围

- **可直接用于后续源文本处理：** {final_counts['extracted']:,} 个当前提取成功对象，但必须保留网页／附件、格式、父发布记录与版本字段；网页可用于发布说明和摘要，不能单独代替附件全文。
- **需要先调整切分或聚合：** PDF 的行／块级单元、CSV／ODS 的行或单元格、长报告的高密度技术片段。后续应在父对象内重组，而不是把当前片段当自然段或独立观察。
- **保留但暂不纳入语言处理：** 4 个下载异常、14 个 `needs_ocr`、5 个不支持格式、2 个 `extraction_failed`。原 HTTP 200 错误页作为历史证据保留，不作为正文。

基于真实分布，建议把 **1997-2026 的全部观察记录保留为政府层来源档案**；把 1997-2010 的稀疏记录主要用于历史语境，把 2011-2025 的完整年份作为进一步评估月度／季度稳定性的候选区间，2026 单列为截止日部分年份。这是审查范围，不是“足以支持时间序列分析”的结论。新闻和公众层的可用月份、分母与权限尚未冻结，因此共同窗口继续保留为未定，不开展跨角色时序推断。

## 7. 图表契约与口径

核心结论：冻结批次的记录在 2010 年后集中，1988 起点不构成连续完整历史覆盖。结果问题是“该冻结查询在哪些年份和月份观察到多少发布记录”。图表采用单面板定量图、Python／Matplotlib、183 mm 宽；主证据是逐年和年×月数量，年代构成是汇总验证。无抽样误差条或显著性检验；`n` 是唯一 `document_id` 数。主要审稿风险是把零返回误读为政策不存在、把 2026 误读为完整年份，或把父年份关联的共享附件相加成唯一附件总量；图注和 CSV 已显式约束这些解释。
"""
    write_text(HERE / "government_corpus_coverage_report.md", report)

    decade_html_rows = "".join(
        f"<tr><td>{html.escape(str(row['period_label']))}</td><td>{int(row['publication_records']):,}</td>"
        f"<td>{float(row['record_share_percent']):.1f}%</td><td>{html.escape(str(row['boundary_status']))}</td></tr>"
        for row in decade_plot_rows
    )
    retry_html_rows = "".join(
        f"<tr><td><code>{html.escape(str(row['content_object_id']))}</code></td>"
        f"<td>{html.escape(str(row['title']))}</td>"
        f"<td><span class='status {'ok' if row['recovered'] else 'warn'}'>{'Recovered' if row['recovered'] else 'Unresolved'}</span></td>"
        f"<td>{html.escape(str(row['final_extraction_status']))}</td></tr>"
        for row in retry_rows
    )
    html_page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>06 批次政府语料覆盖评估</title>
<style>
:root{{--ink:#24343d;--muted:#60737e;--blue:#3f6278;--blue2:#86a5b7;--accent:#b07d46;--paper:#f7f8f6;--line:#dce2e5;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1120px;margin:auto;padding:38px 28px 64px}} h1{{font-size:30px;line-height:1.2;margin:0 0 8px}} h2{{font-size:21px;margin:40px 0 14px;border-bottom:1px solid var(--line);padding-bottom:7px}} p{{max-width:88ch}} .meta{{color:var(--muted)}}
.scope{{border-left:5px solid var(--blue);background:white;padding:16px 20px;margin:22px 0;font-size:18px}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:22px 0}} .card{{background:white;border:1px solid var(--line);padding:16px;border-radius:6px}} .card b{{display:block;font-size:26px;color:var(--blue)}} .card span{{color:var(--muted)}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} figure{{margin:0;background:white;border:1px solid var(--line);padding:12px}} figure.wide{{grid-column:1/-1}} img{{width:100%;height:auto;display:block}} figcaption{{color:var(--muted);font-size:13px;margin-top:8px}}
table{{border-collapse:collapse;width:100%;background:white;font-size:13px}} th,td{{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}} th{{background:#edf1f2;color:#354b57}} code{{font-size:12px}} .status{{font-weight:700}} .ok{{color:#2e6a55}} .warn{{color:#9a622e}}
.links a{{display:inline-block;margin:4px 10px 4px 0;color:var(--blue)}} .note{{background:#eef2f3;padding:14px 17px;border-radius:5px}} @media(max-width:760px){{.cards,.grid{{grid-template-columns:1fr}} .wide{{grid-column:auto}} main{{padding:24px 15px}}}}
</style></head><body><main>
<h1>06 批次政府语料范围与覆盖评估</h1><p class="meta">截止 2026-09-21 · 主日期 first_published_at · 冻结批次 1,020 条发布记录 / 3,025 个内容对象</p>
<div class="scope">本次冻结查询中，GOV.UK 当前 DEFRA 机构标签下、符合 Search API <code>policy_paper</code> 条件的发布记录及其关联内容。</div>
<div class="cards"><div class="card"><b>{final_counts['downloaded']:,}</b><span>下载成功 / 3,025</span></div><div class="card"><b>{final_counts['extracted']:,}</b><span>提取成功 / 3,025</span></div><div class="card"><b>{final_counts['download_exceptions']}</b><span>剩余下载异常</span></div><div class="card"><b>{final_counts['downloaded_extraction_exceptions']}</b><span>已下载但提取异常</span></div></div>
<p class="note">网页提取成功不等于政策全文完整。附件全部提取成功的有附件记录为 {attachment_all_records:,}/{attachment_total_records:,}；部分成功 {attachment_partial_records}；全部未成功 {attachment_none_records}。</p>
<h2>时间构成</h2><div class="grid"><figure class="wide"><img src="annual_publication_records.png" alt="1988 至 2026 年发布记录柱状图"><figcaption>2026 年截至 9 月 21 日；零值表示本冻结查询未观察到记录。</figcaption></figure><figure><img src="decade_composition.png" alt="年代构成横向柱状图"><figcaption>首尾年代均不完整。</figcaption></figure><figure><img src="year_month_heatmap.png" alt="年与月发布记录热图"><figcaption>灰色为 2026 截止日后的未覆盖月份；缺失日期 0 条。</figcaption></figure></div>
<h2>年代汇总</h2><table><thead><tr><th>年代组</th><th>发布记录</th><th>批次内占比</th><th>边界</th></tr></thead><tbody>{decade_html_rows}</tbody></table>
<h2>9 个下载异常的有限处理</h2><p>原地址真实网络重试仍为 8 个 403 与 1 个 HTTP 200 错误页。官网同一文件地址核验后恢复 5 个，剩余 4 个已停止重试。</p><table><thead><tr><th>对象</th><th>标题</th><th>结果</th><th>提取状态</th></tr></thead><tbody>{retry_html_rows}</tbody></table>
<h2>解释边界</h2><ul><li>不是 DEFRA 全部发布、英国政府整体或英语国家政府话语。</li><li>不是连续完整的 1988 年以来政策档案；最早观察记录在 {first_observed_year} 年。</li><li>不是已筛选出的气候／升温恐惧语料。</li><li>当前版本正文可能晚于首次发布日期；{int(updated_count)} 条记录后来有更新。</li><li>共同新闻—公众—政府窗口尚未确定，不能据此宣布时序分析可行。</li></ul>
<h2>文件</h2><p class="links"><a href="government_corpus_coverage_report.md">完整 Markdown 报告</a><a href="annual_distribution.csv">年度 CSV</a><a href="decade_distribution.csv">年代 CSV</a><a href="year_month_counts.csv">年×月 CSV</a><a href="coverage_metrics.csv">覆盖率 CSV</a><a href="retry_results.csv">重试结果 CSV</a><a href="final_checks.json">最终检查</a></p>
</main></body></html>"""
    write_text(HERE / "index.html", html_page)

    expected = config["expected_counts"]
    status_integrity = connection.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT content_object_id), COUNT(DISTINCT fetch_id)
        FROM acquisition_object_statuses WHERE batch_id=?
        """,
        [BATCH_ID],
    ).fetchone()
    object_integrity = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT content_object_id) FROM content_objects"
    ).fetchone()
    frozen_paths = {
        "04_database": PROJECT_ROOT / config["paths"]["frozen_database"],
        "04_manifest": PROJECT_ROOT / config["paths"]["frozen_manifest"],
        "05_database": PROJECT_ROOT / config["paths"]["source_database"],
    }
    frozen_hashes = {name: sha256_file(path) for name, path in frozen_paths.items()}
    checks = {
        "content_object_count_and_ids_stable": (
            int(object_integrity[0]) == int(expected["content_objects"])
            and int(object_integrity[1]) == int(expected["content_objects"])
        ),
        "one_current_status_and_fetch_per_object": (
            int(status_integrity[0]) == int(expected["content_objects"])
            and int(status_integrity[1]) == int(expected["content_objects"])
            and int(status_integrity[2]) == int(expected["content_objects"])
        ),
        "status_totals_align": (
            final_counts["downloaded"] + final_counts["download_exceptions"]
            == int(expected["content_objects"])
            and final_counts["extracted"]
            + final_counts["downloaded_extraction_exceptions"]
            + final_counts["download_exceptions"]
            == int(expected["content_objects"])
        ),
        "annual_records_equal_valid_date_records": (
            sum(int(row["publication_records"]) for row in year_rows)
            == len(valid_documents)
        ),
        "annual_plus_missing_equal_all_documents": (
            sum(int(row["publication_records"]) for row in year_rows)
            + len(missing_date_documents)
            == len(documents)
        ),
        "decade_totals_equal_annual_totals": (
            sum(int(row["publication_records"]) for row in decade_plot_rows)
            == sum(int(row["publication_records"]) for row in year_rows)
        ),
        "year_month_counts_equal_valid_date_records": (
            sum(
                int(row["publication_records"])
                for row in year_month_rows
                if row["window_status"]
                in {
                    "full_calendar_month_within_query_range",
                    "partial_month_to_2026-09-21",
                }
            )
            == len(valid_documents)
        ),
        "attachment_record_states_are_mutually_exclusive_and_exhaustive": (
            attachment_all_records + attachment_partial_records + attachment_none_records
            == attachment_total_records
        ),
        "frozen_04_database_unchanged": frozen_hashes["04_database"]
        == config["frozen_database_sha256"],
        "frozen_04_manifest_unchanged": frozen_hashes["04_manifest"]
        == config["frozen_manifest_sha256"],
        "frozen_05_database_unchanged": frozen_hashes["05_database"]
        == config["source_database_sha256"],
        "all_coverage_rates_have_positive_denominators": all(
            int(row["denominator"]) > 0 for row in coverage_rows
        ),
        "chart_source_rows_match_csv_rows": (
            len(year_rows) == 39 and len(decade_plot_rows) == 5 and len(year_month_rows) == 469
        ),
    }
    checks_payload = {
        "generated_at": "2026-09-21",
        "passed": all(checks.values()),
        "checks": checks,
        "final_counts": final_counts,
        "status_breakdown": [
            {
                "object_kind": row[0],
                "download_status": row[1],
                "extraction_status": row[2],
                "object_count": int(row[3]),
            }
            for row in status_rows
        ],
        "frozen_hashes": frozen_hashes,
        "expected_frozen_hashes": {
            "04_database": config["frozen_database_sha256"],
            "04_manifest": config["frozen_manifest_sha256"],
            "05_database": config["source_database_sha256"],
        },
        "shared_attachment_parent_year_note": {
            "content_object_id": shared_attachment[0],
            "parent_years": shared_attachment[1],
            "parent_record_count": int(shared_attachment[2]),
        },
    }
    write_text(
        HERE / "final_checks.json",
        json.dumps(checks_payload, ensure_ascii=False, indent=2) + "\n",
    )
    connection.close()
    if not checks_payload["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"Coverage analysis checks failed: {failed}")


if __name__ == "__main__":
    main()
