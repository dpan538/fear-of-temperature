"""Continuous native-frontier scheduler within one fixed release. No topic gates."""
import datetime as dt,json,time,os,sys,urllib.parse,hashlib
from pathlib import Path
import transport as t,entities as e
FRONT=t.WORK/'FRONTIERS.json'
FILTER='!)cN)B)B5rJi5kvLl5pKw5R)4jh321X0GAFsQZtqCWdBvL'

def query(base,params):return base+'?'+urllib.parse.urlencode(params,doseq=True)
def checkpoint():
 with t.shared(t.footprint()):
  c=e.db();counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['posts','versions','native_entities','entity_versions','native_edges','native_attachments','responses']};c.close()
  s=t.state();t.atomic(t.WORK/'CHECKPOINT.json',{'at_utc':t.utc(),'charged_requests':s['requests'],'distinct_returned_objects':len(s['returned_object_ids']),'counts':counts,'frontiers':t.read_json(FRONT),'deadline_utc':t.release()['hard_deadline_at_utc']})

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
 if k=='se_questions':
  if f['context_queue']:
   q=f['context_queue'][0];return query('https://api.stackexchange.com/2.3/questions/'+q['ids']+'/'+q['type'],{'site':sid[3:],'order':'asc','sort':'creation','pagesize':100,'page':q['page'],'filter':FILTER}),'se_context'
  y=f['year'];from_=int(dt.datetime(y,1,1,tzinfo=dt.timezone.utc).timestamp());to=int(dt.datetime(y+1,1,1,tzinfo=dt.timezone.utc).timestamp())-1
  to=min(to,int(dt.datetime(2026,9,22,tzinfo=dt.timezone.utc).timestamp())-1)
  return query('https://api.stackexchange.com/2.3/questions',{'site':sid[3:],'fromdate':from_,'todate':to,'sort':'creation','order':'asc','pagesize':100,'page':f['page'],'filter':FILTER}),'se_questions'
 if k=='discourse':
  if f['chunks']:
   q=f['chunks'][0];return query(f['base']+'/t/'+str(q['topic'])+'/posts.json',{'post_ids[]':q['ids']}),'discourse_chunk'
  if f['topics']:return f['base']+'/t/'+str(f['topics'][0])+'.json','discourse_topic'
  return f['base']+'/posts.json'+('' if f['before'] is None else '?before='+str(f['before'])),'discourse_index'
 if k=='mastodon':return query(f['base']+'/api/v1/timelines/public',{'local':'true','limit':40,'max_id':f['max_id']}),'mastodon'
 if k in ('lemmy_posts','lemmy_comments'):
  params={'type_':'Local','sort':'Old','limit':50,'page':f.get('page',1)}
  if k=='lemmy_posts' and f.get('cursor'):params.pop('page');params['page_cursor']=f['cursor']
  return query(f['base']+'/api/v3/'+('post/list' if k=='lemmy_posts' else 'comment/list'),params),k
 if k=='bluesky':
  p={'actor':f['actor'],'limit':100,'filter':'posts_with_replies','includePins':'false'}
  if f.get('cursor'):p['cursor']=f['cursor']
  return query('https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed',p),'bluesky'
 raise t.Stop('unknown_frontier_kind')

def advance(f,data,route):
 if route in ('lemmy_posts','lemmy_comments'):
  items=data.get('posts' if route=='lemmy_posts' else 'comments',[])
  if not items:f['status']='native_local_index_exhausted';return
  fingerprint=t.sha(json.dumps([x.get('post' if route=='lemmy_posts' else 'comment',{}).get('id') for x in items]).encode())
  if fingerprint==f.get('last_batch_fingerprint'):f['status']='nonadvancing_native_cursor';return
  f['last_batch_fingerprint']=fingerprint;f['page']=f.get('page',1)+1
  if route=='lemmy_posts' and data.get('next_page'):f['cursor']=data['next_page']
 elif route.startswith('se_'):
  if route=='se_context':
   if data.get('has_more'):f['context_queue'][0]['page']+=1
   else:f['context_queue'].pop(0)
  else:
   ids=[str(x['question_id']) for x in data.get('items',[])]
   # Native child returns are part of the same continuing ELT, never split into fake posts.
   if ids:
    for typ in ['answers','comments']:f['context_queue'].append({'ids':';'.join(ids),'type':typ,'page':1})
   if data.get('has_more'):
    f['page']+=1
    if f['page']>25:
     f['status']='anonymous_page_limit_requires_narrower_native_date_partition';f['limit_evidence']='25 pages/year; preserve cursor for bounded split'
   else:
    f['year']+=1;f['page']=1
    if f['year']>2026:f['status']='native_frontier_exhausted'
 elif route.startswith('discourse'):
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
 if k=='discourse':
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
  if x['name'] in done:continue
  try:rec=t.fetch(x['url'],x['source'],x.get('purpose','documentation'));done[x['name']]={k:rec.get(k) for k in ['request_id','status','raw_reference','http_status','location','error']}
  except t.Stop as exc:done[x['name']]={'status':'stop','reason':str(exc)}
  t.atomic(t.WORK/'PROBE_RESULTS.json',done);return True
 return False

def main():
 with t.writer():
  t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'pid':os.getpid(),'owner_thread_id':t.OWNER,'at_utc':t.utc(),'worker':str(t.WORK)})
  check=t.read_json(t.WORK/'CHANGED_PIPELINE_CHECK.json');assert check['passed']
  with t.shared(t.footprint()):
   c=e.db();before={x:c.execute('SELECT COUNT(*) FROM '+x).fetchone()[0] for x in ['posts','versions','native_identities']};legacy=[x[0] for x in c.execute("SELECT persistent_post_id FROM native_identities WHERE identity_basis='established_ID_preserved' AND source_id LIKE 'se_%' ORDER BY persistent_post_id")];e.migrate(c)
   after={x:c.execute('SELECT COUNT(*) FROM '+x).fetchone()[0] for x in before};assert before==after
   for source in t.read_json(t.WORK/'source_registry.json'):e.register(c,source)
   c.close()
   t.atomic(t.WORK/'MIGRATION_RECEIPT.json',{'at_utc':t.utc(),'before':before,'after':after,'legacy_mapping_count':len(legacy),'legacy_mapping_digest':t.sha(json.dumps(legacy).encode()),'additive_only':True,'no_old_body_copy':True,'schema':'social-native-v2'})
  hashes={p.name:t.sha(p.read_bytes()) for p in t.WORK.glob('*.py')};hashes['schema_v2.sql']=t.sha((t.WORK/'schema_v2.sql').read_bytes())
  t.atomic(t.WORK/'START_RECEIPT.json',{'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'input_receipt_sha256':t.sha((t.WORK.parent/'control/INPUT_RECEIPT.json').read_bytes()),'implementation_hashes':hashes,'changed_check_passed':True,'lifetime_mutex_held':True,'baseline':before})
  fronts=t.read_json(FRONT) or initial();t.atomic(FRONT,fronts);last_checkpoint=0;cycles=0
  reason=None
  try:
   while True:
    t.release();fronts=requests_import(fronts)
    if probes():continue
    runnable=[f for f in fronts if f['status']=='active' and f.get('defer_until',0)<=time.time()]
    if not runnable:
     active=[x for x in fronts if x['status']=='active']
     if active:time.sleep(min(10,max(1,min(x.get('defer_until',0) for x in active)-time.time())));continue
     # Allow evidenced additions without treating prefix completion as exhaustion.
     t.atomic(t.WORK/'FRONTIER_WAIT.json',{'at_utc':t.utc(),'reason':'known_eligible_frontiers_exhausted_or_blocked; no automatic new release','frontier_states':[{k:f.get(k) for k in ['source','frame','status','stop']} for f in fronts]});reason='evidenced_eligible_frontier_exhaustion';break
    remaining=t.release()['max_distinct_native_content_objects']-len(t.state()['returned_object_ids'])
    feasible=[f for f in runnable if object_bound(f)<=remaining]
    if not feasible:
     # A collected Discourse stream exposes concrete missing native IDs; use the
     # documented single-post route to consume the final bounded remainder.
     chunk=next((f for f in runnable if f['kind']=='discourse' and f.get('chunks')),None)
     if remaining>0 and chunk:
      f=chunk;url=f['base']+'/posts/'+str(f['chunks'][0]['ids'][0])+'.json';route='discourse_single_remaining'
     else:raise t.Stop('native_object_actual_operation_capacity_boundary remaining='+str(remaining))
    else:
     f=feasible[cycles%len(feasible)];url,route=job(f)
    cycles+=1
    try:
     rec=t.fetch(url,f['source'],'content')
     if rec['status']!='saved':f['status']='source_access_stop';f['stop']=rec;continue
     data=t.json_payload(rec)
     if (data.get('error_id') or data.get('error')) if isinstance(data,dict) else False:f['status']='native_api_error';f['stop']={k:data.get(k) for k in ['error_id','error_name','error_message']};continue
     if route in ('lemmy_posts','lemmy_comments'):
      import lemmy_adapter
      rows=lemmy_adapter.records(data,f['source'],f['base'])
     elif route.startswith('se_'):rows=e.se(data,f['source'])
     elif route.startswith('discourse'):rows=e.discourse(data,f['source'],f['base'],f['license'])
     elif route=='mastodon':rows=e.mastodon(data,f['source'])
     else:rows=e.bluesky(data)
     with t.shared(t.footprint()):
      c=e.db();registry={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')};e.register(c,registry[f['source']],frame_definition(f));c.close()
     result=e.load(rows,rec,f['frame']);advance(f,data,route);f['last_load']=result;f['last_url']=url
     if rec.get('api_backoff'):f['defer_until']=time.time()+rec['api_backoff']
     if rec.get('api_quota_remaining')==0:f['status']='native_daily_quota_exhausted'
     print(json.dumps({k:result[k] for k in ['at_utc','frame_id','new_entities','new_qualified_posts','lifetime_returned_objects']}),flush=True)
    except t.Stop as exc:
     why=str(exc)
     if any(x in why for x in ['resource_stop','fixed_deadline','request_ceiling','object_ceiling']):raise
     if why.startswith('server_backoff_until'):f['defer_until']=float(why.rsplit(' ',1)[1])
     else:f['status']='preserved_source_stop';f['stop']=why
    finally:t.atomic(FRONT,fronts)
    if time.time()-last_checkpoint>900:checkpoint();last_checkpoint=time.time()
  except t.Stop as exc:reason=str(exc)
  except Exception as exc:
   t.atomic(t.WORK/'FAILURE.json',{'at_utc':t.utc(),'error':type(exc).__name__+': '+str(exc),'frontier':f if 'f' in locals() else None});raise
  finally:
   t.atomic(t.WORK/'RUN_STOP.json',{'at_utc':t.utc(),'reason':reason or 'unexpected_exception','pid':os.getpid(),'deadline_preserved':True})
if __name__=='__main__':main()
