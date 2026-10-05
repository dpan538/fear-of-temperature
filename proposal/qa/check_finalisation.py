from pathlib import Path
import re,json,sys,hashlib
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r));sys.path.insert(0,str(r/'.runtime'))
import pymupdf as fitz
from apa7 import ordered,dates,reference,citation
bib=(r/'references.bib').read_text();entries={}
for m in re.finditer(r'^@(\w+)\{([^,]+),\n(.*?)^\}',bib,re.M|re.S):
 e={a:b.replace('{','').replace('}','') for a,b in re.findall(r'^\s*(\w+)\s*=\s*\{(.*)\},?$',m[3],re.M)};e['type']=m[1];entries[m[2]]=e
md=(r/'thesis_proposal.md').read_text();ht=(r/'thesis_proposal.html').read_text();txt=(r/'thesis_proposal.txt').read_text()
with fitz.open(r/'thesis_proposal.pdf') as d:
 text='\n'.join(p.get_text() for p in d);pdfurls={a['uri'] for p in d for a in p.get_links() if a.get('uri')}
refs=ordered(entries);ds=dates(entries)
checks={
 '31_bib_entries':len(entries)==31,
 '20_dois':sum('doi' in e for e in entries.values())==20,
 'author_date_not_numeric_citations':not re.search(r'\[\d+(?:,\s*\d+)*\]',text),
 'no_raw_citation_keys_in_exports':not re.search(r'\[@\w+',ht+txt+text),
 'alphabetical_references':re.findall(r'class="reference" id="ref-([^"]+)"',ht)==refs,
 'all_doi_links_in_pdf':all('https://doi.org/'+e['doi'] in pdfurls for e in entries.values() if 'doi' in e),
 'apa_undated_disambiguation':ds['openai_chatgpt']=='n.d.-a' and ds['openai_codex']=='n.d.-b' and ds['uq_ethics']=='n.d.',
 'no_deferred_deadline_note':not any(re.search(r'Conditional on clarification|26 Oct(?:ober)? 2026|report.deadline conflict',s,re.I) for s in [md,ht,txt,text]),
 'no_discussion_draft_label':not any('Complete discussion draft' in s for s in [md,ht,txt,text]),
 'cs_title_in_all_formats':all('Computational analysis of policy, media' in s for s in [md,ht,txt,text]),
 'ethics_route_present':all(s in re.sub(r'\s+',' ',text) for s in ['MyResearch','Human Research Ethics Committee','Research Ethics and Integrity']),
 'compatibility_links':all((r/f'draft_proposal.{ext}').is_symlink() for ext in ['md','pdf','html','txt']),
}
report={'checks':checks,'pdf_sha256':hashlib.sha256((r/'thesis_proposal.pdf').read_bytes()).hexdigest(),'reference_order':refs,'date_labels':ds,'APA_layout_note':'APA 7 reference style within UQ proposal page layout; not an APA double-spaced manuscript.'}
(r/'qa/finalisation_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert all(checks.values())
