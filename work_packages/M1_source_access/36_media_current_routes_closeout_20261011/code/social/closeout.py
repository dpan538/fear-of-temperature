"""Once-only changed-tranche reconciliation and metadata-only publication."""
import collections,csv,gzip,json,os
from pathlib import Path
import transport as t,entities as e,finalize_metadata

def csvfile(name,header,rows):
    p=t.WORK/'summaries'/name;q=p.with_name(p.name+'.pending')
    opener=gzip.open if name.endswith('.gz') else open
    with opener(q,'wt',encoding='utf8',newline='') as f:
        writer=csv.writer(f);writer.writerow(header);writer.writerows(rows)
    q.replace(p);return p

def reference(p):
    return {'path':str(p.relative_to(t.REPO)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())}

def finalize_frames(base):
    """Append missing current native cohort mappings; preserve existing source/frame rows."""
    begin=t.read_json(t.SCOPE_PATH)['earliest_network_and_load_start_at_utc']
    actors={a['cohort_id']:a for a in t.read_json(t.WORK/'ACTOR_COHORTS.json',[])}
    with t.shared(t.footprint(),inflight_at=begin):
        c=e.db()
        frames=c.execute('SELECT DISTINCT o.frame_id,n.source_id FROM entity_observations o JOIN entity_versions v ON v.entity_version_id=o.entity_version_id JOIN native_entities n ON n.entity_id=v.entity_id LEFT JOIN acquisition_frames f ON f.frame_id=o.frame_id WHERE o.rowid>? AND f.frame_id IS NULL',(base['counts']['entity_observations'],)).fetchall()
        c.close()
    prepared=[]
    for fid,sid in frames:
        assert fid in actors and actors[fid]['source_id']==sid
        a=actors[fid]
        fields={k:a.get(k) for k in ('cohort_id','source_id','actor_id','site_id','carrier','genre','role_status','profile_receipt','profile_raw_reference','observed_at','selection_rule','discovery_route','parent_independence')}
        fields['profile_metadata_time_is_not_verified_account_foundation']=True
        prepared.append((fid,sid,'native_personal_blog_history' if a.get('carrier')=='personal_blog' else 'native_public_account_history',a['selection_rule'],None,a.get('role_status','unknown_without_source_evidence'),json.dumps(fields,ensure_ascii=False)))
    added=0;peaks=[]
    for offset in range(0,len(prepared),100):
        batch=prepared[offset:offset+100]
        reserved=finalize_metadata.metadata_footprint(sum(len(str(x).encode()) for row in batch for x in row if x is not None),len(batch))
        with t.shared(reserved,inflight_at=begin):
            c=e.db();before=t.DB.stat().st_size;journal_peak=0
            with c:
                for row in batch:
                    added+=c.execute('INSERT OR IGNORE INTO acquisition_frames VALUES (?,?,?,?,?,?,?)',row).rowcount
                    jp=Path(str(t.DB)+'-journal');journal_peak=max(journal_peak,jp.stat().st_size if jp.exists() else 0)
            c.close();peak=journal_peak+max(0,t.DB.stat().st_size-before)
            assert peak<=reserved;peaks.append(peak)
    receipt={'at_utc':t.utc(),'new_frame_mappings':added,'changed_observation_frame_ids_considered':len(frames),'body_reads':False,'old_source_and_frame_rows_preserved':True,'max_additional_disk_peak_upper_bytes':max(peaks,default=0),'peak_violations':0}
    t.atomic(t.WORK/'CURRENT_COHORT_FRAME_FINALIZATION.json',receipt)
    return receipt

def baseline_calendar(base):
    old=t.REPO/base['predecessor_worker_reference']
    refs=t.read_json(old/'summaries/inherited_metadata_references.json')['references']
    calendar=next(x for x in refs if x['path'].endswith('source_month_calendar.csv'))
    assert t.sha((t.REPO/calendar['path']).read_bytes())==calendar['sha256']
    counts=collections.Counter()
    with (t.REPO/calendar['path']).open() as f:
        for r in csv.DictReader(f):counts[r['source_id'],r['month']]+=int(r['usable_dated_independent_bodies'])
    deltafiles=[t.REPO/x['path'] for x in refs if x['path'].endswith('source_month_deltas.csv')]+[old/'summaries/source_month_deltas.csv']
    seen=set()
    for p in deltafiles:
        if p.resolve() in seen:continue
        seen.add(p.resolve())
        with p.open() as f:
            for r in csv.DictReader(f):counts[r['source_id'],r['month']]+=int(r['new_usable_bodies'])
    assert sum(counts.values())==988701==base['usable_dated_bodies']
    return counts,refs+[reference(old/'summaries/source_month_deltas.csv')]

def main():
    scope=t.read_json(t.SCOPE_PATH);begin=scope['earliest_network_and_load_start_at_utc']
    assert t.read_json(t.WORK/'RUN_STOP.json') and t.read_json(t.WORK/'ADAPTER_STRUCTURAL_REGRESSION.json')['passed']
    base=t.read_json(t.WORK/'INHERITED_BASELINE.json');bounds=base['counts'];old=t.REPO/base['predecessor_worker_reference']
    assert t.sha((old/'CLOSED.json').read_bytes())==base['predecessor_closed_sha256']
    assert t.sha((old/'FINAL_DELIVERY_VERIFICATION.json').read_bytes())==base['predecessor_verification_sha256']
    with t.writer():
        t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'phase':'bounded_changed_tranche_settlement','deadline':scope['hard_deadline_at_utc']})
        frame_receipt=finalize_frames(base)
        meta=finalize_metadata.finalize(batch_records=400)
        model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');model['already_annotated_changed_versions']=meta['quality_annotations'];t.atomic(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json',model)
        st=t.state();prior,refs=baseline_calendar(base);files=[]
        with t.shared(t.footprint(),inflight_at=begin) as capacity:
            c=e.db();c.execute('PRAGMA temp_store=MEMORY')
            for table,key in [('posts','new_core_bodies'),('native_entities','new_entities'),('entity_versions','new_entity_versions')]:
                assert c.execute('SELECT COUNT(*) FROM '+table+' WHERE rowid>?',(bounds[table],)).fetchone()[0]==st[key]
            new_body_versions=c.execute('SELECT COUNT(*) FROM versions WHERE rowid>?',(bounds['versions'],)).fetchone()[0]
            newposts=dict(c.execute('SELECT persistent_post_id,native_created_at FROM posts WHERE rowid>?',(bounds['posts'],)))
            sourcecontexts=t.read_json(t.WORK/'SOURCE_CONTEXT_EVIDENCE.json',{})
            actors=t.read_json(t.WORK/'ACTOR_COHORTS.json',[]);bycohort={a['cohort_id']:a for a in actors}
            ledger=[];seen=set();delta=collections.Counter();carrier=collections.Counter();geo=collections.Counter();authors=collections.Counter();sites=collections.Counter()
            p=t.WORK/'BODY_DELTA.jsonl'
            if p.exists():
                with p.open() as f:
                    for line in f:
                        r=json.loads(line);r['source_context_recorded_observed_at']=r.get('source_context_observed_at')
                        if r['source_id'] in sourcecontexts:r.update({k:sourcecontexts[r['source_id']][k] for k in ('source_context_observed_at','source_context_evidence_ref')})
                        r['author_country_recorded_status']=r.get('author_country_status');r['author_country_historical_at_publication_status']='unmeasured'
                        a=bycohort.get(r.get('cohort_id'),{})
                        r['author_role_observed_at']=a.get('observed_at')
                        r['profile_observed_at']=r.get('profile_observed_at') or a.get('observed_at')
                        r['author_role_evidence_ref']=a.get('profile_raw_reference')
                        r['author_role_historical_at_publication_status']='unmeasured; current self-presentation does not independently verify historical role or identity'
                        if r.get('author_country')=='unknown' and r.get('author_country_status')=='not_stated':r['author_country_status']='unmeasured'
                        eid=r['persistent_post_id'];assert eid not in seen and eid in newposts
                        assert r['publication_at']==newposts[eid] and '1988-01-01'<=r['publication_at'][:10]<='2026-09-21'
                        assert not any(k in r['source_id'] for k in ['python_list','w3talk','mailman'])
                        seen.add(eid);ledger.append(r);delta[r['source_id'],r['publication_at'][:7]]+=1;carrier[r['carrier']]+=1
                        geo[r['source_context_country'],r['source_context_region'],r['publication_at'][:4],r['carrier'],r['genre']]+=1
                        authors[r['author_country'],r['author_country_status'],r['carrier']]+=1
                        if r.get('site_id'):sites[r['site_id']]+=1
            assert len(ledger)==len(newposts)==st['new_core_bodies']
            # Inspect only this tranche's new body bytes once; prior accepted versions use their stored hash reference.
            checked=reused=0
            for body,digest,bodyrow,oldhash in c.execute('SELECT CASE WHEN b.rowid<=? THEN NULL ELSE COALESCE(b.body_original,v.body_original) END,v.body_sha256,b.rowid,b.body_sha256 FROM entity_versions v LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id WHERE v.rowid>?',(bounds['versions'],bounds['entity_versions'])):
                if bodyrow is not None and bodyrow<=bounds['versions']:assert digest==oldhash;reused+=1;continue
                assert (t.sha(body.encode()) if body else None)==digest;checked+=1
            statements={
                'new_native_entities.csv.gz':('SELECT entity_id,source_id,native_namespace,native_id,source_url,native_unit,native_created_at,date_precision,author_id,author_role,first_retrieved_at FROM native_entities WHERE rowid>?',bounds['native_entities']),
                'changed_entity_versions.csv.gz':('SELECT entity_version_id,entity_id,core_body_version_id,body_sha256,native_edited_at,native_revision,content_state,fixed_interval_state,readable_native_unit,independently_authored_body,content_license,licence_basis,flags_json,first_retrieved_at FROM entity_versions WHERE rowid>?',bounds['entity_versions']),
                'new_entity_observations.csv.gz':('SELECT * FROM entity_observations WHERE rowid>?',bounds['entity_observations']),
                'new_relations.csv.gz':('SELECT * FROM native_edges WHERE rowid>?',bounds['native_edges']),
                'new_response_manifest.csv.gz':('SELECT * FROM responses WHERE rowid>?',bounds['responses'])}
            for name,(sql,bound) in statements.items():
                cur=c.execute(sql,(bound,));files.append(csvfile(name,[x[0] for x in cur.description],cur))
            quality=c.execute('SELECT a.* FROM entity_versions v JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE v.rowid>?',(bounds['entity_versions'],))
            files.append(csvfile('changed_source_provenance.csv.gz',[x[0] for x in quality.description],quality))
            frames=c.execute('SELECT DISTINCT f.* FROM entity_observations o JOIN acquisition_frames f ON f.frame_id=o.frame_id WHERE o.rowid>?',(bounds['entity_observations'],))
            files.append(csvfile('changed_native_acquisition_frames.csv.gz',[x[0] for x in frames.description],frames))
            memberships=c.execute('SELECT m.* FROM publication_memberships m JOIN posts p ON p.persistent_post_id=m.entity_id WHERE p.rowid>?',(bounds['posts'],));files.append(csvfile('new_body_publication_memberships.csv.gz',[x[0] for x in memberships.description],memberships))
            native_uri_works=c.execute("SELECT COUNT(DISTINCT m.publication_key) FROM publication_memberships m JOIN posts p ON p.persistent_post_id=m.entity_id WHERE p.rowid>? AND m.publication_key LIKE 'native_original_uri:%'",(bounds['posts'],)).fetchone()[0];c.close()
            header=list(ledger[0]) if ledger else ['persistent_post_id','source_id','publication_at','carrier']
            files.append(csvfile('new_authored_body_metadata.csv.gz',header,([r.get(k) for k in header] for r in ledger)))
            current=prior+delta
            files.append(csvfile('source_month_deltas.csv',['source_id','month','baseline_usable_bodies','new_usable_bodies','current_usable_bodies','reporting_only'],([s,m,prior[s,m],n,current[s,m],1] for (s,m),n in sorted(delta.items()))))
            files.append(csvfile('country_era_carrier_deltas.csv',['source_context_country','source_context_region','year','carrier','genre','new_usable_bodies'],([*k,n] for k,n in sorted(geo.items()))))
            files.append(csvfile('author_country_missingness.csv',['author_country','author_country_status','carrier','new_usable_bodies'],([*k,n] for k,n in sorted(authors.items()))))
            for a in actors:
                a['profile_observed_at']=a.get('observed_at')
                if a['source_id'] in sourcecontexts:a.update({k:sourcecontexts[a['source_id']][k] for k in ('source_context_observed_at','source_context_evidence_ref')})
                if a.get('author_country')=='unknown' and a.get('author_country_status')=='not_stated':a['author_country_status']='unmeasured'
            cursors=t.read_json(t.WORK/'NATIVE_CURSORS.json',[])
            category_candidates=collections.Counter((r['source_id'],r['state']) for r in cursors if r.get('route_type')=='permalink' and '/category/' in r.get('url',''))
            for a in actors:a['discovery_route_json']=json.dumps(a.get('discovery_route'),ensure_ascii=False)
            header=['cohort_id','source_id','actor_id','site_id','carrier','genre','role_status','profile_receipt','profile_raw_reference','observed_at','profile_observed_at','selection_rule','discovery_route_json','source_context_country','source_context_region','source_context_evidence_ref','source_context_observed_at','community_context_scope','author_country','author_country_status','author_country_evidence_type','author_country_evidence_ref','author_country_observed_at','parent_independence']
            files.append(csvfile('actor_site_cohorts.csv.gz',header,([a.get(k) for k in header] for a in actors)))
            import new_source_contribution
            files.extend(new_source_contribution.export(ledger,csvfile))
            frontier=collections.Counter((r['source_id'],r.get('carrier'),r['state']) for r in cursors)
            frozen=t.read_json(t.REPO/scope['route_allowlist_reference'],{}) if scope.get('new_source_admission_allowed') is False else {}
            files.append(csvfile('source_history_frontier_counts.csv',['source_id','carrier','native_history_state','account_or_site_units','allowed_in_amended_frozen_route_scope','interpretation'],([*k,n,k[0] in frozen.get('source_ids',[]) if frozen else True,'source-returned pagination state at observation; not archive completeness'] for k,n in sorted(frontier.items()))))
            allmonths=[f'{y:04}-{m:02}' for y in range(1988,2027) for m in range(1,13) if f'{y:04}-{m:02}'<='2026-09'];neighbors=[]
            for (s,m),n in sorted(delta.items()):
                i=allmonths.index(m);before=[current[s,q] for q in allmonths[max(0,i-3):i]];after=[current[s,q] for q in allmonths[i+1:i+4]];context=before+after
                neighbors.append([s,m,prior[s,m],n,current[s,m],json.dumps(before),json.dumps(after),int(len(context)<6 or i>=len(allmonths)-4),int(bool(context) and current[s,m]>max(context)),'none; independent dated event evidence required'])
            files.append(csvfile('changed_source_month_neighbor_context.csv',['source_id','month','baseline_count','delta_count','current_count','previous_three_counts','following_three_counts','incomplete_boundary_context','greater_than_available_neighbors_candidate','event_attribution'],neighbors))
            newmonths=sorted({m for (s,m),n in current.items() if n}-{m for (s,m),n in prior.items() if n})
            snapshot={'at_utc':t.utc(),'owner_thread_id':t.OWNER,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'authorized_start':begin,'fixed_deadline':scope['hard_deadline_at_utc'],'stop':t.read_json(t.WORK/'RUN_STOP.json'),'publication_interval':scope['publication_interval'],'september_partial':True,'new_core_texts':st['new_core_bodies'],'new_usable_dated_bodies':len(ledger),'retained_core_total':988717+len(ledger),'usable_dated_body_total':988701+len(ledger),'pooled_observed_months':343+len(newmonths),'new_pooled_months':newmonths,'new_entities':st['new_entities'],'new_entity_versions':st['new_entity_versions'],'new_body_versions':new_body_versions,'body_versions_total':bounds['versions']+new_body_versions,'source_returned_original_URI_work_keys_among_new_bodies':native_uri_works,'URI_original_external_body_verification':'pending; distinct native rows are not proven independent publishers','native_entities_total':1037756+st['new_entities'],'entity_versions_total':1204490+st['new_entity_versions'],'round_charged_requests':st['requests']-13339,'lifetime_charged_requests':st['requests'],'lifetime_returned_native_keys':len(st['returned_object_ids']),'external_web_logical_lookups':st.get('external_web_logical_lookups_charged',0),'external_web_internal_HTTP_fanout_unknown':True,'inherited_key_catalog_difference':43,'current_returned_key_catalog_difference':len(st['returned_object_ids'])-(1037756+st['new_entities']),'carrier_new_body_counts':dict(carrier),'technical_list_new_requests':0,'technical_list_new_bodies':0,'technical_list_retained_dated_numerator':613617,'technical_list_baseline_share':613617/988701,'technical_list_current_share':613617/(988701+len(ledger)),'new_site_count':len(sites),'contributing_source_ids':sorted({r['source_id'] for r in ledger}),'contributing_native_author_units':len({(r['source_id'],r['author_id']) for r in ledger if r.get('author_id')}),'native_account_site_is_not_independent_parent':True,'earliest_new_publication':min((r['publication_at'] for r in ledger),default=None),'latest_new_publication':max((r['publication_at'] for r in ledger),default=None),'last_HTTP':st.get('last_successful_http_at_utc'),'last_Load':st.get('last_successful_load_at_utc'),'source_quality':{'changed_body_hashes_checked':checked,'accepted_body_hash_references_reused':reused,'metadata_annotations':meta,'provenance_truth_verification':False,'author_country_not_inferred':True},'capacity_at_delta_output_start':capacity,'climate_affect_or_fear_labels_executed':False,'source_or_count_or_share_finish_gate':False,'raw_and_old_versions_preserved':True,'automatic_successor':False}
            snapshot['author_role_new_body_counts']=dict(collections.Counter(r.get('author_role','unknown') for r in ledger))
            snapshot['author_country_status_new_body_counts']=dict(collections.Counter(r.get('author_country_status','unmeasured') for r in ledger))
            snapshot['historical_author_country_at_publication_unmeasured_bodies']=sum(r['author_country_historical_at_publication_status']=='unmeasured' for r in ledger)
            snapshot['category_archive_URLs_in_permalink_candidate_queue']=[{'source_id':sid,'state':state,'candidate_urls':n} for (sid,state),n in sorted(category_candidates.items())]
            snapshot['embedded_original_bodies_outside_selected_account_cohort']=sum(r.get('cohort_id')=='embedded_context_outside_selected_cohort' for r in ledger)
            snapshot['contributing_ordinary_self_presented_account_units']=len({(r['source_id'],r['author_id']) for r in ledger if r.get('author_role')=='ordinary_public_self_presentation' and r.get('author_id')})
            snapshot['source_quality']['changed_native_frame_finalization']=frame_receipt
            enum=t.read_json(t.WORK/'new_source_preparation/METADATA_PROBES.json',{})
            snapshot['separate_new_source_admission_metadata_requests']=enum.get('network_attempts',0)
            snapshot['separate_new_source_metadata_counter_not_merged_into_writer_requests']=True
            snapshot['separate_native_interface_documentation_web_lookups']=t.read_json(t.WORK/'new_source_preparation/NATIVE_WEB_DOCUMENTATION_LOOKUP.json',{}).get('web_tool_logical_open_calls',0)
            snapshot['documentation_web_lookup_HTTP_fanout_unknown']=True
            prepared_web=t.read_json(t.WORK/'new_source_preparation/NATIVE_WEB_CHANNEL_PREPARED.json',{})
            snapshot['additional_native_blog_sources_prepared']=len(prepared_web.get('plans',[]))
            snapshot['additional_prepared_blog_sources_with_actual_body_Load']=sorted({r['source_id'] for r in ledger}&{p['source']['source_id'] for p in prepared_web.get('plans',[])})
            snapshot['new_native_blog_source_body_counts']={p['source']['source_id']:sum(r['source_id']==p['source']['source_id'] for r in ledger) for p in prepared_web.get('plans',[])}
            snapshot['known_same_named_author_site_relation']={'html_vianegativa_dave':'dave_bonta','html_morningporch':'dave_bonta'}
            snapshot['Geograph_official_dump_route_assessment']=t.read_json(t.WORK/'new_source_preparation/GEOGRAPH_COMPLETE_OPERATION_ASSESSMENT.json',{}).get('status','not activated')
            if frozen:
                snapshot['current_route_amendment']={'effective_at_utc':scope['amendment_effective_at_utc'],'local_instruction_received_at_utc':frozen['local_instruction_received_at_utc'],'freeze_at_utc':frozen['at_utc'],'source_count':len(frozen['source_ids']),'cohort_count':len(frozen['cohort_ids']),'frozen_original_cursor_count':frozen['native_cursor_count_at_freeze'],'active_cursor_count_at_freeze':frozen['active_native_cursor_count_at_freeze'],'remaining_frozen_active_cursors':sum(c['state']=='active' and c['source_id'] in frozen['source_ids'] and c['cohort_id'] in frozen['cohort_ids'] for c in cursors),'new_source_and_cohort_discovery':False,'actor_cohort_count_unchanged_after_freeze':{a['cohort_id'] for a in actors}=={a['cohort_id'] for a in frozen['source_cohort_inventory'] }|{a['cohort_id'] for a in actors if a['source_id']=='html_wand3r'},'six_hour_delta_baseline_preserved':True,'WNDR_first_actual_Load_before_local_instruction_handling':frozen['WNDR_prior_notice_first_actual_Load'].get('at_utc'),'WNDR_further_continuation_allowed':False,'fixed_collection_stop':scope['hard_deadline_at_utc'],'two_hour_delivery_target':scope['report_delivery_target_at_utc']}
            snapshot['Blogger_prepared_routes_held_by_observed_provider_stop']=(t.WORK/'new_source_preparation/BLOGGER_PROVIDER_STOP.json').exists()
            snapshot['H4_operation_age_scheduler_correction']=bool(t.read_json(t.WORK/'H4_CORRECTION_RECEIPT.json',{}).get('passed'))
            snapshot['source_context_asof_derived_correction_original_metadata_preserved']=(t.WORK/'CURRENT_DELTA_SOURCE_CONTEXT_DERIVATION.json').exists()
            final_registry=t.read_json(t.WORK/'source_registry.json')
            for source in final_registry:
                sid=source['source_id'];matching=[r for r in ledger if r['source_id']==sid]
                source['current_tranche_readable_body_observation']={'new_dated_authored_body_rows':len(matching),'first_retrieved_at':min((r['retrieved_at'] for r in matching),default=None),'last_retrieved_at':max((r['retrieved_at'] for r in matching),default=None),'not_fresh_permission_or_source_country_verification':True,'observed_original_external_URI_body_verification':'pending where federated','inherited_source_admission_and_observations_preserved':True}
            # Dispatch identities, live controls and operation-capacity receipts remain local.
            publication_snapshot={k:v for k,v in snapshot.items() if k not in ('owner_thread_id','scope_sha256','capacity_at_delta_output_start','stop')}
            publication_snapshot['production_stop_at_utc']=snapshot['stop']['at_utc']
            publication_snapshot['production_stop_reason']=snapshot['stop']['reason']
            for name,obj in [('collection_manifest.json',publication_snapshot),('inherited_metadata_references.json',{'references':refs,'A_B_calendar_reconciled_once':True,'accepted_baseline_dated':988701}),('source_registry_final.json',final_registry)]:
                p=t.WORK/'summaries'/name;t.atomic(p,obj);files.append(p)
            p=t.WORK/'summaries/SOCIAL_COLLECTION_REPORT.md'
            text=f"# Nonforum social-source expansion and current-route closeout\n\nThe fixed authorized interval was {begin} to {scope['hard_deadline_at_utc']}. Source production stopped at {snapshot['stop']['at_utc']} for `{snapshot['stop']['reason']}`. The inherited phase B counters and accepted A+B calendar chain reconcile once; no old corpus/body audit or Git operation was performed.\n\nThis tranche adds {len(ledger):,} independently authored dated bodies, {st['new_entities']:,} native entities and {st['new_entity_versions']:,} versions, with {snapshot['round_charged_requests']:,} charged request operations. Totals are {snapshot['usable_dated_body_total']:,} dated bodies and {snapshot['retained_core_total']:,} retained core texts across {snapshot['pooled_observed_months']}/465 observed months. New carriers: {dict(carrier)}. Observed earliest new publication is {snapshot['earliest_new_publication']}; native pagination visibility is not complete archive recovery.\n\nThe broader severalfold-growth and source-breadth development objectives are not achieved by this bounded tranche. Actual additions establish observable source presence and inventory recovery; they do not validate population representativeness or complete historical coverage. Pending unopened candidates and incomplete admitted inventories remain separate from acquired bodies. No quantity milestone was used to stop this production.\n\nAll technical-list acquisition was suspended. Its retained dated numerator stays 613,617; cumulative share changes from {snapshot['technical_list_baseline_share']:.4%} to {snapshot['technical_list_current_share']:.4%} through actual new nontechnical bodies. No old records were deleted, downsampled or relabeled. Actor/site directories and permission-bearing personal-blog leads used traceable structural selection, without climate/fear/emotion keywords. Profile self-presentation is evidence of the declared account role, not independently proved identity. Unknown roles remain in prepared metadata and unknown author countries remain retained. Native actor/site units are not proven independent publishing parents. New body-role counts are {snapshot['author_role_new_body_counts']}; {snapshot['embedded_original_bodies_outside_selected_account_cohort']:,} original-body rows are embedded context outside the selected account cohort. The contributing ordinary self-presented account units number {snapshot['contributing_ordinary_self_presented_account_units']:,}; this is a native account-unit count, not independently proved people. Bluesky convenience follower/following graphs and Mastodon opt-in directories have explicit selection limits and do not represent national or platform populations.\n\nSource context and author self-declared country are reported separately, with explicit missingness. New-body country evidence statuses are {snapshot['author_country_status_new_body_counts']}; historical author country at publication remains unmeasured for {snapshot['historical_author_country_at_publication_unmeasured_bodies']:,} bodies. Current profile or site declarations do not assign a country to older posts. Mastodon federation may reproduce an original status; Bluesky repost/quote wrappers, embedded original posts and versions remain separate. Whole WordPress posts retain original HTML and stable site/post/author IDs, plus source permission receipts; commenter permission is separately pending wherever not established. No unavailable credential, paid, application-only or incompatible-retention route was bypassed.\n\nThe fixed publication interval remains 1988-01-01 through 2026-09-21, with partial September and narrower source observation times. Publication, retrieval, version and report time remain separate; a current retrieved body does not establish its historical version. These results demonstrate dated source presence and readable text only. Climate relevance/similarity, validated affect/risk associations and passage-linked fear interpretation are separate later evidence levels.\n\nCumulative social45GB/shared60GB accounting includes old roots, package33/34/35, joint publication and current/global document versions. Complete-operation reservations retain native32MiB/journal64MiB, physical15GiB floor, recovery48MiB, both leases and final local/publication/atomic-output costs. Original raw receipts and source stops remain local; main delivery contains implementation and finalized metadata. No rolling extension or automatic successor is authorized.\n"
            text+=f"\nAdditional named native blog adapters were prepared for {snapshot['additional_native_blog_sources_prepared']} sources; actual new-body Load is recorded for {snapshot['additional_prepared_blog_sources_with_actual_body_Load']}. Source-admission probes made {snapshot['separate_new_source_admission_metadata_requests']} independent HTTP attempts, separately charged from the primary writer and coordinator; these probes are not corpus Load. Blogger prepared routes remained held after observed provider429 evidence: {snapshot['Blogger_prepared_routes_held_by_observed_provider_stop']}. New mappings preserve author-controlled migration/modification dates, native permalink day/time precision, explicit licence exceptions and source spacing. Index wrappers, comments, media-only or hidden crosspost scaffolding are not counted as readable original text.\n"
            if snapshot['H4_operation_age_scheduler_correction']:
                text+="\nThe initial fixed active-list sweep delayed newly appended historical-blog children behind existing account histories. The H+4 correction reselects the current ready/frontier set after every completed operation, with persistent source service time, per-job ready/attempt age and provider spacing. This is operational fairness without corpus-count, genre, year, country, parent or distribution weights, quotas or stopping thresholds. A same-owner handover retained all counters/cursors and the original deadline; a subsequent native child transaction added seven actual historical bodies, then all four new native-blog sources produced text while existing ordinary-account/WordPress routes continued. The current derived route plan was rebound to the existing scope, preserving the previous plan locally. Source-context location asof is bound to the accepted8October evidence; profile observation time is separate. Original BODY_DELTA/native versions remain unchanged, with current-delta overlays and original recorded times retained in finalized metadata. No author-country inference or historical-location backfill was performed.\n"
            text+=f"\nLater named English-author route additions continued through the same operation-age queue and fixed deadline. Actual source contributions are {snapshot['new_native_blog_source_body_counts']}; these are source-site counts, with Via Negativa/Dave and Morning Porch sharing the named Dave Bonta author family. Final source contribution and current self-declaration tables preserve role, permission observation, licence variants, migrations and country uncertainty. Exact unmodified CMS welcome scaffolding remains a native entity rather than an authored body. A named saved1999response was reparsed after an adapter/intake timing fault without a new network request or counter reset; subsequent intake binds plans to actually loaded code. The Sivers book-context pages /m1 and /m2 retain their native2000-01-01 values with historical first-publication mapping unresolved; such source-declared dates are not independently verified historical publication.\n\nGeograph provided a documented permitted official caption-dump route, with401,581,261advertised compressed bytes. That lower bound fit the measured existing headroom, but full decompression/join/index/native-version/export peak and implementation/settlement time were not established in this interval. No dump, partial prefix, media, HTML scrape or key API was activated. This is an unavailable complete-operation proof, not a measured physical no-fit or a source-quality failure.\n"
            if category_candidates:
                text+=f"\nThe retained native queue contains category-archive URLs classified as permalink candidates: {snapshot['category_archive_URLs_in_permalink_candidate_queue']}. Observed unresolved mappings and unattempted directory candidates do not establish complete article inventory or source failure. No directory URL counts as an authored body without its separate native identity/date/body mapping. This route-classification issue remains visible for later repair; no queue evidence was deleted or blanket reset.\n"
            if frozen:
                change=snapshot['current_route_amendment']
                text+=f"\nThe latest direct user amendment restricted continuation to already opened routes and reserved collection plus delivery within two hours from07:57:07UTC. The prior08:24:42UTC stop was prospectively replaced by09:24:42UTC collection stop and09:57:07UTC coordinator delivery target; prior scope/bindings remain preserved. At the completed-operation handover, {change['source_count']} sources and{change['cohort_count']:,} known cohorts were frozen, with{change['active_cursor_count_at_freeze']:,} active native cursors. Source/site/actor discovery and candidate intake were disabled; native pagination/known children inside those frozen cohorts continued fairly. WNDR had an actual first Load at{change['WNDR_first_actual_Load_before_local_instruction_handling']} before this chat handled the new instruction; its actual bytes/rows were preserved and its further route was held. The amended task kept the original six-hour delta baseline and cumulative counters. Remaining active frozen cursors number{change['remaining_frozen_active_cursors']:,}; a fixed stop is not archive completeness.\n"
            q=p.with_suffix('.md.pending');q.write_text(text);q.replace(p);files.append(p)
            t.atomic(t.WORK/'CLOSED.json',snapshot)
        # Verify only changed saved responses; old accepted raw evidence is referenced.
        saved=0;requests=0
        for p in (t.WORK/'receipts').glob('*.json'):
            r=t.read_json(p);requests+=1
            if r.get('status')=='saved':
                packed=(t.REPO/r['raw_reference']).read_bytes()
                assert len(packed)==r['stored_bytes'] and t.sha(packed)==r['stored_sha256']
                raw=gzip.decompress(packed)
                assert len(raw)==r['raw_bytes'] and t.sha(raw)==r['raw_sha256'];saved+=1
        loads=[]
        with (t.WORK/'LOADS.jsonl').open() as f:
            for line in f:loads.append(json.loads(line))
        assert all(r['observed_additional_disk_peak_upper_bytes']<=r['reserved_operation_bytes'] for r in loads)
        frontier_writes=[]
        frontier_log=t.WORK/'FRONTIER_WRITE_CAPACITY.jsonl'
        if frontier_log.exists():
            with frontier_log.open() as f:
                for line in f:frontier_writes.append(json.loads(line))
        assert all(r['shared_lock_held'] and r['observed_atomic_coexistence_upper_bytes']<=r['reserved_operation_bytes'] for r in frontier_writes)
        enum_raws=0
        for r in t.read_json(t.WORK/'new_source_preparation/METADATA_PROBES.json',{}).get('rows',[]):
            if r.get('status')!='saved':continue
            packed=(t.REPO/r['raw_reference']).read_bytes();assert t.sha(packed)==r['stored_sha256']
            raw=gzip.decompress(packed);assert t.sha(raw)==r['raw_sha256'];enum_raws+=1
        implementation=[p for p in t.WORK.glob('*.py')]+[t.WORK/'schema_v2.sql',t.WORK/'schema_legacy.sql']
        manifest={'at_utc':t.utc(),'files':[reference(p) for p in files],'implementation':[reference(p) for p in implementation],'raw_not_publication':True}
        t.atomic(t.WORK/'summaries/delivery_file_manifest.json',manifest)
        # Reserve prospective publication copies and largest atomic coexistence.
        future=sum(p.stat().st_size for p in files+implementation)+max((p.stat().st_size for p in files+implementation),default=0)
        with t.shared(max(t.footprint(),future),inflight_at=begin) as final_capacity:
            verification={'at_utc':t.utc(),'passed':True,'saved_changed_raws_digest_checked':saved,'separate_new_source_metadata_raws_digest_checked':enum_raws,'changed_request_receipts':requests,'new_body_metadata_exact_SQL_ID_match':True,'changed_complete_operation_peaks_checked':len(loads),'peak_violations':0,'delivery_files':len(files),'delivery_bytes':sum(p.stat().st_size for p in files),'future_publication_and_largest_temp_actual_bytes':future,'final_guarded_capacity':final_capacity,'no_old_raw_body_or_whole_store_audit':True,'database_journal_absent':not Path(str(t.DB)+'-journal').exists()}
            t.atomic(t.WORK/'FINAL_DELIVERY_VERIFICATION.json',verification)
    t.atomic(t.WORK/'TERMINAL_COMPLETE.json',{'at_utc':t.utc(),'source_pid':t.read_json(t.WORK/'RUN_STOP.json')['pid'],'terminal_pid':os.getpid(),'writer_mutex_released':True,'verification_passed':True,'fixed_deadline_unchanged':True})
    print(json.dumps({'closed':True,'new_dated_bodies':snapshot['new_usable_dated_bodies'],'total_dated':snapshot['usable_dated_body_total'],'technical_share':snapshot['technical_list_current_share']}))

if __name__=='__main__':main()
