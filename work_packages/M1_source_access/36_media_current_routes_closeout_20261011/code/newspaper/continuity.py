"""Reuse accepted compact source-era state without repeating predecessor audits."""
import json,collections
import elt,production,focused_repair

def prepare():
 focused_repair._month_overlay=json.loads((elt.OWN/'EXPECTED_MONTH_OVERLAY.json').read_text())['entries']
 focused_repair._ready=collections.defaultdict(list)
 for target in production.targets('green_left'):
  key=elt.canon(target['url']);entry=focused_repair._month_overlay.get(key)
  if entry:focused_repair._ready[entry['expected_month']].append(dict(target,month=entry['expected_month']))
 for row in json.loads((elt.OWN/'COMMITTED_GL_ALIAS_PRESERVATION.json').read_text()):production.KNOWN.update(elt.canon(u) for u in row['urls'])
 focused_repair._replay={};focused_repair._replay_done=set();focused_repair._last_dispatch={}
 elt.expected_article_month=focused_repair.expected_month;elt.named_saved_replay_allowed=focused_repair.replay_allowed
 elt.preparation_save('ACCEPTED_CONTINUITY_REUSE.json',dict(at_utc=elt.utc(),source='predecessor accepted named overlays, alias metadata and cursors',no_old_body_raw_or_SQL_scan=True,old_fix_checks_repeated=False,counters_not_reset=True))
