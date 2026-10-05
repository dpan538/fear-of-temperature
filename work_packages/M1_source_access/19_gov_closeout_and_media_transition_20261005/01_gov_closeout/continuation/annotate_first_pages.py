"""Resolve three cover-place parser limits from saved first-page evidence only."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;OWNER=HERE.parent


def read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))


def save_csv(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def main():
    evidence={r['item_uri']:r for r in json.loads((HERE/'evidence/FIRST_PAGE_IDENTITY.json').read_text())}
    rows=read(HERE/'CHANGED_ITEM_TEXT_SHAPE.csv');original=json.loads((HERE/'CHANGED_ITEM_CHECK.json').read_text())
    if not (HERE/'AUTOMATED_CHANGED_ITEM_CHECK.json').exists():
        (HERE/'AUTOMATED_CHANGED_ITEM_CHECK.json').write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n')
    frozen={r['item_uri']:r for r in json.loads((HERE/'B_CORRECTED/RESULT.json').read_text())['outcomes']}
    explicit={14:'Draft amending budget No1',16:'European Fund for Strategic Investments regulation proposal',21:'Stability and Growth Pact flexibility communication'}
    observations=[]
    for r in rows:
        seq=int(r['sequence_new']);text=evidence[r['item_uri']]['first_page_text']
        r.update({k:frozen[r['item_uri']][k] for k in ['source_id','jurisdiction','discourse_role','issuer','genre','language',
                 'parent_manifest','work_query_evidence','metadata_checkpoint_utc','item_route_evidence','date_support']})
        r['metadata_observed_at_utc']=r['metadata_checkpoint_utc']
        if seq in explicit:
            assert 'Strasbourg, 13.1.2015' in text
            r.update(printed_issue_date='2015-01-13',printed_date_role='COM cover Strasbourg date',
                     issue_date_comparison='agrees_with_saved_Work_day',printed_heading_label=explicit[seq],
                     manual_date_observation='saved first-page text and image; original parser only matched Brussels')
        if seq==24:
            assert '31.1.2015' in text and r['publication_dates']=='2015-01-30'
            r['issue_date_comparison']='conflict_one_day_same_month'
            r['manual_date_observation']='OJ2015/C33/05 printed2015-01-31 vs savedCDM2015-01-30; no correction applied'
        r['visual_check']='first page legible and inspected; remaining pages not visually inspected'
        r['analysis_month_support']='2015-01 under both saved CDM day and observed printed day; day-level conflict retained where named'
        observations.append({k:r[k] for k in ['sequence_new','parent_id','item_uri','publication_dates','printed_issue_date',
                            'printed_date_role','issue_date_comparison','printed_references','observed_genre',
                            'selected_manifestation_distinct_items','first_page_multiple_OJ_notice_refs','visual_check',
                            'complete_work_status','parent_statistics_eligible']})
    save_csv('CHANGED_ITEM_TEXT_SHAPE.csv',rows);save_csv('CHANGED_ITEM_IDENTITY_DATE.csv',observations)
    allrows=[{**r,'tranche':'old20','sequence_native':r['sequence']} for r in read(OWNER/'CHANGED_ITEM_TEXT_SHAPE.csv')]
    allrows += [{**r,'tranche':'new27','sequence_native':r['sequence_new']} for r in rows]
    by=defaultdict(list)
    for r in allrows:by[r['raw_sha256']].append(r)
    groups=[]
    for digest,rr in by.items():
        if len(rr)>1:
            for r in rr:
                groups.append({'raw_sha256':digest,'group_Items':len(rr),'parent_id':r['parent_id'],'item_uri':r['item_uri'],
                               'tranche':r['tranche'],'sequence_native':r['sequence_native'],
                               'printed_reference':r.get('printed_references',r.get('printed_reference','')),
                               'relation':'identical saved rendition bytes under different frozen Work/Item identities',
                               'action':'retain originals; selected Work text boundary and shared-rendition ownership pending; no automatic deletion'})
    save_csv('CROSS_WORK_IDENTICAL_ITEM_GROUPS.csv',groups)
    result={**original,'annotated_at_utc':datetime.now(timezone.utc).isoformat(),
            'printed_date_comparison_counts':dict(Counter(r['issue_date_comparison'] for r in rows)),
            'visual_first_page_check':'all27newfirst pages inspected;257totalpages not all visually inspected',
            'manual_parser_limit_resolutions':3,'new_first_page_day_conflicts':1,
            'cumulative_Item_rows':47,'cumulative_raw_sha256_unique':len(by),
            'cross_Work_identical_rendition_groups':len({r['raw_sha256'] for r in groups}),
            'cross_Work_identical_group_Item_rows':len(groups),
            'new_observed_COM_JOIN_documents':sum(r['observed_genre']=='printed COM/SWD/JOIN document' for r in rows),
            'new_observed_OJ_renditions':sum('Official Journal' in r['observed_genre'] for r in rows),
            'raw_rereads_during_annotation':0,'old20_rechecked_during_annotation':False}
    (HERE/'CHANGED_ITEM_CHECK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
