"""BY conditional local-bank injection/recovery; no import-time power access.

Synthetic excess is added AFTER the frozen real-data normalization. This is a
small, truth-local template-bank response experiment, not flux sensitivity,
a new observation, a full detector search, or complete ON/OFF qualification.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
import signal
import sys
from datetime import datetime, timezone

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
sys.dont_write_bytecode = True
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / 'work_bo/vendor/current/kernel_v.py'
CLASSIFIER = ROOT / 'work_bu/partial_search.py'
WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
CONFIG = {
    'q': 254, 'core_width_channels': 4096,
    'center_offsets': [1536, 2560], 'base_drift_indices': [314, 419, 524],
    'drift_grid_phases': [0.0, 0.5], 'carrier_phases': [0.0, 0.5],
    'nonzero_amplitudes': [1.0, 2.0, 4.0, 8.0, 16.0],
    'presence_patterns': ['ON_ONLY', 'ALL_FIVE'], 'zero_controls_per_geometry': 1,
    'bank_index_offsets': [-1, 0, 1], 'widths': list(WIDTHS), 'strides': list(STRIDES),
    'original_grid_rates': 839, 'original_max_abs_drift_hz_s': 4.0,
    'source_match_center_radius': 'width//2+2', 'source_match_max_rate_steps': 1.0,
    'rate_matching_tolerance_hz_s': 1e-12,
    'threshold_ON': 10.0, 'threshold_available_OFF': 5.0,
    'amplitude_units': 'Total normalized excess per integration, before final float32 cast',
    'injection_shape': 'Exposure integral of triangular channel deposition, unit area per integration',
    'independent_score_absolute_tolerance': 5e-5,
    'normalized_background_is_previously_exposed': True,
    'renormalization_after_injection': False,
    'new_observational_coverage': 0,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, obj):
    with Path(path).open('x') as stream:
        json.dump(obj, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def read_json(path):
    return json.loads(Path(path).read_text())


def load_components():
    spec = importlib.util.spec_from_file_location('by_unchanged_kernel', KERNEL)
    kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernel)
    source = ast.parse(CLASSIFIER.read_text())
    nodes = [node for node in source.body if isinstance(node, ast.FunctionDef)
             and node.name == 'classify_partial']
    require(len(nodes) == 1, 'Exact original classifier function required')
    namespace = {'np': np, 'require': require}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CLASSIFIER), 'exec'), namespace)
    return kernel, namespace['classify_partial']


def build_cases(plan):
    rates = np.linspace(-4, 4, 839, dtype=np.float64)
    step = float(rates[1]-rates[0]); cases = []
    for center in CONFIG['center_offsets']:
        for base in CONFIG['base_drift_indices']:
            for drift_phase in CONFIG['drift_grid_phases']:
                for carrier_phase in CONFIG['carrier_phases']:
                    geometry = len(cases)//11
                    common = {
                        'geometry': geometry, 'center_offset': center,
                        'base_drift_index': base, 'drift_grid_phase': drift_phase,
                        'carrier_phase': carrier_phase,
                        'true_center_native_at_scan0_midpoint': CONFIG['q']*4096+center+carrier_phase,
                        'true_drift_hz_s': float(rates[base] + drift_phase*step),
                        'bank_drift_indices': [base-1, base, base+1],
                    }
                    for amplitude, presence in [(0.0, 'ZERO_CONTROL')] + [
                            (a, p) for a in CONFIG['nonzero_amplitudes']
                            for p in CONFIG['presence_patterns']]:
                        cases.append(dict(common, case_index=len(cases), amplitude=amplitude,
                                          presence=presence))
    require(len(cases) == 264, 'Fixed case count differs')
    return cases


def triangle_cdf(z):
    """Stable antiderivative of max(1-|z|,0), normalized to [0,1]."""
    z = np.asarray(z, dtype=np.float64)
    out = np.zeros_like(z)
    negative = (z > -1) & (z < 0)
    positive = (z >= 0) & (z < 1)
    out[negative] = .5*(z[negative]+1)**2
    out[positive] = 1-.5*(1-z[positive])**2
    out[z >= 1] = 1
    return out


def unit_injection(case, scope, source_scope, record, shape):
    """Sparse exposure-integrated weights; each row has total weight one."""
    require(shape[0] == 16, 'Sixteen integrations required')
    gap = (scope['tref_midpoint_mjd']-source_scope['tref_midpoint_mjd'])*86400
    drift = case['true_drift_hz_s']; df = scope['df_hz']; dt = scope['dt_seconds']
    midpoint = case['true_center_native_at_scan0_midpoint'] + drift*gap/df - record['support_start']
    row_centers = midpoint + drift*(np.arange(16, dtype=np.float64)-7.5)*dt/df
    half_sweep = abs(drift*dt/df)/2
    sparse = []
    for row, center in enumerate(row_centers):
        lo, hi = center-half_sweep, center+half_sweep
        channels = np.arange(math.floor(lo)-1, math.ceil(hi)+2, dtype=np.int64)
        if half_sweep == 0:
            weights = np.maximum(1-np.abs(channels-center), 0)
        else:
            weights = (triangle_cdf(hi-channels)-triangle_cdf(lo-channels))/(hi-lo)
        selected = weights > 0
        channels, weights = channels[selected], weights[selected]
        require(len(channels) and channels.min() >= 0 and channels.max() < shape[1],
                'Injected support exceeds sealed normalized crop')
        require(np.isfinite(weights).all() and (weights >= 0).all()
                and abs(math.fsum(weights.tolist())-1) < 1e-10, 'Injection mass differs')
        sparse.append((channels, weights))
    return sparse


def inject(base, sparse, amplitude, active):
    require(base.dtype == np.float32 and np.isfinite(base).all(), 'Finite float32 background required')
    out = base.copy()
    if active and amplitude:
        for row, (channels, weights) in enumerate(sparse):
            out[row, channels] = (base[row, channels].astype(np.float64) + amplitude*weights).astype(np.float32)
    require(np.isfinite(out).all(), 'Nonfinite injected matrix')
    return out


def local_peak_mask(score, size):
    half = size//2
    padded = np.pad(score, (half, half), mode='edge')
    return score == np.lib.stride_tricks.sliding_window_view(padded, size).max(axis=1)


def validate(plan, freeze_path):
    require(plan['schema'] == 'SETI_BY_CONDITIONAL_INJECTION_V1', 'Wrong BY plan schema')
    require(plan['config'] == CONFIG, 'Prospective experiment configuration differs')
    require(np.__version__ == '2.3.5', 'Frozen NumPy runtime differs')
    require(len(plan['scans']) == len(plan['inputs']) == 5, 'Exactly five retained scans required')
    for index, (scope, record) in enumerate(zip(plan['scans'], plan['inputs'])):
        require(scope['scan'] == record['scan'] == index, 'Scan order differs')
        require(scope['role'] == ('ON' if index % 2 == 0 else 'OFF'), 'Role differs')
        require(scope['dt_seconds'] == 18.253611008 and scope['df_hz'] == -2.7939677238464355,
                'Source sampling differs')
        require(record['support_start'] == 253*4096 and record['support_stop'] == 256*4096,
                'Sealed BW support geometry differs')
        p = Path(record['path'])
        require(p.stat().st_size == record['bytes'] and sha(p) == record['sha256'], 'Input bytes differ')
    for path, digest in plan['source_sha256'].items():
        require(sha(path) == digest, 'Frozen source differs: '+path)
    input_manifest = ROOT / 'work_by/INPUTS_BY.json'
    required = [str(Path(__file__).resolve()), str(KERNEL), str(CLASSIFIER), str(input_manifest)]
    require(all(p in plan['source_sha256'] for p in required), 'Numerical dependency or input provenance not pinned')
    source_inputs = read_json(input_manifest)
    require(plan['inputs'] == source_inputs['inputs'] and
            plan['parent_closed_archive_sha256'] == source_inputs['parent_archive_sha256'],
            'Closed BW normalized input provenance differs')
    require(sha(plan['parent_BW_plan_path']) == plan['parent_BW_plan_sha256'], 'BW metadata plan differs')
    require(plan['scans'] == read_json(plan['parent_BW_plan_path'])['scans'],
            'Original BW scan identities, time/frequency geometry or header pins differ')
    freeze = read_json(freeze_path)
    require(isinstance(freeze.get('public_commit'), str) and len(freeze['public_commit']) == 40,
            'Public pre-analysis commit required')
    return freeze


def run(plan_path, freeze_path, out):
    plan_path, freeze_path, out = Path(plan_path), Path(freeze_path), Path(out)
    plan_hash = sha(plan_path); plan = read_json(plan_path)
    freeze = validate(plan, freeze_path)
    require(freeze['plan_sha256'] == plan_hash, 'Public freeze does not bind this plan')
    require(not out.exists(), 'Exclusive new output directory required; no retry')
    out.mkdir(parents=True)
    kernel, classifier = load_components()
    backgrounds = []
    for record in plan['inputs']:
        matrix = np.load(record['path'], allow_pickle=False)
        require(matrix.shape == (16, 12288) and matrix.dtype == np.float32
                and matrix.flags.c_contiguous and np.isfinite(matrix).all(), 'Normalized input format differs')
        backgrounds.append(matrix)
    cases = build_cases(plan)
    write_json(out/'CASES_BY.json', {'schema': 'SETI_BY_CASES_V1', 'config': CONFIG, 'cases': cases})
    rates = np.linspace(-4, 4, 839, dtype=np.float64)
    step = float(rates[1]-rates[0])
    times = (np.arange(16, dtype=np.float64)-7.5)*plan['scans'][0]['dt_seconds']
    offsets = np.rint(rates[:, None]*times[None, :]/plan['scans'][0]['df_hz']).astype(np.int32)
    calibration = np.empty((len(cases), 5, 3, 4, 2), dtype=np.float64)
    hashes = np.empty((len(cases), 5), dtype='<U64')
    seeds_all = []; center_all = []; max_all = []; valid_all = []; pred_all = []
    statuses_all = []; summaries = []; track_count = 0
    for case in cases:
        ci = case['case_index']; bank = case['bank_drift_indices']; case_seeds = []; matrices = []
        source_scope = plan['scans'][0]
        for scan, (scope, record, base) in enumerate(zip(plan['scans'], plan['inputs'], backgrounds)):
            sparse = unit_injection(case, scope, source_scope, record, base.shape)
            active = case['presence'] == 'ALL_FIVE' or (case['presence'] == 'ON_ONLY' and scan % 2 == 0)
            matrix = inject(base, sparse, case['amplitude'], active); matrices.append(matrix)
            hashes[ci, scan] = hashlib.sha256(matrix.tobytes(order='C')).hexdigest()
            start = CONFIG['q']*4096-record['support_start']; stop = start+4096
            for wi, (width, stride) in enumerate(zip(WIDTHS, STRIDES)):
                prepared = kernel.boxcars(matrix, width)
                centers = np.arange(start, stop, stride, dtype=np.int32)
                for bi, ri in enumerate(bank):
                    sums = kernel.tracks_grid(matrix, prepared, offsets[ri], start, stop, stride, width)[0]
                    median = float(np.median(sums)); scale = float(1.4826*np.median(np.abs(sums-median)))
                    require(math.isfinite(scale) and scale > 0, 'Invalid local-q MAD')
                    calibration[ci, scan, bi, wi] = [median, scale]
                    score = (sums-median)/scale; track_count += len(centers)
                    require(np.isfinite(score).all(), 'Nonfinite ESS')
                    if scan == 0 and abs(float(rates[ri])-case['true_drift_hz_s']) <= step+1e-12:
                        truth_center = case['true_center_native_at_scan0_midpoint']
                        eligible = (score >= 10) & local_peak_mask(score, max(3, 2*math.ceil(width/stride)+1))
                        eligible &= np.abs(centers+record['support_start']-truth_center) <= width//2+2
                        for selected in np.flatnonzero(eligible):
                            case_seeds.append({'case_index': ci, 'center_native': int(centers[selected])+record['support_start'],
                                               'drift_index': ri, 'width': width, 'ess': float(score[selected])})
        n = len(case_seeds)
        require(n <= 1000, 'Finite per-case matched seed cap reached')
        center_scores = np.full((n, 6), np.nan); maximum_scores = np.full((n, 6), np.nan)
        valid = np.zeros((n, 6), dtype=np.bool_); predicted = np.full((n, 6), -1, dtype=np.int32)
        for scan, (scope, record, matrix) in enumerate(zip(plan['scans'], plan['inputs'], matrices)):
            gap = (scope['tref_midpoint_mjd']-source_scope['tref_midpoint_mjd'])*86400
            radius = math.ceil(1+.5*step*abs(gap)/abs(scope['df_hz']))
            for wi, width in enumerate(WIDTHS):
                selected_seeds = [(i, seed) for i, seed in enumerate(case_seeds) if seed['width'] == width]
                if not selected_seeds:
                    continue
                prepared = kernel.boxcars(matrix, width)
                for i, seed in selected_seeds:
                    ri = seed['drift_index']; rate = rates[ri]
                    frequency = source_scope['fch1_mhz']+seed['center_native']*source_scope['df_hz']/1e6
                    projected_frequency = frequency+rate*gap/1e6
                    native = int(np.rint((projected_frequency-scope['fch1_mhz'])*1e6/scope['df_hz']))
                    center = native-record['support_start']; predicted[i, scan] = native
                    require(center+int(offsets[ri].min())-width//2-radius >= 0 and
                            center+int(offsets[ri].max())+width//2+radius < matrix.shape[1],
                            'Projected matched seed exceeds support')
                    requested = np.arange(center-radius, center+radius+1, dtype=np.int32)
                    sums = kernel.tracks_selected(matrix, prepared, offsets[ri], requested, width)[0]
                    median, scale = calibration[ci, scan, bank.index(ri), wi]
                    score = (sums-median)/scale
                    center_scores[i, scan] = score[radius]; maximum_scores[i, scan] = score.max(); valid[i, scan] = True
        if n:
            error = np.max(np.abs(center_scores[:, 0]-np.array([s['ess'] for s in case_seeds])))
            require(error == 0, 'Projected source score must equal catalog score exactly')
        classified = classifier(center_scores, maximum_scores, valid)
        for seed in case_seeds:
            seeds_all.append(seed)
        center_all.append(center_scores); max_all.append(maximum_scores); valid_all.append(valid); pred_all.append(predicted)
        statuses_all.append(classified['candidate_status'])
        counts = {label: int((classified['candidate_status'] == label).sum()) for label in
                  ('THREE_ON_FAIL', 'REJECTED_AVAILABLE_OFF', 'INCOMPLETE_OFF_COVERAGE', 'UNSUPPORTED')}
        summaries.append(dict(case, matched_source_seed_rows=n,
                              three_ON_recovered=bool(classified['three_ON_pass'].any()),
                              available_OFF_rejected=bool((classified['candidate_status'] == 'REJECTED_AVAILABLE_OFF').any()),
                              retained_partial=bool((classified['candidate_status'] == 'INCOMPLETE_OFF_COVERAGE').any()),
                              status_counts=counts))
        if (ci+1) % 11 == 0:
            print(json.dumps({'event': 'GEOMETRY_COMPLETE', 'geometry': case['geometry'],
                              'cases_completed': ci+1}), flush=True)
    require(track_count == 42577920, 'Fixed local bank computation count differs')
    arrays = {'calibration': calibration, 'injected_sha256': hashes,
              'center_scores': np.concatenate(center_all), 'max_scores': np.concatenate(max_all),
              'valid': np.concatenate(valid_all), 'predicted_native': np.concatenate(pred_all),
              'candidate_status': np.concatenate(statuses_all)}
    for key, dtype in [('case_index', np.int32), ('center_native', np.int32), ('drift_index', np.int32),
                       ('width', np.int16), ('ess', np.float64)]:
        arrays['seed_'+key] = np.asarray([seed[key] for seed in seeds_all], dtype=dtype)
    with (out/'RESULT_ARRAYS_BY.npz').open('xb') as stream:
        np.savez_compressed(stream, **arrays); stream.flush(); os.fsync(stream.fileno())
    groups = []
    for presence in ['ZERO_CONTROL', 'ON_ONLY', 'ALL_FIVE']:
        for amplitude in ([0.0] if presence == 'ZERO_CONTROL' else CONFIG['nonzero_amplitudes']):
            chosen = [x for x in summaries if x['presence'] == presence and x['amplitude'] == amplitude]
            groups.append({'presence': presence, 'amplitude': amplitude, 'geometries': len(chosen),
                           'source_recovered': sum(x['matched_source_seed_rows'] > 0 for x in chosen),
                           'three_ON_recovered': sum(x['three_ON_recovered'] for x in chosen),
                           'available_OFF_rejected': sum(x['available_OFF_rejected'] for x in chosen),
                           'retained_partial': sum(x['retained_partial'] for x in chosen)})
    validate(plan, freeze_path)
    require(sha(plan_path) == plan_hash, 'Frozen plan changed')
    summary = {'schema': 'SETI_BY_CONDITIONAL_RECOVERY_RESULT_V1',
               'status': 'PASS_CONDITIONAL_INJECTION_RECOVERY', 'plan_sha256': plan_hash,
               'public_freeze_commit': freeze['public_commit'], 'independent_audit_pending': True, 'cases': summaries, 'groups': groups,
               'case_count': len(cases), 'geometry_count': 24, 'matched_seed_rows': len(seeds_all),
               'computed_correlated_track_combinations': track_count,
               'full_cadence_status': 'NOT_EVALUABLE_MISSING_OFF5', 'new_SETI_searches': 0,
               'new_observational_coverage': 0, 'calibrated_astronomical_sensitivity': False,
               'arrays_sha256': sha(out/'RESULT_ARRAYS_BY.npz'),
               'limits': ['Previously exposed q254 backgrounds only; 24 deterministic geometries are not independent random trials.',
                          'Three rates selected around injection truth and scan0 seed matching; not blind or full-bank recovery.',
                          'Normalized-space excess is added after normalization; no calibration to Jy or end-to-end normalization response.',
                          'Ideal triangular channel response and exposure-integrated linear track; not a complete telescope channelizer model.',
                          'OFF5 remains absent; retained partial flags are not candidates or complete cadence detections.',
                          'One scenario may have both rejected and retained overlapping seed rows; group counts need not sum.'],
               'completed_utc': datetime.now(timezone.utc).isoformat()}
    write_json(out/'SUMMARY_BY.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    def expired(signum, frame):
        raise TimeoutError('BY fixed 600-second scientific worker budget reached')
    signal.signal(signal.SIGALRM, expired); signal.alarm(600)
    result = run(args.plan, args.freeze, args.out)
    signal.alarm(0)
    print(json.dumps({'status': result['status'], 'cases': result['case_count'],
                      'matched_seed_rows': result['matched_seed_rows']}), flush=True)
