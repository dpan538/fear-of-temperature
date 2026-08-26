#!/usr/bin/env python3
"""Build the non-destructive analytical relationship layer for Priority 180.

The versioned candidate ledger remains the source/provenance layer.  This
script derives analysis-ready CSVs without changing any candidate record.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "fear-temperature"
EXPORTS = DATA / "exports"
P180 = DATA / "priority180"
ANALYSIS = DATA / "analysis"
ANALYSIS.mkdir(parents=True, exist_ok=True)

ANCHOR_ORDER = ["1842", "1938", "1988", "2006–2007", "2015", "2022"]
ANCHOR_IDS = {
    "1842": "FT-A1842",
    "1938": "FT-A1938",
    "1988": "FT-A1988",
    "2006–2007": "FT-A0607",
    "2015": "FT-A2015",
    "2022": "FT-A2022",
}
LAYERS = ["A", "B", "C", "D"]
VOICES = ["V1", "V2", "V3", "V4", "V5"]
FAMILIES = [
    "temperature_threshold", "heat", "warming", "climate",
    "carbon_greenhouse", "concern_alarm", "worry", "fear_afraid",
    "anxiety", "distress_depression", "danger_threat", "risk",
    "crisis_emergency", "harm_loss_consequences",
]

MISSING_STATES = {
    "NOT_APPLICABLE", "NOT_ANNOTATED_IN_SOURCE", "NOT_EXPOSED_IN_REPORT",
    "NOT_LOCATED", "UNRESOLVED", "ZERO_RESULT",
}

HIGH_AMBIGUITY = {
    "temperature", "heat", "climate", "warming", "concern", "alarm",
    "fear", "afraid", "worry", "worried", "anxiety", "distress",
    "depression", "depressed", "danger", "threat", "risk", "crisis",
    "emergency", "change",
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = re.sub(r"[^\w°%+.-]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip(" .-")


def numeric(value: object) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def explicit(value: object, fallback: str) -> str:
    if value is None or pd.isna(value) or not str(value).strip():
        return fallback
    return str(value).strip()


def write(frame: pd.DataFrame, name: str) -> Path:
    path = ANALYSIS / name
    frame.to_csv(path, index=False, lineterminator="\n")
    return path


def polysemy_status(note: object) -> str:
    text = str(note or "").casefold()
    if any(token in text for token in ("false friend", "not personal", "not itself", "not direct", "highly polysem", "multiple senses")):
        return "HIGH_AMBIGUITY"
    if any(token in text for token in ("polysem", "ambig", "broader", "component", "context")):
        return "CONTEXT_SENSITIVE"
    return "NO_SPECIFIC_POLYSEMY_FLAG"


def missingness(row: pd.Series) -> str:
    states: list[str] = []
    for field, fallback in (
        ("primary_voice", "NOT_ANNOTATED_IN_SOURCE"),
        ("expression_mode", "NOT_EXPOSED_IN_REPORT"),
        ("candidate_provenance", "NOT_EXPOSED_IN_REPORT"),
    ):
        value = explicit(row.get(field), fallback)
        if value in MISSING_STATES or value.startswith("NOT_"):
            states.append(f"{field.upper()}={value}")
    if str(row.get("dictionary_status")) == "UNRESOLVED":
        states.append("DICTIONARY=UNRESOLVED")
    if str(row.get("ngram_status")) == "TECHNICALLY_UNREPRESENTABLE":
        states.append("NGRAM=NOT_APPLICABLE")
    if str(row.get("search_status")) == "COMPLETED_ZERO":
        states.append("SEARCH=ZERO_RESULT")
    return "; ".join(states) if states else "COMPLETE"


def interpretation_warning(row: pd.Series) -> str:
    warnings: list[str] = []
    form_tokens = set(normalize(row.get("surface_form")).split())
    if len(form_tokens) == 1 and form_tokens.intersection(HIGH_AMBIGUITY):
        warnings.append("GENERIC_STRING_REQUIRES_CONTEXT")
    if str(row.get("dictionary_anchor_sense_match")) in {"PARTIAL", "DIFFERENT", "UNRESOLVED"}:
        warnings.append("ANCHOR_AND_MODERN_SENSE_NOT_FULLY_EQUIVALENT")
    if str(row.get("dictionary_status")) == "NO_STANDALONE_HEADWORD":
        warnings.append("PHRASE_NOT_CONVENTIONAL_DICTIONARY_HEADWORD")
    if str(row.get("ngram_mapping_type")) in {"VALIDATED_ALIAS", "NORMALIZED_VARIANT"}:
        warnings.append("NGRAM_MEASURED_VIA_EXPLICIT_MAPPING")
    if str(row.get("ngram_status")) == "TECHNICALLY_UNREPRESENTABLE":
        warnings.append("NO_DIRECT_NGRAM_MEASUREMENT")
    if str(row.get("search_status")) == "COMPLETED_ZERO":
        warnings.append("ZERO_PROVIDER_DISCOVERABILITY_NOT_HISTORICAL_ABSENCE")
    warnings.append("STRING_FREQUENCY_IS_NOT_SEMANTIC_EVIDENCE")
    return "; ".join(dict.fromkeys(warnings))


def candidate_analysis(master: pd.DataFrame, model: pd.DataFrame) -> pd.DataFrame:
    model_small = model[[
        "candidate_id", "anchor_id", "normalized_form", "concept_id",
        "concept_definition", "source_report", "source_page", "provenance_status",
        "ngram_measurement_id",
    ]].copy()
    merged = master.merge(model_small, on="candidate_id", how="left", validate="one_to_one")
    merged["anchor_id"] = merged["anchor_id"].fillna(merged["anchor"].map(ANCHOR_IDS))
    merged["evidence_source"] = merged.apply(
        lambda r: f"{explicit(r.get('source_report'), 'NOT_EXPOSED_IN_REPORT')}; p.{explicit(r.get('source_page'), 'NOT_EXPOSED_IN_REPORT')}", axis=1
    )
    merged["provenance_status"] = merged["provenance_status"].fillna("UNRESOLVED")
    merged["dictionary_polysemy_status"] = merged["dictionary_polysemy_note"].map(polysemy_status)
    merged["ngram_peak_frequency_raw"] = pd.to_numeric(merged["ngram_peak_frequency"], errors="coerce")
    merged["ngram_peak_per_million"] = merged["ngram_peak_frequency_raw"] * 1_000_000
    merged["ngram_anchor_frequency_raw"] = pd.to_numeric(merged["ngram_anchor_value"], errors="coerce")
    merged["ngram_anchor_per_million"] = merged["ngram_anchor_frequency_raw"] * 1_000_000
    merged["ngram_2022_frequency_raw"] = pd.to_numeric(merged["ngram_2022_value"], errors="coerce")
    merged["ngram_2022_per_million"] = merged["ngram_2022_frequency_raw"] * 1_000_000
    merged["search_result_count"] = pd.to_numeric(merged["search_total_results"], errors="coerce")
    merged["search_log10_result_count"] = merged["search_result_count"].map(
        lambda x: math.log10(float(x) + 1) if pd.notna(x) else None
    )
    merged["search_metric_code"] = merged["search_primary_source"].map(
        lambda x: "INTERNET_ARCHIVE_METADATA_TEXT_ITEM_COUNT"
        if "INTERNET_ARCHIVE" in str(x).upper() else explicit(x, "UNRESOLVED")
    )
    merged["annotation_missingness"] = merged.apply(missingness, axis=1)
    merged["interpretation_warning"] = merged.apply(interpretation_warning, axis=1)

    columns = [
        "candidate_id", "anchor_id", "anchor", "priority_rank", "surface_form",
        "normalized_form", "normalized_concept", "lexical_family", "layer",
        "primary_voice", "expression_mode", "evidence_source", "provenance_status",
        "dictionary_status", "dictionary_anchor_sense_match", "dictionary_polysemy_status",
        "ngram_status", "ngram_mapping_type", "ngram_query_id", "ngram_measurement_form", "ngram_first_nonzero_year",
        "ngram_peak_year", "ngram_peak_frequency_raw", "ngram_peak_per_million",
        "ngram_anchor_frequency_raw", "ngram_anchor_per_million",
        "ngram_2022_frequency_raw", "ngram_2022_per_million", "ngram_notes", "search_status",
        "search_metric_code", "search_result_count", "search_log10_result_count",
        "annotation_missingness", "interpretation_warning",
    ]
    result = merged[columns].rename(columns={
        "anchor": "anchor_label", "normalized_concept": "canonical_concept",
        "layer": "layer_code", "primary_voice": "voice_code",
    })
    return result.sort_values(
        ["anchor_label", "priority_rank"], key=lambda s: s.map({a: i for i, a in enumerate(ANCHOR_ORDER)}) if s.name == "anchor_label" else s
    )


def anchor_layer_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for anchor in ANCHOR_ORDER:
        subset = frame[frame.anchor_label == anchor]
        row: dict[str, object] = {"anchor": anchor}
        for layer in LAYERS:
            count = int((subset.layer_code == layer).sum())
            row[f"{layer}_count"] = count
            row[f"{layer}_percentage"] = count / len(subset) if len(subset) else 0
        row["total"] = len(subset)
        rows.append(row)
    return pd.DataFrame(rows)


def anchor_voice_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for anchor in ANCHOR_ORDER:
        subset = frame[frame.anchor_label == anchor]
        row: dict[str, object] = {"anchor": anchor}
        for voice in VOICES:
            count = int((subset.voice_code == voice).sum())
            row[f"{voice}_count"] = count
            row[f"{voice}_percentage"] = count / len(subset) if len(subset) else 0
        row["total"] = len(subset)
        rows.append(row)
    return pd.DataFrame(rows)


def anchor_family_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for anchor in ANCHOR_ORDER:
        subset = frame[frame.anchor_label == anchor]
        counts = Counter(subset.lexical_family)
        for family in FAMILIES:
            count = int(counts.get(family, 0))
            rows.append({
                "anchor": anchor, "family": family, "candidate_count": count,
                "percentage_within_anchor": count / len(subset) if len(subset) else 0,
            })
    return pd.DataFrame(rows)


def voice_family_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for voice in VOICES:
        subset = frame[frame.voice_code == voice]
        counts = Counter(subset.lexical_family)
        for family in FAMILIES:
            rows.append({"voice": voice, "family": family, "candidate_count": int(counts.get(family, 0))})
    return pd.DataFrame(rows)


def anchor_voice_family_counts(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = frame.groupby(["anchor_label", "voice_code", "lexical_family"], dropna=False).size().reset_index(name="candidate_count")
    grouped = grouped.rename(columns={"anchor_label": "anchor", "voice_code": "voice", "lexical_family": "family"})
    return grouped.sort_values(["anchor", "voice", "family"], key=lambda s: s.map({a: i for i, a in enumerate(ANCHOR_ORDER)}) if s.name == "anchor" else s)


def presence_matrix(frame: pd.DataFrame, group_col: str, label_col: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for value, group in frame.groupby(group_col, sort=True):
        row: dict[str, object] = {label_col: value}
        for anchor in ANCHOR_ORDER:
            subset = group[group.anchor_label == anchor]
            row[anchor] = len(subset)
            row[f"{anchor}_candidate_ids"] = "; ".join(subset.candidate_id)
        row["candidate_ids"] = "; ".join(group.candidate_id)
        row["primary_layers"] = "; ".join(sorted(set(group.layer_code)))
        row["voices"] = "; ".join(sorted(set(group.voice_code)))
        rows.append(row)
    return pd.DataFrame(rows)


def measurement_map(master: pd.DataFrame, model: pd.DataFrame) -> pd.DataFrame:
    merged = master.merge(model[["candidate_id", "ngram_measurement_id", "concept_id", "lexical_form_id", "family_id"]], on="candidate_id", how="left", validate="one_to_one")
    out = pd.DataFrame({
        "candidate_id": merged.candidate_id,
        "anchor": merged.anchor,
        "surface_form": merged.surface_form,
        "query_rule_id": merged.ngram_query_id,
        "ngram_measurement_id": merged.ngram_measurement_id.fillna("NOT_APPLICABLE"),
        "ngram_measurement_form": merged.ngram_measurement_form.fillna("NOT_APPLICABLE"),
        "ngram_mapping_type": merged.ngram_mapping_type,
        "ngram_status": merged.ngram_status,
        "dictionary_measurement_key": merged.candidate_id.map(lambda x: f"DICT-{x}"),
        "dictionary_status": merged.dictionary_status,
        "bounded_search_measurement_key": merged.candidate_id.map(lambda x: f"SEARCH-{x}-ALL_AVAILABLE"),
        "search_metric_code": merged.search_primary_source,
        "search_status": merged.search_status,
        "lexical_form_id": merged.lexical_form_id,
        "canonical_concept_id": merged.concept_id,
        "lexical_family_id": merged.family_id,
        "traceability_status": "TRACEABLE",
    })
    return out


def add_relation(rows: list[dict[str, object]], seen: set[tuple[str, str, str]], source: str, target: str,
                 relation_type: str, relation_class: str, anchor_relation: str,
                 evidence_basis: str, confidence: str, provenance_note: str) -> None:
    if not source or not target or source == target:
        return
    key = (source, target, relation_type)
    if key in seen:
        return
    seen.add(key)
    digest = hashlib.sha1("|".join(key).encode("utf-8")).hexdigest()[:14].upper()
    rows.append({
        "relation_id": f"FT-REL-{digest}", "source_candidate_id": source,
        "target_candidate_id": target, "relation_type": relation_type,
        "relation_class": relation_class, "anchor_relation": anchor_relation,
        "evidence_basis": evidence_basis, "confidence": confidence,
        "provenance_note": provenance_note,
    })


def relationship_ledger(frame: pd.DataFrame, model: pd.DataFrame) -> pd.DataFrame:
    work = frame.merge(model[["candidate_id", "ngram_measurement_id"]], on="candidate_id", how="left")
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()

    structural_groups = [
        ("normalized_form", "SAME_SURFACE_FORM", "Normalized lexical form equality"),
        ("canonical_concept", "SAME_CANONICAL_CONCEPT", "Canonical concept equality in candidate ledger"),
        ("lexical_family", "SAME_LEXICAL_FAMILY", "Shared controlled lexical family"),
        ("ngram_measurement_id", "SHARES_NGRAM_MEASUREMENT", "Shared deduplicated Ngram measurement ID"),
    ]
    for column, relation_type, basis in structural_groups:
        for _, group in work[work[column].notna() & (work[column] != "")].groupby(column, sort=True):
            ordered = group.sort_values(["anchor_label", "priority_rank"], key=lambda s: s.map({a: i for i, a in enumerate(ANCHOR_ORDER)}) if s.name == "anchor_label" else s)
            source = ordered.iloc[0]
            for _, target in ordered.iloc[1:].iterrows():
                relation = "CROSS_ANCHOR" if source.anchor_label != target.anchor_label else "WITHIN_ANCHOR"
                add_relation(rows, seen, source.candidate_id, target.candidate_id, relation_type,
                             "COMPUTATIONAL_STRUCTURAL", relation, basis, "HIGH",
                             "Derived from controlled candidate metadata; no semantic evolution is asserted.")

    for _, group in work.groupby("normalized_form", sort=True):
        anchors = set(group.anchor_label)
        voices = set(group.voice_code)
        if len(anchors) > 1:
            ordered = group.sort_values(["anchor_label", "priority_rank"], key=lambda s: s.map({a: i for i, a in enumerate(ANCHOR_ORDER)}) if s.name == "anchor_label" else s)
            base = ordered.iloc[0]
            for _, target in ordered.iloc[1:].iterrows():
                if target.anchor_label != base.anchor_label:
                    add_relation(rows, seen, base.candidate_id, target.candidate_id, "RECURS_ACROSS_ANCHORS",
                                 "COMPUTATIONAL_STRUCTURAL", "CROSS_ANCHOR", "Same normalized lexical form at multiple anchors",
                                 "HIGH", "Recurrence is structural presence in the constructed inventory, not proof of stable sense.")
        if len(voices) > 1:
            ordered = group.sort_values(["voice_code", "candidate_id"])
            base = ordered.iloc[0]
            for _, target in ordered.iloc[1:].iterrows():
                if target.voice_code != base.voice_code:
                    add_relation(rows, seen, base.candidate_id, target.candidate_id, "USED_BY_MULTIPLE_VOICES",
                                 "COMPUTATIONAL_STRUCTURAL", "VOICE_COMPARISON", "Same normalized lexical form assigned to different voices",
                                 "HIGH", "Voice assignment is preserved; shared wording does not imply shared discourse function.")

    for _, row in work[work.ngram_mapping_type.isin(["NORMALIZED_VARIANT", "VALIDATED_ALIAS"])].iterrows():
        targets = work[(work.ngram_measurement_form.map(normalize) == normalize(row.ngram_measurement_form)) & (work.candidate_id != row.candidate_id)]
        if not targets.empty:
            target = targets.sort_values("candidate_id").iloc[0]
            add_relation(rows, seen, row.candidate_id, target.candidate_id, "NORMALIZED_VARIANT_OF",
                         "COMPUTATIONAL_STRUCTURAL", "MEASUREMENT_MAPPING", row.ngram_notes, "HIGH",
                         "Explicit candidate-to-measurement mapping from the Priority 180 acquisition audit.")

    by_form_anchor = {(normalize(r.surface_form), r.anchor_label): r.candidate_id for _, r in work.iterrows()}
    semantic_specs = [
        ("depressing effect", "1842", "depressed", "2022", "SAME_FAMILY_DIFFERENT_SENSE", "Dictionary sense audit and FT-SR-1842-DEPRESSING", "HIGH", "Embodied/bodily energetic meaning must not be read as modern clinical depression."),
        ("global security", "1988", "climate anxiety", "2022", "RELATED_NOT_EQUIVALENT", "FT-SR-1988-SECURITY and FT-SR-2022-ANXIETY", "HIGH", "Institutional threat/security framing is not personal affect."),
        ("Be Worried. Be Very Worried.", "2006–2007", "personally worry", "2006–2007", "SAME_FAMILY_DIFFERENT_SENSE", "FT-SR-2006-WORRIED and FT-SR-2007-WORRY", "HIGH", "Media-prescribed worry differs from survey-elicited endorsement."),
        ("common concern of humankind", "2015", "very worried", "2015", "RELATED_NOT_EQUIVALENT", "FT-SR-2015-CONCERN and candidate dictionary audit", "HIGH", "Legal common concern is not personal emotion."),
        ("climate", "1842", "climate anxiety", "2022", "FALSE_CONTINUITY_RISK", "Dictionary anchor-sense comparison", "HIGH", "Historical climatological condition cannot silently inherit modern climate-anxiety meaning."),
        ("climate anxiety", "2022", "very worried", "2022", "RELATED_NOT_EQUIVALENT", "FT-SR-2022-ANXIETY and FT-SR-2022-WORRIED", "HIGH", "Research construct and instrument-supplied participant endorsement require separate provenance."),
    ]
    for sf, sa, tf, ta, rt, basis, conf, note in semantic_specs:
        source = by_form_anchor.get((normalize(sf), sa))
        target = by_form_anchor.get((normalize(tf), ta))
        add_relation(rows, seen, source, target, rt, "RESEARCH_SEMANTIC_CANDIDATE", "CROSS_ANCHOR" if sa != ta else "WITHIN_ANCHOR",
                     basis, conf, note)
    return pd.DataFrame(rows).sort_values(["relation_class", "relation_type", "source_candidate_id", "target_candidate_id"])


def comparability(frame: pd.DataFrame) -> pd.DataFrame:
    specifications = [
        ("temperature", "temperature_threshold", "STRONGLY_COMPARABLE", "Instrumental/aggregate referents must still be separated."),
        ("heat", "heat", "PARTIALLY_COMPARABLE", "Physical heat, embodied exposure, heatwaves and hazard framing are related but not equivalent."),
        ("climate", "climate", "NOT_COMPARABLE", "The 1842 historical climatological sense cannot be treated as modern climate-change issue language."),
        ("warming", "warming", "PARTIALLY_COMPARABLE", "Temperature increase, climate-system warming and the issue label global warming differ in scope."),
        ("concern", "concern_alarm", "NOT_COMPARABLE", "Legal common concern, institutional concern and personal concern are different discourse functions."),
        ("worry", "worry", "PARTIALLY_COMPARABLE", "Media prescription, elicited response and participant wording require expression-mode separation."),
        ("fear", "fear_afraid", "UNRESOLVED", "Generic fear strings do not establish a stable climate/temperature referent."),
        ("anxiety", "anxiety", "PARTIALLY_COMPARABLE", "Researcher-coded climate anxiety and lay self-description require provenance separation."),
        ("threat", "danger_threat", "PARTIALLY_COMPARABLE", "Institutional threat can recur, but threat is not affect and referents vary."),
        ("risk", "risk", "PARTIALLY_COMPARABLE", "Institutional, scientific and public risk framings are not automatically interchangeable."),
        ("crisis", "crisis_emergency", "PARTIALLY_COMPARABLE", "Generic crisis and climate-specific crisis differ in semantic constraint."),
        ("emergency", "crisis_emergency", "PARTIALLY_COMPARABLE", "Emergency declarations and generic emergency language have different institutional force."),
        ("distress/depression", "distress_depression", "NOT_COMPARABLE", "1842 depressing effect is a false friend for modern psychological depression."),
    ]
    rows: list[dict[str, object]] = []
    for label, family, status, reason in specifications:
        subset = frame[frame.lexical_family == family]
        anchors = [a for a in ANCHOR_ORDER if a in set(subset.anchor_label)]
        if len(anchors) < 2:
            rows.append({
                "term_or_family": label, "source_anchor": anchors[0] if anchors else "NOT_LOCATED",
                "target_anchor": "NOT_LOCATED", "source_voice": "; ".join(sorted(set(subset.voice_code))) or "NOT_LOCATED",
                "target_voice": "NOT_LOCATED", "comparison_status": "UNRESOLVED",
                "reason": f"{reason} Cross-anchor comparison cannot be resolved from the current Priority inventory.",
            })
            continue
        for source_anchor, target_anchor in zip(anchors, anchors[1:]):
            source_voices = "; ".join(sorted(set(subset[subset.anchor_label == source_anchor].voice_code)))
            target_voices = "; ".join(sorted(set(subset[subset.anchor_label == target_anchor].voice_code)))
            rows.append({
                "term_or_family": label, "source_anchor": source_anchor, "target_anchor": target_anchor,
                "source_voice": source_voices, "target_voice": target_voices,
                "comparison_status": status, "reason": reason,
            })
    return pd.DataFrame(rows)


def coverage_bias(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add_dimension(anchor: str, dimension: str, series: pd.Series) -> None:
        counts = Counter(series.astype(str))
        for status, count in sorted(counts.items()):
            rows.append({
                "anchor": anchor, "dimension": dimension, "status": status,
                "candidate_count": int(count), "percentage_within_anchor": count / len(series) if len(series) else 0,
                "interpretation_note": "Coverage/composition diagnostic; not historical prevalence.",
            })

    for anchor in ANCHOR_ORDER:
        subset = frame[frame.anchor_label == anchor].copy()
        add_dimension(anchor, "VOICE_COVERAGE", subset.voice_code.map(lambda x: explicit(x, "NOT_ANNOTATED_IN_SOURCE")))
        add_dimension(anchor, "EXPRESSION_MODE_COMPLETENESS", subset.expression_mode.map(lambda x: explicit(x, "NOT_EXPOSED_IN_REPORT")))
        add_dimension(anchor, "DICTIONARY_STATUS", subset.dictionary_status.map(lambda x: explicit(x, "UNRESOLVED")))
        add_dimension(anchor, "NGRAM_STATUS", subset.ngram_status.map(lambda x: "ZERO_RESULT" if "ZERO_RESPONSE" in str(x) else ("NOT_APPLICABLE" if x == "TECHNICALLY_UNREPRESENTABLE" else explicit(x, "UNRESOLVED"))))
        add_dimension(anchor, "BOUNDED_SEARCH_STATUS", subset.search_status.map(lambda x: "ZERO_RESULT" if x == "COMPLETED_ZERO" else explicit(x, "UNRESOLVED")))
        add_dimension(anchor, "PROVENANCE_COMPLETENESS", subset.provenance_status.map(lambda x: explicit(x, "UNRESOLVED")))
    return pd.DataFrame(rows)


def main() -> None:
    master = pd.read_csv(EXPORTS / "priority180_full_coverage_matrix.csv", keep_default_na=False)
    model = pd.read_csv(P180 / "priority180_candidate_model.csv", keep_default_na=False)
    if len(master) != 180 or master.candidate_id.nunique() != 180:
        raise SystemExit("Priority master must contain exactly 180 unique candidates")

    analysis = candidate_analysis(master, model)
    layer = anchor_layer_counts(analysis)
    voice = anchor_voice_counts(analysis)
    family = anchor_family_counts(analysis)
    voice_family = voice_family_counts(analysis)
    avf = anchor_voice_family_counts(analysis)
    term_presence = presence_matrix(analysis, "normalized_form", "normalized_lexical_form")
    family_presence = presence_matrix(analysis, "lexical_family", "lexical_family")
    measurements = measurement_map(master, model)
    relations = relationship_ledger(analysis, model)
    comparisons = comparability(analysis)
    bias = coverage_bias(analysis)

    outputs = {
        "candidate_analysis_180.csv": analysis,
        "anchor_layer_counts.csv": layer,
        "anchor_voice_counts.csv": voice,
        "anchor_family_counts.csv": family,
        "voice_family_counts.csv": voice_family,
        "anchor_voice_family_counts.csv": avf,
        "term_anchor_presence.csv": term_presence,
        "family_anchor_presence.csv": family_presence,
        "candidate_measurement_map.csv": measurements,
        "candidate_relationship.csv": relations,
        "candidate_comparability.csv": comparisons,
        "coverage_bias_matrix.csv": bias,
    }
    for name, frame in outputs.items():
        write(frame, name)

    manifest = {
        "analysis_version": "exploratory-analysis-v0.2",
        "generated_on": date.today().isoformat(),
        "source": str((EXPORTS / "priority180_full_coverage_matrix.csv").relative_to(ROOT)),
        "priority_rows": len(analysis),
        "relationship_rows": len(relations),
        "comparability_rows": len(comparisons),
        "outputs": {name: len(frame) for name, frame in outputs.items()},
        "principle": "Derived analytical layer; source candidate ledger is not modified.",
    }
    (ANALYSIS / "eda_relationship_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
