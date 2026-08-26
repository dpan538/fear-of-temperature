#!/usr/bin/env python3
"""Generate auditable PostgreSQL seed SQL from the versioned acquisition CSVs."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "fear-temperature"
OUT = ROOT / "db" / "seeds" / "005_priority180_acquisition_evidence.sql"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def q(value: object) -> str:
    if value is None or str(value).strip() == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def n(value: object) -> str:
    text = str(value or "").strip()
    return text if text else "NULL"


def b(value: object) -> str:
    return "true" if str(value).casefold() in {"true", "1", "yes"} else "false"


def sid(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


def main() -> None:
    execution = read(DATA / "priority180" / "ngram" / "ngram_measurement_execution.csv")
    observations = read(DATA / "priority180" / "ngram" / "ngram_timeseries_priority_measurements.csv")
    model = read(DATA / "priority180" / "priority180_candidate_model.csv")
    dictionary_forms = read(DATA / "exports" / "dictionary_unique_forms.csv")
    dictionary_candidates = read(DATA / "exports" / "dictionary_coverage_180.csv")
    searches = read(DATA / "exports" / "search_statistics_long.csv")
    relationships = read(DATA / "analysis" / "candidate_relationship.csv")

    dictionary_by_candidate: dict[str, str] = {}
    for row in dictionary_forms:
        for candidate_id in row["candidate_ids"].split(";"):
            if candidate_id.strip():
                dictionary_by_candidate[candidate_id.strip()] = row["dictionary_form_id"]

    lines = [
        "BEGIN;", "", "SET search_path = fear_temperature, public;", "",
        "-- Generated from the candidate-level acquisition exports; source CSVs remain authoritative.",
    ]
    lines.append("INSERT INTO ngram_measurement (ngram_measurement_id, measurement_form, normalized_measurement_form, provider, corpus_identifier, corpus_version_label, year_start, year_end, smoothing, case_insensitive, execution_status, retrieved_at, request_url, raw_response_path, raw_payload_sha256, status_note) VALUES")
    values = []
    for row in execution:
        values.append("(" + ", ".join([
            q(row["measurement_id"]), q(row["measurement_form"]), q(row["normalized_measurement_form"]),
            q(row["provider"]), q(row["corpus_identifier"]), q(row["corpus_version"]),
            n(row["year_start"]), n(row["year_end"]), n(row["smoothing"]), b(row["case_insensitive"]),
            q(row["execution_status"]), q(row["retrieved_at"]), q(row["request_url"]),
            q(row["raw_response_path"]), q(row["raw_payload_sha256"]), q(row["status_note"]),
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (ngram_measurement_id) DO NOTHING;\n")

    lines.append("INSERT INTO priority_candidate_ngram_map (seed_candidate_id, ngram_measurement_id, mapping_type, project_query_id, mapping_reason, coverage_state) VALUES")
    values = []
    for row in model:
        coverage = "FULLY_COVERED"
        if row["ngram_mapping_type"] in {"NORMALIZED_VARIANT", "VALIDATED_ALIAS"}:
            coverage = "FULLY_ACCOUNTED_WITH_NGRAM_ALIAS"
        elif row["ngram_mapping_type"] == "TECHNICALLY_UNREPRESENTABLE":
            coverage = "FULLY_ACCOUNTED_NGRAM_TECHNICALLY_UNREPRESENTABLE"
        values.append("(" + ", ".join([
            q(row["candidate_id"]), q(row["ngram_measurement_id"]), q(row["ngram_mapping_type"]),
            q(row["ngram_query_id"]), q(row["ngram_mapping_reason"]), q(coverage),
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (seed_candidate_id) DO NOTHING;\n")

    lines.append("INSERT INTO ngram_measurement_observation (ngram_measurement_id, year, normalized_frequency, observation_status) VALUES")
    values = []
    for row in observations:
        values.append("(" + ", ".join([
            q(row["measurement_id"]), n(row["year"]), n(row["normalized_frequency"]), q(row["observation_status"]),
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (ngram_measurement_id, year) DO NOTHING;\n")

    lines.append("INSERT INTO dictionary_form_evidence (dictionary_form_id, normalized_form, representative_surface_form, dictionary_status, primary_source, secondary_source, historical_source, definition_paraphrase, historical_sense, first_attestation, source_url_or_id, accessed_on, provenance_note) VALUES")
    values = []
    for row in dictionary_forms:
        values.append("(" + ", ".join([
            q(row["dictionary_form_id"]), q(row["normalized_form"]), q(row["representative_surface_form"]),
            q(row["dictionary_status"]), q(row["dictionary_primary_source"]), q(row["dictionary_secondary_source"]),
            q(row["dictionary_historical_source"]), q(row["dictionary_definition_paraphrase"]),
            q(row["dictionary_historical_sense"]), q(row["dictionary_first_attestation_if_available"]),
            q(row["dictionary_source_url_or_id"]), q(row["dictionary_access_date"]), q(row["dictionary_provenance_note"]),
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (dictionary_form_id) DO NOTHING;\n")

    lines.append("INSERT INTO priority_candidate_dictionary_map (seed_candidate_id, dictionary_form_id, anchor_sense_match, polysemy_note) VALUES")
    values = []
    for row in dictionary_candidates:
        values.append("(" + ", ".join([
            q(row["candidate_id"]), q(dictionary_by_candidate[row["candidate_id"]]),
            q(row["dictionary_anchor_sense_match"]), q(row["dictionary_polysemy_note"]),
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (seed_candidate_id) DO NOTHING;\n")

    search_ids: list[tuple[str, str]] = []
    lines.append("INSERT INTO bounded_search_measurement (bounded_search_measurement_id, search_source, metric_semantics, search_query, query_window, window_start_year, window_end_year, exactness, search_status, reported_result_count, retrieved_at, api_or_interface, request_url, raw_response_path, raw_response_sha256, notes) VALUES")
    values = []
    for row in searches:
        measurement_id = sid("FT-SEARCH", row["candidate_id"], row["search_source"], row["query_window"], row["search_query"])
        search_ids.append((row["candidate_id"], measurement_id))
        values.append("(" + ", ".join([
            q(measurement_id), q(row["search_source"]), q(row["metric_semantics"]), q(row["search_query"]),
            q(row["query_window"]), n(row["window_start_year"]), n(row["window_end_year"]),
            q(row["search_exactness"]), q(row["search_status"]), n(row["search_total_results"]),
            q(row["retrieved_at"]), q(row["search_api_or_interface"]), q(row["request_url"]),
            q(row["raw_response_path"]), q(row["raw_response_sha256"]), q(row["search_notes"]),
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (bounded_search_measurement_id) DO NOTHING;\n")

    lines.append("INSERT INTO priority_candidate_search_map (seed_candidate_id, bounded_search_measurement_id) VALUES")
    lines.append(",\n".join(f"({q(candidate)}, {q(measurement)})" for candidate, measurement in search_ids) + "\nON CONFLICT (seed_candidate_id, bounded_search_measurement_id) DO NOTHING;\n")

    lines.append("INSERT INTO candidate_relationship (relation_id, source_candidate_id, target_candidate_id, relation_type, relation_class, anchor_relation, evidence_basis, confidence, provenance_note) VALUES")
    values = []
    for row in relationships:
        values.append("(" + ", ".join(q(row[key]) for key in [
            "relation_id", "source_candidate_id", "target_candidate_id", "relation_type",
            "relation_class", "anchor_relation", "evidence_basis", "confidence", "provenance_note",
        ]) + ")")
    lines.append(",\n".join(values) + "\nON CONFLICT (relation_id) DO NOTHING;\n")
    lines.extend(["COMMIT;", ""])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"POSTGRES_SEED={OUT.relative_to(ROOT)}")
    print(f"NGRAM_MEASUREMENTS={len(execution)}")
    print(f"NGRAM_OBSERVATIONS={len(observations)}")
    print(f"DICTIONARY_FORMS={len(dictionary_forms)}")
    print(f"SEARCH_MEASUREMENTS={len(searches)}")
    print(f"RELATIONSHIPS={len(relationships)}")


if __name__ == "__main__":
    main()
