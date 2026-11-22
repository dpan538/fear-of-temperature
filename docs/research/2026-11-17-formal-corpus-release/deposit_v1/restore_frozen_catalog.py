"""Verify a private v1 release bundle and restore its catalog at a new path."""

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

VERSION = "formal-corpus-release-20261117-v1"
PARQUET_INPUTS = {
    "release_records": "release_v1/records/*.parquet",
    "release_membership": "release_v1/RELEASE_MEMBERSHIP.parquet",
    "supplement_audit": "supplement_selection_v1/DECISIONS.parquet",
    "supplement_native_metadata": "release_v1/SUPPLEMENT_NATIVE_METADATA.parquet",
}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def matches(path, expected):
    if sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch for {path.name}")


def verify_inputs(bundle):
    release = bundle / "release_v1"
    receipt = json.loads((release / "COMMIT_RECEIPT.json").read_text(encoding="utf-8"))
    if receipt["version"] != VERSION:
        raise ValueError(f"Expected {VERSION}")
    matches(release / "formal_corpus.duckdb", receipt["catalog_sha256"])
    matches(release / "RELEASE_MEMBERSHIP.parquet", receipt["membership_sha256"])
    matches(release / "LONG_PASSAGE_FINGERPRINTS.parquet", receipt["passage_fingerprint_sha256"])

    baseline = json.loads((release / "BASELINE_MATERIALIZED.json").read_text(encoding="utf-8"))
    supplement = json.loads((release / "SUPPLEMENT_MATERIALIZED.json").read_text(encoding="utf-8"))
    matches(bundle / PARQUET_INPUTS["supplement_audit"], supplement["selection_sha256"])
    parts = {
        Path(part["path"]).name: part["sha256"]
        for part in baseline["parts"] + supplement["parts"]
    }
    actual = {part.name for part in (release / "records").glob("*.parquet")}
    if len(parts) != 150 or actual != set(parts):
        raise ValueError("Record Parquet roster differs from the frozen 150-part manifest")
    for name, expected in sorted(parts.items()):
        matches(release / "records" / name, expected)
    return receipt, parts


def sql_path(path):
    return "'" + str(path).replace("'", "''") + "'"


def restore(bundle, output):
    receipt, parts = verify_inputs(bundle)
    expected = {
        "release_records": receipt["records_materialized"],
        "corpus_records": receipt["formal_records"],
        "quarantine_records": receipt["counts"]["retained_quarantine"],
        "ml_train": receipt["counts"]["split:train"],
        "ml_validation": receipt["counts"]["split:validation"],
        "ml_test": receipt["counts"]["split:test"],
    }
    original = bundle / "release_v1/formal_corpus.duckdb"
    with TemporaryDirectory(dir=output.parent, prefix="restore-catalog-") as scratch:
        candidate = Path(scratch) / "catalog.duckdb"
        shutil.copyfile(original, candidate)
        with duckdb.connect(
            str(candidate), config={"threads": 1, "memory_limit": "512MB"}
        ) as catalog:
            catalog.execute("BEGIN")
            for view, relative_path in PARQUET_INPUTS.items():
                parquet = sql_path(bundle / relative_path)
                options = ", union_by_name = true" if view == "release_records" else ""
                catalog.execute(
                    f"CREATE OR REPLACE VIEW {view} AS "
                    f"SELECT * FROM read_parquet({parquet}{options})"
                )
            catalog.execute("COMMIT")
            actual = {
                view: catalog.sql(f"SELECT count(*) FROM {view}").fetchone()[0]
                for view in expected
            }
            if actual != expected:
                raise ValueError(f"Restored counts differ from receipt: {actual}")
            body_counts = {
                view: catalog.sql(f"SELECT count(DISTINCT body_sha256) FROM {view}").fetchone()[0]
                for view in ("release_records", "corpus_records", "quarantine_records")
            }
            rebound = catalog.execute(
                "SELECT view_name, sql FROM duckdb_views() WHERE NOT internal"
            ).fetchall()
            rebound_sql = {name: sql for name, sql in rebound if "read_parquet(" in sql.lower()}
            if set(rebound_sql) != set(PARQUET_INPUTS) or any(
                sql_path(bundle / path) not in rebound_sql[name]
                for name, path in PARQUET_INPUTS.items()
            ):
                raise ValueError("An external data view still points outside the restored bundle")
        matches(original, receipt["catalog_sha256"])
        os.link(candidate, output)

    roster = json.dumps(parts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "release_version": VERSION,
        "duckdb_version": duckdb.__version__,
        "original_catalog_sha256": receipt["catalog_sha256"],
        "membership_sha256": receipt["membership_sha256"],
        "passage_fingerprint_sha256": receipt["passage_fingerprint_sha256"],
        "materialized_parts_verified": len(parts),
        "parts_roster_sha256": hashlib.sha256(roster).hexdigest(),
        "relocated_external_views_verified": sorted(PARQUET_INPUTS),
        "view_record_counts": actual,
        "distinct_native_body_sha_by_view": body_counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle", type=Path, help="Directory containing release_v1 and supplement_selection_v1"
    )
    parser.add_argument("output", type=Path, help="New relocated DuckDB path")
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, f"Output already exists: {args.output}\n")
    print(json.dumps(restore(args.bundle.resolve(), args.output.absolute()), indent=2))


if __name__ == "__main__":
    main()
