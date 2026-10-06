"""Whole-issue acquisition; article segmentation is explicitly a later step."""
import json
import urllib.parse
from bs4 import BeautifulSoup
from public_capture import capture,ROOT

plan=json.loads((ROOT/'HISTORICAL_PDF_PLAN.json').read_text())
frame_path=ROOT/'HISTORICAL_PDF_FRAME.json'
frames=json.loads(frame_path.read_text()) if frame_path.exists() else []
for url in plan['indexes']:
    raw,receipt=capture(url,'history_index','mit_tech_history')
    soup=BeautifulSoup(raw,'html.parser')
    link=next((a for a in soup.select('a[href]') if a.get_text(' ',strip=True)=='View PDF'),None)
    if link is None:print(json.dumps(dict(index=url,state='no observed PDF link')),flush=True);continue
    wrapper=urllib.parse.urljoin(url,link['href'])
    raw,wrapper_receipt=capture(wrapper,'history_wrapper','mit_tech_history')
    embed=BeautifulSoup(raw,'html.parser').select_one('iframe[src]')
    if embed is None:print(json.dumps(dict(wrapper=wrapper,state='no observed PDF iframe')),flush=True);continue
    pdf=urllib.parse.urljoin(wrapper,embed['src'])
    if not any(f['pdf_url']==pdf for f in frames):
        frames.append(dict(index_url=url,index_receipt=receipt['request_id'],wrapper_url=wrapper,
            wrapper_receipt=wrapper_receipt['request_id'],pdf_url=pdf,unit='whole issue; independent article count unresolved',
            catalog_volume_year_provisional=int(url.split('/')[-2])+1880,printed_date_check='pending',
            selection='native first issue in the next chronological volume; retained publisher embed',
            topic_or_emotion_filter=None,failed_target_replacement=False))
        frame_path.write_text(json.dumps(frames,indent=2)+'\n')
    raw,receipt=capture(pdf,'history_pdf','mit_tech_history')
    print(json.dumps(dict(index=url,url=pdf,status=receipt['status'],raw_bytes=receipt['raw_bytes'])),flush=True)
