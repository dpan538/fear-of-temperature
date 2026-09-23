#!/usr/bin/env python3
"""Read-only post-acquisition distribution and coverage assessment.

The script reads the existing 06 DuckDB and frozen 07 manifests.  It never
opens the database in write mode and writes only to a new report directory.
"""

from __future__ import annotations

import csv
import hashlib
import html as html_lib
import json
import os
import sys
import textwrap
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/fear_temperature_mplconfig")

import duckdb
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap, LogNorm
from matplotlib.patches import Patch


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
MANIFESTS = HERE / "manifests"
REPAIR = HERE / "targeted_gap_repair"
RECOVERY = HERE / "historical_coverage_recovery"
OUT = Path(
    os.environ.get(
        "GOVERNMENT_COVERAGE_OUTPUT_DIR",
        str(HERE / "reports" / "post_acquisition_distribution_coverage"),
    )
).resolve()
FIGURES = OUT / "figures"
QA = OUT / "qa"
DB = PROJECT_ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
SKILL_SCRIPTS = Path("/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402


START = pd.Timestamp("1988-01-01")
CUTOFF = pd.Timestamp("2026-09-21")
MONTHS = pd.period_range(START, CUTOFF, freq="M")
YEARS = list(range(1988, 2027))
SERIES = ["policy_document", "ministerial_written_answer", "ministerial_written_statement"]
SERIES_LABELS = {
    "policy_document": "Policy-source publication records",
    "ministerial_written_answer": "Ministerial written answers",
    "ministerial_written_statement": "Ministerial written statements",
}
SERIES_SHORT = {
    "policy_document": "Policy records",
    "ministerial_written_answer": "Written answers",
    "ministerial_written_statement": "Written statements",
}
SERIES_COLORS = {
    "policy_document": "#24495F",
    "ministerial_written_answer": "#C57A43",
    "ministerial_written_statement": "#6F7D4C",
}
EXPECTED_BASELINE = {
    "all_documents": 239_586,
    "policy_document": 1_054,
    "ministerial_written_answer": 235_824,
    "ministerial_written_statement": 2_708,
    "text_segments": 3_623_437,
}
if os.environ.get("GOVERNMENT_COVERAGE_EXPECTED_BASELINE_JSON"):
    EXPECTED_BASELINE.update(
        {
            key: int(value)
            for key, value in json.loads(
                os.environ["GOVERNMENT_COVERAGE_EXPECTED_BASELINE_JSON"]
            ).items()
        }
    )
STATUS_ORDER = [
    "source_not_supported",
    "not_requested",
    "enumeration_incomplete",
    "complete_with_failures",
    "complete",
    "confirmed_zero",
]
STATUS_LABELS = {
    "source_not_supported": "Source not supported for period",
    "not_requested": "Known target not requested",
    "enumeration_incomplete": "Enumeration/index incomplete",
    "complete_with_failures": "Enumeration complete; acquisition/text failures",
    "complete": "Enumerated; all known targets processed",
    "confirmed_zero": "Enumeration complete; zero in-scope records",
}
STATUS_COLORS = {
    "source_not_supported": "#E6E6E6",
    "not_requested": "#8B6F9C",
    "enumeration_incomplete": "#B64342",
    "complete_with_failures": "#D69A52",
    "complete": "#2F7D75",
    "confirmed_zero": "#BFD9D5",
}
DEPARTMENT_COLORS = {
    "DEFRA": "#24495F",
    "DTI": "#C57A43",
    "BERR": "#A45555",
    "BEIS": "#4D8B8B",
    "DECC": "#7A6F99",
    "DESNZ": "#3F8F98",
    "DETR": "#8E6B55",
    "MAFF": "#9B8BB4",
    "Department of the Environment": "#6F7D4C",
    "Department of Energy": "#C1A45B",
    "COP26": "#A76F91",
    "Other": "#9B8D70",
    "Other / co-publisher": "#9B8D70",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    frame.to_csv(path, index=False)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def series_case(alias: str = "d", source_alias: str = "s") -> str:
    return f"""
        CASE
          WHEN {source_alias}.source_name LIKE 'GOV.UK%' THEN 'policy_document'
          WHEN {alias}.content_type='ministerial_written_answer' THEN 'ministerial_written_answer'
          WHEN {alias}.content_type='ministerial_written_statement' THEN 'ministerial_written_statement'
          ELSE 'other'
        END
    """


def canonical_department(name: str) -> str:
    value = " ".join(str(name or "").upper().replace("&", "AND").split())
    exact = {
        "AGRICULTURE, FISHERIES AND FOOD": "MAFF",
        "ENERGY": "Department of Energy",
        "ENVIRONMENT": "Department of the Environment",
        "ENVIRONMENT, TRANSPORT AND THE REGIONS": "DETR",
        "TRADE AND INDUSTRY": "DTI",
        "DEPARTMENT OF TRADE AND INDUSTRY": "DTI",
        "BUSINESS, ENTERPRISE AND REGULATORY REFORM": "BERR",
        "DEPARTMENT FOR BUSINESS, ENTERPRISE AND REGULATORY REFORM": "BERR",
        "ENERGY AND CLIMATE CHANGE": "DECC",
        "DEPARTMENT FOR ENERGY AND CLIMATE CHANGE": "DECC",
        "ENVIRONMENT, FOOD AND RURAL AFFAIRS": "DEFRA",
        "DEPARTMENT FOR ENVIRONMENT, FOOD AND RURAL AFFAIRS": "DEFRA",
        "DEPARTMENT FOR BUSINESS, ENERGY AND INDUSTRIAL STRATEGY": "BEIS",
        "DEPARTMENT FOR ENERGY SECURITY AND NET ZERO": "DESNZ",
        "COP26": "COP26",
    }
    return exact.get(value, "Other / co-publisher")


def decade_label(year: int) -> str:
    if year <= 1989:
        return "1988–1989 (partial opening period)"
    if year <= 1999:
        return "1990–1999"
    if year <= 2009:
        return "2000–2009"
    if year <= 2019:
        return "2010–2019"
    return "2020–2026-09-21 (partial closing period)"


def configure_plotting() -> None:
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
    plt.rcParams['svg.fonttype'] = 'none'
    mpl.rcParams.update(
        {
            "font.size": 6.6,
            "axes.titlesize": 7.4,
            "axes.labelsize": 6.8,
            "xtick.labelsize": 5.8,
            "ytick.labelsize": 5.8,
            "legend.fontsize": 5.8,
            "figure.titlesize": 9.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
        }
    )


def add_panel_label(axis: plt.Axes, label: str) -> None:
    from matplotlib.transforms import ScaledTranslation

    offset = ScaledTranslation(-7 / 72, 3 / 72, axis.figure.dpi_scale_trans)
    axis.text(
        0,
        1,
        label,
        transform=axis.transAxes + offset,
        ha="left",
        va="bottom",
        fontsize=8,
        fontweight="bold",
    )


def export_figure(
    fig: plt.Figure,
    stem: str,
    axes: list[plt.Axes],
    panel_ids: list[str],
    *,
    row_groups: list[list[str]] | None = None,
    column_groups: list[list[str]] | None = None,
    exclude_axes: list[plt.Axes] | None = None,
    require_panel_labels: bool = True,
) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        axes=axes,
        panel_ids=panel_ids,
        row_groups=row_groups,
        column_groups=column_groups,
        exclude_axes=exclude_axes or [],
        json_out=str(QA / f"{stem}.alignment.json"),
        overlay_svg=str(QA / f"{stem}.alignment.svg"),
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        require_panel_labels=require_panel_labels,
        strict=True,
    )
    fig.savefig(FIGURES / f"{stem}.svg")
    fig.savefig(FIGURES / f"{stem}.pdf")
    fig.savefig(FIGURES / f"{stem}.png", dpi=300)
    fig.savefig(FIGURES / f"{stem}.tiff", dpi=600)
    plt.close(fig)


def collect_documents(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return con.execute(
        f"""
        SELECT d.document_id, d.external_id, d.title, d.canonical_url,
               d.publication_date, year(d.publication_date)::INTEGER AS year,
               month(d.publication_date)::INTEGER AS month,
               quarter(d.publication_date)::INTEGER AS quarter,
               d.publication_date_basis, d.content_type, d.source_id,
               s.source_name, {series_case()} AS series
        FROM documents d JOIN sources s USING(source_id)
        WHERE d.publication_date BETWEEN DATE '1988-01-01' AND DATE '2026-09-21'
        ORDER BY d.publication_date, d.document_id
        """
    ).fetchdf()


def collect_record_lengths(con: duckdb.DuckDBPyConnection, documents: pd.DataFrame) -> pd.DataFrame:
    policy = con.execute(
        """
        SELECT d.document_id, COUNT(ts.segment_id)::BIGINT AS segment_count,
               SUM(length(ts.segment_text))::BIGINT AS character_count
        FROM documents d
        JOIN sources s USING(source_id)
        JOIN document_content_objects rel USING(document_id)
        JOIN content_versions cv USING(content_object_id)
        JOIN text_segments ts USING(content_version_id)
        WHERE s.source_name LIKE 'GOV.UK%'
        GROUP BY d.document_id
        """
    ).fetchdf()
    parliament = con.execute(
        """
        SELECT va.document_id, COUNT(DISTINCT va.segment_id)::BIGINT AS segment_count,
               SUM(length(ts.segment_text))::BIGINT AS character_count
        FROM voice_attributions va JOIN text_segments ts USING(segment_id)
        GROUP BY va.document_id
        """
    ).fetchdf()
    lengths = pd.concat([policy, parliament], ignore_index=True)
    result = documents.merge(lengths, how="left", on="document_id")
    result["segment_count"] = result["segment_count"].fillna(0).astype("int64")
    result["character_count"] = result["character_count"].fillna(0).astype("int64")
    return result


def collect_organisation_links(con: duckdb.DuckDBPyConnection, documents: pd.DataFrame) -> pd.DataFrame:
    links = con.execute(
        """
        SELECT rel.document_id, o.organisation_name,
               rel.fractional_count_weight, rel.full_count_weight,
               rel.association_type, rel.allocation_status
        FROM document_organisations rel
        JOIN organisations o USING(organisation_id)
        """
    ).fetchdf()
    links["department"] = links["organisation_name"].map(canonical_department)
    metadata = documents[["document_id", "series", "year", "month"]]
    links = links.merge(metadata, on="document_id", how="inner")
    return links


def build_time_tables(documents: pd.DataFrame) -> dict[str, pd.DataFrame]:
    base = documents[documents["series"].isin(SERIES)].copy()
    values = base.groupby(["year", "series"]).size().to_dict()
    annual_rows: list[dict[str, Any]] = []
    for year in YEARS:
        for series in SERIES:
            annual_rows.append(
                {
                    "year": year,
                    "series": series,
                    "record_count": int(values.get((year, series), 0)),
                    "period_note": (
                        "partial opening year from 1988-01-01; Historic Hansard observations begin 1988-01-11"
                        if year == 1988
                        else "partial year through 2026-09-21"
                        if year == 2026
                        else "full calendar year in study range"
                    ),
                }
            )
    annual = pd.DataFrame(annual_rows)

    q_values = base.groupby(["year", "quarter", "series"]).size().to_dict()
    quarter_rows: list[dict[str, Any]] = []
    for year in YEARS:
        max_quarter = 3 if year == 2026 else 4
        for quarter in range(1, max_quarter + 1):
            for series in SERIES:
                quarter_rows.append(
                    {
                        "year": year,
                        "quarter": f"Q{quarter}",
                        "series": series,
                        "record_count": int(q_values.get((year, quarter, series), 0)),
                        "period_note": (
                            "partial opening quarter from 1988-01-01"
                            if year == 1988 and quarter == 1
                            else "partial quarter through 2026-09-21"
                            if year == 2026 and quarter == 3
                            else "full quarter in study range"
                        ),
                    }
                )
    quarterly = pd.DataFrame(quarter_rows)

    m_values = base.groupby(["year", "month", "series"]).size().to_dict()
    month_rows: list[dict[str, Any]] = []
    for period in MONTHS:
        for series in SERIES:
            month_rows.append(
                {
                    "year_month": str(period),
                    "year": period.year,
                    "month": period.month,
                    "series": series,
                    "record_count": int(m_values.get((period.year, period.month, series), 0)),
                    "period_note": (
                        "partial study-start month"
                        if period == MONTHS[0]
                        else "partial cutoff month through 2026-09-21"
                        if period == MONTHS[-1]
                        else "full calendar month in study range"
                    ),
                }
            )
    monthly = pd.DataFrame(month_rows)

    decade_rows: list[dict[str, Any]] = []
    temp = annual.copy()
    temp["period"] = temp["year"].map(decade_label)
    for (period, series), group in temp.groupby(["period", "series"], sort=False):
        decade_rows.append({"period": period, "series": series, "record_count": int(group["record_count"].sum())})
    decades = pd.DataFrame(decade_rows)

    presence = (
        monthly.assign(has_record=monthly["record_count"] > 0)
        .groupby("series", sort=False)
        .agg(
            total_month_slots=("year_month", "size"),
            months_with_records=("has_record", "sum"),
        )
        .reset_index()
    )
    presence["months_without_records"] = presence["total_month_slots"] - presence["months_with_records"]
    presence["interpretation"] = "Database observation only; a zero month is not automatically a completed source partition."
    return {"annual": annual, "quarterly": quarterly, "monthly": monthly, "decades": decades, "presence": presence}


def build_text_tables(
    con: duckdb.DuckDBPyConnection,
    record_lengths: pd.DataFrame,
    org_links: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    unique_totals_rows = []
    policy_unique = con.execute(
        """
        SELECT COUNT(*)::BIGINT AS segment_count, SUM(character_count)::BIGINT AS character_count
        FROM (
          SELECT DISTINCT ts.segment_id, length(ts.segment_text)::BIGINT AS character_count
          FROM documents d JOIN sources s USING(source_id)
          JOIN document_content_objects rel USING(document_id)
          JOIN content_versions cv USING(content_object_id)
          JOIN text_segments ts USING(content_version_id)
          WHERE s.source_name LIKE 'GOV.UK%'
        )
        """
    ).fetchone()
    unique_totals_rows.append(
        {"series": "policy_document", "unique_segment_count": int(policy_unique[0]), "unique_character_count": int(policy_unique[1])}
    )
    for series, segments, chars in con.execute(
        """
        SELECT d.content_type, COUNT(DISTINCT va.segment_id)::BIGINT,
               SUM(length(ts.segment_text))::BIGINT
        FROM voice_attributions va
        JOIN text_segments ts USING(segment_id)
        JOIN documents d USING(document_id)
        GROUP BY d.content_type
        """
    ).fetchall():
        unique_totals_rows.append(
            {"series": str(series), "unique_segment_count": int(segments), "unique_character_count": int(chars)}
        )
    unique_totals = pd.DataFrame(unique_totals_rows)
    associated = (
        record_lengths.groupby("series", sort=False)
        .agg(
            record_count=("document_id", "size"),
            record_associated_segment_count=("segment_count", "sum"),
            record_associated_character_count=("character_count", "sum"),
        )
        .reset_index()
    )
    scale = unique_totals.merge(associated, on="series", how="outer")
    scale["count_note"] = (
        "Unique segments measure stored text; record-associated totals can repeat a shared policy object across linked publication records."
    )

    quantiles = [0, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0]
    distribution_rows: list[dict[str, Any]] = []
    for series, group in record_lengths.groupby("series", sort=False):
        for measure in ["character_count", "segment_count"]:
            for quantile, value in group[measure].quantile(quantiles).items():
                distribution_rows.append(
                    {
                        "series": series,
                        "measure": measure,
                        "quantile": f"p{int(round(float(quantile) * 100)):02d}",
                        "value": float(value),
                        "record_count": int(len(group)),
                    }
                )
            distribution_rows.append(
                {
                    "series": series,
                    "measure": measure,
                    "quantile": "mean",
                    "value": float(group[measure].mean()),
                    "record_count": int(len(group)),
                }
            )
    distribution = pd.DataFrame(distribution_rows)

    top = record_lengths.nlargest(20, "character_count")[
        [
            "document_id",
            "series",
            "publication_date",
            "title",
            "canonical_url",
            "character_count",
            "segment_count",
        ]
    ].copy()
    top["share_of_series_characters"] = top.apply(
        lambda row: row["character_count"]
        / max(1, int(scale.loc[scale["series"] == row["series"], "record_associated_character_count"].iloc[0])),
        axis=1,
    )

    dominance_rows = []
    for series, group in record_lengths.groupby("series", sort=False):
        ordered = group.sort_values("character_count", ascending=False)
        total = int(ordered["character_count"].sum())
        dominance_rows.append(
            {
                "series": series,
                "record_count": len(ordered),
                "total_record_associated_characters": total,
                "top_1_character_share": float(ordered.head(1)["character_count"].sum() / max(total, 1)),
                "top_10_character_share": float(ordered.head(10)["character_count"].sum() / max(total, 1)),
                "top_20_character_share": float(ordered.head(20)["character_count"].sum() / max(total, 1)),
            }
        )
    dominance = pd.DataFrame(dominance_rows)

    weighted = org_links.merge(
        record_lengths[["document_id", "character_count", "segment_count"]], on="document_id", how="left"
    )
    weighted["weighted_characters"] = weighted["character_count"] * weighted["fractional_count_weight"]
    weighted["weighted_segments"] = weighted["segment_count"] * weighted["fractional_count_weight"]
    department_scale = (
        weighted.groupby(["series", "department"], as_index=False)
        .agg(
            fractional_record_count=("fractional_count_weight", "sum"),
            weighted_character_count=("weighted_characters", "sum"),
            weighted_segment_count=("weighted_segments", "sum"),
        )
    )
    department_scale["character_share_within_series"] = department_scale.groupby("series")[
        "weighted_character_count"
    ].transform(lambda value: value / max(float(value.sum()), 1.0))
    department_scale["segment_share_within_series"] = department_scale.groupby("series")[
        "weighted_segment_count"
    ].transform(lambda value: value / max(float(value.sum()), 1.0))
    return {
        "scale": scale,
        "distribution": distribution,
        "top": top,
        "dominance": dominance,
        "department_scale": department_scale,
    }


def build_department_tables(org_links: pd.DataFrame, documents: pd.DataFrame) -> dict[str, pd.DataFrame]:
    grouped = (
        org_links.groupby(["series", "year", "department"], as_index=False)
        .agg(
            fractional_record_count=("fractional_count_weight", "sum"),
            full_association_count=("document_id", "size"),
        )
    )
    denominators = documents.groupby(["series", "year"]).size().rename("series_year_records").reset_index()
    grouped = grouped.merge(denominators, on=["series", "year"], how="left")
    grouped["fractional_share"] = grouped["fractional_record_count"] / grouped["series_year_records"]
    grouped["count_note"] = (
        "Ministerial records have one official department. Multi-organisation policy records use stored fractional weights so annual shares sum to the record denominator."
    )

    peaks = []
    for department in ["DTI", "BERR", "BEIS"]:
        subset = grouped[(grouped["department"] == department) & grouped["series"].isin(SERIES)]
        if subset.empty:
            continue
        for series, series_group in subset.groupby("series"):
            best = series_group.sort_values(["fractional_share", "fractional_record_count"], ascending=False).iloc[0]
            peaks.append(
                {
                    "department": department,
                    "series": series,
                    "peak_year": int(best["year"]),
                    "fractional_record_count": float(best["fractional_record_count"]),
                    "series_year_records": int(best["series_year_records"]),
                    "peak_share": float(best["fractional_share"]),
                }
            )
    return {"annual": grouped, "peaks": pd.DataFrame(peaks)}


def rows_by_month(path: Path, date_field: str, predicate: Any = None) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in read_csv_rows(path):
        if predicate is not None and not predicate(row):
            continue
        value = str(row.get(date_field, ""))
        if len(value) >= 7:
            counts[value[:7]] += 1
    return counts


def batch_record_months(con: duckdb.DuckDBPyConnection, batch_id: str, series: str | None = None) -> Counter[str]:
    params: list[Any] = [batch_id]
    where = "e.batch_id=?"
    if series:
        where += " AND d.content_type=?"
        params.append(series)
    rows = con.execute(
        f"""
        SELECT strftime(d.publication_date, '%Y-%m'), COUNT(DISTINCT d.document_id)
        FROM enumeration_records e JOIN documents d USING(document_id)
        WHERE {where}
        GROUP BY 1
        """,
        params,
    ).fetchall()
    return Counter({str(month): int(count) for month, count in rows})


def build_coverage_status(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame]:
    recovery_targets = read_csv_rows(RECOVERY / "manifests/parlparse_target_dates.csv")
    recovery_files = read_csv_rows(RECOVERY / "manifests/parlparse_remote_file_manifest.csv")
    recovery_fetches = read_csv_rows(RECOVERY / "evidence/parlparse_acquisition_status.csv")
    recovery_parse_failures = read_csv_rows(RECOVERY / "evidence/parlparse_parse_failures.csv")
    recovery_month_states: dict[str, list[str]] = defaultdict(list)
    recovery_date_units: list[dict[str, str]] = []
    for target in recovery_targets:
        for kind in ["wrans", "wms"]:
            if target.get(kind) != "True":
                continue
            date_value = target["date"]
            matched_files = [row for row in recovery_files if row.get("date") == date_value and row.get("kind") == kind]
            matched_fetches = [row for row in recovery_fetches if row.get("date") == date_value and row.get("kind") == kind]
            if not matched_files:
                state = "enumeration_incomplete"
            elif any(row.get("download_status") == "unrequested_host_stop" for row in matched_fetches) or len(matched_fetches) < len(matched_files):
                state = "not_requested"
            elif any(row.get("download_status") != "success" for row in matched_fetches):
                state = "complete_with_failures"
            elif any(row.get("date") == date_value and row.get("kind") == kind for row in recovery_parse_failures):
                state = "complete_with_failures"
            else:
                state = "complete"
            recovery_month_states[date_value[:7]].append(state)
            recovery_date_units.append({"date": date_value, "kind": kind, "reasons": target.get("reasons", ""), "state": state})
    recovery_priority = {"enumeration_incomplete": 0, "not_requested": 1, "complete_with_failures": 2, "complete": 3}
    source_specs = [
        {
            "key": "govuk_defra_frozen",
            "label": "GOV.UK frozen DEFRA query",
            "series": "Policy records",
            "start": pd.Period("1988-01", "M"),
            "end": pd.Period("2026-09", "M"),
            "records": batch_record_months(con, "govuk_defra_policy_paper_1988_20260921_v1"),
        },
        {
            "key": "govuk_historical_tags",
            "label": "GOV.UK DTI/DECC/BERR/DETR tags",
            "series": "Policy records",
            "start": pd.Period("1988-01", "M"),
            "end": pd.Period("2009-12", "M"),
            "records": rows_by_month(MANIFESTS / "policy_manifest.csv", "first_published_at"),
        },
        {
            "key": "govuk_exact_historical_recovery",
            "label": "GOV.UK exact historic policy recovery",
            "series": "Policy records",
            "start": pd.Period("1994-01", "M"),
            "end": pd.Period("1994-01", "M"),
            "records": batch_record_months(con, "govuk_historical_policy_targeted_recovery_20260922_v1"),
        },
        {
            "key": "ukgwa_predecessor_routes",
            "label": "UKGWA predecessor policy routes",
            "series": "Policy records",
            "start": pd.Period("1988-01", "M"),
            "end": pd.Period("2009-12", "M"),
            "records": Counter(),
        },
        {
            "key": "historic_hansard",
            "label": "Historic Hansard bulk XML",
            "series": "Answers + statements",
            "start": pd.Period("1988-01", "M"),
            "end": pd.Period("2004-10", "M"),
            "records": batch_record_months(con, "commons_historic_hansard_1988_2004_20260921_v1"),
        },
        {
            "key": "commons_2004_q4_seam",
            "label": "Commons 2004-Q4 cross-route seam",
            "series": "Answers + statements",
            "start": pd.Period("2004-10", "M"),
            "end": pd.Period("2004-12", "M"),
            "records": Counter(),
        },
        {
            "key": "hansard_2005_2010",
            "label": "Hansard API 2005–2010",
            "series": "Answers + statements",
            "start": pd.Period("2005-01", "M"),
            "end": pd.Period("2010-04", "M"),
            "records": batch_record_months(con, "commons_hansard_api_2005_20100430_20260921_v1"),
        },
        {
            "key": "gap_archive_answers",
            "label": "Commons archive gap answers",
            "series": "Written answers",
            "start": pd.Period("2010-05", "M"),
            "end": pd.Period("2014-09", "M"),
            "records": batch_record_months(
                con,
                "commons_hansard_api_20100501_20140911_20260921_v1",
                "ministerial_written_answer",
            ),
        },
        {
            "key": "gap_hansard_statements",
            "label": "Hansard API gap statements",
            "series": "Written statements",
            "start": pd.Period("2010-05", "M"),
            "end": pd.Period("2014-09", "M"),
            "records": batch_record_months(
                con,
                "commons_hansard_api_20100501_20140911_20260921_v1",
                "ministerial_written_statement",
            ),
        },
        {
            "key": "parlparse_bounded_recovery",
            "label": "ParlParse/TWFY bounded gap recovery",
            "series": "Answers + statements (target dates only)",
            "start": pd.Period("2004-10", "M"),
            "end": pd.Period("2014-09", "M"),
            "records": batch_record_months(con, "commons_parlparse_targeted_gap_recovery_20260922_v1"),
            "bounded_months": set(recovery_month_states),
        },
        {
            "key": "modern_questions_statements",
            "label": "Questions/Statements API",
            "series": "Answers + statements",
            "start": pd.Period("2014-09", "M"),
            "end": pd.Period("2026-09", "M"),
            "records": batch_record_months(con, "commons_questions_statements_20140912_20260921_v1"),
        },
    ]

    original_failures = Counter(
        {
            str(month): int(count)
            for month, count in con.execute(
                """
                SELECT strftime(d.publication_date, '%Y-%m'), COUNT(DISTINCT a.content_object_id)
                FROM acquisition_object_statuses a
                JOIN document_content_objects rel USING(content_object_id)
                JOIN documents d USING(document_id)
                WHERE a.batch_id='govuk_defra_policy_paper_1988_20260921_v1'
                  AND (a.download_status<>'success' OR a.extraction_status<>'success')
                GROUP BY 1
                """
            ).fetchall()
        }
    )
    historical_policy_failures = Counter(
        {
            str(month): int(count)
            for month, count in con.execute(
                """
                SELECT strftime(d.publication_date, '%Y-%m'), COUNT(DISTINCT a.content_object_id)
                FROM acquisition_object_statuses a
                JOIN document_content_objects rel USING(content_object_id)
                JOIN documents d USING(document_id)
                WHERE a.batch_id='govuk_historical_policy_1988_2009_20260921_v1'
                  AND (a.download_status<>'success' OR a.extraction_status<>'success')
                GROUP BY 1
                """
            ).fetchall()
        }
    )
    repair_ledger = read_csv_rows(REPAIR / "repair_ledger.csv")
    # Companies House was recovered in the bounded mirror tranche.  The sole
    # remaining 2005–2010 answer issue is the intentionally excluded Asda
    # mixed/attribution target; it is not an access failure.
    answer_failures = Counter({"2006-07": 1})
    candidate_failures: Counter[str] = Counter()
    gap_index_failures = rows_by_month(
        MANIFESTS / "hansard_gap_archive_index_status.csv", "date", lambda row: row.get("status") != "success"
    )
    gap_page_failures = rows_by_month(
        MANIFESTS / "hansard_gap_archive_page_acquisition_status.csv",
        "date",
        lambda row: row.get("download_status") != "success",
    )
    gap_unrequested = rows_by_month(MANIFESTS / "hansard_gap_archive_unprocessed_page_targets.csv", "date")
    gap_residual_indexes = Counter(
        row["date"][:7]
        for row in recovery_date_units
        if row["kind"] == "wrans" and "failed_date_index" in row["reasons"] and row["state"] != "complete"
    )
    gap_residual_failed_pages = Counter(
        row["date"][:7]
        for row in recovery_date_units
        if row["kind"] == "wrans" and "failed_known_page" in row["reasons"] and row["state"] != "complete"
    )
    gap_residual_unrequested = Counter(
        row["date"][:7]
        for row in recovery_date_units
        if row["kind"] == "wrans" and "unrequested_known_page" in row["reasons"] and row["state"] != "complete"
    )
    gap_statement_failures = Counter(
        row["record_date"][:7]
        for row in repair_ledger
        if row.get("gap_id") == "statement_candidate:1009068000001"
        and row.get("disposition") == "unresolved_container"
    )

    rows: list[dict[str, Any]] = []
    for spec in source_specs:
        for period in MONTHS:
            month = str(period)
            supported = spec["start"] <= period <= spec["end"] and (
                not spec.get("bounded_months") or month in spec["bounded_months"]
            )
            record_count: int | None = int(spec["records"].get(month, 0)) if supported else None
            failed_indexes = 0
            failed_targets = 0
            unrequested_targets = 0
            candidate_anomalies = 0
            note = ""
            if not supported:
                status = "source_not_supported"
                note = "Outside this source route's bounded study interval."
            elif spec["key"] == "ukgwa_predecessor_routes":
                status = "enumeration_incomplete"
                record_count = None
                note = "Normal archive route was access-blocked; the predecessor-policy population remains unknown despite exact-item recovery."
            elif spec["key"] == "govuk_exact_historical_recovery":
                status = "complete" if record_count else "complete_with_failures"
                note = "One exact Cm 2428 target; not a historical-policy population denominator."
            elif spec["key"] == "govuk_defra_frozen":
                failed_targets = original_failures[month]
                status = "complete_with_failures" if failed_targets else "complete" if record_count else "confirmed_zero"
                note = "Complete only within the frozen current-DEFRA Search API query."
            elif spec["key"] == "govuk_historical_tags":
                failed_targets = historical_policy_failures[month]
                status = "complete_with_failures" if failed_targets else "complete" if record_count else "confirmed_zero"
                note = "Complete only within visible DTI/DECC/BERR/DETR organisation-tag partitions."
            elif spec["key"] == "historic_hansard":
                if month == "2004-10":
                    status = "enumeration_incomplete"
                    note = "Bulk-volume Commons window ends 2004-10-04; the remainder of October is in the unresolved cross-route seam."
                elif month == "1991-12":
                    failed_targets = 1
                    status = "complete_with_failures"
                    note = "Alternative official daily route enumerated 10/10 sitting days and 322 items; 321 parsed/ingested and one malformed page remains unresolved."
                elif month == "1988-01":
                    status = "complete" if record_count else "confirmed_zero"
                    note = "Official January calendar shows the first sitting on 1988-01-11; 1–10 January is recess, not a collection gap."
                else:
                    status = "complete" if record_count else "confirmed_zero"
                    note = "Within successfully downloaded official volumes."
            elif spec["key"] == "commons_2004_q4_seam":
                status = "enumeration_incomplete"
                record_count = None
                note = "Historic daily pages expose Lords only; both normal Commons hosts stopped after three consecutive HTTP 403 responses. Denominator remains unknown."
            elif spec["key"] == "hansard_2005_2010":
                failed_targets = answer_failures[month]
                candidate_anomalies = candidate_failures[month]
                status = (
                    "complete_with_failures"
                    if failed_targets or candidate_anomalies
                    else "complete"
                    if record_count
                    else "confirmed_zero"
                )
                note = "Answer targets and statement-candidate anomalies are separate units."
            elif spec["key"] == "gap_archive_answers":
                failed_indexes = gap_residual_indexes[month]
                failed_targets = gap_residual_failed_pages[month]
                unrequested_targets = gap_residual_unrequested[month]
                if failed_indexes:
                    status = "enumeration_incomplete"
                elif unrequested_targets:
                    status = "not_requested"
                elif failed_targets:
                    status = "complete_with_failures"
                else:
                    status = "complete" if record_count else "confirmed_zero"
                note = "Failed date indexes imply an unknown record count; page targets are a different unit."
            elif spec["key"] == "gap_hansard_statements":
                candidate_anomalies = gap_statement_failures[month]
                status = "complete_with_failures" if candidate_anomalies else "complete" if record_count else "confirmed_zero"
                note = "Candidate pages are not equivalent to eligible statement records."
            elif spec["key"] == "parlparse_bounded_recovery":
                month_states = recovery_month_states.get(month, ["enumeration_incomplete"])
                status = min(month_states, key=lambda value: recovery_priority[value])
                if status == "complete" and not record_count:
                    status = "confirmed_zero"
                note = "Bounded date×genre mirror targets only; no-file dates remain unknown and mirror overlaps are not new documents."
            else:
                status = "complete" if record_count else "confirmed_zero"
                note = "174 acquired parent list responses support 65,988 derived records; units are kept separate."
            rows.append(
                {
                    "source_key": spec["key"],
                    "source": spec["label"],
                    "series_scope": spec["series"],
                    "year_month": month,
                    "status": status,
                    "status_label": STATUS_LABELS[status],
                    "record_count": record_count,
                    "failed_date_indexes": failed_indexes,
                    "failed_known_targets": failed_targets,
                    "unrequested_known_targets": unrequested_targets,
                    "candidate_anomalies": candidate_anomalies,
                    "note": note,
                }
            )
    status = pd.DataFrame(rows)

    seam_residual_units = sum(
        row["state"] != "complete" and "2004_q4_commons_seam" in row["reasons"]
        for row in recovery_date_units
    )
    gap_index_residual_units = sum(
        row["state"] != "complete" and row["kind"] == "wrans" and "failed_date_index" in row["reasons"]
        for row in recovery_date_units
    )

    anomalies = pd.DataFrame(
        [
            {
                "source": "Historic Hansard bulk XML",
                "interval": "1991-12-02..1991-12-13",
                "issue": "alternative daily route recovered 321/322 frozen items; one malformed item has unresolved attribution",
                "count": 1,
                "unit": "written-answer item",
                "missing_record_count": "1 known unresolved item",
            },
            {
                "source": "Commons 2004-Q4 cross-route seam",
                "interval": "2004-10-05..2004-12-31",
                "issue": "bounded mirror recovery completed where wrans/wms files exist; expected date×genre units with no file remain unknown",
                "count": seam_residual_units,
                "unit": "date × genre target",
                "missing_record_count": "unknown for residual units; not a document count",
            },
            {
                "source": "Hansard API 2005–2010 answers",
                "interval": "2005-01-01..2010-04-30",
                "issue": "Companies House recovered from the bounded mirror; Asda excluded because text/department attribution cannot be separated reliably",
                "count": 1,
                "unit": "excluded ambiguous answer target",
                "missing_record_count": "0 access failures; one non-usable ambiguous target retained as exclusion",
            },
            {
                "source": "Hansard API 2005–2010 statement candidates",
                "interval": "2005-01-01..2010-04-30",
                "issue": "candidate anomalies remaining after child-level resolution",
                "count": sum(candidate_failures.values()),
                "unit": "candidate detail",
                "missing_record_count": "0; three in-scope child statements recovered and out-of-scope children excluded",
            },
            {
                "source": "Commons archive gap answers",
                "interval": "2010-05-01..2014-09-11",
                "issue": "failed dated indexes without a matching bounded mirror wrans file after recovery",
                "count": gap_index_residual_units,
                "unit": "date index",
                "missing_record_count": "unknown",
            },
            {
                "source": "Commons archive gap answers",
                "interval": "2010-05-01..2014-09-11",
                "issue": "baseline failed known page targets; all affected dates obtained as complete alternative XML files",
                "count": sum(gap_page_failures.values()),
                "unit": "baseline HTML page target",
                "missing_record_count": "0 residual affected dates in the chosen mirror; page and record units remain distinct",
            },
            {
                "source": "Commons archive gap answers",
                "interval": "2010-05-01..2014-09-11",
                "issue": "baseline known pages not requested; all affected dates obtained as complete alternative XML files",
                "count": sum(gap_unrequested.values()),
                "unit": "baseline HTML page target",
                "missing_record_count": "0 residual affected dates in the chosen mirror; page and record units remain distinct",
            },
            {
                "source": "Hansard API gap statements",
                "interval": "2010-05-01..2014-09-11",
                "issue": "one repeated cross-date container remains unresolved; Defence candidate excluded",
                "count": sum(gap_statement_failures.values()),
                "unit": "candidate detail",
                "missing_record_count": "eligibility unresolved",
            },
        ]
    )
    return status, anomalies


def metric_row(
    source: str,
    scope: str,
    metric: str,
    numerator: int,
    denominator: int,
    unit: str,
    note: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "series_scope": scope,
        "metric": metric,
        "numerator": numerator,
        "denominator": denominator,
        "unit": unit,
        "percent": 100.0 * numerator / denominator if denominator else None,
        "note": note,
    }


def build_coverage_rates() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    recovery_enumeration = read_json(RECOVERY / "reports/mirror_enumeration_summary.json")
    recovery_acquisition = read_json(RECOVERY / "reports/mirror_acquisition_summary.json")
    recovery_parsed = read_json(RECOVERY / "reports/parlparse_parse_match_summary.json")
    recovery_ingestion = read_json(RECOVERY / "reports/incremental_ingestion_summary.json")
    recovery_policy = read_json(RECOVERY / "reports/early_policy_acquisition_summary.json")

    def add(source: str, scope: str, values: list[tuple[str, int, int, str, str]]) -> None:
        for metric, numerator, denominator, unit, note in values:
            rows.append(metric_row(source, scope, metric, numerator, denominator, unit, note))

    add(
        "GOV.UK frozen DEFRA query",
        "policy records",
        [
            ("Index/enumeration completion", 39, 39, "annual query partition", "Complete as visible in the frozen current-DEFRA Search API query."),
            ("Frozen-target processing", 3025, 3025, "content object", "Webpage and unique attachment objects; not publication records."),
            ("Original acquisition", 3021, 3025, "content object", "Current post-retry download state."),
            ("Text availability", 3000, 3025, "content object", "Successful extraction; not full-policy completeness."),
            ("Formal ingestion completion", 1020, 1020, "eligible publication record", "All frozen publication records retained; object-level extraction gaps remain."),
        ],
    )
    add(
        "GOV.UK historical organisation tags",
        "policy records",
        [
            ("Index/enumeration completion", 88, 88, "organisation-year partition", "Only DTI, DECC, BERR and DETR GOV.UK tags; UK DoE/MAFF archive routes unresolved."),
            ("Frozen-target processing", 84, 84, "content object", "34 webpages and 50 attachments."),
            ("Original acquisition", 84, 84, "content object", "All frozen objects downloaded."),
            ("Text availability", 84, 84, "content object", "Four downloaded PDFs were recovered with local page-mapped OCR; original bytes retained."),
            ("Formal ingestion completion", 34, 34, "eligible net-new publication record", "One of 35 enumerated records already existed in the 06 batch."),
        ],
    )
    add(
        "GOV.UK exact historic policy recovery",
        "policy records",
        [
            ("Frozen-target processing", int(recovery_policy.get("targets", 0)), int(recovery_policy.get("targets", 0)), "exact policy target", "Cm 2428 only; no population denominator inferred."),
            ("Original acquisition", int(recovery_policy.get("acquired", 0)), int(recovery_policy.get("targets", 0)), "exact policy target", "Official Content API, landing page and PDF request evidence retained."),
            ("Text availability", int(recovery_policy.get("acquired", 0)), int(recovery_policy.get("targets", 0)), "exact policy target", "Complete command-paper attachment extracted; not broader archive completeness."),
            ("Formal ingestion completion", int(recovery_policy.get("acquired", 0)), int(recovery_policy.get("acquired", 0)), "eligible recovered policy", "Successful exact identity only."),
        ],
    )
    add(
        "Historic Hansard bulk XML",
        "answers + statements",
        [
            ("Index/enumeration completion", 319, 320, "planned volume", "Volume 200 failed; the number of records hidden by that failure is unknown."),
            ("Frozen-target processing", 320, 320, "planned volume", "All planned volume URLs attempted."),
            ("Original acquisition", 319, 320, "volume", "Valid ZIP/XML volumes."),
            ("Text availability", 319, 320, "volume", "All valid acquired volumes parsed; denominator is volumes, not records."),
            ("Formal ingestion completion", 135761, 135761, "eligible record from acquired volumes", "Known eligible subset only; excludes unknown records in volume 200."),
        ],
    )
    add(
        "Historic Hansard volume 200 daily repair",
        "written answers",
        [
            ("Index/enumeration completion", 10, 10, "actual Commons sitting-day index", "Official December calendar bounds the failed volume to 1991-12-02..13; weekends/non-sittings are excluded."),
            ("Frozen-target processing", 322, 322, "written-answer item", "All exact approved-department item links were requested once through the official daily route."),
            ("Original acquisition", 322, 322, "written-answer item HTML", "All item pages returned HTTP 200 and were retained."),
            ("Text availability", 321, 322, "written-answer item", "One page merges unrelated text inside the questioner contribution and remains unresolved."),
            ("Formal ingestion completion", 321, 321, "eligible parsed record", "All records with deterministic question/response attribution were formally committed."),
        ],
    )
    add(
        "Hansard API 2005–2010 answers",
        "written answers",
        [
            ("Index/enumeration completion", 64, 64, "calendar-month partition", "794/794 sitting-day trees also downloaded."),
            ("Frozen-target processing", 23990, 23990, "answer-section target", "All frozen details attempted."),
            ("Original acquisition", 23990, 23990, "answer-section target", "All original payload requests completed; 85 were parser/detail-validation anomalies rather than transport failures."),
            ("Text availability", 23989, 23990, "answer-section target", "Eighty-three saved payloads were reparsed and Companies House was recovered through the bounded mirror; Asda remains excluded as ambiguous."),
            ("Formal ingestion completion", 23989, 23989, "eligible resolved record", "Successful resolved subset only; not whole-source coverage."),
        ],
    )
    add(
        "Hansard API 2005–2010 statement candidates",
        "written statements",
        [
            ("Index/enumeration completion", 6, 6, "annual candidate-search partition", "Candidate enumeration complete within the route."),
            ("Frozen-target processing", 7013, 7013, "candidate detail", "Candidate unit is not an eligible statement record."),
            ("Original acquisition", 7006, 7013, "candidate detail", "Seven detail routes failed, but their saved official search parents remained available for bounded resolution."),
            ("Candidate resolution", 7013, 7013, "candidate detail", "Failed containers were decomposed using official ContributionExtId evidence; out-of-scope children were excluded."),
            ("Formal ingestion completion", 846, 846, "eligible acquired statement record", "Three newly verified child statements were committed; candidate and statement units remain distinct."),
        ],
    )
    add(
        "Commons publications archive gap answers",
        "written answers",
        [
            ("Index/enumeration completion", 618, 638, "dated sitting-day index", "Twenty failed indexes leave an unknown record denominator."),
            ("Frozen-target processing", 851, 1063, "known HTML page target", "212 known pages were not requested after the throttle stop."),
            ("Original acquisition", 626, 1063, "known HTML page target", "225 attempted pages failed; failed indexes may hide additional unknown targets."),
            ("Text availability", 626, 1063, "known HTML page target", "Successfully downloaded pages parsed without recorded parser errors."),
            ("Formal ingestion completion", 11135, 11135, "eligible record parsed from acquired pages", "Known successful subset only; page and record units are not interchangeable."),
        ],
    )
    recovery_new = int(recovery_parsed.get("new_recovered_identity", 0))
    recovery_committed = int(recovery_ingestion.get("added", {}).get("documents", 0)) - int(recovery_policy.get("acquired", 0))
    add(
        "ParlParse/TWFY bounded gap recovery",
        "answers + statements on frozen target dates",
        [
            ("Index/enumeration completion", int(recovery_enumeration.get("dates_with_files", 0)), int(recovery_enumeration.get("target_dates", 0)), "date partition", "No-file dates remain unknown, not confirmed zero."),
            ("Frozen-target processing", int(recovery_acquisition.get("attempted_or_resumed", 0)), int(recovery_acquisition.get("frozen_files", 0)), "XML file", "Only enumerated target-date files were requested."),
            ("Original acquisition", int(recovery_acquisition.get("acquired", 0)), int(recovery_acquisition.get("frozen_files", 0)), "XML file", "Real per-file request/final URL, status, MIME and timestamp retained."),
            ("Text availability", int(recovery_parsed.get("parsed_in_scope_records", 0)), int(recovery_parsed.get("parsed_in_scope_records", 0)), "in-scope derived record", "Mirror records are derived from acquired XML; overlaps are mapped, not duplicated."),
            ("Formal ingestion completion", recovery_committed, recovery_new, "eligible new stable identity", "Counts only successful formal COMMIT deltas."),
        ],
    )
    add(
        "Hansard API gap statement candidates",
        "written statements",
        [
            ("Index/enumeration completion", 5, 5, "annual candidate-search partition", "Date-bounded candidate partitions completed."),
            ("Frozen-target processing", 5676, 5676, "candidate detail", "Candidate unit is not an eligible statement record."),
            ("Original acquisition", 5674, 5676, "candidate detail", "Two detail failures were retained; saved official search evidence resolved one as out-of-scope Defence."),
            ("Candidate resolution", 5675, 5676, "candidate detail", "One repeated cross-date header/container remains unresolved and is not inserted as a statement."),
            ("Formal ingestion completion", 493, 493, "eligible acquired statement record", "Ingestion denominator excludes non-eligible candidates."),
        ],
    )
    add(
        "Questions/Statements API 2014–2026",
        "answers + statements",
        [
            ("Index/enumeration completion", 62, 62, "department-year-genre partition", "Complete as visible through 2026-09-21."),
            ("Frozen-target processing", 65988, 65988, "derived record target", "All records parsed from acquired parent list responses."),
            ("Original acquisition", 174, 174, "parent API response", "Parent-response unit; never combined with the 65,988-record denominator."),
            ("Text availability", 65988, 65988, "derived record target", "Full text present in verified parent responses."),
            ("Formal ingestion completion", 65988, 65988, "eligible derived record", "Per-record JSON is derived evidence; no fictitious per-record HTTP status."),
        ],
    )
    return pd.DataFrame(rows)


def plot_annual(annual: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(7.205, 5.7), sharex=True)
    for index, (axis, series) in enumerate(zip(axes, SERIES, strict=True)):
        subset = annual[annual["series"] == series]
        axis.bar(subset["year"], subset["record_count"], width=0.82, color=SERIES_COLORS[series], linewidth=0)
        axis.set_title(SERIES_LABELS[series], loc="left", fontweight="bold")
        axis.set_ylabel("Records")
        axis.ticklabel_format(axis="y", style="plain")
        axis.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=4, integer=True))
        axis.axvspan(1987.5, 1988.5, color="#D9D9D9", alpha=0.35, zorder=-1)
        axis.axvspan(2025.5, 2026.5, color="#D9D9D9", alpha=0.35, zorder=-1)
        add_panel_label(axis, chr(ord("a") + index))
    axes[-1].set_xticks(list(range(1988, 2027, 3)))
    plt.setp(axes[-1].get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    axes[-1].set_xlabel("Official publication / answer / statement year")
    fig.suptitle("Annual record distributions remain separate by document genre", x=0.08, ha="left", fontweight="bold")
    fig.text(
        0.08,
        0.018,
        "Independent y-axes. Record counts are not homogeneous policy quantities. 1988 and 2026 are partial study years; cutoff 21 Sep 2026.",
        fontsize=5.8,
        color="#555555",
    )
    fig.subplots_adjust(left=0.10, right=0.985, top=0.92, bottom=0.12, hspace=0.45)
    export_figure(fig, "01_annual_distribution", list(axes), ["a", "b", "c"], column_groups=[["a", "b", "c"]])


def plot_month_heatmaps(monthly: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(7.205, 5.45), sharex=True)
    cbar_axes: list[plt.Axes] = []
    for index, (axis, series) in enumerate(zip(axes, SERIES, strict=True)):
        subset = monthly[monthly["series"] == series]
        matrix = subset.pivot(index="year", columns="month", values="record_count").reindex(index=YEARS, columns=range(1, 13)).fillna(0)
        positive = matrix.to_numpy()[matrix.to_numpy() > 0]
        vmax = max(1, int(positive.max())) if positive.size else 1
        image = axis.imshow(
            matrix.to_numpy() + 1,
            aspect="auto",
            interpolation="nearest",
            cmap=ListedColormap(mpl.colormaps["Blues"](np.linspace(0.08, 0.95, 256))),
            norm=LogNorm(vmin=1, vmax=vmax + 1),
            origin="lower",
        )
        axis.set_title(f"{SERIES_LABELS[series]} · independent log scale · monthly max {vmax:,}", loc="left", fontweight="bold")
        axis.set_ylabel("Year")
        axis.set_yticks(np.arange(0, len(YEARS), 4), [str(YEARS[i]) for i in range(0, len(YEARS), 4)])
        tick_values = [value for value in [1, 10, 100, 1_000, 10_000] if value <= vmax + 1]
        if vmax + 1 not in tick_values:
            tick_values.append(vmax + 1)
        cbar = fig.colorbar(
            image,
            ax=axis,
            fraction=0.018,
            pad=0.012,
            ticks=tick_values,
            format=mpl.ticker.FuncFormatter(lambda value, _position: f"{int(value):,}"),
        )
        cbar.ax.set_ylabel("records + 1", rotation=90, rotation_mode="anchor", labelpad=3)
        cbar_axes.append(cbar.ax)
        add_panel_label(axis, chr(ord("a") + index))
    axes[-1].set_xticks(np.arange(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    axes[-1].set_xlabel("Month")
    fig.suptitle("Year × month record density by independent genre", x=0.08, ha="left", fontweight="bold")
    fig.text(
        0.08,
        0.015,
        "Each panel uses its own scale. White/very pale cells mean zero or low observed records, not proof of no government activity or complete source coverage.",
        fontsize=5.7,
        color="#555555",
    )
    fig.subplots_adjust(left=0.10, right=0.91, top=0.92, bottom=0.105, hspace=0.42)
    export_figure(
        fig,
        "02_year_month_heatmaps",
        list(axes),
        ["a", "b", "c"],
        column_groups=[["a", "b", "c"]],
        exclude_axes=cbar_axes,
    )


def plot_coverage_status(status: pd.DataFrame) -> None:
    source_order = list(dict.fromkeys(status["source"].tolist()))
    matrix = np.zeros((len(source_order), len(MONTHS)), dtype=int)
    code = {value: index for index, value in enumerate(STATUS_ORDER)}
    for row_index, source in enumerate(source_order):
        subset = status[status["source"] == source].set_index("year_month")
        matrix[row_index, :] = [code[str(subset.loc[str(period), "status"])] for period in MONTHS]
    cmap = ListedColormap([STATUS_COLORS[key] for key in STATUS_ORDER])
    norm = BoundaryNorm(np.arange(-0.5, len(STATUS_ORDER) + 0.5), len(STATUS_ORDER))
    fig, axis = plt.subplots(figsize=(7.205, 3.75))
    axis.imshow(matrix, aspect="auto", interpolation="nearest", cmap=cmap, norm=norm)
    axis.set_yticks(np.arange(len(source_order)), source_order)
    year_positions = [i for i, value in enumerate(MONTHS) if value.month == 1 and value.year % 2 == 0]
    axis.set_xticks(year_positions, [str(MONTHS[i].year) for i in year_positions], rotation=45, ha="right", rotation_mode="anchor")
    axis.set_xlabel("Year-month")
    axis.set_title("Collection status is categorical and separate from record quantity", loc="left", fontweight="bold")
    legend = [Patch(facecolor=STATUS_COLORS[key], edgecolor="none", label=STATUS_LABELS[key]) for key in STATUS_ORDER]
    axis.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False)
    axis.axvline(MONTHS.get_loc(pd.Period("1991-12", "M")), color="#272727", linewidth=0.7)
    axis.text(
        MONTHS.get_loc(pd.Period("1991-12", "M")),
        2.8,
        "Vol. 200\n2–13 Dec 1991",
        fontsize=5.5,
        ha="center",
        va="bottom",
        rotation=90,
        rotation_mode="anchor",
    )
    fig.text(
        0.10,
        0.015,
        "Failed indexes may hide an unknown number of records. Known failed pages, unrequested pages and candidate anomalies are different units and are not added as 'missing documents'.",
        fontsize=5.7,
        color="#555555",
    )
    fig.subplots_adjust(left=0.31, right=0.985, top=0.89, bottom=0.32)
    export_figure(fig, "03_collection_coverage_status", [axis], ["a"], require_panel_labels=False)


def plot_department_composition(department_annual: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(7.205, 6.25), sharex=True)
    legend_handles: dict[str, Patch] = {}
    for index, (axis, series) in enumerate(zip(axes, SERIES, strict=True)):
        subset = department_annual[department_annual["series"] == series].copy()
        totals = subset.groupby("department")["fractional_record_count"].sum().sort_values(ascending=False)
        keep = list(totals.head(6).index)
        subset["display_department"] = subset["department"].where(subset["department"].isin(keep), "Other")
        pivot = (
            subset.groupby(["year", "display_department"])["fractional_record_count"]
            .sum()
            .unstack(fill_value=0)
            .reindex(YEARS, fill_value=0)
        )
        shares = pivot.div(pivot.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
        bottom = np.zeros(len(YEARS))
        columns = [value for value in keep if value in shares.columns]
        if "Other" in shares.columns:
            columns.append("Other")
        for department in columns:
            color = DEPARTMENT_COLORS.get(department, "#9B8D70")
            axis.bar(YEARS, shares[department], bottom=bottom, width=0.9, color=color, linewidth=0, label=department)
            bottom += shares[department].to_numpy()
            legend_handles.setdefault(f"{SERIES_SHORT[series]} · {department}", Patch(facecolor=color, label=f"{SERIES_SHORT[series]} · {department}"))
        axis.set_ylim(0, 1)
        axis.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0))
        axis.set_ylabel("Annual share")
        axis.set_title(f"{SERIES_LABELS[series]} · top six departments within series", loc="left", fontweight="bold")
        add_panel_label(axis, chr(ord("a") + index))
    axes[-1].set_xticks(list(range(1988, 2027, 3)))
    plt.setp(axes[-1].get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    fig.suptitle("Department composition changes with machinery of government and source regime", x=0.08, ha="left", fontweight="bold")
    handles = list(legend_handles.values())
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.025), ncol=4, fontsize=5.5, frameon=False)
    fig.text(
        0.08,
        0.145,
        "Ministerial records use one official department. Multi-organisation policy records use stored fractional weights. Shares describe corpus composition, not climate salience.",
        fontsize=5.7,
        color="#555555",
    )
    fig.subplots_adjust(left=0.10, right=0.985, top=0.92, bottom=0.22, hspace=0.42)
    export_figure(fig, "04_department_annual_composition", list(axes), ["a", "b", "c"], column_groups=[["a", "b", "c"]])


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def build_report(
    baseline: dict[str, Any],
    time_tables: dict[str, pd.DataFrame],
    text_tables: dict[str, pd.DataFrame],
    department_tables: dict[str, pd.DataFrame],
    rates: pd.DataFrame,
    anomalies: pd.DataFrame,
    final_checks: dict[str, Any],
) -> str:
    distribution = text_tables["distribution"]
    scale = text_tables["scale"].set_index("series")
    dominance = text_tables["dominance"].set_index("series")
    presence = time_tables["presence"].set_index("series")
    peaks = department_tables["peaks"]

    def q(series: str, measure: str, quantile: str) -> int:
        value = distribution[
            (distribution["series"] == series)
            & (distribution["measure"] == measure)
            & (distribution["quantile"] == quantile)
        ]["value"].iloc[0]
        return int(round(float(value)))

    series_summary = markdown_table(
        ["Document genre", "Records", "Unique text segments", "Characters", "Median chars/record", "P90 chars/record", "Months with records", "Months without records"],
        [
            [
                SERIES_LABELS[series],
                f"{baseline[series]:,}",
                f"{int(scale.loc[series, 'unique_segment_count']):,}",
                f"{int(scale.loc[series, 'unique_character_count']):,}",
                f"{q(series, 'character_count', 'p50'):,}",
                f"{q(series, 'character_count', 'p90'):,}",
                f"{int(presence.loc[series, 'months_with_records']):,}",
                f"{int(presence.loc[series, 'months_without_records']):,}",
            ]
            for series in SERIES
        ],
    )
    baseline_table = markdown_table(
        ["Item", "Expected baseline", "Observed", "Result"],
        [
            [
                key,
                f"{EXPECTED_BASELINE[key]:,}",
                f"{int(baseline[key]):,}",
                "match" if int(baseline[key]) == EXPECTED_BASELINE[key] else "changed",
            ]
            for key in EXPECTED_BASELINE
        ],
    )
    anomaly_table = markdown_table(
        ["Source", "Interval", "Issue", "Count", "Unit", "Missing-record interpretation"],
        [
            [row.source, row.interval, row.issue, f"{int(row.count):,}", row.unit, row.missing_record_count]
            for row in anomalies.itertuples()
        ],
    )
    rate_table = markdown_table(
        ["Source", "Scope", "Metric", "Numerator / denominator", "Unit", "Rate"],
        [
            [row.source, row.series_scope, row.metric, f"{int(row.numerator):,} / {int(row.denominator):,}", row.unit, f"{row.percent:.2f}%"]
            for row in rates.itertuples()
        ],
    )
    peak_lines = []
    for department in ["DTI", "BERR", "BEIS"]:
        subset = peaks[(peaks["department"] == department) & (peaks["series"] == "ministerial_written_answer")]
        if not subset.empty:
            row = subset.iloc[0]
            peak_lines.append(
                f"{department} written-answer share peaks in {int(row['peak_year'])}: {row['fractional_record_count']:,.0f}/{int(row['series_year_records']):,} ({row['peak_share']:.1%})."
            )
    department_scale = text_tables["department_scale"]
    department_leaders = []
    for series in SERIES:
        row = department_scale[department_scale["series"] == series].sort_values("character_share_within_series", ascending=False).iloc[0]
        department_leaders.append(
            f"{SERIES_SHORT[series]}: {row['department']} carries {row['character_share_within_series']:.1%} of weighted characters."
        )

    policy_note = (
        f"The current {int(baseline['policy_document']):,} policy-source records comprise "
        f"{int(baseline['schema_policy_paper']):,} stored `policy_paper` rows plus "
        f"{int(baseline['schema_guidance_in_policy_source']):,} retained `guidance` row from the original frozen Search/API type mismatch; "
        "this report classifies all GOV.UK source records as the policy-source series without rewriting the stored type."
    )
    report = f"""# 补采后的政府语料分布与覆盖评估

统计快照：**{baseline['snapshot_at']}**；范围：**1988-01-01 至 2026-09-21**。本次分布刷新在定点修复提交完成后以只读模式打开数据库；本目录是新建交付，不覆盖上一轮证据。未清洗、未向量化、未修改 proposal。

## 1. 固定基线与口径

{baseline_table}

{policy_note}

三类文种始终分开：政策发布记录不是部长答复，部长声明也不并入答复。政策日期取可核验的发布日；部长答复取答复／坐席日；部长声明取声明日。库内三类记录均有日期，未用抓取时间填补。2026 年只统计到 9 月 21 日；Historic Hansard 的实际观察从 1988-01-11 开始。

{series_summary}

“字符数”和“片段数”是文本规模，不是独立观察数量。政策记录的 record-associated 片段合计比唯一片段多 **{int(scale.loc['policy_document', 'record_associated_segment_count'] - scale.loc['policy_document', 'unique_segment_count']):,}**，来自共享内容对象的多记录关联；报告总量使用唯一片段数。

## 2. 年代、年度、季度和月度分布

- `decade_distribution.csv`、`annual_distribution.csv`、`quarterly_distribution.csv` 和 `year_month_distribution.csv` 分别保留三类文种；年度零值只表示当前数据库没有观察记录。
- 三类文种中有记录月份分别为：政策 **{int(presence.loc['policy_document','months_with_records'])}**、答复 **{int(presence.loc['ministerial_written_answer','months_with_records'])}**、声明 **{int(presence.loc['ministerial_written_statement','months_with_records'])}**；这不是来源完成月数，完成状态另见第 3 节。
- 记录长度差异很大：政策字符中位数 **{q('policy_document','character_count','p50'):,}**，答复 **{q('ministerial_written_answer','character_count','p50'):,}**，声明 **{q('ministerial_written_statement','character_count','p50'):,}**。P99 分别为 **{q('policy_document','character_count','p99'):,}**、**{q('ministerial_written_answer','character_count','p99'):,}**、**{q('ministerial_written_statement','character_count','p99'):,}**。
- 少数超长记录的影响有限但不可忽略：各系列前 10 条记录占 record-associated 字符的比例分别为政策 **{pct(float(dominance.loc['policy_document','top_10_character_share']))}**、答复 **{pct(float(dominance.loc['ministerial_written_answer','top_10_character_share']))}**、声明 **{pct(float(dominance.loc['ministerial_written_statement','top_10_character_share']))}**。具体对象见 `top_20_longest_records.csv`。

![Annual distributions](figures/01_annual_distribution.png)

![Year-month heatmaps](figures/02_year_month_heatmaps.png)

## 3. 采集覆盖状态：与记录数量分开

状态图使用类别色，不把“索引失败”“未请求”“来源不支持”和“已确认零记录”画成同一种数值零。`coverage_status_by_source_month.csv` 同时保留每月记录数和不同异常单位。

![Collection coverage status](figures/03_collection_coverage_status.png)

重点缺口如下：

{anomaly_table}

- Historic Hansard volume 200 的真实日期范围是 **1991-12-02 至 1991-12-13**；替代日索引完整枚举 10 个开会日和 322 个条目，321 个已解析入库，1 个官方页因错接文本／归属不明已排除于可用语料。
- 官方 1988 年 1 月月历显示首个开会日为 **1988-01-11**，因此 1–10 日是休会边界而非采集缺口。批量 Commons 路线在 **2004-10-04** 后停止；Historic 日页在 2004 年第四季度仅提供 Lords 书面材料，不能替代 Commons。
- 2005–2010 的 85 个答复解析异常已有 83 个从保存的 HTTP-200 原文修复；Companies House 已由限定镜像恢复，Asda 因文本／部门归属不可可靠分离而排除。7 个声明候选已完成子项核验，不与答复异常相加。
- 2010-05-01 至 2014-09-11 仍是部分覆盖：原 20 个失败日期索引中 8 个日期取得镜像文件，12 个日期仍无匹配文件且记录数未知；225 个失败页面和 212 个未请求页面所涉日期均取得替代 XML，但这些原页面单位不与派生记录数相加。跨日期声明容器继续排除。
- GOV.UK 历史标签查询只在 DTI/DECC/BERR/DETR 可见组织标签内完成；UK DoE/MAFF 等前身路径未取得可靠总体分母，图中为“枚举不完整”，不是零政策。

## 4. 分层覆盖率

{rate_table}

每一率都保留自己的分母。特别是现代接口的 **174 个父 API 响应**与其中派生的 **65,988 条记录**从未混用为同一分母。枚举不完整的来源，成功子集的下载、文本和入库比例只描述已知目标，不能外推为历史全集覆盖率。

## 5. 部门与文种构成变化

![Department composition](figures/04_department_annual_composition.png)

- 新增长主要来自部长答复系列和新增官方来源，而非政策发布数量同比例增长。Historic Hansard、2005–2010 Hansard API／archive、2010–2014 publications archive 与 2014 后 Questions/Statements API 的记录单位和父证据结构不同。
- {' '.join(peak_lines)} DTI、BERR、BEIS 均为全主题部门材料，不能把这些年度峰值解释为气候关注度或恐惧表达变化。
- {' '.join(department_leaders)} 部门主导反映批准范围、部门存续与来源结构，也可能反映长文本；不构成主题结论。
- 政策、答复、声明的相对构成随来源交界明显改变。2004/2005、2010-05、2014-09 是方法边界：分别从批量卷册到逐条详情、再到 publications archive 派生记录、最后到父列表响应派生记录。跨边界比较必须带来源制度变量，不能直接把数量变化解释为话语变化。

## 6. 后续可用时间范围建议

### 政策发布记录

- **可继续进入清洗：** 已有文本的 {int(baseline['policy_document']):,} 条记录可按当前来源标签进入格式与正文识别；前轮四个指定 PDF 已用本地 OCR 恢复并保留页码映射，本轮新增 Cm 2428 的官方 194 页 PDF 文本层，其他原 06 对象级提取异常仍需单独标志。
- **部分覆盖：** 1988–2009 的历史政策只完成 GOV.UK 可见组织标签，不代表前身部门档案全集；1993 前零记录尤其不能作历史不存在解释。
- **候选比较区间：** 先在同一 GOV.UK 来源制度且月份状态可核验的区间内做描述性月／季度比较；是否与部长、新闻、公众层共窗，仍待其他来源确认。
- **下一轮最值补缺口：** UK DoE/MAFF/DETR 官方档案入口仍影响早期政策总体分母；本轮 OCR 已解决的四个对象不再列为缺口。

### 部长书面答复

- **可继续进入清洗：** 1988–2004 的有效卷册记录、volume 200 日页恢复的 321 条答复、2005–2010 的 23,988 个可用答复目标、2014-09-12 后现代接口记录，可进入来源感知清洗。
- **部分覆盖：** volume 200 有 1 个错接页面被排除，2005–2010 的 Companies House 已恢复、Asda 被排除；2004-10-05..12-31 接缝仍有 8 个日期×文种单位无匹配文件。2010-05-01..2014-09-11 仍有 12 个索引日期无匹配文件，不能声称连续覆盖。
- **候选比较区间：** 适合优先在各自稳定来源制度内做月／季度候选比较，例如 Historic Hansard 的有效卷册区间、2005-01 至 2010-04 的已知成功分区、2014-09-12 后现代接口；跨制度拼接需敏感性检查。
- **下一轮最值补缺口：** 优先为 12 个仍无镜像文件的索引日期寻找可核验官方／机构保存来源；原 225 个失败页面和 212 个未请求页面已在日期级替代 XML 中恢复，不应再按旧队列重复冲击。不能把这些不同层级直接相加为缺失记录数。

### 部长书面声明

- **可继续进入清洗：** 已入库且身份核验的 2,708 条声明可进入独立清洗，始终与答复分开。
- **部分覆盖：** Historic Hansard 仅保留档案明确提供的独立声明类别；2005–2010 的 7 个候选异常已完成子项核验并新增 3 个在范围内子声明，2010–2014 尚有 1 个跨日期容器未解决。缺少独立类别时不能把答复内讲话重分类成声明。
- **候选比较区间：** 2014-09-12 后现代 statements 接口最一致；更早时期只适合在各自来源定义内比较。
- **下一轮最值补缺口：** 9 个候选详情异常可改善已知候选判定，但不会自动证明早期声明系列完整。

共同结论：本轮总量足以支持后续来源感知清洗，但**不足以仅凭总量宣布 1988–2026 连续时间序列可比**。政策、部长话语与新闻／公众层的共同窗口仍需等待其他来源的分布与覆盖确认，由 Dai 决定是否补缺口。

## 7. 数值与视觉核对

- 年度、季度、月度、年代总数均与同一只读快照对齐：**{final_checks['time_reconciliation_passed']}**。
- 数据库大小与修改时间在读取前后不变：**{final_checks['database_stat_unchanged']}**；未执行全库哈希。
- 每项覆盖率分母为正、单位明确：**{final_checks['coverage_rate_denominators_valid']}**。
- 图表只使用对应 CSV 数据；源代码、对齐 JSON、PDF 字号与碰撞检查记录在 `qa/`。
"""
    return report


def build_html(report_summary: str, baseline: dict[str, Any], rates: pd.DataFrame) -> str:
    cards = "".join(
        f"<div class='card'><span>{html_lib.escape(SERIES_LABELS[key])}</span><strong>{int(baseline[key]):,}</strong></div>"
        for key in SERIES
    )
    rate_rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html_lib.escape(str(value))}</td>"
            for value in [row.source, row.metric, f"{int(row.numerator):,} / {int(row.denominator):,}", row.unit, f"{row.percent:.2f}%"]
        )
        + "</tr>"
        for row in rates.itertuples()
    )
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>补采后的政府语料分布与覆盖评估</title><style>
body{{font:15px/1.58 system-ui,-apple-system,sans-serif;color:#20303a;background:#f4f5f2;margin:0}}main{{max-width:1120px;margin:auto;padding:30px}}h1{{font-size:28px;margin-bottom:5px}}h2{{margin-top:34px;border-bottom:1px solid #ccd3d4;padding-bottom:6px}}.meta{{color:#5d6a70}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}}.card{{background:white;border:1px solid #d7ddde;padding:15px;border-radius:4px}}.card span{{display:block;color:#5d6a70}}.card strong{{font-size:27px;color:#24495F}}img{{width:100%;background:white;border:1px solid #d7ddde;margin:8px 0 20px}}table{{border-collapse:collapse;width:100%;background:white;font-size:12px}}th,td{{border:1px solid #d7ddde;padding:6px;text-align:right}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}.warn{{border-left:4px solid #B64342;background:#fff;padding:12px 15px}}code{{background:#e8ebea;padding:2px 4px}}a{{color:#24495F}}@media(max-width:760px){{.cards{{grid-template-columns:1fr}}main{{padding:16px;overflow-x:auto}}}}</style></head><body><main>
<h1>补采后的政府语料分布与覆盖评估</h1><p class='meta'>只读 06 数据库快照 · 1988-01-01 至 2026-09-21 · 2026 为部分年份</p><div class='cards'>{cards}</div>
<p class='warn'>政策、部长书面答复、部长书面声明是三个不同系列。记录数量与采集覆盖状态分开；未知目标数保留为未知。</p>
<h2>年度分布</h2><img src='figures/01_annual_distribution.svg' alt='三类文种年度分布'>
<h2>年月密度</h2><img src='figures/02_year_month_heatmaps.svg' alt='三类文种年月热图'>
<h2>采集覆盖状态</h2><img src='figures/03_collection_coverage_status.svg' alt='来源乘时间采集状态'>
<h2>部门年度构成</h2><img src='figures/04_department_annual_composition.svg' alt='部门年度构成'>
<h2>分层覆盖率</h2><table><thead><tr><th>来源</th><th>指标</th><th>分子 / 分母</th><th>单位</th><th>比例</th></tr></thead><tbody>{rate_rows}</tbody></table>
<h2>结论</h2><p>{html_lib.escape(report_summary)}</p><p>完整解释与建议见 <a href='government_corpus_distribution_coverage_report.md'>Markdown 报告</a>；CSV 文件位于本目录。</p>
</main></body></html>"""


def write_figure_contracts() -> None:
    text = """# Figure contracts

## Figure 1 — annual distributions

Core conclusion: The three genres have different scales and temporal profiles and must remain analytically separate.
Results-level question: How many records are observed per year in each genre?
Figure archetype: quantitative small-multiple grid.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: a policy records; b written answers; c written statements.
Evidence hierarchy: annual record counts are primary; partial-year shading is a boundary cue.
Reviewer risk: independent axes could be misread, so each panel is explicitly labelled and the footer states the rule.

## Figure 2 — year × month heatmaps

Core conclusion: Monthly density varies by genre and observed zero months are not coverage claims.
Results-level question: Where are the dense and sparse months within each genre?
Figure archetype: aligned heatmap small multiples.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: a policy; b answers; c statements.
Evidence hierarchy: within-genre pattern is primary; independent scales prevent the answer series from erasing policy variation.
Reviewer risk: scale differences and zero semantics are stated in titles/footer.

## Figure 3 — collection coverage status

Core conclusion: Source support, incomplete enumeration, failed known targets, unrequested targets and confirmed zero records are categorically different states.
Results-level question: Which source-month partitions are complete, partial, unrequested, unsupported or confirmed zero?
Figure archetype: categorical status matrix.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: one source × month matrix.
Evidence hierarchy: categorical status is primary; volume-200 annotation is a boundary case.
Reviewer risk: unknown record counts must not be converted to numeric zero.

## Figure 4 — department composition

Core conclusion: Department mix changes with machinery of government and source regime.
Results-level question: Which departments constitute each genre in each year?
Figure archetype: normalized stacked small multiples.
Target output: academic report, 183 mm wide.
Backend: Python/matplotlib.
Panel map: a policy; b answers; c statements.
Evidence hierarchy: annual fractional composition is primary; no topic or causal interpretation is made.
Reviewer risk: multi-organisation policy records use stored fractional weights, unlike one-department ministerial records.
"""
    (QA / "figure_contracts.md").write_text(text, encoding="utf-8")


def run() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    db_stat_before = {"size": DB.stat().st_size, "mtime_ns": DB.stat().st_mtime_ns}
    snapshot_at = utc_now()
    con = duckdb.connect(str(DB), read_only=True)
    con.execute("BEGIN TRANSACTION")
    try:
        documents = collect_documents(con)
        record_lengths = collect_record_lengths(con, documents)
        org_links = collect_organisation_links(con, documents)
        time_tables = build_time_tables(documents)
        text_tables = build_text_tables(con, record_lengths, org_links)
        department_tables = build_department_tables(org_links, documents)
        coverage_status, anomalies = build_coverage_status(con)
        baseline = {
            "snapshot_at": snapshot_at,
            "all_documents": int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]),
            "policy_document": int((documents["series"] == "policy_document").sum()),
            "ministerial_written_answer": int((documents["series"] == "ministerial_written_answer").sum()),
            "ministerial_written_statement": int((documents["series"] == "ministerial_written_statement").sum()),
            "text_segments": int(con.execute("SELECT COUNT(*) FROM text_segments").fetchone()[0]),
            "missing_dates": int(con.execute("SELECT COUNT(*) FROM documents WHERE publication_date IS NULL").fetchone()[0]),
            "schema_policy_paper": int(con.execute("SELECT COUNT(*) FROM documents WHERE content_type='policy_paper'").fetchone()[0]),
            "schema_guidance_in_policy_source": int(
                con.execute(
                    """SELECT COUNT(*) FROM documents d JOIN sources s USING(source_id)
                       WHERE s.source_name LIKE 'GOV.UK%' AND d.content_type='guidance'"""
                ).fetchone()[0]
            ),
        }
    finally:
        con.execute("ROLLBACK")
        con.close()

    rates = build_coverage_rates()
    preflight = {
        "generated_at": utc_now(),
        "source_snapshot": str(DB),
        "document_rows_in_range": int(len(documents)),
        "duplicate_document_ids": int(documents["document_id"].duplicated().sum()),
        "missing_publication_dates_in_selected_rows": int(documents["publication_date"].isna().sum()),
        "unexpected_series_rows": int((~documents["series"].isin(SERIES)).sum()),
        "negative_character_counts": int((record_lengths["character_count"] < 0).sum()),
        "negative_segment_counts": int((record_lengths["segment_count"] < 0).sum()),
        "invalid_fractional_weights": int(((org_links["fractional_count_weight"] < 0) | (org_links["fractional_count_weight"] > 1)).sum()),
        "coverage_status_values": sorted(coverage_status["status"].unique().tolist()),
    }
    preflight["passed"] = all(
        [
            preflight["duplicate_document_ids"] == 0,
            preflight["missing_publication_dates_in_selected_rows"] == 0,
            preflight["unexpected_series_rows"] == 0,
            preflight["negative_character_counts"] == 0,
            preflight["negative_segment_counts"] == 0,
            preflight["invalid_fractional_weights"] == 0,
            set(preflight["coverage_status_values"]).issubset(set(STATUS_ORDER)),
        ]
    )
    write_json(QA / "source_data_preflight.json", preflight)
    if not preflight["passed"]:
        raise RuntimeError(f"Source-data preflight failed: {preflight}")
    for name, frame in [
        ("baseline_check.csv", pd.DataFrame([{"metric": key, "expected": EXPECTED_BASELINE.get(key), "observed": value, "match": EXPECTED_BASELINE.get(key) == value if key in EXPECTED_BASELINE else None} for key, value in baseline.items()])),
        ("decade_distribution.csv", time_tables["decades"]),
        ("annual_distribution.csv", time_tables["annual"]),
        ("quarterly_distribution.csv", time_tables["quarterly"]),
        ("year_month_distribution.csv", time_tables["monthly"]),
        ("month_presence_summary.csv", time_tables["presence"]),
        ("text_scale_by_series.csv", text_tables["scale"]),
        ("record_text_length_distribution.csv", text_tables["distribution"]),
        ("top_20_longest_records.csv", text_tables["top"]),
        ("long_record_dominance.csv", text_tables["dominance"]),
        ("text_scale_by_department.csv", text_tables["department_scale"]),
        ("department_annual_composition.csv", department_tables["annual"]),
        ("dti_berr_beis_peak_shares.csv", department_tables["peaks"]),
        ("coverage_status_by_source_month.csv", coverage_status),
        ("coverage_anomaly_summary.csv", anomalies),
        ("coverage_rates.csv", rates),
    ]:
        write_csv(OUT / name, frame)

    configure_plotting()
    plot_annual(time_tables["annual"])
    plot_month_heatmaps(time_tables["monthly"])
    plot_coverage_status(coverage_status)
    plot_department_composition(department_tables["annual"])
    write_figure_contracts()

    db_stat_after = {"size": DB.stat().st_size, "mtime_ns": DB.stat().st_mtime_ns}
    series_totals = time_tables["annual"].groupby("series")["record_count"].sum().to_dict()
    quarter_totals = time_tables["quarterly"].groupby("series")["record_count"].sum().to_dict()
    month_totals = time_tables["monthly"].groupby("series")["record_count"].sum().to_dict()
    decade_totals = time_tables["decades"].groupby("series")["record_count"].sum().to_dict()
    checks = {
        "generated_at": utc_now(),
        "database_opened_read_only": True,
        "database_stat_before": db_stat_before,
        "database_stat_after": db_stat_after,
        "database_stat_unchanged": db_stat_before == db_stat_after,
        "baseline_matches_expected": all(int(baseline[key]) == expected for key, expected in EXPECTED_BASELINE.items()),
        "annual_totals": series_totals,
        "quarter_totals": quarter_totals,
        "month_totals": month_totals,
        "decade_totals": decade_totals,
        "time_reconciliation_passed": series_totals == quarter_totals == month_totals == decade_totals,
        "coverage_rate_denominators_valid": bool((rates["denominator"] > 0).all()),
        "coverage_status_rows": int(len(coverage_status)),
        "coverage_status_expected_rows": int(len(MONTHS) * coverage_status["source"].nunique()),
        "coverage_status_grid_complete": len(coverage_status) == len(MONTHS) * coverage_status["source"].nunique(),
        "figures_exist": all((FIGURES / f"{stem}.{extension}").exists() for stem in ["01_annual_distribution", "02_year_month_heatmaps", "03_collection_coverage_status", "04_department_annual_composition"] for extension in ["svg", "pdf", "png"]),
        "full_database_hash_rerun": False,
    }
    checks["passed"] = all(
        [
            checks["database_stat_unchanged"],
            checks["baseline_matches_expected"],
            checks["time_reconciliation_passed"],
            checks["coverage_rate_denominators_valid"],
            checks["coverage_status_grid_complete"],
            checks["figures_exist"],
        ]
    )
    write_json(OUT / "final_checks.json", checks)
    report = build_report(baseline, time_tables, text_tables, department_tables, rates, anomalies, checks)
    (OUT / "government_corpus_distribution_coverage_report.md").write_text(report, encoding="utf-8")
    summary = (
        "历史补缺后的分布已按最终数据库刷新。Companies House 和所有已匹配日期的镜像 XML 已恢复；Asda、Self-regulating Bodies 与跨日期声明容器按证据边界排除。2004-Q4 仍有 8 个日期×文种单位、2010–2014 仍有 12 个索引日期无匹配文件，早期政策总体分母仍未知。"
    )
    (OUT / "index.html").write_text(build_html(summary, baseline, rates), encoding="utf-8")
    result = {"output_directory": str(OUT), "baseline": baseline, "checks": checks}
    write_json(OUT / "report_summary.json", result)
    manifest_rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "delivery_manifest.csv" and "collision-audit.pdf" not in path.name:
            manifest_rows.append(
                {
                    "path": str(path.relative_to(OUT)),
                    "bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                }
            )
    write_csv(OUT / "delivery_manifest.csv", manifest_rows)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
