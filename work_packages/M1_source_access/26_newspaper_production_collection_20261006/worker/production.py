"""One integrated 30% recovery / 70% continuing-production ELT task."""
import collections,csv,datetime as dt,json,pathlib,re,os,time
from bs4 import BeautifulSoup
import elt,extract_load

SOURCES={'EU/Europe excluding UK':['trinity_news'],'UK':['beaver','mancunion'],'AU':['green_left','indaily'],'US':['mit_tech'],'NZ':['otago_daily_times']}
LANES=['recovery','production','production','recovery','production','production','recovery','production','production','production']
BASELINE=list(csv.DictReader((elt.PREVIOUS/'ARTICLE_REGISTER.csv').open()))
KNOWN={elt.canon(r[k]) for r in BASELINE if r['disposition']=='confirmed_complete' for k in ['source_url','raw_source_url'] if r.get(k)}
_cache={}
_discovery_stops={}

def recovery_needs_discovery(lane,items,coverage,geo):
 return lane=='recovery' and bool(items) and all(coverage.get(('pooled',t['month']),0)>=2 and coverage.get((geo,t['month']),0)>=2 for t in items)

def compact(t,reference=None,index=None):
 q={k:t[k] for k in ['source_id','url','article_url','native_post_id','representation','month'] if k in t}
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
  p=elt.PREVIOUS/'queues'/(sid+'.json')
  _cache[sid]=[compact(t,str(p.relative_to(elt.REPO)),i) for i,t in enumerate(json.loads(p.read_text()))] if p.exists() else []
 p=elt.OWN/'queues'/(sid+'.json')
 return _cache[sid]+(json.loads(p.read_text()) if p.exists() else [])

def eligible(items,known,touched,coverage,geo,lane):
 candidates=[];host_stops=elt.state()['access_stops']
 for t in items:
  sid=t['source_id'];tid=elt.sha((sid+'|article|'+elt.canon(t['url'])).encode())[:24]
  if tid in touched or elt.canon(t.get('article_url') or t['url']) in known:continue
  if elt.canon(t['url']) in elt.OLD_STOPS or elt.urlsplit(t['url']).hostname in host_stops:continue
  if not '1988-01'<=t.get('month','')<='2026-09':continue
  title=(t.get('native_evidence') or {}).get('title','') if isinstance(t.get('native_evidence'),dict) else ''
  if sid=='green_left' and (title or '').strip().lower() in ['radio highlights','write on']:continue
  candidates.append(t)
 if lane=='recovery':
  # Prioritize gaps; production remains eligible after any minimum is reached.
  candidates.sort(key=lambda t:(coverage.get(('pooled',t['month']),0)>=2,coverage.get((geo,t['month']),0)>=2,t['month']))
 return candidates

def issue_eligible(issues,processed):
 # An issue's month reaching two is never a discovery exclusion.
 return [i for i in issues if i['url'] not in processed and elt.eligible(i['publication_date'])]

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
native=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(native)
native.queue=queue;native.KNOWN=KNOWN
_old_get=native.get
def get(url,sid,evidence):
 if url in native.ROOTS:return _old_get(url,sid,evidence)
 r=elt.fetch(url,sid,extract_load.ADAPTERS[sid]['stratum'],'discovery',evidence)
 return (elt.read_payload(r['raw_reference']) if r['status']=='saved' else b''),r
native.get=get

def prepare():
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX)
  for sids in SOURCES.values():
   for sid in sids:targets(sid)
 manifest=[];years=collections.Counter();st=elt.state();attempted=set(st['targets'])
 for geo,sids in SOURCES.items():
  for sid in sids:
   ts=targets(sid);available=eligible(ts,KNOWN,attempted,{},geo,'production')
   for t in ts:years[(sid,t['month'][:4])]+=1
   manifest.append({'source_id':sid,'stratum':geo,'frozen_queue_reference':str((elt.PREVIOUS/'queues'/(sid+'.json')).relative_to(elt.REPO)),'observed_distinct_candidate_links':len({elt.canon(t['url']) for t in ts}),'currently_unattempted_eligible_frontier':len(available),'old_content_copied':False})
 cursors=json.loads((elt.PREVIOUS/'DISCOVERY_PROGRESS.json').read_text())
 # Three named accepted index payloads are read solely to recover native cursor
 # lists, rather than discovering/hash-sweeping old corpus payloads.
 tr=BeautifulSoup((elt.OLD24/'raw/23cd5d9cb90826a9d7c7d538.bin').read_bytes(),'xml')
 ma=BeautifulSoup((elt.OLD24/'raw/814a7e0ce00db75df8aeaafa.bin').read_bytes(),'xml')
 te=BeautifulSoup((elt.OLD24/'raw/7beb68020911811b49c51045.bin').read_bytes(),'html.parser')
 tr_urls=[n.loc.text for n in tr.select('sitemap') if re.search(r'/post-sitemap\d*\.xml$',n.loc.text)]
 ma_urls=[n.loc.text for n in ma.select('sitemap') if re.search(r'/post-sitemap\d+\.xml$',n.loc.text)]
 ma_urls=sorted(ma_urls,key=lambda u:(0 if 'sitemap92.' in u or 'sitemap93.' in u else 1,-int(re.search(r'sitemap(\d+)',u)[1])))
 volumes=collections.defaultdict(list)
 for u in sorted({elt.urljoin('https://thetech.com',a['href']) for a in te.select('a.issue[href]') if re.match(r'/issues/(12[7-9]|13\d|14[0-6])/',a['href'])},key=lambda u:tuple(map(int,u.rsplit('/issues/',1)[1].split('/')))):
  volumes[int(u.rsplit('/issues/',1)[1].split('/')[0])].append(u)
 broad=[]
 for round_number in range(12):
  for volume,urls in sorted(volumes.items()):
   u=urls[min(len(urls)-1,round_number*len(urls)//12)]
   if u not in broad:broad.append(u)
 tech_urls=broad+[u for urls in volumes.values() for u in urls if u not in broad]
 routes={'trinity':tr_urls,'manc':ma_urls,'tech':tech_urls,'gl':['https://www.greenleft.org.au/back-issues?page='+str(i) for i in range(30,-1,-1)]}
 old_issues=elt.PREVIOUS/'GL_ISSUE_QUEUE.json'
 elt.preparation_save('GL_ISSUE_QUEUE.json',[dict(url=i['url'],publication_date=i['publication_date'],month=i['month'],index_receipt={'frozen_issue_queue_reference':str(old_issues.relative_to(elt.REPO)),'entry_index':n}) for n,i in enumerate(json.loads(old_issues.read_text()))])
 elt.preparation_save('NATIVE_CURSORS.json',{'cursors':cursors,'routes':routes,'beaver_next':json.loads((elt.PREVIOUS/'BEAVER_NEXT_PAGE.json').read_text()),'gl_processed_reference':str((elt.PREVIOUS/'GL_ISSUES_PROCESSED.json').relative_to(elt.REPO)),'gl_issue_queue_reference':str((elt.PREVIOUS/'GL_ISSUE_QUEUE.json').relative_to(elt.REPO)),'routes_basis':'Named accepted publisher indexes and already declared native pagination family; no invented article URLs/dates.'})
 elt.preparation_save('QUEUE_MANIFEST.json',{'at_utc':elt.utc(),'sources':manifest,'compact_references_only':True,'source_year_inventory_scope':'Observed frozen native candidate queues, not full newspaper archives','source_year_inventory':[{'source_id':s,'year':y,'observed_candidate_links':n} for (s,y),n in sorted(years.items())]})
 elt.preparation_save('TRANSPORT_STATE.json',st)
 registry=json.loads((elt.REPO/elt.SCOPE['source_registry_reference']).read_text())
 elt.preparation_save('SOURCE_READINESS.json',{'at_utc':elt.utc(),'registry_reference':elt.SCOPE['source_registry_reference'],'additional_parents_activated':0,'retained_active_frames':manifest,'broadening_candidates':[{'title_id':s['title_id'],'title':s['title'],'stratum':s['stratum'],'country':s['country'],'edition':s['edition'],'frame_role':s['frame_role'],'access_state':s['access_state'],'retention_conditions':s['retention_conditions'],'acquisition_routes':s['acquisition_routes']} for s in registry['sources'] if s['title_id'] not in extract_load.ADAPTERS],'qualification':'A blocked rights/key/robots/subscription route is not reopened. Papers Past and Trove general/regional historical routes remain candidates with unresolved route/rate/transport mapping. No extra parent is declared viable solely from its registry entry.'})
 return manifest

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
  ip=elt.OWN/'GL_ISSUE_QUEUE.json';issues=json.loads((ip if ip.exists() else elt.REPO/o['gl_issue_queue_reference']).read_text())
  dp=elt.OWN/'GL_ISSUES_PROCESSED.json';done=set(json.loads((dp if dp.exists() else elt.REPO/o['gl_processed_reference']).read_text()));available=issue_eligible(issues,done)
  if available:
   issue=available[0];native.gl_issue(issue);done.add(issue['url']);elt.save('GL_ISSUES_PROCESSED.json',sorted(done));work=1
  elif c['gl']<len(r['gl']):native.gl_index(r['gl'][c['gl']]);c['gl']+=1;work=1
 elif sid=='indaily':work=extract_load.indaily.discover(o,queue)
 # ODT's policy stop remains in state; no synthetic dates or replacement retries.
 elt.save('NATIVE_CURSORS.json',o)
 return work

def consolidate_baseline(limit=1):
 c=elt.connect();present={r[0] for r in c.execute('SELECT article_id FROM articles')};c.close();count=0
 for r in BASELINE:
  if r['disposition']!='confirmed_complete' or r['article_id'] in present:continue
  body=(elt.REPO/r['body_reference']).read_text();q=dict(r,baseline_TEXT_consolidation=True,raw_provenance_reference='accepted frozen package25 ARTICLE_REGISTER.csv',previous_version_id=r.get('version_id'))
  elt.load(q,body);present.add(r['article_id']);count+=1
  if count>=min(limit,elt.SCOPE['accepted_external_baseline_TEXT_consolidation_ceiling']):break
 return count

def available_discovery(sid):
 if sid in _discovery_stops:return 0
 try:return discovery(sid)
 except ValueError as error:
  if not str(error).startswith('preserved_'):raise
  _discovery_stops[sid]=str(error)
  elt.append('DISCOVERY_SOURCE_STOPS.jsonl',dict(at_utc=elt.utc(),source_id=sid,reason=str(error),network_retry=False,scope='Discovery unavailable in this run; other eligible source frames continue'))
  return 0

def progress_checkpoint(label,first=False):
 baseline_ids={r['article_id'] for r in BASELINE if r['disposition']=='confirmed_complete'}
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);c=elt.connect()
  qualified=c.execute('SELECT a.article_id FROM articles a LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL').fetchall()
  new_ids=[r[0] for r in qualified if r[0] not in baseline_ids]
  proof=[]
  if first:
   for aid in new_ids[:5]:
    row=c.execute('SELECT a.article_id,a.source_url,a.publication_date,a.latest_version_id,length(v.body_text),v.body_sha256,v.raw_reference FROM articles a JOIN article_versions v ON v.version_id=a.latest_version_id WHERE a.article_id=?',(aid,)).fetchone()
    proof.append(dict(zip(['article_id','source_url','publication_date','version_id','whole_TEXT_characters','body_sha256','raw_reference'],row)))
  c.close()
 checkpoint={'at_utc':elt.utc(),'label':label,'new_qualified_article_IDs':len(new_ids),'qualified_whole_TEXT_store_IDs':len(qualified),'baseline_TEXT_consolidated':len(qualified)-392-len(new_ids),'whole_TEXT_Load_evidence':proof,'cumulative_attempts':elt.state()['strata'],'resource':elt.resource(),'deadline_unchanged':elt.SCOPE['hard_deadline_at_utc']}
 elt.save('FIRST_REAL_COLLECTION_CHECKPOINT.json' if first else 'PRODUCTION_CHECKPOINT.json',checkpoint)
 elt.append('PRODUCTION_CHECKPOINT_HISTORY.jsonl',checkpoint)
 print(json.dumps({'REAL_COLLECTION':label,'at_utc':checkpoint['at_utc'],'new_qualified_IDs':len(new_ids),'whole_TEXT_store_IDs':len(qualified),'baseline_TEXT_consolidated':checkpoint['baseline_TEXT_consolidated'],'physical_headroom':checkpoint['resource']['physical_headroom']}),flush=True)
 return len(new_ids)

def run():
 if (elt.OWN/'PHYSICAL_BLOCK.json').exists():raise RuntimeError('Preserved capacity block: requires a meaningful external capacity/input change before another preflight')
 elt.preflight(elt.operation_footprint())
 elt.save('WORKER_PROCESS.json',{'pid':os.getpid(),'started_at_utc':elt.utc(),'single_writer':True,'hard_deadline':elt.SCOPE['hard_deadline_at_utc']})
 iteration=0;last_bytes=elt.cumulative();last_time=time.time();first_recorded=(elt.OWN/'FIRST_REAL_COLLECTION_CHECKPOINT.json').exists()
 try:
  while dt.datetime.now(dt.timezone.utc)<elt.DEADLINE:
   work=0;lane=LANES[iteration%10]
   for geo,sids in SOURCES.items():
    sid=sids[(iteration//2)%len(sids)];st=elt.state()
    elt.append('OPPORTUNITY_LOG.jsonl',{'at_utc':elt.utc(),'iteration':iteration,'stratum':geo,'source_id':sid,'planned_lane':lane})
    if st['strata'][geo]['article']>=elt.SCOPE['article_distinct_target_attempts_per_stratum']:continue
    cov=elt.coverage();ts=eligible(targets(sid),KNOWN,set(st['targets']),cov,geo,lane)
    if recovery_needs_discovery(lane,ts,cov,geo) and elt.effective_count(st,geo,'discovery')<elt.SCOPE['discovery_distinct_targets_per_stratum']:
     discovered=available_discovery(sid);work+=discovered
     if discovered:continue
    if ts:
     t=ts[0];result=extract_load.acquire(t);work+=1
     if result and result.get('load_status')=='confirmed_complete':KNOWN.add(elt.canon(result['source_url']))
    elif elt.effective_count(st,geo,'discovery')<elt.SCOPE['discovery_distinct_targets_per_stratum']:work+=available_discovery(sid)
   iteration+=1
   if not first_recorded:
    new_count=progress_checkpoint('First native body batch saved and immediately TEXT-loaded',first=True)
    first_recorded=new_count>0
   consolidate_baseline(limit=1)
   if elt.cumulative()-last_bytes>=elt.SCOPE['incremental_checkpoint_bytes'] or time.time()-last_time>=900:
    progress_checkpoint('Incremental retained-byte/time production checkpoint');last_bytes=elt.cumulative();last_time=time.time()
   if iteration%10==0:progress_checkpoint('Continuing native production progress')
   if not work:break
 except RuntimeError as error:
  elt.preparation_save('EXECUTION_STOP.json',{'at_utc':elt.utc(),'reason':str(error),'further_network':False})
 except Exception as error:
  elt.preparation_save('EXECUTION_ERROR.json',{'at_utc':elt.utc(),'reason':repr(error),'phase':'named runtime defect; inputs and attempts preserved'})
  raise
 finally:
  elt.preparation_save('WORKER_PROCESS.json',{'pid':os.getpid(),'status':'exiting','at_utc':elt.utc(),'single_writer':True})

if __name__=='__main__':run()
