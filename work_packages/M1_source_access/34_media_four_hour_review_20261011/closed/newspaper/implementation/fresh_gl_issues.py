"""Coordinator-named fresh issue bodies with persistent fair issue rotation."""
import json,collections,re
import elt,production,focused_repair
from fear_temperature.media_planning.core import Opportunity
ISSUES=('293','294','295')
STATE='FRESH_ISSUE_ARTICLE_CURSORS.json'
PROOF='HOUR2_FRESH_ISSUE_REAL_LOAD.json'

def locators():
 rows=json.loads((elt.OWN/'GL_ISSUE_QUEUE.json').read_text())
 out={i['url'].rsplit('/',1)[-1]:i for i in rows if i['url'].rsplit('/',1)[-1] in ISSUES}
 assert set(out)==set(ISSUES)
 return out

def inventory(issue):
 locator=locators()[issue];year=locator['publication_date'][:4];items={}
 for t in focused_repair._ready.get(locator['month'],[]):
  match=re.match(r'^/(\d{4})/(\d+)/',elt.urlsplit(t['url']).path)
  if match and match.groups()==(year,issue):items[elt.canon(t['url'])]=t
 return [items[u] for u in sorted(items)]

def reserved_urls():
 return {elt.canon(t['url']) for issue in ISSUES for t in inventory(issue)}

def state():
 path=elt.OWN/STATE
 return json.loads(path.read_text()) if path.exists() else {'version':1,'issues':{}}

def prepare():
 current=state()
 for issue,locator in locators().items():
  items=inventory(issue);current['issues'].setdefault(issue,dict(next_cursor=0,last_dispatch_at_utc=None,last_dispatch_round=None,completed_bounded_operations=0,attempted_URLs=[],prime_operation_completed=False))
  current['issues'][issue].update(issue_url=locator['url'],issue_publication_date=locator['publication_date'],expected_month=locator['month'],native_candidate_URLs=len(items),candidate_URL_inventory_sha256=elt.sha(json.dumps([t['url'] for t in items]).encode()),cursor_is_not_completion=True)
 elt.save(STATE,current)
 return current

def remaining(issue):
 return production.eligible(inventory(issue),production.KNOWN,set(elt.state()['targets']),{},'AU','historical_native')

def rotated(items,next_cursor):
 if not items:return []
 offset=next_cursor%len(items)
 return items[offset:]+items[:offset]

def options(aged):
 current=state();choices=[];payload={}
 for issue in ISSUES:
  items=inventory(issue);eligible={elt.canon(t['url']) for t in remaining(issue)};v=current['issues'][issue]
  candidates=[t for t in rotated(items,v['next_cursor']) if elt.canon(t['url']) in eligible]
  if not candidates:continue
  key='fresh_gl_issue:'+issue;locator=locators()[issue]
  choices.append(Opportunity(key,'named_fresh_issue_body','green_left',locator['month'],locator['month'],'Coordinator H2 exact issues293/294/295; live merged original directory candidates',wait_rounds=aged[key],need_priority=1))
  payload[key]=issue
 return choices,payload

def proof():
 p=elt.OWN/PROOF
 return json.loads(p.read_text()) if p.exists() else dict(version=1,coordinator_named_issues=list(ISSUES),same_hard_deadline=elt.SCOPE['hard_deadline_at_utc'],real_HTTP_and_normal_Load_not_fixtures=True,operation_article_bound_is_not_quota=True,issues={})

def acquire(issue,round_number,operation_bound=8):
 current=state();v=current['issues'][issue];items=inventory(issue);eligible={elt.canon(t['url']) for t in remaining(issue)}
 selected=[t for t in rotated(items,v['next_cursor']) if elt.canon(t['url']) in eligible][:operation_bound];results=[]
 for target in selected:
  elt.assert_release()
  if not production.eligible([target],production.KNOWN,set(elt.state()['targets']),{},'AU','historical_native'):continue
  tid=elt.transport_target_id('green_left','article',target['url']);result=None;source_error=None
  try:result=focused_repair.acquire(target)
  except ValueError as error:
   if not str(error).startswith('preserved_'):raise
   source_error=str(error)
  attempted=tid in elt.state()['targets'] or result is not None
  if not attempted and source_error is None:continue
  record=dict(at_utc=elt.utc(),issue=issue,dated_issue_url=v['issue_url'],dated_issue_publication_date=v['issue_publication_date'],source_url=target['url'],request_id=tid,article_id=(result or {}).get('article_id'),publication_date=(result or {}).get('publication_date'),load_status=(result or {}).get('load_status') or 'pending_source_access_stop',source_error=source_error)
  elt.append('FRESH_ISSUE_ARTICLE_ATTEMPTS.jsonl',record);results.append(record)
  if attempted:
   v['next_cursor']=next(i for i,t in enumerate(items) if elt.canon(t['url'])==elt.canon(target['url']))+1
   if target['url'] not in v['attempted_URLs']:v['attempted_URLs'].append(target['url'])
  v['last_dispatch_at_utc']=elt.utc();v['last_dispatch_round']=round_number;elt.save(STATE,current)
  out=proof();s=out['issues'].setdefault(issue,dict(issue_url=v['issue_url'],issue_publication_date=v['issue_publication_date'],initial_native_candidates=len(items),actual_results=[]))
  s['actual_results'].append(record);s.update(remaining_executable_candidates=len(remaining(issue)),next_cursor=v['next_cursor'],cursor_reference=STATE,original_issue_processed_flag_reset=False);out['updated_at_utc']=elt.utc();elt.save(PROOF,out)
 v['completed_bounded_operations']+=1;v['prime_operation_completed']=True;v['last_dispatch_at_utc']=elt.utc();v['last_dispatch_round']=round_number;elt.save(STATE,current)
 return results

def prime(round_number):
 performed=0
 # One concrete live bridge demonstration for each named issue, followed by
 # ordinary fair rotation. Every remaining candidate stays executable.
 for issue in ISSUES:
  if state()['issues'][issue]['prime_operation_completed']:continue
  if not remaining(issue):
   out=proof();out['issues'][issue]=dict(issue_url=locators()[issue]['url'],remaining_executable_candidates=0,actual_results=[],unavailability='Current identity/source/touched checks; no completed-article claim',cursor_reference=STATE);elt.save(PROOF,out);continue
  elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=round_number+performed,opportunity='fresh_gl_issue:'+issue,source_id='green_left',kind='acquisition',need_priority=0,coordinator_named_live_bridge=True))
  acquire(issue,round_number+performed);performed+=1
 return performed

def snapshot():
 current=state();out=proof()
 return dict(named_fresh_issues=list(ISSUES),proof_reference=PROOF,cursor_reference=STATE,issues={issue:dict(native_candidates=len(inventory(issue)),remaining_executable_candidates=len(remaining(issue)),next_cursor=current['issues'][issue]['next_cursor'],completed_bounded_operations=current['issues'][issue]['completed_bounded_operations'],actual_new_complete=sum(r.get('load_status')=='confirmed_complete' for r in out['issues'].get(issue,{}).get('actual_results',[])),actual_pending=sum(r.get('load_status')!='confirmed_complete' for r in out['issues'].get(issue,{}).get('actual_results',[]))) for issue in ISSUES},no_month_or_issue_count_completion_gate=True)
