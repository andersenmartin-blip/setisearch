"""LS7I: one fixed outside-event predictor, with nested held-background errors.

This module accepts observable arrays and unlabeled native training records.
Injection recipes and archived decisions belong exclusively in the harness.
Scores are descriptive fit statistics, not calibrated false-alarm probabilities.
"""
from itertools import combinations

import numpy as np


def observe(cube, aperture, start, stop):
    """Separate outside-event features from the event response, in local units.

    Neither reference, scale nor x reads [start-5:stop+5]. The event response
    y is deliberately separate and must never be supplied to predict().
    """
    if not (60 <= start < stop <= len(cube)-60):
        raise ValueError('incomplete protected context')
    left, right = cube[start-60:start-5], cube[stop+5:stop+60]
    side = np.concatenate([left, right])
    if not np.all(np.isfinite(side[:, aperture])):
        raise ValueError('nonfinite aperture sidebands')
    reference = np.median(side, axis=0)
    differences = np.concatenate([np.diff(z[:, aperture].sum(axis=1)) for z in [left, right]])
    sigma = float(1.482602218505602*np.median(abs(differences-np.median(differences)))/np.sqrt(2.))
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError('degenerate observable sideband scale')
    near = [cube[start-15:start-5], cube[stop+5:stop+15]]
    x = np.concatenate([(z[:, aperture].mean(axis=0)-reference[aperture])/sigma for z in near])
    y = (cube[start:stop, aperture].mean(axis=0)-reference[aperture])/sigma
    if not np.all(np.isfinite(y)):
        raise ValueError('nonfinite event')
    return {'x': x, 'y': y, 'sigma': sigma, 'reference': reference}


def ridge_fit(records, excluded, width, strength=1.):
    chosen = [r for r in records if r['anchor'] not in excluded and r['width'] == width]
    x, y = [np.asarray([r[key] for r in chosen], dtype=float) for key in ['x', 'y']]
    if len(chosen) < 3 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or strength <= 0:
        raise ValueError('invalid regression training')
    mx, my = x.mean(axis=0), y.mean(axis=0)
    xc, yc = x-mx, y-my
    cxx, cxy = xc.T@xc/(len(x)-1), xc.T@yc/(len(x)-1)
    penalty = float(strength*np.trace(cxx)/x.shape[1])
    if penalty <= 0:
        raise ValueError('zero feature variance')
    beta = np.linalg.solve(cxx+penalty*np.eye(x.shape[1]), cxy)
    return {'excluded_anchors': sorted(excluded), 'width': width,
            'training_ids': [r['sample_id'] for r in chosen],
            'training_anchors': sorted({r['anchor'] for r in chosen}),
            'samples': len(chosen), 'ridge_strength': strength, 'ridge_penalty': penalty,
            'x_mean': mx.tolist(), 'y_mean': my.tolist(), 'beta': beta.tolist()}


def predict(x, model, method='conditional'):
    mean = np.asarray(model['y_mean'])
    if method == 'static':
        return mean.copy()
    if method != 'conditional':
        raise ValueError('unknown fixed method')
    return mean+(np.asarray(x)-model['x_mean'])@np.asarray(model['beta'])


def residual_covariance(residuals, shrinkage=.05):
    empirical = np.cov(np.asarray(residuals), rowvar=False, ddof=1)
    floor = float(1e-10*np.trace(empirical)/len(empirical))
    if not floor > 0 or not 0 < shrinkage <= 1:
        raise ValueError('degenerate error covariance')
    covariance = (1-shrinkage)*empirical+shrinkage*np.diag(np.diag(empirical))+floor*np.eye(len(empirical))
    np.linalg.cholesky(covariance)
    return {'empirical_covariance': empirical.tolist(), 'shrinkage': shrinkage,
            'floor': floor, 'covariance': covariance.tolist(),
            'eigenvalues': np.linalg.eigvalsh(covariance).tolist()}


def build_folds(records, widths, strength=1., shrinkage=.05):
    """Outer anchor excluded throughout; covariance uses inner held-anchor errors.

    Final predictors use nine backgrounds. Each calibration prediction uses
    eight, never the outer anchor or the sample's own background.
    """
    anchors = sorted({r['anchor'] for r in records})
    models, folds = {}, []
    for width in widths:
        for excluded in [(a,) for a in anchors]+list(combinations(anchors, 2)):
            key = f'w{width}/exclude_'+','.join(str(a) for a in excluded)
            models[key] = {'model_id': key, **ridge_fit(records, excluded, width, strength)}
        for anchor in anchors:
            selected = [r for r in records if r['anchor'] != anchor and r['width'] == width]
            errors = {m: [] for m in ['conditional', 'static']}
            inner_ids = []
            for r in selected:
                key = f'w{width}/exclude_'+','.join(str(a) for a in sorted([anchor, r['anchor']]))
                inner_ids.append(key)
                for method in errors:
                    errors[method].append((np.asarray(r['y'])-predict(r['x'], models[key], method)).tolist())
            folds.append({'fold_id': f'a{anchor:02d}/w{width}', 'excluded_anchor': anchor, 'width': width,
                          'model_id': f'w{width}/exclude_{anchor}',
                          'calibration_ids': [r['sample_id'] for r in selected],
                          'calibration_models': inner_ids,
                          'methods': {m: {'residuals': e, **residual_covariance(e, shrinkage)} for m, e in errors.items()}})
    return {'models': list(models.values()), 'folds': folds}


def decision(star, nuisance, screened, confounded, cfg):
    margin = nuisance['objective']-star['objective']
    gates = {'temporal_screen': bool(screened),
             'source_score': bool(star['amplitude_noise_score'] >= cfg['source_score_min']),
             'weighted_residual': bool(star['chi2']/star['residual_dof'] <= cfg['reduced_chi2_max']),
             'nuisance_margin': bool(margin >= cfg['margin'])}
    accepted = all(gates.values())
    path = next((name for name, ok in gates.items() if not ok), 'confounded' if confounded else 'recovered')
    return {'accepted': accepted, 'recovered': bool(accepted and not confounded),
            'nuisance_preferred_acceptance': bool(accepted and margin < 0),
            'gates': gates, 'recovery_path': path, 'margin': float(margin)}


def common_energy(vector, static_covariance):
    """Use one static metric for both predictors, projecting out uniform flux."""
    w = np.linalg.inv(static_covariance)
    one = np.ones(len(vector)); wone = w@one
    q = w-np.outer(wone, wone)/(one@wone)
    return float(np.asarray(vector)@q@np.asarray(vector))
