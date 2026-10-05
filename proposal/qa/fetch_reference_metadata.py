from pathlib import Path
import re,json,urllib.request,concurrent.futures
p=Path(__file__).resolve().parents[1];out=p/'qa/finalisation_sources'
bib=(p/'references.bib').read_text();jobs=[]
for m in re.finditer(r'^@\w+\{([^,]+),\n(.*?)^\}',bib,re.M|re.S):
 d=re.search(r'doi = \{([^}]+)',m[2])
 if d:jobs.append((m[1],'https://api.crossref.org/works/'+d[1],'.json'))
for k,u in [('uq_ethics','https://policies.uq.edu.au/document/view-current.php?id=346'),('uq_applications','https://research-support.uq.edu.au/resources-and-support/ethics-integrity-and-compliance/human-ethics/ethics-application'),('apa_dois','https://apastyle.apa.org/style-grammar-guidelines/references/dois-urls')]:jobs.append((k,u,'.html'))
for k,aid in [('reimers2019','D19-1410'),('pontiki2014','S14-2004'),('demszky2020','2020.acl-main.372'),('xia2019','P19-1096')]:jobs.append((k+'_acl','https://aclanthology.org/'+aid+'.bib','.bib'))
def fetch(j):
 k,u,e=j
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'Research-bibliography-check/1.0'})
  with urllib.request.urlopen(req,timeout=25) as r:data=r.read()
  (out/(k+e)).write_bytes(data);return {'key':k,'url':u,'ok':True}
 except Exception as err:return {'key':k,'url':u,'ok':False,'error':str(err)}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:results=list(ex.map(fetch,jobs))
(out/'fetch_log.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
