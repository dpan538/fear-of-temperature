"""Rotate evidenced newspaper families and load paired whole articles as obtained."""
import collections,datetime as dt,json,pathlib,re,time,os
from bs4 import BeautifulSoup
import elt,extract_load
ROOTS={r['url']:(elt.OLD24 if (elt.OLD24/(r.get('raw_path') or '_none')).exists() else elt.BASE,r) for r in elt.OLD_REQUESTS if r.get('status')=='saved' and r.get('raw_path')}
REG=[json.loads(x) for x in (elt.OLD24/'article_baseline_v1/ARTICLE_REGISTER.jsonl').read_text().splitlines()]
KNOWN={elt.canon(r['raw_source_url']) for r in REG}

def get(url,sid,evidence):
 if url in ROOTS:
  origin,r=ROOTS[url];p=pathlib.Path(r['raw_path']);p=p if p.is_absolute() else origin/p
  return p.read_bytes(),{'reused_raw_reference':str(p.relative_to(elt.REPO)),'accepted_raw_sha256':r['raw_sha256'],'url':url}
 r=elt.fetch(url,sid,extract_load.ADAPTERS[sid]['stratum'],'discovery',evidence)
 if r['status']=='saved':return (elt.REPO/r['raw_reference']).read_bytes(),r
 return b'',r

def queue(sid,items):
 # Read and replace under the same lock: concurrent metadata additions cannot
 # overwrite another source-discovery batch while the sole ELT writer runs.
 with elt.LOCK.open('a+b') as lock:
  elt.fcntl.flock(lock,elt.fcntl.LOCK_EX);p=elt.OWN/'queues'/f'{sid}.json';old=json.loads(p.read_text()) if p.exists() else [];keys={elt.canon(t['url']) for t in old}
  for t in items:
   u=elt.canon(t['url']);native=elt.canon(t.get('article_url') or t['url'])
   if u not in keys and native not in KNOWN and u not in elt.OLD_STOPS:old.append(t);keys.add(u)
  b=(json.dumps(old,ensure_ascii=False,indent=2)+'\n').encode();elt.preflight(len(b));p.parent.mkdir(exist_ok=True);tmp=p.with_name(p.name+'.pending-'+str(os.getpid()));tmp.write_bytes(b);tmp.replace(p)
 return len(old)

def sitemap(url,sid):
 raw,receipt=get(url,sid,'Native sitemap link from accepted publisher index');soup=BeautifulSoup(raw,'xml');items=[]
 for n in soup.select('url'):
  loc=n.find('loc');u=loc.text if loc else ''
  m=re.search(r'/(\d{4})/(\d{2})(?:/(\d{2}))?/',u)
  if not m:continue
  month=m[1]+'-'+m[2]
  if not '1988-01'<=month<='2026-09':continue
  items.append(dict(source_id=sid,url=u,month=month,native_evidence={'sitemap_url':url,'sitemap_raw_receipt':receipt,'date_is_URL_locator_only':True}))
 queue(sid,items)
 return len(items)

def gl_index(url):
 raw,receipt=get(url,'green_left','Native back-issues pagination observed in accepted listing');soup=BeautifulSoup(raw,'html.parser');items=[]
 for a in soup.select('a[href]'):
  if not re.fullmatch(r'/issue/\d+',a['href']):continue
  m=re.search(r'published (\d{4}-\d{2}-\d{2})',a.parent.get_text(' ',strip=True))
  if not m:continue
  if not elt.eligible(m[1]):continue
  items.append({'url':elt.urljoin(url,a['href']),'publication_date':m[1],'month':m[1][:7],'index_receipt':receipt})
 p=elt.OWN/'GL_ISSUE_QUEUE.json';old=json.loads(p.read_text()) if p.exists() else [];known={x['url'] for x in old}
 for x in items:
  if x['url'] not in known:old.append(x);known.add(x['url'])
 elt.save('GL_ISSUE_QUEUE.json',old)
 return len(items)

def gl_issue(issue):
 raw,receipt=get(issue['url'],'green_left',{'observed_dated_issue':issue});soup=BeautifulSoup(raw,'html.parser');items=[]
 for a in soup.select('a[href]'):
  u=elt.urljoin(issue['url'],a['href'])
  if re.match(r'https://www.greenleft.org.au/\d{4}/\d+/',u):items.append({'source_id':'green_left','url':u,'month':issue['month'],'native_evidence':{'dated_native_issue':issue,'issue_receipt':receipt,'title':a.get_text(' ',strip=True)}})
 queue('green_left',items)
 return len(items)

def beaver_metadata(url):
 raw,receipt=get(url,'beaver','Accepted public WordPress posts API, metadata-only embed context; date-bounded pagination family');objects=json.loads(raw) if raw else [];items=[]
 for obj in objects:
  day=(obj.get('date') or '')[:10]
  if not elt.eligible(day):continue
  api=obj.get('_links',{}).get('self',[{}])[0].get('href')
  if not api or not obj.get('link'):continue
  items.append({'source_id':'beaver','url':api,'article_url':obj['link'],'native_post_id':obj['id'],'representation':'publisher_wp_article_json','month':day[:7],'native_evidence':{'metadata_url':url,'metadata_receipt':receipt,'id':obj['id'],'publisher_date':obj.get('date'),'publisher_title':obj.get('title'),'original_article_url':obj['link'],'advertised_self_api':api}})
 queue('beaver',items)
 if receipt.get('hops'):
  link=receipt['hops'][-1].get('link') or '';m=re.search(r'<([^>]+)>;\s*rel="next"',link)
  if m:elt.save('BEAVER_NEXT_PAGE.json',{'url':m[1],'observed_in_receipt':receipt.get('target_id')})
  else:elt.save('BEAVER_NEXT_PAGE.json',{'url':None,'metadata_pages_exhausted':True})
 return len(items)

def issue_html(url):
 raw,receipt=get(url,'mit_tech','Native issue link from accepted all-issues list');soup=BeautifulSoup(raw,'html.parser');items=[]
 for a in soup.select('main a[href]'):
  u=elt.urljoin(url,a['href']);m=re.search(r'/(\d{4})/(\d{2})/(\d{2})/',u)
  if m and elt.eligible('-'.join(m.groups())):items.append({'source_id':'mit_tech','url':u,'month':m[1]+'-'+m[2],'native_evidence':{'native_issue_url':url,'native_issue_receipt':receipt,'title':a.get_text(' ',strip=True)}})
 queue('mit_tech',items)
 return len(items)

def perform_pair(sid):
 p=elt.OWN/'queues'/f'{sid}.json'
 if not p.exists():return 0
 items=json.loads(p.read_text());geo=extract_load.ADAPTERS[sid]['stratum'];cov=elt.coverage();st=elt.state();touched=set(st['targets']);group=collections.defaultdict(list)
 for t in items:
  tid=elt.sha((sid+'|article|'+elt.canon(t['url'])).encode())[:24]
  # These native listing titles identify previously observed component families.
  # Leave them in the queue as uninspected components; use complete article targets.
  if sid=='green_left' and isinstance(t.get('native_evidence'),dict) and t['native_evidence'].get('title','').strip().lower() in ['radio highlights','write on']:continue
  if tid not in touched and elt.canon(t.get('article_url') or t['url']) not in KNOWN and cov.get((geo,t['month']),0)<2:group[t['month']].append(t)
 if not group:return 0
 # Give pooled deficit months priority, then geographic deficits, earliest first.
 month=min(group,key=lambda m:(cov.get(('pooled',m),0)>=2,m));attempted=0
 for target in group[month]:
  if elt.coverage().get((geo,month),0)>=2:break
  if attempted>=8:break  # resume the remaining native order on the next rotation
  if elt.state()['strata'][geo]['article']>=400:break
  record=extract_load.acquire(target);attempted+=1
  print(json.dumps({'at_utc':elt.utc(),'source':sid,'month':month,'status':record.get('load_status') if record else 'stopped','title':record.get('title') if record else None,'regional_confirmed':elt.coverage().get((geo,month),0)}),flush=True)
 return attempted

def snapshot(label):
 c=elt.connect();articles=c.execute('SELECT count(*) FROM articles a LEFT JOIN article_dispositions d ON a.article_id=d.article_id WHERE d.article_id IS NULL').fetchone()[0];versions=c.execute('SELECT count(*) FROM article_versions').fetchone()[0];evidence=c.execute('SELECT count(*) FROM evidence').fetchone()[0];c.close();cov=elt.coverage();s=elt.state();b=elt.preflight()
 elt.save('CHECKPOINT.json',{'at_utc':elt.utc(),'label':label,'loaded_complete_article_records':articles,'loaded_whole_text_versions':versions,'pending_or_component_evidence_records':evidence,'passing_pooled_months':sum(g=='pooled' and n>=2 for (g,m),n in cov.items()),'single_pooled_months':sum(g=='pooled' and n==1 for (g,m),n in cov.items()),'transport_counts':s['strata'],'resource':b,'early_1988_1990':'Four bounded publisher print issues with observed printed dates and pre-transfer size/page plans supplied eight complete articles: two each in April 1988, October 1988, May 1989 and April 1990. One additional May 1989 continuation remains pending severe native OCR. Crimson retention remains pending. No further network acquisition after the physical-space stop.','deadline':elt.SCOPE['hard_deadline_at_utc']})
 checkpoint=json.loads((elt.OWN/'CHECKPOINT.json').read_text());checkpoint['external_discovery_counts']=elt.external_discovery_counts();elt.append('CHECKPOINT_HISTORY.jsonl',checkpoint)
 print(json.dumps({'CHECKPOINT':label,'clock':elt.utc(),'articles':articles,'passing_months':sum(g=='pooled' and n>=2 for (g,m),n in cov.items()),'bytes':b['cumulative_bytes']}),flush=True)

def extra_jobs():
 p=elt.OWN/'EXTRA_JOBS.json';jobs=json.loads(p.read_text()) if p.exists() else [];done_path=elt.OWN/'EXTRA_JOBS_DONE.json';done=set(json.loads(done_path.read_text())) if done_path.exists() else set()
 for job in jobs:
  key=job['job_id']
  if key in done:continue
  if job['kind']=='alternate_article':extract_load.acquire(job['target'])
  elif job['kind']=='discovery':get(job['url'],job['source_id'],job['native_evidence'])
  elif job['kind']=='historical_pdf':
   sid='mit_tech';url=job['url'];head=elt.fetch(url,sid,'US','discovery',job['printed_date_evidence'],method='HEAD',extra={'necessary_pages':job['necessary_pages'],'derivative_footprint_cap_bytes':job['derivative_footprint_cap_bytes']})
   length=head.get('hops',[{}])[-1].get('content_length');length=int(length) if length and str(length).isdigit() else None
   existing_path=elt.OWN/'NEW_PDF_ISSUES.json';existing=json.loads(existing_path.read_text()) if existing_path.exists() else [];raw_total=sum(x.get('raw_bytes',0) for x in existing)
   if head['status']=='saved_headers' and length and length<=elt.SCOPE['historical_pdf_raw_cap_bytes'] and len(existing)<elt.SCOPE['max_new_historical_issues'] and raw_total+length<=elt.SCOPE['new_historical_pdf_aggregate_raw_cap_bytes']:
    plan=dict(job,observed_content_length_bytes=length,HEAD_receipt=head,frozen_before_transfer_at_utc=elt.utc());elt.save('pdf_plans/'+key+'.json',plan)
    rec=elt.fetch(url,sid,'US','article',plan,cap=elt.SCOPE['historical_pdf_raw_cap_bytes'],extra={'kind':'historical_pdf','observed_printed_date':job['publication_date'],'necessary_pages':job['necessary_pages'],'derivative_footprint_cap_bytes':job['derivative_footprint_cap_bytes']});existing.append(rec);elt.save('NEW_PDF_ISSUES.json',existing)
    elt.load({'source_id':sid,'source_url':url,'publication_date':job['publication_date'],'pdf_plan_reference':'pdf_plans/'+key+'.json','raw_reference':rec.get('raw_reference'),'raw_sha256':rec.get('raw_sha256'),'necessary_pages':job['necessary_pages']},'', 'pending_original_article_mapping_'+rec['status'])
   else:elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job':job,'HEAD_receipt':head,'observed_bytes':length,'reason':'unobserved/larger-than-released footprint or issue/aggregate cap; no blind raw transfer'})
  elif job['kind']=='mapped_article':
   record=dict(job['record']);record.setdefault('title',record.get('native_title'));record.setdefault('raw_sha256',record.get('raw_sha256_reused'));body=(elt.REPO/record['body_reference']).read_text();elt.load(record,body,job.get('status','confirmed_complete'))
  done.add(key);elt.save('EXTRA_JOBS_DONE.json',sorted(done));return 1
 return 0

def run():
 if (elt.OWN/'COLLECTION_CLOSE_REASON.json').exists():raise RuntimeError('Closed tranche: preserve the resource stop; a new bounded release is required for further acquisition')
 elt.ensure_dispositions()
 # All these links are already evidenced; no synthetic date/article URLs.
 trinity=BeautifulSoup((elt.OLD24/'raw/23cd5d9cb90826a9d7c7d538.bin').read_bytes(),'xml');tr_urls=[n.loc.text for n in trinity.select('sitemap') if re.search(r'/post-sitemap\d*\.xml$',n.loc.text)]
 manc=BeautifulSoup((elt.OLD24/'raw/814a7e0ce00db75df8aeaafa.bin').read_bytes(),'xml');m_urls=[n.loc.text for n in manc.select('sitemap') if re.search(r'/post-sitemap\d+\.xml$',n.loc.text)]
 # Broad era rotation of native sitemap files; retained oldest maps first.
 m_urls=sorted(m_urls,key=lambda u:(0 if 'sitemap92.' in u or 'sitemap93.' in u else 1,-int(re.search(r'sitemap(\d+)',u)[1])))
 gl_pages=['https://www.greenleft.org.au/back-issues?page='+str(i) for i in range(30,-1,-1)]
 tech=BeautifulSoup((elt.OLD24/'raw/7beb68020911811b49c51045.bin').read_bytes(),'html.parser');tech_urls=[elt.urljoin('https://thetech.com',a['href']) for a in tech.select('a.issue[href]') if re.match(r'/issues/(12[7-9]|13\d|14[0-6])/',a['href'])]
 # Native chronological issue order; record/date mapping is discovered on page.
 by_volume=collections.defaultdict(list)
 for u in sorted(set(tech_urls),key=lambda u:tuple(map(int,u.rsplit('/issues/',1)[1].split('/')))):
  by_volume[int(u.rsplit('/issues/',1)[1].split('/')[0])].append(u)
 # Breadth across native observed year/issue families before remaining density.
 # Positions do not assert a month; only native dated article links do.
 broad=[]
 for round_number in range(12):
  for volume,urls in sorted(by_volume.items()):
   position=min(len(urls)-1,round_number*len(urls)//12)
   if urls[position] not in broad:broad.append(urls[position])
 tech_urls=broad+[u for urls in by_volume.values() for u in urls if u not in broad]
 progress={'trinity':0,'manc':0,'gl':0,'tech':0};gl_done=set();last_checkpoint=elt.cumulative()
 state_path=elt.OWN/'DISCOVERY_PROGRESS.json'
 if state_path.exists():progress.update(json.loads(state_path.read_text()))
 elt.save('WORKER_PROCESS.json',{'pid':os.getpid(),'started_at_utc':elt.utc(),'single_writer':True,'tech_schedule':'native observed issue positions across all years before dense remainders'})
 snapshot('first integrated checkpoint: cache loaded and early route explicit')
 iterations=0
 while dt.datetime.now(dt.timezone.utc)<elt.DEADLINE-dt.timedelta(minutes=8):
  iterations+=1;work=0
  try:
   capacity=elt.preflight()
   if min(capacity['physical_headroom'],capacity['allocation_headroom'])<16*1048576:
    elt.save('COLLECTION_CLOSE_REASON.json',{'at_utc':elt.utc(),'reason':'Remaining live headroom reserved for at most16MiB consolidated close; no further acquisition transfer','resource':capacity,'final_close_is_same_task':True});break
   work+=extra_jobs()
   # Source/region opportunity is rotated in the same single writer.
   for sid in ['trinity_news','beaver' if iterations%2 else 'mancunion','green_left','mit_tech','otago_daily_times']:
    geo=extract_load.ADAPTERS[sid]['stratum'];st=elt.state()
    if st['strata'][geo]['article']>=400:continue
    performed=perform_pair(sid);work+=performed
    if performed:continue
    if elt.effective_count(st,geo,'discovery')>=200:continue
    if sid=='trinity_news' and progress['trinity']<len(tr_urls):
     sitemap(tr_urls[progress['trinity']],sid);progress['trinity']+=1;work+=1
    elif sid=='mancunion' and progress['manc']<len(m_urls):
     sitemap(m_urls[progress['manc']],sid);progress['manc']+=1;work+=1
    elif sid=='beaver':
     np=elt.OWN/'BEAVER_NEXT_PAGE.json'
     next_page=json.loads(np.read_text()).get('url') if np.exists() else 'https://thebeaverlse.co.uk/wp-json/wp/v2/posts?per_page=100&order=asc&orderby=date&after=1987-12-31T23:59:59&before=2026-09-22T00:00:00&context=embed&status=publish'
     if next_page:beaver_metadata(next_page);work+=1
    elif sid=='green_left':
     ip=elt.OWN/'GL_ISSUE_QUEUE.json';issues=json.loads(ip.read_text()) if ip.exists() else [];cov=elt.coverage();processed=set(json.loads((elt.OWN/'GL_ISSUES_PROCESSED.json').read_text())) if (elt.OWN/'GL_ISSUES_PROCESSED.json').exists() else set()
     available=[i for i in issues if i['url'] not in processed and cov.get(('AU',i['month']),0)<2]
     if available:
      i=min(available,key=lambda i:(cov.get(('pooled',i['month']),0)>=2,i['publication_date']));gl_issue(i);processed.add(i['url']);elt.save('GL_ISSUES_PROCESSED.json',sorted(processed));work+=1
     elif progress['gl']<len(gl_pages):gl_index(gl_pages[progress['gl']]);progress['gl']+=1;work+=1
    elif sid=='mit_tech' and progress['tech']<len(tech_urls):
     # Skip accepted issue/month density where its US month already passes.
     issue_html(tech_urls[progress['tech']]);progress['tech']+=1;work+=1
    elt.save('DISCOVERY_PROGRESS.json',progress)
   if elt.cumulative()-last_checkpoint>=elt.SCOPE['incremental_checkpoint_bytes'] or iterations%12==0:
    snapshot('retained-byte/rotation checkpoint');last_checkpoint=elt.cumulative()
   if not work:
    snapshot('native queues currently exhausted; waiting for other evidenced route queue')
    print('PAUSED_FOR_ADDITIONAL_EVIDENCED_QUEUES',flush=True);break
  except RuntimeError as e:
   elt.append('EXECUTION_STOPS.jsonl',{'at_utc':elt.utc(),'reason':str(e)})
   if 'resource_stop' in str(e) or 'fixed_deadline' in str(e):break
  except Exception as e:
   elt.append('EXECUTION_ERRORS.jsonl',{'at_utc':elt.utc(),'error':repr(e)});print('ERROR',repr(e),flush=True);break
 try:snapshot('run yield')
 except RuntimeError as error:elt.append('EXECUTION_STOPS.jsonl',{'at_utc':elt.utc(),'phase':'closing checkpoint capacity','reason':str(error),'no_further_acquisition':True})
if __name__=='__main__':run()
