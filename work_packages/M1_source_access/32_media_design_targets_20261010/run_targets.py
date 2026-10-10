"""Generate actionable conditional source/amount targets from closed metadata."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from fear_temperature.media_design_targets import (
    append_mass_lower_bound,
    design_requirements,
    minimum_groups_for_influence,
    required_effective_groups,
    required_units,
)
from fear_temperature.media_diagnostics import parent_profile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PACKAGE = ROOT / "work_packages/M1_source_access/27_newspaper_context_recovery_20261008"
NEWSPAPER = PACKAGE / "continuations/20261010_broader_history_four_hour/worker"
SOCIAL = PACKAGE / "social_public_api/continuations/20261010_broader_history_four_hour/worker"

FORUM_CLASSES = {
    "straight_dope": "general_discussion",
    "tildes": "general_discussion",
    "ilxor": "general_discussion",
    "thesession": "culture_hobbies",
    "python_discourse": "technical_scientific",
    "osm_discourse": "technical_scientific",
    "hackernews": "technical_scientific",
    "se_earthscience": "technical_scientific",
    "se_sustainability": "technical_scientific",
}


def classification(stream: str, source: str) -> tuple[str, str]:
    """Provisional source-purpose metadata; no content/topic/emotion classifier."""
    if stream == "newspaper":
        if source in {"green_left", "workers_advocate", "militant_uk_archive"}:
            return "newspaper_title", "advocacy"
        if source == "financial_mirror":
            return "newspaper_title", "specialist_business"
        if source in {"otago_daily_times", "indaily", "devonport_flagstaff",
                      "northern_rivers_times", "montpelier_bridge", "camden_new_journal",
                      "falls_church_news_press", "galway_advertiser", "limerick_post",
                      "newtown_bee"}:
            return "newspaper_title", "regional_local_general"
        return "newspaper_title", "unresolved"
    if source in FORUM_CLASSES:
        return "named_forum_like_community_candidate", FORUM_CLASSES[source]
    if source in {"python_list_archive", "w3_wwwtalk"}:
        return "mailing_list_archive", "technical_scientific"
    if source.startswith(("dowire_", "mpls_")):
        return "mailing_list_archive", "local_civic"
    if source in {"aussie_zone", "feddit_org", "lemmy_nz", "midwest_social"}:
        return "federated_instance_community_mapping_pending", "mixed_unresolved"
    if source.startswith("mastodon_") or source == "bluesky":
        return "social_feed", "mixed_unresolved"
    return "unresolved", "unresolved"


def write_csv(name: str, rows: list[dict]) -> None:
    with (HERE / "results" / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    (HERE / "results").mkdir(exist_ok=True)
    paths = {
        "newspaper_register": NEWSPAPER / "CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv",
        "newspaper_summary": NEWSPAPER / "DELIVERY_SUMMARY.json",
        "social_calendar": SOCIAL / "summaries/source_month_calendar.csv",
        "social_summary": SOCIAL / "summaries/collection_manifest.json",
    }
    data = {k: p.read_bytes() for k, p in paths.items()}
    cells = {s: defaultdict(Counter) for s in ["newspaper", "social"]}
    for row in csv.DictReader(data["newspaper_register"].decode().splitlines()):
        cells["newspaper"][row["publication_date"][:7]][row["source_id"]] += 1
    for row in csv.DictReader(data["social_calendar"].decode().splitlines()):
        amount = int(row["usable_dated_independent_bodies"])
        if amount:
            cells["social"][row["month"]][row["source_id"]] += amount
    assert sum(sum(v.values()) for v in cells["newspaper"].values()) == json.loads(
        data["newspaper_summary"])["current_newspaper_complete_IDs"]
    assert sum(sum(v.values()) for v in cells["social"].values()) == json.loads(
        data["social_summary"])["usable_dated_body_total"]

    totals = {stream: sum(months.values(), Counter()) for stream, months in cells.items()}
    tax_rows, class_rows, annual_rows, dilution_rows = [], [], [], []
    for stream, sources in totals.items():
        classes = defaultdict(Counter)
        for source, count in sources.items():
            kind, purpose = classification(stream, source)
            classes[(kind, purpose)][source] = count
            tax_rows.append({
                "stream": stream, "source_id": source, "count": count,
                "unit_type_provisional": kind, "purpose_provisional": purpose,
                "parent_mapping": "not_verified_by_this_run",
                "classification_status": "proposed_from_existing_source_identity_metadata",
                "forum_count_status": "candidate_not_parent_verified" if source in FORUM_CLASSES
                else "not_counted_as_one_named_forum",
            })
        for (kind, purpose), counts in classes.items():
            class_rows.append({
                "stream": stream, "kind": kind, "purpose": purpose,
                "source_ids": len(counts), "bodies": sum(counts.values()),
                "mass_share": sum(counts.values()) / sum(sources.values()),
                "effective_source_ids": parent_profile(list(counts.values()))["effective_groups"],
                "independent_parents": "unknown",
            })
        for year in range(1988, 2027):
            counts = sum((c for m, c in cells[stream].items()
                          if m.startswith(str(year))), Counter())
            prof = parent_profile(list(counts.values()))
            annual_rows.append({
                "stream": stream, "year": year, "n": prof["n"],
                "source_ids": prof["groups"], "effective_source_ids": prof["effective_groups"],
                "largest_share": max(counts.values()) / prof["n"] if counts else None,
                "parent_status": "source_proxy_only", "partial_year": year == 2026,
            })
        for tolerance in [.20, .10, .075, .05]:
            dilution_rows.append({
                "stream": stream, "largest_group_tolerance": tolerance,
                "necessary_group_count": minimum_groups_for_influence(tolerance),
                "optimistic_extra_nonleading_bodies": append_mass_lower_bound(
                    list(sources.values()), tolerance),
                "purpose": "demonstrate_cost_of_raw_pool_dilution_not_a_collection_target",
            })
    write_csv("SOURCE_CLASSIFICATION_PROPOSAL.csv", tax_rows)
    write_csv("CATEGORY_GAPS_BASELINE.csv", class_rows)
    required_classes = {
        "newspaper": ["national_general", "regional_local_general"],
        "social": ["general_discussion", "local_civic", "household_consumer",
                   "travel_transport", "outdoor", "culture_hobbies", "technical_scientific"],
    }
    category_requirements = []
    for stream, purposes in required_classes.items():
        for purpose in purposes:
            candidates = [r for r in tax_rows if r["stream"] == stream
                          and r["purpose_provisional"] == purpose
                          and (stream == "newspaper" or r["source_id"] in FORUM_CLASSES)]
            category_requirements.append({
                "stream": stream, "proposed_frame_component": purpose,
                "candidate_title_or_forum_communities": len(candidates),
                "candidate_bodies": sum(r["count"] for r in candidates),
                "state": "no_named_candidate_identified" if not candidates
                else "presence_only_depth_and_parents_unverified",
                "next_requirement": "Verify source/era identity and native archive inventory; "
                "use inverse requirements for any declared category-specific inference",
                "equal_category_output_quota": False,
            })
    write_csv("CATEGORY_REQUIREMENTS.csv", category_requirements)
    era_rows = []
    for stream, months in cells.items():
        for start, end in [(1988, 1990), (1991, 2003), (2004, 2012),
                           (2013, 2020), (2021, 2026)]:
            by_class = defaultdict(Counter)
            for month, sources in months.items():
                if start <= int(month[:4]) <= end:
                    for source, count in sources.items():
                        kind, purpose = classification(stream, source)
                        by_class[(kind, purpose)][source] += count
            for (kind, purpose), counts in by_class.items():
                era_rows.append({
                    "stream": stream, "start_year": start, "end_year": end,
                    "kind": kind, "purpose": purpose, "source_ids": len(counts),
                    "bodies": sum(counts.values()),
                    "effective_source_ids": parent_profile(
                        list(counts.values()))["effective_groups"],
                    "classification_verified": False,
                })
    write_csv("ERA_CLASS_SUPPORT.csv", era_rows)
    write_csv("ANNUAL_SOURCE_SUPPORT.csv", annual_rows)
    write_csv("RAW_POOL_DILUTION_LOWER_BOUNDS.csv", dilution_rows)

    targets = []
    for margin in [.10, .075, .05]:
        for rho in [.01, .05, .10]:
            for n in [250, 500, 1000]:
                groups = required_effective_groups(n, margin, rho)
                targets.append({
                    "nominal_95pct_margin": margin, "assumed_rho": rho,
                    "planned_bodies_per_time_cell": n,
                    "effective_groups_needed": groups,
                    "necessary_integer_group_count": None if groups is None else math.ceil(groups),
                    "status": "infeasible_even_if_independent" if groups is None
                    else "conditional_requirement_not_estimated_normality",
                })
    write_csv("SOURCE_COUNT_REQUIREMENTS.csv", targets)

    amounts = []
    for margin in [.10, .075, .05]:
        for rho in [.01, .05, .10]:
            for groups in [5, 10, 20, 30, 50]:
                amounts.append({
                    "nominal_95pct_margin": margin, "assumed_rho": rho,
                    "planned_effective_groups": groups,
                    "bodies_needed": required_units(groups, margin, rho),
                    "unit": "one_month_or_other_declared_time_cell_not_whole_corpus",
                })
    write_csv("AMOUNT_REQUIREMENTS.csv", amounts)

    monthly = []
    calendar = [f"{year}-{month:02}" for year in range(1988, 2027)
                for month in range(1, 13) if (year, month) <= (2026, 9)]
    for stream, months in cells.items():
        for month in calendar:
            for margin in [.10, .075, .05]:
                for rho in [.01, .05, .10]:
                    tolerance = .05 if margin == .05 else .10
                    monthly.append({
                        "stream": stream, "month": month, "margin": margin,
                        "rho_assumed": rho, "influence_tolerance": tolerance,
                        **design_requirements(list(months[month].values()), margin=margin,
                                              rho=rho, influence_tolerance=tolerance),
                        "group_basis": "unverified_source_ID_proxy",
                        "archive_denominator": "unknown",
                        "zero_state": "unresolved_full_calendar_gap_not_zero_expression"
                        if not months[month] else "observed_source_presence",
                    })
    write_csv("MONTHLY_DESIGN_GAPS.csv", monthly)
    matched = []
    for stream, months in cells.items():
        year_totals = {
            year: sum(sum(counts.values()) for month, counts in months.items()
                      if month.startswith(str(year)) and month[-2:] <= "08")
            for year in range(2016, 2027)
        }
        total = sum(year_totals.values())
        for year, amount in year_totals.items():
            matched.append({
                "stream": stream, "year": year, "matched_months": "January-August",
                "n": amount, "share_of_2016_2026_matched_window": amount / total,
                "source_mixture_matched": False,
                "interpretation": "matched_calendar_only; still affected by source composition",
            })
    write_csv("MATCHED_RECENT_YEAR_SHARES.csv", matched)
    summary = {
        "input_hashes": {k: {"path": str(paths[k].relative_to(ROOT)),
                             "sha256": hashlib.sha256(v).hexdigest()}
                         for k, v in data.items()},
        "inputs_are_closed_metadata": True,
        "newspaper_title_goal_user_minimum": 50,
        "newspaper_contributing_title_ids": len(totals["newspaper"]),
        "newspaper_nominal_title_gap": max(0, 50 - len(totals["newspaper"])),
        "forum_goal_interpretation": "more than 20 = at least 21; no count-based collection stop",
        "forum_like_named_community_candidates": sum(s in FORUM_CLASSES for s in totals["social"]),
        "forum_verified_independent_parent_count": None,
        "forum_candidate_gap_to_21": max(0, 21 - sum(s in FORUM_CLASSES for s in totals["social"])),
        "classification_verified": False,
        "working_scenario": {
            "margin": .075, "rho_assumed": .05, "influence_tolerance": .10,
            "per_stream": {
                stream: {
                    "maximum_observed_sources_in_one_month": max(
                        r["nominal_groups"] for r in monthly if r["stream"] == stream),
                    "maximum_effective_source_ids_in_one_month": max(
                        r["effective_groups"] or 0 for r in monthly if r["stream"] == stream),
                    "months_meeting_conditional_scenario": sum(
                        r["scenario_met"] for r in monthly if r["stream"] == stream
                        and r["margin"] == .075 and r["rho_assumed"] == .05),
                } for stream in cells
            },
            "not_an_estimated_ICC_or_universal_quality_rule": True,
        },
        "monthly_scenarios": len(monthly),
        "corpus_quality_certified": False,
        "quality_blockers": [
            "No verified time-varying parent mapping for the full frame",
            "Unknown source-era archive inventory denominators",
            "Source-purpose taxonomy is a proposal, not independently adjudicated",
            "No validated analysis outcome or fitted within-parent correlation",
            "Collection is purposive; model precision cannot repair selection bias",
        ],
        "retention_or_dispatch_actions": "none",
    }
    (HERE / "results/SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "input_hashes"}, indent=2))


if __name__ == "__main__":
    main()
