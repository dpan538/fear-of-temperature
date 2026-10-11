"""Nonsemantic directory cohorts and full native account-history pagination."""
import datetime as dt,importlib,json,os,re,time,urllib.parse
import transport as t,entities as e,evidence_observer as observer,personal_blog_adapter as blogs,blogger_channel,native_web_channel,ready_scheduler
CUR=t.WORK/'NATIVE_CURSORS.json';ACT=t.WORK/'ACTOR_COHORTS.json';DISC=t.WORK/'DISCOVERY_CURSORS.json'
REGIONS={'mastodon_ie':('IE','Europe_excluding_UK'),'mastodon_uk':('GB','UK'),'mastodon_au':('AU','AU'),'mastodon_us':('US','US'),'bluesky':('global','global')}
SOURCE_CONTEXT=t.read_json(t.WORK/'SOURCE_CONTEXT_EVIDENCE.json',{})
_native_revision=None

def load_native_revision():
    """Owner-verified adapters reload only between complete operations."""
    global _native_revision
    path=t.WORK/'APPROVED_NATIVE_ADAPTER_REVISION.json'
    if not path.exists():return
    proof=t.read_json(path);revision=t.sha(path.read_bytes())
    if revision==_native_revision:return
    assert proof['passed'] and proof['scope_sha256']==t.sha(t.SCOPE_PATH.read_bytes()) and proof['fixed_deadline']==t.release()['hard_deadline_at_utc']
    modules=['native_web_adapter','native_html_adapter','native_web_channel','blogger_adapter','blogger_channel']
    assert set(proof['code_sha256'])=={m+'.py' for m in modules}
    for name in modules:assert t.sha((t.WORK/(name+'.py')).read_bytes())==proof['code_sha256'][name+'.py']
    importlib.invalidate_caches()
    for name in modules:importlib.reload(importlib.import_module(name))
    _native_revision=revision
    t.append(t.WORK/'NATIVE_ADAPTER_HOTLOAD.jsonl',{'at_utc':t.utc(),'proof_revision_sha256':revision,'operation_boundary':True,'same_writer_pid':os.getpid(),'scope_deadline_and_counters_unchanged':True})

def save_frontiers(items):
    """Serialize prospective native frontier copies under the shared I/O guard."""
    sizes=[len((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()) for _,value in items]
    before=[path.stat().st_size if path.exists() else 0 for path,_ in items]
    reserved=t.footprint()+sum(sizes)
    begin=t.read_json(t.SCOPE_PATH)['earliest_network_and_load_start_at_utc']
    with t.shared(reserved,inflight_at=begin):
        growth=peak=0
        for (path,value),size,old in zip(items,sizes,before):
            peak=max(peak,growth+size)
            t.atomic(path,value);assert path.stat().st_size==size
            growth+=max(0,size-old)
        assert peak<=reserved
        t.append(t.WORK/'FRONTIER_WRITE_CAPACITY.jsonl',{'at_utc':t.utc(),'files':[p.name for p,_ in items],'serialized_bytes':sizes,'observed_atomic_coexistence_upper_bytes':peak,'reserved_operation_bytes':reserved,'shared_lock_held':True,'existing_bytes_already_charged':True})

def block(source,route,reason,receipt=None):
    t.append(t.WORK/'ROUTE_BLOCKS.jsonl',{'at_utc':t.utc(),'source_id':source,'route':route,'reason':reason,'receipt_id':(receipt or {}).get('request_id'),'status':(receipt or {}).get('status'),'error':(receipt or {}).get('error')})

def role(profile):
    bio=t.clean(profile.get('description',profile.get('note','')))
    if profile.get('bot') or re.search(r'\b(bot|diagnostic|test account|automated account)\b',bio+' '+profile.get('displayName',profile.get('display_name','')),re.I):return 'automated_or_test_self_presentation'
    if re.search(r'\b(official account|we specialize|our company|newsroom|agency|organisation|organization|corporation|university department)\b',bio,re.I):return 'institutional_self_presentation'
    if re.search(r"\b(I|my|me|je suis|retired|photographer|artist|mum|dad|writer|student|he/him|she/her|they/them)\b",bio,re.I) or re.search(r'\b\d{2}\b.{0,80}\b(Australia|Ireland|United Kingdom|New Zealand|United States)\b',bio,re.I):return 'individual_self_presentation'
    return 'unknown_profile_role'

def geography(profile,source,rec):
    bio=t.clean(profile.get('description',profile.get('note','')))+' '+t.clean(' '.join(str(x.get('value','')) for x in profile.get('fields',[])))
    countries=[]
    # Only explicit country strings; city/language/server/name are never used.
    for country,pattern in [('AU',r'\bAustralia\b'),('IE',r'\bIreland\b'),('GB',r'\bUnited Kingdom\b|\bUK\b'),('NZ',r'\bNew Zealand\b'),('US',r'\bUnited States\b|\bUSA\b'),('CA',r'\bCanada\b'),('DE',r'\bGermany\b'),('FR',r'\bFrance\b')]:
        if re.search(pattern,bio,re.I):countries.append(country)
    # Country mention is a candidate only until reviewed as a self-location.
    sourcecountry,region=REGIONS.get(source,('unknown','unknown'))
    context=SOURCE_CONTEXT.get(source,{})
    return {'source_context_country':sourcecountry,'source_context_region':region,'source_context_evidence_ref':context.get('source_context_evidence_ref','inherited source_registry.json admission'),'source_context_observed_at':context.get('source_context_observed_at',rec['retrieved_at']),'profile_observed_at':rec['retrieved_at'],'community_context_scope':'regional_instance_open_membership' if source.startswith('mastodon') else 'global_platform_native_account_graph; exact membership route retained in receipt','author_country':'unknown','author_country_status':'unmeasured' if not countries else 'ambiguous','author_country_evidence_type':'unmeasured' if not countries else 'explicit_country_mention_pending_self_location_review','author_country_evidence_ref':rec['raw_reference'],'author_country_observed_at':rec['retrieved_at'],'explicit_country_candidates':countries}

def admit(profile,source,rec,index,cursors,actors,discovery_route=None):
    aid=profile.get('did') or str(profile.get('id'));cohort=source+':directory:'+aid
    if any(a['cohort_id']==cohort for a in actors):return
    r=role(profile)
    geo=geography(profile,source,rec)
    # Explicit source-visible profile, reviewed country statement for first AU actor.
    if source=='bluesky' and aid=='did:plc:wa77blfapgw2nyqdk6hxuzs3':geo.update(author_country='AU',author_country_status='self_declared',author_country_evidence_type='profile explicitly states New South Wales, Australia')
    actor={'cohort_id':cohort,'source_id':source,'actor_id':aid,'handle':profile.get('handle',profile.get('acct')),'carrier':'microblog','genre':'short_post','role_status':r,'profile_native_evidence':profile,'profile_receipt':rec['request_id'],'profile_raw_reference':rec['raw_reference'],'observed_at':rec['retrieved_at'],'directory_position':index,'selection_rule':'native public directory/follower ordering; source-visible individual self-presentation; no body/topic/emotion filter','parent_independence':'unresolved',**geo}
    if discovery_route:
        actor['discovery_route']={k:discovery_route.get(k) for k in ('anchor','directory_kind','order','selection_rule','anchor_cohort_id','graph_bias')}
    actors.append(actor)
    created=profile.get('createdAt',profile.get('created_at'))
    state='profile_role_pending' if r=='unknown_profile_role' else 'excluded_from_ordinary_account_queue' if r in ('automated_or_test_self_presentation','institutional_self_presentation') else 'active'
    # Profile metadata timestamp is not independently verified account inception.
    cursor_profile_time=created
    cursor={'source_id':source,'actor_id':aid,'cohort_id':cohort,'carrier':'microblog','genre':'short_post','page':0,'cursor':None,'max_id':None,'state':state,'oldest_publication':None,'new_core_bodies':0,'returned_native_rows':0,'profile_receipt':rec['request_id'],'ready_at_utc':t.utc()}
    cursors.append(cursor)

def discoveries():
    d=t.read_json(DISC)
    if d is not None:return d
    return [{'source_id':s['source_id'],'base_url':s['base_url'],'page':0,'offset':0,'cursor':None,'state':'active'} for s in t.read_json(t.WORK/'source_registry.json') if s.get('collection_retention')=='permitted']

def discovery(d,cursors,actors):
    sid=d['source_id']
    if sid=='bluesky':
        args={'actor':d.get('anchor','bsky.app'),'limit':100}
        if d['cursor']:args['cursor']=d['cursor']
        url='https://public.api.bsky.app/xrpc/app.bsky.graph.'+('getFollows' if d.get('directory_kind')=='follows' else 'getFollowers')+'?'+urllib.parse.urlencode(args)
    else:url=d['base_url']+'/api/v1/directory?'+urllib.parse.urlencode({'local':'true','order':d.get('order','new'),'limit':80,'offset':d['offset']})
    try:r=t.fetch(url,sid,'source_metadata')
    except t.Stop as exc:
        if str(exc).startswith(('resource_stop','fixed_deadline')):raise
        d['state']='unavailable';block(sid,url,str(exc));return
    if r['status']!='saved':d['state']='unavailable';block(sid,url,'native_directory_unavailable',r);return
    data=t.json_payload(r);profiles=data if isinstance(data,list) else data.get('follows',[]) if d.get('directory_kind')=='follows' else data.get('followers',[])
    if not profiles:d['state']='native_directory_exhausted';return
    for i,a in enumerate(profiles):admit(a,sid,r,d['offset']+i,cursors,actors,d)
    d['page']+=1;d['offset']+=len(profiles)
    if sid=='bluesky':
        nc=data.get('cursor')
        if not nc or nc==d['cursor']:d['state']='native_directory_exhausted'
        d['cursor']=nc
    d['last_request']=r['request_id']
    save_frontiers([(ACT,actors)])

def add_evidence(rows,cursor,actors):
    by={(a['source_id'],a['actor_id']):a for a in actors}
    for row in rows:
        actor=by.get((row['source_id'],row.get('author_id')))
        meta={k:actor[k] for k in ['cohort_id','carrier','genre','source_context_country','source_context_region','source_context_evidence_ref','source_context_observed_at','community_context_scope','author_country','author_country_evidence_type','author_country_evidence_ref','author_country_observed_at','author_country_status']} if actor else {'carrier':'microblog','genre':'short_post','cohort_id':'embedded_context_outside_selected_cohort','source_context_country':REGIONS.get(row['source_id'],('unknown','unknown'))[0],'source_context_region':REGIONS.get(row['source_id'],('unknown','unknown'))[1],'author_country':'unknown','author_country_status':'unmeasured'}
        if actor:
            row['author_role']='ordinary_public_self_presentation' if actor['role_status']=='individual_self_presentation' else 'unknown'
            meta['role_evidence_ref']=actor['profile_raw_reference'];meta['role_status']=actor['role_status']
        meta['profile_observed_at']=actor.get('observed_at') if actor else None
        if row['source_id'] in SOURCE_CONTEXT:meta.update({k:SOURCE_CONTEXT[row['source_id']][k] for k in ('source_context_observed_at','source_context_evidence_ref')})
        row.setdefault('native_fields',{})['source_expansion_evidence']=meta

def collect(cursor,actors):
    scope=t.release()
    if scope.get('new_source_admission_allowed') is False:
        frozen=t.read_json(t.REPO/scope['route_allowlist_reference'])
        assert cursor['source_id'] in frozen['source_ids'] and cursor['cohort_id'] in frozen['cohort_ids']
    if cursor.get('adapter')=='native_web':
        try:native_web_channel.collect(cursor,actors,cursors_state)
        except t.Stop as exc:
            if str(exc).startswith(('resource_stop','fixed_deadline')):raise
            cursor['state']='native_route_unavailable';block(cursor['source_id'],cursor.get('url'),str(exc))
        return
    if cursor.get('adapter')=='blogger_html':
        try:blogger_channel.collect(cursor,actors,cursors_state)
        except t.Stop as exc:
            if str(exc).startswith(('resource_stop','fixed_deadline')):raise
            cursor['state']='native_route_unavailable';block(cursor['source_id'],cursor.get('url'),str(exc))
        return
    sid=cursor['source_id'];source=next(s for s in t.read_json(t.WORK/'source_registry.json') if s['source_id']==sid)
    if cursor.get('carrier')=='personal_blog':
        url=blogs.job(cursor)
    elif sid=='bluesky':
        args={'actor':cursor['actor_id'],'limit':100,'filter':'posts_with_replies','includePins':'false'}
        if cursor['cursor']:args['cursor']=cursor['cursor']
        url='https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?'+urllib.parse.urlencode(args)
    else:
        args={'limit':40,'exclude_reblogs':'false','exclude_replies':'false'}
        if cursor['max_id']:args['max_id']=cursor['max_id']
        url=source['base_url']+'/api/v1/accounts/'+cursor['actor_id']+'/statuses?'+urllib.parse.urlencode(args)
    try:r=t.fetch(url,sid,'content')
    except t.Stop as exc:
        if str(exc).startswith(('resource_stop','fixed_deadline')):raise
        cursor['state']='unavailable';block(sid,url,str(exc));return
    if r['status']!='saved':
        if cursor.get('carrier')=='personal_blog' and 'raw_object_cap_stop' in r.get('error','') and cursor.get('number',50)>1:
            cursor['number']=max(1,cursor.get('number',50)//2);cursor['state']='active';block(sid,url,'whole_native_batch_size_reduced_after_actual_response_cap',r);return
        cursor['state']='unavailable';block(sid,url,'native_actor_feed_unavailable',r);return
    data=t.json_payload(r)
    if cursor.get('carrier')=='personal_blog':rows=blogs.records(data,cursor,next(a for a in actors if a['cohort_id']==cursor['cohort_id']),source)
    else:
        rows=e.bluesky(data) if sid=='bluesky' else e.mastodon(data,sid)
        add_evidence(rows,cursor,actors)
    if rows:
        result=e.load(rows,r,cursor['cohort_id'])
        if any(t.WORK.glob('MAINTENANCE_STOP_REQUEST.json')):raise t.Stop('observed_complete_operation_peak_exceeded_reserve')
        # Observer exceptions are never allowed to hide a missing changed-body ledger.
        if (t.WORK/'TELEMETRY_ERRORS.jsonl').exists():raise t.Stop('changed_body_evidence_observer_failure')
        cursor['new_core_bodies']+=result['new_qualified_posts'];cursor['returned_native_rows']+=len(rows)
        dates=[x['native_created_at'] for x in rows if x.get('native_created_at')]
        if dates:cursor['oldest_publication']=min(dates+[cursor['oldest_publication']] if cursor['oldest_publication'] else dates)
        if result['new_qualified_posts'] and not (t.WORK/'FIRST_NONFORUM_AUTHORED_BODY_LOAD.json').exists():
            t.atomic(t.WORK/'FIRST_NONFORUM_AUTHORED_BODY_LOAD.json',{'at_utc':t.utc(),'owner':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'load':result,'request':{k:r[k] for k in ['request_id','url','retrieved_at','raw_reference','raw_sha256']},'actor_cursor':cursor,'new_real_authored_bodies':result['new_qualified_posts'],'not_directory_or_container':True,'capacity':t.read_json(t.WORK/'LAST_CAPACITY.json')})
    old=cursor.get('page_handle') if cursor.get('carrier')=='personal_blog' else cursor['cursor'] if sid=='bluesky' else cursor['max_id']
    new=(data.get('meta') or {}).get('next_page') if cursor.get('carrier')=='personal_blog' else data.get('cursor') if sid=='bluesky' else (min((str(p['id']) for p in data),key=int) if data else None)
    if cursor.get('carrier')=='personal_blog':
        cursor['reported_found']=data.get('found');cursor['page_handle']=new
        if not new and data.get('posts') and len(data['posts'])==cursor.get('number',50):new='page_offset_fallback_'+str(cursor['page']+1)
    if not new or new==old:cursor['state']='returned_history_exhausted_at_observation'
    elif cursor.get('carrier')=='personal_blog':pass
    elif sid=='bluesky':cursor['cursor']=new
    else:cursor['max_id']=new
    cursor['page']+=1;cursor['last_request']=r['request_id'];cursor['last_load_at_utc']=t.state().get('last_successful_load_at_utc')
    print(json.dumps({'at_utc':t.utc(),'source':sid,'actor':cursor['actor_id'],'page':cursor['page'],'new_bodies':t.state()['new_core_bodies'],'oldest':cursor['oldest_publication'],'state':cursor['state']}),flush=True)

def main():
    global discoveries_state,cursors_state
    t.release();assert t.read_json(t.WORK/'START_LIVE_PREFLIGHT.json')['passed']
    assert t.read_json(t.WORK/'ACTIVE_SOURCE_ROUTE_PLAN.json')['technical_list_scheduled_routes']==0
    current_only=t.release().get('new_source_admission_allowed') is False
    discoveries_state=t.read_json(DISC,[]) if current_only else discoveries();cursors_state=t.read_json(CUR,[]);actors=t.read_json(ACT,[])
    frozen=t.read_json(t.REPO/t.release()['route_allowlist_reference']) if current_only else None
    with t.writer():
        t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'deadline':t.release()['hard_deadline_at_utc']})
        try:
            if not current_only and not (t.WORK/'PERSONAL_BLOG_PREPARATION_COMPLETE.json').exists():
                blogs.prepare(cursors_state,actors,block)
                t.atomic(t.WORK/'PERSONAL_BLOG_PREPARATION_COMPLETE.json',{'at_utc':t.utc(),'admitted':sum(a.get('carrier')=='personal_blog' for a in actors),'comments':'pending commenter-specific retention; no automatic site-owner license inheritance'})
            if not current_only:
                if blogger_channel.incorporate(cursors_state,actors):save_frontiers([(ACT,actors),(CUR,cursors_state)])
                if native_web_channel.incorporate(cursors_state,actors):save_frontiers([(ACT,actors),(CUR,cursors_state)])
            request_rows=[]
            if (t.WORK/'REQUESTS.jsonl').exists():
                with (t.WORK/'REQUESTS.jsonl').open() as f:request_rows=[json.loads(line) for line in f]
            scheduler=ready_scheduler.Queue(t.read_json(t.WORK/'SCHEDULER_STATE.json'),request_rows)
            while True:
                t.release()
                if not current_only:
                    load_native_revision()
                    if native_web_channel.incorporate(cursors_state,actors):save_frontiers([(ACT,actors),(CUR,cursors_state)])
                registry={s['source_id']:s for s in t.read_json(t.WORK/'source_registry.json')}
                content=[c for c in cursors_state if c['source_id'] in frozen['source_ids'] and c['cohort_id'] in frozen['cohort_ids']] if current_only else cursors_state
                jobs=scheduler.jobs(content,[] if current_only else discoveries_state,registry,t.utc(),t.sha)
                if not jobs:
                    if current_only:raise t.Stop('frozen_frontiers_exhausted_or_source_blocked_at_observation; retained_states_not_archive_completeness')
                    raise t.Stop('all_current_native_account_frontiers_unavailable_or_exhausted; alternate_blog_routes_required')
                st=t.state();spacing={sid:max(t.release()['minimum_host_spacing_seconds'],s.get('minimum_spacing_seconds',0)) for sid,s in registry.items()}
                provider={j['job_key']:t.provider_backoff_until(st,j['host'],urllib.parse.urlsplit(j['url']).path) for j in jobs}
                job,wait=ready_scheduler.select(jobs,scheduler.state['last_source_attempt_at_utc'],time.time(),st['hosts'],spacing,provider)
                if job is None:time.sleep(min(1,max(.01,wait)));continue
                scheduler.attempted(job,t.utc())
                if job['kind']=='content':collect(job['item'],actors)
                else:discovery(job['item'],cursors_state,actors)
                scheduler.completed(job,t.utc())
                save_frontiers([(CUR,cursors_state),(DISC,discoveries_state),(t.WORK/'SCHEDULER_STATE.json',scheduler.state)])
                observer.progress(cursors_state)
                t.append(t.WORK/'SCHEDULER_OPERATIONS.jsonl',{'at_utc':t.utc(),'job_key':job['job_key'],'source_id':job['source_id'],'kind':job['kind'],'ready_at_utc':job['item']['ready_at_utc'],'last_attempt_at_utc':job['item']['last_attempt_at_utc'],'end_state':job['item']['state'],'reselected_current_frontiers':True})
        except (t.Stop,KeyboardInterrupt) as exc:
            save_frontiers([(CUR,cursors_state),(DISC,discoveries_state)])
            t.atomic(t.WORK/'RUN_STOP.json',{'at_utc':t.utc(),'reason':str(exc) or 'owner_requested_completed_operation_boundary_pause_for_named_route_implementation','pid':os.getpid(),'deadline_unchanged':True})
            observer.progress(cursors_state,phase='source_process_stopped')
            print('STOP '+str(exc),flush=True)

if __name__=='__main__':main()
