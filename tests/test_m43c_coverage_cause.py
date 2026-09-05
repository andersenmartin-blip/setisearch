import unittest
import numpy as np
from m43c_coverage_cause import template_diagnostic, truth_cause


class CoverageCauseTests(unittest.TestCase):
    def test_track_shape_failure(self):
        r=template_diagnostic([1,1],[450,550],np.arange(400.,601.),0)
        self.assertEqual(r['cause'],'track-shape-incompatible')
        self.assertAlmostEqual(r['minimum_continuous_residual_hz'],50.)

    def test_outside_range(self):
        r=template_diagnostic([1,1],[700,700],np.arange(400.,601.),0)
        self.assertEqual(r['cause'],'outside-carrier-range')

    def test_grid_gap_with_feasible_continuous_carrier(self):
        r=template_diagnostic([1,1],[500,500],np.array([450.,550.]),0)
        self.assertEqual(r['cause'],'carrier-grid-gap')
        self.assertEqual(r['minimum_continuous_residual_hz'],0.)

    def test_diagnostic_guard_preserves_ambiguity(self):
        r=template_diagnostic([1,1],[480,520],np.arange(400.,601.),0)
        self.assertEqual(r['cause'],'numerical-boundary-unresolved')
        r=template_diagnostic([1,1],[480,520],np.arange(400.,601.),1)
        self.assertEqual(r['cause'],'supported')

    def test_minimax_against_independent_dense_objective(self):
        a=np.array([.9,1.,1.1]);y=np.array([440.,515.,570.])
        r=template_diagnostic(a,y,np.arange(300.,701.),0)
        q=np.linspace(400,650,100001);minimum=np.abs(q[:,None]*a-y).max(axis=1).min()
        self.assertLessEqual(r['minimum_continuous_residual_hz'],minimum+1e-9)
        self.assertLess(minimum-r['minimum_continuous_residual_hz'],.003)

    def test_truth_priority_does_not_hide_ambiguity(self):
        cause,_=truth_cause([{'cause':'track-shape-incompatible'},{'cause':'carrier-grid-gap'}])
        self.assertEqual(cause,'carrier-grid-gap')
        cause,_=truth_cause([{'cause':'numerical-boundary-unresolved'},{'cause':'carrier-grid-gap'}])
        self.assertEqual(cause,'numerical-boundary-unresolved')
