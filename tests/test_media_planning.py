from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from fear_temperature.media_planning.core import (
    COVERAGE_WEIGHTS,
    Opportunity,
    Unit,
    assess_coverage,
    choose_opportunity,
    composition_decomposition,
    execution_guard,
    frontier_metrics,
    identity_groups,
    pooled_metrics,
    resolve_sources,
    source_month_metrics,
    url_comparison_key,
)


def unit(entity="a", source="newspaper:s", key="work:a", day="2026-08-01", **kwargs):
    return Unit("newspaper", source, entity, key, day, True, True, **kwargs)


def test_url_key_does_not_collapse_identity_bearing_query_or_paths():
    assert url_comparison_key("HTTPS://EXAMPLE.ORG:443/A?id=2#x") == "https://example.org/A?id=2"
    assert url_comparison_key("https://example.org/A?id=2") != url_comparison_key(
        "https://example.org/A?id=3"
    )
    assert url_comparison_key("http://example.org/A") != url_comparison_key("https://example.org/A")
    assert url_comparison_key("https://example.org/A/") != url_comparison_key(
        "https://example.org/a"
    )


def test_shared_parent_and_candidate_alias_do_not_merge_sources():
    mapping = resolve_sources(
        {"a", "b"},
        [
            {
                "source_id": "a",
                "canonical_source_id": "b",
                "relation": "same_publisher",
                "status": "confirmed",
                "evidence_ref": "source-register",
            },
            {
                "source_id": "a",
                "canonical_source_id": "b",
                "relation": "same_source",
                "status": "candidate",
                "evidence_ref": "url-match",
            },
        ],
    )
    assert mapping == {"a": "a", "b": "b"}


def test_confirmed_alias_is_reversible_count_view_and_cycles_are_rejected():
    alias = {
        "source_id": "a",
        "canonical_source_id": "b",
        "relation": "same_source",
        "status": "confirmed",
        "evidence_ref": "publisher-declared-alias",
    }
    assert resolve_sources({"a", "b"}, [alias]) == {"a": "b", "b": "b"}
    assert resolve_sources({"a", "b"}, []) == {"a": "a", "b": "b"}
    with pytest.raises(ValueError, match="cycle"):
        resolve_sources(
            {"a", "b"}, [alias, {**alias, "source_id": "b", "canonical_source_id": "a"}]
        )
    with pytest.raises(ValueError, match="evidence"):
        resolve_sources({"a", "b"}, [{**alias, "evidence_ref": ""}])


def test_identical_body_and_different_native_works_remain_distinct():
    a, b = unit(body_hash="same"), unit("b", "newspaper:t", "work:b", body_hash="same")
    pubs, hashes = identity_groups([a, a, b])
    assert not pubs
    assert hashes[0]["count"] == 2
    assert "do_not_merge" in hashes[0]["action"]
    metrics = pooled_metrics([a, a, b], {a.source: a.source, b.source: b.source})
    row = next(r for r in metrics if r["month"] == "2026-08")
    assert row["readable_body_entities"] == row["known_publication_keys"] == 2


def test_known_federated_publication_counts_once_without_deleting_observations():
    a = unit()
    b = unit("b", "newspaper:t", a.publication_key)
    pub, _ = identity_groups([a, b])
    assert pub[0]["count"] == 2
    row = next(
        r
        for r in pooled_metrics([a, b], {a.source: a.source, b.source: b.source})
        if r["month"] == "2026-08"
    )
    assert row["readable_body_entities"] == 2
    assert row["known_publication_keys"] == 1


def test_unknown_denominator_never_becomes_completed_even_at_high_volume():
    units = [unit(str(i), key=f"work:{i}") for i in range(300)]
    registry = {"newspaper:s": {"stream": "newspaper"}}
    result = source_month_metrics(units, registry)
    row = next(r for r in result if r["month"] == "2026-08")
    assert row["known_publication_keys"] == 300
    assert row["body_recovery_fraction"] is None
    assert row["frontier_complete"] is False
    assert row["era_state"] == "historical_scope_unknown"


def inventory(**changes):
    value = {
        "scope_ref": "source-range-v1",
        "inventory_manifest": "sha256:test",
        "snapshot_at": "2026-10-09",
        "unit_namespace": "article",
        "candidate_ids": ["a", "b", "c"],
        "eligible_ids": ["a", "b"],
        "disposition_ids": ["c"],
        "index_exhausted": True,
        "exhaustion_evidence": "native-terminal-page",
    }
    return {**value, **changes}


def test_inventory_exhaustion_does_not_imply_body_completion():
    m = frontier_metrics(inventory(), {"a", "outside-inventory"})
    assert m["body_recovery_fraction"] == 0.5
    assert not m["frontier_complete"]
    assert frontier_metrics(inventory(), {"a", "b"})["frontier_complete"]
    assert not frontier_metrics(inventory(access_blocked=True), {"a", "b"})["frontier_complete"]


def test_unknown_empty_and_invalid_inventory_are_not_fake_100_percent():
    assert frontier_metrics({}, set())["body_recovery_fraction"] is None
    m = frontier_metrics(inventory(candidate_ids=[], eligible_ids=[], disposition_ids=[]), set())
    assert m["body_recovery_fraction"] is None
    assert m["frontier_complete"]  # only an evidenced, scoped empty native inventory
    with pytest.raises(ValueError, match="unique"):
        frontier_metrics(inventory(candidate_ids=["a", "a", "b", "c"]), {"a", "b"})
    with pytest.raises(ValueError, match="inconsistent"):
        frontier_metrics(inventory(disposition_ids=["a", "c"]), {"a", "b"})


def test_date_conflicts_wrappers_and_post_cutoff_do_not_inflate_body_coverage():
    data = [
        unit(),
        replace(unit("bad"), date_usable=False),
        replace(unit("wrapper"), countable_body=False),
        unit("future", day="2026-09-22"),
        unit("cutoff", day="2026-09-21"),
    ]
    rr = pooled_metrics(data, {"newspaper:s": "newspaper:s"})
    assert sum(x["readable_body_entities"] for x in rr) == 2
    assert len(data) == 5
    cells = source_month_metrics(data, {"newspaper:s": {"stream": "newspaper"}})
    assert next(x for x in cells if x["month"] == "2026-09")["calendar_days_in_scope"] == 21


def test_source_entry_decomposition_exposes_collection_composition():
    rows = [
        {"stream": "social", "source_id": s, "month": m, "readable_body_entities": n}
        for s, m, n in [
            ("a", "2026-08", 100),
            ("a", "2026-09", 110),
            ("b", "2026-09", 500),
            ("c", "2026-08", 30),
        ]
    ]
    r = next(x for x in composition_decomposition(rows) if x["to_month"] == "2026-09")
    assert r["count_change"] == 480
    assert r["common_source_change"] == 10
    assert r["appearing_source_bodies"] == 500
    assert r["disappearing_source_bodies"] == 30


def test_pooled_high_counts_and_two_work_diagnostic_never_mark_completion():
    units = [unit("a"), unit("b", key="work:b")]
    row = next(
        x for x in pooled_metrics(units, {"newspaper:s": "newspaper:s"}) if x["month"] == "2026-08"
    )
    assert row["exactly_two_known_works_diagnostic"]
    assert row["single_source_presence"]
    assert row["completion_status"] == "not_inferred_from_count"


def test_scheduler_has_no_fixed_lane_time_share_or_count_stop():
    a = Opportunity("a", "production", "s", "1988-01", "2026-09", "evidence")
    assert all(choose_opportunity([a]) == a for _ in range(100))
    assert choose_opportunity([replace(a, blocked=True)]) is None
    assert choose_opportunity([replace(a, remaining_work=False)]) is None


def test_scheduler_uses_named_need_then_acquisition_and_age():
    a = Opportunity("a", "production", "s", "2020-01", "2026-09", "evidence")
    repair = replace(a, opportunity_id="repair", action_kind="route_resolution")
    assert choose_opportunity([repair, a]) == a
    assert choose_opportunity([replace(repair, need_priority=0), a]).opportunity_id == "repair"
    older = replace(a, opportunity_id="older", need_priority=3, wait_rounds=12)
    assert choose_opportunity([older, replace(a, need_priority=0)]) == older
    # A waiting route is promoted too: prioritizing collection must not starve
    # the unresolved historical route forever.
    assert choose_opportunity([replace(repair, wait_rounds=12), a]).opportunity_id == "repair"
    assert (
        choose_opportunity(
            [replace(repair, wait_rounds=12), replace(a, need_priority=0)]
        ).opportunity_id
        == "repair"
    )
    with pytest.raises(ValueError, match="priority"):
        choose_opportunity([replace(a, need_priority=-1)])


def component(target=("a", "b"), covered=("a",), **changes):
    return {
        "status": "verified",
        "scope_ref": "frame-1-month-2026-08",
        "manifest_ref": "fixture-manifest",
        "unit_namespace": "example-only",
        "target_ids": list(target),
        "covered_ids": list(covered),
        **changes,
    }


def test_coverage_weights_describe_evidence_not_two_article_presence():
    evidence = {name: component() for name in COVERAGE_WEIGHTS}
    result = assess_coverage(evidence)
    assert result["weighted_lower_bound"] == result["weighted_upper_bound"] == 50
    assert result["resolved_weight_fraction"] == 1
    assert not result["completion_claim"]
    full = assess_coverage({name: component(covered=("a", "b")) for name in COVERAGE_WEIGHTS})
    assert full["weighted_lower_bound"] == 100
    assert not full["completion_claim"]  # bounded scope fulfillment is not whole-archive coverage


def test_unknown_dimensions_keep_weight_and_cannot_inflate_completion():
    result = assess_coverage({"identity_date_resolution": component(covered=("a", "b"))})
    assert result["weighted_lower_bound"] == 15
    assert result["weighted_upper_bound"] == 100
    assert result["resolved_weight_fraction"] == 0.15
    assert result["status"] == "partial"
    unknown = assess_coverage({})
    assert unknown["weighted_lower_bound"] == 0
    assert unknown["weighted_upper_bound"] == 100
    assert unknown["resolved_weight_fraction"] == 0


def test_coverage_empty_denominator_is_not_success():
    result = assess_coverage({"inventory_recovery": component(target=(), covered=())})
    assert result["dimensions"]["inventory_recovery"]["status"] == "empty_denominator"
    assert result["weighted_lower_bound"] == 0
    assert result["weighted_upper_bound"] == 100


def test_coverage_inapplicability_requires_evidence_and_changes_denominator_explicitly():
    item = component(status="not_applicable", reason="source did not yet exist")
    result = assess_coverage({name: item for name in COVERAGE_WEIGHTS})
    assert result["weighted_lower_bound"] is None
    assert result["status"] == "all_inapplicable"
    with pytest.raises(ValueError, match="reason"):
        assess_coverage({"inventory_recovery": {**item, "reason": ""}})
    with pytest.raises(ValueError, match="scoped"):
        assess_coverage({"inventory_recovery": {"status": "not_applicable", "reason": "guess"}})


def test_coverage_rejects_duplicate_outside_and_unspecified_target_units():
    with pytest.raises(ValueError, match="unique"):
        assess_coverage({"inventory_recovery": component(target=("a", "a"))})
    with pytest.raises(ValueError, match="subset"):
        assess_coverage({"inventory_recovery": component(covered=("outside",))})
    bad = component()
    del bad["target_ids"]
    with pytest.raises(ValueError, match="enumerate"):
        assess_coverage({"inventory_recovery": bad})


@pytest.mark.parametrize(
    "weights",
    [
        {},
        dict.fromkeys(COVERAGE_WEIGHTS, 1),
        {**COVERAGE_WEIGHTS, "identity_date_resolution": float("nan")},
    ],
)
def test_invalid_coverage_weights_rejected(weights):
    with pytest.raises(ValueError, match="dimensions|weights"):
        assess_coverage({}, weights)


def guard_inputs():
    now = datetime(2026, 10, 9, tzinfo=UTC)
    return dict(
        now=now,
        deadline=now + timedelta(hours=8),
        released=True,
        source_allowed=True,
        free_bytes=60 * 1024**3,
        own_pending_bytes=1024,
        other_leases_bytes=1024,
        retained_bytes=100,
        allocation_bytes=100000,
        actual_retained_growth_bytes=1000,
        stream_retained_bytes=20,
        stream_allocation_bytes=100000,
        request_headroom=100,
        requests_needed=1,
        object_headroom=1000,
        objects_needed=50,
    )


def test_guard_requires_release_and_actual_resources_despite_free_disk():
    params = guard_inputs()
    assert execution_guard(**params) == []
    issues = execution_guard(**{**params, "released": False, "stream_allocation_bytes": 1000})
    assert issues == ["no_active_release", "stream_retained_allocation"]
    assert "deadline_absent_or_expired" in execution_guard(**{**params, "deadline": params["now"]})
    assert "source_access_not_released" in execution_guard(**{**params, "source_allowed": False})
    assert "physical_operation_capacity" in execution_guard(
        **{**params, "own_pending_bytes": 50 * 1024**3}
    )
    assert "native_object_capacity" in execution_guard(**{**params, "objects_needed": 1001})


def test_conflicting_versions_need_a_declared_snapshot_instead_of_last_row_wins():
    a = unit()
    b = replace(a, publication_key="different-work")
    with pytest.raises(ValueError, match="Conflicting"):
        pooled_metrics([a, b], {a.source: a.source})
    with pytest.raises(ValueError, match="Conflicting"):
        source_month_metrics([a, b], {a.source: {"stream": "newspaper"}})


def test_corrected_entity_date_cannot_silently_count_in_two_months():
    a = unit()
    b = replace(a, publication_day="2026-07-01")
    with pytest.raises(ValueError, match="date/version"):
        pooled_metrics([a, b], {a.source: a.source})


def test_source_alias_cannot_merge_newspaper_and_social_frames():
    with pytest.raises(ValueError, match="Cross-stream"):
        resolve_sources(
            {"newspaper:a", "social:a"},
            [
                {
                    "source_id": "newspaper:a",
                    "canonical_source_id": "social:a",
                    "status": "confirmed",
                    "relation": "same_source",
                    "evidence_ref": "assertion",
                }
            ],
        )
