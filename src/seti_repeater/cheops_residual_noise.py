"""LS8M fixed, descriptive residual/noise accounting; no detection rule."""
import numpy as np

MODELS = {'brightness': [0, 3], 'displacement': [1, 2, 3], 'combined': [0, 1, 2, 3]}


def temporal(times, cube, train, target, common):
    """Sideband OLS; target prediction and side residuals share one operator."""
    t = np.asarray(times, float)
    ys = np.asarray(cube[train][:, common], float)
    offset = np.median(ys, axis=0)
    z = ys - offset
    tm = np.mean(t[train]); tx = t[train] - tm
    intercept = z.mean(axis=0)
    slope = tx @ (z - intercept) / (tx @ tx)
    side = z - intercept - tx[:, None] * slope
    event = (cube[target][common] - offset) - intercept - (t[target] - tm) * slope
    mean = np.full(common.shape, np.nan)
    mean[common] = ys.mean(axis=0)
    leverage = 1 + 1 / len(train) + (t[target] - tm) ** 2 / (tx @ tx)
    return event, side, mean, float(leverage)


def prepare(times, cube, train, target, common, center):
    yall, sall, mean, h = temporal(times, cube, train, target, common)
    yy, xx = np.indices(common.shape)
    cx, cy = center
    r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    ann = common & (r2 > 900) & (r2 <= 1600)
    assert ann.any(), 'NO_BACKGROUND_ANNULUS'
    p = mean - np.median(mean[ann])
    gx = np.full_like(p, np.nan); gy = gx.copy()
    gx[:, 1:-1] = (p[:, 2:] - p[:, :-2]) / 2
    gy[1:-1] = (p[2:] - p[:-2]) / 2
    mask = common & (r2 <= 625) & np.isfinite(gx) & np.isfinite(gy)
    assert mask.sum() > 4 and common[r2 <= 625].all(), 'INCOMPLETE_APERTURE'
    take = mask[common]
    y, side = yall[take], sall[:, take]
    x = np.column_stack([p[mask], gx[mask], gy[mask], np.ones(mask.sum())])
    s2 = np.sum(side ** 2, axis=0) / (len(train) - 2)
    median = float(np.median(s2))
    assert np.isfinite(median) and median > 0, 'NO_POSITIVE_SIDEBAND_VARIANCE'
    # Fixed 50% shrinkage. No pixel masking or optimization using event values.
    variance = h * (0.5 * s2 + 0.5 * median)
    return {'y': y, 'side': side, 'x': x, 'variance': variance, 's2': s2,
            'h': h, 'mask': mask, 'xy': np.column_stack([xx[mask], yy[mask]]),
            'center': np.asarray(center, float), 'df': len(train) - 2}


def operator(x, variance):
    root = np.sqrt(variance)
    a = x / root[:, None]
    scales = np.linalg.norm(a, axis=0)
    assert np.all(scales > 0), 'ZERO_TEMPLATE'
    normalized = a / scales
    u, s, vt = np.linalg.svd(normalized, full_matrices=False)
    assert np.sum(s > s[0] * 1e-12) == x.shape[1], 'RANK_DEFICIENT'
    # Maps native-valued pixels to coefficients in unnormalized template units.
    b = ((vt.T / s) @ u.T) / scales[:, None] / root[None, :]
    return b, float(s[0] / s[-1])


def model_result(state, columns):
    y, side, variance = state['y'], state['side'], state['variance']
    x = state['x'][:, columns]
    b, condition = operator(x, variance)
    beta = b @ y; residual = y - x @ beta
    sb = side @ b.T; sr = side - sb @ x.T
    energy = float(y @ y); re = float(residual @ residual)
    wenergy = float(np.sum(y * y / variance)); wr = float(np.sum(residual ** 2 / variance))
    expected = float(state['h'] * np.sum(sr ** 2) / state['df'])
    wexpected = float(state['h'] * np.sum(sr ** 2 / variance) / state['df'])
    coeff_sd = np.sqrt(state['h'] * np.sum(sb ** 2, axis=0) / state['df'])
    flux_sd = float(np.sqrt(state['h'] * np.sum(np.sum(side, axis=1) ** 2) / state['df']))
    diagonal_sd = float(np.sqrt(state['h'] * np.sum(state['s2'])))
    summary = {
        'coefficients': beta.tolist(), 'coefficient_sideband_sd': coeff_sd.tolist(),
        'condition': condition, 'raw_explained': 1 - re / energy if energy > 0 else None,
        'weighted_explained': 1 - wr / wenergy if wenergy > 0 else None,
        'residual_energy_adu2': re, 'weighted_residual_energy': wr,
        'expected_residual_energy_adu2': expected, 'expected_weighted_residual_energy': wexpected,
        'residual_to_sideband_energy_ratio': re / expected if expected > 0 else None,
        'weighted_residual_to_sideband_ratio': wr / wexpected if wexpected > 0 else None,
        'event_flux_adu': float(y.sum()), 'residual_flux_adu': float(residual.sum()),
        'residual_flux_sideband_sd_adu': float(np.sqrt(state['h'] * np.sum(sr.sum(axis=1) ** 2) / state['df'])),
        'aperture_sideband_sd_adu': flux_sd, 'diagonal_aperture_sd_adu': diagonal_sd,
        'aperture_correlation_sd_ratio': flux_sd / diagonal_sd,
    }
    return summary, residual, b


def spatial(state, residual):
    xy, center = state['xy'], state['center']
    dx, dy = (xy - center).T
    r2 = dx * dx + dy * dy
    ring = np.where(r2 <= 64, 0, np.where(r2 <= 256, 1, 2))
    quadrant = np.where(dy >= 0, np.where(dx >= 0, 0, 1), np.where(dx < 0, 2, 3))
    raw = residual ** 2; white = raw / state['variance']
    result = []
    for r in range(3):
        for q in range(4):
            use = (ring == r) & (quadrant == q)
            result.append({'ring': r, 'quadrant': q, 'pixels': int(use.sum()),
                'flux_adu': float(residual[use].sum()),
                'raw_energy_fraction': float(raw[use].sum() / raw.sum()) if raw.sum() else None,
                'weighted_energy_fraction': float(white[use].sum() / white.sum()) if white.sum() else None})
    # Ordered concentration is reported only, never used to mask or classify.
    concentration = {}
    for name, values in [('raw', raw), ('weighted', white)]:
        order = np.argsort(-values, kind='stable')
        total = float(values.sum())
        concentration[name] = {'top1_fraction': float(values[order[:1]].sum() / total) if total else None,
            'top10_fraction': float(values[order[:10]].sum() / total) if total else None,
            'maximum_xy': xy[order[0]].tolist()}
    return {'cells': result, 'concentration': concentration}


def describe(state):
    models = {}; residual = None
    for name, columns in MODELS.items():
        models[name], r, _ = model_result(state, columns)
        if name == 'combined': residual = r
    return {'pixels': len(state['y']), 'sideband_df': state['df'], 'leverage': state['h'],
            'median_sideband_variance_adu2': float(np.median(state['s2'])),
            'models': models, 'spatial': spatial(state, residual)}, residual


def correction_account(cal, cor):
    assert np.array_equal(cal['mask'], cor['mask']), 'PAIRED_FIT_MASK_MISMATCH'
    x = cor['x']; b, _ = operator(x, cor['variance'])
    residual = {}
    for name, y in [('CAL', cal['y']), ('COR', cor['y']), ('DELTA', cor['y'] - cal['y'])]:
        residual[name] = y - x @ (b @ y)
    result = {}
    for name, weight in [('raw', np.ones(len(cor['y']))), ('weighted', 1 / cor['variance'])]:
        a, c, d = residual['CAL'], residual['COR'], residual['DELTA']
        ec = float(np.sum(weight * c * c))
        ea = float(np.sum(weight * a * a)); ed = float(np.sum(weight * d * d))
        cross = float(2 * np.sum(weight * a * d))
        result[name] = {'cor_energy': ec, 'cal_energy': ea, 'delta_energy': ed,
            'twice_cross_energy': cross, 'cal_over_cor': ea / ec, 'delta_over_cor': ed / ec,
            'twice_cross_over_cor': cross / ec,
            'closure_relative_error': (ec - ea - ed - cross) / max(1., ec + ea + ed + abs(cross))}
    return result


def injections(state):
    """Fixed signed pure templates and geometric compact defects, no event tuning."""
    x, xy = state['x'], state['xy']
    pulses = [('brightness', 0.001 * x[:, 0], [0.001, 0, 0, 0]),
              ('shift_x', 0.05 * x[:, 1], [0, 0.05, 0, 0]),
              ('shift_y', 0.05 * x[:, 2], [0, 0, 0.05, 0])]
    for j, offset in enumerate([[0, 0], [10, 0], [0, 10], [-10, 0], [0, -10]]):
        target = state['center'] + offset
        index = int(np.argmin(np.sum((xy - target) ** 2, axis=1)))
        pulse = np.zeros(len(x)); pulse[index] = 5 * np.sqrt(state['variance'][index])
        pulses.append((f'compact_{j}', pulse, None))
    bc, _ = operator(x, state['variance'])
    bd, _ = operator(x[:, MODELS['displacement']], state['variance'])
    records = []
    for name, positive, expected in pulses:
        for sign in (-1, 1):
            pulse = sign * positive
            recovered = bc @ pulse
            increment = bc @ (state['y'] + pulse) - bc @ state['y']
            remaining = pulse - x[:, MODELS['displacement']] @ (bd @ pulse)
            denom = float(pulse.sum())
            records.append({'kind': name, 'sign': sign,
                'expected_combined_coefficients': (sign * np.array(expected)).tolist() if expected is not None else None,
                'pure_combined_coefficients': recovered.tolist(), 'additive_coefficient_increment': increment.tolist(),
                'additive_linearity_max_error': float(np.max(np.abs(increment - recovered))),
                'displacement_removal_retained_weighted_energy_fraction': float(np.sum(remaining ** 2 / state['variance']) / np.sum(pulse ** 2 / state['variance'])),
                'displacement_removal_flux_fraction': float(remaining.sum() / denom) if abs(denom) > 1e-10 * np.sum(np.abs(pulse)) else None,
                'injected_flux_adu': denom})
    return records
