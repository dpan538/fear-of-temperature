"""Bind one new six-hour writer to the canonical release, then run regular ELT."""
import os,json,datetime as dt
import elt,run

def binding():
 c=(elt.REPO/elt.SCOPE['owner_release_reference']).parent if elt.SCOPE.get('owner_release_reference') else elt.OWN.parent/'control';r=json.loads((c/'OWNER_RELEASE.json').read_text());s=(c/'EXECUTION_SCOPE.json').read_bytes()
 assert r['status'] in ['RELEASED_CONDITIONAL_ON_ACTUAL_PREFLIGHT','RELEASED_CONDITIONAL_ON_ROUTE_FREEZE_BINDING_AND_ACTUAL_PREFLIGHT']
 assert r['owner_thread_id']==elt.SCOPE['owner_thread_id']==os.environ['CODEX_THREAD_ID']
 assert elt.sha(s)==elt.sha((elt.OWN/'EXECUTION_SCOPE.json').read_bytes())==r['scope_sha256']
 assert elt.sha((elt.REPO/r['input_receipt_reference']).read_bytes())==r['input_receipt_sha256']
 registry=json.loads((elt.REPO/elt.SCOPE['current_run_registry_reference']).read_text())
 assert registry['owners']['newspaper']==r['owner_thread_id'] and registry['deadline_at_utc']==r['hard_deadline_at_utc']==elt.SCOPE['hard_deadline_at_utc']
 assert registry['start_at_utc']==elt.SCOPE['earliest_network_and_load_start_at_utc'] and registry['duration_hours']==(elt.DEADLINE-elt.NOT_BEFORE).total_seconds()/3600
 canonical=json.loads((elt.REPO/elt.SCOPE['lease_coordination_reference']).read_text())
 leases=[x for x in canonical['active_leases'] if x.get('active',True) and x['lease_id']==elt.SCOPE['lease_id']]
 assert len(leases)==1 and leases[0]['thread_id']==r['owner_thread_id'] and leases[0]['hard_deadline_at_utc']==r['hard_deadline_at_utc']
 assert leases[0]['media_lifetime_cap_bytes']==elt.SCOPE['media_lifetime_cap_bytes']==60000000000
 assert r['network_and_load_require_live_actual_complete_operation_preflight'] and elt.NOT_BEFORE<=dt.datetime.now(dt.timezone.utc)<elt.DEADLINE
 if not elt.SCOPE.get('new_source_admission_allowed',True):
  frozen=json.loads((elt.REPO/elt.SCOPE['route_allowlist_reference']).read_text());assert frozen['scope_sha256']==elt.sha(s) and frozen['old_PID_absence_verified'] and frozen['lifetime_mutex_available'];assert frozen['source_ids']
  try:os.kill(frozen['old_writer_pid'],0)
  except ProcessLookupError:pass
  else:raise RuntimeError('previous_same_owner_writer_still_live')
 return r

def begin():
 r=binding();terminal=json.loads((elt.PREDECESSOR/'TERMINAL_WRITER_EXIT.json').read_text())
 assert terminal['PID_absence_verified'] and terminal['lifetime_mutex_available'] and terminal['host_reported_session_finished']
 try:os.kill(terminal['collector_pid'],0)
 except ProcessLookupError:pass
 else:raise RuntimeError('predecessor_PID_still_exists')
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);capacity=elt.preflight(elt.operation_footprint())
  sources={p:p.read_bytes() for p in elt.OWN.glob('*.py')};elt.preflight(sum(map(len,sources.values()))*3+1048576);dest=elt.OWN/'runtime_implementation_versions';dest.mkdir(exist_ok=True)
  for p,b in sources.items():
   out=dest/(elt.sha(b)+'.py')
   if out.exists():assert out.read_bytes()==b
   else:out.write_bytes(b)
 start=dict(at_utc=elt.utc(),owner_thread_id=os.environ['CODEX_THREAD_ID'],pid=os.getpid(),all_start_predicates_passed=True,previous_writer_exit_observed=True,lifetime_mutex_acquired=True,scope_sha256=r['scope_sha256'],input_receipt_sha256=r['input_receipt_sha256'],implementation_hashes={p.name:elt.sha(p.read_bytes()) for p in elt.OWN.glob('*.py')},implementation_content_addressed_snapshot_directory='runtime_implementation_versions',frozen_predecessor_file_hashes={str((elt.PREDECESSOR/n).relative_to(elt.REPO)):h for n,h in json.loads((elt.OWN/'INPUT_SNAPSHOT.json').read_text())['input_state_sha256'].items()},actual_capacity=capacity,hard_deadline_at_utc=r['hard_deadline_at_utc'],inherited_counters_preserved=True,source_country_extension_reference='SOURCE_COUNTRY_EXTENSION_AMENDMENT.json',source_country_extension_sha256=elt.sha((elt.OWN/'SOURCE_COUNTRY_EXTENSION_AMENDMENT.json').read_bytes()))
 if (elt.OWN/'START_RECEIPT.json').exists():
  old=json.loads((elt.OWN/'START_RECEIPT.json').read_text());elt.preparation_save('runtime_bindings/START_RECEIPT_'+str(old['pid'])+'.json',old)
 if not elt.SCOPE.get('new_source_admission_allowed',True):start.update(current_route_allowlist_reference=elt.SCOPE['route_allowlist_reference'],current_route_allowlist_sha256=elt.sha((elt.REPO/elt.SCOPE['route_allowlist_reference']).read_bytes()),same_owner_current_route_only_amendment=True)
 elt.preparation_save('START_RECEIPT.json',start);elt.preparation_save('WORKER_PROCESS.json',dict(pid=os.getpid(),owner_thread_id=elt.SCOPE['owner_thread_id'],status='running',at_utc=elt.utc()));print(json.dumps({'start_passed':True,'pid':os.getpid(),'deadline':r['hard_deadline_at_utc'],'capacity':capacity}),flush=True)
 run.run()

if __name__=='__main__':
 with (elt.REPO/elt.SCOPE['newspaper_writer_mutex']).open('a+b') as mutex:
  elt.fcntl.flock(mutex,elt.fcntl.LOCK_EX|elt.fcntl.LOCK_NB);begin()
