# Round 2 CSV additions and supersession rule

The [round-2 49×3 matrix](paris_month_role_readiness_49x3_round2.csv) copies all government rows from round 1. It replaces December 2015 media counts with the verified current Guardian archive candidate frame and uses **published-only/opened-at** for public rows in the July 2015–April 2017 UK petition keyword-query coverage period. It leaves the original matrix in place as a dated snapshot. See the [base field dictionary](../FIELD_DICTIONARY.md) for all unchanged fields.

| Field | Meaning |
|---|---|
| `round2_snapshot_utc` | Local table generation time, after the earlier source snapshots. |
| `media_monthly_candidate_date_verification` | For December 2015, the 31 daily archive pages and 396/396 checked original timestamps. The `eligible_denominator` and `dated_independent_parent_count` of 396 refer only to the current environment/nonvideo archive candidate rule. `readable_independent_parent_count=4` is a **verified lower bound** from distinct body-checked articles, not a 396-article full-body audit. |
| `public_all_submitted_query_created_count` | All 177 official `q=climate` query IDs mapped by `created_at` month, including rejected petitions. This is a sensitivity count, not the main public-role series. |
| `public_rejected_query_created_count` | Rejected query IDs by `created_at` month. They lack `opened_at` and are excluded from the main published role. |
| `public_published_query_created_count` | Eventually published query IDs binned by submission/creation month; shows the date lag against the main series. |
| `public_published_query_opened_count` | Published query IDs binned by `opened_at` month. This is the main public/civic **query-frame** count and equals the public row's eligible/date/readable count only within the 177-ID search frame. It is not the all-eligible monthly petition denominator. |

For public November 2015, `0` is a verified zero of **published `q=climate` hits by `opened_at`** only. It does not establish that no public climate discussion or fear expression occurred. Blank full-month relevance fields remain unassessed. `pilot_*` fields in November 2015–January 2016 were remapped to the reviewed published query hits by `opened_at`; no other pilot labels were promoted to monthly rates.
