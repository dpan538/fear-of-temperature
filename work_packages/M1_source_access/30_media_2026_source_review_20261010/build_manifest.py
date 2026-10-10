"""Inventory this bounded review only; no shared-store scan or control change."""
import hashlib
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent

def info(path):
    return {'path':str(path.relative_to(OUT)),'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    target=OUT/'INPUT_OUTPUT_MANIFEST.json'
    assert not target.exists()
    pins=json.loads((OUT/'worker/INPUT_PIN_MANIFEST.json').read_text())
    newspaper=json.loads((OUT/'worker/NAMED_NEWSPAPER_RECORD_CHECKS.json').read_text())
    parents=json.loads((OUT/'worker/NAMED_PRIMARY_PARENT_EVIDENCE.json').read_text())
    scopes=json.loads((OUT/'worker/SCOPE_READ_HASHES.json').read_text())
    deliverables=[info(p) for p in sorted(OUT.iterdir()) if p.is_file()]
    evidence=[info(p) for p in sorted((OUT/'worker').rglob('*')) if p.is_file()]
    controls=[info(p) for p in sorted((OUT/'control').iterdir()) if p.is_file()]
    miscellaneous=[info(p) for p in sorted(OUT.rglob('*')) if p.is_file() and len(p.relative_to(OUT).parts)>1
                   and p.relative_to(OUT).parts[0] not in ['worker','control']]
    expected={'REVIEW_REPORT.md','2026_SOURCE_MONTH_MARKS.csv','2026_RECORD_MARKS.csv',
              'PARENT_SOURCE_EVIDENCE.csv','REVIEW_LIMITS.json','VERIFICATION.json',
              'NATIVE_MECHANISM_REVIEW.csv','NATIVE_MECHANISM_LIMITS.json'}
    assert expected <= {r['path'] for r in deliverables}
    retained=sum(r['bytes'] for r in deliverables+evidence+controls+miscellaneous)
    assert retained<16*1024*1024
    assert shutil.disk_usage(OUT).free-1024*1024>16106127360+50331648
    result={'manifest_at_utc':datetime.now(timezone.utc).isoformat(),
            'publication_interval':['1988-01-01','2026-09-21'],
            'closed_inputs':pins['input_files'],'instruction_scope_read_hashes':scopes,
            'named_original_newspaper_raw_inputs':newspaper['raw_input_manifest'],
            'named_original_parent_raw_inputs':[{k:r[k] for k in ['source_id','raw_locator','saved_compressed_bytes','saved_file_sha256','payload_sha256','source_observed_at_utc']} for r in parents['rows']],
            'final_deliverables_and_review_code':deliverables,
            'local_worker_evidence_and_preserved_interim':evidence,'local_controls':controls,
            'other_local_runtime_files_not_for_publication':miscellaneous,
            'accounting':{'package30_bytes_excluding_this_manifest':retained,
                          'shared_allocation_charge_bytes':retained,
                          'manifest_self_bytes_excluded_from_hash_inventory':True,
                          'manifest_and_all_later_local_bytes_also_chargeable':True,
                          'shared_cap_bytes':30000000000,'counter_reset':False,
                          'scope':'package30 only; original raw/inputs were already retained elsewhere, not recopied as bodies',
                          'simultaneous_live_cumulative_media_usage_measured':False},
            'hash_manifest_self_exclusion':'This file cannot include its own stable digest; all other output/evidence/code/control files are inventoried.',
            'corpus_or_collector_mutations':0,'sealed_evaluator_access':False,
            'reproducibility':'review_metadata.py derives baseline marks from pinned inputs; parent_evidence.py records curated primary assertions; native_mechanism_review.py uses pinned native aggregates; finalize_review.py upgrades only named checked IDs. Scripts refuse overwrite. Keep worker metadata_mark_base and raw check evidence for the staged finalization chain. Pin/named-read scripts alone access named originals under nonblocking shared I/O lock; other review scripts have no corpus/network access.'}
    with target.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'manifest':str(target),'accounting':result['accounting'],
                      'final_output_files':len(deliverables),'local_evidence_files':len(evidence),
                      'package30_actual_bytes_including_manifest':retained+target.stat().st_size},indent=2))

if __name__=='__main__':main()
