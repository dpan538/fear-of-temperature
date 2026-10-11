"""Own one source subprocess and close its fixed interval exactly once."""
import json,os,subprocess,sys,time
import transport as t

def main():
    scope=t.release();started=t.utc()
    t.atomic(t.WORK/'SUPERVISOR.json',{'at_utc':started,'pid':os.getpid(),'owner_thread_id':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'fixed_deadline':scope['hard_deadline_at_utc'],'rolling_extension':False})
    with (t.WORK/'runtime.log').open('a') as log:
        process=subprocess.Popen([sys.executable,str(t.WORK/'run_collect.py')],stdout=log,stderr=subprocess.STDOUT)
        t.atomic(t.WORK/'SOURCE_SUBPROCESS.json',{'at_utc':t.utc(),'pid':process.pid,'supervisor_pid':os.getpid(),'fixed_deadline':scope['hard_deadline_at_utc']})
        code=process.wait()
    stop=t.read_json(t.WORK/'RUN_STOP.json',{})
    t.atomic(t.WORK/'SOURCE_EXIT.json',{'at_utc':t.utc(),'pid':process.pid,'exit_code':code,'stop':stop,'fixed_deadline_unchanged':True})
    if code or stop.get('pid')!=process.pid:
        t.atomic(t.WORK/'SUPERVISOR_NEEDS_ATTENTION.json',{'at_utc':t.utc(),'reason':'source subprocess exception or missing terminal reason; no premature all-frontiers completion','source_exit':code,'source_pid':process.pid});return
    reason=stop.get('reason','')
    if not reason.startswith(('fixed_deadline','resource_stop','frozen_frontiers_exhausted_or_source_blocked')):
        t.atomic(t.WORK/'SUPERVISOR_NEEDS_ATTENTION.json',{'at_utc':t.utc(),'reason':'source frontier pause requires proportionate permitted alternate-route assessment','source_stop':stop});return
    with (t.WORK/'terminal.log').open('a') as log:
        result=subprocess.run([sys.executable,str(t.WORK/'closeout.py')],stdout=log,stderr=subprocess.STDOUT)
    t.atomic(t.WORK/'TERMINAL_EXIT.json',{'at_utc':t.utc(),'exit_code':result.returncode,'source_pid':process.pid,'supervisor_pid':os.getpid(),'fixed_deadline_unchanged':True})
    if result.returncode:t.atomic(t.WORK/'SUPERVISOR_NEEDS_ATTENTION.json',{'at_utc':t.utc(),'reason':'changed-tranche closeout requires source-preserving repair','exit_code':result.returncode})

if __name__=='__main__':main()
