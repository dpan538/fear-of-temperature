"""Full saved-byte and parent/segment integrity audit for sidecar stages."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from acquire import HERE, ROOT

EU=HERE.parent/"10_eu_cellar_acquisition"
HIST=HERE/"raw"/"us_fr_annual_index"
UK=HERE.parent/"06_government_content_acquisition"/"fear_temperature_government_content.duckdb"
OUT=HERE/"reports"/"staging_quality_audit.json"


def sha_file(path):
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1048576),b""):
            digest.update(block)
    return digest.hexdigest()


def audit_eu():
    c=duckdb.connect(str(EU/"eu_stage.duckdb"),read_only=True)
    has_blocks=c.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='eu_source_blocks'").fetchone()[0]>0
    versions=c.execute("SELECT version_id,sha256,raw_path FROM eu_content_versions").fetchall()
    mismatches=[]
    for vid,digest,raw in versions:
        path=EU/raw
        if not path.exists() or sha_file(path)!=digest:
            mismatches.append(vid)
    result={"works":c.execute("SELECT COUNT(*) FROM eu_works").fetchone()[0],
            "work_dates":c.execute("SELECT COUNT(*) FROM eu_work_dates").fetchone()[0],
            "month_bins":c.execute("SELECT COUNT(*) FROM eu_month_status").fetchone()[0],
            "item_candidates":c.execute("SELECT COUNT(*) FROM eu_item_candidates").fetchone()[0],
            "versions":len(versions),"page_segments":c.execute("SELECT COUNT(*) FROM eu_source_pages").fetchone()[0],
            "structured_blocks":c.execute("SELECT COUNT(*) FROM eu_source_blocks").fetchone()[0] if has_blocks else 0,
            "version_hash_mismatches":mismatches,
            "orphan_versions":c.execute("SELECT COUNT(*) FROM eu_content_versions v LEFT JOIN eu_item_candidates i USING(item_uri) WHERE i.item_uri IS NULL").fetchone()[0],
            "orphan_pages":c.execute("SELECT COUNT(*) FROM eu_source_pages p LEFT JOIN eu_content_versions v USING(version_id) WHERE v.version_id IS NULL").fetchone()[0],
            "orphan_structured_blocks":c.execute("SELECT COUNT(*) FROM eu_source_blocks b LEFT JOIN eu_content_versions v USING(version_id) WHERE v.version_id IS NULL").fetchone()[0] if has_blocks else 0,
            "invalid_work_dates":c.execute("SELECT COUNT(*) FROM eu_work_dates WHERE length(document_date) != 10 OR substr(document_date,5,1) != '-'").fetchone()[0]}
    c.close();return result


def audit_au():
    c=duckdb.connect(str(HERE/"au_browser_stage.duckdb"),read_only=True)
    versions=c.execute("SELECT version_id,sha256,raw_path FROM au_browser_versions").fetchall()
    mismatches=[]
    for vid,digest,raw in versions:
        path=ROOT/raw
        if not path.exists() or sha_file(path)!=digest:
            mismatches.append(vid)
    result={"works":c.execute("SELECT COUNT(*) FROM au_browser_works").fetchone()[0],
            "versions":len(versions),"page_segments":c.execute("SELECT COUNT(*) FROM au_browser_pages").fetchone()[0],
            "version_hash_mismatches":mismatches,
            "orphan_versions":c.execute("SELECT COUNT(*) FROM au_browser_versions v LEFT JOIN au_browser_works w USING(landing_url) WHERE w.landing_url IS NULL").fetchone()[0],
            "orphan_pages":c.execute("SELECT COUNT(*) FROM au_browser_pages p LEFT JOIN au_browser_versions v USING(version_id) WHERE v.version_id IS NULL").fetchone()[0],
            "unknown_original_dates":c.execute("SELECT COUNT(*) FROM au_browser_works WHERE date_precision='unknown'").fetchone()[0],
            "issuer_scope_review":c.execute("SELECT COUNT(*) FROM au_browser_works WHERE scope_status LIKE '%review_required%'").fetchone()[0]}
    c.close();return result


def audit_historic():
    issues=[]
    for path in sorted((HIST/"issues").glob("FR-*.pdf")):
        meta_path=path.with_suffix(".request.json")
        meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
        issues.append({"issue":path.stem,"hash_match":meta.get("status")=="downloaded"
                       and path.stat().st_size==meta.get("byte_count") and sha_file(path)==meta.get("sha256")})
    indexes=[]
    for path in sorted(HIST.glob("GPO-FR-INDEX-*.pdf")):
        meta_path=path.with_suffix(".request.json")
        meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
        indexes.append({"year":path.stem[-4:],"hash_match":meta.get("status")=="downloaded"
                        and path.stat().st_size==meta.get("byte_count") and sha_file(path)==meta.get("sha256")})
    samples=[]
    for path in sorted((HIST/"sample_rules").glob("*.json")):
        meta=json.loads(path.read_text())
        source=HIST.parent/meta["source_path"]
        cleaned=HIST.parent/meta["cleaned_path"]
        issue=HIST/"issues"/f"FR-{meta['issue_date']}.pdf"
        samples.append({"fr_doc_number":meta["fr_doc_number"],
                        "issue_hash_match":issue.exists() and sha_file(issue)==meta["source_issue_sha256"],
                        "source_hash_match":source.exists() and sha_file(source)==meta["source_sha256"],
                        "cleaned_hash_match":cleaned.exists() and sha_file(cleaned)==meta["cleaned_sha256"]})
    return {"saved_issue_pdfs":len(issues),"issue_hash_mismatches":[x["issue"] for x in issues if not x["hash_match"]],
            "saved_annual_indexes":len(indexes),"index_hash_mismatches":[x["year"] for x in indexes if not x["hash_match"]],
            "bounded_rule_samples":len(samples),"samples":samples}


def main():
    uk_sha256=sha_file(UK)
    result={"audited_at_utc":datetime.now(timezone.utc).isoformat(),
            "eu_stage":audit_eu(),"au_browser_stage":audit_au(),
            "historical_issue_samples":audit_historic(),
            "uk_baseline_sha256":uk_sha256,
            "uk_baseline_sha256_unchanged":uk_sha256=="d6c285649048f7910810630dc3da8479efcca7c38e35f903a5d20eae20e90465"}
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"eu_versions":result["eu_stage"]["versions"],"eu_mismatches":len(result["eu_stage"]["version_hash_mismatches"]),
                      "au_versions":result["au_browser_stage"]["versions"],"au_mismatches":len(result["au_browser_stage"]["version_hash_mismatches"]),
                      "historical_samples":result["historical_issue_samples"]["bounded_rule_samples"],
                      "uk_unchanged":result["uk_baseline_sha256_unchanged"]}),flush=True)


if __name__=="__main__":main()
