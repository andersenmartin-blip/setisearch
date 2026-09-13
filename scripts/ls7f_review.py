#!/usr/bin/env python3
"""Independent LS7F audit: whitened fits, full-bank minima and scalar ledgers.

Does not import the LS7E fitting implementation or LS7F sweep/count functions.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_fit(y, p, chol, pixel, penalty):
    n = len(y)
    b = np.ones((n, 1)) if pixel is None else np.column_stack([np.ones(n), np.eye(n)[:, pixel]])
    yw = solve_triangular(chol, y, lower=True)
    pw = solve_triangular(chol, p, lower=True)
    bw = solve_triangular(chol, b, lower=True)
    pr = pw-bw@np.linalg.lstsq(bw, pw, rcond=None)[0]
    yr = yw-bw@np.linalg.lstsq(bw, yw, rcond=None)[0]
    norm = float(pr@pr)
    amp = max(0., float(pr@yr)/norm) if norm > 1e-12*float(pw@pw) else 0.
    beta = np.linalg.lstsq(bw, yw-amp*pw, rcond=None)[0]
    residual = yw-amp*pw-bw@beta
    chi = float(residual@residual)
    return {'chi2': chi, 'objective': chi+(penalty if pixel is not None else 0.),
            'amplitude_noise_score': amp*np.sqrt(norm)}


def independent_minima(vectors, templates, chol, sparse, penalty):
    """Whitened QR projection, all alternatives for all vectors in one model."""
    n = chol.shape[0]
    yw = solve_triangular(chol, np.asarray(vectors).T, lower=True)
    pw = solve_triangular(chol, np.asarray(templates).T, lower=True)
    best = np.full(yw.shape[1], np.inf)
    for pixel in [None]+(list(range(n)) if sparse else []):
        b = np.ones((n, 1)) if pixel is None else np.column_stack([np.ones(n), np.eye(n)[:, pixel]])
        bw = solve_triangular(chol, b, lower=True)
        q, _ = np.linalg.qr(bw, mode='reduced')
        pr = pw-q@(q.T@pw)
        yr = yw-q@(q.T@yw)
        norm = np.sum(pr*pr, axis=0)
        valid = norm > 1e-12*np.sum(pw*pw, axis=0)
        cross = np.maximum(pr.T@yr, 0.)
        improvement = np.divide(cross*cross, norm[:, None], out=np.zeros_like(cross), where=valid[:, None])
        objectives = np.maximum(0., np.sum(yr*yr, axis=0)[None, :]-improvement)
        objectives += penalty if pixel is not None else 0.
        best = np.minimum(best, objectives.min(axis=0))
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7f_separation')
    args = parser.parse_args()
    output = args.output
    cfg = json.loads((ROOT/'config/ls7f_separation.json').read_text())
    for name, expected in cfg['input_sha256'].items():
        assert sha(ROOT/name) == expected, name
    for base, filename in [('.', 'LS7F_FREEZE.sha256')]+cfg['preserve_manifests']:
        for line in (ROOT/base/filename).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert sha(ROOT/base/name.strip()) == expected, name
    old = [json.loads(s) for s in gzip.decompress((ROOT/'results_ls7e_joint/trials.jsonl.gz').read_bytes()).splitlines()]
    rows = [json.loads(s) for s in gzip.decompress((output/'features.jsonl.gz').read_bytes()).splitlines()]
    models = {m['model_id']: m for m in json.loads((ROOT/'results_ls7e_joint/models.json').read_text())}
    bank = json.loads((output/'bank.json').read_text())
    templates = np.array(bank['templates'])
    summary = json.loads((output/'summary.json').read_text())
    sweeps = json.loads((output/'sweeps.json').read_text())
    certificates = json.loads((output/'certificates.json').read_text())
    assert len(rows) == len(old) == summary['trials'] == 3180
    assert len({r['trial_id'] for r in rows}) == 3180
    assert [r['trial_id'] for r in rows] == [r['trial_id'] for r in old]
    coords = json.loads((ROOT/'results_ls7d_noise/windows.json').read_text())[0]['aperture_pixel_yx']
    assert bank['aperture_pixel_yx'] == coords
    expected_templates, expected_labels = [], []
    # Direct nested pixel inclusion, separate from vectorized rectangle builder.
    for h, w in cfg['rectangle_shapes']:
        for y in range(12-h):
            for x in range(12-w):
                p = [int(y <= py < y+h and x <= px < x+w) for py, px in coords]
                if any(p):
                    expected_templates.append(p)
                    expected_labels.append(f'rect{h}x{w}_{y}_{x}')
    np.testing.assert_array_equal(templates, expected_templates)
    assert bank['labels'] == expected_labels
    max_direct_error, max_minimum_error = 0., 0.
    direct_count, alternatives = 0, 0
    for model_id, model in models.items():
        indices = [i for i, r in enumerate(rows) if r['model_id'] == model_id]
        chol = np.linalg.cholesky(model['covariance'])
        vectors = [old[i]['event_vector'] for i in indices]
        for method in cfg['methods']:
            sparse = method == 'covariance_sparse'
            minima = independent_minima(vectors, templates, chol, sparse, cfg['sparse_penalty'])
            alternatives += len(indices)*len(templates)*(19 if sparse else 1)
            recorded = [rows[i]['methods'][method]['extended_winner']['objective'] for i in indices]
            max_minimum_error = max(max_minimum_error, float(np.max(np.abs(minima-recorded))))
            np.testing.assert_allclose(minima, recorded, rtol=1e-7, atol=2e-7)
            for i in indices:
                r, source = rows[i], old[i]
                d, archived = r['methods'][method], source['methods'][method]
                for key in r:
                    if key != 'methods':
                        assert r[key] == source[key]
                assert d['star'] == archived['star']
                for fit, p in [(d['star'], model['star_templates'][d['star']['template_index']]),
                               (d['extended_winner'], templates[d['extended_winner']['template_index']])]:
                    result = direct_fit(np.asarray(source['event_vector']), p, chol, fit['sparse_pixel'], cfg['sparse_penalty'])
                    for quantity, value in result.items():
                        max_direct_error = max(max_direct_error, abs(value-fit[quantity]))
                        np.testing.assert_allclose(value, fit[quantity], rtol=1e-7, atol=2e-7)
                    direct_count += 1
                use_ext = d['extended_winner']['objective'] < archived['nuisance']['objective']
                label = bank['labels'][d['extended_winner']['template_index']] if use_ext else model['nuisance_labels'][archived['nuisance']['template_index']]
                assert d['broad_winner_label'] == label
                assert d['broad_winner_origin'] == ('extended' if use_ext else 'original')
                expected_margin = min(d['extended_winner']['objective'], archived['nuisance']['objective'])-d['star']['objective']
                np.testing.assert_allclose(d['margins']['broad'], expected_margin, rtol=1e-12, atol=1e-10)
                assert d['margins']['original'] == archived['nuisance_delta_chi2']
                eligible = bool(source['screen_detected'] and archived['star']['amplitude_noise_score'] >= 5
                                and archived['star']['chi2']/archived['star']['residual_dof'] <= 2)
                assert d['eligible_without_margin'] == eligible
                for name in ('original', 'broad'):
                    accepted = bool(eligible and d['margins'][name] >= 9)
                    assert d['accepted_at_9'][name] == accepted
                    assert d['recovered_at_9'][name] == (accepted and not source['baseline_confounded'])
                assert d['original_recovered'] == archived['recovered']
                assert d['accepted_at_9']['original'] == archived['accepted']
                assert d['lost_at_9'] == (archived['recovered'] and not d['accepted_at_9']['broad'])
                assert not d['accepted_at_9']['broad'] or archived['accepted']
    cells = summary['cells']
    masks = []
    assert len(cells) == 27
    for cell in cells:
        mask = np.array([r['suite'] == cell['suite'] and r['kind'] == cell['kind']
                         and r.get('target_score') == cell['target_score'] for r in rows])
        assert mask.sum() == cell['trials']
        signal = cell['kind'] in ('stellar', 'off_profile')
        assert signal == cell['signal']
        if signal:
            assert cell['trials'] == (40 if cell['kind'] == 'stellar' else 160)
            assert cell['limit'] == (36 if cell['kind'] == 'stellar' else 128)
        else:
            assert cell['limit'] == cell['trials']//20
        masks.append(mask)
    assert len({c['cell_id'] for c in cells}) == 27
    sweep_cells = 0
    for key, sweep in sweeps.items():
        method, name = key.split('/')
        margins = np.array([r['methods'][method]['margins'][name] for r in rows])
        eligible = np.array([r['methods'][method]['eligible_without_margin'] and
                             not (r['kind'] in ('stellar', 'off_profile') and r['baseline_confounded']) for r in rows])
        cuts = np.array(sweep['thresholds'])
        want = sorted(set(margins[eligible].tolist()+[9., float(np.nextafter(max(margins[eligible]), np.inf))]))
        assert cuts.tolist() == want
        # Direct Boolean decisions at every threshold, independent of searchsorted.
        decisions = eligible[None, :] & (margins[None, :] >= cuts[:, None])
        counts = np.column_stack([np.sum(decisions[:, mask], axis=1) for mask in masks])
        np.testing.assert_array_equal(counts, sweep['counts'])
        signal_ok = [all(int(n) >= c['limit'] for n, c in zip(row, cells) if c['signal']) for row in counts]
        control_ok = [all(int(n) <= c['limit'] for n, c in zip(row, cells) if not c['signal']) for row in counts]
        assert signal_ok == sweep['signal_ok'] and control_ok == sweep['control_ok']
        endpoint = summary['endpoints'][key]
        assert endpoint['joint_feasible_thresholds'] == sum(a and b for a, b in zip(signal_ok, control_ok))
        assert endpoint['thresholds_evaluated'] == len(cuts)
        indices = {'reference_9': cuts.tolist().index(9.), 'control_safe': control_ok.index(True),
                   'signal_safe': max(i for i, v in enumerate(signal_ok) if v) if any(signal_ok) else None}
        for point, index in indices.items():
            entry = endpoint['points'][point]
            if index is None:
                assert entry is None and certificates[key][point] is None
                continue
            assert entry == {'index': index, 'threshold': float(cuts[index]), 'counts': counts[index].tolist(),
                             'signal_ok': signal_ok[index], 'control_ok': control_ok[index]}
            for mask, c, certificate in zip(masks, cells, certificates[key][point]):
                ids = np.flatnonzero(mask)
                assert certificate['cell_id'] == c['cell_id']
                accepted = [rows[i]['trial_id'] for i in ids if decisions[index, i]]
                rejected = [rows[i]['trial_id'] for i in ids if not decisions[index, i]]
                losses = [rows[i]['trial_id'] for i in ids if c['signal']
                          and rows[i]['methods'][method]['original_recovered'] and not decisions[index, i]]
                assert certificate['accepted_ids'] == accepted
                assert certificate['rejected_ids'] == rejected
                assert certificate['lost_from_ls7e_ids'] == losses
                assert certificate['ineligible_without_margin_ids'] == [rows[i]['trial_id'] for i in ids if not eligible[i]]
        sweep_cells += counts.size
    for group in summary['groups']:
        key = group['key']
        selected = []
        for r in rows:
            if [r['suite'], r['kind'], r.get('target_score')] != key[:3]:
                continue
            if r['suite'] == 'sparse_stress' and [r['residual_location'], int(np.sign(r['residual_e_per_s']))] != key[3:]:
                continue
            if r['suite'] == 'ls7c_replay' and r.get('target_score') is None and [r.get('amplitude_fraction'), r.get('shape')] != key[3:]:
                continue
            selected.append(r)
        assert len(selected) == group['trials']
        assert sum(r['screen_detected'] for r in selected) == group['screen_detected']
        assert sum(r['baseline_confounded'] for r in selected) == group['confounded']
        for method, banks in group['methods'].items():
            for name, counts in banks.items():
                for kind, n in counts.items():
                    assert sum(r['methods'][method][kind+'_at_9'][name] for r in selected) == n
    for bg in summary['per_background']:
        c = next(c for c in cells if c['cell_id'] == bg['cell_id'])
        selected = [r for r in rows if r['anchor'] == bg['anchor'] and r['suite'] == c['suite']
                    and r['kind'] == c['kind'] and r.get('target_score') == c['target_score']]
        assert len(selected) == bg['trials']
        for key, n in bg['counts_at_9'].items():
            method, name = key.split('/')
            field = 'recovered_at_9' if c['signal'] else 'accepted_at_9'
            assert sum(r['methods'][method][field][name] for r in selected) == n
    result = {'passed': True, 'trials': len(rows), 'models': len(models),
              'direct_whitened_fits': direct_count, 'exhaustive_rectangle_alternatives': alternatives,
              'max_direct_fit_absolute_error': max_direct_error, 'max_full_bank_minimum_absolute_error': max_minimum_error,
              'sweep_cell_counts_checked': sweep_cells, 'core_cells': len(cells),
              'all_certificates_checked': True, 'all_group_and_background_counts_checked': True,
              'historical_manifests_unchanged': True}
    (output/'AUDIT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
