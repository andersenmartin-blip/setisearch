"""LS7J observable scene-motion / off-aperture feasibility experiment.

No new ridge, source fit, covariance calibration, event selection or detector
decision. The simultaneous off-aperture estimate protects a declared family
of full-stamp source footprints by explicit linear projection.
"""
import numpy as np
from scipy.ndimage import shift, gaussian_filter

from .tess_background import observe
from .light_sail_tess_v2 import pointing_delta


def footprint(reference, aperture, displacement=(0., 0.), blur=0.):
    """Observable scene proxy, not a calibrated target PRF.

    Subtract the median border, clip negative values, retain outside-aperture
    wings, optionally broaden, shift, then normalize only its aperture sum.
    The proxy may contain neighboring stars and residual background.
    """
    reference = np.asarray(reference, dtype=float)
    border = np.zeros(reference.shape, bool)
    border[[0, -1], :] = True; border[:, [0, -1]] = True
    p = np.maximum(reference-np.median(reference[border]), 0.)
    if blur:
        p = gaussian_filter(p, sigma=blur, mode='constant', cval=0., truncate=4.)
    p = shift(p, displacement, order=1, mode='constant', cval=0., prefilter=False)
    norm = float(p[aperture].sum())
    if not np.all(np.isfinite(p)) or norm <= 0:
        raise ValueError('invalid full-stamp footprint')
    return p/norm


def prepare(cube, aperture, start, stop, shifts, rank_tolerance=1e-10):
    """Learn the local correction operator from protected sidebands only."""
    aperture = np.asarray(aperture, dtype=bool)
    obs = observe(cube, aperture, start, stop)
    if cube.shape[1:] != (11, 11) or not np.all(np.isfinite(cube)):
        raise ValueError('incomplete finite stamp')
    outside = ~aperture
    side = [cube[start-60:start-5], cube[stop+5:stop+60]]
    diff = np.concatenate([np.diff(s[:, outside], axis=0) for s in side])
    noise = 1.482602218505602*np.median(abs(diff-np.median(diff, axis=0)), axis=0)/np.sqrt(2.)
    variance = noise**2
    positive = variance[variance > 0]
    if not len(positive):
        raise ValueError('zero off-aperture noise')
    floor = float(1e-6*np.median(positive))
    sigma = np.sqrt(np.maximum(variance, floor))
    y, x = np.indices(aperture.shape, dtype=float)
    plane = np.stack([np.ones_like(x), (y-5.)/5., (x-5.)/5.], axis=-1)
    profiles = np.stack([footprint(obs['reference'], aperture, s) for s in shifts])
    protected = profiles[:, outside].T/sigma[:, None]
    u, singular, _ = np.linalg.svd(protected, full_matrices=False)
    rank = int(np.count_nonzero(singular > rank_tolerance*singular[0])) if singular[0] > 0 else 0
    basis = u[:, :rank]
    weighted_plane = plane[outside]/sigma[:, None]
    projected = weighted_plane-basis@(basis.T@weighted_plane)
    values = np.linalg.svd(projected, compute_uv=False)
    plane_rank = int(np.count_nonzero(values > rank_tolerance*values[0])) if values[0] > 0 else 0
    condition = float(values[0]/values[-1]) if values[-1] > 0 else None
    valid = bool(plane_rank == 3 and condition is not None and condition <= 1e8)
    # Map unwhitened outside-pixel differences to plane coefficients. Since
    # projected is orthogonal to the source subspace, its pseudoinverse also
    # annihilates that subspace; an extra subtraction is unnecessary.
    operator = np.linalg.pinv(projected, rcond=rank_tolerance)/sigma[None, :] if valid else None
    return {'start': start, 'stop': stop, 'aperture': aperture, 'outside': outside,
            'reference': obs['reference'], 'sigma': obs['sigma'], 'plane': plane,
            'profiles': profiles, 'outside_noise': sigma, 'outside_variance_floor': floor,
            'floored_pixels': int(np.sum(variance < floor)), 'protected_rank': rank,
            'protected_singular_values': singular, 'plane_rank': plane_rank,
            'plane_singular_values': values, 'plane_condition': condition,
            'valid': valid, 'operator': operator}


def motion(positions_yx, reference, start, stop):
    selected = np.r_[start-60:start-5, start:stop, stop+5:stop+60]
    if positions_yx.shape != (401, 2) or not np.all(np.isfinite(positions_yx[selected])):
        return None, None
    side = np.concatenate([positions_yx[start-60:start-5], positions_yx[stop+5:stop+60]])
    displacement = positions_yx[start:stop].mean(axis=0)-np.median(side, axis=0)
    return pointing_delta(reference, displacement), displacement


def predict(delta, prepared, motion_image):
    """Only simultaneous outside pixels enter the plane coefficients."""
    if not prepared['valid']:
        return {'plane': None, 'motion': motion_image, 'combined': None}, {}
    basis, outside, operator = prepared['plane'], prepared['outside'], prepared['operator']
    beta = operator@np.asarray(delta)[outside]
    predictions = {'plane': basis@beta, 'motion': motion_image, 'combined': None}
    coefficients = {'plane': beta, 'combined': None}
    if motion_image is not None:
        joint_beta = operator@(np.asarray(delta)-motion_image)[outside]
        predictions['combined'] = motion_image+basis@joint_beta
        coefficients['combined'] = joint_beta
    return predictions, coefficients


def response_metrics(expected, actual):
    denominator = float(np.dot(expected, expected))
    if denominator <= 0:
        return None
    return {'gain': float(np.dot(expected, actual)/denominator),
            'relative_distortion': float(np.linalg.norm(actual-expected)/np.sqrt(denominator))}


def aperture_centroid(image, aperture):
    y, x = np.indices(aperture.shape, dtype=float)
    values = np.asarray(image)[aperture]
    total = float(values.sum())
    if not np.all(np.isfinite(values)) or total <= 0:
        return None
    return np.array([np.dot(values, y[aperture]), np.dot(values, x[aperture])])/total
