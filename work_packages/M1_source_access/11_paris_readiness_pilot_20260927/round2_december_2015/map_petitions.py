"""Published/opened main frame versus all-submitted/created sensitivity."""
import csv
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent

def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

frame=read(PARENT/'public_climate_query_frame.csv')
review={r['petition_id']:r for r in read(PARENT/'public_pilot_review.csv')}
assert len(frame)==177 and len({r['petition_id'] for r in frame})==177
mapped=[]
for r in frame:
    pub=bool(r['opened_at']) and r['state']!='rejected'
    t=review.get(r['petition_id'],{})
    mapped.append(dict(petition_id=r['petition_id'],parent_url=r['parent_url'],state=r['state'],
                       created_at=r['created_at'],created_month_utc=r['created_at'][:7],
                       opened_at=r['opened_at'],opened_month_utc=r['opened_at'][:7],
                       rejected_at=r['rejected_at'],published_only_eligible=int(pub),
                       all_submitted_eligible=1,petitioner_body_present=int(bool(r['background'] or r['additional_details'])),
                       pilot_reviewed=int(bool(t)),climate_warming_topic=t.get('climate_warming_topic',''),
                       anticipated_climate_harm_cue=t.get('anticipated_climate_harm_cue',''),
                       explicit_fear_expression=t.get('explicit_fear_expression',''),
                       source_json_url=r['source_json_url']))
write(HERE/'petition_177_id_date_mapping.csv',mapped,list(mapped[0]))

months=('2015-11','2015-12','2016-01')
summary=[]
for m in months:
    submitted=[r for r in mapped if r['created_month_utc']==m]
    published_created=[r for r in submitted if r['published_only_eligible']==1]
    published_opened=[r for r in mapped if r['opened_month_utc']==m and r['published_only_eligible']==1]
    rejected=[r for r in submitted if r['state']=='rejected']
    lag_in=[r for r in published_opened if r['created_month_utc']!=m]
    summary.append(dict(month_utc=m,query_frame='2015-2017 archive parliament=1&q=climate; 177 distinct IDs',
                        all_submitted_by_created_at=len(submitted),published_subset_by_created_at=len(published_created),
                        rejected_by_created_at=len(rejected),published_only_by_opened_at=len(published_opened),
                        opened_this_month_created_elsewhere=len(lag_in),lag_in_ids=' | '.join(r['petition_id'] for r in lag_in),
                        published_body_present=sum(r['petitioner_body_present'] for r in published_opened),
                        published_pilot_reviewed=sum(r['pilot_reviewed'] for r in published_opened),
                        published_pilot_climate_topic=sum(int(r['climate_warming_topic']) for r in published_opened if r['climate_warming_topic']!=''),
                        published_pilot_anticipated_harm=sum(int(r['anticipated_climate_harm_cue']) for r in published_opened if r['anticipated_climate_harm_cue']!=''),
                        published_pilot_explicit_fear=sum(int(r['explicit_fear_expression']) for r in published_opened if r['explicit_fear_expression']!=''),
                        monthly_all_eligible_petition_denominator='unverified',
                        zero_qualifier='zero only within q=climate query' if not published_opened else ''))
write(HERE/'petition_nov2015_jan2016_month_mapping.csv',summary,list(summary[0]))
print('all frame',len(mapped),'published',sum(r['published_only_eligible'] for r in mapped),'rejected',sum(r['state']=='rejected' for r in mapped))
for r in summary:print(r['month_utc'],'created all',r['all_submitted_by_created_at'],'opened published',r['published_only_by_opened_at'],'lag IDs',r['lag_in_ids'])
