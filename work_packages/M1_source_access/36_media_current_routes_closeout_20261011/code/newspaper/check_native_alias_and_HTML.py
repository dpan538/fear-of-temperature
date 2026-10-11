"""Actual saved native publisher mapping checks; no HTTP or database writes."""
import sys,json,copy,types,importlib.machinery,importlib.util
import elt,berkeley_html,extract_load

def module(name,path):
 loader=importlib.machinery.SourceFileLoader(name,str(path));spec=importlib.util.spec_from_loader(name,loader);mod=importlib.util.module_from_spec(spec);loader.exec_module(mod);return mod

checks={};b=module('berkeley_alias_test',elt.OWN/'berkeley_alias_prepared.py.txt');original_profile=berkeley_html.profile();binding=dict(status='confirmed_same_publisher_native_web_alias',primary_evidence_receipts=['fd883c002b99ca27f5cc591e','caadf50e2f791628b7be1ffe','1eab3b6f9fd4ff251478b034'],basis='Same unique native20100 permalink identity,title,date,wholebody,publisher title and contact route on publisher apex/www; not bodyhash alone; all raw and URLs retained')
b.profile=lambda:dict(original_profile,verified_native_alias_binding=binding)
units=[]
for rid in binding['primary_evidence_receipts'][:2]:
 rec=elt._receipt(rid);raw=elt.read_payload(rec['raw_reference']);assert elt.sha(raw)==rec['raw_sha256'];one,_=b.parse_single(raw,rec['final_url'],original_profile['single_article_mapping']);units+=one
checks['apex_www_same_original_native_identity_date_and_wholebody']=all(units[0][k]==units[1][k] for k in ['article_id','native_article_id','publication_date','title','body','author','publisher_native_genre'])
checks['confirmed_alias_uses_inherited_same_native_charge_key']=b.native_key(units[0]['source_url'])==b.native_key(units[1]['source_url'])==elt.sha((b.SID+'|article|'+elt.canon(units[1]['source_url'])).encode())[:24]
checks['foreign_host_not_accepted']=not b.publisher_host_permitted('example.com')
st=copy.deepcopy(elt.state());metadata_receipts=['22fa60799f23b289a840cdc5','fd883c002b99ca27f5cc591e','caadf50e2f791628b7be1ffe','12a5411ff779410a2015838d']
for rid in metadata_receipts:
 rec=elt._receipt(rid);one,_=b.parse_single(elt.read_payload(rec['raw_reference']),rec['final_url'],original_profile['single_article_mapping']);u=one[0];key=b.native_key(u['source_url']);b.charge_saved_participant(st,key,rec,u);prior=st['native_http_hops'][key];assert not b.charge_saved_participant(st,key,rec,u) and st['native_http_hops'][key]==prior
seed=elt._receipt('1eab3b6f9fd4ff251478b034');articles,_=b.parse(elt.read_payload(seed['raw_reference']),seed['url'])
for u in articles:b.charge_saved_participant(st,b.native_key(u['source_url']),seed,u)
checks['actual_apex_carrier_native_units_mapped']=len(articles)==41 and all(u['native_permalink_day']==u['publication_date'] for u in articles)
checks['metadata_native_participants_and_alias_carrier_keep_four_hop_limit']=max(st['native_http_hops'].values())<=4
c=module('cambridge_html_test',elt.OWN/'cambridge_html.py.txt');p=dict(source_id='cambridge_news_nz',title='Cambridge News',country='NZ',stratum='NZ',edition='Original publisher community weekly web edition',source_frame='professional_community_weekly_newspaper',root_url='https://www.cambridgenews.nz/',retention_limit='Private authorized research only; publisher retains copyright',native_mapping_receipt='e0446b1e6fcbd88b3db3a2cd');extract_load.ADAPTERS[p['source_id']]=dict(title=p['title'],country=p['country'],stratum=p['stratum'],edition=p['edition'],frame=p['source_frame'],retention_limit=p['retention_limit'])
rec=elt._receipt(p['native_mapping_receipt']);raw=elt.read_payload(rec['raw_reference']);record,body,status=c.parse(raw,p['source_id'],rec['url']);checks['actual_eligible_2017_original_HTML_complete_ID_date_body_mapping']=bool(status=='confirmed_complete' and record['publication_date']=='2017-09-14' and body and record['source_native_article_id'] and record['publisher_native_genre'])
late=elt._receipt('75d297b0bda638735c3b2873');out,_,status=c.parse(elt.read_payload(late['raw_reference']),p['source_id'],late['url']);checks['fixed_cutoff_rejects_actual_2026_September24_record']=status=='pending_publication_date_outside_fixed_interval' and out['publication_date']=='2026-09-24'
xml=elt._receipt('414ab3e03bf8eca36cbc9d08');v=dict(stage='native_sitemap',xml_routes=[xml['url']],xml_consumed=[],queued_native_article_URLs=[]);queued=[];c.discover(p,v,lambda sid,items:queued.extend(items),lambda *args:xml,lambda *args:True,lambda *args:None)
checks['actual_advertised_1000_article_sitemap_reaches_queue']=len(queued)==1000 and all(x['representation']=='publisher_evidenced_wp_theme_HTML' and x['native_evidence']['publication_time_assignment'].endswith('publication date') for x in queued)
checks['native_sitemap_dates_not_used_as_publication_dates']=all('lastmod' not in x and x['month']==x['url'].split('/')[3]+'-'+x['url'].split('/')[4] for x in queued)
assert all(checks.values()),checks
result=dict(at_utc=elt.utc(),all_passed=True,checks=checks,no_HTTP=True,no_database_writes=True,own_named_new_raw_only=True,confirmed_Berkeley_native_alias_binding=binding,Cambridge_actual_article_record={k:v for k,v in record.items() if k!='body'},Berkeley_metadata_native_participants_charge_receipts=metadata_receipts)
elt.preparation_save('NATIVE_ALIAS_AND_HTML_CHANGED_CHAIN_CHECK.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['Cambridge_actual_article_record']}))
