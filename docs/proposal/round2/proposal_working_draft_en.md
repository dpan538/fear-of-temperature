---
title: "Fear of Temperature: computational analysis of social emotions and their temporal relationships with climate and policy events"
author: "[Official UQ MySI-net name to be confirmed]"
date: "[Submission date to be confirmed]"
lang: en-AU
bibliography: references.bib
---

> Working draft, started 15 September 2026. This version implements the author's latest research positioning. Sections are being written incrementally using the supplied UQ proposal template. Editorial placeholders and this note will be removed before submission. The title remains provisional. This file does not replace the original second-round materials.

**Supervision:** [Names and roles to be confirmed]

# Use of AI Statement

**Have you used AI to explore your topic?** Yes. ChatGPT and Codex assisted discussions of Fear of Temperature, including its focus on social emotions and the use of computational methods to investigate them. I corrected AI interpretations that shifted the project towards a retrieval-system study or treated cultural heritage as an established premise.

**Have you used AI to define your research question?** Yes. AI assisted the formulation and critical review of questions about warming-related emotions, event narratives, changing topics and temporal relationships between policy and public discourse. The questions below are provisional and will be refined through source assessment and supervisory discussion.

**Have you used AI to assist with your literature review?** Yes. Web-assisted AI research helped locate and compare methodological and substantive literature. The accompanying research notes distinguish the sources and sections inspected from material still requiring further reading. I remain responsible for the accuracy of citations and interpretations in the submitted proposal.

**Have you used AI to assist with formatting the answers presented here?** Yes. AI assisted English drafting, organisation, translation and language editing. Final formatting will follow the supplied template.

**Have you used AI for other aspects of your work?** Yes. AI assisted technical feasibility review, research decision recording and the comparison of proposed analysis methods. This proposal revision did not collect a new corpus or run the proposed NLP and time-series experiments. Earlier project work will be disclosed from its actual records.

I acknowledge the use of generative AI tools in completing this assignment. Details of which tools were used and how they were used are provided in the table below, along with appropriate in-text and full references. I take responsibility for critically evaluating and integrating the AI-generated content, and ensuring it adheres to academic integrity standards.

| AI tool and recorded use | Activities relevant to this proposal |
|---|---|
| ChatGPT; project discussions recorded on 11 and 15 September 2026; exact model versions to be confirmed from records | Topic exploration, research questions, literature assistance, methodological critique, writing and language support |
| Gemini; date and model version to be confirmed | Suggested analysis modules and an agenda-setting and lag-analysis direction, subsequently selected and revised by the author |
| Codex; 15 September 2026; exact model identification to be completed from the usage record | Material review, source checks, decision recording, feasibility review and incremental Markdown drafting |

> Editorial task: transfer this factual record into the template's AI-use table and add verified tool references before submission. Do not inherit example dates or model names from the template.

# Contents

Use of AI Statement  
1. Introduction  
2. Background and Literature Review  
3. Project Plan  
References

> Page numbers will be generated during final typesetting.

# 1. Introduction

## 1.1 Motivation and significance

Fear of Temperature investigates social emotions associated with rising temperature and climate change. It asks how fear and related responses are expressed, what consequences and events they are connected to, and how their prominence changes across policy and public discourse. The substantive interest is in the social experience and communication of warming. Natural language processing (NLP) and artificial intelligence provide the principal means of collecting and analysing the textual evidence needed to investigate that interest at scale.

A central empirical problem is the relationship between physical conditions, public communication and emotional expression. Climate-related concern has previously been studied in relation to extreme weather, scientific information, media coverage and political cues [@brulle2012]. Research on affective agenda dynamics has also examined temporal relationships between government, media and public expressions using social-media time series [@zhou2023]. These precedents motivate an investigation of how warming-related attention and emotions develop around climatic conditions and scientific or policy events. The project will examine competing and potentially interacting explanations rather than prescribe a single sequence of influence.

The earlier phase of Fear of Temperature used lexical inventories, dictionary-based search and n-gram analysis to explore temperature-related discourse. The proposed phase will extend this work through a newly collected natural-language corpus, structured database records, Transformer-based text representations and semantic retrieval. Three analytical components will then examine events and relations, aspect-specific sentiment and emotions, and topics and semantic patterns over time. Their outputs will support a common investigation of social emotions, with temporal analysis connecting textual patterns to independently recorded events and climate observations.

This methodological transition is intended to reduce dependence on the researcher's manual selection of expressions and individual passages. Consistent computational procedures will enable a broader body of material to be searched and analysed under documented rules. Limited, structured validation will assess what those procedures actually measure, including whether an emotional expression concerns warming, its anticipated consequences or a policy response. This distinction matters: criticism of an expensive climate policy and fear of future heat damage can both contain negative language while expressing different attitudes towards different objects.

## 1.2 Scope and temporal framing

The collection will prioritise English-language material associated with the United States, Europe, Australia and New Zealand. Broad geographical coverage is a research objective. Policy and institutional texts will be compared with accessible public social-media and forum material. Candidate sources include Facebook, Reddit, YouTube comments, Bluesky, Mastodon, and selected public discussion and question-and-answer forums, including relevant Stack Exchange communities. Media material will be included where needed to examine communication across institutional, media and public sources. The study will document source roles, geographical attribution and the limits of English-language coverage; English text alone will not establish a writer's location or cultural identity.

Around 1988 is the preferred starting point for the main collection. The establishment of the IPCC in that year provides an institutional anchor, while the reporting of James Hansen's congressional testimony provides a prominent communication anchor [@ipcc_history; @conway2008]. These events motivate the proposed sampling boundary without establishing that a uniform public emotional transition occurred at that moment. Recoverable material from 1938 onwards may provide an earlier contextual layer, anchored by Callendar's contribution to the relationship between artificial carbon-dioxide production and temperature [@callendar1938].

The collection's historical span and the observation window for each analysis will be distinguished. Cross-source time-series comparisons will use periods with sufficient overlapping coverage, rather than assume that present-day social platforms provide continuous records from 1988. The analysis will focus on emotions expressed in the collected material. Claims about wider populations will depend on the sampling evidence and any available external validation. Cultural heritage may inform later contextual discussion, but it is not an assumed status of the material or a premise required by the research design.

## 1.3 Broad aim and intended contributions

The broad aim is to investigate how social emotions concerning rising temperature are expressed and change across policy and public discourse, and how their temporal patterns relate to climatic conditions and scientific or policy events, using a reproducible computational analysis of natural-language evidence.

The first intended resource contribution is an openly accessible corpus and database release, developed through documented online collection and source verification. The release will include the text, metadata, identifiers and derived material that can be shared under the relevant source conditions. A modular research architecture will connect collection, representation, extraction, emotion analysis, topic analysis and temporal modelling. Algorithmic or methodological improvements may emerge where the empirical work demonstrates a need and provides evidence of their value. The principal scholarly outcome will be a thesis grounded in substantive findings, with the ambition of developing results suitable for publication.

# 2. Background and Literature Review

> Next writing stage. Planned coverage: social emotions and climate communication; agenda-setting and temporal relationships; event and relation extraction; aspect-specific sentiment and emotion recognition; dynamic topics and semantic change; and the specific contribution in relation to the closest studies. The previous retrieval-centred literature review will be selectively reused, not transferred as the organising argument.

# 3. Project Plan

## 3.1 Research objectives and questions

The first empirical objective is to investigate temporal relationships between warming-related attention and emotional expression, climatic conditions, and scientific or policy events. Event extraction, emotion analysis and temporal topic analysis will supply complementary evidence for this investigation.

**RQ1 — Temporal relationships.** How do warming-related attention and expressions of fear and anxiety vary with climatic conditions and scientific or policy events, and what leading or lagging relationships are observable between policy and public discourse over periods of comparable coverage?

**RQ2 — Events and emotional objects.** Which events, anticipated consequences and proposed responses are associated with warming-related fear and anxiety in the texts, and how do these associations differ across source types and geographical settings with sufficient evidence?

**RQ3 — Change over time.** How do the topics, narrative associations and language of warming-related emotions change over the observed period, and which patterns remain after accounting for changes in source composition and data availability?

The supporting objectives are to:

1. Collect and document an English-language corpus with broad geographical coverage, construct a database linking text to its source and temporal context, and prepare an open release within the sharing conditions of the contributing sources.
2. Implement and evaluate all three required analytical components: event and relation extraction, aspect-specific sentiment and emotion analysis, and temporal topic and semantic analysis.
3. Construct interpretable attention and emotional-expression measures and examine their relationships with independent climate and event records, using temporal models appropriate to the available observations.
4. Produce substantive findings for the thesis and a reproducible research architecture, assessing any proposed algorithmic improvement against an appropriate baseline before claiming a separate methodological contribution.

## 3.2 Initial methodological design

### Corpus construction and representation

Online collection will retain natural-language text together with provenance, source role, available geographical evidence and relevant dates. The database will distinguish publication dates, events mentioned in a text and collection dates. Transformer-based encoders will generate vector representations for semantic retrieval and downstream analysis; a vector index will remain linked to the original text records. Retrieval will identify candidate passages for analysis, with surrounding context retained to resolve emotional targets, attributed statements and event references.

The source assessment will record coverage across the United States, European settings, Australia and New Zealand. It will consider Facebook and Reddit discussions, comments responding to relevant YouTube videos, public Bluesky and Mastodon posts, and topic-based or regional forums. Sustainable Living and Earth Science Stack Exchange are candidates for a supplementary question-and-answer stratum. These candidates serve different potential roles: event-linked comments, conversational narratives, short public reactions and questions about climate consequences or responses. Their suitability and relevant emotional content will be assessed through pilot sampling.

Specific communities, policy repositories, access routes and time windows will be selected after examining availability and comparability. Public visibility, programmatic access and permission to redistribute text will be assessed separately. Sources requiring approved research access will remain conditional until that access is established. The open corpus release will contain material whose redistribution conditions permit inclusion; access-restricted analysis data will be handled under their respective conditions. A broad collection will not by itself establish representative national samples. Cross-region results will therefore identify the sources and populations they can support.

### Three required analytical components

**Event and relation extraction** will identify participants, actions or relations, objects, time and place, and connect these elements to warming-related consequences and responses. Named-entity recognition and dependency parsing may supply components of this process, alongside relation extraction. Extracted links will represent claims or associations made in the text; a narrative that links warming to migration will not by itself establish that causal relationship in the world.

**Aspect-specific sentiment and emotion analysis** will distinguish the object of an attitude from its polarity and emotional category. Aspect-based sentiment analysis provides a task formulation for identifying what an evaluation concerns [@pontiki2014]. Fine-grained emotion resources such as GoEmotions provide candidate categories and models [@demszky2020], but require assessment on the project's sources. Fear, anxiety, grief and opposition to a policy will not be combined into a single score by assumption. The analysis will check whether the emotion concerns warming itself, an expected consequence or a proposed response, and whose emotion is being expressed or reported.

**Temporal topic and semantic analysis** will examine changing topics and expressions using Transformer representations and a topic-modelling approach such as BERTopic [@grootendorst2022]. Topic prevalence and representative passages will be compared across time and source groups. Claims about changing word or concept meanings will require contextual evidence and controls for source composition; changes in topic frequency alone will not be treated as proof of semantic change. The precise semantic-change procedure remains to be specified in the next methods increment.

These components will share document identifiers and contextual records so that a temporal change in emotional expression can be examined alongside its associated events, topics and passages. A stratified validation sample will assess extraction quality, emotional targets and classification errors across sources and periods. The main corpus analysis will use documented computational rules to reduce discretionary selection of evidence.

### First empirical analysis: attention and temporal relationships

The initial measures will separate the proportion of comparable source material discussing warming from the proportion of warming-related material expressing a specified emotion. If collection provides only climate-related texts, the analysis will report emotional composition within that collection rather than infer warming's share of all platform discussion. Embedding similarity will measure semantic relatedness; it will not automatically serve as an anxiety intensity score.

Textual measures will be aligned with independently compiled scientific and policy event dates and suitable climate observations. Global temperature anomalies and local heat exposure address different questions and will be distinguished. Public search-interest data may supplement the comparison where coverage permits. The aggregation interval and common analysis period will follow the temporal resolution and completeness of the source records.

Cross-correlation will explore leading and lagging associations after addressing trends, seasonality and serial dependence. A parsimonious vector autoregression and Granger tests are planned where observation counts, stationarity and model diagnostics support their use. The tests will assess additional predictive information conditional on the included series, with their causal limits made explicit [@shojaie2021]. Event-based dynamic regression is a candidate for sparse scientific or policy interventions. Temporal associations will be interpreted in light of shared drivers, feedback, measurement error and changes in source coverage. Any analysis of public emotion preceding policy action will require a separately defined policy-response measure.

## 3.3 Further planning to be developed

> Subsequent increments will specify source selection and access, sampling and database fields, module-specific evaluation, the temporal model protocol, milestones, resource requirements, risks and ethics. These require source assessment and the actual course and thesis timetable. The current objectives and design are proposals, not completed experiments or final parameter choices.

# References

> The bibliography is maintained in references.bib and will be generated automatically during final typesetting. Only sources used in the developing main text are added to that file; wider reading and technical documentation are linked in METHOD_REVIEW.md. Tool references for the AI statement remain to be completed.
