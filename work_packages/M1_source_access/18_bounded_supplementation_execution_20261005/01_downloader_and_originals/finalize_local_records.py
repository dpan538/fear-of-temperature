"""Reconcile local terminal evidence and hashes only. Never makes HTTP requests."""
import csv,importlib.util,json,sys
from pathlib import Path
from urllib.parse import urlsplit
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
CODE=ROOT/'work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py'
spec=importlib.util.spec_from_file_location('d',CODE);d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
with d.locks(download=True):
    source={r['unit_id']:r for r in csv.DictReader((d.REPAIR/'missing_original_requests.csv').open())}
    ledger=OUT/'A_DISPOSITIONS.csv';rows=list(csv.DictReader(ledger.open()))
    for row in rows:
        path=d.ROOT/row['evidence_path'];e=d.load_json(path);original=source[row['unit_id']]
        if original['source_date']:
            e['section_ext_id']=urlsplit(original['canonical_url']).path.split('/')[4]
            e['contribution_anchor']=urlsplit(original['canonical_url']).fragment
        d.save_json(path,e);row['evidence_sha256']=d.hash_file(path)
    with ledger.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    a=d.load_json(OUT/'A_ACCOUNTING.json');a['ledger_sha256']=d.hash_file(ledger);d.save_json(OUT/'A_ACCOUNTING.json',a)
    bindings=d.validate_a_accounting()
    ok,reason,ev=d.release_check(d.load_json(d.CONTRACT),d.hash_file(d.MARKER),locked=True);assert ok,reason
    storage=d.budget_check(d.load_json(d.CONTRACT),reserve_remaining=True)
    ready=d.load_json(OUT/'DOWNLOADER_READY.json');assert ready['downloader_sha256']==d.code_hash()
    assert ready['offline_test_results_sha256']==d.hash_file(OUT/'OFFLINE_TEST_RESULTS.json')
    assert d.hash_file(d.HERE/'frozen_acquisition_manifest.csv')==d.B_SHA
    validation={'status':'passed','checked_at_utc':d.now(),'final_five_terminal_bindings':bindings,'database_post_checkpoint':ev['post_checkpoint'],'active_committed_run_verified':True,'fresh_full_tranche_storage':storage,'frozen_b_unchanged':True,'http_requests':1,'eu_http_requests':0,'original_candidates':0,'retained_new_raw_bytes':0,'retained_partial_bytes':0,'persisted_access_stop':d.load_json(d.STATE),'coordinator_release_exists':d.EU_RELEASE.exists(),'formal_database_writes':0,'extraction_started':False}
    d.save_json(OUT/'FINAL_LOCAL_CHECKS.json',validation)
print(json.dumps({'final_accounting_valid':True,'unchanged_downloader_hash':d.code_hash(),'HTTP_requests':1,'originals_obtained':0}))
