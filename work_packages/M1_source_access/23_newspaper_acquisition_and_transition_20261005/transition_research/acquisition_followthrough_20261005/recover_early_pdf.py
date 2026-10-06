"""One explicit dynamic-cap recovery of the exact publisher-linked1988 issue."""
import datetime as dt
import fcntl
import hashlib
import json
import pathlib
import shutil
import urllib.request
import importlib.util

ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('collector',ROOT/'collect_first_batch.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
rows=[json.loads(x) for x in (ROOT/'REQUESTS.jsonl').read_text().splitlines()]
target=json.loads((ROOT/'EARLY_PDF_TARGET.json').read_text())
prior=next(x for x in rows if x['url']==target['url'] and x['status']=='object_cap_stop')
rid=hashlib.sha256((target['url']+'|dynamic-recovery-01').encode()).hexdigest()[:24]
receipt={'request_id':rid,'url':target['url'],'purpose':'issue_pdf','requested_at_utc':collector.utc(),
    'previous_request_id':prior['request_id'],'recovery_reason':'Dai explicitly requested dynamic capacity and consecutive acquisition; actual available space supports a larger exact-source object',
    'resource_policy':'DYNAMIC_OBJECT_POLICY.json','unit_kind':'issue_container','status':'not_started'}
if any(x['request_id']==rid for x in rows):
    print(json.dumps(next(x for x in rows if x['request_id']==rid)));raise SystemExit
with collector.LOCK.open('a+b') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    budget=collector.preflight()
    free=shutil.disk_usage(ROOT).free
    cap=min(16*1024**2,(collector.LIFETIME_CAP-budget['media_lifetime_used_bytes'])//4,
            (free-collector.FLOOR-collector.OVERHEAD)//4)
    receipt.update(budget=budget,dynamic_raw_cap_bytes=cap)
    if not budget['passed'] or cap<=len((ROOT/prior['raw_path']).read_bytes()):
        raise RuntimeError('Live dynamic capacity does not support recovery')
    path=ROOT/'raw'/(rid+'.pdf')
    req=urllib.request.Request(target['url'],headers={'User-Agent':'FearOfTemperatureResearch/1.0 (bounded public newspaper acquisition)'})
    opener=urllib.request.build_opener(collector.DeclaredRedirects)
    try:
        with opener.open(req,timeout=40) as response:
            receipt.update(http_status=response.status,content_type=response.headers.get('Content-Type'),
                content_length=response.headers.get('Content-Length'),etag=response.headers.get('ETag'),
                last_modified=response.headers.get('Last-Modified'))
            count=0
            with path.open('wb') as output:
                while True:
                    block=response.read(min(65536,cap-count+1))
                    if not block:break
                    allowed=min(len(block),cap-count);output.write(block[:allowed]);count+=allowed
                    if allowed<len(block):receipt['status']='dynamic_object_cap_stop';break
                    if shutil.disk_usage(ROOT).free-collector.OVERHEAD<collector.FLOOR:
                        receipt['status']='physical_floor_stop';break
        raw=path.read_bytes();prefix=(ROOT/prior['raw_path']).read_bytes()
        agrees=raw[:len(prefix)]==prefix
        receipt.update(raw_path=str(path.relative_to(ROOT)),raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),
            original_partial_prefix_agrees=agrees,partial=receipt['status']!='not_started')
        if receipt['status']=='not_started':receipt['status']='saved' if agrees and raw.startswith(b'%PDF') else 'preserved_content_version_conflict'
    except Exception as error:receipt.update(status='recovery_error',error=str(error))
    receipt['finished_at_utc']=collector.utc()
    with (ROOT/'REQUESTS.jsonl').open('a') as output:output.write(json.dumps(receipt)+'\n')
    (ROOT/'EARLY_PDF_RECOVERY.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
