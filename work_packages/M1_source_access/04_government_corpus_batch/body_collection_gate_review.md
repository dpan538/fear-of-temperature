# 正文采集 gate review

## 当前结论

正文下载、附件保存、文本提取和正文分析继续暂停。这里的准确表述是：**UQ 路径对本政府机构文档语料是否适用尚未得到项目级正式确认；但项目已明确决定，在适用路径被记录前暂停 substantive use。** 不能写成“UQ 已确认本批次必须先获批”，也不能写成“公开网页当然无需伦理路径”。

## 1. 暂停依据与适用操作

- 项目决定：`proposal/thesis_proposal.md` 的 R7 要求在 UQ pathway unresolved 时暂停受影响使用；3.11 要求所有拟用 human-language sources 和派生数据库在 substantive use 前完成 documented ethics screening，并明确没有 clearance。`03_database_pilot/database_design.md` 继续把正文进入切段接口的前提设为可核验伦理路线与逐项权利条件。
- UQ 官方规则：当前 *Human Research Ethics Procedure* 第 8 条规定，涉及或关于人、人体组织或其数据的研究必须接受伦理审查或符合豁免；第 10 条规定相关研究只能在批准、ratification 或豁免条件成立后开始；第 15、17、18 条分别记录豁免、lower-risk 和 HREC 的 MyResearch 路径。
- 尚未核实：纯政府机构政策文本、不以个人为研究对象且不处理个人资料的本批次，是否属于上述“involving or about humans or their data”。proposal 本身也明确“不一定每份公开机构文件都需要 HREC review”。因此，暂停直接由项目 gate 支持；UQ Procedure 支持“若适用则必须先确定路径”，但尚未对本批次作出适用性决定。
- 当前暂停的具体操作：保存网页/PDF 原始字节、运行正文提取、创建真实 `text_segments`、对正文做 NLP/人工标注，以及向项目外发布正文或可逆衍生物。Search/Content API 元数据枚举、附件身份登记和覆盖审计属于当前已完成的 preparatory governance 工作。

官方依据：https://policies.uq.edu.au/document/view-current.php?id=346

## 2. 三类内容分别判断

| 内容 | 权利判断 | 伦理/研究路径判断 |
|---|---|---|
| GOV.UK 政府机构网页 | GOV.UK 一般 OGL 说明是起点；仍需看页面例外、标识和个人资料 | 需确认机构政策文本是否不属于 human research，或应走何种记录/豁免路径 |
| 政府报告附件 | 不因挂在 GOV.UK 页面就自动与 landing page 同一许可；核对附件 credit、版本和 OGL 标识 | 若仅机构文本，问题同上；若含访谈、案例或个人资料，需按实际内容升级判断 |
| 第三方附件、图片、地图或引述材料 | OGL 不自动覆盖第三方权利；需要权利人/数据 custodian 条件 | 个人资料、可识别引语、敏感群体或原始参与者材料需单独判断，不得由政府发布身份代替 |

GOV.UK/OGL 依据：https://www.gov.uk/help/terms-conditions 和 https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

## 3. 各操作仍缺什么

| 操作 | 已有依据 | 未决条件 |
|---|---|---|
| 下载并本地保存 | 公开接口列出 URL；一般 OGL 条款已记录 | UQ 适用性记录、存储/访问条件、附件级权利与个人资料例外 |
| 文本提取与切段 | 已有可恢复 CLI、版本和父文档结构 | 上述路径解除；3 文档 smoke 对照 landing page/附件及提取质量 |
| 研究分析 | schema 可保存 provenance 和缺失状态 | 明确是否不适用、豁免、lower-risk 或 HREC；批准/豁免范围须覆盖实际 NLP、引用和人工复核 |
| 公开发布 | 可发布代码、ID、URL 和本批次元数据治理材料 | 正文/附件逐件再发布权利、OGL attribution、第三方排除、伦理/隐私和可逆衍生物限制 |

## 4. 谁确认、问什么

- **UQ Research Ethics and Integrity**：确认适用路径；如需要，通过 MyResearch 记录豁免、lower-risk 或 HREC。明确询问：本研究仅收集和计算分析公开政府机构政策文件、无招募且不以个人为分析对象时，是否属于 human research；若不属于，应以何种书面方式记录；若附件含个人案例、部长引语或第三方研究，路径是否变化；原始下载与自动提取是否已属于必须等待的“commence”。
- **Dai Pan / 项目负责人**：确认实际研究问题、拟处理内容、引用、人工复核、存储和发布范围，作为向 UQ 提问及申请的准确 protocol；导师决定不能替代 UQ institutional determination。
- **GOV.UK/附件标注的权利人或数据 custodian**：只在条款或附件 credit 不清楚时确认具体复用、保存和公开发布权利。项目目前未联系任何人。

在得到可核验证据前，数据库保持 `ethics_status=pending`、`research_processing_status=pending`、`body_collection_status=blocked`；不自行批准或解除 gate。

