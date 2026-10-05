# Media precollection package

Start with [HANDOFF_zh.md](/Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/02_media_precollection/HANDOFF_zh.md). The actual article manifest is empty; 150 frozen slots are unfilled. The saved HTTP200 object is an access challenge, not readable catalogue/article content.

- Scope: SOURCE_SELECTION_FROZEN.csv / PILOT_SCOPE.json / PROPOSAL_GEOGRAPHY_MAP.csv / INPUT_RECEIPT.json.
- Access and actual evidence: OFFICIAL_EVIDENCE.csv / WEB_ROUTE_CHECKS.csv / REQUEST_LEDGER.csv / requests/ / raw/ / RESPONSE_ASSESSMENTS.json / HTTP_STATE.json.
- Inventory: AVAILABILITY_MATRIX.csv / FRAME_COVERAGE.csv / PILOT_SLOTS.csv / PILOT_MANIFEST.csv / PILOT_RUN.json / media_pilot.sqlite.
- Schema: schema.sql / FIELD_DICTIONARY.md / ACTUAL_EXAMPLE.json; synthetic examples are exclusively in fixtures/ and tests.
- Historic diagnostic receipts: LEGACY_GUARDIAN_RECEIPTS.json, excluded from all new slots.
- Verification: VALIDATION.json / TEST_OUTPUT.txt / test_prototype.py. No tests call the network or government DB.
- Follow-through: LICENSE_ROUTE_OPTIONS.csv / NEXT_BATCH_PLAN.csv; proposal only, no execution release.

Read-only verification (Python3 with requests and beautifulsoup4, used successfully in this environment):

```sh
cd /Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/02_media_precollection
python3 -B test_prototype.py
```

`python3 -B prototype.py` rebuilds only derived local pilot outputs from saved evidence. `--execute` enforces the frozen exact route plan and existing terminal state; it will not retry the completed/challenge request. Preserve this delivery snapshot: replay or later edits must use a separately versioned copy and renewed receipt/manifest, rather than refresh frozen hashes in place. There is no login flow, credential discovery, paywall bypass, article scraping or account creation.

All acquisition raw and partial bytes are in raw/ and charged to 128 MiB. Synthetic generated fixture HTML is not downloaded media. 15 GiB floor and government reserves remain active through the shared 14 heavy-I/O lock. The publisher-country anchors are candidates with explicit verification state; source-era historical owners are NULL. Neither nominal equal quotas nor code tests establish population representativeness or readable article coverage.

A slot weight is a planned rule, never an observed article count. Only a non-NULL acquired parent contributes to an article inventory; all 150 current slots contribute zero articles.
