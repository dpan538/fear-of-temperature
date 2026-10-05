"""Round 22 bounded public acquisition. No retries, credentials or DB access."""
import sys
sys.dont_write_bytecode = True
import contextlib, fcntl, hashlib, json, os, re, shutil, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urljoin, parse_qsl
from urllib.robotparser import RobotFileParser
import requests

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]
HEAVY = ROOT / 'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
SCOPE = OUT / 'control/SCOPE.json'
UA = 'FearTemperatureResearch/22 (AI-assisted noncommercial research; no model training)'
OBJECT_CAP = 2 * 1024 * 1024
def now(): return datetime.now(timezone.utc)
def read(p): return json.loads(Path(p).read_text())
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, x):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink(): raise RuntimeError('Symlink output refused')
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n'); os.replace(t, p)
def deadline():
    seconds = (datetime.fromisoformat(read(SCOPE)['network_deadline_utc']) - now()).total_seconds()
    if seconds <= 0: raise RuntimeError('Network deadline reached')
    return seconds
def retained(folder):
    p = OUT / folder
    total = 0
    for f in p.rglob('*') if p.exists() else []:
        if f.is_symlink(): raise RuntimeError('Evidence symlink refused')
        if f.is_file(): total += f.stat().st_size
    return total
def budget(add=0, lane='media'):
    s = read(SCOPE)
    # Full body copies in detailed inspection JSON also consume the text cap.
    media = s['accepted_media_prior_bytes'] + sum(retained(x) for x in ['media/raw','media/bodies','media/parsed','media/checks'])
    government = 22231574 + retained('government/raw')
    # Original reserves: remaining government cap, 100 MB originals, 64 MiB
    # structured outputs, and remaining original 1 GiB media reservation.
    reserves = max(0, s['government_lifetime_cap_bytes'] - government) + 100000000 + 67108864 + max(0, 1073741824-media)
    free = shutil.disk_usage(OUT).free
    used, cap = (media, s['media_lifetime_cap_bytes']) if lane == 'media' else (government, s['government_lifetime_cap_bytes'])
    if used + add > cap or free - add - reserves < s['minimum_free_floor_bytes']: raise RuntimeError('Storage cap/floor/original reserves prevent request')
    return dict(at_utc=now().isoformat(), free_bytes=free, reserve_bytes=reserves, projected_free_after_reserves=free-add-reserves, media_lifetime_bytes=media, government_lifetime_bytes=government, floor_bytes=s['minimum_free_floor_bytes'], lane=lane, prospective_bytes=add, passed=True)
@contextlib.contextmanager
def lock():
    with HEAVY.open('r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try: yield
        finally: fcntl.flock(f, fcntl.LOCK_UN)
def validate_url(url, hosts):
    u = urlsplit(url)
    if u.scheme != 'https' or u.hostname not in hosts or u.username or u.password: raise RuntimeError('Nonpublic/out-of-scope URL')
    if any(re.search('password|token|api.?key|auth', k, re.I) for k,v in parse_qsl(u.query)): raise RuntimeError('Credential parameter refused')
def robots_allowed(text, url):
    rp = RobotFileParser(); rp.parse(text.splitlines())
    return all(rp.can_fetch(agent,url) for agent in ['FearTemperatureResearch','ChatGPT-User','OAI-SearchBot','GPTBot'])
def robot_receipt(source,hostname):
    p=OUT/'media/policy'/f'{source}_{hostname}_robots.json'
    if p.exists():return p
    legacy=OUT/'media/policy'/f'{source}_robots.json'
    if legacy.exists() and urlsplit(read(legacy)['request_url']).hostname==hostname:return legacy
    raise RuntimeError('Host-specific robots observation required')
def challenge(data):
    from bs4 import BeautifulSoup
    s = BeautifulSoup(data, 'html.parser')
    title = s.title.get_text(' ',strip=True).lower() if s.title else ''
    return title in {'just a moment...', 'access denied', 'robot check', 'verify you are human'} or bool(s.find('script',src=re.compile('/cdn-cgi/challenge-platform|_Incapsula_Resource')) and not s.find('article'))
def preflight_receipt(policy):
    coordination=OUT/'control/COORDINATION.json'
    if not coordination.exists():coordination=OUT/'control/COORDINATION_READ_ONLY_RECEIPT.json'
    paths = [SCOPE, OUT/'PLAN.md', coordination, OUT/'control/CANDIDATES.json', policy]
    paths += sorted((OUT/'prototype').glob('*.py'))
    paths += sorted((OUT/'media/frames').glob('*.json')) if (OUT/'media/frames').exists() else []
    if (OUT/'government/TARGET_SEQUENCE.json').exists(): paths.append(OUT/'government/TARGET_SEQUENCE.json')
    result = dict(at_utc=now().isoformat(), inputs_and_code={str(p.relative_to(OUT)):digest(p) for p in paths}, budget=budget(), no_per_request_coordinator_release_required=True)
    save(OUT/'control/EXECUTION_PREFLIGHT.json', result)
    stamp=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:24]
    save(OUT/'control/preflights'/f'{stamp}.json',result)
    return result
def fetch(source, url, purpose, route, lane='media', cap=OBJECT_CAP, hosts=None, environment_variant='initial'):
    if (OUT/'control/NETWORK_CLOSED.json').exists():
        raise RuntimeError('Round network pass closed; preserved scope cannot be resumed')
    s = read(SCOPE); catalogue = read(OUT/'control/CANDIDATES.json')
    candidate = next((x for x in catalogue['candidates'] if x['source_id']==source), None)
    allowed = hosts or (candidate['hosts'] if candidate else ['publications.europa.eu'])
    validate_url(url, allowed)
    policy = read(OUT/'control/REQUEST_POLICY.json')
    pre = read(OUT/'control/EXECUTION_PREFLIGHT.json')
    for name, h in pre['inputs_and_code'].items():
        if digest(OUT/name) != h: raise RuntimeError('Preflight code/policy/input digest differs')
    cell = None
    if purpose == 'body':
        frames = [read(p) for p in (OUT/'media/frames').glob('*.json')]
        cells = [f for f in frames if f['source_id']==source and url in [a['url'] for a in f['selected']]]
        if len(cells)!=1: raise RuntimeError('Body not uniquely selected in frozen frame')
        cell = cells[0]
        frame_path = OUT / cell['receipt_path']
        if str(frame_path.relative_to(OUT)) not in pre['inputs_and_code']: raise RuntimeError('Frame digest not registered before body')
        if cell['month'] not in s['original_months'] or len(cell['selected'])>5: raise RuntimeError('Source/month quota outside design')
    if lane=='government':
        targets=read(OUT/'government/TARGET_SEQUENCE.json')['targets']
        if purpose!='selected_Item' or url not in [x['request_url'] for x in targets] or len(targets)!=11: raise RuntimeError('Government exact frozen target sequence required')
    rp = robot_receipt(source,urlsplit(url).hostname) if lane=='media' and purpose!='robots' else OUT/'media/policy'/f'{source}_robots.json'
    if lane=='media' and purpose!='robots':
        if not rp.exists(): raise RuntimeError('Robots observation required')
        r = read(rp)
        if r['status']=='robots_404': pass
        elif r['status']!='saved' or not robots_allowed((OUT/r['raw_path']).read_text(), url): raise RuntimeError('Robots route denied or unknown')
    with lock():
        deadline(); b = budget(cap, lane)
        reqdir=OUT/lane/'requests'; reqdir.mkdir(parents=True, exist_ok=True)
        previous=[read(p) for p in reqdir.glob('*.json')]
        same=[x for x in previous if x['source_id']==source and x['request_url']==url and x['purpose']==purpose]
        environment_repair=environment_variant=='network_enabled_after_dns_failure' and purpose!='body' and len(same)==1 and same[0]['http_status'] is None and 'NameResolutionError' in same[0].get('error','') and not same[0]['publisher_denial']
        if same and not environment_repair: raise RuntimeError('Initial attempt already recorded; retries disabled')
        if any(x['source_id']==source and x.get('publisher_denial') and not (x.get('http_status')==401 and '/wp-json/' in x['request_url'] and '/wp-json/' not in url) for x in previous): raise RuntimeError('Publisher denial persists')
        failed_family=[x for x in previous if x['source_id']==source and x['route']==route and x['status'] in {'failed','truncated','challenge','in_progress'} and not (x['http_status'] is None and 'NameResolutionError' in x.get('error',''))]
        if failed_family and not environment_repair: raise RuntimeError('Failed route family stopped')
        if lane=='media':
            meta=[x for x in previous if x['source_id']==source and x['purpose']!='body']
            if purpose!='body' and sum(max(1,len(x.get('hops',[]))) for x in meta)>=s['discovery_requests_per_candidate_cap']: raise RuntimeError('Candidate discovery cap')
            bodies=[x for x in previous if x['purpose']=='body']
            if purpose=='body' and len(bodies)>=s['article_target_cap']: raise RuntimeError('Global body cap')
            if purpose=='body' and sum(x['source_id']==source and x.get('publication_month')==cell['month'] for x in bodies)>=5: raise RuntimeError('Source/month body cap')
        else:
            ordered=read(OUT/'government/TARGET_SEQUENCE.json')['targets']
            if len(previous)>=11 or any(x['status']!='saved' for x in previous): raise RuntimeError('Government first failure stop or target cap')
            if url!=ordered[len(previous)]['request_url']: raise RuntimeError('Government frozen order violation')
        interval=2
        if lane=='media' and purpose!='robots' and rp.exists() and read(rp)['status']=='saved':
            delays=re.findall(r'^\s*Crawl-delay:\s*(\d+)\s*$',(OUT/read(rp)['raw_path']).read_text(),re.I|re.M)
            interval=max([2]+[int(x) for x in delays])
        finished=[x['finished_at_utc'] for x in previous if x['source_id']==source and x.get('finished_at_utc')]
        if finished:
            delay=interval-(now()-datetime.fromisoformat(max(finished))).total_seconds()
            if delay>0: time.sleep(delay)
        rid=hashlib.sha256(json.dumps([lane,source,url,purpose,environment_variant],separators=(',',':')).encode()).hexdigest()[:24]
        receipt=reqdir/f'{rid}.json'
        m=dict(request_id=rid, source_id=source, request_url=url, purpose=purpose, route=route, lane=lane, requested_at_utc=now().isoformat(), status='in_progress', http_status=None, byte_count=0, hops=[], budget_before=b, policy_sha256=digest(OUT/'control/REQUEST_POLICY.json'), code_sha256=digest(Path(__file__)), publisher_denial=False)
        m.update(environment_variant=environment_variant,supersedes_environment_failure_request_id=same[0]['request_id'] if environment_repair else None)
        if cell: m.update(publication_month=cell['month'], frame_path=cell['receipt_path'], frame_sha256=digest(OUT/cell['receipt_path']))
        save(receipt,m)
        path=OUT/lane/'raw'/f'{rid}.bin'; path.parent.mkdir(parents=True,exist_ok=True)
        part=path.with_suffix('.part'); response=None; current=url
        try:
            redirects=0 if lane=='government' else policy['max_redirects']
            for hop in range(redirects+1):
                if lane=='media' and purpose!='body' and sum(max(1,len(x.get('hops',[]))) for x in meta)+hop>=s['discovery_requests_per_candidate_cap']: raise RuntimeError('Discovery cap includes redirect hops')
                remaining=deadline()
                response=requests.get(current,headers={'User-Agent':UA,'Accept':'*/*','Accept-Encoding':'identity'},stream=True,allow_redirects=False,timeout=(min(10,remaining),min(15,remaining)))
                m.update(http_status=response.status_code,publisher_denial=response.status_code in {401,403,429,451})
                m['hops'].append(dict(url=current, status=response.status_code, location=response.headers.get('Location')))
                if response.status_code not in {301,302,303,307,308}: break
                if hop==redirects: raise RuntimeError('Redirect bound reached')
                nexturl=urljoin(current,response.headers.get('Location','')); validate_url(nexturl,allowed)
                if lane=='media' and purpose!='robots' and rp.exists() and read(rp)['status']=='saved' and not robots_allowed((OUT/read(rp)['raw_path']).read_text(),nexturl): raise RuntimeError('Redirect robots denied')
                response.close(); response=None; time.sleep(2); current=nexturl
            m.update(http_status=response.status_code, final_url=current, mime_type=response.headers.get('Content-Type'), response_headers={k:v for k,v in response.headers.items() if k.lower() in {'content-type','content-length','content-encoding','date','retry-after','etag','last-modified'}}, publisher_denial=response.status_code in {401,403,429,451}, denial_scope='authenticated_API_family' if response.status_code==401 and '/wp-json/' in url else 'publisher_or_exact_access_route')
            retry=response.headers.get('Retry-After')
            if retry: m['retry_after']=retry; m['publisher_denial']=True
            with part.open('xb') as f:
                for chunk in response.iter_content(65536):
                    deadline(); n=min(len(chunk),cap-m['byte_count'])
                    if n: budget(n,lane); f.write(chunk[:n]); m['byte_count']+=n
                    if n < len(chunk): m['status']='truncated'; raise RuntimeError('Object cap reached; partial retained')
            os.replace(part,path); m.update(raw_path=str(path.relative_to(OUT)),sha256=digest(path))
            if response.status_code==404 and purpose=='robots': m['status']='robots_404'
            elif response.status_code!=200 or retry: raise RuntimeError(f'HTTP {response.status_code}; route stopped')
            else:
                cl=response.headers.get('Content-Length'); encoding=response.headers.get('Content-Encoding','identity')
                if encoding in {'','identity'} and cl and cl.isdigit() and int(cl)!=m['byte_count']: raise RuntimeError('Incomplete Content-Length')
                if not m['byte_count']: raise RuntimeError('Empty payload')
                if lane=='government' and ((m['mime_type'] or '').split(';')[0].lower().strip() not in {'application/pdf','application/octet-stream'} or not path.read_bytes().startswith(b'%PDF-')): raise RuntimeError('PDF MIME/signature check failed')
                m['status']='saved'
                if 'html' in (m['mime_type'] or '') and challenge(path.read_bytes()): m['status']='challenge'; m['publisher_denial']=True
        except Exception as e:
            if m['status']!='truncated': m['status']='failed'
            m['error']=type(e).__name__+': '+str(e)
            m['failure_dimension']='publisher_restriction' if m['publisher_denial'] else 'transport_or_path_failure_not_proven_publisher_denial'
            if part.exists(): m.update(partial_path=str(part.relative_to(OUT)),partial_sha256=digest(part),byte_count=part.stat().st_size)
        finally:
            if response is not None: response.close()
            m['finished_at_utc']=now().isoformat(); save(receipt,m)
        if purpose=='robots':
            save(rp,m);save(OUT/'media/policy'/f'{source}_{urlsplit(url).hostname}_robots.json',m)
        print(json.dumps({k:m.get(k) for k in ['source_id','purpose','route','http_status','status','byte_count','error']},ensure_ascii=False),flush=True)
        return m
