#!/usr/bin/env python3
"""Independent LS7I audit: scalar observations, augmented ridge LS, whitened fits.

No import of the new predictor, evaluator, summarizer or decision implementation.
The sealed LS7I input audit supplies unchanged historical recipe/temporal evidence.
"""
import argparse
from collections import Counter
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular
from scipy.ndimage import shift

from ls7f_review import direct_fit, independent_minima
from ls7g_review import pulse, temporal

ROOT = Path(__file__).resolve().parents[1]
METHODS = ['conditional', 'static']
SIGNALS = ['stellar', 'off_profile']
ERRORS = Counter()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]


def close(actual, expected, name, rtol=1e-8, atol=2e-8):
    ERRORS[name] = max(ERRORS[name], float(np.max(abs(np.asarray(actual)-np.asarray(expected)))))
    np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol, err_msg=name)


def observation(cube, ap, lo, hi):
    coords = list(zip(*np.where(ap)))
    indices = list(range(lo-60, lo-5))+list(range(hi+5, hi+60))
    assert len(indices) == 110 and lo >= 60 and hi <= len(cube)-60
    reference = np.array([[np.median(cube[indices, y, x]) for x in range(11)] for y in range(11)])
    differences = []
    # Use NumPy's frozen aperture-sum operation; independently enumerate each
    # difference, never one across the gap. A different sum order is immaterial.
    flux = cube[:, ap].sum(axis=1)
    for begin, end in [(lo-60, lo-5), (hi+5, hi+60)]:
        differences += [float(flux[i+1]-flux[i]) for i in range(begin, end-1)]
    median = np.median(differences)
    scale = float(1.482602218505602*np.median([abs(d-median) for d in differences])/np.sqrt(2.))
    assert scale > 0
    x = np.array([(sum(cube[i, y, z] for i in range(begin, end))/10-reference[y, z])/scale
                  for begin, end in [(lo-15, lo-5), (hi+5, hi+15)] for y, z in coords])
    y = np.array([(sum(cube[i, a, b] for i in range(lo, hi))/(hi-lo)-reference[a, b])/scale for a, b in coords])
    return x, y, scale, reference


def regression(samples, recorded):
    assert recorded['model_id'] == f's{recorded["sector"]:03d}/w{recorded["width"]}/exclude_'+','.join(map(str, recorded['excluded_anchors']))
    chosen = [r for r in samples if r['sector'] == recorded['sector'] and r['width'] == recorded['width']
              and r['anchor'] not in recorded['excluded_anchors']]
    assert recorded['training_ids'] == [r['sample_id'] for r in chosen]
    assert recorded['samples'] == len(chosen) == 13*(10-len(recorded['excluded_anchors']))
    assert recorded['training_anchors'] == sorted({r['anchor'] for r in chosen})
    x, y = [np.array([r[k] for r in chosen]) for k in ['x', 'y']]
    mx, my = x.mean(axis=0), y.mean(axis=0)
    xc, yc = x-mx, y-my
    penalty = float(np.sum(xc*xc)/((len(x)-1)*x.shape[1]))
    # An augmented least-squares solve, not the evaluator's normal equations.
    design = np.vstack([xc, np.sqrt((len(x)-1)*penalty)*np.eye(x.shape[1])])
    targets = np.vstack([yc, np.zeros((x.shape[1], y.shape[1]))])
    beta = np.linalg.lstsq(design, targets, rcond=None)[0]
    for key, val in [('x_mean', mx), ('y_mean', my), ('ridge_penalty', penalty), ('beta', beta)]:
        close(val, recorded[key], 'regression_'+key)
    assert recorded['ridge_strength'] == 1.
    return mx, my, beta


def predict(x, model, method):
    mx, my, beta = model
    return my+(np.asarray(x)-mx)@beta if method == 'conditional' else my


def templates(reference, ap, basecfg, cfg):
    coords = list(zip(*np.where(ap))); n = len(coords)
    profile = np.zeros((11, 11)); profile[ap] = np.maximum(reference[ap], 0.); profile /= profile.sum()
    stars = []
    for displacement in basecfg['spatial']['fit_shifts_yx']:
        p = shift(profile, displacement, order=1, mode='constant', cval=0., prefilter=False)
        p[~ap] = 0.; p /= p.sum(); stars.append(p[ap])
    nuisance, labels = [np.zeros(n)], ['uniform']
    for j in range(n):
        nuisance.append(np.eye(n)[j]); labels.append(f'pixel_{j}')
    for a in range(10):
        for b in range(10):
            p = np.array([int(a <= y < a+2 and b <= x < b+2) for y, x in coords])
            if any(p):
                nuisance.append(p); labels.append(f'block2_{a}_{b}')
    for dy, dx in basecfg['spatial']['pointing_template_shifts_yx']:
        image = np.nan_to_num(reference, nan=0.)
        moved = shift(image, [dy, dx], order=1, mode='nearest', prefilter=False)
        moved *= image.sum()/moved.sum()
        for sign in [1, -1]:
            nuisance.append(sign*(moved-image)[ap]); labels.append(f'pointing_{dy}_{dx}_{sign}')
    for h, w in cfg['rectangle_shapes']:
        for a in range(12-h):
            for b in range(12-w):
                p = np.array([int(a <= y < a+h and b <= x < b+w) for y, x in coords])
                if any(p):
                    nuisance.append(p); labels.append(f'rect{h}x{w}_{a}_{b}')
    masks = {'cross3x3': [[0, 1, 0], [1, 1, 1], [0, 1, 0]], 'ring3x3': [[1, 1, 1], [1, 0, 1], [1, 1, 1]],
             'triangle3x3': [[1, 1, 1], [0, 1, 1], [0, 0, 1]]}
    for family in cfg['shape_families']:
        for rotation in range(4 if family == 'triangle3x3' else 1):
            mask = np.rot90(masks[family], rotation)
            for a in range(9):
                for b in range(9):
                    p = np.array([mask[y-a, x-b] if a <= y < a+3 and b <= x < b+3 else 0 for y, x in coords])
                    if any(p):
                        nuisance.append(p); labels.append(f'{family}_r{rotation}_{a}_{b}')
    return np.array(stars), np.array(nuisance), labels


def audit_counts(trials, native, summary):
    cells = summary['core_cells']
    assert len(cells) == 72 and len(summary['per_background_cells']) == 720
    assert len({(c['sector'], c['suite'], c['kind'], c['target_score']) for c in cells}) == 72
    for cell in cells:
        selected = [r for r in trials if all(r[k] == cell[k] for k in ['sector', 'suite', 'kind', 'target_score'])]
        assert len(selected) == cell['trials']
        signal = cell['kind'] in SIGNALS; assert signal == cell['signal']
        assert cell['cohort'] == selected[0]['cohort'] and len({r['cohort'] for r in selected}) == 1
        limit = (36 if cell['kind'] == 'stellar' else 128) if signal else len(selected)//20
        assert cell['limit'] == limit
        assert len(selected) == (40 if cell['kind'] == 'stellar' else 160) if signal else len(selected) in [40, 80]
        for method in METHODS:
            value = sum(r['methods'][method]['decision']['recovered' if signal else 'accepted'] for r in selected)
            assert cell['methods'][method] == {'count': value, 'pass': value >= limit if signal else value <= limit,
                                                'headroom': value-limit if signal else limit-value}
    for bg in summary['per_background_cells']:
        rr = [r for r in trials if all(r[k] == bg[k] for k in ['sector', 'anchor', 'suite', 'kind', 'target_score'])]
        assert len(rr) == bg['trials']
        for method in METHODS:
            for key, n in bg['methods'][method].items():
                assert n == sum(r['methods'][method]['decision'][key] for r in rr)
    diagnostic_total = 0
    for group in summary['diagnostic_groups']:
        cohort, suite, kind, target, fraction, shape, displacement, location, polarity = group['key']
        rr = []
        for r in trials:
            if r['sector'] != group['sector'] or [r[k] for k in ['cohort', 'suite', 'kind', 'target_score', 'amplitude_fraction', 'shape', 'shift_yx']] != [cohort, suite, kind, target, fraction, shape, displacement]:
                continue
            d = r['residual']; loc = None if d is None else d['location']; sign = None if d is None else (1 if d['amplitude_e_per_s'] > 0 else -1)
            if loc == location and sign == polarity:
                rr.append(r)
        assert len(rr) == group['trials']; diagnostic_total += len(rr)
        for method in METHODS:
            for key in ['accepted', 'recovered', 'nuisance_preferred_acceptance']:
                assert group['methods'][method][key] == sum(r['methods'][method]['decision'][key] for r in rr)
            assert group['methods'][method]['paths'] == dict(Counter(r['methods'][method]['decision']['recovery_path'] for r in rr))
    assert diagnostic_total == 7080
    sector_pass = []
    for sector in [29, 32]:
        rr = [r for r in trials if r['sector'] == sector]; ss = summary['sectors'][str(sector)]
        assert ss['trials'] == len(rr) == 3540
        assert ss['historical_trials'] == (3540 if sector == 29 else 3180)
        assert ss['supplement_trials'] == (0 if sector == 29 else 360)
        assert ss['suites'] == dict(Counter(r['suite'] for r in rr))
        signal = [r for r in rr if r['kind'] in SIGNALS]
        bright = [r for r in rr if r['suite'] == 'base' and r['kind'] == 'stellar' and r['amplitude_fraction'] == .1 and r['shape'] != 'doublet30sep87']
        null = [r for r in rr if r['suite'] == 'base' and r['kind'] == 'null']
        pointing = [r for r in rr if r['suite'] == 'bounded_pointing' and r['best']['score'] >= 8]
        sc = [c for c in cells if c['sector'] == sector]
        for method in METHODS:
            mm = ss['methods'][method]
            tally = lambda rs, k: sum(r['methods'][method]['decision'][k] for r in rs)
            gates = {'all_core_cells': all(c['methods'][method]['pass'] for c in sc),
                     'all_target_strengths_matched': all(abs(r['best']['score']-r['target_score']) <= .01 for r in rr if r['target_score'] is not None and r['suite'] != 'sparse_stress'),
                     'ten_percent_single_recovery': tally(bright, 'recovered') >= 54,
                     'no_base_null_acceptance': tally(null, 'accepted') == 0,
                     'confounding_at_most_20_percent': sum(r['baseline_confounded'] for r in signal) <= .2*len(signal),
                     'bounded_pointing_screened_acceptance': bool(pointing) and tally(pointing, 'accepted') <= .05*len(pointing)}
            assert gates == mm['gates'] and all(gates.values()) == mm['trial_gate_pass']
            assert mm['failed_signal_cells'] == sum(c['signal'] and not c['methods'][method]['pass'] for c in sc)
            assert mm['failed_control_cells'] == sum(not c['signal'] and not c['methods'][method]['pass'] for c in sc)
            assert mm['confounded_signals'] == sum(r['baseline_confounded'] for r in signal)
            for name, selected in [('all_signals', signal), ('bright_single', bright), ('base_nulls', null), ('bounded_pointing', pointing)]:
                assert mm[name]['screened' if name == 'bounded_pointing' else 'trials'] == len(selected)
                for key in ['accepted', 'recovered', 'nuisance_preferred_acceptance']:
                    assert mm[name][key] == tally(selected, key)
        ratios, totals = [], {m: 0. for m in METHODS}
        for recorded in ss['native']['per_background']:
            nw = [r for r in native if r['sector'] == sector and r['anchor'] == recorded['anchor']]
            assert len(nw) == recorded['windows'] == 21
            es = {m: sum(r['energies'][m] for r in nw) for m in METHODS}
            ratio = es['conditional']/es['static']; ratios.append(ratio)
            close(ratio, recorded['ratio'], 'native_ratio')
            for m in METHODS:
                close(es[m], recorded[m], 'native_sum'); totals[m] += es[m]
        ratio = totals['conditional']/totals['static']; close(ratio, ss['native']['ratio'], 'native_total_ratio')
        ng = {'total_energy_not_increased': ratio <= 1., 'backgrounds_improved': sum(r < 1. for r in ratios) >= 6,
              'no_background_more_than_doubled': max(ratios) <= 2.}
        assert ng == ss['native']['gates'] and all(ng.values()) == ss['native']['pass']
        sector_pass.append(ss['methods']['conditional']['trial_gate_pass'] and all(ng.values()))
    assert all(sector_pass) == summary['development_requirements_pass']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7i_background')
    args = parser.parse_args(); out = args.output
    cfg = read(ROOT/'config/ls7i_background.json'); basecfg = read(ROOT/'config/ls7c_tess_l9859.json')
    for path, digest in cfg['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    for base, manifest in cfg['preserve_manifests']+[['.', 'LS7I_BACKGROUND_FREEZE.sha256']]:
        for line in (ROOT/base/manifest).read_text().splitlines():
            digest, path = line.split(maxsplit=1)
            assert hashlib.sha256((ROOT/base/path.strip()).read_bytes()).hexdigest() == digest, path
    raw = {}
    for d in read(ROOT/'results_ls7i_inputs/datasets.json'):
        with np.load(ROOT/d['contexts'], allow_pickle=False) as archive:
            raw[d['sector']] = {k: archive[k] for k in ['native', 'seconds', 'aperture', 'sigmas']}
    samples, regressions, folds, frames, trials, native, changes = [rows(out/name) for name in
        ['training.jsonl.gz', 'regressions.jsonl.gz', 'folds.jsonl.gz', 'frames.jsonl.gz', 'trials.jsonl.gz', 'native_windows.jsonl.gz', 'changes.jsonl.gz']]
    summary = read(out/'summary.json')
    assert len(samples) == summary['training_records'] == 780
    assert len(regressions) == summary['regressions'] == 330
    assert len(folds) == summary['nested_folds'] == 60
    assert len(trials) == len({r['case_id'] for r in trials}) == summary['trials'] == 7080
    assert len(native) == len({r['window_id'] for r in native}) == summary['native_windows'] == 420
    assert len(frames) == len({r['frame_id'] for r in frames}) == summary['spatial_frames']
    assert summary['historical_trials'] == 6720 and summary['supplement_trials'] == 360
    assert summary['protected_cases_checked'] == 7080 and summary['maximum_protection_feature_error'] == 0
    assert summary['backgrounds'] == 20 and summary['added_observing_days'] == 0 and summary['primary_method'] == 'conditional'
    assert summary['freeze_sha256'] == hashlib.sha256((ROOT/'LS7I_BACKGROUND_FREEZE.sha256').read_bytes()).hexdigest()
    expected_sample_ids = {f's{s:03d}/a{a:02d}/w{w}/s{start}' for s in [29, 32] for a in range(10) for w in [2, 3, 5] for start in cfg['training_starts']}
    assert {s['sample_id'] for s in samples} == expected_sample_ids
    for r in samples:
        d = raw[r['sector']]
        x, y, scale, _ = observation(d['native'][r['anchor']], d['aperture'], r['start'], r['stop'])
        assert r['stop'] == r['start']+r['width']
        for key, value in [('x', x), ('y', y), ('sigma', scale)]:
            close(value, r[key], 'training_'+key)
    expected_models = {f's{s:03d}/w{w}/exclude_'+','.join(map(str, exc)) for s in [29, 32] for w in [2, 3, 5]
                       for exc in [(a,) for a in range(10)]+list(combinations(range(10), 2))}
    assert {m['model_id'] for m in regressions} == expected_models
    model_map = {r['model_id']: regression(samples, r) for r in regressions}
    reg_records = {r['model_id']: r for r in regressions}
    fold_map, covariances = {f['fold_id']: f for f in folds}, {}
    assert set(fold_map) == {f's{s:03d}/a{a:02d}/w{w}' for s in [29, 32] for a in range(10) for w in [2, 3, 5]}
    for f in folds:
        outer, width, sector = f['excluded_anchor'], f['width'], f['sector']
        assert f['model_id'] == f's{sector:03d}/w{width}/exclude_{outer}'
        chosen = [r for r in samples if r['sector'] == sector and r['anchor'] != outer and r['width'] == width]
        assert f['calibration_ids'] == [r['sample_id'] for r in chosen] and len(chosen) == 117
        assert len(f['calibration_models']) == 117
        for m in METHODS:
            residuals = []
            for r, mid in zip(chosen, f['calibration_models']):
                expected = f's{sector:03d}/w{width}/exclude_'+','.join(map(str, sorted([outer, r['anchor']])))
                assert mid == expected and set(reg_records[mid]['training_anchors']).isdisjoint([outer, r['anchor']])
                residuals.append(np.asarray(r['y'])-predict(r['x'], model_map[mid], m))
            close(residuals, f['methods'][m]['residuals'], 'calibration_residuals')
            centered = np.array(residuals)-np.mean(residuals, axis=0)
            empirical = centered.T@centered/116
            floor = 1e-10*np.mean(np.diag(empirical))
            covariance = .95*empirical+.05*np.diag(np.diag(empirical))+floor*np.eye(len(empirical))
            close(empirical, f['methods'][m]['empirical_covariance'], 'empirical_covariance')
            close(covariance, f['methods'][m]['covariance'], 'nested_covariance')
            close(floor, f['methods'][m]['floor'], 'covariance_floor')
            close(np.linalg.eigvalsh(covariance), f['methods'][m]['eigenvalues'], 'covariance_eigenvalues')
            assert f['methods'][m]['shrinkage'] == .05
            np.linalg.cholesky(covariance); covariances[f['fold_id'], m] = covariance
    print('Verified 780 observable training samples, all 330 regressions and 60 nested covariance folds', flush=True)
    historical = rows(ROOT/'results_ls7i_inputs/trial_recipes.jsonl.gz')
    for r, old in zip(trials[:6720], historical):
        assert all(r[k] == value for k, value in old.items()) and r['cohort'] == 'historical'
    pattern_map = {p['pattern_id']: p for p in read(ROOT/'results_ls7i_inputs/patterns.json')}
    extra = rows(out/'supplement_recipes.jsonl.gz'); added = read(out/'supplement_patterns.json')
    assert len(extra) == 360 and len(added) == 30
    parent_map = {r['case_id']: r for r in historical}
    masks = {'cross3x3': np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]),
             'ring3x3': np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]]),
             'triangle3x3': np.array([[1, 1, 1], [0, 1, 1], [0, 0, 1]])}
    for p in added:
        d = raw[32]; ap = d['aperture']; ref = np.median(d['native'][p['anchor']], axis=0)
        profile = np.zeros((11, 11)); profile[ap] = np.maximum(ref[ap], 0.); profile /= profile.sum()
        mask = masks[p['kind']]; best, corner = -np.inf, None
        for a in range(9):
            for b in range(9):
                score = float(np.sum(profile[a:a+3, b:b+3]*mask))
                if score > best:
                    best, corner = score, [a, b]
        expected = np.zeros((11, 11)); a, b = corner; expected[a:a+3, b:b+3] = mask; expected /= expected[ap].sum()
        close(expected, p['vector'], 'supplement_pattern', atol=1e-12)
        assert p['sector'] == 32 and p['corner_yx'] == corner
        pattern_map[p['pattern_id']] = p
    assert {r['case_id'] for r in extra} == {r['case_id']+'/shape_supplement/'+kind for r in historical
        if r['sector'] == 32 and r['suite'] == 'base' and r['kind'] == 'stellar' and r['target_score'] is not None for kind in masks}
    for r, saved in zip(trials[6720:], extra):
        assert all(r[k] == v for k, v in saved.items())
        parent = parent_map[r['parent_case_id']]
        assert r['cohort'] == 'sector32_shape_supplement' and r['suite'] == 'unmodeled_shapes' and r['sector'] == 32
        for k in ['anchor', 'shape', 'target_score', 'amplitude_fraction', 'shift_yx', 'phase_seconds', 'sign', 'pattern_scale', 'residual', 'context_id']:
            assert r[k] == parent[k]
        assert r['source_parent_trial_id'] == parent['source_trial_id']
        for k in ['source_ledger', 'source_row', 'source_trial_id', 'source_suite', 'source_model_id']:
            assert r[k] is None
    references = {}
    for r in rows(ROOT/'results_ls7g_transfer/trials.jsonl.gz'):
        d = r['methods']['covariance_sparse']['decisions']['broad']['-1']
        references['s029/'+r['trial_id']] = {'ls7g_broad_minus1': {k: d[k] for k in ['accepted', 'recovered']}}
    for r in rows(ROOT/'results_ls7h_morphology/features.jsonl.gz'):
        d = r['decisions']['augmented']
        references['s029/'+r['trial_id']]['ls7h_augmented_minus1'] = {k: d[k] for k in ['accepted', 'recovered']}
    for r in rows(ROOT/'results_ls7f_separation/features.jsonl.gz'):
        d = r['methods']['covariance_sparse']; accepted = d['eligible_without_margin'] and d['margins']['broad'] >= -1
        references['s032/'+r['trial_id']] = {'ls7f_broad_minus1': {'accepted': bool(accepted), 'recovered': bool(accepted and not r['baseline_confounded'])}}
    frame_map, template_map = {f['frame_id']: f for f in frames}, {}
    for f in frames:
        d = raw[f['sector']]
        x, _, scale, ref = observation(d['native'][f['anchor']], d['aperture'], f['start'], f['stop'])
        close(x, f['x'], 'frame_x'); close(scale, f['sigma'], 'frame_sigma'); close(ref, f['reference'], 'frame_reference')
        stars, nuisance, labels = templates(ref, d['aperture'], basecfg, cfg)
        close(stars, f['star_templates'], 'star_templates'); close(nuisance, f['nuisance_templates'], 'nuisance_templates')
        assert labels == f['nuisance_labels']
        assert f['fold_id'] == f's{f["sector"]:03d}/a{f["anchor"]:02d}/w{f["stop"]-f["start"]}'
        template_map[f['frame_id']] = {'star': stars, 'nuisance': nuisance}
        for m in METHODS:
            close(predict(x, model_map[fold_map[f['fold_id']]['model_id']], m), f['predictions'][m], 'frame_prediction')
    for i, r in enumerate(trials):
        d = raw[r['sector']]; a = r['anchor']; ap = d['aperture']
        p, centers = pulse(d['seconds'][a], r['phase_seconds'], r['shape'])
        addition = (p*r['pattern_scale'])[:, None, None]*np.asarray(pattern_map[r['pattern_id']]['vector'])
        if r['residual'] is not None:
            res = r['residual']; y, x = res['pixel_yx']; addition[res['start']:res['stop'], y, x] += res['amplitude_e_per_s']
        lo, hi = r['best']['start'], r['best']['stop']
        np.testing.assert_array_equal(addition[np.r_[lo-60:lo-5, hi+5:hi+60]], 0.)
        cube = d['native'][a]+addition
        f = frame_map[r['frame_id']]
        assert [f[k] for k in ['sector', 'anchor', 'start', 'stop']] == [r['sector'], a, lo, hi]
        # All sideband additions are exactly zero; avoid repeating the 110-sample
        # median for every repeated injection on the same frame.
        y = (np.mean(cube[lo:hi, ap], axis=0)-np.asarray(f['reference'])[ap])/f['sigma']
        close(y, r['normalized_event'], 'trial_response')
        if r['cohort'] != 'historical':
            for name, flux in [('best', cube[:, ap].sum(axis=1)), ('native_best', d['native'][a][:, ap].sum(axis=1))]:
                expected = temporal(flux, d['seconds'][a], centers, d['sigmas'][a], r['sign'])
                assert all(expected[k] == r[name][k] for k in ['start', 'stop'])
                close(expected['score'], r[name]['score'], 'supplement_temporal')
        assert r['references'] == references.get(r['case_id'], {})
        assert r['screen_detected'] == (r['best']['score'] >= 8) and r['baseline_confounded'] == (r['native_best']['score'] >= 8)
        for m in METHODS:
            mm = r['methods'][m]
            close(r['sign']*(y-f['predictions'][m]), mm['residual'], 'trial_residual')
            s, n = mm['star'], mm['nuisance']; margin = n['objective']-s['objective']
            gates = {'temporal_screen': r['best']['score'] >= 8, 'source_score': s['amplitude_noise_score'] >= 5,
                     'weighted_residual': s['chi2']/s['residual_dof'] <= 2, 'nuisance_margin': margin >= -1}
            accepted = bool(all(gates.values())); path = 'confounded' if r['baseline_confounded'] else 'recovered'
            for key in ['nuisance_margin', 'weighted_residual', 'source_score', 'temporal_screen']:
                if not gates[key]:
                    path = key
            expected = {'accepted': accepted, 'recovered': accepted and not r['baseline_confounded'],
                        'nuisance_preferred_acceptance': accepted and margin < 0, 'gates': gates, 'recovery_path': path, 'margin': margin}
            assert mm['decision'] == expected
            assert mm['nuisance_label'] == f['nuisance_labels'][n['template_index']]
        if (i+1) % 1200 == 0:
            print(f'Checked reconstruction, protection and decisions: {i+1}/7080', flush=True)
    direct_count, alternatives = 0, 0
    for i, f in enumerate(frames):
        rr = [r for r in trials if r['frame_id'] == f['frame_id']]
        assert rr
        for m in METHODS:
            chol = np.linalg.cholesky(covariances[f['fold_id'], m])
            vectors = np.array([r['methods'][m]['residual'] for r in rr])
            for key in ['star', 'nuisance']:
                bank = template_map[f['frame_id']][key]
                minimum = independent_minima(vectors, bank, chol, True, 9.)
                close(minimum, [r['methods'][m][key]['objective'] for r in rr], 'full_bank_minimum', rtol=1e-7, atol=2e-7)
                alternatives += len(rr)*len(bank)*(chol.shape[0]+1)
                for r, vector in zip(rr, vectors):
                    fit = r['methods'][m][key]
                    expected = direct_fit(vector, bank[fit['template_index']], chol, fit['sparse_pixel'], 9.)
                    for quantity, val in expected.items():
                        close(val, fit[quantity], 'direct_'+quantity, rtol=1e-7, atol=2e-7)
                    # Also check every stored winning coefficient in observable
                    # units, independently of the objective/minimum checks.
                    pixel = fit['sparse_pixel']; n = len(vector)
                    basis = np.ones((n, 1)) if pixel is None else np.column_stack([np.ones(n), np.eye(n)[:, pixel]])
                    bw = solve_triangular(chol, basis, lower=True)
                    pw = solve_triangular(chol, bank[fit['template_index']], lower=True)
                    yw = solve_triangular(chol, vector, lower=True)
                    pr = pw-bw@np.linalg.lstsq(bw, pw, rcond=None)[0]
                    yr = yw-bw@np.linalg.lstsq(bw, yw, rcond=None)[0]
                    norm = float(pr@pr)
                    amplitude = max(0., float(pr@yr)/norm) if norm > 1e-12*float(pw@pw) else 0.
                    beta = np.linalg.lstsq(bw, yw-amplitude*pw, rcond=None)[0]
                    close(amplitude, fit['amplitude'], 'direct_amplitude', rtol=1e-7, atol=2e-7)
                    close(beta[0], fit['background'], 'direct_background', rtol=1e-7, atol=2e-7)
                    if pixel is None:
                        assert fit['sparse_amplitude'] is None
                    else:
                        close(beta[1], fit['sparse_amplitude'], 'direct_sparse_amplitude', rtol=1e-7, atol=2e-7)
                    assert fit['residual_dof'] == len(vector)-(2 if fit['sparse_pixel'] is None else 3)
                    direct_count += 1
        if (i+1) % 30 == 0:
            print(f'Whitened direct fits and exhaustive minima: {i+1}/{len(frames)} frames', flush=True)
    expected_native = {f's{s:03d}/a{a:02d}/w{w}/s{start}' for s in [29, 32] for a in range(10) for w in [2, 3, 5] for start in cfg['native_starts']}
    assert {r['window_id'] for r in native} == expected_native
    for r in native:
        d = raw[r['sector']]
        x, y, scale, _ = observation(d['native'][r['anchor']], d['aperture'], r['start'], r['stop'])
        for key, val in [('x', x), ('y', y), ('sigma', scale)]:
            close(val, r[key], 'native_'+key)
        f = fold_map[r['fold_id']]
        assert [f[k] for k in ['sector', 'excluded_anchor', 'width']] == [r['sector'], r['anchor'], r['stop']-r['start']]
        chol = np.linalg.cholesky(covariances[r['fold_id'], 'static']); one = solve_triangular(chol, np.ones(len(y)), lower=True)
        for m in METHODS:
            pred = predict(x, model_map[f['model_id']], m); close(pred, r['predictions'][m], 'native_prediction')
            residual = solve_triangular(chol, y-pred, lower=True)
            residual -= one*(one@residual)/(one@one)
            close(residual@residual, r['energies'][m], 'native_energy')
    audit_counts(trials, native, summary)
    change_map = {(r['case_id'], r['reference']): r for r in changes}
    assert len(change_map) == len(changes) == summary['changed_row_reference_pairs']
    checked_changes = 0
    for c in summary['comparisons']:
        selected = [r for r in trials if r['sector'] == c['sector'] and (c['reference'] == 'static' or c['reference'] in r['references'])]
        assert len(selected) == c['paired_trials']
        counts = Counter(); previous_recovered, conditional_recovered, signal_rows = 0, 0, 0
        for r in selected:
            old = r['methods']['static']['decision'] if c['reference'] == 'static' else r['references'][c['reference']]
            new = r['methods']['conditional']['decision']; signal = r['kind'] in SIGNALS
            if signal:
                signal_rows += 1; previous_recovered += old['recovered']; conditional_recovered += new['recovered']
            field = 'recovered' if signal else 'accepted'; pair = r['case_id'], c['reference']
            if old[field] == new[field]:
                assert pair not in change_map; continue
            change = ('stellar_gains' if new[field] else 'stellar_losses') if signal else ('controls_newly_accepted' if new[field] else 'controls_newly_rejected')
            record = change_map[pair]; counts[change] += 1; checked_changes += 1
            assert record['change'] == change and record['before'] == old[field] and record['after'] == new[field]
            assert record['conditional'] == new
            for key in ['case_id', 'sector', 'anchor', 'cohort', 'suite', 'kind', 'target_score', 'amplitude_fraction', 'shape', 'shift_yx', 'residual']:
                assert record[key] == r[key]
        assert c['signal_rows'] == signal_rows and c['control_rows'] == len(selected)-signal_rows
        assert c['reference_recovered'] == previous_recovered and c['conditional_recovered'] == conditional_recovered
        for key in ['stellar_gains', 'stellar_losses', 'controls_newly_accepted', 'controls_newly_rejected']:
            assert c[key] == counts[key]
    assert checked_changes == len(changes) and direct_count == 28320
    audit = {'passed': True, 'scope': 'independent arithmetic, full minima, protection, exclusions, cohorts, decisions and loss accounting',
             'training_records': len(samples), 'regressions': len(regressions), 'nested_folds': len(folds),
             'historical_recipes': 6720, 'supplement_trials': 360, 'protected_trials': len(trials),
             'direct_fits': direct_count, 'fit_alternatives': alternatives, 'native_windows': len(native),
             'core_cells': 72, 'background_cells': 720, 'diagnostic_groups': len(summary['diagnostic_groups']),
             'changed_row_reference_pairs': checked_changes, 'maximum_errors': dict(ERRORS),
             'historical_input_audit_reused_by_hash': True, 'development_requirements_pass': summary['development_requirements_pass']}
    destination = out/('AUDIT_RECHECK.json' if (out/'AUDIT.json').exists() else 'AUDIT.json')
    destination.write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
