# Preprocessing: start here

Notebook 04 applies the fixed first preprocessing pass to all 718,330 eligible records in the
verified Notebook 03 release. It keeps an edit ledger for text changes and compares two
paragraph-based chunk budgets on the same records. The output reports show which expressions
the rules watch, the edits and review flags by source and format, and chunk statistics by format
and document length.

## Run Notebook 04

1. Open the project root in VS Code, or use the root workspace file
   `fear-temperature-preprocessing.code-workspace`.
2. Open [Notebook 04](04_preprocessing_spark_local6.ipynb) and select the
   **Python (Fear of Temperature)** kernel from the project `.venv`.
3. In Notebook 03, publish `structure-v2-overlap-v1` first. Then use **Run All** in Notebook 04.
   It starts local Spark, runs text and chunk regressions, and verifies the input files.
   A completed first pass with matching source and rules is verified and reused.
4. Inspect the results and the record and chunk views in the final cells. Shut down the kernel
   after inspection.

The default inputs are the `metadata` and `paragraph_records` Parquet tables under
`work_packages/formal_corpus_release_20261117/structure-v2/`. The default output is
`data/processed/preprocessing/formal_first_pass_v1/`. Set `FOT04_OUTPUT` before opening
the kernel to use a new run directory directly under `data/processed/preprocessing/`
for an altered policy.

## Local Spark profiles

Set `FOT04_PROFILE` before starting the kernel. Profile definitions are in
`configs/preprocessing_notebook.json`. Restart the kernel after changing the profile.

| Profile | Spark master | Driver JVM heap | Shuffle partitions |
|---|---|---:|---:|
| `daily` | `local[2]` | 2 GiB | 4 |
| `balanced` | `local[4]` | 3 GiB | 8 |
| `local6` (default) | `local[6]` | 4 GiB | 12 |

Total memory includes the JVM and the Python workers. Runtime files are kept under
`.cache/spark_preprocessing/`. The notebook can use the Spark and notebook dependency
extras from the project lockfile.

## Output

- `records/` contains one row per parent, including the input and cleaned SHA-256 values,
  record and split keys, edit evidence, watched expression counts and both chunk offset plans.
- `AUDIT.json` records counts by rule, source and format, inherited splits, the targeted
  expression checks, and chunk statistics.
- `MANIFEST.json` records the input and policy hashes, Spark profile and checksums for the
  published parts.
- `formal_first_pass_v1_quality_v1.json` binds the first-pass manifest to the verified
  overlap snapshot and records overlap states by split and upstream review reason counts.
- In the notebook, `preprocessed_records` exposes the complete cleaned text and publication
  metadata. The `chunk_offsets` and `preprocessed_chunks` views expose the two chunk plans
  and their optional text slices. All chunk offsets refer to the SHA-bound cleaned parent.
  The reading views also inherit the upstream review reasons and overlap evidence.
  The reporting cells quantify the saved operations, describe complete record lengths and
  format composition, and compare the two chunk plans by format and parent length.

## Verify the frozen corpus and source-use inventory

[Notebook 03](03_structure_normalization.ipynb) reconciles the normalized roster
with `formal-corpus-release-20261117-v1`. It writes the reference metadata index for
67,222 historical source-use holds, the 732 exact native-body matches to that archive,
and the canonical release inventory in `structure-v2-source-use-v1/` alongside its
structural snapshot. The inventory has 722,160 distinct native bodies, including
4,826 from structural holds. The database retains all 723,158 source records and
their provenance. The frozen formal catalog assigns 646,414 train, 36,110 validation
and 35,806 test records.

## Historical main-training baseline

The earlier [main-training notebook](../archives/04_preprocessing_main_train_baseline.ipynb)
preserves the historical scan and light-cleaning code for its 614,519-eligible-record cohort.
Its previous result remains under `data/processed/preprocessing/light_urls_v1_20261113/`.
See [training scan and negation policy](../docs/research/2026-11-13-prechunk-pilot/TRAINING_SCAN_AND_NEGATION.md)
and the [eligibility audit](../docs/research/2026-11-13-preprocessing-eligibility-audit/README.md)
for the earlier denominators and review evidence.


## Handoff to Notebook 05

[Notebook 05](05_preprocessing_refinement.ipynb) uses the verified 04 first pass and
the 03 structure and overlap snapshots. Run it in a fresh project kernel. It shares
Notebook 04's `local[6]` default, with `FOT05_PROFILE` available as an override. Its first
step repairs extra line feeds at recorded structural edit boundaries and rebuilds
both chunk plans for changed parents. The final cells report the measured changes.

The compact snapshot is under `data/processed/preprocessing/formal_layout_step_v1/`.
Use `layout_records` for the record keys, edit ledger, plans and overlap evidence.
Use `layout_text_records` to reconstruct the complete body. Set `FOT05_OUTPUT` to a
new sibling directory when changing the policy.

Step 2 scans the complete formal roster for residual markup and publishes a second snapshot
at `data/processed/preprocessing/formal_layout_step_v1_residual_v1/`. It records counts by
source and format, replayable edits for two verified markup patterns, revised paragraph and
chunk offsets, and an exact cross-split check on new body hashes. Its edit offsets refer
to the Step 1 text. Use `refined_text_records` for the combined result.

The complete handoff is under `data/processed/preprocessing/formal_layout_step_v1_handoff_v1/`.
It includes one text row per formal parent with a body hash, publication metadata, paragraph
offsets, both baseline plans, residual marker counts and overlap evidence. `05_CLOSURE.json`
records the corpus-wide validation and the exact cross-split body check for each edit step.
Every Notebook 05 replay also compares all handoff keys with the normalized formal roster
and recomputes the SHA-256 and code-point length of every derived body.
The Parquet files are local, derived research data.

The neighbouring `formal_layout_step_v1_handoff_v1_near_delta_v1/` snapshot compares
the 139 Step 2 edits against the complete before and after rosters using the bound
five-word-shingle index. Its audit reports candidate coverage and exact pair scores.

## Run Notebook 06

[Notebook 06](06_chunk_evaluation.ipynb) reads and verifies the published 05 handoff in a
fresh project kernel. It measures both baseline plans, provides a separate view for known
parent overlap and counts exact chunk reuse across the existing splits. Set `FOT06_INPUT`
to select another verified handoff directory under the preprocessing root. The profile
defaults to `local[6]` and can be overridden with `FOT06_PROFILE`.

Notebook 06 publishes `formal_layout_step_v1_handoff_v1_chunk_review_v1/` for the 1,200
code-point baseline. It queues every parent in the declared complex scope and binds review
windows to the source text and baseline plan. Set `FOT06_COMPLEX_SOURCE_IDS` to add whole
sources by ID, and `FOT06_REVIEW_OUTPUT` to a new sibling directory for a revised scope.
The decision validator checks every unit before assembling an accepted parent's offsets.

The full reference candidate is published beside the 05 handoff with the suffix
`_reference_chunks_v1`. It records Unicode offsets and exact `cl100k_base` token
counts under a 512-content-token budget. Use `tiktoken==0.14.0` and the pinned
local vocabulary for this comparison. A downstream model can require a different
tokenizer and budget. Notebook 06 recomputes exact cross-split chunk reuse on this plan.

Notebook 06 freezes 240 reference-plan review units from complete development parents.
The coordinating Codex desktop window dispatches a small batch of selected parents to
another window in the same workspace. Both use the same read-only packet file. See the
[window handoff](PREPROCESSING_WINDOW_HANDOFF.md) for batch assignments, review receipts
and continuation. Routine boundaries come from the local planner.

The Notebook 05 research handoff records the later unsupervised, self-supervised and
supervised experiments.

## Run Notebook 07

[Notebook 07](07_parallel_chunk_review_pilot.ipynb) partitions the existing frozen
development pilot into disjoint assignments for parallel Codex desktop review. It
checks window receipts, replays the resulting boundaries on the original parent text,
and reports the handoff and duration. See [window handoff](PREPROCESSING_WINDOW_HANDOFF.md)
for checkpoint and dispatch details.

## Run Notebook 08

[Notebook 08](08_targeted_chunk_review.ipynb) measures nonparagraph boundary risk
on the full reference corpus. It freezes the targeted sample and paragraph controls,
publishes an exact cross-split hold ledger, and prepares a small first review tranche
for the existing Codex desktop windows. The paragraph-only fallback retains oversized
paragraphs with an explicit hold from token-limited use. The candidate receipt records
which decisions remain open before adopting a chunk policy.

The default `sample-001` batch uses training parents from the frozen samples and
emphasizes paragraph controls from News and Article. Set `FOT08_REVIEW_BATCH=diagnostic`
in a fresh kernel to open the earlier 47-window diagnostic. For `sample-001`, the final
cells replay the decisions and check newly formed training slices against the unchanged
validation and test reference chunks.

## Run Notebook 09

[Notebook 09](09_targeted_sample_review.ipynb) binds all 4,635 frozen sample
parents to the review ledger. It registers verified receipts from the diagnostic
and first sample batch, stages the remaining assignments in three Codex reviewer
lanes, and replays batches after they return. Use the local `PROGRESS.json` for
replayed parent dispositions and the lane checklists for resumption. The first
sample batch's five adjudications retain their original receipts and record the
independent verified outcome.

## Run Notebook 10

[Notebook 10](10_full_nonparagraph_review.ipynb) expands semantic review to all
16,540 frozen nonparagraph parents and independently resolves the 316 open cases
from the sampled parents. It retains earlier receipts, gives each window a
disjoint review lane, and distinguishes a verified repair from an explicit
model-input hold. The final cells reconcile the full target and recheck exact
cross-split chunk reuse on the revised candidate.

## Run Notebook 11

[Notebook 11](11_program_chunk_qa.ipynb) applies the whole-parent exclusions
and rechecks exact chunk reuse. It freezes 1,500 program-only QA parents in
`.cache/chunk-policy-review/program-chunk-qa-v1`. Completed batch receipts are
under `decisions`. Review assignments and resumable partial receipts are under
`dispatch`.

## Run Notebook 12

[Notebook 12](12_reference_chunk_materialization.ipynb) writes and verifies
the reference text slices under `.cache/chunk-materialization/reference-v1`.
The manifest binds the input snapshots and split-specific Parquet parts.
Model-input eligibility requires semantic QA and validation with the selected
model's tokenizer and input limit.

## Run Notebook 13

[Notebook 13](13_document_eda_and_unsupervised_preparation.ipynb) describes the
formal records, verifies the completed chunk QA receipts, and prepares a
training-only document cohort for unsupervised experiments. It applies the Notebook 03
source-use holds with the existing overlap and chunk input holds. The local snapshot
in `.cache/corpus-eda/document-eda-v3-source-use` contains figures, source tables, the
20,000-document development cohort drawn from 641,180 eligible canonical training
documents, and its fitted vocabulary and sparse TF–IDF features.

## Run Notebook 14

[Notebook 14](14_paragraph_boundary_refinement.ipynb) applies a bounded paragraph
search to training-side material findings from the completed program-only QA
sample. It retains the original plans and ranks alternatives by reported
evidence boundaries, new context risks, and the number of changed edges.
The local snapshot in `.cache/chunk-refinement/paragraph-v2` contains the trial
ledger, the exact-reuse check, and paired packets for semantic review. Offset
adoption requires the paired review and the model input checks.

## Plan and run Notebook 15 locally

[Notebook 15](15_unsupervised_research_plan_and_local_pilot.ipynb) records the
exploratory research hypotheses, verifies the document feature matrix, and
provides the first NMF pilot. The fit is disabled by default. The researcher
sets the run switch and starts the final cell in the project kernel.
The [local replay guide](REPRODUCIBILITY.md) specifies which artifacts and
results to compare when replaying or rebuilding earlier stages.

## Run the document comparison locally

Open [Notebook 16](16_document_unsupervised_comparison.ipynb) in the project
kernel and use **Run All**. The notebook retains all 54 planned configurations.
When the original checkpoint verifies, it reuses 45 saved fits, the MiniLM
vectors and the SVD representations and starts the nine BERTopic retries.
The comparison uses the same 20,000-document development cohort and frozen
validation boundary. [Dated experiment log](../docs/research/2026-11-22-document-comparison/EXPERIMENT_LOG.md)

The RQ1 cells check NMF convergence, source composition and common support,
then run the 20K temporal alignment and adjustment pilot. Use
`FOT16_TEMPORAL_PILOT=0` before starting the kernel to run just the comparison
and evidence-readiness cells. The temporal cache has its own manifest. RQ2
produces a training review roster, and RQ3 records which event evidence remains
pending.

The local run directory under `.cache/document-model-comparison/` contains
shared representations, fitted estimators, document assignments, component
terms, per-run metrics, failures and versioned PNG/PDF reports. The report's
failure history includes the dated initial and retry attempts. Rerunning a
seed verifies and skips its completed fits.
