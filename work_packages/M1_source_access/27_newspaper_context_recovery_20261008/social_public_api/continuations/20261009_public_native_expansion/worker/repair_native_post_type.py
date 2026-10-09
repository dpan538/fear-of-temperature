"""Repair only retained SE comments affected by Discourse field semantics."""
import json,time
import transport as t,entities as e

def repair():
 if (t.WORK/'NATIVE_POST_TYPE_REPAIR.json').exists():return t.read_json(t.WORK/'NATIVE_POST_TYPE_REPAIR.json')
 started=time.monotonic()
 # Meaningful boundary regression: identical field spelling, distinct meaning.
 test={'source_id':'se_sustainability','native_namespace':'comment','native_post_id':'fixture','native_unit':'comment','native_created_at':'2020-01-01T00:00:00+00:00','source_url':'https://sustainability.stackexchange.com/posts/1#comment2_1','body_original':'A retained comment.','native_fields':{'post_type':'question'}}
 assert e.prepare(test)['independently_authored_body']==1
 assert e.prepare(test|{'source_id':'python_discourse','native_namespace':'forum_post','native_unit':'forum_reply','native_fields':{'post_type':3}})['independently_authored_body']==0
 with t.shared(t.footprint(0,8*1048576)):
  c=e.db()
  rows=c.execute("SELECT v.entity_version_id,n.entity_id,n.source_id,v.body_original,v.body_sha256,v.native_fields_json,MIN(o.request_id) FROM entity_versions v JOIN native_entities n ON n.entity_id=v.entity_id JOIN entity_observations o ON o.entity_version_id=v.entity_version_id WHERE n.inherited=0 AND n.source_id LIKE 'se_%' AND n.native_namespace='comment' AND v.readable_native_unit=1 AND v.independently_authored_body=0 GROUP BY v.entity_version_id").fetchall()
  c.close()
 groups={};original_versions=[]
 for vid,eid,sid,body,bodysha,fields,request in rows:
  assert body and t.sha(body.encode())==bodysha,(eid,'named_affected_body_digest')
  records=e.se({'items':[json.loads(fields)|{'body':body}]},sid)
  for r in records:r['flags']['derived_repair']='StackExchange comment post_type describes parent; numeric Discourse event rule scoped to forum_post'
  groups.setdefault((request,sid),[]).extend(records);original_versions.append((vid,eid,sid))
 totals={'affected_entity_versions':len(rows),'new_qualified_posts':0,'new_entity_versions':0,'requests_added':0,'distinct_returned_objects_added':0};before=t.state();before_objects=len(before['returned_object_ids'])
 for (request,sid),records in groups.items():
  rec=t.read_json(t.WORK/'receipts'/f'{request}.json');assert rec['source_id']==sid and rec['purpose']=='content'
  result=e.load(records,rec,sid+':named_native_post_type_semantics_repair')
  for k in ('new_qualified_posts','new_entity_versions'):totals[k]+=result[k]
 with t.shared(t.footprint(0,8*1048576)):
  c=e.db();at=t.utc()
  with c:
   for vid,eid,sid in original_versions:
    correction=t.sha((vid+'|independently_authored_body|source_specific_post_type').encode())
    c.execute('INSERT OR IGNORE INTO structural_corrections VALUES (?,?,?,?,?,?,?)',(correction,eid,'independently_authored_body','0','1',json.dumps({'reason':'Stack Exchange comment parent-type string incorrectly compared with numeric Discourse event type','raw_body_identity_unchanged':True}),at))
    # The table is a derived annotation. Its previous value is preserved above
    # and in the archived pre-repair finalized annotation export.
    c.execute('UPDATE entity_quality_annotations SET independently_authored_body=1,annotated_at=? WHERE entity_version_id=?',(at,vid))
   for vid,eid in c.execute("SELECT v.entity_version_id,n.entity_id FROM entity_versions v JOIN native_entities n ON n.entity_id=v.entity_id WHERE n.inherited=0 AND n.source_id LIKE 'se_%' AND n.native_namespace='comment' AND v.independently_authored_body=1 AND NOT EXISTS(SELECT 1 FROM entity_quality_annotations a WHERE a.entity_version_id=v.entity_version_id)"):
    c.execute('INSERT INTO entity_quality_annotations VALUES (?,?,?,?,?,?,?)',(vid,1,'original_utterance_record_via_documented_source_API','saved API native identity/date/content mapping; not truth verification',0,json.dumps({'later_retrieval_does_not_certify_historical_body':True,'native_role_and_country_not_inferred':True}),at))
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();c.close()
 after=t.state();assert after['requests']==before['requests'] and len(after['returned_object_ids'])==before_objects
 receipt={'at_utc':t.utc(),'scope':'new retained SE readable comments with parent-type strings only','totals':totals,'source_specific_field_regression_passed':True,'old_raw_or_body_read':False,'elapsed_seconds':time.monotonic()-started}
 check=t.read_json(t.WORK/'CHANGED_PIPELINE_CHECK.json');t.atomic(t.WORK/'before_native_post_type_repair/CHANGED_PIPELINE_CHECK.json',check)
 check['checks'].append('source_specific_StackExchange_parent_type_and_Disourse_event_type_semantics');check['named_additional_regression_at_utc']=t.utc();t.atomic(t.WORK/'CHANGED_PIPELINE_CHECK.json',check)
 t.atomic(t.WORK/'NATIVE_POST_TYPE_REPAIR.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
 with t.writer():repair()
