"""Proposed, release-gated continuation. Default is offline; never reset V3 stops.

One direct-Item Accept correction, then the same unrequested frozen B queue if
that single validation succeeds. AU is a separately released four-request plan.
No database writes, replacement Items, sibling expansion or automatic restart.
"""
import argparse
import csv
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP = ROOT/'work_packages/M1_source_access'
OLD_HERE = WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation'
OLD_STAGE = WP/'18_bounded_supplementation_execution_20261005'
OLD_A = OLD_STAGE/'01_downloader_and_originals'
OLD_B = OLD_STAGE/'02_eu_staging'
V3 = OLD_HERE/'stage_frozen_items.py'
V3_SHA = 'f6f2bda93e9745c56ff9fd438be8071af2b40ee65b5f5b625d30f2d1c5e28bb2'
B_SHA = 'af3fa2aa5c9cd6b1e97ad8b27fba17769be2c4916b3ef3dc4a6ab87fb772a4f7'
FAILED_URI = 'http://publications.europa.eu/resource/cellar/3df58e03-97cd-11e4-b8a5-01aa75ed71a1.0006.01/DOC_1'
VERSION = 'gov_closeout_transport_candidate_v1_20261005'
RELEASE = HERE.parent/'control/GOV_CONTINUATION_RELEASE.json'
HEAVY = WP/'14_structural_validation_20261004/control/heavy_io.lock'
OUT = HERE/'continuation'
GLOBAL_STATE = OUT/'GLOBAL_REQUEST_SPACING.json'
GIB = 2**30
INTERVAL = ['1988-01-01','2026-09-21']


def now(): return datetime.now(timezone.utc).isoformat()


def require(value, message):
    if not value: raise RuntimeError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()


def load(path): return json.loads(Path(path).read_text())


def save(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:
        f.write(json.dumps(obj,ensure_ascii=False,indent=2)+'\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)


def read_csv(path):
    with Path(path).open() as f: return list(csv.DictReader(f))


def old_runner():
    require(sha(V3)==V3_SHA,'Accepted V3 changed')
    spec=importlib.util.spec_from_file_location('accepted_staging_v3',V3)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def expected_bindings():
    paths={'old_a_stop_sha256':OLD_A/'SHARED_HTTP_STATE.json',
           'old_b_stop_sha256':OLD_B/'PHASE_HTTP_STATE.json',
           'old_eu_release_sha256':OLD_STAGE/'control/EU_STAGING_RELEASE.json',
           'old_b_result_sha256':OLD_B/'EXECUTION_RESULT.json',
           'old_failed_checkpoint_sha256':OLD_B/'requests/857251ccc1e5593056fbf490ff87c569d31eb81d8b68aa151af03c8a544ecc4f.json',
           'input_manifest_sha256':HERE/'INPUT_MANIFEST.json',
           'input_ready_sha256':HERE/'GOV_CLOSEOUT_INPUT_READY.json',
           'au_plan_sha256':HERE/'AU_ORIGINAL_CHECK_PLAN.csv',
           'repair_ready_sha256':WP/'15_targeted_repairs_and_supplementation_20261004/control/REPAIR_READY.json'}
    return {'transport_version':VERSION,'transport_sha256':sha(Path(__file__)),
            'accepted_v3_sha256':V3_SHA,'frozen_b_manifest_sha256':B_SHA,
            'fixed_publication_interval':INTERVAL,'corrected_item_uri':FAILED_URI,
            'corrected_item_accept':'*/*','maximum_new_b_attempts':959,
            'unattempted_b_accept':'application/pdf','aggregate_government_raw_cap_bytes':2*GIB,
            'collector_floor_bytes':15*GIB,'au_maximum_raw_bytes':54*2**20,
            'maximum_au_requests':4,'au_original_unit_ids':[
                'doc:7c7006b4ea3168ebe548e229915d853b','doc:bc6340389c3977a04993b0a20f55bcca'],
            'old_hansard_stop_remains_effective':True,'old_b_406_one_corrected_validation_accepted':True,
            'b_and_au_are_independent_phases':True,'automatic_restart':False,
            **{k:sha(p) for k,p in paths.items()}}


def check_release(digest):
    require(digest and RELEASE.is_file() and not RELEASE.is_symlink(),'New coordinator continuation release required')
    require(sha(RELEASE)==digest,'Continuation release digest mismatch')
    release=load(RELEASE)
    require(release.get('ready') is True and release.get('issuer')=='coordinator'
            and release.get('status')=='accepted_gov_same_item_correction_and_au_bounded_checks','Release not coordinator acceptance')
    require(all(release.get(k)==v for k,v in expected_bindings().items()),'Continuation release binding mismatch')
    require(sha(OLD_HERE/'frozen_acquisition_manifest.csv')==B_SHA,'Frozen B manifest changed')
    require(load(HERE/'GOV_CLOSEOUT_INPUT_READY.json').get('ready') is True,'Closeout input not ready')
    require(release.get('authorized_phases')==['B_CORRECTED','AU_ORIGINALS'],'Unexpected phases')
    require(load(OLD_B/'PHASE_HTTP_STATE.json').get('halted') is True,'Historical B stop absent')
    require(load(OLD_A/'SHARED_HTTP_STATE.json').get('halted') is True,'Historical A stop absent')
    require(not any(active_cooldown(load(p)) for p in [OLD_A/'SHARED_HTTP_STATE.json',OLD_B/'PHASE_HTTP_STATE.json']),
            'Active inherited cooldown; cannot supersede')
    mod=old_runner()
    contract=mod.load_json(mod.CONTRACT)
    # Reuse the accepted targeted repair-run verification under the caller's lock.
    evidence=mod.validate_release(contract,release['repair_ready_sha256'])
    require(evidence['post_checkpoint']==release.get('post_checkpoint'),'Current repair checkpoint mismatch')
    return contract


def raw_roots():
    return [OLD_HERE/'raw',OLD_A/'raw',OLD_B/'raw',OUT/'B_CORRECTED/raw',OUT/'AU_ORIGINALS/raw']


def raw_accounting():
    paths=[]
    for root in raw_roots():
        require(not root.is_symlink(),'Raw root alias rejected')
        if root.exists():
            for p in sorted(root.rglob('*')):
                require(not p.is_symlink(),'Raw alias rejected')
                if p.is_file(): paths.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,
                                               'partial':p.name.endswith('.part')})
    return {'total_bytes':sum(p['bytes'] for p in paths),
            'partial_bytes':sum(p['bytes'] for p in paths if p['partial']), 'files':paths}


def budget(contract, next_bytes=0, reserve_remaining=False):
    b=contract['budget']; stored=raw_accounting()
    require(b['aggregate_new_raw_cap_bytes']==2*GIB and b['collector_floor_bytes']==15*GIB,'Frozen cap/floor changed')
    require(next_bytes>=0 and stored['total_bytes']+next_bytes<=2*GIB,'Shared A+B cap reached')
    transient=sum(b[k] for k in ['inflight_object_reserve_bytes','checkpoint_error_reserve_bytes','repair_other_activity_reserve_bytes'])
    free=shutil.disk_usage(HERE).free
    reserve=transient+(2*GIB-stored['total_bytes'] if reserve_remaining else next_bytes)
    require(free-reserve>15*GIB,'15 GiB floor plus original reserves reached')
    return {'free_bytes':free,'raw_bytes':stored['total_bytes'],'partial_bytes':stored['partial_bytes'],
            'reserve_bytes':reserve,'remaining_shared_raw_bytes':2*GIB-stored['total_bytes']}


@contextmanager
def locks():
    handles=[]
    try:
        for p in [HEAVY,OLD_HERE/'download.lock']:
            f=p.open('a+')
            try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BaseException: f.close(); raise
            handles.append(f)
        yield
    finally:
        for f in reversed(handles): fcntl.flock(f,fcntl.LOCK_UN); f.close()


def active_cooldown(state):
    return bool(state.get('retry_not_before_utc') and datetime.now(timezone.utc)<datetime.fromisoformat(state['retry_not_before_utc']))


def state_path(phase):
    require(phase in {'B_CORRECTED','AU_ORIGINALS'},'Unknown phase')
    return OUT/phase/'PHASE_HTTP_STATE.json'


def phase_state(phase):
    p=state_path(phase); s=load(p) if p.exists() else {}
    require(not s.get('halted') and not active_cooldown(s),'Persistent continuation stop/cooldown; no restart')
    return s


def request_start(phase):
    state=phase_state(phase); timestamps=[]
    for p in [OLD_A/'SHARED_HTTP_STATE.json',OLD_B/'PHASE_HTTP_STATE.json',OLD_A/'GLOBAL_REQUEST_SPACING.json',
              GLOBAL_STATE,state_path('B_CORRECTED'),state_path('AU_ORIGINALS')]:
        if p.exists():
            for k in ['last_request_started_utc','last_request_finished_utc']:
                if load(p).get(k): timestamps.append(datetime.fromisoformat(load(p)[k]))
    if timestamps:
        delay=2-(datetime.now(timezone.utc)-max(timestamps)).total_seconds()
        if delay>0: time.sleep(delay)
    state.update(last_request_started_utc=now(),request_count=state.get('request_count',0)+1)
    save(state_path(phase),state); save(GLOBAL_STATE,{'phase':phase,'last_request_started_utc':state['last_request_started_utc']})


def request_finish(phase,response=None,error=None):
    p=state_path(phase); state=load(p); state['last_request_finished_utc']=now()
    if response is not None:
        retry=response.headers.get('Retry-After')
        if retry or response.status_code==429:
            until=datetime.now(timezone.utc)+timedelta(hours=1)
            if retry:
                try:
                    until=(datetime.now(timezone.utc)+timedelta(seconds=int(retry)) if retry.isdigit()
                           else parsedate_to_datetime(retry).astimezone(timezone.utc))
                    until=max(until,datetime.now(timezone.utc))
                except (ValueError,TypeError,OverflowError): state['retry_after_parse_pending']=retry
            state.update(halted=True,retry_not_before_utc=until.isoformat(),stop_reason='Retry-After/429')
        elif response.status_code!=200: state.update(halted=True,stop_reason='HTTP '+str(response.status_code))
    if error: state.update(halted=True,stop_reason=error)
    save(p,state); save(GLOBAL_STATE,{'phase':phase,'last_request_finished_utc':state['last_request_finished_utc']})


def safety_stop(phase,error):
    p=state_path(phase);state=load(p) if p.exists() else {}
    state.update(halted=True,stop_reason=error,safety_stop_recorded_at_utc=now())
    save(p,state)


def check_pdf(path):
    with path.open('rb') as f: require(f.read(1024).lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'%PDF-'),'Non-PDF signature')


def fetch(row, contract, phase, release_digest, kind='pdf'):
    import requests
    check_release(release_digest); phase_state(phase)
    url=row['request_url']; parsed=urlsplit(url)
    require(parsed.scheme=='https' and not parsed.username and not parsed.password,'Invalid request URL')
    if phase=='B_CORRECTED':
        frozen={r['item_uri']:r for r in read_csv(OLD_HERE/'frozen_acquisition_manifest.csv')}
        source=frozen.get(row.get('item_uri'))
        require(source and all(row.get(k)==source[k] for k in ['parent_id','expression_uri','manifestation_uri','item_uri',
                  'publication_dates','request_url','format','staging_path','max_object_bytes']),'Changed or sibling Item forbidden')
        require(parsed.hostname=='publications.europa.eu' and kind=='pdf','B route expansion rejected')
        headers={'User-Agent':'FearTemperatureResearch/1.0 (public academic source acquisition)',
                 'Accept':'*/*' if row['item_uri']==FAILED_URI else 'application/pdf','Accept-Encoding':'identity'}
    else:
        plans=read_csv(HERE/'AU_ORIGINAL_CHECK_PLAN.csv')
        require(any(row.get('unit_id')==r['unit_id'] and url==(r['landing_url'] if kind=='html' else r['candidate_pdf_url']) for r in plans),
                'AU target expansion rejected')
        require(parsed.hostname=='www.dcceew.gov.au','AU host expansion rejected')
        require(int(row['max_object_bytes'])==(2*2**20 if kind=='html' else 25*2**20),'AU object cap changed')
        headers={'User-Agent':'FearTemperatureResearch/1.0 (public academic source acquisition)',
                 'Accept':'application/pdf' if kind=='pdf' else 'text/html','Accept-Encoding':'identity'}
    directory=OUT/phase
    key=hashlib.sha256(url.encode()).hexdigest(); cp=directory/'requests'/f'{key}.json'
    path=directory/row['staging_path']; part=path.with_name(path.name+'.part')
    require(path.resolve().is_relative_to((directory/'raw').resolve()),'Output escaped raw root')
    require(not cp.exists() and not path.exists() and not part.exists(),'Existing attempt/raw/partial: no retry or overwrite')
    maximum=int(row['max_object_bytes']); budget(contract,maximum)
    path.parent.mkdir(parents=True,exist_ok=True)
    meta={k:row[k] for k in ['unit_id','parent_id','expression_uri','manifestation_uri','item_uri','publication_dates','format'] if k in row}
    meta.update(request_url=url,request_headers=headers,phase=phase,status='attempt_in_progress',requested_at_utc=now(),
                byte_count=0,raw_path='',sha256='',historical_version_equivalence='unknown')
    save(cp,meta); response=None; attempted=False
    try:
        request_start(phase); attempted=True
        response=requests.get(url,headers=headers,stream=True,allow_redirects=False,timeout=(15,90))
        meta.update(http_status=response.status_code,final_url=response.url,response_headers={k:v for k,v in response.headers.items()
              if k.lower() in {'date','content-type','content-length','content-encoding','etag','last-modified','retry-after','location','content-disposition'}})
        request_finish(phase,response)
        require(response.status_code==200 and response.url==url,'Non-200 or changed Item route; no follow-up request')
        require(not response.headers.get('Retry-After'),'Retry-After present')
        mime=response.headers.get('Content-Type','').split(';')[0].lower().strip()
        require(mime in ({'application/pdf','application/octet-stream'} if kind=='pdf' else {'text/html','application/xhtml+xml'}),
                'Unexpected content type; wildcard Accept does not waive PDF validation')
        require(response.headers.get('Content-Encoding','identity').lower() in {'','identity'},'Encoded stream rejected')
        length=response.headers.get('Content-Length')
        require(length is None or (length.isdigit() and 0<int(length)<=maximum),'Invalid or oversized Content-Length')
        with part.open('xb') as f:
            for chunk in response.iter_content(65536):
                if not chunk: continue
                require(meta['byte_count']+len(chunk)<=maximum,'Object cap reached'); budget(contract,len(chunk))
                f.write(chunk); f.flush(); meta['byte_count']+=len(chunk)
        require(meta['byte_count']>0 and (length is None or int(length)==meta['byte_count']),'Empty/truncated body')
        if kind=='pdf': check_pdf(part)
        else:
            with part.open('rb') as f: prefix=f.read(1024).lower()
            require(b'<html' in prefix or b'<!doctype html' in prefix,'Non-HTML landing')
        os.link(part,path); part.unlink()
        meta.update(status='downloaded_candidate_original',raw_path=str(path.relative_to(ROOT)),sha256=sha(path),retrieved_at_utc=now())
    except Exception as e:
        meta.update(status='failed',error=type(e).__name__+': '+str(e)[:400])
        if part.exists(): meta.update(partial_path=str(part.relative_to(ROOT)),partial_sha256=sha(part),byte_count=part.stat().st_size)
        if attempted: request_finish(phase,error=meta['error'])
    finally:
        if response is not None: response.close()
        save(cp,meta)
    return meta


class Links(HTMLParser):
    def __init__(self): super().__init__(); self.hrefs=[]
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.hrefs.extend(v for k,v in attrs if k=='href' and v)


def execute_b(contract,digest):
    rows=read_csv(OLD_HERE/'frozen_acquisition_manifest.csv')
    require(sha(OLD_HERE/'frozen_acquisition_manifest.csv')==B_SHA and len(rows)==979,'Frozen queue mismatch')
    ledger=read_csv(OLD_B/'B_STATUS_LEDGER.csv'); by={r['item_uri']:r for r in ledger}
    require(len(by)==979,'Prior B ledger incomplete')
    reused=[]; queued=[]
    for r in rows:
        old=by[r['item_uri']]
        if old['status']=='downloaded_candidate_original':
            mod=old_runner(); result=mod.verified_reuse(r,ROOT/old['raw_path'],ROOT/old['checkpoint_path'])
            reused.append({**r,**result})
        else: queued.append(r)
    require(len(reused)==20 and len(queued)==959 and queued[0]['item_uri']==FAILED_URI,'Unexpected continuation queue')
    require(by[FAILED_URI]['status']=='failed' and all(by[r['item_uri']]['status']=='not_attempted_after_stop' for r in queued[1:]),
            'Only named 406 and never-requested frozen Items allowed')
    outcomes=list(reused)
    for r in queued:
        try: result=fetch(r,contract,'B_CORRECTED',digest)
        except Exception as e:
            result={'status':'stopped_pre_request_safety','error':type(e).__name__+': '+str(e)[:400],'HTTP_attempted':False}
            safety_stop('B_CORRECTED',result['error'])
        outcomes.append({**r,**result})
        if result['status']!='downloaded_candidate_original': break
    reached={r['item_uri'] for r in outcomes}
    outcomes.extend({**r,'status':'not_attempted_after_stop'} for r in rows if r['item_uri'] not in reached)
    save(OUT/'B_CORRECTED/RESULT.json',{'finished_at_utc':now(),'frozen_targets':979,'verified_reused_items':20,
         'new_successes':sum(r['status']=='downloaded_candidate_original' for r in outcomes),
         'complete_frozen_item_queue':all(r['status'] in {'verified_local_reuse','downloaded_candidate_original'} for r in outcomes),
         'outcomes':outcomes,'raw_accounting':raw_accounting(),'complete_works_verified':False,'formal_database_writes':0})


def execute_au(contract,digest):
    plans=read_csv(HERE/'AU_ORIGINAL_CHECK_PLAN.csv'); outcomes=[]
    require(len(plans)==2 and {r['unit_id'] for r in plans}=={
        'doc:7c7006b4ea3168ebe548e229915d853b','doc:bc6340389c3977a04993b0a20f55bcca'},'Final two AU targets changed')
    for r in plans:
        key=hashlib.sha256(r['unit_id'].encode()).hexdigest()
        landing={'unit_id':r['unit_id'],'parent_id':r['unit_id'],'request_url':r['landing_url'],
                 'staging_path':f'raw/{key}.html','max_object_bytes':str(2*2**20)}
        try: result=fetch(landing,contract,'AU_ORIGINALS',digest,kind='html')
        except Exception as e:
            result={'unit_id':r['unit_id'],'status':'stopped_pre_request_safety','error':type(e).__name__+': '+str(e)[:400],'HTTP_attempted':False}
            safety_stop('AU_ORIGINALS',result['error'])
        outcomes.append(result)
        if result['status']!='downloaded_candidate_original': break
        parser=Links(); parser.feed((ROOT/result['raw_path']).read_text(errors='replace'))
        if r['candidate_pdf_url'] not in {urljoin(r['landing_url'],u) for u in parser.hrefs}:
            outcomes.append({'unit_id':r['unit_id'],'status':'primary_link_unconfirmed_no_pdf_request'}); continue
        pdf={**landing,'request_url':r['candidate_pdf_url'],'staging_path':f'raw/{key}.pdf','max_object_bytes':str(25*2**20)}
        try: result=fetch(pdf,contract,'AU_ORIGINALS',digest)
        except Exception as e:
            result={'unit_id':r['unit_id'],'status':'stopped_pre_request_safety','error':type(e).__name__+': '+str(e)[:400],'HTTP_attempted':False}
            safety_stop('AU_ORIGINALS',result['error'])
        outcomes.append(result)
        if result['status']!='downloaded_candidate_original': break
    save(OUT/'AU_ORIGINALS/RESULT.json',{'finished_at_utc':now(),'outcomes':outcomes,'maximum_http_requests':4,
         'issue_date_identity_author_publisher_validation':'pending saved-original check; CMS is not issue date',
         'raw_accounting':raw_accounting(),'formal_database_writes':0})


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--execute',action='store_true')
    parser.add_argument('--release-sha256',default=''); args=parser.parse_args()
    if not args.execute:
        print(json.dumps({'version':VERSION,'status':'offline_proposal_only','network_requests':0,
              'new_release_required':True,'release_path':str(RELEASE.relative_to(ROOT))})); return
    with locks():
        contract=check_release(args.release_sha256); budget(contract,reserve_remaining=True)
        # Reject any prior attempted continuation before executing either phase.
        require(not (OUT/'B_CORRECTED/requests').exists() and not (OUT/'AU_ORIGINALS/requests').exists(),
                'Continuation already attempted; only local reconciliation allowed')
        phase_state('B_CORRECTED'); phase_state('AU_ORIGINALS')
        execute_b(contract,args.release_sha256)
        # The explicitly accepted phase separation permits AU after a B stop.
        execute_au(contract,args.release_sha256)


if __name__=='__main__': main()
