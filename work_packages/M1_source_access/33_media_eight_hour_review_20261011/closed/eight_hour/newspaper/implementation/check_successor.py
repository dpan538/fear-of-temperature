"""Targeted transfer/deadline and incremental-reserve fixtures, no corpus reads."""
from pathlib import Path
import json,ast,datetime as dt
W=Path(__file__).resolve().parent
REPO=W.parents[5]
SCOPE=json.loads((W/'EXECUTION_SCOPE.json').read_text())
BINDING=json.loads((W/'SUCCESSOR_INPUT_BINDING.json').read_text())
CHECKS=[]
def check(name,ok,evidence):CHECKS.append(dict(name=name,passed=bool(ok),evidence=evidence))
check('terminal_predecessor_bound',BINDING['predecessor_terminal_verified'],BINDING['predecessor_final_receipts_sha256'])
check('fixed_successor_interval',SCOPE['earliest_network_and_load_start_at_utc']=='2026-10-10T10:27:04+00:00' and SCOPE['hard_deadline_at_utc']=='2026-10-10T18:27:04+00:00','Absolute interval; preparation delay does not move deadline')
check('quantity_and_score_guards_retired',all(SCOPE[k] is None for k in ['article_count_cap','max_http_requests_including_access_and_policy_probes','max_distinct_native_content_objects','discovery_distinct_targets_per_stratum','article_distinct_target_attempts_per_stratum']) and not SCOPE['coverage_score_is_control_input'] and not SCOPE['parent_metrics_are_control_input'],'Provider/access/byte/physical stops retained')
check('runtime_syntax',all(ast.parse(p.read_text()) is not None for p in W.glob('*.py')),'Prepared code only; no request or Load during check')
s=(W/'elt.py').read_text()
check('receipt_and_queue_predecessors_retained','NINE_HOUR_PREDECESSOR' in s and '20261010_four_hour_historical_repair/worker' in s,'Current terminal plus older lookup roots')
old=REPO/SCOPE['predecessor_worker_reference']
original_stops=json.loads((old/'TRANSPORT_STATE.json').read_text())['access_stops'];current_stops=json.loads((W/'TRANSPORT_STATE.json').read_text())['access_stops']
check('source_and_pdf_stops_preserved',SCOPE['inherited_historical_pdf_issues']==SCOPE['max_new_historical_issues']==36 and all(current_stops.get(host)==evidence for host,evidence in original_stops.items()),'All36 consumed slots; every inherited host stop retained unchanged, with new actual stops allowed')
tree=ast.parse((W/'incremental_exports.py').read_text())
ns={'READ_BUFFER_PEAK':0}
pure=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['pending_write_peak','remaining_unmaterialised_bytes']]
exec(compile(ast.Module(body=pure,type_ignores=[]),'incremental-export-fixtures','exec'),ns)
check('materialised_exports_not_reserved_again',ns['pending_write_peak'](20_000_000)==40_065_536,'Future20MB payload needs40MB temp/final peak; retained prior exports remain inside used bytes, not another487MB reserve')
check('large_incremental_write_still_stops',ns['pending_write_peak'](300_000_000)>500_000_000,'Real600MB+write peak exceeds500MB remaining capacity')
ns['READ_BUFFER_PEAK']=100_000_000
check('read_decompression_buffers_retained',ns['pending_write_peak'](20_000_000)==140_065_536,'Measured read/decompression buffers stay in conservative peak')
check('materialised_and_partial_delta_fixtures',ns['remaining_unmaterialised_bytes'](1000,1000)==0 and ns['remaining_unmaterialised_bytes'](1000,400)==600 and ns['remaining_unmaterialised_bytes'](1000,1200)==0,'Complete/partial metadata creates no negative reserve or fictitious free bytes')
result=dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),all_passed=all(c['passed'] for c in CHECKS),checks=CHECKS,prior_accepted_changed_chain_checks_reused=26,prior_check_reference=str((old/'CHANGED_CHAIN_CHECK.json').relative_to(REPO)),no_old_body_or_raw_audit=True,real_Load_executed=False)
(W/'CHANGED_CHAIN_CHECK.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['all_passed'],CHECKS
print(json.dumps({'targeted_checks_passed':len(CHECKS),'no_corpus_or_network_operation':True}))
