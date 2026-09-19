import unittest
from scripts.ls8b_l2_precision_review import reference


class PrecisionAnswers(unittest.TestCase):
    def test_large_linear_background_tiny_positive_and_negative_sum(self):
        xs = list(range(-14, -2)) + list(range(3, 15))
        side = [400_000_000. + 2.*x for x in xs]
        for pulse in [-.000001, 10., -10., 0.]:
            event = 400_000_000. + pulse
            exact_binary64_excess = event - 400_000_000.
            result = reference(xs, side, [1.]*24, [0.], [event])
            self.assertEqual(result['excess_electrons'], exact_binary64_excess)

    def test_three_row_exact_pulse_and_formal_noise_floor(self):
        xs = list(range(-15, -3)) + list(range(4, 16))
        side = [400_000_000. + 4.*x for x in xs]
        event = [400_000_000. + 4.*x + 2. for x in [-1., 0., 1.]]
        result = reference(xs, side, [3.]*24, [-1., 0., 1.], event)
        self.assertEqual(result['excess_electrons'], 6.)
        self.assertEqual(result['sigma_electrons'], 3.)
        self.assertAlmostEqual(result['denominator_electrons'], 3.*(3.+9./24.)**.5)


if __name__ == '__main__':
    unittest.main()
