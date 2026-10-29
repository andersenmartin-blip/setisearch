"""Exact v3 broad-envelope maxima, batched without seed-by-grid masks.

This is context only: these maxima must not be used as automatic OFF vetoes.
Grid construction and boundary inclusion deliberately match run_pilot v3.
"""
from __future__ import annotations

import numpy as np

WIDTHS = (1, 3, 9, 33)


def _exact_bounds(frequencies, seed, halfwidth):
    """Return half-open indices for v3's floating point inclusion predicate.

    searchsorted supplies approximate endpoints. The predicates below correct
    rounding at those endpoints using precisely abs(freq-seed)*1e6 <= halfwidth,
    rather than assuming algebraically rearranged float expressions agree.
    """
    n = len(frequencies)
    lower = np.searchsorted(frequencies, seed - halfwidth / 1e6, side='left')
    upper = np.searchsorted(frequencies, seed + halfwidth / 1e6, side='right')

    def lower_predicate(index, selected):
        f = frequencies[index]
        s = seed[selected]
        return (f >= s) | (np.abs(f - s) * 1e6 <= halfwidth[selected])

    def upper_predicate(index, selected):
        f = frequencies[index]
        s = seed[selected]
        return (f <= s) | (np.abs(f - s) * 1e6 <= halfwidth[selected])

    # Each loop normally needs zero or one correction. The monotone endpoint
    # predicates also handle empty ranges and seed positions outside the grid.
    while True:
        q = np.flatnonzero(lower > 0)
        q = q[lower_predicate(lower[q] - 1, q)]
        if not len(q):
            break
        lower[q] -= 1
    while True:
        q = np.flatnonzero(lower < n)
        q = q[~lower_predicate(lower[q], q)]
        if not len(q):
            break
        lower[q] += 1
    while True:
        q = np.flatnonzero(upper > 0)
        q = q[~upper_predicate(upper[q] - 1, q)]
        if not len(q):
            break
        upper[q] -= 1
    while True:
        q = np.flatnonzero(upper < n)
        q = q[upper_predicate(upper[q], q)]
        if not len(q):
            break
        upper[q] += 1
    if np.any(lower > upper):
        raise AssertionError('Non-monotone exact floating point frequency bounds')
    return lower, upper


def _range_maximum(values, lower, upper):
    """Vectorized segment-tree half-open queries; -inf denotes empty ranges."""
    n = len(values)
    if not n:
        return np.full(lower.shape, -np.inf, dtype=np.float64)
    size = 1 << (n - 1).bit_length()
    tree = np.full(2 * size, -np.inf, dtype=np.float64)
    tree[size:size + n] = values
    width = size
    while width > 1:
        first = width // 2
        tree[first:width] = np.maximum(tree[width:2 * width:2],
                                       tree[width + 1:2 * width:2])
        width = first
    left = np.asarray(lower, dtype=np.int64).copy() + size
    right = np.asarray(upper, dtype=np.int64).copy() + size
    answer = np.full(left.shape, -np.inf, dtype=np.float64)
    while np.any(left < right):
        q = np.flatnonzero((left < right) & ((left & 1) != 0))
        answer[q] = np.maximum(answer[q], tree[left[q]])
        left[q] += 1
        q = np.flatnonzero((left < right) & ((right & 1) != 0))
        right[q] -= 1
        answer[q] = np.maximum(answer[q], tree[right[q]])
        left //= 2
        right //= 2
    return answer


def broad_envelope_max(grid_dict, destination_scope, seed_frequencies_mhz,
                       halfwidth_hz):
    """Return v3 broad-envelope maxima across the four saved width grids.

    Inputs seed_frequencies_mhz and halfwidth_hz are equally shaped 1-D arrays;
    radii must be finite and nonnegative. Saved centers must be strictly
    increasing, scores finite, and df finite/nonzero. Empty destination grids
    are allowed. The result is float64 with NaN where no grid center is included.

    This function does not read powers, change detector calibration, or decide
    whether a source is RFI. Its caller owns the prospective radius definition.
    """
    seed = np.asarray(seed_frequencies_mhz, dtype=np.float64)
    halfwidth = np.asarray(halfwidth_hz, dtype=np.float64)
    if seed.ndim != 1 or halfwidth.shape != seed.shape:
        raise ValueError('Seed frequencies and halfwidths require equal 1-D shapes')
    if (not np.isfinite(seed).all() or not np.isfinite(halfwidth).all()
            or np.any(halfwidth < 0)):
        raise ValueError('Seed frequencies/radii must be finite; radii nonnegative')
    fch1 = float(destination_scope['fch1_mhz'])
    df = float(destination_scope['df_hz'])
    if not np.isfinite(fch1) or not np.isfinite(df) or df == 0:
        raise ValueError('Destination frequency metadata must be finite, df nonzero')
    answer = np.full(seed.shape, -np.inf, dtype=np.float64)
    for width in WIDTHS:
        centers = np.asarray(grid_dict[f'centers_width_{width}'])
        values = np.asarray(grid_dict[f'max_ess_width_{width}'])
        if centers.ndim != 1 or values.shape != centers.shape:
            raise ValueError(f'Invalid width-{width} grid shapes')
        if (not np.isfinite(centers).all() or not np.isfinite(values).all()
                or np.any(centers[1:] <= centers[:-1])):
            raise ValueError(f'Width-{width} grid is not finite/strictly ordered')
        # Preserve v3's operation order and native center dtype in this formula.
        frequencies = fch1 + centers * df / 1e6
        if not np.isfinite(frequencies).all():
            raise ValueError(f'Non-finite width-{width} frequency grid')
        if df < 0:
            frequencies = frequencies[::-1]
            values = values[::-1]
        if np.any(frequencies[1:] <= frequencies[:-1]):
            raise ValueError(f'Width-{width} frequencies are not strictly ordered')
        if not len(frequencies) or not len(seed):
            continue
        lower, upper = _exact_bounds(frequencies, seed, halfwidth)
        answer = np.maximum(answer, _range_maximum(values, lower, upper))
    answer[answer == -np.inf] = np.nan
    return answer
