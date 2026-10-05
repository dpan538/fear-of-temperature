"""Figure 5: full-period quarterly overview derived from monthly_progress.csv."""
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "reports" / "monthly_progress.csv"
OUT = HERE / "reports" / "figure_5_us_au_coverage"


def main():
    with DATA.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["year_month"] != "unknown_month"]
    quarters = [(y, q) for y in range(1988, 2027) for q in range(1, 5) if (y, q) <= (2026, 3)]
    groups = ["US final rules", "US proposed rules", "AU current catalogue"]
    colors = ["#d1d5db", "#e9b05d", "#8ba6ba", "#216a73", "#f7fafb", "#6e4b85"]
    labels = ["Unsupported route", "Unknown denominator", "Partial body recovery", "Selected series acquired", "Verified zero", "Partial cutoff bin"]
    grid = np.zeros((3, len(quarters)), dtype=int)
    source = defaultdict(list)
    for r in rows:
        year, month = map(int, r["year_month"].split("-"))
        q = (month - 1) // 3 + 1
        name = "AU current catalogue" if r["jurisdiction"] == "AU_federal" else "US final rules" if r["genre"] == "final_rule" else "US proposed rules"
        source[(name, year, q)].append(r)
    for col, (year, q) in enumerate(quarters):
        for yi, name in enumerate(groups):
            block = source[(name, year, q)]
            if name.startswith("AU"):
                value = 1
            elif year < 1994:
                value = 0
            elif year == 2026 and q == 3:
                value = 5
            elif all(int(r["target"] or 0) == 0 for r in block):
                value = 4
            elif any(int(r["downloaded"] or 0) < int(r["target"] or 0) for r in block):
                value = 2
            else:
                value = 3
            grid[yi, col] = value
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "pdf.fonttype": 42, "svg.fonttype": "none", "font.size": 8})
    fig, ax = plt.subplots(figsize=(16, 3.15))
    ax.imshow(grid, aspect="auto", cmap=ListedColormap(colors), vmin=-0.5, vmax=5.5, interpolation="nearest")
    ax.set_yticks(range(3), groups)
    ax.set_xticks([i for i, (year, q) in enumerate(quarters) if q == 1 and year % 2 == 0],
                  [str(year) for year, q in quarters if q == 1 and year % 2 == 0])
    ax.tick_params(axis="both", length=0, pad=5)
    ax.set_xlim(-0.5, len(quarters) - 0.5)
    ax.set_ylim(2.5, -0.5)
    ax.set_xlabel("Publication quarter, January 1988–21 September 2026")
    ax.set_title("Figure 5 | Source-specific monthly coverage states, quarterly overview", loc="left", fontsize=10, pad=14)
    ax.set_xticks(np.arange(-0.5, len(quarters), 1), minor=True)
    ax.grid(which="minor", axis="x", color="white", linewidth=0.35)
    for spine in ax.spines.values(): spine.set_visible(False)
    handles = [Patch(facecolor=color, label=label) for color, label in zip(colors, labels)]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.01))
    fig.text(0.13, 0.25, "AU dates use original issue evidence; current catalogue CMS timestamps never fill a month. US zero is only for the fixed EPA/DOE rule series.", fontsize=7)
    fig.subplots_adjust(left=0.13, right=0.99, top=0.77, bottom=0.40)
    fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(OUT.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(OUT.with_suffix(".png"), dpi=300, bbox_inches="tight")
    (OUT.with_suffix(".qa.json")).write_text(json.dumps({"source_data": str(DATA), "grid_quarters": len(quarters),
        "source_rows": len(rows), "panel_alignment": "not_applicable_single_axes", "status_counts": {labels[i]: int((grid == i).sum()) for i in range(6)}}, indent=2) + "\n")
    plt.close(fig)


if __name__ == "__main__": main()
