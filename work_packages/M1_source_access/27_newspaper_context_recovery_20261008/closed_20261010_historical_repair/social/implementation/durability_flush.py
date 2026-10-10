"""Settle already acquired metadata to replace capacity estimates with durable bytes.
No new source request, changed deadline/allocation or counter reset.
"""
import json,os
import transport as t,entities as e,collect
from closeout import reconcile_saved
from finalize_metadata import finalize

def main():
 t.TERMINAL_OPERATION=True
 scope=t.read_json(t.SCOPE_PATH);begin=scope['earliest_network_and_load_start_at_utc']
 stop=t.read_json(t.WORK/'RUN_STOP.json');assert stop
 fronts=t.read_json(t.WORK/'FRONTIERS.json')
 blocked=[f for f in fronts if f['status']=='complete_operation_capacity_blocked'];assert blocked
 completed=[int(p.stem.removeprefix('DURABILITY_FLUSH_').removesuffix('_RECEIPT')) for p in t.WORK.glob('DURABILITY_FLUSH_*_RECEIPT.json') if p.stem.removeprefix('DURABILITY_FLUSH_').removesuffix('_RECEIPT').isdigit()]
 started=[int(p.name.split('_')[3]) for p in t.WORK.glob('METADATA_CAPACITY_FLUSH_*_INPUT_RECEIPT.json')]
 revision=max(completed+started+[0])+1
 phase='capacity_flush_'+str(revision)
 with t.writer():
  t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'pid':os.getpid(),'owner_thread_id':t.OWNER,'at_utc':t.utc(),'phase':'settling_acquired_metadata_to_recheck_actual_capacity','worker':str(t.WORK)})
  model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');t.atomic(t.WORK/('TAIL_MODEL_BEFORE_FLUSH_'+str(revision)+'.json'),model)
  collect.checkpoint(fronts,phase='settling_acquired_metadata_to_recheck_actual_capacity')
  recovery=reconcile_saved(begin)
  result=finalize(phase=phase,batch_records=1000)
  with t.shared(t.footprint(),inflight_at=begin):
   c=e.db();annotated=c.execute('SELECT COUNT(*) FROM entity_versions v JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE v.first_retrieved_at>=?',(begin,)).fetchone()[0];c.close()
  st=t.state();assert annotated==st.get('new_entity_versions',0),(annotated,st.get('new_entity_versions',0))
  model['already_annotated_changed_versions']=annotated;model['last_actual_metadata_flush_at_utc']=t.utc();model['metadata_flush_revision']=revision
  t.atomic(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json',model)
  t.TERMINAL_OPERATION=False
  try:current=t.preflight(scope,t.footprint());ready=True
  except t.Stop as exc:current={'reason':str(exc)};ready=False
  # Restore only resource-blocked state when a measured operation can fit.
  # Provider/access stops are never changed.
  if ready:
   for f in blocked:
    f.setdefault('capacity_failure_history',[]).append({'at_utc':t.utc(),'reason':f.pop('stop'),'resolution':'outstanding metadata settled; same native cursor available for a fresh complete-operation preflight'})
    f['status']='active'
  t.atomic(t.WORK/'FRONTIERS.json',fronts)
  receipt={'at_utc':t.utc(),'revision':revision,'previous_stop':stop,'source_requests':0,'recovery':recovery,'metadata_result':result,'actual_annotated_new_versions':annotated,'new_core_bodies':st['new_core_bodies'],'lifetime_charged_requests':st['requests'],'lifetime_returned_keys':len(st['returned_object_ids']),'restored_only_resource_blocked_frames':[f['frame'] for f in blocked] if ready else [],'resume_possible':ready,'actual_complete_operation_capacity':current,'same_owner_deadline_allocation_and_native_cursors':True}
  t.atomic(t.WORK/('DURABILITY_FLUSH_'+str(revision)+'_RECEIPT.json'),receipt)
  collect.checkpoint(fronts,phase='metadata_settled_ready_to_resume_same_interval' if ready else 'metadata_settled_actual_capacity_still_blocked')
 print(json.dumps({'revision':revision,'annotated_new_versions':annotated,'resume_possible':ready,'capacity':current}))
if __name__=='__main__':main()
