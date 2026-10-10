"""Closed metadata review. No database, raw payload, body or collector access.

Run from the repository root with .venv/bin/python. Inputs are explicit metadata
paths; each selected input is hashed before analysis and checked again afterward.
"""
from pathlib import Path
import json, hashlib, sys, argparse
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import ticker

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--only',help='Export only this figure stem; existing other exports remain unchanged')
ARGS=parser.parse_args()

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
FIG = OUT.parent / 'figures'
QA = OUT / 'qa'
for p in [FIG, QA]: p.mkdir(parents=True, exist_ok=True)
SKILL = Path('/Users/jarlgiovanni/.codex/skills/nature-figure/scripts')
sys.path.insert(0, str(SKILL))
from audit_panel_alignment import require_matplotlib_panel_alignment
P27 = ROOT / 'work_packages/M1_source_access/27_newspaper_context_recovery_20261008'
NP = P27 / 'continuations/20261010_eight_hour_focused_repair/worker'
SOC = P27 / 'social_public_api/continuations/20261010_eight_hour_focused_repair/worker'
PRE = P27 / 'social_public_api/continuations/20261010_broader_history_four_hour/worker'
PAR = ROOT / 'work_packages/M1_source_access/30_media_2026_source_review_20261010/PARENT_SOURCE_EVIDENCE.csv'
inputs = []
def pin(p):
    p = Path(p)
    original=p
    closed=OUT.parent/'closed'
    if p.is_relative_to(NP): candidate=closed/'eight_hour/newspaper'/p.name
    elif p.is_relative_to(SOC): candidate=closed/'eight_hour/social'/('collection_manifest.json' if p.name=='CLOSED.json' else p.name)
    elif p.is_relative_to(PRE): candidate=closed/'broader_history/social'/p.name
    else: candidate=p
    if candidate.exists(): p=candidate
    inputs.append({'path': str(p.relative_to(ROOT)), 'original_metadata_path':str(original.relative_to(ROOT)), 'bytes': p.stat().st_size,
                   'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    return p
def csv(p): return pd.read_csv(pin(p))
def js(p): return json.loads(pin(p).read_text())
def dump(name, value): (OUT/name).write_text(json.dumps(value, indent=2, default=lambda v: v.item() if hasattr(v,'item') else str(v))+'\n')
def export(name, frame): frame.to_csv(OUT/name, index=False)

n = csv(NP/'MONTHLY_BEFORE_AFTER.csv')
nb = csv(NP/'MONTH_SOURCE_COUNTS_BEFORE.csv')
na = csv(NP/'MONTH_SOURCE_COUNTS_AFTER.csv')
legacy = csv(NP/'LEGACY_AFFECTED_MONTH_BEFORE_AFTER.csv')
nr = csv(NP/'CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv')
ng = csv(NP/'NEW_SOURCE_PURPOSE_GENRE_ERA_REGISTER.csv')
front = csv(NP/'SOURCE_FRONTIER_REGISTER.csv')
ns = js(NP/'DELIVERY_SUMMARY.json')
sc = csv(SOC/'summaries/source_month_calendar.csv')
sb = csv(PRE/'summaries/source_month_calendar.csv')
sd = csv(SOC/'summaries/source_month_deltas.csv')
matched = csv(SOC/'summaries/matched_year_source_genre_panel.csv')
registry = js(SOC/'summaries/source_registry_final.json')
ss = js(SOC/'CLOSED.json')
facts = {'source_stop_reason':ss['stop']['reason']}
caps = js(SOC/'summaries/collection_manifest.json')
peaks = js(SOC/'summaries/native_operation_peak_summary.json')
meta_peak = js(SOC/'summaries/metadata_operation_peak_summary.json')
parent = csv(PAR)
publication_accounting=js(OUT/'COORDINATOR_PUBLICATION_ACCOUNTING_NOTE.json')
months = pd.period_range('1988-01','2026-09',freq='M').astype(str)

monthly = []
for stream, before, after in [
    ('newspaper', n.set_index('publication_month').before_complete_article_IDs,
     n.set_index('publication_month').after_complete_article_IDs),
    ('social', sb.groupby('month').usable_dated_independent_bodies.sum(),
     sc.groupby('month').usable_dated_independent_bodies.sum())]:
    x = pd.DataFrame({'month': months})
    x['stream'] = stream
    x['before'] = x.month.map(before).fillna(0).astype(int)
    x['after'] = x.month.map(after).fillna(0).astype(int)
    x['delta'] = x.after-x.before
    assert (x.delta>=0).all()
    monthly.append(x)
monthly = pd.concat(monthly, ignore_index=True)
assert monthly.query("stream=='newspaper'").after.sum()==ns['current_newspaper_complete_IDs']
assert monthly.query("stream=='social'").after.sum()==ss['usable_dated_body_total']
assert monthly.query("stream=='social'").delta.sum()==ss['new_usable_dated_bodies']
assert nr.article_id.nunique()==ns['current_newspaper_complete_IDs']
assert ng.article_id.nunique()==ns['additional_qualified_IDs']
assert n.new_IDs.sum()==ng.article_id.nunique()
export('monthly_before_after.csv', monthly)
monthly['year']=monthly.month.str[:4].astype(int)
annual=monthly.groupby(['stream','year'],as_index=False)[['before','after','delta']].sum()
export('annual_before_after.csv', annual)

genre = matched[['source_id','genre_basis_from_source_frame']].drop_duplicates().set_index('source_id').genre_basis_from_source_frame.to_dict()
titles={r['source_id']:r.get('title',r['source_id']) for r in registry}
titles.update({k:k.replace('_',' ').title() for k in na.source_id.unique()})
titles.update({'berkeley_daily_planet':'Berkeley Daily Planet','green_left':'Green Left',
 'your_local_examiner_au':'Examiner publisher web frame','cambridge_news_nz':'Cambridge News (NZ)',
 'te_awamutu_news':'Te Awamutu News','munster_express':'The Munster Express',
 'mountain_times_vt':'Mountain Times (Vermont)'})
source_frames=[]
for stream,b,a,monthcol,countcol in [('newspaper',nb,na,'publication_month','complete_article_IDs'),
                                  ('social',sb,sc,'month','usable_dated_independent_bodies')]:
    bs=b.groupby('source_id')[countcol].sum()
    for source,g in a.groupby('source_id'):
        keep=g[g[countcol]>0]
        if keep.empty: continue
        old=int(bs.get(source,0)); now=int(keep[countcol].sum())
        newg=ng[ng.source_id==source]
        purpose='; '.join(sorted(newg.source_purpose_frame.dropna().unique())) if stream=='newspaper' else genre.get(source,'unresolved structural source frame')
        source_frames.append({'stream':stream,'source_id':source,'display_title':titles.get(source,source),
          'before':old,'after':now,'delta':now-old,'new_contributing_source':old==0,
          'observed_months':len(keep),'first_observed_month':keep[monthcol].min(),
          'last_observed_month':keep[monthcol].max(),'structural_purpose_or_genre':purpose,
          'historical_inventory_denominator':'unknown; observed native routes are not full archive'})
sources=pd.DataFrame(source_frames)
export('source_before_after_and_era.csv',sources)
export('new_contributing_source_genre_era.csv',sources[sources.new_contributing_source])
export('legacy_month_recovery.csv',legacy)
export('newspaper_new_structural_genre_by_year.csv',ng.groupby(
 ['source_id','publication_year','source_purpose_frame','native_genre_basis'],dropna=False).size().reset_index(name='new_complete_article_IDs'))
sg=sd.copy();sg['publication_year']=sg.month.str[:4].astype(int)
sg['source_frame_genre']=sg.source_id.map(genre).fillna('unresolved structural source frame')
export('social_new_source_genre_by_year.csv',sg.groupby(
 ['source_id','publication_year','source_frame_genre'],as_index=False).new_usable_dated_bodies.sum())
export('pooled_empty_months.csv',monthly[monthly.after==0][['stream','month','before','after']])
export('social_applicability_states.csv',sc.groupby('source_era_applicability',as_index=False).agg(
    source_month_cells=('source_id','size'),dated_bodies=('usable_dated_independent_bodies','sum')))

matched_summary=matched.groupby('year',as_index=False)[['baseline_Jan_Aug_usable_bodies','new_Jan_Aug_usable_bodies','current_Jan_Aug_usable_bodies']].sum()
export('matched_Jan_Aug_2016_2026.csv',matched_summary)
existing=set(sources.query("stream=='social' and before>0").source_id)
fixed=matched[matched.source_id.isin(existing)].groupby('year',as_index=False)[['baseline_Jan_Aug_usable_bodies','current_Jan_Aug_usable_bodies']].sum()
export('matched_baseline_contributing_source_panel.csv',fixed)

current_np_assertions={
 'cambridge_news_nz':('Good Local Media Ltd','https://www.cambridgenews.nz/about/about-us/','ddc7ef6320ff3219e5fe6fae'),
 'te_awamutu_news':('Good Local Media Ltd','https://www.teawamutunews.nz/about/about-us/','43064620101095baf982eb3f'),
 'waltham_forest_echo':('Social Spider CIC, publisher on behalf of WF WellComm CIC','https://walthamforestecho.co.uk/about/','8d3cc3ff440e7fc1e82e6ccc'),
 'enfield_dispatch':('Social Spider Community News; privacy names Social Spider CIC','https://enfielddispatch.co.uk/about/','22ddb14d2344af08a1eae09a')}
export('current_newspaper_parent_assertions.csv',pd.DataFrame([
 {'source_id':k,'dimension':'publisher_organization','parent_assertion':v[0],
  'primary_url':v[1],'receipt_reference':v[2],'status':'supported_current_primary_assertion',
  'historical_validity':'unknown; publisher/operator assertion is not a historical owner/community mapping',
  'metadata_evidence':'closed/eight_hour/newspaper/DELIVERY_SUMMARY.json: source_admission_and_limits'}
 for k,v in current_np_assertions.items()]))
parent_rows=[]
for stream,dimension in [('newspaper','publisher_organization'),('social','platform_network'),('social','community')]:
    sf=sources[sources.stream==stream]
    for r in sf.itertuples():
        evidence=parent[(parent.stream==stream)&(parent.source_id==r.source_id)&(parent.relation_dimension==dimension)]
        e=evidence.iloc[0] if len(evidence)==1 else None
        status=e.evidence_status if e is not None else 'unmapped_in_bounded_review'
        row={'stream':stream,'dimension':dimension,'source_id':r.source_id,
         'bodies':r.after,'mapping_status':status,
         'parent_id_or_label':e.parent_id_or_label if e is not None else 'unmapped',
         'assertion_id':e.assertion_id if e is not None else '',
         'valid_time_limit':e.valid_time_limit if e is not None else 'no reviewed parent assertion',
         'historical_applicability':'not established for entire publication interval'}
        if stream=='newspaper' and r.source_id in current_np_assertions:
            current=current_np_assertions[r.source_id]
            row.update(mapping_status='supported_current_primary_assertion',parent_id_or_label=current[0],
             assertion_id='closed_source_admission:'+r.source_id,valid_time_limit='current publisher assertion; historical owner/operator periods unresolved')
        parent_rows.append(row)
pm=pd.DataFrame(parent_rows);export('parent_dimension_mappings.csv',pm)
ps=pm.groupby(['stream','dimension','mapping_status'],as_index=False).agg(source_ids=('source_id','nunique'),bodies=('bodies','sum'))
export('parent_mapping_coverage.csv',ps)

metrics={}
for stream in ['newspaper','social']:
    f=monthly[monthly.stream==stream]; src=sources[sources.stream==stream]
    metrics[stream]={'before_units':int(f.before.sum()),'after_units':int(f.after.sum()),'added_units':int(f.delta.sum()),
     'before_observed_months':int((f.before>0).sum()),'after_observed_months':int((f.after>0).sum()),
     'zero_months_after':int((f.after==0).sum()),'one_months_after':int((f.after==1).sum()),
     'two_months_before':int((f.before==2).sum()),'two_months_after':int((f.after==2).sum()),
     'before_contributing_source_ids':int((src.before>0).sum()),'after_contributing_source_ids':len(src),
     'new_contributing_source_ids':src[src.new_contributing_source].source_id.tolist(),
     '2026_full_history_share_before':float(f[f.year==2026].before.sum()/f.before.sum()),
     '2026_full_history_share_after':float(f[f.year==2026].after.sum()/f.after.sum())}
metrics['social']['matched_Jan_Aug_2016_2026_share_before']=float(matched_summary.query('year==2026').baseline_Jan_Aug_usable_bodies.sum()/matched_summary.baseline_Jan_Aug_usable_bodies.sum())
metrics['social']['matched_Jan_Aug_2016_2026_share_after']=float(matched_summary.query('year==2026').current_Jan_Aug_usable_bodies.sum()/matched_summary.current_Jan_Aug_usable_bodies.sum())
metrics['social']['baseline_source_panel_share_after']=float(fixed.query('year==2026').current_Jan_Aug_usable_bodies.sum()/fixed.current_Jan_Aug_usable_bodies.sum())
metrics['social']['applicability_state_cells']=sc.source_era_applicability.value_counts().to_dict()
metrics['social']['independently_evidenced_community_family_count']='unresolved in this bounded review; source-frame ledger is not an independent-parent map'
metrics['social']['named_strict_discussion_forums']=publication_accounting['named_strict_discussion_forums']
metrics['social']['named_QA_communities']=publication_accounting['named_QA_communities']
metrics['social']['community_classification_basis']=publication_accounting['community_classification_basis']
metrics['legacy_GL']={'affected_months':len(legacy),'months_with_surplus':int((legacy.new_GL_complete_IDs>0).sum()),
 'new_GL_IDs':int(legacy.new_GL_complete_IDs.sum()),'final_total_frequencies':{str(k):int(v) for k,v in legacy.after_total_complete_IDs.value_counts().sort_index().items()},
 'final_4_or_5_months':int(legacy.after_total_complete_IDs.isin([4,5]).sum()),'inventory_exhaustion_claimed':False}
metrics['publication_interval']=['1988-01-01','2026-09-21']
metrics['social_stop']=facts['source_stop_reason'];metrics['newspaper_stop']=ns['stop_reason']
metrics['snapshot_at_utc']={'newspaper':ns['at_utc'],'social':ss['at_utc']}
metrics['coordinator_publication_accounting']=publication_accounting
metrics['source_id_proxy_is_not_independent_parent_count']=True
metrics['semantic_labels_or_scores_executed']=False
metrics['input_scope']='explicit finalized metadata only; no database/raw/body reads'
dump('METRICS.json',metrics)

BLUE='#306899'; TEAL='#198A85'; GRAY='#A4AFB7'; ORANGE='#BB7936'; DARK='#243747'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','Helvetica','DejaVu Sans'],'font.size':10,'axes.titlesize':12,'axes.labelsize':10,
 'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'legend.frameon':False,
 'pdf.fonttype':42,'svg.fonttype':'none','figure.facecolor':'white','savefig.facecolor':'white'})
figure_contract=[]
def start(name,title,subtitle,shape=(1,2),size=(16,9)):
    fig,axes=plt.subplots(*shape,figsize=size,squeeze=False)
    fig.subplots_adjust(left=.08,right=.96,bottom=.17,top=.80,wspace=.30,hspace=.50)
    fig.text(.055,.965,title,fontsize=20,color=DARK,va='top')
    fig.text(.055,.91,subtitle,fontsize=10.5,color='#536674',va='top')
    figure_contract.append({'figure':name,'claim':title,'archetype':'quantitative grid',
     'backend':'Python/matplotlib','export':'PNG delivery; PDF/SVG for local QA',
     'size_inches':size,'units':'retained metadata counts; no uncertainty intervals or population estimates'})
    return fig,axes
def end(fig,name,footer):
    if ARGS.only and ARGS.only!=name:
        plt.close(fig)
        return
    fig.text(.055,.065,footer,fontsize=9,color='#536674',va='top',linespacing=1.5)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=QA/(name+'.alignment.json'),strict=True)
    fig.savefig(FIG/(name+'.png'),dpi=300)
    fig.savefig(QA/(name+'.pdf'))
    fig.savefig(QA/(name+'.svg'))
    plt.close(fig)
def label(ax,text): ax.set_title(text,loc='left',pad=15)
def fmt(ax): ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))

name='01_coverage_and_month_depth'
fig,axes=start(name,'Newspaper month gaps shrink; social month presence is unchanged',
 'Before/after retained units across all 465 study months. Counts describe observed collection, not archive completion.')
depthrows=[]
bins=[-1,0,1,2,9,49,np.inf]; names=['0','1','2','3–9','10–49','50+']
for ax,stream,color,letter in zip(axes[0],['newspaper','social'],[BLUE,TEAL],['a','b']):
 f=monthly[monthly.stream==stream]
 for j,col in enumerate(['before','after']):
  count=pd.cut(f[col],bins,labels=names).value_counts(sort=False).reindex(names).astype(int)
  b=ax.bar(np.arange(6)+(j-.5)*.38,count,width=.36,color=GRAY if j==0 else color,label=col.capitalize())
  ax.bar_label(b,padding=4,fontsize=9)
  depthrows.extend([{'stream':stream,'snapshot':col,'bin':k,'months':int(v)} for k,v in count.items()])
 ax.set_ylim(0,max(350,int(count.max())*1.18));ax.set_xticks(range(6),names);ax.set_xlabel('Retained units per publication month');ax.set_ylabel('Study months');ax.legend()
 m=metrics[stream];label(ax,f'{letter}  {stream.capitalize()} · observed {m["before_observed_months"]} → {m["after_observed_months"]} / 465')
export('monthly_depth_bins.csv',pd.DataFrame(depthrows))
end(fig,name,'Newspaper: complete article IDs. Social: usable dated independent bodies. Social full-calendar zero bins mix applicability and access limits.\nSeptember 2026 ends on 21 September; neutral/noisy material is retained. No monthly amount is a completion gate.')

name='02_monthly_and_annual_distribution'
fig,axes=start(name,'Historical additions remain uneven across publication time',
 'All monthly bins and annual aggregates are retained; no smoothing, downsampling or peak removal.',(2,2),(16,11))
for col,stream,color in [(0,'newspaper',BLUE),(1,'social',TEAL)]:
 f=monthly[monthly.stream==stream]; a=annual[annual.stream==stream]
 ax=axes[0,col];ax.plot(range(465),f.before,color=GRAY,lw=1,label='Before');ax.plot(range(465),f.after,color=color,lw=1.15,label='After')
 ax.set_yscale('symlog',linthresh=1);ax.set_xticks([0,84,204,324,456],['1988','1995','2005','2015','2026']);ax.set_ylabel('Units / month (symlog)');ax.legend()
 label(ax,f'{"a" if col==0 else "b"}  {stream.capitalize()} · monthly')
 ax=axes[1,col];ax.bar(a.year,a.before,color=GRAY,label='Before');ax.bar(a.year,a.delta,bottom=a.before,color=color,label='This round')
 ax.set_yscale('symlog',linthresh=1);ax.set_xlabel('Publication year');ax.set_ylabel('Units / year (symlog)');ax.legend(loc='upper left',bbox_to_anchor=(0,1.33),ncol=2,fontsize=8.5)
 label(ax,f'{"c" if col==0 else "d"}  {stream.capitalize()} · annual')
end(fig,name,'Symlog retains zero and uses a linear interval ±1, then logarithmic scaling. 2026 is incomplete and has narrower source observation horizons.\nThese are acquired-record distributions. They do not estimate discourse intensity or establish climate-event causes.')

name='03_matched_recent_years'
m=metrics['social']
fig,axes=start(name,'A lower full-history 2026 share does not remove recent-period concentration',
 f'Social 2026 share: full history {m["2026_full_history_share_before"]:.1%} → {m["2026_full_history_share_after"]:.1%}; matched January–August {m["matched_Jan_Aug_2016_2026_share_before"]:.1%} → {m["matched_Jan_Aug_2016_2026_share_after"]:.1%}.')
for ax,g,letter,heading in [(axes[0,0],matched_summary,'a','All contributing source frames'),(axes[0,1],fixed,'b','Baseline contributing source frames retained')]:
 x=np.arange(len(g));ax.bar(x-.18,g.baseline_Jan_Aug_usable_bodies,width=.35,color=GRAY,label='Before');ax.bar(x+.18,g.current_Jan_Aug_usable_bodies,width=.35,color=TEAL,label='After')
 ax.set_xticks(x,g.year,rotation=45,rotation_mode='anchor',ha='right');ax.set_ylabel('Usable dated bodies, January–August');fmt(ax);ax.legend();label(ax,f'{letter}  {heading}')
end(fig,name,'Both panels match calendar months across 2016–2026. The fixed source frame removes newly contributing sources only for this declared comparison.\nIt does not hold each source’s inventory, access, author mix or observation probability constant; no prevalence or representativeness claim follows.')

name='04_source_expansion_and_eras'
fig,axes=start(name,'This round adds actual contributing source frames across several eras',
 'Orange: first contribution in this round. Blue/teal: further acquisition from an existing contributing frame.',(1,2),(18,13))
fig.subplots_adjust(left=.19,right=.97,wspace=.55,top=.84,bottom=.13)
for ax,stream,color,letter in zip(axes[0],['newspaper','social'],[BLUE,TEAL],['a','b']):
 g=sources[(sources.stream==stream)&(sources.delta>0)].sort_values('delta')
 ax.barh(range(len(g)),g.delta,color=[ORANGE if v else color for v in g.new_contributing_source],height=.66)
 labs=[f'{r.display_title[:43]}  [{r.first_observed_month[:4]}–{r.last_observed_month[:4]}]' for r in g.itertuples()]
 ax.set_yticks(range(len(g)),labs,fontsize=8.5);ax.set_xlabel('New retained units in this round');ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
 ax.set_xlim(0,g.delta.max()*1.23)
 for i,r in enumerate(g.itertuples()):ax.text(r.delta+g.delta.max()*.012,i,f'{r.delta:,}',va='center',fontsize=8.5)
 mm=metrics[stream];label(ax,f'{letter}  {stream.capitalize()} · source IDs {mm["before_contributing_source_ids"]} → {mm["after_contributing_source_ids"]}')
end(fig,name,'Bracketed years are each source’s retained observation span, not its founding year or a complete archive. Full structural purpose/genre and era tables accompany this plot.\nA combined newspaper web frame counts once; technical lists, Q&A communities and platform instances remain distinct. Source IDs are not independent parents.')

name='05_legacy_recovery_depth'
L=metrics['legacy_GL']
fig,axes=start(name,'Legacy same-month surplus was loaded; most affected months remain shallow',
 f'All {L["affected_months"]} named Green Left affected months gained surplus ({L["new_GL_IDs"]} IDs); {L["final_4_or_5_months"]} now have four or five total newspaper IDs.')
ax=axes[0,0];g=legacy.sort_values('publication_month');x=np.arange(len(g))
ax.bar(x,g.new_GL_complete_IDs,color=BLUE,width=.8);ax.set_xticks(np.arange(0,len(g),12),g.publication_month.iloc[::12],rotation=45,rotation_mode='anchor',ha='right');ax.set_ylabel('Additional Green Left IDs');ax.set_xlabel('Named affected publication months');label(ax,'a  Per-month recovery from retained inventory')
ax=axes[0,1];v=g.after_total_complete_IDs.value_counts().sort_index();b=ax.bar(range(len(v)),v.values,color=BLUE);ax.bar_label(b,padding=4);ax.set_xticks(range(len(v)),v.index);ax.set_ylim(0,v.max()*1.2);ax.set_xlabel('Final total newspaper IDs / affected month');ax.set_ylabel('Affected months');label(ax,'b  Depth after recovery')
end(fig,name,'Original processed-directory flags and all originals are preserved. Committed surplus proves one repaired path; the observed inventory is not certified exhausted.\nThis clustering is a diagnostic for remaining progression/recovery questions, not a new minimum, forced histogram or instruction to flatten real peaks.')

name='06_parent_mapping_limits'
fig,axes=start(name,'Publisher, platform and community mappings answer different questions',
 'Bounded prior mappings plus four current publisher assertions. Unreviewed sources remain unmapped; historical ownership stays unresolved.',(1,2),(16,9))
fig.subplots_adjust(left=.18,right=.97,wspace=.50)
dimensions=[('newspaper','publisher_organization','Newspaper publisher'),('social','platform_network','Social platform network'),('social','community','Social community')]
rows=[]
for stream,dim,labeltext in dimensions:
 g=pm[(pm.stream==stream)&(pm.dimension==dim)]
 confirmed=g[g.mapping_status.isin(['confirmed','supported_current_primary_assertion'])]
 rows.append((labeltext,len(confirmed),len(g)-len(confirmed),confirmed.bodies.sum()/g.bodies.sum()*100))
ax=axes[0,0];x=np.arange(3);a=np.array([r[1] for r in rows]);b=np.array([r[2] for r in rows]);ax.barh(x,a,color=TEAL,label='Current assertion / prior confirmed');ax.barh(x,b,left=a,color=GRAY,label='Unresolved / unreviewed');ax.set_yticks(x,[r[0] for r in rows]);ax.set_xlabel('Contributing source IDs with dimension mapping');ax.legend(loc='lower right',fontsize=8.5);ax.set_xlim(0,max(a+b)*1.1);label(ax,'a  Mapping coverage · source counts')
ax=axes[0,1];v=[r[3] for r in rows];ax.barh(x,v,color=TEAL);ax.set_yticks(x,[r[0] for r in rows]);ax.set_xlim(0,105);ax.set_xlabel('Current bodies from mapped source IDs (%)')
for i,value in enumerate(v):ax.text(value+1,i,f'{value:.1f}%',va='center')
label(ax,'b  Mapping coverage · retained source mass')
end(fig,name,f'Source-ID proxies: newspaper {metrics["newspaper"]["after_contributing_source_ids"]}; social {metrics["social"]["after_contributing_source_ids"]}. These are separate from publisher/platform/community parent counts.\nMappings cannot be added across dimensions. Unknown/unreviewed mass stays visible; no independent-parent total or historical-validity claim is fabricated.')

name='07_capacity_and_stop_evidence'
fig,axes=start(name,'The streams ended at different operational boundaries',
 'Newspaper: fixed-deadline watchdog. Social: complete-operation capacity failure across remaining permitted routes.',(1,2),(16,9))
fig.subplots_adjust(left=.19,right=.97,wspace=.65)
ax=axes[0,0];nc=ns['final_resource_capacity'];soccap=caps['export_start_capacity']
labels=['Shared guard headroom\n(newspaper terminal)','Physical guard headroom\n(newspaper terminal)','Social guard headroom\n(social export-start)','Social nominal remainder\n(after publication copy)']
vals=[nc['allocation_headroom']/1e6,nc['physical_headroom']/1e6,soccap['social_headroom']/1e6,publication_accounting['social_nominal_remaining_after_publication_bytes']/1e6]
assert all(v>0 for v in vals), 'Log headroom axis requires positive recorded values'
ax.barh(range(4),vals,color=[BLUE,GRAY,ORANGE,TEAL]);ax.set_yticks(range(4),labels,fontsize=9);ax.set_xscale('log');ax.set_xlim(1,200000);ax.set_xlabel('Recorded headroom / nominal remainder (MB decimal)')
for i,v in enumerate(vals):ax.text(v*1.25,i,f'{v:,.1f}',va='center',fontsize=9)
label(ax,'a  Different guard snapshots; no counter reset')
ax=axes[0,1];g=pd.DataFrame([{'source':k,**v} for k,v in peaks['source_classes'].items()]).sort_values('max_ratio_to_reserved')
ax.barh(range(len(g)),g.max_ratio_to_reserved*100,color=TEAL);ax.set_yticks(range(len(g)),[titles.get(s,s)[:35] for s in g.source],fontsize=8);ax.set_xlim(0,105);ax.axvline(100,color=GRAY,lw=.8,ls='--');ax.set_xlabel('Maximum observed / reserved operation peak (%)');label(ax,'b  Changed social Load peak checks')
end(fig,name,f'Guard timestamps differ: newspaper {ns["at_utc"][:19]} UTC; social {soccap["at_utc"][:19]} UTC. Frozen stop evidence is unchanged.\nCorrected social publication copies: 9.455 MB; nominal remainder 147.515 → 138.060 MB. Unchanged minimum reservation 117.506 MB leaves 20.554 MB before payload/rows/controls.\nSmallest-post Load is conditional on live complete-operation checks; sustained four-hour yield is unknown. Changed peak checks cover {peaks["remaining_changed_loads_checked"]:,} Loads with zero exceedances.')

dump('FIGURE_CONTRACT.json',figure_contract)
dump('SOURCE_DATA_MAP.json',{'01':['monthly_before_after.csv','monthly_depth_bins.csv'],
 '02':['monthly_before_after.csv','annual_before_after.csv'],
 '03':['matched_Jan_Aug_2016_2026.csv','matched_baseline_contributing_source_panel.csv'],
 '04':['source_before_after_and_era.csv','new_contributing_source_genre_era.csv','newspaper_new_structural_genre_by_year.csv','social_new_source_genre_by_year.csv'],
 '05':['legacy_month_recovery.csv'],
 '06':['parent_dimension_mappings.csv','parent_mapping_coverage.csv','current_newspaper_parent_assertions.csv'],
 '07':['METRICS.json','COORDINATOR_PUBLICATION_ACCOUNTING_NOTE.json','INPUT_MANIFEST.json']})
dump('INPUT_MANIFEST.json',{'inputs':inputs,'all_input_hashes_unchanged':all(hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in inputs)})
print(json.dumps(metrics,indent=2))
