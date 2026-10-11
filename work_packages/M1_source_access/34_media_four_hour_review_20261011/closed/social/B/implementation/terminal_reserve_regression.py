"""Exercise real terminal/verify guarded reserve path, without corpus reads."""
import json
import transport as t,delta_closeout

def main():
    original=t.preflight;oldflag=t.TERMINAL_OPERATION
    model=t.read_json(t.WORK/'ACQUISITION_TAIL_ACCOUNTING.json');st=t.state();base=t.read_json(t.WORK/'INHERITED_BASELINE.json')
    expected=max(t.footprint(),model['bounded_metadata_journal_bytes'])+max(0,st['new_entity_versions']-model['already_annotated_changed_versions'])*2582+st['new_entity_versions']*(901+901)+st['new_entities']*(75+75)+model['delta_export_fixed_allowance_bytes']+(st['requests']-base['lifetime_charged_requests'])*1024+model['accepted_phase_A_future_publication_upper_bytes']
    try:
        delta_closeout.terminal_reservations()
        with t.writer():
            with t.shared(t.footprint()) as actual:
                assert actual['pending_bytes']==expected and actual['complete_pending_bytes']==expected
                assert actual['terminal_reserve_components']['accepted_phase_A_future_publication_upper_bytes']==2*1048576
                assert actual['terminal_reserve_components']['B_fixed_output_upper_bytes']==8*1048576
                assert actual['terminal_reserve_components']['journal_operation_floor_bytes']==64*1048576
                assert actual['terminal_tail']['bytes']==0
        proof={'at_utc':t.utc(),'passed':True,'actual_terminal_guarded_preflight':actual,'expected_operation_bytes':expected,'omitting_A_future_copy_would_underreserve_bytes':2*1048576,'verify_uses_identical_delta_closeout_terminal_reservations':True,'terminal_code_sha256':t.sha((t.WORK/'delta_closeout.py').read_bytes()),'native_fixed_margin_bytes':32*1048576,'source_requests':0,'database_access':False,'deadline':t.release()['hard_deadline_at_utc']}
        t.atomic(t.WORK/'TERMINAL_RESERVE_REGRESSION.json',proof)
    finally:t.preflight=original;t.TERMINAL_OPERATION=oldflag
    print(json.dumps({'passed':True,'expected_operation_bytes':expected,'A_copy_reserved_bytes':2*1048576,'B_fixed_reserved_bytes':8*1048576}))

if __name__=='__main__':main()
