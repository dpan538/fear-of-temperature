"""Close this owner-bound append interval without duplicating or auditing old bodies."""
import collections,csv,gzip,json,os,re,datetime as dt
from pathlib import Path
import transport as t,entities as e,finalize_metadata,raw_catalog

NEW_CORES_QUERY='''SELECT p.persistent_post_id,p.source_id,p.native_created_at,
 MAX(COALESCE(a.independently_authored_body,v.independently_authored_body))
 FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id
 JOIN posts p ON p.persistent_post_id=v.entity_id
 LEFT JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id
 WHERE NOT EXISTS (SELECT 1 FROM entity_versions old WHERE old.entity_id=p.persistent_post_id
 AND old.core_body_version_id IS NOT NULL AND old.rowid<=?)
 GROUP BY p.persistent_post_id'''

def parse_content(rec):
    sid=rec['source_id'];url=rec['url'];raw=t.payload(rec);maximum=32*1048576 if sid=='python_list_archive' else 20*1048576 if sid=='ilxor' else 16*1048576
    if raw.startswith(b'\x1f\x8b'):
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:raw=f.read(maximum+1)
    if len(raw)>maximum:raise t.Stop('decompressed_operation_bound')
    import archive_adapter,public_html_adapter,lemmy_adapter
    sources={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')}
    if sid=='thesession':
        import thesession_adapter
        return [] if '/discussions/new' in url else thesession_adapter.records(raw,url)[0]
    if sid=='ilxor':return public_html_adapter.ilxor_thread(raw,url)[0]
    if sid=='tildes':return (public_html_adapter.tildes_topic if re.search(r'/~[^/]+/[^/]+',url) else public_html_adapter.tildes_index)(raw,url)[0]
    if sources[sid].get('adapter')=='public_html_adapter.mail_message':return public_html_adapter.mail_message(raw,url,sid)[0] if re.search(r'/msg[0-9]+\.html$',url) else []
    if sid=='python_list_archive':return archive_adapter.mbox_records(raw,sid,url)
    if sid=='w3_wwwtalk':return archive_adapter.w3_records(raw,url,sid) if re.search(r'/[0-9]{4}\.html$',url) else []
    data=json.loads(raw)
    if sid=='hackernews':return archive_adapter.hn_records(data,sid,url.rsplit('/',1)[-1].split('.')[0])
    if sid.startswith('se_'):return e.se(data,sid)
    if sid.startswith('mastodon_'):return e.mastodon(data,sid)
    if sid=='bluesky':return e.bluesky(data)
    if sid in ('lemmy_nz','aussie_zone','feddit_org','midwest_social'):return lemmy_adapter.records(data,sid,sources[sid]['base_url'])
    if '/latest.json' in url:return []
    return e.discourse(data,sid,sources[sid]['base_url'],sources[sid].get('content_license','version_specific_license_unresolved'))

def reconcile_saved():
    """Settle saved but uncommitted content with complete-operation safeguards."""
    loaded={json.loads(x)['request_id'] for x in (t.WORK/'LOADS.jsonl').read_text().splitlines()};result=[]
    loaded-={rid for rid,item in t.read_json(t.WORK/'SMALL_NATIVE_LOAD_STATE.json',{}).items() if not item['complete']}
    for p in sorted((t.WORK/'receipts').glob('*.json')):
        rec=t.read_json(p)
        if rec['status']!='saved' or rec['purpose']!='content' or rec['request_id'] in loaded:continue
        try:
            rows=parse_content(rec)
            # Keep the future metadata/export tail reserved while recovering raw.
            t.TERMINAL_OPERATION=False
            load=e.load(rows,rec,rec['source_id']+':saved_response_terminal_reconciliation')
            result.append({'request_id':rec['request_id'],'status':'loaded','result':load})
        except Exception as exc:
            result.append({'request_id':rec['request_id'],'status':'saved_native_evidence_pending','reason':type(exc).__name__+': '+str(exc)})
        finally:t.TERMINAL_OPERATION=True
    t.atomic(t.WORK/'SAVED_CONTENT_RECONCILIATION.json',{'at_utc':t.utc(),'source_requests':0,'results':result,'raw_receipts_and_pending_evidence_retained':True})
    return result

def base_calendar():
    scope=t.read_json(t.SCOPE_PATH);original=t.REPO/scope['predecessor_worker_reference']
    values=collections.Counter()
    with (original/'summaries/source_month_calendar.csv').open() as f:
        for row in csv.DictReader(f):values[row['source_id'],row['month']]+=int(row['usable_dated_independent_bodies'])
    return values

def fsync_file(path):
    with path.open('rb') as f:os.fsync(f.fileno())

def applicability(source,month,count):
    start=source.get('existence_at');basis=source.get('existence_basis','')
    documented=bool(start and ('closed_beta_date' in basis or 'site_creation_date' in basis))
    if documented and month<start[:7]:
        return 'pre_documented_source_existence_conflicting_dated_records_pending' if count else 'structurally_inapplicable_before_documented_source_existence'
    if start and not documented and month<start[:7]:return 'outside_observed_archive_span_source_existence_unresolved'
    return 'dated_native_records_present_historical_public_access_not_proved' if count else 'applicability_or_archive_completeness_unresolved'

def main():
    assert t.read_json(t.WORK/'RUN_STOP.json')
    assert t.read_json(t.WORK/'SUCCESSOR_INCREMENTAL_TAIL_REGRESSION.json')['passed']
    assert t.read_json(t.WORK/'INCREMENTAL_SELECTION_REGRESSION.json')['passed']
    assert t.read_json(t.WORK/'FOCUSED_CONTINUATION_REGRESSION.json')['passed']
    baseline=t.read_json(t.WORK/'INHERITED_BASELINE.json');bounds=t.read_json(t.WORK/'APPEND_ROWID_BOUNDARIES.json')['bounds']
    scope=t.read_json(t.SCOPE_PATH);begin=scope['earliest_network_and_load_start_at_utc'];out=t.WORK/'summaries';out.mkdir(exist_ok=True)
    files=[]
    def file_receipt(path):
        fsync_file(path);files.append({'path':str(path.relative_to(t.WORK)),'bytes':path.stat().st_size,'sha256':t.sha(path.read_bytes())})
    def export(c,name,sql,params=()):
        cur=c.execute(sql,params);path=out/(name+'.csv.gz')
        with gzip.open(path,'wt',newline='',encoding='utf8') as f:
            writer=csv.writer(f);writer.writerow([x[0] for x in cur.description]);writer.writerows(cur)
        file_receipt(path)
    with t.writer():
        t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'phase':'incremental_terminal_closeout'})
        t.TERMINAL_OPERATION=True
        recovery=reconcile_saved()
        metadata=finalize_metadata.finalize(phase='successor_terminal',batch_records=1000)
        import source_era_provenance
        era_annotations=source_era_provenance.repair_changed_annotations({x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')},bounds['entity_versions'],begin)
        st=t.state();model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json')
        reserve=st['new_entity_versions']*model['export_upper_bytes_per_version']+st['new_entities']*model['export_upper_bytes_per_entity']+model['delta_export_fixed_allowance_bytes']+model['bounded_metadata_journal_bytes']
        with t.shared(reserve,inflight_at=begin) as budget:
            c=e.db();c.execute('PRAGMA temp_store=MEMORY')
            c.execute('CREATE TEMP TABLE changed_versions(id TEXT PRIMARY KEY) WITHOUT ROWID')
            c.execute('INSERT INTO changed_versions SELECT entity_version_id FROM entity_versions WHERE rowid>?',(bounds['entity_versions'],))
            assert c.execute('SELECT COUNT(*) FROM changed_versions').fetchone()[0]==st['new_entity_versions']
            annotated_changed=c.execute('SELECT COUNT(*) FROM changed_versions x JOIN entity_quality_annotations a ON a.entity_version_id=x.id').fetchone()[0]
            assert annotated_changed==st['new_entity_versions']
            c.execute('CREATE TEMP TABLE changed_entities(id TEXT PRIMARY KEY) WITHOUT ROWID')
            c.execute('INSERT INTO changed_entities SELECT DISTINCT v.entity_id FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id')
            assert c.execute('SELECT COUNT(*) FROM native_entities WHERE rowid>?',(bounds['native_entities'],)).fetchone()[0]==st['new_entities']
            assert c.execute('SELECT COUNT(*) FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id LEFT JOIN native_entities n ON n.entity_id=v.entity_id WHERE n.entity_id IS NULL').fetchone()[0]==0
            checked=reused=0
            for vid,sha,body,text,core,old,oldsha in c.execute('''SELECT v.entity_version_id,v.body_sha256,
             CASE WHEN b.rowid<=? THEN NULL ELSE COALESCE(b.body_original,v.body_original) END,
             CASE WHEN b.rowid<=? THEN NULL ELSE COALESCE(b.body_text,v.body_text) END,
             v.core_body_version_id,CASE WHEN b.rowid<=? THEN 1 ELSE 0 END,b.body_sha256
             FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id
             LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id''',(bounds['versions'],)*3):
                if old:assert sha==oldsha;reused+=1;continue
                assert (t.sha(body.encode()) if body else None)==sha,vid
                if core:assert body and text,vid
                checked+=1
            predecessor=t.REPO/scope['predecessor_worker_reference'];prior_peak_path=predecessor/'summaries/native_operation_peak_summary.json'
            prior_manifest=t.read_json(predecessor/'summaries/delivery_file_manifest.json')
            peak_binding=next(x for x in prior_manifest['files'] if x['path']=='summaries/native_operation_peak_summary.json')
            assert t.sha(prior_peak_path.read_bytes())==peak_binding['sha256']
            prior_peak=t.read_json(prior_peak_path);assert prior_peak['passed']
            remaining_loads=[json.loads(line) for line in (t.WORK/'LOADS.jsonl').read_text().splitlines() if line.strip()]
            assert all(r['at_utc']>=begin for r in remaining_loads)
            peak_classes={}
            for r in remaining_loads:
                observed=r['observed_additional_disk_peak_upper_bytes'];reserved=r['reserved_operation_bytes']
                assert observed<=reserved,(r['request_id'],observed,reserved)
                sid=r['frame_id'].split(':',1)[0]
                item=peak_classes.setdefault(sid,{'loads_checked':0,'max_observed_complete_peak_upper_bytes':0,'max_ratio_to_reserved':0,'exceedances':0})
                item['loads_checked']+=1;item['max_observed_complete_peak_upper_bytes']=max(item['max_observed_complete_peak_upper_bytes'],observed);item['max_ratio_to_reserved']=max(item['max_ratio_to_reserved'],observed/reserved)
            peak_summary={'at_utc':t.utc(),'accepted_prior_verification_at_utc':prior_peak['at_utc'],'accepted_prior_verified_loads':prior_peak['accepted_prior_verified_loads']+prior_peak['remaining_changed_loads_checked'],'accepted_prior_summary_sha256':peak_binding['sha256'],'remaining_changed_loads_checked':len(remaining_loads),'source_classes':peak_classes,'passed':True,'original_precalibration_overshoot_and_receipts_preserved':True,'old_body_or_raw_reaudit':False}
            t.atomic(out/'native_operation_peak_summary.json',peak_summary);file_receipt(out/'native_operation_peak_summary.json')
            durability=[t.read_json(p) for p in t.WORK.glob('DURABILITY_FLUSH_*_RECEIPT.json')]
            completed_metadata=[r for r in durability if r.get('actual_annotated_new_versions')]
            assert all(r['observed_complete_peak_bytes']<=r['reserved_complete_peak_bytes'] for r in completed_metadata)
            metadata_peaks={'at_utc':t.utc(),'passed':True,'completed_flushes_checked':len(completed_metadata),'changed_versions_annotated_midwindow':sum(r['actual_annotated_new_versions'] for r in completed_metadata),'max_observed_complete_peak_bytes':max((r['observed_complete_peak_bytes'] for r in completed_metadata),default=0),'max_ratio_to_reserved':max((r['observed_complete_peak_bytes']/r['reserved_complete_peak_bytes'] for r in completed_metadata),default=0),'resource_blocked_flushes_preserved_locally':sum(r.get('partial',False) for r in durability),'tiny_transaction_max_records':50,'fixed_tiny_margin_bytes':32*1048576,'tiny_per_row_margin_bytes':65536,'larger_metadata_and_reserved_terminal_journal_bytes':64*1048576,'source_requests':0,'body_reads':0,'individual_receipts_remain_local':True}
            t.atomic(out/'metadata_operation_peak_summary.json',metadata_peaks);file_receipt(out/'metadata_operation_peak_summary.json')
            rawstats,rawfiles=raw_catalog.catalog(c,out)
            for entry in rawfiles:file_receipt(t.WORK/entry['path'])
            statements={
                'new_native_entities':('SELECT * FROM native_entities WHERE rowid>?',(bounds['native_entities'],)),
                'changed_entity_versions':('''SELECT v.entity_version_id,v.entity_id,v.core_body_version_id,v.body_sha256,v.native_edited_at,v.native_revision,v.content_state,v.fixed_interval_state,v.readable_native_unit,v.independently_authored_body,v.content_license,v.licence_basis,v.flags_json,v.first_retrieved_at FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id''',()),
                'new_entity_observations':('SELECT * FROM entity_observations WHERE rowid>?',(bounds['entity_observations'],)),
                'new_relations':('SELECT * FROM native_edges WHERE rowid>?',(bounds['native_edges'],)),
                'affected_incoming_relations':('SELECT e.* FROM native_edges e WHERE e.target_entity_id IN (SELECT id FROM changed_entities)',()),
                'new_attachment_metadata':('SELECT * FROM native_attachments WHERE rowid>?',(bounds['native_attachments'],)),
                'changed_source_provenance':('SELECT a.* FROM changed_versions x JOIN entity_quality_annotations a ON a.entity_version_id=x.id',()),
                'source_native_migration_metadata':("SELECT v.entity_version_id,n.entity_id,n.source_id,n.source_url,n.native_created_at,json_extract(v.native_fields_json,'$.migrated_from') AS native_migrated_from,json_extract(v.native_fields_json,'$.migrated_to') AS native_migrated_to FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id JOIN native_entities n ON n.entity_id=v.entity_id WHERE json_type(v.native_fields_json,'$.migrated_from') IS NOT NULL OR json_type(v.native_fields_json,'$.migrated_to') IS NOT NULL",()),
                'affected_native_aliases':('SELECT * FROM native_aliases WHERE entity_id IN (SELECT id FROM changed_entities)',()),
                'affected_publication_memberships':('SELECT * FROM publication_memberships WHERE entity_id IN (SELECT id FROM changed_entities)',()),
                'new_structural_corrections':('SELECT * FROM structural_corrections WHERE corrected_at>=?',(begin,)),
                'changed_date_limits':('''SELECT n.entity_id,n.source_id,n.native_created_at,n.date_precision,v.content_state,v.fixed_interval_state,v.flags_json FROM changed_versions x JOIN entity_versions v ON v.entity_version_id=x.id JOIN native_entities n ON n.entity_id=v.entity_id WHERE n.native_created_at IS NULL OR v.fixed_interval_state!='inside_fixed_interval' OR json_extract(v.flags_json,'$.observed_identity_date_or_unit_conflict') IS NOT NULL''',())
            }
            for name,(sql,params) in statements.items():export(c,name,sql,params)
            newcores=c.execute(NEW_CORES_QUERY,(bounds['entity_versions'],)).fetchall();assert len(newcores)==st['new_core_bodies']
            calendar=base_calendar();delta=collections.Counter();usable=0
            for eid,sid,date,authored in newcores:
                if authored:usable+=1;calendar[sid,date[:7]]+=1;delta[sid,date[:7]]+=1
            months={m for (sid,m),n in calendar.items() if n};assert sum(calendar.values())==baseline['usable_dated_bodies']+usable
            path=out/'source_month_deltas.csv'
            with path.open('w',newline='',encoding='utf8') as f:
                writer=csv.writer(f);writer.writerow(['source_id','month','new_usable_dated_bodies','reporting_only_not_acquisition_target']);writer.writerows((sid,m,n,1) for (sid,m),n in sorted(delta.items()))
            file_receipt(path)
            study_months=[f'{year:04}-{month:02}' for year in range(1988,2027) for month in range(1,13) if f'{year:04}-{month:02}'<='2026-09']
            sources=t.read_json(t.WORK/'source_registry.json');sids=sorted({sid for sid,m in calendar}|{x['source_id'] for x in sources})
            path=out/'source_month_calendar.csv'
            with path.open('w',newline='',encoding='utf8') as f:
                registry={x['source_id']:x for x in sources}
                writer=csv.writer(f);writer.writerow(['source_id','month','usable_dated_independent_bodies','source_era_applicability','full_calendar_corpus_presence_not_complete_archive','partial_boundary_month'])
                for sid in sids:
                    for month in study_months:writer.writerow((sid,month,calendar[sid,month],applicability(registry.get(sid,{}),month,calendar[sid,month]),1,int(month=='2026-09')))
            file_receipt(path)
            path=out/'source_month_neighbor_context.csv'
            with path.open('w',newline='',encoding='utf8') as f:
                writer=csv.writer(f);writer.writerow(['source_id','month','count','previous_three_counts','following_three_counts','incomplete_boundary_context','greater_than_all_available_neighbors_candidate','event_attribution'])
                for sid in sids:
                    for i,month in enumerate(study_months):
                        n=calendar[sid,month]
                        if not n:continue
                        before=[calendar[sid,m] for m in study_months[max(0,i-3):i]];after=[calendar[sid,m] for m in study_months[i+1:i+4]];neighbors=before+after
                        writer.writerow((sid,month,n,json.dumps(before),json.dumps(after),int(len(neighbors)<6 or i>=len(study_months)-4),int(bool(neighbors) and n>max(neighbors)),'none; independent dated evidence required'))
            file_receipt(path)
            # Comparable calendar windows are descriptive outputs, never collection controls.
            before_calendar=base_calendar();matched_months={f'{year}-{month:02}' for year in range(2016,2027) for month in range(1,9)}
            baseline_sources={sid for (sid,month),n in before_calendar.items() if n}
            registry={x['source_id']:x for x in sources}
            from source_frame_reporting import genre as frame_genre,METHOD
            def source_genre(sid):return frame_genre(sid,registry)
            path=out/'matched_year_source_genre_panel.csv'
            with path.open('w',newline='',encoding='utf8') as f:
                writer=csv.writer(f);writer.writerow(['year','source_id','genre_basis_from_source_frame','baseline_Jan_Aug_usable_bodies','new_Jan_Aug_usable_bodies','current_Jan_Aug_usable_bodies','source_contributed_in_baseline','unknown_author_role_country','reporting_only'])
                for year in range(2016,2027):
                    for sid in sids:
                        old=sum(before_calendar[sid,f'{year}-{m:02}'] for m in range(1,9));added=sum(delta[sid,f'{year}-{m:02}'] for m in range(1,9))
                        writer.writerow((year,sid,source_genre(sid),old,added,old+added,int(sid in baseline_sources),1,1))
            file_receipt(path)
            panel={}
            for selection in ['all_current_source_frames','baseline_contributing_source_panel']:
                for era in ['full_history','Jan_Aug2016_2026']:
                    for state,values in [('accepted_before',before_calendar),('after_changed_tranche',calendar)]:
                        entries=[(sid,m,n) for (sid,m),n in values.items() if n and (selection=='all_current_source_frames' or sid in baseline_sources) and (era=='full_history' or m in matched_months)]
                        total=sum(n for sid,m,n in entries);year2026=sum(n for sid,m,n in entries if m.startswith('2026-'))
                        panel[selection+'|'+era+'|'+state]={'total_usable_bodies':total,'year2026_bodies':year2026,'descriptive_year2026_share':year2026/total if total else None,'genre_counts':dict(collections.Counter({genre:sum(n for sid,m,n in entries if source_genre(sid)==genre) for genre in {source_genre(sid) for sid,m,n in entries}}))}
            t.atomic(out/'same_era_source_genre_comparison.json',{'at_utc':t.utc(),'panel':panel,'genre_reporting_method':METHOD,'changing_source_frame_and_partial_full_history2026_not_normalized_away':True,'counts_shares_never_sampling_weights_or_acquisition_gates':True,'remaining_narrowness_or_sparse_months_not_declared_healthy':True});file_receipt(out/'same_era_source_genre_comparison.json')
            frames=c.execute('SELECT * FROM acquisition_frames').fetchall()
            newbodyversions=c.execute('SELECT COUNT(*) FROM versions WHERE rowid>?',(bounds['versions'],)).fetchone()[0]
            c.close()
            predecessor=t.REPO/scope['predecessor_worker_reference']
            assert t.sha((predecessor/'CLOSED.json').read_bytes())==baseline['predecessor_closed_snapshot_sha256']
            assert t.sha((predecessor/'summaries/delivery_file_manifest.json').read_bytes())==baseline['predecessor_phase_manifest_sha256']
            snapshot={'at_utc':t.utc(),'publication_interval':scope['publication_interval'],'partial_end_month':True,'authorized_start_at_utc':begin,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'stop':{k:v for k,v in t.read_json(t.WORK/'RUN_STOP.json').items() if k in ('at_utc','reason','deadline_preserved')},'new_core_texts':st['new_core_bodies'],'new_usable_dated_bodies':usable,'retained_core_total':baseline['counts']['posts']+st['new_core_bodies'],'usable_dated_body_total':baseline['usable_dated_bodies']+usable,'pooled_observed_months':len(months),'study_months':465,'new_entities':st['new_entities'],'new_entity_versions':st['new_entity_versions'],'new_body_versions':newbodyversions,'native_entities_total':baseline['counts']['native_entities']+st['new_entities'],'entity_versions_total':baseline['counts']['entity_versions']+st['new_entity_versions'],'round_charged_requests':st['requests']-baseline['lifetime_charged_requests'],'lifetime_charged_requests':st['requests'],'lifetime_returned_native_keys':len(st['returned_object_ids']),'inherited_key_catalog_difference':43,'pending_inherited_source_era_dates':9,'source_year_deltas':st.get('source_year_deltas',{}),'source_month_delta_rows':len(delta),'checks':{'append_version_and_entity_counts_match_Load_counters':True,'changed_identity_links_valid':True,'changed_bodies_checked':checked,'accepted_body_hash_references_reused':reused,'changed_raw_mapping':rawstats,'predecessor_full_integrity_result_reused':True,'old_body_or_raw_reaudit':False},'metadata':metadata,'saved_response_reconciliation':recovery,'export_start_capacity':budget,'reserved_export_and_metadata_journal_bytes':reserve,'predecessor_closed_snapshot_sha256':baseline['predecessor_closed_snapshot_sha256'],'predecessor_delta_manifest_sha256':baseline['predecessor_phase_manifest_sha256'],'semantic_or_affect_labels_executed':False}
            snapshot['checks']['all_changed_versions_have_native_quality_annotations']=annotated_changed
            snapshot['checks']['remaining_changed_native_load_peak_reservations']=peak_summary
            snapshot['metadata_counts_basis']='terminal phase only; completed midwindow annotations are included in the all-changed-version check and exported provenance'
            snapshot['changed_source_era_provenance_annotations']=era_annotations
            snapshot['midwindow_metadata_settlement']=metadata_peaks
            interrupted=t.read_json(t.WORK/'ANNOTATION_COUNTER_RECOVERY_11.json',{})
            if interrupted:snapshot['interrupted_metadata_settlement']={k:interrupted[k] for k in ['interrupted_committed_annotations_added_to_accounting','last_receipt_committed_annotations','commit_after_last_receipt_pending_peak_check','no_body_or_old_corpus_reads','native_source_counters_unchanged']}
            
            for source in sources:
                sid=source['source_id'];observed=sorted(m for (name,m),n in calendar.items() if name==sid and n)
                source['current_collection_observation']={'usable_dated_corpus_bodies':sum(n for (name,m),n in calendar.items() if name==sid),'new_usable_dated_bodies':sum(n for (name,m),n in delta.items() if name==sid),'first_observed_core_month':observed[0] if observed else None,'last_observed_core_month':observed[-1] if observed else None,'source_presence_only_not_archive_completeness_or_emotion_prevalence':True,'inherited_preparation_statements_are_historical':True}
            t.atomic(out/'source_registry_final.json',sources);file_receipt(out/'source_registry_final.json')
            for name in ['SOURCE_EXPANSION_LIMITS.json','NEW_PUBLIC_COMMUNITY_ADMISSIONS.json','ILX_SOURCE_RETURN_COUNT_LIMIT.json']:
                if (t.WORK/name).exists():t.atomic(out/name,t.read_json(t.WORK/name));file_receipt(out/name)
            t.atomic(out/'source_frame_definitions.json',{'columns':['frame_id','source_id','frame_type','selection_rule','existence_lower_bound','actor_role_basis','metadata_json'],'rows':frames,'current_native_selection_evidence':[{k:f.get(k) for k in ['frame','source','kind','selection_rule_evidence'] if k in f} for f in t.read_json(t.WORK/'FRONTIERS.json') if f.get('selection_rule_evidence')]});file_receipt(out/'source_frame_definitions.json')
            code=['bootstrap.py','collect.py','transport.py','entities.py','archive_adapter.py','lemmy_adapter.py','public_html_adapter.py','thesession_adapter.py','finalize_metadata.py','raw_catalog.py','incremental_closeout.py','incremental_durability.py','focused_progress.py','checkpoint_panels.py','source_frame_reporting.py','quota_observation.py','quota_guard_regression.py','stackexchange_community_admission.py','native_capacity_sizing.py','source_era_provenance.py','small_native_regression.py','capacity_queue_recovery.py','capacity_queue_regression.py','schema_v2.sql','schema_legacy.sql']
            t.atomic(out/'implementation_source_manifest.json',{'at_utc':t.utc(),'files':[{'path':n,'bytes':(t.WORK/n).stat().st_size,'sha256':t.sha((t.WORK/n).read_bytes())} for n in code],'execution_controls_and_owner_handoffs_are_local':True});file_receipt(out/'implementation_source_manifest.json')
            from focused_progress import COMMUNITIES
            community_rows=[]
            for sid,label in COMMUNITIES.items():
                n=sum(value for (source,month),value in delta.items() if source==sid)
                observed=sorted(month for (source,month),value in delta.items() if source==sid and value)
                if n:community_rows.append({'source_id':sid,'community':label,'new_usable_dated_bodies':n,'new_observed_months':observed})
            community_table='\n'.join('| '+r['community']+' | '+format(r['new_usable_dated_bodies'],',')+' | '+r['new_observed_months'][0]+' to '+r['new_observed_months'][-1]+' |' for r in community_rows)
            binding=t.read_json(t.WORK/'PREDECESSOR_BINDING_RECEIPT.json')
            snapshot['three_priorities']={'legacy_state_reconciliations':[{k:v for k,v in x.items() if k in ('frame','change')} for x in binding['changes']],'focused_regression':t.read_json(t.WORK/'FOCUSED_CONTINUATION_REGRESSION.json'),'actual_named_community_contributions':community_rows,'source_month_delta_rows':len(delta),'community_development_goal_is_not_a_stop_gate':True,'technical_bulk_python_queue_held':True,'new_pooled_months':sorted(months-{m for (sid,m),n in base_calendar().items() if n})}
            quota_result=t.read_json(t.WORK/'QUOTA_OBSERVATION_RESULT.json',{})
            snapshot['three_priorities']['provider_access_evidence']={'current_scope_observation':{k:v for k,v in quota_result.items() if k in ('at_utc','status','http_status','quota_remaining','api_error','api_backoff','positive_provider_response','historical_host_stop_retained','native_renewal_not_assumed_from_clock','new_key_account_identity_or_ip','counters_reset')},'most_recent_native_provider_state':{k:v for k,v in st.get('latest_stackexchange_provider_state',{}).items() if k!='request_id'},'no_observation_dispatched':not bool(quota_result),'original_exhaustion_evidence_retained':True,'quota_guard_fixture':t.read_json(t.WORK/'QUOTA_OBSERVATION_GUARD_REGRESSION.json',{}),'site_admission_fixture':t.read_json(t.WORK/'STACKEXCHANGE_ADMISSION_REGRESSION.json',{})}
            snapshot['three_priorities']['provider_access_evidence']['method_backoff_fixture']=t.read_json(t.WORK/'PROVIDER_METHOD_BACKOFF_REGRESSION.json',{})
            t.atomic(out/'focused_repair_evidence.json',snapshot['three_priorities']);file_receipt(out/'focused_repair_evidence.json')
            report=f'''# Focused historical and community social collection

This eight-hour continuation adds **{st['new_core_bodies']:,} retained core texts**, {st['new_entities']:,} native entities and {st['new_entity_versions']:,} immutable native versions. Structural and source-quality checks yield {usable:,} new usable dated bodies. The cumulative store contains {snapshot['retained_core_total']:,} retained core texts and {snapshot['usable_dated_body_total']:,} usable dated bodies across {len(months)}/465 observed months. Source presence does not establish complete archives, representative public expression, climate relevance or emotion prevalence.

The fixed authorized interval is 10 October 2026 **20:27:04 AEST through 11 October 04:27:04 AEST**, including preparation. The collector stops for `{snapshot['stop']['reason']}`. Publication eligibility remains **1988-01-01 through 2026-09-21**, with September partial. Publication, later retrieval, visible content edits, archive metadata and this report's time remain distinct. The 15,000,000,000-byte cumulative social allowance sits inside 30,000,000,000 shared media bytes, preserving lifetime accounting, both leases, the 15 GiB physical floor, 48 MiB recovery and complete-operation checks.

The three priorities were inherited completion-state defects, incomplete applicable source-era retrieval, and a narrow community frame. The former two-work diagnostic has no prospective acquisition or evaluation weight. A parsed root or processed prefix does not establish complete native inventory. An old Straight Dope item404 had stranded its chronological frame; the exact receipt remains preserved, while only that unavailable item is isolated in a local overlay. Remaining genuine topics continue. Partial Discourse post-ID chunks retain missing IDs and use exact native single-ID lookups. Provider denials, real host stops, Retry-After/backoff and quota restrictions remain distinct from local processing defects. A failed complete-operation reservation is retained as evidence. Committed metadata settlement can free the current operation reserve; original native cursors are reconsidered only when their guarded operation now fits, and provider denials/quota stops remain separate. Known pending Discourse post IDs can use smaller exact-ID native requests without discarding larger topic/index queues. Native transactions contain whole posts; individual IDs/bodies and the conservative per-operation reservation remain intact. Partially committed responses remain explicitly pending until all returned units are durable. The focused regression includes a native item beyond the first two in the same month, committed interruption/replay and preserved provider/host stops. Real durable Loads are recorded separately from the fixture.

Concrete historical community routes continued without a coverage, year-share, density, body-count or diversity finish gate. Python's large technical mailing-archive cursor remains held for a specifically evidenced uncovered technical source-era need; it did not drive this round. Source-native inventories and complete thread/comment bodies preserve neutral, noisy and nonclimate expression without semantic filtering. Communities, platform instances, software and mailing cross-lists are distinct metadata dimensions. Community development goals do not establish a sampling frame or stop rule.

| Contributing named community frame | New usable dated bodies | Observed new record span |
| --- | ---: | --- |
{community_table}

Straight Dope contributes its general discussion board, The Session its traditional-music discussions, ILX its ILE board subframe, and Tildes general-interest topics/replies. ILX follows the actual 2,000-second host delay, retains the inherited two-message count discrepancy and unknown local timezone, and uses native show-all links where feasible. The Session's documented chronological API provides pointers; complete rendered comment units supply bodies, currently visible attribution and ISO/UTC dates. Inline bios remain only in raw, with no member-profile or location requests and no inferred country. Tildes new-order chronology and all-time vote-ranked inventory retain separate selection mechanisms; the vote route is not a quality or chronology measure. Linked articles and previews are not independent authored forum bodies.

OSCEdays supplies a circular-economy civic/DIY discussion community. Its current contribution terms specify CC BY-SA4.0; historical contract-version continuity remains unresolved. Its root-page HTTP502 is preserved, and independently observed working native JSON routes do not clear a host stop. FIC Forum supplies an intentional-community forum. Its current Code of Conduct licence applies to that document, not member posts; no open member-text or republication grant is asserted. Bounded anonymous local-research retention follows the recorded operational interpretation with no named automation/local-retention ban. First observed native topics in 2015 and 2021 are observation bounds, not proven foundation dates or full archive denominators. Lettucecraft's explicit automation prohibition prevents body acquisition. Exact source observations and limits are in the finalized registry and evidence files. [OSCEdays terms](https://community.oscedays.org/tos), [FIC Forum conduct](https://forum.ic.org/tos).

Survive France supplies an anglophone resident community with observed native topic dates reaching December2009. Current user-contribution terms specify CC BY-NC-SA3.0; migrated current content, historical contract continuity and individual location remain unresolved. iNaturalist Community Forum supplies naturalist/citizen-science discussions with observed forum topics from February2019, distinct from its observation platform. Its separate www terms host returned collector HTTP403 and remains blocked; primary official terms were readable through the public web reader, and the independently verified forum host returned anonymous native metadata. No blocked host was reopened. Current terms default to CC BY-NC with contributor opt-outs, so individual post licences remain unresolved; commercial AI-training prohibition stays recorded. [Survive France terms](https://www.survivefrance.com/tos), [iNaturalist terms](https://www.inaturalist.org/pages/terms).

Elektronauts supplies a mixed creative-music/device-consumer community with observed native topics from July2013 and current CC BY-NC-SA3.0 contribution terms. Food Talk Central supplies food/dining discussions from observed September2015; member copyright remains with authors and no open post licence or blanket republication grant is asserted. Open Food Network Community supplies a cooperative/food-network forum with mixed software discussions from observed January2015. Its current terms publish a CC BY-NC-SA3 contribution clause but retain operator placeholders; legal issuer, individual third-party rights and historical applicability remain unresolved. These community frames are distinct from their software families, not verified independent parents or representative populations. WineBerserkers and Lettucecraft explicit automation bans were observed before native content requests. Cycling Without Age native metadataHTTP403 preserves a host stop and no body contribution. [Elektronauts terms](https://www.elektronauts.com/tos), [Food Talk Central terms](https://www.foodtalkcentral.com/tos), [Open Food Network terms](https://community.openfoodnetwork.org/tos).\n\nCoTech adds a cooperative-technology/worker and civic discussion frame with observed native topics from May2017; its current terms name the operator and publish CC BY-NC-SA3 user-contribution terms. GOATech adds an agricultural practitioner/open-technology frame with observed native topics from December2017; official community pointers are verified, but its contribution terms retain operator placeholders. Historical contract applicability and author roles remain unresolved in both frames. Neither their software nor their technology focus determines independent parent identity or general-public representativeness. [CoTech terms](https://community.coops.tech/tos), [GOATech terms](https://forum.goatech.org/tos).\n\nNew StackExchange gardening, cooking, cycling, travel and outdoor leads share the existing carrier and provider quota. A new community candidate does not count as contributing until eligible native bodies are durably loaded. No fresh credential, account, identity or local quota reset is authorized. Mail Archive's inherited HTTP502 with Retry-After and its conservative persisted carrier stop remain. Other actual access and rights limits remain preserved. The source registry distinguishes anonymous access, collection/retention interpretation, contribution licence and redistribution. Provenance annotations verify recorded identity/date/content mapping, not every statement's truth.

Small incremental native-metadata transactions and terminal changed-tranche checks use append boundaries accepted from the immediate predecessor. All {annotated_changed:,} changed versions have provenance annotations. Batches are at most 1,000 records, with actual journal and positive database growth measured against reserved complete-operation peaks. Completed predecessor exports stay charged as actual bytes rather than duplicated future reserves. Export and raw mapping checks concern this tranche; accepted old body/hash and integrity proofs are reused. Immutable prior reports, raw, IDs, versions, source stops and lifetime counters remain. Nine inherited date/era mappings and the inherited 43-key catalog difference remain explicit rather than silently repaired.

Matched Jan–August2016–2026 source/genre panels retain the baseline-contributing source panel alongside all current frames. Full-history and matched-window2026shares are distinct descriptive outputs; neither repaired volume nor a lower full-history share establishes a healthy or representative frame. Remaining community development and incomplete months stay visible. Source-month tables retain applicable-era uncertainty, full-calendar missingness and partial September context. Native Q&A creation dates before official closed-beta dates are retained with explicit historical community membership limitations; launch dates are never backdated to fit returned content. Where the native API supplies migration metadata, its original-site hint, question ID and on_date value are preserved as provider-reported evidence in a separate metadata table. The original external passage and historical body identity remain independently unverified. One early Gardening record explicitly reports an origin in Home Improvement, so its creation date does not establish Gardening presence before beta. The preserved adapter flag source_creation_before_documented_site_beta originally covered only Earth Science. Final temporal limitations recompute that condition from each documented beta timestamp and retain native migration fields; immutable original version flags remain unchanged. Neighbor counts use the preceding/following three months and incomplete boundary context. Peaks remain legitimate observations unless evidence identifies a structural defect; there is no flattening, downsampling or presumed climate-event attribution. Parent metrics are auxiliary. Dated original-text presence, later climate relevance, validated affect/risk associations and fear-specific interpretation remain separate evidence levels. No corpus topic, affect, fear or semantic exclusion labels were executed.
'''
            (out/'SOCIAL_COLLECTION_REPORT.md').write_text(report);file_receipt(out/'SOCIAL_COLLECTION_REPORT.md')
            t.atomic(out/'collection_manifest.json',snapshot);file_receipt(out/'collection_manifest.json')
            t.atomic(out/'delivery_file_manifest.json',{'at_utc':t.utc(),'files':files,'publication_boundary':'implementation, finalized collection tables/manifests and research summary; raw/queues/leases/checkpoints/dispatch controls remain local'})
            t.atomic(t.WORK/'CLOSED.json',snapshot)
    t.atomic(t.WORK/'WRITER_EXIT_AND_LEASE_RELEASE_REQUEST.json',{'at_utc':t.utc(),'pid':os.getpid(),'writer_mutex_released':True,'deadline_unchanged':True,'canonical_lease_changes_owned_by_coordinator':True})
    print(json.dumps({'closed':True,'new_core_texts':snapshot['new_core_texts'],'retained_core_total':snapshot['retained_core_total'],'observed_months':len(months),'raw_checks':rawstats}))

if __name__=='__main__':main()
