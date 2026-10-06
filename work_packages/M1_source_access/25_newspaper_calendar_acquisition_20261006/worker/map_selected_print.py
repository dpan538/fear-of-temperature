"""Restore selected native original articles as whole bodies; queue the sole Load writer."""
import fcntl,json,re,fitz,sys
import elt

MAPPINGS=[
 {'asset':'000/000/086','day':'1989-05-16','key':'residence-thefts','title':'Residence thefts drop again in 1988','byline':'Andrew L. Fish','genre':'news_article','spans':[(1,[584,282,758,785]),(1,[760,280,934,768]),(13,[37,363,206,573]),(13,[210,349,384,573]),(13,[394,348,580,531])],'boundary':'Page1 two upper-right columns explicitly continue on page13; matching continuation title Campus Police report issued, three columns end in December1987; supporting charts preserved in renders and raw. Native OCR misread13 as3, corrected from visual source before counting.'},
 {'asset':'000/000/086','day':'1989-05-16','key':'institute-recycling','title':'Institute may begin recycling','byline':'Michael Gojer','genre':'news_article','spans':[(1,[49,637,219,797]),(1,[223,637,397,797]),(1,[402,637,577,1038]),(12,[39,100,207,835]),(12,[215,100,387,413]),(12,[395,100,570,313])],'boundary':'Page1 article three columns (third extending below adjacent FinBoard article) explicitly continues on12; matching continuation has three columns, ends Mills said; adjacent advertising and ring promotion excluded. FinBoard candidate remains unmapped due severe native OCR.'},
 {'asset':'000/003/285','day':'1988-10-18','key':'survey-mit-fifth','title':'Survey ranks MIT fifth among universities','byline':'Darrel Tarasewicz','genre':'news_article','spans':[(1,[74,1045,225,1331]),(1,[234,1045,386,1331]),(1,[394,1045,549,1331])],'boundary':'One independently titled/bylined article at lower-left front page in three columns, ends University of Chicago (10); no continuation cue. Upper HASS article and adjacent Graham article excluded.'},
 {'asset':'000/003/285','day':'1988-10-18','key':'kang-charges','title':'State drops Kang charges','byline':'Annabelle Boyd','genre':'news_article','spans':[(1,[396,219,548,546]),(1,[555,219,710,774]),(1,[716,219,871,546]),(2,[406,655,558,743])],'boundary':'Page1 three upper-right columns explicitly continue on2; the small matching final paragraph under State drops case against Thomas Kang ends he said. Adjacent HASS/Graham stories, photo caption and notices excluded.'},
 {'asset':'000/000/142','day':'1990-04-20','key':'faculty-arrests','title':'Faculty denounces arrests','byline':'Niraj S. Desai','genre':'news_article','spans':[(1,[84,615,248,725]),(1,[83,988,246,1105]),(1,[255,615,419,787]),(1,[430,615,591,787]),(14,[152,150,322,1060]),(14,[324,128,492,1063]),(14,[500,129,664,396]),(14,[672,128,836,397])],'boundary':'Page1 three source columns with first column interrupted by PaulGray photo explicitly continue on14; matching continuation article includes arrest discussion, calendar-change and other-business subheadings under Faculty votes in calendar changes, ends teaching. No second byline or new original article boundary within this continuation. Adjacent UA/ROTC/housing stories and advertisements excluded.'},
 {'asset':'000/000/142','day':'1990-04-20','key':'remember-holocaust','title':'We must remember Holocaust','byline':'Michael Franklin','genre':'opinion_column','spans':[(4,[513,199,770,1510]),(4,[771,200,1024,1480])],'boundary':'One titled/bylined opinion column on page4 in two columns with a source photo inset; ends Remember. Author-description footer and staff masthead excluded. Photo/caption retained in raw/render and sidecar; no continuation cue.'}
]

def main():
 issues=json.loads((elt.OWN/'NEW_PDF_ISSUES.json').read_text());results=[]
 with elt.LOCK.open('a+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);elt.preflight(4*1048576);jobs_path=elt.OWN/'EXTRA_JOBS.json';jobs=json.loads(jobs_path.read_text());known={j['job_id'] for j in jobs}
  for item in MAPPINGS:
   if '--corrections-only' in sys.argv and item['key'] not in ['residence-thefts','kang-charges']:continue
   rec=next(r for r in issues if '/'+item['asset']+'/' in r['url']);d=fitz.open(elt.REPO/rec['raw_reference']);parts=[];spans=[];offset=0
   for n,rect in item['spans']:
    part=d[n-1].get_text(clip=fitz.Rect(rect),sort=True).strip()
    part=re.sub(r'^\(?Continued from page [I1]\)?\s*','',part,flags=re.I)
    if item['key']=='kang-charges':part=re.sub(r'Literature turns some students\s*away','',part);part=re.sub(r'\ndents\s+away\s*$','',part)
    if item['key']=='residence-thefts':part=re.sub(r'^(?:p g|U988)\s*\n','',part)
    if item['key']=='remember-holocaust':part=re.sub(r'^A Holocaust(?: victim)?\s*$','',part,flags=re.M)
    spans.append({'page_number':n,'rect_pdf_points_top_left':rect,'character_start':offset,'character_end':offset+len(part)});offset+=len(part)+2;parts.append(part)
   body='\n\n'.join(parts)+'\n';assetkey=item['asset'].replace('/','-');aid='mit_tech:print:asset-'+assetkey+':p'+str(item['spans'][0][0])+':'+item['key'];bh=elt.sha(body.encode());bp=elt.OWN/'bodies'/('mit_tech_print_'+assetkey+'_'+item['key']+'_'+bh[:12]+'.txt');bp.write_text(body);sidecar=elt.OWN/'pdf_mapping'/(item['day']+'_'+item['key']+'_'+bh[:12]+'.json')
   record=dict(article_id=aid,source_id='mit_tech',source='The Tech',source_url=rec['url'],raw_source_url=rec['url'],title=item['title'],byline=item['byline'],genre=item['genre'],publication_date=item['day'],stratum='US',country='US',edition='MIT English archival print student newspaper',source_frame='US student newspaper supplement; original print article',body_reference=str(bp.relative_to(elt.REPO)),body_sha256=elt.sha(body.encode()),raw_reference=rec['raw_reference'],raw_sha256=rec['raw_sha256'],retrieved_at_utc=rec['finished_at_utc'],content_version_time=rec['hops'][-1].get('last_modified'),provenance='archival reproduction of original newspaper article; native publisher asset and printed masthead verified',historical_body_equivalence='Scanned dated original print pages; digitisation/content-version time separately observed',article_boundary_evidence=item['boundary'],coordinate_system='PDF points top-left origin, one-based page',spans=spans,sidecar_reference=str(sidecar.relative_to(elt.REPO)),ocr_limit='Native OCR reused with minor errors and source line breaks; visually traced original columns, full narrative assembled as one body. No arbitrary text segmentation or generated body markers.',semantic_labels_executed=False,length_filter_used=False)
   sidecar.write_text(json.dumps(record,indent=2)+'\n');job_id='mapped_'+assetkey+'_'+item['key']+'_'+bh[:12]
   if job_id not in known:jobs.append({'job_id':job_id,'kind':'mapped_article','record':record});known.add(job_id)
   results.append({'article_id':aid,'chars':len(body),'opening':body[:170],'closing':body[-220:],'column_openings':[p[:60] for p in parts],'column_closings':[p[-65:] for p in parts]})
  pending=jobs_path.with_suffix('.pending');pending.write_text(json.dumps(jobs,indent=2)+'\n');pending.replace(jobs_path)
 print(json.dumps(results,indent=2))

if __name__=='__main__':main()
