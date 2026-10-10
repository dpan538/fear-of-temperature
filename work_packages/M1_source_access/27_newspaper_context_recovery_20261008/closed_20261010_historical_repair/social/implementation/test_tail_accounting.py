"""Complete-operation sizing regression with synthetic metadata, no corpus I/O."""
import json,tempfile
from pathlib import Path
from unittest.mock import patch
import transport as t
checks=[];original=t.WORK
with tempfile.TemporaryDirectory(dir=original) as d:
 w=Path(d)
 with patch.object(t,'WORK',w):
  t.atomic(w/'ACQUISITION_TAIL_ACCOUNTING.json',{'enabled':True,'already_annotated_changed_versions':200,'metadata_bytes_per_changed_version_upper_estimate':2582,'inherited_native_entities':268343,'accepted_predecessor_export_bytes':105070246})
  st={'new_entity_versions':134466,'new_entities':134415,'requests':7000,'returned_object_count':402801}
  t.atomic(w/'STATE.json',st)
  tail=t.acquisition_tail({});assert tail['bytes']==796293963
  checks.append('measured_metadata_and_export_footprints_reserved_together')
  st['new_entity_versions']+=1000;t.atomic(w/'STATE.json',st);assert t.acquisition_tail({})['bytes']>tail['bytes']
  assert t.read_json(w/'STATE.json')['requests']==7000
  checks.append('native_metadata_growth_updates_footprint_without_count_gate_or_counter_reset')
  scope={'lease_coordination_reference':'fixture','owner_pending_lease_bytes':8388608,'prior_media_bytes':0,'media_lifetime_accounting_roots':[],'physical_floor_bytes':16106127360,'recovery_allowance_bytes':50331648,'media_lifetime_cap_bytes':30000000000,'social_incremental_allocation_bytes':8000000000}
  read=t.read_json
  def fixture_read(p,default=None):
   if str(p).endswith('fixture'):return {'active_leases':[{'active':True,'thread_id':t.OWNER,'reserved_bytes':8388608}]}
   return read(p,default)
  with patch.object(t,'read_json',fixture_read),patch.object(t,'bytes_under',return_value=7300000000),patch.object(t.shutil,'disk_usage',return_value=type('Usage',(),{'free':60000000000})()):
   try:t.preflight(scope,16777216)
   except t.Stop as exc:assert str(exc).startswith('resource_stop') and 'terminal_tail' in str(exc)
   else:raise AssertionError('required terminal footprint omitted')
   checks.append('genuine_complete_operation_capacity_failure_precedes_new_request')
   with patch.object(t,'TERMINAL_OPERATION',True):
    b=t.preflight(scope,16777216);assert b['terminal_tail']['bytes']==0 and b['social_headroom']>0
   checks.append('terminal_can_consume_reserved_bytes_without_allocation_expansion')
  assert t.read_json(w/'STATE.json')['returned_object_count']==402801
  checks.append('charged_keys_and_native_identity_counters_preserved')
t.atomic(original/'TAIL_ACCOUNTING_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'checks':checks,'source_requests':0,'corpus_writes':0})
print(json.dumps({'passed':True,'checks':len(checks)}))
