"""Read-only, fixed-cutoff distribution audit of committed source snapshots.

Run from the repository root with: .venv/bin/python <this file>
Only this script's own directory is written. Databases are opened read-only.
"""
from __future__ import annotations

import calendar
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / "work_packages/M1_source_access"
DB = {
    "UK": SOURCE / "06_government_content_acquisition/fear_temperature_government_content.duckdb",
    "US_AU": SOURCE / "09_us_au_government_acquisition/fear_temperature_us_au_v1.duckdb",
    "EU": SOURCE / "10_eu_cellar_acquisition/eu_stage.duckdb",
    "AU_original": SOURCE / "09_us_au_government_acquisition/au_browser_stage.duckdb",
}
START, END = "1988-01-01", "2026-09-21"
MONTHS = pd.period_range("1988-01", "2026-09", freq="M").astype(str).tolist()
US = "us_fr_epa_doe_rules_1994"
AU = "au_dcceew_current_catalogue_2026_snapshot"
SOURCE_SHORT = {
    "src_549acfda11091ff8c9b8": "UK Historic Hansard",
    "src_9e8f487d372ed011db82": "UK Hansard archive",
    "src_3c349b00120866c263a3": "UK ParlParse mirror",
    "src_90b3a872375c9e7fd267": "UK Questions API",
    "src_ac30b1ae596ab5ab5379": "UK DEFRA papers",
    "src_eaf57ccafde8ffd97f7e": "UK historic policy",
    US: "US EPA/DOE Register",
    AU: "AU current catalogue",
    "AU_VERIFIED_ORIGINAL": "AU verified originals",
    "EU_CELLAR_COM": "EU CELLAR COM",
}


def query(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> pd.DataFrame:
    return con.execute(sql, params or []).df()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def month_rows(con: duckdb.DuckDBPyConnection, source_filter: str) -> pd.DataFrame:
    return query(con, f"""
        SELECT d.source_id, d.content_type AS genre,
               CASE WHEN d.publication_date IS NULL THEN 'UNKNOWN'
                    WHEN d.publication_date < DATE '{START}' THEN 'BEFORE'
                    WHEN d.publication_date > DATE '{END}' THEN 'AFTER'
                    ELSE strftime(d.publication_date, '%Y-%m') END AS month,
               count(*) AS parent_count,
               count(*) FILTER (WHERE d.body_status IN
                 ('downloaded_and_extracted','source_extracted_and_cleaned')) AS readable_parent_count,
               count(DISTINCT d.document_id) AS distinct_parent_ids,
               count(DISTINCT d.external_id) AS distinct_external_ids,
               count(DISTINCT d.canonical_url) AS distinct_canonical_urls
        FROM documents d WHERE {source_filter}
        GROUP BY 1,2,3 ORDER BY 1,2,3
    """)


def source_diagnostics(con: duckdb.DuckDBPyConnection, source_filter: str) -> pd.DataFrame:
    return query(con, f"""
        WITH base AS (SELECT * FROM documents WHERE {source_filter}),
        parent AS (
          SELECT source_id, content_type AS genre, count(*) AS parents,
                 count(DISTINCT document_id) AS distinct_parent_ids,
                 count(DISTINCT external_id) AS distinct_external_ids,
                 count(DISTINCT canonical_url) AS distinct_canonical_urls,
                 count(*) FILTER (WHERE publication_date IS NULL) AS unknown_dates,
                 count(*) FILTER (WHERE publication_date < DATE '{START}' OR publication_date > DATE '{END}') AS out_dates,
                 count(*) FILTER (WHERE parent_document_id IS NOT NULL) AS child_document_rows,
                 count(*) FILTER (WHERE body_status IN ('downloaded_and_extracted','source_extracted_and_cleaned')) AS readable_parents
          FROM base GROUP BY 1,2),
        linked AS (
          SELECT d.source_id, d.content_type AS genre,
                 count(*) AS parent_object_links,
                 count(DISTINCT x.content_object_id) AS distinct_objects,
                 count(DISTINCT v.content_version_id) AS distinct_versions,
                 count(DISTINCT d.document_id) FILTER(WHERE v.content_version_id IS NOT NULL) AS parents_with_version,
                 count(*) FILTER(WHERE x.relationship_type='attachment') AS attachment_links,
                 count(*) FILTER(WHERE x.relationship_type='landing_page') AS landing_links
          FROM base d LEFT JOIN document_content_objects x USING(document_id)
          LEFT JOIN content_versions v USING(content_object_id)
          GROUP BY 1,2)
        SELECT p.*, l.parent_object_links,l.distinct_objects,l.distinct_versions,l.parents_with_version,
               l.attachment_links,l.landing_links FROM parent p JOIN linked l USING(source_id,genre)
        ORDER BY p.source_id,p.genre
    """)


def normalized_versions(con: duckdb.DuckDBPyConnection, source_filter: str) -> pd.DataFrame:
    return query(con,f"""SELECT d.source_id,d.content_type AS genre,count(v.document_version_id) AS normalized_parent_versions,
       count(DISTINCT v.document_id) AS parents_with_normalized_version
       FROM documents d LEFT JOIN document_versions v USING(document_id)
       WHERE {source_filter} GROUP BY 1,2""")


def eu_months(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return query(con, f"""
      WITH v AS (SELECT work_uri, count(*) version_count,
         count(*) FILTER(WHERE extraction_status IN ('text_extracted','ocr_candidate_text_extracted')) readable_version_count
         FROM eu_content_versions GROUP BY 1)
      SELECT 'EU_CELLAR_COM' AS source_id, 'COM preparatory Work' AS genre,
             CASE WHEN try_cast(d.document_date AS DATE) IS NULL THEN 'UNKNOWN'
                  WHEN try_cast(d.document_date AS DATE)<DATE '{START}' THEN 'BEFORE'
                  WHEN try_cast(d.document_date AS DATE)>DATE '{END}' THEN 'AFTER'
                  ELSE substr(d.document_date,1,7) END AS month,
             count(*) AS parent_count,
             count(*) FILTER(WHERE coalesce(v.readable_version_count,0)>0) AS readable_parent_count,
             count(DISTINCT d.work_uri) AS distinct_parent_ids,
             count(DISTINCT d.work_uri) AS distinct_external_ids,
             count(DISTINCT d.work_uri) AS distinct_canonical_urls
      FROM eu_work_dates d LEFT JOIN v USING(work_uri) GROUP BY 1,2,3 ORDER BY 3
    """)


def eu_diagnostics(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return query(con, f"""
      SELECT 'EU_CELLAR_COM' AS source_id, 'COM preparatory Work' AS genre,
        count(*) AS parents,count(DISTINCT d.work_uri) AS distinct_parent_ids,
        count(DISTINCT d.work_uri) AS distinct_external_ids,
        count(DISTINCT d.work_uri) AS distinct_canonical_urls,
        count(*) FILTER(WHERE try_cast(d.document_date AS DATE) IS NULL) AS unknown_dates,
        count(*) FILTER(WHERE try_cast(d.document_date AS DATE)<DATE '{START}' OR try_cast(d.document_date AS DATE)>DATE '{END}') AS out_dates,
        0 AS child_document_rows,
        count(*) FILTER(WHERE EXISTS(SELECT 1 FROM eu_content_versions v WHERE v.work_uri=d.work_uri AND v.extraction_status IN ('text_extracted','ocr_candidate_text_extracted'))) AS readable_parents,
        count(*) FILTER(WHERE EXISTS(SELECT 1 FROM eu_content_versions v WHERE v.work_uri=d.work_uri)) AS parent_object_links,
        (SELECT count(DISTINCT item_uri) FROM eu_content_versions) AS distinct_objects,
        (SELECT count(*) FROM eu_content_versions) AS distinct_versions,
        count(*) FILTER(WHERE EXISTS(SELECT 1 FROM eu_content_versions v WHERE v.work_uri=d.work_uri)) AS parents_with_version,
        0 AS attachment_links,0 AS landing_links
      FROM eu_work_dates d
    """)


def au_verified_months(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return query(con,"""SELECT 'AU_VERIFIED_ORIGINAL' AS source_id,
        'verified primary publication' AS genre,
        CASE WHEN e.date_precision IN ('day','month') THEN substr(e.date_value,1,7)
             ELSE 'UNKNOWN' END AS month,
        count(*) AS parent_count,count(*) AS readable_parent_count,
        count(DISTINCT d.document_id) AS distinct_parent_ids,
        count(DISTINCT d.external_id) AS distinct_external_ids,
        count(DISTINCT d.canonical_url) AS distinct_canonical_urls
      FROM us_au_record_evidence e JOIN documents d USING(document_id)
      WHERE d.source_id='au_dcceew_current_catalogue_2026_snapshot'
        AND e.source_status='original_verified'
      GROUP BY 1,2,3 ORDER BY 3""")


def comparison_and_anomaly(counts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for (source, genre), group in counts[counts.month.isin(MONTHS)].groupby(["source_id", "genre"]):
        if source in ('src_3c349b00120866c263a3','au_dcceew_current_catalogue_2026_snapshot','AU_VERIFIED_ORIGINAL'):
            continue  # targeted mirror and unverified/small AU frames lack a continuous denominator
        observed = group[group.parent_count > 0]
        if len(observed) < 24:
            continue
        active_months = [m for m in MONTHS if observed.month.min() <= m <= observed.month.max() and m != "2026-09"]
        lookup = dict(zip(group.month, group.parent_count))
        for month in active_months:
            year, mon = map(int, month.split("-"))
            # An observed peer month is needed for a meaningful denominator.
            # Targeted seam/mirror recovery has deliberate gaps, which are not
            # equivalent to ordinary zero-output months in a continuous frame.
            refs = [f"{yy:04d}-{mon:02d}" for yy in range(year-5, year+6)
                    if yy != year and f"{yy:04d}-{mon:02d}" in active_months
                    and lookup.get(f"{yy:04d}-{mon:02d}",0)>0]
            if len(refs) < 4:
                continue
            values = np.array([int(lookup[r]) for r in refs], dtype=float)
            logs = np.log1p(values)
            baseline = float(np.median(values))
            center = float(np.median(logs))
            scale = max(1.4826 * float(np.median(np.abs(logs-center))), 0.35)
            n = int(lookup.get(month,0))
            z = (math.log1p(n)-center)/scale
            direction = 'high' if z > 0 else 'low'
            flag = abs(z) >= 2.5 and ((direction=='high' and n>=10 and n>=2*max(baseline,1) and n-baseline>=10) or
                                       (direction=='low' and baseline>=10 and n<=baseline/2))
            rows.append([source,genre,month,n,baseline,len(refs),z,direction,flag])
    scored = pd.DataFrame(rows,columns=['source_id','genre','month','parent_count','same_calendar_month_reference_median','reference_months','robust_log_score','direction','flag'])
    flagged = scored[scored.flag].copy()
    flagged['priority'] = flagged.robust_log_score.abs()
    flagged = flagged.sort_values(['priority','source_id','genre','month'],ascending=[False,True,True,True])
    selected = []
    per_source = Counter(); per_direction=Counter(); per_month = Counter(); chosen=set()
    def choose(x):
        key=(x.source_id,x.genre,x.month)
        if key in chosen or len(selected)>=20 or per_source[x.source_id]>=4 or per_month[x.month]>=2 or per_direction[(x.source_id,x.direction)]>=3:
            return
        selected.append(x);chosen.add(key)
        per_source[x.source_id]+=1;per_month[x.month]+=1;per_direction[(x.source_id,x.direction)]+=1
    # Reserve one high flag per source before global severity ranking so large
    # source-frame zeros do not consume every review slot.
    for source in sorted(flagged.source_id.unique()):
        high=flagged[(flagged.source_id==source)&(flagged.direction=='high')]
        if len(high): choose(high.iloc[0])
    for _, x in flagged.iterrows(): choose(x)
    return scored, pd.DataFrame(selected).sort_values(['priority','source_id','genre','month'],ascending=[False,True,True,True])


def anomaly_evidence(con: duckdb.DuckDBPyConnection, source: str, genre: str, month: str) -> dict:
    # Literal values originate in repository data, so parameters are used for every filter.
    where = "d.source_id=? AND d.content_type=? AND strftime(d.publication_date,'%Y-%m')=?"
    p = [source,genre,month]
    q = query(con,f"""WITH x AS (SELECT d.document_id,d.publication_date,d.external_id,d.canonical_url,
           d.body_status,co.content_object_id,co.relationship_type,v.content_version_id
           FROM documents d LEFT JOIN document_content_objects co USING(document_id)
           LEFT JOIN content_versions v USING(content_object_id) WHERE {where})
       SELECT count(DISTINCT document_id) parents,count(DISTINCT external_id) external_ids,
         count(DISTINCT canonical_url) urls,count(DISTINCT content_object_id) objects,
         count(DISTINCT content_version_id) versions,
         count(*) FILTER(WHERE relationship_type='attachment') attachment_links,
         count(*) FILTER(WHERE relationship_type='landing_page') landing_links,
         count(DISTINCT document_id) FILTER(WHERE content_version_id IS NOT NULL) parents_with_version
       FROM x""",p).iloc[0].to_dict()
    days = query(con,f"SELECT cast(publication_date as varchar) AS day,count(*) n FROM documents d WHERE {where} GROUP BY 1 ORDER BY n DESC,day LIMIT 3",p)
    objects = query(con,f"""SELECT count(*) shared_objects,coalesce(max(n),0) max_parents_per_object
       FROM (SELECT co.content_object_id,count(DISTINCT d.document_id) n
         FROM documents d JOIN document_content_objects co USING(document_id)
         WHERE {where} GROUP BY 1 HAVING count(DISTINCT d.document_id)>1)""",p).iloc[0].to_dict()
    batch = query(con,f"""SELECT e.batch_id,count(DISTINCT d.document_id) n
       FROM documents d JOIN enumeration_records e USING(document_id)
       WHERE {where} GROUP BY 1 ORDER BY n DESC,e.batch_id LIMIT 4""",p)
    q.update(objects)
    q['top_days'] = '; '.join(f"{r.day}:{r.n}" for r in days.itertuples())
    q['batches'] = '; '.join(f"{r.batch_id}:{r.n}" for r in batch.itertuples())
    return q


def eu_anomaly_evidence(con: duckdb.DuckDBPyConnection, month: str) -> dict:
    q = query(con,"""WITH m AS (SELECT work_uri,document_date FROM eu_work_dates WHERE substr(document_date,1,7)=?),
       v AS (SELECT work_uri,item_uri,version_id FROM eu_content_versions WHERE work_uri IN (SELECT work_uri FROM m))
       SELECT (SELECT count(*) FROM m) parents,(SELECT count(DISTINCT work_uri) FROM m) external_ids,
        (SELECT count(DISTINCT work_uri) FROM m) urls,(SELECT count(DISTINCT item_uri) FROM v) objects,
        (SELECT count(*) FROM v) versions,(SELECT count(DISTINCT work_uri) FROM v) parents_with_version""",[month]).iloc[0].to_dict()
    days=query(con,"SELECT document_date AS day,count(*) n FROM eu_work_dates WHERE substr(document_date,1,7)=? GROUP BY 1 ORDER BY n DESC,document_date LIMIT 3",[month])
    q.update({'attachment_links':0,'landing_links':0,'shared_objects':0,'max_parents_per_object':1,
              'top_days':'; '.join(f'{r.day}:{r.n}' for r in days.itertuples()),'batches':'EU frozen COM Work enumeration'})
    return q


def interpret(row: pd.Series) -> dict[str,str]:
    source, month = row.source_id, row.month
    parliament_2024='https://www.parliament.uk/about/how/elections-and-voting/general/general-election-2024-timetable/'
    parliament_2015='https://www.parliament.uk/business/news/news-by-year/2015/march/prorogation-end-of-session/'
    parliament_1997='https://publications.parliament.uk/pa/ld199899/ldselect/ldprivi/106i/106i20.htm'
    parliament_recess='https://www.parliament.uk/about/faqs/house-of-commons-faqs/business-faq-page/recess-dates/list-of-previous-commons-recess-dates/'
    parliament_2000='https://publications.parliament.uk/pa/cm200001/csession/100/10010.htm'
    parliament_2010='https://www.parliament.uk/business/news/news-by-year/2010/04/dissolution-of-parliament-12-april-2010/'
    if source=='src_90b3a872375c9e7fd267' and month=='2024-06':
        return dict(assessment='calendar-supported low',supported_cause='Commons dissolved 30 May until new Parliament returned 9 July; no Commons written answers in this source month is calendar-consistent.',alternative_explanation='No independent completeness claim for every other government channel.',unresolved_evidence='Zero applies only to approved Commons answering bodies, not all UK policy text.',action='Retain zero and annotate dissolution in source availability calendar.',independent_evidence_url=parliament_2024)
    if source=='src_90b3a872375c9e7fd267' and month=='2024-08':
        return dict(assessment='date/channel check pending',supported_cause='62 distinct answer parents with unique IDs/URLs, concentrated on 1–5 August; no pagination or shared-object multiplication of parent IDs is observed.',alternative_explanation='Answers can be released in recess, or API date assignment/transition behaviour may differ after the election.',unresolved_evidence='The saved publication-date basis and a bounded sample of original answer pages need comparison with the Commons recess calendar.',action='Retain; verify date fields and original pages for three top-day IDs before interpreting the high.',independent_evidence_url='https://www.parliament.uk/business/news/2024/july/the-house-of-commons-rises-for-summer-recess/')
    if source=='src_90b3a872375c9e7fd267' and month in ('2015-04','2015-05'):
        return dict(assessment='calendar-supported low',supported_cause='Parliament dissolved 30 March; new Parliament first met 18 May, so these month bins contain little/no ordinary Commons business.',alternative_explanation='The selected answering-body frame may also have source-specific gaps.',unresolved_evidence='A calendar explanation does not verify every omitted API record.',action='Retain zero; record dissolution/reassembly and compare other sources separately.',independent_evidence_url=parliament_2015)
    if source=='src_549acfda11091ff8c9b8' and month=='1997-04':
        return dict(assessment='calendar-supported low',supported_cause='Parliament was dissolved on 8 April 1997; the month was interrupted.',alternative_explanation='Historic volume acquisition could also be incomplete.',unresolved_evidence='The zero in this selected department/source frame is not a claim about all government publication.',action='Retain zero; check volume availability only if April 1997 becomes a specified research window.',independent_evidence_url=parliament_1997)
    if source=='src_549acfda11091ff8c9b8' and month in ('1999-09','2000-09'):
        return dict(assessment='calendar-supported low',supported_cause='Commons summer recess covered September in the cited session calendar.',alternative_explanation='Historic archive selection is limited to successfully downloaded volumes.',unresolved_evidence='Source-specific completeness outside the downloaded volumes remains bounded.',action='Retain zero and annotate recess; no volume flattening.',independent_evidence_url=parliament_recess if month=='1999-09' else parliament_2000)
    if source=='src_9e8f487d372ed011db82' and month=='2010-05':
        return dict(assessment='calendar-supported low',supported_cause='Parliament dissolved 12 April and returned 18 May; one selected statement but no answers in May.',alternative_explanation='The official archive partition is not an unrestricted all-departments series.',unresolved_evidence='Restart of written-answer publication after return is not independently checked here.',action='Retain zero; annotate transition month.',independent_evidence_url=parliament_2010)
    if source=='src_9e8f487d372ed011db82' and month=='2005-05':
        return dict(assessment='partial calendar and source onset',supported_cause='Only four dates (23–26 May) contribute 54 parents in this first observed month of the archive source.',alternative_explanation='Election/new-Parliament timing likely reduced available sitting days.',unresolved_evidence='No complete official daily index for the whole month was rechecked.',action='Retain; label first observed source month and avoid comparing as full month.',independent_evidence_url='https://publications.parliament.uk/pa/cm/cmhn0505.htm')
    if source=='src_9e8f487d372ed011db82' and month=='2013-05':
        return dict(assessment='partial acquisition supported',supported_cause='Official archive has 62 answer parents from two dates/two shared pages; overlapping annual query partitions are recorded partial.',alternative_explanation='Targeted mirror has additional 120 records on six dates, but cross-source identity needs reconciliation.',unresolved_evidence='Official index/page/parser gaps prevent an all-month publication estimate.',action='Bounded date/page reconciliation if 2013-05 matters; preserve both original and mirror provenance.',independent_evidence_url='')
    if source==US and month.startswith('1994-'):
        return dict(assessment='source-frame gap unresolved',supported_cause='The frozen selected metadata contains 1994 dates only in January, September and November; this zero is inside the selected API frame.',alternative_explanation='Historical API representation or filter depth may differ from later years; official publication absence is unproven.',unresolved_evidence='No issue-level EPA/DOE denominator for this month; all pages in the saved API enumeration were reconciled.',action='Mark selected-frame gap; use bounded official issue/index check only for a named research window.',independent_evidence_url='')
    if source==US and month=='1996-02':
        return dict(assessment='selected-frame high unresolved',supported_cause='110 final-rule parents have 110 distinct IDs, URLs, objects and versions; top day contributes 15, so duplicate pagination or saved versions do not explain parent volume.',alternative_explanation='A real agency rulemaking concentration or source filter mix.',unresolved_evidence='No independent dated checkpoint or issue-level expected denominator was checked.',action='Retain all 110; inspect source agency/date mix only if February 1996 enters an RQ2 window.',independent_evidence_url='')
    if source=='src_ac30b1ae596ab5ab5379' and month=='2013-04':
        return dict(assessment='dated policy-series concentration',supported_cause='25 of 33 parents share 9 April; 23 have the 2010–2015 government-policy title series. The 33 parents link to 73 objects; attachments are not extra parents.',alternative_explanation='A coordinated original publication or later CMS migration could produce the cluster.',unresolved_evidence='Many saved pages show 2015 update times; their exact 2013 body wording is not established.',action='Retain 33 parents; review first-publication evidence and version history before interpreting the dated spike.',independent_evidence_url='')
    if source=='src_ac30b1ae596ab5ab5379' and month=='2011-06':
        return dict(assessment='dated publication cluster',supported_cause='17 unique parents and 35 linked objects; five distinct papers have 14 June first-publication dates. Object/segment expansion does not increase parent count.',alternative_explanation='Routine departmental publication batching rather than one substantive event.',unresolved_evidence='No independent event attribution is tested; historical body versions may have changed.',action='Retain; preserve individual publication dates and parent-object links.',independent_evidence_url='')
    if source=='EU_CELLAR_COM' and month=='1988-04':
        return dict(assessment='date concentration unresolved',supported_cause='186 distinct Work URIs; 67 map to 5 April in one saved monthly Work page. 136 Works have staged Items; no duplicated Work URI in the month.',alternative_explanation='Real publication batch or historical metadata date assignment.',unresolved_evidence='A bounded original-Item issue-date check is needed for the 5 April cluster.',action='Retain; verify a small Work sample against original dated Items before event use.',independent_evidence_url='')
    if source=='EU_CELLAR_COM':
        return dict(assessment='source-class low unresolved',supported_cause='Distinct COM preparatory Works are counted; no duplicate URI or Item-version multiplication explains the low. No Item bodies are staged for this month.',alternative_explanation='A real publication decline or migration into an adjacent CELLAR class.',unresolved_evidence='Frozen class excludes adjacent proposal types; broad Commission output is not measured.',action='Retain source-class count and compare official class metadata only if this month is analytically selected.',independent_evidence_url='')
    return dict(assessment='unresolved source-volume flag',supported_cause='Distinct parent IDs and URLs; no duplicate pagination or version multiplication observed in the bounded ledger.',alternative_explanation='Ordinary publication/calendar variation.',unresolved_evidence='Source-specific date and availability evidence not yet sufficient for attribution.',action='Retain and label unresolved; inspect only if selected as a research window.',independent_evidence_url='')


def main() -> None:
    HERE.mkdir(parents=True,exist_ok=True)
    uk=duckdb.connect(str(DB['UK']),read_only=True)
    us=duckdb.connect(str(DB['US_AU']),read_only=True)
    eu=duckdb.connect(str(DB['EU']),read_only=True)
    au=duckdb.connect(str(DB['AU_original']),read_only=True)
    au_verified=au_verified_months(us)
    monthly=pd.concat([month_rows(uk,"source_id NOT IN ('us_fr_epa_doe_rules_1994','au_dcceew_current_catalogue_2026_snapshot')"),
                       month_rows(us,f"source_id IN ('{US}','{AU}')"),eu_months(eu),au_verified],ignore_index=True)
    # A complete calendar grid makes zero months explicit. Unknown dates remain
    # separate and are never redistributed across months.
    groups=monthly[['source_id','genre']].drop_duplicates()
    grid=groups.merge(pd.DataFrame({'month':MONTHS}),how='cross')
    monthly=grid.merge(monthly,on=['source_id','genre','month'],how='left',suffixes=('','_source'))
    other_months=pd.concat([month_rows(uk,"source_id NOT IN ('us_fr_epa_doe_rules_1994','au_dcceew_current_catalogue_2026_snapshot')"),
                            month_rows(us,f"source_id IN ('{US}','{AU}')"),eu_months(eu),au_verified],ignore_index=True)
    other_months=other_months[~other_months.month.isin(MONTHS)]
    monthly=pd.concat([monthly,other_months],ignore_index=True)
    numeric=['parent_count','readable_parent_count','distinct_parent_ids','distinct_external_ids','distinct_canonical_urls']
    monthly[numeric]=monthly[numeric].fillna(0).astype(int)
    span=monthly[monthly.parent_count.gt(0)&monthly.month.isin(MONTHS)].groupby(['source_id','genre']).month.agg(['min','max']).reset_index()
    monthly=monthly.merge(span,on=['source_id','genre'],how='left')
    monthly['source_observed_span']=monthly['min'].astype(str)+'..'+monthly['max'].astype(str)
    monthly['in_observed_span']=monthly.apply(lambda r:r.month in MONTHS and r['min']<=r.month<=r['max'],axis=1)
    monthly=monthly.drop(columns=['min','max'])
    monthly['source_label']=monthly.source_id.map(SOURCE_SHORT)
    monthly['count_unit']=monthly.source_id.map(lambda x:'Work' if x=='EU_CELLAR_COM' else 'verified original subset of AU catalogue' if x=='AU_VERIFIED_ORIGINAL' else 'catalogue candidate (date unverified)' if x==AU else 'selected Register document parent' if x==US else 'independent document parent')
    monthly['frame_note']=monthly.source_id.map(lambda x:'frozen COM/act_preparatory/English enumeration' if x=='EU_CELLAR_COM' else '7 verified originals: 5 month/day dated and 2 year-only; overlaps catalogue candidates' if x=='AU_VERIFIED_ORIGINAL' else 'current catalogue; 819/821 parent publication dates unknown in documents table; overlaps verified-original subset' if x==AU else 'EPA/DOE final and proposed rules, metadata selected' if x==US else 'approved UK source/channel and genre')
    monthly['partial_month']=monthly.month.eq('2026-09')
    monthly['date_interval']=START+'..'+END
    monthly=monthly.rename(columns={'readable_parent_count':'extracted_status_parent_count'})
    monthly.to_csv(HERE/'monthly_source_genre_counts.csv',index=False)
    diagnostics=pd.concat([source_diagnostics(uk,"source_id NOT IN ('us_fr_epa_doe_rules_1994','au_dcceew_current_catalogue_2026_snapshot')"),
                           source_diagnostics(us,f"source_id IN ('{US}','{AU}')"),eu_diagnostics(eu)],ignore_index=True)
    au_n=int(au_verified.parent_count.sum())
    au_unknown=int(au_verified.loc[au_verified.month.eq('UNKNOWN'),'parent_count'].sum())
    au_original_diag=pd.DataFrame([{'source_id':'AU_VERIFIED_ORIGINAL','genre':'verified primary publication','parents':au_n,'distinct_parent_ids':au_n,'distinct_external_ids':au_n,'distinct_canonical_urls':au_n,'unknown_dates':au_unknown,'out_dates':0,'child_document_rows':0,'readable_parents':au_n,'parent_object_links':None,'distinct_objects':None,'distinct_versions':None,'parents_with_version':au_n,'attachment_links':None,'landing_links':None}])
    diagnostics=pd.concat([diagnostics,au_original_diag],ignore_index=True)
    nv=pd.concat([normalized_versions(uk,"source_id NOT IN ('us_fr_epa_doe_rules_1994','au_dcceew_current_catalogue_2026_snapshot')"),
                  normalized_versions(us,f"source_id IN ('{US}','{AU}')")],ignore_index=True)
    diagnostics=diagnostics.merge(nv,on=['source_id','genre'],how='left')
    diagnostics['source_label']=diagnostics.source_id.map(SOURCE_SHORT)
    diagnostics['duplicate_parent_ids']=diagnostics.parents-diagnostics.distinct_parent_ids
    diagnostics['duplicate_external_ids']=diagnostics.parents-diagnostics.distinct_external_ids
    diagnostics['duplicate_canonical_urls']=diagnostics.parents-diagnostics.distinct_canonical_urls
    diagnostics['unit_note']=diagnostics.source_id.map(lambda x:'One CELLAR Work; Item versions separate' if x=='EU_CELLAR_COM' else 'Verified original subset of same catalogue candidates; do not add to candidate frame' if x=='AU_VERIFIED_ORIGINAL' else 'Catalogue candidate, not verified original' if x==AU else 'Document parent; object and version counts are distinct global units, shared objects may map to many parents')
    diagnostics['status_extracted_not_text_verified']=True
    diagnostics['extracted_segments_are_independent_parents']=False
    diagnostics['segment_evidence_scope']='See long_text_segment_evidence.csv (dated UK summary); source pages and objects can be shared across parents, so no additive source-month segment count is asserted.'
    diagnostics=diagnostics.rename(columns={'readable_parents':'extracted_status_parents'})
    diagnostics.to_csv(HERE/'unit_and_duplicate_diagnostics.csv',index=False)
    scored, selected=comparison_and_anomaly(monthly)
    scored.to_csv(HERE/'anomaly_scores_all_months.csv',index=False)
    ledger=[]
    for rank,(_,x) in enumerate(selected.iterrows(),1):
        source=x.source_id;genre=x.genre;month=x.month
        con=eu if source=='EU_CELLAR_COM' else us if source in (US,AU) else uk
        ev=eu_anomaly_evidence(eu,month) if source=='EU_CELLAR_COM' else anomaly_evidence(con,source,genre,month)
        item={**x.to_dict(),**ev,'rank':rank,'source_label':SOURCE_SHORT[source]}
        ledger.append(item)
    ledger=pd.DataFrame(ledger)
    if not ledger.empty:
        ledger['observed']=ledger.apply(lambda r:f"{r.parent_count} parents/Works vs same-month reference median {r.same_calendar_month_reference_median:g}; {r.top_days}",axis=1)
        explanations=pd.DataFrame([interpret(row) for _,row in ledger.iterrows()])
        ledger=pd.concat([ledger.reset_index(drop=True),explanations],axis=1)
        ledger['evidence_ref']=ledger.apply(lambda r:f"read-only {DB['EU' if r.source_id=='EU_CELLAR_COM' else 'US_AU' if r.source_id in (US,AU) else 'UK'].relative_to(ROOT)}; source_id={r.source_id}; month={r.month}",axis=1)
        ledger.to_csv(HERE/'anomaly_ledger.csv',index=False)
    # Bounded samples: up to three parents/Works for each nonzero selected flag.
    samples=[]
    for _,r in ledger[ledger.parent_count.gt(0)].iterrows():
        if r.source_id=='EU_CELLAR_COM':
            q=query(eu,"""SELECT d.work_uri AS parent_id,d.document_date AS publication_date,
              d.source_page AS source_locator,coalesce(v.version_count,0) linked_versions,
              coalesce(v.max_text_characters,0) max_version_text_characters
              FROM eu_work_dates d LEFT JOIN
              (SELECT work_uri,count(*) version_count,max(text_characters) max_text_characters
               FROM eu_content_versions GROUP BY 1) v USING(work_uri)
              WHERE substr(d.document_date,1,7)=? ORDER BY d.document_date,d.work_uri LIMIT 3""",[r.month])
            for x in q.to_dict('records'): samples.append({'source_id':r.source_id,'month':r.month,**x})
        else:
            con=us if r.source_id in (US,AU) else uk
            q=query(con,"""SELECT d.document_id AS parent_id,cast(d.publication_date as varchar) AS publication_date,
               d.title,d.canonical_url AS source_locator,count(DISTINCT x.content_object_id) linked_objects,
               count(DISTINCT v.content_version_id) linked_versions,
               count(*) FILTER(WHERE x.relationship_type='attachment') attachment_links,
               max(s.segment_count) AS max_linked_object_segments
               FROM documents d LEFT JOIN document_content_objects x USING(document_id)
               LEFT JOIN content_versions v USING(content_object_id)
               LEFT JOIN acquisition_object_statuses s USING(content_object_id)
               WHERE d.source_id=? AND d.content_type=? AND strftime(d.publication_date,'%Y-%m')=?
               GROUP BY d.document_id,d.publication_date,d.title,d.canonical_url
               ORDER BY d.publication_date,d.document_id LIMIT 3""",[r.source_id,r.genre,r.month])
            for x in q.to_dict('records'): samples.append({'source_id':r.source_id,'month':r.month,**x})
    pd.DataFrame(samples).to_csv(HERE/'bounded_parent_object_samples.csv',index=False)
    peaks=[]
    for source,genre in [('src_549acfda11091ff8c9b8','ministerial_written_answer'),
                         ('src_90b3a872375c9e7fd267','ministerial_written_answer'),
                         (US,'final_rule'),('EU_CELLAR_COM','COM preparatory Work')]:
        q=monthly[(monthly.source_id==source)&(monthly.genre==genre)&monthly.month.isin(MONTHS)]
        x=q.sort_values(['parent_count','month'],ascending=[False,True]).iloc[0]
        ev=eu_anomaly_evidence(eu,x.month) if source=='EU_CELLAR_COM' else anomaly_evidence(us if source==US else uk,source,genre,x.month)
        score=scored[(scored.source_id==source)&(scored.genre==genre)&(scored.month==x.month)]
        is_flag=bool(score.iloc[0].flag) if len(score) else False
        peaks.append({'source_id':source,'source_label':SOURCE_SHORT[source],'genre':genre,'month':x.month,
                      'parent_count':int(x.parent_count),'robust_score':float(score.iloc[0].robust_log_score) if len(score) else None,
                      'flagged_by_rule':is_flag,
                      'review_note':'Absolute maximum for this major source/genre; retained, not downsampled. Review flag is shown separately.' if is_flag else 'Absolute maximum for this major source/genre; unflagged by the seasonal rule and retained.',**ev})
    pd.DataFrame(peaks).to_csv(HERE/'absolute_peak_context.csv',index=False)
    # Exact date/title matches are review candidates, not a deduplicated count.
    mirror_candidates=query(uk,"""WITH m AS (SELECT document_id,publication_date,title,lower(trim(title)) norm_title
       FROM documents WHERE source_id='src_3c349b00120866c263a3'),
       o AS (SELECT document_id,publication_date,title,lower(trim(title)) norm_title
       FROM documents WHERE source_id IN ('src_9e8f487d372ed011db82','src_549acfda11091ff8c9b8'))
       SELECT m.document_id mirror_parent_id,o.document_id official_parent_id,
         m.publication_date,m.title FROM m JOIN o USING(publication_date,norm_title)
       ORDER BY m.publication_date,m.document_id,o.document_id""")
    mirror_candidates.to_csv(HERE/'cross_source_title_date_candidates.csv',index=False)
    length_path=SOURCE/'07_historical_government_acquisition/reports/post_acquisition_distribution_coverage/record_text_length_distribution.csv'
    length=pd.read_csv(length_path)
    length=length[length['quantile'].isin(['p50','p99','p100']) & length['series'].isin(['ministerial_written_answer','policy_document'])]
    length['evidence_unit']='record-level existing UK summary'
    length['source_snapshot_path']=str(length_path.relative_to(ROOT))
    length.to_csv(HERE/'long_text_segment_evidence.csv',index=False)
    # Exact source-level checkpoint and a bounded ordinary-period comparator.
    summary={}
    for name,con in [('UK',uk),('US_AU',us),('EU',eu),('AU_original',au)]:
        if name=='EU':
            result=query(con,'select min(retrieved_at_utc) first_retrieval,max(retrieved_at_utc) last_retrieval from eu_content_versions').iloc[0].to_dict()
        elif name=='AU_original':
            result=query(con,'select min(retrieved_at_utc) first_retrieval,max(retrieved_at_utc) last_retrieval from au_browser_versions').iloc[0].to_dict()
        else:
            result=query(con,'select min(retrieved_at) first_retrieval,max(retrieved_at) last_retrieval from content_versions').iloc[0].to_dict()
        summary[name]={'path':str(DB[name].relative_to(ROOT)),'file_mtime_utc':iso_mtime(DB[name]),'size_bytes':DB[name].stat().st_size,
                       'retrieval_range':{k:str(v) for k,v in result.items()}}
    reference=SOURCE/'12_project_eda_snapshot_20260927/DATA_MANIFEST.json'
    inputs={'generated_utc':datetime.now(timezone.utc).isoformat(),'publication_interval_inclusive':[START,END],
            'september_2026_partial':True,'databases':summary,'baseline_only':str(reference.relative_to(ROOT)),
            'units':{'UK':'documents.document_id; genre=content_type; no shared copy from 09 DB; extracted status is not reverified text',
                     'US':'09 DB documents.document_id; final/proposed rule selected metadata; extracted status based on body_status',
                     'AU':'09 DB current catalogue candidate document_id; 819 unknown publication dates in documents, plus a separately displayed 7-original verified subset (5 month/day dated, 2 year-only); frames overlap and are not additive',
                     'EU':'eu_work_dates.work_uri; frozen COM preparatory Work; Item/version distinct'},
            'filter':'publication_date or EU document_date between 1988-01-01 and 2026-09-21 inclusive; UNKNOWN/BEFORE/AFTER retained as separate rows; no topic/emotion filtering',
            'anomaly_rule':'For each source_id×genre with >=24 positive months, excluding targeted mirror and AU frames: compare each nonpartial month inside observed source span with positive-count same-calendar months in +/-5 years (>=4 references). log1p robust score uses max(1.4826 MAD,0.35); |score|>=2.5, high >=10 and >=2x median with >=10 excess parents, low median>=10 and <=half. Reserve top high flag per source, then fill by |score| descending/source/genre/month, cap 4 per source, 3 per source×direction and 2 per month; take <=20 and re-rank by severity. Review flags only.',
            'source_specific_snapshots_not_synchronous':True}
    inputs['supplementary_inputs']=[{'path':str(length_path.relative_to(ROOT)),'file_mtime_utc':iso_mtime(length_path)},
        {'path':str((SOURCE/'06_government_content_acquisition/text_quality_review/03_segment_length_distribution.csv').relative_to(ROOT)),
         'file_mtime_utc':iso_mtime(SOURCE/'06_government_content_acquisition/text_quality_review/03_segment_length_distribution.csv')}]
    (HERE/'INPUT_MANIFEST.json').write_text(json.dumps(inputs,indent=2,default=str)+'\n')
    # Single small comparison period for each of the three largest historical frames.
    comp=[]
    for source,genre in [('src_549acfda11091ff8c9b8','ministerial_written_answer'),
                         ('src_90b3a872375c9e7fd267','ministerial_written_answer'),
                         (US,'final_rule'),('EU_CELLAR_COM','COM preparatory Work')]:
        d=scored[(scored.source_id==source)&(scored.genre==genre)&(~scored.flag)&(scored.parent_count>0)]
        if len(d):
            x=d.iloc[(d.robust_log_score.abs()).argmin()]
            comp.append(x.to_dict())
    pd.DataFrame(comp).to_csv(HERE/'ordinary_comparison_periods.csv',index=False)
    for con in (uk,us,eu,au): con.close()
    print('monthly rows',len(monthly),'diagnostic rows',len(diagnostics),'flags',int(scored.flag.sum()),'selected',len(ledger))
    print('source totals',monthly[monthly.month.isin(MONTHS)].groupby('source_label').parent_count.sum().to_dict())
    print(ledger[['rank','source_label','genre','month','parent_count','same_calendar_month_reference_median','robust_log_score','top_days']].to_string(index=False))


if __name__=='__main__':main()
