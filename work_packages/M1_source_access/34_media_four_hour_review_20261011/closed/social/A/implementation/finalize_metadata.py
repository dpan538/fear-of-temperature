"""Native metadata annotations and publication identities; no semantic labels."""
import json,urllib.parse,source_era_provenance
import transport as t,entities as e

def metadata_footprint(metadata_bytes,record_count):
 # A tiny batch gets the existing native per-row random-page allowance and
 # fixed margin; larger metadata batches retain their 64 MiB journal reserve.
 return metadata_bytes*16+(record_count*65536+32*1048576 if record_count<=50 else 64*1048576)

def finalize(limit=None, phase="terminal", batch_records=200):
 """Bound changed metadata transactions; reserve their actual operation footprint."""
 assert 1<=batch_records<=1000
 begin=t.read_json(t.SCOPE_PATH)['earliest_network_and_load_start_at_utc']
 registry={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')};at=t.utc()
 prefix='METADATA_FINALIZATION' if phase=='terminal' else 'METADATA_CALIBRATION' if phase=='footprint_calibration' else 'METADATA_'+phase.upper()
 counts={'memberships':0,'quality_annotations':0,'new_topic_post_number_aliases':0,'resolved_post_number_edges':0}
 journal_peaks=[];reservations=[];complete_peaks=[];db_before_bytes=t.DB.stat().st_size
 with t.shared(t.footprint(),inflight_at=begin):
  c=e.db();floor=t.read_json(t.WORK/'APPEND_ROWID_BOUNDARIES.json')['bounds']['entity_versions']
  sql='SELECT v.entity_version_id FROM entity_versions v WHERE v.rowid>? AND NOT EXISTS (SELECT 1 FROM entity_quality_annotations a WHERE a.entity_version_id=v.entity_version_id) ORDER BY v.rowid'
  params=(floor,)
  if limit is not None:
   assert limit>=0
   sql+=' LIMIT ?';params+=(limit,)
  changed_ids=[x[0] for x in c.execute(sql,params)];c.close()
 t.atomic(t.WORK/(prefix+'_INPUT_RECEIPT.json'),{'at_utc':t.utc(),'changed_version_count':len(changed_ids),'changed_version_id_digest':t.sha(json.dumps(changed_ids).encode()),'body_reads':False,'reference':'one bounded append-rowid version-metadata selection in physical row order; prior saved-response retrieval times stay intact; loader inserts versions/observations atomically; ID list is transient memory only'})
 # Schema already exists from the accepted predecessor; never migrate or copy it.
 for offset in range(0,len(changed_ids),batch_records):
  batch=changed_ids[offset:offset+batch_records]
  with t.shared(t.footprint(),inflight_at=begin):
   c=e.db()
   rows=c.execute('SELECT v.entity_version_id,n.entity_id,n.source_id,n.native_namespace,n.native_id,n.native_created_at,v.native_edited_at,v.independently_authored_body,v.native_fields_json,v.flags_json,n.native_unit FROM native_entities n JOIN entity_versions v ON v.entity_id=n.entity_id WHERE v.entity_version_id IN ('+','.join('?' for _ in batch)+') ORDER BY v.rowid',batch).fetchall()
   c.close()
  if not rows:continue
  metadata_bytes=sum(len(str(v).encode()) for row in rows for v in row if v is not None)
  # Bounded affected metadata records per transaction; include metadata copies and
  # 64 MiB for B-tree/alias/edge pages. No whole-DB rewrite or journal estimate.
  pending=metadata_footprint(metadata_bytes,len(rows));reservations.append(pending)
  with t.shared(pending,inflight_at=begin):
   c=e.db();peak=0;batch_db_before=t.DB.stat().st_size
   with c:
    for vid,eid,sid,ns,nid,native_date,edited,independent,fields,flags,unit in rows:
     meta=json.loads(fields);facts=json.loads(flags);uri=None;directness='original_utterance_record_via_documented_source_API'
     if ns=='forum_post' and meta.get('topic_id') is not None and meta.get('post_number') is not None:
      alias=str(meta['topic_id'])+':'+str(meta['post_number'])
      counts['new_topic_post_number_aliases']+=c.execute('INSERT OR IGNORE INTO native_aliases VALUES (?,?,?,?,?)',(sid,'topic_post_number',alias,eid,json.dumps({'native_topic_id':meta['topic_id'],'native_post_number':meta['post_number'],'entity_version_id':vid}))).rowcount
      counts['resolved_post_number_edges']+=c.execute("UPDATE native_edges SET target_entity_id=?,resolution_state='resolved' WHERE target_entity_id IS NULL AND target_source_id=? AND target_namespace='topic_post_number' AND target_native_id=?",(eid,sid,alias)).rowcount
     if registry.get(sid,{}).get('platform')=='native_public_forum_html':directness='original_utterance_record_via_source_public_HTML'
     if facts.get('archival_reproduction_of_original_public_message'):directness='archival_reproduction_of_original_public_mailing_list_message'
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
     if ns=='forum_post' and meta.get('post_type',1)!=1:independent=0;directness='source_native_nonregular_event; authored_body_not_established'
     limitations={'later_retrieval_does_not_certify_historical_body':True,'native_creation_before_documented_beta':facts.get('source_creation_before_documented_site_beta',False),'native_edit_after_cutoff':bool(edited and edited[:10]>'2026-09-21'),'indexedAt_not_publication_time':facts.get('indexedAt_is_not_publication_time'),'native_role_and_country_not_inferred':True}
     limitations.update(source_era_provenance.limitations(registry.get(sid,{}),native_date,meta))
     if facts.get('archival_reproduction_of_original_public_message'):limitations['native_archive_sent_reception_and_snapshot_dates_separate']=True
     if facts.get('archive_date_not_independently_verified_against_original_email_headers'):limitations['archive_display_date_and_original_email_headers_not_independently_reconciled']=True
     if sid=='thesession':limitations.update({'member_profiles_not_requested':True,'bundled_inline_member_bios_retained_only_in_raw':True,'no_author_country_derived_from_inline_bio':True,'historical_no_inline_bio_acquired_flag_means_not_extracted_to_native_metadata':True})
     if facts.get('native_timezone_unknown'):limitations['source_displayed_time_zone_unresolved']=True
     if facts.get('preview_only') or meta.get('preview_only'):limitations['index_preview_is_not_complete_native_text']=True
     if ns=='repost_event' and not meta.get('uri'):limitations['identifier_basis']='derived_native_event_fingerprint; native_repost_record_URI_not_returned'
     counts['quality_annotations']+=c.execute('INSERT OR IGNORE INTO entity_quality_annotations VALUES (?,?,?,?,?,?,?)',(vid,independent,directness,'saved native identity/date/content mapping; not truth verification',0,json.dumps(limitations,ensure_ascii=False),at)).rowcount
     from pathlib import Path
     journal=Path(str(t.DB)+'-journal');peak=max(peak,journal.stat().st_size if journal.exists() else 0)
   c.close();journal_peaks.append(peak)
   batch_db_growth=max(0,t.DB.stat().st_size-batch_db_before)
   complete_peak=peak+batch_db_growth;complete_peaks.append(complete_peak)
  last=rows[-1][0]
  t.atomic(t.WORK/(prefix+'_PROGRESS.json'),{'at_utc':t.utc(),'last_version_id':last,'counts':counts,'observed_journal_peak_bytes':peak,'observed_db_growth_bytes':batch_db_growth,'observed_additional_disk_peak_upper_bytes':complete_peak,'reserved_operation_bytes':pending})
  if complete_peak>pending:raise t.Stop('metadata_complete_peak_exceeded_reservation; committed batch evidence preserved')
 t.atomic(t.WORK/(prefix+'_RECEIPT.json'),{'at_utc':at,'phase':phase,'finalization_complete':limit is None,'native_fields_only':True,'body_reaudit':False,'semantic_labels':False,'counts':counts,'db_before_bytes':db_before_bytes,'db_after_bytes':t.DB.stat().st_size,'changed_versions_selected':len(changed_ids),'bounded_transaction_records':batch_records,'max_reserved_operation_bytes':max(reservations,default=0),'min_reserved_operation_bytes':min(reservations,default=0),'max_observed_journal_peak_bytes':max(journal_peaks,default=0),'max_observed_additional_disk_peak_upper_bytes':max(complete_peaks,default=0),'complete_peak_reservation_violations':0,'journal_reserve_basis':'changed native metadata amplification plus 64 MiB index/alias/edge-page allowance; bounded transactions, no whole DB rewrite'})
 return counts
if __name__=='__main__':
 with t.writer():print(finalize())
