"""Changed-tranche closeout. Cumulative calendars and source panels are references."""
import collections,csv,gzip,json,os
import transport as t,entities as e,finalize_metadata,raw_catalog

def export(c,out,name,sql,args=()):
    cur=c.execute(sql,args);p=out/(name+'.csv.gz')
    with gzip.open(p,'wt',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow([v[0] for v in cur.description]);w.writerows(cur)
    return p

def receipt(p):return {'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())}

def terminal_reservations():
    """Consume the reserved terminal journal while preserving remaining output.

    Every terminal operation reserves at least the inherited 64 MiB journal.
    Future local and publication output, metadata,
    B's 8 MiB fixed allowance and A's 2 MiB future copy remain charged.
    Collection's 32 MiB native margin is never
    lowered; no source request or acquisition is run in this terminal phase.
    """
    original=t.preflight
    def guarded(scope,pending):
        model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');st=t.state();base=t.read_json(t.WORK/'INHERITED_BASELINE.json')
        nv=st['new_entity_versions'];ne=st['new_entities'];remaining=max(0,nv-model['already_annotated_changed_versions'])
        outputs=nv*(model['export_upper_bytes_per_version']+model['future_publication_bytes_per_version'])+ne*(model['export_upper_bytes_per_entity']+model['future_publication_bytes_per_entity'])+model['delta_export_fixed_allowance_bytes']+(st['requests']-base['lifetime_charged_requests'])*model['future_delta_receipt_bytes_per_request']+model.get('accepted_phase_A_future_publication_upper_bytes',0)
        b=original(scope,max(pending,model['bounded_metadata_journal_bytes'])+remaining*model['metadata_bytes_per_changed_version_upper_estimate']+outputs)
        b['terminal_reserve_components']={'accepted_phase_A_future_publication_upper_bytes':model.get('accepted_phase_A_future_publication_upper_bytes',0),'B_fixed_output_upper_bytes':model['delta_export_fixed_allowance_bytes'],'journal_operation_floor_bytes':model['bounded_metadata_journal_bytes'],'all_local_and_future_outputs_reserved_bytes':outputs,'unannotated_B_version_bytes':remaining*model['metadata_bytes_per_changed_version_upper_estimate']}
        return b
    t.TERMINAL_OPERATION=True;t.preflight=guarded

def main():
    assert t.read_json(t.WORK/'RUN_STOP.json')
    assert t.read_json(t.WORK/'ACCOUNTING_REGRESSION.json')['passed'] and t.read_json(t.WORK/'CURSOR_REGRESSION.json')['passed']
    calibration=t.read_json(t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION.json')
    regression=t.read_json(t.WORK/'TERMINAL_RESERVE_REGRESSION.json')
    assert calibration['passed'] and calibration['fixed_output_upper_bytes']==8*1048576
    assert calibration['phase_A_future_publication_locked_upper_bytes']==2*1048576
    assert regression['passed'] and regression['terminal_code_sha256']==t.sha((t.WORK/'delta_closeout.py').read_bytes())
    scope=t.read_json(t.SCOPE_PATH);begin=scope['earliest_network_and_load_start_at_utc'];base=t.read_json(t.WORK/'INHERITED_BASELINE.json');bounds=t.read_json(t.WORK/'APPEND_ROWID_BOUNDARIES.json')['bounds'];pre=t.REPO/base['predecessor_worker_reference'];out=t.WORK/'summaries';out.mkdir(exist_ok=True)
    assert t.sha((pre/'CLOSED.json').read_bytes())==base['predecessor_closed_snapshot_sha256']
    assert t.sha((pre/'summaries/delivery_file_manifest.json').read_bytes())==base['predecessor_delivery_manifest_sha256']
    references=t.read_json(pre/'summaries/inherited_metadata_references.json')['references']
    for name in ('source_month_deltas.csv','collection_manifest.json','native_operation_peak_summary.json'):
        manifest=t.read_json(pre/'summaries/delivery_file_manifest.json');item=next(x for x in manifest['files'] if x['path']=='summaries/'+name);p=pre/item['path'];assert t.sha(p.read_bytes())==item['sha256']
        references.append(item|{'path':str(p.relative_to(t.REPO)),'scope':'accepted phaseA; referenced without reexport'})
    terminal_reservations()
    with t.writer():
        t.atomic(t.WORK/'ACTIVE_PROCESS.json',{'at_utc':t.utc(),'pid':os.getpid(),'owner_thread_id':t.OWNER,'phase':'delta_terminal_closeout','hard_deadline_at_utc':scope['hard_deadline_at_utc']})
        meta=finalize_metadata.finalize(phase='terminal',batch_records=10)
        model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');model['already_annotated_changed_versions']+=meta['quality_annotations'];t.atomic(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json',model)
        st=t.state();files=[]
        with t.shared(t.footprint(),inflight_at=begin) as budget:
            c=e.db();c.execute('PRAGMA temp_store=MEMORY')
            c.execute('CREATE TEMP TABLE changed_versions(id TEXT PRIMARY KEY) WITHOUT ROWID');c.execute('INSERT INTO changed_versions SELECT entity_version_id FROM entity_versions WHERE rowid>?',(bounds['entity_versions'],))
            c.execute('CREATE TEMP TABLE changed_entities(id TEXT PRIMARY KEY) WITHOUT ROWID');c.execute('INSERT INTO changed_entities SELECT DISTINCT v.entity_id FROM changed_versions x CROSS JOIN entity_versions v ON v.entity_version_id=x.id')
            assert c.execute('SELECT COUNT(*) FROM changed_versions').fetchone()[0]==st['new_entity_versions']
            assert c.execute('SELECT COUNT(*) FROM native_entities WHERE rowid>?',(bounds['native_entities'],)).fetchone()[0]==st['new_entities']
            assert c.execute('SELECT COUNT(*) FROM posts WHERE rowid>?',(bounds['posts'],)).fetchone()[0]==st['new_core_bodies']
            assert c.execute('SELECT COUNT(*) FROM changed_versions x JOIN entity_quality_annotations a ON a.entity_version_id=x.id').fetchone()[0]==st['new_entity_versions']
            checked=reused=0
            for vid,digest,body,text,core,old,oldsha in c.execute('''SELECT v.entity_version_id,v.body_sha256,CASE WHEN b.rowid<=? THEN NULL ELSE COALESCE(b.body_original,v.body_original) END,CASE WHEN b.rowid<=? THEN NULL ELSE COALESCE(b.body_text,v.body_text) END,v.core_body_version_id,CASE WHEN b.rowid<=? THEN 1 ELSE 0 END,b.body_sha256 FROM changed_versions x CROSS JOIN entity_versions v ON v.entity_version_id=x.id LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id''',(bounds['versions'],)*3):
                if old:assert digest==oldsha;reused+=1;continue
                assert (t.sha(body.encode()) if body else None)==digest,vid
                if core:assert body and text,vid
                checked+=1
            rawstats,rawfiles=raw_catalog.catalog(c,out);files.extend(t.WORK/x['path'] for x in rawfiles)
            statements={
                'new_native_entities':('SELECT * FROM native_entities WHERE rowid>?',(bounds['native_entities'],)),
                'changed_entity_versions':('SELECT v.entity_version_id,v.entity_id,v.core_body_version_id,v.body_sha256,v.native_edited_at,v.native_revision,v.content_state,v.fixed_interval_state,v.readable_native_unit,v.independently_authored_body,v.content_license,v.licence_basis,v.flags_json,v.first_retrieved_at FROM changed_versions x CROSS JOIN entity_versions v ON v.entity_version_id=x.id',()),
                'new_entity_observations':('SELECT * FROM entity_observations WHERE rowid>?',(bounds['entity_observations'],)),
                'new_relations':('SELECT * FROM native_edges WHERE rowid>?',(bounds['native_edges'],)),
                'affected_incoming_relations':('SELECT r.* FROM native_edges r WHERE r.target_entity_id IN (SELECT id FROM changed_entities)',()),
                'new_attachment_metadata':('SELECT * FROM native_attachments WHERE rowid>?',(bounds['native_attachments'],)),
                'changed_source_provenance':('SELECT a.* FROM changed_versions x JOIN entity_quality_annotations a ON a.entity_version_id=x.id',()),
                'affected_native_aliases':('SELECT * FROM native_aliases WHERE entity_id IN (SELECT id FROM changed_entities)',()),
                'affected_publication_memberships':('SELECT * FROM publication_memberships WHERE entity_id IN (SELECT id FROM changed_entities)',()),
                'changed_date_limits':('SELECT n.entity_id,n.source_id,n.native_created_at,n.date_precision,v.content_state,v.fixed_interval_state,v.flags_json FROM changed_versions x CROSS JOIN entity_versions v ON v.entity_version_id=x.id JOIN native_entities n ON n.entity_id=v.entity_id WHERE n.native_created_at IS NULL OR v.fixed_interval_state!=\'inside_fixed_interval\' OR json_extract(v.flags_json,\'$.observed_identity_date_or_unit_conflict\') IS NOT NULL',())}
            for name,(sql,args) in statements.items():files.append(export(c,out,name,sql,args))
            delta=collections.Counter();source_dates={};usable=0
            for eid,sid,date in c.execute('SELECT persistent_post_id,source_id,native_created_at FROM posts WHERE rowid>?',(bounds['posts'],)):
                authored=c.execute('SELECT a.independently_authored_body FROM entity_versions v JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE v.entity_id=? ORDER BY v.rowid DESC LIMIT 1',(eid,)).fetchone()
                assert authored is not None
                if authored[0]:delta[sid,date[:7]]+=1;usable+=1
                source_dates.setdefault(sid,[]).append(date)
            newbody=c.execute('SELECT COUNT(*) FROM versions WHERE rowid>?',(bounds['versions'],)).fetchone()[0];c.close()
            prior=collections.Counter()
            calendar_reference=next(x for x in references if x['path'].endswith('source_month_calendar.csv'))
            with (t.REPO/calendar_reference['path']).open() as f:
                for row in csv.DictReader(f):prior[row['source_id'],row['month']]+=int(row['usable_dated_independent_bodies'])
            with (pre/'summaries/source_month_deltas.csv').open() as f:
                for row in csv.DictReader(f):prior[row['source_id'],row['month']]+=int(row['new_usable_bodies'])
            assert sum(prior.values())==base['usable_dated_bodies'];current=prior+delta;months={m for (sid,m),n in current.items() if n}
            p=out/'source_month_deltas.csv'
            with p.open('w',encoding='utf8',newline='') as f:
                w=csv.writer(f);w.writerow(['source_id','month','baseline_usable_bodies','new_usable_bodies','current_usable_bodies','reporting_only'])
                for (sid,m),n in sorted(delta.items()):w.writerow([sid,m,prior[sid,m],n,current[sid,m],1])
            files.append(p)
            allmonths=[f'{y:04}-{m:02}' for y in range(1988,2027) for m in range(1,13) if f'{y:04}-{m:02}'<='2026-09'];affected=set()
            for sid,m in delta:
                i=allmonths.index(m);affected.update((sid,q) for q in allmonths[max(0,i-3):i+4])
            p=out/'changed_source_month_neighbor_context.csv'
            with p.open('w',encoding='utf8',newline='') as f:
                w=csv.writer(f);w.writerow(['source_id','month','baseline_count','delta_count','current_count','previous_three_counts','following_three_counts','incomplete_boundary_context','greater_than_all_available_neighbors_candidate','event_attribution'])
                for sid,m in sorted(affected):
                    i=allmonths.index(m);before=[current[sid,q] for q in allmonths[max(0,i-3):i]];after=[current[sid,q] for q in allmonths[i+1:i+4]];neighbors=before+after
                    w.writerow([sid,m,prior[sid,m],delta[sid,m],current[sid,m],json.dumps(before),json.dumps(after),int(len(neighbors)<6 or i>=len(allmonths)-4),int(bool(neighbors) and current[sid,m]>max(neighbors)),'none; independent dated evidence required'])
            files.append(p)
            p=out/'source_era_deltas.csv'
            with p.open('w',encoding='utf8',newline='') as f:
                w=csv.writer(f);w.writerow(['source_id','new_usable_bodies','earliest_new_publication','latest_new_publication','native_queue_cursor_reference','source_existence_claim'])
                for sid,dates in sorted(source_dates.items()):w.writerow([sid,sum(n for (s,m),n in delta.items() if s==sid),min(dates),max(dates),'local NATIVE_CURSORS.json; frozen prior frame referenced','observed new records only; no founding or complete historical access inference'])
            files.append(p)
            loads=[json.loads(x) for x in (t.WORK/'LOADS.jsonl').read_text().splitlines()];assert all(x['observed_additional_disk_peak_upper_bytes']<=x['reserved_operation_bytes'] for x in loads)
            p=out/'native_operation_peak_summary.json';t.atomic(p,{'at_utc':t.utc(),'changed_loads_checked':len(loads),'passed':True,'max_observed_complete_peak_upper_bytes':max((x['observed_additional_disk_peak_upper_bytes'] for x in loads),default=0),'max_ratio_to_reserved':max((x['observed_additional_disk_peak_upper_bytes']/x['reserved_operation_bytes'] for x in loads),default=0),'accepted_prior_peak_summary_reference':next(x for x in reversed(references) if x['path'].endswith('native_operation_peak_summary.json'))});files.append(p)
            p=out/'inherited_metadata_references.json';t.atomic(p,{'at_utc':t.utc(),'references':references,'full_calendars_registries_frames_panels_not_reexported':True,'additional_accounting_roots':scope['social_additional_accounting_roots'],'additional_social_bytes_at_binding':scope['social_publication_bytes_at_binding']});files.append(p)
            cursors=t.read_json(t.WORK/'NATIVE_CURSORS.json');snapshot={'at_utc':t.utc(),'publication_interval':scope['publication_interval'],'partial_end_month':True,'authorized_start_at_utc':begin,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'stop':t.read_json(t.WORK/'RUN_STOP.json'),'new_core_texts':st['new_core_bodies'],'new_usable_dated_bodies':usable,'retained_core_total':base['counts']['posts']+st['new_core_bodies'],'usable_dated_body_total':base['usable_dated_bodies']+usable,'pooled_observed_months':len(months),'study_months':465,'new_pooled_months':sorted(months-{m for (sid,m),n in prior.items() if n}),'new_entities':st['new_entities'],'new_entity_versions':st['new_entity_versions'],'new_body_versions':newbody,'native_entities_total':base['counts']['native_entities']+st['new_entities'],'entity_versions_total':base['counts']['entity_versions']+st['new_entity_versions'],'round_charged_requests':st['requests']-base['lifetime_charged_requests'],'lifetime_charged_requests':st['requests'],'lifetime_returned_native_keys':len(st['returned_object_ids']),'inherited_key_catalog_difference':base['current_returned_key_catalog_difference'],'source_year_deltas':st['source_year_deltas'],'source_month_delta_rows':len(delta),'checks':{'append_counts_match_Load_counters':True,'changed_bodies_checked':checked,'accepted_body_hash_references_reused':reused,'changed_raw_mapping':rawstats,'old_body_or_raw_reaudit':False,'native_load_complete_peak_exceedances':0,'all_changed_versions_provenance_annotated':True},'metadata_terminal_counts':meta,'export_start_capacity':budget,'predecessor_closed_snapshot_sha256':base['predecessor_closed_snapshot_sha256'],'predecessor_delivery_manifest_sha256':base['predecessor_delivery_manifest_sha256'],'semantic_or_affect_labels_executed':False,'fixed_output_allowance_reduced_after_evidence_and_amendment':True,'smaller_complete_response_bound':64*1024,'phase':'B append inside same four-hour release','phase_A_prose_unit_correction':t.read_json(t.WORK/'PHASE_A_PROSE_UNIT_CORRECTION.json'),'saved_context_suffix_restored':t.read_json(t.WORK/'FIRST_APPEND_REAL_LOAD_CURSOR_CAPACITY.json'),'B_fixed_output_upper_bytes':model['delta_export_fixed_allowance_bytes'],'accepted_phase_A_future_publication_upper_bytes':model['accepted_phase_A_future_publication_upper_bytes'],'terminal_reserve_regression':regression,'fixed_output_peak_calibration':calibration,'first_append_true_body_Load_proof':t.read_json(t.WORK/'FIRST_APPEND_TRUE_BODY_LOAD_CURSOR_CAPACITY.json'),'cumulative_outputs_reexported':False,'source_states':[{k:x.get(k) for k in ('source','frame','state','chunk_offset','post_offset','topic_offset','page','native_next_url','new_core_bodies','oldest_returned_publication_at')} for x in cursors],'source_cursor_count_basis':'fully settled operations only; partial committed whole-native rows are counted in Load counters and source-era deltas','remaining_narrowness_sparse_months_or_limits_not_declared_healthy':True,'successor_automatically_authorized':False}
            p=out/'SOCIAL_COLLECTION_REPORT.md'
            text=f'''# H+1 same-deadline social append correction\n\nThe authorized fixed interval was {begin} through {scope['hard_deadline_at_utc']}; preparation was included. Source production stopped at {snapshot['stop']['at_utc']} for `{snapshot['stop']['reason']}`. No rolling successor is authorized.\n\nThe phase added {snapshot['new_core_texts']:,} retained core texts and {usable:,} usable dated independently authored bodies, {st['new_entities']:,} native entities and {st['new_entity_versions']:,} immutable versions. Accepted totals are {snapshot['retained_core_total']:,} retained core / {snapshot['usable_dated_body_total']:,} usable dated bodies across {len(months)}/465 observed months. These are dated presence and readable-text results, not archive completeness, climate relevance, affect prevalence, or a comparable public fear series. The publication interval stays 1988-01-01 through 2026-09-21; September 2026 remains partial. Later retrieval does not certify the historical body version.\n\nThe coordinator's H+1 correction separated completed phaseA local exports (already in actual bytes) from genuinely outstanding output. B reserves only its new dynamic local/future output, an evidenced 8 MiB fixed allowance including an additional4 MiB for the complete joint PNG/report/metadata output, and separately locked2 MiB for phaseA future publication. Native32 MiB, journal64 MiB, both sides'901/version and75/entity,2582/unannotated-new-version and1024/newrequest remain. The empty/small and atomic-coexistence fixture measured write peak is preserved. The terminal and verification code paths explicitly reserve phaseA's2 MiB, confirmed by actual guarded preflight regression. No joint PNG or outside publication is created by the collector. The coordinator must measure all joint final artifacts plus maximum atomic temp at<=4 MiB and each artifact<=1 MiB before publication. All source/provider stops and lifetime counters remain.

The one phaseA pending native mapping was topic736 context_container, rather than an uncommitted authored post as its prose stated. PhaseA's frozen bytes/counts are preserved. B completed only that saved suffix, without reloading the accepted19-record prefix or counting the container as authored text, then continued real full-post acquisition. The append's date/body/provenance checks concern only new rows; phaseA accepted body/raw proofs remain reused.

Named whole-post surplus and chronological discussion routes use compact offsets referencing the frozen predecessor queues. Cursor advance follows durable Load. Native partial returns, context containers and unavailable bodies remain separate. Source creation, publication, edit and retrieval times remain distinct. Neutral/routine bodies are retained. Oversized operations and source denials remain pending with factual evidence; no fragments or guessed IDs establish complete native text.\n\nThis delivery contains changed source-month/neighbor, identity, provenance, date and relation rows. The cumulative calendar, registry, frames and source/era panels remain hash-bound predecessor references. No cumulative reexport, deletion, database migration or semantic exclusion occurred. Sixteen inherited discussion-community families and seven Q&A sites remain distinct classification units; this phase does not establish more than 20 strict discussion forums or resolved independent parents. Existing technical bulk concentration and early-era source gaps remain research limitations.\n\nImplementation fixes, actual new Load and external/resource limitations are reported separately. Source presence does not validate claim truth, speaker role/country, historical access, representativeness, affect, or fear. Parent/coverage/count metrics did not guide collection or stopping. Raw, receipts, queues, owner state and controls remain local; the coordinator owns main publication.\n'''
            p.write_text(text);files.append(p)
            code=[p for p in t.WORK.glob('*.py')]+[t.WORK/'schema_v2.sql',t.WORK/'schema_legacy.sql']
            p=out/'implementation_source_manifest.json';t.atomic(p,{'at_utc':t.utc(),'files':[receipt(q) for q in sorted(code)]});files.append(p)
            output_bytes=sum(p.stat().st_size for p in files);local_bound=st['new_entity_versions']*model['export_upper_bytes_per_version']+st['new_entities']*model['export_upper_bytes_per_entity']+model['delta_export_fixed_allowance_bytes']+(st['requests']-base['lifetime_charged_requests'])*model['future_delta_receipt_bytes_per_request']
            assert sum(p.stat().st_size for p in code)<=calibration['allocations']['new_local_implementation_code_schema_tests']
            assert output_bytes+sum(p.stat().st_size for p in code)+131072<=local_bound
            snapshot['delta_delivery_bytes_before_manifest']=output_bytes;snapshot['local_delta_output_reserved_upper_bytes']=local_bound;snapshot['future_publication_reserved_upper_bytes']=st['new_entity_versions']*model['future_publication_bytes_per_version']+st['new_entities']*model['future_publication_bytes_per_entity']+model['delta_export_fixed_allowance_bytes'];snapshot['implementation_files']=len(code)
            phase_A=t.read_json(pre/'CLOSED.json')
            combined={'at_utc':t.utc(),'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'original_authorized_start_at_utc':begin,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'no_new_window':True,'phase_A_closed_reference':str((pre/'CLOSED.json').relative_to(t.REPO)),'phase_A_closed_sha256':base['predecessor_closed_snapshot_sha256'],'phase_A_delivery_manifest_sha256':base['predecessor_delivery_manifest_sha256'],'phase_A_new_core_texts':phase_A['new_core_texts'],'append_B_new_core_texts':snapshot['new_core_texts'],'combined_new_core_texts':phase_A['new_core_texts']+snapshot['new_core_texts'],'phase_A_round_charged_requests':phase_A['round_charged_requests'],'append_B_round_charged_requests':snapshot['round_charged_requests'],'combined_round_charged_requests':phase_A['round_charged_requests']+snapshot['round_charged_requests'],'current_retained_core_total':snapshot['retained_core_total'],'current_usable_dated_body_total':snapshot['usable_dated_body_total'],'current_observed_months':snapshot['pooled_observed_months'],'lifetime_charged_requests':snapshot['lifetime_charged_requests'],'lifetime_returned_native_keys':snapshot['lifetime_returned_native_keys'],'accepted_A_future_copy_upper_bytes':model['accepted_phase_A_future_publication_upper_bytes'],'B_fixed_upper_bytes':model['delta_export_fixed_allowance_bytes'],'joint_PNG_metadata_report_upper_bytes_in_B_fixed':4*1048576,'joint_publication_final_plus_max_temp_must_be_checked_before_publication':True,'worker_local_joint_PNG_or_external_publication_created':False,'phase_A_topic736_prose_erratum':snapshot['phase_A_prose_unit_correction'],'source_presence_not_archive_completeness_or_emotion_prevalence':True,'no_old_raw_body_or_database_wide_reaudit':True}
            p=out/'combined_collection_manifest.json';t.atomic(p,combined);files.append(p)
            t.atomic(t.WORK/'CLOSED.json',snapshot);p=out/'collection_manifest.json';t.atomic(p,snapshot);files.append(p)
            t.atomic(out/'delivery_file_manifest.json',{'at_utc':t.utc(),'files':[receipt(p) for p in files],'publication_boundary':'implementation and finalized changed tables/manifests/research summary; referenced prior cumulative outputs; runtime/raw/queues/controls stay local'})
        t.atomic(t.WORK/'TERMINAL_COMPLETE.json',{'at_utc':t.utc(),'pid':os.getpid(),'source_requests_during_closeout':0,'delivery_manifest_sha256':t.sha((out/'delivery_file_manifest.json').read_bytes()),'closed_sha256':t.sha((t.WORK/'CLOSED.json').read_bytes())})
    print(json.dumps({k:snapshot[k] for k in ('at_utc','new_core_texts','usable_dated_body_total','round_charged_requests','pooled_observed_months')}))

if __name__=='__main__':main()
