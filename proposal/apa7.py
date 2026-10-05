"""APA 7 references for the document's curated BibTeX entry types.
Sentence case is stored explicitly in BibTeX, not guessed by lowercasing.
UQ proposal page layout is preserved independently of reference styling.
"""
import re,html,unicodedata
from collections import defaultdict

def initials(first):
 return ' '.join('-'.join(p[0]+'.' for p in w.split('-') if p) for w in first.strip().split())
def names(author,editor=False):
 out=[]
 for n in author.split(' and '):
  if ',' not in n:out.append(n);continue
  last,first=n.split(',',1);i=initials(first)
  out.append(i+' '+last if editor else last+', '+i)
 if len(out)>20:out=out[:19]+['…',out[-1]];return ', '.join(out)
 return out[0] if len(out)==1 else ', '.join(out[:-1])+(' & ' if editor and len(out)==2 else ', & ')+out[-1]
def alphabet(s):
 return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
def title_sort(s):return re.sub(r'^(a|an|the)\s+','',s,flags=re.I)
def ordered(entries):
 return sorted(entries,key=lambda k:(alphabet(re.sub(r'^The ','',entries[k]['author'])),entries[k].get('year','0000'),alphabet(title_sort(entries[k]['title']))))
def dates(entries):
 group=defaultdict(list);out={}
 for k in ordered(entries):group[(entries[k]['author'],entries[k].get('year','n.d.'))].append(k)
 for (_,year),ks in group.items():
  for i,k in enumerate(ks):out[k]=year+(('' if year!='n.d.' else '-')+chr(97+i) if len(ks)>1 else '')
 return out

def citation(k,entries,date):
 ns=[n.split(',',1)[0] for n in entries[k]['author'].split(' and ')]
 author=ns[0]+' et al.' if len(ns)>2 else ' & '.join(ns)
 return author+', '+date[k]

def reference(k,entries,date,markup=True):
 e=entries[k];esc=lambda s:html.escape(s,quote=False) if markup else s
 italic=lambda s:'<i>'+esc(s)+'</i>' if markup else s
 author=esc(names(e['author']));s=author+' ('+date[k]+'). '
 title=e['title'];typ=e['type'];pages=e.get('pages','').replace('--','–')
 if typ=='article':
  s+=esc(title)+'. '+italic(e['journal'])
  if 'volume' in e:s+=', '+italic(e['volume'])
  if 'number' in e:s+='('+esc(e['number'])+')'
  if pages:s+=', '+('Article ' if '–' not in pages and pages.isdigit() else '')+pages
  s+='.'
 elif typ=='inproceedings':
  s+=esc(title)+'. In '+esc(names(e['editor'],True))+' (Eds.), '+italic(e['booktitle'])+' (pp. '+pages+'). '+esc(e['publisher'])+'.'
 elif e.get('archivePrefix')=='arXiv':s+=italic(title)+'. arXiv.'
 else:
  s+=italic(title)
  if e.get('format'):s+=' ['+esc(e['format'])+']'
  s+='.'
 url='https://doi.org/'+e['doi'] if e.get('doi') else e['url']
 # Mutable institutional guidance, software and datasets use a documented retrieval date.
 if not e.get('doi') and e.get('urldate') and k!='reit7842':s+=' Retrieved September 15, 2026, from'
 s+=' '+(f'<a href="{html.escape(url,quote=True)}" color="#51247A">{esc(url)}</a>' if markup else url)
 return s
