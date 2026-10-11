"""Render terminal local PNG review only from accepted analysis outputs; no source/store access."""
from pathlib import Path
import argparse,json,hashlib,sys,io,subprocess
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import ticker

BASE=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/jarlgiovanni/.codex/skills/nature-figure/scripts')
from audit_panel_alignment import require_matplotlib_panel_alignment
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','Helvetica','DejaVu Sans'],
 'font.size':10,'axes.titlesize':12,'axes.labelsize':10,'axes.spines.top':False,'axes.spines.right':False,
 'pdf.fonttype':42,'svg.fonttype':'none','figure.facecolor':'white','savefig.facecolor':'white','legend.frameon':False})
BLUE='#306899';TEAL='#198A85';GRAY='#A4AFB7';ORANGE='#BB7936';DARK='#243747'
NBASE='frozen_legacy_baseline_v1';NFINAL='final_comparable_legacy_v1';NFAMILY='final_newspaper_family_v2';SBASE='frozen_social_baseline';SFINAL='final_social_A_B_merged'
names={NBASE:'Frozen legacy baseline',NFINAL:'Comparable legacy final',NFAMILY:'Versioned family final',SBASE:'Social baseline',SFINAL:'Social final A+B'}
colors={NBASE:GRAY,NFINAL:BLUE,NFAMILY:ORANGE,SBASE:GRAY,SFINAL:TEAL}

def build(m,data,qa_python='python3'):
 if not m['terminal_acceptance'].get('metadata_frozen'):raise ValueError('Terminal acceptance missing')
 tables=lambda name:data[name]
 month=tables('monthly_frames.csv');annual=tables('annual_frames.csv');matched=tables('matched_Jan_Aug_2016_2026.csv');summary=tables('frame_summary.csv');sources=tables('source_contributions_genre_era.csv')
 payload={};contracts=[];checks=[]
 def start(name,title,sub,shape=(1,2),size=(16,9)):
  fig,ax=plt.subplots(*shape,figsize=size,squeeze=False);fig.subplots_adjust(left=.10,right=.97,top=.80,bottom=.17,wspace=.40,hspace=.55)
  fig.text(.055,.965,title,fontsize=20,color=DARK,va='top');fig.text(.055,.91,sub,fontsize=10,color='#536674',va='top')
  contracts.append({'figure':name,'claim_or_question':title,'archetype':'quantitative grid','backend':'Python/matplotlib','size_inches':size,'uncertainty':'none: exact frozen metadata, no population estimates'})
  return fig,ax
 def save(fig,name,footer):
  fig.text(.055,.065,footer,fontsize=9,color='#536674',va='top',linespacing=1.5);fig.canvas.draw()
  alignment=require_matplotlib_panel_alignment(fig,strict=True)
  png=io.BytesIO();fig.savefig(png,format='png',dpi=300)
  pdf=io.BytesIO();fig.savefig(pdf,format='pdf');plt.close(fig)
  qa=subprocess.run([qa_python,str(BASE/'qa_memory.py')],input=pdf.getvalue(),capture_output=True)
  result=json.loads(qa.stdout.decode()) if qa.stdout else {'error':qa.stderr.decode()}
  if qa.returncode:raise ValueError(f'Rendered QA failed for {name}: {json.dumps(result)}')
  payload['figures/'+name+'.png']=png.getvalue()
  payload['qa/'+name+'.alignment.json']=(json.dumps(alignment,indent=2)+'\n').encode()
  payload['qa/'+name+'.rendered.json']=(json.dumps(result,indent=2)+'\n').encode()
  checks.append({'figure':name,'automated_pass':True,'manual_visual_inspection_required':True})
 def title(ax,text):ax.set_title(text,loc='left',pad=15)
 def missing(ax,text):ax.set_axis_off();ax.text(.05,.6,text,transform=ax.transAxes,wrap=True,fontsize=12,color=DARK)

 name='01_frame_coverage_and_depth';fig,ax=start(name,'Keep the comparable newspaper frame and the family amendment separate',
  'Month presence describes retained text. The frozen 461-month view is preserved; family-only recovery is independently shown.')
 depth=['zero','one','exactly_two','three_to_nine','ten_to_49','fifty_plus'];labels=['0','1','2','3–9','10–49','50+']
 for panel,frames,letter in [(ax[0,0],[NBASE,NFINAL,NFAMILY],'a'),(ax[0,1],[SBASE,SFINAL],'b')]:
  for j,f in enumerate(frames):
   row=summary.set_index('frame').loc[f];vals=[row[x] for x in depth];w=.75/len(frames);bars=panel.bar(np.arange(6)+(j-(len(frames)-1)/2)*w,vals,width=w*.95,color=colors[f],label=names[f]);panel.bar_label(bars,padding=3,fontsize=8)
  panel.set_xticks(range(6),labels);panel.set_ylabel('Study months / 465');panel.set_xlabel('Retained units per month');panel.set_ylim(0,465);panel.legend(fontsize=8.5);title(panel,f'{letter}  {"Newspaper views" if letter=="a" else "Social independently dated bodies"}')
 save(fig,name,'Verified Supplement family texts must not be described as unrecovered. Family presence in 465 months is not full-archive completion.\nSocial full-calendar absence combines source-era applicability, unknown inventories and access limits. September 2026 is partial.')

 name='02_time_distribution';fig,ax=start(name,'Retained publication-time distributions, with all bins and valid peaks',
  'Monthly and annual aggregates; no climate-event attribution, semantic exclusion, smoothing or forced histogram.',(2,2),(16,11))
 for col,frames in [(0,[NBASE,NFINAL,NFAMILY]),(1,[SBASE,SFINAL])]:
  for f in frames:
   g=month[month.frame==f];ax[0,col].plot(range(465),g.units,color=colors[f],lw=1.1,label=names[f]);a=annual[annual.frame==f];ax[1,col].plot(a.year,a.units,color=colors[f],lw=1.3,label=names[f])
  for r in [0,1]:ax[r,col].set_yscale('symlog',linthresh=1);ax[r,col].set_ylabel('Retained units (symlog)')
  ax[0,col].set_xticks([0,84,204,324,456],['1988','1995','2005','2015','2026']);ax[0,col].legend(fontsize=8)
  title(ax[0,col],f'{"a" if col==0 else "b"}  {"Newspaper" if col==0 else "Social"} · monthly');title(ax[1,col],f'{"c" if col==0 else "d"}  Annual aggregates');ax[1,col].set_xlabel('Publication year')
 save(fig,name,'Symlog keeps zero and a ±1 linear interval. Original publication, archive capture, retrieval, content-version and report times remain separate.\nThe orange family view has an amended source frame; its differences cannot all be interpreted as within-frame production growth.')

 name='03_matched_recent_years';fig,ax=start(name,'Compare recent years using the same January–August observation window',
  'Comparable matched-month views stay separate from full-history 2026 shares.',(1,3),(19,9))
 g=matched[matched.stream=='social'];fixed=tables('social_matched_baseline_source_frame.csv')
 for f in [NBASE,NFINAL,NFAMILY]:
  r=matched[matched.frame==f];ax[0,0].plot(r.year,r.units,marker='o',color=colors[f],label=names[f])
 for f in [SBASE,SFINAL]:
  r=g[g.frame==f];ax[0,1].plot(r.year,r.units,marker='o',color=colors[f],label=names[f])
 for col,c in [('before',GRAY),('after',TEAL)]:ax[0,2].plot(fixed.year,fixed[col],marker='o',color=c,label=col.capitalize())
 for panel in ax[0]:panel.set_ylabel('January–August retained units');panel.set_xlabel('Publication year');panel.legend(fontsize=9);panel.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
 title(ax[0,0],'a  Newspaper views');title(ax[0,1],'b  Social all-source frames');title(ax[0,2],'c  Social baseline source-ID frame')
 save(fig,name,'2016–2026 are matched by months. Holding source IDs fixed does not hold archive recovery, author mixture or access constant.\nNeither a lower full-history share nor this comparison certifies balanced public coverage or discourse prevalence.')

 name='04_source_genre_era';fig,ax=start(name,'Show actual source contributions and their structural genre/era',
  'Every positive delta is retained; classification remains structural. Missing classifications stay unresolved.',(1,2),(20,max(12,.38*int(sources[sources.delta>0].groupby('stream').size().max())+4) if (sources.delta>0).any() else 12));fig.subplots_adjust(left=.24,right=.97,wspace=.80,bottom=.15)
 for panel,stream,c,letter in [(ax[0,0],'newspaper',BLUE,'a'),(ax[0,1],'social',TEAL,'b')]:
  g=sources[(sources.stream==stream)&(sources.delta>0)].sort_values('delta')
  if g.empty:missing(panel,'No positive source increment in the accepted view');continue
  display_genres={'newspaper_title':'Newspaper editorial articles','discussion_forum':'Public discussion forum',
   'qa_community':'Question-and-answer community','technical_list':'Technical mailing list','civic_list':'Civic mailing list',
   'platform_instance':'Public platform instance','unresolved':'Unresolved structural genre'}
  labels=[f'{r.source_id}\n{display_genres.get(r.source_unit_class,"Unresolved structural genre")} · {str(r.first_new_month)[:4]}–{str(r.last_new_month)[:4]}' for r in g.itertuples()]
  panel.barh(range(len(g)),g.delta,color=[ORANGE if v else c for v in g.new_contributing_source]);panel.set_yticks(range(len(g)),labels,fontsize=8);panel.set_xlabel('New retained units');title(panel,f'{letter}  {stream.capitalize()} source IDs')
 display={'newspaper_title':'Titles','discussion_forum':'Strict forums','qa_community':'Q&A','technical_list':'Technical lists','civic_list':'Civic lists','campus_publication':'Campus publications','platform_instance':'Platform instances'}
 unit_text='; '.join(f"{display.get(r['source_unit_class'],r['source_unit_class'])}: {r['contributing_named_units']}" for r in m['named_unit_counts']) or 'Named-unit classifications unavailable'
 save(fig,name,'Orange marks first contribution under the comparable frame. Family-only accepted IDs: '+str(m['family_only_IDs'])+' (separate frame).\n'+unit_text+'. Detailed source-purpose descriptions remain in the accompanying table; independent-parent totals are unresolved.')

 name='05_legacy_inventory_and_evidence';fig,ax=start(name,'Distinguish executable inventory from repair and recovery evidence',
  'Code-fixed, data-recovered and externally blocked are different facts; no inventory exhaustion is inferred from a count plateau.')
 if 'legacy_inventory.csv' in data:
  g=tables('legacy_inventory.csv').sort_values('month');x=np.arange(len(g));ax[0,0].plot(x,g.unattempted_ready,color=BLUE,label='Unattempted ready');ax[0,0].plot(x,g.pending,color=ORANGE,label='Pending');ax[0,0].set_xticks(x[::max(1,len(g)//8)],g.month.iloc[::max(1,len(g)//8)],rotation=45,rotation_mode='anchor',ha='right');ax[0,0].set_ylabel('Named inventory state counts');ax[0,0].legend()
 else:missing(ax[0,0],'Remaining legacy inventory metadata unavailable; exhaustion is not established')
 if 'evidence_dispositions.csv' in data:
  g=tables('evidence_dispositions.csv').groupby('evidence_level').issue_id.nunique();ax[0,1].barh(range(len(g)),g.values,color=TEAL);ax[0,1].set_yticks(range(len(g)),g.index);ax[0,1].set_xlabel('Named issues with that evidence disposition')
 else:missing(ax[0,1],'Issue-level evidence dispositions unavailable; fixture and Load evidence remain separate')
 title(ax[0,0],'a  Remaining named inventory');title(ax[0,1],'b  Evidence-level dispositions')
 save(fig,name,'Pending, ready and committed counts need not sum to an exhaustive inventory. Their native units and evidence references are explicit in source tables.\nA provider prohibition, date conflict or unknown article boundary is preserved; no mass reset, deletion or invented monthly target is introduced.')

 name='06_parent_mapping_unknowns';fig,ax=start(name,'Keep publisher, platform and community mapping limits separate',
  'Current snapshot assertions do not verify historical ownership; source IDs are an auxiliary proxy, not independent parents.');fig.subplots_adjust(left=.20,right=.97,wspace=.60)
 if 'parent_dimension_coverage.csv' in data:
  p=tables('parent_dimension_coverage.csv');rows=[]
  for (stream,dim),g in p.groupby(['stream','relation_dimension']):
   mapped=g.evidence_status.isin(['confirmed','supported_current_primary_assertion','supported_current']);total=g.after.sum();rows.append((stream+' '+dim.replace('_',' '),int(mapped.sum()),len(g),float(g.loc[mapped,'after'].sum()/total*100) if total else 0))
  labels=[r[0] for r in rows];x=np.arange(len(rows));ax[0,0].barh(x,[r[1] for r in rows],color=TEAL);ax[0,0].barh(x,[r[2]-r[1] for r in rows],left=[r[1] for r in rows],color=GRAY);ax[0,0].set_yticks(x,labels,fontsize=8);ax[0,0].set_xlabel('Mapped assertion / unknown source IDs');ax[0,1].barh(x,[r[3] for r in rows],color=TEAL);ax[0,1].set_yticks(x,labels,fontsize=8);ax[0,1].set_xlim(0,100);ax[0,1].set_xlabel('Retained mass from mapped source IDs (%)')
 else:
  for panel in ax[0]:missing(panel,'Parent assertions unavailable; no parent total is fabricated')
 title(ax[0,0],'a  Dimension mapping coverage');title(ax[0,1],'b  Dimension mapping mass')
 save(fig,name,'Unmapped source mass remains visible. Different parent dimensions cannot be added; supported assertions retain their evidence and valid-time limits.\nTechnical archives, editorial/campus texts and undifferentiated platform instances do not inflate strict public discussion-forum totals.')

 name='07_capacity_and_stops';fig,ax=start(name,'Report timestamped operational capacity and genuine stop boundaries',
  'All delivery/publication/code charges count once; nominal budget and protected physical headroom remain separate.');fig.subplots_adjust(left=.20,right=.97,wspace=.60)
 if 'capacity_observations.csv' in data:
  g=tables('capacity_observations.csv').sort_values('at_utc');labels=[f'{r.stream}:{r.phase_id} {r.observation_kind}' for r in g.itertuples()];ax[0,0].barh(range(len(g)),g.nominal_allocation_headroom_bytes/1e6,color=TEAL);ax[0,0].set_yticks(range(len(g)),labels,fontsize=8);ax[0,0].set_xlabel('Recorded nominal headroom (MB decimal)');ax[0,0].set_xlim(left=0)
  text='\n\n'.join(f'{r.stream}:{r.phase_id} · {r.at_utc}\n'+textwrap.fill(str(r.stop_reason),55) for r in g.itertuples());missing(ax[0,1],text)
 else:
  for panel in ax[0]:missing(panel,'Final capacity/stop metadata unavailable; no sustained yield or exhaustion claim')
 title(ax[0,0],'a  Allocation snapshots');title(ax[0,1],'b  Source-stop evidence')
 save(fig,name,'15 GB social remains inside 30 GB shared; original counters, 15 GiB physical floor, 48 MiB recovery and 36 consumed PDF slots remain.\nA small operation can fit only after a live complete-operation check. No rolling extension or forecasted four-hour yield is inferred.')
 payload['FIGURE_CONTRACT.json']=(json.dumps(contracts,indent=2)+'\n').encode()
 payload['qa/QA_SUMMARY.json']=(json.dumps({'all_automated_checks_pass':True,'rendered_checks':checks,'manual_visual_inspection_required':True,'QA_PDF_bytes_held_in_memory_only':True},indent=2)+'\n').encode()
 return payload

def main():
 p=argparse.ArgumentParser(description=__doc__+' Run finalize_report.py to render the complete bounded bundle once.');p.parse_args();p.error('Use finalize_report.py; partial or unbounded figure output is disabled')
if __name__=='__main__':main()
