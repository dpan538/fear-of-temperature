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

**Topic exploration:** Yes; AI supported discussion of the topic and candidate approaches.

**Research questions:** Yes; AI assisted formulation and critique of Section 3.1; I selected the research focus.

**Literature review:** Yes; AI assisted searches and selected claim/reference checks for Section 2. Reading depth is recorded separately.

**Formatting and language:** Yes; AI assisted English drafting, translation, editing and document layout.

**Other uses:** Methodological discussion, planning, Figures 1-8 and export code. No empirical research-data analysis is reported here.

I acknowledge the use of generative AI tools in completing this assessment. Details of which tools were used and how they were used are provided in the table below, along with appropriate in-text and full references. I take responsibility for critically evaluating and integrating the AI-generated content, and ensuring it adheres to academic integrity standards.

<!-- table: ai | 0.28,0.72 -->
**Table A. AI tools and their use in this proposal.**

| Tool and recorded use | Main activities |
|---|---|
| ChatGPT; 11 and 15 September 2026 | Topic and question development, literature assistance, methodological discussion, writing and language editing. |
| Gemini; date/version unrecorded | Suggested NLP modules and event/lag analysis; suggestions were assessed and revised by the author. |
| Codex; 15 September 2026 | Source and feasibility checks, discussion records, drafting, figures, export code and layout inspection. |

Tools: ChatGPT [@openai_chatgpt], Gemini [@google_gemini], Codex [@openai_codex]. Model versions are retained in the working record where available. This declaration concerns proposal preparation; it reports no empirical research-data analysis.

<!-- page: contents -->
# Contents

<!-- contents -->

## Figures and tables

**Figures:** 1. Research relationships; 2. Competing mechanisms; 3. RQ evidence routes; 4. Source denominators; 5. NLP pipeline; 6. Measurement and timing; 7. Contextual evidence; 8. Calendar and workload.

**Tables:** A. AI use; 1. Literature synthesis; 2. Source register; 3a-b. Measures and annotation; 4. Event plan; 5. Evaluation; 6. Risk assessment; 7. OHS and ethics.

**Reading note.** This is a complete proposal draft, not a report of completed experiments. Numerical examples and diagram trajectories explain the design. Access-dependent choices will be resolved through the documented pilot. The provisional submission date is 16 September 2026; the course deadline is 17 September 2026 at 15:00.

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

**Resource contribution.** A versioned corpus and database with documented provenance, coverage and denominators; the open component will contain only redistributable material. Its value will be assessed through traceability, coverage audits and reproducible aggregation.

**Method contribution.** A validated workflow connecting representations, emotion, relations and temporal interpretation. A distinct algorithmic contribution remains conditional on an evaluated improvement over a suitable baseline.

**Scholarly contribution.** A thesis explaining temporal relationships and responsibility narratives through statistical estimates and contextual evidence, suitable for development towards publication. Small, absent or uncertain associations remain legitimate findings; success does not require a dominant driver or a significant policy effect.

<!-- page: background -->
# 2. Background and Literature Review
## 2.1 Climate emotions and anticipated futures

Climate anxiety concerns responses to possible as well as experienced environmental harm. Clayton cautions against assuming that concern is necessarily maladaptive [@clayton2020]. Solastalgia instead describes distress associated with environmental change in a place to which people remain attached [@albrecht2007]. These accounts connect emotion to anticipated futures and lived environments, but neither makes all negative climate language equivalent to anxiety. 

Pihkala's taxonomy distinguishes fear, worry, grief, anger, guilt and hope [@pihkala2022]. For this project, that diversity argues against a single scale running from bodily panic to existential anxiety. Emotional category, target, time horizon and affected group need separate labels. Textual worry does not establish a persistent psychological condition; keyword cues require contextual validation.

O'Neill and Nicholson-Cole examine fear-inducing climate imagery and engagement [@oneill2009]. Their distinction between attracting attention and supporting engagement matters here: a rise in threatening representations need not indicate stronger policy support. The proposed measurements therefore separate issue attention, emotional expression and stance. This gives a more specific account of discourse than a negative-sentiment score, while retaining the limitation that expressions are not direct observations of population mental health.

## 2.2 Agenda-setting and responsibility frames

Agenda-setting addresses relationships between the prominence of issues in media and public agendas [@mccombs1972].  A corpus share, however, measures the prominence of an issue in sampled output; without audience information it does not measure exposure or establish whose agenda changed.

Framing concerns how communication selects a problem, causal interpretation, evaluation and response [@entman1993]. Increased climate coverage can frame warming as economic disruption, physical danger or intergenerational injustice. These are different interpretations even if their overall issue attention is similar. Cause, blame and response duty also differ: an actor may be asked to respond without being blamed for creating the problem. Relations and contextual evidence are therefore needed alongside frequency and emotion measures.

Together these perspectives connect timing with interpretation. Similarity to policy language can reflect adoption, quotation or opposition; converging language alone does not establish agreement.

<!-- table: literature | 0.25,0.35,0.40 -->
**Table 1. Literature-to-design synthesis.** Each strand motivates a distinct design requirement.

| Evidence strand | What it contributes | Requirement for this study |
|---|---|---|
| Climate emotions | Multiple responses to threat | Separate emotion, target and horizon |
| Agenda and framing | Prominence versus interpretation | Measure attention and narrative content |
| Climate concern | Elite/media and physical explanations | Compare roles and exposure scales |
| Contextual NLP | Retrieval and structured text labels | Validate by source and period |
| Temporal methods | Ordering and event-related changes | State estimands and causal limits |

<!-- page: mechanisms -->
## 2.3 Evidence from climate concern and role comparisons

Brulle and colleagues construct quarterly U.S. climate-concern measures from 74 surveys during 2002-2010, comparing weather, science information, media and political factors [@brulle2012]. Their findings motivate institutional explanations, but aggregate concern is not specifically future-oriented fear. National quarterly observations may also conceal responses to local, short-lived heat exposure. The proposed text measures add narrative detail and shorter eligible windows; they introduce selection and classification errors that survey-based concern does not share in the same form. They should complement this evidence rather than be assumed more accurate.

Zhou and colleagues compare public, government and media emotional communication on Weibo during COVID-19 [@zhou2023]. This is a close precedent for role-based temporal comparison, but one platform and a pandemic period differ from a historical climate corpus spanning institutions and media systems. The present design retains the role comparison while testing source continuity, emotional targets and independent physical observations. Neither precedent establishes that a fixed direction of influence applies across all periods.

## 2.4 Competing temporal mechanisms and expectations

Institutional signals can supply authoritative risk interpretations [@brulle2012]; media can select and frame issues [@mccombs1972; @entman1993]; public expression may supply news material and pressure for response. Figure 2 makes the competing temporal expectations visible. H3 is a project hypothesis informed by role-comparison research [@zhou2023], not an established climate result.

![Figure 2. Five competing temporal expectations. H1-H3 show example orderings, not required intermediary paths. H4 links roles through a common event; H5 allows reciprocal prediction. Colours identify roles, while arrows show candidate temporal relationships.](assets/figure_06_mechanisms.svg)

The same ordering can arise from anticipation, shared releases, reposting or changing participants. A coarse monthly bin can hide a faster ordering. Local heat exposure also differs from global climate background. These expectations may coexist across windows; temporal prediction alone cannot identify social feedback or individual emotional contagion.

<!-- page: literature_methods -->
## 2.5 From textual representation to social measurement

Sentence-BERT supports efficient semantic comparison of sentences [@reimers2019]. This can locate relevant expressions beyond exact dictionary phrases, but similarity does not by itself measure emotion, intensity or agreement. A shared encoder will maintain a common representation; validated relevance decisions will determine which texts enter the climate subset. A lexical/TF-IDF baseline remains useful for assessing what contextual representations recover and which relevant expressions they miss.

Aspect-based sentiment analysis links evaluations to their objects [@pontiki2014]. This matters when a negative statement concerns the cost of a policy rather than warming. GoEmotions distinguishes fine-grained emotions in English Reddit comments [@demszky2020]; it includes fear and nervousness, but no dedicated climate-anxiety category. Neither general sentiment nor an unvalidated model label can supply the project's future-worry measure. Cross-period and cross-source validation will assess this transfer before monthly means are interpreted.

PropBank describes predicate-argument roles [@palmer2005], while emotion-cause pair extraction links emotional expressions with reported causes [@xia2019]. These inform complementary parts of the relation layer. A grammatical subject is not automatically culpable: in "government blamed industry", the speaker and blamed actor differ. The project must also distinguish described causes from attributed blame and response duties, retaining the predicate and evidence span rather than reducing every relation to an unqualified triple.

BERTopic combines embeddings, clustering and class-based term representation [@grootendorst2022]. It provides a practical topic-analysis candidate, although the cited account is a preprint and suitability for this corpus remains to be tested. A change in topic prevalence can arise from source composition or vocabulary rather than changing meaning. A shared encoder, fixed-source checks, stable clusters and contextual passages are needed before describing semantic or metaphorical evolution.

Together the three modules address different omissions. Emotion detection identifies the expressed response and target; relation extraction recovers the text's explanation of that response; topic analysis examines recurring narrative groupings and their change. Their combination is justified by the substantive questions, not by an assumption that adding models automatically creates innovation. Agreement between modules is not independent confirmation if all inherit the same retrieval or representation error.

## 2.6 Selected research gap

The reviewed strands leave a measurement connection to establish: when discourse changes, what emotion is expressed, and how is it explained? This selected gap does not imply that no earlier study combined NLP and climate discourse. The proposed workflow joins traceable role/time records, validated future-oriented emotion and evidence-linked responsibility narratives. It distinguishes growing discussion from growing fear within that discussion, then uses contextual passages to examine adoption, contestation and reinterpretation.

The temporal methods answer bounded questions. Granger analysis concerns added prediction [@shojaie2022]; ITS separates level and slope changes [@lopezbernal2017], while a temporal cutoff alone does not identify a causal effect [@hausman2018]. Cross-lagged interpretations also require distinguishing stable unit differences from within-unit change [@hamaker2015]. These limitations support the existing small-model pathway, rather than additional methods. The scholarly contribution depends on interpretable evidence and validated measurement, not a predetermined direction of influence.

<!-- page: questions_pipeline -->
# 3. Project Plan
## 3.1 Research questions

**RQ1 - Who changes first?** What leading, lagging, synchronous or reciprocal relationships connect government and policy discourse, news reporting and public expressions of warming-related fear and anxiety over periods of comparable coverage?

**RQ2 - What changes around events?** How do independently dated heat, scientific and policy events relate to changes in attention, public emotion and framing, including immediate level changes and subsequent changes in trend?

**RQ3 - How is fear explained?** How do texts connect warming-related emotions to events, future horizons, causes, blame and duties, and how are these connections adopted, contested or reinterpreted across source roles?

The main outcome is future-oriented warming fear or worry in public texts. Figure 3 separates attention ordering, event-associated changes and narrative interpretation.

![Figure 3. Research questions mapped to evidence. RQ1/2 use common monthly bins or non-overlapping quarters; RQ3 retains passage-level evidence. Follow each question through measurement to interpretation.](assets/figure_07_rq_routes.svg)

S measures attention; E measures emotion within relevant discourse. B = S × E is derived, not independent evidence. Prediction does not establish causation, and similar frames do not establish adoption.

## 3.2 Evidence-driven implementation

The common-window pilot tests ingestion, role/date assignment, all three NLP modules and aggregation. Select by source overlap and independent dates. Expansion depends on measured processing and annotation costs.

Freeze outcomes, weights, label rules, lag ranges and event windows before final comparisons. Other measures support interpretation rather than becoming additional primary tests. Figure 5 shows the shared pipeline.

<!-- page: sources -->
## 3.3 Corpus construction and sampling

Table 2 separates archive history from obtainable coverage. Sources remain candidates until access and a sample extraction are verified.

<!-- table: sources | 0.29,0.18,0.32,0.21 -->
**Table 2. Source register and coverage status.** Statistical windows will use verified overlap, not nominal archive age.

| Candidate source | Role / type | Time coverage to establish | Access state |
|---|---|---|---|
| EPA, White House; UK/EU/AU/NZ records | Policy / institutional | Target 1988-2026; archive-specific gaps | ◐ Candidate |
| UNFCCC; IPCC reports | Policy decisions; science | Publication-specific; discontinuous | ◐ Candidate |
| NYT, Guardian, WSJ, FT; AU/NZ news | Media / articles | Title, edition and year entitlement | ◐ Candidate |
| Letters, Usenet, preserved forums | Public / historical | Surviving dated records; no continuity assumed | ◐ Candidate |
| Reddit research route | Public / platform | Rolling 5 years; 6-month delay [@reddit_research] | ◐ Candidate |
| Facebook, YouTube, Bluesky, Mastodon; forums | Public / platform | API/archive-specific; overlap unverified | ◐ Candidate |

Status: ● access/sample verified; ◐ candidate; ○ unresolved. Record advertised, accessible and acquired dates, gaps and release conditions.

![Figure 4. Source-specific attention denominators. Each fraction pairs relevant units with the entire eligible collection of the same type. Posts and comments remain separate; weights and aggregation rules are fixed within each comparison.](assets/figure_08_sampling.svg)

An issue-independent sample estimates attention. Enriched climate retrieval supports emotion/relations; prevalence requires known inclusion weights. Fixed stratum weights describe a stable source mix; size weights target the documented eligible population. Their effects will be checked.

Historical public channels remain separate unless overlap supports comparison. IPCC assessments retain a scientific subtype; climate-specialist collections cannot supply government-wide denominators. Missing bins differ from zero counts. Record IDs, publication/collection dates, parent documents, roles, quoted speakers, location evidence and duplicates to preserve provenance and control repeated-text weight.

<!-- page: measures -->
## 3.4 Operational definitions and construct validity

The primary outcome is future-oriented warming fear or worry expressed in public texts. Fear, anxiety and worry will be treated as distinguishable, potentially overlapping expressions rather than diagnoses. Fear may concern an anticipated threat; worry often describes thinking about possible consequences. Neither category fixes a time horizon. Immediate heat danger and long-term concern will be collected together and labelled separately.

<!-- table: measures | 0.21,0.41,0.38 -->
**Table 3a. Constructs and measurements.** Similarity, attention, emotion and stance answer different questions.

| Construct | Operational measure | Interpretation boundary |
|---|---|---|
| Attention S | Weighted relevant share of eligible units | Sampled output, not audience exposure |
| Emotion E | Validated label/share within relevant units | Expression, not clinical severity |
| Joint share B | Relevant emotional units / eligible units | Derived from S and E |
| Risk framing | Validated multi-label prototype/classifier scores | Mixed/other frames retained |
| Responsibility | Evidence-linked cause, blame and duty | Grammatical subject is not culpability |
| Stance | Position on a stated threat or policy | Policy opposition is not denial |

For source stratum r and time bin t, U denotes the eligible unit set and i indexes its members. The weight w accounts for sampling; R indicates warming relevance and F with superscript future indicates expressed fear/worry targeting anticipated warming impacts. Equations (1)-(3) use identical units, weights and inclusion rules.

<!-- equation: attention -->
$$S_{rt}=\frac{\sum_{i\in\mathcal{U}_{rt}}w_i R_i}{\sum_{i\in\mathcal{U}_{rt}}w_i}\tag{1}$$

<!-- equation: emotion -->
$$E_{rt}=\frac{\sum_{i\in\mathcal{U}_{rt}}w_i R_i F_i^{\mathrm{future}}}{\sum_{i\in\mathcal{U}_{rt}}w_i R_i}\tag{2}$$

<!-- equation: joint -->
$$B_{rt}=\frac{\sum_{i\in\mathcal{U}_{rt}}w_i R_i F_i^{\mathrm{future}}}{\sum_{i\in\mathcal{U}_{rt}}w_i}=S_{rt}E_{rt}\tag{3}$$

S separates discussion volume from E, the emotional composition of relevant discussion. B describes their joint prevalence and will not enter a model as independent evidence alongside both S and E. An empty denominator produces a missing value. Scores require calibration or an explicitly score-based interpretation; a classifier probability is not a validated measure of psychological intensity.

Weights and aggregation rules remain fixed within a comparison. Media article shares and policy paragraph shares can support within-series changes and temporal comparisons, but their levels are not identical quantities. Differences between such shares will not be interpreted as a direct ranking of which role is more fearful.

<!-- page: labels -->
## 3.4 Operational definitions (continued)

Each annotated passage will retain its emotional target, temporal horizon, publisher/source role, quoted speaker, emotion-holder, and assertion/quotation scope. A newspaper can report a scientist describing residents' fear: these are three distinct positions. An institution's risk statement will not automatically count as an institutional emotion. Multiple or unknown holders remain explicit. Quoted public emotion stays attached to its institutional or media source; it is not silently transferred into the public-source series.

Negation and modality will be attached to the expression or relation they modify. A reassurance such as "should not panic" does not establish that panic occurred. A conditional future statement can express present worry about a possible event, so hypothetical wording is not a reason to discard the whole passage. Counterfactual and explicitly denied emotions require separate handling. Uncertain cases remain available for review and will not be forced into the positive class.

<!-- table: labels | 0.39,0.29,0.32 -->
**Table 3b. Synthetic boundary examples.** Labels depend on the target and holder, not isolated keywords.

| Synthetic passage | Emotion / target / horizon | Speaker, holder and scope |
|---|---|---|
| I worry about my children's future. | Worry; target unspecified; future | Self-expression; climate context needed |
| I fear warming will harm my children. | Fear; warming impacts; future | Self-expression; anticipated harm |
| The government said people should not panic. | Reassurance; no observed fear established | Government reported; negated advice |
| Scientists warn heatwaves are deadly. | Risk statement; heat; unspecified time | Reported warning; no fear required |
| If warming worsens, I fear our town will become unsafe. | Fear; warming impacts; future | Present fear; conditional consequence |
| I am not afraid of warming; I oppose this tax. | Fear denied; policy opposition | Negation of fear; distinct stance |

Time horizon and threatened group will be coded independently: immediate/near-term versus longer/intergenerational futures, and self/family/community where expressed. Ambiguous phrases will retain an unspecified category. The guide will record evidence spans and counterexamples for each label; development and held-out checks will be separated. This is a text annotation convention to be validated, not a new clinical taxonomy.

Semantic relevance will use several natural-language prototypes and development-set thresholds. Frame directions are not assumed orthogonal; the absolute projection onto one vector can assign the same magnitude to opposite directions and is not sufficient validation. Continuous alternatives face the same construct checks as classification. The fear/anxiety ratio and stance-distribution bimodality remain secondary: unstable denominators and classification mixtures can distort either, and bimodality alone does not demonstrate population polarisation.

These distinctions connect RQ3 back to the temporal results. A public-emotion rise will be examined alongside evidence about what was feared, who was described as affected, and whether the text assigned a cause, blame or duty. An unexpressed attribution will remain missing, rather than being inferred from a nearby event date.


<!-- page: extraction -->
## 3.5 Representation and three NLP components

A shared sentence encoder will produce versioned embeddings linked to the original passage and context. A lexical/TF-IDF baseline and a sentence-embedding candidate will be compared for relevance using precision, recall and missed cases [@reimers2019]. The encoder will stay fixed within comparisons. Selection depends on validation, licence, throughput and local compatibility; a pilot will measure documents/hour, memory and annotation cost. MPS acceleration remains conditional.

![Figure 5. NLP research pipeline. All three required components share a versioned representation and original context. Validation precedes corpus expansion and substantive interpretation.](assets/figure_02_pipeline.svg)

**Event and relation extraction.** Named entities and parsing support event candidates, followed by an evaluated semantic role labelling (SRL) or contextual relation model. Outputs distinguish event, speaker, described cause, blamed actor, response duty and affected group [@palmer2005; @xia2019]. Evidence spans, negation, modality and quotation remain attached. Events used as external analytical dates are verified independently of narrative extraction.

**Aspect-specific sentiment and emotion.** A suitable GoEmotions-derived candidate will be compared with interpretable cues [@demszky2020]. The aspect is the object being evaluated; the emotion layer distinguishes fear and project-defined future worry. Nervousness will not simply be renamed climate anxiety. The same procedure will check risks reported by institutions and emotions expressed by identifiable holders.

**Temporal topics and semantics.** BERTopic will use a shared embedding space and inspected representations [@grootendorst2022]. Topic prevalence, frame distributions and representative passages will be compared by role and time, with resampling stability and outlier coverage checks. Matched-source context is required before interpreting a shift as changing meaning. The three components remain the agreed method set; validation determines their usable distinctions.


<!-- page: temporal -->
## 3.6 Temporal alignment and analysis

Comparisons require common coverage and frequency: monthly where supported, daily/weekly for dense heat pilots, or common quarters for sparse institutions. Recompute ratios from aggregated counts; never repeat quarterly values into artificial months. Regional GISTEMP anomalies describe climate background; station/ERA5 measures address local exposure [@gistemp; @era5]. Record location evidence, baselines and versions; publication location is not exposure.

**RQ1: ordering and conditional prediction.** Cross-correlation (CCF) explores candidate lags after addressing trends, seasonality and serial dependence. In Equation (4), X and Y are processed series; positive k means X precedes Y. Compare role attention, or policy/media attention with public emotion.

<!-- equation: ccf -->
$$C_{XY}(k)=\operatorname{Corr}\,\left(X_t,\,Y_{t+k}\right)\tag{4}$$

A small vector autoregression (VAR), where observations and diagnostics permit, will test whether other roles add predictive information beyond the outcome's own history [@shojaie2022]. Report direction, lag range, uncertainty and held-out predictive gain. The largest CCF peak alone will not choose the lag order. Separate role-specific S from public E; B is secondary. Freeze lag limits, outcomes and processing before final comparisons.

**RQ2: event-associated change.** Segmented regression/interrupted time series (ITS) estimates a level change and a post-event slope change [@lopezbernal2017]. Equation (5) uses outcome Y and time t centred on event onset. D switches from 0 to 1 at onset; β₂ is the level change and β₃ the slope change. Disturbance u requires serial-dependence diagnostics and appropriate uncertainty treatment.

<!-- equation: its -->
$$Y_t=\beta_0+\beta_1t+\beta_2D_t+\beta_3(tD_t)+u_t\tag{5}$$

![Figure 6. Measurement and temporal analysis. Curves illustrate possible ordering and level, slope or null responses. All trajectories are schematic, not observed results.](assets/figure_04_temporal.svg)

<!-- page: events -->
## 3.6 Event selection and narrative interpretation (continued)

Select events from independent records before inspecting outcome peaks. Eligibility requires a verified date/interval, common coverage and an auditable denominator. The pilot tests one eligible event. Policy announcement, adoption and implementation, and scientific release and reporting, retain separate dates.

<!-- table: events | 0.26,0.20,0.27,0.27 -->
**Table 4. Candidate event-analysis plan.** The same eligibility rules apply to favourable, null and conflicting patterns.

| Candidate / type | External date | Window / outcome | Comparison and limit |
|---|---|---|---|
| Kyoto adoption / policy | 11 Dec 1997 [@unfccc_kyoto] | Initially ±6 months; S/E level and slope | Historical overlap unverified |
| Paris adoption / policy | 12 Dec 2015 [@unfccc_paris] | Initially ±6 months; S/E level and slope | Anticipation; concurrent coverage |
| Heat episode / physical | ○ Independent onset, peak and end | Dense local window; danger and future worry | Matched exposure; seasonality |
| IPCC release / scientific | ○ Report-specific release date | Common coverage; S/E and frames | Shared shock; media spillover |

The six-month windows are initial specifications, not a guarantee of adequate time points. Longer baselines are needed where trend, seasonality or serial dependence cannot be assessed within them. Inferential windows and aggregation will be fixed before final tests, using coverage and seasonal-baseline adequacy rather than outcome peaks.

Comparison series require comparable pre-event measurement and defensibly different exposure. Another outlet/topic is not automatically a control. Register concurrent shocks and anticipation; inseparable events form a joint window. Placebo dates and alternative windows test sensitivity, not causal identification [@hausman2018].

**RQ3: narrative explanation.** Relation and topic outputs will locate evidence about causes, blame, duties and threatened futures. Similar passages will be checked for quotation and stance before being described as adoption, contestation or reinterpretation. Narrative attribution differs from estimated event effects. Include representative and contradictory passages.


![Figure 7. From language to evidence. The synthetic sentence illustrates overlapping labels and two attribution axes. Its temporal phrase does not prove that policy caused worry; a response duty remains unspecified.](assets/figure_03_evidence.svg)

<!-- page: evaluation -->
## 3.7 Evaluation and validity

Evaluation will test the measurement system before interpreting temporal results. A first development batch of approximately 150 passages, balanced across the three source roles, is a planning allowance for finding label ambiguities and estimating annotation cost; it is not a powered final test. A separate stratified test set will be sized after observing class prevalence, annotation time and the desired precision. Rare labels may require enriched evaluation samples, with their sampling implications stated.

The author will prepare an annotation guide and seek an independent second reader for a subset. Agreement will be reported only where independent ratings exist. If a second reader is unavailable, a separated repeat assessment and documented disagreements will be reported as limited single-author validation, without claiming inter-rater reliability. Development and test sets will be separated by document/duplicate cluster; source and period holdouts will probe transfer.

<!-- table: evaluation | 0.21,0.42,0.37 -->
**Table 5. Evaluation protocol and evidence for success.** Validate measurement before interpreting temporal patterns.

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

Database construction is the main delivery risk because delays reduce the time available for validated analysis. Table 6 records each risk, its likely consequence and a practical response. Ratings are provisional management priorities, not estimated probabilities. OHS and ethics controls appear in Section 3.10.

### 3.8.1 Risk assessment

<!-- table: risks | 0.22,0.23,0.12,0.43 -->
**Table 6. Project risk assessment.** Prioritise threats to usable evidence and the analysis deadline.

| Risk | Potential consequence | Rating | Mitigation strategy |
|---|---|---|---|
| R1. Database construction overruns | Validation and analysis time is compressed. | High | Test an end-to-end pilot early; freeze the core corpus in December. If delayed, stop optional sources and analyse validated batches. |
| R2. Access or release restrictions | Planned sources or outputs become unavailable. | High | Verify access before expansion; use a permitted same-role alternative. Reassess comparability and keep restricted originals separate. |
| R3. Sparse historical coverage | Unstable indices; too few common time points. | High | Use common non-overlapping quarters or a shorter supported window. Keep sparse material as context; aggregation cannot recover missing data. |
| R4. Unreliable NLP measurements | Emotion or attribution trends are misclassified. | High | Validate by source and period; refine or narrow labels. Continuous scores also require validation. |
| R5. Misleading temporal signals | Apparent leads reflect shared shocks or dependence. | High | Check seasonality, serial dependence, duplicates and overlapping events. Report uncertainty and prediction/association limits. |
| R6. Changing source composition | Sampling or encoder changes resemble social change. | High | Freeze encoder and weighting rules within comparisons; check fixed-source subsets and archive gaps. |
| R7. Compute or review constraints | Processing or annotation exceeds capacity. | Medium | Measure pilot costs, cache outputs and cap comparisons. Retain a CPU-compatible route; report limits if no second reader is available. |
| R8. Illness or data loss | Lost work and delayed completion. | Medium | Keep versioned backups and test restoration; protect revision time and discuss scope adjustment with the supervisor. |

### 3.8.2 Review points and scope adjustment

The author will review progress against the usable pilot (16 October), core corpus (18 December), measurement validation (15 January) and completed analyses (28 February 2027). Section 3.9 gives the work allocation; required resources are archive access, local compute/storage, annotation time and supervisory feedback.

A missed gate or sustained workload above 10-20 hours/week triggers review of optional sources and comparisons. Protect the three discourse roles, three NLP components and validation before expanding coverage. Record each scope change and its implications for the research questions. Counts below 100 flag review; effective sample size, uncertainty and usable time points determine aggregation.

<!-- page: timetable -->
## 3.9 Milestones, resources and time allocation

At 10-20 hours/week, the provisional budget is 450-590 hours plus 15% contingency. All analysis and robustness checks must finish by 28 February 2027. The 320-400 hours allocated before March require about 14-17 hours/week before contingency; sustained lower capacity will trigger early scope reduction.

![Figure 8. Calendar, planned effort and concrete outputs. Solid bars show lower effort estimates; outlined ends extend to upper estimates. Hatching marks optional expansion, diamonds mark gates and arrows connect usable increments. All hours are planning values.](assets/figure_05_schedule.svg)

Resource dependencies are permitted archives, storage/local compute, annotation time and supervisory feedback. The pilot is due by 16 October; core data and denominator checks freeze on 18 December. Measurement validation freezes on 15 January, followed by all temporal, event, topic and attribution analyses by 28 February. Release requires a permissions review and reproduction instructions.

Assessment anchors: seminar, 12-16 October; Thesis Plan, 1-19 March 2027; rehearsal, 10-14 May; final pitch/poster/demonstration/Q&A, 7-11 June [@reit7842]. March-June centres on writing and feedback using completed analyses.

Missed freezes trigger narrower comparisons while preserving three roles, three modules and the February target.

<!-- page: ethics -->
## 3.10 OHS, ethics and data governance

This is computer-based documentary research, with no planned physical experiment, fieldwork or active recruitment. Workstation and induction requirements will be confirmed before relevant work. Table 7 separates occupational health from data risks; controls will be reviewed when sources and settings are fixed.

<!-- table: ethics | 0.23,0.42,0.35 -->
**Table 7. OHS and ethics controls for the proposed activities.** Review both workstation and data risks.

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
