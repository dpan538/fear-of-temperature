"""Single-writer persistent newspaper ELT and bounded transport, package25."""
import collections,csv,datetime as dt,fcntl,hashlib,importlib.util,json,pathlib,re,shutil,sqlite3,time,os
from urllib.parse import urljoin,urlsplit,urlunsplit
import requests
from bs4 import BeautifulSoup
OWN=pathlib.Path(__file__).resolve().parent
REPO=OWN.parents[3]
OLD24=REPO/'work_packages/M1_source_access/24_newspaper_coverage_successor_20261006/worker'
BASE=REPO/'work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/transition_research/acquisition_followthrough_20261005'
SCOPE=json.loads((OWN.parent/'control/EXECUTION_SCOPE.json').read_text())
LOCK=REPO/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
DEADLINE=dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
DB=OWN/'newspaper_elt.sqlite3'
spec=importlib.util.spec_from_file_location('retained_inline_renderer',BASE.parents[1]/'newspaper/prototype/parser.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
OLD_STOP_HOSTS=json.loads((OLD24/'TRANSPORT_STATE.json').read_text())['access_stops']
OLD_REQUESTS=[]
for p in [BASE/'REQUESTS.jsonl',OLD24/'REQUESTS.jsonl']:
 if p.exists():OLD_REQUESTS += [json.loads(x) for x in p.read_text().splitlines() if x]
OLD_STOPS={r['url'] for r in OLD_REQUESTS if r.get('status') not in ['saved']}

def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(url):
 p=urlsplit(url);return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,p.query,''))
def article_id(sid,url):return sid+':article:'+sha((sid+'|publisher-item|'+canon(url)).encode())[:24]
def eligible(day):
 try:return dt.date.fromisoformat(day).isoformat()==day and '1988-01-01'<=day<='2026-09-21'
 except (ValueError,TypeError):return False
def cumulative():return SCOPE['prior_media_bytes']+sum(p.stat().st_size for r in SCOPE['media_lifetime_accounting_roots'] for p in (REPO/r).rglob('*') if p.is_file())
def preflight(pending=0):
 used=cumulative();free=shutil.disk_usage(OWN).free;co=json.loads((OWN.parent/'control/COORDINATION.json').read_text())
 leases=[l for l in co.get('active_leases',[]) if l.get('active',True)];own=sum(l['reserved_bytes'] for l in leases if l.get('thread_id')==SCOPE['owner_thread_id']);other=sum(l['reserved_bytes'] for l in leases if l.get('thread_id')!=SCOPE['owner_thread_id']);reserved=other+max(own,pending)+65536
 b=dict(at_utc=utc(),cumulative_bytes=used,cap_bytes=SCOPE['media_lifetime_cap_bytes'],free_bytes=free,own_lease_bytes=own,other_lease_bytes=other,pending_bytes=pending,effective_pending_and_leases_bytes=reserved,physical_headroom=free-SCOPE['physical_floor_bytes']-SCOPE['recovery_allowance_bytes']-reserved,allocation_headroom=SCOPE['media_lifetime_cap_bytes']-used-reserved)
 if min(b['physical_headroom'],b['allocation_headroom'])<0:raise RuntimeError('resource_stop '+json.dumps(b))
 return b
def save(name,obj):
 b=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);preflight(len(b));p=OWN/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.pending-'+str(os.getpid()));tmp.write_bytes(b);tmp.replace(p)
def append(name,obj):
 with (OWN/name).open('a') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n')
def connect():
 c=sqlite3.connect(DB,timeout=60);c.execute('PRAGMA journal_mode=DELETE');c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);preflight(4*1024*1024)
  c=connect();c.executescript('''
  CREATE TABLE IF NOT EXISTS articles(article_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,source_url TEXT NOT NULL,title TEXT NOT NULL,publication_date TEXT NOT NULL,stratum TEXT NOT NULL,work_family_id TEXT NOT NULL,latest_version_id TEXT NOT NULL,first_loaded_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS article_versions(version_id TEXT PRIMARY KEY,article_id TEXT NOT NULL REFERENCES articles(article_id),body_text TEXT NOT NULL,body_sha256 TEXT NOT NULL,raw_reference TEXT,raw_sha256 TEXT,body_reference TEXT,provenance_json TEXT NOT NULL,loaded_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,source_id TEXT,source_url TEXT,status TEXT NOT NULL,metadata_json TEXT NOT NULL,body_text TEXT,loaded_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS transport(target_id TEXT PRIMARY KEY,purpose TEXT,stratum TEXT,status TEXT,receipt_json TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS baseline(article_id TEXT PRIMARY KEY,publication_date TEXT,stratum TEXT,work_family_id TEXT,source_url TEXT);
  ''')
  baseline=[json.loads(x) for x in (OLD24/'article_baseline_v1/ARTICLE_REGISTER.jsonl').read_text().splitlines() if x]
  with c:
   c.executemany('INSERT OR IGNORE INTO baseline VALUES(?,?,?,?,?)',[(r['article_id'],r['publication_date'],r['stratum'],r['work_family_id'],r['source_url']) for r in baseline if r['disposition']=='confirmed_complete'])
  c.close()
def load(record,body,status='confirmed_complete'):
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);preflight(len(body.encode())*4+1048576);c=connect();stamp=utc()
  record=dict(record);record['load_status']=status;record['loaded_at_utc']=stamp
  if status=='confirmed_complete':
   assert eligible(record['publication_date']) and body.strip() and record['source_url']
   aid=record['article_id'];bh=sha(body.encode());vid=aid+':body:'+bh[:24];record.update(version_id=vid,body_sha256=bh,work_family_id=record.get('work_family_id') or aid)
   match=c.execute('SELECT v.article_id,a.work_family_id FROM article_versions v JOIN articles a ON a.article_id=v.article_id WHERE v.body_sha256=? AND v.article_id<>? LIMIT 1',(bh,aid)).fetchone()
   if match:record['work_family_id']=match[1];record['known_exact_body_copy_of']=match[0]
   with c:
    c.execute('DELETE FROM article_dispositions WHERE article_id=?',(aid,))
    c.execute('INSERT INTO articles VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(article_id) DO UPDATE SET latest_version_id=excluded.latest_version_id,work_family_id=excluded.work_family_id',(aid,record['source_id'],record['source_url'],record['title'],record['publication_date'],record['stratum'],record['work_family_id'],vid,stamp))
    c.execute('INSERT OR IGNORE INTO article_versions VALUES(?,?,?,?,?,?,?,?,?)',(vid,aid,body,bh,record.get('raw_reference'),record.get('raw_sha256'),record.get('body_reference'),json.dumps(record,ensure_ascii=False),stamp))
  else:
   eid=record.get('evidence_id') or sha((record['source_id']+'|'+record['source_url']+'|'+status).encode())[:32];record['evidence_id']=eid
   with c:c.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?)',(eid,record['source_id'],record['source_url'],status,json.dumps(record,ensure_ascii=False),body,stamp))
  c.close();append('LOAD_LOG.jsonl',{k:v for k,v in record.items() if k not in ['opening_passage','closing_passage']});return record
def ensure_dispositions():
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);preflight(1048576);c=connect()
  with c:c.execute('CREATE TABLE IF NOT EXISTS article_dispositions(article_id TEXT PRIMARY KEY REFERENCES articles(article_id),status TEXT NOT NULL,reason TEXT NOT NULL,updated_at_utc TEXT NOT NULL)')
  c.close()
def reclassify_named(aid,status,reason):
 with LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);preflight(1048576);c=connect()
  with c:c.execute('INSERT OR REPLACE INTO article_dispositions VALUES(?,?,?,?)',(aid,status,reason,utc()))
  c.close()
 append('STRUCTURAL_CORRECTIONS.jsonl',{'at_utc':utc(),'article_id':aid,'status':status,'reason':reason,'original_article_versions_preserved':True})
def coverage():
 c=connect();data=c.execute('SELECT article_id,publication_date,stratum,work_family_id FROM baseline UNION SELECT a.article_id,a.publication_date,a.stratum,a.work_family_id FROM articles a LEFT JOIN article_dispositions d ON d.article_id=a.article_id WHERE d.article_id IS NULL').fetchall();c.close();result=collections.defaultdict(set)
 for aid,day,geo,fam in data:result[('pooled',day[:7])].add(fam);result[(geo,day[:7])].add(fam)
 return {key:len(v) for key,v in result.items()}
def state():
 p=OWN/'TRANSPORT_STATE.json';return json.loads(p.read_text()) if p.exists() else {'strata':{s:{'article':0,'discovery':0} for s in SCOPE['strata']},'hosts':{},'access_stops':dict(OLD_STOP_HOSTS),'targets':{}}
def external_discovery_counts():
 result={s:0 for s in SCOPE['strata']}
 for p in OWN.glob('WEB_DISCOVERY_BATCH_*.json'):
  o=json.loads(p.read_text())
  if 'new_distinct_discovery_targets_by_stratum' in o:
   for geo,n in o['new_distinct_discovery_targets_by_stratum'].items():result[geo]+=n
  elif o.get('stratum'):result[o['stratum']]+=o.get('new_distinct_discovery_targets',0)
  elif o.get('items') and all(t.get('source_id')=='otago_daily_times' for t in o['items']):result['NZ']+=o.get('new_distinct_discovery_targets',0)
 return result
def effective_count(st,geo,purpose):return st['strata'][geo][purpose]+(external_discovery_counts()[geo] if purpose=='discovery' else 0)
def fetch(url,sid,geo,purpose='article',evidence=None,cap=None,method='GET',extra=None):
 assert purpose in ['article','discovery'];url=canon(url);tid=sha((sid+'|'+purpose+'|'+url).encode())[:24];st=state()
 if tid in st['targets']:
  return json.loads((OWN/'receipts'/f'{tid}.json').read_text())
 if url in OLD_STOPS:raise ValueError('preserved_exact_stop '+url)
 host=urlsplit(url).hostname
 if host in st['access_stops']:raise ValueError('preserved_host_stop '+host)
 if dt.datetime.now(dt.timezone.utc)>=DEADLINE:raise RuntimeError('fixed_deadline')
 limit=SCOPE['article_distinct_target_attempts_per_stratum'] if purpose=='article' else SCOPE['discovery_distinct_targets_per_stratum']
 native_url=canon((extra or {}).get('native_target_identity') or url);native_key=sha((sid+'|'+purpose+'|'+native_url).encode())[:24]
 already_charged=native_key in st['targets'] or native_key in st.get('charged_native_targets',[])
 if not already_charged and effective_count(st,geo,purpose)>=limit:raise RuntimeError('distinct_target_ceiling '+geo+' '+purpose)
 cap=cap or SCOPE['default_raw_object_cap_bytes'];target=dict(target_id=tid,url=url,source_id=sid,stratum=geo,purpose=purpose,native_evidence=evidence,cap_bytes=cap,method=method,extra=extra,frozen_at_utc=utc());save('targets/'+tid+'.json',target)
 rec=dict(target=target,target_id=tid,url=url,source_id=sid,stratum=geo,purpose=purpose,status='in_progress',started_at_utc=utc(),hops=[],raw_bytes=0,partial=False)
 # Charge exactly once, persist before transport; interruption consumes the attempt.
 if not already_charged:st['strata'][geo][purpose]+=1
 st.setdefault('charged_native_targets',[])
 if native_key not in st['charged_native_targets']:st['charged_native_targets'].append(native_key)
 rec.update(native_target_identity=native_url,native_target_key=native_key,new_distinct_target_charge=not already_charged)
 st['targets'][tid]='in_progress';save('receipts/'+tid+'.json',rec);save('TRANSPORT_STATE.json',st)
 path=OWN/'raw'/(tid+'.bin');path.parent.mkdir(exist_ok=True);session=requests.Session();session.trust_env=False;session.headers['User-Agent']='FearOfTemperatureResearch/1.0 (public newspaper ELT, bounded)';current=url
 try:
  prior_hops=st.get('native_http_hops',{}).get(native_key,0)
  if already_charged and native_key not in st.get('native_http_hops',{}) and (OWN/'receipts'/f'{native_key}.json').exists():prior_hops=len(json.loads((OWN/'receipts'/f'{native_key}.json').read_text())['hops'])
  for hop in range(max(0,SCOPE['max_http_hops_per_target']-prior_hops)):
   host=urlsplit(current).hostname
   if host in st['access_stops']:raise ValueError('redirect_to_stopped_host')
   if urlsplit(current).scheme!='https':raise ValueError('non_https_redirect')
   wait=2.0-(time.time()-st['hosts'].get(host,0))
   if wait>0:time.sleep(wait)
   with LOCK.open('a+b') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);rec['preflight']=preflight(cap+8*1024*1024);st['hosts'][host]=time.time()
    with session.request(method,current,stream=True,allow_redirects=False,timeout=(15,30)) as response:
     h={'url':current,'status':response.status_code,'location':response.headers.get('Location'),'retry_after':response.headers.get('Retry-After'),'content_length':response.headers.get('Content-Length'),'content_type':response.headers.get('Content-Type'),'last_modified':response.headers.get('Last-Modified'),'link':response.headers.get('Link'),'x_wp_total':response.headers.get('X-WP-Total'),'x_wp_totalpages':response.headers.get('X-WP-TotalPages')};rec['hops'].append(h)
     if response.status_code in [301,302,303,307,308]:current=urljoin(current,h['location']);continue
     if response.status_code!=200:
      rec['status']='http_stop'
      if response.status_code in [401,403,429,451] or h['retry_after']:st['access_stops'][host]=h
      break
     if method=='HEAD':rec['status']='saved_headers';rec['final_url']=current;break
     declared=int(h['content_length']) if h['content_length'] and h['content_length'].isdigit() else None
     if declared and declared>cap:rec['status']='declared_object_cap_stop';break
     dig=hashlib.sha256()
     with path.open('wb') as f:
      for chunk in response.iter_content(65536):
       if not chunk:continue
       remaining=cap-rec['raw_bytes']
       if len(chunk)>remaining:
        f.write(chunk[:remaining]);dig.update(chunk[:remaining]);rec['raw_bytes']+=remaining;rec['status']='object_cap_stop';rec['partial']=True;break
       f.write(chunk);dig.update(chunk);rec['raw_bytes']+=len(chunk)
       if dt.datetime.now(dt.timezone.utc)>=DEADLINE:rec['status']='deadline_partial';rec['partial']=True;break
      else:rec['status']='saved'
     rec.update(raw_reference=str(path.relative_to(REPO)),raw_sha256=dig.hexdigest(),final_url=current)
     break
  else:rec['status']='redirect_limit_stop'
 except Exception as error:rec['status']='transport_error';rec['error']=str(error)[:700]
 finally:
  if rec['status']=='in_progress':
   rec['status']='interrupted_pending';rec['partial']=path.exists()
   if path.exists():rec.update(raw_reference=str(path.relative_to(REPO)),raw_sha256=sha(path.read_bytes()),raw_bytes=path.stat().st_size)
  st.setdefault('native_http_hops',{})[native_key]=prior_hops+len(rec['hops']) if 'prior_hops' in locals() else len(rec['hops'])
  session.close();rec['finished_at_utc']=utc();st['targets'][tid]=rec['status'];save('receipts/'+tid+'.json',rec);save('TRANSPORT_STATE.json',st)
  with LOCK.open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);preflight(1048576);c=connect()
   with c:c.execute('INSERT OR REPLACE INTO transport VALUES(?,?,?,?,?)',(tid,purpose,geo,rec['status'],json.dumps(rec)))
   c.close()
  append('REQUESTS.jsonl',rec)
 return rec
