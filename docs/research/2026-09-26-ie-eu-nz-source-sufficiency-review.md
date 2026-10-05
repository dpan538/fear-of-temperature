# Ireland, EU and New Zealand: source opportunity and data sufficiency

Review date: 26 September 2026. Study cutoff retained: 21 September 2026.
Status: evidence review and proposed planning gates, not a change to the proposal or approved analysis plan.

## Evidence and scope

This review recomputed summaries from the 08 work package's saved observations of 23 September and checked official documentation and several publication routes online. It did not acquire a new bulk corpus or change any database. The earlier `08/reports/coverage_report.md` predates some later EU/NZ observations and understates the available reconnaissance evidence.

| Jurisdiction/source | Observed target universe | What remains unknown | Research value |
|---|---|---|---|
| EU/European Commission, CELLAR, English expression, `cdm:act_preparatory`, 1988–cutoff | 50,578 summed monthly DISTINCT-Work counts across 465 months; 464 positive months; 2024-08 is the only zero in this query | Global distinct Work count, accessible digital full texts, document-subtype mix, climate/fear yield, query-classification completeness | Strongest candidate for extending early institutional text coverage; a supranational series, not member-state government coverage |
| Ireland/Oireachtas, all-department written-question index, 2012-07–cutoff | 684,809 indexed questions across 171 months; 152 positive months, 19 query-zero months | Unique ministerial answer units, portfolio history, actual answer dates, target-department total, pre-2012 systematic coverage | English ministerial replies provide a useful genre comparator for UK replies |
| Ireland pilot, 2012-09 | 3,171 question records; 357 addressed to Environment (269) or Communications (88), all with answer text; 280 distinct full answer strings | Whether repeated strings represent joint answers or distinct repeated utterances; stable portfolio scope across time | Demonstrates real answer access and exposes duplicate weighting risk |
| New Zealand Parliament, Climate Change portfolio, currently answered questions, 2025 | 536 displayed question records across 12 positive months; monthly range 14–106 | Unique answer units, answer/publication-date distribution, historical UI coverage and download route, corrected-reply histories | Bounded contemporary climate-governance corpus; likely better suited initially to quarterly summaries or event/context studies |
| NZ Ministry for the Environment and Beehive | Named originals and archive entrances verified; no defensible total yet | Complete catalogue, portfolio/genre counts, predecessor coverage and version boundaries | Earlier policy originals and direct ministerial communication, supplementing parliamentary replies |

These numbers are different units and must not be added into a single eligible-corpus count. A monthly count sum is not a verified global unique count. Index access does not establish full-text download success.

EU counts by display period: 1988–2000: 12,057 (156 months); 2001–2013: 26,087 (156); 2014–2026-09: 12,434 (153). The selected class covers all topics, not climate policy alone. Investigate the recent reduction in counts and the August 2024 zero before interpreting them as changes in institutional output.

Ireland's one-month target share is 357/3,171 = 11.26%. Mechanically applying it to 684,809 gives about 77,098 question-linked candidates, but this is **not a forecast**: portfolio responsibilities, session timing and answer grouping vary. For budgeting only, Ireland plausibly requires processing an index of hundreds of thousands to obtain a smaller departmental subset. A stratified set of additional months is needed for a defensible target estimate; do not commit to harvesting 684,809 answers.

The 357 Irish answers contain 77 excess exact-string instances across 45 repeated-string groups. These are duplicate candidates for weighting and identity review, not 77 records authorised for deletion. The question records and relationships should be retained.

## Official routes and what they establish

- Oireachtas documents its API and the XML answer/debate route at <https://api.oireachtas.ie/>. Its questions page directs pre-July-2012 material to Dáil debates: <https://www.oireachtas.ie/en/debates/questions/?questionType=written>. This review's direct web fetch of that page returned 403, although the official search-index text and API documentation remain available. An actual pre-2012 example includes two questions handled by one ministerial answer: <https://www.oireachtas.ie/en/debates/question/2009-03-10/section/31/>.
- CELLAR's official model separates Work, language Expression, format Manifestation and Item: <https://op.europa.eu/en/web/cellar/cellar-data>. Deduplicate works while retaining English content representations. A print-only manifestation is not a downloadable full text. Commission preparatory acts encompass heterogeneous proposals, communications and supporting documents; subtype and issuer should remain explicit.
- NZ's first national communication is a real 70-page official PDF whose cover is dated September 1994: <https://environment.govt.nz/assets/publications/climate-change/newnc1.pdf>. It also contains a 1995 UN executive-summary insert, so distinguish constituent dates. Its retrospective account of a 1988 programme is not a document published in 1988.
- Beehive has an official archived 1993–1996 administration listing with dated 1996 ministerial releases and speeches: <https://www.beehive.govt.nz/portfolio/national-1993-1996/national-1993-1996>. This establishes a promising source entrance, not full coverage for every year in the label.
- A current NZ policy page explicitly distinguishes an original December 2024 publication from a January 2026 amendment: <https://environment.govt.nz/publications/new-zealands-second-emissions-reduction-plan/>. Its revisions must not be backdated as original wording.

## Recommended collection priorities

1. EU: enumerate the Work IDs underlying the known month counts and inspect English digital-content availability and subtypes. Prioritise earlier periods and source consistency. The all-topic index is useful as a source-specific denominator, even if full-text analysis later uses a validated relevant subset.
2. Ireland: calibrate target volume using 12–18 months selected across early/middle/recent periods, seasons and portfolio transitions, then acquire a bounded ministerial-answer series. Resolve grouped answers and publication dates before expanding the period. Use the archival debate route for older material only after a real record boundary is demonstrated.
3. NZ: enumerate the 536 known 2025 Climate Change records and establish reply/version dates; inspect adjacent years before projecting a multi-year total. Enumerate Beehive Environment/Climate Change/Energy portfolios and MfE publications as separate series. They can supplement institutional context; their counts cannot be silently spliced into parliamentary answers.

Additional jurisdictions expand geographical coverage. They do not fill a missing UK observation. EU institutions constitute a supranational level and should not be treated as an EU member-state sample. Each source needs its own issuer, genre, publication-date basis and denominator.

## What counts as enough data

No universal raw-record threshold establishes adequacy. The relevant quantities are unique parent documents/answer units, validated relevant parents within each time bin, effective information after duplication/clustering/weighting, and the number of comparable time points. Three million segments from a few long reports do not constitute three million independent observations.

The following are **proposed planning gates**, not demonstrated power results, university requirements or acceptance guarantees:

| Experiment | Initial planning target | Acceptance basis |
|---|---|---|
| Retrieval validation | Around 50 distinct held-out information needs; judge pooled lexical/dense top results, roughly 600–1,200 query–passage pairs after pooling, plus 200–400 separately sampled background units | Source/period-stratified uncertainty; avoid reference/test leakage; pooled relevance judgements do not establish absolute corpus recall |
| RQ3 similarity structure | Start with 500–2,000 source-balanced passages while retaining parent IDs and duplicate relationships | Stable groups under resampling/reference changes; inspect representative and contradictory passages; number is a manageable pilot size, not an inferential minimum |
| Monthly document-weighted Q | Seek 50–100 effective relevant parent units per source/role/month as a screening target | Interval width relative to the smallest meaningful change, dependence and measurement error decide resolution |
| RQ1 temporal comparison | Initially assess at least 60 comparable monthly bins; prefer about 96–120 for richer diagnostics and held-out prediction | Actual variance, serial dependence, model dimension, source stability and simulation determine feasibility; low-order models only when supported |
| RQ2 event analysis | Plan around 24 pre-event and 24 post-event monthly observations when source/event context permits | Effect-size/variance/autocorrelation-based power assessment; overlapping events and date uncertainty may prevent attribution |

Five years at 50–100 relevant independent parents per month implies **3,000–6,000 relevant parents per series**; ten years implies 6,000–12,000. These are arithmetic workloads conditional on the proposed screening target, not evidence of adequate statistical power. The government, media and public series must all support the chosen comparison window. Adding government data cannot repair missing public or media observations.

If relevant-parent yield is 5%, 100 relevant parents require approximately 2,000 eligible parents per month; at 1% yield, approximately 10,000. These are hypothetical yield scenarios. Measure actual yield first. If a genuine source census contains only 20 relevant documents, retain all 20 and their uncertainty rather than manufacturing additional information by rescaling or oversampling. Quarter aggregation changes the time resolution and lag interpretation; it does not create missing source coverage.

For an illustrative independent binary proportion near 0.5, approximate 95% margins of error are ±13.9, ±9.8, ±6.9 and ±4.9 percentage points at n=50,100,200,400. These do not describe model error, correlated documents, the whole population, or cosine-similarity uncertainty. Use appropriate binomial intervals for actual small-count estimates; see NIST <https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm>.

For document-weighted continuous similarity Q, a planning approximation is n_eff ≈ (1.96 × sigma / delta)^2. Hypothetically sigma=0.15 and desired half-width delta=0.03 imply about 97 effective independent parents. Estimate sigma and dependence from an actual pilot and use parent/duplicate-cluster resampling. Effective n from weights alone does not fully correct clustered or serial dependence.

ITS simulation research demonstrates why a fixed time-point minimum is insufficient: outcome frequency, per-period sample size, effect size and event location all matter. Its health-data numerical thresholds should not be transplanted into this NLP study. Source: <https://pmc.ncbi.nlm.nih.gov/articles/PMC6394245/>.

## Avoiding excessive normalization and noise

- Keep country/institution, genre, original publication date, language and channel visible. Compare like-for-like within source before attempting pooled summaries.
- Do not z-score unlike genres and infer that their levels are comparable. Do not use equal-size resampling or large weights to manufacture a sparse country's contribution.
- For attention S retain the eligible background denominator; for Q report the relevant-parent denominator. A corpus selected only by climate keywords cannot estimate climate attention in all government output.
- Aggregate passage scores to their parent before document-level comparison. Preserve joint-answer relationships, reuse links and revisions; separate retrieval instances from independent evidential units.
- Treat risk reporting, quoted fear, negation and actual fear/worry expression as distinct validation cases. Transformer similarity does not eliminate construct error or source bias.
- Frozen reference definitions, a fixed encoder within each comparison and source/period checks should precede interpretation. When uncertainty exceeds the effect of interest, narrow the claim or use a justified coarser window.

## Decision proposed for Dai

Prioritise EU for early institutional coverage, Ireland for a comparable English reply series, and NZ for bounded climate-portfolio and primary-policy evidence. Define one feasible shared period for government/media/public analysis before requiring every jurisdiction to support 1988–2026. Release criteria should report completed source scope, unresolved gaps, usable text and validation uncertainty. Total raw records alone cannot determine whether the thesis experiment is sufficiently supported.

Evidence files: `08_cross_region_government_coverage/eu_cellar_commission_preparatory_month_index.csv`, `ie_written_question_month_index.csv`, `ie_2012_09_question_answer_records.csv`, its saved raw answer responses, `nz_parliament_climate_answered_2025_month_index.csv`, `nz_parliament_answer_identity_sample.csv`. Existing proposal read for alignment only: `proposal/thesis_proposal.md`, especially RQ1–RQ3, Q/S definitions and source/period validation.
