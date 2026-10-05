"""Read exported PDF/HTML and render all pages for visual inspection."""
from pathlib import Path
import sys,re,json
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'.runtime'))
import fitz
from PIL import Image,ImageOps,ImageDraw
out=R/'qa/revision_render';out.mkdir(exist_ok=True)
d=fitz.open(R/'thesis_proposal.pdf');texts=[];issues=[]
for n,p in enumerate(d,1):
 texts.append(p.get_text())
 pix=p.get_pixmap(matrix=fitz.Matrix(1.65,1.65),alpha=False)
 pix.save(out/f'page-{n:02}.png')
 for b in p.get_text('dict')['blocks']:
  for line in b.get('lines',[]):
   for span in line['spans']:
    x0,y0,x1,y1=span['bbox']
    if x0<-1 or y0<-1 or x1>p.rect.width+1 or y1>p.rect.height+1:issues.append({'page':n,'text':span['text'],'bbox':span['bbox']})
 for bad in ['\ufffd','\x00']:
  if bad in texts[-1]:issues.append({'page':n,'bad_character':repr(bad)})
for start in range(0,len(d),6):
 contact=Image.new('RGB',(1050,1560),'#dce2e7');draw=ImageDraw.Draw(contact)
 for j,n in enumerate(range(start,min(start+6,len(d)))):
  im=Image.open(out/f'page-{n+1:02}.png');im.thumbnail((340,480))
  x=(j%3)*350+(350-im.width)//2;y=(j//3)*520+25
  contact.paste(im,(x,y));draw.text((x,y-18),f'Physical page {n+1}',fill='black')
 contact.save(out/f'contact-{start//6+1}.png')
raw=(R/'thesis_proposal.md').read_text();pdftext='\n'.join(texts)
keys={k for group in re.findall(r'\[@[^\]]+\]',raw) for k in re.findall(r'@(\w+)',group)};bibkeys=set(re.findall(r'^@\w+\{([^,]+)',(R/'references.bib').read_text(),re.M))
report={'pages':len(d),'bounds_or_encoding_issues':issues,'citation_keys_match':keys==bibkeys,'citation_count':len(keys),'figures':re.findall(r'^!\[(Figure \d+)',raw,re.M),'equation_count':raw.count('<!-- equation:'),'ai_statement_pages':[i+1 for i,t in enumerate(texts) if 'Topic exploration' in t and 'AI' in t],'no_abstract_page':not any(t.startswith('Abstract') for t in texts),'time_requirement':all(x in pdftext for x in ['10-20 hours/week','28 February 2027']),'pdf_text':pdftext}
(R/'qa/revision_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='pdf_text'},indent=2))
