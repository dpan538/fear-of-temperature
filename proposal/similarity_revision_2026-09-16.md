# Similarity and structural analysis revision — 16 September 2026

## Research canon and scope

The latest user discussion supersedes the earlier commitment to three separate NLP modules. Fear of rising temperatures remains the substantive focus; the primary method is pretrained embedding similarity and structural comparison. No independent emotion classifier, semantic-role extraction system or BERTopic implementation is mandatory. The author, supervisor, historical collection target, English core and 10–20 h/week schedule remain unchanged. Analysis must finish by 28 February 2027.

## Evidence and decision register

| Claim / decision | Basis | Boundary |
|---|---|---|
| Fear remains the research object | User's explicit correction | General climate proximity alone is insufficient |
| No separate semantic-analysis module | User's explicit scope choice | Contextual validation is retained |
| Reference-guided similarity | Latest discussion approved for inclusion | Initial operational specification, to validate |
| MiniLM primary representation | User's named candidate; official model card | Default input truncation requires segmentation |
| ClimateBERT bounded comparison | User's candidate; official masked-LM model card | Pooling and retrieval quality need validation |
| FAISS nearest-neighbour indexing | Official FAISS documentation | Not a language model or discourse graph |
| Encoder spaces remain separate | Different learned representations | Do not pool or directly equate their scores |
| Fixed reference set | Reproducible temporal comparison | Sensitivity checks, no outcome-driven selection |
| q = average reference cosine | Transparent initial design | Not an emotion probability or intensity |
| Q = weighted relevant-subset mean q | Matches units/weights | Conditional on eligible coverage |
| S requires background denominator | Existing sampling design | Fear-only retrieval cannot estimate all-topic share |
| Tree/graph definition unresolved | User has not selected edge semantics | Pilot gate explicitly retained |
| Similarity edges indicate proximity | Meaning of construction | Not diffusion, agreement or causal ancestry |
| Real replies/citations are separate | Distinct evidence type | Optional, not assumed available |
| Corpus construction remains R1 | Existing risk and user workload discussion | NoSQL/vector normalisation does not fix comparability |
| MPhil thesis is workload context | Uploaded Duan thesis: title page, abstract, experiments | Not coursework minimum or required architecture |

Model/documentation sources checked during the discussion:
- https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- https://huggingface.co/climatebert/distilroberta-base-climate-f
- https://faiss.ai/

## Argument map and section contracts

1. Motivation: retain warming fear; explain why reference-guided retrieval addresses lexical limitations. Do not promise automatic psychological measurement.
2. Literature/gap: connect expressions, proximity and structure. Replace mandatory classification/extraction literature with the actual representation tools; do not claim new architecture.
3. RQs: timing of convergence/divergence; event-associated change; organisation of fear expressions. RQ3 no longer promises automatic cause/blame/duty extraction.
4. Measures: replace E and B emotion-label formulas with q/Q reference similarity. Keep S only where an eligible denominator exists.
5. Implementation: MiniLM, lexical baseline, FAISS and one pilot-selected structure. ClimateBERT optional and separately indexed.
6. Validation: ranked judgements, counterexamples, background misses, source/period transfer and structural sensitivity. No unsupported full-corpus recall.
7. Delivery: protect validated retrieval/structure, reduce breadth first. Preserve the February analysis deadline.

## Independent review

A read-only scope reviewer identified eight required consistency checks: fear-reference validation; removal of three-module commitments; distinct tool roles; replacement of emotion equations; RQ alignment; explicit unresolved edge definition; updated risks/evaluation; coherent figures/literature/schedule. These checks informed the revision. No empirical results were added.

## Applied changes

- Revised §§1.2–1.4, selected background passages, §§2.5–2.6 and §§3.1–3.9/3.11.
- Updated the RQ mapping, pipeline, reference-example and temporal-measure figures; updated the schedule validation label.
- Replaced Equations 2–3 in the Markdown and shared equation renderer.
- Removed unused references to the superseded mandatory modules; added three official tool/model documentation records.
- Retained original versions and assets under `versions/before_similarity_revision_2026-09-16/`.
- This note does not amend the separately prepared group-meeting report, which still reflects the prior scope until revised.

## Remaining design decisions

The pilot must select the primary tree/graph construction, edge rules, structural summary and cross-time alignment. Reference set composition and sufficient validation quality remain empirical decisions. These are visible in the proposal rather than silently fixed. Workload estimates are planning values, not measurements inferred from another student's thesis.

## Verification

All four canonical formats regenerated. PDF: 21 pages, 8 figures, 9 table panels, 29 references. Citation keys match bibliography entries exactly. Layout preflight reports no overflow; revised RQ, measures, validation, pipeline, temporal, event and risk pages were rendered and inspected. Figure alignment/collision audits passed. No empirical pipeline or environment was modified.
