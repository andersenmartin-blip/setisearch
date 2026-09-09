"""Check diagnostic witness accounting without altering the detector."""
from m43ac_dual_evidence import witness_trace


def fixture(epochs):
    return dict(original_alias=dict(records=[dict(record_id='left', receiver_alias_evidence=dict(
        best_receiver_alias_witness=dict(record_id='right', matched_active_epochs=[
            dict(epoch_zero_based=0), dict(epoch_zero_based=1)])))]), centered_signatures={
                side: [dict(epoch_zero_based=e, peak_snr=snr, peak_frequency_mhz=freq)
                       for e, snr, freq in values] for side, values in epochs.items()})


def test_floor_loss_has_precedence_over_simultaneous_separation():
    rec = fixture(dict(left=[(0, 5.5, 1.), (1, 5.499, 1.)],
                       right=[(0, 6., 1.), (1, 6., 1.0001)]))
    result = witness_trace(rec, 'left')
    assert result['cause'] == 'fewer_than_two_shared_centered_epochs_above_floor'
    assert result['epochs'][0]['centered_pair_matches']
    assert not result['epochs'][1]['both_centered_above_floor']


def test_previously_unmatched_shared_epoch_can_restore_a_witness():
    rec = fixture(dict(left=[(0, 6., 1.), (1, 4., 1.), (2, 6., 1.)],
                       right=[(0, 6., 1.), (1, 4., 1.), (2, 6., 1.)]))
    result = witness_trace(rec, 'left')
    assert result['cause'] == 'old_witness_still_matches'
    assert [r['epoch'] for r in result['epochs']] == [0, 1, 2]
    assert result['epochs'][2]['old_match'] is None


def test_qualified_epochs_can_fail_frequency_agreement():
    rec = fixture(dict(left=[(0, 6., 1.), (1, 6., 1.)],
                       right=[(0, 6., 1.), (1, 6., 1.0001)]))
    assert witness_trace(rec, 'left')['cause'] == 'centered_peak_separation'
