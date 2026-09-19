import unittest
import numpy as np
from decimal import Decimal
from ls8c_auxiliary_audit import reference_series, UNITS
from seti_repeater.cheops_auxiliary import diagnose_series, coupling, unwrap_degrees, diagnose_context, FIELDS


class AuxiliaryAnswers(unittest.TestCase):
    def setUp(self):
        self.x = np.arange(30, dtype=float) - 14.
        self.side = np.r_[np.arange(12), np.arange(18, 30)]
        self.event = np.array([14, 15])

    def test_large_offset_slope_and_both_signs(self):
        for pulse in (1e-6, -1e-6, 17., -17.):
            y = 400_000_000. + 2. * self.x
            y[self.event] += pulse
            r = diagnose_series(self.x, y, self.side, self.event)
            expected = float(y[14] - 400_000_000.)
            self.assertAlmostEqual(r['mean_residual'], expected, places=12)
            self.assertAlmostEqual(r['slope_per_second'], 2., places=12)
            self.assertIsNone(r['mad_displacement'])

    def test_event_and_guards_cannot_train_coupling(self):
        a = np.sin(self.x)
        f = 1e5 + 7. * a + .5 * self.x
        a[self.event] += 2.
        f[self.event] += 14.
        f[12:14] += 1e6
        f[16:18] -= 1e6
        dr = diagnose_series(self.x, f, self.side, self.event)
        ar = diagnose_series(self.x, a, self.side, self.event)
        c = coupling(dr, ar, self.side)
        self.assertAlmostEqual(c['beta_electron_per_unit'], 7., places=9)
        self.assertAlmostEqual(c['side_correlation'], 1., places=12)
        self.assertAlmostEqual(c['remaining_flux_mean_residual'], 0., places=8)

    def test_wrap_and_exact_half_turn(self):
        np.testing.assert_array_equal(unwrap_degrees([358., 359., 0., 1.]), [358., 359., 360., 361.])
        np.testing.assert_array_equal(unwrap_degrees([0., 180., 0.]), [0., -180., -360.])

    def test_missing_and_constant_are_explicit(self):
        y = np.ones(30)
        r = diagnose_series(self.x, y, self.side, self.event)
        self.assertIsNone(r['mad_displacement'])
        self.assertEqual(coupling(r, r, self.side)['status'], 'UNAVAILABLE_SCATTER')
        y[12] = np.nan  # even a missing guard value invalidates this series
        self.assertEqual(diagnose_series(self.x, y, self.side, self.event)['status'], 'UNAVAILABLE_NONFINITE')

    def test_common_intended_measured_motion_cancels(self):
        names = ['BJD_TIME'] + [n for n in FIELDS if not n.startswith('OFFSET_')]
        table = np.zeros(60, dtype=[(n, 'f8') for n in names])
        table['BJD_TIME'] = np.arange(60) / 86400.
        table['LOCATION_X'] = np.arange(60) * .1
        table['LOCATION_X'][25:27] += 2.
        table['CENTROID_X'] = table['LOCATION_X'] + 3.
        table['CENTROID_Y'] = table['LOCATION_Y'] + 4.
        r = diagnose_context(table, 25, 2)
        self.assertAlmostEqual(r['series']['CENTROID_X']['mean_residual'], 2., places=11)
        self.assertAlmostEqual(r['centroid_offset_residual_norm_pixels'], 0., places=11)
        self.assertEqual(r['event_indices'], [25, 26])
        self.assertEqual(len(r['side_indices']), 24)

    def test_independent_decimal_known_answer(self):
        self.assertEqual(UNITS, FIELDS)
        x = [Decimal.from_float(v) for v in self.x]
        for pulse in (1e-6, -1e-6, 17., -17.):
            y = 400_000_000. + 2. * self.x
            y[self.event] += pulse
            r = reference_series(x, [Decimal.from_float(v) for v in y],
                                 self.side.tolist(), self.event.tolist())
            expected = Decimal.from_float(float(y[14] - 400_000_000.))
            self.assertEqual(r['mean_residual'], expected)
            self.assertEqual(r['slope_per_second'], Decimal(2))


if __name__ == '__main__':
    unittest.main()
