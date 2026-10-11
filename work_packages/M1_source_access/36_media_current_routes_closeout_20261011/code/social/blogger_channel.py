"""Bounded whole-post Blogger ELT route, using source-declared sitemaps."""
import json,urllib.parse,urllib.robotparser,xml.etree.ElementTree as ET
import transport as t,entities as e,blogger_adapter as b

def prepare():
 P=t.WORK/'new_source_preparation';rows=t.read_json(P/'METADATA_PROBES.json')['rows'];by={r['name']:r for r in rows}
 plans=[]
 for sid,host,stem,license,needle,author in [
  ('blogger_gardenfancy','gardenfancy.blogspot.com','gardenfancy','CC-BY-4.0','creativecommons.org/licenses/by/4.0/','12283184170369157189'),
  ('blogger_canativegarden','canativegarden.blogspot.com','canativegarden','CC-BY-NC-ND-3.0','creativecommons.org/licenses/by-nc-nd/3.0/',None)]:
  permission=by[stem+'_permission'];robots=by[stem+'_robots'];assert permission['status']==robots['status']=='saved'
  text=t.payload(permission).decode('utf8');assert needle in text
  robottext=t.payload(robots).decode('utf8');rp=urllib.robotparser.RobotFileParser();rp.parse(robottext.splitlines())
  base='https://'+host;sitemaps=rp.site_maps() or [];assert sitemaps and rp.can_fetch('FearOfTemperatureResearch',base+'/')
  source={'source_id':sid,'title':'Garden Fancy' if stem=='gardenfancy' else 'CA Native Garden','base_url':base,'platform':'Blogger_author_published_HTML','frame':'personal_weblog_native_posts','collection_retention':'permitted','retention_scope':'bounded noncommercial local research snapshot; source-own material; quotes/guest/comments separately unresolved','content_license':license,'redistribution':'not part of this task; no full text/media public release','api_documentation':['https://support.google.com/blogger/answer/97933?hl=en'],'permission_raw_reference':permission['raw_reference'],'permission_retrieved_at':permission['retrieved_at'],'robots_raw_reference':robots['raw_reference'],'robots_text':robottext,'inferred_author_country':False,'source_instance_inception':'unresolved; native post timestamp not proof of unchanged historical publication/body'}
  cohort=sid+':native_site'
  actor={'cohort_id':cohort,'source_id':sid,'site_id':host,'actor_id':author,'carrier':'personal_blog','genre':'personal_weblog','role_status':'individual_self_presentation' if author else 'source_owner_personal_self_presentation; post-author identity pending','profile_receipt':'independent_metadata:'+stem+'_permission','profile_raw_reference':permission['raw_reference'],'observed_at':permission['retrieved_at'],'selection_rule':'named licensed personal-blog leads; complete native post permalinks from publisher-declared sitemap, no topic/emotion query','parent_independence':'unresolved','source_context_country':'global','source_context_region':'global','source_context_evidence_ref':permission['raw_reference'],'source_context_observed_at':permission['retrieved_at'],'community_context_scope':'individual personal weblog; not forum or national population','author_country':'unknown','author_country_status':'unmeasured','author_country_evidence_type':'unmeasured; no provider/domain/language inference','author_country_evidence_ref':permission['raw_reference'],'author_country_observed_at':permission['retrieved_at']}
  routes=[('permalink',base+'/')]+[('sitemap',u) for u in sitemaps if urllib.parse.urlsplit(u).hostname==host and rp.can_fetch('FearOfTemperatureResearch',u)]
  cursors=[{'source_id':sid,'actor_id':author,'site_id':host,'cohort_id':cohort,'carrier':'personal_blog','genre':'personal_weblog','adapter':'blogger_html','route_type':kind,'url':u,'page':0,'cursor':None,'max_id':None,'state':'active','new_core_bodies':0,'returned_native_rows':0,'oldest_publication':None} for kind,u in routes]
  plans.append({'source':source,'actor':actor,'cursors':cursors})
 t.atomic(P/'BLOGGER_CHANNEL_PREPARED.json',{'at_utc':t.utc(),'plans':plans,'corpus_Loads':0,'adapters_prepared_not_live_source_counts':True,'original_deadline_unchanged':True,'healthy_writer_not_paused':True})
 return plans

def incorporate(cursors,actors):
 if (t.WORK/'new_source_preparation/BLOGGER_PROVIDER_STOP.json').exists():return False
 p=t.WORK/'new_source_preparation/BLOGGER_CHANNEL_PREPARED.json'
 if not p.exists():return False
 changed=False;registry=t.read_json(t.WORK/'source_registry.json')
 for plan in t.read_json(p)['plans']:
  source=plan['source'];actor=plan['actor'];sid=source['source_id']
  if any(a['cohort_id']==actor['cohort_id'] for a in actors):continue
  # Only new source/frame rows; existing accepted rows are untouched.
  with t.shared(t.footprint()):
   c=e.db()
   if not c.execute('SELECT 1 FROM acquisition_sources WHERE source_id=?',(sid,)).fetchone():e.register(c,source,{'frame_id':actor['cohort_id'],'frame_type':'publisher_declared_sitemap_native_permalink','selection_rule':actor['selection_rule'],'actor_role_basis':actor['role_status']})
   c.close();registry.append(source);t.atomic(t.WORK/'source_registry.json',registry)
  actors.append(actor);cursors.extend(plan['cursors']);changed=True
 return changed

def collect(cursor,actors,cursors):
 sid=cursor['source_id'];source=next(s for s in t.read_json(t.WORK/'source_registry.json') if s['source_id']==sid)
 rp=urllib.robotparser.RobotFileParser();rp.parse(source['robots_text'].splitlines());url=cursor['url']
 if urllib.parse.urlsplit(url).hostname!=urllib.parse.urlsplit(source['base_url']).hostname or not rp.can_fetch('FearOfTemperatureResearch',url):cursor['state']='source_robots_or_origin_not_admitted';return
 rec=t.fetch(url,sid,'source_metadata' if cursor['route_type']=='sitemap' else 'content')
 if rec['status']!='saved':cursor['state']='native_route_unavailable';cursor['last_request']=rec['request_id'];return
 raw=t.payload(rec)
 if cursor['route_type']=='sitemap':
  root=ET.fromstring(raw);kind=root.tag.rsplit('}',1)[-1]
  locs=[x.text for x in root.iter() if x.tag.rsplit('}',1)[-1]=='loc' and x.text]
  for u in locs:
   p=urllib.parse.urlsplit(u)
   if p.hostname!=urllib.parse.urlsplit(source['base_url']).hostname or not rp.can_fetch('FearOfTemperatureResearch',u):continue
   if any(c.get('url')==u and c['source_id']==sid for c in cursors):continue
   if p.scheme=='http':u=urllib.parse.urlunsplit(('https',p.netloc,p.path,p.query,''))
   child=dict(cursor);child.update(url=u,route_type='sitemap' if kind=='sitemapindex' else 'permalink',page=0,state='active',new_core_bodies=0,returned_native_rows=0,oldest_publication=None,ready_at_utc=t.utc(),last_attempt_at_utc=None,last_operation_end_at_utc=None);child.pop('scheduler_job_key',None);child.pop('last_request',None)
   cursors.append(child)
  cursor['state']='native_sitemap_return_processed_not_archive_complete';cursor['discovered_permalink_or_sitemap_units']=len(locs)
 else:
  actor=next(a for a in actors if a['cohort_id']==cursor['cohort_id'])
  rows=b.permalink_records(raw.decode('utf8','replace'),source,actor,url)
  for u in b.native_links(raw.decode('utf8','replace'),source['base_url']):
   if any(c.get('url')==u and c['source_id']==sid for c in cursors) or not rp.can_fetch('FearOfTemperatureResearch',u):continue
   child=dict(cursor);child.update(url=u,route_type='permalink',page=0,state='active',new_core_bodies=0,returned_native_rows=0,oldest_publication=None,ready_at_utc=t.utc(),last_attempt_at_utc=None,last_operation_end_at_utc=None);child.pop('scheduler_job_key',None);child.pop('last_request',None);cursors.append(child)
  if rows:
   result=e.load(rows,rec,cursor['cohort_id']);cursor['new_core_bodies']+=result['new_qualified_posts'];cursor['returned_native_rows']+=len(rows)
   dates=[r['native_created_at'] for r in rows if r.get('native_created_at')];cursor['oldest_publication']=min(dates,default=None)
   if result['new_qualified_posts'] and not (t.WORK/'FIRST_BLOGGER_AUTHORED_BODY_LOAD.json').exists():t.atomic(t.WORK/'FIRST_BLOGGER_AUTHORED_BODY_LOAD.json',{'at_utc':t.utc(),'load':result,'native_post_ids':[r['native_post_id'] for r in rows],'native_publication_times':dates,'permission_raw_reference':source['permission_raw_reference'],'actual_Load_not_inventory':True})
   if (t.WORK/'TELEMETRY_ERRORS.jsonl').exists():raise t.Stop('changed_body_evidence_observer_failure')
  cursor['state']='native_permalink_processed' if rows else 'native_permalink_identity_body_mapping_unresolved'
 cursor['page']+=1;cursor['last_request']=rec['request_id']
