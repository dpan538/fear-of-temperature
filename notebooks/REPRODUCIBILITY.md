# Local replay and experiment provenance

## What must match

Treat the code, local data snapshots, reviewer receipts and execution environment as
versioned inputs. Verify file SHA-256 values when reopening an existing snapshot.
Compare logical records when rebuilding. Spark can choose different part filenames,
row order and file metadata even when the records are equivalent.

| Checkpoint | Compare on a local replay |
| --- | --- |
| 01–02, environment and synthetic gate | Use the registered project kernel with the locked dependencies. Verify the fixture hash and the assertions in the notebooks. Keep the optional model path disabled for the default fixture replay. |
| 03–05, document preprocessing | Bind the same formal release and metadata fingerprints. Compare record keys, inherited splits, body hashes, offsets, hold reasons, known overlap evidence and reconciled counts. |
| 06–08, reference planning and frozen review scopes | Use the same PySpark profile, Notebook 05 handoff, reference tokenizer and pinned vocabulary. Compare parent IDs, offsets, exact token counts, hashed scope membership and occurrence holds. |
| 07–11, recorded semantic decisions | Restore the frozen assignments, packets, reviewer decisions and adjudication receipts. Replay them through the corresponding notebook cells. Compare the final per-parent offset, disposition and exact hold ledgers. A fresh reviewer pass is a separate measurement. |
| 12, reference text materialization | Compare the set of parent IDs, chunk ordinals, half-open ranges, slice hashes and split eligibility. The accepted reference checkpoint has 1,511,656 chunks and zero surviving exact cross-split groups. |
| 13, document EDA | Compare census and sampled parent rosters, ordered vocabulary and IDF, ordered sparse feature values, and aggregate statistics. The frozen fitted vocabulary fixes feature index order. A rebuilt vocabulary must have its own manifest and be checked for term or index drift before comparing models. |
| 14, training-side refinement | Compare the 494-case roster, original and proposed offsets, dispositions, paired packet hashes and projected exact cross-split counts. The file contains proposals with the recorded model-input status and semantic gate. |
| 15, local NMF | Use the same CSR matrix, feature order, parameters, seeds, software versions and linear algebra settings. Align equivalent components before comparing factors. The pilot uses relative tolerance `1e-8` and absolute tolerance `1e-10` for a saved run in the same recorded environment. |

## Local inputs and order

1. Open the project at the notebook checkpoint and select its Python 3.12 kernel.
   Use the locked project dependencies and the same local Java and Spark profile.
   Keep the separately pinned `tiktoken==0.14.0` and its checksum-bound local
   `cl100k_base` vocabulary when reopening the chunk reference. The existing
   [notebook guide](PREPROCESSING_START_HERE.md) specifies each input and run order.
2. Restore the formal release and its local body stores, then the needed derived
   snapshots. Keep the local review trees and receipt checksums with the backup.
   The [checkpoint](PREPROCESSING_CHECKPOINT.md) lists local locations and completed
   checks. The source-only repository backup carries the notebook code and summaries.
3. Reopen the existing snapshots for a receipt replay. Where a notebook supports a
   new output path, put a full rebuild into a separate versioned snapshot and compare
   its records to the frozen run before adopting it. Earlier immutable checkpoint
   artifacts are inputs to the comparison.
4. The original Notebook 11 snapshot binds the whole code-only notebook file SHA.
   Use the source copy from the backed-up checkpoint when validating that historical
   snapshot. Saving editor outputs into that particular file changes its file SHA.
5. Open [Notebook 15](15_unsupervised_research_plan_and_local_pilot.ipynb) to verify
   the listed checkpoint assets, the latest program-review packet and receipt hashes,
   and the ordered feature matrix in both Parquet file orders. Its default run keeps
   fitting disabled. The researcher starts a fit explicitly in the project kernel.

A checksum verification confirms the saved inputs and outputs. A new end-to-end
rebuild also requires the source snapshots and receipts at every upstream stage and
a comparison of the recomputed logical outputs. Record the scope that was actually
rerun in the experiment log.
