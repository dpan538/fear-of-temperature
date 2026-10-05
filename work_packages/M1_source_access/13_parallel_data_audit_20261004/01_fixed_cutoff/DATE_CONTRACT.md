# Fixed publication-date contract — proposed integration

**Status:** review proposal, 4 October 2026. The study publication interval is **1988-01-01 through 2026-09-21 inclusive**. September 2026 is partial. The corresponding UTC timestamp half-open interval is `[1988-01-01T00:00:00Z, 2026-09-22T00:00:00Z)`. This timestamp representation does not imply that every source uses UTC calendar dates or was observed until the final second of September 21.

## Four clocks

1. **Publication:** source-evidenced day, timestamp, or bounded precision interval. This alone determines eligibility and monthly placement after its basis is recorded.
2. **Retrieval/extraction:** when metadata or body bytes were fetched or parsed. This supports observation provenance, not a fallback publication date.
3. **Content version/modification:** when a source says its page or document changed, or which bytes were saved. Later retrieval of a 2005 page does not prove the captured wording was present in 2005.
4. **Report/snapshot:** when counts were computed. An October report still ends its publication interval on September 21.

The 04 GOV.UK scope fixes the inclusive *query date* on September 21 but documents a first Search API observation from **2026-09-21 01:05:02 to 01:10:54 UTC**. The 06 collection authorisation is separately recorded at **2026-09-21 06:01:20 UTC**. The 04 enumeration summary was generated at **01:10:55 UTC**. These are observation, permission and report/summary times, respectively. They do not identify one exact global extraction-start second. The accepted study endpoint is day precision from that initial collection period.

## Proposed classification

Use `boundary_filter.py` on publication evidence only. An exact day inside the interval is included; a post-cutoff or pre-1988 exact day is outside. A month/year is a possible date interval: include only if its entire interval falls inside scope, mark it **uncertain** if it crosses either boundary, and never invent day 1 or day 21. A missing or unsupported date remains unresolved. An offset-aware timestamp is converted to UTC for the proposed timestamp comparison; a timezone-less timestamp is invalid for that comparison until its source timezone is established. Keep original strings, offsets and date precision.

Out-of-range and uncertain records stay in raw/source metadata and in an exception ledger; derived in-window counts omit them until review. A changed date or mapping needs an evidence-linked derived repair. Neither duplicate suspicion nor date uncertainty authorises deleting the source object.

| Evidence input | Proposed result | Why |
|---|---|---|
| day `1988-01-01` or `2026-09-21` | included | inclusive edges |
| day `1987-12-31` or `2026-09-22` | outside | exact day beyond an edge |
| unknown original date | missing | no publication fallback |
| month `2026-08` | included | entire month precedes the end |
| month `2026-09` or year `2026` | uncertain | interval overlaps post-cutoff days |
| `2026-09-22T00:30:00+01:00` | included under UTC timestamp convention | UTC day is September 21; keep source-local day too |
| `2026-09-21T23:30:00-01:00` | outside under UTC timestamp convention | UTC day is September 22 |
| `2026-09-21T23:30:00` without offset | invalid pending timezone | cannot safely select a UTC day |

### GOV.UK local-day conflict requiring one explicit decision

The 06 coverage report calls `first_published_at` a UTC calendar date. The 04/07 ingestion instead stores `datetime.date()` from the original offset timestamp. In the read-only metadata, **119** GOV.UK parents have `+01:00` at local midnight, so their stored publication day is one day later than the UTC date of `publication_timestamp`; all 119 stored dates match the raw source-local date. Both possible dates lie within the study interval, so study membership does not change. **Three** cross a month boundary, so monthly counts can change. See `date_exceptions.csv` and `date_counts.json`. The coordinator should choose a documented analysis-day convention after checking GOV.UK Search/Content API date semantics, retain both raw and normalized dates, and regenerate affected monthly derivatives once. Do not silently rewrite the 119 source dates.

### Source-specific roles

| Source frame | Publication date evidence | Important constraint |
|---|---|---|
| GOV.UK DEFRA and historical policies | Content API `first_published_at` | `updated_at` is version evidence. The first Search observation is narrower than a full September 21 day. |
| UK Parliament written answers/statements | Official answer/made date or parliamentary sitting date, with basis per genre | The historic ingester has a `dateAnswered`/`dateMade` fallback to the list row date. Review fallback records before asserting exact answer timing. |
| US Federal Register EPA/DOE RULE/PRORULE | Official `publication_date`, day | The selected 1994–2026 API ledger is fixed to September 21; attachment formats are not extra parents. |
| AU DCCEEW catalogue | Original Work/issue date only when evidenced | CMS `created_at` is not original publication. Year/month evidence stays at its true precision. The 821 landing URLs are candidates, not 821 dated Works. |
| EU CELLAR Commission preparatory | `cdm:work_date_document` at Work level | Item retrieval and Expression/Manifestation dates do not replace the Work date. September 2026 query uses exclusive `2026-09-22`. |
| Media and civic pilots | Original article publication and relevant petition opened/created fields | Article modification time and petition submission/opening play separate roles; pilot outputs are not the corpus frame. |

## Integration checks

- Assert the fixed start/end values in every collector and report entrypoint, including a *day-level* check for the final month. The pooled AU report currently checks `date[:7] <= '2026-09'`, which would admit an evidenced September 22–30 day if such a row arrived later. No such dated AU row is in the queried DB snapshot.
- Rename or relabel the 08 AU `within_cutoff` field: it is calculated from CMS creation time. Two candidate cards have CMS dates after September 21, but neither original Work date is established. Keep both candidates pending original-date review.
- Stage EU Work dates with an assertion of the exact day range; `--end 2026-09` alone is a month selector, not a day-level guarantee. The audited current staged Work dates all pass.
- Treat `datetime.now()`/`date.today()` in current source code as acquisition, retry or report times where so used. Do not allow those values, filesystem modification times, or the latest fetched record to become a default publication end.
- Preserve source-specific first/last observation times and publication-date precision. A day-level study cutoff does not prove an end-of-day source snapshot.

## Later backfill

A later query may discover or recover an independently dated 1998 parent, or an eligible parent dated September 21 or earlier, and add it to a new committed snapshot **inside the same fixed interval**. Store its 2026/2027 retrieval time and content-version evidence separately. Backfill may change counts or observed source coverage but cannot change the publication endpoint or establish historical body-version fidelity. Moving the endpoint past September 21 requires Dai's explicit decision and a new corpus version.
