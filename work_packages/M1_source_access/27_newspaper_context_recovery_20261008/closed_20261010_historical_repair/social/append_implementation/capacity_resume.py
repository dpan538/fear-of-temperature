"""Same-release append phase: materialized snapshot is not an outstanding tail."""
import sys,json,math,hashlib,os,datetime as dt
from pathlib import Path
PHASE=Path(__file__).resolve().parent
ORIGINAL=PHASE.parent
sys.path.insert(0,str(ORIGINAL))
import transport as t,entities as e,collect
ORIGINAL_READ=t.read_json
OWNER_RELEASE=ORIGINAL.parent/'control/OWNER_RELEASE.json'
def phase_read(path,default=None):
    if Path(path)==PHASE.parent/'control/OWNER_RELEASE.json':path=OWNER_RELEASE
    return ORIGINAL_READ(path,default)
t.read_json=phase_read
t.WORK=PHASE
collect.FRONT=PHASE/'FRONTIERS.json'
candidate_versions=0
DELIVERY=ORIGINAL_READ(ORIGINAL/'summaries/delivery_file_manifest.json')
BASE=ORIGINAL_READ(PHASE/'PHASE_BASELINE.json')
MEASURED=ORIGINAL_READ(ORIGINAL/'summaries/collection_manifest.json')
entity_bytes=next(x['bytes'] for x in DELIVERY['files'] if x['path'].endswith('native_entities_manifest.csv.gz'))
version_bytes=sum(x['bytes'] for x in DELIVERY['files'] if any(s in x['path'] for s in ['changed_content_versions','changed_observations','changed_relations','changed_source_provenance','publication_memberships','native_aliases']))
ENTITY_RATE=math.ceil(2*entity_bytes/BASE['counts']['native_entities'])
VERSION_RATE=math.ceil(2*version_bytes/MEASURED['new_entity_versions'])
METADATA_RATE=ORIGINAL_READ(ORIGINAL/'ACQUISITION_TAIL_ACCOUNTING.json')['metadata_bytes_per_changed_version_upper_estimate']
def delta_tail_values(new_versions,new_entities,annotated=0,pending_candidates=0):
    unannotated=max(0,new_versions-annotated)+pending_candidates
    exports=(new_versions+pending_candidates)*VERSION_RATE+(new_entities+pending_candidates)*ENTITY_RATE+16*1048576
    return {'bytes':unannotated*METADATA_RATE+exports+64*1048576,
            'unannotated_phase_versions':unannotated,'metadata_bytes':unannotated*METADATA_RATE,
            'delta_export_bytes':exports,'bounded_metadata_journal_bytes':64*1048576,
            'materialized_closed_snapshot_tail_bytes':0,
            'basis':'2x measured completed per-version and per-entity compressed metadata; 16 MiB delta envelope; measured metadata upper rate; 64 MiB bounded metadata journal'}
def phase_tail(scope):
    if t.TERMINAL_OPERATION:return {'bytes':0,'phase':'terminal_delta_operation_consumes_reserved_tail'}
    st=t.state()
    return delta_tail_values(st.get('new_entity_versions',0),st.get('new_entities',0),0,candidate_versions)
t.acquisition_tail=phase_tail
original_load=e.load
def load_with_pending_tail(records,rec,frame):
    global candidate_versions
    candidate_versions=len(records)
    try:return original_load(records,rec,frame)
    finally:candidate_versions=0
e.load=load_with_pending_tail
original_fetch=t.fetch
def recover_local_dns_only(url,source_id,purpose='policy',cap=None,recovery_evidence=None):
    proof=PHASE/'SANDBOX_TRANSPORT_FAILURE_EVIDENCE.json'
    if proof.exists() and recovery_evidence is None:
        key=t.sha((source_id+'|'+purpose+'|'+url).encode())[:24]
        approved=ORIGINAL_READ(proof)['original_attempts'].get(key)
        if approved:
            receipt=PHASE/'receipts'/f'{key}.json'
            assert t.sha(receipt.read_bytes())==approved['receipt_sha256']
            recovery_evidence='local_sandbox_dns_failure:'+t.sha(proof.read_bytes())
    return original_fetch(url,source_id,purpose,cap,recovery_evidence)
t.fetch=recover_local_dns_only

def fixture():
    empty=delta_tail_values(0,0)
    one=delta_tail_values(1,1)
    settled=delta_tail_values(100,100,100)
    pending=delta_tail_values(0,0,0,100)
    assert empty['materialized_closed_snapshot_tail_bytes']==0
    assert empty['bytes']==80*1048576
    assert one['bytes']-empty['bytes']==METADATA_RATE+VERSION_RATE+ENTITY_RATE
    assert settled['metadata_bytes']==0 and settled['delta_export_bytes']>empty['delta_export_bytes']
    assert pending['metadata_bytes']==100*METADATA_RATE
    old=ORIGINAL_READ(ORIGINAL/'FINAL_ACTUAL_ACCOUNTING.json')
    assert old['budget']['social_bytes']+empty['bytes']+23068672+65536<8_000_000_000
    return {'passed':True,'checks':5,'entity_export_upper_bytes_per_entity':ENTITY_RATE,'version_export_upper_bytes_per_version':VERSION_RATE,'metadata_upper_bytes_per_version':METADATA_RATE,'fixed_delta_and_journal_envelope_bytes':80*1048576,'closed_exports_already_charged_as_actual_bytes':True,'caps_deadline_provider_stops_unchanged':True}

def main():
    test=fixture();t.atomic(PHASE/'DELTA_TAIL_REGRESSION.json',test)
    scope=t.release()
    before_hash={str(p.relative_to(ORIGINAL)):t.sha(p.read_bytes()) for p in [ORIGINAL/'CLOSED.json',*list((ORIGINAL/'summaries').iterdir())] if p.is_file()}
    with t.shared(23068672) as budget:pass
    recheck={'at_utc':t.utc(),'decision':'resume_existing_capacity_blocked_historical_routes_under_same_owner_release','original_deadline_at_utc':scope['hard_deadline_at_utc'],'publication_cutoff':'2026-09-21','measured_complete_next_operation':budget,'model_fixture':test,'closed_snapshot_hashes':before_hash,'phase_directory':str(PHASE),'scope_digest':t.sha(t.SCOPE_PATH.read_bytes()),'code_fix':'phase tail excludes settled metadata and already-materialized full exports; new response candidate versions reserve metadata and delta exports before Load','first_resumed_HTTP':None,'first_resumed_Load':None,'limitations':['Technical-community frame and mailing-list concentration remain explicit','Source/provider prohibitions and quotas unchanged','No new source admission, full export or old corpus audit']}
    if not (ORIGINAL/'COORDINATOR_CAPACITY_RECHECK.json').exists():t.atomic(ORIGINAL/'COORDINATOR_CAPACITY_RECHECK.json',recheck)
    t.atomic(PHASE/('PHASE_START_RECEIPT.json' if not (PHASE/'PHASE_START_RECEIPT.json').exists() else 'NETWORK_RECOVERY_START_RECEIPT.json'),recheck)
    collect.main()

if __name__=='__main__':main()
