#!/usr/bin/env python3
"""Read-only, source-specific provenance ledger from committed checkpoints.

Run from the repository root: .venv/bin/python work_packages/M1_source_access/
13_parallel_data_audit_20261004/03_source_quality/build_source_quality.py
The only writes are beside this script. review_annotations.json adds bounded manual checks.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
START, END = "1988-01-01", "2026-09-21"
UKDB = ROOT / "work_packages/M1_source_access/06_government_content_acquisition/fear_temperature_government_content.duckdb"
USCSV = ROOT / "work_packages/M1_source_access/09_us_au_government_acquisition/reports/object_status.csv"
USSPOT = ROOT / "work_packages/M1_source_access/09_us_au_government_acquisition/reports/identity_spot_checks.csv"
AUCSV = ROOT / "work_packages/M1_source_access/09_us_au_government_acquisition/reports/au_candidate_outcomes.csv"
EUCSV = ROOT / "work_packages/M1_source_access/10_eu_cellar_acquisition/reports/eu_work_dispositions.csv"
GUARDIAN = ROOT / "work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/guardian_dec2015_article_metadata.csv"
MEDIAPILOT = ROOT / "work_packages/M1_source_access/11_paris_readiness_pilot_20260927/media_pilot_review.csv"
PETITIONS = ROOT / "work_packages/M1_source_access/11_paris_readiness_pilot_20260927/round2_december_2015/petition_177_id_date_mapping.csv"
PUBLICPILOT = ROOT / "work_packages/M1_source_access/11_paris_readiness_pilot_20260927/public_pilot_review.csv"
AUORIGINAL = ROOT / "work_packages/M1_source_access/08_cross_region_government_coverage/au_primary_originals_manifest.csv"
ANNOT = OUT / "review_annotations.json"

FIELDS = ["record_level", "frame_id", "source", "evidence_role", "parent_id", "version_or_object_id", "publication_date", "publication_date_precision", "retrieval_or_snapshot_time_utc", "source_issuer", "original_utterance_url", "reproduction_or_archive_url", "local_evidence_path", "directness", "classification_basis", "identity_status", "date_status", "version_status", "content_mapping_status", "access_status", "provenance_conflict", "substantive_claim_dispute", "checked_at_utc", "evidence_reference", "review_note", "count_unit", "frame_count"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stamp(path: Path) -> dict:
    st = path.stat()
    return {"path": str(path.relative_to(ROOT)), "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(), "bytes": st.st_size}


def hashed(rows: list[dict], key: str, n: int = 1) -> list[dict]:
    return sorted(rows, key=lambda x: (hashlib.sha256(str(x[key]).encode()).hexdigest(), str(x[key])))[:n]


def frame(fid, source, role, directness, count, basis, evidence, unit, issuer, original="", archive="", note=""):
    return dict(record_level="frame_rule", frame_id=fid, source=source, evidence_role=role, parent_id="", version_or_object_id="", publication_date="", publication_date_precision="varies", retrieval_or_snapshot_time_utc="see INPUT_MANIFEST.json", source_issuer=issuer, original_utterance_url=original, reproduction_or_archive_url=archive, local_evidence_path="", directness=directness, classification_basis=basis, identity_status="not individually verified by this rule", date_status="not individually verified by this rule", version_status="not individually verified by this rule", content_mapping_status="not individually verified by this rule", access_status="see source_quality_summary.csv", provenance_conflict="not assessed from source route", substantive_claim_dispute="not assessed; independent dimension", checked_at_utc="", evidence_reference=evidence, review_note=note, count_unit=unit, frame_count=count)


def sample(fid, source, role, pid, date, precision, issuer, original, archive, local, category, basis, evidence, version=""):
    return dict(record_level="individual_sample", frame_id=fid, source=source, evidence_role=role, parent_id=str(pid), version_or_object_id=str(version), publication_date=str(date or ""), publication_date_precision=precision or "unknown", retrieval_or_snapshot_time_utc="see INPUT_MANIFEST.json", source_issuer=issuer, original_utterance_url=original or "", reproduction_or_archive_url=archive or "", local_evidence_path=local or "", directness=category, classification_basis=basis, identity_status="pending", date_status="pending", version_status="pending", content_mapping_status="pending", access_status="pending", provenance_conflict="none observed", substantive_claim_dispute="not assessed", checked_at_utc="", evidence_reference=evidence, review_note="", count_unit="parent/Work", frame_count="")


def main():
    inputs = [UKDB, USCSV, USSPOT, AUCSV, EUCSV, GUARDIAN, MEDIAPILOT, PETITIONS, PUBLICPILOT, AUORIGINAL,
              ROOT/"work_packages/M1_source_access/09_us_au_government_acquisition/FILTER_CONTRACT.md",
              ROOT/"work_packages/M1_source_access/10_eu_cellar_acquisition/FILTER_CONTRACT.md",
              ROOT/"work_packages/M1_source_access/09_us_au_government_acquisition/browser_observations.jsonl",
              ROOT/"work_packages/M1_source_access/10_eu_cellar_acquisition/reports/html_placeholder_audit.csv",
              ROOT/"work_packages/M1_source_access/12_project_eda_snapshot_20260927/DATA_MANIFEST.json",
              ROOT/"work_packages/M1_source_access/09_us_au_government_acquisition/reports/targeted_2015_bridge/parent_acceptance.csv"]
    us, spots, au, eu, guardian, media, petitions, public = map(read_csv, [USCSV, USSPOT, AUCSV, EUCSV, GUARDIAN, MEDIAPILOT, PETITIONS, PUBLICPILOT])
    assert len([x for x in us if x["series"].startswith("us_fr")]) == 33544
    assert len(au) == 821 and len(eu) == 50578 and len(guardian) == 396 and len(petitions) == 177
    con = duckdb.connect(str(UKDB), read_only=True)
    uk_routes = [
        ("UK_HISTORIC", "src_549acfda11091ff8c9b8", "UK Historic Hansard", "archival_reproduction", 2, "Official historic parliamentary archive/bulk XML reproduces dated ministerial written records."),
        ("UK_QS_API", "src_90b3a872375c9e7fd267", "UK Questions/Statements API", "original_utterance", 2, "Official API records issued written answers/statements, direct to the ministerial utterance; its current API version is not a frozen historical body."),
        ("UK_HANSARD_ARCHIVE", "src_9e8f487d372ed011db82", "UK Hansard/publications archive", "archival_reproduction", 1, "Official archive HTML/detail route reproduces parliamentary record."),
        ("UK_TWFY_MIRROR", "src_3c349b00120866c263a3", "UK ParlParse/TWFY mirror", "archival_reproduction", 1, "Third-party XML mirror of Commons written records; parliamentary date is an attribution, upstream alignment needs parent checks."),
        ("UK_GOVUK_DEFRA", "src_ac30b1ae596ab5ab5379", "UK DEFRA GOV.UK", "original_utterance", 1, "Issuer-hosted policy publication landing/attachments; original publication date is metadata, current version may differ."),
        ("UK_GOVUK_HIST", "src_eaf57ccafde8ffd97f7e", "UK historical GOV.UK", "original_utterance", 1, "Official publication route; current hosted version and historical original may differ."),
    ]
    ledger, samples, summary = [], [], []
    for fid, sid, name, cat, n_sample, basis in uk_routes:
        count = con.execute("select count(*) from documents where source_id=? and publication_date between cast(? as date) and cast(? as date)", [sid, START, END]).fetchone()[0]
        eligible = con.execute("select document_id, external_id, canonical_url, publication_date, publication_date_basis, title, body_status, updated_timestamp from documents where source_id=? and publication_date between cast(? as date) and cast(? as date) order by sha256(document_id) limit ?", [sid, START, END, n_sample]).fetchall()
        ledger.append(frame(fid, name, "government ministerial or policy record", cat, count, basis, str(UKDB.relative_to(ROOT))+"#documents,sources", "independent document parent", "Parliament/ministerial issuer" if "GOVUK" not in fid else "GOV.UK publisher; document issuer needs checking", archive="official archive or mirror as named by route" if cat == "archival_reproduction" else "", note="Rule-derived source route; no inference that claims are true."))
        for d in eligible:
            obj = con.execute("select count(distinct dco.content_object_id), count(distinct cv.content_version_id), count(distinct ts.segment_id), min(cv.raw_path), string_agg(distinct cv.content_version_id, '|') from document_content_objects dco left join content_versions cv on cv.content_object_id=dco.content_object_id left join text_segments ts on ts.content_version_id=cv.content_version_id where dco.document_id=?", [d[0]]).fetchone()
            samples.append(sample(fid,name,"government ministerial or policy record",d[0],d[3],"day", "Parliament/ministerial issuer" if "GOVUK" not in fid else "GOV.UK publisher; document issuer to check",d[2] if cat=="original_utterance" else "",d[2] if cat=="archival_reproduction" else "",str(obj[3] or ""),cat,basis,str(UKDB.relative_to(ROOT))+f"#documents:{d[0]};external_id={d[1]};objects={obj[0]};versions={obj[1]};segments={obj[2]}",obj[4] or ""))
        if fid in ("UK_GOVUK_DEFRA","UK_GOVUK_HIST"):
            mapped=con.execute("select count(distinct d.document_id) from documents d join document_content_objects dco on d.document_id=dco.document_id join content_versions cv on dco.content_object_id=cv.content_object_id join text_segments ts on cv.content_version_id=ts.content_version_id where d.source_id=? and d.publication_date between cast(? as date) and cast(? as date)",[sid,START,END]).fetchone()[0]
            availability_basis="parents with linked text segments despite parent body_status caveat"
        else:
            mapped=count
            availability_basis="parents with body_status=downloaded_and_extracted"
        summary.append(dict(frame_id=fid,source=name,evidence_role="government",count_unit="independent document parent",denominator=count,rule_derived_directness=cat,rule_derived_count=count,source_text_or_body_status_count=mapped,availability_basis=availability_basis,metadata_only_or_unfetched_count="",source_checkpoint="UK static DB; file mtime in INPUT_MANIFEST.json",frame_filter=f"source_id={sid}; publication_date {START}..{END}"))
    con.close()

    us_rows=[x for x in us if x["series"].startswith("us_fr") and START<=x["date_value"]<=END]
    for route, fid, name in [("federalregister_raw_text","US_FR_RAW","US Federal Register raw text"),("govinfo_html_fallback","US_GOVINFO_FALLBACK","US govinfo fallback")]:
        rr=[x for x in us_rows if x["source_route"]==route]
        basis="Official digitised Federal Register publication of EPA/DOE rule; agency utterance and Register issue remain distinct from current host/version."
        ledger.append(frame(fid,name,"government rule publication","archival_reproduction",len(rr),basis,str(USCSV.relative_to(ROOT))+"#source_route="+route,"selected document parent","EPA/DOE as indexed; individual issuing-agency check pending",archive="Federal Register or govinfo original publication reproduction"))
        summary.append(dict(frame_id=fid,source=name,evidence_role="government",count_unit="selected document parent",denominator=len(rr),rule_derived_directness="archival_reproduction",rule_derived_count=len(rr),source_text_or_body_status_count=sum(x["fetch_status"] in ("downloaded","reused_verified_08") for x in rr),metadata_only_or_unfetched_count=sum(x["fetch_status"] in ("not_requested","failed") for x in rr),source_checkpoint="US object-status export; file mtime in INPUT_MANIFEST.json",frame_filter=f"series=us_fr_epa_doe_rules_1994; source_route={route}; date {START}..{END}"))
    us_by_url={x["canonical_url"]:x for x in us_rows}
    us_pick=[]
    us_pick += hashed([x for x in us_rows if x["source_route"]=="federalregister_raw_text" and x["fetch_status"]=="downloaded"],"document_id")
    us_pick += hashed([x for x in us_rows if x["source_route"]=="govinfo_html_fallback" and x["fetch_status"]=="downloaded"],"document_id")
    for suffix in ["/1995/09/29/95-24211/", "/1995/11/13/95-24211/", "/1995/06/26/95-14725/"]:
        us_pick.append(next(x for x in us_rows if suffix in x["canonical_url"]))
    assert len({x["document_id"] for x in us_pick})==5
    for x in us_pick:
        fid="US_FR_RAW" if x["source_route"]=="federalregister_raw_text" else "US_GOVINFO_FALLBACK"
        samples.append(sample(fid,"US Federal Register raw text" if fid=="US_FR_RAW" else "US govinfo fallback","government rule publication",x["document_id"],x["date_value"],x["date_precision"],x["agency"],x["canonical_url"],x["final_url"],x["raw_path"],"archival_reproduction","Rule route plus local saved issue text; same document number can identify distinct dated publications.",str(USCSV.relative_to(ROOT))+f"#document_id={x['document_id']};fetch={x['fetch_status']}",x["sha256"]))

    eu_with=[x for x in eu if x["selected_item_uri"]]
    eu_without=[x for x in eu if not x["selected_item_uri"]]
    assert len(eu_with)+len(eu_without)==len(eu)
    for fid,rr,cat,basis in [("EU_ITEM",eu_with,"archival_reproduction","EU Publications Office CELLAR Work→Expression→Manifestation→Item route; selected digital item is a candidate reproduction of an institutional Work, not a body or issuer verification."),("EU_NO_ITEM",eu_without,"unknown","No English digital Item link in this Work ledger; directness/content mapping of absent item cannot be verified.")]:
        ledger.append(frame(fid,"EU CELLAR preparatory Works","government preparatory Work",cat,len(rr),basis,str(EUCSV.relative_to(ROOT))+"#selected_item_uri", "preparatory Work", "Commission preparatory filter; individual Work issuer unchecked",archive="CELLAR selected Item URI" if fid=="EU_ITEM" else ""))
        summary.append(dict(frame_id=fid,source="EU CELLAR preparatory Works",evidence_role="government",count_unit="preparatory Work",denominator=len(rr),rule_derived_directness=cat,rule_derived_count=len(rr),source_text_or_body_status_count=sum(x["disposition"]=="source_text_extracted_relevance_unreviewed" for x in rr),metadata_only_or_unfetched_count=sum(x["disposition"] in ("selected_item_not_requested","no_english_digital_item_link") for x in rr),source_checkpoint="EU disposition export; file mtime in INPUT_MANIFEST.json",frame_filter=f"Works dated {START}..{END}; selected_item_uri {'present' if fid=='EU_ITEM' else 'absent'}"))
    eu_pick=hashed([x for x in eu if x["disposition"]=="source_text_extracted_relevance_unreviewed"],"work_uri",2)
    for status in ["ocr_candidate_layout_review","source_html_table_placeholder_review","no_english_digital_item_link"]:
        eu_pick+=hashed([x for x in eu if x["disposition"]==status],"work_uri")
    assert len(eu_pick)==5
    for x in eu_pick:
        fid="EU_ITEM" if x["selected_item_uri"] else "EU_NO_ITEM"
        samples.append(sample(fid,"EU CELLAR preparatory Works","government preparatory Work",x["work_uri"],x["document_dates"],"as provided; may be multiple", "Commission preparatory filter; individual issuer unchecked",x["work_uri"],x["selected_item_uri"],str((ROOT/"work_packages/M1_source_access/10_eu_cellar_acquisition"/x["raw_path"]).relative_to(ROOT)) if x["raw_path"] else "", "archival_reproduction" if fid=="EU_ITEM" else "unknown",f"CELLAR WEMI link; disposition={x['disposition']}; extraction={x['extraction_status']}",str(EUCSV.relative_to(ROOT))+f"#work_uri={x['work_uri']}",x["selected_item_uri"]))

    au_verified=[x for x in au if x["outcome"] in ("original_pair_verified","browser_original_pair_verified","browser_original_pair_verified_issuer_review")]
    au_unknown=[x for x in au if x not in au_verified]
    assert len(au_verified)==8 and len(au_unknown)==813
    for fid,rr,cat,basis in [("AU_ORIGINAL_PAIR",au_verified,"original_utterance","Landing-to-primary-file pair checked in prior local ledger; issuer may be a predecessor or contractor and date precision varies."),("AU_UNRESOLVED",au_unknown,"unknown","Catalogue landing row does not establish the original publication, issuer, date or primary body; CMS timestamp is not original date.")]:
        ledger.append(frame(fid,"AU DCCEEW catalogue","government-hosted policy candidate",cat,len(rr),basis,str(AUCSV.relative_to(ROOT))+"#outcome", "catalogue landing parent", "DCCEEW host; original issuer case-specific"))
        summary.append(dict(frame_id=fid,source="AU DCCEEW catalogue",evidence_role="government",count_unit="catalogue landing parent",denominator=len(rr),rule_derived_directness=cat,rule_derived_count=len(rr),source_text_or_body_status_count=sum(x["landing_provenance"]=="reused_verified_08" for x in rr),metadata_only_or_unfetched_count=sum(x["landing_provenance"]!="reused_verified_08" for x in rr),source_checkpoint="AU candidate-outcomes export; file mtime in INPUT_MANIFEST.json",frame_filter="821 deduplicated catalogue landing URLs; original dates only where verified"))
    au_terms=["/2015-ncras", "/epbc-act-policy-statement-21-", "/acoustic-tracking-glyphis-", "/standardised-protocols-collection-", "/sustainable-ocean-plan"]
    au_pick=[next(x for x in au if term in x["landing_url"]) for term in au_terms]
    for x in au_pick:
        fid="AU_ORIGINAL_PAIR" if x in au_verified else "AU_UNRESOLVED"
        samples.append(sample(fid,"AU DCCEEW catalogue","government-hosted policy candidate",x["landing_url"],x["verified_original_date"] or x["labelled_date_candidate_unverified"],x["verified_date_precision"] or "unverified",x["verified_original_publisher"] or "unverified",x["web_first_pdf_url"] or "",x["landing_url"],x["landing_raw_path"],"original_utterance" if fid=="AU_ORIGINAL_PAIR" else "unknown",f"Prior outcome={x['outcome']}; landing host alone is insufficient",str(AUCSV.relative_to(ROOT))+f"#landing_url={x['landing_url']}",x["web_first_pdf_url"]))

    ledger.append(frame("GUARDIAN_DEC2015","Guardian December archive","media article","original_utterance",len(guardian),"Original newspaper site articles are direct evidence of Guardian discourse, including quotation/reporting; archive cards/metadata alone do not verify each body.",str(GUARDIAN.relative_to(ROOT)),"distinct article URL","The Guardian",archive="Guardian /environment/YYYY/MM/DD/all cards"))
    december_pilot=[x for x in media if x["original_published_at"].startswith("2015-12")]
    assert len(december_pilot)==1
    summary.append(dict(frame_id="GUARDIAN_DEC2015",source="Guardian December archive",evidence_role="media",count_unit="distinct nonvideo article URL",denominator=len(guardian),rule_derived_directness="original_utterance",rule_derived_count=len(guardian),source_text_or_body_status_count=1,metadata_only_or_unfetched_count=len(guardian)-1,source_checkpoint="Guardian December metadata export plus prior December body pilot; distinct checkpoints",frame_filter="December 2015 /environment/all; nonvideo; distinct URL"))
    media_by_url={x["parent_url"]:x for x in media}
    guardian_picks=[x for x in guardian if x["article_url"]==december_pilot[0]["parent_url"]]+hashed([x for x in guardian if x["article_url"]!=december_pilot[0]["parent_url"]],"article_url",3)
    assert len(guardian_picks)==4
    for g in guardian_picks:
        x=media_by_url.get(g["article_url"])
        samples.append(sample("GUARDIAN_DEC2015","Guardian December archive","media article",g["article_url"],g["original_published_at"],"timestamp", "The Guardian",g["article_url"],f"https://www.theguardian.com/environment/{g['archive_days'][:4]}/{g['archive_days'][5:7]}/{g['archive_days'][8:10]}/all" if g["archive_days"] else "", "", "original_utterance","Original outlet article; archive metadata checks identity/date, body mapping only if prior pilot checked it.",(str(MEDIAPILOT.relative_to(ROOT))+f"#parent_url={g['article_url']}") if x else (str(GUARDIAN.relative_to(ROOT))+f"#article_url={g['article_url']}"),x["response_sha256"] if x else ""))

    ledger.append(frame("PETITION_QUERY","UK Parliament archived petitions","public/civic submission","original_utterance",len(petitions),"Petitioner-authored fields are direct evidence of that submitter's expression in an official archive; embedded government responses must be excluded. Rejected submissions remain submissions but are not published/opened main-frame records.",str(PETITIONS.relative_to(ROOT)),"distinct petition ID","individual petitioner",archive="petition.parliament.uk archived JSON"))
    summary.append(dict(frame_id="PETITION_QUERY",source="UK Parliament archived petitions",evidence_role="public/civic",count_unit="distinct q=climate query petition ID",denominator=len(petitions),rule_derived_directness="original_utterance",rule_derived_count=len(petitions),source_text_or_body_status_count=sum(x["petitioner_body_present"]=="1" for x in petitions),metadata_only_or_unfetched_count=0,source_checkpoint="177-ID mapping export; published=77, rejected=100",frame_filter="official archived q=climate query; 177 distinct IDs; created date within fixed interval"))
    pub_pick=hashed([x for x in public if x["state"]!="rejected"],"petition_id",2)+hashed([x for x in public if x["state"]=="rejected"],"petition_id")
    assert len(pub_pick)==3
    for x in pub_pick:
        samples.append(sample("PETITION_QUERY","UK Parliament archived petitions","public/civic submission",x["petition_id"],x["opened_at"] or x["created_at"],"timestamp; opened or created", "individual petitioner",x["parent_url"],x["source_json_url"],"", "original_utterance","Petitioner-authored action/background/additional details, government response excluded.",str(PUBLICPILOT.relative_to(ROOT))+f"#petition_id={x['petition_id']};state={x['state']}",x["source_page_sha256"]))

    assert len(samples)==30 and len({(s["source"],s["parent_id"]) for s in samples})==30
    ann=json.loads(ANNOT.read_text()) if ANNOT.exists() else {}
    for s in samples:
        key=s["frame_id"]+"|"+s["parent_id"]
        if key in ann:
            for k,v in ann[key].items():
                assert k in FIELDS and k not in ("record_level","frame_id","parent_id","frame_count","count_unit"),k
                s[k]=v
    ledger.extend(samples)
    write_csv(OUT/"source_quality_ledger.csv",ledger,FIELDS)
    write_csv(OUT/"verification_sample.csv",samples,FIELDS)
    by_frame=defaultdict(list)
    for s in samples:by_frame[s["frame_id"]].append(s)
    for q in summary:
        ss=by_frame[q["frame_id"]]
        if "availability_basis" not in q:
            q["availability_basis"]={
                "US_FR_RAW":"object_status fetch_status downloaded or reused_verified_08",
                "US_GOVINFO_FALLBACK":"object_status fetch_status downloaded or reused_verified_08",
                "EU_ITEM":"disposition source_text_extracted_relevance_unreviewed only; OCR/placeholder excluded",
                "EU_NO_ITEM":"no selected English digital Item",
                "AU_ORIGINAL_PAIR":"landing_provenance reused_verified_08 raw checkpoint; other pair checks may be browser only",
                "AU_UNRESOLVED":"landing_provenance reused_verified_08 raw checkpoint",
                "GUARDIAN_DEC2015":"one December current body checked in earlier pilot; 396 metadata pages checked",
                "PETITION_QUERY":"petitioner_body_present in 177-ID mapping; 21 bodies manually reviewed earlier",
            }[q["frame_id"]]
        q["sampled_n"]=len(ss)
        def checked(value):
            return value.startswith("verified") and "pending" not in value
        q["individually_verified_identity_n"]=sum(checked(x["identity_status"]) for x in ss)
        q["individually_verified_date_n"]=sum(checked(x["date_status"]) for x in ss)
        q["individually_verified_mapping_n"]=sum(checked(x["content_mapping_status"]) for x in ss)
        q["sample_pending_or_partial_n"]=sum(any(not checked(x[k]) for k in ("identity_status","date_status","content_mapping_status")) for x in ss)
        q["sample_provenance_conflict_n"]=sum(x["provenance_conflict"] not in ("none observed","none") for x in ss)
        q["unassessed_individual_n"]=q["denominator"]-len(ss)
        assert q["rule_derived_count"]==q["denominator"] and q["unassessed_individual_n"]>=0
    sum_fields=["frame_id","source","evidence_role","count_unit","denominator","rule_derived_directness","rule_derived_count","source_text_or_body_status_count","availability_basis","metadata_only_or_unfetched_count","sampled_n","individually_verified_identity_n","individually_verified_date_n","individually_verified_mapping_n","sample_pending_or_partial_n","sample_provenance_conflict_n","unassessed_individual_n","source_checkpoint","frame_filter"]
    write_csv(OUT/"source_quality_summary.csv",summary,sum_fields)
    sample_paths=sorted({str(x["local_evidence_path"]) for x in samples if x["local_evidence_path"] and (ROOT/x["local_evidence_path"]).is_file()})
    manifest={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"study_publication_interval_inclusive":[START,END],"inputs":[stamp(p) for p in inputs],"sample_local_originals":[stamp(ROOT/p) for p in sample_paths],"review_annotation_path":str(ANNOT.relative_to(ROOT)),"frames":[{"frame_id":x["frame_id"],"unit":x["count_unit"],"denominator":x["denominator"],"filter":x["frame_filter"]} for x in summary],"conventions":["UK document_id is independent parent; attachments and text segments excluded from counts.","US document_id/canonical URL is selected parent; document number alone is not unique; later 125-parent EPA bridge is a separate checkpoint, not added here.","EU work_uri is Work; Expressions/Items/versions do not add Works.","AU catalogue landing URL is candidate parent, not proven original publication; CMS timestamp is not original date.","Guardian article URL and petition ID are separate limited pilot frames, never pooled with government counts.","Rule-derived directness describes route evidence; individually checked fields exist only for 30 sampled parents.","Snapshot/export timestamps do not change publication endpoint or prove historical body version."]}
    (OUT/"INPUT_MANIFEST.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"frame_rows":len(summary),"frame_counts":{x["frame_id"]:x["denominator"] for x in summary},"sample_rows":len(samples),"annotations_applied":sum((s["frame_id"]+"|"+s["parent_id"]) in ann for s in samples)},indent=2))


if __name__=="__main__":main()
