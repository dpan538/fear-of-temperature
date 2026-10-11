"""Enforce this owner's one fixed deadline; never signal a different writer."""
import pathlib,json,sys,datetime as dt,time,os,signal
W=pathlib.Path(__file__).resolve().parent;pid=int(sys.argv[1]);scope=json.loads((W/'EXECUTION_SCOPE.json').read_text());deadline=dt.datetime.fromisoformat(scope['hard_deadline_at_utc'])
start=json.loads((W/'START_RECEIPT.json').read_text());assert start['pid']==pid and start['owner_thread_id']==scope['owner_thread_id']
os.kill(pid,0)
print(json.dumps(dict(armed=True,collector_pid=pid,signal_permission_checked=True,fixed_deadline=scope['hard_deadline_at_utc'])),flush=True)
while True:
 current=json.loads((W/'START_RECEIPT.json').read_text())
 if current['pid']!=pid:result=dict(action='no_signal',reason='Bound writer replaced; successor needs its own exact-deadline watcher');break
 now=dt.datetime.now(dt.timezone.utc)
 try:os.kill(pid,0)
 except ProcessLookupError:result=dict(action='no_signal',reason='Bound writer already exited');break
 if now>=deadline:
  os.kill(pid,signal.SIGINT);result=dict(action='SIGINT',reason='Original fixed post-review four-hour deadline reached; no extension');break
 time.sleep(min(1,max(.01,(deadline-now).total_seconds())))
result.update(at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),collector_pid=pid,fixed_deadline=scope['hard_deadline_at_utc'],no_scope_extension=True)
(W/'DEADLINE_WATCHDOG_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
