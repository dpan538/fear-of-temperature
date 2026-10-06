"""Read exactly one coordinator-named saved raw object. Never contributes newspaper counts."""
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import parser,staging,transport

def main():
    own=transport.OWN
    started=transport.utc()
    executed_code={p.name:transport.sha(p) for p in (Path(__file__),Path(parser.__file__),Path(staging.__file__),Path(transport.__file__))}
    old=own.parent.parent/'22_real_payload_acquisition_20261005'
    rid='ca1698af14973f0b5c0ba528'
    receipt=json.loads((old/'media/requests'/f'{rid}.json').read_text())
    raw=old/receipt['raw_path'];data=raw.read_bytes()
    if parser.digest(data)!=receipt['sha256']:raise RuntimeError('Frozen raw digest mismatch')
    oldbody=old/'media/bodies'/f'{rid}.txt';oldhash=parser.digest(oldbody.read_bytes())
    # Inspection found three aside nodes: newsletter, ad slot, and empty widget.
    # This exclusion belongs to this observed adapter, not all newspaper HTML.
    result=parser.extract(data,selector='.entry-content',remove=('aside','.below-content'),
        boundary_evidence='Named raw DOM inspection: seven narrative p blocks; aside newsletter/ad/empty widget and below-content widgets excluded')
    if 'l ong-time' in result['body'] or 'long-time' not in result['body']:
        raise RuntimeError('Inline regression')
    for contaminant in ('Never miss a story','/5805113/Texas-Tribune-Post-Insertion-1'):
        if contaminant in result['body']:raise RuntimeError('Inspected widget remains')
    with transport.HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        directory=own/'diagnostics';directory.mkdir(exist_ok=True)
        name=f"{rid}_{result['parser_sha256'][:12]}_{result['adapter_sha256'][:12]}"
        body=directory/(name+'.txt')
        if body.exists() and body.read_text()!=result['body']:raise RuntimeError('Existing derivative conflict')
        if not body.exists():body.write_text(result['body'])
        record=dict(lane='diagnostic',source_id='texastribune',native_id=receipt['request_url'].rstrip('/'),acquisition_parent='texastribune_public_html',stratum='US',country='US',edition='Texas English digital',publication_date='2015-12-01',publication_precision='publisher-local day; exact original timestamp remains in frozen manifest',unit_kind='article',provenance='direct publisher media discourse; newspaper identity not established',newspaper_eligible=0)
        version=dict(raw_path=str(raw),raw_sha256=receipt['sha256'],body_path=str(body),body_sha256=result['body_sha256'],parser_sha256=result['parser_sha256'],retrieved_at=receipt['finished_at_utc'],content_version_time=None,historical_version_equivalence='not established',qualified_readable=0,extraction_json=json.dumps({k:v for k,v in result.items() if k!='body'}))
        cursor={'last_raw_request':rid,'last_parser_sha256':result['parser_sha256'],'last_adapter_sha256':result['adapter_sha256'],'next':'none; targeted diagnostic only','newspaper_collection_started':False}
        db=own/'staging/newspaper.sqlite3'
        with staging.writer(db) as con:first=staging.ingest(con,record,version,receipt,cursor)
        with staging.writer(db) as con:
            second=staging.ingest(con,record,version,receipt,cursor);snap=staging.snapshot(con)
        assert second['new_versions_inserted']==0 and snap['qualified_newspaper_articles']==0
        assert parser.digest(raw.read_bytes())==receipt['sha256'] and parser.digest(oldbody.read_bytes())==oldhash
        report={'started_at_utc':started,'at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'executed_code_sha256':executed_code,'lane':'real_saved_non_newspaper_diagnostic',
            'raw_path':str(raw),'raw_sha256_before_after':receipt['sha256'],'old_body_sha256_before_after':oldhash,
            'body_path':str(body),'body_bytes':body.stat().st_size,'body_sha256':result['body_sha256'],
            'parser_sha256':result['parser_sha256'],'adapter_sha256':result['adapter_sha256'],
            'inline_token':'long-time','widget_regressions_removed':True,'first_write':first,
            'restart_duplicate_write':second,'staging_snapshot':snap,'new_downloads':0,
            'newspaper_coverage_contribution':0,'historical_body_equivalence':'unverified'}
        # Preserve every historical pass receipt, including the original first-write proof.
        stamp=started.replace(':','').replace('.','').replace('+','_')
        (directory/(name+'_'+stamp+'_RECEIPT.json')).write_text(json.dumps(report,indent=2)+'\n')
        (own/'staging/CHECKPOINT.json').write_text(json.dumps(snap,indent=2)+'\n')
        print(json.dumps(report,indent=2))

if __name__=='__main__':main()
