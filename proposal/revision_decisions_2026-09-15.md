# 解释性修订：已确认设计、术语与记录

## 授权与范围

用户批准按上轮优化顺序直接修改，并要求公式采用独立居中、右侧编号的论文形式。本轮不增加新的方法、模型、语言或必做实验；增加的是已有方法的解释、可执行规则及图表对应关系。

核心：研究升温相关社会情绪，特别是面向未来的恐惧与担忧；比较政府／政策、媒体及公众表达的领先、滞后和叙事归因。NLP 是主要方法，论文是主要学术成果。英语／美欧澳新核心，中文及新增地区为扩展。1938 为历史背景，1988-2026 为目标采集范围，实际分析期由共同覆盖决定。文化遗产仅是讨论背景。

每周 10–20 小时；2027-02-28 前完成全部分析、主题／归因解释及稳健性检查。三月后写作、反馈、修订及展示。450–590 小时＋15% 余量仍为暂定规划。官方最终报告日期冲突仍保留，不假定已澄清。

## 论证顺序与章节契约

| 部分 | 目的与输入 | 允许的结论 | 不允许升级为 |
|---|---|---|---|
| 2.1–2.2 | 气候情绪、议题设定与框架文献 | 构念不同，因此分开测量 | 负面情感就是恐惧 |
| 2.3–2.4 | 最近的实证研究及五种机制 | 条件性时间预期与替代解释 | 五种已经成立的因果机制 |
| 2.5–2.6 | 既有 NLP 和时序文献 | 联合模块补足测量链的不同环节 | 堆叠模型就是算法创新 |
| 3.1–3.3 | 三个 RQ、来源与抽样设计 | 数据／指标／分析一一对应 | 候选平台已有连续历史数据 |
| 3.4–3.5 | 标注原型、计算公式、现有模型候选 | 对表达及其目标进行可重复判断 | 临床焦虑诊断、自动心理强度 |
| 3.6–3.7 | 事件记录、共同窗口与验证 | 关联、预测、事件相关变化及叙事解释 | Granger 或日期断点单独证明因果 |
| 3.8–3.11 | 已确认时间与资源约束 | 冻结和缩减范围保护分析时间 | 默认三月后补做主分析 |

## 本轮证据与阅读边界

沿用 reading_register_complete_draft.md、method_review.md 与现有 31 条参考文献。未新增文献条目，也未声称本轮重新通读全部来源。上轮对照了 Word/LaTeX 模板及 Brulle、Granger 综述的出版者材料；本轮沿用这些核对结果与已有证据登记。五种时间预期为项目提出的竞争性解释，不是引用文献已经证明的共同结论。

| 主张／设计 | 依据或来源 | 本轮处理 |
|---|---|---|
| 多维气候情绪 | Clayton；Pihkala；Albrecht | 情绪、目标、时间、群体分开 |
| 显著性与解释框架不同 | McCombs/Shaw；Entman | S 与框架／责任关系分开 |
| 政治媒体因素与公众关注 | Brulle 2012 | 限定美国、时期、季度调查；文本不默认优于调查 |
| 角色间情绪比较 | Zhou 2023 | 使用为先例，说明平台与事件语境差异 |
| 相似度非情绪或立场 | Sentence-BERT、ABSA、GoEmotions | 相关性与标签分别校验 |
| 角色不是责任 | PropBank；emotion-cause pair extraction | 施事、说话者、原因、责备、义务分开 |
| 主题变动非自动语义演进 | BERTopic 及现有方法审核 | 共同编码、源构成、语境检验 |
| 预测非因果 | Shojaie/Fox；Hausman/Rapson | 写明可支持结论与限制 |
| 事件水平／斜率 | Lopez Bernal 等 ITS 教程 | 为现有分段回归补编号公式 |
| 非显著不能证明不存在 | Wasserstein/Lazar | 保留区间与数据能力解释 |

## 已确定图表

- 图 1：角色关系与外部事件。
- 图 2：数据库、共同表示及三个 NLP 组件。
- 图 3：指标与领先／滞后、事件变化示意（原图 4 内容，按出现顺序重编号）。
- 图 4：合成句的事件、情绪及责任证据（原图 3 内容）。
- 图 5：紧凑日历＋工作量，和里程碑表同页。
- 表 A：按学校原用途分类转置的 AI 勾选表，声明压缩为一页内。
- 表 1–2：文献综合、RQ 总映射。
- 表 3a–b：来源覆盖／状态、抽样单位／分母。
- 表 4a–b：构念测量、合成标注边界。
- 表 5–9：事件计划、验证、风险、里程碑、OHS／伦理。

总计五图、十二个表格面板。三线表、浅底深字；角色颜色仅用于真正表示来源角色的行，不能把含 policy 一词的普通例子误着色。状态同时写文字。长格优先删重复或拆分，未用缩小正文字号强塞一页。

## 专业术语与模型边界

| 术语 | 本文用途／约定 |
|---|---|
| Source role | 发布来源的角色；不等于被引述者或情绪体验者 |
| Emotion-holder | 文本中被归属该情绪的人／群体，允许未知或多个 |
| Attention / salience, S | 合格集合中的升温相关单位加权比例；不是 Transformer attention 权重 |
| Emotion share, E | 相关集合内特定情绪表达的加权比例；主要为未来恐惧／担忧 |
| Joint share, B | 同单位／权重条件下 B = S × E；衍生量，不是独立证据 |
| Semantic similarity | 表示空间中的接近程度；不能直接命名为情绪强度 |
| Aspect | 情感评价或情绪指向的对象 |
| SRL | Semantic role labelling；为关系提取提供角色信息，施事不自动等于责任人 |
| CCF | Cross-correlation function；正 k 表示 X 先于 Y；探索候选滞后 |
| VAR | Vector autoregression；条件预测路径，适用性由观测和诊断决定 |
| ITS | Interrupted time series；本项目既有分段回归的水平／斜率变化分析 |
| Cause / blame / duty | 描述原因、责备归属、应对义务，分别记录 |
| Semantic change | 需要匹配来源和语境证据，不等同于主题频率变化 |

保留词汇／TF-IDF 基线、Sentence-BERT 类表示、已讨论的 SRL／关系方案、GoEmotions-derived 情绪候选、BERTopic，以及 CCF／小型 VAR／ITS。没有新增模型家族或必须运行的新检验。具体版本仍依据先导验证选择，不伪造已经完成的模型选择。

## 公式约定

公式 (1) S、(2) E、(3) B、(4) CCF、(5) ITS。使用矢量数学字形，居中、右侧编号，正文定义符号。MD 保留 LaTeX；HTML 使用独立 SVG 并含文字替代；PDF 嵌入矢量；TXT 保留可读公式和编号。F 的 future 上标明确主要标签，避免 MD 与输出定义不同。

## 审核与取舍

researchwrite 要求的独立方法审查核对了指标依赖、角色／情绪体验者、样本分母及事件解释。已修正 MD 的 future 标签一致性；Gemini 的研究问题／内容反馈勾选没有充分记录，因此不勾选，其已记录的方法建议和文字生成用途保留。

初版扩写为 22 页，合并重复研究缺口说明后为 21 页（含前置页与参考文献）。为保持 12 pt 正文、约 9 pt 表格和五张完整图，接受约 20 页范围内的一页增加。未把图单独放大成整页。参考文献对应检查仍是文件一致性检查，不等于文献结论全部重新验证。

旧版保存在 versions/before_explanatory_revision_2026-09-15/。最终生成／视觉检查见 qa/revision_checks.json、qa/html_checks.json、qa/visual_review.md。

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
