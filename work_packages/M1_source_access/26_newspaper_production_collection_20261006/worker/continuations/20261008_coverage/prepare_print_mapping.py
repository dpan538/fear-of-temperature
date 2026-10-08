"""Prepare visually traced original pieces; no network or formal database writes."""
import fcntl,fitz,json,sys
from pathlib import Path
import elt
def prepare(specs):
 with elt.LOCK.open('a+b') as h:
  fcntl.flock(h,fcntl.LOCK_EX);elt.preflight(32*1024**2);receipts={r['target']['extra']['native_issue_URL']:r for r in json.loads((elt.OWN/'NEW_PDF_ISSUES.json').read_text()) if r['status']=='saved'};p=elt.OWN/'EXTRA_JOBS.json';jobs=json.loads(p.read_text());keys={j['job_id'] for j in jobs};added=[]
  for spec in specs:
   url='https://thetech.com/issues/'+spec['issue'];r=receipts[url];aid='mit_tech:print:'+spec['issue'].replace('/',':')+':p'+str(spec['regions'][0][0])+':'+spec['key'];jid='mapped-new-original-'+aid
   if jid in keys:continue
   assert spec['date_visually_confirmed'] and spec['complete_article_visually_traced'] and elt.eligible(spec['publication_date']);d=fitz.open(stream=elt.read_payload(r['raw_reference']),filetype='pdf');parts=[];mapping=[]
   for n,box in spec['regions']:
    text=d[n-1].get_text(clip=fitz.Rect(box),sort=True);override=spec.get('text_overrides',{}).get(str(len(mapping)+1));derived=(elt.REPO/override).read_text() if override else text;parts.append(derived.strip());mapping.append(dict(page=n,coordinates_pdf_points=box,native_ocr=text,derived_text=derived,manual_transcription_reference=override,reading_order=len(mapping)+1))
   body=spec['title']+'\nBy '+spec['byline']+'\n\n'+'\n\n'.join(parts)+'\n';name=aid.replace(':','_');bp=elt.OWN/'bodies'/('print_'+name+'.txt');bp.write_text(body);sp=elt.OWN/'article_mapping'/('print_'+name+'.json')
   m=dict(spec,article_id=aid,regions=mapping,raw_reference=r['raw_reference'],raw_sha256=r['raw_sha256'],raw_bytes=r['raw_bytes'],request_id=r['target_id'],article_boundary_basis='Visually identified complete original piece; ordered native columns through printed closing paragraph/author note; no unrelated pieces included',extraction='Native PDF OCR; any named manual transcription override retains its original OCR and rendered-source reference. Spelling/spacing limitations retained; no topic/fear/length gate',boundary_check_at_utc=elt.utc());sp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
   rec=dict(article_id=aid,source_id='mit_tech',source_url=url,title=spec['title'],publication_date=spec['publication_date'],stratum='US',work_family_id=aid,parent_id=aid,source_frame='MIT student newspaper The Tech; printed original issue',genre=spec['genre'],provenance='archival_reproduction',byline=spec['byline'],body_reference=str(bp.relative_to(elt.REPO)),raw_reference=r['raw_reference'],raw_sha256=r['raw_sha256'],raw_bytes=r['raw_bytes'],raw_encoding=r['raw_encoding'],stored_bytes=r['stored_bytes'],stored_sha256=r['stored_sha256'],request_id=r['target_id'],mapping_reference=str(sp.relative_to(elt.REPO)),retrieved_at_utc=r['finished_at_utc'],content_version_time=r['hops'][-1].get('last_modified'),historical_body_equivalence='Dated printed original; scan upload/content version is separate; claim truth not established',retention='Complete independent original piece; native OCR limitations retained',semantic_labels_executed=False,length_filter_used=False,complete_article=True,historical_original_print=True,date_field='printed_masthead',publisher_timestamp=spec['publication_date'],native_issue_id=spec['issue'],pages=sorted(set(n for n,_ in spec['regions'])),role_attribution_limit=spec.get('role_attribution_limit'),extraction_method='Native OCR plus named manual source transcription' if spec.get('text_overrides') else 'Native PDF OCR')
   jobs.append(dict(job_id=jid,kind='mapped_article',record=rec));added.append(jid)
  jobs.sort(key=lambda j:0 if j['kind']=='mapped_article' else 1)
  t=p.with_suffix('.pending');t.write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n');t.replace(p)
  elt.append('PRINT_MAPPING_PREPARATION.jsonl',dict(at_utc=elt.utc(),jobs=added,formal_database_written_by_helper=False,sole_writer_Load=True,new_HTTP_attempts=0,preflight=elt.resource()))
  print(json.dumps(dict(prepared_article_jobs=added)))
if __name__=='__main__':prepare(json.loads(Path(sys.argv[1]).read_text()))
