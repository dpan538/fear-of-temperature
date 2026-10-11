# Source context and author-location metadata

This contract is prospective. The accompanying tables derive source context from closed metadata; they do not retrofit measured author countries onto existing bodies.

Record `source_id`, native actor/site ID, native body ID, work/version/parent relationships, carrier/genre, publication time, retrieval time and source observation interval independently. A platform is not one community, and multiple instances, blogs or newspaper titles are not automatically independent publishing parents.

Keep these geography dimensions separate:

| Dimension | Required evidence | Unknown handling |
| --- | --- | --- |
| Newspaper title/publisher country and region | Publisher identity/contact or accepted source admission evidence, observation date and scope | Preserve unresolved country within an accepted regional stratum. Current publisher location does not establish historical ownership. |
| Social community context | Explicit community description, evidence URL and observed date; distinguish target community from operator location | Global, mixed and unresolved are valid categories. Instance geography does not locate all participants. |
| Individual author's self-declared country | Explicit country statement in a public source-visible profile or author statement, observed date and evidence reference | Record as self-declared, time-specific and potentially outdated. Do not infer from names, language, server, topic, platform headquarters or geotags of a discussed object. |
| Individual publication location | Native location attached to that body with documented meaning and consent/access conditions | Keep separate from nationality, residence and profile location; do not collect precise coordinates just to produce country totals. |

The minimal additive geography fields are `source_context_country`, `source_context_region`, `source_context_evidence_ref`, `source_context_observed_at`, `community_context_scope`, `author_country`, `author_country_evidence_type`, `author_country_evidence_ref`, `author_country_observed_at` and `author_country_status`. Use `unmeasured`, `not_stated`, `ambiguous`, `self_declared` or `conflicting`; missing author location is retained and reported. These are evidence categories, not confidence scores or exclusion criteria.

Ordinary public expression, institutional accounts, publisher/editorial accounts, personal blogs, forum posts and technical lists remain distinguishable source frames. Account/cohort selection must have a traceable nonsemantic rule. Do not select accounts or retain bodies using climate, fear or emotion words. A documented API route does not grant a content license, permanent retention or complete historical visibility.

Future outputs should report source-country/region × month/year × genre, contributing title/community/actor units and parent-unknown mass, plus author-country totals and missingness when measured. Report applicable source eras separately from the 465-month calendar. Do not use geography shares, source counts, body counts or distribution diagnostics as quotas or stopping rules.
