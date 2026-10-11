"""Prepare exact metadata aggregates after terminal acceptance; never open a store or body."""
from pathlib import Path
import argparse, csv, gzip, hashlib, json
import pandas as pd

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
MONTHS=pd.period_range('1988-01','2026-09',freq='M').astype(str)
DEADLINE='2026-10-11T01:44:10.127246+00:00'
DENIED_COLUMNS={'body','text','content','html','raw_json','payload','body_text','raw_body'}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def truth(value):return str(value).lower() in {'true','1'}

class Inputs:
    def __init__(self):self.receipts=[]
    def path(self,ref):
        if not ref or not ref.get('path') or not ref.get('sha256'):raise ValueError('A finalized path and SHA256 are required')
        p=Path(ref['path']);p=p if p.is_absolute() else ROOT/p;p=p.resolve()
        if 'raw' in p.parts or p.suffix in {'.db','.sqlite','.sqlite3','.bin'}:raise ValueError(f'Excluded store/raw input: {p.name}')
        if p.name.endswith(('.csv','.csv.gz')):
            opener=gzip.open if p.name.endswith('.gz') else open
            with opener(p,'rt',newline='') as f:fields=next(csv.reader(f))
            if DENIED_COLUMNS.intersection(str(c).lower() for c in fields):raise ValueError('Body-bearing input rejected before hashing/row reads')
        got=sha(p)
        if got!=ref['sha256']:raise ValueError(f'Hash mismatch: {p.name}')
        self.receipts.append({'path':str(p),'sha256':got,'bytes':p.stat().st_size})
        return p
    def table(self,ref,required):
        p=self.path(ref)
        opener=gzip.open if p.name.endswith('.gz') else open
        with opener(p,'rt',newline='') as f:fields=next(csv.reader(f))
        if DENIED_COLUMNS.intersection(str(c).lower() for c in fields):raise ValueError('Body-bearing export rejected before row reads')
        frame=pd.read_csv(p)
        if ref.get('column_map'):frame=frame.rename(columns=ref['column_map'])
        missing=set(required)-set(frame.columns)
        if missing:raise ValueError(f'{p.name}: missing fields {sorted(missing)}')
        return frame
    def obj(self,ref):return json.loads(self.path(ref).read_text())
    def unchanged(self):return all(sha(Path(x['path']))==x['sha256'] for x in self.receipts)

def register(loader,ref):
    f=loader.table(ref,['article_id','source_id','source_url','publication_date'])
    if f[['article_id','source_id','source_url','publication_date']].isna().any().any() or f.article_id.duplicated().any():raise ValueError('Register requires unique stable IDs and source/date/URL mappings')
    f['publication_date']=f.publication_date.astype(str).str[:10]
    pd.to_datetime(f.publication_date,errors='raise')
    if not f.publication_date.between('1988-01-01','2026-09-21').all():raise ValueError('Publication interval changed')
    f['month']=f.publication_date.str[:7]
    return f
def source_month(f,count='units'):
    return f.groupby(['source_id','month']).size().rename(count).reset_index()
def calendar(loader,ref):
    f=loader.table(ref,['source_id','month','usable_dated_independent_bodies'])
    if f[['source_id','month']].isna().any().any() or f.duplicated(['source_id','month']).any():raise ValueError('Missing/duplicate source-month cells')
    f=f.rename(columns={'usable_dated_independent_bodies':'units'})
    valid_counts(f,'units')
    if not f.month.isin(MONTHS).all():raise ValueError('Out-of-interval calendar cells')
    return f
def valid_counts(f,col):
    f[col]=pd.to_numeric(f[col],errors='raise')
    if f[col].isna().any() or (f[col]<0).any() or (f[col]%1!=0).any():raise ValueError(f'Invalid counts in {col}')
    f[col]=f[col].astype('int64')
def comparable(old,new):
    if not set(old.article_id).issubset(set(new.article_id)):raise ValueError('Baseline stable IDs disappeared')
    a=old.set_index('article_id');b=new.set_index('article_id').loc[a.index]
    for col in ['source_id','publication_date']:
        if not a[col].equals(b[col]):raise ValueError(f'Baseline identity/date field changed: {col}')
def delta_cells(before,after):
    b=before.set_index(['source_id','month']).units;a=after.set_index(['source_id','month']).units
    x=pd.concat([b.rename('before'),a.rename('after')],axis=1).fillna(0).astype(int).reset_index()
    x['delta']=x.after-x.before
    if (x.delta<0).any():raise ValueError('Snapshot decrease requires separate evidenced reconciliation, not silent exclusion')
    return x

def social_merge(loader,phases,before,after,baseline_hash,final_hash):
    if not phases:raise ValueError('Explicit immutable social A/B phases required, even for zero growth')
    mode={bool(p.get('keys')) for p in phases}
    if len(mode)!=1:raise ValueError('Use identity keys for every phase, or accepted append proofs for every phase')
    frames=[];key_frames=[];proofs=[];seen_phase=set();previous=baseline_hash
    for phase in phases:
        phase_id=phase['phase_id']
        if phase_id in seen_phase:raise ValueError('Repeated phase ID')
        seen_phase.add(phase_id)
        f=loader.table(phase['delta'],['source_id','month','new_usable_dated_bodies'])
        if f[['source_id','month']].isna().any().any():raise ValueError('Phase delta requires explicit source/month')
        valid_counts(f,'new_usable_dated_bodies')
        if not f.month.isin(MONTHS).all():raise ValueError('Out-of-interval phase delta')
        f=f.groupby(['source_id','month'],as_index=False).new_usable_dated_bodies.sum();f['phase_id']=phase_id;frames.append(f)
        if phase.get('keys'):
            k=loader.table(phase['keys'],['unit_key','source_id','month'])
            if k[['unit_key','source_id','month']].isna().any().any():raise ValueError('Missing social stable independent-body key/source/month')
            if k.groupby('unit_key')[['source_id','month']].nunique().max().max()>1:raise ValueError('Conflicting repeated key inside phase')
            k=k.drop_duplicates('unit_key');check=source_month(k).set_index(['source_id','month']).units
            expected=f.set_index(['source_id','month']).new_usable_dated_bodies
            if not check.reindex(expected.index,fill_value=0).equals(expected) or int(check.sum())!=int(expected.sum()):raise ValueError('Phase key counts do not equal independent-body delta')
            k['phase_id']=phase_id;key_frames.append(k)
        else:
            proof=loader.obj(phase['append_proof'])
            needed=['accepted','count_unit','independent_body_identity_reconciliation_accepted','store_id','baseline_snapshot_sha256','after_snapshot_sha256','disjoint_append_ranges','evidence_refs']
            if any(k not in proof for k in needed):raise ValueError('Incomplete append proof')
            if proof['accepted'] is not True or proof['count_unit']!='new_usable_dated_independent_body':raise ValueError('Unaccepted/incorrect append unit')
            if proof['independent_body_identity_reconciliation_accepted'] is not True:raise ValueError('Version/entity ranges alone do not prove independent-body increments')
            if int(f.new_usable_dated_bodies.sum())>0 and not proof['disjoint_append_ranges']:raise ValueError('Nonzero phase lacks accepted append ranges')
            if proof['baseline_snapshot_sha256']!=previous:raise ValueError('A/B accepted snapshot chain is not contiguous')
            if not proof['evidence_refs']:raise ValueError('Append proof lacks named evidence')
            previous=proof['after_snapshot_sha256'];proofs.append(proof)
    phase_deltas=pd.concat(frames,ignore_index=True)
    duplicate_keys=0
    if key_frames:
        keys=pd.concat(key_frames,ignore_index=True)
        if keys.groupby('unit_key')[['source_id','month']].nunique().max().max()>1:raise ValueError('A/B stable key has conflicting source/date')
        duplicate_keys=len(keys)-keys.unit_key.nunique()
        merged=source_month(keys.drop_duplicates('unit_key'),'new_usable_dated_bodies')
    else:
        if len({p['store_id'] for p in proofs})!=1:raise ValueError('Append phases are not the same store')
        if previous!=final_hash:raise ValueError('Accepted append chain does not end at the final calendar SHA256')
        ranges=[]
        for p in proofs:
            for r in p['disjoint_append_ranges']:
                if r['start']>r['end']:raise ValueError('Invalid append range')
                for q in ranges:
                    if r['namespace']==q['namespace'] and max(r['start'],q['start'])<=min(r['end'],q['end']):raise ValueError('Overlapping A/B append ranges')
                ranges.append(r)
        merged=phase_deltas.groupby(['source_id','month'],as_index=False).new_usable_dated_bodies.sum()
    actual=delta_cells(before,after)
    wanted=actual.set_index(['source_id','month']).delta
    got=merged.set_index(['source_id','month']).new_usable_dated_bodies
    if not got.reindex(wanted.index,fill_value=0).equals(wanted) or int(got.sum())!=int(wanted.sum()):raise ValueError('Merged A/B differs from final-minus-baseline calendar')
    return actual,phase_deltas,{'deduplication_mode':'stable_body_keys' if key_frames else 'accepted_disjoint_append_proofs','overlapping_phase_keys_merged_once':int(duplicate_keys),'phase_ids':sorted(seen_phase),'merged_dated_increment':int(got.sum()),'phase_A_outputs_preserved':True}

def terminal_gate(config,loader):
    t=loader.obj(config['terminal_acceptance'])
    if t.get('metadata_frozen') is not True or t.get('changed_tranche_accepted') is not True:raise ValueError('Final metadata not frozen/accepted')
    if t.get('fixed_deadline_at_utc')!=DEADLINE:raise ValueError('Fixed four-hour deadline changed')
    for stream in ['newspaper','social']:
        v=t['writers'][stream]
        if v.get('writer_exited') is not True or v.get('mutex_free') is not True:raise ValueError('Writer handover not verified')
        if pd.Timestamp(v['source_requests_stopped_at_utc'])>pd.Timestamp(DEADLINE):raise ValueError('Source requests extended past cutoff')
        if not v.get('evidence_refs'):raise ValueError('Missing terminal writer evidence')
    return t

def run(config,loader,out=None,baseline_only=False,return_tables=False):
    old=register(loader,config['baseline_newspaper']);s_old=calendar(loader,config['baseline_social_calendar'])
    if len(old)!=27662 or old.month.nunique()!=461 or int(s_old.units.sum())!=987252:raise ValueError('Accepted eight-hour baseline does not reconcile')
    if baseline_only:
        if not loader.unchanged():raise ValueError('Frozen baseline changed during preparation check')
        return {'baseline_inputs_verified':True,'baseline_newspaper_IDs':len(old),'baseline_newspaper_observed_months':old.month.nunique(),'baseline_social_dated_bodies':int(s_old.units.sum()),'terminal_report_generated':False}
    t=terminal_gate(config,loader)
    current=register(loader,config['final_newspaper_legacy']);family=register(loader,config['final_newspaper_family']);comparable(old,current);comparable(current,family)
    extra=family[~family.article_id.isin(current.article_id)]
    for c in ['family_only_unit_reason','date_boundary_verified','evidence_ref']:
        if c not in family:raise ValueError(f'Family amendment lacks {c}')
    if not extra.date_boundary_verified.map(truth).all() or extra.family_only_unit_reason.isna().any() or extra.evidence_ref.isna().any():raise ValueError('Family-only date/boundary/membership evidence incomplete')
    s_final=calendar(loader,config['final_social_calendar'])
    s_delta,phase_delta,merge=social_merge(loader,config['social_phases'],s_old,s_final,config['baseline_social_calendar']['sha256'],config['final_social_calendar']['sha256'])
    tables={};monthly=[]
    for frame,r in [('frozen_legacy_baseline_v1',old),('final_comparable_legacy_v1',current),('final_newspaper_family_v2',family)]:
        x=pd.DataFrame({'month':MONTHS});x['stream']='newspaper';x['frame']=frame;x['units']=x.month.map(r.groupby('month').size()).fillna(0).astype(int);monthly.append(x)
    for frame,r in [('frozen_social_baseline',s_old),('final_social_A_B_merged',s_final)]:
        x=pd.DataFrame({'month':MONTHS});x['stream']='social';x['frame']=frame;x['units']=x.month.map(r.groupby('month').units.sum()).fillna(0).astype(int);monthly.append(x)
    pool=pd.concat(monthly,ignore_index=True);pool['year']=pool.month.str[:4].astype(int)
    tables['monthly_frames.csv']=pool
    tables['annual_frames.csv']=pool.groupby(['stream','frame','year'],as_index=False).units.sum()
    tables['matched_Jan_Aug_2016_2026.csv']=pool[(pool.year.between(2016,2026))&(pool.month.str[-2:].astype(int)<=8)].groupby(['stream','frame','year'],as_index=False).units.sum()
    tables['social_source_month_changed_cells.csv']=s_delta[s_delta.delta>0].copy();tables['social_phase_positive_deltas.csv']=phase_delta[phase_delta.new_usable_dated_bodies>0].copy()
    existing=set(s_delta.groupby('source_id').before.sum().loc[lambda s:s>0].index)
    fixed=s_delta[s_delta.source_id.isin(existing)].copy();fixed['year']=fixed.month.str[:4].astype(int)
    fixed=fixed[fixed.year.between(2016,2026)&(fixed.month.str[-2:].astype(int)<=8)]
    tables['social_matched_baseline_source_frame.csv']=fixed.groupby('year',as_index=False)[['before','after']].sum()
    tables['newspaper_family_only_membership.csv']=extra
    tables['newspaper_family_only_source_month.csv']=source_month(extra)
    summary=[]
    for (stream,frame),g in pool.groupby(['stream','frame']):
        summary.append({'stream':stream,'frame':frame,'units':int(g.units.sum()),'observed_months':int((g.units>0).sum()),'zero':int((g.units==0).sum()),'one':int((g.units==1).sum()),'exactly_two':int((g.units==2).sum()),'three_to_nine':int(g.units.between(3,9).sum()),'ten_to_49':int(g.units.between(10,49).sum()),'fifty_plus':int((g.units>=50).sum())})
    tables['frame_summary.csv']=pd.DataFrame(summary)
    src=[]
    for stream,b,a in [('newspaper',source_month(old),source_month(current)),('social',s_old,s_final)]:
        cells=delta_cells(b,a)
        for sid,g in cells.groupby('source_id'):
            present=g[g.after>0]
            if present.empty:continue
            src.append({'stream':stream,'source_id':sid,'before':int(g.before.sum()),'after':int(g.after.sum()),'delta':int(g.delta.sum()),'new_contributing_source':int(g.before.sum())==0,'first_observed_month':present.month.min(),'last_observed_month':present.month.max(),'first_new_month':g.loc[g.delta>0,'month'].min() if (g.delta>0).any() else None,'last_new_month':g.loc[g.delta>0,'month'].max() if (g.delta>0).any() else None})
    sources=pd.DataFrame(src)
    if config.get('source_units'):
        units=loader.table(config['source_units'],['stream','source_id','source_unit_class','source_unit_id','structural_genre','evidence_ref'])
        if units.duplicated(['stream','source_id']).any():raise ValueError('One source classification row per stream/source required')
        if units.loc[units.source_unit_id.notna(),['source_unit_class','evidence_ref']].isna().any().any():raise ValueError('A counted named unit requires classification and evidence')
        sources=sources.merge(units,on=['stream','source_id'],how='left',validate='one_to_one')
    else:
        sources['source_unit_class']='unresolved';sources['source_unit_id']=None;sources['structural_genre']='unresolved'
    tables['source_contributions_genre_era.csv']=sources
    unit_counts=sources[sources.source_unit_id.notna()].groupby(['stream','source_unit_class'],as_index=False).source_unit_id.nunique().rename(columns={'source_unit_id':'contributing_named_units'})
    tables['named_source_units.csv']=unit_counts
    if config.get('parent_assertions'):
        parents=loader.table(config['parent_assertions'],['stream','source_id','relation_dimension','parent_id','evidence_status','valid_time_limit','evidence_ref'])
        if parents.duplicated(['stream','source_id','relation_dimension']).any():raise ValueError('Conflicting parent dimension rows require resolution')
        pr=[]
        for stream,dim in [('newspaper','publisher_organization'),('social','platform_network'),('social','community')]:
            sf=sources[sources.stream==stream];p=parents[(parents.stream==stream)&(parents.relation_dimension==dim)]
            joined=sf[['source_id','after']].merge(p,on='source_id',how='left');joined['relation_dimension']=dim;joined['stream']=stream;joined['evidence_status']=joined.evidence_status.fillna('unmapped');pr.append(joined)
        tables['parent_dimension_coverage.csv']=pd.concat(pr,ignore_index=True)
    for key,columns in [('legacy_inventory',['month','known_candidates','unattempted_ready','pending','committed_new','exhaustion_status','evidence_ref']),('evidence_dispositions',['issue_id','stream','evidence_level','status','evidence_ref']),('capacity_observations',['stream','phase_id','at_utc','observation_kind','shared_cumulative_bytes','social_cumulative_bytes','outside_store_publication_bytes','pending_reserved_bytes','physical_headroom_bytes','nominal_allocation_headroom_bytes','stop_reason','evidence_ref'])]:
        if config.get(key):tables[key+'.csv']=loader.table(config[key],columns)
    if config.get('publication_charges'):
        charges=loader.table(config['publication_charges'],['charge_id','stream','bytes','evidence_ref']);valid_counts(charges,'bytes')
        if charges.groupby('charge_id').bytes.nunique().max()>1:raise ValueError('Conflicting repeated publication charge')
        tables['publication_charges.csv']=charges.drop_duplicates('charge_id')
    shares={}
    for frame,g in pool.groupby('frame'):
        total=int(g.units.sum());recent=g[g.year.between(2016,2026)&(g.month.str[-2:].astype(int)<=8)]
        denominator=int(recent.units.sum())
        shares[frame]={'full_history_2026_share':float(g.loc[g.year==2026,'units'].sum()/total) if total else None,
         'matched_Jan_Aug_2016_2026_share_of_2026':float(recent.loc[recent.year==2026,'units'].sum()/denominator) if denominator else None}
    fixed_table=tables['social_matched_baseline_source_frame.csv'];fixed_denominator=int(fixed_table.after.sum())
    shares['final_social_A_B_merged']['baseline_source_frame_matched_2026_share']=float(fixed_table.loc[fixed_table.year==2026,'after'].sum()/fixed_denominator) if fixed_denominator else None
    metrics={'publication_interval':['1988-01-01','2026-09-21'],'partial_end_month':True,'fixed_window_deadline_at_utc':DEADLINE,'frames':summary,'distribution_shares':shares,'social_merge':merge,'family_only_IDs':len(extra),'family_only_recovered_months':sorted(extra.month.unique()),'named_unit_counts':unit_counts.to_dict('records'),'source_classification_coverage':[{'stream':stream,'contributing_source_IDs':len(g),'named_classified_source_IDs':int(g.source_unit_id.notna().sum()),'unclassified_source_IDs':int(g.source_unit_id.isna().sum())} for stream,g in sources.groupby('stream')],'source_ID_counts_are_not_independent_parents':True,'joint_csv_policy':'all source-month cells reconciled in memory; unchanged cells omitted from the new derived changed-cell table; original inputs preserved by hash references','archive_completeness_not_established':True,'climate_emotion_fear_labels_executed':False,'terminal_acceptance':t,'missing_optional_inputs':[k for k in ['source_units','parent_assertions','legacy_inventory','evidence_dispositions','capacity_observations','publication_charges'] if not config.get(k)]}
    if not loader.unchanged():raise ValueError('Metadata changed during read')
    if out is not None:
        out.mkdir(parents=True,exist_ok=True)
        for name,table in tables.items():table.to_csv(out/name,index=False)
        (out/'METRICS.json').write_text(json.dumps(metrics,indent=2,default=int)+'\n')
        (out/'INPUT_RECEIPT.json').write_text(json.dumps({'inputs':loader.receipts,'all_hashes_unchanged':True,'database_raw_body_reads':False},indent=2)+'\n')
    return (metrics,tables) if return_tables else metrics

def analysis_bundle(metrics,tables,loader):
    payload={name:table.to_csv(index=False).encode() for name,table in tables.items()}
    payload['METRICS.json']=(json.dumps(metrics,indent=2,default=int)+'\n').encode()
    payload['INPUT_RECEIPT.json']=(json.dumps({'inputs':loader.receipts,'all_hashes_unchanged':True,'database_raw_body_reads':False},indent=2)+'\n').encode()
    return payload

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--validate-only',action='store_true');p.add_argument('--check-baseline',action='store_true');p.add_argument('--out',default='terminal_output');args=p.parse_args()
    cfg=json.loads(Path(args.config).read_text());loader=Inputs()
    out=(BASE/args.out).resolve()
    if not out.is_relative_to(BASE):raise ValueError('Output must remain in local report_preparation; no publication package is authorized')
    if not (args.validate_only or args.check_baseline):raise ValueError('Use finalize_report.py for one complete capacity-checked PNG bundle; no partial terminal output is written')
    metrics=run(cfg,loader,None,args.check_baseline)
    if args.check_baseline:
        (BASE/'PREPARATION_BASELINE_CHECK.json').write_text(json.dumps(metrics,indent=2,default=int)+'\n')
    print(json.dumps({'validation_passed':True,'baseline_only':args.check_baseline,'terminal_output_written':not(args.validate_only or args.check_baseline)}))
if __name__=='__main__':main()
