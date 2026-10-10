"""Bounded, named saved public source metadata; no raw tree or store scan."""
import fcntl
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PIN=OUT/'worker/pinned'

def main():
    with (ROOT/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        registry=json.loads((PIN/'s4_source_registry.json').read_text())
        rows=[]; total=0
        for source in registry:
            if source['source_id'] not in ['mastodon_ie','mastodon_uk','mastodon_au','mastodon_us','aussie_zone','lemmy_nz']:continue
            for o in source.get('observations',[]):
                url=o.get('url','') or ''
                if not (url.endswith('/api/v2/instance') or url.endswith('/extended_description') or '_native_site_metadata' in o.get('probe','')):continue
                path=ROOT/o['raw_reference']
                raw=path.read_bytes();total+=len(raw)
                assert total<2*1024*1024
                body=gzip.decompress(raw)
                assert len(body)<1024*1024
                data=json.loads(body)
                if 'site_view' in data:
                    site=data['site_view']['site']
                    projection={'site':{k:site.get(k) for k in ['name','description','sidebar','actor_id','published','updated']},
                                'version':data.get('version'),
                                'local_site':{k:data['site_view'].get('local_site',{}).get(k) for k in ['federation_enabled','private_instance']}}
                else:
                    projection={k:data.get(k) for k in ['domain','title','description','version','source_url','content'] if k in data}
                url=url or source['base_url']+'/api/v3/site'
                expected=o.get('raw_sha256')
                actual=hashlib.sha256(body).hexdigest()
                assert not expected or expected in [actual,hashlib.sha256(raw).hexdigest()]
                rows.append({'source_id':source['source_id'],'primary_url':url,'source_observed_at_utc':o.get('retrieved_at'),
                             'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'raw_locator':o['raw_reference'],
                             'saved_compressed_bytes':len(raw),'saved_file_sha256':hashlib.sha256(raw).hexdigest(),
                             'payload_sha256':actual,'expected_hash_verified':bool(expected),
                             'projection':projection,'projection_scope':'source metadata only; administrator/account lists omitted'})
        target=OUT/'worker/NAMED_PRIMARY_PARENT_EVIDENCE.json'
        with target.open('x') as f:f.write(json.dumps({'named_reads':len(rows),'compressed_input_bytes':total,'rows':rows},indent=2)+'\n')
        print(json.dumps({'named_reads':len(rows),'compressed_input_bytes':total,'rows':rows},indent=2))

if __name__=='__main__':main()
