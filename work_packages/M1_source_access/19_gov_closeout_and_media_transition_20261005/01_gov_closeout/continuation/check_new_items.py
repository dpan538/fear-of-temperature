"""One changed-tranche check of new saved PDFs only. No network or database."""
import csv
import fcntl
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
OWNER=HERE.parent;ROOT=OWNER.parents[3];WP=ROOT/'work_packages/M1_source_access'
LOCK=WP/'14_structural_validation_20261004/control/heavy_io.lock'
REL=WP/'15_targeted_repairs_and_supplementation_20261004/04_targeted_supplementation/selected_work_item_relationships.csv'


def read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def csvout(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def convert(value):
    d,m,y=map(int,value.split('.'))
    try:return date(y,m,d).isoformat()
    except ValueError:return ''


def printed_dates(text):
    cover=re.findall(r'Brussels,\s*(\d{1,2}\.\d{1,2}\.\d{4})',text,re.I)
    oj=re.findall(r'(\d{1,2}\.\d{1,2}\.\d{4})\s+EN\s+Official Journal',text,re.I)
    oj+=re.findall(r'Official Journal of the European Union\s+(\d{1,2}\.\d{1,2}\.\d{4})',text,re.I)
    values=sorted(set(convert(d) for d in cover+oj)-{''})
    return values,('COM cover Brussels date' if cover else ('Official Journal issue header/footer' if oj else 'unresolved'))


def main():
    execution=json.loads((HERE/'B_CORRECTED/RESULT.json').read_text())
    assert (HERE/'AU_ORIGINALS/RESULT.json').is_file()
    assert json.loads((HERE/'B_CORRECTED/PHASE_HTTP_STATE.json').read_text())['halted'] is True
    assert json.loads((HERE/'AU_ORIGINALS/PHASE_HTTP_STATE.json').read_text())['halted'] is True
    targets=[r for r in execution['outcomes'] if r['status']=='downloaded_candidate_original']
    assert len(targets)==27 and all('continuation/B_CORRECTED/raw/' in r['raw_path'] for r in targets)
    relations=read(REL);old=read(OWNER/'CHANGED_ITEM_TEXT_SHAPE.csv')
    old_sha={r['raw_sha256'] for r in old}
    shapes=[];pages=[];evidence=[];thumbs=[]
    (HERE/'evidence').mkdir(exist_ok=True)
    with LOCK.open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for i,row in enumerate(targets,1):
            path=ROOT/row['raw_path'];before=path.stat()
            assert not path.is_symlink() and path.resolve().is_relative_to((HERE/'B_CORRECTED/raw').resolve())
            raw=path.read_bytes()  # one body read, used for hash/signature/PDF processing
            digest=hashlib.sha256(raw).hexdigest()
            assert digest==row['sha256'] and len(raw)==row['byte_count'] and len(raw)<=int(row['max_object_bytes'])
            assert raw[:1024].lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'%PDF-')
            cp=HERE/'B_CORRECTED/requests'/f"{hashlib.sha256(row['request_url'].encode()).hexdigest()}.json"
            request=json.loads(cp.read_text())
            assert request['sha256']==digest and request['raw_path']==row['raw_path'] and request['item_uri']==row['item_uri']
            selected={r['item_uri'] for r in relations if r['parent_id']==row['parent_id'] and r['manifestation_uri']==row['manifestation_uri']}
            alternatives={r['item_uri'] for r in relations if r['parent_id']==row['parent_id']}
            assert row['item_uri'] in selected
            r={k:row[k] for k in ['parent_id','expression_uri','manifestation_uri','item_uri','publication_dates','format','request_url','raw_path']}
            r.update(sequence_new=i,source_id='EU_CELLAR_COM',jurisdiction='EU_supranational',
              source_frame='COM act_preparatory ENG frozen metadata class',publication_month=row['publication_dates'][:7],
              metadata_date_role='saved official CDM work_date_document, unchanged',
              metadata_observed_at_utc='2026-09-26T14:39:16.266001+00:00 (frozen Work frame; narrower relation receipt retained)',
              raw_sha256=digest,raw_bytes=len(raw),raw_sha256_rechecked=digest,sha256_matches=True,signature_pdf=True,
              request_checkpoint_path=str(cp.relative_to(ROOT)),request_checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),
              requested_at_utc=request['requested_at_utc'],retrieved_at_utc=request['retrieved_at_utc'],
              observed_content_type=request['response_headers'].get('Content-Type',''),
              request_accept=request['request_headers']['Accept'],
              content_version_etag=request['response_headers'].get('ETag',''),
              content_version_last_modified=request['response_headers'].get('Last-Modified',''),
              selected_manifestation_distinct_items=len(selected),all_distinct_item_alternatives=len(alternatives),
              observed_selected_Item_count_for_Work=1,raw_sha256_matches_old_Item=digest in old_sha,
              new_parent_created=False,formal_ingestion_performed=False,parent_statistics_eligible=False,
              length_unit='one saved selected PDF Item, all text-layer characters incl. cover/header/footnote',
              ocr_status='not run',visual_check='pending first-page inspection; other pages not visually inspected',
              complete_work_status='pending component and selected-Work content-boundary acceptance',
              historical_version_equivalence='unknown; later retrieval/HTTP version metadata not proof of original wording',
              body_identity_status='official frozen WEMI links selected Item to Work; no saved Work title/reference for independent printed-reference comparison',
              provenance_class='official archival reproduction; recorded utterance/author attribution requires passage mapping',
              rights_boundary='official public stream; document-specific third-party rights/redistribution unassessed')
            try:
                doc=pdfium.PdfDocument(raw);assert len(doc)>0
                texts=[];localpages=[]
                metadata=doc.get_metadata_dict()
                for n in range(len(doc)):
                    page=doc[n];tp=page.get_textpage();text=tp.get_text_range();texts.append(text)
                    pr={'item_uri':row['item_uri'],'pdf_page_number':n+1,'text_codepoints':len(text),
                        'nonspace_codepoints':sum(not c.isspace() for c in text),'whitespace_tokens':len(text.split()),
                        'empty_text':not text.strip(),'width_pt':round(page.get_width(),3),'height_pt':round(page.get_height(),3),
                        'unit':'PDF page, not independent parent'}
                    pages.append(pr);localpages.append(pr)
                    if n==0:
                        thumb=page.render(scale=.75).to_pil().convert('RGB');thumb.thumbnail((440,620));thumbs.append((i,thumb.copy()))
                    tp.close();page.close()
                doc.close()
                body='\n'.join(texts);first=' '.join(texts[0].split());dates,role=printed_dates(first)
                com=list(dict.fromkeys(re.findall(r'(?:COM|SWD|JOIN)\s*\(\s*\d{4}\s*\)\s*\d+(?:\s*final)?',first)))
                oj=list(dict.fromkeys(re.findall(r'\d{4}/[A-Z]\s*\d+/\d+',first)))
                genre='printed COM/SWD/JOIN document' if com else ('Official Journal notice/list/communication/corrigendum rendition' if oj or 'Official Journal of the European Union' in first else 'unresolved printed form')
                comparison=('agrees_with_saved_Work_day' if dates==[row['publication_dates']] else
                            ('conflict' if len(dates)==1 else 'unresolved_or_multiple_printed_dates'))
                r.update(pdf_parse_status='parsed',pdf_page_count=len(texts),text_codepoints=len(body),
                    nonspace_codepoints=sum(not c.isspace() for c in body),whitespace_tokens=len(body.split()),
                    empty_text_page_count=sum(p['empty_text'] for p in localpages),replacement_codepoint_count=body.count('\ufffd'),
                    text_layer_status='all_pages_nonempty_text_layer' if all(not p['empty_text'] for p in localpages) else 'one_or_more_empty_text_pages',
                    ocr_need='no empty text pages' if all(not p['empty_text'] for p in localpages) else 'empty-page image/blank/OCR distinction unresolved',
                    printed_issue_date=';'.join(dates),printed_date_role=role,issue_date_comparison=comparison,
                    printed_references=';'.join(com+oj),first_page_multiple_OJ_notice_refs=len(oj)>1,
                    printed_heading_excerpt=first[:1000],observed_genre=genre,
                    pdf_metadata_json=json.dumps(metadata,ensure_ascii=False),
                    PDF_metadata_time_role='file creation/modification only; not issue date',
                    analysis_month_support='saved metadata supports2015-01; printed-day comparison separately pending',
                    required_component_coverage='unestablished; no extra Items downloaded')
                evidence.append({'sequence_new':i,'item_uri':row['item_uri'],'evidence_page':1,'first_page_text':texts[0],
                                 'printed_issue_dates_candidates':dates,'date_role':role,'printed_references':com+oj,
                                 'scope':'first-page identity/date/structure evidence, not corpus ingestion'})
            except Exception as e:
                r.update(pdf_parse_status='failed',pdf_parse_error=type(e).__name__+': '+str(e),pdf_page_count=0,
                         text_layer_status='unresolved',issue_date_comparison='unresolved')
            assert path.stat().st_mtime_ns==before.st_mtime_ns and path.stat().st_size==before.st_size
            shapes.append(r)
            del raw
        fcntl.flock(lock,fcntl.LOCK_UN)
    csvout('CHANGED_ITEM_TEXT_SHAPE.csv',shapes);csvout('CHANGED_PDF_PAGE_SHAPE.csv',pages)
    (HERE/'evidence/FIRST_PAGE_IDENTITY.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    for batch in range((len(thumbs)+9)//10):
        sheet=Image.new('RGB',(2300,1360),'white');draw=ImageDraw.Draw(sheet)
        for j,(seq,thumb) in enumerate(thumbs[batch*10:(batch+1)*10]):
            x,y=j%5*460,j//5*680;draw.text((x+8,y+8),f'New Item {seq:02d} - first page',fill='black');sheet.paste(thumb,(x+8,y+35))
        sheet.save(HERE/f'evidence/FIRST_PAGES_{batch+1:02d}.png')
    result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'new_Items':len(shapes),
            'new_raw_bytes_rechecked':sum(r['raw_bytes'] for r in shapes),'all_new_raw_hashes_match':True,
            'old_20_text_or_PDF_rereads_in_this_check':0,'raw_modified':False,
            'pdf_parse_status_counts':dict(Counter(r['pdf_parse_status'] for r in shapes)),
            'pdf_pages':len(pages),'empty_text_pages':sum(p['empty_text'] for p in pages),
            'printed_date_comparison_counts':dict(Counter(r['issue_date_comparison'] for r in shapes)),
            'new_unique_raw_sha256':len({r['raw_sha256'] for r in shapes}),
            'new_sha256_matches_old_Item_count':sum(r['raw_sha256_matches_old_Item'] for r in shapes),
            'multiple_selected_manifestation_Item_count':sum(r['selected_manifestation_distinct_items']>1 for r in shapes),
            'multi_OJ_notice_first_pages':sum(r.get('first_page_multiple_OJ_notice_refs',False) for r in shapes),
            'visual_first_page_check':'pending','complete_Work_acceptance':'not established',
            'certified_parent_length_rows':0,'production_extraction_started':False,
            'network_requests':0,'database_queries':0,'database_writes':0,'corpus_wide_reads':False}
    (HERE/'CHANGED_ITEM_CHECK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
