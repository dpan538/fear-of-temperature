#!/usr/bin/env python3
"""Automated integrity checks for the Priority 180 coverage gate."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "data" / "fear-temperature" / "exports"
P180 = ROOT / "data" / "fear-temperature" / "priority180"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    master = rows(EXPORTS / "priority180_full_coverage_matrix.csv")
    dictionary = rows(EXPORTS / "dictionary_coverage_180.csv")
    dictionary_unique = rows(EXPORTS / "dictionary_unique_forms.csv")
    search = rows(EXPORTS / "search_statistics_180.csv")
    search_long = rows(EXPORTS / "search_statistics_long.csv")
    ngram = rows(EXPORTS / "priority180_ngram_coverage.csv")
    execution = rows(P180 / "ngram" / "ngram_measurement_execution.csv")
    annual = rows(P180 / "ngram" / "ngram_timeseries_priority_measurements.csv")
    reconciliation = json.loads((P180 / "ngram" / "baseline_reconciliation.json").read_text(encoding="utf-8"))

    for name, population in [("master", master), ("dictionary", dictionary), ("search", search), ("ngram", ngram)]:
        require(len(population) == 180, f"{name} must contain exactly 180 candidate rows")
        require(len({r["candidate_id"] for r in population}) == 180, f"{name} candidate IDs must be unique")
    ids = {r["candidate_id"] for r in master}
    require(ids == {r["candidate_id"] for r in dictionary} == {r["candidate_id"] for r in search} == {r["candidate_id"] for r in ngram}, "Candidate populations diverge")

    allowed_coverage = {
        "FULLY_COVERED", "FULLY_ACCOUNTED_WITH_NGRAM_ALIAS",
        "FULLY_ACCOUNTED_NGRAM_TECHNICALLY_UNREPRESENTABLE",
    }
    require(all(r["coverage_status"] in allowed_coverage for r in master), "Unexplained or invalid coverage state")
    require(all(r["ngram_mapping_type"] in {"EXACT", "NORMALIZED_VARIANT", "VALIDATED_ALIAS", "TECHNICALLY_UNREPRESENTABLE"} for r in master), "Missing Ngram accounting")
    require(all(r["dictionary_status"] in {"DIRECT_HEADWORD", "TECHNICAL_GLOSSARY", "NO_STANDALONE_HEADWORD", "UNRESOLVED"} for r in master), "Missing dictionary accounting")
    require(all(r["search_status"] in {"COMPLETED_ZERO", "COMPLETED_NONZERO"} for r in master), "Missing primary search accounting")

    execution_ids = {r["measurement_id"] for r in execution}
    for row in ngram:
        if row["ngram_mapping_type"] != "TECHNICALLY_UNREPRESENTABLE":
            measurement_form = row["ngram_measurement_form"]
            require(measurement_form != "", f"Mapped Ngram form missing: {row['candidate_id']}")
            # Query mappings resolve through the candidate model and deduplicated execution table.
            model = next(r for r in rows(P180 / "priority180_candidate_model.csv") if r["candidate_id"] == row["candidate_id"])
            require(model["ngram_measurement_id"] in execution_ids, f"Unresolved measurement: {row['candidate_id']}")

    model = rows(P180 / "priority180_candidate_model.csv")
    mapped = [r for r in model if r["ngram_measurement_id"]]
    require(any(count > 1 for count in Counter(r["ngram_measurement_id"] for r in mapped).values()), "No demonstrated shared Ngram series mapping")
    require(len(annual) == len(execution) * 181, "Annual grid must cover 1842–2022 for every represented measurement")
    require(len({(r["measurement_id"], r["year"]) for r in annual}) == len(annual), "Duplicate measurement/year annual rows")
    require(all((r["normalized_frequency"] != "" and r["observation_status"] == "OBSERVED_NUMERIC") or (r["normalized_frequency"] == "" and r["observation_status"] == "NO_SERIES_RETURNED") for r in annual), "Raw numeric and no-series states are conflated")
    require(any(r["observation_status"] == "NO_SERIES_RETURNED" for r in annual), "Zero/empty responses were not retained")

    require(len(dictionary_unique) == 171, "Expected 171 deduplicated Priority lexical forms")
    require(len({r["dictionary_form_id"] for r in dictionary_unique}) == len(dictionary_unique), "Duplicate dictionary form IDs")
    require(all(r["dictionary_primary_source"] and r["dictionary_source_url_or_id"] and r["dictionary_access_date"] for r in dictionary), "Dictionary source attribution is incomplete")
    require(all(r["dictionary_anchor_sense_match"] in {"STRONG", "PARTIAL", "DIFFERENT", "UNRESOLVED"} for r in dictionary), "Invalid anchor sense match")

    require(len(search_long) == 1260, "Expected 180 candidates x (6 bounded source/window rows + 1 Google Books provider row)")
    ia_all = [r for r in search_long if r["search_source"] == "INTERNET_ARCHIVE" and r["query_window"] == "ALL_AVAILABLE"]
    require(len(ia_all) == 180 and all(r["search_status"] in {"COMPLETED_ZERO", "COMPLETED_NONZERO"} for r in ia_all), "Primary Internet Archive search is incomplete")
    require(all(r["retrieved_at"] and r["raw_response_path"] and r["raw_response_sha256"] for r in ia_all), "Primary search provenance is incomplete")
    require(all(r["metric_semantics"] == "INTERNET_ARCHIVE_METADATA_TEXT_ITEM_COUNT" for r in ia_all), "Search count semantics are unidentified")
    require(any(r["search_status"] == "COMPLETED_ZERO" for r in ia_all), "Search zero results were not retained")

    require(all("RECONSTRUCTED_FROM_REPORT" in r["candidate_provenance"] for r in master), "Reconstructed provenance label is missing")
    require(reconciliation["query_rule_count"] == 143, "Baseline query-rule count changed")
    require(reconciliation["ngram_executable_count"] == 138, "Baseline executable count changed")
    require(reconciliation["ngram_success_count"] == 132, "Baseline success count changed")
    require(reconciliation["ngram_zero_result_count"] == 6, "Six executable zero-result rules are not reconciled")
    require(reconciliation["unexplained_rules"] == 0, "Baseline Ngram rules remain unexplained")

    counts = json.loads((P180 / "coverage_counts.json").read_text(encoding="utf-8"))
    require(counts["accounted"] == 180, "Priority accounted count is not 180")
    require(counts["ngram_unexplained"] == counts["dictionary_unexplained"] == counts["search_unexplained"] == 0, "Coverage gate has unexplained rows")
    print("PRIORITY180_VALIDATION=PASS")
    print("PRIORITY_CANDIDATES=180")
    print("PRIORITY_ACCOUNTED=180")
    print("NGRAM_UNEXPLAINED=0")
    print("DICTIONARY_UNEXPLAINED=0")
    print("SEARCH_UNEXPLAINED=0")


if __name__ == "__main__":
    main()
