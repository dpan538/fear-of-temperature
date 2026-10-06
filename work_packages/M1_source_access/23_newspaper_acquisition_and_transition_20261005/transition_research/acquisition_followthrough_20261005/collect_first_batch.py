"""Bounded real newspaper retrieval. Review follows saving; no semantic gate."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import pathlib
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup

ROOT=pathlib.Path(__file__).resolve().parent
REPO=next(p for p in ROOT.parents if (p/'AGENTS.md').exists())
OLD=ROOT.parents[1]/'newspaper'
LOCK=REPO/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
FLOOR=15*1024**3
OLD_RESERVE=3335940580
OVERHEAD=48*1024**2
OBJECT_CAP=2*1024**2
BATCH_CAP=16*1024**2
LIFETIME_CAP=128*1024**2
PRIOR=25819723
INDEXES=[('2007-02','https://thetech.com/issues/127/1'),('2026-08','https://thetech.com/issues/146/13')]

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def total_bytes(directory): return sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())
def resource_reserve():
    p=ROOT/'RESOURCE_DECISION.json'
    if not p.exists(): return OLD_RESERVE
    decision=json.loads(p.read_text())
    if not decision.get('direct_user_authorization') or not decision.get('recorded_at_utc'):
        raise ValueError('Resource decision needs direct user authorization and timestamp')
    reserve=decision['original_remaining_reserve_bytes']
    if not isinstance(reserve,int) or reserve<0: raise ValueError('Invalid resource reserve')
    return reserve
def preflight():
    free=shutil.disk_usage(ROOT).free
    reserve=resource_reserve()
    used=PRIOR+total_bytes(OLD)+total_bytes(ROOT)
    dynamic_cap=max(0,min(OBJECT_CAP,(free-reserve-OVERHEAD-FLOOR)//4,(LIFETIME_CAP-used)//4))
    projected=free-reserve-OVERHEAD-4*dynamic_cap
    return dict(at_utc=utc(),free_bytes=free,original_remaining_reserve_bytes=reserve,
                physical_floor_bytes=FLOOR,staging_recovery_allowance_bytes=OVERHEAD,
                pending_raw_derivative_allowance_bytes=4*dynamic_cap,dynamic_object_cap_bytes=dynamic_cap,projected_free_bytes=projected,
                media_lifetime_used_bytes=used,media_lifetime_cap_bytes=LIFETIME_CAP,
                passed=dynamic_cap>=1024 and projected>=FLOOR and used+4*dynamic_cap<=LIFETIME_CAP)

class DeclaredRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,response,code,message,headers,newurl):
        # No unrecorded redirect hops. The caller saves a stop and keeps the selected URL.
        return None

def main():
    arguments=argparse.ArgumentParser();arguments.add_argument('--execute',action='store_true')
    arguments.add_argument('--plan',type=pathlib.Path)
    args=arguments.parse_args()
    plan=json.loads(args.plan.read_text()) if args.plan else {'batch_id':'first','indexes':INDEXES,'articles_per_index':6}
    indexes=plan['indexes'];limit=plan['articles_per_index']
    if not isinstance(limit,int) or not 1<=limit<=40:raise ValueError('Bounded article selection limit required')
    if len(indexes)>12:raise ValueError('Index batch exceeds remaining bounded metadata allowance')
    result={'started_at_utc':utc(),'source':'The Tech','stratum':'US student newspaper supplement',
            'publication_interval':['1988-01-01','2026-09-21'],'indexes_saved':0,'article_responses_saved':0,
            'qualified_readable_articles':'pending post-acquisition review','raw_bytes':0,'requests':0,'new_article_downloads':0,
            'topic_or_emotion_filter':None,'automatic_failed_target_replacement':False,'batch_id':plan['batch_id'],'issue_pdf_downloads':0}
    initial=preflight();(ROOT/'LATEST_PREFLIGHT.json').write_text(json.dumps(initial,indent=2)+'\n')
    if not args.execute or not initial['passed']:
        result['stop']='preflight_only' if not args.execute else 'resource_allocation_blocked'
        result['preflight']=initial
        output=ROOT/('RUN_RESULT.json' if plan['batch_id']=='first' else 'RUN_RESULT_'+plan['batch_id']+'.json')
        output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result));return
    deadline=time.monotonic()+1200
    opener=urllib.request.build_opener(DeclaredRedirects)
    last_request=0
    frames_path=ROOT/('FROZEN_FRAMES.json' if plan['batch_id']=='first' else 'FROZEN_FRAMES_'+plan['batch_id']+'.json')
    frames=json.loads(frames_path.read_text()) if frames_path.exists() else []
    def fetch(url,purpose):
        nonlocal last_request
        if time.monotonic()>=deadline: raise RuntimeError('20-minute bound reached')
        parts=urllib.parse.urlsplit(url)
        permitted_host=parts.hostname=='thetech.com'
        if purpose=='issue_pdf' and parts.hostname=='s3.amazonaws.com':
            observed=ROOT/'EARLY_PDF_TARGET.json'
            permitted_host=observed.exists() and json.loads(observed.read_text())['url']==url
        if parts.scheme!='https' or not permitted_host or parts.path.startswith(('/api','/search','/admin','/image_search')):
            raise ValueError('URL is outside declared public publisher paths')
        time.sleep(max(0,2-(time.monotonic()-last_request)))
        rid=hashlib.sha256((purpose+'|'+url).encode()).hexdigest()[:24]
        receipt={'request_id':rid,'url':url,'purpose':purpose,'requested_at_utc':utc(),'status':'not_started'}
        path=ROOT/'raw'/(rid+'.bin')
        prior=[]
        ledger=ROOT/'REQUESTS.jsonl'
        if ledger.exists():prior=[json.loads(line) for line in ledger.read_text().splitlines() if line]
        previous=next((item for item in reversed(prior) if item['request_id']==rid),None)
        if previous:
            if previous['status']=='saved':
                data=path.read_bytes()
                if hashlib.sha256(data).hexdigest()!=previous['raw_sha256']:raise RuntimeError('Saved raw hash conflict')
                return data,previous
            if previous['status'] in {'transport_error','object_cap_stop'} or previous.get('http_status') in {404,410,500,502,503,504}:
                result['preserved_failed_targets']=result.get('preserved_failed_targets',0)+1
                return None,previous
            raise RuntimeError('Preserved request stop; no automatic retry: '+previous['status'])
        if purpose=='index' and plan.get('round_id'):
            scope_path=ROOT/(plan['round_id'].upper().replace('SUCCESSOR_ROUND_','ROUND')+'_SCOPE.json')
            scope=json.loads(scope_path.read_text())
            cumulative=18+sum(item['purpose']=='index' for item in prior)
            if cumulative-scope['prior_metadata_total']>=scope['new_metadata_allowance']:
                raise RuntimeError('Recorded round metadata allowance reached; prior requests remain counted')
        if path.exists(): raise RuntimeError('Raw exists without its receipt; preserve for recovery')
        with LOCK.open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            budget=preflight();receipt['budget']=budget
            if not budget['passed']: raise RuntimeError('Measured resource preflight failed')
            cap=min(budget['dynamic_object_cap_bytes'],BATCH_CAP-result['raw_bytes'])
            if cap<1024: raise RuntimeError('16MiB batch cap reached')
            receipt['object_cap_bytes']=cap
            request=urllib.request.Request(url,headers={'User-Agent':'FearOfTemperatureResearch/1.0 (bounded public newspaper acquisition)'})
            last_request=time.monotonic();result['requests']+=1
            try:
                with opener.open(request,timeout=30) as response:
                    data=response.read(cap+1)
                    partial=len(data)>cap;data=data[:cap]
                    path.parent.mkdir(exist_ok=True);path.write_bytes(data)
                    receipt.update(status='object_cap_stop' if partial else 'saved',http_status=response.status,
                        content_type=response.headers.get('Content-Type'),response_date=response.headers.get('Date'),
                        last_modified=response.headers.get('Last-Modified'),raw_path=str(path.relative_to(ROOT)),
                        raw_bytes=len(data),raw_sha256=hashlib.sha256(data).hexdigest(),partial=partial)
                    result['raw_bytes']+=len(data)
                    if purpose=='article' and not partial:result['new_article_downloads']+=1
            except urllib.error.HTTPError as error:
                receipt.update(status='http_stop',http_status=error.code,location=error.headers.get('Location'),
                               retry_after=error.headers.get('Retry-After'))
            except Exception as error: receipt.update(status='transport_error',error=str(error))
            receipt['finished_at_utc']=utc()
            with (ROOT/'REQUESTS.jsonl').open('a') as output:output.write(json.dumps(receipt)+'\n')
        if receipt['status']=='transport_error' or receipt.get('http_status') in {404,410,500,502,503,504}:
            result['preserved_failed_targets']=result.get('preserved_failed_targets',0)+1
            return None,receipt
        if receipt['status']=='object_cap_stop':return None,receipt
        if receipt['status']!='saved': raise RuntimeError('Preserved request stop: '+receipt['status'])
        return data,receipt
    try:
        for month,url in indexes:
            raw,receipt=fetch(url,'index')
            if raw is None:continue
            result['indexes_saved']+=1
            soup=BeautifulSoup(raw,'html.parser');targets=[];seen=set()
            for link in soup.select('a[href]'):
                article=urllib.parse.urljoin(url,link['href']).split('#')[0]
                p=urllib.parse.urlsplit(article);match=re.match(r'^/(\d{4})/(\d{2})/(\d{2})/[^/]+',p.path)
                if p.hostname!='thetech.com' or not match or article in seen:continue
                day='-'.join(match.groups())
                try:dt.date.fromisoformat(day)
                except ValueError:continue
                if (month not in {'auto','calendar'} and day[:7]!=month) or not '1988-01-01'<=day<='2026-09-21':continue
                seen.add(article);targets.append(dict(url=article,native_order=len(targets)+1,url_date=day,title=link.get_text(' ',strip=True)))
            if plan.get('presence_first'):
                covered=set();subset=[]
                for target in targets:
                    key=target['url_date'][:7]
                    if key not in covered:covered.add(key);subset.append(target)
                targets=subset
            frame=next((item for item in frames if item['index_receipt']==receipt['request_id']),None)
            if frame and (frame['index_receipt']!=receipt['request_id'] or frame['selected']!=targets[:limit]):
                raise RuntimeError('Frozen selection conflict; no overwrite or refill')
            frame=frame or dict(source='mit_tech',month=month,index_receipt=receipt['request_id'],frozen_at_utc=utc(),
                       order='native_DOM',selected=targets[:limit],eligible_frame_complete=False,eligible_count=None,
                       url_date_requires_body_corroboration=True,failed_target_replacement=False)
            if not any(item['index_receipt']==receipt['request_id'] for item in frames):frames.append(frame)
            frames_path.write_text(json.dumps(frames,indent=2)+'\n')
            for target in frame['selected']:
                body,response=fetch(target['url'],'article')
                if body is not None:result['article_responses_saved']+=1
        for target in plan.get('payloads',[]):
            data,response=fetch(target['url'],target['purpose'])
            if data is not None and target['purpose']=='issue_pdf':result['issue_pdf_downloads']+=1
        result['stop']='bounded_batch_downloaded; post-acquisition identity/date/body review pending'
    except Exception as error:result['stop']=str(error)
    finally:
        result['finished_at_utc']=utc();result['closing_preflight']=preflight()
        output=ROOT/('RUN_RESULT.json' if plan['batch_id']=='first' else 'RUN_RESULT_'+plan['batch_id']+'.json')
        output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
