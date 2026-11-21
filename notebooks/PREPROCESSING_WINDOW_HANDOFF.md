# Codex window handoff for chunk review

Notebook 05 provides the versioned parent texts and paragraph offsets. Notebook 06
prepares the reference chunk boundaries locally and identifies complex documents for
review. The coordinator assigns each selected complex parent in full to one Codex
desktop window in the same workspace. The default reviewer is GPT-6.2 Sol with Extra
High reasoning. The notebook only reads and writes local files.

## Start or resume the first assignment

1. Run Notebook 06 through **Prepare the first Codex window assignment**. Its output
   gives the versioned directory under `.cache/chunk-window-review/`. The bundle
   holds the shared `PACKETS.jsonl`, a line index, the batch assignment and the
   manifest. The manifest binds the source text, reference plan, selection and file
   hashes. Keep this directory and its receipts locally.
2. Send the reviewer the bundle path and `BATCH_001.json`. Verify the source SHA-256
   and read only the 1-based lines in the assignment. Check each packet hash against
   its assignment entry. The coordinator saves the window ID, source hash and
   receipt path in `DISPATCH_001.json`. Use that record to resume in the same
   window. All windows read the same packet file and receive disjoint parent rosters.
3. Review the proposed boundaries for attribution, negation, quoted speech, intensity
   and references to heat or temperature. Each packet contains the slice
   `[context_start, context_end)`. Its offsets refer to Unicode code points in the
   full parent. Subtract `context_start` when looking up a boundary in the slice.
   Make decisions within the assigned `[start, end)` range. Read every unit for an
   assigned parent to check continuity between units.
4. Write one JSON line per assigned packet to the designated receipt. Use
   `packet_sha256`, `reviewer`, `reviewer_version`, `status`,
   `selected_boundary_ids` and `reason`. For `accept`, copy the baseline IDs.
   For `adjust`, choose different IDs from the candidate list in ascending order.
   If the available boundaries cannot preserve the evidence, use `escalate` and
   an empty list. Explain the boundary decision and the evidence at stake.
5. Keep any partial receipt under a temporary filename in `decisions/`. On resume,
   check its packet hashes and continue with outstanding units. When the assigned
   roster is complete, publish the final receipt by atomic rename. Use one writer
   per receipt and retain each finished receipt for the coordinator.
6. Run **Validate a returned assignment** to verify the roster and replay each
   choice against the reference plan. A parent with an escalation or a resulting
   chunk above the reference token budget stays open. Count a parent as boundary
   review complete after all its units pass. The coordinator reruns cross-split
   checks when assembling an adopted set of chunks.

For the pilot, record completed and escalated parents, changes to proposed boundaries,
elapsed time and any context needed to make the decisions. Estimate full-queue time
from observed batch timings and document-size mix. The pilot covers a development
cohort. Track production coverage separately against the full complex review queue.

## Run the parallel pilot

[Notebook 07](07_parallel_chunk_review_pilot.ipynb) prepares the remaining 228 units in
12 disjoint batches of 19 under the bundle's `parallel-v1/` directory. Each uses the
same Notebook 06 packet file. Run the notebook in a fresh project kernel to replay
returned decisions against the versioned parents and reference plans.

The coordinator uses `dispatch/STATE.json` to track assignments and completed Codex
turns. A partial receipt is a checkpoint. Reassign a batch only after its previous
window has stopped writing, and have the receiving window check existing packet hashes
before reviewing outstanding units. The controlled Batch 002 relay retains its two
initial decisions and compares them with the final receipt. The notebook reports
parent-level outcomes and writes `PILOT_REPLAY.json` after all batches reconcile.
