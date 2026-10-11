"""Changed saved native carrier/frontier conservation checks, no HTTP/DB writes."""
import sys,json,copy,types,importlib.machinery,importlib.util,collections
import elt
checks={};path=elt.OWN/'berkeley_gap_carriers.py.txt'
loader=importlib.machinery.SourceFileLoader('berkeley_gap_checked',str(path));spec=importlib.util.spec_from_loader(loader.name,loader);b=importlib.util.module_from_spec(spec);loader.exec_module(b)
seeds=b.prepared_carriers();assert len(seeds)==5
st=copy.deepcopy(elt.state());counts=[];duplicate_units=[]
for seed in seeds:
 rec=seed['receipt'];raw=elt.read_payload(rec['raw_reference']);assert elt.sha(raw)==rec['raw_sha256'];units,soup=b.parse(raw,seed['carrier_url'])
 assert len(units)==len({u['native_article_id'] for u in units})
 assert all(u['publication_date']==u['native_permalink_day'] and u['body'] and u['title'] for u in units if u['status']=='confirmed_complete')
 for u in units:
  key=elt.sha((b.SID+'|article|'+elt.canon(u['source_url'])).encode())[:24];b.charge_saved_participant(st,key,rec,u)
  before=json.dumps(st,sort_keys=True);assert not b.charge_saved_participant(st,key,rec,u) and json.dumps(st,sort_keys=True)==before
 duplicate_units += [u for u in units if u.get('native_duplicate_carrier_occurrences',1)>1]
 counts.append((len(units),sum(u['status']=='confirmed_complete' for u in units)))
checks['actual_five_carriers_native_units']=counts==[(47,45),(38,36),(42,40),(92,92),(50,48)]
checks['all_native_participants_including_retained_have_safe_idempotent_hops']=max(st['native_http_hops'].values())<=4
checks['same_native_duplicate_occurrences_preserve_identity_and_raw_evidence']=sum(u['native_duplicate_carrier_occurrences']-1 for u in duplicate_units)==4 and all(all(e['same_ID_date_author_and_body'] and e['raw_occurrence_preserved'] for e in u['native_duplicate_carrier_evidence']) for u in duplicate_units)
# A conflicting repeat of the same native ID must remain pending rather than become a complete original.
seed=seeds[-1];raw=elt.read_payload(seed['receipt']['raw_reference']);units,soup=b.parse(raw,seed['carrier_url']);dups=collections.defaultdict(list)
for n in soup.select('#main #summary > div.story'):
 a=n.select_one('div.has_copy > h2 > a[href]')
 if a:dups[a['href']].append(n)
pair=next(nodes for nodes in dups.values() if len(nodes)>1);pair[-1].select_one('div.has_copy > .has_copy_copy.copy').append(' Conflicting native rendition fixture.')
conflicts,_=b.parse(str(soup).encode(),seed['carrier_url']);checks['conflicting_same_native_ID_is_typed_pending']=any(u['status']=='pending_conflicting_native_representations_in_carrier' for u in conflicts)
v=copy.deepcopy(b.state());before_units=copy.deepcopy(v['units']);contexts=[dict(stage='native_index',next_url='observed_A'),dict(stage='native_individual_body',next_url='observed_B',observed_native_article_targets=[{'native_article_id':'preserved'}])];v['frontier_queue']=copy.deepcopy(contexts);old={k:v.get(k) for k in b.CONTEXT_FIELDS};b.rotate_frontier(v)
checks['rotation_preserves_suspended_frontier_pending_targets_and_loaded_IDs']=v['next_url']=='observed_A' and v['units']==before_units and v['frontier_queue']==[contexts[1],old]
old_state=b.state;old_save=elt.save;old_append=elt.append;captured={};b.state=lambda:copy.deepcopy(v);elt.save=lambda n,x:captured.update(saved=copy.deepcopy(x));elt.append=lambda *args:None
try:b.activate_saved(seeds[0])
finally:b.state=old_state;elt.save=old_save;elt.append=old_append
checks['saved_carrier_activation_preserves_existing_contexts_and_committed_IDs']=captured['saved']['stage']=='saved_carrier' and captured['saved']['units']==before_units and len(captured['saved']['frontier_queue'])==3
# Check actual pending dispatcher text under the new adapter.
oldmodule=sys.modules.get('berkeley_html');sys.modules['berkeley_html']=b
loader=importlib.machinery.SourceFileLoader('run_gap_checked',str(elt.OWN/'run_gap_carriers.py.txt'));spec=importlib.util.spec_from_loader(loader.name,loader);run=importlib.util.module_from_spec(spec);loader.exec_module(run)
called=[];old=b.activate_saved;b.activate_saved=lambda seed:called.append(seed)
try:run.dispatch(types.SimpleNamespace(source_id=b.SID,opportunity_id='berkeley_carrier:actual'),{'berkeley_carrier:actual':seeds[0]})
finally:b.activate_saved=old;sys.modules['berkeley_html']=oldmodule
checks['actual_dispatch_activates_named_saved_carrier']=called==[seeds[0]]
assert all(checks.values()),checks
result=dict(at_utc=elt.utc(),checks=checks,all_passed=True,no_HTTP=True,no_database_writes=True,own_changed_carriers_only=True)
elt.preparation_save('BERKELEY_MULTI_CARRIER_CHANGED_CHAIN_CHECK.json',result);print(json.dumps(result))
