import json,datetime as dt
import elt,production,broaden,native_html,extract_load
checks=[]
def test(name,assertion):
 assert assertion,name;checks.append({'test':name,'passed':True})
def t(url,month='1992-01',sid='green_left'):return {'source_id':sid,'url':url,'month':month,'native_evidence':{}}
items=[t('https://www.greenleft.org.au/1992/45/news/first'),t('https://www.greenleft.org.au/1992/45/news/second'),t('https://www.greenleft.org.au/1992/45/news/third')]
production.elt.state=lambda:{'access_stops':{}}
# Native status reader has no source-body threshold input.
test('source month at two complete bodies still returns third eligible inventory',len(production.eligible(items,{'https://www.greenleft.org.au/1992/45/news/first','https://www.greenleft.org.au/1992/45/news/second'},set(),{('AU','1992-01'):2},'AU','historical_native'))==1)
test('legitimate inventory beyond first batch remains eligible',len(production.eligible(items,set(),set(),{('AU','1992-01'):200},'AU','historical_native'))==3)
test('source existence is local and GL cannot supply pre-foundation fixture',not production.eligible([t('https://www.greenleft.org.au/1988/1/news/x','1988-01')],set(),set(),{},'AU','historical_native'))
test('fixed endpoint Sep21 retained and later publication ineligible',elt.eligible('2026-09-21') and not elt.eligible('2026-09-22'))
# Camden is evidenced as a1982-founded newspaper; no global1991 calendar start.
extract_load.ADAPTERS['camden_new_journal']={'title':'Camden New Journal','stratum':'UK','country':'UK','edition':'fixture','frame':'fixture'}
raw=b'<article class="Article__container"><h1>Historical fixture</h1><div class="ArticlePublishInfo">Friday, 1st January 1988</div><div class="Article__content"><p>Complete short original prose.</p></div></article>'
r,b,s=native_html.parse(raw,'camden_new_journal','https://www.camdennewjournal.co.uk/article/fixture')
test('pre1991 eligible whole article fixture can qualify independently',r['publication_date']=='1988-01-01' and s=='confirmed_complete')
raw=b'<h1>Fixture</h1><meta property="article:published_time" content="1992-01-15T10:00:00"><meta property="article:modified_time" content="2026-09-01T10:00:00"><article class="node--type-article"><div class="field--name-field-body"><p>Original complete prose.</p></div></article>'
r,b,s=extract_load.parse(raw,'green_left','https://www.greenleft.org.au/1992/45/news/fixture')
test('publication precedes2026 content version',r['publication_date']=='1992-01-15' and s=='confirmed_complete')
r,b,s=extract_load.parse(b'<h1>Fixture</h1><meta property="article:modified_time" content="2026-09-01"><article class="node--type-article"><div class="field--name-field-body"><p>Prose.</p></div></article>','green_left','https://www.greenleft.org.au/1992/45/news/missing')
test('missing publication never defaults to retrieval or current year',r['publication_date'] is None and s!='confirmed_complete')
# Exercise real parser without source transport/corpus writes.
from green_left_issue_candidates import issue_candidates
raw=b'<h1>Issue 45</h1><main><div class="layout-content"><div class="region-content"><a href="/1992/45/news/real">Real</a><aside><a href="/2026/1464/news/sidebar">Current sidebar</a></aside></div></div></main>'
o=issue_candidates(raw,'https://www.greenleft.org.au/issue/45')
test('native issue discovery excludes current sidebar and validates issue relation',len(o['candidates'])==1 and o['candidates'][0]['issue_relation']=='path_issue_matches')
# Public API pagination uses native next, never a first-batch completion flag.
p={'source_id':'fixture','root_url':'https://fixture.example','stratum':'US','country':'US','title':'Fixture','edition':'Fixture','source_frame':'Fixture','title_classification_reference':'fixture','source_access_reference':'fixture','retention_limit':'private','classification_verified':True,'source_use_gate_passed':True,'public_API_documentation_reference':'https://developer.wordpress.org/rest-api/'}
v={'fixture':{'stage':'metadata_pages','next_url':'https://fixture.example/wp-json/wp/v2/posts?page=1','collection_url':'https://fixture.example/wp-json/wp/v2/posts','api_root':'https://fixture.example/wp-json/','queued_native_post_IDs':[],'attempted_pages':0}}
seen=[];queued=[]
broaden.profiles=lambda:[p];broaden.active_ids=lambda geo=None:['fixture'];broaden._state=lambda:v;broaden._save=lambda o:None;broaden._update_frontier=lambda *a:None;broaden._permitted=lambda *a:True
broaden._fetch=lambda p,u,e:seen.append(u) or {'status':'saved','raw_reference':u,'target_id':str(len(seen)),'hops':[{'link':'<https://fixture.example/wp-json/wp/v2/posts?page=2>; rel="next"' if len(seen)==1 else '', 'x_wp_total':'2','x_wp_totalpages':'2'}]}
elt.read_payload=lambda ref:json.dumps([{'id':len(seen),'date':'1988-02-01T10:00:00','link':'https://fixture.example/article/'+str(len(seen)),'_links':{'self':[{'href':'https://fixture.example/wp-json/wp/v2/posts/'+str(len(seen))}]},'title':{'rendered':'Original'}}]).encode()
broaden.discover('fixture',lambda sid,items:queued.extend(items));broaden.discover('fixture',lambda sid,items:queued.extend(items))
test('native pagination advances past first batch and oldest fixture date retained',len(seen)==2 and seen[-1].endswith('page=2') and len(queued)==2 and queued[0]['month']=='1988-02')
test('native exhaustion does not consume body opportunities',v['fixture']['stage']=='exhausted' and len(production.eligible(queued,set(),set(),{('US','1988-02'):2},'US','historical_native'))==2)
(elt.OWN/'CHANGED_CHAIN_CHECK.json').write_text(json.dumps({'at_utc':elt.utc(),'all_passed':True,'checks':checks,'source_network':False,'corpus_writes':False},indent=2)+'\n')
print(json.dumps({'all_passed':True,'checks':len(checks)}))
