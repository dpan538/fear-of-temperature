"""Actual focused dispatch and restart/identity fixtures; no HTTP or Load."""
import sys,json,collections
import elt
sys.path.insert(0,str(elt.REPO/'src'))
import production,focused_repair as focus,run
import month_routes,broaden
from fear_temperature.media_planning.core import choose_opportunity
rows=focus.prepare();checks=[]
def check(name,value):checks.append(dict(name=name,passed=bool(value)))
check('exact_affected_frame_116',len(focus.MONTHS)==116)
ts=focus._ready['1994-01'];eligible=production.eligible(ts,production.KNOWN,set(elt.state()['targets']),{},'AU','historical_native')
check('real_month_inventory_more_than_two',len(eligible)>2)
options,payload=focus.options(collections.Counter());op=next(o for o in options if o.opportunity_id=='focused_gl:1994')
original=focus.acquire;received=[]
focus.acquire=lambda t:received.append(t)
run.dispatch(op,payload)
focus.acquire=original
check('actual_run_dispatch_accepts_focused_list_payload',received==[payload[op.opportunity_id][0]])
rec={'source_id':'green_left','source_url':ts[0]['url'],'raw_source_url':ts[0]['url'],'publication_date':'1994-01-19'}
receipt={'target':{'extra':{'month':'2026-09'}}};unchanged=json.dumps(receipt,sort_keys=True)
check('overlay_changes_expected_hint_only',focus.expected_month(rec,receipt)=='1994-01' and rec['publication_date']=='1994-01-19' and json.dumps(receipt,sort_keys=True)==unchanged)
aid=elt.article_id('green_left',ts[0]['url'])
check('stable_ID_on_saved_replay',aid==elt.article_id('green_left',ts[0]['url']) and aid==elt.article_id('green_left',elt.canon(ts[0]['url'])))
tid=elt.transport_target_id('green_left','article',eligible[0]['url']);old_replay=focus._replay;old_done=focus._replay_done
focus._replay={tid:{'fixture':'named saved pending native date conflict'}};focus._replay_done=set()
candidates=production.eligible(eligible[:4],production.KNOWN,{tid},{},'AU','historical_native')
check('saved_pending_touch_does_not_suppress_named_replay',len(candidates)==4)
focus._replay_done={tid};candidates=production.eligible(eligible[:4],production.KNOWN,{tid},{},'AU','historical_native')
check('durable_replay_done_survives_next_selection',len(candidates)==3)
focus._replay_done=set();candidates=production.eligible(eligible[:4],production.KNOWN|{elt.canon(eligible[0]['url'])},{tid},{},'AU','historical_native')
check('committed_identity_wins_over_replay_candidate',len(candidates)==3)
focus._replay=old_replay;focus._replay_done=old_done
issues=json.loads((elt.OWN/'GL_ISSUE_QUEUE.json').read_text())[:2]
original_dispositions=production._DIRECTORY_SCOPE
production._DIRECTORY_SCOPE={issues[0]['url']:{'status':'pending_or_observed_empty','evidence_revision':production.issue_evidence_revision(issues[0])}}
check('zero_or_pending_issue_advances_to_next_locator',production.issue_eligible(issues,set())==[issues[1]])
revised=dict(issues[0],index_receipt={'new_native_evidence':'fixture'})
check('new_locator_evidence_allows_reconsideration',production.issue_eligible([revised],set())==[revised])
production._DIRECTORY_SCOPE=original_dispositions
broaden.active_ids();routes=month_routes.prepare();key=next(iter(routes));r=routes[key]
original_perform=month_routes.perform;dispatched=[];month_routes.perform=lambda value:dispatched.append(value)
from fear_temperature.media_planning.core import Opportunity
run.dispatch(Opportunity(key,'named_missing_month',r['source_id'],r['month'],r['month'],'Source-advertised query'),{})
month_routes.perform=original_perform
check('actual_run_dispatch_accepts_named_missing_month_route',dispatched==[key])
check('month_query_uses_advertised_schema_and_fixed_month',all(v['schema_receipt'] and v['collection_url'] and v['permitted_query_checked'] and 'after=' in v['next_url'] and 'before=' in v['next_url'] for v in routes.values()))
result=dict(at_utc=elt.utc(),all_passed=all(c['passed'] for c in checks),checks=checks,metadata_inventory_only=True,HTTP_executed=False,database_Load_executed=False,real_1994_01_surplus_candidate_URLs=len(eligible),named_saved_replay_candidates=len(focus._replay))
elt.preparation_save('FOCUSED_REGRESSION_CHECK.json',result);assert result['all_passed'],checks
chain=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());chain['focused_regression_checks']=checks;chain['all_passed']=chain['all_passed'] and result['all_passed'];elt.preparation_save('CHANGED_CHAIN_CHECK.json',chain)
print(json.dumps({k:result[k] for k in ['all_passed','real_1994_01_surplus_candidate_URLs','named_saved_replay_candidates']}),flush=True)
