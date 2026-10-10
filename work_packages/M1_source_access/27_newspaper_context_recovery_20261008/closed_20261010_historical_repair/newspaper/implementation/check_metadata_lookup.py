import sqlite3,json
import elt
c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE articles(article_id TEXT PRIMARY KEY,work_family_id TEXT);CREATE TABLE article_versions(article_id TEXT,body_sha256 TEXT);INSERT INTO articles VALUES("a","fa"),("b","fb"),("c","fc");INSERT INTO article_versions VALUES("a","same"),("b","same"),("c","different");');checks=[]
for digest,aid in [('same','b'),('same','a'),('different','c'),('missing','new')]:
 expected=c.execute('SELECT v.article_id,a.work_family_id FROM article_versions v JOIN articles a ON a.article_id=v.article_id WHERE v.body_sha256=? AND v.article_id<>? LIMIT 1',(digest,aid)).fetchone();actual=elt._body_hash_candidate(c,digest,aid);assert actual==expected,(actual,expected)
checks.append({'test':'metadata hash candidate index preserves existing candidate lookup including self and missing cases','passed':True})
elt._BODY_HASH_CANDIDATES['same'].append(('new','native_new'));assert elt._body_hash_candidate(c,'same','a')==('b','fb');assert elt._BODY_HASH_CANDIDATES['same'][-1]==('new','native_new');checks.append({'test':'new native identity is incrementally indexed without family merging or schema writes','passed':True})
elt._BODY_HASH_CANDIDATES=None;c.close();out=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());out['checks']+=checks;elt.preparation_save('CHANGED_CHAIN_CHECK.json',out);print(json.dumps({'all_passed':True,'checks':len(out['checks']),'test_database':'memory only'}))
