import copy
from types import SimpleNamespace

import numpy as np
import pytest

from seti_repeater.acquisition_m43af import acquire
from m43af_scalar_audit import audit_acquisition


class Store:
    def __init__(self):
        self.on = np.zeros((3, 65), dtype='<f4')
        self.on[:, 32] = (12., 4., 0.)
        self.off = self.on/np.float32(2)
        self.expected_ids = {('on', 0, 1):'on', ('off', 0, 1):'off'}

    def get(self, kind, t, w):
        assert t == 0 and w == 1
        return getattr(self, kind), kind


def fixture():
    support = 1000.+np.arange(65)
    grid = SimpleNamespace(score_bin_count=33, support_bin_count=65,
        score_slice=slice(16, 49), support_hz=support, score_hz=support[16:49],
        channel_width_hz=1.)
    factors = [np.ones((1, 16)) for _ in range(3)]
    m = dict(record_id='weak', template_index=0, proxy_carrier_index=16,
        spectral_width_channels=1, active_epochs_zero_based=[0, 1],
        epoch_values_at_proxy_carrier=[12., 4., 0.],
        passes_evaluated_physical_vetoes=True, meets_diagnostic_rank_cut=True)
    return dict(members=[m]), Store(), grid, factors


def test_pre_confirmation_acquisition_scalar_and_coordinates():
    audit, store, grid, factors = fixture()
    evidence = acquire(audit, store, grid, factors, factors)
    assert evidence['counts']['eligible_before_remaining'] == 1
    assert evidence['counts']['eligible_passing_old_remaining'] == 0
    assert evidence['counts']['requested_unique_profiles'] == 4
    assert evidence['counts']['member_profile_links'] == 4
    result = audit_acquisition(audit, evidence, grid, factors, factors)
    assert result['profiles'] == 4
    assert evidence['measurements'][0]['on']['defined']


def test_exact_reuse_and_rejected_geometry_do_not_change_queries():
    audit, store, grid, factors = fixture()
    original = acquire(audit, store, grid, factors, factors)
    saved = copy.deepcopy(original['profiles'])
    evidence = acquire(audit, store, grid, factors, factors, saved)
    assert evidence['counts']['reused_complete_profiles'] == 4
    assert evidence['measurements'] == original['measurements']
    assert saved == original['profiles']
    audit['members'][0]['passes_evaluated_physical_vetoes'] = False
    evidence = acquire(audit, store, grid, factors, factors, saved)
    assert evidence['profiles'] == {} and evidence['measurements'] == []


@pytest.mark.parametrize('corruption', ['score', 'identity', 'profile', 'placeholder'])
def test_corruption_is_not_silently_remeasured(corruption):
    audit, store, grid, factors = fixture()
    saved = acquire(audit, store, grid, factors, factors)['profiles']
    pid = next(iter(saved))
    if corruption == 'score':
        store.on[0, 32] += 1
    elif corruption == 'identity':
        store.expected_ids['on', 0, 1] = 'changed'
    elif corruption == 'profile':
        saved[pid]['aligned_off_values'][1] += 1
    else:
        saved[pid] = dict(complete=True, profile_id=None, queried=False)
    with pytest.raises(ValueError):
        acquire(audit, store, grid, factors, factors, saved)


def test_scalar_audit_catches_measurement_and_link_corruption():
    audit, store, grid, factors = fixture()
    evidence = acquire(audit, store, grid, factors, factors)
    evidence['measurements'][0]['on']['projection_mean'] += .01
    with pytest.raises(AssertionError):
        audit_acquisition(audit, evidence, grid, factors, factors)
    evidence = acquire(audit, store, grid, factors, factors)
    evidence['links'][0]['profile_ids'].pop()
    with pytest.raises(AssertionError):
        audit_acquisition(audit, evidence, grid, factors, factors)
