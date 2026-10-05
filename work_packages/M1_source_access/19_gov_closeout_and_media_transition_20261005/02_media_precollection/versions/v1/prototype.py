"""Bounded date/type media pilot. No topic query, credential discovery or gov DB.
Default writes/validates a separate small SQLite pilot from saved evidence.
--execute performs only allowlisted public route probes, never login/paywall access.
"""
import argparse,csv,fcntl,hashlib,json,os,re,shutil,sqlite3,time,sys
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
WP=ROOT/'work_packages/M1_source_access'
HEAVY=WP/'14_structural_validation_20261004/control/heavy_io.lock'
STATE=OUT/'HTTP_STATE.json'
SCOPE=OUT/'PILOT_SCOPE.json'
VERSION='media_route_pilot_v1_20261005'

def now():return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)
def read(p):return json.loads(Path(p).read_text())
def require(c,msg):
 if not c:raise RuntimeError(msg)
def sid(*parts):return hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:32]
def csv_write(path,rows,fields):
 with Path(path).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
@contextmanager
def lock():
 with HEAVY.open('a+') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:yield
  finally:fcntl.flock(f,fcntl.LOCK_UN)

def raw_account():
 root=OUT/'raw';files=[]
 require(not root.is_symlink(),'Raw symlink rejected')
 if root.exists():
  for p in sorted(root.rglob('*')):
   require(not p.is_symlink(),'Raw symlink rejected')
   if p.is_file():files.append({'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'partial':p.name.endswith('.part'),'sha256':sha(p)})
 return {'total_bytes':sum(p['bytes'] for p in files),'partial_bytes':sum(p['bytes'] for p in files if p['partial']),'files':files}
def budget(next_bytes=0):
 scope=read(SCOPE);used=raw_account()['total_bytes'];free=shutil.disk_usage(OUT).free
 require(used+next_bytes<=scope['raw_cap_bytes'],'128 MiB media raw cap reached')
 # Charge media bytes to the already reserved 1 GiB other-activity allowance.
 # Conservatively keep the entire government 2 GiB reserve; no gov corpus scan.
 other=1073741824-used-next_bytes
 reserve=scope['government_batch_reserved_bytes']+100000000+67108864+max(0,other)
 require(other>=0 and free-next_bytes-reserve>scope['storage_floor_bytes'],'15 GiB floor plus government reserves reached')
 return {'free_bytes':free,'media_raw_bytes':used,'media_cap_remaining_bytes':scope['raw_cap_bytes']-used,'government_reserved_bytes':scope['government_batch_reserved_bytes'],'other_activity_remaining_bytes':other,'reserved_bytes':reserve,'floor_bytes':scope['storage_floor_bytes']}

def canonical(url):
 p=urlsplit(url);query=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
 return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,urlencode(query),''))
def native_parent(source,url,native=None):return 'article:'+sid(source,native or canonical(url))
def dated_url(url):
 p=urlsplit(url).path
 m=re.search(r'/(\d{4})/(\d{2})/(\d{2})(?:/|[-.])',p)
 if m:
  try:return datetime.strptime('-'.join(m.groups()),'%Y-%m-%d').date().isoformat()
  except ValueError:return None
 return None

def article_jsonld(data):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(data,'html.parser');found=[]
 def walk(x):
  if isinstance(x,list):
   for y in x:walk(y)
  elif isinstance(x,dict):
   types=x.get('@type',[]);types=[types] if isinstance(types,str) else types
   if any(t in {'NewsArticle','Article','ReportageNewsArticle','OpinionNewsArticle'} for t in types):found.append(x)
   if '@graph' in x:walk(x['@graph'])
 for node in soup.find_all('script',type='application/ld+json'):
  try:walk(json.loads(node.string or node.get_text()))
  except (ValueError,TypeError):pass
 return found

def parse_article(data,url):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(data,'html.parser');items=article_jsonld(data);x=items[0] if items else {}
 link=soup.find('link',rel='canonical');canon=canonical(link.get('href')) if link and link.get('href') else canonical(url)
 published=x.get('datePublished');updated=x.get('dateModified');body=x.get('articleBody')
 precision='timestamp_with_offset' if published and re.search(r'(Z|[+-]\d\d:\d\d)$',published) else ('day' if published and re.fullmatch(r'\d{4}-\d{2}-\d{2}',published) else 'unknown')
 # A paywall/preview marker prevents claiming readable complete content.
 preview= x.get('isAccessibleForFree') is False or bool(soup.find(attrs={'data-testid':'paywall'}))
 return {'canonical_url':canon,'first_publication_value':published,'first_date_precision':precision,'updated_value':updated,'updated_precision':'observed_metadata' if updated else 'unknown','byline':x.get('author'),'genre':x.get('@type','unknown'),'publishing_role':'media','body_character_count':len(body) if body else None,'readability_status':'preview_only' if preview else ('body_structurally_present_boundary_pending' if body else 'no_body_in_structured_metadata'),'preview_status':'paywall_or_preview' if preview else 'not_established','quoted_speakers':'unassessed','author_geography':None,'reported_places':None,'content_version_time':None}

def assess_payload(data):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(data,'html.parser');text=soup.get_text(' ',strip=True)
 challenge=any(x in data.decode('utf-8',errors='replace').lower() for x in ['_incapsula_resource','_cf_chl','verify you are human','captcha'])
 return {'payload_state':'access_challenge' if challenge else ('visible_text_boundary_pending' if text else 'empty_HTML_unreadable'),'visible_text_characters':len(text),'article_body_claimed':False,'stop_source':challenge or not text,'note':'HTTP success alone never establishes readable catalogue/article content; do not execute challenge scripts or bypass.'}

def parse_frame(data,url,month,source):
 from bs4 import BeautifulSoup
 soup=BeautifulSoup(data,'html.parser');main=soup.find('main') or soup
 links={};navigation=[]
 for a in main.find_all('a',href=True):
  u=canonical(urljoin(url,a['href']))
  if urlsplit(u).hostname!=urlsplit(url).hostname:continue
  if '/article-index/' in u:
   navigation.append(u);continue # A dated index/day link is never an article parent.
  d=dated_url(u)
  if d and d[:7]==month:links[u]=d
 texts=main.get_text(' ',strip=True)
 retired='no longer being updated' in texts.lower()
 return {'candidates':[{'canonical_url':u,'source_date_candidate':d,'date_precision':'day_from_url_unverified','parent_id':native_parent(source,u)} for u,d in sorted(links.items())], 'observed_unique_links':len(links),'monthly_denominator':None,'enumeration_state':'route_retired' if retired else ('partial_visible_frame' if links else 'dynamic_or_empty_unverified'),'pagination_truncated':True,'scope_detail':'One visible official page only; no monthly completeness inferred','navigation_urls':sorted(set(navigation)),'retired_notice':retired}

def request(source,url,purpose,allowed_hosts):
 import requests
 plan=read(OUT/'ROUTE_PLAN.json')
 require(any(x['source_id']==source and x['url']==url and x['purpose']==purpose and set(x['allowed_hosts'])==allowed_hosts for x in plan['allowlisted_probes']),'Request is outside frozen exact route plan')
 require(urlsplit(url).scheme=='https' and urlsplit(url).hostname in allowed_hosts,'Unapproved route/host')
 require(not any(k.lower() in {'api-key','apikey','token','access_token'} for k,v in parse_qsl(urlsplit(url).query)),'Credential-bearing URLs forbidden in this pilot')
 reqid=sid(source,url,purpose);cp=OUT/'requests'/f'{reqid}.json'
 require(not cp.exists(),'Attempt exists: no automatic retry')
 state=read(STATE) if STATE.exists() else {'sources':{}}
 per=state['sources'].get(source,{})
 require(not per.get('halted'),'Source halted: no automatic restart')
 until=per.get('retry_not_before_utc');require(not until or datetime.now(timezone.utc)>=datetime.fromisoformat(until),'Source cooldown active')
 last=state.get('last_request_finished_utc') or state.get('last_request_started_utc')
 if last:
  delay=2-(datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()
  if delay>0:time.sleep(delay)
 maximum=read(SCOPE)['object_cap_bytes']
 # A busy government heavy-I/O lease must fail before a request or checkpoint.
 guard=lock();guard.__enter__()
 try:budget(maximum)
 except BaseException:
  guard.__exit__(None,None,None);raise
 meta={'request_id':reqid,'source_id':source,'purpose':purpose,'request_url':url,'requested_at_utc':now(),'http_status':None,'status':'attempt_in_progress','transport':'requests; no automatic redirects/retries','byte_count':0,'raw_path':None,'sha256':None}
 save(cp,meta);state['last_request_started_utc']=now();save(STATE,state)
 path=OUT/'raw'/f'{reqid}.html';part=path.with_suffix('.html.part');path.parent.mkdir(exist_ok=True)
 response=None
 try:
  if True: # The shared heavy-I/O lock remains held for this entire bounded request.
   response=requests.get(url,headers={'User-Agent':'FearTemperatureResearch/MediaRoutePilot (bounded public route metadata; no model training)','Accept':'text/html,application/json','Accept-Encoding':'identity'},stream=True,allow_redirects=False,timeout=(15,30))
   headers={k:v for k,v in response.headers.items() if k.lower() in {'date','content-type','content-length','content-encoding','retry-after','etag','last-modified'}}
   if response.headers.get('Location'):
    loc=urlsplit(urljoin(url,response.headers['Location']));headers['Location_without_query']=urlunsplit((loc.scheme,loc.hostname or '',loc.path,'',''))
   meta.update(http_status=response.status_code,final_url=response.url,response_headers=headers)
   retry=response.headers.get('Retry-After')
   if response.status_code in {401,403,429} or retry:
    per.update(halted=True,stop_reason=f'HTTP {response.status_code} or Retry-After')
    if retry or response.status_code==429:
     until=datetime.now(timezone.utc)+timedelta(hours=1)
     if retry:
      try:until=datetime.now(timezone.utc)+timedelta(seconds=int(retry)) if retry.isdigit() else parsedate_to_datetime(retry).astimezone(timezone.utc)
      except (ValueError,TypeError):per['retry_after_parse_pending']=retry
     per['retry_not_before_utc']=until.isoformat();meta['retry_not_before_utc']=until.isoformat()
    raise RuntimeError(per['stop_reason'])
   require(response.status_code==200,'HTTP '+str(response.status_code)+'; bounded route terminal')
   cl=response.headers.get('Content-Length')
   if cl is not None:require(cl.isdigit() and 0<int(cl)<=maximum,'Malformed/excess Content-Length')
   require(response.headers.get('Content-Encoding','identity').lower() in {'identity',''},'Encoded length unresolved')
   with part.open('xb') as f:
    for b in response.iter_content(65536):
     if not b:continue
     require(meta['byte_count']+len(b)<=maximum,'Object cap exceeded');budget(len(b));f.write(b);f.flush();meta['byte_count']+=len(b)
   require(meta['byte_count']>0 and (cl is None or meta['byte_count']==int(cl)),'Empty/truncated body')
   os.link(part,path);part.unlink();meta.update(status='saved_public_route_evidence',raw_path=str(path.relative_to(OUT)),sha256=sha(path))
   assessment=assess_payload(path.read_bytes())
   if assessment['stop_source']:per.update(halted=True,stop_reason=assessment['payload_state'])
 except Exception as exc:
  meta.update(status='failed',error=type(exc).__name__+(': '+str(exc)[:350] if isinstance(exc,RuntimeError) else ': transport or I/O failure; details omitted'))
  per.update(halted=True,stop_reason=meta['error'])
  if part.exists():meta.update(partial_path=str(part.relative_to(OUT)),partial_sha256=sha(part),byte_count=part.stat().st_size)
 finally:
  if response is not None:response.close()
  meta['finished_at_utc']=now();state['last_request_finished_utc']=meta['finished_at_utc'];state['sources'][source]=per;save(STATE,state);save(cp,meta)
  guard.__exit__(None,None,None)
 return meta

def setup_db():
 p=OUT/'media_pilot.sqlite';require(p.parent==OUT,'Only local pilot DB')
 if p.exists():p.unlink() # Rebuild only this small derived pilot from frozen/saved inputs.
 con=sqlite3.connect(p);con.executescript((OUT/'schema.sql').read_text());return con

def build_pilot():
 scope=read(SCOPE);policies=read(OUT/'SOURCE_ROUTE_POLICY.json');frames=[];slots=[];articles=[];requests=[]
 for s in scope['sources']:
  policy=policies[s['source_id']]
  for month in scope['probe_months']:
   frame={'frame_id':'frame:'+sid(s['source_id'],month),'source_id':s['source_id'],'region_layer':s['region_layer'],'publisher_country':s['publisher_country'],'edition_market':s['edition_market'],'month':month,'slots_allocated':5,'filled_slots':0,'monthly_denominator':None,'observed_unique_links':None,'enumeration_state':policy['frame_state'],'reason':policy['reason'],'date_filter_json':json.dumps({'month':month,'fixed_end':'2026-09-21'}),'type_filter_json':json.dumps({'editorial_article_types':'all; source-specific mapping pending','exclude':'reader comments/social posts/images'}),'topic_query':None,'scope_detail':'No topic query; source-specific date/type public route or access gate','pi':None,'source_rights_status':policy['rights_status'],'frame_evidence':policy['evidence_url']}
   # Consume only saved actual official frame probes; no fictitious record creation.
   checkpoint=OUT/'frames'/f"{s['source_id']}_{month}.json"
   if checkpoint.exists():
    result=read(checkpoint);frame.update({k:v for k,v in result.items() if k!='candidates'})
    chosen=result.get('candidates',[])[:5]
    for row in chosen:
     parent={**row,'source_id':s['source_id'],'region_layer':s['region_layer'],'edition_id':'edition:'+s['source_id'],'frame_id':frame['frame_id'],'month':month,'publishing_role':'media','genre':'unknown_pending_article_metadata','new_body_status':'not_requested_rights_or_route_gate','pi':None}
     articles.append(parent)
    frame['filled_slots']=len(chosen)
   elif s['source_id']=='irish_times' and month=='1995-07':
    frame.update(enumeration_state='digital_index_outside_displayed_year_range',reason='Official article-index starts with displayed year 1996; print issue may exist under licensed archive, which requires sign-in. Not a publication zero.')
   elif s['source_id']=='bbc' and month=='1995-07':
    frame.update(enumeration_state='not_applicable_to_1997_news_web_era',reason='News web service era starts 1997; earlier BBC broadcasting/print material is a different frame, not a news-article zero.')
   for n in range(1,6):
    eligible=[a for a in articles if a['frame_id']==frame['frame_id']]
    slots.append({'slot_id':'slot:'+sid(frame['frame_id'],n),'frame_id':frame['frame_id'],'source_id':s['source_id'],'region_layer':s['region_layer'],'month':month,'slot_index':n,'parent_id':eligible[n-1]['parent_id'] if len(eligible)>=n else None,'status':'filled_metadata_only' if len(eligible)>=n else 'unfilled_'+frame['enumeration_state'],'unfilled_reason':None if len(eligible)>=n else frame['reason'],'selection_design':'non_probability_route_pilot_first_five_stable_urls','pi':None,'planned_region_weight':0.2,'planned_source_within_region_weight':0.5,'observed_inventory_weight':1})
   frames.append(frame)
 for p in sorted((OUT/'requests').glob('*.json')) if (OUT/'requests').exists() else []:requests.append(read(p))
 csv_write(OUT/'FRAME_COVERAGE.csv',frames,list(frames[0]))
 csv_write(OUT/'PILOT_SLOTS.csv',slots,list(slots[0]))
 csv_write(OUT/'PILOT_MANIFEST.csv',articles,list(articles[0]) if articles else ['parent_id','source_id','region_layer','edition_id','canonical_url','source_date_candidate','date_precision','frame_id','month','publishing_role','genre','new_body_status','pi'])
 csv_write(OUT/'REQUEST_LEDGER.csv',requests,list(dict.fromkeys(k for r in requests for k in r)) if requests else ['request_id','source_id','request_url','status','http_status'])
 assessments=[]
 for r in requests:
  if r.get('raw_path'):
   x={'request_id':r['request_id'],'source_id':r['source_id'],**assess_payload((OUT/r['raw_path']).read_bytes())};assessments.append(x)
   if x['stop_source']:
    state=read(STATE) if STATE.exists() else {'sources':{}};state['sources'].setdefault(r['source_id'],{}).update(halted=True,stop_reason=x['payload_state'],derived_assessment_at_utc=now());save(STATE,state)
 save(OUT/'RESPONSE_ASSESSMENTS.json',assessments)
 con=setup_db()
 for s in scope['sources']:
  src=s['source_id'];policy=policies[src]
  con.execute('INSERT INTO publisher VALUES (?,?,?,?,?)',('publisher:'+src,s['publisher'],s['publisher_country'],policy['evidence_url'],'frozen_publisher_country_anchor; exact_HQ_and_historical_owner_pending; author location not inferred'))
  con.execute('INSERT INTO outlet VALUES (?,?,?,?,?,?)',(src,'publisher:'+src,s['outlet'],s['outlet_type'],'Distinct publisher/editorial source; syndicated stories retained separately',s['official_home']))
  con.execute('INSERT INTO edition VALUES (?,?,?,?,?,?,?)',('edition:'+src,src,s['region_layer'],s['edition_market'],policy['evidence_url'],'item_edition_unverified','Frozen publisher/editorial anchoring; UK disjoint from Europe'))
 for f in frames:
  src=f['source_id'];era='era:'+sid(src,f['month']);policy=policies[src]
  con.execute('INSERT INTO source_era (era_id,edition_id,month,medium,applicability,era_scope_note,route,rights_status,rights_evidence_url,access_status,access_entitlement,checked_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(era,'edition:'+src,f['month'],'web_index_or_licensed_print_route',f['enumeration_state'],f['reason'],policy['route'],policy['rights_status'],policy['evidence_url'],f['enumeration_state'],'No institution/account entitlement asserted',now()))
  con.execute('INSERT INTO frame VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f['frame_id'],era,src,f['month'],'article_publication_instance',f['date_filter_json'],f['type_filter_json'],None,f['enumeration_state'],None,f['observed_unique_links'],None,None,f['frame_evidence'],1,f.get('visited_pages',0),f['scope_detail'],f.get('retrieval_at_utc')))
 for a in articles:
  con.execute('INSERT OR IGNORE INTO article_parent VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(a['parent_id'],a['source_id'],a['edition_id'],canonical(a['canonical_url']),'canonical_native_URL_fallback',a['canonical_url'],'en_unverified',a['genre'],'media',None,'unknown',None,a['source_date_candidate'],a['source_date_candidate'],'URL date candidate only',None,None,None,'frame_link_only_original_identity_pending'))
  con.execute('INSERT OR IGNORE INTO frame_membership VALUES (?,?,?,?,?)',(a['frame_id'],a['parent_id'],a.get('index_url',''),1,'Saved official visible index link'))
 for x in slots:con.execute('INSERT INTO sample_slot VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(x['slot_id'],x['frame_id'],x['slot_index'],x['parent_id'],x['status'],x['unfilled_reason'],x['selection_design'],None,None,.2,.5,1))
 for obj in raw_account()['files']:
  r=next((r for r in requests if r.get('raw_path')==obj['path'] or r.get('partial_path')==obj['path']),{})
  con.execute('INSERT INTO raw_object VALUES (?,?,?,?,?,?,?,?,?,?,?)',('raw:'+sid(obj['path'],obj['sha256']),obj['path'],obj['sha256'],obj['bytes'],r.get('response_headers',{}).get('Content-Type'),'library_catalogue_or_route_HTML',int(obj['partial']),'catalogue_route_terms_unverified; not publisher article rights' if r.get('purpose')=='official_archive_catalogue_metadata' else policies[r['source_id']]['rights_status'] if r else 'unresolved','restricted_private_evidence; no open full-text redistribution',r.get('request_id'),r.get('finished_at_utc',now())))
 for r in requests:
  rawsha=r.get('sha256') or r.get('partial_sha256');rawpath=r.get('raw_path') or r.get('partial_path')
  con.execute('INSERT INTO request_attempt VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['request_id'],r['source_id'],r['purpose'],r['request_url'],r['requested_at_utc'],r['finished_at_utc'],r['http_status'],r['status'],r.get('final_url'),json.dumps(r.get('response_headers',{})),'raw:'+sid(rawpath,rawsha) if rawsha else None,r.get('error'),r.get('retry_not_before_utc'),r['transport']))
 legacy_path=OUT/'LEGACY_GUARDIAN_RECEIPTS.json'
 if legacy_path.exists():
  for x in read(legacy_path)['body_checks']:
   con.execute('INSERT INTO legacy_diagnostic VALUES (?,?,?,?,?,?,?,?,?,?,?)',(x['diagnostic_id'],'guardian',x['parent_url'],x['original_publication_value'],x.get('content_hash_receipt'),x['evidence_path'],x['evidence_sha256'],x['original_scope'],0,0,x['diagnostic_note']))
 con.commit();require(con.execute('PRAGMA foreign_key_check').fetchall()==[],'Pilot foreign-key failure');con.close()
 report={'recorded_at_utc':now(),'version':VERSION,'frame_cells':len(frames),'slots':len(slots),'filled_metadata_slots':sum(x['parent_id'] is not None for x in slots),'new_article_targets':len({a['parent_id'] for a in articles}),'new_full_bodies':0,'requests':len(requests),'access_challenge_payloads':sum(x['payload_state']=='access_challenge' for x in assessments),'raw_accounting':raw_account(),'monthly_complete_frames':0,'verified_monthly_zeroes':0,'pi_assigned':0,'government_DB_queries_or_writes':0,'actual_records_separate_from_fixtures':True}
 save(OUT/'PILOT_RUN.json',report);return report

def execute():
 scope=read(SCOPE);require(sha(OUT/'SOURCE_SELECTION_FROZEN.csv')==scope['source_selection_sha256'],'Frozen source selection changed')
 plan=read(OUT/'ROUTE_PLAN.json')
 for route in plan['allowlisted_probes']:
  src=route['source_id'];state=read(STATE) if STATE.exists() else {'sources':{}}
  if state['sources'].get(src,{}).get('halted'):continue
  if (OUT/'requests'/f"{sid(src,route['url'],route['purpose'])}.json").exists():continue
  result=request(src,route['url'],route['purpose'],set(route['allowed_hosts']))
  if result['status']!='saved_public_route_evidence':continue
  raw=OUT/result['raw_path']
  if route.get('month'):
   frame=parse_frame(raw.read_bytes(),route['url'],route['month'],src)
   frame.update(frame_evidence=result['raw_path'],retrieval_at_utc=result['finished_at_utc'],visited_pages=1,reason='Bounded visible index; monthly denominator unverified')
   save(OUT/'frames'/f"{src}_{route['month']}.json",frame)
  print(json.dumps({'source':src,'purpose':route['purpose'],'HTTP':result['http_status'],'status':result['status'],'bytes':result['byte_count']}),flush=True)
 return build_pilot()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
 print(json.dumps(execute() if args.execute else build_pilot(),ensure_ascii=False))
