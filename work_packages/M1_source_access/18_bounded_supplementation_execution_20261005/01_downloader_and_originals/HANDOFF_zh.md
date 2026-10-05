# Task 3 有界原件与下载器交接（2026-10-05）

下载器 V3 的 32 项阻断网络测试通过，包含原 24 项及阶段分离反例。本窗口 A 已按停止规则结束：首条 Hansard canonical HTML 在 2026-10-04T18:19:15Z 返回 403；其余四条明确记为因全局停止未尝试。它们的可获取性没有被验证，不能改称“不可取得”。没有取得新原件或复用原件，新增 raw 和保留 partial 都为 0；共同 raw 预算剩余 2,147,483,648 字节。

## 已冻结的执行证据

真实 A 请求使用 **bounded_staging_v2_20261005**，代码 SHA256 `86f5055124a482c74350d10db5e7046de6754bd62e5a279b4de6ae56fda6f2f8`。请求前的 ready 和无网络测试已分别保存为 `DOWNLOADER_READY.v2.json`、`OFFLINE_TEST_RESULTS.v2.json`，源码与补丁为 `stage_frozen_items.v2.py`、`downloader.before_after.v2.patch`；`A_EXECUTION_VERSION.json` 绑定它们及真实五项 ledger/accounting。A 的失败 sidecar、时间、`SHARED_HTTP_STATE.json` 和终态台账未因 V3 修改。

当前 V3 SHA256 为 `f6f2bda93e9745c56ff9fd438be8071af2b40ee65b5f5b625d30f2d1c5e28bb2`。它保留 A 的持久停止，只允许协调者明确接受这一次 Hansard 403 后，为独立 B 来源首次放行。V3 修复和测试期间没有新 HTTP；本窗口始终没有 EU HTTP、正式数据库写入或提取。

## 协调者的 B 放行条件

`EU_RELEASE_REQUIREMENTS.json` 是**所需模式和当前精确绑定值**，不是放行文件。协调者确认 A 停止与 V3 后，才可在自己的 `control/EU_STAGING_RELEASE.json` 写入：

- `ready=true`；`status=coordinator_accepted_downloader_and_A_released_B`；`issuer=coordinator`。
- `expected_bindings` 中全部字段：V3 版本/代码哈希、当前 ready 哈希、repair marker 哈希、固定区间、active run、post checkpoint、最终 A 源 manifest、五项 ledger/accounting 哈希、冻结 B manifest 哈希。
- `a_http_state_sha256`、`a_http_stop_accepted=true`、完整 `a_http_stop_reason`。当前 A stop digest 为 `72e7686bd89df18659662c1793389cafc94b0edf3dee7fa866a9a51473b17f94`。
- `authorized_phase=B`；`authorized_b_hosts=["op.europa.eu","publications.europa.eu"]`，顺序也按模式保留。

签发前必须核对 A 没有活动 Retry-After/429 cooldown。本次 403 记录未含 cooldown；下载器每次 B 请求仍核对 A state 的精确 digest 和继承 cooldown。签发不会清除或改写 A 停止，更不允许重新访问失败 Hansard 路线。B 有自己的 `02_eu_staging/PHASE_HTTP_STATE.json`，其失败、403、429、流量/存储超限会持久停止整个 B；冷却到期也不会自动恢复失败批次。

全局 heavy-I/O/download 锁和 `GLOBAL_REQUEST_SPACING.json` 跨阶段保持单请求及至少两秒间隔；全局间隔也读取已经保存的 A 末次请求时间。2 GiB A+B raw cap 包含保留 partial，15 GiB floor 保留瞬时对象、检查点和其他活动预留。B 始终只允许冻结的 979 selected Items，保留 1,009 Works、30 no-link outcomes 及 Work/Expression/Manifestation/Item 关系；不会补下 sibling/alternate Items 或宣称 complete Work。

## 无网络预检与测试命令

在项目目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python work_packages/M1_source_access/18_bounded_supplementation_execution_20261005/01_downloader_and_originals/preflight_no_network.py
```

此命令阻断 socket connect/connect_ex、create_connection 和 HTTP Session.request；仅在锁内只读检查已提交 run 的一条记录、checkpoint、哈希和空间，写本窗口 `NO_NETWORK_PREFLIGHT.json`。**不执行 B、不在 B 目录写执行文件**。当前本地输入和空间通过；B 因协调者 release 缺失仍被拒绝。Release 出现后仍需协调者向 EU 窗口发送执行指令。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python work_packages/M1_source_access/18_bounded_supplementation_execution_20261005/01_downloader_and_originals/test_downloader_offline.py
```

测试中所有 HTTP 为夹具；网络尝试为零。生产数据库只在夹具结束后执行单条只读 run 核验；夹具中的 run 查询被替换。测试覆盖无接受/错 digest/错 host/非冻结 Item 拒绝、签发后独立 B 与不变的 A halt、继承活动 cooldown、跨阶段间隔、B 403/429/超限持久停止，以及原 release、预算、partial、复用与签名/长度保护。

## 仍未解决的源问题

三项 Hansard 的原 HTTP400 API 失败和搜索证据保留，未重试；section ExtId 与 contribution anchor 分开登记。2007 项新 HTML 返回 403；2009/2010 项没有新访问。

两项 AU 原件没有新访问。既有明确 PDF 候选链接、目录和 CMS 时间保留，primary identity、author/issuer、imprint 及发表日期仍待验证。CMS `2026-09-17`/`2026-09-22` 不作发表日期；后一时间也不据此排除。固定发表区间仍为 **1988-01-01—2026-09-21**，九月部分覆盖。没有作气候/情绪/恐惧筛选、完整性或历史措辞不变的推断。
