"""One-writer ELT hooks for named licensed nonforum native blog routes."""
import json,time,urllib.parse,urllib.robotparser
import transport as t,entities as e,native_web_adapter as wp,native_html_adapter as h,personal_blog_adapter as blogs
P=t.WORK/'new_source_preparation'
LOADED_CODE_SHA256=t.sha(__import__('pathlib').Path(__file__).read_bytes())

def prepare():
 by={r['name']:r for r in t.read_json(P/'METADATA_PROBES.json')['rows']}
 rows=[
  ('wp_mochilados','Mochilados','https://www.mochilados.es','self_hosted_WordPress','CC-BY-NC-SA-4.0','mochilados_permission','mochilados_robots','wp2',2,[('wp2','https://www.mochilados.es/wp-json/wp/v2/posts/29'),('wp2_collection','https://www.mochilados.es/wp-json/wp/v2/posts?per_page=10&order=asc&orderby=date')]),
  ('html_emergentkiwi','Emergent Kiwi / Steve Taylor','https://emergentkiwi.org.nz','self_hosted_author_HTML','CC-BY-NC-SA-1.0','emergentkiwi_march2004','emergentkiwi_robots','emergentkiwi',10,[('permalink','https://emergentkiwi.org.nz/archive/questions-that-need-answering/'),('index','https://emergentkiwi.org.nz/archive/2004/03/')]),
  ('neocities_elsewhere','Field Guides / giant robot tackler','https://elsewhere-elsewhere.neocities.org','Neocities','CC-BY-SA-4.0','elsewhere_archive_canonical',None,'elsewhere',2,[('permalink','https://elsewhere-elsewhere.neocities.org/posts/2023-11-26-1.-intro'),('index','https://elsewhere-elsewhere.neocities.org/archive')]),
  ('neocities_bulltown','Bulltown.neo / Joe Jenett','https://bulltown.neocities.org','Neocities','CC-BY-NC-SA-4.0','bulltown_archive','bulltown_robots','bulltown',2,[('index','https://bulltown.neocities.org/archive/')])]
 plans=[]
 for sid,title,base,platform,license_,permission_name,robots_name,kind,spacing,routes in rows:
  permission=by[permission_name];assert permission['status']=='saved'
  license_url={'CC-BY-NC-SA-4.0':'creativecommons.org/licenses/by-nc-sa/4.0/','CC-BY-NC-SA-1.0':'creativecommons.org/licenses/by-nc-sa/1.0/','CC-BY-SA-4.0':'creativecommons.org/licenses/by-sa/4.0/'}[license_]
  assert license_url in t.payload(permission).decode('utf8','replace')
  robots=by.get(robots_name);robottext=t.payload(robots).decode('utf8','replace') if robots and robots['status']=='saved' else ''
  assert not robots or robots['status']=='saved' or robots.get('http_status')==404
  rp=urllib.robotparser.RobotFileParser();rp.parse(robottext.splitlines())
  assert all(rp.can_fetch('FearOfTemperatureResearch',u) for _,u in routes)
  source={'source_id':sid,'title':title,'base_url':base,'platform':platform,'carrier':'personal_blog','genre':'personal_weblog','collection_retention':'permitted','retention_basis':'Current author-owned text licence; bounded noncommercial research snapshot. Source/post exceptions and third-party works excluded from blanket grant. Comments and media not acquired.','content_license':license_,'redistribution':'no full text/media public release in this task; actual author licence conditions retained','api_documentation':['https://developer.wordpress.org/rest-api/reference/posts/'] if kind=='wp2' else [base+'/','publisher-declared HTML permalink and archive routes; identity/date/body mapping in structural adapter'],'permission_raw_reference':permission['raw_reference'],'permission_url':permission['url'],'permission_retrieved_at':permission['retrieved_at'],'robots_raw_reference':(robots or {}).get('raw_reference'),'robots_text':robottext,'robots_observation_status':(robots or {}).get('status','404 observed by coordinator'),'minimum_spacing_seconds':spacing,'native_adapter_kind':kind,'source_instance_inception':'unresolved; earliest native date not unchanged historical body proof','stratum':'GLOBAL_UNKNOWN','author_country':'unknown'}
  cohort=sid+':native_site'
  actor={'cohort_id':cohort,'source_id':sid,'actor_id':None,'site_id':urllib.parse.urlsplit(base).hostname,'carrier':'personal_blog','genre':'personal_weblog','role_status':'named_personal_blog_self_presentation; native author mapping separately preserved','profile_raw_reference':permission['raw_reference'],'profile_receipt':'independent_metadata:'+permission_name,'observed_at':permission['retrieved_at'],'selection_rule':'named licensed personal blogs; source-published historical permalink/native post inventory, no topic or emotion query','parent_independence':'unresolved','source_context_country':'unknown','source_context_region':'unknown','source_context_evidence_ref':permission['raw_reference'],'source_context_observed_at':permission['retrieved_at'],'community_context_scope':'individual personal weblog, not a national population','author_country':'unknown','author_country_status':'unmeasured','author_country_evidence_type':'unmeasured; no domain/place/language inference','author_country_evidence_ref':permission['raw_reference'],'author_country_observed_at':permission['retrieved_at']}
  cursors=[{'source_id':sid,'actor_id':None,'site_id':actor['site_id'],'cohort_id':cohort,'carrier':'personal_blog','genre':'personal_weblog','adapter':'native_web','route_type':route,'url':u,'page':0,'native_page':1,'cursor':None,'max_id':None,'state':'active','new_core_bodies':0,'returned_native_rows':0,'oldest_publication':None} for route,u in routes]
  plans.append({'source':source,'actor':actor,'cursors':cursors})
 t.atomic(P/'NATIVE_WEB_CHANNEL_PREPARED.json',{'at_utc':t.utc(),'plans':plans,'corpus_Loads':0,'not_live_source_counts':True,'fixed_deadline_unchanged':True})
 return plans

def incorporate(cursors,actors):
 p=P/'NATIVE_WEB_CHANNEL_PREPARED.json'
 if not p.exists():return False
 changed=False;registry=t.read_json(t.WORK/'source_registry.json')
 for plan in t.read_json(p)['plans']:
  actor=plan['actor'];source=plan['source'];sid=source['source_id']
  if any(a['cohort_id']==actor['cohort_id'] for a in actors):continue
  loaded=plan.get('required_native_loaded_code_sha256')
  if loaded and loaded!={'native_web_adapter.py':wp.LOADED_CODE_SHA256,'native_html_adapter.py':h.LOADED_CODE_SHA256,'native_web_channel.py':LOADED_CODE_SHA256}:continue
  required=plan.get('required_native_adapter_code_sha256')
  if required and required!=t.sha((t.WORK/'native_html_adapter.py').read_bytes()):continue
  if required and t.read_json(t.WORK/'APPROVED_NATIVE_ADAPTER_REVISION.json',{}).get('code_sha256',{}).get('native_html_adapter.py')!=required:continue
  with t.shared(t.footprint()):
   c=e.db()
   if not c.execute('SELECT 1 FROM acquisition_sources WHERE source_id=?',(sid,)).fetchone():e.register(c,source,{'frame_id':actor['cohort_id'],'frame_type':'native_author_permalink_or_post_API_inventory','selection_rule':actor['selection_rule'],'actor_role_basis':actor['role_status']})
   c.close();registry.append(source);t.atomic(t.WORK/'source_registry.json',registry)
  actors.append(actor);cursors.extend(plan['cursors']);changed=True
 repairs=t.read_json(P/'NAMED_SAVED_RESPONSE_REPAIRS.json',{}).get('repairs',[])
 for repair in repairs:
  if repair['adapter_sha256']!=t.sha((t.WORK/'native_html_adapter.py').read_bytes()):continue
  for cursor in cursors:
   if cursor.get('source_id')!=repair['source_id'] or cursor.get('url')!=repair['url'] or cursor.get('state')!=repair['expected_state'] or cursor.get('last_request')!=repair['saved_request_id']:continue
   rec=t.read_json(t.WORK/'receipts'/(repair['saved_request_id']+'.json'))
   assert rec['status']=='saved' and rec['source_id']==repair['source_id'] and rec['url']==repair['url'] and rec['raw_sha256']==repair['raw_sha256']
   cursor.update(state='active',ready_at_utc=t.utc(),last_attempt_at_utc=None,named_saved_response_repair=repair['saved_request_id'])
   t.append(P/'NAMED_SAVED_RESPONSE_REPAIR_APPLIED.jsonl',{'at_utc':t.utc(),'source_id':repair['source_id'],'saved_request_id':repair['saved_request_id'],'counter_reset':False,'new_HTTP_required':False});changed=True
 return changed

def collect(cursor,actors,cursors):
 source=next(s for s in t.read_json(t.WORK/'source_registry.json') if s['source_id']==cursor['source_id']);actor=next(a for a in actors if a['cohort_id']==cursor['cohort_id']);url=cursor['url']
 rp=urllib.robotparser.RobotFileParser();rp.parse(source['robots_text'].splitlines())
 api_prefix=blogs.API+str(source.get('native_site_id',''))+'/posts/'
 documented_wpcom=source['native_adapter_kind']=='wpcom' and url.startswith(api_prefix) and source.get('api_documentation')==[blogs.DOC]
 if not documented_wpcom and (urllib.parse.urlsplit(url).hostname!=urllib.parse.urlsplit(source['base_url']).hostname or not rp.can_fetch('FearOfTemperatureResearch',url)):cursor['state']='source_robots_or_origin_not_admitted';return
 delay=source['minimum_spacing_seconds']-(time.time()-t.state()['hosts'].get(urllib.parse.urlsplit(url).hostname,0))
 if delay>0:time.sleep(delay)
 t.release();rec=t.fetch(url,source['source_id'],'source_metadata' if cursor['route_type']=='index' else 'content')
 if rec.get('http_status') in (301,302,307,308) and rec.get('location'):
  target=urllib.parse.urljoin(url,rec['location'])
  if target.startswith('https://') and urllib.parse.urlsplit(target).hostname==urllib.parse.urlsplit(source['base_url']).hostname and rp.can_fetch('FearOfTemperatureResearch',target):cursor.update(url=target,last_request=rec['request_id']);return
 if rec['status']!='saved':cursor.update(state='native_route_unavailable',last_request=rec['request_id']);return
 kind=source['native_adapter_kind'];rows=[]
 if kind=='wpcom':
  data=t.json_payload(rec);rows=blogs.records(data,cursor,actor,source)
  for row in rows:
   row['native_fields']['native_author_alias_to_named_owner']='pending; publisher-owned blog licence plus native site/author identity, not a verified legal-person equivalence'
   row['native_fields']['source_expansion_evidence']['genre']=source['genre']
   if row.get('author_id')!=source['licensed_native_author_id']:row.update(body_original='',content_state='native_guest_author_permission_mapping_unresolved')
   if t.clean(row.get('body_original',''))=='Welcome to WordPress.com. This is your first post. Edit or delete it and start blogging!':
    row.update(content_state='cms_default_template_not_authored',native_unit='cms_template_wrapper')
    row['flags']['literal_unmodified_CMS_welcome_scaffolding']=True
  nextpage=(data.get('meta') or {}).get('next_page');cursor['reported_found']=data.get('found')
  if nextpage:cursor['page_handle']=nextpage
  elif len(data.get('posts',[]))==cursor.get('number',20):cursor['native_page']+=1
  else:cursor['state']='returned_native_inventory_exhausted_at_observation'
  if cursor['state']=='active':
   args={'number':cursor.get('number',20),'order':'ASC','order_by':'date','status':'publish','type':'post'}
   if nextpage:args['page_handle']=nextpage
   else:args['page']=cursor['native_page']
   cursor['url']=api_prefix+'?'+urllib.parse.urlencode(args)
 elif kind=='wp2':
  data=t.json_payload(rec);rows=wp.wp2_records(data,source,actor)
  if cursor['route_type']=='wp2_collection':
   pages=(rec.get('headers') or {}).get('X-WP-TotalPages');cursor['reported_total_pages']=pages
   if pages and cursor['native_page']<int(pages):
    cursor['native_page']+=1;cursor['url']=source['base_url']+'/wp-json/wp/v2/posts?'+urllib.parse.urlencode({'per_page':10,'order':'asc','orderby':'date','page':cursor['native_page']})
   else:cursor['state']='returned_native_inventory_exhausted_at_observation' if pages else 'native_page_processed_total_pages_unresolved'
  else:cursor['state']='native_post_processed'
 else:
  raw=t.payload(rec).decode('utf8','replace')
  if cursor['route_type']!='index':rows=h.records(raw,url,source,actor,kind)
  for route in h.native_links(raw,url,kind):
   if not rp.can_fetch('FearOfTemperatureResearch',route['url']) or any(c.get('url')==route['url'] and c['source_id']==source['source_id'] for c in cursors):continue
   child=dict(cursor);child.update(**route,page=0,state='active',new_core_bodies=0,returned_native_rows=0,oldest_publication=None,ready_at_utc=t.utc(),last_attempt_at_utc=None,last_operation_end_at_utc=None);child.pop('scheduler_job_key',None);child.pop('last_request',None);cursors.append(child)
  cursor['state']='native_index_processed_not_archive_complete' if cursor['route_type']=='index' else 'native_permalink_processed' if rows else 'native_permalink_mapping_unresolved'
 if rows:
  result=e.load(rows,rec,cursor['cohort_id']);cursor['new_core_bodies']+=result['new_qualified_posts'];cursor['returned_native_rows']+=len(rows)
  dates=[r['native_created_at'] for r in rows if r.get('native_created_at')];cursor['oldest_publication']=min(dates+[cursor['oldest_publication']] if cursor.get('oldest_publication') else dates,default=None)
  if result['new_qualified_posts']:
   proof=t.WORK/('FIRST_'+source['source_id'].upper()+'_AUTHORED_BODY_LOAD.json')
   if not proof.exists():t.atomic(proof,{'at_utc':t.utc(),'load':result,'source_id':source['source_id'],'native_post_ids':[r['native_post_id'] for r in rows],'native_publication_times':dates,'permission_raw_reference':source['permission_raw_reference'],'actual_Load_not_inventory':True})
  if (t.WORK/'TELEMETRY_ERRORS.jsonl').exists():raise t.Stop('changed_body_evidence_observer_failure')
 cursor['page']+=1;cursor['last_request']=rec['request_id']
