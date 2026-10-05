"""Stage only the frozen B Item manifest; never write a formal database.

Default: no-download preflight. --execute additionally requires the SHA256 of
the Task3 release reviewed for actual committed/checked before-after evidence.
The hash binds that review, and is not a substitute for reviewing the release.
Unrecognised release semantics fail closed rather than guessing readiness.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import shutil
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONTRACT = HERE/'ACQUISITION_CONTRACT.json'
GIB = 2**30


def now():
    return datetime.now(timezone.utc).isoformat()


def hash_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def walk(value, prefix=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, prefix+'.'+key)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child, prefix)
    else:
        yield prefix.lower(), value


def release_check(contract, expected_sha):
    marker = ROOT/contract['repair_release_path']
    if not marker.exists():
        return False, 'waiting_on_repair', {}
    digest = hash_file(marker)
    if not expected_sha or digest != expected_sha:
        return False, 'reviewed_committed_release_digest_required', {'marker_sha256':digest}
    data = json.loads(marker.read_text())
    leaves = list(walk(data))
    bad = any((('staged_only' in key or 'storage_blocked' in key) and value is True)
              or (isinstance(value,str) and value.lower() in {'staged_only','blocked_storage','storage_blocked'})
              for key,value in leaves)
    committed = any('committed' in key and (value is True or value == 'committed') for key,value in leaves)
    checked = any(('checked' in key or 'verified' in key or 'validation' in key)
                  and (value is True or value in ['passed','checked','verified','complete']) for key,value in leaves)
    before = any('before' in key and ('checkpoint' in key or 'snapshot' in key) for key,value in leaves)
    after = any('after' in key and ('checkpoint' in key or 'snapshot' in key) for key,value in leaves)
    request_paths=[]
    for key,value in leaves:
        if isinstance(value,str) and value.endswith('.csv') and 'request' in (key+value).lower():
            candidate=Path(value)
            candidate=candidate if candidate.is_absolute() else ROOT/candidate
            if candidate.is_file() and '03_existing_data_repair' in str(candidate):
                request_paths.append(str(candidate))
    if bad or not (committed and checked and before and after and request_paths):
        return False, 'release_content_not_recognised_as_committed_checked_checkpoint_with_request_paths', {
            'marker_sha256':digest,'committed_assertion':committed,'checked_assertion':checked,
            'before_checkpoint_fields':before,'after_checkpoint_fields':after,'request_paths':request_paths}
    return True, 'released', {'marker_sha256':digest,'request_paths':request_paths,
                              'request_manifest_sha256':{p:hash_file(Path(p)) for p in request_paths}}


def preflight(contract, expected_sha):
    budget=contract['budget']
    free=shutil.disk_usage(HERE).free
    reserve=sum(budget[k] for k in ['aggregate_new_raw_cap_bytes','inflight_object_reserve_bytes',
                                   'checkpoint_error_reserve_bytes','repair_other_activity_reserve_bytes'])
    storage_ok=free-reserve>budget['collector_floor_bytes']
    repair_ok,reason,evidence=release_check(contract,expected_sha)
    return {'checked_at_utc':now(),'status':reason if not repair_ok else ('ready' if storage_ok else 'blocked_storage'),
            'repair_gate_passes':repair_ok,'release_evidence':evidence,'storage_gate_passes':storage_ok,
            'free_bytes':free,'free_gib':free/GIB,'projected_remaining_gib':(free-reserve)/GIB,
            'floor_bytes':budget['collector_floor_bytes'],'reserve_bytes':reserve,'downloads_started':False}


def stream_one(row, contract):
    import requests
    path=HERE/row['staging_path']
    path.parent.mkdir(parents=True,exist_ok=True)
    checkpoint=path.with_suffix('.request.json')
    attempts=path.with_suffix('.attempts.jsonl')
    prior=json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    retry=prior.get('retry_not_before_utc')
    if retry and datetime.now(timezone.utc)<datetime.fromisoformat(retry):
        raise RuntimeError('Checkpointed cooldown has not elapsed')
    if prior:
        with attempts.open('a') as handle:
            handle.write(json.dumps(prior)+'\n')
    # Preserve failed partial bytes under their own attempt timestamp.
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    part=path.with_name(path.name+'.'+stamp+'.part')
    meta={'parent_id':row['parent_id'],'item_uri':row['item_uri'],'expression_uri':row['expression_uri'],
          'manifestation_uri':row['manifestation_uri'],'publication_dates':row['publication_dates'],
          'request_url':row['request_url'],'requested_at_utc':now(),'byte_count':0,'http_status':0,
          'raw_path':'','sha256':'','status':'failed','body_verification':'identity/date/content boundary pending',
          'rights_status':row['rights_access'],'format':row['format']}
    digest=hashlib.sha256()
    try:
        headers={'User-Agent':'FearTemperatureResearch/1.0 (public academic source acquisition)',
                 'Accept':'application/pdf','Accept-Language':'eng','Accept-Max-Cs-Size':row['max_object_bytes']}
        with requests.get(row['request_url'],headers=headers,stream=True,timeout=(15,90)) as response:
            meta.update(http_status=response.status_code,final_url=response.url,
                        response_headers={k:v for k,v in response.headers.items() if k.lower() in
                                          {'date','content-type','content-length','etag','last-modified','retry-after','content-disposition'}})
            retry=response.headers.get('Retry-After')
            if retry:
                try:
                    base=parsedate_to_datetime(response.headers['Date']) if response.headers.get('Date') else datetime.now(timezone.utc)
                    until=base+timedelta(seconds=int(retry)) if retry.isdigit() else parsedate_to_datetime(retry)
                    meta['retry_not_before_utc']=until.astimezone(timezone.utc).isoformat()
                except (ValueError,TypeError):
                    meta['retry_after_parse_pending']=retry
            if response.status_code==429 and not retry:
                meta['retry_not_before_utc']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
            if response.status_code!=200:
                raise RuntimeError('HTTP '+str(response.status_code)+'; stop without alternate route')
            if int(response.headers.get('Content-Length','0'))>int(row['max_object_bytes']):
                raise RuntimeError('Content-Length exceeds frozen object cap')
            with part.open('wb') as handle:
                for chunk in response.iter_content(65536):
                    if meta['byte_count']+len(chunk)>int(row['max_object_bytes']):
                        raise RuntimeError('Stream exceeds frozen object cap')
                    if shutil.disk_usage(HERE).free-len(chunk)<=contract['budget']['collector_floor_bytes']:
                        raise RuntimeError('Storage floor reached during stream')
                    handle.write(chunk);digest.update(chunk);meta['byte_count']+=len(chunk)
            with part.open('rb') as handle:
                if not handle.read(16).lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'%PDF-'):
                    raise RuntimeError('Unexpected PDF signature; possible access/error page')
            if path.exists():
                raise RuntimeError('Concurrent existing target; preserve both paths and stop')
            part.rename(path)
            meta.update(status='downloaded_candidate_original',raw_path=str(path.relative_to(ROOT)),
                        sha256=digest.hexdigest(),retrieved_at_utc=now())
    except Exception as exc:
        meta['error']=type(exc).__name__+': '+str(exc)[:400]
        if part.exists():
            meta['partial_path']=str(part.relative_to(ROOT))
            meta['partial_sha256']=hash_file(part)
    save_json(checkpoint,meta)
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--repair-ready-sha256',default='')
    args=parser.parse_args()
    contract=json.loads(CONTRACT.read_text())
    manifest=HERE/'frozen_acquisition_manifest.csv'
    if hash_file(manifest)!=contract['manifest_sha256']:
        raise SystemExit('Frozen manifest hash mismatch')
    state=preflight(contract,args.repair_ready_sha256)
    save_json(HERE/'EXECUTION_PREFLIGHT.json',state)
    if not args.execute or not (state['repair_gate_passes'] and state['storage_gate_passes']):
        print(json.dumps(state));return
    rows=list(csv.DictReader(manifest.open()))
    lock_paths=[ROOT/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock',HERE/'download.lock']
    locks=[]
    outcome=[]
    try:
        for lock_path in lock_paths:
            handle=lock_path.open('a+')
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            locks.append(handle)
        started=time.monotonic()
        raw_cap=contract['budget']['aggregate_new_raw_cap_bytes']
        for row in rows:
            fresh=preflight(contract,args.repair_ready_sha256)
            if not fresh['repair_gate_passes'] or not fresh['storage_gate_passes']:
                raise RuntimeError(fresh['status'])
            staging=HERE/row['staging_path']
            own_meta=staging.with_suffix('.request.json')
            if staging.exists() and not own_meta.exists():
                raise RuntimeError('Existing Task4 raw target lacks checkpoint; resolve locally before any request')
            if staging.exists() and own_meta.exists():
                old=json.loads(own_meta.read_text())
                if old.get('status')=='downloaded_candidate_original' and hash_file(staging)==old['sha256']:
                    outcome.append({**old,'disposition':'reuse_verified_task4_bytes'});continue
                raise RuntimeError('Existing Task4 target/checkpoint conflict')
            old_target=ROOT/row['local_existing_item_path']
            if old_target.exists() or old_target.with_suffix('.request.json').exists():
                raise RuntimeError('Existing source Item/checkpoint appeared; resolve reuse before any redownload')
            external=ROOT/'work_packages/M1_source_access/10_eu_cellar_acquisition/raw/items_external'
            if external.is_symlink():
                digest=hashlib.sha256(row['item_uri'].encode()).hexdigest()
                other=external/digest[:2]/f'{digest}.bin'
                if other.exists() or other.with_suffix('.request.json').exists():
                    raise RuntimeError('Existing external source Item/checkpoint appeared')
            raw_dir=HERE/'raw'
            stored=sum(p.stat().st_size for p in raw_dir.rglob('*') if p.is_file()) if raw_dir.exists() else 0
            if stored+int(row['max_object_bytes'])>raw_cap:
                raise RuntimeError('Frozen aggregate cap: insufficient space for next maximum-sized Item')
            delay=2-(time.monotonic()-started)
            if delay>0:time.sleep(delay)
            result=stream_one(row,contract)
            started=time.monotonic()
            outcome.append(result)
            print(json.dumps({'parent_id':row['parent_id'],'status':result['status'],'bytes':result['byte_count']}),flush=True)
            if result['status']!='downloaded_candidate_original':
                raise RuntimeError(result.get('error','object failed; stop'))
        state['status']='frozen_candidate_items_accounted_for'
    except (RuntimeError,BlockingIOError) as exc:
        state.update(status='stopped_partial',stop_reason=str(exc))
    finally:
        for handle in reversed(locks):
            fcntl.flock(handle,fcntl.LOCK_UN);handle.close()
        fields=['parent_id','item_uri','expression_uri','manifestation_uri','publication_dates','raw_path',
                'sha256','byte_count','format','retrieved_at_utc','request_url','final_url','status',
                'body_verification','rights_status']
        with (HERE/'ingestion_manifest.csv').open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore')
            writer.writeheader();writer.writerows(r for r in outcome if r.get('status')=='downloaded_candidate_original')
        state.update(downloads_started=bool(outcome),candidate_originals=sum(r.get('status')=='downloaded_candidate_original' for r in outcome),
                     verified_complete_bodies=0,finished_at_utc=now(),formal_database_writes=0)
        save_json(HERE/'EXECUTION_RESULT.json',state)


if __name__=='__main__':
    main()
