"""Compact changed-tranche evidence; no sampling or stopping scores."""
import csv,json,datetime as dt
import transport as t,entities as e
COMMUNITIES={'straight_dope':'Straight Dope Message Board','tildes':'Tildes','ilxor':'ILX (ILE board subframe)','thesession':'The Session Discussions','foodtalkcentral':'Food Talk Central','openfoodnetwork':'Open Food Network Community','elektronauts':'Elektronauts','inaturalist_forum':'iNaturalist Community Forum','survivefrance':'Survive France','fic_forum':'FIC Forum','oscedays':'Open Source Circular Economy Days','cotech':'Cooperative Technologists Community','goatech':'GOATech Community','se_gardening':'Gardening & Landscaping','se_cooking':'Seasoned Advice','se_bicycles':'Bicycles','se_travel':'Travel','se_outdoors':'The Great Outdoors'}
def snapshot(fronts):
 scope=t.read_json(t.SCOPE_PATH);elapsed=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(scope['earliest_network_and_load_start_at_utc'])).total_seconds();due=[h for h in scope['ordinary_checkpoint_hours'] if elapsed>=h*3600 and not (t.WORK/f'HOUR_{h}_THREE_PRIORITY_EVIDENCE.json').exists()]
 if not due:return
 base=t.read_json(t.WORK/'INHERITED_BASELINE.json');prior=t.REPO/scope['predecessor_worker_reference'];before={};base_months=set()
 with (prior/'summaries/source_month_calendar.csv').open() as f:
  for r in csv.DictReader(f):
   count=int(r['usable_dated_independent_bodies']);before[r['source_id'],r['month']]=count
   if count:base_months.add(r['month'])
 with t.shared(t.footprint()):
  c=e.db();delta=c.execute('SELECT source_id,SUBSTR(native_created_at,1,7),COUNT(*) FROM posts WHERE rowid>? GROUP BY source_id,SUBSTR(native_created_at,1,7)',(base['counts']['posts'],)).fetchall();c.close()
 st=t.state();binding=t.read_json(t.WORK/'PREDECESSOR_BINDING_RECEIPT.json');gains=[{'source':sid,'month':month,'new_core_bodies':n,'first_observed_for_source_in_accepted_store':before.get((sid,month),0)==0} for sid,month,n in delta];months=base_months|{m for _,m,n in delta if n};communities={}
 for sid,month,n in delta:
  if sid in COMMUNITIES:communities.setdefault(sid,{'name':COMMUNITIES[sid],'new_dated_core_bodies':0,'observed_new_months':set()});communities[sid]['new_dated_core_bodies']+=n;communities[sid]['observed_new_months'].add(month)
 for x in communities.values():x['observed_new_months']=sorted(x['observed_new_months'])
 result={'at_utc':t.utc(),'fixed_deadline':scope['hard_deadline_at_utc'],'elapsed_seconds':elapsed,'legacy_state_priority':{'named_reconciliations':binding['changes'],'overlay_sha256':t.sha((t.WORK/'NATIVE_RECONCILIATION_OVERLAY.jsonl').read_bytes()),'fixture':t.read_json(t.WORK/'FOCUSED_CONTINUATION_REGRESSION.json'),'real_new_core_bodies':st['new_core_bodies'],'seen_root_is_not_complete_thread':True},'month_priority':{'baseline_observed_months':len(base_months),'current_observed_months':len(months),'new_pooled_months':sorted(months-base_months),'remaining_full_calendar_unobserved_months':465-len(months),'source_month_deltas':gains,'pre_foundation_not_zero_expression':True},'breadth_priority':{'actual_contributing_named_community_frames':communities,'platform_instances_software_and_crosslists_not_counted_as_communities':True,'new_candidates_do_not_count_as_contributions':True,'development_goal_is_not_a_finish_gate':True},'source_year_deltas':st.get('source_year_deltas',{}),'lifetime_requests':st['requests'],'round_requests':st['requests']-base['lifetime_charged_requests'],'last_http':st.get('last_successful_http_at_utc'),'last_load':st.get('last_successful_load_at_utc'),'actual_capacity':t.read_json(t.WORK/'LAST_CAPACITY.json'),'live_cursors':[{k:f.get(k) for k in ['source','frame','kind','status','native_next_url','page','before','cursor','oldest_returned_publication_at']} for f in fronts if f['status']=='active'],'context_risk':'compact on-disk digest and owner handoff preserved; no deadline extension','semantic_labels':False}
 for h in due:t.atomic(t.WORK/f'HOUR_{h}_THREE_PRIORITY_EVIDENCE.json',result)
 t.atomic(t.WORK/'LATEST_THREE_PRIORITY_EVIDENCE.json',result)
