import copy

import pytest

from seti_repeater.boundary_m43af import fit
from m43af_study_audit import audit_fit
from test_m43af_boundary import case, baseline


def test_independent_boundary_grid_and_corruption():
    training = [case('s', True, (5., 1.), True), case('c1', False, (8., 4.)),
                case('c2', False, (2., 0.))]
    b = baseline()
    model = fit(training, b)
    assert audit_fit(training, b, [], model)['passed']
    corrupted = copy.deepcopy(model)
    corrupted['grid'][0]['outcomes'][0]['final_members'] += 1
    with pytest.raises(AssertionError):
        audit_fit(training, b, [], corrupted)
    corrupted = copy.deepcopy(model)
    corrupted['boundary']['on_lower'] += 1
    with pytest.raises(AssertionError):
        audit_fit(training, b, [], corrupted)


def test_independent_audit_of_infeasible_and_incomplete_training():
    training = [case('s', True, (5., 1.), True), case('c', False, (5., 1.))]
    b = baseline()
    assert audit_fit(training, b, [], fit(training, b))['passed']
    null = case('n', False, None, panel='null_training')
    assert audit_fit(training, b, [null], fit(training, b, [null]))['passed']
