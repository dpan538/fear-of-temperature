#!/usr/bin/env python3
"""Automated validation gates for exploratory-analysis-v0.2."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "data" / "fear-temperature" / "analysis"
REPORT = ROOT / "docs" / "research" / "fear-temperature" / "EDA_VALIDATION_REPORT.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(ANALYSIS / name, keep_default_na=False)


def main() -> None:
    candidate = load("candidate_analysis_180.csv")
    relationships = load("candidate_relationship.csv")
    comparison = load("candidate_comparability.csv")
    measurement = load("candidate_measurement_map.csv")
    layer = load("anchor_layer_counts.csv")
    voice = load("anchor_voice_counts.csv")
    family = load("anchor_family_counts.csv")
    bias = load("coverage_bias_matrix.csv")

    require(len(candidate) == 180, "candidate_analysis_180 must contain exactly 180 rows")
    require(candidate.candidate_id.nunique() == 180, "candidate IDs must be unique")
    require(candidate.anchor_id.str.len().gt(0).all(), "every candidate must map to one anchor")
    require(candidate.anchor_label.nunique() == 6, "exactly six anchors required")
    require(set(candidate.layer_code) <= {"A", "B", "C", "D"}, "invalid layer code")
    require(candidate.layer_code.str.len().gt(0).all(), "every candidate must have a layer")
    require(candidate.voice_code.str.len().gt(0).all(), "voice or explicit missingness required")
    require(candidate.expression_mode.str.len().gt(0).all(), "expression mode or explicit missingness required")
    require(candidate.annotation_missingness.str.len().gt(0).all(), "annotation missingness must be explicit")
    require(candidate.interpretation_warning.str.contains("STRING_FREQUENCY_IS_NOT_SEMANTIC_EVIDENCE").all(), "interpretation warning missing")

    ids = set(candidate.candidate_id)
    require(set(relationships.source_candidate_id) <= ids, "unresolved source relationship endpoint")
    require(set(relationships.target_candidate_id) <= ids, "unresolved target relationship endpoint")
    require((relationships.source_candidate_id != relationships.target_candidate_id).all(), "self relationship found")
    require(set(relationships.relation_class) <= {"COMPUTATIONAL_STRUCTURAL", "RESEARCH_SEMANTIC_CANDIDATE"}, "invalid relation class")
    semantic = relationships[relationships.relation_class == "RESEARCH_SEMANTIC_CANDIDATE"]
    require(len(semantic) > 0, "evidence-supported semantic candidate relations missing")
    require(semantic.evidence_basis.str.len().gt(0).all(), "semantic relation lacks evidence basis")

    require(len(measurement) == 180 and measurement.candidate_id.nunique() == 180, "measurement map must resolve 180 candidates")
    require((measurement.traceability_status == "TRACEABLE").all(), "candidate measurement traceability failure")
    require(measurement.dictionary_status.str.len().gt(0).all(), "dictionary mapping incomplete")
    require(measurement.search_status.str.len().gt(0).all(), "search mapping incomplete")
    require(len(layer) == 6 and (layer.total == 30).all(), "anchor-layer totals must be 30 per anchor")
    require(len(voice) == 6 and (voice.total == 30).all(), "anchor-voice totals must be 30 per anchor")
    require(len(family) == 84, "anchor-family grid must include 6 x 14 cells")
    require(set(comparison.comparison_status) <= {"STRONGLY_COMPARABLE", "PARTIALLY_COMPARABLE", "NOT_COMPARABLE", "UNRESOLVED"}, "invalid comparability state")
    require({"NOT_APPLICABLE", "ZERO_RESULT"}.intersection(set(bias.status)), "bias matrix must retain zero/not-applicable states")

    raw_columns = ["ngram_peak_frequency_raw", "ngram_anchor_frequency_raw", "ngram_2022_frequency_raw"]
    ppm_columns = ["ngram_peak_per_million", "ngram_anchor_per_million", "ngram_2022_per_million"]
    for raw, ppm in zip(raw_columns, ppm_columns):
        pairs = candidate[(candidate[raw] != "") & (candidate[ppm] != "")]
        if not pairs.empty:
            raw_values = pd.to_numeric(pairs[raw])
            ppm_values = pd.to_numeric(pairs[ppm])
            require(((raw_values * 1_000_000 - ppm_values).abs() < 1e-9).all(), f"per-million conversion failure: {raw}")

    migration = (ROOT / "db" / "migrations" / "003_eda_relationship_views.sql").read_text(encoding="utf-8")
    for object_name in [
        "candidate_relationship", "vw_candidate_analysis_180", "vw_anchor_layer_counts",
        "vw_anchor_voice_counts", "vw_anchor_family_counts", "vw_voice_family_counts",
        "vw_anchor_voice_family_counts", "vw_term_anchor_presence",
        "vw_family_anchor_presence", "vw_candidate_measurement_map",
    ]:
        require(object_name in migration, f"missing PostgreSQL object: {object_name}")

    runtime_path = ANALYSIS / "postgres_eda_runtime_validation.json"
    runtime_status = "NOT_RUN"
    if runtime_path.exists():
        runtime_status = json.loads(runtime_path.read_text(encoding="utf-8")).get("status", "UNRESOLVED")
    result = {
        "status": "PASS", "priority_rows": len(candidate),
        "relationship_rows": len(relationships), "semantic_relationship_rows": len(semantic),
        "comparability_rows": len(comparison), "measurement_map_rows": len(measurement),
        "postgres_runtime": runtime_status,
    }
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
