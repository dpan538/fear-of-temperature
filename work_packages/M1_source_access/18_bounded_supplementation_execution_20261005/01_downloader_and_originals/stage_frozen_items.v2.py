"""Bounded staging v2. Default is offline B preflight; execution needs coordinator release.
No extraction or formal database writes. Immutable input manifests are never rewritten.
Shared raw accounting and persistent HTTP state cover A and B, including partials.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import os
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP = ROOT/'work_packages/M1_source_access'
STAGE = WP/'18_bounded_supplementation_execution_20261005'
A_OUT = STAGE/'01_downloader_and_originals'
B_OUT = STAGE/'02_eu_staging'
CONTRACT = HERE/'ACQUISITION_CONTRACT.json'
REPAIR = WP/'15_targeted_repairs_and_supplementation_20261004/03_existing_data_repair'
MARKER = REPAIR.parent/'control/REPAIR_READY.json'
DB = WP/'06_government_content_acquisition/fear_temperature_government_content.duckdb'
HEAVY = WP/'14_structural_validation_20261004/control/heavy_io.lock'
DOWNLOAD_LOCK = HERE/'download.lock'
STATE = A_OUT/'SHARED_HTTP_STATE.json'
EU_RELEASE = STAGE/'control/EU_STAGING_RELEASE.json'
VERSION = 'bounded_staging_v2_20261005'
INTERVAL = ['1988-01-01', '2026-09-21']
RUN = 'repair_20261004_task3_v1'
RULE = 'targeted_structural_repair_v1_20261004'
A_SHA = '969c388e7815c27f086c4a50aa82e7268740f9eb0d0ad0f306919f5c380300dd'
B_SHA = 'af3fa2aa5c9cd6b1e97ad8b27fba17769be2c4916b3ef3dc4a6ab87fb772a4f7'
A_IDS = {'doc_5b740259ea5cdcdbdbdf', 'doc_6fe9e11be5ea65fab67e', 'doc_76b0ddb367df2c048a60',
         'doc:7c7006b4ea3168ebe548e229915d853b', 'doc:bc6340389c3977a04993b0a20f55bcca'}
TERMINALS = {'verified_local_reuse', 'original_obtained_validation_pending', 'bounded_unavailable',
             'access_restricted', 'date_unresolved', 'outside_fixed_interval', 'stopped_safety_or_access'}
GIB = 2**30


def now():
    return datetime.now(timezone.utc).isoformat()


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('w') as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_json(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def exact_path(value, expected):
    candidate = Path(value)
    candidate = candidate if candidate.is_absolute() else ROOT/candidate
    require(candidate == expected and candidate.resolve() == expected and not candidate.is_symlink(),
            'Unexpected or aliased evidence path: '+str(candidate))
    return candidate


@contextmanager
def locks(download=False):
    handles = []
    try:
        for path in ([HEAVY, DOWNLOAD_LOCK] if download else [HEAVY]):
            handle = path.open('a+')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BaseException:
                handle.close(); raise
            handles.append(handle)
        yield
    finally:
        for handle in reversed(handles):
            fcntl.flock(handle, fcntl.LOCK_UN); handle.close()


def checkpoint():
    require(not DB.is_symlink(), 'Database symlink rejected')
    st = DB.stat()
    return {'path': str(DB.relative_to(ROOT)), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns}


def active_run():
    import duckdb
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute('SELECT active, rule_version, plan_sha256, committed_at_utc, plan_path FROM repair_runs WHERE run_id=?', [RUN]).fetchone()
    finally:
        con.close()


def validate_release(contract, expected_sha):
    exact_path(contract['repair_release_path'], MARKER)
    require(MARKER.is_file() and hash_file(MARKER) == expected_sha and bool(expected_sha), 'Repair release digest mismatch or missing')
    data = load_json(MARKER)
    require(data.get('ready') is True and data.get('status') == 'committed_repairs_checked_targeted_acquisition_released', 'Repair release is not committed/checked/released')
    require(data.get('fixed_publication_interval') == INTERVAL == contract['study_publication_interval'], 'Fixed interval mismatch')
    require(data.get('run_id') == RUN and data.get('rule_version') == RULE, 'Unexpected repair run/rule')
    exact_path(data['authority'], DB)
    for name in ['pre_checkpoint', 'post_checkpoint']:
        cp = data[name]
        exact_path(cp['path'], DB)
        require(type(cp['bytes']) is int and type(cp['mtime_ns']) is int and cp['bytes'] > 0, 'Malformed checkpoint')
    require(data['pre_checkpoint'] != data['post_checkpoint'], 'Missing commit checkpoint change')
    evidence = {}
    for field, filename in [('acceptance_path', 'ACCEPTANCE.json'), ('result_path', 'RESULT.json'), ('change_manifest_path', 'CHANGE_MANIFEST.json')]:
        path = exact_path(data[field], REPAIR/filename)
        evidence[filename] = load_json(path)
    acceptance, result, changes = (evidence[k] for k in ['ACCEPTANCE.json', 'RESULT.json', 'CHANGE_MANIFEST.json'])
    applied = load_json(REPAIR/'APPLIED.json')
    require(acceptance.get('status') == 'passed' and acceptance.get('failures') == [], 'Acceptance did not pass')
    require(result.get('repair_ready') is True and result.get('status') == 'complete_with_named_unresolved_cases' and result.get('fixed_publication_interval') == INTERVAL, 'Result is not the released repair result')
    require(applied.get('status') == 'applied_and_checked' and applied.get('acceptance') == acceptance, 'Missing committed acceptance evidence')
    for linked in [changes, applied]:
        require(linked.get('run_id') == RUN and linked.get('plan_sha256') == data['plan_sha256'], 'Linked run/plan mismatch')
    require(changes.get('rule_version') == RULE, 'Linked rule mismatch')
    for linked in [result, changes, applied]:
        require(linked.get('pre_checkpoint') == data['pre_checkpoint'] and linked.get('post_checkpoint') == data['post_checkpoint'], 'Linked checkpoint mismatch')
    source = exact_path(data['missing_original_requests_path'], REPAIR/'missing_original_requests.csv')
    exact_path(contract['repair_request_path'], source)
    require(hash_file(source) == A_SHA, 'Final A manifest hash mismatch')
    rows = list(csv.DictReader(source.open()))
    require(len(rows) == 5 and {r['unit_id'] for r in rows} == A_IDS and data.get('counts', {}).get('requests') == 5, 'Final five A request identities mismatch')
    require(checkpoint() == data['post_checkpoint'], 'Current database post-checkpoint mismatch')
    active = active_run()
    require(active is not None and active[0] is True and active[1] == RULE and active[2] == data['plan_sha256'], 'Committed repair run inactive or mismatched')
    exact_path(active[4], REPAIR/'PLAN.json')
    # repair_runs records transaction insertion time; APPLIED records post-commit receipt time.
    require(datetime.fromisoformat(active[3]) <= datetime.fromisoformat(applied['committed_at_utc']) <= datetime.fromisoformat(data['last_formal_write_at_utc']) <= datetime.fromisoformat(data['released_at_utc']), 'Committed run/receipt chronology mismatch')
    require(checkpoint() == data['post_checkpoint'], 'Database changed during targeted read')
    return {'marker_sha256': expected_sha, 'run_id': RUN, 'post_checkpoint': data['post_checkpoint'],
            'request_path': str(source.relative_to(ROOT)), 'request_manifest_sha256': A_SHA,
            'unit_ids': sorted(A_IDS), 'linked_evidence_sha256': {k: hash_file(REPAIR/k) for k in [*evidence, 'APPLIED.json']},
            'active_committed_run_verified': True, 'run_recorded_at_utc': active[3], 'postcommit_receipt_at_utc': applied['committed_at_utc'],
            'database_query': 'targeted repair_runs primary-key read; read_only=True'}


def release_check(contract, expected_sha, locked=False):
    try:
        if locked:
            evidence = validate_release(contract, expected_sha)
        else:
            with locks():
                evidence = validate_release(contract, expected_sha)
        return True, 'released', evidence
    except Exception as exc:
        return False, 'blocked_repair_release', {'error': type(exc).__name__+': '+str(exc)}


def raw_roots():
    return [HERE/'raw', A_OUT/'raw', B_OUT/'raw']


def raw_accounting():
    files = []
    for root in raw_roots():
        require(not root.is_symlink(), 'Staging raw root symlink rejected')
        if not root.exists():
            continue
        for path in sorted(root.rglob('*')):
            require(not path.is_symlink(), 'Staging raw symlink rejected')
            if path.is_file():
                require(path.resolve().is_relative_to(root.resolve()), 'Raw path escaped staging root')
                files.append({'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'partial': path.name.endswith('.part')})
    return {'total_bytes': sum(f['bytes'] for f in files), 'partial_bytes': sum(f['bytes'] for f in files if f['partial']), 'files': files}


def budget_check(contract, next_bytes=0, reserve_remaining=False):
    budget = contract['budget']
    require(budget['aggregate_new_raw_cap_bytes'] == 2*GIB and budget['collector_floor_bytes'] == 15*GIB, 'Frozen storage budget mismatch')
    stored = raw_accounting()
    cap = budget['aggregate_new_raw_cap_bytes']
    require(next_bytes >= 0 and stored['total_bytes'] + next_bytes <= cap, 'Shared A+B raw cap reached')
    transient = sum(budget[k] for k in ['inflight_object_reserve_bytes', 'checkpoint_error_reserve_bytes', 'repair_other_activity_reserve_bytes'])
    free = shutil.disk_usage(HERE).free
    reserve = transient + (cap-stored['total_bytes'] if reserve_remaining else next_bytes)
    require(free-reserve > budget['collector_floor_bytes'], 'Storage floor plus transient/checkpoint/other reserves reached')
    return {'free_bytes': free, 'raw_bytes': stored['total_bytes'], 'partial_bytes': stored['partial_bytes'],
            'remaining_shared_raw_bytes': cap-stored['total_bytes'], 'reserve_bytes': reserve, 'floor_bytes': budget['collector_floor_bytes']}


def code_hash():
    return hash_file(Path(__file__))


def validate_a_accounting():
    ledger, accounting = A_OUT/'A_DISPOSITIONS.csv', A_OUT/'A_ACCOUNTING.json'
    require(ledger.is_file() and accounting.is_file(), 'Final A ledger/accounting missing')
    rows = list(csv.DictReader(ledger.open()))
    require(len(rows) == 5 and {r['unit_id'] for r in rows} == A_IDS and all(r['terminal_status'] in TERMINALS and r['evidence_path'] for r in rows), 'A terminal ledger incomplete')
    data = load_json(accounting)
    require(data.get('complete') is True and data.get('unit_ids') == sorted(A_IDS) and data.get('source_manifest_sha256') == A_SHA and data.get('ledger_sha256') == hash_file(ledger), 'A accounting binding mismatch')
    for row in rows:
        p = ROOT/row['evidence_path']
        require(p.resolve().is_relative_to(A_OUT.resolve()) and hash_file(p) == row['evidence_sha256'], 'A terminal evidence mismatch')
    actual = [f for f in raw_accounting()['files'] if Path(ROOT/f['path']).is_relative_to(A_OUT/'raw')]
    require(actual == [{k:f[k] for k in ['path', 'bytes', 'partial']} for f in data['A_raw_files']], 'A retained raw accounting changed')
    for f in data['A_raw_files']:
        require(hash_file(ROOT/f['path']) == f['sha256'], 'A raw digest mismatch')
    return {'a_ledger_sha256': hash_file(ledger), 'a_accounting_sha256': hash_file(accounting), 'a_manifest_sha256': A_SHA}


def eu_release_check(repair_evidence):
    require(EU_RELEASE.is_file() and not EU_RELEASE.is_symlink(), 'Coordinator EU_STAGING_RELEASE.json missing; EU HTTP forbidden')
    release = load_json(EU_RELEASE)
    require(release.get('ready') is True and release.get('status') == 'coordinator_accepted_downloader_and_A_released_B' and release.get('issuer') == 'coordinator', 'EU release is not coordinator acceptance')
    bindings = {'downloader_version': VERSION, 'downloader_sha256': code_hash(), 'repair_release_sha256': repair_evidence['marker_sha256'],
                'frozen_b_manifest_sha256': B_SHA, 'run_id': RUN, 'fixed_publication_interval': INTERVAL,
                'post_checkpoint': repair_evidence['post_checkpoint'], **validate_a_accounting()}
    bindings['downloader_ready_sha256'] = hash_file(A_OUT/'DOWNLOADER_READY.json')
    require(all(release.get(k) == v for k,v in bindings.items()), 'Coordinator EU release binding mismatch')
    require(hash_file(HERE/'frozen_acquisition_manifest.csv') == B_SHA, 'Frozen B manifest changed')
    return bindings


def preflight(contract, expected_sha, locked=False, execution=False):
    ok, reason, evidence = release_check(contract, expected_sha, locked)
    state = {'checked_at_utc': now(), 'status': reason, 'repair_gate_passes': ok, 'release_evidence': evidence,
             'storage_gate_passes': False, 'downloads_started': False, 'eu_http_authorized': False}
    try:
        state.update(budget_check(contract, reserve_remaining=True)); state['storage_gate_passes'] = True
        if ok:
            state['status'] = 'ready_for_local_preflight_only'
            if execution:
                state['eu_release_bindings'] = eu_release_check(evidence)
                state.update(eu_http_authorized=True, status='ready_for_coordinator_released_B')
    except Exception as exc:
        state.update(status='blocked', error=type(exc).__name__+': '+str(exc))
    return state


def signature(path, kind):
    with Path(path).open('rb') as handle:
        prefix = handle.read(1024).lstrip(b'\xef\xbb\xbf \r\n\t')
    if kind == 'pdf':
        require(prefix.startswith(b'%PDF-'), 'Unexpected PDF signature; access/error page possible')
    elif kind == 'html':
        require(b'<html' in prefix.lower() or b'<!doctype html' in prefix.lower(), 'Unexpected HTML signature')


def verified_reuse(row, path, checkpoint_path=None, kind='pdf'):
    path = Path(path)
    checkpoint_path = Path(checkpoint_path) if checkpoint_path else path.with_suffix('.request.json')
    require(path.is_file() and checkpoint_path.is_file(), 'Existing raw lacks checkpoint')
    meta = load_json(checkpoint_path)
    require(meta.get('status') in {'downloaded_candidate_original', 'downloaded', 'success'}, 'Existing checkpoint is not successful')
    for key in ['parent_id', 'item_uri', 'expression_uri', 'manifestation_uri', 'request_url']:
        if key in row:
            require(meta.get(key) == row[key], 'Reuse identity mismatch: '+key)
    require(path.stat().st_size == meta.get('byte_count') and path.stat().st_size <= int(row['max_object_bytes']), 'Reuse byte length/cap mismatch')
    require(hash_file(path) == meta.get('sha256'), 'Reuse SHA256 mismatch')
    signature(path, kind)
    return {**meta, 'status': 'verified_local_reuse', 'raw_path': str(path), 'new_raw_bytes': 0}


def network_guard():
    state = load_json(STATE) if STATE.exists() else {}
    require(not state.get('halted'), 'Persistent HTTP stop: '+str(state.get('stop_reason', 'unresolved failed attempt')))
    cooldown = state.get('retry_not_before_utc')
    require(not cooldown or datetime.now(timezone.utc) >= datetime.fromisoformat(cooldown), 'Persisted Retry-After/429 cooldown active')
    last = state.get('last_request_finished_utc') or state.get('last_request_started_utc')
    if last:
        delay = 2-(datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()
        if delay > 0:
            time.sleep(delay)
    state['last_request_started_utc'] = now()
    state['request_count'] = state.get('request_count', 0)+1
    save_json(STATE, state)


def network_finished(response=None, error=None):
    state = load_json(STATE)
    state['last_request_finished_utc'] = now()
    if error:
        state.update(halted=True, stop_reason=error)
    if response is not None:
        retry = response.headers.get('Retry-After')
        if retry or response.status_code == 429:
            until = datetime.now(timezone.utc)+timedelta(hours=1)
            if retry:
                try:
                    until = datetime.now(timezone.utc)+timedelta(seconds=int(retry)) if retry.isdigit() else parsedate_to_datetime(retry).astimezone(timezone.utc)
                    until = max(until, datetime.now(timezone.utc))
                except (ValueError, TypeError, OverflowError):
                    state['retry_after_parse_pending'] = retry
            state.update(retry_not_before_utc=until.isoformat(), halted=True, stop_reason='Retry-After/429; no automatic resumption')
        elif response.status_code in {401, 403}:
            state.update(halted=True, stop_reason='HTTP access restriction '+str(response.status_code))
    save_json(STATE, state)


def stream_one(row, contract, output_dir=None, kind='pdf', allowed_hosts=None):
    """Caller holds both locks and release gate. One attempt, bounded explicit redirects.
    A failed checkpoint always blocks rerun, even after a cooldown expires.
    """
    import requests
    output_dir = Path(output_dir or B_OUT)
    require(output_dir in {A_OUT, B_OUT}, 'Only the two bounded staging roots are authorized')
    if output_dir == B_OUT:
        ok, _, evidence = release_check(contract, hash_file(MARKER), locked=True)
        require(ok, 'Fresh committed repair release failed')
        eu_release_check(evidence)
    else:
        ready = load_json(A_OUT/'DOWNLOADER_READY.json')
        require(ready.get('status') == 'ready' and ready.get('downloader_sha256') == code_hash()
                and ready.get('a_manifest_sha256') == A_SHA, 'Downloader offline readiness missing/mismatched')
        require(row.get('unit_id') in A_IDS, 'A route not associated with final five requests')
        ok, _, _ = release_check(contract, ready['repair_release_sha256'], locked=True)
        require(ok, 'Fresh A repair release failed')
    path = output_dir/row['staging_path']
    require(path.resolve().is_relative_to((output_dir/'raw').resolve()), 'Target path escaped raw staging')
    cp = output_dir/'requests'/((hashlib.sha256(row['request_url'].encode()).hexdigest())+'.json')
    require(not cp.exists() and not path.exists(), 'Existing target or attempt: reconcile locally; no automatic retry')
    maximum = int(row['max_object_bytes'])
    budget_check(contract, maximum)
    cp.parent.mkdir(parents=True, exist_ok=True); path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name+'.'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.part')
    meta = {k: row[k] for k in ['parent_id','item_uri','expression_uri','manifestation_uri','publication_dates','request_url','format'] if k in row}
    meta.update(status='attempt_in_progress', requested_at_utc=now(), byte_count=0, redirects=[], raw_path='', sha256='', checkpoint_path=str(cp.relative_to(ROOT)), body_verification='identity/date/content boundary pending')
    save_json(cp, meta)  # Persist attempted state before HTTP; an interrupted process cannot retry.
    response = None
    try:
        url = row['request_url']
        allowed_hosts = set(allowed_hosts or {'publications.europa.eu','op.europa.eu'})
        for redirect in range(3):
            require(urlsplit(url).scheme == 'https' and urlsplit(url).hostname in allowed_hosts, 'Unapproved request/redirect host')
            network_guard()
            try:
                response = requests.get(url, headers={'User-Agent':'FearTemperatureResearch/1.0 (public academic source acquisition)', 'Accept':'application/pdf' if kind=='pdf' else 'text/html', 'Accept-Encoding':'identity'}, stream=True, allow_redirects=False, timeout=(15,90))
            except Exception as exc:
                network_finished(error=type(exc).__name__+': '+str(exc)[:300]); raise
            meta.update(http_status=response.status_code, final_url=response.url, response_headers={k:v for k,v in response.headers.items() if k.lower() in {'date','content-type','content-length','etag','last-modified','retry-after','content-disposition','location','content-encoding'}})
            network_finished(response)
            if response.status_code not in {301,302,303,307,308}:
                break
            require(redirect < 2 and response.headers.get('Location'), 'Redirect bound exceeded/missing Location')
            meta['redirects'].append({'url':url,'status':response.status_code,'location':response.headers['Location']})
            url = urljoin(url,response.headers['Location']); response.close(); response=None
        require(response.status_code == 200, 'HTTP '+str(response.status_code)+'; terminal failed route')
        require(not response.headers.get('Retry-After'), 'Retry-After present; stop without streaming')
        raw_length = response.headers.get('Content-Length')
        length = None
        if raw_length is not None:
            require(raw_length.isdigit(), 'Malformed Content-Length')
            length = int(raw_length)
            require(0 < length <= maximum, 'Content-Length outside object cap')
        require(response.headers.get('Content-Encoding','identity').lower() in {'','identity'}, 'Encoded stream: byte-length verification unresolved')
        with part.open('xb') as handle:
            for chunk in response.iter_content(65536):
                if not chunk: continue
                require(meta['byte_count']+len(chunk) <= maximum, 'Stream exceeds object cap')
                budget_check(contract, len(chunk))
                handle.write(chunk); handle.flush(); meta['byte_count'] += len(chunk)
        require(meta['byte_count'] > 0 and (length is None or length == meta['byte_count']), 'Empty/truncated Content-Length body')
        signature(part,kind)
        require(not path.exists(), 'Concurrent existing target')
        # Hard link is exclusive: a concurrent target can never be overwritten.
        os.link(part,path); part.unlink()
        meta.update(status='downloaded_candidate_original', raw_path=str(path.relative_to(ROOT)), sha256=hash_file(path), retrieved_at_utc=now())
    except Exception as exc:
        meta.update(status='failed', error=type(exc).__name__+': '+str(exc)[:400])
        if part.exists():
            meta.update(partial_path=str(part.relative_to(ROOT)), partial_sha256=hash_file(part), byte_count=part.stat().st_size)
        # Ordinary bounded 404/410 is a terminal route, not a replacement queue.
        if meta.get('http_status') not in {404,410}:
            if STATE.exists(): network_finished(error=meta['error'])
    finally:
        if response is not None: response.close()
        save_json(cp,meta)
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--repair-ready-sha256',default='')
    args=parser.parse_args()
    contract=load_json(CONTRACT)
    require(hash_file(HERE/'frozen_acquisition_manifest.csv') == B_SHA == contract['manifest_sha256'], 'Frozen B manifest mismatch')
    B_OUT.mkdir(parents=True,exist_ok=True)
    state=preflight(contract,args.repair_ready_sha256,execution=args.execute)
    save_json(B_OUT/'EXECUTION_PREFLIGHT.json',state)
    if not args.execute or not (state['repair_gate_passes'] and state['storage_gate_passes'] and state['eu_http_authorized']):
        print(json.dumps(state));return
    rows=list(csv.DictReader((HERE/'frozen_acquisition_manifest.csv').open()))
    require(len(rows)==979 and len({r['item_uri'] for r in rows})==979, 'Frozen target identities mismatch')
    outcomes=[]; started_http = 0
    try:
        with locks(download=True):
            require(preflight(contract,args.repair_ready_sha256,locked=True,execution=True)['eu_http_authorized'], 'Fresh EU release failed')
            for row in rows:
                fresh=preflight(contract,args.repair_ready_sha256,locked=True,execution=True)
                require(fresh['eu_http_authorized'] and fresh['storage_gate_passes'], 'Fresh release/storage failed')
                digest=hashlib.sha256(row['request_url'].encode()).hexdigest()
                candidates=[(B_OUT/row['staging_path'], B_OUT/'requests'/f'{digest}.json'),
                            (HERE/row['staging_path'], (HERE/row['staging_path']).with_suffix('.request.json')),
                            (ROOT/row['local_existing_item_path'], (ROOT/row['local_existing_item_path']).with_suffix('.request.json'))]
                external=WP/'10_eu_cellar_acquisition/raw/items_external'
                if external.is_symlink():
                    item_digest=hashlib.sha256(row['item_uri'].encode()).hexdigest()
                    other=external/item_digest[:2]/f'{item_digest}.bin'
                    candidates.append((other,other.with_suffix('.request.json')))
                reused=None
                for path,cp in candidates:
                    if path.exists() or cp.exists():
                        reused=verified_reuse(row,path,cp);break
                if reused:
                    outcomes.append({**row,**reused});continue
                result=stream_one(row,contract);started_http+=1
                outcomes.append({**row,**result})
                require(result['status']=='downloaded_candidate_original',result.get('error','failed Item; stop'))
            state['status']='frozen_candidate_items_accounted_for'
    except Exception as exc:
        state.update(status='stopped_partial',stop_reason=type(exc).__name__+': '+str(exc))
    accounted={r['item_uri'] for r in outcomes}
    outcomes.extend({**r,'status':'not_attempted_after_stop','error':state.get('stop_reason','not reached')} for r in rows if r['item_uri'] not in accounted)
    fields=['parent_id','expression_uri','manifestation_uri','item_uri','publication_dates','request_url','status','raw_path','sha256','byte_count','checkpoint_path','error','body_verification']
    with (B_OUT/'B_STATUS_LEDGER.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(outcomes)
    state.update(finished_at_utc=now(), frozen_items=979, ledger_rows=len(outcomes), attempted_items=started_http,
                 candidate_originals=sum(r['status']=='downloaded_candidate_original' for r in outcomes),
                 verified_reuse=sum(r['status']=='verified_local_reuse' for r in outcomes),
                 raw_accounting=raw_accounting(),formal_database_writes=0,extraction_started=False)
    save_json(B_OUT/'EXECUTION_RESULT.json',state)
    print(json.dumps(state))


if __name__=='__main__': main()
