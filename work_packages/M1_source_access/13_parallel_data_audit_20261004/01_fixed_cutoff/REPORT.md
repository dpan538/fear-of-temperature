# Fixed cutoff and date-integrity audit

**Study interval:** publication dates **1988-01-01–2026-09-21 inclusive**; September 2026 is partial. **Audit type:** read-only metadata and callsite review. No collector, database, raw file, shared source code, proposal, or shared log was changed. The exact input file checkpoints, units, filters and ID conventions are in `INPUT_MANIFEST.json`; this report's counts come from `date_counts.json`, not the September 27 EDA atlas.

## Endpoint provenance

The 04 GOV.UK collection scope and 39-partition query ledger establish an inclusive September 21 Search API publication-date filter and an actual first enumeration observation **01:05:02–01:10:54 UTC on 2026-09-21**. The 04 enumeration summary was generated at **01:10:55 UTC**. Dai's 06 collection authorisation was recorded separately at **06:01:20 UTC** that day. These are different kinds of time. They support the already accepted **day-level publication endpoint** and a narrower first GOV.UK observation; they do not support one exact global extraction-start timestamp or end-of-day completeness. `DATE_CONTRACT.md` and `corpus_scope.json` make that distinction executable for future integration.

## Read-only metadata findings

| Input frame and checkpoint | Parent/Work unit | Stored publication-date result |
|---|---:|---|
| 06 UK DB, mtime 2026-09-22 13:37:31 UTC | 248,035 independent `documents` parents | 0 null, 0 before 1988-01-01, 0 after 2026-09-21 |
| 09 US/AU DB, mtime 2026-09-27 12:36:23 UTC | 33,544 selected Federal Register parents | 0 null/outside |
| Same 09 DB | 821 Australian **landing URL candidates** | 819 lack verified day-level original date; 2 have day-level dates inside scope; 0 stored days outside |
| 10 EU stage DB, mtime 2026-09-27 15:31:29 UTC | 50,578 distinct CELLAR Works and one recorded date row per Work | 0 before/after, invalid, source-month mismatch or multi-date Work |

The 09 DB also contains a copy of the 06 UK parents; it is **not** an additional UK corpus. These checkpoints are not synchronous. The US count is selected metadata, not necessarily readable bodies; the AU count is candidate landings, not 821 verified Works. EU Work date does not establish Item version fidelity.

The **938-row** `date_exceptions.csv` contains **819 AU original-date unresolved** candidates and **119 GOV.UK local-day/UTC-day differences**. The AU precision recorded in the 09 evidence table is 813 unknown, 4 month, 2 year among those 819. Two additional September 2026 month-only date candidates appear in the AU outcome ledger with raw originals pending; their day-level eligibility remains uncertain, and those candidate values are kept separate from verified DB evidence. Two AU CMS creation dates are after September 21, but CMS time cannot decide original Work eligibility. Preserve these candidates pending original-date evidence.

All 119 GOV.UK differences have raw `first_published_at` strings with `+01:00`: the stored DATE equals the source-local day, while the UTC-normalized timestamp falls on the preceding day. **Three** cross a month boundary: 2004-09-01 versus 2004-08-31; 2022-07-01 versus 2022-06-30; and 2022-09-01 versus 2022-08-31. Both dates for every discrepant row are inside the study interval. This is a **monthly-bin convention conflict**, not an observed post-cutoff publication or a reason to remove a source. The 06 coverage report describes a UTC publication day, whereas the ingestion uses the timestamp's local `.date()`. One source-day convention must be chosen and logged before recalculating monthly derivatives; the source strings should remain available either way.

## Entrypoint review

`callsite_audit.csv` inventories the relevant active reusable collectors/stagers and completed/legacy reports. The US Federal Register, EU CELLAR, Irish question index and UK historical routes use fixed September 21 bounds. `datetime.now()` and `date.today()` observed in those paths serve retrieval, retry or generated-report timestamps, not a rolling publication endpoint. Three specific integration risks remain:

1. The AU catalogue `within_cutoff` flag in the 08 harvester is actually based on **CMS creation time**; 08 coverage reporting uses it. Relabel it as metadata-only so it cannot masquerade as original publication eligibility.
2. The 09 pooled month report accepts Australian day/month evidence by `date[:7] <= '2026-09'`. A future evidenced September 22–30 day could enter the partial month. This is a latent guard issue; no such day-level AU row is in the queried DB.
3. The 10 EU stager selects manifest months through `2026-09` without its own day-level assertion. Its upstream query uses exclusive `2026-09-22`, and the staged dates currently pass; retain an exact-date validation at the staging/report boundary.

The 07 UK parliamentary ingester chooses `dateAnswered`/`dateMade` or a row-date fallback before storing a sitting date. The fallback count was not measured in this bounded audit; verify date-basis provenance before claiming exact answer/statement timing. The completed 06 coverage renderer has a hardcoded September 21 generated date; a future rerun should display its actual snapshot time while keeping the study endpoint fixed.

## Proposed next integration

1. Review `corpus_scope.json` and the small `boundary_filter.py` helper; apply an exact publication-date assertion to future staged/ingested tranches and the September 2026 monthly report paths. Keep exceptions rather than deleting candidates.
2. Decide whether GOV.UK monthly bins use the source-local publication day or UTC timestamp day. The 119-row ledger supplies raw strings and IDs; only three bins change month. Document the choice and perform one bounded derivative refresh, preserving both dates.
3. Rename the 08 AU CMS-based cutoff label and review only the two September-month original-date candidates and any further AU records needed for specific research windows. No broad recollection is implied.

Backfill discovered after September 21 can add eligible **older publication dates** to a later snapshot, with its later retrieval and content-version times recorded separately. It cannot move the endpoint or prove that a currently fetched body is the historical body. Extending the endpoint requires Dai's explicit decision and a new corpus version. Date integrity is a structural quality question; no climate/emotion relevance or fear eligibility was assessed here.

## Reproduction and limits

From the repository root, run `.venv/bin/python work_packages/M1_source_access/13_parallel_data_audit_20261004/01_fixed_cutoff/build_date_evidence.py` to regenerate the metadata exception ledger and count summary. Run `python3 work_packages/M1_source_access/13_parallel_data_audit_20261004/01_fixed_cutoff/boundary_filter.py` for eleven focused boundary examples. The SQL uses read-only connections and parent metadata only. A database file's modification time is a practical checkpoint proxy, not a transactional snapshot ID; a subsequent collection can change counts without changing this report's historical meaning. No body/version audit or live source query was performed.
