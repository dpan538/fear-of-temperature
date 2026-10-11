"""Settle only named newly saved capacity-blocked returns; no fresh HTTP."""
import json,urllib.parse
import transport as t,entities as e,small_collect as s,thesession_adapter

def main():
    assert t.read_json(t.WORK/'RUN_STOP.json');scope=t.release();cs=t.read_json(s.CUR);frames=s.old_frames();before=t.state()['new_core_bodies'];events=[]
    with t.writer():
        for cursor in cs:
            if cursor['state']!='complete_operation_capacity_blocked':continue
            f=frames[cursor['frame']];url,route,unit=s.job(cursor,f)
            if not url:continue
            rid=t.sha((cursor['source']+'|content|'+url).encode())[:24];rec=t.read_json(t.WORK/'receipts'/f'{rid}.json',{})
            if rec.get('status')!='saved':continue
            if route=='session_topic':rows,data=thesession_adapter.records(t.payload(rec),url)
            elif route=='session_index':rows,data=thesession_adapter.index(t.json_payload(rec))
            else:
                data=t.json_payload(rec);rows=[] if route=='created_index' else e.discourse(data,cursor['source'],f['base'],f['license'])
            ledger=t.read_json(t.WORK/'SMALL_NATIVE_LOAD_STATE.json',{}).get(rid,{})
            offset=ledger.get('committed_prefix_records',0)
            if ledger:
                assert ledger['total_records']==len(rows)
                assert ledger['native_key_digest']==t.sha(json.dumps(sorted(e.key(r) for r in rows)).encode())
            partial_sum=0
            if (t.WORK/'LOADS.jsonl').exists():
                partial_sum=sum(r['new_qualified_posts'] for r in map(json.loads,(t.WORK/'LOADS.jsonl').read_text().splitlines()) if r['request_id']==rid and r['frame_id']==cursor['frame'])
            phase_before=t.state()['new_core_bodies']
            original_digest=t.sha(json.dumps(sorted(e.key(r) for r in rows)).encode())
            suffix_digest=t.sha(json.dumps(sorted(e.key(r) for r in rows[offset:])).encode())
            t.append(t.WORK/'NAMED_SAVED_PREFIX_INPUTS.jsonl',{'at_utc':t.utc(),'request_id':rid,'original_native_key_digest':original_digest,'original_total_records':len(rows),'suffix_offset':offset,'previous_ledger':ledger})
            completed=False
            try:
                # The suffix starts at a whole native-record boundary. Never
                # lower native32MiB, journal64MiB, per-row, metadata or output bounds.
                result=e.load(rows[offset:],rec,cursor['frame']);s.advance(cursor,f,data,route,unit,rows)
                cursor['new_core_bodies']+=partial_sum+result['new_qualified_posts']
                dates=[r['native_created_at'] for r in rows if r.get('native_created_at')]
                if dates:cursor['oldest_returned_publication_at']=min(dates+[cursor.get('oldest_returned_publication_at') or min(dates)])
                state='all_saved_whole_native_units_committed_cursor_advanced'
                completed=True
            except t.Stop as exc:state='remaining_complete_operation_capacity_or_scope_bound';cursor['stop']=str(exc)
            ledgers=t.read_json(t.WORK/'SMALL_NATIVE_LOAD_STATE.json',{});latest=ledgers.get(rid,{})
            additional_prefix=latest.get('committed_prefix_records',0) if latest.get('native_key_digest')==suffix_digest and latest.get('total_records')==len(rows)-offset else 0
            prefix=len(rows) if completed else min(len(rows),offset+additional_prefix)
            ledgers[rid]=latest|{'at_utc':t.utc(),'request_id':rid,'frame_id':cursor['frame'],'native_key_digest':original_digest,'total_records':len(rows),'committed_prefix_records':prefix,'complete':completed,'whole_native_bodies_preserved':True,'source_response_prefix_basis_restored_after_suffix_recovery':True,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes())};t.atomic(t.WORK/'SMALL_NATIVE_LOAD_STATE.json',ledgers)
            events.append({'at_utc':t.utc(),'request_id':rid,'frame':cursor['frame'],'source_url':url,'raw_sha256':rec['raw_sha256'],'whole_native_records':len(rows),'previously_committed_prefix':offset,'additional_core_bodies_loaded':t.state()['new_core_bodies']-phase_before,'state':state,'fresh_HTTP_requests':0})
            t.atomic(s.CUR,cs)
    result={'at_utc':t.utc(),'events':events,'additional_core_bodies_loaded':t.state()['new_core_bodies']-before,'fresh_HTTP_requests':0,'new_saved_responses_only':True,'source_stops_preserved':True,'fixed_margins_or_lifetime_counters_reduced':False,'hard_deadline_at_utc':scope['hard_deadline_at_utc']}
    s.progress(cs,t.read_json(t.WORK/'RUN_STOP.json')['reason'])
    t.atomic(t.WORK/'NAMED_SAVED_RESPONSE_RECOVERY.json',result);print(json.dumps(result))

if __name__=='__main__':main()
