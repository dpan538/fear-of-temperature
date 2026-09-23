from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import duckdb


PACKAGE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PACKAGE_DIR / "fear_temperature_government_content.duckdb"
RAW_DIR = PACKAGE_DIR / "raw"
OUTPUT_DIR = PACKAGE_DIR / "text_quality_review"
BATCH_ID = "govuk_defra_policy_paper_content_20260921_v1"


FORMAT_GROUP_LABELS = {
    "webpage": "网页",
    "pdf": "PDF",
    "csv": "CSV",
    "other": "其他",
}

RECORD_MODEL_LABELS = {
    "webpage_html_paragraph": "网页 HTML：标题及 main 内的标题、段落、列表项或引文；一元素一片段",
    "html_attachment_paragraph": "HTML 附件：标题及 main 内的标题、段落、列表项或引文；一元素一片段",
    "odt_paragraph": "ODT：标题或段落块；一 XML h/p 元素一片段",
    "pdf_line_block": "PDF：PDFium 页面文本按换行拆分；一行/块一片段",
    "csv_row": "CSV：一表格行一片段；单元格按列序用“ | ”拼接",
    "ods_row": "ODS：一非空表格行一片段；非空单元格用“ | ”拼接（未保留工作表名/单元格地址）",
    "pptx_slide_block": "PPTX：一幻灯片文本段落/块一片段",
}


SAMPLES = [
    {
        "category": "网页",
        "content_object_id": "cnt_94b75aa5b50aa70a7ff0",
        "sequence_note": "DOM 主内容顺序可追溯；末尾仍包含 GOV.UK 更新/打印提示。",
        "content_note": "网页本身有较长说明，但两个 PDF 附件文本量约为网页的 96 倍；完整方案正文主要在附件。",
        "noise_note": "未见站点导航栏，但保留 Details、Documents、Updates 等服务性结构文本。",
        "recommendation": "网页可作元数据/摘要；政策正文以附件为主，避免把“网页提取成功”当作“全文已齐”。",
    },
    {
        "category": "网页",
        "content_object_id": "cnt_f1cf4af61edc7903aff8",
        "sequence_note": "DOM 段落顺序合理，片段数量少。",
        "content_note": "无附件，正文主要位于网页；当前提取覆盖标题、说明和更新信息。",
        "noise_note": "含标准 GOV.UK 结构标题，但正文段落本身可读。",
        "recommendation": "可直接进入后续文本处理，先过滤固定服务性标题。",
    },
    {
        "category": "网页",
        "content_object_id": "cnt_bf22e780896f75e2298d",
        "sequence_note": "DOM 顺序正常。",
        "content_note": "落地页与所谓 PDF 附件均得到 HTML，且实质片段完全精确重合；附件链接未形成独立 PDF 正文。",
        "noise_note": "主要风险不是导航噪声，而是网页/附件重复计数和 MIME/落地结果误判。",
        "recommendation": "保留两条获取记录，但正文处理只保留一个逻辑副本，并把附件标成重复候选。",
    },
    {
        "category": "普通 PDF",
        "content_object_id": "cnt_b5f4b427261c58559d61",
        "sequence_note": "页码与块号单调，正文阅读顺序基本合理。",
        "content_note": "10 页政策说明可读，片段以完整文本行为主。",
        "noise_note": "包含版权页、页眉/页脚及少量短行；重复片段率低。",
        "recommendation": "内容可用；进入段落级处理前按页合并相邻行并剔除重复页眉/页脚。",
    },
    {
        "category": "普通 PDF",
        "content_object_id": "cnt_3500a8001e519734136e",
        "sequence_note": "页码与块号单调，正文顺序整体连贯。",
        "content_note": "报告正文可读，短片段比例较低。",
        "noise_note": "句子常被换行切成两段，结尾不一定对应 PDF 最后一页的完整逻辑结尾。",
        "recommendation": "可作为可用正文，但建议在下游按页面/句子重组，不改写 source_extracted 层。",
    },
    {
        "category": "普通 PDF",
        "content_object_id": "cnt_cbc39b369a7bdd20494b",
        "sequence_note": "页码与块号单调；中段文本可读。",
        "content_note": "正文可抽取，但短片段偏多，尾部包含网址和联系信息。",
        "noise_note": "37.8% 片段不超过 20 字符，页眉、网址和联系栏会进入语言文本。",
        "recommendation": "先做页内相邻行合并和页眉/联系栏标记，再纳入语言处理。",
    },
    {
        "category": "长报告/法案",
        "content_object_id": "cnt_7e6de02166f756401f80",
        "sequence_note": "页码单调，但版面被拆成大量极短块；局部顺序不足以代表自然段顺序。",
        "content_note": "687 页文件提取出 149,429 片段，95.1% 不超过 20 字符，是全库最大片段来源。",
        "noise_note": "印刷文件名、页码、标点和重复短词大量独立成片，重复片段率很高。",
        "recommendation": "必须调整切分；当前层仅作可追溯原始提取，不直接作为语言模型/向量文本。",
    },
    {
        "category": "长报告/表格型 PDF",
        "content_object_id": "cnt_0cda1f6ed4af80345372",
        "sequence_note": "页码单调，但跨列表格按视觉布局拆成线性块，列与行关系不稳定。",
        "content_note": "1,936 页附件以水体状态表为主，97,409 个片段中大量为代码、状态值和页眉。",
        "noise_note": "重复页眉、表头和分类值导致 91.4% 片段文本重复。",
        "recommendation": "保留作结构化/表格证据；在版面表格重建前暂不纳入通用语言处理。",
    },
    {
        "category": "长报告",
        "content_object_id": "cnt_fef7848a752411b6c923",
        "sequence_note": "页码与块号单调；正文、表格和修订记录混在同一片段流。",
        "content_note": "754 页 programme document 有可读段落，也有大量表格/编号记录。",
        "noise_note": "26.1% 为极短片段，重复片段率 40.2%；末端主要是修订/标识记录。",
        "recommendation": "按页型/章节分流：叙述性章节可重组后使用，表格和修订清单保留但分开处理。",
    },
    {
        "category": "CSV 表格",
        "content_object_id": "cnt_b74985815043b7817ded",
        "sequence_note": "CSV 行序与列序保留；每行被压成一个文本片段。",
        "content_note": "10,657 行环境浓度数据库完整进入片段层，是结构化数据而非连续正文。",
        "noise_note": "没有导航噪声，但“ | ”拼接不等于语义句子，空值/单位/列名需要按表结构解释。",
        "recommendation": "保留并用于表格分析；暂不作为通用语言文本或段落向量输入。",
    },
    {
        "category": "CSV 表格",
        "content_object_id": "cnt_fae9ae23a0b089359400",
        "sequence_note": "221 行的行序、列序清楚。",
        "content_note": "三列机构名录提取稳定，当前片段正好对应一条表格记录。",
        "noise_note": "无明显网页噪声；风险在于把分类表误当自然语言段落。",
        "recommendation": "直接用于结构化筛选/关联；通用语言处理应排除或使用表格专用表示。",
    },
    {
        "category": "ODS 表格",
        "content_object_id": "cnt_494d2a46237874ced427",
        "sequence_note": "行序可见，但 locator 只有全局 row，未保留工作表名；跨表边界不可直接判断。",
        "content_note": "1,726 个非空行被抽成文本，行内非空单元格按顺序拼接。",
        "noise_note": "空单元格被过滤，可能造成列位置漂移；部分行只有短标签。",
        "recommendation": "保留原 ODS 并改进表格定位（sheet/cell/列名）后再用于结构化处理；暂不作语言正文。",
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def as_dicts(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(numerator: float | int, denominator: float | int) -> float:
    return round(100.0 * float(numerator) / float(denominator), 2) if denominator else 0.0


def fmt_int(value: Any) -> str:
    return f"{int(value):,}"


def fmt_pct(value: Any) -> str:
    return f"{float(value):.2f}%"


def clip_markdown(value: str, limit: int = 280) -> str:
    compact = value.replace("\n", " ").replace("|", "\\|")
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def make_controls_visible(value: str) -> str:
    """Render embedded C0 controls visibly without changing the stored source text."""
    return re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
        lambda match: f"⟨U+{ord(match.group(0)):04X}⟩",
        value,
    )


def group_for(object_kind: str, actual_format: str) -> str:
    if object_kind == "webpage":
        return "webpage"
    if actual_format == "pdf":
        return "pdf"
    if actual_format == "csv":
        return "csv"
    return "other"


def record_model_for(object_kind: str, actual_format: str) -> str:
    if object_kind == "webpage":
        return "webpage_html_paragraph"
    return {
        "html": "html_attachment_paragraph",
        "odt": "odt_paragraph",
        "pdf": "pdf_line_block",
        "csv": "csv_row",
        "ods": "ods_row",
        "pptx": "pptx_slide_block",
    }.get(actual_format, "no_text_or_unsupported")


def segment_window(
    segments: list[dict[str, Any]], mode: str, minimum_chars: int = 320, maximum_segments: int = 20
) -> tuple[str, str]:
    if not segments:
        return "", ""
    count = len(segments)
    if mode == "start":
        indices = range(0, min(count, maximum_segments))
    elif mode == "middle":
        anchor = count // 2
        start = anchor
        indices = range(start, min(count, start + maximum_segments))
    else:
        indices = range(count - 1, max(-1, count - maximum_segments - 1), -1)

    selected: list[dict[str, Any]] = []
    running = 0
    for index in indices:
        item = segments[index]
        if mode == "end":
            selected.insert(0, item)
        else:
            selected.append(item)
        running += len(item["segment_text"])
        if running >= minimum_chars:
            break

    first = selected[0]["locator"]
    last = selected[-1]["locator"]
    locator = first if first == last else f"{first} → {last}"
    pieces = []
    for item in selected:
        text = item["segment_text"]
        if len(text) > 800:
            text = text[:800] + "…[单片段展示截断]"
        pieces.append(make_controls_visible(text))
    return locator, " ⟦片段边界⟧ ".join(pieces)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db_hash_before = sha256_file(DATABASE_PATH)
    raw_count_before = sum(1 for path in RAW_DIR.rglob("*") if path.is_file())
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)
    try:
        object_metrics = as_dicts(
            connection.execute(
                """
                WITH segment_metrics AS (
                    SELECT
                        v.content_object_id,
                        COUNT(*) AS segments,
                        SUM(LENGTH(s.segment_text)) AS characters,
                        QUANTILE_DISC(LENGTH(s.segment_text), 0.5) AS median_chars,
                        SUM(LENGTH(s.segment_text) <= 20) AS extremely_short_segments,
                        COUNT(DISTINCT s.text_sha256) AS distinct_segment_texts
                    FROM content_versions v
                    JOIN text_segments s USING (content_version_id)
                    GROUP BY v.content_object_id
                ), document_links AS (
                    SELECT
                        dco.content_object_id,
                        STRING_AGG(DISTINCT d.title, ' || ' ORDER BY d.title) AS document_titles,
                        STRING_AGG(DISTINCT dco.relationship_type, '|' ORDER BY dco.relationship_type) AS relationship_types
                    FROM document_content_objects dco
                    JOIN documents d USING (document_id)
                    GROUP BY dco.content_object_id
                )
                SELECT
                    a.content_object_id,
                    a.object_kind,
                    a.actual_format,
                    a.download_status,
                    a.validation_status,
                    a.extraction_status,
                    a.extraction_reason,
                    a.byte_size,
                    a.segment_count,
                    a.raw_path,
                    co.title,
                    co.canonical_url,
                    COALESCE(sm.segments, 0) AS segments,
                    COALESCE(sm.characters, 0) AS characters,
                    COALESCE(sm.median_chars, 0) AS median_chars,
                    COALESCE(sm.extremely_short_segments, 0) AS extremely_short_segments,
                    COALESCE(sm.distinct_segment_texts, 0) AS distinct_segment_texts,
                    COALESCE(dl.document_titles, '') AS document_titles,
                    COALESCE(dl.relationship_types, '') AS relationship_types
                FROM acquisition_object_statuses a
                JOIN content_objects co USING (content_object_id)
                LEFT JOIN segment_metrics sm USING (content_object_id)
                LEFT JOIN document_links dl USING (content_object_id)
                WHERE a.batch_id = ?
                ORDER BY a.content_object_id
                """,
                [BATCH_ID],
            )
        )
        by_object = {row["content_object_id"]: row for row in object_metrics}
        total_segments = sum(int(row["segments"]) for row in object_metrics)
        total_characters = sum(int(row["characters"]) for row in object_metrics)

        # 1. Format summary: requested four groups plus auditable detail rows.
        format_summary: list[dict[str, Any]] = []
        grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in object_metrics:
            row["format_group"] = group_for(row["object_kind"], row["actual_format"])
            row["record_model"] = record_model_for(row["object_kind"], row["actual_format"])
            grouped[("group", row["format_group"])].append(row)
            grouped[("detail", row["format_group"], row["object_kind"], row["actual_format"])].append(row)
        for key, rows in sorted(grouped.items(), key=lambda item: item[0]):
            row_type = key[0]
            group = key[1]
            object_kind = "ALL" if row_type == "group" else key[2]
            actual_format = "ALL" if row_type == "group" else key[3]
            segments = sum(int(row["segments"]) for row in rows)
            characters = sum(int(row["characters"]) for row in rows)
            record_models = sorted({row["record_model"] for row in rows})
            format_summary.append(
                {
                    "row_type": row_type,
                    "format_group": group,
                    "format_group_zh": FORMAT_GROUP_LABELS[group],
                    "object_kind": object_kind,
                    "actual_format": actual_format,
                    "object_count": len(rows),
                    "download_success_count": sum(row["download_status"] == "success" for row in rows),
                    "extraction_success_count": sum(row["extraction_status"] == "success" for row in rows),
                    "segment_count": segments,
                    "segment_share_pct": pct(segments, total_segments),
                    "character_count": characters,
                    "character_share_pct": pct(characters, total_characters),
                    "record_model": " | ".join(record_models),
                }
            )
        format_summary.sort(
            key=lambda row: (
                0 if row["row_type"] == "group" else 1,
                ["webpage", "pdf", "csv", "other"].index(row["format_group"]),
                row["actual_format"],
            )
        )
        write_csv(
            OUTPUT_DIR / "01_format_summary.csv",
            format_summary,
            [
                "row_type",
                "format_group",
                "format_group_zh",
                "object_kind",
                "actual_format",
                "object_count",
                "download_success_count",
                "extraction_success_count",
                "segment_count",
                "segment_share_pct",
                "character_count",
                "character_share_pct",
                "record_model",
            ],
        )

        # Top 20 objects by segment count.
        top20: list[dict[str, Any]] = []
        ranked_objects = sorted(
            object_metrics,
            key=lambda row: (-int(row["segments"]), row["content_object_id"]),
        )[:20]
        for rank, row in enumerate(ranked_objects, start=1):
            segments = int(row["segments"])
            top20.append(
                {
                    "rank": rank,
                    "content_object_id": row["content_object_id"],
                    "title": row["title"],
                    "document_titles": row["document_titles"],
                    "relationship_types": row["relationship_types"],
                    "format_group": row["format_group"],
                    "actual_format": row["actual_format"],
                    "canonical_url": row["canonical_url"],
                    "raw_path": row["raw_path"],
                    "segment_count": segments,
                    "segment_share_pct": pct(segments, total_segments),
                    "character_count": int(row["characters"]),
                    "median_segment_chars": int(row["median_chars"]),
                    "extremely_short_segments_le_20": int(row["extremely_short_segments"]),
                    "extremely_short_share_pct": pct(row["extremely_short_segments"], segments),
                    "repeated_text_share_pct": pct(
                        segments - int(row["distinct_segment_texts"]), segments
                    ),
                }
            )
        write_csv(
            OUTPUT_DIR / "02_top20_objects.csv",
            top20,
            [
                "rank",
                "content_object_id",
                "title",
                "document_titles",
                "relationship_types",
                "format_group",
                "actual_format",
                "canonical_url",
                "raw_path",
                "segment_count",
                "segment_share_pct",
                "character_count",
                "median_segment_chars",
                "extremely_short_segments_le_20",
                "extremely_short_share_pct",
                "repeated_text_share_pct",
            ],
        )

        # 2. Segment length distribution by requested group and actual record model.
        connection.execute(
            """
            CREATE TEMP VIEW quality_segment_lengths AS
            SELECT
                v.content_object_id,
                CASE
                    WHEN a.object_kind = 'webpage' THEN 'webpage'
                    WHEN a.actual_format = 'pdf' THEN 'pdf'
                    WHEN a.actual_format = 'csv' THEN 'csv'
                    ELSE 'other'
                END AS format_group,
                CASE
                    WHEN a.object_kind = 'webpage' THEN 'webpage_html_paragraph'
                    WHEN a.actual_format = 'html' THEN 'html_attachment_paragraph'
                    WHEN a.actual_format = 'odt' THEN 'odt_paragraph'
                    WHEN a.actual_format = 'pdf' THEN 'pdf_line_block'
                    WHEN a.actual_format = 'csv' THEN 'csv_row'
                    WHEN a.actual_format = 'ods' THEN 'ods_row'
                    WHEN a.actual_format = 'pptx' THEN 'pptx_slide_block'
                    ELSE 'other'
                END AS record_model,
                LENGTH(s.segment_text) AS segment_chars
            FROM text_segments s
            JOIN content_versions v USING (content_version_id)
            JOIN acquisition_object_statuses a USING (content_object_id)
            WHERE a.batch_id = 'govuk_defra_policy_paper_content_20260921_v1'
            """
        )
        aggregate_sql = """
            SELECT
                {scope_type} AS scope_type,
                {scope_value} AS scope_value,
                COUNT(DISTINCT content_object_id) AS objects_with_segments,
                COUNT(*) AS segment_count,
                SUM(segment_chars) AS character_count,
                MIN(segment_chars) AS min_chars,
                QUANTILE_DISC(segment_chars, 0.01) AS p01_chars,
                QUANTILE_DISC(segment_chars, 0.05) AS p05_chars,
                QUANTILE_DISC(segment_chars, 0.10) AS p10_chars,
                QUANTILE_DISC(segment_chars, 0.25) AS p25_chars,
                QUANTILE_DISC(segment_chars, 0.50) AS p50_chars,
                QUANTILE_DISC(segment_chars, 0.75) AS p75_chars,
                QUANTILE_DISC(segment_chars, 0.90) AS p90_chars,
                QUANTILE_DISC(segment_chars, 0.95) AS p95_chars,
                QUANTILE_DISC(segment_chars, 0.99) AS p99_chars,
                MAX(segment_chars) AS max_chars,
                ROUND(AVG(segment_chars), 2) AS mean_chars,
                SUM(segment_chars <= 5) AS le_5_count,
                ROUND(100.0 * SUM(segment_chars <= 5) / COUNT(*), 2) AS le_5_share_pct,
                SUM(segment_chars <= 10) AS le_10_count,
                ROUND(100.0 * SUM(segment_chars <= 10) / COUNT(*), 2) AS le_10_share_pct,
                SUM(segment_chars <= 20) AS le_20_count,
                ROUND(100.0 * SUM(segment_chars <= 20) / COUNT(*), 2) AS le_20_share_pct,
                SUM(segment_chars <= 30) AS le_30_count,
                ROUND(100.0 * SUM(segment_chars <= 30) / COUNT(*), 2) AS le_30_share_pct
            FROM quality_segment_lengths
            {group_by}
        """
        length_distribution: list[dict[str, Any]] = []
        length_distribution.extend(
            as_dicts(
                connection.execute(
                    aggregate_sql.format(
                        scope_type="'all'", scope_value="'all'", group_by=""
                    )
                )
            )
        )
        length_distribution.extend(
            as_dicts(
                connection.execute(
                    aggregate_sql.format(
                        scope_type="'format_group'",
                        scope_value="format_group",
                        group_by="GROUP BY format_group",
                    )
                )
            )
        )
        length_distribution.extend(
            as_dicts(
                connection.execute(
                    aggregate_sql.format(
                        scope_type="'record_model'",
                        scope_value="record_model",
                        group_by="GROUP BY record_model",
                    )
                )
            )
        )
        for row in length_distribution:
            row["record_model_explanation"] = RECORD_MODEL_LABELS.get(row["scope_value"], "")
        length_distribution.sort(
            key=lambda row: (
                {"all": 0, "format_group": 1, "record_model": 2}[row["scope_type"]],
                str(row["scope_value"]),
            )
        )
        length_fields = [
            "scope_type",
            "scope_value",
            "objects_with_segments",
            "segment_count",
            "character_count",
            "min_chars",
            "p01_chars",
            "p05_chars",
            "p10_chars",
            "p25_chars",
            "p50_chars",
            "p75_chars",
            "p90_chars",
            "p95_chars",
            "p99_chars",
            "max_chars",
            "mean_chars",
            "le_5_count",
            "le_5_share_pct",
            "le_10_count",
            "le_10_share_pct",
            "le_20_count",
            "le_20_share_pct",
            "le_30_count",
            "le_30_share_pct",
            "record_model_explanation",
        ]
        write_csv(OUTPUT_DIR / "03_segment_length_distribution.csv", length_distribution, length_fields)

        # 3. Twelve readable samples, with exact segment boundaries marked only for display.
        sample_ids = [item["content_object_id"] for item in SAMPLES]
        segment_rows = as_dicts(
            connection.execute(
                """
                SELECT
                    v.content_object_id,
                    s.segment_order,
                    s.locator,
                    s.segment_text
                FROM text_segments s
                JOIN content_versions v USING (content_version_id)
                WHERE v.content_object_id IN (SELECT UNNEST(?))
                ORDER BY v.content_object_id, s.segment_order
                """,
                [sample_ids],
            )
        )
        sample_segments: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in segment_rows:
            sample_segments[row["content_object_id"]].append(row)
        sample_rows: list[dict[str, Any]] = []
        for sample_number, sample in enumerate(SAMPLES, start=1):
            object_id = sample["content_object_id"]
            metrics = by_object[object_id]
            segments = sample_segments[object_id]
            start_locator, start_text = segment_window(segments, "start")
            middle_locator, middle_text = segment_window(segments, "middle")
            end_locator, end_text = segment_window(segments, "end")
            sample_rows.append(
                {
                    "sample_number": sample_number,
                    "category": sample["category"],
                    "content_object_id": object_id,
                    "title": metrics["title"],
                    "document_titles": metrics["document_titles"],
                    "relationship_types": metrics["relationship_types"],
                    "actual_format": metrics["actual_format"],
                    "canonical_url": metrics["canonical_url"],
                    "raw_path": metrics["raw_path"],
                    "segment_count": metrics["segments"],
                    "character_count": metrics["characters"],
                    "median_segment_chars": metrics["median_chars"],
                    "extremely_short_share_pct": pct(
                        metrics["extremely_short_segments"], metrics["segments"]
                    ),
                    "start_locator": start_locator,
                    "start_current_extraction": start_text,
                    "middle_locator": middle_locator,
                    "middle_current_extraction": middle_text,
                    "end_locator": end_locator,
                    "end_current_extraction": end_text,
                    "sequence_assessment": sample["sequence_note"],
                    "content_completeness_assessment": sample["content_note"],
                    "noise_assessment": sample["noise_note"],
                    "review_recommendation": sample["recommendation"],
                }
            )
        sample_fields = list(sample_rows[0].keys())
        write_csv(OUTPUT_DIR / "04_readable_samples.csv", sample_rows, sample_fields)

        # 4. Per-document web/attachment value and conservative exact-overlap candidates.
        document_value = as_dicts(
            connection.execute(
                """
                WITH object_metrics AS (
                    SELECT
                        a.content_object_id,
                        a.actual_format,
                        a.download_status,
                        a.extraction_status,
                        COALESCE(COUNT(s.segment_id), 0) AS segments,
                        COALESCE(SUM(LENGTH(s.segment_text)), 0) AS characters
                    FROM acquisition_object_statuses a
                    LEFT JOIN content_versions v ON v.content_object_id = a.content_object_id
                    LEFT JOIN text_segments s ON s.content_version_id = v.content_version_id
                    WHERE a.batch_id = ?
                    GROUP BY a.content_object_id, a.actual_format, a.download_status, a.extraction_status
                ), document_metrics AS (
                    SELECT
                        d.document_id,
                        d.title,
                        d.canonical_url,
                        d.publication_date,
                        MAX(dco.content_object_id) FILTER (WHERE dco.relationship_type = 'landing_page') AS landing_object_id,
                        COALESCE(SUM(om.segments) FILTER (WHERE dco.relationship_type = 'landing_page'), 0) AS webpage_segments,
                        COALESCE(SUM(om.characters) FILTER (WHERE dco.relationship_type = 'landing_page'), 0) AS webpage_characters,
                        COUNT(*) FILTER (WHERE dco.relationship_type = 'attachment') AS attachment_object_count,
                        COUNT(*) FILTER (WHERE dco.relationship_type = 'attachment' AND om.download_status = 'success') AS attachment_download_success_count,
                        COUNT(*) FILTER (WHERE dco.relationship_type = 'attachment' AND om.extraction_status = 'success') AS attachment_extraction_success_count,
                        COUNT(*) FILTER (WHERE dco.relationship_type = 'attachment' AND om.extraction_status != 'success') AS attachment_not_extracted_count,
                        COALESCE(SUM(om.segments) FILTER (WHERE dco.relationship_type = 'attachment'), 0) AS attachment_segments,
                        COALESCE(SUM(om.characters) FILTER (WHERE dco.relationship_type = 'attachment'), 0) AS attachment_characters,
                        COALESCE(STRING_AGG(DISTINCT om.actual_format, '|' ORDER BY om.actual_format) FILTER (WHERE dco.relationship_type = 'attachment'), '') AS attachment_formats
                    FROM documents d
                    JOIN document_content_objects dco USING (document_id)
                    JOIN object_metrics om USING (content_object_id)
                    GROUP BY d.document_id, d.title, d.canonical_url, d.publication_date
                ), substantive_text AS (
                    SELECT
                        dco.document_id,
                        dco.relationship_type,
                        s.text_sha256,
                        MAX(LENGTH(s.segment_text)) AS characters
                    FROM document_content_objects dco
                    JOIN content_versions v USING (content_object_id)
                    JOIN text_segments s USING (content_version_id)
                    WHERE LENGTH(s.segment_text) >= 40
                    GROUP BY dco.document_id, dco.relationship_type, s.text_sha256
                ), substantive_sums AS (
                    SELECT
                        document_id,
                        COALESCE(SUM(characters) FILTER (WHERE relationship_type = 'landing_page'), 0) AS webpage_substantive_characters,
                        COALESCE(SUM(characters) FILTER (WHERE relationship_type = 'attachment'), 0) AS attachment_substantive_characters
                    FROM substantive_text
                    GROUP BY document_id
                ), shared_text AS (
                    SELECT
                        w.document_id,
                        COUNT(*) AS exact_shared_substantive_segments,
                        SUM(w.characters) AS exact_shared_characters
                    FROM substantive_text w
                    JOIN substantive_text a
                      ON a.document_id = w.document_id
                     AND a.text_sha256 = w.text_sha256
                     AND a.relationship_type = 'attachment'
                    WHERE w.relationship_type = 'landing_page'
                    GROUP BY w.document_id
                )
                SELECT
                    dm.*,
                    CASE
                        WHEN dm.attachment_characters >= 1000
                         AND dm.attachment_characters >= 3 * GREATEST(dm.webpage_characters, 1)
                            THEN 'attachment_primary'
                        WHEN dm.webpage_characters >= 1000
                         AND (dm.attachment_characters = 0 OR dm.webpage_characters >= 3 * dm.attachment_characters)
                            THEN 'webpage_primary'
                        WHEN dm.webpage_characters >= 500 AND dm.attachment_characters >= 500
                            THEN 'mixed_substantive'
                        WHEN dm.webpage_characters > 0
                            THEN 'webpage_short_or_attachment_unavailable'
                        ELSE 'no_extracted_text'
                    END AS primary_body_location,
                    COALESCE(ss.webpage_substantive_characters, 0) AS webpage_substantive_characters,
                    COALESCE(ss.attachment_substantive_characters, 0) AS attachment_substantive_characters,
                    COALESCE(st.exact_shared_substantive_segments, 0) AS exact_shared_substantive_segments,
                    COALESCE(st.exact_shared_characters, 0) AS exact_shared_characters,
                    ROUND(
                        100.0 * COALESCE(st.exact_shared_characters, 0)
                        / GREATEST(1, LEAST(
                            COALESCE(ss.webpage_substantive_characters, 0),
                            COALESCE(ss.attachment_substantive_characters, 0)
                        )),
                        2
                    ) AS exact_overlap_pct_of_smaller_side,
                    CASE
                        WHEN COALESCE(st.exact_shared_substantive_segments, 0) >= 3
                         AND 100.0 * COALESCE(st.exact_shared_characters, 0)
                             / GREATEST(1, LEAST(
                                 COALESCE(ss.webpage_substantive_characters, 0),
                                 COALESCE(ss.attachment_substantive_characters, 0)
                             )) >= 90
                            THEN 'high_confidence_exact_near_duplicate'
                        WHEN COALESCE(st.exact_shared_substantive_segments, 0) >= 2
                         AND 100.0 * COALESCE(st.exact_shared_characters, 0)
                             / GREATEST(1, LEAST(
                                 COALESCE(ss.webpage_substantive_characters, 0),
                                 COALESCE(ss.attachment_substantive_characters, 0)
                             )) >= 25
                            THEN 'possible_exact_overlap'
                        ELSE 'not_flagged'
                    END AS duplicate_candidate_status
                FROM document_metrics dm
                LEFT JOIN substantive_sums ss USING (document_id)
                LEFT JOIN shared_text st USING (document_id)
                ORDER BY dm.document_id
                """,
                [BATCH_ID],
            )
        )
        document_fields = list(document_value[0].keys())
        write_csv(OUTPUT_DIR / "05_document_body_value.csv", document_value, document_fields)

        # Report calculations.
        group_rows = {
            row["format_group"]: row for row in format_summary if row["row_type"] == "group"
        }
        all_length = next(
            row for row in length_distribution if row["scope_type"] == "all"
        )
        group_lengths = {
            row["scope_value"]: row
            for row in length_distribution
            if row["scope_type"] == "format_group"
        }
        body_class_counts: dict[str, int] = defaultdict(int)
        for row in document_value:
            body_class_counts[row["primary_body_location"]] += 1
        duplicate_counts: dict[str, int] = defaultdict(int)
        for row in document_value:
            duplicate_counts[row["duplicate_candidate_status"]] += 1
        duplicate_examples = sorted(
            [row for row in document_value if row["duplicate_candidate_status"] != "not_flagged"],
            key=lambda row: (-float(row["exact_overlap_pct_of_smaller_side"]), -int(row["exact_shared_characters"])),
        )[:5]
        top20_segments = sum(int(row["segment_count"]) for row in top20)
        webpage_boilerplate_terms = {
            "Details",
            "Documents",
            "Updates to this page",
            "Sign up for emails or print this page",
        }
        boilerplate_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM text_segments s
            JOIN content_versions v USING (content_version_id)
            JOIN acquisition_object_statuses a USING (content_object_id)
            WHERE a.object_kind = 'webpage'
              AND s.segment_text IN (SELECT UNNEST(?))
            """,
            [sorted(webpage_boilerplate_terms)],
        ).fetchone()[0]
        failure_rows = as_dicts(
            connection.execute(
                """
                SELECT download_status, extraction_status, COUNT(*) AS object_count
                FROM acquisition_object_statuses
                WHERE batch_id = ?
                  AND (download_status != 'success' OR extraction_status != 'success')
                GROUP BY download_status, extraction_status
                ORDER BY download_status, extraction_status
                """,
                [BATCH_ID],
            )
        )

        report: list[str] = []
        report.append("# 06 批次真实文本质量报告（供 Dai 审阅）")
        report.append("")
        report.append(
            f"> 生成时间：{generated_at}。范围：现有 06 批次；只读检查，不联网、不补采、不向量化、不调用模型、不改写原始文件、不改数据库结构。"
        )
        report.append("")
        report.append("## 结论摘要")
        report.append("")
        report.append(
            f"06 批次共有 **{fmt_int(len(object_metrics))} 个对象、{fmt_int(total_segments)} 个片段、{fmt_int(total_characters)} 个字符**。片段总量主要由 PDF 驱动：PDF 占 {fmt_pct(group_rows['pdf']['segment_share_pct'])}；前 20 个对象又占全部片段的 {fmt_pct(pct(top20_segments, total_segments))}。"
        )
        report.append(
            f"整体片段长度中位数仅 **{all_length['p50_chars']} 字符**；定义“极短”为 **≤20 字符**，共有 **{fmt_int(all_length['le_20_count'])} 个（{fmt_pct(all_length['le_20_share_pct'])}）**。核心原因是 PDF 按页面换行逐行/块切分，而非自然段切分。"
        )
        report.append(
            f"按文本量启发式判断，{body_class_counts['attachment_primary']} / {len(document_value)} 个发布记录的正文主要在附件；只有 {body_class_counts['webpage_primary']} 个明显以网页为主，{body_class_counts['mixed_substantive']} 个网页与附件均有实质内容。网页提取成功不能代表政策全文已经取得。"
        )
        report.append(
            "当前数据层适合做可追溯的 source_extracted 存档，但不宜把全部 285 万片段直接投入向量化或语言分析。"
        )
        report.append("")
        report.append("## 1. 对象、片段与字符数量")
        report.append("")
        report.append(
            "分类口径：`网页`只指 1,020 个 publication landing page；HTML 附件归入`其他`，避免把发布页与附件混在一起。字符数为当前 `segment_text` 的 Unicode 字符数之和。"
        )
        report.append("")
        report.append("| 格式组 | 对象数 | 下载成功 | 提取成功 | 片段数 | 片段占比 | 字符数 |")
        report.append("|---|---:|---:|---:|---:|---:|---:|")
        for group in ["webpage", "pdf", "csv", "other"]:
            row = group_rows[group]
            report.append(
                f"| {FORMAT_GROUP_LABELS[group]} | {fmt_int(row['object_count'])} | {fmt_int(row['download_success_count'])} | {fmt_int(row['extraction_success_count'])} | {fmt_int(row['segment_count'])} | {fmt_pct(row['segment_share_pct'])} | {fmt_int(row['character_count'])} |"
            )
        report.append("")
        report.append(
            "`其他`包括 538 个 HTML 附件、60 个 ODT、2 个 ODS、2 个 PPTX，以及无文本片段的 ZIP/XLS/PNG；完整明细见 [01_format_summary.csv](01_format_summary.csv)。"
        )
        report.append("")
        report.append("### 片段数最高的 20 个对象")
        report.append("")
        report.append("| 排名 | 标题 | 格式 | 片段数 | 占总片段 | ≤20 字符 |")
        report.append("|---:|---|---|---:|---:|---:|")
        for row in top20:
            report.append(
                f"| {row['rank']} | {clip_markdown(row['title'], 88)} | {row['actual_format']} | {fmt_int(row['segment_count'])} | {fmt_pct(row['segment_share_pct'])} | {fmt_pct(row['extremely_short_share_pct'])} |"
            )
        report.append("")
        report.append(
            f"前 20 个对象合计 **{fmt_int(top20_segments)} 个片段（{fmt_pct(pct(top20_segments, total_segments))}）**。最高对象《{top20[0]['title']}》单独产生 {fmt_int(top20[0]['segment_count'])} 个片段，其中 {fmt_pct(top20[0]['extremely_short_share_pct'])} 不超过 20 字符。"
        )
        report.append("")
        report.append("## 2. 切分粒度")
        report.append("")
        report.append(
            "极短片段的审阅阈值定为 ≤20 字符；同时在配套 CSV 中给出 ≤5、≤10、≤20、≤30 四档，避免阈值选择掩盖分布。"
        )
        report.append("")
        report.append("| 范围 | P25 | 中位数 | P75 | P90 | P95 | P99 | ≤20 字符数 | 比例 |")
        report.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        report.append(
            f"| 全部 | {all_length['p25_chars']} | {all_length['p50_chars']} | {all_length['p75_chars']} | {all_length['p90_chars']} | {all_length['p95_chars']} | {all_length['p99_chars']} | {fmt_int(all_length['le_20_count'])} | {fmt_pct(all_length['le_20_share_pct'])} |"
        )
        for group in ["webpage", "pdf", "csv", "other"]:
            row = group_lengths[group]
            report.append(
                f"| {FORMAT_GROUP_LABELS[group]} | {row['p25_chars']} | {row['p50_chars']} | {row['p75_chars']} | {row['p90_chars']} | {row['p95_chars']} | {row['p99_chars']} | {fmt_int(row['le_20_count'])} | {fmt_pct(row['le_20_share_pct'])} |"
            )
        report.append("")
        report.append(
            f"全部片段中，≤5 字符 {fmt_int(all_length['le_5_count'])} 个（{fmt_pct(all_length['le_5_share_pct'])}），≤10 字符 {fmt_int(all_length['le_10_count'])} 个（{fmt_pct(all_length['le_10_share_pct'])}），≤30 字符 {fmt_int(all_length['le_30_count'])} 个（{fmt_pct(all_length['le_30_share_pct'])}）。"
        )
        report.append("")
        report.append("当前记录语义如下：")
        report.append("")
        report.append("- 网页及 HTML 附件：标题与 `main` 中的 h/p/li/blockquote 元素，一元素一片段，属于段落/列表项级。")
        report.append("- ODT：h/p 元素，一块一片段，近似段落级。")
        report.append("- PDF：页面文本按换行拆分，locator 为 `page=N;block=M`；这是行/块，不是自然段。")
        report.append("- CSV：每一行一个片段，单元格按列序用 ` | ` 拼接，locator 为 `row=N`。")
        report.append("- ODS：每一非空行一个片段，仅拼接非空单元格；未保存工作表名和单元格坐标，空列位置可能丢失。")
        report.append("- PPTX：一张幻灯片内的段落/文本块一片段。当前没有按单元格独立存储的记录。")
        report.append("")
        report.append(
            f"网页 extractor 已移除 nav/footer/cookie banner，但仍保留 `{', '.join(sorted(webpage_boilerplate_terms))}` 这 4 类固定服务性文本，共 {fmt_int(boilerplate_count)} 个片段，占网页片段的 {fmt_pct(pct(boilerplate_count, group_rows['webpage']['segment_count']))}。这不是正文缺失，但会污染语言频率。"
        )
        report.append("")
        report.append("## 3. 12 个可读样例")
        report.append("")
        report.append(
            "下列“当前提取结果”未改写文字内容；`⟦片段边界⟧`仅为本报告加入的展示分隔符，PDF 内嵌控制字符以 `⟨U+XXXX⟩` 可视化。每个对象展示开头、中部、结尾窗口，完整内容仍在原数据库和原始文件中。"
        )
        report.append("")
        for row in sample_rows:
            report.append(
                f"### {row['sample_number']}. {row['title']}（{row['category']}）"
            )
            report.append("")
            report.append(
                f"来源：[{row['canonical_url']}]({row['canonical_url']})；对象 `{row['content_object_id']}`；{fmt_int(row['segment_count'])} 片段，极短片段 {fmt_pct(row['extremely_short_share_pct'])}。"
            )
            report.append("")
            for label, locator_key, text_key in [
                ("开头", "start_locator", "start_current_extraction"),
                ("中部", "middle_locator", "middle_current_extraction"),
                ("结尾", "end_locator", "end_current_extraction"),
            ]:
                report.append(
                    f"- **{label} · `{row[locator_key]}`**：{clip_markdown(row[text_key])}"
                )
            report.append("")
            report.append(
                f"审阅：{row['content_completeness_assessment']} {row['sequence_assessment']} {row['noise_assessment']} **建议：{row['review_recommendation']}**"
            )
            report.append("")
        report.append("完整样例窗口及原始路径见 [04_readable_samples.csv](04_readable_samples.csv)。")
        report.append("")
        report.append("## 4. 下载成功与正文价值不是同一件事")
        report.append("")
        report.append(
            "以下判断只使用现有文本量、对象关系和精确片段重合，不使用向量或模型。`附件为主`规则为附件字符数至少 1,000 且至少为网页的 3 倍；这是审阅优先级启发式，不是语义完整性证明。"
        )
        report.append("")
        report.append("| 正文位置判断 | 发布记录数 | 含义 |")
        report.append("|---|---:|---|")
        report.append(
            f"| 附件为主 | {body_class_counts['attachment_primary']} | 网页通常是摘要、说明或附件清单；正文主要在附件。 |"
        )
        report.append(
            f"| 网页为主 | {body_class_counts['webpage_primary']} | 网页文本明显多于附件，或没有实质附件文本。 |"
        )
        report.append(
            f"| 两者均有实质内容 | {body_class_counts['mixed_substantive']} | 网页与附件都需保留，不能只选其一。 |"
        )
        report.append(
            f"| 网页短文本/附件不可用 | {body_class_counts['webpage_short_or_attachment_unavailable']} | 只有短网页文本，附件不存在、未下载或未提取。 |"
        )
        report.append("")
        report.append(
            f"网页—附件重复采用保守的精确匹配：只比较长度 ≥40 的标准化片段，并以较小一侧的实质字符数为分母。共标出 **{duplicate_counts['possible_exact_overlap']} 个可能重合**，其中 **{duplicate_counts['high_confidence_exact_near_duplicate']} 个近完整精确重复**；这只能发现精确重合，不能排除改写、不同切分或版面差异造成的重复。"
        )
        report.append("")
        report.append("| 重复候选示例 | 较小一侧重合比例 | 精确共享片段 |")
        report.append("|---|---:|---:|")
        for row in duplicate_examples:
            report.append(
                f"| {clip_markdown(row['title'], 100)} | {fmt_pct(row['exact_overlap_pct_of_smaller_side'])} | {fmt_int(row['exact_shared_substantive_segments'])} |"
            )
        report.append("")
        report.append("未形成可用正文的对象如下：")
        report.append("")
        for row in failure_rows:
            report.append(
                f"- 下载状态 `{row['download_status']}` / 提取状态 `{row['extraction_status']}`：{fmt_int(row['object_count'])} 个对象。"
            )
        report.append("")
        report.append("逐发布记录的正文位置、附件成功数和重复候选见 [05_document_body_value.csv](05_document_body_value.csv)。")
        report.append("")
        report.append("## 5. 后续建议（本轮不执行）")
        report.append("")
        report.append("### 可直接用于后续文本处理")
        report.append("")
        report.append("- HTML/ODT 的段落级正文，保留标题和 locator；进入分析前排除固定 GOV.UK 服务性片段。")
        report.append("- 网页为主的 3 个发布记录，以及网页/附件均有实质内容的 20 个记录，可按对象关系保留两侧来源。")
        report.append("- 普通、叙述性 PDF 中短片段比例低且重复率低的对象，可把当前层作为证据源；下游按页合并相邻行后再生成分析文本。")
        report.append("")
        report.append("### 需要调整切分")
        report.append("")
        report.append("- PDF：从逐换行片段改为页内自然段/版面块，并保留原 `page/block` 到新片段的映射；优先处理前 20 个高片段对象。")
        report.append("- 长法案和长报告：分离正文、表格、目录、页眉页脚、修订记录；对高重复页眉/表头做标记而非删除原始层。")
        report.append("- 网页：给固定服务性标题增加 `boilerplate` 标记，避免其进入词频、主题或向量输入。")
        report.append("- CSV/ODS：保留列名、工作表名、单元格地址和空值位置；不要只用拼接后的行文本替代表结构。")
        report.append("")
        report.append("### 应保留但暂不纳入通用语言处理")
        report.append("")
        report.append("- CSV、ODS 及明显表格型 PDF：进入结构化/表格专用流程，而不是自然语言段落流程。")
        report.append("- 14 个 `needs_ocr` 对象、5 个不支持格式对象、2 个提取失败对象，以及 9 个下载失败/错误页对象。")
        report.append("- 《Draft Marine Bill》及河流流域 Annex B 等高碎片、高重复对象，在重切前只保留作证据，不进入向量化或模型分析。")
        report.append("")
        report.append("## 配套文件与完整性")
        report.append("")
        report.append("- [01_format_summary.csv](01_format_summary.csv)：四类汇总及实际格式明细。")
        report.append("- [02_top20_objects.csv](02_top20_objects.csv)：片段数最高 20 个对象。")
        report.append("- [03_segment_length_distribution.csv](03_segment_length_distribution.csv)：分位数、极短片段和记录模型。")
        report.append("- [04_readable_samples.csv](04_readable_samples.csv)：12 个对象的来源、位置、当前提取窗口和审阅判断。")
        report.append("- [05_document_body_value.csv](05_document_body_value.csv)：1,020 个发布记录的网页/附件正文位置与精确重合候选。")
        report.append("")
        report.append(f"输入数据库 SHA-256（读取前）：`{db_hash_before}`；原始文件数（读取前）：`{raw_count_before}`。")

        report_path = OUTPUT_DIR / "text_quality_report_for_dai.md"
        report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    finally:
        connection.close()

    db_hash_after = sha256_file(DATABASE_PATH)
    raw_count_after = sum(1 for path in RAW_DIR.rglob("*") if path.is_file())
    if db_hash_after != db_hash_before:
        raise RuntimeError("Read-only review unexpectedly changed the database hash")
    if raw_count_after != raw_count_before:
        raise RuntimeError("Read-only review unexpectedly changed the raw file count")

    report_path = OUTPUT_DIR / "text_quality_report_for_dai.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"读取后数据库 SHA-256：`{db_hash_after}`；原始文件数：`{raw_count_after}`。两项与读取前一致。\n"
        )

    print(f"Wrote report and 5 CSV files to {OUTPUT_DIR}")
    print(f"Database SHA-256 unchanged: {db_hash_after}")
    print(f"Raw file count unchanged: {raw_count_after}")


if __name__ == "__main__":
    main()
