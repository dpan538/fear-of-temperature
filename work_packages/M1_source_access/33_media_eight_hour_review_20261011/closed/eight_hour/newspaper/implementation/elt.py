"""Prospective non-campus newspaper production; accepted ELT, no article quota."""
from pathlib import Path
_LOCAL_OWN=Path(__file__).resolve().parent
_LOCAL_REPO=_LOCAL_OWN.parents[5]
_ORIGINAL_CONTEXT=_LOCAL_REPO/'work_packages/M1_source_access/27_newspaper_context_recovery_20261008/worker'
_code=(_ORIGINAL_CONTEXT/'elt.py').read_text().replace("'package27_context_recovery_20261008'","'newspaper_focused_repair_20261010'")
_guard='if not charged and effective_count(st,geo,purpose)>=limit:'
assert _code.count(_guard)==1
_code=_code.replace(_guard,'if limit is not None and not charged and effective_count(st,geo,purpose)>=limit:')
_spacing_needle="delay=SCOPE['min_per_host_spacing_seconds']-(time.time()-st['hosts'].get(host,0))"
assert _code.count(_spacing_needle)==1
_code=_code.replace(_spacing_needle,"delay=provider_spacing(current,sid)-(time.time()-st['hosts'].get(host,0))")
_request_needle="    with session.request(method,current,stream=True,allow_redirects=False,timeout=(max(.1,min(15,remaining)),max(.1,min(30,remaining)))) as response:"
assert _code.count(_request_needle)==1
_code=_code.replace(_request_needle,"    rec['HTTP_request_attempts_recorded']=rec.get('HTTP_request_attempts_recorded',0)+1\n"+_request_needle)
_retry_id_needle="tid=sha((sid+'|'+purpose+'|'+url).encode())[:24]; st=state()"
assert _code.count(_retry_id_needle)==1
_code=_code.replace(_retry_id_needle,"tid=transport_target_id(sid,purpose,url); st=state()")
_code=_code.replace('if url in OLD_STOPS:', 'if url in OLD_STOPS and not transport_reopen_allowed(sid,purpose,url):')
_month_needle="hint=receipt.get('target',{}).get('extra',{}).get('month')"
assert _code.count(_month_needle)==1
_code=_code.replace(_month_needle,'hint=expected_article_month(record,receipt)')
exec(compile(_code,str(_ORIGINAL_CONTEXT/'elt.py'),'exec'))
OWN=_LOCAL_OWN
EARLIER_CONTINUATION=OWN.parents[1]/'20261008_global_distribution/worker'
OPEN_PRODUCTION_PREDECESSOR=OWN.parents[1]/'20261009_newspaper_open_production/worker'
NINE_HOUR_PREDECESSOR=OWN.parents[1]/'20261009_nine_hour_newspaper/worker'
HISTORICAL_REPAIR_PREDECESSOR=OWN.parents[1]/'20261010_four_hour_historical_repair/worker'
PREDECESSOR=OWN.parents[1]/'20261010_broader_history_four_hour/worker'
CONTEXT_PREDECESSOR=_ORIGINAL_CONTEXT
SCOPE=json.loads((OWN/'EXECUTION_SCOPE.json').read_text())
DEADLINE=dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
NOT_BEFORE=dt.datetime.fromisoformat(SCOPE['earliest_network_and_load_start_at_utc'])
DB=REPO/SCOPE['newspaper_durable_database'];LOCK=REPO/SCOPE['shared_heavy_io_lock']
COVERAGE_PREDECESSOR=REPO/'work_packages/M1_source_access/26_newspaper_production_collection_20261006/worker/continuations/20261008_coverage'
QUEUE_ROOTS=[PREVIOUS,PRODUCTION_ROOT,COVERAGE_PREDECESSOR,CONTEXT_PREDECESSOR,EARLIER_CONTINUATION,OPEN_PRODUCTION_PREDECESSOR,NINE_HOUR_PREDECESSOR,HISTORICAL_REPAIR_PREDECESSOR,PREDECESSOR]
RECEIPT_ROOTS=[OWN,PREDECESSOR,HISTORICAL_REPAIR_PREDECESSOR,NINE_HOUR_PREDECESSOR,OPEN_PRODUCTION_PREDECESSOR,EARLIER_CONTINUATION,CONTEXT_PREDECESSOR,COVERAGE_PREDECESSOR,PRODUCTION_ROOT,PREVIOUS]
EXCLUDED=set(SCOPE['excluded_newspaper_analysis_source_ids'])

def assert_release():
 control=OWN.parent/'control'; release=json.loads((control/'OWNER_RELEASE.json').read_text())
 assert release['version']==SCOPE['version']=='newspaper-eight-hour-focused-repair-20261010-v1'
 assert release['status']=='CONDITIONALLY_RELEASED' and release['owner_thread_id']==os.environ['CODEX_THREAD_ID']==SCOPE['owner_thread_id']
 assert sha((control/'EXECUTION_SCOPE.json').read_bytes())==sha((OWN/'EXECUTION_SCOPE.json').read_bytes())==release['scope_sha256']
 assert sha((REPO/SCOPE['input_receipt_reference']).read_bytes())==release['input_receipt_sha256']
 assert release['network_and_durable_load_released']
 if 'network_and_load_released_on_start_predicates' in release:assert release['network_and_load_released_on_start_predicates']
 if dt.datetime.now(dt.timezone.utc)<NOT_BEFORE:raise RuntimeError('successor_not_before')
 if dt.datetime.now(dt.timezone.utc)>=DEADLINE:raise RuntimeError('fixed_deadline')
 start=json.loads((OWN/'START_RECEIPT.json').read_text())
 assert start['all_start_predicates_passed'] and start['previous_writer_exit_observed']
 if not globals().get('_START_SEAL_VERIFIED',False):
  for ref,h in start['frozen_predecessor_file_hashes'].items():assert sha((REPO/ref).read_bytes())==h
  for ref,h in start['implementation_hashes'].items():assert sha((OWN/ref).read_bytes())==h
  globals()['_START_SEAL_VERIFIED']=True
 assert SCOPE['hard_deadline_at_utc']==release['hard_deadline_at_utc']
 return release

_original_fetch=fetch
def fetch(url,sid,geo,*args,**kwargs):
 if sid in EXCLUDED:raise ValueError('excluded_campus_source_in_newspaper_lane '+sid)
 return _original_fetch(url,sid,geo,*args,**kwargs)

def coverage():
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);c=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True)
  rows=c.execute('SELECT a.publication_date,a.stratum,a.work_family_id FROM articles a LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL AND a.source_id NOT IN (?,?,?,?)',tuple(sorted(EXCLUDED))).fetchall();c.close()
 out=collections.defaultdict(set)
 for day,geo,family in rows:
  for g in ['pooled',geo]:out[g,day[:7]].add(family)
 return {k:len(v) for k,v in out.items()}
def native_article_unit_status(obj):
 from bs4 import BeautifulSoup
 if obj.get('content',{}).get('protected') or obj.get('status')!='publish' or obj.get('type')!='post':return 'pending_protected_or_nonpublic_native_body'
 dom=BeautifulSoup(obj.get('content',{}).get('rendered',''),'html.parser')
 for n in dom.select('script,style,form,svg,.sharedaddy,.related-posts'):n.decompose()
 if not any(c.isalnum() for c in dom.get_text(' ',strip=True)):return 'pending_image_original_TEXT_or_article_boundary'
 embedded=bool(dom.select('iframe,object,embed'))
 for n in dom.select('h1,h2,h3,h4,h5,h6,iframe,object,embed'):n.decompose()
 if not any(c.isalnum() for c in dom.get_text(' ',strip=True)):
  return 'pending_embedded_original_article_or_issue_mapping' if embedded else 'pending_heading_only_original_article_boundary'
 tables=dom.select('table')
 for n in tables:n.decompose()
 if tables and not any(c.isalnum() for c in dom.get_text(' ',strip=True)):return 'pending_table_only_original_article_boundary'
 return None

_parent_scoped_load=load

def load(record,body,status='confirmed_complete'):
 record=dict(record)
 if record.get('source_id') in EXCLUDED:raise ValueError('excluded_campus_source_in_newspaper_lane')
 record['collection_frame']='newspaper_current_noncampus'
 if record.get('source_native_post_id') and record.get('source_id') not in ['beaver','mancunion']:
  import broaden
  profile=next((p for p in broaden.profiles() if p['source_id']==record['source_id'] and broaden.approved(p)),None)
  if profile:
   record['article_id']=record['source_id']+':post:'+str(record['source_native_post_id'])
   record['retention_limit']=profile['retention_limit']
   record['native_identity_basis']='Source-verifiable persistent publisher post ID; canonical/alias URLs and body versions are separate'
   if record.get('request_id') and status=='confirmed_complete':
    rec=_receipt(record['request_id']);hint=record.get('native_listing_month') or rec.get('target',{}).get('extra',{}).get('month')
    url_day=re.search(r'/(\d{4})/(\d{2})/(\d{2})/',record.get('source_url',''))
    url_month='-'.join(url_day.groups())[:7] if url_day else None
    day_month=(record.get('publication_date') or '')[:7]
    if (hint and hint!=day_month) or (url_month and url_month!=day_month):
     record.update(expected_native_listing_month=hint,canonical_URL_month=url_month,date_mapping_status='conflicting native listing/URL and public article date; no override')
     status='pending_newspaper_native_date_mapping'
   if record.get('raw_reference') and status=='confirmed_complete':
    obj=json.loads(read_payload(record['raw_reference']))
    if isinstance(obj,list):
     matches=[item for item in obj if item.get('id')==record.get('native_batch_item_id')]
     assert len(matches)==1 and matches[0].get('id')==record['source_native_post_id']
     obj=matches[0]
    unit_status=native_article_unit_status(obj)
    if unit_status:
     record.update(native_unit_disposition_basis='Public native post has no readable original TEXT beyond images/headings/embedded resources, or is not a public published post; no length or topic threshold',complete_original_article_not_established=True)
     status=unit_status
 return _parent_scoped_load(record,body,status)


for _root in [PREDECESSOR,NINE_HOUR_PREDECESSOR,OPEN_PRODUCTION_PREDECESSOR,CONTEXT_PREDECESSOR]:
 for _line in (_root/'REQUESTS.jsonl').read_text().split('\n'):
  if _line:
   _r=json.loads(_line)
   if _r.get('status')!='saved':OLD_STOPS.add(_r['url'])

# A bounded append transaction changes rows/index paths, not every old body page.
# Allow8MiB dirty-page journal/index/slack plus3x UTF8 body and bounded raw/gzip.
# No full-store copy or migration is required. The physical48MiB recovery stays.
def operation_footprint(raw_cap=None,body_bytes=None):
 cap=raw_cap if raw_cap is not None else SCOPE['default_raw_object_cap_bytes']
 body=body_bytes if body_bytes is not None else cap*4
 return cap+cap//100+body*3+8*1024*1024

# Runtime metadata index replaces an unindexed per-article full version-table scan.
# Initialize while the existing loader holds the shared lock, reading no body TEXT.
_BODY_HASH_CANDIDATES=None
def _body_hash_candidate(c,bh,aid):
 global _BODY_HASH_CANDIDATES
 if _BODY_HASH_CANDIDATES is None:
  _BODY_HASH_CANDIDATES=collections.defaultdict(list)
  for article,family,digest in c.execute('SELECT v.article_id,a.work_family_id,v.body_sha256 FROM article_versions v JOIN articles a ON a.article_id=v.article_id ORDER BY v.rowid'):
   _BODY_HASH_CANDIDATES[digest].append((article,family))
  append('METADATA_LOOKUP_INDEX_RECEIPT.jsonl',{'at_utc':utc(),'scope':'article/version hash and family metadata only; no old body or raw read','version_hash_entries':sum(map(len,_BODY_HASH_CANDIDATES.values())),'candidate_only':True,'database_schema_changed':False})
 return next((item for item in _BODY_HASH_CANDIDATES.get(bh,[]) if item[0]!=aid),None)

# Identical hashes are prospective overlap candidates, preserving native families.
import inspect
_base_code=inspect.getsource(_load_previous)
_old="if match:record['work_family_id']=match[1];record['known_exact_body_copy_of']=match[0]"
assert _base_code.count(_old)==1
_base_code=_base_code.replace(_old,"if match:record['identical_body_candidate_of']=match[0];record['identity_action']='candidate_only; do_not_merge_or_delete'")
_lookup_needle="match=c.execute('SELECT v.article_id,a.work_family_id FROM article_versions v JOIN articles a ON a.article_id=v.article_id WHERE v.body_sha256=? AND v.article_id<>? LIMIT 1',(bh,aid)).fetchone()"
assert _base_code.count(_lookup_needle)==1
_base_code=_base_code.replace(_lookup_needle,'match=_body_hash_candidate(c,bh,aid)')
_base_code=_base_code.replace('def load(','def _non_destructive_base_load(',1)
exec(compile(_base_code,str(OWN/'elt.py')+'#base-loader','exec'))
_load_previous=_non_destructive_base_load

_previous_load=load
_new_totals=collections.Counter()
_first_http=None;_last_http=None;_first_load=None;_last_load=None
_event_registered=set()
def emit_committed_metadata(record):
 try:
  sid=record['source_id'];aid=record.get('article_id')
  if not aid or record.get('load_status')!='confirmed_complete':return
  if sid not in _event_registered:
   append('COMMITTED_METADATA_EVENTS.jsonl',{'kind':'source','revision':1,'source':{'source_id':sid,'stream':'newspaper'}});_event_registered.add(sid)
  append('COMMITTED_METADATA_EVENTS.jsonl',{'kind':'entity','revision':1,'unit':{'stream':'newspaper','source':sid,'entity_id':aid,'publication_key':record.get('work_family_id',aid),'publication_day':record['publication_date'],'countable_body':True,'date_usable':True,'body_hash':record.get('body_sha256',''),'acquisition_parent':sid}})
 except Exception as error:
  try:append('AUXILIARY_MONITOR_ERRORS.jsonl',{'at_utc':utc(),'error':repr(error),'Load_already_committed':True})
  except Exception:pass
def load(record,body,status='confirmed_complete'):
 global _first_load,_last_load
 result=_previous_load(record,body,status)
 if result.get('load_status')!='already_retained_identity':
  _new_totals[result.get('load_status',status)]+=1
  if result.get('load_status')=='confirmed_complete':
   _last_load=utc();_first_load=_first_load or _last_load;emit_committed_metadata(result)
 return result
_OWN_TRANSPORT_TARGET_IDS=set();_OWN_HTTP_RESPONSE_HOPS=0;_OWN_HTTP_REQUEST_ATTEMPTS_RECORDED=0;_OWN_REQUEST_RECEIPTS_WITHOUT_ATTEMPT_INSTRUMENTATION=0
_wrapped_fetch=fetch
def source_access_challenge(data):
 lower=data.lower()
 return b'_incapsula_resource' in lower and (b'noindex' in lower or b'incapsula incident id' in lower)

def preserve_source_access_challenge(rec):
 host=urlsplit(rec.get('final_url') or rec['url']).hostname;st=state()
 evidence={'status':200,'url':rec['url'],'source_denial_classification':'HTML access challenge instead of requested source document','receipt_reference':'receipts/'+rec['target_id']+'.json','raw_reference':rec['raw_reference'],'original_transport_status_preserved':rec['status'],'robots_permission_does_not_override_access_challenge':True}
 if host not in st['access_stops']:
  st['access_stops'][host]=evidence;save('TRANSPORT_STATE.json',st);append('SOURCE_ACCESS_CHALLENGE_REGISTER.jsonl',dict(at_utc=utc(),host=host,**evidence))
 return dict(rec,status='saved_source_access_challenge',original_transport_status=rec['status'])

def fetch(*args,**kwargs):
 global _first_http,_last_http,_OWN_HTTP_RESPONSE_HOPS,_OWN_HTTP_REQUEST_ATTEMPTS_RECORDED,_OWN_REQUEST_RECEIPTS_WITHOUT_ATTEMPT_INSTRUMENTATION
 result=_wrapped_fetch(*args,**kwargs)
 if result.get('status')=='saved' and result.get('raw_reference') and source_access_challenge(read_payload(result['raw_reference'])):result=preserve_source_access_challenge(result)
 if result.get('finished_at_utc') and result['finished_at_utc']>=SCOPE['earliest_network_and_load_start_at_utc']:
  if result['target_id'] not in _OWN_TRANSPORT_TARGET_IDS:
   _OWN_TRANSPORT_TARGET_IDS.add(result['target_id']);_OWN_HTTP_RESPONSE_HOPS+=len(result.get('hops',[]));_OWN_HTTP_REQUEST_ATTEMPTS_RECORDED+=result.get('HTTP_request_attempts_recorded',0);_OWN_REQUEST_RECEIPTS_WITHOUT_ATTEMPT_INSTRUMENTATION+=int('HTTP_request_attempts_recorded' not in result)
  if result.get('status')=='saved':
   stamp=result['finished_at_utc'];_last_http=max(_last_http or stamp,stamp);_first_http=min(_first_http or stamp,stamp)
 return result

# Provider delay is taken from every matching most-specific saved robots group.
# The accepted source-permission guard remains in broaden; this transport also
# preserves declared request-rate/host spacing, without an inherited count cap.
_PROVIDER_POLICY_CACHE={}
def provider_spacing(url,sid):
 minimum=float(SCOPE['min_per_host_spacing_seconds'])
 origin=urlunsplit((*urlsplit(url)[:2],'','',''));robots=origin+'/robots.txt'
 if canon(url)==canon(robots):return minimum
 tid=sha((sid+'|discovery|'+canon(robots)).encode())[:24]
 if tid in _PROVIDER_POLICY_CACHE:return max(minimum,_PROVIDER_POLICY_CACHE[tid])
 try:rec=_receipt(tid)
 except ValueError:return minimum # Reuse accepted original-frame policy evidence elsewhere.
 if rec.get('status')!='saved':return minimum
 text=read_payload(rec['raw_reference']).decode('utf-8',errors='replace')
 groups=[];agents=[];fields=[]
 for line in text.splitlines()+['User-agent: __end__']:
  key,sep,value=line.split('#',1)[0].partition(':')
  if not sep:continue
  key=key.strip().lower();value=value.strip()
  if key=='user-agent':
   if fields:groups.append((agents,fields));agents=[];fields=[]
   agents.append(value.lower())
  elif agents:fields.append((key,value))
 agent='fearoftemperatureresearch/1.0';matching=[]
 for agents,fields in groups:
  matches=[len(a) if a!='*' else 0 for a in agents if a=='*' or a in agent]
  if matches:matching.append((max(matches),fields))
 delays=[]
 if matching:
  best=max(n for n,_ in matching)
  for specificity,fields in matching:
   if specificity!=best:continue
   for key,value in fields:
    if key=='crawl-delay':
     try:delays.append(float(value.strip('<>')))
     except ValueError:pass
    elif key=='request-rate':
     try:
      count,seconds=value.split('/',1);delays.append(float(seconds)/float(count))
     except (ValueError,ZeroDivisionError):pass
 delay=max([minimum]+delays);_PROVIDER_POLICY_CACHE[tid]=delay
 return delay

# Restore this tranche's observation counters/times after controlled restarts.
if (OWN/'LOAD_LOG.jsonl').exists():
 for line in (OWN/'LOAD_LOG.jsonl').read_text().splitlines():
  if not line:continue
  rec=json.loads(line);_new_totals[rec.get('load_status','unknown')]+=1
  if rec.get('load_status')=='confirmed_complete':
   stamp=rec.get('loaded_at_utc');_first_load=_first_load or stamp;_last_load=stamp or _last_load
if (OWN/'REQUESTS.jsonl').exists():
 for line in (OWN/'REQUESTS.jsonl').read_text().splitlines():
  if not line:continue
  rec=json.loads(line)
  if rec['target_id'] not in _OWN_TRANSPORT_TARGET_IDS:
   _OWN_TRANSPORT_TARGET_IDS.add(rec['target_id']);_OWN_HTTP_RESPONSE_HOPS+=len(rec.get('hops',[]));_OWN_HTTP_REQUEST_ATTEMPTS_RECORDED+=rec.get('HTTP_request_attempts_recorded',0);_OWN_REQUEST_RECEIPTS_WITHOUT_ATTEMPT_INSTRUMENTATION+=int('HTTP_request_attempts_recorded' not in rec)
  if rec.get('status')=='saved':
   stamp=rec.get('finished_at_utc');_first_http=min(_first_http or stamp,stamp);_last_http=max(_last_http or stamp,stamp)

# Explicit named retries do not erase attempted IDs, receipts or native charges.
TRANSPORT_REOPENS=json.loads((OWN/'REOPEN_NO_HTTP_TARGETS.json').read_text())
def transport_reopen_allowed(sid,purpose,url):
 base=sha((sid+'|'+purpose+'|'+canon(url)).encode())[:24]
 return base in TRANSPORT_REOPENS
def transport_target_id(sid,purpose,url):
 base=sha((sid+'|'+purpose+'|'+canon(url)).encode())[:24]
 return TRANSPORT_REOPENS.get(base,{}).get('retry_target_id',base)

_R_GLOB_CUMULATIVE=cumulative
def cumulative():
 total=SCOPE['prior_media_bytes']
 for relative in SCOPE['media_lifetime_accounting_roots']:
  stack=[REPO/relative]
  while stack:
   directory=stack.pop()
   if not directory.exists():continue
   with os.scandir(directory) as entries:
    for entry in entries:
     if entry.is_dir(follow_symlinks=False):stack.append(Path(entry.path))
     elif entry.is_file():total+=entry.stat().st_size
 return total

# The focused module installs versioned named overlays before any Load.
def expected_article_month(record,receipt):
 return receipt.get("target",{}).get("extra",{}).get("month")
def named_saved_replay_allowed(tid):return False
