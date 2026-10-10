"""Changed named-issue/preparation dispatch regression; no HTTP or database Load."""
import sys,json,collections
import elt
sys.path.insert(0,str(elt.REPO/'src'))
import run,broaden,named_issue_routes as routes,focused_repair as focus,production
from fear_temperature.media_planning.core import Opportunity
checks=[]
def check(name,v):checks.append(dict(name=name,passed=bool(v)))
routes.prepare();ops,payload=routes.options(collections.Counter());chosen=ops[0];seen=[];old=routes.perform;routes.perform=lambda issue:seen.append(issue);run.dispatch(chosen,payload);routes.perform=old
check('actual_named_issue_dispatch_delivers_selected_locator',seen==[payload[chosen.opportunity_id]])
job=dict(job_id='fixture_selected_metadata',source_id='berkeley_daily_planet',stratum='US',kind='metadata_doc',url='https://www.berkeleydailyplanet.com/issue/2000-06-27/full_text')
key='prepare:'+job['job_id'];seen=[];old=broaden.perform_job;broaden.perform_job=lambda j:seen.append(j);run.dispatch(Opportunity(key,'source_preparation',job['source_id'],'1988-01','2026-09','fixture named source job',action_kind='route_resolution',need_priority=0),{key:job});broaden.perform_job=old
check('actual_preparation_dispatch_runs_exact_selected_job',seen==[job])
issue=payload[chosen.opportunity_id];flags=(elt.OWN/'GL_ISSUES_PROCESSED.json').read_bytes();saved=[];queued=[];added=[];appended=[]
originals=(elt.fetch,elt.read_payload,elt.save,elt.append,production.queue,focus.add_candidates)
fixture={'target_id':'fixture_named_directory','status':'saved','raw_reference':'fixture-no-HTTP','raw_sha256':'fixture'}
elt.fetch=lambda *a,**k:fixture
elt.save=lambda *a,**k:saved.append(a)
elt.append=lambda *a,**k:appended.append(a)
production.queue=lambda sid,items:queued.append(items)
focus.add_candidates=lambda *a:added.append(a)
n=issue['url'].rsplit('/',1)[-1]
elt.read_payload=lambda *a: ('<h1>Issue '+n+'</h1><main><div class="layout-content"><div class="region-content"><a href="/1999/'+n+'/test/complete-unit">Native article</a><a href="/1993/'+n+'/test/conflicting-year">Conflict preserved</a><aside><a href="/1999/999/aside">Sidebar</a></aside></div></div></main>').encode()
r=routes.perform(issue)
check('named_directory_preserves_processed_flag',flags==(elt.OWN/'GL_ISSUES_PROCESSED.json').read_bytes() and r['original_processed_flag_changed'] is False)
check('native_year_issue_matched_candidate_only_queued',len(queued[-1])==1 and queued[-1][0]['month']==issue['month'] and len(r['pending_candidates'])==1)
check('new_candidates_extend_real_focused_ready_chain',added[-1][0]==issue and added[-1][1]==queued[-1])
elt.read_payload=lambda *a: ('<h1>Issue '+n+'</h1><main><div class="layout-content"><div class="region-content"></div></div></main>').encode()
r=routes.perform(issue);check('empty_success_is_observed_empty_without_body_exhaustion',r['phase']=='observed_empty' and r['body_exhaustion'] is False and r['whole_archive_exhaustion'] is False)
elt.fetch,elt.read_payload,elt.save,elt.append,production.queue,focus.add_candidates=originals
result=dict(at_utc=elt.utc(),checks=checks,all_passed=all(c['passed'] for c in checks),HTTP_executed=False,database_Load_executed=False,old_processed_flag_preserved=True)
elt.preparation_save('NAMED_ROUTE_REGRESSION_CHECK.json',result);assert result['all_passed'],checks
chain=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());chain['named_route_regression_checks']=checks;chain['all_passed']=chain['all_passed'] and result['all_passed'];elt.preparation_save('CHANGED_CHAIN_CHECK.json',chain)
print(json.dumps({'all_passed':result['all_passed'],'changed_route_checks':len(checks)}))
