#!/usr/bin/env python3
"""Build the 143-rule provisional quantitative query inventory.

The unavailable legacy query_rules.csv is never impersonated. This builder assigns
new FT-Q-V01-* IDs to report-visible Priority forms and to the explicitly required
quantitative baseline terms. Every rule carries source/report provenance and an
Ngram compatibility decision; unsupported rules remain present in the audit.
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data" / "fear-temperature" / "seed"
EXPORTS = ROOT / "data" / "fear-temperature" / "exports"
SQL_PATH = ROOT / "db" / "seeds" / "003_quantitative_query_inventory.sql"
VERSION_ID = "fear-temperature-quant-v0.1-provisional"
LATEST_REPORT = "Fear of Temperature — Deep Research Round Two_ Historical Semantic Validation, Cross-Voice Relationa.pdf"

ANCHOR_ORDER = ["FT-A1842", "FT-A1938", "FT-A1988", "FT-A0607", "FT-A2015", "FT-A2022"]
ANCHOR_WINDOWS = {
    "FT-A1842": ("1842", 1842, 1842, 1839, 1845),
    "FT-A1938": ("1938", 1938, 1938, 1936, 1940),
    "FT-A1988": ("1988", 1988, 1988, 1986, 1990),
    "FT-A0607": ("2006–2007", 2006, 2007, 2005, 2008),
    "FT-A2015": ("2015", 2015, 2015, 2014, 2016),
    "FT-A2022": ("2022", 2022, 2022, 2021, 2023),
}

# These are the required quantitative groups in the task contract. They are
# inserted only when the top-ranked report-visible Priority selection does not
# already contain the surface form.
MANDATORY_TERMS = [
    ("climatic change", "FT-A1938"),
    ("climate change", "FT-A2015"),
    ("greenhouse effect", "FT-A1988"),
    ("global warming", "FT-A1988"),
    ("changing atmosphere", "FT-A1988"),
    ("climate system", "FT-A0607"),
    ("climate crisis", "FT-A2022"),
    ("climate emergency", "FT-A2022"),
    ("temperature", "FT-A1842"),
    ("mean temperature", "FT-A1842"),
    ("temperature increase", "FT-A0607"),
    ("global temperature", "FT-A1988"),
    ("global average temperature", "FT-A2015"),
    ("heat", "FT-A1842"),
    ("heat wave", "FT-A1938"),
    ("extreme heat", "FT-A2022"),
    ("fear", "FT-A2022"),
    ("afraid", "FT-A2022"),
    ("worry", "FT-A0607"),
    ("worried", "FT-A0607"),
    ("concern", "FT-A2015"),
    ("anxiety", "FT-A2022"),
    ("climate anxiety", "FT-A2022"),
    ("eco-anxiety", "FT-A2022"),
    ("distress", "FT-A2022"),
    ("psychological distress", "FT-A2022"),
    ("depressed", "FT-A2022"),
    ("danger", "FT-A0607"),
    ("threat", "FT-A1988"),
    ("risk", "FT-A2015"),
    ("crisis", "FT-A1988"),
    ("emergency", "FT-A2015"),
    ("damage", "FT-A0607"),
    ("loss and damage", "FT-A2015"),
    ("mortality", "FT-A2022"),
]

GENERIC = {
    "temperature", "heat", "climate", "warming", "fear", "afraid", "worry",
    "worried", "concern", "alarm", "anxiety", "distress", "depression",
    "depressed", "danger", "threat", "risk", "crisis", "emergency", "change",
    "damage", "mortality", "air", "atmosphere", "weather", "drought",
}

EXCLUSIONS = {
    "temperature": "Exclude body/fever, cooking, and unrelated industrial senses during passage review.",
    "heat": "Exclude cooking, oven, machinery, process heat, and political metaphor senses.",
    "climate": "Exclude business, political, social, and school climate senses.",
    "warming": "Exclude warming food/rooms and interpersonal metaphor senses.",
    "concern": "Separate personal affect, institutional evaluation, legal formula, and business-enterprise senses.",
    "alarm": "Exclude alarm devices and clocks; require an attributed public/actor reaction.",
    "fear": "Require an identified experiencer and climate/temperature/consequence target.",
    "worry": "Separate media prescription, instrument wording, participant endorsement, and spontaneous use.",
    "worried": "Separate media prescription, instrument wording, participant endorsement, and spontaneous use.",
    "anxiety": "Exclude unrelated clinical uses; preserve researcher/instrument/participant provenance.",
    "distress": "Exclude financial distress, distress signals, and unrelated clinical contexts.",
    "depression": "Exclude economic, topographic, meteorological, and unrelated clinical senses.",
    "depressed": "Exclude economic, topographic, meteorological, and unrelated clinical senses.",
    "danger": "Require the danger object and threatened subject.",
    "threat": "Exclude military, cyber, and unrelated political threat senses; threat is not affect.",
    "risk": "Exclude investment, credit, surgery, and unrelated insurance senses; risk is not emotion.",
    "crisis": "Exclude generic economic, political, and health crises without a climate referent.",
    "emergency": "Exclude medical and unrelated emergency-service senses.",
    "change": "Standalone change is prohibited; only constrained historical or climate forms are allowed.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", value).strip()


def sql(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    return "'" + str(value).replace("'", "''") + "'"


def rank_of(row: dict[str, str]) -> int:
    match = re.search(r"PRIORITY_RANK=(\d+)", row["original_decision"])
    if not match:
        raise ValueError(f"Missing Priority rank: {row}")
    return int(match.group(1))


def choose_concept(surface: str, layer: str, concepts: list[dict[str, str]]) -> dict[str, str]:
    """Choose the nearest retained concept without treating family terms as synonyms."""
    s = normalize(surface)
    by_code = {r["concept_code"]: r for r in concepts}

    def use(code: str) -> dict[str, str]:
        return by_code[code]

    if "1.5" in s or "1·5" in s:
        return use("temperature_threshold_1_5c")
    if "2°" in s or re.search(r"\b2 ?c\b", s):
        return use("temperature_threshold_2c")
    if any(x in s for x in ("global average temperature", "global surface temperature", "global temperature", "world temperature", "global average air")):
        return use("global_aggregate_temperature")
    if "mean temperature" in s:
        return use("mean_temperature")
    if any(x in s for x in ("thermometer", "temperature", "degree")) and "increase" not in s:
        return use("local_instrumental_temperature")
    if any(x in s for x in ("extreme heat", "unbearable heat", "excessive heat", "heat-related")):
        return use("extreme_heat_hazard")
    if any(x in s for x in ("heat wave", "heatwave", "hottest", "scorching", "hot weather", "hot spell")):
        return use("heatwave_weather_event")
    if "heat" in s or "sun" in s:
        if any(x in s for x in ("men", "suffocating", "faint", "perspiration", "complain")):
            return use("embodied_heat_exposure")
        return use("physical_heat_state")
    if "global warming" in s:
        return use("global_warming_issue_label")
    if any(x in s for x in ("warming of the climate system", "climate warming")):
        return use("climate_system_warming")
    if any(x in s for x in ("warming", "warmer", "temperature increase", "actually increased")):
        return use("temperature_increase")
    if "changing atmosphere" in s:
        return use("changing_atmosphere")
    if "climate system" in s or "climate model" in s:
        return use("climate_system")
    if "climatic change" in s or "change of climate" in s:
        return use("historical_climatic_change")
    if "climate change" in s:
        return use("modern_climate_change")
    if any(x in s for x in ("greenhouse gas", "ghg emissions")):
        return use("anthropogenic_greenhouse_gas_emissions")
    if "greenhouse" in s:
        return use("greenhouse_mechanism")
    if any(x in s for x in ("artificial production of carbon dioxide", "anthropogenic co2", "fuel combustion")):
        return use("anthropogenic_carbon_dioxide_production")
    if "carbon dioxide" in s or "co₂" in s:
        return use("atmospheric_carbon_dioxide")
    if any(x in s for x in ("climate", "meteorological", "weather", "atmosphere", "air", "radiation", "water vapour")) and layer == "B":
        return use("historical_climate_condition")
    if "common concern of humankind" in s:
        return use("common_concern_legal_formula")
    if "alarm" in s:
        return use("public_alarm")
    if "concern" in s:
        return use("personal_concern" if layer == "C" else "institutional_evaluation")
    if "personally worry" in s or "worry a great deal" in s:
        return use("elicited_worry_category")
    if "very worried" in s or "somewhat worried" in s:
        return use("participant_worry_endorsement")
    if "worried" in s or "worry" in s:
        return use("prescribed_worry" if "be worried" in s else "spontaneous_worry")
    if "afraid" in s:
        return use("participant_afraid_endorsement")
    if "fear" in s:
        return use("direct_fear")
    if "climate anxiety" in s:
        return use("climate_anxiety_research_construct")
    if "eco-anxiety" in s or "eco anxiety" in s:
        return use("eco_anxiety_research_construct")
    if any(x in s for x in ("symptoms of anxiety", "anxiety and stress")):
        return use("anxiety_symptom_measure")
    if "anxiety" in s or "anxious" in s:
        return use("anxious_affect")
    if "depressing effect" in s:
        return use("historical_depressing_effect")
    if "psychological distress" in s or "distress" in s:
        return use("psychological_distress")
    if any(x in s for x in ("depress", "hopeless", "sad", "guilt", "angry", "frustrated", "outraged", "disgusted", "powerlessness")):
        return use("depressed_affect")
    if "global security" in s:
        return use("global_security_frame")
    if any(x in s for x in ("threat", "danger", "deadly", "grave")):
        return use("institutional_climate_threat" if layer == "D" else "hazard_evaluation")
    if any(x in s for x in ("risk", "probability")):
        return use("administrative_risk_assessment" if layer == "D" else "probabilistic_risk")
    if "climate crisis" in s:
        return use("climate_crisis_issue_label")
    if "climate emergency" in s:
        return use("climate_emergency_declaration")
    if "emergency" in s:
        return use("emergency_response_category")
    if "crisis" in s:
        return use("severity_crisis_predicate")
    if "loss and damage" in s:
        return use("loss_and_damage")
    if "non-economic" in s:
        return use("non_economic_losses")
    if "mortality" in s or "death" in s:
        return use("mortality")
    if "vulnerab" in s:
        return use("vulnerability")
    if "future generation" in s:
        return use("future_generation_harm")
    if any(x in s for x in ("harm", "damage", "impact", "effect", "drought", "flood", "fire", "ill health", "shortage", "hunger", "dislocation")):
        return use("generic_damage")
    if layer == "A":
        return use("local_instrumental_temperature")
    if layer == "B":
        return use("historical_climate_condition")
    if layer == "C":
        return use("personal_concern")
    return use("generic_damage")


def compatibility(surface: str) -> tuple[str, str]:
    s = normalize(surface)
    tokens = re.findall(r"[a-z]+(?:[-'][a-z]+)*|\d+(?:\.\d+)?", s)
    if s == "change":
        return "SEMANTICALLY_USELESS_ISOLATED", "Standalone 'change' is prohibited by the semantic contract."
    if "/" in surface:
        return "STRUCTURALLY_UNSUPPORTED", "Slash construction is not a defensible isolated Ngram phrase."
    if len(tokens) > 7:
        return "TOO_LONG", f"Contains {len(tokens)} lexical tokens; exceeds the current seven-token public-interface ceiling."
    if any(symbol in surface for symbol in ("°", "₂", "₁")):
        return "NUMERIC_OR_SYMBOLIC", "Degree/subscript notation is not queried as an isolated public-interface Ngram."
    if sum(surface.count(mark) for mark in (".", "!", "?", ";", ":")) >= 2:
        return "PUNCTUATION_HEAVY", "Sentence-level punctuation makes this a corpus-context rule, not an Ngram phrase."
    if not tokens:
        return "STRUCTURALLY_UNSUPPORTED", "No queryable lexical tokens."
    return "COMPATIBLE", "Compatible exact string/phrase for unsmoothed public Ngram retrieval (current interface supports up to seven words)."


def risks(surface: str, interpretation: str, compatible: str) -> tuple[str, str, str]:
    s = normalize(surface)
    ambiguity = "HIGH" if s in GENERIC or interpretation == "BACKGROUND_AMBIGUOUS" else "MEDIUM"
    precision = "HIGH" if s in EXCLUSIONS or compatible != "COMPATIBLE" else ("MEDIUM" if len(s.split()) == 1 else "LOW")
    recall = "HIGH" if "-" in s or compatible != "COMPATIBLE" else ("MEDIUM" if len(s.split()) >= 4 else "LOW")
    return ambiguity, precision, recall


def main() -> None:
    seed_rows = read_csv(SEED / "seed_candidates.csv")
    concepts = read_csv(SEED / "canonical_concepts.csv")
    families = {row["family_id"]: row for row in read_csv(SEED / "lexical_families.csv")}
    high_forms = read_csv(SEED / "high_value_lexical_forms.csv")
    form_by_normalized = {row["normalized_form"]: row for row in high_forms}

    priority = [row for row in seed_rows if row["originating_seed_stage"] == "PRIORITY_180"]
    priority.sort(key=lambda row: (ANCHOR_ORDER.index(row["anchor_id"]), rank_of(row)))

    selected: list[dict[str, str]] = [row for row in priority if rank_of(row) <= 20]
    globally_selected = {normalize(row["surface_form"]) for row in selected}

    for surface, anchor_id in MANDATORY_TERMS:
        if normalize(surface) in globally_selected:
            continue
        high = form_by_normalized.get(normalize(surface), {})
        selected.append({
            "seed_candidate_id": "",
            "originating_seed_stage": "HIGH_VALUE_CASE",
            "original_candidate_id": "",
            "source_page": "14–17",
            "anchor_id": anchor_id,
            "surface_form": surface,
            "layer_code": families.get(next((c["family_id"] for c in concepts if c["concept_id"] == high.get("concept_id")), ""), {}).get("primary_layer_code", ""),
            "voice_code": "",
            "source_id": "",
            "original_decision": "MANDATORY_QUANTITATIVE_BASELINE_TERM",
            "reconciliation_status": "QUERY_VARIANT",
            "originating_report": LATEST_REPORT,
            "provenance_note": "Required quantitative baseline term from the current methodological contract; assigned a new project query ID.",
        })
        globally_selected.add(normalize(surface))

    # The report states that the missing artifact contained 143 rules. Fill the
    # remaining reconstructed ledger with the next report-visible Priority rows.
    selected_keys = {(row["anchor_id"], normalize(row["surface_form"])) for row in selected}
    for row in sorted(priority, key=lambda r: (rank_of(r), ANCHOR_ORDER.index(r["anchor_id"]))):
        key = (row["anchor_id"], normalize(row["surface_form"]))
        if key in selected_keys:
            continue
        selected.append(row)
        selected_keys.add(key)
        if len(selected) == 143:
            break
    if len(selected) != 143:
        raise ValueError(f"Expected 143 reconstructed rules, found {len(selected)}")

    all_forms = list(high_forms)
    known_forms = {row["normalized_form"]: row for row in all_forms}
    senses: list[dict[str, str]] = []
    rules: list[dict[str, Any]] = []
    contexts: list[dict[str, str]] = []

    concept_by_id = {row["concept_id"]: row for row in concepts}
    for sequence, source in enumerate(selected, 1):
        surface = re.sub(r"\s+", " ", source["surface_form"]).strip()
        norm = normalize(surface)
        layer = source.get("layer_code") or ""
        existing = known_forms.get(norm)
        if existing:
            concept = concept_by_id[existing["concept_id"]]
            form = existing
            interpretation = {
                "CLIMATE_SPECIFIC": "CLIMATE_SPECIFIC",
                "BACKGROUND_OR_AMBIGUOUS": "BACKGROUND_AMBIGUOUS",
                "CONTEXT_REQUIRED": "CONTEXT_REQUIRED",
                "NEGATIVE_CONTROL": "NEGATIVE_CONTROL",
                "PROHIBITED_STANDALONE": "PROHIBITED_STANDALONE",
            }[existing["ambiguity_class"]]
        else:
            concept = choose_concept(surface, layer or "D", concepts)
            family = families[concept["family_id"]]
            layer = layer or family["primary_layer_code"]
            interpretation = "BACKGROUND_AMBIGUOUS" if norm in GENERIC else "CONTEXT_REQUIRED"
            form_id = "FT-LF-Q-" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12].upper()
            form = {
                "lexical_form_id": form_id,
                "surface_form": surface,
                "normalized_form": norm,
                "concept_id": concept["concept_id"],
                "ambiguity_class": "BACKGROUND_OR_AMBIGUOUS" if interpretation == "BACKGROUND_AMBIGUOUS" else "CONTEXT_REQUIRED",
                "is_high_value": "False",
                "provenance_note": "Provisional query form reconstructed from a report-visible research row; new project ID, not a recovered legacy form ID.",
            }
            known_forms[norm] = form
            all_forms.append(form)
        family = families[concept["family_id"]]
        layer = layer or family["primary_layer_code"]
        status, reason = compatibility(surface)
        eligible = status == "COMPATIBLE"
        if eligible and interpretation == "BACKGROUND_AMBIGUOUS":
            classification = "BACKGROUND_AMBIGUOUS"
        elif eligible:
            classification = "EXECUTABLE_NGRAM"
        elif status in {"TOO_LONG", "PUNCTUATION_HEAVY", "NUMERIC_OR_SYMBOLIC", "STRUCTURALLY_UNSUPPORTED"}:
            classification = "EXECUTABLE_CORPUS_ONLY"
        else:
            classification = "CONTEXT_ONLY"
        ambiguity, precision, recall = risks(surface, interpretation, status)
        label, strict_start, strict_end, contextual_start, contextual_end = ANCHOR_WINDOWS[source["anchor_id"]]
        query_id = f"FT-Q-V01-{sequence:03d}"
        exclusion = EXCLUSIONS.get(norm, "")
        source_page = source.get("source_page", "")
        source_report = source.get("originating_report", LATEST_REPORT)
        query = {
            "query_id": query_id,
            "research_version_id": VERSION_ID,
            "lexical_form_id": form["lexical_form_id"],
            "concept_id": concept["concept_id"],
            "concept_label": concept["preferred_label"],
            "family_id": family["family_id"],
            "family_code": family["family_code"],
            "primary_layer_code": layer,
            "anchor_id": source["anchor_id"],
            "anchor_label": label,
            "strict_start_year": strict_start,
            "strict_end_year": strict_end,
            "contextual_start_year": contextual_start,
            "contextual_end_year": contextual_end,
            "surface_form": surface,
            "normalized_form": norm,
            "query_type": "EXACT_STRING" if len(norm.split()) == 1 else "EXACT_PHRASE",
            "query_classification": classification,
            "interpretation_class": interpretation,
            "ngram_compatibility_status": status,
            "ngram_execution_eligible": eligible,
            "ngram_compatibility_reason": reason,
            "case_policy": "CASE_INSENSITIVE_AGGREGATE",
            "hyphenation_policy": "Use attested spelling only; do not generate speculative variants.",
            "orthographic_policy": "Use report-visible form; variants require separate identified rules.",
            "ocr_policy": "No speculative OCR variants; add only after image-level confirmation.",
            "production_allowed": norm != "change",
            "ambiguity_risk": ambiguity,
            "precision_risk": precision,
            "recall_risk": recall,
            "retrieval_smoothing": 0,
            "expected_voice_code": source.get("voice_code", ""),
            "source_strata": source.get("source_id", "") or "Cross-corpus lexical baseline; passage-level source stratum unresolved.",
            "review_priority": "HIGH" if precision == "HIGH" or ambiguity == "HIGH" else "MEDIUM",
            "minimum_context": "Matching sentence plus preceding/following sentence and enclosing paragraph; preserve source, date, speaker, and quotation boundary.",
            "exclusions_note": exclusion or "No predefined term-specific exclusion; apply source, date, sense, voice, and context review.",
            "valid_match_pattern": "Exact report-visible surface string; semantic acceptance requires source-level review.",
            "invalid_match_pattern": exclusion or "Wrong referent, sense, date, voice, or insufficient context.",
            "reconstructed": True,
            "provenance_status": "RECONSTRUCTED_FROM_REPORT",
            "source_report": source_report,
            "source_page": source_page,
            "source_seed_candidate_id": source.get("seed_candidate_id", ""),
            "provenance_note": "New quantitative-v0.1 rule ID. The missing legacy query_rules.csv and its row identities have not been reconstructed or claimed.",
        }
        rules.append(query)
        if norm in EXCLUSIONS:
            for term in ("climate", "temperature", "heat", "warming", "weather", "atmosphere"):
                contexts.append({"query_id": query_id, "context_role": "OPTIONAL", "context_term": term})

        sense_key = (form["lexical_form_id"], concept["concept_id"], source["anchor_id"])
        if not any((s["lexical_form_id"], s["concept_id"], s["anchor_id"]) == sense_key for s in senses):
            senses.append({
                "lexical_form_sense_id": "FT-LFS-Q-" + hashlib.sha256("|".join(sense_key).encode("utf-8")).hexdigest()[:14].upper(),
                "lexical_form_id": form["lexical_form_id"],
                "concept_id": concept["concept_id"],
                "anchor_id": source["anchor_id"],
                "sense_label": f"Provisional {label} retrieval sense: {concept['preferred_label']}",
                "relation_type": "RELATED_NOT_EQUIVALENT" if interpretation != "CLIMATE_SPECIFIC" else "EXACT_VARIANT_OF",
                "provenance_note": "Query-linked provisional sense; a raw Ngram hit is not accepted semantic evidence.",
            })

    rule_fields = list(rules[0].keys())
    write_csv(SEED / "query_rules.csv", rules, rule_fields)
    write_csv(SEED / "lexical_forms_full.csv", all_forms, list(all_forms[0].keys()))
    write_csv(SEED / "lexical_form_senses_quantitative.csv", senses, list(senses[0].keys()))
    write_csv(SEED / "query_rule_context_terms.csv", contexts, ["query_id", "context_role", "context_term"])

    audit = [{
        "query_id": row["query_id"],
        "anchor": row["anchor_label"],
        "surface_form": row["surface_form"],
        "classification": row["query_classification"],
        "compatibility_status": row["ngram_compatibility_status"],
        "execution_eligible": row["ngram_execution_eligible"],
        "reason": row["ngram_compatibility_reason"],
        "interpretation_class": row["interpretation_class"],
        "source_report": row["source_report"],
        "source_page": row["source_page"],
        "provenance_status": row["provenance_status"],
    } for row in rules]
    write_csv(EXPORTS / "ngram_compatibility_audit.csv", audit, list(audit[0].keys()))

    new_forms = [row for row in all_forms if row["lexical_form_id"].startswith("FT-LF-Q-")]
    lines = ["BEGIN;", "SET search_path = fear_temperature, public;", ""]
    for row in new_forms:
        lines.append(
            "INSERT INTO lexical_form (lexical_form_id, surface_form, normalized_form, language_tag, ambiguity_class, is_high_value, provenance_note) VALUES ("
            + ", ".join([sql(row["lexical_form_id"]), sql(row["surface_form"]), sql(row["normalized_form"]), "'en'", sql(row["ambiguity_class"]), "false", sql(row["provenance_note"])])
            + ") ON CONFLICT DO NOTHING;"
        )
    lines.append("")
    for row in senses:
        lines.append(
            "INSERT INTO lexical_form_sense (lexical_form_sense_id, lexical_form_id, concept_id, anchor_id, sense_label, relation_type, provenance_note) VALUES ("
            + ", ".join(sql(row[key]) for key in ["lexical_form_sense_id", "lexical_form_id", "concept_id", "anchor_id", "sense_label", "relation_type", "provenance_note"])
            + ") ON CONFLICT DO NOTHING;"
        )
    lines.append("")
    sql_rule_fields = [
        "query_id", "research_version_id", "lexical_form_id", "concept_id", "family_id", "primary_layer_code", "anchor_id", "surface_form",
        "query_type", "query_classification", "interpretation_class", "ngram_compatibility_status", "ngram_execution_eligible", "ngram_compatibility_reason",
        "case_policy", "hyphenation_policy", "orthographic_policy", "ocr_policy", "production_allowed", "ambiguity_risk", "precision_risk", "recall_risk",
        "retrieval_smoothing", "expected_voice_code", "source_strata", "review_priority", "minimum_context", "exclusions_note", "valid_match_pattern",
        "invalid_match_pattern", "reconstructed", "provenance_status", "source_report", "source_page", "provenance_note",
    ]
    for row in rules:
        values = []
        for key in sql_rule_fields:
            value = row[key]
            if key in {"ngram_execution_eligible", "production_allowed", "reconstructed"}:
                values.append("true" if value else "false")
            elif key == "retrieval_smoothing":
                values.append(str(value))
            else:
                values.append(sql(value))
        lines.append(
            f"INSERT INTO query_rule ({', '.join(sql_rule_fields)}) VALUES ({', '.join(values)}) ON CONFLICT DO NOTHING;"
        )
    lines.append("")
    for row in contexts:
        lines.append(
            "INSERT INTO query_rule_context_term (query_id, context_role, context_term) VALUES ("
            + ", ".join(sql(row[key]) for key in ["query_id", "context_role", "context_term"])
            + ") ON CONFLICT DO NOTHING;"
        )
    lines.extend(["", "COMMIT;", ""])
    SQL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQL_PATH.write_text("\n".join(lines), encoding="utf-8")

    counts = Counter(row["query_classification"] for row in rules)
    compat_counts = Counter(row["ngram_compatibility_status"] for row in rules)
    print(f"query_rules={len(rules)} forms={len(all_forms)} new_forms={len(new_forms)} senses={len(senses)}")
    print("classifications", dict(counts))
    print("compatibility", dict(compat_counts))


if __name__ == "__main__":
    main()
