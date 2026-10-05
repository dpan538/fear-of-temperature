# EU2015 本地准备交接

**状态：`waiting_for_coordinator_EU_release`。本轮本地准备完成，补采未开始。**

冻结清单 SHA-256 仍为 `af3fa2aa5c9cd6b1e97ad8b27fba17769be2c4916b3ef3dc4a6ab87fb772a4f7`；979 个唯一 Work / selected Item、2015 年全部 12 个月、既有来源合同及请求路线一致。新 `INPUT_RECEIPT.json` 保存了输入哈希与时间，未覆盖旧报告或清单。

`B_TARGET_STATUS.csv` 覆盖全部 **979 项**：本地状态均为 **unrequested**，本次尝试状态均为 **not_attempted_waiting_for_coordinator_EU_release**。仅检查已声明的 source raw/items、旧 Task4 暂存和新 B 暂存目标路径及同 Item sidecar/partial 前缀；未发现 raw、request sidecar 或 partial。目录检查不等于成功下载；本轮 raw hash 读取为 0。

保留 **1,009 个已枚举 Work、30 个 no-link outcome**。973 个目标 Work 有多个不同 Item；其中 **253 个 Work 在 selected PDF Manifestation 内有多个 Item**，726 个在该 Manifestation 内只有一个，最大为 10。8,409 条保存关系与逐 Work multiplicity 表核对一致。不能据此断言所有 sibling 都是附件，也不能断言 726 个单 Item Work 完整；不追加 sibling、alternate 或 annex 队列。

15 项本地范围/身份/月份/关系检查通过。实测约 **19.23 GiB** 可用，扣除既有约 3.16 GiB 预留后约 **16.07 GiB**，本快照高于 **15 GiB** 下限。跨 A+B 的 **2 GiB new-raw cap** 包含保留 partial；最终五项 A 的终态与实际字节预算仍待 Task3/协调者验收，不能假定 A 消耗为零。

本轮未编辑或导入下载器、未执行原 preflight/下载器、未发 HTTP（含 HEAD）、未提取正文、未打开或写入正式数据库、未定位/读取/解密/执行/复制/探测封存审计代码或凭据；未做语义/气候/情绪/恐惧过滤、commit/push。未修改或签发 release；无等待循环或后台 collector。

下一步由 Task3 完成下载器修正与离线验证、最终五项 original 请求终态和预算核算；协调者验收并签发 `control/EU_STAGING_RELEASE.json`，再向本窗口发送明确执行 follow-up。随后使用验收版下载器暂存同一 979 项，保留限速、cooldown、首次失败停止、空间及总 cap 门槛。已有修复 release 本身有效，但不能替代这次 A-before-B 与下载器验收。

固定出版区间 **1988-01-01–2026-09-21**，9 月不完整；本 tranche 仅 2015 年。证据层级：1）日期/关系元数据核对完成，本轮新增候选正文/已验证可读完整 Work 均为 0；2）气候相关性与相似度未评估；3）情感/风险/未来伤害/责任关联未评估；4）恐惧解释未评估。上述指标均不作当前保留或采集门槛。
