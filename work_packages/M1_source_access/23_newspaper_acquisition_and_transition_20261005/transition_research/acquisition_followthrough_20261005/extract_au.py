"""Structural extraction from already retained AU publisher pages."""
import datetime as dt
import hashlib
import json
import re
from bs4 import BeautifulSoup

def extract(receipts,root,con,renderer,previous=None):
    rows=[];added=0
    extractor_sha=hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()
    for receipt in receipts:
        if receipt['purpose']!='au_article' or receipt['status']!='saved':continue
        cached=(previous or {}).get(receipt['request_id'])
        if cached and cached.get('extractor_sha256')==extractor_sha and cached.get('raw_sha256')==receipt['raw_sha256'] and cached.get('raw_mtime_ns')==(root/receipt['raw_path']).stat().st_mtime_ns:
            if cached.get('body_path') and (root/cached['body_path']).stat().st_mtime_ns==cached.get('body_mtime_ns'):
                rows.append(cached);continue
        raw=(root/receipt['raw_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=receipt['raw_sha256']:raise ValueError('AU retained raw hash conflict')
        soup=BeautifulSoup(raw,'html.parser');h=soup.find('h1')
        record=dict(url=receipt['url'],source='InDaily',stratum='AU',source_frame='newspaper-brand digital successor; print/digital break retained',
            raw_path=receipt['raw_path'],raw_sha256=receipt['raw_sha256'],request_id=receipt['request_id'],
            retrieved_at_utc=receipt['finished_at_utc'],title=h.get_text(' ',strip=True) if h else '',
            historical_body_equivalence='unknown; current archive body may have later publisher updates',
            topic_or_emotion_filter=None,semantic_labels_executed=False,length_filter_used=False,
            extractor_sha256=extractor_sha,raw_mtime_ns=(root/receipt['raw_path']).stat().st_mtime_ns,
            retention='bounded local research evidence; copyright retained; no open grant/public raw redistribution assumed',
            independent_original_work_status='unassessed; preserve byline, republished-work notice and publisher-native parent separately')
        published=soup.select_one('meta[property="article:published_time"]')
        modified=soup.select_one('meta[property="article:modified_time"]')
        record['publisher_publication_timestamp']=published.get('content') if published else None
        record['publisher_content_version_timestamp']=modified.get('content') if modified else None
        date=dt.datetime.fromisoformat(record['publisher_publication_timestamp']).date().isoformat() if published else None
        match=re.search(r'/(\d{4})/(\d{2})/(\d{2})/',receipt['url'])
        url_date='-'.join(match.groups()) if match else None
        sidebar=soup.select_one('[data-location="article-sidebar"]')
        names=sidebar.select('a.block[href*="/contributor/"]') if sidebar else []
        record['byline']=';'.join(dict.fromkeys(n.get_text(' ',strip=True) for n in names))
        record['publisher_sidebar_metadata']=sidebar.get_text(' ',strip=True) if sidebar else ''
        record['displayed_timestamp']=next((n.get_text(' ',strip=True) for n in sidebar.find_all('span') if re.search(r'\b\d{4}\b',n.get_text())),None) if sidebar else None
        record.update(publication_date=date,url_date=url_date,date_mapping_status='agrees' if date and date==url_date else 'pending conflict/missing',
                      genre=receipt['url'].split('/news/')[1].split('/')[0])
        prose=soup.find('p',class_='mb-4')
        body_node=prose.find_parent('div',class_='relative') if prose else None
        if body_node is None or 'overflow-hidden' not in body_node.get('class',[]):
            record['state']='retained_boundary_pending';rows.append(record);continue
        lead=h.find_next_sibling('div') if h else None
        for child in list(body_node.find_all('div',recursive=False)):
            classes=child.get('class',[])
            if ('border-y' in classes and child.get_text(' ',strip=True).startswith('You might like')) or (child.find('form') and child.find('h1')):
                child.decompose()
        for child in body_node.select('script,style,svg,form'):child.decompose()
        body=renderer.normalise((renderer.render(lead) if lead else '')+'\n\n'+renderer.render(body_node))
        record['provenance']='direct evidence of newspaper-brand publication; quoted and syndicated work origins separately recorded'
        record['syndication_notices']=[n.get_text(' ',strip=True) for n in body_node.select('p') if 'first published' in n.get_text().lower() or 'republished' in n.get_text().lower()]
        record.update(body_boundary='headline-adjacent standfirst plus native div.relative.w-full.overflow-hidden article prose; observed related/newsletter modules removed',
            body_characters=len(body),body_sha256=hashlib.sha256(body.encode()).hexdigest(),paragraph_count=len(body_node.find_all('p')),
            table_count=len(body_node.find_all('table')),publication_unit='native newspaper-brand digital publication page',
            state='saved_readable_publication_unit' if body and date and '1988-01-01'<=date<='2026-09-21' else 'retained_pending_date_or_body')
        path=root/'bodies'/(receipt['request_id']+'_'+record['body_sha256'][:12]+'.txt')
        if not path.exists():path.write_text(body)
        record['body_path']=str(path.relative_to(root))
        record['body_mtime_ns']=path.stat().st_mtime_ns
        with con:
            con.execute('INSERT OR IGNORE INTO pages VALUES(?,?,?,?,?,?,?)',
                (record['url'],'InDaily','AU',date,record['title'],record['genre'],record['state']))
            cursor=con.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?,?,?)',
                (record['url'],record['raw_sha256'],record['body_sha256'],record['raw_path'],record['body_path'],record['retrieved_at_utc'],json.dumps(record)))
            added+=cursor.rowcount
        rows.append(record)
    return rows,added
