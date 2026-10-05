"""Targeted provenance, identity, hash, parent and date-quality checks."""
import hashlib
import json
from pathlib import Path

import duckdb

from acquire import AU_SOURCE, DB, HERE, ROOT, US_SOURCE

BASE = HERE.parent / "06_government_content_acquisition" / "fear_temperature_government_content.duckdb"
EXPECTED_BASE_SHA = "d6c285649048f7910810630dc3da8479efcca7c38e35f903a5d20eae20e90465"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1024 * 1024): h.update(block)
    return h.hexdigest()


def main():
    c = duckdb.connect(str(DB), read_only=True)
    checks = {}
    checks["uk_baseline_sha256"] = file_sha(BASE)
    checks["uk_baseline_unchanged"] = checks["uk_baseline_sha256"] == EXPECTED_BASE_SHA
    checks["new_documents"] = dict(c.execute("SELECT source_id, count(*) FROM documents WHERE source_id IN (?,?) GROUP BY 1", [US_SOURCE, AU_SOURCE]).fetchall())
    checks["new_document_canonical_duplicates"] = c.execute("SELECT count(*) FROM (SELECT canonical_url FROM documents WHERE source_id IN (?,?) GROUP BY 1 HAVING count(*)>1)", [US_SOURCE, AU_SOURCE]).fetchone()[0]
    checks["us_agency_associations"] = c.execute("SELECT count(*) FROM document_organisations x JOIN documents d USING(document_id) WHERE d.source_id=?", [US_SOURCE]).fetchone()[0]
    checks["au_attachment_links"] = c.execute("SELECT count(*) FROM document_content_objects x JOIN documents d USING(document_id) WHERE d.source_id=? AND x.relationship_type='attachment'", [AU_SOURCE]).fetchone()[0]
    checks["au_day_or_month_dates"] = c.execute("SELECT count(*) FROM us_au_record_evidence WHERE source_series=? AND date_precision IN ('day','month')", [AU_SOURCE]).fetchone()[0]
    checks["au_year_only_dates"] = c.execute("SELECT count(*) FROM us_au_record_evidence WHERE source_series=? AND date_precision='year'", [AU_SOURCE]).fetchone()[0]
    checks["au_unknown_dates"] = c.execute("SELECT count(*) FROM us_au_record_evidence WHERE source_series=? AND date_precision='unknown'", [AU_SOURCE]).fetchone()[0]
    checks["orphan_segments"] = c.execute("SELECT count(*) FROM text_segments s LEFT JOIN content_versions v USING(content_version_id) WHERE v.content_version_id IS NULL").fetchone()[0]
    checks["unmapped_new_clean_segments"] = c.execute("""SELECT count(*) FROM text_segments s
        LEFT JOIN (SELECT DISTINCT clean_segment_id FROM us_au_clean_source_map) m ON m.clean_segment_id=s.segment_id
        WHERE s.representation_kind='cleaned' AND s.extraction_run_id IN
        (SELECT extraction_run_id FROM extraction_runs WHERE batch_id IN ('us_fr_epa_doe_rules_1994_v1','au_dcceew_2026_snapshot_v1'))
        AND m.clean_segment_id IS NULL""").fetchone()[0]
    versions = c.execute("""SELECT DISTINCT v.content_version_id, v.raw_path, v.storage_sha256, v.byte_size
        FROM content_versions v JOIN document_content_objects x USING(content_object_id)
        JOIN documents d USING(document_id) WHERE d.source_id IN (?,?)""", [US_SOURCE, AU_SOURCE]).fetchall()
    mismatches = []
    for vid, raw_path, digest, size in versions:
        path = ROOT / raw_path
        if not path.exists() or path.stat().st_size != size or file_sha(path) != digest:
            mismatches.append({"version": vid, "path": raw_path})
    checks["verified_content_versions"] = len(versions) - len(mismatches)
    checks["hash_or_size_mismatches"] = mismatches
    checks["us_multi_agency_parents"] = c.execute("""SELECT count(*) FROM
        (SELECT d.document_id FROM documents d JOIN document_organisations x USING(document_id)
        WHERE d.source_id=? GROUP BY 1 HAVING count(*)=2)""", [US_SOURCE]).fetchone()[0]
    checks["us_publication_date_null"] = c.execute("SELECT count(*) FROM documents WHERE source_id=? AND publication_date IS NULL", [US_SOURCE]).fetchone()[0]
    checks["au_month_imputed_from_cms"] = c.execute("""SELECT count(*) FROM documents d JOIN us_au_record_evidence e USING(document_id)
        WHERE d.source_id=? AND e.date_precision='unknown' AND d.publication_date IS NOT NULL""", [AU_SOURCE]).fetchone()[0]
    (HERE / "reports" / "integrity_audit.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))
    c.close()


if __name__ == "__main__": main()
