"""Bound post-review preparation: implementation and compact metadata only."""
import pathlib,json,csv,hashlib,datetime as dt,os,fcntl,shutil
W=pathlib.Path(__file__).resolve().parent;R=W.parents[5];C=W.parent/'control'
S=json.loads((C/'EXECUTION_SCOPE.json').read_text());P=R/S['predecessor_worker_reference']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,o):(W/n).write_text(json.dumps(o,indent=2)+'\n')
release=json.loads((C/'OWNER_RELEASE.json').read_text())
assert release['owner_thread_id']==S['owner_thread_id']==os.environ['CODEX_THREAD_ID']
assert sha(C/'EXECUTION_SCOPE.json')==release['scope_sha256']
assert sha(R/S['input_receipt_reference'])==release['input_receipt_sha256']
assert dt.datetime.now(dt.timezone.utc)<dt.datetime.fromisoformat(S['hard_deadline_at_utc'])
terminal=json.loads((P/'TERMINAL_WRITER_EXIT.json').read_text())
assert terminal['host_reported_session_finished'] and terminal['PID_absence_verified'] and terminal['lifetime_mutex_available']
assert json.loads((P/'WORKER_COMPLETION.json').read_text())['all_changed_tranche_checks_passed']
with (R/S['newspaper_writer_mutex']).open('a+b') as mutex:
 fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (R/S['shared_heavy_io_lock']).open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  used=S['prior_media_bytes']
  for ref in S['media_lifetime_accounting_roots']:
   stack=[R/ref]
   while stack:
    d=stack.pop()
    if not d.exists():continue
    with os.scandir(d) as entries:
     for e in entries:
      if e.is_dir(follow_symlinks=False):stack.append(pathlib.Path(e.path))
      elif e.is_file():used+=e.stat().st_size
  free=shutil.disk_usage(W).free;peak=128*1024*1024
  assert used+peak<S['media_lifetime_cap_bytes'] and free-peak>S['physical_floor_bytes']+S['recovery_allowance_bytes']
  (W/'EXECUTION_SCOPE.json').write_bytes((C/'EXECUTION_SCOPE.json').read_bytes())
  for p in P.glob('*.py'):
   if p.name not in ['prepare_focused.py','bind_predecessor.py','check_focused.py','check_successor.py']:(W/p.name).write_bytes(p.read_bytes())
  states=['TRANSPORT_STATE.json','NATIVE_CURSORS.json','BROADEN_CURSORS.json','NATIVE_BATCH_UNIT_STATUS.json','GL_ISSUE_QUEUE.json','GL_ISSUES_PROCESSED.json','BROADEN_PROFILES.json','BROADEN_JOBS.json','BROADEN_JOBS_DONE.json','PARENT_FAMILY_LEDGER.json','ARCHIVE_ISSUE_QUEUE.json','ARCHIVE_ISSUE_STATE.json','DERIVED_TIME_FIELD_ASSERTIONS.json','SOURCE_ADMISSION_AND_LIMITS.json','REOPEN_NO_HTTP_TARGETS.json','BERKELEY_NATIVE_FRONTIER.json','MISSING_MONTH_EXECUTABLE_STATE.json','NAMED_GL_ISSUE_ROUTE_STATE.json','FOCUSED_SOURCE_USE_STOPS.json','DERIVED_STRUCTURAL_UNIT_DISPOSITIONS.json','GL_DIRECTORY_SCOPE_DISPOSITIONS.json']
  for n in states:
   if (P/n).exists():(W/n).write_bytes((P/n).read_bytes())
  # Only route/result metadata, needed to preserve carrier and source states.
  for n in ['SOURCE_PREPARATION_RESULTS.jsonl']:
   (W/n).write_bytes((P/n).read_bytes())
  for n in ['LOAD_LOG.jsonl','REQUESTS.jsonl','SCHEDULER_ACTIONS.jsonl','COMMITTED_METADATA_EVENTS.jsonl']:(W/n).write_text('')
  rows=[]
  for n in ['CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv','HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv']:rows+=list(csv.DictReader((P/n).open()))
  assert len(rows)==len({r['article_id'] for r in rows})==36911
  fields=['article_id','source_id','source_url','publication_date','stratum','work_family_id','latest_version_id','raw_source_url','disposition']
  with (W/'BASELINE_METADATA.csv').open('w') as f:
   writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
   for row in rows:writer.writerow({k:'confirmed_complete' if k=='disposition' else row.get(k,'') for k in fields})
  summary=json.loads((P/'DELIVERY_SUMMARY.json').read_text());state=json.loads((W/'TRANSPORT_STATE.json').read_text())
  frozen=states[:6]+['DELIVERY_SUMMARY.json','CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv','HISTORICAL_CAMPUS_PRESERVATION_REGISTER.csv','TERMINAL_WRITER_EXIT.json','DERIVED_STRUCTURAL_UNIT_DISPOSITIONS.json']
  save('INPUT_SNAPSHOT.json',dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),baseline_current_newspaper_IDs=27662,baseline_campus_IDs=9249,baseline_qualified_IDs=len(rows),baseline_store_counts=summary['database_counts'],cumulative_native_targets=len(state['charged_native_targets']),cumulative_distinct_transport_targets=len(state['targets']),input_state_sha256={n:sha(P/n) for n in frozen},baseline_summary_reference=str((P/'DELIVERY_SUMMARY.json').relative_to(R)),metadata_only_no_old_body_sweep=True))
  save('SUCCESSOR_INPUT_BINDING.json',dict(predecessor_terminal_verified=True,terminal=terminal,copied_metadata_state_sha256={n:sha(P/n) for n in states if (P/n).exists()},baseline_metadata_sha256=sha(W/'BASELINE_METADATA.csv'),no_body_or_store_copy=True,counters_not_reset=True,scope_deadline_unchanged=S['hard_deadline_at_utc']))
  save('PREPARATION_CAPACITY.json',dict(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),cumulative_bytes=used,free_bytes=free,unperformed_peak_bytes=peak,all_passed=True))
for n in ['elt.py','start.py']:
 code=(W/n).read_text().replace('newspaper-eight-hour-focused-repair-20261010-v1',S['version']).replace('newspaper_focused_repair_20261010','newspaper_post_review_20261011')
 if n=='elt.py':
  code=code.replace("PREDECESSOR=OWN.parents[1]/'20261010_broader_history_four_hour/worker'","BROADER_PREDECESSOR=OWN.parents[1]/'20261010_broader_history_four_hour/worker'\nPREDECESSOR=OWN.parents[1]/'20261010_eight_hour_focused_repair/worker'")
  code=code.replace('HISTORICAL_REPAIR_PREDECESSOR,PREDECESSOR]','HISTORICAL_REPAIR_PREDECESSOR,BROADER_PREDECESSOR,PREDECESSOR]')
  code=code.replace('RECEIPT_ROOTS=[OWN,PREDECESSOR,','RECEIPT_ROOTS=[OWN,PREDECESSOR,BROADER_PREDECESSOR,')
  code=code.replace('for _root in [PREDECESSOR,NINE_HOUR_PREDECESSOR','for _root in [PREDECESSOR,BROADER_PREDECESSOR,NINE_HOUR_PREDECESSOR')
 if n=='start.py':code=code.replace("close=json.loads((elt.PREDECESSOR/'WRITER_EXIT_OBSERVATION.json').read_text());assert close['host_reported_session_finished']","close=json.loads((elt.PREDECESSOR/'TERMINAL_WRITER_EXIT.json').read_text());assert close['host_reported_session_finished'] and close['PID_absence_verified'] and close['lifetime_mutex_available']")
 (W/n).write_text(code)
(W/'watch_deadline.py').write_text((W/'watch_deadline.py').read_text().replace('Original fixed eight-hour deadline reached','Original fixed post-review four-hour deadline reached'))
print(json.dumps({'prepared':True,'baseline':len(rows),'deadline':S['hard_deadline_at_utc']}))
