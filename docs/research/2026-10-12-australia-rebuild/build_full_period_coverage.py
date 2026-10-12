"""465-month coverage inventory; presence and readiness are distinct states."""
from pathlib import Path
from collections import defaultdict
import csv, json

HERE=Path(__file__).resolve().parent

def months():
    y,m=1988,1
    while (y,m)<=(2026,9):
        yield f'{y:04d}-{m:02d}'
        y,m=(y+1,1) if m==12 else (y,m+1)

def main():
    stock=json.loads((HERE.parent/'2026-10-12-australia-source-freeze/NEWS_PUBLIC_METADATA_SUMMARY.json').read_text())
    counts={k:defaultdict(int) for k in ['newspaper','public_community']}
    sourcecounts={k:defaultdict(int) for k in counts}
    for stream in counts:
        for s in stock[stream]['by_source']:
            for month,n in s['source_month_counts']:
                counts[stream][month]+=n
                if n:sourcecounts[stream][month]+=1
    sessions=defaultdict(int)
    with (HERE/'government_session_month_counts.csv').open() as f:
        for r in csv.DictReader(f):sessions[r['month']]+=int(r['sittings'])
    pm_examples=defaultdict(int)
    gov=json.loads((HERE/'government_evidence.json').read_text())
    # Examples verify a route, not a PM inventory. Do not borrow an example total.
    for date in ['1988-08-07','2024-09-06','2025-06-04','2026-09-21']:
        pm_examples[date[:7]]+=1
    rows=[]
    for mo in months():
        news=counts['newspaper'][mo];public=counts['public_community'][mo]
        rows.append({'month':mo,'publication_boundary':'partial through2026-09-21; narrower observations retained' if mo=='2026-09' else 'full calendar month',
            'newspaper_saved_complete_article_candidates':news,'newspaper_contributing_source_ids':sourcecounts['newspaper'][mo],
            'media_presence':'candidate_stock_present; admission and source-frame review pending' if news else 'no_saved_candidate; full-period media gap',
            'community_saved_dated_independent_body_candidates':public,'community_contributing_source_ids':sourcecounts['public_community'][mo],
            'public_civic_presence':'community_candidate_stock_present; historical/civic genre coverage separate' if public else 'no_saved_community_candidate; historical public/civic channels unresolved',
            'RAPID_sitting_metadata_rows':sessions[mo],'PM_confirmed_named_examples':pm_examples[mo],
            'institutional_presence':'parliamentary_sitting_metadata_present; original-unit/dated-role admission pending' if sessions[mo] else 'no_RAPID_sitting_metadata; executive/historical channel and official calendar unresolved',
            'government_utterance_inventory':'unknown; sitting/example count is not a government-body denominator',
            'media_new_admitted_units':0,'public_civic_new_admitted_units':0,'government_new_admitted_units':0,
            'all_three_ready_coverage':'not_established',
            'whole_public_role_applicability':'public expression existed before modern platforms; historical source/genre evidence needed',
            'complete_archive_recovery':'unknown','topic_affect_fear_state':'not_run; never structural coverage gates'})
    with (HERE/'full_period_coverage_months.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    def ranges(missing):
        output=[]
        for mo in missing:
            if output:
                y,m=map(int,output[-1]['end'].split('-'));nextmo=f'{y+1:04d}-01' if m==12 else f'{y:04d}-{m+1:02d}'
            else:nextmo=None
            if nextmo==mo:output[-1]['end']=mo;output[-1]['months']+=1
            else:output.append({'start':mo,'end':mo,'months':1})
        return output
    summary={'version':'AU-full-period-coverage-v3','steering':'Dai prioritises dated government climate explanations/warnings to justify minimum analytical windows, while maintaining full-period pooled coverage and role gaps for long-run distribution/RQ1/RQ2. Avoid forced calendar filling; recent subset is verification only.',
        'fixed_interval':['1988-01-01','2026-09-21'],'calendar_months':465,'new_active_imports':0,
        'coverage_contract_status':'Dai confirms pooled overall monthly full-period coverage with separate three-role gaps. Latest priority: first map dated government climate explanations/warnings to choose supported minimum analytical windows; full-calendar coverage/distribution remain long-run RQ1/RQ2 requirements, without forced acquisition or an automatic completeness claim.',
        'newspaper':{'saved_candidate_articles':8169,'observed_months':sum(counts['newspaper'][m]>0 for m in months()),'no_saved_candidate_months':sum(counts['newspaper'][m]==0 for m in months()),'no_saved_candidate_ranges':ranges([m for m in months() if counts['newspaper'][m]==0])},
        'public_community':{'saved_candidate_bodies':45679,'observed_months':sum(counts['public_community'][m]>0 for m in months()),'no_saved_candidate_months':sum(counts['public_community'][m]==0 for m in months()),'no_saved_candidate_ranges':ranges([m for m in months() if counts['public_community'][m]==0])},
        'parliament_metadata':{'sittings':sum(sessions.values()),'observed_months':sum(sessions[m]>0 for m in months()),'no_sitting_row_months':sum(sessions[m]==0 for m in months()),'no_sitting_row_ranges':ranges([m for m in months() if sessions[m]==0]),'not_government_text_coverage':True},
        'all_three_source_presence_proxy_months':sum(counts['newspaper'][m]>0 and counts['public_community'][m]>0 and sessions[m]>0 for m in months()),
        'pooled_source_presence_proxy_months':sum(counts['newspaper'][m]>0 or counts['public_community'][m]>0 or sessions[m]>0 for m in months()),
        'pooled_proxy_without_presence_ranges':ranges([m for m in months() if not (counts['newspaper'][m]>0 or counts['public_community'][m]>0 or sessions[m]>0)]),
        'proxy_warning':'Pooled proxy includes sitting metadata, not a verified original-text union. It does not certify complete coverage; original-unit admission remains pending.',
        'all_three_ready_or_complete_months':0,'complete_study_claim_supported':False,
        'no_new_rule':['No coverage>=2 completion revival','No fixed article/post/passages count or source quotas','No climate/fear/affect gate','No old data deletion or downsampling','No automatic collector or expired lease'],
        'next_work':'Build government dated climate-expression candidate/validated inventory, preserving uninspected/missing/zero distinctions, then justify minimum analytical windows. Maintain full465month source/genre/role distribution and lawful route gap plan; historical public genres remain distinct. No semantic deletion or forced month-filling.'}
    assert len(rows)==465 and summary['newspaper']['observed_months']==220 and summary['public_community']['observed_months']==50
    (HERE/'FULL_PERIOD_COVERAGE.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['newspaper','public_community','parliament_metadata']},indent=2))

if __name__=='__main__':main()
