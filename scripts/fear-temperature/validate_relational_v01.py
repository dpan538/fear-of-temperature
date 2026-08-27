#!/usr/bin/env python3
"""Validation gates for the relationship-centred analysis."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "fear-temperature" / "analysis" / "relational-v01"
ANCHORS = ["1842", "1938", "1988", "2006–2007", "2015", "2022"]
VOICES = ["V1", "V2", "V3", "V4", "V5"]


def rows(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_linkage() -> None:
    required = [
        "AB_object_passages.csv", "threat_linkage_passages.csv", "affect_linkage_passages.csv",
        "threat_linkage_by_anchor.csv", "threat_linkage_by_anchor_voice.csv",
        "threat_linkage_by_anchor_object_family.csv", "threat_linkage_by_anchor_source_genre.csv",
        "affect_linkage_by_anchor.csv", "affect_linkage_by_anchor_voice.csv",
        "affect_linkage_by_anchor_object_family.csv", "affect_linkage_by_anchor_source_genre.csv",
        "affect_linkage_by_anchor_affect_mode.csv", "linkage_data_gap_registry.csv",
        "linkage_metric_manifest.json",
    ]
    require(all((OUT / name).exists() for name in required), "linkage output set is incomplete")
    require(rows("AB_object_passages.csv") == [], "A/B registry must remain empty until real validated passages exist")
    require(rows("threat_linkage_passages.csv") == [], "threat registry must not fabricate passage rows")
    require(rows("affect_linkage_passages.csv") == [], "affect registry must not fabricate passage rows")

    for linkage in ["Threat", "Affect"]:
        lower = linkage.lower()
        anchor_rows = rows(f"{lower}_linkage_by_anchor.csv")
        voice_rows = rows(f"{lower}_linkage_by_anchor_voice.csv")
        require(len(anchor_rows) == 6, f"{lower} anchor grid must contain six anchors")
        require(len(voice_rows) == 30, f"{lower} voice grid must contain 6 x 5 cells")
        require({row["anchor"] for row in anchor_rows} == set(ANCHORS), f"{lower} anchors incomplete")
        require({row["voice"] for row in voice_rows} == set(VOICES), f"{lower} voices incomplete")
        for row in anchor_rows + voice_rows:
            require(row["AB_Object_Passage_Count"] == "0", "unsupported denominator must be explicit zero")
            require(row[f"{linkage}_Link_Count"] == "0", "link count must match empty registry")
            require(row[f"{linkage}_Link_Rate"] == "", "zero denominator must produce blank rate")
            require(row["Rate_Status"] == "UNSUPPORTED_DENOMINATOR_ZERO", "rate status missing")
            require(row["Low_N_Flag"] == "True", "zero-denominator cell must be low-N flagged")
            require(row["Data_Status"] == "UNSUPPORTED_NO_VALIDATED_AB_PASSAGES", "data gap must be explicit")

    migration = (ROOT / "db" / "migrations" / "004_relational_passage_linkage.sql").read_text(encoding="utf-8")
    for object_name in [
        "passage_linkage_validation", "vw_ab_object_passages",
        "vw_threat_linkage_passages", "vw_affect_linkage_passages",
    ]:
        require(object_name in migration, f"database scaffold missing {object_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["linkage", "all"], default="all")
    args = parser.parse_args()
    if args.stage in {"linkage", "all"}:
        validate_linkage()
    print(f"PASS relational-v01 validation stage={args.stage}")


if __name__ == "__main__":
    main()
