"""Close only this append phase; preserve the existing closed snapshot byte-for-byte."""
import json,csv,gzip,importlib.util,datetime as dt,collections,os
from pathlib import Path
import capacity_resume as phase
t=phase.t;e=phase.e
def local_module(name):
    spec=importlib.util.spec_from_file_location('phase_'+name,phase.PHASE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main():
    assert (t.WORK/'RUN_STOP.json').exists()
    assert t.read_json(t.WORK/'DELTA_TAIL_REGRESSION.json')['passed']
    assert t.read_json(t.WORK/'DELTA_CORE_SELECTION_REGRESSION.json')['passed']
    t.TERMINAL_OPERATION=True
    begin=phase.BASE['phase_started_at_utc'];out=t.WORK/'delta_summaries';out.mkdir(exist_ok=True)
    files=[]
    def export(c,name,sql,params=(begin,)):
        cur=c.execute(sql,params);p=out/(name+'.csv.gz')
        with gzip.open(p,'wt',newline='',encoding='utf8') as f:
            w=csv.writer(f);w.writerow([x[0] for x in cur.description]);w.writerows(cur)
        files.append({'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())})
    with t.writer():
        metadata=local_module('finalize_metadata').finalize(phase='delta_terminal',batch_records=200)
        st=t.state();reserve=phase.delta_tail_values(st['new_entity_versions'],st['new_entities'],st['new_entity_versions'])['delta_export_bytes']
        with t.shared(reserve,inflight_at=begin) as budget:
            c=e.db()
            ids=[r[0] for r in c.execute('SELECT entity_version_id FROM entity_versions WHERE first_retrieved_at>=?',(begin,))]
            assert len(ids)==st['new_entity_versions']
            assert c.execute('SELECT COUNT(*) FROM entity_versions v LEFT JOIN native_entities n ON n.entity_id=v.entity_id WHERE v.first_retrieved_at>=? AND n.entity_id IS NULL',(begin,)).fetchone()[0]==0
            checked=oldhash=0
            for vid,sha,body,text,core,old,oldsha in c.execute('SELECT v.entity_version_id,v.body_sha256,CASE WHEN b.first_retrieved_at<? THEN NULL ELSE COALESCE(b.body_original,v.body_original) END,CASE WHEN b.first_retrieved_at<? THEN NULL ELSE COALESCE(b.body_text,v.body_text) END,v.core_body_version_id,CASE WHEN b.first_retrieved_at<? THEN 1 ELSE 0 END,b.body_sha256 FROM entity_versions v LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id WHERE v.first_retrieved_at>=?',(begin,begin,begin,begin)):
                if old:assert sha==oldsha;oldhash+=1;continue
                assert (t.sha(body.encode()) if body else None)==sha
                if core:assert body and text
                checked+=1
            rawstats,rawfiles=local_module('raw_catalog').catalog(c,out);files.extend(rawfiles)
            for name,sql in {
                'new_native_entities':'SELECT * FROM native_entities WHERE first_retrieved_at>=?',
                'phase_entity_versions':'SELECT entity_version_id,entity_id,core_body_version_id,body_sha256,native_edited_at,native_revision,content_state,fixed_interval_state,readable_native_unit,independently_authored_body,content_license,licence_basis,flags_json,first_retrieved_at FROM entity_versions WHERE first_retrieved_at>=?',
                'phase_observations':'SELECT * FROM entity_observations WHERE retrieved_at>=?',
                'new_relations':'SELECT * FROM native_edges WHERE first_retrieved_at>=?',
                'affected_incoming_relations':'SELECT * FROM native_edges WHERE target_entity_id IN (SELECT entity_id FROM entity_versions WHERE first_retrieved_at>=?)',
                'phase_source_provenance':'SELECT * FROM entity_quality_annotations WHERE annotated_at>=?',
                'affected_native_aliases':'SELECT * FROM native_aliases WHERE entity_id IN (SELECT entity_id FROM entity_versions WHERE first_retrieved_at>=?)',
                'affected_publication_memberships':'SELECT * FROM publication_memberships WHERE entity_id IN (SELECT entity_id FROM entity_versions WHERE first_retrieved_at>=?)',
                'phase_structural_corrections':'SELECT * FROM structural_corrections WHERE corrected_at>=?',
                'phase_date_limits':"SELECT n.entity_id,n.source_id,n.native_created_at,v.content_state,v.fixed_interval_state,v.flags_json FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id WHERE v.first_retrieved_at>=? AND (n.native_created_at IS NULL OR v.fixed_interval_state!='inside_fixed_interval' OR json_extract(v.flags_json,'$.observed_identity_date_or_unit_conflict') IS NOT NULL)"
            }.items():export(c,name,sql)
            newcores=c.execute('SELECT p.persistent_post_id,p.source_id,p.native_created_at,MAX(COALESCE(a.independently_authored_body,v.independently_authored_body)) FROM posts p JOIN entity_versions v ON v.entity_id=p.persistent_post_id LEFT JOIN entity_quality_annotations a ON a.entity_version_id=v.entity_version_id WHERE p.persistent_post_id IN (SELECT entity_id FROM entity_versions WHERE first_retrieved_at>=?) AND NOT EXISTS (SELECT 1 FROM entity_versions old WHERE old.entity_id=p.persistent_post_id AND old.core_body_version_id IS NOT NULL AND old.first_retrieved_at<?) GROUP BY p.persistent_post_id',(begin,begin)).fetchall()
            assert len(newcores)==st['new_core_bodies']
            months=set()
            with (phase.ORIGINAL/'summaries/source_month_calendar.csv').open() as f:
                for row in csv.DictReader(f):
                    if int(row['usable_dated_independent_bodies']):months.add(row['month'])
            delta_months=collections.Counter();usable=0
            for eid,sid,date,authored in newcores:
                if authored:usable+=1;months.add(date[:7]);delta_months[sid,date[:7]]+=1
            p=out/'source_month_deltas.csv'
            with p.open('w',newline='',encoding='utf8') as f:
                writer=csv.writer(f);writer.writerow(['source_id','month','new_usable_dated_bodies','not_an_acquisition_target'])
                writer.writerows((sid,month,n,1) for (sid,month),n in sorted(delta_months.items()))
            files.append({'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())})
            c.close()
            baseline=phase.MEASURED
            snapshot={'at_utc':t.utc(),'phase_started_at_utc':begin,'original_deadline_at_utc':t.release(inflight_at=begin)['hard_deadline_at_utc'],'closed_snapshot_reference':'../CLOSED.json','new_core_texts':st['new_core_bodies'],'new_entities':st['new_entities'],'new_entity_versions':st['new_entity_versions'],'phase_charged_requests':st['requests']-phase.BASE['lifetime_charged_requests'],'lifetime_charged_requests':st['requests'],'lifetime_returned_keys':len(st['returned_object_ids']),'retained_core_total':baseline['counts']['posts']+st['new_core_bodies'],'usable_dated_body_total':baseline['publication_month_qualified_independent_body_entities']+usable,'pooled_observed_months':len(months),'source_year_deltas':st.get('source_year_deltas',{}),'pending_inherited_source_era_dates':9,'stop':t.read_json(t.WORK/'RUN_STOP.json'),'checks':{'phase_version_count_matches_Load_counters':True,'changed_foreign_identity_links_valid':True,'new_version_bodies_checked':checked,'accepted_body_hash_references_reused':oldhash,'new_raw_mapping':rawstats,'old_corpus_or_full_integrity_reaudit':False},'metadata':metadata,'delta_export_reserved_bytes':reserve,'export_start_capacity':budget,'semantic_labels':False}
            prior=phase.ORIGINAL_READ(phase.PHASE/'PHASE_START_RECEIPT.json')
            for path,sha in prior['closed_snapshot_hashes'].items():assert t.sha((phase.ORIGINAL/path).read_bytes())==sha,path
            snapshot['original_closed_snapshot_and_summary_hashes_preserved']=True
            implementation={'at_utc':t.utc(),'files':[{'path':name,'bytes':(t.WORK/name).stat().st_size,'sha256':t.sha((t.WORK/name).read_bytes())} for name in ['capacity_resume.py','delta_closeout.py','finalize_metadata.py','raw_catalog.py']],'reused_accepted_implementation_manifest':'../summaries/implementation_source_manifest.json','no_source_scope_or_database_migration':True}
            t.atomic(out/'implementation_append_manifest.json',implementation)
            files.append({'path':str((out/'implementation_append_manifest.json').relative_to(t.WORK)),'bytes':(out/'implementation_append_manifest.json').stat().st_size,'sha256':t.sha((out/'implementation_append_manifest.json').read_bytes())})
            report=f"""# Same-release capacity correction and historical append phase

The previous closed snapshot remains byte-for-byte preserved. Its early stop occurred before exports were generated, using a conservative projected export footprint. The final settlement at 04:12 UTC still failed next-operation preflight with a 487,233,227-byte export estimate plus bounded metadata journal allowance. Completed exports at 04:41 UTC actually measured 142,462,810 bytes. Reusing the old prospective tail model after that closeout would charge the already materialized exports again. A five-check fixture and live accounting verified that bounded new requests, metadata and delta exports fit the unchanged 8 GB social / 30 GB shared allowance. This continuation charges only its new tail; completed files remain in actual lifetime bytes. Physical floor, recovery, active leases, original owner/deadline and all source/provider protections remain.

This append phase adds **{st['new_core_bodies']:,} core texts**, {st['new_entities']:,} native entities and {st['new_entity_versions']:,} versions. The store now has {snapshot['retained_core_total']:,} retained core texts and {snapshot['usable_dated_body_total']:,} usable dated bodies across {len(months)}/465 observed study months. Source/year and month deltas are observations, not targets or completeness claims. Existing oldest-created forum, W3C and HN cursors continued; the large Python mailing-list contribution in the earlier snapshot remains a technical-community subframe and its concentration is explicit.

The phase stops for `{snapshot['stop']['reason']}`. Its original hard deadline remains **15:43:58.368759 AEST on 10 October 2026**. Publication eligibility remains 1988-01-01 through 2026-09-21, September partial. Native creation/sent dates, retrieval, edits and snapshots remain separate; historical public availability and historical body equality are not inferred.

Five local DNS failures received no HTTP response and stay charged with their original receipts. A digest-bound environment recovery produced separate charged attempts. Provider refusals, source rights, quota stops and inherited counters were not reset. Changed body/raw/identity/date checks and metadata exports apply only to this phase; the prior full integrity check is reused. Nine inherited era mappings remain pending. No full corpus scans, mandatory duplicate full exports, semantic filtering or emotion/fear labels ran. Original raw, IDs, body versions and the previous CLOSED.json, reports and hash manifests are preserved. This report and delta files supplement that snapshot rather than replace it.
"""
            (out/'DELTA_COLLECTION_REPORT.md').write_text(report)
            files.append({'path':str((out/'DELTA_COLLECTION_REPORT.md').relative_to(t.WORK)),'bytes':(out/'DELTA_COLLECTION_REPORT.md').stat().st_size,'sha256':t.sha((out/'DELTA_COLLECTION_REPORT.md').read_bytes())})
            t.atomic(out/'delta_collection_manifest.json',snapshot)
            t.atomic(out/'delivery_file_manifest.json',{'at_utc':t.utc(),'files':files,'delta_collection_manifest_sha256':t.sha((out/'delta_collection_manifest.json').read_bytes())})
            t.atomic(t.WORK/'PHASE_CLOSED.json',snapshot)
    t.atomic(t.WORK/'WRITER_EXIT_AND_LEASE_RELEASE_REQUEST.json',{'at_utc':t.utc(),'pid':os.getpid(),'writer_mutex_released':True,'original_deadline_unchanged':True,'canonical_lease_changes_owned_by_coordinator':True})
    print(json.dumps(snapshot),flush=True)
if __name__=='__main__':main()
