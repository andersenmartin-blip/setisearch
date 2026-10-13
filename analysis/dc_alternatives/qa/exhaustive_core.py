"""Independent arithmetic core for the frozen DC-alternative hypothesis audit.

Imports no numerical modules and reads no inputs at import. Call only after
root admits exact original frames, row terms, geometry and grid protocol.
No detector helper is imported. Whole-frame nearest median boundaries and
prefix origin are preserved; independent reestimated terms are audit-only.
"""
import math


def original_z_from_raw_frame(raw, saved_normalization, np, tile=512):
    """Exact original residual arithmetic using frozen original normalization.

    A raw frame may be a crop or whole native array: never shorten the prefix.
    Median501 reproduces SciPy nearest boundaries with explicit edge padding.
    """
    if raw.ndim != 2 or raw.shape[0] != 16 or raw.dtype.str != '<f4':
        raise ValueError('Original sixteen-row float32 frame required')
    if not np.isfinite(raw).all() or (raw < 0).any():
        raise ValueError('Invalid raw power in original frame')
    level, location, scale = [np.asarray(saved_normalization[k], dtype=np.float64)
        for k in ('row_power_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale')]
    if any(a.shape != (16,) or not np.isfinite(a).all() for a in (level, location, scale)) or (level <= 0).any() or (scale <= 0).any():
        raise ValueError('Original row normalization terms invalid')
    z = np.empty(raw.shape, dtype=np.float64)
    for row in range(16):
        normalized = raw[row].astype(np.float64) / level[row]
        padded = np.pad(normalized, (250, 250), mode='edge')
        windows = np.lib.stride_tricks.sliding_window_view(padded, 501)
        for start in range(0, raw.shape[1], tile):
            stop = min(start + tile, raw.shape[1])
            median = np.median(windows[start:stop], axis=1)
            z[row, start:stop] = ((normalized[start:stop] - median) - location[row]) / scale[row]
    return z


def independent_core_normalization_audit(raw, source_channel0, core_interval, np, tile=512):
    """Reestimate core terms separately; never feed these into exact prefix QA."""
    start, stop = [int(x) - int(source_channel0) for x in core_interval]
    if stop - start != 4096 or start < 250 or stop + 250 > raw.shape[1]:
        raise ValueError('Original physical core requires4096 cells and501 support')
    core = raw[:, start:stop].astype(np.float64)
    level = np.median(core, axis=1)
    residual = np.empty_like(core)
    for row in range(16):
        support = raw[row, start-250:stop+250].astype(np.float64) / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(support, 501)
        for lo in range(0, 4096, tile):
            hi = min(lo+tile, 4096)
            residual[row, lo:hi] = core[row, lo:hi]/level[row] - np.median(windows[lo:hi], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826*np.median(np.abs(residual-center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual-center[:, None], -5*scale[:, None], 5*scale[:, None]), axis=1)
    return {'row_power_median': level, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location}


def exhaustive_original_scores(z, source_channel0, frequencies_hz, drifts_hz_s, widths,
                               times_s, fch1_hz, df_hz, frozen_DC_channels, np):
    """Exact original numeric sequence plus independent row-loop DC geometry.

    Return one width-ordered1570×N table. Argmax along hypotheses preserves
    original width1-before3 and ascending-drift first exact tie semantics.
    """
    times = np.asarray(times_s, dtype=np.float64)
    drifts = np.asarray(drifts_hz_s, dtype=np.float64)
    frequency = np.asarray(frequencies_hz, dtype=np.float64)
    if times.shape != (16,) or drifts.shape != (785,) or tuple(widths) != (1,3):
        raise ValueError('Frozen original16/785/width1,3 family required')
    base = (frequency - fch1_hz) / df_hz
    prefix = np.zeros((16, z.shape[1]+1), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(z, axis=1, dtype=np.float64)
    scores, admissible = [], []
    for width in widths:
        score = np.zeros((785, len(base)), dtype=np.float64)
        clean = np.ones(score.shape, dtype=bool)
        for row, elapsed in enumerate(times):
            absolute = np.rint(base[None, :] + drifts[:, None]*elapsed/df_hz).astype(np.int64)
            left = absolute-int(source_channel0)-int(width)//2
            if left.min() < 0 or (left+width).max() > z.shape[1]:
                raise ValueError('Hypothesis support outside exact original frame')
            # Same subtraction and sequential row += operations as original.
            contribution = prefix[row, left+width] - prefix[row, left]
            score += contribution
            for dc in frozen_DC_channels:
                clean &= np.abs(absolute-int(dc)) > int(width)//2
        score /= np.sqrt(len(times)*width)
        scores.append(score);admissible.append(clean)
    raw = np.concatenate(scores, axis=0)
    valid = np.concatenate(admissible, axis=0)
    filtered = np.where(valid, raw, -np.inf)
    arg = np.argmax(filtered, axis=0)
    nonempty = valid.any(axis=0)
    maximum = filtered[arg, np.arange(len(base))]
    tie_count = np.where(nonempty, (filtered == maximum[None, :]).sum(axis=0), 0)
    original_arg = np.argmax(raw, axis=0)
    return {'raw_prefix_scores': raw, 'admissible': valid, 'best_clean_index': arg,
            'has_clean_hypothesis': nonempty, 'best_clean_score': maximum,
            'exact_maximum_tie_count': tie_count,
            'unconstrained_best_index': original_arg,
            'unconstrained_best_score': raw[original_arg, np.arange(len(base))]}


def direct_cell_score(z, source_channel0, frequency_hz, drift_hz_s, width, times_s,
                      fch1_hz, df_hz, np):
    """Independent local cell sum for tolerance audit, never winner selection."""
    centers = np.rint((frequency_hz-fch1_hz)/df_hz + drift_hz_s*np.asarray(times_s)/df_hz).astype(np.int64)
    terms = []
    for row, center in enumerate(centers):
        lo = int(center)-int(source_channel0)-int(width)//2
        terms.append(float(z[row, lo:lo+width].sum(dtype=np.float64)))
    return float(np.asarray(terms, dtype=np.float64).sum(dtype=np.float64)/np.sqrt(16*width))
