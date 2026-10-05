"""Network-denied offline fixtures plus one targeted read-only real release check."""
import copy
import csv
import importlib.util
import json
import socket
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[4]
CODE=ROOT/'work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py'
spec=importlib.util.spec_from_file_location('downloader',CODE)
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
REAL={k:getattr(d,k) for k in ['ROOT','HERE','WP','STAGE','A_OUT','B_OUT','REPAIR','MARKER','DB','HEAVY','DOWNLOAD_LOCK','STATE','EU_RELEASE','CONTRACT']}
CONTRACT=d.load_json(d.CONTRACT)
MARKER_SHA=d.hash_file(d.MARKER)
NETWORK_CALLS=[]
def deny(*args,**kwargs):
    NETWORK_CALLS.append(str(args[:1]));raise AssertionError('Network forbidden during offline validation')

class FakeResponse:
    def __init__(self,body=b'%PDF-1.7\nfixture',headers=None,status=200):
        self.body=body;self.headers=headers or {};self.status_code=status;self.url='https://example.test/object'
    def iter_content(self,n):
        yield self.body[:7];yield self.body[7:]
    def close(self): pass

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name).resolve()
        for k,p in REAL.items(): setattr(d,k,self.base/p.relative_to(REAL['ROOT']))
        d.ROOT=self.base
        for folder in [d.HERE,d.REPAIR,d.MARKER.parent,d.HEAVY.parent,d.A_OUT,d.B_OUT]:folder.mkdir(parents=True,exist_ok=True)
        for name in ['ACCEPTANCE.json','RESULT.json','CHANGE_MANIFEST.json','APPLIED.json','missing_original_requests.csv']:
            (d.REPAIR/name).write_bytes((REAL['REPAIR']/name).read_bytes())
        d.MARKER.write_bytes(REAL['MARKER'].read_bytes())
        d.DB.parent.mkdir(parents=True,exist_ok=True);d.DB.write_bytes(b'fixture database')
        cp=d.load_json(d.MARKER)['post_checkpoint']
        self.cp=cp
        self.patches=[patch.object(d,'checkpoint',return_value=cp),patch.object(d,'active_run',return_value=(True,d.RULE,d.load_json(d.MARKER)['plan_sha256'],d.load_json(d.REPAIR/'APPLIED.json')['committed_at_utc'],str((d.REPAIR/'PLAN.json').relative_to(d.ROOT)))),patch.object(d.shutil,'disk_usage',return_value=type('Disk',(),{'free':100*d.GIB})())]
        for p in self.patches:p.start()
        d.save_json(d.A_OUT/'DOWNLOADER_READY.json',{'status':'ready','downloader_sha256':d.code_hash(),'a_manifest_sha256':d.A_SHA,'repair_release_sha256':d.hash_file(d.MARKER)})
        self.row={'unit_id':sorted(d.A_IDS)[0],'parent_id':'fixture-parent','item_uri':'fixture-item','expression_uri':'fixture-expression','manifestation_uri':'fixture-manifestation','request_url':'https://example.test/object','publication_dates':'2015-01-01','format':'pdf','staging_path':'raw/fixture.bin','max_object_bytes':'100'}
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        for k,p in REAL.items():setattr(d,k,p)
        self.tmp.cleanup()
    def release(self):return d.release_check(CONTRACT,d.hash_file(d.MARKER),locked=True)
    def change_marker(self,**values):
        marker=d.load_json(d.MARKER);marker.update(values);d.save_json(d.MARKER,marker)
    def stream(self,response):
        with patch('requests.get',return_value=response):
            return d.stream_one(self.row,CONTRACT,output_dir=d.A_OUT,allowed_hosts={'example.test'})
    def test_real_schema_accepted(self):self.assertTrue(self.release()[0])
    def test_staged_and_wrong_interval_rejected(self):
        self.change_marker(status='staged_only');self.assertFalse(self.release()[0])
        self.change_marker(status='committed_repairs_checked_targeted_acquisition_released',fixed_publication_interval=['1988-01-01','2026-10-05']);self.assertFalse(self.release()[0])
    def test_missing_and_modified_A_rejected(self):
        p=d.REPAIR/'missing_original_requests.csv';b=p.read_bytes();p.unlink();self.assertFalse(self.release()[0]);p.write_bytes(b+b'\n');self.assertFalse(self.release()[0])
    def test_wrong_marker_hash_and_run_rejected(self):
        self.assertFalse(d.release_check(CONTRACT,'bad',locked=True)[0]);self.change_marker(run_id='old_run');self.assertFalse(self.release()[0])
    def test_inactive_and_wrong_committed_plan_rejected(self):
        with patch.object(d,'active_run',return_value=(False,d.RULE,'bad','date')):self.assertFalse(self.release()[0])
        with patch.object(d,'active_run',return_value=(True,d.RULE,'bad','date')):self.assertFalse(self.release()[0])
    def test_moved_and_wrong_current_checkpoint_rejected(self):
        cp={**self.cp,'path':'other.duckdb'};self.change_marker(post_checkpoint=cp);self.assertFalse(self.release()[0])
        self.change_marker(post_checkpoint=self.cp)
        with patch.object(d,'checkpoint',return_value={**self.cp,'mtime_ns':0}):self.assertFalse(self.release()[0])
    def test_path_spoofing_and_linked_acceptance_rejected(self):
        self.change_marker(acceptance_path=str(d.REPAIR/'../03_existing_data_repair/ACCEPTANCE.json'));self.assertFalse(self.release()[0])
    def test_linked_evidence_conflict_rejected(self):
        p=d.REPAIR/'ACCEPTANCE.json';j=d.load_json(p);j['status']='failed';d.save_json(p,j);self.assertFalse(self.release()[0])
    def test_B_needs_coordinator_even_with_repair_release(self):
        self.assertRaises(RuntimeError,d.eu_release_check,self.release()[2])
        d.save_json(d.EU_RELEASE,{'ready':True,'issuer':'worker','status':'ready'});self.assertRaises(RuntimeError,d.eu_release_check,self.release()[2])
    def test_full_B_binding_accepts_then_rejects_wrong_hashes(self):
        (d.HERE/'frozen_acquisition_manifest.csv').write_bytes((REAL['HERE']/'frozen_acquisition_manifest.csv').read_bytes())
        rows=[]
        for i,unit in enumerate(sorted(d.A_IDS)):
            p=d.A_OUT/f'evidence_{i}.json';d.save_json(p,{'unit_id':unit,'terminal_status':'bounded_unavailable'})
            rows.append({'unit_id':unit,'terminal_status':'bounded_unavailable','evidence_path':str(p.relative_to(d.ROOT)),'evidence_sha256':d.hash_file(p)})
        ledger=d.A_OUT/'A_DISPOSITIONS.csv'
        with ledger.open('w',newline='') as h:
            w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        d.save_json(d.A_OUT/'A_ACCOUNTING.json',{'complete':True,'unit_ids':sorted(d.A_IDS),'source_manifest_sha256':d.A_SHA,'ledger_sha256':d.hash_file(ledger),'A_raw_files':[]})
        evidence=self.release()[2]
        release={'ready':True,'status':'coordinator_accepted_downloader_and_A_released_B','issuer':'coordinator','downloader_version':d.VERSION,'downloader_sha256':d.code_hash(),'repair_release_sha256':evidence['marker_sha256'],'frozen_b_manifest_sha256':d.B_SHA,'run_id':d.RUN,'fixed_publication_interval':d.INTERVAL,'post_checkpoint':evidence['post_checkpoint'],**d.validate_a_accounting(),'downloader_ready_sha256':d.hash_file(d.A_OUT/'DOWNLOADER_READY.json')}
        d.save_json(d.EU_RELEASE,release);self.assertEqual(d.eu_release_check(evidence)['a_manifest_sha256'],d.A_SHA)
        for key in ['downloader_sha256','repair_release_sha256','a_manifest_sha256','a_ledger_sha256','a_accounting_sha256','frozen_b_manifest_sha256','post_checkpoint','downloader_ready_sha256']:
            d.save_json(d.EU_RELEASE,{**release,key:'wrong'});self.assertRaises(RuntimeError,d.eu_release_check,evidence)
        d.save_json(d.EU_RELEASE,release);ledger.unlink();self.assertRaises(RuntimeError,d.eu_release_check,evidence)
    def test_A_B_and_old_partials_share_budget(self):
        for i,p in enumerate(d.raw_roots()):p.mkdir(parents=True);(p/f'{i}.part').write_bytes(b'x'*10)
        self.assertEqual(d.raw_accounting()['total_bytes'],30);self.assertEqual(d.raw_accounting()['partial_bytes'],30)
        self.assertRaises(RuntimeError,d.budget_check,CONTRACT,2*d.GIB-29)
    def test_floor_includes_transient_checkpoint_other_reserves(self):
        with patch.object(d.shutil,'disk_usage',return_value=type('Disk',(),{'free':15*d.GIB+1000})()):self.assertRaises(RuntimeError,d.budget_check,CONTRACT,1)
    def test_cooldown_survives_rerun_and_elapsed_still_halts(self):
        d.save_json(d.STATE,{'retry_not_before_utc':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()});self.assertRaises(RuntimeError,d.network_guard)
        d.save_json(d.STATE,{'halted':True,'stop_reason':'429 unresolved','retry_not_before_utc':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()});self.assertRaises(RuntimeError,d.network_guard)
    def test_persisted_spacing(self):
        d.save_json(d.STATE,{'last_request_finished_utc':d.now()})
        with patch.object(d.time,'sleep') as sleep:d.network_guard();self.assertGreaterEqual(sleep.call_args.args[0],1.8)
    def test_429_invalid_retry_after_has_persistent_default(self):
        result=self.stream(FakeResponse(status=429,headers={'Retry-After':'invalid'}));self.assertEqual(result['status'],'failed')
        state=d.load_json(d.STATE);self.assertTrue(state['halted']);self.assertIn('retry_not_before_utc',state)
    def test_success_length_signature_hash_and_reuse(self):
        b=b'%PDF-1.7\nfixture';result=self.stream(FakeResponse(b,{'Content-Length':str(len(b))}));self.assertEqual(result['status'],'downloaded_candidate_original')
        p=d.ROOT/result['raw_path'];cp=d.ROOT/result['checkpoint_path'];self.assertEqual(d.verified_reuse(self.row,p,cp)['status'],'verified_local_reuse')
        p.write_bytes(b'x'*len(b));self.assertRaises(RuntimeError,d.verified_reuse,self.row,p,cp)
    def test_reuse_wrong_lineage_length_and_signature(self):
        p=d.A_OUT/'raw/fixture.bin';p.parent.mkdir();p.write_bytes(b'%PDF-fixture');cp=d.A_OUT/'meta.json'
        meta={**self.row,'status':'downloaded','byte_count':p.stat().st_size,'sha256':d.hash_file(p)};d.save_json(cp,meta)
        for changed in [{'parent_id':'other'},{'byte_count':1}]:d.save_json(cp,{**meta,**changed});self.assertRaises(RuntimeError,d.verified_reuse,self.row,p,cp)
        p.write_bytes(b'<html>error');d.save_json(cp,{**meta,'byte_count':p.stat().st_size,'sha256':d.hash_file(p)});self.assertRaises(RuntimeError,d.verified_reuse,self.row,p,cp)
    def test_stream_cap_and_partial_preservation(self):
        result=self.stream(FakeResponse(b'%PDF-'+b'x'*110));self.assertEqual(result['status'],'failed');self.assertIn('partial_path',result);self.assertGreater(d.raw_accounting()['partial_bytes'],0)
        self.assertRaises(RuntimeError,d.stream_one,self.row,CONTRACT,d.A_OUT,'pdf',{'example.test'})
    def test_bad_content_length_and_truncated_body(self):
        for length in ['invalid','101','1']:
            with self.subTest(length=length):
                self.row['request_url']='https://example.test/'+length;self.row['staging_path']='raw/'+length+'.bin'
                if d.STATE.exists():d.STATE.unlink() # fixture isolation; production never clears stops
                result=self.stream(FakeResponse(headers={'Content-Length':length}));self.assertEqual(result['status'],'failed')
    def test_stream_floor_and_shared_cap_checked_inside_stream(self):
        with patch.object(d,'budget_check',side_effect=[{},RuntimeError('floor reserve')]):
            result=self.stream(FakeResponse());self.assertEqual(result['status'],'failed');self.assertIn('floor reserve',result['error'])
    def test_bad_pdf_and_unapproved_redirect_rejected(self):
        result=self.stream(FakeResponse(b'<html>login'));self.assertEqual(result['status'],'failed')
    def test_redirect_may_not_escape_host_or_limit(self):
        result=self.stream(FakeResponse(status=302,headers={'Location':'https://other.test/file'}));self.assertEqual(result['status'],'failed');self.assertIn('host',result['error'])
    def test_missing_readiness_denies_A_without_HTTP(self):
        (d.A_OUT/'DOWNLOADER_READY.json').unlink()
        with patch('requests.get') as get:
            self.assertRaises(FileNotFoundError,d.stream_one,self.row,CONTRACT,d.A_OUT,'pdf',{'example.test'});get.assert_not_called()
    def test_raw_symlink_rejected(self):
        p=d.A_OUT/'raw';p.symlink_to(d.B_OUT);self.assertRaises(RuntimeError,d.raw_accounting)

if __name__=='__main__':
    # Deny low-level sockets and ordinary HTTP; only individual fixture tests may mock requests.get.
    with patch('socket.socket.connect',side_effect=deny),patch('socket.socket.connect_ex',side_effect=deny),patch('socket.create_connection',side_effect=deny),patch('requests.sessions.Session.request',side_effect=deny):
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        real=d.release_check(CONTRACT,MARKER_SHA)
        report={'status':'passed' if result.wasSuccessful() and real[0] and not NETWORK_CALLS else 'failed','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'network_policy':'socket connect/connect_ex, create_connection and Session.request deny; HTTP fixture responses only','network_attempts':NETWORK_CALLS,'real_release_check':real,'formal_database_writes':0,'tested_code_sha256':d.code_hash(),'version':d.VERSION,'checked_at_utc':d.now()}
        d.save_json(REAL['A_OUT']/'OFFLINE_TEST_RESULTS.json',report)
    raise SystemExit(0 if report['status']=='passed' else 1)
