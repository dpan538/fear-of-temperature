# ruff: noqa: E501

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from .cleaning import stable_id

SCHEMA_VERSION = "m1_database_pilot_v1"
NORMALISATION_RULE_VERSION = "govuk_metadata_v1"
NORMALISATION_RULES: dict[str, Any] = {
    "publisher_role": {
        "government_policy_source": "policy",
        "rule": "publishing function, not quoted speaker",
    },
    "publication_date": {
        "field": "first_published_at",
        "basis": "GOV.UK Content API first_published_at",
    },
    "update_date": {"field": "public_updated_at"},
    "document_identity": ["source_id", "Content API content_id"],
    "document_counting": "one unique content_id per document; organisation links do not duplicate documents",
    "organisation_counting": {
        "full": "one per linked organisation",
        "fractional": "1 / number of linked organisations",
    },
    "body_policy": "no body text imported while item rights and ethics route remain pending",
    "unknown_policy": "retain unknown or pending with a reason; do not infer confirmation",
}

SOURCE_SCOPE = (
    "GOV.UK policy_paper publication landing-page content items tagged to DEFRA and "
    "first published from 2026-07-01 through 2026-07-31 inclusive, as observed in the "
    "saved 2026-09-16 metadata snapshot"
)
DENOMINATOR_LIMIT = (
    "N=9 applies only when reproducing this exact source, organisation tag, content type, "
    "first-publication date field, inclusive window, document unit, and deduplication rule; "
    "it is not all DEFRA output, all UK policy, climate attention, or a passage denominator."
)


@dataclass(frozen=True)
class PilotBundle:
    selected_source: dict[str, str]
    checks: dict[str, Any]
    search_snapshot: dict[str, Any]
    metadata_snapshot: dict[str, Any]
    records: list[dict[str, Any]]
    search_snapshot_path: Path
    metadata_snapshot_path: Path
    source_register_path: Path
    checks_path: Path
    search_sha256: str
    metadata_sha256: str


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_versions (
    schema_version VARCHAR PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL,
    description VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS normalisation_rules (
    rule_version VARCHAR PRIMARY KEY,
    rule_sha256 VARCHAR NOT NULL,
    rules_json VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('active', 'superseded'))
);

CREATE TABLE IF NOT EXISTS sources (
    source_id VARCHAR PRIMARY KEY,
    source_name VARCHAR NOT NULL,
    publisher_role VARCHAR NOT NULL CHECK (publisher_role IN ('policy', 'media', 'public', 'unknown')),
    raw_role_label VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    access_method VARCHAR NOT NULL,
    actual_coverage VARCHAR NOT NULL,
    licence_status VARCHAR NOT NULL,
    licence_reason VARCHAR NOT NULL,
    ethics_status VARCHAR NOT NULL CHECK (ethics_status IN ('approved', 'exempt', 'pending', 'not_applicable', 'unknown')),
    ethics_reason VARCHAR NOT NULL,
    source_documentation_urls VARCHAR NOT NULL,
    local_source_register_path VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS collection_batches (
    batch_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES sources(source_id),
    accessed_at TIMESTAMPTZ NOT NULL,
    query_url VARCHAR NOT NULL,
    query_conditions_json VARCHAR NOT NULL,
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    date_filter_field VARCHAR NOT NULL,
    pagination_json VARCHAR NOT NULL,
    reported_total INTEGER NOT NULL,
    returned_count INTEGER NOT NULL,
    completeness_status VARCHAR NOT NULL,
    completeness_reason VARCHAR NOT NULL,
    search_snapshot_path VARCHAR NOT NULL,
    search_snapshot_sha256 VARCHAR NOT NULL,
    metadata_snapshot_path VARCHAR NOT NULL,
    metadata_snapshot_sha256 VARCHAR NOT NULL,
    research_sample BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS coverage_records (
    coverage_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL UNIQUE REFERENCES collection_batches(batch_id),
    coverage_unit VARCHAR NOT NULL,
    denominator_value INTEGER NOT NULL,
    actual_coverage VARCHAR NOT NULL,
    sampling_rule VARCHAR NOT NULL,
    denominator_scope_limit VARCHAR NOT NULL,
    completeness_status VARCHAR NOT NULL,
    channel_era_status VARCHAR NOT NULL,
    channel_era_reason VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_records (
    raw_record_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL REFERENCES collection_batches(batch_id),
    source_id VARCHAR NOT NULL REFERENCES sources(source_id),
    external_id VARCHAR NOT NULL,
    raw_payload_json VARCHAR NOT NULL,
    raw_payload_sha256 VARCHAR NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    source_artifact_path VARCHAR NOT NULL,
    validation_status VARCHAR NOT NULL,
    UNIQUE (batch_id, external_id, raw_payload_sha256)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES sources(source_id),
    external_id VARCHAR NOT NULL,
    canonical_url VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    publication_date DATE,
    publication_timestamp TIMESTAMPTZ,
    publication_date_basis VARCHAR NOT NULL,
    updated_timestamp TIMESTAMPTZ,
    collected_at TIMESTAMPTZ NOT NULL,
    publisher_role VARCHAR NOT NULL CHECK (publisher_role IN ('policy', 'media', 'public', 'unknown')),
    content_type VARCHAR NOT NULL,
    unit_type VARCHAR NOT NULL CHECK (unit_type IN ('document', 'post', 'comment', 'unknown')),
    parent_document_id VARCHAR REFERENCES documents(document_id),
    interaction_type VARCHAR NOT NULL,
    body_status VARCHAR NOT NULL,
    body_status_reason VARCHAR NOT NULL,
    deduplication_status VARCHAR NOT NULL,
    source_overlap_status VARCHAR NOT NULL,
    licence_status VARCHAR NOT NULL,
    ethics_status VARCHAR NOT NULL CHECK (ethics_status IN ('approved', 'exempt', 'pending', 'not_applicable', 'unknown')),
    ethics_reason VARCHAR NOT NULL,
    research_sample BOOLEAN NOT NULL,
    UNIQUE (source_id, external_id),
    UNIQUE (canonical_url)
);

CREATE TABLE IF NOT EXISTS document_versions (
    document_version_id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    normalisation_rule_version VARCHAR NOT NULL REFERENCES normalisation_rules(rule_version),
    raw_payload_sha256 VARCHAR NOT NULL,
    normalised_payload_json VARCHAR NOT NULL,
    normalised_payload_sha256 VARCHAR NOT NULL,
    normalised_at TIMESTAMPTZ NOT NULL,
    is_current BOOLEAN NOT NULL,
    UNIQUE (document_id, normalisation_rule_version, raw_payload_sha256)
);

CREATE TABLE IF NOT EXISTS document_version_raw_links (
    document_version_id VARCHAR NOT NULL REFERENCES document_versions(document_version_id),
    raw_record_id VARCHAR NOT NULL REFERENCES raw_records(raw_record_id),
    PRIMARY KEY (document_version_id, raw_record_id)
);

CREATE TABLE IF NOT EXISTS organisations (
    organisation_id VARCHAR PRIMARY KEY,
    external_id VARCHAR NOT NULL UNIQUE,
    organisation_name VARCHAR NOT NULL,
    canonical_url VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS document_organisations (
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    organisation_id VARCHAR NOT NULL REFERENCES organisations(organisation_id),
    association_type VARCHAR NOT NULL,
    lead_status VARCHAR NOT NULL CHECK (lead_status IN ('confirmed', 'not_lead', 'unknown', 'pending')),
    full_count_weight DOUBLE NOT NULL CHECK (full_count_weight = 1.0),
    fractional_count_weight DOUBLE NOT NULL CHECK (fractional_count_weight > 0 AND fractional_count_weight <= 1.0),
    allocation_status VARCHAR NOT NULL,
    PRIMARY KEY (document_id, organisation_id)
);

CREATE TABLE IF NOT EXISTS text_segments (
    segment_id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    parent_segment_id VARCHAR REFERENCES text_segments(segment_id),
    segment_kind VARCHAR NOT NULL CHECK (segment_kind IN ('paragraph', 'post_body', 'comment_body', 'quoted_block', 'unknown')),
    segment_order INTEGER NOT NULL CHECK (segment_order >= 0),
    segment_text VARCHAR NOT NULL,
    locator VARCHAR NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    text_sha256 VARCHAR NOT NULL,
    origin_kind VARCHAR NOT NULL CHECK (origin_kind IN ('acquired', 'synthetic_test')),
    permission_status VARCHAR NOT NULL,
    research_sample BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_attributions (
    attribution_id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    segment_id VARCHAR REFERENCES text_segments(segment_id),
    actor_name VARCHAR,
    attribution_role VARCHAR NOT NULL CHECK (attribution_role IN ('quoted_speaker', 'emotion_holder', 'reported_actor', 'unknown')),
    evidence_locator VARCHAR,
    status VARCHAR NOT NULL CHECK (status IN ('confirmed', 'pending', 'unknown'))
);

CREATE TABLE IF NOT EXISTS document_relationships (
    relationship_id VARCHAR PRIMARY KEY,
    from_document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    to_document_id VARCHAR NOT NULL REFERENCES documents(document_id),
    relationship_type VARCHAR NOT NULL CHECK (relationship_type IN ('exact_duplicate', 'near_duplicate', 'source_overlap', 'quote', 'repost', 'reply', 'unknown')),
    evidence_status VARCHAR NOT NULL CHECK (evidence_status IN ('confirmed', 'pending', 'unknown')),
    evidence_note VARCHAR NOT NULL,
    rule_version VARCHAR NOT NULL
);
"""


EXPORT_QUERIES: dict[str, str] = {
    "schema_versions": "SELECT * FROM schema_versions ORDER BY schema_version",
    "normalisation_rules": "SELECT * FROM normalisation_rules ORDER BY rule_version",
    "sources": "SELECT * FROM sources ORDER BY source_id",
    "collection_batches": "SELECT * FROM collection_batches ORDER BY batch_id",
    "coverage_records": "SELECT * FROM coverage_records ORDER BY coverage_id",
    "raw_records": "SELECT * FROM raw_records ORDER BY raw_record_id",
    "documents": "SELECT * FROM documents ORDER BY publication_timestamp, document_id",
    "document_versions": "SELECT * FROM document_versions ORDER BY document_id, document_version_id",
    "document_version_raw_links": (
        "SELECT * FROM document_version_raw_links ORDER BY document_version_id, raw_record_id"
    ),
    "organisations": "SELECT * FROM organisations ORDER BY organisation_name, organisation_id",
    "document_organisations": (
        "SELECT d.document_id, d.title, o.organisation_id, o.organisation_name, "
        "r.association_type, r.lead_status, r.full_count_weight, r.fractional_count_weight, "
        "r.allocation_status FROM document_organisations r "
        "JOIN documents d USING (document_id) JOIN organisations o USING (organisation_id) "
        "ORDER BY d.publication_timestamp, d.document_id, o.organisation_name"
    ),
    "text_segments": "SELECT * FROM text_segments ORDER BY document_id, segment_order, segment_id",
    "voice_attributions": "SELECT * FROM voice_attributions ORDER BY document_id, attribution_id",
    "document_relationships": (
        "SELECT * FROM document_relationships ORDER BY from_document_id, to_document_id, relationship_id"
    ),
    "traceability": (
        "SELECT d.document_id, d.external_id, d.title, d.publication_date, "
        "d.publication_timestamp, "
        "dv.document_version_id, dv.normalisation_rule_version, rr.raw_record_id, "
        "rr.raw_payload_sha256, b.batch_id, b.query_url, b.accessed_at, s.source_id, "
        "s.publisher_role, d.body_status, d.ethics_status "
        "FROM documents d JOIN document_versions dv ON dv.document_id = d.document_id "
        "AND dv.is_current JOIN document_version_raw_links l USING (document_version_id) "
        "JOIN raw_records rr USING (raw_record_id) JOIN collection_batches b USING (batch_id) "
        "JOIN sources s ON s.source_id = d.source_id "
        "ORDER BY d.publication_timestamp, d.document_id, rr.raw_record_id"
    ),
    "institution_counting": (
        "SELECT o.organisation_id, o.organisation_name, COUNT(*) AS linked_document_count, "
        "SUM(r.full_count_weight) AS full_count, "
        "SUM(r.fractional_count_weight) AS fractional_count "
        "FROM document_organisations r JOIN organisations o USING (organisation_id) "
        "GROUP BY o.organisation_id, o.organisation_name ORDER BY o.organisation_name"
    ),
}


TABLE_PURPOSES = {
    "schema_versions": "数据库结构版本；不是研究数据版本。",
    "normalisation_rules": "可核验的字段映射与计数规则版本。",
    "sources": "来源登记：角色、访问、覆盖、许可、伦理与文档依据。",
    "collection_batches": "一次有界查询及其时间窗、分页、数量和证据快照。",
    "coverage_records": "批次对应的分母单位、范围限制及完整性/渠道状态。",
    "raw_records": "原始保存元数据的不可变版本及逐记录校验值。",
    "documents": "当前规范化文档/帖子/评论接口；本轮仅含真实 policy documents。",
    "document_versions": "原始内容或规范化规则变化时新增的规范化版本。",
    "document_version_raw_links": "规范化版本到原始记录的多对多追溯边。",
    "organisations": "发布页面关联的机构实体。",
    "document_organisations": "文档—机构多对多关系以及完整/分数计数权重。",
    "text_segments": "段落/正文接口；本轮真实数据库为空，不伪造正文。",
    "voice_attributions": "引用说话者、情绪持有者等接口；与 publisher_role 分离。",
    "document_relationships": "重复、来源重叠、引用、回复与转发关系接口。",
}


FIELD_DESCRIPTIONS = {
    "source_id": "由规范化角色和来源名称生成的稳定 ID。",
    "publisher_role": "按发布功能定义的 policy/media/public/unknown；不是被引用说话者。",
    "raw_role_label": "来源登记表中的原始角色标签，保留映射前证据。",
    "content_type": "来源或文档内容类型；本轮为 policy_paper。",
    "access_method": "实际使用或核验的访问路径。",
    "actual_coverage": "实测范围，不外推到完整历史或总体。",
    "licence_status": "许可审核状态；pending 不等于拒绝或批准。",
    "licence_reason": "许可状态的依据与未决条件。",
    "ethics_status": "approved/exempt/pending/not_applicable/unknown；不得凭公开可访问改成 approved。",
    "ethics_reason": "伦理状态的可审计原因。",
    "source_documentation_urls": "API、条款和许可文档链接的 JSON 数组。",
    "local_source_register_path": "本地来源登记表相对路径。",
    "batch_id": "由来源、查询、采集时间和快照校验值生成的稳定批次 ID。",
    "accessed_at": "API/网页元数据的采集时间，不是发布日期。",
    "query_url": "本批次的有界查询 URL。",
    "query_conditions_json": "机构、类型、日期字段和筛选规则。",
    "window_start": "查询时间窗起点（inclusive）。",
    "window_end": "查询时间窗终点（inclusive）。",
    "date_filter_field": "用于筛选时间窗的来源字段。",
    "pagination_json": "分页 URL、页数和集合一致性证据。",
    "reported_total": "来源接口报告的数量。",
    "returned_count": "保存并核验的返回记录数。",
    "completeness_status": "只针对明示范围的完整性状态。",
    "completeness_reason": "支持完整性状态的证据。",
    "search_snapshot_path": "保存的 Search API 最小证据快照。",
    "search_snapshot_sha256": "Search API 快照 SHA-256。",
    "metadata_snapshot_path": "保存的逐项 Content API 元数据快照。",
    "metadata_snapshot_sha256": "Content API 元数据快照 SHA-256。",
    "research_sample": "是否计入研究样本/覆盖统计；合成接口必须为 false。",
    "coverage_id": "覆盖记录稳定 ID。",
    "coverage_unit": "分母单位；本轮是唯一 publication landing-page document。",
    "denominator_value": "仅在同范围、同单位、同筛选和同去重规则下有效的分母。",
    "sampling_rule": "纳入与去重规则。",
    "denominator_scope_limit": "防止把 9 外推成 DEFRA/英国政策/气候关注度总体。",
    "channel_era_status": "历史渠道连续性审核状态。",
    "channel_era_reason": "渠道/年代覆盖未决原因。",
    "raw_record_id": "批次、外部 ID 和原始载荷哈希生成的不可变 ID。",
    "external_id": "来源系统 ID；本轮为 GOV.UK content_id。",
    "raw_payload_json": "原样字段的规范 JSON 序列化，不含正文。",
    "raw_payload_sha256": "单条原始载荷的 SHA-256；变化会产生新版本。",
    "acquired_at": "该原始记录被观察的时间。",
    "source_artifact_path": "原始记录来自的本地证据文件。",
    "validation_status": "导入前字段/范围核验状态。",
    "document_id": "source_id + external_id 生成的跨重建稳定文档 ID。",
    "canonical_url": "来源规范 URL。",
    "title": "规范化标题。",
    "language": "记录语言；unknown 时保留 unknown。",
    "publication_timestamp": "首次发布时间；缺失时为 NULL，不以更新时间代填。",
    "publication_date": "来源时间戳中的日历日期；用于时间窗核验，避免运行机器时区改变日期。",
    "publication_date_basis": "publication_timestamp 的来源字段与核验依据。",
    "updated_timestamp": "公开更新时间，与首次发布时间和采集时间分离。",
    "collected_at": "元数据采集时间。",
    "unit_type": "document/post/comment/unknown，预留公众主帖与评论分离。",
    "parent_document_id": "评论/回复等父项；本轮 policy documents 为 NULL。",
    "interaction_type": "original/reply/quote/repost/unknown；本轮为 original。",
    "body_status": "正文是否取得及可处理状态。",
    "body_status_reason": "正文未采集或不可用的原因。",
    "deduplication_status": "文档去重核验边界；不把无正文误写成内容去重。",
    "source_overlap_status": "跨来源重叠检查状态。",
    "document_version_id": "文档 + 原始载荷哈希 + 规则版本生成的规范化版本 ID。",
    "normalisation_rule_version": "产生此记录的字段规范版本。",
    "normalised_payload_json": "决定当前文档字段的规范化载荷。",
    "normalised_payload_sha256": "规范化载荷 SHA-256。",
    "normalised_at": "本批证据进入规范结构的可重复时间戳（采用证据采集时间）。",
    "is_current": "同一文档目前采用的规范化版本。",
    "rule_version": "规则的语义版本标识。",
    "rule_sha256": "规则 JSON 的 SHA-256；同名规则变更会被拒绝。",
    "rules_json": "可机读规范化规则。",
    "status": "当前状态；含义由所属表限定。",
    "organisation_id": "来源机构稳定 ID。",
    "organisation_name": "来源记录中的机构名称。",
    "association_type": "机构与文档的关系；本轮仅确认 GOV.UK tagged organisation。",
    "lead_status": "lead/emphasised 机构未核验时为 unknown。",
    "full_count_weight": "分机构完整计数权重；每条关联为 1。",
    "fractional_count_weight": "跨机构汇总的分数计数候选权重；每文档关联权重和为 1。",
    "allocation_status": "计数规则是否已批准；本轮两种权重仅供明确选择，不做机构统计。",
    "segment_id": "文档内文本段稳定 ID。",
    "parent_segment_id": "嵌套引用等父段 ID。",
    "segment_kind": "paragraph/post_body/comment_body/quoted_block/unknown。",
    "segment_order": "父文档内零起始顺序。",
    "segment_text": "合法取得的段落文本；本轮不填。",
    "locator": "段落在来源中的 CSS/XPath/页码/字符范围等定位。",
    "start_char": "可选的父文本起始字符位置。",
    "end_char": "可选的父文本结束字符位置。",
    "text_sha256": "原段落文本 SHA-256。",
    "origin_kind": "acquired 或 synthetic_test；合成文本不得计入研究样本。",
    "permission_status": "该文本可处理/存储状态。",
    "created_at": "段落记录建立时间。",
    "attribution_id": "声音归因稳定 ID。",
    "actor_name": "来源明确给出的说话者/持有者；不推断身份。",
    "attribution_role": "quoted_speaker/emotion_holder/reported_actor/unknown。",
    "evidence_locator": "支持归因的文本位置。",
    "relationship_id": "文档关系稳定 ID。",
    "from_document_id": "关系起点文档。",
    "to_document_id": "关系终点文档。",
    "relationship_type": "duplicate/overlap/quote/repost/reply 等明确类型。",
    "evidence_status": "关系证据确认状态。",
    "evidence_note": "关系判定证据或未决原因。",
    "schema_version": "数据库结构版本。",
    "recorded_at": "结构版本记录时间。",
    "description": "该版本/对象的简短说明。",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _relative(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def load_pilot_bundle(feasibility_dir: str | Path) -> PilotBundle:
    root = Path(feasibility_dir).resolve()
    checks_path = root / "checks.json"
    source_register_path = root / "source_access_register.csv"
    search_snapshot_path = root / "evidence/search_index_snapshot.json"
    metadata_snapshot_path = root / "evidence/content_metadata_snapshot.json"

    checks = json.loads(checks_path.read_text(encoding="utf-8"))
    search_snapshot = json.loads(search_snapshot_path.read_text(encoding="utf-8"))
    metadata_snapshot = json.loads(metadata_snapshot_path.read_text(encoding="utf-8"))
    with source_register_path.open(encoding="utf-8", newline="") as handle:
        selected_rows = [row for row in csv.DictReader(handle) if row["selected"].lower() == "true"]
    if len(selected_rows) != 1:
        raise ValueError(f"Expected exactly one selected source, found {len(selected_rows)}")

    search_sha = _sha256_file(search_snapshot_path)
    metadata_sha = _sha256_file(metadata_snapshot_path)
    expected_search_sha = checks["evidence_files"][search_snapshot_path.name]["sha256"]
    expected_metadata_sha = checks["evidence_files"][metadata_snapshot_path.name]["sha256"]
    if search_sha != expected_search_sha or metadata_sha != expected_metadata_sha:
        raise ValueError(
            "Saved evidence SHA-256 does not match checks.json; refresh checks before import"
        )

    records = metadata_snapshot.get("records")
    if not isinstance(records, list):
        raise ValueError("content_metadata_snapshot.json records must be a list")
    expected_count = checks["selected_query"]["content_api_records_verified"]
    if len(records) != expected_count:
        raise ValueError(f"Expected {expected_count} metadata records, found {len(records)}")
    if metadata_snapshot.get("accessed_at") != checks["run"]["accessed_at"]:
        raise ValueError("Metadata snapshot and checks.json acquisition timestamps differ")

    return PilotBundle(
        selected_source=selected_rows[0],
        checks=checks,
        search_snapshot=search_snapshot,
        metadata_snapshot=metadata_snapshot,
        records=records,
        search_snapshot_path=search_snapshot_path,
        metadata_snapshot_path=metadata_snapshot_path,
        source_register_path=source_register_path,
        checks_path=checks_path,
        search_sha256=search_sha,
        metadata_sha256=metadata_sha,
    )


def _create_schema(connection: duckdb.DuckDBPyConnection, *, recorded_at: datetime) -> None:
    connection.execute(SCHEMA_SQL)
    _upsert(
        connection,
        "schema_versions",
        ["schema_version"],
        {
            "schema_version": SCHEMA_VERSION,
            "recorded_at": recorded_at,
            "description": "Minimal source-to-document pilot with versioned provenance and empty text interfaces",
        },
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW current_document_traceability AS
        SELECT d.document_id, d.external_id, d.title, dv.document_version_id,
               rr.raw_record_id, rr.raw_payload_sha256, b.batch_id, b.query_url,
               b.accessed_at, d.body_status, d.ethics_status
        FROM documents d
        JOIN document_versions dv ON dv.document_id = d.document_id AND dv.is_current
        JOIN document_version_raw_links l USING (document_version_id)
        JOIN raw_records rr USING (raw_record_id)
        JOIN collection_batches b USING (batch_id)
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE VIEW embedding_ready_segments AS
        SELECT ts.*
        FROM text_segments ts
        JOIN documents d USING (document_id)
        WHERE ts.research_sample
          AND d.research_sample
          AND ts.origin_kind = 'acquired'
          AND ts.permission_status IN ('approved', 'permitted')
        """
    )


def _upsert(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    key_columns: Sequence[str],
    row: dict[str, Any],
) -> None:
    columns = list(row)
    placeholders = ", ".join("?" for _ in columns)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({', '.join(key_columns)}) DO NOTHING"
    )
    connection.execute(sql, [row[column] for column in columns])


def _register_rule(
    connection: duckdb.DuckDBPyConnection,
    rule_version: str,
    rules: dict[str, Any],
) -> str:
    rules_json = _canonical_json(rules)
    rule_sha = _sha256_bytes(rules_json.encode("utf-8"))
    existing = connection.execute(
        "SELECT rule_sha256 FROM normalisation_rules WHERE rule_version = ?", [rule_version]
    ).fetchone()
    if existing and existing[0] != rule_sha:
        raise ValueError(
            f"Normalisation rule {rule_version!r} changed without a new version identifier"
        )
    _upsert(
        connection,
        "normalisation_rules",
        ["rule_version"],
        {
            "rule_version": rule_version,
            "rule_sha256": rule_sha,
            "rules_json": rules_json,
            "status": "active",
        },
    )
    return rule_sha


def ingest_pilot_bundle(
    connection: duckdb.DuckDBPyConnection,
    bundle: PilotBundle,
    *,
    project_root: str | Path,
    rule_version: str = NORMALISATION_RULE_VERSION,
    rules: dict[str, Any] | None = None,
) -> dict[str, str]:
    project = Path(project_root).resolve()
    accessed_at = _parse_timestamp(bundle.checks["run"]["accessed_at"])
    if accessed_at is None:
        raise ValueError("checks.json run.accessed_at is required")
    _create_schema(connection, recorded_at=accessed_at)
    rule_payload = rules or NORMALISATION_RULES
    rule_sha = _register_rule(connection, rule_version, rule_payload)

    source = bundle.selected_source
    source_name = source["source_name"]
    source_id = stable_id("src", "policy", source_name)
    source_docs = [value.strip() for value in source["official_documentation"].split("|")]
    source_docs.extend(
        [
            "https://www.gov.uk/help/terms-conditions",
            "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        ]
    )
    _upsert(
        connection,
        "sources",
        ["source_id"],
        {
            "source_id": source_id,
            "source_name": source_name,
            "publisher_role": "policy",
            "raw_role_label": source["source_role"],
            "content_type": source["document_type"],
            "access_method": source["retrieval_route"],
            "actual_coverage": SOURCE_SCOPE,
            "licence_status": "pending_item_and_attachment_review",
            "licence_reason": source["storage_redistribution"],
            "ethics_status": "pending",
            "ethics_reason": (
                "No verifiable approval or exemption was found in the reviewed project record; "
                "this pilot stores metadata only and does not claim clearance for body use."
            ),
            "source_documentation_urls": _canonical_json(source_docs),
            "local_source_register_path": _relative(bundle.source_register_path, project),
        },
    )

    query_url = bundle.checks["selected_query"]["url"]
    batch_id = stable_id(
        "bat", source_id, query_url, accessed_at.isoformat(), bundle.metadata_sha256
    )
    query_conditions = {
        "organisation_slug": "department-for-environment-food-rural-affairs",
        "content_store_document_type": "policy_paper",
        "date_field": bundle.checks["window"]["date_field"],
        "window_start": bundle.checks["window"]["start"],
        "window_end": bundle.checks["window"]["end"],
        "inclusive": bundle.checks["window"]["inclusive"],
        "selection_is_topic_independent": True,
        "deduplication_keys": ["Content API content_id", "canonical_url"],
    }
    pagination = bundle.checks["pagination_check"]
    _upsert(
        connection,
        "collection_batches",
        ["batch_id"],
        {
            "batch_id": batch_id,
            "source_id": source_id,
            "accessed_at": accessed_at,
            "query_url": query_url,
            "query_conditions_json": _canonical_json(query_conditions),
            "window_start": date.fromisoformat(bundle.checks["window"]["start"]),
            "window_end": date.fromisoformat(bundle.checks["window"]["end"]),
            "date_filter_field": bundle.checks["window"]["date_field"],
            "pagination_json": _canonical_json(pagination),
            "reported_total": bundle.checks["selected_query"]["reported_total"],
            "returned_count": bundle.checks["selected_query"]["returned_count"],
            "completeness_status": "bounded_complete_list_verified",
            "completeness_reason": (
                "Search API total and returned count are 9; independent 5+4 pagination union "
                "matches the full set; 9 Content API records were verified."
            ),
            "search_snapshot_path": _relative(bundle.search_snapshot_path, project),
            "search_snapshot_sha256": bundle.search_sha256,
            "metadata_snapshot_path": _relative(bundle.metadata_snapshot_path, project),
            "metadata_snapshot_sha256": bundle.metadata_sha256,
            "research_sample": True,
        },
    )
    coverage_id = stable_id("cov", batch_id, "document")
    _upsert(
        connection,
        "coverage_records",
        ["coverage_id"],
        {
            "coverage_id": coverage_id,
            "batch_id": batch_id,
            "coverage_unit": "unique GOV.UK publication landing-page document",
            "denominator_value": 9,
            "actual_coverage": SOURCE_SCOPE,
            "sampling_rule": (
                "Complete enumeration within the bounded query; one document per unique Content "
                "API content_id; all organisation links retained without duplicating documents."
            ),
            "denominator_scope_limit": DENOMINATOR_LIMIT,
            "completeness_status": "bounded_complete_list_verified",
            "channel_era_status": "unknown",
            "channel_era_reason": (
                "One July 2026 snapshot does not establish the historical start, stability, or "
                "comparability of GOV.UK channels across 1988-2026."
            ),
        },
    )

    for record in bundle.records:
        external_id = str(record.get("content_id") or "").strip()
        if not external_id:
            raise ValueError("Every saved Content API metadata record requires content_id")
        raw_json = _canonical_json(record)
        raw_sha = _sha256_bytes(raw_json.encode("utf-8"))
        raw_record_id = stable_id("raw", batch_id, external_id, raw_sha)
        _upsert(
            connection,
            "raw_records",
            ["raw_record_id"],
            {
                "raw_record_id": raw_record_id,
                "batch_id": batch_id,
                "source_id": source_id,
                "external_id": external_id,
                "raw_payload_json": raw_json,
                "raw_payload_sha256": raw_sha,
                "acquired_at": accessed_at,
                "source_artifact_path": _relative(bundle.metadata_snapshot_path, project),
                "validation_status": "metadata_fields_and_bounded_scope_verified",
            },
        )

        publication_timestamp = _parse_timestamp(record.get("first_published_at"))
        updated_timestamp = _parse_timestamp(record.get("public_updated_at"))
        canonical_url = str(record.get("canonical_url") or "").strip()
        title = str(record.get("title") or "").strip()
        if not canonical_url or not title:
            raise ValueError(f"Record {external_id} is missing canonical_url or title")
        document_id = stable_id("doc", source_id, external_id)
        normalised_payload = {
            "document_id": document_id,
            "source_id": source_id,
            "external_id": external_id,
            "canonical_url": canonical_url,
            "title": title,
            "language": "en",
            "publication_date": record["first_published_at"][:10]
            if record.get("first_published_at")
            else None,
            "publication_timestamp": publication_timestamp.isoformat()
            if publication_timestamp
            else None,
            "publication_date_basis": "GOV.UK Content API first_published_at",
            "updated_timestamp": updated_timestamp.isoformat() if updated_timestamp else None,
            "publisher_role": "policy",
            "content_type": str(record.get("document_type") or "unknown"),
            "unit_type": "document",
            "interaction_type": "original",
            "body_status": "not_collected",
            "licence_status": "pending_item_and_attachment_review",
            "ethics_status": "pending",
        }
        normalised_json = _canonical_json(normalised_payload)
        normalised_sha = _sha256_bytes(normalised_json.encode("utf-8"))
        document_version_id = stable_id("docv", document_id, raw_sha, rule_version, rule_sha)
        _upsert(
            connection,
            "documents",
            ["document_id"],
            {
                **normalised_payload,
                "publication_timestamp": publication_timestamp,
                "updated_timestamp": updated_timestamp,
                "collected_at": accessed_at,
                "parent_document_id": None,
                "body_status_reason": (
                    "The saved M1 evidence is metadata-only; body and attachments await item-level "
                    "rights review and a documented ethics route."
                ),
                "deduplication_status": "content_id_and_canonical_url_unique_within_batch",
                "source_overlap_status": "unknown_not_checked_without_cross_source_corpus",
                "ethics_reason": (
                    "Metadata-only pilot; no documented approval or exemption was found for "
                    "substantive body use."
                ),
                "research_sample": True,
            },
        )
        connection.execute(
            "UPDATE document_versions SET is_current = false "
            "WHERE document_id = ? AND document_version_id <> ?",
            [document_id, document_version_id],
        )
        _upsert(
            connection,
            "document_versions",
            ["document_version_id"],
            {
                "document_version_id": document_version_id,
                "document_id": document_id,
                "normalisation_rule_version": rule_version,
                "raw_payload_sha256": raw_sha,
                "normalised_payload_json": normalised_json,
                "normalised_payload_sha256": normalised_sha,
                "normalised_at": accessed_at,
                "is_current": True,
            },
        )
        _upsert(
            connection,
            "document_version_raw_links",
            ["document_version_id", "raw_record_id"],
            {"document_version_id": document_version_id, "raw_record_id": raw_record_id},
        )

        organisations = record.get("organisations") or []
        if not organisations:
            raise ValueError(f"Record {external_id} has no saved organisation links")
        fractional_weight = 1.0 / len(organisations)
        for organisation in organisations:
            organisation_external_id = str(organisation.get("content_id") or "").strip()
            organisation_name = str(organisation.get("title") or "").strip()
            base_path = str(organisation.get("base_path") or "").strip()
            if not organisation_external_id or not organisation_name or not base_path:
                raise ValueError(f"Record {external_id} has an incomplete organisation link")
            organisation_id = stable_id("org", "govuk", organisation_external_id)
            _upsert(
                connection,
                "organisations",
                ["organisation_id"],
                {
                    "organisation_id": organisation_id,
                    "external_id": organisation_external_id,
                    "organisation_name": organisation_name,
                    "canonical_url": f"https://www.gov.uk{base_path}",
                },
            )
            _upsert(
                connection,
                "document_organisations",
                ["document_id", "organisation_id"],
                {
                    "document_id": document_id,
                    "organisation_id": organisation_id,
                    "association_type": "govuk_tagged_organisation",
                    "lead_status": "unknown",
                    "full_count_weight": 1.0,
                    "fractional_count_weight": fractional_weight,
                    "allocation_status": (
                        "both_weights_recorded_but_institutional_aggregation_rule_pending"
                    ),
                },
            )

    return {"source_id": source_id, "batch_id": batch_id, "rule_sha256": rule_sha}


def _scalar(connection: duckdb.DuckDBPyConnection, sql: str) -> Any:
    row = connection.execute(sql).fetchone()
    return row[0] if row else None


def _table_counts(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    tables = [
        "sources",
        "collection_batches",
        "coverage_records",
        "raw_records",
        "documents",
        "document_versions",
        "document_version_raw_links",
        "organisations",
        "document_organisations",
        "text_segments",
        "voice_attributions",
        "document_relationships",
    ]
    return {table: int(_scalar(connection, f"SELECT COUNT(*) FROM {table}")) for table in tables}


def validate_database(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, observed: Any, expected: Any, note: str) -> None:
        checks.append(
            {
                "name": name,
                "observed": observed,
                "expected": expected,
                "passed": observed == expected,
                "note": note,
            }
        )

    add(
        "unique_research_documents",
        _scalar(connection, "SELECT COUNT(*) FROM documents WHERE research_sample"),
        9,
        "Organisation links must not inflate the document denominator.",
    )
    add(
        "distinct_document_ids",
        _scalar(connection, "SELECT COUNT(DISTINCT document_id) FROM documents"),
        9,
        "Stable IDs remain unique.",
    )
    add(
        "raw_records",
        _scalar(connection, "SELECT COUNT(*) FROM raw_records"),
        9,
        "One saved Content API metadata record per item in this batch.",
    )
    add(
        "current_document_versions",
        _scalar(connection, "SELECT COUNT(*) FROM document_versions WHERE is_current"),
        9,
        "Every document has one current normalised version.",
    )
    add(
        "traceable_documents",
        _scalar(
            connection, "SELECT COUNT(DISTINCT document_id) FROM current_document_traceability"
        ),
        9,
        "Current documents trace to raw records and the collection batch.",
    )
    add(
        "multi_organisation_documents",
        _scalar(
            connection,
            "SELECT COUNT(*) FROM (SELECT document_id FROM document_organisations GROUP BY document_id HAVING COUNT(*) > 1)",
        ),
        3,
        "Matches the saved M1 check.",
    )
    add(
        "document_organisation_links",
        _scalar(connection, "SELECT COUNT(*) FROM document_organisations"),
        14,
        "All six organisations and all document links are retained.",
    )
    add(
        "full_count_weight_sum",
        float(_scalar(connection, "SELECT SUM(full_count_weight) FROM document_organisations")),
        14.0,
        "Full counting counts every institution link.",
    )
    add(
        "fractional_weight_sum",
        round(
            float(
                _scalar(
                    connection, "SELECT SUM(fractional_count_weight) FROM document_organisations"
                )
            ),
            10,
        ),
        9.0,
        "Fractional weights sum to the nine unique documents.",
    )
    add(
        "missing_first_publication_dates",
        _scalar(connection, "SELECT COUNT(*) FROM documents WHERE publication_timestamp IS NULL"),
        0,
        "Unknown dates would remain NULL rather than borrowing update dates.",
    )
    add(
        "wrong_date_basis",
        _scalar(
            connection,
            "SELECT COUNT(*) FROM documents WHERE publication_date_basis <> 'GOV.UK Content API first_published_at'",
        ),
        0,
        "Search public_timestamp is not used as first publication.",
    )
    add(
        "dates_outside_window",
        _scalar(
            connection,
            "SELECT COUNT(*) FROM documents WHERE publication_date NOT BETWEEN DATE '2026-07-01' AND DATE '2026-07-31'",
        ),
        0,
        "All documents match the bounded first-publication window.",
    )
    add(
        "null_titles_or_urls",
        _scalar(
            connection,
            "SELECT COUNT(*) FROM documents WHERE title IS NULL OR title = '' OR canonical_url IS NULL OR canonical_url = ''",
        ),
        0,
        "Required inspection fields are populated.",
    )
    add(
        "duplicate_external_ids",
        _scalar(connection, "SELECT COUNT(*) - COUNT(DISTINCT external_id) FROM documents"),
        0,
        "No duplicate source IDs.",
    )
    add(
        "duplicate_urls",
        _scalar(connection, "SELECT COUNT(*) - COUNT(DISTINCT canonical_url) FROM documents"),
        0,
        "No duplicate canonical URLs.",
    )
    add(
        "coverage_denominator",
        _scalar(connection, "SELECT denominator_value FROM coverage_records"),
        9,
        "Only the exact bounded query may reuse this denominator.",
    )
    add(
        "real_text_segments",
        _scalar(connection, "SELECT COUNT(*) FROM text_segments WHERE origin_kind = 'acquired'"),
        0,
        "No unapproved body text is invented or collected.",
    )
    add(
        "all_text_segments",
        _scalar(connection, "SELECT COUNT(*) FROM text_segments"),
        0,
        "The paragraph interface is present but empty in the research database.",
    )
    add(
        "embedding_ready_segments",
        _scalar(connection, "SELECT COUNT(*) FROM embedding_ready_segments"),
        0,
        "No real text is eligible for vectors yet.",
    )
    add(
        "non_pending_source_ethics",
        _scalar(connection, "SELECT COUNT(*) FROM sources WHERE ethics_status <> 'pending'"),
        0,
        "No approval or exemption is invented.",
    )
    add(
        "non_pending_document_ethics",
        _scalar(connection, "SELECT COUNT(*) FROM documents WHERE ethics_status <> 'pending'"),
        0,
        "All human-language records retain the pending gate.",
    )

    foreign_key_orphans = int(
        _scalar(
            connection,
            """
            SELECT
              (SELECT COUNT(*) FROM collection_batches b LEFT JOIN sources s USING (source_id) WHERE s.source_id IS NULL) +
              (SELECT COUNT(*) FROM coverage_records c LEFT JOIN collection_batches b USING (batch_id) WHERE b.batch_id IS NULL) +
              (SELECT COUNT(*) FROM raw_records r LEFT JOIN collection_batches b USING (batch_id) WHERE b.batch_id IS NULL) +
              (SELECT COUNT(*) FROM documents d LEFT JOIN sources s USING (source_id) WHERE s.source_id IS NULL) +
              (SELECT COUNT(*) FROM document_versions v LEFT JOIN documents d USING (document_id) WHERE d.document_id IS NULL) +
              (SELECT COUNT(*) FROM document_version_raw_links l LEFT JOIN document_versions v USING (document_version_id) WHERE v.document_version_id IS NULL) +
              (SELECT COUNT(*) FROM document_version_raw_links l LEFT JOIN raw_records r USING (raw_record_id) WHERE r.raw_record_id IS NULL) +
              (SELECT COUNT(*) FROM document_organisations x LEFT JOIN documents d USING (document_id) WHERE d.document_id IS NULL) +
              (SELECT COUNT(*) FROM document_organisations x LEFT JOIN organisations o USING (organisation_id) WHERE o.organisation_id IS NULL)
            """,
        )
    )
    add(
        "foreign_key_orphans",
        foreign_key_orphans,
        0,
        "Manual orphan audit complements enforced database constraints.",
    )
    return {
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "table_counts": _table_counts(connection),
    }


def _normalise_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _query_payload(connection: duckdb.DuckDBPyConnection, query: str) -> dict[str, Any]:
    # TIMESTAMPTZ is an instant, but DuckDB renders it in the session timezone.
    # UTC keeps CSVs and logical fingerprints stable across rebuild machines.
    connection.execute("SET TimeZone = 'UTC'")
    cursor = connection.execute(query)
    columns = [item[0] for item in cursor.description]
    rows = [[_normalise_cell(value) for value in row] for row in cursor.fetchall()]
    return {"columns": columns, "rows": rows}


def logical_fingerprint(connection: duckdb.DuckDBPyConnection) -> str:
    payload = {name: _query_payload(connection, query) for name, query in EXPORT_QUERIES.items()}
    return _sha256_bytes(_canonical_json(payload).encode("utf-8"))


def _write_csv(path: Path, columns: Iterable[str], rows: Iterable[Sequence[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def export_database(
    connection: duckdb.DuckDBPyConnection, exports_dir: str | Path
) -> dict[str, dict[str, Any]]:
    target = Path(exports_dir)
    target.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, Any]] = {}
    for name, query in EXPORT_QUERIES.items():
        payload = _query_payload(connection, query)
        path = target / f"{name}.csv"
        _write_csv(path, payload["columns"], payload["rows"])
        manifest[path.name] = {
            "rows": len(payload["rows"]),
            "sha256": _sha256_file(path),
        }
    return manifest


def export_data_dictionary(connection: duckdb.DuckDBPyConnection, destination: str | Path) -> None:
    rows = connection.execute(
        """
        SELECT table_name, column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'main'
          AND table_name IN (
            'schema_versions', 'normalisation_rules', 'sources', 'collection_batches',
            'coverage_records', 'raw_records', 'documents', 'document_versions',
            'document_version_raw_links', 'organisations', 'document_organisations',
            'text_segments', 'voice_attributions', 'document_relationships'
          )
        ORDER BY table_name, ordinal_position
        """
    ).fetchall()
    output_rows = []
    for table_name, column_name, data_type, is_nullable, _ in rows:
        description = FIELD_DESCRIPTIONS.get(column_name)
        if description is None:
            description = f"{TABLE_PURPOSES[table_name]} 字段 {column_name}。"
        output_rows.append(
            [
                table_name,
                TABLE_PURPOSES[table_name],
                column_name,
                data_type,
                is_nullable,
                description,
            ]
        )
    _write_csv(
        Path(destination),
        ["table_name", "table_purpose", "field_name", "duckdb_type", "nullable", "definition"],
        output_rows,
    )


def _versioning_self_check(bundle: PilotBundle, project_root: Path) -> dict[str, Any]:
    with duckdb.connect(":memory:") as connection:
        ingest_pilot_bundle(connection, bundle, project_root=project_root)
        base_counts = _table_counts(connection)
        ingest_pilot_bundle(connection, bundle, project_root=project_root)
        repeated_counts = _table_counts(connection)

        changed_records = copy.deepcopy(bundle.records)
        changed_records[0]["title"] = changed_records[0]["title"] + " [VERSION TEST ONLY]"
        changed_metadata = {**bundle.metadata_snapshot, "records": changed_records}
        changed_bundle = replace(
            bundle,
            metadata_snapshot=changed_metadata,
            records=changed_records,
            metadata_sha256=_sha256_bytes(_canonical_json(changed_metadata).encode("utf-8")),
        )
        ingest_pilot_bundle(connection, changed_bundle, project_root=project_root)
        after_raw_change = _table_counts(connection)
        raw_change_version_delta = (
            after_raw_change["document_versions"] - repeated_counts["document_versions"]
        )

        changed_rules = {**NORMALISATION_RULES, "self_check_marker": "version 2 test only"}
        ingest_pilot_bundle(
            connection,
            bundle,
            project_root=project_root,
            rule_version="govuk_metadata_v2_self_check_only",
            rules=changed_rules,
        )
        after_rule_change = _table_counts(connection)
        rule_change_version_delta = (
            after_rule_change["document_versions"] - after_raw_change["document_versions"]
        )
        current_versions = int(
            _scalar(connection, "SELECT COUNT(*) FROM document_versions WHERE is_current")
        )
    return {
        "passed": (
            base_counts == repeated_counts
            and raw_change_version_delta == 1
            and rule_change_version_delta == 9
            and current_versions == 9
        ),
        "repeat_import_counts_unchanged": base_counts == repeated_counts,
        "raw_change_document_version_delta": raw_change_version_delta,
        "rule_change_document_version_delta": rule_change_version_delta,
        "current_versions_after_changes": current_versions,
        "note": "Executed only in an in-memory test database; self-check records are absent from the pilot database and coverage counts.",
    }


def _write_quality_report(
    path: Path,
    validation: dict[str, Any],
    reproducibility: dict[str, Any],
    versioning: dict[str, Any],
) -> None:
    status = (
        "PASS"
        if validation["passed"] and reproducibility["passed"] and versioning["passed"]
        else "FAIL"
    )
    lines = [
        "# 数据质量与重建检查",
        "",
        f"**总状态：{status}。** 该状态只覆盖 9 条已保存 GOV.UK/DEFRA 元数据的数据库试点，不评价正文、历史覆盖、主题相关性或伦理许可。",
        "",
        "## 关键边界",
        "",
        f"- {DENOMINATOR_LIMIT}",
        "- 真实正文段落为 0；`text_segments` 和 `embedding_ready_segments` 只是接口。",
        "- 来源与 9 条文档的伦理状态均为 `pending`；未发现可核验的 approved/exempt 记录。",
        "- 多机构发布不增加文档总数；完整机构关联权重和分数权重均保存，但尚未选择机构统计口径。",
        "",
        "## 数据检查",
        "",
        "| 检查 | 观察值 | 期望值 | 结果 |",
        "|---|---:|---:|---|",
    ]
    for item in validation["checks"]:
        result = "PASS" if item["passed"] else "FAIL"
        lines.append(f"| `{item['name']}` | {item['observed']} | {item['expected']} | {result} |")
    lines.extend(
        [
            "",
            "## 可重复性与版本检查",
            "",
            f"- 同一批次重复导入行数不变：{'PASS' if reproducibility['idempotent_counts_unchanged'] else 'FAIL'}。",
            f"- 删除式干净重建的逻辑指纹一致：{'PASS' if reproducibility['clean_rebuild_fingerprint_match'] else 'FAIL'}。",
            f"- 原始记录变化产生 1 个新文档版本（内存测试）：{versioning['raw_change_document_version_delta']}。",
            f"- 规则版本变化为 9 条文档各产生新版本（内存测试）：{versioning['rule_change_document_version_delta']}。",
            f"- 版本测试后仍恰有 9 个 current versions：{versioning['current_versions_after_changes']}。",
            "",
            "## 未解决阻塞点",
            "",
            "1. 尚无已记录的 UQ ethics approval 或 exemption；不能把 `pending` 改成 `approved`。",
            "2. 正文和附件尚未做逐项许可/第三方权利审核，因此没有采集或切段真实正文。",
            "3. Lead/emphasised organisation 尚未核验，机构归属统计口径尚未批准。",
            "4. 单月快照不能证明 1988–2026 历史覆盖、渠道连续性或跨年代可比性。",
            "5. 尚未检查跨来源重复或内容重叠；没有正文时也不能做内容级重复判定。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def rebuild_pilot(
    feasibility_dir: str | Path,
    database_path: str | Path,
    exports_dir: str | Path,
    *,
    project_root: str | Path,
    quality_report_path: str | Path,
    dictionary_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    bundle = load_pilot_bundle(feasibility_dir)
    project = Path(project_root).resolve()
    destination = Path(database_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="m1_db_pilot_", dir=destination.parent) as temp_dir:
        temp_root = Path(temp_dir)
        first_db = temp_root / "first.duckdb"
        second_db = temp_root / "second.duckdb"

        with duckdb.connect(str(first_db)) as connection:
            ingest_pilot_bundle(connection, bundle, project_root=project)
            before_repeat = _table_counts(connection)
            ingest_pilot_bundle(connection, bundle, project_root=project)
            after_repeat = _table_counts(connection)
            first_validation = validate_database(connection)
            first_fingerprint = logical_fingerprint(connection)

        with duckdb.connect(str(second_db)) as connection:
            ingest_pilot_bundle(connection, bundle, project_root=project)
            second_validation = validate_database(connection)
            second_fingerprint = logical_fingerprint(connection)

        reproducibility = {
            "passed": (
                before_repeat == after_repeat
                and first_fingerprint == second_fingerprint
                and first_validation["passed"]
                and second_validation["passed"]
            ),
            "idempotent_counts_unchanged": before_repeat == after_repeat,
            "clean_rebuild_fingerprint_match": first_fingerprint == second_fingerprint,
            "logical_fingerprint": second_fingerprint,
            "counts_before_repeat": before_repeat,
            "counts_after_repeat": after_repeat,
        }
        os.replace(second_db, destination)

    with duckdb.connect(str(destination), read_only=True) as connection:
        validation = validate_database(connection)
        exports = export_database(connection, exports_dir)
        export_data_dictionary(connection, dictionary_path)

    versioning = _versioning_self_check(bundle, project)
    quality_path = Path(quality_report_path)
    _write_quality_report(quality_path, validation, reproducibility, versioning)
    result = {
        "status": "passed"
        if validation["passed"] and reproducibility["passed"] and versioning["passed"]
        else "failed",
        "scope": SOURCE_SCOPE,
        "database": _relative(destination, project),
        "database_sha256": _sha256_file(destination),
        "inputs": {
            _relative(bundle.search_snapshot_path, project): bundle.search_sha256,
            _relative(bundle.metadata_snapshot_path, project): bundle.metadata_sha256,
            _relative(bundle.checks_path, project): _sha256_file(bundle.checks_path),
            _relative(bundle.source_register_path, project): _sha256_file(
                bundle.source_register_path
            ),
        },
        "schema_version": SCHEMA_VERSION,
        "normalisation_rule_version": NORMALISATION_RULE_VERSION,
        "validation": validation,
        "reproducibility": reproducibility,
        "versioning_self_check": versioning,
        "exports": exports,
        "data_dictionary_sha256": _sha256_file(Path(dictionary_path)),
        "quality_report_sha256": _sha256_file(quality_path),
    }
    manifest = Path(manifest_path)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] != "passed":
        raise RuntimeError("Database pilot validation failed; see the quality report")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rebuild the bounded M1 GOV.UK metadata database pilot"
    )
    parser.add_argument("--feasibility-dir", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--exports-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--quality-report", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = rebuild_pilot(
        args.feasibility_dir,
        args.database,
        args.exports_dir,
        project_root=args.project_root,
        quality_report_path=args.quality_report,
        dictionary_path=args.dictionary,
        manifest_path=args.manifest,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "database": result["database"],
                "documents": result["validation"]["table_counts"]["documents"],
                "text_segments": result["validation"]["table_counts"]["text_segments"],
                "logical_fingerprint": result["reproducibility"]["logical_fingerprint"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
