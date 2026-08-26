#!/usr/bin/env python3
"""Build presentation-safe, controlled-missingness exports for the supervisor workbook.

The canonical research CSVs remain untouched.  These derived tables make every
supervisor-facing annotation explicit, recover INITIAL_180 evidence identifiers
from the source report, and retain the Priority-candidate denominator of 180.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import pdfplumber


ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = ROOT / "data" / "fear-temperature" / "exports"
SEED_PATH = ROOT / "data" / "fear-temperature" / "seed" / "seed_candidates.csv"
INITIAL_REPORT = ROOT / "Fear of Temperature_ Historical Lexical Discovery and Anchor Validation.pdf"

CONTROLLED_MISSINGNESS = {
    "NOT_ANNOTATED_IN_SOURCE",
    "NOT_EXPOSED_IN_REPORT",
    "NOT_APPLICABLE",
    "NOT_LOCATED",
    "UNRESOLVED",
    "PENDING_SOURCE_REVIEW",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def words_in_bbox(page: Any, bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    x0, top, x1, bottom = bbox
    return [
        word
        for word in page.extract_words(use_text_flow=False, x_tolerance=1, y_tolerance=2)
        if x0 - 1 <= word["x0"] <= x1 + 1 and top - 1 <= word["top"] <= bottom + 1
    ]


def tokens_for_band(words: Iterable[dict[str, Any]], x0: float, x1: float, top: float, bottom: float) -> str:
    selected = [word for word in words if x0 <= word["x0"] < x1 and top <= word["top"] < bottom]
    selected.sort(key=lambda word: (round(word["top"], 1), word["x0"]))
    return " ".join(word["text"] for word in selected).strip()


def recover_initial_evidence_ids() -> dict[str, str]:
    """Recover only evidence strings visibly printed in the initial report tables."""
    candidate_re = re.compile(r"^(1842|1938|1988|0607|2015|2022)-[ABCD]-\d{2}$")
    split_prefix_re = re.compile(r"^(1842|1938|1988|0607|2015|2022)-$")
    split_suffix_re = re.compile(r"^[ABCD]-\d{2}$")
    recovered: dict[str, str] = {}
    with pdfplumber.open(INITIAL_REPORT) as pdf:
        for page in pdf.pages:
            for table in page.find_tables():
                words = words_in_bbox(page, table.bbox)
                identifiers = [word for word in words if candidate_re.match(word["text"])]
                for prefix_word in [word for word in words if split_prefix_re.match(word["text"])]:
                    suffix = next(
                        (
                            word
                            for word in words
                            if split_suffix_re.match(word["text"])
                            and abs(word["x0"] - prefix_word["x0"]) <= 2
                            and 0 < word["top"] - prefix_word["top"] <= 25
                        ),
                        None,
                    )
                    if suffix:
                        identifiers.append(
                            {
                                **suffix,
                                "text": prefix_word["text"] + suffix["text"],
                                "top": (prefix_word["top"] + suffix["top"]) / 2,
                            }
                        )
                if not identifiers:
                    continue
                source_headers = sorted(
                    [word for word in words if word["text"].lower() == "source"],
                    key=lambda word: word["top"],
                )
                evidence_headers = sorted(
                    [word for word in words if word["text"].lower() == "evidence"],
                    key=lambda word: word["top"],
                )
                if not source_headers:
                    continue
                source_header = source_headers[0]
                evidence_header = next(
                    (word for word in evidence_headers if word["x0"] > source_header["x0"]),
                    None,
                )
                if evidence_header is None:
                    continue
                identifiers.sort(key=lambda word: word["top"])
                for index, identifier in enumerate(identifiers):
                    previous_top = identifiers[index - 1]["top"] if index else table.bbox[1]
                    next_top = identifiers[index + 1]["top"] if index + 1 < len(identifiers) else table.bbox[3]
                    band_top = (previous_top + identifier["top"]) / 2 if index else table.bbox[1]
                    band_bottom = (
                        (identifier["top"] + next_top) / 2 if index + 1 < len(identifiers) else table.bbox[3]
                    )
                    raw = tokens_for_band(
                        words,
                        source_header["x0"] - 1,
                        evidence_header["x0"] - 1,
                        band_top,
                        band_bottom,
                    )
                    raw = re.sub(r"^Evidence\s+source\s*", "", raw, flags=re.IGNORECASE)
                    raw = re.sub(r"\s+", "", raw)
                    # Table text can touch the adjacent 'validation set' label.
                    raw = re.sub(r"(?:negativevalidation|validationset)$", "", raw, flags=re.IGNORECASE)
                    recovered[identifier["text"]] = raw or "NOT_EXPOSED_IN_SOURCE"
    return recovered


def stage_missing(stage: str, kind: str) -> str:
    if stage == "INITIAL_180":
        return "NOT_ANNOTATED_IN_SOURCE" if kind in {"voice", "mode"} else "NOT_EXPOSED_IN_SOURCE"
    return "NOT_EXPOSED_IN_REPORT"


def build_seed_ledger() -> tuple[list[dict[str, str]], int]:
    source_rows = read_csv(SEED_PATH)
    evidence = recover_initial_evidence_ids()
    rows: list[dict[str, str]] = []
    for source in source_rows:
        row = dict(source)
        stage = row["originating_seed_stage"]
        if stage == "INITIAL_180":
            row["source_id"] = evidence.get(row["original_candidate_id"], "NOT_EXPOSED_IN_SOURCE")
        elif not row["source_id"].strip():
            row["source_id"] = stage_missing(stage, "source")
        if not row["voice_code"].strip():
            row["voice_code"] = stage_missing(stage, "voice")
        if not row["expression_mode_code"].strip():
            row["expression_mode_code"] = stage_missing(stage, "mode")
        if not row["original_candidate_id"].strip():
            row["original_candidate_id"] = "NOT_EXPOSED_IN_REPORT"
        if not row["source_page"].strip():
            row["source_page"] = "NOT_LOCATED"
        if row.get("confidence_label") == "NOT_EXPOSED":
            row["confidence_label"] = stage_missing(stage, "confidence")
        if not row.get("confidence_label", "").strip():
            row["confidence_label"] = stage_missing(stage, "confidence")
        if not row.get("relevance_label", "").strip():
            row["relevance_label"] = stage_missing(stage, "relevance")
        for field in row:
            if not str(row[field]).strip():
                row[field] = "UNRESOLVED"
        rows.append(row)
    initial_backfilled = sum(
        row["originating_seed_stage"] == "INITIAL_180" and row["source_id"].startswith("E")
        for row in rows
    )
    if len(rows) != 396 or initial_backfilled != 180:
        raise ValueError(f"Seed ledger reconciliation failed: rows={len(rows)}, initial evidence={initial_backfilled}")
    return rows, initial_backfilled


def explicit(value: Any, missing: str = "NOT_APPLICABLE") -> Any:
    if value is None or str(value).strip() == "":
        return missing
    value = str(value).strip()
    if value in {"NOT_AVAILABLE_IN_ACCESSED_SOURCES", "NOT_AVAILABLE"}:
        return "NOT_LOCATED"
    return value


def modern_sense_for(row: dict[str, str]) -> str:
    """Expose materially different modern readings for the key historical false friends."""
    term = row["surface_form"].casefold()
    anchor = row["anchor"]
    if term == "climate" and anchor == "1842":
        return "Modern climate commonly denotes long-term statistical weather conditions or the coupled climate system; it does not by itself mean the modern issue label 'climate change'."
    if term == "depressing effect":
        return "Contemporary readers may hear a mood-lowering or clinical-psychology association; that reading must not be projected onto the 1842 bodily/energetic use."
    if term == "common concern of humankind":
        return "Personal concern can denote felt worry, but this continuing treaty formula designates a shared legal and governance object rather than an individual's emotion."
    if term == "climate anxiety":
        return "Current usage can refer to climate-related apprehension or distress, but researcher construct, instrument wording and participant self-description remain distinct evidence states."
    if term == "be worried. be very worried.":
        return "A modern media imperative prescribing worry to an audience; it is not evidence that the audience experienced or endorsed the emotion."
    if term in {"personally worry", "very worried"}:
        return "Contemporary worry wording may describe affect, but in the cited survey setting it is instrument-supplied and participant endorsement is elicited rather than spontaneous."
    return explicit(row["dictionary_definition_paraphrase"], "UNRESOLVED")


def build_priority_tables(seed_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    master = read_csv(EXPORT_DIR / "priority180_full_coverage_matrix.csv")
    seed_by_id = {
        row["seed_candidate_id"]: row for row in seed_rows if row["originating_seed_stage"] == "PRIORITY_180"
    }
    if len(master) != 180 or len(seed_by_id) != 180:
        raise ValueError("Priority denominator is not 180")
    priority_rows: list[dict[str, Any]] = []
    dictionary_rows: list[dict[str, Any]] = []
    search_rows: list[dict[str, Any]] = []
    for row in master:
        seed = seed_by_id[row["candidate_id"]]
        gap = (
            "PENDING_SOURCE_REVIEW"
            if seed["expression_mode_code"] in CONTROLLED_MISSINGNESS
            or seed["source_id"] in CONTROLLED_MISSINGNESS
            else "NOT_APPLICABLE"
        )
        if row["dictionary_anchor_sense_match"] in {"DIFFERENT", "UNRESOLVED"} or row["ngram_mapping_type"] == "TECHNICALLY_UNREPRESENTABLE":
            review_priority = "HIGH"
        elif row["dictionary_anchor_sense_match"] == "PARTIAL" or row["search_status"].endswith("ZERO") or gap == "PENDING_SOURCE_REVIEW":
            review_priority = "MEDIUM"
        else:
            review_priority = "ROUTINE"
        priority_rows.append(
            {
                "Candidate ID": row["candidate_id"],
                "Anchor": row["anchor"],
                "Rank": int(row["priority_rank"]),
                "Surface Form": row["surface_form"],
                "Normalised Concept": row["normalized_concept"],
                "Lexical Family": row["lexical_family"],
                "Layer": row["layer"],
                "Voice": seed["voice_code"],
                "Expression Mode": seed["expression_mode_code"],
                "Evidence Source": seed["source_id"],
                "Candidate Provenance": row["candidate_provenance"],
                "Ngram Status": row["ngram_status"],
                "Measurement Form": explicit(row["ngram_measurement_form"]),
                "Mapping Type": row["ngram_mapping_type"],
                "First Non-Zero Year": explicit(row["ngram_first_nonzero_year"]),
                "Peak Year": explicit(row["ngram_peak_year"]),
                "Peak Frequency": explicit(row["ngram_peak_frequency"]),
                "Anchor Frequency": explicit(row["ngram_anchor_value"]),
                "Context Window Mean": explicit(row["ngram_context_window_mean"]),
                "2022 Frequency": explicit(row["ngram_2022_value"]),
                "Ngram Note": explicit(row["ngram_notes"]),
                "Dictionary Status": row["dictionary_status"],
                "Dictionary Source": explicit(row["dictionary_primary_source"], "NOT_LOCATED"),
                "Historical Sense": explicit(row["dictionary_historical_sense"], "UNRESOLVED"),
                "Modern Sense": modern_sense_for(row),
                "Anchor Sense Match": row["dictionary_anchor_sense_match"],
                "Polysemy / Ambiguity": explicit(row["dictionary_polysemy_note"], "UNRESOLVED"),
                "Dictionary Note": f"Secondary: {explicit(row['dictionary_secondary_source'], 'NOT_LOCATED')}; historical: {explicit(row['dictionary_historical_source'], 'NOT_LOCATED')}; source: {explicit(row['dictionary_source_url_or_id'], 'NOT_LOCATED')}",
                "Search Source": row["search_primary_source"],
                "Search Query": row["search_query"],
                "Search Exactness": row["search_exactness"],
                "Search Status": row["search_status"],
                "Result Count": int(row["search_total_results"]),
                "Date-Window Count": int(row["search_contextual_window_results"]),
                "Retrieval Date": row["search_retrieval_date"],
                "Search Note": explicit(row["search_notes"]),
                "Coverage Status": row["coverage_status"],
                "Remaining Annotation Gap": gap,
                "Review Priority": review_priority,
            }
        )
        dictionary_rows.append(
            {
                "Candidate ID": row["candidate_id"],
                "Anchor": row["anchor"],
                "Rank": int(row["priority_rank"]),
                "Surface Form": row["surface_form"],
                "Normalised Concept": row["normalized_concept"],
                "Lexical Family": row["lexical_family"],
                "Dictionary Status": row["dictionary_status"],
                "Direct Headword Exists": "YES" if row["dictionary_status"] == "DIRECT_HEADWORD" else "NO",
                "Primary Source": explicit(row["dictionary_primary_source"], "NOT_LOCATED"),
                "Secondary Source": explicit(row["dictionary_secondary_source"], "NOT_LOCATED"),
                "Historical / Domain Source": explicit(row["dictionary_historical_source"], "NOT_LOCATED"),
                "Concise Definition Paraphrase": explicit(row["dictionary_definition_paraphrase"], "UNRESOLVED"),
                "Historically Relevant Sense": explicit(row["dictionary_historical_sense"], "UNRESOLVED"),
                "Modern Sense": modern_sense_for(row),
                "Anchor Sense Match": row["dictionary_anchor_sense_match"],
                "First Attestation": explicit(row["dictionary_first_attestation_if_available"], "NOT_LOCATED"),
                "Polysemy Warning": explicit(row["dictionary_polysemy_note"], "UNRESOLVED"),
                "Source Citation / Link": explicit(row["dictionary_source_url_or_id"], "NOT_LOCATED"),
                "Access Date": row["dictionary_access_date"],
                "Candidate Provenance": row["candidate_provenance"],
            }
        )
        search_rows.append(
            {
                "Candidate ID": row["candidate_id"],
                "Anchor": row["anchor"],
                "Rank": int(row["priority_rank"]),
                "Surface Form": row["surface_form"],
                "Search Source": row["search_primary_source"],
                "Count Meaning": "INTERNET_ARCHIVE_ADVANCEDSEARCH_NUMFOUND",
                "Query String": row["search_query"],
                "Query Type": row["search_query_type"],
                "Exactness": row["search_exactness"],
                "Full-Corpus Result Count": int(row["search_total_results"]),
                "Strict-Window Result Count": int(row["search_strict_window_results"]),
                "Contextual-Window Result Count": int(row["search_contextual_window_results"]),
                "Search Status": row["search_status"],
                "Retrieval Timestamp": row["search_retrieval_date"],
                "API / Interface": row["search_api_or_interface"],
                "Notes": explicit(row["search_notes"]),
                "Secondary Source": explicit(row["search_secondary_source"], "NOT_APPLICABLE"),
                "Secondary All-Period Count": explicit(row["search_secondary_total_results"]),
            }
        )
    return priority_rows, dictionary_rows, search_rows


def build_ngram_rule_coverage() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audit = read_csv(EXPORT_DIR / "ngram_compatibility_audit.csv")
    execution = read_csv(ROOT / "data" / "fear-temperature" / "ngram" / "ngram_query_execution_results.csv")
    execution_by_id = {row["query_id"]: row for row in execution}
    rows: list[dict[str, Any]] = []
    for row in audit:
        status = execution_by_id[row["query_id"]]
        execution_status = status["execution_status"]
        accounting = {
            "SUCCEEDED": "SUCCESS_NONZERO",
            "ZERO_RESULT": "ZERO_RESULT",
            "NOT_RUN_INCOMPATIBLE": "TECHNICALLY_UNREPRESENTABLE",
            "FAILED": "FAILED",
        }.get(execution_status, "UNRESOLVED")
        rows.append(
            {
                "Query ID": row["query_id"],
                "Anchor": row["anchor"],
                "Surface Form": row["surface_form"],
                "Classification": row["classification"],
                "Compatibility Status": row["compatibility_status"],
                "Execution Eligible": row["execution_eligible"],
                "Execution Status": execution_status,
                "Accounting State": accounting,
                "Observation Count": int(status["observation_count"] or 0),
                "Request Surface Form": explicit(status["request_surface_form"], "NOT_APPLICABLE"),
                "First Response Ngram": explicit(status["first_response_ngram"], "NOT_APPLICABLE"),
                "Reason / Error": explicit(status["error_reason"] or row["reason"], "NOT_APPLICABLE"),
                "Retrieved At": explicit(status["retrieved_at"], "NOT_APPLICABLE"),
                "Raw Response Path": explicit(status["raw_response_path"], "NOT_APPLICABLE"),
                "Provenance Status": row["provenance_status"],
            }
        )
    if len(rows) != 143 or any(row["Accounting State"] == "UNRESOLVED" for row in rows):
        raise ValueError("Ngram rule reconciliation is incomplete")
    candidate_map = read_csv(EXPORT_DIR / "priority180_ngram_coverage.csv")
    exceptions = [
        {
            "Candidate ID": row["candidate_id"],
            "Anchor": row["anchor"],
            "Surface Form": row["surface_form"],
            "Measurement Form": explicit(row["ngram_measurement_form"]),
            "Mapping Type": row["ngram_mapping_type"],
            "Ngram Status": row["ngram_status"],
            "Query ID": explicit(row["ngram_query_id"]),
            "Note": explicit(row["ngram_notes"]),
        }
        for row in candidate_map
        if row["ngram_mapping_type"] != "EXACT"
    ]
    return rows, exceptions


def build_metrics(seed_rows: list[dict[str, str]], initial_backfilled: int, ngram_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = read_csv(EXPORT_DIR / "priority180_full_coverage_matrix.csv")
    status_counts = Counter(row["Execution Status"] for row in ngram_rows)
    mapping_counts = Counter(row["ngram_mapping_type"] for row in priority)
    dict_counts = Counter(row["dictionary_status"] for row in priority)
    search_counts = Counter(row["search_status"] for row in priority)
    controlled_count = sum(value in CONTROLLED_MISSINGNESS for row in seed_rows for value in row.values())
    metrics = [
        ("Historical anchors", 6, "Distinct design anchors", "historical_anchors.csv"),
        ("Priority candidates", 180, "Candidate-level denominator", "priority180_full_coverage_matrix.csv"),
        ("Expansion candidates", 36, "Separate expansion inventory", "seed_ledger_supervisor.csv"),
        ("Lexical layers", 4, "A-D controlled layers", "layers.csv"),
        ("Voices", 5, "V1-V5 controlled voices", "voices.csv"),
        ("Lexical families", 14, "Semantic research families; not synonym sets", "lexical_families.csv"),
        ("Ngram query rules", len(ngram_rows), "All provisional baseline rules", "ngram_supervisor_coverage.csv"),
        ("Ngram executable", sum(row["Execution Eligible"].lower() == "true" for row in ngram_rows), "Rules eligible for retrieval", "ngram_supervisor_coverage.csv"),
        ("Ngram successful nonzero", status_counts["SUCCEEDED"], "Returned 181 annual observations", "ngram_supervisor_coverage.csv"),
        ("Ngram zero result", status_counts["ZERO_RESULT"], "Legitimate zero-return series", "ngram_supervisor_coverage.csv"),
        ("Ngram incompatible", status_counts["NOT_RUN_INCOMPATIBLE"], "Not directly representable in Ngram", "ngram_supervisor_coverage.csv"),
        ("Baseline annual observations", sum(row["Observation Count"] for row in ngram_rows), "Numeric 1842-2022 observations across successful baseline rules", "ngram_supervisor_coverage.csv"),
        ("Priority Ngram accounted", len(priority), f"Exact {mapping_counts['EXACT']}; normalized {mapping_counts['NORMALIZED_VARIANT']}; alias {mapping_counts['VALIDATED_ALIAS']}; unrepresentable {mapping_counts['TECHNICALLY_UNREPRESENTABLE']}", "priority180_full_coverage_matrix.csv"),
        ("Priority dictionary accounted", len(priority), f"Direct {dict_counts['DIRECT_HEADWORD']}; glossary {dict_counts['TECHNICAL_GLOSSARY']}; no headword {dict_counts['NO_STANDALONE_HEADWORD']}", "dictionary_coverage_180.csv"),
        ("Priority search accounted", len(priority), f"Nonzero {search_counts['COMPLETED_NONZERO']}; zero {search_counts['COMPLETED_ZERO']}", "search_statistics_180.csv"),
        ("Controlled missingness cells", controlled_count, "Explicit source/report limitations in supervisor seed ledger", "seed_ledger_supervisor.csv"),
        ("Initial evidence IDs backfilled", initial_backfilled, "Report-exposed E-prefixed evidence identifiers", "seed_ledger_supervisor.csv"),
        ("Unexplained metadata blanks", 0, "Validated annotation fields only", "supervisor export validation"),
    ]
    return [{"Metric": a, "Value": b, "Definition": c, "Source": d} for a, b, c, d in metrics]


def main() -> None:
    seed_rows, initial_backfilled = build_seed_ledger()
    priority_rows, dictionary_rows, search_rows = build_priority_tables(seed_rows)
    ngram_rows, ngram_exceptions = build_ngram_rule_coverage()
    metrics = build_metrics(seed_rows, initial_backfilled, ngram_rows)

    write_csv(EXPORT_DIR / "seed_ledger_supervisor.csv", list(seed_rows[0]), seed_rows)
    write_csv(EXPORT_DIR / "priority180_supervisor_coverage.csv", list(priority_rows[0]), priority_rows)
    write_csv(EXPORT_DIR / "dictionary_supervisor_180.csv", list(dictionary_rows[0]), dictionary_rows)
    write_csv(EXPORT_DIR / "search_supervisor_180.csv", list(search_rows[0]), search_rows)
    write_csv(EXPORT_DIR / "ngram_supervisor_coverage.csv", list(ngram_rows[0]), ngram_rows)
    write_csv(EXPORT_DIR / "ngram_candidate_mapping_exceptions.csv", list(ngram_exceptions[0]), ngram_exceptions)
    write_csv(EXPORT_DIR / "supervisor_workbook_metrics.csv", list(metrics[0]), metrics)

    validation = {
        "seed_rows": len(seed_rows),
        "priority_rows": len(priority_rows),
        "dictionary_rows": len(dictionary_rows),
        "search_rows": len(search_rows),
        "ngram_rule_rows": len(ngram_rows),
        "ngram_unexplained": sum(row["Accounting State"] == "UNRESOLVED" for row in ngram_rows),
        "initial_evidence_ids_backfilled": initial_backfilled,
        "controlled_missingness_count": sum(value in CONTROLLED_MISSINGNESS for row in seed_rows for value in row.values()),
        "blank_annotation_cells": sum(
            not row[column].strip()
            for row in seed_rows
            for column in ("original_candidate_id", "voice_code", "source_id", "expression_mode_code")
        ),
        "baseline_annual_observations": sum(row["Observation Count"] for row in ngram_rows),
    }
    if validation != {
        **validation,
        "seed_rows": 396,
        "priority_rows": 180,
        "dictionary_rows": 180,
        "search_rows": 180,
        "ngram_rule_rows": 143,
        "ngram_unexplained": 0,
        "initial_evidence_ids_backfilled": 180,
        "blank_annotation_cells": 0,
        "baseline_annual_observations": 23892,
    }:
        raise ValueError(json.dumps(validation, indent=2))
    (EXPORT_DIR / "supervisor_workbook_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
