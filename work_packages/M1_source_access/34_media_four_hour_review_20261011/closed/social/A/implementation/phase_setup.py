"""One owner-bound delta binding; frozen predecessor metadata stays referenced."""
import json
import transport as t,entities as e

def initialize():
    if (t.WORK/'INHERITED_BASELINE.json').exists():return
    scope=t.release();rel=t.read_json(t.WORK.parent/'control/OWNER_RELEASE.json');receipt=t.REPO/scope['input_receipt_reference']
    assert rel['input_receipt_sha256']==t.sha(receipt.read_bytes())
    pre=t.REPO/scope['predecessor_worker_reference'];prefix=str(pre.relative_to(t.REPO))+'/'
    verified={}
    for name,digest in t.read_json(receipt)['metadata_inputs_sha256'].items():
        if name.startswith(prefix):assert t.sha((t.REPO/name).read_bytes())==digest,name;verified[name]=digest
    closed=t.read_json(pre/'CLOSED.json');assert closed['retained_core_total']==987268 and closed['usable_dated_body_total']==987252
    t.atomic(t.WORK/'STATE.json',{'inherited_state_reference':str((pre/'STATE.json').relative_to(t.REPO)),'requests':closed['lifetime_charged_requests'],'returned_object_count':closed['lifetime_returned_native_keys'],'new_entities':0,'new_core_bodies':0,'new_entity_versions':0,'source_year_deltas':{},'first_successful_http_at_utc':None,'last_successful_http_at_utc':None,'first_successful_load_at_utc':None,'last_successful_load_at_utc':None})
    with t.writer():
        with t.shared(t.footprint()) as budget:
            c=e.db();tables=['posts','versions','native_entities','entity_versions','entity_observations','native_edges','native_attachments','responses']
            bounds={name:c.execute('SELECT MAX(rowid) FROM '+name).fetchone()[0] for name in tables};c.close()
            assert bounds['posts']==closed['retained_core_total'] and bounds['native_entities']==closed['native_entities_total'] and bounds['entity_versions']==closed['entity_versions_total']
            baseline={'at_utc':t.utc(),'counts':bounds,'lifetime_charged_requests':closed['lifetime_charged_requests'],'lifetime_distinct_returned_objects':closed['lifetime_returned_native_keys'],'usable_dated_bodies':closed['usable_dated_body_total'],'pooled_observed_months':closed['pooled_observed_months'],'predecessor_closed_snapshot_sha256':t.sha((pre/'CLOSED.json').read_bytes()),'predecessor_delivery_manifest_sha256':t.sha((pre/'summaries/delivery_file_manifest.json').read_bytes()),'input_social_metadata_verified':verified,'current_returned_key_catalog_difference':closed['lifetime_returned_native_keys']-bounds['native_entities'],'actual_capacity':budget,'prior_exports_charged_in_actual_bytes_only':True,'no_old_body_or_raw_audit':True}
            t.atomic(t.WORK/'INHERITED_BASELINE.json',baseline);t.atomic(t.WORK/'APPEND_ROWID_BOUNDARIES.json',{'at_utc':t.utc(),'bounds':bounds,'basis':'indexed append maxima match accepted final counters; no deletion or migration'})
        fronts=t.read_json(pre/'FRONTIERS.json');cursors=[]
        for f in fronts:
            if f['source'] not in ('straight_dope','thesession','survivefrance','foodtalkcentral','oscedays'):continue
            if f['source']=='straight_dope' or f.get('historical_route'):
                allowed=f['status']=='complete_operation_capacity_blocked'
                cursors.append({'frame':f['frame'],'source':f['source'],'kind':f['kind'],'state':'active' if allowed else 'preserved_source_stop','predecessor_frame_reference':str((pre/'FRONTIERS.json').relative_to(t.REPO)),'predecessor_frame_file_sha256':t.sha((pre/'FRONTIERS.json').read_bytes()),'original_status':f['status'],'original_stop':f.get('stop'),'chunk_offset':0,'post_offset':0,'topic_offset':0,'native_next_url':f.get('native_next_url'),'page':f.get('page'),'new_core_bodies':0,'defer_until':0,'new_pending_chunks':[],'new_topics':[],'seen_new_topics':[],'blocked_complete_native_ids':[]})
        t.atomic(t.WORK/'NATIVE_CURSORS.json',cursors)
        t.atomic(t.WORK/'START_RECEIPT.json',{'at_utc':t.utc(),'owner_thread_id':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'input_receipt_sha256':t.sha(receipt.read_bytes()),'deadline':scope['hard_deadline_at_utc'],'accounting_regression':t.read_json(t.WORK/'ACCOUNTING_REGRESSION.json'),'actual_smallest_preflight':budget,'append_boundaries':bounds,'lifetime_counters_preserved':True,'native_queues_referenced_not_copied':True,'provider_and_source_stops_preserved':True,'source_requests':0,'database_loads':0})

if __name__=='__main__':initialize()
