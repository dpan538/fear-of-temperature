"""Independent boundary, algebra and scenario tests for report-only diagnostics."""

import math

import pytest
from statsmodels.stats.proportion import proportion_confint

from fear_temperature.media_diagnostics import (
    effective_n,
    inventory_fraction,
    joint_scenario,
    js_divergence,
    parent_bounds,
    parent_profile,
    precision_scenario,
    scope_days,
    signed_deviation,
    temporal_panel,
)


@pytest.mark.parametrize("n", [2, 10, 100, 1000])
def test_precision_matches_independent_wilson_implementation(n):
    low, high = proportion_confint(n / 2, n, alpha=0.05, method="wilson")
    assert precision_scenario(n)["scenario_half_width"] == pytest.approx((high - low) / 2)


@pytest.mark.parametrize("margin,reference", [(0.1, 93), (0.075, 167), (0.05, 381)])
def test_scenario_reference_meets_precision_not_acquisition_threshold(margin, reference):
    row = precision_scenario(reference, margin)
    assert row["independent_n_reference"] == reference
    assert row["scenario_half_width"] <= margin
    assert precision_scenario(reference - 1, margin)["scenario_half_width"] > margin


def test_two_bodies_do_not_have_small_scenario_uncertainty():
    assert precision_scenario(2)["scenario_half_width"] > 0.40
    assert precision_scenario(2)["amount_index_01"] < 0.20
    assert precision_scenario(3)["amount_index_01"] > precision_scenario(2)["amount_index_01"]


def test_zero_is_absence_not_precision_or_parent_diversity():
    assert parent_profile([])["effective_groups"] is None
    assert parent_bounds([], [])["mapped_fraction"] is None
    assert precision_scenario(0)["amount_index_01"] == 0
    assert precision_scenario(0)["scenario_half_width"] is None


def test_same_count_different_parent_dependence():
    one = effective_n(1000, 1, 0.05)
    ten = effective_n(1000, 10, 0.05)
    assert one == pytest.approx(19.6270853778)
    assert ten == pytest.approx(168.0672268908)
    assert ten > one
    assert effective_n(1000, 1, 0) == 1000
    assert effective_n(1000, 10, 1) == 10


def test_equal_groups_effective_count_and_dominant_source():
    assert parent_profile([25] * 4)["effective_groups"] == 4
    assert parent_profile([97, 1, 1, 1])["effective_groups"] < 1.07
    assert parent_profile([100])["diversity_01"] == 0


def test_unknown_mapping_is_bounded_not_counted_as_known():
    bounds = parent_bounds([40], [30, 30])
    assert bounds["mapped_fraction"] == 0.4
    assert bounds["effective_groups_low"] == 1
    assert bounds["effective_groups_high"] == pytest.approx(1 / 0.34)
    assert parent_bounds([], [40, 30, 30])["effective_groups_low"] == 1


def test_known_parent_merging_changes_effective_units_not_raw_count():
    separate = parent_profile([50, 50])
    merged = parent_profile([100])
    assert separate["n"] == merged["n"]
    assert separate["effective_groups"] == 2 * merged["effective_groups"]


def test_distribution_sign_range_and_no_flattening():
    assert signed_deviation(300, 100) == 0.5
    assert signed_deviation(100, 300) == -0.5
    assert signed_deviation(0, 0) is None
    assert signed_deviation(1, 0) == 1
    assert signed_deviation(0, 1) == -1


def test_js_has_known_endpoints_symmetry_and_scale_invariance():
    assert js_divergence({"a": 1}, {"a": 99}) == 0
    assert js_divergence({"a": 1}, {"b": 1}) == 1
    p, q = {"a": 9, "b": 1}, {"a": 5, "b": 5}
    assert js_divergence(p, q) == pytest.approx(js_divergence(q, p))
    assert js_divergence(p, q) == pytest.approx(js_divergence(p, {"a": 50, "b": 50}))
    assert js_divergence({}, q) is None


def cells(pulse=1):
    return [
        {
            "source_id": source,
            "month": f"2025-{m:02d}",
            "n": scope_days(f"2025-{m:02d}") * (pulse if m == 4 else 1),
        }
        for source in ["a", "b"]
        for m in range(1, 8)
    ]


def test_event_peak_retained_as_positive_signed_observation():
    data = cells(4)
    before = [dict(r) for r in data]
    panel = temporal_panel(data, "2025-04")
    assert panel["signed_distribution_m11"] == pytest.approx(0.6)
    joint = joint_scenario(panel, {"a": "p1", "b": "p2"})
    assert joint["joint_low_m11"] > 0
    assert joint["collection_gate"] is False
    assert joint["deletion_recommendation"] is False
    assert data == before


def test_new_source_spike_separates_from_within_panel_change():
    data = cells()
    data.append({"source_id": "new", "month": "2025-04", "n": 10000})
    panel = temporal_panel(data, "2025-04")
    assert panel["signed_distribution_m11"] == 0
    assert panel["panel_sources"] == ["a", "b"]
    assert panel["panel_share_of_current"] < 0.01


def test_partial_september_calendar_rate_and_missing_future():
    data = [
        {"source_id": "a", "month": f"2026-{m:02d}", "n": scope_days(f"2026-{m:02d}")}
        for m in range(6, 10)
    ]
    panel = temporal_panel(data, "2026-09")
    assert panel["signed_distribution_m11"] == 0
    assert panel["calendar_days_in_scope"] == 21
    assert panel["incomplete_neighbor_context"] is True
    assert panel["calendar_exposure_is_verified_capture"] is False


def test_missing_month_is_not_imputed_to_zero_expression():
    panel = temporal_panel(cells(), "1988-01")
    assert panel["signed_distribution_m11"] is None
    assert joint_scenario(panel, {})["joint_low_m11"] is None


def test_negative_joint_bounds_remain_ordered():
    panel = temporal_panel(cells(0.1), "2025-04")
    row = joint_scenario(panel, {})
    assert -1 <= row["joint_low_m11"] <= row["joint_high_m11"] < 0


def test_no_parent_evidence_not_silently_renormalized():
    row = joint_scenario(temporal_panel(cells(4), "2025-04"), {})
    assert row["mapped_fraction"] == 0
    assert row["effective_groups_low"] == 1
    assert row["effective_groups_high"] == 2
    assert row["joint_low_m11"] < row["joint_high_m11"]


def test_unknown_denominator_never_completed_from_count():
    assert inventory_fraction(1000000, None) is None
    assert inventory_fraction(25, 100, "verified_native_inventory") == 0.25
    assert inventory_fraction(0, 0, "empty_native_inventory") is None
    with pytest.raises(ValueError):
        inventory_fraction(2, 2)
    with pytest.raises(ValueError):
        inventory_fraction(101, 100, "inventory")


@pytest.mark.parametrize("bad", [-1, math.nan, math.inf, True])
def test_invalid_counts_rejected(bad):
    with pytest.raises(ValueError):
        parent_profile([bad])


@pytest.mark.parametrize("month", ["1987-12", "2026-10", "2026-9", "wrong"])
def test_out_of_scope_or_malformed_months_rejected(month):
    with pytest.raises(ValueError):
        scope_days(month)


def test_duplicate_snapshot_cells_not_silently_added():
    data = cells()
    with pytest.raises(ValueError):
        temporal_panel(data + [data[0]], "2025-04")


def test_invalid_dependence_and_precision_rejected():
    for rho in [-0.1, 1.1, math.nan]:
        with pytest.raises(ValueError):
            effective_n(100, 2, rho)
    with pytest.raises(ValueError):
        effective_n(100, 101, 0.1)
    with pytest.raises(ValueError):
        precision_scenario(10, margin=0)


def test_large_one_parent_count_cannot_fake_independent_amount():
    small = effective_n(1000, 1, 0.05)
    large = effective_n(1000000, 1, 0.05)
    assert small < large < 20
    assert precision_scenario(large)["amount_index_01"] < 0.5


def test_annual_weights_preserve_raw_and_total():
    from fear_temperature.media_diagnostics import year_group_sensitivity

    cells = [
        {"year": 2025, "group": "a", "n": 10},
        {"year": 2026, "group": "a", "n": 80},
        {"year": 2026, "group": "b", "n": 10},
    ]
    raw = year_group_sensitivity(cells, 0, 0)
    assert all(r["per_unit_weight"] == pytest.approx(1) for r in raw["cells"])
    assert raw["weight_only_effective_n"] == pytest.approx(100)
    weighted = year_group_sensitivity(cells, 0.5, 0.5)
    assert sum(r["weighted_n"] for r in weighted["cells"]) == pytest.approx(100)
    assert weighted["annual_shares"][1]["scenario_share"] == pytest.approx(0.75)
    assert weighted["annual_shares"][1]["raw_share"] == pytest.approx(0.9)
    assert 0 < weighted["weight_only_effective_fraction_01"] < 1
    assert cells[1]["n"] == 80
    assert not weighted["expected_population_growth_estimated"]
    assert not weighted["collection_gate"]


def test_year_and_group_weights_are_separate_scenarios():
    from fear_temperature.media_diagnostics import year_group_sensitivity

    cells = [
        {"year": 2025, "group": "a", "n": 10},
        {"year": 2026, "group": "a", "n": 80},
        {"year": 2026, "group": "b", "n": 10},
    ]
    r = year_group_sensitivity(cells, 0, 1)
    assert r["annual_shares"][1]["scenario_share"] == pytest.approx(0.9)
    assert r["cells"][1]["weighted_n"] == pytest.approx(45)
    assert r["cells"][2]["weighted_n"] == pytest.approx(45)
    assert r["annual_total_variation_01"] == pytest.approx(0)
    equal = year_group_sensitivity(cells, 1, 0)
    assert equal["annual_shares"][0]["scenario_share"] == pytest.approx(0.5)
    assert len(equal["annual_shares"]) == 2  # no invented missing years


def test_unknown_feedback_bucket_is_retained():
    from fear_temperature.media_diagnostics import year_group_sensitivity

    r = year_group_sensitivity([{"year": 2026, "group": "unknown", "n": 100}], 0.5, 0.5)
    assert r["cells"][0]["weighted_n"] == pytest.approx(100)
    assert r["cells"][0]["group"] == "unknown"
    assert not r["deletion_recommendation"]
    assert year_group_sensitivity([])["status"] == "no_observed_mass"


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), True])
def test_invalid_weight_scenario_rejected(value):
    from fear_temperature.media_diagnostics import year_group_sensitivity

    with pytest.raises(ValueError):
        year_group_sensitivity([], value, 0)


def test_duplicate_weight_cells_rejected():
    from fear_temperature.media_diagnostics import year_group_sensitivity

    row = {"year": 2026, "group": "a", "n": 2}
    with pytest.raises(ValueError):
        year_group_sensitivity([row, row])
