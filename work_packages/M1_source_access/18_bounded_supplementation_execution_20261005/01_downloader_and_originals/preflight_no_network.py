"""Local input/release/storage preflight. Denies network; no B execution/output mutation."""
import importlib.util,json,socket,sys
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
CODE=ROOT/'work_packages/M1_source_access/15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/stage_frozen_items.py'
s=importlib.util.spec_from_file_location('d',CODE);d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
attempts=[]
def deny(*args,**kwargs):
    attempts.append(str(args[:1]));raise AssertionError('Network prohibited by this preflight')
with patch('socket.socket.connect',side_effect=deny),patch('socket.socket.connect_ex',side_effect=deny),patch('socket.create_connection',side_effect=deny),patch('requests.sessions.Session.request',side_effect=deny):
    with d.locks(download=True):
        ready=d.load_json(OUT/'DOWNLOADER_READY.json')
        assert ready['downloader_sha256']==d.code_hash()
        state=d.preflight(d.load_json(d.CONTRACT),ready['repair_release_sha256'],locked=True,execution=True)
        state.update(network_attempts=attempts,mode='network_denied_local_preflight_only',A_http_state_sha256=d.hash_file(d.STATE),final_A_bindings=d.validate_a_accounting(),formal_database_writes=0,EU_HTTP_requests=0)
        d.save_json(OUT/'NO_NETWORK_PREFLIGHT.json',state)
print(json.dumps(state,ensure_ascii=False))
raise SystemExit(0 if state['repair_gate_passes'] and state['storage_gate_passes'] and not attempts else 1)
