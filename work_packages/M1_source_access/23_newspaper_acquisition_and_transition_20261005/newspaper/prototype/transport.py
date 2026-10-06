"""Bounded public transport. No production route is enabled by this module alone.

Every index/body download requires passing storage and a recorded public-route gate.
Policy documents are compact source preparation, never substituted for corpus payloads.
No retries, credentials, cookies, hidden API discovery, reserve relaxation or quota transfer.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import fcntl
import hashlib
import json
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit, urljoin
import requests

OWN = Path(__file__).resolve().parents[1]
# Locate by fixed repository-relative marker, rather than depend on launch CWD.
REPO = next(p for p in OWN.parents if (p/'AGENTS.md').exists())
SCOPE = json.loads((OWN.parent/'control/SCOPE.json').read_text())
DEADLINE = dt.datetime.fromisoformat(SCOPE['network_deadline_utc'])
HEAVY_LOCK = REPO/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
OVERHEAD = 48 * 1024 * 1024
UA = 'FearOfTemperatureResearch/1.0 (public newspaper source preparation)'

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def corpus_bytes():
    # Conservative: count all own-package files, including policies, metadata,
    # code and SQLite/WAL. This is wider than just corpus-bearing copies.
    return sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file())

def preflight(prospective=SCOPE['default_object_cap_bytes']):
    free = shutil.disk_usage(OWN).free
    used = SCOPE['accepted_media_prior_bytes'] + corpus_bytes()
    projected = free-SCOPE['original_remaining_reserve_bytes_snapshot']-OVERHEAD-prospective
    # Raw + up to three bytes of UTF-8 derivative per source byte + record growth.
    # Stop before fetching if retained copies would exhaust the lifetime ceiling.
    pending_copies = 3*prospective+65536
    return {'at_utc':utc(),'free_bytes':free,
            'original_remaining_reserve_bytes':SCOPE['original_remaining_reserve_bytes_snapshot'],
            'additional_staging_WAL_recovery_reserve_bytes':OVERHEAD,'prospective_bytes':prospective,
            'media_lifetime_bytes':used,'media_lifetime_cap_bytes':SCOPE['media_lifetime_cap_bytes'],
            'pending_derivative_and_record_cap_bytes':pending_copies,
            'floor_bytes':SCOPE['minimum_free_floor_bytes'],'projected_free_after_all_reserves':projected,
            'passed':projected>=SCOPE['minimum_free_floor_bytes'] and used+prospective+pending_copies<=SCOPE['media_lifetime_cap_bytes']}

def deadline_check():
    if dt.datetime.now(dt.timezone.utc) >= DEADLINE:
        raise RuntimeError('Hard network deadline reached')

def read_state():
    path=OWN/'control/TRANSPORT_STATE.json'
    return json.loads(path.read_text()) if path.exists() else {'titles':{},'hosts':{}}

def save_state(state):
    path=OWN/'control/TRANSPORT_STATE.json'
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state,indent=2)+'\n')
    tmp.replace(path)

def fetch(source_id, url, purpose, gate, *, request_version='initial',previous_request_id=None,recovery_reason=None):
    """gate must be a reviewed own-package record, not caller-assumed API readiness.

    The gate declares allowed public hosts, robots/rights evidence and absence of
    a prior exact-route prohibition/cooldown. Unknown access remains a stop.
    """
    if purpose not in {'policy','index','article'}:
        raise ValueError('Unsupported request purpose')
    if not request_version.replace('_','').replace('-','').isalnum():raise ValueError('Unsafe request version')
    gate_path=Path(gate).resolve()
    if OWN not in gate_path.parents:
        raise ValueError('Gate must belong to this newspaper package')
    g=json.loads(gate_path.read_text())
    if g['source_id']!=source_id or g.get('access_state')!='public_route_permitted':
        raise RuntimeError('Public route is not cleared')
    if purpose!='policy' and not g.get('changed_parser_validated'):
        raise RuntimeError('Changed parser validation missing')
    cap = 128*1024 if purpose=='policy' else SCOPE['default_object_cap_bytes']
    metadata=purpose!='article'
    rid=hashlib.sha256((source_id+'|'+purpose+'|'+url+'|'+request_version).encode()).hexdigest()[:24]
    directory=OWN/('policies' if purpose=='policy' else 'raw')
    directory.mkdir(parents=True,exist_ok=True)
    receipts=OWN/'requests'; receipts.mkdir(exist_ok=True)
    previous=None
    if request_version!='initial':
        if not previous_request_id or not recovery_reason:raise ValueError('A recovery requires its preserved prior receipt and concrete reason')
        if len(previous_request_id)!=24 or any(c not in '0123456789abcdef' for c in previous_request_id):raise ValueError('Invalid prior receipt identifier')
        previous_path=receipts/(previous_request_id+'.json')
        previous=json.loads(previous_path.read_text())
        if any(previous[k]!=v for k,v in [('source_id',source_id),('url',url),('purpose',purpose)]):
            raise ValueError('Recovery must retain the same selected source/URL/purpose')
    receipt_path=receipts/(rid+'.json')
    if receipt_path.exists():
        return json.loads(receipt_path.read_text()) # Exact stopped/saved request does not silently retry.
    receipt={'request_id':rid,'source_id':source_id,'url':url,'purpose':purpose,
             'requested_at_utc':utc(),'transport_sha256':sha(__file__),
             'gate_sha256':sha(gate_path),'scope_sha256':sha(OWN.parent/'control/SCOPE.json'),
             'request_version':request_version,'previous_request_id':previous_request_id,
             'recovery_reason':recovery_reason,
             'previous_receipt_sha256':sha(previous_path) if previous else None,
             'hops':[],'charged_attempts':0,'status':'not_started','byte_count':0,'partial':False,'publisher_denial':False}
    part=directory/(rid+'.part')
    raw=directory/(rid+'.bin')
    with HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            deadline_check()
            budget=preflight(cap)
            receipt['budget_before']=budget
            if purpose!='policy' and not budget['passed']:
                receipt['status']='storage_blocked'
                return receipt
            # Compact policy preparation still preserves the physical floor.
            if purpose=='policy' and budget['free_bytes']-cap<SCOPE['minimum_free_floor_bytes']:
                receipt['status']='physical_floor_blocked'
                return receipt
            state=read_state()
            entry=state['titles'].setdefault(source_id,{'metadata':0,'body':0,'search':0})
            if entry.get('access_stop') or time.time()<entry.get('cooldown_until',0):
                raise RuntimeError('Recorded source refusal/cooldown remains active')
            session=requests.Session(); session.trust_env=False
            session.headers.update({'User-Agent':UA})
            current=url
            for _ in range(4):
                deadline_check()
                host=urlsplit(current).hostname
                if host in entry.get('stopped_hosts',{}):raise RuntimeError('Preserved host-specific access stop remains active')
                if host not in g['public_hosts'] or urlsplit(current).scheme!='https':
                    raise RuntimeError('Redirect/URL is outside the declared public hosts')
                if metadata and entry['metadata']>=SCOPE['metadata_requests_per_title_cap']:
                    raise RuntimeError('Metadata request cap reached')
                wait=max(2,g.get('minimum_interval_seconds',2))- (time.time()-state['hosts'].get(host,0))
                if wait>60:
                    receipt.update(status='rate_wait_deferred',resume_not_before_utc=dt.datetime.fromtimestamp(time.time()+wait,dt.timezone.utc).isoformat())
                    break
                if wait>0:
                    time.sleep(wait)
                deadline_check()
                entry['metadata' if metadata else 'body']+=1
                receipt['charged_attempts']+=1
                state['hosts'][host]=time.time(); save_state(state)
                # Each redirect is a separately charged request; no automatic retries.
                session.cookies.clear()
                response=session.get(current,allow_redirects=False,stream=True,timeout=(10,20))
                location=response.headers.get('Location')
                receipt['hops'].append({'url':current,'status':response.status_code,'location':location,
                    'Retry-After':response.headers.get('Retry-After'),'at_utc':utc()})
                if response.status_code in {301,302,303,307,308} and location:
                    current=urljoin(current,location); response.close(); continue
                receipt['http_status']=response.status_code
                receipt['mime_type']=response.headers.get('Content-Type')
                receipt['final_url']=current
                receipt['response_date']=response.headers.get('Date')
                receipt['last_modified']=response.headers.get('Last-Modified')
                receipt['Retry-After']=response.headers.get('Retry-After')
                if response.status_code!=200:
                    receipt['status']='http_stop'
                    receipt['publisher_denial']=response.status_code in {401,403,429}
                    if response.status_code in {401,403}:
                        entry['access_stop']={'http_status':response.status_code,'url':current}
                    if response.status_code==429:
                        value=response.headers.get('Retry-After')
                        try:
                            until=time.time()+float(value)
                        except (TypeError,ValueError):
                            try:
                                until=email.utils.parsedate_to_datetime(value).timestamp()
                            except (TypeError,ValueError):
                                # Unknown cooldown does not authorise a retry on a new URL.
                                entry['access_stop']={'http_status':429,'url':current,'cooldown':'unknown'}
                                until=0
                        entry['cooldown_until']=until
                    save_state(state)
                    response.close(); break
                with part.open('wb') as out:
                    for chunk in response.iter_content(16384):
                        deadline_check()
                        available=cap-receipt['byte_count']
                        out.write(chunk[:available]); receipt['byte_count']+=min(len(chunk),available)
                        if len(chunk)>available:
                            receipt['partial']=True; receipt['status']='object_cap_stop'; break
                response.close()
                if not receipt['partial']:
                    part.replace(raw); receipt['status']='saved'
                kept=part if part.exists() else raw
                receipt['raw_path']=str(kept.relative_to(OWN))
                receipt['raw_sha256']=sha(kept)
                break
            else:
                receipt['status']='redirect_cap_stop'
        except Exception as exc:
            receipt['status']='transport_error'
            receipt['error']=type(exc).__name__+': '+str(exc)
            if part.exists():
                receipt.update(partial=True,byte_count=part.stat().st_size,
                               raw_path=str(part.relative_to(OWN)),raw_sha256=sha(part))
        finally:
            receipt['finished_at_utc']=utc()
            receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
