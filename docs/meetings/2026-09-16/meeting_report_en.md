# Fear of Temperature
## Research direction and initial source-feasibility progress

**Dai Pan · Supervisor: Mashhuda Glencross · 16 September 2026**

### 1. Research focus and motivation

My project examines how fear and anxiety about rising temperatures are expressed across government policy, news media and public discourse. I am particularly interested in concerns about future living conditions, families and future generations, while also distinguishing these from immediate heat-related threats.

The research question has not changed. What has changed is how I intend to collect and analyse the evidence. The project is a computational study of a social question, using a validated NLP and temporal-analysis pipeline. The thesis and its empirical findings remain the main outcome, supported by a traceable corpus and reproducible code.

### 2. Why move from keyword searches to NLP?

The earlier approach relied mainly on keywords, dictionaries and Ngrams. These are useful for identifying explicit terms and tracking their frequency, but they depend heavily on which words I select in advance.

People can express similar concerns using very different language. Conversely, a passage containing a fear-related word may be a quotation, a denial or a general risk statement. Counting those words alone would not reliably tell us who is worried, what they are worried about, or whether the concern relates to immediate heat or a distant future.

I therefore plan to combine semantic retrieval with emotion, relation and topic analysis. The aim is to make the selection and measurement process more systematic and testable. This does not remove human interpretation or guarantee that a model is more accurate. Keyword and TF-IDF methods will remain as baselines, and the added value of NLP will need to be demonstrated on held-out examples.

### 3. Why use 1988 as the collection starting point?

The proposed collection range is 1988–2026. The establishment of the IPCC in 1988 provides a clear institutional anchor for studying the relationship between scientific assessment, policy communication and public discussion.[1]

This is a scope decision, not a claim that fear of warming began in 1988 or that a change in public emotion has already been demonstrated at that date. Earlier material, including the 1938 scientific context, can still inform the historical background.

Extending the main comparison much further back would introduce additional risks: sparse coverage, digitisation and OCR problems, changing language, different publication systems and uncertain denominators. These are anticipated limitations to investigate, rather than measured findings that earlier material is necessarily noisier.

The actual statistical analysis will use periods with sufficiently comparable coverage across the relevant sources. I will not assume that letters to editors, early forums and contemporary social platforms form one continuous public-emotion series. Changes in source composition will be recorded and checked separately.

### 4. How the computational workflow will operate

The planned workflow is:

**Source and denominator audit → permitted text collection → cleaning and passage segmentation → traceable database → encoding and semantic retrieval → NLP analysis → validation → temporal aggregation → interpretation.**

First, documents and passages will retain their dates, source identifiers and links to the original evidence. The database will distinguish the publishing institution from a quoted speaker and from the person or group whose emotion is being described.

Next, a Transformer sentence encoder, such as a Sentence-BERT model, will turn passages into embeddings. The encoder produces the vectors; it is not a separate step applied after vectorisation. A natural-language query can be encoded with the same model, allowing passages to be ranked by cosine similarity.[2]

For example, a query about concern for future generations might retrieve relevant passages that never use the word “fear”. However, semantic similarity measures relevance to a query, not emotional intensity. Retrieved passages still require contextual analysis and validation.

Three required NLP components will then address complementary tasks:

| Component | Purpose | Candidate approach |
|---|---|---|
| Emotion analysis | Identify the emotion, its target, holder and time horizon | An evaluated emotion classifier, with climate-specific annotation |
| Event and relation extraction | Recover events, causes, blame and duties with supporting text spans | Entity and semantic-role analysis combined with contextual relation extraction |
| Topic and semantic analysis | Examine themes and framing across roles and periods | BERTopic or a comparable evaluated topic workflow |

The exact model checkpoints are not yet fixed. GoEmotions can inform the emotion component, but it is a dataset rather than a single model, and its labels cannot simply be treated as a validated climate-anxiety scale.[3] BERTopic is a candidate for embedding-based topic analysis, rather than a commitment to invent a new model architecture.[4]

These components can share passage identifiers and versioned representations without necessarily using the same classifier or being jointly trained. Their outputs will be evaluated before aggregation, including checks across sources and periods.

### 5. Why three research questions?

| Research question | What it explains | Planned analysis |
|---|---|---|
| **RQ1: Who changes first?** | Leading, lagging and synchronous patterns across policy, media and public expression | Cross-correlation and conditional VAR, including predictive comparison with an own-history baseline |
| **RQ2: What changes around events?** | Changes in level or slope around selected physical, scientific or policy events | Segmented regression / interrupted time series, with window and placebo-date checks |
| **RQ3: How is fear explained?** | Narratives of causes, affected groups, blame and responsibility | Evidence-linked relation extraction, topic analysis and contextual interpretation |

These questions connect timing, events and meaning. A time series alone would not explain what people fear or how responsibility is assigned. Textual interpretation alone would not establish the sequence of changes across communication roles.

The temporal models will support statements about association and predictive relationships. They will not automatically establish that one communication channel caused another to change. Publicly expressed emotion also cannot be treated as a direct measure of the psychological state of an entire population.

### 6. What has been completed this week?

The first completed task was a bounded source-feasibility check, rather than a model experiment. I tested whether a policy source could provide a reproducible list of records, reliable dates and a clearly defined document-level denominator.

The pilot used GOV.UK records tagged to DEFRA, classified as `policy_paper`, and first published during July 2026. According to the saved collection and validation records from 16 September:

| Check | Recorded result |
|---|---:|
| Matching indexed records | 9 |
| Accessible Content API records and public pages | 9/9 |
| Pagination check | 5 + 4; same record set |
| Missing key metadata fields | 0 |
| Duplicate identifiers or URLs | 0 |
| Records linked to multiple organisations | 3 |
| Document bodies retained for analysis | 0 |

The outcome is a **conditional go for this narrowly defined source window**. It does not demonstrate complete historical coverage, represent all DEFRA publications, or establish a paragraph-level denominator.

A practical finding was that the Search API could filter by first publication date but did not support sorting by that field. The dates were therefore checked through the Content API and sorted locally. The three multi-organisation records also show why an explicit counting rule is needed.

No embeddings, emotion scores or temporal relationships have been estimated yet. The value of this first step is that it establishes what belongs in the denominator before asking what proportion of the material concerns warming.

### 7. Plan for next week: 21–27 September

Within approximately **10–20 hours**, I plan to:

1. Preserve the current snapshot, repeat the bounded-window check, and inspect a small number of historical windows for coverage differences.
2. Document the date fields, units of analysis and options for counting jointly associated documents.
3. Subject to the required supervision, ethics and rights arrangements, test document-to-passage extraction on three documents while preserving provenance. If those conditions are not ready, continue metadata work and clearly labelled synthetic-data checks.
4. Draft an initial semantic-query set and emotion-annotation guide.
5. Prepare a small lexical-versus-embedding retrieval demonstration if the environment and permitted text are ready.

The priority is a reliable small data workflow. Completing all emotion models or running VAR is not a next-week commitment. Before any collection rerun, the original outputs need to be preserved because the existing script can overwrite them.

### 8. Reading plan

| Paper | Reading focus | Intended output |
|---|---|---|
| Reimers & Gurevych (2019), *Sentence-BERT* [2] | Sentence representations and semantic retrieval | A lexical-versus-semantic retrieval comparison plan |
| Pihkala (2022), *Toward a Taxonomy of Climate Emotions* [5] | Boundaries between fear, anxiety, worry and related emotions | A draft annotation guide |
| Demszky et al. (2020), *GoEmotions* [3] | Labels, source data and transfer limitations | A label-to-construct mapping |
| Brulle et al. (2012), *Shifting public opinion on climate change* [6] | Explanatory variables and temporal research design | Notes on candidate controls and RQ1 |

The first two are priorities for close reading; the other two are targeted readings. These are planned activities, not claims of completed full-text review.

### 9. Points for supervisor discussion

- Is the proposed historical scope appropriate, with statistical comparisons restricted to defensible common windows?
- How should jointly associated policy documents be counted within and across institutional groups?
- What supervision, ethics and rights steps should be completed before a small substantive-text pilot?

### Closing summary

The project still asks how society expresses and explains fear of rising temperatures. The methodological change is to move from manually selected search terms towards a traceable corpus, validated NLP measurements and temporal comparison. This week established the feasibility of one bounded policy-data window. The next step is to strengthen that data foundation and connect a small amount of permitted text to a reproducible analysis workflow.

## Sources and evidence

1. IPCC. *History*. https://www.ipcc.ch/about/history/
2. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence embeddings using Siamese BERT-networks*. https://aclanthology.org/D19-1410/
3. Demszky, D., et al. (2020). *GoEmotions: A dataset of fine-grained emotions*. https://aclanthology.org/2020.acl-main.372/
4. Grootendorst, M. (2022). *BERTopic: Neural topic modeling with a class-based TF-IDF procedure*. https://arxiv.org/abs/2203.05794
5. Pihkala, P. (2022). *Toward a taxonomy of climate emotions*. https://www.frontiersin.org/journals/climate/articles/10.3389/fclim.2021.738154/full
6. Brulle, R. J., Carmichael, J., & Jenkins, J. C. (2012). *Shifting public opinion on climate change: An empirical assessment of factors influencing concern over climate change in the U.S., 2002–2010*. https://link.springer.com/article/10.1007/s10584-012-0403-y

Local design source: `proposal/thesis_proposal.md`. Pilot evidence: `work_packages/M1_source_access/01_feasibility/checks.json`, `document_sample.csv`, `denominator_assessment.md` and `meeting_brief.md`. This report summarises those saved records; it does not constitute a new online collection run.
