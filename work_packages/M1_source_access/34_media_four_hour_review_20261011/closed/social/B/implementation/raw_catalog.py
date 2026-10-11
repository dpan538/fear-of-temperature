"""Terminal catalog/mapping check of new raw responses; accepted raw is reused."""
import csv,gzip,json,re
import transport as t,entities as e
import lemmy_adapter

def catalog(c,out):
 loaded={json.loads(line)['request_id'] for line in (t.WORK/'LOADS.jsonl').read_text().splitlines()}
 sources={s['source_id']:s for s in t.read_json(t.WORK/'source_registry.json')}
 # One metadata-only scan of changed observations avoids per-object table scans.
 mappings={};notice_corrections={}
 for req,sid,ns,nid,bodysha,date,flags,vid in c.execute("SELECT o.request_id,n.source_id,n.native_namespace,n.native_id,v.body_sha256,n.native_created_at,v.flags_json,v.entity_version_id FROM entity_observations o JOIN entity_versions v ON v.entity_version_id=o.entity_version_id JOIN native_entities n ON n.entity_id=v.entity_id WHERE o.rowid>?",(t.read_json(t.WORK/'APPEND_ROWID_BOUNDARIES.json')['bounds']['entity_observations'],)):
  mappings.setdefault((req,sid,ns,nid),[]).append((bodysha,date,flags,vid))
 stats={'transport_receipts':0,'saved_raw_responses':0,'mapped_native_return_observations':0,'mapping_issues':0,'parse_pending_content_responses':0}
 p=out/'raw_object_catalog.csv';issues=out/'native_mapping_issues.csv'
 with p.open('w',newline='',encoding='utf8') as f,issues.open('w',newline='',encoding='utf8') as g:
  w=csv.writer(f);w.writerow(['request_id','source_id','purpose','source_url','retrieved_at','http_status','transport_state','raw_reference','raw_sha256','stored_sha256','raw_bytes','stored_bytes','content_encoding','mapping_state','mapped_native_return_observations','unresolved_native_return_observations','HTTP_content_type','HTTP_content_length','HTTP_last_modified_literal','HTTP_last_modified_time_basis'])
  q=csv.writer(g);q.writerow(['request_id','source_id','native_namespace','native_id','issue'])
  for receipt in sorted((t.WORK/'receipts').glob('*.json')):
   r=t.read_json(receipt);stats['transport_receipts']+=1;state='transport_stop_no_raw_payload';matched=missing=0
   if r['status']=='saved':
    packed=(t.REPO/r['raw_reference']).read_bytes();assert t.sha(packed)==r['stored_sha256']
    raw=gzip.decompress(packed);assert t.sha(raw)==r['raw_sha256'];stats['saved_raw_responses']+=1
    state='source_provided_attachment_payload; authored_body_mapping_pending; not_separate_native_message' if r.get('purpose')=='archive_attachment_content_evidence' else 'noncontent_access_policy_or_frame_metadata'
    if r.get('purpose')=='content' or (r['source_id'] in ('ilxor','thesession') and r['request_id'] in loaded):
     sid=r['source_id'];source=sources[sid];body=gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
     try:
      import archive_adapter
      data=json.loads(body) if sid not in ('python_list_archive','w3_wwwtalk','tildes','ilxor','thesession') and source.get('adapter')!='public_html_adapter.mail_message' else {}
      if source.get('adapter')=='public_html_adapter.mail_message':
       import public_html_adapter
       rows,_=public_html_adapter.mail_message(body,r['url'],sid) if re.search(r'/msg[0-9]+\.html$',r['url']) else public_html_adapter.mail_index(body,r['url'])
      elif sid=='thesession':
       import thesession_adapter
       rows=[] if '/discussions/new' in r['url'] else thesession_adapter.records(body,r['url'])[0]
      elif sid=='ilxor':
       import public_html_adapter
       rows,_=public_html_adapter.ilxor_thread(body,r['url'])
      elif sid=='tildes':
       import public_html_adapter
       rows,_=(public_html_adapter.tildes_topic if '/~' in __import__('urllib.parse',fromlist=['urlsplit']).urlsplit(r['url']).path else public_html_adapter.tildes_index)(body,r['url'])
      elif sid=='python_list_archive':rows=archive_adapter.mbox_records(body,sid,r['url'])
      elif sid=='w3_wwwtalk':rows=archive_adapter.w3_records(body,r['url'],sid) if re.search(r'/[0-9]{4}\.html$',r['url']) else []
      elif sid=='hackernews':rows=archive_adapter.hn_records(data,sid,r['url'].rsplit('/',1)[-1].split('.')[0])
      elif sid.startswith('se_'):rows=e.se(data,sid)
      elif sid.startswith('mastodon_'):rows=e.mastodon(data,sid)
      elif sid=='bluesky':rows=e.bluesky(data)
      elif sid in ('lemmy_nz','aussie_zone','feddit_org','midwest_social'):rows=lemmy_adapter.records(data,sid,source['base_url'])
      else:rows=e.discourse(data,sid,source['base_url'],source.get('content_license','version_specific_license_unresolved'))
     except Exception as exc:
      rows=None;state='saved_content_parse_pending';stats['parse_pending_content_responses']+=1
      q.writerow([r['request_id'],sid,'','','current_adapter_parse_pending:'+type(exc).__name__]);stats['mapping_issues']+=1
     if rows is not None:
      if r.get('reused_saved_whole_response'):
       assert r.get('only_append_suffix_native_mapping_checked')
       rows=rows[r['accepted_phase_A_committed_prefix_records']:]
      state='loaded_native_returns' if r['request_id'] in loaded else 'saved_content_not_loaded_native_evidence'
      for row in rows:
       record=e.prepare(row)
       found=mappings.get((r['request_id'],sid,row['native_namespace'],str(row['native_post_id'])),[])
       candidates=[x for x in found if x[0]==record['body_sha256']]
       valid=any(x[1]==row.get('native_created_at') or json.loads(x[2]).get('observed_identity_date_or_unit_conflict',{}).get('observed',[None])[0]==row.get('native_created_at') for x in candidates)
       if valid:
        matched+=1
        if row.get('flags',{}).get('source_archive_generated_notice_only'):
         for candidate in candidates:notice_corrections[candidate[3]]={'request_id':r['request_id'],'source_id':sid,'native_namespace':row['native_namespace'],'native_id':str(row['native_post_id']),'source_url':r['url'],'raw_sha256':r['raw_sha256'],'native_attachment_url':row['native_fields'].get('source_scrubbed_attachment_url'),'notice_body_preserved':True,'authored_body_recovery':'pending'}
       else:
        missing+=1;q.writerow([r['request_id'],sid,row['native_namespace'],row['native_post_id'],'saved_native_identity_date_body_mapping_pending' if found else 'saved_native_return_not_in_entity_observations'])
      if missing:state='loaded_with_explicit_mapping_pending' if r['request_id'] in loaded else 'saved_content_native_mapping_pending'
      stats['mapped_native_return_observations']+=matched;stats['mapping_issues']+=missing
   w.writerow([r.get('request_id'),r.get('source_id'),r.get('purpose'),r.get('url'),r.get('retrieved_at'),r.get('http_status'),r.get('status'),r.get('raw_reference'),r.get('raw_sha256'),r.get('stored_sha256'),r.get('raw_bytes'),r.get('stored_bytes'),(r.get('headers') or {}).get('Content-Encoding'),state,matched,missing,(r.get('headers') or {}).get('Content-Type'),(r.get('headers') or {}).get('Content-Length'),(r.get('headers') or {}).get('Last-Modified'),'server_representation_metadata; not native message publication or verified edit time'])
 # These are explicit derived source-quality corrections on newly fetched raw,
 # never edits/deletions of native IDs, bodies, versions or historical baseline.
 with c:
  for vid,evidence in notice_corrections.items():
   ann=c.execute('SELECT temporal_limitations_json FROM entity_quality_annotations WHERE entity_version_id=?',(vid,)).fetchone()
   if not ann:raise AssertionError('new notice version lacks terminal quality annotation')
   limits=json.loads(ann[0]);limits.update({'source_archive_generated_notice_only':True,'authored_attachment_body_not_established':True,'evidence':evidence})
   c.execute("UPDATE entity_quality_annotations SET independently_authored_body=0,directness='archive_generated_attachment_notice; original_authored_body_unrecovered',temporal_limitations_json=? WHERE entity_version_id=?",(json.dumps(limits,ensure_ascii=False),vid))
   eid=c.execute('SELECT entity_id FROM entity_versions WHERE entity_version_id=?',(vid,)).fetchone()[0]
   cid=t.sha(('archive_notice_only|'+vid).encode())
   c.execute('INSERT OR IGNORE INTO structural_corrections VALUES (?,?,?,?,?,?,?)',(cid,eid,'independently_authored_body','historical adapter treated source-generated notice as authored text','0; raw/body/version retained; attachment recovery pending',json.dumps(evidence,ensure_ascii=False),t.utc()))
 stats['archive_notice_only_version_corrections']=len(notice_corrections)
 t.atomic(t.WORK/'ARCHIVE_NOTICE_QUALITY_CORRECTIONS.json',{'at_utc':t.utc(),'versions':notice_corrections,'scope':'once terminal changed-raw mapping; original raw/body/version/identity/counters retained; derived authored-body annotation corrected'})
 return stats,[{'path':str(x.relative_to(t.WORK)),'bytes':x.stat().st_size,'sha256':t.sha(x.read_bytes())} for x in (p,issues)]
