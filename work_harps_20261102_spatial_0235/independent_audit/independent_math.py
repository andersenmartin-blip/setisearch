"""Scalar reference arithmetic for the frozen spatial diagnostic; no I/O.

Does not import the production implementation. Python statistics, bisect and
explicit scalar sums provide an independent arithmetic route.
"""
import bisect
import math
import statistics

GRID = list(range(-8, 9))
CONTROL_CENTERS = [-255, -205, -155, -105, 106, 156, 206, 256]


def partition():
    flanks = list(range(-280, -80)) + list(range(81, 281))
    windows = {'TARGET': list(range(-5, 6))}
    for i, center in enumerate(CONTROL_CENTERS, 1):
        windows[f'C{i:02d}'] = list(range(center - 5, center + 6))
    training = [r for r in flanks
                if all(abs(r - center) > 10 for center in CONTROL_CENTERS)]
    return training, windows


def interpolate(x, xp, yp):
    if x < xp[0] or x > xp[-1]:
        raise ValueError('No extrapolation in reference arithmetic')
    hi = bisect.bisect_left(xp, x)
    if hi == len(xp):
        return yp[-1]
    if xp[hi] == x:
        return yp[hi]
    lo = hi - 1
    return yp[lo] + (yp[hi] - yp[lo]) * ((x - xp[lo]) / (xp[hi] - xp[lo]))


def geometry(raw, center):
    d = [round(center) + j - center for j in range(-12, 13)]
    background_indices = [i for i, x in enumerate(d) if 9 <= abs(x) <= 12]
    fit_indices = [i for i, x in enumerate(d) if abs(x) <= 8]
    if len(raw) != 25 or not all(math.isfinite(x) for x in raw):
        raise ValueError('Nonfinite or malformed native row')
    if len(background_indices) < 6:
        raise ValueError('Insufficient background pixels')
    bg_values = [raw[i] for i in background_indices]
    background = statistics.median(bg_values)
    noise = 1.4826 * statistics.median([abs(x - background) for x in bg_values])
    return d, fit_indices, background_indices, background, noise


def templates(strips, centers, training):
    prepared, dispositions = {}, []
    for row in training:
        try:
            d, _, bgi, bg, _ = geometry(strips[row], centers[row])
            y = [x - bg for x in strips[row]]
            profile = [interpolate(g, d, y) for g in GRID]
            net = math.fsum(profile)
            if not math.isfinite(net) or net <= 0:
                raise ValueError('Nonpositive signed training profile sum')
            prepared[row] = [x / net for x in profile]
            dispositions.append(dict(relative_raw_row=row, status='USABLE',
                                     signed_normalization_adu=net,
                                     background_adu=bg, background_pixels=len(bgi),
                                     negative_outer_median_adu=statistics.median(strips[row][i] for i in bgi if d[i] < 0),
                                     positive_outer_median_adu=statistics.median(strips[row][i] for i in bgi if d[i] > 0)))
        except ValueError as error:
            dispositions.append(dict(relative_raw_row=row, status='UNUSABLE',
                                     reason=str(error)))
    result, details = {}, {}
    subsets = [('pooled', training, 200),
               ('negative_raw_flank', [r for r in training if r < 0], 100),
               ('positive_raw_flank', [r for r in training if r > 0], 100)]
    for name, subset, minimum in subsets:
        valid = [r for r in subset if r in prepared]
        details[name] = dict(declared_rows=len(subset), valid_rows=len(valid), minimum_rows=minimum)
        if len(valid) < minimum:
            details[name]['status'] = 'BLOCKED_INSUFFICIENT_TRAINING'
            continue
        median = [statistics.median([prepared[r][i] for r in valid]) for i in range(17)]
        net = math.fsum(median)
        if not all(math.isfinite(x) for x in median) or net <= 0:
            details[name]['status'] = 'BLOCKED_NONPOSITIVE_MEDIAN_TEMPLATE'
            continue
        result[name] = [x / net for x in median]
        details[name] = dict(declared_rows=len(subset), valid_rows=len(valid),
                             minimum_rows=minimum, pre_normalization_signed_sum=net,
                             negative_grid_samples=sum(x < 0 for x in result[name]), status='USABLE')
    return result, dispositions, details


def fit(raw, center, template):
    d, fi, bi, bg, noise = geometry(raw, center)
    evaluated = [interpolate(d[i], GRID, template) for i in fi]
    total = math.fsum(evaluated)
    if not math.isfinite(total) or total <= 0:
        raise ValueError('Nonpositive evaluated template sum')
    evaluated = [x / total for x in evaluated]
    denom = math.fsum(x*x for x in evaluated)
    if denom <= 0:
        raise ValueError('Degenerate evaluated template')
    amplitude = math.fsum(t*(raw[i]-bg) for t, i in zip(evaluated, fi)) / denom
    model = [math.nan] * 25
    for i, t in zip(fi, evaluated):
        model[i] = bg + amplitude*t
    residual = [y - m for y, m in zip(raw, model)]
    metrics = dict(amplitude_adu=amplitude, background_adu=bg,
                   outer_mad_proxy_adu=noise, fit_pixels=len(fi),
                   background_pixels=len(bi), fractional_trace_column=center-round(center),
                   negative_outer_median_adu=statistics.median(raw[i] for i in bi if d[i] < 0),
                   positive_outer_median_adu=statistics.median(raw[i] for i in bi if d[i] > 0),
                   signed_residual_sum_adu=math.fsum(residual[i] for i in fi),
                   residual_rms_adu=math.sqrt(math.fsum(residual[i]**2 for i in fi)/len(fi)))
    return d, fi, bi, model, residual, metrics


def window(name, rr, strips, centers, template):
    rows, arrays, weighted = [], [], []
    mid = rr[len(rr)//2]
    for row in rr:
        d, fi, bi, model, residual, metrics = fit(strips[row], centers[row], template)
        rows.append(dict(window=name, relative_raw_row=row, **metrics))
        arrays.append((d, fi, model, residual))
        for i in fi:
            weighted.append((residual[i], d[i], row-mid))
    l1 = math.fsum(abs(e) for e, _, _ in weighted)
    pos = math.fsum(max(e, 0) for e, _, _ in weighted)
    on = [(e, d, y) for e, d, y in weighted if abs(d) <= 3]
    off = [(e, d, y) for e, d, y in weighted if abs(d) > 3]
    metrics = dict(window=name, center_relative_raw_row=mid, rows=len(rr),
        fit_pixels=len(weighted), on_trace_pixels=len(on), off_trace_pixels=len(off),
        amplitude_sum_adu=math.fsum(r['amplitude_adu'] for r in rows),
        median_background_adu=statistics.median(r['background_adu'] for r in rows),
        median_outer_mad_proxy_adu=statistics.median(r['outer_mad_proxy_adu'] for r in rows),
        signed_residual_sum_adu=math.fsum(e for e, _, _ in weighted), residual_l1_adu=l1,
        on_trace_residual_l1_adu=math.fsum(abs(e) for e, _, _ in on),
        off_trace_residual_l1_adu=math.fsum(abs(e) for e, _, _ in off),
        off_trace_l1_fraction=math.fsum(abs(e) for e, _, _ in off)/l1 if l1 else None,
        maximum_pixel_l1_fraction=max(abs(e) for e, _, _ in weighted)/l1 if l1 else None,
        l1_centroid_crossdisp_pixels=math.fsum(abs(e)*d for e, d, _ in weighted)/l1 if l1 else None,
        l1_centroid_dispersion_pixels=math.fsum(abs(e)*y for e, _, y in weighted)/l1 if l1 else None,
        positive_residual_sum_adu=pos,
        negative_residual_sum_adu=math.fsum(min(e,0) for e,_,_ in weighted),
        on_trace_mean_absolute_residual_adu=math.fsum(abs(e) for e,_,_ in on)/len(on),
        off_trace_mean_absolute_residual_adu=math.fsum(abs(e) for e,_,_ in off)/len(off),
        positive_residual_centroid_crossdisp_pixels=math.fsum(max(e,0)*d for e,d,_ in weighted)/pos if pos else None,
        positive_residual_centroid_dispersion_pixels=math.fsum(max(e,0)*y for e,_,y in weighted)/pos if pos else None,
        zero_residual_l1=l1==0, zero_positive_residual_sum=pos==0)
    return metrics, rows, arrays
