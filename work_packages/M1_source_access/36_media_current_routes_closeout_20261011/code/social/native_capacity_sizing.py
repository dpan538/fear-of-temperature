"""Smaller whole-native-unit transactions after a genuine reservation failure."""
import json
import transport as t

def load_smaller(records,rec,frame_id,loader):
    digest=t.sha(json.dumps(sorted(r['source_id']+'|'+r['native_namespace']+'|'+str(r['native_post_id']) for r in records)).encode())
    path=t.WORK/'SMALL_NATIVE_LOAD_STATE.json'
    ledger=t.read_json(path,{})
    entry={'at_utc':t.utc(),'request_id':rec['request_id'],'frame_id':frame_id,'native_key_digest':digest,'total_records':len(records),'committed_prefix_records':0,'complete':False,'whole_native_bodies_preserved':True,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes())}
    ledger[rec['request_id']]=entry;t.atomic(path,ledger)
    offset=0;batch_size=10;results=[]
    try:
        while offset<len(records):
            batch=records[offset:offset+batch_size]
            try:result=loader(batch,rec,frame_id)
            except t.Stop as exc:
                if not str(exc).startswith('resource_stop') or batch_size==1:raise
                batch_size=1;continue
            results.append(result);offset+=len(batch)
            entry.update(at_utc=t.utc(),committed_prefix_records=offset,last_batch_records=len(batch))
            t.atomic(path,ledger)
        entry.update(complete=True,at_utc=t.utc());t.atomic(path,ledger)
    except Exception as exc:
        entry.update(at_utc=t.utc(),pending_reason=type(exc).__name__+': '+str(exc));t.atomic(path,ledger);raise
    result=dict(results[-1])
    for key in ('returned_entities','new_entities','new_entity_versions','new_qualified_posts'):
        result[key]=sum(r[key] for r in results)
    result.update(smaller_complete_native_transactions=True,transaction_count=len(results),native_key_digest=digest)
    return result
