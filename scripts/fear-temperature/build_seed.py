#!/usr/bin/env python3
"""Reconstruct the provisional research seed from supplied narrative PDFs.

The compact PDF reports are treated as report evidence, never as missing original
structured artifacts. Every emitted seed row receives a new project ID and an
explicit RECONSTRUCTED_FROM_REPORT provenance status. Original candidate IDs are
retained only where they are visibly recoverable in the first seed report.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pdfplumber


ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "data" / "fear-temperature" / "seed"
EXPORT_DIR = ROOT / "data" / "fear-temperature" / "exports"
SQL_PATH = ROOT / "db" / "seeds" / "002_provisional_lexicon.sql"

VERSION_ID = "fear-temperature-quant-v0.1-provisional"
INITIAL_REPORT = ROOT / "Fear of Temperature_ Historical Lexical Discovery and Anchor Validation.pdf"
PRIORITY_REPORT = ROOT / "Fear of Temperature_ Stratified Lexical Expansion, Voice Mapping, and Semantic-Relational Pre-Valida.pdf"
LATEST_REPORT = "Fear of Temperature — Historical Semantic Validation, Cross-Voice Relational Modelling, and Retrieval-Specification Freeze"

ANCHOR_BY_PREFIX = {
    "1842": "FT-A1842",
    "1938": "FT-A1938",
    "1988": "FT-A1988",
    "0607": "FT-A0607",
    "2015": "FT-A2015",
    "2022": "FT-A2022",
}
ANCHOR_LABEL_BY_ID = {
    "FT-A1842": "1842",
    "FT-A1938": "1938",
    "FT-A1988": "1988",
    "FT-A0607": "2006–2007",
    "FT-A2015": "2015",
    "FT-A2022": "2022",
}

ANCHORS = [
    ("FT-A1842", "1842", "1842-01-01", "1842-12-31", "1839-01-01", "1845-12-31", "Meteorological/environmental and embodied-heat baseline."),
    ("FT-A1938", "1938", "1938-01-01", "1938-12-31", "1936-01-01", "1940-12-31", "CO₂–temperature causal-science bridge."),
    ("FT-A1988", "1988", "1988-01-01", "1988-12-31", "1986-01-01", "1990-12-31", "Institutional climate-risk and mediated-warning anchor."),
    ("FT-A0607", "2006–2007", "2006-01-01", "2007-12-31", "2005-01-01", "2008-12-31", "Public-communication and threat-framing bridge."),
    ("FT-A2015", "2015", "2015-01-01", "2015-12-31", "2014-01-01", "2016-12-31", "Temperature-threshold governance anchor."),
    ("FT-A2022", "2022", "2022-01-01", "2022-12-31", "2021-01-01", "2023-12-31", "Contemporary heat/risk/affect endpoint."),
]

LAYERS = [
    ("A", "Temperature / Physical Phenomenon"),
    ("B", "Climate / Atmospheric / Causal"),
    ("C", "Affect"),
    ("D", "Threat / Risk / Harm"),
]

VOICES = [
    ("V1", "Scientific / Research"),
    ("V2", "Institutional / Governance"),
    ("V3", "Mediated Public"),
    ("V4", "Organised Civic / Advocacy"),
    ("V5", "Direct Public / Lay"),
]

EXPRESSION_MODES = [
    ("E1", "Direct / Spontaneous"),
    ("E2", "Quoted / Mediated"),
    ("E3", "Elicited"),
    ("E4", "Researcher-Coded / Researcher-Labelled"),
    ("E5", "Not Applicable"),
]

FAMILIES = [
    ("FT-F01", "temperature_threshold", "Temperature / Threshold", "A"),
    ("FT-F02", "heat", "Heat", "A"),
    ("FT-F03", "warming", "Warming", "A"),
    ("FT-F04", "climate", "Climate", "B"),
    ("FT-F05", "carbon_greenhouse", "Carbon / Greenhouse", "B"),
    ("FT-F06", "concern_alarm", "Concern / Alarm", "C"),
    ("FT-F07", "worry", "Worry", "C"),
    ("FT-F08", "fear_afraid", "Fear / Afraid", "C"),
    ("FT-F09", "anxiety", "Anxiety", "C"),
    ("FT-F10", "distress_depression", "Distress / Depression", "C"),
    ("FT-F11", "danger_threat", "Danger / Threat", "D"),
    ("FT-F12", "risk", "Risk", "D"),
    ("FT-F13", "crisis_emergency", "Crisis / Emergency", "D"),
    ("FT-F14", "harm_loss_consequences", "Harm / Loss / Consequences", "D"),
]


def concept(family: str, code: str, label: str, definition: str, status: str = "PROVISIONAL_QUERYABLE") -> dict[str, str]:
    return {
        "concept_id": f"FT-C-{code.upper()}",
        "family_id": family,
        "concept_code": code,
        "preferred_label": label,
        "definition": definition,
        "provisional_status": status,
        "provenance_note": "Boundary explicitly retained by the latest semantic-validation report; provisional pending structured-seed reconciliation.",
    }


CONCEPTS = [
    concept("FT-F01", "local_instrumental_temperature", "local / instrumental temperature", "A local or instrument-specific temperature reading."),
    concept("FT-F01", "mean_temperature", "mean temperature", "A temporally or spatially averaged temperature value."),
    concept("FT-F01", "global_aggregate_temperature", "global aggregate temperature", "A global-scale aggregate temperature metric."),
    concept("FT-F01", "temperature_threshold_2c", "2°C threshold", "A governed two-degree temperature limit or threshold."),
    concept("FT-F01", "temperature_threshold_1_5c", "1.5°C threshold", "A governed one-and-a-half-degree temperature limit or threshold."),
    concept("FT-F02", "physical_heat_state", "physical heat source / state", "Heat as a physical source, state, or thermal condition."),
    concept("FT-F02", "embodied_heat_exposure", "embodied heat exposure", "Heat experienced by bodies in occupational, domestic, or environmental settings."),
    concept("FT-F02", "heatwave_weather_event", "heatwave / weather event", "A bounded hot-weather or heatwave event."),
    concept("FT-F02", "extreme_heat_hazard", "extreme-heat hazard", "Extreme heat framed as a hazard with health or social consequences."),
    concept("FT-F03", "temperature_increase", "temperature increase", "An observed, estimated, or projected increase in temperature."),
    concept("FT-F03", "climate_system_warming", "climate-system warming", "Warming attributed to or observed across the climate system."),
    concept("FT-F03", "global_warming_issue_label", "global warming as issue label", "Global warming used as an established public, scientific, or policy issue label."),
    concept("FT-F04", "historical_climate_condition", "historical climate / climatological condition", "Climate as a historical, geographical, seasonal, or climatological condition."),
    concept("FT-F04", "historical_climatic_change", "historical climatic change", "Historically attested climatic change or change-of-climate formulation."),
    concept("FT-F04", "modern_climate_change", "modern climate change", "Modern climate change as an anthropogenic scientific, public, or governance problem."),
    concept("FT-F04", "climate_system", "climate system", "The coupled physical climate system."),
    concept("FT-F04", "changing_atmosphere", "changing atmosphere", "Atmospheric change framed as a climatic or institutional problem."),
    concept("FT-F05", "atmospheric_carbon_dioxide", "atmospheric carbon dioxide", "Carbon dioxide as an atmospheric constituent."),
    concept("FT-F05", "anthropogenic_carbon_dioxide_production", "anthropogenic carbon-dioxide production", "Human production of carbon dioxide as a climatic cause."),
    concept("FT-F05", "greenhouse_mechanism", "greenhouse mechanism", "Radiative greenhouse mechanism or greenhouse effect."),
    concept("FT-F05", "anthropogenic_greenhouse_gas_emissions", "anthropogenic greenhouse-gas emissions", "Human-produced greenhouse-gas emissions in scientific or governance framing."),
    concept("FT-F06", "personal_concern", "personal concern", "Concern expressed or endorsed by an identifiable person about a climate or heat object."),
    concept("FT-F06", "institutional_evaluation", "institutional concern / evaluation", "Concern as institutional evaluation or stance, not necessarily personal affect."),
    concept("FT-F06", "common_concern_legal_formula", "common concern of humankind", "A legal-diplomatic formula identifying a shared governance object, not personal emotion."),
    concept("FT-F06", "public_alarm", "public alarm", "Alarm attributed to or anticipated for a public, requiring direct evidence and sense review."),
    concept("FT-F07", "prescribed_worry", "prescribed worry", "Worry explicitly prescribed to an audience by a communicator."),
    concept("FT-F07", "elicited_worry_category", "elicited worry category", "Worry wording supplied by a survey or other instrument."),
    concept("FT-F07", "participant_worry_endorsement", "participant worry endorsement", "A participant selection or endorsement of a supplied worry category."),
    concept("FT-F07", "spontaneous_worry", "spontaneous worry", "Worry wording independently generated by a public speaker or participant."),
    concept("FT-F08", "direct_fear", "direct fear", "Fear directly expressed by an identified experiencer toward a climate, heat, or consequence target."),
    concept("FT-F08", "participant_afraid_endorsement", "participant afraid endorsement", "Participant endorsement of a supplied afraid category."),
    concept("FT-F08", "research_instrument_fear_category", "research / instrument fear category", "Fear wording supplied by a researcher or instrument."),
    concept("FT-F09", "anxious_affect", "anxious affect", "Anxious feeling directly expressed or endorsed by a participant."),
    concept("FT-F09", "anxiety_symptom_measure", "anxiety symptom measure", "Anxiety operationalised as a symptom or health measure."),
    concept("FT-F09", "climate_anxiety_research_construct", "climate anxiety research construct", "Climate anxiety used as a researcher-defined construct."),
    concept("FT-F09", "eco_anxiety_research_construct", "eco-anxiety research construct", "Eco-anxiety used as a researcher-defined construct."),
    concept("FT-F09", "participant_climate_anxiety_self_label", "participant climate-anxiety self-label", "Participant-generated use of the climate-anxiety compound where independently evidenced.", "UNRESOLVED"),
    concept("FT-F10", "historical_depressing_effect", "historical depressing effect", "Historical bodily or energetic depressing effect; false friend with modern clinical depression."),
    concept("FT-F10", "psychological_distress", "psychological distress", "Modern psychological distress as a research, health, or participant category."),
    concept("FT-F10", "depressed_affect", "depressed affect", "Depressed affect directly expressed or instrument-endorsed in a climate context."),
    concept("FT-F11", "hazard_evaluation", "hazard evaluation", "Danger or threat evaluation of a specified hazard."),
    concept("FT-F11", "institutional_climate_threat", "institutional climate threat", "Climate change framed as an institutional threat."),
    concept("FT-F11", "personal_community_threat_appraisal", "personal / community threat appraisal", "Threat appraised for a person or community, including elicited appraisal."),
    concept("FT-F11", "global_security_frame", "global security frame", "Atmospheric or climatic change framed as a global-security matter."),
    concept("FT-F12", "probabilistic_risk", "probabilistic risk", "Risk expressed probabilistically for a specified outcome."),
    concept("FT-F12", "economic_climate_risk", "economic climate risk", "Economic cost or risk attributed to climate change."),
    concept("FT-F12", "administrative_risk_assessment", "administrative risk assessment", "Risk managed or assessed through institutional procedure."),
    concept("FT-F12", "loss_damage_risk", "loss-and-damage risk", "Risk associated with climate loss and damage."),
    concept("FT-F12", "personal_perceived_risk", "personal perceived risk", "Individual or community perception of climate or heat risk."),
    concept("FT-F13", "severity_crisis_predicate", "severity / crisis predicate", "Crisis used as a severity predicate without necessarily being an established issue label."),
    concept("FT-F13", "climate_crisis_issue_label", "climate crisis issue label", "Climate crisis used as an established issue label."),
    concept("FT-F13", "emergency_response_category", "emergency response category", "Emergency preparedness or response as a governance procedure."),
    concept("FT-F13", "climate_emergency_declaration", "climate emergency frame / declaration", "Climate emergency used as a public, civic, or institutional frame or declaration."),
    concept("FT-F14", "bodily_harm", "bodily harm", "Heat- or climate-related bodily harm or illness."),
    concept("FT-F14", "mortality", "mortality", "Death or mortality attributed to heat or climate consequences."),
    concept("FT-F14", "generic_damage", "generic damage", "Generic material, ecological, or social damage."),
    concept("FT-F14", "loss_and_damage", "loss and damage", "The climate-governance domain of loss and damage."),
    concept("FT-F14", "non_economic_losses", "non-economic losses", "Non-economic loss as a distinct governance category."),
    concept("FT-F14", "vulnerability", "vulnerability", "Susceptibility of an identified subject or group to harm."),
    concept("FT-F14", "future_generation_harm", "future-generation harm", "Harm or loss explicitly attributed to future generations."),
]

CONCEPT_BY_CODE = {row["concept_code"]: row["concept_id"] for row in CONCEPTS}


def form(code: str, surface: str, concept_code: str, ambiguity: str, high_value: bool = True) -> dict[str, Any]:
    return {
        "lexical_form_id": f"FT-LF-{code.upper()}",
        "surface_form": surface,
        "normalized_form": normalize_form(surface),
        "concept_id": CONCEPT_BY_CODE[concept_code],
        "ambiguity_class": ambiguity,
        "is_high_value": high_value,
        "provenance_note": "High-value provisional form supported by the semantic-validation contract.",
    }


def normalize_form(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", value).strip()


FORMS = [
    form("TEMPERATURE", "temperature", "local_instrumental_temperature", "BACKGROUND_OR_AMBIGUOUS"),
    form("MEAN_TEMPERATURE", "mean temperature", "mean_temperature", "CONTEXT_REQUIRED"),
    form("GLOBAL_AVERAGE_TEMPERATURE", "global average temperature", "global_aggregate_temperature", "CLIMATE_SPECIFIC"),
    form("2C", "2°C", "temperature_threshold_2c", "CONTEXT_REQUIRED"),
    form("1_5C", "1.5°C", "temperature_threshold_1_5c", "CONTEXT_REQUIRED"),
    form("HEAT", "heat", "physical_heat_state", "BACKGROUND_OR_AMBIGUOUS"),
    form("HEAT_WAVE", "heat wave", "heatwave_weather_event", "CLIMATE_SPECIFIC"),
    form("EXTREME_HEAT", "extreme heat", "extreme_heat_hazard", "CLIMATE_SPECIFIC"),
    form("TEMPERATURE_INCREASE", "temperature increase", "temperature_increase", "CLIMATE_SPECIFIC"),
    form("WARMING", "warming", "climate_system_warming", "BACKGROUND_OR_AMBIGUOUS"),
    form("GLOBAL_WARMING", "global warming", "global_warming_issue_label", "CLIMATE_SPECIFIC"),
    form("CLIMATIC_CHANGE", "climatic change", "historical_climatic_change", "CLIMATE_SPECIFIC"),
    form("CLIMATE_CHANGE", "climate change", "modern_climate_change", "CLIMATE_SPECIFIC"),
    form("CLIMATE", "climate", "historical_climate_condition", "BACKGROUND_OR_AMBIGUOUS"),
    form("CLIMATE_SYSTEM", "climate system", "climate_system", "CLIMATE_SPECIFIC"),
    form("CHANGING_ATMOSPHERE", "changing atmosphere", "changing_atmosphere", "CLIMATE_SPECIFIC"),
    form("GREENHOUSE_EFFECT", "greenhouse effect", "greenhouse_mechanism", "CLIMATE_SPECIFIC"),
    form("CONCERN", "concern", "personal_concern", "BACKGROUND_OR_AMBIGUOUS"),
    form("COMMON_CONCERN", "common concern of humankind", "common_concern_legal_formula", "CLIMATE_SPECIFIC"),
    form("ALARM", "alarm", "public_alarm", "BACKGROUND_OR_AMBIGUOUS"),
    form("WORRY", "worry", "spontaneous_worry", "BACKGROUND_OR_AMBIGUOUS"),
    form("WORRIED", "worried", "spontaneous_worry", "BACKGROUND_OR_AMBIGUOUS"),
    form("BE_WORRIED", "Be Worried. Be Very Worried.", "prescribed_worry", "CLIMATE_SPECIFIC"),
    form("PERSONALLY_WORRY", "personally worry", "elicited_worry_category", "CONTEXT_REQUIRED"),
    form("VERY_WORRIED", "very worried", "participant_worry_endorsement", "CONTEXT_REQUIRED"),
    form("FEAR", "fear", "direct_fear", "BACKGROUND_OR_AMBIGUOUS"),
    form("AFRAID", "afraid", "participant_afraid_endorsement", "BACKGROUND_OR_AMBIGUOUS"),
    form("ANXIETY", "anxiety", "anxious_affect", "BACKGROUND_OR_AMBIGUOUS"),
    form("CLIMATE_ANXIETY", "climate anxiety", "climate_anxiety_research_construct", "CLIMATE_SPECIFIC"),
    form("ECO_ANXIETY", "eco-anxiety", "eco_anxiety_research_construct", "CLIMATE_SPECIFIC"),
    form("DISTRESS", "distress", "psychological_distress", "BACKGROUND_OR_AMBIGUOUS"),
    form("DEPRESSION", "depression", "depressed_affect", "BACKGROUND_OR_AMBIGUOUS"),
    form("DEPRESSING_EFFECT", "depressing effect", "historical_depressing_effect", "CONTEXT_REQUIRED"),
    form("DANGER", "danger", "hazard_evaluation", "BACKGROUND_OR_AMBIGUOUS"),
    form("THREAT", "threat", "institutional_climate_threat", "BACKGROUND_OR_AMBIGUOUS"),
    form("GLOBAL_SECURITY", "global security", "global_security_frame", "CONTEXT_REQUIRED"),
    form("RISK", "risk", "probabilistic_risk", "BACKGROUND_OR_AMBIGUOUS"),
    form("CRISIS", "crisis", "severity_crisis_predicate", "BACKGROUND_OR_AMBIGUOUS"),
    form("CLIMATE_CRISIS", "climate crisis", "climate_crisis_issue_label", "CLIMATE_SPECIFIC"),
    form("EMERGENCY", "emergency", "emergency_response_category", "BACKGROUND_OR_AMBIGUOUS"),
    form("CLIMATE_EMERGENCY", "climate emergency", "climate_emergency_declaration", "CLIMATE_SPECIFIC"),
    form("LOSS_AND_DAMAGE", "loss and damage", "loss_and_damage", "CLIMATE_SPECIFIC"),
    form("NON_ECONOMIC_LOSSES", "non-economic losses", "non_economic_losses", "CLIMATE_SPECIFIC"),
    form("CHANGE", "change", "historical_climatic_change", "PROHIBITED_STANDALONE"),
]


EXPANSIONS = {
    "FT-A1842": [
        ("the heat is remarkable", "A"), ("92° in the shade", "A"),
        ("80 yesterday in the shade", "A"), ("very depressing effect on the energies", "C"),
        ("fatal", "D"), ("mortality", "D"),
    ],
    "FT-A1938": [
        ("blinding sun", "D"), ("choking death from thirst and starvation", "D"),
        ("birds dropped dead", "D"), ("thermometers burst", "A"),
        ("heat-related illness", "D"), ("warming trend", "A"),
    ],
    "FT-A1988": [
        ("enemy is invisible but deadly", "D"), ("traps heat from the sun", "B"),
        ("global nuclear war", "D"), ("high degree of confidence", "C"),
        ("probability of occurrence", "D"), ("more frequent", "A"),
    ],
    "FT-A0607": [
        ("effects already begun", "D"), ("human activities", "B"),
        ("media underestimates problem", "C"), ("very serious concern", "C"),
        ("religious duty", "C"), ("serious challenge of global climate change", "D"),
    ],
    "FT-A2015": [
        ("severe weather", "D"), ("long periods of unusually hot weather", "A"),
        ("red line", "D"), ("at risk from climate change", "D"),
        ("for the planet", "D"), ("future generations", "D"),
    ],
    "FT-A2022": [
        ("climate worry", "C"), ("chronic uncertainty", "C"),
        ("isolation", "C"), ("climate emergency", "D"),
        ("chronic fear of environmental doom", "C"), ("fear of a degraded Earth", "C"),
    ],
}


SEMANTIC_RULES = [
    ("FT-SR-1842-DEPRESSING", "FT-A1842", "depressing effect", "V5", "E3", "AFFECT_ADJACENT", "NO_THREAT", "ACCEPT_WITH_QUALIFICATION", "Embodied/bodily energetic sense; FALSE_FRIEND with modern clinical depression."),
    ("FT-SR-1938-COINCIDENCE", "FT-A1938", "rather a coincidence", "V1", "E2", "NO_AFFECT", "NO_THREAT", "ACCEPT_WITH_QUALIFICATION", "Epistemic evaluation; normally no affect; inspect the original discussion turn before stronger coding."),
    ("FT-SR-1988-SECURITY", "FT-A1988", "global security", "V2", "E1", "NO_AFFECT", "THREAT_WITHOUT_AFFECT", "ACCEPT", "Institutional threat/security frame; threat is not evidence of fear."),
    ("FT-SR-2006-WORRIED", "FT-A0607", "Be Worried. Be Very Worried.", "V3", "E1", "AFFECT_PRESCRIPTION", "THREAT_WITH_AFFECT", "ACCEPT", "Media imperative prescribing affect to readers; it does not establish reader emotion."),
    ("FT-SR-2007-PERSONALLY-WORRY", "FT-A0607", "personally worry", "V5", "E3", "EXPLICIT_AFFECT", "UNRESOLVED", "ACCEPT_WITH_QUALIFICATION", "Instrument wording and participant endorsement must be separate; participant response is elicited, not spontaneous vocabulary."),
    ("FT-SR-2015-COMMON-CONCERN", "FT-A2015", "common concern of humankind", "V2", "E1", "NO_AFFECT", "THREAT_WITHOUT_AFFECT", "ACCEPT", "Legal/institutional formula; never personal concern or emotion."),
    ("FT-SR-2022-CLIMATE-ANXIETY", "FT-A2022", "climate anxiety", "V1", "E4", "RESEARCH_CONSTRUCT", "NO_THREAT", "ACCEPT_WITH_QUALIFICATION", "Research construct unless an underlying passage independently proves participant self-use."),
    ("FT-SR-2022-VERY-WORRIED", "FT-A2022", "very worried", "V5", "E3", "EXPLICIT_AFFECT", "UNRESOLVED", "ACCEPT_WITH_QUALIFICATION", "Participant endorsement when tied to a response; wording remains instrument-supplied."),
]


EXCLUSION_RULES = [
    ("temperature", "REQUIRE_CONTEXT", "atmosphere; environment; measurement; global aggregate; governance threshold", "body/fever; cooking; unrelated industrial temperature", "Require the measured object or environmental/climate referent."),
    ("heat", "EXCLUDE_DOMAIN", "environmental heat; occupational heat; sun heat; heatwave", "cooking; oven; machinery; process heat; political metaphor", "Require environmental, weather, occupational, or bodily-exposure context."),
    ("climate", "EXCLUDE_DOMAIN", "climatology; climate system; climate change", "business climate; political climate; social climate; school climate", "Require a physical/environmental or historically reviewed climatological sense."),
    ("warming", "EXCLUDE_DOMAIN", "temperature increase; climate-system warming", "warming food; warming rooms; interpersonal metaphor", "Require the warmed object or a climate/temperature referent."),
    ("concern", "REQUIRE_PROVENANCE_SPLIT", "personal concern; institutional evaluation; legal formula", "business concern; matter/enterprise concern; unspecified concern", "Store speaker, object, and discourse function; legal formula is not personal affect."),
    ("alarm", "EXCLUDE_DOMAIN", "public alarm about heat/climate; attributed reaction", "alarm clock; device; unrelated warning system", "Require an attributed public/actor reaction or climate/heat object."),
    ("fear", "REQUIRE_PROVENANCE_SPLIT", "identified experiencer fears climate/heat/consequence", "unrelated fear; fearmongering accusation; rhetorical mention", "Require experiencer, target, and quotation boundary."),
    ("worry", "REQUIRE_PROVENANCE_SPLIT", "media imperative; instrument wording; participant endorsement; spontaneous worry", "unrelated worry; negated worry", "Record who produced the wording; never infer E1 from E3."),
    ("anxiety", "REQUIRE_PROVENANCE_SPLIT", "climate-linked affect; symptom measure; named construct", "unrelated clinical anxiety; researcher label treated as participant wording", "Require construct, instrument, or participant provenance and a climate target."),
    ("distress", "EXCLUDE_DOMAIN", "climate/heat psychological or bodily distress", "financial distress; distress signal; unrelated clinical context", "Require climate/heat target and affect/health sense."),
    ("depression", "FALSE_FRIEND", "explicit climate-related depressed affect", "economic depression; topographic depression; meteorological depression; unrelated clinical depression", "Mandatory anti-presentist sense check; 1842 depressing effect is not modern depression."),
    ("danger", "REQUIRE_CONTEXT", "climate; carbon dioxide; heat danger", "unrelated danger", "Require danger object and threatened subject."),
    ("threat", "EXCLUDE_DOMAIN", "explicit climate/heat threat", "military; cyber; unrelated political threat", "Require threat object and affected subject; do not infer affect."),
    ("risk", "EXCLUDE_DOMAIN", "climate/heat risk with specified outcome", "investment; credit; surgery; unrelated insurance", "Store domain and outcome; risk is not emotion."),
    ("crisis", "REQUIRE_CONTEXT", "climate crisis; explicitly climate-linked crisis", "generic economic; political; health crisis", "Require an explicit climate referent or enclosing governance section."),
    ("emergency", "REQUIRE_CONTEXT", "climate emergency; climate-context emergency preparedness", "medical emergency; unrelated emergency services", "Separate issue label/declaration from response category."),
    ("change", "PROHIBIT_STANDALONE", "climate change; climatic change; historically validated change of climate", "standalone change", "Standalone change must never become a production query."),
]


VOICE_MATRIX = [
    ("FT-A1842", "V1", "STRONG", "wet bulb temperature; mean temperature; meteorological observations", "Royal Society Colaba and Ross observation records; measurement-centred."),
    ("FT-A1842", "V2", "THIN_CONTEXTUAL", "changes of temperature; sickness and mortality", "Institutional inquiry context is present, but substantive worker testimony remains V5."),
    ("FT-A1842", "V3", "THIN_CONTEXTUAL", "alarm to the public", "Possible/negated public-health formulation; not proof that a public reported alarm."),
    ("FT-A1842", "V4", "NOT_LOCATED", "", "No defensible organised-civic stratum located; cell intentionally unfilled."),
    ("FT-A1842", "V5", "ATTESTED", "heat of the irons; most suffocating; faint away; depressing effect", "Worker testimony and correspondence show embodied heat experience, not climate fear."),
    ("FT-A1938", "V1", "STRONG", "artificial production of carbon dioxide; mean temperature; radiation absorption", "Callendar causal-science configuration."),
    ("FT-A1938", "V2", "THIN_CONTEXTUAL", "meteorological stations", "Official/institutional material is secondary to the scientific anchor."),
    ("FT-A1938", "V3", "ATTESTED", "heat wave; scorching westerly wind; pitiless sun; unbearable heat", "Heat-event journalism, partly from secondary reproduction; not reception of Callendar."),
    ("FT-A1938", "V4", "NOT_LOCATED", "", "No defensible organised-civic stratum located; cell intentionally unfilled."),
    ("FT-A1938", "V5", "NOT_LOCATED", "", "No strong exact-year lay reception of Callendar located."),
    ("FT-A1988", "V1", "STRONG", "greenhouse effect; global warming; global temperature; regional heat waves", "Hansen scientific work/testimony."),
    ("FT-A1988", "V2", "STRONG", "global security; major threat; impending crisis; harmful consequences", "Toronto institutional threat/security framing."),
    ("FT-A1988", "V3", "ATTESTED", "Global Warming Has Begun; too much carbon dioxide is dangerous", "Public-facing journalism; does not substitute for V5 evidence."),
    ("FT-A1988", "V4", "THIN_NOT_ALLOCATED", "", "No strong exact-year V4 passage allocation in the current pilot plan."),
    ("FT-A1988", "V5", "NOT_LOCATED", "", "Exact-year direct-public fear/worry/anxiety evidence remains weak/not located."),
    ("FT-A0607", "V1", "STRONG", "warming of the climate system; unequivocal; temperature increase", "IPCC scientific assessment language."),
    ("FT-A0607", "V2", "STRONG", "serious global threat; costs and risks; damage", "Stern and institutional risk/governance framing."),
    ("FT-A0607", "V3", "ATTESTED", "Be Worried. Be Very Worried.; global warming", "Media-prescribed affect; not evidence readers felt worried."),
    ("FT-A0607", "V4", "ATTESTED", "dangerous climate change; serious negative effects", "Organised civic/advocacy framing."),
    ("FT-A0607", "V5", "ATTESTED_ELICITED", "personally worry; worry a great deal; urgent threat", "Survey/instrument evidence; participant endorsement is E3."),
    ("FT-A2015", "V1", "THIN_CONTEXTUAL", "global average temperature; climate change", "Scientific context supports governance thresholds but is not the dominant documentary voice."),
    ("FT-A2015", "V2", "STRONG", "well below 2°C; 1.5°C; common concern of humankind; loss and damage", "Paris legal/governance language; common concern is not personal affect."),
    ("FT-A2015", "V3", "ATTESTED", "extreme heat; climate change", "Public-facing circulation exists but is not the anchor's strongest evidence stratum."),
    ("FT-A2015", "V4", "ATTESTED", "climate justice; red line; We are nature defending itself", "COP21 mobilisation and protest."),
    ("FT-A2015", "V5", "ATTESTED_ELICITED", "very worried; serious problem; harm them personally", "Survey-elicited public appraisal."),
    ("FT-A2022", "V1", "STRONG", "climate anxiety; eco-anxiety; anxiety and stress; heat-related mortality", "Research constructs and assessment categories; not automatically participant self-labelling."),
    ("FT-A2022", "V2", "ATTESTED", "climate-related risk; heatwaves; mental-health challenges", "Institutional/assessment framing remains distinct from individual affect."),
    ("FT-A2022", "V3", "ATTESTED", "extreme heat; climate emergency", "Public-facing media framing requires source-specific verification."),
    ("FT-A2022", "V4", "ATTESTED", "climate crisis; climate emergency", "Advocacy/threat framing; crisis is not itself affect."),
    ("FT-A2022", "V5", "STRONG_ELICITED", "very worried; afraid; anxious; hopeless", "Dense survey-elicited endorsement; instrument wording and participant-generated wording remain separate."),
]


PILOT_PLAN = [
    ("FT-A1842", 30, 12, 3, 3, 0, 12),
    ("FT-A1938", 28, 16, 2, 10, 0, 0),
    ("FT-A1988", 30, 12, 12, 6, 0, 0),
    ("FT-A0607", 36, 7, 7, 6, 4, 12),
    ("FT-A2015", 38, 4, 14, 5, 6, 9),
    ("FT-A2022", 38, 10, 6, 4, 4, 14),
]


def words_in_bbox(page: Any, bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    x0, top, x1, bottom = bbox
    return [
        word for word in page.extract_words(use_text_flow=False, x_tolerance=1, y_tolerance=2)
        if x0 - 1 <= word["x0"] <= x1 + 1 and top - 1 <= word["top"] <= bottom + 1
    ]


def tokens_for_band(words: Iterable[dict[str, Any]], x0: float, x1: float, top: float, bottom: float) -> str:
    selected = [word for word in words if x0 <= word["x0"] < x1 and top <= word["top"] < bottom]
    selected.sort(key=lambda word: (round(word["top"], 1), word["x0"]))
    return " ".join(word["text"] for word in selected).strip()


def extract_initial_candidates() -> list[dict[str, Any]]:
    candidate_re = re.compile(r"^(1842|1938|1988|0607|2015|2022)-[ABCD]-\d{2}$")
    split_prefix_re = re.compile(r"^(1842|1938|1988|0607|2015|2022)-$")
    split_suffix_re = re.compile(r"^[ABCD]-\d{2}$")
    rows: list[dict[str, Any]] = []
    with pdfplumber.open(INITIAL_REPORT) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            for table in page.find_tables():
                words = words_in_bbox(page, table.bbox)
                ids = [word for word in words if candidate_re.match(word["text"])]
                for prefix_word in [word for word in words if split_prefix_re.match(word["text"])]:
                    suffix = next((
                        word for word in words
                        if split_suffix_re.match(word["text"])
                        and abs(word["x0"] - prefix_word["x0"]) <= 2
                        and 0 < word["top"] - prefix_word["top"] <= 25
                    ), None)
                    if suffix:
                        ids.append({
                            **suffix,
                            "text": prefix_word["text"] + suffix["text"],
                            "top": (prefix_word["top"] + suffix["top"]) / 2,
                        })
                if not ids:
                    continue
                candidate_headers = sorted(
                    [word for word in words if word["text"] == "Candidate"],
                    key=lambda word: word["x0"],
                )
                layer_headers = [word for word in words if word["text"] == "Layer"]
                term_x0 = candidate_headers[1]["x0"] if len(candidate_headers) >= 2 else 189
                term_x1 = min(word["x0"] for word in layer_headers) - 1 if layer_headers else 261
                ids.sort(key=lambda word: word["top"])
                for index, id_word in enumerate(ids):
                    previous_top = ids[index - 1]["top"] if index else table.bbox[1]
                    next_top = ids[index + 1]["top"] if index + 1 < len(ids) else table.bbox[3]
                    band_top = (previous_top + id_word["top"]) / 2 if index else table.bbox[1]
                    band_bottom = (id_word["top"] + next_top) / 2 if index + 1 < len(ids) else table.bbox[3]
                    original_id = id_word["text"]
                    prefix = original_id.split("-", 1)[0]
                    surface = tokens_for_band(words, term_x0 - 1, term_x1, band_top, band_bottom)
                    surface = re.sub(r"^Candidate\s+term\s+", "", surface)
                    confidence_text = tokens_for_band(words, 790, 845, band_top, band_bottom)
                    carry_text = tokens_for_band(words, 845, 930, band_top, band_bottom)
                    confidence = next((v for v in ("Strong", "Moderate", "Weak") if v in confidence_text), "NOT_EXPOSED")
                    carry = next((v for v in ("Conditional", "Yes", "No") if v in carry_text), "NOT_EXPOSED")
                    reconciliation = {"Yes": "RETAIN", "No": "EXCLUDE", "Conditional": "UNRESOLVED"}.get(carry, "UNRESOLVED")
                    rows.append({
                        "seed_candidate_id": f"FT-SEED-R1-{original_id}",
                        "originating_seed_stage": "INITIAL_180",
                        "original_candidate_id": original_id,
                        "source_page": str(page_number),
                        "anchor_id": ANCHOR_BY_PREFIX[prefix],
                        "surface_form": re.sub(r"\s+", " ", surface).strip(),
                        "layer_code": original_id.split("-")[1],
                        "voice_code": "",
                        "source_id": "",
                        "original_decision": f"CONFIDENCE={confidence};CARRY_FORWARD={carry}",
                        "reconciliation_status": reconciliation,
                        "originating_report": INITIAL_REPORT.name,
                        "provenance_note": "Original candidate ID and row fields reconstructed from the compact narrative PDF table; this is not the missing original structured record.",
                    })
    return rows


def normalize_table_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s*·\s*", " · ", value)
    value = re.sub(r"([A-D])/\s+(V[1-5])", r"\1/\2", value)
    value = re.sub(r"-\s+", "-", value)
    return value.strip()


def extract_priority_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with pdfplumber.open(PRIORITY_REPORT) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            for table in page.find_tables():
                words = words_in_bbox(page, table.bbox)
                if sum(word["text"] == "Candidate" for word in words) < 3 or sum(word["text"] == "Rank" for word in words) < 3:
                    continue
                rank_headers = sorted({round(word["x0"], 1) for word in words if word["text"] == "Rank"})
                candidate_headers = sorted({round(word["x0"], 1) for word in words if word["text"] == "Candidate"})
                if len(rank_headers) != 3 or len(candidate_headers) != 3:
                    raise ValueError(f"Unexpected priority-table header geometry on page {page_number}")
                column_specs = [
                    (rank_headers[index], candidate_headers[index], rank_headers[index + 1] - 2 if index < 2 else table.bbox[2] + 1)
                    for index in range(3)
                ]
                for rank_x, candidate_x, candidate_end in column_specs:
                    rank_words = [
                        word for word in words
                        if word["text"].isdigit() and 1 <= int(word["text"]) <= 30 and abs(word["x0"] - rank_x) <= 8
                    ]
                    rank_words.sort(key=lambda word: word["top"])
                    for index, rank_word in enumerate(rank_words):
                        if index:
                            band_top = (rank_words[index - 1]["top"] + rank_word["top"]) / 2
                        else:
                            next_gap = rank_words[index + 1]["top"] - rank_word["top"] if len(rank_words) > 1 else 50
                            band_top = rank_word["top"] - next_gap / 2
                        if index + 1 < len(rank_words):
                            band_bottom = (rank_word["top"] + rank_words[index + 1]["top"]) / 2
                        else:
                            previous_gap = rank_word["top"] - rank_words[index - 1]["top"] if index else 50
                            band_bottom = rank_word["top"] + previous_gap / 2
                        cell_text = normalize_table_text(tokens_for_band(words, candidate_x - 2, candidate_end, band_top, band_bottom))
                        parts = [part.strip() for part in cell_text.split(" · ")]
                        if len(parts) < 3:
                            raise ValueError(f"Could not parse priority cell on page {page_number}: {cell_text!r}")
                        surface, layer_voice, source_id = parts[0], parts[1], parts[2]
                        match = re.fullmatch(r"([A-D])/(V[1-5])", layer_voice)
                        if not match:
                            raise ValueError(
                                f"Could not parse layer/voice on page {page_number}, rank {rank_word['text']}, "
                                f"column {candidate_x}: {layer_voice!r}; cell={cell_text!r}; parts={parts!r}"
                            )
                        source_id = source_id.replace(" ", "")
                        anchor_prefix_match = re.match(r"S(1842|1938|1988|0607|2015|2022)", source_id)
                        if not anchor_prefix_match:
                            raise ValueError(f"Could not infer anchor from source {source_id!r}")
                        anchor_id = ANCHOR_BY_PREFIX[anchor_prefix_match.group(1)]
                        rank = int(rank_word["text"])
                        rows.append({
                            "seed_candidate_id": f"FT-SEED-R1B-P-{anchor_id.removeprefix('FT-A')}-{rank:02d}",
                            "originating_seed_stage": "PRIORITY_180",
                            "original_candidate_id": "",
                            "source_page": str(page_number),
                            "anchor_id": anchor_id,
                            "surface_form": surface,
                            "layer_code": match.group(1),
                            "voice_code": match.group(2),
                            "source_id": source_id,
                            "original_decision": f"PRIORITY_RANK={rank};ORIGINAL_ROW_CONFIDENCE_NOT_EXPOSED",
                            "reconciliation_status": "UNRESOLVED",
                            "originating_report": PRIORITY_REPORT.name,
                            "provenance_note": "New surrogate project ID assigned from the compact report table; never an original later-stage structured candidate ID.",
                        })
    return rows


def build_expansion_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    report_pages = {"FT-A1842": "7", "FT-A1938": "8", "FT-A1988": "9", "FT-A0607": "10", "FT-A2015": "12", "FT-A2022": "13"}
    for anchor_id, values in EXPANSIONS.items():
        for index, (surface, layer) in enumerate(values, 1):
            rows.append({
                "seed_candidate_id": f"FT-SEED-R1B-X-{anchor_id.removeprefix('FT-A')}-{index:02d}",
                "originating_seed_stage": "EXPANSION_36",
                "original_candidate_id": "",
                "source_page": report_pages[anchor_id],
                "anchor_id": anchor_id,
                "surface_form": surface,
                "layer_code": layer,
                "voice_code": "",
                "source_id": "",
                "original_decision": f"EXPANSION_ORDER={index};ORIGINAL_ROW_METADATA_NOT_EXPOSED",
                "reconciliation_status": "UNRESOLVED",
                "originating_report": PRIORITY_REPORT.name,
                "provenance_note": "New surrogate project ID assigned from the report's narrative Expansion list; original structured row identity and per-row voice/source metadata were unavailable.",
            })
    return rows


def infer_source_genre(source_id: str, voice_code: str) -> str:
    if any(token in source_id for token in ("GALLUP", "YALE", "PEW")):
        return "SURVEY"
    if any(token in source_id for token in ("CHADWICK", "PARIS", "TORONTO", "STERN", "NOBEL")):
        return "INSTITUTIONAL"
    if any(token in source_id for token in ("TIME", "TIMES", "NYT", "COURIER", "TORCH", "EVENING", "WIRED")):
        return "MEDIA"
    if any(token in source_id for token in ("COPPROTEST", "CCNI", "XR")):
        return "CIVIC"
    return {"V1": "SCIENTIFIC", "V2": "INSTITUTIONAL", "V3": "MEDIA", "V4": "CIVIC", "V5": "DIRECT_PUBLIC"}[voice_code]


SOURCE_NAMES = {
    "S1842-CHADWICK": "Chadwick sanitary inquiry and embedded testimony",
    "S1938-CALLENDAR": "Callendar 1938 scientific article",
    "S1988-HANSEN": "Hansen 1988 scientific work/testimony",
    "S1988-TORONTO": "Toronto Conference on the Changing Atmosphere",
    "S0607-TIME": "TIME, Be Worried. Be Very Worried.",
    "S0607-GALLUP": "Gallup environmental worry survey material",
    "S2015-PARIS": "Paris Agreement",
    "S2022-IPCC": "IPCC Working Group II assessment",
    "S2022-NATURE": "Nature Climate Change climate-anxiety article",
    "S2022-REHLING": "Rehling eco-anxiety qualitative study",
}


def source_rows(priority_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_source: dict[str, dict[str, str]] = {}
    for row in priority_rows:
        source_id = row["source_id"]
        by_source.setdefault(source_id, {
            "source_id": source_id,
            "source_genre_code": infer_source_genre(source_id, row["voice_code"]),
            "canonical_name": SOURCE_NAMES.get(source_id, source_id),
            "provenance_status": "RECONSTRUCTED_FROM_REPORT",
            "provenance_note": "Compact later-stage report source identifier; complete standalone source registry was unavailable.",
        })
    return sorted(by_source.values(), key=lambda row: row["source_id"])


def augment_candidate_metadata(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose report-supported metadata fields without inventing absent values."""
    semantic_modes = {
        (anchor_id, normalize_form(surface)): expression_mode
        for _, anchor_id, surface, _, expression_mode, *_ in SEMANTIC_RULES
    }
    augmented = []
    for row in rows:
        decision = row.get("original_decision", "")
        confidence_match = re.search(r"CONFIDENCE=([^;]+)", decision)
        if confidence_match:
            confidence = confidence_match.group(1)
        elif "ORIGINAL_ROW_CONFIDENCE_NOT_EXPOSED" in decision:
            confidence = "NOT_EXPOSED"
        else:
            confidence = "NOT_EXPOSED"
        if row["originating_seed_stage"] == "INITIAL_180":
            relevance_match = re.search(r"CARRY_FORWARD=([^;]+)", decision)
            relevance = relevance_match.group(1) if relevance_match else "NOT_EXPOSED"
        elif row["originating_seed_stage"] == "PRIORITY_180":
            rank_match = re.search(r"PRIORITY_RANK=(\d+)", decision)
            relevance = f"PRIORITY_RANK_{int(rank_match.group(1)):02d}" if rank_match else "PRIORITY"
        else:
            order_match = re.search(r"EXPANSION_ORDER=(\d+)", decision)
            relevance = f"EXPANSION_ORDER_{int(order_match.group(1)):02d}" if order_match else "EXPANSION"
        augmented.append({
            **row,
            "expression_mode_code": semantic_modes.get(
                (row["anchor_id"], normalize_form(row["surface_form"])), ""
            ),
            "confidence_label": confidence,
            "relevance_label": relevance,
            "reconstruction_status": "RECONSTRUCTED_FROM_REPORT",
        })
    return augmented


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sql_literal(value: Any) -> str:
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    return "'" + str(value).replace("'", "''") + "'"


def sql_insert(table: str, columns: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    values = ["(" + ", ".join(sql_literal(row.get(column)) for column in columns) + ")" for row in rows]
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n" + ",\n".join(values) + "\nON CONFLICT DO NOTHING;\n"


def build_sql(concepts: list[dict[str, Any]], forms: list[dict[str, Any]], sources: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> None:
    sense_rows = [{
        "lexical_form_sense_id": form_row["lexical_form_id"].replace("FT-LF-", "FT-LFS-"),
        "lexical_form_id": form_row["lexical_form_id"],
        "concept_id": form_row["concept_id"],
        "anchor_id": None,
        "sense_label": next(c["preferred_label"] for c in concepts if c["concept_id"] == form_row["concept_id"]),
        "relation_type": "PREFERRED_LABEL",
        "provenance_note": form_row["provenance_note"],
    } for form_row in forms]
    sql_candidates = [{
        **row,
        "research_version_id": VERSION_ID,
        "reconstructed": True,
        "provenance_status": "RECONSTRUCTED_FROM_REPORT",
    } for row in candidates]
    sections = [
        "BEGIN;\nSET search_path = fear_temperature, public;\n",
        sql_insert("canonical_concept", ["concept_id", "family_id", "preferred_label", "definition", "provisional_status", "provenance_note"], concepts),
        sql_insert("lexical_form", ["lexical_form_id", "surface_form", "normalized_form", "ambiguity_class", "is_high_value", "provenance_note"], forms),
        sql_insert("lexical_form_sense", ["lexical_form_sense_id", "lexical_form_id", "concept_id", "anchor_id", "sense_label", "relation_type", "provenance_note"], sense_rows),
        sql_insert("source", ["source_id", "source_genre_code", "canonical_name", "provenance_status", "provenance_note"], sources),
        sql_insert("seed_candidate", [
            "seed_candidate_id", "research_version_id", "originating_report", "originating_seed_stage",
            "original_candidate_id", "reconstructed", "provenance_status", "source_page", "anchor_id",
            "surface_form", "layer_code", "voice_code", "expression_mode_code", "source_id",
            "original_decision", "confidence_label", "relevance_label", "reconstruction_status",
            "reconciliation_status", "provenance_note",
        ], sql_candidates),
        "COMMIT;\n",
    ]
    SQL_PATH.write_text("\n".join(sections), encoding="utf-8")


def validate(initial: list[dict[str, Any]], priority: list[dict[str, Any]], expansions: list[dict[str, Any]]) -> int:
    if len(initial) != 180:
        raise ValueError(f"Expected 180 initial records, found {len(initial)}")
    if len(priority) != 180:
        raise ValueError(f"Expected 180 priority records, found {len(priority)}")
    if len(expansions) != 36:
        raise ValueError(f"Expected 36 expansion records, found {len(expansions)}")
    for name, rows in (("initial", initial), ("priority", priority), ("expansion", expansions)):
        counts = Counter(row["anchor_id"] for row in rows)
        expected = 30 if name != "expansion" else 6
        if set(counts.values()) != {expected} or len(counts) != 6:
            raise ValueError(f"Unexpected {name} anchor counts: {dict(counts)}")
        if len({row["seed_candidate_id"] for row in rows}) != len(rows):
            raise ValueError(f"Duplicate stable IDs in {name}")
        if any(not row["surface_form"] for row in rows):
            raise ValueError(f"Blank surface form in {name}")
    initial_forms = defaultdict(set)
    for row in initial:
        initial_forms[row["anchor_id"]].add(normalize_form(row["surface_form"]))
    exact_matches = sum(
        normalize_form(row["surface_form"]) in initial_forms[row["anchor_id"]]
        for row in priority
    )
    # The latest report states 36 exact surface matches. Direct reconstruction of
    # the two supplied compact tables yields 37 anchor-local normalized strings.
    # Preserve the discrepancy instead of arbitrarily choosing one row to drop.
    if exact_matches != 37:
        raise ValueError(f"Expected the reproducible compact-table count of 37, found {exact_matches}")
    return exact_matches


def main() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    initial = extract_initial_candidates()
    priority = extract_priority_candidates()
    expansions = build_expansion_candidates()
    exact_matches = validate(initial, priority, expansions)
    candidates = augment_candidate_metadata(initial + priority + expansions)
    sources = source_rows(priority)

    write_csv(SEED_DIR / "historical_anchors.csv", ["anchor_id", "label", "strict_start", "strict_end", "contextual_start", "contextual_end", "definition"], [
        dict(zip(["anchor_id", "label", "strict_start", "strict_end", "contextual_start", "contextual_end", "definition"], row)) for row in ANCHORS
    ])
    write_csv(SEED_DIR / "layers.csv", ["layer_code", "label"], [
        {"layer_code": code, "label": label} for code, label in LAYERS
    ])
    write_csv(SEED_DIR / "voices.csv", ["voice_code", "label"], [
        {"voice_code": code, "label": label} for code, label in VOICES
    ])
    write_csv(SEED_DIR / "expression_modes.csv", ["expression_mode_code", "label"], [
        {"expression_mode_code": code, "label": label} for code, label in EXPRESSION_MODES
    ])
    write_csv(SEED_DIR / "lexical_families.csv", ["family_id", "family_code", "label", "primary_layer_code", "is_synonym_group"], [
        {"family_id": row[0], "family_code": row[1], "label": row[2], "primary_layer_code": row[3], "is_synonym_group": "false"} for row in FAMILIES
    ])
    write_csv(SEED_DIR / "canonical_concepts.csv", ["concept_id", "family_id", "concept_code", "preferred_label", "definition", "provisional_status", "provenance_note"], CONCEPTS)
    write_csv(SEED_DIR / "high_value_lexical_forms.csv", ["lexical_form_id", "surface_form", "normalized_form", "concept_id", "ambiguity_class", "is_high_value", "provenance_note"], FORMS)
    write_csv(SEED_DIR / "seed_candidates.csv", [
        "seed_candidate_id", "originating_seed_stage", "original_candidate_id", "source_page",
        "anchor_id", "surface_form", "layer_code", "voice_code", "source_id",
        "expression_mode_code", "original_decision", "confidence_label", "relevance_label",
        "reconstruction_status", "reconciliation_status", "originating_report",
        "provenance_status", "provenance_note",
    ], [{**row, "provenance_status": "RECONSTRUCTED_FROM_REPORT"} for row in candidates])
    write_csv(SEED_DIR / "source_registry_reconstructed.csv", ["source_id", "source_genre_code", "canonical_name", "provenance_status", "provenance_note"], sources)
    write_csv(SEED_DIR / "semantic_rules.csv", ["semantic_rule_id", "anchor_id", "surface_form", "voice_code", "expression_mode_code", "affect_status", "threat_status", "review_outcome", "rule_note"], [
        dict(zip(["semantic_rule_id", "anchor_id", "surface_form", "voice_code", "expression_mode_code", "affect_status", "threat_status", "review_outcome", "rule_note"], row)) for row in SEMANTIC_RULES
    ])
    write_csv(SEED_DIR / "exclusion_rules.csv", ["surface_form", "rule_type", "valid_context_examples", "excluded_context_examples", "minimum_evidence"], [
        dict(zip(["surface_form", "rule_type", "valid_context_examples", "excluded_context_examples", "minimum_evidence"], row)) for row in EXCLUSION_RULES
    ])
    write_csv(EXPORT_DIR / "voice_keyword_matrix.csv", ["anchor_id", "anchor_label", "voice_code", "coverage_status", "representative_high_value_lexical_forms", "source_evidence_note"], [
        {
            "anchor_id": anchor_id,
            "anchor_label": ANCHOR_LABEL_BY_ID[anchor_id],
            "voice_code": voice,
            "coverage_status": status,
            "representative_high_value_lexical_forms": forms,
            "source_evidence_note": note,
        }
        for anchor_id, voice, status, forms, note in VOICE_MATRIX
    ])
    write_csv(SEED_DIR / "pilot_plan.csv", ["anchor_id", "anchor_label", "accepted_passage_target", "v1_target", "v2_target", "v3_target", "v4_target", "v5_target"], [
        {
            "anchor_id": row[0], "anchor_label": ANCHOR_LABEL_BY_ID[row[0]], "accepted_passage_target": row[1],
            "v1_target": row[2], "v2_target": row[3], "v3_target": row[4], "v4_target": row[5], "v5_target": row[6],
        } for row in PILOT_PLAN
    ])
    write_csv(SEED_DIR / "seed_import_status.csv", ["seed_version", "seed_import_status", "initial_records", "priority_records", "expansion_records", "total_seed_stage_records", "exact_surface_matches_reported", "exact_surface_matches_recomputed", "identity_discrepancy_status", "original_later_stage_ids_available", "production_freeze_status", "provenance_note"], [{
        "seed_version": VERSION_ID,
        "seed_import_status": "PARTIAL_RECONSTRUCTION",
        "initial_records": len(initial),
        "priority_records": len(priority),
        "expansion_records": len(expansions),
        "total_seed_stage_records": len(candidates),
        "exact_surface_matches_reported": 36,
        "exact_surface_matches_recomputed": exact_matches,
        "identity_discrepancy_status": "UNRESOLVED",
        "original_later_stage_ids_available": "false",
        "production_freeze_status": "BLOCKED_FOR_INPUT_RECONCILIATION",
        "provenance_note": "All rows are reconstructed from narrative PDF reports. Initial-seed original IDs are retained where visible; later-stage records use new project surrogate IDs because original structured IDs were unavailable. The latest report states 36 exact surface matches, while deterministic anchor-local table reconstruction yields 37; no arbitrary identity decision was made.",
    }])
    build_sql(CONCEPTS, FORMS, sources, candidates)
    print(f"seed_candidates={len(candidates)} initial={len(initial)} priority={len(priority)} expansion={len(expansions)} exact_matches={exact_matches} sources={len(sources)} concepts={len(CONCEPTS)} forms={len(FORMS)}")


if __name__ == "__main__":
    main()
