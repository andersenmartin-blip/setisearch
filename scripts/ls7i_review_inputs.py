#!/usr/bin/env python3
"""Independent reconstruction of the common LS7I input package.

Reuse audited pulse/temporal arithmetic; do not import the new recipe builder.
When --cache is supplied, independently restore sector-32 FITS slices too.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import shift

from ls7g_review import pulse, temporal

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def raw_review(cache, archive, source):
    from astropy.io import fits
    products = source['products']
    for p in products:
        path = cache/p['name']
        assert path.stat().st_size == p['bytes'] and digest(path) == p['sha256']
    paths = {p['kind']: cache/p['name'] for p in products}
    maximum = 0.
    with fits.open(paths['tp'], memmap=False) as tp, fits.open(paths['lc'], memmap=False) as lc:
        assert tp[0].header['SECTOR'] == lc[0].header['SECTOR'] == 32
        assert tp[0].header['TICID'] == lc[0].header['TICID'] == 307210830
        t, lt = tp[1].data, lc[1].data
        ap = (tp['APERTURE'].data & 2) != 0
        np.testing.assert_array_equal(ap, archive['aperture'])
        np.testing.assert_array_equal(t['CADENCENO'], lt['CADENCENO'])
        cr = tp['TARGET COSMIC RAY'].data
        column, row = int(tp[1].header['1CRV5P']), int(tp[1].header['2CRV5P'])
        corrections = {}
        for record in cr:
            corrections.setdefault(int(record['CADENCENO']), []).append(
                (int(record['RAWY'])-row, int(record['RAWX'])-column, float(record['COSMIC_RAY'])))
        def restored_slice(lo, hi):
            values = np.array(t['FLUX'][lo:hi], dtype=float)
            for j, cadence in enumerate(t['CADENCENO'][lo:hi]):
                for y, x, value in corrections.get(int(cadence), []):
                    assert 0 <= y < 11 and 0 <= x < 11
                    values[j, y, x] += value
            return values
        for a, idx in enumerate(archive['anchors']):
            lo, hi = int(idx)-200, int(idx)+201
            expected = restored_slice(lo, hi)
            maximum = max(maximum, float(np.max(abs(expected-archive['native'][a]))))
            np.testing.assert_array_equal(expected, archive['native'][a])
            np.testing.assert_array_equal(t['CADENCENO'][lo:hi], archive['context_cadence'][a])
            q = np.array(t['QUALITY'][lo:hi], dtype=np.int64) | np.array(lt['QUALITY'][lo:hi], dtype=np.int64)
            np.testing.assert_array_equal(q, archive['context_quality'][a])
            sec = (np.array(t['TIME'][lo:hi], dtype=float)-float(t['TIME'][idx]))*86400
            np.testing.assert_array_equal(sec, archive['seconds'][a])
            assert float(t['TIME'][idx]) == archive['anchor_btjd'][a]
            run_lo, run_hi = map(int, archive[f'run_bounds_{a}'])
            expected_flux = restored_slice(run_lo, run_hi)[:, ap].sum(axis=1)
            np.testing.assert_array_equal(expected_flux, archive[f'run_flux_{a}'])
    return {'passed': True, 'full_stamp_context_samples': 4010, 'maximum_pixel_error': maximum,
            'original_run_flux_arrays_checked': 10, 'source_products_checked': len(products)}


def independent32(row, originals, native, aperture):
    reference = np.median(native, axis=0)
    profile = np.zeros((11, 11)); profile[aperture] = np.maximum(reference[aperture], 0.)
    profile /= profile.sum()
    parent_id, residual = None, None
    if row['suite'] in ['ls7c_replay', 'sparse_stress']:
        parent_id = row['original']['trial_id'] if row['suite'] == 'ls7c_replay' else row['parent_trial_id']
        p = originals[parent_id]; kind = p['kind']; movement = p['shift_yx']
        scale = p['tuning']['amplitude_e_per_s'] if p['tuning'] is not None else np.median(native[:, aperture].sum(axis=1))*p['amplitude_fraction']
        if row['suite'] == 'sparse_stress':
            residual = {'pixel_yx': row['residual_yx'], 'start': p['best']['start'], 'stop': p['best']['stop'],
                        'amplitude_e_per_s': row['residual_e_per_s'], 'location': row['residual_location']}
    else:
        kind = row['kind']; movement = row.get('shift_yx', [0., 0.])
        scale = row['amplitude_e_per_s'] if row['suite'] == 'extended' else 1.
    if kind in ['stellar', 'off_profile', 'null']:
        pattern = shift(profile, movement, order=1, mode='constant', cval=0., prefilter=False)
        pattern[~aperture] = 0; pattern /= pattern.sum()
    elif kind == 'pointing':
        image = np.nan_to_num(reference, nan=0.)
        moved = shift(image, movement, order=1, mode='nearest', prefilter=False)
        moved *= image.sum()/moved.sum(); pattern = moved-image
        if row['suite'] != 'physical_pointing':
            pattern /= abs(pattern[aperture].sum())
        assert row['sign'] == (1 if pattern[aperture].sum() >= 0 else -1)
    elif kind == 'single_pixel':
        pattern = np.zeros((11, 11)); pattern.flat[np.argmax(profile)] = 1.
    elif kind == 'uniform':
        pattern = np.ones((11, 11)); pattern /= pattern[aperture].sum()
    else:
        h, w = {'block_2x2': (2, 2), 'block3x3': (3, 3), 'row1x5': (1, 5), 'column5x1': (5, 1)}[kind]
        positions = [(float(np.sum(profile[y:y+h, x:x+w])), y, x) for y in range(12-h) for x in range(12-w)]
        _, y, x = max(positions, key=lambda v: v[0])
        if row['suite'] == 'extended':
            assert row['corner_yx'] == [y, x]
        pattern = np.zeros((11, 11)); pattern[y:y+h, x:x+w] = 1.; pattern /= pattern[aperture].sum()
    return pattern, float(scale), residual, parent_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7i_inputs')
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args()
    out = args.output
    cfg = json.loads((ROOT/'config/ls7i_inputs.json').read_text())
    for name, expected in cfg['input_sha256'].items():
        assert digest(ROOT/name) == expected
    for base, manifest in cfg['preserve_manifests']+[('.', 'LS7I_INPUT_FREEZE.sha256')]:
        for line in (ROOT/base/manifest).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert digest(ROOT/base/name.strip()) == expected, name
    recipes = [json.loads(x) for x in gzip.decompress((out/'trial_recipes.jsonl.gz').read_bytes()).splitlines()]
    patterns = {p['pattern_id']: p for p in json.loads((out/'patterns.json').read_text())}
    summary = json.loads((out/'summary.json').read_text())
    datasets = json.loads((out/'datasets.json').read_text())
    contexts = json.loads((out/'contexts.json').read_text())
    originals = {r['trial_id']: r for r in json.loads((ROOT/'results_ls7c_tess/trials.json').read_text())}
    assert len(recipes) == len({r['case_id'] for r in recipes}) == 6720
    assert len(contexts) == 20 and summary['trials'] == 6720 and summary['backgrounds'] == 20
    assert summary['new_trials'] == summary['added_observing_days'] == 0
    assert [d['sector'] for d in datasets] == [29, 32]
    raw_check = None
    errors, checked, used_patterns = {}, {}, set()
    for sector in [29, 32]:
        spec = cfg['sectors'][str(sector)]
        path = ROOT/spec['contexts'] if sector == 29 else out/'sector32.npz'
        raw = np.load(path, allow_pickle=False)
        native, seconds, sigmas, aperture = [raw[k] for k in ['native', 'seconds', 'sigmas', 'aperture']]
        assert native.shape == (10, 401, 11, 11) and aperture.sum() == spec['aperture_pixels']
        assert raw['anchors'].tolist() == spec['anchors'] and np.all(np.diff(raw['context_cadence'], axis=1) == 1)
        assert np.all(np.diff(raw['seconds'], axis=1) > 0) and np.all((raw['context_quality'] & ~1088) == 0)
        assert np.all(np.isfinite(native[:, :, aperture]))
        desc = next(d for d in datasets if d['sector'] == sector)
        assert desc['contexts'] == spec['contexts'] and digest(path) == desc['contexts_sha256']
        assert desc['source_ledger'] == spec['ledger'] and digest(ROOT/spec['ledger']) == desc['source_ledger_sha256']
        assert desc['source_models'] == spec['models'] and desc['source_training'] == spec['training']
        assert desc['anchors'] == spec['anchors'] and desc['aperture_pixels'] == int(aperture.sum())
        cs = [c for c in contexts if c['sector'] == sector]
        assert len(cs) == 10 and [c['anchor'] for c in cs] == list(range(10))
        for a, c in enumerate(cs):
            assert c['context_id'] == f's{sector:03d}/a{a:02d}' and c['samples'] == 401
            assert c['native_index'] == raw['anchors'][a] and c['btjd'] == raw['anchor_btjd'][a]
            assert c['first_cadence'] == raw['context_cadence'][a, 0] and c['last_cadence'] == raw['context_cadence'][a, -1]
            assert c['aperture_pixels'] == aperture.sum() and c['sigma_e_per_s'] == sigmas[a]
            d = np.diff(raw[f'run_flux_{a}'])
            sigma = 1.482602218505602*np.median(abs(d-np.median(d)))/np.sqrt(2)
            np.testing.assert_allclose(sigma, sigmas[a], rtol=1e-12, atol=1e-12)
        if sector == 32 and args.cache is not None:
            raw_check = raw_review(args.cache, raw, json.loads((out/'sector32_source.json').read_text()))
        old = [json.loads(x) for x in gzip.decompress((ROOT/spec['ledger']).read_bytes()).splitlines()]
        models = {m['model_id']: m for m in json.loads((ROOT/spec['models']).read_text())}
        rr = [r for r in recipes if r['sector'] == sector]
        assert len(rr) == len(old) == spec['trials'] == desc['trials']
        assert [r['source_row'] for r in rr] == list(range(len(old)))
        old_patterns = ({p['pattern_id']: p for p in json.loads((ROOT/'results_ls7g_transfer/patterns.json').read_text())}
                        if sector == 29 else None)
        err = {'event_vector': 0., 'temporal_score': 0., 'training_vector': 0.}
        native_best_cache = {}
        for r, archived in zip(rr, old):
            assert r['case_id'] == f's{sector:03d}/{archived["trial_id"]}'
            assert r['source_trial_id'] == archived['trial_id'] and r['source_ledger'] == spec['ledger']
            assert r['source_suite'] == archived['suite'] and r['source_model_id'] == archived['model_id']
            suite = archived['suite'] if sector == 29 else {'ls7c_replay': 'base', 'sparse_stress': 'sparse_stress', 'extended': 'known_extended', 'physical_pointing': 'bounded_pointing'}[archived['suite']]
            assert r['suite'] == suite
            for key in ['kind', 'shape', 'anchor', 'phase_seconds', 'sign', 'best', 'native_best', 'screen_detected', 'baseline_confounded']:
                assert r[key] == archived[key]
            for key in ['target_score', 'amplitude_fraction']:
                assert r[key] == archived.get(key)
            assert r['shift_yx'] == archived.get('shift_yx', [0., 0.])
            assert r['context_id'] == f's{sector:03d}/a{r["anchor"]:02d}'
            a = r['anchor']; p = patterns[r['pattern_id']]
            used_patterns.add(r['pattern_id'])
            assert p['sector'] == sector and p['anchor'] == a
            if sector == 29:
                expected = old_patterns[archived['pattern_id']]['vector']
                scale, residual, parent = archived['pattern_scale'], archived['residual'], archived.get('parent_trial_id')
            else:
                expected, scale, residual, parent = independent32(archived, originals, native[a], aperture)
            np.testing.assert_allclose(p['vector'], expected, rtol=1e-12, atol=1e-10)
            np.testing.assert_allclose(r['pattern_scale'], scale, rtol=1e-12, atol=1e-10)
            assert r['residual'] == residual and r['source_parent_trial_id'] == parent
            pulses, centers = pulse(seconds[a], r['phase_seconds'], r['shape'])
            injected = native[a]+(scale*pulses)[:, None, None]*np.array(expected)
            if residual is not None:
                y, x = residual['pixel_yx']
                injected[residual['start']:residual['stop'], y, x] += residual['amplitude_e_per_s']
            lo, hi = r['best']['start'], r['best']['stop']
            side = np.concatenate([injected[lo-60:lo-5][:, aperture], injected[hi+5:hi+60][:, aperture]])
            vector = r['sign']*(np.mean(injected[lo:hi][:, aperture], axis=0)-np.median(side, axis=0))
            err['event_vector'] = max(err['event_vector'], float(np.max(abs(vector-archived['event_vector']))))
            np.testing.assert_allclose(vector, archived['event_vector'], rtol=1e-11, atol=1e-9)
            key = (a, r['phase_seconds'], r['shape'], r['sign'])
            if key not in native_best_cache:
                native_best_cache[key] = temporal(native[a][:, aperture].sum(axis=1), seconds[a], centers, sigmas[a], r['sign'])
            actual = temporal(injected[:, aperture].sum(axis=1), seconds[a], centers, sigmas[a], r['sign'])
            for result, target in [(actual, r['best']), (native_best_cache[key], r['native_best'])]:
                assert (result['start'], result['stop']) == (target['start'], target['stop'])
                err['temporal_score'] = max(err['temporal_score'], abs(result['score']-target['score']))
                np.testing.assert_allclose(result['score'], target['score'], rtol=1e-10, atol=1e-8)
            assert r['screen_detected'] == (actual['score'] >= 8)
            assert r['baseline_confounded'] == (native_best_cache[key]['score'] >= 8)
            model = models[r['source_model_id']]
            assert (model['anchor'], model['start'], model['stop']) == (a, lo, hi)
        training = json.loads((ROOT/spec['training']).read_text())['samples']
        assert len(training) == 150
        for t in training:
            a, lo, hi = t['anchor'], t['start'], t['start']+t['width']
            side = np.concatenate([native[a, lo-60:lo-5][:, aperture], native[a, hi+5:hi+60][:, aperture]])
            delta = (np.mean(native[a, lo:hi][:, aperture], axis=0)-np.median(side, axis=0))/sigmas[a]
            err['training_vector'] = max(err['training_vector'], float(np.max(abs(delta-t['normalized_delta']))))
            np.testing.assert_allclose(delta, t['normalized_delta'], rtol=1e-11, atol=1e-11)
        assert summary['suite_counts'][str(sector)] == dict(Counter(r['suite'] for r in rr))
        checked[str(sector)] = {'trials': len(rr), 'training_vectors': len(training), 'model_links': len(models)}
        errors[str(sector)] = err
        print(f'Independently checked sector {sector}: {len(rr)} recipes and {len(training)} training vectors.', flush=True)
    assert used_patterns == set(patterns)
    audit = {'passed': True, 'trial_recipes_checked': len(recipes), 'background_contexts_checked': len(contexts),
             'training_vectors_checked': 300, 'sectors': checked, 'maximum_errors': errors,
             'sector32_raw_fits_review': raw_check, 'historical_spatial_fit_audits_reused_by_hash': True,
             'source_order_identity_and_all_temporal_decisions_checked': True}
    # A local derived-only verification must not overwrite the sealed raw audit.
    if args.cache is not None:
        (out/'AUDIT.json').write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
