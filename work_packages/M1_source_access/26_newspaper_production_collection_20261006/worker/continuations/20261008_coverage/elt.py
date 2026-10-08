import pathlib
_HERE=pathlib.Path(__file__).resolve()
_PREDECESSOR=_HERE.parents[2]
__file__=str(_PREDECESSOR/'elt.py')
"""Package 26 single-writer continuation of the accepted newspaper store.

Reuse unchanged structural/identity functions without changing package 25 files.
New transport stores one recoverable gzip object and two distinct digests.
"""
import pathlib
_ROOT = pathlib.Path(__file__).resolve().parents[4]
_PREVIOUS = _ROOT / 'work_packages/M1_source_access/25_newspaper_calendar_acquisition_20261006/worker'
exec(compile((_PREVIOUS / 'elt.py').read_text(), str(_PREVIOUS / 'elt.py'), 'exec'))
import gzip, io, copy

PREVIOUS = _PREVIOUS
DB = REPO / SCOPE['newspaper_durable_database']
_load_previous = load
_old_state = json.loads((PREVIOUS / 'TRANSPORT_STATE.json').read_text())
_external = {g: 0 for g in SCOPE['strata']}
for _p in PREVIOUS.glob('WEB_DISCOVERY_BATCH_*.json'):
 _o = json.loads(_p.read_text())
 if 'new_distinct_discovery_targets_by_stratum' in _o:
  for _g, _n in _o['new_distinct_discovery_targets_by_stratum'].items(): _external[_g] += _n
 elif _o.get('stratum'): _external[_o['stratum']] += _o.get('new_distinct_discovery_targets', 0)
 elif _o.get('items') and all(t.get('source_id') == 'otago_daily_times' for t in _o['items']): _external['NZ'] += _o.get('new_distinct_discovery_targets', 0)
for _line in (PREVIOUS / 'REQUESTS.jsonl').read_text().splitlines():
 _r = json.loads(_line)
 if _r.get('status') != 'saved': OLD_STOPS.add(_r['url'])

def state():
 p = OWN / 'TRANSPORT_STATE.json'
 if p.exists(): return json.loads(p.read_text())
 s = copy.deepcopy(_old_state)
 for g, n in _external.items(): s['strata'][g]['discovery'] += n
 s['inherited_external_discovery_charges'] = _external
 s['inherited_state_reference'] = str((PREVIOUS / 'TRANSPORT_STATE.json').relative_to(REPO))
 s['inherited_exact_stops_preserved'] = True
 return s

def external_discovery_counts():
 totals={g:0 for g in SCOPE['strata']}
 for p in OWN.glob('EXTERNAL_SOURCE_PREPARATION_RECEIPT_*.json'):
  o=json.loads(p.read_text())
  if o.get('new_distinct_discovery_targets_by_stratum'):
   for g,n in o['new_distinct_discovery_targets_by_stratum'].items():totals[g]+=n
  elif o.get('stratum'):totals[o['stratum']]+=o.get('new_distinct_discovery_targets',0)
 folded=state().get('new_external_discovery_charges',{})
 return {g:max(0,n-folded.get(g,0)) for g,n in totals.items()}

def resource(pending=0):
 co = json.loads((PREDECESSOR.parent / 'control/COORDINATION.json').read_text())
 leases = [x for x in co.get('active_leases', []) if x.get('active', True)]
 own = max(SCOPE['owner_pending_lease_bytes'], sum(x['reserved_bytes'] for x in leases if x.get('thread_id') == SCOPE['owner_thread_id']))
 other = sum(x['reserved_bytes'] for x in leases if x.get('thread_id') != SCOPE['owner_thread_id'])
 reserve = other + max(own, pending) + 65536
 free = shutil.disk_usage(OWN).free; used = cumulative()
 return dict(at_utc=utc(), free_bytes=free, cumulative_bytes=used, cap_bytes=SCOPE['media_lifetime_cap_bytes'], physical_floor_bytes=SCOPE['physical_floor_bytes'], recovery_allowance_bytes=SCOPE['recovery_allowance_bytes'], own_lease_bytes=own, other_lease_bytes=other, actual_pending_footprint_bytes=pending, effective_pending_and_leases_bytes=reserve, physical_headroom=free-SCOPE['physical_floor_bytes']-SCOPE['recovery_allowance_bytes']-reserve, allocation_headroom=SCOPE['media_lifetime_cap_bytes']-used-reserve)

def preflight(pending=0):
 b = resource(pending)
 if min(b['physical_headroom'], b['allocation_headroom']) < 0: raise RuntimeError('resource_stop ' + json.dumps(b))
 return b

def preparation_save(name, obj):
 """Only small, explicitly released local preparation/delivery metadata.

 No network, original bodies or database transactions use this path. Preserve
 the protected floor even when the production recovery reserve is unavailable.
 """
 b = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode()
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock, fcntl.LOCK_EX)
  if shutil.disk_usage(OWN).free - SCOPE['physical_floor_bytes'] < len(b)*2 + 65536: raise RuntimeError('preparation_metadata_floor_stop')
  p = OWN / name; p.parent.mkdir(parents=True, exist_ok=True)
  tmp = p.with_name(p.name + '.pending-' + str(os.getpid())); tmp.write_bytes(b); tmp.replace(p)

def operation_footprint(raw_cap=None, body_bytes=None):
 # Conservative rollback-journal bound: the existing DB may be touched once.
 # Gzip may marginally expand incompressible input; full TEXT, body sidecar and
 # SQLite growth are included. RAM-only decompression creates no hidden file.
 cap = raw_cap if raw_cap is not None else SCOPE['default_raw_object_cap_bytes']
 body = body_bytes if body_bytes is not None else cap * 4
 return DB.stat().st_size + cap + cap//100 + body*3 + 1048576

def read_payload(ref):
 p = REPO / ref
 return gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes()

class PayloadPath:
 def __init__(self, p): self.p = p
 def read_bytes(self): return read_payload(str(self.p.relative_to(REPO)))
 def read_text(self): return self.read_bytes().decode('utf-8')

def raw_digest_fields(data):
 stored = gzip.compress(data, mtime=0)
 return stored, {'raw_sha256': sha(data), 'raw_bytes': len(data), 'raw_encoding': 'gzip', 'stored_sha256': sha(stored), 'stored_bytes': len(stored)}

def load(record, body, status='confirmed_complete'):
 record = dict(record)
 # Preserve pre-existing accepted IDs/versions/dispositions on restart.
 c = sqlite3.connect('file:'+str(DB)+'?mode=ro', uri=True)
 existing = c.execute('SELECT article_id FROM articles WHERE article_id=?', (record.get('article_id'),)).fetchone() if status == 'confirmed_complete' else None
 c.close()
 if existing:
  return dict(record, load_status='already_retained_identity', body_not_reloaded=True)
 record['origin_package'] = 'package26_coverage_continuation_20261008'
 ref = record.get('raw_reference')
 if ref and ref.endswith('.gz'):
  rid = pathlib.Path(ref).name.removesuffix('.bin.gz')
  rp = OWN/'receipts'/(rid+'.json')
  if rp.exists():
   r = json.loads(rp.read_text())
   for key in ['raw_encoding', 'stored_sha256', 'stored_bytes', 'raw_bytes']: record[key] = r.get(key)
 preflight(operation_footprint(0, len(body.encode())))
 result = _load_previous(record, body, status)
 append('TRANSACTION_RECEIPTS.jsonl', {'at_utc':utc(), 'article_id':result.get('article_id'), 'version_id':result.get('version_id'), 'status':status, 'body_sha256':result.get('body_sha256'), 'baseline_TEXT_consolidation':bool(record.get('baseline_TEXT_consolidation')), 'accepted_rows_preserved':True})
 return result

def _receipt(tid):
 for base in [OWN, PREVIOUS]:
  p = base/'receipts'/(tid+'.json')
  if p.exists(): return json.loads(p.read_text())
 raise ValueError('preserved_attempt_without_reusable_receipt '+tid)

def fetch(url, sid, geo, purpose='article', evidence=None, cap=None, method='GET', extra=None):
 assert purpose in ['article','discovery']; url=canon(url); extra=extra or {}; cap=cap or SCOPE['default_raw_object_cap_bytes']
 tid=sha((sid+'|'+purpose+'|'+url).encode())[:24]; st=state()
 if tid in st['targets']: return _receipt(tid)
 if url in OLD_STOPS: raise ValueError('preserved_exact_stop '+url)
 if urlsplit(url).hostname in st['access_stops']: raise ValueError('preserved_host_stop '+str(urlsplit(url).hostname))
 if dt.datetime.now(dt.timezone.utc)>=DEADLINE: raise RuntimeError('fixed_deadline')
 native=canon(extra.get('native_target_identity') or url); nk=sha((sid+'|'+purpose+'|'+native).encode())[:24]
 charged=nk in st.get('charged_native_targets',[]) or nk in st['targets']
 limit=SCOPE['article_distinct_target_attempts_per_stratum'] if purpose=='article' else SCOPE['discovery_distinct_targets_per_stratum']
 if not charged and effective_count(st,geo,purpose)>=limit: raise RuntimeError('distinct_target_ceiling '+geo+' '+purpose)
 footprint=operation_footprint(cap); preflight(footprint)
 target=dict(target_id=tid,url=url,source_id=sid,stratum=geo,purpose=purpose,native_evidence=evidence,cap_bytes=cap,method=method,extra=extra,frozen_at_utc=utc())
 save('targets/'+tid+'.json',target)
 rec=dict(target_id=tid,target=target,url=url,source_id=sid,stratum=geo,purpose=purpose,status='in_progress',started_at_utc=utc(),hops=[],raw_bytes=0,partial=False,native_target_key=nk,native_target_identity=native,new_distinct_target_charge=not charged)
 if not charged: st['strata'][geo][purpose]+=1
 st.setdefault('charged_native_targets',[])
 if nk not in st['charged_native_targets']: st['charged_native_targets'].append(nk)
 st['targets'][tid]='in_progress'; save('receipts/'+tid+'.json',rec); save('TRANSPORT_STATE.json',st)
 path=OWN/'raw'/(tid+'.bin.gz'); path.parent.mkdir(exist_ok=True)
 session=requests.Session(); session.trust_env=False; session.headers['User-Agent']='FearOfTemperatureResearch/1.0 (public newspaper ELT, bounded)'
 current=url; prior=st.get('native_http_hops',{}).get(nk,0); original=hashlib.sha256(); count=0
 try:
  for hop in range(max(0,SCOPE['max_http_hops_per_target']-prior)):
   host=urlsplit(current).hostname
   if host in st['access_stops']: raise ValueError('redirect_to_stopped_host')
   if urlsplit(current).scheme!='https': raise ValueError('non_https_redirect')
   delay=SCOPE['min_per_host_spacing_seconds']-(time.time()-st['hosts'].get(host,0))
   if delay>0: time.sleep(delay)
   with LOCK.open('a+b') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX); rec['preflight']=preflight(footprint); st['hosts'][host]=time.time()
    remaining=(DEADLINE-dt.datetime.now(dt.timezone.utc)).total_seconds()
    if remaining<=0:raise RuntimeError('fixed_deadline')
    with session.request(method,current,stream=True,allow_redirects=False,timeout=(max(.1,min(15,remaining)),max(.1,min(30,remaining)))) as response:
     h={key:response.headers.get(value) for key,value in [('location','Location'),('retry_after','Retry-After'),('content_length','Content-Length'),('content_type','Content-Type'),('last_modified','Last-Modified'),('link','Link'),('x_wp_total','X-WP-Total'),('x_wp_totalpages','X-WP-TotalPages')]}; h.update(url=current,status=response.status_code); rec['hops'].append(h)
     if response.status_code in [301,302,303,307,308]: current=urljoin(current,h['location']); continue
     if response.status_code!=200:
      rec['status']='http_stop'
      if response.status_code in [401,403,429,451] or h['retry_after']: st['access_stops'][host]=h
      break
     if method=='HEAD': rec['status']='saved_headers';rec['final_url']=current;break
     declared=int(h['content_length']) if h['content_length'] and h['content_length'].isdigit() else None
     if declared and declared>cap: rec['status']='declared_object_cap_stop';break
     with path.open('wb') as out, gzip.GzipFile(filename='',fileobj=out,mode='wb',mtime=0) as gz:
      for chunk in response.iter_content(65536):
       if not chunk: continue
       if dt.datetime.now(dt.timezone.utc)>=DEADLINE:rec['status']='deadline_partial';rec['partial']=True;break
       remaining=cap-count; data=chunk[:remaining]; gz.write(data);original.update(data);count+=len(data)
       if len(chunk)>remaining:rec['status']='object_cap_stop';rec['partial']=True;break
      else: rec['status']='saved'
     rec['final_url']=current;break
  else: rec['status']='redirect_limit_stop'
 except Exception as error:
  rec['status']='interrupted_pending' if isinstance(error,RuntimeError) else 'transport_error';rec['error']=str(error)[:1400];rec['partial']=path.exists()
 finally:
  session.close()
  if rec['status']=='in_progress':rec['status']='interrupted_pending';rec['partial']=path.exists()
  if path.exists():rec.update(raw_reference=str(path.relative_to(REPO)),raw_sha256=original.hexdigest(),raw_bytes=count,raw_encoding='gzip',stored_bytes=path.stat().st_size,stored_sha256=sha(path.read_bytes()))
  rec['finished_at_utc']=utc(); st['targets'][tid]=rec['status'];st.setdefault('native_http_hops',{})[nk]=prior+len(rec['hops'])
  # Closing small receipts remains possible even when production capacity stops.
  preparation_save('receipts/'+tid+'.json',rec);preparation_save('TRANSPORT_STATE.json',st)
  append('REQUESTS.jsonl',rec)
 if 'resource_stop' in rec.get('error','') or 'fixed_deadline' in rec.get('error',''):raise RuntimeError(rec['error'])
 return rec

__file__=str(_HERE)
PREDECESSOR=_PREDECESSOR
OWN=_HERE.parent
SCOPE=json.loads((OWN/'EXECUTION_SCOPE.json').read_text())
DEADLINE=dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
DB=REPO/SCOPE['newspaper_durable_database']
for _line in (PREDECESSOR/'REQUESTS.jsonl').read_text().split('\n'):
 if _line:
  _r=json.loads(_line)
  if _r.get('status')!='saved':OLD_STOPS.add(_r['url'])
def state():
 p=OWN/'TRANSPORT_STATE.json'
 if not p.exists():raise RuntimeError('Missing successor state; no counter reset allowed')
 return json.loads(p.read_text())
def _receipt(tid):
 for base in [OWN,PREDECESSOR,PREVIOUS]:
  p=base/'receipts'/(tid+'.json')
  if p.exists():return json.loads(p.read_text())
 raise ValueError('preserved_attempt_without_reusable_receipt '+tid)
