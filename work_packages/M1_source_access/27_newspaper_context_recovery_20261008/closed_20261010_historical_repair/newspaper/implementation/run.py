"""Fixed four-hour newspaper historical repair and acquisition."""
import os,json,time,datetime as dt,collections,traceback
import elt,broaden,production,native_batches,extract_load
import sys
sys.path.insert(0,str(elt.REPO/'src'))
from fear_temperature.media_planning.core import Opportunity,choose_opportunity
AGED=collections.Counter();rounds=sum(1 for x in (elt.OWN/'SCHEDULER_ACTIONS.jsonl').read_text().splitlines() if x) if (elt.OWN/'SCHEDULER_ACTIONS.jsonl').exists() else 0;next_action=None

def opportunities():
 st=elt.state();touched=set(st['targets']);options=[];payload={}
 for sid in dict.fromkeys(['green_left','indaily']+broaden.active_ids()):
  geo=extract_load.ADAPTERS[sid]['stratum']
  if sid=='workers_advocate':
   import archive_issues
   issues=archive_issues.available()
   if issues:
    issue=issues[0];key=sid+':issue';options.append(Opportunity(key,'historical_native',sid,issue['month'],issue['month'],'ARCHIVE_ISSUE_QUEUE.json; native original article anchors',wait_rounds=AGED[key],need_priority=0 if issue['month']<='1991-01' else 1));payload[key]=issue
   items=[]
  else:items=production.eligible(production.targets(sid),production.KNOWN,touched,{},geo,'historical_native')
  if items:
   first=items[0].get('month') or 'unknown';key=sid+':body';priority=0 if first<='1991-01' else (1 if sid=='green_left' and first<'2005-01' else 2)
   options.append(Opportunity(key,'historical_native',sid,first,first,'retained native inventory; no coverage input',wait_rounds=AGED[key],need_priority=priority));payload[key]=items
  if sid=='green_left':
   o=json.loads((elt.OWN/'NATIVE_CURSORS.json').read_text());todo=production.issue_eligible(json.loads((elt.OWN/'GL_ISSUE_QUEUE.json').read_text()),set(json.loads((elt.OWN/'GL_ISSUES_PROCESSED.json').read_text())));more=o['cursors']['gl']<len(o['routes']['gl']) or bool(todo)
  elif sid=='indaily':
   o=json.loads((elt.OWN/'NATIVE_CURSORS.json').read_text());k='indaily_retained_sitemaps';more=o['cursors'].get(k,0)<len(o['routes'].get(k,[]))
  else:more=broaden._state().get(sid,{}).get('stage','robots') not in ['blocked','exhausted','observed_public_frontier_consumed']
  if more and sid not in production._discovery_stops:
   key=sid+':native_cursor';options.append(Opportunity(key,'frontier',sid,'1988-01','2026-09','restored native chronological cursor',wait_rounds=AGED[key],need_priority=0 if sid=='workers_advocate' else 2));payload[key]=None
 jobs=json.loads((elt.OWN/'BROADEN_JOBS.json').read_text());done=set(json.loads((elt.OWN/'BROADEN_JOBS_DONE.json').read_text()))
 for j in jobs:
  if j['job_id'] not in done:
   key='prepare:'+j['job_id'];options.append(Opportunity(key,'source_preparation',j['source_id'],'1988-01','2026-09','concrete historical route preparation',wait_rounds=AGED[key],need_priority=0,action_kind='route_resolution'));payload[key]=j
 return options,payload

def progress(phase='collecting',reason=None):
 now=elt.utc();st=elt.state();elapsed=(dt.datetime.now(dt.timezone.utc)-elt.NOT_BEFORE).total_seconds()/3600
 o=dict(at_utc=now,pid=os.getpid(),owner_thread_id=elt.SCOPE['owner_thread_id'],phase=phase,hard_deadline_at_utc=elt.SCOPE['hard_deadline_at_utc'],elapsed_hours=elapsed,completed_bounded_operations=rounds,cumulative_distinct_transport_targets=len(st['targets']),cumulative_charged_native_targets=len(st['charged_native_targets']),cumulative_stratum_counters=st['strata'],new_HTTP_response_hops=elt._OWN_HTTP_RESPONSE_HOPS,new_HTTP_request_attempts_recorded=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED,new_Load_status_counts=dict(elt._new_totals),first_successful_HTTP_at_utc=elt._first_http,last_successful_HTTP_at_utc=elt._last_http,first_successful_Load_at_utc=elt._first_load,last_successful_Load_at_utc=elt._last_load,next_concrete_action=next_action,source_year_deltas=dict(collections.Counter(r['source_id']+'|'+r['publication_date'][:4] for r in map(json.loads,(elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()) if r.get('load_status')=='confirmed_complete')),oldest_returned_publication_by_route={sid:min(r['publication_date'] for r in map(json.loads,(elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()) if r.get('source_id')==sid and r.get('load_status')=='confirmed_complete') for sid in set(r['source_id'] for r in map(json.loads,(elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()) if r.get('load_status')=='confirmed_complete')},source_cursors={k:{x:v.get(x) for x in ['stage','attempted_pages','next_url','blocked_reason']} for k,v in broaden._state().items()},actual_capacity=elt.resource(elt.operation_footprint()),stop_reason=reason,parent_and_coverage_metrics_control_input=False)
 elt.preparation_save('PROGRESS.json',o);elt.append('PROGRESS_HISTORY.jsonl',o)
 for h in [1,2,3]:
  if elapsed>=h and not (elt.OWN/f'H{h}_CHECKPOINT.json').exists():elt.preparation_save(f'H{h}_CHECKPOINT.json',o)
 (elt.OWN/'CONTINUATION_DIGEST.md').write_text(f"# Newspaper historical repair continuity\nOwner {elt.SCOPE['owner_thread_id']}; deadline {elt.SCOPE['hard_deadline_at_utc']}.\nPhase {phase}; operations {rounds}; stop {reason}.\nNew Loads {dict(elt._new_totals)}; last HTTP {elt._last_http}; last Load {elt._last_load}.\nCounters preserved: {len(st['targets'])} transport targets / {len(st['charged_native_targets'])} native targets.\nNext {next_action}. Entry start.py; state under this worker; own progress and BUG_REPAIR_LEDGER.md.\nOriginal raw/IDs/versions and prior stops retained. No coverage, density, count or parent completion gate.\nMonitor active writer through fixed closeout; frozen predecessor unchanged; no coordinator/Git/other-stream writes.\n")
 print(json.dumps({k:o[k] for k in ['at_utc','phase','completed_bounded_operations','new_HTTP_request_attempts_recorded','new_Load_status_counts','next_concrete_action','stop_reason']}),flush=True)
 return o

def run():
 global rounds,next_action
 elt.assert_release();elt.preflight(elt.operation_footprint());broaden.active_ids();progress('collecting_start');last=time.monotonic();reason=None
 elt.preparation_save('WORKER_PROCESS.json',dict(pid=os.getpid(),status='running',at_utc=elt.utc()))
 try:
  while dt.datetime.now(dt.timezone.utc)<elt.DEADLINE:
   if native_batches.resume_saved(production.KNOWN,production.targets):rounds+=1;continue
   options,payload=opportunities();chosen=choose_opportunity([o for o in options if o.need_priority==min((x.need_priority for x in options),default=0)])
   if not chosen:
    next_action={'kind':'awaiting_evidenced_route_replenishment'}
    if (elt.OWN/'ALL_ROUTES_EVIDENCED_BLOCKED.json').exists():reason='all_permitted_evidenced_frontiers_unavailable';break
    if time.monotonic()-last>120:progress('route_replenishment_required');last=time.monotonic()
    time.sleep(min(20,max(.01,(elt.DEADLINE-dt.datetime.now(dt.timezone.utc)).total_seconds())));continue
   for option in options:AGED[option.opportunity_id]+=1
   AGED[chosen.opportunity_id]=0;sid=chosen.source_id;next_action=dict(opportunity=chosen.opportunity_id,source_id=sid,kind=chosen.action_kind)
   elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=rounds,**next_action,need_priority=chosen.need_priority))
   if chosen.opportunity_id.endswith(':issue'):
    import archive_issues
    archive_issues.acquire(payload[chosen.opportunity_id])
   elif chosen.opportunity_id.endswith(':body'):
    ts=payload[chosen.opportunity_id];result=native_batches.acquire(sid,ts,production.KNOWN)
    if not result:
     result=extract_load.acquire(ts[0])
     if result and result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
   elif chosen.opportunity_id.endswith(':native_cursor'):production.available_discovery(sid)
   else:broaden.perform(payload[chosen.opportunity_id]['stratum'],production.queue)
   rounds+=1
   if rounds==1 or time.monotonic()-last>=120:progress();last=time.monotonic()
  reason=reason or 'fixed_deadline'
 except KeyboardInterrupt:
  reason="controlled_owner_interrupt_same_deadline";raise
 except RuntimeError as e:reason=str(e)
 except Exception as e:
  reason='runtime_integrity_failure '+repr(e);elt.preparation_save('EXECUTION_ERROR.json',dict(at_utc=elt.utc(),reason=reason,traceback=traceback.format_exc()));raise
 finally:
  progress('writer_exiting',reason);elt.preparation_save('EXECUTION_STOP.json',dict(at_utc=elt.utc(),reason=reason,further_network=False));elt.preparation_save('WORKER_PROCESS.json',dict(pid=os.getpid(),status='exiting',at_utc=elt.utc()))
