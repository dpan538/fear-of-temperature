import json
import elt
checks=[];records=[]
for row in map(json.loads,(elt.OWN/'SOURCE_PREPARATION_RESULTS.jsonl').read_text().splitlines()):
 if row['job_id'] in ['papers_past_material_use','papers_past_copyright','papers_past_identity_era']:
  rec=elt._receipt(row['receipt_reference'].split('/')[-1].removesuffix('.json'));assert elt.source_access_challenge(elt.read_payload(rec['raw_reference']));records.append((row,rec));elt.append('SOURCE_PREPARATION_RETURN_CLASSIFICATIONS.jsonl',{'at_utc':elt.utc(),'job_id':row['job_id'],'original_transport_status':rec['status'],'derived_source_content_status':'source_access_challenge_not_readable_requested_document','raw_reference':rec['raw_reference'],'identity_date_content_mapping':'not_verified','new_HTTP':False})
assert len(records)==3;checks.append({'test':'three actual HTTP200 HTML challenge responses are not readable source documents','passed':True})
normal=elt._receipt('27d7acd9ca679bdc6de82288');assert not elt.source_access_challenge(elt.read_payload(normal['raw_reference']));checks.append({'test':'actual1988 native newspaper issue is not misclassified as an access challenge','passed':True})
result=elt.preserve_source_access_challenge(records[0][1]);assert result['status']=='saved_source_access_challenge' and elt._receipt(records[0][1]['target_id'])['status']=='saved' and 'paperspast.natlib.govt.nz' in elt.state()['access_stops'];checks.append({'test':'source host stop preserves actual saved transport receipt and raw evidence','passed':True})
out=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());out['checks']+=checks;elt.preparation_save('CHANGED_CHAIN_CHECK.json',out);print(json.dumps({'all_passed':True,'checks':len(out['checks']),'original_responses_preserved':True}))
