# Historical government acquisition

This work package extends the existing 06 DuckDB with bounded historical GOV.UK policy records and a separate House of Commons ministerial written-answer/statement series. It does not modify the proposal, clean or re-chunk the corpus, create embeddings, or run model analysis.

Authoritative database:

`../06_government_content_acquisition/fear_temperature_government_content.duckdb`

The recovery file under `recovery/` is a pre-expansion snapshot, not a second working corpus. The two aborted `/private/tmp/historical_ingest_smoke*.duckdb` files are diagnostics only and never count toward formal progress.

## Resume rules

- Run only one DuckDB writer at a time.
- Run only one Parliament network phase at a time. `BoundedClient` applies one aggregate request-start interval across its workers and records any 429 event under `reports/rate_limit_events.jsonl`.
- Re-running an acquisition phase validates and reuses saved raw files and fetch metadata. It does not redownload verified successes.
- Formal ingestion reads only acquired manifest records not already present under the stable source identity. Parliament records are prepared and committed in blocks of 1,000; policy publications are committed one at a time because two attachments are unusually large.
- A checkpoint and progress line are written only after `COMMIT` succeeds. `ON CONFLICT DO NOTHING` rows are excluded from new-row counts.

Typical resume commands, run from the project root with `PYTHONPATH=src`:

```bash
export PYTHONPATH=src
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py acquire-hansard-answer-details
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py enumerate-hansard-gap-answers
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py probe-hansard-gap-publications-archive
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py enumerate-hansard-gap-archive-answers
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py acquire-hansard-gap-archive-answers
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py enumerate-hansard-gap-statements
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py acquire-hansard-gap-statement-details
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py acquire-modern
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py ingest --source historic
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py ingest --source policy
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py ingest --source hansard
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py ingest --source hansard_gap
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/historical_government_acquisition.py ingest --source modern
.venv/bin/python work_packages/M1_source_access/07_historical_government_acquisition/build_reports.py
```

Do not use `all` as a routine resume command: source-specific phases make the network quota, acquisition state and formal commit boundary explicit.

## Provenance boundary

Historic Hansard per-record JSON is derived from an acquired official ZIP/XML volume. The database links each derived record to the parent volume content version and preserves its source locator. The 2010–2014 archive-answer JSON is likewise derived from an acquired official Commons HTML page and linked to that parent page and question anchor. The modern Questions/Statements API list responses already contain complete question/answer or statement fields; their per-record JSON is derived by official record ID and linked to the downloaded list response. None of these three routes invents a per-record HTTP request, status or MIME type. A stopped 1,000-record modern detail-path diagnostic is retained separately and is not counted as formal progress. For actual Hansard/API detail records, request URL, final URL, retrieval time, status and MIME type come from each saved `.fetch.json`. Formal ingestion time is stored separately from retrieval time.

Final tables, figures, the Markdown report and the compact HTML page are generated under `reports/`. The final audit workbook is generated under the task-specific `outputs/` directory after those CSVs pass reconciliation.
