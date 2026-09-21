# M1.2（工作包序号 03）数据库试点

本工作包把 M1.1 已保存的 9 条真实 GOV.UK/DEFRA `policy_paper` 元数据导入仓库既有的 DuckDB 路线，形成可重建、可追溯的最小数据库。目录使用 `03_database_pilot`，因为 `02_meeting_report` 已存在；这不改变 proposal 的里程碑编号。

## 运行

从仓库根目录运行：

```bash
.venv/bin/python work_packages/M1_source_access/03_database_pilot/scripts/rebuild_pilot.py
```

脚本不访问网络，只读取 `01_feasibility/` 内保存的真实证据。它会：

1. 校验两个 evidence JSON 的 SHA-256 与 `checks.json` 一致；
2. 在两个临时 DuckDB 中分别执行重复导入和干净重建；
3. 比较逻辑指纹，验证重复运行不增加记录；
4. 原子替换本地 `fear_temperature_m1_pilot.duckdb`；
5. 重建 CSV、字段字典、质量报告和 manifest。

运行测试：

```bash
.venv/bin/pytest tests/test_database_pilot.py
.venv/bin/ruff check src/fear_temperature/database_pilot.py tests/test_database_pilot.py work_packages/M1_source_access/03_database_pilot/scripts/rebuild_pilot.py
.venv/bin/mypy src
```

## 交付物

- `database_design.md`：表、ID、版本、日期、角色、单位和多机构计数契约。
- `data_dictionary.csv`：从实际 schema 生成的逐字段字典。
- `fear_temperature_m1_pilot.duckdb`：本地试点数据库（仓库规则忽略 `*.duckdb`，但重建脚本可随时生成）。
- `exports/*.csv`：来源、批次、覆盖、原始记录、文档、版本、机构、文本接口及追溯视图。
- `data_quality_report.md`：有针对性的验证、伦理/许可阻塞与计数边界。
- `rebuild_manifest.json`：输入/输出哈希、逻辑指纹、表行数和全部检查结果。
- `scripts/rebuild_pilot.py`：工作包入口；共用实现位于 `src/fear_temperature/database_pilot.py`。
- `progress_report.md`：本轮发现、未解决规范化问题与下一最小任务。

## 真实与合成数据边界

- 数据库内 9 条文档、9 条原始记录及 14 条机构关联均来自 M1.1 保存的 GOV.UK 元数据。
- 真实正文、段落、引用说话者、情绪持有者、重复内容关系和向量均为 0。
- 版本机制自检会在内存数据库中临时修改一条标题并切换规则版本；该测试数据不会写入试点数据库、CSV 或覆盖统计。
- 本轮没有采集公众数据，也没有把政策文档解释为公众表达。

## 计数限制

`N=9` 只有在重现同一 GOV.UK 来源、DEFRA 机构标签、`policy_paper` 类型、`first_published_at` 字段、2026-07-01..2026-07-31 inclusive 窗口、文档单位和去重规则时才能作为分母。它不是 DEFRA 当月全部政策、英国全部政策、气候政策或气候关注度的分母。

多机构发布保留全部关联，但文档总数仍为 9。导出同时提供完整计数和分数计数权重；Lead organisation 仍为 `unknown`，机构统计口径仍待确认。

## 已知限制

- 未发现可核验的伦理批准或豁免，状态保持 `pending`。
- OGL 多数适用的说明不能替代逐件正文/附件和第三方权利审核。
- 单月元数据成功不证明历史语料可获得或跨年代渠道可比。
- 没有正文，因此没有合法的真实切段、内容级重复检测、跨来源重叠检测或向量输入。
- DuckDB 文件的物理字节布局不作为重建一致性标准；脚本比较排序后的逻辑表内容和 CSV 哈希。
