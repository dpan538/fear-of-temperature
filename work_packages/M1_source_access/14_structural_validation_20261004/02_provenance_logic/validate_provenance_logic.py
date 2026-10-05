#!/usr/bin/env python3
"""Read-only, source-aware structural provenance validator.

Run: .venv/bin/python validate_provenance_logic.py --lock-wait-seconds 900
Only this script's directory is written. Full DB reads hold the shared fcntl mutex.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SRC = ROOT / "work_packages/M1_source_access"
UKDB = SRC / "06_government_content_acquisition/fear_temperature_government_content.duckdb"
USDB = SRC / "09_us_au_government_acquisition/fear_temperature_us_au_v1.duckdb"
EUDB = SRC / "10_eu_cellar_acquisition/eu_stage.duckdb"
AUC = SRC / "09_us_au_government_acquisition/reports/au_candidate_outcomes.csv"
GUA = SRC / "11_paris_readiness_pilot_20260927/round2_december_2015/guardian_dec2015_article_metadata.csv"
GUB = SRC / "13_parallel_data_audit_20261004/guardian_body_check_correction.csv"
PET = SRC / "11_paris_readiness_pilot_20260927/round2_december_2015/petition_177_id_date_mapping.csv"
DATE_EX = SRC / "13_parallel_data_audit_20261004/01_fixed_cutoff/date_exceptions.csv"
BRIDGE = SRC / "09_us_au_government_acquisition/reports/targeted_2015_bridge/parent_acceptance.csv"
EU_DISP = SRC / "10_eu_cellar_acquisition/reports/eu_work_dispositions.csv"
LOCK = SRC / "14_structural_validation_20261004/control/heavy_io.lock"
START, END = date(1988,1,1), date(2026,9,21)
UK_NAMES = {
 "src_3c349b00120866c263a3": ("UK_TWFY", "archival_reproduction"),
 "src_549acfda11091ff8c9b8": ("UK_HISTORIC", "archival_reproduction"),
 "src_90b3a872375c9e7fd267": ("UK_QS_API", "original_utterance"),
 "src_9e8f487d372ed011db82": ("UK_HANSARD", "archival_reproduction"),
 "src_ac30b1ae596ab5ab5379": ("UK_DEFRA", "original_utterance"),
 "src_eaf57ccafde8ffd97f7e": ("UK_GOVUK_HIST", "original_utterance"),
}
USID = "us_fr_epa_doe_rules_1994"
AUID = "au_dcceew_current_catalogue_2026_snapshot"
RULES = {
 "DATE_SCOPE": "original publication interval and precision",
 "DATE_ROLE": "publication/date-field semantics",
 "DATE_CROSS": "independent date-field comparison",
 "DATE_CLOCKS": "publication, update and retrieval roles",
 "IDENT": "source parent identity",
 "ISSUER": "issuer/host/directness relationship",
 "CONTENT_LINK": "parent-to-version/content mapping",
 "STATUS": "availability status versus saved content",
 "ATTACHMENT": "parent versus object/attachment boundary",
 "ORIGINAL_ROUTE": "original/archive citation route",
}
FINDING_FIELDS = ["finding_id","frame_id","unit_type","unit_id","source_id","source_version","input_snapshot","rule_id","rule_version","dimension","observed","expected","outcome","severity","evidence_path","evidence_locator","reason","proposed_action","checked_at_utc"]
COVER_FIELDS = ["frame_id","unit_type","source_id","input_snapshot","rule_id","rule_version","eligible","checked","supported","conflict","needs_review","uncheckable","not_applicable","unassessed","coverage_note"]


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fields,extrasaction="ignore");w.writeheader();w.writerows(rows)


def stamp(path):
    st=path.stat()
    return {"path":str(path.relative_to(ROOT)),"modified_utc":datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat(),"bytes":st.st_size}


def iso_day(value):
    if value is None or value=="":return None
    if isinstance(value,datetime):return value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    if isinstance(value,date):return value
    s=str(value)
    try:
        if len(s)>10 and ("+" in s[10:] or s.endswith("Z")):
            return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc).date()
        return date.fromisoformat(s[:10])
    except ValueError:return None


def scope(value, precision=""):
    """Return structural interval status, never substituting retrieval/CMS dates."""
    s=str(value or "").strip();p=(precision or "").lower()
    if not s or p in ("unknown","missing"):return "uncheckable"
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",s[:10]) and (p in ("","day","timestamp") or len(s)>=10):
            d=date.fromisoformat(s[:10]);a=b=d
        elif re.fullmatch(r"\d{4}-\d{2}",s) or p=="month":
            y,m=map(int,s[:7].split("-"));a=date(y,m,1);b=date(y+1,1,1) if m==12 else date(y,m+1,1);b=date.fromordinal(b.toordinal()-1)
        elif re.fullmatch(r"\d{4}",s) or p=="year":
            y=int(s[:4]);a=date(y,1,1);b=date(y,12,31)
        else:return "uncheckable"
    except ValueError:return "conflict"
    if b<START or a>END:return "conflict"
    if a<START or b>END:return "needs_review"
    return "supported"


def date_clock_role(publication, updated=None, retrieved=None, basis=""):
    """A later update/retrieval is evidence of a version, never original wording."""
    if not publication:return "uncheckable"
    if (basis or "").lower().strip() in ("cms_created_at", "retrieved_at", "extracted_at", "cms creation as issue date"):
        return "conflict"
    pub=iso_day(publication)
    if not pub:return "uncheckable"
    for val in (updated,retrieved):
        d=iso_day(val)
        if d and d<pub:return "needs_review"
    return "supported"


def issuer_host_relation(issuer, host, original_pair=False):
    if not issuer:return "uncheckable"
    if host=="DCCEEW" and "CSIRO" in issuer.upper():return "needs_review"
    if host=="DCCEEW" and not original_pair:return "uncheckable"
    return "supported"


def source_directness(role, is_original, is_archive):
    if role in ("media_article","petitioner_text") and is_original:return "original_utterance"
    if is_archive:return "archival_reproduction"
    if is_original:return "original_utterance"
    return "unknown"


def parent_key(frame, canonical, publication, external=""):
    # FR document number is metadata; canonical URL and day remain the parent key.
    return (frame,canonical or "",str(publication or ""))


def fr_number_from_url(url):
    """FR document number is a relation hint, never a unique parent key."""
    match=re.search(r"/documents/\d{4}/\d{2}/\d{2}/([^/?#]+)",str(url or ""))
    return match.group(1) if match else ""


def answer_date_outcome(answered, for_answer, stored):
    if not answered:return "uncheckable"
    if iso_day(answered)==iso_day(stored):return "supported"
    # dateForAnswer may be an earlier deadline and is never silently substituted.
    return "needs_review"


def fetch_all(con, sql, params=None):
    cur=con.execute(sql,params or [])
    cols=[x[0] for x in cur.description]
    rows=[]
    while True:
        chunk=cur.fetchmany(10000)
        if not chunk:break
        rows.extend(dict(zip(cols,row)) for row in chunk)
    return rows


def relation_map(con, source_ids):
    placeholders=",".join("?" for _ in source_ids)
    sql=f"""WITH text_versions AS (SELECT DISTINCT content_version_id FROM text_segments)
    SELECT dco.document_id, count(DISTINCT dco.content_object_id) object_count,
           count(DISTINCT cv.content_version_id) version_count,
           count(DISTINCT CASE WHEN tv.content_version_id IS NOT NULL THEN cv.content_version_id END) text_version_count,
           count(DISTINCT CASE WHEN dco.relationship_type='attachment' THEN dco.content_object_id END) attachment_count,
           min(cv.content_version_id) source_version, min(cv.retrieved_at) first_retrieved
    FROM document_content_objects dco JOIN documents d ON d.document_id=dco.document_id
    LEFT JOIN content_versions cv ON cv.content_object_id=dco.content_object_id
    LEFT JOIN text_versions tv ON tv.content_version_id=cv.content_version_id
    WHERE d.source_id IN ({placeholders}) GROUP BY dco.document_id"""
    return {x["document_id"]:x for x in fetch_all(con,sql,source_ids)}


def acquire_lock(wait_seconds, log):
    # Existing shared inode: never unlink or recreate.
    if not LOCK.is_file():raise RuntimeError(f"Missing shared lock file: {LOCK}")
    fh=LOCK.open("r+")
    start=time.monotonic();last=-100
    while True:
        try:
            fcntl.flock(fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            log.append({"event":"lock_acquired","time_utc":datetime.now(timezone.utc).isoformat(),"wait_seconds":round(time.monotonic()-start,3)})
            print("Acquired heavy-I/O lock",flush=True)
            return fh
        except BlockingIOError:
            elapsed=time.monotonic()-start
            if elapsed-last>=10:
                print(f"Waiting for shared heavy-I/O lock ({elapsed:.0f}s)",flush=True);last=elapsed
            if elapsed>=wait_seconds:
                fh.close();raise TimeoutError("Timed out waiting for shared heavy-I/O lock")
            time.sleep(2)


def load_heavy(wait_seconds, log):
    fh=acquire_lock(wait_seconds,log)
    try:
        uk=duckdb.connect(str(UKDB),read_only=True)
        uk_docs=fetch_all(uk,"select document_id,source_id,external_id,canonical_url,publication_date,publication_timestamp,publication_date_basis,updated_timestamp,collected_at,body_status,content_type,publisher_role from documents")
        uk_rel=relation_map(uk,list(UK_NAMES))
        answer_rows=fetch_all(uk,"""select dv.document_id,
          json_extract_string(rr.raw_payload_json,'$.value.dateAnswered') date_answered,
          json_extract_string(rr.raw_payload_json,'$.value.dateForAnswer') date_for_answer,
          rr.source_artifact_path raw_path
          from document_versions dv join document_version_raw_links l on l.document_version_id=dv.document_version_id
          join raw_records rr on rr.raw_record_id=l.raw_record_id
          join documents d on d.document_id=dv.document_id
          where d.source_id=? and dv.is_current=true""",["src_90b3a872375c9e7fd267"])
        uk.close();print(f"UK: {len(uk_docs)} parents, {len(uk_rel)} link groups, {len(answer_rows)} API answer dates",flush=True)
        ua=duckdb.connect(str(USDB),read_only=True)
        usau_docs=fetch_all(ua,"select document_id,source_id,external_id,canonical_url,publication_date,publication_timestamp,publication_date_basis,updated_timestamp,collected_at,body_status,content_type,publisher_role from documents where source_id in (?,?)",[USID,AUID])
        usau_rel=relation_map(ua,[USID,AUID])
        evid=fetch_all(ua,"select document_id,source_series,date_value,date_precision,original_publisher,cms_created_at,attachment_role_status,source_status from us_au_record_evidence where source_series in (?,?)",[USID,AUID])
        ua.close();print(f"US/AU: {len(usau_docs)} parents/candidates, {len(usau_rel)} link groups",flush=True)
        eu=duckdb.connect(str(EUDB),read_only=True)
        works=fetch_all(eu,"select work_uri,issuer_uri,work_type_uri,language_uri,first_seen_month,boundary_status from eu_works")
        dates=fetch_all(eu,"select work_uri,document_date,source_month,source_page from eu_work_dates")
        items=fetch_all(eu,"select item_uri,work_uri,expression_uri,manifestation_uri,format,alternatives,selection_status from eu_item_candidates")
        versions=fetch_all(eu,"select version_id,item_uri,work_uri,sha256,raw_path,retrieved_at_utc,http_status,mime_type,bytes,extraction_status,text_characters from eu_content_versions")
        eu.close();print(f"EU: {len(works)} Works, {len(dates)} date rows, {len(items)} Item candidates, {len(versions)} saved versions",flush=True)
        return uk_docs,uk_rel,answer_rows,usau_docs,usau_rel,evid,works,dates,items,versions
    finally:
        log.append({"event":"lock_released","time_utc":datetime.now(timezone.utc).isoformat()})
        fcntl.flock(fh.fileno(),fcntl.LOCK_UN);fh.close()
        print("Released heavy-I/O lock",flush=True)


def evaluate(r, canonical_n, external_n):
    """Return named, source-specific metadata outcomes for one parent/Work."""
    kind=r["kind"]; out={}
    def put(rule,status,observed="",expected="",reason="",action="",emit=False,severity="info"):
        assert status in ("supported","conflict","needs_review","uncheckable","not_applicable")
        out[rule]=(status,str(observed or ""),str(expected or ""),reason,action,emit,severity)
    pub=r.get("pub");prec=r.get("precision","")
    scope_status=scope(pub,prec)
    if kind=="AU" and not pub and str(r.get("au_candidate","")).startswith("2026-09"):
        scope_status="needs_review"
        put("DATE_SCOPE",scope_status,r["au_candidate"],"exact issue date no later than 2026-09-21","Unverified September 2026 candidate overlaps fixed cutoff; CMS date is not issue date.","Check one original issue day; retain candidate until resolved.",True,"high")
    else:
        put("DATE_SCOPE",scope_status,pub or "missing",f"{START}..{END}, precision={prec or 'unknown'}", "Original publication date outside scope." if scope_status=="conflict" else "Original date is absent or unsupported at this precision." if scope_status=="uncheckable" else "Date interval crosses the fixed boundary." if scope_status=="needs_review" else "Saved original date interval lies inside fixed scope.","Check original issue/date field; do not substitute acquisition time." if scope_status!="supported" else "",scope_status in ("conflict","needs_review","uncheckable"),"high" if scope_status=="conflict" else "medium")

    if kind=="UK":
        basis=r.get("basis","")
        status="supported" if basis and "cms" not in basis.lower() and "retriev" not in basis.lower() else "conflict" if basis else "uncheckable"
        put("DATE_ROLE",status,basis,"official parliamentary date or GOV.UK first_published_at, not retrieval", "Stored publication basis is source-specific." if status=="supported" else "Publication basis is missing or uses an observation clock.","Inspect original date metadata." if status!="supported" else "",status!="supported")
        if r["frame"] in ("UK_DEFRA","UK_GOVUK_HIST"):
            ex=r.get("date_exception")
            if ex:
                raw=ex.get("raw_source_first_published_at","")
                try:
                    dt=datetime.fromisoformat(raw.replace("Z","+00:00"));local=dt.date();utc=dt.astimezone(timezone.utc).date();stored=iso_day(pub)
                    status="needs_review" if stored==local and local!=utc else "conflict"
                    reason="Stored source-local day differs from UTC day; month-bin convention must be chosen." if status=="needs_review" else "Stored date does not match the evidenced local/UTC publication date."
                    put("DATE_CROSS",status,json.dumps({"source_local":str(local),"utc":str(utc),"stored":str(stored),"raw":raw}),"preserve both local and UTC days",reason,"Choose one analysis-day convention; retain raw timestamp.",True,"medium" if status=="needs_review" else "high")
                except ValueError:
                    put("DATE_CROSS","uncheckable",raw,"offset-aware source timestamp","Source timestamp parse failed.","Inspect raw publication metadata.",True,"medium")
            elif r.get("pub_timestamp"):
                utcday=iso_day(r["pub_timestamp"])
                status="supported" if utcday==iso_day(pub) else "needs_review"
                put("DATE_CROSS",status,json.dumps({"stored":str(pub),"utc":str(utcday)}),"same day unless source offset explains difference","UTC and stored date agree." if status=="supported" else "Timestamp/date mismatch lacks an offset explanation in the prior exception ledger.","Review raw source timestamp." if status!="supported" else "",status!="supported")
            else:put("DATE_CROSS","uncheckable",pub,"independent source timestamp","No independent publication timestamp in this projection.")
        elif r["frame"]=="UK_QS_API":
            a=r.get("answer") or {}
            s=answer_date_outcome(a.get("date_answered"),a.get("date_for_answer"),pub)
            put("DATE_CROSS",s,json.dumps({"stored":str(pub),"dateAnswered":a.get("date_answered"),"dateForAnswer":a.get("date_for_answer")}),"dateAnswered matches stored publication date; dateForAnswer is a separate deadline","Official answer date comparison." if s=="supported" else "Answer date missing or differs; dateForAnswer is not a substitute.","Review saved official API list record." if s!="supported" else "",s=="needs_review")
        else:put("DATE_CROSS","uncheckable",pub,"independent source date","No separately projected original date for this parliamentary route; Task 1 checks archive source boundaries.")
        clocks=date_clock_role(pub,r.get("updated"),r.get("retrieved"),basis)
        if r["frame"] in ("UK_DEFRA","UK_GOVUK_HIST") and r.get("date_exception") and clocks=="needs_review" and r.get("updated"):
            try:
                source_dt=datetime.fromisoformat(r["date_exception"]["raw_source_first_published_at"].replace("Z","+00:00")).astimezone(timezone.utc)
                updated_dt=r["updated"].astimezone(timezone.utc)
                if abs((source_dt-updated_dt).total_seconds())<1:
                    clocks="supported"  # Same instant, two calendar conventions; DATE_CROSS retains the 119 review flags.
            except (ValueError,AttributeError,TypeError):pass
        put("DATE_CLOCKS",clocks,json.dumps({"published":str(pub),"updated":str(r.get("updated") or ""),"first_retrieved":str(r.get("retrieved") or "")}),"distinct publication, modification and retrieval roles","Chronology field roles are retained; later modification does not verify historical wording." if clocks=="supported" else "A clock predates publication or uses an observation date as issue date.","Review field semantics and source timezone." if clocks!="supported" else "",clocks!="supported")
    elif kind in ("US","AU"):
        e=r.get("evidence") or {}
        basis=r.get("basis","")
        if kind=="US":
            status="supported" if e.get("date_precision")=="day" and e.get("date_value") else "uncheckable"
            put("DATE_ROLE",status,json.dumps({"date_value":e.get("date_value"),"precision":e.get("date_precision")}),"Federal Register official publication_date day","Source issue-date role identified." if status=="supported" else "Original issue day missing.","Inspect selected source metadata." if status!="supported" else "",status!="supported")
            status="supported" if str(r.get("pub") or "")==str(e.get("date_value") or "") else "conflict" if r.get("pub") and e.get("date_value") else "uncheckable"
            put("DATE_CROSS",status,json.dumps({"document_date":str(r.get("pub") or ""),"record_evidence_date":e.get("date_value")}),"equal original publication day","Saved document and source evidence dates agree." if status=="supported" else "Independent metadata dates differ or one is missing.","Review official issue header/date." if status!="supported" else "",status!="supported","high" if status=="conflict" else "medium")
        else:
            if any(w in basis.lower() for w in ("cms created as publication","cms_created_at as publication")):
                st="conflict"
            else:st="supported" if pub else "uncheckable"
            put("DATE_ROLE",st,json.dumps({"basis":basis,"original_date":str(pub or ""),"cms_created_at":e.get("cms_created_at")}),"original issue date only; CMS creation separate","AU original-date and CMS roles remain separate." if st=="supported" else "Original date unavailable or CMS may have been substituted.","Check primary publication/date metadata." if st!="supported" else "",st=="conflict")
            ev=str(e.get("date_value") or "")
            if ev and pub:
                st="supported" if str(pub)==ev else "needs_review"
            elif r.get("au_verified") and not pub:st="needs_review"
            else:st="uncheckable"
            put("DATE_CROSS",st,json.dumps({"document_date":str(pub or ""),"original_evidence_date":ev,"outcome_verified_date":r.get("au_verified")}),"same precision and value if independently evidenced","Date mapping agrees." if st=="supported" else "Original issue date cannot be independently reconciled.","Inspect named original file/date." if st!="supported" else "",st=="needs_review")
        clocks=date_clock_role(pub,r.get("updated"),r.get("retrieved"),basis)
        put("DATE_CLOCKS",clocks,json.dumps({"published":str(pub or ""),"retrieved":str(r.get("retrieved") or ""),"cms_created_at":e.get("cms_created_at")}),"observation and issue clocks remain separate","Date clocks remain labelled." if clocks=="supported" else "Issue date missing or an observation clock may be used.","Keep unknown publication date separate from CMS/retrieval." if clocks!="supported" else "",clocks=="needs_review")
    elif kind=="EU":
        dates=r.get("dates",[])
        st="supported" if dates else "uncheckable"
        put("DATE_ROLE",st,json.dumps(dates),"CELLAR Work document_date, not Item retrieval","Work date available." if dates else "No Work document_date was staged.","Check Work metadata." if not dates else "",not dates)
        months={str(x.get("document_date") or "")[:7] for x in dates if x.get("document_date")}
        wrong=[x for x in dates if x.get("source_month") and x.get("document_date") and x["source_month"]!=x["document_date"][:7]]
        st="needs_review" if wrong or len(months)>1 else "supported" if dates else "uncheckable"
        put("DATE_CROSS",st,json.dumps({"dates":[x.get("document_date") for x in dates],"first_seen_month":r.get("first_seen_month"),"source_months":[x.get("source_month") for x in dates]}),"Work date agrees with its source month; multiple dates retain separate evidence","Multiple Work dates/month mappings require review, not automatic error." if st=="needs_review" else "Work date/month relation is recorded.","Review CELLAR Work date observations only." if st=="needs_review" else "",st=="needs_review")
        put("DATE_CLOCKS","supported" if dates else "uncheckable",json.dumps({"work_date":str(pub or ""),"saved_item_retrieval":r.get("retrieved")}),"Item retrieval does not replace Work issue date","Source and Item clocks kept separate." if dates else "No Work issue date to compare.")
    elif kind=="GUARDIAN":
        st="supported" if r.get("pub") and r.get("canonical")==r.get("id") else "needs_review"
        put("DATE_ROLE",st,json.dumps({"original_published":str(pub),"modified":r.get("updated")}),"article original publication time distinct from modification","Original and modification fields are separate." if st=="supported" else "Canonical or original publication time missing.","Check archived article metadata." if st!="supported" else "",st!="supported")
        st="supported" if str(pub or "")[:7]==r.get("published_month") else "needs_review"
        put("DATE_CROSS",st,json.dumps({"published":str(pub),"published_utc_month":r.get("published_month")}),"same UTC month","Article date and frame month agree." if st=="supported" else "Article month/frame mismatch.","Check UTC/local article date convention." if st!="supported" else "",st!="supported")
        st=date_clock_role(pub,r.get("updated"),None,"original_published_at")
        put("DATE_CLOCKS",st,json.dumps({"published":str(pub),"modified":r.get("updated")}),"modification is version clock","Later modification is permitted and does not prove original wording." if st=="supported" else "Modified time precedes original publication.","Review page metadata." if st!="supported" else "",st!="supported")
    else: # petition
        created=r.get("created");opened=r.get("opened");state=r.get("state")
        st="supported" if created and ((state=="rejected" and not opened) or (state!="rejected" and opened)) else "needs_review"
        put("DATE_ROLE",st,json.dumps({"created":created,"opened":opened,"state":state}),"published/opened uses opened_at; rejected submission uses created_at","Petition lifecycle fields are distinct." if st=="supported" else "Lifecycle/date fields need review.","Check saved petition JSON status and dates." if st!="supported" else "",st!="supported")
        st="supported" if created and (not opened or str(created)<=str(opened)) else "needs_review"
        put("DATE_CROSS",st,json.dumps({"created":created,"opened":opened}),"opened_at is not before created_at","Submission/opening order is consistent." if st=="supported" else "Opening precedes submission or submission time missing.","Review petition JSON." if st!="supported" else "",st!="supported")
        put("DATE_CLOCKS","supported" if created else "uncheckable",json.dumps({"created":created,"opened":opened,"rejected":r.get("rejected")}),"created, opened and rejected are separate lifecycle clocks","Lifecycle clocks remain separate." if created else "No creation clock.")

    key=(r["frame"],r.get("canonical") or "")
    if not r.get("id") or not r.get("canonical"):
        st="uncheckable"
    elif canonical_n[key]>1:
        st="needs_review"
    elif kind=="US" and r.get("fr_number") and external_n[(r["frame"],r["fr_number"])]>1:
        st="needs_review"
    else:st="supported"
    put("IDENT",st,json.dumps({"parent_id":r.get("id"),"canonical":r.get("canonical"),"external_id":r.get("external"),"fr_document_number":r.get("fr_number"),"canonical_occurrences":canonical_n[key],"fr_number_occurrences":external_n[(r["frame"],str(r.get("fr_number") or ""))] if kind=="US" else None}),"unique canonical parent within source; FR number alone not key","Canonical or FR document-number relationship requires review, but no automatic merge." if st=="needs_review" else "Stable source-specific identity recorded." if st=="supported" else "Stable ID/route missing.","Compare dated originals; retain distinct URL/date parents." if st!="supported" else "",st!="supported")

    if kind=="UK":st="supported";issuer=r.get("source_id");msg="Named official/archive/mirror route; speaker attribution is a separate field."
    elif kind=="US":st="supported" if (r.get("evidence") or {}).get("original_publisher") else "uncheckable";issuer=(r.get("evidence") or {}).get("original_publisher");msg="EPA/DOE agency associations may both refer to one parent."
    elif kind=="AU":
        issuer=r.get("au_publisher") or (r.get("evidence") or {}).get("original_publisher")
        st=issuer_host_relation(issuer,"DCCEEW",bool(r.get("au_verified")))
        msg="Current DCCEEW host may differ from original report issuer; keep both."
    elif kind=="EU":
        issuer=r.get("issuer");st="supported" if issuer=="http://publications.europa.eu/resource/authority/corporate-body/COM" else "uncheckable" if not issuer else "needs_review";msg="Commission issuer URI is a source filter, not claim truth."
    else:st="supported";issuer="The Guardian" if kind=="GUARDIAN" else "petitioner";msg="Direct evidence of article/petitioner expression, including reporting/citation."
    put("ISSUER",st,json.dumps({"issuer":issuer,"host":r.get("host"),"route_class":r.get("directness")}),"issuer/host/evidence role remain distinct",msg,"Review original title page/commissioning role." if st=="needs_review" else "",st in ("needs_review","uncheckable") and kind=="AU")

    rel=r.get("rel") or {};obj=int(rel.get("object_count") or 0);ver=int(rel.get("version_count") or 0);textv=int(rel.get("text_version_count") or 0)
    if kind in ("UK","US","AU"):
        st="supported" if obj and ver else "needs_review" if r.get("body_status")=="downloaded_and_extracted" else "uncheckable"
        put("CONTENT_LINK",st,json.dumps({"objects":obj,"versions":ver,"text_versions":textv}),"parent→object→saved version, not parent→every shared segment","Link chain present; individual reply span is a separate Task 1 check." if st=="supported" else "Saved parent has no complete object/version chain at this checkpoint.","Inspect named parent/object link only for a specified evidence need." if st!="supported" else "",st in ("needs_review","uncheckable"))
        body=r.get("body_status") or ""
        success_labels={"downloaded_and_extracted","source_extracted_and_cleaned"}
        if textv and body in success_labels:st="supported"
        elif textv and body not in success_labels:st="needs_review"
        elif not textv and body in success_labels:st="needs_review"
        else:st="uncheckable"
        put("STATUS",st,json.dumps({"body_status":body,"text_linked_versions":textv}),"availability label matches saved text-link evidence","Status needs interpretation against linked saved text." if st=="needs_review" else "Availability evidence consistent at this checkpoint." if st=="supported" else "Body not available or not requested at this checkpoint.","Reconcile status semantics for this parent without discarding saved bytes." if st=="needs_review" else "",st=="needs_review")
        st="supported" if obj else "uncheckable"
        put("ATTACHMENT",st,json.dumps({"object_count":obj,"attachment_links":int(rel.get("attachment_count") or 0)}),"object/attachment counted beneath parent, not as extra parent","A multi-object parent or shared object is allowed." if st=="supported" else "No parent-object relationship observed.","Resolve primary file boundary for named AU candidate." if st=="uncheckable" and kind=="AU" else "",st=="uncheckable" and kind=="AU")
    elif kind=="EU":
        items=r.get("items") or [];vers=r.get("versions") or []
        disposition=r.get("disposition") or ""
        if disposition in ("ocr_candidate_layout_review","source_html_table_placeholder_review","selected_item_failed"):
            st="needs_review"
        elif not items:st="uncheckable"
        elif not vers:st="uncheckable"
        elif any(int(v.get("text_characters") or 0)>0 for v in vers):st="supported"
        else:st="needs_review"
        put("CONTENT_LINK",st,json.dumps({"item_candidates":len(items),"saved_versions":len(vers),"max_text_characters":max([int(v.get("text_characters") or 0) for v in vers] or [0]),"disposition":disposition}),"Work→English Item→saved version; OCR/placeholder not validated full body","Item/Work route saved." if st=="supported" else "No selected/saved readable Item or known extraction exception at this checkpoint.","Inspect named Work/Item alternative only if research need exists." if st!="supported" else "",st in ("needs_review","uncheckable"))
        st="needs_review" if disposition in ("ocr_candidate_layout_review","source_html_table_placeholder_review","selected_item_failed") else "supported" if vers and any(int(v.get("text_characters") or 0)>0 for v in vers) else "needs_review" if vers else "uncheckable"
        put("STATUS",st,json.dumps({"saved_versions":len(vers),"extraction_statuses":sorted({str(v.get("extraction_status") or "") for v in vers})}),"saved Item status aligns with recorded text characters","Version extraction metadata recorded." if st=="supported" else "Saved Item has no validated text evidence or was not requested.","Review OCR/placeholder Item only as needed." if st=="needs_review" else "",st=="needs_review")
        put("ATTACHMENT","supported" if items else "uncheckable",len(items),"Items/alternatives remain under one Work","Item alternatives do not multiply Works.","Check English Item route only for named Work." if not items else "",not items)
    elif kind=="GUARDIAN":
        st="supported" if r.get("body_checked") else "uncheckable"
        put("CONTENT_LINK",st,"body_checked" if r.get("body_checked") else "metadata_only","current article body linked to canonical URL","Current body was checked in prior bounded pilot." if st=="supported" else "Article body outside documented check set.","Check named article body only if required.",st=="uncheckable")
        put("STATUS",st,"body_checked" if r.get("body_checked") else "body_unchecked","separate candidate URL from checked current body","Body-check status is explicit.","",False)
        put("ATTACHMENT","not_applicable","","article URL parent","No attachment-work rule in this pilot.")
    else:
        st="supported" if str(r.get("body_present"))=="1" else "uncheckable"
        put("CONTENT_LINK",st,r.get("body_present"),"petitioner-authored body present; government response separate","Petitioner text presence recorded." if st=="supported" else "Petitioner body absent or unknown.","Check saved JSON authorial fields." if st!="supported" else "",st!="supported")
        put("STATUS",st,r.get("state"),"submitted status kept separate from published/opened status","Published and rejected submissions are separate frame states.")
        put("ATTACHMENT","not_applicable","","petition ID parent","No attachment-work rule in this pilot.")

    if kind=="AU":
        route=bool(r.get("au_verified"));st="supported" if route else "uncheckable"
    elif kind=="EU":route=bool(r.get("items"));st="supported" if route else "uncheckable"
    else:route=bool(r.get("canonical"));st="supported" if route else "uncheckable"
    put("ORIGINAL_ROUTE",st,json.dumps({"url":r.get("canonical"),"archive_or_item_route":r.get("archive_route")}),"traceable source or archive route; not a historical body/truth verdict","Archive/original route recorded." if st=="supported" else "Original alignment/access route remains unresolved.","Align one mirror or original route if analysis needs it." if st=="needs_review" else "",st=="needs_review" or (st=="uncheckable" and kind in ("AU","EU")))
    assert set(out)==set(RULES)
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lock-wait-seconds",type=int,default=900)
    args=ap.parse_args()
    runlog=[{"event":"run_started","time_utc":datetime.now(timezone.utc).isoformat()}]
    inputs=[UKDB,USDB,EUDB,AUC,GUA,GUB,PET,DATE_EX,BRIDGE,EU_DISP,
            SRC/"09_us_au_government_acquisition/FILTER_CONTRACT.md",
            SRC/"10_eu_cellar_acquisition/FILTER_CONTRACT.md",
            SRC/"13_parallel_data_audit_20261004/COORDINATOR_CORRECTIONS.md"]
    sources={str(p.relative_to(ROOT)):stamp(p) for p in inputs}
    try:
        au_by_url={x["landing_url"]:x for x in read_csv(AUC)}
        guardian=read_csv(GUA);guardian_checked={x["article_url"] for x in read_csv(GUB)}
        petitions=read_csv(PET)
        date_ex={x["document_id"]:x for x in read_csv(DATE_EX) if x["exception_type"]=="source_calendar_day_vs_utc_day"}
        bridge=[x for x in read_csv(BRIDGE) if x.get("verified_original")=="True" or x.get("verified_original")=="1"]
        eu_disp={x["work_uri"]:x for x in read_csv(EU_DISP)}
        loaded=load_heavy(args.lock_wait_seconds,runlog)
        uk_docs,uk_rel,answer_rows,ua_docs,ua_rel,evidence,eu_works,eu_dates,eu_items,eu_versions=loaded
        ans_by_doc={x["document_id"]:x for x in answer_rows}
        ev_by_doc={x["document_id"]:x for x in evidence}
        dates_by_work=defaultdict(list);items_by_work=defaultdict(list);vers_by_work=defaultdict(list)
        for x in eu_dates:dates_by_work[x["work_uri"]].append(x)
        for x in eu_items:items_by_work[x["work_uri"]].append(x)
        for x in eu_versions:vers_by_work[x["work_uri"]].append(x)
        records=[]
        for d in uk_docs:
            if d["source_id"] not in UK_NAMES:continue
            frame,direct=UK_NAMES[d["source_id"]];rel=uk_rel.get(d["document_id"],{})
            evidence_path=str(UKDB.relative_to(ROOT))
            if d["document_id"] in date_ex:evidence_path+=" | "+str(DATE_EX.relative_to(ROOT))
            records.append(dict(kind="UK",frame=frame,unit_type="independent_document_parent",id=d["document_id"],source_id=d["source_id"],external=d["external_id"],canonical=d["canonical_url"],pub=d["publication_date"],precision="day",basis=d["publication_date_basis"],pub_timestamp=d["publication_timestamp"],updated=d["updated_timestamp"],retrieved=rel.get("first_retrieved"),body_status=d["body_status"],rel=rel,answer=ans_by_doc.get(d["document_id"]),date_exception=date_ex.get(d["document_id"]),directness=direct,host="UK Parliament or GOV.UK",evidence_path=evidence_path,locator="documents.document_id="+d["document_id"],source_version=rel.get("source_version") or ""))
        for d in ua_docs:
            if d["source_id"] not in (USID,AUID):continue
            kind="US" if d["source_id"]==USID else "AU";frame="US_FR" if kind=="US" else "AU_CATALOGUE"
            e=ev_by_doc.get(d["document_id"],{});rel=ua_rel.get(d["document_id"],{})
            a=au_by_url.get(d["canonical_url"],{}) if kind=="AU" else {}
            verified=a.get("verified_original_date") if a.get("outcome") in ("original_pair_verified","browser_original_pair_verified","browser_original_pair_verified_issuer_review") else ""
            pub=e.get("date_value") if kind=="US" else verified or e.get("date_value") or ""
            prec=e.get("date_precision") if kind=="US" else a.get("verified_date_precision") or e.get("date_precision") or "unknown"
            if kind=="AU" and not verified and not e.get("date_value"):pub=""
            evidence_path=str(USDB.relative_to(ROOT))+(" | "+str(AUC.relative_to(ROOT)) if kind=="AU" else "")
            records.append(dict(kind=kind,frame=frame,unit_type="selected_document_parent" if kind=="US" else "catalogue_landing_candidate",id=d["document_id"],source_id=d["source_id"],external=d["external_id"],fr_number=fr_number_from_url(d["canonical_url"]) if kind=="US" else "",canonical=d["canonical_url"],pub=pub,precision=prec,basis=d["publication_date_basis"],pub_timestamp=d["publication_timestamp"],updated=d["updated_timestamp"],retrieved=rel.get("first_retrieved"),body_status=d["body_status"],rel=rel,evidence=e,au_verified=verified,au_candidate=a.get("labelled_date_candidate_unverified") or "",au_publisher=a.get("verified_original_publisher") or "",directness="archival_reproduction" if kind=="US" else "original_utterance" if verified else "unknown",host="Federal Register" if kind=="US" else "DCCEEW",evidence_path=evidence_path,locator="documents.document_id="+d["document_id"],source_version=rel.get("source_version") or ""))
        for w in eu_works:
            dates=dates_by_work[w["work_uri"]];first=dates[0]["document_date"] if dates else ""
            disposition_row=eu_disp.get(w["work_uri"],{})
            items=list(items_by_work[w["work_uri"]]);vers=vers_by_work[w["work_uri"]]
            # Candidate Item links in the earlier complete Work ledger remain valid
            # metadata even when this later staging DB has not requested that Item.
            selected=disposition_row.get("selected_item_uri") or ""
            if selected and selected not in {x["item_uri"] for x in items}:
                items.append({"item_uri":selected,"selection_status":"candidate_link_from_disposition_export"})
            records.append(dict(kind="EU",frame="EU_CELLAR",unit_type="preparatory_Work",id=w["work_uri"],source_id="eu_cellar_com_preparatory_en_v1",external="",canonical=w["work_uri"],pub=first,precision="day" if len(first)==10 else "unknown",basis="cdm:work_date_document",issuer=w["issuer_uri"],first_seen_month=w["first_seen_month"],dates=dates,items=items,versions=vers,disposition=disposition_row.get("disposition",""),retrieved=min((x["retrieved_at_utc"] for x in vers if x.get("retrieved_at_utc")),default=""),directness="archival_reproduction" if items else "unknown",host="CELLAR",archive_route=selected or (items[0]["item_uri"] if items else ""),evidence_path=str(EUDB.relative_to(ROOT))+" | "+str(EU_DISP.relative_to(ROOT)),locator="eu_works.work_uri="+w["work_uri"],source_version=vers[0]["version_id"] if vers else ""))
        for x in guardian:
            records.append(dict(kind="GUARDIAN",frame="GUARDIAN_DEC2015",unit_type="distinct_article_URL",id=x["article_url"],source_id="guardian_environment_archive_dec2015",canonical=x["canonical_url"],external="",pub=x["original_published_at"],precision="timestamp",updated=x["current_modified_at"],published_month=x["published_utc_month"],body_checked=x["article_url"] in guardian_checked,directness="original_utterance",host="The Guardian",archive_route=x["archive_days"],evidence_path=str(GUA.relative_to(ROOT))+" | "+str(GUB.relative_to(ROOT)),locator="article_url="+x["article_url"],source_version=x["current_modified_at"] or ""))
        for x in petitions:
            pub=x["created_at"] if x["state"]=="rejected" else x["opened_at"]
            records.append(dict(kind="PETITION",frame="PETITION_QUERY",unit_type="distinct_petition_ID",id=x["petition_id"],source_id="uk_parliament_archived_petition_q_climate",canonical=x["parent_url"],external="",pub=pub,precision="timestamp",created=x["created_at"],opened=x["opened_at"],rejected=x["rejected_at"],state=x["state"],body_present=x["petitioner_body_present"],body_checked=x["pilot_reviewed"]=="1",directness="original_utterance",host="UK Parliament petition archive",archive_route=x["source_json_url"],evidence_path=str(PET.relative_to(ROOT)),locator="petition_id="+x["petition_id"],source_version=""))
        byframe=Counter(x["frame"] for x in records)
        assert sum(byframe[f] for f in {v[0] for v in UK_NAMES.values()})==248035
        assert byframe["US_FR"]==33544 and byframe["AU_CATALOGUE"]==821
        assert byframe["EU_CELLAR"]==50578 and byframe["GUARDIAN_DEC2015"]==396 and byframe["PETITION_QUERY"]==177
        can_n=Counter((x["frame"],x.get("canonical") or "") for x in records if x.get("canonical"))
        ext_n=Counter((x["frame"],str(x.get("fr_number") or "")) for x in records if x["kind"]=="US" and x.get("fr_number"))
        frames=sorted(byframe)
        snapshots={f: sources[str((UKDB if f.startswith("UK_") else USDB if f in ("US_FR","AU_CATALOGUE") else EUDB if f=="EU_CELLAR" else GUA if f=="GUARDIAN_DEC2015" else PET).relative_to(ROOT))]["modified_utc"] for f in frames}
        snapshots["EU_CELLAR"] += "|disposition="+sources[str(EU_DISP.relative_to(ROOT))]["modified_utc"]
        for frame in ("UK_DEFRA","UK_GOVUK_HIST"):
            snapshots[frame] += "|date_exceptions="+sources[str(DATE_EX.relative_to(ROOT))]["modified_utc"]
        snapshots["AU_CATALOGUE"] += "|candidate_outcomes="+sources[str(AUC.relative_to(ROOT))]["modified_utc"]
        snapshots["GUARDIAN_DEC2015"] += "|body_check_correction="+sources[str(GUB.relative_to(ROOT))]["modified_utc"]
        checked_at=datetime.now(timezone.utc).isoformat()
        cover=defaultdict(Counter);findings=[]
        for i,r in enumerate(records,1):
            rr=evaluate(r,can_n,ext_n)
            for rule,val in rr.items():
                status,observed,expected,reason,action,emit,severity=val
                cover[(r["frame"],rule)][status]+=1
                if emit and status in ("conflict","needs_review","uncheckable"):
                    key="|".join([r["frame"],r["id"],rule,"1",snapshots[r["frame"]]])
                    findings.append(dict(finding_id=hashlib.sha256(key.encode()).hexdigest(),frame_id=r["frame"],unit_type=r["unit_type"],unit_id=r["id"],source_id=r["source_id"],source_version=r.get("source_version") or "",input_snapshot=snapshots[r["frame"]],rule_id=rule,rule_version="1",dimension=RULES[rule],observed=observed,expected=expected,outcome=status,severity=severity,evidence_path=r["evidence_path"],evidence_locator=r["locator"],reason=reason,proposed_action=action,checked_at_utc=checked_at))
            if i%100000==0:print(f"Evaluated {i:,} source units",flush=True)
        coverage=[]
        for frame in frames:
            for rule in RULES:
                c=cover[(frame,rule)];n=byframe[frame];total=sum(c.values());assert total==n,(frame,rule,total,n)
                coverage.append(dict(frame_id=frame,unit_type=next(x["unit_type"] for x in records if x["frame"]==frame),source_id=next(x["source_id"] for x in records if x["frame"]==frame),input_snapshot=snapshots[frame],rule_id=rule,rule_version="1",eligible=n,checked=c["supported"]+c["conflict"]+c["needs_review"],supported=c["supported"],conflict=c["conflict"],needs_review=c["needs_review"],uncheckable=c["uncheckable"],not_applicable=c["not_applicable"],unassessed=0,coverage_note="Metadata/relational structural rule; supported never means substantive claim truth or historical body-version fidelity."))
        findings.sort(key=lambda x:(x["frame_id"],x["unit_id"],x["rule_id"]))
        assert len({x["finding_id"] for x in findings})==len(findings)
        write_csv(OUT/"execution_coverage.csv",coverage,COVER_FIELDS)
        write_csv(OUT/"findings.csv",findings,FINDING_FIELDS)
        reviewed={"US_FR":len({x["document_id"] for x in bridge}),"AU_CATALOGUE":sum(x.get("outcome") in ("original_pair_verified","browser_original_pair_verified","browser_original_pair_verified_issuer_review") for x in au_by_url.values()),"GUARDIAN_DEC2015":len(guardian_checked),"PETITION_QUERY":sum(x["pilot_reviewed"]=="1" for x in petitions)}
        prior_sample=read_csv(SRC/"13_parallel_data_audit_20261004/03_source_quality/verification_sample.csv")
        for x in prior_sample:
            if x["frame_id"].startswith("UK_"):
                name=x["frame_id"].replace("UK_HANSARD_ARCHIVE","UK_HANSARD").replace("UK_TWFY_MIRROR","UK_TWFY").replace("UK_GOVUK_DEFRA","UK_DEFRA")
                reviewed[name]=reviewed.get(name,0)+1
        summary=[]
        for frame in frames:
            n=byframe[frame];d=next(x for x in records if x["frame"]==frame)
            direct=Counter(x["directness"] for x in records if x["frame"]==frame)
            q={(x["rule_id"]):x for x in coverage if x["frame_id"]==frame}
            k=reviewed.get(frame,0)
            summary.append(dict(frame_id=frame,unit_type=d["unit_type"],source_id=d["source_id"],input_snapshot=snapshots[frame],denominator=n,original_utterance_route_n=direct["original_utterance"],archival_reproduction_route_n=direct["archival_reproduction"],indirect_secondary_route_n=direct["indirect_secondary"],mixed_route_n=direct["mixed"],unknown_route_n=direct["unknown"],date_supported_n=q["DATE_SCOPE"]["supported"],date_conflict_n=q["DATE_SCOPE"]["conflict"],date_needs_review_n=q["DATE_SCOPE"]["needs_review"],date_uncheckable_n=q["DATE_SCOPE"]["uncheckable"],content_link_supported_n=q["CONTENT_LINK"]["supported"],content_link_uncheckable_n=q["CONTENT_LINK"]["uncheckable"],documented_bounded_parent_review_n=k,individually_unassessed_n=n-k,review_basis="previous purposive UK sample" if frame.startswith("UK_") else "125-parent EPA bridge" if frame=="US_FR" else "AU local/browser original pairs" if frame=="AU_CATALOGUE" else "two Guardian pilots" if frame=="GUARDIAN_DEC2015" else "prior petition manual pilot" if frame=="PETITION_QUERY" else "no corpus-wide individual original-body verification",substantive_claim_truth="unassessed"))
        sum_fields=list(summary[0]);write_csv(OUT/"source_quality_summary.csv",summary,sum_fields)
        inventory=[dict(frame_id=x["frame_id"],unit_type=x["unit_type"],registered_saved_count=x["denominator"],validation_state="checked_saved_metadata",source_id=x["source_id"],note="See execution_coverage.csv for applicable rule denominators") for x in summary]
        inventory += [dict(frame_id=f,unit_type="not_enumerated",registered_saved_count="unknown",validation_state="candidate_route_only",source_id=f,note="Known reconnaissance route; no independent stored parent frame to validate or count as zero") for f in ["US_pre_1994_print","AU_predecessor_archive","IE_Oireachtas_questions","NZ_publications","EU_Parliament_question_sample"]]
        write_csv(OUT/"frame_inventory.csv",inventory,["frame_id","unit_type","registered_saved_count","validation_state","source_id","note"])
        manifest={"generated_at_utc":checked_at,"publication_interval_inclusive":[str(START),str(END)],"inputs":list(sources.values())+[stamp(SRC/"13_parallel_data_audit_20261004/03_source_quality/verification_sample.csv")],"source_checkpoints":snapshots,"frame_units":{x["frame_id"]:x["unit_type"] for x in summary},"id_conventions":["UK 06 database is the only UK parent frame; copied UK rows in 09 are excluded.","US canonical URL plus publication day is identity; FR number can repeat.","EU Work URI is parent, Item/version separate.","AU landing URL is candidate, not verified Work.","Guardian article URL and petition ID are limited pilot frames."],"filter":"UK saved parents; US EPA/DOE RULE/PRORULE 1994–cutoff; EU COM act_preparatory ENG Work date; AU 821 current catalogue candidates; December 2015 Guardian nonvideo archive; archived q=climate petition IDs. No semantic filter."}
        (OUT/"INPUT_MANIFEST.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
        counts=Counter((x["rule_id"],x["outcome"]) for x in findings)
        result={"status":"complete_with_named_unresolved_records","publication_interval_inclusive":[str(START),str(END)],"checked_at_utc":checked_at,"saved_frames":{x["frame_id"]:x["denominator"] for x in summary},"coverage_rows":len(coverage),"finding_rows":len(findings),"finding_outcomes":dict(Counter(x["outcome"] for x in findings)),"source_quality_summary_path":str((OUT/"source_quality_summary.csv").relative_to(ROOT)),"input_manifest_path":str((OUT/"INPUT_MANIFEST.json").relative_to(ROOT)),"no_formal_database_changes":True,"limits":["Structural metadata support is not original-body or substantive-claim truth verification.","Shared archive reply-span validation belongs to Task 1.","Current saved bodies do not prove historical wording.","Unenumerated source routes have unknown denominators, not zero records."],"proposed_minimal_next_actions":["Choose and log GOV.UK local/UTC analysis-day convention before refreshing three affected monthly bins.","Reconcile UK parent body-status semantics against linked saved text.","Resolve named AU original date, issuer and primary-file boundaries; retain unknown-date candidates.","Use Task 1 archive split findings before any parent repair.","Only after coordinator review, specify evidence-based new source frames if source/genre/period concentration warrants them."]}
        (OUT/"RESULT.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
        runlog.append({"event":"run_finished","time_utc":datetime.now(timezone.utc).isoformat(),"frame_unit_counts":dict(byframe),"coverage_rows":len(coverage),"finding_rows":len(findings)})
        print(json.dumps({"coverage_rows":len(coverage),"findings":len(findings),"incompatible_frame_units":dict(byframe)},indent=2),flush=True)
    finally:
        (OUT/"RUN_LOG.json").write_text(json.dumps(runlog,indent=2)+"\n")


if __name__=="__main__":main()
