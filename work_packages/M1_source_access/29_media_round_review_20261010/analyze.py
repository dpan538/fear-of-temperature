"""Closed metadata review; never opens corpus databases, bodies, or raw responses."""
from pathlib import Path
import json, hashlib
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PKG = ROOT / 'work_packages/M1_source_access/27_newspaper_context_recovery_20261008'
NP = PKG / 'continuations/20261009_nine_hour_newspaper/worker'
SM = PKG / 'social_public_api/continuations/20261009_nine_hour_social/worker'
BASE = ROOT / 'work_packages/M1_source_access/28_media_identity_coverage_and_lakehouse_20261009/results_v4'
months = pd.period_range('1988-01', '2026-09', freq='M').astype(str)
inputs = {}
def read(path, **kwargs):
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return pd.read_csv(path, keep_default_na=False, **kwargs)
def js(path):
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())
def save(frame, name):
    frame.to_csv(OUT/'tables'/name, index=False)
def integer(v): return int(v)

ns = js(NP/'DELIVERY_SUMMARY.json'); ss = js(SM/'summaries/collection_manifest.json')
n = read(NP/'CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv', usecols=['article_id','source_id','source','publication_date','stratum','work_family_id','body_sha256','whole_TEXT_characters'])
assert len(n)==16138 and n.article_id.nunique()==len(n)
n['month'] = n.publication_date.str[:7]
assert n.month.isin(months).all()
s = read(SM/'summaries/source_month_calendar.csv')
old = read(BASE/'source_month_metrics.csv')
old['source_id'] = old.source_id.str.split(':',n=1).str[-1]
oldp = read(BASE/'pooled_month_metrics.csv')
registry = js(SM/'source_registry.json')
labels = dict(zip(n.source_id,n.source)); labels.update({x['source_id']:x['title'] for x in registry})
npmap = read(NP/'SOURCE_PARENT_IDENTITY_REGISTER.csv')
n = n.merge(npmap[['source_id','acquisition_parent_family_id']], on='source_id', validate='many_to_one')
npmonthly = n.groupby('month').agg(bodies=('article_id','size'),works=('work_family_id','nunique'),sources=('source_id','nunique'),parents=('acquisition_parent_family_id','nunique')).reindex(months,fill_value=0)
smmonthly = s.groupby('month').usable_dated_independent_bodies.sum().reindex(months,fill_value=0)
assert smmonthly.sum()==ss['publication_month_qualified_independent_body_entities']==239392
pool=[]
for stream, vals in [('newspaper',npmonthly.bodies),('social',smmonthly)]:
    before=oldp[oldp.stream==stream].set_index('month').readable_body_entities.reindex(months,fill_value=0)
    for month in months: pool.append({'stream':stream,'month':month,'before':int(before[month]),'after':int(vals[month]),'added':int(vals[month]-before[month])})
pool=pd.DataFrame(pool); assert (pool.added>=0).all();save(pool,'monthly_before_after.csv')
source_month=[]
ng=n.groupby(['source_id','month']).size()
for stream,data in [('newspaper',ng),('social',s.groupby(['source_id','month']).usable_dated_independent_bodies.sum())]:
    for (source,month),count in data.items():
        source_month.append({'stream':stream,'source_id':source,'month':month,'bodies':int(count)})
source_month=pd.DataFrame(source_month);save(source_month,'source_month.csv')
sources=[]
for (stream,source),g in source_month.groupby(['stream','source_id']):
    total=int(g.bodies.sum())
    if total==0:continue
    bef=old[(old.stream==stream)&(old.source_id==source)]
    active=g[g.bodies>0]
    row={'stream':stream,'source_id':source,'label':labels.get(source,source),'before_bodies':int(bef.readable_body_entities.sum()),'after_bodies':total,'added_bodies':total-int(bef.readable_body_entities.sum()),'before_months':int((bef.readable_body_entities>0).sum()),'after_months':len(active),'first_observed_month':active.month.min(),'last_observed_month':active.month.max(),'share':total/(16138 if stream=='newspaper' else 239392)}
    if stream=='social':
        states=s[s.source_id==source].groupby('state').size().to_dict()
        row.update({'era_states':json.dumps(states),'platform_software_label':next(x['platform'] for x in registry if x['source_id']==source)})
    sources.append(row)
sources=pd.DataFrame(sources);save(sources,'source_comparison.csv')
parents=[]
for parent,g in n.groupby('acquisition_parent_family_id'):
    children=g.source_id.unique().tolist(); before=int(old[(old.stream=='newspaper')&old.source_id.isin(children)].readable_body_entities.sum())
    parents.append({'stream':'newspaper','dimension':'acquisition_family','parent':parent,'before':before,'after':len(g),'sources':len(children),'share':len(g)/len(n),'status':'recorded snapshot; not verified historical ownership'})
mapping=js(BASE/'parent_source_statistics.json')['mapping_assertions']
for dimension in ['platform_network','software_family','instance','community','publisher_organization']:
    assertions=[x for x in mapping if x['source_id'].startswith('social:') and x['dimension']==dimension and x['status'] in ('recorded','confirmed')]
    assigned=set()
    for parent in sorted({x['parent_id'] for x in assertions}):
        children={x['source_id'].split(':',1)[1] for x in assertions if x['parent_id']==parent}
        g=sources[(sources.stream=='social')&sources.source_id.isin(children)]
        if not len(g):continue
        assigned|=set(g.source_id)
        parents.append({'stream':'social','dimension':dimension,'parent':parent.split(':',1)[-1],'before':int(g.before_bodies.sum()),'after':int(g.after_bodies.sum()),'sources':len(g),'share':g.after_bodies.sum()/239392,'status':'recorded snapshot; dimensions not additive'})
    g=sources[(sources.stream=='social')&~sources.source_id.isin(assigned)]
    parents.append({'stream':'social','dimension':dimension,'parent':'Unmapped / applicability unresolved','before':int(g.before_bodies.sum()),'after':int(g.after_bodies.sum()),'sources':len(g),'share':g.after_bodies.sum()/239392,'status':'unmapped does not imply a failed source'})
parents=pd.DataFrame(parents);save(parents,'parent_comparison.csv')

def longest_zero(series):
    spans=[]; start=None
    for i,v in enumerate(series):
        if not v and start is None:start=i
        if start is not None and (v or i==len(series)-1):
            end=i-1 if v else i; spans.append({'start':months[start],'end':months[end],'months':end-start+1});start=None
    return sorted(spans,key=lambda x:-x['months'])

region=[]
for name in ['EU/Europe excluding UK','UK','AU','US','NZ']:
    g=n[n.stratum==name].groupby('month').size().reindex(months,fill_value=0)
    region.append({'region':name,'articles':int(g.sum()),'observed_months':int((g>0).sum()),'zero_months':int((g==0).sum()),'one_months':int((g==1).sum())})
save(pd.DataFrame(region),'newspaper_region.csv')
era=s.groupby(['source_id','state']).size().rename('months').reset_index();save(era,'social_era_states.csv')

# Peaks retain all records. Recompute the same transparent context rule for the pooled view.
peaks=[]
for stream in ['newspaper','social']:
    series=pool[pool.stream==stream].set_index('month').after
    for i,(month,v) in enumerate(series.items()):
        nei=[series.iloc[j] for j in range(max(0,i-3),min(len(series),i+4)) if j!=i]
        avg=float(np.mean(nei));ratio=float(v/avg) if avg else None
        if v>0 and (avg==0 or v>3*avg):
            mix=source_month[(source_month.stream==stream)&(source_month.month==month)].sort_values('bodies',ascending=False)
            peaks.append({'stream':stream,'month':month,'bodies':int(v),'neighbor_mean':avg,'ratio':ratio,'boundary_incomplete':len(nei)<6,'largest_source':mix.iloc[0].source_id,'largest_source_share':float(mix.iloc[0].bodies/v),'action':'flag only; retain; event cause unassessed'})
save(pd.DataFrame(peaks),'pooled_peak_flags.csv')
new_2026=source_month[source_month.month.str.startswith('2026')].copy();save(new_2026,'composition_2026.csv')
overlap=read(NP/'EXACT_BODY_OVERLAP_REVIEW_REGISTER.csv')
roles=read(SM/'summaries/role_summary.csv'); states=read(SM/'summaries/content_states.csv'); types=read(SM/'summaries/source_native_type_counts.csv')
for df,name in [(roles,'social_roles.csv'),(states,'social_content_states.csv'),(types,'social_native_types.csv')]:save(df,name)
relations=read(SM/'summaries/changed_relations_manifest.csv.gz',usecols=['relation_type','resolution_state'])
save(relations.groupby(['relation_type','resolution_state']).size().rename('edges').reset_index(),'changed_relation_resolution.csv')
membership=read(SM/'summaries/publication_memberships.csv.gz',usecols=['entity_id','publication_key'])
mem=membership.groupby('publication_key').entity_id.nunique(); multi=mem[mem>1]
metrics={'newspaper':{'before':9538,'after':16138,'added':6600,'observed_months_before':380,'observed_months_after':int((npmonthly.bodies>0).sum()),'zero_months':int((npmonthly.bodies==0).sum()),'exactly_two_bodies_before':int(((pool.stream=='newspaper')&(pool.before==2)).sum()),'exactly_two_bodies_after':int((npmonthly.bodies==2).sum()),'single_source_months':int((npmonthly.sources==1).sum()),'known_work_exactly_two_after':int((npmonthly.works==2).sum()),'longest_gaps':longest_zero(npmonthly.bodies),'sources':int(n.source_id.nunique()),'parents':int(n.acquisition_parent_family_id.nunique()),'work_keys':int(n.work_family_id.nunique()),'exact_body_candidate_groups':int(overlap.body_sha256.nunique()),'exact_body_candidate_ids':int(overlap.article_id.nunique()),'pending_records':76},'social':{'before':42488,'after':239402,'added':196914,'dated_before':42478,'dated_after':239392,'observed_months_before':165,'observed_months_after':201,'sources':int(sum(sources.stream=='social')),'new_native_entities':216717,'native_entities':268343,'native_versions':275580,'edges':505508,'attachment_metadata':91409,'pending_dates':9,'publication_key_groups_multi_entity':int(len(multi)),'native_entities_in_multi_entity_keys':int(multi.sum()),'roles':roles.groupby('author_role').core_texts.sum().to_dict()},'resources':{'shared_snapshot_bytes':ns['resource_at_delivery']['cumulative_bytes'],'shared_cap':30000000000,'social_terminal_start_bytes':ss['actual_capacity_at_terminal_start']['social_bytes'],'social_cap':8000000000,'free_at_newspaper_delivery_bytes':ns['resource_at_delivery']['free_bytes']},'source_mix':{},'peak_flags':peaks,'scope':'1988-01-01 through2026-09-21; September partial; counts are not archive recovery or public representativeness','inventory_denominators':'unknown: observed cursor endpoints are not complete historical archive denominators'}
for stream in ['newspaper','social']:
    g=sources[sources.stream==stream].sort_values('after_bodies',ascending=False)
    dated=source_month[source_month.stream==stream]
    tot=int(g.after_bodies.sum()); yr26=int(dated[dated.month.str.startswith('2026')].bodies.sum()); sept=int(dated[dated.month=='2026-09'].bodies.sum())
    before26=int(pool[(pool.stream==stream)&pool.month.str.startswith('2026')].before.sum());beforetotal=int(pool[pool.stream==stream].before.sum())
    metrics['source_mix'][stream]={'top_source':g.iloc[0].source_id,'top_share':float(g.iloc[0]['share']),'top2_share':float(g.head(2)['share'].sum()),'year2026':yr26,'year2026_share':yr26/tot,'year2026_share_before':before26/beforetotal,'september2026':sept,'september2026_share':sept/tot}
save(npmonthly.reset_index(names='month'),'newspaper_month_details.csv')
(OUT/'analysis.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False)+'\n')
(OUT/'input_manifest.json').write_text(json.dumps(inputs,indent=2)+'\n')
print(json.dumps(metrics,ensure_ascii=False,indent=2))
