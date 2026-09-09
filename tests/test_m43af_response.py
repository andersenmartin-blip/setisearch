import copy
import math

import numpy as np
import pytest

from seti_repeater.response_m43af import projection, query_inventory, measure_member


def member(values=(8., 4., 6.), active=(0, 1, 2), **changes):
    m = dict(record_id='member', template_index=0, proxy_carrier_index=20,
             spectral_width_channels=1, active_epochs_zero_based=list(active),
             epoch_values_at_proxy_carrier=list(values),
             passes_evaluated_physical_vetoes=True, meets_diagnostic_rank_cut=True)
    m.update(changes)
    return m


def profiles(m):
    result = {}
    for h in ('receiver_mean', 'candidate_track'):
        for e in m['active_epochs_zero_based']:
            a = m['epoch_values_at_proxy_carrier'][e]
            result[f'0:20:1:{e}:{h}'] = dict(template=0, score_index=20, width=1,
                epoch=e, hypothesis=h, complete=True, on_values=[0., a, 0.],
                aligned_off_values=[0., a/2, 0.])
    return result


def test_projection_has_analytic_scale_and_offset_invariance():
    a = np.array([0., 3., 0.]); b = a/2
    p = projection(a, b)
    assert p['projection'] == pytest.approx(math.sqrt(6)/2)
    assert p['correlation'] == pytest.approx(1.)
    assert projection(10*a+7, b+100)['projection'] == pytest.approx(p['projection'])


def test_negative_and_constant_responses_are_not_discarded():
    p = projection([0., 3., 0.], [0., -2., 0.])
    assert p['projection'] < 0 and p['correlation'] == pytest.approx(-1.)
    assert projection([0., 3., 0.], [4., 4., 4.])['projection'] == 0.
    p = projection([2., 2., 2.], [0., 3., 0.])
    assert not p['defined'] and p['projection'] is None


@pytest.mark.parametrize('a,b', [([1., 2.], [1., 2.]), ([1., 2., 3.], [1., 2., 3., 4.]),
                              ([0., float('nan'), 0.], [0., 1., 0.])])
def test_invalid_profiles_fail(a, b):
    with pytest.raises(ValueError): projection(a, b)


def test_weak_epoch_failure_is_queried_before_the_old_cut():
    m = member((12., 4., 0.), (0, 1))
    original = copy.deepcopy(m)
    links, requests = query_inventory([m])
    assert not links[0]['old_remaining']['remaining_passed']
    assert len(requests) == 4 and links[0]['eligible_before_remaining']
    assert m == original
    for changes in ({'passes_evaluated_physical_vetoes': False}, {'meets_diagnostic_rank_cut': False}):
        links, requests = query_inventory([dict(m, **changes)])
        assert not requests and not links[0]['eligible_before_remaining']


def test_duplicate_members_fail_but_shared_queries_are_deduplicated():
    m = member()
    with pytest.raises(ValueError): query_inventory([m, m])
    links, requests = query_inventory([m, dict(m, record_id='second')])
    assert len(links) == 2 and len(requests) == 6


def test_joint_measurements_have_analytic_values_without_decisions():
    m = member(); p = profiles(m); original = copy.deepcopy(p)
    r = measure_member(m, p)
    scale = math.sqrt(2/3)
    assert r['off']['receiver_mean']['projection_mean'] == pytest.approx(3*scale)
    assert r['on']['projection_mean'] == pytest.approx(5*scale)
    assert r['on']['template_epoch'] == 0
    assert p == original and 'vetoed' not in r and 'p_value' not in r


def test_strongest_tie_is_canonical_and_is_excluded_from_confirmation():
    m = member((8., 8., 2.)); r = measure_member(m, profiles(m))
    assert r['on']['template_epoch'] == 0
    assert r['on']['remaining_epochs'] == [1, 2]
    m = member((1., 8., 8.), (1, 2)); r = measure_member(m, profiles(m))
    assert r['on']['template_epoch'] == 1 and r['on']['remaining_epochs'] == [2]


def test_missing_mapping_never_becomes_a_partial_average():
    m = member(); p = profiles(m)
    p.pop('0:20:1:1:receiver_mean')
    r = measure_member(m, p)
    assert not r['off']['receiver_mean']['complete']
    assert r['off']['receiver_mean']['projection_mean'] is None
    assert r['off']['candidate_track']['complete'] and r['on']['complete']
    p['0:20:1:1:candidate_track']['complete'] = False
    r = measure_member(m, p)
    assert not r['on']['complete'] and r['on']['projection_mean'] is None


def test_constant_strongest_on_profile_is_undefined_not_zero_evidence():
    m = member(); p = profiles(m)
    for h in ('receiver_mean', 'candidate_track'):
        p[f'0:20:1:0:{h}']['on_values'] = [8., 8., 8.]
    r = measure_member(m, p)
    assert r['on']['complete'] and not r['on']['defined']
    assert r['on']['projection_mean'] is None


@pytest.mark.parametrize('change', ['identity', 'center', 'hypothesis_on_disagreement'])
def test_profile_corruption_is_detected(change):
    m = member(); p = profiles(m); row = p['0:20:1:0:receiver_mean']
    if change == 'identity': row['epoch'] = 1
    elif change == 'center': row['on_values'][1] += 1
    else: row['on_values'][0] += 1
    with pytest.raises(ValueError): measure_member(m, p)
