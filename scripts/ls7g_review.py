#!/usr/bin/env python3
"""Independent LS7G audit from published background extracts and fit ledgers."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import median_filter, shift

from ls7f_review import direct_fit, independent_minima

ROOT = Path(__file__).resolve().parents[1]


def pulse(seconds, phase, shape):
    centers = [phase-43.5, phase+43.5] if shape == 'doublet30sep87' else [phase]
    duration = 30. if shape == 'doublet30sep87' else float(shape[3:])
    p = np.zeros_like(seconds)
    for center in centers:
        for i, t in enumerate(seconds):
            p[i] += max(0., min(t+10., center+duration/2)-max(t-10., center-duration/2))/20.
    return p, centers


def temporal(flux, seconds, centers, sigma, sign):
    residual = sign*(flux-median_filter(flux, size=121, mode='nearest'))
    best = None
    for width in [2, 3, 5]:
        for start in range(60, len(flux)-60-width+1):
            mid = (seconds[start]+seconds[start+width-1])/2
            if min(abs(mid-c) for c in centers) <= 20.1:
                score = float(np.sum(residual[start:start+width])/(sigma*np.sqrt(width)))
                if best is None or score > best['score']:
                    best = {'start': start, 'stop': start+width, 'score': score}
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7g_transfer')
    args = parser.parse_args()
    out = args.output
    cfg = json.loads((ROOT/'config/ls7g_transfer.json').read_text())
    for filename, expected in cfg['input_sha256'].items():
        assert hashlib.sha256((ROOT/filename).read_bytes()).hexdigest() == expected
    for base, filename in [('.', 'LS7G_FREEZE.sha256')]+cfg['preserve_manifests']:
        for line in (ROOT/base/filename).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert hashlib.sha256((ROOT/base/name.strip()).read_bytes()).hexdigest() == expected
    raw = np.load(out/'backgrounds.npz', allow_pickle=False)
    native, seconds, sigmas, aperture = [raw[k] for k in ['native', 'seconds', 'sigmas', 'aperture']]
    assert native.shape == (10, 401, 11, 11) and aperture.sum() == 21
    assert raw['anchors'].tolist() == cfg['anchors']
    assert np.all(np.diff(raw['context_cadence'], axis=1) == 1)
    assert np.all((raw['context_quality'] & ~1088) == 0)
    assert np.all(np.isfinite(native[:, :, aperture]))
    for a in range(10):
        d = np.diff(raw[f'run_flux_{a}'])
        sigma = 1.482602218505602*np.median(np.abs(d-np.median(d)))/np.sqrt(2)
        np.testing.assert_allclose(sigma, sigmas[a], rtol=1e-12)
    rows = [json.loads(x) for x in gzip.decompress((out/'trials.jsonl.gz').read_bytes()).splitlines()]
    assert len(rows) == len({r['trial_id'] for r in rows}) == 3540
    assert dict(Counter(r['suite'] for r in rows)) == {'base': 1460, 'sparse_stress': 1040, 'known_extended': 360, 'unmodeled_shapes': 360, 'bounded_pointing': 320}
    models = {m['model_id']: m for m in json.loads((out/'models.json').read_text())}
    patterns = {p['pattern_id']: p for p in json.loads((out/'patterns.json').read_text())}
    training = json.loads((out/'training.json').read_text())
    summary = json.loads((out/'summary.json').read_text())
    assert summary['trials'] == 3540 and summary['primary_rule'] == 'covariance_sparse/broad/-1'
    source = json.loads((out/'source_manifest.json').read_text())
    historical_sources = json.loads((ROOT/'results_ls7b_tess/source_manifest.json').read_text())['products']
    for p, old in zip(source['products'], historical_sources):
        assert all(p[k] == old[k] for k in ['kind', 'name', 'bytes', 'sha256'])
    assert json.loads((out/'preflight.json').read_text()) == json.loads((ROOT/'results_ls7b_tess/preflight.json').read_text())
    # Independently rebuild every injection pattern, including omitted shapes.
    masks = {'block3x3': np.ones((3, 3)), 'row1x5': np.ones((1, 5)), 'column5x1': np.ones((5, 1)),
             'cross3x3': np.array([[0., 1., 0.], [1., 1., 1.], [0., 1., 0.]]),
             'ring3x3': np.array([[1., 1., 1.], [1., 0., 1.], [1., 1., 1.]]),
             'triangle3x3': np.array([[1., 1., 1.], [0., 1., 1.], [0., 0., 1.]])}
    for record in patterns.values():
        ref = np.median(native[record['anchor']], axis=0)
        profile = np.zeros((11, 11)); profile[aperture] = np.maximum(ref[aperture], 0.)
        profile /= profile.sum()
        kind, displacement = record['kind'], record['shift_yx']
        if kind in ['stellar', 'off_profile', 'null']:
            expected = shift(profile, displacement, order=1, mode='constant', cval=0., prefilter=False)
            expected[~aperture] = 0.; expected /= expected.sum()
        elif kind in ['pointing', 'bounded_pointing']:
            image = np.nan_to_num(ref, nan=0.)
            moved = shift(image, displacement, order=1, mode='nearest', prefilter=False)
            moved *= image.sum()/moved.sum()
            expected = moved-image
            assert record['sign'] == (1 if expected[aperture].sum() >= 0 else -1)
            if kind == 'pointing':
                expected /= abs(expected[aperture].sum())
        elif kind == 'single_pixel':
            expected = np.zeros((11, 11)); expected.flat[np.argmax(profile)] = 1.
        elif kind == 'uniform':
            expected = np.ones((11, 11))/aperture.sum()
        else:
            mask = np.ones((2, 2)) if kind == 'block_2x2' else masks[kind]
            h, width = mask.shape; best_score, corner = -np.inf, None
            for y in range(12-h):
                for x in range(12-width):
                    score = float(sum(profile[y+iy, x+ix]*mask[iy, ix] for iy in range(h) for ix in range(width)))
                    if score > best_score:
                        best_score, corner = score, [y, x]
            y, x = corner
            expected = np.zeros((11, 11)); expected[y:y+h, x:x+width] = mask
            expected /= expected[aperture].sum()
            if record['corner_yx'] is not None:
                assert record['corner_yx'] == corner
        np.testing.assert_allclose(expected, record['vector'], rtol=1e-12, atol=1e-10)
    max_covariance_error, max_event_error, max_score_error = 0., 0., 0.
    assert len(training['samples']) == 150 and len(training['folds']) == 30
    for sample in training['samples']:
        a, lo, width = sample['anchor'], sample['start'], sample['width']
        hi = lo+width
        side = np.concatenate([native[a, lo-60:lo-5][:, aperture], native[a, hi+5:hi+60][:, aperture]])
        vector = (np.mean(native[a, lo:hi][:, aperture], axis=0)-np.median(side, axis=0))/sigmas[a]
        np.testing.assert_allclose(vector, sample['normalized_delta'], rtol=1e-12, atol=1e-12)
    for fold in training['folds']:
        chosen = [r for r in training['samples'] if r['anchor'] != fold['excluded_anchor'] and r['width'] == fold['width']]
        assert len(chosen) == 45 and [r['sample_id'] for r in chosen] == fold['training_ids']
        assert sorted({r['anchor'] for r in chosen}) == fold['training_anchors']
        x = np.array([r['normalized_delta'] for r in chosen])
        mu = [sum(v[j] for v in x)/45 for j in range(21)]
        c = np.array([[sum((v[i]-mu[i])*(v[j]-mu[j]) for v in x)/44 for j in range(21)] for i in range(21)])
        np.testing.assert_allclose(c, fold['empirical_covariance'], rtol=1e-11, atol=1e-11)
        expected = .95*c+.05*np.diag(np.diag(c))+np.eye(21)*np.trace(c)/21*1e-10
        max_covariance_error = max(max_covariance_error, float(np.max(abs(expected-fold['covariance']))))
        np.testing.assert_allclose(expected, fold['covariance'], rtol=1e-11, atol=1e-11)
    # Direct template reconstruction from saved native sidebands and coordinates.
    fit_shifts = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())['spatial']['fit_shifts_yx']
    for model in models.values():
        a, lo, hi = model['anchor'], model['start'], model['stop']
        fold = next(f for f in training['folds'] if f['excluded_anchor'] == a and f['width'] == hi-lo)
        np.testing.assert_allclose(model['covariance'], np.array(fold['covariance'])*sigmas[a]**2, rtol=1e-12)
        ref = np.median(np.concatenate([native[a, lo-60:lo-5], native[a, hi+5:hi+60]]), axis=0)
        profile = np.zeros((11, 11)); profile[aperture] = np.maximum(ref[aperture], 0.)
        profile /= profile.sum()
        for actual, displacement in zip(model['star_templates'], fit_shifts):
            p = shift(profile, displacement, order=1, mode='constant', cval=0., prefilter=False)
            p[~aperture] = 0; p /= p.sum()
            np.testing.assert_allclose(actual, p[aperture], rtol=1e-12, atol=1e-12)
        assert len(model['broad_templates']) > len(model['original_templates'])
        assert model['broad_templates'][:len(model['original_templates'])] == model['original_templates']
        for label, actual in zip(model['broad_labels'], model['broad_templates']):
            if label.startswith('rect'):
                size, y, x = label[4:].split('_'); h, w = map(int, size.split('x'))
                p = np.zeros((11, 11)); p[int(y):int(y)+h, int(x):int(x)+w] = 1
                np.testing.assert_array_equal(actual, p[aperture])
    reconstructed, losses, ambiguity = [], [], []
    for r in rows:
        a = r['anchor']; model = models[r['model_id']]
        pattern = np.array(patterns[r['pattern_id']]['vector'])
        p, centers = pulse(seconds[a], r['phase_seconds'], r['shape'])
        injected = native[a]+(r['pattern_scale']*p)[:, None, None]*pattern
        if r['residual'] is not None:
            d = r['residual']; y, x = d['pixel_yx']
            injected[d['start']:d['stop'], y, x] += d['amplitude_e_per_s']
            parent = next(q for q in rows if q['trial_id'] == r['parent_trial_id'])
            assert (d['start'], d['stop']) == (parent['best']['start'], parent['best']['stop'])
            assert r['pattern_id'] == parent['pattern_id'] and r['pattern_scale'] == parent['pattern_scale']
            fold = next(f for f in training['folds'] if f['excluded_anchor'] == a and f['width'] == d['stop']-d['start'])
            j = d['reference_pixel_index']
            expected = d['polarity']*8*np.sqrt(np.array(fold['covariance'])[j, j]*sigmas[a]**2)
            np.testing.assert_allclose(expected, d['amplitude_e_per_s'], rtol=1e-12)
            ref = np.median(native[a], axis=0)
            assert j == int(np.argmin(np.maximum(ref[aperture], 0.)))
            assert [y, x] == (np.argwhere(aperture)[j].tolist() if d['location'] == 'inside' else [0, 0])
        actual = temporal(injected[:, aperture].sum(axis=1), seconds[a], centers, sigmas[a], r['sign'])
        baseline = temporal(native[a][:, aperture].sum(axis=1), seconds[a], centers, sigmas[a], r['sign'])
        for actual_best, recorded in [(actual, r['best']), (baseline, r['native_best'])]:
            assert (actual_best['start'], actual_best['stop']) == (recorded['start'], recorded['stop'])
            max_score_error = max(max_score_error, abs(actual_best['score']-recorded['score']))
            np.testing.assert_allclose(actual_best['score'], recorded['score'], rtol=1e-10, atol=1e-8)
        assert r['screen_detected'] == (actual['score'] >= 8.)
        assert r['baseline_confounded'] == (baseline['score'] >= 8.)
        if r['tuning'] is not None:
            assert r['strength_matched'] == (r['tuning']['matched'] and abs(actual['score']-r['target_score']) <= .01)
        if r['suite'] == 'bounded_pointing':
            assert r['pattern_scale'] == r['pattern_multiplier'] == 1.
        lo, hi = r['best']['start'], r['best']['stop']
        assert (model['anchor'], model['start'], model['stop']) == (a, lo, hi)
        side = np.concatenate([injected[lo-60:lo-5][:, aperture], injected[hi+5:hi+60][:, aperture]])
        vector = r['sign']*(np.mean(injected[lo:hi][:, aperture], axis=0)-np.median(side, axis=0))
        max_event_error = max(max_event_error, float(np.max(abs(vector-r['event_vector']))))
        np.testing.assert_allclose(vector, r['event_vector'], rtol=1e-11, atol=1e-9)
        reconstructed.append(vector)
        for method, d in r['methods'].items():
            for bank in ['original', 'broad']:
                margin = d[bank+'_nuisance']['objective']-d['star']['objective']
                np.testing.assert_allclose(margin, d['margins'][bank], rtol=1e-12, atol=1e-10)
                eligible = r['screen_detected'] and d['star']['amplitude_noise_score'] >= 5 and d['star']['chi2']/d['star']['residual_dof'] <= 2
                for threshold in [-1, 0, 9]:
                    accepted = bool(eligible and margin >= threshold)
                    want = {'accepted': accepted, 'recovered': bool(accepted and not r['baseline_confounded']),
                            'nuisance_preferred_acceptance': bool(accepted and margin < 0)}
                    assert d['decisions'][bank][str(threshold)] == want
            if r['kind'] in ['stellar', 'off_profile'] and d['decisions']['original']['9']['recovered'] and not d['decisions']['broad']['-1']['recovered']:
                losses.append({'trial_id': r['trial_id'], 'method': method})
            if d['decisions']['broad']['-1']['nuisance_preferred_acceptance']:
                ambiguity.append({'trial_id': r['trial_id'], 'method': method, 'kind': r['kind'], 'margin': d['margins']['broad']})
    direct_count, alternative_count, max_fit_error, max_min_error = 0, 0, 0., 0.
    for model_id, model in models.items():
        ids = [i for i, r in enumerate(rows) if r['model_id'] == model_id]
        chol = np.linalg.cholesky(model['covariance'])
        vectors = [reconstructed[i] for i in ids]
        for method in cfg['methods']:
            sparse = method == 'covariance_sparse'
            for field, templates in [('star', model['star_templates']), ('original_nuisance', model['original_templates']), ('broad_nuisance', model['broad_templates'])]:
                minima = independent_minima(vectors, templates, chol, sparse, 9.)
                recorded = [rows[i]['methods'][method][field]['objective'] for i in ids]
                alternative_count += len(ids)*len(templates)*(22 if sparse else 1)
                max_min_error = max(max_min_error, float(np.max(abs(minima-recorded))))
                np.testing.assert_allclose(minima, recorded, rtol=1e-7, atol=2e-7)
                for i in ids:
                    fit = rows[i]['methods'][method][field]
                    scalar = direct_fit(reconstructed[i], templates[fit['template_index']], chol, fit['sparse_pixel'], 9.)
                    for key, value in scalar.items():
                        max_fit_error = max(max_fit_error, abs(value-fit[key]))
                        np.testing.assert_allclose(value, fit[key], rtol=1e-7, atol=2e-7)
                    direct_count += 1
    # Independently select all reported cells; no import of production grouping.
    def select(key, anchor=None):
        chosen = [r for r in rows if [r['suite'], r['kind'], r.get('target_score')] == key[:3] and (anchor is None or r['anchor'] == anchor)]
        if key[0] == 'base' and key[2] is None:
            chosen = [r for r in chosen if [r.get('amplitude_fraction'), r['shape']] == key[3:]]
        if key[0] == 'sparse_stress':
            chosen = [r for r in chosen if [r['residual']['location'], r['residual']['polarity']] == key[3:]]
        return chosen
    for group in summary['groups']:
        chosen = select(group['key'])
        assert len(chosen) == group['trials']
        for key, field in [('screen_detected', 'screen_detected'), ('confounded', 'baseline_confounded')]:
            assert sum(r[field] for r in chosen) == group[key]
        assert sum(r['strength_matched'] is True for r in chosen) == group['matched']
        for rule, counts in group['rules'].items():
            method, bank, threshold = rule.split('/')
            for field, count in counts.items():
                assert sum(r['methods'][method]['decisions'][bank][threshold][field] for r in chosen) == count
    assert len(summary['core_cells']) == 36
    for cell in summary['core_cells']:
        chosen = select(cell['key']); signal = cell['key'][1] in ['stellar', 'off_profile']
        assert cell['signal'] == signal
        limit = int(np.ceil((.9 if cell['key'][1] == 'stellar' else .8)*len(chosen))) if signal else len(chosen)//20
        assert cell['limit'] == limit
        for rule, counts in cell['rules'].items():
            method, bank, threshold = rule.split('/')
            value = sum(r['methods'][method]['decisions'][bank][threshold]['recovered' if signal else 'accepted'] for r in chosen)
            assert counts == {'count': value, 'pass': bool(value >= limit if signal else value <= limit)}
    for bg in summary['per_background']:
        chosen = select(bg['key'], bg['anchor']); signal = bg['key'][1] in ['stellar', 'off_profile']
        assert len(chosen) == bg['trials'] and sum(r['screen_detected'] for r in chosen) == bg['screen_detected']
        for rule, count in bg['rules'].items():
            method, bank, threshold = rule.split('/')
            assert sum(r['methods'][method]['decisions'][bank][threshold]['recovered' if signal else 'accepted'] for r in chosen) == count
    for rule, result in summary['rules'].items():
        method, bank, threshold = rule.split('/')
        choose = lambda r: r['methods'][method]['decisions'][bank][threshold]
        bright = [r for r in rows if r['suite'] == 'base' and r['kind'] == 'stellar' and r.get('amplitude_fraction') == .1 and r['shape'] != 'doublet30sep87']
        nulls = [r for r in rows if r['suite'] == 'base' and r['kind'] == 'null']
        physical = [r for r in rows if r['suite'] == 'bounded_pointing' and r['screen_detected']]
        signals = [r for r in rows if r['kind'] in ['stellar', 'off_profile']]
        expected = {'all_core_cells': all(c['rules'][rule]['pass'] for c in summary['core_cells']),
                    'all_target_strengths_matched': all(r['strength_matched'] for r in rows if r['tuning'] is not None),
                    'ten_percent_single_recovery': sum(choose(r)['recovered'] for r in bright) >= 54,
                    'no_base_null_acceptance': not any(choose(r)['accepted'] for r in nulls),
                    'confounding_at_most_20_percent': sum(r['baseline_confounded'] for r in signals) <= .2*len(signals),
                    'bounded_pointing_screened_acceptance': bool(physical) and sum(choose(r)['accepted'] for r in physical) <= .05*len(physical)}
        assert result == {'pass': all(expected.values()), 'gates': expected}
    audit = {'passed': True, 'trials_reconstructed': len(rows), 'covariance_folds': 30,
             'max_covariance_absolute_error': max_covariance_error, 'max_event_vector_absolute_error': max_event_error,
             'max_temporal_score_absolute_error': max_score_error, 'direct_whitened_fits': direct_count,
             'exhaustive_fit_alternatives': alternative_count, 'max_direct_fit_absolute_error': max_fit_error,
             'max_minimum_objective_absolute_error': max_min_error, 'all_groups_and_gates_checked': True,
             'per_background_counts_checked': len(summary['per_background']),
             'losses_relative_to_original_margin_9': losses, 'nuisance_preferred_acceptances_at_minus_1': ambiguity}
    (out/'AUDIT.json').write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if not isinstance(v, list)}, indent=2))


if __name__ == '__main__':
    main()
