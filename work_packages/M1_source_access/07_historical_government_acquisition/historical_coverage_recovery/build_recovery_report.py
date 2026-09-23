#!/usr/bin/env python3
"""Build the final historical-coverage recovery ledgers, report and Figure 5.

This is read-only with respect to the formal 06 database.  It consumes the
bounded recovery evidence and the single post-ingestion distribution refresh.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/fear_temperature_recovery_mplconfig")

import duckdb
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

SKILL_SCRIPTS = Path("/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "work_packages/M1_source_access/07_historical_government_acquisition"
RECOVERY = WORK / "historical_coverage_recovery"
REPORTS = RECOVERY / "reports"
DIST = REPORTS / "final_distribution_coverage"
FIGURES = REPORTS / "figures"
QA = REPORTS / "qa"
DB = ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
START = pd.Period("1988-01", "M")
END = pd.Period("2026-09", "M")
MONTHS = pd.period_range(START, END, freq="M")
SERIES = ["policy_document", "ministerial_written_answer", "ministerial_written_statement"]
SERIES_LABELS = {
    "policy_document": "Policy records",
    "ministerial_written_answer": "Written answers",
    "ministerial_written_statement": "Written statements",
}
STATUS_ORDER = ["blocked", "unknown", "unrequested", "partial", "complete", "confirmed_zero"]
STATUS_LABELS = {
    "blocked": "Access / parsing blocked",
    "unknown": "Enumeration incomplete / denominator unknown",
    "unrequested": "Known target not requested",
    "partial": "Partial coverage / bounded exclusion",
    "complete": "Verified route complete for known scope",
    "confirmed_zero": "Verified enumeration; zero in-scope records",
}
STATUS_COLORS = {
    "blocked": "#A6423A",
    "unknown": "#5F6B75",
    "unrequested": "#806493",
    "partial": "#D39A4A",
    "complete": "#2F766D",
    "confirmed_zero": "#C5DCD7",
}
STATUS_PRIORITY = {"blocked": 0, "unknown": 1, "unrequested": 2, "partial": 3, "complete": 4, "confirmed_zero": 5}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def intv(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def db_snapshot() -> dict[str, Any]:
    with duckdb.connect(str(DB), read_only=True) as con:
        return {
            "snapshot_at": utc_now(),
            "documents": int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]),
            "policy_records": int(con.execute("SELECT COUNT(*) FROM documents d JOIN sources s USING(source_id) WHERE s.source_name LIKE 'GOV.UK%'").fetchone()[0]),
            "written_answers": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_answer'").fetchone()[0]),
            "written_statements": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='ministerial_written_statement'").fetchone()[0]),
            "text_segments": int(con.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0]),
            "recovery_batch_documents": int(con.execute("SELECT COUNT(DISTINCT document_id) FROM enumeration_records WHERE batch_id IN ('commons_parlparse_targeted_gap_recovery_20260922_v1','govuk_historical_policy_targeted_recovery_20260922_v1')").fetchone()[0]),
            "recovery_written_answers": int(con.execute("SELECT COUNT(*) FROM documents d JOIN enumeration_records e USING(document_id) WHERE e.batch_id='commons_parlparse_targeted_gap_recovery_20260922_v1' AND d.content_type='ministerial_written_answer'").fetchone()[0]),
            "recovery_written_statements": int(con.execute("SELECT COUNT(*) FROM documents d JOIN enumeration_records e USING(document_id) WHERE e.batch_id='commons_parlparse_targeted_gap_recovery_20260922_v1' AND d.content_type='ministerial_written_statement'").fetchone()[0]),
            "recovery_policy_segments": int(con.execute("SELECT COUNT(*) FROM text_segments WHERE extraction_run_id=(SELECT extraction_run_id FROM extraction_runs WHERE batch_id='govuk_historical_policy_targeted_recovery_20260922_v1')").fetchone()[0]),
            "recovery_policy_text_pages": int(con.execute("SELECT COUNT(DISTINCT regexp_extract(locator, 'page=([0-9]+)', 1)) FROM text_segments WHERE extraction_run_id=(SELECT extraction_run_id FROM extraction_runs WHERE batch_id='govuk_historical_policy_targeted_recovery_20260922_v1')").fetchone()[0]),
        }


def target_date_state(
    target: dict[str, str],
    kind: str,
    remote: list[dict[str, str]],
    acquisition: list[dict[str, str]],
    parse_failures: list[dict[str, str]],
) -> str:
    date_value = target["date"]
    files = [row for row in remote if row.get("date") == date_value and row.get("kind") == kind]
    if not files:
        return "unknown"
    statuses = [row for row in acquisition if row.get("date") == date_value and row.get("kind") == kind]
    if any(row.get("download_status") == "unrequested_host_stop" for row in statuses):
        return "unrequested"
    if len(statuses) < len(files):
        return "unrequested"
    if any(row.get("download_status") == "failed" for row in statuses):
        return "blocked"
    if any(row.get("date") == date_value and row.get("kind") == kind for row in parse_failures):
        return "partial"
    if statuses and all(row.get("download_status") == "success" for row in statuses):
        return "complete"
    return "unknown"


def aggregate_status(values: list[str]) -> str:
    if not values:
        return "unknown"
    if all(value == "confirmed_zero" for value in values):
        return "confirmed_zero"
    non_zero = [value for value in values if value != "confirmed_zero"]
    if not non_zero:
        return "confirmed_zero"
    return min(non_zero, key=lambda value: STATUS_PRIORITY[value])


def build_coverage_tables() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    distribution = read_csv(DIST / "year_month_distribution.csv")
    counts = {(row["series"], row["year_month"]): intv(row["record_count"]) for row in distribution}
    targets = read_csv(RECOVERY / "manifests/parlparse_target_dates.csv")
    remote = read_csv(RECOVERY / "manifests/parlparse_remote_file_manifest.csv")
    acquisition = read_csv(RECOVERY / "evidence/parlparse_acquisition_status.csv")
    parse_failures = read_csv(RECOVERY / "evidence/parlparse_parse_failures.csv")

    target_states: dict[tuple[str, str], list[str]] = defaultdict(list)
    target_units: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for target in targets:
        month = target["date"][:7]
        reasons = set(target.get("reasons", "").split(";"))
        if target.get("wrans") == "True":
            state = target_date_state(target, "wrans", remote, acquisition, parse_failures)
            target_states[("ministerial_written_answer", month)].append(state)
            target_units[("ministerial_written_answer", month)][state] += 1
        if target.get("wms") == "True" and "2004_q4_commons_seam" in reasons:
            state = target_date_state(target, "wms", remote, acquisition, parse_failures)
            target_states[("ministerial_written_statement", month)].append(state)
            target_units[("ministerial_written_statement", month)][state] += 1

    monthly: list[dict[str, Any]] = []
    for series in SERIES:
        for period in MONTHS:
            month = str(period)
            note = ""
            if series == "policy_document":
                if period.year <= 2009:
                    status = "blocked"
                    note = "Predecessor-department population remains unknown; normal UKGWA route was access-blocked. Exact recovered items do not close the denominator."
                else:
                    status = "complete"
                    note = "Complete only for the frozen current-DEFRA Search/API route, not all UK government policy."
            elif series == "ministerial_written_answer":
                status = "complete"
                note = "Verified within the applicable bounded source route."
                if month == "1988-01":
                    status, note = "partial", "Study starts 1988-01-01; first observed Commons sitting is 1988-01-11."
                if month == "1991-12":
                    status, note = "partial", "One malformed Historic Hansard item remains excluded/unresolved."
                if pd.Period("2004-10", "M") <= period <= pd.Period("2004-12", "M"):
                    status = aggregate_status(target_states.get((series, month), []))
                    note = "Bounded ParlParse/TWFY seam target dates; no-file dates remain unknown rather than zero."
                if month == "2006-07":
                    status, note = "partial", "Asda target excluded because text/department attribution cannot be separated reliably."
                if pd.Period("2010-05", "M") <= period <= pd.Period("2014-09", "M") and target_states.get((series, month)):
                    status = aggregate_status(target_states[(series, month)])
                    note = "Known failed-index/failed-page/unrequested-page dates checked against the bounded XML mirror."
                if month == "2014-09" and status == "complete":
                    status, note = "partial", "Month crosses the historical/modern source boundary on 2014-09-12."
                if month == "2026-09":
                    status, note = "partial", "Partial cutoff month through 2026-09-21."
            else:
                status = "complete"
                note = "Verified within the applicable bounded statement source route."
                if month == "1988-01":
                    status, note = "partial", "Study starts 1988-01-01; first observed Commons sitting is 1988-01-11."
                if pd.Period("2004-10", "M") <= period <= pd.Period("2004-12", "M"):
                    status = aggregate_status(target_states.get((series, month), []))
                    note = "Bounded WMS mirror seam; no-file sitting dates remain unknown rather than zero."
                if month == "2010-09":
                    status, note = "partial", "Unresolved cross-date statement container excluded; identified child statements retained."
                if month == "2014-09" and status == "complete":
                    status, note = "partial", "Month crosses the historical/modern source boundary on 2014-09-12."
                if month == "2026-09":
                    status, note = "partial", "Partial cutoff month through 2026-09-21."
            record_count = counts.get((series, month), 0)
            if status == "complete" and record_count == 0:
                status = "confirmed_zero"
                note = "Applicable source route enumerated; no in-scope record observed in this month."
            units = target_units.get((series, month), Counter())
            monthly.append(
                {
                    "series": series,
                    "series_label": SERIES_LABELS[series],
                    "year_month": month,
                    "year": period.year,
                    "month": period.month,
                    "status": status,
                    "status_label": STATUS_LABELS[status],
                    "record_count": record_count,
                    "target_dates_complete": units["complete"],
                    "target_dates_unknown": units["unknown"],
                    "target_dates_blocked": units["blocked"],
                    "target_dates_unrequested": units["unrequested"],
                    "target_dates_partial": units["partial"],
                    "note": note,
                }
            )

    quarter_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in monthly:
        quarter = str(pd.Period(row["year_month"], "M").asfreq("Q"))
        quarter_groups[(row["series"], quarter)].append(row)
    quarterly: list[dict[str, Any]] = []
    for (series, quarter), rows in sorted(quarter_groups.items()):
        status = aggregate_status([row["status"] for row in rows])
        quarterly.append(
            {
                "series": series,
                "series_label": SERIES_LABELS[series],
                "year_quarter": quarter,
                "year": int(quarter[:4]),
                "quarter": int(quarter[-1]),
                "status": status,
                "status_label": STATUS_LABELS[status],
                "record_count": sum(row["record_count"] for row in rows),
                "months_in_period": len(rows),
                "aggregation_rule": "worst evidence state; confirmed zero only when all months are confirmed zero",
            }
        )
    date_rows: list[dict[str, Any]] = []
    for target in targets:
        for kind, series in [("wrans", "ministerial_written_answer"), ("wms", "ministerial_written_statement")]:
            if target.get(kind) != "True":
                continue
            state = target_date_state(target, kind, remote, acquisition, parse_failures)
            date_rows.append(
                {
                    "date": target["date"],
                    "series": series,
                    "reasons": target["reasons"],
                    "state": state,
                    "state_label": STATUS_LABELS[state],
                    "enumerated_files": sum(row.get("date") == target["date"] and row.get("kind") == kind for row in remote),
                    "acquired_files": sum(row.get("date") == target["date"] and row.get("kind") == kind and row.get("download_status") == "success" for row in acquisition),
                }
            )
    return monthly, quarterly, date_rows


def configure_plotting() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )


def plot_coverage(monthly: list[dict[str, Any]], quarterly: list[dict[str, Any]]) -> None:
    configure_plotting()
    FIGURES.mkdir(parents=True, exist_ok=True)
    frame_m = pd.DataFrame(monthly)
    frame_q = pd.DataFrame(quarterly)
    colors = [STATUS_COLORS[key] for key in STATUS_ORDER]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(-0.5, len(colors) + 0.5), len(colors))
    code = {key: index for index, key in enumerate(STATUS_ORDER)}
    years = list(range(1988, 2027))
    fig, axes = plt.subplots(3, 2, figsize=(7.2, 9.4), gridspec_kw={"width_ratios": [0.78, 1.45], "hspace": 0.29, "wspace": 0.18})
    letters = iter("abcdef")
    for row_index, series in enumerate(SERIES):
        q = frame_q[frame_q.series == series]
        qgrid = np.full((len(years), 4), np.nan)
        for value in q.itertuples():
            qgrid[years.index(int(value.year)), int(value.quarter) - 1] = code[value.status]
        m = frame_m[frame_m.series == series]
        mgrid = np.full((len(years), 12), np.nan)
        for value in m.itertuples():
            mgrid[years.index(int(value.year)), int(value.month) - 1] = code[value.status]
        for col_index, (axis, grid, labels, title) in enumerate(
            [
                (axes[row_index, 0], qgrid, ["Q1", "Q2", "Q3", "Q4"], "quarters"),
                (axes[row_index, 1], mgrid, ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"], "months"),
            ]
        ):
            axis.imshow(grid, aspect="auto", interpolation="nearest", cmap=cmap, norm=norm, origin="upper")
            axis.set_xticks(range(len(labels)), labels)
            tick_years = [1988, 1995, 2000, 2005, 2010, 2015, 2020, 2026]
            axis.set_yticks([years.index(value) for value in tick_years], [str(value) for value in tick_years] if col_index == 0 else [])
            axis.set_title(f"{next(letters)}  {SERIES_LABELS[series]} · {title}", loc="left", fontweight="bold")
            axis.tick_params(length=0)
            for spine in axis.spines.values():
                spine.set_color("#9CA7AD")
                spine.set_linewidth(0.5)
    legend = [Patch(facecolor=STATUS_COLORS[key], edgecolor="none", label=STATUS_LABELS[key]) for key in STATUS_ORDER]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.014), fontsize=6.7, columnspacing=1.5)
    fig.suptitle("Government corpus coverage over time", x=0.07, y=0.99, ha="left", fontsize=13, fontweight="bold", color="#20303A")
    fig.text(0.07, 0.955, "1988-01 to 2026-09-21 · evidence state, not document volume or UK-government-wide coverage", ha="left", fontsize=7.5, color="#4F5D63")
    fig.text(0.07, 0.087, "Quarter status uses the worst monthly evidence state; 2026 Q3 and September are partial at the cutoff.\nEarly-policy archive access remains blocked and its population denominator is unknown.", ha="left", va="top", fontsize=6.2, linespacing=1.25, color="#4F5D63")
    fig.subplots_adjust(top=0.925, bottom=0.135, left=0.07, right=0.99)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        axes=list(axes.flat),
        panel_ids=list("abcdef"),
        row_groups=[["a", "b"], ["c", "d"], ["e", "f"]],
        column_groups=[["a", "c", "e"], ["b", "d", "f"]],
        json_out=str(QA / "05_government_corpus_coverage_over_time.alignment.json"),
        overlay_svg=str(QA / "05_government_corpus_coverage_over_time.alignment.svg"),
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=False,
        strict=True,
    )
    stem = FIGURES / "05_government_corpus_coverage_over_time"
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    fig.savefig(stem.with_suffix(".svg"))
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


def build_progress(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    enumeration = read_json(REPORTS / "mirror_enumeration_summary.json")
    acquisition = read_json(REPORTS / "mirror_acquisition_summary.json")
    parsed = read_json(REPORTS / "parlparse_parse_match_summary.json")
    policy = read_json(REPORTS / "early_policy_acquisition_summary.json")
    ingestion = read_json(REPORTS / "incremental_ingestion_summary.json")
    reconciliation = read_json(REPORTS / "incremental_reconciliation.json")
    committed = sum(intv(row.get("new_documents")) for row in read_csv(REPORTS / "incremental_commit_chunks.csv"))
    return [
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Frozen target dates", "value": enumeration.get("target_dates", 0), "unit": "date partition", "denominator": enumeration.get("target_dates", 0), "note": "Distinct from files and records."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Dates with enumerated files", "value": enumeration.get("dates_with_files", 0), "unit": "date partition", "denominator": enumeration.get("target_dates", 0), "note": "No-file dates remain unknown, not confirmed zero."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Frozen files", "value": acquisition.get("frozen_files", 0), "unit": "XML file", "denominator": acquisition.get("frozen_files", 0), "note": "wrans and bounded 2004-Q4 wms files."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Original files acquired", "value": acquisition.get("acquired", 0), "unit": "XML file", "denominator": acquisition.get("frozen_files", 0), "note": "Actual HTTP request metadata retained per file."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Files failed", "value": acquisition.get("failed", 0), "unit": "XML file", "denominator": acquisition.get("frozen_files", 0), "note": "Not converted to document counts."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Files unrequested after host stop", "value": acquisition.get("unrequested_after_stop", 0), "unit": "XML file", "denominator": acquisition.get("frozen_files", 0), "note": "Separate from download failure."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "In-scope derived records parsed", "value": parsed.get("parsed_in_scope_records", 0), "unit": "derived record", "denominator": "n/a", "note": "Question/context retained but not counted as government response."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Already present", "value": parsed.get("already_present", 0), "unit": "derived record", "denominator": parsed.get("parsed_in_scope_records", 0), "note": "Matched to formal 06 records; not reinserted."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "New stable identities", "value": parsed.get("new_recovered_identity", 0), "unit": "derived record", "denominator": parsed.get("parsed_in_scope_records", 0), "note": "Eligible for formal incremental insertion."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Written answers formally committed", "value": snapshot["recovery_written_answers"], "unit": "ministerial written answer", "denominator": parsed.get("new_recovered_identity", 0), "note": "Question/context segments are retained but not counted as government responses."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Written statements formally committed", "value": snapshot["recovery_written_statements"], "unit": "ministerial written statement", "denominator": parsed.get("new_recovered_identity", 0), "note": "Independent statement series."},
        {"source": "ParlParse/TWFY bounded mirror", "metric": "Duplicate mirror representations", "value": parsed.get("duplicate_within_mirror_files", 0), "unit": "derived record", "denominator": parsed.get("parsed_in_scope_records", 0), "note": "Not independent documents."},
        {"source": "Official GOV.UK command paper", "metric": "Exact policy targets acquired", "value": policy.get("acquired", 0), "unit": "policy publication", "denominator": policy.get("targets", 1), "note": "Cm 2428 only; not a historical-population denominator."},
        {"source": "Official GOV.UK command paper", "metric": "Extracted text lines", "value": snapshot["recovery_policy_segments"], "unit": "source line segment", "denominator": 194, "note": "188 pages contain text; six no-text pages were visually verified as blank or image-only separators."},
        {"source": "Formal 06 database", "metric": "New documents committed", "value": committed, "unit": "document", "denominator": ingestion.get("parliament_candidates_new", 0) + policy.get("acquired", 0), "note": "Only successful COMMIT deltas count."},
        {"source": "Formal 06 database", "metric": "Recovery batch documents present", "value": snapshot["recovery_batch_documents"], "unit": "document", "denominator": committed, "note": "Post-commit read-only reconciliation."},
        {"source": "Formal 06 database", "metric": "Duplicate source/external-id groups", "value": reconciliation.get("source_external_duplicate_groups", 0), "unit": "duplicate group", "denominator": "n/a", "note": "Must remain zero."},
    ]


def pct(value: int, denominator: int) -> str:
    return "n/a" if not denominator else f"{100 * value / denominator:.1f}%"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(map(clean, headers)) + " |", "|" + "|".join(["---"] * len(headers)) + "|", *["| " + " | ".join(clean(value) for value in row) + " |" for row in rows]])


def build_report(snapshot: dict[str, Any], monthly: list[dict[str, Any]], quarterly: list[dict[str, Any]], date_rows: list[dict[str, Any]], progress: list[dict[str, Any]]) -> str:
    bootstrap = read_json(REPORTS / "bootstrap_summary.json")
    enumeration = read_json(REPORTS / "mirror_enumeration_summary.json")
    acquisition = read_json(REPORTS / "mirror_acquisition_summary.json")
    parsed = read_json(REPORTS / "parlparse_parse_match_summary.json")
    policy = read_json(REPORTS / "early_policy_acquisition_summary.json")
    ingestion = read_json(REPORTS / "incremental_ingestion_summary.json")
    reconciliation = read_json(REPORTS / "incremental_reconciliation.json")
    exclusions = read_csv(RECOVERY / "exclusion_ledger.csv")
    date_enum = read_csv(RECOVERY / "evidence/parlparse_target_date_enumeration.csv")
    no_file = [row for row in date_enum if row.get("mirror_date_status") == "no_matching_mirror_file"]
    unresolved_date_units = [row for row in date_rows if row["state"] != "complete"]
    unresolved_by_series = Counter(row["series"] for row in unresolved_date_units)
    commits = read_csv(REPORTS / "incremental_commit_chunks.csv")
    new_docs = sum(intv(row.get("new_documents")) for row in commits)
    parliament_new = sum(intv(row.get("new_documents")) for row in commits if row.get("series") == "parliament")
    policy_new = sum(intv(row.get("new_documents")) for row in commits if row.get("series") == "policy")
    after = ingestion.get("after", {})
    before = ingestion.get("before", {})
    added_segments = intv(ingestion.get("added", {}).get("text_segments"))
    qcounts = Counter(row["status"] for row in quarterly)
    progress_table = markdown_table(
        ["Source", "Metric", "Value", "Unit", "Denominator / boundary"],
        [[row["source"], row["metric"], f"{intv(row['value']):,}", row["unit"], row["denominator"]] for row in progress],
    )
    exclusion_table = markdown_table(
        ["Target", "Disposition", "Reason"],
        [[row["target_id"], row["disposition"], row["reason"]] for row in exclusions],
    )
    no_file_dates = ", ".join(row["date"] for row in no_file) or "none"
    return f"""# Historical coverage recovery — final report

Snapshot: **{snapshot['snapshot_at']}**. This round reused the formal 06 database and performed only bounded historical recovery. No proposal, cleaning, vectors or model analysis were changed.

## Outcome

- Formal database moved from **{intv(before.get('documents')):,}** to **{intv(after.get('documents')):,}** documents: **{new_docs:,}** genuine additions after successful commits (**{snapshot['recovery_written_answers']:,}** written answers, **{snapshot['recovery_written_statements']:,}** written statements and **{policy_new:,}** policy record).
- Text segments increased by **{added_segments:,}**. Final totals are **{snapshot['documents']:,} documents** and **{snapshot['text_segments']:,} unique text segments**.
- The mirror route froze **{enumeration.get('target_dates', 0):,} date partitions** and **{acquisition.get('frozen_files', 0):,} XML files**; **{acquisition.get('acquired', 0):,}** files were acquired, **{acquisition.get('failed', 0):,}** failed, and **{acquisition.get('unrequested_after_stop', 0):,}** remained unrequested after host stop.
- It parsed **{parsed.get('parsed_in_scope_records', 0):,}** in-scope records: **{parsed.get('already_present', 0):,}** already existed, **{parsed.get('new_recovered_identity', 0):,}** were new stable identities, and **{parsed.get('duplicate_within_mirror_files', 0):,}** were duplicate mirror representations.
- One exact early policy was recovered: *Biodiversity: the UK action plan* (25 January 1994, Cm 2428, ISBN 0101242824). Its official 194-page PDF is retained and yielded **{snapshot['recovery_policy_segments']:,}** source-line segments across **{snapshot['recovery_policy_text_pages']:,}** text-bearing pages. The six no-text pages were visually verified as two blank pages and four image-only globe separators, so they do not hide policy prose. This one item does **not** make the 1988–2009 policy population complete.
- Reconciliation passed: **{reconciliation.get('passed', False)}**; duplicate `(source_id, external_id)` groups: **{reconciliation.get('source_external_duplicate_groups', 'n/a')}**; excluded targets inserted by this recovery: **{reconciliation.get('excluded_records_inserted_by_recovery', 'n/a')}**.

## Source and unit ledger

{progress_table}

Files, dates, pages and derived records are deliberately not added together. A no-file date has an unknown record denominator, not a zero document count.

## What changed in the gaps

- **2004-10-05 to 2004-12-31 Commons seam:** 43 previously identified sitting dates were checked against separate `wrans`/`wms` mirror holdings. Recovered records are reported by genre in `parlparse_record_manifest.csv`; months with a missing expected mirror file remain unknown in the fifth figure.
- **2010-05-01 to 2014-09-11 answers:** the original 20 failed date indexes, 225 failed pages and 212 unrequested pages remain distinct units. Their union produced a bounded date set; successful XML retrieval repairs known date partitions, while dates without a matching mirror file remain unresolved.
- **Named 2005–2010 anomalies:** Companies House was recovered under the exact BERR title/identity recorded in the identity ledger. Asda is excluded because its saved evidence cannot support reliable text/department attribution.
- **Early policy:** the verified Cm 2428 recovery improves actual 1994 text availability, but normal UKGWA access was blocked and predecessor-department catalogue coverage remains unknown. No broad completeness claim is made.

Mirror target dates with no file of either requested kind (**{len(no_file):,} date partitions**): {no_file_dates}. At the more precise date × genre level, **{len(unresolved_date_units):,} target units** remain non-complete (**{unresolved_by_series['ministerial_written_answer']:,} answer units; {unresolved_by_series['ministerial_written_statement']:,} statement units**). These are not document counts.

## Explicit exclusions

{exclusion_table}

These **{len(exclusions)} evidence rows** are retained but not counted as recovered. Two Asda evidence identifiers describe the same attribution problem; they are not converted into two missing documents. The unresolved statement container is not ingested as one statement; identified child statements remain separate.

## Coverage over time

![Government corpus coverage over time](figures/05_government_corpus_coverage_over_time.png)

`monthly_coverage_status.csv` keeps every month from 1988-01 through the 2026-09-21 cutoff. `quarterly_coverage_status.csv` applies a documented worst-evidence-state rule; its status counts are: {', '.join(f'{STATUS_LABELS[key]} {qcounts[key]:,}' for key in STATUS_ORDER)}. These are coverage-state partitions, not document counts or coverage percentages.

- **Policy records:** 1988–2009 stays blocked/unknown at the population level despite the exact 1994 recovery. From 2010 onward, “complete” means complete only for the frozen current-DEFRA Search/API route.
- **Written answers:** recovered mirror records close only the target dates with a complete file/parse chain. Historic source boundaries, the Asda exclusion and the 2026 cutoff remain visible.
- **Written statements:** the 2004 seam is independently evaluated from `wms` holdings. The unresolved 2010-09 container remains excluded, and the 2014-09 source transition is marked partial.

## Refreshed distribution

The four distribution figures and CSVs were refreshed once after the final commit in `reports/final_distribution_coverage/`:

1. [Annual distribution](final_distribution_coverage/figures/01_annual_distribution.png)
2. [Year × month distribution](final_distribution_coverage/figures/02_year_month_heatmaps.png)
3. [Source × time coverage status](final_distribution_coverage/figures/03_collection_coverage_status.png)
4. [Department annual composition](final_distribution_coverage/figures/04_department_annual_composition.png)

The database now contains **{snapshot['policy_records']:,} policy-source records**, **{snapshot['written_answers']:,} ministerial written answers**, and **{snapshot['written_statements']:,} ministerial written statements**. These are heterogeneous series and are not summed as a homogeneous policy count.

## Remaining bounded gaps

1. Predecessor-department policy coverage for 1988–2009 still lacks an independent, reliable population denominator. The exact recovered item and catalogue evidence cannot substitute for complete enumeration.
2. **{len(unresolved_date_units):,}** date × genre target units remain non-complete; their record count remains unknown. Download failures (**{acquisition.get('failed', 0):,} files**), unrequested-after-stop (**{acquisition.get('unrequested_after_stop', 0):,} files**) and parse failures (**{parsed.get('source_files_parse_failed', 0):,} files**) are separate.
3. Ambiguous mixed records remain excluded. This preserves the denominator and provenance rather than manufacturing successful recovery.

The present corpus can proceed to source-aware cleaning only for the verified subsets. It still cannot support a claim of continuous, complete UK-government coverage from 1988 to 2026.
"""


def build_html(snapshot: dict[str, Any], report: str) -> str:
    cards = "".join(
        f"<div class='card'><span>{label}</span><strong>{snapshot[key]:,}</strong></div>"
        for key, label in [("policy_records", "Policy records"), ("written_answers", "Written answers"), ("written_statements", "Written statements"), ("text_segments", "Text segments")]
    )
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Historical coverage recovery</title><style>
body{{font:15px/1.55 system-ui,-apple-system,sans-serif;color:#20303a;background:#f3f5f3;margin:0}}main{{max-width:1120px;margin:auto;padding:28px}}h1{{font-size:28px;margin-bottom:4px}}h2{{margin-top:32px;border-bottom:1px solid #ccd3d4;padding-bottom:5px}}.meta{{color:#5d6a70}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}}.card{{background:white;border:1px solid #d8dddd;padding:14px;border-radius:4px}}.card span{{display:block;color:#5d6a70}}.card strong{{font-size:25px;color:#24495f}}.warn{{background:#fff;border-left:4px solid #a6423a;padding:12px}}img{{width:100%;background:white;border:1px solid #d8dddd;margin:8px 0 18px}}a{{color:#24495f}}li{{margin:.35em 0}}@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}}main{{padding:16px}}}}</style></head><body><main>
<h1>Historical coverage recovery</h1><p class='meta'>Formal 06 database · through 2026-09-21 · generated {html.escape(snapshot['snapshot_at'])}</p><div class='cards'>{cards}</div>
<p class='warn'>Coverage states are evidence states, not document volume or UK-government-wide coverage percentages. Unknown and blocked periods are not plotted as zero.</p>
<h2>Government corpus coverage over time</h2><img src='figures/05_government_corpus_coverage_over_time.svg' alt='Coverage status by policy, written answers and written statements'>
<h2>Refreshed distribution</h2><img src='final_distribution_coverage/figures/01_annual_distribution.svg' alt='Annual distribution'><img src='final_distribution_coverage/figures/02_year_month_heatmaps.svg' alt='Year month distribution'><img src='final_distribution_coverage/figures/03_collection_coverage_status.svg' alt='Source coverage status'><img src='final_distribution_coverage/figures/04_department_annual_composition.svg' alt='Department composition'>
<h2>Evidence</h2><ul><li><a href='../historical_gap_register.csv'>Historical gap register</a></li><li><a href='../alternative_source_register.csv'>Alternative-source register</a></li><li><a href='../exclusion_ledger.csv'>Exclusion ledger</a></li><li><a href='recovery_progress_by_source.csv'>Recovery progress by source</a></li><li><a href='monthly_coverage_status.csv'>Monthly coverage status</a></li><li><a href='quarterly_coverage_status.csv'>Quarterly coverage status</a></li><li><a href='historical_coverage_recovery_report.md'>Full Markdown report</a></li></ul>
</main></body></html>"""


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    snapshot = db_snapshot()
    monthly, quarterly, date_rows = build_coverage_tables()
    progress = build_progress(snapshot)
    progress.extend(
        [
            {"source": "ParlParse/TWFY bounded mirror", "metric": "Target date × genre units complete", "value": sum(row["state"] == "complete" for row in date_rows), "unit": "date × genre", "denominator": len(date_rows), "note": "A unit is complete only when every enumerated file was acquired and parsed."},
            {"source": "ParlParse/TWFY bounded mirror", "metric": "Target date × genre units non-complete", "value": sum(row["state"] != "complete" for row in date_rows), "unit": "date × genre", "denominator": len(date_rows), "note": "Unknown, blocked, unrequested and partial remain distinct in the date ledger."},
        ]
    )
    write_csv(REPORTS / "monthly_coverage_status.csv", monthly)
    write_csv(REPORTS / "quarterly_coverage_status.csv", quarterly)
    write_csv(REPORTS / "target_date_coverage_outcomes.csv", date_rows)
    write_csv(REPORTS / "recovery_progress_by_source.csv", progress)
    plot_coverage(monthly, quarterly)
    report = build_report(snapshot, monthly, quarterly, date_rows, progress)
    (REPORTS / "historical_coverage_recovery_report.md").write_text(report, encoding="utf-8")
    (REPORTS / "index.html").write_text(build_html(snapshot, report), encoding="utf-8")
    qa = {
        "generated_at": utc_now(),
        "monthly_rows": len(monthly),
        "monthly_expected": len(MONTHS) * len(SERIES),
        "quarterly_rows": len(quarterly),
        "monthly_unique_keys": len({(row['series'], row['year_month']) for row in monthly}),
        "quarterly_unique_keys": len({(row['series'], row['year_quarter']) for row in quarterly}),
        "status_values": sorted({row['status'] for row in monthly}),
        "database_read_only": True,
        "figure_files_exist": all((FIGURES / f"05_government_corpus_coverage_over_time.{suffix}").exists() for suffix in ["png", "svg", "pdf", "tiff"]),
    }
    qa["passed"] = qa["monthly_rows"] == qa["monthly_expected"] == qa["monthly_unique_keys"] and qa["figure_files_exist"]
    write_json(QA / "recovery_report_preflight.json", qa)
    contract = """# Figure 5 contract\n\nCore conclusion: evidence coverage differs across policy, written-answer and written-statement series; unknown, blocked, unrequested, partial and confirmed-zero periods are not interchangeable.\n\nResults-level question: Which months and quarters have a verified source chain, and where do bounded gaps remain?\n\nArchetype: aligned categorical year-by-quarter and year-by-month matrices.\n\nTarget output: 183 mm academic report figure.\n\nBackend: Python/matplotlib.\n\nPanels: a/b policy quarterly/monthly; c/d answers quarterly/monthly; e/f statements quarterly/monthly.\n\nAggregation: quarter takes the worst monthly evidence state; confirmed zero requires every included month to be confirmed zero.\n\nReviewer risk: states describe the approved source routes, not all UK government material, and never use document volume as a coverage percentage.\n"""
    (QA / "figure_05_contract.md").write_text(contract, encoding="utf-8")
    manifest = []
    for path in sorted(REPORTS.rglob("*")):
        if path.is_file() and path.name != "delivery_manifest.csv":
            manifest.append({"path": str(path.relative_to(REPORTS)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(REPORTS / "delivery_manifest.csv", manifest)
    write_json(REPORTS / "recovery_report_summary.json", {"snapshot": snapshot, "qa": qa, "deliverables": len(manifest)})
    print(json.dumps({"snapshot": snapshot, "qa": qa, "deliverables": len(manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
