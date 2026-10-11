"""Isolated fixed-output peak calibration; no corpus or network access."""
import csv,gzip,io,json,os
from pathlib import Path
import transport as t

FIX=t.WORK/'calibration_fixtures';measurements=[]
def atomic_bytes(path,content):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.pending')
    before=t.bytes_under(FIX);old=path.stat().st_size if path.exists() else 0
    with temp.open('wb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    peak=t.bytes_under(FIX);assert peak==before+len(content)
    measurements.append({'path':str(path.relative_to(t.WORK)),'old_final_bytes':old,'temporary_bytes':len(content),'coexistence_peak_bytes':peak,'previous_fixture_bytes':before})
    temp.replace(path)

def csv_bytes(headers,rows):
    b=io.StringIO(newline='');w=csv.writer(b);w.writerow(headers);w.writerows(rows);return b.getvalue().encode()

def calibrate_base4():
    A=t.SEGMENT_A;manifest=t.read_json(A/'summaries/delivery_file_manifest.json');code=t.read_json(A/'summaries/implementation_source_manifest.json')
    for item in manifest['files']+code['files']:
        p=A/item['path'];assert p.stat().st_size==item['bytes'] and t.sha(p.read_bytes())==item['sha256']
    accepted=sum(x['bytes'] for x in manifest['files'])+sum(x['bytes'] for x in code['files'])+(A/'summaries/delivery_file_manifest.json').stat().st_size
    assert accepted==956288
    preservation={'at_utc':t.utc(),'phase_A_closed_sha256':t.sha((A/'CLOSED.json').read_bytes()),'phase_A_terminal_sha256':t.sha((A/'TERMINAL_COMPLETE.json').read_bytes()),'phase_A_verification_sha256':t.sha((A/'FINAL_DELIVERY_VERIFICATION.json').read_bytes()),'phase_A_delivery_manifest_sha256':t.sha((A/'summaries/delivery_file_manifest.json').read_bytes()),'phase_A_implementation_manifest_sha256':t.sha((A/'summaries/implementation_source_manifest.json').read_bytes()),'referenced_implementation_files':code['files'],'metadata_bindings':{n:t.sha((A/n).read_bytes()) for n in ('STATE.json','NATIVE_CURSORS.json','SMALL_NATIVE_LOAD_STATE.json','source_registry.json','SOURCE_ACCESS_CONSTRAINTS.json')},'accepted_delivery_bytes':accepted,'raw_state_body_trees_duplicated':False,'accepted_phase_A_files_rewritten':False}
    t.atomic(t.WORK/'PHASE_A_PRESERVATION_RECEIPT.json',preservation)
    FIX.mkdir(exist_ok=True)
    for name,number in [('empty',0),('small',2)]:
        out=FIX/name;rows=[[f'fixture:{i}','fixture',f'2002-04-{i+1:02}T00:00:00Z','synthetic mapping; no body or corpus Load'] for i in range(number)]
        atomic_bytes(out/'identities.csv.gz',gzip.compress(csv_bytes(['entity_id','source_id','created_at','provenance'],rows),mtime=0))
        atomic_bytes(out/'report.md',(f'# Synthetic {name} append output\n\n'+('Complete fake-unit provenance and date fixture only.\n'*number)).encode())
        report={'fixture':name,'count':number,'publication_output_included':True,'source_requests':0,'corpus_database_access':False}
        atomic_bytes(out/'manifest.json',(json.dumps(report,indent=2)+'\n').encode())
        # A second atomic version proves old final/new temp coexistence.
        atomic_bytes(out/'manifest.json',(json.dumps(report|{'updated':True},indent=2)+'\n').encode())
    upper=512*1024
    atomic_bytes(FIX/'largest_fixed_artifact.bin',b'A'*upper)
    atomic_bytes(FIX/'largest_fixed_artifact.bin',b'B'*upper)
    # Conservative fixed month/neighbor serialization ceiling, independent of
    # observed volume. No source/count or calendar value controls acquisition.
    months=[f'{y:04}-{m:02}' for y in range(1988,2027) for m in range(1,13) if f'{y:04}-{m:02}'<='2026-09'];sources=('straight_dope','thesession','foodtalkcentral');n=15000000000
    delta=csv_bytes(['source_id','month','baseline_usable_bodies','new_usable_bodies','current_usable_bodies','reporting_only'],[[sid,m,n,n,n,1] for sid in sources for m in months])
    neighbors=csv_bytes(['source_id','month','baseline_count','delta_count','current_count','previous_three_counts','following_three_counts','incomplete_boundary_context','greater_than_all_available_neighbors_candidate','event_attribution'],[[sid,m,n,n,n,json.dumps([n]*3),json.dumps([n]*3),1,1,'none; independent dated evidence required'] for sid in sources for m in months])
    month_upper=len(delta)+len(neighbors)+16384
    assert month_upper<=640*1024,(month_upper,len(delta),len(neighbors))
    allocations={'new_local_implementation_code_schema_tests':288*1024,'future_publication_implementation_code_schema_tests':288*1024,'new_local_fixed_month_neighbor_era_tables':640*1024,'future_publication_fixed_month_neighbor_era_tables':640*1024,'new_local_fixed_controls_reports_readme_manifests':256*1024,'future_publication_fixed_reports_readme_manifests':128*1024,'preserved_empty_small_and_peak_calibration_fixtures':640*1024,'compact_phase_A_preservation_receipts':64*1024,'future_combined_PNG_final':512*1024,'largest_atomic_temporary_coexistence':512*1024}
    fixed=4*1048576;sum_allocated=sum(allocations.values());safety=fixed-sum_allocated
    assert safety>=128*1024 and t.bytes_under(FIX)<=allocations['preserved_empty_small_and_peak_calibration_fixtures']
    a_future=2*1048576;max_a=max(x['bytes'] for x in manifest['files']+code['files']);a_extras={'largest_atomic_copy_temporary':max_a,'phase_A_publication_readme_log_final_and_temp':128*1024,'phase_A_publication_manifest_final_and_temp':32*1024};assert accepted+sum(a_extras.values())<a_future
    proof={'at_utc':t.utc(),'passed':True,'fixed_output_upper_bytes':fixed,'allocations':allocations,'explicit_safety_margin_bytes':safety,'phase_A_future_publication_locked_upper_bytes':a_future,'phase_A_accepted_copy_bytes':accepted,'phase_A_extra_allocations':a_extras,'phase_A_future_copy_safety_bytes':a_future-accepted-sum(a_extras.values()),'all_combined_PNG_cost_assigned_to_append_fixed_allowance':True,'fixed_month_neighbor_serialization_upper_bytes':month_upper,'fixed_table_derivation':'three currently permitted source families across all465 fixed calendar months;11-digit physical15GB formatting upper; reporting only, never a source/count stopping rule','fixture_final_bytes':t.bytes_under(FIX),'fixture_complete_write_peak_bytes':max(x['coexistence_peak_bytes'] for x in measurements),'atomic_measurements':measurements,'publication_atomic_writes_sequential_and_file_upper_bytes':upper,'dynamic_local_and_future_publication_bytes_per_version_each':901,'dynamic_local_and_future_publication_bytes_per_entity_each':75,'unannotated_new_version_bytes':2582,'additional_new_request_bytes':1024,'dynamic_rows_raw_SQLite_growth_and_body_reservations_are_additional':True,'native_fixed_margin_bytes':32*1048576,'terminal_journal_margin_bytes':64*1048576,'network_requests':0,'canonical_database_access':False,'no_outside_publication_created':True,'source_and_physical_safeguards_unchanged':True}
    t.atomic(t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION.json',proof)
    assert (t.WORK/'PHASE_A_PRESERVATION_RECEIPT.json').stat().st_size+(t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION.json').stat().st_size<=allocations['compact_phase_A_preservation_receipts']
    print(json.dumps({k:proof[k] for k in ('passed','fixed_output_upper_bytes','fixture_final_bytes','fixture_complete_write_peak_bytes','explicit_safety_margin_bytes','fixed_month_neighbor_serialization_upper_bytes')}))

def main():
    # The base fixture is evidence for the append's own output only. Preserve it
    # and apply the coordinator's mandatory full joint-report supplement.
    preserved=t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION_BASE4_PRESERVED.json'
    if not preserved.exists():
        calibrate_base4()
        t.atomic(preserved,t.read_json(t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION.json'))
    proof=t.read_json(preserved)
    assert proof['passed'] and proof['fixed_output_upper_bytes']==4*1048576
    allocations=proof['allocations'].copy()
    allocations['new_local_fixed_month_neighbor_era_tables']=512*1024
    allocations['future_publication_fixed_month_neighbor_era_tables']=512*1024
    allocations['new_local_fixed_controls_reports_readme_manifests']=512*1024
    assert sum(allocations.values())+proof['explicit_safety_margin_bytes']==4*1048576
    assert proof['fixed_month_neighbor_serialization_upper_bytes']<=512*1024
    proof.update(at_utc=t.utc(),fixed_output_upper_bytes=8*1048576,allocations=allocations,
        base_append_local_and_future_output_upper_bytes=4*1048576,
        coordinator_joint_report_extra_upper_bytes=4*1048576,
        base4_proof_scope='append own outputs and fixture peak; excludes complete joint seven-PNG report',
        joint_PNG_budget_assignment='full coordinator PNG/report/metadata/manifest plus maximum atomic coexistence in additional4MiB; no worker joint copy',
        coordinator_observed_prior_seven_PNG_bytes=2809129,
        coordinator_observed_prior_large_PNG_bytes=[592612,607744],
        joint_report_single_artifact_upper_bytes=1048576,
        joint_report_all_final_plus_max_atomic_temp_upper_bytes=4*1048576,
        joint_report_remaining_if_same_PNGs_and_max_temp_bytes=4*1048576-2809129-1048576,
        joint_report_publication_requires_actual_prepublication_size_check=True,
        worker_joint_PNG_or_external_publication_created=False,
        base4_proof_preserved_sha256=t.sha(preserved.read_bytes()),
        four_MiB_as_total_formal_output_allowance_rejected=True,
        correction_authority='coordinator same-deadline H+1 mandatory supplement',
        allocation_refinement='256KiB from month-table padding to local fixed control/report overhead; totals unchanged')
    assert proof['phase_A_future_publication_locked_upper_bytes']==2*1048576
    t.atomic(t.WORK/'FIXED_OUTPUT_PEAK_CALIBRATION.json',proof)
    print(json.dumps({'passed':True,'B_fixed_output_upper_bytes':8*1048576,'A_future_publication_upper_bytes':2*1048576,'base4_fixture_reused':True,'network_or_database_access':False}))

if __name__=='__main__':main()
