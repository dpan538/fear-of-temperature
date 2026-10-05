# Government isolation log: writing and sealing rules

Dedicated log: [GOVERNMENT_ISOLATION_LOG.jsonl](GOVERNMENT_ISOLATION_LOG.jsonl). It records government input acceptance, qualitative closeout, independent audit delivery and its Git version anchor. Media requests retain their own acquisition records.

Isolation means a separate namespace, coordinating-auditor single-writer discipline and verifiable records. All windows share a filesystem; this is not OS permission isolation. Extraction windows provide factual evidence issues without modifying the log, frozen report or audit receipts. Reviewer source, hidden fixtures and credentials remain encrypted outside extraction.

Each entry has sequential`seq`, actual`recorded_at_utc` and`recorded_at_cst`, a separate`event_time_utc`, writer, event, evidence locator and facts. Historical events cite their original timestamps; records are not backdated. Unknown exact event times are null.

The hash chain uses UTF-8 JSON with sorted keys and compact separators. Calculate SHA256 after omitting`entry_sha256`. The first`previous_entry_sha256` is 64 zeros; subsequent entries reference the previous entry hash. `FREEZE_MANIFEST.json` binds the chain head, with the Git commit as an external version anchor. This detects inconsistency against that anchor; it is neither a digital signature nor access control.

After freezing, do not append to or rewrite this version. An authorised later government task creates a new version whose first entry references this file hash and chain head. Corrections are separate evidenced events; original errors and stops persist.

Never record passwords, keys, credential environment variables, private evaluator paths, hidden fixtures or optimisation score targets. Public figures and evidence receipts may be shared. This round accessed no evaluator source, decrypted nothing, created no evaluator plaintext and performed no new acquisition or formal database write.
