#!/usr/bin/env python3
"""Build the evidence-labelled EDA interpretation and semantic shortlist.

This script deliberately derives observations from the frozen Priority-180
analytical exports.  It ranks questions for later passage review; it does not
collect or validate passages and does not infer semantic evolution.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "data/fear-temperature/analysis"
EXPORTS = ROOT / "data/fear-temperature/exports"
DOCS = ROOT / "docs/research/fear-temperature"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt_pm(raw: str) -> str:
    if raw in ("", None):
        return "not measured"
    return f"{float(raw) * 1_000_000:.4g} per million"


def joined(values: set[str]) -> str:
    anchor_order = ["1842", "1938", "1988", "2006–2007", "2015", "2022"]
    voice_order = ["V1", "V2", "V3", "V4", "V5"]
    if values and values <= set(anchor_order):
        return "; ".join(value for value in anchor_order if value in values)
    if values and values <= set(voice_order):
        return "; ".join(value for value in voice_order if value in values)
    return "; ".join(sorted(values))


def main() -> None:
    candidates = read_csv(ANALYSIS / "candidate_analysis_180.csv")
    ngrams = read_csv(EXPORTS / "keyword_frequency_summary.csv")
    query_metadata = read_csv(ROOT / "data/fear-temperature/ngram/ngram_query_metadata.csv")
    anchor_layers = read_csv(ANALYSIS / "anchor_layer_counts.csv")
    anchor_voices = read_csv(ANALYSIS / "anchor_voice_counts.csv")

    by_query_term = {row["surface_form"].casefold(): row for row in ngrams}
    query_anchor_by_term = {
        row["surface_form"].casefold(): row["anchor_id"].replace("FT-A0607", "2006–2007").replace("FT-A", "")
        for row in query_metadata
    }

    # Each item was assessed against the actual candidate ledger and query
    # inventory. Match forms are explicit to avoid substring-driven inflation.
    specifications = [
        (1, "temperature", "temperature_threshold", ["temperature"], ["temperature"],
         "The generic series spans the full interval, but the Priority ledger distinguishes local measurement, means, global aggregates and thresholds.",
         "Which passages mark a shift from local/instrumental measurement to aggregate or governed temperature?", 14),
        (2, "heat", "heat", ["heat"], ["heat", "excessive heat", "heat wave", "extreme heat"],
         "The generic string is highly polysemous, while candidate forms distinguish physical, embodied, weather-event and hazard senses.",
         "Which voice and context convert physical or embodied heat into an explicit hazard appraisal?", 14),
        (3, "climate", "climate", ["climate"], ["climate"],
         "The 1842 dictionary match is PARTIAL; the generic series cannot identify modern climate-change meaning.",
         "How does climatological condition differ from later system, change and governance meanings?", 14),
        (4, "climatic change", "climate", ["climatic change"], [],
         "This climate-specific query peaks earlier than the modern issue label but first-nonzero output may include non-target or OCR cases.",
         "When is the phrase used descriptively, causally or as a public issue label?", 10),
        (5, "greenhouse effect", "carbon_greenhouse", ["greenhouse effect"], ["greenhouse effect"],
         "The raw series peaks in 1990 and declines thereafter; frequency alone does not identify scientific, institutional or media function.",
         "How does the mechanism label travel among scientific explanation, institutional threat and media warning?", 12),
        (6, "global warming", "warming", ["global warming"], ["global warming", "global warming has begun"],
         "The phrase recurs across 1988, 2006–2007 and 2022 candidates and shares one Ngram measurement across different voices.",
         "Does the same issue label perform equivalent work in scientific, mediated and lay contexts?", 14),
        (7, "climate change", "climate", ["climate change"], ["climate change"],
         "The raw series peaks at the 2022 endpoint and the candidate form recurs under institutional and lay voices.",
         "Which passages use the phrase as causal description, governance object, threat referent or public concern?", 14),
        (8, "common concern of humankind", "concern_alarm", ["common concern of humankind"], ["common concern of humankind"],
         "The dictionary anchor-sense match is DIFFERENT because this is a legal formula rather than personal emotion.",
         "What textual features keep legal common concern distinct from affective concern?", 8),
        (9, "worry", "worry", ["worry"], ["be worried. be very worried.", "personally worry", "worry a great deal", "very worried", "somewhat worried"],
         "The ledger separates a media imperative from elicited response wording even where the generic corpus string is identical or related.",
         "How should prescribed, instrument-supplied and participant-endorsed worry be distinguished in passages?", 14),
        (10, "fear / afraid", "fear_afraid", ["fear", "afraid"], ["afraid"],
         "Generic fear is frequent across the corpus, but the Priority ledger contains direct afraid evidence only at the contemporary anchor.",
         "Which occurrences are direct affect, quotation, rhetorical prescription or unrelated generic fear?", 12),
        (11, "anxiety", "anxiety", ["anxiety"], ["anxious", "symptoms of anxiety", "anxiety and stress"],
         "Generic anxiety peaks in 2022, while Priority evidence separates participant endorsement from researcher-labelled constructs.",
         "Who supplies the anxiety label, and does the participant independently use it?", 12),
        (12, "climate anxiety", "anxiety", ["climate anxiety"], ["climate anxiety"],
         "The query has a sparse modern trajectory and a PARTIAL anchor-sense match because the candidate is a research construct.",
         "When is climate anxiety researcher-defined, instrument-supplied or participant self-description?", 12),
        (13, "eco-anxiety", "anxiety", ["eco-anxiety"], ["eco-anxiety"],
         "The compound is sparse in Ngram despite nonzero bounded-search discovery; early nonzero years need validation.",
         "Which attestations carry the recognised construct rather than OCR, hyphenation or unrelated component effects?", 10),
        (14, "risk", "risk", ["risk"], ["risk of conflicts", "costs and risks of climate change", "risks and impacts", "risk of loss and damage"],
         "The high generic peak is not climate-specific, while candidate forms are predominantly institutional and governance-oriented.",
         "How do probabilistic, governance and consequence senses vary by source and referent?", 12),
        (15, "threat", "danger_threat", ["threat"], ["major threat", "grave threats", "serious global threat", "urgent threat", "very serious threat"],
         "Threat candidates span institutional and elicited lay voices; threat must not be treated as emotion.",
         "When is threat an institutional classification, media warning or elicited public appraisal?", 12),
        (16, "global security", "danger_threat", ["global security"], ["global security"],
         "The 1988 candidate is an institutional security frame and its raw string trajectory cannot establish affect.",
         "How does security framing connect to climatic risk without being recoded as fear?", 8),
        (17, "crisis", "crisis_emergency", ["crisis"], ["impending crisis"],
         "The generic crisis curve is background-ambiguous and the candidate ledger anchors an institutional severity predicate.",
         "Which referent and speaker make crisis climate-specific rather than a general severity term?", 10),
        (18, "climate crisis", "crisis_emergency", ["climate crisis"], ["climate crisis"],
         "The raw series rises sharply at the contemporary endpoint, but early isolated nonzero observations are not validated target-sense emergence.",
         "When does climate crisis function as advocacy label, media frame or participant vocabulary?", 12),
        (19, "climate emergency", "crisis_emergency", ["climate emergency"], [],
         "The climate-specific query rises late, while its early Ngram nonzero observations are methodologically suspect without passage validation.",
         "Which attestations refer to a declared governance frame rather than accidental phrase adjacency?", 10),
        (20, "depressing effect / depressed", "distress_depression", ["depressing effect", "depressed"], ["depressing effect", "depressed"],
         "The 1842 depressing effect match is DIFFERENT from the contemporary affective depressed candidate, creating a documented false-continuity risk.",
         "How do bodily energetic, causal-lowering and psychological senses separate across the two anchors?", 14),
    ]

    out_rows: list[dict[str, object]] = []
    for priority, item, family, query_terms, match_forms, problem, question, sample in specifications:
        normalized_matches = {form.casefold() for form in match_forms}
        matched = [row for row in candidates if row["normalized_form"].casefold() in normalized_matches]
        anchors = {row["anchor_label"] for row in matched}
        voices = {row["voice_code"] for row in matched}
        candidate_ids = [row["candidate_id"] for row in matched]
        query_rows = [by_query_term[term.casefold()] for term in query_terms if term.casefold() in by_query_term]
        if not anchors:
            query_anchors = {query_anchor_by_term.get(term.casefold(), "") for term in query_terms}
            anchors = {anchor for anchor in query_anchors if anchor}
        if not voices:
            voices = {"NOT_APPLICABLE_QUERY_LEVEL"}

        observations = []
        observed_measurement_forms = set()
        for query in query_rows:
            observed_measurement_forms.add(query["surface_form"].casefold())
            observations.append(
                f"{query['surface_form']}: first nonzero {query['first_nonzero_year'] or 'none'}, "
                f"peak {query['peak_year'] or 'none'} at {fmt_pm(query['peak_frequency'])}, "
                f"2022 {fmt_pm(query['2022_value'])}"
            )
        for candidate in matched:
            measurement_form = candidate["ngram_measurement_form"]
            if (
                candidate["ngram_peak_frequency_raw"]
                and measurement_form.casefold() not in observed_measurement_forms
                and (not query_rows or candidate["dictionary_anchor_sense_match"] == "DIFFERENT")
            ):
                observed_measurement_forms.add(measurement_form.casefold())
                observations.append(
                    f"{measurement_form}: first nonzero {candidate['ngram_first_nonzero_year'] or 'none'}, "
                    f"peak {candidate['ngram_peak_year'] or 'none'} at {fmt_pm(candidate['ngram_peak_frequency_raw'])}, "
                    f"2022 {fmt_pm(candidate['ngram_2022_frequency_raw'])}"
                )
        if not observations:
            observations.append("No standalone baseline query; assessment is candidate-led and requires passage evidence.")

        out_rows.append({
            "priority": priority,
            "term_or_family": item,
            "family": family,
            "anchors": joined(anchors) if anchors else "UNRESOLVED",
            "voices": joined(voices),
            "candidate_count": len(matched),
            "candidate_ids": "; ".join(candidate_ids) if candidate_ids else "QUERY_RULE_LEVEL_ONLY",
            "query_terms": "; ".join(row["surface_form"] for row in query_rows) if query_rows else "NOT_APPLICABLE",
            "observed_pattern_class": "OBSERVED_CORPUS_PATTERN" if observed_measurement_forms else "CONSTRUCTED_INVENTORY_PATTERN",
            "observed_quantitative_pattern": " | ".join(observations),
            "ambiguity_or_problem": problem,
            "semantic_question": question,
            "recommended_passage_sample": sample,
            "sample_note": "Planning count; overlapping passages may answer multiple shortlist questions.",
            "hypothesis_status": "SEMANTIC_HYPOTHESIS_NOT_YET_TESTED",
            "data_sources": "candidate_analysis_180.csv; keyword_frequency_summary.csv; candidate_comparability.csv; candidate_relationship.csv",
        })

    shortlist_path = ANALYSIS / "semantic_analysis_shortlist.csv"
    with shortlist_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)

    layer_totals = Counter(row["layer_code"] for row in candidates)
    voice_totals = Counter(row["voice_code"] for row in candidates)
    dictionary_totals = Counter(row["dictionary_status"] for row in candidates)
    search_totals = Counter(row["search_status"] for row in candidates)
    ngram_totals = Counter(row["ngram_status"] for row in candidates)
    anchor_voice_by_label = {row["anchor"]: row for row in anchor_voices}
    anchor_layer_by_label = {row["anchor"]: row for row in anchor_layers}

    def query_fact(term: str) -> str:
        row = by_query_term[term.casefold()]
        return (
            f"`{term}` first registers a nonzero raw string value in {row['first_nonzero_year']}, "
            f"peaks in {row['peak_year']} at {fmt_pm(row['peak_frequency'])}, and records "
            f"{fmt_pm(row['2022_value'])} in 2022"
        )

    doc = f"""# Fear of Temperature — Exploratory Analysis v0.2

This analysis derives relationships from the fixed 180-candidate Priority inventory. It does not add keywords, collect passages, or claim semantic evolution. Each finding is labelled by evidence type so that inventory construction, corpus frequency, source composition, searchability and semantic hypotheses remain separate.

## Current evidence structure

- **CONSTRUCTED_INVENTORY_PATTERN** — The analytical population contains 180 candidates: 30 at each of six anchors. The four layers contain A={layer_totals['A']}, B={layer_totals['B']}, C={layer_totals['C']} and D={layer_totals['D']} candidates. These counts describe the constructed inventory, not language prevalence.
- **CONSTRUCTED_INVENTORY_PATTERN** — All 180 candidates retain candidate-to-Ngram, dictionary and bounded-search mappings. The relationship ledger contains 337 evidence-labelled links; only six are research/semantic candidate relations, and none asserts an automatic historical progression.
- **UNRESOLVED** — Passage-level reception, referent, quotation boundary and respondent/instrument distinctions remain outside this EDA and are assigned to the shortlist rather than inferred.

## Lexical composition

- **CONSTRUCTED_INVENTORY_PATTERN** — Layer A forms {float(anchor_layer_by_label['1842']['A_percentage']):.0%} of the 1842 inventory, whereas layer D forms {float(anchor_layer_by_label['2015']['D_percentage']):.0%} of the 2015 inventory and layer C forms {float(anchor_layer_by_label['2022']['C_percentage']):.0%} of the 2022 inventory.
- **CONSTRUCTED_INVENTORY_PATTERN** — This contrast reflects deliberate anchor-specific candidate construction and source recovery. It is not evidence that historical populations used affect or threat vocabulary in these proportions.

## Voice/source composition

- **SOURCE_COMPOSITION_PATTERN** — V1 accounts for {voice_totals['V1']} candidates overall and {float(anchor_voice_by_label['1842']['V1_percentage']):.0%} of the 1842 inventory; V2 accounts for {float(anchor_voice_by_label['2015']['V2_percentage']):.0%} of 2015; V5 accounts for {float(anchor_voice_by_label['2022']['V5_percentage']):.0%} of 2022.
- **SOURCE_COMPOSITION_PATTERN** — V4 has only {voice_totals['V4']} candidates overall and is absent in the 1842, 1938 and 1988 Priority samples. V5 is absent in the exact-1938 and exact-1988 Priority samples. These gaps must remain visible rather than being balanced synthetically.
- **SEMANTIC_HYPOTHESIS** — Some apparent movement from measurement to threat and affect may reflect changing source/speaker composition. Passage review must test this before it is narrated as historical change.

## Temporal lexical trajectories

- **OBSERVED_CORPUS_PATTERN** — {query_fact('climatic change')}; {query_fact('greenhouse effect')}; {query_fact('global warming')}; and {query_fact('climate change')}.
- **OBSERVED_CORPUS_PATTERN** — {query_fact('climate crisis')}; {query_fact('climate emergency')}; {query_fact('climate anxiety')}; and {query_fact('eco-anxiety')}.
- **UNRESOLVED** — First nonzero Ngram years are string observations in Google Books, not validated coinage or target-sense dates. The early values for modern compounds are therefore treated as audit flags, not historical emergence claims.

## Search/dictionary diagnostics

- **SEARCHABILITY_PATTERN** — Internet Archive metadata search returned nonzero discovery counts for {search_totals['COMPLETED_NONZERO']} candidates and zero for {search_totals['COMPLETED_ZERO']}. These are provider discovery counts, not corpus word frequencies or historical abundance.
- **CONSTRUCTED_INVENTORY_PATTERN** — Lexicographic accounting comprises {dictionary_totals['DIRECT_HEADWORD']} direct headwords, {dictionary_totals['TECHNICAL_GLOSSARY']} technical-glossary treatments and {dictionary_totals['NO_STANDALONE_HEADWORD']} phrases without a standalone headword.
- **SEARCHABILITY_PATTERN** — Easier retrieval of modern material may reflect metadata quality, digitisation and provider indexing. Zero is retained as an observed provider/query result and never converted into a claim of historical absence.

## Ambiguity and corpus artefacts

- **OBSERVED_CORPUS_PATTERN** — The Priority Ngram mapping contains {ngram_totals['SUCCEEDED_REUSED_BASELINE'] + ngram_totals['SUCCEEDED_NEW']} successful candidate mappings, {ngram_totals['ZERO_RESPONSE_REUSED_BASELINE'] + ngram_totals['ZERO_RESPONSE_NEW']} explicit zero-response mappings and {ngram_totals['TECHNICALLY_UNREPRESENTABLE']} technically unrepresentable candidate.
- **UNRESOLVED** — Generic strings including temperature, heat, fear, concern, anxiety, threat, risk and crisis remain semantically ambiguous. Their raw curves cannot be interpreted as climate-specific affect.
- **SEMANTIC_HYPOTHESIS** — Disagreement among Ngram first nonzero, dictionary evidence and validated anchor context is a useful passage-selection signal; it is not by itself evidence of semantic reconfiguration.

## Candidate historical patterns

- **OBSERVED_CORPUS_PATTERN** — `global warming` peaks in 2009 in the current raw Ngram series, while `climate change` peaks at the 2022 endpoint. The curves describe publication-string frequency, not public reception.
- **SOURCE_COMPOSITION_PATTERN** — `global warming` recurs in V1, V3 and V5 candidate records; the shared string measurement therefore cannot stand in for a shared social function.
- **CONSTRUCTED_INVENTORY_PATTERN** — `common concern of humankind` and 1842 `depressing effect` are the two DIFFERENT anchor-sense matches. They provide concrete negative tests against recoding legal concern as emotion or embodied depression as modern clinical depression.
- **SEMANTIC_HYPOTHESIS** — The distinction between the 2006 media imperative and elicited worry, and between 2022 researcher-labelled climate anxiety and participant endorsement, should be tested at sentence/paragraph and instrument-question level.

## Questions requiring semantic validation

The generated shortlist contains {len(out_rows)} terms or term-clusters. Ranking uses cross-anchor recurrence, voice contrast, dictionary mismatch, raw-string/attestation tension, ambiguity and false-continuity risk. Recommended passage counts are planning weights; because one passage may test multiple questions, they are not an additive collection quota.

Highest-priority questions are:

1. **SEMANTIC_HYPOTHESIS** — When does temperature refer to local measurement, aggregate climate state or a governance threshold?
2. **SEMANTIC_HYPOTHESIS** — When does physical or embodied heat become a hazard or affective appraisal?
3. **SEMANTIC_HYPOTHESIS** — How do `climate`, `climatic change`, `global warming` and `climate change` differ by voice and function?
4. **SEMANTIC_HYPOTHESIS** — How should institutional threat/risk/crisis be separated from emotion?
5. **SEMANTIC_HYPOTHESIS** — Who supplies worry/anxiety terminology: media, instrument, researcher or participant?
6. **SEMANTIC_HYPOTHESIS** — Which early Ngram observations for modern compounds are OCR, adjacency, other-sense or valid target-sense attestations?

The next phase is a passage-level semantic validation pilot designed from this shortlist. No passage collection was performed in this round.

## Reproducibility and source map

- Candidate population and joined measurements: `data/fear-temperature/analysis/candidate_analysis_180.csv`
- Relationship and comparability evidence: `candidate_relationship.csv` and `candidate_comparability.csv`
- Inventory matrices: `anchor_layer_counts.csv`, `anchor_voice_counts.csv`, `anchor_family_counts.csv`, `voice_family_counts.csv`
- Raw annual Ngram observations: `data/fear-temperature/ngram/ngram_timeseries_full.csv` (smoothing=0)
- Per-query statistics: `data/fear-temperature/exports/keyword_frequency_summary.csv`
- Bounded-search and dictionary candidate evidence: `priority180_full_coverage_matrix.csv`
- Shortlist: `data/fear-temperature/analysis/semantic_analysis_shortlist.csv`

All quantitative descriptions are descriptive. No family frequencies are summed and no “Fear Score” is constructed.
"""
    (DOCS / "EXPLORATORY_ANALYSIS_V02.md").write_text(doc, encoding="utf-8")

    print(f"SEMANTIC_SHORTLIST_COUNT={len(out_rows)}")
    print(f"INTERPRETATION_DOCUMENT={DOCS / 'EXPLORATORY_ANALYSIS_V02.md'}")


if __name__ == "__main__":
    main()
