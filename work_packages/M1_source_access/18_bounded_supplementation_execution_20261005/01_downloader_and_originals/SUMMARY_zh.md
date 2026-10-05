# 有界原件处理与下载器修正

下载器已修为 V3，32 项阻断网络测试通过。真实修复放行模式、active committed run、固定区间与当前 post checkpoint 核验通过；B 必须另有协调者接受 A 停止的精确 release 才能请求。

| 最终请求 | 本次结果 | 新 HTTP |
|---|---|---:|
| Hansard 2007-05-17 `doc_5b740259ea5cdcdbdbdf` | 官方 canonical HTML 返回 403，访问停止 | 1 |
| Hansard 2009-02-12 `doc_6fe9e11be5ea65fab67e` | 因持久停止未尝试，正文/边界仍待核验 | 0 |
| Hansard 2010-02-23 `doc_76b0ddb367df2c048a60` | 因持久停止未尝试，正文/边界仍待核验 | 0 |
| AU methane `doc:7c7006b4ea3168ebe548e229915d853b` | 因持久停止未尝试，原件身份与发表日期仍待核验 | 0 |
| AU ocean plan `doc:bc6340389c3977a04993b0a20f55bcca` | 因持久停止未尝试，原件身份与发表日期仍待核验 | 0 |

五项处置齐全，**不代表取得五项原件**。新增/复用原件 0，retained raw/partial 0 字节，共同 raw cap 剩余 2 GiB。未重试原 API 或 403 路线；未启动 EU、提取或正式数据库写入。

真实 A 使用 V2；其 ready、测试、代码、请求和停止证据已保存。V3 将 B HTTP 状态独立，但保留 A 原停止。协调者须绑定 A state digest、明确接受这次 403、限定 B 为冻结 EU hosts/979 Items，并核对继承 cooldown；两阶段仍共享锁、至少两秒间隔和预算。完整模式及命令见 `HANDOFF_zh.md` / `EU_RELEASE_REQUIREMENTS.json`。
