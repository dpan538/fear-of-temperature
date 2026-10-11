"""Saved suffix first, then same-scope small whole historical native units."""
import json,os
import transport as t,entities as e,small_collect as s,smaller_bound_resume

def restore_named_suffix():
    A=t.SEGMENT_A;rid='a2c75d4d4491de4ea8d94814';old=t.read_json(A/'SMALL_NATIVE_LOAD_STATE.json')[rid];rec=t.read_json(A/'receipts'/f'{rid}.json');cs=t.read_json(s.CUR);frames=s.old_frames()
    cursor=next(c for c in cs if c['frame']==old['frame_id']);f=frames[cursor['frame']];url,route,unit=s.job(cursor,f)
    assert url==rec['url'] and route=='topic';data=t.json_payload(rec);rows=e.discourse(data,cursor['source'],f['base'],f['license'])
    assert len(rows)==old['total_records'] and t.sha(json.dumps(sorted(e.key(r) for r in rows)).encode())==old['native_key_digest']
    offset=old['committed_prefix_records'];suffix=rows[offset:];assert len(suffix)==1 and suffix[0]['native_namespace']=='topic' and suffix[0]['native_post_id']=='736'
    with t.writer():
        result=e.load(suffix,rec,cursor['frame']);s.advance(cursor,f,data,route,unit,rows);cursor['new_core_bodies']+=result['new_qualified_posts'];t.atomic(s.CUR,cs)
        compact=rec|{'reused_saved_whole_response':True,'accepted_phase_A_committed_prefix_records':offset,'only_append_suffix_native_mapping_checked':True,'accepted_phase_A_receipt_reference':str((A/'receipts'/f'{rid}.json').relative_to(t.REPO)),'accepted_phase_A_receipt_sha256':t.sha((A/'receipts'/f'{rid}.json').read_bytes())}
        t.atomic(t.WORK/'receipts'/f'{rid}.json',compact)
        proof={'at_utc':t.utc(),'pid':os.getpid(),'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'hard_deadline_at_utc':t.release()['hard_deadline_at_utc'],'request_id':rid,'raw_sha256':rec['raw_sha256'],'new_Load':result,'actual_native_unit':'topic736 context_container; not independently authored body','fresh_HTTP_requests':0,'cursor_after':{k:cursor[k] for k in ('topic_offset','chunk_offset','post_offset','native_next_url')},'capacity':t.read_json(t.WORK/'LAST_CAPACITY.json'),'phase_A_prefix_reloaded':False,'lifetime_counters_conserved':True}
        t.atomic(t.WORK/'FIRST_APPEND_REAL_LOAD_CURSOR_CAPACITY.json',proof)
    print(json.dumps({'at_utc':t.utc(),'saved_suffix_settled':True,'new_entities':result['new_entities'],'new_entity_versions':result['new_entity_versions'],'new_core_bodies':result['new_qualified_posts'],'pid':os.getpid()}),flush=True)

def main():
    assert t.read_json(t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION.json')['fixed_output_upper_bytes']==8*1048576
    assert t.read_json(t.WORK/'TERMINAL_RESERVE_REGRESSION.json')['passed']
    if not (t.WORK/'FIRST_APPEND_REAL_LOAD_CURSOR_CAPACITY.json').exists():restore_named_suffix()
    original_flush=s.flush_metadata
    def flush(force=False):
        try:return original_flush(force)
        except t.Stop as exc:
            if not str(exc).startswith('resource_stop'):raise
            return smaller_bound_resume.flush(force=True)
    s.flush_metadata=flush
    s.run()
    t.atomic(t.WORK/'APPEND_SOURCE_EXEC_COMPLETE.json',{'at_utc':t.utc(),'pid':os.getpid(),'deadline':t.read_json(t.SCOPE_PATH)['hard_deadline_at_utc'],'scope_unchanged':True,'stop':t.read_json(t.WORK/'RUN_STOP.json')})

if __name__=='__main__':main()
