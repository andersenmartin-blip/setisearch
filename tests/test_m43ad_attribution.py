from types import SimpleNamespace
import copy
import numpy as np
import pytest
from seti_repeater.attribution_m43ad import attribute_peak, aligned_profile, attributed_signatures, apply_controls, POLICIES
from seti_repeater.receiver_v0p6 import _predicted_midpoint_hz


def signature(hz, peak, score, epoch=0):
    pred = hz/1e6; freq = peak/1e6
    return dict(epoch_zero_based=epoch, predicted_mid_mhz=pred, peak_frequency_mhz=freq,
                peak_snr=score, offset_from_prediction_hz=(freq-pred)*1e6)


def test_same_displaced_peak_is_unrelated_for_narrow_but_retained_for_broad():
    factors = np.ones(4); hz = 1e9
    old = signature(hz, hz+30, 40.); center = signature(hz, hz, 6.)
    untouched = copy.deepcopy((old, center))
    narrow, ev = attribute_peak(old, center, hz, factors, 1, 3.)
    broad, bev = attribute_peak(old, center, hz, factors, 129, 3.)
    assert narrow == center and ev['selected_measurement'] == 'centered'
    assert broad == old and bev['selected_measurement'] == 'local_peak'
    assert (old, center) == untouched


def test_full_track_and_closed_envelope_boundary_control_attribution():
    hz = 1000.; factors = np.array([.99, 1.01])
    mid = _predicted_midpoint_hz(hz, factors)
    center = signature(mid, mid, 7.)
    # A peak far from the midpoint is allowed when the actual track reaches it.
    old = signature(mid, 1010., 20.)
    assert attribute_peak(old, center, hz, factors, 1, 2.)[0] == old
    edge = signature(1e6, 1e6, 12.)
    edge['peak_frequency_mhz'] = 1.000001
    edge['offset_from_prediction_hz'] = (edge['peak_frequency_mhz']-1.)*1e6
    # Test inclusion using a representable peak, then a strictly smaller padding.
    spacing = 2*edge['offset_from_prediction_hz']
    c = signature(1e6, 1e6, 6.)
    assert attribute_peak(edge, c, 1e6, np.ones(2), 1, spacing)[0] == edge
    assert attribute_peak(edge, c, 1e6, np.ones(2), 1, spacing*.99)[0] == c


def test_alignment_is_fixed_by_geometry_and_handles_fractional_channels():
    n = 101; hz = 1000.+np.arange(n)
    g = SimpleNamespace(score_bin_count=61, support_bin_count=n, score_slice=slice(20,81),
                        support_hz=hz, score_hz=hz[20:81], channel_width_hz=1.)
    on_f = np.array([1.]); off_f = np.array([1./1.0025])
    # A linear profile permits an analytic interpolation oracle at every point.
    on = (2*hz+7).astype('<f4'); off = (2*hz*off_f[0]+7).astype('<f4')
    out = aligned_profile(on, off, g, 30, 9, on_f, off_f)
    assert out['complete'] and out['correlation'] > .999999
    assert np.max(np.abs(np.array(out['aligned_off_values'])-out['on_values'])) < .001
    shifted = aligned_profile(on, off, g, 30, 9, on_f, on_f)
    assert out['off_positions'] != shifted['off_positions']
    # Scores cannot alter the frequency transform.
    changed = aligned_profile(on[::-1].copy(), off, g, 30, 9, on_f, off_f)
    assert changed['off_positions'] == out['off_positions']


def test_constant_profiles_and_missing_support_are_explicit():
    g = SimpleNamespace(score_bin_count=21, support_bin_count=41, score_slice=slice(10,31),
        support_hz=1000.+np.arange(41), score_hz=1010.+np.arange(21), channel_width_hz=1.)
    a = np.ones(41, dtype='<f4')
    out = aligned_profile(a, a, g, 10, 3, np.ones(2), np.ones(2))
    assert out['complete'] and out['correlation'] is None
    assert not aligned_profile(a,a,g,10,3,np.ones(2),np.full(2,.5))['complete']
    with pytest.raises(ValueError):
        aligned_profile(a.astype(float),a,g,10,3,np.ones(2),np.ones(2))
    with pytest.raises(ValueError):
        attributed_signatures([], {'extra': []}, {}, [], g)


def test_integrated_controls_preserve_prior_veto_and_report_missing_evidence():
    n = 101; hz = 1000.+np.arange(n)
    g = SimpleNamespace(score_bin_count=61, support_bin_count=n, score_slice=slice(20,81),
                        support_hz=hz, score_hz=hz[20:81], channel_width_hz=1.)
    profile = (10*np.exp(-((np.arange(n)-50)/8)**2)).astype('<f4')
    values = np.stack([profile]*3)
    class Store:
        expected_ids = {('on',0,9): 'on', ('off',0,9): 'off'}
        def get(self, kind, t, w): return values, kind
    member = dict(record_id='x', template_index=0, proxy_carrier_index=30,
        spectral_width_channels=9, active_epochs_zero_based=[0,1],
        epoch_values_at_proxy_carrier=[10.,10.,10.], passes_evaluated_physical_vetoes=True,
        meets_diagnostic_rank_cut=True, physical_disposition='pending_receiver_alias_evaluation')
    audit = dict(members=[member]); factors = [np.ones((1,2))]*3
    out, ev = apply_controls(audit, Store(), g, factors, factors)
    assert out[POLICIES[0]]['final_diagnostic_survivors'] == 1
    assert out[POLICIES[1]]['final_diagnostic_survivors'] == 0
    assert out[POLICIES[2]]['final_diagnostic_survivors'] == 0
    assert ev[0]['aligned_complete'] and ev[0]['aligned_vetoed']
    missing, ev = apply_controls(audit, Store(), g, factors, [np.full((1,2),.5)]*3)
    assert not ev[0]['aligned_complete']
    assert 'incomplete_aligned_OFF_evidence' in missing[POLICIES[2]]['members'][0]['m43ad_rejections']
    assert missing[POLICIES[2]]['final_diagnostic_survivors'] == 0
    member['passes_evaluated_physical_vetoes'] = False
    member['physical_disposition'] = 'prior_veto'
    out, ev = apply_controls(audit, Store(), g, factors, factors)
    assert all(a['members'][0]['physical_disposition'] == 'prior_veto' for a in out.values())
    assert all(not r['queried'] for r in ev[0]['aligned'])
