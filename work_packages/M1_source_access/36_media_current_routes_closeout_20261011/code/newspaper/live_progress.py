"""Compact in-operation observations; no corpus/raw/SQL audit or control score."""
import json,collections,time,datetime as dt,os
import elt
_last=time.monotonic();_rows=__import__('current_tranche_counting').countable_rows(json.loads(x) for x in (elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines() if x)

def genre(row):
 v=row.get('publisher_native_genre')
 return json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v or row.get('source_frame') or 'unknown'
def observe_load(row):
 if row.get('load_status')=='confirmed_complete':_rows[row['article_id']]=row
 heartbeat()
def observe_HTTP(row):heartbeat()
def heartbeat():
 global _last
 if time.monotonic()-_last<60:return
 import run,production,expansion,broaden
 regular=__import__('current_tranche_counting').regular_rows(_rows)
 now=elt.utc();path=elt.OWN/'PROGRESS.json';o=json.loads(path.read_text()) if path.exists() else {}
 st=elt.state();o.update(at_utc=now,pid=os.getpid(),owner_thread_id=elt.SCOPE['owner_thread_id'],phase='collecting',hard_deadline_at_utc=elt.SCOPE['hard_deadline_at_utc'],elapsed_hours=(dt.datetime.now(dt.timezone.utc)-elt.NOT_BEFORE).total_seconds()/3600,completed_bounded_operations=run.rounds,current_operation=run.next_action,cumulative_distinct_transport_targets=len(st['targets']),cumulative_charged_native_targets=len(st['charged_native_targets']),cumulative_stratum_counters=st['strata'],new_HTTP_response_hops=elt._OWN_HTTP_RESPONSE_HOPS,new_HTTP_request_attempts_recorded=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED,new_Load_status_counts=dict(elt._new_totals),first_successful_HTTP_at_utc=elt._first_http,last_successful_HTTP_at_utc=elt._last_http,first_successful_Load_at_utc=elt._first_load,last_successful_Load_at_utc=elt._last_load,new_complete_article_IDs=len(_rows),new_regular_article_IDs=len(regular),new_contributing_title_ids=sorted({r['source_id'] for r in regular.values()}-{r['source_id'] for r in production.BASELINE}),new_country_deltas=dict(collections.Counter(r.get('country') or 'unknown' for r in _rows.values())),new_region_deltas=dict(collections.Counter(r['stratum'] for r in _rows.values())),new_genre_deltas=dict(collections.Counter(genre(r) for r in _rows.values())),source_year_deltas=dict(collections.Counter(r['source_id']+'|'+r['publication_date'][:4] for r in _rows.values())),new_source_expansion={sid:{k:v.get(k) for k in ['stage','title','country','stratum','reason']} for sid,v in expansion.state().items()},source_cursors={sid:{k:v.get(k) for k in ['stage','attempted_pages','next_url','blocked_reason']} for sid,v in broaden._state().items()},stop_reason=None,in_operation_snapshot=True,counts_and_geography_not_control_gates=True)
 elt.preparation_save('PROGRESS.json',o);elt.preparation_save('LIVE_PROGRESS_CLOCK.json',dict(at_utc=now,current_operation=run.next_action,last_HTTP=elt._last_http,last_Load=elt._last_load,new_complete_IDs=len(_rows),source_year_deltas=o['source_year_deltas']))
 print(json.dumps(dict(at_utc=now,phase='collecting_in_operation',new_complete_IDs=len(_rows),new_titles=o['new_contributing_title_ids'],current_operation=run.next_action,last_HTTP=elt._last_http,last_Load=elt._last_load)),flush=True);_last=time.monotonic()
