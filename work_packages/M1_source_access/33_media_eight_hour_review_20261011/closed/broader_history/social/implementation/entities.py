"""Version-preserving social entity extension; source-native facts only."""
import datetime as dt
import json
import sqlite3
from pathlib import Path
import transport as t
SCHEMA=t.WORK/'schema_v2.sql'

def db(path=t.DB):
 c=sqlite3.connect(path);c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=DELETE');return c

def migrate(c):
 c.executescript(SCHEMA.read_text())
 if c.execute("SELECT 1 FROM social_schema_versions WHERE version='social-native-v2'").fetchone():return
 with c:
  c.execute("INSERT OR IGNORE INTO social_schema_versions VALUES ('social-native-v2',?,?)",(t.utc(),t.sha(t.SCOPE_PATH.read_bytes())))
  c.execute("""INSERT OR IGNORE INTO native_entities SELECT p.persistent_post_id,p.source_id,i.native_namespace,p.native_post_id,p.source_url,p.native_unit,p.native_created_at,'source_timestamp',p.author_id,p.author_role,p.author_country,(SELECT MIN(first_retrieved_at) FROM versions v WHERE v.persistent_post_id=p.persistent_post_id),1 FROM posts p JOIN native_identities i ON i.persistent_post_id=p.persistent_post_id WHERE i.identity_basis!='deprecated_adapter_alias_not_native_namespace'""")
  c.execute("""INSERT OR IGNORE INTO entity_versions SELECT v.body_version_id,v.persistent_post_id,v.body_version_id,NULL,NULL,v.body_sha256,v.native_edited_at,v.native_revision,'complete_native_text','inside_fixed_interval',1,1,v.content_license,v.license_basis,'{"inherited_accepted":true}',v.native_fields_json,v.first_retrieved_at FROM versions v JOIN native_entities n ON n.entity_id=v.persistent_post_id WHERE n.inherited=1 AND v.first_retrieved_at<'2026-10-09T02:41:51.640855+00:00'""")
  c.execute("INSERT OR IGNORE INTO entity_observations SELECT body_version_id,request_id,'predecessor_accepted_frame',retrieved_at FROM observations o WHERE EXISTS (SELECT 1 FROM entity_versions v WHERE v.entity_version_id=o.body_version_id)")

def register(c,source,frame=None):
 with c:
  c.execute('INSERT OR REPLACE INTO acquisition_sources VALUES (?,?,?,?,?,?,?)',(source['source_id'],source.get('base_url'),source.get('stratum',source.get('geographic_stratum',source.get('region','GLOBAL'))),source.get('public_access','documented_anonymous_public_read'),source.get('collection_retention'),source.get('redistribution','no_blanket_grant_verified'),json.dumps(source,ensure_ascii=False)))
  for i,url in enumerate(source.get('api_documentation',[])):
   c.execute('INSERT OR IGNORE INTO acquisition_interfaces VALUES (?,?,?,?,?)',(source['source_id']+':docs:'+str(i),source['source_id'],url,source.get('base_url',''),source.get('adapter','native_api')))
  if frame:
   c.execute('INSERT OR IGNORE INTO acquisition_frames VALUES (?,?,?,?,?,?,?)',(frame['frame_id'],source['source_id'],frame.get('frame_type','native_index'),frame['selection_rule'],frame.get('existence_lower_bound'),frame.get('actor_role_basis','unknown_without_source_evidence'),json.dumps(frame,ensure_ascii=False)))

def key(r): return r['source_id']+'|'+r['native_namespace']+'|'+str(r['native_post_id'])
def edge(kind,target,ns=None,source=None,url=None,meta=None):return dict(relation_type=kind,target_native_id=str(target) if target is not None else None,target_namespace=ns,target_source_id=source,target_url=url,native_fields=meta or {})

def prepare(r):
 r=dict(r);body=r.get('body_original') or ''
 text=body.replace('\r\n','\n').strip() if r.get('body_format')=='plain' else t.clean(body)
 r['body_text']=text;r['body_sha256']=t.sha(body.encode()) if body else None
 date=r.get('native_created_at');ds=date[:10] if isinstance(date,str) else ''
 r['fixed_interval_state']='inside_fixed_interval' if '1988-01-01'<=ds<='2026-09-21' else 'outside_fixed_interval' if ds else 'missing_or_unresolved_date'
 r['content_state']=r.get('content_state') or ('complete_native_text' if text else 'bodyless_native_entity')
 r['readable_native_unit']=int(bool(text) and r['content_state']=='complete_native_text' and r['fixed_interval_state']=='inside_fixed_interval' and bool(r.get('source_url')))
 r['independently_authored_body']=int(bool(r['readable_native_unit']) and r['native_unit'] not in ('repost_wrapper','context_container','tombstone','index_preview') and (r['native_namespace']!='forum_post' or r.get('native_fields',{}).get('post_type',1)==1))
 return r

def load(records,rec,frame_id):
 t.PENDING_CANDIDATE_VERSIONS=len(records)
 try:return _load_impl(records,rec,frame_id)
 finally:t.PENDING_CANDIDATE_VERSIONS=0

def _load_impl(records,rec,frame_id):
 rows=[prepare(r) for r in records];bodybytes=sum(len((r.get('body_original') or '').encode())+len(json.dumps({k:r.get(k) for k in ('native_fields','flags','attachments','edges')},ensure_ascii=False).encode()) for r in rows)
 db_before_bytes=t.DB.stat().st_size
 with t.shared(t.footprint(0,bodybytes,len(rows)),inflight_at=rec.get('started_at') or rec['retrieved_at']):
  st=t.state();returned=set(st['returned_object_ids'])|{key(r) for r in rows}
  if not t.within_optional_limit(len(returned),t.release(inflight_at=rec.get('started_at') or rec['retrieved_at'])['max_distinct_native_content_objects']):raise t.Stop('returned_native_object_ceiling')
  c=db();new=nv=qualified=0;journal_peak=0;year_deltas={}
  with c:
   c.execute('INSERT OR IGNORE INTO responses VALUES (?,?,?,?,?,?,?,?)',(rec['request_id'],rec['url'],rec['retrieved_at'],rec['raw_reference'],rec['raw_sha256'],rec['stored_sha256'],rec['raw_bytes'],rec['stored_bytes']))
   for r in rows:
    identity=c.execute('SELECT entity_id FROM native_entities WHERE source_id=? AND native_namespace=? AND native_id=?',(r['source_id'],r['native_namespace'],str(r['native_post_id']))).fetchone()
    eid=identity[0] if identity else 'social:'+r['source_id']+':'+r['native_namespace']+':'+str(r['native_post_id'])
    r['persistent_post_id']=eid
    new+=c.execute('INSERT OR IGNORE INTO native_entities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)',(eid,r['source_id'],r['native_namespace'],str(r['native_post_id']),r.get('source_url'),r['native_unit'],r.get('native_created_at'),r.get('date_precision') or ('source_timestamp' if r.get('native_created_at') else 'unknown'),r.get('author_id'),r.get('author_role','unknown'),None,rec['retrieved_at'])).rowcount
    flags=dict(r.get('flags',{}));old=c.execute('SELECT native_created_at,native_unit FROM native_entities WHERE entity_id=?',(eid,)).fetchone()
    if old!=(r.get('native_created_at'),r['native_unit']):flags['observed_identity_date_or_unit_conflict']={'established':old,'observed':[r.get('native_created_at'),r['native_unit']]}
    core=None
    if r['readable_native_unit'] and r['independently_authored_body']:
     # Identity remains stable across preview->complete and body corrections.
     prepared=t.prepare_record(r,{key(r):eid});prepared['native_fields']=r.get('native_fields',{})
     core=prepared['body_version_id']
     prior=c.execute('SELECT 1 FROM posts WHERE persistent_post_id=?',(eid,)).fetchone()
     if not prior:
      added=c.execute('INSERT OR IGNORE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(eid,r['source_id'],str(r['native_post_id']),r['source_url'],r['native_unit'],str(r.get('thread_id') or 'unresolved'),r.get('reply_to_post_id'),r['native_created_at'],r.get('author_id'),r.get('author_role','unknown'),None,r.get('context_status','context_partial'))).rowcount
      qualified+=added
      if added:year_deltas[r['source_id']+'|'+r['native_created_at'][:4]]=year_deltas.get(r['source_id']+'|'+r['native_created_at'][:4],0)+added
     c.execute('INSERT OR IGNORE INTO native_identities VALUES (?,?,?,?,?)',(r['source_id'],r['native_namespace'],str(r['native_post_id']),eid,'native_namespace_typed_ID'))
     c.execute('INSERT OR IGNORE INTO post_urls VALUES (?,?,?,?)',(eid,r['source_url'],rec['request_id'],'canonical' if not prior else 'observed_alias'))
     c.execute('INSERT OR IGNORE INTO parent_context VALUES (?,?,?,?,?)',(eid,r.get('parent_namespace'),r.get('reply_to_post_id'),r.get('thread_id'),r.get('context_status','context_partial')))
     c.execute('INSERT OR IGNORE INTO versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(core,eid,r['body_sha256'],r['body_original'],r['body_text'],r.get('native_edited_at'),str(r.get('native_revision')) if r.get('native_revision') is not None else None,rec['retrieved_at'],r.get('content_license','unknown'),r.get('license_basis','unresolved'),r['content_state'],'direct_source_native_response',json.dumps(r.get('native_fields',{}),ensure_ascii=False)))
     c.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?)',(core,rec['request_id'],rec['retrieved_at']))
    # Metadata/state changes also have immutable versions; core body IDs stay unchanged.
    serial=json.dumps({k:r.get(k) for k in ['body_sha256','native_edited_at','native_revision','content_state','fixed_interval_state','native_created_at','native_unit','native_fields','flags']},sort_keys=True,ensure_ascii=False)
    vid=t.sha((eid+'|'+serial).encode())
    nv+=c.execute('INSERT OR IGNORE INTO entity_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(vid,eid,core,None if core else r.get('body_original'),None if core else r['body_text'],r['body_sha256'],r.get('native_edited_at'),str(r.get('native_revision')) if r.get('native_revision') is not None else None,r['content_state'],r['fixed_interval_state'],r['readable_native_unit'],r['independently_authored_body'],r.get('content_license','unknown'),r.get('license_basis','unresolved'),json.dumps(flags,ensure_ascii=False),json.dumps(r.get('native_fields',{}),ensure_ascii=False),rec['retrieved_at'])).rowcount
    c.execute('INSERT OR IGNORE INTO entity_observations VALUES (?,?,?,?)',(vid,rec['request_id'],frame_id,rec['retrieved_at']))
    for a in r.get('attachments',[]):
     aid=t.sha((vid+'|'+json.dumps(a,sort_keys=True)).encode())
     c.execute('INSERT OR IGNORE INTO native_attachments VALUES (?,?,?,?,?,?,?)',(aid,vid,str(a.get('id')) if a.get('id') is not None else None,a.get('type','unknown'),a.get('url') or (a.get('external') or {}).get('uri'),'metadata_only_media_not_downloaded',json.dumps(a,ensure_ascii=False)))
    edges=list(r.get('edges',[]))
    if r['body_sha256']:
     same=c.execute('SELECT DISTINCT entity_id FROM entity_versions WHERE body_sha256=? AND entity_id!=? LIMIT 10',(r['body_sha256'],eid)).fetchall()
     edges += [dict(relation_type='exact_body_overlap',target_entity_id=x[0],native_fields={'does_not_prove_common_work_or_delete':True}) for x in same]
    for e in edges:
     ts=e.get('target_source_id') or r['source_id'];ns=e.get('target_namespace');nid=e.get('target_native_id');te=e.get('target_entity_id')
     if not te and ns and nid:
      row=c.execute('SELECT entity_id FROM native_entities WHERE source_id=? AND native_namespace=? AND native_id=?',(ts,ns,nid)).fetchone();te=row[0] if row else None
     edgeid=t.sha((eid+'|'+json.dumps(e,sort_keys=True,ensure_ascii=False)).encode())
     c.execute('INSERT OR IGNORE INTO native_edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(edgeid,eid,e['relation_type'],ts,ns,nid,te,e.get('target_url'),'resolved' if te else 'unresolved_native_endpoint',json.dumps(e.get('native_fields',{}),ensure_ascii=False),rec['request_id'],rec['retrieved_at']))
    journal_path=Path(str(t.DB)+'-journal');journal_peak=max(journal_peak,journal_path.stat().st_size if journal_path.exists() else 0)
   for r in rows:
    c.execute("UPDATE native_edges SET target_entity_id=(SELECT entity_id FROM native_entities WHERE source_id=? AND native_namespace=? AND native_id=?),resolution_state='resolved' WHERE target_entity_id IS NULL AND target_source_id=? AND target_namespace=? AND target_native_id=?",(r['source_id'],r['native_namespace'],str(r['native_post_id']),r['source_id'],r['native_namespace'],str(r['native_post_id'])))
   journal_path=Path(str(t.DB)+'-journal');journal_peak=max(journal_peak,journal_path.stat().st_size if journal_path.exists() else 0)
  c.close();st['returned_object_ids']=sorted(returned)
  if not st.get('first_successful_load_at_utc'):st['first_successful_load_at_utc']=t.utc()
  st['last_successful_load_at_utc']=t.utc()
  st['new_entities']=st.get('new_entities',0)+new;st['new_entity_versions']=st.get('new_entity_versions',0)+nv;st['new_core_bodies']=st.get('new_core_bodies',0)+qualified
  for k,n in year_deltas.items():st.setdefault('source_year_deltas',{})[k]=st.get('source_year_deltas',{}).get(k,0)+n
  t.persist_state(st)
  result={'at_utc':t.utc(),'request_id':rec['request_id'],'frame_id':frame_id,'returned_entities':len(rows),'new_entities':new,'new_entity_versions':nv,'new_qualified_posts':qualified,'observed_journal_peak_bytes':journal_peak,'reserved_operation_bytes':t.footprint(0,bodybytes,len(rows)),'body_and_native_metadata_bytes':bodybytes,'db_before_bytes':db_before_bytes,'db_after_bytes':t.DB.stat().st_size,'observed_additional_disk_peak_upper_bytes':journal_peak+max(0,t.DB.stat().st_size-db_before_bytes),'lifetime_returned_objects':len(returned),'raw_reference':rec['raw_reference'],'source_year_deltas':year_deltas}
  t.append(t.WORK/'LOADS.jsonl',result)
  if result['observed_additional_disk_peak_upper_bytes']>result['reserved_operation_bytes']:
   t.atomic(t.WORK/'MAINTENANCE_STOP_REQUEST.json',{'at_utc':t.utc(),'reason':'Observed complete native write peak exceeds prospective operation reserve; committed data retained; recalibrate before another same-class write','load_receipt':result,'deadline_unchanged':True})
  if new and not (t.WORK/'FIRST_REAL_LOAD.json').exists():t.atomic(t.WORK/'FIRST_REAL_LOAD.json',result)
  try:
   import planning_adapter
   planning_adapter.emit(rows,rec)
  except Exception as exc:
   t.append(t.WORK/'TELEMETRY_ERRORS.jsonl',{'at_utc':t.utc(),'request_id':rec['request_id'],'error':type(exc).__name__+': '+str(exc),'load_already_committed':True})
 return result

def se(data,sid):
 rows=t.stackexchange_records(data,sid)
 for r in rows:
  r['native_namespace']='comment' if r['native_unit']=='comment' else 'post';r['edges']=[]
  if r.get('reply_to_post_id'):r['edges'].append(edge('reply',r['reply_to_post_id'],'post'))
  if r.get('thread_id') and r['thread_id']!='unresolved':r['edges'].append(edge('root',r['thread_id'],'post'))
  r['flags']={'source_creation_before_documented_site_beta':sid=='se_earthscience' and r['native_created_at']<'2014-04-15'}
 return rows

def discourse(data,sid,base,license_):
 if 'post_stream' in data:posts=data['post_stream'].get('posts',[])
 elif 'latest_posts' in data:posts=data['latest_posts']
 elif 'id' in data and 'topic_id' in data:posts=[data]
 else:posts=data.get('posts',[])
 rows=[];lookup={(p.get('topic_id'),p.get('post_number')):str(p['id']) for p in posts}
 for p in posts:
  tid=p.get('topic_id',data.get('id'));num=p.get('post_number');parentnum=p.get('reply_to_post_number');pid=lookup.get((tid,parentnum));edges=[edge('root_container',tid,'topic')]
  if parentnum:edges.append(edge('reply',pid or str(tid)+':'+str(parentnum),'forum_post' if pid else 'topic_post_number',meta={'native_reply_to_post_number':parentnum}))
  state='tombstone' if p.get('deleted_at') else 'hidden_native_entity' if p.get('hidden') else 'truncated_index_preview' if p.get('truncated') else 'complete_native_text' if p.get('cooked') else 'bodyless_native_entity'
  rows.append(dict(source_id=sid,native_namespace='forum_post',native_post_id=str(p['id']),native_unit='tombstone' if p.get('deleted_at') else 'forum_post' if num==1 else 'forum_reply',source_url=base+(p.get('post_url') or f'/t/{tid}/{num}'),native_created_at=p.get('created_at'),native_edited_at=p.get('updated_at'),native_revision=p.get('version'),thread_id=str(tid),reply_to_post_id=pid,author_id=str(p.get('user_id')) if p.get('user_id') is not None else None,author_role='unknown',body_original=p.get('cooked') or p.get('excerpt') or '',content_state=state,content_license=license_,license_basis='source user-contribution terms; version-specific native licence remains separately unresolved',native_fields={k:v for k,v in p.items() if k not in ('cooked','raw','excerpt')},flags={k:p.get(k) for k in ('hidden','deleted_at','truncated','post_type','staff','admin','moderator')},edges=edges))
 if 'post_stream' in data:
  rows.append(dict(source_id=sid,native_namespace='topic',native_post_id=str(data['id']),native_unit='context_container',source_url=base+'/t/'+str(data['id']),native_created_at=data.get('created_at'),body_original='',content_state='context_container',native_fields={k:v for k,v in data.items() if k!='post_stream'}|{'native_post_stream_ids':data['post_stream'].get('stream',[])}))
 return rows

def mastodon(data,sid):
 rows=[]
 for p in data:
  wrapper=bool(p.get('reblog'));body=p.get('content','');text=t.clean(body);edges=[]
  if p.get('in_reply_to_id'):edges.append(edge('reply',p['in_reply_to_id'],'status'))
  if wrapper:edges.append(edge('repost',p['reblog'].get('id'),'status',url=p['reblog'].get('url'),meta={'native_uri':p['reblog'].get('uri')}))
  if p.get('card',{}):edges.append(edge('link',None,url=p['card'].get('url')))
  unit='repost_wrapper' if wrapper else 'media_only_post' if not text and p.get('media_attachments') else 'link_only_post' if not text and p.get('card') else 'public_platform_post'
  rows.append(dict(source_id=sid,native_namespace='status',native_post_id=str(p['id']),source_url=p.get('url') or p.get('uri'),native_unit=unit,native_created_at=p.get('created_at'),native_edited_at=p.get('edited_at'),author_id=str(p.get('account',{}).get('id')),author_role='unknown',body_original=body,content_state='repost_wrapper' if wrapper else 'nonpublic_return_evidence' if p.get('visibility')!='public' else 'complete_native_text' if text else 'bodyless_native_entity',content_license='no_open_content_grant_verified',license_basis='accepted documented public/local-retention conditions; author ownership retained',thread_id=str(p['id']) if not p.get('in_reply_to_id') else 'unresolved',reply_to_post_id=p.get('in_reply_to_id'),flags={k:p.get(k) for k in ('visibility','language','sensitive','spoiler_text')},native_fields={k:v for k,v in p.items() if k not in ('content','reblog','media_attachments')},edges=edges,attachments=p.get('media_attachments',[])))
  if wrapper:
   nested=mastodon([p['reblog']],sid)
   for r in nested:r['flags']['returned_as_embedded_reblog_context']=True
   rows.extend(nested)
 return rows

def bluesky(data):
 rows=[]
 for item in data.get('feed',[]):
  p=item.get('post') or {};r=p.get('record') or {};uri=p.get('uri')
  if not uri:continue
  did=(p.get('author') or {}).get('did');reply=r.get('reply') or {};edges=[];embed=r.get('embed') or {}
  for kind in ('root','parent'):
   if reply.get(kind,{}).get('uri'):edges.append(edge('root' if kind=='root' else 'reply',reply[kind]['uri'],'at_uri'))
  quote_record=embed.get('record') or {};quote=quote_record.get('uri') or (quote_record.get('record') or {}).get('uri')
  if quote:edges.append(edge('quote',quote,'at_uri'))
  if (embed.get('external') or {}).get('uri'):edges.append(edge('link',None,url=embed['external']['uri']))
  rows.append(dict(source_id='bluesky',native_namespace='at_uri',native_post_id=uri,source_url=f'https://bsky.app/profile/{did}/post/{uri.rsplit("/",1)[-1]}',native_unit='quote_post' if quote else 'public_platform_post' if r.get('text') else 'media_only_post' if embed else 'unresolved_native_entity',native_created_at=r.get('createdAt'),native_revision=p.get('cid'),body_original=r.get('text',''),body_format='plain',author_id=did,author_role='institutional' if p.get('author',{}).get('handle')=='bsky.app' else 'unknown',thread_id=reply.get('root',{}).get('uri') or uri,reply_to_post_id=reply.get('parent',{}).get('uri'),content_license='no_open_content_grant_verified',license_basis='accepted official documented public API/local data copy; ownership retained',native_fields={k:v for k,v in p.items() if k!='record'}|{'native_record_metadata':{k:v for k,v in r.items() if k!='text'}},flags={'native_labels':p.get('labels',[])},edges=edges,attachments=[embed] if embed else []))
  if item.get('reason'):
   reason=item['reason'];actor=reason.get('by',{}).get('did');indexed=reason.get('indexedAt');wid=reason.get('uri') or t.sha(json.dumps(reason,sort_keys=True).encode())+':'+uri
   rows.append(dict(source_id='bluesky',native_namespace='repost_event',native_post_id=wid,source_url=None,native_unit='repost_wrapper',native_created_at=None,body_original='',content_state='repost_wrapper',author_id=actor,native_fields=reason,flags={'indexedAt_is_not_publication_time':indexed},edges=[edge('repost',uri,'at_uri')] ))
 return rows

# Extend the core adapter with embedded native record views; no extra HTTP.
_bluesky_outer=bluesky
def bluesky(data):
 rows=_bluesky_outer(data)
 def view(v):
  if not isinstance(v,dict):return
  if v.get('uri') and v.get('$type','').endswith('#viewRecord') and isinstance(v.get('value'),dict):
   post={k:x for k,x in v.items() if k not in ('value','$type','embeds')};post['record']=v['value']
   nested=_bluesky_outer({'feed':[{'post':post}]})
   for r in nested:r['flags']['returned_as_embedded_quote_context']=True
   rows.extend(nested)
  elif v.get('uri') and any(v.get('$type','').endswith(t) for t in ('#viewNotFound','#viewBlocked')):
   rows.append(dict(source_id='bluesky',native_namespace='at_uri',native_post_id=v['uri'],native_unit='tombstone' if v['$type'].endswith('#viewNotFound') else 'unresolved_native_entity',native_created_at=None,body_original='',content_state='unavailable_embedded_native_entity',native_fields=v,flags={'no_missing_body_or_publication_time_invented':True}))
  for k in ('record','media'):
   if isinstance(v.get(k),dict):view(v[k])
  for x in v.get('embeds',[]) or []:view(x)
 for item in data.get('feed',[]):view((item.get('post') or {}).get('embed'))
 return rows
