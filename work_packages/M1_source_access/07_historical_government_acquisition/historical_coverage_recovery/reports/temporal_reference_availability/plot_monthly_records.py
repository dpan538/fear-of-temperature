"""Three chronological monthly panels; observed record counts, no inference.

Contract: locate months with/without records and show genre composition.
Archetype: quantitative grid, three user-requested chronological strata.
Style-only inheritance from the existing project palette and Arial typography.
All 465 months and all 248,035 records are retained. No interpolation or smoothing.
Policy date basis is the current stored date, not a new original-publication audit.
"""
from pathlib import Path
import sys
import json
import math
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import StrMethodFormatter

sys.path.insert(0, str(Path.home()/'.codex/skills/nature-figure/scripts'))
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures'
OUT.mkdir(exist_ok=True)
src=pd.read_csv(ROOT/'monthly_reference_availability.csv')
data=src.pivot(index='year_month',columns='series',values='record_count').astype(int)
assert len(data)==465 and int(data.to_numpy().sum())==248035
assert (data.to_numpy()>=0).all()
data.to_csv(ROOT/'monthly_record_counts_wide.csv')
COLORS={'policy_document':'#24495F','ministerial_written_answer':'#C57A43','ministerial_written_statement':'#6F7D4C'}
LABELS={'policy_document':'Policy records','ministerial_written_answer':'Written answers','ministerial_written_statement':'Written statements'}
ORDER=['ministerial_written_answer','ministerial_written_statement','policy_document']
INK='#20303A';MUTED='#5D6A70';GAP='#F4E4E1';GRID='#DFE3E4'
plt.rcParams['font.family']='sans-serif'
plt.rcParams['font.sans-serif']=['Arial','DejaVu Sans','Liberation Sans']
mpl.rcParams.update({"svg.fonttype": "none"})
mpl.rcParams.update({'font.size':10,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9,'legend.fontsize':11,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'savefig.facecolor':'white','text.color':INK,'axes.labelcolor':INK,'xtick.color':MUTED,'ytick.color':MUTED})
fig,axes=plt.subplots(3,1,figsize=(18,10))
fig.subplots_adjust(left=.065,right=.985,bottom=.145,top=.805,hspace=.69)
fig.text(.065,.956,'Monthly government records across the study period',fontsize=22,fontweight='bold')
fig.text(.065,.915,'January 1988 to 21 September 2026  |  One bar per month  |  Stacked genres; shared count scale',fontsize=12,color=MUTED)
handles=[Patch(facecolor=COLORS[k],label=LABELS[k],edgecolor='none') for k in ['policy_document','ministerial_written_answer','ministerial_written_statement']]
handles.append(Patch(facecolor=GAP,label='No records in any of the three genres',edgecolor='none'))
fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.061,.883),ncol=4,frameon=False,handlelength=1.5,columnspacing=2)
ylim=math.ceil(float(data.sum(axis=1).max())/500)*500
summary=[]
for ax,(lo,hi),panel in zip(axes,[(1988,2000),(2001,2013),(2014,2026)],'abc'):
 subset=data[(data.index.str[:4].astype(int)>=lo)&(data.index.str[:4].astype(int)<=hi)]
 n=len(subset);x=np.arange(n);totals=subset.sum(axis=1);empty=np.flatnonzero(totals.to_numpy()==0)
 for i in empty:ax.axvspan(i-.5,i+.5,color=GAP,linewidth=0,zorder=0)
 ax.set_axisbelow(True);ax.grid(axis='y',color=GRID,linewidth=.55)
 bottom=np.zeros(n)
 for key in ORDER:
  vals=subset[key].to_numpy();ax.bar(x,vals,bottom=bottom,width=.86,color=COLORS[key],linewidth=0,zorder=2)
  bottom+=vals
 ax.set_ylim(0,ylim);ax.set_xlim(-.65,155.65)
 ax.set_yticks(np.arange(0,ylim+1,500));ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
 ax.set_ylabel('Records (count)',labelpad=12)
 ax.spines['left'].set_color('#B9C2C6');ax.spines['bottom'].set_color('#B9C2C6')
 ax.tick_params(axis='y',length=0,pad=5)
 ax.set_xticks([])
 for i,m in enumerate(subset.index):
  month=int(m[5:]);ax.text(i,-.085,'JFMAMJJASOND'[month-1],ha='center',va='top',fontsize=6.8,color=MUTED,transform=ax.get_xaxis_transform())
  if month==1:
   ax.text(i+5.5,-.205,m[:4],ha='center',va='top',fontsize=10,transform=ax.get_xaxis_transform())
   if i:ax.axvline(i-.5,color=GRID,linewidth=.5,zorder=0)
 period=f'{lo}–{hi}' if hi!=2026 else '2014–September 2026'
 ax.text(-.034,1.10,panel,transform=ax.transAxes,fontsize=14,fontweight='bold',va='bottom')
 ax.text(0,1.10,period,transform=ax.transAxes,fontsize=13,fontweight='bold',va='bottom')
 detail=f'{int(totals.sum()):,} records  |  {n-len(empty)}/{n} months with records  |  {len(empty)} empty months'
 ax.text(1,1.10,detail,transform=ax.transAxes,ha='right',va='bottom',fontsize=10,color=MUTED)
 if n<156:ax.axvspan(n-.5,155.65,color='#F3F4F4',linewidth=0,zorder=0)
 summary.append({'period':period,'months':n,'empty_months':len(empty),'records':int(totals.sum()),'counts':{k:int(subset[k].sum()) for k in ORDER}})
fig.text(.065,.062,'Counts use the current stored publication date. GOV.UK page dates may differ from original policy publication dates; historical date review is pending.',fontsize=10,color=MUTED)
fig.text(.065,.034,'Shading marks zero stored records, not proof of no historical publications. September 2026 is partial; October–December 2026 are outside the cutoff.',fontsize=10,color=MUTED)
fig.canvas.draw()
stem=OUT/'monthly_government_records_landscape'
require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',overlay_svg=str(stem)+'.alignment.svg',strict=True,tolerance_pt=1.5,gutter_tolerance_pt=1.5)
fig.savefig(OUT/'monthly_government_records_landscape.pdf')
fig.savefig(OUT/'monthly_government_records_landscape.svg')
fig.savefig(str(stem)+'.png',dpi=300)
(OUT/'monthly_government_records_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'png':str(stem)+'.png','pixels':[5400,3000],'records':248035,'months':465,'empty_months':sum(r['empty_months'] for r in summary)}))
