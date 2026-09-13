#!/usr/bin/env python3
"""Evaluate the prospectively fixed LS7I background model on both closed sectors."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess

import numpy as np

from seti_repeater.tess_background import observe, build_folds, predict, decision, common_energy
from seti_repeater.tess_context_inputs import reconstruct
from seti_repeater.tess_joint_spatial import template_bank, FitBank
from seti_repeater.tess_separation import rectangle_bank
from seti_repeater.tess_morphology import shape_bank
from seti_repeater.tess_transfer import placed_pattern
from seti_repeater.light_sail_tess_v3 import empirical_profile, matched_window

ROOT = Path(__file__).resolve().parents[1]
METHODS = ['conditional', 'static']
SIGNALS = ['stellar', 'off_profile']


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def save_rows(path, value):
    path.write_bytes(gzip.compress(b''.join((json.dumps(r, separators=(',', ':'), allow_nan=False)+'\n').encode() for r in value), mtime=0))


def verify(cfg):
    for path, digest in cfg['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    for base, filename in cfg['preserve_manifests']+[['.', 'LS7I_BACKGROUND_FREEZE.sha256']]:
        for line in (ROOT/base/filename).read_text().splitlines():
            digest, path = line.split(maxsplit=1)
            assert hashlib.sha256((ROOT/base/path.strip()).read_bytes()).hexdigest() == digest, path


def supplement(recipes, raw, patterns, basecfg, cfg):
    """Separate 360-row control cohort; use parent strength without retuning."""
    selected = [r for r in recipes if r['sector'] == 32 and r['suite'] == 'base'
                and r['kind'] == 'stellar' and r['target_score'] is not None]
    assert len(selected) == 120
    output, added = [], {}
    ap = raw['aperture']
    for parent in selected:
        a = parent['anchor']
        profile = empirical_profile(np.median(raw['native'][a], axis=0), ap)
        for kind in cfg['shape_families']:
            pattern_id = f's032/supplement/a{a:02d}/{kind}'
            if pattern_id not in added:
                p, corner = placed_pattern(kind, profile, ap)
                added[pattern_id] = {'pattern_id': pattern_id, 'sector': 32, 'anchor': a,
                                     'kind': kind, 'corner_yx': corner, 'vector': p.tolist()}
            r = {**parent, 'case_id': parent['case_id']+'/shape_supplement/'+kind,
                 'cohort': 'sector32_shape_supplement', 'suite': 'unmodeled_shapes', 'kind': kind,
                 'source_ledger': None, 'source_row': None, 'source_trial_id': None, 'source_suite': None,
                 'source_model_id': None, 'source_parent_trial_id': parent['source_trial_id'],
                 'parent_case_id': parent['case_id'], 'pattern_id': pattern_id}
            cube, centers = reconstruct(raw['native'][a], raw['seconds'][a], r, added[pattern_id]['vector'])
            r['best'] = matched_window(cube[:, ap].sum(axis=1), raw['seconds'][a], centers, raw['sigmas'][a], basecfg, 1)
            r['native_best'] = matched_window(raw['native'][a][:, ap].sum(axis=1), raw['seconds'][a], centers, raw['sigmas'][a], basecfg, 1)
            r['screen_detected'], r['baseline_confounded'] = r['best']['score'] >= 8., r['native_best']['score'] >= 8.
            output.append(r)
    assert len(output) == 360
    patterns.update(added)
    return output, list(added.values())


def archived_references():
    references = {}
    for row in rows(ROOT/'results_ls7g_transfer/trials.jsonl.gz'):
        d = row['methods']['covariance_sparse']['decisions']['broad']['-1']
        references['s029/'+row['trial_id']] = {'ls7g_broad_minus1': {k: d[k] for k in ['accepted', 'recovered']}}
    for row in rows(ROOT/'results_ls7h_morphology/features.jsonl.gz'):
        d = row['decisions']['augmented']
        references['s029/'+row['trial_id']]['ls7h_augmented_minus1'] = {k: d[k] for k in ['accepted', 'recovered']}
    for row in rows(ROOT/'results_ls7f_separation/features.jsonl.gz'):
        d = row['methods']['covariance_sparse']
        accepted = bool(d['eligible_without_margin'] and d['margins']['broad'] >= -1)
        references['s032/'+row['trial_id']] = {'ls7f_broad_minus1': {'accepted': accepted, 'recovered': accepted and not row['baseline_confounded']}}
    return references


def count(selected, method):
    return {key: sum(r['methods'][method]['decision'][key] for r in selected)
            for key in ['accepted', 'recovered', 'nuisance_preferred_acceptance']}


def summarize(trials, native, cfg):
    sectors, cells, backgrounds, diagnostics = {}, [], [], []
    for sector in cfg['sectors']:
        selected = [r for r in trials if r['sector'] == sector]
        keys = sorted({(r['suite'], r['kind'], r['target_score']) for r in selected
                       if r['suite'] in ['base', 'known_extended', 'unmodeled_shapes'] and r['target_score'] is not None}, key=str)
        sector_cells = []
        for suite, kind, target in keys:
            chosen = [r for r in selected if (r['suite'], r['kind'], r['target_score']) == (suite, kind, target)]
            signal = kind in SIGNALS
            limit = int(np.ceil((.9 if kind == 'stellar' else .8)*len(chosen))) if signal else len(chosen)//20
            item = {'sector': sector, 'suite': suite, 'kind': kind, 'target_score': target, 'signal': signal,
                    'cohort': chosen[0]['cohort'], 'trials': len(chosen), 'limit': limit, 'methods': {}}
            for method in METHODS:
                value = count(chosen, method)['recovered' if signal else 'accepted']
                item['methods'][method] = {'count': value, 'pass': value >= limit if signal else value <= limit,
                                           'headroom': value-limit if signal else limit-value}
            cells.append(item); sector_cells.append(item)
            for a in range(10):
                rr = [r for r in chosen if r['anchor'] == a]
                backgrounds.append({'sector': sector, 'anchor': a, 'suite': suite, 'kind': kind, 'target_score': target,
                                    'trials': len(rr), 'methods': {m: count(rr, m) for m in METHODS}})
        assert len(sector_cells) == 36
        bright = [r for r in selected if r['suite'] == 'base' and r['kind'] == 'stellar'
                  and r['amplitude_fraction'] == .1 and r['shape'] != 'doublet30sep87']
        nulls = [r for r in selected if r['suite'] == 'base' and r['kind'] == 'null']
        signals = [r for r in selected if r['kind'] in SIGNALS]
        pointing = [r for r in selected if r['suite'] == 'bounded_pointing' and r['screen_detected']]
        matched = [r for r in selected if r['target_score'] is not None and r['suite'] != 'sparse_stress']
        assert len(bright) == 60 and len(nulls) == 20
        ratios = []
        for a in range(10):
            rr = [r for r in native if r['sector'] == sector and r['anchor'] == a]
            totals = {m: sum(r['energies'][m] for r in rr) for m in METHODS}
            assert len(rr) == 21 and totals['static'] > 0
            ratios.append({'anchor': a, 'windows': len(rr), **totals, 'ratio': totals['conditional']/totals['static']})
        total = {m: sum(r[m] for r in ratios) for m in METHODS}
        native_ratio = total['conditional']/total['static']
        ng = {'total_energy_not_increased': native_ratio <= cfg['native_total_ratio_max'],
              'backgrounds_improved': sum(r['ratio'] < 1 for r in ratios) >= cfg['native_backgrounds_improved_min'],
              'no_background_more_than_doubled': max(r['ratio'] for r in ratios) <= cfg['native_background_ratio_max']}
        sector_summary = {'trials': len(selected), 'historical_trials': sum(r['cohort'] == 'historical' for r in selected),
                          'supplement_trials': sum(r['cohort'] != 'historical' for r in selected),
                          'suites': dict(Counter(r['suite'] for r in selected)), 'methods': {},
                          'native': {'windows': 210, 'ratio': native_ratio, 'per_background': ratios,
                                     'gates': ng, 'pass': all(ng.values())}}
        for method in METHODS:
            g = {'all_core_cells': all(c['methods'][method]['pass'] for c in sector_cells),
                 'all_target_strengths_matched': all(abs(r['best']['score']-r['target_score']) <= .01 for r in matched),
                 'ten_percent_single_recovery': count(bright, method)['recovered'] >= 54,
                 'no_base_null_acceptance': count(nulls, method)['accepted'] == 0,
                 'confounding_at_most_20_percent': sum(r['baseline_confounded'] for r in signals) <= .2*len(signals),
                 'bounded_pointing_screened_acceptance': bool(pointing) and count(pointing, method)['accepted'] <= .05*len(pointing)}
            sector_summary['methods'][method] = {'gates': g, 'trial_gate_pass': all(g.values()),
                'failed_signal_cells': sum(c['signal'] and not c['methods'][method]['pass'] for c in sector_cells),
                'failed_control_cells': sum(not c['signal'] and not c['methods'][method]['pass'] for c in sector_cells),
                'all_signals': {'trials': len(signals), **count(signals, method)},
                'bright_single': {'trials': len(bright), **count(bright, method)},
                'base_nulls': {'trials': len(nulls), **count(nulls, method)},
                'bounded_pointing': {'screened': len(pointing), **count(pointing, method)},
                'confounded_signals': sum(r['baseline_confounded'] for r in signals)}
        sectors[str(sector)] = sector_summary
        def diagnostic_key(r):
            residual = r.get('residual')
            return (r['cohort'], r['suite'], r['kind'], r['target_score'], r['amplitude_fraction'],
                    r['shape'], tuple(r['shift_yx']), None if residual is None else residual['location'],
                    None if residual is None else (1 if residual['amplitude_e_per_s'] > 0 else -1))
        for key in sorted({diagnostic_key(r) for r in selected}, key=str):
            rr = [r for r in selected if diagnostic_key(r) == key]
            diagnostics.append({'sector': sector, 'key': list(key), 'trials': len(rr),
                                'methods': {m: {**count(rr, m), 'paths': dict(Counter(r['methods'][m]['decision']['recovery_path'] for r in rr))} for m in METHODS}})
    return {'sectors': sectors, 'core_cells': cells, 'per_background_cells': backgrounds,
            'diagnostic_groups': diagnostics,
            'development_requirements_pass': all(s['methods']['conditional']['trial_gate_pass'] and s['native']['pass'] for s in sectors.values())}


def comparisons(trials):
    changes, aggregates = [], []
    for sector in [29, 32]:
        selected = [r for r in trials if r['sector'] == sector]
        names = sorted({name for r in selected for name in r['references']})+['static']
        for name in names:
            rr = selected if name == 'static' else [r for r in selected if name in r['references']]
            old = lambda r: r['methods']['static']['decision'] if name == 'static' else r['references'][name]
            signal_rows = [r for r in rr if r['kind'] in SIGNALS]
            control_rows = [r for r in rr if r['kind'] not in SIGNALS]
            entry = {'sector': sector, 'reference': name, 'paired_trials': len(rr), 'signal_rows': len(signal_rows),
                     'control_rows': len(control_rows), 'reference_recovered': sum(old(r)['recovered'] for r in signal_rows),
                     'conditional_recovered': sum(r['methods']['conditional']['decision']['recovered'] for r in signal_rows),
                     'stellar_losses': 0, 'stellar_gains': 0, 'controls_newly_accepted': 0, 'controls_newly_rejected': 0}
            for r in rr:
                signal = r['kind'] in SIGNALS
                key = 'recovered' if signal else 'accepted'
                before, after = old(r)[key], r['methods']['conditional']['decision'][key]
                if before == after:
                    continue
                change = ('stellar_gains' if after else 'stellar_losses') if signal else ('controls_newly_accepted' if after else 'controls_newly_rejected')
                entry[change] += 1
                changes.append({'case_id': r['case_id'], 'sector': sector, 'anchor': r['anchor'], 'reference': name,
                                'change': change, 'cohort': r['cohort'], 'suite': r['suite'], 'kind': r['kind'],
                                'target_score': r['target_score'], 'amplitude_fraction': r['amplitude_fraction'],
                                'shape': r['shape'], 'shift_yx': r['shift_yx'], 'residual': r['residual'],
                                'before': before, 'after': after, 'conditional': r['methods']['conditional']['decision']})
            aggregates.append(entry)
    return changes, aggregates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7i_background')
    args = parser.parse_args(); out = args.output
    if out.exists():
        raise SystemExit('Refusing to overwrite an existing model result')
    cfg = read(ROOT/'config/ls7i_background.json'); verify(cfg)
    basecfg = read(ROOT/'config/ls7c_tess_l9859.json')
    datasets = read(ROOT/'results_ls7i_inputs/datasets.json')
    raw = {}
    for d in datasets:
        with np.load(ROOT/d['contexts'], allow_pickle=False) as archive:
            raw[d['sector']] = {k: archive[k] for k in ['native', 'seconds', 'aperture', 'sigmas']}
    recipes = [{**r, 'cohort': 'historical'} for r in rows(ROOT/'results_ls7i_inputs/trial_recipes.jsonl.gz')]
    patterns = {r['pattern_id']: r for r in read(ROOT/'results_ls7i_inputs/patterns.json')}
    extra, extra_patterns = supplement(recipes, raw[32], patterns, basecfg, cfg)
    recipes += extra
    assert len(recipes) == len({r['case_id'] for r in recipes}) == 7080
    out.mkdir(parents=True)
    save_rows(out/'supplement_recipes.jsonl.gz', extra); save(out/'supplement_patterns.json', extra_patterns)
    training, regressions, folds = [], [], []
    for sector in cfg['sectors']:
        data = raw[sector]; selected = []
        assert data['native'].shape == (10, 401, 11, 11)
        for a in range(10):
            for width in cfg['widths']:
                for start in cfg['training_starts']:
                    obs = observe(data['native'][a], data['aperture'], start, start+width)
                    selected.append({'sample_id': f's{sector:03d}/a{a:02d}/w{width}/s{start}',
                                     'sector': sector, 'anchor': a, 'width': width, 'start': start, 'stop': start+width,
                                     'sigma': obs['sigma'], 'x': obs['x'].tolist(), 'y': obs['y'].tolist()})
        bundle = build_folds(selected, cfg['widths'], cfg['ridge_strength'], cfg['shrinkage'])
        for model in bundle['models']:
            model['model_id'] = f's{sector:03d}/'+model['model_id']; model['sector'] = sector
        for fold in bundle['folds']:
            fold['sector'] = sector; fold['fold_id'] = f's{sector:03d}/'+fold['fold_id']
            fold['model_id'] = f's{sector:03d}/'+fold['model_id']
            fold['calibration_models'] = [f's{sector:03d}/'+key for key in fold['calibration_models']]
        training += selected; regressions += bundle['models']; folds += bundle['folds']
        print(f'Sector {sector}: 390 native training records, 165 excluded-background regressions, 30 nested folds', flush=True)
    save_rows(out/'training.jsonl.gz', training); save_rows(out/'regressions.jsonl.gz', regressions); save_rows(out/'folds.jsonl.gz', folds)
    regression_map = {r['model_id']: r for r in regressions}; fold_map = {r['fold_id']: r for r in folds}
    references = archived_references()
    frames, banks, trials, max_protection_error = {}, {}, [], 0.
    for i, recipe in enumerate(recipes):
        sector, a = recipe['sector'], recipe['anchor']; data = raw[sector]; ap = data['aperture']
        cube, _ = reconstruct(data['native'][a], data['seconds'][a], recipe, patterns[recipe['pattern_id']]['vector'])
        lo, hi = recipe['best']['start'], recipe['best']['stop']
        obs = observe(cube, ap, lo, hi)
        # Harness-only preservation assertion: native truth is never passed to predict.
        native_obs = observe(data['native'][a], ap, lo, hi)
        for key in ['x', 'sigma', 'reference']:
            np.testing.assert_allclose(obs[key], native_obs[key], rtol=0, atol=0, equal_nan=True)
        max_protection_error = max(max_protection_error, float(np.max(abs(obs['x']-native_obs['x']))))
        fid = f's{sector:03d}/a{a:02d}/s{lo}/e{hi}'
        fold_id = f's{sector:03d}/a{a:02d}/w{hi-lo}'
        fold = fold_map[fold_id]; regression = regression_map[fold['model_id']]
        if fid not in frames:
            star, nuisance, labels = template_bank(obs['reference'], ap, basecfg['spatial']['fit_shifts_yx'], basecfg['spatial']['pointing_template_shifts_yx'])
            rectangle, rectangle_labels = rectangle_bank(np.argwhere(ap), [11, 11], cfg['rectangle_shapes'])
            shapes, shape_labels = shape_bank(ap, cfg['shape_families'])
            nuisance = np.vstack([nuisance, rectangle, shapes]); labels += rectangle_labels+shape_labels
            prediction = {m: predict(obs['x'], regression, m).tolist() for m in METHODS}
            frames[fid] = {'frame_id': fid, 'fold_id': fold_id, 'sector': sector, 'anchor': a, 'start': lo, 'stop': hi,
                           'x': obs['x'].tolist(), 'sigma': obs['sigma'], 'reference': obs['reference'].tolist(),
                           'predictions': prediction, 'star_templates': star.tolist(),
                           'nuisance_templates': nuisance.tolist(), 'nuisance_labels': labels}
            banks[fid] = {m: (FitBank(fold['methods'][m]['covariance'], star, True, cfg['sparse_penalty']),
                              FitBank(fold['methods'][m]['covariance'], nuisance, True, cfg['sparse_penalty'])) for m in METHODS}
        frame = frames[fid]
        np.testing.assert_array_equal(obs['x'], frame['x'])
        assert obs['sigma'] == frame['sigma']
        methods = {}
        for method in METHODS:
            y = recipe['sign']*(obs['y']-frame['predictions'][method])
            star, nuisance = [bank.fit(y) for bank in banks[fid][method]]
            methods[method] = {'residual': y.tolist(), 'star': star, 'nuisance': nuisance,
                               'nuisance_label': frame['nuisance_labels'][nuisance['template_index']],
                               'decision': decision(star, nuisance, recipe['screen_detected'], recipe['baseline_confounded'], cfg)}
        trials.append({**recipe, 'frame_id': fid, 'normalized_event': obs['y'].tolist(), 'methods': methods,
                       'references': references.get(recipe['case_id'], {})})
        if (i+1) % 600 == 0:
            print(f'Evaluated {i+1}/7080 fixed cases', flush=True)
    save_rows(out/'frames.jsonl.gz', list(frames.values())); save_rows(out/'trials.jsonl.gz', trials)
    native = []
    for sector in cfg['sectors']:
        data = raw[sector]
        for a in range(10):
            for width in cfg['widths']:
                fold = fold_map[f's{sector:03d}/a{a:02d}/w{width}']; regression = regression_map[fold['model_id']]
                for start in cfg['native_starts']:
                    obs = observe(data['native'][a], data['aperture'], start, start+width)
                    predictions = {m: predict(obs['x'], regression, m) for m in METHODS}
                    energies = {m: common_energy(obs['y']-predictions[m], fold['methods']['static']['covariance']) for m in METHODS}
                    native.append({'window_id': f's{sector:03d}/a{a:02d}/w{width}/s{start}', 'sector': sector,
                                   'anchor': a, 'start': start, 'stop': start+width, 'fold_id': fold['fold_id'],
                                   'x': obs['x'].tolist(), 'y': obs['y'].tolist(), 'sigma': obs['sigma'],
                                   'predictions': {m: p.tolist() for m, p in predictions.items()}, 'energies': energies})
    save_rows(out/'native_windows.jsonl.gz', native)
    changes, comparison_summary = comparisons(trials); save_rows(out/'changes.jsonl.gz', changes)
    summary = {'status': 'EVALUATED_AWAITING_AUDIT', 'created_utc': datetime.now(timezone.utc).isoformat(),
               'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'github_run_id': os.environ.get('GITHUB_RUN_ID'),
               'freeze_sha256': hashlib.sha256((ROOT/'LS7I_BACKGROUND_FREEZE.sha256').read_bytes()).hexdigest(),
               'scope': 'one fixed model and static ablation on two closed sectors; no unused-data qualification',
               'primary_method': 'conditional', 'trials': len(trials), 'historical_trials': 6720, 'supplement_trials': 360,
               'training_records': len(training), 'regressions': len(regressions), 'nested_folds': len(folds),
               'spatial_frames': len(frames), 'native_windows': len(native), 'backgrounds': 20, 'added_observing_days': 0,
               'maximum_protection_feature_error': max_protection_error, 'protected_cases_checked': len(trials),
               'comparisons': comparison_summary, 'changed_row_reference_pairs': len(changes),
               'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'matplotlib']}},
               **summarize(trials, native, cfg)}
    save(out/'summary.json', summary); verify(cfg)
    print(json.dumps({k: summary[k] for k in ['trials', 'spatial_frames', 'development_requirements_pass', 'comparisons']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
