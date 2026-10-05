"""Vectorized, idempotent metadata seed after the row-wise transaction hit RAM limits."""
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from acquire import AU_CSV, AU_SOURCE, DB, HERE, US_CSV, US_SOURCE, au_rows, rel, sid, us_raw_url, us_rows


STAGE = HERE / "checkpoints" / "metadata_stage"
STAGE.mkdir(parents=True, exist_ok=True)
N = "\\N"


def write_table(name, records):
    path = STAGE / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for record in records:
            w.writerow([N if x is None else x for x in record])
    return path


def main():
    stamp = datetime.now(timezone.utc).isoformat()
    stage = defaultdict(list)
    for r in us_rows():
        did = sid("doc", US_SOURCE, r["canonical_url"])
        oid = sid("obj", "us_fr_raw", r["canonical_url"])
        stage["documents"].append((did, US_SOURCE, r["canonical_url"], r["canonical_url"], r["title"], "en", r["publication_date"], None,
            "Federal Register publication_date; day", None, stamp, "policy", r["genre"], "document", None, "original", "not_requested", "Metadata enumerated; body pending",
            "canonical_URL_and_date", "cross_agency_deduplicated", "internal_only_rights_not_reassessed", "pending", "Project-authorised; no UQ institutional approval/exemption asserted", True))
        stage["us_au_record_evidence"].append((did, US_SOURCE, r["publication_date"], "day", r["agency_names_from_api"], None, rel(US_CSV), None, "format_links_pending", "enumerated"))
        stage["content_objects"].append((oid, "webpage", r["document_number"], us_raw_url(r), "text/plain", None, None, "public", "internal_only", "pending", r["title"], "not_attempted",
            json.dumps({"canonical_html_url": r["canonical_url"], "representation": "official raw-text route"})))
        stage["document_content_objects"].append((did, oid, "landing_page", 0))
        agencies = r["agency_strata"].split(";")
        for agency in agencies:
            orgid = sid("org", "us_fr", agency)
            stage["organisations"].append((orgid, agency, "Environmental Protection Agency" if agency == "EPA" else "Energy Department",
                 "https://www.federalregister.gov/agencies/" + ("environmental-protection-agency" if agency == "EPA" else "energy-department")))
            stage["document_organisations"].append((did, orgid, "official_API_agency_hierarchy_stratum", "unknown", 1.0, 1.0/len(agencies), "verified_partition_membership"))
    for r in au_rows():
        did = sid("doc", AU_SOURCE, r["landing_url"])
        oid = sid("obj", "au_landing", r["landing_url"])
        stage["documents"].append((did, AU_SOURCE, r["landing_url"], r["landing_url"], r["title"], "en", None, None,
            "Original date unresolved; CMS timestamp excluded", None, stamp, "policy", "catalogue_publication_candidate", "document", None, "original", "not_requested",
            "Landing and primary-file boundary pending", "canonical_landing_URL_candidate", "original_work_identity_pending", "internal_only_rights_not_reassessed", "pending",
            "Project-authorised; no UQ institutional approval/exemption asserted", True))
        stage["us_au_record_evidence"].append((did, AU_SOURCE, None, "unknown", None, r["catalogue_created_at"], rel(AU_CSV), r["catalogue_page"], "primary_file_unknown", "catalogue_candidate"))
        stage["content_objects"].append((oid, "webpage", None, r["landing_url"], "text/html", None, None, "public", "internal_only", "pending", r["title"], "not_attempted",
            json.dumps({"role": "catalogue_landing", "original_date_unknown": True})))
        stage["document_content_objects"].append((did, oid, "landing_page", 0))
    c = duckdb.connect(str(DB))
    c.execute("SET threads=1")
    c.execute("SET memory_limit='4GB'")
    c.execute("SET preserve_insertion_order=false")
    c.execute("INSERT INTO acquisition_authorizations VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
        [sid("auth", "us_au_government_2026_09_26"), stamp, "Dai Pan",
         "Directly collect, store, insert and clean US/Australian government source texts within the fixed 1988-01-01..2026-09-21 study window.",
         "Explicit user direction relayed to this independent acquisition task", "Current delegated task instruction",
         "project_authorized_for_public_source_collection_storage_and_cleaning", "not_asserted_no_UQ_HREC_approval_or_exemption_recorded",
         "internal_research_storage_source_extraction_and_initial_cleaning", "raw_full_text_internal_only_not_cleared_for_public_redistribution",
         json.dumps({"US": "EPA/DOE RULE/PRORULE 1994+", "AU": "DCCEEW current publications catalogue and verified originals"}),
         "01a0a369-5516-7492-a412-adbbabfb032f"])
    for table in ["documents", "content_objects", "organisations", "us_au_record_evidence", "document_content_objects", "document_organisations"]:
        records = stage[table]
        if table == "organisations":
            records = list({x[0]: x for x in records}.values())
        path = write_table(table, records)
        columns = [r[1] for r in c.execute(f"PRAGMA table_info('{table}')").fetchall()]
        # Headers let DuckDB retain the exact schema column order in the stage.
        body = path.read_text(encoding="utf-8")
        with path.open("w", encoding="utf-8") as f:
            f.write(",".join(columns) + "\n")
            f.write(body)
        escaped = str(path).replace("'", "''")
        c.execute(f"INSERT INTO {table} SELECT * FROM read_csv('{escaped}', header=true, all_varchar=true, nullstr='\\N') ON CONFLICT DO NOTHING")
        print(table, len(records), "total", c.execute(f"SELECT count(*) FROM {table}").fetchone()[0], flush=True)
    c.close()


if __name__ == "__main__": main()
