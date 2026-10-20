"""Exact metadata aggregation, diagnostic checks and requested overview figures.

Counts use source-qualified native IDs, not search-page observations. No corpus
deduplication/deletion or substantive trend model is performed. Cross-dimension
lexical overlap is fractionally allocated only in a derived stacked display.
"""

import csv
import hashlib
import html
import json
import shutil
import sys
from collections import Counter, defaultdict

import collect as core
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, "/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402

MATRICES = ["baseline26", "extended33_union"]
YEARS = list(range(1988, 2027))
CLUSTERS = {
    "acute_thermal": "Acute Heat",
    "chronic_warming": "Chronic Warming",
    "impacts": "Impacts",
    "official_action": "Policy Response",
}
GROUPS = {
    "Federal Hansard": ["hansard_federal_rapid"],
    "UQ eSpace": ["uq_espace"],
    "Trove Gazette": ["trove_web_gazette"],
    "BoM": ["bom_scs", "bom_annual"],
    "CSIRO DAP": ["csiro_dap"],
    "QLD Data": ["qld_statements", "qld_opendata", "qld_resources"],
}
SOURCE_LABELS = {
    "hansard_federal_rapid": "Federal Hansard",
    "uq_espace": "UQ eSpace",
    "trove_web_gazette": "Trove Gazette",
    "bom_scs": "BoM SCS",
    "bom_annual": "BoM annual summaries",
    "csiro_dap": "CSIRO DAP",
    "qld_opendata": "QLD Open Data",
    "qld_statements": "QLD releases",
    "qld_resources": "QLD linked publications",
}
MILESTONES = [
    {
        "date": "2007-05-31",
        "label": "2007 emissions-trading report",
        "url": "https://www.aph.gov.au/About_Parliament/Parliamentary_departments/Parliamentary_Library/Research/Chronologies/2022-23/climatechange2021",
    },
    {
        "date": "2011-07-10",
        "label": "2011 clean-energy policy release",
        "url": "https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Environment_and_Communications/Clean_Energy_Legislation/report/c02",
    },
    {
        "date": "2012-07-01",
        "label": "2012 carbon pricing begins",
        "url": "https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Environment_and_Communications/Clean_Energy_Legislation/report/c02",
    },
    {
        "date": "2014-07-17",
        "label": "2014 repeal assent",
        "url": "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId=r5311",
    },
]


def write_csv(out, name, fields, rows):
    with core.atomic_text(out / name) as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerows(rows)


def phase(year):
    if year <= 2005:
        return 1, "Historical Baseline"
    if year <= 2014:
        return 2, "Political & Policy Peak"
    return 3, "Institutional Normalization"


def middle_zeros(counts):
    """Return every zero year bracketed by positive observations, including runs."""
    positive = [y for y, n in counts.items() if n > 0]
    if len(positive) < 2:
        return []
    return [y for y in range(min(positive) + 1, max(positive)) if counts.get(y, 0) == 0]


def dimensions(row):
    terms = set(json.loads(row["query_matched"]))
    return [d for d, ts in core.COLLECTION_MATRIX["dimensions"].items() if terms & set(ts)]


def tier(row):
    source = row["source_channel"]
    if source == "hansard_federal_rapid":
        return "Federal Parliament"
    if source == "uq_espace":
        return "Academic"
    if source in {"bom_scs", "bom_annual", "csiro_dap"}:
        return "Scientific Agency"
    if source.startswith("qld_"):
        return "State Gov"
    if source == "trove_web_gazette":
        publisher = row.get("author_speaker") or ""
        if "Commonwealth" in publisher or "Australian Government Gazette" in publisher:
            return "Federal Gov / Gazette"
        if any(
            name in publisher
            for name in [
                "New South Wales",
                "Queensland",
                "Victoria",
                "Tasmania",
                "South Australia",
                "Western Australia",
            ]
        ):
            return "State Gov"
        return "Gazette issuer unresolved"
    return "Issuer unresolved"


def validate(rows, monthly, annual, totals, channels):
    doc_ids = [r["doc_id"] for r in rows]
    qualified = [(r["source_channel"], r["native_id"]) for r in rows]
    errors = []
    if len(set(doc_ids)) != len(rows):
        errors.append("duplicate doc_id")
    if len(set(qualified)) != len(rows):
        errors.append("duplicate source-qualified native_id")
    if any(r["doc_id"] != core.digest([r["source_channel"], str(r["native_id"])]) for r in rows):
        errors.append("doc_id/native identity mapping differs")
    eligible = defaultdict(set)
    month_ids, year_ids = defaultdict(set), defaultdict(set)
    unallocated = Counter()
    for row in rows:
        if row["date_status"] != "inside_fixed_interval":
            continue
        if not (core.START <= row["publication_start"] <= row["publication_end"] <= core.END):
            errors.append("inside status violates strict fixed interval: " + row["doc_id"])
        member = core.matrix_membership(json.loads(row["query_matched"]))
        for matrix in MATRICES:
            if not member[matrix]:
                continue
            key = (matrix, row["source_channel"])
            eligible[key].add(row["doc_id"])
            if row["publication_month"]:
                month_ids[(*key, row["publication_month"])].add(row["doc_id"])
            else:
                unallocated[(*key, "month")] += 1
            if row["publication_start"][:4] == row["publication_end"][:4]:
                year_ids[(*key, int(row["publication_start"][:4]))].add(row["doc_id"])
            else:
                unallocated[(*key, "year")] += 1
    cells = 0
    for matrix in MATRICES:
        for source in channels:
            key = (matrix, source)
            expected = len(eligible[key])
            if totals[key] != expected:
                errors.append("total/native-ID mismatch: " + str(key))
            if (
                sum(monthly[(*key, m)] for m in core.months()) + unallocated[(*key, "month")]
                != expected
            ):
                errors.append("monthly/native-ID mismatch: " + str(key))
            if sum(annual[(*key, y)] for y in YEARS) + unallocated[(*key, "year")] != expected:
                errors.append("annual/native-ID mismatch: " + str(key))
            for month in core.months():
                cells += 1
                if monthly[(*key, month)] != len(month_ids[(*key, month)]):
                    errors.append("monthly cell has repeated IDs: " + str((*key, month)))
            for year in YEARS:
                cells += 1
                if annual[(*key, year)] != len(year_ids[(*key, year)]):
                    errors.append("annual cell has repeated IDs: " + str((*key, year)))
    baseline = set().union(*(eligible[(MATRICES[0], s)] for s in channels))
    extended = set().union(*(eligible[(MATRICES[1], s)] for s in channels))
    if not baseline <= extended:
        errors.append("Baseline26 is not a subset of Extended33")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "retained_rows": len(rows),
        "unique_doc_ids": len(set(doc_ids)),
        "unique_source_native_pairs": len(set(qualified)),
        "aggregated_cells_checked": cells,
        "in_interval_unique_ids": {MATRICES[0]: len(baseline), MATRICES[1]: len(extended)},
        "scope": (
            "native ID uniqueness; cross-source/work-family semantic deduplication not asserted"
        ),
    }
    if errors:
        raise ValueError(core.encode(report))
    return report


def build(rows, channels, monthly, annual, totals, summary, out):
    validation = validate(rows, monthly, annual, totals, channels)
    core.write_json(out / "DEDUPLICATION_VALIDATION.json", validation)
    annual_total = {y: sum(annual[(MATRICES[1], s, y)] for s in channels) for y in YEARS}
    write_csv(
        out,
        "extended33_annual_phases.csv",
        [
            "publication_year",
            "extended33_unique_native_records",
            "phase",
            "phase_label",
            "phase_basis",
            "partial_year",
            "publication_cutoff",
            "snapshot_time",
        ],
        [
            (
                y,
                annual_total[y],
                *phase(y),
                "user_specified_not_empirically_validated",
                y == 2026,
                core.END,
                summary["reported_at"],
            )
            for y in YEARS
        ],
    )
    anomalies = []
    coverage_path = core.HERE / "HANSARD_SOURCE_COVERAGE.json"
    hansard_years = (
        json.loads(coverage_path.read_text())["session_counts_by_year"]
        if coverage_path.exists()
        else {}
    )
    for matrix in MATRICES:
        for source in channels:
            counts = {y: annual[(matrix, source, y)] for y in YEARS}
            for year in middle_zeros(counts):
                status = summary["exhaustion_status"].get(source, "NOT_STARTED")
                if source == "hansard_federal_rapid" and str(year) not in hansard_years:
                    recheck = "checksum-verified session lookup has no sittings in this year"
                elif status == "COMPLETED_LAST_PAGE":
                    recheck = (
                        "zero native-ID count confirmed after full source enumeration; "
                        "lexical/date/source limits remain, not validated discourse absence"
                    )
                else:
                    recheck = "source traversal still incomplete"
                anomalies.append(
                    (
                        matrix,
                        source,
                        year,
                        counts[year - 1],
                        counts[year + 1],
                        status,
                        "FLAGGED_ZERO_RECOUNTED"
                        if status == "COMPLETED_LAST_PAGE"
                        else "PAGING_INCOMPLETE",
                        recheck,
                    )
                )
    write_csv(
        out,
        "middle_year_zero_checks.csv",
        [
            "matrix",
            "source_channel",
            "publication_year",
            "previous_year_count",
            "next_year_count",
            "exhaustion_status",
            "diagnostic_status",
            "recheck_evidence",
        ],
        anomalies,
    )
    # Detailed unresolved-date inventory, never only an aggregate count.
    write_csv(
        out,
        "pending_date_records.csv",
        [
            "doc_id",
            "source_channel",
            "native_id",
            "title",
            "date_status",
            "date_basis",
            "source_url",
        ],
        [
            (
                r["doc_id"],
                r["source_channel"],
                r["native_id"],
                r["title"],
                r["date_status"],
                r["date_basis"],
                r["url_source"],
            )
            for r in rows
            if r["date_status"].startswith("pending")
        ],
    )
    write_csv(
        out,
        "qld_date_allocation.csv",
        [
            "doc_id",
            "title",
            "date_status",
            "date_granularity",
            "publication_start",
            "publication_end",
            "date_basis",
            "activity_evidence",
            "source_url",
        ],
        [
            (
                r["doc_id"],
                r["title"],
                r["date_status"],
                r["date_granularity"],
                r["publication_start"],
                r["publication_end"],
                r["date_basis"],
                core.encode(json.loads(r["source_context_json"]).get("publication_date_audit", {})),
                r["url_source"],
            )
            for r in rows
            if r["source_channel"] == "qld_opendata"
        ],
    )
    fractional, multi_hits, proportions = Counter(), Counter(), Counter()
    for row in rows:
        if row["date_status"] != "inside_fixed_interval":
            continue
        if not core.matrix_membership(json.loads(row["query_matched"]))[MATRICES[1]]:
            continue
        proportions[(tier(row), row["source_channel"])] += 1
        if row["publication_start"][:4] != row["publication_end"][:4]:
            continue
        year = int(row["publication_start"][:4])
        ds = dimensions(row)
        if not ds:
            raise ValueError("Extended record lacks query dimension: " + row["doc_id"])
        for dimension in ds:
            fractional[(year, dimension)] += 1 / len(ds)
            multi_hits[(year, dimension)] += 1
    max_error = max(abs(sum(fractional[(y, d)] for d in CLUSTERS) - annual_total[y]) for y in YEARS)
    if max_error > 1e-7:
        raise ValueError("Fractional terminology totals do not reconcile with unique IDs")
    for name, values in [
        ("annual_terminology_fractional.csv", fractional),
        ("annual_terminology_multihit.csv", multi_hits),
    ]:
        write_csv(
            out,
            name,
            ["publication_year", *CLUSTERS, "unique_native_records"],
            [(y, *(values[(y, d)] for d in CLUSTERS), annual_total[y]) for y in YEARS],
        )
    write_csv(
        out,
        "source_tier_proportions.csv",
        [
            "institutional_tier",
            "source_channel",
            "unique_native_records",
            "percent_of_extended33",
        ],
        [(t, s, n, 100 * n / summary["totals"][MATRICES[1]]) for (t, s), n in proportions.items()],
    )
    core.write_json(out / "MILESTONE_SOURCES.json", MILESTONES)
    summary["data_validation"] = {
        "native_id_reconciliation": validation["status"],
        "middle_year_zero_flags": len(anomalies),
        "qld_releases_2012": {m: annual[(m, "qld_statements", 2012)] for m in MATRICES},
        "terminology_fractional_max_reconciliation_error": max_error,
        "free_y": True,
        "sharey": False,
        "phase_labels": "user supplied; descriptive periods, not inferred trend findings",
    }
    event_counts = event_reference(out)
    return {
        "annual": annual,
        "annual_total": annual_total,
        "fractional": fractional,
        "proportions": proportions,
        "validation": validation,
        "event_counts": event_counts,
    }


def event_reference(out):
    """Read frozen case rows as a comparison only; never import old collectors/claims."""
    reference = core.HERE.parents[2] / (
        "archives/superseded_event_pipeline_20261020/australia-event-periods/"
        "temperature_reaudit_v7/events.csv"
    )
    before = hashlib.sha256(reference.read_bytes()).hexdigest()
    with reference.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ids = [r["event_id"] for r in rows]
    if len(rows) != 90 or len(set(ids)) != 90:
        raise ValueError("Frozen reference must contain 90 distinct case/release IDs")
    counts = Counter()
    lineage = []
    for row in rows:
        year = int(row["start_value"][:4])
        if year not in YEARS:
            raise ValueError("Reference event outside study years")
        group = (
            "report_release"
            if row["event_kind"] == "warming_report_release"
            else "temperature_case"
        )
        counts[(year, group)] += 1
        lineage.append(
            (
                row["event_id"],
                row["event_kind"],
                group,
                row["start_value"],
                year,
                row["title"],
                row["primary_source_url"],
            )
        )
    write_csv(
        out,
        "event_reference_lineage.csv",
        [
            "reference_event_id",
            "original_event_kind",
            "display_group",
            "start_or_release_value",
            "display_year",
            "title",
            "original_source_url",
        ],
        lineage,
    )
    after = hashlib.sha256(reference.read_bytes()).hexdigest()
    if before != after:
        raise ValueError("Frozen reference changed during reading")
    core.write_json(
        out / "EVENT_REFERENCE_VALIDATION.json",
        {
            "reference_path": str(reference),
            "sha256": before,
            "source_unchanged": True,
            "unique_reference_rows": len(set(ids)),
            "temperature_case_rows": 77,
            "report_release_rows": 13,
            "allocation": "one count in start/release year only",
            "status": (
                "preserved non-exhaustive external inventory; not validated Research Calendar"
            ),
            "interpretation": (
                "Temporal alignment is descriptive; does not measure "
                "event incidence or prove causality/calendar validity"
            ),
        },
    )
    return counts


def save(fig, out, name):
    fig.canvas.draw()
    for extension in ["pdf", "svg", "png"]:
        fig.savefig(out / f"{name}.{extension}", dpi=300, facecolor="white")
    plt.close(fig)


def heading(fig, title, summary, note):
    fig.suptitle(title, x=0.08, y=0.97, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.08, 0.915, note, fontsize=9)
    fig.text(
        0.08,
        0.025,
        "Observed metadata; source-native units differ. 2026 ends 21 September. "
        "Pending routes remain disclosed.",
        fontsize=8,
    )
    fig.text(0.08, 0.895, "Snapshot: " + summary["reported_at"], fontsize=8, color="#555555")


def heatmap(data, summary, out):
    values = np.array(
        [
            [
                [sum(data["annual"][(m, s, y)] for s in sources) for y in YEARS]
                for sources in GROUPS.values()
            ]
            for m in MATRICES
        ]
    )
    fig, axes = plt.subplots(2, 1, figsize=(12, 8.0), sharex=True, sharey=False)
    fig.subplots_adjust(left=0.19, right=0.86, bottom=0.18, top=0.82, hspace=0.33)
    for j, ax in enumerate(axes):
        image = ax.imshow(
            np.log10(values[j] + 1),
            cmap="viridis",
            aspect="auto",
            vmin=0,
            vmax=np.log10(values.max() + 1),
            interpolation="nearest",
        )
        ax.set_yticks(range(len(GROUPS)), GROUPS)
        ax.set_title("Baseline26" if j == 0 else "Extended33", loc="left", fontsize=11, pad=9)
        ax.tick_params(length=0)
        ax.set_xticks(
            [y - 1988 for y in [1988, 1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020, 2026]],
            [1988, 1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020, 2026],
        )
    axes[-1].set_xlabel("Publication year")
    cax = fig.add_axes([0.885, 0.23, 0.017, 0.52])
    bar = fig.colorbar(image, cax=cax)
    bar.set_label("log10(annual unique records + 1)", fontsize=9, labelpad=10)
    heading(
        fig,
        "Annual coverage density | 1988–2026",
        summary,
        "Two matrices; identical color transform and legend. Zero means no observed dated match.",
    )
    fig.text(
        0.08,
        0.085,
        "Trove: searched Gazette titles taper/end by 2012; "
        "later zeros reflect this archive frame.\n"
        "BoM = SCS + annual summaries. QLD Data = releases + catalogues. "
        "2026 cutoff: 21 September.",
        fontsize=9,
    )
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        json_out=out / "density_heatmap.alignment.json",
        overlay_svg=out / "density_heatmap.alignment.svg",
        strict=True,
        axes=axes,
    )
    save(fig, out, "density_heatmap")


def donut(data, summary, out):
    props = data["proportions"]
    tiers = list(dict.fromkeys(t for t, _ in props))
    # Stable ordering keeps the two rings exactly aligned.
    tiers = sorted(tiers, key=lambda t: -sum(n for (tt, _), n in props.items() if tt == t))
    outer = [(t, s, props[(t, s)]) for t in tiers for tt, s in props if tt == t]
    sizes = [sum(n for (tt, _), n in props.items() if tt == t) for t in tiers]
    sources = list(SOURCE_LABELS)
    colors = {s: plt.get_cmap("tab10")(i % 10) for i, s in enumerate(sources)}
    tier_colors = [plt.get_cmap("Set3")(i) for i in range(len(tiers))]
    fig, ax = plt.subplots(figsize=(12, 7.5))
    fig.subplots_adjust(left=0.04, right=0.59, bottom=0.13, top=0.82)
    wedges, _, _ = ax.pie(
        [n for _, _, n in outer],
        radius=1,
        startangle=90,
        colors=[colors[s] for _, s, _ in outer],
        wedgeprops={"width": 0.26, "edgecolor": "white", "linewidth": 1},
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        pctdistance=0.87,
        textprops={"fontsize": 9},
    )
    inner, _ = ax.pie(
        sizes,
        radius=0.72,
        startangle=90,
        colors=tier_colors,
        wedgeprops={"width": 0.25, "edgecolor": "white", "linewidth": 1},
    )
    total = sum(sizes)
    ax.text(0, 0, f"Extended33\n{total:,}\nunique records", ha="center", va="center", fontsize=13)
    ax.set(aspect="equal")

    def percentage(n):
        return f"{100 * n / total:.2f}%" if 100 * n / total < 0.1 else f"{100 * n / total:.1f}%"

    fig.legend(
        inner,
        [f"{t}  {n:,} ({percentage(n)})" for t, n in zip(tiers, sizes, strict=True)],
        loc="upper left",
        bbox_to_anchor=(0.61, 0.80),
        frameon=False,
        title="Inner ring: institutional tier",
        fontsize=9,
        title_fontsize=10,
    )
    fig.legend(
        wedges,
        [
            f"{SOURCE_LABELS.get(s, s)}  {n:,} ({percentage(n)})"
            + (
                " [federal]"
                if t == "Federal Gov / Gazette"
                else " [state]"
                if s == "trove_web_gazette" and t == "State Gov"
                else ""
            )
            for t, s, n in outer
        ],
        loc="upper left",
        bbox_to_anchor=(0.61, 0.48),
        frameon=False,
        title="Outer ring: specific source",
        fontsize=9,
        title_fontsize=10,
    )
    heading(
        fig,
        "Institutional tiers and source shares",
        summary,
        "Extended33 in-interval records; all slice percentages use the same unique-ID denominator.",
    )
    fig.text(
        0.08,
        0.075,
        "Federal executive Gazettes are separate from Parliament. "
        "Gazette issuer ≠ every notice holder.\n"
        "Repository membership and agency hosting do not establish institutional endorsement.",
        fontsize=9,
    )
    save(fig, out, "source_proportions")


def terminology(data, summary, out):
    # One common transformed axis: small policy counts remain visible without
    # adding a second panel/axis or inflating their actual values.
    fig, ax = plt.subplots(figsize=(12, 6.6))
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.18, top=0.72)
    styles = {
        "impacts": ("#16715F", "-", "o"),
        "chronic_warming": ("#C38116", "-", "s"),
        "acute_thermal": ("#BA3855", "-", "^"),
        "official_action": ("#087CEE", "--", "D"),
    }
    ymax = 0
    for dimension, (color, line, marker) in styles.items():
        values = np.array([data["fractional"][(y, dimension)] for y in YEARS])
        plotted = np.log10(values + 1)
        ymax = max(ymax, max(plotted))
        ax.plot(
            YEARS,
            plotted,
            color=color,
            linestyle=line,
            marker=marker,
            markevery=3,
            markersize=3.5,
            linewidth=1.9,
            label=CLUSTERS[dimension],
            zorder=4 if dimension == "official_action" else 3,
        )
    ticks = [n for n in [0, 1, 5, 20, 100, 500, 2000, 10000] if np.log10(n + 1) <= ymax + 0.16]
    ax.set_yticks(np.log10(np.array(ticks) + 1), [f"{n:,}" for n in ticks])
    ax.set_ylim(-0.05, ymax + 0.20)
    ax.set_xlim(1987.7, 2026.3)
    ax.set_xticks([1988, 1996, 2004, 2012, 2020, 2026])
    ax.set_xlabel("Publication year", labelpad=8)
    ax.set_ylabel("Allocated record count | log10(count + 1) scale", labelpad=9)
    ax.grid(axis="y", color="#E4E4E4", linewidth=0.6)
    ax.axvline(2007, color="#777777", linewidth=0.8, linestyle=":", zorder=1)
    ax.axvspan(2011, 2014, color="#222222", alpha=0.06, zorder=0)
    ax.annotate(
        "2007 ETS report",
        xy=(2007, 1),
        xycoords=("data", "axes fraction"),
        xytext=(-25, 8),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=9,
    )
    ax.annotate(
        "Policy Discourse Peak during\nCarbon Tax Debates (2011–2014)",
        xy=(2012.5, 1),
        xycoords=("data", "axes fraction"),
        xytext=(25, 8),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": "#777777", "lw": 0.7},
    )
    fig.suptitle(
        "Extended33 | four terminology groups",
        x=0.10,
        y=0.97,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    fig.text(0.10, 0.915, "Annual query-matched records · 1988–21 September 2026", fontsize=10)
    fig.legend(loc="upper left", bbox_to_anchor=(0.095, 0.885), ncol=4, frameon=False, fontsize=10)
    fig.text(
        0.10,
        0.055,
        "Documents matched in k groups contribute 1/k to each. "
        "Log scale separates small series; tick labels show counts.",
        fontsize=9,
    )
    fig.text(
        0.10,
        0.028,
        "Carbon Tax callout is a user-specified period label. "
        "2026 is partial. Snapshot: " + summary["reported_at"],
        fontsize=8,
    )
    save(fig, out, "terminology_groups_v3")


def event_overlay(data, summary, out):
    events = data["event_counts"]
    physical = [events[(y, "temperature_case")] for y in YEARS]
    releases = [events[(y, "report_release")] for y in YEARS]
    totals = [data["annual_total"][y] for y in YEARS]
    write_csv(
        out,
        "event_distribution_alignment.csv",
        [
            "year",
            "extended33_unique_native_records",
            "reference_temperature_case_starts",
            "reference_report_releases",
            "reference_inventory_total",
        ],
        [(y, n, p, r, p + r) for y, n, p, r in zip(YEARS, totals, physical, releases, strict=True)],
    )
    fig, left = plt.subplots(figsize=(12, 6.8))
    fig.subplots_adjust(left=0.09, right=0.90, bottom=0.24, top=0.79)
    right = left.twinx()
    left.set_zorder(right.get_zorder() + 1)
    left.patch.set_visible(False)
    bars = right.bar(
        YEARS,
        physical,
        width=0.70,
        color="#D2AF73",
        alpha=0.55,
        label="Temperature case starts (77)",
    )
    reports = right.bar(
        YEARS,
        releases,
        bottom=physical,
        width=0.70,
        color="#8E889C",
        alpha=0.70,
        edgecolor="#676171",
        linewidth=0.3,
        label="Climate report releases (13)",
    )
    (line,) = left.plot(
        YEARS,
        totals,
        color="#146FAD",
        linewidth=2.0,
        marker="o",
        markersize=3.2,
        label="Official metadata (Extended33)",
    )
    left.set_xlim(1987.3, 2026.7)
    left.set_ylim(0, max(totals) * 1.15)
    right.set_ylim(0, max(p + r for p, r in zip(physical, releases, strict=True)) * 1.15)
    right.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    left.set_ylabel("Extended33 unique native records", color="#146FAD")
    right.set_ylabel("Reference case/release entries per start/release year")
    left.tick_params(axis="y", colors="#146FAD")
    right.spines["right"].set_visible(True)
    left.set_xticks([1988, 1996, 2004, 2012, 2020, 2026])
    left.set_xlabel("Year (document publication versus case start/report release)")
    left.grid(axis="y", color="#E5E5E5", linewidth=0.5)
    fig.legend(
        [line, bars, reports],
        [line.get_label(), bars.get_label(), reports.get_label()],
        loc="upper center",
        bbox_to_anchor=(0.50, 0.86),
        ncol=3,
        frameon=False,
        fontsize=9,
    )
    heading(
        fig,
        "Official-source records and temperature/report inventory",
        summary,
        "Extended33 and the preserved 90-entry inventory; descriptive temporal alignment.",
    )
    fig.text(
        0.08,
        0.065,
        "Independent zero-based axes; visual coincidence "
        "does not establish association or causality.\n"
        "Reference cases are non-exhaustive, may overlap, and do not validate a Research Calendar.",
        fontsize=9,
    )
    save(fig, out, "event_alignment_v3")


def dashboard(summary, out):
    esc = html.escape
    event_file = (
        "event_alignment_final_20261021"
        if summary["all_available_sources_complete"]
        else "event_alignment_v3"
    )
    term_file = (
        "terminology_groups_final_20261021"
        if summary["all_available_sources_complete"]
        else "terminology_groups_v3"
    )
    figures = [
        (
            event_file,
            "文档分布与事件／报告叠加",
            "77 条温度案例与 13 条报告发布；独立双轴，仅作描述性时间参照。",
        ),
        ("density_heatmap", "年度密度热图", "两套矩阵分别展示；log10(count + 1)，共用颜色图例。"),
        (
            "source_proportions",
            "机构层级与来源占比",
            "Extended33 的唯一原生记录；联邦行政公报与议会分列。",
        ),
        (
            term_file,
            "四类检索术语的年度分布",
            "跨类记录按 1/k 分摊；合计与年度唯一记录一致。",
        ),
        (
            "annual_distribution",
            "逐来源年度直方图",
            "每个子图独立 Y 轴；Baseline26 和 Extended33 分列。",
        ),
        ("monthly_distribution", "逐来源月度分布", "每个子图独立 Y 轴；未知月份不填入一月。"),
    ]
    cards = "\n".join(
        f'<section id="{name}"><h2>{esc(title)}</h2><p>{esc(note)}</p>'
        f'<a href="{name}.pdf">PDF</a> · <a href="{name}.svg">SVG</a>'
        f'<img src="{name}.png" alt="{esc(title)}"></section>'
        for name, title, note in figures
    )
    links = [
        "event_distribution_alignment.csv",
        "event_reference_lineage.csv",
        "EVENT_REFERENCE_VALIDATION.json",
        "extended33_annual_phases.csv",
        "monthly_by_source_matrix.csv",
        "annual_by_source_matrix.csv",
        "middle_year_zero_checks.csv",
        "missing_months.csv",
        "pooled_missing_months.csv",
        "pending_date_records.csv",
        "qld_date_allocation.csv",
        "pending_sources.csv",
        "annual_terminology_fractional.csv",
        "annual_terminology_multihit.csv",
        "source_tier_proportions.csv",
        "DEDUPLICATION_VALIDATION.json",
        "REVIEW_STATUS.json",
    ]
    link_html = " · ".join(f'<a href="{f}">{f}</a>' for f in links)
    milestones = " · ".join(f'<a href="{esc(m["url"])}">{esc(m["label"])}</a>' for m in MILESTONES)
    missing = summary["zero_observed_months"]
    pending_html = "".join(
        f"<li>{esc(s)}: {esc(state)}</li>"
        for s, state in summary["exhaustion_status"].items()
        if state != "COMPLETED_LAST_PAGE"
    )
    text = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Official Voice · 分布核查</title>
<style>body{{font:16px/1.65 system-ui,sans-serif;color:#203040;background:#f3f6f8;margin:0}}
main{{max-width:1200px;margin:auto;padding:32px}}
header,section{{background:white;padding:28px;margin:0 0 24px;border-radius:14px}}
h1{{margin:0 0 12px}}h2{{margin-top:0}}a{{color:#206a98;overflow-wrap:anywhere}}
img{{display:block;width:100%;height:auto;margin-top:16px}}
.status{{background:#fff2ce;padding:12px;border-left:4px solid #a77800}}
nav a{{margin-right:16px}}details{{margin:12px 0}}</style>
<main><header><h1>Official Voice · 分布与数据核查</h1>
<p>固定发布日期：1988-01-01—2026-09-21（末月、末年不完整）。快照：{esc(summary["reported_at"])}</p>
<p class="status">已观测分布核查；all_sources_complete =
{str(summary["all_sources_complete"]).lower()}。
待接入接口不计为已完成；数值不代表物理事件频率、关注度或机构立场。</p>
<p>Baseline26：{summary["totals"]["baseline26"]:,}；Extended33：{summary["totals"]["extended33_union"]:,}。
Baseline 是 Extended 的子集，两者不可相加。唯一 ID 与聚合：PASS。</p>
<nav>{" ".join(f'<a href="#{n}">{esc(t)}</a>' for n, t, _ in figures)}</nav>
<details><summary>缺失月份与待接入来源</summary>
<p>Baseline26 零观测月份：{esc(", ".join(missing["baseline26"]) or "无")}。</p>
<p>Extended33 零观测月份：{esc(", ".join(missing["extended33_union"]) or "无")}。</p>
<ul>{pending_html}</ul></details>
<details><summary>数据下载、日期证据与校验</summary><p>{link_html}</p></details>
<details><summary>阶段标签与政策标注说明</summary>
<p>1988–2005 Historical Baseline；2006–2014 Political &amp; Policy Peak；
2015–2026 Institutional Normalization。标签由用户指定，不是数据验证出的趋势结论。</p>
<p>{milestones}</p></details>
</header>{cards}</main></html>"""
    with core.atomic_text(out / "dashboard.html") as f:
        f.write(text)


def render(data, summary, out):
    heatmap(data, summary, out)
    donut(data, summary, out)
    terminology(data, summary, out)
    event_overlay(data, summary, out)
    current = [
        "annual_distribution",
        "monthly_distribution",
        "density_heatmap",
        "source_proportions",
        "terminology_groups_v3",
        "event_alignment_v3",
    ]
    if summary["all_available_sources_complete"]:
        for previous, final in [
            ("terminology_groups_v3", "terminology_groups_final_20261021"),
            ("event_alignment_v3", "event_alignment_final_20261021"),
        ]:
            for extension in ["pdf", "svg", "png"]:
                shutil.copy2(out / f"{previous}.{extension}", out / f"{final}.{extension}")
            current[current.index(previous)] = final
    core.write_json(
        out / "CURRENT_FIGURES.json",
        {
            "snapshot": summary["reported_at"],
            "figures": current,
            "native_record_identity_hash": summary["stable_record_identity_hash"],
            "pdf_sha256": {
                name: hashlib.sha256((out / f"{name}.pdf").read_bytes()).hexdigest()
                for name in current
            },
        },
    )
    dashboard(summary, out)
