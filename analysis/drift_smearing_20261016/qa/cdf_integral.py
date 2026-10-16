"""Independent bin-mass integral for a unit box plus uniform drift sweep.

This module has no dependency on the production implementation.  If X is
uniform on [-1/2, 1/2] and Y is uniform on [-L/2, L/2], the CDF of X + Y
is a quadratic lower ramp, linear middle, and quadratic upper ramp.
Differences of that CDF at integer channel edges give unit-area bin masses.
"""
from __future__ import annotations

import math
import numpy as np


def convolved_box_cdf(x: float, sweep_width_channels: float) -> float:
    """P(X+Y <= x), with a unit-width intrinsic box and sweep L>=0."""
    x = np.longdouble(x)
    width = np.longdouble(sweep_width_channels)
    if not np.isfinite(x) or not np.isfinite(width) or width < 0:
        raise ValueError("Finite x and nonnegative finite sweep width required")
    if width == 0:
        return float(np.clip(x + np.longdouble('0.5'), 0, 1))
    small, large = sorted((np.longdouble(1), width))
    half_support = (small + large) / 2
    half_flat = (large - small) / 2
    if x <= -half_support:
        return 0.0
    if x >= half_support:
        return 1.0
    if x < -half_flat:
        return float((x + half_support) ** 2 / (2 * small * large))
    if x <= half_flat:
        return float(np.longdouble('0.5') + x / large)
    return float(1 - (half_support - x) ** 2 / (2 * small * large))


def channel_masses(local_center: float, sweep_width_channels: float):
    """Return all positive-support integer local channel centers and masses."""
    half = (1.0 + sweep_width_channels) / 2.0
    lo = math.floor(local_center - half - 0.5) - 1
    hi = math.ceil(local_center + half + 0.5) + 1
    bins, masses = [], []
    for index in range(lo, hi + 1):
        a = index - 0.5 - local_center
        b = index + 0.5 - local_center
        mass = convolved_box_cdf(b, sweep_width_channels) - convolved_box_cdf(a, sweep_width_channels)
        if mass > 0:
            bins.append(index)
            masses.append(mass)
    return np.asarray(bins, dtype=np.int64), np.asarray(masses, dtype=np.float64)


def selftest():
    expected = {
        0.0: ([0], [1.0]),
        1.0: ([-1, 0, 1], [.125, .75, .125]),
        2.0: ([-1, 0, 1], [.25, .5, .25]),
    }
    for width, (expected_bins, expected_masses) in expected.items():
        bins, masses = channel_masses(0.0, width)
        np.testing.assert_array_equal(bins, expected_bins)
        np.testing.assert_allclose(masses, expected_masses, rtol=0, atol=1e-15)
    cases = 0
    max_area_error = 0.0
    for width in (0.0, 1e-8, .1, .5, 1.0, 2.0, 6.25, 25.47, 100.0):
        for center in (-1024.49, -1.0, -.5, 0.0, .29, .5, .9999, 1024.49):
            bins, masses = channel_masses(center, width)
            area_error = abs(float(np.sum(masses)) - 1.0)
            max_area_error = max(max_area_error, area_error)
            assert np.all(masses >= 0)
            assert area_error < 1e-14
            mirrored_bins, mirrored_masses = channel_masses(-center, width)
            np.testing.assert_array_equal(bins, -mirrored_bins[::-1])
            np.testing.assert_allclose(masses, mirrored_masses[::-1], rtol=0, atol=2e-15)
            cases += 1
    return {"cases": cases, "known_exact_cases": len(expected), "max_area_error": max_area_error}


if __name__ == "__main__":
    import json
    print(json.dumps(selftest(), indent=2))
