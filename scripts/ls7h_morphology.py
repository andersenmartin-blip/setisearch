#!/usr/bin/env python3
"""Execute the frozen LS7H diagnosis on saved LS7G vectors and cutouts."""
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
from seti_repeater.tess_morphology import shape_bank, components, margin_components, decision, summarize

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def check_manifest(base, filename):
    for line in (base/filename).read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        assert hashlib.sha256((base/path.strip()).read_bytes()).hexdigest() == digest, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7h_morphology')
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('refusing to overwrite an existing result')
    cfg = json.loads((ROOT/'config/ls7h_morphology.json').read_text())
    for path, digest in cfg['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    for base, filename in cfg['preserve_manifests']+[('.', 'LS7H_FREEZE.sha256')]:
        check_manifest(ROOT/base, filename)
    source = ROOT/'results_ls7g_transfer'
    rows = [json.loads(x) for x in gzip.decompress((source/'trials.jsonl.gz').read_bytes()).splitlines()]
    models = {m['model_id']: m for m in json.loads((source/'models.json').read_text())}
    patterns = {p['pattern_id']: p for p in json.loads((source/'patterns.json').read_text())}
    previous = json.loads((source/'summary.json').read_text())
    raw = np.load(source/'backgrounds.npz', allow_pickle=False)
    native, seconds, aperture = [raw[k] for k in ['native', 'seconds', 'aperture']]
    assert len(rows) == len({r['trial_id'] for r in rows}) == 3540
    assert len(models) == 80 and aperture.sum() == 21
    added, labels = shape_bank(aperture, cfg['added_families'])
    args.output.mkdir(parents=True)
    save(args.output/'bank.json', {'families': cfg['added_families'], 'aperture_pixel_yx': np.argwhere(aperture).tolist(),
                                 'stamp_shape': list(aperture.shape), 'labels': labels,
                                 'templates': added.tolist(), 'duplicates_retained': True})
    features, cache = [], {}
    max_event_error, max_nonadditivity, max_decomposition_error = 0., 0., 0.
    for i, r in enumerate(rows):
        model = models[r['model_id']]
        if r['model_id'] not in cache:
            c = np.asarray(model['covariance'])
            cache[r['model_id']] = (FitBank(c, model['star_templates'], True, cfg['sparse_penalty']),
                                    FitBank(c, model['broad_templates'], True, cfg['sparse_penalty']),
                                    FitBank(c, added, True, cfg['sparse_penalty']))
        star_bank, broad_bank, added_bank = cache[r['model_id']]
        b, clean, pure, observed = components(native[r['anchor']], seconds[r['anchor']], aperture,
                                               patterns[r['pattern_id']]['vector'], r)
        error = float(np.max(abs(observed-r['event_vector'])))
        max_event_error = max(max_event_error, error)
        np.testing.assert_allclose(observed, r['event_vector'], rtol=1e-11, atol=1e-9)
        max_nonadditivity = max(max_nonadditivity, float(np.max(abs(clean-pure))))
        y = np.asarray(r['event_vector'])
        old = r['methods']['covariance_sparse']; plain = r['methods']['covariance_plain']
        new = added_bank.fit(y)
        use_added = new['objective'] < old['broad_nuisance']['objective']
        margin = min(new['objective'], old['broad_nuisance']['objective'])-old['star']['objective']
        ds = {'ls7g': decision(r, old['star'], old['margins']['broad'], cfg),
              'augmented': decision(r, old['star'], margin, cfg),
              'plain_ablation': decision(r, plain['star'], plain['margins']['broad'], cfg)}
        assert all(ds['ls7g'][k] == old['decisions']['broad']['-1'][k] for k in ['accepted', 'recovered', 'nuisance_preferred_acceptance'])
        assert not ds['augmented']['accepted'] or ds['ls7g']['accepted']
        clean_star, clean_broad, clean_added = [bank.fit(clean) for bank in cache[r['model_id']]]
        terms = margin_components(b, clean, model['covariance'],
                                  model['star_templates'][old['star']['template_index']],
                                  model['broad_templates'][old['broad_nuisance']['template_index']],
                                  old['star'], old['broad_nuisance'], cfg['sparse_penalty'])
        term_error = abs(terms['sum']-old['margins']['broad'])
        max_decomposition_error = max(max_decomposition_error, term_error)
        np.testing.assert_allclose(terms['sum'], old['margins']['broad'], rtol=1e-7, atol=2e-7)
        f = {'trial_id': r['trial_id'], 'model_id': r['model_id'], 'native_vector': b.tolist(),
             'clean_vector': clean.tolist(), 'pure_injection_vector': pure.tolist(),
             'added_fit': new, 'augmented_margin': margin,
             'augmented_winner_origin': 'added' if use_added else 'ls7g',
             'augmented_winner_label': labels[new['template_index']] if use_added else model['broad_labels'][old['broad_nuisance']['template_index']],
             'decisions': ds, 'fixed_winner_margin_components': terms,
             'clean': {'star': clean_star, 'broad': clean_broad, 'added': clean_added,
                       'margin_broad': clean_broad['objective']-clean_star['objective'],
                       'margin_augmented': min(clean_broad['objective'], clean_added['objective'])-clean_star['objective']}}
        features.append(f)
        if (i+1) % 300 == 0:
            print(f'Diagnosed {i+1}/{len(rows)} saved trials', flush=True)
    payload = b''.join((json.dumps(f, separators=(',', ':'), allow_nan=False)+'\n').encode() for f in features)
    (args.output/'features.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    result = summarize(rows, features, previous, cfg)
    focused_ids = {tid for cell in result['focus_cells'] for tid in cell['accepted_ids']}
    paired = []
    for r, f in zip(rows, features):
        if r['trial_id'] in focused_ids:
            ids = [j for j, q in enumerate(rows) if q['suite'] == 'base' and q['kind'] in ('stellar', 'off_profile')
                   and all(q.get(k) == r.get(k) for k in ['anchor', 'phase_seconds', 'shape', 'target_score'])]
            assert len(ids) == 5
            paired.append({'control_id': r['trial_id'], 'anchor': r['anchor'], 'shape': r['shape'],
                           'target_score': r['target_score'], 'paired_signals': [
                               {'trial_id': rows[j]['trial_id'], 'model_id': rows[j]['model_id'],
                                'shift_yx': rows[j]['shift_yx'], 'decisions': features[j]['decisions']}
                               for j in ids]})
    save(args.output/'paired_signals.json', paired)
    summary = {'status': 'COMPLETED', 'created_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'retrospective diagnosis and one fixed augmented-bank comparison on closed LS7G inputs',
               'source_commit': cfg['source_commit'], 'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'freeze_sha256': hashlib.sha256((ROOT/'LS7H_FREEZE.sha256').read_bytes()).hexdigest(),
               'trials': len(rows), 'backgrounds': len(native), 'models': len(models), 'added_templates': len(added),
               'suites': dict(Counter(r['suite'] for r in rows)), 'added_observing_days': 0,
               'margin': cfg['margin'], 'max_event_vector_error': max_event_error,
               'max_clean_pure_difference': max_nonadditivity, 'max_margin_decomposition_error': max_decomposition_error,
               'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'matplotlib']}},
               **result}
    save(args.output/'summary.json', summary)
    for base, filename in cfg['preserve_manifests']+[('.', 'LS7H_FREEZE.sha256')]:
        check_manifest(ROOT/base, filename)
    print(json.dumps({k: summary[k] for k in ['status', 'trials', 'added_templates', 'rules', 'max_clean_pure_difference']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
