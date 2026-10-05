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
 fig,ax=canvas(230);heading(ax,'One social question, three discourse roles','How do warming-fear expressions change across roles and time?')
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
 fig,ax=canvas(247);heading(ax,'Research questions → computational tasks → evaluation','Three questions share one corpus, representation and validation protocol.')
 cols=[0,128,274];widths=[113,131,179]
 for x,s in zip(cols,['QUESTION','COMPUTATIONAL TASK','ANALYSIS + EVALUATION']):text(ax,x,45,s,7.2,M,True)
 rows=[(P,'RQ1','Who changes first?','Reference similarity','S / Q by source role','CCF / conditional VAR','Lags + held-out predictive gain'),(B,'RQ2','What changes at events?','Similarity + structure','S / Q; fixed summaries','Segmented regression / ITS','Level / slope + window checks'),(G,'RQ3','How is fear organised?','Similarity structure','Groups + source passages','Stability + context','Reference / source / period checks')]
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
 for i,(c,role,unit,den) in enumerate([(P,'Policy','policy documents','All eligible; same institution + genre'),(B,'Media','deduplicated articles','All eligible; same title + edition + bin'),(G,'Public','posts; comments separate','All eligible posts; same community')]):
  y=43+i*39
  box(ax,0,y,91,32,c,r=5);doc(ax,8,y+7,c,w=12,h=17);text(ax,29,y+16,role,8.8,c,True)
  arr(ax,(95,y+16),(111,y+16),c)
  text(ax,122,y+5,'Relevant '+unit.lower(),7.7,c,True)
  line(ax,118,y+16,339,y+16,c,.8)
  text(ax,122,y+27,den,7.7,INK)
  chip(ax,354,y+7,98,'Within-source S',c)
 text(ax,0,174,'Climate-only subsets support similarity analysis, not general attention estimates.',7.6,M)
 return save(fig,'figure_08_sampling')

def pipeline():
 fig,ax=canvas(263);heading(ax,'Fear references → embeddings → retrieval → structure','One bounded workflow; original passages remain linked to every result.')
 for x,c,lab in [(0,P,'Policy'),(155,B,'Media'),(310,G,'Public')]:
  box(ax,x,40,143,29,c,r=5);doc(ax,x+11,46,c,w=12,h=16);text(ax,x+35,55,lab,9,c,True)
  line(ax,x+71,72,x+71,81,c)
 line(ax,71,81,381,81,M);arr(ax,(226,81),(226,90),M)
 box(ax,112,92,230,29,P);text(ax,227,107,'Traceable passages + fear references',8.8,P,True,'center')
 line(ax,226,125,71,125,P);arr(ax,(71,125),(71,135),P)
 for x,c,t,sub in [(0,P,'MiniLM encoder','Versioned passage vectors'),(155,B,'FAISS retrieval','Ranked nearest neighbours'),(310,G,'Similarity hierarchy','Pilot validates merge rule')]:
  box(ax,x,138,143,43,c);text(ax,x+10,152,t,8.8,c,True);text(ax,x+10,169,sub,7.5,M)
 arr(ax,(143,159),(155,159),M);arr(ax,(298,159),(310,159),M)
 for x,c,t,sub in [(0,P,'Lexical baseline','Same judged queries'),(155,B,'ClimateBERT option','Separate representation'),(310,G,'Context checks','Counterexamples + stability')]:
  box(ax,x,196,143,37,c,fill='#F3F5F7');text(ax,x+10,208,t,8,c,True);text(ax,x+10,223,sub,7.3,M)
 text(ax,W/2,252,'VALIDATE  →  COMPARE ROLES / TIME  →  INTERPRET',8.7,P,True,'center')
 return save(fig,'figure_02_pipeline')

def evidence():
 fig,ax=canvas(205);heading(ax,'Fear remains the reference, not an assumed model label','Synthetic examples; topical similarity alone cannot establish fear.')
 rows=[(P,'I fear warming will harm my children.','Candidate reference: anticipated harm'),(B,'Heatwaves are deadly.','Counterexample: risk without expressed fear'),(G,'I am not afraid of warming.','Counterexample: explicit negation')]
 for i,(c,phrase,note) in enumerate(rows):
  y=41+i*45;box(ax,0,y,W,38,c,r=4);text(ax,10,y+12,phrase,9,c,True);text(ax,10,y+28,note,7.8,M)
 text(ax,0,190,'Inspect context → validate retrieval → interpret groups with original passages.',7.8,M)
 return save(fig,'figure_03_evidence')

def topology():
 fig,ax=canvas(228)
 heading(ax,'Different structures encode different relations','Design sketches only: grammar, similarity and temporal matching are distinct.')
 panels=[]
 for j in range(3):
  left=j*155
  a=fig.add_axes([left/W,37/228,143/W,147/228]);a.set_xlim(0,143);a.set_ylim(147,0);a.axis('off');panels.append(a)
  a.add_patch(Rectangle((0,0),143,147,facecolor='#F5F7F9',edgecolor=RULE,lw=.6))
 for a,title in zip(panels,['a  Sentence syntax','b  Passage similarity','c  Across-time groups']):text(a,7,12,title,8.2,INK,True)
 a=panels[0]
 for x,y,lab in [(70,42,'fear'),(28,88,'I'),(111,88,'warming')]:
  box(a,x-24,y-10,48,20,P);text(a,x,y,lab,8,P,True,'center')
 arr(a,(60,54),(32,75),M);arr(a,(82,54),(108,75),M)
 text(a,23,60,'subject',6.8,M);text(a,100,60,'object',6.8,M)
 text(a,8,119,'Tokens + grammatical edges',7.0,INK)
 text(a,8,134,'Not an emotion-cause model',6.8,M)
 a=panels[1]
 # An illustrative dendrogram; heights do not encode empirical distances.
 for x,y1,y2 in [(21,76,91),(56,76,91),(90,67,91),(122,67,91)]:line(a,x,y1,x,y2,M,1.1)
 line(a,21,76,56,76,M,1.1);line(a,90,67,122,67,M,1.1)
 line(a,38.5,76,38.5,42,M,1.1);line(a,106,67,106,42,M,1.1);line(a,38.5,42,106,42,M,1.1)
 for x,lab,c in [(21,'P1',P),(56,'M1',B),(90,'U1',G),(122,'U2',G)]:
  a.add_patch(Circle((x,98),8,facecolor=c,edgecolor='white',lw=.6));text(a,x,98,lab,6.5,'white',True,'center')
 text(a,8,119,'Leaves = passage IDs',7.0,INK)
 text(a,8,134,'Merges = modelled proximity',6.8,M)
 a=panels[2]
 text(a,32,35,'t1',7.5,M,True,'center');text(a,108,35,'t2',7.5,M,True,'center')
 for x1,y1,x2,y2 in [(39,55,99,51),(39,55,99,82),(39,94,99,82),(39,94,99,108)]:line(a,x1,y1,x2,y2,M,.8,ls='--')
 for x,y in [(31,55),(31,94),(108,51),(108,82),(108,108)]:a.add_patch(Circle((x,y),7,facecolor=PALE[B],edgecolor=B,lw=1))
 text(a,8,126,'Groups may split or merge',7.0,INK)
 text(a,8,140,'Matching is not diffusion',6.8,M)
 text(ax,0,207,'Core: similarity hierarchy. Syntax is diagnostic; temporal matching is conditional.',7.4,M)
 text(ax,0,222,'P / M / U: policy / media / public. All examples and connections are synthetic.',7.2,M)
 return save(fig,'figure_09_topology',axes=panels,groups=[{'id':'structural_scales','panels':['p0','p1','p2']}])

def temporal():
 fig,ax=canvas(248);heading(ax,'Measure the discourse, then test its timing','Illustrative trajectories only; no observed data or estimated effects.')
 for x,c,lab,sub in [(0,P,'S  Attention','Relevant / eligible'),(155,G,'q  Proximity','Cosine to fear references'),(310,B,'Q  Mean proximity','Within relevant discourse')]:
  box(ax,x,40,143,35,c,r=6);text(ax,x+10,52,lab,9.4,c,True);text(ax,x+10,67,sub,7.6,M)
 text(ax,0,93,'a   CCF / VAR: ordering',8.9,P,True);text(ax,252,93,'b   ITS: event response',8.9,B,True)
 h=fig._height
 left=fig.add_axes([10/W,(h-191)/h,206/W,82/h]);right=fig.add_axes([251/W,(h-191)/h,195/W,82/h])
 for a in [left,right]:
  a.spines[['top','right','left']].set_visible(False);a.spines['bottom'].set_color(RULE);a.set_yticks([]);a.tick_params(length=0,labelsize=7.2);a.set_ylim(0,1.25)
 x=np.linspace(0,1,160)
 for mu,c,lab,ls in [(0.34,P,'Policy','-'),(.50,B,'Media','--'),(.66,G,'Public',':')]:
  y=np.exp(-((x-mu)/.17)**2);left.plot(x,y,c=c,lw=1.8,ls=ls);left.fill_between(x,0,y,color=c,alpha=.10)
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
 for x0,c,lab,ls in [(0,P,'Policy','-'),(70,B,'Media','--'),(137,G,'Public',':')]:line(ax,x0,220,x0+14,220,c,2,ls);text(ax,x0+18,220,lab,7.5,c)
 text(ax,251,220,'Level / slope are distinct estimands.',7.5,M)
 text(ax,0,241,'Inputs: aligned S / Q and event dates. Outputs: lags, predictive gain and level / slope.',7.5,M)
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
 text(ax,0,337,'Decision rule: narrow the comparison early; retain validation and one validated structural comparison.',7.6,M)
 return save(fig,'figure_09_risk_routes')

def schedule():
 rows=list(csv.DictReader((ROOT/'assets/schedule_source.csv').open()))
 fig,ax=canvas(396);heading(ax,'A research calendar with protected analysis time','10–20 hours/week · planned task effort 450–590 h + 15% contingency')
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
 cards=[('G1 · 30 SEP','Access + schema','Confirm scope and dates',P),('18 DEC','Core corpus frozen','Audit sampling denominators',P),('G2 · 15 JAN','Measurement frozen','References + encoder fixed',G),('G3 · 28 FEB','All analysis complete','Include robustness checks',G),('MAR–14 MAY','Thesis + feedback','Writing and rehearsal',B),('G4 · 11 JUN','Revision + release','Reproduction + presentation',B)]
 for i,(date,title,detail,c) in enumerate(cards):
  x=(i%3)*155;y=286+(i//3)*55;box(ax,x,y,143,47,c,r=6);text(ax,x+9,y+10,date,7.2,c,True);text(ax,x+9,y+25,title,8.3,c,True);text(ax,x+9,y+39,detail,7.0,M)
 return save(fig,'figure_05_schedule')

def make_all():
 results=[f() for f in [relationships,mechanisms,rqmap,sampling,pipeline,evidence,topology,temporal,schedule]]
 qa=ROOT/'assets/visual_qa'
 run=subprocess.run([sys.executable,str(SCRIPTS/'validate_figure.py'),str(Path(__file__)),'--json'],capture_output=True,text=True)
 (qa/'source_preflight.json').write_text(run.stdout)
 return results
if __name__=='__main__':print('\n'.join(map(str,make_all())))
