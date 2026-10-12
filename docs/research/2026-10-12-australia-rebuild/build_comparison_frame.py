"""Reproduce source/month stock and sitting diagnostics without opening stores."""
from pathlib import Path
import csv, json, hashlib
from collections import defaultdict

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def months(start,end):
    y,m=map(int,start.split('-'))
    while f'{y:04d}-{m:02d}'<=end:
        yield f'{y:04d}-{m:02d}'
        y,m=(y+1,1) if m==12 else (y,m+1)

def main():
    path=HERE.parent/'2026-10-12-australia-source-freeze/NEWS_PUBLIC_METADATA_SUMMARY.json'
    data=json.loads(path.read_text())
    rows=[]; totals={}
    for stream,unit in [('newspaper','complete_article_ID'),('public_community','dated_independently_authored_native_body')]:
        for s in data[stream]['by_source']:
            counts=dict(s['source_month_counts']);totals[s['source_id']]=s['count']
            assert sum(counts.values())==s['count']
            for month in months('1988-01','2026-09'):
                n=counts.get(month,0)
                rows.append({'source_id':s['source_id'],'source_context':'AU publisher' if stream=='newspaper' else 'evidenced AU community context',
                             'stream':stream,'unit':unit,'month':month,'saved_candidate_count':n,'new_active_import_count':0,
                             'presence_state':'observed_saved_candidate' if n else 'no_saved_candidate_presence',
                             'source_existence_applicability':'unresolved_per_month; first observation is not foundation date',
                             'archive_inventory_denominator':'unknown','boundary':'partial through2026-09-21; narrower source observations apply' if month=='2026-09' else 'full calendar month; archive completeness unknown'})
    output=HERE/'media_community_source_month.csv'
    with output.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    recent=list(months('2024-06','2026-08')); report=[]
    for sid in totals:
        current=[r for r in rows if r['source_id']==sid and r['month'] in recent]
        report.append({'source_id':sid,'count':sum(r['saved_candidate_count'] for r in current),'observed_months':sum(r['saved_candidate_count']>0 for r in current),'calendar_months':27})
    session_path=HERE/'government_session_month_counts.csv'
    sitting={}
    if session_path.exists():
        with session_path.open() as f:
            sr=list(csv.DictReader(f))
        # Aggregate chamber rows to retain sittings rather than speeches/paragraphs.
        for r in sr:
            mo=r.get('month',r.get('publication_month'))
            n=r.get('sittings',r.get('sitting_count',r.get('session_count',r.get('count'))))
            if n is None:raise ValueError(f'Unknown sitting-count column: {list(r)}')
            sitting[mo]=sitting.get(mo,0)+int(n)
    comparison=[]
    for mo in months('2024-06','2026-09'):
        counts={sid:next(r['saved_candidate_count'] for r in rows if r['source_id']==sid and r['month']==mo) for sid in ['northern_rivers_times','mastodon_au','aussie_zone']}
        comparison.append({'month':mo,'newspaper_article_stock':counts['northern_rivers_times'],'AusSocial_body_stock':counts['mastodon_au'],'AussieZone_body_stock':counts['aussie_zone'],
                           'RAPID_sittings':sitting.get(mo) if sitting else None,'government_executive_utterance_count':None,
                           'parliament_text_admission':'pending paragraph/procedural/speaker-role joins; sitting presence only',
                           'boundary':'partial; Parliament last observed2026-09-08' if mo=='2026-09' else 'full calendar month; saved inventories not population denominators'})
    with (HERE/'recent_comparison_months.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    result={'version':'AU-rebuild-confirmation-v3','new_active_import_count':0,'fixed_publication_interval':['1988-01-01','2026-09-21'],
            'bounded_verification_window':['2024-06','2026-08'],'priority_minimum_analysis_window':'not frozen; derive from dated validated government climate explanations/warnings and source comparability',
            'full_period_contract':'pooled overall monthly coverage with separate role gaps; retain full465month distribution/coverage long term, avoid forced month-filling',
            'partial_boundary':'2026-09 through fixed21September, source-specific narrower observation',
            'source_month_rows':len(rows),'total_stock_by_source':totals,'recent_full_month_sources':report,
            'RAPID_recent_sittings':sum(sitting.get(mo,0) for mo in recent) if sitting else None,
            'RAPID_recent_sitting_presence_months':sum(sitting.get(mo,0)>0 for mo in recent) if sitting else None,
            'RAPID_recent_months_without_saved_sitting':[mo for mo in recent if sitting.get(mo,0)==0] if sitting else None,
            'interpretation':'Counts are independent within native unit only. Sittings do not certify paragraphs/speeches or executive government expression. A no-row parliament month needs an official sitting-calendar check; it is not zero emotion or a proven download gap.',
            'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [path]+([session_path] if session_path.exists() else [])]}
    (HERE/'COMPARISON_FRAME.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
