# Prespecified 2015 source-text bridge rule

Frozen before new requests on 27 September 2026, after the US sequential supervisor stopped on its 11:27 UTC HTTP 429 and committed its preceding tranche. This is a bounded acquisition and source-continuity check, not topical selection or an effect estimate.

## Source and parent rule

- Existing source namespace: `us_fr_epa_doe_rules_1994`, FederalRegister.gov official public API enumeration and original document text. No new global enumeration or climate keyword filter.
- One independent parent per canonical Federal Register document URL; agency membership must include **EPA** in the frozen `agency_strata`, and the frozen genre must be **`final_rule`**. A cross-agency hit is still one parent.
- Month follows the original Federal Register **publication day**, not download, update or portal time. The source text is its verified official raw-text representation or the existing documented official GovInfo HTML fallback for an individual 404/410.
- Frozen enumeration file SHA-256: `0bf7e771bbba01785975942e8744c7542338079a3d18b415109ea3836176c46b`. The [125-parent selection](selected_parents.csv) SHA-256 is `eccf91b0890afc5bd2596b32859a98153424ed17f4204d29d8e3bcfc122afcfd`.

## Fixed denominator and retrieval set

The [2012–2019 metadata frame](metadata_frame_2012_2019.csv) has 4,407 eligible distinct parents in 95/96 months; **2019-01 is a verified zero for this exact frozen series**. The Paris comparison window, 2013-12 through 2017-12, has 2,304 eligible parents and at least one in each of its 49 months. These are eligible-document denominators, not downloaded-body counts.

Fetch **all 63** eligible parents dated 2015-04 and **all 38** dated 2015-05. For source-continuity validation, fetch three deterministic parents in each of eight other months: 2013-12 and 2017-12 as window endpoints; 2015-03 and 2015-06 as adjacent months; 2014-04/05 and 2016-04/05 as same-calendar-month comparisons. Sort each month's eligible parents by `(publication_date, document_number, canonical_url)` and take indices `floor((N−1)×q/10)` for `q = 1, 5, 9`. This yields **24** validation parents and **125** selected parents in total. The sample checks date, genre, extraction and source composition; it is not a monthly census outside the two gap months or a climate-relevance sample.

## Acceptance and limits

For every selected parent, keep original bytes and request evidence, verify the saved hash, map to the original canonical parent and date, insert a content version and nonempty source text, and retain cleaned text as a separate representation. Report each month as metadata-only, downloaded, extracted, or unresolved/verified-zero. The two gap months gain government stored-text presence only after at least one independently dated selected parent in each has committed nonempty source text. Full gap-month acquisition requires all 101 parents or an explicit per-object exception; a few successful examples cannot establish the frozen series census. The validation sample supports a bounded comparability check only if the selected parents across months retain the same EPA/final-rule/date rule and extractable official text. Even 24 successful samples do not prove complete 49-month text acquisition.

Do not request before **2026-09-27 12:27:03 UTC**, one hour after the latest FederalRegister.gov HTTP 429, subject to any later source `Retry-After`. Hold the existing US supervisor and polite-wrapper locks during the target fetch and insertion; stop on 403/429/503 or repeated transport failures, and keep at least 15 GB of disk space. The concurrent EU Item supervisor owns a different stage database and must not be duplicated.

If the US series cannot be bridged within these safeguards, the smallest already enumerated alternative is the frozen EU Commission `COM`/`cdm:act_preparatory`/English Work series: its Paris metadata frame is positive in 49/49 months, with 71 dated Works (69 English Item links) in 2015-04 and 92 (91 links) in 2015-05. The EU Item writer would first need its own safe checkpoint; EU metadata alone does not fill either source-text gap.
