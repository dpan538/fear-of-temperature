# Field dictionary and counting contract

All dates are Gregorian. `month` uses the primary publication or creation date in UTC where a timestamp is supplied. Blank is **unknown, outside the audited source frame, or not reviewed**; numeric `0` is reserved for a defined reviewed set or a verified zero under a named query. The 49 × 3 matrix has one row per calendar month and discourse role.

## `paris_month_role_readiness_49x3.csv`

| Field(s) | Meaning |
|---|---|
| `month`, `role`, `event_month_offset` | Month, government/media/public role, and offset from December 2015 (−24 through +24). |
| `eligible_denominator_source`, `eligible_denominator` | Explicit source rule and count. Government: EPA original-date `final_rule` metadata only; public: distinct IDs in the archive `q=climate` query by creation month; media: unique nonvideo title cards on one fixed archive day. These denominators are **not interchangeable** and do not define all texts in a role/month. |
| `dated_independent_parent_count`, `readable_independent_parent_count` | Independent Work/document/petition/article parents observed and with readable authorial text under the stated count qualifier. Government figures are documented lower bounds from an earlier pooled checkpoint plus newly committed EPA bridge parents. Media dates and bodies were verified only for selected articles, not every archive card. Public counts are the complete keyword-query result, including rejected submissions. |
| `count_qualifier`, `coverage_state` | Boundary of the count and whether the finite source frame has readable text, only a verified query zero, or remains uncollected/unaudited. `verified_zero_within_keyword_query` is never a zero for public discourse or warming relevance. |
| `verified_warming_relevant_parent_count`, `verified_fear_relevant_parent_count`, `relevance_review_state` | Full-month relevance census fields. They are blank throughout because no full-month topical census was conducted. |
| `pilot_reviewed_parent_count`, `pilot_verified_climate_warming_parent_count`, `pilot_verified_anticipated_harm_parent_count`, `pilot_verified_explicit_fear_parent_count` | Counts **only among the finite pilot review subset** in that role-month. A zero here means reviewed zero within the subset; a blank means no pilot review in that month. Anticipated climate harm is distinct from an explicit fear expression. |
| `source_genre`, `evidence_paths` | Origin/genre and local traceability. |
| `uk_*`, `eu_*`, `us_*`, `au_*` | Source-specific dated/readable checkpoint parent counts for the government role; a EU Work is a parent, not each Item version. US values include the newly committed 125-parent EPA bridge on top of the earlier pooled snapshot. |
| `epa_eligible`, `epa_selected_readable` | Frozen EPA `final_rule` eligible parent denominator and acquired readable body count. EPA's own bodies occur in 10 of the 49 months. |

## Pilot files

`government_pilot_selected.csv` and `government_pilot_review.csv` use one row per independent UK policy/ministerial or EPA rule parent. `sampling_stratum` distinguishes the original hash selection from the explicitly post hoc exact-title supplement. `candidate_pool` and `control_pool` are source-month selection-frame sizes. `content_versions`, `object_kinds`, `attachment_count`, `segment_ids`, `segment_locator`, `segment_version_match`, `raw_paths` and `raw_sha256` are provenance checks or pointers. UK policy webpages and attachments remain one parent; the official EPA original is one content version with source and cleaned representations. `mapped_segment_count` is a small inspected UK segment count, but for EPA it is the accepted cleaned-segment count from the bridge ledger and **never** an independent observation count. `evidence_excerpt` is a short diagnostic passage, not full text. The review file adds `climate_warming_topic`, `anticipated_climate_harm_cue`, `explicit_fear_expression`, `label_basis`, and `review_note`.

`media_day_archive_frame.csv` holds unique nonvideo article title cards from the three archive days, with archive response SHA-256. `media_pilot_selected.csv` and `media_pilot_review.csv` hold selected article URL, original publication timestamp, later modification timestamp, body existence and a short excerpt. The full Guardian body is not redistributed.

`public_climate_query_frame.csv` contains the 177 distinct IDs returned across eight official archived petition search pages. `created_at` is the submission date used for this pilot's monthly bins; `opened_at` identifies publication; `rejected_at` and `state` keep nonpublished submissions separate. `action`, `background` and `additional_details` are petitioner-authored. `government_response_excluded` flags whether a response existed but was excluded from the public text. `public_pilot_2015_11_to_2016_01.csv` is the bounded 21-parent review subset; `public_pilot_review.csv` stores its manual labels. `public_query_month_counts.csv` gives the query-hit counts across its active period.

The SHA-256 values certify observed response bytes or previously accepted raw source files at the recorded snapshots; they are not proof that a website has never changed.
