"""Bounded offline receipt and local path checks for the unchanged 979 B targets.

No HTTP, downloader import, formal DB access, extraction, or shared-file writes.
Raw-byte hashing is opt-in and bounded; this preparation needs none if paths
are absent. Existing bytes never establish readability or complete-Work status.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
WP = ROOT/'work_packages/M1_source_access'
OLD = WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation'
PACKAGE = OUT.parent
EXPECTED = 'af3fa2aa5c9cd6b1e97ad8b27fba17769be2c4916b3ef3dc4a6ab87fb772a4f7'
INPUTS = {}
CHECKS = []


def checked(label, condition):
    CHECKS.append({'check':label,'passed':bool(condition)})
    if not condition:
        raise RuntimeError(label)


def load(path, kind='text'):
    before=path.stat()
    raw=path.read_bytes()
    after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise RuntimeError('Input moved during read: '+str(path))
    INPUTS[str(path.relative_to(ROOT))]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
        'mtime_ns':after.st_mtime_ns,'mtime_utc':datetime.fromtimestamp(after.st_mtime,timezone.utc).isoformat()}
    if kind=='csv':return list(csv.DictReader(raw.decode('utf-8').splitlines()))
    if kind=='json':return json.loads(raw)
    return raw.decode('utf-8')


def dump(name, value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def csv_dump(name, rows):
    with (OUT/name).open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def rel(path):
    return str(path.relative_to(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hash-existing',action='store_true',help='At most 8 matching raw candidates and 64 MiB, under heavy-I/O lock')
    args=parser.parse_args()
    if (OUT/'INPUT_RECEIPT.json').exists():
        raise SystemExit('Preparation receipt exists; preserve this snapshot rather than overwrite it.')
    for path in [ROOT/'AGENTS.md',ROOT/'docs/PROJECT_DIRECTION.md',ROOT/'docs/PROJECT_LOG.md',
                 PACKAGE/'COORDINATION.md',WP/'16_post_repair_analysis_20261004/CURRENT_STATE.md',
                 WP/'10_eu_cellar_acquisition/FILTER_CONTRACT.md']:
        load(path)
    initial=load(PACKAGE/'control/INITIAL_PREFLIGHT.json','json')
    contract=load(OLD/'ACQUISITION_CONTRACT.json','json')
    manifest_path=OLD/'frozen_acquisition_manifest.csv'
    targets=load(manifest_path,'csv')
    population=load(OLD/'source_frame_population.csv','csv')
    relationships=load(OLD/'selected_work_item_relationships.csv','csv')
    multiplicity=load(WP/'16_post_repair_analysis_20261004/eu_selected_item_multiplicity.csv','csv')
    # Receipt only: the valid old release does not release this continuation.
    repair_release=WP/'15_targeted_repairs_and_supplementation_20261004/control/REPAIR_READY.json'
    load(repair_release,'json')
    a_manifest=WP/'15_targeted_repairs_and_supplementation_20261004/03_existing_data_repair/missing_original_requests.csv'
    a_rows=load(a_manifest,'csv')
    checked('frozen manifest digest matches explicit coordination and contract',
        INPUTS[rel(manifest_path)]['sha256']==EXPECTED==contract['manifest_sha256']==initial['frozen_eu_manifest_sha256'])
    checked('979 unique Work and selected Item identities',len(targets)==979 and len({r['parent_id'] for r in targets})==979 and len({r['item_uri'] for r in targets})==979)
    checked('all 12 consecutive months',sorted({r['month'] for r in targets})==[f'2015-{m:02d}' for m in range(1,13)])
    checked('source genre issuer language and parent-unit contract',all(r['source_id']=='EU_CELLAR_COM' and r['issuer']=='COM' and r['genre']=='COM act_preparatory' and r['language']=='ENG' and r['discourse_role']=='government' and r['unit']=='distinct CELLAR Work URI' for r in targets))
    checked('fixed study/tranche intervals preserved',contract['study_publication_interval']==['1988-01-01','2026-09-21'] and contract['tranche_publication_interval']==['2015-01-01','2015-12-31'])
    checked('all target source dates in correct 2015 month',all('2015-01-01'<=d<='2015-12-31' and d[:7]==r['month'] for r in targets for d in r['publication_dates'].split(';')))
    checked('frozen HTTPS request routes unchanged',all(r['request_url']==r['item_uri'].replace('http://','https://',1) and r['request_url'].startswith('https://publications.europa.eu/resource/cellar/') for r in targets))
    checked('1009 population Works and 30 no-link outcomes retained',len(population)==1009 and len({r['parent_id'] for r in population})==1009 and sum(not r['item_uri'] for r in population)==30)
    available={r['parent_id']:r for r in population if r['item_uri']}
    checked('target selection matches source population',len(available)==979 and all(available[r['parent_id']]['item_uri']==r['item_uri'] for r in targets))
    checked('five released A rows supersede old provisional three',len(a_rows)==5 and INPUTS[rel(a_manifest)]['sha256']==initial['original_requests_sha256'])
    by_work=defaultdict(list)
    for r in relationships:by_work[r['parent_id']].append(r)
    multiple={r['parent_id']:r for r in multiplicity}
    checked('bounded relationship and multiplicity populations match targets',len(relationships)==8409 and set(by_work)==set(available)==set(multiple))
    component_counts=[]
    for r in targets:
        linked=by_work[r['parent_id']]
        all_items={s['item_uri'] for s in linked}
        selected_items={s['item_uri'] for s in linked if s['manifestation_uri']==r['manifestation_uri']}
        selected_format_items={s['item_uri'] for s in linked if s['format']==r['format']}
        m=multiple[r['parent_id']]
        if not (len(all_items)==int(m['all_distinct_item_alternatives'])==int(r['unique_item_alternatives'])
                and len(selected_items)==int(m['selected_manifestation_distinct_items'])
                and len(selected_format_items)==int(m['selected_format_distinct_items'])
                and len(linked)==int(r['item_relationship_rows'])
                and any(s['item_uri']==r['item_uri'] and s['expression_uri']==r['expression_uri'] and s['manifestation_uri']==r['manifestation_uri'] and s['selected']=='True' for s in linked)):
            raise RuntimeError('Work/Item relationship mismatch: '+r['parent_id'])
        component_counts.append(len(selected_items))
    checked('253 selected PDF Manifestations with multiple Items and 726 single-Item',sum(n>1 for n in component_counts)==253 and sum(n==1 for n in component_counts)==726 and max(component_counts)==10)
    checked('973 multi-alternative Works retained',sum(int(m['all_distinct_item_alternatives'])>1 for m in multiplicity)==973)

    observations=[];ledger=[];sidecar_receipts={};hash_bytes=0;hash_files=0;lock=None
    external=WP/'10_eu_cellar_acquisition/raw/items_external'
    for ordinal,r in enumerate(targets,1):
        item_hash=hashlib.sha256(r['item_uri'].encode()).hexdigest()
        checked_path=Path(r['staging_path'])
        if checked_path.is_absolute() or '..' in checked_path.parts or checked_path.as_posix()!=f'raw/items/{item_hash[:2]}/{item_hash}.bin':
            raise RuntimeError('Frozen target path mismatch')
        paths=[('source_existing',ROOT/r['local_existing_item_path']),('prior_Task4_staging',OLD/checked_path),('new_B_staging',OUT/checked_path)]
        if external.is_symlink():paths.append(('declared_external_store',external/item_hash[:2]/f'{item_hash}.bin'))
        found=[]
        for location,raw_path in paths:
            sidecar=raw_path.with_suffix('.request.json')
            # Prefix inventory is limited to this selected Item's declared directory.
            matches=list(raw_path.parent.glob(item_hash+'*')) if raw_path.parent.is_dir() else []
            relevant=[p for p in matches if p.is_file()]
            partials=[p for p in relevant if '.part' in p.name]
            meta={};parse_error='';hash_state='not_needed_absent';raw_sha='';cooldown=False
            if sidecar.is_file():
                if sidecar.stat().st_size>1024*1024:parse_error='sidecar exceeds bounded 1 MiB local parse cap'
                else:
                    data=sidecar.read_bytes();sidecar_receipts[rel(sidecar)]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
                    try:meta=json.loads(data)
                    except (ValueError,UnicodeError):parse_error='sidecar parse unresolved'
                retry=meta.get('retry_not_before_utc')
                if retry:
                    try:cooldown=datetime.now(timezone.utc)<datetime.fromisoformat(retry)
                    except (ValueError,TypeError):parse_error+='; cooldown date unresolved'
            state='unrequested';conflict='';observed_size=raw_path.stat().st_size if raw_path.is_file() else 0
            if raw_path.is_file():
                state='local_reuse_pending_verification';hash_state='not_read_local_candidate_pending'
                if not sidecar.is_file() or parse_error:
                    state='local_conflict_stop_before_request';conflict='raw without valid request sidecar'
                elif (meta.get('item_uri')!=r['item_uri'] or (meta.get('parent_id') or meta.get('work_uri'))!=r['parent_id'] or int(meta.get('byte_count',-1))!=observed_size):
                    state='local_conflict_stop_before_request';conflict='sidecar identity/byte-count mismatch'
                elif args.hash_existing and hash_files<8 and hash_bytes+observed_size<=64*2**20:
                    if lock is None:
                        candidate_lock=(WP/'14_structural_validation_20261004/control/heavy_io.lock').open('r')
                        try:fcntl.flock(candidate_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);lock=candidate_lock
                        except BlockingIOError:candidate_lock.close();hash_state='pending_shared_lock_busy'
                    if lock:
                        digest=hashlib.sha256()
                        with raw_path.open('rb') as handle:
                            for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
                        raw_sha=digest.hexdigest();hash_files+=1;hash_bytes+=observed_size
                        if raw_sha==meta.get('sha256'):
                            state='candidate_bytes_hash_verified_readability_unassessed';hash_state='matched_saved_sidecar'
                        else:state='local_conflict_stop_before_request';conflict='raw SHA256 mismatch';hash_state='mismatch'
            elif sidecar.is_file() or partials:
                state='existing_attempt_failure_or_stop'
                hash_state='not_needed_no_final_raw'
                if meta.get('status') in {'downloaded','downloaded_candidate_original'}:
                    state='local_conflict_stop_before_request';conflict='downloaded sidecar without final raw bytes'
                if parse_error:state='local_conflict_stop_before_request';conflict=parse_error
                if cooldown:state='existing_failure_cooldown_active'
            found.append(state)
            observations.append({'ordinal':ordinal,'parent_id':r['parent_id'],'item_uri':r['item_uri'],'location':location,
                'raw_path':rel(raw_path),'raw_exists':raw_path.is_file(),'observed_raw_bytes':observed_size,
                'request_sidecar_path':rel(sidecar),'request_sidecar_exists':sidecar.is_file(),'sidecar_status':meta.get('status',''),
                'sidecar_http_status':meta.get('http_status',''),'retry_not_before_utc':meta.get('retry_not_before_utc',''),
                'cooldown_active':cooldown,'partial_paths':';'.join(rel(p) for p in partials),'partial_bytes':sum(p.stat().st_size for p in partials),
                'other_selected_Item_sidecars':';'.join(rel(p) for p in relevant if p!=raw_path and p!=sidecar and p not in partials),
                'local_observation':state,'raw_hash_state':hash_state,'checked_raw_sha256':raw_sha,'conflict_reason':conflict})
        if 'local_conflict_stop_before_request' in found:overall='local_conflict_stop_before_request'
        elif 'candidate_bytes_hash_verified_readability_unassessed' in found:overall='candidate_bytes_hash_verified_readability_unassessed'
        elif 'local_reuse_pending_verification' in found:overall='local_reuse_pending_verification'
        elif 'existing_failure_cooldown_active' in found:overall='existing_failure_cooldown_active'
        elif 'existing_attempt_failure_or_stop' in found:overall='existing_attempt_failure_or_stop'
        else:overall='unrequested'
        ledger.append({'ordinal':ordinal,'parent_id':r['parent_id'],'expression_uri':r['expression_uri'],
            'manifestation_uri':r['manifestation_uri'],'item_uri':r['item_uri'],'month':r['month'],
            'publication_dates':r['publication_dates'],'source_id':r['source_id'],'genre':r['genre'],'format':r['format'],
            'request_url':r['request_url'],'planned_staging_path':rel(OUT/checked_path),'local_state':overall,
            'attempted_this_continuation':False,'attempt_state':'not_attempted_waiting_for_coordinator_EU_release',
            'stop_or_not_attempted_reason':'await accepted runner/final-five A accounting, coordinator release and execution follow-up',
            'candidate_bytes_observed':any(s!='unrequested' for s in found) and any(o['raw_exists'] for o in observations[-len(paths):]),
            'selected_Item_readability':'unassessed','identity_date_content_mapping':'original-body verification pending',
            'selected_manifestation_distinct_items':multiple[r['parent_id']]['selected_manifestation_distinct_items'],
            'all_distinct_item_alternatives':multiple[r['parent_id']]['all_distinct_item_alternatives'],
            'component_roles':'unresolved from saved relationship metadata; no sibling acquisition authorised',
            'complete_Work_required_components':'unassessed; single-Item does not prove completeness',
            'content_version_state':'no new version acquired in this preparation','rights_status':r['rights_access']})
    if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    csv_dump('B_TARGET_STATUS.csv',ledger);csv_dump('B_PATH_OBSERVATIONS.csv',observations)
    checked('all 979 targets accounted for without HTTP attempt',len(ledger)==979 and all(not r['attempted_this_continuation'] for r in ledger))
    checked('original manifest unchanged after preparation',hashlib.sha256(manifest_path.read_bytes()).hexdigest()==EXPECTED)
    now=datetime.now(timezone.utc);free=shutil.disk_usage(OUT).free
    reserve=initial['reserve_bytes'];floor=initial['floor_bytes']
    summary={'status':'waiting_for_coordinator_EU_release','preparation_status':'complete',
        'prepared_at_utc':now.isoformat(),'prepared_at_local':now.astimezone(ZoneInfo('Asia/Shanghai')).isoformat(),
        'publication_interval':['1988-01-01','2026-09-21'],'september_2026_partial':True,
        'tranche_interval':['2015-01-01','2015-12-31'],'manifest_sha256':EXPECTED,
        'target_count':979,'enumerated_Works':1009,'no_link_Works':30,'months':12,
        'multiple_alternative_Works':973,'multiple_Items_in_selected_PDF_manifestation_Works':253,
        'single_Item_selected_manifestation_Works':726,'max_selected_manifestation_Items':10,
        'local_state_counts':dict(Counter(r['local_state'] for r in ledger)),
        'observed_raw_target_paths':sum(r['raw_exists'] for r in observations),
        'observed_request_sidecars':sum(r['request_sidecar_exists'] for r in observations),
        'observed_partial_paths':sum(bool(r['partial_paths']) for r in observations),
        'local_raw_hash_reads':hash_files,'local_raw_bytes_hashed':hash_bytes,
        'HTTP_requests_this_preparation':0,'new_downloads':0,'complete_readable_Works_verified':0,
        'formal_database_reads':0,'formal_database_writes':0,'extraction_runs':0,'downloader_imports_or_edits':0,
        'checks':CHECKS,'checks_passed':len(CHECKS),
        'A_before_B':{'released_A_manifest_rows':5,'A_terminal_outcomes_reviewed':False,'A_consumed_new_raw_bytes':'pending final accounting; not assumed zero'},
        'gates':{'execution_followup_received':False,'EU_STAGING_RELEASE_exists_at_snapshot':(PACKAGE/'control/EU_STAGING_RELEASE.json').exists(),
                 'EU_STAGING_RELEASE_read_or_validated':False,'old_repair_release_alone_is_insufficient':True,
                 'downloader_acceptance':'Task3/coordinator pending; downloader not executed here'},
        'budget':{'aggregate_new_raw_cap_A_plus_B_bytes':2*2**30,'retained_partials_count_toward_cap':True,
                  'A_budget_remaining_for_B':'pending coordinator accepted A accounting',
                  'free_bytes':free,'free_gib':free/2**30,'existing_reserve_bytes':reserve,'floor_bytes':floor,
                  'projected_remaining_gib_before_new_A_accounting':(free-reserve)/2**30,
                  'snapshot_storage_above_reserve_and_floor':free-reserve>floor,
                  'fresh_execution_recheck_required':True},
        'limits':['Path absence/presence is not download success or readability evidence.',
                  'Saved relationship multiplicity does not identify all sibling roles or certify any complete Work.',
                  'No alternate, sibling or annex target added; no sealed reviewer code or credential located/read/probed.'],
        'next_action':'Task3 completes runner/offline validation and final-five terminal A/budget accounting; coordinator accepts, signs EU_STAGING_RELEASE.json and sends this window an execution follow-up. Then use accepted runner for unchanged 979 targets.'}
    dump('LOCAL_PREPARATION.json',summary)
    dump('INPUT_RECEIPT.json',{'created_at_utc':now.isoformat(),'root':str(ROOT),'inputs':INPUTS,
        'existing_target_sidecar_receipts':sidecar_receipts,'frozen_manifest_expected_sha256':EXPECTED,
        'scope':'named local preparation inputs only; no evaluator/credentials, formal DB contents or all-corpus scans',
        'old_files_rewritten':[],'new_downloads':0,'execution_release_consumed':False})
    dump('RESULT.json',{**summary,'primary_outputs':['B_TARGET_STATUS.csv','B_PATH_OBSERVATIONS.csv','INPUT_RECEIPT.json',
        'LOCAL_PREPARATION.json','RESULT.json','LOG_ENTRY.md','HANDOFF_zh.md','inspect_local_targets.py'],
        'exclusive_output':str(OUT),'background_poll_or_collector':False})
    print(json.dumps({'status':summary['status'],'local_states':summary['local_state_counts'],
        'checks':len(CHECKS),'free_gib':summary['budget']['free_gib'],'projected_remaining_gib':summary['budget']['projected_remaining_gib_before_new_A_accounting']}))


if __name__=='__main__':main()
