"""Join frozen metadata to terminal B receipts; no network, raw reads or DB access.

Run after the single accepted downloader command reaches its terminal state.
Uses downloader SHA receipts and scoped file sizes, without repeating raw hashes.
"""
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
WP=ROOT/'work_packages/M1_source_access'
OLD=WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation'
A=OUT.parent/'01_downloader_and_originals'
CONTROL=OUT.parent/'control'
EXPECTED_MANIFEST='af3fa2aa5c9cd6b1e97ad8b27fba17769be2c4916b3ef3dc4a6ab87fb772a4f7'
EXPECTED_RUNNER='f6f2bda93e9745c56ff9fd438be8071af2b40ee65b5f5b625d30f2d1c5e28bb2'
INPUTS={}
CHECKS=[]


def load(path,kind='json'):
    raw=path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
        'mtime_ns':path.stat().st_mtime_ns}
    if kind=='csv':return list(csv.DictReader(raw.decode('utf-8').splitlines()))
    if kind=='text':return raw.decode('utf-8')
    return json.loads(raw)


def check(name,condition):
    CHECKS.append({'check':name,'passed':bool(condition)})
    if not condition:raise RuntimeError(name)


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def csv_write(name,rows,fields=None):
    fields=fields or list(rows[0])
    with (OUT/name).open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(rows)


def main():
    execution=load(OUT/'EXECUTION_RESULT.json')
    check('accepted command terminal receipt present',bool(execution.get('finished_at_utc')))
    preflight=load(OUT/'EXECUTION_PREFLIGHT.json')
    release=load(CONTROL/'EU_STAGING_RELEASE.json')
    ready=load(A/'DOWNLOADER_READY.json')
    a_account=load(A/'A_ACCOUNTING.json')
    a_state=load(A/'SHARED_HTTP_STATE.json')
    load(A/'A_DISPOSITIONS.csv','csv')
    contract=load(OLD/'ACQUISITION_CONTRACT.json')
    load(OLD/'stage_frozen_items.py','text')  # Only hash the accepted normal downloader; never copy/edit it.
    frozen=load(OLD/'frozen_acquisition_manifest.csv','csv')
    population=load(OLD/'source_frame_population.csv','csv')
    multiplicity=load(WP/'16_post_repair_analysis_20261004/eu_selected_item_multiplicity.csv','csv')
    ledger=load(OUT/'B_STATUS_LEDGER.csv','csv')
    phase=load(OUT/'PHASE_HTTP_STATE.json')
    preparation=load(OUT/'LOCAL_PREPARATION.json')
    load(OUT/'EXECUTION_STDOUT.log','text')
    check('accepted runner and frozen manifest unchanged',INPUTS[str((OLD/'stage_frozen_items.py').relative_to(ROOT))]['sha256']==EXPECTED_RUNNER==release['downloader_sha256']==ready['downloader_sha256'] and INPUTS[str((OLD/'frozen_acquisition_manifest.csv').relative_to(ROOT))]['sha256']==EXPECTED_MANIFEST==contract['manifest_sha256']==release['frozen_b_manifest_sha256'])
    for name,key in [('A_DISPOSITIONS.csv','a_ledger_sha256'),('A_ACCOUNTING.json','a_accounting_sha256'),('SHARED_HTTP_STATE.json','a_http_state_sha256'),('DOWNLOADER_READY.json','downloader_ready_sha256')]:
        check('A/ready binding unchanged: '+name,INPUTS[str((A/name).relative_to(ROOT))]['sha256']==release[key])
    check('A stop preserved without raw/partial',a_state['halted'] is True and a_account['A_raw_bytes']==a_account['A_partial_bytes']==0)
    check('initial B execution gates passed',preflight['repair_gate_passes'] and preflight['storage_gate_passes'] and preflight['eu_http_authorized'])
    by_item={r['item_uri']:r for r in frozen};by_mult={r['parent_id']:r for r in multiplicity}
    check('979 terminal ledger identities match frozen targets',len(ledger)==979 and len({r['item_uri'] for r in ledger})==979 and set(r['item_uri'] for r in ledger)==set(by_item))
    check('1009 Works and 30 no-link outcomes preserved',len(population)==1009 and sum(not r['item_uri'] for r in population)==30)
    check('253 multi-Item selected Manifestations retained',sum(int(r['selected_manifestation_distinct_items'])>1 for r in multiplicity)==253)
    states=Counter(r['status'] for r in ledger)
    check('observed terminal status accounting',states==Counter({'downloaded_candidate_original':20,'failed':1,'not_attempted_after_stop':958}))
    check('runner actual counters match terminal ledger',execution['attempted_items']==21 and execution['candidate_originals']==20 and execution['verified_reuse']==0 and phase['request_count']==21)
    check('source failure persists as B stop',execution['status']=='stopped_partial' and phase['halted'] and 'HTTP 406' in phase['stop_reason'])
    handoff=[];remaining=[];received_bytes=0;http_counts=Counter();redirects=0;scoped_raw_files=[]
    for ordinal,r in enumerate(ledger,1):
        f=by_item[r['item_uri']]
        check_fields=['parent_id','expression_uri','manifestation_uri','publication_dates','request_url']
        if not all(r[k]==f[k] for k in check_fields):raise RuntimeError('Terminal lineage differs from frozen row')
        cp={}
        if r['status']!='not_attempted_after_stop':
            cp=load(ROOT/r['checkpoint_path'])
            if not all(cp[k]==r[k] for k in ['parent_id','item_uri',*check_fields[1:]]):
                raise RuntimeError('Checkpoint identity mismatch')
            if cp['status']!=r['status'] or int(cp['byte_count'])!=int(r['byte_count']):
                raise RuntimeError('Checkpoint status/size mismatch')
            http_counts[str(cp.get('http_status',''))]+=1
            redirects+=len(cp.get('redirects',[]))
        if r['status'] in {'downloaded_candidate_original','verified_local_reuse'}:
            raw=ROOT/r['raw_path']
            if not raw.is_file() or raw.stat().st_size!=int(r['byte_count']) or not r['sha256'] or cp['sha256']!=r['sha256']:
                raise RuntimeError('Candidate file/stat/SHA receipt mismatch')
            if not raw.resolve().is_relative_to((OUT/'raw').resolve()):
                raise RuntimeError('Acquired candidate escaped staging root')
            received_bytes+=int(r['byte_count']);scoped_raw_files.append({'path':r['raw_path'],'bytes':raw.stat().st_size,'sha256':r['sha256'],'hash_source':'accepted downloader checkpoint; not rehashed'})
            headers=cp.get('response_headers',{})
            headers_lower={k.lower():v for k,v in headers.items()}
            mult=by_mult[r['parent_id']]
            handoff.append({'parent_id':r['parent_id'],'expression_uri':r['expression_uri'],'manifestation_uri':r['manifestation_uri'],
                'item_uri':r['item_uri'],'source_id':f['source_id'],'jurisdiction':f['jurisdiction'],'issuer':f['issuer'],
                'discourse_role':f['discourse_role'],'genre':f['genre'],'language':f['language'],'publication_month':f['month'],
                'publication_dates':r['publication_dates'],'date_support':f['date_support'],
                'parent_manifest':f['parent_manifest'],'work_query_evidence':f['work_query_evidence'],
                'metadata_checkpoint_utc':f['metadata_checkpoint_utc'],'item_route_evidence':f['item_route_evidence'],
                'request_url':r['request_url'],'final_url':cp.get('final_url',''),'requested_at_utc':cp.get('requested_at_utc',''),
                'retrieved_at_utc':cp.get('retrieved_at_utc',''),'format':f['format'],'raw_path':r['raw_path'],
                'raw_sha256':r['sha256'],'raw_bytes':int(r['byte_count']),'technical_state':r['status'],
                'checkpoint_path':r['checkpoint_path'],'checkpoint_sha256':INPUTS[r['checkpoint_path']]['sha256'],
                'http_status':cp.get('http_status',''),'observed_content_type':headers_lower.get('content-type',''),
                'content_version_etag':headers_lower.get('etag',''),'content_version_last_modified':headers_lower.get('last-modified',''),
                'saved_response_headers_json':json.dumps(headers,ensure_ascii=False,sort_keys=True),
                'sha_verification':'stream saved and SHA256 checked by accepted downloader; sidecar/stat reconciled here',
                'candidate_selected_Item_state':'candidate bytes obtained; PDF signature checked by downloader',
                'selected_Item_readability':'unassessed; no text extraction in this task',
                'identity_date_content_mapping':'Work/Item route lineage retained; original-body title/issuer/printed date/boundary pending',
                'all_distinct_item_alternatives':mult['all_distinct_item_alternatives'],
                'selected_manifestation_distinct_items':mult['selected_manifestation_distinct_items'],
                'observed_selected_Item_count_for_Work':1,'component_roles':'unresolved from relationship metadata',
                'required_component_coverage':'unassessed; no sibling/annex expansion authorised',
                'complete_Work_state':'unassessed; candidate Item does not certify complete Work',
                'historical_version_equivalence':'unassessed; current HTTP version metadata does not prove 2015 wording',
                'rights_boundary':f['rights_access'],'directness_expected':f['directness_expected'],
                'cross_source_dedup':f['cross_source_dedup'],'new_parent_created':False,
                'formal_ingestion_performed':False,'coordinator_writer_action':'serial structural/date/component/readability acceptance before integration'})
        else:
            remaining.append({**f,'terminal_B_status':r['status'],'terminal_error_or_not_attempted_reason':r['error'],
                'checkpoint_path':r['checkpoint_path'],'automatic_retry_authorized':False,
                'next_action':'retain persistent B stop; coordinator decision required before any further HTTP'})
    check('actual response and sidecar counts match attempts',http_counts==Counter({'200':20,'406':1}) and len([p for p in INPUTS if '/02_eu_staging/requests/' in p])==21)
    check('candidate byte total matches runtime raw accounting',received_bytes==9020646==execution['raw_accounting']['total_bytes'] and execution['raw_accounting']['partial_bytes']==0)
    check('candidate-only handoff and remainder reconcile',len(handoff)==20 and len(remaining)==959 and len(handoff)+len(remaining)==979)
    csv_write('STAGING_INGESTION_HANDOFF.csv',handoff)
    csv_write('B_REMAINING_TARGETS.csv',remaining)
    csv_write('B_NO_LINK_WORKS.csv',[r for r in population if not r['item_uri']])
    coverage=[]
    for month in [f'2015-{m:02d}' for m in range(1,13)]:
        month_states=Counter(r['status'] for r in ledger if by_item[r['item_uri']]['month']==month)
        coverage.append({'month':month,'enumerated_Works':sum(r['month']==month for r in population),
            'frozen_selected_Item_targets':sum(r['month']==month for r in frozen),
            'no_link_Works':sum(r['month']==month and not r['item_uri'] for r in population),
            'candidate_Items_downloaded':month_states['downloaded_candidate_original'],'verified_local_reuse':month_states['verified_local_reuse'],
            'failed':month_states['failed'],'not_attempted_after_stop':month_states['not_attempted_after_stop'],
            'readable_selected_Items_verified':0,'complete_Works_verified':0,
            'scope':'observed candidate bytes only; publication month follows saved Work metadata'})
    csv_write('B_COVERAGE_EXPECTED_VS_OBSERVED.csv',coverage)
    for name in ['RESULT.json','HANDOFF_zh.md','LOG_ENTRY.md','OUTPUT_RECEIPT.json']:
        path=OUT/name;archive=OUT/(path.stem+'.local_preparation'+path.suffix)
        if path.exists() and not archive.exists():shutil.copyfile(path,archive)
    failed=next(r for r in ledger if r['status']=='failed')
    now=datetime.now(timezone.utc);free=shutil.disk_usage(OUT).free
    total_cap=contract['budget']['aggregate_new_raw_cap_bytes'];remaining_cap=total_cap-received_bytes
    extra_reserve=sum(contract['budget'][k] for k in ['inflight_object_reserve_bytes','checkpoint_error_reserve_bytes','repair_other_activity_reserve_bytes'])
    notes=[]
    if execution.get('downloads_started') is False and execution['attempted_items']>0:
        notes.append({'field':'EXECUTION_RESULT.json.downloads_started','saved_value':False,
            'interpretation':'carried forward from preflight; execution attempted_items/phase request count/checkpoints show 21 real HTTP attempts',
            'correction_in_this_derived_result':'downloads_started=true; original runtime receipt preserved unchanged'})
    dump('RUNNER_REPORTING_NOTES.json',{'notes':notes,'downloader_modified_by_this_worker':False,'runtime_receipt_modified':False})
    receipt={'created_at_utc':now.isoformat(),'inputs':INPUTS,'scoped_raw_size_and_sha_receipts':scoped_raw_files,
        'accepted_single_execution_command':'.venv/bin/python work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py --execute --repair-ready-sha256 7e885c328ebedf70c486c0bc0afb6e505318665ef0eeebeb6464fb66077cf805',
        'network_execution':'normal require_escalated execution approved; native exec session 6068 completed exit 0; script recorded stopped_partial',
        'downloader_launches_this_worker':1,'retries_or_alternate_routes_this_worker':0,'extra_raw_rehashes_during_handoff':0,
        'sealed_evaluator_or_credential_access':False,'verification_checks':CHECKS,'passed_checks':len(CHECKS)}
    dump('EXECUTION_INPUT_RECEIPT.json',receipt)
    result={'status':'stopped_partial','task_status':'single_authorized_execution_and_terminal_handoff_complete',
        'reported_at_utc':now.isoformat(),'reported_at_local':now.astimezone(ZoneInfo('Asia/Shanghai')).isoformat(),
        'downloads_started':True,'candidate_acquisition_complete':False,
        'fixed_publication_interval':['1988-01-01','2026-09-21'],'september_2026_partial':True,
        'tranche_publication_interval':['2015-01-01','2015-12-31'],'frozen_manifest_sha256':EXPECTED_MANIFEST,
        'accepted_downloader_sha256':EXPECTED_RUNNER,'downloader_version':release['downloader_version'],
        'execution_finished_at_utc':execution['finished_at_utc'],'command_launches':1,'process_exit_code':0,
        'frozen_selected_Item_targets':979,'enumerated_Works':1009,'no_link_Works':30,
        'HTTP_requests_B':phase['request_count'],'attempted_selected_Items':21,'new_candidate_Items':20,
        'verified_local_reuse':0,'failed_Items':1,'not_attempted_after_stop':958,'remaining_targets':959,
        'redirect_HTTP_requests':redirects,'candidate_raw_bytes':received_bytes,'retained_partial_bytes':0,
        'A_raw_bytes':a_account['A_raw_bytes'],'A_partial_bytes':a_account['A_partial_bytes'],
        'shared_new_raw_cap_bytes':total_cap,'shared_new_raw_bytes':received_bytes,'remaining_shared_raw_budget_bytes':remaining_cap,
        'stop_reason':phase['stop_reason'],'failed_Item':failed,'B_stop_persistent':phase['halted'],
        'automatic_restart':False,'failed_route_retry':False,'alternate_sibling_annex_expansion':False,
        'storage_end':{'free_bytes':free,'free_gib':free/2**30,'floor_bytes':contract['budget']['collector_floor_bytes'],
            'remaining_cap_plus_existing_extra_reserves_bytes':remaining_cap+extra_reserve,
            'projected_remaining_gib':(free-remaining_cap-extra_reserve)/2**30},
        'source_completeness':{'selected_Item_readability_verified':0,'original_body_identity_date_verified':0,
            'required_components_verified':0,'complete_Work_verified':0,'selected_manifestation_multi_Item_Works_total':253,
            'selected_manifestation_multi_Item_Works_in_candidate_handoff':sum(int(r['selected_manifestation_distinct_items'])>1 for r in handoff),
            'historical_version_equivalence':'unassessed'},
        'method_boundaries':{'text_extraction':False,'formal_database_writes':0,'new_parents_created':0,
            'database_read_scope':'accepted runner targeted read-only repair_runs active-run/checkpoint verification; no corpus scan',
            'database_read_count':'not instrumented; not claimed zero','raw_rehashes_in_handoff':0,
            'semantic_topic_emotion_fear_filters':False,'commit':False,'push':False,'sealed_reviewer_access':False},
        'evidence_levels':{'1':'20 saved candidate selected Items with hashes and dates from preexisting Work metadata; readable/complete originals pending',
            '2':'climate/warming relevance and similarity unassessed','3':'affect/risk/future-harm/responsibility unassessed','4':'fear-specific interpretation unassessed'},
        'reporting_notes':notes,'final_handoff_checks_passed':len(CHECKS),
        'historical_preparation_preserved':'LOCAL_PREPARATION.json and original input receipt; prior report snapshots archived locally',
        'primary_outputs':['RESULT.json','LOG_ENTRY.md','HANDOFF_zh.md','STAGING_INGESTION_HANDOFF.csv','B_STATUS_LEDGER.csv',
            'B_REMAINING_TARGETS.csv','B_NO_LINK_WORKS.csv','B_COVERAGE_EXPECTED_VS_OBSERVED.csv','EXECUTION_PREFLIGHT.json',
            'EXECUTION_RESULT.json','EXECUTION_STDOUT.log','PHASE_HTTP_STATE.json','EXECUTION_INPUT_RECEIPT.json','RUNNER_REPORTING_NOTES.json'],
        'next_action':'Coordinator/single writer reviews the 20 candidate-byte handoff for later serial readability/identity/date/component acceptance. Keep the HTTP406 route and 959 remaining targets stopped; no automatic resumption or substitute queue.'}
    dump('RESULT.json',result)
    print(json.dumps({'status':result['status'],'new_candidates':20,'failed':1,'not_attempted':958,
        'raw_bytes':received_bytes,'partial_bytes':0,'checks_passed':len(CHECKS),
        'multipart_candidates':result['source_completeness']['selected_manifestation_multi_Item_Works_in_candidate_handoff']}))


if __name__=='__main__':main()
