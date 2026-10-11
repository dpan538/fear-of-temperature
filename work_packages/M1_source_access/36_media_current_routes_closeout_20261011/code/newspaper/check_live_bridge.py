"""Exercise actual dispatch/eligibility/bridge and date validation, no real I/O."""
import json,collections,sqlite3
import elt,production,focused_repair as focus,run,broaden,extract_load
from fear_temperature.media_planning.core import Opportunity
checks=[]
def check(n,v):
 checks.append(dict(name=n,passed=bool(v)))
 assert v,n
real_reconciliation=focus.prepare()
real_options,real_payload=focus.options(collections.Counter())
real_inventory=sum(len(v) for v in real_payload.values())
check('real_saved_native_inventory_remains_eligible',real_inventory>6)
original=(elt.state,elt.save,elt.append,elt._receipt,elt.read_payload,elt.assert_release,elt._accepted_load,extract_load.acquire,production.KNOWN,broaden.active_ids,production.queue,production._cache,focus._ready,focus._month_overlay)
db=sqlite3.connect(':memory:');db.execute('create table fixture_commits(url text primary key)')
targets=[dict(source_id='green_left',url=f'https://www.greenleft.org.au/1994/124/fixture-{i}',month='1994-01',native_evidence={}) for i in range(8)]
known={elt.canon(t['url']) for t in targets[:2]};touched={elt.transport_target_id('green_left','article',t['url']) for t in targets[:2]}
for url in known:db.execute('insert into fixture_commits values (?)',(url,))
production.KNOWN=known
state=dict(targets=touched,access_stops={})
elt.state=lambda:state
elt.save=lambda *a,**k:None;elt.append=lambda *a,**k:None
calls=[]
def fixture_acquire(t):
 url=elt.canon(t['url']);calls.append(url)
 db.execute('insert or ignore into fixture_commits values (?)',(url,));db.commit()
 touched.add(elt.transport_target_id('green_left','article',url))
 return dict(source_url=url,publication_date='1994-01-19',article_id=elt.article_id('green_left',url),load_status='confirmed_complete')
extract_load.acquire=fixture_acquire
op=Opportunity('focused_gl:1994','named_legacy_source_era','green_left','1994-01','1994-01','fixture')
run.dispatch(op,{op.opportunity_id:targets})
check('eight_same_month_two_committed_all_remaining_six_Load',len(calls)==6 and db.execute('select count(*) from fixture_commits').fetchone()[0]==8)
run.dispatch(op,{op.opportunity_id:targets})
check('rerun_adds_zero',len(calls)==6)
known.clear();known.update(elt.canon(t['url']) for t in targets[:2]);touched.clear();touched.update(elt.transport_target_id('green_left','article',t['url']) for t in targets[:2])
db.execute('delete from fixture_commits');db.executemany('insert into fixture_commits values (?)',[(u,) for u in known]);db.commit()
def interrupted(t):
 result=fixture_acquire(t);known.add(elt.canon(t['url']))
 raise KeyboardInterrupt('fixture after durable first article')
extract_load.acquire=interrupted
try:run.dispatch(op,{op.opportunity_id:targets})
except KeyboardInterrupt:pass
remaining=production.eligible(targets,known,touched,{},'AU','historical_native')
check('interruption_after_one_preserves_other_five',len(remaining)==5)
extract_load.acquire=fixture_acquire
run.dispatch(op,{op.opportunity_id:remaining})
check('resume_Loads_remaining_five',db.execute('select count(*) from fixture_commits').fetchone()[0]==8)
issue=dict(url='https://www.greenleft.org.au/issue/124',publication_date='1994-01-19',month='1994-01')
rec=dict(status='saved',target_id='fixture-directory',raw_reference='fixture',raw_sha256='fixture')
focus._ready={};focus._month_overlay={};queued=[]
production.queue=lambda sid,items:queued.extend(items)
old_get=production.get
production.get=lambda *a: (b'<h1>Issue 124</h1><main><div class="layout-content"><div class="region-content"><a href="/1994/124/new-immediate">Native</a><a href="/1993/124/conflict">Wrong year</a></div></div></main>',rec)
production.scoped_gl_issue(issue)
production.get=old_get
check('actual_directory_parser_updates_live_ready_without_restart',len(queued)==1 and len(focus._ready['1994-01'])==1 and focus._ready['1994-01'][0]['url']==queued[0]['url'])
record=dict(source_id='green_left',source_url=queued[0]['url'],raw_source_url=queued[0]['url'],article_id='fixture-pending-date',publication_date='1994-02-02',request_id='fixture-date')
elt._receipt=lambda *a:dict(target=dict(extra=dict(month='1994-01')))
elt.assert_release=lambda:True
elt._accepted_load=lambda r,b,s:dict(r,load_status=s)
result=elt.load(record,'Fixture complete body')
check('independent_conflicting_article_date_stays_pending',result['load_status']=='pending_issue_article_date_conflict' and result['publication_date']=='1994-02-02')
production._cache={'green_left':[dict(source_id='green_left',url='https://www.greenleft.org.au/2005/650/generic-ready',month='2005-01',native_evidence={})]}
broaden.active_ids=lambda:[]
old_mo,old_io,old_bo=run.month_routes.options,run.named_issue_routes.options,run.berkeley_html.options
run.month_routes.options=run.named_issue_routes.options=run.berkeley_html.options=lambda a:([],{})
ops,payload=run.opportunities()
check('generic_GL_body_fallback_is_executable',any(o.opportunity_id=='green_left:body' for o in ops))
run.month_routes.options,run.named_issue_routes.options,run.berkeley_html.options=old_mo,old_io,old_bo
elt.state,elt.save,elt.append,elt._receipt,elt.read_payload,elt.assert_release,elt._accepted_load,extract_load.acquire,production.KNOWN,broaden.active_ids,production.queue,production._cache,focus._ready,focus._month_overlay=original
db.close()
result=dict(at_utc=elt.utc(),all_passed=all(c['passed'] for c in checks),checks=checks,real_native_candidate_inventory=real_inventory,production_HTTP_executed=False,production_database_Load_executed=False,fixture_commit_store='isolated in-memory SQLite only',baseline_empty_months=sorted(focus.ZEROS),old_flags_and_date_conflicts_not_reset=True)
elt.preparation_save('CHANGED_CHAIN_CHECK.json',result)
print(json.dumps(result))
