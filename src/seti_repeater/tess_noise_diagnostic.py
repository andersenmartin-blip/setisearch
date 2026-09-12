"""Closed-data noise accounting; never creates detection decisions."""
import numpy as np

MAD_NORMAL = 1.482602218505602


def sideband_differences(parts, width=1):
    """Adjacent nonoverlapping block-mean differences within each sideband.

    The tail shorter than ``width`` is counted and unused for that diagnostic.
    No difference bridges an event gap or two separate sidebands.
    """
    if not isinstance(width, int) or width < 1:
        raise ValueError("positive integer block width required")
    differences, tails, blocks = [], [], []
    for part in parts:
        x = np.asarray(part, dtype=float)
        if x.ndim != 2 or not np.all(np.isfinite(x)):
            raise ValueError("finite sample-by-pixel sidebands required")
        count = len(x) // width
        if count < 2:
            raise ValueError("each sideband needs at least two blocks")
        means = x[:count*width].reshape(count, width, x.shape[1]).mean(axis=1)
        differences.append(np.diff(means, axis=0))
        tails.append(len(x) % width)
        blocks.append(count)
    return np.concatenate(differences), {"blocks_per_side": blocks, "unused_tail_samples_per_side": tails}


def mad_scale(differences):
    d = np.asarray(differences, dtype=float)
    return MAD_NORMAL*np.median(np.abs(d-np.median(d, axis=0)), axis=0)/np.sqrt(2)


def ratio(numerator, denominator):
    return float(numerator/denominator) if denominator > 0 else None


def covariance_accounting(differences):
    """Exact sample-covariance identity for first differences divided by sqrt(2).

    C = cov(d)/2 is a difference-domain diagnostic. It is not an assertion of
    white temporal noise or a covariance for the event-minus-median estimator.
    """
    d = np.asarray(differences, dtype=float)
    if d.ndim != 2 or len(d) < 2 or not np.all(np.isfinite(d)):
        raise ValueError("at least two finite difference vectors required")
    centered = d-d.mean(axis=0)
    covariance = centered.T @ centered / (2*(len(d)-1))
    diagonal = float(np.trace(covariance))
    projected = float(covariance.sum())
    # Independent scalar path, including sum before centering.
    scalar = float(np.var(d.sum(axis=1), ddof=1)/2)
    tolerance = 1e-10*max(diagonal, scalar, 1.)
    if abs(projected-scalar) > tolerance:
        raise ArithmeticError("aperture covariance projection identity failed")
    return {"covariance": covariance.tolist(), "difference_vectors": len(d),
            "pixel_count": d.shape[1], "diagonal_variance": diagonal,
            "cross_variance": projected-diagonal, "projected_variance": projected,
            "scalar_variance": scalar, "identity_absolute_error": abs(projected-scalar),
            "covariance_sum_to_diagonal_variance_ratio": ratio(projected, diagonal),
            "diagonal_to_projected_sigma_ratio": ratio(np.sqrt(diagonal), np.sqrt(max(scalar, 0.))),
            "aperture_difference_mad_sigma": float(mad_scale(d.sum(axis=1))),
            "quadrature_pixel_mad_sigma": float(np.linalg.norm(mad_scale(d)))}


def decompose_noise(restored_parts, corrected_parts, error_parts, aperture, run_sigma):
    """Use the exact LS7C sidebands and archived errors; keep all differences."""
    if len(restored_parts) != 2 or len(corrected_parts) != 2 or len(error_parts) != 2:
        raise ValueError("exactly two sidebands required")
    ap = np.asarray(aperture, dtype=bool)
    errors = np.concatenate(error_parts)
    if not np.all(np.isfinite(errors)) or np.any(errors <= 0) or run_sigma <= 0:
        raise ValueError("invalid supplied or run noise")
    restored_d, layout = sideband_differences(restored_parts)
    corrected_d, corrected_layout = sideband_differences(corrected_parts)
    if layout != corrected_layout or errors.shape[1] != len(ap):
        raise ValueError("mismatched sideband dimensions")
    supplied = np.median(errors, axis=0)
    empirical = mad_scale(restored_d)
    spatial = np.maximum(supplied, empirical)
    q_spatial = float(np.linalg.norm(spatial[ap]))
    q_supplied = float(np.linalg.norm(supplied[ap]))
    q_empirical = float(np.linalg.norm(empirical[ap]))
    restored = covariance_accounting(restored_d[:, ap])
    corrected = covariance_accounting(corrected_d[:, ap])
    local_sigma = restored["aperture_difference_mad_sigma"]
    factors = {"archived_error_floor": ratio(q_spatial, q_empirical),
               "marginal_mad_to_aperture_mad": ratio(q_empirical, local_sigma),
               "local_to_run_aperture_mad": ratio(local_sigma, run_sigma)}
    lhs = q_spatial/run_sigma
    rhs = float(np.prod(list(factors.values()))) if all(v is not None for v in factors.values()) else None
    if rhs is not None and not np.isclose(lhs, rhs, rtol=1e-12, atol=1e-12):
        raise ArithmeticError("noise-ratio factorization failed")
    scales = []
    for width in (1, 2, 3, 5):
        r_d, r_layout = sideband_differences(restored_parts, width)
        c_d, c_layout = sideband_differences(corrected_parts, width)
        scales.append({"width_samples": width, **r_layout, "difference_vectors": len(r_d),
                       "restored_aperture_mad_sigma": float(mad_scale(r_d[:, ap].sum(axis=1))),
                       "corrected_aperture_mad_sigma": float(mad_scale(c_d[:, ap].sum(axis=1)))})
    return {"run_aperture_mad_sigma": float(run_sigma),
            "quadrature_ls7c_sigma": q_spatial, "quadrature_supplied_sigma": q_supplied,
            "quadrature_empirical_sigma": q_empirical,
            "quadrature_to_run_sigma_ratio": lhs, "multiplicative_factors": factors,
            "factorization_absolute_error": None if rhs is None else abs(lhs-rhs),
            "supplied_dominant_aperture_pixels": int(np.count_nonzero(supplied[ap] >= empirical[ap])),
            "supplied_dominant_stamp_pixels": int(np.count_nonzero(supplied >= empirical)),
            "pixel_supplied_sigma": supplied.tolist(), "pixel_empirical_sigma": empirical.tolist(),
            "restored": restored, "corrected": corrected, "block_scales": scales,
            "full_stamp_covariance_rank_upper_bound": min(len(restored_d)-1, len(ap)),
            "valid_stamp_pixels": len(ap)}
