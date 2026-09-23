# 06 批次真实文本质量报告（供 Dai 审阅）

> 生成时间：2026-09-21T18:41:26+10:00。范围：现有 06 批次；只读检查，不联网、不补采、不向量化、不调用模型、不改写原始文件、不改数据库结构。

## 结论摘要

06 批次共有 **3,025 个对象、2,853,343 个片段、143,725,193 个字符**。片段总量主要由 PDF 驱动：PDF 占 96.22%；前 20 个对象又占全部片段的 29.32%。
整体片段长度中位数仅 **39 字符**；定义“极短”为 **≤20 字符**，共有 **879,748 个（30.83%）**。核心原因是 PDF 按页面换行逐行/块切分，而非自然段切分。
按文本量启发式判断，984 / 1020 个发布记录的正文主要在附件；只有 3 个明显以网页为主，20 个网页与附件均有实质内容。网页提取成功不能代表政策全文已经取得。
当前数据层适合做可追溯的 source_extracted 存档，但不宜把全部 285 万片段直接投入向量化或语言分析。

## 1. 对象、片段与字符数量

分类口径：`网页`只指 1,020 个 publication landing page；HTML 附件归入`其他`，避免把发布页与附件混在一起。字符数为当前 `segment_text` 的 Unicode 字符数之和。

| 格式组 | 对象数 | 下载成功 | 提取成功 | 片段数 | 片段占比 | 字符数 |
|---|---:|---:|---:|---:|---:|---:|
| 网页 | 1,020 | 1,020 | 1,020 | 19,116 | 0.67% | 1,308,969 |
| PDF | 1,375 | 1,375 | 1,362 | 2,745,617 | 96.22% | 125,381,080 |
| CSV | 22 | 22 | 22 | 11,520 | 0.40% | 3,049,298 |
| 其他 | 608 | 599 | 591 | 77,090 | 2.70% | 13,985,846 |

`其他`包括 538 个 HTML 附件、60 个 ODT、2 个 ODS、2 个 PPTX，以及无文本片段的 ZIP/XLS/PNG；完整明细见 [01_format_summary.csv](01_format_summary.csv)。

### 片段数最高的 20 个对象

| 排名 | 标题 | 格式 | 片段数 | 占总片段 | ≤20 字符 |
|---:|---|---|---:|---:|---:|
| 1 | Draft Marine Bill - Full Text | pdf | 149,429 | 5.24% | 95.12% |
| 2 | Humber river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 97,409 | 3.41% | 38.71% |
| 3 | South West river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 77,176 | 2.70% | 38.95% |
| 4 | Anglian river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 73,156 | 2.56% | 40.19% |
| 5 | Severn river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 70,453 | 2.47% | 38.99% |
| 6 | North West river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 58,718 | 2.06% | 40.04% |
| 7 | Thames river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 52,666 | 1.85% | 42.28% |
| 8 | Northumbria river basin district RBMP 2009 Annex B: Water body status objectives | pdf | 33,553 | 1.18% | 38.86% |
| 9 | RDPE programme document 2014 to 2020 | pdf | 24,704 | 0.87% | 26.15% |
| 10 | Department for Environment, Food and Rural Affairs/Welsh Assembly Government - Launch o… | pdf | 20,634 | 0.72% | 91.85% |
| 11 | Draft Water Bill - Full Text | pdf | 20,207 | 0.71% | 24.08% |
| 12 | Draft Natural Environment and Rural Communities Bill - Full Text | pdf | 19,789 | 0.69% | 74.32% |
| 13 | The Insolvency (England and Wales) Rules 2016: Keeling Schedule | pdf | 19,640 | 0.69% | 14.68% |
| 14 | An economic analysis to inform the air quality strategy | pdf | 18,983 | 0.67% | 31.51% |
| 15 | National Food Strategy: part two | pdf | 18,021 | 0.63% | 22.36% |
| 16 | Draft Climate Change Bill - Full Text | pdf | 17,258 | 0.60% | 73.32% |
| 17 | South East river basin district RBMP 2009 Annex C: Actions to deliver objectives | pdf | 17,256 | 0.60% | 57.61% |
| 18 | Fine Particulate Matter (PM2.5) in the UK | pdf | 16,506 | 0.58% | 23.00% |
| 19 | Coastal Change Pathfinder Review | pdf | 16,060 | 0.56% | 22.80% |
| 20 | Draft Flood and Water Management Bill - Full Text | pdf | 14,845 | 0.52% | 14.61% |

前 20 个对象合计 **836,463 个片段（29.32%）**。最高对象《Draft Marine Bill - Full Text》单独产生 149,429 个片段，其中 95.12% 不超过 20 字符。

## 2. 切分粒度

极短片段的审阅阈值定为 ≤20 字符；同时在配套 CSV 中给出 ≤5、≤10、≤20、≤30 四档，避免阈值选择掩盖分布。

| 范围 | P25 | 中位数 | P75 | P90 | P95 | P99 | ≤20 字符数 | 比例 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 全部 | 16 | 39 | 80 | 91 | 100 | 256 | 879,748 | 30.83% |
| 网页 | 20 | 43 | 92 | 152 | 212 | 363 | 5,482 | 28.68% |
| PDF | 15 | 38 | 79 | 90 | 95 | 117 | 865,050 | 31.51% |
| CSV | 250 | 273 | 294 | 316 | 335 | 386 | 135 | 1.17% |
| 其他 | 40 | 114 | 259 | 440 | 573 | 872 | 9,081 | 11.78% |

全部片段中，≤5 字符 301,720 个（10.57%），≤10 字符 505,237 个（17.71%），≤30 字符 1,230,343 个（43.12%）。

当前记录语义如下：

- 网页及 HTML 附件：标题与 `main` 中的 h/p/li/blockquote 元素，一元素一片段，属于段落/列表项级。
- ODT：h/p 元素，一块一片段，近似段落级。
- PDF：页面文本按换行拆分，locator 为 `page=N;block=M`；这是行/块，不是自然段。
- CSV：每一行一个片段，单元格按列序用 ` | ` 拼接，locator 为 `row=N`。
- ODS：每一非空行一个片段，仅拼接非空单元格；未保存工作表名和单元格坐标，空列位置可能丢失。
- PPTX：一张幻灯片内的段落/文本块一片段。当前没有按单元格独立存储的记录。

网页 extractor 已移除 nav/footer/cookie banner，但仍保留 `Details, Documents, Sign up for emails or print this page, Updates to this page` 这 4 类固定服务性文本，共 4,076 个片段，占网页片段的 21.32%。这不是正文缺失，但会污染语言频率。

## 3. 12 个可读样例

下列“当前提取结果”未改写文字内容；`⟦片段边界⟧`仅为本报告加入的展示分隔符，PDF 内嵌控制字符以 `⟨U+XXXX⟩` 可视化。每个对象展示开头、中部、结尾窗口，完整内容仍在原数据库和原始文件中。

### 1. RDPE programme document 2014 to 2020（网页）

来源：[https://www.gov.uk/government/publications/rdpe-programme-document-2014-to-2020](https://www.gov.uk/government/publications/rdpe-programme-document-2014-to-2020)；对象 `cnt_94b75aa5b50aa70a7ff0`；139 片段，极短片段 6.47%。

- **开头 · `html:title → main:p[2]`**：RDPE programme document 2014 to 2020 - GOV.UK ⟦片段边界⟧ RDPE programme document 2014 to 2020 ⟦片段边界⟧ Formal programme document setting out, in detail, what the Rural Development Programme for England will achieve. ⟦片段边界⟧ Applies to England ⟦片段边界⟧ Publication for Northern Ireland ⟦片段…
- **中部 · `main:li[41] → main:li[44]`**：making small changes to align the Programme document with the underpinning state aid notifications ⟦片段边界⟧ making an adjustment to add potential RDPE delivery bodies ⟦片段边界⟧ making amendments to balance financial adjustments ⟦片段边界⟧ The second modification adjustments were adopted …
- **结尾 · `main:p[35] → main:h2[8]`**：Programme document updated following our first Programme modification (adopted 4 July 2016), includes adjustments that were requested by the Commission, proposals from Defra and setting up of the emergency Farming Recovery Fund. ⟦片段边界⟧ 9 December 2015 Updated state aids document…

审阅：网页本身有较长说明，但两个 PDF 附件文本量约为网页的 96 倍；完整方案正文主要在附件。 DOM 主内容顺序可追溯；末尾仍包含 GOV.UK 更新/打印提示。 未见站点导航栏，但保留 Details、Documents、Updates 等服务性结构文本。 **建议：网页可作元数据/摘要；政策正文以附件为主，避免把“网页提取成功”当作“全文已齐”。**

### 2. Designation of structures and features for flood and coastal erosion risk management purposes: Information note（网页）

来源：[https://www.gov.uk/government/publications/designation-of-structures-and-features-for-flood-and-coastal-erosion-risk-management-purposes-information-note](https://www.gov.uk/government/publications/designation-of-structures-and-features-for-flood-and-coastal-erosion-risk-management-purposes-information-note)；对象 `cnt_f1cf4af61edc7903aff8`；11 片段，极短片段 18.18%。

- **开头 · `html:title → main:blockquote[1]`**：Designation of structures and features for flood and coastal erosion risk management purposes: Information note - GOV.UK ⟦片段边界⟧ Designation of structures and features for flood and coastal erosion risk management purposes: Information note ⟦片段边界⟧ A newer version of this publicat…
- **中部 · `main:p[2] → main:p[4]`**：A newer version of this publication is now available at: ⟦片段边界⟧ www.defra.gov.uk/publications/2012/07/20/pb13804-fcerm-info/ ⟦片段边界⟧ This information note is about the statutory designation of structures and other features (natural or manmade) as defined by the Flood and Water Ma…
- **结尾 · `main:p[4] → main:h2[3]`**：This information note is about the statutory designation of structures and other features (natural or manmade) as defined by the Flood and Water Management Act 2010 (the 2010 Act), and the implications of designation for designating and responsible authorities in England and Wal…

审阅：无附件，正文主要位于网页；当前提取覆盖标题、说明和更新信息。 DOM 段落顺序合理，片段数量少。 含标准 GOV.UK 结构标题，但正文段落本身可读。 **建议：可直接进入后续文本处理，先过滤固定服务性标题。**

### 3. Memorandum of understanding: enforcing wildlife crime（网页）

来源：[https://www.gov.uk/government/publications/memorandum-of-understanding-enforcing-wildlife-crime](https://www.gov.uk/government/publications/memorandum-of-understanding-enforcing-wildlife-crime)；对象 `cnt_bf22e780896f75e2298d`；14 片段，极短片段 35.71%。

- **开头 · `html:title → main:p[3]`**：Memorandum of understanding: enforcing wildlife crime - GOV.UK ⟦片段边界⟧ Memorandum of understanding: enforcing wildlife crime ⟦片段边界⟧ Partnership For Action Against Wildlife Crime policy on how high-level groups can work together to stop wildlife crime. ⟦片段边界⟧ Documents ⟦片段边界⟧ http…
- **中部 · `main:h2[3] → main:h2[5]`**：Updates to this page ⟦片段边界⟧ 9 July 2014 Replaced document with link to the latest version. ⟦片段边界⟧ Replaced document with link to the latest version. ⟦片段边界⟧ 1 December 2008 First published. ⟦片段边界⟧ First published. ⟦片段边界⟧ Sign up for emails or print this page ⟦片段边界⟧ Related content
- **结尾 · `main:p[3] → main:h2[5]`**：This memorandum sets out the roles and responsibilities of Natural England, Countryside Council for Wales, Crown Prosecution Service and the Association of Chief Police Officers of England, Wales and Northern Ireland, so that they can help each other to prevent, look into and ta…

审阅：落地页与所谓 PDF 附件均得到 HTML，且实质片段完全精确重合；附件链接未形成独立 PDF 正文。 DOM 顺序正常。 主要风险不是导航噪声，而是网页/附件重复计数和 MIME/落地结果误判。 **建议：保留两条获取记录，但正文处理只保留一个逻辑副本，并把附件标成重复候选。**

### 4. Noise policy statement for England（普通 PDF）

来源：[https://assets.publishing.service.gov.uk/media/5a7956e0ed915d0422067947/pb13750-noise-policy.pdf](https://assets.publishing.service.gov.uk/media/5a7956e0ed915d0422067947/pb13750-noise-policy.pdf)；对象 `cnt_b5f4b427261c58559d61`；252 片段，极短片段 16.27%。

- **开头 · `page=1;block=1 → page=2;block=9`**：Noise Policy Statement for England ⟦片段边界⟧ (NPSE) ⟦片段边界⟧ March 2010 ⟦片段边界⟧ www.defra.gov.uk ⟦片段边界⟧ Department for Environment, Food and Rural Affairs ⟦片段边界⟧ Nobel House ⟦片段边界⟧ 17 Smith Square ⟦片段边界⟧ London SW1P 3JR ⟦片段边界⟧ Telephone 020 7238 6000 ⟦片段边界⟧ Website: www.defra.gov.uk ⟦…
- **中部 · `page=6;block=39 → page=7;block=1`**：2.7 In addition, the application of the NPSE should enable noise to be considered ⟦片段边界⟧ alongside other relevant issues and not to be considered in isolation. In the past, the ⟦片段边界⟧ wider benefits of a particular policy, development or other activity may not have been ⟦片段边界⟧ g…
- **结尾 · `page=9;block=39 → page=10;block=7`**：will be opportunities for such measures to be taken and that they will deliver potential ⟦片段边界⟧ benefits to society. The protection of quiet places and quiet times as well as the ⟦片段边界⟧ enhancement of the acoustic environment will assist with delivering this aim. ⟦片段边界⟧ Page \| …

审阅：10 页政策说明可读，片段以完整文本行为主。 页码与块号单调，正文阅读顺序基本合理。 包含版权页、页眉/页脚及少量短行；重复片段率低。 **建议：内容可用；进入段落级处理前按页合并相邻行并剔除重复页眉/页脚。**

### 5. Three-year report on the South East Inshore Marine Plan（普通 PDF）

来源：[https://assets.publishing.service.gov.uk/media/6862521a62b2e559cbd753fb/South_East_Report__2025_.pdf](https://assets.publishing.service.gov.uk/media/6862521a62b2e559cbd753fb/South_East_Report__2025_.pdf)；对象 `cnt_3500a8001e519734136e`；266 片段，极短片段 8.27%。

- **开头 · `page=1;block=1 → page=2;block=2`**：Three-year report on the South East ⟦片段边界⟧ Inshore Marine Plan ⟦片段边界⟧ For the period 23 June 2021 to 22 June 2024 ⟦片段边界⟧ Presented to Parliament pursuant to Sections 54 and ⟦片段边界⟧ 61 of the Marine and Coastal Access Act 2009 ⟦片段边界⟧ June 2025 ⟦片段边界⟧ We are the Department for Envi…
- **中部 · `page=6;block=5 → page=6;block=9`**：Process monitoring ⟦片段边界⟧ Since the adoption of the Plan, plan use training delivered to external decision-makers, ⟦片段边界⟧ such as Local Authorities, Natural England and Inshore Fisheries Conservation ⟦片段边界⟧ Authorities, has shifted to online engagement due to the constraints of …
- **结尾 · `page=9;block=16 → page=12;block=2`**：to identify clear trends in plan policy effects and effectiveness. However, it is advised that ⟦片段边界⟧ the recommendation is reassessed once the outputs of the Marine Spatial Prioritisation ⟦片段边界⟧ Programme, the replacement East Marine Plan, the Winser Review, and the Strategic ⟦…

审阅：报告正文可读，短片段比例较低。 页码与块号单调，正文顺序整体连贯。 句子常被换行切成两段，结尾不一定对应 PDF 最后一页的完整逻辑结尾。 **建议：可作为可用正文，但建议在下游按页面/句子重组，不改写 source_extracted 层。**

### 6. Government response to the ‘One Year On’ assessment（普通 PDF）

来源：[https://assets.publishing.service.gov.uk/media/5a7c774c40f0b62aff6c1dce/pb13882-farming-reg-task-force-gov-response.pdf](https://assets.publishing.service.gov.uk/media/5a7c774c40f0b62aff6c1dce/pb13882-farming-reg-task-force-gov-response.pdf)；对象 `cnt_cbc39b369a7bdd20494b`；254 片段，极短片段 37.80%。

- **开头 · `page=1;block=1 → page=1;block=9`**：Department for Environment, Food and Rural Affairs ⟦片段边界⟧ Farming Regulation Task Force ⟦片段边界⟧ Implementation Group ⟦片段边界⟧ Government response to the ‘One Year on’ ⟦片段边界⟧ Assessment ⟦片段边界⟧ February 2013 ⟦片段边界⟧ Contents ⟦片段边界⟧ Introduction ........................................…
- **中部 · `page=5;block=31 → page=5;block=38`**：guidance by March ⟦片段边界⟧ 2014. ⟦片段边界⟧ We are conducting a root and branch review of data collected from ⟦片段边界⟧ farmers to determine whether we are collecting the right information to ⟦片段边界⟧ serve our underlying objectives. Through this review, we will look for ⟦片段边界⟧ opportuniti…
- **结尾 · `page=8;block=6 → page=8;block=12`**：Policy Team, The National Archives, Kew, London TW9 4DU, or e-mail: ⟦片段边界⟧ psi@nationalarchives.gsi.gov.uk ⟦片段边界⟧ This document/publication is also available on our website at: ⟦片段边界⟧ www.defra.gov.uk/food-farm/farm-manage/farm-regulation/ ⟦片段边界⟧ Any enquiries regarding this doc…

审阅：正文可抽取，但短片段偏多，尾部包含网址和联系信息。 页码与块号单调；中段文本可读。 37.8% 片段不超过 20 字符，页眉、网址和联系栏会进入语言文本。 **建议：先做页内相邻行合并和页眉/联系栏标记，再纳入语言处理。**

### 7. Draft Marine Bill - Full Text（长报告/法案）

来源：[https://assets.publishing.service.gov.uk/media/5a74e63d40f0b65f61323253/7351.pdf](https://assets.publishing.service.gov.uk/media/5a74e63d40f0b65f61323253/7351.pdf)；对象 `cnt_7e6de02166f756401f80`；149,429 片段，极短片段 95.12%。

- **开头 · `page=1;block=1 → page=4;block=2`**：Draft Marine Bill ⟦片段边界⟧ April 2008 ⟦片段边界⟧ 7598-TSO-Marine Bill-Part 1.indd 1 31/3/08 18:30:58 ⟦片段边界⟧ Draft Marine Bill ⟦片段边界⟧ Presented to Parliament by the Secretary of State for ⟦片段边界⟧ Environment, Food and Rural Affairs ⟦片段边界⟧ By Command of Her Majesty ⟦片段边界⟧ April 2008 ⟦片段边…
- **中部 · `page=325;block=2 → page=325;block=21`**：⟨U+0005⟩!⟨U+0007⟩⟨U+0019⟩⟨U+0019⟩ ⟦片段边界⟧ "⟨U+0004⟩⟨U+000E⟩⟨U+0010⟩⟨U+0005⟩⟨U+0017⟩⟨U+0005⟩<⟨U+0005⟩⟨U+0006⟩⟨U+0007⟩⟨U+0008⟩ ⟨U+000E⟩⟨U+0007⟩⟨U+0008⟩ ⟦片段边界⟧ ⟨U+0004⟩%⟨U+0010⟩⟨U+000E⟩⟨U+0005⟩A⟨U+0005⟩<⟨U+0005⟩ ⟨U+0007⟩ ⟨U+000E⟩⟨U+0004⟩⟨U+0010⟩ ⟦片段边界⟧ ⟨U+000E⟩&⟨U+0005⟩⟨U+0004⟩ ⟦片段边…
- **结尾 · `page=687;block=15 → page=687;block=23`**：028 9023 8451 Fax 028 9023 5401 ⟦片段边界⟧ 71 Lothian Road, Edinburgh EH3 9AZ ⟦片段边界⟧ 0870 606 5566 Fax 0870 606 5588 ⟦片段边界⟧ The Parliamentary Bookshop ⟦片段边界⟧ 12 Bridge Street, Parliament Square, ⟦片段边界⟧ London SW1A 2JX ⟦片段边界⟧ TSO@Blackwell and other Accredited Agents 9 780101 735124 …

审阅：687 页文件提取出 149,429 片段，95.1% 不超过 20 字符，是全库最大片段来源。 页码单调，但版面被拆成大量极短块；局部顺序不足以代表自然段顺序。 印刷文件名、页码、标点和重复短词大量独立成片，重复片段率很高。 **建议：必须调整切分；当前层仅作可追溯原始提取，不直接作为语言模型/向量文本。**

### 8. Humber river basin district RBMP 2009 Annex B: Water body status objectives（长报告/表格型 PDF）

来源：[https://assets.publishing.service.gov.uk/media/5a7c0202e5274a7202e18f75/gene0910bsqt-e-e.pdf](https://assets.publishing.service.gov.uk/media/5a7c0202e5274a7202e18f75/gene0910bsqt-e-e.pdf)；对象 `cnt_0cda1f6ed4af80345372`；97,409 片段，极短片段 38.71%。

- **开头 · `page=1;block=1 → page=2;block=10`**：River Basin Management Plan ⟦片段边界⟧ Humber River Basin District ⟦片段边界⟧ Annex B: Water body status ⟦片段边界⟧ objectives ⟦片段边界⟧ Annex B Erratum sheet ⟦片段边界⟧ The following changes were made to this document in January 2011. ⟦片段边界⟧ Changes ⟦片段边界⟧ WBID Catchment Element Decision code ⟦片段…
- **中部 · `page=914;block=19 → page=914;block=29`**：Heavily Modified ⟦片段边界⟧ Drinking Water, Water Storage - non-specific ⟦片段边界⟧ SK 26249 95987 ⟦片段边界⟧ Good Ecological Potential by 2027 ⟦片段边界⟧ No ⟦片段边界⟧ Disproportionately expensive, Technically infeasible ⟦片段边界⟧ Drinking Water Protected Area, Nitrates Directive ⟦片段边界⟧ Broomhead Res…
- **结尾 · `page=1936;block=34 → page=1936;block=47`**：Ecological Potential Assessment ⟦片段边界⟧ Element Current status Predicted Status by ⟦片段边界⟧ 2015 ⟦片段边界⟧ Justification for not achieving ⟦片段边界⟧ good status by 2015 ⟦片段边界⟧ Mitigation Measures ⟦片段边界⟧ Assessment ⟦片段边界⟧ Moderate Moderate Technically infeasible (M1b, M1g) ⟦片段边界⟧ Chemical…

审阅：1,936 页附件以水体状态表为主，97,409 个片段中大量为代码、状态值和页眉。 页码单调，但跨列表格按视觉布局拆成线性块，列与行关系不稳定。 重复页眉、表头和分类值导致 91.4% 片段文本重复。 **建议：保留作结构化/表格证据；在版面表格重建前暂不纳入通用语言处理。**

### 9. RDPE programme document 2014 to 2020（长报告）

来源：[https://assets.publishing.service.gov.uk/media/63369ebee90e0772e400e682/United_Kingdom_-_Rural_Development_Programme_England.pdf](https://assets.publishing.service.gov.uk/media/63369ebee90e0772e400e682/United_Kingdom_-_Rural_Development_Programme_England.pdf)；对象 `cnt_fef7848a752411b6c923`；24,704 片段，极短片段 26.15%。

- **开头 · `page=1;block=1 → page=1;block=13`**：1 ⟦片段边界⟧ United Kingdom - Rural Development ⟦片段边界⟧ Programme (Regional) - England ⟦片段边界⟧ CCI 2014UK06RDRP001 ⟦片段边界⟧ Programme type Rural Development Programme ⟦片段边界⟧ Country United Kingdom ⟦片段边界⟧ Region England ⟦片段边界⟧ Programming period 2014 - 2020 ⟦片段边界⟧ Managing authority Depa…
- **中部 · `page=355;block=12 → page=355;block=14`**：priorities will be identified and applications scored to secure the best quality “offers”. Coordination would ⟦片段边界⟧ not be obligatory. Rather, high quality individual applications addressing local priorities will characterise ⟦片段边界⟧ these agreements. The initial objectives for …
- **结尾 · `page=754;block=51 → page=756;block=1`**：8_2 M11 ⟦片段边界⟧ Annex - ⟦片段边界⟧ Verification ⟦片段边界⟧ of double ⟦片段边界⟧ funding calcs ⟦片段边界⟧ - CS Organic ⟦片段边界⟧ 30- ⟦片段边界⟧ 05- ⟦片段边界⟧ 2022 ⟦片段边界⟧ n005if54 ⟦片段边界⟧ Agri-environment payment ⟦片段边界⟧ rate review verification ⟦片段边界⟧ 18 Ex-ante assessment of ⟦片段边界⟧ verifiability, controllab…

审阅：754 页 programme document 有可读段落，也有大量表格/编号记录。 页码与块号单调；正文、表格和修订记录混在同一片段流。 26.1% 为极短片段，重复片段率 40.2%；末端主要是修订/标识记录。 **建议：按页型/章节分流：叙述性章节可重组后使用，表格和修订清单保留但分开处理。**

### 10. Long-chain PFCAs – environmental concentrations database（CSV 表格）

来源：[https://assets.publishing.service.gov.uk/media/6267f2738fa8f523b7221bd0/Environmental_Concentrations_Database.csv](https://assets.publishing.service.gov.uk/media/6267f2738fa8f523b7221bd0/Environmental_Concentrations_Database.csv)；对象 `cnt_b74985815043b7817ded`；10,657 片段，极短片段 0.00%。

- **开头 · `row=1`**：Substance Acronym \| Chemical Name in Article \| Standardized Chemical Name \| Chain Length \| Sampling Location Type \| Sampling Location \| Sampling Location \| Country \| Sampling Year \| Compartment \| Tissue \| Species \| Common Name \| Mean \| Standard Deviation \| Median …
- **中部 · `row=5329 → row=5330`**：PFDoDA \| perfluorododecanoic acid \| Perfluorododecanoic acid \| C12 PFCA \| Land \| Rot \| Antwerp \| Belgium \| 2016 \| bird \| plasma \| Parus major Linnaeus \| great tits \| <1.8 \| NR \| \| <1.8 \| 7.74 \| NR \| pg/mL \| NA \| NR \| 1.8 \| NR \| NR \| NR \| NR \| Lopez-Ant…
- **结尾 · `row=10656 → row=10657`**：PFUnDA \| PFUnDA \| Perfluorooundecanoic acid \| C11 PFCA \| Lake \| Lake Vättern \| Mariestadssjön \| Sweden \| 2017 \| surface water \| NA \| NA \| NA \| <0.02-0.03 \| NR \| \| NR \| NR \| NR \| ng/L \| NR \| NR \| NR \| NR \| NR \| NR \| NR \| Kärrman et al. 2019 \| ⟦片段边界⟧ PF…

审阅：10,657 行环境浓度数据库完整进入片段层，是结构化数据而非连续正文。 CSV 行序与列序保留；每行被压成一个文本片段。 没有导航噪声，但“ | ”拼接不等于语义句子，空值/单位/列名需要按表结构解释。 **建议：保留并用于表格分析；暂不作为通用语言文本或段落向量输入。**

### 11. GGCs: bodies in scope（CSV 表格）

来源：[https://assets.publishing.service.gov.uk/media/67a9ec93acab8c9492a461ea/GGCs-bodies-in-scope.csv](https://assets.publishing.service.gov.uk/media/67a9ec93acab8c9492a461ea/GGCs-bodies-in-scope.csv)；对象 `cnt_fae9ae23a0b089359400`；221 片段，极短片段 0.00%。

- **开头 · `row=1 → row=5`**：Parent Department \| Body \| Classification ⟦片段边界⟧ Cabinet Office (CO) \| Cabinet Office (CO) Core \| Government Department ⟦片段边界⟧ Cabinet Office (CO) \| Commission for Equality and Human Rights \| Non-Departmental Public Body (NDPB) ⟦片段边界⟧ Cabinet Office (CO) \| Crown Commercia…
- **中部 · `row=111 → row=114`**：Department for Transport (DfT) \| Network Rail \| Non-Departmental Public Body (NDPB) ⟦片段边界⟧ Department for Transport (DfT) \| Northern Lighthouse Board (Commissioners of Northern Lighthouses) \| Non-Departmental Public Body (NDPB) ⟦片段边界⟧ Department for Transport (DfT) \| Office…
- **结尾 · `row=218 → row=221`**：Ministry of Justice (MOJ) \| Youth Justice Board for England and Wales \| Non-Departmental Public Body (NDPB) ⟦片段边界⟧ National Crime Agency (NCA) \| National Crime Agency (NCA) Core \| Government Department ⟦片段边界⟧ Office for National Statistics (ONS) \| Office for National Statis…

审阅：三列机构名录提取稳定，当前片段正好对应一条表格记录。 221 行的行序、列序清楚。 无明显网页噪声；风险在于把分类表误当自然语言段落。 **建议：直接用于结构化筛选/关联；通用语言处理应排除或使用表格专用表示。**

### 12. Chlorpyrifos draft risk management evaluation – additional information table （ODS 表格）

来源：[https://assets.publishing.service.gov.uk/media/65e9fbe75b65240011f21bf7/Chlorpyrifos_RME_Additional_information_Tables_26_Feb_2024.ods](https://assets.publishing.service.gov.uk/media/65e9fbe75b65240011f21bf7/Chlorpyrifos_RME_Additional_information_Tables_26_Feb_2024.ods)；对象 `cnt_494d2a46237874ced427`；1,726 片段，极短片段 16.11%。

- **开头 · `row=1 → row=4`**：Table 1. Countries in which chlorpyrifos is completely banned ⟦片段边界⟧ Country \| Agriculture (food) \| Agriculture (non-food) \| Veterinary \| Residential, industrial and public health uses \| Year banned \| Source \| MRLs? \| Legal Document/Regulatory Authority \| Notes ⟦片段边界⟧ A…
- **中部 · `row=870 → row=874`**：Agriculture (food) \| Vegetable \| n.d. \| n.d. \| Indoxacarb \| CRC, Malaysia ⟦片段边界⟧ Agriculture (food) \| Vegetable \| n.d. \| n.d. \| Lufenuron \| CRC, Malaysia ⟦片段边界⟧ Agriculture (food) \| Vegetable \| n.d. \| n.d. \| Malathion \| CRC, Malaysia ⟦片段边界⟧ Agriculture (food) \| V…
- **结尾 · `row=1737 → row=1748`**：Reddy et al 2009 (PAN, Annex F) ⟦片段边界⟧ Thailand, Annex F ⟦片段边界⟧ Thailand, Annex F submission ⟦片段边界⟧ TNAU Agritech Portal, 2023 (PAN, Annex F) ⟦片段边界⟧ UK, Annex F ⟦片段边界⟧ UNEP/FAO/RC/CRC.19/13 ⟦片段边界⟧ UNEP/FAO/RC/CRC.19/8 ⟦片段边界⟧ UNEP/POPS/POPRC.19/4 ⟦片段边界⟧ Watts and Williams 2015 (P…

审阅：1,726 个非空行被抽成文本，行内非空单元格按顺序拼接。 行序可见，但 locator 只有全局 row，未保留工作表名；跨表边界不可直接判断。 空单元格被过滤，可能造成列位置漂移；部分行只有短标签。 **建议：保留原 ODS 并改进表格定位（sheet/cell/列名）后再用于结构化处理；暂不作语言正文。**

完整样例窗口及原始路径见 [04_readable_samples.csv](04_readable_samples.csv)。

## 4. 下载成功与正文价值不是同一件事

以下判断只使用现有文本量、对象关系和精确片段重合，不使用向量或模型。`附件为主`规则为附件字符数至少 1,000 且至少为网页的 3 倍；这是审阅优先级启发式，不是语义完整性证明。

| 正文位置判断 | 发布记录数 | 含义 |
|---|---:|---|
| 附件为主 | 984 | 网页通常是摘要、说明或附件清单；正文主要在附件。 |
| 网页为主 | 3 | 网页文本明显多于附件，或没有实质附件文本。 |
| 两者均有实质内容 | 20 | 网页与附件都需保留，不能只选其一。 |
| 网页短文本/附件不可用 | 13 | 只有短网页文本，附件不存在、未下载或未提取。 |

网页—附件重复采用保守的精确匹配：只比较长度 ≥40 的标准化片段，并以较小一侧的实质字符数为分母。共标出 **43 个可能重合**，其中 **1 个近完整精确重复**；这只能发现精确重合，不能排除改写、不同切分或版面差异造成的重复。

| 重复候选示例 | 较小一侧重合比例 | 精确共享片段 |
|---|---:|---:|
| Memorandum of understanding: enforcing wildlife crime | 100.00% | 7 |
| Water industry national environment programme (WINEP) roadmap | 76.67% | 3 |
| Establishing the Best Available Techniques for the UK (UK BAT) | 68.26% | 6 |
| Urban waste water treatment: updated sensitive areas maps 2023 | 63.61% | 25 |
| 'Not for EU’ labelling for retail products across Great Britain: Policy update | 51.89% | 2 |

未形成可用正文的对象如下：

- 下载状态 `access_denied` / 提取状态 `not_attempted_download_failed`：8 个对象。
- 下载状态 `error_page` / 提取状态 `error_page`：1 个对象。
- 下载状态 `success` / 提取状态 `extraction_failed`：2 个对象。
- 下载状态 `success` / 提取状态 `needs_ocr`：14 个对象。
- 下载状态 `success` / 提取状态 `unsupported_format`：5 个对象。

逐发布记录的正文位置、附件成功数和重复候选见 [05_document_body_value.csv](05_document_body_value.csv)。

## 5. 后续建议（本轮不执行）

### 可直接用于后续文本处理

- HTML/ODT 的段落级正文，保留标题和 locator；进入分析前排除固定 GOV.UK 服务性片段。
- 网页为主的 3 个发布记录，以及网页/附件均有实质内容的 20 个记录，可按对象关系保留两侧来源。
- 普通、叙述性 PDF 中短片段比例低且重复率低的对象，可把当前层作为证据源；下游按页合并相邻行后再生成分析文本。

### 需要调整切分

- PDF：从逐换行片段改为页内自然段/版面块，并保留原 `page/block` 到新片段的映射；优先处理前 20 个高片段对象。
- 长法案和长报告：分离正文、表格、目录、页眉页脚、修订记录；对高重复页眉/表头做标记而非删除原始层。
- 网页：给固定服务性标题增加 `boilerplate` 标记，避免其进入词频、主题或向量输入。
- CSV/ODS：保留列名、工作表名、单元格地址和空值位置；不要只用拼接后的行文本替代表结构。

### 应保留但暂不纳入通用语言处理

- CSV、ODS 及明显表格型 PDF：进入结构化/表格专用流程，而不是自然语言段落流程。
- 14 个 `needs_ocr` 对象、5 个不支持格式对象、2 个提取失败对象，以及 9 个下载失败/错误页对象。
- 《Draft Marine Bill》及河流流域 Annex B 等高碎片、高重复对象，在重切前只保留作证据，不进入向量化或模型分析。

## 配套文件与完整性

- [01_format_summary.csv](01_format_summary.csv)：四类汇总及实际格式明细。
- [02_top20_objects.csv](02_top20_objects.csv)：片段数最高 20 个对象。
- [03_segment_length_distribution.csv](03_segment_length_distribution.csv)：分位数、极短片段和记录模型。
- [04_readable_samples.csv](04_readable_samples.csv)：12 个对象的来源、位置、当前提取窗口和审阅判断。
- [05_document_body_value.csv](05_document_body_value.csv)：1,020 个发布记录的网页/附件正文位置与精确重合候选。

输入数据库 SHA-256（读取前）：`baa191627921700bb579e55c34b7c8ed9c1739eb610b11448de81918305cc7b0`；原始文件数（读取前）：`3017`。
读取后数据库 SHA-256：`baa191627921700bb579e55c34b7c8ed9c1739eb610b11448de81918305cc7b0`；原始文件数：`3017`。两项与读取前一致。
