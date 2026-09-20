#!/usr/bin/env python3
"""Independent raw-byte, long-double and scalar normal-equation LS8M audit.

Does not import the producer or its numerical module. Rebuilds all reported
native, leave-one-sideband, injection and spatial-accounting quantities.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8m_residuals'
LD = np.longdouble
ROW = struct.Struct('>26sddddii7d4f')
MODEL_COLUMNS = {'brightness': (0, 3), 'displacement': (1, 2, 3), 'combined': (0, 1, 2, 3)}


def total(a):
    return float(np.asarray(a, dtype=LD).sum())


def reconstruct(times, cube, train, target, valid, center):
    t = np.asarray(times, dtype=LD)
    values = cube[train][:, valid].astype(LD)
    offset = np.median(values, axis=0); z = values - offset
    n = LD(len(train)); sx = t[train].sum(); sx2 = (t[train] ** 2).sum()
    sy = z.sum(axis=0); sxy = (t[train, None] * z).sum(axis=0)
    determinant = n * sx2 - sx * sx
    a = (sy * sx2 - sxy * sx) / determinant
    b = (n * sxy - sx * sy) / determinant
    side = z - a - t[train, None] * b
    event = cube[target][valid].astype(LD) - offset - a - t[target] * b
    h = float(1 + 1 / n + (t[target] - sx / n) ** 2 / (sx2 - sx * sx / n))
    mean = np.full(valid.shape, np.nan); mean[valid] = values.sum(axis=0) / n
    yy, xx = np.indices(valid.shape)
    radius = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    annulus = valid & (radius > 900) & (radius <= 1600)
    profile = mean - float(np.median(mean[annulus]))
    gx = np.full_like(profile, np.nan); gy = gx.copy()
    gx[:, 1:-1] = 0.5 * (profile[:, 2:] - profile[:, :-2])
    gy[1:-1] = 0.5 * (profile[2:] - profile[:-2])
    mask = valid & (radius <= 625) & np.isfinite(gx) & np.isfinite(gy)
    use = mask[valid]
    s = np.asarray(side[:, use], float); y = np.asarray(event[use], float)
    variance = np.asarray((side[:, use] ** 2).sum(axis=0) / (n - 2), float)
    x = np.column_stack([profile[mask], gx[mask], gy[mask], np.ones(mask.sum())])
    return {'y': y, 'side': s, 'x': x, 's2': variance,
            'variance': h * (variance + float(np.median(variance))) / 2,
            'h': h, 'df': len(train) - 2, 'mask': mask,
            'xy': np.column_stack([xx[mask], yy[mask]]), 'center': np.asarray(center)}


def regression_matrix(x, variance):
    # Scalar fsum cross-products and normal equations, distinct from producer SVD.
    cols = [(x[:, i] / np.sqrt(variance)).tolist() for i in range(x.shape[1])]
    norms = [math.sqrt(math.fsum(v * v for v in c)) for c in cols]
    normalized = [np.asarray(c) / n for c, n in zip(cols, norms)]
    gram = np.array([[math.fsum(float(a) * float(b) for a, b in zip(c, d))
                     for d in normalized] for c in normalized])
    rhs = np.array(normalized) / np.sqrt(variance)[None, :]
    mapping = np.linalg.solve(gram, rhs) / np.asarray(norms)[:, None]
    sv = np.linalg.svd(np.column_stack(normalized), compute_uv=False)
    assert np.sum(sv > sv[0] * 1e-12) == x.shape[1]
    return mapping, float(sv[0] / sv[-1])


def model(state, columns):
    x = state['x'][:, columns]; y = state['y']; s = state['side']
    mapping, condition = regression_matrix(x, state['variance'])
    beta = np.asarray(mapping, dtype=LD) @ np.asarray(y, dtype=LD)
    residual = np.asarray(y, dtype=LD) - np.asarray(x, dtype=LD) @ beta
    bs = np.asarray(s, dtype=LD) @ np.asarray(mapping.T, dtype=LD)
    rs = np.asarray(s, dtype=LD) - bs @ np.asarray(x.T, dtype=LD)
    w = np.asarray(state['variance'], dtype=LD)
    e = total(residual ** 2); we = total(residual ** 2 / w)
    noise = state['h'] * total(rs ** 2) / state['df']
    wn = state['h'] * total(rs ** 2 / w) / state['df']
    csd = np.sqrt(state['h'] * (bs ** 2).sum(axis=0) / state['df'])
    fsd = math.sqrt(state['h'] * total(np.asarray(s, dtype=LD).sum(axis=1) ** 2) / state['df'])
    dsd = math.sqrt(state['h'] * total(state['s2']))
    ey = total(np.asarray(y, dtype=LD) ** 2); ewy = total(np.asarray(y, dtype=LD) ** 2 / w)
    result = {'coefficients': np.asarray(beta, float).tolist(), 'coefficient_sideband_sd': np.asarray(csd, float).tolist(),
        'condition': condition, 'raw_explained': 1 - e / ey if ey else None,
        'weighted_explained': 1 - we / ewy if ewy else None,
        'residual_energy_adu2': e, 'weighted_residual_energy': we,
        'expected_residual_energy_adu2': noise, 'expected_weighted_residual_energy': wn,
        'residual_to_sideband_energy_ratio': e / noise if noise else None,
        'weighted_residual_to_sideband_ratio': we / wn if wn else None,
        'event_flux_adu': total(y), 'residual_flux_adu': total(residual),
        'residual_flux_sideband_sd_adu': math.sqrt(state['h'] * total(rs.sum(axis=1) ** 2) / state['df']),
        'aperture_sideband_sd_adu': fsd, 'diagonal_aperture_sd_adu': dsd,
        'aperture_correlation_sd_ratio': fsd / dsd}
    return result, np.asarray(residual, float)


def cells(state, residual):
    raw = np.asarray(residual, dtype=LD) ** 2; weighted = raw / state['variance']
    er, ew = total(raw), total(weighted)
    memberships = [[] for _ in range(12)]
    for i, (x, y) in enumerate(state['xy']):
        dx, dy = x - state['center'][0], y - state['center'][1]
        radius = dx * dx + dy * dy
        r = 0 if radius <= 64 else (1 if radius <= 256 else 2)
        q = (0 if dx >= 0 else 1) if dy >= 0 else (2 if dx < 0 else 3)
        memberships[r * 4 + q].append(i)
    rows = []
    for i, use in enumerate(memberships):
        rows.append({'ring': i // 4, 'quadrant': i % 4, 'pixels': len(use),
            'flux_adu': total(residual[use]), 'raw_energy_fraction': total(raw[use]) / er if er else None,
            'weighted_energy_fraction': total(weighted[use]) / ew if ew else None})
    concentration = {}
    for name, v in [('raw', raw), ('weighted', weighted)]:
        order = sorted(range(len(v)), key=lambda i: (-v[i], i)); energy = total(v)
        concentration[name] = {'top1_fraction': total(v[order[:1]]) / energy if energy else None,
            'top10_fraction': total(v[order[:10]]) / energy if energy else None,
            'maximum_xy': state['xy'][order[0]].tolist()}
    return {'cells': rows, 'concentration': concentration}


def description(state):
    fits = {}; residual = None
    for name, columns in MODEL_COLUMNS.items():
        fits[name], rr = model(state, columns)
        if name == 'combined': residual = rr
    return {'pixels': len(state['y']), 'sideband_df': state['df'], 'leverage': state['h'],
        'median_sideband_variance_adu2': float(np.median(state['s2'])),
        'models': fits, 'spatial': cells(state, residual)}, residual


def paired(cal, cor):
    x = cor['x']; mapping, _ = regression_matrix(x, cor['variance'])
    rr = {}
    for name, y in [('CAL', cal['y']), ('COR', cor['y']), ('DELTA', cor['y'] - cal['y'])]:
        rr[name] = np.asarray(y, dtype=LD) - np.asarray(x, dtype=LD) @ (np.asarray(mapping, dtype=LD) @ np.asarray(y, dtype=LD))
    result = {}
    for name, weight in [('raw', np.ones(len(cor['y']), dtype=LD)), ('weighted', 1 / np.asarray(cor['variance'], dtype=LD))]:
        ec = total(weight * rr['COR'] ** 2); ea = total(weight * rr['CAL'] ** 2); ed = total(weight * rr['DELTA'] ** 2)
        cross = 2 * total(weight * rr['CAL'] * rr['DELTA'])
        result[name] = {'cor_energy': ec, 'cal_energy': ea, 'delta_energy': ed, 'twice_cross_energy': cross,
            'cal_over_cor': ea / ec, 'delta_over_cor': ed / ec, 'twice_cross_over_cor': cross / ec,
            'closure_relative_error': (ec - ea - ed - cross) / max(1., ec + ea + ed + abs(cross))}
    return result


def controls(state):
    x = state['x']; y = state['y']; xy = state['xy']
    combined, _ = regression_matrix(x, state['variance'])
    xd = x[:, (1, 2, 3)]; displacement, _ = regression_matrix(xd, state['variance'])
    cases = []
    specs = [('brightness', 0, 0.001), ('shift_x', 1, 0.05), ('shift_y', 2, 0.05)]
    for name, column, scale in specs:
        truth = np.zeros(4); truth[column] = scale
        cases.append((name, x[:, column] * scale, truth))
    for j, (dx, dy) in enumerate([(0, 0), (10, 0), (0, 10), (-10, 0), (0, -10)]):
        target = state['center'] + [dx, dy]
        i = min(range(len(xy)), key=lambda k: (float(np.sum((xy[k] - target) ** 2)), k))
        pulse = np.zeros(len(x)); pulse[i] = 5 * math.sqrt(state['variance'][i])
        cases.append((f'compact_{j}', pulse, None))
    results = []
    for name, plus, truth in cases:
        for sign in (-1, 1):
            pulse = sign * plus; pure = combined @ pulse
            incremental = combined @ (y + pulse) - combined @ y
            residual = pulse - xd @ (displacement @ pulse)
            flux = total(pulse)
            results.append({'kind': name, 'sign': sign,
                'expected_combined_coefficients': (sign * truth).tolist() if truth is not None else None,
                'pure_combined_coefficients': pure.tolist(), 'additive_coefficient_increment': incremental.tolist(),
                'additive_linearity_max_error': float(np.max(np.abs(incremental - pure))),
                'displacement_removal_retained_weighted_energy_fraction': total(np.asarray(residual, dtype=LD) ** 2 / state['variance']) / total(np.asarray(pulse, dtype=LD) ** 2 / state['variance']),
                'displacement_removal_flux_fraction': total(residual) / flux if abs(flux) > 1e-10 * total(np.abs(pulse)) else None,
                'injected_flux_adu': flux})
    return results


def main():
    cfg = json.loads((ROOT / 'config/ls8m_residuals.json').read_text())
    original = json.loads((ROOT / 'config/ls8l_images.json').read_text())
    for name, digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    actual = json.loads((OUT / 'diagnostics.json').read_text())
    old = {v['id']: v for v in json.loads((ROOT / 'results_ls8l_images/diagnostics.json').read_text())}
    failures = []; counts = {'numeric': 0, 'exact': 0}; maximum_scaled_error = 0.

    def compare(a, b, path, array_native=False):
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
            scaled = float(np.max(diff / tolerance, initial=0))
            maximum_scaled_error = max(maximum_scaled_error, scaled)
            if not np.isfinite(diff).all() or np.any(diff > tolerance):
                failures.append({'path': path, 'reason': 'array numerical mismatch', 'maximum_scaled_error': scaled})
        elif isinstance(b, dict):
            counts['exact'] += 1
            if set(a) != set(b): failures.append({'path': path, 'reason': 'keys mismatch'}); return
            for k, v in b.items(): compare(a[k], v, path + '.' + k)
        elif isinstance(b, list):
            counts['exact'] += 1
            if len(a) != len(b): failures.append({'path': path, 'reason': 'length mismatch'}); return
            for i, v in enumerate(b): compare(a[i], v, path + f'[{i}]')
        elif isinstance(b, float):
            counts['numeric'] += 1
            dimensionless = any(s in path for s in ('fraction', 'ratio', 'explained', 'condition', 'leverage', 'over_cor', 'closure_relative', 'coefficients', 'linearity'))
            tolerance = (1e-8 if dimensionless else 1e-6) + 2e-8 * abs(b)
            diff = abs(a - b) if isinstance(a, (int, float)) else math.inf
            maximum_scaled_error = max(maximum_scaled_error, diff / tolerance)
            if not math.isfinite(diff) or diff > tolerance:
                failures.append({'path': path, 'actual': a, 'reference': b, 'tolerance': tolerance})
        else:
            counts['exact'] += 1
            if a != b: failures.append({'path': path, 'actual': a, 'reference': b})

    references = []; injection_reference = []
    for c in original['contexts']:
        key = c['file_key']
        rawrows = (ROOT / 'results_ls8k_l2_screen' / key / 'lightcurve_table.bin').read_bytes()
        rows = list(ROW.iter_unpack(rawrows))[c['lo']:c['hi']]
        times = np.array([(LD(r[2]) - LD(rows[14][2])) * 86400 for r in rows], dtype=LD)
        side = list(range(12)) + list(range(17, 29)); arrays = {}
        for kind in ('CAL', 'COR'):
            path = ROOT / 'results_ls8l_images' / c['id'] / f'SCI_{kind}_SubArray.bin.gz'
            receipt = json.loads(path.with_suffix(path.suffix + '.json').read_text())
            raw = gzip.decompress(path.read_bytes())
            assert hashlib.sha256(raw).hexdigest() == receipt['raw_sha256']
            arrays[kind] = np.fromiter((v[0] for v in struct.iter_unpack('>d', raw)), dtype=float).reshape(29, 200, 200)
        valid = np.ones((200, 200), bool)
        for i in side + [14]: valid &= np.isfinite(arrays['CAL'][i]) & np.isfinite(arrays['COR'][i])
        spec = original['sources'][key]['SCI_COR_SubArray']
        center = [math.fsum(rows[i][16] for i in side) / 24 - spec['xoff'], math.fsum(rows[i][17] for i in side) / 24 - spec['yoff']]
        item = {'id': c['id'], 'sign': c['sign'], 'original_ls8l_classification': old[c['id']]['classification'], 'conventions': {}}
        with np.load(ROOT / 'results_ls8l_images' / c['id'] / 'event_maps.npz') as previous:
            compare(valid, previous['COMMON'], c['id'] + '.unchanged_common')
        for number in (0, 1):
            conv = f'C{number}'; cc = np.asarray(center) - number
            data = {}; states = {}
            with np.load(OUT / c['id'] / f'{conv}_arrays.npz') as saved:
                compare(saved['COMMON'], valid, c['id'] + '.' + conv + '.COMMON')
                for kind in ('CAL', 'COR'):
                    state = reconstruct(times, arrays[kind], side, 14, valid, cc)
                    states[kind] = state; result, residual = description(state)
                    for name in ('y', 'side', 'x', 'variance', 's2', 'mask', 'xy'):
                        compare(saved[f'{kind}_{name}'], state[name], c['id'] + '.' + conv + '.' + kind + '.' + name)
                    compare(saved[f'{kind}_residual'], residual, c['id'] + '.' + conv + '.' + kind + '.residual')
                    result['loso'] = []
                    for held in side:
                        refstate = reconstruct(times, arrays[kind], [i for i in side if i != held], held, valid, cc)
                        refresult, _ = description(refstate)
                        result['loso'].append({'held_local_row': held, **refresult})
                    value = result['models']['combined']['weighted_residual_to_sideband_ratio']
                    result['loso_at_least_event'] = sum(r['models']['combined']['weighted_residual_to_sideband_ratio'] >= value for r in result['loso'])
                    result['loso_count'] = 24
                    result['original_ls8l_unweighted_fits'] = old[c['id']]['conventions'][conv]['fits'][kind]
                    data[kind] = result
                    injection_reference.extend({'id': c['id'], 'convention': conv, 'product': kind, **r} for r in controls(state))
            data['correction_residual_account'] = paired(states['CAL'], states['COR'])
            data['center'] = cc.tolist(); item['conventions'][conv] = data
        references.append(item)
        print(c['id'], 'independent reconstruction complete', flush=True)
    compare(actual, references, 'diagnostics')
    actual_controls = json.loads((OUT / 'injection_controls.json').read_text())
    compare(actual_controls, injection_reference, 'injection_controls')
    truth_cases = 0
    for r in actual_controls:
        if r['expected_combined_coefficients'] is not None:
            truth_cases += 1
            error = max(abs(a - b) for a, b in zip(r['pure_combined_coefficients'], r['expected_combined_coefficients']))
            if error > 1e-9: failures.append({'path': 'known_answer_control', 'record': r, 'error': error})
        if r['additive_linearity_max_error'] > 1e-9:
            failures.append({'path': 'additive_linearity_control', 'record': r})
    result = {'status': 'PASS' if not failures else 'FAIL', 'comparisons': counts,
        'maximum_fraction_of_numeric_tolerance': maximum_scaled_error, 'failures': failures,
        'known_answer_signed_template_cases': truth_cases, 'signed_compact_cases': len(actual_controls) - truth_cases,
        'all_additive_cases': len(actual_controls), 'new_native_source_bytes': 0,
        'reference_method': 'independent struct decoding, long-double temporal normal equations, scalar-fsum weighted spatial normal equations'}
    (OUT / 'independent_reference.json').write_text(json.dumps(references, indent=2, allow_nan=False) + '\n')
    (OUT / 'independent_controls.json').write_text(json.dumps(injection_reference, indent=2, allow_nan=False) + '\n')
    (OUT / 'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    assert not failures, 'independent audit failed; preserve outcome without threshold changes'


if __name__ == '__main__':
    main()
