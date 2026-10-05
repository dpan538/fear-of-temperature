> 引用更新：正式UQ来源精简为一条研究伦理Procedure；行政网页用途审查见 [reference_scope_review.md](reference_scope_review.md)。下文保留原先完整核查过程，不能视为当前参考文献清单。

> 后续更新：当前为21页；精简目标与渠道转换诊断见 [compression_review.md](compression_review.md)。以下记录描述上一轮定稿准备及仍有效的研究取舍。

# Thesis proposal 定稿审阅记录 — 15 September 2026

## 当前定位与版本

当前主稿为 `thesis_proposal.md`，同源导出 HTML、PDF、TXT。封面为 **Project proposal**，不再标注 discussion draft。此状态表示可供导师审阅的提案版本，不表示导师批准、伦理批准或已提交。旧稿已归档；旧 `draft_proposal.*` 路径仅作为最新文件的兼容链接。

标题：**Fear of temperature: Computational analysis of policy, media and public climate emotions**。

定位：使用可验证 NLP 与时间分析管线的 computational social science / climate communication 研究。研究对象仍为社会情绪与升温恐惧；时间排序和叙事解释仍为主问题。计算资源、基线、评估与复现更显眼；没有改为算法 benchmark，没有新增联合训练架构，也没有将附属代码取代学位论文。

## 用户建议的推理与处理

| 建议 | 处理及理由 |
|---|---|
| 技术副标题 | 采用 computational analysis，避免标题提前暗示管线已通过验证。 |
| RQ 后加技术路径 | 保留三项社会问题；补上 CCF/conditional VAR、ITS、证据跨度和跨来源检验。 |
| Technical resource / validated method / empirical contribution | 纳入 1.4；全部是拟议贡献。 |
| multi-task pipeline | 写为 modular pipeline；共享表示不等于多任务联合训练。 |
| Emotion fine-tuning | 不作为已决定或必做实验；保留 GoEmotions-derived candidate 与可解释 cues，先验证迁移。 |
| LDA / 新编码器消融 | 未新增强制实验。现有 TF-IDF 比较、BERTopic 配置/重采样、固定来源/编码器及窗口敏感性承担当前评估。 |
| 删除时间对齐作为消融 | 不把破坏可比性当成有效基线；时间对齐是估计有效性的条件。 |
| 运行成本与复现 | 显式 documents/hour、peak memory、runtime、annotation cost，以及 code/config/seeds/data dictionary。 |
| 图形工程化 | Figure 3 加任务/验证；Figure 5 加 baseline 与 versioned embeddings；Figure 6 加 CCF/VAR/ITS 和输入输出，三角色曲线补线型。 |
| 2.4 视觉重设计 | 保持待讨论；没有擅自重绘机制结构或调色。 |

## 3.8：触发条件与替代方案

R1–R8 均写出 trigger 和具体 fallback。数据库按 18 December core freeze 控制，超时优先停止扩张并保留可验证批次。Reddit 若在 pilot gate 不可用，首先评估有许可的 Mastodon 实例/社区；不是承诺该平台有完整历史档案。更早公众材料可以评估获许可的来信、论坛归档，但更换群体必须单列时期/来源，并重新审核共同窗口和 all-topic 分母。没有合格公众层则缩小可比较窗口并记录未回答的 RQ，不伪造跨平台连续总体。

Mastodon 官方 public timeline API 支持公开状态读取，但实例可能禁用预览或要求认证；该接口不保证所需历史深度、地域代表性或再发布许可。依据：[官方 timelines 方法](https://docs.joinmastodon.org/methods/timelines/)。

## 3.10：UQ 伦理程序核查

核查日：15 September 2026。研究与提案写作本身不等于已经取得伦理许可。

- **导师审核是本项目承诺的前置关卡。** 由 Dai Pan 请 Mashhuda Glencross 审核来源、权限、可识别性、存储与释放方案。不是声称 UQ 对每一种自然语言文本都规定完全相同的审批流程。
- **正式伦理程序另行判定。** UQ Human Research Ethics Procedure 涵盖涉及人及其数据的研究；公开可见不自动豁免。现有数据豁免有低风险、去标识、禁止重识别、原始收集/复用合规、数据保管人权限等条件，豁免仍须登记 MyResearch。教学训练豁免不能作为拟发表研究的当然依据。
- **学生不能当伦理申请 CI。** MyResearch FAQ 建议适当情况下由 UQ 导师作为 CI；只有 CI 可提交申请。提案没有替导师确认其已接受该职责。
- **人工 A/B 评审只作后续条件分支。** 导师先审 protocol/recruitment/consent/tasks/data plan；REI 确认是否构成人类参与者研究以及新申请或 amendment 路线。相关招募与数据收集必须在所需批准之后。普通导师质量复核不能代替正式审批。
- 应联系单位为 **UQ Research Ethics and Integrity**；申请指导页列明 Human Ethics Coordinators：`humanethics@research.uq.edu.au`。本轮没有发邮件或提交任何伦理申请。

官方依据：

1. [Human Research Ethics Procedure](https://policies.uq.edu.au/document/view-current.php?id=346)，尤其 clauses 8–10、14–18、44；全文 HTML 留存于 QA 来源目录。
2. [Ethics application](https://research-support.uq.edu.au/resources-and-support/ethics-integrity-and-compliance/human-ethics/ethics-application)：MyResearch、申请类别、变更及联系地址；全文 HTML 留存。
3. [MyResearch frequently asked questions](https://research-support.uq.edu.au/resources-and-support/research-systems/myresearch/myresearch-frequently-asked-questions)：学生/CI/提交权限；官方页面本轮读取。

## APA 7 与来源核对边界

- 正文采用作者—年份；多篇文献按字母排序，同机构同年加 a/b/c，并在首次 UQ 引用中定义缩写。
- 文末按作者字母排序，作者姓名与缩写、句首式标题、期刊/卷斜体、会议编辑/出版者、Article number、0.5 inch hanging indent、完整 DOI URL。
- 19 篇期刊/正式会议文献已有 DOI；本轮补充 BERTopic 的 arXiv DOI **10.48550/arXiv.2203.05794**。合计20项 DOI。没有给无 DOI 的机构页面虚构 DOI。
- 易变的机构/API/数据/软件页面记录实际检索日；有 DOI 的固定出版物不机械添加访问日期。课程2026页面引用课程年份。
- 保留 UQ proposal 的版面、页眉页脚与紧凑行距；APA 7 用于引用体例，不声称整篇文档套用了 APA 学术期刊手稿的双倍行距模板。
- Crossref 完整元数据成功核对16项；4项 ACL proceedings 另外读取官方 BibTeX，补全 editors、venue、publisher。Crossref 限流项以 ACL / Wiley / ScienceDirect 页面可得记录补充。所有成功取得的 Crossref 作者与原稿一致。
- 保留 Pihkala 2022 的正式出版年份，不以 DOI 中2021覆盖；Lopez Bernal 保留最终卷期2017/46(1)/348–355，不误用 online-first 2016；McCombs 保留完整页段，不以 Crossref 的仅首条页码覆盖。
- 这是引用格式和指定字段核查，**不等于重新通读全部34项参考资料或重验所有文献结论**。网络获取失败/限流写在 `qa/finalisation_sources/fetch_log.json`，没有当成成功。
- APA 原则参照 [Griffith Library APA 7](https://www.griffith.edu.au/library/study/referencing/apa-7)；官方 APA 页面遇到读取限制，未伪称阅读全文。

## 定稿前仍应确认（不写入提交正文的内部事项）

1. 用户与导师核实最终 Thesis Report 日期。按用户要求，日期冲突警示没有放回 proposal。
2. 导师对研究范围、英语核心、三角色数据可用性及 CI/伦理路线的意见。
3. 用户最后审阅 AI use 声明与实际使用是否一致；没有为淡化 AI 而删除已发生的用途。
4. 2.4 图的审美取舍仍可讨论。该待讨论项不等于当前图有检测到的溢出。

每周10–20小时、2027年2月底完成所有分析、450–590小时加15% contingency 的规划保持一致。提案可以提交审阅；正式数据访问、模型定型和审批结果仍由后续 pilot/学校程序决定。
