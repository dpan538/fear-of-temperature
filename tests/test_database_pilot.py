from __future__ import annotations

import json
from pathlib import Path

import duckdb

from fear_temperature.config import PROJECT_ROOT
from fear_temperature.database_pilot import (
    ingest_pilot_bundle,
    load_pilot_bundle,
    logical_fingerprint,
    rebuild_pilot,
    validate_database,
)

FEASIBILITY = PROJECT_ROOT / "work_packages/M1_source_access/01_feasibility"


def test_saved_govuk_metadata_import_is_idempotent_and_traceable() -> None:
    bundle = load_pilot_bundle(FEASIBILITY)
    with duckdb.connect(":memory:") as connection:
        ingest_pilot_bundle(connection, bundle, project_root=PROJECT_ROOT)
        first_fingerprint = logical_fingerprint(connection)
        ingest_pilot_bundle(connection, bundle, project_root=PROJECT_ROOT)
        second_fingerprint = logical_fingerprint(connection)
        validation = validate_database(connection)

        assert validation["passed"]
        assert first_fingerprint == second_fingerprint
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone() == (9,)
        assert connection.execute("SELECT COUNT(*) FROM raw_records").fetchone() == (9,)
        assert connection.execute("SELECT COUNT(*) FROM text_segments").fetchone() == (0,)


def test_clean_rebuild_produces_stable_exports(tmp_path: Path) -> None:
    database = tmp_path / "pilot.duckdb"
    exports = tmp_path / "exports"
    quality = tmp_path / "quality.md"
    dictionary = tmp_path / "dictionary.csv"
    manifest = tmp_path / "manifest.json"

    first = rebuild_pilot(
        FEASIBILITY,
        database,
        exports,
        project_root=PROJECT_ROOT,
        quality_report_path=quality,
        dictionary_path=dictionary,
        manifest_path=manifest,
    )
    first_document_hash = first["exports"]["documents.csv"]["sha256"]
    database.unlink()
    second = rebuild_pilot(
        FEASIBILITY,
        database,
        exports,
        project_root=PROJECT_ROOT,
        quality_report_path=quality,
        dictionary_path=dictionary,
        manifest_path=manifest,
    )

    assert (
        first["reproducibility"]["logical_fingerprint"]
        == second["reproducibility"]["logical_fingerprint"]
    )
    assert first_document_hash == second["exports"]["documents.csv"]["sha256"]
    assert json.loads(manifest.read_text(encoding="utf-8"))["status"] == "passed"
