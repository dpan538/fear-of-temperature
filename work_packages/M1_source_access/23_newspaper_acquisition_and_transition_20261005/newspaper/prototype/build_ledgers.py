"""Create the fixed calendar plan from own-package evidence; no collection/network."""
import collections,csv,datetime as dt,fcntl,hashlib,json,sqlite3
from pathlib import Path
import transport

def write_csv(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)

def plan_title(stratum,month):
    if stratum=='EU/Europe excluding UK':return 'times_of_malta'
    if stratum=='UK':return 'beaver' if month<='2011-12' else 'varsity'
    if stratum=='AU':return 'canberra_times' if month<='1995-12' else 'alice_springs_news' if month<'2011-03' else 'indaily'
    if stratum=='US':return 'mit_tech'
    if month<='1995-12':return 'the_press'
    if month<='1999-12' or month[:4]=='2001':return 'ruapehu_bulletin'
    return 'otago_daily_times'

def main():
    own=transport.OWN;registry=json.loads((own/'sources/SOURCE_REGISTRY_EFFECTIVE.json').read_text())
    sources=registry['sources'];byid={s['title_id']:s for s in sources}
    observations=json.loads((own/'sources/PROBE_OBSERVATIONS.json').read_text())['probes']
    obs=collections.defaultdict(list)
    for row in observations:obs[row['stratum'],row['month']].append(row['evidence_id'])
    out=own/'coverage';out.mkdir(exist_ok=True)
    months=[f'{y}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y}-{m:02d}'<='2026-09']
    assert len(months)==465
    with transport.HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        con=sqlite3.connect(f'file:{own}/staging/newspaper.sqlite3?mode=ro',uri=True)
        retained=dict(((s,m),n) for s,m,n in con.execute("SELECT a.stratum,substr(a.publication_date,1,7),count(DISTINCT a.article_id) FROM articles a JOIN versions v USING(article_id) WHERE a.lane='newspaper' AND a.newspaper_eligible=1 AND v.qualified_readable=1 GROUP BY a.stratum,substr(a.publication_date,1,7)"))
        parents=[dict(zip([x[0] for x in con.execute('SELECT * FROM articles').description],row)) for row in con.execute('SELECT * FROM articles')]
        versions=[dict(zip([x[0] for x in con.execute('SELECT * FROM versions').description],row)) for row in con.execute('SELECT * FROM versions')]
        con.close()
    rows=[];pooled=[]
    for month in months:
        for stratum in transport.SCOPE['strata']:
            title=plan_title(stratum,month);n=retained.get((stratum,month),0)
            rows.append(dict(stratum=stratum,month=month,period_end='2026-09-21' if month=='2026-09' else '',
                partial_month=month=='2026-09',planned_presence_effort=1,planned_candidate_title=title,
                source_assignment_status='provisional route plan; no discovered article selection',
                candidate_access_limit=byid[title]['access_state'],frame_frozen=False,frame_complete=False,
                qualified_retained_article_count=n,underlying_publication_count='',eligible_frame_population='',
                inclusion_probability='',population_state='unknown; not observed zero',
                observation_state='metadata_only' if obs[stratum,month] else 'unassessed',
                metadata_evidence_ids='|'.join(obs[stratum,month]),
                collection_state='storage_blocked_before_local_enumeration',
                regional_structural_inapplicability='not established',verified_empty_frame=False,
                failed_target_replacement='none',quota_transferred=False))
        ns=[retained.get((s,month),0) for s in transport.SCOPE['strata']]
        pooled.append(dict(month=month,planned_presence_effort=5,qualified_retained_article_count=sum(ns),
            strata_with_qualified_presence=sum(n>0 for n in ns),underlying_publication_count='',
            eligible_frame_population='',population_state='unknown; not observed zero',
            metadata_only_strata='|'.join(s for s in transport.SCOPE['strata'] if obs[s,month]),
            calendar_presence_established=False,complete_population_verified=False,partial_month=month=='2026-09'))
    assert len(rows)==2325 and len(set((r['stratum'],r['month']) for r in rows))==2325
    assert all(sum(r['planned_presence_effort'] for r in rows if r['stratum']==s)==465 for s in transport.SCOPE['strata'])
    write_csv(out/'REGIONAL_MONTH_LEDGER.csv',rows);write_csv(out/'POOLED_MONTH_LEDGER.csv',pooled)
    (out/'LEDGER_SCHEMA.json').write_text(json.dumps({'generated_at_utc':transport.utc(),
        'publication_interval':['1988-01-01','2026-09-21'],'month_count':465,'regional_coordinates':2325,
        'count_semantics':'qualified_retained_article_count=actual owner staging newspaper lane; zero means acquired zero, not publication absence',
        'csv_blank_numeric_fields':'unknown/null, never zero; underlying publication and frame populations have not been audited',
        'planned_candidate_title':'conditional future route assignment, not a frozen selected article or automatic replacement rule',
        'metadata_only':'dated calendar/issue/article-link observations; no retained readable newspaper prose',
        'title_era_gap':'a route may be outside its documented era; this is not regional publication inapplicability',
        'selection':'freeze native/date-ordered discovered article frame before bodies; preserve failed targets',
        'source_registry_sha256':transport.sha(own/'sources/SOURCE_REGISTRY_EFFECTIVE.json'),
        'qualified_newspaper_articles':sum(retained.values()),'framework_generator_sha256':transport.sha(__file__)},indent=2)+'\n')
    manifests=own/'manifests';manifests.mkdir(exist_ok=True)
    for name,value in [('ARTICLE_MANIFEST.json',parents),('VERSION_MANIFEST.json',versions)]:
        (manifests/name).write_text(json.dumps({'scope':'own staging only; diagnostic lanes excluded from newspaper coverage','records':value},indent=2)+'\n')
    requests=[json.loads(p.read_text()) for p in sorted((own/'requests').glob('*.json'))]
    payloads=[r for r in requests if r['purpose'] in {'article','index'}]
    frames=[{'path':str(p.relative_to(own)),'sha256':transport.sha(p)} for p in sorted((own/'frames').glob('*.json'))]
    (manifests/'NEWSPAPER_RAW_AND_REQUEST_MANIFEST.json').write_text(json.dumps({'newspaper_network_payload_requests':sum(r.get('charged_attempts',len(r.get('hops',[]))) for r in payloads),
        'newspaper_payload_receipts':payloads,
        'newspaper_raw_objects':[{'request_id':r['request_id'],'source_id':r['source_id'],'path':r['raw_path'],'sha256':r['raw_sha256'],'partial':r['partial']} for r in payloads if r.get('raw_path')],
        'newspaper_frozen_article_frames':frames,
        'stop':'Current status must be read with FINAL_STORAGE_CHECK and CONTINUATION_CURSOR; no publication-absence claim.',
        'source_preparation_requests':'../sources/DISCOVERY_REQUESTS.jsonl and POLICY_REQUESTS.jsonl',
        'real_saved_diagnostic_raw':'external frozen round22 object reference, not recopied'},indent=2)+'\n')
    print(json.dumps({'regional_rows':len(rows),'pooled_rows':len(pooled),'metadata_only_regional_cells':sum(r['observation_state']=='metadata_only' for r in rows),'actual_newspaper_articles':sum(retained.values()),'diagnostic_parents':len(parents),'diagnostic_versions':len(versions)}))

if __name__=='__main__':main()
