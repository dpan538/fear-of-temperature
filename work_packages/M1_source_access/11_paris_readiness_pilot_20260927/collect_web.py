"""Bounded read-only feasibility capture; never writes formal corpus databases."""
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

OUT=Path(__file__).resolve().parent
SEED='paris-readiness-20260927-v1'
HEAD={'User-Agent':'FearTemperatureResearch/0.1 (academic source feasibility; contact via project owner)'}
S=requests.Session();S.headers.update(HEAD)
DATES=('2015/nov/30','2015/dec/13','2016/jan/17')
BASE='https://petition.parliament.uk/archived/petitions.json'
PARAMS={'parliament':'1','q':'climate'}

def get(url,params=None):
    r=S.get(url,params=params,timeout=25)
    r.raise_for_status()
    return r

def sha(data):return hashlib.sha256(data).hexdigest()
def rank(s):return sha((SEED+'|'+s).encode())
def clean(s):return re.sub(r'\s+',' ',s or '').strip()
def write_csv(name,rows,fields):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def media():
    frame=[];samples=[];days=[]
    for day in DATES:
        iso_day=datetime.strptime(day,'%Y/%b/%d').date().isoformat()
        url=f'https://www.theguardian.com/environment/{day}/all'
        r=get(url); soup=BeautifulSoup(r.text,'html.parser')
        cards={}
        for h in soup.select('h3.fc-item__title'):
            a=h.find('a',href=True)
            if not a:continue
            link=a['href'].split('?')[0]
            if 'theguardian.com/' not in link or '/video/' in urlparse(link).path:continue
            cards[link]=clean(h.get_text(' ',strip=True))
        for link,title in sorted(cards.items()):
            frame.append(dict(archive_day=iso_day,url=link,title=title,archive_url=url,archive_sha256=sha(r.content),unit='unique_nonvideo_title_card'))
        days.append((day,len(cards)))
        if not cards:continue
        chosen=[('hash_control',min(cards,key=rank))]
        exact=[link for link,title in cards.items() if any(t in title.lower() for t in ('climate','greenhouse','global warming','paris'))]
        if exact:
            extra=min(exact,key=rank)
            if extra!=chosen[0][1]:chosen.append(('supplementary_exact_title',extra))
        for stratum,link in chosen:
            a=get(link); page=BeautifulSoup(a.text,'html.parser')
            def meta(prop):
                e=page.find('meta',attrs={'property':prop});return e.get('content','') if e else ''
            body=page.select_one('[data-gu-name="body"]')
            paragraphs=[clean(x.get_text(' ',strip=True)) for x in body.find_all('p')] if body else []
            samples.append(dict(role='media',sampling_stratum=stratum,parent_url=link,title=meta('og:title') or cards[link],
                original_published_at=meta('article:published_time'),current_modified_at=meta('article:modified_time'),
                archive_day=iso_day,archive_day_frame_count=len(cards),body_present=bool(body and clean(body.get_text(' ',strip=True))),
                body_paragraph_count=len(paragraphs),body_characters=sum(len(x) for x in paragraphs),
                body_evidence_excerpt=' | '.join(x[:95] for x in paragraphs[:2]),
                response_sha256=sha(a.content),archive_url=url,access_url=a.url,
                licence_note='Guardian article: metadata and short research excerpt only; full body not redistributed'))
    write_csv('media_day_archive_frame.csv',frame,['archive_day','url','title','archive_url','archive_sha256','unit'])
    write_csv('media_pilot_selected.csv',samples,list(samples[0]) if samples else ['role'])
    return {'archive_days':days,'article_samples':len(samples)}

def public():
    rows=[];url=BASE;params=PARAMS;seen=set();pages=0;seen_ids=set();duplicate_ids=[]
    while url:
        if url in seen:raise ValueError('pagination loop')
        seen.add(url)
        r=get(url,params=params);x=r.json();pages+=1
        if pages>20:raise ValueError('unexpected page count')
        for z in x['data']:
            a=z['attributes']; pid=str(z['id'])
            if pid in seen_ids:
                duplicate_ids.append(pid)
                continue
            seen_ids.add(pid)
            authorial=' '.join(clean(a.get(k,'')) for k in ('action','background','additional_details'))
            rows.append(dict(role='public',petition_id=pid,created_at=a.get('created_at',''),opened_at=a.get('opened_at',''),
               rejected_at=a.get('rejected_at',''),state=a.get('state',''),action=clean(a.get('action','')),
               background=clean(a.get('background','')),additional_details=clean(a.get('additional_details','')),
               authorial_text_character_count=len(authorial),query_term_in_authorial_text='climate' in authorial.lower(),
               government_response_excluded=bool(a.get('government_response')),
               parent_url=f'https://petition.parliament.uk/archived/petitions/{pid}',
               source_json_url=z['links']['self'],source_page_sha256=sha(r.content)))
        url=x['links'].get('next');params=None
    if len({r['petition_id'] for r in rows})!=len(rows):raise ValueError('deduplication failed')
    fields=list(rows[0])
    write_csv('public_climate_query_frame.csv',rows,fields)
    subset=[r for r in rows if '2015-11'<=r['created_at'][:7]<='2016-01']
    write_csv('public_pilot_2015_11_to_2016_01.csv',subset,fields)
    monthly={}
    for r in rows:monthly[r['created_at'][:7]]=monthly.get(r['created_at'][:7],0)+1
    write_csv('public_query_month_counts.csv',[{'month':k,'query_hit_parents':v} for k,v in sorted(monthly.items())],['month','query_hit_parents'])
    return {'query_pages':pages,'query_hits':len(rows),'duplicate_ids_across_pages':duplicate_ids,
            'pilot_subset':len(subset),'pilot_months':{m:sum(r['created_at'][:7]==m for r in subset) for m in ('2015-11','2015-12','2016-01')},
            'query_url':f'{BASE}?parliament=1&q=climate'}

if __name__=='__main__':
    result={'snapshot_utc':datetime.now(timezone.utc).isoformat(),'media':media(),'public':public()}
    (OUT/'web_pilot_snapshot.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
