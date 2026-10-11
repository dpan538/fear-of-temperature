"""Compact changed-body metadata. Source and author geography stay distinct."""
import collections,json,os
import transport as t,entities as e
_seen=None

def emit(rows,rec,result):
    global _seen
    if _seen is None:
        _seen=set()
        p=t.WORK/'BODY_DELTA.jsonl'
        if p.exists():
            with p.open() as f:
                for line in f:_seen.add(json.loads(line)['persistent_post_id'])
    base=t.read_json(t.WORK/'INHERITED_BASELINE.json');c=e.db()
    for r in rows:
        eid=r.get('persistent_post_id')
        if not eid or eid in _seen:continue
        p=c.execute('SELECT rowid FROM posts WHERE persistent_post_id=?',(eid,)).fetchone()
        if not p or p[0]<=base['counts']['posts']:continue
        meta=dict(r.get('native_fields',{}).get('source_expansion_evidence',{}))
        context=t.read_json(t.WORK/'SOURCE_CONTEXT_EVIDENCE.json',{}).get(r['source_id'])
        if context:meta.update({k:context[k] for k in ('source_context_observed_at','source_context_evidence_ref')})
        item={'persistent_post_id':eid,'source_id':r['source_id'],'native_namespace':r['native_namespace'],'native_id':str(r['native_post_id']),'source_url':r.get('source_url'),'publication_at':r['native_created_at'],'retrieved_at':rec['retrieved_at'],'body_sha256':r['body_sha256'],'request_id':rec['request_id'],'author_id':r.get('author_id'),'author_role':r.get('author_role','unknown'),'native_unit':r['native_unit'],'carrier':meta.get('carrier','microblog'),'genre':meta.get('genre','short_post'),'cohort_id':meta.get('cohort_id','embedded_context_outside_selected_cohort'),'site_id':meta.get('site_id'),'independent_parent_status':'unresolved; native account/site is not proof of independence',**{k:meta.get(k,'unknown') for k in ['source_context_country','source_context_region','source_context_evidence_ref','source_context_observed_at','community_context_scope','author_country','author_country_evidence_type','author_country_evidence_ref','author_country_observed_at','author_country_status']}}
        item['profile_observed_at']=meta.get('profile_observed_at')
        t.append(t.WORK/'BODY_DELTA.jsonl',item);_seen.add(eid)
    c.close()
    if len(_seen)!=t.state()['new_core_bodies']:
        raise t.Stop('changed_body_metadata_counter_mismatch')

def progress(cursors=None,phase='production'):
    s=t.state();b=t.read_json(t.WORK/'INHERITED_BASELINE.json');scope=t.read_json(t.SCOPE_PATH)
    actors=t.read_json(t.WORK/'ACTOR_COHORTS.json',[]);cs=cursors if cursors is not None else t.read_json(t.WORK/'NATIVE_CURSORS.json',[])
    out={'at_utc':t.utc(),'owner_thread_id':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'writer_pid':os.getpid(),'phase':phase,'deadline_at_utc':scope['hard_deadline_at_utc'],'lifetime_requests':s['requests'],'round_requests':s['requests']-b['lifetime_charged_requests'],'lifetime_returned_native_keys':len(s['returned_object_ids']),'new_core_bodies':s['new_core_bodies'],'dated_body_total':b['usable_dated_bodies']+s['new_core_bodies'],'retained_core_total':b['counts']['posts']+s['new_core_bodies'],'new_entities':s['new_entities'],'new_entity_versions':s['new_entity_versions'],'last_http_at_utc':s.get('last_successful_http_at_utc'),'last_load_at_utc':s.get('last_successful_load_at_utc'),'discovered_actor_profiles':sum(a.get('carrier')=='microblog' for a in actors),'ordinary_account_cohorts_with_profile_evidence':sum(a.get('role_status')=='individual_self_presentation' for a in actors),'new_sites_admitted':sum(a.get('carrier')=='personal_blog' for a in actors),'source_mix_new':dict(collections.Counter({k.split('|')[0]:sum(v for q,v in s['source_year_deltas'].items() if q.split('|')[0]==k.split('|')[0]) for k in s['source_year_deltas']})),'technical_list_new_bodies':0,'technical_list_new_requests':0,'technical_list_retained_dated_numerator':613617,'technical_list_current_share':613617/(988701+s['new_core_bodies']),'cursor_states':dict(collections.Counter(c.get('state','active') for c in cs)),'next_executable_routes':[{k:c.get(k) for k in ['source_id','actor_id','carrier','page','cursor','max_id','oldest_publication','state']} for c in cs if c.get('state')=='active'][:12],'blocks_reference':'ROUTE_BLOCKS.jsonl','actor_evidence_reference':'ACTOR_COHORTS.json','source_author_geography_contract':'package35 GEOGRAPHY_CONTRACT.md','stop_reason':t.read_json(t.WORK/'RUN_STOP.json',{}).get('reason') if phase!='production' else None,'capacity':t.read_json(t.WORK/'LAST_CAPACITY.json')}
    t.atomic(t.WORK/'PROGRESS.json',out)
    text=f"# Social source expansion digest\n\nOwner `{t.OWNER}`; scope `{out['scope_sha256']}`; writer PID {os.getpid()}. Fixed deadline {scope['hard_deadline_at_utc']}.\n\nNew independently authored dated bodies: {s['new_core_bodies']:,}; cumulative dated {out['dated_body_total']:,}; requests {out['round_requests']:,} new / {s['requests']:,} lifetime. Last HTTP {out['last_http_at_utc']}; last Load {out['last_load_at_utc']}. Technical-list increment: zero; retained numerator 613,617, current share {out['technical_list_current_share']:.4%}. No topic/affect/fear selection.\n\nAccount/site evidence and author-country unknowns are preserved in ACTOR_COHORTS and BODY_DELTA; cursor states {out['cursor_states']}. Concrete blocks are in ROUTE_BLOCKS. Old phase B STATE/NATIVE_CURSORS and accepted A+B calendar chain remain referenced. Source request/body counts never stop production.\n"
    p=t.WORK/'DIGEST.md';q=p.with_suffix('.md.pending');q.write_text(text);q.replace(p)
    return out
