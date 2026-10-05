"""Three fixed Guardian original-body spot checks; store only short excerpts."""
import csv
import hashlib
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HERE=Path(__file__).resolve().parent
SEED='paris-readiness-20260927-v2'

def read(name):
    with (HERE/name).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def rank(url):return hashlib.sha256((SEED+'|'+url).encode()).hexdigest()

rows=read('guardian_dec2015_article_metadata.csv')
bands=[('pre_agreement',1,11),('agreement',12,13),('post_agreement',14,31)]
selected=[]
for label,start,end in bands:
    eligible=[r for r in rows if start<=int(r['original_published_at'][8:10])<=end and
              any(t in r['title'].lower() for t in ('climate','paris','warming'))]
    if not eligible:raise ValueError(f'no title candidate in {label}')
    r=min(eligible,key=lambda x:rank(x['article_url']))
    selected.append((label,len(eligible),r))
out=[]
for label,n,r in selected:
    resp=requests.get(r['article_url'],timeout=25,headers={'User-Agent':'FearTemperatureResearch/0.1 (academic source-feasibility body spot check)'})
    resp.raise_for_status()
    soup=BeautifulSoup(resp.text,'html.parser')
    body=soup.select_one('[data-gu-name="body"]')
    paras=[re.sub(r'\s+',' ',p.get_text(' ',strip=True)).strip() for p in body.find_all('p')] if body else []
    out.append(dict(phase=label,candidate_title_pool=n,article_url=r['article_url'],title=r['title'],
        original_published_at=r['original_published_at'],current_modified_at=r['current_modified_at'],
        body_present=bool(body and any(paras)),body_paragraph_count=len(paras),body_characters=sum(len(p) for p in paras),
        short_evidence_excerpt=' | '.join(p[:95] for p in paras[:2]),html_sha256=hashlib.sha256(resp.content).hexdigest(),
        climate_warming_topic='',anticipated_climate_harm_cue='',explicit_fear_expression='',
        review_state='body_access_checked; relevance_not_classified_in_this_script'))
with (HERE/'guardian_dec2015_body_spot_checks.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,list(out[0]));w.writeheader();w.writerows(out)
for r in out:print(r['phase'],r['original_published_at'],r['title'][:90],r['body_present'],r['body_paragraph_count'])
