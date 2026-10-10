"""Reconsider local capacity failures only when current guarded operations fit."""
import json
import transport as t

def fits(pending):
    try:
        with t.shared(pending):return True
    except t.Stop as exc:
        if str(exc).startswith('resource_stop'):return False
        raise

def reconsider(fronts,metadata_changed=False):
    changes=[]
    for f in fronts:
        small=f.get('capacity_small_native_only',False)
        if f['status']!='complete_operation_capacity_blocked' and not (small and metadata_changed):continue
        why=f.get('preserved_default_response_capacity_failure') if small else f.get('stop')
        if not isinstance(why,str) or not why.startswith('resource_stop '):continue
        pending=json.loads(why[len('resource_stop '):])['pending_bytes']
        if metadata_changed and fits(pending):
            f['preserved_capacity_failures']=f.get('preserved_capacity_failures',[])+[why]
            f['status']='active';f.pop('stop',None)
            if small:
                f['capacity_small_native_only']=False
                old=f.get('capacity_original_raw_cap_bytes')
                if old is None:f.pop('raw_cap_bytes',None)
                else:f['raw_cap_bytes']=old
            changes.append({'frame':f['frame'],'state':'original operation reservation now fits after changed metadata settlement','original_pending_bytes':pending})
        elif not small and f['kind'] in ('discourse','discourse_archive') and f.get('chunks') and fits(t.footprint(262144)):
            f['preserved_default_response_capacity_failure']=why
            f['capacity_original_raw_cap_bytes']=f.get('raw_cap_bytes')
            f['capacity_small_native_only']=True;f['raw_cap_bytes']=262144;f['status']='active';f.pop('stop',None)
            changes.append({'frame':f['frame'],'state':'exact existing single native post lookup fits smaller response reservation','native_ids_preserved':True,'larger_operation_failure_preserved':True})
    if changes:t.append(t.WORK/'CAPACITY_QUEUE_RECHECKS.jsonl',{'at_utc':t.utc(),'metadata_changed':metadata_changed,'changes':changes,'source_prohibition_cleared':False,'fixed_interval_preserved':True})
    return bool(changes)
