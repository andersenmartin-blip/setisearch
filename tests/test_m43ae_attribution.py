from types import SimpleNamespace
import copy
import numpy as np
import pytest
from seti_repeater.attribution_m43ae import response_profile, apply_controls, evidence_complete, POLICIES


def fixture():
    n = 301; hz = 1000.+np.arange(n)
    grid = SimpleNamespace(score_bin_count=201, support_bin_count=n,
        score_slice=slice(50,251), support_hz=hz, score_hz=hz[50:251], channel_width_hz=1.)
    profile = np.exp(-((np.arange(n)-150)/8)**2).astype('<f4')
    return grid, profile


@pytest.mark.parametrize('hypothesis', ['receiver_mean', 'candidate_track'])
def test_distant_high_maximum_cannot_supply_center_amplitude(hypothesis):
    g, shape = fixture(); on = 10*shape; off = 3*shape; off[160] = 100.
    p = response_profile(on, off, g, 100, 3, np.ones(2), np.ones(2), hypothesis)
    assert p['correlation'] > .999999 and max(off) == 100.
    assert p['off_center_score'] == 3. and not p['vetoed']


@pytest.mark.parametrize('on_amp,off_amp,expected', [(5.5,5.5,True),(5.499,6.,False),(6.,5.499,False)])
def test_both_amplitudes_at_the_center_use_the_inclusive_unchanged_floor(on_amp, off_amp, expected):
    g, shape = fixture()
    p = response_profile(on_amp*shape, off_amp*shape, g, 100, 9, np.ones(2), np.ones(2), 'candidate_track')
    assert p['vetoed'] is expected


def test_fixed_receiver_and_candidate_track_are_different_hypotheses():
    g, shape = fixture(); off = np.roll(10*shape, 40)
    factors = np.array([1150./1190.])
    stationary = response_profile(10*shape, off, g, 100, 9, np.ones(1), factors, 'receiver_mean')
    moving = response_profile(10*shape, off, g, 100, 9, np.ones(1), factors, 'candidate_track')
    assert stationary['vetoed'] and abs(stationary['center_shift_bins']-40.) < 1e-9
    assert not moving['vetoed'] and moving['center_shift_bins'] == 0.
    altered = response_profile(np.roll(10*shape, 1), off, g, 100, 9, np.ones(1), factors, 'receiver_mean')
    assert altered['off_positions'] == stationary['off_positions']


def test_constant_and_incomplete_profiles_are_explicit():
    g, shape = fixture(); constant = np.full(301, 10., dtype='<f4')
    p = response_profile(constant, constant, g, 100, 9, np.ones(2), np.ones(2), 'candidate_track')
    assert p['correlation'] is None and not p['vetoed']
    p = response_profile(10*shape, 10*shape, g, 100, 9, np.ones(2), np.full(2,.5), 'receiver_mean')
    assert not p['complete'] and not p['vetoed']
    with pytest.raises(ValueError):
        response_profile(constant.astype(float),constant,g,100,9,np.ones(2),np.ones(2),'candidate_track')


def test_fractional_receiver_center_is_the_interpolated_shape_center():
    g, shape = fixture(); on = (np.arange(301)+10).astype('<f4'); off = on.copy()
    p = response_profile(on, off, g, 100, 9, np.ones(1), np.array([1150./1190.5]), 'receiver_mean')
    assert abs(p['off_positions'][9]-190.5) < 1e-9
    assert abs(p['off_center_score']-200.5) < 1e-9
    assert p['off_center_score'] == p['aligned_off_values'][9]


def test_policy_specific_incompleteness_and_prior_veto_precedence():
    g, shape = fixture(); on = np.stack([10*shape]*3); off = np.zeros_like(on)
    class Store:
        expected_ids = {('on',0,9):'on', ('off',0,9):'off'}
        def get(self, kind, t, w): return (on if kind == 'on' else off), kind
    m = dict(record_id='x', template_index=0, proxy_carrier_index=100, spectral_width_channels=9,
        active_epochs_zero_based=[0,1], epoch_values_at_proxy_carrier=[10.,10.,10.],
        passes_evaluated_physical_vetoes=True, meets_diagnostic_rank_cut=True,
        physical_disposition='pending_receiver_alias_evaluation')
    audit = {'members':[m]}; original = copy.deepcopy(audit); factors = [np.ones((1,2))]*3
    out, ev, profiles = apply_controls(audit, Store(), g, factors, [np.full((1,2),.5)]*3)
    assert [out[p]['final_diagnostic_survivors'] for p in POLICIES] == [0,1,0]
    assert [evidence_complete(ev,p) for p in POLICIES] == [False,True,False]
    assert audit == original and len(profiles) == 4
    m.update(passes_evaluated_physical_vetoes=False, physical_disposition='prior_veto')
    out, ev, profiles = apply_controls(audit, Store(), g, factors, factors)
    assert not profiles and all(a['members'][0]['physical_disposition'] == 'prior_veto' for a in out.values())


def test_union_rejects_if_either_hypothesis_has_a_co_located_response():
    g, shape = fixture(); on = np.stack([10*shape]*3); off = np.stack([np.roll(10*shape,40)]*3)
    class Store:
        expected_ids = {('on',0,9):'on', ('off',0,9):'off'}
        def get(self,kind,t,w): return (on if kind=='on' else off),kind
    m = dict(record_id='x',template_index=0,proxy_carrier_index=100,spectral_width_channels=9,
        active_epochs_zero_based=[0,1],epoch_values_at_proxy_carrier=[10.,10.,10.],
        passes_evaluated_physical_vetoes=True,meets_diagnostic_rank_cut=True,physical_disposition='pending_receiver_alias_evaluation')
    out,ev,profiles = apply_controls({'members':[m]},Store(),g,[np.ones((1,2))]*3,[np.full((1,2),1150./1190.)]*3)
    assert [out[p]['final_diagnostic_survivors'] for p in POLICIES] == [0,1,0]
