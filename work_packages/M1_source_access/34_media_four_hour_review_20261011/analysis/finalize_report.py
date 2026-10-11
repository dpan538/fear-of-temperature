"""After closure, build and QA one complete local report in memory, then enforce its reserved footprint."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
from analyze_report import BASE,Inputs,run,analysis_bundle
from render_report import build

JOINT_LIMIT=4*1024*1024
ARTIFACT_LIMIT=1024*1024

def json_bytes(value):return (json.dumps(value,indent=2,default=int)+'\n').encode()
def footprint(payload):
    total=sum(map(len,payload.values()));largest=max(map(len,payload.values()),default=0)
    return {'final_joint_bytes':total,'largest_artifact_bytes':largest,'maximum_atomic_coexistence_bytes':largest,'conservative_peak_bytes':total+largest,'joint_reserved_limit_bytes':JOINT_LIMIT,'single_artifact_limit_bytes':ARTIFACT_LIMIT}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--out',default='terminal_output')
    p.add_argument('--qa-python',default='python3',help='Existing Python runtime containing PyMuPDF')
    args=p.parse_args();cfg=json.loads(Path(args.config).read_text())
    target=(BASE/args.out).resolve()
    if not target.is_relative_to(BASE) or target==BASE:raise ValueError('Output must be a new child of local report_preparation')
    if target.exists():raise ValueError('Refusing to overwrite an existing report or retry partial output; preserve it and inspect the named failure')
    skill=Path('/Users/jarlgiovanni/.codex/skills/nature-figure/scripts')
    pre=subprocess.run([args.qa_python,str(skill/'validate_figure.py'),str(BASE/'render_report.py'),'--json'],capture_output=True,text=True)
    report=json.loads(pre.stdout) if pre.stdout else {'findings':[{'check_id':'PREFLIGHT-RUNTIME','level':'FAIL','message':pre.stderr}]}
    failures=[r for r in report['findings'] if r['level']=='FAIL' and r['check_id']!='EXPORT-VECTOR']
    report['authorized_format_exception']={'check_id':'EXPORT-VECTOR','reason':'The user requests PNG-only final delivery; the actual generated PDF is audited in memory, without persisted SVG/PDF duplication','other_failures_block_output':True}
    report['effective_preflight_pass']=not failures
    if failures:raise ValueError('Figure source preflight failed: '+json.dumps(failures))
    loader=Inputs();metrics,tables=run(cfg,loader,return_tables=True)
    payload=analysis_bundle(metrics,tables,loader)
    payload.update(build(metrics,tables,args.qa_python))
    payload['qa/source_preflight.json']=json_bytes(report)
    payload['REPORT_NOTES.md']=(
        '# Local four-hour metadata review\n\n'
        'Fixed publication interval: 1988-01-01 through 2026-09-21; September is partial. '
        'The frozen legacy baseline, comparable legacy final and separately versioned newspaper-family final are distinct. '
        'Observed monthly text presence does not establish complete archives.\n\n'
        'Social immutable A/B deltas are reconciled cell by cell against the final-minus-baseline source-month snapshot. '
        'Source IDs, named title/forum/Q&A units, publisher, platform and community dimensions remain distinct. '
        'Unknown parent identity, applicability and inventory denominators remain unknown.\n\n'
        'All report tables and seven 300 dpi PNGs are generated once from hash-bound metadata. '
        'Generated QA PDFs are held only in memory. The largest possible atomic companion is included in the reported footprint. '
        'A/B source-table and implementation publication copies are inputs under their own reserves and are not copied again here. '
        'All output bytes still require one actual accounting charge; the report manifest is not an allocation or collector restart.\n\n'
        'Automated alignment, PDF text/collision and source checks pass before writing. '
        'Every exported PNG still requires visual inspection, with any failure recorded and no final coordinator decision inferred.\n'
    ).encode()
    code_refs=[{'path':str(BASE/name),'sha256':hashlib.sha256((BASE/name).read_bytes()).hexdigest()} for name in ['analyze_report.py','render_report.py','qa_memory.py','finalize_report.py']]
    manifest={'delivery_format':'PNG','terminal_inputs':loader.receipts,'script_refs':code_refs,'manual_visual_inspection_required':True,'manifest_self_hash_excluded':True,'source_preflight_format_exception':report['authorized_format_exception'],'artifacts':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(payload.items())]}
    payload['FINAL_MANIFEST.json']=json_bytes(manifest)
    previous=None
    for _ in range(12):
        size=footprint(payload)
        payload['OUTPUT_FOOTPRINT.json']=json_bytes(size)
        manifest['artifacts']=[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(payload.items()) if name!='FINAL_MANIFEST.json']
        payload['FINAL_MANIFEST.json']=json_bytes(manifest)
        if footprint(payload)==size and size==previous:break
        previous=size
    else:raise ValueError('Footprint manifest did not converge; no output written')
    size=footprint(payload)
    oversized=[{'path':name,'bytes':len(data)} for name,data in payload.items() if len(data)>ARTIFACT_LIMIT]
    if size['conservative_peak_bytes']>JOINT_LIMIT or oversized:
        print(json.dumps({'written':False,'capacity_requirement':size,'oversized_artifacts':oversized,'action':'Report actual requirement; do not lower accounting, delete evidence or shrink legibility to bypass the reserve'}))
        return 2
    if not loader.unchanged():raise ValueError('Accepted inputs changed after rendering; no report written')
    target.mkdir()
    for name,data in sorted(payload.items()):
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    print(json.dumps({'written':True,'output':str(target),'footprint':size,'manual_visual_inspection_required':True}))
    return 0
if __name__=='__main__':sys.exit(main())
