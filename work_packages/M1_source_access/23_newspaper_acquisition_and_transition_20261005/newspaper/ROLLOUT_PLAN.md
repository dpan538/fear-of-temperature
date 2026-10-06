# Continuous newspaper acquisition rollout

The objective remains 1988-01-01 through 2026-09-21: 465 months and 2,325 disjoint regional coordinates. September 2026 is partial. `coverage/REGIONAL_MONTH_LEDGER.csv` assigns one planned presence effort to every stratum-month; `POOLED_MONTH_LEDGER.csv` retains every study month. These are conditional route assignments, not already frozen article selections, publication counts, sufficient density or a completed corpus.

Each source begins with identity, source-era and public route checks. Preserve publisher dates, archive issue dates, article dates, retrieval times, content-version times and report times as separate fields. A source route outside its advertised era is structurally inapplicable for that route, not proof that the region had no newspapers. Empty tool responses, holiday calendars and term-time schedules do not establish empty regional publication frames.

## First-pass source routing

| Stratum | Conditional source order across time | Explicit gap/alternative |
|---|---|---|
| EU/Europe excluding UK | Times of Malta is the initial historical candidate; retain Cyprus Mail, Irish Times and Trinity News as separately declared alternatives. | Malta subscriber archive and Cyprus retention stop remain unresolved; Ireland routes do not resolve the early-period public-body gap. |
| UK | Beaver through 2011; Varsity thereafter in the provisional calendar. | Beaver end-year/mapping and Varsity retention unresolved. Guardian requires applicable key/rights and begins in 1999; Mancunion has physical holdings only. |
| AU | Canberra Times through 1995; Alice Springs News to the digital transition; InDaily thereafter. | ACT/NLA end-year discrepancy, Trove live access, Alice actor restriction, exact InDaily era/edition boundaries. SMH licensed access remains unestablished. |
| US | The Tech's current issue portal is the provisional first route throughout; preserve Stanford, Deseret and NYT separately. | Early PDF segmentation/date/OCR, wire rights, student composition, Deseret terms stop, Stanford live interface, NYT entitlement. |
| NZ | Press to 1995; Ruapehu through 1999 and in 2001; ODT otherwise. | ODT before documented open web/replica eras is an unassessed route gap. Ruapehu 2000 holdings gap is not newspaper absence; Herald retention stop preserved. |

This order is provisional and does not authorise silent fallback after a failed selected article. A source-month discovered frame must be frozen first. Select the first structurally identified article in declared native DOM or native date order, without climate, fear, affect or length filters. Store aliases and unknown denominator/inclusion probability. Preserve rejected, unavailable and truncated targets; named repair or later replacement requires an explicit new frame version with its reason. Do not move effort to another region or infer national representativeness from successful student/regional sources.

## Executable chain and stops

`prototype/pipeline.py` implements frozen frame → bounded transport → raw receipt → new parser derivative → evidence-linked review → atomic staging/cursor commit. `parser.py` preserves inline DOM adjacency and requires a source-specific body boundary. `staging.py` separates article identity from content versions and keeps diagnostic/fixture lanes out of newspaper coverage. `transport.py` checks the fixed deadline, original reserves, lifetime ceiling, public-host gate, request allowances, per-source timing, redirects, object truncation and access/cooldown state. No production source gate is enabled in this package.

Start with at most two native discovery pages per source-month. Stop earlier at a prior refusal/cooldown, unknown applicable rights, failed date/parent mapping, object cap, shared request limit, storage stop or deadline. Record next-page/next-source-month cursors and stop reasons. An incomplete bounded frame does not prove the eligible population count. Shared issue/year indexes may supply multiple months only after date and article mapping are verified; never fabricate a hidden API or use prohibited search/API paths.

Review identity, independent article parent, publication date, full visible prose, issue/page separation, body boundary and provenance using the exact raw/body/parser/adapter hashes. A preview, JSON-LD component, issue OCR blob or article-tagged advertisement/public notice does not automatically qualify. OCR uncertainty and continued articles need explicit parent/segment evidence. Keep valid routine/neutral discourse; no fear-specific gate is used. Current retrieved bodies are not presumed to be their historical versions.

Use the shared heavy-I/O lock without unlinking it and the owner-only newspaper SQLite writer lock. Requests, article/version records and source cursor commit together under a transaction; an interrupted fixture transaction rolled back completely. Exact duplicate reruns added zero versions. Budget/storage failure sends no network payload request. Full corpus rollout has not been demonstrated live.

## Capacity and request feasibility

The lifetime ceiling remains 134,217,728 bytes, including the accepted 25,819,723-byte prior tranche. This prototype conservatively counts all own-package files, including code, policies, metadata, derivatives and SQLite/WAL, rather than narrowing the numerator to make downloads pass. No raw or body is silently discarded to fit.

For a default 2 MiB raw object, the required free-space threshold is 19,494,496,740 bytes: 15 GiB free floor + original remaining reserves 3,335,940,580 + additional staging/WAL/recovery 50,331,648 + prospective raw 2,097,152. Original reserves are not relaxed. Lifetime preflight also reserves derivative/record growth. Every actual measurement in this tranche has failed; `control/FINAL_STORAGE_CHECK.json` is the closing snapshot. A future actual passing check is necessary before any article/index download.

Even if disk space improves, approximately 108 MB or less of lifetime allowance remains after prior/new files. Dividing the remaining allowance by all 2,325 cells is only a budget scenario, roughly 46 KB per cell including retained copies and overhead; it is not a measured newspaper payload size. The 2 MiB ceiling is a per-object stop, not expected size. A full pass at that ceiling would greatly exceed the lifetime allowance. Source size distributions and attainable cell count remain unknown until a small permitted tranche supplies real evidence. No density/completeness guarantee follows from a presence target.

Each initial title has at most 32 metadata/discovery/policy operations and three domain/date search responses; four titles therefore provide at most 128 metadata operations per region. If every month needs a separate operation, 465 months cannot fit that initial regional allowance. Verified reusable indexes can reduce operations, but their suitability is unverified. Preserve all calendar coordinates and release a later bounded continuation only after coordinator review; do not silently reset counters, raise limits, extend the two-hour deadline or create an automation/window.

## Concrete continuation

First resolve actual storage capacity without deleting user data or lowering safeguards. Then validate a small, declared public issue/article chain for The Tech or a permitted Press HTML route, and Trove's documented anonymous route/terms if independently viable. Validate at least early, middle and recent applicable intervals; a recent newspaper page does not validate an early PDF/OCR adapter. Beaver's public date controls remain a concrete unused enumeration path. Confirm the actual Mancunion and Trinity publisher/archive routes from primary native links rather than repeat the unverified search domains. Rights-stopped titles stay stopped unless new applicable permission evidence appears. The reader can inspect `sources/REQUEST_ALLOWANCES.json` for exact unused capacity; no claim of discovery exhaustion is made.

The next live chain must freeze its native/date selection before bodies, preserve failed targets, acquire bounded raw, validate structure and article identity, then stage a distinct eligible newspaper parent. Run one changed-tranche verification, export all monthly ledgers and continue usable intervals. No social-post acquisition, government reopening, hidden evaluator access, corpus-wide semantic cleaning or climate/fear labelling is authorised here. RQ1/RQ2 remain ahead of deferred RQ3; later similarity/affect/fear validation is separate from acquisition readiness.
