#!/usr/bin/env python3
"""Build passage-linkage outputs without substituting candidate counts for passages.

The current repository has a complete passage schema but no populated passage,
occurrence, annotation, review, or linkage rows.  This builder therefore emits
complete analytical grids with explicit unsupported rates and empty, import-ready
passage registries.  Later passage exports can replace the empty registries without
changing the metric contract.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "fear-temperature" / "analysis" / "relational-v01"

ANCHORS = ["1842", "1938", "1988", "2006–2007", "2015", "2022"]
VOICES = ["V1", "V2", "V3", "V4", "V5"]
OBJECT_FAMILIES = ["temperature", "heat", "climate", "warming", "carbon/greenhouse"]
SOURCE_GENRES = ["SCIENTIFIC", "INSTITUTIONAL", "MEDIA", "SURVEY", "DIRECT_PUBLIC", "CIVIC"]
AFFECT_MODES = [
    "AFFECT_MODE_DIRECT",
    "AFFECT_MODE_PRESCRIBED",
    "AFFECT_MODE_ELICITED",
    "AFFECT_MODE_RESEARCHER_LABELLED",
]
LOW_N_THRESHOLD = 5
UNSUPPORTED = "UNSUPPORTED_NO_VALIDATED_AB_PASSAGES"
RATE_STATUS = "UNSUPPORTED_DENOMINATOR_ZERO"
DENOMINATOR_NOTE = (
    "No validated A/B object passages exist in the current source-of-truth data; "
    "0 records is a dataset state, not evidence of historical absence."
)

LEXICAL_TERMS = [
    ("climatic change", "climate_framing"),
    ("climate change", "climate_framing"),
    ("greenhouse effect", "climate_framing"),
    ("global warming", "climate_framing"),
    ("anxiety", "affect_specialisation"),
    ("climate anxiety", "affect_specialisation"),
    ("eco-anxiety", "affect_specialisation"),
    ("fear", "affect_specialisation"),
    ("afraid", "affect_specialisation"),
    ("worry", "affect_specialisation"),
    ("worried", "affect_specialisation"),
    ("crisis", "threat_specialisation"),
    ("climate crisis", "threat_specialisation"),
    ("emergency", "threat_specialisation"),
    ("climate emergency", "threat_specialisation"),
    ("threat", "threat_specialisation"),
    ("risk", "threat_specialisation"),
]
ANCHOR_START_YEAR = {
    "1842": 1842, "1938": 1938, "1988": 1988,
    "2006–2007": 2006, "2015": 2015, "2022": 2022,
}


AB_COLUMNS = [
    "passage_id", "object_annotation_id", "anchor", "voice", "source", "source_genre", "object_term",
    "object_family", "object_layer", "validation_status", "notes",
]
THREAT_REGISTRY_COLUMNS = [
    "passage_id", "object_annotation_id", "linked_annotation_id", "anchor", "voice", "linked_voice", "source", "source_genre",
    "object_term", "object_family", "object_layer", "threat_term", "threat_family",
    "relation_strength", "validation_status", "notes",
]
AFFECT_REGISTRY_COLUMNS = [
    "passage_id", "object_annotation_id", "linked_annotation_id", "anchor", "voice", "linked_voice", "source", "source_genre",
    "object_term", "object_family", "object_layer", "affect_term", "affect_family",
    "affect_mode", "relation_strength", "validation_status", "notes",
]


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def unsupported_row(linkage: str, **dimensions: str) -> dict[str, object]:
    count_name = f"{linkage}_Link_Count"
    rate_name = f"{linkage}_Link_Rate"
    return {
        **dimensions,
        "AB_Object_Passage_Count": 0,
        count_name: 0,
        rate_name: "",
        "Rate_Status": RATE_STATUS,
        "Low_N_Flag": True,
        "Data_Status": UNSUPPORTED,
        "Denominator_Note": DENOMINATOR_NOTE,
    }


def metric_fields(linkage: str, dimensions: list[str]) -> list[str]:
    return dimensions + [
        "AB_Object_Passage_Count", f"{linkage}_Link_Count", f"{linkage}_Link_Rate",
        "Rate_Status", "Low_N_Flag", "Data_Status", "Denominator_Note",
    ]


def build_metric_grids() -> None:
    for linkage in ["Threat", "Affect"]:
        lower = linkage.lower()
        write_csv(
            f"{lower}_linkage_by_anchor.csv",
            metric_fields(linkage, ["anchor"]),
            [unsupported_row(linkage, anchor=anchor) for anchor in ANCHORS],
        )
        write_csv(
            f"{lower}_linkage_by_anchor_voice.csv",
            metric_fields(linkage, ["anchor", "voice"]),
            [
                unsupported_row(linkage, anchor=anchor, voice=voice)
                for anchor in ANCHORS for voice in VOICES
            ],
        )
        write_csv(
            f"{lower}_linkage_by_anchor_object_family.csv",
            metric_fields(linkage, ["anchor", "object_family"]),
            [
                unsupported_row(linkage, anchor=anchor, object_family=family)
                for anchor in ANCHORS for family in OBJECT_FAMILIES
            ],
        )
        write_csv(
            f"{lower}_linkage_by_anchor_source_genre.csv",
            metric_fields(linkage, ["anchor", "source_genre"]),
            [
                unsupported_row(linkage, anchor=anchor, source_genre=genre)
                for anchor in ANCHORS for genre in SOURCE_GENRES
            ],
        )

    write_csv(
        "affect_linkage_by_anchor_affect_mode.csv",
        metric_fields("Affect", ["anchor", "affect_mode"]),
        [
            unsupported_row("Affect", anchor=anchor, affect_mode=mode)
            for anchor in ANCHORS for mode in AFFECT_MODES
        ],
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_voice_comparison() -> None:
    threat = {
        (row["anchor"], row["voice"]): row
        for row in read_csv(OUT / "threat_linkage_by_anchor_voice.csv")
    }
    affect = {
        (row["anchor"], row["voice"]): row
        for row in read_csv(OUT / "affect_linkage_by_anchor_voice.csv")
    }
    rows: list[dict[str, object]] = []
    for anchor in ANCHORS:
        for voice in VOICES:
            t = threat[(anchor, voice)]
            a = affect[(anchor, voice)]
            denominator = int(t["AB_Object_Passage_Count"])
            threat_rate = t["Threat_Link_Rate"]
            affect_rate = a["Affect_Link_Rate"]
            ratio: object = ""
            ratio_status = "UNSUPPORTED_MISSING_RATES"
            if threat_rate != "" and affect_rate != "":
                if float(affect_rate) > 0:
                    ratio = float(threat_rate) / float(affect_rate)
                    ratio_status = "COMPUTED"
                else:
                    ratio_status = "UNSUPPORTED_AFFECT_RATE_ZERO"
            rows.append({
                "anchor": anchor,
                "voice": voice,
                "AB_Object_Passage_Count": denominator,
                "Threat_Link_Count": int(t["Threat_Link_Count"]),
                "Threat_Link_Rate": threat_rate,
                "Affect_Link_Count": int(a["Affect_Link_Count"]),
                "Affect_Link_Rate": affect_rate,
                "Threat_to_Affect_Ratio": ratio,
                "Ratio_Status": ratio_status,
                "Low_N_Flag": denominator < LOW_N_THRESHOLD,
                "Small_Denominator_Note": (
                    f"Denominator {denominator} is below the low-N threshold ({LOW_N_THRESHOLD}); "
                    "rates and ratios are not estimable."
                ),
                "Data_Status": UNSUPPORTED,
            })
    write_csv("voice_linkage_summary.csv", list(rows[0]), rows)

    candidates = read_csv(ROOT / "data/fear-temperature/analysis/candidate_analysis_180.csv")
    grid: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in candidates:
        layer_group = "AB" if row["layer_code"] in {"A", "B"} else row["layer_code"]
        grid[(row["anchor_label"], row["voice_code"])][layer_group] += 1
    inventory_rows: list[dict[str, object]] = []
    for anchor in ANCHORS:
        for voice in VOICES:
            counts = grid[(anchor, voice)]
            inventory_rows.append({
                "anchor": anchor,
                "voice": voice,
                "AB_Object_Candidate_Count": counts["AB"],
                "C_Affect_Candidate_Count": counts["C"],
                "D_Threat_Candidate_Count": counts["D"],
                "D_minus_C_Candidate_Balance": counts["D"] - counts["C"],
                "Total_Priority_Candidates": sum(counts.values()),
                "Evidence_Class": "CONSTRUCTED_INVENTORY_PATTERN",
                "Interpretation_Warning": (
                    "Candidate composition is not passage linkage or historical prevalence."
                ),
            })
    write_csv("inventory_voice_layer_balance.csv", list(inventory_rows[0]), inventory_rows)


def candidate_matches(term: str, candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    pattern = re.compile(rf"(?<![a-z]){re.escape(term.casefold())}(?![a-z])")
    return [row for row in candidates if pattern.search(row["normalized_form"].casefold())]


def load_selected_ngram_series() -> dict[str, dict[int, float]]:
    selected = {term for term, _ in LEXICAL_TERMS}
    observations: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    path = ROOT / "data/fear-temperature/ngram/ngram_timeseries_full.csv"
    for row in read_csv(path):
        term = row["term"].casefold()
        if term in selected:
            observations[term][int(row["year"])].append(float(row["normalized_frequency"]))

    consolidated: dict[str, dict[int, float]] = {}
    for term in selected:
        if term not in observations:
            raise AssertionError(f"selected term lacks Ngram series: {term}")
        consolidated[term] = {}
        for year, values in observations[term].items():
            if max(values) - min(values) > 1e-15:
                raise AssertionError(f"duplicate Ngram mappings disagree for {term} in {year}")
            consolidated[term][year] = values[0]
    return consolidated


def first_sustained_year(series: dict[int, float], run_length: int = 3) -> int | None:
    years = sorted(series)
    if not years:
        return None
    for year in years:
        if all(series.get(candidate, 0.0) > 0 for candidate in range(year, year + run_length)):
            return year
    return None


def build_lexicalisation() -> None:
    candidates = read_csv(ROOT / "data/fear-temperature/analysis/candidate_analysis_180.csv")
    series_by_term = load_selected_ngram_series()
    comparison_rows: list[dict[str, object]] = []
    timeseries_rows: list[dict[str, object]] = []

    for term, family in LEXICAL_TERMS:
        series = series_by_term[term]
        nonzero_years = [year for year, value in series.items() if value > 0]
        first_nonzero: object = min(nonzero_years) if nonzero_years else "UNRESOLVED"
        sustained = first_sustained_year(series)
        first_sustained: object = sustained if sustained is not None else "UNRESOLVED"
        peak_year = max(series, key=lambda year: (series[year], -year))
        peak_per_million = series[peak_year] * 1_000_000

        matches = candidate_matches(term, candidates)
        anchors = sorted(
            {row["anchor_label"] for row in matches},
            key=lambda value: ANCHORS.index(value),
        )
        voices = sorted({row["voice_code"] for row in matches}, key=VOICES.index)
        attestation_year: object = (
            min(ANCHOR_START_YEAR[row["anchor_label"]] for row in matches)
            if matches else "UNRESOLVED"
        )
        target_matches = [
            row for row in matches
            if row["dictionary_anchor_sense_match"] in {"STRONG", "PARTIAL"}
        ]
        target_year: object = (
            min(ANCHOR_START_YEAR[row["anchor_label"]] for row in target_matches)
            if target_matches else "UNRESOLVED"
        )
        match_forms = sorted({row["normalized_form"] for row in matches})

        if target_matches:
            status_note = (
                f"Earliest source-backed Priority candidate is anchored at {target_year}; "
                "the target-sense marker is candidate-level and passage review remains pending."
            )
            scope = "CANDIDATE_LEVEL_PROJECT_ANCHOR; PASSAGE_VALIDATION_PENDING"
        elif matches:
            status_note = (
                "A source-backed Priority candidate contains the form, but the target sense "
                "is not responsibly resolved."
            )
            scope = "ATTESTATION_ONLY; TARGET_SENSE_UNRESOLVED"
        else:
            status_note = (
                "Raw Ngram series exists, but no source-backed Priority candidate establishes "
                "a validated attestation or target-sense anchor."
            )
            scope = "NGRAM_STRING_ONLY"

        if "climate" in term or term in {"greenhouse effect", "global warming", "eco-anxiety"}:
            warning = (
                "Early Ngram values may be OCR, phrase adjacency, or another sense; raw string "
                "occurrence is not coinage or validated target meaning."
            )
        else:
            warning = (
                "Generic term is highly polysemous and its Ngram curve is not climate-specific; "
                "candidate context does not establish population prevalence."
            )

        comparison_rows.append({
            "term": term,
            "family": family,
            "anchor_presence": "; ".join(anchors) if anchors else "UNRESOLVED_NO_PRIORITY_CANDIDATE",
            "voice_presence": "; ".join(voices) if voices else "UNRESOLVED_NO_PRIORITY_CANDIDATE",
            "first_ngram_nonzero_year": first_nonzero,
            "first_sustained_ngram_year": first_sustained,
            "first_validated_attestation_year": attestation_year,
            "first_validated_target_sense_year": target_year,
            "ngram_peak_year": peak_year,
            "ngram_peak_per_million": peak_per_million,
            "priority_candidate_match_forms": "; ".join(match_forms) if match_forms else "NONE",
            "validation_scope": scope,
            "current_status_note": status_note,
            "ambiguity_warning": warning,
        })

        for year in sorted(series):
            timeseries_rows.append({
                "term": term,
                "family": family,
                "year": year,
                "normalized_frequency": series[year],
                "frequency_per_million": series[year] * 1_000_000,
                "is_first_nonzero": year == first_nonzero,
                "is_first_sustained": year == sustained,
                "is_peak": year == peak_year,
            })

    write_csv("lexicalisation_comparison.csv", list(comparison_rows[0]), comparison_rows)
    write_csv("lexicalisation_term_timeseries.csv", list(timeseries_rows[0]), timeseries_rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv("AB_object_passages.csv", AB_COLUMNS, [])
    write_csv("threat_linkage_passages.csv", THREAT_REGISTRY_COLUMNS, [])
    write_csv("affect_linkage_passages.csv", AFFECT_REGISTRY_COLUMNS, [])
    build_metric_grids()
    build_voice_comparison()
    build_lexicalisation()

    gap_rows = [{
        "gap_id": "REL-V01-GAP-001",
        "module": "THREAT_AND_AFFECT_PASSAGE_LINKAGE",
        "required_grain": "Validated passage with accepted A/B object annotation and explicit validated C/D relation",
        "available_record_count": 0,
        "blocking_tables": "evidence_passage; lexical_occurrence; semantic_annotation; review_decision; passage_linkage_validation",
        "impact": "All passage denominators are zero and all linkage rates are unsupported.",
        "resolution": "Run targeted semantic passage retrieval, annotation, independent review, and relation validation.",
    }]
    write_csv("linkage_data_gap_registry.csv", list(gap_rows[0]), gap_rows)

    manifest = {
        "analysis_id": "fear-temperature-relational-v0.1",
        "analytical_object": "Validated passage-level relations from A/B temperature-climate objects to D threat or C affect",
        "methodological_principle": "D is not the same as C; co-occurrence is not a validated relation.",
        "source_state": "NO_POPULATED_PASSAGE_CHAIN",
        "available_validated_ab_object_passages": 0,
        "low_n_threshold": LOW_N_THRESHOLD,
        "rate_policy": "Leave rate blank when denominator is zero; never encode missing or unsupported as 0%.",
        "affect_modes": AFFECT_MODES,
        "object_families": OBJECT_FAMILIES,
        "output_directory": str(OUT.relative_to(ROOT)),
        "lexicalisation_sustained_rule": "First of three consecutive annual nonzero observations.",
        "lexicalisation_term_count": len(LEXICAL_TERMS),
        "voice_summary_cells": len(ANCHORS) * len(VOICES),
    }
    (OUT / "linkage_metric_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
