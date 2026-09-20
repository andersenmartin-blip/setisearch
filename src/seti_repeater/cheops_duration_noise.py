"""LS8U fixed-duration covariance and residual diagnostics for retained LS8T.

No source access, event-selected masks, new classification or calibrated p-values.
Pinned LS8M spatial algebra and LS8P temporal propagation, generalized to the
one-row and three-row durations and their own nominal cadence.
"""
import numpy as np
from .cheops_residual_noise import (
    MODELS, operator, correction_account)
from .cheops_three_sum_noise import describe, boundary_account

def layout(duration):
    assert duration in (1, 3), 'UNFROZEN_DURATION'
    side = np.r_[np.arange(12), np.arange(16 + duration, 28 + duration)]
    event = np.arange(14, 14 + duration)
    blocks = [np.arange(start, start + duration)
              for lo in (0, 16 + duration) for start in range(lo, lo + 12, duration)]
    return side, event, blocks


def training_rows(side, block):
    return side[(side < block[0] - 2) | (side > block[-1] + 2)]


def temporal(times, cube, train, target, common):
    t = np.asarray(times, float); train = np.asarray(train); target = np.asarray(target)
    assert len(target) in (1, 3) and not np.intersect1d(train, target).size
    values = np.asarray(cube[train][:, common], float)
    offset = np.median(values, axis=0); z = values - offset
    tm = t[train].mean(); tx = t[train] - tm; xx = tx @ tx
    assert xx > 0 and len(train) > 2
    a = z.mean(axis=0); b = tx @ (z - a) / xx
    residual = z - a - tx[:, None] * b
    event = np.sum((cube[target][:, common] - offset) - a - (t[target] - tm)[:, None] * b, axis=0)
    weights = np.zeros(len(t)); weights[target] = 1
    weights[train] = -len(target) / len(train) - np.sum(t[target] - tm) * tx / xx
    projection = np.eye(len(train)) - np.ones((len(train), len(train))) / len(train) - np.outer(tx, tx) / xx
    mean = np.full(common.shape, np.nan); mean[common] = values.mean(axis=0)
    return event, residual, mean, weights, projection


def covariance(times, train, side, weights, projection, cadence):
    """PSD Bartlett lag-2 correlation; zeros across cadence gaps or missing rows.

    Lag sums use a common biased denominator, not separate pair counts. This
    is the autocorrelation of zero-padded segments times a Bartlett window,
    and is PSD. OLS residuals make this a descriptive covariance estimate.
    """
    train = np.asarray(train); times = np.asarray(times, float)
    iid_s2 = np.sum(side ** 2, axis=0) / (len(train) - 2)
    median = float(np.median(iid_s2))
    assert np.isfinite(median) and median > 0, 'NO_POSITIVE_SIDEBAND_VARIANCE'
    standardized = side / np.sqrt((iid_s2 + median) / 2)
    denom = float(np.sum(standardized ** 2))
    assert np.isfinite(cadence) and cadence > 0
    segments = np.r_[0, np.cumsum((np.diff(times) < .5 * cadence) | (np.diff(times) > 1.5 * cadence))]
    lags = []; pairs = []
    for lag, taper in ((1, 2 / 3), (2, 1 / 3)):
        a, b = np.where((train[None, :] - train[:, None] == lag) &
                        (segments[train, None] == segments[train][None, :]))
        lags.append(float(taper * np.sum(standardized[a] * standardized[b]) / denom))
        pairs.append(len(a))
    corr = np.eye(len(times)); indices = np.arange(len(times))
    for lag, rho in enumerate(lags, 1):
        use = (np.abs(indices[:, None] - indices[None, :]) == lag) & (segments[:, None] == segments[None, :])
        corr[use] = rho
    trace = float(np.trace(projection @ corr[np.ix_(train, train)]))
    h = float(weights @ corr @ weights); iid_h = float(weights @ weights)
    assert trace > 0 and h > 0 and np.linalg.eigvalsh(corr)[0] > 0, 'INVALID_TEMPORAL_COVARIANCE'
    return corr, h, trace, {'cadence_seconds': float(cadence), 'rho_lag1': lags[0], 'rho_lag2': lags[1],
        'lag_pair_counts': pairs, 'cadence_segments': int(segments[-1] + 1),
        'iid_sum_factor': iid_h, 'correlated_sum_factor': h,
        'iid_residual_df': len(train) - 2, 'correlated_residual_trace': trace,
        'correlated_to_iid_variance_factor': (h / trace) / (iid_h / (len(train) - 2)),
        'target_rows': np.flatnonzero(weights == 1).tolist(), 'train_rows': train.tolist(),
        'row_weights': weights.tolist()}


def prepare(times, cube, train, target, common, center, cadence):
    yall, sall, mean, weights, projection = temporal(times, cube, train, target, common)
    yy, xx = np.indices(common.shape); cx, cy = center
    radius = (xx - cx) ** 2 + (yy - cy) ** 2
    annulus = common & (radius > 900) & (radius <= 1600)
    assert annulus.any(), 'NO_BACKGROUND_ANNULUS'
    p = mean - np.median(mean[annulus])
    gx = np.full_like(p, np.nan); gy = gx.copy()
    gx[:, 1:-1] = (p[:, 2:] - p[:, :-2]) / 2
    gy[1:-1] = (p[2:] - p[:-2]) / 2
    mask = common & (radius <= 625) & np.isfinite(gx) & np.isfinite(gy)
    assert np.array_equal(mask, radius <= 625), 'INCOMPLETE_OR_CHANGED_APERTURE'
    take = mask[common]; side = sall[:, take]
    corr, h, df, info = covariance(times, train, side, weights, projection, cadence)
    s2 = np.sum(side ** 2, axis=0) / df
    variance = h * (s2 + np.median(s2)) / 2
    return {'y': yall[take], 'side': side,
        'x': np.column_stack([p[mask], gx[mask], gy[mask], np.ones(mask.sum())]),
        'variance': variance, 's2': s2, 'h': h, 'df': df, 'mask': mask,
        'xy': np.column_stack([xx[mask], yy[mask]]), 'center': np.asarray(center, float),
        'temporal': info, 'row_weights': weights, 'correlation': corr}


def injections(state):
    """All pulses denote a sum over the original duration, equal per exposure."""
    duration = len(state['temporal']['target_rows'])
    x, xy = state['x'], state['xy']
    cases = [('brightness', .001 * duration * x[:, 0], [.001 * duration, 0, 0, 0]),
             ('shift_x', .05 * duration * x[:, 1], [0, .05 * duration, 0, 0]),
             ('shift_y', .05 * duration * x[:, 2], [0, 0, .05 * duration, 0])]
    for j, offset in enumerate(([0, 0], [10, 0], [0, 10], [-10, 0], [0, -10])):
        index = int(np.argmin(np.sum((xy - state['center'] - offset) ** 2, axis=1)))
        pulse = np.zeros(len(x)); pulse[index] = 5 * np.sqrt(state['variance'][index])
        cases.append((f'compact_{j}', pulse, None))
    bc, _ = operator(x, state['variance']); xd = x[:, MODELS['displacement']]
    bd, _ = operator(xd, state['variance']); result = []
    for name, positive, truth in cases:
        for sign in (-1, 1):
            pulse = sign * positive; recovered = bc @ pulse
            increment = bc @ (state['y'] + pulse) - bc @ state['y']
            remaining = pulse - xd @ (bd @ pulse); flux = float(pulse.sum())
            result.append({'kind': name, 'sign': sign, 'exposures': duration,
                'expected_combined_coefficients': (sign * np.asarray(truth)).tolist() if truth is not None else None,
                'pure_combined_coefficients': recovered.tolist(), 'additive_coefficient_increment': increment.tolist(),
                'additive_linearity_max_error': float(np.max(np.abs(increment - recovered))),
                'displacement_removal_retained_weighted_energy_fraction': float(np.sum(remaining ** 2 / state['variance']) / np.sum(pulse ** 2 / state['variance'])),
                'displacement_removal_flux_fraction': float(remaining.sum() / flux) if abs(flux) > 1e-10 * np.sum(np.abs(pulse)) else None,
                'injected_flux_adu': flux})
    return result
