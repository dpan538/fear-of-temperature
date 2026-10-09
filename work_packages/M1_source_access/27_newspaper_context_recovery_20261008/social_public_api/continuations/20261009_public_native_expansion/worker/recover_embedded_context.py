"""Recover only named omitted embedded objects from this new tranche's raw.

No HTTP, predecessor raw/body sweep, full-body queue or renumbering is used.
"""
import json
import transport as t,entities as e

def recover():
 cutoff=t.read_json(t.WORK/'START_RECEIPT.json')['at_utc'];receipts=[];totals={'new_entities':0,'new_qualified_posts':0,'new_entity_versions':0}
 for p in sorted((t.WORK/'receipts').glob('*.json')):
  rec=t.read_json(p);sid=rec.get('source_id','')
  if rec.get('purpose')!='content' or rec.get('status')!='saved' or rec['started_at']>=cutoff or not (sid.startswith('mastodon_') or sid=='bluesky'):continue
  data=t.json_payload(rec);rows=e.mastodon(data,sid) if sid.startswith('mastodon_') else e.bluesky(data)
  nested=[r for r in rows if r.get('flags',{}).get('returned_as_embedded_reblog_context') or r.get('flags',{}).get('returned_as_embedded_quote_context') or r.get('content_state')=='unavailable_embedded_native_entity']
  if not nested:continue
  frame=sid+':recovered_embedded_context_from_saved_pre_fix_native_response'
  result=e.load(nested,rec,frame);receipts.append({'request_id':rec['request_id'],'embedded_entities_observed':len(nested),'new_entities':result['new_entities']})
  for k in totals:totals[k]+=result[k]
 t.atomic(t.WORK/'EMBEDDED_CONTEXT_RECOVERY.json',{'at_utc':t.utc(),'cutoff_start_binding':cutoff,'scope':'named new-tranche embedded-context omissions before parser repair','predecessor_raw_opened':False,'http_requests':0,'totals':totals,'receipts':receipts});return totals
if __name__=='__main__':
 with t.writer():print(recover())
