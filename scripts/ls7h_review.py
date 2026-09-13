#!/usr/bin/env python3
"""Independent LS7H audit; no import of its analysis or counting functions.

Reuse the already frozen LS7F whitened least-squares audit and LS7G analytical
pulse integration. Do not re-execute LS7G's unchanged temporal/covariance work.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular

from ls7f_review import direct_fit, independent_minima
from ls7g_review import pulse

ROOT = Path(__file__).resolve().parents[1]


def group_key(r):
    key = [r['suite'], r['kind'], r.get('target_score')]
    if r['suite'] == 'base' and r.get('target_score') is None:
        key += [r.get('amplitude_fraction'), r['shape']]
    if r['suite'] == 'sparse_stress':
        key += [r['residual']['location'], r['residual']['polarity']]
    return key


def projected_parts(chol, template, fit, background, clean):
    n = len(background)
    columns = [np.ones(n)]
    if fit['sparse_pixel'] is not None:
        columns.append(np.eye(n)[fit['sparse_pixel']])
    if fit['amplitude'] > 0:
        columns.append(template)
    bw = solve_triangular(chol, np.column_stack(columns), lower=True)
    vectors = solve_triangular(chol, np.column_stack([background, clean]), lower=True)
    residual = vectors-bw@np.linalg.lstsq(bw, vectors, rcond=None)[0]
    return residual[:, 0], residual[:, 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7h_morphology')
    args = parser.parse_args()
    out = args.output
    cfg = json.loads((ROOT/'config/ls7h_morphology.json').read_text())
    for name, digest in cfg['input_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    for base, manifest in cfg['preserve_manifests']+[('.', 'LS7H_FREEZE.sha256')]:
        for line in (ROOT/base/manifest).read_text().splitlines():
            digest, name = line.split(maxsplit=1)
            assert hashlib.sha256((ROOT/base/name.strip()).read_bytes()).hexdigest() == digest, name
    source = ROOT/'results_ls7g_transfer'
    rows = [json.loads(x) for x in gzip.decompress((source/'trials.jsonl.gz').read_bytes()).splitlines()]
    features = [json.loads(x) for x in gzip.decompress((out/'features.jsonl.gz').read_bytes()).splitlines()]
    models = {m['model_id']: m for m in json.loads((source/'models.json').read_text())}
    patterns = {p['pattern_id']: p for p in json.loads((source/'patterns.json').read_text())}
    summary = json.loads((out/'summary.json').read_text())
    old_summary = json.loads((source/'summary.json').read_text())
    paired = json.loads((out/'paired_signals.json').read_text())
    bank = json.loads((out/'bank.json').read_text())
    raw = np.load(source/'backgrounds.npz', allow_pickle=False)
    native, seconds, aperture = [raw[k] for k in ['native', 'seconds', 'aperture']]
    coords = np.argwhere(aperture).tolist()
    assert bank['aperture_pixel_yx'] == coords
    assert bank['families'] == cfg['added_families']
    assert bank['duplicates_retained'] and bank['stamp_shape'] == [11, 11]
    expected, labels = [], []
    # Independent integer coordinates: a CCW rotation maps (y,x) to (2-x,y).
    for family in ['cross3x3', 'ring3x3', 'triangle3x3']:
        if family == 'cross3x3':
            base = {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}
        elif family == 'ring3x3':
            base = {(y, x) for y in range(3) for x in range(3) if (y, x) != (1, 1)}
        else:
            base = {(y, x) for y in range(3) for x in range(3) if x >= y}
        for rotation in (range(4) if family == 'triangle3x3' else [0]):
            mask = set(base)
            for _ in range(rotation):
                mask = {(2-x, y) for y, x in mask}
            for y in range(9):
                for x in range(9):
                    p = [int((py-y, px-x) in mask) for py, px in coords]
                    if any(p):
                        expected.append(p); labels.append(f'{family}_r{rotation}_{y}_{x}')
    np.testing.assert_array_equal(expected, bank['templates'])
    assert labels == bank['labels'] and len(labels) == summary['added_templates']
    added = np.array(expected)
    assert len(rows) == len(features) == summary['trials'] == 3540
    assert [r['trial_id'] for r in rows] == [f['trial_id'] for f in features]
    assert len({f['trial_id'] for f in features}) == 3540
    assert summary['backgrounds'] == 10 and summary['models'] == 80 and summary['added_observing_days'] == 0
    assert summary['margin'] == cfg['margin'] == -1
    assert summary['suites'] == dict(Counter(r['suite'] for r in rows))
    max_vector_error, max_nonadditivity, max_attribution_error = 0., 0., 0.
    decisions, clean_vectors = [], []
    chols = {mid: np.linalg.cholesky(m['covariance']) for mid, m in models.items()}
    for r, f in zip(rows, features):
        assert f['model_id'] == r['model_id']
        a, lo, hi = r['anchor'], r['best']['start'], r['best']['stop']
        p, _ = pulse(seconds[a], r['phase_seconds'], r['shape'])
        addition = (r['pattern_scale']*p)[:, None, None]*np.array(patterns[r['pattern_id']]['vector'])
        if r['residual'] is not None:
            d = r['residual']; y, x = d['pixel_yx']
            addition[d['start']:d['stop'], y, x] += d['amplitude_e_per_s']
        values = []
        for cube in [native[a], native[a]+addition, addition]:
            side = np.concatenate([cube[lo-60:lo-5][:, aperture], cube[hi+5:hi+60][:, aperture]])
            values.append(r['sign']*(np.mean(cube[lo:hi][:, aperture], axis=0)-np.median(side, axis=0)))
        background, observed, pure = values
        clean = observed-background
        for actual, recorded in [(background, f['native_vector']), (clean, f['clean_vector']),
                                  (pure, f['pure_injection_vector']), (observed, r['event_vector'])]:
            max_vector_error = max(max_vector_error, float(np.max(abs(actual-recorded))))
            np.testing.assert_allclose(actual, recorded, rtol=1e-11, atol=1e-9)
        max_nonadditivity = max(max_nonadditivity, float(np.max(abs(clean-pure))))
        clean_vectors.append(clean)
        old = r['methods']['covariance_sparse']; model = models[r['model_id']]
        use_new = f['added_fit']['objective'] < old['broad_nuisance']['objective']
        margin = min(f['added_fit']['objective'], old['broad_nuisance']['objective'])-old['star']['objective']
        assert f['augmented_winner_origin'] == ('added' if use_new else 'ls7g')
        assert f['augmented_winner_label'] == (labels[f['added_fit']['template_index']] if use_new else model['broad_labels'][old['broad_nuisance']['template_index']])
        np.testing.assert_allclose(margin, f['augmented_margin'], rtol=1e-12, atol=1e-10)
        for name, minimum in [('margin_broad', f['clean']['broad']['objective']),
                              ('margin_augmented', min(f['clean']['broad']['objective'], f['clean']['added']['objective']))]:
            np.testing.assert_allclose(f['clean'][name], minimum-f['clean']['star']['objective'], rtol=1e-12, atol=1e-10)
        ds = {}
        for rule in ['ls7g', 'augmented', 'plain_ablation']:
            method = r['methods']['covariance_plain' if rule == 'plain_ablation' else 'covariance_sparse']
            star = method['star']; m = margin if rule == 'augmented' else method['margins']['broad']
            accepted = bool(r['screen_detected'] and star['amplitude_noise_score'] >= 5
                            and star['chi2']/star['residual_dof'] <= 2 and m >= -1)
            paths = [(not r['screen_detected'], 'temporal'), (star['amplitude_noise_score'] < 5, 'source_score'),
                     (star['chi2']/star['residual_dof'] > 2, 'residual'), (m < -1, 'nuisance_margin'),
                     (r['baseline_confounded'], 'confounded'), (True, 'recovered')]
            ds[rule] = {'accepted': accepted, 'recovered': bool(accepted and not r['baseline_confounded']),
                        'recovery_path': next(name for condition, name in paths if condition),
                        'nuisance_preferred_acceptance': bool(accepted and m < 0)}
            assert ds[rule] == f['decisions'][rule]
            if rule != 'augmented':
                assert all(ds[rule][k] == method['decisions']['broad']['-1'][k] for k in ['accepted', 'recovered', 'nuisance_preferred_acceptance'])
        assert not ds['augmented']['accepted'] or ds['ls7g']['accepted']
        decisions.append(ds)
        chol = chols[r['model_id']]
        sb, sc = projected_parts(chol, model['star_templates'][old['star']['template_index']], old['star'], background, clean)
        nb, nc = projected_parts(chol, model['broad_templates'][old['broad_nuisance']['template_index']], old['broad_nuisance'], background, clean)
        terms = {'injected_shape': float(nc@nc-sc@sc), 'native_background': float(nb@nb-sb@sb),
                 'interaction': float(2*(nb@nc-sb@sc)),
                 'penalty_difference': float(9*((old['broad_nuisance']['sparse_pixel'] is not None)-(old['star']['sparse_pixel'] is not None)))}
        terms['sum'] = sum(terms.values())
        for key, actual in terms.items():
            max_attribution_error = max(max_attribution_error, abs(actual-f['fixed_winner_margin_components'][key]))
            np.testing.assert_allclose(actual, f['fixed_winner_margin_components'][key], rtol=1e-7, atol=2e-7)
        np.testing.assert_allclose(terms['sum'], old['margins']['broad'], rtol=1e-7, atol=2e-7)
    direct_count, alternatives, max_direct, max_minimum = 0, 0, 0., 0.
    for mid, model in models.items():
        ids = [i for i, r in enumerate(rows) if r['model_id'] == mid]
        chol = chols[mid]
        cases = [('observed_added', added, [rows[i]['event_vector'] for i in ids], [features[i]['added_fit'] for i in ids]),
                 ('clean_star', model['star_templates'], [clean_vectors[i] for i in ids], [features[i]['clean']['star'] for i in ids]),
                 ('clean_broad', model['broad_templates'], [clean_vectors[i] for i in ids], [features[i]['clean']['broad'] for i in ids]),
                 ('clean_added', added, [clean_vectors[i] for i in ids], [features[i]['clean']['added'] for i in ids])]
        for name, templates, vectors, fits in cases:
            minimum = independent_minima(vectors, templates, chol, True, 9)
            recorded = [fit['objective'] for fit in fits]
            max_minimum = max(max_minimum, float(np.max(abs(minimum-recorded))))
            np.testing.assert_allclose(minimum, recorded, rtol=1e-7, atol=2e-7)
            alternatives += len(ids)*len(templates)*22
            for vector, fit in zip(vectors, fits):
                direct = direct_fit(np.array(vector), np.array(templates[fit['template_index']]), chol, fit['sparse_pixel'], 9)
                for quantity, actual in direct.items():
                    max_direct = max(max_direct, abs(actual-fit[quantity]))
                    np.testing.assert_allclose(actual, fit[quantity], rtol=1e-7, atol=2e-7)
                direct_count += 1
    rules = ['ls7g', 'augmented', 'plain_ablation']
    for group in summary['groups']:
        ids = [i for i, r in enumerate(rows) if group_key(r) == group['key']]
        assert group['trials'] == len(ids)
        for rule in rules:
            counts = {field: sum(decisions[i][rule][field] for i in ids) for field in ['accepted', 'recovered', 'nuisance_preferred_acceptance']}
            counts['recovery_paths'] = dict(Counter(decisions[i][rule]['recovery_path'] for i in ids))
            assert counts == group['rules'][rule]
    assert len(summary['groups']) == len({tuple(group_key(r)) for r in rows})
    assert len(summary['core_cells']) == len(old_summary['core_cells']) == 36
    for cell, old in zip(summary['core_cells'], old_summary['core_cells']):
        assert all(cell[k] == old[k] for k in ['key', 'trials', 'signal', 'limit'])
        ids = [i for i, r in enumerate(rows) if group_key(r) == cell['key']]
        assert len(ids) == cell['trials']
        for rule in rules:
            count = sum(decisions[i][rule]['recovered' if cell['signal'] else 'accepted'] for i in ids)
            passed = count >= cell['limit'] if cell['signal'] else count <= cell['limit']
            assert cell['rules'][rule] == {'count': count, 'pass': passed}
        assert cell['rules']['ls7g'] == old['rules'][old_summary['primary_rule']]
    assert len(summary['per_background']) == 360
    for cell in summary['per_background']:
        ids = [i for i, r in enumerate(rows) if group_key(r) == cell['key'] and r['anchor'] == cell['anchor']]
        assert len(ids) == cell['trials']
        field = 'recovered' if cell['key'][1] in ('stellar', 'off_profile') else 'accepted'
        assert cell['rules'] == {rule: sum(decisions[i][rule][field] for i in ids) for rule in rules}
    signals = [i for i, r in enumerate(rows) if r['kind'] in ('stellar', 'off_profile')]
    bright = [i for i, r in enumerate(rows) if r['suite'] == 'base' and r['kind'] == 'stellar' and r.get('amplitude_fraction') == .1 and r['shape'] != 'doublet30sep87']
    nulls = [i for i, r in enumerate(rows) if r['suite'] == 'base' and r['kind'] == 'null']
    physical = [i for i, r in enumerate(rows) if r['suite'] == 'bounded_pointing' and r['screen_detected']]
    for rule in rules:
        gates = {'all_core_cells': all(c['rules'][rule]['pass'] for c in summary['core_cells']),
                 'all_target_strengths_matched': all(r['strength_matched'] for r in rows if r['tuning'] is not None),
                 'ten_percent_single_recovery': sum(decisions[i][rule]['recovered'] for i in bright) >= 54,
                 'no_base_null_acceptance': not any(decisions[i][rule]['accepted'] for i in nulls),
                 'confounding_at_most_20_percent': sum(rows[i]['baseline_confounded'] for i in signals) <= .2*len(signals),
                 'bounded_pointing_screened_acceptance': bool(physical) and sum(decisions[i][rule]['accepted'] for i in physical) <= .05*len(physical)}
        assert summary['rules'][rule] == {'pass': all(gates.values()), 'gates': gates}
        assert summary['signal_recovery_paths'][rule] == dict(Counter(decisions[i][rule]['recovery_path'] for i in signals))
    lost = [rows[i]['trial_id'] for i in signals if decisions[i]['ls7g']['recovered'] and not decisions[i]['augmented']['recovered']]
    rejected = [r['trial_id'] for r, d in zip(rows, decisions) if r['kind'] not in ('stellar', 'off_profile') and d['ls7g']['accepted'] and not d['augmented']['accepted']]
    assert summary['lost_stellar_ids'] == lost
    assert summary['newly_rejected_nonstellar_ids'] == rejected
    assert len(summary['focus_cells']) == 4
    focus_ids = set()
    for cell, key in zip(summary['focus_cells'], cfg['focus_cells']):
        assert cell['key'] == key
        ids = [i for i, r in enumerate(rows) if [r['suite'], r['kind'], r.get('target_score')] == key]
        accepted = [i for i in ids if decisions[i]['ls7g']['accepted']]
        assert cell['trials'] == len(ids) == 40
        expected = {'accepted_ids': [rows[i]['trial_id'] for i in accepted],
                    'augmented_accepted_ids': [rows[i]['trial_id'] for i in ids if decisions[i]['augmented']['accepted']],
                    'clean_margin_rejects_ids': [rows[i]['trial_id'] for i in accepted if features[i]['clean']['margin_broad'] < -1],
                    'star_sparse_ids': [rows[i]['trial_id'] for i in accepted if rows[i]['methods']['covariance_sparse']['star']['sparse_pixel'] is not None],
                    'plain_accepted_ids': [rows[i]['trial_id'] for i in ids if decisions[i]['plain_ablation']['accepted']]}
        assert all(cell[k] == value for k, value in expected.items())
        focus_ids.update(cell['accepted_ids'])
    assert {p['control_id'] for p in paired} == focus_ids and len(paired) == len(focus_ids)
    index = {r['trial_id']: i for i, r in enumerate(rows)}
    for p in paired:
        control = rows[index[p['control_id']]]
        selected = [i for i, r in enumerate(rows) if r['suite'] == 'base' and r['kind'] in ('stellar', 'off_profile')
                    and all(r.get(k) == control.get(k) for k in ['anchor', 'phase_seconds', 'shape', 'target_score'])]
        assert len(selected) == len(p['paired_signals']) == 5
        for i, record in zip(selected, p['paired_signals']):
            assert all(record[k] == rows[i][k] for k in ['trial_id', 'model_id', 'shift_yx'])
            assert record['decisions'] == decisions[i]
    np.testing.assert_allclose(max_nonadditivity, summary['max_clean_pure_difference'], rtol=1e-12, atol=1e-12)
    audit = {'passed': True, 'trials_reconstructed': len(rows), 'added_templates_checked': len(added),
             'direct_whitened_fits': direct_count, 'exhaustive_fit_alternatives': alternatives,
             'max_component_vector_error': max_vector_error, 'max_clean_pure_difference': max_nonadditivity,
             'max_margin_attribution_error': max_attribution_error, 'max_direct_fit_error': max_direct,
             'max_minimum_objective_error': max_minimum, 'core_cells_checked': 36,
             'per_background_cells_checked': 360, 'focus_controls_paired': len(paired),
             'all_signal_losses_checked': len(lost), 'all_groups_paths_and_gates_checked': True,
             'unchanged_ls7g_temporal_and_covariance_audit_reused_by_hash': True}
    (out/'AUDIT.json').write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
