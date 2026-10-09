"""Terminal catalog/mapping check of new raw responses; accepted raw is reused."""
import csv,gzip,json
import transport as t,entities as e
import lemmy_adapter

def catalog(c,out):
 loaded={json.loads(line)['request_id'] for line in (t.WORK/'LOADS.jsonl').read_text().splitlines()}
 sources={s['source_id']:s for s in t.read_json(t.WORK/'source_registry.json')}
 # One metadata-only scan of changed observations avoids per-object table scans.
 mappings={}
 for req,sid,ns,nid,bodysha,date,flags in c.execute("SELECT o.request_id,n.source_id,n.native_namespace,n.native_id,v.body_sha256,n.native_created_at,v.flags_json FROM entity_observations o JOIN entity_versions v ON v.entity_version_id=o.entity_version_id JOIN native_entities n ON n.entity_id=v.entity_id WHERE o.retrieved_at>='2026-10-09T02:41:51.640855+00:00'"):
  mappings.setdefault((req,sid,ns,nid),[]).append((bodysha,date,flags))
 stats={'transport_receipts':0,'saved_raw_responses':0,'mapped_native_return_observations':0,'mapping_issues':0,'parse_pending_content_responses':0}
 p=out/'raw_object_catalog.csv';issues=out/'native_mapping_issues.csv'
 with p.open('w',newline='',encoding='utf8') as f,issues.open('w',newline='',encoding='utf8') as g:
  w=csv.writer(f);w.writerow(['request_id','source_id','purpose','source_url','retrieved_at','http_status','transport_state','raw_reference','raw_sha256','stored_sha256','raw_bytes','stored_bytes','content_encoding','mapping_state','mapped_native_return_observations','unresolved_native_return_observations'])
  q=csv.writer(g);q.writerow(['request_id','source_id','native_namespace','native_id','issue'])
  for receipt in sorted((t.WORK/'receipts').glob('*.json')):
   r=t.read_json(receipt);stats['transport_receipts']+=1;state='transport_stop_no_raw_payload';matched=missing=0
   if r['status']=='saved':
    packed=(t.REPO/r['raw_reference']).read_bytes();assert t.sha(packed)==r['stored_sha256']
    raw=gzip.decompress(packed);assert t.sha(raw)==r['raw_sha256'];stats['saved_raw_responses']+=1
    state='noncontent_access_policy_or_frame_metadata'
    if r.get('purpose')=='content':
     sid=r['source_id'];source=sources[sid];body=gzip.decompress(raw) if raw.startswith(b'\x1f\x8b') else raw
     try:
      data=json.loads(body)
      if sid.startswith('se_'):rows=e.se(data,sid)
      elif sid.startswith('mastodon_'):rows=e.mastodon(data,sid)
      elif sid=='bluesky':rows=e.bluesky(data)
      elif sid in ('lemmy_nz','aussie_zone','feddit_org','midwest_social'):rows=lemmy_adapter.records(data,sid,source['base_url'])
      else:rows=e.discourse(data,sid,source['base_url'],source.get('content_license','version_specific_license_unresolved'))
     except Exception as exc:
      rows=None;state='saved_content_parse_pending';stats['parse_pending_content_responses']+=1
      q.writerow([r['request_id'],sid,'','','current_adapter_parse_pending:'+type(exc).__name__]);stats['mapping_issues']+=1
     if rows is not None:
      state='loaded_native_returns' if r['request_id'] in loaded else 'saved_content_not_loaded_native_evidence'
      for row in rows:
       record=e.prepare(row)
       found=mappings.get((r['request_id'],sid,row['native_namespace'],str(row['native_post_id'])),[])
       candidates=[x for x in found if x[0]==record['body_sha256']]
       valid=any(x[1]==row.get('native_created_at') or json.loads(x[2]).get('observed_identity_date_or_unit_conflict',{}).get('observed',[None])[0]==row.get('native_created_at') for x in candidates)
       if valid:matched+=1
       else:
        missing+=1;q.writerow([r['request_id'],sid,row['native_namespace'],row['native_post_id'],'saved_native_identity_date_body_mapping_pending' if found else 'saved_native_return_not_in_entity_observations'])
      if missing:state='loaded_with_explicit_mapping_pending' if r['request_id'] in loaded else 'saved_content_native_mapping_pending'
      stats['mapped_native_return_observations']+=matched;stats['mapping_issues']+=missing
   w.writerow([r.get('request_id'),r.get('source_id'),r.get('purpose'),r.get('url'),r.get('retrieved_at'),r.get('http_status'),r.get('status'),r.get('raw_reference'),r.get('raw_sha256'),r.get('stored_sha256'),r.get('raw_bytes'),r.get('stored_bytes'),(r.get('headers') or {}).get('Content-Encoding'),state,matched,missing])
 return stats,[{'path':str(x.relative_to(t.WORK)),'bytes':x.stat().st_size,'sha256':t.sha(x.read_bytes())} for x in (p,issues)]
