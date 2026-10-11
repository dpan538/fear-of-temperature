"""Persistent operation-age fairness; no corpus volume or quality weights."""
import datetime as dt,urllib.parse
def epoch(value):
 if not value:return 0.0
 try:return dt.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
 except (ValueError,AttributeError):return 0.0

def select(jobs,source_attempts,now,host_attempts,spacing,provider_until=None):
 """Choose an eligible least-recently-served source, then its oldest job."""
 available=[];waits=[]
 for index,job in enumerate(jobs):
  sid=job['source_id'];host=job['host'];until=host_attempts.get(host,0)+spacing.get(sid,2)
  until=max(until,(provider_until or {}).get(job['job_key'],0))
  if until>now:waits.append(until-now);continue
  age=epoch(job.get('last_attempt_at_utc') or job.get('ready_at_utc'))
  available.append((epoch(source_attempts.get(sid)),age,index,job))
 return (min(available,key=lambda r:r[:3])[3],0) if available else (None,min(waits,default=0))

class Queue:
 def __init__(self,state=None,request_rows=()):
  self.state=state or {'version':'operation-age-source-and-job-fairness-v1','last_source_attempt_at_utc':{}}
  self.state.setdefault('last_source_attempt_at_utc',{});self.by_request={}
  for row in request_rows:
   at=row.get('started_at');sid=row.get('source_id')
   if not at or not sid:continue
   self.by_request[row['request_id']]=at
   old=self.state['last_source_attempt_at_utc'].get(sid)
   if epoch(at)>epoch(old):self.state['last_source_attempt_at_utc'][sid]=at
 def jobs(self,cursors,discoveries,registry,now,hash_fn):
  jobs=[]
  for kind,items in [('content',cursors),('discovery',discoveries)]:
   for item in items:
    if item['state']!='active':continue
    sid=item['source_id'];source=registry[sid]
    item.setdefault('ready_at_utc',now)
    item.setdefault('ready_time_basis','native frontier becomes scheduler-visible; not publication/foundation time')
    if not item.get('last_attempt_at_utc') and item.get('last_request') in self.by_request:item['last_attempt_at_utc']=self.by_request[item['last_request']]
    identity='|'.join(str(item.get(k,'')) for k in ('source_id','cohort_id','actor_id','url','anchor','directory_kind','order'))
    item.setdefault('scheduler_job_key',kind+':'+hash_fn(identity.encode())[:24])
    url=item.get('url') if item.get('adapter') in ('native_web','blogger_html') else 'https://public-api.wordpress.com/' if item.get('carrier')=='personal_blog' else 'https://public.api.bsky.app/' if sid=='bluesky' else source['base_url']
    jobs.append({'job_key':item['scheduler_job_key'],'source_id':sid,'kind':kind,'item':item,'host':urllib.parse.urlsplit(url).hostname,'url':url,'ready_at_utc':item['ready_at_utc'],'last_attempt_at_utc':item.get('last_attempt_at_utc')})
  return jobs
 def attempted(self,job,at):
  job['item']['last_attempt_at_utc']=at
  self.state['last_source_attempt_at_utc'][job['source_id']]=at
  self.state['last_dispatch']={'job_key':job['job_key'],'source_id':job['source_id'],'kind':job['kind'],'attempt_at_utc':at}
 def completed(self,job,at):
  job['item']['last_operation_end_at_utc']=at
  self.state['last_operation_completed_at_utc']=at
