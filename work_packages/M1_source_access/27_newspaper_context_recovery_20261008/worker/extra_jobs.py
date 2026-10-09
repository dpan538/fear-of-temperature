"""Bounded original-print recovery jobs, executed only by the sole ELT writer."""
import json
import elt

def pdf_release_ok(head,existing):
 length=head.get('hops',[{}])[-1].get('content_length')
 size=int(length) if length and str(length).isdigit() else None
 return bool(head.get('status')=='saved_headers' and size and size<=elt.SCOPE['historical_pdf_raw_cap_bytes'] and len(existing)<elt.SCOPE['max_new_historical_issues'] and sum(r.get('raw_bytes',0) for r in existing)+size<=elt.SCOPE['new_historical_pdf_aggregate_raw_cap_bytes'])

def perform():
 path=elt.OWN/'EXTRA_JOBS.json'
 if not path.exists():return 0
 jobs=json.loads(path.read_text());dp=elt.OWN/'EXTRA_JOBS_DONE.json';done=set(json.loads(dp.read_text())) if dp.exists() else set()
 for job in jobs:
  if job['job_id'] in done:continue
  if job['kind']=='historical_pdf':
   url=job['url']
   if url in elt.OLD_STOPS or elt.urlsplit(url).hostname in elt.state()['access_stops']:
    elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'reason':'Preserved inherited exact-target or host stop','new_HTTP_attempt':False,'original_date_and_article_mapping':'Unavailable on this blocked route'})
    done.add(job['job_id']);elt.save('EXTRA_JOBS_DONE.json',sorted(done));return 1
   head=elt.fetch(url,'mit_tech','US','discovery',job['publication_date_basis'],method='HEAD',extra={'necessary_pages':job['necessary_pages'],'derivative_footprint_cap_bytes':job['derivative_footprint_cap_bytes']})
   ip=elt.OWN/'NEW_PDF_ISSUES.json';existing=json.loads(ip.read_text()) if ip.exists() else []
   if pdf_release_ok(head,existing):
    plan=dict(job,observed_content_length_bytes=int(head['hops'][-1]['content_length']),HEAD_receipt=head,frozen_before_transfer_at_utc=elt.utc(),printed_date_confirmation_pending=True)
    elt.save('pdf_plans/'+job['job_id']+'.json',plan)
    rec=elt.fetch(url,'mit_tech','US','article',plan,cap=elt.SCOPE['historical_pdf_raw_cap_bytes'],extra={'kind':'historical_pdf','native_issue_URL':job['native_issue_URL'],'publisher_date_hint':job['publisher_date_hint'],'necessary_pages':job['necessary_pages'],'derivative_footprint_cap_bytes':job['derivative_footprint_cap_bytes']})
    existing.append(rec);elt.save('NEW_PDF_ISSUES.json',existing)
    elt.load({'source_id':'mit_tech','source_url':url,'publication_date':None,'publisher_date_hint':job['publisher_date_hint'],'printed_date_confirmation_pending':True,'pdf_plan_reference':'pdf_plans/'+job['job_id']+'.json','raw_reference':rec.get('raw_reference'),'raw_sha256':rec.get('raw_sha256'),'necessary_pages':job['necessary_pages']},'','pending_original_article_mapping_'+rec['status'])
   else:elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'HEAD_receipt':head,'reason':'Unobserved/over-limit original size, issue or aggregate ceiling; no original transferred'})
  elif job['kind']=='issue_pdf_chain':
   from bs4 import BeautifulSoup
   import re
   url=job['native_issue_URL'];ip=elt.OWN/'NEW_PDF_ISSUES.json';existing=json.loads(ip.read_text()) if ip.exists() else []
   plan_path=elt.OWN/'pdf_plans'/(job['job_id']+'.json')
   if url in elt.OLD_STOPS or elt.urlsplit(url).hostname in elt.state()['access_stops']:
    elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'reason':'Inherited native issue stop; no request'})
    done.add(job['job_id']);elt.save('EXTRA_JOBS_DONE.json',sorted(done));return 1
   if len(existing)>=elt.SCOPE['max_new_historical_issues']:
    elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'reason':'Historical original issue ceiling; no request'})
   else:
    page=elt.fetch(url,'mit_tech','US','discovery',job,extra={'native_target_identity':url})
    wrapper_url=None;raw_url=None
    if page['status']=='saved':
     soup=BeautifulSoup(elt.read_payload(page['raw_reference']),'html.parser')
     links=[elt.urljoin(url,a['href']) for a in soup.select('a[href]') if a['href'].endswith('/pdf')]
     wrapper_url=next((v for v in links if v.startswith(url+'/pdf')),None)
    if wrapper_url and wrapper_url not in elt.OLD_STOPS:
     wrapper=elt.fetch(wrapper_url,'mit_tech','US','discovery',{'observed_link_in':page,'printed_date_pending':True})
     if wrapper['status']=='saved':
      frame=BeautifulSoup(elt.read_payload(wrapper['raw_reference']),'html.parser').select_one('iframe[src]')
      if frame:
       observed=elt.urljoin(wrapper_url,frame['src'])
       if observed.startswith('https://s3.amazonaws.com/thetech-production/issues/pdfs/') and re.search(r'/original/tech_pdf\.pdf(?:\?|$)',observed):raw_url=observed
    if raw_url and raw_url not in elt.OLD_STOPS and elt.urlsplit(raw_url).hostname not in elt.state()['access_stops']:
     head=elt.fetch(raw_url,'mit_tech','US','discovery',{'wrapper_link_receipt':wrapper,'printed_date_pending':True},method='HEAD')
     if pdf_release_ok(head,existing):
      plan=dict(job,observed_original_URL=raw_url,observed_content_length_bytes=int(head['hops'][-1]['content_length']),HEAD_receipt=head,native_issue_receipt_reference='receipts/'+page['target_id']+'.json',frozen_before_original_transfer_at_utc=elt.utc(),printed_date_confirmation_pending=True)
      elt.save('pdf_plans/'+job['job_id']+'.json',plan)
      rec=elt.fetch(raw_url,'mit_tech','US','article',plan,cap=elt.SCOPE['historical_pdf_raw_cap_bytes'],extra={'kind':'historical_pdf','native_target_identity':url,'native_issue_URL':url,'necessary_pages':job['necessary_pages'],'derivative_footprint_cap_bytes':job['derivative_footprint_cap_bytes']})
      existing.append(rec);elt.save('NEW_PDF_ISSUES.json',existing)
      elt.load({'source_id':'mit_tech','source_url':url,'publication_date':None,'printed_date_confirmation_pending':True,'pdf_plan_reference':'pdf_plans/'+job['job_id']+'.json','raw_reference':rec.get('raw_reference'),'raw_sha256':rec.get('raw_sha256')},'','pending_original_article_mapping_'+rec['status'])
     else:elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'HEAD_receipt':head,'reason':'Original size/issue/aggregate release condition not met; no original transfer'})
    else:elt.append('PDF_ROUTE_STOPS.jsonl',{'at_utc':elt.utc(),'job_id':job['job_id'],'reason':'No eligible observed original locator; inherited stops preserved','native_issue_receipt':page})
  elif job['kind']=='staged_article':
   import extract_load
   extract_load.acquire(job['target']) # Existing saved receipt; no renewed native target charge.
  elif job['kind']=='mapped_article':
   record=dict(job['record']);body=(elt.REPO/record['body_reference']).read_text();assert body and elt.eligible(record['publication_date'])
   elt.load(record,body,job.get('status','confirmed_complete'))
  else:raise ValueError('Unsupported bounded recovery job '+job['kind'])
  done.add(job['job_id']);elt.save('EXTRA_JOBS_DONE.json',sorted(done));return 1
 return 0
