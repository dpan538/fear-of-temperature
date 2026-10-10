"""Released continuous non-campus production, without article-count gates."""
import collections,csv,datetime as dt,json,pathlib,re,os,time
from bs4 import BeautifulSoup
import elt,extract_load,extra_jobs,broaden,native_batches

SOURCES={'EU/Europe excluding UK':[],'UK':[],'AU':['green_left','indaily'],'US':[],'NZ':[]}
LANES=None # Demand/readiness and bounded batch ageing; no fixed lane ratio
BASELINE=list(csv.DictReader((elt.OWN/'BASELINE_METADATA.csv').open()))
KNOWN={elt.canon(r[k]) for r in BASELINE if r['disposition']=='confirmed_complete' for k in ['source_url','raw_source_url'] if r.get(k)}
for _line in (elt.OWN/'LOAD_LOG.jsonl').read_text().split('\n') if (elt.OWN/'LOAD_LOG.jsonl').exists() else []:
 if _line:
  _record=json.loads(_line)
  if _record.get('load_status')=='confirmed_complete' and _record.get('source_url'):KNOWN.add(elt.canon(_record['source_url']))
_cache={}
_discovery_stops={}

def public_html_frontier_needs_discovery(sid):
 profile=next((p for p in broaden.profiles() if p['source_id']==sid and broaden.approved(p)),None)
 if not profile or profile.get('interface_type')!='publisher_native_sitemap':return False
 v=broaden._state().get(sid,{})
 return v.get('stage','robots') in ['robots','native_root'] or (v.get('stage')=='native_xml' and not v.get('queued_native_article_URLs'))
 # Once a public historical body frontier exists, regular production loads it;
 # remaining XML/category routes advance in the existing broader schedule.

def recovery_needs_discovery(lane,items,coverage,geo):
 return False # Coverage floor never prevents body production

def compact(t,reference=None,index=None):
 q={k:t[k] for k in ['source_id','url','article_url','native_post_id','representation','month','saved_request_id'] if k in t}
 e=t.get('native_evidence',{})
 title=e.get('title') if isinstance(e,dict) else None
 if reference:q['native_evidence']={'frozen_queue_reference':reference,'entry_index':index,'title':title}
 else:
  def slim(o):
   if isinstance(o,dict):
    if o.get('target_id') and ('hops' in o or 'target' in o):return {'receipt_reference':str((elt.OWN/'receipts'/(o['target_id']+'.json')).relative_to(elt.REPO)),'raw_reference':o.get('raw_reference'),'raw_sha256':o.get('raw_sha256'),'url':o.get('url')}
    return {k:slim(v) for k,v in o.items() if k not in ['content','content.rendered']}
   if isinstance(o,list):return [slim(v) for v in o]
   return o
  q['native_evidence']=slim(e)
 return q

def targets(sid):
 if sid not in _cache:
  _cache[sid]=[]
  for root in elt.QUEUE_ROOTS:
   p=root/'queues'/(sid+'.json')
   if p.exists():_cache[sid]+=[compact(t,str(p.relative_to(elt.REPO)),i) for i,t in enumerate(json.loads(p.read_text()))]
 p=elt.OWN/'queues'/(sid+'.json')
 return _cache[sid]+(json.loads(p.read_text()) if p.exists() else [])

def eligible(items,known,touched,coverage,geo,lane):
 candidates=[];host_stops=elt.state()['access_stops'];batch_status=native_batches.status_map()
 for t in items:
  sid=t['source_id'];tid=elt.transport_target_id(sid,'article',t['url'])
  if (tid in touched and not elt.named_saved_replay_allowed(tid)) or elt.canon(t.get('article_url') or t['url']) in known:continue
  if (elt.canon(t['url']) in elt.OLD_STOPS and not elt.transport_reopen_allowed(sid,'article',t['url'])) or elt.urlsplit(t['url']).hostname in host_stops:continue
  if t.get('native_post_id') and sid+':post:'+str(t['native_post_id']) in batch_status:continue
  if sid=='green_left':
   m=re.match(r'^/(\d{4})/(\d+)/',elt.urlsplit(t['url']).path)
   if m and int(m[1])<1991:continue # Declared source existence; never a corpus-wide start.
  if not ('1988-01'<=t.get('month','')<='2026-09' or t.get('representation') in ['publisher_camden_native_html','publisher_galway_native_html','publisher_evidenced_archive_HTML','publisher_newtown_native_html'] or sid=='green_left'):continue
  title=(t.get('native_evidence') or {}).get('title','') if isinstance(t.get('native_evidence'),dict) else ''
  candidates.append(t)
 if candidates and candidates[0].get('representation')=='publisher_camden_native_html':
  # Observed lastmod orders opportunities only; it never supplies publication dates or eligibility.
  candidates.sort(key=lambda t:((t.get('native_evidence') or {}).get('native_lastmod_observed') or '9999',elt.canon(t['url'])))
 if lane=='historical_native':
  # Prioritize gaps; production remains eligible after any minimum is reached.
  candidates.sort(key=lambda t:(t.get('month','') or (re.search(r'/(\d{4})/',t['url'])[1]+'-00' if re.search(r'/(\d{4})/',t['url']) else '9999'),elt.canon(t['url'])))
 return candidates

_DIRECTORY_SCOPE_FILE=elt.OWN/'GL_DIRECTORY_SCOPE_DISPOSITIONS.json'
_DIRECTORY_SCOPE=json.loads(_DIRECTORY_SCOPE_FILE.read_text()) if _DIRECTORY_SCOPE_FILE.exists() else {}
def issue_evidence_revision(issue):
 return elt.sha((json.dumps(issue,sort_keys=True)+'|'+elt.sha((elt.OWN/'green_left_issue_candidates.py').read_bytes())).encode())
def issue_eligible(issues,processed):
 # Pending/observed-empty in this scope is separate from body exhaustion.
 # New locator/parser evidence permits reconsideration; real stops persist.
 return [i for i in issues if i['url'] not in processed and elt.eligible(i['publication_date']) and _DIRECTORY_SCOPE.get(i['url'],{}).get('evidence_revision')!=issue_evidence_revision(i)]

def queue(sid,items):
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX)
  p=elt.OWN/'queues'/(sid+'.json'); old=json.loads(p.read_text()) if p.exists() else []
  keys={elt.canon(t['url']) for t in targets(sid)}
  for t in items:
   if elt.canon(t['url']) not in keys and elt.canon(t.get('article_url') or t['url']) not in KNOWN:
    old.append(compact(t));keys.add(elt.canon(t['url']))
  b=(json.dumps(old,ensure_ascii=False,separators=(',',':'))+'\n').encode();elt.preflight(len(b)*2)
  p.parent.mkdir(exist_ok=True);tmp=p.with_suffix('.pending');tmp.write_bytes(b);tmp.replace(p)
 return len(old)

# Reuse accepted native discovery parsers, replacing their queue/raw readers.
import importlib.util
_spec=importlib.util.spec_from_file_location('accepted_native_discovery',elt.PREVIOUS/'calendar_run.py')
native=importlib.util.module_from_spec(_spec)
_native_source=(elt.PREVIOUS/'calendar_run.py').read_text()
_native_source=_native_source[:_native_source.index('def perform_pair(')]
exec(compile(_native_source,str(elt.PREVIOUS/'calendar_run.py')+'#discovery-only','exec'),native.__dict__)
native.queue=queue;native.KNOWN=KNOWN
_old_get=native.get
def get(url,sid,evidence):
 if url in native.ROOTS:return _old_get(url,sid,evidence)
 r=elt.fetch(url,sid,extract_load.ADAPTERS[sid]['stratum'],'discovery',evidence)
 return (elt.read_payload(r['raw_reference']) if r['status']=='saved' else b''),r
native.get=get
from green_left_issue_candidates import issue_candidates
def scoped_gl_issue(issue):
 raw,receipt=get(issue['url'],'green_left',{'observed_dated_issue':issue,'scoped_directory_parser':True})
 if receipt['status']!='saved':return 0
 result=issue_candidates(raw,issue['url']);items=[]
 for candidate in result['candidates']:
  if candidate['issue_relation']!='path_issue_matches':
   elt.append('GREEN_LEFT_DIRECTORY_PENDING.jsonl',dict(at_utc=elt.utc(),issue_url=issue['url'],candidate=candidate,raw_reference=receipt.get('raw_reference'),action='Preserved unresolved path/issue relation; no date assignment'));continue
  items.append(dict(source_id='green_left',url=candidate['url'],month=issue['month'],native_evidence=dict(title=candidate['title'],dated_native_issue=issue,issue_receipt={k:receipt.get(k) for k in ['target_id','raw_reference','raw_sha256']},issue_relation=candidate['issue_relation'],date_assignment=candidate['date_assignment'])))
 queue('green_left',items);elt.append('GREEN_LEFT_DIRECTORY_RESULTS.jsonl',dict(at_utc=elt.utc(),issue_url=issue['url'],issue_publication_date=issue['publication_date'],parser_status=result['status'],queued_native_candidates=len(items),HTTP_success_is_not_directory_success=True,raw_reference=receipt.get('raw_reference')))
 return len(items)
native.gl_issue=scoped_gl_issue

def prepare():
 return {'inherited_native_cursors':json.loads((elt.OWN/'NATIVE_CURSORS.json').read_text())['cursors'],'old_queues_copied':False}

def discovery(sid):
 p=elt.OWN/'NATIVE_CURSORS.json';o=json.loads(p.read_text());c=o['cursors'];r=o['routes'];work=0
 if sid in ['trinity_news','mancunion','mit_tech']:
  key={'trinity_news':'trinity','mancunion':'manc','mit_tech':'tech'}[sid]
  if c[key]<len(r[key]):
   url=r[key][c[key]]
   (native.issue_html(url) if sid=='mit_tech' else native.sitemap(url,sid));c[key]+=1;work=1
 elif sid=='beaver':
  np=elt.OWN/'BEAVER_NEXT_PAGE.json';url=(json.loads(np.read_text()) if np.exists() else o['beaver_next']).get('url')
  if url:native.beaver_metadata(url);work=1
 elif sid=='green_left':
  issues=json.loads((elt.OWN/'GL_ISSUE_QUEUE.json').read_text());done=set(json.loads((elt.OWN/'GL_ISSUES_PROCESSED.json').read_text()));cov={};available=issue_eligible(issues,done)
  gaps=[i for i in available if i['month']<='1991-01']
  advance=choose_gl_action(_current_lane,available,gaps,c['gl']<len(r['gl']))
  if advance=='index':native.gl_index(r['gl'][c['gl']]);c['gl']+=1;work=1
  elif advance=='issue':
   issue=min(gaps or available,key=lambda i:(i['month'],i['publication_date']))
   queued=native.gl_issue(issue)
   if queued:done.add(issue['url']);elt.save('GL_ISSUES_PROCESSED.json',sorted(done))
   else:
    try:receipt=elt._receipt(elt.transport_target_id('green_left','discovery',issue['url']))
    except ValueError:receipt={'status':'missing_saved_receipt'}
    status='transport_unavailable' if receipt.get('status')!='saved' else 'pending_identity_or_observed_empty'
    results=elt.OWN/'GREEN_LEFT_DIRECTORY_RESULTS.jsonl'
    if receipt.get('status')=='saved' and results.exists():
     for line in results.read_text().splitlines():
      row=json.loads(line)
      if row.get('issue_url')==issue['url']:status='observed_empty' if row.get('parser_status')=='observed_empty_issue_directory' else 'pending_identity_or_container'
    _DIRECTORY_SCOPE[issue['url']]=dict(at_utc=elt.utc(),evidence_revision=issue_evidence_revision(issue),status=status,transport_status=receipt.get('status'),processed_flag_added=False,body_exhaustion=False,reconsideration='New dated locator/parser/response evidence; no repeated unchanged parse within this scope')
    elt.save('GL_DIRECTORY_SCOPE_DISPOSITIONS.json',_DIRECTORY_SCOPE)
    elt.append('GL_DIRECTORY_PARSE_PENDING.jsonl',dict(at_utc=elt.utc(),issue_url=issue['url'],processed_flag_added=False))
   work=1
 elif sid=='indaily':work=extract_load.indaily.discover(o,queue)
 elif sid in broaden.active_ids():work=broaden.discover(sid,queue)
 # ODT's policy stop remains in state; no synthetic dates or replacement retries.
 elt.save('NATIVE_CURSORS.json',o)
 return work

def consolidate_baseline(limit=1):
 return 0 # All141 external bodies are already in the accepted TEXT baseline.

_current_lane='recovery'
def choose_gl_action(lane,available,gaps,index_remaining):
 if gaps:return 'issue'
 if index_remaining:return 'index'
 if available:return 'issue'
 return 'index' if index_remaining else None

def available_discovery(sid):
 if sid in _discovery_stops:return 0
 try:return discovery(sid)
 except ValueError as error:
  if not str(error).startswith('preserved_'):raise
  _discovery_stops[sid]=str(error)
  elt.append('DISCOVERY_SOURCE_STOPS.jsonl',dict(at_utc=elt.utc(),source_id=sid,reason=str(error),network_retry=False,scope='Discovery unavailable in this run; other eligible source frames continue'))
  return 0


_inherited_targets=targets
_GL_ISSUE_DATES={elt.urlsplit(i['url']).path.rsplit('/',1)[-1]:i for i in json.loads((elt.OWN/'GL_ISSUE_QUEUE.json').read_text())}
def targets(sid):
 items=_inherited_targets(sid)
 if sid!='green_left':return items
 result=[]
 for original in items:
  t=dict(original);m=re.match(r'^/(\d{4})/(\d+)/',elt.urlsplit(t['url']).path);issue=_GL_ISSUE_DATES.get(m[2]) if m else None
  if m and issue and issue['publication_date'][:4]==m[1]:
   t['month']=issue['month'];t['native_evidence']=dict(t.get('native_evidence') or {},inherited_month_hint=original.get('month'),derived_issue_locator=issue['url'],locator_basis='URL issue number matches dated native issue inventory; publication date still checked independently on article')
  elif m and t.get('month','')[:4]!=m[1]:
   t['month']='';t['native_evidence']=dict(t.get('native_evidence') or {},inherited_month_hint=original.get('month'),locator_year=m[1],locator_basis='Conflicting inherited sidebar/month hint removed from derived ordering/date validation; article itself supplies publication date')
  result.append(t)
 return result
