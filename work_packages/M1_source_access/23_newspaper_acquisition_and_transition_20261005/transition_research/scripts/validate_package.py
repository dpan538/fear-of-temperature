"""One bounded verification of research artifacts, retained evidence and citations."""
import csv
import datetime
import hashlib
import html
import io
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
checks=[]
def check(name,condition,details=""):
    checks.append(dict(check=name,passed=bool(condition),details=details))
def read_csv(name):
    with (ROOT/name).open(newline="",encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

sources=read_csv("SOURCE_REGISTRY.csv")
claims=read_csv("EVIDENCE_TABLE.csv")
annual=read_csv("LONGITUDINAL_VALUES.csv")
eras=read_csv("SOURCE_ERA_RECOMMENDATIONS.csv")
check("Unique source identities",len(sources)==len({r['source_id'] for r in sources}))
check("Unique claim identities",len(claims)==len({r['evidence_id'] for r in claims}))
check("Twelve core evidence families",len({r['evidence_family'] for r in sources if r['evidence_family']!='supplementary'})==12)
ids={r['source_id'] for r in sources}
check("Claim and annual source references resolve",all(r['source_id'] in ids for r in claims+annual))
required=['authors','title','publication_year','primary_url','study_period_or_field_dates','population',
          'design','sample_size_or_units','measure','denominator','verified_finding','primary_locator',
          'limitations_or_pending','full_text_read_scope','metadata_verification']
check("Required claim fields present",all(all(r.get(k) for k in required) for r in claims))
strata={s for r in claims for s in r['stratum'].split(';')}
check("All five strata addressed",{'US','UK','AU','NZ','EU_Europe_excluding_UK'}<=strata)
check("Five journal references",(ROOT/'references.bib').read_text().count('@article{')==5)

bib=(ROOT/'references.bib').read_text()
for f in ['crossref_westlund.json','crossref_fletcher.json','crossref_thurman.json','crossref_neuman.json','crossref_dewaal.json']:
    m=json.loads((ROOT/'sources'/f).read_text())['message']
    doi=m['DOI']
    entry=next((e for e in bib.split('@article{')[1:] if 'doi = {'+doi+'}' in e),None)
    check("Journal DOI resolves to saved Crossref metadata: "+doi,entry is not None)
    if entry:
        year=m['published-print']['date-parts'][0][0]
        check("Issue year, volume, number and pages: "+doi,
              all(v in entry for v in [f'year = {{{year}}}',f'volume = {{{m["volume"]}}}',
                    f'number = {{{m["issue"]}}}',f'pages = {{{m["page"].replace("-","--")}}}']))
        short=html.unescape(m['container-title'][0])
        check("Journal title: "+doi,'journal = {'+short+'}' in entry)

for filename,doi in [('dnr2015_doi.json','10.60625/risj-y3dr-t653'),
                     ('cornia2018_doi.json','10.60625/risj-cg3f-he14'),
                     ('au2025_doi.json','10.60836/md4e-k570')]:
    d=json.loads((ROOT/'sources'/filename).read_text())['data']['attributes']
    src=next(r for r in sources if r['doi']==doi)
    check('Report DOI/year: '+doi,d['doi'].lower()==doi and str(d['publicationYear'])==src['publication_year'])

for sid,name,scol,pcol in [('R02b','uk2017_sources_chart_v7.html','Social','Print'),
                          ('R02c','uk2018_sources_chart_v3.html','Social media','Printed newspapers')]:
    raw=(ROOT/'sources'/name).read_text()
    match=re.search(r'\n\s*data: ("(?:\\.|[^"\\])*")',raw)
    payload=json.loads(match.group(1))
    parsed=list(csv.DictReader(io.StringIO(payload)))
    selected=[r for r in annual if r['source_id']==sid]
    check('Original chart transcribed: '+sid,len(selected)==len(parsed) and
          all(float(a['social_percent'])==float(p[scol]) and float(a['newspaper_or_print_percent'])==float(p[pcol])
              and a['wave']==p.get('Year',p.get('Column1')) for a,p in zip(selected,parsed)))

raw=(ROOT/'sources/germany2020_chart_v4.html').read_text()
m=re.search(r'window\.__DW_SVELTE_PROPS__\s*=\s*JSON.parse\(("(?:\\.|[^"\\])*")\)',raw)
payload=json.loads(json.loads(m.group(1)))['data']['chartData']
parsed=list(csv.DictReader(io.StringIO(payload)))
selected=[r for r in annual if r['source_id']=='R03']
check('Original Germany2020 chart transcribed',len(selected)==len(parsed) and
      all(float(a['social_percent'])==float(p['Social']) and float(a['newspaper_or_print_percent'])==float(p['Print'])
          and a['wave']==p['Year'] for a,p in zip(selected,parsed)))

# Key arithmetic checks use the retained annual observations; they are not fitted transition models.
def first_above(sid,country):
    rows=[r for r in annual if r['source_id']==sid and r['geography']==country]
    return next((r['wave'] for r in rows if float(r['social_percent'])>float(r['newspaper_or_print_percent'])),None)
check('UK2018 first strict exceedance in displayed series',first_above('R02c','United Kingdom')=='2018')
check('Germany2020 first strict exceedance in displayed series',first_above('R03','Germany')=='2020')
check('Ofcom comparable-wave first exceedance is2022W2',first_above('R06','United Kingdom')=='2022 W2')
check('NZ unresolved timing retained',next(r for r in claims if r['evidence_id']=='E20')['timing_status']=='national newspaper/social crossover unresolved')
check('Recommendations preserve fixed endpoint and calendar',all('2026-09-21' in r['collection_frame'] and 'Jan1988-Sep2026' in r['collection_frame'] for r in eras))

receipts=[json.loads(line) for line in (ROOT/'sources/RETRIEVAL_RECEIPTS.jsonl').read_text().splitlines() if line]
saved=[r for r in receipts if r['retrieval_status']=='saved']
mismatches=[]
for receipt in saved:
    path=ROOT/receipt['local_file']
    if not path.is_file(): mismatches.append(receipt['local_file']+': missing');continue
    data=path.read_bytes()
    if len(data)!=receipt['bytes'] or hashlib.sha256(data).hexdigest()!=receipt['sha256']:
        mismatches.append(receipt['local_file']+': bytes/hash differ')
check('Retained public retrieval objects match receipt hashes',not mismatches,', '.join(mismatches))
check('Authored reports contain no CJK text',all(not re.search(r'[\u3400-\u9fff]',(ROOT/f).read_text()) for f in
      ['RESEARCH_REPORT.md','SEARCH_AND_VERIFICATION_LOG.md','references.bib']))

report=dict(validated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='This bounded research package only; no corpus audit or acquisition',
    counts=dict(source_entries=len(sources),core_families=12,claim_rows=len(claims),
                annual_comparisons=len(annual),era_recommendations=len(eras),journal_references=5,
                saved_public_retrieval_objects=len(saved),failed_public_retrieval_requests=len(receipts)-len(saved)),
    passed=all(c['passed'] for c in checks),checks=checks,
    unresolved=['Full-text/field-date/base limits stated in source registry',
                'Survey vintages and taxonomy differences not harmonised',
                'Ofcom2024 and NZOnAir2024 base differences not resolved',
                'NZ national crossover not identified; no universal switch year'])
(ROOT/'VALIDATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
manifest=[]
for p in sorted(ROOT.rglob('*')):
    if p.is_file() and p.name!='PACKAGE_MANIFEST.json':
        data=p.read_bytes();manifest.append(dict(path=str(p.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(ROOT/'PACKAGE_MANIFEST.json').write_text(json.dumps(dict(created_at_utc=report['validated_at_utc'],files=manifest),indent=2)+'\n')
print(json.dumps(dict(passed=report['passed'],checks=len(checks),failed_checks=[c for c in checks if not c['passed']],counts=report['counts'],manifest_files=len(manifest))))
if not report['passed']: raise SystemExit(1)
