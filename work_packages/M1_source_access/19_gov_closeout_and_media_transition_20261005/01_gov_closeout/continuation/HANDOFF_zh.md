# 政府合并续跑终态与最终输入

本轮已按协调者新release执行一次合并续跑并完成新增批次检查。B及AU均达到持久停止条件，已冻结真实可用输入供独立分布分析；政府全队列并未完成。固定发表区间仍为1988-01-01–2026-09-21，九月部分覆盖。原403/406状态、冻结队列、旧检查/报告、旧release和本轮代码均保持原样。没有再次改代码、再发一个头/路线请求或扩大sibling范围。

## 实际执行与全目标记账

协调者release为`control/GOV_CONTINUATION_RELEASE.json`，SHA256 `56acd7de09d6116cc332ca82637158dcfc8e6f53a0dca74a1cac9e9c5e1442b9`；接受的代码SHA256 `73e5bd472a98c690971638c88237ab73d30761143f587eab9e68090dfae4f47c`。原生进程94311正常结束（exit0），2026-10-04T19:42:39.005605 UTC完成本次源请求。exit0代表受控终态，不代表原件齐全。

| 单位 | 上轮/本轮事实 | 最终状态 |
|---|---|---|
| 2015元数据Work总体 | 1,009Work；979选定Item目标，30无链接Work | 分母不变 |
| 旧20保存Item | 9,020,646 bytes，原135页检查保留 | 执行启动为安全复用复核hash/签名，未下载，未重复文本/视觉审核 |
| 本轮B | 28次请求，27个新PDF成功，下一项406 | 新raw13,210,928 bytes；不重试 |
| 最终979目标 | 20复用+27新增+1当前失败+931未尝试 | 47个Work身份各有一个候选Item，完整Work数量未建立 |
| 本轮AU | 首条landing一次请求，90秒ReadTimeout | 第二条landing与两份候选PDF均未尝试；新增原件/raw0 |
| 政府A+B累计raw | 22,231,574 bytes，partial0 | 约21.20MiB，不计页面/文本/父记录为新增raw原件 |

旧失败Item`3df58e03-97cd-11e4-b8a5-01aa75ed71a1.0006.01/DOC_1`在**唯一一次**`Accept:*/*`纠正请求中返回200，并保存PDF。其旧406 checkpoint没有删除或改写。本次可行性得到验证，单次先后对比仍不能证明旧406完全由Accept引起：资源/服务状态与请求时间也变化，未做受控因果比较。官方说明的支持与原候选解释保留在前一轮`TRANSPORT_DIAGNOSIS_zh.md`，不改成已证明根因。

之后按原次序及原`Accept:application/pdf`执行未请求目标。新停止项为Work `818145b6-97cd-11e4-b8a5-01aa75ed71a1`的ENG Expression`.0006`、PDF/A-1A Manifestation`.0006.01`、Item`.0006.01/DOC_1`，保存元数据日2015-01-09。相同精确URL返回406、XML类型、声明1000bytes；错误正文未保存，raw/partial0，无重定向。新B状态明确halted=true；没有为它再尝试通配Accept、格式专用头、Work URL或另一个Item。

`FINAL_B_STATUS_LEDGER.csv`有完整979行，保留原B状态、当前状态、sidecar、raw/hash及历史来源；`FINAL_B_REMAINING_TARGETS.csv`有932行（1失败+931未尝试）。`FINAL_B_MONTH_DISPOSITIONS.csv`有12月：2015-01的93Work/91目标中47个保存、1失败、43未尝试、2无链接；其余月份没有本轮新正文。不能把1月进展说成2015全年完成，更不能扩大到完整国际覆盖。

## AU和原五条请求的不同终态

两条AU原件计划由新release独立接受，受总4请求/54MiB对象预算约束。实际只请求了fugitive methane interim report官方landing：19:41:08.884107 UTC开始，19:42:39.001827 UTC发生90秒读取超时，未取得HTTP状态或正文。其候选PDF因为landing失败而未请求。Sustainable Ocean Plan landing及其候选PDF在AU持久停止后未尝试；它们的可访问性尚未检验。

`FINAL_A_DISPOSITIONS.csv`完整登记原五条parent：原Hansard首个403与另外两条未尝试保持旧证据；两条AU分别是本轮landing超时和未尝试。新增原件均为0。超时不是来源不存在，也不是已确认权限拒绝。原发行日、版本日期、作者、法律出版者、委托issuer仍未知；DCCEEW host及CMS2026-09-17/09-22不是这些字段的替代。未据09-22的CMS时间把Ocean Plan排出固定发表区间；原件日期未知就保留未知。无登录、付费、反爬挑战绕过或新路线探测。

## 一次新增27个Item的结构与来源验收

共享heavy-I/O锁下，只对这27个新PDF进行了单次changed-tranche检查：13,210,928bytes全部hash匹配、PDF签名通过，27项均可解析，257页均有非空文本层；27个首页已可视检查，其余页面没有全部可视阅读。raw字节及mtime未修改，未生成正式库正文/segment，不运行OCR、主题/情绪/恐惧模型。旧20个PDF未重复读取文本或视觉审核。本轮和旧20合计392页面，页面数不是独立文档数。

新增26项印刷日与CDM Work日相同。新增序号24 `2015/C33/05`（Ciliegia di Vignola amendment application）的CDM日2015-01-30、公报印刷日2015-01-31，保留同月日级冲突；加上旧信用评级名单冲突，共2项。原日期不改、日历分配不自动纠正。三个Strasbourg2015-01-13封面日期从已保存首文本/图像确认，补充了只识别Brussels的自动解析器限制，未重读raw或扩大检查。报告保留`AUTOMATED_CHANGED_ITEM_CHECK.json`与人工观察记录。

新增11个COM/JOIN文件中有提案、预算草案、报告及communication，16个为OJ通知/名单/通信等rendition；与旧20合计18个COM/JOIN文件、29个OJ rendition。冻结COM RDF类不是统一正文体裁，JOIN封面及多个机构/Member State通信按原证据保留。政府host或Commission再刊不能自动等同于所有原话作者/holder；没有主张真实性或情绪归属结论。

新增4个选定Manifestation有多Item（累计10个），新增3个首页含多个OJ通知编号（累计7个Item标记）。字节hash比较还发现两组跨Work的完全相同PDF：新增序号9与旧序号10、新增序号12与旧序号11，分别含OJ2015/C28/08–09与2015/C29/03–04的共享页面。详见`CROSS_WORK_IDENTICAL_ITEM_GROUPS.csv`。47个Item有45个不同SHA256；45不是完整或独立Work正文数。各Work/Item身份及raw全部保留，未删除/降采样。共享页面下的目标Work文本所有权及组件覆盖仍待核。

`CHANGED_ITEM_TEXT_SHAPE.csv`是新增27行，`ALL_SAVED_ITEM_TEXT_SHAPE.csv`合并47个Item的原检查与新检查，明确tranche。词数为whitespace token，字符为codepoint，包含封面、表头/脚注/同页通知；不是完整独立Work正文长度。所有行`parent_statistics_eligible=False`，组件/annex与历史版本等价性仍未建立。这是统计单位边界，不能当作源不合格、气候不相关或fear不存在的结论。source/CDM日期、Item印刷日、取得/版本/报告时点及路径分开。

## 最终冻结输入与使用范围

`FINAL_INPUT_MANIFEST.json`绑定协调者release/代码、旧输入包与停止状态、新requests/终态、27项局部验证、47Item清单及各源保存月表/hash。`FINAL_INPUT_READY.json`表示有界停止后可用输入ready，不是新HTTP或正式入库授权。原23个来源/体裁框架、各源历史检查点和UK有效月表继续使用；`FINAL_GOV_FRAME_REGISTER.csv`只对EU/AU这轮状态作明确overlay。其他来源没有新raw读取/采集、正式库查询或全库审核。

UK仍为248,319来源父身份，mirror/shared reply和区间/adapter限制保留；US仍为33,544选定元数据parent，旧18,590operational状态不升级成普遍原件验收；EU50,578Work/旧19,114Item版本和19,085extraction状态保持原snapshot，不加47到一个“完整Work”分子。AU821候选与重叠7原件分开，IE684,809是171分区问题指数，NZ536是2025当前answered问题显示记录。来源不同步、单位不同，不拼新的池化独立总量。历史465/465政府有文本月份未刷新。

本轮执行含已批准的逐请求targeted `repair_runs`只读门控；新增PDF检查和最终packaging没有新DB查询，正式库写入0。没有全集text scan、重建库、proposal修改、commit/push、语义排除或峰值气候/情绪归因，也没有读取/定位/探测封存审计代码、夹具或凭据。源码仍由独立协调者运行，政府分布/图形和合并建议归其工作线。

`FINAL_CURRENT_GAPS.csv`集中22行，含重叠/聚合数量，不能相加为独立错误总数。原有完整父长度和部门crosswalk缺口继续保留；原`BOUNDED_PARENT_EXPORT_REQUEST.json`的一次2015来源×日期可选存储字段导出建议可用，不以此阻止媒体推进。来源route不能直接改叫部门，Item长度也不能拼成完整父长度小提琴。

2GiB政府累计raw/partial cap与15GiB floor、原inflight/checkpoint/1GiBother reserves未改变。最终metadata预算复核通过，剩余raw cap2,125,252,074bytes；媒体128MiB仍计入既有other reserve，共享持久heavy-I/O锁且未删锁。两个新phase的halt及原停止均保留，本轮没有自动或新授权续跑。当前可用政府证据和真实缺口可以进入独立分析及媒体阶段，不要求逐国全覆盖或填满979。

四层证据保持区分：①日期/来源存在与有限可读Item证据；②气候/升温相关性与相似性未评估且不是当前门槛；③affect/risk/future-harm/responsibility未验证且不自动等于fear；④fear特异解释未进行，仍需要原段落与holder/target/horizon/quotation/negation证据。覆盖、计数和文本形状不建立三角色情绪流或因果影响。

本目录`RESULT.json`、完整账本、`FINAL_INPUT_READY.json`及`OUTPUT_RECEIPT.json`是本轮终态。`LOG_ENTRY.md`供协调者合并；未直接编辑共享PROJECT_LOG，未发跨聊天消息，未另开窗口或拆微任务。
