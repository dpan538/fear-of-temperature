"""Metadata-only, non-destructive frame revision and collection diagnostics.

No collector imports, database access, HTTP, topic labels or data deletion.
Run from any directory. Frozen evidence remains authoritative for its own scope.
"""
from pathlib import Path
import csv, json, hashlib, collections, statistics
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT.parent
REPO = PACKAGE.parents[2]
NEWS = PACKAGE/'continuations/20261008_global_distribution/worker'
SOCIAL = PACKAGE/'social_public_api'
CAMPUS = {'mit_tech', 'trinity_news', 'beaver', 'mancunion'}
TABLES = ROOT/'tables'

def read(path):
    with path.open(newline='') as f: return list(csv.DictReader(f))

def write(name, rows, fields=None):
    rows=list(rows)
    with (TABLES/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),extrasaction='ignore')
        w.writeheader();w.writerows(rows)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def frame(source): return 'campus_publication' if source in CAMPUS else 'newspaper'

def run(reuse_reconciliation=False):
    TABLES.mkdir(parents=True,exist_ok=True)
    frozen=read(NEWS/'CUMULATIVE_ARTICLE_REGISTER.csv')
    articles=[r for r in frozen if r['disposition']=='confirmed_complete']
    assert len(articles)==12334 and len({r['article_id'] for r in articles})==12334
    ledger=read(NEWS/'coverage/MONTHLY_pooled.csv'); months=[r['month'] for r in ledger]
    assert len(months)==465 and months==sorted(set(months))
    fields=['article_id','analysis_frame','source_id','source','source_url','publication_date','stratum','country','edition','source_frame','genre','work_family_id','version_id','body_sha256','raw_sha256','retrieved_at_utc','content_version_time','provenance','whole_TEXT_characters','historical_body_equivalence','source_native_post_id','retention_limit']
    # One projection, with explicit source-frame labels. Stable identity is untouched.
    write('article_frame_register.csv',({**r,'analysis_frame':frame(r['source_id'])} for r in articles),fields)
    by=collections.defaultdict(list)
    for r in articles: by[r['source_id']].append(r)
    source=[]
    for sid,rs in sorted(by.items()):
        source.append(dict(source_id=sid,title=rs[0]['source'],analysis_frame=frame(sid),native_article_IDs=len(rs),known_work_families=len({r['work_family_id'] or r['article_id'] for r in rs}),first_observed_date=min(r['publication_date'] for r in rs),last_observed_date=max(r['publication_date'] for r in rs),observed_months=len({r['publication_date'][:7] for r in rs}),stratum=rs[0]['stratum'],discourse_role='editorial_or_author_specific_unresolved',classification_basis='Dai 9 October campus-publication reassignment' if sid in CAMPUS else 'Retained evidenced non-student newspaper frame; specialist/advocacy limits remain'))
    write('source_composition.csv',source)
    grouped=collections.defaultdict(list)
    for r in articles:
        for geo in ['pooled',r['stratum']]:grouped[frame(r['source_id']),geo,r['publication_date'][:7]].append(r)
    calendars=[]
    strata=['pooled','EU/Europe excluding UK','UK','AU','US','NZ']
    for f in ['newspaper','campus_publication']:
        for geo in strata:
            for month in months:
                rs=grouped[f,geo,month];works={r['work_family_id'] or r['article_id'] for r in rs}
                calendars.append(dict(month=month,analysis_frame=f,stratum=geo,native_article_IDs=len(rs),known_work_families=len(works),source_titles=len({r['source_id'] for r in rs}),two_work_floor_met=len(works)>=2,additional_required=max(0,2-len(works)),partial_month=month=='2026-09'))
    write('monthly_frame_coverage.csv',calendars)
    current=[r for r in calendars if r['analysis_frame']=='newspaper' and r['stratum']=='pooled']
    write('current_newspaper_gaps.csv',(r for r in current if r['known_work_families']<2))
    # Named gap diagnostics use saved index and conflict metadata only.
    issues=read(TABLES/'green_left_issue_frontier.csv')
    done={r['url'] for r in issues if r['discovery_attempt_recorded']=='True'}
    conflicts=collections.defaultdict(set); examples={}
    for r in read(TABLES/'named_date_conflicts.csv'):
        m=r['native_issue_month'];conflicts[m].add(r['article_id']);examples.setdefault(m,r['source_url'])
    gaps=[]
    for r in ledger:
        if int(r['complete_independent_articles'])>=2:continue
        m=r['month'];ii=[x for x in issues if x['month']==m];n=sum(x['url'] not in done for x in ii)
        if conflicts[m]:
            cause='Verified issue/article date conflict; saved native fields disagree'
            action='Resolve named native issue-to-article mapping against independent dated publisher evidence; retain conflicting bodies without fabricated coverage'
            status='confirmed_mapping_conflict'
        elif n:
            cause='Saved dated native issue frontier contains unprocessed issues; fixed deadline stopped traversal'
            action='Continue the known issue frontier, then retain independently verified whole articles beyond the minimum'
            status='confirmed_unprocessed_frontier_not_promised_yield'
        elif ii:
            cause='Named issue 374/379 saved pages have empty content directories; legacy whole-page parser selected 20 sidebar URLs from 2026 in each. Other issue pages remain untested'
            action='Use repaired content-directory parser with explicit empty state; seek alternate dated native index evidence within source limits, without reassigning sidebar dates'
            status='confirmed_for_one_named_issue_per_month_not_all_issues'
        elif m<'1991-02':
            cause='Historical recovery relied on narrow campus print frame; inherited 36-issue allowance consumed; these titles now belong to campus publications'
            action='Develop eligible non-student historical newspaper parents; campus PDF recovery cannot close the revised newspaper frame'
            status='confirmed_frame_limitation_month_specific_publication_unknown'
        else:
            cause='No issue entry for this month in retained Green Left index frontier; 18 index routes remain, while available non-student frames are incomplete'
            action='Continue permitted native index chronology and general/regional newspaper sources; absence from current frontier is not archive absence'
            status='confirmed_current_frontier_absence_completeness_unknown'
        gaps.append(dict(month=m,frozen_native_IDs=int(r['complete_native_article_IDs']),frozen_known_works=int(r['complete_independent_articles']),additional_required=int(r['additional_articles_required']),evidence_status=status,cause=cause,green_left_known_issues=len(ii),green_left_unprocessed_issues=n,conflicting_article_IDs=len(conflicts[m]),example_source_url=examples.get(m,ii[0]['url'] if ii else ''),next_action=action,newspaper_frame_revision='All 36 remain deficient after campus reassignment; see current_newspaper_gaps.csv for all 203 current gaps'))
    assert len(gaps)==36
    write('frozen_36_gap_diagnosis.csv',gaps)
    frontier=read(NEWS/'SOURCE_FRONTIER_REGISTER.csv')
    for r in frontier:
        r['analysis_frame']=frame(r['source_id'])
        r['interpretation']=''
        if r['frontier_state']=='exhausted':r['interpretation']='Metadata pagination ended; queued body acquisition remains open'
        elif r['source_id']=='montpelier_bridge':r['interpretation']='US discovery counter reached 1000; queued body targets remain separately available'
        elif r['source_id']=='indaily':r['interpretation']='All current queued targets touched; retained-opportunities label is not evidence of a usable next route; asset-host stop remains'
        elif r['source_id'] in CAMPUS:r['interpretation']='Retain as campus_publication; no future newspaper coverage credit'
        else:r['interpretation']='Source state and actual access stops both apply; unattempted targets are not verified eligible yield'
    write('source_frontier_interpretation.csv',frontier)
    # Transparent flags only. Missing bins are not manufactured future observations.
    # Default screen: >=20 IDs and >=3x every observed adjacent-month count.
    # It is an exploratory workload flag, never an ingestion/inclusion decision.
    peak=[]
    series={'newspaper:pooled':[r['native_article_IDs'] for r in current]}
    for sid,rs in by.items():
        c=collections.Counter(r['publication_date'][:7] for r in rs)
        series[frame(sid)+':'+sid]=[c[m] for m in months]
    for key,values in series.items():
        for i,(m,v) in enumerate(zip(months,values)):
            prev=values[max(0,i-3):i];following=values[i+1:i+4];neighbors=prev+following
            complete=len(prev)==len(following)==3
            high=v>=20 and v>=3*max(1,max(neighbors,default=0))
            peak.append(dict(series=key,month=m,native_IDs=v,preceding_months=len(prev),following_months=len(following),preceding_sum=sum(prev),following_sum=sum(following),neighbor_max=max(neighbors,default=0),neighbor_median=statistics.median(neighbors),ratio_to_max_or_one=round(v/max(1,max(neighbors,default=0)),4),full_six_month_context=complete,context_includes_partial_cutoff_month='2026-09' in months[max(0,i-3):i]+months[i+1:i+4],isolated_high_screen=high,action='retain_and_flag' if high else 'retain',interpretation='Observed acquisition count; no event or population claim'))
    write('adjacent_month_diagnostics.csv',peak)
    write('flagged_months.csv',(r for r in peak if r['isolated_high_screen']),list(peak[0]))
    # Peak attribution: all largest pooled months, with source mix and date limits.
    largest=sorted(current,key=lambda r:r['native_article_IDs'],reverse=True)[:12]
    attribution=[]
    for r in largest:
        m=r['month'];mix=collections.Counter(x['source_id'] for x in articles if frame(x['source_id'])=='newspaper' and x['publication_date'][:7]==m)
        attribution.append(dict(month=m,native_IDs=r['native_article_IDs'],known_work_families=r['known_work_families'],source_mix=json.dumps(dict(mix),sort_keys=True),status='retained; source/frame/cursor selection remains a competing explanation; event attribution untested'))
    write('largest_newspaper_months.csv',attribution)
    # Final metadata hashes only; no database/raw/body reads.
    selected=['DELIVERY_REPORT.md','DELIVERY_SUMMARY.json','CUMULATIVE_ARTICLE_REGISTER.csv','SOURCE_FRONTIER_REGISTER.csv','SOURCE_PARENT_IDENTITY_REGISTER.csv','MONTH_SOURCE_PARENT_DISTRIBUTION.csv','MONTH_SOURCE_GENRE_DISTRIBUTION.csv','ARTICLE_URL_ALIAS_REGISTER.csv','ARTICLE_VERSION_REGISTER.csv','EXACT_BODY_OVERLAP_REVIEW_REGISTER.csv','PROVENANCE_AND_VERIFICATION_REGISTER.csv','NEW_PENDING_OR_COMPONENT_REGISTER.csv','RETAINED_DISPOSITION_REGISTER.csv','HOST_STOP_REGISTER.csv']
    receipts={} if reuse_reconciliation else json.loads((NEWS/'DELIVERY_FILE_RECEIPTS.json').read_text())['files'];verified=[]
    if reuse_reconciliation:
        verified=json.loads((ROOT/'review_manifest.json').read_text())['verified_metadata_files']
        selected=[]
    for ref in ([] if reuse_reconciliation else selected+['coverage/'+p.name for p in sorted((NEWS/'coverage').glob('MONTHLY_*.csv'))]):
        f=NEWS/ref;e=receipts[ref];assert digest(f)==e['sha256'] and f.stat().st_size==e['bytes'],ref
        verified.append(dict(path=str(f.relative_to(REPO)),sha256=e['sha256'],bytes=e['bytes']))
    sm=json.loads((SOCIAL/'summaries/collection_manifest.json').read_text())
    for ref,e in ({} if reuse_reconciliation else sm['outputs']|sm['implementation']).items():
        f=SOCIAL/ref;assert digest(f)==e['sha256'] and f.stat().st_size==e['bytes'],ref
        verified.append(dict(path=str(f.relative_to(REPO)),sha256=e['sha256'],bytes=e['bytes']))
    summary=dict(fixed_publication_interval=['1988-01-01','2026-09-21'],frozen_native_articles=12334,frozen_floor_months=429,frozen_deficient_months=36,current_newspaper_IDs=sum(len(rs) for sid,rs in by.items() if sid not in CAMPUS),campus_publication_IDs=sum(len(rs) for sid,rs in by.items() if sid in CAMPUS),current_newspaper_floor_months=sum(r['known_work_families']>=2 for r in current),current_newspaper_one_months=sum(r['known_work_families']==1 for r in current),current_newspaper_zero_months=sum(r['known_work_families']==0 for r in current),social_native_posts=sm['native_posts'],social_months=sm['observed_pooled_months'],source_and_frame_counts=source,isolated_high_flags=sum(r['isolated_high_screen'] for r in peak),all_articles_preserved=True,stores_changed=False,full_body_or_raw_sweep=False,accepted_collector_checks_reused=True,metadata_hash_reconciliation_passed=True,verified_metadata_files=verified)
    (ROOT/'review_manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if not isinstance(v,list)},indent=2))

if __name__=='__main__':
    import sys
    run(reuse_reconciliation='--reuse-reconciliation' in sys.argv)
