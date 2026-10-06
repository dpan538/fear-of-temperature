"""Post-acquisition structural extraction of retained The Tech article pages."""
import csv
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import pathlib
import re
import shutil
import sqlite3
from bs4 import BeautifulSoup
import extract_au

ROOT=pathlib.Path(__file__).resolve().parent
REPO=next(p for p in ROOT.parents if (p/'AGENTS.md').exists())
PARSER=ROOT.parents[1]/'newspaper/prototype/parser.py'
spec=importlib.util.spec_from_file_location('bounded_prior_parser',PARSER)
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
MONTHS={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}

def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    receipts=[json.loads(line) for line in (ROOT/'REQUESTS.jsonl').read_text().splitlines() if line]
    selected={r['request_id']:r for r in receipts if r['purpose']=='article' and r['status']=='saved'}
    records=[];added=0;metadata_added=0;reused=0
    previous_path=ROOT/'PUBLICATION_UNITS.jsonl'
    previous={r['request_id']:r for r in [json.loads(line) for line in previous_path.read_text().split('\n') if line] if r.get('request_id')} if previous_path.exists() else {}
    extractor_sha=digest(pathlib.Path(__file__).read_bytes());renderer_sha=digest(PARSER.read_bytes())
    lockpath=REPO/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
    with lockpath.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if shutil.disk_usage(ROOT).free-48*1024**2<15*1024**3:raise RuntimeError('Live physical floor would be crossed')
        con=sqlite3.connect(ROOT/'newspaper_followthrough.sqlite3')
        con.executescript('''
        CREATE TABLE IF NOT EXISTS pages(url TEXT PRIMARY KEY,source TEXT,stratum TEXT,publication_date TEXT,title TEXT,genre TEXT,identity_status TEXT);
        CREATE TABLE IF NOT EXISTS versions(url TEXT,raw_sha256 TEXT,body_sha256 TEXT,raw_path TEXT,body_path TEXT,retrieved_at TEXT,record_json TEXT,PRIMARY KEY(url,raw_sha256,body_sha256));
        CREATE TABLE IF NOT EXISTS checkpoints(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS metadata_revisions(url TEXT,raw_sha256 TEXT,body_sha256 TEXT,metadata_sha256 TEXT,derived_at_utc TEXT,record_json TEXT,PRIMARY KEY(url,raw_sha256,body_sha256,metadata_sha256));
        ''')
        for rid,receipt in selected.items():
            cached=previous.get(rid)
            raw_file=ROOT/receipt['raw_path']
            if cached and cached.get('extractor_sha256')==extractor_sha and cached.get('inline_renderer_sha256')==renderer_sha and cached.get('raw_sha256')==receipt['raw_sha256'] and cached.get('raw_mtime_ns')==raw_file.stat().st_mtime_ns:
                body_file=ROOT/cached['body_path'] if cached.get('body_path') else None
                if body_file is None or (body_file.exists() and body_file.stat().st_mtime_ns==cached.get('body_mtime_ns')):
                    records.append(cached);reused+=1;continue
            raw=(ROOT/receipt['raw_path']).read_bytes()
            if digest(raw)!=receipt['raw_sha256']:raise ValueError('Saved response hash differs from receipt')
            soup=BeautifulSoup(raw,'html.parser');nodes=soup.select('main.container > article.article')
            record={'url':receipt['url'],'source':'The Tech','stratum':'US','source_frame':'student newspaper supplement',
                'request_id':rid,'retrieved_at_utc':receipt['finished_at_utc'],'raw_path':receipt['raw_path'],
                'raw_sha256':receipt['raw_sha256'],'body_boundary':'main.container > article.article, retained native content children',
                'extractor_sha256':extractor_sha,'inline_renderer_sha256':renderer_sha,'raw_mtime_ns':raw_file.stat().st_mtime_ns,
                'historical_body_equivalence':'unknown; current publisher archive rendition',
                'provenance':'direct newspaper publication; underlying quoted-work origin separately unresolved',
                'semantic_labels_executed':False,'length_filter_used':False,'state':'boundary_pending'}
            if len(nodes)!=1:records.append(record);continue
            article=nodes[0];title=article.select_one('h1.headline')
            record['title']=title.get_text(' ',strip=True) if title else ''
            record['genre']=';'.join(n.get_text(' ',strip=True) for n in article.select('.article-sections .section'))
            record['byline']=';'.join(n.get_text(' ',strip=True) for n in article.select('.article-meta .author'))
            stamp=article.select_one('.article-meta .timestamp')
            text=stamp.get_text(' ',strip=True) if stamp else ''
            record['displayed_date']=text
            m=re.search(r'([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})',text)
            date=None
            if m and m.group(1)[:3].lower() in MONTHS:
                date=dt.date(int(m.group(3)),MONTHS[m.group(1)[:3].lower()],int(m.group(2))).isoformat()
            url_match=re.search(r'/(\d{4})/(\d{2})/(\d{2})/',receipt['url'])
            url_date='-'.join(url_match.groups()) if url_match else None
            record.update(publication_date=date,url_date=url_date,date_mapping_status='agrees' if date and date==url_date else 'pending conflict/missing')
            media=[]
            for n in article.select('.slideshow'):media.append(n.get_text(' ',strip=True))
            record['image_captions']=media
            for node in article.select('.article-sections,h1.headline,h2.subhead,h4.article-meta,.article-social,.article-tags,.slideshow'):
                node.decompose()
            for node in article.find_all('h3',recursive=False):
                if ' '.join(node.get_text().split())==' '.join(record['title'].split()):node.decompose()
            body=parser.normalise(parser.render(article))
            record.update(paragraph_count=len(article.find_all('p')),table_count=len(article.find_all('table')),
                body_characters=len(body),body_sha256=digest(body.encode()),
                publication_unit='native newspaper page; table/component relations unassessed' if article.find('table') else 'native newspaper prose page',
                independent_original_work_status='unassessed; URL uniqueness does not establish independent original story',
                source_publication_identity='publisher-native article path and displayed title/date',
                state='saved_readable_publication_unit' if body and date and '1988-01-01'<=date<='2026-09-21' else 'retained_pending_date_or_body')
            body_path=ROOT/'bodies'/(rid+'_'+record['body_sha256'][:12]+'.txt');body_path.parent.mkdir(exist_ok=True)
            if not body_path.exists():body_path.write_text(body,encoding='utf-8')
            record['body_path']=str(body_path.relative_to(ROOT))
            record['body_mtime_ns']=body_path.stat().st_mtime_ns
            with con:
                existing=con.execute('SELECT publication_date,title FROM pages WHERE url=?',(record['url'],)).fetchone()
                if existing and existing!=(date,record['title']):record['identity_change']='retained version; prior parent fields preserved'
                con.execute('INSERT OR IGNORE INTO pages VALUES(?,?,?,?,?,?,?)',(record['url'],'The Tech','US',date,record['title'],record['genre'],record['state']))
                cursor=con.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?,?,?)',
                    (record['url'],record['raw_sha256'],record['body_sha256'],record['raw_path'],record['body_path'],record['retrieved_at_utc'],json.dumps(record,ensure_ascii=False)))
                added+=cursor.rowcount
            records.append(record)
        early_path=ROOT/'EARLY_ARTICLE_RECORD.json'
        if early_path.exists():
            early=json.loads(early_path.read_text())
            for field,hash_field in [('raw_path','raw_sha256'),('body_path','body_sha256')]:
                if digest((ROOT/early[field]).read_bytes())!=early[hash_field]:
                    raise ValueError('Early retained article hash differs from its receipt')
            early.update(stratum='US',request_id=pathlib.Path(early['raw_path']).stem,state='saved_readable_article_OCR_uncertainty_retained',
                date_mapping_status='printed issue masthead visually checked',
                historical_body_equivalence='scanned historical issue; scan/version time separate',
                publication_unit='one article; seven geometric segments with explicit page continuation',
                body_characters=len((ROOT/early['body_path']).read_text()),semantic_labels_executed=False,
                length_filter_used=False,provenance='direct newspaper issue scan; publisher OCR uncertainty retained')
            with con:
                con.execute('INSERT OR IGNORE INTO pages VALUES(?,?,?,?,?,?,?)',
                    (early['url'],'The Tech','US',early['publication_date'],early['title'],early['genre'],early['state']))
                cursor=con.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?,?,?,?)',
                    (early['url'],early['raw_sha256'],early['body_sha256'],early['raw_path'],early['body_path'],early['retrieved_at_utc'],json.dumps(early,ensure_ascii=False)))
                added+=cursor.rowcount
            records.append(early)
        au_records,au_added=extract_au.extract(receipts,ROOT,con,parser,previous)
        records.extend(au_records);added+=au_added
        with con:
            for record in records:
                if not record.get('body_sha256'):continue
                old=con.execute('SELECT record_json FROM versions WHERE url=? AND raw_sha256=? AND body_sha256=?',
                    (record['url'],record['raw_sha256'],record['body_sha256'])).fetchone()
                if old and json.loads(old[0])!=record:
                    serialized=json.dumps(record,sort_keys=True)
                    cursor=con.execute('INSERT OR IGNORE INTO metadata_revisions VALUES(?,?,?,?,?,?)',
                        (record['url'],record['raw_sha256'],record['body_sha256'],digest(serialized.encode()),dt.datetime.now(dt.timezone.utc).isoformat(),serialized))
                    metadata_added+=cursor.rowcount
        with con:con.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?)',('retained_article_receipts',json.dumps(sorted(selected))))
        issue_path=ROOT/'ISSUE_CONTAINER_MANIFEST.json'
        issues=json.loads(issue_path.read_text()) if issue_path.exists() else []
        con.execute('CREATE TABLE IF NOT EXISTS issue_containers(source_url TEXT PRIMARY KEY,publication_date TEXT,raw_sha256 TEXT,record_json TEXT)')
        with con:
            for issue in issues:
                con.execute('INSERT OR IGNORE INTO issue_containers VALUES(?,?,?,?)',
                    (issue['source_url'],issue['publication_date'],issue['raw_sha256'],json.dumps(issue)))
        integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
        parents=con.execute('SELECT COUNT(*) FROM pages').fetchone()[0];versions=con.execute('SELECT COUNT(*) FROM versions').fetchone()[0];con.close()
    with (ROOT/'PUBLICATION_UNITS.jsonl').open('w') as output:
        for row in records:output.write(json.dumps(row,ensure_ascii=True)+'\n')
    us_records=[r for r in records if r['stratum']=='US']
    months=sorted({r['publication_date'][:7] for r in us_records if r['state'].startswith('saved_readable')})
    all_months=[]
    for year in range(1988,2027):
        for month in range(1,13):
            key=f'{year:04d}-{month:02d}'
            if key>'2026-09':break
            all_months.append({'month':key,'stratum':'US','source_frame':'The Tech student press supplement',
                'saved_readable_publication_units':sum(bool(r.get('publication_date')) and r.get('publication_date','')[:7]==key and r['state'].startswith('saved_readable') for r in us_records),
                'coverage_state':'readable publication units saved; independent parent relations pending' if key in months else 'not acquired in this successor',
                'eligible_population_count':'unknown','full_frame_complete':False})
    with (ROOT/'US_SOURCE_MONTH_LEDGER.csv').open('w',newline='') as output:
        writer=csv.DictWriter(output,fieldnames=list(all_months[0]));writer.writeheader();writer.writerows(all_months)
    strata=['EU/Europe excluding UK','UK','AU','US','NZ','pooled']
    combined=[]
    for stratum in strata:
        for item in all_months:
            key=item['month']
            retained=[r for r in records if r.get('publication_date','') and r['publication_date'][:7]==key and (stratum=='pooled' or r['stratum']==stratum)]
            count=sum(r['state'].startswith('saved_readable') for r in retained)
            issue_count=sum(i['publication_date'][:7]==key and (stratum=='pooled' or i['stratum']==stratum) for i in issues)
            combined.append(dict(month=key,stratum=stratum,readable_saved_units=count,retained_publication_units=len(retained),whole_issue_PDFs=issue_count,dated_source_presence=bool(count or issue_count),
                state='bounded retained presence; full archive incomplete' if count or issue_count else 'not acquired/readable in this successor; no expression-zero claim',
                fixed_upper_cutoff='2026-09-21',eligible_population='unknown',sources=';'.join(sorted({r['source'] for r in retained}))))
    with (ROOT/'NEWSPAPER_MONTH_LEDGER.csv').open('w',newline='') as output:
        writer=csv.DictWriter(output,fieldnames=list(combined[0]));writer.writeheader();writer.writerows(combined)
    result={'at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'native_pages_staged':parents,'content_versions':versions,
        'new_versions_this_run':added,'new_metadata_revisions_this_run':metadata_added,'reused_unchanged_US_derivations':reused,'retained_pending_units':sum(not r['state'].startswith('saved_readable') for r in records),'readable_publication_units':sum(r['state'].startswith('saved_readable') for r in records),
        'html_date_agreement':sum(r.get('date_mapping_status')=='agrees' for r in records),
        'early_pdf_articles_with_visual_date_check':sum(r['state']=='saved_readable_article_OCR_uncertainty_retained' for r in records),
        'table_bearing_units':sum(bool(r.get('table_count')) for r in records),'saved_months':months,
        'readable_by_stratum':{s:sum(r['stratum']==s and r['state'].startswith('saved_readable') for r in records) for s in strata[:-1]},
        'observed_months_by_stratum':{s:sorted({r['publication_date'][:7] for r in records if r['stratum']==s and r['state'].startswith('saved_readable')}) for s in strata[:-1]},
        'whole_issue_containers':len(issues),'dated_presence_months_by_stratum':{st:sum(x['stratum']==st and x['dated_source_presence'] for x in combined) for st in strata},
        'calendar_months_reported':len(all_months),'staging_integrity':integrity,
        'independent_original_story_total':'not established; pending relation checks do not delete saved units'}
    (ROOT/'STAGING_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
