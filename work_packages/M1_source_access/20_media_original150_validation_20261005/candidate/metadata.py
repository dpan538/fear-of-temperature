"""Structural candidates only. No topic/affect labels and no implicit full-body claim."""
import json,re,calendar
from datetime import datetime
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from identity import canonical

def date_value(value):
 if not isinstance(value,str):return {'raw':value,'precision':'unknown','valid':False,'month':None,'timezone':None}
 try:
  if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):datetime.strptime(value,'%Y-%m-%d');precision='day';zone=None
  elif re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?',value):
   d=datetime.fromisoformat(value.replace('Z','+00:00'));zone=d.strftime('%z') if d.tzinfo else None;precision='timestamp_with_offset' if zone else 'timestamp_timezone_unknown'
  else:raise ValueError('Unsupported date precision')
  return {'raw':value,'precision':precision,'valid':True,'month':value[:7],'local_day':value[:10],'timezone':zone}
 except (ValueError,TypeError):return {'raw':value,'precision':'invalid_or_unknown','valid':False,'month':None,'timezone':None}

def eligible(value,month):
 d=date_value(value);return d['valid'] and d['month']==month and '1988-01-01'<=d['local_day']<='2026-09-21'

def challenge(data):
 s=BeautifulSoup(data,'html.parser');title=(s.title.get_text(' ',strip=True) if s.title else '').lower();text=s.get_text(' ',strip=True)
 structural=bool(s.find('script',src=re.compile(r'_Incapsula_Resource|/cdn-cgi/challenge-platform|_cf_chl',re.I)))
 gate=title in {'just a moment...','access denied','robot check','verify you are human'}
 # Mentioning captcha in an ordinary article/privacy text is not itself a gate.
 return {'state':'access_challenge' if gate or (structural and not s.find('article')) else 'not_structurally_challenge','visible_text_chars':len(text),'stop':gate or (structural and not s.find('article'))}

def nodes(soup):
 result=[]
 def walk(x):
  if isinstance(x,list):
   for y in x:walk(y)
  elif isinstance(x,dict):
   t=x.get('@type',[]);t=[t] if isinstance(t,str) else t
   if any(y in {'Article','NewsArticle','ReportageNewsArticle','OpinionNewsArticle'} for y in t):result.append(x)
   if '@graph' in x:walk(x['@graph'])
 for n in soup.find_all('script',type='application/ld+json'):
  try:walk(json.loads(n.get_text()))
  except (ValueError,TypeError):pass
 return result

def extract(data,url,month,body_selector=None):
 soup=BeautifulSoup(data,'html.parser');c=soup.find('link',rel='canonical');u=canonical(urljoin(url,c.get('href'))) if c and c.get('href') else canonical(url)
 answer={'canonical_url':u,'identity_status':'pending','first_publication':None,'updated':None,'eligible_month':False,'body_text':None,'body_selector':body_selector,'readability_status':'boundary_pending','rights_status':'article_specific_pending','content_version_time':None}
 if challenge(data)['stop']:answer['readability_status']='access_challenge';return answer
 if urlsplit(u).hostname!=urlsplit(url).hostname:answer['identity_status']='canonical_cross_host_conflict';return answer
 matched=[];unbound=[]
 for x in nodes(soup):
  refs=[x.get('url'),x.get('@id'),x.get('mainEntityOfPage')]
  refs=[r.get('@id') or r.get('url') if isinstance(r,dict) else r for r in refs]
  refs=[canonical(urljoin(url,r.split('#')[0])) for r in refs if isinstance(r,str)]
  if u in refs:matched.append(x)
  elif not refs:unbound.append(x)
 if len(matched)!=1:
  answer['identity_status']='ambiguous_or_unbound_article_nodes';return answer
 x=matched[0];answer.update(identity_status='canonical_JSONLD_match',first_publication=date_value(x.get('datePublished')),updated=date_value(x.get('dateModified')),eligible_month=eligible(x.get('datePublished'),month),byline=x.get('author'),genre=x.get('@type'))
 preview=x.get('isAccessibleForFree') in (False,'false','False') or bool(soup.select('[data-testid="paywall"],.paywall,.article-paywall'))
 lic=x.get('license');licenses=[]
 if isinstance(lic,str):licenses.append(lic)
 root=soup.select_one('article')
 if root:
  licenses += [a.get('href') for a in root.find_all('a',href=True) if 'creativecommons.org/licenses/' in a['href']]
 answer['article_license_urls']=sorted(set(licenses))
 if any(re.search(r'creativecommons.org/licenses/by(?:-nc)?(?:-nd)?(?:-sa)?/[34]\.0',u) for u in licenses):answer['rights_status']='article_CC_observed; attribution/third_party_limits_apply'
 selected=soup.select(body_selector) if body_selector else []
 if len(selected)==1 and selected[0].find_parent('article') is not None:
  b=BeautifulSoup(str(selected[0]),'html.parser')
  for n in b.select('script,style,nav,aside,form,footer,.related-posts'):n.decompose()
  text=b.get_text('\n',strip=True)
  if text:answer['body_text']=text;answer['readability_status']='visible_body_boundary_pending'
 if preview:answer['readability_status']='preview_only'
 answer['JSONLD_body_present']=isinstance(x.get('articleBody'),str) and bool(x['articleBody'])
 # Neither body presence nor DOM container implies completeness. Certification is separate.
 return answer
