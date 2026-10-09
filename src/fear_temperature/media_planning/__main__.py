"""Offline CLI over named closed media metadata, never corpus bodies or stores."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from .core import (
    Opportunity,
    Unit,
    assess_coverage,
    composition_decomposition,
    identity_groups,
    pooled_metrics,
    resolve_sources,
    source_month_metrics,
    url_comparison_key,
)
from .parent_monitor import bootstrap_parent_monitor


def rows(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        path.write_text("")
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for k, v in record.items()
                }
            )


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(
    snapshot: Path, output: Path, config_path: Path, coverage_evidence_path: Path | None = None
) -> dict:
    if output.exists():
        raise ValueError("Output must be new; frozen/previous outputs are never overwritten")
    config = json.loads(config_path.read_text())
    if config.get("publication_interval") != ["1988-01-01", "2026-09-21"]:
        raise ValueError("This adapter is bound to the fixed accepted study interval")
    if config.get("article_count_stop") is not None or config.get("coverage_completion_from_count"):
        raise ValueError("Count-based stopping/completion is not supported")
    if "lane_weights" in config or config.get("legacy_two_article_weight") != 0:
        raise ValueError("Coverage weights are not time shares; the legacy floor has zero weight")
    assess_coverage({}, config["coverage_dimension_weights"])
    n = snapshot / "continuations/20261009_newspaper_open_production/worker"
    s = (
        snapshot
        / "social_public_api/continuations/20261009_public_native_expansion"
        / "worker/summaries"
    )
    inputs = [config_path]

    def csv_input(path: Path) -> list[dict]:
        inputs.append(path)
        return rows(path)

    nr = csv_input(n / "CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv")
    parent = {
        r["source_id"]: r["acquisition_parent_family_id"]
        for r in csv_input(n / "SOURCE_PARENT_IDENTITY_REGISTER.csv")
    }
    frontier = csv_input(n / "SOURCE_FRONTIER_REGISTER.csv")
    blocked_sources = {"newspaper:" + r["source_id"] for r in frontier if r.get("blocked_reason")}
    sources_path = s / "source_registry_final.json"
    inputs.append(sources_path)
    social_sources = json.loads(sources_path.read_text())
    registry = {}
    for r in nr:
        key = "newspaper:" + r["source_id"]
        parsed = urlsplit(r["source_url"])
        registry[key] = {
            "stream": "newspaper",
            "source_id": key,
            "label": r["source"],
            "platform_family": "newspaper",
            "stratum": r["stratum"],
            "base_url": f"{parsed.scheme}://{parsed.netloc}",
            "acquisition_parent": parent.get(r["source_id"], ""),
            "parent_evidence": "SOURCE_PARENT_IDENTITY_REGISTER.csv",
            "publisher_independence": "not_established_by_acquisition_parent_alone",
        }
    for r in social_sources:
        key = "social:" + r["source_id"]
        registry[key] = {
            "stream": "social",
            "source_id": key,
            "label": r["title"],
            "platform_family": r.get("platform", "unknown"),
            "stratum": r.get("stratum", "unknown"),
            "base_url": r["base_url"],
            "acquisition_parent": "",
            "parent_evidence": "unknown",
            "publisher_independence": "platform_or_instance_is_not_publisher_independence",
        }
    source_map = resolve_sources(set(registry), config["source_aliases"])
    units = [
        Unit(
            "newspaper",
            "newspaper:" + r["source_id"],
            r["article_id"],
            r["work_family_id"] or r["article_id"],
            r["publication_date"],
            True,
            True,
            r["body_sha256"],
            parent.get(r["source_id"], ""),
        )
        for r in nr
    ]
    sm = csv_input(s / "native_entities_manifest.csv")
    publication = defaultdict(set)
    for r in csv_input(s / "publication_memberships.csv"):
        publication[r["entity_id"]].add(r["publication_key"])
    hashes = defaultdict(set)
    for r in csv_input(s / "content_versions_manifest.csv"):
        if r["body_sha256"]:
            hashes[r["entity_id"]].add(r["body_sha256"])
    date_pending = {r["entity_id"] for r in csv_input(s / "native_date_mapping_limits.csv")}
    conflicts = []
    for r in sm:
        entity = r["entity_id"]
        keys = publication[entity]
        if len(keys) != 1:
            conflicts.append(
                {
                    "entity_id": entity,
                    "issue": "ambiguous_publication_membership",
                    "count": len(keys),
                }
            )
        if len(hashes[entity]) > 1:
            conflicts.append(
                {
                    "entity_id": entity,
                    "issue": "multiple_version_body_hashes",
                    "count": len(hashes[entity]),
                }
            )
        units.append(
            Unit(
                "social",
                "social:" + r["source_id"],
                entity,
                next(iter(keys)) if len(keys) == 1 else "",
                r["native_created_at"],
                r["independently_authored_body"] == "1",
                entity not in date_pending,
                next(iter(hashes[entity])) if len(hashes[entity]) == 1 else "",
            )
        )
    era_states = {
        ("social:" + r["source_id"], r["month"]): r["state"]
        for r in csv_input(s / "source_month_calendar.csv")
    }
    # These accepted artifacts contain no verified source-month ID inventory.
    # A source-wide total or stopped cursor is not a replacement denominator.
    cells = source_month_metrics(
        units, registry, aliases=config["source_aliases"], era_states=era_states
    )
    pooled = pooled_metrics(units, source_map)
    supplied_coverage = {}
    if coverage_evidence_path:
        inputs.append(coverage_evidence_path)
        supplied = json.loads(coverage_evidence_path.read_text())
        if supplied.get("snapshot_ref") != str(snapshot.resolve()):
            raise ValueError("Coverage evidence must reference this exact closed snapshot")
        valid_cells = {(r["stream"], r["month"]) for r in pooled}
        for item in supplied["cells"]:
            key = (item["stream"], item["month"])
            if key not in valid_cells or key in supplied_coverage:
                raise ValueError("Duplicate or out-of-frame coverage evidence cell")
            supplied_coverage[key] = item["dimensions"]
    coverage = [
        {
            "stream": r["stream"],
            "month": r["month"],
            **assess_coverage(
                supplied_coverage.get((r["stream"], r["month"]), {}),
                config["coverage_dimension_weights"],
            ),
        }
        for r in pooled
    ]
    composition = composition_decomposition(cells)
    pub_groups, hash_groups = identity_groups(units)
    parent_stats = bootstrap_parent_monitor(registry, units).snapshot()
    baseline = csv_input(snapshot / "review_20261009/tables/monthly_frame_coverage.csv")
    prior_two = {
        r["month"]
        for r in baseline
        if r["stratum"] == "pooled"
        and "newspaper" in r["analysis_frame"]
        and int(r["known_work_families"]) == 2
    }
    legacy = [
        {
            **r,
            "also_two_before_tranche": r["month"] in prior_two,
            "action": "resume_declared_inventory; no_article_count_stop",
        }
        for r in pooled
        if r["stream"] == "newspaper" and r["exactly_two_known_works_diagnostic"]
    ]
    endpoints = defaultdict(list)
    for key, r in registry.items():
        endpoints[url_comparison_key(r["base_url"])].append(key)
    candidates = [
        {
            "normalized_endpoint": k,
            "sources": sorted(v),
            "status": "candidate_only; endpoint_equality_not_source_equivalence",
        }
        for k, v in sorted(endpoints.items())
        if len(v) > 1
    ]
    source_rows = [
        {
            **r,
            "canonical_source_id": source_map[key],
            "normalized_endpoint_candidate": url_comparison_key(r["base_url"]),
        }
        for key, r in sorted(registry.items())
    ]

    # Plans reference evidence, not executable endpoints or request credentials.
    opportunities = [
        Opportunity(
            "historical:newspaper:1988-1991",
            "historical",
            "unresolved_historical_source_frame",
            "1988-01",
            "1991-01",
            "closed pooled calendar: 37-month gap; route research required",
            action_kind="route_resolution",
            need_priority=0,
        )
    ]
    for source in sorted({r["source_id"] for r in cells if r["stream"] == "newspaper"}):
        selected = [
            r
            for r in cells
            if r["source_id"] == source and r["month"] in prior_two and r["readable_body_entities"]
        ]
        if selected:
            opportunities.append(
                Opportunity(
                    "legacy:" + source,
                    "legacy_recovery",
                    source,
                    selected[0]["month"],
                    selected[-1]["month"],
                    "legacy_floor_months.csv; declare full source-range frontier before requests",
                    blocked=source in blocked_sources,
                    need_priority=1,
                )
            )
    for r in frontier:
        source = "newspaper:" + r["source_id"]
        if source not in registry:
            continue
        blocked = bool(r.get("blocked_reason"))
        try:
            remaining = int(r.get("eligible_unattempted_native_targets") or 0)
        except ValueError:
            remaining = 0
        if remaining:
            opportunities.append(
                Opportunity(
                    "production:" + source,
                    "production",
                    source,
                    "1988-01",
                    "2026-09",
                    "closed SOURCE_FRONTIER_REGISTER.csv; dates pending",
                    blocked=blocked,
                )
            )
    for source, rr in registry.items():
        if rr["stream"] == "newspaper" or any(
            u.source == source and u.countable_body for u in units
        ):
            opportunities.append(
                Opportunity(
                    "continuity:" + source,
                    "continuity",
                    source,
                    "2026-01",
                    "2026-09",
                    "source_month_metrics.csv; check era/access and declared cursor span first",
                    blocked=source in blocked_sources,
                    need_priority=1,
                )
            )
    assert len({o.opportunity_id for o in opportunities}) == len(opportunities)
    summary = {
        "status": "offline_metadata_preparation; not_integrated_or_released",
        "registry_entries": len(registry),
        "canonical_sources": len(set(source_map.values())),
        "confirmed_source_aliases_applied": sum(k != v for k, v in source_map.items()),
        "endpoint_alias_candidates": len(candidates),
        "input_entities": len(units),
        "newspaper_dated_body_entities": sum(
            r["readable_body_entities"] for r in pooled if r["stream"] == "newspaper"
        ),
        "social_dated_independent_body_entities": sum(
            r["readable_body_entities"] for r in pooled if r["stream"] == "social"
        ),
        "known_publication_multimember_groups": len(pub_groups),
        "hash_overlap_candidate_groups": len(hash_groups),
        "legacy_two_work_months": len(legacy),
        "legacy_two_work_months_unchanged": sum(r["also_two_before_tranche"] for r in legacy),
        "source_month_inventory_denominators_verified": 0,
        "count_based_completion_claims": 0,
        "coverage_dimension_weights": config["coverage_dimension_weights"],
        "coverage_cells_with_any_verified_dimension": sum(
            bool(r["resolved_weight_fraction"]) for r in coverage
        ),
        "scheduler": "demand_and_readiness; no_fixed_time_shares",
        "parent_statistics": "six_separate_relations; auxiliary_only; no_collector_feedback",
        "retention_action": "none; source/native IDs, versions and raw evidence unchanged",
        "campus_ids_preserved_outside_this_computation": 9249,
        "limitations": [
            "candidate hashes do not establish duplicate works",
            "acquisition parents do not prove publisher independence",
            "no population denominator or representativeness claim",
            "all opportunities require fresh release/access/resource preflight",
        ],
    }
    assert summary["newspaper_dated_body_entities"] == 9538
    assert summary["social_dated_independent_body_entities"] == 42478
    output.mkdir(parents=True)
    for name, records in {
        "source_registry": source_rows,
        "source_month_metrics": cells,
        "pooled_month_metrics": pooled,
        "coverage_assessment": coverage,
        "composition_decomposition": composition,
        "legacy_floor_months": legacy,
        "identity_conflicts": conflicts,
    }.items():
        write_csv(output / f"{name}.csv", records)
    write_json(output / "source_alias_candidates.json", candidates)
    write_json(output / "publication_groups.json", pub_groups)
    write_json(output / "hash_overlap_candidates.json", hash_groups)
    write_json(output / "parent_source_statistics.json", parent_stats)
    write_json(output / "summary.json", summary)
    write_json(
        output / "input_manifest.json",
        [
            {"path": str(p.resolve()), "sha256": sha(p), "bytes": p.stat().st_size}
            for p in sorted(set(inputs))
        ],
    )
    # Local planning controls stay out of main publication.
    control = output / "control"
    control.mkdir()
    write_json(control / "opportunities.json", [asdict(o) for o in opportunities])
    implementation = sorted(Path(__file__).parent.glob("*.py"))
    write_json(
        output / "RUN_MANIFEST.json",
        {
            "algorithm_version": "media-planning-3",
            "implementation": [{"name": p.name, "sha256": sha(p)} for p in implementation],
            "outputs": [
                {"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size}
                for p in sorted(output.iterdir())
                if p.is_file()
            ],
            "self_excluded": True,
            "execution_mode": "offline_metadata_only",
        },
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--coverage-evidence", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(build(args.snapshot, args.output, args.config, args.coverage_evidence), indent=2)
    )


if __name__ == "__main__":
    main()
