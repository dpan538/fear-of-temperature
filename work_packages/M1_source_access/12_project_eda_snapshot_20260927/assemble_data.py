"""Freeze figure-specific inputs from read-only project evidence."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SOURCE = ROOT / "work_packages/M1_source_access"
POOLED = SOURCE / "09_us_au_government_acquisition/reports/pooled_month_role_coverage_2026-09-27.csv"
UPDATED = SOURCE / "09_us_au_government_acquisition/reports/targeted_2015_bridge/updated_monthly_government_presence.csv"
BRIDGE = SOURCE / "09_us_au_government_acquisition/reports/targeted_2015_bridge/parent_acceptance.csv"
PILOT = SOURCE / "11_paris_readiness_pilot_20260927"
ROUND2 = PILOT / "round2_december_2015/paris_month_role_readiness_49x3_round2.csv"
QUANT = SOURCE / "07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/record_text_length_distribution.csv"
UKDB = SOURCE / "06_government_content_acquisition/fear_temperature_government_content.duckdb"
SNAPSHOT = SOURCE / "09_us_au_government_acquisition/reports/pooled_month_role_snapshot_2026-09-27.md"
FMT = SOURCE / "06_government_content_acquisition/text_quality_review/01_format_summary.csv"
SEGLEN = SOURCE / "06_government_content_acquisition/text_quality_review/03_segment_length_distribution.csv"
QUALITY = SOURCE / "06_government_content_acquisition/text_quality_review/text_quality_report_for_dai.md"
INPUTS = [POOLED, UPDATED, BRIDGE, ROUND2, QUANT, UKDB,
          PILOT / "government_pilot_review.csv", PILOT / "media_pilot_review.csv",
          PILOT / "public_pilot_review.csv", SNAPSHOT, FMT, SEGLEN, QUALITY,
          PILOT / "round2_december_2015/guardian_dec2015_article_metadata.csv",
          PILOT / "round2_december_2015/petition_177_id_date_mapping.csv"]


def save(name: str, frame: pd.DataFrame) -> None:
    frame.to_csv(DATA / name, index=False)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    p = pd.read_csv(POOLED).query("role == 'government'").copy()
    u = pd.read_csv(UPDATED)
    m = p.merge(u, on="year_month", validate="one_to_one")
    b = pd.read_csv(BRIDGE)
    r = pd.read_csv(ROUND2)

    eu_saved = int(re.search(r"([\d,]+) saved Item versions", SNAPSHOT.read_text()).group(1).replace(",", ""))
    inventory = pd.DataFrame([
        ["UK", "independent parent", int(u.uk_independent_records.sum()), int(u.uk_records_with_text.sum()), int(u.uk_records_with_text.sum()), "UK read-only DB + 12:36 UTC source-text audit"],
        ["US selected", "selected parent", int(p.us_dated_parents.sum()), int(p.us_cleaned_parents.sum()+len(b)), int(p.us_cleaned_parents.sum()+len(b)), "10:53 UTC checkpoint + 125 committed EPA originals"],
        ["EU", "preparatory Work", int(p.eu_dated_works.sum()), eu_saved, int(p.eu_source_text_parents.sum()), "10:53 UTC; 27 placeholder-only extractions excluded"],
        ["AU verified", "original parent", int(p.au_original_month_parents.sum()), int(p.au_cleaned_parents.sum()), int(p.au_cleaned_parents.sum()), "10:53 UTC checkpoint"],
    ], columns=["source", "unit", "dated", "saved_original", "readable_text", "checkpoint"])
    save("figure_01_inventory.csv", inventory)
    articles = pd.read_csv(PILOT / "round2_december_2015/guardian_dec2015_article_metadata.csv")
    petitions = pd.read_csv(PILOT / "round2_december_2015/petition_177_id_date_mapping.csv")
    save("figure_01_pilots.csv", pd.DataFrame([
        ["Guardian Dec 2015", "candidate article URL", articles.article_url.nunique(), "current archive; four body checks"],
        ["Petition q=climate", "distinct submitted ID", petitions.petition_id.nunique(), f"{int(petitions.published_only_eligible.sum())} published; {int((petitions.state == 'rejected').sum())} rejected"],
    ], columns=["source", "unit", "count", "qualification"]))

    rows = []
    for _, x in m.iterrows():
        ym = x.year_month
        source_values = [
            ("UK", int(x.uk_independent_records), int(x.uk_records_with_text)),
            ("EU", int(x.eu_enumerated_works), int(x.eu_source_text_parents)),
            ("US", int(x.us_dated_parents), int(x.us_cleaned_parents + x.targeted_us_epa_final_rule_source_text_parents)),
            ("AU", int(x.au_original_month_parents), int(x.au_cleaned_parents)),
        ]
        for source, dated, text in source_values:
            status = "readable" if text else "metadata only" if dated else "unaudited or absent"
            rows.append([ym, source, dated, text, status])
        rows.append([ym, "Pooled government", int(x.uk_independent_records + x.eu_enumerated_works + x.us_dated_parents + x.au_original_month_parents), int(x.pooled_government_text_present_updated), "readable" if x.pooled_government_text_present_updated else "metadata only"])
        for role in ["media", "public"]:
            rr = r[(r.month == ym) & (r.role == role)]
            if rr.empty:
                status = "unaudited or absent"
                dated = text = 0
            else:
                z = rr.iloc[0]
                status = "readable pilot" if z.coverage_state in ("sampled_readable_parent_present", "monthly_archive_candidate_frame_dated_body_subset", "published_query_hit_readable") else "confirmed query zero" if z.coverage_state == "verified_zero_within_published_keyword_query" else "unaudited or absent"
                dated = int(z.dated_independent_parent_count) if pd.notna(z.dated_independent_parent_count) else 0
                text = int(z.readable_independent_parent_count) if pd.notna(z.readable_independent_parent_count) else 0
            rows.append([ym, role.title() + " pilot", dated, text, status])
    coverage = pd.DataFrame(rows, columns=["month", "source", "dated_count", "text_count_or_presence", "status"])
    save("figure_02_months.csv", coverage)

    con = duckdb.connect(str(UKDB), read_only=True)
    uk = con.execute("""SELECT year(publication_date) AS year, content_type AS genre,
        count(DISTINCT document_id) AS parent_count FROM documents
        WHERE publication_date >= DATE '1988-01-01' AND publication_date < DATE '2026-10-01'
        GROUP BY 1,2 ORDER BY 1,2""").df()
    con.close()
    uk["source"] = "UK"
    uk = uk.rename(columns={"parent_count": "count"})
    other = []
    for source, dated_col, text_col in [("EU", "eu_dated_works", "eu_source_text_parents"), ("US", "us_dated_parents", "us_cleaned_parents")]:
        q = p.copy()
        q["year"] = q.year_month.str[:4].astype(int)
        for year, group in q.groupby("year"):
            extra = int(b[b.year_month.str.startswith(str(year))].shape[0]) if source == "US" else 0
            other.append([year, source, "selected parents" if source == "US" else "preparatory Works", int(group[dated_col].sum()), int(group[text_col].sum()) + extra])
    uk["readable_count"] = pd.NA
    annual = pd.concat([uk, pd.DataFrame(other, columns=["year", "source", "genre", "count", "readable_count"])], ignore_index=True)
    save("figure_03_annual.csv", annual)

    seen = set()
    geo = []
    for source in ["UK", "EU", "US", "AU"]:
        months = set(coverage[(coverage.source == source) & (coverage.status == "readable")].month)
        geo.append([source, "Government", len(months), len(months - seen), "full or bounded official source"])
        seen |= months
    geo += [["UK (Guardian)", "Media pilot", 3, None, "sampled bodies; Dec candidates only"], ["UK (petitions)", "Public pilot", 19, None, "published q=climate query months only"]]
    save("figure_04_footprint.csv", pd.DataFrame(geo, columns=["issuer_scope", "role", "text_months", "incremental_government_months", "qualification"]))

    q = pd.read_csv(QUANT)
    q = q[q.measure == "character_count"].copy()
    q["source"] = "UK"
    epachars = b.source_characters.dropna().astype(float)
    ep = pd.DataFrame([["US EPA bridge", "character_count", f"p{n:02d}", float(epachars.quantile(n / 100)), len(epachars), "US"] for n in [10, 25, 50, 75, 90, 95]], columns=q.columns.tolist() + ["source"] if "source" not in q.columns else q.columns)
    shape = pd.concat([q, ep], ignore_index=True)
    save("figure_05_text_shape.csv", shape)
    fmt = pd.read_csv(FMT).query("row_type == 'group'")
    seg = pd.read_csv(SEGLEN).query("scope_type == 'format_group'")
    fs = fmt.merge(seg[["scope_value", "p50_chars"]], left_on="format_group", right_on="scope_value", validate="one_to_one")
    fs["format"] = "UK " + fs.format_group.str.upper().where(fs.format_group.isin(["pdf", "csv"]), fs.format_group)
    save("figure_05_format.csv", fs.rename(columns={"object_count":"objects", "extraction_success_count":"extracted_objects", "segment_count":"segments", "p50_chars":"median_segment_characters"})[["format","objects","extracted_objects","segments","median_segment_characters"]])
    quality_text = QUALITY.read_text()
    statuses = []
    for status in ["needs_ocr", "unsupported_format", "extraction_failed"]:
        count = int(re.search(rf"`{status}`：([\d,]+) 个对象", quality_text).group(1).replace(",", ""))
        statuses.append(["UK quality snapshot", status, count])
    statuses += [["EU 10:53 UTC checkpoint", "ocr_review_candidate", int(p.eu_ocr_review_candidates.sum())],
                 ["EU 10:53 UTC checkpoint", "scan_ocr_pending", int(p.eu_scan_ocr_pending.sum())]]
    save("figure_05_status.csv", pd.DataFrame(statuses, columns=["snapshot", "status", "objects_or_items"]))

    readiness = r[["month", "role", "dated_independent_parent_count", "readable_independent_parent_count", "pilot_reviewed_parent_count", "pilot_verified_climate_warming_parent_count", "coverage_state", "relevance_review_state", "eligible_denominator", "public_published_query_opened_count"]].copy()
    save("figure_06_paris.csv", readiness)

    review = []
    for role in ["government", "media", "public"]:
        d = pd.read_csv(PILOT / f"{role}_pilot_review.csv")
        for _, x in d.iterrows():
            pid = str(x.get("parent_id", x.get("parent_url", x.get("petition_id", ""))))
            if role == "public": pid = "petition:" + str(x.petition_id)
            if role == "media": pid = str(x.parent_url)
            review.append([role, str(x.sampling_stratum) if role != "public" else str(x.state), pid,
                           int(x.climate_warming_topic), int(x.anticipated_climate_harm_cue), int(x.explicit_fear_expression),
                           str(x.get("publication_date", x.get("original_published_at", x.get("opened_at", ""))))])
    rev = pd.DataFrame(review, columns=["role", "stratum", "parent_id", "climate_topic", "anticipated_harm", "explicit_fear", "source_date"])
    save("figure_07_review.csv", rev)
    examples = []
    for role in ["government", "media", "public"]:
        d = pd.read_csv(PILOT / f"{role}_pilot_review.csv")
        hit = d[d.climate_warming_topic == 1].iloc[0]
        examples.append([role, str(hit.get("parent_id", hit.get("parent_url", "petition:" + str(hit.get("petition_id", ""))))),
                         str(hit.get("content_versions", hit.get("response_sha256", hit.get("source_page_sha256", "")))),
                         str(hit.get("segment_locator", "body checked" if role == "media" else "petitioner-authored fields")),
                         str(hit.get("publication_date", hit.get("original_published_at", hit.get("opened_at", "")))),
                         int(hit.anticipated_climate_harm_cue)])
    save("figure_08_topology.csv", pd.DataFrame(examples, columns=["role", "parent_id", "version_or_hash", "locator", "date", "anticipated_harm"]))

    manifest = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "source_checkpoints": {"UK": "read-only DB and 12:36 UTC corrected source-text ledger", "US": "10:53 UTC pooled checkpoint plus 12:36 UTC committed 125-parent EPA bridge", "EU": "10:53 UTC pooled checkpoint; 15,299 usable text Works", "AU": "10:53 UTC pooled checkpoint", "Paris": "14:16 UTC round-2 table"},
                "inputs": [{"path": str(path.relative_to(ROOT)), "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), "bytes": path.stat().st_size} for path in INPUTS],
                "boundaries": ["source-specific checkpoints, not a synchronized census", "parent/Work units are not summed across sources", "465 pooled government text months are source presence, not climate relevance", "pilot labels are deliberately enriched diagnostics, not prevalence", "partial September 2026 bin"]}
    (HERE / "DATA_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Wrote figure inputs and manifest")


if __name__ == "__main__":
    main()
