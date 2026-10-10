"""Run with a Python runtime containing PyMuPDF; default system python3 is suitable here."""
from pathlib import Path
import json,subprocess,sys,argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--only',help='Recheck one changed figure, preserving prior checks for unchanged exports')
args=parser.parse_args()
OUT=Path(__file__).resolve().parent
QA=OUT/'qa'
SKILL=Path('/Users/jarlgiovanni/.codex/skills/nature-figure/scripts')
results=[]
if args.only and (QA/'QA_SUMMARY.json').exists():
    results=[r for r in json.loads((QA/'QA_SUMMARY.json').read_text())['rendered_checks'] if r['figure']!=args.only]
pre=subprocess.run([sys.executable,str(SKILL/'validate_figure.py'),str(OUT/'build_review.py'),'--json'],capture_output=True,text=True)
(QA/'source_preflight.json').write_text(pre.stdout)
for p in sorted(QA.glob('*.pdf')):
    if 'collision' in p.name:continue
    if args.only and p.stem!=args.only:continue
    t=subprocess.run([sys.executable,str(SKILL/'audit_pdf_text.py'),str(p),'--min-pt','5','--json'],capture_output=True,text=True)
    (QA/(p.stem+'.text_audit.json')).write_text(t.stdout)
    c=subprocess.run([sys.executable,str(SKILL/'audit_figure_collisions.py'),str(p),'--json-out',str(QA/(p.stem+'.collision.json'))],capture_output=True,text=True)
    results.append({'figure':p.stem,'text_exit':t.returncode,'collision_exit':c.returncode,'collision_report':str(QA/(p.stem+'.collision.json'))})
    print(p.stem,t.returncode,c.returncode)
summary={'source_preflight_exit':pre.returncode,'rendered_checks':sorted(results,key=lambda r:r['figure']),'all_automated_checks_pass':pre.returncode==0 and all(x['text_exit']==0 and x['collision_exit']==0 for x in results)}
(QA/'QA_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
sys.exit(0 if summary['all_automated_checks_pass'] else 1)
