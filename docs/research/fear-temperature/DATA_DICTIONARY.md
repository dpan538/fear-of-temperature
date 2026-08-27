# Data Dictionary — Quantitative Baseline v0.1

## Research and controlled dimensions

| Table | Purpose | Key controls |
| --- | --- | --- |
| `research_version` | Names a reproducible research state and its provenance limits. | Stable text ID; status; source report; notes. |
| `historical_anchor` | Stores strict and contextual windows for the six analytical anchors. | Unique label; strict window must be contained by contextual window. |
| `lexical_layer` | A–D lexical layers. | Stable code and label. |
| `lexical_family` | Fourteen semantic research families. | Family code; primary layer; explicitly not a synonym set. |
| `voice` | V1–V5 speaker positions. | Stable code and label. |
| `expression_mode` | E1–E5 expression/provenance modes. | Stable code and label. |
| `review_outcome` | Controlled passage-review outcomes. | Stable code. |

## Lexical and seed model

| Table | Purpose | Important relationship |
| --- | --- | --- |
| `canonical_concept` | Holds analytically distinct meanings such as local temperature, global aggregate temperature, elicited worry, or legal concern. | One family can contain many concepts. |
| `lexical_form` | Holds normalized and display forms. | A form is not assumed to equal a concept. |
| `lexical_form_sense` | Connects forms to historically bounded concepts and metadata. | Supports one form → multiple senses and one concept → multiple forms. |
| `seed_candidate` | Preserves every recoverable seed-stage research record without deduplication. | Retains source stage, anchor, visible original ID where genuine, reconstructed flag, decision, and provenance note. |
| `exclusion_rule` | Records wrong-sense and false-positive contexts. | Linked to a form or family rather than stored as free JSON. |

The provisional seed ledger contains 396 rows: 180 historical discovery records, 180 Priority records, and 36 Expansion records. Repeated surface strings remain separate records when their research provenance differs.

## Source, retrieval, and frequency model

| Table | Purpose | Important fields |
| --- | --- | --- |
| `source_genre`, `source`, `document` | Identifies source collections and individual documents. | Voice is not inferred solely from genre. |
| `query_rule` | Stores each anchor-specific retrieval rule and compatibility decision. | Classification, interpretation class, anchor, form, concept, exclusions, reconstructed provenance. |
| `query_run` | Stores a provider/corpus/parameter execution. | Provider, corpus ID/version, year range, smoothing, retrieval metadata. |
| `query_execution_result` | Preserves success, zero, failure, and not-run outcomes. | Attempt count, reason, raw response path/hash. |
| `frequency_observation` | Stores annual normalized Ngram-style observations. | Unique query + run + year + parameter set; raw smoothing recorded explicitly. |
| `search_observation` | Reserves bounded-corpus counts for later collection. | Raw hits, unique documents, retrieved/reviewed/accepted/rejected passages, and false positives remain `NULL`/not-run until a connector exists. |

Canonical CSV exports use normalized frequencies in the provider's native proportion. Presentation tables multiply these values by one million and label the unit explicitly.

## Passage and review chain

| Table | Purpose |
| --- | --- |
| `evidence_passage` | Stores candidate or accepted text with sentence, surrounding context, paragraph, source, speaker, and quotation boundaries. |
| `lexical_occurrence` | Locates the matched form within a passage. |
| `semantic_annotation` | Records sense, family/layer, voice, expression mode, referent, and semantic qualifications. |
| `review_decision` | Stores reviewer outcome and rationale without deleting rejected evidence. |
| `passage_linkage_validation` | Stores an explicit validated relation from an accepted A/B object annotation to a C affect or D threat annotation. Co-occurrence never creates this relation automatically. |
| `provenance_event` | Provides an append-only audit trail for import, transformation, retrieval, and review events. |

The intended traceability chain is `source → document → passage → occurrence → annotation → review`.

Relational analysis adds `passage → accepted A/B object annotation → validated C/D linkage`. Affect linkages also require one preserved mode: direct, prescribed, elicited, or researcher-labelled.

## Relational-analysis exports

| File | Grain |
| --- | --- |
| `AB_object_passages.csv` | One validated A/B object annotation within a passage; currently header-only because no passage chain is populated. |
| `threat_linkage_passages.csv` | One explicitly validated A/B → D passage relation. |
| `affect_linkage_passages.csv` | One explicitly validated A/B → C passage relation with affect mode. |
| `voice_linkage_summary.csv` | One anchor × voice cell with denominators, counts, rates, ratios and low-N status. |
| `lexicalisation_comparison.csv` | One selected term with four distinct temporal markers and ambiguity notes. |

When the A/B denominator is zero, the exported rate is blank and `Rate_Status=UNSUPPORTED_DENOMINATOR_ZERO`; it is never encoded as `0%`.

## Main exports

| File | Grain |
| --- | --- |
| `seed_candidates.csv` | One provenance-bearing seed-stage record. |
| `query_rules.csv` | One anchor-specific provisional query rule. |
| `ngram_query_execution_results.csv` | One execution outcome per query rule. |
| `ngram_timeseries_full.csv` | One successful query/corpus/year observation. |
| `keyword_frequency_summary.csv` | One descriptive summary per query rule. |
| `anchor_keyword_frequency_matrix.csv` | Raw annual values at the six anchor positions. |
| `anchor_keyword_contextual_matrix.csv` | Contextual-window descriptive values per query. |
| `lexical_family_frequency_summary.csv` | Non-additive comparison of family members. |
| `voice_keyword_matrix.csv` | One anchor × voice coverage cell. |

JSON is limited to raw provider payloads, irregular metadata, and collector details; controlled analytical dimensions remain relational.
