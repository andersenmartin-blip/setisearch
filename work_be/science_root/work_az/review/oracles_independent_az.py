"""Independent saved-native QA arithmetic, with no detector imports.

This module never opens input files. Its caller must enforce prospective release.
Full-vector Neumaier accumulation uses at most one chunk of centers; scalar
math.fsum remains the independent reference for every saved fixed-center trace.
"""
from __future__ import annotations

import hashlib
import math
import numpy as np

WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
FULL_VECTOR_DRIFT_INDICES = (0, 279, 559, 838)
SUM_TOLERANCE = 5e-5
ESS_ATOL = 1e-4
ESS_RTOL = 5e-6
CHUNK_CENTERS = 65536


def sorted_median_f32(values):
    values=np.sort(np.asarray(values,dtype=np.float32))
    n=len(values)
    return np.float32(values[n//2]) if n%2 else np.float32(np.float32(values[n//2-1]+values[n//2])/np.float32(2.))


LAST_NORMALIZATION_REPORT={}

def normalize_independently(raw, block=4096):
    """Independent sorted anchors; shared np.interp allpixel replay plus scalar checks.

    np.interp and float64 rounding order are shared with the production method.
    Bounded pixel checks use independently written scalar interpolation. Exact
    block digests attest allpixel reconstruction, not an independent allpixel
    interpolation oracle.
    """
    global LAST_NORMALIZATION_REPORT
    from bisect import bisect_right
    if raw.ndim != 2 or raw.dtype != np.dtype('<f4') or raw.shape[0] < 2 or block != 4096:
        raise ValueError('Native little-endian float32 and4096block required')
    nr,nc=raw.shape
    starts=list(range(0,nc,block));stops=[min(lo+block,nc) for lo in starts]
    anchors=np.array([(lo+hi-1)/2 for lo,hi in zip(starts,stops)],dtype=np.float64)
    medians=np.empty((len(starts),nr),dtype=np.float32);scales=np.empty_like(medians)
    for bi,(lo,hi) in enumerate(zip(starts,stops)):
        for row in range(nr):
            values=np.asarray(raw[row,lo:hi])
            if not np.isfinite(values).all():raise ValueError('Nonfinite raw input')
            median=sorted_median_f32(values)
            scale=np.float32(sorted_median_f32(np.abs(values-median))*np.float32(1.4826))
            if not math.isfinite(float(scale)) or scale<=0:raise ValueError('Nonpositive scale')
            medians[bi,row]=median;scales[bi,row]=scale
    channels=np.arange(nc,dtype=np.float64);y=np.empty(raw.shape,dtype=np.float32)
    for row in range(nr):
        median=np.interp(channels,anchors,medians[:,row].astype(np.float64))
        scale=np.interp(channels,anchors,scales[:,row].astype(np.float64))
        y[row]=((raw[row].astype(np.float64)-median)/scale).astype(np.float32)
    if not np.isfinite(y).all():raise ValueError('Nonfinite normalized reconstruction')
    # Fixed before powers: first/last full halos; each interior block edge±1;
    # four pixels bracketing each half-integer block-center anchor.
    sample=set(range(min(block,nc)))|set(range(max(0,nc-block),nc))
    for edge in range(block,nc,block):sample.update([edge-1,edge,edge+1])
    for anchor in anchors:
        floor=math.floor(anchor);sample.update([floor-1,floor,floor+1,floor+2])
    sample=sorted(v for v in sample if 0<=v<nc)
    maximum_error=maximum_spacings=0.;equal=pixels=0
    nodes=anchors.tolist()
    for channel in sample:
        if channel<=nodes[0]:left=right=0
        elif channel>=nodes[-1]:left=right=len(nodes)-1
        else:left=bisect_right(nodes,float(channel))-1;right=left+1
        for row in range(nr):
            m=float(medians[left,row]);s=float(scales[left,row])
            if left!=right:
                d=nodes[right]-nodes[left];x=float(channel)-nodes[left]
                m=m+((float(medians[right,row])-m)/d)*x
                s=s+((float(scales[right,row])-s)/d)*x
            reference=np.float32((float(raw[row,channel])-m)/s)
            got=y[row,channel];difference=abs(float(reference)-float(got))
            tolerance=max(abs(float(np.spacing(reference))),float(np.nextafter(np.float32(0),np.float32(1))))
            if difference>tolerance:raise ValueError(('Scalar interpolation mismatch',row,channel,difference,tolerance))
            maximum_error=max(maximum_error,difference);maximum_spacings=max(maximum_spacings,difference/tolerance)
            equal+=int(reference==got);pixels+=1
    digests=np.array([np.frombuffer(hashlib.sha256(y[:,lo:hi].tobytes(order='C')).digest(),dtype=np.uint8) for lo,hi in zip(starts,stops)],dtype=np.uint8)
    LAST_NORMALIZATION_REPORT={'anchor_row_block_pairs':medians.size,'independent_anchor_method':'sorted float32 values/deviations with explicit midpoint average','sample_pixels':pixels,'sample_channel_count':len(sample),'maximum_scalar_pixel_error':maximum_error,'maximum_scalar_error_float32_spacings':maximum_spacings,'scalar_sample_equal_pixels':equal,'shared_allpixel_primitive':'np.interp and float64 subtract/divide then one float32 cast','independent_allpixel_interpolation_oracle':False,'normalized_blocks_digest_checked':len(starts)}
    return y,medians,scales,digests



def derive_grid(nrows, nchannels, dt, df, maxdrift=4.0, halo=4096):
    if nrows < 2 or nchannels <= 2 * halo or not all(map(math.isfinite, [dt, df, maxdrift])) or dt <= 0 or df == 0 or maxdrift <= 0:
        raise ValueError('Invalid native grid geometry')
    side = int(math.ceil(maxdrift * (nrows * dt) / abs(df)))
    rates = np.linspace(-maxdrift, maxdrift, 2 * side + 1, dtype=np.float64)
    times = (np.arange(nrows, dtype=np.float64) - (nrows - 1) / 2) * dt
    offsets = np.rint(rates[:, None] * times[None, :] / df).astype(np.int32)
    if int(np.abs(offsets).max()) + max(WIDTHS) // 2 > halo:
        raise ValueError('Frozen halo does not support full rate/width grid')
    centers = {w: np.arange(halo, nchannels - halo, s, dtype=np.int32) for w, s in zip(WIDTHS, STRIDES)}
    return rates, offsets, centers


def validate_request(y, offsets, centers, width):
    offsets, centers = np.asarray(offsets), np.asarray(centers)
    if y.ndim != 2 or y.dtype != np.float32 or width not in WIDTHS:
        raise ValueError('Normalized float32 matrix and supported width required')
    if offsets.shape != (len(y),) or offsets.dtype.kind not in 'iu' or centers.ndim != 1 or centers.dtype.kind not in 'iu':
        raise ValueError('Integer row offsets and centers required')
    half = width // 2
    if len(centers) and (int(centers.min()) + int(offsets.min()) - half < 0 or int(centers.max()) + int(offsets.max()) + half >= y.shape[1]):
        raise ValueError('Independent request outside stored support')
    return offsets, centers


def fsum_tracks(y, offsets, centers, width):
    """Literal row-then-width CPython math.fsum, no precomputed boxcars."""
    offsets, centers = validate_request(y, offsets, centers, width)
    half = width // 2
    result = np.empty(len(centers), dtype=np.float64)
    for ci, center in enumerate(centers):
        result[ci] = math.fsum(float(y[t, int(center) + int(off) + j])
                              for t, off in enumerate(offsets)
                              for j in range(-half, half + 1))
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite independent fsum')
    return result


def compensated_vector(y, offsets, centers, width, chunk_centers=CHUNK_CENTERS):
    """Independent explicit pixel Neumaier sums, chunked across centers.

    Never uses convolution, prefix sums, detector boxcars or detector track
    accumulation. This is not advertised as a formally proved arbitrary-input
    error bound or bit-identical math.fsum for all possible floating inputs.
    """
    offsets, centers = validate_request(y, offsets, centers, width)
    if not isinstance(chunk_centers, int) or chunk_centers <= 0:
        raise ValueError('Positive chunk size required')
    output = np.empty(len(centers), dtype=np.float64)
    half = width // 2
    for start in range(0, len(centers), chunk_centers):
        requested = centers[start:start + chunk_centers].astype(np.int64, copy=False)
        high = np.zeros(len(requested), dtype=np.float64)
        low = np.zeros_like(high)
        for ti, off in enumerate(offsets):
            base = requested + int(off)
            for j in range(-half, half + 1):
                value = y[ti, base + j].astype(np.float64)
                updated = high + value
                low += np.where(np.abs(high) >= np.abs(value), (high - updated) + value, (value - updated) + high)
                high = updated
        output[start:start + len(requested)] = np.where((low != 0) & np.isfinite(low), high + low, high)
    if not np.isfinite(output).all():
        raise ValueError('Nonfinite independent compensated sum')
    return output


def calibrate(values):
    values = np.asarray(values)
    if values.dtype != np.float64 or values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError('Finite nonempty float64 sum vector required')
    ordered=np.sort(values);n=len(ordered)
    center=float(ordered[n//2]) if n%2 else float((ordered[n//2-1]+ordered[n//2])/2.)
    deviations=np.sort(np.abs(values-center))
    mad=float(deviations[n//2]) if n%2 else float((deviations[n//2-1]+deviations[n//2])/2.)
    scale = float(1.4826 * mad)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Nonpositive independently reconstructed calibration')
    return np.array([center, scale], dtype=np.float64)


def original_template_requests(scopes, rates, templates, maxdrift=4.0):
    """Reproduce original S's specified topocentric frequency projection."""
    reference = scopes[0]
    requests = []
    for scope in scopes:
        gap = (scope['tref_midpoint_mjd'] - reference['tref_midpoint_mjd']) * 86400
        rows = []
        for ti, template in enumerate(templates):
            ri = int(np.argmin(np.abs(rates - template['drift_fraction'] * maxdrift)))
            frequency = reference['fch1_mhz'] + template['source_center'] * reference['df_hz'] / 1e6 + rates[ri] * gap / 1e6
            center = int(np.rint((frequency - scope['fch1_mhz']) * 1e6 / scope['df_hz']))
            rows.append({'original_template_index': ti, 'width_channels': template['width_channels'], 'drift_index': ri, 'native_center': center})
        requests.append(rows)
    return requests
