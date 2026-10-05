"""Persistent preparation, bounded release-gated execution and offline finalisation."""
import sys
sys.dont_write_bytecode=True
import csv,json,hashlib,argparse
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from transport import OUT,ROOT,STATE,read,save,budget,before_deadline,check_release,_fetch
from store import open_db,transaction,record_observation,record_request,finalize_review,counts
from metadata import extract
OLD=ROOT/'work_packages/M1_source_access/19_gov_closeout_and_media_transition_20261005/02_media_precollection'
def insert(c,table,values):c.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))
def csv_rows(path):
 with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def initialise(path=None,plan=None):
 c=open_db(path or OUT/'media_execution.sqlite')
 sources=csv_rows(OLD/'SOURCE_SELECTION_FROZEN.csv');slots=csv_rows(OLD/'PILOT_SLOTS.csv');pol=read(OLD/'SOURCE_ROUTE_POLICY.json')
 if not c.execute('SELECT 1 FROM outlet LIMIT 1').fetchone():
  with transaction(c):
   for s in sources:
    src=s['source_id'];ed='edition:'+src
    insert(c,'publisher',{'publisher_id':'publisher:'+src,'name':s['publisher'],'hq_verification':'unknown; frozen country is a planning anchor'})
    insert(c,'outlet',{'source_id':src,'publisher_id':'publisher:'+src,'outlet_name':s['outlet'],'outlet_type':s['outlet_type'],'official_home':s['official_home']})
    insert(c,'edition',{'edition_id':ed,'source_id':src,'region_layer':s['region_layer'],'edition_market':s['edition_market'],'edition_verification':'item_edition_unverified','region_assignment_basis':'original frozen source/market anchor'})
    for month in read(OUT/'control/SCOPE.json')['original_months']:
     era='era20:'+src+':'+month;f=next(x['frame_id'] for x in slots if x['source_id']==src and x['month']==month)
     insert(c,'source_era',{'era_id':era,'edition_id':ed,'month':month,'medium':'original frame, not newly requested','applicability':'original_stop_preserved','era_scope_note':pol[src]['reason'],'rights_status':pol[src]['rights_status'],'access_status':'no_new_request'})
     insert(c,'frame',{'frame_id':f,'era_id':era,'provider':src,'month':month,'unit':'article_publication_instance','date_filter_json':json.dumps({'month':month,'endpoint':'2026-09-21'}),'type_filter_json':'{"topic_filter":null}','enumeration_state':'original_stop_preserved','page_limit':1,'scope_detail':'original150 slots; no new corpus presence inferred'})
   for x in slots:insert(c,'sample_slot',{'slot_id':x['slot_id'],'frame_id':x['frame_id'],'slot_index':int(x['slot_index']),'status':x['status'],'unfilled_reason':x['unfilled_reason'],'selection_design':x['selection_design'],'planned_region_weight':.2,'planned_source_within_region_weight':.5,'observed_inventory_weight':1})
 if plan:register_candidates(c,plan)
 return c

def register_candidates(c,plan):
 with transaction(c):
  for s in plan.get('candidate_sources',[]):
   src=s['source_id'];ed=s['edition_id']
   if not c.execute('SELECT 1 FROM outlet WHERE source_id=?',(src,)).fetchone():
    insert(c,'publisher',{'publisher_id':'publisher:'+src,'name':s['publisher'],'hq_country':s['publisher_country'],'hq_evidence_url':s['identity_evidence_url'],'hq_verification':s['publisher_country_basis']})
    insert(c,'outlet',{'source_id':src,'publisher_id':'publisher:'+src,'outlet_name':s['name'],'outlet_type':s['genre'],'official_home':s['official_home'],'editorial_identity_evidence':s['identity_evidence_url']})
    insert(c,'edition',{'edition_id':ed,'source_id':src,'region_layer':s['region_layer'],'edition_market':s['edition_market'],'edition_market_evidence':s['market_evidence_url'],'edition_verification':'declared European English market; member publisher attribution remains per article','region_assignment_basis':s['region_basis']})
    insert(c,'candidate_mapping',{'mapping_id':s['mapping_id'],'original_source_id':s['original_source_id'],'candidate_source_id':src,'candidate_edition_id':ed,'region_layer':s['region_layer'],'scope_changed':1,'reason':s['revision_reason'],'evidence':json.dumps(s['evidence_urls'])})
   else:
    m=c.execute('SELECT candidate_source_id,candidate_edition_id,original_source_id,region_layer FROM candidate_mapping WHERE mapping_id=?',(s['mapping_id'],)).fetchone()
    if m!=(src,ed,s['original_source_id'],s['region_layer']):raise RuntimeError('Frozen candidate identity changed')
  for cell in plan.get('released_candidates',[])+plan.get('nonexecuted_cells',[]):
   f=cell['frame_id'];era='era20:'+cell['source_id']+':'+cell['month']
   if not c.execute('SELECT 1 FROM frame WHERE frame_id=?',(f,)).fetchone():
    insert(c,'source_era',{'era_id':era,'edition_id':cell['edition_id'],'month':cell['month'],'medium':'digital news/aggregation','applicability':cell.get('applicability','candidate_era_applicable'),'era_scope_note':'network launched2017; historical body version unknown','route':cell.get('query'),'rights_status':cell['rights_basis'],'rights_evidence_url':cell['rights_evidence_url'],'access_status':'public policy observed; article access untested' if cell.get('query') else 'not_applicable_before2017'})
    insert(c,'frame',{'frame_id':f,'era_id':era,'provider':cell['source_id'],'month':cell['month'],'unit':'article_publication_instance','date_filter_json':json.dumps({'query':cell.get('query'),'publication_month':cell['month']}),'type_filter_json':'{"topic_filter":null,"length_filter":null}','enumeration_state':'declared_partial_search_frame' if cell.get('query') else 'not_applicable_before2017','page_limit':1,'scope_detail':'One public date/domain search page; first five stable unique URLs; not monthly census; pi NULL. Pre2017 cells are not applicable and never requested.'})

def retain_attempt(c,source,r):
 with transaction(c):
  rid=None
  if r.get('raw_path'):
   rid='raw:'+r['sha256']
   if not c.execute('SELECT 1 FROM raw_object WHERE raw_id=?',(rid,)).fetchone():insert(c,'raw_object',{'raw_id':rid,'path':r['raw_path'],'sha256':r['sha256'],'byte_count':r['byte_count'],'mime_type':r.get('mime_type'),'object_kind':'HTTP_payload_not_automatically_article','is_partial':0,'rights_status':'route/per_article_review_pending','redistribution_status':'restricted_private_research; no automatic public redistribution','request_id':r['request_id'],'retained_at_utc':r['finished_at_utc']})
  elif r.get('partial_path'):
   rid='partial:'+r['request_id']
   if not c.execute('SELECT 1 FROM raw_object WHERE raw_id=?',(rid,)).fetchone():insert(c,'raw_object',{'raw_id':rid,'path':r['partial_path'],'sha256':r['partial_sha256'],'byte_count':r['byte_count'],'object_kind':'partial_HTTP_payload','is_partial':1,'rights_status':'unknown','redistribution_status':'restricted_private_research','request_id':r['request_id'],'retained_at_utc':r['finished_at_utc']})
  record_request(c,source,r,rid)

def process_payload(c,cell,r,original_slot,review=None):
 retain_attempt(c,cell['source_id'],r);pid=None
 if r['status']!='raw_retained':status='scope_changed_access_stopped'
 else:
  data=(OUT/r['raw_path']).read_bytes()
  if hashlib.sha256(data).hexdigest()!=r['sha256']:raise RuntimeError('Actual raw hash mismatch')
  parsed=extract(data,r['request_url'],cell['month'],cell.get('body_selector'));save(OUT/'evidence/parsed'/f"{r['request_id']}.json",parsed)
  if parsed['identity_status']!='canonical_JSONLD_match':status='scope_changed_identity_pending'
  elif not parsed['eligible_month']:status='scope_changed_first_date_outside_or_pending'
  else:
   bodypath=None
   # Route policy allows CC BY by default; exceptions must be checked in offline review.
   if parsed.get('body_text') and parsed['readability_status']!='preview_only':
    b=parsed['body_text'].encode();p=OUT/'bodies'/f"{r['request_id']}.txt";p.parent.mkdir(exist_ok=True)
    if not p.exists():budget(len(b));p.write_bytes(b)
    if p.read_bytes()!=b:raise RuntimeError('Body path already differs')
    bodypath=str(p.relative_to(OUT))
   review=review if review and review.get('rights_review')=='route_licence_applies_no_observed_exception' else None
   result=record_observation(c,cell['source_id'],cell['edition_id'],cell['frame_id'],parsed,r,r['raw_path'],bodypath,review);pid=result['parent_id']
   status='scope_changed_full_boundary_verified' if result['full_body_verified'] else 'scope_changed_article_boundary_or_rights_pending'
 with transaction(c):
  existing=c.execute('SELECT status,parent_id FROM candidate_sample WHERE original_slot_id=?',(original_slot,)).fetchone()
  if not existing:insert(c,'candidate_sample',{'original_slot_id':original_slot,'mapping_id':cell['mapping_id'],'candidate_frame_id':cell['frame_id'],'parent_id':pid,'status':status,'note':json.dumps({'request_id':r['request_id'],'raw_retained':bool(r.get('raw_path')),'original_source_success':False,'pi':None})})
 return status

def run_bodies(plan_path):
 check_release(plan_path);plan=read(plan_path)
 if not plan.get('released_candidates'):raise RuntimeError('No evidenced released candidate')
 c=initialise(plan=plan)
 try:
  for cell in plan['released_candidates']:
   before_deadline();receipt=OUT/cell['frame_receipt_path']
   if not receipt.exists():continue
   frame=read(receipt)
   if frame['query']!=cell['query'] or frame.get('frame_pages')!=1 or frame.get('monthly_denominator') is not None or frame.get('pi') is not None:raise RuntimeError('Partial frame evidence/query mismatch')
   frame_raw=OUT/frame['raw_receipt_path']
   if frame_raw.parent!=OUT/'raw' or frame_raw.is_symlink() or hashlib.sha256(frame_raw.read_bytes()).hexdigest()!=frame['raw_receipt_sha256']:raise RuntimeError('Frozen search response raw receipt/hash missing')
   budget()
   links=sorted(set(frame['article_urls']))[:5]
   if any(urlsplit(u).hostname!=cell['host'] for u in links):raise RuntimeError('Unapproved candidate host')
   robots_bytes=(OUT/cell['robots_raw_path']).read_bytes()
   if hashlib.sha256(robots_bytes).hexdigest()!=cell['robots_sha256']:raise RuntimeError('Frozen robots hash differs')
   robot=RobotFileParser();robot.parse(robots_bytes.decode().splitlines())
   if any(not robot.can_fetch(agent,u) for agent in ['FearTemperatureResearch','OAI-SearchBot','GPTBot'] for u in links):raise RuntimeError('Robots restriction; no alternate client/host')
   save(OUT/'evidence/frames'/f"{cell['source_id']}_{cell['month']}_selection.json",{'query':frame['query'],'selected_urls':links,'selection':'lexicographic first5 before body; no replacement for ineligible or failed bodies','pi':None,'monthly_denominator':None})
   with transaction(c):c.execute('UPDATE frame SET visited_pages=1,observed_unique_links=?,retrieval_at_utc=?,count_evidence=? WHERE frame_id=?',(len(set(frame['article_urls'])),frame['observed_at_utc'],str(receipt.relative_to(OUT)),cell['frame_id']))
   for i,u in enumerate(links,1):
    before_deadline();slot=cell['original_slot_ids'][i-1]
    if c.execute('SELECT 1 FROM candidate_sample WHERE original_slot_id=?',(slot,)).fetchone():continue
    state=read(STATE)
    if state['sources'].get(cell['source_id'],{}).get('halted'):break
    purpose='body:'+cell['source_id']+':'+cell['month']+':'+str(i)
    rid=hashlib.sha256(json.dumps([cell['source_id'],u,purpose],separators=(',',':')).encode()).hexdigest()[:32];cp=OUT/'evidence/requests'/f'{rid}.json'
    if cp.exists():
     r=read(cp)
     if r['status']=='in_progress':break
    else:r=_fetch(cell['source_id'],u,purpose)
    reviewpath=OUT/'evidence/reviews'/f"{r['request_id']}.json";review=read(reviewpath) if reviewpath.exists() else None
    process_payload(c,cell,r,slot,review)
    if r['status']!='raw_retained':break
 finally:terminal_slots(c,plan);c.close()

def finalise_reviews(c):
 for p in (OUT/'evidence/reviews').glob('*.json') if (OUT/'evidence/reviews').exists() else []:
  review=read(p);r=read(OUT/'evidence/requests'/p.name);parsed=read(OUT/'evidence/parsed'/p.name)
  if review.get('rights_review')!='route_licence_applies_no_observed_exception':continue
  row=c.execute('SELECT version_id FROM article_version JOIN raw_object USING(raw_id) WHERE request_id=?',(r['request_id'],)).fetchone()
  if row:finalize_review(c,row[0],parsed,review,OUT)

def terminal_slots(c=None,plan=None):
 rows=csv_rows(OLD/'PILOT_SLOTS.csv');planned={slot:cell for cell in (plan or {}).get('released_candidates',[])+(plan or {}).get('nonexecuted_cells',[]) for slot in cell['original_slot_ids']}
 for x in rows:
  cell=planned.get(x['slot_id']);obs=c.execute('SELECT candidate_source_id,parent_id,status FROM candidate_sample JOIN candidate_mapping USING(mapping_id) WHERE original_slot_id=?',(x['slot_id'],)).fetchone() if c else None
  full=False
  if obs and obs[1]:full=bool(c.execute("SELECT 1 FROM article_version WHERE parent_id=? AND readability_status='full_boundary_verified'",(obs[1],)).fetchone())
  x.update(round20_status=('scope_changed_full_boundary_verified' if full else obs[2]) if obs else (cell.get('terminal_status','scope_changed_not_attempted_pending_release_or_frame') if cell else 'original_stop_preserved_no_article_request'),candidate_source_id=obs[0] if obs else (cell['source_id'] if cell else ''),candidate_parent_id=obs[1] if obs and obs[1] else '',old_scope_unchanged=True,original_source_success=False,pi='')
 with (OUT/'SLOT_TERMINAL_150.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 return rows
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute-bodies',action='store_true');p.add_argument('--finalise-reviews',action='store_true');a=p.parse_args();plan=read(OUT/'ROUTE_PLAN.json')
 if a.execute_bodies:run_bodies(OUT/'ROUTE_PLAN.json')
 else:
  c=initialise(plan=plan)
  if a.finalise_reviews:finalise_reviews(c)
  terminal_slots(c,plan);print(json.dumps({'actual_counts':counts(c),'original_slots':150,'budget':budget()},ensure_ascii=False));c.close()
