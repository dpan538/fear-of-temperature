# Round23 newspaper package

Read `FINAL_REPORT.md` first. `SOURCE_ERA_AND_INTERFACE_REPORT.md` describes verified metadata, archive eras and unresolved route conditions; `ROLLOUT_PLAN.md` preserves the continuous calendar objective. The effective source registry retains 20 candidates across five strata. Coverage CSV blank numeric fields mean unknown, not zero publication.

## Local offline verification

From the repository root:

```sh
python3 work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/newspaper/tests/test_changed_chain.py
python3 work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/newspaper/prototype/build_ledgers.py
```

The tests use temporary synthetic payloads/databases and mocked transport. They do not collect newspaper bodies. The ledger command reads only this owner's small staging database. The diagnostic repair command, if rerun, reads exactly the named frozen Texas Tribune raw object, preserves old files and writes a new dated execution receipt; it remains a non-newspaper diagnostic.

## Collection API

The callable interface is `pipeline.freeze_frame(source, month, discovery_receipt, candidates, native_order=...)`, `inspect_target(frame_path, gate_path, adapter)` and `stage_reviewed(inspection_path, source_record, review_path)`. Candidates require article native IDs, URLs and publication days already verified from native discovery; an issue URL is not an article. No caller-supplied ID whitelist marks completion. The adapter includes an explicit selector, exclusions and boundary evidence; generic parser fixtures are not source validation.

A public-route gate is a reviewed JSON record in this package with `source_id`, `access_state=public_route_permitted`, allowed `public_hosts`, `changed_parser_validated` and any stricter `minimum_interval_seconds`. Supporting policy/date/identity evidence belongs beside it. No such production gate is shipped. Preparation robots code cannot clear a source by itself. Metadata and body requests are bounded independently of parser success. Exact stopped/saved request IDs are restart-stable and do not refetch silently; a later authorised recovery needs an explicit new bounded request version, not deleting receipts.

Recovery uses `request_version`, `previous_request_id` and `recovery_reason` keyword arguments on `fetch` or `inspect_target`. It must keep the same frozen source/URL/purpose, preserves and hashes the earlier receipt, and reruns the actual budget/access/deadline checks. Counters and cooldowns persist. The fixture proves that a capacity recovery can save a new request version while the earlier failed receipt remains unchanged; it does not demonstrate improved real disk space or a live newspaper recovery.

The reviewed article file binds raw/body/parser/adapter hashes and true structural checks for newspaper identity, independent article parent, publication-date mapping, complete visible prose, issue/page separation, body boundary and provenance. Retention and source-work rights must already be applicable. The staging record has source/native article identity, acquisition parent, stratum/country/edition and day/precision. Content versions keep raw/body paths and hashes, exact parser hash, retrieval time, content-version time if known, and unresolved historical equivalence. The fixed cutoff is checked again at staging.

`staging/newspaper.sqlite3` currently contains one diagnostic parent and two derivative versions, and zero qualified newspapers. `manifests/` exports that lane explicitly. Do not import it into government databases or add it to newspaper/month coverage. `control/CONTINUATION_CURSOR.json` identifies the unstarted newspaper rollout and its actual stop. Worker outputs are owned here only; coordinator owns shared logs, root controls, acceptance and Git.
