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
