"""Read-only, bounded Paris-window readiness and government diagnostic sample."""
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'work_packages/M1_source_access'
BRIDGE = BASE / '09_us_au_government_acquisition/reports/targeted_2015_bridge'
POOL = BASE / '09_us_au_government_acquisition/reports/pooled_month_role_coverage_2026-09-27.csv'
UK_DB = BASE / '06_government_content_acquisition/fear_temperature_government_content.duckdb'
SEED = 'paris-readiness-20260927-v1'
TERMS = ('climate', 'warming', 'carbon', 'greenhouse', 'energy', 'temperature', 'emission')
UK_SOURCES = {
    'policy': 'src_ac30b1ae596ab5ab5379',
    'ministerial_answer_statement': 'src_90b3a872375c9e7fd267',
}


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def rank(identifier):
    return hashlib.sha256(f'{SEED}|{identifier}'.encode()).hexdigest()


def clipped(s, n=360):
    return re.sub(r'\s+', ' ', s or '').strip()[:n]


def month_range():
    y, m = 2013, 12
    while (y, m) <= (2017, 12):
        yield f'{y:04d}-{m:02d}'
        m += 1
        if m == 13:
            y, m = y + 1, 1


def matrix():
    pooled = {r['year_month']: r for r in read_csv(POOL) if r['role'] == 'government'}
    updated = {r['year_month']: r for r in read_csv(BRIDGE / 'updated_monthly_government_presence.csv')}
    epa = {r['year_month']: r for r in read_csv(BRIDGE / 'monthly_source_coverage_2012_2019.csv')}
    rows = []
    for offset, month in enumerate(month_range(), -24):
        p, u, e = pooled[month], updated[month], epa[month]
        new = int(e['selected_nonempty_source_text_count'])
        # The earlier pooled checkpoint predates this newly accepted bridge tranche.
        dated_floor = int(p['source_parent_sum_observed']) + new
        readable_floor = int(p['source_parent_sum_readable']) + new
        gov = dict(month=month, role='government', event_month_offset=offset,
                   eligible_denominator_source='EPA in frozen FR agency strata; API final_rule; original publication day',
                   eligible_denominator=int(e['eligible_unique_parent_count']),
                   dated_independent_parent_count=dated_floor,
                   readable_independent_parent_count=readable_floor,
                   count_qualifier='documented_checkpoint_lower_bound; earlier pooled snapshot plus newly accepted EPA bridge',
                   verified_warming_relevant_parent_count='', verified_fear_relevant_parent_count='',
                   relevance_review_state='not_reviewed_for_full_month',
                   coverage_state='readable_parent_present' if u['pooled_government_text_present_updated']=='1' else 'no_readable_parent',
                   source_genre='UK policy/ministerial answer or statement; EU Commission preparatory Work; US Federal Register rule; AU if present',
                   uk_dated=int(p['uk_dated_parents']), uk_readable=int(p['uk_extracted_parents']),
                   eu_dated=int(p['eu_dated_works']), eu_readable=int(p['eu_source_text_parents']),
                   us_dated_checkpoint=int(p['us_dated_parents'])+new,
                   us_readable_checkpoint=int(p['us_cleaned_parents'])+new,
                   au_dated=int(p['au_original_month_parents']), au_readable=int(p['au_cleaned_parents']),
                   epa_eligible=int(e['eligible_unique_parent_count']), epa_selected_readable=new,
                   evidence_paths=f'{POOL.relative_to(ROOT)} | {(BRIDGE / "updated_monthly_government_presence.csv").relative_to(ROOT)} | {(BRIDGE / "monthly_source_coverage_2012_2019.csv").relative_to(ROOT)}')
        rows.append(gov)
        for role in ('media', 'public'):
            rows.append(dict(month=month, role=role, event_month_offset=offset,
                             eligible_denominator_source='', eligible_denominator='',
                             dated_independent_parent_count='', readable_independent_parent_count='',
                             count_qualifier='not_collected_or_audited_for_complete_month',
                             verified_warming_relevant_parent_count='', verified_fear_relevant_parent_count='',
                             relevance_review_state='not_reviewed_for_full_month', coverage_state='not_collected_or_audited',
                             source_genre='', evidence_paths=''))
    fields=list(rows[0].keys())
    write_csv(OUT/'paris_month_role_readiness_49x3.csv', rows, fields)
    assert len(rows)==147 and sum(r['coverage_state']=='readable_parent_present' for r in rows)==49
    return rows


def uk_sample():
    db = duckdb.connect(str(UK_DB), read_only=True)
    rows=[]
    try:
        for genre, sid in UK_SOURCES.items():
            for month in ('2015-02','2015-03','2015-06','2015-07'):
                docs=db.execute("""SELECT document_id, external_id, title, canonical_url,
                          CAST(publication_date AS VARCHAR), CAST(updated_timestamp AS VARCHAR),
                          body_status, content_type
                    FROM documents WHERE source_id=? AND strftime(publication_date,'%Y-%m')=?
                    ORDER BY document_id""", [sid, month]).fetchall()
                candidates=[d for d in docs if any(t in d[2].lower() for t in TERMS)]
                selected=[]
                if candidates: selected.append(('title_candidate',min(candidates,key=lambda d:rank(d[0]))))
                controls=[d for d in docs if not any(t in d[2].lower() for t in TERMS)]
                if controls: selected.append(('control',min(controls,key=lambda d:rank(d[0]))))
                exact=[d for d in docs if any(t in d[2].lower() for t in ('climate','greenhouse','global warming','paris'))]
                if exact:
                    extra=min(exact,key=lambda d:rank(d[0]))
                    if all(d[0]!=extra[0] for _,d in selected): selected.append(('supplementary_exact_title',extra))
                for stratum,d in selected:
                    did, ext, title, url, date, upd, status, ctype=d
                    links=db.execute("""SELECT o.object_kind, v.content_version_id, v.raw_path,
                                      v.version_status, o.canonical_url
                                      FROM document_content_objects x
                                      JOIN content_objects o USING(content_object_id)
                                      LEFT JOIN content_versions v USING(content_object_id)
                                      WHERE x.document_id=? ORDER BY o.object_kind, o.canonical_url""",[did]).fetchall()
                    vids=[x[1] for x in links if x[1]]
                    segs=[]
                    if genre=='ministerial_answer_statement' and ext.startswith('written_question:'):
                        qid=ext.split(':',1)[1]
                        segs=db.execute("""SELECT segment_id, content_version_id, locator, segment_text
                                  FROM text_segments WHERE locator LIKE ? OR locator LIKE ?
                                  ORDER BY locator LIMIT 8""",[f'%source_id=question:{qid};%',f'%source_id=answer:{qid}:%']).fetchall()
                    elif vids:
                        segs=db.execute("""SELECT segment_id, content_version_id, locator, segment_text
                                   FROM text_segments WHERE content_version_id IN (SELECT unnest(?))
                                   AND (lower(segment_text) LIKE '%climate%' OR lower(segment_text) LIKE '%warming%'
                                        OR lower(segment_text) LIKE '%carbon%' OR lower(segment_text) LIKE '%temperature%')
                                   ORDER BY segment_order LIMIT 4""",[vids]).fetchall()
                        if not segs:
                            segs=db.execute("""SELECT segment_id, content_version_id, locator, segment_text
                                      FROM text_segments WHERE content_version_id IN (SELECT unnest(?))
                                      AND length(segment_text)>80 AND locator NOT LIKE '%title%'
                                      ORDER BY segment_order LIMIT 2""",[vids]).fetchall()
                    segment_ids=' | '.join(s[0] for s in segs)
                    excerpt=' | '.join(clipped(s[3],220) for s in segs[:3])
                    rows.append(dict(role='government',source='UK '+genre,month=month,sampling_stratum=stratum,
                         candidate_pool=len(candidates),control_pool=len(controls),parent_id=did,external_id=ext,
                         title=title,publication_date=date,updated_at=upd,url=url,body_status=status,
                         content_type=ctype,content_versions=' | '.join(vids),object_kinds=' | '.join(x[0] for x in links),
                         attachment_count=sum(x[0]!='webpage' for x in links),segment_ids=segment_ids,
                         mapped_segment_count=len(segs),segment_locator=' | '.join(s[2] for s in segs[:3]),
                         segment_version_match=all(s[1] in vids for s in segs),raw_paths=' | '.join(x[2] or '' for x in links),
                         evidence_excerpt=excerpt,header_subtype='',raw_sha256=''))
    finally: db.close()
    return rows


def epa_sample():
    rows=[]
    manifest=read_csv(BRIDGE/'parent_acceptance.csv')
    for month in ('2015-03','2015-04','2015-05','2015-06'):
        docs=[r for r in manifest if r['year_month']==month]
        candidates=[r for r in docs if any(t in (r['canonical_url']+' '+r['header_action']).lower() for t in TERMS)]
        selected=[]
        if candidates: selected.append(('title_candidate',min(candidates,key=lambda r:rank(r['document_id']))))
        controls=[r for r in docs if r not in candidates]
        if controls: selected.append(('control',min(controls,key=lambda r:rank(r['document_id']))))
        exact=[r for r in docs if any(t in r['canonical_url'].lower() for t in ('climate','greenhouse','global-warming','paris'))]
        if exact:
            extra=min(exact,key=lambda r:rank(r['document_id']))
            if all(r['document_id']!=extra['document_id'] for _,r in selected): selected.append(('supplementary_exact_title',extra))
        for stratum,r in selected:
            raw=ROOT/r['raw_path']
            text=raw.read_text(errors='replace') if raw.is_file() else ''
            lines=[x.strip() for x in text.splitlines() if x.strip()]
            hits=[x for x in lines if any(t in x.lower() for t in TERMS)]
            excerpt=' | '.join(clipped(x,220) for x in (hits[:2] or lines[:2]))
            rows.append(dict(role='government',source='US EPA final_rule',month=month,sampling_stratum=stratum,
                candidate_pool=len(candidates),control_pool=len(controls),parent_id=r['document_id'],
                external_id=r['document_number'],title=r['canonical_url'].rstrip('/').split('/')[-1].replace('-',' '),
                publication_date=r['publication_date'],updated_at='',url=r['canonical_url'],body_status=r['body_status'],
                content_type=r['genre'],content_versions=r['committed_content_version_id'],object_kinds='official_raw_text',
                attachment_count=0,segment_ids='',mapped_segment_count=r['cleaned_segments'],segment_locator='see parent_acceptance; source_segments=1',
                segment_version_match=r['source_identity_date_genre_ok']=='1' and r['committed_content_version_id']!='',
                raw_paths=r['raw_path'],evidence_excerpt=excerpt,header_subtype=r['header_subtype'],raw_sha256=r['raw_sha256']))
    return rows


if __name__=='__main__':
    matrix()
    rows=uk_sample()+epa_sample()
    fields=list(rows[0].keys())
    write_csv(OUT/'government_pilot_selected.csv',rows,fields)
    print(json.dumps({'matrix_rows':147,'government_samples':len(rows),'uk_samples':sum(r['source'].startswith('UK') for r in rows),'epa_samples':sum(r['source'].startswith('US') for r in rows)},indent=2))
