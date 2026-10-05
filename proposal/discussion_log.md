# Fear of Temperature 第二轮研究定位与决定记录

更新日期：2026-09-15。用途：保存用户在本次对话中的最新定位，供后续逐步写作使用。本文件不是已经完成的研究结果，也不是课程政策。用户当前直接指示优先于旧稿、Deep Research 建议和旧交接文件。

当前主目录：项目最外层 `proposal/`。`draft_proposal.md` 是主稿；HTML、PDF、TXT 是从主稿生成的阅读版本。本记录持续追加决定与理由，旧材料中的意见不自动转为研究要求。

## 当前研究定位

- 核心研究对象是人／社会对气候变化与气温升高的情绪，重点为恐惧、焦虑及其表达与关联。
- 历史主要说明数据的时间跨度和来源背景。文化遗产最多是背景或未来讨论方向，不能预先认定本研究对象已经构成文化遗产。
- 用户概括：**核心是用计算机制去承载人文命题。**
- NLP 与 AI 是核心研究方法，服务于作者自己的社会情绪研究，不把项目替换为供其他研究者使用的检索系统研究。
- 自动采集、结构化处理、文本表示及计算分析旨在减少研究者逐条判断和挑选材料所带来的影响。模型与代码的有效性仍需检查；计算输出不是天然无偏的事实。
- 用户希望体现足够的 NLP／AI 应用和创新。具体课程 rubric 尚未取得；不能宣称任何方法组合已保证满足评分或发表要求。

## 成果目标

1. 第一项可能的贡献：通过互联网信息采集建立数据库，形成可开放的语料资源。全文、元数据、派生特征与代码的开放范围分别核查，不预先声称所有抓取文本可再分发。
2. 可能的可扩展研究架构。
3. 可能的算法或方法改进，是否形成独立创新由实际研究决定。
4. 以实际研究发现为依据，完成具有可发表潜力的 thesis／论文；不承诺录用或预定结果。

## 时间与来源

- 1938 是暂定的早期起点／科学背景锚点。
- 用户认为 1988 前后是更合理的主要分析起点，理由包括 IPCC 成立及 Hansen 国会证词；“全球恐慌已经发生”不能直接作为由这些事件推出的事实。
- 核心比较现已明确为政府／政策话语、新闻媒体报道、公众表达三个来源角色。新闻媒体正式纳入主设计；社交平台是承载渠道，不直接等同于公众角色。
- 用户进一步确认：**以英语为主，主要集中在美国、欧洲、澳大利亚和新西兰，需要广阔的地域覆盖；优先主流社交平台（如 Facebook）与论坛。** 欧洲内部国家、具体论坛与平台访问途径尚未固定。英语材料不自动代表当地全部语言群体或全体公众。
- 用户随后补充：**社交来源不限于 Facebook，可以多列几个具备开放访问可能的候选网站。** 已加入 Reddit、YouTube 评论、Bluesky、Mastodon、Stack Exchange 和其他公开论坛作为待评估候选；不等于承诺全部采集。访问与再分发核查见 source_candidates.md。
- 不默认社交媒体或 Google Trends 存在自 1988 年起的连续记录。跨数据流比较使用实际重叠期。
- 原 34-source／180-candidate 工作属于旧探索背景，不能当作新语料规模或真值。没有在本轮移动或覆盖旧数据。

## 用户明确要求的三个必做模块

1. 事件与关系抽取：提取参与者、谓词／关系、对象、时间与地点，研究文本中关于升温、后果、情绪与行为的叙述关系。
2. 细粒度情感与情绪分析：面向温度／气候相关 aspect，分析恐惧、焦虑及其他相关情绪；检查表达者、对象和引用关系。
3. 动态主题与语义演进分析：研究话题构成及相关表达随时间的变化。

模块必须保留。spaCy、Stanza、BERT-NER、OpenIE、GoEmotions、BERTopic、Top2Vec 是候选实现，不要求全部实现；具体工具能力和标签需核实。

## 第一优先实证目标

用户选择的主问题是 **谁先变化：政府／政策话语、新闻媒体报道与社交媒体中的公众情绪之间的领先和滞后关系**。气温与科学／政策事件提供事件背景和解释变量。地域与语言主要作为分层、协调口径和统计调整因素，不再作为独立核心比较问题；广地域覆盖目标保留。

用户认为当代政府与新闻媒体话语高度绑定。这是值得检验的工作预期，不作为已经证实的跨国家事实。政府与新闻媒体保留独立标识与序列，以检验同步、领先、滞后或共同事件响应。用户强调按人群治理数据，再进行向量化研究；当前以来源／表达者角色作为首层划分，进一步人群分类仍待定义，不擅自推断个人身份、政治立场或人口属性。

候选方法包括语义特征时间序列、事件窗口、CCF、VAR 与 Granger 检验。将它们作为拟研究的方法，适用性由时间覆盖、观测数量和序列诊断决定。Granger 检验识别条件预测关系，不能单凭该检验确证社会心理或政策的因果机制。

## 新确认：恐惧范围与归因框架

- 统一采集升温相关自然语言；长期气候预期为分析重点，同时纳入直接高温威胁，在采集后标记，允许同一文本同时包含两者。
- 用户提出的初始解释框架：个体生存、家庭／下一代未来、社会集体焦虑；短期具体、长期预期、超长期想象／推演。
- 实现上将“受威胁对象／社会范围”与“时间尺度”分开记录，保留交叉与多标签。集体焦虑可以发生在当前热浪，家庭担忧也可以涉及长期未来；具体年数阈值尚未定。
- 事件与关系抽取模块加入 SRL（语义角色标注）、情绪—原因配对与叙述因果链提取。
- 两个归因轴：①时间节点与事件；②原因机制与责任主体。后者分别记录物理原因、道德／政治责备及应对责任，避免将语法施事者自动认定为责任人。
- 自然／不可抗力、工业化、制度／系统失灵、个体消费及人类整体责任等作为候选叙述类别；不预设自然解释只属于早期／非科学，也不把类别演变写成已知历史结论。
- “恐惧几乎总伴随归因句式”作为待核查的经验预期。无明确归因、隐含归因、否定和不确定表达均可保留，不作为排除语料的理由。

## 新确认：政策同时作为事件与文本

- 以独立记录的重大制度／政策节点为锚点，初始考察前后各六个月，比较公众表达的水平、增长斜率、语义分布及责任框架。
- 候选锚点：1988 年 IPCC 成立（制度事件，具体分析日期待定）、1997 年京都议定书通过、2015 年巴黎协定通过。通过、签署、生效和报道时间分别记录；早期节点只使用实际存在且可取得的公众材料。
- 分段／中断时间序列用于区分即时水平变化与后续斜率变化；前后差异不自动构成因果断点识别。±6 个月为先导窗口，不预先承诺足够统计功效或显著结果。
- 政策文本另用于分析风险对象、原因解释、责任分配和应对义务；比较新闻／公众是否采纳、引用、质疑或重新解释这些框架。
- 语义相似度不能独立判断赞同或反对；框架关系、立场和情绪分别测量。
- 本轮细化的是研究设计，没有运行模型、采集数据或发现实际领先／滞后。

## 撤回的助手解释

- 撤回“文化遗产是项目核心立场”的判断。
- 撤回“NLP 方法研究替换原项目、历史仅充当技术案例”的判断。
- 撤回“帮助其他研究者检索是主要目的”的判断。
- 撤回“检索是最终唯一主任务，三个内容模块可以仅作可选扩展”的潜在解释。

## 写作进度

- 已记录：以上研究定位与用户决定。
- 已完成初步核查：事件锚点、工具能力、情绪标签、动态主题方法、时间序列推断与候选平台访问条件；实际阅读深度及未决项记录在 method_review.md 和 source_candidates.md。
- 已逐步写入英文稿：模板前置结构、AI 使用记录草案、Introduction、三个研究问题、支持目标与初始方法设计。配套引用独立保存，不覆盖原始第二轮参考文献。
- 后续逐节完善：文献综述、三个模块的具体方法、时间序列设计、时间表与风险、AI 声明和最终排版。

## 仍需实际信息

欧洲具体国家、政策来源、论坛名单及平台历史访问能力；可用算力与预算、正式身份／导师信息。英语优先及美国／欧洲／澳大利亚／新西兰的广地域覆盖目标已由用户确认，无需重复询问。页数、每周工时及多数日期已在下文“学校材料对照”更新；最终报告日期存在公开课程页面冲突，尚需澄清。

## 2026-09-15 本轮更新与讨论记录

### 已实施的内容决定

- RQ1 改为政府／政策、新闻媒体与公众表达谁先变化，保留同步和双向反馈的可能。
- RQ2 改为政策／制度节点前后的水平与斜率变化。
- RQ3 改为事件、时间尺度、原因机制与责任框架及其采纳／质疑／重释。
- 新闻媒体成为主设计的数据流；平台、发布者角色、被引述者与被描述群体分开记录。
- 政策文本不必表达“恐惧”一词：风险表述、情绪报告、责任分配可分别分析。
- 统一收集后标注长期预期与直接高温。人群／受威胁对象与时间尺度采用不同字段，不强制三个互斥类别。
- SRL 与情绪—原因配对、上下文关系抽取共同支撑两个归因轴；未经验证的隐含解释不得作为确定责任。
- 跨组与跨窗口使用同一版本的向量编码器，保留文本级记录和组内分布。政策相似度与立场分别测量。

### 用户提出的预期，与暂不作为事实的部分

- 政府与新闻话语高度绑定：作为待检验预期；保留两条独立来源序列。
- 恐惧表达几乎总带归因句式：待先导样本验证，不能据此丢弃无明确原因的文本。
- 政策节点可能产生显著结论：研究目标是估计方向、大小与不确定性；不把显著性作为项目成功的必要条件。
- 地域／语言作为归一参数：主次安排已接受；具体调整不能自动消除采集与测量差异。

### 方法细化的理由

政策前后的即时跳变和之后增长速度变化是两个参数。初始采用分段时间序列思路，保留 RDiT 作为需额外识别条件的方法，而不将简单前后差异称作政策因果效应。六个月窗口若按月聚合仅约十二个时间点，具体频率、基线与模型复杂度需由数据覆盖决定。三个历史锚点不等同于三个都已有可用社交数据的实验。

### 用户文件组织要求（原话）

> 我们需要在fear of temperature的文件夹中的最外层开一个proposal的文件夹，然后在里面写draft proposal，并且我需要html和pdf以及txt三种格式，还要有专门的md文档记录过程和我们讨论中的内容

已执行：建立最外层 `proposal/`，复制并更新当前主稿及研究记录，以共同内容源生成三种阅读格式；旧目录保留迁移指引。没有把草稿占位章节伪装成完整 proposal。

### 下一轮真正需要讨论的内容

1. 公众内部的人群划分：首先按社区／参与角色／自述的家庭或生活情境，还是其他有文本证据的分类？研究不默认掌握个人真实人口属性。
2. 核心指标：恐惧表达比例、焦虑得分、风险框架占比与责任归因分布，哪些作为主要结果，哪些作为解释变量？
3. 第一项事件先导：优先选数据最充分的较近政策事件，还是以巴黎协定为首个历史案例？需先查覆盖。

## 2026-09-15 学校材料对照、20 页规划与日历核查

### 用户新增要求与确认

> 我们还需要继续讨论，因为这份proposal的合理程度大概是20页左右
> coordinator提到中间有些是要用图表展示的，我们根据学校给到的内容以及example再来讨论我们还缺什么内容，以及哪些地方要用图表，要画什么图，表要怎么画，risk和预期的时间节点怎么做。

用户后续确认页数口径：

> 整份 PDF 约 20 页，包含前置页与参考文献

用户提供日期与工时（原话）：

> proposal截止日期是9月17日，详细的可以查具体的reit7842的assessment，progress seminar 12/10/2026 - 16/10/2026, thesis plan due by 1/03/2027 - 19/03/2027, thesis report 26/10/2026 3:00 pm, thesis 3 minutes pitch 7/06/2027 - 11/06/2027
> 每周大概投入10-30小时不等

### 材料与权威边界

- 读取三份 proposal 示例（23、23、18 页）与 S4／S5 讲义（28、29 页）文本，视觉检查关键结构图、比较表、甘特图和风险页；不声称重核全部示例引用或视觉检查全部页面。
- 五份 PDF 原样归档于 `course_materials/`，与 Downloads 原件哈希一致；示例题目、实验、工时、年份及伦理判断不成为本项目要求。
- 当前公开评分表为 Topic Definition 20%、Background 30%、Project Plan 20%、Presentation 25%、Professional Practice 5%；S5 截图中的 Project Plan 25% 另行记录版本差异。OHS／Ethics 是单列通过要求。

### 讨论建议，尚未拍板

- 全稿预算 20 页：前置4、Introduction 2、Background/Literature Review 4、方法与评价5、资源时间1.5、风险OHS伦理1.5、参考文献2。
- 主文建议5张图：研究关系、数据与三模块流程、文本到指标的标注示例、政策事件窗口／水平与斜率设计、甘特图；真实数据覆盖热图待先导后考虑。
- 建议6类研究表：近邻文献、来源与共同窗口、概念指标、RQ—评价对应、里程碑资源、风险；AI 声明表另计。
- 风险写成影响—触发点—应对—剩余限制，并与里程碑关联；不虚构概率评级、实验准确率、显著性或真实结果图。
- 按每周10小时安排核心必做工作，20小时周推进主路径、30小时作为阶段余量，是助手建议；假期投入尚未确定。

### 核查结果与冲突

- 浏览器直接核实本届 `REIT7842-60234-7660`：proposal 为 2026-09-17 15:00；用户列出的其他日期均与公开页面相符。
- **公开大纲确实将 Thesis Report 写为 2026-10-26 15:00，与其跨两学期结构及2027 Thesis Plan的顺序冲突。没有把用户日期认定为笔误，也没有擅改成2027某日。** 最终期限需课程明确说明；研究长程日历为有条件方案。
- 补入2027-05-10至05-14 F&3MP预演反馈。2027-06正式项目包括pitch、poster、demonstration与Q&A。
- 本届assessment未列独立Conference Paper；可发表论文仍属用户研究目标，不从旧届网页新增必交课程任务。

### 文件与进度

- 详细规划：[course_alignment_and_plan.md](course_alignment_and_plan.md)。
- 日期和公开评分表依据：[assessment_calendar_review.md](assessment_calendar_review.md)。
- 本轮保存讨论与规划；英文主稿与HTML／PDF／TXT未扩写。接下来优先完成文献论证、主要指标、来源窗口与评价表，再将已确定内容逐节写入正文。

## 2026-09-15 指标、事件驱动与数据库风险讨论

### 用户进一步提出的设计

- 首先用独立气温／热浪事件与公众情绪表达做滞后分析；随后比较政策、新闻与公众的反馈回路。
- 三类语料候选扩展到IPCC／UNFCCC／EPA／白宫、主要报刊数据库、Usenet／读者来信／论坛及当代社交档案；核心时间目标为1988年1月至2026年，以月度索引组织。
- 五类指标：相关话语占比、fear与anxiety、风险框架、责任归因、立场与极化；提出锚点、GoEmotions、投影、SRL和NLI的具体候选做法。
- 提出CSV／Parquet衍生时序库及Python pipeline；版权新闻原文不全文开放；MPS为加速候选。
- 用户指出最大风险是数据库建设超时挤压后续开发，并认可此前其他风险。
- 用户认可增加NLP技术管线图与指标测量／时序分析示意图。

### 已回答的范围问题（原话）

> 英语核心，中文与新增地区作扩展候选

> 仍作为背景／讨论，不预设遗产地位

因此保留美欧澳新英语核心；中文、东亚、AOSIS作为扩展候选；文化遗产仍不作为已成立结论或必做理论目标。

### 助手审核后的修订建议，不能冒充用户已确认

- 同时保留物理驱动、机构／媒体驱动、共同响应与反馈，不预先确认单向因果链；政策行动需要独立事件字段。
- GoEmotions没有anxiety标签，fear／nervousness与即时／长期时间尺度不能直接对应；词表是线索，连续分数也要验证。
- 框架原型不天然正交；绝对投影可能把相反方向计成高强度。先比较多原型相似度／多标签基线，真正subspace方法保留为需验证的候选。
- ARG0／ARG1不等于罪责者／受害者；责任关系需要引述、否定、语义关系和证据片段。spaCy标准pipeline不内置SRL；AllenNLP归档状态进入选型风险。
- 月度气候背景与日尺度热暴露分开；出版地不等于事件地／受众暴露地；有统一月索引不代表共同覆盖完整。
- 用户提出N<100、kappa<0.65、F1<0.70保留为待验证预警候选，不记为学校标准或最终验收门槛。
- 不接受“气温p>0.05即可推断政策完全主导”的推理；零／不确定结果仍报告，不能根据显著性切换结论。
- 建议数据库按端到端先导、增量扩展与冻结版本推进；9月24日、10月2日和10月9日是建议内部检查点，不是外部审批或实验完成承诺。

### 文件状态

已写入 [operationalization_review.md](operationalization_review.md)：完整指标审核、来源深度、风险与两张图规格，并附三段可用于英文稿的文字。当前图仍为设计规格，未生成实证图；英文主稿与三格式导出本轮未改动。待方法讨论收束后再逐节整合，保持同源导出。

## 2026-09-15 分母原型与推理要求

### 用户原话与新增原型

> 我们现在还有哪些问题需要解决？我给的所有内容都需要你给一定的推理，不要直接采纳，但可以作为设计原型记录

- 媒体：当月主题新闻篇数／目标媒体总新闻篇数；查询LexisNexis／ProQuest总量。
- 政策：同机构主题政策／议会记录字数或段落数／全部同类记录总字数或段落数；候选季度聚合。
- 公众：所选Subreddit／Usenet等社区主题帖子数／全部帖子数；候选分层等额抽样或档案总量。

### 记录规则更新

技术公式、工具、阈值和机制全部先标为原型；与已确认的研究主题、范围、三个必做模块及论文主导分开。助手审核建议不得写成用户已确认，未经先导检验不得写成已验证。历史日志中的“用户提出”不代表自动接受其方法有效性。

### 本轮主要推理

- 分子分母同范围、同过滤、同单位、同日期与去重规则；抽样分子不直接除全库分母。100条随机样本中10条相关估计10%，不是用10除全库10,000。
- 数据库收录总量不自动等于媒体真实全部发稿；检索候选中的NLP分类还需检查召回遗漏。产品说明未证明UQ具体订阅或个人权限。
- 政策文种分层；气候专项报告不能代表政府总体议程。段落、词数、文档份额各有不同解释。
- 政策季度序列与其他序列做共同频率分析时统一重聚合，使用分子分母之和；不把季度值复制成三个独立月份。
- 公众帖子／评论／线程分开；固定样本量应层内随机，跨社区汇总需明确平均社区或总体帖子份额及权重。档案内总量不是平台完整真值。
- 三种salience可研究变化关系，但数值大小不具天然相同含义。保留相对比例、绝对相关量和总量；关注度与情绪条件比例分别分析。
- 官方RFR说明五年历史窗口及六个月延迟，Pushshift API限获批版主管理用途。已存来源链接；未将历史档案一概判为不存在，也未声称获批研究访问。

### 文件与剩余问题

已新增 [sampling_and_denominators.md](sampling_and_denominators.md)，含三原型详细审核、所有方法原型状态索引，以及提交前／先导期／写作行政三组待办。下一步优先决定主结果、公众分群／采样框、首个先导选择规则、单位频率和验证资源；具体样本数、theta与滞后阶数由明确的先导程序确定。英文主稿与HTML／PDF／TXT本轮未改动。

### 随后确认的作者、导师与稿件日期

用户原话：

> author是我的话就是Dai Pan，supervisor是Mashhuda Glencross，submit的日期暂定写9月16日，可以写入到proposal draft中

已实施：author=Dai Pan；supervisor=Mashhuda Glencross；稿件日期=16 September 2026（暂定）。课程截止2026-09-17 15:00仍单独记录。导出脚本改为读取主稿元数据，同步HTML、PDF、TXT与PDF作者属性；检查三种格式文字、12页总页数及受影响的封面／AI声明页视觉效果。方法原型仍只存讨论文件，未自动并入正式方法正文。

## 2026-09-15 完整草稿与视觉修改

### 用户授权与后续纠正

> 目前的信息应该已经足够开始写draft了，我觉得可以开始写一版完全的，所有的图表都是全的，给我之前先看一下图表有没有溢出，是否足够通俗易懂并且是否注意视觉排列

> 重点是视觉性和复杂性都需要提高，现在的时间轴就是不够复杂，或者装饰性不够

> 不是要你这样，这个图没必要单独占一页，可以试一下 git clone https://github.com/Yuan1z0825/nature-skills.git … scripts/update-codex-skills.sh --pull

### 本轮实施

- 完成英文 Introduction、Background and Literature Review、Project Plan、AI statement、Abstract、Contents 和 References；补齐五张矢量图和八张表。
- 保留社会情绪作为研究对象、论文主导、三 NLP 模块必做、英语／美欧澳新核心、文化遗产只作背景、三类来源比较和两个归因轴。
- 三种分母原型经审核后写成同范围、同单位的抽样估计设计；不把检索候选数量除以全库数量。
- 150 段开发批次、210–290 h 工作包和15%余量是本轮拟议规划，不是实测成本、学校标准或用户逐项确认。
- 曾尝试整页时间规划并使文档达到21页；用户明确否定，已归档并恢复嵌入式双面板时间图和20页排版。旧方案不是当前要求。
- 用户指定的 Nature Skills 仓库已克隆，执行更新脚本并校验20个技能目录；本次采用 nature-figure，沿用既有 Python 后端。
- 紧凑时间图以共用任务行的“日历／依赖”主面板和“工时范围”辅助面板增加信息密度；不靠增大页面制造视觉复杂度。
- 三格式共享主稿、引用与图形，TXT提供图形文字等价说明；源文件、素材、脚本与 QA 记录保存于本目录。

### 仍需确认的事项

最终 Thesis Report 的2026-10-26日期冲突仍未解决；具体数据访问、先导共同窗口、最终模型／阈值、独立标注资源和节假日投入将在既定先导流程中确定。提交前还需作者核读 AI 声明并补充能够确认的模型／使用信息。完整草稿不等于已经完成研究或可以绕过这些检查。

## 2026-09-15 最新工时与完成节点（覆盖之前的计划）

用户明确：

> 基本我们的要求是每周10-20小时，所以不要把工作量预估这么轻，其实应该在3月之前就完成所有的analysis

已确认的约束更新为 **每周10–20小时**，**2027年2月底前完成全部分析及稳健性检查**。3月之后主要论文组织、写作、反馈修订、发布与展示；不再把主要分析安排到3–4月。

重新估算的工作包为：M1 20–30h，M2 100–130h，M3 100–130h，M4 100–110h，M5 90–130h，M6 40–60h，总计450–590h，另留15%余量。前四包320–400h安排在3月前。**这些工时区间仍是助手提出的规划估计，不是用户逐项确认、实测耗时或完成记录。** 它们替代此前过轻的210–290h版本。

按9月中旬至2月底约24周，前期需要约14–17h/周，加入15%余量约16–20h/周。因此不能声称长期保持10h/周也能无条件完成同一范围。若连续投入偏低，需提前收缩来源、时段或模型比较数；三角色、三模块和2月底分析目标保持可见。各包工时不是在整条日历柱上均匀分布，重叠期间需要动态分配。

内部检查点同步改为：9月30日访问／schema；10月16日先导；12月18日核心语料冻结；1月15日测量验证／编码器冻结；2月28日全部分析与稳健性完成。课程最终报告日期冲突仍独立记录，未被这次内部计划自动解决。


## 2026-09-15：批准解释性修订与编号公式

用户确认方法和专业术语已经足够，要求不引入新方法，只拓展解释，并批准按“RQ 映射→理论／文献→标注、分母与事件→前置页→视觉检查”的顺序修改。公式参照截图采用独立居中、右侧编号。已完成的设计决定、术语边界、图表清单和取舍见 revision_decisions_2026-09-15.md。新版保留每周 10–20 小时与 2027-02-28 前完成全部分析的安排。正文 12 pt，表格约 9 pt；为完整展示新增解释及图表，本版共 21 页（含前置与参考文献）。AI 声明保留在开头，压缩至一页以内，保留真实用途与模板分类；不以减少强调为由改变已记录使用事实。

## 2026-09-15：彩色图形与连线优先的视觉重构

用户指出前版字数增加而视觉吸引力不足，导师偏好带线条、彩色图案的表，要求使用 skill 并在交付前检查、迭代。

本轮采用 nature-figure：五种竞争机制由连续五段改为带 H1–H5 的节点连线图；RQ 总映射、抽样分母、风险触发—应对改为彩色图形化表格；三角色来源流汇入数据库与共享表示，再进入既定三 NLP 模块；时间线将计划工时分布、阶段色带、纹理、冻结点和交付卡片整合。原普通表格面板从 12 个减为 8 个，矢量图从 5 张增为 9 张，PDF 保持 21 页，公式仍为 5 个，参考文献仍为 31 条。

字数统计采用构建脚本同一规则：Markdown body 的词元从 6548 到 5883（减少约 10%）。该口径含标记/图注，不含图内文字，也不是学校正式字数；一部分信息转入图形，不能解释为全部阅读量减少同样比例。

进行了独立图和整页渲染迭代：修复三角色连接线压字、时间线分隔线穿过标签、短工时区间不明显、可选纹理边界、时序标签被图层覆盖及端点标签裁切；微调时序标签行距，压缩两页冗余句使排版回到边界内。未缩小正文到 12 pt 以下，未新增方法、来源承诺或研究结果。保留 10–20 h/周、2 月 28 日前全部分析完成、课程截止日期冲突、抽样与因果解释边界。图示曲线明确标记为示意；所有工时均为计划。

## 2026-09-15 22:41 feedback: targeted fixes and two pending redesigns

用户允许直接简化 AI-use Table A，修复 3.5 管线和 3.6 RQ1 公式重叠；2.4 与 3.8 要先讨论修改方案。

已实施：Table A 恢复早期两列、每工具一行，保留真实用途与日期，移除逐类别打勾矩阵；声明未删减真实 AI 使用范围。管线的来源输入改为公共汇流线，唯一箭头进入数据库顶端；共享表示通过独立分流线进入三个模块。CCF 的 Corr 改为数学运算符，并用正间距替换原负间距；LaTeX、PDF、HTML、TXT 同步。所有数学含义和既有研究组件不变。

### 尚未实施：2.4 的建议方案

问题：五条彩色底条和 G/M/P 字母需要读者反复解码，箭头链条显得像已知机制；一行一色主要起装饰作用，并未提高可检验含义的辨识度。

建议：用白底的三角色时序关系图，保留 H1–H5 的五个假设面板。角色写全称（Policy / Media / Public）；每行从左到右统一表示相对先后，标出起始角色以及可能响应角色。H4 用一个明确标注的外部事件节点分叉连接三角色；H5 用双向连接，注明仅是候选反馈关系。配色限于深灰正文、低饱和蓝色路径、少量暖色外部事件，角色用位置和文字辨认。每个面板配一句可观察结果（如政策注意力领先媒体/公众），同时说明可能共同驱动、非固定完整中介链。无伪造数据曲线、数值时滞或新模型。

### 尚未实施：3.8 的建议方案

问题：九个同宽色条及多数 H 徽章使风险几乎等重，颜色与风险等级或触发点无稳定对应。最大的数据库风险没有成为视觉重点，读者仍要逐行阅读长表。

建议：重构为“关键路径与风险控制点”：上方主路径为来源访问→可用先导→核心语料冻结→测量冻结→2月底分析完成，在先导/核心语料节点下直接给出延误时的缩减动作。保留既定节点日期，数据库延误作为唯一强调项。下方保留简短辅助风险登记，按数据访问/覆盖、测量与时序有效性、资源/备份、课程日期四组组织，并保留 R1–R9 的追溯关系。白底、深灰细线、低饱和蓝色阶段，深赭色标关键触发；不画缺乏评估依据的概率×影响热图。具体触发与应对保留正文。两图方案待用户选择后才绘制。

## 2026-09-15: adopt coordinator-preferred example structure for Section 3.8

User identified Sections 3.4 and 3.5 of `Proposal_44796231-Language learning.pdf` as coordinator-approved examples. Read all relevant source sections (physical pages 11-15): 3.4.2 uses Risk / Potential Damage / Risk Rating / Mitigation Strategy; 3.5 gives available working time, contingency, Gantt chart, hours by task, and milestone duration/resources/deliverables. These are structural examples, not project-specific instructions or verified requirements for this project. Do not inherit 2022 dates, school participant risks, device testing, 25% contingency, or that project's permission workflow.

Implementation: Section 3.8 becomes 3.8.1 Risk assessment (four-column table) and 3.8.2 Review points and scope adjustment (dates/resources/decisions linked to existing Section 3.9). Existing R1-R8 controls remain. Graphical risk routes removed from current exports; schedule renumbered Figure 8, risk table Table 6, OHS table Table 7. Section 2.4 remains awaiting discussion. Neutral header and a muted rating column replace decorative row colours.

### User correction: keep deadline clarification out of proposal

User: “Conditional on clarification of the published 26 Oct 2026 report deadline.这个暂时不要加在proposal中，我明天会和老师核实”. Remove this warning, risk R9 and corresponding reading-note/body references from current MD/HTML/PDF/TXT, plus the schedule footer. Keep the issue here only: user intends to check with the teacher on 16 September 2026. Removal is a presentation decision; it does not verify or change the actual course deadline. No reminder or message to the teacher has been scheduled or sent.


## 2026-09-15：定稿准备与轻度 CS 表述

用户要求风险具体替代方案、UQ ethics 核查、APA 7、短图注及明确2.6研究空白。已迁移到 thesis_proposal.*（22页），旧draft路径仅为兼容链接。随后用户确认提高CS技术可见度：标题、1.2/1.4、2.5、RQ技术说明、3.5、Table5与Figures3/5/6同步更新。研究对象、三角色、三个必做NLP模块和既定分析集不变。multi-task改为modular；不承诺未经决定的微调/LDA/新架构。

详细推理、官方条例来源、引用核查范围和待导师核实事项见 finalisation_review.md。已把“导师方案审核”与“学校正式伦理判定/批准”分开；人工A/B评审仅为后续条件分支，未引入新的强制实验，也未联系学校。2.4视觉结构保持待讨论，报告日期冲突仅留内部。


## 精简目标纠正与渠道转换诊断

用户澄清：目标不是20页，而是精简不必要的重复说明并压缩多余空白。按此停止以页数倒逼删文；当前21页，正文/图形字号保持，参考文献适度紧排。3.6加入复用公式(5)的Channel-transition diagnostic，R6交叉引用；基于独立覆盖节点、固定来源检查和转换两侧可比观测，只作composition-bias警示，不预设虚假情绪或因果结论。完整推理与修改见 compression_review.md。


## UQ引用用途审查

用户质疑四条UQ引用的必要性。核对正文后，保留Human Research Ethics Procedure；Ethics application、MyResearch FAQ、REIT7842课程页移入过程/课程记录。CI操作权限和联系邮箱从正文移除，导师审核、MyResearch伦理判定、豁免和后续人类评估审批义务保留，由直接支持这些要求的正式Procedure引用。其余文献按理论、方法、数据、事件、平台和AI声明核对用途；现在31条、20项DOI。详见reference_scope_review.md；不是为了引用条目数或页数删文献。
# 16 September 2026 — Similarity and structure scope update

The author clarified that the intended pipeline uses pretrained representations, similarity retrieval and tree/graph topology rather than separate emotion classification, SRL or topic modelling. Fear remains central through validated fear/worry reference passages and contextual counterexamples. MiniLM is primary; ClimateBERT is a bounded separate comparison; FAISS is retrieval infrastructure. RQ wording, measurements, figures and evaluation were synchronised. Tree/graph edge semantics remain a pilot decision. See `similarity_revision_2026-09-16.md`; the earlier proposal and assets are archived in `versions/before_similarity_revision_2026-09-16/`.
# 16 September 2026 — Source priorities, six risks and topology comparison

Implemented author-requested source priorities (GOV.UK, Guardian, preferred Reddit application), cross-role/historical normalisation standards, model-fit/tuning cost, low-risk model replacement, implementation dependencies, human-data ethics and rollback risks. Added independent, initially project-unfamiliar methodological review with neutral guidance, distinct from supervisor oversight and UQ ethics determination. Added topology sketch and comparison of similarity hierarchy, dependency, constituency, WordNet, causal-event and group-evolution approaches. Core remains validated similarity; auxiliary parsing is not a mandatory new pipeline. See `sources_topology_ethics_revision_2026-09-16.md`.

## 2026-09-16 — RQ3 ownership and atomic risk register

User correction: tree methods belong to RQ3; risk rows must separate distinct failure conditions and sort High → Medium → Low. Moved detailed topology sketch/comparison from 3.5 to the RQ3 part of 3.6. Section 3.5 now covers representation/retrieval with a hand-off reference. Reference-validation figure moved beside reference validation; figure/table numbering regenerated in reading order.

Split 9 bundled risks into 17: High R1 cross-role harmonisation, R2 historical channel change, R3 corpus construction delay, R4 model suitability, R5 fine-tuning overrun, R6 integration conflict, R7 ethics clearance, R8 source access denial, R9 insufficient coverage, R10 measurement failure; Medium R11 analysis specification, R12 compute capacity, R13 independent review, R14 release restrictions, R15 personal disruption, R16 artefact loss; Low R17 better model release. Atomic means one manageable failure condition, not statistical independence. Each row has a trigger and response. Ratings are management priorities, not measured probabilities.

Exported HTML/PDF/TXT, 23 PDF pages. Automated layout audit: no overflow. Rendered and visually reviewed topology and risk pages; retained font sizes and reduced risk-cell padding. Prior exports preserved in versions/before_atomic_risks/.

## 2026-09-16 — Mechanism explanations, construct boundaries, diagnostics and numbering

Expanded H1–H5 into separate theory/observable-expectation paragraphs. Added four construct-boundary paragraphs covering fear/anxiety/worry, anticipated harm/time, voice/negation and modality. Added five diagnostic paragraphs covering missingness, trends/seasonality, variables/lags, residuals/uncertainty and multiplicity/inference. The approximately 13 observations in ±6 months are explicitly insufficient as an assumed adjusted ITS design; longer eligible estimation windows or descriptive limits are required.

Renumbered distinct sections and subheadings: sources 3.3, harmonisation 3.4, concepts 3.5.1–3.5.2, representation 3.6, analysis 3.7.1–3.7.4, evaluation 3.8, risks 3.9, milestones 3.10, ethics 3.11, outputs 3.12. RQ3 still owns the tree design. Checked supplied original Word/LaTeX templates: neither contains Abstract. No abstract added. Updated directory and old figure/table-list labels. Exported and visually inspected 23-page PDF plus HTML/TXT; retained font and figure sizes. See mechanisms_diagnostics_revision_2026-09-16.md for evidence and validation details.

## 2026-09-16 — Restore the earlier SVG pipeline style

User preferred the earlier 3.6 pipeline visual. Compared archived and current figures; restored the database cylinder, coloured embedding matrix, source branches and connected flow from the pre-similarity-revision design. Labels retain the current bounded method: MiniLM, FAISS, reference validation, optional separate ClimateBERT representation and RQ-specific outputs. The tree remains the RQ3 endpoint; removed legacy emotion/SRL/topic commitments were not restored. Figure is an illustrative workflow, not observed data; coloured matrix cells do not encode measured values. No methods or section numbering changed.

Updated generator plus SVG/PDF/PNG assets and proposal HTML/PDF/TXT. Collision audit PASS (zero failures/warnings); visually inspected figure and full 3.6 page. Proposal remains 23 pages, no overflow. Backups: versions/before_pipeline_style_restore/.
