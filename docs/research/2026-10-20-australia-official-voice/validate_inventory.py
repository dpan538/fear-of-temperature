"""Validate every actual metadata row without creating, altering or cleaning a store."""

import hashlib
import json
import sqlite3
from collections import Counter
from types import SimpleNamespace

import collect as core
from jsonschema import Draft202012Validator, FormatChecker


def main():
    database = core.DEFAULT_OUTPUT / "official_voice.sqlite"
    if not database.is_file():
        raise FileNotFoundError(
            "Existing acquisition database required; never create an empty replacement"
        )
    db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("BEGIN")
    schema = json.loads((core.HERE / "source_documents.schema.json").read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors, units, dates = [], Counter(), Counter()
    max_excerpt, rows = 0, 0
    for source_row in db.execute("SELECT * FROM source_documents ORDER BY doc_id"):
        row = dict(source_row)
        rows += 1
        for field in [
            "query_matched",
            "query_dimensions",
            "related_work_ids",
            "source_context_json",
            "metadata_version_history",
        ]:
            row[field] = json.loads(row[field])
        errors.extend(
            {"doc_id": row["doc_id"], "path": list(e.path), "message": e.message}
            for e in validator.iter_errors(row)
        )
        max_excerpt = max(max_excerpt, len(row["excerpt_text"] or ""))
        units[(row["source_channel"], row["native_unit"])] += 1
        dates[(row["source_channel"], row["date_status"])] += 1
        if row["doc_id"] != core.digest([row["source_channel"], row["native_id"]]):
            errors.append({"doc_id": row["doc_id"], "message": "native identity hash mismatch"})
        if row["date_status"] == "inside_fixed_interval" and not (
            core.START <= row["publication_start"] <= row["publication_end"] <= core.END
        ):
            errors.append({"doc_id": row["doc_id"], "message": "fixed interval mismatch"})
    quick = db.execute("PRAGMA quick_check").fetchone()[0]
    fk_errors = [list(r) for r in db.execute("PRAGMA foreign_key_check")]
    unique_ids = db.execute("SELECT count(DISTINCT doc_id) FROM source_documents").fetchone()[0]
    unique_native = db.execute(
        "SELECT count(*) FROM (SELECT source_channel,native_id FROM source_documents "
        "GROUP BY source_channel,native_id)"
    ).fetchone()[0]
    claims = db.execute("SELECT count(*) FROM event_claims").fetchone()[0]
    completion = core.exhaustion_summary(SimpleNamespace(db=db))
    db.rollback()
    report = {
        "validated_at": core.now(),
        "status": "PASS"
        if (
            not errors
            and not fk_errors
            and quick == "ok"
            and rows == unique_ids == unique_native
            and max_excerpt <= 500
        )
        else "FAIL",
        "json_schema_validated_actual_documents": rows,
        "schema_errors": errors,
        "unique_doc_ids": unique_ids,
        "unique_source_native_pairs": unique_native,
        "max_excerpt_characters": max_excerpt,
        "sqlite_quick_check": quick,
        "foreign_key_errors": fk_errors,
        "actual_claim_rows": claims,
        "calendar_validated": False,
        **completion,
        "date_states": [
            {"source": s, "state": state, "records": n} for (s, state), n in sorted(dates.items())
        ],
        "native_units": [
            {"source": s, "unit": unit, "records": n} for (s, unit), n in sorted(units.items())
        ],
        "matrix_config_sha256": {
            f: hashlib.sha256((core.HERE / f).read_bytes()).hexdigest()
            for f in ["query_matrix.json", "query_matrix_extended.json"]
        },
        "full_source_bodies_retained": False,
    }
    core.write_json(core.HERE / "VALIDATION.json", report)
    print(
        report["status"],
        rows,
        "rows; unique IDs",
        unique_ids,
        "schema errors",
        len(errors),
        "max excerpt",
        max_excerpt,
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
