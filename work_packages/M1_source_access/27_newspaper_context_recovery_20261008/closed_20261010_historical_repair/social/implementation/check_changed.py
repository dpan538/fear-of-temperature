import tempfile,sqlite3,json
from pathlib import Path
import transport as t,entities as e
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'fixture.sqlite';c=e.db(p);c.executescript((t.WORK/'schema_legacy.sql').read_text())
 c.execute("INSERT INTO posts VALUES ('social:se_test:1','se_test','1','https://test/q/1','question','1',NULL,'2020-01-01','u','unknown',NULL,'partial')")
 c.execute("INSERT INTO native_identities VALUES ('se_test','post','1','social:se_test:1','established_ID_preserved')")
 c.execute("INSERT INTO versions VALUES ('legacyversion','social:se_test:1','sha','old','old',NULL,NULL,'2026-10-09','unknown','native','full','direct','{}')");c.commit();e.migrate(c)
 assert c.execute('SELECT entity_id FROM native_entities').fetchone()[0]=='social:se_test:1'
 assert c.execute('SELECT core_body_version_id FROM entity_versions').fetchone()[0]=='legacyversion'
 checks=['legacy_id_and_version_reference_preserved']
 rows=e.se({'items':[{'question_id':1,'creation_date':1577836800,'body':'x','link':'https://test/q/1'},{'comment_id':1,'post_id':1,'creation_date':1577836800,'body':'x'}]},'se_test')
 assert len({e.key(x) for x in rows})==2;checks.append('same_numeric_question_comment_distinct')
 cases=[dict(source_id='test',native_namespace='status',native_post_id='1',native_unit='media_only_post',body_original='',source_url='https://test/1',native_created_at='2020-01-01'),dict(source_id='test',native_namespace='post',native_post_id='2',native_unit='index_preview',body_original='hello',content_state='truncated_index_preview',source_url='https://test/2',native_created_at='2020-01-01'),dict(source_id='test',native_namespace='post',native_post_id='3',native_unit='forum_post',body_original='短文',source_url='https://test/3',native_created_at=None),dict(source_id='test',native_namespace='post',native_post_id='4',native_unit='forum_reply',body_original='x',source_url='https://test/4',native_created_at='2020-01-01')]
 prepared=[e.prepare(x) for x in cases];assert [x['readable_native_unit'] for x in prepared]==[0,0,0,1];checks.append('bodyless_preview_missing_date_retained_without_coverage_short_text_retained')
 b=e.bluesky({'feed':[{'post':{'uri':'at://did:test/app.bsky.feed.post/1','cid':'cid','author':{'did':'did:test'},'record':{'text':'x','createdAt':'2020-01-01','reply':{'parent':{'uri':'at://missing'},'root':{'uri':'at://root'}}}},'reason':{'by':{'did':'did:other'},'indexedAt':'2020-01-02'}}]})
 assert len(b)==2 and b[1]['native_unit']=='repost_wrapper' and not e.prepare(b[1])['readable_native_unit'];checks.append('repost_and_authored_entity_separate_unresolved_edges')
 assert len(b[0]['edges'])==2;checks.append('typed_reply_root_edges')
 # Execute the changed transactional loader twice in the isolated synthetic store.
 import contextlib
 original_work=t.WORK;original_shared=t.shared;original_release=t.release;original_db=e.db
 t.WORK=Path(d);t.atomic(t.WORK/'STATE.json',{'requests':1109,'returned_object_ids':['inherited|post|'+str(i) for i in range(51671)],'object_ids':[]})
 @contextlib.contextmanager
 def fixture_lock(*a,**kw):yield {}
 t.shared=fixture_lock;t.release=lambda **kw:{'max_distinct_native_content_objects':None}
 e.db=lambda:original_db(p)
 rec={'request_id':'fixture','url':'https://test/native','retrieved_at':'2026-10-09','raw_reference':'fixture_only','raw_sha256':'sha','stored_sha256':'stored','raw_bytes':1,'stored_bytes':1}
 first=e.load(cases,rec,'fixture');second=e.load(cases,rec,'fixture')
 assert not (t.WORK/'TELEMETRY_ERRORS.jsonl').exists()
 assert (t.WORK/'COMMITTED_METADATA.jsonl').exists()
 assert first['lifetime_returned_objects']==51675
 assert t.state()['requests']==1109
 assert first['new_entities']==4 and second['new_entities']==0 and second['new_entity_versions']==0
 assert c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]==2
 checks += ['changed_loader_sql_transaction_all_entity_states','load_rerun_idempotent_no_preview_or_bodyless_qualified_posts']
 e.db=original_db;t.shared=original_shared;t.release=original_release;t.WORK=original_work
 t._state_cache.clear()
 t.atomic(t.WORK/'CHANGED_PIPELINE_CHECK.json',{'at_utc':t.utc(),'passed':True,'checks':checks,'synthetic_only':True,'accepted_predecessor_checks_reused':True})
 print(json.dumps({'passed':True,'checks':len(checks)}))
