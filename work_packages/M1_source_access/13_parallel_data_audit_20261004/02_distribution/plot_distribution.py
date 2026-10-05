"""Two landscape, single-panel Python figures from distribution audit CSVs.

Run after build_distribution.py. All drawing, preview and exports use Matplotlib.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR','/private/tmp/fot_distribution_mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
OUT=HERE/'figures'
OUT.mkdir(exist_ok=True)
GOV='#6E4D9B'; INK='#1F2D3A'; MUTED='#637485'; LIGHT='#E8EDF0'; WARM='#C67738'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.titlesize':11,
                     'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,
                     'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,
                     'axes.spines.right':False,'savefig.facecolor':'white'})
plt.rcParams['font.family']='sans-serif'
plt.rcParams['font.sans-serif']=['DejaVu Sans']


def single_axes(fig,rect):
    return fig.add_axes(rect)


def save(fig,name):
    fig.savefig(OUT/f'{name}.png',dpi=320)
    fig.savefig(OUT/f'{name}.svg')
    fig.savefig(OUT/f'{name}.pdf')
    plt.close(fig)


def figure_1():
    """Claim: volume varies with source channel and month, including sharp low bins."""
    d=pd.read_csv(HERE/'monthly_source_genre_counts.csv')
    months=pd.period_range('1988-01','2026-09',freq='M').astype(str).tolist()
    series=[
      ('src_549acfda11091ff8c9b8','ministerial_written_answer','UK historic answers'),
      ('src_9e8f487d372ed011db82','ministerial_written_answer','UK archive answers'),
      ('src_90b3a872375c9e7fd267','ministerial_written_answer','UK API answers'),
      ('src_ac30b1ae596ab5ab5379','policy_paper','UK DEFRA papers'),
      ('us_fr_epa_doe_rules_1994','final_rule','US final rules'),
      ('us_fr_epa_doe_rules_1994','proposed_rule','US proposed rules'),
      ('EU_CELLAR_COM','COM preparatory Work','EU COM Works'),
    ]
    arr=[]
    for src,genre,_ in series:
        q=d[(d.source_id==src)&(d.genre==genre)&d.month.isin(months)].set_index('month').reindex(months)
        n=q.parent_count.to_numpy(dtype=float)
        active=q.in_observed_span.astype(bool).to_numpy()
        cap=max(np.quantile(n[active],.95),1)
        vals=np.clip(np.log1p(n)/np.log1p(cap),0,1)
        vals[~active]=np.nan
        arr.append(vals)
    z=np.ma.masked_invalid(np.array(arr))
    cmap=LinearSegmentedColormap.from_list('volume',['#E8EDF0','#B8A3D0',GOV,'#3D285D'])
    cmap.set_bad('white')
    f=plt.figure(figsize=(13.4,5.35),facecolor='white')
    f.text(.055,.936,'01  Monthly volume has source-specific gaps and clusters',fontsize=15.5,weight='bold',color=INK)
    f.text(.055,.894,'Independent parent/Work counts; colour is scaled to each row’s own 95th percentile, so rows are not directly comparable.',fontsize=9,color=MUTED)
    a=single_axes(f,[.18,.29,.76,.51])
    a.imshow(z,aspect='auto',interpolation='none',cmap=cmap,vmin=0,vmax=1)
    a.set_yticks(range(len(series)),[x[2] for x in series])
    ix=[0,60,120,180,240,300,360,420,464]
    a.set_xticks(ix,[months[i] for i in ix])
    a.set_xlim(-.5,len(months)-.5);a.set_ylim(len(series)-.5,-.5)
    a.axvline(months.index('2026-09')-.5,color=WARM,lw=1.2,ls='--')
    for y in np.arange(.5,len(series)-.5,1):a.axhline(y,color='white',lw=2)
    f.text(.18,.218,'Pale = low within that source frame  ·  dark = high  ·  white = outside observed dated span',fontsize=8.5,color=INK)
    f.text(.18,.178,'Examples: 1999/2000 September Commons recesses; 2013 April DEFRA policy-series cluster; sparse 1994 US selected metadata.',fontsize=8.2,color=MUTED)
    f.text(.055,.065,'Study publication interval: 1988-01-01–2026-09-21. September 2026 is partial. Zero means zero in the defined source frame.',fontsize=7.6,color=MUTED)
    f.text(.055,.039,'Source data: monthly_source_genre_counts.csv. Source checkpoints differ; this chart does not infer an event or cross-source rate.',fontsize=7.6,color=MUTED)
    save(f,'figure_01_monthly_intensity')


def figure_2():
    """Claim: object/version/segment totals are distinct from independent parents."""
    u=pd.read_csv(HERE/'unit_and_duplicate_diagnostics.csv')
    rows=[
      ('src_549acfda11091ff8c9b8','ministerial_written_answer','UK historic answers'),
      ('src_90b3a872375c9e7fd267','ministerial_written_answer','UK API answers'),
      ('src_9e8f487d372ed011db82','ministerial_written_answer','UK archive answers'),
      ('src_ac30b1ae596ab5ab5379','policy_paper','UK DEFRA papers'),
      ('us_fr_epa_doe_rules_1994','final_rule','US final rules'),
      ('EU_CELLAR_COM','COM preparatory Work','EU COM Works'),
      ('au_dcceew_current_catalogue_2026_snapshot','catalogue_publication_candidate','AU catalogue candidates'),
    ]
    f=plt.figure(figsize=(13.4,5.7),facecolor='white')
    f.text(.055,.94,'02  Content objects and versions are not parent records',fontsize=15.5,weight='bold',color=INK)
    f.text(.055,.899,'Distinct objects and saved content versions per 100 source-frame parents, candidates or Works; baseline = 100.',fontsize=9,color=MUTED)
    a=single_axes(f,[.24,.30,.69,.49])
    a.axvline(100,color=INK,lw=1.15,ls='--',zorder=0)
    for i,(src,genre,label) in enumerate(rows):
        x=u[(u.source_id==src)&(u.genre==genre)].iloc[0]
        ob=100*x.distinct_objects/x.parents
        ve=100*x.distinct_versions/x.parents
        y=len(rows)-1-i
        a.plot([ob,ve],[y,y],color='#B8A3D0',lw=2,zorder=1)
        a.scatter(ob,y,s=90,marker='s',facecolor='white',edgecolor=GOV,lw=1.6,zorder=3)
        a.scatter(ve,y,s=28,marker='o',facecolor=GOV,edgecolor=GOV,zorder=4)
        a.text(max(ob,ve)*1.10,y,f'{x.parents:,.0f} parents',va='center',fontsize=7.4,color=MUTED)
    a.set_xscale('log');a.set_xlim(.08,850);a.set_ylim(-.5,len(rows)-.5)
    a.set_yticks(range(len(rows)),[x[2] for x in rows[::-1]])
    a.set_xticks([.1,1,10,100,1000],['0.1','1','10','100','1,000'])
    a.grid(axis='x',color=LIGHT,zorder=0)
    a.set_xlabel('Distinct linked units per 100 source-frame parents / Works (log scale)')
    from matplotlib.lines import Line2D
    handles=[Line2D([0],[0],marker='s',color=GOV,markerfacecolor='white',lw=0,label='Content objects'),
             Line2D([0],[0],marker='o',color=GOV,markerfacecolor=GOV,lw=0,label='Saved content versions')]
    a.legend(handles=handles,loc='upper left',frameon=False,ncol=2,bbox_to_anchor=(0,1.10),fontsize=8)
    f.text(.055,.209,'UK source pages can hold many written-answer parents; DEFRA papers can have multiple attachments.',fontsize=8.5,color=INK)
    f.text(.055,.173,'US/EU gaps between parents and versions reflect saved-body depth. AU candidate counts are not verified original works.',fontsize=8.5,color=INK)
    f.text(.055,.122,'Separate extraction scale: 1,362 UK PDF objects generated 2,745,617 line/block segments (median 38 characters per segment).',fontsize=8,color=MUTED)
    f.text(.055,.089,'Segments and shared objects are not additive parent counts; linked objects may appear in more than one parent or month.',fontsize=8,color=MUTED)
    f.text(.055,.044,'Source data: unit_and_duplicate_diagnostics.csv; 21 Sep 2026 UK format summary. Source checkpoints are not synchronized.',fontsize=7.6,color=MUTED)
    save(f,'figure_02_count_units')


if __name__=='__main__':
    figure_1();figure_2()
    print('saved two landscape figures in',OUT)
