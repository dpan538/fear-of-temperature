"""Write a compact cross-source progress snapshot without touching the US DB."""
import csv
import json
import shutil
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from acquire import HERE

EU = HERE.parent / "10_eu_cellar_acquisition"
HIST = HERE / "raw" / "us_fr_annual_index"
OUT = HERE / "reports" / "acquisition_progress_snapshot.md"


def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def scalar(db, query):
    c=duckdb.connect(str(db),read_only=True)
    result=c.execute(query).fetchone()[0]
    c.close()
    return result


def eu_counts(db):
    for attempt in range(20):
        try:
            c=duckdb.connect(str(db),read_only=True)
            break
        except duckdb.IOException:
            if attempt == 19:
                raise
            time.sleep(0.5)
    try:
        has_blocks=c.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='eu_source_blocks'").fetchone()[0]
        return {"works":c.execute("SELECT COUNT(*) FROM eu_works").fetchone()[0],
                "versions":c.execute("SELECT COUNT(*) FROM eu_content_versions").fetchone()[0],
                "pages":c.execute("SELECT COUNT(*) FROM eu_source_pages").fetchone()[0],
                "structured_blocks":c.execute("SELECT COUNT(*) FROM eu_source_blocks").fetchone()[0] if has_blocks else 0}
    finally:
        c.close()


def main():
    us=json.loads((HERE/"checkpoints"/"supervisor_state.json").read_text())
    completed_early_group = 10_237 if us.get("year_scope", [0])[0] >= 2003 else 0
    au=csv_rows(HERE/"reports"/"au_candidate_outcomes.csv")
    au_outcomes=Counter(row["outcome"] for row in au)
    months=[json.loads(p.read_text()) for p in (EU/"manifests"/"months").glob("*.json")]
    wemi=[json.loads(p.read_text()) for p in (EU/"manifests"/"wemi").glob("*.json")]
    item_roots=[EU/"raw"/"items",EU/"raw"/"items_external"]
    eu_items=[json.loads(p.read_text()) for root in item_roots if root.exists() for p in root.glob("*/*.request.json")]
    eu_downloads=[x for x in eu_items if x.get("status")=="downloaded"]
    eu_extract=[json.loads(p.read_text()) for root in item_roots if root.exists() for p in root.glob("*/*.extract.json")]
    hist=[json.loads((HIST/f"{y}_parent_agency_candidate_locators.summary.json").read_text()) for y in range(1988,1994)]
    resolved={}
    for y in range(1988,1994):
        checkpoints=[json.loads(p.read_text()) for p in (HIST/f"{y}_resolved_pages").glob("*.request.json")]
        resolved[y] = {"pages":hist[y-1988]["unique_pages"] if "unique_pages" in hist[y-1988] else len({r["fr_start_page_candidate"] for r in csv_rows(HIST/f"{y}_parent_agency_candidate_locators.csv")}),
                       "resolved":sum(row.get("state")=="resolved_to_issue_page" for row in checkpoints),
                       "issue_dates":len({row.get("issue_date") for row in checkpoints if row.get("issue_date")})}
    eu_db=EU/"eu_stage.duckdb"
    au_db=HERE/"au_browser_stage.duckdb"
    eu_stage=eu_counts(eu_db)
    au_stage={"works":scalar(au_db,"SELECT COUNT(*) FROM au_browser_works"),
              "versions":scalar(au_db,"SELECT COUNT(*) FROM au_browser_versions"),
              "pages":scalar(au_db,"SELECT COUNT(*) FROM au_browser_pages"),
              "eligible_dated":scalar(au_db,"SELECT COUNT(*) FROM au_browser_works WHERE original_date <> '' AND original_date < '2026-09' AND scope_status NOT LIKE '%review_required%'"),
              "issuer_review":scalar(au_db,"SELECT COUNT(*) FROM au_browser_works WHERE scope_status LIKE '%review_required%'"),
              "unknown_date":scalar(au_db,"SELECT COUNT(*) FROM au_browser_works WHERE date_precision='unknown'")}
    work_audit=json.loads((EU/"reports"/"work_enumeration_audit.json").read_text())
    wemi_audit=json.loads((EU/"reports"/"wemi_relationship_audit.json").read_text())
    dispositions=json.loads((EU/"reports"/"eu_work_dispositions.summary.json").read_text())
    us_quality=json.loads((HERE/"reports"/"quality_metrics.json").read_text())
    ocr_sidecars=[json.loads(p.read_text()) for root in item_roots if root.exists() for p in root.glob("*/*.ocr.meta.json")]
    page_alignment=json.loads((HIST/"saved_issue_page_alignment.summary.json").read_text())
    size_sample=json.loads((HIST/"issue_size_sample.summary.json").read_text())
    free=shutil.disk_usage(HERE).free
    wemi_access=("The 1997-02 HTTP 503 with Retry-After 1800 seconds was honored; the same WEMI checkpoint reconciled on the slower retry."
                 if (EU/"manifests"/"wemi"/"1997-02.json").exists()
                 else "WEMI SPARQL access paused at 1997-02 after HTTP 503 with Retry-After 1800 seconds (not before 2026-09-26 15:20:06 UTC).")
    later_503=EU/"raw"/"wemi_pages"/"2007"/"2007-04_batch_0002.request.json"
    if later_503.exists():
        later_meta=json.loads(later_503.read_text())
        if later_meta.get("http_status")==503 and not (EU/"manifests"/"wemi"/"2007-04.json").exists():
            wemi_access += f" The 2007-04 HTTP 503 is waiting until {later_meta.get('retry_not_before_utc','unknown')} before the single supervisor retries."
        elif (EU/"manifests"/"wemi"/"2007-04.json").exists():
            wemi_access += " The later 2007-04 Retry-After checkpoint also reconciled."
    lines=["# Government acquisition progress snapshot","",
           f"Generated: {datetime.now(timezone.utc).isoformat()}","",
           "This is a checkpoint snapshot while source acquisition continues; it is not the final full-hash corpus audit.","",
           "## US Federal Register 1994–2026","",
           f"- Frozen unique API parents: 33,544. Latest supervisor scope: {us['year_scope'][0]}–{us['year_scope'][1]} with {us['target']:,} targets.",
           f"- Supervisor: {us['status']}; {us['downloaded']:,} verified downloads and {us['ingested']:,} ingested parents in its current year scope after {us['cycles']} cycles, last checkpoint {us['updated_at_utc']}.",
           f"- Last full US report ({us_quality['generated_at_utc']}) counted {us_quality['US_downloaded_verified']:,}/33,544 committed verified bodies, including {us_quality.get('US_raw_text_404_or_410_recovered_by_govinfo_html',0)} official GovInfo HTML fallbacks. The 1994–2002 group has 10,237/10,237 bodies. Current later-year access status: {us['status']}.",
           f"- Current checkpoint total across the completed early group and later-year scope: {completed_early_group + us['downloaded']:,} verified bodies and {completed_early_group + us['ingested']:,} ingested parents; the batch counters are checkpoint totals, not the last full audit.",
           "- The 09 DuckDB writer is single-process. Later years and remaining current-scope parents are pending.","",
           "## US historical 1988–1993","",
           "- Six official annual index PDFs saved with request checkpoints and extractable OCR text.",
           f"- {len(list((HIST/'issues').glob('FR-*.pdf')))} full official issue PDFs are saved and hash checked; these are source containers, not article counts.",
           f"- Candidate parent-heading index tokens by year: " + ", ".join(f"{x['year']}: {x['index_locator_rows']:,}" for x in hist) + ". These are page references, not Work counts.",
           "- Official link-service issue-date/jump-fragment resolutions by year: " + ", ".join(f"{y}: {resolved[y]['resolved']:,}/{resolved[y]['pages']:,}" for y in range(1988,1994)) + ". Jump fragments are unverified PDF page locators until checked in the scans.",
           f"- Across all six years, {sum(x['index_locator_rows'] for x in hist):,} index tokens / {sum(resolved[y]['pages'] for y in range(1988,1994)):,} distinct candidate pages map to {sum(resolved[y]['issue_dates'] for y in range(1988,1994)):,} issue dates. None of these totals is a verified article denominator.",
           "- Six final/proposed-rule samples are independently bounded from official issues: DOE 53 FR 21646 / FR Doc. 88-13009, EPA 53 FR 20 / FR Doc. 87-29874, EPA 53 FR 126 / FR Doc. 88-50, EPA 53 FR 392 / FR Doc. 88-177, DOE 54 FR 17734 / FR Doc. 89-9909, and EPA 54 FR 17769 / FR Doc. 89-9872. Source and cleaned text are saved. `53 FR 3` was a false index token, and the 53 FR 392 jump fragment pointed eight PDF pages too late. Historical denominator remains unknown.","",
           f"- Saved-scan page-header audit: {page_alignment['candidate_locator_rows_in_saved_issues']} locator rows, " + ", ".join(f"{k} {v}" for k,v in page_alignment['alignment_status_counts'].items()) + ". Page alignment does not establish article identity.","",
           f"- Storage sample: {size_sample['valid_content_lengths']}/{size_sample['sampled_issues']} official issue PDF headers returned lengths, median {size_sample['median_bytes']/1_000_000:.1f} MB. Median × 1,325 dates is about {size_sample['median_extrapolation_bytes']/1_000_000_000:.0f} GB, a rough capacity estimate rather than a total or rule count.","",
           "## Australia DCCEEW catalogue","",
           f"- Frozen landing candidates: {len(au):,}. Current outcomes: " + ", ".join(f"{key} {value}" for key,value in sorted(au_outcomes.items())) + ".",
           f"- Browser stage: {au_stage['works']} landing Works with saved files, {au_stage['versions']} verified versions, {au_stage['pages']} source/cleaned PDF pages. {au_stage['eligible_dated']} have eligible pre-cutoff original dates, {au_stage['issuer_review']} require issuer-scope review, and {au_stage['unknown_date']} have unresolved original dates.",
           "- Direct HTTP requests to the current host failed with a timeout or HTTP/2 stream error; ordinary in-app browser visits/downloads worked for the saved originals. The remaining 807 landings received read-only web-reader queries, with errors and omitted responses retained as unresolved, not absent originals. Web page/PDF links add no downloaded original bytes.","",
           "## EU Commission CELLAR","",
           f"- Monthly Work bins: {len(months)}/465 reconciled; sum of official month counts {sum(x['expected_distinct_works'] for x in months):,}. The stage has {eu_stage['works']:,} unique Work parents with official document dates.",
           f"- English WEMI months complete: {len(wemi)}/465; {sum(x['works_with_items'] for x in wemi):,} Works with at least one Item link in those months; {sum(x['works_without_items'] for x in wemi):,} without an Item link.",
           f"- Original Item streams: {len(eu_downloads):,} verified downloads; {sum(x.get('status')=='text_extracted' for x in eu_extract):,} text-extracted records. The stage currently has {eu_stage['versions']:,} versions, {eu_stage['pages']:,} PDF page segments and {eu_stage['structured_blocks']:,} HTML/DOC text blocks; it is refreshed after each completed download cohort.",
           f"- Scan-only PDFs with local OCR sidecars: {sum(x.get('status')=='ocr_candidate_text_extracted' for x in ocr_sidecars)}; these are page-linked candidate transcriptions pending source-layout review.",
           f"- Per-Work disposition ledger: {dispositions['unique_works']:,} globally unique Works; " + ", ".join(f"{key} {value:,}" for key,value in sorted(dispositions['status_counts'].items())) + ". Extraction and OCR remain subject to relevance and layout review.",
           "- The 2024-08 zero applies only to the frozen `act_preparatory` class. An official CELLAR diagnostic identified an August 2024 COM proposal in the adjacent `proposal_decision_implementing_ec` class; the class boundary is documented in the EU runbook without changing this denominator.",
           f"- Independent raw-page audits: Work enumeration {work_audit['official_months']}/465 months and {work_audit['globally_distinct_works']:,} global Works, {work_audit['issue_count']} discrepancies; WEMI {wemi_audit['completed_months']} completed months / {wemi_audit['saved_batch_pages']} raw batches, {wemi_audit['issue_count']} discrepancies at {wemi_audit['audited_at_utc']}.",
           f"- {wemi_access} The content stream route is being processed independently.","",
           f"Free disk: {free/1_000_000_000:.2f} GB. No proposal/model edits, commits, or pushes are part of this acquisition run.",""]
    OUT.write_text("\n".join(lines))
    print(json.dumps({"snapshot":str(OUT),"eu_months":len(months),"eu_wemi_months":len(wemi),"eu_items":len(eu_downloads),"us_downloaded_current_scope":us["downloaded"],"free_bytes":free}),flush=True)


if __name__=="__main__":main()
