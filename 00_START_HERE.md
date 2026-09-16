# 从这里开始：VS Code 快速上手

当前 Python 环境、模型和 Jupyter kernel 已经安装完成。日常使用不需要重新运行
`bootstrap.sh`。

## 1. 找到并运行第一个 notebook

在 VS Code 左侧 Explorer 中找到 `notebooks` 文件夹。点击文件夹左边的小三角展开，
然后依次使用：

1. `notebooks/01_workspace_check.ipynb`
2. `notebooks/02_synthetic_end_to_end.ipynb`

打开 `01_workspace_check.ipynb` 后：

1. 查看右上角 kernel；如果未自动选择，点击 **Select Kernel**；
2. 选择 **Python (Fear of Temperature)**；
3. 点击 **Run All**。

正常结果会显示 Python 3.12、项目 `.venv`、MPS/CPU device、37 条 synthetic
输入和 36 条去重后的 passage。然后打开 `02_synthetic_end_to_end.ipynb`，再次点击
**Run All**，即可运行完整演示。

如果没有出现 Workspace Trust 提示，通常表示这个目录已经被信任。只有 VS Code 左下角
出现 **Restricted Mode** 时才需要点击并选择信任当前仓库。

## 2. 不打开 notebook 也可以运行

按 `Cmd+Shift+P`，输入 `Tasks: Run Task`，然后选择：

- `Workspace: doctor`：检查 Python、路径、模型、MPS 和 kernel；
- `Demo: full synthetic pipeline`：运行完整 synthetic NLP 示例；
- `Tests: pytest`：运行数据约束和时序测试；
- `Notebooks: execute all`：从头执行两个 notebook；
- `Figures: regenerate demo exports`：重新生成示例图表。

也可以在 VS Code Terminal 中运行：

```bash
.venv/bin/fear-temperature-doctor --full-models
.venv/bin/fear-temperature-demo --offline
.venv/bin/pytest
```

## 3. 哪些文件最常用

| 位置 | 用途 |
|---|---|
| `notebooks/01_workspace_check.ipynb` | 第一次打开时确认环境 |
| `notebooks/02_synthetic_end_to_end.ipynb` | 查看完整 NLP/时序演示 |
| `configs/default.yaml` | 输入、输出、随机种子和演示参数 |
| `configs/models.yaml` | 模型 ID、revision 和用途边界 |
| `data/fixtures/synthetic_passages.jsonl` | 输入格式示例；不是研究语料或人工 gold labels |
| `src/fear_temperature/pipeline.py` | 完整演示入口 |
| `src/fear_temperature/` | 清洗、存储、检索、情绪、关系、主题和时序模块 |
| `outputs/demo/` | 可重新生成的表格、向量、DuckDB、图和 manifest |

## 4. 准备自己的数据时

不要覆盖 synthetic fixture。将本地材料放在被 Git 忽略的 `data/raw/` 下。CSV、JSONL
或 Parquet 至少需要以下字段：

```text
source_name
publisher_role    # policy、media 或 public
external_id
publication_date
text
```

可选字段包括 `title`、`location`、`quoted_speaker`、`speaker_role` 和
`emotion_holder`。当前端到端 demo 中的 `fixture_*` 字段只用于软件验收；真实研究数据
需要按 proposal 完成来源许可、人工标签和验证后再进入正式分析。

## 5. 什么时候运行 bootstrap

只有全新 clone 或需要重建 `.venv` 时运行：

```bash
./scripts/bootstrap.sh
```

环境和常见故障详见 `docs/ENVIRONMENT.md`；实际验收结果见
`docs/WORKSPACE_VALIDATION.md`。
