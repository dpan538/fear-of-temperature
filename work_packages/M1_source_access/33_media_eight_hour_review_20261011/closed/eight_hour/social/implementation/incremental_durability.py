"""Small append-only provenance transactions inside the existing owner mutex."""
import time
import transport as t,finalize_metadata

def flush_if_due(force=False):
    previous=t.read_json(t.WORK/'LAST_INCREMENTAL_METADATA_FLUSH.json',{})
    if not force and time.time()-previous.get('completed_epoch',0)<120:return
    model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json')
    outstanding=t.state().get('new_entity_versions',0)-model.get('already_annotated_changed_versions',0)
    if not outstanding:return
    revision=previous.get('revision',0)+1;phase='incremental_'+str(revision)
    batch_records=1 if previous.get('partial') and str(previous.get('pending_reason','')).startswith('resource_stop') else 50
    selection_limit=min(50 if batch_records==1 else 1000,outstanding)
    partial=False;pending_reason=None
    try:
        counts=finalize_metadata.finalize(limit=selection_limit,phase=phase,batch_records=batch_records)
    except t.Stop as exc:
        if not str(exc).startswith('resource_stop'):raise
        partial=True;pending_reason=str(exc)
        counts=t.read_json(t.WORK/('METADATA_'+phase.upper()+'_PROGRESS.json'),{}).get('counts',{'quality_annotations':0})
        t.atomic(t.WORK/'INCREMENTAL_METADATA_PENDING.json',{'at_utc':t.utc(),'reason':pending_reason,'completed_epoch':time.time(),'committed_annotations_preserved':counts['quality_annotations'],'native_rows_and_cursors_preserved':True})
    actual=counts['quality_annotations']
    model['already_annotated_changed_versions']=model.get('already_annotated_changed_versions',0)+actual
    t.atomic(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json',model)
    proof_path=t.WORK/('METADATA_'+phase.upper()+('_PROGRESS.json' if partial else '_RECEIPT.json'))
    proof=t.read_json(proof_path,{})
    receipt={'at_utc':t.utc(),'completed_epoch':time.time(),'revision':revision,'actual_annotated_new_versions':actual,'partial':partial,'pending_reason':pending_reason,'source_requests':0,'resume_possible':True,'bounded_changed_version_selection':True,'counts':counts,'metadata_receipt_sha256':t.sha(proof_path.read_bytes()) if proof_path.exists() else None,'observed_complete_peak_bytes':proof.get('max_observed_additional_disk_peak_upper_bytes',proof.get('observed_additional_disk_peak_upper_bytes',0)),'reserved_complete_peak_bytes':proof.get('max_reserved_operation_bytes',proof.get('reserved_operation_bytes',0)),'provider_stops_and_deadline_preserved':True}
    t.atomic(t.WORK/('DURABILITY_FLUSH_'+str(revision)+'_RECEIPT.json'),receipt)
    t.atomic(t.WORK/'LAST_INCREMENTAL_METADATA_FLUSH.json',receipt)
    return receipt
