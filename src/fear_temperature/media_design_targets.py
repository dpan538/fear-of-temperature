"""Invert explicit study-design tolerances into source and amount requirements.

Outputs are conditional planning requirements, not estimated population targets,
collector quotas, or permission to declare an unverified corpus representative.
Source-ID inputs must remain labelled proxies until parent mappings are verified.
"""

from __future__ import annotations

import math

from fear_temperature.media_diagnostics import effective_n, parent_profile, precision_scenario


def _rho(value: float) -> None:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("rho must be in [0,1]")


def required_effective_groups(n: int, margin: float, rho: float) -> float | None:
    """Effective groups needed at a specified finite body count; None is infeasible.

    Uses the existing worst-case Wilson independent-N reference and exchangeable
    within-group correlation model. No outcome or ICC has been estimated.
    """
    _rho(rho)
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a nonnegative integer")
    target = precision_scenario(0, margin)["independent_n_reference"]
    if n < target:
        return None
    if rho == 0:
        return 1.0
    return max(1.0, rho * n / (n / target - 1 + rho))


def required_units(groups: float, margin: float, rho: float) -> int | None:
    """Body-count requirement at fixed effective groups; None means no finite N.

    Fixed group concentration and stated dependence are hypothetical, not a
    claim that acquiring more bodies will preserve or improve the mixture.
    """
    _rho(rho)
    if not math.isfinite(groups) or groups < 1:
        raise ValueError("Effective groups must be at least one")
    target = precision_scenario(0, margin)["independent_n_reference"]
    if rho == 0:
        return max(math.ceil(groups), target)
    if rho == 1:
        return math.ceil(groups) if groups >= target else None
    denominator = 1 - rho * target / groups
    if denominator <= 0:
        return None
    return max(math.ceil(groups), math.ceil(target * (1 - rho) / denominator - 1e-10))


def minimum_groups_for_influence(tolerance: float) -> int:
    """Necessary nominal group count for max share <= tolerance.

    For a fixed-weight mean of a [0,1] outcome, deleting group g and
    renormalizing shifts the mean by at most its original weight share p_g.
    This bound does not apply to arbitrary regressions, trends or causal effects.
    Count alone is insufficient: actual group shares must also meet the bound.
    """
    if not math.isfinite(tolerance) or not 0 < tolerance <= 1:
        raise ValueError("Influence tolerance must be in (0,1]")
    return math.ceil(1 / tolerance - 1e-12)


def append_mass_lower_bound(counts: list[int], tolerance: float) -> int:
    """Necessary extra mass outside the largest group without deleting any units.

    An optimistic bound, not a collection target or a feasible source inventory.
    Other groups can also violate the tolerance, and sufficient distinct groups
    must exist. Unlimited current-group expansion is not assumed to solve this.
    """
    minimum_groups_for_influence(tolerance)
    profile = parent_profile(counts)
    if not profile["n"]:
        return 0
    return max(0, math.ceil(max(counts) / tolerance - profile["n"] - 1e-8))


def design_requirements(
    counts: list[int], *, margin: float, rho: float, influence_tolerance: float
) -> dict:
    """Three separate [0,1] attainment ratios, explicit gaps and unknown validity."""
    minimum = minimum_groups_for_influence(influence_tolerance)
    _rho(rho)
    profile = parent_profile(counts)
    n = profile["n"]
    target = precision_scenario(0, margin)["independent_n_reference"]
    if not n:
        return {
            "n": 0, "nominal_groups": 0, "effective_groups": None,
            "largest_share": None, "independent_n_requirement": target,
            "effective_n_scenario": 0.0, "units_at_current_mix": None,
            "minimum_groups_for_influence": minimum, "groups_needed_at_current_n": None,
            "amount_attainment_01": 0.0, "group_attainment_01": 0.0,
            "influence_attainment_01": 0.0, "scenario_met": False,
            "quality_certified": False,
        }
    groups = profile["effective_groups"]
    actual_n = effective_n(n, groups, rho)
    group_target = required_effective_groups(int(n), margin, rho)
    share = max(counts) / n
    return {
        "n": int(n), "nominal_groups": profile["groups"], "effective_groups": groups,
        "largest_share": share, "independent_n_requirement": target,
        "effective_n_scenario": actual_n,
        "units_at_current_mix": required_units(groups, margin, rho),
        "minimum_groups_for_influence": minimum,
        "groups_needed_at_current_n": group_target,
        "amount_attainment_01": min(1.0, actual_n / target),
        "group_attainment_01": min(1.0, groups / group_target) if group_target else 0.0,
        "influence_attainment_01": min(1.0, influence_tolerance / share),
        "scenario_met": actual_n >= target - 1e-9 and share <= influence_tolerance + 1e-12,
        "quality_certified": False,
    }
