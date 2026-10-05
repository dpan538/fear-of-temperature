# Government acquisition progress snapshot

Generated: 2026-09-27T07:01:20.699487+00:00

This is a checkpoint snapshot while source acquisition continues; it is not the final full-hash corpus audit.

## US Federal Register 1994–2026

- Frozen unique API parents: 33,544. Latest supervisor scope: 2003–2026 with 23,307 targets.
- Supervisor: running; 4,569 verified downloads and 4,569 ingested parents in its current year scope after 1 cycles, last checkpoint 2026-09-27T06:50:37.883150+00:00.
- Last full US report (2026-09-27T00:40:52.315522+00:00) counted 10,293/33,544 committed verified bodies, including 19 official GovInfo HTML fallbacks. The 1994–2002 group has 10,237/10,237 bodies. Current later-year access status: running.
- Current checkpoint total across the completed early group and later-year scope: 14,806 verified bodies and 14,806 ingested parents; the batch counters are checkpoint totals, not the last full audit.
- The 09 DuckDB writer is single-process. Later years and remaining current-scope parents are pending.

## US historical 1988–1993

- Six official annual index PDFs saved with request checkpoints and extractable OCR text.
- 7 full official issue PDFs are saved and hash checked; these are source containers, not article counts.
- Candidate parent-heading index tokens by year: 1988: 863, 1989: 893, 1990: 685, 1991: 630, 1992: 677, 1993: 1,096. These are page references, not Work counts.
- Official link-service issue-date/jump-fragment resolutions by year: 1988: 780/780, 1989: 826/826, 1990: 639/639, 1991: 594/594, 1992: 643/643, 1993: 903/903. Jump fragments are unverified PDF page locators until checked in the scans.
- Across all six years, 4,844 index tokens / 4,385 distinct candidate pages map to 1,325 issue dates. None of these totals is a verified article denominator.
- Six final/proposed-rule samples are independently bounded from official issues: DOE 53 FR 21646 / FR Doc. 88-13009, EPA 53 FR 20 / FR Doc. 87-29874, EPA 53 FR 126 / FR Doc. 88-50, EPA 53 FR 392 / FR Doc. 88-177, DOE 54 FR 17734 / FR Doc. 89-9909, and EPA 54 FR 17769 / FR Doc. 89-9872. Source and cleaned text are saved. `53 FR 3` was a false index token, and the 53 FR 392 jump fragment pointed eight PDF pages too late. Historical denominator remains unknown.

- Saved-scan page-header audit: 34 locator rows, printed_page_not_found_in_header 7, fragment_matches_printed_page 25, corrected_from_printed_page_header 2. Page alignment does not establish article identity.

- Storage sample: 18/18 official issue PDF headers returned lengths, median 105.8 MB. Median × 1,325 dates is about 140 GB, a rough capacity estimate rather than a total or rule count.

## Australia DCCEEW catalogue

- Frozen landing candidates: 821. Current outcomes: browser_files_verified_date_pending 1, browser_original_pair_verified 3, browser_original_pair_verified_issuer_review 1, individual_request_failed 1, official_web_landing_observed_raw_pending 363, official_web_pdf_identified_raw_pending 419, official_web_read_only_open_failed_raw_pending 29, original_pair_verified 4.
- Browser stage: 5 landing Works with saved files, 9 verified versions, 525 source/cleaned PDF pages. 3 have eligible pre-cutoff original dates, 1 require issuer-scope review, and 1 have unresolved original dates.
- Direct HTTP requests to the current host failed with a timeout or HTTP/2 stream error; ordinary in-app browser visits/downloads worked for the saved originals. The remaining 807 landings received read-only web-reader queries, with errors and omitted responses retained as unresolved, not absent originals. Web page/PDF links add no downloaded original bytes.

## EU Commission CELLAR

- Monthly Work bins: 465/465 reconciled; sum of official month counts 50,578. The stage has 50,578 unique Work parents with official document dates.
- English WEMI months complete: 465/465; 47,472 Works with at least one Item link in those months; 3,106 without an Item link.
- Original Item streams: 12,458 verified downloads; 12,358 text-extracted records. The stage currently has 12,427 versions, 216,498 PDF page segments and 107,305 HTML/DOC text blocks; it is refreshed after each completed download cohort.
- Scan-only PDFs with local OCR sidecars: 96; these are page-linked candidate transcriptions pending source-layout review.
- Per-Work disposition ledger: 50,578 globally unique Works; no_english_digital_item_link 3,106, ocr_candidate_layout_review 96, selected_item_not_requested 35,975, source_html_table_placeholder_review 18, source_text_extracted_relevance_unreviewed 11,383. Extraction and OCR remain subject to relevance and layout review.
- The 2024-08 zero applies only to the frozen `act_preparatory` class. An official CELLAR diagnostic identified an August 2024 COM proposal in the adjacent `proposal_decision_implementing_ec` class; the class boundary is documented in the EU runbook without changing this denominator.
- Independent raw-page audits: Work enumeration 465/465 months and 50,578 global Works, 0 discrepancies; WEMI 465 completed months / 1359 raw batches, 0 discrepancies at 2026-09-26T23:56:10.969400+00:00.
- The 1997-02 HTTP 503 with Retry-After 1800 seconds was honored; the same WEMI checkpoint reconciled on the slower retry. The later 2007-04 Retry-After checkpoint also reconciled. The content stream route is being processed independently.

Free disk: 20.60 GB. No proposal/model edits, commits, or pushes are part of this acquisition run.
