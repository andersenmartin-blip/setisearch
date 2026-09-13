#!/usr/bin/env python3
"""LS7F: fixed broad-bank fits and exhaustive closed-data margin accounting."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from seti_repeater.tess_joint_spatial import FitBank
from seti_repeater.tess_separation import (
    rectangle_bank, exact_thresholds, threshold_counts, core_cells, group_key,
)

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def check_manifest(base, manifest):
    count = 0
    for line in manifest.read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        assert digest(base/name.strip()) == expected, name
        count += 1
    return count


def preflight(cfg):
    for name, expected in cfg['input_sha256'].items():
        assert digest(ROOT/name) == expected, name
    checked = {'LS7F_FREEZE.sha256': check_manifest(ROOT, ROOT/'LS7F_FREEZE.sha256')}
    for base, filename in cfg['preserve_manifests']:
        checked[base+'/'+filename] = check_manifest(ROOT/base, ROOT/base/filename)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7f_separation')
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('refusing to overwrite results')
    cfg = json.loads((ROOT/'config/ls7f_separation.json').read_text())
    checked = preflight(cfg)
    original = ROOT/'results_ls7e_joint'
    rows = [json.loads(line) for line in gzip.decompress((original/'trials.jsonl.gz').read_bytes()).splitlines()]
    models = {m['model_id']: m for m in json.loads((original/'models.json').read_text())}
    windows = json.loads((ROOT/'results_ls7d_noise/windows.json').read_text())
    coords = windows[0]['aperture_pixel_yx']
    assert all(w['aperture_pixel_yx'] == coords for w in windows)
    assert len(rows) == 3180 and len({r['trial_id'] for r in rows}) == 3180
    assert len(models) == 94 and len(coords) == 18
    assert dict(Counter(r['suite'] for r in rows)) == cfg['expected_suites']
    extended, labels = rectangle_bank(coords, [11, 11], cfg['rectangle_shapes'])
    # Independently locate the old named 2x2 templates in the aperture geometry.
    old_rectangles, old_labels = rectangle_bank(coords, [11, 11], [[2, 2]])
    old_geometry = {label.replace('rect2x2_', 'block2_'): p for label, p in zip(old_labels, old_rectangles)}
    for m in models.values():
        for label, p in zip(m['nuisance_labels'], m['nuisance_templates']):
            if label.startswith('block2_'):
                np.testing.assert_array_equal(p, old_geometry[label])
    args.output.mkdir(parents=True)
    save(args.output/'bank.json', {'aperture_pixel_yx': coords, 'stamp_shape': [11, 11],
                                 'shapes': cfg['rectangle_shapes'], 'labels': labels,
                                 'templates': extended.tolist(), 'duplicates_retained': True})
    cache, features = {}, []
    errors = Counter()
    for i, r in enumerate(rows):
        model = models[r['model_id']]
        assert (model['anchor'], model['start'], model['stop']) == (r['anchor'], r['best']['start'], r['best']['stop'])
        y = np.asarray(r['event_vector'])
        feature = {k: v for k, v in r.items() if k not in ('methods', 'event_vector', 'original')}
        feature['methods'] = {}
        for method in cfg['methods']:
            sparse = method == 'covariance_sparse'
            key = (r['model_id'], method)
            if key not in cache:
                c = np.asarray(model['covariance'])
                cache[key] = (FitBank(c, model['star_templates'], sparse, cfg['sparse_penalty']),
                              FitBank(c, model['nuisance_templates'], sparse, cfg['sparse_penalty']),
                              FitBank(c, extended, sparse, cfg['sparse_penalty']))
            star_bank, old_bank, ext_bank = cache[key]
            old = r['methods'][method]
            for name, bank in [('star', star_bank), ('nuisance', old_bank)]:
                fresh = bank.fit(y)
                for quantity in ('chi2', 'objective', 'amplitude_noise_score'):
                    errors[quantity] = max(errors[quantity], abs(fresh[quantity]-old[name][quantity]))
                    np.testing.assert_allclose(fresh[quantity], old[name][quantity], rtol=1e-7, atol=2e-7)
            # Retain the archived star and old margin exactly, after verifying
            # that the current runtime reproduces the frozen arithmetic.
            ext = ext_bank.fit(y)
            use_ext = ext['objective'] < old['nuisance']['objective']
            broad = ext if use_ext else old['nuisance']
            broad_label = labels[ext['template_index']] if use_ext else model['nuisance_labels'][broad['template_index']]
            star = old['star']
            eligible = bool(r['screen_detected'] and star['amplitude_noise_score'] >= 5.
                            and star['chi2']/star['residual_dof'] <= 2.)
            margins = {'original': old['nuisance_delta_chi2'],
                       'broad': broad['objective']-star['objective']}
            accepted = {bank: bool(eligible and margin >= 9.) for bank, margin in margins.items()}
            assert accepted['original'] == old['accepted']
            assert margins['broad'] <= margins['original']+1e-9
            assert not accepted['broad'] or accepted['original']
            feature['methods'][method] = {
                'eligible_without_margin': eligible, 'star': star,
                'extended_winner': ext, 'broad_winner_origin': 'extended' if use_ext else 'original',
                'broad_winner_label': broad_label, 'margins': margins,
                'accepted_at_9': accepted,
                'recovered_at_9': {k: bool(v and not r['baseline_confounded']) for k, v in accepted.items()},
                'original_recovered': old['recovered'],
                'lost_at_9': bool(old['recovered'] and not accepted['broad']),
            }
        features.append(feature)
        if (i+1) % 500 == 0:
            print(json.dumps({'rows_scored': i+1}), flush=True)
    cells = core_cells(features)
    masks = []
    for c in cells:
        mask = np.zeros(len(rows), dtype=bool)
        mask[c['indices']] = True
        masks.append(mask)
    is_signal = np.array([r['kind'] in ('stellar', 'off_profile') for r in rows])
    confounded = np.array([r['baseline_confounded'] for r in rows])
    sweeps, endpoints, certificates = {}, {}, {}
    signal_cols = np.array([c['signal'] for c in cells])
    limits = np.array([c['limit'] for c in cells])
    for method in cfg['methods']:
        for bank in ('original', 'broad'):
            key = method+'/'+bank
            margin = np.array([r['methods'][method]['margins'][bank] for r in features])
            eligible = np.array([r['methods'][method]['eligible_without_margin'] for r in features])
            eligible &= ~(is_signal & confounded)
            thresholds = exact_thresholds(margin, eligible)
            counts = threshold_counts(margin, eligible, thresholds, masks)
            signal_ok = np.all(counts[:, signal_cols] >= limits[signal_cols], axis=1)
            control_ok = np.all(counts[:, ~signal_cols] <= limits[~signal_cols], axis=1)
            indices = {'reference_9': int(np.flatnonzero(thresholds == 9.)[0]),
                       'control_safe': int(np.flatnonzero(control_ok)[0]),
                       'signal_safe': int(np.flatnonzero(signal_ok)[-1]) if np.any(signal_ok) else None}
            sweeps[key] = {'thresholds': thresholds.tolist(), 'counts': counts.tolist(),
                           'signal_ok': signal_ok.tolist(), 'control_ok': control_ok.tolist()}
            endpoints[key] = {'thresholds_evaluated': len(thresholds),
                              'joint_feasible_thresholds': int(np.sum(signal_ok & control_ok)), 'points': {}}
            certificates[key] = {}
            for name, index in indices.items():
                if index is None:
                    endpoints[key]['points'][name] = None
                    certificates[key][name] = None
                    continue
                selected = eligible & (margin >= thresholds[index])
                endpoints[key]['points'][name] = {'index': index, 'threshold': float(thresholds[index]),
                                                  'counts': counts[index].tolist(),
                                                  'signal_ok': bool(signal_ok[index]), 'control_ok': bool(control_ok[index])}
                certificates[key][name] = []
                for c in cells:
                    old_accepted = lambda i: features[i]['methods'][method]['original_recovered']
                    certificates[key][name].append({
                        'cell_id': c['cell_id'],
                        'accepted_ids': [features[i]['trial_id'] for i in c['indices'] if selected[i]],
                        'rejected_ids': [features[i]['trial_id'] for i in c['indices'] if not selected[i]],
                        'lost_from_ls7e_ids': [features[i]['trial_id'] for i in c['indices']
                                               if c['signal'] and old_accepted(i) and not selected[i]],
                        'ineligible_without_margin_ids': [features[i]['trial_id'] for i in c['indices'] if not eligible[i]],
                    })
    groups = []
    for key in sorted({group_key(r) for r in features}, key=str):
        selected = [r for r in features if group_key(r) == key]
        groups.append({'key': list(key), 'trials': len(selected),
                       'screen_detected': sum(r['screen_detected'] for r in selected),
                       'confounded': sum(r['baseline_confounded'] for r in selected),
                       'methods': {m: {b: {'accepted': sum(r['methods'][m]['accepted_at_9'][b] for r in selected),
                                          'recovered': sum(r['methods'][m]['recovered_at_9'][b] for r in selected)}
                                       for b in ('original', 'broad')} for m in cfg['methods']}})
    background = []
    for a in range(10):
        for c in cells:
            selected = [features[i] for i in c['indices'] if features[i]['anchor'] == a]
            background.append({'anchor': a, 'cell_id': c['cell_id'], 'trials': len(selected),
                               'counts_at_9': {m+'/'+b: sum(r['methods'][m]['recovered_at_9'][b] if c['signal']
                                                           else r['methods'][m]['accepted_at_9'][b] for r in selected)
                                               for m in cfg['methods'] for b in ('original', 'broad')}})
    after = preflight(cfg)
    assert checked == after
    payload = ''.join(json.dumps(r, separators=(',', ':'), allow_nan=False)+'\n' for r in features).encode()
    (args.output/'features.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'Retrospective separation development on 3180 saved LS7E trials, ten closed sector-32 backgrounds; no new injections or observing coverage',
               'source_commit': cfg['source_commit'],
               'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'freeze_sha256': digest(ROOT/'LS7F_FREEZE.sha256'),
               'environment': {'python': platform.python_version(), **{k: importlib.metadata.version(k) for k in ('numpy', 'scipy')}},
               'trials': len(features), 'models': len(models), 'backgrounds': 10,
               'new_rectangle_templates': len(labels), 'old_fit_checks': len(features)*len(cfg['methods'])*2,
               'original_fit_max_absolute_error': dict(errors), 'preserved_manifests_before_after': checked,
               'cells': [{k: v for k, v in c.items() if k != 'indices'} for c in cells],
               'endpoints': endpoints, 'groups': groups, 'per_background': background}
    save(args.output/'summary.json', summary)
    save(args.output/'sweeps.json', sweeps)
    save(args.output/'certificates.json', certificates)
    save(args.output/'source_manifest.json', {'source_commit': cfg['source_commit'], 'input_sha256': cfg['input_sha256']})
    print(json.dumps({'completed_trials': len(features), 'templates': len(labels),
                      'joint_feasible_thresholds': {k: v['joint_feasible_thresholds'] for k, v in endpoints.items()}}), flush=True)


if __name__ == '__main__':
    main()
