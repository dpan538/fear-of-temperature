# Access and denominator probes, 27 September 2026 UTC

## Guardian environment daily archive

Between approximately 13:47 and 13:54 UTC, all 31 fixed December 2015 `/environment/2015/dec/DD/all` paths returned HTTP 200. The observed pagination controls link only to older/newer **dates**; none exposed within-day page-number pagination. A `?page=2` probe on 1 and 12 December returned the same 27/17 title-card counts as the unparameterised pages and did not establish a second daily page. The [daily status ledger](guardian_dec2015_archive_days.csv) holds each URL, response hash, nonvideo card count and pagination link.

The 31 pages yielded 396 distinct Guardian-host nonvideo title-card URLs. The [card ledger](guardian_dec2015_archive_cards.csv) retains archive-day provenance. By approximately 13:54 UTC, a metadata-only first-64-KiB probe of each linked article found HTTP 200, a canonical URL matching the card URL and `article:published_time` in December 2015 UTC for **396/396**. No full copyrighted body was saved. The [article metadata ledger](guardian_dec2015_article_metadata.csv) retains original and current-modified timestamps, URL and exception fields. Three additional hash-selected originals had readable body HTML; [short spot-check evidence](guardian_dec2015_body_spot_checks.csv) is separate. A fourth December body had been checked in the earlier pilot.

This supports a **396-article current archive candidate denominator for December 2015 under the fixed environment/nonvideo rule**. It does not prove that the archive is an immutable record of all articles visible to readers in December 2015, that all 396 bodies are readable, or that the 396 are warming or fear relevant. The Open Platform test key had returned HTTP 401 in round 1; it was not bypassed.

## UK Parliament published-petition denominator

The existing official [archived search](https://petition.parliament.uk/archived/petitions?parliament=1) returned 177 distinct IDs for `parliament=1&q=climate`. Re-mapping those IDs by `opened_at` yields a 77-ID **published keyword-query** frame; the other 100 have rejected state and no `opened_at`. `created_at` retains all 177 for the submitted sensitivity frame. The [ID-level mapping](petition_177_id_date_mapping.csv) and [three-month comparison](petition_nov2015_jan2016_month_mapping.csv) show this without new broad collection.

Targeted official route probes at approximately 14:10–14:15 UTC:

- `https://petition.parliament.uk/archived/petitions.csv?parliament=1&state=published` returned HTTP 200 with CSV columns `Petition,URL,State,Signatures Count` but **no creation or opening date**. `state=all` exposed the same four column names. The first-byte probe did not download either entire export.
- `https://petition.parliament.uk/archived/petitions.json?parliament=1&state=published` returned 25 dated petition objects per page and a `last` link at page **438**. `per_page=10000` and `page_size=10000` still returned 25 objects and page 438. The archive search form exposed text `q` and `state`, not a date filter.

Thus an official route to **all published petition records** exists, but a directly supplied **monthly all-eligible denominator** was not verified. Building one from this route would require a separate, governed traversal of up to 438 published JSON pages, extraction of `opened_at`, and deduplication/acceptance; that was outside this hour. The CSV cannot supply the monthly denominator by itself. A query-zero is only zero within `q=climate`, never a zero for all published public/civic discourse.

## Fallback boundary

If Guardian terms or future month audits prevent a sustained media series, Carbon Brief is a narrowly scoped specialist-media **candidate** with accessible dated 2015 articles ([example](https://www.carbonbrief.org/carbon-briefs-15-numbers-for-2015/)). A one-record December 2015 WordPress API probe returned HTTP 403, so it is **not** a validated substitute or a source of monthly denominators in this snapshot. The smallest next step would be a bounded archive-page and rights check, not a silent switch of media source.

An Obama White House `We the People` archived-petition API was also checked as a possible civic alternative: the archived API route returned HTTP 404 and the old API host failed TLS in this runtime. Its [official archival documentation](https://petitions.obamawhitehouse.archives.gov/developers) itself warns that historical links may no longer work. It was not substituted for UK petitions.
