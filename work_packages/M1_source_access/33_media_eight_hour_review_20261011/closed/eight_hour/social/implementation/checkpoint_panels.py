"""Supplement checkpoint metadata with matched era/genre panels; never control acquisition."""
import csv,collections,json
import transport as t
from focused_progress import COMMUNITIES

def create(hour):
 p=t.WORK/f'HOUR_{hour}_THREE_PRIORITY_EVIDENCE.json';out=t.WORK/f'HOUR_{hour}_SOURCE_GENRE_PANEL.json'
 if not p.exists() or out.exists():return
 point=t.read_json(p);scope=t.read_json(t.SCOPE_PATH);before=collections.Counter();delta=collections.Counter()
 with (t.REPO/scope['predecessor_worker_reference']/'summaries/source_month_calendar.csv').open() as f:
  for r in csv.DictReader(f):before[r['source_id'],r['month']]=int(r['usable_dated_independent_bodies'])
 for r in point['month_priority']['source_month_deltas']:delta[r['source'],r['month']]=r['new_core_bodies']
 registry={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')};prior_sids={sid for (sid,m),n in before.items() if n}
 from source_frame_reporting import genre as frame_genre,METHOD
 def genre(sid):return frame_genre(sid,registry)
 rows=[]
 for year in range(2016,2027):
  for sid in sorted(prior_sids|{sid for sid,m in delta}):
   old=sum(before[sid,f'{year}-{m:02}'] for m in range(1,9));added=sum(delta[sid,f'{year}-{m:02}'] for m in range(1,9))
   rows.append({'year':year,'source':sid,'genre_from_source_frame':genre(sid),'accepted_Jan_Aug_before':old,'new_Jan_Aug':added,'current_Jan_Aug':old+added,'baseline_contributing_source_panel':sid in prior_sids})
 actual_new=[{'source':sid,'community':COMMUNITIES[sid],'new_dated_core_bodies':sum(n for (name,m),n in delta.items() if name==sid)} for sid in [sid for sid,x in registry.items() if x.get('named_community_frame') or sid in ('oscedays','fic_forum')] if sid in COMMUNITIES and any(name==sid and n for (name,m),n in delta.items())]
 fronts=t.read_json(t.WORK/'FRONTIERS.json');remaining=[{'source':f['source'],'frame':f['frame'],'state':f['status'],'pending_topics':len(f.get('topics',[])),'pending_post_IDs':sum(len(q['ids']) for q in f.get('chunks',[])),'current_unavailable_posts':len(f.get('unavailable_native_post_ids',[])),'reason':f.get('stop')} for f in fronts if f.get('historical_route') or f.get('ordinary_public_community_need')]
 t.atomic(out,{'at_utc':t.utc(),'checkpoint_sha256':t.sha(p.read_bytes()),'matched_period':'January-August2016-2026','genre_reporting_method':METHOD,'rows':rows,'actual_new_community_frames':actual_new,'remaining_named_frontiers':remaining,'full_calendar_unobserved_months':point['month_priority']['remaining_full_calendar_unobserved_months'],'source_applicable_denominators_not_inferred_from_first_record':True,'same_month_new_surplus_examples':[r for r in point['month_priority']['source_month_deltas'] if r['new_core_bodies']>2][:12],'code_fixture_and_real_Load_evidence_separate':True,'greater_than20_development_goal_remains_open_not_a_finish_gate':True,'provider_access_and_rights_limits':t.read_json(t.WORK/'SOURCE_EXPANSION_LIMITS.json'),'genre_source_counts_and_shares_are_reporting_only':True,'no_healthy_frame_or_complete_archive_claim':True})

def enrich(hour):
 p=t.WORK/f'HOUR_{hour}_THREE_PRIORITY_EVIDENCE.json'
 if not p.exists():return
 point=t.read_json(p);reg={x['source_id']:x for x in t.read_json(t.WORK/'source_registry.json')};names=dict(COMMUNITIES);names.update({sid:x['title'] for sid,x in reg.items() if x.get('named_community_frame')})
 actual={}
 for r in point['month_priority']['source_month_deltas']:
  sid=r['source']
  if sid in names:
   a=actual.setdefault(sid,{'name':names[sid],'new_dated_core_bodies':0,'observed_new_months':[]});a['new_dated_core_bodies']+=r['new_core_bodies'];a['observed_new_months'].append(r['month'])
 original=t.WORK/f'HOUR_{hour}_INITIAL_NATIVE_CHECKPOINT.json'
 if not original.exists():original.write_bytes(p.read_bytes())
 point['breadth_priority']['actual_contributing_named_community_frames']=actual;point['source_name_map_amendment']={'at_utc':t.utc(),'initial_snapshot_sha256':t.sha(original.read_bytes()),'counts_and_dates_reused_from_original_source_month_delta':True,'approved_source_names_refreshed_without_corpus_read':True}
 t.atomic(p,point);t.atomic(t.WORK/'LATEST_THREE_PRIORITY_EVIDENCE.json',point)
 create(hour)
