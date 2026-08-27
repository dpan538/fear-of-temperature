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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv("AB_object_passages.csv", AB_COLUMNS, [])
    write_csv("threat_linkage_passages.csv", THREAT_REGISTRY_COLUMNS, [])
    write_csv("affect_linkage_passages.csv", AFFECT_REGISTRY_COLUMNS, [])
    build_metric_grids()

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
    }
    (OUT / "linkage_metric_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
