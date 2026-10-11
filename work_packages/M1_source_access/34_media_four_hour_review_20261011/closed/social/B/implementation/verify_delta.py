"""Verify finalized changed delivery and writer handover without corpus reaudit."""
import csv,gzip,json
import transport as t,entities as e,delta_closeout

def main():
    terminal=t.read_json(t.WORK/'TERMINAL_COMPLETE.json');assert terminal
    closed=t.read_json(t.WORK/'CLOSED.json');manifest=t.read_json(t.WORK/'summaries/delivery_file_manifest.json');bounds=t.read_json(t.WORK/'APPEND_ROWID_BOUNDARIES.json')['bounds'];scope=t.read_json(t.SCOPE_PATH)
    assert terminal['closed_sha256']==t.sha((t.WORK/'CLOSED.json').read_bytes())
    preserved=t.read_json(t.WORK/'PHASE_A_PRESERVATION_RECEIPT.json')
    for name,field in [('CLOSED.json','phase_A_closed_sha256'),('TERMINAL_COMPLETE.json','phase_A_terminal_sha256'),('FINAL_DELIVERY_VERIFICATION.json','phase_A_verification_sha256'),('summaries/delivery_file_manifest.json','phase_A_delivery_manifest_sha256'),('summaries/implementation_source_manifest.json','phase_A_implementation_manifest_sha256')]:
        assert t.sha((t.SEGMENT_A/name).read_bytes())==preserved[field]
    for item in preserved['referenced_implementation_files']:
        assert t.sha((t.SEGMENT_A/item['path']).read_bytes())==item['sha256']
    for name,digest in preserved['metadata_bindings'].items():
        assert t.sha((t.SEGMENT_A/name).read_bytes())==digest
    assert terminal['delivery_manifest_sha256']==t.sha((t.WORK/'summaries/delivery_file_manifest.json').read_bytes())
    assert json.loads((t.WORK/'summaries/collection_manifest.json').read_text())==closed
    total=0;rows={}
    for item in manifest['files']:
        p=t.WORK/item['path'];assert p.stat().st_size==item['bytes'];assert t.sha(p.read_bytes())==item['sha256'];total+=item['bytes']
        if p.name.endswith('.csv.gz'):
            with gzip.open(p,'rt',encoding='utf8',newline='') as f:
                reader=csv.reader(f);header=next(reader);assert header;rows[p.name]=sum(1 for _ in reader)
    implementation=t.read_json(t.WORK/'summaries/implementation_source_manifest.json')
    for item in implementation['files']:
        p=t.WORK/item['path'];assert p.stat().st_size==item['bytes'];assert t.sha(p.read_bytes())==item['sha256']
    assert rows['new_native_entities.csv.gz']==closed['new_entities'] and rows['changed_entity_versions.csv.gz']==closed['new_entity_versions']
    assert rows['changed_source_provenance.csv.gz']==closed['new_entity_versions']
    assert closed['checks']['native_load_complete_peak_exceedances']==0
    requests=[json.loads(x) for x in (t.WORK/'REQUESTS.jsonl').read_text().splitlines()]
    assert len(requests)==closed['round_charged_requests']
    assert all(scope['earliest_network_and_load_start_at_utc']<=x['started_at']<scope['hard_deadline_at_utc'] for x in requests)
    assert all(x['status']!='in_progress' for x in requests)
    assert not (t.DB.parent/(t.DB.name+'-journal')).exists()
    delta_closeout.terminal_reservations()
    with t.writer():
        with t.shared(t.footprint(),inflight_at=scope['earliest_network_and_load_start_at_utc']) as budget:
            assert budget['terminal_reserve_components']['accepted_phase_A_future_publication_upper_bytes']==2*1048576
            assert budget['terminal_reserve_components']['B_fixed_output_upper_bytes']==8*1048576
            c=e.db()
            assert c.execute('SELECT COUNT(*) FROM posts WHERE rowid>?',(bounds['posts'],)).fetchone()[0]==closed['new_core_texts']
            assert c.execute("SELECT COUNT(*) FROM posts WHERE rowid>? AND (substr(native_created_at,1,10)<'1988-01-01' OR substr(native_created_at,1,10)>'2026-09-21')",(bounds['posts'],)).fetchone()[0]==0
            c.close()
    result={'at_utc':t.utc(),'passed':True,'delivery_files_checked':len(manifest['files']),'delivery_bytes':total,'implementation_files_checked':len(implementation['files']),'changed_csv_rows':rows,'network_requests_within_fixed_window':len(requests),'source_and_terminal_exec_exits_checked_by_owner':True,'social_writer_mutex_available':True,'database_journal_absent':True,'actual_final_capacity_with_future_publication_reserve':budget,'old_body_raw_or_full_integrity_reaudit':False,'phase_A_terminal_manifests_implementation_and_compact_state_preserved':True,'future_publication_bytes_reserved':True,'accepted_A_future2MiB_reserved_in_actual_terminal_verify_path':True,'B_fixed8MiB_reserved_in_actual_terminal_verify_path':True,'full_cumulative_reexports':False,'delivery_manifest_sha256':t.sha((t.WORK/'summaries/delivery_file_manifest.json').read_bytes())}
    t.atomic(t.WORK/'FINAL_DELIVERY_VERIFICATION.json',result);print(json.dumps({k:result[k] for k in ('at_utc','passed','delivery_files_checked','delivery_bytes','social_writer_mutex_available')}))

if __name__=='__main__':main()
