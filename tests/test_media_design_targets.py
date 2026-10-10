"""Inversion and influence guarantees, independent of collector implementation."""

import math
from itertools import product

import pytest

from fear_temperature.media_design_targets import (
    append_mass_lower_bound,
    design_requirements,
    minimum_groups_for_influence,
    required_effective_groups,
    required_units,
)
from fear_temperature.media_diagnostics import effective_n, precision_scenario


@pytest.mark.parametrize("margin", [0.10, 0.075, 0.05])
@pytest.mark.parametrize("rho", [0, 0.01, 0.05, 0.10, 1])
def test_inverse_requirements_satisfy_original_variance_model(margin, rho):
    target = precision_scenario(0, margin)["independent_n_reference"]
    for groups in [1, 10, 20, 30, 50, 500]:
        needed = required_units(groups, margin, rho)
        if needed is None:
            assert rho > 0 and groups / rho <= target
            continue
        assert effective_n(needed, groups, rho) >= target - 1e-9
        if needed - 1 >= groups:
            assert effective_n(needed - 1, groups, rho) < target
    for n in [target, target + 1, 500, 2000]:
        if n < target:
            continue
        groups = required_effective_groups(n, margin, rho)
        assert groups is not None and 1 <= groups <= n + 1e-9
        assert effective_n(n, groups, rho) >= target - 1e-9


def test_two_bodies_cannot_meet_even_independent_precision():
    result = design_requirements([1, 1], margin=.10, rho=0, influence_tolerance=.10)
    assert not result["scenario_met"]
    assert result["groups_needed_at_current_n"] is None
    assert result["amount_attainment_01"] == 2 / 93


def test_fifty_names_with_a_dominant_group_is_not_fifty_effective_groups():
    result = design_requirements([10000] + [1] * 49, margin=.075, rho=.05,
                                 influence_tolerance=.10)
    assert result["nominal_groups"] == 50
    assert result["effective_groups"] < 1.02
    assert result["units_at_current_mix"] is None
    assert not result["scenario_met"]


def test_single_group_deletion_bound_against_all_binary_assignments():
    counts = [7, 2, 1]
    weights = [n / sum(counts) for n in counts]
    for outcomes in product([0, 1], repeat=3):
        full = sum(w * y for w, y in zip(weights, outcomes, strict=True))
        for i, p in enumerate(weights):
            removed = (full - p * outcomes[i]) / (1 - p)
            assert abs(full - removed) <= p + 1e-12


def test_append_bound_is_necessary_and_does_not_claim_feasibility():
    counts = [600, 200, 200]
    needed = append_mass_lower_bound(counts, .10)
    assert needed == 5000
    assert 600 / (sum(counts) + needed - 1) > .10
    assert math.isclose(600 / (sum(counts) + needed), .10)
    assert minimum_groups_for_influence(.10) == 10
    assert minimum_groups_for_influence(.05) == 20


def test_empirical_quality_never_certified_by_scenario_pass():
    result = design_requirements([100] * 50, margin=.10, rho=.05,
                                 influence_tolerance=.10)
    assert result["scenario_met"]
    assert not result["quality_certified"]


def test_empty_and_invalid_inputs():
    assert not design_requirements([], margin=.10, rho=.05,
                                   influence_tolerance=.10)["scenario_met"]
    for rho in [-1, 2, float("nan")]:
        with pytest.raises(ValueError):
            required_units(10, .10, rho)
    with pytest.raises(ValueError):
        required_effective_groups(-1, .10, .05)
    with pytest.raises(ValueError):
        minimum_groups_for_influence(0)
