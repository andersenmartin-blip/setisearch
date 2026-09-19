#!/usr/bin/env python3
"""Independent struct decoding and 60-decimal scalar reference for LS8C."""
import csv
from decimal import Decimal, getcontext, ROUND_FLOOR
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

getcontext().prec = 60
D = Decimal
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8c_auxiliary'
ROW = struct.Struct('>26sddddii7d4f')
INDEX = {'FLUX': 3, 'DARK': 7, 'BACKGROUND': 8, 'CONTA_LC': 9,
         'CONTA_LC_ERR': 10, 'SMEARING_LC': 11, 'SMEARING_LC_ERR': 12,
         'ROLL_ANGLE': 13, 'LOCATION_X': 14, 'LOCATION_Y': 15,
         'CENTROID_X': 16, 'CENTROID_Y': 17}
UNITS = dict(zip(INDEX, ['electron', 'electron', 'electron', 'ratio', 'ratio',
                         'electron', 'ratio', 'degree', 'pixel', 'pixel', 'pixel', 'pixel']))
UNITS.update(OFFSET_X='pixel', OFFSET_Y='pixel')
COUPLING = ('DARK', 'BACKGROUND', 'CONTA_LC', 'SMEARING_LC', 'ROLL_ANGLE', 'OFFSET_X', 'OFFSET_Y')
EPS = D(2) ** -52


def median(values):
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def mean(values):
    return sum(values) / len(values)


def reference_series(times, values, side, event):
    if not all(v.is_finite() for v in times + values):
        return {'status': 'UNAVAILABLE_NONFINITE'}
    scale = max(D(1), max(abs(v) for v in values))
    floor = 64 * EPS * scale
    offset = median([values[i] for i in side])
    x, y = [times[i] for i in side], [values[i] - offset for i in side]
    n, sx, sy = D(len(x)), sum(x), sum(y)
    sxx, sxy = sum(v * v for v in x), sum(a * b for a, b in zip(x, y))
    det = n * sxx - sx * sx
    if det <= 0:
        return {'status': 'UNAVAILABLE_TIME_RANK'}
    a, b = (sy * sxx - sx * sxy) / det, (n * sxy - sx * sy) / det
    fit = [a + b * v for v in times]
    residual = [v - offset - f for v, f in zip(values, fit)]
    rs = [residual[i] for i in side]
    rm = median(rs)
    mad = D.from_float(1.4826) * median([abs(v - rm) for v in rs])
    rms = mean([v * v for v in rs]).sqrt()
    delta = mean([residual[i] for i in event])
    return {'status': 'AVAILABLE', 'roundoff_floor': floor,
            'event_mean': mean([values[i] for i in event]),
            'predicted_event_mean': offset + mean([fit[i] for i in event]),
            'mean_residual': delta, 'sum_residual': sum(residual[i] for i in event),
            'side_mad': mad, 'side_rms': rms, 'slope_per_second': b,
            'mad_displacement': delta / mad if mad > floor else None,
            'values': values, 'baseline': [offset + f for f in fit], 'residual': residual}


def reference_context(rows, start, duration):
    lo, hi = start - 14, start + duration + 14
    ctx = rows[lo:hi]
    assert len(ctx) == 28 + duration
    assert all(r[5] == r[6] == 0 for r in ctx)
    times = [(D.from_float(r[2]) - D.from_float(rows[start][2])) * 86400 for r in ctx]
    side = list(range(12)) + list(range(16 + duration, 28 + duration))
    event = list(range(14, 14 + duration))
    series = {}
    for name, unit in UNITS.items():
        if name.startswith('OFFSET_'):
            axis = name[-1]
            values = [D.from_float(r[INDEX['CENTROID_' + axis]]) -
                      D.from_float(r[INDEX['LOCATION_' + axis]]) for r in ctx]
        else:
            values = [D.from_float(r[INDEX[name]]) for r in ctx]
        if name == 'ROLL_ANGLE' and all(v.is_finite() for v in values):
            unwrapped = [values[0]]
            for i in range(1, len(values)):
                delta = values[i] - values[i - 1]
                turns = ((delta + 180) / 360).to_integral_value(rounding=ROUND_FLOOR)
                unwrapped.append(unwrapped[-1] + delta - 360 * turns)
            values = unwrapped
        series[name] = {'unit': unit, **reference_series(times, values, side, event)}
    flux, couplings = series['FLUX'], {}
    for name in COUPLING:
        aux = series[name]
        if flux['status'] != 'AVAILABLE' or aux['status'] != 'AVAILABLE':
            couplings[name] = {'status': 'UNAVAILABLE_INPUT'}
            continue
        if flux['side_rms'] <= flux['roundoff_floor'] or aux['side_rms'] <= aux['roundoff_floor']:
            couplings[name] = {'status': 'UNAVAILABLE_SCATTER'}
            continue
        ff = sum(flux['residual'][i] ** 2 for i in side)
        aa = sum(aux['residual'][i] ** 2 for i in side)
        fa = sum(flux['residual'][i] * aux['residual'][i] for i in side)
        beta = fa / aa
        predicted = beta * aux['mean_residual']
        couplings[name] = {'status': 'AVAILABLE', 'beta_electron_per_unit': beta,
            'side_correlation': fa / (ff * aa).sqrt(),
            'predicted_flux_mean_residual': predicted,
            'remaining_flux_mean_residual': flux['mean_residual'] - predicted,
            'predicted_fraction_of_flux_residual': (predicted / flux['mean_residual']
                if abs(flux['mean_residual']) > flux['roundoff_floor'] else None)}
    dx, dy = series['OFFSET_X'], series['OFFSET_Y']
    motion = ((dx['mean_residual'] ** 2 + dy['mean_residual'] ** 2).sqrt()
              if dx['status'] == dy['status'] == 'AVAILABLE' else None)
    return {'context_start': lo, 'context_stop': hi,
            'side_indices': [i + lo for i in side], 'event_indices': [i + lo for i in event],
            'times_seconds': times, 'series': series, 'couplings': couplings,
            'centroid_offset_residual_norm_pixels': motion}


def to_float(x):
    if isinstance(x, D):
        return float(x)
    if isinstance(x, dict):
        return {k: to_float(v) for k, v in x.items()}
    if isinstance(x, list):
        return [to_float(v) for v in x]
    return x


def main():
    cfg = json.loads((ROOT / 'config/ls8c_auxiliary.json').read_text())
    saved = json.loads((OUT / 'diagnostics.json').read_text())
    reference, failed, counts, maxima = [], [], {'numeric': 0, 'exact': 0}, {}
    tables = {}
    for key, expected in cfg['input_table_sha256'].items():
        raw = (ROOT / 'results_ls8b_l2_suite' / key / 'lightcurve_table.bin').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        assert len(raw) % ROW.size == 0
        tables[key] = list(ROW.iter_unpack(raw))
    identities = [(r['file_key'], r['sign'], r['cluster_id'], r['start'], r['duration']) for r in saved]
    assert identities == [tuple(r) for r in cfg['representatives']]
    csv_rows = list(csv.DictReader((ROOT / 'results_ls8b_l2_suite/cluster_representatives.csv').open()))
    assert identities == [(r['file_key'], r['sign'], int(r['cluster_id']), int(r['start_row']),
                           int(r['duration_rows'])) for r in csv_rows]
    old_decimal = [json.loads(line) for line in gzip.decompress(
        (ROOT / 'results_ls8b_l2_suite/decimal_reference.jsonl.gz').read_bytes()).splitlines()]
    old_lookup = {(r['file_key'], r['start'], r['duration']): r for r in old_decimal}

    def compare(actual, expected, path, scale=1., dimensionless=False):
        if isinstance(expected, dict):
            counts['exact'] += 1
            if set(actual) != set(expected):
                failed.append({'path': path, 'reason': 'key mismatch'})
                return
            for k, v in expected.items():
                compare(actual[k], v, path + '.' + k, scale, dimensionless or k in (
                    'mad_displacement', 'side_correlation', 'predicted_fraction_of_flux_residual'))
        elif isinstance(expected, list):
            counts['exact'] += 1
            if len(actual) != len(expected):
                failed.append({'path': path, 'reason': 'length mismatch'})
                return
            for i, v in enumerate(expected):
                compare(actual[i], v, path + f'[{i}]', scale, dimensionless)
        elif isinstance(expected, float):
            counts['numeric'] += 1
            tol = ((1e-7 + 1e-8 * abs(expected)) if dimensionless else
                   (1e-9 * abs(expected) + 512. * 2.**-52 * max(1., scale, abs(expected))))
            diff = abs(actual - expected) if actual is not None else math.inf
            key = path.split('.', 1)[1].split('[')[0]
            maxima[key] = max(maxima.get(key, 0.), diff)
            if not math.isfinite(diff) or diff > tol:
                failed.append({'path': path, 'actual': actual, 'reference': expected, 'tolerance': tol})
        else:
            counts['exact'] += 1
            if actual != expected:
                failed.append({'path': path, 'actual': actual, 'reference': expected})

    for idx, record in enumerate(saved):
        ident = {k: record[k] for k in ('file_key', 'sign', 'cluster_id', 'start', 'duration')}
        ref = to_float(reference_context(tables[record['file_key']], record['start'], record['duration']))
        reference.append({**ident, **ref})
        for key in ('context_start', 'context_stop', 'side_indices', 'event_indices', 'times_seconds'):
            compare(record[key], ref[key], f'{idx}.{key}', max(abs(v) for v in ref['times_seconds']))
        for field, rs in ref['series'].items():
            scale = max([1.] + [abs(v) for v in rs.get('values', [])])
            compare(record['series'][field], rs, f'{idx}.series.{field}', scale)
        for field, rc in ref['couplings'].items():
            for key, value in rc.items():
                scale = (max(abs(v) for v in ref['series']['FLUX']['values'])
                         if key in ('predicted_flux_mean_residual', 'remaining_flux_mean_residual') else 1.)
                compare(record['couplings'][field][key], value, f'{idx}.couplings.{field}.{key}',
                        scale, key in ('side_correlation', 'predicted_fraction_of_flux_residual'))
        compare(record['centroid_offset_residual_norm_pixels'], ref['centroid_offset_residual_norm_pixels'],
                f'{idx}.centroid_offset_residual_norm_pixels')
        old = old_lookup[(record['file_key'], record['start'], record['duration'])]
        compare(record['series']['FLUX']['sum_residual'], old['excess_electrons'],
                f'{idx}.ls8b_decimal_flux_excess', max(abs(v) for v in ref['series']['FLUX']['values']))
    (OUT / 'decimal_reference.json').write_text(json.dumps(reference, indent=2, allow_nan=False) + '\n')
    audit = {'status': 'FAIL' if failed else 'PASS', 'decimal_precision': 60,
             'representatives': len(reference), 'comparisons': counts,
             'maximum_absolute_differences': maxima, 'disagreements': failed,
             'tolerances': cfg['audit_tolerances'],
             'method': 'independent big-endian struct decoding and 60-decimal scalar normal equations',
             'original_ls8b_audit_status': 'FAIL'}
    (OUT / 'audit.json').write_text(json.dumps(audit, indent=2, allow_nan=False) + '\n')
    summary = json.loads((OUT / 'summary.json').read_text())
    summary['status'] = 'COMPLETE_AUDIT_FAILED' if failed else 'COMPLETE_AUDITED'
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'status': audit['status'], 'comparisons': counts, 'disagreements': failed}, indent=2))
    return bool(failed)


if __name__ == '__main__':
    sys.exit(main())
