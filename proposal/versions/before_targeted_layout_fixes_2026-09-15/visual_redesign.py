"""Visual research plan: schematic paths, graphical tables and planned effort.
No empirical observations or estimated research effects are depicted.
"""
from pathlib import Path
import sys,os,csv,json,subprocess,datetime
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.runtime'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'qa/matplotlib'))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle,Rectangle,FancyBboxPatch,FancyArrowPatch,Ellipse,Arc,Polygon
from matplotlib.font_manager import fontManager
SCRIPTS=ROOT.parent/'tools/nature-skills/skills/nature-figure/scripts'
sys.path.insert(0,str(SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment
for f in ['Arial.ttf','Arial Bold.ttf']:fontManager.addfont('/System/Library/Fonts/Supplemental/'+f)
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8.5,'svg.fonttype':'none','pdf.fonttype':42,'axes.linewidth':.6,'savefig.facecolor':'white'})
W=453.54
P='#643A91';B='#2376AB';G='#008878';A='#BF8130';R='#AD4F64';INK='#263748';M='#647487';RULE='#D5DFE8'
PALE={P:'#F0E8F7',B:'#E9F2F9',G:'#E5F4F0',A:'#FAF1DF',R:'#F8E9EE'}
def canvas(h):
 fig=plt.figure(figsize=(W/72,h/72));ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,W);ax.set_ylim(h,0);ax.axis('off');fig._height=h;return fig,ax
def text(ax,x,y,s,size=8.5,c=INK,bold=False,ha='left',va='center',**kw):
 return ax.text(x,y,s,fontsize=size,color=c,fontweight='bold' if bold else 'normal',ha=ha,va=va,linespacing=1.25,**kw)
def line(ax,x1,y1,x2,y2,c=RULE,lw=.8,ls='-'):
 ax.plot([x1,x2],[y1,y2],color=c,lw=lw,linestyle=ls,zorder=1)
def box(ax,x,y,w,h,c=P,fill=None,r=6,lw=0,hatch=None):
 p=FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={r}',facecolor=fill or PALE[c],edgecolor=c if lw or hatch else 'none',lw=lw,hatch=hatch,zorder=0);ax.add_patch(p);return p
def arr(ax,a,b,c=M,lw=1.25,rad=0,style='-|>',dash=False):
 ax.add_patch(FancyArrowPatch(a,b,connectionstyle=f'arc3,rad={rad}',arrowstyle=style,mutation_scale=8,lw=lw,color=c,linestyle=(0,(3,2)) if dash else '-',zorder=1))
def badge(ax,x,y,s,c=P,r=12,size=8.8):
 ax.add_patch(Circle((x,y),r,facecolor=c,edgecolor='white',lw=1,zorder=2));text(ax,x,y,s,size,'white',True,'center',zorder=3)
def chip(ax,x,y,w,s,c=P):
 box(ax,x,y,w,19,c,r=9);text(ax,x+w/2,y+9.5,s,7.8,c,True,'center')
def doc(ax,x,y,c=P,w=15,h=19):
 ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=c,lw=.9))
 for yy in [y+5,y+9,y+13]:line(ax,x+3,yy,x+w-3,yy,c,.75)
def heading(ax,title,sub):
 text(ax,0,9,title,10.5,INK,True);text(ax,0,25,sub,7.6,M)
def save(fig,key,axes=None,groups=None,exemptions=None):
 base=ROOT/'assets'/key;qa=ROOT/'assets/visual_qa';qa.mkdir(exist_ok=True)
 require_matplotlib_panel_alignment(fig,json_out=qa/f'{key}.alignment.json',overlay_svg=qa/f'{key}.alignment.svg',strict=True,axes=axes or fig.axes,panel_ids=[f'p{i}' for i in range(len(axes or fig.axes))],row_groups=groups or [],exemptions=exemptions or [])
 fig.savefig(str(base)+'.svg');fig.savefig(str(base)+'.pdf');fig.savefig(str(base)+'.png',dpi=300);plt.close(fig)
 env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'.runtime')
 jobs=[('audit_pdf_text.py',[str(base)+'.pdf','--min-pt','5','--json'],qa/f'{key}.text.json'),('audit_figure_collisions.py',[str(base)+'.pdf','--json-out',str(qa/f'{key}.collisions.json'),'--overlay-pdf',str(qa/f'{key}.collisions.pdf')],None)]
 for script,args,out in jobs:
  run=subprocess.run([sys.executable,str(SCRIPTS/script),*args],capture_output=True,text=True,env=env)
  if out:out.write_text(run.stdout)
  if run.returncode:raise RuntimeError(f'Figure audit failed: {key}, {script}: {run.stdout[:500]}')
 return base

def relationships():
 fig,ax=canvas(230);heading(ax,'One social question, three discourse roles','Who changes first, and how is warming-related fear explained?')
 box(ax,0,42,269,155,P,fill='#F7F5FA',r=12)
 positions=[(54,89,'G',P,'Government / policy'),(215,89,'M',B,'News media'),(134,153,'P',G,'Public expression')]
 arr(ax,(80,83),(190,83),M,1.3,rad=.17,style='<->',dash=True)
 arr(ax,(80,99),(116,131),M,1.3,rad=-.2,style='<->',dash=True)
 arr(ax,(197,108),(155,141),M,1.3,rad=-.16,style='<->',dash=True)
 for x,y,t,c,lab in positions:
  ax.add_patch(Circle((x,y),23,fill=False,edgecolor=c,lw=5,alpha=.13))
  badge(ax,x,y,t,c,r=17,size=12);text(ax,x,y+30,lab,8,c,True,'center')
 text(ax,0,215,'Dashed arrows: competing relationships, not established effects.',7.7,M)
 # A side spine distinguishes inputs from the social discourse network.
 text(ax,290,48,'Independent anchors',9,P,True)
 for y,c,title,sub in [(81,A,'Physical events','Local heat / climate background'),(132,B,'Scientific events','Dated assessments / releases'),(183,P,'Policy events','Announcement / adoption / action')]:
  badge(ax,298,y,'+',c,r=8,size=9);text(ax,313,y-6,title,8.4,c,True);text(ax,313,y+9,sub,7.1,M)
  arr(ax,(282,y),(274,y),c,dash=True)
 return save(fig,'figure_01_relationships')

def mechanisms():
 fig,ax=canvas(258);heading(ax,'Five competing temporal patterns','Read each row as a candidate explanation; routes may differ across windows.')
 text(ax,5,45,'EXPECTATION',7.2,M,True);text(ax,184,45,'POSSIBLE ORDERING',7.2,M,True);text(ax,333,45,'WHAT TO LOOK FOR',7.2,M,True)
 rows=[('H1','Institutional lead',P,'Institution first'),('H2','Media lead',B,'Media first'),('H3','Public lead',G,'Public first'),('H4','Common event',A,'Shared timing'),('H5','Feedback',R,'Both directions')]
 for i,(code,title,c,obs) in enumerate(rows):
  y=72+i*34;box(ax,0,y-14,W,29,c,r=5);badge(ax,17,y,code,c,10,7.8);text(ax,35,y,title,8.6,c,True)
  coords={'G':170,'M':229,'P':288};colors={'G':P,'M':B,'P':G}
  if i<3:
   seq=[['G','M','P'],['M','P','G'],['P','M','G']][i]
   for j,label in enumerate(seq):badge(ax,170+j*59,y,label,colors[label],9,7.7)
   arr(ax,(181,y),(217,y),c);arr(ax,(240,y),(276,y),c)
  elif i==3:
   for label,x in coords.items():badge(ax,x,y,label,colors[label],9,7.7)
   # Shared upper bracket is an event linkage, not a measured lag.
   line(ax,161,y-12,297,y-12,A,1.3)
   for x in coords.values():line(ax,x,y-12,x,y-10,A,1.3)
  else:
   for label,x in coords.items():badge(ax,x,y,label,colors[label],9,7.7)
   arr(ax,(181,y),(217,y),R,style='<->');arr(ax,(240,y),(276,y),R,style='<->')
  text(ax,333,y,obs,8.1,INK)
 text(ax,0,250,'G: government/policy   M: media   P: public   ·   Predictive ordering alone is not causation.',7.5,M)
 return save(fig,'figure_06_mechanisms')

def rqmap():
 fig,ax=canvas(247);heading(ax,'From research question to interpretable evidence','Three questions share one validated corpus and representation.')
 cols=[0,128,274];widths=[113,131,179]
 for x,s in zip(cols,['QUESTION','MEASURE + NLP','ANALYSIS → CLAIM']):text(ax,x,45,s,7.2,M,True)
 rows=[(P,'RQ1','Who changes first?','Relevance + emotion','S by role; public E','CCF / conditional VAR','Lead / lag; added prediction'),(B,'RQ2','What changes at events?','Event links + emotion','S / E; common windows','Segmented regression / ITS','Level / slope; association'),(G,'RQ3','How is fear explained?','Relations + topics','Cause / blame / duty','Patterns + evidence spans','Attribution / reinterpretation')]
 for i,(c,code,q,mod,measure,method,claim) in enumerate(rows):
  y=59+i*54
  box(ax,0,y,W,47,c,r=6)
  ax.add_patch(Rectangle((0,y),3,47,facecolor=c,lw=0))
  text(ax,12,y+12,code,10,c,True);text(ax,12,y+31,q,7.5,INK)
  arr(ax,(112,y+24),(125,y+24),c,lw=1.5)
  text(ax,137,y+14,mod,8.0,c,True);text(ax,137,y+32,measure,7.6,M)
  arr(ax,(259,y+24),(272,y+24),c,lw=1.5)
  text(ax,284,y+14,method,8.1,c,True);text(ax,284,y+32,claim,7.7,INK)
 text(ax,0,232,'Shared safeguards: fixed units + weights · source/time validation · original context',7.8,M)
 return save(fig,'figure_07_rq_routes')

def sampling():
 fig,ax=canvas(183);heading(ax,'Three source roles, three auditable denominators','General attention comes from the eligible collection, not climate-only retrieval.')
 for i,(c,role,unit,den) in enumerate([(P,'Policy','paragraphs OR speaking turns','All eligible; same institution + genre'),(B,'Media','deduplicated articles','All eligible; same title + edition + bin'),(G,'Public','posts; comments separate','All eligible posts; same community')]):
  y=43+i*39
  box(ax,0,y,91,32,c,r=5);doc(ax,8,y+7,c,w=12,h=17);text(ax,29,y+16,role,8.8,c,True)
  arr(ax,(95,y+16),(111,y+16),c)
  text(ax,122,y+5,'Relevant '+unit.lower(),7.7,c,True)
  line(ax,118,y+16,339,y+16,c,.8)
  text(ax,122,y+27,den,7.7,INK)
  chip(ax,354,y+7,98,'Within-source S',c)
 text(ax,0,174,'Climate-only subsets support emotion and relations; they cannot estimate general attention.',7.6,M)
 return save(fig,'figure_08_sampling')

def pipeline():
 fig,ax=canvas(263);heading(ax,'Language → database → representation → interpretation','Original text and provenance remain attached throughout the pipeline.')
 # Three strands converge on the database; widths do not encode volumes.
 for x,c,lab in [(0,P,'Policy'),(155,B,'Media'),(310,G,'Public')]:
  box(ax,x,40,143,31,c,r=6);doc(ax,x+11,47,c,w=12,h=16);text(ax,x+37,56,lab,9,c,True)
  arr(ax,(x+71,74),(W/2,100),c,lw=2.1,rad=.10 if x<150 else -.10 if x>200 else 0)
 # Database cylinder paired with the representative feature matrix.
 ax.add_patch(Rectangle((126,102),93,38,facecolor=PALE[P],edgecolor=P,lw=.8))
 ax.add_patch(Ellipse((172.5,102),93,12,facecolor=PALE[P],edgecolor=P,lw=.8))
 ax.add_patch(Arc((172.5,140),93,12,theta1=0,theta2=180,edgecolor=P,lw=.8))
 text(ax,173,121,'Traceable database',8.5,P,True,'center')
 arr(ax,(224,120),(249,120),P,lw=1.4)
 for iy in range(4):
  for ix in range(8):ax.add_patch(Rectangle((259+ix*8,103+iy*8),6,6,facecolor=[P,B,G][(iy+ix)%3],alpha=.23+.10*((ix+2*iy)%4),lw=0))
 text(ax,338,114,'Shared encoder',8.5,P,True);text(ax,338,130,'Schematic features',7.2,M)
 for x,c in [(71,P),(226,G),(381,B)]:arr(ax,(290,146),(x,170),c,lw=1.3,rad=0)
 for x,c,t1,t2 in [(0,P,'Events + relations','Cause · blame · duty'),(155,G,'Targeted emotions','Emotion · target · holder'),(310,B,'Topics + semantics','Themes · frames · context')]:
  box(ax,x,175,143,43,c,r=7);text(ax,x+10,189,t1,8.7,c,True);text(ax,x+10,206,t2,7.8,INK)
  arr(ax,(x+71,220),(x+71,230),c)
 line(ax,20,236,434,236,P,1.3)
 text(ax,W/2,252,'VALIDATE  →  AGGREGATE  →  ANALYSE  →  INTERPRET',8.7,P,True,'center')
 return save(fig,'figure_02_pipeline')

def evidence():
 fig,ax=canvas(205);heading(ax,'One passage, several linked pieces of evidence','Synthetic example; contextual relations are not verified causal effects.')
 segments=[(P,'After the new climate plan was announced,','EVENT / TIME'),(G,'I still worry about the world my children will inherit','EMOTION / HORIZON'),(B,'because major emitters are not being held accountable.','CAUSE / RESPONSIBILITY')]
 for i,(c,phrase,label) in enumerate(segments):
  y=43+i*27;box(ax,0,y,W,23,c,r=4);text(ax,9,y+11,phrase,9,c)
 for i,(x,c,head,sub) in enumerate([(0,P,'Policy announcement','Temporal reference only'),(155,G,'Worry about the future','Family / next generation'),(310,B,'Emitters; accountability','Negation retained')]):
  arr(ax,(x+71,124),(x+71,140),c)
  line(ax,x,144,x+143,144,c,3)
  text(ax,x+3,159,head,8.6,c,True);text(ax,x+3,175,sub,7.7,M)
 text(ax,0,199,'Still unresolved: policy caused the worry; who has the duty to act.',7.8,M)
 return save(fig,'figure_03_evidence')

def temporal():
 fig,ax=canvas(248);heading(ax,'Measure the discourse, then test its timing','Illustrative trajectories only; no observed data or estimated effects.')
 for x,c,lab,sub in [(0,P,'S  Attention','Relevant / eligible'),(155,G,'E  Emotion','Emotion / relevant'),(310,B,'B  Joint share','S × E; derived measure')]:
  box(ax,x,40,143,35,c,r=6);text(ax,x+10,52,lab,9.4,c,True);text(ax,x+10,67,sub,7.6,M)
 text(ax,0,93,'a   Relative timing',8.9,P,True);text(ax,252,93,'b   Event-associated change',8.9,B,True)
 h=fig._height
 left=fig.add_axes([10/W,(h-191)/h,206/W,82/h]);right=fig.add_axes([251/W,(h-191)/h,195/W,82/h])
 for a in [left,right]:
  a.spines[['top','right','left']].set_visible(False);a.spines['bottom'].set_color(RULE);a.set_yticks([]);a.tick_params(length=0,labelsize=7.2);a.set_ylim(0,1.25)
 x=np.linspace(0,1,160)
 for mu,c,lab in [(0.34,P,'Policy'),(.50,B,'Media'),(.66,G,'Public')]:
  y=np.exp(-((x-mu)/.17)**2);left.plot(x,y,c=c,lw=1.8);left.fill_between(x,0,y,color=c,alpha=.10)
 left.set_xticks([0,1],['Earlier','Later']);left.set_xlim(0,1)
 # Three alternatives share units and the same event position; vertical offsets are labelled layouts.
 right.set_xlim(-1,1);right.axvline(0,color=M,lw=.75,ls=(0,(3,2)))
 right.plot([-1,0,0,1],[.83,.83,1.05,1.05],color=P,lw=1.8)
 right.plot([-1,0,1],[.49,.49,.72],color=B,lw=1.8)
 right.plot([-1,1],[.15,.15],color=G,lw=1.8)
 right.set_xticks([-1,0,1],['Before','Event','After'])
 for yy,lab,c in [(1.13,'Level',P),(.66,'Slope',B),(.30,'Null',G)]:text(right,-.95,yy,lab,7.3,c,True)
 right.get_xticklabels()[-1].set_ha('right')
 left.get_xticklabels()[0].set_ha('left')
 for x0,c,lab in [(0,P,'Policy'),(70,B,'Media'),(137,G,'Public')]:line(ax,x0,220,x0+14,220,c,2);text(ax,x0+18,220,lab,7.5,c)
 text(ax,251,220,'Level / slope are distinct estimands.',7.5,M)
 text(ax,0,241,'CCF explores lags. Conditional models assess added prediction. Neither alone proves causation.',7.5,M)
 return save(fig,'figure_04_temporal',axes=[left,right],groups=[{'id':'comparison','panels':['p0','p1']}],exemptions=[{'panels':['p0','p1'],'checks':['panel-width'],'reason':'Schematic timing and event alternatives use intentionally different plot widths.'}])

def risks():
 fig,ax=canvas(346);heading(ax,'Protect the analysis deadline','Qualitative planning priorities: H = high; M = moderate. No probabilities estimated.')
 for x,lab in [(0,'RISK'),(143,'TRIGGER'),(291,'ACTION / LIMIT')]:text(ax,x,47,lab,7.3,M,True)
 items=[('R1','Database delay','H','Pilot / freeze missed','Stop expansion; analyse core',R),('R2','Access / release','H','No workable access','Permitted same-role source',P),('R3','Sparse history','H','Few usable time points','Common quarters / context',P),('R4','Measurement error','H','Labels fail validation','Refine or narrow labels',B),('R5','False temporal signal','H','Duplicates / shared shocks','Diagnostics; bounded claims',B),('R6','Composition change','H','Source / encoder shifts','Fixed-source checks + weights',B),('R7','Compute / staffing','M','Cost exceeds capacity','Cache; cap comparisons',G),('R8','Loss / interruption','M','Illness / backup failure','Snapshots; protected revision',G),('R9','Date conflict','H','Report date unresolved','Clarify; replan if earlier',R)]
 for i,(code,name,priority,trigger,action,c) in enumerate(items):
  y=66+i*29
  box(ax,0,y-11,W,24,c,r=4)
  badge(ax,12,y,priority,c,7,6.8);text(ax,25,y,code+'  '+name,7.8,c,True)
  text(ax,151,y,trigger,7.6,INK);arr(ax,(275,y),(286,y),c,lw=1)
  text(ax,298,y,action,7.4,INK)
 text(ax,0,337,'Decision rule: narrow the comparison early; retain validation and all three NLP components.',7.6,M)
 return save(fig,'figure_09_risk_routes')

def schedule():
 rows=list(csv.DictReader((ROOT/'assets/schedule_source.csv').open()))
 fig,ax=canvas(425);heading(ax,'A research calendar with protected analysis time','10–20 hours/week · planned task effort 450–590 h + 15% contingency')
 text(ax,0,47,'WORK PACKAGE',7.3,M,True);text(ax,122,47,'2026',8,P,True);text(ax,213,47,'2027',8,P,True);text(ax,361,47,'PLANNED HOURS',7.3,M,True)
 dt=lambda x:datetime.date.fromisoformat(x)
 start=dt('2026-09-01');end=dt('2027-07-01')
 xx=lambda v:120+(dt(v)-start).days/(end-start).days*221
 for startx,endx,c in [('2026-09-01','2027-01-01',P),('2027-01-01','2027-03-01',G),('2027-03-01','2027-07-01',B)]:
  ax.add_patch(Rectangle((xx(startx),76),xx(endx)-xx(startx),159,facecolor=PALE[c],edgecolor='none'))
 for m in range(9,19):
  d=datetime.date(2026+(m-1)//12,(m-1)%12+1,1);x=xx(d.isoformat());line(ax,x,76,x,235,'#CFD8E1',.45);text(ax,xx(d.replace(day=15).isoformat()),65,d.strftime('%b'),7,M,ha='center')
 for i,r in enumerate(rows):
  y=91+i*25;c=[P,P,G,B,P,G][i];text(ax,0,y-5,r['code'],8.6,c,True);text(ax,23,y-5,r['label'],8,c,True)
  lo,hi=int(r['hours_low']),int(r['hours_high']);xs,xe=xx(r['start']),xx(r['end'])
  ax.add_patch(Rectangle((xs,y-6),xe-xs,10,facecolor=c,edgecolor='none'))
  if r['gate']:ax.plot(xe,y-1,marker='D',markersize=4.8,mfc='white',mec=c,mew=.9)
  if i<5:
   target=max(xe,xx(rows[i+1]['start']));arr(ax,(xe,y+6),(target,y+15),c,lw=.8)
  text(ax,360,y-7,f'{lo}–{hi}',7.5,c,True)
  line(ax,360,y+4,444,y+4,'#E4EAF0',5)
  line(ax,360,y+4,360+lo/140*84,y+4,c,4)
  ax.add_patch(Rectangle((360+lo/140*84,y+2), (hi-lo)/140*84,4,facecolor=PALE[c],edgecolor=c,lw=.5))
  line(ax,0,y+12,W,y+12,RULE,.45) if i<5 else None
 deadline=xx('2027-03-01');line(ax,deadline,76,deadline,236,G,1.4,ls=(0,(3,2)))
 # Optional expansion hatch is not a progress or probability mark.
 ax.add_patch(Rectangle((xx('2026-10-10'),226),xx('2026-12-18')-xx('2026-10-10'),8,facecolor=PALE[P],edgecolor=P,lw=.5))
 
 for hx in np.arange(xx('2026-10-10')+2,xx('2026-12-18')-4,5):line(ax,hx,233,hx+4,227,P,.65)
 text(ax,0,230,'Optional expansion',7.4,M)
 text(ax,0,253,'DATA + METHODS',7.5,P,True);text(ax,168,253,'ANALYSIS FREEZE',7.5,G,True);text(ax,332,253,'WRITE + DELIVER',7.5,B,True)
 text(ax,0,269,'Hatching: optional work · Diamonds: gates · Outlined effort ends: upper estimates',7.4,M)
 # Milestone cards encode concrete outputs rather than another numerical table.
 cards=[('G1 · 30 SEP','Access + schema','Confirm scope and dates',P),('18 DEC','Core corpus frozen','Audit sampling denominators',P),('G2 · 15 JAN','Measurement frozen','Validated labels + encoder',G),('G3 · 28 FEB','All analysis complete','Include robustness checks',G),('MAR–14 MAY','Thesis + feedback','Writing and rehearsal',B),('G4 · 11 JUN','Revision + release','Reproduction + presentation',B)]
 for i,(date,title,detail,c) in enumerate(cards):
  x=(i%3)*155;y=286+(i//3)*55;box(ax,x,y,143,47,c,r=6);text(ax,x+9,y+10,date,7.2,c,True);text(ax,x+9,y+25,title,8.3,c,True);text(ax,x+9,y+39,detail,7.0,M)
 text(ax,0,409,'Conditional on clarification of the published 26 Oct 2026 report deadline.',7.8,R,True)
 return save(fig,'figure_05_schedule')

def make_all():
 results=[f() for f in [relationships,mechanisms,rqmap,sampling,pipeline,evidence,temporal,risks,schedule]]
 qa=ROOT/'assets/visual_qa'
 run=subprocess.run([sys.executable,str(SCRIPTS/'validate_figure.py'),str(Path(__file__)),'--json'],capture_output=True,text=True)
 (qa/'source_preflight.json').write_text(run.stdout)
 return results
if __name__=='__main__':print('\n'.join(map(str,make_all())))
