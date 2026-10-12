"""Pure, bounded Australian admission contract; all imports use in-memory SQLite.

No network, old-store connection, donor-module import, production path, scheduler,
topic/emotion model, archive move, or full-corpus traversal is implemented here.
Input is an explicit JSON projection prepared by a source-specific adapter.
The CLI emits metadata only. Synthetic examples are conformance tests, not data.
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any

CONTRACT = "au-rebuild-contract-v1"
START, END = date(1988, 1, 1), date(2026, 9, 21)
MAX_INPUT_BYTES = 1_048_576  # Fixture safety bound, not a corpus/source quota.
CONTEXT_KINDS = {"context_container", "repost", "preview", "parliament_sitting",
                 "parliament_procedural_unit", "signature_count_context"}
KINDS = CONTEXT_KINDS | {"news_article", "public_letter", "civic_submission", "social_post", "social_reply",
    "social_question", "social_answer", "social_comment", "parliament_utterance",
    "parliament_paragraph", "government_document", "petition", "ministerial_response"}
PROVENANCE = {"direct_original", "archival_reproduction", "indirect_secondary", "mixed", "unresolved"}
RELATIONS = {"in_sitting", "in_procedural_unit", "in_utterance", "paragraph_order",
    "reply_to", "thread_context", "repost_of", "quotes_remote", "attachment_of",
    "syndicated_from", "mirror_of", "identity_resolution"}


def serial(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(serial(value).encode("utf-8")).hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def key(prefix: str, *values: Any) -> str:
    return prefix + ":" + digest(list(values))


def publication_bounds(p: dict[str, Any]) -> tuple[str | None, str | None, str, str]:
    """Preserve precision; never impute month/day or use retrieval date as publication."""
    value, precision = p.get("value"), p.get("precision", "unknown")
    if not value or precision == "unknown":
        return None, None, "pending", "publication_unknown"
    try:
        if precision == "timestamp":
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.utcoffset() is None:
                return None, None, "pending", "publication_timezone_unknown"
            lower = upper = parsed.date()  # Original supplied source offset, not UTC binning.
        elif precision == "day":
            lower = upper = date.fromisoformat(value)
            if value != lower.isoformat():
                raise ValueError("noncanonical date")
        elif precision == "month":
            year, month = map(int, value.split("-"))
            lower = date(year, month, 1)
            upper = date(year, month, calendar.monthrange(year, month)[1])
            if value != f"{year:04d}-{month:02d}":
                raise ValueError("noncanonical month")
        elif precision == "year":
            year = int(value)
            lower, upper = date(year, 1, 1), date(year, 12, 31)
            if value != f"{year:04d}":
                raise ValueError("noncanonical year")
        else:
            raise ValueError("unsupported precision")
    except (ValueError, TypeError, AttributeError):
        return None, None, "failed", "publication_invalid"
    # An evidenced interval can narrow a partial boundary without upgrading precision.
    if p.get("bounded_interval"):
        try:
            interval = p["bounded_interval"]
            a, b = date.fromisoformat(interval["lower"]), date.fromisoformat(interval["upper"])
            if not (lower <= a <= b <= upper) or not interval.get("evidence"):
                raise ValueError("unproved interval")
            lower, upper = a, b
        except (KeyError, ValueError, TypeError):
            return lower.isoformat(), upper.isoformat(), "pending", "publication_interval_unproved"
    if upper < START or lower > END:
        state, reason = "outside_scope", "publication_outside_fixed_interval"
    elif lower < START or upper > END:
        state, reason = "pending", "publication_boundary_overlap"
    elif p.get("state") in {"pending", "conflict"}:
        state, reason = p["state"], "publication_evidence_" + p["state"]
    elif p.get("state") != "verified" or not p.get("evidence"):
        state, reason = "pending", "publication_evidence_missing"
    else:
        state, reason = "verified", "publication_interval_verified"
    return lower.isoformat(), upper.isoformat(), state, reason


def review_record(r: dict[str, Any]) -> dict[str, Any]:
    """Seven independent structural checks; no semantic or concentration check."""
    s, n, p, c, rights = (r[k] for k in ("source", "native", "publication", "content", "rights"))
    checks: list[dict[str, str]] = []

    def add(name: str, state: str, reason: str, evidence: str | None) -> None:
        checks.append(dict(check_name=name, check_state=state,
                           reason_code=reason, evidence_locator=evidence or ""))

    if s.get("context_state") == "outside_scope" or s.get("context_basis") == "outside_scope":
        add("source", "outside_scope", "source_outside_australian_context", s.get("context_evidence"))
    elif s.get("context_state") == "conflict" or s.get("identity_state") == "conflict":
        add("source", "conflict", "source_context_or_identity_conflict", s.get("context_evidence"))
    elif s.get("context_state") == s.get("identity_state") == "verified" and s.get("context_evidence") and s.get("context_basis") in {
            "australian_institution", "australian_publisher", "australian_community"}:
        add("source", "verified", "australian_source_context_verified", s["context_evidence"])
    else:
        add("source", "pending", "australian_source_context_pending", s.get("context_evidence"))

    identity_state = n.get("identity_state", "pending")
    if identity_state not in {"verified", "pending", "conflict"}:
        identity_state = "pending"
    if not n.get("id") or not n.get("namespace") or not n.get("identity_evidence"):
        identity_state = "pending"
    add("identity", identity_state, "native_identity_" + identity_state, n.get("identity_evidence"))
    lower, upper, date_state, date_reason = publication_bounds(p)
    add("publication_date", date_state, date_reason, p.get("evidence"))

    kind = n.get("kind")
    legacy = r.get("legacy_disposition", {})
    if kind not in KINDS:
        add("native_unit", "failed", "unsupported_native_unit", n.get("unit_evidence"))
    elif legacy.get("state") == "confirmed_structural_fault":
        add("native_unit", "failed", "inherited_confirmed_structural_hold:" + legacy.get("reason", "unknown"), legacy.get("evidence"))
    elif legacy.get("state") not in {"checked_no_hold", "not_applicable"} or not legacy.get("evidence"):
        add("native_unit", "pending", "inherited_disposition_requires_resolution:" + legacy.get("reason", "unknown"), legacy.get("evidence"))
    elif n.get("unit_state") == "confirmed_invalid":
        add("native_unit", "failed", "confirmed_native_boundary_fault", n.get("unit_evidence"))
    elif n.get("unit_state") == "verified" and n.get("unit_evidence"):
        add("native_unit", "verified", "native_boundary_verified", n["unit_evidence"])
    else:
        add("native_unit", "pending", "native_boundary_pending", n.get("unit_evidence"))

    original = c.get("original_text")
    expected = c.get("original_text_sha256")
    if c.get("completeness") == "confirmed_incomplete":
        add("content", "failed", "confirmed_incomplete_original", c.get("evidence"))
    elif kind in CONTEXT_KINDS and original is None and c.get("completeness") == "native_context":
        add("content", "not_applicable", "bodyless_native_context", c.get("evidence"))
    elif original is not None and not isinstance(original, str):
        add("content", "failed", "original_text_type_invalid", c.get("evidence"))
    elif original is not None and expected and text_hash(original) != expected:
        add("content", "failed", "original_text_hash_mismatch", c.get("evidence"))
    elif original is not None and not original.strip():
        add("content", "failed", "unreadable_original", c.get("evidence"))
    elif original is None or not expected or not c.get("evidence") or not c.get("reference"):
        add("content", "pending", "original_content_mapping_pending", c.get("evidence"))
    elif c.get("original_text_sha256_basis") != "utf8_original_native_string":
        add("content", "pending", "original_hash_representation_basis_pending", c.get("evidence"))
    elif c.get("readable_original") is not True:
        add("content", "pending", "original_readability_pending", c.get("evidence"))
    elif c.get("completeness") != "verified_complete" or c.get("provenance") not in PROVENANCE - {"unresolved"}:
        add("content", "pending", "original_completeness_or_provenance_pending", c.get("evidence"))
    else:
        add("content", "verified", "original_content_mapping_verified", c["evidence"])

    operations = [rights.get(k, "unknown") for k in ("public_access", "local_retention", "internal_analysis")]
    if "denied" in operations:
        add("rights", "restricted", "intended_internal_operation_denied", rights.get("evidence"))
    elif all(x == "allowed" for x in operations) and rights.get("evidence") and rights.get("intended_use"):
        add("rights", "verified", "intended_internal_operations_supported", rights["evidence"])
    else:
        add("rights", "pending", "intended_internal_operations_pending", rights.get("evidence"))
    # Unknown redistribution is retained, but is not a barrier to supported internal use.

    relations = r.get("relations", [])
    needed = set()
    if kind in {"parliament_utterance", "parliament_paragraph", "parliament_procedural_unit"}:
        needed.add("in_sitting")
    if kind in {"parliament_utterance", "parliament_paragraph"}:
        needed.add("in_procedural_unit")
    if kind == "parliament_paragraph" and n.get("paragraph_parent_mode") == "utterance":
        needed.add("in_utterance")
    good = {x.get("type") for x in relations if x.get("state") == "verified" and
            all(x.get(k) for k in ("target_source", "target_namespace", "target_id", "evidence"))}
    if any(x.get("type") not in RELATIONS for x in relations):
        add("lineage", "failed", "unsupported_native_relation", n.get("unit_evidence"))
    elif kind == "parliament_paragraph" and n.get("paragraph_parent_mode") not in {"utterance", "procedural"}:
        add("lineage", "pending", "parliamentary_parent_boundary_pending", n.get("unit_evidence"))
    elif needed - good:
        add("lineage", "pending", "parliamentary_lineage_pending", n.get("unit_evidence"))
    else:
        add("lineage", "verified" if relations or needed else "not_applicable",
            "native_lineage_preserved" if relations or needed else "no_required_parent_lineage", n.get("unit_evidence"))

    states = {x["check_state"] for x in checks}
    if "failed" in states:
        disposition = "quarantine"
    elif "outside_scope" in states:
        disposition = "archive_only"
    elif "restricted" in states:
        disposition = "restricted"
    elif states & {"pending", "conflict"}:
        disposition = "pending"
    else:
        disposition = "context_only" if kind in CONTEXT_KINDS else "admitted"
    return dict(checks=checks, disposition=disposition, publication_lower=lower,
                publication_upper=upper, date_state=date_state,
                reasons=[x["reason_code"] for x in checks if x["check_state"] not in {"verified", "not_applicable"}])


def fixture_database() -> sqlite3.Connection:
    """No destination argument: the only available implementation is :memory:."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    conn.execute("INSERT INTO dataset_contract VALUES (?,?,?,?,?,?)",
                 (CONTRACT, START.isoformat(), END.isoformat(), 100_000_000_000, 15 * 1024**3, "synthetic_conformance"))
    return conn


def insert_same(conn: sqlite3.Connection, table: str, row: dict[str, Any], primary: tuple[str, ...]) -> None:
    """Identical replay is harmless; changed immutable values are never overwritten."""
    columns = tuple(row)
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})", tuple(row.values()))
    found = conn.execute(f"SELECT {','.join(columns)} FROM {table} WHERE " +
        " AND ".join(f"{x}=?" for x in primary), tuple(row[x] for x in primary)).fetchone()
    if found is None or tuple(found) != tuple(row.values()):
        raise ValueError("immutable_projection_conflict:" + table)


def import_record(conn: sqlite3.Connection, r: dict[str, Any], reviewer: str = "synthetic-contract-test") -> dict[str, Any]:
    """Import one explicit projection into a fixture, preserving archive/new mappings."""
    if any(row[2] for row in conn.execute("PRAGMA database_list")):
        raise ValueError("only_in_memory_fixture_database_is_supported")
    if len(serial(r).encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("bounded_fixture_input_exceeded")
    result = review_record(r)
    a, s, n, p, c, rights, times = (r[k] for k in ("archive", "source", "native", "publication", "content", "rights", "times"))
    legacy = r.get("legacy_disposition", {})
    if n.get("kind") not in KINDS:
        raise ValueError("unsupported_native_unit_requires_external_pending_projection")
    report_at = times["report_at"]
    # Candidate identities remain distinguishable from validated native identities.
    unresolved = not n.get("id") or not n.get("namespace")
    namespace = "archive-unresolved" if unresolved else n["namespace"]
    native_id = key("candidate", a["snapshot_id"], a["original_id"]) if unresolved else n["id"]
    uid = key("au-unit-v1", s["id"], namespace, native_id)
    arid = key("archive-record-v1", a["snapshot_id"], a["original_id"], a["original_version_id"], a["locator"])
    sid, rid = key("source-assertion-v1", s), key("rights-v1", s["id"], rights)
    mid = key("metadata-v1", uid, p, n, legacy, times, s.get("source_url", ""), sid)
    original = c.get("original_text")
    body_hash = text_hash(original) if isinstance(original, str) else None
    cid = key("content-v1", uid, body_hash, c.get("native_revision"), times.get("content_version_at"), arid) if original is not None else None
    uvid = key("unit-version-v1", uid, mid, cid, rid)
    did = key("admission-v1", arid, uvid, result, reviewer, report_at)
    with conn:
        insert_same(conn, "archive_snapshots", dict(snapshot_id=a["snapshot_id"], reference_path=a["snapshot_path"],
            reference_digest=a.get("snapshot_digest"), digest_basis=a.get("snapshot_digest_basis", "recorded_reference_not_rehashed"),
            observed_at=a["snapshot_observed_at"], preservation_status="preserve_in_place"), ("snapshot_id",))
        insert_same(conn, "archive_records", dict(archive_record_id=arid, snapshot_id=a["snapshot_id"], original_id=a["original_id"],
            original_version_id=a["original_version_id"], locator=a["locator"], recorded_content_hash=a.get("recorded_content_hash"),
            hash_basis=a.get("hash_basis", "unknown"), raw_reference=a.get("raw_reference")), ("archive_record_id",))
        insert_same(conn, "sources", dict(source_id=s["id"], label=s["label"], stream=s["stream"]), ("source_id",))
        insert_same(conn, "source_assertions", dict(assertion_id=sid, source_id=s["id"], australian_context_basis=s.get("context_basis", "unknown"),
            australian_context_state=s.get("context_state", "pending"), identity_state=s.get("identity_state", "pending"), genre=s.get("genre", "unknown"),
            context_as_of=s.get("context_as_of"), evidence_locator=s.get("context_evidence", ""), applicability_start=s.get("applicability_start"),
            applicability_end=s.get("applicability_end"), applicability_state=s.get("applicability_state", "unknown")), ("assertion_id",))
        insert_same(conn, "rights_assertions", dict(rights_id=rid, source_id=s["id"], **{k:rights.get(k, "unknown") for k in
            ("public_access", "local_retention", "internal_analysis", "redistribution")}, licence=rights.get("licence", "unknown"),
            intended_use=rights.get("intended_use", ""), conditions=rights.get("conditions", ""), evidence_locator=rights.get("evidence", ""),
            checked_at=rights["checked_at"]), ("rights_id",))
        insert_same(conn, "units", dict(unit_id=uid, source_id=s["id"], native_namespace=namespace, native_id=native_id,
            unit_kind=n["kind"]), ("unit_id",))
        insert_same(conn, "metadata_versions", dict(metadata_version_id=mid, unit_id=uid, source_assertion_id=sid, source_url=s.get("source_url", ""),
            publication_value=p.get("value"), publication_precision=p.get("precision", "unknown"), publication_lower_day=result["publication_lower"],
            publication_upper_day=result["publication_upper"], publication_timezone=p.get("timezone"), date_state=result["date_state"],
            date_evidence=p.get("evidence", ""), native_identity_state="pending" if unresolved else n.get("identity_state", "pending"),
            author_native_id=n.get("author_id"), author_geography=n.get("author_geography"), author_geography_basis=n.get("author_geography_basis", "unmeasured"),
            retrieved_at=times["retrieved_at"], extracted_at=times.get("extracted_at"), content_version_at=times.get("content_version_at"),
            report_at=report_at, original_metadata_json=serial(dict(publication=p, native=n, legacy_disposition=legacy))), ("metadata_version_id",))
        if cid:
            insert_same(conn, "content_versions", dict(content_version_id=cid, unit_id=uid, archive_record_id=arid, original_text_sha256=body_hash,
                original_format=c.get("original_format", "unknown"), source_bytes_sha256=c.get("source_bytes_sha256"), source_bytes_hash_basis=c.get("source_bytes_hash_basis", "unknown"),
                native_revision=c.get("native_revision"), content_version_at=times.get("content_version_at"),
                provenance_type=c.get("provenance", "unresolved"), provenance_evidence=c.get("evidence", ""), completeness_state=c.get("completeness", "pending"),
                original_reference=c.get("reference", "")), ("content_version_id",))
            repid = key("representation-v1", cid, "original", body_hash)
            insert_same(conn, "text_representations", dict(representation_id=repid, content_version_id=cid, representation_kind="original", text_sha256=body_hash,
                text_value=original, external_reference=None, extraction_rule="explicit_inline_projection", extraction_rule_version="v1", evidence_locator=c.get("evidence", "")), ("representation_id",))
            for index, part in enumerate(c.get("source_parts", [])):
                insert_same(conn, "content_source_parts", dict(content_version_id=cid, part_ordinal=index, source_locator=part["locator"],
                    source_object_hash=part.get("hash"), hash_basis=part.get("hash_basis", "unknown"), part_role=part["role"], page_number=part.get("page_number"),
                    source_span_json=serial(part.get("source_span", {})), evidence_locator=part["evidence"]), ("content_version_id", "part_ordinal"))
        authored = int(n.get("independently_authored_body") is True and n["kind"] not in CONTEXT_KINDS)
        insert_same(conn, "unit_versions", dict(unit_version_id=uvid, unit_id=uid, metadata_version_id=mid, content_version_id=cid,
            rights_id=rid, independently_authored_body=authored, recorded_at=report_at), ("unit_version_id",))
        for relation in r.get("relations", []):
            target = key("au-unit-v1", relation["target_source"], relation["target_namespace"], relation["target_id"])
            exists = conn.execute("SELECT 1 FROM units WHERE unit_id=?", (target,)).fetchone()
            relid = key("relation-v1", uid, relation, target if exists else None)
            insert_same(conn, "unit_relations", dict(relation_id=relid, child_unit_id=uid, relation_type=relation["type"],
                target_source_id=relation["target_source"], target_namespace=relation["target_namespace"], target_native_id=relation["target_id"],
                target_unit_id=target if exists else None, ordinal=relation.get("ordinal"), verification_state=relation.get("state", "pending"),
                evidence_locator=relation.get("evidence", "")), ("relation_id",))
        insert_same(conn, "admission_ledger", dict(decision_id=did, archive_record_id=arid, unit_version_id=uvid, disposition=result["disposition"],
            reason_codes_json=serial(result["reasons"]), reviewer=reviewer, reviewed_at=report_at, contract_id=CONTRACT), ("decision_id",))
        for check in result["checks"]:
            insert_same(conn, "admission_checks", dict(decision_id=did, **check), ("decision_id", "check_name"))
        state = {"admitted":"accepted", "context_only":"context", "pending":"proposed"}.get(result["disposition"], "withheld")
        mapping = dict(archive_record_id=arid, unit_version_id=uvid, decision_id=did, mapping_state=state, original_id=a["original_id"],
            original_version_id=a["original_version_id"], original_recorded_hash=a.get("recorded_content_hash"), new_unit_id=uid,
            new_content_version_id=cid, new_original_text_hash=body_hash)
        insert_same(conn, "archive_to_new_map", mapping, ("archive_record_id", "unit_version_id", "decision_id"))
        # The sole implemented transform is exact CRLF→LF. Originals stay intact.
        if isinstance(original, str) and "\r\n" in original:
            derived = original.replace("\r\n", "\n")
            derived_id = key("representation-v1", cid, "crlf_to_lf-v1", text_hash(derived))
            insert_same(conn, "text_representations", dict(representation_id=derived_id, content_version_id=cid, representation_kind="structural_derived",
                text_sha256=text_hash(derived), text_value=derived, external_reference=None, extraction_rule="crlf_to_lf", extraction_rule_version="v1",
                evidence_locator="exact-reversible-line-ending-transform;original=" + repid), ("representation_id",))
            change = dict(change_id=key("change-v1", uvid, derived_id), archive_record_id=arid, unit_version_id=uvid, field_name="text_line_endings",
                prior_value_json=serial(dict(representation_id=repid, hash=body_hash)), derived_value_json=serial(dict(representation_id=derived_id, hash=text_hash(derived))),
                reason_code="crlf_to_lf", evidence_locator="exact-reversible-line-ending-transform", reviewer=reviewer, reviewed_at=report_at,
                derived_representation_id=derived_id)
            insert_same(conn, "structural_changes", change, ("change_id",))
    return dict(disposition=result["disposition"], reasons=result["reasons"], checks=result["checks"], mapping=mapping)


def validate_fixture(conn: sqlite3.Connection) -> dict[str, Any]:
    foreign = [tuple(x) for x in conn.execute("PRAGMA foreign_key_check")]
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    return dict(integrity=integrity, foreign_key_failures=foreign,
        dispositions={x[0]:x[1] for x in conn.execute("SELECT disposition,COUNT(*) FROM admission_ledger GROUP BY disposition")},
        accepted_units_by_kind={x[0]:x[1] for x in conn.execute("SELECT unit_kind,COUNT(DISTINCT unit_id) FROM accepted_native_versions GROUP BY unit_kind")},
        monthly_units_by_kind={x[0]:x[1] for x in conn.execute("SELECT unit_kind,COUNT(DISTINCT unit_id) FROM accepted_monthly_versions GROUP BY unit_kind")},
        passages_created=conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0],
        active_database_created=False, protected_store_connections=0, semantic_checks=0)


def combine_compatible_counts(rows: list[dict[str, Any]]) -> int:
    """Only disjoint counts with the same native unit and role/frame may be summed."""
    frames = {(r["unit_kind"], r["role_frame"], r["version_basis"]) for r in rows}
    if len(frames) > 1 or not all(r.get("disjoint_verified") is True for r in rows):
        raise ValueError("incompatible_or_unproved_count_units")
    return sum(r["count"] for r in rows)


def full_period_cells(frame_id: str, source_id: str, genre: str, role_frame: str,
                      unit_kind: str) -> list[dict[str, Any]]:
    """Full fixed-calendar scaffold; absent evidence is unknown, never zero discourse."""
    cells = []
    year, month = START.year, START.month
    while (year, month) <= (END.year, END.month):
        lower = date(year, month, 1)
        upper = min(END, date(year, month, calendar.monthrange(year, month)[1]))
        cells.append(dict(frame_id=frame_id, source_id=source_id, genre=genre, role_frame=role_frame,
            unit_kind=unit_kind, month=f"{year:04d}-{month:02d}", lower_day=lower.isoformat(), upper_day=upper.isoformat(),
            applicability_state="unknown", observation_state="unknown", readable_native_units=None,
            independent_work_count=None, pending_units=None, inventory_state="unknown", evidence_locator=""))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return cells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True, help="Explicit tiny self-contained fixture projection only")
    args = parser.parse_args()
    with args.input_jsonl.open("rb") as handle:
        payload = handle.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise SystemExit("bounded_fixture_input_exceeded")
    records = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
    conn = fixture_database()
    try:
        maps = [import_record(conn, r) for r in records]
        print(json.dumps(dict(status="offline_in_memory_conformance_only", validation=validate_fixture(conn), mappings=maps), ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
