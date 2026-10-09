"""Transparent coverage evidence; never a corpus-quality or inclusion gate."""

from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit

START = date(1988, 1, 1)
END = date(2026, 9, 21)
COVERAGE_WEIGHTS = {
    "inventory_recovery": 0.40,
    "source_frame_breadth": 0.25,
    "publication_period_recovery": 0.20,
    "identity_date_resolution": 0.15,
}


def months() -> list[str]:
    return [
        f"{year}-{month:02d}"
        for year in range(START.year, END.year + 1)
        for month in range(1, 13)
        if (year, month) <= (END.year, END.month)
    ]


def eligible_day(value: str) -> str | None:
    """Retain the reported calendar date; do not shift local publication dates to UTC."""
    try:
        parsed = date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None
    return parsed.isoformat() if START <= parsed <= END else None


def url_comparison_key(value: str) -> str:
    """Conservative candidate comparison only; not a native/source identity rule.

    Keep scheme, path case, query order, unknown parameters and trailing slash.
    Never identify sources by registrable domain or strip feed/API paths.
    """
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Expected an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("Credential-bearing URLs are not source identifiers")
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    port = parsed.port
    if port and not (
        (port == 80 and parsed.scheme.lower() == "http")
        or (port == 443 and parsed.scheme.lower() == "https")
    ):
        host += f":{port}"
    return urlunsplit((parsed.scheme.lower(), host, parsed.path, parsed.query, ""))


def resolve_sources(source_ids: set[str], aliases: list[dict[str, str]]) -> dict[str, str]:
    """Only explicit, evidenced SAME-SOURCE aliases can change a counting view.

    Canonical targets must be stable registry IDs, never a content hash. A shared
    platform, publisher, domain, ownership change or similar title is insufficient.
    The caller supplies a versioned/as-of applicable assertion set.
    """
    links: dict[str, str] = {}
    for row in aliases:
        if row.get("status") != "confirmed" or row.get("relation") != "same_source":
            continue
        if not row.get("evidence_ref"):
            raise ValueError("Confirmed alias requires evidence")
        source, target = row["source_id"], row["canonical_source_id"]
        if ":" in source and ":" in target and source.split(":")[0] != target.split(":")[0]:
            raise ValueError("Cross-stream source aliases cannot collapse analytical frames")
        if source not in source_ids or target not in source_ids:
            raise ValueError("Alias endpoint absent from registry")
        if source == target:
            continue
        if source in links and links[source] != target:
            raise ValueError("Conflicting canonical source assertions")
        links[source] = target
    result = {}
    for source in sorted(source_ids):
        path = set()
        current = source
        while current in links:
            if current in path:
                raise ValueError("Canonical source cycle")
            path.add(current)
            current = links[current]
        result[source] = current
    return result


@dataclass(frozen=True)
class Unit:
    stream: str
    source: str
    entity_id: str
    publication_key: str
    publication_day: str
    countable_body: bool
    date_usable: bool
    body_hash: str = ""
    acquisition_parent: str = ""


def validate_snapshot(units: list[Unit]) -> None:
    """Persistent entity IDs are global within a stream; versions are not rows here."""
    seen = {}
    for unit in units:
        key = (unit.stream, unit.entity_id)
        if key in seen and seen[key] != unit:
            raise ValueError("Conflicting entity snapshot, including date/version changes")
        seen[key] = unit


def identity_groups(units: list[Unit]) -> tuple[list[dict], list[dict]]:
    """Counting memberships preserve every entity; hash equality stays a candidate."""
    validate_snapshot(units)
    publications: dict[tuple, set] = defaultdict(set)
    bodies: dict[tuple, set] = defaultdict(set)
    for u in units:
        if u.publication_key and u.countable_body:
            publications[(u.stream, u.publication_key)].add((u.source, u.entity_id))
        if u.body_hash:
            bodies[(u.stream, u.body_hash)].add((u.source, u.entity_id))
    pub_rows = [
        {
            "stream": stream,
            "publication_key": key,
            "members": sorted(members),
            "count": len(members),
            "action": "retain_members; shared_counting_key_only",
        }
        for (stream, key), members in sorted(publications.items())
        if len(members) > 1
    ]
    hash_rows = [
        {
            "stream": stream,
            "body_sha256": key,
            "members": sorted(members),
            "count": len(members),
            "action": "candidate_only; do_not_merge_or_delete",
        }
        for (stream, key), members in sorted(bodies.items())
        if len(members) > 1
    ]
    return pub_rows, hash_rows


def frontier_metrics(evidence: dict, loaded_entities: set[str]) -> dict:
    """Completeness is scoped to a declared, evidenced native inventory snapshot.

    Eligible IDs and disposition IDs must partition an enumerated unique-ID set.
    A stopped endpoint or an empty return alone cannot certify exhaustion.
    """
    required = ["scope_ref", "inventory_manifest", "snapshot_at", "unit_namespace"]
    if not all(evidence.get(k) for k in required):
        return {
            "inventory_status": "unknown",
            "candidate_count": None,
            "body_recovery_fraction": None,
            "frontier_complete": False,
        }
    candidates = set(evidence.get("candidate_ids", []))
    eligible = set(evidence.get("eligible_ids", []))
    dispositions = set(evidence.get("disposition_ids", []))
    if not (eligible | dispositions) <= candidates or eligible & dispositions:
        raise ValueError("Inventory dispositions are inconsistent")
    if len(candidates) != len(evidence.get("candidate_ids", [])):
        raise ValueError("Inventory must enumerate unique native IDs")
    resolved = eligible | dispositions
    loaded = eligible & loaded_entities
    complete = bool(
        evidence.get("exhaustion_evidence")
        and evidence.get("index_exhausted")
        and resolved == candidates
        and loaded == eligible
        and not evidence.get("access_blocked")
    )
    return {
        "inventory_status": "declared_frontier_complete" if complete else "partial",
        "candidate_count": len(candidates),
        "eligible_count": len(eligible),
        "eligibility_unresolved": len(candidates - resolved),
        "loaded_eligible": len(loaded),
        "body_recovery_fraction": len(loaded) / len(eligible) if eligible else None,
        "frontier_complete": complete,
        "scope_limit": "declared observed interface snapshot only; not whole historical population",
    }


def source_month_metrics(
    units: list[Unit],
    registry: dict[str, dict],
    *,
    aliases: list[dict] | None = None,
    inventories: dict[tuple[str, str], dict] | None = None,
    era_states: dict[tuple[str, str], str] | None = None,
) -> list[dict]:
    """Produce source-month cells without inventing eras or denominator coverage."""
    validate_snapshot(units)
    alias_map = resolve_sources(set(registry), aliases or [])
    buckets: dict[tuple, dict[str, Unit]] = defaultdict(dict)
    undated: Counter = Counter()
    for u in units:
        source = alias_map[u.source]
        day = eligible_day(u.publication_day) if u.date_usable else None
        if day:
            old = buckets[(source, day[:7])].get(u.entity_id)
            if old and old != u:
                raise ValueError("Provide one accepted entity state, not conflicting versions")
            buckets[(source, day[:7])][u.entity_id] = u
        else:
            undated[source] += 1
    result = []
    for source in sorted(set(alias_map.values())):
        for month in months():
            members = list(buckets[(source, month)].values())
            bodies = [u for u in members if u.countable_body]
            keys = {u.publication_key for u in bodies if u.publication_key}
            state = (era_states or {}).get((source, month), "historical_scope_unknown")
            frontier = frontier_metrics(
                (inventories or {}).get((source, month), {}), {u.entity_id for u in bodies}
            )
            result.append(
                {
                    "stream": registry[source]["stream"],
                    "source_id": source,
                    "month": month,
                    "dated_entities": len(members),
                    "readable_body_entities": len(bodies),
                    "known_publication_keys": len(keys),
                    "publication_key_missing": sum(not u.publication_key for u in bodies),
                    "observed_publication_days": len({u.publication_day[:10] for u in bodies}),
                    "observation_state": "observed_body" if bodies else "not_observed",
                    "era_state": state,
                    "partial_month": month == "2026-09",
                    "calendar_days_in_scope": END.day
                    if month == "2026-09"
                    else calendar.monthrange(int(month[:4]), int(month[5:]))[1],
                    **frontier,
                }
            )
    return result


def pooled_metrics(units: list[Unit], source_map: dict[str, str]) -> list[dict]:
    validate_snapshot(units)
    by: dict[tuple, dict[str, Unit]] = defaultdict(dict)
    for u in units:
        day = eligible_day(u.publication_day) if u.date_usable else None
        if day and u.countable_body:
            key = (u.stream, day[:7])
            if u.entity_id in by[key] and by[key][u.entity_id] != u:
                raise ValueError("Conflicting entity observations")
            by[key][u.entity_id] = u
    result = []
    for stream in sorted({u.stream for u in units}):
        for month in months():
            members = list(by[(stream, month)].values())
            counts = Counter(source_map[u.source] for u in members)
            known = {u.publication_key for u in members if u.publication_key}
            result.append(
                {
                    "stream": stream,
                    "month": month,
                    "readable_body_entities": len(members),
                    "known_publication_keys": len(known),
                    "observed_sources": len(counts),
                    "observed_acquisition_parents": len(
                        {u.acquisition_parent for u in members if u.acquisition_parent}
                    ),
                    "sources_without_parent_mapping": len(
                        {source_map[u.source] for u in members if not u.acquisition_parent}
                    ),
                    "largest_source_share": max(counts.values()) / len(members)
                    if members
                    else None,
                    "single_source_presence": len(counts) == 1,
                    "exactly_two_known_works_diagnostic": len(known) == 2,
                    "completion_status": "not_inferred_from_count",
                }
            )
    return result


def composition_decomposition(cells: list[dict]) -> list[dict]:
    """Exact adjacent-month identity: delta = common + appearing - disappearing.

    Appearance is in the collected body view, not platform founding or entry into
    the actual public population. No expression/causal change is inferred.
    """
    by: dict[tuple, dict] = defaultdict(dict)
    for r in cells:
        if r["readable_body_entities"]:
            by[(r["stream"], r["month"])][r["source_id"]] = r["readable_body_entities"]
    result = []
    for stream in sorted({r["stream"] for r in cells}):
        for before, after in zip(months(), months()[1:], strict=False):
            p, q = by[(stream, before)], by[(stream, after)]
            common = set(p) & set(q)
            within = sum(q[s] - p[s] for s in common)
            entering = sum(q[s] for s in set(q) - set(p))
            leaving = sum(p[s] for s in set(p) - set(q))
            delta = sum(q.values()) - sum(p.values())
            assert delta == within + entering - leaving
            union = set(p) | set(q)
            result.append(
                {
                    "stream": stream,
                    "from_month": before,
                    "to_month": after,
                    "count_change": delta,
                    "common_source_change": within,
                    "appearing_source_bodies": entering,
                    "disappearing_source_bodies": leaving,
                    "appearing_sources": sorted(set(q) - set(p)),
                    "disappearing_sources": sorted(set(p) - set(q)),
                    "observed_source_jaccard": len(common) / len(union) if union else None,
                    "interpretation": "collection composition diagnostic; no event inference",
                }
            )
    return result


def assess_coverage(evidence: dict[str, dict], weights: dict[str, float] | None = None) -> dict:
    """Weighted accounting of four explicit evidence dimensions, not readiness.

    Weights express a provisional reporting preference, not fitted probabilities,
    time shares, retention weights or sampling weights. Unknown components retain
    their weight as an uncertainty range; they cannot silently disappear.
    Each verified component enumerates unique target/covered units in one declared
    scope. This is deliberately separate from the acquisition scheduler.
    """
    weights = COVERAGE_WEIGHTS if weights is None else weights
    if set(weights) != set(COVERAGE_WEIGHTS) or set(evidence) - set(COVERAGE_WEIGHTS):
        raise ValueError("Exactly the four named coverage dimensions are supported")
    if any(not 0 < w <= 1 for w in weights.values()) or abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("Positive finite coverage weights must sum to one")
    dimensions = {}
    lower = unknown = applicable_weight = known_weight = 0.0
    for name, weight in weights.items():
        item = evidence.get(name, {})
        state = item.get("status", "unknown")
        if state not in {"verified", "unknown", "not_applicable"}:
            raise ValueError("Unrecognized coverage evidence state")
        required = ("scope_ref", "manifest_ref", "unit_namespace")
        if state != "unknown" and not all(item.get(k) for k in required):
            raise ValueError("Verified or inapplicable dimensions require scoped evidence")
        row = {
            "status": state,
            "base_weight": weight,
            "ratio": None,
            "numerator": None,
            "denominator": None,
            "evidence": {k: item.get(k) for k in required},
            "reason": item.get("reason", ""),
        }
        if state == "not_applicable":
            if not item.get("reason"):
                raise ValueError("Inapplicability requires an evidenced reason")
        else:
            applicable_weight += weight
            if state == "verified":
                if "target_ids" not in item or "covered_ids" not in item:
                    raise ValueError("Verified evidence must enumerate target and covered IDs")
                target, covered = set(item["target_ids"]), set(item["covered_ids"])
                if len(target) != len(item["target_ids"]) or len(covered) != len(
                    item["covered_ids"]
                ):
                    raise ValueError("Coverage evidence must enumerate unique IDs")
                if not covered <= target:
                    raise ValueError("Covered IDs must be a subset of the declared target")
                row.update(numerator=len(covered), denominator=len(target))
                if target:
                    row["ratio"] = len(covered) / len(target)
                    lower += weight * row["ratio"]
                    known_weight += weight
                else:
                    row["status"] = "empty_denominator"
                    unknown += weight
            else:
                unknown += weight
        dimensions[name] = row
    return {
        "dimensions": dimensions,
        "weighted_lower_bound": 100 * lower / applicable_weight if applicable_weight else None,
        "weighted_upper_bound": 100 * (lower + unknown) / applicable_weight
        if applicable_weight
        else None,
        "resolved_weight_fraction": known_weight / applicable_weight if applicable_weight else None,
        "applicable_weight": applicable_weight,
        "status": "all_inapplicable"
        if not applicable_weight
        else "partial"
        if unknown
        else "measured",
        "completion_claim": False,
        "interpretation": (
            "provisional scope-fulfillment accounting; "
            "not population coverage or a statistical confidence interval"
        ),
    }


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    lane: str
    source_id: str
    first_month: str
    last_month: str
    evidence_ref: str
    remaining_work: bool = True
    blocked: bool = False
    wait_rounds: int = 0
    action_kind: str = "acquisition"
    need_priority: int = 2


def choose_opportunity(
    opportunities: list[Opportunity],
) -> Opportunity | None:
    """Demand/readiness scheduling without time quotas or coverage-score rewards.

    Named unresolved needs determine priority; prefer acquisition at equal need
    and age bounded batches to avoid starving old or harder source routes.
    Lane is a reporting label, never a fixed share. A runner updates remaining,
    blocked/cooldown and waiting states after each real operation.
    """
    for o in opportunities:
        if not o.evidence_ref or o.action_kind not in {"acquisition", "route_resolution"}:
            raise ValueError("Missing opportunity evidence or unknown action kind")
        if o.need_priority not in range(4) or o.wait_rounds < 0:
            raise ValueError("Need priority must be 0..3 and waiting rounds nonnegative")
    eligible = [o for o in opportunities if o.remaining_work and not o.blocked]
    if not eligible:
        return None
    # Promote waiting needs every four completed bounded batches. A necessary
    # route repair can outrank routine production, without reserving a time share.
    return min(
        eligible,
        key=lambda o: (
            max(0, o.need_priority - o.wait_rounds // 4),
            -o.wait_rounds,
            o.action_kind != "acquisition",
            o.opportunity_id,
        ),
    )


def execution_guard(
    *,
    now: datetime,
    deadline: datetime | None,
    released: bool,
    source_allowed: bool,
    free_bytes: int,
    own_pending_bytes: int,
    other_leases_bytes: int,
    retained_bytes: int,
    allocation_bytes: int,
    actual_retained_growth_bytes: int,
    stream_retained_bytes: int,
    stream_allocation_bytes: int,
    request_headroom: int,
    requests_needed: int,
    object_headroom: int,
    objects_needed: int,
) -> list[str]:
    """Pure prospective preflight contract; never an authorization or live check.

    A production adapter must obtain all values under the shared resource lock,
    hold its stream writer mutex and bind a fresh release before using this result.
    Pending bytes is PEAK additional footprint, including journal/export overhead.
    """
    values = [
        free_bytes,
        own_pending_bytes,
        other_leases_bytes,
        retained_bytes,
        allocation_bytes,
        actual_retained_growth_bytes,
        stream_retained_bytes,
        stream_allocation_bytes,
        request_headroom,
        requests_needed,
        object_headroom,
        objects_needed,
    ]
    if any(x < 0 for x in values):
        raise ValueError("Resource inputs cannot be negative")
    issues = []
    if not released:
        issues.append("no_active_release")
    if deadline is None or now >= deadline:
        issues.append("deadline_absent_or_expired")
    if not source_allowed:
        issues.append("source_access_not_released")
    floor = 15 * 1024**3
    recovery = 48 * 1024**2
    receipt_reserve = 64 * 1024
    if free_bytes - floor - recovery - other_leases_bytes - own_pending_bytes - receipt_reserve < 0:
        issues.append("physical_operation_capacity")
    if (
        retained_bytes + actual_retained_growth_bytes + other_leases_bytes + receipt_reserve
        > allocation_bytes
    ):
        issues.append("shared_retained_allocation")
    if (
        stream_retained_bytes + actual_retained_growth_bytes + receipt_reserve
        > stream_allocation_bytes
    ):
        issues.append("stream_retained_allocation")
    if requests_needed > request_headroom:
        issues.append("request_capacity")
    if objects_needed > object_headroom:
        issues.append("native_object_capacity")
    return issues
