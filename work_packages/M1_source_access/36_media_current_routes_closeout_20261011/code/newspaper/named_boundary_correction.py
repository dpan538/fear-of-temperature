"""One named current-tranche boundary disposition, by the sole writer."""
import json
import elt
def perform_once():
 p=elt.OWN/'NAMED_BOUNDARY_CORRECTION_DONE.json'
 if p.exists():return
 aid='border_watch:post:5163';rows=[json.loads(x) for x in (elt.OWN/'LOAD_LOG.jsonl').read_text().splitlines() if x]
 row=next(r for r in rows if r.get('article_id')==aid and r.get('load_status')=='confirmed_complete')
 assert row['request_id']=='90506ca4772e6aab26ca4ef3' and row['public_HTML_request_id']=='ca288819066dea895e00176c'
 status='pending_live_recording_wrapper_complete_written_article_boundary'
 reason='Named post5163 is a YouTube live-recording wrapper with two descriptive paragraphs; matching HTML/native text does not establish a complete independent written article. Keep stable ID/body/versions/raw and original Load receipt; no video download, length/topic rule or source rejection.'
 elt.assert_release();elt.reclassify_named(aid,status,reason)
 body=elt.read_payload(row['raw_reference']);assert elt.sha(body)==row['raw_sha256']
 row.update(boundary_correction_reference='NAMED_BORDER_LIVE_RECORDING_REVIEW.json',complete_original_article_not_established=True,original_confirmed_version_preserved=row['version_id'])
 result=elt.load(row,'',status)
 states=json.loads((elt.OWN/'NATIVE_BATCH_UNIT_STATUS.json').read_text());states[aid]=dict(states.get(aid,{}),status=status,named_boundary_correction=True);elt.save('NATIVE_BATCH_UNIT_STATUS.json',states)
 elt.save('NAMED_BOUNDARY_CORRECTION_DONE.json',dict(at_utc=elt.utc(),article_id=aid,status=status,current_countable=False,original_versions_preserved=True,pending_evidence_id=result.get('evidence_id')))
 try:__import__('live_progress')._rows.pop(aid,None)
 except ImportError:pass
