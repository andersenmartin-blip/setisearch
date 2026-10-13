#!/usr/bin/env python3
"""Prospective NumPy-only kernels for the original12096 prefix arithmetic.

This is a code proposal, not an admitted scientific runner. Its only command
is --check-only. It opens no observation/map arrays and performs no numerical
queries at import or command invocation. A separately frozen GO runner may
call the kernels on producer-preserved original frames after admission.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

ROWS, FRAME, CORE, HALO = 16, 12096, 4096, 4000
REQUIRED_NUMPY = '2.3.5'
WIDTHS = (1, 3)
DRIFT_TILE, CARRIER_TILE = 16, 512
DC = (178782208, 179830784, 180879360)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def original_z_from_saved_terms(raw_frame, original_normalization, np):
    """Reconstruct all original501-nearest positions, retaining stored terms.

    NumPy partition selects the single middle value of each odd501 window;
    no averaging or changed normalization is introduced. Before claiming an
    exact replay, the admitted runner must reconcile original cached winners
    bit-for-bit and retain all discrepancies. If an authenticated original z
    frame is also provided, compare every z bit before hypothesis evaluation.
    """
    require(np.__version__ == REQUIRED_NUMPY, 'Exact original NumPy runtime required')
    require(raw_frame.shape == (ROWS, FRAME) and raw_frame.dtype.str == '<f4', 'Complete original rawfloat32 frame required')
    require(np.isfinite(raw_frame).all() and (raw_frame >= 0).all(), 'Invalid original power values')
    require(original_normalization['normalization_unmasked_counts'] == [CORE] * ROWS, 'Original full16 unmasked4096 normalization required')
    p = np.asarray(raw_frame, dtype=np.float64)
    level = np.asarray(original_normalization['row_power_median'], dtype=np.float64)
    location = np.asarray(original_normalization['row_winsorized_residual_location'], dtype=np.float64)
    scale = np.asarray(original_normalization['row_residual_MAD_scale'], dtype=np.float64)
    require(all(v.shape == (ROWS,) and np.isfinite(v).all() for v in (level, location, scale)), 'Original16-row terms required')
    require((level > 0).all() and (scale > 0).all(), 'Invalid original row level/scale')
    normalized = p / level[:, None]
    filtered = np.empty_like(normalized)
    for row in range(ROWS):
        padded = np.pad(normalized[row], (250, 250), mode='edge')
        windows = np.lib.stride_tricks.sliding_window_view(padded, 501)
        for first in range(0, FRAME, 512):
            last = min(first + 512, FRAME)
            filtered[row, first:last] = np.partition(windows[first:last], 250, axis=1)[:, 250]
    residual = normalized - filtered
    return (residual - location[:, None]) / scale[:, None]


def original_prefix_boxes(z, original_mask, np):
    """Mirror original detector._box_arrays from the complete frame leftedge."""
    require(np.__version__ == REQUIRED_NUMPY, 'Exact original NumPy runtime required')
    require(z.shape == (ROWS, FRAME) and z.dtype.str == '<f8', 'Complete original zfloat64 frame required')
    require(original_mask.shape == z.shape and original_mask.dtype.kind == 'b', 'Original mask shape/type required')
    prefix = np.zeros((z.shape[0], z.shape[1] + 1), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(z, axis=1, dtype=np.float64)
    bad = np.zeros(prefix.shape, dtype=np.int32)
    bad[:, 1:] = np.cumsum(~original_mask, axis=1, dtype=np.int32)
    boxes = {width: (prefix[:, width:] - prefix[:, :-width],
                     (bad[:, width:] - bad[:, :-width]) == 0) for width in WIDTHS}
    return boxes


def original_score_tile(boxes, base, times, df_hz, drifts, width, source_channel0, np):
    """Mirror the original sequential row additions and one final division."""
    box, unmasked = boxes[width]
    score = np.zeros((drifts.size, base.size), dtype=np.float64)
    valid = np.ones(score.shape, dtype=bool)
    touches_DC = np.zeros(score.shape, dtype=bool)
    radius = width // 2
    for row, time in enumerate(times):
        absolute = np.rint(base[None, :] + drifts[:, None] * time / df_hz).astype(np.int64)
        index = absolute - source_channel0 - radius
        require(index.min() >= 0 and index.max() < box.shape[1], 'Original hypothesis lacks full frame support')
        score += box[row, index]
        valid &= unmasked[row, index]
        for dc in DC:
            touches_DC |= np.abs(absolute - dc) <= radius
    score /= np.sqrt(times.size * width)
    score[~valid] = -np.inf
    # Geometry only: never change power, z, mask, prefix, or box arrays.
    return score, valid, touches_DC


def original_family_and_admissible(boxes, original_frequencies, fch1_hz, df_hz,
                                   original_times, original_drifts, source_channel0, np):
    """Prospective dual maxima; caller must reconcile original before release.

    Operate only on the frozen originally DC-bad carrier list. The complete
    original785 grid/width1,3 family is replayed. Its unrestricted maximum is
    preserved alongside the best geometrically DC-untouched hypothesis.
    This function has no file loading, public-GO bypass, or automatic caller.
    """
    require(np.__version__ == REQUIRED_NUMPY, 'Exact original NumPy runtime required')
    require(original_drifts.shape == (785,) and original_times.shape == (16,), 'Exact original drift/time dimensions required')
    require(np.array_equal(original_drifts, np.linspace(-4.0, 4.0, 785)), 'Original drift bits/order required; do not zero the tiny zero-neighbour')
    base = (original_frequencies - fch1_hz) / df_hz
    count = base.size
    best = np.full(count, -np.inf)
    best_drift = np.full(count, np.nan)
    best_width = np.zeros(count, dtype=np.int16)
    alternative = np.full(count, -np.inf)
    alternative_drift = np.full(count, np.nan)
    alternative_width = np.zeros(count, dtype=np.int16)
    valid_counts = np.zeros(count, dtype=np.int64)
    admissible_counts = np.zeros(count, dtype=np.int64)
    for width in WIDTHS:
        for first in range(0, len(original_drifts), DRIFT_TILE):
            drifts = original_drifts[first:first + DRIFT_TILE]
            for lo in range(0, count, CARRIER_TILE):
                hi = min(lo + CARRIER_TILE, count)
                scores, valid, touched = original_score_tile(boxes, base[lo:hi], original_times,
                    df_hz, drifts, width, source_channel0, np)
                valid_counts[lo:hi] += valid.sum(axis=0)
                columns = np.arange(hi - lo)
                arg = scores.argmax(axis=0)
                values = scores[arg, columns]
                improve = values > best[lo:hi]
                positions = np.arange(lo, hi)[improve]
                best[positions] = values[improve]
                best_drift[positions] = drifts[arg[improve]]
                best_width[positions] = width
                admissible = valid & ~touched
                admissible_counts[lo:hi] += admissible.sum(axis=0)
                eligible_scores = np.where(admissible, scores, -np.inf)
                eligible_arg = eligible_scores.argmax(axis=0)
                eligible_values = eligible_scores[eligible_arg, columns]
                improve = eligible_values > alternative[lo:hi]
                positions = np.arange(lo, hi)[improve]
                alternative[positions] = eligible_values[improve]
                alternative_drift[positions] = drifts[eligible_arg[improve]]
                alternative_width[positions] = width
    return {'original_score': best, 'original_drift': best_drift, 'original_width': best_width,
            'original_valid_count': valid_counts, 'admissible_score': alternative,
            'admissible_drift': alternative_drift, 'admissible_width': alternative_width,
            'admissible_count': admissible_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', required=True)
    parser.parse_args()
    with Path(__file__).open('rb') as stream:
        code_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    print(json.dumps({'status': 'PROSPECTIVE_ARITHMETIC_KERNELS_ONLY_NO_ARRAYS',
                      'code_sha256': code_hash, 'required_original_numpy': REQUIRED_NUMPY,
                      'installed_numpy_metadata': version('numpy'),
                      'expected_frames': 18, 'frame_shape': [ROWS, FRAME],
                      'source_float_values_read': 0, 'hypothesis_scores_computed': 0,
                      'scientific_runner_present': False}))


if __name__ == '__main__':
    main()
