"""Compact calendar/workload composite from explicit provisional planning records.
No observed research data, probability distribution or completed work is implied.
"""
from pathlib import Path
import os,sys,csv,json,datetime
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.runtime'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'qa'/'matplotlib'))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import ConnectionPatch
from matplotlib.font_manager import fontManager
sys.path.insert(0,str(ROOT.parent/'tools/nature-skills/skills/nature-figure/scripts'))
from audit_panel_alignment import require_matplotlib_panel_alignment
fontManager.addfont('/System/Library/Fonts/Supplemental/Arial.ttf')
fontManager.addfont('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.6,'legend.frameon':False,'savefig.facecolor':'white'})
P='#6D548F';INK='#293B49';GRAY='#647584';RED='#B34B55';LIGHT='#E4E8EC'

def make():
 rows=list(csv.DictReader((ROOT/'assets/schedule_source.csv').open()))
 dt=lambda s:mdates.date2num(datetime.date.fromisoformat(s))
 fig=plt.figure(figsize=(6.2991666667,3.4166666667),dpi=300)
 # Main calendar and subordinate workload panel share the same task rows.
 a=fig.add_axes([.224,.22,.505,.59]);b=fig.add_axes([.817,.22,.16,.59])
 for ax in [a,b]:
  ax.set_ylim(6.65,-.65);ax.tick_params(length=0,labelsize=7.7,pad=4);ax.spines[['left','right','top','bottom']].set_visible(False)
  ax.set_axisbelow(True)
 a.set_xlim(dt('2026-09-01'),dt('2027-06-30'));b.set_xlim(0,145)
 starts=['2026-09-01','2027-01-01','2027-03-01'];ends=['2027-01-01','2027-03-01','2027-07-01']
 for start,end,color in zip(starts,ends,['#F1EDF6','#EDF5F3','#EEF3F8']):a.axvspan(dt(start),dt(end),color=color,zorder=0)
 months=[datetime.date(2026+(m-1)//12,(m-1)%12+1,1) for m in range(9,19)]
 for date in months:a.axvline(mdates.date2num(date),color='#DCE3E8',lw=.45,zorder=1)
 mid=[mdates.date2num(x.replace(day=15)) for x in months]
 a.set_xticks(mid,[x.strftime('%b') for x in months]);a.xaxis.tick_top()
 a.set_yticks(range(7),[r['code']+('/'+r['gate'] if r['gate'] else '')+'  '+r['label'] for r in rows]+['Corpus expansion*'])
 a.tick_params(axis='y',labelsize=7.7,pad=8)
 b.set_yticks([]);b.set_xticks([0,70,140]);b.set_xlabel('Estimated hours',fontsize=8,labelpad=6)
 for y,r in enumerate(rows):
  start,end=dt(r['start']),dt(r['end']);col=r['color']
  a.plot([start,end],[y,y],color=col,lw=6.7,solid_capstyle='butt',zorder=4)
  # Gates and dependencies encode review steps, not progress percentages.
  if r['gate']:
   a.scatter([end],[y],marker='D',s=17,facecolors='white',edgecolors=col,linewidths=.8,zorder=5)
  lo,hi=int(r['hours_low']),int(r['hours_high'])
  b.plot([0,lo],[y,y],color=col,lw=5.2,solid_capstyle='butt')
  b.plot([lo,hi],[y,y],color='#CEDAE3',lw=5.2,solid_capstyle='butt')
  b.annotate(f'{lo}–{hi}',(0,y),xytext=(0,7),textcoords='offset points',fontsize=7.3,color=INK)
  a.axhline(y+.5,color='#DFE5E9',lw=.4,zorder=0)
 for idx in range(5):
  end=dt(rows[idx]['end']);target=max(end,dt(rows[idx+1]['start']))
  # A usable increment releases expansion; preparatory work can overlap.
  a.annotate('',xy=(target,idx+1-.23),xytext=(end,idx+.22),arrowprops=dict(arrowstyle='-|>',lw=.65,color=GRAY,connectionstyle='arc3,rad=0',mutation_scale=5),zorder=3)
 a.barh(6,dt('2026-12-18')-dt('2026-10-10'),left=dt('2026-10-10'),height=.25,facecolor='none',edgecolor='#7696AE',linewidth=.6,zorder=3)
 for xx in range(int(dt('2026-10-10'))+2,int(dt('2026-12-18'))-6,9):
  a.plot([xx,xx+6],[6.10,5.90],color='#7696AE',lw=.7,zorder=4)
 # Course markers are a separate calendar row above work rows.
 for date in ['2026-09-17','2026-10-14','2027-03-10','2027-05-12','2027-06-09']:
  a.scatter([dt(date)],[-.48],s=12,color='#AA7638',zorder=5,clip_on=False)
 a.axvline(dt('2026-10-26'),color=RED,ls=(0,(3,2)),lw=.8,zorder=2)
 a.axvline(dt('2027-03-01'),color=P,ls=(0,(2,2)),lw=.9,zorder=2)
 # Small hierarchy labels; the calendar receives the dominant visual area.
 fig.text(.008,.932,'a',fontsize=10,fontweight='bold',color=INK)
 fig.text(.047,.932,'Calendar, dependencies and gates',fontsize=9,fontweight='bold',color=INK)
 fig.text(.785,.932,'b',fontsize=10,fontweight='bold',color=INK)
 fig.text(.826,.932,'Workload',fontsize=9,fontweight='bold',color=INK)
 fig.text(.322,.867,'2026',fontsize=8,color=GRAY,ha='center');fig.text(.566,.867,'2027',fontsize=8,color=GRAY,ha='center')
 fig.text(.224,.139,'Data + methods',fontsize=7.6,color=P)
 fig.text(.440,.139,'Analysis',fontsize=7.6,color='#397D79')
 fig.text(.578,.139,'Write + deliver',fontsize=7.6,color='#477DAB')
 fig.text(.008,.078,'Diamonds: gates · Dots: course dates · * Optional expansion · Red: report-date conflict',fontsize=7.6,color=GRAY)
 fig.text(.008,.015,'450–590 h + 15% contingency · Analysis complete before March · Pale ends: upper estimates.',fontsize=7.6,color=GRAY)
 # Geometry is deliberately asymmetric: the calendar has ten time bins, workload one scale.
 require_matplotlib_panel_alignment(fig,json_out=ROOT/'assets/nature_qa/schedule.alignment.json',overlay_svg=ROOT/'assets/nature_qa/schedule.alignment.svg',tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True,axes=[a,b],panel_ids=['a','b'],row_groups=[{'id':'shared-task-rows','panels':['a','b']}],exemptions=[{'panels':['a','b'],'checks':['panel-width'],'reason':'Calendar hero panel requires ten month bins; workload is a subordinate common-row comparison.'}])
 out=ROOT/'assets/figure_05_schedule'
 fig.savefig(str(out)+'.pdf');fig.savefig(str(out)+'.svg');fig.savefig(str(out)+'.png',dpi=300)
 plt.close(fig)
 # Fresh source, typography and collision audits accompany every export.
 import subprocess
 scripts=ROOT.parent/'tools/nature-skills/skills/nature-figure/scripts'
 env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'.runtime')
 jobs=[('validate_figure.py',[str(Path(__file__)), '--json'],'schedule.source.json'),('audit_pdf_text.py',[str(out)+'.pdf','--min-pt','5','--json'],'schedule.text.json'),('audit_figure_collisions.py',[str(out)+'.pdf','--json-out',str(ROOT/'assets/nature_qa/schedule.collisions.json'),'--overlay-pdf',str(ROOT/'assets/nature_qa/schedule.collisions.pdf')],None)]
 for script,args,report in jobs:
  run=subprocess.run([sys.executable,str(scripts/script),*args],capture_output=True,text=True,env=env)
  if report:(ROOT/'assets/nature_qa'/report).write_text(run.stdout)
  if run.returncode:raise RuntimeError(script+' failed: '+run.stdout+run.stderr)
 return out
if __name__=='__main__':print(make())
