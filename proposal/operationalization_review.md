# 指标、事件驱动、反馈与数据库风险：方法讨论增量

更新：2026-09-15。状态：研究设计审核与可用于英文稿的段落；未运行语料采集、NLP 或统计实验，未承诺真实效果、已获访问或已完成跨语言验证。本轮先保存方法推理，范围澄清已记录；后续逐节整合英文主稿。

后续用户明确要求所有技术建议先作为设计原型审核，不直接采纳。新增分母、抽样推理与完整原型状态索引见 [sampling_and_denominators.md](sampling_and_denominators.md)。本文件中“用户提出”不表示方法已经验证；已确认的研究主题和范围与技术原型分开管理。

## 1. 本轮用户决定与待澄清项

### 明确支持的推进方向

- 以独立物理事件／气温序列到公众表达的领先与滞后，作为首个可执行分析；再扩展政府、新闻、公众之间的反馈关系。
- 建立政府／政策、新闻媒体、公众／民间三类语料，并保留历史媒体、读者来信和早期网络材料作为候选。
- 核心收集目标为1988年1月至2026年，月度存储为初始共同基准；地理信息用于与气温数据对齐。
- 五类候选测量：关注度、恐惧／焦虑、风险框架、责任归因、立场／极化。
- 交付结构化数据库、Python pipeline 和 thesis；MPS 是用户提出的加速候选，不是已验证的性能承诺。
- 数据库建设周期超预期是用户认为的最大风险；此前其他风险也获用户认可。
- 增加 NLP 技术管线图、指标测量与时序分析示意图。

### 用户已澄清的范围与假说边界

- 用户已确认：“英语核心，中文与新增地区作扩展候选”。美欧澳新继续为核心地理覆盖目标；中文、东亚与 AOSIS 不作为当前必须完成的跨语言／跨地区比较。
- 用户已确认：“仍作为背景／讨论，不预设遗产地位”。文化遗产不成为 thesis 必须证明的核心结论或单独的必做理论目标。
- “1988 年前事件驱动、之后政策与媒体驱动”是待检验假说。核心语料从1988年起，不能单靠该语料检验1988年前后；需要另有足够、可比的前期资料。

## 2. 理论核查与建议表述

| 用户提出的依据 | 核查与可采用的写法 |
|---|---|
| Clayton (2020) | 可支持气候变化的心理反应、焦虑及社会应对背景；本轮读取书目信息与摘要，不将其概括为首次提出所有生态焦虑概念。[来源](https://pubmed.ncbi.nlm.nih.gov/32623280/) |
| Albrecht (2009)／Solastalgia | 与所述标题对应的论文为 Albrecht et al. (2007)，出版网页另显示2009年上线时间。Solastalgia 强调仍身处家园时由环境变化造成的痛苦，不能等同所有未来恐惧或生态悲伤。[书目与摘要](https://pubmed.ncbi.nlm.nih.gov/18027145/) |
| Pihkala (2020) | 2020年的《Anxiety and the Ecological Crisis》与2022年发表的《Toward a Taxonomy of Climate Emotions》应分开引用；后者DOI包含2021但官方引用年份为2022。分类远超fear/grief二分，不能将两者固定对应现场／未来。[2022全文与引文](https://www.frontiersin.org/journals/climate/articles/10.3389/fclim.2021.738154/full) |
| McCombs & Shaw (1972) | 用于议题显著性与媒体／公众议程关系。第二层属性议题设定及框架理论需要另外的文献，不能全部归到1972年文章，也不把媒体必定决定公众关注当作本文已成立的因果关系。[原文书目](https://academic.oup.com/poq/article-abstract/36/2/176/1853310) |
| Brosius & Kepplinger (1990) | 检索确认《The Agenda-Setting Function of Television News: Static and Dynamic Views》；本轮出版社全文未成功读取。暂不将具体“突破阈值”机制或1988年IPCC例子归为该文已验证结论。[出版社记录](https://journals.sagepub.com/doi/10.1177/009365090017002003) |

建议以相关而可并存的维度描述气候情绪，不预设单一连续轴：情绪类别（fear/worry/anxiety/grief等）、即时身体危险线索、未来时间尺度、受威胁对象、情绪表达者。Fear可以面向未来，anxiety可以围绕正在发生的事件；一条文本不能证明某人具有“慢性”或临床恐慌症状。

这里测量的是 **表达出来或被报道的情绪**。自动分析可以减少手选案例，但标签、模型与采样仍需验证，不能以“代码分析”直接宣称客观测量了整个人群的心理。

## 3. 先导研究与竞争路径

### 3.1 第一条可执行路径

选一个有可定位文本及独立气象记录的事件／共同观察期，先验证：区域热暴露变化是否领先于公众文本中的即时危险表达及长期担忧变化。首次先导可局部执行以检查可行性，不据此取消总体广地域覆盖目标，也不把直接酷热替换长期预期的核心兴趣。

物理事件 → 公众表达 → 媒体 → 政策是一个假说；另设媒体／政策先行、同时响应和反馈等竞争解释。一个气温—公众CCF峰值不能确认后两段，更不能证明完整中介链。若要研究“倒逼政策”，需单独建立政策行动清单（宣布、通过、生效、预算／实施等），不能把政策措辞相似度当政策出台。

### 3.2 区分四类“归因”

1. 文本归因：说话者声称什么导致恐惧、谁应负责。
2. 时间关联：哪个序列在数据中先变化。
3. 条件预测：加入某序列过去值是否改善另一序列预测。
4. 因果效应：若没有该事件，结果会如何；需要额外识别条件。

SRL支撑第一类，CCF支撑第二类，VAR／Granger可支撑第三类。它们并不会自动合成第四类。

### 3.3 物理变量与时间尺度

- 月度GISTEMP／HadCRUT适合较长期气候背景；极端热浪需日尺度高温、阈值超越、持续天数等暴露信息，必要时使用站点数据或ERA5日统计。月均异常不能代替几天内的身体热暴露。
- 先存月度长期表，事件先导保留可用日／周表，分析频率由问题与文本密度共同决定。发布不完整的最新月份要标记；“截至2026最新”最终需冻结到具体截止日期／最后完整共同月份。
- GISTEMP公开月度数据及2°网格；HadCRUT有不同网格、基准与不确定性表示。选择主数据产品、记录版本与基准，另一个产品可作敏感性检查，不直接拼接成同一连续序列。[NASA](https://data.giss.nasa.gov/gistemp/)、[HadCRUT5](https://www.metoffice.gov.uk/hadobs/hadcrut5/data/HadCRUT.5.0.1.0/download.html)、[ECMWF日统计](https://www.ecmwf.int/en/forecasts/datasets/era5-post-processed-daily-statistics-single-levels-1940-present)
- 分别保存出版机构位置、作者自报位置、文本讨论地点和事件地点。NYT总部所在地不是每篇报道的热暴露地点；没有位置证据的公众文本保留unknown，不强行匹配当地气温。
- 区域平均的面积权重与人口暴露权重回答不同问题，须预先说明。AOSIS是地理分散的国家联盟，可先国家级对齐再按明确权重汇总，不能当作单一连续气象区域。细小岛屿在粗网格下的代表性需要单独检查。

### 3.4 CCF、VAR与CLPM的选择逻辑

CCF定义建议统一为 C(k)=Corr(T[t], E[t+k])；k>0表示气温先于情绪，代码测试其符号约定。去趋势、季节性处理及必要预白化后探索候选滞后；报告预设范围内的完整结果，不从大量扫描中挑最大峰当确定结论。保留时间依赖的区间估计和滞后多重比较／留出检查。探索窗口与确认窗口尽量分开。[Penn State方法指导](https://online.stat.psu.edu/stat510/Lesson09)

VAR的一个主分析向量可以使用三类来源的同一关注度指标；另一个模型分析各类可比情绪指标。若研究政策注意、媒体框架、公众焦虑组成的异质变量向量，需明确每条系数所回答的不同问题，不能仅凭数值较大宣布“主导”。温度／事件控制可使用VARX或动态回归；气温是否外生和采用哪些控制需声明。不要一次把所有平台×地区×五类指标塞入一个大模型。

模型阶数依据样本量、AIC/BIC、残差和稳定性及时间留出预测选择；CCF峰值不是直接确定多变量VAR阶数。标准稳定VAR要求适用平稳性；存在趋势或协整时比较差分／VECM等适用设计并说明解释变化。使用多变量系统中的条件Granger检验，而非将多个双变量检验称作三变量条件检验。[statsmodels VAR](https://www.statsmodels.org/stable/vector_ar.html)

比较历史窗口可先考虑分时期／滚动VAR，检查覆盖与测量一致。**时间窗口本身不是panel。** CLPM只在确实有重复观察的单位（例如持续可比的国家或社区）与足够结构时列为候选；需区分单位内变化和稳定单位间差异。不存在把CLPM加上就更科学的保证。[Hamaker et al. (2015)](https://research-portal.uu.nl/en/publications/a-critique-of-the-cross-lagged-panel-model/)

## 4. 语料结构审核

三类分析角色可以保留，但机构层内部必须区分：政府政策／沟通、国际政策决定、科学评估。IPCC报告属于科学评估，不等同政府政策，FAR从1990年开始；1988成立是机构事件，不是FAR发布日期。[IPCC职责](https://www.ipcc.ch/2010/02/04/the-role-of-the-ipcc-and-key-elements-of-the-ipcc-assessment-process/)、[FAR](https://www.ipcc.ch/report/climate-change-the-ipcc-1990-and-1992-assessments/)

| 候选层 | 用户提出的来源 | 必须在来源调查中核实 |
|---|---|---|
| 政府／国际机构／科学评估 | IPCC FAR–AR6、UNFCCC、EPA、白宫；国务院／生态环境部为中文候选 | 文种、真实覆盖、原始版本、发布时间、更新／生效日期及许可；长报告不能补成连续月度政策流 |
| 新闻 | NYT、Guardian、WSJ、FT；人民日报、新华社、财新为中文候选 | NexisUni／校图书馆是否实际覆盖该报和该年、全文与批量文本挖掘条件；没有宣称1988–2026连续可抓取 |
| 历史公众表达 | Usenet sci.environment、早期论坛、BBS、读者来信 | 起止年份、缺失、归档时间与原始发布时间、作者／线程字段；来信经过编辑筛选，与当代社交材料分开记录 |
| 当代公众表达 | X档案、Reddit、Facebook等此前候选；微博／贴吧为中文候选 | 合法访问、档案组成、删除／缺失、转载与机器人、地理证据；2006只是候选时代分界，不保证每个平台当时已有可用数据 |

“建制派／商业”可记录为有独立依据的媒体属性，但不能仅按报纸名称预设政治立场。主比较继续按政府、新闻、公众角色；平台、出版者、引述者、文种另存。

月度统一索引保留 **missing与zero的区别**：没有取得材料是missing；在完整规定采样框中没有相关文本才可记0。核心收集起点不等于所有角色／国家共同可分析起点。

## 5. 五类指标：保留目标，修订测量

### 5.1 关注度：相关话语占比

可采用用户提出的阈值相关性比例，命名优先用 attention/relevant-discourse share，避免“semantic density”同时指相似度强度和篇数比例。

令D[r,g,t]为角色r、地理层g、时期t内按固定规则收集的全部合格观察单位，w[i]为已定义的采样／文档权重；R[i]为经过验证的升温相关性标签：

S[r,g,t] = sum(w[i] * R[i]) / sum(w[i])。

R[i]的先导可由 cos(d[i], a) > theta 给出；a使用多条自然语言定义／例句及必要多个原型，既测试未来升温也测试直接高温。只用气候词中心可能漏掉隐含表达；threshold在开发集选定后冻结，在按时期和来源划分的留出数据检查。不同域如需校准，记录规则并检验跨域可比性。

若D只包含气候关键词检出的结果，上式仅代表该检索集合内的比例，不能称平台总体关注度。需背景抽样流或有明确边界的全量来源作为分母，另保留相关语料供深度分析。存储单位可以是passage，但长政策报告分成很多段不应无控制地压倒短帖；预先选择文档级“至少一个相关段落”或文档内权重归一策略，并保存段落级结果。

### 5.2 恐惧、焦虑与时间尺度

GoEmotions包含fear、nervousness、grief等标签，**没有anxiety或eco-dread标签**。GoEmotions-RoBERTa需要指定确切模型，训练域为英语Reddit并不自动支持历史政策语境或中文。[官方标签表](https://github.com/google-research/google-research/blob/master/goemotions/README.md)

分别估计经领域校验的fear、future-oriented worry/anxiety、grief及直接身体危险线索；目标是否关于warming、谁在表达、即时／未来指向均作为单独字段。heatstroke是健康后果词，不自动证明恐惧；children也不自动证明焦虑。词表可作提示／基线，不能让AND规则成为唯一测量方法。

月度E[k] = sum(w[i] * R[i] * p_calibrated(k|text,context)) / sum(w[i] * R[i])；未经校准的输出称model score，不称已校准概率。E衡量相关文本中的表达组成／倾向，不自动等于人群临床焦虑强度。

主报告两条时间序列及不确定性。E_fear/E_anxiety仅作探索性派生指标：分母接近0设不可解释／缺失，不任意添加epsilon得到巨大比率；可补充有条件的归一差值 (E_fear-E_anxiety)/(E_fear+E_anxiety)，但仍需处理低总量。两类表达允许重叠，不据比率将社会划为急性或慢性。

### 5.3 风险框架与语义原型

技术／经济、危机／战争、道德／正义可以作为初始框架族，但可能重叠或需要细分。**词组平均向量不天然正交，单个向量只定义一个方向。** 用Gram-Schmidt正交化也不能保证变换后仍对应原来的三个可解释框架。

用户公式 abs(d·u)/||u|| 是直线投影长度；取绝对值会把朝相反方向的向量也计成高分，不适合作为未经验证的框架强度。更稳妥的首个基线是对归一化多句框架原型计算带符号cosine相似度，同时加入对照表达，进行多标签验证并保留mixed/other/uncertain。

若要研究真正多维subspace，需要足够的框架标注例句拟合基Q，再研究 ||Q Q^T d||^2 / ||d||^2 等描述性量，比较其效度和基线；投影长度或能量本身也不能识别肯定／否定。它作为可研究的方法候选保留，不预先保证比分类更准确。框架份额不强制加起来等于100%，除非另行定义并验证互斥主框架。

### 5.4 SRL与责任归因

SRL抽取谓词论元后，还需要关系判定、否定／引述／情态处理，才能标注cause、blame、duty和affected group。ARG0／ARG1是依谓词框架解释的角色，不等于所有句子通用的罪责者／受害者。例：“The government blamed fossil-fuel firms for the crisis”：blamed的ARG0可能是政府，但被归责对象是企业。

基本记录建议为 speaker + predicate + attributed_actor + relation_type + affected_group + event/time + evidence_span + negation/modality + confidence + model_version。施事者聚类在关系判定后进行；Nature/God应能拆分，自然机制不等于道德责备。

spaCy标准Transformer pipeline提供表示、parser、NER等，**不内置开箱即用的通用SRL组件**；AllenNLP SRL存在但官方库已归档。将独立SRL／关系模型列为候选，通过兼容性、质量和吞吐量比较后选定，不在proposal承诺某个现成包必然可用。[spaCy官方](https://spacy.io/usage/processing-pipelines)、[AllenNLP模型库](https://github.com/allenai/allennlp-models)

归因主体份额在“含可判定归因的文本／事件”中计算，并同时报告归因覆盖率。不能只给已识别主体的百分比，掩盖大量未识别文本；一条归因链内多主体的计数规则需固定。

### 5.5 立场与极化

分开问：承认升温是否存在、是否视为严重威胁、是否支持具体政策、信任何种责任解释。相信威胁不等于支持政策；反对某政策不等于否认升温。

BART-MNLI可作英语NLI基线，但需对命题、引述者、否定与讽刺校验。用户提出的score=P(entailment)-P(contradiction)是[-1,1]内的**连续**分数。使用三分类输出保留neutral／无关；默认zero-shot示例可能丢弃neutral，不能据其配置把所有文本强制推向支持／反对。[模型卡](https://huggingface.co/facebook/bart-large-mnli)

双峰系数受偏度、样本量、分布形状影响，单峰偏态也可能高分，不能单凭Sarle's b声称公众政治极化。[方法说明](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00700/full)

优先报告支持／反对／不确定或未表态比例及完整得分分布；双峰检验、两端占比与峰间分离作为辅助，并做来源构成和模型置信度检查。若研究群体间极化，另需明确群体证据和群体间差异，不能只把总体混合分布命名为群体极化。

### 5.6 避免主结果无限扩展

建议第一先导的主要结果为相关话语占比及长期担忧／恐惧表达指标；即时身体危险表达作对照维度。框架、归因、主题演进与立场用于解释变化；极化及复杂subspace为评估后开展的扩展分析。这不取消三个必做NLP模块；它限制的是同时进行的主假设与多重检验数量。

## 6. 风险：将可控失败与研究结果分开

### 6.1 首要风险——数据库工程拖延

数据库建设按可交付的端到端版本推进，而不等待1988–2026全量齐备后才运行模型。

| 建议节点 | 可检查的交付 | 超时／不足时的处理 |
|---|---|---|
| 2026-09-24 前后，访问决策点 | 每类主角色的候选来源、样本／访问证据、许可状态、时期范围和替代来源表 | 某来源仍只有申请意向时，不让它阻塞其他允许来源；同步评估同角色备选 |
| 2026-10-02 前后，端到端先导 | 一段共同观察期、三类角色、原文—ID—时间—角色—向量—模块输出可追溯；估算清洗与推理工时 | 若字段／接口尚不能支撑分析，优先固定最小schema与导出契约；缩小先导批量而非继续新增抓取器 |
| 2026-10-09 前后，seminar证据包 | 真实覆盖、三个模块尝试、错误类型、成本估计与下一步选择 | 如未能跑通，展示实际阻塞和有证据的调整；不编造完整数据库或模型结果 |

这些是助手提出的内部检查点，需按实际投入调整，不是外部审批完成承诺。先使用满足适用访问／伦理条件的材料。

最小结构先固定document/source/role/text/date/version；清洗、编码和模型推理增量执行、缓存结果、按版本冻结。数据库后端由查询、体量和访问需要选定，不先追求大型架构。年度／平台扩展作为后续版本；新批次可加入，已冻结分析可复现。

建议触发条件还包括：估算剩余清洗／抓取工时超过分配工时，或连续两个内部检查点无可分析增量。依据每周10–30小时重新排资源，停止增加非核心来源连接器；范围调整保留三类角色及三模块，说明广地域覆盖受影响的程度。

### 6.2 历史稀疏：N<100作为预警，不作为普适统计定律

保留用户提出的N<100为候选预警值，但N需注明是独立文档、作者还是去重段落，并同时检查有效样本量与区间宽度。大量同一报告段落不是100次独立社会反应；决定VAR可估计性的还包括时间点数，不只是每月文本数。

需要降频时，对共同比较的序列采用一致、非重叠季度重新聚合；不要某些月份是月度、另一些行是滚动季度却当等间隔序列。重叠滑动窗口会引入依赖、模糊峰值，不创造新样本。WLS可在适用回归中处理已估计的异方差，但不能修复缺失、选择偏差或一般VAR的所有问题。

### 6.3 模型噪声：区分标注一致性和模型性能

保留用户提出的kappa<0.65、F1<0.70作为**待验证的内部预警候选**。Cohen's kappa是两位标注者的适用一致性指标；单人一次标注不能算两人一致性，多标签／多标注者需相应方案。模型F1要注明macro/per-class、独立测试集与关键类别误差。

低一致性先检查概念与标注手册；模型低F1再检查样本量、域差异、校准和选型。连续embedding得分可以作为独立基线，但也可能失真，不能作为无需验证的安全退路。改变指标后重新验证并说明研究问题含义是否改变，保留三个必做模块。

### 6.4 非显著结果：不是失败，也不是相反结论

**不采用“气温p>0.05，所以政策／媒体完全主导”的预案。** 它把未拒绝一个假设误写成证明另一个假设。应报告效应、区间、功效／可识别范围与测量限制；如要支持可忽略效应，需要预先定义有实质意义的等效界限及相应设计。[ASA声明](https://doi.org/10.1080/00031305.2016.1154108)

物理、政策／科学事件、混合驱动模型从一开始都纳入比较，不在看见p值后选择有利故事。无法识别方向或小／零效应可以形成有价值的结果；“政策完全主导”仍需独立证据及更强识别条件。RDiT不能作为不显著后寻找显著结果的替代按钮，政策事件的预期效应、共同冲击和反事实问题仍存在。

真正项目风险是数据／模型无法支持可解释且有界的判断，或预设叙事导致选择性报告；缓解措施为预先记录主要指标、模型与探索性分析边界、保留全部结果和调整理由。

## 7. 交付物的建议版本

1. **版本化研究数据库与可发布部分**：按实际覆盖提供CSV／Parquet；包含来源／角色／地理／时间键、样本量与有效样本量、缺失标记、气象产品与基准、模型及标签版本、五类经验证的特征、质量／不确定性字段、ID／URL和数据字典。1988–2026是目标覆盖，不能承诺所有月×地区×角色都有值。
2. **可复现Python pipeline**：采集／导入、治理、Transformer表示、事件关系／情绪／主题三个模块、时间对齐和分析。MPS经兼容性及吞吐量先导后启用，保留CPU兼容路径；不先承诺加速比。
3. **开放材料**：版权新闻不全文公开是合适的边界；结构特征、原文URL、引文、用户级向量等仍按逐来源许可与隐私条件评估。加工不自动产生再发布权。语料开放部分、受限分析数据、代码与汇总结果分别说明。
4. **Master's thesis**：提出社会情绪问题、解释理论与方法、报告领先／滞后或反馈证据及不确定性、分析责任与主题／语义演进，讨论限制。1988转折、语义相变、文化遗产、政治或物理完全主导均不作为已经保证的结果。
5. **附属方法贡献**：架构、原型测量或算法若有实证改进，再报告比较结果；不把组合现成工具本身当作已证明的算法创新。

## 8. 两张图的具体规格

### F2 NLP技术管线图（完善既有F2，不重复增加同用途图）

三类角色来源（机构层含政府／政策与科学评估子类）→访问与抽样框→文本／时间／角色／地点／去重治理→可追溯数据库→共享版本的Transformer表示。三个并行分支为：①事件／SRL／归因；②对象、情绪与时间尺度；③动态主题与语义演进。每支接验证节点；原文上下文同时供给模块。通过质量检查的输出汇合到角色—地域—时间特征表，再接统计分析与论文解释。

图下注明：数据库与分析迭代推进，受限原文与可公开产物分开；连续分数亦需验证。图中不画模型已完成／性能数字。

### F4 指标测量与时序分析示意（整合此前事件窗口图）

Panel A：一条明确标为synthetic的示例文本 → relevance、fear／future worry、frame、attribution、stance，显示字段与证据位置。

Panel B：三类角色按时间桶形成特征表；左侧接区域气候／日尺度热暴露，右侧接独立政策／科学事件；清楚标注missing、样本量与日期，而非虚构完整覆盖。

Panel C：上部示意时间对齐和正滞后定义；下部两个分析分支：CCF／条件VAR用于时间关联与预测，事件窗口／分段回归用于水平和斜率变化；框架／归因／主题用于解释。所有示意曲线标“illustrative, not empirical results”，不画未经估计的p值／置信区间。

## 9. 可用于英文稿的短段落

### Event-driven pilot and reciprocal dynamics

The first pilot will examine whether independently measured regional heat exposure precedes changes in public expressions of immediate threat and anticipated climate-related worry. Physical-event-led, institution-led and reciprocal pathways will be considered as competing explanations. Cross-correlation will identify candidate temporal associations after accounting for trends, seasonality and serial dependence. Where coverage and diagnostics permit, parsimonious multivariate models will test incremental predictive relationships between institutional, media and public series. These analyses will distinguish temporal precedence, textual attribution and causal identification. Policy action will be recorded separately from policy discourse when examining whether public expression precedes institutional responses.

### Measurement and validation

Attention will be operationalised as the share of relevant discourse within a defined sampling frame. Emotional category, temporal horizon, threatened group and stance will be recorded separately and may overlap. Embedding-based prototypes and pretrained classifiers will be evaluated on source- and period-stratified material before substantive comparison. Scores will remain linked to source passages and versioned measurement rules. Changes in measurement procedures will be documented and revalidated rather than interpreted as changes in social emotion.

### Database delivery and uncertainty

The principal delivery risk is that corpus acquisition and database preparation consume the time required for analysis. Construction will therefore proceed through usable, versioned increments, beginning with a small end-to-end pilot across the three source roles. Source-access and throughput checkpoints will guide expansion, while all three NLP components are tested on eligible pilot material. Uncertain or non-significant temporal results will be reported with their effect estimates and limitations; they will not be used to infer that a competing pathway is exclusively responsible.

## 10. 阅读深度与尚未核验项

本轮查阅官方模型标签／组件／模型卡、统计软件和课程方法说明、气象数据产品页面、IPCC职责与FAR记录；Pihkala分类、双峰系数方法文及ASA声明核查相关正文。Clayton、Albrecht、McCombs使用可访问摘要／书目；Brosius全文未取回，未据此核实“阈值”细节。未逐一核查候选报刊、NexisUni、历史论坛与中文平台的真实访问和连续覆盖，未给它们标为已可采集。完整理论综述与领域验证仍属后续写作／研究任务。
