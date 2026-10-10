"""Bounded larger metadata transactions: journal sizing and idempotent replay."""
import contextlib,json,sqlite3,tempfile
from pathlib import Path
from unittest.mock import patch
import transport as t,entities as e
from finalize_metadata import finalize
@contextlib.contextmanager
def fixture_lock(*a,**k):yield {}
with tempfile.TemporaryDirectory(dir=t.WORK) as name:
 w=Path(name);db=w/'synthetic.sqlite3';scope=w/'scope.json';at='2026-10-10T01:43:58.368759+00:00';t.atomic(scope,{'earliest_network_and_load_start_at_utc':at});t.atomic(w/'source_registry.json',[{'source_id':'fixture_archive'}])
 c=sqlite3.connect(db);c.executescript('CREATE TABLE native_entities(entity_id PRIMARY KEY,source_id,native_namespace,native_id,native_created_at,native_unit);CREATE TABLE entity_versions(entity_version_id PRIMARY KEY,entity_id,native_edited_at,independently_authored_body,native_fields_json,flags_json,first_retrieved_at);CREATE TABLE publication_memberships(entity_id,publication_key,basis,evidence_json,PRIMARY KEY(entity_id,publication_key));CREATE TABLE entity_quality_annotations(entity_version_id PRIMARY KEY,independently_authored_body,directness,native_mapping_basis,original_external_body_checked,temporal_limitations_json,annotated_at);')
 for i in range(1001):
  eid='stable-native-'+str(i);c.execute('INSERT INTO native_entities VALUES (?,?,?,?,?,?)',(eid,'fixture_archive','message_id','<'+str(i)+'@native>','2002-07-02T01:23:48+00:00','mailing_list_message'));c.execute('INSERT INTO entity_versions VALUES (?,?,?,?,?,?,?)',(t.sha(eid.encode()),eid,None,1,json.dumps({'native_headers':'metadata'*70}),json.dumps({'archival_reproduction_of_original_public_message':True}),at))
 c.commit();before=c.execute('SELECT entity_version_id,entity_id FROM entity_versions ORDER BY entity_version_id').fetchall();c.close()
 with patch.object(t,'WORK',w),patch.object(t,'DB',db),patch.object(t,'SCOPE_PATH',scope),patch.object(t,'shared',fixture_lock),patch.object(e,'db',lambda:sqlite3.connect(db)):
  result=finalize(batch_records=1000);assert result['quality_annotations']==1001 and result['memberships']==1001
  receipt=t.read_json(w/'METADATA_FINALIZATION_RECEIPT.json');assert receipt['bounded_transaction_records']==1000 and receipt['max_observed_journal_peak_bytes']<receipt['max_reserved_operation_bytes']
  repeated=finalize(batch_records=1000);assert not any(repeated.values())
 c=sqlite3.connect(db);assert c.execute('SELECT entity_version_id,entity_id FROM entity_versions ORDER BY entity_version_id').fetchall()==before;assert c.execute('SELECT COUNT(*) FROM entity_quality_annotations WHERE directness=?',('archival_reproduction_of_original_public_mailing_list_message',)).fetchone()[0]==1001;c.close()
t.atomic(t.WORK/'METADATA_BATCH_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'checks':['1001_new_version_annotations_in_two_bounded_transactions','observed_journal_within_complete_operation_reservation','idempotent_replay_and_stable_native_version_IDs','archival_directness_preserved'],'source_requests':0,'real_corpus_writes':0});print({'passed':True,'records':1001,'transactions':2,'measured_peak_bytes':receipt['max_observed_journal_peak_bytes']})
