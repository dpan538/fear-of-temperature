"""Read-only media diagnostics, not acquisition controls or emotion measurements.

The joint signed index is a proposed descriptive construction. Parent correlation
and precision are scenarios, not fitted properties or calibrated probabilities.
No function returns a retention, deletion, stopping or sampling decision.
"""

from __future__ import annotations

import calendar
import math
from collections import defaultdict
from datetime import date
from statistics import NormalDist, median

START = date(1988, 1, 1)
END = date(2026, 9, 21)
VERSION = "media-joint-diagnostics-1"


def _number(value: float, *, minimum: float = 0) -> float:
    if isinstance(value, bool) or not math.isfinite(value) or value < minimum:
        raise ValueError("Expected a finite nonnegative number")
    return float(value)


def month_index(month: str) -> int:
    try:
        value = date.fromisoformat(month + "-01")
    except (ValueError, TypeError) as exc:
        raise ValueError("Month must be YYYY-MM") from exc
    if not START <= value <= END:
        raise ValueError("Month outside the fixed publication interval")
    return value.year * 12 + value.month - 1


def scope_days(month: str) -> int:
    """Calendar opportunity only: not days of verified archive capture."""
    month_index(month)
    year, part = map(int, month.split("-"))
    return END.day if month == END.strftime("%Y-%m") else calendar.monthrange(year, part)[1]


def _counts(values: list[float]) -> list[float]:
    result = [_number(x) for x in values]
    return [x for x in result if x > 0]


def parent_profile(counts: list[float]) -> dict:
    """Hill q=2 effective groups and collision complement, within one dimension."""
    positive = _counts(counts)
    total = sum(positive)
    if not total:
        return {"n": 0, "groups": 0, "effective_groups": None, "diversity_01": None}
    concentration = sum((x / total) ** 2 for x in positive)
    return {
        "n": total,
        "groups": len(positive),
        "effective_groups": 1 / concentration,
        "diversity_01": 1 - concentration,
    }


def parent_bounds(known_groups: list[float], unknown_source_blocks: list[float]) -> dict:
    """Logical bounds conditional on evidenced distinct known groups.

    Each unknown source-month block has one unresolved parent in this dimension.
    It can join a known parent or another unknown block. It cannot split into
    multiple parents. A multi-parent source must be resolved before using this
    contract. These are mapping bounds, not confidence intervals.
    """
    known, unknown = _counts(known_groups), _counts(unknown_source_blocks)
    total = sum(known) + sum(unknown)
    if not total:
        return {
            "mapped_fraction": None,
            "effective_groups_low": None,
            "effective_groups_high": None,
            "n": 0,
        }
    lower = known[:]
    if unknown:
        if lower:
            i = max(range(len(lower)), key=lower.__getitem__)
            lower[i] += sum(unknown)
        else:
            lower = [sum(unknown)]
    return {
        "n": total,
        "mapped_fraction": sum(known) / total,
        "effective_groups_low": parent_profile(lower)["effective_groups"],
        "effective_groups_high": parent_profile(known + unknown)["effective_groups"],
    }


def effective_n(n: float, effective_parents: float, rho: float) -> float:
    """Exchangeable within-parent sensitivity; cross-parent covariance is zero.

    Var(mean) = sigma^2/N^2 * [N + rho*(sum(n_g^2)-N)]. Thus the
    design-effect scenario is 1 + rho*(N/P_eff - 1). No ICC is estimated here.
    """
    n = _number(n)
    rho = _number(rho)
    if rho > 1:
        raise ValueError("rho must be in [0, 1]")
    if n == 0:
        return 0.0
    p = _number(effective_parents, minimum=1)
    if p > n + 1e-9:
        raise ValueError("Effective parent count cannot exceed unit count")
    return n / (1 + rho * (n / p - 1))


def precision_scenario(n: float, margin: float = 0.10, confidence: float = 0.95) -> dict:
    """Worst-case Wilson half-width benchmark for a FUTURE binary estimand.

    With fractional n_eff, this is only a design sensitivity surrogate, not an
    actual binomial interval or achieved coverage. There are no outcome labels.
    The bounded index is proposed here: margin/(margin + half_width).
    A value of 0.5 denotes equality to a chosen margin, never 'complete'.
    """
    n, margin = _number(n), _number(margin)
    if not 0 < margin < 0.5 or not 0 < confidence < 1:
        raise ValueError("Invalid precision scenario")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    reference = max(1, math.ceil(z * z / (4 * margin * margin) - z * z))
    if n == 0:
        return {
            "scenario_half_width": None,
            "amount_index_01": 0.0,
            "independent_n_reference": reference,
        }
    half_width = z / (2 * math.sqrt(n + z * z))
    return {
        "scenario_half_width": half_width,
        "amount_index_01": margin / (margin + half_width),
        "independent_n_reference": reference,
    }


def inventory_fraction(loaded: int, eligible: int | None, evidence_ref: str = "") -> float | None:
    """Only a matched, enumerated source inventory has a coverage denominator."""
    if eligible is None:
        return None
    if not evidence_ref:
        raise ValueError("Known inventory requires scoped evidence")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in [loaded, eligible]):
        raise ValueError("Inventory counts must be integers")
    if loaded < 0 or eligible < 0 or loaded > eligible:
        raise ValueError("Inventory numerator and denominator conflict")
    return loaded / eligible if eligible else None


def js_divergence(left: dict[str, float], right: dict[str, float]) -> float | None:
    """Equal-mixture Jensen–Shannon divergence, base 2; empty mass is unknown."""
    for values in [left, right]:
        for value in values.values():
            _number(value)
    lp, rp = sum(left.values()), sum(right.values())
    if not lp or not rp:
        return None
    divergence = 0.0
    for key in left.keys() | right.keys():
        p, q = left.get(key, 0) / lp, right.get(key, 0) / rp
        mid = (p + q) / 2
        if p:
            divergence += 0.5 * p * math.log2(p / mid)
        if q:
            divergence += 0.5 * q * math.log2(q / mid)
    return min(1.0, max(0.0, divergence))


def signed_deviation(value: float, baseline: float) -> float | None:
    value, baseline = _number(value), _number(baseline)
    return (value - baseline) / (value + baseline) if value + baseline else None


def temporal_panel(cells: list[dict], month: str, radius: int = 3) -> dict:
    """Fixed common-source observed-presence panel within +/-radius months.

    Missing or zero unverified cells are NOT zero population expression. We use
    only sources positively observed at the target and every available nonempty
    neighbor. Selected-panel results must be shown beside pooled counts and mix
    change. This can select persistent sources; it is not a population estimator.
    """
    if not isinstance(radius, int) or isinstance(radius, bool) or radius < 1:
        raise ValueError("Positive integer radius required")
    by: dict[str, dict[str, float]] = defaultdict(dict)
    for row in cells:
        month_index(row["month"])
        key = row["source_id"]
        if key in by[row["month"]]:
            raise ValueError("Duplicate source-month cell; versions/aliases need resolution first")
        by[row["month"]][key] = _number(row["n"])
    index = month_index(month)
    neighbor_months = sorted(
        m
        for m, counts in by.items()
        if 0 < abs(month_index(m) - index) <= radius and sum(counts.values()) > 0
    )
    current = {s: n for s, n in by.get(month, {}).items() if n > 0}
    result = {
        "month": month,
        "neighbor_months": neighbor_months,
        "incomplete_neighbor_context": len(neighbor_months) < 2 * radius,
        "calendar_days_in_scope": scope_days(month),
        "calendar_exposure_is_verified_capture": False,
        "panel_sources": [],
        "panel_counts": {},
        "panel_n": 0,
        "panel_share_of_current": None,
        "signed_distribution_m11": None,
        "status": "insufficient_observed_panel",
    }
    if not current or len(neighbor_months) < 2:
        return result
    common = set(current)
    for neighbor in neighbor_months:
        common &= {s for s, n in by[neighbor].items() if n > 0}
    if not common:
        return result
    counts = {s: current[s] for s in sorted(common)}
    rates = [sum(by[m][s] for s in common) / scope_days(m) for m in neighbor_months]
    current_rate = sum(counts.values()) / scope_days(month)
    baseline = median(rates)
    result.update(
        panel_sources=sorted(common),
        panel_counts=counts,
        panel_n=sum(counts.values()),
        panel_share_of_current=sum(counts.values()) / sum(current.values()),
        current_panel_calendar_rate=current_rate,
        baseline_panel_calendar_rate=baseline,
        signed_distribution_m11=signed_deviation(current_rate, baseline),
        status="observed_panel_diagnostic_only",
    )
    return result


def joint_scenario(
    panel: dict,
    known_parent_by_source: dict[str, str],
    rho: float = 0.05,
    margin: float = 0.10,
) -> dict:
    """Link amount, parent dependence and distribution without a quality gate.

    J = D * A(n_eff). D and J are signed collection-volume contrasts, NOT
    emotional valence, invalidity probability or significance. Missing parents
    produce logical mapping bounds, not one guessed publisher total.
    """
    known: dict[str, float] = defaultdict(float)
    unknown = []
    for source, n in panel["panel_counts"].items():
        if known_parent_by_source.get(source):
            known[known_parent_by_source[source]] += n
        else:
            unknown.append(n)
    bounds = parent_bounds(list(known.values()), unknown)
    d = panel["signed_distribution_m11"]
    if d is None:
        return {
            "rho_scenario": rho,
            "margin_scenario": margin,
            "joint_low_m11": None,
            "joint_high_m11": None,
            "status": "insufficient_observed_panel",
        }
    n = bounds["n"]
    low_n = effective_n(n, bounds["effective_groups_low"], rho)
    high_n = effective_n(n, bounds["effective_groups_high"], rho)
    low = precision_scenario(low_n, margin)
    high = precision_scenario(high_n, margin)
    joint = sorted([d * low["amount_index_01"], d * high["amount_index_01"]])
    return {
        "rho_scenario": rho,
        "margin_scenario": margin,
        **bounds,
        "effective_n_low": low_n,
        "effective_n_high": high_n,
        "amount_low_01": low["amount_index_01"],
        "amount_high_01": high["amount_index_01"],
        "independent_n_reference": low["independent_n_reference"],
        "joint_low_m11": joint[0],
        "joint_high_m11": joint[1],
        "status": "proposed_descriptive_sensitivity_not_calibrated",
        "collection_gate": False,
        "deletion_recommendation": False,
    }


def year_group_sensitivity(
    cells: list[dict], alpha_year: float = 0.5, alpha_group: float = 0.0
) -> dict:
    """Observed-mass tempering for comparison only, not population calibration.

    Each unique cell has year, group and integer n. The caller declares a common
    observation window and ONE group dimension (source, verified parent, or
    native thread/type). Missing groups/years are never synthesized. Targets:
    q_y proportional to p_y**(1-alpha_year); q_g|y proportional to
    p_g|y**(1-alpha_group). alpha=1 is an equal-observed-groups stress test,
    NOT the expected growth curve. Per-unit weights have observed mean one.
    """
    ay, ag = _number(alpha_year), _number(alpha_group)
    if ay > 1 or ag > 1:
        raise ValueError("Sensitivity exponents must be in [0, 1]")
    grouped = defaultdict(dict)
    for row in cells:
        year, group, n = row["year"], row["group"], row["n"]
        if not isinstance(year, int) or isinstance(year, bool) or not 1988 <= year <= 2026:
            raise ValueError("Invalid study year")
        if not isinstance(group, str) or not group:
            raise ValueError("A named group or explicit unknown group is required")
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("Observed counts must be nonnegative integers")
        if group in grouped[year]:
            raise ValueError("Duplicate year-group cell")
        grouped[year][group] = n
    totals = {y: sum(c.values()) for y, c in grouped.items() if sum(c.values()) > 0}
    n = sum(totals.values())
    if not n:
        return {
            "status": "no_observed_mass",
            "cells": [],
            "annual_shares": [],
            "weight_only_effective_n": None,
            "collection_gate": False,
        }
    year_raw = {y: v / n for y, v in totals.items()}
    year_mass = {y: p ** (1 - ay) for y, p in year_raw.items()}
    year_target = {y: v / sum(year_mass.values()) for y, v in year_mass.items()}
    output, annual = [], []
    for year, total in sorted(totals.items()):
        raw = {g: v / total for g, v in grouped[year].items() if v > 0}
        group_mass = {g: p ** (1 - ag) for g, p in raw.items()}
        for group, mass in sorted(group_mass.items()):
            target = year_target[year] * mass / sum(group_mass.values())
            count = grouped[year][group]
            weight = target / (count / n)
            output.append(
                {
                    "year": year,
                    "group": group,
                    "n": count,
                    "per_unit_weight": weight,
                    "weighted_n": count * weight,
                    "raw_joint_share": count / n,
                    "scenario_joint_share": target,
                }
            )
        annual.append(
            {
                "year": year,
                "n": total,
                "raw_share": year_raw[year],
                "scenario_share": year_target[year],
            }
        )
    sum_weight_squared = sum(r["n"] * r["per_unit_weight"] ** 2 for r in output)
    return {
        "status": "sensitivity_only_not_population_calibration",
        "alpha_year": ay,
        "alpha_group": ag,
        "n": n,
        "cells": output,
        "annual_shares": annual,
        "annual_total_variation_01": sum(abs(year_raw[y] - year_target[y]) for y in totals) / 2,
        "joint_total_variation_01": sum(
            abs(r["raw_joint_share"] - r["scenario_joint_share"]) for r in output
        )
        / 2,
        "weight_only_effective_n": n * n / sum_weight_squared,
        "weight_only_effective_fraction_01": n / sum_weight_squared,
        "max_per_unit_weight": max(r["per_unit_weight"] for r in output),
        "min_per_unit_weight": min(r["per_unit_weight"] for r in output),
        "dependence_adjusted": False,
        "unobserved_years_imputed": False,
        "expected_population_growth_estimated": False,
        "collection_gate": False,
        "deletion_recommendation": False,
    }
