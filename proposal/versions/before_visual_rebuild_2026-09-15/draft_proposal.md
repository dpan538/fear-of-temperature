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

**Other uses:** Methodological discussion, planning, Figures 1-5 and export code. No empirical research-data analysis is reported here.

I acknowledge the use of generative AI tools in completing this assessment. Details of which tools were used and how they were used are provided in the table below, along with appropriate in-text and full references. I take responsibility for critically evaluating and integrating the AI-generated content, and ensuring it adheres to academic integrity standards.

<!-- table: ai | 0.46,0.18,0.18,0.18 -->
**Table A. AI-use declaration.** Template usage categories are transposed for legibility; a tick records use.

| AI tool usage | ChatGPT | Gemini | Codex |
|---|---|---|---|
| Recorded date (September 2026) | 11, 15 | Unrecorded | 15 |
| Model version | Unrecorded | Unrecorded | GPT-6 |
| Topic exploration | ✓ | ✓ | ✓ |
| Research question | ✓ | — | ✓ |
| Literature review | ✓ | — | ✓ |
| Methodological support | ✓ | ✓ | ✓ |
| Data analysis | — | — | — |
| Visual content creation | — | — | ✓ |
| Written content creation | ✓ | ✓ | ✓ |
| Language translation | ✓ | — | ✓ |
| Grammar/style/spelling | ✓ | — | ✓ |
| Feedback on content | ✓ | — | ✓ |
| Other use | — | — | Notes; export code |

Tools: ChatGPT [@openai_chatgpt], Gemini [@google_gemini], Codex [@openai_codex]. Dashes mean no use documented in the available record. Tool versions will be added where recoverable before submission.

<!-- page: contents -->
# Contents

<!-- contents -->

## Figures and tables

**Figures:** 1. Research relationships; 2. NLP research pipeline; 3. Measurement and temporal analysis; 4. From language to evidence; 5. Work plan and decision points.

**Tables:** A. AI use; 1. Literature synthesis; 2. RQ mapping; 3a-b. Sources and denominators; 4a-b. Measures and annotation; 5. Event plan; 6. Evaluation; 7. Risks; 8. Milestones; 9. OHS and ethics.

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

**H1: Institutional leadership.** Policy announcements and elite signals can supply authoritative interpretations that enter reporting and public discussion [@brulle2012]. The expectation is that institutional attention or frames precede corresponding media and public changes. Anticipatory policy responses to a common event remain an alternative explanation; a lead alone does not identify policy influence.

**H2: Media leadership.** Issue selection can increase prominence, while framing can make particular consequences salient [@mccombs1972; @entman1993]. Media attention or risk frames may precede public worry. The comparison must check whether repeated reporting, a shared press release or publication delays account for the ordering.

**H3: Public leadership.** Public accounts of danger or future concern may provide news material and signals for institutional response. This is a project hypothesis, informed by reciprocal role comparison [@zhou2023], rather than an established climate finding. Public expression would lead later reporting or institutional attention; changes in participation and coordinated activity could produce a similar pattern.

**H4: Common-event response.** Physical exposure or a scientific release may reach several roles within the same time bin. Synchronous changes would be compatible with a shared shock, but could also conceal an ordering faster than the available monthly or quarterly resolution. Local heat exposure and global climate background must remain distinct.

**H5: Reciprocal reinforcement.** Roles may respond to one another over successive intervals. Bidirectional predictive relationships would be consistent with feedback, subject to omitted shared events and duplicated content. These expectations may coexist across windows. Aggregate curves alone cannot establish individual emotional contagion, audience exposure or a causal feedback mechanism.

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

The main emotional outcome is future-oriented warming fear or worry in public texts. RQ1 separately compares issue attention across roles and its temporal relationship with public emotion. RQ2 estimates changes in specified outcomes around independently dated events. RQ3 interprets narrative relations using validated evidence spans.

<!-- table: rqmap | 0.13,0.25,0.20,0.20,0.22 -->
**Table 2. Research questions, measurements and inference.** Each question has a defined evidence path and interpretation boundary.

| RQ / focus | NLP contribution | Measure / unit | Analysis | Supported interpretation |
|---|---|---|---|---|
| RQ1: ordering | Relevance + emotion; frame context | S by role; public E; common bins | CCF; small conditional VAR | Lead/lag and added prediction |
| RQ2: events | Event linking + emotion; frames | S or E; level/slope change | Segmented regression / ITS | Event-associated change |
| RQ3: explanation | Relations + topics; emotion context | Cause/blame/duty; evidence spans | Validated distributions and passages | Narrative attribution and reinterpretation |

S is the relevant share of eligible discourse; E is the emotion share within relevant discourse. B = S × E is a secondary joint share, not an independent third outcome. Bins are monthly where supported, or common non-overlapping quarters. RQ3 combines aggregate patterns with passage-level interpretation. Prediction does not itself establish causation; frame similarity does not itself establish adoption.

## 3.2 Evidence-driven implementation

The first pilot will use a small, eligible common window to test ingestion, date and role assignment, representation, all three modules and aggregation end to end. Event selection will depend on source overlap, geographic evidence and independent dates, rather than an expected significant response. Source expansion follows a usable increment and a measured estimate of processing and annotation costs.

The measurement and analysis plan will then freeze the primary outcome, sampling weights, relevance and label rules, lag range and event windows before final comparisons. Other measures explain the content of change; not every possible relationship becomes a primary test. Figure 2 shows how validation supports this staged implementation.

<!-- page: sources -->
## 3.3 Corpus construction and sampling

Table 3a separates archive history from obtainable coverage. Sources remain candidates until access and a sample extraction are verified.

<!-- table: sources | 0.29,0.18,0.32,0.21 -->
**Table 3a. Source register and coverage status.** Statistical windows will use verified overlap, not nominal archive age.

| Candidate source | Role / type | Time coverage to establish | Access state |
|---|---|---|---|
| EPA, White House; UK/EU/AU/NZ records | Policy / institutional | Target 1988-2026; archive-specific gaps | ◐ Candidate |
| UNFCCC; IPCC reports | Policy decisions; science | Publication-specific; discontinuous | ◐ Candidate |
| NYT, Guardian, WSJ, FT; AU/NZ news | Media / articles | Title, edition and year entitlement | ◐ Candidate |
| Letters, Usenet, preserved forums | Public / historical | Surviving dated records; no continuity assumed | ◐ Candidate |
| Reddit research route | Public / platform | Rolling 5 years; 6-month delay [@reddit_research] | ◐ Candidate |
| Facebook, YouTube, Bluesky, Mastodon; forums | Public / platform | API/archive-specific; overlap unverified | ◐ Candidate |

Status key: ● access and sample verified; ◐ candidate route; ○ unresolved selection. The register separates advertised, accessible and acquired dates, gaps and release conditions.

<!-- table: denominators | 0.17,0.21,0.37,0.25 -->
**Table 3b. Sampling units and attention denominators.** Numerator and denominator must describe the same eligible collection.

| Layer | Counting unit | Attention denominator | Weight / use |
|---|---|---|---|
| Media | Article; deduplicated | All eligible archive articles in title/edition/bin | Stratum weights; RQ1/2 |
| Policy | Paragraph OR speaking turn | Same institution, genre and unit | Fixed units; RQ1/2 |
| Public | Post; comments separate | Eligible posts in sampled community/bin | Inclusion weights; RQ1/2 |
| Climate-only subset | Passage with parent ID | Relevant units; no general salience estimate | Emotion/relations; RQ1-3 |

An issue-independent sample or bounded complete collection estimates attention. Enriched climate retrieval supports detailed emotion and relation analysis; it cannot supply prevalence without known inclusion weights. Posts and comments, paragraphs and speaking turns will not be pooled as interchangeable units. Across strata, fixed weights describe a stable source mix; size weights target the documented eligible population. Both choices and their effects will be reported.

Historical public channels remain distinct from contemporary platforms unless overlap supports comparison. IPCC assessments retain a scientific subtype; climate-specialist collections cannot provide government-wide denominators. Missing bins differ from zero counts. Stable IDs, publication/collection dates, parent documents, source role, quoted speaker, location evidence and duplicate clusters preserve provenance and prevent long reports or repeated quotations from receiving uncontrolled weight.

<!-- page: measures -->
## 3.4 Operational definitions and construct validity

The primary outcome is future-oriented warming fear or worry expressed in public texts. Fear, anxiety and worry will be treated as distinguishable, potentially overlapping expressions rather than diagnoses. Fear may concern an anticipated threat; worry often describes thinking about possible consequences. Neither category fixes a time horizon. Immediate heat danger and long-term concern will be collected together and labelled separately.

<!-- table: measures | 0.21,0.41,0.38 -->
**Table 4a. Constructs and measurements.** Similarity, attention, emotion and stance answer different questions.

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
**Table 4b. Synthetic boundary examples.** Labels depend on the target and holder, not isolated keywords.

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

![Figure 2. NLP research pipeline. All three required components share a versioned representation and original context. Validation precedes corpus expansion and substantive interpretation.](assets/figure_02_pipeline.svg)

**Event and relation extraction.** Named entities and parsing support event candidates, followed by an evaluated semantic role labelling (SRL) or contextual relation model. Outputs distinguish event, speaker, described cause, blamed actor, response duty and affected group [@palmer2005; @xia2019]. Evidence spans, negation, modality and quotation remain attached. Events used as external analytical dates are verified independently of narrative extraction.

**Aspect-specific sentiment and emotion.** A suitable GoEmotions-derived candidate will be compared with interpretable cues [@demszky2020]. The aspect is the object being evaluated; the emotion layer distinguishes fear and project-defined future worry. Nervousness will not simply be renamed climate anxiety. The same procedure will check risks reported by institutions and emotions expressed by identifiable holders.

**Temporal topics and semantics.** BERTopic will use a shared embedding space and inspected representations [@grootendorst2022]. Topic prevalence, frame distributions and representative passages will be compared by role and time, with resampling stability and outlier coverage checks. Matched-source context is required before interpreting a shift as changing meaning. The three components remain the agreed method set; validation determines their usable distinctions.


<!-- page: temporal -->
## 3.6 Temporal alignment and analysis

Comparisons require common coverage and frequency: monthly where supported, daily/weekly for dense heat pilots, or common quarters for sparse institutions. Recompute ratios from aggregated counts; never repeat quarterly values into artificial months. Regional GISTEMP anomalies describe climate background; station/ERA5 measures address local exposure [@gistemp; @era5]. Record location evidence, baselines and versions; publication location is not exposure.

**RQ1: ordering and conditional prediction.** Cross-correlation (CCF) explores candidate lags after addressing trends, seasonality and serial dependence. In Equation (4), X and Y are processed series; positive k means X precedes Y. Compare role attention, or policy/media attention with public emotion.

<!-- equation: ccf -->
$$C_{XY}(k)=\mathrm{Corr}\!\left(X_t,Y_{t+k}\right)\tag{4}$$

A small vector autoregression (VAR), where observations and diagnostics permit, will test whether other roles add predictive information beyond the outcome's own history [@shojaie2022]. Report direction, lag range, uncertainty and held-out predictive gain. The largest CCF peak alone will not choose the lag order. Separate role-specific S from public E; B is secondary. Freeze lag limits, outcomes and processing before final comparisons.

**RQ2: event-associated change.** Segmented regression/interrupted time series (ITS) estimates a level change and a post-event slope change [@lopezbernal2017]. Equation (5) uses outcome Y and time t centred on event onset. D switches from 0 to 1 at onset; β₂ is the level change and β₃ the slope change. Disturbance u requires serial-dependence diagnostics and appropriate uncertainty treatment.

<!-- equation: its -->
$$Y_t=\beta_0+\beta_1t+\beta_2D_t+\beta_3(tD_t)+u_t\tag{5}$$

![Figure 3. Measurement and temporal analysis. Curves illustrate possible ordering and level, slope or null responses. All trajectories are schematic, not observed results.](assets/figure_04_temporal.svg)

<!-- page: events -->
## 3.6 Event selection and narrative interpretation (continued)

Select events from independent records before inspecting outcome peaks. Eligibility requires a verified date/interval, common coverage and an auditable denominator. The pilot tests one eligible event. Policy announcement, adoption and implementation, and scientific release and reporting, retain separate dates.

<!-- table: events | 0.26,0.20,0.27,0.27 -->
**Table 5. Candidate event-analysis plan.** The same eligibility rules apply to favourable, null and conflicting patterns.

| Candidate / type | External date | Window / outcome | Comparison and limit |
|---|---|---|---|
| Kyoto adoption / policy | 11 Dec 1997 [@unfccc_kyoto] | Initially ±6 months; S/E level and slope | Historical overlap unverified |
| Paris adoption / policy | 12 Dec 2015 [@unfccc_paris] | Initially ±6 months; S/E level and slope | Anticipation; concurrent coverage |
| Heat episode / physical | ○ Independent onset, peak and end | Dense local window; danger and future worry | Matched exposure; seasonality |
| IPCC release / scientific | ○ Report-specific release date | Common coverage; S/E and frames | Shared shock; media spillover |

The six-month windows are initial specifications, not a guarantee of adequate time points. Longer baselines are needed where trend, seasonality or serial dependence cannot be assessed within them. Inferential windows and aggregation will be fixed before final tests, using coverage and seasonal-baseline adequacy rather than outcome peaks.

Comparison series require comparable pre-event measurement and defensibly different exposure. Another outlet/topic is not automatically a control. Register concurrent shocks and anticipation; inseparable events form a joint window. Placebo dates and alternative windows test sensitivity, not causal identification [@hausman2018].

**RQ3: narrative explanation.** Relation and topic outputs will locate evidence about causes, blame, duties and threatened futures. Similar passages will be checked for quotation and stance before being described as adoption, contestation or reinterpretation. Narrative attribution differs from estimated event effects. Include representative and contradictory passages.


![Figure 4. From language to evidence. The synthetic sentence illustrates overlapping labels and two attribution axes. Its temporal phrase does not prove that policy caused worry; a response duty remains unspecified.](assets/figure_03_evidence.svg)

<!-- page: evaluation -->
## 3.7 Evaluation and validity

Evaluation will test the measurement system before interpreting temporal results. A first development batch of approximately 150 passages, balanced across the three source roles, is a planning allowance for finding label ambiguities and estimating annotation cost; it is not a powered final test. A separate stratified test set will be sized after observing class prevalence, annotation time and the desired precision. Rare labels may require enriched evaluation samples, with their sampling implications stated.

The author will prepare an annotation guide and seek an independent second reader for a subset. Agreement will be reported only where independent ratings exist. If a second reader is unavailable, a separated repeat assessment and documented disagreements will be reported as limited single-author validation, without claiming inter-rater reliability. Development and test sets will be separated by document/duplicate cluster; source and period holdouts will probe transfer.

<!-- table: evaluation | 0.21,0.42,0.37 -->
**Table 6. Evaluation protocol and evidence for success.** Validate measurement before interpreting temporal patterns.

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

Database construction is the largest delivery risk. Analysis will start on an end-to-end increment before expansion. Table 7 prioritises dependency and impact, not measured probabilities; priorities will be reviewed after the pilot. OHS and ethics controls appear in Section 3.10.

<!-- table: risks | 0.22,0.32,0.46 -->
**Table 7. Project risk register.** Database freezes protect analysis time. H = high priority; M = moderate.

| Risk / priority | Trigger or consequence | Response and remaining limitation |
|---|---|---|
| R1 Database delay / H | No pilot increment by October, no core-corpus freeze by 18 December, or preparation exceeds available hours | Freeze the schema; analyse pilot batches; stop non-core connectors. Narrow sources or periods early to protect the February analysis target. |
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

At 10-20 hours/week, the provisional budget is 450-590 hours plus 15% contingency. All analysis and robustness checks must finish by 28 February 2027. The 320-400 hours allocated before March require about 14-17 hours/week before contingency; sustained lower capacity will trigger early scope reduction.

![Figure 5. Calendar and workload share task rows. Shading marks phases; arrows link usable increments; diamonds mark gates. Pale bar ends are upper workload estimates. All values are provisional.](assets/figure_05_schedule.svg)

<!-- table: milestones | 0.18,0.47,0.35 -->
**Table 8. Milestones, estimated effort and resource dependencies.** Gates protect the February analysis deadline.

| Milestone | Deliverable and decision | Timing / effort estimate |
|---|---|---|
| M1 / G1 | Source/access register, minimal schema, scope and deadline clarification | By 30 Sep; 20-30 h; archive/library information and supervisor advice |
| M2 | Pilot by 16 Oct; core corpus and denominator audit frozen by 18 Dec | Sep-Dec; 100-130 h; permitted data, storage and local compute |
| M3 / G2 | Validated labels, frozen encoder and measurement protocol | By 15 Jan; 100-130 h; annotation and independent review if available |
| M4 / G3 | All temporal, event, topic and attribution analyses; robustness checks completed | By 28 Feb; 100-110 h; validated measures and sufficient common coverage |
| M5 | Full thesis, evidence figures, feedback and pitch/poster rehearsal | Mar-14 May; 90-130 h; writing and supervisory review |
| M6 / G4 | Thesis revision, permissible release, reproduction instructions and presentation | 17 May-11 Jun; 40-60 h; release review and clarified thesis deadline |

Assessment anchors: seminar, 12-16 October; Thesis Plan, 1-19 March 2027; rehearsal, 10-14 May; final pitch/poster/demonstration/Q&A, 7-11 June [@reit7842]. March-June centres on writing and feedback using completed analyses.

Missed freezes trigger narrower comparisons while preserving three roles, three modules and the February target.

<!-- page: ethics -->
## 3.10 OHS, ethics and data governance

This is computer-based documentary research, with no planned physical experiment, fieldwork or active recruitment. Workstation and induction requirements will be confirmed before relevant work. Table 9 separates occupational health from data risks; controls will be reviewed when sources and settings are fixed.

<!-- table: ethics | 0.23,0.42,0.35 -->
**Table 9. OHS and ethics controls for the proposed activities.** Review both workstation and data risks.

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
