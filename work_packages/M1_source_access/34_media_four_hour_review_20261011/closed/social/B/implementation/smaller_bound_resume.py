"""One evidenced smaller whole-response continuation inside the same release."""
import json,os
import transport as t,small_collect as s,finalize_metadata

def flush(force=False):
    model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');st=t.state()
    if st['new_entity_versions']<=model['already_annotated_changed_versions']:return False
    start=t.utc();before=model['already_annotated_changed_versions'];counts=None;failure=None
    try:counts=finalize_metadata.finalize(limit=None,phase='smaller_bound',batch_records=1)
    except t.Stop as exc:failure=exc
    selection=t.read_json(t.WORK/'METADATA_SMALLER_BOUND_INPUT_RECEIPT.json',{})
    if selection.get('at_utc','')>=start:
        total_pending=selection['changed_version_count'];progress=t.read_json(t.WORK/'METADATA_SMALLER_BOUND_PROGRESS.json',{})
        committed=(counts or {}).get('quality_annotations',0)
        if not counts and progress.get('at_utc','')>=selection['at_utc']:committed=progress['counts']['quality_annotations']
        model['already_annotated_changed_versions']=st['new_entity_versions']-total_pending+committed
        assert before<=model['already_annotated_changed_versions']<=st['new_entity_versions']
        t.atomic(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json',model)
        t.append(t.WORK/'METADATA_FLUSHES.jsonl',{'at_utc':t.utc(),'phase':'one_whole_metadata_record_per_transaction','counts':counts,'pending_selected':total_pending,'committed_annotations_in_call':committed,'already_annotated_changed_versions':model['already_annotated_changed_versions'],'resource_failure':str(failure) if failure else None})
    if failure:raise failure
    return model['already_annotated_changed_versions']>before

def main():
    scope=t.release();old=t.read_json(t.WORK/'RUN_STOP.json');assert old['reason'].startswith('complete_operation_capacity_failure')
    with t.writer():
        # Atomic history remains local; no counter or old receipt reset.
        t.atomic(t.WORK/'FIRST_CAPACITY_STOP_PRESERVED.json',old)
        try:flush(force=True)
        except t.Stop as exc:
            if not str(exc).startswith('resource_stop'):raise
        cs=t.read_json(s.CUR);eligible=[]
        for c in cs:
            if c['state']!='complete_operation_capacity_blocked':continue
            try:
                with t.shared(t.footprint(64*1024)) as budget:pass
            except t.Stop as exc:
                if not str(exc).startswith('resource_stop'):raise
                continue
            c['previous_256KiB_complete_operation_capacity_stop']=c['stop'];c['state']='active';eligible.append(c['frame'])
        t.atomic(s.CUR,cs)
        proof={'at_utc':t.utc(),'pid':os.getpid(),'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'previous_stop':old,'raw_response_upper_bytes':64*1024,'whole_native_body_required':True,'partial_response_or_body_fragments_counted':False,'native_fixed_margin_bytes':32*1048576,'terminal_journal_margin_bytes':64*1048576,'fixed_output_allowance_reduced':False,'frontiers_reconsidered_after_live_preflight':eligible,'requests_before_resume':t.state()['requests'],'new_core_before_resume':t.state()['new_core_bodies'],'driver_sha256':t.sha((t.WORK/'smaller_bound_resume.py').read_bytes())}
        t.atomic(t.WORK/'SMALLER_COMPLETE_RESPONSE_START.json',proof)
    if eligible:
        s.CAP=64*1024;s.flush_metadata=flush;s.run()
    else:print('no permitted smaller complete response fits; original capacity boundary remains')

if __name__=='__main__':main()
