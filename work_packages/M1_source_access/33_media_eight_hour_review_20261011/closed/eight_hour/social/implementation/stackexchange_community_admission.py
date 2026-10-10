"""Admit named Q&A communities from one saved official network inventory."""
import copy
import datetime as dt
import urllib.parse
import transport as t
import quota_observation as quota

CANDIDATES = {
    'gardening': ('Gardening & Landscaping', 'gardening_and_landscaping_QA'),
    'cooking': ('Seasoned Advice', 'food_and_cooking_QA'),
    'bicycles': ('Bicycles', 'cycling_QA'),
    'travel': ('Travel', 'travel_QA'),
    'outdoors': ('The Great Outdoors', 'outdoor_recreation_QA'),
}

def run_if_ready():
    if (t.WORK/'STACKEXCHANGE_COMMUNITY_ADMISSION_RESULT.json').exists(): return False
    if not quota.native_access_confirmed(t.state()): return False
    name='se_network_site_identity_after_provider_observation'
    results=t.read_json(t.WORK/'PROBE_RESULTS.json', {})
    entry=results.get(name)
    if not entry:
        tasks=t.read_json(t.WORK/'PROBE_TASKS.json', [])
        if not any(x['name']==name for x in tasks):
            # /sites documents an unbounded pagesize and a one-day cache.
            tasks.append({'name':name, 'source':'se_sustainability', 'url':'https://api.stackexchange.com/2.3/sites?pagesize=1000', 'purpose':'source_metadata'})
            t.atomic(t.WORK/'PROBE_TASKS.json', tasks)
        return False
    if entry.get('status')!='saved':
        t.atomic(t.WORK/'STACKEXCHANGE_COMMUNITY_ADMISSION_RESULT.json', {'at_utc':t.utc(), 'status':'native_identity_unavailable', 'evidence':entry, 'candidates_not_contributing':True})
        return False
    rec=t.read_json(t.WORK/'receipts'/(entry['request_id']+'.json'))
    data=t.json_payload(rec)
    if data.get('error_id'):
        t.atomic(t.WORK/'STACKEXCHANGE_COMMUNITY_ADMISSION_RESULT.json', {'at_utc':t.utc(), 'status':'provider_error; no_unverified_admission', 'request_id':rec['request_id'], 'api_error':rec.get('api_error'), 'has_more':data.get('has_more')})
        return False
    registry=t.read_json(t.WORK/'source_registry.json');template=next(x for x in registry if x['source_id']=='se_sustainability')
    fronts=t.read_json(t.WORK/'FRONTIER_ADDITIONS.json');known={x['frame'] for x in fronts};admitted=[];pending=[]
    def date(value):return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat() if isinstance(value,int) else None
    for token,(label,frame) in CANDIDATES.items():
        matches=[s for s in data.get('items',[]) if s.get('api_site_parameter')==token and s.get('site_type')=='main_site' and urllib.parse.urlsplit(s.get('site_url','')).hostname==token+'.stackexchange.com']
        if len(matches)!=1:pending.append({'site':token,'reason':'exact_native_network_identity_unresolved'});continue
        site=matches[0];existence=date(site.get('closed_beta_date'));public_beta=date(site.get('open_beta_date'));launch=date(site.get('launch_date'))
        if not existence:pending.append({'site':token,'reason':'native_era_lower_bound_unresolved'});continue
        start=max(1988,int(existence[:4]));sid='se_'+token;fid=sid+':all_creation_order_native_index'
        source={k:copy.deepcopy(v) for k,v in template.items() if k not in ['observations','existence_at','public_beta_at','launch_at','era_evidence','audience','geographic_evidence']}
        source.update(source_id=sid,title=label,base_url='https://'+token+'.stackexchange.com',frame=frame,source_frame_purpose=frame,stratum='global; individual author country and role unresolved',named_community_frame=True,existence_at=existence,public_beta_at=public_beta,launch_at=launch,era_evidence=rec['url'],audience=site.get('audience'),geographic_evidence='Named global Q&A community; provider carrier location never assigns author country',historical_scope='Provider closed beta, public beta, graduation launch and first retained question are distinct. Current API bodies do not prove historical rendition or historical public access; deleted/private units remain unavailable. Anonymous page limit25 uses inclusive native creation-date partition, preserving ties and IDs.',status='ready_for_native_ELT_after_provider_identity_and_positive_quota_observation',prospective_permission_assessment_at_utc=t.utc())
        source['observations']=[{k:rec.get(k) for k in ['url','purpose','status','http_status','retrieved_at','raw_sha256','raw_reference']}]
        source['inherited_network_policy_reference']={'source_id':'se_sustainability','policy_urls':template['policy_urls'],'network_permission_reused_without_old_body_audit':True}
        source['policy_urls']=list(template['policy_urls'])+['https://'+token+'.stackexchange.com/help/licensing']
        source['content_license']='per_revision_CC_BY_SA; retain returned native content_license field, do not infer current revision licence solely from creation date'
        registry=[x for x in registry if x['source_id']!=sid]+[source]
        if fid not in known:
            fronts.append({'source':sid,'kind':'se_questions','year':start,'page':1,'start_year':start,'context_queue':[],'status':'active','historical_route':True,'ordinary_public_community_need':True,'frame':fid,'selection_rule_evidence':'All public native creation-ordered question/answer/comment returns across observed applicable era and fixed publication cutoff; no topic/affect, count, share or coverage completion gate; same anonymous provider identity, quota and method backoff.'})
        admitted.append({'source_id':sid,'provider_site_name':site['name'],'provider_closed_beta_at':existence,'provider_public_beta_at':public_beta,'provider_graduation_launch_at':launch,'first_retained_native_record_not_yet_claimed':True})
    t.atomic(t.WORK/'source_registry.json', registry)
    limits=t.read_json(t.WORK/'SOURCE_EXPANSION_LIMITS.json')
    for x in admitted:limits[x['source_id']]={'status':'native network identity and era verified; continuing creation-ordered ELT admitted only under positive provider state; real bodies required for contribution counts','network_inventory_request_id':rec['request_id'],'per_revision_licence_and_historical_body_limits':True}
    t.atomic(t.WORK/'SOURCE_EXPANSION_LIMITS.json', limits)
    admission=t.read_json(t.WORK/'NEW_PUBLIC_COMMUNITY_ADMISSIONS.json');admission['source_ids']=sorted(set(admission['source_ids'])|{x['source_id'] for x in admitted});admission['last_amended_at_utc']=t.utc();t.atomic(t.WORK/'NEW_PUBLIC_COMMUNITY_ADMISSIONS.json', admission)
    t.atomic(t.WORK/'FRONTIER_ADDITIONS.json', fronts)
    t.atomic(t.WORK/'STACKEXCHANGE_COMMUNITY_ADMISSION_RESULT.json', {'at_utc':t.utc(),'status':'native_identity_admission_complete','network_inventory_request_id':rec['request_id'],'network_inventory_has_more':data.get('has_more'),'each_admitted_identity_verified_independently_of_inventory_completeness':True,'admitted':admitted,'pending':pending,'same_provider_carrier_not_independent_parent_count':True,'historical_quota_stop_retained':True,'candidate_counts_not_real_contribution_counts':True})
    return bool(admitted)
