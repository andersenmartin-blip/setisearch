"""LS7O affine motion from six distinct stars; no target photons or POS_CORR.

Moment-centroid displacement is an explicit unit-response approximation.
Reported errors condition on the fitted sideband centers and weights; they
exclude temporal/cross-star covariance and centroid-to-PRF response error.
"""
import numpy as np


def affine_reference_motion(centroids_xy, errors_xy, quality, design, side, selected):
    """Arrays are (6,401,2), quality (6,401), design (6,3)."""
    c, e, q, x = map(np.asarray, (centroids_xy, errors_xy, quality, design))
    side, selected = np.asarray(side), np.asarray(selected)
    if c.shape != (6,401,2) or e.shape != c.shape or q.shape != (6,401) or x.shape != (6,3):
        raise ValueError('wrong six-reference shape')
    if not np.array_equal(x[:,0], np.ones(6)):
        raise ValueError('design must be centered on the science target')
    if not np.isin(side,selected).all():
        raise ValueError('selected rows must include sidebands')
    if not (np.isfinite(c[:,selected]).all() and np.isfinite(e[:,selected]).all() and
            (e[:,selected]>0).all() and (q[:,selected]==0).all()):
        raise ValueError('all six references require finite quality-zero selected rows')
    center = np.median(c[:,side], axis=1)
    sigma = np.median(e[:,side], axis=1)
    positions = np.full((401,2), np.nan)
    formal_sigma = np.full((401,2), np.nan)
    operators, conditions, scatter, coefficients = [], [], [], []
    for axis in range(2):
        weighted = x/sigma[:,axis,None]
        singular = np.linalg.svd(weighted, compute_uv=False)
        rank = int(np.sum(singular>1e-10*singular[0]))
        condition = float(singular[0]/singular[-1]) if singular[-1]>0 else np.inf
        if rank != 3 or condition>1e8:
            raise ValueError('reference affine geometry is rank deficient or ill conditioned')
        operator = np.linalg.pinv(weighted,rcond=1e-10)/sigma[:,axis][None,:]
        delta = c[:,selected,axis]-center[:,axis,None]
        beta = operator@delta
        positions[selected,axis] = beta[0]
        formal_sigma[selected,axis] = np.sqrt(np.sum((operator[0,:,None]*e[:,selected,axis])**2,axis=0))
        residual = delta-x@beta
        scatter.append(float(np.mean(np.sum((residual/e[:,selected,axis])**2,axis=0)/3)))
        operators.append(operator)
        conditions.append(condition)
        coefficients.append(beta.T)
    if np.max(np.abs(positions[selected]))>.25:
        raise ValueError('reference motion exceeds frozen quarter-pixel domain')
    return {'positions_xy':positions, 'formal_sigma_xy':formal_sigma,
            'centers_xy':center, 'sideband_median_error_xy':sigma,
            'operators_xy':np.array(operators), 'conditions_xy':conditions,
            'reference_residual_mean_chi2_per_3_dof_xy':scatter,
            'affine_coefficients_xy':np.stack(coefficients,axis=-1)}
