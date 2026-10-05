"""Figure 5 from the final US/AU/EU source-specific monthly ledger."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np

from acquire import HERE, US_SOURCE, AU_SOURCE
from consolidated_coverage import EU_SOURCE


LABELS = ["Unsupported source period", "Original-date denominator unknown",
          "Partial original acquisition", "Selected source route processed",
          "Verified zero in frozen series", "Partial cutoff quarter"]
COLORS = ["#d1d5db", "#e9b05d", "#8ba6ba", "#216a73", "#f7fafb", "#6e4b85"]
GROUPS = ["US final rules", "US proposed rules", "AU current catalogue",
          "EU Commission preparatory acts"]


def quarter(month):
    year, m = map(int, month.split("-"))
    return year, (m - 1) // 3 + 1


def status(group, year, q, rows):
    if group.startswith("AU"):
        return 1
    if group.startswith("US") and year < 1994:
        return 0
    if year == 2026 and q == 3:
        return 5
    if not rows:
        return 0
    if all(int(r["n_enumerated_targets"] or 0) == 0 for r in rows):
        return 4
    if group.startswith("EU"):
        return 2 if any(r["coverage_status"] == "partial_original_acquisition" for r in rows) else 3
    return 2 if any(r["coverage_status"] in {"partial_body_acquisition", "downloaded_extraction_pending"}
                    for r in rows) else 3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=HERE / "reports" / "cross_source_monthly_coverage.csv")
    parser.add_argument("--output-prefix", type=Path, default=HERE / "reports" / "figure_5_cross_source_coverage")
    args = parser.parse_args()
    with args.source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_quarter = defaultdict(list)
    for row in rows:
        if row["year_month"] == "unknown_month":
            continue
        if row["source_series"] == US_SOURCE:
            group = "US final rules" if row["genre"] == "final_rule" else "US proposed rules"
        elif row["source_series"] == AU_SOURCE:
            group = "AU current catalogue"
        elif row["source_series"] == EU_SOURCE:
            group = "EU Commission preparatory acts"
        else:
            raise RuntimeError(f"unexpected source series: {row['source_series']}")
        by_quarter[group, *quarter(row["year_month"])].append(row)
    quarters = [(year, q) for year in range(1988, 2027) for q in range(1, 5)
                if (year, q) <= (2026, 3)]
    grid = np.array([[status(group, year, q, by_quarter[group, year, q]) for year, q in quarters]
                     for group in GROUPS], dtype=int)
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "pdf.fonttype": 42, "svg.fonttype": "none", "font.size": 8})
    fig, ax = plt.subplots(figsize=(16, 3.8))
    ax.imshow(grid, aspect="auto", cmap=ListedColormap(COLORS), vmin=-0.5, vmax=5.5, interpolation="nearest")
    ax.set_yticks(range(len(GROUPS)), GROUPS)
    ticks = [i for i, (year, q) in enumerate(quarters) if q == 1 and year % 2 == 0]
    ax.set_xticks(ticks, [str(quarters[i][0]) for i in ticks])
    ax.tick_params(axis="both", length=0, pad=5)
    ax.set_xlim(-0.5, len(quarters) - 0.5)
    ax.set_ylim(len(GROUPS) - 0.5, -0.5)
    ax.set_xlabel("Publication quarter, January 1988–21 September 2026")
    ax.set_title("Figure 5 | Government source coverage by quarter", loc="left", fontsize=10, pad=14)
    ax.set_xticks(np.arange(-0.5, len(quarters), 1), minor=True)
    ax.grid(which="minor", axis="x", color="white", linewidth=0.35)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.legend(handles=[Patch(facecolor=color, label=label) for color, label in zip(COLORS, LABELS)],
               loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.08))
    fig.text(0.20, 0.23, "Rows keep separate denominators. 'Processed' does not establish relevance or complete-body usability; EU 2024-08 is zero only in the frozen class.", fontsize=7)
    fig.subplots_adjust(left=0.20, right=0.99, top=0.78, bottom=0.40)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 300})):
        fig.savefig(args.output_prefix.with_suffix("." + ext), bbox_inches="tight", **kw)
    qa = {"source": str(args.source), "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
          "source_rows": len(rows), "quarters": len(quarters), "groups": GROUPS,
          "status_counts": {LABELS[i]: int((grid == i).sum()) for i in range(len(LABELS))}}
    args.output_prefix.with_suffix(".qa.json").write_text(json.dumps(qa, indent=2) + "\n")
    plt.close(fig)
    print(json.dumps({"quarters": len(quarters), "groups": len(GROUPS),
                      "source_rows": len(rows), "output_prefix": str(args.output_prefix)}), flush=True)


if __name__ == "__main__":
    main()
