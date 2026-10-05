"""Original vector research diagrams. No empirical observations are plotted."""
from pathlib import Path
from math import atan2, sin, cos
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle, PolyLine, Path as GPath
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT=Path(__file__).resolve().parent
W=453.54
INK='#263746'; MUTED='#5D6B78'; PURPLE='#51247A'; BLUE='#266596'; TEAL='#16796F'; AMBER='#A96312'; RED='#AD3C41'
PALE='#F4F6F8'; RULE='#DAE0E6'
DESCRIPTIONS={}

def new(h):
 d=Drawing(W,h); d.add(Rect(0,0,W,h,fillColor=HexColor('#FFFFFF'),strokeColor=None)); d._audit=[]; return d

def txt(d,x,y,s,size=9,color=INK,bold=False,anchor='start'):
 font='Helvetica-Bold' if bold else 'Helvetica'
 d.add(String(x,d.height-y,s,fontName=font,fontSize=size,fillColor=HexColor(color),textAnchor=anchor))
 width=stringWidth(s,font,size); left=x if anchor=='start' else x-width/2 if anchor=='middle' else x-width
 assert left>=-0.2 and left+width<=W+.2,(s,left,width)
 assert y>=size*.65 and y<=d.height-1,(s,y,d.height)
 d._audit.append(dict(text=s,x=left,top=y-size,width=width,size=size))

def line(d,x1,y1,x2,y2,color=RULE,width=1,dash=False):
 d.add(Line(x1,d.height-y1,x2,d.height-y2,strokeColor=HexColor(color),strokeWidth=width,strokeDashArray=[3,3] if dash else None))

def arrow(d,x1,y1,x2,y2,color=MUTED,dash=False,both=False):
 line(d,x1,y1,x2,y2,color,1,dash)
 def head(x,y,a):
  pts=[x,d.height-y,x-4*cos(a)+2*sin(a),d.height-y+4*sin(a)+2*cos(a),x-4*cos(a)-2*sin(a),d.height-y+4*sin(a)-2*cos(a)]
  d.add(Polygon(pts,fillColor=HexColor(color),strokeColor=None))
 a=atan2(y2-y1,x2-x1);head(x2,y2,a)
 if both:head(x1,y1,a+3.141592653589793)

def box(d,x,y,w,h,title,body=(),color=PURPLE,fill=PALE,ts=10,bs=8.6):
 d.add(Rect(x,d.height-y-h,w,h,rx=5,ry=5,fillColor=HexColor(fill),strokeColor=HexColor(RULE),strokeWidth=.6))
 d.add(Rect(x,d.height-y-h,3,h,fillColor=HexColor(color),strokeColor=None))
 txt(d,x+10,y+17,title,ts,color,True)
 for i,s in enumerate(body):
  assert stringWidth(s,'Helvetica',bs)<=w-18,(title,s,w)
  txt(d,x+10,y+32+i*11.5,s,bs)

def tag(d,x,y,s,color=PURPLE): txt(d,x,y,s,8,color,True)

def relationships():
 d=new(219)
 tag(d,0,10,'ONE QUESTION · THREE DISCOURSE ROLES')
 # A triangular network leaves the relationships visually open to investigation.
 nodes=[(88,94,PURPLE,'Government / policy','Institutions and decisions'),(365,94,BLUE,'News media','Reports and frames'),(226,167,TEAL,'Public expression','Posts, letters and forums')]
 arrow(d,118,95,335,95,MUTED,True,True)
 arrow(d,113,108,201,153,MUTED,True,True)
 arrow(d,340,108,252,153,MUTED,True,True)
 for x,y,col,title,sub in nodes:
  d.add(Circle(x,d.height-y,27,fillColor=HexColor(col),strokeColor=None))
  # Original document / speech glyph, intentionally simple.
  if col==PURPLE:
   d.add(Polygon([x-13,d.height-y+7,x,d.height-y+15,x+13,d.height-y+7],fillColor=HexColor('#FFFFFF'),strokeColor=None))
   for xx in [x-9,x,x+9]:line(d,xx,y-4,xx,y+9,'#FFFFFF',2)
   line(d,x-14,y+12,x+14,y+12,'#FFFFFF',2)
  elif col==BLUE:
   d.add(Rect(x-12,d.height-y-12,24,25,rx=2,ry=2,fillColor=None,strokeColor=HexColor('#FFFFFF'),strokeWidth=1.5))
   for yy in [y-6,y,y+6]:line(d,x-7,yy,x+7,yy,'#FFFFFF',1.5)
  else:
   d.add(Rect(x-14,d.height-y-8,28,19,rx=4,ry=4,fillColor=None,strokeColor=HexColor('#FFFFFF'),strokeWidth=1.5))
   line(d,x-7,y+8,x-12,y+14,'#FFFFFF',1.5)
   for xx in [x-7,x,x+7]:d.add(Circle(xx,d.height-y+1,1.4,fillColor=HexColor('#FFFFFF'),strokeColor=None))
  if y<120:
   txt(d,x,y+43,title,10,col,True,'middle');txt(d,x,y+57,sub,8.5,MUTED,False,'middle')
  else:
   txt(d,x+41,y-2,title,10,col,True);txt(d,x+41,y+12,sub,8.5,MUTED)
 txt(d,W/2,84,'WHO CHANGES FIRST?',8.4,PURPLE,True,'middle')
 # Independent inputs are visually separate from the social-role triangle.
 for x,w,col,t in [(0,219,AMBER,'Physical observations / heat exposure'),(234,219,PURPLE,'Policy decisions / scientific events')]:
  d.add(Rect(x,d.height-43,w,24,rx=12,ry=12,fillColor=HexColor('#F4F0E9' if col==AMBER else '#F0EBF5'),strokeColor=None));txt(d,x+w/2,34,t,8.7,col,False,'middle')
 line(d,W/2,46,W/2,67,MUTED,1,True)
 txt(d,0,207,'Compare attention, emotion and responsibility over time.',9,INK,True)
 txt(d,W,219-2,'Dashed links are hypotheses.',8.1,MUTED,False,'end')
 return d

def pipeline():
 d=new(277)
 for x,t,c in [(0,'Policy / government',PURPLE),(155,'News media',BLUE),(310,'Public expression',TEAL)]:
  box(d,x,0,143,34,t,(),c,ts=9.5);arrow(d,x+71.5,35,x+71.5,47,c)
 box(d,0,49,W,41,'1  Acquire and sample',('Check permission, coverage and the issue-independent denominator',),PURPLE)
 arrow(d,W/2,91,W/2,100)
 box(d,0,102,W,41,'2  Build a traceable database',('Preserve dates, roles, context, evidence spans and duplicate clusters',),PURPLE)
 arrow(d,W/2,144,W/2,153)
 box(d,0,155,W,36,'3  Shared representations + original language',(),PURPLE)
 txt(d,10,183,'Versioned Transformer embeddings; contextual text remains available',8.6)
 for x in [71.5,226.5,381.5]:arrow(d,x,192,x,200)
 box(d,0,202,143,47,'Events + relations',('Who, what, when;','cause, blame and duty'),PURPLE,ts=9.4)
 box(d,155,202,143,47,'Targeted emotions',('Emotion, target, speaker;','time horizon and group'),TEAL,ts=9.4)
 box(d,310,202,143,47,'Topics + semantics',('Themes, frames and','change in context'),BLUE,ts=9.4)
 txt(d,W/2,267,'VALIDATE  →  Aggregate by role and time  →  Analyse  →  Interpret in the thesis',9,PURPLE,True,'middle')
 return d

def evidence():
 d=new(204)
 tag(d,0,10,'SYNTHETIC TEXT → CONTEXTUAL EVIDENCE')
 d.add(Rect(0,d.height-84,W,63,rx=7,ry=7,fillColor=HexColor('#F5F6F8'),strokeColor=None))
 # Colour links the source language to the three extracted feature groups.
 txt(d,12,38,'“After the new climate plan was announced,',9.5,PURPLE)
 txt(d,12,56,'I still worry about the world my children will inherit',9.5,TEAL)
 txt(d,12,74,'because major emitters are not being held accountable.”',9.5,BLUE)
 for x,col in [(71,PURPLE),(226,TEAL),(381,BLUE)]:arrow(d,x,87,x,102,col)
 for x,title,lines,col in [(0,'Event / time',['Policy announcement','Temporal reference only'],PURPLE),(155,'Emotion / horizon',['Worry; anticipated future','Family / next generation'],TEAL),(310,'Cause / responsibility',['Emitters; accountability','Negation must be retained'],BLUE)]:
  d.add(Rect(x,d.height-164,143,59,rx=6,ry=6,fillColor=HexColor(PALE),strokeColor=None))
  d.add(Rect(x,d.height-108,143,3,fillColor=HexColor(col),strokeColor=None))
  txt(d,x+9,124,title,9.5,col,True)
  for j,t in enumerate(lines):txt(d,x+9,140+j*12,t,8.5,INK)
 txt(d,0,182,'Attribution axes:',8.7,PURPLE,True);txt(d,87,182,'event / time  +  causes / responsibility',8.7)
 txt(d,0,198,'Unresolved: policy caused the worry; who has the duty to act. No population inference.',8.5,MUTED)
 return d

def temporal():
 d=new(249)
 # Ratio cards are visually keyed to their role as measurements.
 for x,k,t,sub,col in [(0,'S','Attention','Relevant / all eligible',PURPLE),(155,'E','Emotion share','Emotion / relevant',TEAL),(310,'B','Joint share','Emotion-related / all; S × E',BLUE)]:
  d.add(Rect(x,d.height-50,143,50,rx=7,ry=7,fillColor=HexColor(PALE),strokeColor=None))
  d.add(Circle(x+20,d.height-21,13,fillColor=HexColor(col),strokeColor=None));txt(d,x+20,25,k,13,'#FFFFFF',True,'middle')
  txt(d,x+40,18,t,9.7,col,True);txt(d,x+9,44,sub,8.2,MUTED)
 txt(d,W/2,63,'Align role + time + geography · Add physical observations and event dates',8.7,INK,True,'middle')
 line(d,0,73,W,73,RULE,.8)
 tag(d,0,88,'A  WHO CHANGES FIRST?',BLUE)
 tag(d,244,88,'B  WHAT CHANGES AFTER AN EVENT?',PURPLE)
 # Smooth trajectories convey a lag. They are deliberately synthetic, without numeric axes.
 x0=12;y0=177;cw=193
 line(d,x0,y0,x0+cw,y0,RULE,.8);line(d,x0,107,x0,y0,RULE,.8)
 for lag,col in [(0,PURPLE),(22,BLUE),(44,TEAL)]:
  path=GPath();path.moveTo(x0,d.height-(y0-4))
  path.curveTo(x0+22+lag,d.height-(y0-4),x0+35+lag,d.height-(y0-65),x0+58+lag,d.height-(y0-62))
  path.curveTo(x0+88+lag,d.height-(y0-60),x0+96+lag,d.height-(y0-5),x0+148+lag,d.height-(y0-4))
  path.strokeColor=HexColor(col);path.strokeWidth=2;path.fillColor=None;d.add(path)
 txt(d,x0,189,'Earlier',8,MUTED);txt(d,x0+cw,189,'Later',8,MUTED,False,'end')
 for x,t,col in [(0,'Policy',PURPLE),(71,'Media',BLUE),(143,'Public',TEAL)]:
  line(d,x,204,x+14,204,col,2);txt(d,x+19,207,t,8.5,col)
 # Three compact event alternatives show level, slope and null outcomes.
 for j,(label,pts) in enumerate([('Level',[(0,0),(24,0),(24,23),(52,23)]),('Slope',[(0,0),(24,0),(52,29)]),('Null',[(0,0),(52,0)])]):
  x=249+j*70;y=169
  d.add(Rect(x-5,d.height-178,65,74,rx=4,ry=4,fillColor=HexColor(PALE),strokeColor=None))
  line(d,x,y+4,x+52,y+4,RULE,.6);line(d,x+24,110,x+24,175,MUTED,.7,True)
  pts2=[]
  for px,py in pts:pts2 += [x+px,d.height-(y-py)]
  d.add(PolyLine(pts2,strokeColor=HexColor(PURPLE),strokeWidth=2,fillColor=None));txt(d,x+26,190,label,8.5,PURPLE,True,'middle')
 txt(d,244,207,'Dashed lines mark the event date.',8.3,MUTED)
 line(d,0,219,W,219,RULE,.6)
 txt(d,0,233,'CCF → candidate lags; dynamic models → prediction',8.5,BLUE,True)
 txt(d,0,247,'ILLUSTRATIVE TRAJECTORIES ONLY · No observed data or estimated effects',8.3,MUTED)
 return d

def schedule():
 from nature_schedule import make
 from reportlab.platypus import Flowable
 from pdfrw import PdfReader
 from pdfrw.buildxobj import pagexobj
 from pdfrw.toreportlab import makerl
 import pymupdf as fitz
 out=make()
 class VectorFigure(Flowable):
  def __init__(self,path):
   super().__init__();self.page=pagexobj(PdfReader(str(path)).pages[0]);self.width=float(self.page.BBox[2]);self.height=float(self.page.BBox[3]);self._audit=[]
   with fitz.open(str(path)) as pdf:
    for block in pdf[0].get_text('dict')['blocks']:
     for row in block.get('lines',[]):
      for span in row['spans']:
       bb=span['bbox'];self._audit.append(dict(text=span['text'],x=bb[0],top=bb[1],width=bb[2]-bb[0],size=span['size']))
  def draw(self):self.canv.doForm(makerl(self.canv,self.page))
 return VectorFigure(str(out)+'.pdf')

def make_figures():
 figs={
 'figure_01_relationships':relationships(), 'figure_02_pipeline':pipeline(),
 'figure_03_evidence':evidence(), 'figure_04_temporal':temporal(), 'figure_05_schedule':schedule()}
 for k,d in figs.items():
  if k!='figure_05_schedule': renderSVG.drawToFile(d,str(ROOT/'assets'/f'{k}.svg'))
  DESCRIPTIONS[k]=' | '.join(a['text'] for a in d._audit)
 return figs
