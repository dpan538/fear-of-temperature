"""Build a bounded next tranche from the saved native catalog and live capacity."""
import argparse
import datetime as dt
import json
import math
import re
import urllib.parse
from bs4 import BeautifulSoup
import collect_first_batch as resources

ROOT=resources.ROOT
args=argparse.ArgumentParser();args.add_argument('--round',type=int,required=True);a=args.parse_args()
receipts=[json.loads(s) for s in (ROOT/'REQUESTS.jsonl').read_text().splitlines() if s]
budget=resources.preflight()
available=max(0,min(budget['free_bytes']-resources.FLOOR-resources.OVERHEAD,
                    resources.LIFETIME_CAP-budget['media_lifetime_used_bytes']))
sizes=sorted(r['raw_bytes'] for r in receipts if r['purpose']=='article' and r['status']=='saved')
p90=sizes[min(len(sizes)-1,math.floor(len(sizes)*.9))] if sizes else 65536
estimated_index_cost=65536+40*max(65536,4*p90)
index_limit=min(12,available//estimated_index_cost)
catalog=next(r for r in receipts if r['url']=='https://thetech.com/issues' and r['status']=='saved')
soup=BeautifulSoup((ROOT/catalog['raw_path']).read_bytes(),'html.parser')
observed=[]
for node in soup.select('a.issue[href]'):
    m=re.fullmatch(r'/issues/(\d+)/(\d+)',node['href'])
    if m and 127<=int(m[1])<=146:
        observed.append((int(m[1]),int(m[2]),'https://thetech.com'+node['href']))
visited={r['url'] for r in receipts if r['purpose']=='index'}
selected=[['auto',u] for v,n,u in sorted(observed) if u not in visited][:index_limit]
payloads=[]
if not selected:
    attempted={r['url'] for r in receipts if r['purpose']=='article'}
    payload_limit=min(40,available//max(65536,4*p90))
    for index in [r for r in receipts if r['purpose']=='index' and r['status']=='saved']:
        index_soup=BeautifulSoup((ROOT/index['raw_path']).read_bytes(),'html.parser')
        for node in index_soup.select('a[href]'):
            url=urllib.parse.urljoin(index['url'],node['href']).split('#')[0]
            match=re.fullmatch(r'https://thetech.com/(\d{4})/(\d{2})/(\d{2})/[^/]+',url)
            if not match or url in attempted:continue
            day='-'.join(match.groups())
            if not '1988-01-01'<=day<='2026-09-21':continue
            attempted.add(url)
            payloads.append(dict(url=url,purpose='article',parent_index_receipt=index['request_id'],url_date=day))
            if len(payloads)>=payload_limit:break
        if len(payloads)>=payload_limit:break
    if not payload_limit:payloads=[]
stamp=dt.datetime.now(dt.timezone.utc).isoformat()
scope=dict(round_id=f'successor_round_{a.round:02d}',authorized_by='Dai explicitly authorizes consecutive real collection rounds with dynamic capacity',recorded_at_utc=stamp,
    prior_rounds_preserved=True,prior_metadata_total=18+sum(r['purpose']=='index' for r in receipts),
    new_metadata_allowance=len(selected),per_batch_metadata_cap=12,raw_lifetime_ceiling_bytes=resources.LIFETIME_CAP,
    free_floor_bytes=resources.FLOOR,publication_interval=['1988-01-01','2026-09-21'],
    selection='Next unattempted catalog issue in chronological volume/issue order; first 40 native dated article URLs, no semantic selection',
    dynamic_task_sizing=dict(live_available_bytes=available,observed_raw_p90_bytes=p90,estimated_cost_per_index=estimated_index_cost,index_count=index_limit),
    no_new_source_titles_or_platforms=True)
plan=dict(batch_id=f'round{a.round:02d}_native',round_id=scope['round_id'],indexes=selected,articles_per_index=40,payloads=payloads)
scope_path=ROOT/f'ROUND{a.round:02d}_SCOPE.json';plan_path=ROOT/f'ROUND{a.round:02d}_PLAN.json'
if scope_path.exists() or plan_path.exists():raise RuntimeError('Preserve existing round plans; choose a fresh round id')
scope_path.write_text(json.dumps(scope,indent=2)+'\n');plan_path.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(dict(scope=str(scope_path),plan=str(plan_path),indexes=len(selected),direct_native_payloads=len(payloads),live_budget=budget,
    state='ready for actual acquisition' if selected or payloads else 'no new bounded payload fits measured capacity or unattempted native frame')))
