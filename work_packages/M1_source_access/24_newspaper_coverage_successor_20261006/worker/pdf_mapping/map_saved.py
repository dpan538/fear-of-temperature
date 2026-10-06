"""Three named article mappings from saved issues; all coordinates trace to scans."""
import datetime as dt,fcntl,json,sys
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core

CONFIG=[
 {'date':'1989-02-07','title':'CFYP report: End freshman 2nd term P/F','byline':'Niraj S. Desai',
  'segments':[(1,[51,318,225,914]),(1,[232,615,402,915]),(14,[80,113,253,232]),(14,[262,110,434,232]),(14,[439,110,612,595]),(14,[614,108,789,596]),(14,[792,108,965,601])],
  'continuation':'First-page explicit Please turn to page14; page14 CFYP report advocates elimination of frosh P/F and Continued from page1. Photo/caption and separate SEWG story excluded.'},
 {'date':'1990-02-06','title':'Council adopts porn policy','byline':'Andrea Lamberti',
  'segments':[(1,[45,285,320,781]),(1,[325,285,585,782])],
  'continuation':'Complete two-column first-page report ending in Keyser quotation; separate shaded policy excerpt and UA activity-fee report excluded. Page17 is an advertisement, not a continuation.'},
 {'date':'1991-02-01','title':'Joel Moses new engineering dean','byline':'Brian Rosenberg',
  'segments':[(1,[42,503,205,717]),(1,[208,315,372,717]),(2,[62,665,226,1433])],
  'continuation':'First-page Please turn to page2; page2 Joel Moses named dean / Continued from page1. Photo/caption and neighbouring protests, Media Lab and employment advertisement excluded.',
  'first_page_ocr':'1991_page1_VISION_OCR.json'}
]

def vision_clip(rows,rect,width,height):
    kept=[]
    for row in rows:
        b=row['box_bottom_left_normalized'];x=(b[0]+b[2])*width/2;y=(1-(b[1]+b[3])/2)*height
        if rect[0]<=x<=rect[2] and rect[1]<=y<=rect[3]:kept.append((y,x,row['text']))
    return '\n'.join(t for y,x,t in sorted(kept))

def main():
    issues=json.loads((core.BASE/'ISSUE_CONTAINER_MANIFEST.json').read_text())
    core.save('pdf_mapping/MAPPING_PLAN_v1.json',{'frozen_at_utc':core.utc(),'mappings':CONFIG,'coordinate_system':'PDF page points, top-left origin; page numbers one-based','selection':'First top-left native front-page article for each existing issue-only month, one per month; 1988 existing mapped article reused by reference','mapper_sha256':core.sha(__file__)})
    records=[]
    old=json.loads((core.BASE/'EARLY_ARTICLE_RECORD.json').read_text())
    core.save('pdf_mapping/EXISTING_1988_REFERENCE.json',{'baseline_reference':str(core.BASE/'EARLY_ARTICLE_RECORD.json'),'record':old,'new_parent_contribution':0,'no_redownload_or_body_copy':True})
    for config in CONFIG:
        issue=next(i for i in issues if i['publication_date']==config['date'])
        with core.LOCK.open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);budget=core.material_check(262144)
            doc=fitz.open(core.BASE/issue['raw_path']);parts=[];segments=[]
            for number,rect in config['segments']:
                page=doc[number-1]
                assert fitz.Rect(rect) in page.rect
                if number==1 and config.get('first_page_ocr'):
                    ocr=json.loads((Path(__file__).parent/config['first_page_ocr']).read_text())
                    text=vision_clip(ocr,rect,page.rect.width,page.rect.height);method='local macOS Vision OCR on saved page render; native OCR unusable'
                else:text=page.get_text(clip=fitz.Rect(rect),sort=True);method='geometrically clipped publisher native OCR'
                assert text.strip()
                parts.append(text.strip());segments.append({'page_number':number,'rect_pdf_points_top_left':rect,'ocr_method':method,'text_sha256':core.digest(text.strip().encode())})
            doc.close()
            body='\n\n[CONTIGUOUS ARTICLE SEGMENT]\n\n'.join(parts)
            uid=issue['index_url']+'#article-'+core.digest(config['title'].encode())[:12]
            body_path=core.OWN/'bodies'/('mapped_'+config['date']+'.txt');body_path.parent.mkdir(exist_ok=True);body_path.write_text(body)
        record=dict(unit_id=uid,url=uid,source_id='mit_tech',source='The Tech',stratum='US',country='US',edition='MIT English student newspaper archival print issue',source_frame='student newspaper supplement',
            unit_kind='mapped_article',title=config['title'],byline=config['byline'],publication_date=config['date'],raw_path=str(core.BASE/issue['raw_path']),raw_sha256=issue['raw_sha256'],body_path=str(body_path.relative_to(core.OWN)),body_sha256=core.digest(body.encode()),
            retrieved_at_utc=issue['retrieved_at_utc'],derived_at_utc=core.utc(),content_version_time=issue.get('content_version_last_modified'),readable=True,state='mapped_readable_article_OCR_uncertainty_retained',
            segments=segments,continuation_evidence=config['continuation'],printed_date_evidence='Named retained first-page render visually checked; masthead agrees with accepted issue receipt',
            mapper_sha256=core.sha(__file__),mapping_plan_sha256=core.sha(core.OWN/'pdf_mapping/MAPPING_PLAN_v1.json'),body_completeness='Article span visually traced across listed columns/pages; transcription has uncorrected OCR uncertainties, not a clean verbatim edition',
            ocr_uncertainty='Noisy characters, line breaks and end-line hyphens retained. 1991 first page uses new local image OCR; boxes and native scan remain auditable. No numeric source-confidence rank.',
            independent_parent_status='single named/bylined article with explicit geometric/continuation mapping; original-story/syndication independence remains unassessed',
            issue_parent_reference=issue['index_url'],provenance='archival reproduction of original student-newspaper utterance',historical_body_equivalence='original issue scan; scan-version time remains separate',semantic_labels_executed=False,length_filter_used=False,material_write_budget=budget)
        record['new_versions_inserted']=core.stage(record);records.append(record)
    core.save('MAPPED_ARTICLE_MANIFEST.json',{'derived_at_utc':core.utc(),'new_mapped_parents':records,'existing_1988_parent_reused_reference':'pdf_mapping/EXISTING_1988_REFERENCE.json','new_raw_bytes':0,'whole_issue_remainder':'unsegmented; pages/segments not additional article parents','no_old_raw_hash_scan':'Accepted immutable issue raw digests reused by reference; only selected pages read'})
    print(json.dumps({'new_mapped_article_parents':len(records),'new_readable_months':[r['publication_date'][:7] for r in records],'body_chars':[len((core.OWN/r['body_path']).read_text()) for r in records],'old_raw_redownloads':0}))

if __name__=='__main__':main()
