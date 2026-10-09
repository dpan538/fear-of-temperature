"""Serial evidenced newspaper-frame opportunities; no guessed/private APIs."""
import json,re,urllib.robotparser
from urllib.parse import urlsplit,urljoin,urlencode,parse_qs,urlunsplit
from bs4 import BeautifulSoup
import elt,extract_load

def profiles():
 p=elt.OWN/'BROADEN_PROFILES.json'
 return json.loads(p.read_text()) if p.exists() else []

def approved(p):
 return bool(p.get('classification_verified') and p.get('source_use_gate_passed') and p.get('title_classification_reference') and p.get('source_access_reference') and p.get('retention_limit') and p.get('stratum') in elt.SCOPE['strata'])

def active_ids(geo=None):
 active=[];families={g:set() for g in elt.SCOPE['strata']}
 for p in profiles():
  if not approved(p) or (geo and p['stratum']!=geo):continue
  sid=p['source_id'];geo_key=p['stratum'];family=p.get('parent_family_id',sid)
  inherited=elt.SCOPE.get('inherited_additional_parent_families',{}).get(geo_key,0)
  if family not in families[geo_key] and inherited+len(families[geo_key])>=elt.SCOPE['max_additional_acquisition_parents_per_stratum']:continue
  families[geo_key].add(family)
  extract_load.ADAPTERS[sid]=dict(title=p['title'],country=p['country'],stratum=p['stratum'],edition=p['edition'],frame=p['source_frame'],selectors=p.get('selectors',['.entry-content']),exclude=['script','style','form','svg','.sharedaddy','.related-posts','.author-bio'])
  active.append(sid)
 return active

def _state():
 p=elt.OWN/'BROADEN_CURSORS.json';return json.loads(p.read_text()) if p.exists() else {}

def _save(o):elt.save('BROADEN_CURSORS.json',o)

def _update_frontier(p,v):
 f=elt.OWN/'SOURCE_FRONTIER_STATE.json';o=json.loads(f.read_text()) if f.exists() else {'sources':[]}
 by={r['source_id']:r for r in o['sources']};by[p['source_id']]=dict(source_id=p['source_id'],title=p['title'],stratum=p['stratum'],country=p['country'],edition=p['edition'],source_frame=p['source_frame'],title_classification_reference=p['title_classification_reference'],source_access_reference=p['source_access_reference'],retention_limit=p['retention_limit'],interface=v)
 o.update(at_utc=elt.utc(),sources=list(by.values()));elt.save('SOURCE_FRONTIER_STATE.json',o)

def _fetch(p,url,evidence):
 if elt.effective_count(elt.state(),p['stratum'],'discovery')>=elt.SCOPE['discovery_distinct_targets_per_stratum']:return {'status':'inherited_discovery_ceiling'}
 return elt.fetch(url,p['source_id'],p['stratum'],'discovery',evidence)

def _policy(p,v):
 origin=urlunsplit((*urlsplit(p['root_url'])[:2],'','',''));url=origin+'/robots.txt'
 rec=_fetch(p,url,{'purpose':'New evidenced newspaper native-interface robots; source-specific use limits retained'})
 v['robots_receipt']=rec.get('target_id')
 if rec['status']=='saved':
  robot=urllib.robotparser.RobotFileParser();robot.parse(elt.read_payload(rec['raw_reference']).decode('utf-8',errors='replace').splitlines());v['robots_raw_reference']=rec['raw_reference'];v['robots_allows_root']=robot.can_fetch('FearOfTemperatureResearch/1.0',p['root_url'])
 elif rec.get('hops') and rec['hops'][-1].get('status')==404:v['robots_missing_404']=True;v['robots_allows_root']=True
 else:v['blocked_reason']='Robots unavailable/stopped; no publisher body attempted';v['stage']='blocked';return
 if not v['robots_allows_root']:v['stage']='blocked';v['blocked_reason']='Declared research-agent ordinary root route disallowed'
 else:v['stage']='native_root'

def advertised_api(soup,rec,p):
 node=soup.select_one('link[rel="https://api.w.org/"][href]')
 link=(rec.get('hops') or [{}])[-1].get('link') or ''
 match=re.search(r'<([^>]+)>;\s*rel="https://api\.w\.org/"',link)
 api=urljoin(p['root_url'],node['href']) if node else (match[1] if match else None)
 allowed=[urlsplit(p['root_url']).hostname]+p.get('verified_publisher_alias_hosts',[])
 return api if api and urlsplit(api).scheme=='https' and urlsplit(api).hostname in allowed else None

def _permitted(v,url):
 if v.get('robots_raw_reference'):
  robot=urllib.robotparser.RobotFileParser();robot.parse(elt.read_payload(v['robots_raw_reference']).decode('utf-8',errors='replace').splitlines());return robot.can_fetch('FearOfTemperatureResearch/1.0',url)
 return bool(v.get('robots_missing_404'))

def discover(sid,queue):
 p=next((p for p in profiles() if p['source_id']==sid and approved(p)),None)
 if not p:return 0
 active_ids();o=_state();v=o.setdefault(sid,{'stage':'robots','attempted_pages':0,'queued_native_post_IDs':[]});stage=v['stage']
 if stage in ['blocked','exhausted']:return 0
 try:
  if stage=='robots':_policy(p,v)
  elif stage=='native_root':
   rec=_fetch(p,p['root_url'],{'classification_reference':p['title_classification_reference'],'source_specific_retention_limit':p['retention_limit']})
   if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Native publisher root '+rec['status'])
   else:
    soup=BeautifulSoup(elt.read_payload(rec['raw_reference']),'html.parser');api=advertised_api(soup,rec,p)
    if not api:v.update(stage='blocked',blocked_reason='No advertised documented WordPress public API; no private endpoint guessed',native_root_receipt=rec['target_id'])
    elif not _permitted(v,api):v.update(stage='blocked',blocked_reason='Advertised API route disallowed to declared agent')
    else:v.update(stage='API_schema',api_root=api,native_root_receipt=rec['target_id'])
  elif stage=='API_schema':
   if not p.get('public_API_documentation_reference'):v.update(stage='blocked',blocked_reason='Documented public interface proof missing')
   else:
    rec=_fetch(p,v['api_root'],{'advertised_in_receipt':v['native_root_receipt'],'documentation':p['public_API_documentation_reference']})
    if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Advertised API schema '+rec['status'])
    else:
     api=json.loads(elt.read_payload(rec['raw_reference']));route=api.get('routes',{}).get('/wp/v2/posts',{});links=route.get('_links',{}).get('self',[]);collection=next((x['href'] for x in links if x.get('href')),None)
     if not collection or urlsplit(collection).scheme!='https' or urlsplit(collection).hostname!=urlsplit(v['api_root']).hostname:v.update(stage='blocked',blocked_reason='Source API did not expose same-publisher documented public posts collection')
     else:
      query=urlencode({'after':'1987-12-31T23:59:59','before':'2026-09-22T00:00:00','orderby':'date','order':'asc','per_page':50,'_fields':'id,date,modified,link,title,_links,status,type,categories'})
      url=collection+(' & ' if '?' in collection else '?')+query
      url=url.replace(' & ','&')
      if not _permitted(v,url):v.update(stage='blocked',blocked_reason='Documented collection query disallowed to declared agent')
      else:v.update(stage='metadata_pages',next_url=url,collection_url=collection,schema_receipt=rec['target_id'],documentation=p['public_API_documentation_reference'])
  elif stage=='metadata_pages':
   url=v['next_url'];rec=_fetch(p,url,{'source_verified_collection':v['collection_url'],'documentation':p['public_API_documentation_reference'],'metadata_only_fields':True,'fixed_publication_interval':elt.SCOPE['publication_interval']})
   if rec['status']!='saved':v.update(stage='blocked',blocked_reason='Native metadata page '+rec['status'])
   else:
    posts=json.loads(elt.read_payload(rec['raw_reference']));assert isinstance(posts,list);items=[];known=set(v['queued_native_post_IDs'])
    for post in posts:
     day=(post.get('date') or '')[:10];pid=post.get('id');article=post.get('link');links=post.get('_links',{}).get('self',[]);self_url=next((x['href'] for x in links if x.get('href')),None)
     if not (pid and article and self_url and elt.eligible(day)) or pid in known:continue
     if urlsplit(self_url).scheme!='https' or urlsplit(self_url).hostname!=urlsplit(v['api_root']).hostname:continue
     if urlsplit(article).hostname not in [urlsplit(p['root_url']).hostname]+p.get('verified_publisher_alias_hosts',[]):continue
     if not _permitted(v,self_url):continue
     items.append(dict(source_id=sid,url=self_url,article_url=article,native_post_id=pid,representation='publisher_wp_article_json',month=day[:7],native_evidence=dict(title=BeautifulSoup(post.get('title',{}).get('rendered',''),'html.parser').get_text(' ',strip=True),native_date=post.get('date'),native_modified=post.get('modified'),native_category_IDs=post.get('categories'),native_list_receipt={'target_id':rec['target_id'],'raw_reference':rec['raw_reference']},publisher_API_documentation=p['public_API_documentation_reference'],source_classification=p['title_classification_reference'],source_specific_retention_limit=p['retention_limit'])))
     known.add(pid)
    queue(sid,items);v['queued_native_post_IDs']=sorted(known);v['attempted_pages']+=1;headers=rec.get('hops',[{}])[-1];link=headers.get('link') or '';n=re.search(r'<([^>]+)>;\s*rel="next"',link);v['observed_native_total_posts']=headers.get('x_wp_total');v['observed_native_total_pages']=headers.get('x_wp_totalpages')
    if n and _permitted(v,n[1]):v['next_url']=n[1]
    else:v.update(stage='exhausted',next_url=None,reason='Observed native pagination ended; queued eligible surplus remains retained')
  else:raise ValueError('Unknown approved native-interface stage '+stage)
 except ValueError as e:
  if str(e).startswith('preserved_'):v.update(stage='blocked',blocked_reason=str(e))
  else:v.update(stage='blocked',blocked_reason='Named source interface/schema defect '+repr(e))
 _save(o);_update_frontier(p,v);return 1

def perform(geo,queue):
 jobs_path=elt.OWN/'BROADEN_JOBS.json';jobs=json.loads(jobs_path.read_text()) if jobs_path.exists() else [];done_path=elt.OWN/'BROADEN_JOBS_DONE.json';done=set(json.loads(done_path.read_text())) if done_path.exists() else set()
 for job in jobs:
  if job['stratum']!=geo or job['job_id'] in done:continue
  if job['kind']!='metadata_doc':raise ValueError('Only named public source metadata documents are accepted')
  rec=elt.fetch(job['url'],job['source_id'],geo,'discovery',job['evidence']);elt.append('SOURCE_PREPARATION_RESULTS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'source_id':job['source_id'],'url':job['url'],'receipt_reference':'receipts/'+rec['target_id']+'.json','status':rec['status'],'body_or_database_Load':False})
  done.add(job['job_id']);elt.save('BROADEN_JOBS_DONE.json',sorted(done));return 1
 for sid in active_ids(geo):
  if discover(sid,queue):return 1
 return 0
