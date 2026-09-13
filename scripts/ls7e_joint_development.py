#!/usr/bin/env python3
"""Frozen closed-sector LS7E comparison, with complete paired decision ledgers."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from ls7_tess_pilot import ROOT, load_products, sha256, save_json
from ls7d_noise_diagnostic import verify_manifest
from seti_repeater.light_sail_tess import pulse_shape
from seti_repeater.light_sail_tess_v2 import shifted_profile, pointing_delta
from seti_repeater.light_sail_tess_v3 import (
    empirical_profile, nuisance_pattern, matched_window, strength_amplitude,
)
from seti_repeater.tess_joint_spatial import (
    event_difference, training_covariance, template_bank, FitBank, diagnose,
)


def records_summary(rows):
    keys = sorted({(r['suite'], r['kind'], r.get('target_score')) for r in rows}, key=str)
    result = []
    for suite, kind, score in keys:
        selected = [r for r in rows if (r['suite'], r['kind'], r.get('target_score')) == (suite, kind, score)]
        g = {'suite': suite, 'kind': kind, 'target_score': score, 'trials': len(selected),
             'screen_detected': sum(r['screen_detected'] for r in selected),
             'confounded': sum(r['baseline_confounded'] for r in selected),
             'methods': {}}
        for m in selected[0]['methods']:
            g['methods'][m] = {k: sum(r['methods'][m][k] for r in selected) for k in ('accepted', 'recovered')}
        if suite == 'ls7c_replay':
            g['ls7c_original_recovered'] = sum(r['original']['recovered'] for r in selected)
            g['ls7c_original_accepted'] = sum(r['original']['accepted'] for r in selected)
        result.append(g)
    return result


def extended_pattern(kind, profile, aperture):
    sizes = {'block3x3': (3, 3), 'row1x5': (1, 5), 'column5x1': (5, 1)}
    h, w = sizes[kind]
    choices = [(profile[y:y+h, x:x+w].sum(), y, x)
               for y in range(profile.shape[0]-h+1) for x in range(profile.shape[1]-w+1)]
    _, y, x = max(choices, key=lambda p: p[0])
    p = np.zeros(profile.shape); p[y:y+h, x:x+w] = 1.
    return p/p[aperture].sum(), [int(y), int(x)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7e_joint')
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('refusing to overwrite results')
    own = verify_manifest(ROOT, ROOT/'LS7E_FREEZE.sha256')
    cfg = json.loads((ROOT/'config/ls7e_joint.json').read_text())
    oldcfg = json.loads((ROOT/'config/ls7c_tess_l9859.json').read_text())
    for name, expected in cfg['input_sha256'].items():
        if sha256(ROOT/name) != expected:
            raise RuntimeError('changed input: '+name)
    preserved = {name: verify_manifest(ROOT, ROOT/name) for name in
                 ('LS7_FREEZE.sha256', 'LS7B_FREEZE.sha256', 'LS7C_FREEZE.sha256', 'LS7D_FREEZE.sha256')}
    for dirname, manifest in cfg['preserved_manifests']:
        base = ROOT/dirname
        preserved[dirname+'/'+manifest] = verify_manifest(base, base/manifest)
    sources = json.loads((ROOT/'results_ls7c_tess/source_manifest.json').read_text())['products']
    paths = {p['kind']: args.cache/p['name'] for p in sources}
    for p in sources:
        if sha256(paths[p['kind']]) != p['sha256']:
            raise RuntimeError('wrong FITS bytes')
    cube, aperture, time, cadence, _, _, _, metadata = load_products(paths, oldcfg)
    old = json.loads((ROOT/'results_ls7c_tess/trials.json').read_text())
    if len(old) != 1460 or metadata['sector'] != 32 or aperture.sum() != 18:
        raise RuntimeError('unexpected source dimensions')
    contexts, training = {}, []
    for a in range(10):
        src = next(r for r in old if r['anchor'] == a)
        idx, sigma = src['native_index'], src['sigma_e_per_s']
        native = cube[idx-200:idx+201].copy()
        seconds = (time[idx-200:idx+201]-time[idx])*86400
        if not np.all(np.diff(cadence[idx-200:idx+201]) == 1) or not np.all(np.isfinite(native)):
            raise RuntimeError('invalid fixed anchor context')
        reference = np.median(native, axis=0)
        profile = empirical_profile(reference, aperture)
        contexts[a] = {'native': native, 'seconds': seconds, 'sigma': sigma,
                       'reference': reference, 'profile': profile,
                       'level': float(np.median(native[:, aperture].sum(axis=1))), 'index': idx}
        for width in oldcfg['box_samples']:
            for start in cfg['training_starts']:
                delta, _ = event_difference(native[:, aperture], start, start+width)
                training.append({'sample_id': f'a{a:02d}_w{width}_s{start}', 'anchor': a,
                                 'width': width, 'start': start, 'sigma': sigma,
                                 'normalized_delta': (delta/sigma).tolist()})
    folds, covs = [], {}
    for a in range(10):
        for width in oldcfg['box_samples']:
            c, info = training_covariance(training, a, width, cfg['shrinkage'])
            covs[a, width] = c*contexts[a]['sigma']**2
            folds.append(info)
    args.output.mkdir(parents=True)
    save_json(args.output/'training.json', {'samples': training, 'folds': folds})
    rows, bank_cache, model_records, max_error = [], {}, {}, 0.

    def score(a, injected, best, sign):
        start, stop = best['start'], best['stop']
        key = (a, start, stop)
        if key not in bank_cache:
            _, ref = event_difference(contexts[a]['native'], start, stop)
            stars, nuisances, labels = template_bank(ref, aperture, oldcfg['spatial']['fit_shifts_yx'],
                                                    oldcfg['spatial']['pointing_template_shifts_yx'])
            c = covs[a, stop-start]
            model_records[key] = {'model_id': f'a{a}_s{start}_e{stop}', 'anchor': a,
                                  'start': start, 'stop': stop, 'covariance': c.tolist(),
                                  'star_templates': stars.tolist(), 'nuisance_templates': nuisances.tolist(),
                                  'nuisance_labels': labels}
            bank_cache[key] = {m: (FitBank(np.diag(np.diag(c)) if m == 'diagonal_sparse' else c,
                                          stars, m != 'covariance_plain', cfg['sparse_penalty']),
                                  FitBank(np.diag(np.diag(c)) if m == 'diagonal_sparse' else c,
                                          nuisances, m != 'covariance_plain', cfg['sparse_penalty']))
                               for m in cfg['methods']}
        delta, _ = event_difference(injected[:, aperture], start, stop)
        return {m: diagnose(sign*delta, *banks, cfg['spatial_gates']) for m, banks in bank_cache[key].items()}

    def append(a, injected, centers, sign, spec, original=None):
        ctx = contexts[a]
        best = matched_window(injected[:, aperture].sum(axis=1), ctx['seconds'], centers, ctx['sigma'], oldcfg, sign)
        native_best = matched_window(ctx['native'][:, aperture].sum(axis=1), ctx['seconds'], centers, ctx['sigma'], oldcfg, sign)
        detected = best['score'] >= oldcfg['score_threshold']
        confounded = native_best['score'] >= oldcfg['score_threshold']
        methods = score(a, injected, best, sign)
        for decision in methods.values():
            decision['accepted'] = bool(detected and decision['pass'])
            decision['recovered'] = bool(decision['accepted'] and not confounded)
        r = {**spec, 'anchor': a, 'native_index': ctx['index'], 'sign': sign,
             'best': best, 'native_best': native_best, 'screen_detected': bool(detected),
             'baseline_confounded': bool(confounded), 'methods': methods}
        r['model_id'] = f"a{a}_s{best['start']}_e{best['stop']}"
        r['event_vector'] = (sign*event_difference(injected[:, aperture], best['start'], best['stop'])[0]).tolist()
        if original is not None:
            nonlocal max_error
            error = abs(best['score']-original['best']['score'])
            max_error = max(max_error, error)
            if (error > 1e-8 or best['start'] != original['best']['start']
                    or best['stop'] != original['best']['stop'] or sign != original['sign']
                    or detected != original['screen_detected'] or confounded != original['baseline_confounded']):
                raise RuntimeError('original temporal result did not reproduce: '+original['trial_id'])
            r['original'] = {k: original[k] for k in ('trial_id', 'accepted', 'recovered', 'spatial_pass')}
            r['temporal_score_absolute_error'] = error
        rows.append(r)
        return best

    for a in range(10):
        ctx = contexts[a]
        for r in (r for r in old if r['anchor'] == a):
            pulse, centers = pulse_shape(ctx['seconds'], r['phase_seconds'], r['shape'], oldcfg['cadence_seconds'])
            if r['kind'] in ('stellar', 'off_profile', 'null'):
                pattern = shifted_profile(ctx['profile'], aperture, r['shift_yx'])
            else:
                pattern, _, _ = nuisance_pattern(r['kind'], ctx['reference'], ctx['profile'], aperture, r['shift_yx'])
            amp = (r['tuning']['amplitude_e_per_s'] if r['tuning'] is not None
                   else ctx['level']*r['amplitude_fraction'])
            injected = ctx['native']+(amp*pulse)[:, None, None]*pattern
            common = {k: r[k] for k in ('kind', 'shape', 'phase_seconds')}
            common['target_score'] = r.get('target_score')
            common['amplitude_fraction'] = r.get('amplitude_fraction')
            common['shift_yx'] = r['shift_yx']
            append(a, injected, centers, r['sign'], {'trial_id': 'replay_'+r['trial_id'],
                   'suite': 'ls7c_replay', 'source_group': r['group'], **common}, r)
            if (r['group'] == 'matched' and r['kind'] in ('stellar', 'block_2x2')) or r['kind'] == 'null':
                # Fixed faint aperture pixel; far exterior pixel. No event-driven choice.
                locations = {'inside': tuple(np.argwhere(aperture)[np.argmin(ctx['profile'][aperture])]),
                             'outside': (0, 0)}
                if aperture[0, 0]:
                    raise RuntimeError('fixed exterior pixel unexpectedly in aperture')
                j = int(np.argmin(ctx['profile'][aperture]))
                width = r['best']['stop']-r['best']['start']
                magnitude = cfg['residual_sigma']*np.sqrt(covs[a, width][j, j])
                for location, (y, x) in locations.items():
                    for polarity in (-1, 1):
                        altered = injected.copy()
                        altered[r['best']['start']:r['best']['stop'], y, x] += polarity*magnitude
                        append(a, altered, centers, r['sign'], {'trial_id': f"res_{r['trial_id']}_{location}_{polarity}",
                               'suite': 'sparse_stress', **common, 'parent_trial_id': r['trial_id'],
                               'residual_location': location, 'residual_yx': [int(y), int(x)],
                               'residual_e_per_s': float(polarity*magnitude)})
        for phase in oldcfg['injections']['phases_seconds']:
            for shape in oldcfg['strength_trials']['shapes']:
                pulse, centers = pulse_shape(ctx['seconds'], phase, shape, oldcfg['cadence_seconds'])
                for target in oldcfg['strength_trials']['scores']:
                    strength = strength_amplitude(ctx['native'][:, aperture].sum(axis=1), pulse, ctx['seconds'],
                                                  centers, ctx['sigma'], target, oldcfg)
                    if not strength['matched']:
                        raise RuntimeError('extended control strength could not be matched')
                    for kind in cfg['extended_controls']:
                        pattern, corner = extended_pattern(kind, ctx['profile'], aperture)
                        injected = ctx['native']+(strength['amplitude_e_per_s']*pulse)[:, None, None]*pattern
                        best = append(a, injected, centers, 1, {'trial_id': f'ext_a{a}_p{phase}_s{shape}_t{target}_{kind}',
                                      'suite': 'extended', 'kind': kind, 'shape': shape, 'phase_seconds': phase,
                                      'target_score': target, 'corner_yx': corner,
                                      'amplitude_e_per_s': strength['amplitude_e_per_s']})
                        if abs(best['score']-target) > .01:
                            raise RuntimeError('extended strength mismatch')
                for shift in cfg['physical_pointing_shifts_yx']:
                    pattern = pointing_delta(ctx['reference'], shift)
                    projection = float(pattern[aperture].sum())
                    sign = 1 if projection >= 0 else -1
                    injected = ctx['native']+pulse[:, None, None]*pattern
                    append(a, injected, centers, sign, {'trial_id': f'point_a{a}_p{phase}_s{shape}_d{shift[0]}_{shift[1]}',
                           'suite': 'physical_pointing', 'kind': 'pointing', 'shape': shape, 'phase_seconds': phase,
                           'target_score': None, 'shift_yx': shift, 'pattern_multiplier': 1.,
                           'aperture_projection_e_per_s': projection})
        print(json.dumps({'anchor_completed': a, 'cumulative_trials': len(rows)}), flush=True)
    if dict(Counter(r['suite'] for r in rows)) != cfg['expected_suites'] or len({r['trial_id'] for r in rows}) != len(rows):
        raise RuntimeError('trial accounting mismatch')
    summary = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'Closed sector 32 retrospective development; no new sector, coverage, candidate, or detector adoption',
               'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'freeze_sha256': sha256(ROOT/'LS7E_FREEZE.sha256'),
               'environment': {'python': platform.python_version(), **{k: importlib.metadata.version(k) for k in ('numpy', 'scipy', 'astropy', 'matplotlib')}},
               'source_metadata': metadata, 'total_trials': len(rows), 'suites': dict(Counter(r['suite'] for r in rows)),
               'original_temporal_scores_reproduced': 1460, 'max_temporal_score_error': max_error,
               'training_vectors': len(training), 'folds': len(folds), 'training_backgrounds_per_fold': 9,
               'covariance_samples_per_fold': 45, 'aperture_pixels': int(aperture.sum()),
               'preserved_input_checks': preserved, 'own_freeze_checks': own,
               'groups': records_summary(rows)}
    save_json(args.output/'summary.json', summary)
    save_json(args.output/'source_manifest.json', {'products': sources, 'input_sha256': cfg['input_sha256']})
    save_json(args.output/'models.json', list(model_records.values()))
    payload = ''.join(json.dumps(r, allow_nan=False, separators=(',', ':'))+'\n' for r in rows).encode()
    (args.output/'trials.jsonl.gz').write_bytes(gzip.compress(payload, mtime=0))
    for name, expected in cfg['input_sha256'].items():
        if sha256(ROOT/name) != expected:
            raise RuntimeError('input changed during run: '+name)
    print(json.dumps({'total_trials': len(rows), 'max_temporal_score_error': max_error}), flush=True)


if __name__ == '__main__':
    main()
