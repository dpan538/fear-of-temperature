import os,json,datetime as dt
import elt,run

def begin():
 control=elt.OWN.parent/'control';release=json.loads((control/'OWNER_RELEASE.json').read_text());scope=(control/'EXECUTION_SCOPE.json').read_bytes()
 assert release['status']=='CONDITIONALLY_RELEASED' and release['network_and_durable_load_released']
 assert release['version']==elt.SCOPE['version']=='newspaper-post-eight-hour-directed-repair-20261011-v1'
 assert release['owner_thread_id']==elt.SCOPE['owner_thread_id']==os.environ['CODEX_THREAD_ID']
 assert elt.sha(scope)==elt.sha((elt.OWN/'EXECUTION_SCOPE.json').read_bytes())==release['scope_sha256']
 assert elt.sha((elt.REPO/elt.SCOPE['input_receipt_reference']).read_bytes())==release['input_receipt_sha256']
 assert json.loads((elt.OWN/'SUCCESSOR_INPUT_BINDING.json').read_text())['predecessor_terminal_verified']
 assert elt.NOT_BEFORE<=dt.datetime.now(dt.timezone.utc)<elt.DEADLINE
 assert json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text())['all_passed']
 close=json.loads((elt.PREDECESSOR/'TERMINAL_WRITER_EXIT.json').read_text());assert close['host_reported_session_finished'] and close['PID_absence_verified'] and close['lifetime_mutex_available']
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);capacity=elt.preflight(elt.operation_footprint())
 start=dict(at_utc=elt.utc(),owner_thread_id=os.environ['CODEX_THREAD_ID'],pid=os.getpid(),all_start_predicates_passed=True,previous_writer_exit_observed=True,lifetime_mutex_acquired=True,scope_sha256=release['scope_sha256'],input_receipt_sha256=release['input_receipt_sha256'],implementation_hashes={p.name:elt.sha(p.read_bytes()) for p in elt.OWN.glob('*.py')},frozen_predecessor_file_hashes=json.loads((elt.OWN/'INPUT_SNAPSHOT.json').read_text())['input_state_sha256'],actual_capacity=capacity,hard_deadline_at_utc=elt.SCOPE['hard_deadline_at_utc'],inherited_counters_preserved=True)
 # Key the predecessor digest map by exact repository-relative references.
 start['frozen_predecessor_file_hashes']={str((elt.PREDECESSOR/n).relative_to(elt.REPO)):h for n,h in start['frozen_predecessor_file_hashes'].items()}
 if (elt.OWN/'START_RECEIPT.json').exists():
  assert (elt.OWN/'CONTROLLED_RESTART_WRITER_EXIT.json').exists();elt.preparation_save('runtime_bindings/START_RECEIPT_'+str(json.loads((elt.OWN/'START_RECEIPT.json').read_text())['pid'])+'.json',json.loads((elt.OWN/'START_RECEIPT.json').read_text()))
 elt.preparation_save('START_RECEIPT.json',start);print(json.dumps({'start_passed':True,'deadline':elt.SCOPE['hard_deadline_at_utc']}),flush=True);run.run()

if __name__=='__main__':
 with (elt.REPO/elt.SCOPE['newspaper_writer_mutex']).open('a+b') as mutex:
  elt.fcntl.flock(mutex,elt.fcntl.LOCK_EX|elt.fcntl.LOCK_NB);begin()
