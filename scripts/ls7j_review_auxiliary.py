#!/usr/bin/env python3
"""Independent LS7J audit using direct joint least squares and scalar geometry.

Does not import the new correction, response, extraction or summary code.
Reuses only the prior independent observation and pulse audit primitives.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular
from scipy.ndimage import convolve1d

from ls7i_review_background import observation
from ls7g_review import pulse

ROOT = Path(__file__).resolve().parents[1]
ERRORS = Counter()


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]


def close(x, y, name, rtol=1e-8, atol=1e-9):
    ERRORS[name] = max(ERRORS[name], float(np.max(abs(np.asarray(x)-np.asarray(y)))))
    np.testing.assert_allclose(x, y, rtol=rtol, atol=atol, err_msg=name)


def shifted(image, displacement, nearest):
    out = np.zeros_like(image, dtype=float)
    for y in range(11):
        for x in range(11):
            ry, rx = y-displacement[0], x-displacement[1]
            if nearest:
                ry, rx = max(0., min(10., ry)), max(0., min(10., rx))
            elif not (0 <= ry <= 10 and 0 <= rx <= 10):
                continue
            iy, ix = int(np.floor(ry)), int(np.floor(rx)); fy, fx = ry-iy, rx-ix
            out[y, x] = ((1-fy)*(1-fx)*image[iy, ix]+fy*(1-fx)*image[min(iy+1, 10), ix]
                         +(1-fy)*fx*image[iy, min(ix+1, 10)]+fy*fx*image[min(iy+1, 10), min(ix+1, 10)])
    return out


def footprint(reference, ap, displacement, blur):
    edge = [reference[y, x] for y in range(11) for x in range(11) if y in [0, 10] or x in [0, 10]]
    source = np.maximum(reference-np.median(edge), 0.)
    if blur:
        axis = np.arange(-int(4*blur+.5), int(4*blur+.5)+1)
        kernel = np.exp(-axis**2/(2*blur**2)); kernel /= kernel.sum()
        source = convolve1d(convolve1d(source, kernel, axis=0, mode='constant', cval=0.), kernel, axis=1, mode='constant', cval=0.)
    source = shifted(source, displacement, False)
    return source/source[ap].sum()


def metrics(expected, actual):
    n2 = sum(float(v*v) for v in expected)
    if n2 <= 0:
        return None
    return {'gain': sum(float(a*b) for a, b in zip(expected, actual))/n2,
            'relative_distortion': np.sqrt(sum(float((a-b)**2) for a, b in zip(expected, actual))/n2)}


def centroid(image, ap):
    pixels = list(zip(*np.where(ap)))
    total = sum(float(image[y, x]) for y, x in pixels)
    if total <= 0 or not np.isfinite(total):
        return None
    return np.array([sum(float(image[y, x])*y for y, x in pixels), sum(float(image[y, x])*x for y, x in pixels)])/total


def raw_check(cache, auxiliary, raw, sources):
    from astropy.io import fits
    mapping = {'position_yx': ['POS_CORR2', 'POS_CORR1'], 'moment_centroid_yx': ['MOM_CENTR2', 'MOM_CENTR1'],
               'moment_error_yx': ['MOM_CENTR2_ERR', 'MOM_CENTR1_ERR'], 'psf_centroid_yx': ['PSF_CENTR2', 'PSF_CENTR1'],
               'psf_error_yx': ['PSF_CENTR2_ERR', 'PSF_CENTR1_ERR'], 'sap_background': ['SAP_BKG'], 'sap_background_error': ['SAP_BKG_ERR']}
    checked = 0
    for source in sources:
        sector = source['sector']; path = cache/source['name']; data = auxiliary[sector]
        assert path.stat().st_size == source['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        with fits.open(path, memmap=False) as hdus:
            table = hdus[1].data
            assert len(table) == source['rows']
            lookup = {int(c): i for i, c in enumerate(table['CADENCENO'])}
            assert len(lookup) == len(table)
            index = np.array([[lookup[int(c)] for c in row] for row in raw[sector]['context_cadence']])
            np.testing.assert_array_equal(index, raw[sector]['anchors'][:, None]+np.arange(-200, 201))
            for name, column in [('cadence', 'CADENCENO'), ('time', 'TIME'), ('quality', 'QUALITY')]:
                np.testing.assert_array_equal(data[name], table[column][index])
            np.testing.assert_array_equal(data['anchors'], raw[sector]['anchors'])
            np.testing.assert_array_equal(raw[sector]['aperture'], (hdus['APERTURE'].data & 2) != 0)
            for name, columns in mapping.items():
                for j, column in enumerate(columns):
                    source_column = source['columns'][column]
                    assert source_column['present'] == (column in table.names)
                    array = data[name][:, :, j] if len(columns) == 2 else data[name]
                    if column in table.names:
                        np.testing.assert_array_equal(array, np.asarray(table[column], dtype=float)[index])
                        assert source_column['unit'] == hdus[1].columns[column].unit
                        assert source_column['format'] == hdus[1].columns[column].format
                    else:
                        assert np.all(np.isnan(array))
                    assert source_column['finite_context_values'] == int(np.isfinite(array).sum())
                    assert source_column['finite_per_background'] == np.isfinite(array).sum(axis=1).tolist()
                    assert source_column['context_values'] == 4010
                    checked += array.size
            for key, value in source['metadata'].items():
                assert value == hdus[0].header.get(key, hdus[1].header.get(key))
    return {'passed': True, 'raw_products': 2, 'context_rows': 8020, 'auxiliary_values_checked': checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7j_auxiliary')
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args(); out = args.output
    cfg = read(ROOT/'config/ls7j_auxiliary.json')
    for path, expected in cfg['input_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected
    for base, name in cfg['preserve_manifests']+[['.', 'LS7J_FREEZE.sha256']]:
        for line in (ROOT/base/name).read_text().splitlines():
            expected, path = line.split(maxsplit=1)
            assert hashlib.sha256((ROOT/base/path.strip()).read_bytes()).hexdigest() == expected
    raw, auxiliary = {}, {}
    for d in read(ROOT/'results_ls7i_inputs/datasets.json'):
        with np.load(ROOT/d['contexts'], allow_pickle=False) as archive:
            raw[d['sector']] = {k: archive[k] for k in archive.files}
        with np.load(out/f'auxiliary_s{d["sector"]:03d}.npz', allow_pickle=False) as archive:
            auxiliary[d['sector']] = {k: archive[k] for k in archive.files}
    summary, sources, baselines = [read(out/name) for name in ['summary.json', 'sources.json', 'baselines.json']]
    for source in sources:
        for key, val in cfg['products'][str(source['sector'])].items():
            assert source[key] == val
    raw_audit = raw_check(args.cache, auxiliary, raw, sources) if args.cache else None
    baseline_map = {r['fold_id']: r for r in baselines}
    old_native = rows(ROOT/'results_ls7i_background/native_windows.jsonl.gz')
    old_folds = {r['fold_id']: r for r in rows(ROOT/'results_ls7i_background/folds.jsonl.gz')}
    old_regressions = {r['model_id']: r for r in rows(ROOT/'results_ls7i_background/regressions.jsonl.gz')}
    assert len(baselines) == len(baseline_map) == 60
    for b in baselines:
        f = old_folds[b['fold_id']]; r = old_regressions[f['model_id']]
        assert b['mean'] == r['y_mean'] and b['covariance'] == f['methods']['static']['covariance']
        assert r['excluded_anchors'] == [b['excluded_anchor']] and b['excluded_anchor'] not in r['training_anchors']
        assert b['sector'] == r['sector'] and b['width'] == r['width'] and len(r['training_anchors']) == 9
    frames, native, responses = [rows(out/name) for name in ['frames.jsonl.gz', 'native_windows.jsonl.gz', 'responses.jsonl.gz']]
    frame_map = {r['frame_id']: r for r in frames}
    assert len(frames) == len(frame_map) == summary['spatial_frames']
    expected_keys = {f's{r["sector"]:03d}/a{r["anchor"]:02d}/s{r["start"]}/e{r["stop"]}' for r in old_native}
    recipes = [{**r, 'cohort': 'historical'} for r in rows(ROOT/'results_ls7i_inputs/trial_recipes.jsonl.gz')]
    recipes += rows(ROOT/'results_ls7i_background/supplement_recipes.jsonl.gz')
    expected_keys |= {f's{r["sector"]:03d}/a{r["anchor"]:02d}/s{r["best"]["start"]}/e{r["best"]["stop"]}' for r in recipes}
    assert set(frame_map) == expected_keys
    operators, motions, designs = {}, {}, {}
    joint_columns = 0
    for i, f in enumerate(frames):
        d = raw[f['sector']]; ap = d['aperture']; outside = ~ap; lo, hi, a = f['start'], f['stop'], f['anchor']
        cube = d['native'][a]
        _, _, scale, reference = observation(cube, ap, lo, hi)
        close(reference, f['reference'], 'reference'); close(scale, f['sigma'], 'local_sigma')
        close(cube[lo:hi].mean(axis=0)-reference, f['native_delta'], 'native_delta')
        close(cube[lo:hi].mean(axis=0), f['native_event_image'], 'native_event_image')
        differences = []
        for start, stop in [(lo-60, lo-5), (hi+5, hi+60)]:
            differences += [(cube[j+1]-cube[j])[outside] for j in range(start, stop-1)]
        differences = np.array(differences)
        sigma = 1.482602218505602*np.median(abs(differences-np.median(differences, axis=0)), axis=0)/np.sqrt(2.)
        variance = sigma**2; floor = 1e-6*np.median(variance[variance > 0]); sigma = np.sqrt(np.maximum(variance, floor))
        close(sigma, f['outside_noise'], 'outside_noise'); close(floor, f['outside_variance_floor'], 'noise_floor')
        assert f['floored_pixels'] == int(np.sum(variance < floor))
        plane = np.array([[[1., (y-5.)/5., (x-5.)/5.] for x in range(11)] for y in range(11)])
        np.testing.assert_array_equal(plane, f['plane'])
        profiles = np.array([footprint(reference, ap, s, 0.) for s in cfg['protected_shifts_yx']])
        close(profiles, f['profiles'], 'protected_profiles')
        weighted = profiles[:, outside].T/sigma[:, None]
        u, singular, _ = np.linalg.svd(weighted, full_matrices=False)
        rank = int(sum(singular > 1e-10*singular[0])) if singular[0] > 0 else 0
        assert rank == f['protected_rank']; close(singular, f['protected_singular_values'], 'protected_singular_values')
        pmat = plane[outside]/sigma[:, None]; q = u[:, :rank]
        projected = pmat-q@(q.T@pmat)
        values = np.linalg.svd(projected, compute_uv=False)
        plane_rank = int(sum(values > 1e-10*values[0])) if values[0] > 0 else 0
        condition = values[0]/values[-1] if values[-1] > 0 else None
        valid = plane_rank == 3 and condition is not None and condition <= 1e8
        assert plane_rank == f['plane_rank'] and valid == f['valid']
        close(values, f['plane_singular_values'], 'plane_singular_values')
        if condition is None:
            assert f['plane_condition'] is None
        else:
            close(condition, f['plane_condition'], 'plane_condition')
        # Independently solve the simultaneous source + plane model, not the
        # evaluator's projected-plane pseudoinverse. Use all unit input columns
        # to verify the entire linear response operator, for arbitrary events.
        design = np.column_stack([q, pmat]); designs[f['frame_id']] = (design, sigma)
        if valid:
            coef = np.linalg.lstsq(design, np.diag(1./sigma), rcond=1e-12)[0]
            operator = coef[-3:]; close(operator, f['operator'], 'joint_operator', atol=2e-8)
            joint_columns += outside.sum()
            operators[f['frame_id']] = operator
            for p, recorded in zip(profiles, f['protected_basis_response']):
                expected = metrics(p[ap], (p-plane@(operator@p[outside]))[ap])
                for key in expected:
                    close(expected[key], recorded[key], 'basis_'+key, atol=2e-8)
        else:
            assert f['operator'] is None and all(r is None for r in f['protected_basis_response'])
            operators[f['frame_id']] = None
        pos = auxiliary[f['sector']]['position_yx'][a]
        selected = np.r_[lo-60:lo-5, lo:hi, hi+5:hi+60]
        if np.all(np.isfinite(pos[selected])):
            displacement = pos[lo:hi].mean(axis=0)-np.median(pos[np.r_[lo-60:lo-5, hi+5:hi+60]], axis=0)
            moved = shifted(reference, displacement, True); moved *= reference.sum()/moved.sum()
            image = moved-reference; close(image, f['motion_image'], 'motion_image', atol=1e-8)
            close(displacement, f['motion_displacement_yx'], 'motion_yx')
        else:
            image = None; assert f['motion_image'] is None and f['motion_displacement_yx'] is None
        motions[f['frame_id']] = image
        if (i+1) % 100 == 0:
            print(f'Audited outside-pixel operators and motion geometry: {i+1}/{len(frames)}', flush=True)
    assert len(native) == summary['native_windows'] == 420
    assert [r['window_id'] for r in native] == [r['window_id'] for r in old_native]
    for r, old in zip(native, old_native):
        f = frame_map[r['frame_id']]; ap = raw[r['sector']]['aperture']; outside = ~ap
        assert [r[k] for k in ['sector', 'anchor', 'fold_id']] == [old[k] for k in ['sector', 'anchor', 'fold_id']]
        b = baseline_map[r['fold_id']]; delta = np.array(f['native_delta']); plane = np.array(f['plane']); operator = operators[f['frame_id']]
        preds = {'motion': motions[f['frame_id']], 'plane': None, 'combined': None}
        if operator is not None:
            preds['plane'] = plane@(operator@delta[outside])
            if preds['motion'] is not None:
                preds['combined'] = preds['motion']+plane@(operator@(delta-preds['motion'])[outside])
        y = delta[ap]/f['sigma']; close(y, r['normalized_response'], 'native_response')
        chol = np.linalg.cholesky(b['covariance']); one = solve_triangular(chol, np.ones(ap.sum()), lower=True)
        for method, correction in {'static': np.zeros((11, 11)), **preds}.items():
            if correction is None:
                assert r['energies'][method] is None and r['corrections_aperture'][method] is None
                continue
            residual = solve_triangular(chol, y-b['mean']-correction[ap]/f['sigma'], lower=True)
            residual -= one*np.dot(residual, one)/np.dot(one, one)
            close(residual@residual, r['energies'][method], 'native_energy', atol=2e-7)
            if method != 'static':
                close(correction[ap], r['corrections_aperture'][method], 'native_correction', atol=2e-8)
            if method in ['plane', 'combined']:
                source = delta if method == 'plane' else delta-preds['motion']
                design, noise = designs[f['frame_id']]
                beta = np.linalg.lstsq(design, source[outside]/noise, rcond=1e-12)[0][-3:]
                close(beta, r['plane_coefficients'][method], 'native_coefficients', atol=2e-8)
        close(r['energies']['static'], old['energies']['static'], 'reused_static_energy')
    # Retain all old cohorts and separately reconstruct every new full-stamp
    # profile. The injection footprint comes from the whole native context;
    # the protected inference footprint was independently built from sidebands.
    patterns = {r['pattern_id']: r for r in read(ROOT/'results_ls7i_inputs/patterns.json')+read(ROOT/'results_ls7i_background/supplement_patterns.json')}
    full_patterns = rows(out/'full_stamp_patterns.jsonl.gz'); full_recipes = rows(out/'full_stamp_recipes.jsonl.gz')
    assert len(full_patterns) == 200 and len(full_recipes) == 2400
    assert len({p['pattern_id'] for p in full_patterns}) == 200
    for p in full_patterns:
        d = raw[p['sector']]
        assert p['cohort'] in ['full_stamp', 'broadened_full_stamp']
        index = cfg['injected_shifts_yx'].index(p['shift_yx'])
        assert p['pattern_id'] == f's{p["sector"]:03d}/a{p["anchor"]:02d}/{p["cohort"]}/shift{index}'
        assert p['blur_sigma'] == (0. if p['cohort'] == 'full_stamp' else .5)
        expected = footprint(np.median(d['native'][p['anchor']], axis=0), d['aperture'], p['shift_yx'], p['blur_sigma'])
        close(expected, p['vector'], 'injection_footprint', atol=1e-12)
        close(expected[~d['aperture']].sum(), p['outside_to_aperture_flux_ratio'], 'outside_flux_ratio')
        patterns[p['pattern_id']] = p
    parent_map = {r['case_id']: r for r in recipes}
    expected_full_ids = {r['case_id']+'/auxiliary/'+cohort+f'/shift{i}' for r in recipes
                         if r['suite'] == 'base' and r['kind'] == 'stellar' and r['target_score'] is not None
                         for cohort in ['full_stamp', 'broadened_full_stamp'] for i in range(5)}
    assert {r['case_id'] for r in full_recipes} == expected_full_ids
    for r in full_recipes:
        parent = parent_map[r['parent_case_id']]
        for key in ['sector', 'anchor', 'best', 'native_best', 'phase_seconds', 'shape', 'target_score', 'pattern_scale', 'residual', 'sign']:
            assert r[key] == parent[key]
        index = cfg['injected_shifts_yx'].index(r['shift_yx'])
        assert r['case_id'] == parent['case_id']+'/auxiliary/'+r['cohort']+f'/shift{index}'
        assert r['suite'] == 'full_stamp_response' and r['kind'] == ('stellar' if index == 0 else 'off_profile')
        assert r['pattern_id'] == f's{r["sector"]:03d}/a{r["anchor"]:02d}/{r["cohort"]}/shift{index}'
        assert all(r[field] is None for field in ['source_ledger', 'source_row', 'source_trial_id', 'source_suite', 'source_model_id'])
    recipes += full_recipes
    assert len(recipes) == len(responses) == len({r['case_id'] for r in responses}) == summary['response_rows'] == 9480
    for i, (r, recipe) in enumerate(zip(responses, recipes)):
        for key in ['case_id', 'sector', 'anchor', 'cohort', 'suite', 'kind', 'shape', 'phase_seconds', 'target_score', 'amplitude_fraction', 'shift_yx', 'pattern_id', 'pattern_scale', 'residual']:
            assert r[key] == recipe[key]
        assert r['parent_case_id'] == recipe.get('parent_case_id')
        f = frame_map[r['frame_id']]; d = raw[r['sector']]; a = r['anchor']; ap = d['aperture']; outside = ~ap
        lo, hi = recipe['best']['start'], recipe['best']['stop']
        assert [f[k] for k in ['sector', 'anchor', 'start', 'stop']] == [r['sector'], a, lo, hi]
        pv, _ = pulse(d['seconds'][a], recipe['phase_seconds'], recipe['shape'])
        addition = (recipe['pattern_scale']*pv)[:, None, None]*np.array(patterns[r['pattern_id']]['vector'])
        residual = np.zeros_like(addition)
        if recipe['residual'] is not None:
            extra = recipe['residual']; y, x = extra['pixel_yx']; residual[extra['start']:extra['stop'], y, x] = extra['amplitude_e_per_s']
        np.testing.assert_array_equal(addition[np.r_[lo-60:lo-5, hi+5:hi+60]], 0.)
        np.testing.assert_array_equal(residual[np.r_[lo-60:lo-5, hi+5:hi+60]], 0.)
        signal, extra = addition[lo:hi].mean(axis=0), residual[lo:hi].mean(axis=0)
        close(signal[ap], r['signal_addition_aperture'], 'signal_addition')
        close(extra[ap], r['residual_addition_aperture'], 'residual_addition')
        # Verify the actual injected cube's event difference as well as the
        # linear response, without relying on a median-additivity assumption.
        injected = d['native'][a]+addition+residual
        observed = injected[lo:hi].mean(axis=0)-np.array(f['reference'])
        close(observed, np.array(f['native_delta'])+signal+extra, 'observed_event', atol=1e-8)
        operator = operators[f['frame_id']]; plane = np.array(f['plane'])
        assert r['operator_valid'] == f['valid'] and r['motion_available'] == (motions[f['frame_id']] is not None)
        for method in ['plane', 'combined']:
            if operator is None or (method == 'combined' and motions[f['frame_id']] is None):
                assert r['response'][method] is None; continue
            pulse_response = (signal-plane@(operator@signal[outside]))[ap]
            total_response = (signal+extra-plane@(operator@(signal+extra)[outside]))[ap]
            close(pulse_response, r['response'][method]['pulse_transfer'], 'pulse_transfer', atol=2e-8)
            close(total_response, r['response'][method]['whole_addition_transfer'], 'whole_transfer', atol=2e-8)
            mm = metrics(signal[ap], pulse_response)
            if mm is None:
                assert r['response'][method]['pulse_metrics'] is None
            else:
                for key, value in mm.items():
                    close(value, r['response'][method]['pulse_metrics'][key], 'response_'+key, atol=2e-8)
            image = np.zeros((11, 11)) if method == 'plane' else motions[f['frame_id']]
            design, noise = designs[f['frame_id']]
            beta = np.linalg.lstsq(design, (observed-image)[outside]/noise, rcond=1e-12)[0][-3:]
            close(beta, r['response'][method]['plane_coefficients'], 'direct_case_coefficients', atol=2e-8)
        first = centroid(np.array(f['native_event_image'])+extra, ap)
        second = centroid(np.array(f['native_event_image'])+extra+signal, ap)
        if first is None or second is None:
            assert r['proxy_centroid_pulse_shift_yx'] is None
        else:
            close(second-first, r['proxy_centroid_pulse_shift_yx'], 'proxy_centroid_shift')
        if (i+1) % 1500 == 0:
            print(f'Audited actual cubes and protected/mismatched pulse response: {i+1}/9480', flush=True)
    # Independent scalar recount, including explicit missing-data denominators.
    sector_pass = []
    for sector in [29, 32]:
        ss = summary['sectors'][str(sector)]
        nn = [r for r in native if r['sector'] == sector]; rr = [r for r in responses if r['sector'] == sector]
        ff = [r for r in frames if r['sector'] == sector]
        assert len(nn) == ss['native_windows'] == 210 and len(rr) == ss['response_trials'] == 4740
        assert ss['cohorts'] == dict(Counter(r['cohort'] for r in rr))
        for method in ['static', 'motion', 'plane', 'combined']:
            mm = ss['methods'][method]; paired = [r for r in nn if r['energies'][method] is not None]
            assert mm['available_windows'] == len(paired)
            total = sum(r['energies'][method] for r in paired); baseline = sum(r['energies']['static'] for r in paired)
            close(total, mm['energy'], 'sector_energy'); close(baseline, mm['paired_static_energy'], 'sector_baseline')
            ratio = total/baseline if baseline > 0 else None
            if ratio is None:
                assert mm['ratio'] is None
            else:
                close(ratio, mm['ratio'], 'sector_ratio')
            ratios = []
            assert len(mm['per_background']) == 10
            for a, bg in enumerate(mm['per_background']):
                selected = [r for r in paired if r['anchor'] == a]
                assert bg['anchor'] == a and bg['available_windows'] == len(selected)
                e = sum(r['energies'][method] for r in selected); b = sum(r['energies']['static'] for r in selected)
                value = e/b if b > 0 else None; ratios.append(value)
                close(e, bg['energy'], 'background_energy'); close(b, bg['paired_static_energy'], 'background_baseline')
                if value is None:
                    assert bg['ratio'] is None
                else:
                    close(value, bg['ratio'], 'background_ratio')
            gates = {'all_210_windows_available': len(paired) == 210, 'aggregate_not_increased': ratio is not None and ratio <= 1.,
                     'six_backgrounds_improve': sum(r is not None and r < 1 for r in ratios) >= 6,
                     'no_background_more_than_doubled': all(r is not None and r <= 2 for r in ratios)}
            assert gates == mm['gates'] and all(gates.values()) == mm['pass']
        for group, protection in ss['protection'].items():
            selected = ([r for r in rr if r['cohort'] in ['historical', 'sector32_shape_supplement'] and r['kind'] in ['stellar', 'off_profile']]
                        if group == 'aperture_limited_historical' else [r for r in rr if r['cohort'] == group])
            valid = [r for r in selected if r['response']['combined'] is not None and r['response']['combined']['pulse_metrics'] is not None]
            limit = {'aperture_limited_historical': 1e-10, 'full_stamp': .01, 'broadened_full_stamp': .05}[group]
            assert protection['trials'] == len(selected) == (1320 if group == 'aperture_limited_historical' else 600)
            assert protection['available'] == len(valid) and protection['distortion_limit'] == limit
            failed = [r['case_id'] for r in selected if r['response']['combined'] is None or r['response']['combined']['pulse_metrics'] is None
                      or r['response']['combined']['pulse_metrics']['relative_distortion'] > limit]
            assert failed == protection['failed_case_ids'] and (not failed) == protection['pass']
            if valid:
                ms = [r['response']['combined']['pulse_metrics'] for r in valid]
                close(max(m['relative_distortion'] for m in ms), protection['maximum_distortion'], 'maximum_distortion')
                close(min(m['gain'] for m in ms), protection['minimum_gain'], 'minimum_gain')
                close(max(m['gain'] for m in ms), protection['maximum_gain'], 'maximum_gain')
        errors = [r['relative_distortion'] for f in ff for r in f['protected_basis_response'] if r is not None]
        maximum = max(errors) if errors else None
        assert ss['spatial_frames'] == len(ff) and ss['valid_operators'] == sum(f['valid'] for f in ff)
        assert ss['available_motion_frames'] == sum(f['motion_image'] is not None for f in ff)
        if maximum is not None:
            close(maximum, ss['protected_basis_max_distortion'], 'basis_maximum')
        operator_pass = all(f['valid'] for f in ff) and len(errors) == 9*len(ff) and maximum <= 1e-8
        assert operator_pass == ss['operator_gate_pass']
        passed = ss['methods']['combined']['pass'] and operator_pass and all(p['pass'] for p in ss['protection'].values())
        assert passed == ss['feasibility_pass']; sector_pass.append(passed)
    assert all(sector_pass) == summary['feasibility_pass']
    assert summary['historical_recipe_rows'] == 6720 and summary['prior_shape_supplement_rows'] == 360
    assert summary['new_full_stamp_response_rows'] == 2400 and summary['backgrounds'] == 20
    assert summary['added_observing_days'] == summary['new_detector_decisions'] == 0
    assert summary['freeze_sha256'] == hashlib.sha256((ROOT/'LS7J_FREEZE.sha256').read_bytes()).hexdigest()
    audit = {'passed': True, 'raw_auxiliary_review': raw_audit, 'native_windows': len(native), 'response_rows': len(responses),
             'new_full_stamp_rows': 2400, 'protected_operator_frames': len(frames), 'joint_unit_input_columns': int(joint_columns),
             'independent_geometry': 'scalar bilinear shifts and explicit Gaussian kernels',
             'independent_operator': 'simultaneous source and plane least squares on every unit input',
             'maximum_errors': dict(ERRORS), 'feasibility_pass': summary['feasibility_pass'],
             'prior_input_and_baseline_audits_reused_by_hash': True}
    destination = out/('AUDIT_RECHECK.json' if (out/'AUDIT.json').exists() else 'AUDIT.json')
    destination.write_text(json.dumps(audit, indent=2, allow_nan=False)+'\n')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
