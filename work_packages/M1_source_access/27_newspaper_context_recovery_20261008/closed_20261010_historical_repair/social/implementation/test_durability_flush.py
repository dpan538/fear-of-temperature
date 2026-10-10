"""Capacity settlement reopens only our resource stops, with no source work."""
import contextlib,json,sqlite3,tempfile
from pathlib import Path
from unittest.mock import patch
import transport as t,entities as e,durability_flush as d
@contextlib.contextmanager
def no_io_lock(*a,**k):yield {}
checks=[]
original=t.WORK
for ready in [True,False]:
 with tempfile.TemporaryDirectory(dir=original) as name:
  w=Path(name);scope=w/'scope.json';t.atomic(scope,{'earliest_network_and_load_start_at_utc':'2026-10-10T01:00:00+00:00','hard_deadline_at_utc':'2026-10-10T05:43:58.368759+00:00'})
  t.atomic(w/'RUN_STOP.json',{'reason':'owner_requested_committed_boundary_maintenance'})
  t.atomic(w/'FRONTIERS.json',[{'frame':'native-history','status':'complete_operation_capacity_blocked','stop':'resource_stop fixture'},{'frame':'provider','status':'preserved_source_stop','stop':'quota_exhausted'}]);t.atomic(w/'ACQUISITION_TAIL_ACCOUNTING.json',{'already_annotated_changed_versions':0})
  st={'new_entity_versions':0,'new_core_bodies':250000,'requests':7500,'returned_object_ids':['persisted-native-key']}
  def database():
   c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE entity_versions(entity_version_id,first_retrieved_at);CREATE TABLE entity_quality_annotations(entity_version_id);');return c
  def capacity(*a):
   if not ready:raise t.Stop('resource_stop actual retained bytes still block operation')
   return {'social_headroom':50000000}
  with patch.object(t,'WORK',w),patch.object(t,'SCOPE_PATH',scope),patch.object(t,'writer',no_io_lock),patch.object(t,'shared',no_io_lock),patch.object(t,'state',return_value=st),patch.object(t,'preflight',capacity),patch.object(e,'db',database),patch.object(d,'reconcile_saved',return_value=[]),patch.object(d,'finalize',return_value={'quality_annotations':0}),patch.object(d.collect,'checkpoint'):
   d.main()
  fronts=t.read_json(w/'FRONTIERS.json');assert fronts[1]['status']=='preserved_source_stop' and fronts[1]['stop']=='quota_exhausted'
  assert fronts[0]['status']==('active' if ready else 'complete_operation_capacity_blocked')
  receipt=t.read_json(w/'DURABILITY_FLUSH_1_RECEIPT.json');assert receipt['resume_possible']==ready and receipt['source_requests']==0 and receipt['lifetime_charged_requests']==7500 and receipt['lifetime_returned_keys']==1
  assert st['new_core_bodies']==250000
  checks.append('reopen_resource_only_after_actual_capacity' if ready else 'retain_genuine_remaining_capacity_failure')
t.atomic(original/'DURABILITY_FLUSH_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'checks':checks,'source_requests':0,'real_corpus_writes':0});print(json.dumps({'passed':True,'checks':len(checks)}))
