#!/usr/bin/env python3
"""Restore closed sector-32 contexts and seal a common 6,720-row input index."""
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
from seti_repeater.light_sail_tess_v3 import matched_window
from seti_repeater.tess_joint_spatial import event_difference
from seti_repeater.tess_context_inputs import row_identity, sector32_recipe, reconstruct, validate_links


def check_sources(cfg):
    for path, expected in cfg['input_sha256'].items():
        assert sha256(ROOT/path) == expected, path
    counts = {}
    for base, manifest in cfg['preserve_manifests']+[('.', 'LS7I_INPUT_FREEZE.sha256')]:
        counts[base+'/'+manifest] = check_manifest(ROOT/base, ROOT/base/manifest)
    return counts


def restore32(cache, out, cfg):
    basecfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
    sources = json.loads((ROOT/'results_ls7e_joint/source_manifest.json').read_text())['products']
    paths, records = {}, []
    cache.mkdir(parents=True, exist_ok=True)
    for product in sources:
        path, record = retrieve({k: product[k] for k in ['kind', 'name', 'bytes']}, cache)
        assert record['sha256'] == product['sha256'], 'changed source product'
        paths[product['kind']] = path; records.append(record)
    preflight, _, _, good, quality = read_preflight(paths, basecfg)
    assert preflight == json.loads((ROOT/'results_ls7c_tess/preflight.json').read_text())
    assert preflight['pass'] and preflight['anchors'] == cfg['sectors']['32']['anchors']
    cube, aperture, time, cadence, _, flux, _, metadata = load_products(paths, basecfg)
    assert aperture.shape == (11, 11) and aperture.sum() == 18
    noises = json.loads((ROOT/'results_ls7c_tess/segments.json').read_text())
    old = json.loads((ROOT/'results_ls7c_tess/trials.json').read_text())
    native, seconds, sigmas, extra = [], [], [], {}
    anchors = preflight['anchors']
    for a, idx in enumerate(anchors):
        lo, hi = idx-200, idx+201
        assert np.all(good[lo:hi]) and np.all(np.diff(cadence[lo:hi]) == 1)
        matches = [n for n in noises if n['start'] <= lo and hi <= n['stop']]
        assert len(matches) == 1
        n = matches[0]; run_flux = flux[n['start']:n['stop']]
        sigma = robust_sigma(run_flux)
        np.testing.assert_allclose(sigma, n['sigma_e_per_s'], rtol=1e-12, atol=1e-12)
        src = [r for r in old if r['anchor'] == a]
        assert len(src) == 146 and all(r['native_index'] == idx for r in src)
        np.testing.assert_allclose([r['sigma_e_per_s'] for r in src], sigma, rtol=1e-12, atol=1e-12)
        native.append(cube[lo:hi].copy()); seconds.append((time[lo:hi]-time[idx])*86400.)
        sigmas.append(sigma)
        extra[f'run_flux_{a}'] = run_flux.copy()
        extra[f'run_bounds_{a}'] = np.array([n['start'], n['stop']])
    assert np.all(np.isfinite(native))
    np.savez_compressed(out/'sector32.npz', native=np.array(native), seconds=np.array(seconds), sigmas=np.array(sigmas),
                        aperture=aperture, anchors=np.array(anchors), anchor_btjd=time[anchors],
                        context_cadence=np.array([cadence[i-200:i+201] for i in anchors]),
                        context_quality=np.array([quality[i-200:i+201] for i in anchors]), **extra)
    for p in records:
        assert sha256(paths[p['kind']]) == p['sha256']
    save_json(out/'sector32_source.json', {'products': records, 'preflight': preflight, 'metadata': metadata})
    print('Restored 10 sector-32 contexts with original eligibility and source hashes.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7i_inputs')
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('refusing to overwrite an input package')
    cfg = json.loads((ROOT/'config/ls7i_inputs.json').read_text())
    before = check_sources(cfg)
    args.output.mkdir(parents=True)
    restore32(args.cache, args.output, cfg)
    basecfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
    old32 = {r['trial_id']: r for r in json.loads((ROOT/'results_ls7c_tess/trials.json').read_text())}
    recipes, patterns, datasets, checks, context_index = [], [], [], {}, []
    for sector in [29, 32]:
        spec = cfg['sectors'][str(sector)]
        path = ROOT/spec['contexts'] if sector == 29 else args.output/'sector32.npz'
        raw = np.load(path, allow_pickle=False)
        native, seconds, sigmas, aperture = [raw[k] for k in ['native', 'seconds', 'sigmas', 'aperture']]
        assert native.shape == (10, 401, 11, 11) and seconds.shape == (10, 401)
        assert aperture.sum() == spec['aperture_pixels'] and raw['anchors'].tolist() == spec['anchors']
        rows = [json.loads(x) for x in gzip.decompress((ROOT/spec['ledger']).read_bytes()).splitlines()]
        models = {m['model_id']: m for m in json.loads((ROOT/spec['models']).read_text())}
        training = json.loads((ROOT/spec['training']).read_text())
        old_patterns = ({p['pattern_id']: p for p in json.loads((ROOT/'results_ls7g_transfer/patterns.json').read_text())}
                        if sector == 29 else None)
        pattern_cache, maximum = {}, {'event_vector': 0., 'temporal_score': 0., 'training_vector': 0.}
        assert len(rows) == spec['trials']
        for sample in training['samples']:
            a, lo, width = sample['anchor'], sample['start'], sample['width']
            delta = event_difference(native[a][:, aperture], lo, lo+width)[0]/sigmas[a]
            maximum['training_vector'] = max(maximum['training_vector'], float(np.max(abs(delta-sample['normalized_delta']))))
            np.testing.assert_allclose(delta, sample['normalized_delta'], rtol=1e-11, atol=1e-11)
        for a in range(10):
            context_index.append({'context_id': f's{sector:03d}/a{a:02d}', 'sector': sector, 'anchor': a,
                                  'native_index': int(raw['anchors'][a]), 'btjd': float(raw['anchor_btjd'][a]),
                                  'first_cadence': int(raw['context_cadence'][a, 0]), 'last_cadence': int(raw['context_cadence'][a, -1]),
                                  'samples': 401, 'aperture_pixels': int(aperture.sum()), 'sigma_e_per_s': float(sigmas[a])})
        for i, r in enumerate(rows):
            f = row_identity(sector, r, i, spec['ledger'])
            if sector == 29:
                pattern = np.array(old_patterns[r['pattern_id']]['vector'])
                scale, residual = r['pattern_scale'], r['residual']
                parent = r.get('parent_trial_id')
            else:
                pattern, scale, residual, parent = sector32_recipe(r, old32, native[r['anchor']], aperture)
            # Physical kind/shift and anchor define a recipe pattern. Include its
            # bytes in the deduplication key so no semantic guess can merge it.
            key = (r['anchor'], pattern.astype('<f8').tobytes())
            if key not in pattern_cache:
                pid = f's{sector:03d}/pattern{len(pattern_cache):04d}'
                pattern_cache[key] = pid
                patterns.append({'pattern_id': pid, 'sector': sector, 'anchor': r['anchor'], 'vector': pattern.tolist()})
            f.update(pattern_id=pattern_cache[key], pattern_scale=float(scale), residual=residual,
                     source_parent_trial_id=parent, context_id=f's{sector:03d}/a{r["anchor"]:02d}')
            injected, centers = reconstruct(native[r['anchor']], seconds[r['anchor']], f, pattern)
            delta = r['sign']*event_difference(injected[:, aperture], r['best']['start'], r['best']['stop'])[0]
            maximum['event_vector'] = max(maximum['event_vector'], float(np.max(abs(delta-r['event_vector']))))
            np.testing.assert_allclose(delta, r['event_vector'], rtol=1e-11, atol=1e-9)
            for cube, recorded in [(injected, r['best']), (native[r['anchor']], r['native_best'])]:
                actual = matched_window(cube[:, aperture].sum(axis=1), seconds[r['anchor']], centers, sigmas[r['anchor']], basecfg, r['sign'])
                assert (actual['start'], actual['stop']) == (recorded['start'], recorded['stop'])
                maximum['temporal_score'] = max(maximum['temporal_score'], abs(actual['score']-recorded['score']))
                np.testing.assert_allclose(actual['score'], recorded['score'], rtol=1e-10, atol=1e-8)
            model = models[r['model_id']]
            assert (model['anchor'], model['start'], model['stop']) == (r['anchor'], r['best']['start'], r['best']['stop'])
            recipes.append(f)
            if (i+1) % 500 == 0:
                print(f'Sector {sector}: reconstructed {i+1}/{len(rows)} existing trial recipes', flush=True)
        checks[str(sector)] = {'trials': len(rows), 'models': len(models), 'training_vectors': len(training['samples']),
                               'patterns': len(pattern_cache), 'maximum_errors': maximum}
        datasets.append({'sector': sector, 'contexts': spec['contexts'], 'contexts_sha256': sha256(path),
                         'source_ledger': spec['ledger'], 'source_ledger_sha256': sha256(ROOT/spec['ledger']),
                         'source_models': spec['models'], 'source_training': spec['training'],
                         'aperture_pixels': int(aperture.sum()), 'anchors': spec['anchors'], 'trials': len(rows)})
    validate_links(recipes, {sector: s['trials'] for sector, s in cfg['sectors'].items()})
    payload = ''.join(json.dumps(r, separators=(',', ':'), allow_nan=False)+'\n' for r in recipes).encode()
    (args.output/'trial_recipes.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    save_json(args.output/'patterns.json', patterns)
    save_json(args.output/'contexts.json', context_index)
    save_json(args.output/'datasets.json', datasets)
    summary = {'status': 'INPUTS_RECONSTRUCTED', 'created_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'Restored inputs only; no new model, search, threshold, trial or coverage',
               'source_commit': cfg['source_commit'], 'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'github_run_id': os.environ.get('GITHUB_RUN_ID'), 'trials': len(recipes), 'backgrounds': len(context_index),
               'new_trials': 0, 'added_observing_days': 0, 'sectors': checks,
               'suite_counts': {str(s): dict(Counter(r['suite'] for r in recipes if r['sector'] == s)) for s in [29, 32]},
               'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'astropy']}},
               'preserved_manifests': before}
    assert check_sources(cfg) == before
    save_json(args.output/'summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
