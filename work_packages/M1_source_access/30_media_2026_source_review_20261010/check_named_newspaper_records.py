"""Check twelve named records in at most ten saved native JSON batches."""
import csv
import fcntl
import gzip
import hashlib
import html
import json
import re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PIN=OUT/'worker/pinned'

def main():
    with (ROOT/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (PIN/'np9_2026_metadata.csv').open(newline='') as f:records=list(csv.DictReader(f))
        wanted=set(['northern_rivers_times:post:42243','northern_rivers_times:post:42412',
                    'northern_rivers_times:post:43810','northern_rivers_times:post:43819',
                    'northern_rivers_times:post:44220','northern_rivers_times:post:44221'])
        for source in ['devonport_flagstaff','northern_rivers_times']:
            r=sorted([r for r in records if r['source_id']==source],key=lambda r:(r['publication_date'],r['article_id']))
            wanted.update([r[0]['article_id'],r[-1]['article_id']])
            if source=='northern_rivers_times':
                r=[r for r in r if r['publication_date'].startswith('2026-07')];wanted.update([r[0]['article_id'],r[-1]['article_id']])
        selected=[r for r in records if r['article_id'] in wanted]
        payloads={};rows=[];total=0;raw_manifest=[]
        for r in selected:
            path=ROOT/r['raw_reference']
            if path not in payloads:
                raw=path.read_bytes();total+=len(raw)
                assert total<8*1024*1024
                body=gzip.decompress(raw) if path.suffix=='.gz' else raw
                assert len(body)<16*1024*1024
                data=json.loads(body)
                if isinstance(data,dict) and 'data' in data:data=data['data']
                if isinstance(data,dict):data=[data]
                payloads[path]={str(p.get('id')):p for p in data if isinstance(p,dict)}
                raw_manifest.append({'path':r['raw_reference'],'bytes':len(raw),'file_sha256':hashlib.sha256(raw).hexdigest(),
                                     'payload_sha256':hashlib.sha256(body).hexdigest(),'selected_native_ids_only':True})
            native_id=r['article_id'].rsplit(':',1)[-1]
            post=payloads[path].get(native_id)
            assert post is not None,r['article_id']
            content=post.get('content',{}).get('rendered','')
            text=html.unescape(re.sub('<[^>]+>',' ',content))
            text=' '.join(text.split())
            rows.append({'article_id':r['article_id'],'source_id':r['source_id'],'native_id':native_id,
                         'export_publication_date':r['publication_date'],'native_date':post.get('date'),
                         'native_date_gmt':post.get('date_gmt'),'native_modified':post.get('modified'),
                         'native_link':post.get('link'),'export_source_url':r['source_url'],
                         'id_date_link_mapping_matches':post.get('date','')[:10]==r['publication_date'] and post.get('link')==r['source_url'],
                         'content_rendered_sha256':hashlib.sha256(content.encode()).hexdigest(),
                         'plain_rendered_whitespace_sha256':hashlib.sha256(text.encode()).hexdigest(),
                         'rendered_characters':len(content),'plain_rendered_characters':len(text),
                         'native_title':html.unescape(post.get('title',{}).get('rendered','')),
                         'raw_locator':r['raw_reference'],'checked_at_utc':datetime.now(timezone.utc).isoformat(),
                         'content_scope':'saved native content inspected structurally; no historical-version equivalence or claim truth audit',
                         'semantic_labels_used':False})
        result={'records_checked':len(rows),'saved_batches_read':len(payloads),'compressed_input_bytes':total,
                'selection':'source endpoints; July Northern Rivers endpoints; three exact-body-hash candidate pairs',
                'not_random_or_prevalence_sample':True,'raw_input_manifest':raw_manifest,'rows':rows}
        with (OUT/'worker/NAMED_NEWSPAPER_RECORD_CHECKS.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))

if __name__=='__main__':main()
