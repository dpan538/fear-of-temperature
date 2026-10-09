"""Collection-frame diagnostic; all qualified IDs retained, no smoothing.

Conclusion: current newspaper and campus publication counts have different
observed temporal profiles; collection selection prevents population inference.
Single quantitative panel, 183 x 88 mm; counts have no sampling error bars.
"""
from pathlib import Path
import csv, os, sys
os.environ.setdefault('MPLCONFIGDIR','/tmp/fear-temperature-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, DateFormatter
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'tables/monthly_frame_coverage.csv').open()))
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':0.6,'legend.frameon':False})
fig,ax=plt.subplots(figsize=(7.204724,3.464567))
fig.subplots_adjust(left=.095,right=.985,bottom=.22,top=.83)
for frame,label,color in [('campus_publication','Campus publications (9,249)','#ba7a41'),('newspaper','Newspapers (3,085)','#276b8c')]:
    rs=[r for r in rows if r['analysis_frame']==frame and r['stratum']=='pooled']
    assert len(rs)==465
    ax.plot([datetime.strptime(r['month'],'%Y-%m') for r in rs],[int(r['native_article_IDs']) for r in rs],color=color,lw=.85,label=label)
ax.set_ylabel('Acquired article IDs per month')
ax.set_xlabel('Publication month (September 2026 is partial)')
ax.xaxis.set_major_locator(YearLocator(5));ax.xaxis.set_major_formatter(DateFormatter('%Y'))
ax.set_xlim(datetime(1988,1,1),datetime(2026,9,1));ax.set_ylim(bottom=0)
ax.legend(loc='upper left',ncol=2,bbox_to_anchor=(0,1.23),borderaxespad=0)
fig.text(.095,.035,'Observed collection only; no smoothing, downsampling, population weighting or event attribution.',fontsize=7)
fig.canvas.draw()
# A single panel has no comparable-panel alignment requirement.
(ROOT/'figures/alignment.json').write_text('{"status":"NOT_APPLICABLE","reason":"One quantitative panel"}\n')
fig.savefig(ROOT/'figures/monthly_collection.svg')
fig.savefig(ROOT/'figures/monthly_collection.pdf')
fig.savefig(ROOT/'figures/monthly_collection.png',dpi=300)
plt.close(fig)
