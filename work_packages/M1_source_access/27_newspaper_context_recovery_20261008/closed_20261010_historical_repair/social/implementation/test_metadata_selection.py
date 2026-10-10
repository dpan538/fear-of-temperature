"""New-version ID selection matches committed observation metadata without hash-order scans."""
import sqlite3,transport as t
c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE entity_versions(entity_version_id TEXT PRIMARY KEY,first_retrieved_at TEXT);CREATE TABLE entity_observations(entity_version_id TEXT,request_id TEXT,retrieved_at TEXT,PRIMARY KEY(entity_version_id,request_id));CREATE TABLE entity_quality_annotations(entity_version_id TEXT PRIMARY KEY);')
begin='2026-10-10T01:43:58.368759+00:00'
for i in range(401):
 vid=t.sha(str(i).encode());c.execute('INSERT INTO entity_versions VALUES (?,?)',(vid,begin));c.execute('INSERT INTO entity_observations VALUES (?,?,?)',(vid,str(i),begin))
 if i%2==0:c.execute('INSERT INTO entity_observations VALUES (?,?,?)',(vid,str(i)+'repeat',begin))
 if i<200:c.execute('INSERT INTO entity_quality_annotations VALUES (?)',(vid,))
c.execute('INSERT INTO entity_versions VALUES (?,?)',('accepted-old','2026-10-09T20:00:00+00:00'));c.execute('INSERT INTO entity_observations VALUES (?,?,?)',('accepted-old','reobserve-old',begin))
old='SELECT DISTINCT o.entity_version_id FROM entity_observations o JOIN entity_versions v ON v.entity_version_id=o.entity_version_id WHERE o.retrieved_at>=? AND v.first_retrieved_at>=? AND NOT EXISTS (SELECT 1 FROM entity_quality_annotations a WHERE a.entity_version_id=v.entity_version_id) ORDER BY o.entity_version_id'
new='SELECT v.entity_version_id FROM entity_versions v WHERE v.first_retrieved_at>=? AND NOT EXISTS (SELECT 1 FROM entity_quality_annotations a WHERE a.entity_version_id=v.entity_version_id) ORDER BY v.rowid'
a={x[0] for x in c.execute(old,(begin,begin))};b=[x[0] for x in c.execute(new,(begin,))];assert a==set(b) and len(b)==201 and 'accepted-old' not in b
plan=c.execute('EXPLAIN QUERY PLAN '+new,(begin,)).fetchall();assert 'SCAN v' in plan[0][3] and 'USING INDEX' not in plan[0][3]
t.atomic(t.WORK/'METADATA_SELECTION_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'synthetic':True,'checks':['same_new_unannotated_version_set_with_repeated_observations','accepted_old_versions_not_reaudited','sequential_version_row_scan_without_full_hash-order_observation_lookups'],'source_requests':0,'corpus_writes':0,'query_plan':plan});print({'passed':True,'new_ids':len(b),'plan':plan})
