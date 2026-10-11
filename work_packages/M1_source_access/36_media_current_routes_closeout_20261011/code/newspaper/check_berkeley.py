"""Changed native newspaper chain checks; no HTTP or database writes."""
import json,collections,types
import elt,berkeley_html,run,broaden
checks={}
r=elt._receipt('cb46d1e7783160ce331859c7');raw=elt.read_payload(r['raw_reference']);units,soup=berkeley_html.parse(raw,r['url'])
checks['saved_native_raw_hash']=elt.sha(raw)==r['raw_sha256']
checks['seventy_distinct_native_ID_units']=len(units)==len({u['article_id'] for u in units})==70
checks['carrier_date_not_assigned_to_back_stories']=len({u['publication_date'] for u in units})==6 and next(u for u in units if u['native_article_id']=='531')['publication_date']=='2000-06-23'
checks['complete_originals_keep_all_copy_TEXT']=sum(u['status']=='confirmed_complete' for u in units)==52 and all(u['body'] and u['title'] and u['publication_date']==u['native_permalink_day'] for u in units if u['status']=='confirmed_complete')
checks['structural_pending_units_preserved']=len([u for u in units if u['status']!='confirmed_complete'])==18
st={};k='native-test';berkeley_html.charge_saved_participant(st,k,r,units[0]);before=json.dumps(st,sort_keys=True);again=berkeley_html.charge_saved_participant(st,k,r,units[0]);checks['saved_native_charge_idempotent']=not again and json.dumps(st,sort_keys=True)==before and st['native_http_hops'][k]==len(r['hops'])
try:berkeley_html.charge_saved_participant({'native_http_hops':{k:4}},k,r,units[0])
except ValueError:checks['inherited_four_hop_limit_enforced']=True
else:checks['inherited_four_hop_limit_enforced']=False
old=berkeley_html.perform;called=[];berkeley_html.perform=lambda:called.append(True)
try:run.dispatch(types.SimpleNamespace(source_id=berkeley_html.SID,opportunity_id='berkeley_native:body'),{})
finally:berkeley_html.perform=old
checks['actual_dispatch_reaches_native_adapter']=called==[True]
checks['future_body_requires_verified_single_mapping']="single_article_mapping_verified" in (elt.OWN/'berkeley_html.py').read_text()
cfg=dict(headline_selector='#main #content > .gutter > h2 > a',body_selector='#main #content > .gutter > div.copy',date_selector='#main #content > .gutter > .auth_date_box > div:not(.auth_box)',author_selector='#main #content > .gutter > .auth_date_box > .auth_box',body_boundary_evidence='Verified single native article531 exact main/gutter copy boundary')
single=elt._receipt('22fa60799f23b289a840cdc5');individual,_=berkeley_html.parse_single(elt.read_payload(single['raw_reference']),single['url'],cfg);full=next(u for u in units if u['native_article_id']=='531')
checks['single_native_wholebody_exact_carrier_match']=individual[0]['body']==full['body'] and individual[0]['publication_date']==full['publication_date'] and individual[0]['title']==full['title']
checks['HTML_comment_extraction_artifact_removed']='@article.copy.gsub' not in individual[0]['body']
allowed,reason=broaden.metadata_permission(dict(url='https://trove.nla.gov.au/newspaper/article/102039555',source_id='trove_canberra_times',stratum='AU'));checks['explicit_source_use_stop_has_no_request']=not allowed and reason['disposition_status']=='blocked_explicit_automated_access_requires_prior_written_consent'
assert all(checks.values()),checks
result=dict(at_utc=elt.utc(),checks=checks,all_passed=True,new_HTTP=False,database_writes=False,actual_saved_native_carrier=r['target_id'],source_scope='One own changed carrier only; no old full-corpus sweep')
elt.preparation_save('BERKELEY_CHANGED_CHAIN_CHECK.json',result)
p=json.loads((elt.OWN/'CHANGED_CHAIN_CHECK.json').read_text());p['berkeley_native_changed_chain']=result;p['all_passed']=p['all_passed'] and result['all_passed'];elt.preparation_save('CHANGED_CHAIN_CHECK.json',p)
print(json.dumps(result))
