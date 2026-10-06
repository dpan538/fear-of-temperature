"""Package24 bounded resource/transport and changed-unit staging; no old DB writes."""
import datetime as dt
import fcntl
import hashlib
import json
import shutil
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit,urljoin
import requests

OWN=Path(__file__).resolve().parent
REPO=OWN.parents[3]
BASE=REPO/'work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/transition_research/acquisition_followthrough_20261005'
OLD=BASE.parents[1]/'newspaper'
SCOPE=json.loads((OWN.parent/'control/EXECUTION_SCOPE.json').read_text())
LOCK=REPO/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
DEADLINE=dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
UA='FearOfTemperatureResearch/1.0 (bounded public newspaper acquisition)'

def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def save(name,value):
    p=OWN/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2)+'\n')
def rows(name):
    p=OWN/name
    return [json.loads(x) for x in p.read_text().splitlines() if x] if p.exists() else []
def append(name,value):
    with (OWN/name).open('a') as f:f.write(json.dumps(value)+'\n')
def cumulative():
    return SCOPE['prior_media_bytes']+sum(p.stat().st_size for root in SCOPE['media_lifetime_accounting_roots'] for p in (REPO/root).rglob('*') if p.is_file())
def preflight(raw_cap=0,derived_cap=0):
    used=cumulative();free=shutil.disk_usage(OWN).free
    # No active worker lease is declared in the coordinator's execution controls;
    # shared mutex serializes this material operation. New declared leases add here.
    coord=json.loads((OWN.parent/'control/COORDINATION.json').read_text())
    leases=sum(x['reserved_bytes'] for x in coord.get('active_leases',[]) if x.get('active',True))
    pending=raw_cap+derived_cap+65536
    projected=free-SCOPE['physical_floor_bytes']-SCOPE['recovery_allowance_bytes']-leases-pending
    allocation_left=SCOPE['media_lifetime_cap_bytes']-used-pending
    return dict(at_utc=utc(),free_bytes=free,cumulative_media_bytes=used,lifetime_cap_bytes=SCOPE['media_lifetime_cap_bytes'],
        original_combined_reserve_bytes=0,physical_floor_bytes=SCOPE['physical_floor_bytes'],recovery_allowance_bytes=SCOPE['recovery_allowance_bytes'],
        active_lease_bytes=leases,active_lease_basis='current named coordinator controls; no unreported lease assumed',raw_cap_bytes=raw_cap,derived_cap_bytes=derived_cap,
        pending_receipt_allowance_bytes=65536,physical_headroom_after_pending_bytes=projected,allocation_headroom_after_pending_bytes=allocation_left,
        passed=projected>=0 and allocation_left>=0,limiting_constraint='physical_floor_or_lease' if projected<0 else 'cumulative_media_allocation' if allocation_left<0 else None)
def material_check(size):
    b=preflight(0,size)
    if not b['passed']:raise RuntimeError(json.dumps(b))
    return b
def eligible(day):
    try:return dt.date.fromisoformat(day).isoformat()==day and SCOPE['publication_interval'][0]<=day<=SCOPE['publication_interval'][1]
    except (ValueError,TypeError):return False
def charge_state():
    p=OWN/'TRANSPORT_STATE.json'
    return json.loads(p.read_text()) if p.exists() else {'strata':{s:{'discovery':0,'article':0} for s in SCOPE['strata']},'hosts':{},'access_stops':{}}
def old_stops():
    return {r['url']:r for r in [json.loads(x) for x in (BASE/'REQUESTS.jsonl').read_text().splitlines()] if r['status'] not in {'saved'}}

def fetch(target):
    """Target frozen in own TARGETS; saved exact requests never refetch or retry."""
    rid=digest((target['source_id']+'|'+target['purpose']+'|'+target['url']).encode())[:24]
    previous=next((r for r in rows('REQUESTS.jsonl') if r['request_id']==rid),None)
    if previous:return previous
    checkpoint=json.loads((OWN/'EXECUTION_CHECKPOINT.json').read_text())
    if not checkpoint['offline_checks_passed']:raise RuntimeError('Offline gate missing')
    for name,h in checkpoint['code_digests'].items():
        if sha(OWN/name)!=h:raise RuntimeError('Checkpoint code changed: '+name)
    if sha(OWN.parent/'PLAN.md')!=checkpoint['plan_sha256'] or sha(OWN.parent/'control/EXECUTION_SCOPE.json')!=checkpoint['scope_sha256']:raise RuntimeError('Release changed')
    frame=json.loads((OWN/target['frame_path']).read_text())
    if frame['target']!=target:raise RuntimeError('Native target freeze differs')
    if target['url'] in old_stops():raise RuntimeError('Preserved exact old target stop')
    if target.get('access_cleared') is not True:raise RuntimeError('Applicable public-route evidence missing')
    category='article' if target['purpose']=='article' else 'discovery'
    cap=target.get('raw_cap_bytes',SCOPE['default_object_cap_bytes'])
    if cap>SCOPE['default_object_cap_bytes'] and not target.get('explicit_large_footprint'):raise RuntimeError('No released named large-object conditions')
    with LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        receipt=dict(request_id=rid,target=target,url=target['url'],source_id=target['source_id'],stratum=target['stratum'],purpose=target['purpose'],
            requested_at_utc=utc(),code_sha256=sha(__file__),frame_sha256=sha(OWN/target['frame_path']),status='not_started',hops=[],charged_attempts=0,raw_bytes=0,partial=False)
        part=OWN/'raw'/(rid+'.part');part.parent.mkdir(exist_ok=True)
        state=charge_state();entry=state['strata'][target['stratum']]
        try:
            budget=preflight(cap,3*cap);receipt['budget_before']=budget
            if not budget['passed']:
                receipt['status']='resource_stop';return receipt
            session=requests.Session();session.trust_env=False;session.headers.update({'User-Agent':UA})
            current=target['url']
            for i in range(4):
                if dt.datetime.now(dt.timezone.utc)>=DEADLINE:raise RuntimeError('Fixed deadline reached')
                parts=urlsplit(current);host=parts.hostname
                if parts.scheme!='https' or host not in target['public_hosts']:raise RuntimeError('Outside frozen public hosts')
                if host in state['access_stops']:raise RuntimeError('Preserved host refusal/cooldown')
                limit=SCOPE['article_transfers_per_stratum'] if category=='article' else SCOPE['discovery_operations_per_stratum']
                if entry[category]>=limit:raise RuntimeError('Geographic allowance reached')
                wait=max(2,target.get('minimum_interval_seconds',2))-(time.time()-state['hosts'].get(host,0))
                if wait>60:raise RuntimeError('Published cooldown needs later cursor')
                if wait>0:time.sleep(wait)
                if dt.datetime.now(dt.timezone.utc)>=DEADLINE:raise RuntimeError('Fixed deadline reached')
                entry[category]+=1;receipt['charged_attempts']+=1;state['hosts'][host]=time.time();save('TRANSPORT_STATE.json',state)
                session.cookies.clear()
                r=session.get(current,allow_redirects=False,stream=True,timeout=(10,20))
                receipt['hops'].append(dict(url=current,status=r.status_code,location=r.headers.get('Location'),at_utc=utc()))
                if r.status_code in {301,302,303,307,308} and r.headers.get('Location'):
                    current=urljoin(current,r.headers['Location']);r.close();continue
                receipt.update(http_status=r.status_code,content_type=r.headers.get('Content-Type'),last_modified=r.headers.get('Last-Modified'),response_date=r.headers.get('Date'),final_url=current,retry_after=r.headers.get('Retry-After'))
                if r.status_code!=200:
                    receipt['status']='http_stop'
                    if r.status_code in {401,403,429}:state['access_stops'][host]={'url':current,'status':r.status_code,'retry_after':r.headers.get('Retry-After')};save('TRANSPORT_STATE.json',state)
                    r.close();break
                with part.open('wb') as out:
                    for chunk in r.iter_content(16384):
                        if dt.datetime.now(dt.timezone.utc)>=DEADLINE:raise RuntimeError('Fixed deadline reached')
                        n=min(len(chunk),cap-receipt['raw_bytes']);out.write(chunk[:n]);receipt['raw_bytes']+=n
                        if n<len(chunk):receipt.update(partial=True,status='object_cap_stop');break
                r.close()
                if not receipt['partial']:
                    raw=part.with_suffix('.bin');part.replace(raw);receipt['status']='saved'
                else:raw=part
                receipt.update(raw_path=str(raw.relative_to(OWN)),raw_sha256=sha(raw));break
            else:receipt['status']='redirect_cap_stop'
        except Exception as e:
            receipt.update(status='transport_error',error=type(e).__name__+': '+str(e))
            if part.exists():receipt.update(raw_path=str(part.relative_to(OWN)),raw_bytes=part.stat().st_size,raw_sha256=sha(part),partial=True)
        finally:
            receipt['finished_at_utc']=utc();append('REQUESTS.jsonl',receipt)
        return receipt

def freeze_target(source_id,stratum,url,purpose,evidence,hosts,month=None,cap=None):
    rid=digest((source_id+'|'+purpose+'|'+url).encode())[:24]
    target=dict(source_id=source_id,stratum=stratum,url=url,purpose=purpose,native_evidence=evidence,public_hosts=hosts,
                month=month,access_cleared=True,raw_cap_bytes=cap or SCOPE['default_object_cap_bytes'],frame_path='targets/'+rid+'.json')
    p=OWN/target['frame_path']
    if p.exists():
        prior=json.loads(p.read_text())
        if prior['target']!=target:raise RuntimeError('Do not replace frozen target')
    else:save(target['frame_path'],{'frozen_at_utc':utc(),'native_order_selection':'first declared unit for previously missing month; remaining frontier retained','target':target,'code_sha256':sha(__file__)})
    return target

def stage(record,interrupt=False):
    """One changed-unit writer; parent metadata conflicts do not silently reassign."""
    with LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        material_check(len(json.dumps(record).encode())*3+262144)
        con=sqlite3.connect(OWN/'staging.sqlite3')
        con.execute('PRAGMA journal_mode=WAL');con.execute('PRAGMA synchronous=FULL')
        con.executescript('CREATE TABLE IF NOT EXISTS units(unit_id TEXT PRIMARY KEY,source_id TEXT,stratum TEXT,publication_date TEXT,title TEXT,unit_kind TEXT);CREATE TABLE IF NOT EXISTS versions(unit_id TEXT,raw_sha TEXT,body_sha TEXT,record_json TEXT,PRIMARY KEY(unit_id,raw_sha,body_sha));CREATE TABLE IF NOT EXISTS cursors(source_id TEXT PRIMARY KEY,cursor_json TEXT);')
        try:
            con.execute('BEGIN IMMEDIATE')
            fields=tuple(record[k] for k in ['unit_id','source_id','stratum','publication_date','title','unit_kind'])
            old=con.execute('SELECT * FROM units WHERE unit_id=?',(record['unit_id'],)).fetchone()
            if old and old!=fields:raise ValueError('Parent identity/date/title conflict')
            con.execute('INSERT OR IGNORE INTO units VALUES(?,?,?,?,?,?)',fields)
            c=con.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?)',(record['unit_id'],record['raw_sha256'],record['body_sha256'],json.dumps(record)))
            added=c.rowcount
            if interrupt:raise RuntimeError('Injected interruption')
            con.execute('INSERT OR REPLACE INTO cursors VALUES(?,?)',(record['source_id'],json.dumps({'last_unit':record['unit_id'],'month':record['publication_date'][:7],'updated_at_utc':utc()})))
            con.commit();return added
        except Exception:con.rollback();raise
        finally:con.close()
