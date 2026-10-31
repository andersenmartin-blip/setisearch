"""Independent BY local injection/recovery audit; no production imports.

Only a public frozen plan may authorize retained observation array reads.
Injection uses piecewise trapezoid integration, while production uses a CDF.
Track vectors use direct element additions; forced tracks use math.fsum.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import signal
import time
from datetime import datetime, timezone
import numpy as np

WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
SCORE_TOLERANCE = 5e-5


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    def bad(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_constant=bad)


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def triangle(x):
    return max(0.0, 1.0 - abs(float(x)))


def time_averaged_triangle(low, high, channel):
    """Integrate a linear spline by its breakpoints, independently of a CDF."""
    require(high >= low, 'Reversed trajectory')
    if high == low:
        return triangle(low - channel)
    points = sorted({float(low), float(high)} |
                    {float(k) for k in (channel-1, channel, channel+1)
                     if low < k < high})
    area = math.fsum((b-a) * (triangle(a-channel)+triangle(b-channel)) / 2.0
                     for a, b in zip(points, points[1:]))
    return area / (high-low)


def independent_injection(base, amplitude, present, origin_channel,
                          rate, scan_gap_seconds, dt, df, support_start):
    result = base.copy()
    if not present or amplitude == 0:
        return result, {'row_mass_error': 0.0, 'changed_cells': 0}
    maximum_mass_error = 0.0
    changed = 0
    for row in range(16):
        midpoint = origin_channel + rate*(scan_gap_seconds+(row-7.5)*dt)/df
        distance = abs(rate*dt/df)/2.0
        low, high = midpoint-distance, midpoint+distance
        channels = range(math.floor(low)-1, math.ceil(high)+2)
        weights = [(channel, time_averaged_triangle(low, high, channel))
                   for channel in channels]
        maximum_mass_error = max(maximum_mass_error,
                                 abs(math.fsum(w for _, w in weights)-1.0))
        for channel, weight in weights:
            if not weight:
                continue
            column = channel-support_start
            require(0 <= column < base.shape[1], 'Injected track outside support')
            result[row, column] = np.float32(float(base[row, column]) +
                                             float(amplitude)*weight)
            changed += 1
    require(maximum_mass_error < 1e-10, 'Injection mass is not conserved')
    return result, {'row_mass_error': maximum_mass_error, 'changed_cells': changed}


def direct_vector(y, offsets, centers, width):
    require(centers.ndim == 1 and len(offsets) == 16, 'Wrong track geometry')
    half = width//2
    require(centers.min()+offsets.min()-half >= 0 and
            centers.max()+offsets.max()+half < y.shape[1], 'Track outside support')
    total = np.zeros(len(centers), dtype=np.float64)
    for row in range(16):
        for delta in range(-half, half+1):
            total += y[row, centers+int(offsets[row])+delta].astype(np.float64)
    return total


def scalar_sum(y, offsets, center, width):
    return math.fsum(float(y[row, center+int(offsets[row])+delta])
                     for row in range(16)
                     for delta in range(-(width//2), width//2+1))


def median_mad(values):
    # Python's sorted order statistics avoid using the production np.median.
    ordered = sorted(float(x) for x in values)
    n = len(ordered)
    median = (ordered[(n-1)//2]+ordered[n//2])/2.0
    deviations = sorted(abs(x-median) for x in ordered)
    scale = 1.4826*(deviations[(n-1)//2]+deviations[n//2])/2.0
    require(math.isfinite(scale) and scale > 0, 'Invalid independent MAD')
    return median, scale


def expected_cases():
    rates = np.linspace(-4, 4, 839, dtype=np.float64)
    step = float(rates[1]-rates[0])
    result = []
    geometry = 0
    for center in (1536, 2560):
        for rate_index in (314, 419, 524):
            for rate_phase in (0.0, 0.5):
                for channel_phase in (0.0, 0.5):
                    common = dict(geometry=geometry, center_offset=center,
                                  base_drift_index=rate_index,
                                  drift_grid_phase=rate_phase,
                                  carrier_phase=channel_phase,
                                  true_center_native_at_scan0_midpoint=254*4096+center+channel_phase,
                                  true_drift_hz_s=float(rates[rate_index]+rate_phase*step),
                                  bank_drift_indices=[rate_index-1, rate_index, rate_index+1])
                    settings = [(0.0, 'ZERO_CONTROL')]
                    for amplitude in (1.0, 2.0, 4.0, 8.0, 16.0):
                        settings.extend([(amplitude, 'ON_ONLY'), (amplitude, 'ALL_FIVE')])
                    for amplitude, presence in settings:
                        result.append(dict(common, case_index=len(result), amplitude=amplitude,
                                           presence=presence))
                    geometry += 1
    return result


def declared_cdf(value):
    """Exact declared CDF formula for byte reconstruction, separately checked."""
    if value <= -1:
        return 0.0
    if value < 0:
        return .5*(value+1)**2
    if value < 1:
        return 1-.5*(1-value)**2
    return 1.0


def audited_weights(case, scope, reference, record):
    gap = (scope['tref_midpoint_mjd']-reference['tref_midpoint_mjd'])*86400
    rate, df, dt = case['true_drift_hz_s'], scope['df_hz'], scope['dt_seconds']
    midpoint = case['true_center_native_at_scan0_midpoint']+rate*gap/df-record['support_start']
    row_centers = midpoint+rate*(np.arange(16, dtype=np.float64)-7.5)*dt/df
    half = abs(rate*dt/df)/2
    result = []
    maximum_error = 0.0
    mass_error = 0.0
    checked = 0
    for row, center in enumerate(row_centers):
        low, high = float(center-half), float(center+half)
        indices, values = [], []
        independent_center = (case['true_center_native_at_scan0_midpoint']+
                              rate*(gap+(row-7.5)*dt)/df-record['support_start'])
        require(abs(float(center)-independent_center) < 1e-8,
                'Independently ordered physical track geometry differs')
        for channel in range(math.floor(low)-1, math.ceil(high)+2):
            value = (triangle(float(center)-channel) if half == 0 else
                     (declared_cdf(high-channel)-declared_cdf(low-channel))/(high-low))
            independent = time_averaged_triangle(low, high, channel)
            error = abs(value-independent)
            require(error < 1e-12, 'CDF weight differs from independent exposure integral')
            maximum_error = max(maximum_error, error)
            checked += 1
            if value > 0:
                require(0 <= channel < 12288, 'Injection is outside support')
                indices.append(channel)
                values.append(value)
        mass_error = max(mass_error, abs(math.fsum(values)-1))
        require(mass_error < 1e-10, 'Exposure weight mass differs')
        result.append((np.asarray(indices, dtype=np.int64), np.asarray(values, dtype=np.float64)))
    return result, dict(weight_comparisons=checked, maximum_weight_error=maximum_error,
                        maximum_mass_error=mass_error)


def reconstructed_matrix(base, weights, amplitude, active):
    matrix = base.copy()
    if amplitude and active:
        for row, (columns, values) in enumerate(weights):
            # The declared single final cast is necessary for exact input-byte binding.
            matrix[row, columns] = (base[row, columns].astype(np.float64)+
                                    amplitude*values).astype(np.float32)
    return matrix


def is_local_peak(scores, position, radius):
    # Clipping the comparison interval is equivalent to edge padding for a maximum.
    return float(scores[position]) == max(float(x) for x in
                                          scores[max(0, position-radius):
                                                 min(len(scores), position+radius+1)])


def audit(plan_path, freeze_path, production, out):
    began = time.monotonic()
    plan_path, freeze_path, production, out = map(Path, (plan_path, freeze_path, production, out))
    plan, freeze = read(plan_path), read(freeze_path)
    ph = sha(plan_path)
    require(plan['schema'] == 'SETI_BY_CONDITIONAL_INJECTION_V1', 'Wrong plan family')
    require(freeze['plan_sha256'] == ph and len(freeze['public_commit']) == 40,
            'Public freeze does not bind this plan')
    require(np.__version__ == '2.3.5', 'Wrong NumPy version')
    require(len(plan['inputs']) == len(plan['scans']) == 5, 'Five scans required')
    parent = read(plan['parent_BW_plan_path'])
    require(sha(plan['parent_BW_plan_path']) == plan['parent_BW_plan_sha256'], 'BW plan bytes differ')
    keys = ('scan', 'archive_id', 'role', 'target', 'dt_seconds', 'df_hz',
            'fch1_mhz', 'tref_midpoint_mjd')
    for i, scope in enumerate(plan['scans']):
        require(all(scope[key] == parent['scans'][i][key] for key in keys),
                'BY scope differs from original authenticated BW geometry')
    bound = {str(plan_path): ph, str(freeze_path): sha(freeze_path)}
    bound[plan['parent_BW_plan_path']] = plan['parent_BW_plan_sha256']
    bound.update(plan['source_sha256'])
    require(str(Path(__file__).resolve()) in bound, 'Independent reviewer must be frozen')
    for record in plan['inputs']:
        require(Path(record['path']).stat().st_size == record['bytes'], 'Input size differs')
        require(record['support_start'] == 253*4096 and record['support_stop'] == 256*4096,
                'Input support differs')
        bound[record['path']] = record['sha256']
    for name in ('SUMMARY_BY.json', 'CASES_BY.json', 'RESULT_ARRAYS_BY.npz'):
        bound[str(production/name)] = sha(production/name)
    require(all(sha(path) == digest for path, digest in bound.items()), 'Bound bytes differ')
    require(not out.exists(), 'Exclusive audit output required; no retry')
    out.mkdir(parents=True)
    summary, saved_cases = read(production/'SUMMARY_BY.json'), read(production/'CASES_BY.json')
    cases = expected_cases()
    require(saved_cases['cases'] == cases and saved_cases['config'] == plan['config'], 'Cases differ')
    require(summary['status'] == 'PASS_CONDITIONAL_INJECTION_RECOVERY' and
            summary['plan_sha256'] == ph and summary['public_freeze_commit'] == freeze['public_commit'],
            'Production summary identity differs')
    require(summary['arrays_sha256'] == sha(production/'RESULT_ARRAYS_BY.npz'), 'Array binding differs')
    require(summary['case_count'] == 264 and summary['geometry_count'] == 24 and
            summary['computed_correlated_track_combinations'] == 42577920, 'Scope counts differ')
    require(summary['new_SETI_searches'] == summary['new_observational_coverage'] == 0 and
            summary['calibrated_astronomical_sensitivity'] is False and
            summary['full_cadence_status'] == 'NOT_EVALUABLE_MISSING_OFF5', 'Scientific claims differ')
    with np.load(production/'RESULT_ARRAYS_BY.npz', allow_pickle=False) as source:
        arrays = {name: source[name] for name in source.files}
    require(arrays['calibration'].shape == (264,5,3,4,2), 'Calibration shape differs')
    require(np.isfinite(arrays['calibration']).all() and
            (arrays['calibration'][...,1] > 0).all(), 'Invalid stored calibration')
    n = len(arrays['seed_case_index'])
    require(n == summary['matched_seed_rows'], 'Seed count differs')
    for key in ('center_scores', 'max_scores', 'valid', 'predicted_native'):
        require(arrays[key].shape == (n,6), 'Six-slot association required')
    require(np.isnan(arrays['center_scores'][:,5]).all() and
            np.isnan(arrays['max_scores'][:,5]).all() and
            not arrays['valid'][:,5].any() and
            (arrays['predicted_native'][:,5] == -1).all(), 'Missing OFF5 substituted')
    backgrounds = []
    for record in plan['inputs']:
        y = np.load(record['path'], allow_pickle=False)
        require(y.shape == (16,12288) and y.dtype == np.dtype('<f4') and
                np.isfinite(y).all(), 'Invalid background')
        backgrounds.append(y)
    rates = np.linspace(-4,4,839,dtype=np.float64)
    step = float(rates[1]-rates[0])
    dt, df = plan['scans'][0]['dt_seconds'], plan['scans'][0]['df_hz']
    offsets = {ri: np.asarray([round(float(rates[ri])*(row-7.5)*dt/df)
                              for row in range(16)], dtype=np.int32)
               for base in (314,419,524) for ri in (base-1,base,base+1)}
    expected_rows = []
    maximum_calibration_error = maximum_scalar_error = maximum_score_error = 0.0
    maximum_weight_error = maximum_mass_error = 0.0
    vector_count = scalar_count = injection_count = weight_count = computed_tracks = 0
    case_summaries = []
    weights_cache = {}
    global_cursor = 0
    for case in cases:
        ci = case['case_index']
        expected_seeds = []
        matrices = []
        local_calibration = np.empty((5,3,4,2), dtype=np.float64)
        for scan, (scope, record, base) in enumerate(zip(plan['scans'],plan['inputs'],backgrounds)):
            cache_key = case['geometry'], scan
            if cache_key not in weights_cache:
                weights_cache[cache_key] = audited_weights(case, scope, plan['scans'][0], record)
                detail = weights_cache[cache_key][1]
                weight_count += detail['weight_comparisons']
                maximum_weight_error = max(maximum_weight_error,detail['maximum_weight_error'])
                maximum_mass_error = max(maximum_mass_error,detail['maximum_mass_error'])
            weights = weights_cache[cache_key][0]
            active = case['presence'] == 'ALL_FIVE' or (case['presence'] == 'ON_ONLY' and scan in (0,2,4))
            y = reconstructed_matrix(base, weights, case['amplitude'], active)
            require(hashlib.sha256(y.tobytes(order='C')).hexdigest() == arrays['injected_sha256'][ci,scan],
                    'Independent declared-byte injection reconstruction differs')
            injection_count += 1
            matrices.append(y)
            for wi, (width, stride) in enumerate(zip(WIDTHS,STRIDES)):
                centers = np.arange(4096,8192,stride,dtype=np.int32)
                for bi, ri in enumerate(case['bank_drift_indices']):
                    sums = direct_vector(y,offsets[ri],centers,width)
                    median, scale = median_mad(sums)
                    local_calibration[scan,bi,wi] = median,scale
                    error = float(np.max(np.abs(local_calibration[scan,bi,wi]-
                                                 arrays['calibration'][ci,scan,bi,wi])))
                    require(error < SCORE_TOLERANCE, 'Independent calibration differs')
                    maximum_calibration_error = max(maximum_calibration_error,error)
                    vector_count += 1
                    computed_tracks += len(centers)
                    scores = (sums-median)/scale
                    # All truth-near possible catalog positions are independently inspected.
                    if scan == 0 and abs(float(rates[ri])-case['true_drift_hz_s']) <= step+1e-12:
                        near = np.flatnonzero(np.abs(centers+record['support_start']-
                                                    case['true_center_native_at_scan0_midpoint']) <= width//2+2)
                        radius = max(3,2*math.ceil(width/stride)+1)//2
                        for index in near:
                            if scores[index] >= 10 and is_local_peak(scores,int(index),radius):
                                expected_seeds.append((ci,int(centers[index])+record['support_start'],ri,width,float(scores[index])))
        indices = np.flatnonzero(arrays['seed_case_index'] == ci)
        require(indices.tolist() == list(range(global_cursor,global_cursor+len(expected_seeds))),
                'Seed case membership or ordering differs')
        counts = {key:0 for key in ('THREE_ON_FAIL','REJECTED_AVAILABLE_OFF','INCOMPLETE_OFF_COVERAGE','UNSUPPORTED')}
        for i, seed in zip(indices,expected_seeds):
            _,native_seed,ri,width,source_score = seed
            for key,value in [('case_index',ci),('center_native',native_seed),('drift_index',ri),('width',width)]:
                require(int(arrays['seed_'+key][i]) == value, 'Exact local peak seed differs')
            error = abs(float(arrays['seed_ess'][i])-source_score)
            require(error < SCORE_TOLERANCE, 'Source seed score differs')
            maximum_score_error = max(maximum_score_error,error)
            centers_scores, maxima = [], []
            for scan,(scope,record,y) in enumerate(zip(plan['scans'],plan['inputs'],matrices)):
                gap = (scope['tref_midpoint_mjd']-plan['scans'][0]['tref_midpoint_mjd'])*86400
                frequency = plan['scans'][0]['fch1_mhz']+native_seed*plan['scans'][0]['df_hz']/1e6
                projected = int(round((frequency+float(rates[ri])*gap/1e6-scope['fch1_mhz'])*1e6/scope['df_hz']))
                require(projected == int(arrays['predicted_native'][i,scan]), 'Seed projection differs')
                radius = math.ceil(1+.5*step*abs(gap)/abs(scope['df_hz']))
                center = projected-record['support_start']
                bi,wi = case['bank_drift_indices'].index(ri),WIDTHS.index(width)
                median,scale = local_calibration[scan,bi,wi]
                forced = []
                forced_sums = []
                for channel in range(center-radius,center+radius+1):
                    value = scalar_sum(y,offsets[ri],channel,width)
                    forced_sums.append(value)
                    forced.append((value-median)/scale)
                    scalar_count += 1
                score,maximum = forced[radius],max(forced)
                require(bool(arrays['valid'][i,scan]), 'Supported forced slot marked invalid')
                saved_median,saved_scale = arrays['calibration'][ci,scan,bi,wi]
                sum_error = max(abs(forced_sums[radius]-(float(arrays['center_scores'][i,scan])*saved_scale+saved_median)),
                                abs(max(forced_sums)-(float(arrays['max_scores'][i,scan])*saved_scale+saved_median)))
                require(sum_error < SCORE_TOLERANCE, 'Scalar sums differ from saved center/maximum score')
                maximum_scalar_error = max(maximum_scalar_error,sum_error)
                error = max(abs(score-float(arrays['center_scores'][i,scan])),
                            abs(maximum-float(arrays['max_scores'][i,scan])))
                require(error < SCORE_TOLERANCE, 'Independent scalar forced scores differ')
                maximum_score_error = max(maximum_score_error,error)
                centers_scores.append(score);maxima.append(maximum)
            on = all(centers_scores[s] >= 10 for s in (0,2,4))
            off = any(maxima[s] >= 5 for s in (1,3))
            label = ('THREE_ON_FAIL' if not on else
                     'REJECTED_AVAILABLE_OFF' if off else 'INCOMPLETE_OFF_COVERAGE')
            require(str(arrays['candidate_status'][i]) == label, 'Independent classification differs')
            counts[label] += 1
        global_cursor += len(expected_seeds)
        expected = dict(case,matched_source_seed_rows=len(expected_seeds),
                        three_ON_recovered=bool(counts['REJECTED_AVAILABLE_OFF']+counts['INCOMPLETE_OFF_COVERAGE']),
                        available_OFF_rejected=bool(counts['REJECTED_AVAILABLE_OFF']),
                        retained_partial=bool(counts['INCOMPLETE_OFF_COVERAGE']),status_counts=counts)
        require(summary['cases'][ci] == expected, 'Per-case summary differs')
        case_summaries.append(expected)
        if (ci+1)%11 == 0:
            print(json.dumps({'event':'INDEPENDENT_GEOMETRY_COMPLETE','geometry':case['geometry'],
                              'cases_checked':ci+1}),flush=True)
    require(global_cursor == n and computed_tracks == 42577920 and vector_count == 15840,
            'Total independent scope differs')
    groups = []
    for presence in ('ZERO_CONTROL','ON_ONLY','ALL_FIVE'):
        for amplitude in ((0.0,) if presence == 'ZERO_CONTROL' else (1.0,2.0,4.0,8.0,16.0)):
            chosen = [case for case in case_summaries if case['presence'] == presence and case['amplitude'] == amplitude]
            groups.append(dict(presence=presence,amplitude=amplitude,geometries=len(chosen),
                               source_recovered=sum(x['matched_source_seed_rows'] > 0 for x in chosen),
                               three_ON_recovered=sum(x['three_ON_recovered'] for x in chosen),
                               available_OFF_rejected=sum(x['available_OFF_rejected'] for x in chosen),
                               retained_partial=sum(x['retained_partial'] for x in chosen)))
    require(groups == summary['groups'], 'Aggregate recovery groups differ')
    require(all(sha(path) == digest for path,digest in bound.items()), 'Bound bytes changed during audit')
    result = dict(schema='SETI_BY_INDEPENDENT_INJECTION_REVIEW_V1',
                  status='PASS_INDEPENDENT_INJECTION_REVIEW',plan_sha256=ph,
                  reviewer_sha256=sha(__file__),production_summary_sha256=sha(production/'SUMMARY_BY.json'),
                  arrays_sha256=sha(production/'RESULT_ARRAYS_BY.npz'),
                  cases_checked=264,geometries_checked=24,injected_matrices_byte_verified=injection_count,
                  independent_exposure_weight_comparisons=weight_count,
                  maximum_exposure_weight_error=maximum_weight_error,
                  maximum_exposure_mass_error=maximum_mass_error,
                  complete_calibration_vectors_checked=vector_count,
                  calibration_track_sums_checked=computed_tracks,
                  matched_seeds_checked=n,forced_scalar_tracks_recomputed=scalar_count,
                  forced_center_and_maximum_slots_checked=n*5,
                  maximum_calibration_absolute_error=maximum_calibration_error,
                  maximum_scalar_absolute_error=maximum_scalar_error,
                  maximum_score_absolute_error=maximum_score_error,
                  groups=groups,all_bound_bytes_unchanged=True,
                  limits=['No production numerical imports: direct vector additions, Python order statistics and math.fsum forced tracks.',
                          'Declared CDF formula is independently implemented for exact injected bytes; every distinct weight also has an independent piecewise-trapezoid integral check.',
                          'NPY decoder, NumPy float storage and drift-grid construction remain shared primitives.',
                          'Conditional 24-geometry normalized-space experiment; not full-bank blind sensitivity, independent observations or complete cadence qualification.'],
                  wall_seconds=time.monotonic()-began,completed_utc=datetime.now(timezone.utc).isoformat())
    write(out/'REVIEW_BY.json',result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--freeze',required=True,type=Path)
    parser.add_argument('--production',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args = parser.parse_args()
    def expired(signum,frame):
        raise TimeoutError('BY fixed 600-second independent audit budget reached')
    signal.signal(signal.SIGALRM,expired);signal.alarm(600)
    result = audit(args.plan,args.freeze,args.production,args.out)
    signal.alarm(0)
    print(json.dumps({'status':result['status'],'cases':result['cases_checked'],
                      'matched_seeds':result['matched_seeds_checked']}),flush=True)
