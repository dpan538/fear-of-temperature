"""Serial bounded capture for observed public archive routes; saved stops are final."""
import argparse
import fcntl
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import collect_first_batch as resources

ROOT=resources.ROOT
AGENT='FearOfTemperatureResearch/1.0 (bounded public newspaper acquisition)'

def capture(url,purpose,source_id):
    parts=urllib.parse.urlsplit(url)
    robots=urllib.robotparser.RobotFileParser()
    object_ceiling=resources.OBJECT_CAP
    if parts.scheme!='https':raise ValueError('HTTPS public routes required')
    if source_id=='the_press' and parts.hostname=='paperspast.natlib.govt.nz':
        policy=(resources.OLD/'policies/the_press_robots.txt').read_text()
        metadata_cap=15
    elif source_id=='indaily' and parts.hostname in {'www.indailysa.com.au','assets.indailysa.com.au'}:
        previous_root=resources.REPO/'work_packages/M1_source_access/22_real_payload_acquisition_20261005'
        policy_id='5b677aaa0f09e7d820f2e856' if parts.hostname.startswith('www.') else '37fc8a77a36a6e560ca0ae76'
        policy=(previous_root/'media/raw'/(policy_id+'.bin')).read_text()
        metadata_cap=29
        if parts.hostname.startswith('assets.'):
            declared=parts.path in {'/sitemaps/news-indailysa/posts/post-300.xml','/sitemaps/news-indailysa/sitemap.xml'}
            if not declared and re.fullmatch(r'/sitemaps/news-indailysa/posts/post-\d+\.xml',parts.path):
                from bs4 import BeautifulSoup
                for row in [json.loads(s) for s in (ROOT/'REQUESTS.jsonl').read_text().splitlines() if s]:
                    if row['purpose']=='au_sitemap_index' and row['status']=='saved':
                        index=BeautifulSoup((ROOT/row['raw_path']).read_bytes(),'xml')
                        declared=url in {n.get_text() for n in index.find_all('loc')}
            if not declared:raise ValueError('Only observed newspaper sitemap links are in scope')
        if parts.hostname.startswith('www.') and not parts.path.startswith('/news/'):
            raise ValueError('Other site publications are outside the newspaper subframe')
    elif source_id=='mit_tech_history' and parts.hostname=='thetech.com' and parts.path.startswith('/issues/'):
        policy=(resources.OLD/'policies/mit_tech_robots.txt').read_text();metadata_cap=6
    elif source_id=='mit_tech_history' and parts.hostname=='s3.amazonaws.com' and purpose=='history_pdf':
        frames=json.loads((ROOT/'HISTORICAL_PDF_FRAME.json').read_text())
        if url not in {item['pdf_url'] for item in frames}:raise ValueError('PDF was not observed in a retained publisher wrapper')
        policy='User-agent: *\nAllow: /';metadata_cap=6;object_ceiling=16*1024**2
    else:raise ValueError('Outside the declared publisher route')
    robots.parse(policy.splitlines())
    if not robots.can_fetch(AGENT,url):raise ValueError('Saved native robots excludes the route')
    rid=hashlib.sha256((purpose+'|'+url).encode()).hexdigest()[:24]
    ledger=ROOT/'REQUESTS.jsonl'
    prior=[json.loads(s) for s in ledger.read_text().splitlines() if s]
    previous=next((r for r in reversed(prior) if r['request_id']==rid),None)
    if previous:
        if previous['status']!='saved':raise RuntimeError('Preserved stop; no automatic retry')
        raw=(ROOT/previous['raw_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=previous['raw_sha256']:raise RuntimeError('Saved hash conflict')
        return raw,previous
    with resources.LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        prior=[json.loads(s) for s in ledger.read_text().splitlines() if s]
        same=[r for r in prior if r.get('source_id')==source_id]
        metadata_purposes={'nz_calendar','nz_issue','au_sitemap','au_sitemap_index','history_index','history_wrapper'}
        metadata=sum(r['purpose'] in metadata_purposes for r in same)
        if purpose in metadata_purposes and metadata>=metadata_cap:
            raise RuntimeError('Initial remaining source metadata allowance reached; new scope required')
        budget=resources.preflight()
        cap=min(object_ceiling,
                (budget['free_bytes']-resources.resource_reserve()-resources.FLOOR-resources.OVERHEAD)//4,
                (resources.LIFETIME_CAP-budget['media_lifetime_used_bytes'])//4)
        if cap<1024:raise RuntimeError('Measured dynamic resource capacity is below 1 KiB')
        if same:
            elapsed=time.time()-__import__('datetime').datetime.fromisoformat(same[-1]['finished_at_utc']).timestamp()
            time.sleep(max(0,3-elapsed))
        path=ROOT/'raw'/(rid+'.bin')
        if path.exists():raise RuntimeError('Existing raw without receipt retained for recovery')
        receipt=dict(request_id=rid,source_id=source_id,url=url,purpose=purpose,
                     requested_at_utc=resources.utc(),budget=budget,object_cap_bytes=cap,status='not_started',
                     redirects_followed=False,automatic_retry=False)
        opener=urllib.request.build_opener(resources.DeclaredRedirects)
        try:
            with opener.open(urllib.request.Request(url,headers={'User-Agent':AGENT}),timeout=30) as response:
                raw=response.read(cap+1);partial=len(raw)>cap;raw=raw[:cap]
                path.write_bytes(raw)
                receipt.update(status='object_cap_stop' if partial else 'saved',http_status=response.status,
                    content_type=response.headers.get('Content-Type'),response_date=response.headers.get('Date'),
                    last_modified=response.headers.get('Last-Modified'),raw_path=str(path.relative_to(ROOT)),
                    raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),partial=partial)
        except urllib.error.HTTPError as error:
            receipt.update(status='http_stop',http_status=error.code,location=error.headers.get('Location'),retry_after=error.headers.get('Retry-After'))
        except Exception as error:receipt.update(status='transport_error',error=str(error))
        receipt['finished_at_utc']=resources.utc()
        with ledger.open('a') as output:output.write(json.dumps(receipt)+'\n')
    if receipt['status']!='saved':raise RuntimeError(json.dumps(receipt))
    return raw,receipt

if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('url');args.add_argument('purpose');args.add_argument('--source',default='the_press')
    a=args.parse_args();raw,receipt=capture(a.url,a.purpose,a.source);print(json.dumps(receipt))
