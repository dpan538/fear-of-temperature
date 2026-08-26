# Fear of Temperature — Full Priority 180 Coverage Audit

Status: **COMPLETE for the provisional Priority population**

Research version: `fear-temperature-quant-v0.1-provisional`

Audit date: 2026-08-26

This is a candidate-level audit. Repeated strings at different anchors or voices remain separate research records, while technically identical external requests may share a cached measurement.

```ini
PRIORITY_CANDIDATES=180
PRIORITY_ACCOUNTED=180
```

```ini
NGRAM_EXACT=174
NGRAM_NORMALIZED_VARIANT=2
NGRAM_VALIDATED_ALIAS=3
NGRAM_TECHNICALLY_UNREPRESENTABLE=1
NGRAM_UNEXPLAINED=0
```

```ini
DICTIONARY_DIRECT_HEADWORD=25
DICTIONARY_TECHNICAL_GLOSSARY=49
DICTIONARY_NO_STANDALONE_HEADWORD=106
DICTIONARY_UNRESOLVED=0
DICTIONARY_UNEXPLAINED=0
```

```ini
SEARCH_PRIMARY_COMPLETED=180
SEARCH_PRIMARY_ZERO_RESULTS=39
SEARCH_PRIMARY_NONZERO_RESULTS=141
SEARCH_SECONDARY_COMPLETED=36
SEARCH_UNEXPLAINED=0
```

## What “accounted” means

Every Priority candidate has:

- one explicit Ngram strategy, including retained empty responses and one justified technical exception;
- one lexicographic record with a source, concise project paraphrase, historical sense, polysemy note, and anchor-sense match;
- one completed Internet Archive bounded-search measurement, plus strict and contextual-window measurements;
- candidate provenance retaining `RECONSTRUCTED_FROM_REPORT`.

The same value is not being measured three times. Ngram frequency, dictionary evidence, and discovery counts are parallel evidence dimensions with different denominators and meanings.

## Ngram accounting

The stored quantitative baseline is internally consistent:

| State | Count | Meaning |
| --- | ---: | --- |
| Provisional query rules | 143 | Reconstructed project rules, not recovered legacy IDs |
| Ngram-executable rules | 138 | Compatible with the verified public interface |
| Numeric 1842–2022 series | 132 | Complete unsmoothed annual series in the baseline |
| Explicit empty responses | 6 | Executed rules whose endpoint payload contained no usable series |
| Interface-incompatible rules | 5 | Preserved, not silently dropped |
| Failed rules | 0 | No baseline request failure |
| Unexplained rules | 0 | Every rule has an execution/accounting state |

The six executable rules outside the 132 numeric baseline series are not missing. They are the six `ZERO_RESULT` records:

1. `mean temperature of sea at surface`;
2. `sun's heat`;
3. `small increases in mean temperature`;
4. `Hottest Day for Ten Years`;
5. `Heat Wave Over Queensland`;
6. `changed climatic extremes`.

At candidate level, 170 deduplicated representable measurement forms were audited. Of these, 153 returned numeric series and 17 returned an empty payload. The exported annual grid contains 30,770 measurement-year rows: 27,693 numeric observations and 3,077 explicitly blank `NO_SERIES_RETURNED` rows. Blank rows are not numeric zero and are not claims of historical absence.

The candidate population maps as follows:

| Candidate form | Measurement form | Mapping | Reason |
| --- | --- | --- | --- |
| `40-degree temperatures` | `40 degree temperatures` | Normalized variant | Hyphenation only |
| `Be Worried. Be Very Worried.` | `be worried be very worried` | Normalized variant | Case and sentence punctuation removed; wording preserved |
| `anthropogenic CO₂` | `anthropogenic carbon dioxide` | Validated alias | Standard chemical abbreviation expanded |
| `well below 2°C above pre-industrial levels` | `well below two degrees above pre-industrial levels` | Validated alias | Symbolic threshold verbalized |
| `1.5°C above pre-industrial levels` | `one point five degrees above pre-industrial levels` | Validated alias | Decimal threshold verbalized |
| `heat wave/drought occurrences` | no single Ngram | Technically unrepresentable | Slash coordination contains two lexical objects; a linear substitute would change the object |

All other 174 candidate records use their report-visible surface form. Repeated forms such as `global warming` share the same underlying annual curve but retain separate anchor-specific statistics.

The corpus is the public current English dataset identified during the baseline run as `eng_CURRENT_ENGLISH_JULY_2024_DATASET`, retrieved for 1842–2022 with smoothing `0` and case-insensitive aggregation.

## Lexicographic accounting

The 180 candidate rows resolve to 171 unique lexical forms. Coverage uses three non-exclusive evidence strategies:

- direct headword evidence for simple conventional forms;
- authoritative technical or legal terminology for domain expressions;
- explicit `NO_STANDALONE_HEADWORD` treatment for titles, clauses, survey options, treaty formulations, and longer phrases.

No long proprietary dictionary definition is reproduced. The export stores concise project paraphrases and source metadata. Direct-access checks used the open DictionaryAPI.dev interface where responsive and stable Webster 1913 headword URLs. Technical meanings use sources such as the [IPCC glossary](https://www.ipcc.ch/site/assets/uploads/2018/02/WGIIAR5-AnnexII_FINAL.pdf), [IPCC AR6 Synthesis Report](https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_FullVolume.pdf), [Paris Agreement](https://unfccc.int/sites/default/files/english_paris_agreement.pdf), and relevant health/psychology terminology.

Important historical-sense decisions are visible rather than collapsed:

| Candidate | Anchor-sense match | Audit decision |
| --- | --- | --- |
| `climate` (1842) | PARTIAL | Regional/prevailing meteorological condition; not silently assigned the modern `climate change` issue meaning |
| `depressing effect` (1842) | DIFFERENT | Bodily/energetic lowering under oppressive heat; not modern clinical depression |
| `rather a coincidence` (1938) | STRONG | Epistemic evaluation; normally no affect |
| `global security` (1988) | STRONG | Institutional threat/security frame; threat without personal affect |
| `Be Worried. Be Very Worried.` (2006) | STRONG | Media imperative prescribing worry; not audience reception |
| `personally worry` (2007) | STRONG | Survey-elicited endorsement; wording remains instrument-supplied |
| `common concern of humankind` (2015) | DIFFERENT | Legal-institutional formula; not personal concern |
| `climate anxiety` (2022) | PARTIAL | Research construct unless participant self-use is independently evidenced |
| `very worried` (2022) | STRONG | Participant endorsement may be evidence, but lexical options are instrument-supplied |

Webster 1913 exposes stable public-domain headword routes, but automated page retrieval was inconsistent during this run. Where no response was cached, the row records that limitation and relies on the report-visible anchor context plus technical/general lexical evidence. It does not claim an inaccessible proprietary entry.

## Bounded search accounting

The primary source is the documented [Internet Archive Advanced Search API](https://doc-tools.readthedocs.io/en/ia-test-gsod/item-search-apis.html). For every candidate, it reports:

> `INTERNET_ARCHIVE_METADATA_TEXT_ITEM_COUNT`: the number of text items whose searchable metadata matches the exact quoted phrase at retrieval time.

This is not a full-text word count and not a measure of historical language prevalence. The pipeline separately stores:

- all available dates;
- the candidate's strict anchor window;
- the candidate's contextual validation window.

All 540 Internet Archive candidate/window rows completed: 342 are non-zero and 198 are zero. In the all-period candidate summary, 141 candidates are non-zero and 39 are zero. Zero is retained as a valid API result, not translated into historical absence.

[OpenAlex Works search](https://developers.openalex.org/api-reference/works/list-works) is the secondary source. Its metric is:

> `OPENALEX_WORK_COUNT`: the number of scholarly works discoverable through the quoted search expression and OpenAlex search fields.

OpenAlex completed 100 deduplicated source/window requests, corresponding to 36 candidate all-period rows after candidate mapping. It then returned an explicit anonymous daily-budget exhaustion response. Remaining OpenAlex rows retain that provider limitation rather than zero. The secondary source is therefore partial and is never substituted for the complete primary source.

The official [Google Books API volume-search interface](https://developers.google.com/books/docs/v1/using) was runtime-probed, but the available project returned quota value `0`. `GOOGLE_BOOKS_SEARCH_COMPLETED=0`; no `totalItems` counts were invented. This limitation does not affect the separately verified Google Books Ngram series.

## Selected quantitative observations

These observations describe strings in the current Ngram corpus, not historical emotions:

1. `greenhouse effect` peaks in 1990, `global warming` in 2009, and `climate change` in 2022, so the three framing strings have different corpus trajectories.
2. The three Priority records for `global warming` share one underlying curve but have different anchor measurements: approximately 0.640 per million in 1988, 4.178 for the 2006–2007 mean, and 3.964 in 2022.
3. `climate anxiety` reaches its interval maximum in 2022, but its first non-zero string observation is 1972. This is precisely why corpus-observed presence is not treated as coinage or semantic validation.
4. `depressing effect` has a non-zero 1842 Ngram value, while its 1842 sense is marked `DIFFERENT` from modern clinical depression. Frequency and sense evidence therefore cannot be collapsed.
5. Internet Archive all-period metadata search returns zero for 39 candidates even though those records remain lexicographically and, where possible, Ngram-accounted. Source/query zero is a result, not proof of historical absence.

## Outputs and reproducibility

- Master matrix: `data/fear-temperature/exports/priority180_full_coverage_matrix.csv`
- Candidate dictionary: `data/fear-temperature/exports/dictionary_coverage_180.csv`
- Unique-form dictionary: `data/fear-temperature/exports/dictionary_unique_forms.csv`
- Candidate search summary: `data/fear-temperature/exports/search_statistics_180.csv`
- Search long format: `data/fear-temperature/exports/search_statistics_long.csv`
- Candidate Ngram coverage: `data/fear-temperature/exports/priority180_ngram_coverage.csv`
- Candidate anchor statistics: `data/fear-temperature/exports/priority180_ngram_anchor_stats.csv`
- Full workbook: `outputs/priority180/fear_temperature_full_180_coverage.xlsx`
- Validation: `python3 scripts/fear-temperature/validate_priority180.py`

Raw API responses are cached under `data/fear-temperature/priority180/` with request URLs, retrieval timestamps, and SHA-256 values.

## Coverage gate and next phase

```ini
PRIORITY_ACCOUNTED=180
NGRAM_UNEXPLAINED=0
DICTIONARY_UNEXPLAINED=0
SEARCH_UNEXPLAINED=0
```

The 36 Expansion Candidates were not mixed into the Priority denominator and were not run in this task because the OpenAlex daily budget had already been exhausted. They remain a separately reported population.

The project is ready for the next phase: the **200-passage source-linked semantic retrieval pilot**. That pilot was deliberately not started here.
