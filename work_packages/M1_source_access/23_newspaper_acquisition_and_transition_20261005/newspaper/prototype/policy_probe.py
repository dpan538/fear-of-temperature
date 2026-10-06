"""One compact public robots request/host. Source preparation only; no body/index.

This bootstrap records policy text and stops; it cannot clear a corpus route.
Tool-inaccessible robots are distinguished from explicit HTTP/access denials.
"""
import argparse,datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import requests,shutil,time
from urllib.parse import urlsplit
from transport import OWN, HEAVY_LOCK, deadline_check, read_state, save_state, utc, UA,SCOPE,corpus_bytes

HOSTS=[('stanford_daily','https://archives.stanforddaily.com/robots.txt'),
       ('the_press','https://paperspast.natlib.govt.nz/robots.txt'),
       ('deseret_news','https://www.deseret.com/robots.txt'),
       ('alice_springs_news','https://www.alicespringsnews.com.au/robots.txt'),
       ('beaver','https://digital.library.lse.ac.uk/robots.txt'),
       ('mit_tech','https://thetech.com/robots.txt')]

def main(selected=None):
    directory=OWN/'policies';directory.mkdir(exist_ok=True)
    ledger=OWN/'sources/POLICY_REQUESTS.jsonl';ledger.parent.mkdir(exist_ok=True)
    with HEAVY_LOCK.open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        state=read_state()
        for source,url in HOSTS:
            if selected is not None and source!=selected:continue
            target=directory/(source+'_robots.txt')
            if target.exists(): continue
            deadline_check()
            entry=state['titles'].setdefault(source,{'metadata':0,'search':0,'body':0})
            if entry['metadata']>=32: raise RuntimeError('Metadata cap')
            if entry.get('access_stop') or time.time()<entry.get('cooldown_until',0):raise RuntimeError('Prior access stop/cooldown remains active')
            if shutil.disk_usage(OWN).free-131072<SCOPE['minimum_free_floor_bytes']:raise RuntimeError('Compact preparation physical floor stop')
            if SCOPE['accepted_media_prior_bytes']+corpus_bytes()+131072>=SCOPE['media_lifetime_cap_bytes']:raise RuntimeError('Compact preparation lifetime cap stop')
            host=urlsplit(url).hostname
            wait=2-(time.time()-state['hosts'].get(host,0))
            if wait>0:time.sleep(wait)
            entry['metadata']+=1;save_state(state)
            state['hosts'][host]=time.time();save_state(state)
            receipt={'source_id':source,'request_url':url,'purpose':'robots_policy',
                     'requested_at_utc':utc(),'user_agent':UA,'cap_bytes':131072,
                     'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     'corpus_payload':False,'redirects_followed':False,'retry':False}
            try:
                s=requests.Session();s.trust_env=False
                with s.get(url,headers={'User-Agent':UA},stream=True,allow_redirects=False,timeout=(10,15)) as response:
                    receipt.update(http_status=response.status_code,location=response.headers.get('Location'),
                                   content_type=response.headers.get('Content-Type'))
                    data=b''
                    for chunk in response.iter_content(16384):
                        deadline_check()
                        if len(data)+len(chunk)>131072:
                            data+=chunk[:131072-len(data)];receipt['partial']=True;break
                        data+=chunk
                    target.write_bytes(data)
                    receipt.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                                   local_path=str(target.relative_to(OWN)),
                                   status='saved_policy' if response.status_code==200 else 'http_stop')
                    if response.status_code in {401,403,429}:
                        entry['access_stop']={'url':url,'http_status':response.status_code,'purpose':'policy'}
                        save_state(state)
            except Exception as exc:
                receipt.update(status='transport_failure',error=type(exc).__name__+': '+str(exc))
            receipt['finished_at_utc']=utc()
            with ledger.open('a') as out:out.write(json.dumps(receipt)+'\n')
            print(json.dumps({k:v for k,v in receipt.items() if k not in {'user_agent','code_sha256'}}),flush=True)

if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('--source',choices=[x[0] for x in HOSTS]);main(args.parse_args().source)
