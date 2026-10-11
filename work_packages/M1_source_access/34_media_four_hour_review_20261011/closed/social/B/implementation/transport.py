"""Anonymous, policy-gated native social ELT. No other corpus store is opened.

Transport attempts are charged before dispatch and never silently retried. Raw
responses are losslessly compressed, separately hashed and immediately Loaded.
Runtime controls/receipts/raw/SQLite are local; summaries omit full text.
"""
import argparse
import contextlib
import datetime as dt
import fcntl
import gzip
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request

WORK = Path(__file__).resolve().parent
ROOT = Path('/Users/jarlgiovanni/Desktop/fear_of_temperature/work_packages/M1_source_access/27_newspaper_context_recovery_20261008/social_public_api')
REPO = Path('/Users/jarlgiovanni/Desktop/fear_of_temperature')
OWNER = '01a1237a-7cb0-7783-97fc-9173cb66e84b'
TERMINAL_OPERATION = False
SEGMENT_A = WORK.parent
SCOPE_PATH = SEGMENT_A.parent / 'control/EXECUTION_SCOPE.json'
DB = ROOT / 'worker/social_elt.sqlite3'
SCHEMA = WORK / 'schema_legacy.sql'

def sha(b): return hashlib.sha256(b).hexdigest()
def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def read_json(p, default=None):
    p=Path(p)
    if not p.exists() and p.parent==WORK and p.name in ('source_registry.json','SOURCE_ACCESS_CONSTRAINTS.json'):
        p=SEGMENT_A/p.name
    return json.loads(p.read_text()) if p.exists() else default
def atomic(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    b = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode()
    q = p.with_name(p.name + '.pending')
    with q.open('wb') as f: f.write(b); f.flush(); os.fsync(f.fileno())
    q.replace(p)
def append(p, obj):
    with p.open('a', encoding='utf8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n'); f.flush(); os.fsync(f.fileno())
def bytes_under(p):
    # Each preflight still performs a complete live scan. DirEntry supplies
    # type information and one fresh stat without redundant pathlib calls.
    total = 0
    stack = [p]
    while stack:
        directory = stack.pop()
        try:
            entries = os.scandir(directory)
        except OSError:
            # Match os.walk's default handling of unreadable directories.
            continue
        with entries:
          for entry in entries:
            try:
                if entry.is_symlink(): continue
                if entry.is_dir(follow_symlinks=False): stack.append(entry.path)
                else: total += entry.stat(follow_symlinks=False).st_size
            except FileNotFoundError:
                pass
    return total

class Stop(RuntimeError): pass

def release(inflight_at=None):
    scope=read_json(SCOPE_PATH)
    rel=read_json(SCOPE_PATH.parent/'OWNER_RELEASE.json', {})
    if scope.get('owner_thread_id')!=OWNER or rel.get('owner_thread_id')!=OWNER:
        raise Stop('owner_binding_pending_or_mismatch')
    if rel.get('status') not in ('RELEASED','CONDITIONALLY_RELEASED') or not rel.get('network_and_durable_load_released'):
        raise Stop('release_missing')
    if rel.get('scope_sha256')!=sha(SCOPE_PATH.read_bytes()): raise Stop('scope_digest_mismatch')
    if scope['hard_deadline_at_utc']!=rel['hard_deadline_at_utc']: raise Stop('deadline_binding_mismatch')
    start=dt.datetime.fromisoformat(scope['earliest_network_and_load_start_at_utc'])
    if dt.datetime.now(dt.timezone.utc)<start: raise Stop('release_start_not_yet_live')
    if dt.datetime.now(dt.timezone.utc)>=dt.datetime.fromisoformat(rel['hard_deadline_at_utc']):
        if not inflight_at or not start<=dt.datetime.fromisoformat(inflight_at)<dt.datetime.fromisoformat(rel['hard_deadline_at_utc']):
            raise Stop('fixed_deadline')
    return scope

@contextlib.contextmanager
def shared(pending=0,inflight_at=None):
    scope=release(inflight_at=inflight_at)
    with (REPO/scope['shared_heavy_io_lock']).open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        scope=release(inflight_at=inflight_at)
        budget=preflight(scope,pending)
        atomic(WORK/'LAST_CAPACITY.json',budget)
        yield budget

@contextlib.contextmanager
def writer():
    WORK.mkdir(parents=True,exist_ok=True)
    with (ROOT/'worker/SOCIAL_OWNER_MUTEX.lock').open('a+b') as f:
        try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise Stop('social_writer_already_active')
        yield

PENDING_CANDIDATE_VERSIONS = 0

def acquisition_tail(scope):
    if TERMINAL_OPERATION:return {'bytes':0,'phase':'terminal_incremental_operation_consumes_reserved_tail'}
    model=read_json(WORK/'ACQUISITION_TAIL_ACCOUNTING.json',{})
    if not model.get('enabled'):return {'bytes':0,'phase':'no_model_yet'}
    st=state();nv=st.get('new_entity_versions',0);ne=st.get('new_entities',0)
    candidates=PENDING_CANDIDATE_VERSIONS
    unannotated=max(0,nv-model.get('already_annotated_changed_versions',0))+candidates
    metadata=unannotated*model['metadata_bytes_per_changed_version_upper_estimate']
    baseline=read_json(WORK/'INHERITED_BASELINE.json',{})
    request_delta=max(0,st.get('requests',0)-baseline.get('lifetime_charged_requests',st.get('requests',0)))
    exports=(nv+candidates)*(model['export_upper_bytes_per_version']+model.get('future_publication_bytes_per_version',0))+(ne+candidates)*(model['export_upper_bytes_per_entity']+model.get('future_publication_bytes_per_entity',0))+model['delta_export_fixed_allowance_bytes']+request_delta*model.get('future_delta_receipt_bytes_per_request',0)
    journal=model['bounded_metadata_journal_bytes']
    extra=model.get('accepted_phase_A_future_publication_upper_bytes',0)
    return {'bytes':metadata+exports+journal+extra,'accepted_phase_A_future_publication_upper_bytes':extra,'unannotated_changed_versions':unannotated,'metadata_bytes':metadata,'incremental_export_bytes':exports,'bounded_metadata_journal_bytes':journal,'materialized_predecessor_export_tail_bytes':0,'basis':'measured conservative per-version/entity delta output and native metadata; completed predecessor exports remain charged in actual bytes only'}

def disjoint_roots(paths):
    roots=[]
    for path in sorted({Path(p).resolve() for p in paths},key=lambda p:len(p.parts)):
        if not any(path==root or root in path.parents for root in roots):roots.append(path)
    return roots

def accounting_totals(scope):
    media_roots=disjoint_roots([REPO/p for p in scope['media_lifetime_accounting_roots']])
    social_roots=disjoint_roots([ROOT]+[REPO/p for p in scope.get('social_additional_accounting_roots',[])])
    media_measure=[{'path':str(p),'bytes':bytes_under(p)} for p in media_roots]
    social_measure=[{'path':str(p),'bytes':bytes_under(p)} for p in social_roots]
    return {'media_bytes':scope['prior_media_bytes']+sum(x['bytes'] for x in media_measure),'social_bytes':sum(x['bytes'] for x in social_measure),'media_accounting_roots':media_measure,'social_accounting_roots':social_measure,'social_additional_accounting_bytes':sum(x['bytes'] for x in social_measure if Path(x['path'])!=ROOT.resolve()),'exact_once_canonical_disjoint_roots':True}

def preflight(scope, pending):
    leases=read_json(REPO/scope['lease_coordination_reference'])['active_leases']
    leases=[x for x in leases if x.get('active',False)]
    own=sum(x['reserved_bytes'] for x in leases if x['thread_id']==OWNER)
    other=sum(x['reserved_bytes'] for x in leases if x['thread_id']!=OWNER)
    if own<scope['owner_pending_lease_bytes']: raise Stop('active_social_lease_missing')
    tail=acquisition_tail(scope)
    complete_pending=pending+tail['bytes']
    reserved=other+max(own,complete_pending)+65536
    accounting=accounting_totals(scope)
    used=accounting['media_bytes'];social=accounting['social_bytes']
    free=shutil.disk_usage(WORK).free
    b=dict(at_utc=utc(),free_bytes=free,media_bytes=used,social_bytes=social,
           own_lease_bytes=own,other_lease_bytes=other,pending_bytes=pending,terminal_tail=tail,complete_pending_bytes=complete_pending,reserved_bytes=reserved,
           physical_headroom=free-scope['physical_floor_bytes']-scope['recovery_allowance_bytes']-reserved,
           media_headroom=scope['media_lifetime_cap_bytes']-used-reserved,
           social_headroom=scope['social_incremental_allocation_bytes']-social-max(own,complete_pending)-65536)
    b.update({k:v for k,v in accounting.items() if k not in ('media_bytes','social_bytes')})
    if min(b['physical_headroom'],b['media_headroom'],b['social_headroom'])<0:
        raise Stop('resource_stop '+json.dumps(b))
    return b

_state_cache = {}
_persisted_keys = {}
_inherited_attempts = {}
def hydrate_state(path, seen=None):
    """Restore reference chains and only their metadata/key journals; no body copy."""
    seen=set() if seen is None else seen
    path=Path(path).resolve()
    if path in seen: raise Stop('inherited_state_reference_cycle')
    seen.add(path)
    own=read_json(path,{})
    ref=own.get('inherited_state_reference')
    prior=hydrate_state(REPO/ref,seen) if ref else {}
    result=dict(prior);result.update(own)
    attempts=dict(prior.get('attempts',{}));attempts.update(own.get('attempts',{}));result['attempts']=attempts
    keys=set(prior.get('returned_object_ids',[]));keys.update(own.get('returned_object_ids',[]))
    journal=path.parent/'RETURNED_KEYS.jsonl'
    if journal.exists():
        with journal.open() as f:
            for line in f: keys.update(json.loads(line)['keys'])
    result['returned_object_ids']=sorted(keys)
    result['object_ids']=own.get('object_ids',prior.get('object_ids',[]))
    if own.get('returned_object_count') is not None and len(keys)!=own['returned_object_count']:
        raise Stop('inherited_returned_key_counter_mismatch '+str(path))
    return result

def state():
    cachekey=str(WORK)
    if cachekey in _state_cache: return _state_cache[cachekey]
    own=read_json(WORK/'STATE.json',dict(requests=0,hosts={},attempts={},blocked_hosts={},object_ids=[],returned_object_ids=[],backoff_methods={}))
    if own.get('inherited_state_reference'):
        baseline=hydrate_state(REPO/own['inherited_state_reference'])
        result=hydrate_state(WORK/'STATE.json')
        _persisted_keys[cachekey]=set(result['returned_object_ids']);_inherited_attempts[cachekey]=baseline['attempts']
    else:result=own
    _state_cache[cachekey]=result
    return result

def inherited_receipt(key):
    own=read_json(WORK/'STATE.json',{})
    paths=[WORK,ROOT/'worker']
    pred=release().get('predecessor_worker_reference')
    if pred:paths.append(REPO/pred)
    ref=own.get('inherited_state_reference');seen=set()
    while ref and ref not in seen:
        seen.add(ref);p=REPO/ref;paths.append(p.parent);ref=read_json(p,{}).get('inherited_state_reference')
    for parent in paths:
        rec=read_json(parent/'receipts'/f'{key}.json',{})
        if rec:return rec
    return {}

def persist_state(st):
    cachekey=str(WORK)
    if not st.get('inherited_state_reference'):
        atomic(WORK/'STATE.json',st); _state_cache[cachekey]=st; return
    keys=set(st['returned_object_ids']); delta=keys-_persisted_keys[cachekey]
    if delta: append(WORK/'RETURNED_KEYS.jsonl',dict(at_utc=utc(),keys=sorted(delta)))
    _persisted_keys[cachekey]=keys
    compact={k:v for k,v in st.items() if k not in ('object_ids','returned_object_ids','attempts')}
    compact['attempts']={k:v for k,v in st['attempts'].items() if _inherited_attempts[cachekey].get(k)!=v}
    compact['returned_object_count']=len(keys)
    atomic(WORK/'STATE.json',compact); _state_cache[cachekey]=st

def below_optional_limit(value,limit): return limit is None or value<limit
def within_optional_limit(value,limit): return limit is None or value<=limit

def footprint(raw_cap=0,body_bytes=0,record_count=0):
    # Body-byte amplification alone missed random B-tree pages in large native
    # batches. Three observed mbox journals reached 39-44 KiB per returned row.
    # Reserve 64 KiB per row (>=1.5x that range), body/growth amplification and
    # a 32 MiB fixed index/receipt margin. Already saved raw/exports stay in
    # actual retained bytes; no whole database or feed copy is included.
    return raw_cap*3+body_bytes*12+record_count*65536+32*1048576

def provider_method_key(host,path):
    if host!='api.stackexchange.com':return host+'|'+path
    # Provider backoff is shared by method across IDs and community tokens.
    path=urllib.parse.unquote(path)
    path=re.sub(r'^/2\.[0-9]+(?=/)', '', path)
    path=re.sub(r'/[0-9]+(?:;[0-9]+)*(?=/|$)', '/{ids}', path)
    if path=='/me' or path.startswith('/me/'):path='/users/{ids}'+path[3:]
    return host+'|'+path

def provider_backoff_until(st,host,path):
    key=provider_method_key(host,path)
    values=[]
    for old,until in st.get('backoff_methods',{}).items():
        oldhost,separator,oldpath=old.partition('|')
        if separator and provider_method_key(oldhost,oldpath)==key:values.append(until)
    return max(values,default=0)

def fetch(url, source_id, purpose='policy', cap=None, recovery_evidence=None):
    scope=release(); cap=cap or scope['default_raw_object_cap_bytes']
    if not url.startswith('https://'): raise Stop('https_required')
    key=sha((source_id+'|'+purpose+'|'+url+('|' + recovery_evidence if recovery_evidence else '')).encode())[:24]
    st=state()
    if key in st['attempts']:
        rec=inherited_receipt(key)
        if rec.get('status')=='saved': return rec
        # An owner's evidenced technical interruption is distinct from a source
        # prohibition/timeout. Exactly one charged, digest-bound recovery path;
        # the original attempt/raw remain and provider stops are still checked.
        ref=rec.get('owner_runtime_correction_reference')
        if rec.get('status')=='interrupted_transport_stop' and ref and rec.get('owner_thread_id')==OWNER and recovery_evidence is None:
            proof=WORK/ref
            if proof.exists() and sha(proof.read_bytes())==rec.get('owner_runtime_correction_sha256'):
                return fetch(url,source_id,purpose,cap,recovery_evidence='owner_runtime_correction:'+rec['owner_runtime_correction_sha256'])
        raise Stop('preserved_attempt_stop '+key)
    host=urllib.parse.urlsplit(url).hostname
    if host in st['blocked_hosts']:
        allowed=False
        if host=='api.stackexchange.com':
            import quota_observation
            allowed=(quota_observation.observation_allowed(url,source_id,purpose,st) if purpose=='quota_observation' else quota_observation.native_access_confirmed(st))
        if not allowed:raise Stop('preserved_host_stop '+host)
    path=urllib.parse.urlsplit(url).path
    method=provider_method_key(host,path)
    until=provider_backoff_until(st,host,path)
    if time.time()<until: raise Stop('server_backoff_until '+str(until))
    if purpose=='content':
        registry=read_json(WORK/'source_registry.json',[])
        source=next((x for x in registry if x['source_id']==source_id),{})
        if source.get('collection_retention')!='permitted': raise Stop('source_rights_not_cleared')
        if not source.get('api_documentation'): raise Stop('documented_api_required')
    constraints=read_json(WORK/'SOURCE_ACCESS_CONSTRAINTS.json',{}).get(host,{})
    source_until=st['hosts'].get(host,0)+constraints.get('minimum_spacing_seconds',0)
    if time.time()<source_until:raise Stop('server_backoff_until '+str(source_until))
    delay=scope['minimum_host_spacing_seconds']-(time.time()-st['hosts'].get(host,0))
    if delay>0: time.sleep(delay)
    rec=dict(request_id=key,source_id=source_id,purpose=purpose,url=url,started_at=utc(),status='in_progress',recovery_evidence=recovery_evidence)
    with shared(footprint(cap)) as budget:
        st=state()
        if not below_optional_limit(st['requests'],scope['max_http_requests_including_access_and_policy_probes']):
            raise Stop('request_ceiling')
        st['requests']+=1; st['hosts'][host]=time.time(); st['attempts'][key]='in_progress'
        persist_state(st); atomic(WORK/'receipts'/f'{key}.json',rec)
        rec['preflight']=budget
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args): return None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        req=urllib.request.Request(url,headers={'User-Agent':'FearOfTemperatureResearch/1.0 (bounded anonymous public-source research)','Accept':'application/json,text/html;q=0.9','Accept-Encoding':'identity'})
        remaining=(dt.datetime.fromisoformat(scope['hard_deadline_at_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
        old_handler=signal.getsignal(signal.SIGALRM)
        def request_deadline(signum,frame): raise TimeoutError('total_native_request_duration_bound')
        try:
            release()  # Recheck immediately before HTTP; charged attempt remains.
            if remaining<=0: raise Stop('fixed_deadline_before_dispatch')
            signal.signal(signal.SIGALRM,request_deadline);signal.setitimer(signal.ITIMER_REAL,min(25,remaining))
            with opener.open(req,timeout=max(.1,min(25,remaining))) as response:
                rec['http_status']=response.status
                rec['headers']={k:response.headers.get(k) for k in ('Content-Type','Content-Encoding','Content-Length','Last-Modified','Retry-After','Location')}
                b=response.read(cap+1)
                signal.setitimer(signal.ITIMER_REAL,0)
                if len(b)>cap: raise Stop('raw_object_cap_stop')
                if host=='api.stackexchange.com' and 'json' in (rec['headers']['Content-Type'] or ''):
                    decoded=gzip.decompress(b) if b.startswith(b'\x1f\x8b') else b
                    obj=json.loads(decoded)
                    rec['api_quota_remaining']=obj.get('quota_remaining')
                    rec['api_backoff']=obj.get('backoff')
                    rec['api_method_key']=method
                    if obj.get('backoff'): st.setdefault('backoff_methods',{})[method]=time.time()+obj['backoff']
                    if obj.get('error_id'): rec['api_error']={k:obj.get(k) for k in ('error_id','error_name','error_message')}
                    if obj.get('quota_remaining')==0: st['blocked_hosts'][host]={'reason':'quota_exhausted'}
                    import quota_observation
                    quota_observation.record_provider_state(st,rec)
                packed=gzip.compress(b,mtime=0)
                p=WORK/'raw'/f'{key}.bin.gz'; p.parent.mkdir(exist_ok=True)
                with p.open('wb') as f: f.write(packed); f.flush(); os.fsync(f.fileno())
                rec.update(status='saved',retrieved_at=utc(),raw_bytes=len(b),stored_bytes=len(packed),raw_sha256=sha(b),stored_sha256=sha(packed),raw_encoding='gzip',raw_reference=str(p.relative_to(REPO)))
        except urllib.error.HTTPError as e:
            rec.update(status='http_stop',http_status=e.code,location=e.headers.get('Location'),retry_after=e.headers.get('Retry-After'))
            if e.code in (401,403,429,451) or rec['retry_after']: st['blocked_hosts'][host]=rec
        except Exception as e:
            rec.update(status='transport_stop',error=type(e).__name__+': '+str(e))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
        st['attempts'][key]=rec['status']
        if rec['status']=='saved':
            if not st.get('first_successful_http_at_utc'):st['first_successful_http_at_utc']=rec['retrieved_at']
            st['last_successful_http_at_utc']=rec['retrieved_at']
        persist_state(st)
        atomic(WORK/'receipts'/f'{key}.json',rec); append(WORK/'REQUESTS.jsonl',rec)
    return rec

def payload(rec):
    if rec['status']!='saved': raise Stop(rec['status'])
    b=gzip.decompress((REPO/rec['raw_reference']).read_bytes())
    if sha(b)!=rec['raw_sha256']: raise Stop('raw_digest_mismatch')
    return b

def json_payload(rec):
    b=payload(rec)
    if b.startswith(b'\x1f\x8b'):
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(b)) as f: b=f.read(16*1048576+1)
    if len(b)>16*1048576: raise Stop('decompressed_payload_operation_bound')
    return json.loads(b)

class Plain(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag in ('p','div','br','li','pre','blockquote','tr'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('p','div','li','pre','blockquote','tr'): self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)
def clean(body):
    p=Plain(); p.feed(body)
    return '\n'.join(x.strip() for x in html.unescape(''.join(p.parts)).splitlines() if x.strip())

def connect(path=DB):
    c=sqlite3.connect(path); c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=DELETE')
    sql=c.execute("SELECT sql FROM sqlite_master WHERE name='posts'").fetchone()
    if sql and 'UNIQUE(source_id,native_post_id)' in sql[0]:
        # Single local new-stream migration. Keep every persistent ID/version.
        c.execute('PRAGMA foreign_keys=OFF')
        with c:
            new=SCHEMA.read_text().split(';',1)[0].replace('IF NOT EXISTS posts','posts_new')
            c.execute(new); c.execute('INSERT INTO posts_new SELECT * FROM posts')
            c.execute('DROP TABLE posts'); c.execute('ALTER TABLE posts_new RENAME TO posts')
        c.execute('PRAGMA foreign_keys=ON')
    c.executescript(SCHEMA.read_text())
    if 'question_thread_id' in {x[1] for x in c.execute('PRAGMA table_info(parent_context)')}:
        c.execute('ALTER TABLE parent_context RENAME COLUMN question_thread_id TO root_thread_id')
    with c:
        c.execute("INSERT OR IGNORE INTO native_identities SELECT source_id,CASE WHEN native_unit='comment' THEN 'comment' WHEN native_unit IN ('question','answer') THEN 'post' WHEN native_unit IN ('forum_post','forum_reply') THEN 'forum_post' WHEN source_id LIKE 'mastodon_%' THEN 'status' WHEN source_id='bluesky' THEN 'at_uri' ELSE native_unit END,native_post_id,persistent_post_id,'established_ID_preserved' FROM posts WHERE NOT EXISTS (SELECT 1 FROM native_identities i WHERE i.persistent_post_id=posts.persistent_post_id)")
        # Preserve earlier adapter aliases as explicit deprecated metadata.
        c.execute("UPDATE native_identities SET identity_basis='deprecated_adapter_alias_not_native_namespace' WHERE native_namespace NOT IN ('post','comment','forum_post','status','at_uri')")
        c.execute("INSERT OR IGNORE INTO parent_context SELECT persistent_post_id,NULL,reply_to_post_id,thread_id,context_status FROM posts")
    return c

def namespace(r):
    if r.get('native_namespace'): return r['native_namespace']
    return 'comment' if r['native_unit']=='comment' else 'post' if r['native_unit'] in ('question','answer') else 'forum_post' if r['native_unit'] in ('forum_post','forum_reply') else r['native_unit']

def native_key(r): return r['source_id']+'|'+namespace(r)+'|'+str(r['native_post_id'])

def prepare_record(r, identities=None):
    r=dict(r); identities=identities or {}
    r['persistent_post_id']=identities.get(native_key(r)) or 'social:'+r['source_id']+':'+namespace(r)+':'+str(r['native_post_id'])
    r['body_text']=r['body_original'].replace('\r\n','\n').strip() if r.get('body_format')=='plain' else clean(r['body_original'])
    r['body_sha256']=sha(r['body_original'].encode())
    r['body_version_id']=sha((r['persistent_post_id']+'|'+r['body_sha256']+'|'+str(r.get('native_edited_at'))+'|'+str(r.get('native_revision'))).encode())
    return r

def insert_rows(c, accepted, rec):
    new=0; versions=0
    with c:
        c.execute('INSERT OR IGNORE INTO responses VALUES (?,?,?,?,?,?,?,?)',(rec['request_id'],rec['url'],rec['retrieved_at'],rec['raw_reference'],rec['raw_sha256'],rec['stored_sha256'],rec['raw_bytes'],rec['stored_bytes']))
        for r in accepted:
            prior=c.execute('SELECT source_url,native_created_at,native_unit FROM posts WHERE persistent_post_id=?',(r['persistent_post_id'],)).fetchone()
            if prior and prior[1:]!=(r['native_created_at'],r['native_unit']):
                raise Stop('identity_date_unit_conflict '+r['persistent_post_id'])
            new+=c.execute('INSERT OR IGNORE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(r['persistent_post_id'],r['source_id'],str(r['native_post_id']),r['source_url'],r['native_unit'],str(r['thread_id']),r.get('reply_to_post_id'),r['native_created_at'],r.get('author_id'),r.get('author_role','unknown'),None,r.get('context_status','partial'))).rowcount
            c.execute('INSERT OR IGNORE INTO native_identities VALUES (?,?,?,?,?)',(r['source_id'],namespace(r),str(r['native_post_id']),r['persistent_post_id'],'native_namespace_typed_ID'))
            c.execute('INSERT OR IGNORE INTO post_urls VALUES (?,?,?,?)',(r['persistent_post_id'],r['source_url'],rec['request_id'],'alias' if prior and prior[0]!=r['source_url'] else 'canonical'))
            c.execute('INSERT OR REPLACE INTO parent_context VALUES (?,?,?,?,?)',(r['persistent_post_id'],r.get('parent_namespace'),r.get('reply_to_post_id'),r.get('question_thread_id') or (r.get('thread_id') if r.get('thread_id')!='unresolved' else None),r.get('context_status','partial')))
            versions+=c.execute('INSERT OR IGNORE INTO versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['body_version_id'],r['persistent_post_id'],r['body_sha256'],r['body_original'],r['body_text'],r.get('native_edited_at'),str(r.get('native_revision')) if r.get('native_revision') is not None else None,rec['retrieved_at'],r.get('content_license','unknown'),r.get('license_basis','unresolved'),r.get('completeness','native_body_returned'),r.get('provenance','direct_original'),json.dumps(r.get('native_fields',{}),ensure_ascii=False))).rowcount
            c.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?)',(r['body_version_id'],rec['request_id'],rec['retrieved_at']))
    return new,versions

def load(records, rec):
    """One version-preserving transaction; reject out-of-interval native dates."""
    scope=release(); registry=read_json(WORK/'source_registry.json',[])
    rights={x['source_id']:x for x in registry}
    accepted=[]; excluded=[]
    returned={native_key(r) for r in records}
    with shared(footprint()):
        c=connect()
        identities={a+'|'+b+'|'+d:p for a,b,d,p in c.execute('SELECT source_id,native_namespace,native_post_id,persistent_post_id FROM native_identities')}
        c.close()
    for r in records:
        native_date=r.get('native_created_at','')[:10]
        if not scope['publication_interval'][0]<=native_date<=scope['publication_interval'][1]:
            excluded.append({'native_post_id':r.get('native_post_id'),'reason':'outside_fixed_interval_or_missing_native_date'}); continue
        if rights[r['source_id']]['collection_retention']!='permitted': raise Stop('load_rights_not_cleared')
        if not r.get('source_url') or not r.get('body_original'): raise Stop('missing_identity_or_body')
        r=prepare_record(r,identities)
        if not r['body_text']: raise Stop('unreadable_body')
        accepted.append(r)
    with shared(footprint(0,sum(len(r['body_original'].encode()) for r in accepted))):
        st=state(); allids=set(st['object_ids'])|{r['persistent_post_id'] for r in accepted}
        # Earlier state used persistent IDs. Derive typed keys from established
        # native identity metadata; never reset cumulative counters or IDs.
        old_returned=set(st.get('returned_object_ids',[]))
        reverse={v:k for k,v in identities.items()}
        returned_all={reverse.get(x,x) for x in old_returned}|returned
        if not within_optional_limit(len(returned_all),scope['max_distinct_native_content_objects']): raise Stop('object_ceiling')
        c=connect(); new,versions=insert_rows(c,accepted,rec)
        c.close()
        st['object_ids']=sorted(allids); st['returned_object_ids']=sorted(returned_all); persist_state(st)
        result=dict(at_utc=utc(),request_id=rec['request_id'],new_posts=new,new_versions=versions,eligible_records=len(accepted),excluded_records=excluded,total_distinct_objects=len(allids))
        append(WORK/'LOADS.jsonl',result)
        if new and not (WORK/'FIRST_REAL_BATCH.json').exists():
            atomic(WORK/'FIRST_REAL_BATCH.json',dict(result,database=str(DB.relative_to(REPO)),raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],posts=[{k:r.get(k) for k in ('persistent_post_id','source_id','native_post_id','source_url','native_created_at','native_edited_at','body_version_id','body_sha256','content_license')} for r in accepted]))
    return result

def stackexchange_records(data, source_id):
    out=[]
    for r in data.get('items',[]):
        typ='comment' if 'comment_id' in r else 'answer' if 'answer_id' in r else 'question'
        nid=r.get(typ+'_id'); qid=r.get('question_id')
        if typ=='comment' and r.get('post_type')=='question': qid=r.get('post_id')
        parent=r.get('post_id') if typ=='comment' else qid if typ=='answer' else None
        created=dt.datetime.fromtimestamp(r['creation_date'],dt.timezone.utc).isoformat()
        edited=dt.datetime.fromtimestamp(r['last_edit_date'],dt.timezone.utc).isoformat() if r.get('last_edit_date') else None
        license_=r.get('content_license','unknown')
        site=source_id.removeprefix('se_')
        link=r.get('link') or r.get('post_link')
        if typ=='comment' and not link: link=f'https://{site}.stackexchange.com/posts/{parent}#comment{nid}_{parent}'
        out.append(dict(source_id=source_id,native_post_id=str(nid),source_url=link,native_unit=typ,thread_id=str(qid) if qid else 'unresolved',question_thread_id=str(qid) if qid else None,reply_to_post_id=str(parent) if parent else None,parent_namespace=r.get('post_type','post') if typ=='comment' else 'question' if typ=='answer' else None,native_created_at=created,native_edited_at=edited,author_id=str(r.get('owner',{}).get('user_id')) if r.get('owner',{}).get('user_id') else None,author_role='unknown',body_original=r.get('body',''),content_license=license_,license_basis='native API content_license field; historical revisions may differ',native_fields={k:v for k,v in r.items() if k!='body'},context_status='answer_parent_question_root_unresolved' if typ=='comment' and not qid else 'thread_context_not_fully_collected'))
    return out

def discourse_records(data, source_id):
    posts=data.get('latest_posts') or data.get('post_stream',{}).get('posts') or []
    lookup={(x['topic_id'],x['post_number']):str(x['id']) for x in posts}
    rows=[]; dispositions=[]
    for p in posts:
        if p.get('post_type')!=1 or p.get('hidden') or p.get('deleted_at') or p.get('truncated') or not p.get('cooked'):
            dispositions.append(dict(native_post_id=str(p['id']),reason='non_regular_hidden_deleted_truncated_or_missing_body',truncated=p.get('truncated')));continue
        topic=p['topic_id']; number=p['post_number']; parent_number=p.get('reply_to_post_number')
        parent=lookup.get((topic,parent_number)) if parent_number else None
        base=next(x['base_url'] for x in read_json(WORK/'source_registry.json') if x['source_id']==source_id)
        url=urllib.parse.urljoin(base,p.get('post_url') or f'/t/{topic}/{number}')
        rows.append(dict(source_id=source_id,native_post_id=str(p['id']),source_url=url,native_unit='forum_post' if number==1 else 'forum_reply',thread_id=str(topic),reply_to_post_id=parent,parent_namespace='forum_post',native_created_at=p['created_at'],native_edited_at=p.get('updated_at'),native_revision=p.get('version'),author_id=str(p.get('user_id')) if p.get('user_id') else None,author_role='unknown',body_original=p['cooked'],content_license='CC BY-NC-SA 3.0',license_basis='Python Discussions site terms, user-contribution grant; restricted noncommercial reuse',native_fields={k:v for k,v in p.items() if k not in ('raw','cooked','excerpt')},completeness='full_cooked_body_returned_not_truncated',context_status='reply_post_number_unmapped' if parent_number and not parent else 'partial_thread_context'))
    return rows,dispositions

def mastodon_records(data, source_id):
    rows=[];dispositions=[]
    for p in data:
        if p.get('reblog') or p.get('visibility')!='public' or not p.get('content') or not clean(p['content']):
            dispositions.append(dict(native_post_id=str(p['id']),reason='repost_wrapper_nonpublic_or_no_readable_text'));continue
        rows.append(dict(source_id=source_id,native_namespace='status',native_post_id=str(p['id']),source_url=p.get('url') or p.get('uri'),native_unit='public_platform_post',thread_id='unresolved' if p.get('in_reply_to_id') else str(p['id']),reply_to_post_id=p.get('in_reply_to_id'),parent_namespace='status',native_created_at=p['created_at'],native_edited_at=p.get('edited_at'),author_id=str(p.get('account',{}).get('id')) if p.get('account',{}).get('id') else None,author_role='unknown',body_original=p['content'],content_license='no_open_content_grant_verified',license_basis='Documented public API/read and local research snapshot; no open-content or redistribution grant asserted',native_fields={k:v for k,v in p.items() if k not in ('content','account','reblog','media_attachments')},context_status='reply_root_unresolved' if p.get('in_reply_to_id') else 'native_root_post; replies_not_fully_collected',completeness='complete_native_text; media_not_downloaded'))
    return rows,dispositions

def bluesky_records(data):
    rows=[];dispositions=[]
    for item in data.get('feed',[]):
        p=item.get('post',{});native=p.get('record',{});uri=p.get('uri')
        if item.get('reason') or not native.get('text') or not uri:
            dispositions.append(dict(native_post_id=uri,reason='repost_view_or_no_native_authored_text'));continue
        did=p.get('author',{}).get('did');rkey=uri.rsplit('/',1)[-1];reply=native.get('reply',{})
        rows.append(dict(source_id='bluesky',native_namespace='at_uri',native_post_id=uri,source_url=f'https://bsky.app/profile/{did}/post/{rkey}',native_unit='public_platform_post',thread_id=reply.get('root',{}).get('uri') or uri,reply_to_post_id=reply.get('parent',{}).get('uri'),parent_namespace='at_uri',native_created_at=native['createdAt'],native_edited_at=None,native_revision=p.get('cid'),author_id=did,author_role='institutional' if p.get('author',{}).get('handle')=='bsky.app' else 'unknown',body_original=native['text'],body_format='plain',content_license='no_open_content_grant_verified',license_basis='Official developer/content docs support local public-data copy; author retains copyright; no redistribution grant asserted',native_fields={k:v for k,v in p.items() if k!='record'}|{'native_record_metadata':{k:v for k,v in native.items() if k!='text'}},context_status='native_reply_root_parent_URIs; context_partial' if reply else 'native_root_post; replies_not_fully_collected',completeness='complete_native_text; embeds_media_not_downloaded'))
    return rows,dispositions

def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('fetch'); p.add_argument('url'); p.add_argument('--source',required=True); p.add_argument('--purpose',default='policy',choices=['policy','documentation','source_metadata','content'])
    sub.add_parser('preflight')
    args=parser.parse_args()
    with writer():
        if args.command=='preflight':
            with shared(footprint(2097152)) as b: print(json.dumps(b))
        else:
            rec=fetch(args.url,args.source,args.purpose)
            print(json.dumps({k:rec.get(k) for k in ('request_id','status','http_status','raw_bytes','raw_reference','location','error')}))
if __name__=='__main__': main()
