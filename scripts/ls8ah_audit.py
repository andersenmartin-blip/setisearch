#!/usr/bin/env python3
"""Independent LS8AH reconstruction; never imports producer modules.

Struct raw decoding, long-double temporal normal equations, scalar lag sums,
explicit covariance quadratic forms and the pinned independent LS8M spatial
normal-equation implementation, with independent coordinate set accounting.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from ls8m_audit import LD, ROW, MODEL_COLUMNS, total, model, cells, paired, regression_matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8ah_residuals'

def reconstruct(times, cube, train, target, valid, center, cadence):
    t = np.asarray(times, dtype=LD); n = LD(len(train)); d = LD(len(target))
    values = cube[train][:, valid].astype(LD)
    offset = np.median(values, axis=0); z = values - offset
    sx = t[train].sum(); sx2 = (t[train] ** 2).sum()
    sy = z.sum(axis=0); sxy = (t[train, None] * z).sum(axis=0)
    determinant = n * sx2 - sx ** 2
    a = (sy * sx2 - sxy * sx) / determinant
    b = (n * sxy - sx * sy) / determinant
    residuals = z - a - t[train, None] * b
    event = (cube[target][:, valid].astype(LD) - offset - a - t[target, None] * b).sum(axis=0)
    weights = np.zeros(len(t), dtype=LD)
    for i in target: weights[i] = 1
    q = t[target].sum()
    for i in train:
        weights[i] = -((d * sx2 - q * sx) + (n * q - d * sx) * t[i]) / determinant
    projection = np.empty((len(train), len(train)), dtype=LD)
    for i, ri in enumerate(train):
        for j, rj in enumerate(train):
            projection[i, j] = int(i == j) - (sx2 - sx * (t[ri] + t[rj]) + n * t[ri] * t[rj]) / determinant
    mean = np.full(valid.shape, np.nan); mean[valid] = values.mean(axis=0)
    yy, xx = np.indices(valid.shape); radius = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    annulus = valid & (radius > 900) & (radius <= 1600)
    p = mean - float(np.median(mean[annulus]))
    gx = np.full_like(p, np.nan); gy = gx.copy()
    gx[:, 1:-1] = (p[:, 2:] - p[:, :-2]) * .5
    gy[1:-1] = (p[2:] - p[:-2]) * .5
    mask = valid & (radius <= 625) & np.isfinite(gx) & np.isfinite(gy)
    assert np.array_equal(mask, radius <= 625)
    side = residuals[:, mask[valid]]
    sse = (side ** 2).sum(axis=0); iid_s2 = sse / (n - 2)
    median = np.median(iid_s2); assert median > 0
    standardized = side / np.sqrt((iid_s2 + median) / 2)
    denom = (standardized ** 2).sum(); segments = [0]
    for i in range(1, len(t)):
        segments.append(segments[-1] + int(not LD(cadence) / 2 <= t[i] - t[i - 1] <= LD(cadence) * 3 / 2))
    lags = []; counts = []
    for lag, taper in ((1, LD(2) / 3), (2, LD(1) / 3)):
        pairs = [(i, j) for i, ri in enumerate(train) for j, rj in enumerate(train)
                 if rj - ri == lag and segments[ri] == segments[rj]]
        numerator = sum((standardized[i] * standardized[j]).sum() for i, j in pairs)
        lags.append(float(taper * numerator / denom)); counts.append(len(pairs))
    corr = np.eye(len(t), dtype=LD)
    for i in range(len(t)):
        for j in range(i + 1, len(t)):
            if j - i in (1, 2) and segments[i] == segments[j]:
                corr[i, j] = corr[j, i] = lags[j - i - 1]
    h = float(sum(weights[i] * corr[i, j] * weights[j] for i in range(len(t)) for j in range(len(t))))
    df = float(sum(projection[i, j] * corr[rj, ri] for i, ri in enumerate(train) for j, rj in enumerate(train)))
    iid_h = float((weights ** 2).sum()); s2 = np.asarray(sse / df, float)
    assert h > 0 and df > 0
    info = {'cadence_seconds': float(cadence), 'rho_lag1': lags[0], 'rho_lag2': lags[1], 'lag_pair_counts': counts,
        'cadence_segments': segments[-1] + 1, 'iid_sum_factor': iid_h,
        'correlated_sum_factor': h, 'iid_residual_df': len(train) - 2,
        'correlated_residual_trace': df,
        'correlated_to_iid_variance_factor': (h / df) / (iid_h / (len(train) - 2)),
        'target_rows': target, 'train_rows': train, 'row_weights': np.asarray(weights, float).tolist()}
    return {'y': np.asarray(event[mask[valid]], float), 'side': np.asarray(side, float),
        'x': np.column_stack([p[mask], gx[mask], gy[mask], np.ones(mask.sum())]),
        's2': s2, 'variance': h * (s2 + np.median(s2)) / 2, 'h': h, 'df': df,
        'mask': mask, 'xy': np.column_stack([xx[mask], yy[mask]]), 'center': np.asarray(center),
        'row_weights': np.asarray(weights, float), 'correlation': np.asarray(corr, float), 'temporal': info}


def description(state):
    models = {}; residual = None
    for name, columns in MODEL_COLUMNS.items():
        models[name], rr = model(state, columns)
        if name == 'combined': residual = rr
    iid = dict(state); iid['h'] = state['temporal']['iid_sum_factor']
    iid['df'] = state['temporal']['iid_residual_df']
    iid['s2'] = np.asarray((state['side'].astype(LD) ** 2).sum(axis=0) / iid['df'], float)
    iid['variance'] = iid['h'] * (iid['s2'] + np.median(iid['s2'])) / 2
    return {'pixels': len(state['y']), 'temporal': state['temporal'],
        'median_sideband_variance_adu2': float(np.median(state['s2'])),
        'models': models, 'iid_models': {name: model(iid, cols)[0] for name, cols in MODEL_COLUMNS.items()},
        'spatial': cells(state, residual)}, residual


def boundary(maps, masks):
    a = set(zip(*np.where(masks[0]))); b = set(zip(*np.where(masks[1])))
    regions = {'intersection': a & b, 'C0_only': a - b, 'C1_only': b - a, 'C0': a, 'C1': b}
    result = {'pixel_counts': {name: len(coords) for name, coords in regions.items()}, 'products': {}}
    for kind in ('CAL', 'COR', 'DELTA'):
        item = {}
        for name, coords in regions.items():
            v = np.array([maps[kind][y, x] for y, x in sorted(coords)], dtype=LD)
            item[name] = {'flux_adu': total(v), 'energy_adu2': total(v * v)}
        for measure in ('flux_adu', 'energy_adu2'):
            diff = item['C1'][measure] - item['C0'][measure]
            pred = item['C1_only'][measure] - item['C0_only'][measure]
            item['difference_' + measure] = diff; item['boundary_difference_' + measure] = pred
            item['closure_relative_' + measure] = (diff - pred) / max(1., sum(abs(item[k][measure]) for k in regions))
        result['products'][kind] = item
    for name in ('C0_only', 'C1_only'):
        coords = sorted(regions[name])
        result[name + '_pixels'] = {'xy': [[int(x), int(y)] for y, x in coords],
            **{kind: [float(maps[kind][y, x]) for y, x in coords] for kind in ('CAL', 'COR', 'DELTA')}}
    return result


def controls(state):
    duration = len(state['temporal']['target_rows'])
    x = state['x']; y = state['y']; xy = state['xy']
    combined, _ = regression_matrix(x, state['variance'])
    xd = x[:, (1, 2, 3)]; displacement, _ = regression_matrix(xd, state['variance'])
    cases = []
    for name, column, per_row in [('brightness', 0, .001), ('shift_x', 1, .05), ('shift_y', 2, .05)]:
        truth = np.zeros(4); truth[column] = duration * per_row
        cases.append((name, sum(x[:, column] * per_row for _ in range(duration)), truth))
    for j, (dx, dy) in enumerate([(0, 0), (10, 0), (0, 10), (-10, 0), (0, -10)]):
        target = state['center'] + [dx, dy]
        i = min(range(len(xy)), key=lambda k: (float(np.sum((xy[k] - target) ** 2)), k))
        pulse = np.zeros(len(x)); pulse[i] = 5 * math.sqrt(state['variance'][i])
        cases.append((f'compact_{j}', pulse, None))
    records = []
    for name, plus, truth in cases:
        for sign in (-1, 1):
            pulse = sign * plus; pure = combined @ pulse
            increment = combined @ (y + pulse) - combined @ y
            residual = pulse - xd @ (displacement @ pulse); flux = total(pulse)
            records.append({'kind': name, 'sign': sign, 'exposures': duration,
                'expected_combined_coefficients': (sign * truth).tolist() if truth is not None else None,
                'pure_combined_coefficients': pure.tolist(), 'additive_coefficient_increment': increment.tolist(),
                'additive_linearity_max_error': float(np.max(np.abs(increment - pure))),
                'displacement_removal_retained_weighted_energy_fraction': total(residual.astype(LD) ** 2 / state['variance']) / total(pulse.astype(LD) ** 2 / state['variance']),
                'displacement_removal_flux_fraction': total(residual) / flux if abs(flux) > 1e-10 * total(np.abs(pulse)) else None,
                'injected_flux_adu': flux})
    return records


def main():
    cfg = json.loads((ROOT / 'config/ls8ah_residuals.json').read_text())
    original = json.loads((ROOT / 'config/ls8ag_images.json').read_text())
    for name, digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for line in (ROOT / 'results_ls8ag_images/SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((ROOT / 'results_ls8ag_images' / name).read_bytes()).hexdigest() == digest
    actual = json.loads((OUT / 'diagnostics.json').read_text())
    previous = {v['id']: v for v in json.loads((ROOT / 'results_ls8ag_images/diagnostics.json').read_text())}
    failures = []; counts = {'numeric': 0, 'exact': 0}; maximum_scaled_error = 0.

    def compare(a, b, path):
        nonlocal maximum_scaled_error
        if isinstance(b, np.ndarray):
            counts['exact'] += 1
            if np.shape(a) != b.shape:
                failures.append({'path': path, 'reason': 'array shape mismatch'}); return
            if b.dtype.kind in 'biu':
                counts['exact'] += b.size
                if not np.array_equal(a, b): failures.append({'path': path, 'reason': 'exact array mismatch'})
                return
            counts['numeric'] += b.size
            diff = np.abs(a - b); tolerance = 1e-6 + 2e-8 * np.abs(b)
            scaled = float(np.max(diff / tolerance, initial=0)); maximum_scaled_error = max(maximum_scaled_error, scaled)
            if not np.isfinite(diff).all() or np.any(diff > tolerance):
                failures.append({'path': path, 'reason': 'array mismatch', 'maximum_scaled_error': scaled})
        elif isinstance(b, dict):
            counts['exact'] += 1
            if set(a) != set(b): failures.append({'path': path, 'reason': 'key mismatch'}); return
            for k, v in b.items(): compare(a[k], v, path + '.' + k)
        elif isinstance(b, list):
            counts['exact'] += 1
            if len(a) != len(b): failures.append({'path': path, 'reason': 'length mismatch'}); return
            for i, v in enumerate(b): compare(a[i], v, path + f'[{i}]')
        elif isinstance(b, float):
            counts['numeric'] += 1
            dimensionless = any(s in path for s in ('fraction', 'ratio', 'explained', 'condition', 'over_cor', 'closure_relative', 'coefficients', 'linearity', 'factor', 'trace', 'rho_', 'row_weights'))
            tolerance = (1e-8 if dimensionless else 1e-6) + 2e-8 * abs(b)
            diff = abs(a - b) if isinstance(a, (int, float)) else math.inf
            maximum_scaled_error = max(maximum_scaled_error, diff / tolerance)
            if not math.isfinite(diff) or diff > tolerance: failures.append({'path': path, 'actual': a, 'reference': b, 'tolerance': tolerance})
        else:
            counts['exact'] += 1
            if a != b: failures.append({'path': path, 'actual': a, 'reference': b})

    references = []; injected = []
    for c in original['contexts']:
        duration = c['duration']; cadence = cfg['contexts'][c['id']]['cadence_seconds']
        assert duration in (1, 3)
        SIDE = list(range(12)) + list(range(16 + duration, 28 + duration))
        EVENT = list(range(14, 14 + duration))
        BLOCKS = [list(range(start, start + duration))
                  for lo in (0, 16 + duration) for start in range(lo, lo + 12, duration)]
        compare(cfg['contexts'][c['id']], {'duration_rows': duration, 'cadence_seconds': cadence,
            'side_rows': SIDE, 'event_rows': EVENT, 'held_blocks': BLOCKS}, c['id'] + '.frozen_layout')
        key = c['file_key']; rows = list(ROW.iter_unpack((ROOT / 'results_ls8af_l2_screen' / key / 'lightcurve_table.bin').read_bytes()))[c['lo']:c['hi']]
        times = np.array([(LD(r[2]) - LD(rows[14][2])) * 86400 for r in rows], dtype=LD)
        cubes = {}
        for kind in ('CAL', 'COR'):
            path = ROOT / 'results_ls8ag_images' / c['id'] / f'SCI_{kind}_SubArray.bin.gz'
            raw = gzip.decompress(path.read_bytes()); receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
            assert len(raw) == (28 + duration) * 320000 and hashlib.sha256(raw).hexdigest() == receipt['raw_sha256']
            cubes[kind] = np.fromiter((r[0] for r in struct.iter_unpack('>d', raw)), dtype=float).reshape(28 + duration, 200, 200)
        valid = np.ones((200, 200), bool)
        for i in SIDE + EVENT: valid &= np.isfinite(cubes['CAL'][i]) & np.isfinite(cubes['COR'][i])
        spec = original['sources'][key]['SCI_COR_SubArray']
        center = [math.fsum(rows[i][16] for i in SIDE) / 24 - spec['xoff'], math.fsum(rows[i][17] for i in SIDE) / 24 - spec['yoff']]
        item = {'id': c['id'], 'sign': c['sign'], 'original_ls8ag_classification': previous[c['id']]['classification'],
            'duration_rows': duration, 'cadence_seconds': cadence, 'event_rows': EVENT, 'conventions': {}}
        masks = []
        with np.load(ROOT / 'results_ls8ag_images' / c['id'] / 'event_maps.npz') as saved:
            compare(saved['COMMON'], valid, c['id'] + '.original_common')
            maps = {kind: saved[kind].copy() for kind in ('CAL', 'COR', 'DELTA')}
        for number in (0, 1):
            conv = f'C{number}'; cc = np.asarray(center) - number; data = {}; states = {}
            with np.load(OUT / c['id'] / f'{conv}_arrays.npz') as saved:
                compare(saved['COMMON'], valid, c['id'] + '.' + conv + '.COMMON')
                for kind in ('CAL', 'COR'):
                    state = reconstruct(times, cubes[kind], SIDE, EVENT, valid, cc, cadence); states[kind] = state
                    result, residual = description(state)
                    for name in ('y', 'side', 'x', 'variance', 's2', 'mask', 'xy', 'row_weights', 'correlation'):
                        compare(saved[f'{kind}_{name}'], state[name], c['id'] + '.' + conv + '.' + kind + '.' + name)
                    compare(saved[f'{kind}_residual'], residual, c['id'] + '.' + conv + '.' + kind + '.residual')
                    compare(state['y'], maps[kind][state['mask']], c['id'] + '.' + conv + '.' + kind + '.original_map')
                    result['held_blocks'] = []
                    for block in BLOCKS:
                        training = [i for i in SIDE if i < block[0] - 2 or i > block[-1] + 2]
                        pseudo = reconstruct(times, cubes[kind], training, block, valid, cc, cadence)
                        detail, _ = description(pseudo)
                        result['held_blocks'].append({'held_local_rows': block, **detail})
                    metric = result['models']['combined']['weighted_residual_to_sideband_ratio']
                    result['held_blocks_at_least_event'] = sum(p['models']['combined']['weighted_residual_to_sideband_ratio'] >= metric for p in result['held_blocks'])
                    result['held_block_count'] = len(BLOCKS)
                    result['original_ls8ag_unweighted_fits'] = previous[c['id']]['conventions'][conv]['fits'][kind]
                    data[kind] = result
                    injected.extend({'id': c['id'], 'convention': conv, 'product': kind, **r} for r in controls(state))
            masks.append(states['COR']['mask']); data['center'] = cc.tolist()
            data['correction_residual_account'] = paired(states['CAL'], states['COR'])
            item['conventions'][conv] = data
        item['boundary_account'] = boundary(maps, masks)
        compare(json.loads((OUT / c['id'] / 'diagnostics.json').read_text()), item, c['id'] + '.per_context_copy')
        references.append(item); print(c['id'], 'independent duration/covariance/boundary reconstruction complete', flush=True)
    compare(actual, references, 'diagnostics')
    actual_controls = json.loads((OUT / 'injection_controls.json').read_text())
    compare(actual_controls, injected, 'injection_controls')
    truth_cases = 0
    for r in actual_controls:
        if r['expected_combined_coefficients'] is not None:
            truth_cases += 1
            error = max(abs(a - b) for a, b in zip(r['pure_combined_coefficients'], r['expected_combined_coefficients']))
            if error > 1e-9: failures.append({'path': 'known_answer_control', 'record': r, 'error': error})
        if r['additive_linearity_max_error'] > 1e-9: failures.append({'path': 'additive_linearity', 'record': r})
    compare(json.loads((OUT / 'summary.json').read_text()), {
        'status': 'COMPLETE_UNAUDITED', 'contexts': 1, 'actual_product_conventions': 4,
        'held_duration_matched_cases': 96, 'signed_injection_cases': 64,
        'retained_cal_cor_bytes_read': 18560000, 'new_native_source_bytes': 0,
        'new_classifier': False, 'qualified_candidates_added': 0, 'qualified_coverage_added': False,
        'original_ls8ag_classifications_unchanged': True}, 'summary')
    result = {'status': 'PASS' if not failures else 'FAIL', 'comparisons': counts,
        'maximum_fraction_of_numeric_tolerance': maximum_scaled_error, 'failures': failures,
        'known_answer_signed_template_cases': truth_cases, 'signed_compact_cases': len(actual_controls) - truth_cases,
        'all_additive_cases': len(actual_controls), 'new_native_source_bytes': 0,
        'reference_method': 'struct decoding, long-double temporal normal equations and scalar covariance, independent weighted spatial normal equations and coordinate sets'}
    for name, value in [('independent_reference.json', references), ('independent_controls.json', injected), ('audit.json', result)]:
        (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    assert not failures, 'independent audit failed; preserve outcome without threshold changes'


if __name__ == '__main__':
    main()
