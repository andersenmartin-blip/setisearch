"""Explicit fixed-mask flux moments and conditional uncertainty diagnostics.

These are measurements, not qualified pointing estimates. Negative calibrated
pixels are retained. No interpolation, clipping, quality waiver or native fit.
"""
import numpy as np


def moments(flux, error, pixel_xy):
    f, e, xy = map(lambda x: np.asarray(x, dtype=float), (flux, error, pixel_xy))
    if f.shape != e.shape or xy.shape != (f.shape[-1], 2) or not np.isfinite(xy).all():
        raise ValueError('matching pixel flux/errors and finite fixed x/y coordinates required')
    total = f.sum(axis=-1)
    valid = np.isfinite(f).all(-1) & np.isfinite(e).all(-1) & (e > 0).all(-1) & (total > 0)
    # Local coordinates limit cancellation in detector coordinates near 2000.
    origin = xy[0]
    with np.errstate(invalid='ignore', divide='ignore'):
        center = np.einsum('...p,pk->...k', f, xy-origin)/total[..., None] + origin
        gradient = (xy-center[..., None, :])/total[..., None, None]
        covariance = np.einsum('...pi,...pj,...p->...ij', gradient, gradient, e*e)
        sigma = np.sqrt(np.diagonal(covariance, axis1=-2, axis2=-1))
        correlation_unknown_bound = np.einsum('...p,...pi->...i', e, abs(gradient))
        # Rounding interval for a pre-export binary32 flux, with normal/subnormal
        # spacing treated symmetrically by taking the larger adjacent spacing.
        ff = f.astype(np.float32)
        up = np.nextafter(ff, np.float32(np.inf)).astype(float)-f
        down = f-np.nextafter(ff, np.float32(-np.inf)).astype(float)
        rounding = .5*np.maximum(up, down)
        denominator = total-rounding.sum(-1)
        quantization_bound = (np.einsum('...p,...pi->...i', rounding, abs(xy-center[..., None, :]))
                              / denominator[..., None] + 2e-11)
    valid &= np.isfinite(center).all(-1) & (denominator > 0)
    def masked(value):
        return np.where(valid.reshape(valid.shape+(1,)*(value.ndim-valid.ndim)), value, np.nan)
    return {'valid': valid, 'total': masked(total), 'center_xy': masked(center),
            'covariance_xy': masked(covariance), 'sigma_xy': masked(sigma),
            'correlation_unknown_bound_xy': masked(correlation_unknown_bound),
            'binary32_centroid_bound_xy': masked(quantization_bound)}


def additive_shift(flux, addition, pixel_xy):
    """Exact finite-change identity, including signed/duplicate CR corrections."""
    f, d, xy = map(lambda x: np.asarray(x, dtype=float), (flux, addition, pixel_xy))
    if f.shape != d.shape or xy.shape != (f.shape[-1], 2):
        raise ValueError('matching fixed-mask arrays required')
    s = f.sum(-1)
    with np.errstate(invalid='ignore', divide='ignore'):
        c = np.einsum('...p,pk->...k', f, xy-xy[0])/s[..., None]+xy[0]
        return (np.einsum('...p,...pk->...k', d, xy-c[..., None, :])
                / (s+d.sum(-1))[..., None])


def cr_additions(cadence, records, origin_xy, shape_yx):
    """Map only selected sparse records. Outside-context payload is not decoded."""
    cadence = np.asarray(cadence)
    ids = cadence.ravel()
    if len(set(ids.tolist())) != len(ids):
        raise ValueError('unique selected cadences required')
    lookup = {int(c): i for i, c in enumerate(ids)}
    rows, cols = shape_yx
    cube = np.zeros((len(ids), rows, cols))
    counts = np.zeros_like(cube, dtype=np.int32)
    for c, x, y, value in records:
        if int(c) not in lookup:
            raise ValueError('cosmic-ray record outside selected contexts')
        xx, yy = int(x-origin_xy[0]), int(y-origin_xy[1])
        if not (0 <= xx < cols and 0 <= yy < rows and np.isfinite(value)):
            raise ValueError('invalid cosmic-ray coordinate or value')
        i = lookup[int(c)]
        cube[i, yy, xx] += value
        counts[i, yy, xx] += 1
    return cube.reshape(cadence.shape+(rows, cols)), counts.reshape(cadence.shape+(rows, cols))
