#!/usr/bin/env python3
"""Validation gates for the relationship-centred analysis."""

from __future__ import annotations

import argparse
import csv
import math
import json
import zipfile
from PIL import Image
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


def validate_comparison() -> None:
    voice = rows("voice_linkage_summary.csv")
    require(len(voice) == 30, "voice summary must contain 6 x 5 cells")
    for row in voice:
        require(row["AB_Object_Passage_Count"] == "0", "voice denominator mismatch")
        require(row["Threat_Link_Rate"] == "" and row["Affect_Link_Rate"] == "", "unsupported rates must be blank")
        require(row["Threat_to_Affect_Ratio"] == "", "ratio must be blank when component rates are missing")
        require(row["Ratio_Status"] == "UNSUPPORTED_MISSING_RATES", "ratio status missing")
        require(row["Low_N_Flag"] == "True", "low-N flag missing from voice summary")

    inventory = rows("inventory_voice_layer_balance.csv")
    require(len(inventory) == 30, "inventory balance must contain 6 x 5 cells")
    require(sum(int(row["Total_Priority_Candidates"]) for row in inventory) == 180, "inventory voice totals must reconcile to 180")
    require(
        all(row["Evidence_Class"] == "CONSTRUCTED_INVENTORY_PATTERN" for row in inventory),
        "inventory counts must be labelled as constructed",
    )

    lexical = rows("lexicalisation_comparison.csv")
    require(len(lexical) == 17, "lexicalisation comparison must contain 17 selected terms")
    require(len({row["term"] for row in lexical}) == 17, "lexicalisation terms must be unique")
    required_families = {"climate_framing", "affect_specialisation", "threat_specialisation"}
    require({row["family"] for row in lexical} == required_families, "lexicalisation family set incomplete")
    for row in lexical:
        for field in [
            "first_ngram_nonzero_year", "first_sustained_ngram_year",
            "first_validated_attestation_year", "first_validated_target_sense_year",
        ]:
            require(row[field] != "", f"{field} must be a year or explicit UNRESOLVED")
        require(row["current_status_note"] != "" and row["ambiguity_warning"] != "", "lexical caution missing")

    timeseries = rows("lexicalisation_term_timeseries.csv")
    require(len(timeseries) == 17 * 181, "selected lexical series must contain 17 x 181 observations")
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in timeseries:
        grouped.setdefault(row["term"], []).append(row)
    for row in lexical:
        term_rows = grouped[row["term"]]
        positive = [int(item["year"]) for item in term_rows if float(item["normalized_frequency"]) > 0]
        expected_first = str(min(positive)) if positive else "UNRESOLVED"
        require(row["first_ngram_nonzero_year"] == expected_first, f"first nonzero mismatch for {row['term']}")
        peak = max(term_rows, key=lambda item: (float(item["normalized_frequency"]), -int(item["year"])))
        require(row["ngram_peak_year"] == peak["year"], f"peak year mismatch for {row['term']}")
        require(math.isclose(float(row["ngram_peak_per_million"]), float(peak["normalized_frequency"]) * 1_000_000, rel_tol=1e-12), f"peak unit mismatch for {row['term']}")


def validate_figures() -> None:
    figure_dir = ROOT / "figures/fear-temperature/relational-v01"
    manifest = json.loads((figure_dir / "figure_manifest.json").read_text(encoding="utf-8"))
    require(manifest["figure_count"] == 12, "exactly 12 relational figures required")
    metadata = rows_from_path(figure_dir / "sources/figure_metadata_source.csv")
    require(len(metadata) == 12, "figure metadata must contain 12 rows")
    required_ids = {f"figure_{number:02d}" for number in range(1, 13)}
    require({row["figure_id"][:9] for row in metadata} == required_ids, "required figure numbering incomplete")
    for row in metadata:
        stem = row["figure_id"]
        png = figure_dir / f"{stem}.png"
        svg = figure_dir / f"{stem}.svg"
        source = ROOT / row["source_csv"]
        meta = figure_dir / f"{stem}_metadata.json"
        require(png.exists() and png.stat().st_size > 10_000, f"missing or blank PNG: {stem}")
        require(svg.exists() and svg.stat().st_size > 1_000, f"missing or blank SVG: {stem}")
        require(source.exists() and source.stat().st_size > 20, f"missing figure source: {stem}")
        require(meta.exists(), f"missing figure metadata: {stem}")
        require(row["caption"] and row["interpretation_warning"], f"figure caveat missing: {stem}")
        with Image.open(png) as image:
            require(image.size == (1600, 1000), f"unexpected figure dimensions: {stem}")
    for number in [2, 3, 4, 5, 6]:
        item = next(row for row in metadata if row["figure_id"].startswith(f"figure_{number:02d}_"))
        require("zero" in item["interpretation_warning"].lower() or "not estimable" in item["caption"].lower() or "unsupported" in item["caption"].lower(), f"missing zero/missing safeguard in figure {number}")


def validate_workbook() -> None:
    validation_path = OUT / "relational_workbook_validation.json"
    require(validation_path.exists(), "relational workbook validation record missing")
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    require(validation["status"] == "PASS", "workbook status did not pass")
    require(validation["formula_check"] == "PASS", "workbook formula scan did not pass")
    require(validation["artifact_tool_reopen_check"] == "PASS", "artifact-tool reopen check failed")
    require(validation["sheet_inspection_contains_all_new_sheets"], "new workbook sheet set incomplete")
    require(validation["new_sheet_count"] == 7, "seven presentation sheets required")
    require(validation["source_priority_candidates"] == 180, "workbook candidate total mismatch")
    require(validation["validated_ab_object_passages"] == 0, "workbook passage denominator mismatch")
    require(validation["threat_linked_passages"] == 0 and validation["affect_linked_passages"] == 0, "workbook link counts mismatch")
    require(validation["lexicalisation_terms"] == 17, "workbook lexical term total mismatch")
    require(validation["relational_figure_count"] == 12, "workbook figure total mismatch")
    require(validation["rendered_new_sheets"] == 7, "all new sheets must be rendered")
    open_check_path = OUT / "relational_workbook_open_check.json"
    require(open_check_path.exists(), "independent workbook open check missing")
    open_check = json.loads(open_check_path.read_text(encoding="utf-8"))
    require(open_check["status"] == "PASS" and open_check["exported_pdf_pages"] > 0, "independent workbook open check failed")
    workbook_path = ROOT / "outputs/quantitative-v01/fear_temperature_quantitative_v01.xlsx"
    require(workbook_path.exists() and workbook_path.stat().st_size > 1_000_000, "workbook missing or unexpectedly small")
    with zipfile.ZipFile(workbook_path) as archive:
        names = archive.namelist()
        require("xl/workbook.xml" in names, "invalid XLSX package")
        require(sum(name.startswith("xl/media/") for name in names) >= 22, "embedded relational figures missing")
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        for sheet_name in validation["new_sheet_names"]:
            require(sheet_name in workbook_xml, f"workbook XML missing sheet: {sheet_name}")
    brief = ROOT / "docs/research/fear-temperature/SUPERVISOR_BRIEFING_ONEPAGE.md"
    require(brief.exists(), "supervisor briefing missing")
    text = brief.read_text(encoding="utf-8")
    for phrase in [
        "Threat is not affect", "180 Priority Candidates", "not yet estimable",
        "targeted semantic passage validation",
    ]:
        require(phrase in text, f"supervisor briefing missing required point: {phrase}")


def rows_from_path(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["linkage", "comparison", "figures", "workbook", "all"], default="all")
    args = parser.parse_args()
    if args.stage in {"linkage", "all"}:
        validate_linkage()
    if args.stage in {"comparison", "all"}:
        validate_comparison()
    if args.stage in {"figures", "all"}:
        validate_figures()
    if args.stage in {"workbook", "all"}:
        validate_workbook()
    print(f"PASS relational-v01 validation stage={args.stage}")


if __name__ == "__main__":
    main()
