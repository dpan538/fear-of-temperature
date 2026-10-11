"""Named new-tranche template replay using saved responses and unchanged IDs."""
import json
import elt,native_batches,production
def resume_one():
 p=elt.OWN/'NEW_TITLE_TEMPLATE_RECOVERY.json'
 if not p.exists():return 0
 manifest=json.loads(p.read_text());donepath=elt.OWN/'NEW_TITLE_TEMPLATE_RECOVERY_DONE.json';done=set(json.loads(donepath.read_text())) if donepath.exists() else set()
 for row in manifest:
  aid=row['article_id']
  if aid in done:continue
  assert row['source_id'] in ['barnet_post','haringey_community_press','newham_voices','west_highland_free_press','ec1_echo'] and row['original_load_status']=='pending_public_HTML_native_body_version_mapping'
  receipt=elt._receipt(row['native_request_id']);assert receipt['source_id']==row['source_id'] and receipt['status']=='saved'
  objects=json.loads(elt.read_payload(receipt['raw_reference']));objects=[objects] if isinstance(objects,dict) else objects;matches=[(i,o) for i,o in enumerate(objects) if o.get('id')==row['native_post_id']];assert len(matches)==1
  index,obj=matches[0];target=dict(native_post_id=row['native_post_id'],article_url=row['source_url'],url=row['native_source_url'],month=row['publication_month'])
  record,body,status=native_batches.representation(obj,row['source_id'],target,receipt,index)
  record.update(saved_public_HTML_request_id=row['public_HTML_request_id'],structural_replay_reference='NEW_TITLE_TEMPLATE_RECOVERY.json',original_pending_evidence_id=row['original_pending_evidence_id'],original_pending_load_status=row['original_load_status'],replayed_without_new_HTTP=True)
  import run
  run.next_action=dict(opportunity='saved_new_title_template_replay:'+aid,source_id=row['source_id'],kind='saved_response_structural_Load',new_HTTP=False)
  result=elt.load(record,body,status)
  statuses=native_batches.raw_status_map();original=statuses.get(aid,dict(status=row['original_load_status'],request_id=row['native_request_id'],individual_saved_native_response_not_batch=True));statuses[aid]=dict(original,status=result['load_status'],body_sha256=result.get('body_sha256'),version_id=result.get('version_id'),structural_replay_preserves_original_receipt=True)
  elt.append('NEW_TITLE_TEMPLATE_RECOVERY_RESULTS.jsonl',dict(at_utc=elt.utc(),article_id=aid,original_unit_status=original,load_status=result['load_status'],new_HTTP=False,raw_and_native_IDs_unchanged=True))
  elt.save('NATIVE_BATCH_UNIT_STATUS.json',statuses)
  if result['load_status'] in ['confirmed_complete','already_retained_identity']:production.KNOWN.add(elt.canon(result['source_url']))
  done.add(aid);elt.save('NEW_TITLE_TEMPLATE_RECOVERY_DONE.json',sorted(done));return 1
 return 0
