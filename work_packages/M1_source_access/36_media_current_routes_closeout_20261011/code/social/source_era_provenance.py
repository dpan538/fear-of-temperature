"""Derived launch/date provenance; never alter native dates, bodies or eligibility."""
import datetime as dt,json
import transport as t,entities as e

def migration_facts(fields):
    facts={}
    for name in ('migrated_from','migrated_to'):
        item=fields.get(name)
        if not isinstance(item,dict):continue
        site=item.get('other_site') or {}
        facts[name]={'on_date_native_value':item.get('on_date'),'question_id':item.get('question_id'),'other_site':{k:site[k] for k in ('api_site_parameter','site_url','name','site_type','closed_beta_date','open_beta_date','launch_date') if k in site},'original_external_passage_fetched_or_verified':False,'evidence_basis':'literal current native API migration field; historical body identity not independently checked'}
    return facts

def limitations(source,native_date,fields=None):
    beta=source.get('existence_at');basis=source.get('existence_basis','')
    if 'closed_beta_date' not in basis or not beta or not native_date:return {}
    before=dt.datetime.fromisoformat(native_date.replace('Z','+00:00'))<dt.datetime.fromisoformat(beta.replace('Z','+00:00'))
    result={'native_creation_before_documented_beta':before,'documented_closed_beta_at':beta,'documented_beta_basis':basis,'historical_community_membership_at_creation':'unresolved_before_documented_beta' if before else 'not_independently_verified','migration_explanation':'possible_not_verified' if before else 'not_attributed','native_date_and_body_retained':True}
    facts=migration_facts(fields or {})
    if facts:
        result['native_provider_migration_metadata']=facts
        result['migration_explanation']='native_provider_reports_migration; original_historical_body_not_independently_verified'
        if 'migrated_from' in facts:result['historical_community_membership_at_creation']='native_provider_reports_other_site_origin; original_passage_unverified'
    return result

def repair_changed_annotations(registry,bound,begin):
    total=0;checked=0;cursor=bound;peaks=[]
    sids=[sid for sid,s in registry.items() if 'closed_beta_date' in s.get('existence_basis','')]
    while sids:
        with t.shared(t.footprint(),inflight_at=begin):
            c=e.db()
            rows=c.execute('SELECT v.rowid,v.entity_version_id,n.source_id,n.native_created_at,a.temporal_limitations_json,v.native_fields_json FROM entity_versions v JOIN native_entities n ON n.entity_id=v.entity_id JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE v.rowid>? AND n.source_id IN ('+','.join('?' for _ in sids)+') ORDER BY v.rowid LIMIT 100',(cursor,*sids)).fetchall();c.close()
        if not rows:break
        pending=sum(len(str(x).encode()) for row in rows for x in row)*16+64*1048576
        with t.shared(pending,inflight_at=begin):
            c=e.db();before_bytes=t.DB.stat().st_size;peak=0
            with c:
                for rowid,vid,sid,date,old,fields in rows:
                    checked+=1;prior=json.loads(old);derived=limitations(registry[sid],date,json.loads(fields));new=prior|derived
                    if new!=prior:
                        t.append(t.WORK/'SOURCE_ERA_ANNOTATION_DERIVATIONS.jsonl',{'entity_version_id':vid,'prior_limitations':prior,'derived_limitations':derived,'native_date_preserved':date,'body_read':False})
                        c.execute('UPDATE entity_quality_annotations SET temporal_limitations_json=? WHERE entity_version_id=?',(json.dumps(new,ensure_ascii=False),vid));total+=1
                    journal=t.DB.with_name(t.DB.name+'-journal');peak=max(peak,journal.stat().st_size if journal.exists() else 0)
            c.close();actual=peak+max(0,t.DB.stat().st_size-before_bytes);peaks.append(actual)
            if actual>pending:raise t.Stop('source_era_metadata_peak_exceeded_reservation')
        cursor=rows[-1][0]
    proof={'at_utc':t.utc(),'checked_changed_versions':checked,'derived_annotations_updated':total,'append_rowid_bound':bound,'old_body_reads':0,'body_or_native_date_changes':0,'max_observed_complete_peak_bytes':max(peaks,default=0),'source_existence_not_backdated':True,'historical_migration_unverified':True}
    t.atomic(t.WORK/'SOURCE_ERA_ANNOTATION_REPAIR.json',proof);return proof


_beta_limitations = limitations
def limitations(source,native_date,fields=None):
    result=_beta_limitations(source,native_date,fields)
    fields=fields or {}
    platform=source.get('platform')
    datebasis={'Bluesky':'source-returned AT record.createdAt; client-supplied publication/creation value, not independent historical verification','Mastodon':'source-returned status.created_at; federated/original-host equivalence separately pending','WordPress.com':'native post.date publication field; author-editable, separate from modified and retrieval time','self_hosted_WordPress':'native post.date and date_gmt; author-controlled migrated publication field, separate from modified/modified_gmt and retrieval','self_hosted_author_HTML':'source-visible original-permalink date; timezone and historical body/version separately unresolved','Neocities':'source-visible native permalink publication date; current rendition and remixed older works remain distinct','Blogger_author_published_HTML':'native post published metadata on author HTML; updated and retrieval times separate'}.get(platform,'source-native creation/publication field')
    evidence=fields.get('source_expansion_evidence',{})
    result.update({'publication_time_basis':datebasis,'native_date_not_independently_verified_against_historical_original':True,'author_country_evidence_is_observation_time_not_historical_publication_location':True,'author_identity_independently_verified':False,'profile_metadata_timestamp_not_verified_account_inception':platform in ('Bluesky','Mastodon'),'source_context_observed_at':evidence.get('source_context_observed_at'),'historical_source_context_equivalence':'unresolved; current source/instance context does not prove historical author location','current_retention_admission_does_not_certify_historical_body_version':True})
    return result


_context_aware_limitations = limitations
_source_context_evidence = t.read_json(t.WORK/'SOURCE_CONTEXT_EVIDENCE.json',{})
_profile_by_cohort={a['cohort_id']:a.get('observed_at') for a in t.read_json(t.WORK/'ACTOR_COHORTS.json',[])}
def limitations(source,native_date,fields=None):
    result=_context_aware_limitations(source,native_date,fields)
    context=_source_context_evidence.get(source.get('source_id'))
    if context:
        result['source_context_recorded_observed_at']=result.get('source_context_observed_at')
        evidence=(fields or {}).get('source_expansion_evidence',{})
        result['profile_observed_at']=evidence.get('profile_observed_at') or _profile_by_cohort.get(evidence.get('cohort_id'))
        result['source_context_observed_at']=context['source_context_observed_at']
        result['source_context_evidence_ref']=context['source_context_evidence_ref']
        result['source_context_current_profile_retrieval_does_not_refresh_location_evidence']=True
    return result
