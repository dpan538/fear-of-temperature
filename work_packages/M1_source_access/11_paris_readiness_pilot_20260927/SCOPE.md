# Frozen pilot rules (written before pilot extraction)

Snapshot target: 2026-09-27 UTC. Paris adoption is binned in 2015-12; the accounting window is 2013-12 through 2017-12 inclusive. This is a preparation and feasibility audit, not a role trend estimate.

## Government

Reuse the saved 10:53 UTC pooled month-by-role ledger and the 12:36 UTC EPA bridge ledger. The older pooled counts plus the 125 newly committed EPA parents are a **documented lower-bound checkpoint**, not a live total while other writers continue. For each month retain source-specific UK, EU and US counts and the EPA fixed-rule denominator; do not merge genres into a rate. Use updated pooled text-presence from the bridge as authoritative. Empty relevance values mean not reviewed; zero is reserved for an explicitly reviewed finite set.

Pilot seed: `paris-readiness-20260927-v1`. Selection is deterministic and fixed by source and month before reading bodies. UK source strata: GOV.UK DEFRA policy papers and UK Parliament Questions and Statements API answers/statements, months 2015-02, 2015-03, 2015-06 and 2015-07. EPA `final_rule`: 2015-03, 2015-04, 2015-05, 2015-06 from the 125-parent bridge manifest. Within each available source-month select the lowest SHA-256 of `seed|parent_id` among title/header candidates containing `climate`, `warming`, `carbon`, `greenhouse`, `energy`, `temperature` or `emission`, and the lowest hash among all remaining parents as a control; if no candidate exists, take only a control. This is a diagnostic enriched sample, not a random prevalence sample. UK 2015-04/05 have no stored UK parents; absence is retained. The exact selected IDs and candidate pools are output.

Review each selected parent for original date, title/action, content-version and source-segment mapping, readable body, attachment scope, web/PDF service noise, correction or withdrawal, and whether the **authorial text** concerns physical warming/climate impacts, fear/anticipated harm, both, or neither. Policy discussion of emissions can be climate-related without fear; an `air temperature` or `warming` token alone is not sufficient. Store short evidence snippets only.

## Media and public

Media frame: three fixed Guardian `environment/YYYY/mon/DD/all` archive days, 2015-11-30, 2015-12-13 and 2016-01-17. Count unique text article URLs in the visible archive title cards, excluding `/video/`. Select the lowest `seed|URL` hash per archive day; inspect original article date/body marker and URL. The archive-day count is **not** a monthly or topic census; pages can change retrospectively. Guardian Open Platform `api-key=test` returned HTTP 401 on 2026-09-27, so no API-wide monthly denominator is asserted. Store metadata and short evidence snippets, not complete copyrighted bodies.

Public frame: official UK Parliament 2015–2017 archived petitions JSON query `parliament=1&q=climate`, all linked result pages at the snapshot, with distinct petition ID. Keep the full search-result ID/date ledger and the November 2015–January 2016 subset of petitioner-authored action/background/additional detail; do not count government responses as public text. The query result is a keyword-retrieval denominator, **not** all public discourse or all petitions. Separate `created_at`, `opened_at` and rejected state; monthly bin uses creation date for the pilot and published-only sensitivity uses `opened_at`.

No formal corpus database write, full vectorisation, emotion estimate, causal model, or proposal edit is in scope. Network reads stop at the fixed pages and selected article/petition records.

## Declared diagnostic supplement after the first extraction

The first hash-selected controls exposed generic `energy` matches and, on the media archive, a wildlife article. To test precision on clearer candidate text, add one deterministic `climate`, `greenhouse`, `global warming` or `Paris` title/URL candidate per available source-month/day, again taking the lowest `seed|parent ID or URL` hash. This supplement is explicitly post hoc, is kept separate from the original selected rows, and cannot estimate the prevalence of relevant records. For EPA, use only already acquired parents in the frozen 125 manifest; no new source requests. Public pilot already retains every returned search hit in the three-month subwindow and needs no extra selection.
