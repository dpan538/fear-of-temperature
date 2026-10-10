# Focused eight-hour newspaper repair — 10 October 2026

The bounded run added **6,829 complete article IDs**, increasing the current newspaper frame from 20,833 to **27,662 IDs**. Its terminal reason is `fixed_deadline_watchdog_interrupt`; the unchanged hard deadline was 2026-10-10T18:27:04+00:00. Actual writer exit, PID absence and the available lifetime mutex are recorded in `TERMINAL_WRITER_EXIT.json`.

The publication interval remains **1988-01-01 through 2026-09-21**. There is dated source-text presence in **461/465 months**, with 4 empty months. September 2026 is partial; source observation times do not establish end-of-day completeness. The 9,249 historical campus article IDs remain a separate preserved subframe.

## The three repair priorities

**Legacy queue effects.** The frozen evidence identified 116 Green Left-only months with exactly two retained IDs. This run loaded 338 additional native article IDs in 116 of those months. Original directory-consumed flags and raw evidence were preserved. The derived chronological queue uses verified native issue/year and per-article dates; it does not treat two records, a processed directory, a score or a plateau as archive completion. `LEGACY_AFFECTED_MONTH_BEFORE_AFTER.csv` records every affected month, including those with no new load. Unattempted and unresolved inventory remains explicit.

**Initially empty months.** 20 of the 24 initially empty months now contain complete articles: 1999-09, 1999-10, 2004-03, 2004-04, 2004-05, 2004-06, 2004-11, 2005-12, 2006-01, 2006-02, 2006-03, 2006-04, 2006-05, 2009-10, 2009-11, 2010-05, 2010-09, 2011-02, 2011-09, 2011-10. The remaining months are 1988-11, 1988-12, 1989-04, 1990-11. Presence is a recovered observation, not proof of complete historical coverage. The Workers’ Advocate archive index/masthead conflict remains pending; the index says November 1988 and the linked masthead says December 1988. Neither month was assigned by inference.

**Contributing titles.** The number of title IDs with complete retained articles changed from 14 to 24. Newly contributing title IDs are berkeley_daily_planet, cambridge_news_nz, dublin_gazette, enfield_dispatch, kilkenny_observer, mountain_times_vt, munster_express, te_awamutu_news, waltham_forest_echo, your_local_examiner_au. Admitted profiles and investigated candidates are reported separately from actual contributors. The source50 development goal was never a quota or stop condition; related titles are not automatically independent publishers or works.

## Actual new articles by source and era

| Source ID | Complete new IDs | Observed publication years |
| --- | ---: | --- |
| berkeley_daily_planet | 625 | 2000: 54; 2004: 209; 2005: 92; 2006: 270 |
| cambridge_news_nz | 13 | 2017: 13 |
| camden_new_journal | 16 | 2010: 2; 2011: 2; 2015: 1; 2018: 1; 2020: 2; 2023: 5; 2024: 2; 2025: 1 |
| dublin_gazette | 3 | 2012: 3 |
| enfield_dispatch | 325 | 2018: 56; 2019: 178; 2020: 91 |
| falls_church_news_press | 1,742 | 2009: 505; 2010: 612; 2011: 625 |
| galway_advertiser | 20 | 2008: 20 |
| green_left | 338 | 1992: 26; 1993: 31; 1994: 40; 1995: 29; 1996: 24; 1997: 24; 1998: 24; 1999: 24; 2000: 24; 2001: 24; 2002: 23; 2003: 23; 2004: 22 |
| kilkenny_observer | 300 | 2020: 202; 2021: 98 |
| limerick_post | 1,291 | 2009: 497; 2010: 468; 2011: 326 |
| montpelier_bridge | 491 | 2025: 337; 2026: 154 |
| mountain_times_vt | 300 | 2012: 1; 2014: 299 |
| munster_express | 400 | 2006: 2; 2007: 161; 2008: 237 |
| newtown_bee | 15 | 1998: 2; 1999: 13 |
| te_awamutu_news | 325 | 2019: 5; 2020: 150; 2021: 170 |
| waltham_forest_echo | 325 | 2014: 32; 2015: 106; 2016: 171; 2017: 16 |
| your_local_examiner_au | 300 | 2015: 300 |

The table describes actual returned articles, not the complete eras of a title or its founding history. Native article-section labels and category IDs appear in `NEW_SOURCE_PURPOSE_GENRE_ERA_REGISTER.csv`; unresolved category names remain unresolved. No semantic genre, climate, affect or fear model was run.

## Source quality and retained evidence

Original publisher pages/API records are direct evidence of the recorded newspaper utterance. Workers’ Advocate and Militant archive transcriptions remain archival reproductions, with transcription/version time separated from publication and retrieval time. Embedded quotations, reprints, letters and speaker attribution require their own passage-level checks. Provenance verification does not establish the truth of every claim.

Berkeley issue pages were treated as containers. Native story IDs, headlines, authors, dates and complete bodies determine countable articles. Same-ID repeated carrier occurrences retain raw evidence and collapse only the derived identical unit; conflicting representations remain pending. The confirmed apex/www alias relies on publisher/native-ID/date/title/author/body evidence and preserves actual fetched URLs. Compiled letters/calendars and incomplete native units remain explicit pending dispositions.

Cambridge News uses an advertised sitemap and verified original HTML article mapping, without guessing an API. Sitemap modification times are not publication dates. Native published dates after 21 September 2026 remain ineligible. Related Good Local Media titles and historical merged print editions are distinct mappings.

The publisher’s native unit `cambridge_news_nz:article:194`, headed ‘Example Sports Headline’ with placeholder copy, loaded immediately before its queue hold. Its original database row, ID, version, raw, Load log and counters remain preserved. The exact evidenced derived disposition excludes it from qualified article counts; it is recorded in `STRUCTURAL_UNIT_DISPOSITION_REGISTER.csv`. This is a structural unit decision, without a topic, emotion, language or length threshold. The run retained 6,830 new Load IDs, of which 6,829 are qualified complete articles.

Trove’s explicit automated-access/copy restriction is preserved in `FOCUSED_SOURCE_USE_STOPS.json`; no further request or body load was made after identifying it. Other inherited host stops, account/paywall/robots limits and all 36 consumed PDF slots were retained. Public access, permission, licensing and redistribution are separate observations. No open-content or unrestricted full-text redistribution license is inferred.

## Post-exit verification

Changed-tranche checks passed: **True**. SQLite quick-check: ['ok']; foreign-key errors: 0. The check preserved 30,082 baseline identity/source/date/version memberships and verified 6,829 new complete IDs, their body hashes, raw mapping, fixed dates and applicable native identity/body boundaries. Own request raw-object verification is recorded separately. No old-body or old-raw corpus sweep was performed.

The cumulative transport/native counters are 18,739/40,651; they were not reset on controlled restarts. The maximum recorded native HTTP hops is 3 against the inherited four-hop ceiling. Actual-operation accounting, the shared 30 GB allowance, social’s separate envelope, the 15 GiB physical floor and 48 MiB recovery reserve remained active. Allocation is not evidence of physical capacity.

At 15:43:56 UTC the writer exited independently when an unlocked progress capacity scan encountered another stream’s temporary metadata filename during atomic rename. Actual session exit, PID absence and a free lifetime mutex were verified. The progress scan was placed under the existing shared heavy-I/O lock and the same bounded task resumed at 15:47:28 UTC, preserving all counters and its original deadline. The repaired code and prior runtime binding remain archived locally.

A separate shared-lock wait was observed between 16:33 and 16:36 UTC while the social incremental closeout process had the heavy-I/O lock open. Newspaper loading resumed at 16:36:38 UTC after the lock became available. No other-stream process or control was changed and no time was added to the window; the exact lock hold duration was not measured.

Charlotte’s advertised native API returned one smaller chronological metadata page after a 50-item response timed out. The documented 10-item response provided native IDs and the actual next href; the first body batch and the next metadata page still timed out. This establishes a bounded interface limitation, not absent newspaper content. Failed targets, pending units and original counters remain preserved.

## Remaining work and interpretation limits

The frozen terminal source frontier, named-gap statuses and legacy queue inventory identify concrete work that remains available or unresolved. Interface exhaustion describes the observed interface only; it is not a claim that all historical editions were recovered. Pending native batches, mismatched dates, mixed source frames, ambiguous article boundaries and access limits remain preserved. `SOURCE_FRONTIER_REGISTER.csv`, `RESIDUAL_EMPTY_MONTHS.csv` and `PENDING_DISPOSITION_REGISTER.csv` provide the factual inventory.

Monthly peaks are diagnostic flags against the preceding/following available three months, with incomplete boundary context retained. Valid peaks were neither flattened nor downsampled; no peak was attributed to a climate event. Article IDs are not automatically independent published works. Parent statistics remain auxiliary and did not control acquisition.

This delivery establishes dated source presence and readable original text where verified. Climate relevance/similarity, validated affect/risk associations, and fear-specific interpretation remain separate later evidence levels. Coverage, query hits and counts do not establish emotion prevalence or a comparable three-role time series.

No extension or four-hour successor has been selected, prepared or released. This report supplies factual eight-hour results for the coordinator’s later independent assessment.

## Delivery files

- `DELIVERY_SUMMARY.json` and `CHANGED_TRANCHE_FINAL_CHECK.json`: counts, checks and resource/exit evidence.
- `ADDITIONAL_ARTICLE_REGISTER.csv`, `CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv`, `SOURCE_PROVENANCE_AND_DATE_REGISTER.csv`: retained identities, versions, native/raw mappings and provenance.
- `MONTHLY_BEFORE_AFTER.csv`, `MONTH_SOURCE_COUNTS_BEFORE.csv`, `MONTH_SOURCE_COUNTS_AFTER.csv`, `SOURCE_YEAR_DELTA.csv`, `MONTH_PEAK_CONTEXT_FLAGS.csv`: distribution and diagnostic context.
- `LEGACY_AFFECTED_MONTH_BEFORE_AFTER.csv`, `RESIDUAL_EMPTY_MONTHS.csv`, `SOURCE_FRONTIER_REGISTER.csv`, `PENDING_DISPOSITION_REGISTER.csv`: repaired and unresolved inventory.
- `RAW_OBJECT_MANIFEST.csv`, `NEW_SOURCE_PURPOSE_GENRE_ERA_REGISTER.csv`, `HOST_STOP_REGISTER.csv`, `HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv`: source/native evidence and preserved boundaries.
- `STRUCTURAL_UNIT_DISPOSITION_REGISTER.csv` and `DERIVED_STRUCTURAL_UNIT_DISPOSITIONS.json`: exact named structural count correction, with all original evidence retained.
- `DELIVERY_FILE_RECEIPTS.json`: final delivery file sizes and hashes.
