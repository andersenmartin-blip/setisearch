"""Deterministic AC continuous robust spectral normalization candidate.

Each native row retains the original float32 median and 1.4826*MAD estimate
in every nonoverlapping frequency block. Those coefficients are placed at
the actual block centers and linearly interpolated in float64. Endpoint
coefficients remain constant outside the first/last center. The normalized
matrix is rounded to float32 once, for unchanged downstream track scoring.

This module has no file loading, acquisition, threshold, selection or search
code. Continuity concerns the coefficient fields, not arbitrary raw spectra.
Qualification and signal-loss controls belong to a separately frozen plan.
"""
from __future__ import annotations

import hashlib
import numpy as np

VERSION = 'ac-native-f32-anchors-f64-linear-center-interpolation-v1'
DEFAULT_BLOCK_CHANNELS = 4096
MAD_FACTOR = np.float32(1.4826)


def _native_matrix(raw):
    x = np.asarray(raw)
    if x.ndim != 2 or x.dtype != np.dtype('<f4'):
        raise ValueError('Native little-endian float32 matrix required')
    if x.shape[0] < 2 or x.shape[1] < 2:
        raise ValueError('At least two time rows and two frequency channels required')
    return x


def _block_size(block):
    if isinstance(block, (bool, np.bool_)) or not isinstance(block, (int, np.integer)) or block <= 0:
        raise ValueError('Positive integer block size required')
    return int(block)


def fit_anchors(raw, block=DEFAULT_BLOCK_CHANNELS):
    """Return unchanged original float32 robust coefficients and pixel centers.

Medians and scales have [block, time-row] shape. The final partial block uses
its actual pixel center and statistics. Any nonfinite input or nonpositive
MAD is fatal; no epsilon replacement, masking, clipping or adaptive merging
is performed. Input bytes are never modified.
"""
    x = _native_matrix(raw)
    block = _block_size(block)
    nr, nc = x.shape
    starts = np.arange(0, nc, block, dtype=np.int64)
    stops = np.minimum(starts + block, nc).astype(np.int64)
    centers = (starts.astype(np.float64) + stops.astype(np.float64) - 1.0) / 2.0
    medians = np.empty((len(starts), nr), dtype=np.float32)
    scales = np.empty_like(medians)
    for index, (lo, hi) in enumerate(zip(starts, stops, strict=True)):
        values = x[:, int(lo):int(hi)]
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite native power')
        # These three operations deliberately match the original normalization.
        center = np.median(values, axis=1)
        deviations = np.abs(values - center[:, None])
        scale = np.median(deviations, axis=1) * MAD_FACTOR
        if center.dtype != np.float32 or scale.dtype != np.float32:
            raise TypeError('Original robust anchor arithmetic must remain float32')
        if not np.isfinite(center).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
            raise ValueError('Nonpositive or nonfinite spectral MAD scale')
        medians[index] = center
        scales[index] = scale
    return {
        'block_start': starts,
        'block_stop': stops,
        'anchor_channel': centers,
        'block_median': medians,
        'block_MAD_scale': scales,
    }


def _validated_anchors(anchors):
    required = {'block_start', 'block_stop', 'anchor_channel', 'block_median', 'block_MAD_scale'}
    if not required <= set(anchors):
        raise ValueError('Incomplete robust anchor record')
    starts = np.asarray(anchors['block_start'])
    stops = np.asarray(anchors['block_stop'])
    centers = np.asarray(anchors['anchor_channel'])
    medians = np.asarray(anchors['block_median'])
    scales = np.asarray(anchors['block_MAD_scale'])
    nb = len(centers) if centers.ndim == 1 else 0
    if nb < 1 or starts.shape != (nb,) or stops.shape != (nb,):
        raise ValueError('Invalid robust anchor geometry')
    if starts.dtype != np.dtype('int64') or stops.dtype != np.dtype('int64') or centers.dtype != np.dtype('float64'):
        raise TypeError('Anchor geometry must use int64 blocks and float64 centers')
    if medians.ndim != 2 or medians.shape[0] != nb or medians.shape[1] < 2 or scales.shape != medians.shape:
        raise ValueError('Invalid robust anchor coefficient shape')
    if medians.dtype != np.float32 or scales.dtype != np.float32:
        raise TypeError('Robust anchor coefficients must remain float32')
    if starts[0] != 0 or np.any(stops <= starts) or not np.array_equal(starts[1:], stops[:-1]):
        raise ValueError('Robust anchor blocks must be positive, contiguous and start at zero')
    expected = (starts.astype(np.float64) + stops.astype(np.float64) - 1.0) / 2.0
    if not np.array_equal(centers, expected) or not np.isfinite(centers).all() or np.any(np.diff(centers) <= 0):
        raise ValueError('Robust anchors must use increasing actual block centers')
    if not np.isfinite(medians).all() or not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError('Robust anchor scales must be finite and positive')
    return centers, medians, scales


def interpolate_coefficients(anchors, channels):
    """Evaluate continuous median/scale fields at finite channel coordinates.

Returns two float64 arrays with [time-row, queried-channel] shape. Linear
interpolation uses convex weights between anchors; extrapolation is constant.
It creates no mandatory step at any original block edge. Slope changes at
anchor centers and endpoint joins are retained and disclosed.
"""
    centers, medians, scales = _validated_anchors(anchors)
    channels = np.asarray(channels, dtype=np.float64)
    if channels.ndim != 1 or not np.isfinite(channels).all():
        raise ValueError('Finite one-dimensional channel coordinates required')
    m = np.empty((medians.shape[1], len(channels)), dtype=np.float64)
    s = np.empty_like(m)
    for row in range(medians.shape[1]):
        m[row] = np.interp(channels, centers, medians[:, row].astype(np.float64))
        s[row] = np.interp(channels, centers, scales[:, row].astype(np.float64))
    if not np.isfinite(m).all() or not np.isfinite(s).all() or np.any(s <= 0):
        raise ValueError('Invalid interpolated robust coefficient field')
    return m, s


def normalize(raw, block=DEFAULT_BLOCK_CHANNELS):
    """Normalize every stored channel using continuous interpolated anchors.

The numerical change is confined to normalization. The output is finite
float32, suitable for the existing unchanged boxcar/track-sum/ESS methods.
This function loops over time rows to avoid materializing two full float64
coefficient matrices. Audit digests cover all normalized pixels in original
frequency blocks; anchors and block geometry are returned for independent
reconstruction. Statistics include stored halo channels as before.
"""
    x = _native_matrix(raw)
    anchors = fit_anchors(x, block)
    centers, medians, scales = _validated_anchors(anchors)
    channels = np.arange(x.shape[1], dtype=np.float64)
    y = np.empty(x.shape, dtype=np.float32)
    for row in range(x.shape[0]):
        m = np.interp(channels, centers, medians[:, row].astype(np.float64))
        s = np.interp(channels, centers, scales[:, row].astype(np.float64))
        if not np.isfinite(m).all() or not np.isfinite(s).all() or np.any(s <= 0):
            raise ValueError('Invalid interpolated robust coefficient field')
        normalized = (x[row].astype(np.float64) - m) / s
        y[row] = normalized.astype(np.float32)
        if not np.isfinite(y[row]).all():
            raise ValueError('Nonfinite normalized power')
    digests = np.empty((len(anchors['block_start']), 32), dtype=np.uint8)
    for index, (lo, hi) in enumerate(zip(anchors['block_start'], anchors['block_stop'], strict=True)):
        payload = y[:, int(lo):int(hi)].tobytes(order='C')
        digests[index] = np.frombuffer(hashlib.sha256(payload).digest(), dtype=np.uint8)
    return y, {**anchors, 'normalized_block_sha256': digests}
