---
experiment_id: FOT-B-261122-001
sample_batch: FOT-DOCDEV-20K
date: 2026-11-22
timezone: Asia/Shanghai
notebook: 16_document_unsupervised_comparison.ipynb
original_release: formal-corpus-release-20261117-v1
original_run: ee0a82a0e8ce8f3b90d0
original_report: report-842561b77f1a17
original_report_manifest_sha256: 0751e84a5162ce577239953d5dab7e983803196bce27bdcedc37d15d9c23c46c
planned_fits: 54
verified_initial_fits: 45
initial_failed_attempts: 9
status: technical_run_complete_research_measurement_unvalidated
approved_primary_prevalence_model: null
full_frame_projection: deferred_pending_validation
---

# Document comparison experiment log

## 22 November 2026

The local run used the same 20,000 sampled development documents from Notebook 13.
Two zero-feature documents were excluded from the common training matrix. The
comparison used 19,998 fitted documents, 5,000 held-out validation documents
and seeds 1729, 2211 and 4021. The test split remains reserved. The first report
sealed at **17:15:58 UTC+08:00** with 45 verified fits across five model families.
All nine BERTopic configurations failed.

Among the verified configurations, NMF-16 had the highest mean validation NPMI
(0.2936), 99.98% assignment coverage and a common-assignment ARI of 0.9995.
NMF-12 remains the registered comparison reference. The NMF-16 topic drill-down
is exploratory and was chosen after inspection of the first results.

### Initial failures

All times are on 22 November 2026 in Asia/Shanghai (UTC+08:00). The start time
comes from the JSON receipt. The write time is the local file modification
timestamp observed after the run.

| Configuration | Attempt started | Failure receipt written |
| --- | ---: | ---: |
| `bertopic-20-seed1729` | 16:54:15 | 16:54:46 |
| `bertopic-50-seed1729` | 16:54:46 | 16:55:06 |
| `bertopic-100-seed1729` | 16:55:06 | 16:55:25 |
| `bertopic-20-seed2211` | 17:04:16 | 17:04:35 |
| `bertopic-50-seed2211` | 17:04:35 | 17:04:55 |
| `bertopic-100-seed2211` | 17:04:55 | 17:05:14 |
| `bertopic-20-seed4021` | 17:14:04 | 17:14:23 |
| `bertopic-50-seed4021` | 17:14:23 | 17:14:42 |
| `bertopic-100-seed4021` | 17:14:42 | 17:15:01 |

Each attempt raised `ValueError: Input contains infinity or a value too large
for dtype('float64').` BERTopic 0.17.4 stripped Unicode and apostrophes from
its grouped topic documents in English mode. It used the raw input for the
representative-document vectorization. Of the frozen 24,000 terms, 514 could
appear under the raw analyzer but could never appear after the ASCII cleanup.
An absent column receives an infinite class-based inverse frequency, which
then reached cosine similarity when a representative document emitted the term.

The tracebacks and exact attempt digests are preserved under the original local
run's `attempts/` directory and indexed by its report manifest. The original
fit and report files remain the evidence for this entry.

### Retry design

Notebook 16 uses Unicode-preserving BERTopic text handling and keeps the
original ordered vocabulary entries emitted by that analyzer on the bound
training documents. The BERTopic receipts record the resulting vocabulary
fingerprint. The comparison binds the existing 45 successful fits, MiniLM
vectors and SVD artifacts to the original protocol and uses a new registry for
the retry. Each report exports `failure_history.csv` with both initial and
retry attempts, and future failures record both UTC start and failure times.

The operator started the retry in Notebook 16 using **Run All**. The retry
used the existing parameter grid, seeds, sample and validation panel.

The notebook input and report check recovered all 45 successful fits and all
nine attempt receipts. The revised BERTopic analyzer emitted every one of the
24,000 frozen vocabulary entries on the 19,998 training documents. The initial
validation comparison found nine shared host and format strata. They covered
1,017 of 1,552 early documents, 541 of 1,555 middle-period documents and 484 of
1,893 late documents. The completed temporal pilot and BERTopic retry are
recorded below.

### Research-question outputs

- **RQ1** is the immediate focus. The notebook reports topic composition by
  publication year and period, checks the original NMF fits, and measures
  support for a fixed host and format mix. The development pilot uses independent
  NMF windows, adjacent cosine and top-term alignment, and a temporally anchored
  NMF sensitivity. It exports validation shares, release-group bootstrap intervals
  and leave-one-host-out results, with exploratory false-discovery adjustment
  for early-to-late contrasts. Contextual measurement validity, temporal support
  and alignment govern any later projection to the 641,180-document screened
  training frame. Capture,
  version and verified event covariates remain pending. A separate STM or DMR
  experiment can estimate covariate-dependent topic prevalence directly.
- **RQ2** produces a training-only contextual review roster from low- and
  high-margin NMF assignments. Affect classification accuracy and calibration
  require independent annotations.
- **RQ3** audits the provisional event registry and validation-year coverage.
  Event comparisons await independently evidenced dates and frozen windows.

The working cultural-learning hypothesis requires longitudinal, contextual
and historical evidence beyond the unsupervised document comparison.
[Accepted research questions](../2026-11-13-corpus-release/RESEARCH_QUESTIONS.md)

### Completed retry and research decision

The retry report sealed at **19:18:33 UTC+08:00** on 22 November 2026. Its local
registry is `faba1e820b243b531d3f` and its report is `report-734728858f6801`.
The report manifest SHA-256 is
`a67c631c9947033e221107db66156e96d000c21b2ca83bbd431b14a167855b30`.
All 34 listed report files passed checksum verification. The report contains
54 verified fits, comprising 45 reused fits and nine successful BERTopic retries.
The failure history retains the nine first-run failures.

| Configuration | Validation coverage | Unassigned share | Seed-pair ARI |
| --- | ---: | ---: | ---: |
| BERTopic-20 | 57.55% | 42.45% | 0.989 |
| BERTopic-50 | 58.64% | 41.36% | 0.980 |
| BERTopic-100 | 72.03% | 27.97% | 0.349 |

The BERTopic-20 and BERTopic-50 ARIs are computed on mean jointly assigned
shares of 49.74% and 51.18%. BERTopic-100 yielded a mean of 25.7 validation
topics with a standard deviation of 19.6. BERTopic may guide local evidence
review. Primary prevalence estimation remains unapproved.

**Measurement decision.** The completed comparison is an exploration of corpus
structure and discourse vocabulary. The original interpretation gave too much
weight to NMF-16's NPMI and seed agreement. Frequent function words, pronouns,
sports discussion and host-specific styles occupy multiple components. The
climate-related components identified in the focus readout largely concern
politics, warming, carbon tax and energy. Their affect and Fear content has yet
to be established using contextual evidence. The scorecard does not apportion
NPMI between substantive vocabulary and common or overlapping expressions.
NMF agreement was measured across seeds on one fixed sample with the same
initialisation strategy and solver. Sampling and initialisation sensitivity
remain untested. No model has passed a substantive prevalence or affect gate.

**RQ1 remains open.** Source and format standardisation covers only nine
shared strata. Late-period support is 484 of 1,893 validation documents
(25.6%). Sixteen of 32 adjacent matches require review. Static component IDs
and time-window IDs are separate. Window slots 3 and 13 have first-transition
cosines of 0.0098 and 0.0414. Window slot 11, which carries climate and warming
descriptors, has adjusted shares of 2.746%, 0.607% and 1.433% in the anchored
sequence and 2.746%, 0.468% and 1.300% in the independent sequence. These
are topic shares within the supported source mix. Capture process, text
version and event exposure remain outside the adjustment. Current claims are
limited to differences in observed discourse composition and evidence of
alignment and coverage constraints.

**RQ2 remains open.** The 96-document roster supports a first codebook and
annotation exercise. The sampled topic and margin values are selection
metadata. Reliable recognition of somatic or indirect affect, worry and Fear
requires independent contextual labels and subsequent calibration and held-out
evaluation. The roster supplies no measured classifier performance.

**RQ3 prerequisites.** The four provisional events still lack approved dates
and frozen analysis windows. Zero event comparisons ran. Event composition
therefore also remains pending for RQ1.

### Gate for the next RQ1 pilot

Keep the development sample and successful fits as comparison evidence. Before
using a model to estimate full-frame prevalence, define the outcomes for climate
relation, the object of affect, worry and Fear and review positive examples,
ambiguous examples and counterexamples. Include sports and generic first-person
language in the counterexamples. The 96-document roster is suitable for testing
the coding protocol and can be supplemented with targeted cases across independent
sources and formats.

A measurement candidate must show contextual validity, source sensitivity and
stability under resampling and alternative initialisation before temporal
application. Report topic drift, support coverage and the capture, version and
event covariate status with any estimate. The full screened training frame of
641,180 documents is a later application. Cultural learning and transmission
require separate evidence of recurring expressions, attribution, circulation or
cross-source timing together with contextual reading.

### Hypothesis-driven revision, 22 November 2026

Notebook 16's default workflow now measures explicit heat-linked text cues
and prepares an independent review of their interpretation. The archived
six-family exploration remains at checkpoint `2f685da`, with all 54 completed
fits and the nine earlier BERTopic failure receipts preserved locally. Its
internal scores did not establish a measure of affect or cultural learning.

The default cells were replayed at **20:04 UTC+08:00** in the local project kernel on the frozen
19,998-document development cohort and 5,000-document validation panel.
The 80-codepoint rule matched Fear cues in 8 validation documents and worry
cues in 5. Counts by period were 3, 3, 2 and 2, 2, 1 respectively. For each
of these two cues the common-support analysis had one early and zero late
matches. The contrast table marks their bootstrap intervals unavailable.
The rule matches provide review targets. Their interpretation and sensitivity
to indirect expressions require human annotation.

The report also includes 140 training-only review documents from distinct
release groups, a blank review form, evidence offsets, annual counts, both
distance settings, and control comparisons. Its private manifest is
`.cache/hypothesis-document-pilot/30c3c906dd7852b2a844/MANIFEST.json` with
SHA-256 `c6eb93bc258fbc7dbd54f439436aa427b05134189a949044b8dfb3b8e957af31`.
The affect measurement status is `awaiting_independent_adjudication`.
The optional learning cell passed a synthetic check for separate split metrics,
uncertain labels, and rejection of invalid evidence offsets. Zero real-data
models were fitted in this revision. Event adjustment and full-frame inference
remain pending.
