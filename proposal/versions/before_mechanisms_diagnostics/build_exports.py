#!/usr/bin/env python3
"""Reproducible paginated Markdown → PDF, HTML and accessible TXT.
PDF layout is preflighted before export; diagrams remain vector artwork.
"""
from pathlib import Path
import re, html, json, hashlib
from urllib.parse import urlparse
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

ROOT=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('Symbols',str(ROOT/'.runtime/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf')))
FONTS=Path('/System/Library/Fonts/Supplemental')
for family,file in [('Times','Times New Roman'),('Helvetica','Arial')]:
 normal='Times-Roman' if family=='Times' else 'Helvetica'
 ital='Times-Italic' if family=='Times' else 'Helvetica-Oblique'
 bi='Times-BoldItalic' if family=='Times' else 'Helvetica-BoldOblique'
 for alias,suffix in [(normal,''),(family+'-Bold',' Bold'),(ital,' Italic'),(bi,' Bold Italic')]:
  pdfmetrics.registerFont(TTFont(alias,str(FONTS/(file+suffix+'.ttf'))))
 pdfmetrics.registerFontFamily(normal,normal=normal,bold=family+'-Bold',italic=ital,boldItalic=bi)
from build_figures import make_figures, DESCRIPTIONS
FIGURES=make_figures()
raw=(ROOT/'thesis_proposal.md').read_text()
meta=dict(re.findall(r'^(\w+): "(.*)"$',raw,re.M))
body=raw.split('---',2)[2]
keys=list(dict.fromkeys(k for group in re.findall(r'\[@[^\]]+\]',body) for k in re.findall(r'@(\w+)',group)))

bib=(ROOT/'references.bib').read_text()
entries={}
for m in re.finditer(r'^@(\w+)\{([^,]+),\n(.*?)^\}',bib,re.M|re.S):
 typ,k,fs=m.groups();e={a:b.replace('{','').replace('}','') for a,b in re.findall(r'^\s*(\w+)\s*=\s*\{(.*)\},?$',fs,re.M)};e['type']=typ
 if k in entries:raise ValueError('Duplicate key '+k)
 entries[k]=e
assert set(keys)==set(entries),set(keys)^set(entries)

from apa7 import ordered, dates, citation, reference
refkeys=ordered(entries)
refdates=dates(entries)
def cite(s,links=False):
 def sub(m):
  ks=sorted(re.findall(r'@(\w+)',m[0]),key=refkeys.index)
  groups=[]
  for k in ks:
   label=citation(k,entries,refdates)
   author,year=label.rsplit(', ',1)
   if groups and groups[-1][0]==author:groups[-1][1].append((k,year))
   else:groups.append((author,[(k,year)]))
  parts=[]
  for author,items in groups:
   labels=[]
   for j,(k,year) in enumerate(items):
    label=(author+', ' if j==0 else '')+year
    labels.append(f'<a href="#ref-{k}" color="#51247A">{html.escape(label)}</a>' if links else label)
   parts.append(', '.join(labels))
  return '('+'; '.join(parts)+')'
 return re.sub(r'\[@[^\]]+\]',sub,s)

def rich(s,pdf=True):
 s=html.escape(s,quote=False)
 s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
 s=re.sub(r'`(.+?)`',r'\1',s)
 s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
 s=cite(s,True)
 if pdf:
  s=re.sub('[✓◐●○β₂₃]',lambda m:'<font name="Symbols">'+m[0]+'</font>',s)
 return s

def plain(s):return re.sub(r'\*\*|`','',cite(s))

def ref_text(k):return reference(k,entries,refdates,markup=False)

W,H=A4;X=70.87;WIDTH=W-2*X;TOP=H-65;BOTTOM=56;AVAIL=TOP-BOTTOM
from build_equations import build as build_equations, SPECS
EQUATIONS=build_equations(WIDTH)
styles={
 'p':ParagraphStyle('body',fontName='Times-Roman',fontSize=12,leading=13.8,textColor=HexColor('#263746'),spaceAfter=8),
 'h1':ParagraphStyle('chapter',fontName='Times-Bold',fontSize=19,leading=23,textColor=HexColor('#51247A'),spaceAfter=13),
 'h2':ParagraphStyle('section',fontName='Times-Bold',fontSize=13.0,leading=16,textColor=HexColor('#51247A'),spaceBefore=7,spaceAfter=8),
 'cap':ParagraphStyle('caption',fontName='Helvetica',fontSize=8.8,leading=11.3,textColor=HexColor('#4E5C68'),spaceAfter=10),
 'cell':ParagraphStyle('cell',fontName='Helvetica',fontSize=9.0,leading=11.4,textColor=HexColor('#263746')),
 'th':ParagraphStyle('th',fontName='Helvetica-Bold',fontSize=9.0,leading=11.5,textColor=HexColor('#263746')),
 'ref':ParagraphStyle('ref',fontName='Times-Roman',fontSize=10.5,leading=12.5,spaceAfter=4,leftIndent=36,firstLineIndent=-36,textColor=HexColor('#263746')),
 'toc':ParagraphStyle('toc',fontName='Times-Roman',fontSize=10.5,leading=13.4,spaceAfter=1.5),
 'toc1':ParagraphStyle('toc1',fontName='Times-Bold',fontSize=11.1,leading=14.2,spaceBefore=6,spaceAfter=2,textColor=HexColor('#51247A')),
 'eq':ParagraphStyle('eq',fontName='Helvetica',fontSize=10.1,leading=15.8,spaceAfter=9,backColor=HexColor('#F2EEF7'),borderPadding=9),
}
# blocks retain source semantics and are rendered by each output format.
pages=[]
for m in re.finditer(r'<!-- page: (\w+) -->(.*?)(?=<!-- page:|\Z)',body,re.S):
 name,chunk=m.groups();lines=chunk.strip().splitlines();bs=[];i=0;ratios=None
 while i<len(lines):
  l=lines[i].strip()
  if not l:i+=1;continue
  if l.startswith('<!-- table:'):
   ratios=[float(x) for x in l.split('|')[1].split('-->')[0].split(',')];i+=1;continue
  if l=='<!-- contents -->':bs.append(('toc',));i+=1;continue
  if l=='<!-- bibliography -->':bs.append(('bib',));i+=1;continue
  if l.startswith('<!-- equation:'):
   key=l.split(':',1)[1].split('-->')[0].strip();eq=[];i+=1
   while i<len(lines) and lines[i].strip():eq.append(lines[i]);i+=1
   bs.append(('eq',key));continue
  if l.startswith('<!--'):raise ValueError('Unsupported directive '+l)
  mh=re.match(r'^(#{1,3}) (.*)',l)
  if mh:bs.append(('h',len(mh[1]),mh[2]));i+=1;continue
  mi=re.match(r'^!\[(.*?)\]\((.*?)\)$',l)
  if mi:bs.append(('fig',mi[1],Path(mi[2]).stem));i+=1;continue
  if l.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r':?-+:?',x) for x in cells):rows.append(cells)
    i+=1
   assert ratios and all(len(r)==len(ratios) for r in rows)
   bs.append(('table',rows,ratios));ratios=None;continue
  para=[l];i+=1
  while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||<!--|!\[)',lines[i].strip()):para.append(lines[i].strip());i+=1
  bs.append(('p',' '.join(para)))
 pages.append(dict(name=name,blocks=bs))

page_no={p['name']:i+2 for i,p in enumerate(pages)}
first_body=page_no['introduction']
def label(n):return {2:'i',3:'ii',4:'iii'}.get(n,str(n-first_body+1)) if n<first_body else str(n-first_body+1)
toc=[]
for p in pages:
 if p['name'] in ['contents','ai','abstract']:continue
 for b in p['blocks']:
  if b[0]=='h' and '(continued)' not in b[2]:toc.append((b[1],b[2],p['name'],label(page_no[p['name']])))

def P(s,style='p',ready=False):return Paragraph(s if ready else rich(s),styles[style])
def table(rows,ratios):
 cells=[]
 for i,row in enumerate(rows):
  line=[]
  for j,s in enumerate(row):
   style=ParagraphStyle('table-cell',parent=styles['th' if i==0 else 'cell'])
   ai=rows[0][0]=='AI tool usage'
   status=rows[0][j]=='Access state'
   if (ai and j>0) or status or rows[0][j]=='Rating':style.alignment=1
   if i and j==0 and rows[0][0] in ['Candidate source','Layer']:
    role=' '.join(row[:2]).lower()
    color=('#51247A' if re.search(r'\b(policy|epa|white house|unfccc)\b',role) else '#226799' if re.search(r'\b(media|nyt|guardian)\b',role) else '#087E76' if re.search(r'\b(public|reddit|letters|facebook)\b',role) else None)
    if color:style.textColor=HexColor(color)
   line.append(Paragraph(rich(s),style))
  cells.append(line)
 t=Table(cells,colWidths=[WIDTH*r for r in ratios],hAlign='LEFT')
 pad = 2 if any('R17.' in str(cell) for row in rows for cell in row) else 4
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),HexColor('#EDE8F3')),('LINEABOVE',(0,0),(-1,0),.9,HexColor('#697889')),('LINEBELOW',(0,0),(-1,0),.6,HexColor('#A3ADB7')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),('LINEBELOW',(0,-1),(-1,-1),.8,HexColor('#697889'))]))
 if rows[0][0]=='Risk':
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#E9ECEF'))]))
  for i,row in enumerate(rows[1:],1):
   t.setStyle(TableStyle([('BACKGROUND',(2,i),(2,i),HexColor('#F5EDDF' if row[2]=='High' else '#F0F2F4')),('LINEBELOW',(0,i),(-1,i),.35,HexColor('#D8DEE3'))]))
 t.spaceAfter=10;return t

def flows(bs):
 out=[]
 for b in bs:
  typ=b[0]
  if typ=='h':out.append(P(b[2],'h1' if b[1]==1 else 'h2'))
  elif typ=='p':out.append(P(b[1],'cap' if b[1].startswith('**Table ') else 'p'))
  elif typ=='table':out.append(table(b[1],b[2]))
  elif typ=='eq':out.append(EQUATIONS[b[1]])
  elif typ=='fig':
   out.append(FIGURES[b[2]]);out.append(P(b[1],'cap'))
  elif typ=='toc':
   for lev,title,target,num in toc:
    text=f'<a href="#page-{target}" color="#263746">{html.escape(title)}</a>'
    t=Table([[P(text,'toc1' if lev==1 else 'toc',True),P(num,'toc')]],colWidths=[WIDTH-28,28])
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),2 if lev==1 else 0),('BOTTOMPADDING',(0,0),(-1,-1),2)]));out.append(t)
  elif typ=='ref':
   k=b[1];s=reference(k,entries,refdates)
   q=P(s,'ref',True);q.refkey=k;out.append(q)
  else:raise ValueError('Unknown block '+str(b))
 return out

def measure(fs):
 rows=[];used=0
 for j,f in enumerate(fs):
  before=0 if j==0 else f.getSpaceBefore()
  w,h=f.wrap(WIDTH,AVAIL);used+=before+h+f.getSpaceAfter()
  rows.append(dict(type=type(f).__name__,width=round(w,2),height=round(h,2),cumulative=round(used,2)))
 return used,rows
# Pack whole APA entries without splitting an entry or forcing overflow.
refpages=[];current=[('h',1,'References')]
for k in refkeys:
 candidate=current+[('ref',k)]
 if measure(flows(candidate))[0]>AVAIL:
  refpages.append(current);current=[('h',1,'References (continued)'),('ref',k)]
 else:current=candidate
refpages.append(current)
# Balance contiguous alphabetical reference groups at the established page count.
from itertools import combinations
heights=[measure(flows([b]))[0] for b in [('ref',k) for k in refkeys]]
header=measure(flows([('h',1,'References (continued)')]))[0]
prefix=[0]
for h in heights:prefix.append(prefix[-1]+h)
best=None
for cuts in combinations(range(1,len(refkeys)),len(refpages)-1):
 bounds=(0,)+cuts+(len(refkeys),)
 hs=[header+prefix[b]-prefix[a] for a,b in zip(bounds,bounds[1:])]
 if max(hs)<=AVAIL:
  score=max(hs)-min(hs)
  if best is None or score<best[0]:best=(score,bounds)
if best:
 refpages=[[('h',1,'References' if i==0 else 'References (continued)')]+[('ref',k) for k in refkeys[a:b]] for i,(a,b) in enumerate(zip(best[1],best[1][1:]))]
pages[-1]['blocks']=refpages[0]
for i,blocks in enumerate(refpages[1:],2):pages.append(dict(name='references_'+str(i),blocks=blocks))
report=[];allflows=[]
for p in pages:
 fs=flows(p['blocks']);used,rows=measure(fs);allflows.append(fs)
 report.append(dict(page=p['name'],physical_page=len(report)+2,used=round(used,2),available=round(AVAIL,2),remaining=round(AVAIL-used,2),flowables=rows))
(ROOT/'qa').mkdir(exist_ok=True)
(ROOT/'qa'/'layout_report.json').write_text(json.dumps(report,indent=2))
errors=[(r['page'],r['remaining']) for r in report if r['remaining']<0]
if errors:raise ValueError('Page overflow: '+str(errors))

pdf=ROOT/'thesis_proposal.pdf';c=Canvas(str(pdf),pagesize=A4,pageCompression=1)
c.setTitle(meta['title']);c.setAuthor(meta['author']);c.setSubject('REIT7842 thesis project proposal')
# Original university mark and restrained cover typography.
logo=ROOT/'assets'/'UQ_Logo.png';iw,ih=Image.open(logo).size;lw=WIDTH*.6;lh=lw*ih/iw
c.drawImage(str(logo),(W-lw)/2,H-90-lh,width=lw,height=lh,mask='auto')
coverstyle=ParagraphStyle('cover',fontName='Times-Bold',fontSize=25,leading=31,alignment=1,textColor=HexColor('#51247A'))
q=Paragraph('Fear of temperature',coverstyle);_,hh=q.wrap(WIDTH,300);q.drawOn(c,X,H-280-hh)
sub=ParagraphStyle('subtitle',fontName='Times-Roman',fontSize=20,leading=26,alignment=1,textColor=HexColor('#263746'))
q=Paragraph('Computational analysis of policy, media<br/>and public climate emotions',sub);_,hh=q.wrap(WIDTH,300);q.drawOn(c,X,H-335-hh)
c.setFillColor(HexColor('#263746'));c.setFont('Times-Bold',16);c.drawCentredString(W/2,325,'Project proposal')
c.setFont('Times-Roman',13)
for y,s in [(280,'Dai Pan'),(251,'Supervisor: Mashhuda Glencross'),(208,'REIT7842'),(179,meta['date'])]:c.drawCentredString(W/2,y,s)
c.setFont('Helvetica',9);c.setFillColor(HexColor('#65727D'));c.drawCentredString(W/2,96,'Computational social science • NLP • Temporal analysis')
c.showPage()
for i,(p,fs) in enumerate(zip(pages,allflows),2):
 c.bookmarkPage('page-'+p['name']);c.addOutlineEntry(p['blocks'][0][2] if p['blocks'][0][0]=='h' else p['name'],'page-'+p['name'],0)
 c.setFillColor(HexColor('#64717D'));c.setFont('Helvetica',7.7);c.drawString(X,H-36,'FEAR OF TEMPERATURE');c.drawRightString(W-X,H-36,'PROJECT PROPOSAL')
 c.setStrokeColor(HexColor('#DCE1E6'));c.setLineWidth(.6);c.line(X,H-43,W-X,H-43)
 y=TOP
 for j,f in enumerate(fs):
  if j:y-=f.getSpaceBefore()
  w,h=f.wrap(WIDTH,AVAIL)
  if hasattr(f,'refkey'):c.bookmarkHorizontalAbsolute('ref-'+f.refkey,y)
  f.drawOn(c,X,y-h);y-=h+f.getSpaceAfter()
 c.setFont('Helvetica',8);c.setFillColor(HexColor('#64717D'));c.drawString(X,33,'Dai Pan • 16 September 2026');c.drawRightString(W-X,33,label(i));c.showPage()
c.save()

# HTML uses the same page groups, figures, bibliography and links.
def htmlblocks(bs):
 out=[]
 for b in bs:
  typ=b[0]
  if typ=='h':out.append(f'<h{b[1]}>{rich(b[2],False)}</h{b[1]}>')
  elif typ=='p':out.append('<p class="'+('caption' if b[1].startswith('**Table ') else '')+'">'+rich(b[1],False)+'</p>')
  elif typ=='table':
   s='<div class="table-wrap"><table><colgroup>'+''.join(f'<col style="width:{r*100}%">' for r in b[2])+'</colgroup><thead><tr>'
   s+=''.join(('<th style="background:#e9ecef">' if b[1][0][0]=='Risk' else '<th>')+rich(x,False)+'</th>' for x in b[1][0])+'</tr></thead><tbody>'
   for row in b[1][1:]:
    s+='<tr>'
    for j,x in enumerate(row):
     attrs=[]
     if b[1][0][0]=='Risk':
      attrs.append('border-bottom:0.5px solid #d8dee3')
      if b[1][0][j]=='Rating':attrs.extend(['text-align:center','background:'+('#f5eddf' if x=='High' else '#f0f2f4')])
     if (b[1][0][0]=='AI tool usage' and j>0) or b[1][0][j]=='Access state':attrs.append('text-align:center')
     if j==0 and b[1][0][0] in ['Candidate source','Layer']:
      role=' '.join(row[:2]).lower()
      col=('#51247a' if re.search(r'\b(policy|epa|white house|unfccc)\b',role) else '#226799' if re.search(r'\b(media|nyt|guardian)\b',role) else '#087e76' if re.search(r'\b(public|reddit|letters|facebook)\b',role) else None)
      if col:attrs.append('color:'+col)
     s+='<td style="'+';'.join(attrs)+'">'+rich(x,False)+'</td>'
    s+='</tr>'
   s+='</tbody></table></div>';out.append(s)
  elif typ=='fig':out.append(f'<figure><img src="assets/{b[2]}.svg" alt="{html.escape(DESCRIPTIONS[b[2]],quote=True)}"><figcaption>{rich(b[1],False)}</figcaption></figure>')
  elif typ=='eq':out.append(f'<div class="equation" id="eq-{SPECS[b[1]][0]}"><img src="assets/equations/{b[1]}.svg" alt="{html.escape(SPECS[b[1]][2])} (Equation {SPECS[b[1]][0]})"></div>')
  elif typ=='toc':out.append('<nav class="contents">'+''.join(f'<a class="level{lev}" href="#page-{target}"><span>{html.escape(t)}</span><span>{n}</span></a>' for lev,t,target,n in toc)+'</nav>')
  elif typ=='ref':
   k=b[1]
   out.append(f'<p class="reference" id="ref-{k}">{reference(k,entries,refdates)}</p>')
 return '\n'.join(out)
css='''*{box-sizing:border-box}body{margin:0;background:#e9edf1;color:#263746;font-family:"Times New Roman",serif;font-size:15px;line-height:1.27}a{color:#51247a;text-decoration:none}a:hover{text-decoration:underline}.toolbar{position:sticky;top:0;background:#51247a;color:white;padding:12px 24px;z-index:4;font-family:Arial,sans-serif;font-size:13px}.toolbar a{color:white;margin-right:22px}.page{width:794px;min-height:1123px;margin:24px auto;padding:62px 94px 62px;background:white;box-shadow:0 4px 22px #18273417;position:relative;break-after:page}.running{font:10px Arial;color:#64717d;border-bottom:1px solid #dce1e6;padding-bottom:9px;display:flex;justify-content:space-between;margin-bottom:20px}h1{font-size:25.3px;line-height:1.21;color:#51247a;margin:0 0 18px}h2{font-size:17.3px;line-height:1.22;color:#51247a;margin:12px 0 10px}p{margin:0 0 11px}figure{margin:7px 0 13px}figure img{display:block;width:100%;height:auto}figcaption,.caption{font:11.7px/1.3 Arial,sans-serif;color:#4e5c68;margin:5px 0 11px}table{border-collapse:collapse;table-layout:fixed;width:100%;font:12px/1.27 Arial,sans-serif;margin-bottom:13px}th,td{padding:8px 9px;vertical-align:top;text-align:left;overflow-wrap:break-word}table{border-top:1.2px solid #697889;border-bottom:1.1px solid #697889}thead{border-bottom:1px solid #a3adb7}th{background:#ede8f3;color:#263746;font-weight:600}td,th{padding:5.3px 8px}.equation{margin:5px 0 9px}.equation img{width:100%;display:block}.contents a{display:flex;gap:20px;justify-content:space-between;font-size:14px;line-height:1.28;margin-bottom:3px}.contents .level1{font-weight:bold;margin-top:10px;color:#51247a}.contents+h2{margin-top:18px}.reference{font-size:14px;line-height:1.1905;margin-bottom:5.33px;padding-left:48px;text-indent:-48px;overflow-wrap:anywhere}.cover{text-align:center;padding-top:105px}.cover img{width:60%;height:auto}.cover h1{font-size:33.3px;margin-top:100px}.cover .subtitle{font-size:26.6px;line-height:1.3}.cover .meta{font-size:17.3px;margin-top:65px;line-height:1.9}.cover .status{font:12px Arial;margin-top:70px;color:#65727d}.foot{position:absolute;left:94px;right:94px;bottom:32px;display:flex;justify-content:space-between;font:10.7px Arial;color:#64717d}@media(max-width:820px){.page{width:calc(100% - 24px);min-height:0;padding:30px 24px 65px;margin:12px auto}.foot{left:24px;right:24px;bottom:22px}.toolbar{position:relative}.table-wrap{overflow-x:auto}table{min-width:540px}.cover h1{margin-top:50px}.cover .meta{margin-top:35px}.cover .status{margin-top:35px}.cover img{max-width:330px}.running{font-size:9px}figure{overflow-x:auto}figure img{min-width:530px}}@media print{@page{size:A4;margin:0}body{background:white}.toolbar{display:none}.page{width:210mm;height:297mm;min-height:0;box-shadow:none;margin:0;padding:16.4mm 25mm;overflow:visible}.cover{padding-top:28mm}.foot{bottom:8.5mm;left:25mm;right:25mm}}'''
cover=f'<section class="page cover"><img src="assets/UQ_Logo.png" alt="The University of Queensland"><h1>Fear of temperature</h1><p class="subtitle">Computational analysis of policy, media<br>and public climate emotions</p><div class="meta"><b>Project proposal</b><br>Dai Pan<br>Supervisor: Mashhuda Glencross<br>REIT7842<br>{meta["date"]}</div><p class="status">Computational social science • NLP • Temporal analysis</p></section>'
ht='<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(meta['title'])+'</title><style>'+css+'</style></head><body><div class="toolbar"><a href="#page-contents">Contents</a><a href="thesis_proposal.pdf">PDF</a><a href="thesis_proposal.txt">Plain text</a>Project proposal</div>'+cover
for i,p in enumerate(pages,2):ht+=f'<section class="page" id="page-{p["name"]}"><div class="running"><span>FEAR OF TEMPERATURE</span><span>PROJECT PROPOSAL</span></div>'+htmlblocks(p['blocks'])+f'<div class="foot"><span>Dai Pan • 16 September 2026</span><span>{label(i)}</span></div></section>'
(ROOT/'thesis_proposal.html').write_text(ht+'</body></html>')
# Plain text retains tables and a text equivalent of every diagram.
txt=[meta['title'],'Project proposal','Author: '+meta['author'],'Supervisor: '+meta['supervisor'],'REIT7842',meta['date'],'Project proposal']
for i,p in enumerate(pages,2):
 txt.append('\n'+'='*70+'\nPAGE '+label(i)+'\n'+'='*70)
 for b in p['blocks']:
  if b[0]=='h':txt.append(b[2])
  elif b[0]=='p':txt.append(plain(b[1]))
  elif b[0]=='eq':txt.append(SPECS[b[1]][2]+f'  ({SPECS[b[1]][0]})')
  elif b[0]=='table':txt.append('\n'.join(' | '.join(plain(x) for x in row) for row in b[1]))
  elif b[0]=='fig':txt.extend([plain(b[1]),'Diagram text equivalent: '+DESCRIPTIONS[b[2]]])
  elif b[0]=='toc':txt.append('\n'.join(t+' ... '+n for _,t,_,n in toc))
  elif b[0]=='ref':
   k=b[1];txt.append(ref_text(k))
(ROOT/'thesis_proposal.txt').write_text('\n\n'.join(txt)+'\n')
manifest=dict(pages=len(pages)+1,figures=len(FIGURES),tables=sum(b[0]=='table' for p in pages for b in p['blocks']),references=len(keys),peer_reviewed_entries=sum(e['type'] in ['article','inproceedings'] for e in entries.values()),body_words=len(re.findall(r'\b[\w-]+\b',body)),outputs={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['thesis_proposal.md','thesis_proposal.html','thesis_proposal.pdf','thesis_proposal.txt','references.bib']},figure_min_font_size=min(a['size'] for d in FIGURES.values() for a in d._audit),assets={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'assets').glob('*.svg')})
manifest['equations']={k:{'number':v[0],'latex':v[1],'plain':v[2]} for k,v in SPECS.items()}
(ROOT/'qa'/'export_manifest.json').write_text(json.dumps(manifest,indent=2))
(ROOT/'qa'/'figure_text_bounds.json').write_text(json.dumps({k:d._audit for k,d in FIGURES.items()},indent=2))
print(json.dumps(manifest,indent=2));print('Page free space:',[(r['page'],r['remaining']) for r in report])
