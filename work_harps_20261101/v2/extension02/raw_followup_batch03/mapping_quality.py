"""Fixed five-window trace support inherited unchanged from mapping43.

Prospectively used for every covering order in batch02. This is a geometry
quality check, not an origin classifier. The original global orientation and
coordinates are never adjusted by this calculation.
"""
import numpy as np
from scipy.ndimage import median_filter

METHOD_CONFIGURATION = {
    'reference_windows_half_open': [[128, 768], [896, 1536], [1664, 2304], [2432, 3072], [3200, 3968]],
    'candidate_exclusion_half_width_pixels': 80,
    'minimum_samples_per_reference_window': 200,
    'minimum_valid_reference_windows': 3,
    'median_correlation_strict_minimum': 0.8,
    'maximum_median_abs_peak_offset': 0.75,
    'minimum_windows_within_one_pixel': 3,
}


def verify_method_configuration(plan):
    if plan.get('mapping_quality') != METHOD_CONFIGURATION:
        raise RuntimeError('Plan five-window method differs from inherited fixed method')


def poly(header, prefix, degree, order, x):
    return np.polynomial.polynomial.polyval(x, [header[prefix + str(order * (degree + 1) + j)] for j in range(degree + 1)])


def trace(header, order, x, flips):
    argument = 4095 - x if flips['argument_flip'] else x
    column = poly(header, 'ESO DRS CAL LOC CTR', int(header['ESO DRS CAL LOC DEG CTR']), order, argument)
    return 4095 - column if flips['column_flip'] else column


def interp(raw, yy, columns):
    low = np.floor(columns).astype(int)
    fraction = columns - low
    return raw[yy, low] * (1 - fraction) + raw[yy, low + 1] * fraction


def hp(array):
    return array - median_filter(array, size=31, mode='nearest')


def peak(profile):
    k = int(np.argmax(profile))
    position = float(k - 8)
    if 0 < k < 16:
        a, b, c = profile[k - 1:k + 2]
        denominator = a - 2 * b + c
        if denominator:
            position += float(.5 * (a - c) / denominator)
    return position


def reference_order(raw, native, header, order, flips, candidates, windows):
    results = []
    for lo, hi in windows:
        x = np.arange(lo, hi)
        yy = 4095 - x if flips['row_flip'] else x
        columns = trace(header, order, x, flips)
        bounds = (columns >= 9) & (columns < 4086)
        mask = bounds.copy()
        excluded = []
        for candidate in candidates:
            if candidate['order'] == order:
                near = abs(x - candidate['native_pixel']) <= 80
                if near.any():
                    excluded.append(candidate['review_id'])
                mask &= ~near
        result = dict(pixel_interval_half_open=[lo, hi], samples=int(mask.sum()), excluded_ids=excluded, correlation=None, peak_offset=None, profile=None)
        if mask.sum() >= 200 and bounds.all():
            values = np.stack([interp(raw, yy, columns + offset) for offset in range(-8, 9)])
            profile = np.median(values[:, mask], axis=1)
            profile -= np.median(profile[np.r_[0:2, 15:17]])
            correlation = float(np.corrcoef(hp(native[order, x])[mask], hp(values[5:12].sum(axis=0))[mask])[0, 1])
            result.update(correlation=correlation if np.isfinite(correlation) else None, peak_offset=peak(profile), profile=profile.tolist(), peak_above_outer_baseline=float(profile.max()))
        results.append(result)
    good = [result for result in results if result['correlation'] is not None]
    correlation = float(np.median([result['correlation'] for result in good])) if good else None
    offset = float(np.median([abs(result['peak_offset']) for result in good])) if good else None
    within_one = sum(abs(result['peak_offset']) <= 1 for result in good)
    usable = bool(len(good) >= 3 and correlation > .8 and offset <= .75 and within_one >= 3)
    return dict(order=order, valid_reference_windows=len(good), median_correlation=correlation, median_abs_peak_offset=offset, windows_within_one_pixel=within_one, mapping_supported=usable, windows=results)

