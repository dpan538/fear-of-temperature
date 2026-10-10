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
    original=t.WORK.parent.parent/'20261010_four_hour_historical_repair'/'worker'
    values=collections.Counter()
    with (original/'summaries/source_month_calendar.csv').open() as f:
        for row in csv.DictReader(f):values[row['source_id'],row['month']]+=int(row['usable_dated_independent_bodies'])
    with (original/'capacity_resume_1520/delta_summaries/source_month_deltas.csv').open() as f:
        for row in csv.DictReader(f):values[row['source_id'],row['month']]+=int(row['new_usable_dated_bodies'])
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
            prior_peak=t.read_json(t.WORK/'NATIVE_PEAK_POST_INTEGRATION_VERIFICATION.json');assert prior_peak['passed']
            remaining_loads=[json.loads(line) for line in (t.WORK/'LOADS.jsonl').read_text().splitlines() if line.strip()]
            remaining_loads=[r for r in remaining_loads if r['at_utc']>prior_peak['at_utc']]
            peak_classes={}
            for r in remaining_loads:
                observed=r['observed_additional_disk_peak_upper_bytes'];reserved=r['reserved_operation_bytes']
                assert observed<=reserved,(r['request_id'],observed,reserved)
                sid=r['frame_id'].split(':',1)[0]
                item=peak_classes.setdefault(sid,{'loads_checked':0,'max_observed_complete_peak_upper_bytes':0,'max_ratio_to_reserved':0,'exceedances':0})
                item['loads_checked']+=1;item['max_observed_complete_peak_upper_bytes']=max(item['max_observed_complete_peak_upper_bytes'],observed);item['max_ratio_to_reserved']=max(item['max_ratio_to_reserved'],observed/reserved)
            peak_summary={'at_utc':t.utc(),'accepted_prior_verification_at_utc':prior_peak['at_utc'],'accepted_prior_verified_loads':prior_peak['loads_checked'],'remaining_changed_loads_checked':len(remaining_loads),'source_classes':peak_classes,'passed':True,'original_precalibration_overshoot_and_receipts_preserved':True,'old_body_or_raw_reaudit':False}
            t.atomic(out/'native_operation_peak_summary.json',peak_summary);file_receipt(out/'native_operation_peak_summary.json')
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
            frames=c.execute('SELECT * FROM acquisition_frames').fetchall()
            newbodyversions=c.execute('SELECT COUNT(*) FROM versions WHERE rowid>?',(bounds['versions'],)).fetchone()[0]
            c.close()
            predecessor=t.WORK.parent.parent/'20261010_four_hour_historical_repair'/'worker'
            assert t.sha((predecessor/'CLOSED.json').read_bytes())==baseline['predecessor_closed_snapshot_sha256']
            assert t.sha((predecessor/'capacity_resume_1520/delta_summaries/delta_collection_manifest.json').read_bytes())==baseline['predecessor_phase_manifest_sha256']
            snapshot={'at_utc':t.utc(),'publication_interval':scope['publication_interval'],'partial_end_month':True,'authorized_start_at_utc':begin,'hard_deadline_at_utc':scope['hard_deadline_at_utc'],'stop':t.read_json(t.WORK/'RUN_STOP.json'),'new_core_texts':st['new_core_bodies'],'new_usable_dated_bodies':usable,'retained_core_total':baseline['counts']['posts']+st['new_core_bodies'],'usable_dated_body_total':baseline['usable_dated_bodies']+usable,'pooled_observed_months':len(months),'study_months':465,'new_entities':st['new_entities'],'new_entity_versions':st['new_entity_versions'],'new_body_versions':newbodyversions,'native_entities_total':baseline['counts']['native_entities']+st['new_entities'],'entity_versions_total':baseline['counts']['entity_versions']+st['new_entity_versions'],'round_charged_requests':st['requests']-baseline['lifetime_charged_requests'],'lifetime_charged_requests':st['requests'],'lifetime_returned_native_keys':len(st['returned_object_ids']),'inherited_key_catalog_difference':43,'pending_inherited_source_era_dates':9,'source_year_deltas':st.get('source_year_deltas',{}),'source_month_delta_rows':len(delta),'checks':{'append_version_and_entity_counts_match_Load_counters':True,'changed_identity_links_valid':True,'changed_bodies_checked':checked,'accepted_body_hash_references_reused':reused,'changed_raw_mapping':rawstats,'predecessor_full_integrity_result_reused':True,'old_body_or_raw_reaudit':False},'metadata':metadata,'saved_response_reconciliation':recovery,'export_start_capacity':budget,'reserved_export_and_metadata_journal_bytes':reserve,'predecessor_closed_snapshot_sha256':baseline['predecessor_closed_snapshot_sha256'],'predecessor_delta_manifest_sha256':baseline['predecessor_phase_manifest_sha256'],'semantic_or_affect_labels_executed':False}
            snapshot['checks']['all_changed_versions_have_native_quality_annotations']=annotated_changed
            snapshot['checks']['remaining_changed_native_load_peak_reservations']=peak_summary
            snapshot['metadata_counts_basis']='terminal phase only; completed midwindow annotations are included in the all-changed-version check and exported provenance'
            snapshot['midwindow_metadata_settlement']=[{'revision':r['revision'],'actual_annotated_new_versions':r['actual_annotated_new_versions'],'source_requests':r['source_requests'],'resume_possible':r['resume_possible']} for p in sorted(t.WORK.glob('DURABILITY_FLUSH_*_RECEIPT.json')) for r in [t.read_json(p)]]
            
            for source in sources:
                sid=source['source_id'];observed=sorted(m for (name,m),n in calendar.items() if name==sid and n)
                source['current_collection_observation']={'usable_dated_corpus_bodies':sum(n for (name,m),n in calendar.items() if name==sid),'new_usable_dated_bodies':sum(n for (name,m),n in delta.items() if name==sid),'first_observed_core_month':observed[0] if observed else None,'last_observed_core_month':observed[-1] if observed else None,'source_presence_only_not_archive_completeness_or_emotion_prevalence':True,'inherited_preparation_statements_are_historical':True}
            t.atomic(out/'source_registry_final.json',sources);file_receipt(out/'source_registry_final.json')
            for name in ['BROADER_SOURCE_ADMISSION_LIMITS.json','SOURCE_TEMPORARY_STOP_DIAGNOSTIC.json','ILX_SOURCE_RETURN_COUNT_LIMIT.json']:
                if (t.WORK/name).exists():t.atomic(out/name,t.read_json(t.WORK/name));file_receipt(out/name)
            t.atomic(out/'source_frame_definitions.json',{'columns':['frame_id','source_id','frame_type','selection_rule','existence_lower_bound','actor_role_basis','metadata_json'],'rows':frames,'current_native_selection_evidence':[{k:f.get(k) for k in ['frame','source','kind','selection_rule_evidence'] if k in f} for f in t.read_json(t.WORK/'FRONTIERS.json') if f.get('selection_rule_evidence')]});file_receipt(out/'source_frame_definitions.json')
            code=['bootstrap.py','collect.py','transport.py','entities.py','archive_adapter.py','lemmy_adapter.py','public_html_adapter.py','thesession_adapter.py','finalize_metadata.py','raw_catalog.py','incremental_closeout.py','schema_v2.sql','schema_legacy.sql']
            t.atomic(out/'implementation_source_manifest.json',{'at_utc':t.utc(),'files':[{'path':n,'bytes':(t.WORK/n).stat().st_size,'sha256':t.sha((t.WORK/n).read_bytes())} for n in code],'execution_controls_and_owner_handoffs_are_local':True});file_receipt(out/'implementation_source_manifest.json')
            report=f'''# Broader historical social collection

This bounded continuation adds **{st['new_core_bodies']:,} retained core texts**, {st['new_entities']:,} native entities and {st['new_entity_versions']:,} native versions. Derived source-quality checks yield {usable:,} new usable dated bodies. The cumulative store contains {snapshot['retained_core_total']:,} retained core texts and {snapshot['usable_dated_body_total']:,} usable dated bodies across {len(months)}/465 observed study months. Counts describe the accepted source frames and recovered corpus; they do not establish complete archives, population representation, climate relevance, emotion prevalence or a comparable multi-role time series.

The authorization runs from 10 October 2026 15:43:58.368759 through 19:43:58.368759 AEST. Acquisition stops for `{snapshot['stop']['reason']}`. Publication eligibility remains **1988-01-01 through 2026-09-21**, with September partial; retrieval, source content edits, archive capture and snapshot time remain separate. The larger allocation is **15,000,000,000 cumulative social bytes inside 30,000,000,000 shared media bytes**, preserving counters, active leases, 15 GiB physical floor, 48 MiB recovery and actual complete-operation safeguards.

Historical native forum, mailing-archive and chronological API routes continued beyond any old coverage floor. The Python mailing archive remains a technical-community subframe; its large contribution is visible in source/year and month deltas. Tildes contributes source-native general-interest topics/replies through documented public HTML. New-order/all-time and source vote-ranked/all-time inventories have different selection mechanisms and unknown total denominators. Linked articles stay link metadata, index previews stay previews, and bodyless topics and later out-of-interval replies remain preserved native evidence. Ordinary authors retain copyright; the documentation/wiki licence is not assigned to their posts.

The original E-Democracy project links the recovered civic-newswire archives. These are archival reproductions of civic participation newsletters, with sender, quoted speakers and original authorship kept distinct. The three archive/list namespaces remain separate; cross-list aliases and original Message-ID equivalence are unresolved. Displayed timestamps retain their literal offset, while reconciliation against nonpublic original email headers remains unavailable. This civic-newswire channel is not assumed to represent ordinary public expression as a whole. Local HTML copying is explicitly permitted by the archive, subject to rate limits; public access is not a blanket redistribution licence. [Original project archive pointer](https://blog.e-democracy.org/posts/3193), [archive download conditions](https://www.mail-archive.com/faq.html#download).

The original archived Minneapolis Issues group explicitly identifies its discussions as public to view and links surviving archives covering 2000 and 2001-2005. These two local civic archives now use source-documented full-interval date searches sorted oldest first, without title/body/topic terms. Only whole native message pages enter the readable core; expanded search fragments demonstrably truncate longer bodies and stay raw index evidence. Citizens, elected officials and community leaders are heterogeneous participants, so forum location and channel do not assign each author's country or discourse role. The two archive namespaces and any cross-server work equivalence remain separate and unresolved. [Original archived public group and archive pointers](https://web.archive.org/web/20240425042924/http://forums.e-democracy.org/groups/mpls).

ILX now contributes own public forum posts/replies from source-returned ILE board threads, sorted by the displayed start month/year. The initial thread returns 100 complete individual messages but explicitly skips 10,654 intervening messages; its native show-all link was acquired after the 2,000-second delay and restored the intervening own-message units. The current all-view returns 10,752 own-message units, two fewer than the default count plus its skip badge; that arithmetic discrepancy remains unresolved without invented IDs or deletion reasons. The valid multi-year volume is retained, with source-year/month context and no climate-event attribution. Message IDs retain board/thread scope and native anchors; author display names are not verified account IDs. Local timestamps retain unknown timezone and possible migrated midnight precision. Quoted media passages stay within each forum author’s utterance, not newspaper articles. ILX access follows its actual 2,000-second crawl delay and public-board restrictions. The Boing Boing BBS redirects to a premium destination and its separate parent returned HTTP403; no account or premium route was used. The original E-Democracy host redirect, reported archive loss and TLS hostname failure remain recorded. Source-linked archival alternatives, access limits and unresolved mappings remain explicit. The recovered Mail Archive carrier returned HTTP502 with Retry-After 60 on a newswire message; the inherited transport policy then preserved a carrier-wide stop. This is recorded as a temporary server response with conservative persisted acquisition consequences, not proven permanent prohibition. No host stop was cleared. Static E-Democracy topic indexes remain metadata; particular topic routes returned unavailable captures or recorded original redirects, rather than verified authored bodies. MetaFilter robots/FAQ returned HTTP403. Urban75 public board/index navigation was readable, but its actual terms retain author and compilation rights and require permission for use elsewhere; it remains metadata-only preparation with collection/retention unresolved for this corpus. No account or permission request was made. The source registry and frame definitions record actual observations; source presence or provenance checks do not verify every statement's truth.

The Session supplies a distinct traditional-music community discussion subframe through native creation-ordered inventory, starting with observed June 2001 discussions. The operator documents a read-only API and explicitly exports complete HTML for local browsing/copies. The archive is over 2GB compressed and about 10GB expanded, so that whole-copy route was not executed. The documented API supplies chronological topic pointers; complete rendered HTML comment units supply readable bodies, native IDs, ISO/UTC publication times and currently visible attribution. The cross-check found two comments whose API attribution remained present despite current rendered anonymity; the raw discrepancy is preserved, and HTML-anonymous authors stay anonymous. Member profiles and locations were not requested separately. Bundled inline member bios remain in the preserved raw HTML and are not extracted to native author metadata or used to infer country. An open licence for individual member text and blanket redistribution remain unverified. First observed discussion dates do not establish the whole source foundation or pre-2001 applicability. [Operator API and archive documentation](https://thesession.org/api).

The first large native batch exceeded the former body-byte-only disk reservation. Its original receipt is preserved. Three measured journals informed a per-returned-record allowance, with database growth and future observed complete disk peaks recorded separately. Export selection uses validated append boundaries, retaining source retrieval timestamps even when an older saved response is reused. January 2009 returned HTTP200 with a declared 17,080,359-byte monthly representation, slightly above the local 16MiB bound. The exact attempt is preserved, with a separately charged digest-bound 32MiB recovery and finite raw/decompression limits. Later native monthly URLs were stranded by the local-bound-to-source-stop classification; this queue effect is repaired while provider denials remain preserved. HTTP Last-Modified is representation metadata, kept separate from native message publication and verified author edit time. Checks apply to this changed tranche and reuse accepted predecessor integrity evidence. Nine inherited era mappings remain pending. Identical body hashes remain candidates; raw text, identities, versions, valid volume peaks and earlier frozen reports remain preserved.

A complete-operation capacity block triggered committed maintenance and settlement of already-acquired native metadata. Interrupted partial settlements retain their committed rows and evidence. Batches of at most 1,000 records preserve dynamic metadata and journal reservations. An uncached scandir traversal matched all 11 accounting-root totals and the symlink fixture; every preflight still measures current bytes. The actual metadata settlement replaces the conservative outstanding estimate without resetting counters, changing the allocation or extending the deadline. Only resource-blocked frontiers are eligible to resume after another complete-operation preflight; provider and access stops remain preserved. All {annotated_changed:,} changed native versions have source-quality annotations, including earlier settlement phases. These annotations describe provenance and structural limitations, not semantic or emotion labels.

Source-month neighbor counts include the preceding/following three months and incomplete boundary context. Relative count candidates are reporting diagnostics, never deletion, downsampling, acquisition weighting or completion targets. No peak is attributed to a climate event without independent dated evidence. Parent statistics remain auxiliary. Climate/warming retrieval and similarity validation are deferred; affect/risk associations and fear-specific interpretations require later validation and traceable original passages. No topic, affect, fear or semantic exclusion labels were executed in this collection.
'''
            (out/'SOCIAL_COLLECTION_REPORT.md').write_text(report);file_receipt(out/'SOCIAL_COLLECTION_REPORT.md')
            t.atomic(out/'collection_manifest.json',snapshot);file_receipt(out/'collection_manifest.json')
            t.atomic(out/'delivery_file_manifest.json',{'at_utc':t.utc(),'files':files,'publication_boundary':'implementation, finalized collection tables/manifests and research summary; raw/queues/leases/checkpoints/dispatch controls remain local'})
            t.atomic(t.WORK/'CLOSED.json',snapshot)
    t.atomic(t.WORK/'WRITER_EXIT_AND_LEASE_RELEASE_REQUEST.json',{'at_utc':t.utc(),'pid':os.getpid(),'writer_mutex_released':True,'deadline_unchanged':True,'canonical_lease_changes_owned_by_coordinator':True})
    print(json.dumps({'closed':True,'new_core_texts':snapshot['new_core_texts'],'retained_core_total':snapshot['retained_core_total'],'observed_months':len(months),'raw_checks':rawstats}))

if __name__=='__main__':main()
