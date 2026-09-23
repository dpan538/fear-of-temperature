# Temporal reference availability — 23 September 2026

Study interval: 1988-01-01 to the frozen acquisition cutoff 2026-09-21. There are 465 calendar-month bins and 155 quarter bins; September 2026 and 2026 Q3 are incomplete calendar periods.

This read-only assessment answers whether an interval contains a stored record linked to non-empty extracted text. It does not establish full-body completeness, clean text quality, climate relevance, independent sample size, adequate statistical power or complete historical population coverage.

## Method

Read the authoritative 06 DuckDB with `read_only=True`. Identify policy records by content_type policy_paper/guidance; match non-empty text via document_content_objects → content_versions → text_segments. For ministerial records, match voice_attributions → text_segments. Deduplicate document identities before aggregating by publication month. The voice link establishes associated text, not a fresh audit of all speaker labels. Policy pages/attachments can provide partial text: a document with text is not proof that every attachment has been extracted.

Join these text-bearing document counts to the existing monthly coverage CSV. Preserve its separate route-completeness status. Sum monthly counts by quarter and count months with text; do not convert quarterly presence into monthly completeness.

All 248,035 stored records in the study interval have some linked non-empty extracted text. This is consistent with outstanding content-object failures because a record can have more than one content object. No database, acquisition status, extraction or proposal was modified.

## Results

| Series | Records with associated text | Months with text / 465 | Quarters with text / 155 |
|---|---:|---:|---:|
| Policy-source records | 1,055 | 229 | 98 |
| Ministerial written answers | 244,229 | 421 | 155 |
| Ministerial written statements | 2,751 | 257 | 96 |
| At least one of the three series | 248,035 | 434 | 155 |
| All three series present in the same bin | — | 198 | 88 |

Therefore every quarter has reference material, but 31 months have no material in any of the three series. The smallest quarter by associated-text record count is 2010 Q2 (356 records across the three series); this is not an adequacy threshold and does not resolve that quarter's enumeration gap.

## Completely empty months across the three series

- 1988: August, September
- 1989: August, September
- 1990: August
- 1991: August, September
- 1992: August
- 1993: August, September
- 1994: August, September
- 1995: August, September
- 1996: August, September
- 1997: April, August, September
- 1998: August
- 1999: August
- 2000: August, September
- 2001: August, September
- 2002: August
- 2003: August
- 2007: August
- 2008: August
- 2015: April, May

Calendar/sitting context can explain parliamentary inactivity, but no new calendar validation was performed here. An empty government bin cannot establish absence of policy publications while their historical population remains unknown. Do not invent/interpolate source documents to fill such months.

## Early policy availability

| Interval | Months with policy text | Records |
|---|---:|---:|
| 1988–1992 | 0 / 60 | 0 |
| 1993–1999 | 7 / 84 | 7 |
| 2000–2009 | 44 / 120 | 83 |
| 2010–2026 cutoff | 178 / 201 | 965 |

The historic-policy track remains the main missing reference series. Early ministerial answers provide government speech but cannot replace missing policy-publication records.

## Unknown enumeration does not mean no text

The current coverage table marks these parliamentary series-months unknown:

| Series | Month | Records with text |
|---|---|---:|
| Answers | 2004-11 | 882 |
| Answers | 2010-05 | 0 |
| Answers | 2012-05 | 245 |
| Answers | 2013-05 | 182 |
| Answers | 2014-06 | 253 |
| Statements | 2004-10 | 6 |
| Statements | 2004-11 | 22 |

These retain unknown completeness even where hundreds of reference records exist. Monthly/quarterly presence is not population coverage.

## Files and reporting recommendation

- `monthly_reference_availability.csv`: each genre/month, record counts, associated-text counts, presence flag and previous acquisition coverage state.
- `quarterly_reference_availability.csv`: each genre/quarter, counts and number of months with text.
- `annual_reference_availability.csv`: each genre/year, counts and number of populated months.
- `months_without_any_reference.csv`: the 31 fully empty months with all three genre rows and their inherited states.

Future coverage summaries should lead with this presence table and distinguish: (1) whether there is any reference text, (2) how many records and months contribute, and (3) whether the enumerated source coverage is complete. Figure 5 currently focuses on (3); it should not be read as a map of text presence. Maintain the current evidence figure and add the presence view or count labels when it is next revised, rather than replacing completeness with volume.
