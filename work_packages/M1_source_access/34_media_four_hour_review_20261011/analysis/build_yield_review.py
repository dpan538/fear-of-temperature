"""Compare closed rounds from finalized manifests, without opening source stores."""
from pathlib import Path
import csv, hashlib, json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
PREVIOUS = ROOT/'work_packages/M1_source_access/33_media_eight_hour_review_20261011/closed'
CURRENT = BASE.parent/'closed'

def load(path):
    data = path.read_bytes()
    receipts.append({'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(data).hexdigest()})
    return json.loads(data)

receipts = []
rows = []
for label, hours in [('broader_history',4), ('eight_hour',8), ('four_hour',4)]:
    newspaper = load((CURRENT/'newspaper' if label=='four_hour' else PREVIOUS/label/'newspaper')/'DELIVERY_SUMMARY.json')
    social = [load(CURRENT/f'social/{phase}/summaries/collection_manifest.json') for phase in ['A','B']] if label=='four_hour' else [load(PREVIOUS/label/'social/collection_manifest.json')]
    for stream in ['newspaper','social']:
        count = newspaper['additional_regular_newspaper_IDs'] if stream=='newspaper' and label=='four_hour' else newspaper['additional_qualified_IDs'] if stream=='newspaper' else sum(d['new_usable_dated_bodies'] for d in social)
        requests = newspaper['new_recorded_HTTP_request_attempts'] if stream=='newspaper' else sum(d['round_charged_requests'] for d in social)
        rows.append({'round':label, 'stream':stream, 'authorized_hours':hours,
          'new_comparable_units':count, 'new_separate_supplement_articles':34 if label=='four_hour' and stream=='newspaper' else 0,
          'recorded_request_attempts':requests, 'units_per_authorized_hour':count/hours, 'units_per_recorded_request':count/requests,
          'rate_denominator':'authorized hours, including preparation and capacity-stopped time; not measured active worker throughput'})
with (BASE/'ROUND_YIELD_COMPARISON.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
result={'rounds':rows,'input_receipts':receipts,
 'four_vs_eight_hour_rate_change':{s:next(r['units_per_authorized_hour'] for r in rows if r['stream']==s and r['round']=='four_hour')/next(r['units_per_authorized_hour'] for r in rows if r['stream']==s and r['round']=='eight_hour')-1 for s in ['newspaper','social']},
 'interpretation_limits':['Different source/era/native transport mixtures are not interchangeable quantities.',
   'Authorized-hour rates are realized window yields, not active CPU or HTTP throughput.',
   'The earlier large technical-list addition does not establish broad public-community coverage.',
   'No expected natural distribution, archive denominator or causal throughput attribution is inferred.']}
(BASE/'YIELD_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['four_vs_eight_hour_rate_change']))
