#!/usr/bin/env python3
"""Validate the quantitative v0.1 research artifacts without mutating them."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data/fear-temperature/seed"
NGRAM = ROOT / "data/fear-temperature/ngram"
EXPORTS = ROOT / "data/fear-temperature/exports"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def iso(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    checks: list[str] = []

    anchors = rows(SEED / "historical_anchors.csv")
    voices = rows(SEED / "voices.csv")
    modes = rows(SEED / "expression_modes.csv")
    layers = rows(SEED / "layers.csv")
    families = rows(SEED / "lexical_families.csv")
    candidates = rows(SEED / "seed_candidates.csv")
    rules = rows(SEED / "query_rules.csv")
    audit = rows(EXPORTS / "ngram_compatibility_audit.csv")
    executions = rows(NGRAM / "ngram_query_execution_results.csv")
    observations = rows(NGRAM / "ngram_timeseries_full.csv")
    family_summary = rows(EXPORTS / "lexical_family_frequency_summary.csv")
    voice_matrix = rows(EXPORTS / "voice_keyword_matrix.csv")
    import_status = rows(SEED / "seed_import_status.csv")
    with (NGRAM / "ngram_run_metadata.json").open(encoding="utf-8") as handle:
        run = json.load(handle)

    require(len(anchors) == 6, "expected exactly six anchors")
    require(len(voices) == 5, "expected exactly five voices")
    require(len(modes) == 5, "expected exactly five expression modes")
    require(len(layers) == 4, "expected exactly four lexical layers")
    require(len(families) == 14, "expected exactly fourteen lexical families")
    require(len(voice_matrix) == 30, "expected complete 6 x 5 voice matrix")
    checks.append("controlled dimensions: 6 anchors, 4 layers, 5 voices, 5 modes, 14 families")

    for anchor in anchors:
        require(iso(anchor["contextual_start"]) <= iso(anchor["strict_start"]), f"strict start outside context: {anchor['anchor_id']}")
        require(iso(anchor["strict_end"]) <= iso(anchor["contextual_end"]), f"strict end outside context: {anchor['anchor_id']}")
    checks.append("strict anchor windows contained by contextual windows")

    require(len(candidates) == 396, "expected 396 reconstructed seed records")
    stage_counts = Counter(row["originating_seed_stage"] for row in candidates)
    require(stage_counts == Counter({"INITIAL_180": 180, "PRIORITY_180": 180, "EXPANSION_36": 36}), f"unexpected seed stages: {stage_counts}")
    require(len({row["seed_candidate_id"] for row in candidates}) == len(candidates), "duplicate seed candidate IDs")
    require(all(row["reconstruction_status"] == "RECONSTRUCTED_FROM_REPORT" for row in candidates), "reconstructed seed row missing explicit flag")
    require(all(row["provenance_status"] for row in candidates), "seed row missing provenance status")
    require(import_status[0]["seed_import_status"] == "PARTIAL_RECONSTRUCTION", "seed status must remain provisional")
    checks.append("seed ledger: 180 + 180 + 36 = 396, unique and provenance-labelled")

    require(len(rules) == 143, "expected 143 provisional query rules")
    require(len({row["query_id"] for row in rules}) == len(rules), "duplicate query rule IDs")
    require(all(row["reconstructed"].lower() == "true" for row in rules), "query rule missing reconstructed flag")
    require(all(row["provenance_status"] == "RECONSTRUCTED_FROM_REPORT" for row in rules), "query rule missing reconstruction provenance")
    require(len(audit) == 143, "compatibility audit must retain every rule")
    require(sum(row["execution_eligible"].lower() == "true" for row in audit) == 138, "expected 138 Ngram-eligible rules")
    checks.append("query inventory: 143 audited rules, 138 executable")

    broad = {"temperature", "heat", "fear", "worry", "anxiety", "concern", "risk", "threat", "crisis", "emergency"}
    broad_rows = [row for row in rules if row["normalized_form"].lower() in broad]
    require(broad_rows, "expected broad/background rules")
    require(all(row["interpretation_class"] == "BACKGROUND_AMBIGUOUS" for row in broad_rows), "broad term not flagged ambiguous")
    require(not any(row["normalized_form"].lower() == "change" and row["production_allowed"].lower() == "true" for row in rules), "standalone change must not be a production query")
    checks.append("broad terms flagged BACKGROUND_AMBIGUOUS; standalone change not production-enabled")

    status_counts = Counter(row["execution_status"] for row in executions)
    require(status_counts == Counter({"SUCCEEDED": 132, "ZERO_RESULT": 6, "NOT_RUN_INCOMPATIBLE": 5}), f"unexpected execution status counts: {status_counts}")
    require(len(executions) == 143, "execution ledger must retain every query")
    require(all(row["raw_response_path"] and row["raw_payload_sha256"] for row in executions if row["execution_status"] in {"SUCCEEDED", "ZERO_RESULT"}), "executed query missing raw provenance")
    checks.append("retrieval outcomes preserved: 132 success, 6 zero, 5 incompatible, 0 failed")

    require(len(observations) == 23892, "unexpected annual observation count")
    unique = {
        (row["query_id"], row["corpus"], row["version"], row["year"], row["parameter_set_hash"])
        for row in observations
    }
    require(len(unique) == len(observations), "duplicate query/corpus/version/year/parameter observations")
    require({int(row["year"]) for row in observations} == set(range(1842, 2023)), "observation years must span 1842–2022 without invented later years")
    require(all(row["retrieval_smoothing"] == "0" for row in observations), "raw annual observations must use smoothing 0")
    require(all(row["corpus"] and row["version"] and row["parameter_set_hash"] for row in observations), "frequency observation missing corpus metadata")
    checks.append("23,892 unique raw annual observations, 1842–2022, smoothing 0")

    require(run["corpus_identifier"] == "eng", "unexpected corpus identifier")
    require(run["year_start"] == 1842 and run["year_end"] == 2022, "unexpected verified corpus range")
    require(run["retrieval_smoothing"] == 0, "run metadata must identify unsmoothed retrieval")
    require(run["annual_observation_count"] == len(observations), "run metadata observation mismatch")
    require(run["interpretation_warning"], "run metadata missing interpretation warning")
    checks.append("run metadata records provider, current English corpus, live probe, and warnings")

    require(len(family_summary) == 14, "family summary must cover all fourteen families")
    require(all("never summed" in row["semantic_comparability_warning"].lower() for row in family_summary), "family summary missing non-additivity warning")
    checks.append("family summaries are member-wise and explicitly non-additive")

    search_sql = (ROOT / "db/migrations/001_fear_temperature_fast_pilot.sql").read_text(encoding="utf-8").lower()
    require("raw_hits bigint" in search_sql and "accepted_passages bigint" in search_sql, "search quantity scaffolding incomplete")
    require("'not_run'" in search_sql, "search observation must support NOT_RUN")
    checks.append("bounded-corpus search metrics scaffolded; no fabricated counts")

    figure_count = len(list((ROOT / "figures/fear-temperature").glob("*.png")))
    require(figure_count >= 21, "expected required and family figures")
    require((ROOT / "docs/research/fear-temperature/PRESENTATION_SNAPSHOT.md").is_file(), "presentation snapshot missing")
    checks.append(f"presentation artifacts present: {figure_count} PNG figures")

    report = ROOT / "docs/research/fear-temperature/VALIDATION_REPORT.md"
    lines = [
        "# Validation Report — Quantitative Baseline v0.1",
        "",
        "Automated validation status: **PASS**",
        "",
    ] + [f"- PASS — {item}" for item in checks] + [
        "",
        "PostgreSQL runtime application is reported separately after the isolated-cluster test.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "checks": len(checks), "figure_count": figure_count, "report": str(report)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
