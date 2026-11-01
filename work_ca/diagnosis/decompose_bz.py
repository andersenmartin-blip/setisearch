"""CA posthoc diagnostic of closed BZ outputs; never reruns the detector bank.

Select each A=8 ON_ONLY case's already stored seed maximizing its minimum
stored ON score, then decompose its three scores using the existing local
median/MAD. No template, threshold or calibration is fitted here. A separate
frequency reflection check exercises sparse injections and integer tracks.
"""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import math
import sys
import zipfile

sys.dont_write_bytecode = True
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'SCORE_DECOMPOSITION_CA.json'
ON = (0, 2, 4)
WIDTHS = (1, 3, 9, 33)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def read(path):
    return json.loads(Path(path).read_text())

def track(matrix, offsets, center, width):
    half = width // 2
    require(center + min(offsets) - half >= 0 and
            center + max(offsets) + half < matrix.shape[1], 'Out of support')
    return math.fsum(float(matrix[t, center + int(o) + j])
                     for t, o in enumerate(offsets)
                     for j in range(-half, half + 1))

def main():
    require(not OUT.exists(), 'Exclusive diagnostic output required')
    pins = {}
    def pin(path):
        path = Path(path)
        pins[str(path.relative_to(ROOT))] = sha(path)
        return path
    pin(Path(__file__))
    plan = read(pin(ROOT / 'work_bz/PLAN_BZ.json'))
    source = pin(ROOT / 'work_by/inject_recover.py')
    require(sha(source) == '8260c03c757dc36763f70cf0dd82b0b9553788f7cdca84d7d74636e6e962e0c8',
            'Injection source differs')
    spec = importlib.util.spec_from_file_location('ca_pinned_by', source)
    by = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(by)
    backgrounds = []
    for item in plan['inputs']:
        path = pin(ROOT / 'work_by/inputs' / Path(item['path']).name)
        require(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'],
                'Sealed normalized input differs')
        y = np.load(path, allow_pickle=False)
        require(y.shape == (16, 12288) and y.dtype == np.float32 and np.isfinite(y).all(),
                'Bad background format')
        backgrounds.append(y)
    archive_path = pin(ROOT / 'work_bz/execution/production/EVIDENCE.zip')
    receipt = read(pin(ROOT / 'work_bz/execution/production/RESULT.json'))
    require(receipt['status'] == 'PASS' and receipt['actual_exit_code'] == 0 and
            sha(archive_path) == receipt['archive']['sha256'], 'Closed production not bound')
    with zipfile.ZipFile(archive_path) as z:
        manifest = json.loads(z.read('ARCHIVE_MANIFEST.json'))
        require(manifest['members'] == receipt['archive']['members'], 'Manifest differs')
        require(z.testzip() is None, 'Archive CRC error')
        for member in manifest['members']:
            b = z.read(member['path'])
            require(len(b) == member['bytes'] and hashlib.sha256(b).hexdigest() == member['sha256'],
                    'Archive member differs')
        cases = json.loads(z.read('outputs/CASES_BZ.json'))['cases']
        summary = json.loads(z.read('outputs/SUMMARY_BZ.json'))
        blob = z.read('outputs/RESULT_ARRAYS_BZ.npz')
        require(hashlib.sha256(blob).hexdigest() == summary['arrays_sha256'], 'Array binding differs')
        with np.load(io.BytesIO(blob), allow_pickle=False) as a:
            arrays = {k: a[k] for k in a.files}
    selected = [c for c in cases if c['amplitude'] == 8.0 and c['presence'] == 'ON_ONLY']
    require(len(selected) == 24, 'Unexpected selected case count')
    results = []
    errors = []
    mirrored_weight_errors = []
    mirrored_track_errors = []
    total_sparse_mirror_pairs = 0
    for case in selected:
        ci = case['case_index']
        rows = np.flatnonzero(arrays['seed_case_index'] == ci)
        value = {k: case[k] for k in ('case_index', 'geometry', 'base_drift_index',
                                      'center_offset', 'carrier_phase', 'drift_grid_phase',
                                      'true_drift_hz_s')}
        value['matched_seed_count'] = len(rows)
        sparse_by_scan = []
        # Reflection is an algebraic diagnostic on the exposed template model.
        # It is not a second astronomical test set or a detector rerun.
        for scan, (scope, item, bg) in enumerate(zip(plan['scans'], plan['inputs'], backgrounds)):
            sparse = by.unit_injection(case, scope, plan['scans'][0], item, bg.shape)
            sparse_by_scan.append(sparse)
            axis_sum = 2 * item['support_start'] + bg.shape[1] - 1
            reflected = dict(case,
                true_center_native_at_scan0_midpoint=axis_sum-case['true_center_native_at_scan0_midpoint'],
                true_drift_hz_s=-case['true_drift_hz_s'])
            mirror = by.unit_injection(reflected, scope, plan['scans'][0], item, bg.shape)
            for (channels, weights), (mc, mw) in zip(sparse, mirror):
                require(np.array_equal(bg.shape[1]-1-channels[::-1], mc), 'Reflected channel support differs')
                mirrored_weight_errors.append(float(np.max(np.abs(weights[::-1]-mw), initial=0)))
            total_sparse_mirror_pairs += 1
        if not len(rows):
            value['best_common_seed'] = None
            value['limitation'] = 'No source seed above threshold was stored; no substitute seed is invented.'
            results.append(value)
            continue
        min_score = arrays['center_scores'][rows][:, ON].min(axis=1)
        row = int(rows[int(np.argmax(min_score))])
        rate = float(arrays['seed_drift_hz_s'][row])
        ri = int(arrays['seed_refined_index'][row])
        width = int(arrays['seed_width'][row])
        wi = WIDTHS.index(width)
        value['best_common_seed'] = {'union_row': row, 'width': width,
            'center_native': int(arrays['seed_center_native'][row]),
            'refined_index': ri, 'drift_hz_s': rate,
            'minimum_ON_score': float(min_score.max()),
            'three_ON_recovered': bool(min_score.max() >= 10), 'scans': []}
        for scan in ON:
            scope = plan['scans'][scan]
            item = plan['inputs'][scan]
            bg = backgrounds[scan]
            sparse = sparse_by_scan[scan]
            injected = by.inject(bg, sparse, 8.0, True)
            require(hashlib.sha256(injected.tobytes()).hexdigest() == arrays['injected_sha256'][ci, scan],
                    'Reconstructed injected bytes differ')
            offsets = np.rint(rate * (np.arange(16)-7.5) * scope['dt_seconds'] / scope['df_hz']).astype(np.int32)
            native = int(arrays['predicted_native'][row, scan])
            center = native - item['support_start']
            median, scale = map(float, arrays['calibration'][ci, scan, ri, wi])
            raw = track(injected, offsets, center, width)
            raw_bg = track(bg, offsets, center, width)
            raw_excess = track(injected.astype(np.float64)-bg.astype(np.float64), offsets, center, width)
            score = (raw-median)/scale
            stored_score = float(arrays['center_scores'][row, scan])
            errors.append(abs(score-stored_score))
            require(abs(score-stored_score) < 1e-10 and abs(raw-raw_bg-raw_excess) < 1e-10,
                    'Scalar decomposition differs from stored score')
            half = width//2
            captured_weight = math.fsum(float(weight) for t, (channels, weights) in enumerate(sparse)
                for channel, weight in zip(channels, weights)
                if abs(int(channel)-(center+int(offsets[t]))) <= half)
            mirrored_track_errors.append(abs(raw_bg-track(bg[:, ::-1], -offsets, bg.shape[1]-1-center, width)))
            component = {'scan': scan, 'native_center': native, 'median_stored': median,
                'MAD_scale_stored': scale, 'stored_score': stored_score,
                'scalar_score': score, 'background_score_term': (raw_bg-median)/scale,
                'injected_excess_score_term': raw_excess/scale,
                'raw_background_sum': raw_bg, 'raw_injected_excess_sum': raw_excess,
                'captured_fraction_of_ideal_excess': captured_weight/16,
                'ideal_excess_sum_before_float32': 8*captured_weight,
                'float32_injection_rounding_delta': raw_excess-8*captured_weight,
                'exposure_sweep_channels': abs(case['true_drift_hz_s']*scope['dt_seconds']/scope['df_hz']),
                'passes_with_background_term_omitted': bool(raw_excess/scale >= 10),
                'passes_stored': bool(stored_score >= 10)}
            value['best_common_seed']['scans'].append(component)
        results.append(value)
    groups=[]
    for rate_index in (314,419,524):
        group=[v for v in results if v['base_drift_index']==rate_index]
        present=[v for v in group if v['best_common_seed'] is not None]
        components=[s for v in present for s in v['best_common_seed']['scans']]
        g={'base_drift_index':rate_index, 'geometries':len(group),
           'geometries_with_source_seed':len(present),
           'three_ON_recovered':sum(v['best_common_seed']['three_ON_recovered'] for v in present),
           'evaluated_selected_seed_ON_tracks':len(components)}
        if components:
            for key in ('background_score_term','injected_excess_score_term','captured_fraction_of_ideal_excess',
                        'MAD_scale_stored','float32_injection_rounding_delta'):
                a=np.array([s[key] for s in components])
                g[key]={'minimum':float(a.min()),'median':float(np.median(a)),'maximum':float(a.max())}
            g['failed_stored_tracks_with_excess_alone_at_least_10'] = sum(
                not s['passes_stored'] and s['passes_with_background_term_omitted'] for s in components)
            g['failed_stored_tracks'] = sum(not s['passes_stored'] for s in components)
        groups.append(g)
    require(max(mirrored_weight_errors, default=0) < 1e-9, 'Sparse reflection weight tolerance exceeded')
    require(max(mirrored_track_errors, default=0) < 1e-10, 'Track reflection tolerance exceeded')
    require(all(sha(ROOT/p)==h for p,h in pins.items()), 'Bound inputs changed')
    result={'schema':'SETI_CA_POSTHOC_STORED_SEED_SCORE_DECOMPOSITION_V1',
        'status':'PASS_POSTHOC_DECOMPOSITION_AND_REFLECTION_CHECK',
        'posthoc':True,'independent_validation':False,'new_observations':0,
        'new_detector_bank_searches':0,'recomputed_calibration_vectors':0,
        'input_sha256':pins,
        'selection':'A=8 ON_ONLY; among existing BZ factor8 seeds, maximize minimum stored ON center score; first stored row breaks ties.',
        'decomposition':'stored score = (background sum - stored median)/stored MAD + float32 injected excess sum/stored MAD',
        'geometries':24,'geometries_with_source_seed':sum(v['best_common_seed'] is not None for v in results),
        'scalar_score_decompositions':len(errors),'maximum_stored_score_absolute_error':max(errors),
        'reflection':{'sparse_geometry_scan_pairs':total_sparse_mirror_pairs,
            'sparse_time_rows':len(mirrored_weight_errors),
            'maximum_sparse_weight_absolute_error':max(mirrored_weight_errors),
            'integer_track_pairs':len(mirrored_track_errors),
            'maximum_integer_track_sum_absolute_error':max(mirrored_track_errors),
            'scope':'Frequency-reflected sparse template with opposite rate; integer track against reflected background with opposite integer offsets. Does not test every source-selection/projection branch.'},
        'groups':groups,'cases':results,
        'limits':['Posthoc selected paths on exposed backgrounds; group summaries are descriptive and affected by source selection.',
                  'Four no-source-seed cases have no stored best common path and are not decomposed.',
                  'Background-term removal is an algebraic counterfactual with stored med/MAD held fixed, not a calibrated new detector.',
                  'Frequency reflection checks template/track algebra only; it does not imply equal sensitivity on unreflected real backgrounds.',
                  'No new ON/OFF search, global false-alarm calibration, independent observations, Jy sensitivity or missing OFF5 qualification.']}
    OUT.parent.mkdir(exist_ok=True, parents=True)
    with OUT.open('x') as f: json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','scalar_score_decompositions','maximum_stored_score_absolute_error','reflection','groups')},indent=2))

if __name__ == '__main__':
    main()
