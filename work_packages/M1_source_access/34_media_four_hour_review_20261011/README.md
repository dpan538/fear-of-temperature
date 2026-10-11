# Four-hour media ingestion repair and closed collection results

The fixed 11 October 2026 window added **3,042 comparable newspaper articles**, **34 separately typed Supplement articles**, and **1,449 dated independent social bodies**. The collection defects have actual Load evidence, while source breadth, historical depth and social concentration remain unresolved. The last two rounds produce smaller social increments; newspaper growth also falls in this shorter window.

The execution interval was **07:44:10.127246–11:44:10.127246 AEST**, corresponding to **2026-10-10T21:44:10.127246–2026-10-11T01:44:10.127246 UTC**. Preparation and repair were included. Publication dates remain **1988-01-01–2026-09-21**, with a partial September 2026. Finalization timestamps do not extend acquisition.

| Frozen measure | Before | After | New units |
| --- | ---: | ---: | ---: |
| Comparable non-campus newspaper articles | 27,662 | 30,704 | 3,042 |
| Separately typed Supplement articles in this delivery | 0 | 34 | 34 |
| Expanded newspaper-family articles | 27,662 | 30,738 | 3,076 |
| Comparable newspaper months with text | 461/465 | 461/465 | 0 |
| Expanded family months with text | 461/465 | 465/465 | 4 |
| Contributing newspaper titles | 24 | 30 | 6 |
| Social dated independent bodies | 987,252 | 988,701 | 1,449 |
| Social retained core texts | 987,268 | 988,717 | 1,449 |
| Social observed months | 343/465 | 343/465 | 0 |
| Social contributing source IDs | 39 | 39 | 0 |

## Quantity contraction

The [round comparison](analysis/ROUND_YIELD_COMPARISON.csv) uses qualified comparable article IDs and dated independent authored bodies. Authorized-hour rates include preparation and resource-stopped time; they are realized window yields, not active worker throughput.

| Closed round | Authorized hours | New newspaper articles | New social dated bodies |
| --- | ---: | ---: | ---: |
| Broader-history round, 10 October | 4 | 2,592 | 416,529 |
| Focused repair, 10–11 October | 8 | 6,829 | 66,357 |
| This repair, 11 October | 4 | 3,042, plus 34 separate Supplement | 1,449 |

Newspaper production changes from **853.63 to 760.50 comparable articles per authorized hour**, a **10.91% decline**. Its raw total falls 55.45%, with half the authorized time. Recorded request attempts rise 1,074→1,661, while articles per recorded request fall 6.36→1.83. The changed transport/source mixture includes individual publisher HTML recovery instead of high-yield native batches. Named scheduler and recovery defects were repaired during the interval; the records do not support assigning a precise share of the yield loss to CPU, network or verification time.

Social's authorized-hour yield falls **95.63%** against the eight-hour round. Its A/B phases add 1,156 and 293 bodies, with 301 and 210 charged requests. B stops at **09:18:56.615003 AEST** because no permitted complete small operation fits the unchanged 15 GB cumulative social envelope. Physical and shared-budget space remain; source inventory is not exhausted. The earlier 416,529-body round was heavily dominated by one technical mailing list, so it is not a comparable promise of broad community production. A larger budget or another acquisition window is not activated by this report.

## Repairs and actual recovery

The generic Green Left body fallback, live issue-to-ready merge and persistent fresh-issue scheduling are implemented in the [newspaper code](closed/newspaper/implementation). Legacy named months gain **948 complete articles across 88 months**. Fresh issues 293–295 supply **96 real new article IDs**, 32 per issue at this frozen endpoint; their operation bounds are not issue quotas. The remaining legacy inventory contains **12,260 untouched candidate URLs** and seven touched pending URLs across the 116 named rows. These are candidate routes, not verified complete articles or an exhausted archive.

Workers Advocate Supplement contributes 8 articles in 1988-11, 9 in 1988-12, 8 in 1989-04 and 9 in 1990-11. These four months are genuinely recovered in the explicitly amended family frame. They remain empty in the comparable regular frame. The Supplement is an archival reproduction and does not add a new independent title. Six new contributing titles are Castlemaine Mail, Charlotte News, Chester Telegraph, Gippsland Times, Islington Tribune and Midland Express. The 30-title frame remains below the 50-title development objective.

Publisher visibility/template recovery retains original versions and pending mappings. The MemberPress preview `gippsland_times:post:8980` is preserved but excluded from qualified complete-article counts; matching public JSON and HTML is insufficient whole-body evidence. A late checker failure was caused by requiring sidecars for 1,990 native records whose durable text is validly stored in SQL with no declared sidecar. The corrected checker verifies SQL/native hashes and declared sidecars separately. Original data and the first failed check are preserved; no additional source request or Load was performed for this correction.

Social publication accounting now includes both previously published roots outside the stream store, retains 64 MiB journal and 32 MiB native margins, and uses evidenced incremental output reservations. Accepted A outputs remain frozen. The [merged source-month calendar](closed/social/FINAL_SOURCE_MONTH_CALENDAR.csv) reconciles both phases once using stable independent-body keys, with zero overlapping A/B keys. The initial topic736 context container counts as zero authored bodies. Three small saved-response bodies are included in A's accepted total, not added again.

## Distribution and source limits

Regular newspaper depth improves: zero/one/exactly-two months change **4/15/15→4/12/9**; months with 3–9 articles change149→65 and with10–49 change83→163. These counts still show sparse periods, and pooled presence does not establish full archives or comparable regional/source coverage. Preserve all legitimate peaks and the separate 9,249 historical campus IDs.

Social retains **16 strict discussion-forum families plus seven Q&A communities**. Q&A, technical/civic lists and platform instances do not inflate the strict forum total. No new community contributes this round. Python-list remains **613,429 dated bodies, 62.04%** of the final social total. In matched January–August2016–2026 bins, 2026 remains **54.44%** of social bodies, compared with54.45% before this window. Its full-history2026share is16.78%; that smaller number does not certify repaired recent-period concentration. The current four-hour baseline includes all39 prior source IDs, so its fixed-source comparison differs from older narrower baseline comparisons.

Publisher, platform and community mappings retain separate dimensions, unresolved mass and historical validity limits. Neither source IDs nor summed relation dimensions establish independent-parent counts. Full-calendar social gaps include pre-foundation inapplicability and unknown recoverable inventories. No climate/emotion/fear exclusion, peak flattening or corpus-wide semantic labelling was executed.

## Seven PNGs and verification

1. [Monthly presence and depth](analysis/finalized/figures/01_frame_coverage_and_depth.png)
2. [Monthly and annual time distributions](analysis/finalized/figures/02_time_distribution.png)
3. [Matched recent-year distributions](analysis/finalized/figures/03_matched_recent_years.png)
4. [Source contribution, structural genre and era](analysis/finalized/figures/04_source_genre_era.png)
5. [Legacy inventory and evidence dispositions](analysis/finalized/figures/05_legacy_inventory_and_evidence.png)
6. [Parent mapping and unknown mass](analysis/finalized/figures/06_parent_mapping_unknowns.png)
7. [Capacity receipts and stop reasons](analysis/finalized/figures/07_capacity_and_stops.png)

All seven 300 dpi PNGs pass strict panel alignment, generated PDF text/collision checks and manual visual inspection. The report binds inputs and implementation by SHA-256. Its source-month/body-key reconciliation and baseline-ID conservation pass. [Source and schema notes](SOURCE_AND_SCHEMA.md) define the counting units and receipt timestamps. [Publication accounting](PUBLICATION_ACCOUNTING.json) includes originals and new social/report/code copies exactly once, the largest possible atomic companion and actual physical headroom.

Newspaper's last HTTP response is **11:43:54.070762 AEST**, and its last real Load is **11:43:22.460367 AEST**. Its watchdog interrupts at the fixed endpoint; PID exit and mutex release are independently accepted. Social's stop and both phase final checks were accepted earlier. The coordinator reused those checks and read only frozen metadata, without rescanning any old store/raw/body corpus. A remote compaction failure in the predecessor coordinator was handled by transferring coordination and preserving successful dispatch, scopes and collector counters; the remote service defect itself was not locally repaired.

The publication contains completed acquisition implementation, final metadata/manifests and this research summary. Runtime controls, owners, leases, request queues, raw material and individual target receipts remain local with original digest bindings. Both acquisition windows are closed. The coordinating heartbeat is paused after the completed main push; no successor is authorized.
