"""Primary-source title/policy documents in the same serial newspaper ELT chain."""
import csv,json,re
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
import elt,broaden
from fear_temperature.media_planning.core import Opportunity
CANDIDATES=elt.REPO/'work_packages/M1_source_access/35_media_geography_and_source_expansion_20261011/NEWSPAPER_ROUTE_CANDIDATES.csv'
STATE='EXPANSION_ADMISSION_STATE.json'

def candidates():
 rows=list(csv.DictReader(CANDIDATES.open()))
 added=elt.OWN/'COORDINATOR_CANDIDATE_ADDITIONS.json'
 if added.exists():rows+=json.loads(added.read_text())
 result=[]
 for row in rows:
  sid=row.get('source_id') or re.sub('[^a-z0-9]+','_',row['candidate_title'].lower()).strip('_');parts=urlsplit(row['candidate_site']);root=parts.scheme+'://'+parts.netloc+'/'
  geo=row.get('proposed_stratum') or {'GB':'UK','IE':'EU/Europe excluding UK','DK':'EU/Europe excluding UK','PT':'EU/Europe excluding UK','MT':'EU/Europe excluding UK','NZ':'NZ','AU':'AU','US':'US'}[row['proposed_country']]
  assert geo in elt.SCOPE['strata'] and sid not in {r['source_id'] for r in result}
  result.append(dict(row,source_id=sid,root_url=root,stratum=geo))
 return result

def state():
 p=elt.OWN/STATE;return json.loads(p.read_text()) if p.exists() else {}

def options(aged):
 current=state();choices=[];payload={}
 for row in candidates():
  sid=row['source_id'];v=current.get(sid,{});stage=v.get('stage','robots')
  if stage in ['blocked','pending_owner_primary_review','admitted']:continue
  key='expand:'+sid
  choices.append(Opportunity(key,'source_preparation',sid,'1988-01','2026-09','Package35 named primary title/access documents; same serial ELT',wait_rounds=aged[key],need_priority=0 if row['identity_status']=='identity_primary_verified' else 2,action_kind='route_resolution'));payload[key]=row
 return choices,payload

def perform(row):
 current=state();sid=row['source_id'];v=current.setdefault(sid,dict(stage='robots',title=row['candidate_title'],country=row['proposed_country'],stratum=row['stratum'],root_url=row['root_url'],documents=[],primary_identity_status=row['identity_status']));stage=v['stage']
 try:
  if stage=='robots':
   probe={'job_id':'sixhour:'+sid+':robots','source_id':sid,'stratum':row['stratum'],'url':row['root_url']+'robots.txt'}
   allowed,policy=broaden.metadata_permission(probe)
   if not allowed:v.update(stage='blocked',reason=policy)
   else:
    rec=elt.fetch(probe['url'],sid,row['stratum'],'discovery',{'purpose':'Source policy for package35 named conventional title; no corpus/body requests yet'})
    v['robots_request_id']=rec['target_id']
    if rec['status']=='saved' or ((rec.get('hops') or [{}])[-1].get('status')==404):v['stage']='identity_doc'
    else:v.update(stage='blocked',reason=rec['status'])
  else:
   if stage=='identity_doc':url=row.get('primary_evidence_url') or row['candidate_site']
   elif stage=='root':url=row['root_url']
   elif stage=='policies':
    todo=[u for u in v.get('policy_urls',[]) if u not in [d['url'] for d in v['documents']] and u not in v.get('metadata_attempted_policy_urls',[])]
    if not todo:v['stage']='pending_owner_primary_review';elt.save(STATE,current);return 1
    url=todo[0]
   else:return 0
   allowed,policy=broaden.metadata_permission(dict(job_id='sixhour:'+sid+':'+stage,source_id=sid,stratum=row['stratum'],url=url))
   if not allowed:v.update(stage='blocked',reason=policy)
   else:
    rec=elt.fetch(url,sid,row['stratum'],'discovery',{'purpose':'Exact primary title/edition and source-use admission','candidate_title':row['candidate_title'],'no_body_SQL_Load_or_candidate_count_inflation':True})
    if rec['status']!='saved':
     if stage=='policies' and (rec.get('hops') or [{}])[-1].get('status')==404:
      v.setdefault('metadata_attempted_policy_urls',[]).append(url);v.setdefault('metadata_access_limits',[]).append(dict(url=url,status=404,request_id=rec['target_id'],no_host_access_denial=True));v['stage']='policies'
     else:v.update(stage='blocked',reason=rec['status'],url=url)
    else:
     soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');links=[]
     for a in soup.select('a[href]'):
      label=a.get_text(' ',strip=True);u=urljoin(rec.get('final_url',url),a['href'])
      if urlsplit(u).hostname==urlsplit(row['root_url']).hostname and re.fullmatch(r'(?:about(?: us)?|privacy(?: policy|, policies and cookies)?|terms(?: and conditions| of use| of service)?|copyright(?: notice)?|cookies(?: policy)?)',label.strip(),re.I) and not re.search('comment|login|account|subscribe',u,re.I):links.append(u)
     for n in soup.select('script,style,nav,form,svg'):n.decompose()
     text=soup.get_text(' ',strip=True)
     v['documents'].append(dict(url=url,request_id=rec['target_id'],raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],observed_at_utc=rec['finished_at_utc'],text_excerpt=text[:14000],explicit_automation_candidates=re.findall(r'.{0,120}(?:automated|scrap(?:e|ing)|database|robot|text and data mining).{0,180}',text,re.I)))
     if stage=='identity_doc':v['stage']='root'
     elif stage=='root':
      v['policy_urls']=list(dict.fromkeys(links));v['stage']='policies' if links else 'pending_owner_primary_review';v['root_request_id']=rec['target_id']
     elif stage=='policies':
      if not [u for u in v['policy_urls'] if u not in [d['url'] for d in v['documents']] and u not in v.get('metadata_attempted_policy_urls',[])]:v['stage']='pending_owner_primary_review'
 except ValueError as error:
  if not str(error).startswith('preserved_'):raise
  v.update(stage='blocked',reason=str(error))
 elt.save(STATE,current);return 1

def admit_reviewed():
 p=elt.OWN/'EXPANSION_OWNER_REVIEWS.json'
 if not p.exists():return 0
 current=state();profiles=broaden.profiles();existing={x['source_id'] for x in profiles};changed=0
 for review in json.loads(p.read_text()):
  sid=review['source_id'];v=current.get(sid)
  if v is None:continue
  if sid in existing or v['stage']=='admitted':continue
  if review['decision']!='admit':v.update(stage='blocked',owner_review=review);continue
  assert v['stage']=='pending_owner_primary_review'
  assert review['classification_verified'] and review['source_use_gate_passed'] and review['title_classification_reference'] and review['retention_limit']
  assert set(review['document_request_ids_reviewed'])=={d['request_id'] for d in v['documents']}
  profile=dict(review,title=v['title'],country={'GB':'UK'}.get(v['country'],v['country']),stratum=v['stratum'],root_url=v['root_url'],edition='One primary-evidenced conventional title publisher web edition; historical owner relations unresolved',source_frame='general_local_newspaper_publisher_web',source_purpose_category='conventional_local_newspaper',source_access_reference='; '.join([v['root_url']+'robots.txt']+[d['url'] for d in v['documents']]),public_API_documentation_reference='https://developer.wordpress.org/rest-api/using-the-rest-api/discovery/',selectors=review.get('selectors',['.entry-content','.td-post-content']),approval_reference='EXPANSION_OWNER_REVIEWS.json',public_HTML_visibility_required=review.get('public_HTML_visibility_required',True),historical_scope=review.get('historical_scope','Source publication foundation and recoverable web era are separate. Actual eligible dates determine observed inventory; current versions do not establish historical equivalence.'))
  profiles.append(profile);existing.add(sid);v.update(stage='admitted',reviewed_at_utc=elt.utc(),not_contributing_until_complete_Load=True);changed+=1
 elt.save('BROADEN_PROFILES.json',profiles);elt.save(STATE,current);broaden.active_ids();return changed

def prime_primary_documents():
 """Resolve explicitly named primary identities once, then return to production."""
 import run
 for row in candidates():
  if row['identity_status']!='identity_primary_verified':continue
  while True:
   v=state().get(row['source_id'],{});stage=v.get('stage','robots')
   if stage in ['blocked','pending_owner_primary_review','admitted']:break
   elt.assert_release();run.next_action=dict(opportunity='primary_document:'+row['source_id']+':'+stage,source_id=row['source_id'],kind='route_resolution')
   elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=run.rounds,**run.next_action,need_priority=0,need='NEWSPAPER_TASK six primary-identified title routes; in-line admission, no sample or count completion gate'))
   before_documents=len(v.get('documents',[]));before_attempts=len(v.get('metadata_attempted_policy_urls',[]));perform(row);run.rounds+=1
   after=state().get(row['source_id'],{})
   if after.get('stage')==stage and len(after.get('documents',[]))==before_documents and len(after.get('metadata_attempted_policy_urls',[]))==before_attempts:break

def prime_newly_admitted():
 """Newly reviewed title enters the same native cursor and whole-body Load chain."""
 import run,production,native_batches,extract_load
 ledger_path=elt.OWN/'NEW_TITLE_CHAIN_ENTRY_STATE.json';ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
 for profile in profiles_for_entry():
  sid=profile['source_id']
  if ledger.get(sid,{}).get('entry_processed'):continue
  broaden.active_ids();geo=profile['stratum'];before=broaden._state().get(sid,{}).get('stage','robots')
  # Each step uses the existing advertised source adapter; no endpoint guessed.
  if before not in ['blocked','exhausted','observed_public_frontier_consumed']:
   run.next_action=dict(opportunity='new_title_chain:'+sid+':'+before,source_id=sid,kind='route_resolution');elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=run.rounds,**run.next_action,need_priority=0,new_title_chain_entry=True));broaden.discover(sid,production.queue);run.rounds+=1
  current=broaden._state().get(sid,{}).get('stage')
  items=production.eligible(production.targets(sid),production.KNOWN,set(elt.state()['targets']),{},geo,'historical_native')
  if items:
   run.next_action=dict(opportunity='new_title_chain:'+sid+':body',source_id=sid,kind='acquisition');elt.append('SCHEDULER_ACTIONS.jsonl',dict(at_utc=elt.utc(),round=run.rounds,**run.next_action,need_priority=0,new_title_chain_entry=True))
   batch=native_batches.acquire(sid,items,production.KNOWN)
   if batch is None:
    r=extract_load.acquire(items[0])
    if r and r.get('load_status') in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(r['source_url']))
   run.rounds+=1;ledger[sid]=dict(entry_processed=True,at_utc=elt.utc(),source_actual_complete_Loads=elt._new_totals.get('confirmed_complete',0),entry_is_not_archive_or_emotion_success_gate=True)
  elif current in ['blocked','exhausted','observed_public_frontier_consumed']:ledger[sid]=dict(entry_processed=True,at_utc=elt.utc(),state=current,no_complete_source_claim=True)
  else:ledger[sid]=dict(entry_processed=False,at_utc=elt.utc(),state=current)
  elt.save('NEW_TITLE_CHAIN_ENTRY_STATE.json',ledger)
  return 1
 return 0

def profiles_for_entry():
 return [p for p in broaden.profiles() if p.get('approval_reference')=='EXPANSION_OWNER_REVIEWS.json' and broaden.approved(p)]


def perform_chain(row):
 """One finite primary admission chain; actual HTTP/save operations stay guarded."""
 sid=row['source_id'];before=state().get(sid,{});initial_ids={d['request_id'] for d in before.get('documents',[])};steps=0
 while True:
  v=state().get(sid,{});stage=v.get('stage','robots')
  if stage in ['blocked','pending_owner_primary_review','admitted']:break
  stamp=(stage,len(v.get('documents',[])),len(v.get('metadata_attempted_policy_urls',[])))
  elt.assert_release();perform(row);steps+=1;after=state().get(sid,{})
  if stamp==(after.get('stage','robots'),len(after.get('documents',[])),len(after.get('metadata_attempted_policy_urls',[]))):break
 current=state().get(sid,{})
 elt.append('SOURCE_PREPARATION_CHAIN_LOG.jsonl',dict(at_utc=elt.utc(),source_id=sid,initial_stage=before.get('stage','robots'),final_stage=current.get('stage'),document_steps=steps,new_document_request_ids=[d['request_id'] for d in current.get('documents',[]) if d['request_id'] not in initial_ids],one_finite_named_primary_route_chain=True,no_source_country_or_policy_inferred_from_candidate_name=True,no_corpus_body_requests_or_SQL_Loads=True,actual_operation_capacity_and_source_rules_retained=True))
 return steps
