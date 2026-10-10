"""Continuous native-frontier scheduler within one fixed release. No topic gates."""
import datetime as dt,json,time,os,sys,urllib.parse,hashlib,re
from pathlib import Path
import transport as t,entities as e
FRONT=t.WORK/'FRONTIERS.json'
FILTER='!)cN)B)B5rJi5kvLl5pKw5R)4jh321X0GAFsQZtqCWdBvL'

def query(base,params):return base+'?'+urllib.parse.urlencode(params,doseq=True)
def checkpoint(fronts=None,phase='acquiring',stop_reason=None):
 scope=t.read_json(t.SCOPE_PATH);fronts=fronts if fronts is not None else t.read_json(FRONT,[])
 st=t.state();active=[f for f in fronts if f['status']=='active'];nextf=select_frontier(active) if active else None
 now=dt.datetime.now(dt.timezone.utc);elapsed=(now-dt.datetime.fromisoformat(scope['earliest_network_and_load_start_at_utc'])).total_seconds()
 progress={'at_utc':t.utc(),'owner_thread_id':t.OWNER,'pid':os.getpid(),'phase':phase,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'elapsed_seconds':elapsed,'charged_requests':st['requests'],'distinct_returned_native_objects':len(st['returned_object_ids']),'round_requests':st['requests']-t.read_json(t.WORK/'INHERITED_BASELINE.json')['lifetime_charged_requests'],'new_entities':st.get('new_entities',0),'new_core_bodies':st.get('new_core_bodies',0),'new_entity_versions':st.get('new_entity_versions',0),'first_successful_http_at_utc':st.get('first_successful_http_at_utc'),'last_successful_http_at_utc':st.get('last_successful_http_at_utc'),'first_successful_load_at_utc':st.get('first_successful_load_at_utc'),'last_successful_load_at_utc':st.get('last_successful_load_at_utc'),'active_frontiers':len(active),'blocked_frontiers':sum('stop' in f['status'] or 'error' in f['status'] for f in fronts),'exhausted_frontiers':sum('exhausted' in f['status'] for f in fronts),'next_action':{k:nextf.get(k) for k in ['source','kind','frame','year','page','before','max_id','native_next_url','cursor','next_id']} if nextf else 'proportionate documented inventory replenishment','actual_capacity':t.read_json(t.WORK/'LAST_CAPACITY.json',None),'stop_reason':stop_reason,'routes':[{k:f.get(k) for k in ['source','frame','kind','status','oldest_returned_publication_at','new_core_bodies','year_deltas','before','max_id','cursor','native_next_url','stop']} for f in fronts if f['status']=='active' or f.get('historical_route')],'source_year_deltas':st.get('source_year_deltas',{})}
 t.atomic(t.WORK/'PROGRESS.json',progress)
 t.append(t.WORK/'PROGRESS_HISTORY.jsonl',{k:progress[k] for k in ['at_utc','phase','charged_requests','round_requests','distinct_returned_native_objects','new_core_bodies','active_frontiers','stop_reason']})
 for hour in [1,2,3]:
  path=t.WORK/f'HOUR_{hour}_CHECKPOINT.json'
  if elapsed>=hour*3600 and not path.exists():t.atomic(path,progress)
 digest=f"# Social broader historical continuation\n\nOwner {t.OWNER}; PID {os.getpid()}; phase {phase}. Fixed deadline {scope['hard_deadline_at_utc']} / {scope.get('hard_deadline_AEST')}. Scope {scope['version']}.\n\nEntry collect.py, compact state STATE.json and recursive predecessor metadata references; RETURNED_KEYS.jsonl journals only new keys. All old raw, frozen exports, identities and stops remain unchanged. Existing stream store and lifetime mutex only.\n\nLifetime {st['requests']} requests / {len(st['returned_object_ids'])} returned keys. Round {progress['round_requests']} requests, {st.get('new_core_bodies',0)} new core bodies / {st.get('new_entities',0)} entities. Last HTTP {st.get('last_successful_http_at_utc')}; last Load {st.get('last_successful_load_at_utc')}. Active routes {len(active)}. Next {progress['next_action']}.\n\nSource-year deltas and oldest returned publication dates: PROGRESS.json. Evidence ledger BUG_REPAIR_LEDGER.md; bound code START_RECEIPT.json; inventory/cursor receipts INVENTORY_PROGRESS.jsonl. {stop_reason or 'Acquisition running; native backoff and current process are distinct from chat idle.'}\n\n30 GB shared / 15 GB social cumulative, 15 GiB physical floor / 48 MiB recovery and real operation headroom remain live checked. Climate/affect/fear unexecuted. No target histogram, coverage2 completion, parent-score controls, Git/control/shared-log edits or rolling extension.\n"
 (t.WORK/'CONTINUATION_DIGEST.md').write_text(digest)

def select_frontier(runnable):
 source_age=t.state().get('source_last_action',{})
 source=min({x['source'] for x in runnable},key=lambda sid:source_age.get(sid,0))
 choices=[x for x in runnable if x['source']==source]
 historical=[x for x in choices if x.get('historical_route')]
 return min(historical or choices,key=lambda x:x.get('last_attempt_epoch',0))

def initial():
 f=[]
 for sid,start in [('se_sustainability',2013),('se_earthscience',2014)]:
  f.append({'source':sid,'kind':'se_questions','year':start,'page':1,'start_year':start,'context_queue':[],'status':'active','frame':sid+':all_creation_order_native_index'})
 f.append({'source':'python_discourse','kind':'discourse','base':'https://discuss.python.org','license':'CC BY-NC-SA 3.0','before':None,'topics':[],'seen_topics':[],'chunks':[],'status':'active','frame':'python_discourse:public_latest_posts_and_whole_topic_streams'})
 # Inherit exact first-wave minimum native cursors using compact manifests only.
 import csv
 minima={}
 with (t.ROOT/'summaries/native_posts_manifest.csv').open() as g:
  for x in csv.DictReader(g):
   sid=x['source_id']
   if sid.startswith('mastodon_'):minima[sid]=min(minima.get(sid,int(x['native_post_id'])),int(x['native_post_id']))
 registry={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')}
 for sid in ['mastodon_ie','mastodon_uk','mastodon_au','mastodon_us']:
  f.append({'source':sid,'kind':'mastodon','base':registry[sid]['base_url'],'max_id':str(minima[sid]),'status':'active','frame':sid+':local_public_creation_cursor'})
 return f

def frame_definition(f):return {'frame_id':f['frame'],'frame_type':f['kind'],'selection_rule':'All native index returns with genuine source paging; no semantic/affect/length exclusion. Source and era limits explicit. '+json.dumps({k:f.get(k) for k in ['actor','list_uri','base','year','max_id'] if f.get(k)}),'existence_lower_bound':None}

def job(f):
 sid=f['source'];k=f['kind']
 if k=='mail_archive_html':
  if f.get('rolling_native_pages'):return (f['message_queue'][0],'mail_archive_message') if f['message_queue'] else (f['native_next_url'],'mail_archive_index')
  return (f['native_next_url'],'mail_archive_index') if not f.get('index_drained') else (f['message_queue'][0],'mail_archive_message')
 if k=='thesession':return (f['topics'][0],'thesession_topic') if f['topics'] else (query('https://thesession.org/discussions/new',{'format':'json','perpage':50,'page':f['page']}),'thesession_index')
 if k=='ilxor_html':return f['topics'][0],'ilxor_topic'
 if k=='tildes_html':
  return (f['topics'][0],'tildes_topic') if f['topics'] else (f['native_next_url'],'tildes_index')
 if k=='mbox_archive':return f['archive_queue'][0],'mbox_archive'
 if k=='w3_archive':return (f['message_queue'][0],'w3_message') if f['message_queue'] else (f['period_queue'][0],'w3_period_index')
 if k=='hackernews':return 'https://hacker-news.firebaseio.com/v0/item/'+str(f['next_id'])+'.json','hackernews'
 if k=='se_questions':
  if f['context_queue']:
   q=f['context_queue'][0];return query('https://api.stackexchange.com/2.3/questions/'+q['ids']+'/'+q['type'],{'site':sid[3:],'order':'asc','sort':'creation','pagesize':100,'page':q['page'],'filter':FILTER}),'se_context'
  y=f['year'];from_=f.get('partition_from') or int(dt.datetime(y,1,1,tzinfo=dt.timezone.utc).timestamp());to=int(dt.datetime(y+1,1,1,tzinfo=dt.timezone.utc).timestamp())-1
  to=min(to,int(dt.datetime(2026,9,22,tzinfo=dt.timezone.utc).timestamp())-1)
  return query('https://api.stackexchange.com/2.3/questions',{'site':sid[3:],'fromdate':from_,'todate':to,'sort':'creation','order':'asc','pagesize':100,'page':f['page'],'filter':FILTER}),'se_questions'
 if k in ('discourse','discourse_archive'):
  if f['chunks']:
   q=f['chunks'][0];return query(f['base']+'/t/'+str(q['topic'])+'/posts.json',{'post_ids[]':q['ids']}),'discourse_chunk'
  if f['topics']:return f['base']+'/t/'+str(f['topics'][0])+'.json','discourse_topic'
  if k=='discourse_archive':return f.get('native_next_url') or query(f['base']+'/latest.json',{'order':'created','ascending':'true','per_page':50}),'discourse_archive_index'
  return f['base']+'/posts.json'+('' if f['before'] is None else '?before='+str(f['before'])),'discourse_index'
 if k=='mastodon':return query(f['base']+'/api/v1/timelines/public',{'local':'true','limit':40,'max_id':f['max_id']}),'mastodon'
 if k in ('lemmy_posts','lemmy_comments'):
  params={'type_':'Local','sort':'Old','limit':50,'page':f.get('page',1)}
  if k=='lemmy_comments' and f.get('parent_queue'):params['post_id']=f['parent_queue'][0]
  if k=='lemmy_posts' and f.get('cursor'):params.pop('page');params['page_cursor']=f['cursor']
  return query(f['base']+'/api/v3/'+('post/list' if k=='lemmy_posts' else 'comment/list'),params),k
 if k=='bluesky':
  p={'actor':f['actor'],'limit':100,'filter':'posts_with_replies','includePins':'false'}
  if f.get('cursor'):p['cursor']=f['cursor']
  return query('https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed',p),'bluesky'
 raise t.Stop('unknown_frontier_kind')

def advance(f,data,route):
 if route.startswith('thesession_'):
  if route=='thesession_index':
   f['topics'] += [x for x in data['topic_urls'] if x not in f['seen_topics'] and x not in f['topics']]
   f['seed_index_loaded']=True;f['page']=data['page']-1
   if f['page']<1:f['index_exhausted']=True
  else:
   previous=f['topics'].pop(0);f['seen_topics'].append(previous)
   if previous==f.get('seed_response_url'):f['seed_loaded']=True
   next_page=data.get('native_next_comment_page_url')
   if next_page and next_page not in f['seen_topics'] and next_page not in f['topics']:f['topics'].insert(0,next_page)
  if f.get('index_exhausted') and not f['topics']:f['status']='source_returned_native_creation_inventory_drained'
  return
 if route=='ilxor_topic':
  previous=f['topics'].pop(0);f['seen_topics'].append(previous)
  if previous==f.get('seed_response_url'):f['seed_loaded']=True
  showall=data.get('source_showall_url')
  if showall and showall not in f['seen_topics'] and showall not in f['topics']:f['topics'].insert(0,showall)
  if not f['topics']:f['status']='source_returned_native_thread_inventory_drained'
  return
 if route.startswith('mail_archive_'):
  if f.get('rolling_native_pages'):
   if route=='mail_archive_index':
    known=set(f['seen_messages'])|set(f['message_queue']);f['message_queue'] += [x for x in data['native_message_urls'] if x not in known]
    previous=f['native_next_url'];f['native_next_url']=data['native_next_url']
    if f['native_next_url']==previous:f['native_next_url']=None;f['index_end_reason']='nonadvancing_native_pagination_url'
   else:f['seen_messages'].append(f['message_queue'].pop(0))
   if not f['native_next_url'] and not f['message_queue']:f['status']='native_observed_archive_inventory_drained'
   return
  if route=='mail_archive_index':
   known=set(f['message_queue']);f['message_queue'] += [x for x in data['native_message_urls'] if x not in known]
   previous=f['native_next_url'];f['native_next_url']=data['native_next_url']
   if not f['native_next_url'] or f['native_next_url']==previous:
    f['index_drained']=True;f['message_queue'].reverse()
  else:f['seen_messages'].append(f['message_queue'].pop(0))
  if f.get('index_drained') and not f['message_queue']:f['status']='native_observed_archive_inventory_drained'
  return
 if route.startswith('tildes_'):
  if route=='tildes_topic':
   f['seen_topics'].append(f['topics'].pop(0))
  else:
   f['topics'] += [x for x in data['topic_urls'] if x not in f['seen_topics'] and x not in f['topics']]
   previous=f['native_next_url'];f['native_next_url']=data['native_next_url']
   if not f['native_next_url'] or f['native_next_url']==previous:f['index_exhausted']=True
  if f.get('index_exhausted') and not f['topics']:f['status']='native_html_inventory_exhausted_or_nonadvancing'
  return
 if route=='mbox_archive':
  f['archive_queue'].pop(0)
  if not f['archive_queue']:f['status']='native_observed_downloadable_archives_drained'
  return
 if route=='w3_period_index':
  f['period_queue'].pop(0);f['message_queue']=data['native_message_urls']
  if not f['period_queue'] and not f['message_queue']:f['status']='native_observed_archive_periods_drained'
  return
 if route=='w3_message':
  f['message_queue'].pop(0)
  if not f['period_queue'] and not f['message_queue']:f['status']='native_observed_archive_periods_drained'
  return
 if route=='hackernews':
  f['next_id']+=1
  if f['next_id']>f['max_observed_id']:f['status']='native_maxitem_snapshot_reached'
  return
 if route in ('lemmy_posts','lemmy_comments'):
  items=data.get('posts' if route=='lemmy_posts' else 'comments',[])
  if route=='lemmy_comments' and f.get('parent_queue'):
   fingerprint=t.sha(json.dumps([x.get('comment',{}).get('id') for x in items]).encode())
   limit_reason='native_parent_context_empty_end' if not items else 'provider_parent_page_100_bound' if f.get('page',1)>=100 else 'native_parent_context_nonadvancing' if fingerprint==f.get('last_batch_fingerprint') else None
   if limit_reason:
    parent=f['parent_queue'].pop(0)
    t.append(t.WORK/'PARENT_CONTEXT_ROUTE_LIMITS.jsonl',{'at_utc':t.utc(),'source_id':f['source'],'parent_native_post_id':parent,'page':f.get('page',1),'reason':limit_reason,'project_count_gate':False})
    f['page']=1;f.pop('last_batch_fingerprint',None)
    if not f['parent_queue']:f['status']='native_parent_context_catalog_drained'
   else:f['last_batch_fingerprint']=fingerprint;f['page']=f.get('page',1)+1
   return
  if not items:f['status']='native_local_index_exhausted';return
  fingerprint=t.sha(json.dumps([x.get('post' if route=='lemmy_posts' else 'comment',{}).get('id') for x in items]).encode())
  if fingerprint==f.get('last_batch_fingerprint'):f['status']='nonadvancing_native_cursor';return
  f['last_batch_fingerprint']=fingerprint;f['page']=f.get('page',1)+1
  if route=='lemmy_posts' and data.get('next_page'):f['cursor']=data['next_page']
 elif route.startswith('se_'):
  if route=='se_context':
   if data.get('has_more'):f['context_queue'][0]['page']+=1
   else:f['context_queue'].pop(0)
   if f.get('questions_exhausted') and not f['context_queue']:f['status']='native_frontier_exhausted'
  else:
   ids=[str(x['question_id']) for x in data.get('items',[])]
   # Native child returns are part of the same continuing ELT, never split into fake posts.
   if ids:
    for typ in ['answers','comments']:f['context_queue'].append({'ids':';'.join(ids),'type':typ,'page':1})
   if data.get('has_more'):
    f['page']+=1
    if f['page']>25:
     items=data.get('items',[]);boundary=max(x['creation_date'] for x in items) if items else None
     if boundary is None or boundary<=f.get('partition_from',0):f['status']='nonadvancing_provider_date_partition';f['limit_evidence']='25 anonymous pages; timestamp partition could not advance'
     else:f['partition_from']=boundary;f['page']=1;f['limit_evidence']='25 anonymous pages; continuing inclusive native-date partition preserves ties and IDs'
   else:
    f['year']+=1;f['page']=1;f.pop('partition_from',None)
    if f['year']>2026:
     f['questions_exhausted']=True
     if not f['context_queue']:f['status']='native_frontier_exhausted'
 elif route.startswith('discourse'):
  if route=='discourse_archive_index':
   listing=data.get('topic_list',{});topics=listing.get('topics',[]);seen=set(f['seen_topics']);f['topics'] += [x['id'] for x in topics if x['id'] not in seen and x['id'] not in f['topics']]
   nxt=listing.get('more_topics_url');previous=f.get('native_next_url')
   if nxt:
    nxt=urllib.parse.urljoin(f['base'],nxt);parts=urllib.parse.urlsplit(nxt)
    if parts.hostname!=urllib.parse.urlsplit(f['base']).hostname or parts.scheme!='https':raise t.Stop('native_pagination_cross_host_or_protocol')
    if not parts.path.endswith('.json'):nxt=urllib.parse.urlunsplit((parts.scheme,parts.netloc,parts.path+'.json',parts.query,parts.fragment))
    if nxt==previous:f['index_exhausted']=True;f['index_end_reason']='nonadvancing_native_topic_index'
    else:f['native_next_url']=nxt
   else:f['index_exhausted']=True;f['index_end_reason']='native_no_more_topics_url'
   if f.get('index_exhausted') and not f['topics']:f['status']='native_index_exhausted'
   return
  if route=='discourse_index':
   p=data.get('latest_posts',[])
   if not p:f['status']='native_index_exhausted';return
   nxt=min(x['id'] for x in p)
   if f.get('before') is not None and nxt>=f['before']:f['status']='nonadvancing_native_cursor';return
   f['before']=nxt;seen=set(f['seen_topics']);f['topics'] += [tid for tid in dict.fromkeys(x['topic_id'] for x in p) if tid not in seen and tid not in f['topics']]
  elif route=='discourse_topic':
   tid=f['topics'].pop(0);f['seen_topics'].append(tid);stream=data.get('post_stream',{});returned={x['id'] for x in stream.get('posts',[])};missing=[x for x in stream.get('stream',[]) if x not in returned]
   f['chunks'] += [{'topic':tid,'ids':missing[i:i+20]} for i in range(0,len(missing),20)]
  elif route=='discourse_single_remaining':
   f['chunks'][0]['ids'].pop(0)
   if not f['chunks'][0]['ids']:f['chunks'].pop(0)
  else:f['chunks'].pop(0)
  if f.get('index_exhausted') and not f['topics'] and not f['chunks']:f['status']='native_index_exhausted'
 elif route=='mastodon':
  if not data:f['status']='native_public_timeline_exhausted';return
  nxt=min(int(x['id']) for x in data)
  if nxt>=int(f['max_id']):f['status']='nonadvancing_native_cursor'
  else:f['max_id']=str(nxt)
 elif route=='bluesky':
  if not data.get('cursor') or data.get('cursor')==f.get('cursor'):f['status']='native_author_feed_exhausted'
  else:f['cursor']=data['cursor']

def object_bound(f):
 k=f['kind']
 if k=='bluesky':return 300
 if k=='mastodon':return 80
 if k=='lemmy_posts':return 50
 if k=='lemmy_comments':return 100
 if k=='se_questions':return 100
 if k in ('discourse','discourse_archive'):
  if f['chunks']:return len(f['chunks'][0]['ids'])
  return 21 if f['topics'] else 50
 return 300

def requests_import(f):
 p=t.WORK/'FRONTIER_ADDITIONS.json'
 additions=t.read_json(p,[])
 known={x['frame'] for x in f}
 for x in additions:
  if x['frame'] not in known:f.append(x);known.add(x['frame'])
 return f

def probes():
 tasks=t.read_json(t.WORK/'PROBE_TASKS.json',[]);done=t.read_json(t.WORK/'PROBE_RESULTS.json',{})
 for x in tasks:
  if x['name'] in done or x.get('not_before_epoch',0)>time.time():continue
  try:rec=t.fetch(x['url'],x['source'],x.get('purpose','documentation'),cap=x.get('raw_cap_bytes'));done[x['name']]={k:rec.get(k) for k in ['request_id','status','raw_reference','http_status','location','error']}
  except t.Stop as exc:
   if str(exc).startswith('server_backoff_until'):
    x['not_before_epoch']=float(str(exc).rsplit(' ',1)[1]);t.atomic(t.WORK/'PROBE_TASKS.json',tasks);return False
   done[x['name']]={'status':'stop','reason':str(exc)}
  t.atomic(t.WORK/'PROBE_RESULTS.json',done);return True
 return False

def replenish(fronts):
 """Continue documented native graph inventory after the initial actor prefix."""
 graph=t.read_json(t.WORK/'GRAPH_FRONTIER.json',{'cursor':'3mxfwcn42uc2p','status':'active','predecessor_request_id':'95432ca8fc941d45d3a9f5ac','frame':'bluesky:present_official_followers_graph'})
 if graph['status']!='active':return False
 if any(f['status']=='active' for f in fronts):return False
 url=query('https://public.api.bsky.app/xrpc/app.bsky.graph.getFollowers',{'actor':'bsky.app','limit':100,'cursor':graph['cursor']})
 try:
  rec=t.fetch(url,'bluesky','source_metadata')
  if rec['status']!='saved':graph['status']='preserved_graph_source_stop';graph['stop']={k:rec.get(k) for k in ['request_id','status','http_status','error']};return False
  data=t.json_payload(rec);known={f.get('actor') for f in fronts if f['kind']=='bluesky'};added=0
  for actor in data.get('followers',[]):
   did=actor.get('did')
   if did and did not in known:
    fronts.append({'source':'bluesky','kind':'bluesky','actor':did,'cursor':None,'status':'active','frame':'bluesky:official_followers_graph:'+did,'graph_observation_request':rec['request_id'],'historical_graph_membership':'unknown'});known.add(did);added+=1
  previous=graph['cursor'];graph['cursor']=data.get('cursor');graph['last_request_id']=rec['request_id']
  if not graph['cursor'] or graph['cursor']==previous:graph['status']='native_graph_exhausted_or_nonadvancing'
  t.append(t.WORK/'INVENTORY_PROGRESS.jsonl',{'at_utc':t.utc(),'source_id':'bluesky','frame_id':graph['frame'],'request_id':rec['request_id'],'unit_scope':'contemporary_official_account_followers_graph','returned_actors':len(data.get('followers',[])),'new_actor_frontiers':added,'cursor_before':previous,'cursor_after':graph['cursor'],'inventory_total':None,'historical_membership':'unknown'})
  t.atomic(FRONT,fronts);return added>0 or graph['status']=='active'
 except t.Stop as exc:
  if any(x in str(exc) for x in ['resource_stop','fixed_deadline']):raise
  graph['status']='preserved_graph_source_stop';graph['stop']=str(exc);return False
 finally:t.atomic(t.WORK/'GRAPH_FRONTIER.json',graph)

def main():
 with t.writer():
  t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'pid':os.getpid(),'owner_thread_id':t.OWNER,'at_utc':t.utc(),'worker':str(t.WORK)})
  check=t.read_json(t.WORK/'CHANGED_PIPELINE_CHECK.json');assert check['passed']
  assert t.read_json(t.WORK/'GUARD_REGRESSION.json')['passed']
  assert t.read_json(t.WORK/'HISTORICAL_REPAIR_REGRESSION.json')['passed']
  assert t.read_json(t.WORK/'ARCHIVE_ADAPTER_REGRESSION.json')['passed']
  assert t.read_json(t.WORK/'TAIL_ACCOUNTING_REGRESSION.json')['passed']
  assert t.read_json(t.WORK/'ARCHIVE_NOTICE_REGRESSION.json')['passed']
  scope=t.release();rel=t.read_json(t.WORK.parent/'control/OWNER_RELEASE.json')
  assert rel['input_receipt_sha256']==t.sha((t.REPO/scope['input_receipt_reference']).read_bytes())
  baseline=t.read_json(t.WORK/'INHERITED_BASELINE.json');before=baseline['counts']
  hashes={p.name:t.sha(p.read_bytes()) for p in t.WORK.glob('*.py')}
  for name in ['schema_v2.sql','schema_legacy.sql','source_registry.json','FRONTIER_ADDITIONS.json']:hashes[name]=t.sha((t.WORK/name).read_bytes())
  t.atomic(t.WORK/('START_RECEIPT.json' if not (t.WORK/'START_RECEIPT.json').exists() else 'RESUME_START_RECEIPT_'+str(os.getpid())+'.json'),{'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'input_receipt_sha256':t.sha((t.REPO/t.release()['input_receipt_reference']).read_bytes()),'implementation_hashes':hashes,'changed_check_passed':True,'lifetime_mutex_held':True,'baseline':before,'inherited_counters':{'requests':baseline['lifetime_charged_requests'],'returned_keys':baseline['lifetime_distinct_returned_objects']},'predecessor_schema_and_integrity_accepted':True,'no_body_copy_or_migration':True})
  with t.shared(t.footprint()):
   c=e.db();assert c.execute("SELECT 1 FROM social_schema_versions WHERE version='social-native-v2'").fetchone()
   for source in t.read_json(t.WORK/'source_registry.json'):e.register(c,source)
   c.close()
  t.atomic(t.WORK/'MIGRATION_RECEIPT.json',{'at_utc':t.utc(),'legacy_mapping_digest':t.read_json(t.REPO/scope['predecessor_worker_reference']/'MIGRATION_RECEIPT.json')['legacy_mapping_digest'],'schema_reused':'social-native-v2','no_migration_or_old_body_audit':True})
  fronts=t.read_json(FRONT) or initial();t.atomic(FRONT,fronts);last_checkpoint=0;cycles=0
  reason=None
  try:
   while True:
    t.release()
    if (t.WORK/'MAINTENANCE_STOP_REQUEST.json').exists():reason='owner_requested_committed_boundary_maintenance';break
    fronts=requests_import(fronts)
    if probes():continue
    if replenish(fronts):checkpoint(fronts);continue
    runnable=[f for f in fronts if f['status']=='active' and f.get('defer_until',0)<=time.time()]
    if not runnable:
     active=[x for x in fronts if x['status']=='active']
     if active:time.sleep(min(10,max(1,min(x.get('defer_until',0) for x in active)-time.time())));continue
     # Allow evidenced additions without treating prefix completion as exhaustion.
     t.atomic(t.WORK/'FRONTIER_WAIT.json',{'at_utc':t.utc(),'reason':'retained chronological source routes plus documented graph replenishment exhausted or blocked; source stops preserved','frontier_states':[{k:f.get(k) for k in ['source','frame','status','stop']} for f in fronts]});reason='complete_operation_capacity_failure_across_remaining_permitted_routes' if any(x['status']=='complete_operation_capacity_blocked' for x in fronts) else 'evidenced_eligible_frontier_exhaustion';break
    # Fair ageing by the last bounded source operation prevents graph size from
    # consuming the round. No coverage, parent, body-count or time-share input.
    source_age=t.state().get('source_last_action',{})
    source=min({x['source'] for x in runnable},key=lambda sid:source_age.get(sid,0))
    f=select_frontier(runnable);source=f['source'];url,route=job(f)
    f['last_attempt_epoch']=time.time();t.state().setdefault('source_last_action',{})[source]=time.time()
    cycles+=1
    try:
     if route=='thesession_index' and f.get('seed_index_response_request_id') and not f.get('seed_index_loaded'):rec=t.read_json(t.WORK/'receipts'/(f['seed_index_response_request_id']+'.json'))
     elif route in ('ilxor_topic','thesession_topic') and url==f.get('seed_response_url') and not f.get('seed_loaded'):rec=t.read_json(t.WORK/'receipts'/(f['seed_response_request_id']+'.json'))
     else:rec=t.fetch(url,f['source'],'content',cap=f.get('raw_cap_bytes'))
     if rec['status']!='saved':f['status']='source_access_stop';f['stop']=rec;continue
     if route.startswith('thesession_'):
      import thesession_adapter
      rows,data=thesession_adapter.index(t.json_payload(rec)) if route=='thesession_index' else thesession_adapter.records(t.payload(rec),url)
     elif route=='ilxor_topic':
      import public_html_adapter
      rows,data=public_html_adapter.ilxor_thread(t.payload(rec),url)
     elif route.startswith('mail_archive_'):
      import public_html_adapter
      rows,data=public_html_adapter.mail_index(t.payload(rec),url) if route=='mail_archive_index' else public_html_adapter.mail_message(t.payload(rec),url,f['source'])
     elif route.startswith('tildes_'):
      import public_html_adapter
      rows,data=(public_html_adapter.tildes_index if route=='tildes_index' else public_html_adapter.tildes_topic)(t.payload(rec),url)
     elif route in ('mbox_archive','w3_period_index','w3_message'):
      import archive_adapter
      raw=t.payload(rec)
      maximum=f.get('decompressed_cap_bytes',16*1048576)
      if raw.startswith(b'\x1f\x8b'):
       import gzip,io
       with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:raw=g.read(maximum+1)
      if len(raw)>maximum:raise t.Stop('decompressed_archive_operation_bound')
      if route=='mbox_archive':rows=archive_adapter.mbox_records(raw,f['source'],url);data={}
      elif route=='w3_message':rows=archive_adapter.w3_records(raw,url,f['source']);data={}
      else:
       links=archive_adapter.html_links(raw,url);data={'native_message_urls':sorted(x for x in links if urllib.parse.urlsplit(x).hostname=='lists.w3.org' and re.search(r'/[0-9]{4}\.html$',x))};rows=[]
     else:data=t.json_payload(rec)
     if (data.get('error_id') or data.get('error')) if isinstance(data,dict) else False:f['status']='native_api_error';f['stop']={k:data.get(k) for k in ['error_id','error_name','error_message']};continue
     if route in ('mbox_archive','w3_period_index','w3_message','ilxor_topic') or route.startswith(('tildes_','mail_archive_','thesession_')):pass
     elif route=='hackernews':
      import archive_adapter
      rows=archive_adapter.hn_records(data,f['source'],f['next_id'])
     elif route in ('lemmy_posts','lemmy_comments'):
      import lemmy_adapter
      rows=lemmy_adapter.records(data,f['source'],f['base'])
     elif route.startswith('se_'):rows=e.se(data,f['source'])
     elif route=='discourse_archive_index':rows=[]
     elif route.startswith('discourse'):rows=e.discourse(data,f['source'],f['base'],f['license'])
     elif route=='mastodon':rows=e.mastodon(data,f['source'])
     else:rows=e.bluesky(data)
     with t.shared(t.footprint()):
      c=e.db();registry={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')};e.register(c,registry[f['source']],frame_definition(f));c.close()
     before={k:f.get(k) for k in ['year','page','partition_from','before','max_id','cursor','next_id','topics','chunks'] if k in f and k not in ('topics','chunks')}
     result=e.load(rows,rec,f['frame']);advance(f,data,route);f['last_load']=result;f['last_url']=url
     dates=[r.get('native_created_at') for r in rows if r.get('native_created_at')]
     if dates:f['oldest_returned_publication_at']=min(dates+[f.get('oldest_returned_publication_at') or min(dates)])
     f['new_core_bodies']=f.get('new_core_bodies',0)+result['new_qualified_posts']
     t.append(t.WORK/'INVENTORY_PROGRESS.jsonl',{'at_utc':t.utc(),'source_id':f['source'],'frame_id':f['frame'],'request_id':rec['request_id'],'native_index_url':url,'unit_scope':route,'cursor_before':before,'cursor_after':{k:f.get(k) for k in before},'returned_entities':len(rows),'native_id_set_sha256':t.sha(json.dumps(sorted(e.key(r) for r in rows)).encode()),'observed_state':f['status'],'inventory_total':None,'denominator_status':'unknown_snapshot_inventory'})
     checkpoint(fronts)
     if rec.get('api_backoff'):f['defer_until']=time.time()+rec['api_backoff']
     if rec.get('api_quota_remaining')==0:f['status']='native_daily_quota_exhausted'
     print(json.dumps({k:result[k] for k in ['at_utc','frame_id','new_entities','new_qualified_posts','lifetime_returned_objects']}),flush=True)
    except t.Stop as exc:
     why=str(exc)
     if why.startswith('resource_stop'):
      f['status']='complete_operation_capacity_blocked';f['stop']=why
      t.append(t.WORK/'CAPACITY_BLOCKED_OPERATIONS.jsonl',{'at_utc':t.utc(),'source_id':f['source'],'frame_id':f['frame'],'native_url':url,'reason':why,'remaining_routes_continue':True})
     elif any(x in why for x in ['fixed_deadline','request_ceiling','object_ceiling']):raise
     elif why.startswith('server_backoff_until'):f['defer_until']=float(why.rsplit(' ',1)[1])
     else:f['status']='preserved_source_stop';f['stop']=why
    finally:t.atomic(FRONT,fronts)
    if time.time()-last_checkpoint>300:checkpoint(fronts);last_checkpoint=time.time()
  except KeyboardInterrupt:reason='runtime_correction_interruption_preserved_state';raise
  except t.Stop as exc:reason=str(exc)
  except Exception as exc:
   t.atomic(t.WORK/'FAILURE.json',{'at_utc':t.utc(),'error':type(exc).__name__+': '+str(exc),'frontier':f if 'f' in locals() else None});raise
  finally:
   checkpoint(fronts,phase='stopped',stop_reason=reason or 'unexpected_exception')
   t.atomic(t.WORK/'RUN_STOP.json',{'at_utc':t.utc(),'reason':reason or 'unexpected_exception','pid':os.getpid(),'deadline_preserved':True})
if __name__=='__main__':main()
