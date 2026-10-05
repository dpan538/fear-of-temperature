# Five-minute group-meeting speaking script

**Fear of Temperature: research direction and initial source-feasibility progress**  
Dai Pan · 16 September 2026

## 0:00–0:35 — Topic and purpose

Today I will explain why the project is moving from keyword searches towards a validated NLP evidence chain, and what I actually completed in the first M1 source-feasibility pilot.

The topic has not changed. I am studying how policy, news media and public communication express fear and worry about rising temperatures. The three questions are: who changes first, what changes around events, and how causes, affected groups, blame and response duties are narrated.

## 0:35–1:15 — Why move beyond keywords?

Keywords, dictionaries and Ngrams remain useful, transparent baselines. But they depend on words selected in advance. Concern may be expressed without the word “fear”, while a fear-related word may occur in a quotation, denial or unrelated context.

The new design adds a traceable corpus and semantic retrieval. Every result must retain its source, date, passage and speaker context. A Sentence-BERT-type encoder counts as an improvement only if held-out evaluation shows a clear, interpretable gain over the lexical baseline. Semantic similarity is not emotional intensity.

The year 1988 is a collection anchor associated with the establishment of the IPCC, not a claim that fear began then. Final comparisons will use the period with reliable common coverage.

## 1:15–2:05 — Planned workflow and research questions

The planned chain begins with sources, rights and denominators, then moves through cleaning and passage segmentation; semantic retrieval; emotion, relation and topic analysis; validation; temporal aggregation; and interpretation linked back to original passages.

RQ1 asks who changes first. Cross-correlation will explore lags, and a small conditional VAR may test predictive information beyond a series’ own history. This is not automatic causation.

RQ2 asks what changes around independently dated events. Interrupted time series may estimate level and slope changes, with alternative windows and placebo dates. An association may still reflect anticipation or a common shock.

RQ3 asks how fear is explained: who is threatened, what cause is described, and how blame or response duty is assigned. This requires evidence-linked relations, quotation scope, stance and original text.

## 2:05–3:15 — What was completed this week

This week I did not collect climate keyword hits. I tested whether one policy source could provide a reproducible denominator. I fixed the source as GOV.UK, the organisation tag as DEFRA, the document type as `policy_paper`, and the first-publication window as July 2026.

The saved Search API response reported nine records and returned nine. Splitting the request into two pages produced five plus four records, and the union matched the complete set. I checked every record through the Content API and its public page. All nine were accessible. First-publication date, update date, type and organisation metadata were present, with no duplicate content IDs or canonical URLs.

This is a conditional go for that narrow document set. The denominator is nine GOV.UK landing pages—not all DEFRA output, all UK policy, or a paragraph denominator. A deliberately non-climate example confirms that the denominator was not constructed from climate search results.

Document bodies and paragraph examples remain at zero. I have not produced embeddings, emotion scores, topics, relations, S, E or B estimates, cross-correlations, VAR or interrupted time-series results.

## 3:15–4:00 — Technical findings and limits

The pilot revealed two practical issues. The Search API accepted `first_published_at` as a filter but did not return populated values for that field, and sorting by it produced HTTP 422. I therefore verified dates through the Content API and sorted locally.

Three records had multiple organisations. The pilot counted each page once when DEFRA was among its tags, but later analysis needs a pre-registered rule: all organisations, lead organisation only, or fractional weights.

A complete one-month snapshot does not establish coverage from 1988 to 2026. Open-licence content may still have attachment, third-party and personal-data exceptions.

## 4:00–5:00 — Next week and decisions

For 21 to 27 September, within ten to twenty hours, I will preserve this snapshot and audit one recent, intermediate and earlier window. I will draft date, unit and organisation-counting rules. Only if supervision, ethics and rights conditions are clear will I test passage provenance on three public documents; otherwise I will remain at metadata level.

The reading plan is to closely read Sentence-BERT and Pihkala’s climate-emotion taxonomy, with targeted reading of GoEmotions and Brulle and colleagues’ temporal design. These are planned readings, not completed work.

I need guidance on three decisions: whether final comparisons should use the best common coverage window even if collection begins in 1988; how jointly associated policy documents should be counted; and what supervision, ethics advice and rights checks are required before the three-document passage pilot.

My principle is simple: make the denominator, evidence location and validation chain defensible before running complex models.

## Short answers for likely questions

**Why not train a model immediately?** Without a stable source, aligned denominator and traceable units, model outputs cannot be interpreted as changes in attention or emotion.

**Why 1988?** It is an institutional collection anchor associated with the IPCC, not an emotional origin or demonstrated breakpoint.

**Do the nine records show climate fear?** No. They only show that one bounded policy-document set could be enumerated completely at the saved index time.

**Why retain the keyword baseline?** It measures what semantic retrieval adds and which new errors it introduces.

**Why are document bodies still zero?** This pilot tested the index, dates, denominator and rights route. Text retention requires supervision, ethics and item-level rights decisions.
