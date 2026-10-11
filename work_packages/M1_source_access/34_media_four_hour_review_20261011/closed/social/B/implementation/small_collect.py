"""Owner-bound whole-native historical recovery with reference-only old queues."""
import datetime as dt,json,os,signal,threading,time,urllib.parse
import transport as t,entities as e,thesession_adapter,finalize_metadata

CUR=t.WORK/'NATIVE_CURSORS.json'
CAP=64*1024
stop_event=threading.Event()

def query(url,params):return url+'?'+urllib.parse.urlencode(params,doseq=True)

def old_frames():
    cs=t.read_json(CUR);path=t.REPO/cs[0]['predecessor_frame_reference']
    assert t.sha(path.read_bytes())==cs[0]['predecessor_frame_file_sha256']
    return {f['frame']:f for f in t.read_json(path)}

def pending_chunk(c,f):
    chunks=f.get('chunks',[])
    if c['chunk_offset']<len(chunks):
        q=chunks[c['chunk_offset']];return q,c['post_offset'],'old'
    if c['new_pending_chunks']:return c['new_pending_chunks'][0],0,'new'
    return None,0,None

def job(c,f):
    if c['kind']!='thesession':
        q,offset,origin=pending_chunk(c,f)
        if q:return query(f['base']+'/t/'+str(q['topic'])+'/posts.json',{'post_ids[]':[q['ids'][offset]]}),'exact_post',{'origin':origin,'topic':q['topic'],'post_id':q['ids'][offset]}
    if c.get('next_comment_url'):return c['next_comment_url'],'session_topic',{'origin':'next'}
    if c['topic_offset']<len(f.get('topics',[])):
        tid=f['topics'][c['topic_offset']];origin='old'
    elif c['new_topics']:tid=c['new_topics'][0];origin='new'
    else:tid=None;origin=None
    if tid is not None:
        return (tid,'session_topic',{'origin':origin}) if c['kind']=='thesession' else (f['base']+'/t/'+str(tid)+'.json','topic',{'origin':origin,'topic':tid})
    if c.get('index_exhausted'):return None,None,None
    if c['kind']=='thesession':return query('https://thesession.org/discussions/new',{'format':'json','perpage':50,'page':c['page']}),'session_index',{}
    if c['kind']=='discourse_archive':return c['native_next_url'],'created_index',{}
    # Current/latest index is outside this historical prioritisation. Its known
    # queued surplus remains referenced; draining it never declares exhaustion.
    return None,None,None

def advance(c,f,data,route,unit,rows):
    if route=='exact_post':
        q,offset,origin=pending_chunk(c,f)
        if origin=='old':
            c['post_offset']+=1
            if c['post_offset']>=len(q['ids']):c['chunk_offset']+=1;c['post_offset']=0
        else:
            q['ids'].pop(0)
            if not q['ids']:c['new_pending_chunks'].pop(0)
        if str(unit['post_id']) not in {r['native_post_id'] for r in rows if r['native_namespace']=='forum_post'}:
            t.append(t.WORK/'NATIVE_UNAVAILABLE_ITEMS.jsonl',{'at_utc':t.utc(),'frame':c['frame'],'native_unit':unit,'state':'HTTP200 exact lookup omitted requested native body; cause unresolved'})
    elif route in ('topic','session_topic'):
        if unit['origin']=='old':c['topic_offset']+=1
        elif unit['origin']=='new':c['new_topics'].pop(0)
        if route=='topic':
            stream=data.get('post_stream',{});returned={p['id'] for p in stream.get('posts',[])}
            missing=[pid for pid in stream.get('stream',[]) if pid not in returned]
            if missing:c['new_pending_chunks'].append({'topic':unit['topic'],'ids':missing})
        else:c['next_comment_url']=data.get('native_next_comment_page_url')
    elif route=='session_index':
        c['new_topics']+=data['topic_urls'];c['page']=data['page']-1
        if c['page']<1:c['index_exhausted']=True
    elif route=='created_index':
        listing=data.get('topic_list',{});seen=set(f.get('seen_topics',[]))|set(f.get('topics',[]))|set(c['seen_new_topics'])
        added=[x['id'] for x in listing.get('topics',[]) if x['id'] not in seen]
        c['new_topics']+=added;c['seen_new_topics']+=added
        nxt=listing.get('more_topics_url')
        if nxt:
            nxt=urllib.parse.urljoin(f['base'],nxt);parts=urllib.parse.urlsplit(nxt)
            if parts.hostname!=urllib.parse.urlsplit(f['base']).hostname or parts.scheme!='https':raise t.Stop('native_pagination_cross_host_or_protocol')
            if not parts.path.endswith('.json'):nxt=urllib.parse.urlunsplit((parts.scheme,parts.netloc,parts.path+'.json',parts.query,parts.fragment))
            if nxt==c['native_next_url']:c['index_exhausted']=True
            else:c['native_next_url']=nxt
        else:c['index_exhausted']=True

def flush_metadata(force=False):
    st=t.state();model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');remaining=st['new_entity_versions']-model['already_annotated_changed_versions']
    if remaining<=0 or (remaining<50 and not force):return False
    counts=finalize_metadata.finalize(limit=min(remaining,100),phase='incremental',batch_records=10)
    # The SQL insert count is the committed new annotation delta, never a guess.
    model['already_annotated_changed_versions']+=counts['quality_annotations'];t.atomic(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json',model)
    t.append(t.WORK/'METADATA_FLUSHES.jsonl',{'at_utc':t.utc(),'counts':counts,'already_annotated_changed_versions':model['already_annotated_changed_versions']})
    return counts['quality_annotations']>0

def progress(cs,reason=None):
    st=t.state();b=t.read_json(t.WORK/'INHERITED_BASELINE.json');scope=t.read_json(t.SCOPE_PATH)
    out={'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'new_entities':st['new_entities'],'new_entity_versions':st['new_entity_versions'],'new_core_bodies':st['new_core_bodies'],'round_requests':st['requests']-b['lifetime_charged_requests'],'charged_requests':st['requests'],'distinct_returned_native_objects':len(st['returned_object_ids']),'source_year_deltas':st.get('source_year_deltas',{}),'first_successful_http_at_utc':st.get('first_successful_http_at_utc'),'last_successful_http_at_utc':st.get('last_successful_http_at_utc'),'first_successful_load_at_utc':st.get('first_successful_load_at_utc'),'last_successful_load_at_utc':st.get('last_successful_load_at_utc'),'cursor_states':[{k:c.get(k) for k in ('source','frame','state','chunk_offset','post_offset','topic_offset','page','native_next_url','new_core_bodies','oldest_returned_publication_at','stop')} for c in cs],'actual_capacity':t.read_json(t.WORK/'LAST_CAPACITY.json'),'stop_reason':reason,'coverage_count_parent_scores_used_for_stopping':False}
    t.atomic(t.WORK/'PROGRESS.json',out)
    elapsed=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(scope['earliest_network_and_load_start_at_utc'])).total_seconds()
    for hour in (1,2,3):
        p=t.WORK/f'CHECKPOINT_H{hour}.json'
        if hour>1 and elapsed>=hour*3600 and not p.exists():t.atomic(p,out)

def skip_item(c,f,route,unit,rec):
    # A bounded raw object or an isolated native 404 remains unresolved evidence.
    # It advances only this attempt disposition, never source inventory completion.
    t.append(t.WORK/'NATIVE_UNAVAILABLE_ITEMS.jsonl',{'at_utc':t.utc(),'frame':c['frame'],'native_unit':unit,'url':rec['url'],'request_id':rec['request_id'],'state':rec['status'],'http_status':rec.get('http_status'),'error':rec.get('error'),'whole_body_unavailable':True,'inventory_exhaustion_inferred':False})
    if route=='exact_post':advance(c,f,{},route,unit,[])
    elif route in ('topic','session_topic'):
        c['blocked_complete_native_ids'].append(unit|{'url':rec['url'],'request_id':rec['request_id']})
        if unit['origin']=='old':c['topic_offset']+=1
        elif unit['origin']=='new':c['new_topics'].pop(0)
        else:c['next_comment_url']=None
    else:c['state']='bounded_index_operation_unavailable';c['stop']=rec

def run():
    scope=t.release();assert t.read_json(t.WORK/'ACCOUNTING_REGRESSION.json')['passed']
    end=dt.datetime.fromisoformat(scope['hard_deadline_at_utc']).timestamp();cs=t.read_json(CUR);fs=old_frames();reason=None
    runtime={'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'code_sha256':t.sha((t.WORK/'small_collect.py').read_bytes())}
    t.atomic(t.WORK/'ACTIVE_PROCESS.json',runtime);t.atomic(t.WORK/'DEADLINE_WATCHDOG.json',runtime|{'mechanism':'same-process deadline event plus every-operation owner-bound release and bounded HTTP deadline','deadline_check_before_every_request':True})
    def watchdog():
        if not stop_event.wait(max(0,end-time.time())):stop_event.set()
    threading.Thread(target=watchdog,daemon=True).start()
    signal.signal(signal.SIGINT,lambda *_:stop_event.set())
    with t.writer():
        try:
            while not stop_event.is_set():
                t.release()
                if (t.WORK/'MAINTENANCE_STOP_REQUEST.json').exists():reason='complete_native_peak_reservation_violation';break
                try:flush_metadata()
                except t.Stop as exc:
                    if not str(exc).startswith('resource_stop'):raise
                    t.append(t.WORK/'METADATA_PENDING.jsonl',{'at_utc':t.utc(),'reason':str(exc)})
                runnable=[c for c in cs if c['state']=='active' and c['defer_until']<=time.time()]
                candidates=[]
                for c in runnable:
                    url,route,unit=job(c,fs[c['frame']])
                    if url:candidates.append((c,url,route,unit))
                    else:c['state']='native_observed_queue_drained' if c.get('index_exhausted') else 'saved_queue_drained_larger_latest_route_deferred'
                if not candidates:
                    if any(c['state']=='active' for c in cs):time.sleep(1);progress(cs);continue
                    changed=False
                    try:changed=flush_metadata(force=True)
                    except t.Stop:pass
                    if changed:
                        for c in cs:
                            if c['state']=='complete_operation_capacity_blocked':c['state']='active'
                        if any(c['state']=='active' for c in cs):continue
                    reason='complete_operation_capacity_failure_across_permitted_small_routes' if any(c['state']=='complete_operation_capacity_blocked' for c in cs) else 'remaining_named_routes_unavailable_or_observed_inventory_drained';break
                # Ageing follows actual bounded source work; cardinality, semantic
                # labels, coverage and parent statistics do not select operations.
                c,url,route,unit=min(candidates,key=lambda x:x[0].get('last_action',0));f=fs[c['frame']]
                c['last_action']=time.time()
                try:
                    rec=t.fetch(url,c['source'],'content',cap=CAP)
                    if rec['status']!='saved':
                        isolated=rec.get('http_status')==404 and not rec.get('retry_after')
                        bounded=rec['status']=='transport_stop' and 'raw_object_cap_stop' in rec.get('error','')
                        if isolated or bounded:skip_item(c,f,route,unit,rec)
                        else:c['state']='preserved_source_stop';c['stop']=rec
                        continue
                    if route=='session_topic':rows,data=thesession_adapter.records(t.payload(rec),url)
                    elif route=='session_index':rows,data=thesession_adapter.index(t.json_payload(rec))
                    else:
                        data=t.json_payload(rec)
                        if data.get('error') or data.get('errors'):raise t.Stop('native_api_error_response')
                        rows=[] if route=='created_index' else e.discourse(data,c['source'],f['base'],f['license'])
                    result=e.load(rows,rec,c['frame']);advance(c,f,data,route,unit,rows)
                    dates=[r['native_created_at'] for r in rows if r.get('native_created_at')]
                    if dates:c['oldest_returned_publication_at']=min(dates+[c.get('oldest_returned_publication_at') or min(dates)])
                    c['new_core_bodies']+=result['new_qualified_posts']
                    t.append(t.WORK/'NATIVE_RECONCILIATION_OVERLAY.jsonl',{'at_utc':t.utc(),'frame':c['frame'],'request_id':rec['request_id'],'native_route':route,'native_unit':unit,'state':'parsed_and_durably_committed','committed_native_keys':sorted(e.key(r) for r in rows),'returned_entities':len(rows),'new_core_bodies':result['new_qualified_posts'],'root_seen_is_not_thread_complete':True,'native_next_url':c.get('native_next_url'),'old_queue_reference_only':True})
                    print(json.dumps({'at_utc':t.utc(),'source':c['source'],'route':route,'new_core':result['new_qualified_posts'],'phase_core':t.state()['new_core_bodies']}),flush=True)
                except t.Stop as exc:
                    why=str(exc)
                    if why.startswith('resource_stop'):
                        c['state']='complete_operation_capacity_blocked';c['stop']=why
                        t.append(t.WORK/'CAPACITY_BLOCKED_OPERATIONS.jsonl',{'at_utc':t.utc(),'frame':c['frame'],'url':url,'native_unit':unit,'reason':why,'remaining_routes_continue':True})
                    elif why.startswith('server_backoff_until'):c['defer_until']=float(why.rsplit(' ',1)[1])
                    elif why=='fixed_deadline':raise
                    else:c['state']='preserved_source_stop';c['stop']=why
                finally:t.atomic(CUR,cs);progress(cs)
            reason=reason or 'fixed_deadline'
        except t.Stop as exc:reason=str(exc)
        except Exception as exc:
            reason='integrity_or_runtime_failure';t.atomic(t.WORK/'FAILURE.json',{'at_utc':t.utc(),'error':type(exc).__name__+': '+str(exc)});raise
        finally:
            stop_event.set();t.atomic(CUR,cs);progress(cs,reason);t.atomic(t.WORK/'RUN_STOP.json',{'at_utc':t.utc(),'pid':os.getpid(),'reason':reason,'deadline_preserved':True})

if __name__=='__main__':run()
