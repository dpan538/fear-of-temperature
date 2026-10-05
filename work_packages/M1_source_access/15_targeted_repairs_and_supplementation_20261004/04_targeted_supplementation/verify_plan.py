"""Check frozen identities, month accounting, dates and no-download preflight."""
import ast
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def read_csv(name):
    return list(csv.DictReader((HERE/name).open()))


def main():
    contract=json.loads((HERE/'ACQUISITION_CONTRACT.json').read_text())
    targets=read_csv('frozen_acquisition_manifest.csv')
    population=read_csv('source_frame_population.csv')
    coverage=read_csv('coverage_expected_vs_observed.csv')
    leads=read_csv('potential_requests.csv')
    checks=[]
    def check(label,condition):
        checks.append({'check':label,'passed':bool(condition)})
        if not condition:raise AssertionError(label)
    digest=hashlib.sha256((HERE/'frozen_acquisition_manifest.csv').read_bytes()).hexdigest()
    check('frozen manifest content hash',digest==contract['manifest_sha256'])
    check('source population accounts for targets and no-links',len(population)==1009 and len(targets)==979 and sum(not r['item_uri'] for r in population)==30)
    check('unique Work and selected Item identities',len({r['parent_id'] for r in targets})==979 and len({r['item_uri'] for r in targets})==979)
    check('all consecutive 2015 months retained',sorted({r['month'] for r in population})==[f'2015-{n:02d}' for n in range(1,13)])
    check('published dates stay in declared tranche',all('2015-01-01'<=date<='2015-12-31' and date[:7]==r['month'] for r in targets for date in r['publication_dates'].split(';')))
    counts=Counter(r['month'] for r in targets)
    check('monthly route counts reconcile',all(counts[r['month']]==int(r['candidate_item_works']) and int(r['enumerated_parent_works'])==int(r['candidate_item_works'])+int(r['no_item_link_works']) for r in coverage))
    check('current Task4 acquired/body counts are zero',all(int(r['observed_task4_downloads'])==int(r['observed_task4_verified_full_bodies'])==0 for r in coverage) and not (HERE/'raw').exists())
    check('A leads remain provisional without invented dates',len(leads)==3 and all(r['fetch_permitted']=='False' and r['publication_date']=='' for r in leads))
    check('no semantic selection or database writes in contract',contract['semantic_filters'] is None and contract['formal_database_writes'] is False)
    check('15 GiB floor preserved',contract['budget']['collector_floor_bytes']==15*2**30)
    check('frozen metadata inputs unchanged',all((ROOT/r['parent_manifest']).exists() and (ROOT/r['item_route_evidence']).exists() for r in targets))
    input_manifest=json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    # Project log/control can progress concurrently; frozen target metadata must match exactly.
    metadata_checks=[]
    for path,detail in input_manifest['inputs'].items():
        if '/10_eu_cellar_acquisition/manifests/' in path or 'monthly_source_genre_counts.csv' in path:
            actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            metadata_checks.append(actual==detail['sha256'])
    check('hashed selected metadata/composition inputs unchanged',bool(metadata_checks) and all(metadata_checks))
    for name in ['build_plan.py','stage_frozen_items.py','verify_plan.py']:
        ast.parse((HERE/name).read_text())
    check('local helper syntax',True)
    result=subprocess.run([sys.executable,str(HERE/'stage_frozen_items.py')],capture_output=True,text=True,check=True)
    preflight=json.loads(result.stdout)
    check('default runner performs no download',preflight['downloads_started'] is False and not (HERE/'raw').exists())
    guarded=subprocess.run([sys.executable,str(HERE/'stage_frozen_items.py'),'--execute'],capture_output=True,text=True,check=True)
    guarded_result=json.loads(guarded.stdout)
    check('execute flag without reviewed release fails closed',guarded_result['repair_gate_passes'] is False and guarded_result['downloads_started'] is False and not (HERE/'raw').exists())
    if not (ROOT/contract['repair_release_path']).exists():
        check('absent repair marker fails closed',preflight['status']=='waiting_on_repair' and preflight['repair_gate_passes'] is False)
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed','checks':checks,
            'passed_checks':len(checks),'network_download_tests':0,'formal_database_tests':0,
            'execution_limit':'runner syntax and guarded no-download path verified; released network stream path not executed',
            'preflight':preflight}
    (HERE/'VERIFY_RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'passed','checks':len(checks),'preflight_status':preflight['status']}))


if __name__=='__main__':main()
