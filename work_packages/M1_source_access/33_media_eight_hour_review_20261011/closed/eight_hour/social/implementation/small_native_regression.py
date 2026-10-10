"""Bounded native transaction and provenance fixtures; no HTTP or canonical DB."""
import contextlib,json,sqlite3,tempfile
from pathlib import Path
import transport as t,entities as e,source_era_provenance as era,finalize_metadata as metadata

def main():
    original=(t.WORK,t.DB,t.SCOPE_PATH,t.shared,e._load_impl,e.db)
    checks=[]
    def check(name,value):
        assert value,name
        checks.append(name)
    records=[{'source_id':'fixture','native_namespace':'post','native_post_id':str(i),'body_original':'whole body '+str(i)} for i in range(13)]
    def result(batch):return {'at_utc':'fixture','returned_entities':len(batch),'new_entities':len(batch),'new_entity_versions':len(batch),'new_qualified_posts':len(batch),'lifetime_returned_objects':len(batch)}
    try:
        with tempfile.TemporaryDirectory(prefix='smaller_native_fixture_',dir=t.WORK) as root:
            t.WORK=Path(root);t.DB=t.WORK/'fixture.sqlite';t.SCOPE_PATH=t.WORK/'scope.json';t.atomic(t.SCOPE_PATH,{'fixture_only':True})
            rec={'request_id':'fixture-request'};seen=[]
            def loader(batch,rec,frame):
                if len(batch)>10:raise t.Stop('resource_stop fixture larger transaction')
                seen.extend(batch);return result(batch)
            e._load_impl=loader
            before=json.dumps(records,sort_keys=True)
            combined=e.load(records,rec,'fixture-frame')
            check('all whole native records committed in exact order',seen==records)
            check('no body ID date or field mutation',before==json.dumps(records,sort_keys=True))
            check('aggregate counts and completed response ledger',combined['new_qualified_posts']==13 and t.read_json(t.WORK/'SMALL_NATIVE_LOAD_STATE.json')['fixture-request']['complete'])
            seen=[]
            def singleton(batch,rec,frame):
                if len(batch)>1:raise t.Stop('resource_stop fixture singleton required')
                seen.extend(batch);return result(batch)
            e._load_impl=singleton;e.load(records,{'request_id':'single'},'fixture-frame')
            check('smaller one unit operations preserve complete native bodies',seen==records)
            seen=[]
            def partial(batch,rec,frame):
                if len(batch)>1 or len(seen)==3:raise t.Stop('resource_stop fixture true remaining capacity')
                seen.extend(batch);return result(batch)
            e._load_impl=partial
            try:e.load(records,{'request_id':'partial'},'fixture-frame')
            except t.Stop:pass
            pending=t.read_json(t.WORK/'SMALL_NATIVE_LOAD_STATE.json')['partial']
            check('partial commits explicitly pending with exact cursor',pending['committed_prefix_records']==3 and not pending['complete'])
            e._load_impl=lambda *args:(_ for _ in ()).throw(t.Stop('preserved_host_stop fixture'))
            try:e.load(records,{'request_id':'denied'},'fixture-frame')
            except t.Stop as exc:check('provider prohibition never triggers smaller-operation retry',str(exc).startswith('preserved_host_stop') and 'denied' not in t.read_json(t.WORK/'SMALL_NATIVE_LOAD_STATE.json'))
            source={'existence_at':'2011-06-08T19:00:00+00:00','existence_basis':'Official API closed_beta_date'}
            check('exact prelaunch timestamp flagged without date correction',era.limitations(source,'2011-06-08T18:59:59Z')['native_creation_before_documented_beta'])
            check('same-date at-launch record not flagged prelaunch',not era.limitations(source,'2011-06-08T19:00:00Z')['native_creation_before_documented_beta'])
            check('first observed archive span not mistaken for foundation',era.limitations({'existence_at':source['existence_at'],'existence_basis':'first observed native record'},'2011-03-01T00:00:00Z')=={})
            migrated=era.limitations(source,'2011-03-01T00:00:00Z',{'migrated_from':{'question_id':5057,'on_date':1329337246,'other_site':{'site_url':'https://diy.stackexchange.com','api_site_parameter':'diy','name':'Home Improvement'}}})
            check('native migration fields distinguish provider claim from external passage verification',migrated['native_provider_migration_metadata']['migrated_from']['original_external_passage_fetched_or_verified'] is False and migrated['native_creation_before_documented_beta'])
            check('migration never backdates documented community launch',migrated['documented_closed_beta_at']==source['existence_at'] and migrated['native_date_and_body_retained'])
            c=sqlite3.connect(t.DB)
            c.executescript('CREATE TABLE native_entities(entity_id TEXT PRIMARY KEY,source_id TEXT,native_created_at TEXT);CREATE TABLE entity_versions(entity_version_id TEXT PRIMARY KEY,entity_id TEXT,native_fields_json TEXT);CREATE TABLE entity_quality_annotations(entity_version_id TEXT PRIMARY KEY,temporal_limitations_json TEXT);CREATE TABLE immutable_fixture_bodies(id TEXT,body TEXT);')
            for i,date in enumerate(['2011-03-01T00:00:00Z','2011-04-01T00:00:00Z','2011-06-08T19:00:00Z'],1):
                c.execute('INSERT INTO native_entities VALUES (?,?,?)',(str(i),'fixture',date));c.execute('INSERT INTO entity_versions VALUES (?,?,?)',(str(i),str(i),'{}'));c.execute('INSERT INTO entity_quality_annotations VALUES (?,?)',(str(i),'{"native_creation_before_documented_beta":false}'))
            c.execute('INSERT INTO immutable_fixture_bodies VALUES (?,?)',('1','preserve full native body'));c.commit()
            old_dates=c.execute('SELECT * FROM native_entities').fetchall();old_bodies=c.execute('SELECT * FROM immutable_fixture_bodies').fetchall();c.close()
            t.shared=lambda *args,**kwargs:contextlib.nullcontext({});e.db=lambda:sqlite3.connect(t.DB)
            proof=era.repair_changed_annotations({'fixture':source},1,'fixture')
            c=sqlite3.connect(t.DB);rows=dict(c.execute('SELECT entity_version_id,temporal_limitations_json FROM entity_quality_annotations'))
            check('only changed annotation rows amended',proof['checked_changed_versions']==2 and 'documented_closed_beta_at' not in json.loads(rows['1']))
            check('literal dates and bodies preserved during metadata repair',c.execute('SELECT * FROM native_entities').fetchall()==old_dates and c.execute('SELECT * FROM immutable_fixture_bodies').fetchall()==old_bodies)
            check('changed prelaunch membership unresolved and same-time state literal',json.loads(rows['2'])['historical_community_membership_at_creation']=='unresolved_before_documented_beta' and not json.loads(rows['3'])['native_creation_before_documented_beta']);c.close()
            check('tiny metadata retains native fixed and per-row random-page allowances',metadata.metadata_footprint(100,50)==100*16+50*65536+32*1048576)
            check('larger metadata journal reservation remains 64 MiB',metadata.metadata_footprint(100,51)==100*16+64*1048576)
            check('tiny metadata operation can fit where old batch cannot',metadata.metadata_footprint(10000,50)<50000000<metadata.metadata_footprint(100000,500))
    finally:t.WORK,t.DB,t.SCOPE_PATH,t.shared,e._load_impl,e.db=original
    proof={'at_utc':t.utc(),'passed':True,'check_count':len(checks),'checks':checks,'fixture_only':True,'source_requests':0,'canonical_database_reads_or_writes':0,'implementation_sha256':{name:t.sha((t.WORK/name).read_bytes()) for name in ['entities.py','native_capacity_sizing.py','finalize_metadata.py','source_era_provenance.py','incremental_durability.py']}}
    t.atomic(t.WORK/'SMALL_NATIVE_OPERATION_REGRESSION.json',proof);print(json.dumps(proof))

if __name__=='__main__':main()
