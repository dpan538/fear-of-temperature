"""Native metadata annotations and publication identities; no semantic labels."""
import json,urllib.parse
import transport as t,entities as e

def finalize():
 with t.shared(t.footprint(0,24*1048576)):
  c=e.db();registry={s['source_id']:s for s in t.read_json(t.WORK/'source_registry.json')};at=t.utc();counts={'memberships':0,'quality_annotations':0}
  with c:
   c.execute('CREATE TABLE IF NOT EXISTS publication_memberships(entity_id TEXT NOT NULL REFERENCES native_entities,publication_key TEXT NOT NULL,key_basis TEXT NOT NULL,evidence_json TEXT NOT NULL,PRIMARY KEY(entity_id,publication_key))')
   c.execute('CREATE TABLE IF NOT EXISTS entity_quality_annotations(entity_version_id TEXT PRIMARY KEY REFERENCES entity_versions,independently_authored_body INTEGER NOT NULL,directness TEXT NOT NULL,native_mapping_basis TEXT NOT NULL,original_external_body_checked INTEGER NOT NULL,temporal_limitations_json TEXT NOT NULL,annotated_at TEXT NOT NULL)')
   for sid,source in registry.items():
    c.execute('UPDATE acquisition_sources SET source_region=? WHERE source_id=?',(source.get('stratum','GLOBAL'),sid))
   for vid,eid,sid,ns,nid,native_date,edited,independent,fields,flags,unit in c.execute('SELECT v.entity_version_id,n.entity_id,n.source_id,n.native_namespace,n.native_id,n.native_created_at,v.native_edited_at,v.independently_authored_body,v.native_fields_json,v.flags_json,n.native_unit FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id'):
    meta=json.loads(fields);facts=json.loads(flags);uri=None;directness='original_utterance_record_via_documented_source_API'
    if ns=='at_uri':uri=nid
    elif ns=='status':
     uri=meta.get('uri')
     if uri and urllib.parse.urlsplit(uri).hostname!=urllib.parse.urlsplit(registry.get(sid,{}).get('base_url','')).hostname:directness='federated_reproduction_of_original_status'
    elif 'lemmy.post' in meta:
     obj=meta.get('lemmy.comment') if ns=='comment' else meta.get('lemmy.post');obj=obj or {};uri=obj.get('ap_id')
     if obj.get('local') is False:directness='federated_reproduction_of_original_native_object'
    elif ns=='repost_event':directness='native_repost_view_wrapper; not_independent_authored_body'
    if unit=='context_container':directness='source_native_context_container'
    if uri:key='native_original_uri:'+uri;basis='source-returned canonical native URI; original external body not separately fetched'
    else:key='source_native_identity:'+sid+'|'+ns+'|'+nid;basis='typed source-native identity; cross-provider equivalence unresolved when URI absent'
    counts['memberships']+=c.execute('INSERT OR IGNORE INTO publication_memberships VALUES (?,?,?,?)',(eid,key,basis,json.dumps({'entity_version_id':vid,'native_uri':uri},ensure_ascii=False))).rowcount
    # Source-defined small actions/moderation/whisper events are not asserted authored text.
    if ns=='forum_post' and meta.get('post_type',1)!=1:independent=0;directness='source_native_nonregular_event; authored_body_not_established'
    limitations={'later_retrieval_does_not_certify_historical_body':True,'native_creation_before_documented_beta':facts.get('source_creation_before_documented_site_beta',False),'native_edit_after_cutoff':bool(edited and edited[:10]>'2026-09-21'),'indexedAt_not_publication_time':facts.get('indexedAt_is_not_publication_time'),'native_role_and_country_not_inferred':True}
    if ns=='repost_event' and not meta.get('uri'):limitations['identifier_basis']='derived_native_event_fingerprint; native_repost_record_URI_not_returned'
    counts['quality_annotations']+=c.execute('INSERT OR IGNORE INTO entity_quality_annotations VALUES (?,?,?,?,?,?,?)',(vid,independent,directness,'saved API native identity/date/content mapping; not truth verification',0,json.dumps(limitations,ensure_ascii=False),at)).rowcount
  c.close();t.atomic(t.WORK/'METADATA_FINALIZATION_RECEIPT.json',{'at_utc':at,'native_fields_only':True,'body_reaudit':False,'semantic_labels':False,'counts':counts});return counts
if __name__=='__main__':
 with t.writer():print(finalize())
