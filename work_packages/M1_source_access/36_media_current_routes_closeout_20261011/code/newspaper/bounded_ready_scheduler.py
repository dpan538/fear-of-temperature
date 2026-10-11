"""Fair ready work after each bounded operation; no time/count/source quota."""
def choose(options):
 ready=[o for o in options if o.remaining_work and not o.blocked]
 for o in ready:
  assert o.evidence_ref and o.wait_rounds>=0 and o.action_kind in {'acquisition','route_resolution'}
 # Unbounded operational wait debt prevents permanent priority starvation.
 # At equal need and wait debt, readable body work precedes route resolution.
 return min(ready,key=lambda o:(o.need_priority-o.wait_rounds,o.action_kind!='acquisition',o.opportunity_id)) if ready else None
