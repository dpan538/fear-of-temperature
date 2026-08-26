# Fear of Temperature — Exploratory Analysis v0.2

This analysis derives relationships from the fixed 180-candidate Priority inventory. It does not add keywords, collect passages, or claim semantic evolution. Each finding is labelled by evidence type so that inventory construction, corpus frequency, source composition, searchability and semantic hypotheses remain separate.

## Current evidence structure

- **CONSTRUCTED_INVENTORY_PATTERN** — The analytical population contains 180 candidates: 30 at each of six anchors. The four layers contain A=47, B=29, C=33 and D=71 candidates. These counts describe the constructed inventory, not language prevalence.
- **CONSTRUCTED_INVENTORY_PATTERN** — All 180 candidates retain candidate-to-Ngram, dictionary and bounded-search mappings. The relationship ledger contains 337 evidence-labelled links; only six are research/semantic candidate relations, and none asserts an automatic historical progression.
- **UNRESOLVED** — Passage-level reception, referent, quotation boundary and respondent/instrument distinctions remain outside this EDA and are assigned to the shortlist rather than inferred.

## Lexical composition

- **CONSTRUCTED_INVENTORY_PATTERN** — Layer A forms 53% of the 1842 inventory, whereas layer D forms 67% of the 2015 inventory and layer C forms 67% of the 2022 inventory.
- **CONSTRUCTED_INVENTORY_PATTERN** — This contrast reflects deliberate anchor-specific candidate construction and source recovery. It is not evidence that historical populations used affect or threat vocabulary in these proportions.

## Voice/source composition

- **SOURCE_COMPOSITION_PATTERN** — V1 accounts for 71 candidates overall and 60% of the 1842 inventory; V2 accounts for 80% of 2015; V5 accounts for 57% of 2022.
- **SOURCE_COMPOSITION_PATTERN** — V4 has only 4 candidates overall and is absent in the 1842, 1938 and 1988 Priority samples. V5 is absent in the exact-1938 and exact-1988 Priority samples. These gaps must remain visible rather than being balanced synthetically.
- **SEMANTIC_HYPOTHESIS** — Some apparent movement from measurement to threat and affect may reflect changing source/speaker composition. Passage review must test this before it is narrated as historical change.

## Temporal lexical trajectories

- **OBSERVED_CORPUS_PATTERN** — `climatic change` first registers a nonzero raw string value in 1844, peaks in 1990 at 1.085 per million, and records 0.3561 per million in 2022; `greenhouse effect` first registers a nonzero raw string value in 1843, peaks in 1990 at 1.961 per million, and records 0.4531 per million in 2022; `global warming` first registers a nonzero raw string value in 1843, peaks in 2009 at 5.446 per million, and records 3.964 per million in 2022; and `climate change` first registers a nonzero raw string value in 1842, peaks in 2022 at 28.9 per million, and records 28.9 per million in 2022.
- **OBSERVED_CORPUS_PATTERN** — `climate crisis` first registers a nonzero raw string value in 1867, peaks in 2022 at 0.9388 per million, and records 0.9388 per million in 2022; `climate emergency` first registers a nonzero raw string value in 1846, peaks in 2022 at 0.2626 per million, and records 0.2626 per million in 2022; `climate anxiety` first registers a nonzero raw string value in 1972, peaks in 2022 at 0.03579 per million, and records 0.03579 per million in 2022; and `eco-anxiety` first registers a nonzero raw string value in 1901, peaks in 2022 at 0.05496 per million, and records 0.05496 per million in 2022.
- **UNRESOLVED** — First nonzero Ngram years are string observations in Google Books, not validated coinage or target-sense dates. The early values for modern compounds are therefore treated as audit flags, not historical emergence claims.

## Search/dictionary diagnostics

- **SEARCHABILITY_PATTERN** — Internet Archive metadata search returned nonzero discovery counts for 141 candidates and zero for 39. These are provider discovery counts, not corpus word frequencies or historical abundance.
- **CONSTRUCTED_INVENTORY_PATTERN** — Lexicographic accounting comprises 25 direct headwords, 49 technical-glossary treatments and 106 phrases without a standalone headword.
- **SEARCHABILITY_PATTERN** — Easier retrieval of modern material may reflect metadata quality, digitisation and provider indexing. Zero is retained as an observed provider/query result and never converted into a claim of historical absence.

## Ambiguity and corpus artefacts

- **OBSERVED_CORPUS_PATTERN** — The Priority Ngram mapping contains 162 successful candidate mappings, 17 explicit zero-response mappings and 1 technically unrepresentable candidate.
- **UNRESOLVED** — Generic strings including temperature, heat, fear, concern, anxiety, threat, risk and crisis remain semantically ambiguous. Their raw curves cannot be interpreted as climate-specific affect.
- **SEMANTIC_HYPOTHESIS** — Disagreement among Ngram first nonzero, dictionary evidence and validated anchor context is a useful passage-selection signal; it is not by itself evidence of semantic reconfiguration.

## Candidate historical patterns

- **OBSERVED_CORPUS_PATTERN** — `global warming` peaks in 2009 in the current raw Ngram series, while `climate change` peaks at the 2022 endpoint. The curves describe publication-string frequency, not public reception.
- **SOURCE_COMPOSITION_PATTERN** — `global warming` recurs in V1, V3 and V5 candidate records; the shared string measurement therefore cannot stand in for a shared social function.
- **CONSTRUCTED_INVENTORY_PATTERN** — `common concern of humankind` and 1842 `depressing effect` are the two DIFFERENT anchor-sense matches. They provide concrete negative tests against recoding legal concern as emotion or embodied depression as modern clinical depression.
- **SEMANTIC_HYPOTHESIS** — The distinction between the 2006 media imperative and elicited worry, and between 2022 researcher-labelled climate anxiety and participant endorsement, should be tested at sentence/paragraph and instrument-question level.

## Questions requiring semantic validation

The generated shortlist contains 20 terms or term-clusters. Ranking uses cross-anchor recurrence, voice contrast, dictionary mismatch, raw-string/attestation tension, ambiguity and false-continuity risk. Recommended passage counts are planning weights; because one passage may test multiple questions, they are not an additive collection quota.

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
