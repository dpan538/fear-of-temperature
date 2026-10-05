"""Fixed 31-day archive audit; metadata-only article probes with no body storage."""
import argparse
import csv
import hashlib
import re
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HERE=Path(__file__).resolve().parent
HEAD={'User-Agent':'FearTemperatureResearch/0.1 (academic source-feasibility audit; metadata only)'}
S=requests.Session();S.headers.update(HEAD)
MONTHS=('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec')

def write(name,rows,fields):
    with (HERE/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def read(name):
    with (HERE/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def digest(data):return hashlib.sha256(data).hexdigest()

def archive():
    days=[];cards=[]
    for day in range(1,32):
        d=date(2015,12,day)
        url=f'https://www.theguardian.com/environment/2015/dec/{day:02d}/all'
        state=dict(day=d.isoformat(),archive_url=url,http_status='',archive_sha256='',nonvideo_card_positions='',
                   distinct_nonvideo_url_count='',pagination_links='',pagination_issue='',error='')
        try:
            r=S.get(url,timeout=20);state['http_status']=r.status_code;r.raise_for_status()
            state['archive_sha256']=digest(r.content)
            soup=BeautifulSoup(r.text,'html.parser')
            all_cards=soup.select('h3.fc-item__title')
            found=[]
            for h in all_cards:
                a=h.find('a',href=True)
                if not a:continue
                link=a['href'].split('?')[0]
                host=urlparse(link).hostname or ''
                if host not in ('theguardian.com','www.theguardian.com') or '/video/' in urlparse(link).path:continue
                found.append((link,h.get_text(' ',strip=True)))
            state['nonvideo_card_positions']=len(found)
            state['distinct_nonvideo_url_count']=len({x[0] for x in found})
            pagination=[(a.get('rel',''),a.get('href','')) for a in soup.select('.pagination a[href]')]
            state['pagination_links']=' | '.join(str(x) for x in pagination)
            if any('page=' in href for _,href in pagination):state['pagination_issue']='page_parameter_present'
            elif len(pagination)>2:state['pagination_issue']='more_than_day_navigation'
            else:state['pagination_issue']='day_navigation_only_or_none'
            for link,title in found:
                cards.append(dict(archive_day=d.isoformat(),article_url=link,title=title,
                                  archive_url=url,archive_sha256=state['archive_sha256']))
        except Exception as e:state['error']=f'{type(e).__name__}: {str(e)[:180]}'
        days.append(state)
        print(d,state['http_status'],state['distinct_nonvideo_url_count'],state['pagination_issue'],state['error'],flush=True)
        time.sleep(0.15)
    write('guardian_dec2015_archive_days.csv',days,list(days[0]))
    write('guardian_dec2015_archive_cards.csv',cards,list(cards[0]))
    unique={r['article_url'] for r in cards}
    print('days',len(days),'card_positions',len(cards),'unique_urls',len(unique),'problem_days',[r['day'] for r in days if r['http_status']!=200 or r['pagination_issue']!='day_navigation_only_or_none'])

def probe(url):
    r=S.get(url,timeout=20,stream=True)
    status=r.status_code
    chunks=[];size=0
    try:
        for chunk in r.iter_content(chunk_size=16384):
            chunks.append(chunk);size+=len(chunk)
            if size>=65536:break
    finally:r.close()
    sample=b''.join(chunks).decode('utf-8','replace')
    pub=re.search(r'<meta\s+property="article:published_time"\s+content="([^"]+)"',sample)
    if not pub:pub=re.search(r'<meta\s+content="([^"]+)"\s+property="article:published_time"',sample)
    mod=re.search(r'<meta\s+property="article:modified_time"\s+content="([^"]+)"',sample)
    canon=re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"',sample)
    return status,pub.group(1) if pub else '',mod.group(1) if mod else '',canon.group(1) if canon else '',size

def metadata():
    cards=read('guardian_dec2015_archive_cards.csv')
    grouped={}
    for r in cards:grouped.setdefault(r['article_url'],[]).append(r)
    rows=[]
    for n,url in enumerate(sorted(grouped),1):
        row=dict(article_url=url,title=grouped[url][0]['title'],archive_days=' | '.join(sorted({x['archive_day'] for x in grouped[url]})),
                 archive_card_occurrences=len(grouped[url]),http_status='',original_published_at='',current_modified_at='',
                 canonical_url='',metadata_bytes_read='',published_utc_month='',body_checked='no',error='')
        try:
            status,pub,mod,canon,size=probe(url)
            row.update(http_status=status,original_published_at=pub,current_modified_at=mod,
                       canonical_url=canon,metadata_bytes_read=size,published_utc_month=pub[:7])
            if status!=200:row['error']=f'HTTP {status}'
            elif not pub:row['error']='original publication meta absent in first 64KiB'
        except Exception as e:row['error']=f'{type(e).__name__}: {str(e)[:180]}'
        rows.append(row)
        if n%50==0:print('probed',n,'of',len(grouped),flush=True)
        time.sleep(0.12)
    write('guardian_dec2015_article_metadata.csv',rows,list(rows[0]) if rows else ['article_url'])
    print('article_urls',len(rows),'HTTP200',sum(r['http_status']==200 for r in rows),
          'publication_dates',sum(bool(r['original_published_at']) for r in rows),
          'December_UTC',sum(r['published_utc_month']=='2015-12' for r in rows),
          'unresolved',sum(bool(r['error']) for r in rows),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('archive','metadata'));a=p.parse_args()
    {'archive':archive,'metadata':metadata}[a.stage]()
