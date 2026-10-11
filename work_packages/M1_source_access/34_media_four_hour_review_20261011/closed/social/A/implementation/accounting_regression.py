"""Exact-once growth/overlap accounting fixtures; no corpus access or HTTP."""
import tempfile,json
from pathlib import Path
import transport as t

def main():
    previous=t.REPO,t.ROOT,t.WORK,t.acquisition_tail
    checks=[]
    def check(name,value):assert value,name;checks.append(name)
    try:
        with tempfile.TemporaryDirectory(prefix='accounting_fixture_',dir=t.WORK) as root:
            r=Path(root);t.REPO=r;t.ROOT=r/'live';t.WORK=r/'worker';t.WORK.mkdir();t.ROOT.mkdir();a=r/'publication'/'a';b=r/'publication'/'b';a.mkdir(parents=True);b.mkdir()
            (t.ROOT/'bytes').write_bytes(b'a'*100);(a/'bytes').write_bytes(b'a'*30);(b/'bytes').write_bytes(b'b'*40)
            scope={'prior_media_bytes':5,'media_lifetime_accounting_roots':['live','publication','publication/a'],'social_additional_accounting_roots':['publication/a','publication/b','publication/a'],'lease_coordination_reference':'leases.json','owner_pending_lease_bytes':8,'physical_floor_bytes':0,'recovery_allowance_bytes':0,'media_lifetime_cap_bytes':1000000,'social_incremental_allocation_bytes':1000000}
            t.atomic(r/'leases.json',{'active_leases':[{'thread_id':t.OWNER,'active':True,'reserved_bytes':8},{'thread_id':'fixture-other','active':True,'reserved_bytes':8}]});t.acquisition_tail=lambda _: {'bytes':10}
            old=t.preflight(scope,3)
            check('live plus both publication roots charged exactly once',old['social_bytes']==170 and old['social_additional_accounting_bytes']==70)
            check('nested package publication root not double charged in shared accounting',old['media_bytes']==175)
            (a/'growth').write_bytes(b'a'*17);one=t.preflight(scope,3)
            check('growth in first publication root immediately reduces both budgets',old['social_headroom']-one['social_headroom']==17 and old['media_headroom']-one['media_headroom']==17)
            (b/'growth').write_bytes(b'b'*23);two=t.preflight(scope,3)
            check('growth in second publication root immediately reduces both budgets',one['social_headroom']-two['social_headroom']==23 and one['media_headroom']-two['media_headroom']==23)
            scope['social_additional_accounting_roots']+=['live','live/child'];check('duplicate and nested live paths cannot double charge',t.accounting_totals(scope)['social_bytes']==210)
            check('journal and native fixed margins remain unchanged',t.footprint()==32*1048576)
    finally:t.REPO,t.ROOT,t.WORK,t.acquisition_tail=previous
    proof={'at_utc':t.utc(),'passed':True,'checks':checks,'source_requests':0,'canonical_database_access':False,'transport_sha256':t.sha((t.WORK/'transport.py').read_bytes()),'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'fixed_output_allowance_reduced':False}
    t.atomic(t.WORK/'ACCOUNTING_REGRESSION.json',proof);print(json.dumps(proof))

if __name__=='__main__':main()
