# Post-repair corpus state and bounded supplementation recommendation

Checked on **4 October 2026, 22:21 China Standard Time (14:21 UTC)**. The publication interval remains **1988-01-01–2026-09-21 inclusive**; September 2026 is partial. This report continues the analysis/coordinator handoff. The repair release is valid at the checked database checkpoint. The proposed EU candidate-body tranche is justified as a bounded source-depth addition, but the current downloader needs a release-schema correction and final five-request accounting before execution.

## Checked evidence and units

The [handoff](../../../docs/handoffs/2026-10-04-analysis-continuation.md), [coordinator review](../15_targeted_repairs_and_supplementation_20261004/COORDINATOR_REVIEW.md), Task 3 report/result/release and Task 4 report/source plan were read. Saved changed-month, exception, request, source-composition and WEMI relationship ledgers were reconciled. One read-only metadata aggregate of `repair_current_documents` established current UK month/source/genre counts and date precision. The shared heavy-I/O lock was acquired nonblockingly and released without unlinking it. No text-table scan, validator rerun, raw-file hash audit or pooled readable-text recalculation was performed.

The authoritative UK06 file remains **3,590,598,656 bytes**, modification checkpoint **1791108746288675852 ns**, matching `REPAIR_READY.json` before and after the read. See [CHECKED_STATE.json](CHECKED_STATE.json), [INPUT_MANIFEST.json](INPUT_MANIFEST.json), [SQL](uk_metadata_aggregate.sql) and [reproduction script](check_current_state.py). Saved input hashes cover the bounded evidence files, not whole databases or original bodies.

A UK parent is a source-specific document identity, not necessarily a unique utterance across mirrors or shared answers. EU parents are Work URIs; Items, formats, annexes, versions, pages and extracted segments are separate units. UK09 is a historical copy and contributes no additional UK parents. US/AU09 and EU10 figures below retain their prior source checkpoints; they were not rescanned.

## Current UK shape and the changed months

| Measure | Checked value | Meaning |
|---|---:|---|
| Effective UK source-specific parents | 248,319 | Includes the committed correction layer |
| Historical UK parents | 248,035 | Preserved extraction history |
| Additional locally derived parents | 284 | 202 saved-ZIP recoveries and 82 HTML reply-group partitions; zero network acquisitions |
| Corrected existing parent projections | 1,256 | Reported committed Task 3 tranche; does not add parent identities |
| Corrected/recovered segments | 6,852 | Passage units, not independent documents |
| Parents assignable to one month | 248,268 | Includes 73 October 2003 intervals |
| Parents with an effective exact day | 248,195 | Metadata date support, not universal independently verified issue days |
| Cross-month interval parents | 51 | Retained in inventory without a single analysis month |
| Current technical-state annotations | 1,054 | Separate from historical attempts, ethics and licensing |

The metadata aggregate found zero effective dates/interval bounds outside the fixed interval and zero parents lacking both an effective day and a supported interval. This is a metadata consistency result, not proof that every date or historical body version is correct. The 119 source-local/UTC differences remain convention-sensitive; no bin convention was changed here.

All nine changed calendar bins belong to **Historic Hansard written answers**. [The comparison CSV](uk_changed_month_comparison.csv) joins the saved pre-repair audit to the current effective aggregate:

| Month | Historical parents | Effective parents | Change | Evidence for change |
|---|---:|---:|---:|---|
| 1991-12 | 599 | 681 | +82 | Previously combined HTML groups repartitioned |
| 1992-01 | 585 | 602 | +17 | Groups recovered from saved ZIP |
| 1994-03 | 1,099 | 1,114 | +15 | Groups recovered from saved ZIP |
| 1994-07 | 730 | 760 | +30 | Groups recovered from saved ZIP |
| 1997-11 | 950 | 1,034 | +84 | Groups recovered from saved ZIP |
| 2000-07 | 1,128 | 1,184 | +56 | Groups recovered from saved ZIP |
| 2003-06 | 853 | 802 | −51 | Remove unsupported parser month; retain 2002-12-20–2003-01-06 interval |
| 2003-07 | 756 | 683 | −73 | Remove unsupported parser month |
| 2003-10 | 338 | 411 | +73 | Saved interval 2003-10-07–2003-10-13 supports this month |

The calendar-bin net increase is **233**; the separate cross-month bucket adds **51**, reconciling the inventory increase of **284**. Neither December 2002 nor January 2003 receives those 51 as an invented point allocation. Exact days remain unknown for all 124 interval cases. The largest relative increase in these bins is October 2003, about **21.6%**, driven by date correction. It is not evidence of a new discourse response or climate event. No counts were flattened or records excluded on semantic grounds.

The historical **465/465 pooled government source-text months** remain a dated milestone. This metadata query does not refresh readable-text coverage. It therefore supplies no new pooled coverage claim.

## Source and genre composition

[Current UK source/genre totals](uk_effective_source_genre.csv) are:

| Source | Written answers | Written statements | Policy/guidance parents |
|---|---:|---:|---:|
| Historic Hansard | 135,973 | 393 | 0 |
| Hansard archive | 35,123 | 1,339 | 0 |
| Questions API | 65,012 | 976 | 0 |
| ParlParse mirror | 8,405 | 43 | 0 |
| DEFRA papers | 0 | 0 | 1,020 |
| Historic policy | 0 | 0 | 35 |

The three official answer routes contribute **236,108** parent identities. Including the mirror, written answers account for **244,513/248,319 (98.47%)** of UK source-specific inventory. This describes UK genre composition; mirror and shared-answer relationships prevent treating it as an independent-utterance share or pooled international share. The correction slightly increases historic answer depth and does not diversify the genre frame.

The previous distribution checkpoint records **33,544 US EPA/DOE final/proposed-rule parents**, **50,578 EU COM preparatory Works**, and **821 AU catalogue candidates**. EU's 19,114 staged Item versions and 19,085 Work extraction statuses are distinct from complete readable Work counts. The seven verified AU originals overlap the catalogue, and its 819 missing main-table publication days are not converted into dated parents. These differently timed source frames are not added into a new pooled independent total.

For the saved **2015** composition, UK Questions API has 2,674 answers and 64 statements; DEFRA has 32 policy parents; US has 648 final and 596 proposed rules; EU has 1,009 COM preparatory Works. The saved operational extraction-status counts are 2,674 answers, 64 statements, 107 US final rules and zero EU Works. DEFRA's zero in that old status column is stale; it does not establish absent text. Task 3's current technical-state view must be used for repaired availability, and NULL outside that tranche does not mean unavailable.

EU body depth would add evidence from a Commission executive-publication process alongside parliamentary answers. This is a reason to assess the bounded tranche, not proof that bias is reduced or that texts are interchangeable across genres. Preserve source, jurisdiction and genre when later constructing denominators and sensitivity comparisons. The selected year does not provide the full 2013-12–2017-12 Paris pre/post window or media/public response evidence.

Earlier peak/calendar findings retain their saved scope. The UK 2013-05 archive partition was partial; DEFRA 2013-04 was a dated policy-series concentration; US 1994 selected-frame gaps, EU 1988-04 date concentration and UK 2024-08 answer dates remain named limitations. No new anomaly scoring or event attribution was performed, and none warrants a global acquisition restart.

## Remaining exceptions and source quality

The [remaining exception summary](remaining_exception_summary.csv) verifies **318 issue instances across 165 distinct units**:

| Evidence need | Issue instances | Distinct units | Treatment |
|---|---:|---:|---|
| EU content-link and technical-status/layout findings | 306 | 153 | Paired findings on the same Works; retain OCR/placeholder/selected-Item limits; inspect only for a specified need |
| UK reply-role/source-mapping uncertainty | 9 | 9 | Three missing section originals; other cases concern saved identity collisions or ambiguous group mapping |
| AU date scope and author/host/issuer separation | 3 | 3 | Two original-date/primary-file requests; one already saved report needs publisher/commissioning annotation |

The **37 frozen HTML-adapter limitations** are a separate validation dimension of the changed tranche, not 37 additional missing originals to add to the 165. Task 3 records 1,503 supported checks among 1,540 changed/recovered parents, retaining those 37 limitations. Do not replace named uncertainty with a universal pass. The 56,271 previously uncheckable annotations remain outside the acquisition queue.

Parliamentary archive text is archival reproduction of recorded utterances; GOV.UK institutional text is direct evidence of that institution's expression when its mapping is verified. CELLAR's expected official reproduction is still a body-level verification task for the proposed tranche. The externally authored AU report has checked author/affiliation and August 2005 evidence but unresolved legal publisher/commissioning responsibility; government hosting does not establish government authorship. AU catalogue routes alone have unresolved date/file mapping. No new population totals for original/archival/secondary/mixed/unresolved directness were calculated. Verification, conflicting mapping, date precision, completeness and access remain separate dimensions, without a trust score or claim-truth conclusion.

The withdrawn EU original request remains withdrawn: its selected bytes and extracted-text metadata already exist. Its layout/completeness review survives as an annotation, not another download.

## Final five original-evidence requests

Task 4's provisional three contribution-ID API routes are superseded by Task 3's **five-row released manifest**. The distinction between a section ExtId and contribution anchor is material:

| Existing parent / original | Section ExtId | Contribution anchor / date |
|---|---|---|
| `doc_5b740259ea5cdcdbdbdf` | `07051786000018` | `07051786000046`; 2007-05-17 |
| `doc_6fe9e11be5ea65fab67e` | `09021291000008` | `09021291000017`; 2009-02-12 |
| `doc_76b0ddb367df2c048a60` | `10022378000029` | `10022378000984`; 2010-02-23 |
| AU fugitive methane interim report 2026 | Original title/imprint and primary-file mapping | Publication day unknown; CMS 2026-09-17 is not issue-day evidence |
| AU Sustainable Ocean Plan | Original title/imprint and primary-file mapping | Publication day unknown; CMS 2026-09-22 neither proves exclusion nor inclusion |

The three correct Hansard section API routes previously returned HTTP 400. Use a documented alternate original route, such as the manifest's canonical official section page, with anchor/date mapping; do not repeat the old failed request blindly or substitute the contribution ID as a section ID. The AU cases require primary-file and issue-date evidence before inclusion in a dated eligible frame. If an original proves publication after 2026-09-21, record that outcome and preserve raw evidence without extending the cutoff. A route may remain unavailable after one bounded attempt; successful recovery of all five is not a gate for useful work on other sources.

## EU 2015 plan and execution readiness

The frozen manifest hash matches the contract: **979 distinct Work/selected-Item targets**, within **1,009 enumerated Works** and all 12 months, with **30 no-link outcomes** retained. Metadata parents are already enumerated: this is a candidate-body acquisition, not 979 new parents. No new body was acquired in Task 4 or this analysis.

Saved WEMI accounting confirms **973/979 Works** have multiple Item alternatives. More specifically, **253 Works have multiple Items within the selected PDF Manifestation itself** (726 have one); the maximum is ten. Thus the issue includes potential component boundaries within the chosen rendition, not only alternate formats. [Per-Work multiplicity](eu_selected_item_multiplicity.csv) records this distinction. Relationship metadata alone does not identify every sibling as an annex, duplicated format, component or revision. It also does not prove that the other 726 selected PDFs are complete.

Keep the 979 target selection frozen for first staging. Record separate states for candidate bytes, readable selected Item, verified identity/date, observed component coverage, and complete Work/required annex set. Retain component locators under their Work rather than adding parents. Missing siblings or annex evidence becomes a named later request only when needed; this analysis authorises no expansion to all 8,409 relationship rows or alternate Items.

Focused inspection and a **side-effect-free call to the existing preflight function** found:

| Check | Result |
|---|---|
| Actual committed release and UK file checkpoint | Match |
| Frozen EU manifest hash/count | Match |
| Storage preflight at 14:21 UTC | Pass: about **20.67 GiB** free; **17.51 GiB** projected after the existing 3.16 GiB reserve |
| Current script's release parser | **Fails** on the actual marker |
| HTTP streaming execution | Unexecuted and untested against the network in this task |

The marker explicitly has `status=committed_repairs_checked_targeted_acquisition_released`, `pre_checkpoint` and `post_checkpoint`, with linked acceptance/result files. `release_check()` instead searches leaf **keys** for committed/checked assertions and `before`/`after` checkpoint fields. Its returned flags are all false despite the valid released evidence. [The saved preflight](task4_read_only_preflight.json) reproduces this schema incompatibility. Do not modify or fabricate the release to satisfy the parser.

The script also has no explicit check for completed five-request A dispositions; the documented A-before-B order currently depends on the coordinator. Correct this in a scoped runner update or enforcing wrapper, preserving the frozen B contract. Validate the actual marker schema, active committed run evidence and matching file checkpoint under the shared lock; require a final A accounting artifact with five terminal outcomes (including local reuse or bounded unavailable). Reject staged/inactive/moved releases. Then check no-network fixtures and preflight once before executing the exact frozen queue. Streamed size/signature checks, one request at a time, two-second spacing, cooldowns, failure stops, dedup and provenance checkpoints must remain intact.

## Concrete continuation instruction

**Next package: scoped downloader readiness correction, five-original accounting, then EU2015 candidate-byte staging and changed-tranche acceptance.** Reconcile A from the final Task 3 manifest; preserve correct section IDs, unresolved AU dates and the withdrawn EU request. Correct and check the runner locally before any HTTP body requests. After A's bounded outcomes are recorded, stage the same 979 targets with the **2 GiB new-raw cap**, **15 GiB free-space floor**, transient/concurrent reserve, fresh per-object storage checks and existing rate/access stops. Account for A bytes and retained partial files in the overall staging budget; do not create an automatic replacement queue if the cap stops the tranche.

Export raw/version evidence to the coordinator. A separate serial formal writer must check source parent/Work identity, readable text, date and component boundaries before integrating changed records. Use `repair_parent_inventory` for UK dedup and the effective document/segment/link/annotation views for analysis; use source-native Work identities for EU. Keep completeness-pending candidates out of a claimed complete-Work numerator while preserving them as observed Items. Perform one acceptance of the changed tranche and carry the named residual list forward.

This task executed **zero downloads and zero formal data writes**. No downstream collector was started, script patched, source frame expanded, old figure regenerated, topic/emotion/fear classification performed, proposal revised, chat messaged/created, commit made or push performed. The inherited project collection permission and checked release remain valid; this initial handoff deliverable stops at analysis and the next instruction.

## Evidence levels

1. **Dated presence and original text:** UK effective metadata and committed saved-source repairs checked within the stated scope; EU2015 candidate routes established, new candidate bytes/readable complete Works zero.
2. **Climate/warming relevance and similarity:** unassessed here; not a cleaning or source-inclusion gate.
3. **Affect/risk/future-harm/responsibility association:** unvalidated here; not automatically fear.
4. **Fear interpretation:** unassessed; would require traceable passages and holder/target/horizon/quotation/negation checks.

Counts, technical availability and expected genre depth establish neither substantive claim truth, comparable three-role emotion prevalence nor causal influence. No new diagnostic figure was needed: the changed-month and unit tables convey the bounded result directly.
