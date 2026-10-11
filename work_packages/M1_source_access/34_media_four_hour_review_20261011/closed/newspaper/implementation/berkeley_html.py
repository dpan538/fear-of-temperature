"""Native Berkeley story IDs from dated full-text carriers, never arbitrary chunks."""
import json,re,datetime as dt
from urllib.parse import urlsplit,urljoin,urlunsplit
from bs4 import BeautifulSoup,Comment
import elt,broaden,production
from fear_temperature.media_planning.core import Opportunity
SID='berkeley_daily_planet';FILE='BERKELEY_NATIVE_FRONTIER.json'
def profile():return next((p for p in broaden.profiles() if p['source_id']==SID and broaden.approved(p)),None)
def publisher_host_permitted(host):
 if host=='www.berkeleydailyplanet.com':return True
 p=profile() or {};binding=p.get('verified_native_alias_binding',{})
 return host=='berkeleydailyplanet.com' and binding.get('status')=='confirmed_same_publisher_native_web_alias' and bool(binding.get('primary_evidence_receipts'))
def native_identity_url(url):
 u=urlsplit(url);assert publisher_host_permitted(u.hostname)
 return urlunsplit((u.scheme,'www.berkeleydailyplanet.com',u.path,'',''))
def native_key(url):return elt.sha((SID+'|article|'+elt.canon(native_identity_url(url))).encode())[:24]
def state():
 p=elt.OWN/FILE
 return json.loads(p.read_text()) if p.exists() else dict(stage='saved_carrier',carrier_receipt='cb46d1e7783160ce331859c7',carrier_url='https://www.berkeleydailyplanet.com/issue/2000-06-27/full_text',units={},seen_indexes=[])
def parse(data,carrier_url):
 soup=BeautifulSoup(data,'html.parser');units=[];seen=set();by_native={}
 for story in soup.select('#main #summary > div.story'):
  headings=story.select('div.has_copy > h2 > a[href]');copies=story.select('div.has_copy > .has_copy_copy.copy');datebox=story.select('div.has_copy > .auth_date_box')
  if len(headings)!=1 or len(copies)!=1 or len(datebox)!=1:continue
  original=urljoin(carrier_url,headings[0]['href']);u=urlsplit(original);match=re.fullmatch(r'/issue/(\d{4}-\d{2}-\d{2})/article/(\d+)',u.path)
  if not match or not publisher_host_permitted(u.hostname):continue
  canonical=urlunsplit((u.scheme,u.netloc,u.path,'',''));native_id=match[2]
  seen.add(native_id);title=headings[0].get_text(' ',strip=True)
  candidates=[n.get_text(' ',strip=True) for n in datebox[0].select(':scope > div:not(.auth_box)')];day=None;stamp=None
  if len(candidates)==1:
   stamp=candidates[0];m=re.fullmatch(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) ([A-Za-z]+) (\d{1,2}), (\d{4})(?: - .*)?',stamp)
   if m:
    try:
     value=dt.datetime.strptime(' '.join(m.groups()[1:]),'%B %d %Y').date()
     if value.strftime('%A')==m[1]:day=value.isoformat()
    except ValueError:pass
  node=copies[0]
  for n in node.find_all(string=lambda t:isinstance(t,Comment)):n.extract()
  for n in node.select('script,style,form,svg,nav,aside'):n.decompose()
  body=elt.renderer.normalise(elt.renderer.render(node));status='confirmed_complete'
  if not title or not body:status='pending_missing_native_headline_or_body'
  elif not day or not elt.eligible(day) or day!=match[1]:status='pending_native_article_date_mapping'
  elif title in ['Calendar of Events & Activities','Arts & Entertainment Calendar','Letters to the Editor'] or (title in ['News Briefs','Police Briefs'] and len(node.select('h3'))>1):status='pending_compiled_calendar_letters_or_notice_original_units'
  elif node.select('.paywall,.subscription-wall,.article-preview'):status='pending_visible_preview_or_paywall'
  genre=story.find_previous('h1');publisher_genre=genre.get_text(' ',strip=True) if genre else None
  author=datebox[0].select_one('.auth_box')
  unit=dict(native_article_id=native_id,article_id=SID+':article:'+native_id,source_url=canonical,original_permalink=original,title=title,publication_date=day,publisher_timestamp=stamp,author=author.get_text(' ',strip=True) if author else None,body=body,status=status,publisher_native_genre=publisher_genre,paragraph_count=len(node.select('p')),body_boundary='One native div.story > div.has_copy > div.has_copy_copy.copy linked by unique h2 article ID; entire copy order',native_permalink_day=match[1])
  if native_id not in by_native:units.append(unit);by_native[native_id]=unit
  else:
   original_unit=by_native[native_id];same=all(original_unit.get(k)==unit.get(k) for k in ['source_url','title','publication_date','publisher_timestamp','author','body'])
   original_unit['native_duplicate_carrier_occurrences']=original_unit.get('native_duplicate_carrier_occurrences',1)+1
   original_unit.setdefault('native_duplicate_carrier_evidence',[]).append(dict(native_article_id=native_id,publication_date=unit['publication_date'],title=unit['title'],body_sha256=elt.sha(unit['body'].encode()),same_ID_date_author_and_body=same,raw_occurrence_preserved=True))
   if not same:original_unit['status']='pending_conflicting_native_representations_in_carrier'

 return units,soup

def parse_single(data,url,mapping):
 soup=BeautifulSoup(data,'html.parser');parts={k:soup.select(mapping[k]) for k in ['headline_selector','body_selector','date_selector']}
 if any(len(v)!=1 for v in parts.values()):raise ValueError('Verified native single-article containers changed')
 u=urlsplit(url);m=re.fullmatch(r'/issue/(\d{4}-\d{2}-\d{2})/article/(\d+)',u.path);assert m and publisher_host_permitted(u.hostname)
 stamp=parts['date_selector'][0].get_text(' ',strip=True);day=None
 d=re.fullmatch(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) ([A-Za-z]+) (\d{1,2}), (\d{4})(?: - .*)?',stamp)
 if d:
  value=dt.datetime.strptime(' '.join(d.groups()[1:]),'%B %d %Y').date()
  if value.strftime('%A')==d[1]:day=value.isoformat()
 node=parts['body_selector'][0]
 for n in node.find_all(string=lambda t:isinstance(t,Comment)):n.extract()
 for n in node.select('script,style,form,svg,nav,aside'):n.decompose()
 title=parts['headline_selector'][0].get_text(' ',strip=True);body=elt.renderer.normalise(elt.renderer.render(node));status='confirmed_complete'
 if not title or not body:status='pending_missing_native_headline_or_body'
 elif day!=m[1] or not elt.eligible(day):status='pending_native_article_date_mapping'
 elif title in ['Calendar of Events & Activities','Arts & Entertainment Calendar','Letters to the Editor'] or (title in ['News Briefs','Police Briefs'] and len(node.select('h3'))>1):status='pending_compiled_calendar_letters_or_notice_original_units'
 elif node.select('.paywall,.subscription-wall,.article-preview'):status='pending_visible_preview_or_paywall'
 genre_nodes=soup.select('#main #content > .gutter > h1');publisher_genre=genre_nodes[0].get_text(' ',strip=True) if len(genre_nodes)==1 else None
 author=soup.select_one(mapping['author_selector']) if mapping.get('author_selector') else None
 canonical=urlunsplit((u.scheme,u.netloc,u.path,'',''))
 return [dict(native_article_id=m[2],article_id=SID+':article:'+m[2],source_url=canonical,original_permalink=url,title=title,publication_date=day,publisher_timestamp=stamp,author=author.get_text(' ',strip=True) if author else None,body=body,status=status,publisher_native_genre=publisher_genre,paragraph_count=len(node.select('p')),body_boundary=mapping['body_boundary_evidence'],native_permalink_day=m[1])],soup

def charge_saved_participant(st,key,rec,u):
 charged=st.setdefault('HTML_native_participant_charge_receipts',{}).setdefault(key,[])
 if rec['target_id'] in charged:return False
 hops=len(rec.get('hops',[]));prior=st.get('native_http_hops',{}).get(key,0)
 if prior+hops>elt.SCOPE['max_http_hops_per_target']:raise ValueError('Saved carrier participant would exceed inherited native HTTP hop ceiling')
 st.setdefault('native_http_hops',{})[key]=prior+hops
 if key not in st.setdefault('charged_native_targets',[]):st['charged_native_targets'].append(key)
 charged.append(rec['target_id'])
 st.setdefault('native_derived_from_public_HTML_carriers',{})[key]=dict(source_id=SID,native_article_id=u['native_article_id'],carrier_receipt=rec['target_id'],actual_new_article_HTTP=False,carrier_HTTP_hops=hops)
 return True

def policy(v):
 r=elt._receipt('d8f53f95722d9f5f5539a838');assert r['status']=='saved'
 v['robots_raw_reference']=r['raw_reference'];return v

CONTEXT_FIELDS=['stage','next_url','next_native_index','observed_native_article_targets','representation','carrier_receipt','carrier_url','frontier_basis']
def rotate_frontier(v):
 q=v.setdefault('frontier_queue',[])
 if not q:return v
 if v['stage'] in ['native_index','native_individual_body']:q.append({k:v.get(k) for k in CONTEXT_FIELDS})
 next_context=q.pop(0)
 for k in CONTEXT_FIELDS:v.pop(k,None)
 v.update(next_context)
 return v

def prepared_carriers():
 jobs={j['job_id']:j for j in json.loads((elt.OWN/'BROADEN_JOBS.json').read_text()) if j.get('eligible_native_seed_carrier') and j['source_id']==SID}
 completed=set(state().get('completed_carrier_receipts',[]));out=[]
 for row in map(json.loads,(elt.OWN/'SOURCE_PREPARATION_RESULTS.jsonl').read_text().splitlines()):
  if row['job_id'] not in jobs or row['status']!='saved':continue
  rec=elt._receipt(row['receipt_reference'].split('/')[-1].removesuffix('.json'))
  if rec['target_id'] not in completed:out.append(dict(job_id=row['job_id'],receipt=rec,carrier_url=jobs[row['job_id']]['url']))
 return out

def activate_saved(seed):
 v=state();assert v['stage']!='saved_carrier';rec=seed['receipt'];assert rec['source_id']==SID and rec['status']=='saved'
 if v['stage'] in ['native_index','native_individual_body']:v.setdefault('frontier_queue',[]).append({k:v.get(k) for k in CONTEXT_FIELDS})
 elt.append('BERKELEY_FRONTIER_CONTEXT_HISTORY.jsonl',dict(at_utc=elt.utc(),previous={k:v.get(k) for k in CONTEXT_FIELDS},activated_saved_carrier=rec['target_id'],raw_preserved=True,new_HTTP=False))
 v.update(stage='saved_carrier',representation=None,carrier_receipt=rec['target_id'],carrier_url=seed['carrier_url']);elt.save(FILE,v)

def options(aged):
 if not profile():return [],{}
 v=state();options=[];payload={}
 for seed in prepared_carriers():
  key='berkeley_carrier:'+seed['job_id'];options.append(Opportunity(key,'named_dated_historical_carrier',SID,seed['carrier_url'].split('/issue/')[1][:7],seed['carrier_url'].split('/issue/')[1][:7],'Actual saved primary fulltext carrier for named historical gap; native per-article identity/date/body required',wait_rounds=aged[key],need_priority=0));payload[key]=seed
 key='berkeley_native:body' if v['stage']=='saved_carrier' else 'berkeley_native:frontier'
 if v['stage'] in ['saved_carrier','native_index','native_individual_body'] and (v['stage']!='native_individual_body' or profile().get('single_article_mapping_verified')):
  options.append(Opportunity(key,'named_historical_newspaper',SID,'1999-04','2026-09','Verified original native article IDs/date/copy containers; public href or evidenced issue-parent frontier',wait_rounds=aged[key],need_priority=0));payload[key]=v
 return options,payload

def perform():
 p=profile();assert p;v=policy(state())
 if v['stage']=='saved_carrier':
  rec=elt._receipt(v['carrier_receipt']);parsed_carrier_url=v['carrier_url'];assert rec['status']=='saved' and rec['source_id']==SID
  raw=elt.read_payload(rec['raw_reference'])
  with elt.LOCK.open('a+b') as lock:
   elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);elt.preflight(len(raw)*24+8*1024*1024)
  if v.get('representation')=='individual_native_article':units,soup=parse_single(raw,v['carrier_url'],p['single_article_mapping'])
  else:units,soup=parse(raw,v['carrier_url'])
  assert elt.sha(raw)==rec['raw_sha256']
  # Every native participant returned in a carrier is charged once, including repeats whose body is already retained.
  st=elt.state();changed=False
  for unit in units:
   key=native_key(unit['source_url'])
   changed=charge_saved_participant(st,key,rec,unit) or changed
  if changed:elt.save('TRANSPORT_STATE.json',st)
  todo=[u for u in units if u['native_article_id'] not in v['units']]
  for u in todo[:25]:
   aid=u['article_id'];key=native_key(u['source_url'])
   st=elt.state()
   if charge_saved_participant(st,key,rec,u):elt.save('TRANSPORT_STATE.json',st)
   record=dict(article_id=aid,source_id=SID,source=p['title'],source_url=u['source_url'],raw_source_url=v['carrier_url'],url_aliases=[u['source_url'],u['original_permalink']],source_native_article_id=u['native_article_id'],native_identity_basis='Persistent publisher article ID in unique native story permalink; aliases and versions separate',title=u['title'],publication_date=u['publication_date'],date_field='Unique per-article displayed auth_date_box date, weekday validated against permalink day; carrier date never assigned',publisher_timestamp=u['publisher_timestamp'],observed_author=u['author'],publisher_native_genre=u.get('publisher_native_genre'),publisher_genre_basis='Original publisher section heading in saved native representation, not a semantic model label',stratum=p['stratum'],country=p['country'],edition=p['edition'],source_frame=p['source_frame'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],request_id=rec['target_id'],retrieved_at_utc=rec['finished_at_utc'],native_carrier_url=v['carrier_url'],native_article_permalink_day=u['native_permalink_day'],body_boundary=u['body_boundary'],article_boundary_evidence=(p['single_article_mapping']['body_boundary_evidence'] if v.get('representation')=='individual_native_article' else 'Full Text of All Articles page provides individual native story containers, IDs, complete copies and separate dates, including dated back stories; carrier is not one article'),paragraph_count=u['paragraph_count'],native_duplicate_carrier_occurrences=u.get('native_duplicate_carrier_occurrences',1),native_duplicate_carrier_evidence=u.get('native_duplicate_carrier_evidence',[]),provenance='direct original newspaper publisher historical web representation; embedded quotation/reprint origins separate',content_version_time=None,historical_body_equivalence='unknown; retrieved archive copy',retention_limit=p['retention_limit'],semantic_labels_executed=False,length_filter_used=False)
   if u['body']:
    bodyfile=elt.OWN/'bodies'/(aid.replace(':','_')+'_'+elt.sha(u['body'].encode())[:12]+'.txt')
    with elt.LOCK.open('a+b') as lock:
     elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);elt.preflight(len(u['body'].encode())*3+1048576);bodyfile.parent.mkdir(exist_ok=True);bodyfile.write_text(u['body'])
    record['body_reference']=str(bodyfile.relative_to(elt.REPO))
   result=elt.load(record,u['body'],u['status']);v['units'][u['native_article_id']]=dict(article_id=aid,status=result.get('load_status'),publication_date=u['publication_date'],body_sha256=result.get('body_sha256'),carrier_receipt=rec['target_id'])
   if result.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.update(elt.canon(x) for x in record['url_aliases'])
   elt.save(FILE,v)
  if all(u['native_article_id'] in v['units'] for u in units) and v.get('representation')=='individual_native_article':
   v.update(stage='native_individual_body',representation=None);rotate_frontier(v)
  elif all(u['native_article_id'] in v['units'] for u in units):
   if rec['target_id'] not in v.setdefault('completed_carrier_receipts',[]):v['completed_carrier_receipts'].append(rec['target_id'])
   dated=[u for u in units if u.get('publication_date')]
   older=min(dated,key=lambda u:u['publication_date']) if dated else None
   parent=older['source_url'].split('/article/')[0] if older else None
   previous=next((urljoin(v['carrier_url'],a['href']) for a in soup.select('a[href]') if a.get_text(' ',strip=True)=='Previous Issue'),None)
   route=parent if parent and parent not in v['seen_indexes'] else previous
   if route and broaden._permitted(v,route):v.update(stage='native_index',next_url=route,frontier_basis='Parent of observed dated article permalink; documented publisher issue route' if route==parent else 'Observed Previous Issue href')
   else:v.update(stage='observed_bounded_frontier_consumed',whole_archive_exhaustion=False)
   rotate_frontier(v)
  elt.append('BERKELEY_NATIVE_RESULTS.jsonl',dict(at_utc=elt.utc(),carrier_receipt=rec['target_id'],carrier_url=parsed_carrier_url,native_units_in_carrier=len(units),bounded_units_processed=min(25,len(todo)),stage=v['stage'],whole_archive_exhaustion=False,carrier_is_not_article=True));elt.save(FILE,v)
 elif v['stage']=='native_index':
  url=v['next_url']
  if not broaden._permitted(v,url):v.update(stage='blocked_declared_agent');elt.save(FILE,v);return
  rec=elt.fetch(url,SID,p['stratum'],'discovery',{'purpose':'Public historical issue parent derived from actual native article permalink / observed Previous Issue; no archive-search or PDF','frontier_basis':v.get('frontier_basis')})
  v['seen_indexes'].append(url)
  if rec['status']!='saved':v.update(stage='pending_transport',reason=rec['status'])
  else:
   soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');items=[];seen=set()
   for a in soup.select('#main a[href]'):
    u=urlsplit(urljoin(url,a['href']));m=re.fullmatch(r'/issue/(\d{4}-\d{2}-\d{2})/article/(\d+)',u.path)
    if m and publisher_host_permitted(u.hostname) and m[2] not in seen:
     seen.add(m[2]);items.append(dict(native_article_id=m[2],article_url=urlunsplit((u.scheme,u.netloc,u.path,'','')),original_permalink=urljoin(url,a['href']),native_permalink_day=m[1],index_receipt=rec['target_id']))
   older=[i for i in items if i['native_permalink_day']<url.rsplit('/',1)[-1]]
   parent=min(older,key=lambda i:i['native_permalink_day'])['article_url'].split('/article/')[0] if older else None
   prev=next((urljoin(url,a['href']) for a in soup.select('a[href]') if a.get_text(' ',strip=True)=='Previous Issue'),None)
   v.update(stage='native_individual_body',observed_native_article_targets=items,next_native_index=parent or prev,whole_archive_exhaustion=False,individual_body_mapping_required=True)
   rotate_frontier(v)
  elt.save(FILE,v)

 elif v['stage']=='native_individual_body':
  assert p.get('single_article_mapping_verified') and p.get('single_article_mapping_receipt')
  pending=[i for i in v.get('observed_native_article_targets',[]) if i['native_article_id'] not in v['units'] and elt.canon(i['article_url']) not in production.KNOWN]
  if not pending:
   route=v.get('next_native_index')
   if route and route not in v['seen_indexes'] and broaden._permitted(v,route):v.update(stage='native_index',next_url=route,frontier_basis='Observed older dated article permalink issue parent / actual Previous Issue href')
   else:v.update(stage='observed_bounded_frontier_consumed',whole_archive_exhaustion=False)
   rotate_frontier(v)
  else:
   item=pending[0];url=item['article_url']
   if not broaden._permitted(v,url):v.update(stage='blocked_declared_agent')
   else:
    rec=elt.fetch(url,SID,p['stratum'],'article',{'purpose':'Single publisher native article href from saved issue inventory, verified complete original container, per-article date/ID; no overlapping fulltext carrier, API, archive-search orPDF','index_receipt':item['index_receipt'],'source_retention_limit':p['retention_limit']},extra={'native_target_identity':native_identity_url(url)})
    if rec['status']=='saved':
     # Transport already charged this exact native participant; the saved parse must not charge it again.
     st=elt.state();key=native_key(url);st.setdefault('HTML_native_participant_charge_receipts',{}).setdefault(key,[]).append(rec['target_id']);elt.save('TRANSPORT_STATE.json',st)
     v.update(stage='saved_carrier',representation='individual_native_article',carrier_url=url,carrier_receipt=rec['target_id'])
    else:v['units'][item['native_article_id']]=dict(status='pending_native_article_'+rec['status'],carrier_receipt=rec['target_id'])
  elt.save(FILE,v)
