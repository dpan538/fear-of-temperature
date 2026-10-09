"""One isolated changed-chain check; fixtures never enter the corpus store."""
import json
import social_elt as e

def run():
    c=e.connect(':memory:')
    rec=dict(request_id='fixture_response',url='https://fixture.invalid',retrieved_at='2026-10-08T00:00:00Z',raw_reference='fixture_only',raw_sha256='fixture',stored_sha256='fixture',raw_bytes=0,stored_bytes=0)
    native=dict(question_id=12,creation_date=1420070400,body='<p>one &amp; two</p>',link='https://fixture.invalid/questions/12',content_license='CC BY-SA 3.0',owner={'user_id':4})
    r=e.stackexchange_records({'items':[native]},'fixture')[0]
    assert r['native_created_at'].startswith('2015-01-01')
    assert r['content_license']=='CC BY-SA 3.0' and r['author_role']=='unknown'
    r=e.prepare_record(r,{'fixture|post|12':'social:fixture:12'})
    assert r['body_text']=='one & two' and 'body' not in r['native_fields']
    assert e.insert_rows(c,[r],rec)==(1,1)
    assert e.insert_rows(c,[r],rec)==(0,0)
    r2=e.prepare_record(dict(r,body_original='<p>corrected</p>',native_edited_at='2026-10-01T00:00:00Z'),{'fixture|post|12':'social:fixture:12'})
    assert e.insert_rows(c,[r2],rec)==(0,1)
    assert c.execute('SELECT COUNT(*) FROM posts').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM versions').fetchone()[0]==2
    assert c.execute('SELECT body_original FROM versions WHERE body_version_id=?',(r['body_version_id'],)).fetchone()[0]==native['body']
    comment=e.stackexchange_records({'items':[dict(comment_id=12,post_id=99,post_type='answer',creation_date=1420070401,body='a reply',content_license='CC BY-SA 3.0')]},'fixture')[0]
    comment=e.prepare_record(comment)
    assert comment['thread_id']=='unresolved' and comment['reply_to_post_id']=='99'
    assert comment['persistent_post_id']=='social:fixture:comment:12'
    assert e.insert_rows(c,[comment],rec)==(1,1)
    assert e.insert_rows(c,[comment],rec)==(0,0)
    assert c.execute('SELECT COUNT(*) FROM native_identities').fetchone()[0]==2
    alias=dict(r2,source_url='https://fixture.invalid/questions/12/new-slug')
    assert e.insert_rows(c,[alias],rec)==(0,0)
    assert c.execute("SELECT COUNT(*) FROM post_urls WHERE canonical_or_alias='alias'").fetchone()[0]==1
    assert c.execute('SELECT source_url FROM posts WHERE persistent_post_id=?',(r['persistent_post_id'],)).fetchone()[0]==native['link']
    bad=dict(r,native_created_at='2014-01-01T00:00:00Z')
    try: e.insert_rows(c,[bad],rec)
    except e.Stop: pass
    else: raise AssertionError('date conflict must stop')
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    c.close()
    result=dict(at_utc=e.utc(),passed=True,checks=['question_comment_numeric_ID_collision','established_identity_alias_preserved','answer_parent_question_root_unresolved','URL_slug_alias_preserves_identity','native_creation_UTC','native_license_preserved','role_not_inferred','structural_plain_text','same_ID_same_version_idempotent','changed_body_preserves_old_version','date_conflict_stops','foreign_key_consistency'],fixture_store='memory_only',fixture_corpus_rows=0)
    with e.shared(65536): e.atomic(e.WORK/'PIPELINE_CHECK_IDENTITY.json',result)
    print(json.dumps(result))
if __name__=='__main__':
    with e.writer(): run()
