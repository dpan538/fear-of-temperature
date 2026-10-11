"""One conservative provider-state observation; never resets quota or old stops."""
import datetime as dt
import json
import time
import transport as t

HOST = 'api.stackexchange.com'

def observation_allowed(url, source_id, purpose, st, now=None):
    plan = t.read_json(t.WORK/'QUOTA_OBSERVATION_PLAN.json', {})
    now = now or dt.datetime.now(dt.timezone.utc)
    if not plan.get('enabled') or (t.WORK/'QUOTA_OBSERVATION_RESULT.json').exists(): return False
    if (url, source_id, purpose) != (plan.get('exact_readonly_endpoint'), plan.get('source_id'), 'quota_observation'): return False
    if plan.get('scope_sha256') != t.sha(t.SCOPE_PATH.read_bytes()): return False
    if now < dt.datetime.fromisoformat(plan['earliest_observation_at_utc']): return False
    old = t.REPO/plan['original_receipt']
    if not old.exists() or t.sha(old.read_bytes()) != plan['original_receipt_sha256']: return False
    receipt = t.read_json(old)
    if type(receipt.get('api_quota_remaining')) is not int or receipt['api_quota_remaining'] != 0 or receipt.get('api_error'): return False
    if st.get('blocked_hosts', {}).get(HOST) != {'reason': 'quota_exhausted'}: return False
    if plan.get('max_observations_this_scope') != 1: return False
    # The wait is conservative. Elapsed time itself never grants native access.
    return True

def native_access_confirmed(st):
    plan=t.read_json(t.WORK/'QUOTA_OBSERVATION_PLAN.json', {})
    if not plan.get('enabled'):return False
    grant = t.read_json(t.WORK/'QUOTA_PROVIDER_RENEWAL_EVIDENCE.json', {})
    if not grant.get('positive_provider_response') or grant.get('scope_sha256') != t.sha(t.SCOPE_PATH.read_bytes()): return False
    if st.get('blocked_hosts', {}).get(HOST) != {'reason': 'quota_exhausted'}: return False
    latest = st.get('latest_stackexchange_provider_state', {})
    if type(latest.get('quota_remaining')) is not int or latest['quota_remaining'] <= 0 or latest.get('api_error'): return False
    recpath = t.WORK/'receipts'/(grant['request_id']+'.json')
    if not recpath.exists() or t.sha(recpath.read_bytes()) != grant['receipt_sha256']: return False
    rec=t.read_json(recpath);plan=t.read_json(t.WORK/'QUOTA_OBSERVATION_PLAN.json', {})
    if rec.get('purpose')!='quota_observation' or rec.get('url')!=plan.get('exact_readonly_endpoint'): return False
    if rec.get('status')!='saved' or rec.get('http_status')!=200 or type(rec.get('api_quota_remaining')) is not int or rec['api_quota_remaining']<=0 or rec.get('api_error'): return False
    return True

def record_provider_state(st, rec):
    event = {'at_utc':t.utc(), 'request_id':rec['request_id'], 'quota_remaining':rec.get('api_quota_remaining'), 'api_error':rec.get('api_error'), 'api_backoff':rec.get('api_backoff')}
    st['latest_stackexchange_provider_state'] = event
    t.append(t.WORK/'QUOTA_PROVIDER_EVENTS.jsonl', event)

def run_if_due():
    plan = t.read_json(t.WORK/'QUOTA_OBSERVATION_PLAN.json', {})
    if not plan.get('enabled') or (t.WORK/'QUOTA_OBSERVATION_RESULT.json').exists(): return False
    if time.time() < plan.get('defer_until', 0): return False
    if not observation_allowed(plan['exact_readonly_endpoint'], plan['source_id'], 'quota_observation', t.state()): return False
    try:
        rec = t.fetch(plan['exact_readonly_endpoint'], plan['source_id'], 'quota_observation', cap=65536)
    except t.Stop as exc:
        why = str(exc)
        if why.startswith('server_backoff_until'):
            plan['defer_until'] = float(why.rsplit(' ',1)[1]);t.atomic(t.WORK/'QUOTA_OBSERVATION_PLAN.json', plan)
            return False
        if why == 'fixed_deadline': raise
        t.atomic(t.WORK/'QUOTA_OBSERVATION_RESULT.json', {'at_utc':t.utc(), 'status':'not_dispatched_or_preserved_attempt_stop', 'reason':why, 'historical_host_stop_retained':True})
        return False
    positive = rec.get('status') == 'saved' and rec.get('http_status') == 200 and type(rec.get('api_quota_remaining')) is int and rec['api_quota_remaining'] > 0 and not rec.get('api_error')
    result = {'at_utc':t.utc(), 'request_id':rec['request_id'], 'status':rec['status'], 'http_status':rec.get('http_status'), 'quota_remaining':rec.get('api_quota_remaining'), 'api_error':rec.get('api_error'), 'api_backoff':rec.get('api_backoff'), 'positive_provider_response':positive, 'provider_renewal_mechanism':'unverified; literal positive remaining quota only', 'old_exhaustion_receipt':plan['original_receipt'], 'old_exhaustion_receipt_sha256':plan['original_receipt_sha256'], 'historical_host_stop_retained':True, 'native_renewal_not_assumed_from_clock':True, 'new_key_account_identity_or_ip':False, 'counters_reset':False}
    t.atomic(t.WORK/'QUOTA_OBSERVATION_RESULT.json', result)
    if positive:
        t.atomic(t.WORK/'QUOTA_PROVIDER_RENEWAL_EVIDENCE.json', dict(result, scope_sha256=plan['scope_sha256'], receipt_sha256=t.sha((t.WORK/'receipts'/(rec['request_id']+'.json')).read_bytes())))
    return True
