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
status: retry_prepared_pending_operator
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

The operator starts the retry in Notebook 16 using **Run All**. The retry
uses the existing parameter grid, seeds, sample and validation panel.
The number of successful BERTopic retries will be recorded after execution.

The notebook input and report check recovered all 45 successful fits and all
nine attempt receipts. The revised BERTopic analyzer emitted every one of the
24,000 frozen vocabulary entries on the 19,998 training documents. The initial
validation comparison found nine shared host and format strata. They covered
1,017 of 1,552 early documents, 541 of 1,555 middle-period documents and 484 of
1,893 late documents. The date-conditioned topic fitting and BERTopic retries
await the operator's run.

### Research-question outputs

- **RQ1** is the immediate focus. The notebook reports topic composition by
  publication year and period, checks the original NMF fits, and measures
  support for a fixed host and format mix. The development pilot uses independent
  NMF windows, adjacent cosine and top-term alignment, and a temporally anchored
  NMF sensitivity. It exports validation shares, release-group bootstrap intervals
  and leave-one-host-out results, with exploratory false-discovery adjustment
  for early-to-late contrasts. The fitted pilot and alignment review govern any
  later projection to the 641,180-document screened training frame. Capture,
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
