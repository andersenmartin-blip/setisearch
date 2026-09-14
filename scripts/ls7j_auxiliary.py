#!/usr/bin/env python3
"""Frozen LS7J feasibility study: observable motion, outside pixels and pulses."""
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

from seti_repeater.tess_auxiliary import prepare, motion, predict, footprint, response_metrics, aperture_centroid
from seti_repeater.light_sail_tess import pulse_shape
from seti_repeater.tess_background import common_energy

ROOT = Path(__file__).resolve().parents[1]
METHODS = ['static', 'motion', 'plane', 'combined']
FIELDS = {'position_yx': ['POS_CORR2', 'POS_CORR1'],
          'moment_centroid_yx': ['MOM_CENTR2', 'MOM_CENTR1'],
          'moment_error_yx': ['MOM_CENTR2_ERR', 'MOM_CENTR1_ERR'],
          'psf_centroid_yx': ['PSF_CENTR2', 'PSF_CENTR1'],
          'psf_error_yx': ['PSF_CENTR2_ERR', 'PSF_CENTR1_ERR'],
          'sap_background': ['SAP_BKG'], 'sap_background_error': ['SAP_BKG_ERR']}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]


def serial(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def save(path, value):
    path.write_text(json.dumps(serial(value), indent=2, allow_nan=False)+'\n')


def save_rows(path, records):
    path.write_bytes(gzip.compress(b''.join((json.dumps(serial(r), separators=(',', ':'), allow_nan=False)+'\n').encode() for r in records), mtime=0))


def verify(cfg):
    for path, expected in cfg['input_sha256'].items():
        assert sha(ROOT/path) == expected, path
    for base, name in cfg['preserve_manifests']+[['.', 'LS7J_FREEZE.sha256']]:
        for line in (ROOT/base/name).read_text().splitlines():
            expected, path = line.split(maxsplit=1)
            assert sha(ROOT/base/path.strip()) == expected, path


def restore_auxiliary(raw, cfg, cache, out):
    from astropy.io import fits
    from ls7_tess_pilot import retrieve
    cache.mkdir(parents=True, exist_ok=True)
    auxiliary, sources = {}, []
    for sector in cfg['sectors']:
        product = cfg['products'][str(sector)]
        path, record = retrieve({k: product[k] for k in ['kind', 'name', 'bytes']}, cache)
        assert record['sha256'] == product['sha256'], 'changed historical light-curve product'
        data = raw[sector]; indices = np.array([np.arange(i-200, i+201) for i in data['anchors']])
        with fits.open(path, memmap=False) as hdus:
            hdus.verify('exception'); table = hdus[1].data; header = hdus[1].header
            assert hdus[0].header['TICID'] == 307210830 and hdus[0].header['SECTOR'] == sector
            assert header['TIMESYS'] == 'TDB' and header['BJDREFI']+header.get('BJDREFF', 0) == 2457000
            np.testing.assert_allclose(header['TIMEDEL']*86400., 20., rtol=1e-6)
            np.testing.assert_array_equal((hdus['APERTURE'].data & 2) != 0, data['aperture'])
            cadence = np.asarray(table['CADENCENO'], dtype=np.int64)[indices]
            time = np.asarray(table['TIME'], dtype=float)[indices]
            quality = np.asarray(table['QUALITY'], dtype=np.int64)[indices]
            np.testing.assert_array_equal(cadence, data['context_cadence'])
            np.testing.assert_allclose(time, data['anchor_btjd'][:, None]+data['seconds']/86400., rtol=0, atol=1e-7)
            assert np.all((quality | data['context_quality']) == data['context_quality'])
            values = {'time': time, 'cadence': cadence, 'quality': quality, 'anchors': data['anchors']}
            columns = {}
            for name, fields in FIELDS.items():
                parts = []
                for field in fields:
                    present = field in table.names
                    part = np.asarray(table[field], dtype=float)[indices] if present else np.full((10, 401), np.nan)
                    unit = hdus[1].columns[field].unit if present else None
                    if present and name not in ['sap_background', 'sap_background_error']:
                        assert unit in ['pixel', 'pixels'], (field, unit)
                    columns[field] = {'present': present, 'unit': unit,
                                      'format': hdus[1].columns[field].format if present else None,
                                      'finite_context_values': int(np.isfinite(part).sum()), 'context_values': 4010,
                                      'finite_per_background': np.isfinite(part).sum(axis=1).tolist()}
                    parts.append(part)
                values[name] = np.stack(parts, axis=-1) if len(parts) > 1 else parts[0]
            metadata = {key: hdus[0].header.get(key, header.get(key)) for key in
                        ['TICID', 'SECTOR', 'CAMERA', 'CCD', 'DATA_REL', 'PROCVER', 'DATE-OBS', 'DATE-END', 'PDCMETHD', 'CROWDSAP', 'FLFRCSAP']}
            sources.append({**record, 'sector': sector, 'rows': len(table), 'columns': columns, 'metadata': metadata,
                            'position_array_order': ['CCD row: POS_CORR2', 'CCD column: POS_CORR1'],
                            'missing_values_preserved': True, 'interpolation_applied': False})
        np.savez_compressed(out/f'auxiliary_s{sector:03d}.npz', **values)
        auxiliary[sector] = values
        print(f'Sector {sector}: restored 4010 auxiliary rows from the original hashed light-curve file', flush=True)
    save(out/'sources.json', sources)
    return auxiliary, sources


def frame_record(key, sector, anchor, cube, ap, lo, hi, position, shifts):
    prepared = prepare(cube, ap, lo, hi, shifts)
    motion_image, displacement = motion(position, prepared['reference'], lo, hi)
    delta = cube[lo:hi].mean(axis=0)-prepared['reference']
    record = {'frame_id': key, 'sector': sector, 'anchor': anchor,
              **{k: v for k, v in prepared.items() if k not in ['aperture', 'outside']},
              'motion_image': motion_image, 'motion_displacement_yx': displacement,
              'native_delta': delta, 'native_event_image': cube[lo:hi].mean(axis=0)}
    theory = []
    for p in prepared['profiles']:
        if prepared['valid']:
            predicted, _ = predict(p, prepared, np.zeros((11, 11)))
            theory.append(response_metrics(p[ap], (p-predicted['plane'])[ap]))
        else:
            theory.append(None)
    record['protected_basis_response'] = theory
    return record, prepared, motion_image


def addition(recipe, seconds, pattern):
    pulse, _ = pulse_shape(seconds, recipe['phase_seconds'], recipe['shape'], 20.)
    lo, hi = recipe['best']['start'], recipe['best']['stop']
    np.testing.assert_array_equal(pulse[np.r_[lo-60:lo-5, hi+5:hi+60]], 0.)
    signal = recipe['pattern_scale']*pulse[lo:hi].mean()*np.asarray(pattern)
    residual = np.zeros((11, 11))
    r = recipe['residual']
    if r is not None:
        support = np.zeros(401); support[r['start']:r['stop']] = r['amplitude_e_per_s']
        np.testing.assert_array_equal(support[np.r_[lo-60:lo-5, hi+5:hi+60]], 0.)
        residual[tuple(r['pixel_yx'])] = support[lo:hi].mean()
    return signal, residual


def case_response(recipe, pattern, seconds, record, model, image):
    signal, residual = addition(recipe, seconds, pattern)
    base = record['native_delta']
    native_prediction, _ = predict(base, model, image)
    observed_prediction, coefficients = predict(base+signal+residual, model, image)
    held_prediction, _ = predict(base+residual, model, image)
    ap = model['aperture']; response = {}
    # The plane is the only photon-dependent term. Motion metadata is held
    # fixed in these digital perturbations; that is not an independence proof
    # for the upstream mission processing that produced those metadata.
    for method in ['plane', 'combined']:
        if observed_prediction[method] is None:
            response[method] = None
            continue
        correction = (observed_prediction[method]-native_prediction[method])[ap]
        pulse_correction = (observed_prediction[method]-held_prediction[method])[ap]
        response[method] = {'whole_addition_transfer': (signal[ap]+residual[ap]-correction).tolist(),
                            'pulse_transfer': (signal[ap]-pulse_correction).tolist(),
                            'pulse_metrics': response_metrics(signal[ap], signal[ap]-pulse_correction),
                            'plane_coefficients': coefficients[method].tolist()}
    before = aperture_centroid(record['native_event_image']+residual, ap)
    after = aperture_centroid(record['native_event_image']+residual+signal, ap)
    return {'case_id': recipe['case_id'], 'sector': recipe['sector'], 'anchor': recipe['anchor'],
            'frame_id': record['frame_id'], 'cohort': recipe['cohort'], 'suite': recipe['suite'], 'kind': recipe['kind'],
            'shape': recipe['shape'], 'phase_seconds': recipe['phase_seconds'], 'target_score': recipe['target_score'],
            'amplitude_fraction': recipe['amplitude_fraction'], 'shift_yx': recipe['shift_yx'],
            'pattern_id': recipe['pattern_id'], 'pattern_scale': recipe['pattern_scale'], 'residual': recipe['residual'],
            'signal_addition_aperture': signal[ap].tolist(), 'residual_addition_aperture': residual[ap].tolist(),
            'response': response, 'motion_available': image is not None, 'operator_valid': model['valid'],
            'proxy_centroid_pulse_shift_yx': None if before is None or after is None else (after-before).tolist(),
            'parent_case_id': recipe.get('parent_case_id')}


def summarize(native, responses, frames, sources, cfg):
    result = {}
    for sector in cfg['sectors']:
        ns = [r for r in native if r['sector'] == sector]; rs = [r for r in responses if r['sector'] == sector]
        ff = [r for r in frames if r['sector'] == sector]
        methods = {}
        for method in METHODS:
            available = [r for r in ns if r['energies'][method] is not None]
            by_background = []
            for a in range(10):
                selected = [r for r in available if r['anchor'] == a]
                static = sum(r['energies']['static'] for r in selected)
                energy = sum(r['energies'][method] for r in selected)
                by_background.append({'anchor': a, 'available_windows': len(selected), 'energy': energy,
                                      'paired_static_energy': static, 'ratio': energy/static if static > 0 else None})
            total = sum(r['energies'][method] for r in available)
            static = sum(r['energies']['static'] for r in available)
            ratio = total/static if static > 0 else None
            gates = {'all_210_windows_available': len(available) == 210,
                     'aggregate_not_increased': ratio is not None and ratio <= 1.,
                     'six_backgrounds_improve': sum(b['ratio'] is not None and b['ratio'] < 1 for b in by_background) >= 6,
                     'no_background_more_than_doubled': all(b['ratio'] is not None and b['ratio'] <= 2. for b in by_background)}
            methods[method] = {'available_windows': len(available), 'energy': total, 'paired_static_energy': static,
                               'ratio': ratio, 'per_background': by_background, 'gates': gates, 'pass': all(gates.values())}
        protection = {}
        groups = [('aperture_limited_historical', [r for r in rs if r['cohort'] in ['historical', 'sector32_shape_supplement']
                                                and r['kind'] in ['stellar', 'off_profile']], cfg['historical_distortion_max']),
                  ('full_stamp', [r for r in rs if r['cohort'] == 'full_stamp'], cfg['full_stamp_distortion_max']),
                  ('broadened_full_stamp', [r for r in rs if r['cohort'] == 'broadened_full_stamp'], cfg['broadened_distortion_max'])]
        for name, selected, limit in groups:
            assert len(selected) == (1320 if name == 'aperture_limited_historical' else 600)
            valid = [r for r in selected if r['response']['combined'] is not None and r['response']['combined']['pulse_metrics'] is not None]
            metrics = [r['response']['combined']['pulse_metrics'] for r in valid]
            valid_ids = {r['case_id'] for r in valid}
            failed = [r['case_id'] for r in selected if r['case_id'] not in valid_ids or r['response']['combined']['pulse_metrics']['relative_distortion'] > limit]
            protection[name] = {'trials': len(selected), 'available': len(valid), 'distortion_limit': limit,
                                'maximum_distortion': max((m['relative_distortion'] for m in metrics), default=None),
                                'minimum_gain': min((m['gain'] for m in metrics), default=None),
                                'maximum_gain': max((m['gain'] for m in metrics), default=None),
                                'failed_case_ids': failed, 'pass': not failed}
        basis = [p for f in ff for p in f['protected_basis_response']]
        basis_error = max((r['relative_distortion'] for r in basis if r is not None), default=None)
        operator_gate = all(f['valid'] for f in ff) and all(r is not None for r in basis) and basis_error <= 1e-8
        source = next(r for r in sources if r['sector'] == sector)
        result[str(sector)] = {'native_windows': len(ns), 'response_trials': len(rs), 'cohorts': dict(Counter(r['cohort'] for r in rs)),
                               'methods': methods, 'protection': protection,
                               'spatial_frames': len(ff), 'valid_operators': sum(f['valid'] for f in ff),
                               'available_motion_frames': sum(f['motion_image'] is not None for f in ff),
                               'protected_basis_max_distortion': basis_error, 'operator_gate_pass': operator_gate,
                               'position_finite_values': {k: source['columns'][k]['finite_context_values'] for k in ['POS_CORR1', 'POS_CORR2']},
                               'feasibility_pass': bool(methods['combined']['pass'] and operator_gate and all(v['pass'] for v in protection.values()))}
    return {'sectors': result, 'feasibility_pass': all(r['feasibility_pass'] for r in result.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7j_auxiliary')
    args = parser.parse_args(); out = args.output
    if out.exists():
        raise SystemExit('Refusing to overwrite an existing LS7J result')
    cfg = read(ROOT/'config/ls7j_auxiliary.json'); verify(cfg)
    raw = {}
    for d in read(ROOT/'results_ls7i_inputs/datasets.json'):
        with np.load(ROOT/d['contexts'], allow_pickle=False) as archive:
            raw[d['sector']] = {k: archive[k] for k in ['native', 'seconds', 'aperture', 'anchors', 'anchor_btjd', 'context_cadence', 'context_quality']}
    out.mkdir(parents=True)
    auxiliary, sources = restore_auxiliary(raw, cfg, args.cache, out)
    old_native = rows(ROOT/'results_ls7i_background/native_windows.jsonl.gz')
    old_folds = {r['fold_id']: r for r in rows(ROOT/'results_ls7i_background/folds.jsonl.gz')}
    baselines = {}
    for r in old_native:
        key = r['fold_id']
        item = {'fold_id': key, 'sector': r['sector'], 'excluded_anchor': r['anchor'], 'width': r['stop']-r['start'],
                'mean': r['predictions']['static'], 'covariance': old_folds[key]['methods']['static']['covariance']}
        if key in baselines:
            assert baselines[key] == item
        baselines[key] = item
    assert len(baselines) == 60
    save(out/'baselines.json', list(baselines.values()))
    frame_map, model_map, motion_map = {}, {}, {}

    def frame(sector, anchor, lo, hi):
        key = f's{sector:03d}/a{anchor:02d}/s{lo}/e{hi}'
        if key not in frame_map:
            record, model, image = frame_record(key, sector, anchor, raw[sector]['native'][anchor], raw[sector]['aperture'],
                                                lo, hi, auxiliary[sector]['position_yx'][anchor], cfg['protected_shifts_yx'])
            frame_map[key], model_map[key], motion_map[key] = record, model, image
        return frame_map[key], model_map[key], motion_map[key]

    native = []
    for r in old_native:
        record, model, image = frame(r['sector'], r['anchor'], r['start'], r['stop'])
        ap = model['aperture']; y = record['native_delta'][ap]/model['sigma']
        np.testing.assert_allclose(y, r['y'], rtol=1e-12, atol=1e-12)
        baseline = baselines[r['fold_id']]
        predictions, coefficients = predict(record['native_delta'], model, image)
        residual = y-baseline['mean']
        energies = {'static': common_energy(residual, baseline['covariance'])}
        np.testing.assert_allclose(energies['static'], r['energies']['static'], rtol=1e-10, atol=1e-9)
        for method in ['motion', 'plane', 'combined']:
            p = predictions[method]
            energies[method] = None if p is None else common_energy(residual-p[ap]/model['sigma'], baseline['covariance'])
        native.append({'window_id': r['window_id'], 'sector': r['sector'], 'anchor': r['anchor'],
                       'frame_id': record['frame_id'], 'fold_id': r['fold_id'], 'energies': energies,
                       'corrections_aperture': {m: None if p is None else p[ap] for m, p in predictions.items()},
                       'plane_coefficients': coefficients, 'normalized_response': y})
    save_rows(out/'native_windows.jsonl.gz', native)
    print('Evaluated 420 fixed native windows with one combined correction and two component ablations', flush=True)
    recipes = [{**r, 'cohort': 'historical'} for r in rows(ROOT/'results_ls7i_inputs/trial_recipes.jsonl.gz')]
    recipes += rows(ROOT/'results_ls7i_background/supplement_recipes.jsonl.gz')
    patterns = {r['pattern_id']: r for r in read(ROOT/'results_ls7i_inputs/patterns.json')+read(ROOT/'results_ls7i_background/supplement_patterns.json')}
    assert len(recipes) == 7080
    responses, new_patterns, full_recipes = [], {}, []
    for i, recipe in enumerate(recipes):
        s, a = recipe['sector'], recipe['anchor']
        rec, model, image = frame(s, a, recipe['best']['start'], recipe['best']['stop'])
        responses.append(case_response(recipe, patterns[recipe['pattern_id']]['vector'], raw[s]['seconds'][a], rec, model, image))
        if (i+1) % 1200 == 0:
            print(f'Checked observable correction response: {i+1}/7080 existing recipes', flush=True)
    parents = [r for r in recipes if r['suite'] == 'base' and r['kind'] == 'stellar' and r['target_score'] is not None]
    assert len(parents) == 240
    for parent in parents:
        sector, a = parent['sector'], parent['anchor']
        for cohort, blur in [('full_stamp', 0.), ('broadened_full_stamp', cfg['broadening_sigma_pixels'])]:
            for index, displacement in enumerate(cfg['injected_shifts_yx']):
                pid = f's{sector:03d}/a{a:02d}/{cohort}/shift{index}'
                if pid not in new_patterns:
                    p = footprint(np.median(raw[sector]['native'][a], axis=0), raw[sector]['aperture'], displacement, blur)
                    new_patterns[pid] = {'pattern_id': pid, 'sector': sector, 'anchor': a, 'cohort': cohort,
                                         'shift_yx': displacement, 'blur_sigma': blur, 'vector': p,
                                         'outside_to_aperture_flux_ratio': float(p[~raw[sector]['aperture']].sum())}
                recipe = {**parent, 'case_id': parent['case_id']+'/auxiliary/'+cohort+f'/shift{index}',
                           'cohort': cohort, 'suite': 'full_stamp_response', 'parent_case_id': parent['case_id'],
                           'pattern_id': pid, 'shift_yx': displacement, 'kind': 'stellar' if index == 0 else 'off_profile'}
                for field in ['source_ledger', 'source_row', 'source_trial_id', 'source_suite', 'source_model_id']:
                    recipe[field] = None
                full_recipes.append(recipe)
                rec, model, image = frame(sector, a, recipe['best']['start'], recipe['best']['stop'])
                responses.append(case_response(recipe, new_patterns[pid]['vector'], raw[sector]['seconds'][a], rec, model, image))
    assert len(responses) == len({r['case_id'] for r in responses}) == 9480 and len(new_patterns) == 200
    save_rows(out/'full_stamp_recipes.jsonl.gz', full_recipes); save_rows(out/'full_stamp_patterns.jsonl.gz', list(new_patterns.values()))
    save_rows(out/'responses.jsonl.gz', responses); save_rows(out/'frames.jsonl.gz', list(frame_map.values()))
    save(out/'summary.json', {'status': 'FEASIBILITY_EVALUATED_AWAITING_AUDIT', 'created_utc': datetime.now(timezone.utc).isoformat(),
         'scope': 'auxiliary-observable availability, fixed physical correction, native prediction and signal response; no detector qualification',
         'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'github_run_id': os.environ.get('GITHUB_RUN_ID'), 'freeze_sha256': sha(ROOT/'LS7J_FREEZE.sha256'),
         'primary_method': 'combined', 'historical_recipe_rows': 6720, 'prior_shape_supplement_rows': 360,
         'new_full_stamp_response_rows': 2400, 'response_rows': len(responses), 'native_windows': len(native),
         'backgrounds': 20, 'added_observing_days': 0, 'new_detector_decisions': 0, 'spatial_frames': len(frame_map),
         'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'astropy', 'matplotlib']}},
         **summarize(native, responses, list(frame_map.values()), sources, cfg)})
    verify(cfg)
    summary = read(out/'summary.json')
    print(json.dumps({'feasibility_pass': summary['feasibility_pass'], 'response_rows': len(responses),
                      'native_ratios': {s: v['methods']['combined']['ratio'] for s, v in summary['sectors'].items()}}, indent=2), flush=True)


if __name__ == '__main__':
    main()
