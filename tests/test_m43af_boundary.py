import copy
import math

import pytest

from seti_repeater.boundary_m43af import accepts, coordinates, fit, higher_grid, REFERENCES
from m43af_scalar_audit import scalar_projection


def case(name, signal, xy, recovered=False, panel='training'):
    return dict(name=name, panel=panel, signal_present=signal, complete=True,
        members=[dict(record_id=name, coordinate=None if xy is None else dict(on=xy[0], off=xy[1]))],
        associated_record_ids=[name], reference_recovered={p:recovered for p in REFERENCES})


def baseline():
    b = case('baseline', False, (0., 0.), panel='baseline')
    b['members'] = []
    b['associated_record_ids'] = []
    return b


def test_joint_boundary_uses_both_coordinates_and_case_outcomes():
    # ON alone cannot remove high-ON controls; OFF alone cannot remove low-OFF controls.
    training = [case('signal', True, (5., 1.), True),
                case('control-high', False, (8., 4.)),
                case('control-low', False, (2., 0.))]
    before = copy.deepcopy(training)
    result = fit(training, baseline())
    assert result['feasible']
    assert result['boundary'] == dict(on_lower=5., off_upper=4.)
    assert training == before
    selected = next(r for r in result['grid'] if r['boundary'] == result['boundary'])
    assert selected['recovered_signal_cases'] == 1
    assert selected['leaking_control_or_baseline_cases'] == []


def test_identical_signal_control_has_no_fallback_boundary():
    training = [case('s', True, (5., 1.), True), case('c', False, (5., 1.))]
    result = fit(training, baseline())
    assert not result['feasible'] and result['boundary'] is None
    assert result['reason'] == 'no_feasible_joint_boundary'


def test_missing_evidence_blocks_fit_and_holdout_is_forbidden():
    training = [case('s', True, (5., 1.), True), case('c', False, None)]
    assert fit(training, baseline())['reason'] == 'incomplete_or_undefined_evidence'
    training[0]['panel'] = 'validation'
    with pytest.raises(ValueError):
        fit(training, baseline())


def test_boundary_inequalities_and_unbounded_values_are_explicit():
    xy = dict(on=5., off=4.)
    assert not accepts(xy, dict(on_lower=5., off_upper=4.))
    assert accepts(xy, dict(on_lower=5., off_upper=None))
    assert accepts(xy, dict(on_lower=None, off_upper=5.))
    assert not accepts(None, dict(on_lower=None, off_upper=None))


def test_higher_quantiles_and_nonfinite_rejection():
    assert higher_grid(list(range(65))) == list(range(0, 65, 2))
    assert higher_grid([3., 3.]) == [3.]
    with pytest.raises(ValueError):
        higher_grid([math.nan])


def test_complete_coordinates_preserve_negative_response():
    m = dict(spectral_width=1, on=dict(complete=True, defined=True, projection_mean=3.),
             off={h:dict(complete=True, defined=True, projection_mean=-2.)
                  for h in ('receiver_mean', 'candidate_track')})
    assert coordinates(m) == dict(on=3/math.sqrt(3), off=-2/math.sqrt(3))
    m['off']['receiver_mean']['complete'] = False
    assert coordinates(m) is None


def test_independent_scalar_analytic_sign_and_constant_template():
    result = scalar_projection([0., 3., 0.], [0., -2., 0.])
    assert result['projection'] == pytest.approx(-math.sqrt(8/3))
    assert result['correlation'] == pytest.approx(-1.)
    assert not scalar_projection([2., 2., 2.], [0., 3., 0.])['defined']
