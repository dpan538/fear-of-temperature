"""Observed inventory distributions, never population/event/attention estimates.

Figure contract: quantitative grid; each row preserves a source-native unit,
columns compare Baseline26 with its Extended33 superset using independent Y scales.
Raw metadata are never removed. Year-only dates enter annual counts and remain
unallocated in monthly counts. No smoothing, sampling, model or significance test.
Python is the saved backend. Export PDF/SVG and 300-dpi PNG for review, min font8pt.
"""

import csv
import hashlib
import json
import string
import sys
from collections import Counter
from pathlib import Path

import collect as core
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import report_enhancements as enhanced

mpl.use("Agg")

SKILL = Path("/Users/jarlgiovanni/.codex/skills/nature-figure/scripts")
sys.path.insert(0, str(SKILL))
from audit_panel_alignment import require_matplotlib_panel_alignment  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "distribution_review_20261021"
MATRICES = ["baseline26", "extended33_union"]
LABELS = {
    "hansard_federal_rapid": ("Federal Hansard", "procedural records"),
    "uq_espace": ("UQ eSpace", "publication metadata"),
    "trove_web_gazette": ("Trove Gazette", "reproduced gazette articles"),
    "bom_scs": ("BoM special statements", "statement documents"),
    "bom_annual": ("BoM annual summaries", "summary documents"),
    "qld_statements": ("QLD ministerial releases", "release documents"),
    "csiro_dap": ("CSIRO DAP", "dataset catalogues"),
    "qld_opendata": ("QLD Open Data", "dataset catalogues"),
    "qld_resources": ("QLD linked resources", "linked publication documents"),
}


def csv_out(name, fields, rows):
    with core.atomic_text(OUT / name) as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerows(rows)


def aggregate():
    OUT.mkdir(exist_ok=True)
    store = core.Store()
    store.db.execute("BEGIN")
    rows = [
        dict(r)
        for r in store.db.execute(
            "SELECT "
            "doc_id,native_id,source_channel,native_unit,query_matched,query_dimensions,"
            "date_status,publication_month,publication_start,publication_end,date_granularity,"
            "author_speaker,source_context_json,url_source,title,date_basis"
            " FROM source_documents"
        )
    ]
    exhaustion = core.exhaustion_summary(store)
    jobs = [
        {k: v for k, v in dict(r).items() if k != "cursor"}
        for r in store.db.execute("SELECT * FROM ingest_jobs")
    ]
    store.db.rollback()
    month_counts, year_counts, totals, unallocated, pending = (Counter() for _ in range(5))
    channels = list(LABELS)
    for row in rows:
        source = row["source_channel"]
        if source not in channels:
            channels.append(source)
        membership = core.matrix_membership(json.loads(row["query_matched"]))
        for matrix in MATRICES:
            if not membership[matrix]:
                continue
            if row["date_status"] != "inside_fixed_interval":
                pending[(matrix, source, row["date_status"])] += 1
                continue
            totals[(matrix, source)] += 1
            if month := row["publication_month"]:
                month_counts[(matrix, source, month)] += 1
            else:
                unallocated[(matrix, source, "month")] += 1
            start, end = row["publication_start"], row["publication_end"]
            if start and end and start[:4] == end[:4]:
                year_counts[(matrix, source, int(start[:4]))] += 1
            else:
                unallocated[(matrix, source, "year")] += 1
    month_rows = [
        (m, s, t, month_counts[(m, s, t)], exhaustion["exhaustion_status"].get(s, "NOT_STARTED"))
        for m in MATRICES
        for s in channels
        for t in core.months()
    ]
    year_rows = [
        (m, s, y, year_counts[(m, s, y)])
        for m in MATRICES
        for s in channels
        for y in range(1988, 2027)
    ]
    csv_out(
        "monthly_by_source_matrix.csv",
        [
            "matrix",
            "source_channel",
            "publication_month",
            "unique_native_records",
            "exhaustion_status",
        ],
        month_rows,
    )
    csv_out(
        "annual_by_source_matrix.csv",
        ["matrix", "source_channel", "publication_year", "unique_native_records"],
        year_rows,
    )
    csv_out(
        "monthly_pooled_matrix.csv",
        ["matrix", "publication_month", "unique_native_metadata_records"],
        [
            (m, t, sum(month_counts[(m, s, t)] for s in channels))
            for m in MATRICES
            for t in core.months()
        ],
    )
    missing = [
        (m, "ALL_OBSERVED_SOURCES", t, "zero_observed_not_validated_absence")
        for m in MATRICES
        for t in core.months()
        if not sum(month_counts[(m, s, t)] for s in channels)
    ]
    missing += [
        (m, s, t, "zero_observed_not_validated_absence") for m, s, t, n, _ in month_rows if not n
    ]
    csv_out(
        "pooled_missing_months.csv",
        ["matrix", "publication_month", "interpretation"],
        [(m, t, note) for m, s, t, note in missing if s == "ALL_OBSERVED_SOURCES"],
    )
    csv_out(
        "missing_months.csv",
        ["matrix", "source_channel", "publication_month", "interpretation"],
        missing,
    )
    csv_out(
        "unallocated_or_pending_dates.csv",
        ["matrix", "source_channel", "state", "unique_native_records"],
        [
            (m, s, "in_interval_month_unallocated", n)
            for (m, s, unit), n in unallocated.items()
            if unit == "month"
        ]
        + [(m, s, state, n) for (m, s, state), n in pending.items()],
    )
    csv_out(
        "source_totals.csv",
        [
            "matrix",
            "source_channel",
            "native_unit",
            "in_interval_total",
            "monthly_allocated",
            "year_only_or_month_unallocated",
            "date_pending_or_outside",
        ],
        [
            (
                m,
                s,
                LABELS.get(s, (s, "see native metadata"))[1],
                totals[(m, s)],
                sum(month_counts[(m, s, t)] for t in core.months()),
                unallocated[(m, s, "month")],
                sum(n for (mm, ss, _), n in pending.items() if mm == m and ss == s),
            )
            for m in MATRICES
            for s in channels
        ],
    )
    incomplete = [
        s for s, v in exhaustion["exhaustion_status"].items() if v != "COMPLETED_LAST_PAGE"
    ]
    registry = {s["channel"]: s for s in core.REGISTRY["sources"]}
    csv_out(
        "pending_sources.csv",
        ["source_channel", "exhaustion_status", "reason", "endpoint"],
        [
            (
                s,
                exhaustion["exhaustion_status"][s],
                registry[s].get("status") or registry[s].get("verification"),
                registry[s].get("endpoint"),
            )
            for s in incomplete
        ],
    )
    core.write_json(OUT / "pagination_jobs.json", jobs)
    summary = {
        "reported_at": core.now(),
        "publication_interval": [core.START, core.END],
        "artifact_type": "distribution_review; not formal all-sources-complete corpus export",
        **exhaustion,
        "totals": {m: sum(totals[(m, s)] for s in channels) for m in MATRICES},
        "month_allocated": {
            m: sum(month_counts[(m, s, t)] for s in channels for t in core.months())
            for m in MATRICES
        },
        "zero_observed_months": {
            m: [t for t in core.months() if not sum(month_counts[(m, s, t)] for s in channels)]
            for m in MATRICES
        },
        "source_rows": len(rows),
        "stable_record_identity_hash": core.digest(
            sorted(
                (r["doc_id"], r["date_status"], r["publication_month"], r["query_matched"])
                for r in rows
            )
        ),
        "interpretation": (
            "Observed query-matched source-native metadata, "
            "heterogeneous units; not event frequency, physical "
            "warming, population attention or verified institutional "
            "endorsement. Baseline subset of Extended; do not add "
            "totals. September2026 partial through21. Year-only dates "
            "not assigned to January."
        ),
        "qa_statistics": (
            "Exact deterministic counts. No inferential tests, "
            "uncertainty intervals, smoothing or record sampling. No "
            "image manipulation."
        ),
    }
    extra = enhanced.build(rows, channels, month_counts, year_counts, totals, summary, OUT)
    core.write_json(OUT / "REVIEW_STATUS.json", summary)
    return channels, month_counts, year_counts, totals, unallocated, pending, summary, extra


def plot(kind, channels, monthly, annual, totals, unallocated, pending, summary):
    show = [
        s
        for s in channels
        if any(
            totals[(m, s)] or sum(n for (mm, ss, _), n in pending.items() if mm == m and ss == s)
            for m in MATRICES
        )
    ]
    fig, axes = plt.subplots(
        len(show), 2, figsize=(12, 1.55 * len(show) + 1.9), sharex=True, sharey=False, squeeze=False
    )
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.075, top=0.885, hspace=0.85, wspace=0.17)
    incomplete = not summary["all_sources_complete"]
    fig.suptitle(
        ("Annual" if kind == "annual" else "Monthly")
        + " observed official-source metadata | 1988–2026",
        x=0.10,
        y=0.982,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.10,
        0.953,
        "Baseline26 and Extended33 shown separately; source-native units differ.",
        fontsize=10,
    )
    fig.text(
        0.10,
        0.930,
        (
            (
                "Available routes complete; additional pending routes are disclosed."
                if summary["all_available_sources_complete"]
                else "PROVISIONAL: source scans still in progress; pending routes disclosed."
            )
            if incomplete
            else "All registered routes traversed to their terminal pages."
        ),
        fontsize=9,
        color="#624C3A",
    )
    periods = list(range(1988, 2027)) if kind == "annual" else list(core.months())
    x = np.arange(len(periods))
    colors = ["#326B8C", "#64438A"]
    for i, source in enumerate(show):
        values = [
            [(annual if kind == "annual" else monthly)[(matrix, source, t)] for t in periods]
            for matrix in MATRICES
        ]
        for j, _matrix in enumerate(MATRICES):
            ax = axes[i, j]
            vals = values[j]
            ymax = max(vals)
            ax.set_ylim(0, max(1, ymax) * 1.15)
            ax.set_xlim(-0.7, len(x) - 0.3)
            label = string.ascii_lowercase[i * 2 + j]
            ax.annotate(
                label,
                xy=(0, 1),
                xycoords="axes fraction",
                xytext=(-24, 8),
                textcoords="offset points",
                fontsize=10,
                fontweight="bold",
                ha="left",
                va="bottom",
            )
            ax.set_title(
                LABELS.get(source, (source, ""))[0]
                + (" | Baseline26" if j == 0 else " | Extended33"),
                loc="left",
                pad=12,
                fontsize=10,
            )
            if j == 0:
                ax.set_ylabel("Records", fontsize=9)
            ax.text(
                0,
                1.02,
                LABELS.get(source, ("", "native metadata"))[1],
                transform=ax.transAxes,
                fontsize=8,
                color="#555555",
                va="bottom",
            )
            if ymax:
                if kind == "annual":
                    ax.bar(x, vals, width=0.78, color=colors[j], linewidth=0)
                else:
                    ax.vlines(x, 0, vals, color=colors[j], linewidth=0.7)
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No publication-date allocation\nSee pending-date inventory",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="#666666",
                )
            ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(3, integer=True))
            ax.grid(axis="y", color="#E5E5E5", linewidth=0.5, zorder=0)
            if i == len(show) - 1:
                ticks = [0, 8, 16, 24, 32, 38] if kind == "annual" else [0, 96, 192, 288, 384, 464]
                ax.set_xticks(ticks, ["1988", "1996", "2004", "2012", "2020", "2026"])
                ax.set_xlabel(
                    "Publication year" if kind == "annual" else "Publication month (year ticks)"
                )
    month_unknown = sum(unallocated[(m, s, "month")] for s in channels for m in [MATRICES[1]])
    footer = (
        "Independent Y scale in every panel (free_y). 2026 ends 21 September. Zero = "
        "no observed dated match, not verified absence."
    )
    fig.text(0.10, 0.035, footer, fontsize=9)
    fig.text(
        0.10,
        0.018,
        (
            f"Extended33: {month_unknown:,} in-interval records lack "
            f"month precision. Annual panels include year-only dates. No"
            f" smoothing."
        ),
        fontsize=9,
    )
    path = OUT / (kind + "_distribution")
    scale_audit = []
    for i, source in enumerate(show):
        for j, matrix in enumerate(MATRICES):
            ax = axes[i, j]
            if any(
                ax.get_shared_y_axes().joined(ax, other) for other in axes.flat if other is not ax
            ):
                raise ValueError("A subplot Y axis remains shared")
            scale_audit.append(
                {
                    "source": source,
                    "matrix": matrix,
                    "free_y": True,
                    "observed_max": max(
                        (annual if kind == "annual" else monthly)[(matrix, source, t)]
                        for t in periods
                    ),
                    "y_limits": list(ax.get_ylim()),
                }
            )
    core.write_json(path.with_suffix(".scales.json"), scale_audit)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        json_out=str(path) + ".alignment.json",
        overlay_svg=str(path) + ".alignment.svg",
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        strict=True,
    )
    fig.savefig(f"{path}.pdf", facecolor="white")
    fig.savefig(f"{path}.svg", facecolor="white")
    fig.savefig(f"{path}.png", dpi=300, facecolor="white")
    plt.close(fig)


def main():
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": 9,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )
    data = aggregate()
    for kind in ["monthly", "annual"]:
        plot(kind, *data[:7])
    enhanced.render(data[7], data[6], OUT)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob("*.csv")}
    core.write_json(OUT / "SOURCE_DATA_HASHES.json", hashes)
    print(json.dumps(data[6], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
