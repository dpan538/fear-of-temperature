"""Proportionate final metadata/whole-unit checks; no source gate is weakened."""
import json
import transport as t,smaller_bound_resume,settle_saved,small_collect as s

def main():
    assert t.read_json(t.WORK/'RUN_STOP.json');scope=t.release()
    with t.writer():
        try:smaller_bound_resume.flush(force=True)
        except t.Stop as exc:
            if not str(exc).startswith('resource_stop'):raise
            t.atomic(t.WORK/'FINAL_METADATA_CAPACITY_BOUNDARY.json',{'at_utc':t.utc(),'reason':str(exc),'single_whole_metadata_record':True})
    prior=t.read_json(t.WORK/'NAMED_SAVED_RESPONSE_RECOVERY.json')
    t.append(t.WORK/'NAMED_SAVED_RESPONSE_RECOVERY_HISTORY.jsonl',prior)
    settle_saved.main()
    # A single metadata-only route probe is not admission, corpus contribution,
    # verified historical presence, independent-parent evidence, or permission.
    url='https://community.ricksteves.com/robots.txt';before=t.state()['requests'];rec=None;failure=None
    with t.writer():
        try:rec=t.fetch(url,'rick_steves_travel_forum_candidate','policy',cap=8192)
        except t.Stop as exc:failure=str(exc)
    evidence={'at_utc':t.utc(),'candidate_url':url,'purpose':'bounded public access metadata only','whole_response_upper_bytes':8192,'source_admitted':False,'native_authored_bodies_loaded':0,'actual_HTTP_requests':t.state()['requests']-before,'transport_status':rec.get('status') if rec else 'preflight_or_preserved_stop_no_HTTP','request_id':rec.get('request_id') if rec else None,'http_status':rec.get('http_status') if rec else None,'raw_sha256':rec.get('raw_sha256') if rec else None,'failure':failure or (rec.get('error') if rec else None),'collection_retention_permission':'unresolved; robots alone does not grant rights','open_content_license':'unresolved','redistribution':'unresolved','native_identity_date_body_mapping':'not checked; no forum body or historical snapshot fetched','independent_parent':'unresolved; candidate not counted','historical_access_or_era':'unresolved; current policy metadata alone is not historical coverage','native_32MiB_and_terminal_64MiB_margins_retained':True,'source_and_provider_stops_preserved':True,'hard_deadline_at_utc':scope['hard_deadline_at_utc']}
    t.atomic(t.WORK/'PROPORTIONATE_ROUTE_EVIDENCE.json',evidence)
    s.progress(t.read_json(s.CUR),t.read_json(t.WORK/'RUN_STOP.json')['reason'])
    print(json.dumps({k:evidence[k] for k in ('at_utc','actual_HTTP_requests','transport_status','source_admitted','native_authored_bodies_loaded')}))

if __name__=='__main__':main()
