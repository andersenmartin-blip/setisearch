#!/usr/bin/env python3
"""Acquire identity-pinned, already closed sector 29 and run frozen LS7G."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess

import numpy as np

from ls7_tess_pilot import ROOT, load_products, retrieve, save_json, sha256
from ls7b_tess_pilot import read_preflight
from ls7f_separation import check_manifest
from seti_repeater.light_sail_tess import robust_sigma
from seti_repeater.tess_transfer import evaluate_contexts, expected_suites, summarize


def check_sources(cfg):
    for name, expected in cfg['input_sha256'].items():
        assert sha256(ROOT/name) == expected, name
    checks = {'LS7G_FREEZE.sha256': check_manifest(ROOT, ROOT/'LS7G_FREEZE.sha256')}
    for base, name in cfg['preserve_manifests']:
        checks[base+'/'+name] = check_manifest(ROOT/base, ROOT/base/name)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7g_transfer')
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('refusing existing results')
    cfg = json.loads((ROOT/'config/ls7g_transfer.json').read_text())
    before = check_sources(cfg)
    oldcfg = json.loads((ROOT/'config/ls7b_tess_l9859.json').read_text())
    basecfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    paths, sources = {}, []
    for product in json.loads((ROOT/'results_ls7b_tess/source_manifest.json').read_text())['products']:
        path, record = retrieve({k: product[k] for k in ['kind', 'name', 'bytes']}, args.cache)
        assert record['sha256'] == product['sha256'], 'changed MAST bytes'
        paths[product['kind']] = path
        sources.append(record)
    preflight, segments, searchable, good, quality = read_preflight(paths, oldcfg)
    historical = json.loads((ROOT/'results_ls7b_tess/preflight.json').read_text())
    assert preflight == historical, 'sector-29 eligibility no longer reproduces'
    assert preflight['pass'] and preflight['anchors'] == cfg['anchors']
    cube, aperture, time, cadence, _, flux, corrected_flux, meta = load_products(paths, oldcfg)
    assert aperture.sum() == 21 and aperture.shape == (11, 11)
    noises = json.loads((ROOT/'results_ls7b_tess/segments.json').read_text())
    native, seconds, sigmas, archive = [], [], [], {}
    for a, idx in enumerate(cfg['anchors']):
        lo, hi = idx-200, idx+201
        assert np.all(good[lo:hi]) and np.all(np.diff(cadence[lo:hi]) == 1)
        selected = [n for n in noises if n['start'] <= lo and hi <= n['stop']]
        assert len(selected) == 1
        n = selected[0]
        run_flux = flux[n['start']:n['stop']]
        sigma = robust_sigma(run_flux)
        np.testing.assert_allclose(sigma, n['sigma_e_per_s'], rtol=1e-12, atol=1e-12)
        native.append(cube[lo:hi].copy())
        seconds.append((time[lo:hi]-time[idx])*86400.)
        sigmas.append(sigma)
        archive[f'run_flux_{a}'] = run_flux.copy()
        archive[f'run_bounds_{a}'] = np.array([n['start'], n['stop']])
    native, seconds, sigmas = np.asarray(native), np.asarray(seconds), np.asarray(sigmas)
    args.output.mkdir(parents=True)
    np.savez_compressed(args.output/'backgrounds.npz', native=native, seconds=seconds, sigmas=sigmas,
                        aperture=aperture, anchors=np.array(cfg['anchors']), anchor_btjd=time[cfg['anchors']],
                        context_cadence=np.array([cadence[i-200:i+201] for i in cfg['anchors']]),
                        context_quality=np.array([quality[i-200:i+201] for i in cfg['anchors']]), **archive)
    save_json(args.output/'preflight.json', preflight)
    rows, training, models, patterns = evaluate_contexts(native, seconds, aperture, sigmas, cfg, basecfg,
                                                       progress=lambda d: print(json.dumps(d), flush=True))
    assert dict(Counter(r['suite'] for r in rows)) == expected_suites()
    assert len(rows) == len({r['trial_id'] for r in rows}) == 3540
    save_json(args.output/'training.json', training)
    save_json(args.output/'models.json', models)
    save_json(args.output/'patterns.json', patterns)
    payload = ''.join(json.dumps(r, allow_nan=False, separators=(',', ':'))+'\n' for r in rows).encode()
    (args.output/'trials.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'status': 'COMPLETED',
              'scope': 'Fixed transfer on previously inspected sector 29, not independent qualification or a candidate search',
              'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'freeze_sha256': sha256(ROOT/'LS7G_FREEZE.sha256'), 'source_commit': cfg['source_commit'],
              'github_run_id': os.environ.get('GITHUB_RUN_ID'),
              'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'astropy', 'matplotlib']}},
              'trials': len(rows), 'suites': expected_suites(), 'models': len(models),
              'training_samples': len(training['samples']), 'covariance_folds': len(training['folds']),
              'source_metadata': meta, 'aperture_pixels': int(aperture.sum()), 'backgrounds': 10,
              'added_observing_days': 0, 'primary_rule': 'covariance_sparse/broad/-1',
              'preserved_manifests_before_after': before, **summarize(rows, cfg)}
    assert check_sources(cfg) == before
    for p in sources:
        assert sha256(paths[p['kind']]) == p['sha256']
    save_json(args.output/'summary.json', result)
    save_json(args.output/'source_manifest.json', {'products': sources, 'input_sha256': cfg['input_sha256']})
    print(json.dumps({'trials': len(rows), 'primary_diagnostic_pass': result['rules'][result['primary_rule']]['pass']}), flush=True)


if __name__ == '__main__':
    main()
