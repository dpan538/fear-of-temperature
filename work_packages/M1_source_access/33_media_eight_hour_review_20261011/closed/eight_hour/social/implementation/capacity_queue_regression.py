"""Capacity state fixtures without HTTP, source resets or canonical DB access."""
import contextlib,copy,json,tempfile
from pathlib import Path
import transport as t,capacity_queue_recovery as recovery,collect

def main():
    original=t.WORK,t.shared;checks=[]
    def check(name,value):assert value,name;checks.append(name)
    try:
        with tempfile.TemporaryDirectory(prefix='capacity_queue_fixture_',dir=t.WORK) as root:
            t.WORK=Path(root)
            failed='resource_stop '+json.dumps({'pending_bytes':t.footprint(2097152)})
            base={'source':'fixture','kind':'discourse_archive','base':'https://example.invalid','license':'fixture','frame':'fixture:frame','status':'complete_operation_capacity_blocked','stop':failed,'chunks':[{'topic':7,'ids':[11,12,13]}],'topics':[8],'seen_topics':[7]}
            def shared(pending,*args,**kwargs):
                if pending>36000000:raise t.Stop('resource_stop fixture current capacity')
                return contextlib.nullcontext({})
            t.shared=shared;f=copy.deepcopy(base)
            recovery.reconsider([f]);url,route=collect.job(f)
            check('smaller known native lookup admitted without dropping IDs',f['status']=='active' and f['chunks'][0]['ids']==[11,12,13] and route=='discourse_single_remaining' and 'post_ids%5B%5D=11' in url)
            check('original larger operation failure retained',f['preserved_default_response_capacity_failure']==failed and f['topics']==[8])
            deny={'status':'source_access_stop','stop':{'http_status':403}};quota={'status':'native_daily_quota_exhausted'}
            recovery.reconsider([deny,quota],metadata_changed=True)
            check('source denial and quota stop states never reopened',deny['status']=='source_access_stop' and quota['status']=='native_daily_quota_exhausted')
            t.shared=lambda *args,**kwargs:contextlib.nullcontext({})
            recovery.reconsider([f],metadata_changed=True)
            check('only improved guarded headroom restores original operation',f['status']=='active' and not f['capacity_small_native_only'] and 'raw_cap_bytes' not in f and f['chunks'][0]['ids']==[11,12,13])
            g=copy.deepcopy(base);g['chunks']=[];recovery.reconsider([g],metadata_changed=False)
            check('larger operations remain blocked without metadata change',g['status']=='complete_operation_capacity_blocked')
            t.shared=lambda *args,**kwargs:(_ for _ in ()).throw(t.Stop('fixed_deadline'))
            try:recovery.reconsider([g],metadata_changed=True)
            except t.Stop as exc:check('deadline boundary propagates without capacity override',str(exc)=='fixed_deadline')
    finally:t.WORK,t.shared=original
    proof={'at_utc':t.utc(),'passed':True,'check_count':len(checks),'checks':checks,'source_requests':0,'canonical_database_access':False,'implementation_sha256':{name:t.sha((t.WORK/name).read_bytes()) for name in ['capacity_queue_recovery.py','collect.py','incremental_durability.py']}}
    t.atomic(t.WORK/'CAPACITY_QUEUE_REGRESSION.json',proof);print(json.dumps(proof))

if __name__=='__main__':main()
