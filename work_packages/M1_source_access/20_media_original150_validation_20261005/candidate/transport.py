"""Bounded policy requests now; article/frame execution requires coordinator release."""
import sys
sys.dont_write_bytecode=True
import json,os,time,hashlib,fcntl,shutil,re
from pathlib import Path
from datetime import datetime,timezone,timedelta
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import requests
from metadata import challenge
OUT=Path(__file__).resolve().parent.parent;ROOT=OUT.parents[2]
SCOPE=OUT/'control/SCOPE.json';STATE=OUT/'evidence/HTTP_STATE.json';HEAVY=ROOT/'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
DOCS=[{'source_id':'edjnet','url':'https://www.europeandatajournalism.eu/robots.txt','purpose':'policy_robots'},{'source_id':'edjnet','url':'https://www.europeandatajournalism.eu/about/licence/','purpose':'policy_licence'},{'source_id':'opendemocracy','url':'https://www.opendemocracy.net/robots.txt','purpose':'policy_robots'},{'source_id':'opendemocracy','url':'https://www.opendemocracy.net/syndication-2/','purpose':'policy_licence'}]
def now():return datetime.now(timezone.utc)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 if p.is_symlink():raise RuntimeError('Symlink checkpoint forbidden')
 temp=p.with_name(p.name+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(temp,p)
def budget(add=0):
 s=read(SCOPE);used=s['prior_media_raw_bytes']
 for folder in ['raw','bodies']:
  p=OUT/folder
  if p.is_symlink():raise RuntimeError('Evidence symlink forbidden')
  for f in p.rglob('*') if p.exists() else []:
   if f.is_symlink():raise RuntimeError('Evidence symlink forbidden')
   if f.is_file():used+=f.stat().st_size
 reserve=2147483648+100000000+67108864+max(0,1073741824-used-add)
 free=shutil.disk_usage(OUT).free
 if used+add>s['combined_media_raw_cap_bytes'] or free-add-reserve<s['floor_bytes']:raise RuntimeError('Cumulative cap/floor/reserve prevents request')
 return {'free_bytes':free,'media_retained_raw_and_text_bytes':used,'cap_remaining_bytes':s['combined_media_raw_cap_bytes']-used,'reserved_bytes':reserve,'floor_bytes':s['floor_bytes'],'prior_media_raw_bytes':s['prior_media_raw_bytes'],'derived_body_text_also_charged_to_cap':True}
def before_deadline():
 remaining=(datetime.fromisoformat(read(SCOPE)['execution_deadline_utc'])-now()).total_seconds()
 if remaining<=0:raise RuntimeError('Operation deadline reached')
 return remaining
@contextmanager
def lock():
 with HEAVY.open('r+') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:yield
  finally:fcntl.flock(f,fcntl.LOCK_UN)
def check_release(plan):
 p=OUT/'control/MEDIA_EXECUTION_RELEASE.json'
 if not p.exists():raise RuntimeError('Coordinator execution release missing')
 r=read(p)
 if r.get('approved') is not True:raise RuntimeError('Execution not released')
 for name,h in r.get('code_sha256',{}).items():
  if sha(OUT/name)!=h:raise RuntimeError('Released code digest differs')
 needed={'candidate/schema.sql','candidate/identity.py','candidate/metadata.py','candidate/store.py','candidate/transport.py','candidate/run.py'}
 if not needed.issubset(r.get('code_sha256',{})):raise RuntimeError('Incomplete code release')
 if r.get('route_plan_sha256')!=sha(plan) or r.get('scope_sha256')!=sha(SCOPE):raise RuntimeError('Scope/route digest differs')
 if r.get('execution_deadline_utc')!=read(SCOPE)['execution_deadline_utc']:raise RuntimeError('Deadline release differs')
 before_deadline()
def fetch(source,url,purpose,policy=False):
 if policy:
  if not any(x['source_id']==source and x['url']==url and x['purpose']==purpose for x in DOCS):raise RuntimeError('Not an allowlisted new policy document')
  if purpose!='policy_robots':
   from urllib.robotparser import RobotFileParser
   candidates=[read(p) for p in (OUT/'evidence/requests').glob('*.json') if read(p).get('source_id')==source and read(p).get('purpose')=='policy_robots']
   if len(candidates)!=1 or candidates[0]['status']!='raw_retained':raise RuntimeError('Retained robots policy required')
   robot=RobotFileParser();robot.parse((OUT/candidates[0]['raw_path']).read_text().splitlines())
   if any(not robot.can_fetch(agent,url) for agent in ['FearTemperatureResearch','OAI-SearchBot','GPTBot']):raise RuntimeError('Policy document robots stop')
 else:raise RuntimeError('Use run.execute after exact coordinator release; no direct frame/body fetch')
 return _fetch(source,url,purpose)
def _fetch(source,url,purpose):
 from urllib.parse import urlsplit,parse_qsl
 u=urlsplit(url)
 if u.scheme!='https' or u.username or any(re.search(r'key|token|password|auth',k,re.I) for k,v in parse_qsl(u.query)):raise RuntimeError('Credential-bearing or nonHTTPS route forbidden')
 if purpose.startswith('body:'):
  check_release(OUT/'ROUTE_PLAN.json');plan=read(OUT/'ROUTE_PLAN.json')
  cell=next((x for x in plan['released_candidates'] if x['source_id']==source and purpose.startswith('body:'+source+':'+x['month']+':')),None)
  if not cell or u.hostname!=cell['host']:raise RuntimeError('Body outside released source/month/host')
  frame=read(OUT/cell['frame_receipt_path'])
  if url not in sorted(set(frame['article_urls']))[:5]:raise RuntimeError('Body outside frozen first5 selection')
 with lock():
  before_deadline();budget(read(SCOPE)['object_cap_bytes'])
  state=read(STATE) if STATE.exists() else {'sources':{}}
  rid=hashlib.sha256(json.dumps([source,url,purpose],separators=(',',':')).encode()).hexdigest()[:32];cp=OUT/'evidence/requests'/f'{rid}.json'
  prior=list((OUT/'evidence/requests').glob('*.json')) if (OUT/'evidence/requests').exists() else []
  if purpose.startswith('body:'):
   attempts=[read(p) for p in prior if read(p).get('purpose','').startswith('body:')]
   cell_prefix=':'.join(purpose.split(':')[:3])+':'
   if len(attempts)>=read(SCOPE)['article_cap'] or sum(r['purpose'].startswith(cell_prefix) for r in attempts)>=read(SCOPE)['per_source_month_article_cap']:raise RuntimeError('Persisted body attempt cap reached')
  if cp.exists() or state['sources'].get(source,{}).get('halted') or any(read(p).get('source_id')==source and read(p).get('status') in {'in_progress','failed','access_challenge'} for p in prior):raise RuntimeError('Persisted attempt/source stop forbids automatic retry')
  if state.get('last_finished_utc'):
   delay=2-(now()-datetime.fromisoformat(state['last_finished_utc'])).total_seconds()
   if delay>0:time.sleep(delay)
  remaining=before_deadline();meta={'request_id':rid,'source_id':source,'request_url':url,'purpose':purpose,'requested_at_utc':now().isoformat(),'status':'in_progress','http_status':None,'byte_count':0,'raw_path':None}
  save(cp,meta) # A crash after this intent cannot lead to another automatic attempt.
  path=OUT/'raw'/f'{rid}.bin';path.parent.mkdir(exist_ok=True);part=path.with_suffix('.part');response=None
  try:
   response=requests.get(url,headers={'User-Agent':'FearTemperatureResearch/20 (bounded noncommercial research; no model training)','Accept-Encoding':'identity'},stream=True,allow_redirects=False,timeout=(min(10,max(.1,remaining)),min(10,max(.1,remaining))))
   meta.update(http_status=response.status_code,mime_type=response.headers.get('Content-Type'),response_headers={k:v for k,v in response.headers.items() if k.lower() in {'content-type','content-length','content-encoding','date','retry-after','etag','last-modified'}})
   retry=response.headers.get('Retry-After')
   if response.status_code!=200 or retry:
    if retry:
     until=now()+timedelta(hours=1)
     try:until=now()+timedelta(seconds=int(retry)) if retry.isdigit() else parsedate_to_datetime(retry).astimezone(timezone.utc)
     except (ValueError,TypeError,OverflowError):pass
     meta['retry_not_before_utc']=until.isoformat()
    raise RuntimeError('HTTP non200 or Retry-After; no redirect/retry')
   if response.headers.get('Content-Encoding','identity').lower() not in {'','identity'}:raise RuntimeError('Encoded object length unresolved')
   cap=read(SCOPE)['object_cap_bytes'];cl=response.headers.get('Content-Length')
   if cl and (not cl.isdigit() or not 0<int(cl)<=cap):raise RuntimeError('Content-Length exceeds object cap or invalid')
   with part.open('xb') as f:
    for b in response.iter_content(65536):
     before_deadline()
     if meta['byte_count']+len(b)>cap:raise RuntimeError('Object cap reached')
     budget(len(b));f.write(b);f.flush();meta['byte_count']+=len(b)
   if meta['byte_count']==0 or (cl and meta['byte_count']!=int(cl)):raise RuntimeError('Empty/truncated response')
   os.link(part,path);part.unlink();meta.update(raw_path=str(path.relative_to(OUT)),sha256=sha(path),status='raw_retained')
   if 'html' in (meta['mime_type'] or '') and challenge(path.read_bytes())['stop']:meta['status']='access_challenge';state['sources'][source]={'halted':True,'reason':'HTTP200 challenge'}
  except BaseException as e:
   meta.update(status='failed',error=type(e).__name__+': bounded request stopped; no retry')
   if part.exists():meta.update(partial_path=str(part.relative_to(OUT)),partial_sha256=sha(part),byte_count=part.stat().st_size)
   state['sources'][source]={'halted':True,'reason':meta['error']}
  finally:
   if response is not None:response.close()
   meta['finished_at_utc']=now().isoformat();state['last_finished_utc']=meta['finished_at_utc'];save(cp,meta);save(STATE,state)
  return meta
if __name__=='__main__':
 for x in DOCS:
  state=read(STATE) if STATE.exists() else {'sources':{}}
  if state['sources'].get(x['source_id'],{}).get('halted'):continue
  r=fetch(x['source_id'],x['url'],x['purpose'],policy=True);print(json.dumps({k:r.get(k) for k in ['source_id','purpose','http_status','status','byte_count']}),flush=True)
 print(json.dumps(budget(),ensure_ascii=False))
