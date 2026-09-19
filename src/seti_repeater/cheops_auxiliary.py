"""LS8C descriptive auxiliary diagnostics; no event selection or veto."""
import numpy as np

EPS = np.finfo(float).eps
FIELDS = {
    'FLUX': 'electron', 'DARK': 'electron', 'BACKGROUND': 'electron',
    'CONTA_LC': 'ratio', 'CONTA_LC_ERR': 'ratio',
    'SMEARING_LC': 'electron', 'SMEARING_LC_ERR': 'ratio',
    'ROLL_ANGLE': 'degree', 'LOCATION_X': 'pixel', 'LOCATION_Y': 'pixel',
    'CENTROID_X': 'pixel', 'CENTROID_Y': 'pixel',
    'OFFSET_X': 'pixel', 'OFFSET_Y': 'pixel',
}
COUPLING_FIELDS = ('DARK', 'BACKGROUND', 'CONTA_LC', 'SMEARING_LC',
                   'ROLL_ANGLE', 'OFFSET_X', 'OFFSET_Y')


def unwrap_degrees(values):
    """First angle unchanged; successive differences lie in [-180, 180)."""
    v = np.asarray(values, dtype=float)
    return np.r_[v[0], v[0] + np.cumsum((np.diff(v) + 180.) % 360. - 180.)]


def diagnose_series(times, values, side, event):
    """All rows must be finite. Centering preserves small residuals at large DC."""
    x, y = np.asarray(times, float), np.asarray(values, float)
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return {'status': 'UNAVAILABLE_NONFINITE'}
    scale = max(1., float(np.max(np.abs(y))))
    floor = 64. * EPS * scale
    offset = float(np.median(y[side]))
    ys = y[side] - offset
    xs = x[side]
    xc = xs - np.mean(xs)
    var = float(xc @ xc)
    if var <= 0.:
        return {'status': 'UNAVAILABLE_TIME_RANK'}
    slope = float(xc @ (ys - np.mean(ys)) / var)
    intercept = float(np.mean(ys) - slope * np.mean(xs))
    fitted_centered = intercept + slope * x
    residual = (y - offset) - fitted_centered
    rs = residual[side]
    mad = float(1.4826 * np.median(np.abs(rs - np.median(rs))))
    rms = float(np.sqrt(np.mean(rs * rs)))
    delta = float(np.mean(residual[event]))
    return {
        'status': 'AVAILABLE', 'roundoff_floor': floor,
        'event_mean': float(np.mean(y[event])),
        'predicted_event_mean': float(offset + np.mean(fitted_centered[event])),
        'mean_residual': delta, 'sum_residual': float(np.sum(residual[event])),
        'side_mad': mad, 'side_rms': rms, 'slope_per_second': slope,
        'mad_displacement': delta / mad if mad > floor else None,
        'values': y.tolist(), 'baseline': (offset + fitted_centered).tolist(),
        'residual': residual.tolist(),
    }


def coupling(flux, auxiliary, side):
    """Single-field descriptive OLS trained ONLY on sideband residuals."""
    if flux['status'] != 'AVAILABLE' or auxiliary['status'] != 'AVAILABLE':
        return {'status': 'UNAVAILABLE_INPUT'}
    if (flux['side_rms'] <= flux['roundoff_floor'] or
            auxiliary['side_rms'] <= auxiliary['roundoff_floor']):
        return {'status': 'UNAVAILABLE_SCATTER'}
    f, a = np.array(flux['residual'])[side], np.array(auxiliary['residual'])[side]
    fa, aa, ff = float(f @ a), float(a @ a), float(f @ f)
    beta = fa / aa
    predicted = beta * auxiliary['mean_residual']
    return {'status': 'AVAILABLE', 'beta_electron_per_unit': beta,
            'side_correlation': fa / np.sqrt(aa * ff),
            'predicted_flux_mean_residual': predicted,
            'remaining_flux_mean_residual': flux['mean_residual'] - predicted,
            'predicted_fraction_of_flux_residual': (
                predicted / flux['mean_residual']
                if abs(flux['mean_residual']) > flux['roundoff_floor'] else None)}


def diagnose_context(table, start, duration):
    lo, hi = start - 14, start + duration + 14
    if lo < 0 or hi > len(table):
        raise ValueError('fixed context falls outside saved table')
    t = table[lo:hi]
    side = np.r_[np.arange(12), np.arange(16 + duration, 28 + duration)]
    event = np.arange(14, 14 + duration)
    times = (t['BJD_TIME'].astype(float) - float(table['BJD_TIME'][start])) * 86400.
    series = {}
    for name, unit in FIELDS.items():
        if name.startswith('OFFSET_'):
            axis = name[-1]
            values = t['CENTROID_' + axis].astype(float) - t['LOCATION_' + axis].astype(float)
        else:
            values = t[name].astype(float)
        if name == 'ROLL_ANGLE' and np.isfinite(values).all():
            values = unwrap_degrees(values)
        series[name] = {'unit': unit, **diagnose_series(times, values, side, event)}
    dx, dy = series['OFFSET_X'], series['OFFSET_Y']
    motion = (float(np.hypot(dx['mean_residual'], dy['mean_residual']))
              if dx['status'] == dy['status'] == 'AVAILABLE' else None)
    return {'context_start': lo, 'context_stop': hi,
            'side_indices': (side + lo).tolist(), 'event_indices': (event + lo).tolist(),
            'times_seconds': times.tolist(), 'series': series,
            'centroid_offset_residual_norm_pixels': motion,
            'couplings': {name: coupling(series['FLUX'], series[name], side)
                          for name in COUPLING_FIELDS}}
