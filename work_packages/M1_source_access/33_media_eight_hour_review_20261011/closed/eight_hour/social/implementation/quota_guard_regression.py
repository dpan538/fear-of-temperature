"""Synthetic provider-guard cases only; no HTTP, database or native Load."""
import copy
import datetime as dt
from pathlib import Path
import tempfile
import transport as t
import quota_observation as quota

def main():
    previous=t.read_json(t.WORK/'QUOTA_OBSERVATION_GUARD_REGRESSION.json', {})
    previous_sha=t.sha((t.WORK/'QUOTA_OBSERVATION_GUARD_REGRESSION.json').read_bytes()) if previous else None
    original=(t.WORK,t.REPO,t.SCOPE_PATH);checks=[]
    def check(name,value):
        assert value,name
        checks.append(name)
    try:
        with tempfile.TemporaryDirectory(prefix='quota_guard_fixture_',dir=t.WORK) as temp:
            root=Path(temp);t.WORK=root;t.REPO=root;t.SCOPE_PATH=root/'scope.json';t.atomic(t.SCOPE_PATH,{'fixture_only':True})
            old=root/'old_receipt.json';t.atomic(old,{'api_quota_remaining':0,'api_error':None})
            plan={'enabled':True,'exact_readonly_endpoint':'https://api.stackexchange.com/2.3/info?site=sustainability','source_id':'se_sustainability','scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'earliest_observation_at_utc':'2026-10-10T15:05:56+00:00','original_receipt':'old_receipt.json','original_receipt_sha256':t.sha(old.read_bytes()),'max_observations_this_scope':1}
            t.atomic(root/'QUOTA_OBSERVATION_PLAN.json',plan)
            state={'blocked_hosts':{quota.HOST:{'reason':'quota_exhausted'}}};now=dt.datetime(2026,10,10,16,tzinfo=dt.timezone.utc)
            args=(plan['exact_readonly_endpoint'],'se_sustainability','quota_observation',state)
            check('exact_one_metadata_observation_after_wait',quota.observation_allowed(*args,now=now))
            check('before_wait_rejected',not quota.observation_allowed(*args,now=dt.datetime(2026,10,10,14,tzinfo=dt.timezone.utc)))
            check('body_purpose_rejected',not quota.observation_allowed(args[0],args[1],'content',state,now))
            check('other_endpoint_rejected',not quota.observation_allowed('https://api.stackexchange.com/2.3/questions?site=cooking',args[1],args[2],state,now))
            check('credential_parameter_rejected',not quota.observation_allowed(args[0]+'&key=fixture',args[1],args[2],state,now))
            check('other_source_rejected',not quota.observation_allowed(args[0],'se_cooking',args[2],state,now))
            denied=copy.deepcopy(state);denied['blocked_hosts'][quota.HOST]={'http_status':403}
            check('actual403_not_reopened',not quota.observation_allowed(args[0],args[1],args[2],denied,now))
            for name,update in [('disabled_preparation',{'enabled':False}),('different_release',{'scope_sha256':'different'}),('more_than_one_observation',{'max_observations_this_scope':2})]:
                t.atomic(root/'QUOTA_OBSERVATION_PLAN.json',dict(plan,**update));check(name+'_rejected',not quota.observation_allowed(*args,now=now))
            t.atomic(root/'QUOTA_OBSERVATION_PLAN.json',plan)
            t.atomic(root/'QUOTA_OBSERVATION_RESULT.json',{'fixture':True});check('second_observation_rejected',not quota.observation_allowed(*args,now=now));(root/'QUOTA_OBSERVATION_RESULT.json').unlink()
            t.atomic(old,{'api_quota_remaining':1});check('changed_origin_digest_rejected',not quota.observation_allowed(*args,now=now))
            rec={'request_id':'fixture_positive','status':'saved','http_status':200,'api_quota_remaining':50,'purpose':'quota_observation','url':plan['exact_readonly_endpoint']};rp=root/'receipts/fixture_positive.json';t.atomic(rp,rec)
            grant={'positive_provider_response':True,'scope_sha256':t.sha(t.SCOPE_PATH.read_bytes()),'request_id':'fixture_positive','receipt_sha256':t.sha(rp.read_bytes())};t.atomic(root/'QUOTA_PROVIDER_RENEWAL_EVIDENCE.json',grant)
            state['latest_stackexchange_provider_state']={'quota_remaining':50,'api_error':None}
            check('positive_provider_evidence_permits_forward_access',quota.native_access_confirmed(state))
            for name,update in [('new_quota_zero',{'quota_remaining':0}),('quota_boolean',{'quota_remaining':True}),('new_provider_error',{'api_error':{'error_id':502}})]:
                original_latest=state['latest_stackexchange_provider_state'];state['latest_stackexchange_provider_state']=dict(original_latest,**update);check(name+'_revokes_access',not quota.native_access_confirmed(state));state['latest_stackexchange_provider_state']=original_latest
            for status in [403,429,451]:
                state['blocked_hosts'][quota.HOST]={'http_status':status};check('http'+str(status)+'_revokes_access',not quota.native_access_confirmed(state))
            state['blocked_hosts'][quota.HOST]={'reason':'quota_exhausted'}
            for name,update in [('other_purpose',{'purpose':'content'}),('other_provider_endpoint',{'url':'https://api.stackexchange.com/2.3/questions'}),('saved_zero_quota',{'api_quota_remaining':0}),('saved_http403',{'http_status':403}),('saved_api_error',{'api_error':{'error_id':502}})]:
                t.atomic(rp,dict(rec,**update));t.atomic(root/'QUOTA_PROVIDER_RENEWAL_EVIDENCE.json',dict(grant,receipt_sha256=t.sha(rp.read_bytes())));check(name+'_cannot_grant_access',not quota.native_access_confirmed(state))
    finally:t.WORK,t.REPO,t.SCOPE_PATH=original
    if previous and not (t.WORK/'QUOTA_OBSERVATION_GUARD_INITIAL_REGRESSION.json').exists():t.atomic(t.WORK/'QUOTA_OBSERVATION_GUARD_INITIAL_REGRESSION.json',previous)
    t.atomic(t.WORK/'QUOTA_OBSERVATION_GUARD_REGRESSION.json',{'at_utc':t.utc(),'passed':True,'checks':checks,'previous_regression_sha256':previous_sha,'fixture_only_no_network_or_native_Load':True,'same_release_deadline_transport_checks_retained':True,'provider_observation_not_installed_in_running_process':True})
    print({'passed':True,'checks':len(checks),'HTTP_or_native_Load':False})

if __name__=='__main__':main()
