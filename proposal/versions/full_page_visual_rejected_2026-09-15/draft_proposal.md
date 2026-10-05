---
title: "Fear of temperature: policy, news media and public emotions in a changing climate"
author: "Dai Pan"
supervisor: "Mashhuda Glencross"
date: "16 September 2026"
lang: en-AU
bibliography: references.bib
status: "Complete discussion draft; submission date provisional"
---

<!-- page: ai -->
# Use of AI Statement

**Have you used AI to explore your topic?** Yes. ChatGPT, Gemini and Codex supported discussion of the topic and candidate methods. I selected the focus on social emotions and corrected suggestions that treated cultural heritage as an established premise or made a retrieval service the project's main purpose.

**Have you used AI to define your research question?** Yes. AI supported formulation and critique of the questions in Section 3.1. I prioritised leading and lagging relationships between policy, news and public expression, and retained three required NLP components.

**Have you used AI to assist with your literature review?** Yes. AI-assisted searches located literature and checked selected claims and bibliographic details. Section 2 synthesises the sources consulted; the project reading register records whether full text, relevant sections or abstracts were available. This is a targeted review, not a systematic review.

**Have you used AI to assist with formatting the answers presented here?** Yes. AI supported English drafting, translation, grammar, document organisation, and the preparation and inspection of Figures 1-5 and the tables.

**Have you used AI for other aspects of your work?** Yes. AI supported the methodological review, sampling calculations, risk planning and document-export code. No new corpus collection, NLP experiment or empirical time-series result is reported in this proposal. Figure 3 uses a synthetic sentence and Figure 4 uses design illustrations.

I acknowledge the use of generative AI tools in completing this assessment. Details of which tools were used and how they were used are provided below, with references to the services [@openai_chatgpt; @google_gemini; @openai_codex]. I take responsibility for critically evaluating and integrating the AI-generated content and ensuring that it adheres to academic integrity standards.

<!-- table: ai | 0.23,0.77 -->
**Table A. AI tools and project-specific use.**

| Tool and recorded dates | Uses and limits of the record |
|---|---|
| ChatGPT; discussions recorded 11 and 15 September 2026 | Topic exploration, research questions, literature assistance, methodological support, writing, translation, language editing and feedback. Exact model versions were not recorded. |
| Gemini; date/version not recorded | Suggested candidate NLP modules and event/agenda analysis, subsequently assessed and revised by the author. Its suggestions are not empirical findings. |
| Codex; 15 September 2026 | Literature and feasibility checks, discussion records, writing, diagram and table preparation, export programming and layout inspection. No research-data analysis was performed for this draft. |

Service references identify the tools, not undocumented model versions. The declaration will be updated if further AI use occurs before submission.

<!-- page: abstract -->
# Abstract

Fear of Temperature investigates how fear and related emotions about rising temperature are expressed and change across government and policy discourse, news reporting and public discussion. Its central question is who changes first, and whether physical events, institutional communication and public expression exhibit leading, lagging or reciprocal relationships. The substantive emphasis is on anticipated warming and threats to personal, family and collective futures, while direct high-temperature danger remains a related analytical dimension.

The project will construct a traceable English-language corpus with intended coverage across the United States, Europe, Australia and New Zealand. Collection will target 1988-2026, with earlier material used where recoverable for context. Each statistical comparison will use the period for which suitable sources actually overlap. A structured database and Transformer-based representations will support three complementary components: event and relation extraction; aspect-specific sentiment and emotion analysis; and temporal topic and semantic analysis. These components will produce measures of attention, expressed emotion, risk framing, responsibility attribution and stance. Source-specific denominators and stratified validation will distinguish changes in discourse from changes in sampling or model behaviour.

A first pilot will align independently measured heat exposure with public expressions of immediate danger and future-oriented concern. Subsequent analyses will compare policy, media and public series through cross-correlation, conditional predictive models and event-centred analyses of level and slope changes. Temporal precedence and narrative attribution will be distinguished from causal identification. The intended contributions are a documented database with a permissible open release, a reproducible computational workflow, and a thesis with substantive findings suitable for development towards publication. Database construction will proceed incrementally so that analysis and validation begin before full corpus expansion.

**Keywords:** climate emotions; anticipated warming; natural language processing; agenda-setting; responsibility attribution; temporal analysis.

<!-- page: contents -->
# Contents

<!-- contents -->

## Figures and tables

**Figures:** 1. Research relationships; 2. NLP research pipeline; 3. From language to evidence; 4. Measurement and temporal analysis; 5. Work plan and decision points.

**Tables:** A. AI use; 1. Literature synthesis; 2. Source and sampling plan; 3. Measurement definitions; 4. Evaluation protocol; 5. Project risk register; 6. Milestones and resources; 7. OHS and ethics controls.

**Reading note.** This is a complete proposal draft, not a report of completed experiments. Numerical examples and diagram trajectories explain the design. Access-dependent choices will be resolved through the documented pilot. The provisional submission date is 16 September 2026; the course deadline is 17 September 2026 at 15:00. A conflict in the published final-report date is identified in Section 3.8.

<!-- page: introduction -->
# 1. Introduction
## 1.1 Motivation and significance

Rising temperature is both a physical process and an object of social anticipation. People may describe immediate danger during a heatwave, worry about the world their children will inherit, or assign responsibility for future disruption. These expressions involve different emotions, time horizons and social relationships. Climate-anxiety research recognises psychological responses to anticipated environmental change as well as direct exposure [@clayton2020]. Studying how such responses are communicated can illuminate the changing social meaning of warming without assuming that every negative statement expresses fear.

Fear of Temperature asks how warming-related fear and anxiety develop across government and policy discourse, news media and public expression. A central problem is temporal ordering: does public concern follow physical events, institutional communication or media attention, and when might it precede them? Earlier work links climate concern to political cues, media and other conditions [@brulle2012]. Research on affective agenda dynamics also demonstrates the relevance of comparing government, media and public expressions [@zhou2023]. Figure 1 frames these as competing relationships to investigate rather than a predetermined chain of influence.

![Figure 1. Three discourse roles and the question of temporal ordering. Dashed links show candidate relationships, not established causal effects. Independent physical observations and dated events inform the comparison.](assets/figure_01_relationships.svg)

## 1.2 A methodological transition

Earlier project exploration used dictionaries and n-grams to locate temperature-related language. This proposal extends the method through natural-language collection, database construction, Transformer representations and contextual analysis. The purpose is to support the author's substantive investigation of social emotions at scale. Consistent procedures should reduce discretionary passage selection, while validation will test whether the procedures measure the intended concepts. NLP is the principal research method; the thesis remains the principal scholarly outcome.

<!-- page: scope -->
## 1.3 Scope and historical framing

The core collection will prioritise English-language texts associated with the United States, European settings, Australia and New Zealand. Broad geographical coverage is an objective, while the main comparison concerns source roles and identifiable communities. Chinese-language material, East Asian settings and AOSIS members are extension candidates rather than dependencies of the core study. Publication location, author location and the place discussed in a text will be distinguished. English language alone will not establish geographic or cultural identity.

The target collection begins in January 1988 and extends to a documented cutoff in 2026. The establishment of the IPCC in 1988 motivates an institutional anchor [@ipcc_history]. It does not establish an emotional turning point. Recoverable material from 1938 onwards may form an earlier contextual layer, with Callendar's work providing a scientific-historical reference [@callendar1938]. A claim about change across 1988 requires adequate observations on both sides; the main collection alone cannot demonstrate that transition.

Historical span and analytical coverage are therefore different. Each comparison will use a sufficiently dense common window, with incomplete months, archive gaps and changes of source explicitly recorded. Letters to editors and early forums may extend the record of public expression, but their selection processes differ from contemporary platforms. The intended inference concerns the sampled discourse. Claims about population emotion require additional sampling or validation evidence.

Longer-term anticipated consequences are the substantive priority. Direct heat danger will be collected alongside them and labelled after collection. Emotional category, immediate bodily-threat cues, time horizon and threatened group will be separate, potentially overlapping attributes. Fear can concern the future, and collective anxiety can arise during a present emergency. Cultural heritage may inform discussion, but the project does not presuppose heritage status.

## 1.4 Broad aim and intended contribution

The broad aim is to understand how warming-related social emotions, anticipated futures and responsibility narratives change across policy, news and public discourse, and how their temporal relationships vary with physical and institutional events.

The intended resource contribution is a versioned corpus and database, with an open component limited to material that may be redistributed. The technical contribution is a reproducible architecture connecting collection, representation, extraction, emotion measurement and temporal analysis. A distinct algorithmic contribution will be claimed only if an evaluated modification improves on an appropriate baseline. The scholarly contribution will be evidence about temporal relationships and changing narratives, including small, absent or uncertain associations where the design supports that conclusion.

The project is successful when it produces reliable, interpretable evidence and documents the limits of its methods. Neither a significant policy effect nor proof of a single dominant driver is a required outcome.

<!-- page: background -->
# 2. Background and Literature Review
## 2.1 Climate emotions and anticipated futures

Climate anxiety is a useful starting point because concern can arise from anticipated harm, not only a disaster already experienced. Clayton distinguishes the need to understand anxiety from an assumption that all concern is maladaptive [@clayton2020]. Albrecht and colleagues' solastalgia describes distress associated with environmental change while people remain connected to their home environment [@albrecht2007]. These concepts concern related but non-identical experiences. They do not justify treating any mention of loss, heat or future generations as evidence of the same emotional state.

Pihkala's taxonomy identifies a wider range of climate emotions, including fear, worry, grief, anger, guilt and hope [@pihkala2022]. This supports a multidimensional annotation scheme rather than a single panic-to-anxiety scale. The present study will examine expressed or reported emotion, its target and temporal horizon. It will not diagnose clinical anxiety from posts or infer that isolated expressions establish chronic distress.

O'Neill and Nicholson-Cole examine fear-inducing climate imagery and public engagement [@oneill2009]. Their work makes a useful distinction for this project: attention, emotional response and engagement are not interchangeable. A text may recognise warming as threatening while rejecting a proposed response; a fearful representation may attract attention without demonstrating policy support. Stance and emotion therefore require separate measures.

## 2.2 Agenda-setting and responsibility frames

Agenda-setting concerns relationships between the prominence of issues in media and public agendas [@mccombs1972]. For this project, attention means the relative presence of warming-related discourse within a defined source collection. It does not measure audience exposure unless suitable exposure data are available. Entman's account of framing distinguishes the selection of a problem, causal interpretation, evaluation and proposed response [@entman1993]. This motivates separate records for causes, blame and duties, rather than treating all agency as responsibility.

The two perspectives connect different questions. Agenda analysis asks when an issue becomes prominent; frame analysis asks how that issue is described. A rise in warming-related reporting may emphasise economic cost, physical danger or intergenerational justice. Similarity to policy language may indicate adoption, quotation or opposition. Measuring prominence without these distinctions would leave the social-emotion question under-specified.

## 2.3 Climate concern and reciprocal communication

Brulle and colleagues analyse quarterly U.S. climate concern during 2002-2010 using an aggregate of survey measures, comparing weather, scientific information, media and political cues [@brulle2012]. Their reported importance of elite and media factors motivates competing institutional and physical explanations. It is not evidence that weather is irrelevant in every location or that future-oriented fear behaves like aggregate concern. The present design uses more differentiated text measures and preserves exposure scale and source context.

<!-- page: literature_methods -->
## 2.4 From textual representation to social measurement

Sentence-BERT shows how sentence representations can support efficient semantic comparison [@reimers2019]. This is relevant when warming-related fear is expressed without an exact dictionary phrase. However, semantic similarity is not itself emotional intensity or agreement. A shared encoder will provide a consistent comparison space, while separate decisions establish relevance, emotional target and stance. Lexical retrieval remains an interpretable baseline and a way to examine what the richer representation adds.

Aspect-based sentiment analysis provides a formulation for linking evaluations to their objects [@pontiki2014]. This is important when negative language concerns policy cost rather than warming. GoEmotions provides fine-grained labels from English Reddit comments [@demszky2020]. Its categories include fear, nervousness and grief, but not a dedicated climate-anxiety label. Its source domain also differs from older news and institutional prose. Model outputs therefore require validation by source and period before becoming time-series measures.

PropBank supplies a predicate-argument approach to semantic roles [@palmer2005]. Emotion-cause pair extraction treats emotional expressions and their reported causes as linked analytical objects [@xia2019]. Together these approaches motivate contextual extraction, but neither licenses equating a grammatical subject with a culpable actor. The statement "government blamed industry" assigns distinct speaking and responsibility roles. The proposed relation layer will preserve the predicate, relevant entities, quotation, negation and evidence spans.

BERTopic combines embeddings, clustering and class-based term representation [@grootendorst2022]. It offers a practical starting point for temporal topic analysis, but its introduction is a preprint and its suitability here requires empirical assessment. Changes in topic prevalence are not automatically changes in meaning. Stable encoding, matched source subsets, representative passages and sensitivity to clustering will be used before interpreting conceptual or metaphorical evolution.

## 2.5 Temporal evidence and its limits

Zhou and colleagues compare emotional communication by public, government and media accounts on Weibo during the COVID-19 pandemic [@zhou2023]. This provides a close role-based precedent, although a short pandemic period in one platform differs from the proposed climate study's historical and cross-source setting. The opportunity is to connect such role comparisons to validated targets, responsibility narratives and independent physical observations.

Granger causality concerns whether past observations improve conditional prediction; its causal interpretation depends on assumptions and the variables observed [@shojaie2022]. Interrupted time-series designs distinguish immediate changes from subsequent trend changes [@lopezbernal2017], while Hausman and Rapson explain why a temporal cutoff alone does not establish causal regression discontinuity [@hausman2018]. Hamaker and colleagues additionally show why cross-lagged panel interpretations must distinguish stable differences between units from changes within them [@hamaker2015]. These studies favour a small, justified model over the automatic accumulation of sophisticated techniques.

<!-- page: synthesis -->
## 2.6 Synthesis and selected research gap

Table 1 organises the closest contributions by the design decision they inform. The limitation column describes what this project still needs; it does not assert that an omitted feature was absent from every study in a field.

<!-- table: literature | 0.24,0.34,0.42 -->
**Table 1. Literature synthesis and implications for the proposed study.**

| Research strand | Contribution relevant here | Remaining need and design response |
|---|---|---|
| Climate emotions [@clayton2020; @pihkala2022] | Distinguishes multiple responses to environmental threat and anticipation. | Text scores are not clinical measures. Validate emotion, target and horizon separately. |
| Fear and engagement [@oneill2009] | Examines how fearful representations relate to public engagement. | Attention cannot stand in for fear or action. Keep these constructs separate. |
| Agenda and framing [@mccombs1972; @entman1993] | Connects prominence with the selection and interpretation of issues. | Define source-specific denominators and separate blame, cause and duty. |
| U.S. climate concern [@brulle2012] | Compares physical, informational and political factors in a longitudinal design. | Extend the question to differentiated expressions and regional exposure without inheriting its result. |
| Affective agenda dynamics [@zhou2023] | Directly compares public, government and media communication. | Test comparable roles across sources, periods and climate-event contexts. |
| Contextual NLP [@reimers2019; @demszky2020; @xia2019] | Supports semantic retrieval, fine-grained emotions and emotion-cause relations. | Evaluate domain transfer and trace aggregate measures back to passages. |
| Topic and temporal methods [@grootendorst2022; @shojaie2022; @hausman2018] | Supplies tractable topic and time-series approaches. | Demonstrate measurement stability and distinguish prediction from causal identification. |

The selected gap lies at the connection between these strands: a traceable, source-aware study of warming-related social emotions that relates validated textual measures to physical and institutional events, while examining what the expressions attribute to events, mechanisms and responsible actors. This is a bounded contribution in relation to the reviewed work, not a claim that no related research exists.

Three design requirements follow. First, comparable observations and denominators must be established before interpreting differences in attention. Second, emotion, target, horizon and responsibility must remain distinguishable throughout the pipeline. Third, changes in model outputs must be checked against source composition and measurement error before being interpreted as historical change. The three NLP components address these requirements jointly.

The literature review is targeted and will be extended as the source pilot identifies the closest empirical setting. New evidence may change the preferred implementation. Such changes will be recorded with their rationale while preserving the core social-emotion question.

<!-- page: questions_pipeline -->
# 3. Project Plan
## 3.1 Research questions

**RQ1 - Who changes first?** What leading, lagging, synchronous or reciprocal relationships connect government and policy discourse, news reporting and public expressions of warming-related fear and anxiety over periods of comparable coverage?

**RQ2 - What changes around events?** How do independently dated heat, scientific and policy events relate to changes in attention, public emotion and framing, including immediate level changes and subsequent changes in trend?

**RQ3 - How is fear explained?** How do texts connect warming-related emotions to events, future horizons, causes, blame and duties, and how are these connections adopted, contested or reinterpreted across source roles?

The study will construct a traceable database, implement and assess all three NLP components, compare temporal relationships, and produce a thesis and permissible reproducible outputs. Figure 2 shows how these activities form an iterative research process.

![Figure 2. NLP research pipeline. Three required components share a versioned representation and original context. Validation informs iteration; corpus expansion does not have to finish before analysis begins.](assets/figure_02_pipeline.svg)

## 3.2 Evidence-driven implementation

The first pilot will use a small, eligible common window to test ingestion, date and role assignment, representation, all three modules and aggregation end to end. The choice of event will depend on actual source overlap, geographic evidence and independent dates rather than an expected significant response. Institutional-first, physical-event-first and reciprocal pathways will be compared. More sources and years will be added only after the pilot exposes the necessary fields, errors and costs.

<!-- page: sources -->
## 3.3 Corpus construction and sampling

Table 2 lists candidates, not secured datasets. Source assessment will record accessible dates, document types, access conditions, available identifiers, estimated volume and gaps. The core retains broad English-language coverage across the United States, Europe, Australia and New Zealand; a local pilot tests feasibility without redefining the final geographical ambition.

<!-- table: sources | 0.20,0.43,0.37 -->
**Table 2. Candidate sources and their intended sampling roles.**

| Stratum | Candidate material | Sampling and access decision |
|---|---|---|
| Government / policy | EPA and White House material; parliamentary records and government releases in UK, European, Australian and New Zealand settings | Fix institution and document type; obtain a broader issue pool for salience. Separate policy speech from action. |
| International institutions | UNFCCC decisions; IPCC assessment reports | Record policy decisions and scientific assessments as distinct subtypes. Specialist climate reports are not a government-wide denominator. |
| News media | NYT, Guardian, WSJ, FT; suitable Australian and New Zealand news archives | Verify title/year coverage and text-mining access through available archives; do not presume complete publication totals. |
| Historical public expression | Letters to editors; Usenet, including sci.environment; preserved forums | Verify publication dates, archive completeness and editorial selection. Treat changing channels as separate source strata. |
| Contemporary public expression | General-interest and climate-focused Reddit communities; eligible Facebook, YouTube, Bluesky, Mastodon and public-forum material | Distinguish posts, comments, channels and community roles. Select sustainable, permitted access with auditable sampling. |

Two collection streams will serve different purposes. An issue-independent background sample, or a complete bounded source collection, will estimate attention. A broader climate-candidate stream will support detailed emotion and relation analysis. Candidate retrieval will be checked against the background sample for missed relevant texts. Enriched samples will not be pooled into prevalence estimates without appropriate inclusion weights.

Media salience will use relevant eligible articles divided by all eligible articles within the same database, title, edition, date, genre and deduplication rules. Policy salience will use relevant paragraphs or speaking turns, optionally weighted by their word counts, within a fixed institution and document type. Public salience will use relevant posts divided by eligible posts in the sampled community; comments will be a separate unit. Equal-sized random samples estimate each stratum's share. Aggregation across strata will use explicit fixed or population-size weights, with both the sampled population and weight interpretation stated.

Every record will preserve a stable ID, source URL/identifier, publication and collection dates, text unit, role, quoted speaker, location evidence, document parent, duplicate cluster, access status and processing version. Missing observations will remain distinct from true zero counts. Long reports will not gain uncontrolled weight simply because they contain more passages. Restricted original content and permissible release material will be separated from the outset.

<!-- page: measures -->
## 3.4 Operational definitions

The main substantive outcome is future-oriented warming-related fear or worry expressed in public texts. Attention will distinguish increased discussion from a change in emotion within that discussion. Direct bodily-threat expressions provide a related comparison. The remaining measures explain the content of change; their inclusion does not make every possible relationship a primary hypothesis.

<!-- table: measures | 0.20,0.41,0.39 -->
**Table 3. Measurement definitions and safeguards.**

| Construct | Proposed operational measure | Interpretation and safeguard |
|---|---|---|
| Attention | Weighted share of relevant units within a defined background collection; relevance from validated semantic retrieval/classification | Not platform-wide attention unless the sampling frame supports it. Keep numerator, denominator and coverage. |
| Fear / future worry | Separate validated labels or calibrated scores among warming-related units; emotion target and speaker recorded | Fear, nervousness and future orientation are not interchangeable. No clinical diagnosis from text. |
| Risk frame | Multi-label proximity/classification for instrumental, crisis and moral/justice frames, using several example prototypes | Retain mixed, other and uncertain cases. Prototype directions are not assumed orthogonal. |
| Responsibility | Evidence-linked cause, blame, response duty and affected-group relations | Grammatical agent does not equal culpable actor. Store quotation, negation and uncertainty. |
| Stance / polarisation | Separate positions on warming threat and a specified policy; score distributions and category shares | Policy opposition is not warming denial. Bimodality is exploratory, not sufficient proof of social polarisation. |

For one source-time stratum, let R(i) indicate relevance, F(i) a validated emotion label and w(i) the sampling weight. The primary proportions are:

<!-- equation: shares -->
S = sum[w(i) R(i)] / sum[w(i)]
E = sum[w(i) R(i) F(i)] / sum[w(i) R(i)]
B = sum[w(i) R(i) F(i)] / sum[w(i)] = S x E

Here S is climate-related attention, E is emotion within relevant discourse and B is their joint share. The identity requires the same units, weights and labels. Empty denominators yield missing values. Model scores require calibration or a clearly limited score-based interpretation.

The proposed fear/anxiety ratio will be secondary because small denominators can produce unstable values. Semantic similarity will use several natural-language prototypes and thresholds chosen on development data. Absolute projection onto a single direction will not be treated as a validated frame score: opposite directions can have the same absolute projection. Continuous measures will undergo the same validity checks as categorical outputs.

<!-- page: extraction -->
## 3.5 Representation and the three NLP components

A sentence encoder will provide common, versioned embeddings linked to text and context. A lexical/TF-IDF baseline and a sentence-embedding candidate will first be compared for relevance using precision, recall and representative missed cases [@reimers2019]. The encoder will remain fixed within a substantive comparison; separate unaligned spaces will not be fitted for each group. Exact models will be chosen by validation quality, licence, throughput and local compatibility. A pilot benchmark will estimate documents/hour, memory, storage and annotation cost. MPS acceleration is conditional on compatibility; no speed-up is assumed.

**Event and relation extraction.** Named entities and parsing will support event candidates, followed by an evaluated SRL or contextual relation model. The output will distinguish the speaker, described event, cause, blamed actor, response duty and affected group. Emotion-cause pairing informs this design [@xia2019]. Evidence spans, negation, modality and quotations will be retained. An explicit causal phrase is not required for corpus inclusion, and missing attribution will not be filled by speculation.

![Figure 3. From language to evidence. This synthetic sentence illustrates overlapping labels and two attribution axes. A temporal phrase does not prove that the policy caused the worry; the duty-holder remains unspecified.](assets/figure_03_evidence.svg)

**Aspect-specific sentiment and emotions.** Pretrained emotion models, including a suitable GoEmotions-derived candidate, will be compared with interpretable cues [@demszky2020]. Future-oriented worry needs project-specific validation rather than relabelling nervousness. Heatstroke and future-generation terms can guide candidate selection, but neither alone proves an emotion. Policy texts may report a risk or quote another person's fear; the model must distinguish these from an institution expressing emotion itself.

**Temporal topics and semantics.** BERTopic will be piloted with one shared embedding space and inspected topic representations [@grootendorst2022]. Topic prevalence, frame distributions and contextual exemplars will be compared across time and role. Clustering stability under resampling, outlier coverage and representative-passage coherence will be assessed. Claims of semantic or metaphor change require matched-source contextual evidence beyond a change in topic frequency. Annotation and model revisions will precede the main analytical freeze.

<!-- page: temporal -->
## 3.6 Temporal alignment and analysis

Monthly indexes will organise the historical collection. Daily or weekly observations may support a sufficiently dense heat-event pilot; sparse institutional material may require a separate quarterly comparison. All series within a standard joint model will use the same frequency, with ratios recomputed from aggregated numerators and denominators. Quarterly values will not be duplicated into artificial monthly observations.

Global or regional temperature anomalies describe climatic background; local heat exposure addresses immediate physical danger. GISTEMP provides monthly anomalies [@gistemp], while daily heat statistics may be obtained from suitable station data or ERA5 [@era5]. Product, baseline, spatial weights, version and time zone will be documented. Publication location will not substitute for exposure location. Records without adequate geographic evidence remain unmatched to local exposure.

![Figure 4. Measurement and temporal analysis. Shifted curves illustrate a possible ordering; event panels illustrate level, slope and null patterns. All trajectories are schematic, not observed data or estimated effects.](assets/figure_04_temporal.svg)

Cross-correlation will examine candidate lags after treatment of trends, seasonality and serial dependence. The sign convention will be C(k) = Corr[T(t), E(t+k)]: positive k means temperature precedes emotion. The lag range and primary outcomes will be recorded before confirmatory comparisons. Where observations and diagnostics permit, a small VAR or suitable dynamic regression will assess additional prediction from other roles conditional on included variables [@shojaie2022]. Lag order will consider information criteria, residuals, stability and time-held-out prediction; the largest CCF peak alone will not determine it.

Policy adoption, implementation and scientific publication will be dated separately. Kyoto adoption (11 December 1997) and Paris adoption (12 December 2015) are historical candidates, conditional on usable before-and-after material [@unfccc_kyoto; @unfccc_paris]. An initial six-month window on each side will examine level and slope changes using segmented regression [@lopezbernal2017]. Longer baselines, anticipation, concurrent events, comparison series and placebo dates will be considered. A causal interpretation requires a defensible counterfactual; otherwise the result is an event-associated change [@hausman2018].

<!-- page: evaluation -->
## 3.7 Evaluation and validity

Evaluation will test the measurement system before interpreting temporal results. A first development batch of approximately 150 passages, balanced across the three source roles, is a planning allowance for finding label ambiguities and estimating annotation cost; it is not a powered final test. A separate stratified test set will be sized after observing class prevalence, annotation time and the desired precision. Rare labels may require enriched evaluation samples, with their sampling implications stated.

The author will prepare an annotation guide and seek an independent second reader for a subset. Agreement will be reported only where independent ratings exist. If a second reader is unavailable, a separated repeat assessment and documented disagreements will be reported as limited single-author validation, without claiming inter-rater reliability. Development and test sets will be separated by document/duplicate cluster; source and period holdouts will probe transfer.

<!-- table: evaluation | 0.21,0.42,0.37 -->
**Table 4. Evaluation protocol and evidence for success.**

| Component / question | Evidence and comparison | Decision rule |
|---|---|---|
| Corpus and relevance | Date/role audit, retrieval precision and recall, background-sample misses, duplicate clusters and source-time coverage | A traceable, adequately observed common window is required; document volume alone is insufficient. |
| Emotion and attribution | Per-label and macro F1, evidence-span and relation precision/recall, confusion by source/period, calibration where probabilities are used | Compare rules with pretrained/contextual models. Revise or narrow unreliable labels before analysis. |
| Topics and semantics | Topic coverage, resampling stability, coherence of representative passages, matched-source checks | Interpret only changes supported by contextual evidence and more than one reasonable configuration. |
| RQ1: temporal ordering | Own-history baseline versus added role/physical series; held-out prediction, lag estimates and uncertainty | Assess stability and predictive gain; do not require a significant direction. |
| RQ2: event change | Level/slope estimates, interval widths, window sensitivity, pre-trends and placebo dates | Report associations unless identification supports stronger claims. Twelve monthly points may be insufficient. |
| RQ3: narratives | Validated relation/frame changes, stance and quotation checks, traceable examples | Support interpretations with the distribution and its evidence, including uncertain or contradictory cases. |

F1 below 0.70 or two-rater kappa below 0.65 may trigger review during development; these are provisional warning levels, not universal adequacy standards. Passing them alone will not validate the aggregate measures. Classification error will also be tested for its impact on temporal estimates through resampling or plausible error perturbations. Time-block and source/author/duplicate dependence will inform uncertainty estimation.

The primary analysis plan will freeze outcomes, thresholds, weighting and lag ranges before final comparisons. Alternative windows and models will be identified as sensitivity or exploratory analyses. Non-significance will not be interpreted as proof of no physical influence or exclusive policy control [@wasserstein2016].

<!-- page: risks -->
## 3.8 Project risks and scope adjustment

Database construction is the largest delivery risk. Analysis will start on an end-to-end increment before expansion. Table 5 prioritises dependency and impact, not measured probabilities; priorities will be reviewed after the pilot. OHS and ethics controls appear in Section 3.10.

<!-- table: risks | 0.22,0.32,0.46 -->
**Table 5. Project risk register. H = high planning priority; M = moderate.**

| Risk / priority | Trigger or consequence | Response and remaining limitation |
|---|---|---|
| R1 Database delay / H | No analysable increment by a checkpoint, or remaining preparation exceeds allocated hours | Freeze the schema; analyse pilot batches; stop non-core connectors. Retain three roles and modules; record reduced coverage. |
| R2 Access / release / H | Required source has no workable access path at G1 | Select a permitted same-role alternative; separate restricted data and open outputs. Alternatives may change the population studied. |
| R3 Sparse history / H | Low independent counts, wide intervals or too few usable time points | Reassess windows or use common non-overlapping quarters. Earlier material may remain contextual; aggregation cannot restore missing observations. |
| R4 Measurement error / H | Critical labels or sources fail G2 validity checks | Refine the guide, calibrate or compare models; narrow unsupported distinctions. Continuous scores are not an automatically reliable fallback. |
| R5 False temporal pattern / H | Reposting, seasonality, anticipation or concurrent events dominate results | Track content clusters; use diagnostics, alternate windows and comparison series. Retain association-only conclusions where needed. |
| R6 Composition change / H | Source mix, archive availability or encoder versions change across periods | Fixed-source checks, explicit weights and common encoding. Geographic adjustment does not eliminate all selection differences. |
| R7 Compute / staffing / M | Measured inference or annotation cost exceeds capacity | Cache outputs, cap model comparisons and reduce pilot scale; CPU-compatible path if MPS fails. Independent validation remains resource-dependent. |
| R8 Loss / interruption / M | Backup failure, illness or feedback delay | Versioned snapshots, restore check, continuous writing and protected revision time. Replan at milestones rather than silently reducing validation. |
| R9 Date conflict / H | Published final-report date remains unresolved | Seek course clarification immediately; keep both the public date and conditional long plan visible. An earlier confirmed deadline requires substantive replanning. |

Counts below 100 are screening flags. Aggregation depends on effective sample size, uncertainty and usable time points; overlapping windows do not create independent observations.

The course profile lists Thesis Report as **26 October 2026, 15:00**, despite a 2027 Thesis Plan [@reit7842]. Figure 5 is conditional on clarification, not an assumed extension. If October is confirmed, the approximately 5.5 weeks after the proposal require immediate scope renegotiation.

<!-- page: timetable -->
## 3.9 Milestones, resources and time allocation

The author expects 10-30 hours per week; essential work will use the lower end. Figure 5 distributes the provisional 210-290 hours plus 15% contingency. Pilot throughput and holiday availability will inform revision. Assessment dates are conditional anchors [@reit7842].

![Figure 5. Conditional work programme and estimated workload. Phase bands, dependency lines, gates and course markers show different planning layers. Workload bars show provisional ranges; none represent completed work.](assets/figure_05_schedule.svg)

<!-- page: milestone_details -->
## 3.9 Milestones and resources (continued)

The decision gates link the timeline to reviewable outputs. Work may overlap, but expansion depends on a usable preceding increment. Table 6 specifies the deliverables and resources behind the visual schedule.

<!-- table: milestones | 0.18,0.47,0.35 -->
**Table 6. Milestones, estimated effort and resource dependencies.**

| Milestone | Deliverable and decision | Timing / effort estimate |
|---|---|---|
| M1 / G1 | Source/access register, minimal schema, scope and deadline clarification | By 24 Sep; 15-20 h; author, archive/library information and supervisor advice |
| M2 | End-to-end pilot database, denominator audit and three-module trial outputs | By 9 Oct; 30-40 h; permitted data, storage and local compute |
| M3 / G2 | Validated labels, frozen encoder/measurement plan and revised thesis outline | Oct-Mar; 50-70 h; annotation time and independent review if available |
| M4 / G3 | Frozen corpus; temporal/event estimates and robustness report | Mar-Apr; 50-70 h; validated measures and adequate coverage |
| M5 | Full thesis draft, evidence figures, poster/pitch rehearsal and feedback | Apr-May; 40-55 h; writing and supervisory review |
| M6 / G4 | Revision, permissible release, reproduction instructions and final presentation | May-Jun; 25-35 h; release review and clarified thesis deadline |

Reading and writing run throughout. The October seminar (12-16 October) will report actual progress; the Thesis Plan window is 1-19 March 2027, the rehearsal is 10-14 May, and the final pitch/poster/demonstration/Q&A is 7-11 June. No independent conference-paper assessment is assumed for this course version.

A failed gate triggers a smaller valid comparison or same-role source substitution, with the change in inferential scope recorded. External paid services require a justified cost estimate.

<!-- page: ethics -->
## 3.10 OHS, ethics and data governance

This is computer-based documentary research, with no planned physical experiment, fieldwork or active recruitment. Workstation and induction requirements will be confirmed before relevant work. Table 7 separates occupational health from data risks; controls will be reviewed when sources and settings are fixed.

<!-- table: ethics | 0.23,0.42,0.35 -->
**Table 7. OHS and ethics controls for the proposed activities.**

| Issue | Preventive control | Review / residual issue |
|---|---|---|
| Posture, eyestrain and repetitive work | Appropriate workstation setup, regular breaks and task rotation | Review workspace and sustained-session workload; discomfort requires adjustment. |
| Workload and distressing content | Bounded work sessions, manageable annotation batches, access to university support | Monitor fatigue and distress; avoid routine intensive exposure to harmful material. |
| Personal data and searchable quotations | Minimise identifiers; restrict raw access; use paraphrase or approved quotation where identification risk warrants | Public visibility is not blanket consent or redistribution permission. |
| Group labels and representation | Use observable source/community roles; retain uncertainty; avoid inferring sensitive personal identities | Sampled discourse does not represent entire countries or demographic groups. |
| External services and release | Local processing where feasible; review data transfer, licensing, retention and deletion requirements by source | Derived features and embeddings are not automatically unrestricted. |

UQ's human-research procedure requires an applicable review or exemption pathway for research involving people or their data [@uq_ethics]. The intention to publish and release resources means this study cannot simply assume the teaching-only exception. The relevant determination will be documented before collecting or analysing material that requires it. No approval or exemption is claimed here. Access-dependent work will not begin merely because the proposal has been submitted.

Current Reddit research access has a five-year historical window and a six-month delay, with additional content and sharing restrictions [@reddit_research]. This cannot establish continuous 1988-2026 coverage. Source-specific conditions will govern storage, access, retention and any external inference. Restricted full text, identifiers and public derivatives will be handled separately; permitted outputs will be selected through a release review rather than by assuming that transformation removes restrictions.

## 3.11 Outputs, interpretation and research record

The database will document source-time keys, permitted IDs/URLs, sampling weights, missingness, climate metadata, NLP versions, features and uncertainty. Permissible CSV/Parquet exports and code will include a data dictionary and versioned configuration; restricted material will have access descriptions.

The thesis will connect temporal findings to validated passages, including contradictory evidence and limits of population inference. A decision log, source register and progress notes will support supervisory discussion. Reproducible evidence will underpin subsequent publication or algorithmic claims.

<!-- page: references -->
# References

<!-- bibliography -->
