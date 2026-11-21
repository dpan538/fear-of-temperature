# Verified preprocessing checkpoint

This checkpoint records the formal-release preprocessing and offline calibration preparation
completed on 21 November 2026. Notebooks and configuration are backed up here. Corpus stores,
per-record ledgers and review packets are local research assets. The pinned snapshots below
make the applicable inputs explicit.

## Completed scope

| Notebook | Verified result |
|---|---|
| 01 | Workspace and synthetic fixture gates passed in the project kernel. |
| 02 | The default synthetic run passed with 37 input rows, 36 canonical passages and one exact copy. |
| 03 | 718,330 formal parents have normalized metadata and structured bodies. The overlap extension marks 1,801 parents across inherited splits. |
| 04 | The first pass edited 1,741 parents. Both 1,200 and 2,400 code-point plans passed coverage checks. |
| 05 | The final handoff reconciled 718,330 body hashes, paragraph ranges and both baseline plans. The incremental search exactly scored 1,993 cross-split candidates involving the 139 residual edits and found zero newly matching pairs within the candidate search. |
| 06 | The baseline and overlap diagnostics ran locally. The paired pilot freezes 240 review units from 177 complete parents. The fixture rehearsal recovered 480 receipts across four durable batches with zero duplicate submissions. |

Validation at checkpoint included a fresh default run of Notebooks 01 and 02, ten focused
unit tests, Ruff, the offline lock check, and 567 local Parquet file and row-count
checks across the verified snapshots. The public notebook copies preserve the executed code.
Outputs regenerate from the corresponding inputs.

## Local inputs for resuming the work

Use `uv sync --locked --extra notebook --extra spark` in the project environment and an
appropriate local Java runtime. Use the project Python kernel. [Start here](PREPROCESSING_START_HERE.md)
describes the notebook order and output locations. The optional Notebook 02 model path uses the
project's separately provisioned NLP snapshots and dependencies.

Restore `data/processed/corpus_releases/CURRENT_RELEASE.json` together with the local
formal release and metadata under `work_packages/formal_corpus_release_20261117/`.
Use the manifest hashes to verify the local inputs before reuse. Treat the following paths
as local snapshot locations relative to the project root.

| Local snapshot | Manifest SHA-256 |
|---|---|
| `work_packages/formal_corpus_release_20261117/structure-v2` | `272a85a0e68a489f358036edd8f9aad9ac0931c27b462a56d239b2cd29494a75` |
| `work_packages/formal_corpus_release_20261117/structure-v2-overlap-v1` | `b3b8cf0bb6de93e16dba3c33410b8403f7d25ed56b295ab93dc58f6b9e81ea7e` |
| `data/processed/preprocessing/formal_first_pass_v1` | `9f91fc9e59815ea681499b67271f531e12fce0ea5d76b97d4b3370e532747848` |
| `data/processed/preprocessing/formal_layout_step_v1` | `4258c1f4873b9abf9ba91209fc3681f70355eb1fcf8d19a44f94053ea3163ab1` |
| `data/processed/preprocessing/formal_layout_step_v1_residual_v1` | `d490e743b9ee8bb33cfc1817dd9eb33b54fd3acbbc5bdf16f476f597a4b362fb` |
| `data/processed/preprocessing/formal_layout_step_v1_handoff_v1` | `ff507ad49c929a8352669e93e46151371a64b280857010559aecb38c639bbfcf` |
| `data/processed/preprocessing/formal_layout_step_v1_handoff_v1_near_delta_v1` | `b838961c77d1b4113fbf6379fc89b49831d1144547ae82e3b1f95bd547d22d79` |
| `data/processed/preprocessing/formal_layout_step_v1_handoff_v1_chunk_review_v1` | `80ec3a0a745bf5c810432b2fe6f6051e095fb64c6ab43f33c36eeea35863b526` |
| `data/processed/preprocessing/formal_layout_step_v1_handoff_v1_chunk_review_v1_calibration_v1` | `36fae27dc5de8e463dd64f2a2ea2b9073df5821fed5b60325165064a3890da6c` |

## Continuing from the checkpoint

The paired pilot row describes the historical offline checkpoint. For current work use the
[Codex window handoff](PREPROCESSING_WINDOW_HANDOFF.md) and the reference plan produced by
Notebook 06. The local window assignment and its verified receipt determine pilot progress.
Record the next repository checkpoint after the corresponding stage has passed validation.

## Verified parallel development pilot

Notebook 06 verified 1,526,588 reference chunks across 718,330 parents. Notebook 07
replayed all 13 development pilot receipts, covering 240 units in 177 complete parents.
The reviewers accepted 134 proposed unit plans and adjusted 106. All 177 parent plans
passed coverage and the 512-reference-token budget. The controlled handoff preserved
two original decisions and added 17 decisions in a different window.

Three GPT-6.2 Sol Extra High windows reviewed the remaining 228 pilot units over
15 minutes and 24 seconds, measured from the first dispatch to the last completed
review turn. The observed aggregate rate was 888.3 units per wall hour over this run.
The pilot contains a deliberately selected development cohort. Production review
coverage and sustained throughput require separate measurement.

## Completed targeted review sample

Notebook 09 replayed the complete frozen sample of 4,635 parents. It reconciled
77 earlier parent reviews and 177 additional batch receipts covering 4,558 parents
and 8,293 windows. The final handoff retained all 26 checkpointed decisions in the
affected receipt. Bulk desktop review from the first new dispatch to the final receipt
took about two hours and 26 minutes across three Codex windows.

The reconciled dispositions are 4,318 boundary reviews complete, 204 semantic
escalations, 112 reference-token budget reviews, and one explicit model-input hold.
The five independent first-batch adjudications accounted for four retained reference
plans and the explicit hold. The weighted first-pass material-finding shares were
43.2% for the nonparagraph sample and 11.2% for paragraph and terminal controls.

The sample-reviewed candidate contains 1,527,714 chunks. Its exact chunk scan
found 444 cross-split groups and zero surviving groups after applying the candidate
occurrence holds. Adoption remains a separate decision after open cases and the
downstream tokenizer have been evaluated.

## Completed full nonparagraph review

Notebook 10 replayed all 16,540 nonparagraph parents. It reused 4,135 completed
sample reviews and reconciled 484 new receipts covering 12,405 parents and 22,727
targeted windows. The new decisions comprise 16,564 accepts, 5,132 adjustments,
and 1,031 escalations. Two mid-run handoffs preserved 13 checkpointed decisions
byte-for-byte. The elapsed time from the first new review receipt to the final
receipt was about four hours and 35 minutes, with three windows in the first
wave and six after the controlled handoff.

All 204 original semantic escalations and all 112 original reference-budget
cases have verified dispositions. The former account for 152 repairs, 38 retained
reference plans, and 14 explicit model-input holds. All 112 budget cases received
verified repairs. In the full nonparagraph scope, 15,589 parents passed boundary
review, 15 have explicit holds, and another 936 remain outside model-input
eligibility pending review. Those 936 comprise 691 semantic escalations and 245
reference-budget cases discovered during the expanded review.

The revised candidate contains 1,530,300 chunks and 437 exact cross-split groups
before holds. A bound ledger of 2,101 held occurrences reduced the exact
cross-split group count to zero. This checkpoint records the reference-token
candidate. Model-specific tokenizer checks and the remaining review decisions
govern adoption.
