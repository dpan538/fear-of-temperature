"""Render two README figures from the aggregate companion's CSV files."""

import argparse
import csv
from collections import Counter
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

DATA_DIR = Path(__file__).resolve().parent
INK = "#172C3B"
MUTED = "#455E6E"
TRACK = "#E8EFF2"
BASELINE = "#295473"
TRAIN = "#18645D"
VALIDATION = "#6886A0"
TEST = "#B57736"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 10,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})


def figure_frame(height, plot_area, title, subtitle):
    fig = plt.figure(figsize=(9, height), facecolor="white")
    fig.text(.04, .89, title, fontsize=22, weight="bold", color=INK)
    fig.text(.04, .79, subtitle, fontsize=11, color=MUTED)
    return fig, fig.add_axes(plot_area)


def read_rows(name):
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def corpus_accounting(counts):
    splits = [
        ("v1 training", counts["train"], TRAIN),
        ("v1 validation", counts["validation"], VALIDATION),
        ("v1 test", counts["test"], TEST),
    ]
    eligible = counts["formal_eligible"]
    active = counts["active_acquisition_pool"]
    holdings = counts["preserved_acquisition_holdings"]
    if sum(value for _, value, _ in splits) != eligible:
        raise ValueError("Split totals differ from formal eligibility")
    if counts["materialized_release"] - counts["structural_holds"] != eligible:
        raise ValueError("Structural holds do not reconcile to formal eligibility")
    if holdings != counts["historical_formal"] + counts["phase32_gross_receipts"]:
        raise ValueError("Historical and appendix records do not reconcile to holdings")

    fig, ax = figure_frame(
        3.18, (.34, .29, .49, .44),
        "Acquisition holdings and formal release",
        "Native record identities through 17 November 2026",
    )
    ax.set(xlim=(0, holdings), ylim=(-.5, 2.5))
    ax.set_axis_off()

    stages = [
        ("Preserved acquisition holdings", holdings, "#7896A9"),
        ("Active acquisition pool", active, BASELINE),
        ("Formal v1 corpus", eligible, TRAIN),
    ]
    for position, (label, value, color) in zip((2, 1, 0), stages, strict=True):
        ax.barh(position, holdings, height=.42, color=TRACK)
        if position == 0:
            left = 0
            for _, size, split_color in splits:
                ax.barh(position, size, left=left, height=.42, color=split_color)
                left += size
        else:
            ax.barh(position, value, height=.42, color=color)
        ax.text(-.612, position, label, transform=ax.get_yaxis_transform(),
                va="center", fontsize=12, color=INK)
        ax.text(1.105, position, f"{value:,}", transform=ax.get_yaxis_transform(),
                va="center", fontsize=13, weight="bold", color=INK)

    for x, (label, value, color) in zip((.04, .36, .68), splits, strict=True):
        fig.text(x, .159, f"{value:,}", fontsize=19, weight="bold", color=color)
        fig.text(x, .080, f"{label}  ·  {value / eligible:.1%}", fontsize=11, color=MUTED)
    return fig


def publication_coverage(counts):
    yearly = Counter()
    for row in read_rows("year_by_stage.csv"):
        yearly[row["publication_year"], row["release_stage"]] += int(row["records"])
    years = list(range(2003, 2026))
    cohorts = ("baseline", "supplement")
    unknown = sum(yearly["Unknown", cohort] for cohort in cohorts)
    baseline, supplement = (
        [yearly[str(year), cohort] for year in years] for cohort in cohorts
    )
    if sum(baseline) + sum(supplement) + unknown != counts["formal_eligible"]:
        raise ValueError("Year counts do not reconcile to formal eligibility")

    fig, ax = figure_frame(
        3.55, (.085, .25, .875, .47),
        "Publication coverage, 2003–2025",
        f'{counts["formal_eligible"]:,} eligible records across '
        f'{counts["publication_hosts"]:,} publication hosts',
    )
    ax.bar(years, baseline, width=.76, color=BASELINE, label="Retained baseline")
    ax.bar(years, supplement, bottom=baseline, width=.76, color=TEST,
           label="Audited supplement")
    ax.set(xlim=(2002.35, 2025.65), xticks=[2003, 2007, 2011, 2015, 2019, 2023, 2025])
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda n, _: f"{n / 1000:g}k" if n else "0"))
    ax.tick_params(axis="both", length=0, pad=6, labelcolor=MUTED)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=TRACK)
    ax.spines[:].set_visible(False)
    ax.legend(loc="lower left", bbox_to_anchor=(.04, .055), bbox_transform=fig.transFigure,
              ncols=2, frameon=False, labelcolor=INK, borderaxespad=0)
    fig.text(.96, .075, f"{unknown:,} records outside the bars lack a single assigned year.",
             ha="right", fontsize=9, color=MUTED)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--vector", action="store_true", help="Also export PDF and SVG")
    args = parser.parse_args()
    plt.switch_backend("Agg")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts = {row["measure"]: int(row["count"]) for row in read_rows("release_counts.csv")}
    for name, render in [
        ("corpus_accounting", corpus_accounting),
        ("publication_coverage", publication_coverage),
    ]:
        fig = render(counts)
        fig.savefig(args.output_dir / f"{name}.png", dpi=300)
        if args.vector:
            fig.savefig(args.output_dir / f"{name}.pdf")
            fig.savefig(args.output_dir / f"{name}.svg")
        plt.close(fig)


if __name__ == "__main__":
    main()
