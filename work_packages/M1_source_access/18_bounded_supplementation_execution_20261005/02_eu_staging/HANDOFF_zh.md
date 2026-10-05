# EU2015 单轮暂存终态交接

**状态：stopped_partial。** 协调者签发 release 后，仅启动一次验收版 V3 下载器；第 21 项 HTTP 406 后停止，未重试、改路由、换 sibling 或自动续跑。命令于 **2026-10-05 02:38:18（Asia/Shanghai）** 终结，退出码 0 表示停止结果已保存，不表示全部目标完成。

| 实际结果 | 数量 |
|---|---:|
| 冻结 selected Work/Item 目标 | 979 |
| EU HTTP 请求 / 尝试 Item | 21 / 21 |
| 新取得候选 Item | 20 |
| 核对复用 | 0 |
| 失败 | 1 |
| 停止后未尝试 | 958 |
| 尚未取得目标，含失败项 | 959 |
| 保存 raw | 9,020,646 bytes（约 8.60 MiB） |
| 保留 partial | 0 bytes |

**当前全表为 B_STATUS_LEDGER.csv。** B_REMAINING_TARGETS.csv 保存 959 项具体失败/未尝试原因，不是自动重试队列。LOCAL_PREPARATION.json、INPUT_RECEIPT.json 和 B_TARGET_STATUS.csv 保留为下载前历史；原报告另存为 *.local_preparation.*。本轮新输入收据为 EXECUTION_INPUT_RECEIPT.json，stdout、preflight/result、21 个 requests sidecar 和 raw 均保留。

失败 Work 为 http://publications.europa.eu/resource/cellar/3df58e03-97cd-11e4-b8a5-01aa75ed71a1，冻结 Item 为 .0006.01/DOC_1，元数据日期 2015-01-09、格式 pdfa1a。该原 HTTPS Item route 实际返回 HTTP 406；sidecar 保留请求时间、最终 URL 与 XML 响应头，没有候选正文或 partial。PHASE_HTTP_STATE.json 持久停止。本次只证明该路线失败，其余 958 项没有被验证为不可获取。A 原 403、四项停止后未尝试及 A sidecar/state 未变，未再访问 A。

使用版本 bounded_staging_v3_20261005，代码 SHA256 f6f2bda93e9745c56ff9fd438be8071af2b40ee65b5f5b625d30f2d1c5e28bb2；冻结 manifest SHA256 af3fa2aa5c9cd6b1e97ad8b27fba17769be2c4916b3ef3dc4a6ab87fb772a4f7，执行后均未改变。已授权命令通过正常 require_escalated 网络机制运行；没有本地权限拒绝，也未把本地网络拒绝误报为源站失败。使用已验收的全局锁、单请求、至少两秒间隔、逐对象/stream 空间与 cap 检查和首次失败停止；32 项无网络夹具由前窗口/协调者验收，本窗口未重复测试或编辑下载器。

跨 A+B 的 2 GiB new-raw cap 含 partial；A raw/partial 均 0，本轮用 9,020,646 bytes，剩余 **2,138,463,002 bytes**。15 GiB floor 与原 reserve 保留，本轮因 HTTP 406 停止，未触及 cap 或空间下限。终态测量见 RESULT.json。

STAGING_INGESTION_HANDOFF.csv **仅含 20 项实际候选字节**，连接原 Work/Expression/Manifestation/Item、source/jurisdiction/genre/date evidence、raw SHA/bytes、retrieval/version headers、技术状态及 rights 边界。下载器已计算原字节 SHA 并验证 PDF 签名；本地交接核对 sidecar 身份、哈希收据与文件尺寸，不重复 raw rehash。17 项终态交接检查通过。20 项均在元数据 2015-01；其他月份仍只有既有目录/关系证据，不能称已取得完整 2015 年正文。

保留 **1,009 已枚举 Works、30 no-link outcomes**（B_NO_LINK_WORKS.csv），没有新建 parent。总体 973 个多替代 Item Work、253 个 selected PDF Manifestation 内多 Item Work 的限制仍有效；本轮 20 项中有 **6 个**属于后者。关系不能证明所有 sibling 都是附件，单 Item 也不证明完整。未增加 alternate/sibling/annex 队列。

候选 selected-Item 字节、可读性、原件身份/日期、required component coverage、complete Work 分开：**后四项本轮均未验证**，没有 text extraction 或正式入库。保留 publication metadata 与本次 retrieval、ETag/Last-Modified；HTTP 版本时间不是 2015 原文等同的证明。逐文档/第三方权利边界仍待核对，不赋予附件统一许可。

EXECUTION_RESULT.json 的 downloads_started=false 携带自 preflight，与实际 attempted_items=21、21 个 sidecar 和 HTTP state 不符。原运行收据未修改；新 RESULT.json 按证据记 downloads_started=true，RUNNER_REPORTING_NOTES.json 保存此报告字段问题。退出码及该字段均不能替代实际终态台账。

**下一步：**协调者/单一 writer 对这 20 项安排后续串行可读性、身份、出版日期及组件验收，再决定集成；本窗口不提取或入库。406 和剩余 959 项保持停止，无自动恢复或替代队列。原 LOCAL_PREPARATION、共享 PROJECT_LOG、repair/EU release、旧冻结报告和 proposal 未改；无语义/气候/情绪/恐惧过滤、全库扫描/rebuild/rehash、commit/push，未接触封存审计代码或凭据。验收版 runner 只读核对 active repair run，不等同全库审计，本窗口不虚称数据库读取为零。

固定出版区间 **1988-01-01–2026-09-21**，9 月不完整；tranche 仍仅 2015 年。四层证据：1）20 项候选字节和哈希、日期来自既有元数据，可读完整原文待验；2）气候相关性/相似度未评估；3）情感/风险/未来伤害/责任关联未评估；4）恐惧解释未评估。没有新 465/465 readable-text 覆盖、情绪时间序列或因果结论。
