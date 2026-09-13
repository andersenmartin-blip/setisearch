#!/usr/bin/env python3
"""Audit LS7E with direct whitened least squares and independent accounting."""
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular

ROOT = Path(__file__).resolve().parents[1]


def scalar_fit(y, template, chol, pixel, penalty):
    n = len(y)
    b = np.ones((n, 1)) if pixel is None else np.column_stack((np.ones(n), np.eye(n)[:, pixel]))
    yw = solve_triangular(chol, y, lower=True)
    pw = solve_triangular(chol, template, lower=True)
    bw = solve_triangular(chol, b, lower=True)
    pr = pw-bw @ np.linalg.lstsq(bw, pw, rcond=None)[0]
    yr = yw-bw @ np.linalg.lstsq(bw, yw, rcond=None)[0]
    norm = float(pr@pr)
    amp = max(0., float(pr@yr)/norm) if norm > 1e-12*float(pw@pw) else 0.
    beta = np.linalg.lstsq(bw, yw-amp*pw, rcond=None)[0]
    residual = yw-amp*pw-bw @ beta
    chi = float(residual@residual)
    return {'chi2': chi, 'objective': chi+(penalty if pixel is not None else 0.),
            'amplitude': amp, 'amplitude_noise_score': float(amp*np.sqrt(norm)),
            'background': float(beta[0]), 'sparse_amplitude': None if pixel is None else float(beta[1])}


def main():
    output = ROOT/'results_ls7e_joint'
    cfg = json.loads((ROOT/'config/ls7e_joint.json').read_text())
    rows = [json.loads(r) for r in gzip.decompress((output/'trials.jsonl.gz').read_bytes()).splitlines()]
    old = {r['trial_id']: r for r in json.loads((ROOT/'results_ls7c_tess/trials.json').read_text())}
    models = {r['model_id']: r for r in json.loads((output/'models.json').read_text())}
    training = json.loads((output/'training.json').read_text())
    oldcfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
    summary = json.loads((output/'summary.json').read_text())
    assert len(rows) == 3180 == summary['total_trials']
    assert len({r['trial_id'] for r in rows}) == len(rows)
    assert {s: sum(r['suite'] == s for r in rows) for s in cfg['expected_suites']} == cfg['expected_suites']
    covariance_error = 0.
    for fold in training['folds']:
        samples = [r for r in training['samples'] if r['width'] == fold['width'] and r['anchor'] != fold['excluded_anchor']]
        assert len(samples) == 45 and sorted({r['anchor'] for r in samples}) == fold['training_anchors']
        assert [r['sample_id'] for r in samples] == fold['training_ids']
        x = [r['normalized_delta'] for r in samples]
        mu = [sum(v[j] for v in x)/45 for j in range(18)]
        manual = np.array([[sum((v[i]-mu[i])*(v[j]-mu[j]) for v in x)/44
                            for j in range(18)] for i in range(18)])
        covariance_error = max(covariance_error, float(np.max(np.abs(manual-np.asarray(fold['empirical_covariance'])))))
        np.testing.assert_allclose(manual, fold['empirical_covariance'], rtol=1e-12, atol=1e-12)
        want = (1-cfg['shrinkage'])*manual+cfg['shrinkage']*np.diag(np.diag(manual))+np.eye(18)*np.trace(manual)/18*1e-10
        np.testing.assert_allclose(want, fold['covariance'], rtol=1e-12, atol=1e-12)
    maxima = {k: 0. for k in ('chi2', 'objective', 'amplitude', 'amplitude_noise_score')}
    exhaustive = set()
    fit_count, exhaustive_fits, originals = 0, 0, 0
    chol_cache = {}
    for r in rows:
        model = models[r['model_id']]
        assert r['best']['start'] == model['start'] and r['best']['stop'] == model['stop'] and r['anchor'] == model['anchor']
        width = model['stop']-model['start']
        fold = next(f for f in training['folds'] if f['width'] == width and f['excluded_anchor'] == r['anchor'])
        sigma = next(v['sigma'] for v in training['samples'] if v['anchor'] == r['anchor'])
        np.testing.assert_allclose(model['covariance'], np.asarray(fold['covariance'])*sigma**2, rtol=1e-12)
        assert r['screen_detected'] == (r['best']['score'] >= 8.)
        assert r['baseline_confounded'] == (r['native_best']['score'] >= 8.)
        if r['suite'] == 'ls7c_replay':
            original = old[r['original']['trial_id']]
            for k in ('accepted', 'recovered', 'spatial_pass'):
                assert r['original'][k] == original[k]
            assert abs(r['best']['score']-original['best']['score']) <= 1e-8
            assert all(r['best'][k] == original['best'][k] for k in ('start', 'stop'))
            assert r['screen_detected'] == original['screen_detected']
            originals += 1
        if r['suite'] == 'extended':
            assert abs(r['best']['score']-r['target_score']) <= .01
        if r['suite'] == 'physical_pointing':
            assert r['pattern_multiplier'] == 1. and max(abs(v) for v in r['shift_yx']) <= .2
        y = np.asarray(r['event_vector'])
        representative = (r['anchor'], r['suite'])
        full = representative not in exhaustive
        for method, d in r['methods'].items():
            ck = (r['model_id'], method)
            if ck not in chol_cache:
                c = np.asarray(model['covariance'])
                if method == 'diagonal_sparse':
                    c = np.diag(np.diag(c))
                chol_cache[ck] = np.linalg.cholesky(c)
            chol = chol_cache[ck]
            for hypothesis in ('star', 'nuisance'):
                f = d[hypothesis]
                templates = np.asarray(model[hypothesis+'_templates'])
                actual = scalar_fit(y, templates[f['template_index']], chol, f['sparse_pixel'], cfg['sparse_penalty'])
                for k in maxima:
                    maxima[k] = max(maxima[k], abs(actual[k]-f[k]))
                    if not np.isclose(actual[k], f[k], rtol=1e-7, atol=2e-7):
                        raise AssertionError((r['trial_id'], method, hypothesis, k, actual[k], f[k]))
                fit_count += 1
                if full:
                    pixels = [None] if method == 'covariance_plain' else [None]+list(range(18))
                    optimum = min(scalar_fit(y, p, chol, j, cfg['sparse_penalty'])['objective'] for p in templates for j in pixels)
                    exhaustive_fits += len(templates)*len(pixels)
                    np.testing.assert_allclose(optimum, f['objective'], rtol=1e-7, atol=2e-7)
            gates = {'source_amplitude': d['star']['amplitude_noise_score'] >= 5.,
                     'weighted_residual': d['star']['chi2']/d['star']['residual_dof'] <= 2.,
                     'nuisance_separation': d['nuisance']['objective']-d['star']['objective'] >= 9.}
            assert gates == d['gates'] and d['pass'] == all(gates.values())
            assert d['accepted'] == (r['screen_detected'] and d['pass'])
            assert d['recovered'] == (d['accepted'] and not r['baseline_confounded'])
        exhaustive.add(representative)
    assert originals == 1460
    # Independently rebuild every published summary cell.
    for g in summary['groups']:
        selected = [r for r in rows if (r['suite'], r['kind'], r.get('target_score')) == (g['suite'], g['kind'], g['target_score'])]
        assert len(selected) == g['trials']
        assert sum(r['screen_detected'] for r in selected) == g['screen_detected']
        for m, counts in g['methods'].items():
            for key, n in counts.items():
                assert sum(r['methods'][m][key] for r in selected) == n
    comparison, stress, anchors = [], [], []
    for score in oldcfg['strength_trials']['scores']:
        for kind in ('stellar', 'off_profile', 'single_pixel', 'block_2x2', 'uniform', 'pointing'):
            ss = [r for r in rows if r['suite'] == 'ls7c_replay' and r.get('source_group') == 'matched'
                  and r['kind'] == kind and r['target_score'] == score]
            signal = kind in ('stellar', 'off_profile')
            key = 'recovered' if signal else 'accepted'
            required = (.9 if kind == 'stellar' else .8) if signal else .05
            cell = {'kind': kind, 'score': score, 'trials': len(ss), 'original': sum(r['original'][key] for r in ss),
                    'methods': {m: sum(r['methods'][m][key] for r in ss) for m in cfg['methods']}}
            cell['meets_original_requirement'] = {m: (n/len(ss) >= required if signal else n/len(ss) <= required) for m, n in cell['methods'].items()}
            comparison.append(cell)
    for location in ('inside', 'outside'):
        for kind in ('stellar', 'block_2x2', 'null'):
            ss = [r for r in rows if r['suite'] == 'sparse_stress' and r['kind'] == kind and r['residual_location'] == location]
            stress.append({'location': location, 'kind': kind, 'trials': len(ss), 'screen_detected': sum(r['screen_detected'] for r in ss),
                           'methods': {m: sum(r['methods'][m]['recovered' if kind == 'stellar' else 'accepted'] for r in ss) for m in cfg['methods']}})
    for a in range(10):
        ss = [r for r in rows if r['anchor'] == a and r['suite'] == 'ls7c_replay' and r['kind'] == 'stellar' and r['source_group'] == 'matched']
        anchors.append({'anchor': a, 'nominal_matched_trials': len(ss), 'original': sum(r['original']['recovered'] for r in ss),
                        'methods': {m: sum(r['methods'][m]['recovered'] for r in ss) for m in cfg['methods']}})
    audit = {'status': 'PASS', 'trial_rows': len(rows), 'original_decisions_preserved': originals,
             'covariance_folds_checked': len(training['folds']), 'scalar_covariance_max_error': covariance_error,
             'direct_whitened_winning_fits': fit_count, 'exhaustive_anchor_suite_pairs': len(exhaustive),
             'exhaustive_fits': exhaustive_fits, 'max_fit_absolute_errors': maxima,
             'comparison': comparison, 'stress': stress, 'by_anchor': anchors,
             'all_original_matched_requirements_pass': {m: all(g['meets_original_requirement'][m] for g in comparison) for m in cfg['methods']}}
    (output/'AUDIT.json').write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in audit.items() if k not in ('comparison', 'stress', 'by_anchor')}, indent=2))


if __name__ == '__main__':
    main()
