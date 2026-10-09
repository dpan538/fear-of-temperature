"""Prospective non-campus newspaper production; accepted ELT, no article quota."""
from pathlib import Path
_LOCAL_OWN=Path(__file__).resolve().parent
_LOCAL_REPO=_LOCAL_OWN.parents[5]
_ORIGINAL_CONTEXT=_LOCAL_REPO/'work_packages/M1_source_access/27_newspaper_context_recovery_20261008/worker'
_code=(_ORIGINAL_CONTEXT/'elt.py').read_text().replace("'package27_context_recovery_20261008'","'newspaper_open_production_20261009'")
_guard='if not charged and effective_count(st,geo,purpose)>=limit:'
assert _code.count(_guard)==1
_code=_code.replace(_guard,'if limit is not None and not charged and effective_count(st,geo,purpose)>=limit:')
exec(compile(_code,str(_ORIGINAL_CONTEXT/'elt.py'),'exec'))
OWN=_LOCAL_OWN
PREDECESSOR=OWN.parents[1]/'20261008_global_distribution/worker'
CONTEXT_PREDECESSOR=_ORIGINAL_CONTEXT
SCOPE=json.loads((OWN/'EXECUTION_SCOPE.json').read_text())
DEADLINE=dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
NOT_BEFORE=dt.datetime.fromisoformat(SCOPE['earliest_network_and_load_start_at_utc'])
DB=REPO/SCOPE['newspaper_durable_database'];LOCK=REPO/SCOPE['shared_heavy_io_lock']
COVERAGE_PREDECESSOR=REPO/'work_packages/M1_source_access/26_newspaper_production_collection_20261006/worker/continuations/20261008_coverage'
QUEUE_ROOTS=[PREVIOUS,PRODUCTION_ROOT,COVERAGE_PREDECESSOR,CONTEXT_PREDECESSOR,PREDECESSOR]
RECEIPT_ROOTS=[OWN,PREDECESSOR,CONTEXT_PREDECESSOR,COVERAGE_PREDECESSOR,PRODUCTION_ROOT,PREVIOUS]
EXCLUDED=set(SCOPE['excluded_newspaper_analysis_source_ids'])

def assert_release():
 control=OWN.parent/'control';release=json.loads((control/'OWNER_RELEASE.json').read_text())
 assert release['version']==SCOPE['version']=='newspaper-open-production-20261009-15gb'
 assert release['status']=='CONDITIONALLY_RELEASED' and release['owner_thread_id']==os.environ['CODEX_THREAD_ID']==SCOPE['owner_thread_id']
 assert sha((control/'EXECUTION_SCOPE.json').read_bytes())==sha((OWN/'EXECUTION_SCOPE.json').read_bytes())==release['scope_sha256']
 assert sha((control/'INPUT_RECEIPT.json').read_bytes())==release['input_receipt_sha256']
 assert release['network_and_load_released_on_start_predicates']
 if dt.datetime.now(dt.timezone.utc)<NOT_BEFORE:raise RuntimeError('successor_not_before')
 start=json.loads((OWN/'SUCCESSOR_START_RECEIPT.json').read_text())
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


for _root in [PREDECESSOR,CONTEXT_PREDECESSOR]:
 for _line in (_root/'REQUESTS.jsonl').read_text().split('\n'):
  if _line:
   _r=json.loads(_line)
   if _r.get('status')!='saved':OLD_STOPS.add(_r['url'])
