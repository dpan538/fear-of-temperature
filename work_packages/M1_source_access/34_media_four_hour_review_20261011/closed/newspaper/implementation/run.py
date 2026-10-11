"""Fixed post-review four-hour newspaper repair and acquisition."""
import os,json,time,datetime as dt,collections,traceback
import elt,broaden,production,native_batches,extract_load
import sys
sys.path.insert(0,str(elt.REPO/'src'))
from fear_temperature.media_planning.core import Opportunity,choose_opportunity
import focused_repair,month_routes,named_issue_routes,berkeley_html,fresh_gl_issues
def resume_counter_baseline(logged, recorded):
 return max(logged, recorded)
_history=[json.loads(x) for x in (elt.OWN/'PROGRESS_HISTORY.jsonl').read_text().splitlines() if x] if (elt.OWN/'PROGRESS_HISTORY.jsonl').exists() else []
_high_water={key:max((row.get(key,0) for row in _history),default=0) for key in ['completed_bounded_operations','new_HTTP_request_attempts_recorded','new_HTTP_response_hops']}
_logged_rounds=sum(1 for x in (elt.OWN/'SCHEDULER_ACTIONS.jsonl').read_text().splitlines() if x) if (elt.OWN/'SCHEDULER_ACTIONS.jsonl').exists() else 0
_logged_attempts=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED;_logged_hops=elt._OWN_HTTP_RESPONSE_HOPS
rounds=resume_counter_baseline(_logged_rounds,_high_water['completed_bounded_operations']);next_action=None
# Preserve last-selection metadata across this same-window handover. This is
# operational waiting age, without coverage, parent or source-count input.
_previous_actions=[json.loads(x) for x in (elt.OWN/'SCHEDULER_ACTIONS.jsonl').read_text().splitlines() if x] if (elt.OWN/'SCHEDULER_ACTIONS.jsonl').exists() else []
_last_selected={r['opportunity']:r['round'] for r in _previous_actions if 'opportunity' in r and 'round' in r}
AGED=collections.Counter({key:max(0,rounds-last-1) for key,last in _last_selected.items()})
elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED=resume_counter_baseline(_logged_attempts,_high_water['new_HTTP_request_attempts_recorded'])
elt._OWN_HTTP_RESPONSE_HOPS=resume_counter_baseline(_logged_hops,_high_water['new_HTTP_response_hops'])

def opportunities():
 st=elt.state();touched=set(st['targets']);fresh_reserved=fresh_gl_issues.reserved_urls();options,payload=focused_repair.options(AGED,fresh_reserved)
 fo,fp=fresh_gl_issues.options(AGED);options+=fo;payload.update(fp)
 mo,mp=month_routes.options(AGED);options+=mo;payload.update(mp)
 io,ip=named_issue_routes.options(AGED);options+=io;payload.update(ip)
 bo,bp=berkeley_html.options(AGED);options+=bo;payload.update(bp)
 for sid in dict.fromkeys(['green_left','indaily']+broaden.active_ids()):
  if sid==berkeley_html.SID:continue # Independent native HTML unit/frontier adapter; never a guessed WP source.
  geo=extract_load.ADAPTERS[sid]['stratum']
  if sid=='workers_advocate':
   import archive_issues
   issues=archive_issues.available()
   if issues:
    issue=issues[0];key=sid+':issue';options.append(Opportunity(key,'historical_native',sid,issue['month'],issue['month'],'ARCHIVE_ISSUE_QUEUE.json; native original article anchors',wait_rounds=AGED[key],need_priority=0 if issue['month']<='1991-01' else 1));payload[key]=issue
   items=[]
  else:items=production.eligible(production.targets(sid),production.KNOWN,touched,{},geo,'historical_native')
  if sid=='green_left':
   named={elt.canon(t['url']) for m,ts in focused_repair._ready.items() if m in focused_repair.MONTHS|focused_repair.ZEROS for t in ts}
   excluded_green_left=named|fresh_reserved
   items=[t for t in items if elt.canon(t['url']) not in excluded_green_left]
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
 # The capacity walk reads both stores; serialize it with their atomic saves.
 with elt.LOCK.open('a+b') as capacity_lock:
  elt.fcntl.flock(capacity_lock,elt.fcntl.LOCK_EX);capacity=elt.resource(elt.operation_footprint())
 o=dict(at_utc=now,pid=os.getpid(),owner_thread_id=elt.SCOPE['owner_thread_id'],phase=phase,hard_deadline_at_utc=elt.SCOPE['hard_deadline_at_utc'],elapsed_hours=elapsed,completed_bounded_operations=rounds,cumulative_distinct_transport_targets=len(st['targets']),cumulative_charged_native_targets=len(st['charged_native_targets']),cumulative_stratum_counters=st['strata'],new_HTTP_response_hops=elt._OWN_HTTP_RESPONSE_HOPS,new_HTTP_request_attempts_recorded=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED,new_Load_status_counts=dict(elt._new_totals),first_successful_HTTP_at_utc=elt._first_http,last_successful_HTTP_at_utc=elt._last_http,first_successful_Load_at_utc=elt._first_load,last_successful_Load_at_utc=elt._last_load,next_concrete_action=next_action,source_year_deltas=dict(collections.Counter(r['source_id']+'|'+r['publication_date'][:4] for r in map(json.loads,(elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()) if r.get('load_status')=='confirmed_complete')),oldest_returned_publication_by_route={sid:min(r['publication_date'] for r in map(json.loads,(elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()) if r.get('source_id')==sid and r.get('load_status')=='confirmed_complete') for sid in set(r['source_id'] for r in map(json.loads,(elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines()) if r.get('load_status')=='confirmed_complete')},source_cursors={k:{x:v.get(x) for x in ['stage','attempted_pages','next_url','blocked_reason']} for k,v in broaden._state().items()},actual_capacity=capacity,stop_reason=reason,parent_and_coverage_metrics_control_input=False)
 o['focused_priorities']=focused_repair.snapshot();o['fresh_issue_bridge']=fresh_gl_issues.snapshot()
 elt.preparation_save('PROGRESS.json',o);elt.append('PROGRESS_HISTORY.jsonl',o)
 for h in [1,2,3]:
  if elapsed>=h and not (elt.OWN/f'H{h}_CHECKPOINT.json').exists():elt.preparation_save(f'H{h}_CHECKPOINT.json',o)
 (elt.OWN/'CONTINUATION_DIGEST.md').write_text(f"# Directed four-hour newspaper repair continuity\nOwner {elt.SCOPE['owner_thread_id']}; deadline {elt.SCOPE['hard_deadline_at_utc']}.\nPhase {phase}; operations {rounds}; stop {reason}.\nNew Loads {dict(elt._new_totals)}; last HTTP {elt._last_http}; last Load {elt._last_load}.\nCounters preserved: {len(st['targets'])} transport targets / {len(st['charged_native_targets'])} native targets.\nNext {next_action}. Entry start.py; state under this worker; own progress and BUG_REPAIR_LEDGER.md.\nOriginal raw/IDs/versions and prior stops retained. No coverage, density, count or parent completion gate.\nFresh issue proof HOUR2_FRESH_ISSUE_REAL_LOAD.json; cursor FRESH_ISSUE_ARTICLE_CURSORS.json. Monitor active writer through fixed closeout; frozen predecessor unchanged; no coordinator/Git/other-stream writes.\n")
 print(json.dumps({k:o[k] for k in ['at_utc','phase','completed_bounded_operations','new_HTTP_request_attempts_recorded','new_Load_status_counts','next_concrete_action','stop_reason']}),flush=True)
 return o

def resume_named_saved_articles():
 manifest=elt.OWN/'DERIVED_SAVED_ARTICLE_RECOVERY.json'
 if not manifest.exists():return 0
 entries=json.loads(manifest.read_text());done_path=elt.OWN/'DERIVED_SAVED_ARTICLE_RECOVERY_DONE.json'
 done=set(json.loads(done_path.read_text())) if done_path.exists() else set()
 for entry in entries:
  request_id=entry['saved_request_id']
  if request_id in done:continue
  receipt=elt._receipt(request_id)
  assert receipt['source_id']==entry['source_id']=='galway_advertiser' and receipt['status']=='saved'
  assert receipt['url']==entry['url']
  result=extract_load.acquire(entry)
  if result and result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
  done.add(request_id);elt.save('DERIVED_SAVED_ARTICLE_RECOVERY_DONE.json',sorted(done))
  elt.append('DERIVED_SAVED_ARTICLE_RECOVERY_RESULTS.jsonl',dict(at_utc=elt.utc(),request_id=request_id,new_HTTP=False,source_id=entry['source_id'],load_status=(result or {}).get('load_status'),reason='Current-window saved native ID evidence compacted away; exact frozen metadata match restored, original pending evidence preserved'))
  return 1
 return 0

def dispatch(chosen,payload):
 sid=chosen.source_id
 if chosen.opportunity_id.startswith('berkeley_carrier:'):
  berkeley_html.activate_saved(payload[chosen.opportunity_id])
 elif chosen.opportunity_id.startswith('berkeley_native:'):
  berkeley_html.perform()
 elif chosen.opportunity_id.startswith('focused_month:'):
  month_routes.perform(chosen.opportunity_id)
 elif chosen.opportunity_id.startswith('focused_issue:'):
  named_issue_routes.perform(payload[chosen.opportunity_id])
 elif chosen.opportunity_id.startswith('fresh_gl_issue:'):
  fresh_gl_issues.acquire(payload[chosen.opportunity_id],rounds)
 elif chosen.opportunity_id.startswith('focused_gl:'):
  focused_repair.acquire_batch(payload[chosen.opportunity_id])
 elif chosen.opportunity_id.endswith(':issue'):
  import archive_issues
  archive_issues.acquire(payload[chosen.opportunity_id])
 elif chosen.opportunity_id.endswith(':body'):
  ts=payload[chosen.opportunity_id]
  if sid=='green_left':focused_repair.acquire_batch(ts);return
  result=native_batches.acquire(sid,ts,production.KNOWN)
  if not result:
   result=extract_load.acquire(ts[0])
   if result and result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
 elif chosen.opportunity_id.endswith(':native_cursor'):production.available_discovery(sid)
 else:broaden.perform_job(payload[chosen.opportunity_id])

def run():
 global rounds,next_action
 elt.assert_release();elt.preflight(elt.operation_footprint());broaden.active_ids();focused_repair.prepare();fresh_gl_issues.prepare();month_routes.prepare();named_issue_routes.prepare();progress('collecting_start');last=time.monotonic();reason=None
 elt.preparation_save('RESUME_COUNTER_BASELINE.json',dict(at_utc=elt.utc(),completed_log_operations=_logged_rounds,recorded_high_water=_high_water,restored_operations=rounds,completed_request_log_attempts=_logged_attempts,restored_recorded_attempts=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED,completed_request_log_response_hops=_logged_hops,restored_recorded_response_hops=elt._OWN_HTTP_RESPONSE_HOPS,basis='Preserve original own PROGRESS_HISTORY high-water values; interrupted attempts and saved-recovery steps need not have completed-log rows',original_history_and_logs_changed=False,prospective_quantity_gate=False))
 elt.preparation_save('WORKER_PROCESS.json',dict(pid=os.getpid(),status='running',at_utc=elt.utc()))
 try:
  proof=elt.OWN/'REAL_LIVE_BRIDGE_PROOF.json'
  if not proof.exists():
   named,payload=focused_repair.options(AGED)
   chosen=next((o for o in named if o.opportunity_id=='focused_gl:1994'),named[0] if named else None)
   if chosen:
    batch=payload[chosen.opportunity_id][:8];before={elt.canon(t['url']) for t in batch if elt.canon(t['url']) in production.KNOWN}
    next_action=dict(opportunity=chosen.opportunity_id,source_id='green_left',kind='named_real_bridge_demonstration')
    elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=rounds,**next_action,need_priority=chosen.need_priority))
    results=focused_repair.acquire_batch(batch);rounds+=1
    elt.preparation_save(proof.name,dict(at_utc=elt.utc(),named_month=chosen.publication_start if hasattr(chosen,'publication_start') else batch[0]['month'],operation_article_bound=8,target_URLs=[t['url'] for t in batch],preexisting_committed_URLs=sorted(before),results=[{k:r.get(k) for k in ['article_id','source_url','publication_date','load_status','request_id']} for r in results if r],remaining_ready_candidates=len(production.eligible(focused_repair._ready.get(batch[0]['month'],[]),production.KNOWN,set(elt.state()['targets']),{},'AU','historical_native')),count_is_not_completion=True))
    progress();last=time.monotonic()
  # These five newly admitted profiles already have named saved root/schema
  # proof. Run those exact records through the existing source adapter before
  # ordinary body scheduling; no cursor is set from an assumed interface.
  for profile in broaden.profiles():
   if profile.get('approval_reference')!='NEW_TITLE_ADMISSION_EVIDENCE.json' or not broaden.approved(profile):continue
   sid=profile['source_id']
   for step in range(3):
    before=broaden._state().get(sid,{}).get('stage','robots')
    if before not in ['robots','native_root','API_schema']:break
    elt.assert_release();before_attempts=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED
    next_action=dict(opportunity='admitted_interface:'+sid+':'+before,source_id=sid,kind='route_resolution')
    elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=rounds,**next_action,need_priority=0,evidence='NEW_TITLE_ADMISSION_EVIDENCE.json; exact saved publisher root/schema; standard robots and native adapter'))
    broaden.discover(sid,production.queue);rounds+=1
    after=broaden._state().get(sid,{}).get('stage')
    elt.append('SOURCE_INTERFACE_PROJECTION_RESULTS.jsonl',dict(at_utc=elt.utc(),source_id=sid,before_stage=before,after_stage=after,new_HTTP_attempts=elt._OWN_HTTP_REQUEST_ATTEMPTS_RECORDED-before_attempts,source_of_truth='Normal source adapter using exact saved receipts and original robots',cursor_reset=False,body_or_SQL_Load=False,deadline_unchanged=True))
    if after==before:break
   if time.monotonic()-last>=120:progress();last=time.monotonic()
  import named_source_time_recovery
  rounds+=named_source_time_recovery.perform()
  import named_visible_template_recovery
  rounds+=named_visible_template_recovery.perform()
  rounds+=fresh_gl_issues.prime(rounds)
  while dt.datetime.now(dt.timezone.utc)<elt.DEADLINE:
   boundary=elt.OWN/'CONTROLLED_BOUNDARY_EXIT_REQUEST.json'
   request=json.loads(boundary.read_text()) if boundary.exists() else {}
   if request.get('bound_pid')==os.getpid() and request.get('same_deadline')==elt.SCOPE['hard_deadline_at_utc']:reason='owner_requested_code_handover_at_operation_boundary';break
   pending_job_path=elt.OWN/'BROADEN_JOBS.json';done_jobs=set(json.loads((elt.OWN/'BROADEN_JOBS_DONE.json').read_text()))
   named=next((j for j in json.loads(pending_job_path.read_text()) if j.get('focused_admission_mapping_check') and j['job_id'] not in done_jobs),None)
   if named:
    next_action=dict(opportunity='named_admission:'+named['job_id'],source_id=named['source_id'],kind='route_resolution');broaden.perform_job(named);rounds+=1
    if time.monotonic()-last>=120:progress();last=time.monotonic()
    continue
   if berkeley_html.profile() and berkeley_html.state()['stage']=='saved_carrier':
    next_action=dict(opportunity='berkeley_native:saved_Load',source_id=berkeley_html.SID,kind='acquisition');berkeley_html.perform();rounds+=1
    if time.monotonic()-last>=120:progress();last=time.monotonic()
    continue
   if resume_named_saved_articles():rounds+=1;continue
   if native_batches.resume_saved(production.KNOWN,production.targets):rounds+=1;continue
   options,payload=opportunities();chosen=choose_opportunity(options)
   if not chosen:
    next_action={'kind':'awaiting_evidenced_route_replenishment'}
    if (elt.OWN/'ALL_ROUTES_EVIDENCED_BLOCKED.json').exists():reason='all_permitted_evidenced_frontiers_unavailable';break
    if time.monotonic()-last>120:progress('route_replenishment_required');last=time.monotonic()
    time.sleep(min(20,max(.01,(elt.DEADLINE-dt.datetime.now(dt.timezone.utc)).total_seconds())));continue
   for option in options:AGED[option.opportunity_id]+=1
   AGED[chosen.opportunity_id]=0;sid=chosen.source_id;next_action=dict(opportunity=chosen.opportunity_id,source_id=sid,kind=chosen.action_kind)
   elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=rounds,**next_action,need_priority=chosen.need_priority))
   dispatch(chosen,payload)
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
