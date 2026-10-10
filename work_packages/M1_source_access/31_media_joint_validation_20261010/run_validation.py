"""Reproduce bounded diagnostics from explicitly named closed metadata only.

No database, body, network, collector control, deletion or semantic-label access.
Run from the repository root; use a fresh output directory for every invocation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from fear_temperature.media_diagnostics import (
    effective_n,
    joint_scenario,
    js_divergence,
    parent_profile,
    precision_scenario,
    temporal_panel,
    year_group_sensitivity,
)

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
P27 = ROOT / "work_packages/M1_source_access/27_newspaper_context_recovery_20261008"
INPUTS = {
    "nine_hour_closed": ROOT
    / "work_packages/M1_source_access/29_media_round_review_20261010/tables/source_month.csv",
    "social_four_hour_main_closed": P27
    / "social_public_api/continuations/20261010_four_hour_historical_repair/worker"
    / "summaries/source_month_calendar.csv",
}
RHOS = [0, 0.01, 0.05, 0.10, 1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()}
            )


def read_inputs():
    datasets = defaultdict(list)
    for snapshot, path in INPUTS.items():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                stream = row.get("stream", "social")
                n = int(row.get("bodies", row.get("usable_dated_independent_bodies", "0")))
                datasets[(snapshot, stream)].append(
                    {"source_id": row["source_id"], "month": row["month"], "n": n}
                )
    return datasets


def empirical(datasets):
    metrics, summaries = [], []
    for (snapshot, stream), cells in datasets.items():
        by_month, by_source = defaultdict(dict), defaultdict(int)
        for cell in cells:
            if cell["source_id"] in by_month[cell["month"]]:
                raise ValueError("Duplicate source-month in closed input")
            by_month[cell["month"]][cell["source_id"]] = cell["n"]
            by_source[cell["source_id"]] += cell["n"]
        n = sum(by_source.values())
        month_totals = {m: sum(v.values()) for m, v in by_month.items()}
        n2026 = sum(v for m, v in month_totals.items() if m.startswith("2026"))
        top = max(by_source, key=by_source.get)
        summaries.append(
            {
                "snapshot": snapshot,
                "stream": stream,
                "dated_units": n,
                "observed_months_of_465": sum(v > 0 for v in month_totals.values()),
                "exactly_two_months_historical_diagnostic_only": sum(
                    v == 2 for v in month_totals.values()
                ),
                "units_2026": n2026,
                "share_2026": n2026 / n,
                "contributing_source_ids": sum(v > 0 for v in by_source.values()),
                "source_id_effective_groups_not_verified_parents": parent_profile(
                    list(by_source.values())
                )["effective_groups"],
                "top_source_id": top,
                "top_source_share": by_source[top] / n,
                "publisher_parent_mapping": "unknown_in_these_inputs",
                "inventory_completeness": "unknown",
                "social_four_hour_scope_note": (
                    "main closed phase only; subsequent capacity-resume delta excluded"
                    if snapshot == "social_four_hour_main_closed"
                    else "not applicable"
                ),
            }
        )
        for year in range(1988, 2027):
            for month_no in range(1, 13):
                month = f"{year}-{month_no:02d}"
                if month > "2026-09":
                    continue
                panel = temporal_panel(cells, month)
                previous = f"{year - 1}-12" if month_no == 1 else f"{year}-{month_no - 1:02d}"
                mix_js = js_divergence(by_month.get(month, {}), by_month.get(previous, {}))
                for rho in RHOS:
                    # No undocumented conversion of source IDs into publisher parents.
                    joint = joint_scenario(panel, {}, rho=rho)
                    metrics.append(
                        {
                            "snapshot": snapshot,
                            "stream": stream,
                            "month": month,
                            "pooled_n": month_totals.get(month, 0),
                            "presence_only": month_totals.get(month, 0) > 0,
                            "inventory_recovery_01": None,
                            "inventory_state": "unknown_denominator",
                            "parent_relation_dimension": "publisher_operator",
                            "mapping_assumption": "one_unknown_parent_per_source_month_block",
                            "adjacent_source_mix_js_01": mix_js,
                            **{k: v for k, v in panel.items() if k != "panel_counts"},
                            **joint,
                        }
                    )
    return metrics, summaries


def simulations(seed=20261010, replicates=30000):
    """Validate variance identity with beta-binomial dependent synthetic units."""
    rng = np.random.default_rng(seed)
    rows = []
    cases = {
        "one_parent": [1000],
        "ten_balanced": [100] * 10,
        "unequal": [800] + [20] * 10,
        "two_singletons": [1, 1],
    }
    for name, counts in cases.items():
        n = sum(counts)
        peff = parent_profile(counts)["effective_groups"]
        for rho in RHOS:
            if rho == 0:
                totals = rng.binomial(n, 0.5, size=replicates)
            else:
                totals = np.zeros(replicates)
                for size in counts:
                    theta = (
                        rng.binomial(1, 0.5, size=replicates)
                        if rho == 1
                        else rng.beta((1 / rho - 1) / 2, (1 / rho - 1) / 2, size=replicates)
                    )
                    totals += rng.binomial(size, theta)
            neff = effective_n(n, peff, rho)
            theoretical = 0.25 / neff
            empirical_variance = float(np.var(totals / n, ddof=1))
            rows.append(
                {
                    "case": name,
                    "n": n,
                    "source_groups": len(counts),
                    "p_effective": peff,
                    "rho": rho,
                    "n_effective": neff,
                    "replicates": replicates,
                    "seed": seed,
                    "theoretical_variance": theoretical,
                    "empirical_variance": empirical_variance,
                    "relative_error": abs(empirical_variance / theoretical - 1),
                    "model_assumptions": (
                        "equal marginal p=.5; common nonnegative within-parent ICC; "
                        "independent parents"
                    ),
                }
            )
    return rows


def scenarios():
    rows = []
    for n, parents in [(2, 1), (2, 2), (100, 1), (1000, 1), (1000, 10), (1000, 100)]:
        for rho in RHOS:
            neff = effective_n(n, parents, rho)
            for margin in [0.10, 0.075, 0.05]:
                rows.append(
                    {
                        "n": n,
                        "balanced_parent_scenario": parents,
                        "rho": rho,
                        "margin": margin,
                        "n_effective": neff,
                        **precision_scenario(neff, margin),
                    }
                )
    return rows


def annual_sensitivity(datasets):
    annual, weights, summaries, panels = [], [], [], []
    variants = [
        ("raw", 0, 0),
        ("year_gentle", 0.25, 0),
        ("year_moderate", 0.5, 0),
        ("source_moderate", 0, 0.5),
        ("joint_moderate", 0.5, 0.5),
        ("equal_observed_stress_only", 1, 1),
    ]
    for (snapshot, stream), cells in datasets.items():
        for frame in ["all_available_partial_2026", "2016_2026_Jan_Aug"]:
            counts = defaultdict(int)
            for row in cells:
                year, month = map(int, row["month"].split("-"))
                if frame == "2016_2026_Jan_Aug" and (year < 2016 or month > 8):
                    continue
                counts[year, row["source_id"]] += row["n"]
            grouped = [{"year": y, "group": g, "n": n} for (y, g), n in counts.items()]
            prefix = {
                "snapshot": snapshot,
                "stream": stream,
                "comparison_frame": frame,
                "group_dimension": "source_id_not_verified_parent_or_noise_class",
            }
            for label, ay, ag in variants:
                result = year_group_sensitivity(grouped, ay, ag)
                header = {**prefix, "scenario": label}
                annual.extend({**header, **row} for row in result["annual_shares"])
                weights.extend({**header, **row} for row in result["cells"])
                summaries.append(
                    {
                        **header,
                        **{k: v for k, v in result.items() if k not in ["annual_shares", "cells"]},
                    }
                )
            if frame == "2016_2026_Jan_Aug":
                # Same January-August calendar window; never scale partial September.
                sources = [
                    {g for (y, g), n in counts.items() if y == year and n > 0}
                    for year in range(2016, 2027)
                ]
                common = set.intersection(*sources)
                for year in range(2016, 2027):
                    pooled = sum(n for (y, _g), n in counts.items() if y == year)
                    panel_n = sum(counts[year, g] for g in common)
                    panels.append(
                        {
                            **prefix,
                            "year": year,
                            "pooled_n": pooled,
                            "fixed_panel_n": panel_n if common else None,
                            "fixed_sources": sorted(common),
                            "panel_share": panel_n / pooled if pooled and common else None,
                            "status": "observed_panel_only" if common else "no_common_panel",
                            "verified_capture_denominator": False,
                        }
                    )
    return annual, weights, summaries, panels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = {str(p.relative_to(ROOT)): digest(p) for p in INPUTS.values()}
    metrics, summaries = empirical(read_inputs())
    sim = simulations()
    annual, weights, weight_summary, annual_panel = annual_sensitivity(read_inputs())
    write_csv(args.output / "monthly_joint_diagnostics.csv", metrics)
    write_csv(args.output / "snapshot_summary.csv", summaries)
    write_csv(args.output / "dependence_simulation.csv", sim)
    write_csv(args.output / "precision_scenarios.csv", scenarios())
    write_csv(args.output / "annual_share_scenarios.csv", annual)
    write_csv(args.output / "year_source_weights.csv", weights)
    write_csv(args.output / "weight_sensitivity_summary.csv", weight_summary)
    write_csv(args.output / "annual_fixed_source_panel.csv", annual_panel)
    assert before == {str(p.relative_to(ROOT)): digest(p) for p in INPUTS.values()}
    validation = {
        "at_utc": datetime.now(UTC).isoformat(),
        "schema_version": "media-joint-v2-annual-source-sensitivity",
        "annual_weight_scenario_cases": len(weight_summary),
        "noise_and_feedback_class_labels": "not supplied; no semantic classes inferred",
        "monthly_scenario_rows": len(metrics),
        "snapshot_rows": len(summaries),
        "simulation_cases": len(sim),
        "maximum_simulation_relative_variance_error": max(r["relative_error"] for r in sim),
        "simulation_tolerance": 0.05,
        "simulation_pass": all(r["relative_error"] < 0.05 for r in sim),
        "input_bytes_unchanged": True,
        "database_or_body_read": False,
        "parent_mapping_claim": (
            "logical sensitivity bounds; no verified publisher mapping in chosen inputs"
        ),
        "not_validated": [
            "actual media ICC",
            "population representativeness",
            "automatic anomaly classification",
            "emotional validity",
            "archive completeness",
            "collection stopping threshold",
        ],
        "collection_gate": False,
        "deletion_or_replacement_performed": False,
    }
    (args.output / "VALIDATION_REPORT.json").write_text(json.dumps(validation, indent=2) + "\n")
    outputs = {p.name: digest(p) for p in sorted(args.output.iterdir()) if p.is_file()}
    implementation = [
        Path(__file__),
        ROOT / "src/fear_temperature/media_diagnostics.py",
        ROOT / "tests/test_media_diagnostics.py",
    ]
    manifest = {
        "inputs_sha256": before,
        "outputs_sha256": outputs,
        "implementation_sha256": {str(p.relative_to(ROOT)): digest(p) for p in implementation},
    }
    (args.output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not validation["simulation_pass"]:
        raise SystemExit("Synthetic variance check failed; inspect retained outputs")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
