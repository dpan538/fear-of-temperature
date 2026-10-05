# 政府收尾：可用输入、已保存Item验收与一轮续跑提案

本窗口已完成输入所有者交付。可用输入已冻结，可进入协调者的独立分析；政府补采队列仍未完成。本轮没有新请求EU Item、Hansard或AU原件，没有正式库查询/写入，也没有执行独立审计脚本。固定发表区间1988-01-01–2026-09-21，2026年9月部分覆盖；报告时间及后续取得时间不延长端点。

## 当前实际数量

| 层次 | 当前事实 | 使用边界 |
|---|---|---|
| B冻结元数据 | 2015年1,009个Work，979个选定Item目标，30个无链接Work | 不是979份完整正文或新增父记录 |
| 上轮真实B HTTP | 21次：20成功候选PDF，1个406，958未尝试 | 上轮已停止；不宣称全队列完成 |
| 保存raw | 9,020,646 bytes，20个不同SHA256；partial0 | 本轮原字节全部复核一次，未修改或重下载 |
| 本轮PDF结构 | 20个PDF、135页，所有页有非空文本层；20个首页可视检查 | 不等于逐页阅读/视觉验收，也不等于完整Work |
| A原件 | 首个Hansard403，另外4项未尝试，新增原件0 | 两条AU未知日期/原件检查集中准备；Hansard停止保留 |
| 新续跑 | 0次 | 代码及16项离线夹具通过；需要新协调者release |

`CHANGED_ITEM_TEXT_SHAPE.csv`保留原Work/Expression/Manifestation/Item、元数据日期、取得时间、ETag/Last-Modified、raw路径/hash和页面/文本长度。字符为Python字符串codepoints；词长为whitespace token数，包含封面、表头和脚注，未经正文去噪。这20行是Item版本的形状，不能作为完整父记录长度。`PDF_PAGE_SHAPE.csv`的135行是页面单位，不能变成135个文档父记录。

## 这20项的实证限制

19项印刷发表日与保存的CDM Work日相符；第17项信用评级机构名单CDM为2015-01-30、公报印刷日为2015-01-31，两天同在2015-01。日期冲突单独登记，不改旧日期或自动纠正。第15项提案编号`COM(2014)750`，封面日期2015-01-09；编号年份不是发表日。

实际首页有7个COM提案，13个公报通知、名单、通信或勘误；冻结`COM/act_preparatory/ENG`类不等于一种均匀的提案体裁。至少4个Item首页含两条通知编号（序号3、7、10、11），需确定目标Work与页面共享的文本边界。6个Work的选定Manifestation在保存关系中还有其他Item；一个已保存Item也不能证明其他14个Work完整。组件、annex和历史版本等价性均未建立。全部20行的`parent_statistics_eligible=False`，这是长度/完整Work统计的边界，不是语义排除。

来源为官方CELLAR归档再现，印刷机构/通信者另列。Member State通知、ESMA名单与Commission再刊关系保留，不能把当前托管者自动等同于每条原始话语的作者。官方路由、hash和首页印刷证据支持各自有限验证，不证明每个主张真实。后来的HTTP Last-Modified/ETag不证明2015年原始措辞，历史版本仍标unknown。

## 一次合并续跑提案

406的确切根因未证实。保存的错误正文为空；同轮13个PDF/A-1A成功反驳“该格式普遍需要换头”的说法。官方direct Item说明和旧接口规范支持URI足以确定语言/类型时使用`Accept: */*`，因此可以提出对**同一失败Item的一次**纠正后验证。证据、推断与服务限制区分见[诊断](TRANSPORT_DIAGNOSIS_zh.md)。不换Work/Expression/Manifestation/Item，不调次序、不抓sibling、不使用Work协商替代，不产生第二种头或第二路线尝试。

`transport_continuation.py`保留V3，默认只输出离线状态。新release必须由协调者在`19.../control/GOV_CONTINUATION_RELEASE.json`签发，具体绑定见`CONTINUATION_RELEASE_TEMPLATE.json`（ready=false，不能作为授权）。`TRANSPORT_PATCH_READY.json`只表示离线候选可审查。

释放后的B流程：复核复用已保存20项 → 一个同一Item的纠正后验证 → 仅在它成功后继续原958项未请求队列。只有失败Item改为通配Accept，后958项保留V3头。任何非200、重定向、访问/Retry-After、签名/长度/编码问题或预算停止均写新持久状态；新请求/partial不覆盖旧406证据或已有raw，不自动重启。修正成功仍是候选字节，需要单次新增批次身份/日期/组件验收。

两条AU属于从未请求的独立原件检查。`AU_ORIGINAL_CHECK_PLAN.csv`绑定最终两个现有parent、官方landing及保存的候选PDF链接；最多每项一landing加一已确认的同名PDF，总4请求、54 MiB对象上限，仍计入政府A+B2 GiB。若landing未确认精确链接，就不请求PDF。403/编码/超cap/重定向等不绕过。印刷imprint/发表日、作者、法律出版者、委托issuer和host分开核实。CMS2026-09-17与09-22既不证明原发表日，也不决定截止日资格。Hansard原403及另外两条未尝试状态不被AU阶段覆盖。

预算保持原2 GiB累计raw/partial cap、15 GiB floor及100,000,000 inflight、67,108,864 checkpoint、1 GiB other reserves。冻结时free约19.17 GiB，扣原剩余raw和reserve后约16.02 GiB，仍通过；执行须逐对象/流chunk重新预检。媒体128 MiB在other reserve内，共用持久heavy-I/O锁；不删除锁文件。正式写入仍须单writer另行验收，此代码不写库。

协调者若决定执行，先审查候选代码/输入、复制并正式签署新release，再使用其真实SHA256执行：

```text
.venv/bin/python work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/01_gov_closeout/transport_continuation.py --execute --release-sha256 <coordinator-signed-release-sha256>
```

本窗口没有自签或改写旧`REPAIR_READY`、`EU_STAGING_RELEASE`。没有auto-review拒绝；当前停止来自项目的持久HTTP和协调者release边界。

## 交给独立分析的冻结输入

`GOV_FRAME_REGISTER.csv`有23个来源/体裁框架，分开元数据存在、可读原文、尚未验证的正文、日期精度、来源身份和访问限制。`inputs/`包含UK修复后有效月表、US/EU/AU历史来源月表、EU旧阶段月表、IE问题指数与NZ2025问题指数。`INPUT_MANIFEST.json`记录这些证据、旧请求/停止状态和本轮20raw的hash；数据库只登记stat检查点，不重新扫描或hash整个库。

| 来源框架 | 可复用事实 | 不得合并/升级的单位 |
|---|---|---|
| UK有效层 | 248,319来源父记录；248,268可单月分配；124区间中51跨月保留；11来源×体裁行 | mirrors/共享回复不保证跨路由独立；UK09副本不加样本；119日历惯例差、37adapter限制保留 |
| US EPA/DOE | 33,544元数据parent；18,590旧operational extraction/status数量 | EPA/DOE关联重复与原件版本分开；1988–1993指数token/page/issue不作Work分母 |
| EU固定类 | 50,578Work；19,114旧Item版本、19,085旧extraction状态 | 新20Item未入库，不追加到“完整可读Work”数；465个元数据月不等于465完整正文月 |
| AU | 821目录候选；819主表缺日；7原件为重叠子集（5日/月、2仅年） | 当前host/CMS不作原日期/作者；不加7到821 |
| IE | 171分区合计684,809问题指数；152正值、19查询零 | 问题不等于独立ministerial answer；2012-09选定357条含280个不同完整回复字符串 |
| NZ | 2025年12个正值月、536个当前answered问题显示记录 | question-asked日不等于answer-received日；旧portfolio过滤保持历史scope |

这些来源检查点不同步，不出新的池化独立总量。历史政府465/465有文本月份只保留其原检查点意义，没有重新计算。本窗口没有计算entropy/HHI、优化队列或读取/探测封存评估代码、夹具、密钥。独立审计的脚本、图形和合并结论仍由协调者完成。

当前只有聚合月表和20个Item形状，缺合格逐父完整文本长度及部门crosswalk。`BOUNDED_PARENT_EXPORT_REQUEST.json`建议可选的**一次2015来源×日期导出**，使用已接受存储字段，不重新读全库原文或OCR；未知长度/部门保留unknown，来源route不改叫部门。输入不足时不拼旧分位数小提琴，也不因此阻止媒体阶段。

`CURRENT_GAPS.csv`集中登记21行事实缺口及边界；聚合与重叠行不可相加作为独立缺口总数。原165 unresolved units/318 issue instances和37adapter限制保留历史scope，不用新增注释追改其冻结数。本轮提出**一次协调者合并决定**：验收这份可用输入，并选择签发同一Item/AU有界续跑，或保留真实传输/访问缺口后推进独立分析和媒体。

## 四层证据

1. 日期/来源存在与可读文本：本轮20Item hash/结构及首页印刷证据；其他来源使用各自保存检查点，命名局限不清零。
2. 气候/升温相关性与相似性：本轮未评估，非清洗/来源保留门槛。
3. affect/risk/future-harm/responsibility：未验证，不自动等于fear。
4. fear特异解释：未进行；仍需原段落与speaker/holder、target、time horizon、quote/negation证据。

不执行语义筛除或恐惧标签，不预归因峰值，不改proposal，不写共享PROJECT_LOG。可摘录的进展在`LOG_ENTRY.md`；结构验收与输出hash见`DELIVERY_CHECK.json`、`OUTPUT_RECEIPT.json`。
