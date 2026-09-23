# 2010 年前政府语料补充来源调查

日期：2026-09-21。状态：来源搜索与决策报告；未批量抓取、未入库、未修改 proposal。供 Dai 与决策窗口讨论后另行下达采集指令。

## 1. 当前缺口

依据 06 批次 coverage_analysis 的年度和年代 CSV：1988–1989 为 0 条，1990–1999 为 3 条，2000–2009 为 52 条；2010 年前共 55/1,020（5.39%）。2010 年有 14 条；2011–2025 的完整年份仍需逐月/季度和来源结构判断，不能用年代总数证明每月覆盖充分。

本轮查看了用户附的 decade_composition.collision-audit.pdf，并核对配套 CSV。图中的占比是冻结查询的内部构成，不是英国政府历史覆盖率。

## 2. 原因判断与实际遗漏例子

当前筛选固定为 DEFRA 标签 + policy_paper。DEFRA 的官方议会证据说明该部门于 2001-06-08 成立，由 DETR 的部分环境职能、MAFF 及少量 Home Office 职能组成。因此旧机构不能仅靠今日 DEFRA 标签代表。[DEFRA 官方证据](https://publications.parliament.uk/pa/cm200102/cmselect/cmenvfru/991/2071002.htm)

本次实际查到以下政策仍在 GOV.UK，且对照 04 冻结 enumeration_manifest 的 canonical_url 未发现对应发布记录：

- 2003-02-24，DTI，《Our energy future - creating a low carbon economy》，Cm 5761；官方页面列 144 页 PDF。页面已打开；PDF 工具因 32 MB 大小上限未完整读取，不能据此判为源文件不可下载。[页面](https://www.gov.uk/government/publications/our-energy-future-creating-a-low-carbon-economy)
- 2009-07-15，DECC，《The UK low carbon transition plan》，220 页 PDF；页面和 PDF 正文均可由浏览工具读取。[页面](https://www.gov.uk/government/publications/the-uk-low-carbon-transition-plan-national-strategy-for-climate-and-energy)
- 1994-01-25，《Biodiversity: the UK action plan》，Cm 2428；当前页面 From 字段是 Department of the Environment (Northern Ireland)。这说明旧材料登记需要核对原件署名与当前托管标签，不能静默视为同一机构。[页面](https://www.gov.uk/government/publications/biodiversity-the-uk-action-plan)

2006 年《Climate change: the UK programme 2006》则已在现有 manifest，属于重复检查样例，不是新增数量。[页面](https://www.gov.uk/government/publications/climate-change-the-uk-programme-2006)

结论：已证实当前范围漏掉部分相关部门政策；尚未量化这一原因对所有年份缺口的贡献。不能把所有稀疏性都归因于单一机制。

## 3. 候选来源与核验程度

### A. GOV.UK 历史政策与 Official Documents — 优先

用途：优先补 2000–2009，兼顾仍在线的 1990 年代正式出版物。可复用现有 Search/Content API 工作方式；下一次应按明确批准的机构/文种范围枚举，而不是仅凭气候关键词收集几个著名例子。

DTI、DECC 已有具体政策可用证据；DoE、DETR、MAFF、BERR 是需逐项核对职能与历史登记的候选，不能假定全部有可直接调用的完整机构索引。Northern Ireland 的 Department of the Environment 与原 UK DoE 不能只凭同名合并。

议会说明：Official Documents 从 2005 年起提供 Command Papers；政府对专门委员会报告的回应从 1997 年起另可在委员会页面找到。个别更早在线文件不证明全系列完整。[官方范围说明](https://www.parliament.uk/about/how/publications/government/)

预计新增篇数：未知，需按选定范围枚举并与现有记录去重。分母只能是该范围可核验的公开记录集合。

### B. UK Government Web Archive — 旧网站与历史版本

官方 A–Z 索引明确列出 Defra 主站、ww2 站和 Archive。档案于 2003 年开始采集，部分站点最早可至 1996 年；这不是所有部门都覆盖至 1996 年，也不能补齐 1988–1995。[档案说明](https://www.nationalarchives.gov.uk/webarchive/about/)；[A–Z](https://www.nationalarchives.gov.uk/webarchive/find-a-website/atoz/)

官方检索说明支持网站过滤、归档年份过滤及 CSV/JSON 导出，每次搜索最多导出前 10,000 条。年份过滤指抓存时间，不是发表时间；结果是快照，需按原始 URL/文档及版本去重。[检索与导出](https://www.nationalarchives.gov.uk/webarchive/find-a-website/how-to-find-an-archived-website/)

核验程度：官方说明和索引经搜索索引读取；浏览工具直开部分 TNA 页面遇到 403/internal error。本轮没有验证完整的快照导出或文件下载链路，因此它是有明确官方依据的候选，尚不是批量获取已通过的来源。旧域名逐年覆盖也未枚举。[档案技术限制](https://www.nationalarchives.gov.uk/webarchive/find-a-website/limitations/)

### C. Hansard 部长答复／声明 — 1988 年起的直接文本候选

已打开 1988 年 sittings 年目录、1988-07-20 日目录及同日 Greenhouse Effect 书面答复全文，包含问题、发言人、答复、日期和卷栏号。[年目录](https://api.parliament.uk/historic-hansard/sittings/1988/index.html)；[真实答复](https://api.parliament.uk/historic-hansard/written-answers/1988/jul/20/greenhouse-effect)

官方说明：Historic Hansard 为 1803–2005；另一 Commons 日期档案覆盖 1988 年 11 月至 2016 年 3 月。站点和时期重叠需去重，不以域名含 api 推断其提供已验证的批量 REST 接口。[官方档案入口](https://www.parliament.uk/commons-hansard/)

重要范围决定：议会不是行政政府本身。建议优先考虑部长以职务身份发表的答复和声明，并保存问题上下文；反对党问题不能被计为政府观点。ministerial_answer / ministerial_statement 应与 policy_paper 分层，不能把早期答复与后期政策文件直接拼接成同一种单位的趋势。若选择这一系列，应覆盖跨越 2010 的重叠期或延续至后期，避免人为制造渠道切换。

能否完整按部门/职务筛选及确切篇数尚未验证。

### D. UNFCCC 国家通信 — 少量、直接的历史政府报告

- 英国第一份国家通信的 1994 年官方执行摘要：HTML 正文可读；页面本身是摘要，不能标为完整首份报告。摘要说明原报告于 1994 年 1 月出版，而该摘要日期为 1994-10-04，必须区分。[1994 摘要](https://www.unfccc.int/resource/docs/nc/gbr01.htm)
- 英国第二份国家通信：81 页英文 PDF 可读，属 1997 年报告系列。[NC2 PDF](https://unfccc.int/cop3/fccc/natcom/natc/uknc2.pdf)
- 官方 NC1–NC3 索引按国家组织，包括澳大利亚、新西兰、美国和欧洲国家；英国 NC3 的官方审查说明提交时间为 2001-10-30。索引可由搜索读取，直开超时；本轮未逐国验证每个全文。[NC1–NC3 索引](https://unfccc.int/process-and-meetings/transparency-and-reporting/reporting-and-review-under-the-convention/national-communications-and-biennial-reports-annex-i-parties/national-communication-submissions/first-second-third-national-communications-annex-i)；[英国 NC3 审查说明](https://unfccc.int/sites/default/files/resource/docs/idr/gbr03.pdf)

这些是政府提交报告，托管于 UNFCCC；UNFCCC 专家审查报告则是不同作者/文种。报告专题性强、周期较长，适合历史语境和文本比较，不能提供全部政府发布的 attention 分母或填满月度空白。

### E. ProQuest UK Parliamentary Papers — 早期正式文件的有条件候选

英国议会确认其收录数字化编号 Command Papers（1833–2015），可补 1988–1990 年代纸本出版物。需要订阅；本轮未确认 UQ 具体馆藏权限、文本导出或 TDM 授权，不能给执行窗口承诺直接批量抓取。[议会官方说明](https://www.parliament.uk/about/how/publications/government/)

《This Common Inheritance》（1990，Cm 1200）已确认有官方参考文献及书目线索，但本轮没有核验可公开直接获取的完整原件；不列入“全文已确认可用”数量。

### F. Deposited Papers — 次优补充

官方说明：目录从 1987 年起，数字文件从 2007 年 11 月起可用。可以补 2007–2009 的部门材料；早期目录存在不等于早期全文可下载。与政策、答复分别登记文种。[TNA Parliament 指南](https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/parliament/)

## 4. 建议与尚待讨论的范围

1. 优先扩展英国相关部门的正式政策系列（尤其已有真实遗漏证据的 DTI/DECC），再查 Defra 历史站点。政府话语范围按环境/气候政策职能界定，不能默认单个 DEFRA 标签等于该职能的完整历史。
2. 1988–1995 若需要连续性，Hansard 部长答复/声明是值得优先评估的公开来源；但纳入这一文种是一个研究范围决定，而非技术上随意补数。
3. 国家通信作为有边界的历史补充系列；暂不为补英国缺口突然混入其他国家。若未来扩地域，可复用同一官方索引。
4. 纸本文献数字化数据库放在机构访问条件确认之后，不作为本周必须依赖的路径。
5. 新增来源加入既有数据库并按稳定身份、出版编号/ISBN、URL 和内容哈希去重；补充来源不等于重复引入已有批次。
6. 不能仅靠主题搜索结果建立全部话语的分母。当前搜索发现的例子用于证明来源存在；未来采集范围确定后须独立枚举，并报告唯一记录数、年度/季度分布及文本可得率。无法确认历史总体时明确写未知。

当前不发布抓取命令、不启动枚举任务、不宣称能补齐每个月。供下一次讨论的首要选择是：是否同时建立独立的部长答复/声明系列，还是本轮只扩展正式政策文档。
