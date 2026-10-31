"""Independent BZ nested-grid audit; no production numerical imports.

Only a public frozen plan may authorize retained observation array reads.
BY audited baseline is hash-bound and reused; only new drift rates are rescored.
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


COARSE_POSITIONS = (0, 8, 16)
NEW_POSITIONS = tuple(i for i in range(17) if i not in COARSE_POSITIONS)
FACTORS = (1, 2, 4, 8)
LABELS = ('THREE_ON_FAIL', 'REJECTED_AVAILABLE_OFF', 'INCOMPLETE_OFF_COVERAGE', 'UNSUPPORTED')
METRICS = ('source_recovered', 'three_ON_recovered', 'available_OFF_rejected', 'retained_partial')


def nested_rates(base_index):
    """Scalar interval construction; coarse anchors are copied bit-exactly."""
    coarse = np.linspace(-4.0, 4.0, 839, dtype=np.float64)
    anchors = [float(coarse[base_index + delta]) for delta in (-1, 0, 1)]
    result = []
    for interval in (0, 1):
        start, stop = anchors[interval:interval+2]
        spacing = (stop-start)/8.0
        result.extend(start + j*spacing for j in range(8))
    result.append(anchors[-1])
    result[0], result[8], result[16] = anchors
    return np.asarray(result, dtype=np.float64)


def exact_array(left, right, label):
    require(left.dtype == right.dtype and left.shape == right.shape and
            left.tobytes(order='C') == right.tobytes(order='C'),
            'Byte-identical ' + label + ' required')


def case_flag(case, metric):
    return bool(case['matched_source_seed_rows']) if metric == 'source_recovered' else bool(case[metric])


def independent_groups(case_summaries):
    groups = []
    for presence in ('ZERO_CONTROL', 'ON_ONLY', 'ALL_FIVE'):
        for amplitude in ((0.0,) if presence == 'ZERO_CONTROL' else (1.0, 2.0, 4.0, 8.0, 16.0)):
            selected = [case for case in case_summaries
                        if case['presence'] == presence and case['amplitude'] == amplitude]
            group = dict(presence=presence, amplitude=amplitude, geometries=len(selected))
            group.update({key: sum(case_flag(case, key) for case in selected) for key in METRICS})
            group['both_retained_and_rejected'] = sum(case['retained_partial'] and case['available_OFF_rejected']
                                                     for case in selected)
            groups.append(group)
    return groups


def independently_classify(center_scores, max_scores, valid):
    if not all(bool(valid[s]) for s in range(5)):
        return 'UNSUPPORTED'
    if not all(float(center_scores[s]) >= 10.0 for s in (0, 2, 4)):
        return 'THREE_ON_FAIL'
    if any(float(max_scores[s]) >= 5.0 for s in (1, 3)):
        return 'REJECTED_AVAILABLE_OFF'
    return 'INCOMPLETE_OFF_COVERAGE'


def audit(plan_path, freeze_path, production, out):
    began = time.monotonic()
    plan_path, freeze_path, production, out = map(Path, (plan_path, freeze_path, production, out))
    plan, freeze = read(plan_path), read(freeze_path)
    ph = sha(plan_path)
    require(plan['schema'] == 'SETI_BZ_NESTED_DRIFT_GRID_V1', 'Wrong plan family')
    require(freeze['plan_sha256'] == ph and len(freeze['public_commit']) == 40 and
            all(c in '0123456789abcdef' for c in freeze['public_commit']) and
            freeze['exact_readback_verified'], 'Public freeze does not bind this plan')
    expected_config = dict(q=254,factors=[1,2,4,8],new_factors=[2,4,8],union_factor=8,
                           union_rates_per_case=17,new_rates_per_case=14,
                           coarse_anchor_refined_indices=[0,8,16],base_drift_indices=[314,419,524],
                           original_grid_rates=839,original_max_abs_drift_hz_s=4.0,
                           source_match_max_original_rate_steps=1.0,rate_match_tolerance_hz_s=1e-12,
                           refined_radius_used=False,kernel_widths=[1,3,9,33],kernel_strides=[1,1,2,8],
                           threshold_ON=10.0,threshold_available_OFF=5.0,case_count=264,geometry_count=24,
                           injected_matrices=1320,new_calibration_vectors=73920,reused_calibration_vectors=15840,
                           new_correlated_track_combinations=198696960,reused_baseline_track_combinations=42577920,
                           union_nominal_track_combinations=241274880,new_observations=False,new_SETI_searches=0,
                           calibrated_astronomical_sensitivity=False,method_selected_after_BY_results=True,
                           association_radius='ceil(1+0.5*ORIGINAL_rate_step*abs(scan_gap)/abs(df_hz))')
    require(all(plan['config'].get(key) == value for key,value in expected_config.items()),
            'Prospective numerical configuration differs')
    require(np.__version__ == '2.3.5', 'Wrong NumPy version')
    require(len(plan['inputs']) == len(plan['scans']) == 5, 'Exactly five real scans required')
    parent_path = plan['parent_BY_plan_path']
    require(sha(parent_path) == plan['parent_BY_plan_sha256'], 'Parent BY plan differs')
    parent = read(parent_path)
    require(parent['schema'] == 'SETI_BY_CONDITIONAL_INJECTION_V1', 'Wrong parent family')
    require(plan['scans'] == parent['scans'], 'Observational geometry differs from BY')
    bound = {str(plan_path): ph, str(freeze_path): sha(freeze_path), parent_path: sha(parent_path)}
    bound.update(plan['source_sha256'])
    require(str(Path(__file__).resolve()) in bound, 'Independent reviewer must be publicly frozen')
    for record, old in zip(plan['inputs'], parent['inputs']):
        require({key:value for key,value in record.items() if key != 'path'} ==
                {key:value for key,value in old.items() if key != 'path'}, 'Input provenance differs from BY')
        require(Path(record['path']).stat().st_size == record['bytes'], 'Input size differs')
        require(record['support_start'] == 253*4096 and record['support_stop'] == 256*4096,
                'Input support differs')
        bound[record['path']] = record['sha256']
    baseline = plan['baseline']
    for name in ('summary', 'arrays', 'cases', 'review'):
        bound[baseline[name+'_path']] = baseline[name+'_sha256']
    for name in ('SUMMARY_BZ.json', 'CASES_BZ.json', 'RESULT_ARRAYS_BZ.npz'):
        bound[str(production/name)] = sha(production/name)
    require(all(sha(path) == digest for path,digest in bound.items()), 'Frozen bytes differ before audit')
    old_summary, old_cases, old_review = [read(baseline[name+'_path'])
                                         for name in ('summary','cases','review')]
    require(old_summary['status'] == 'PASS_CONDITIONAL_INJECTION_RECOVERY' and
            old_summary['plan_sha256'] == plan['parent_BY_plan_sha256'] and
            old_summary['arrays_sha256'] == baseline['arrays_sha256'], 'BY production authority differs')
    require(old_review['status'] == 'PASS_INDEPENDENT_INJECTION_REVIEW' and
            old_review['plan_sha256'] == plan['parent_BY_plan_sha256'] and
            old_review['production_summary_sha256'] == baseline['summary_sha256'] and
            old_review['arrays_sha256'] == baseline['arrays_sha256'] and
            old_review['complete_calibration_vectors_checked'] == 15840 and
            old_review['calibration_track_sums_checked'] == 42577920 and
            old_review['all_bound_bytes_unchanged'], 'BY independent audit authority differs')
    require(out.is_absolute() and str(out).startswith('/dev/shm/') and not out.exists(),
            'Exclusive independent tmpfs audit output required; no retry')
    out.mkdir(parents=True)
    summary, saved_cases = read(production/'SUMMARY_BZ.json'), read(production/'CASES_BZ.json')
    cases = expected_cases()
    require(old_cases['cases'] == cases and old_cases['config'] == parent['config'], 'BY cases differ')
    require(saved_cases['cases'] == cases and saved_cases['config'] == plan['config'], 'BZ cases differ')
    require(summary['status'] == 'PASS_NESTED_GRID_ABLATION' and
            summary['plan_sha256'] == ph and summary['public_freeze_commit'] == freeze['public_commit'],
            'Production identity differs')
    require(summary['arrays_sha256'] == sha(production/'RESULT_ARRAYS_BZ.npz'), 'Array binding differs')
    require(summary['case_count'] == 264 and summary['geometry_count'] == 24, 'Case counts differ')
    require(summary['new_SETI_searches'] == summary['new_observational_coverage'] == 0 and
            summary['calibrated_astronomical_sensitivity'] is False and
            summary['full_cadence_status'] == 'NOT_EVALUABLE_MISSING_OFF5', 'Scientific claims differ')
    with np.load(baseline['arrays_path'], allow_pickle=False) as source:
        old = {name:source[name] for name in source.files}
    with np.load(production/'RESULT_ARRAYS_BZ.npz', allow_pickle=False) as source:
        arrays = {name:source[name] for name in source.files}
    require(old['calibration'].shape == (264,5,3,4,2), 'Wrong BY calibration shape')
    require(arrays['calibration'].shape == (264,5,17,4,2), 'Wrong BZ calibration shape')
    require(np.isfinite(arrays['calibration']).all() and
            (arrays['calibration'][...,1] > 0).all(), 'Invalid saved calibration')
    exact_array(arrays['calibration'][:,:,COARSE_POSITIONS,:,:], old['calibration'], 'coarse calibration')
    exact_array(arrays['injected_sha256'], old['injected_sha256'], 'BY injected matrix hash matrix')
    n = len(arrays['seed_case_index'])
    for key in ('center_scores','max_scores','valid','predicted_native'):
        require(arrays[key].shape == (n,6), 'Six-slot association matrix required')
    for key in ('seed_case_index','seed_refined_index','seed_coarse_drift_index',
                'seed_center_native','seed_width','seed_ess','candidate_status','seed_baseline_row','seed_drift_hz_s'):
        require(arrays[key].shape == (n,), 'Seed vector shape differs')
    require(np.isnan(arrays['center_scores'][:,5]).all() and
            np.isnan(arrays['max_scores'][:,5]).all() and
            not arrays['valid'][:,5].any() and
            (arrays['predicted_native'][:,5] == -1).all(), 'Missing OFF5 was substituted')
    require(np.isfinite(arrays['center_scores'][:,:5]).all() and
            np.isfinite(arrays['max_scores'][:,:5]).all() and arrays['valid'][:,:5].all(),
            'A real projected scan is unsupported or nonfinite')
    require(((0 <= arrays['seed_case_index']) & (arrays['seed_case_index'] < 264)).all(), 'Bad seed case')
    require(((0 <= arrays['seed_refined_index']) & (arrays['seed_refined_index'] <= 16)).all(), 'Bad refined index')
    require(set(map(int,arrays['seed_width'])) <= set(WIDTHS), 'Bad seed width')
    require(np.isfinite(arrays['seed_ess']).all(), 'Nonfinite source score')
    saved_identities = {}
    for i in range(n):
        identity = tuple(int(arrays[key][i]) for key in
                         ('seed_case_index','seed_center_native','seed_refined_index','seed_width'))
        require(identity not in saved_identities, 'Duplicated seed identity')
        saved_identities[identity] = i
    require(list(saved_identities) == sorted(saved_identities,key=lambda item:(item[0],WIDTHS.index(item[3]),item[2],item[1])),
            'Declared case-width-rate-center seed ordering differs')
    baseline_rows_checked = 0
    for old_i in range(len(old['seed_case_index'])):
        ci = int(old['seed_case_index'][old_i])
        coarse_ri = int(old['seed_drift_index'][old_i])
        pos = 8*(coarse_ri-cases[ci]['base_drift_index']+1)
        identity = (ci,int(old['seed_center_native'][old_i]),pos,int(old['seed_width'][old_i]))
        require(identity in saved_identities, 'Lost exact BY seed identity')
        i = saved_identities[identity]
        require(int(arrays['seed_coarse_drift_index'][i]) == coarse_ri and
                int(arrays['seed_baseline_row'][i]) == old_i, 'Coarse drift or baseline row identity differs')
        for key in ('seed_ess','center_scores','max_scores','valid','predicted_native','candidate_status'):
            exact_array(arrays[key][i:i+1], old[key][old_i:old_i+1], 'coarse seed '+key)
        baseline_rows_checked += 1
    coarse_rows = np.isin(arrays['seed_refined_index'],COARSE_POSITIONS)
    require(int(coarse_rows.sum()) == baseline_rows_checked == 736, 'Coarse catalog differs from sealed BY')
    require((arrays['seed_coarse_drift_index'][~coarse_rows] == -1).all() and
            (arrays['seed_baseline_row'][~coarse_rows] == -1).all(), 'New rate mislabeled as old rate')
    backgrounds = []
    for record in plan['inputs']:
        y = np.load(record['path'], allow_pickle=False)
        require(y.shape == (16,12288) and y.dtype == np.dtype('<f4') and np.isfinite(y).all(),
                'Invalid retained background')
        backgrounds.append(y)
    coarse_rates = np.linspace(-4,4,839,dtype=np.float64)
    old_step = float(coarse_rates[1]-coarse_rates[0])
    dt,df = plan['scans'][0]['dt_seconds'],plan['scans'][0]['df_hz']
    rates_by_base = {base:nested_rates(base) for base in (314,419,524)}
    exact_array(arrays['base_drift_indices'],np.asarray([314,419,524],dtype=np.int32),'base drift indices')
    exact_array(arrays['rate_grid_by_base'],np.asarray([rates_by_base[base] for base in (314,419,524)]),
                'independently constructed nested grid')
    for identity,i in saved_identities.items():
        ci,_,ri,_ = identity
        expected_rate = rates_by_base[cases[ci]['base_drift_index']][ri]
        require(float(arrays['seed_drift_hz_s'][i]).hex() == float(expected_rate).hex(),
                'Stored seed rate differs from exact nested grid')
    offsets_by_base = {base:{ri:np.asarray([round(float(rates[ri])*(row-7.5)*dt/df)
                                           for row in range(16)],dtype=np.int32)
                            for ri in NEW_POSITIONS} for base,rates in rates_by_base.items()}
    maximum_calibration_error = maximum_scalar_error = maximum_score_error = 0.0
    maximum_weight_error = maximum_mass_error = 0.0
    vector_count = scalar_count = injection_count = weight_count = computed_tracks = new_seed_count = 0
    weights_cache = {}
    for case in cases:
        ci,base_index = case['case_index'],case['base_drift_index']
        rates,offsets = rates_by_base[base_index],offsets_by_base[base_index]
        expected_new_seeds = {}
        matrices = []
        calibration = arrays['calibration'][ci].copy()
        for scan,(scope,record,background) in enumerate(zip(plan['scans'],plan['inputs'],backgrounds)):
            cache_key = case['geometry'],scan
            if cache_key not in weights_cache:
                weights_cache[cache_key] = audited_weights(case,scope,plan['scans'][0],record)
                detail = weights_cache[cache_key][1]
                weight_count += detail['weight_comparisons']
                maximum_weight_error = max(maximum_weight_error,detail['maximum_weight_error'])
                maximum_mass_error = max(maximum_mass_error,detail['maximum_mass_error'])
            active = case['presence'] == 'ALL_FIVE' or (case['presence'] == 'ON_ONLY' and scan in (0,2,4))
            y = reconstructed_matrix(background,weights_cache[cache_key][0],case['amplitude'],active)
            require(hashlib.sha256(y.tobytes(order='C')).hexdigest() == old['injected_sha256'][ci,scan],
                    'Independent injection matrix bytes differ from sealed BY')
            injection_count += 1
            matrices.append(y)
            for wi,(width,stride) in enumerate(zip(WIDTHS,STRIDES)):
                centers = np.arange(4096,8192,stride,dtype=np.int32)
                for ri in NEW_POSITIONS:
                    sums = direct_vector(y,offsets[ri],centers,width)
                    median,scale = median_mad(sums)
                    calibration[scan,ri,wi] = median,scale
                    error = float(np.max(np.abs(calibration[scan,ri,wi]-arrays['calibration'][ci,scan,ri,wi])))
                    require(error < SCORE_TOLERANCE, 'Independent new-rate calibration differs')
                    maximum_calibration_error = max(maximum_calibration_error,error)
                    vector_count += 1
                    computed_tracks += len(centers)
                    scores = (sums-median)/scale
                    if scan == 0 and abs(float(rates[ri])-case['true_drift_hz_s']) <= old_step+1e-12:
                        near = np.flatnonzero(np.abs(centers+record['support_start']-
                                                    case['true_center_native_at_scan0_midpoint']) <= width//2+2)
                        radius = max(3,2*math.ceil(width/stride)+1)//2
                        for position in near:
                            if scores[position] >= 10 and is_local_peak(scores,int(position),radius):
                                identity = (ci,int(centers[position])+record['support_start'],ri,width)
                                require(identity not in expected_new_seeds, 'Independent duplicate seed')
                                expected_new_seeds[identity] = float(scores[position])
        actual_new = {key:i for key,i in saved_identities.items() if key[0] == ci and key[2] in NEW_POSITIONS}
        require(set(actual_new) == set(expected_new_seeds), 'Complete new-rate source catalog differs')
        for identity,source_score in expected_new_seeds.items():
            _,native_seed,ri,width = identity
            i = actual_new[identity]
            error = abs(float(arrays['seed_ess'][i])-source_score)
            require(error < SCORE_TOLERANCE, 'New source seed score differs')
            maximum_score_error = max(maximum_score_error,error)
            centers_scores,maxima = [],[]
            for scan,(scope,record,y) in enumerate(zip(plan['scans'],plan['inputs'],matrices)):
                gap = (scope['tref_midpoint_mjd']-plan['scans'][0]['tref_midpoint_mjd'])*86400
                frequency = plan['scans'][0]['fch1_mhz']+native_seed*plan['scans'][0]['df_hz']/1e6
                projected = int(round((frequency+float(rates[ri])*gap/1e6-scope['fch1_mhz'])*1e6/scope['df_hz']))
                require(projected == int(arrays['predicted_native'][i,scan]), 'New seed projection differs')
                radius = math.ceil(1+.5*old_step*abs(gap)/abs(scope['df_hz']))
                center = projected-record['support_start']
                require(center+int(offsets[ri].min())-width//2-radius >= 0 and
                        center+int(offsets[ri].max())+width//2+radius < y.shape[1],
                        'Independent projected track is outside support')
                wi = WIDTHS.index(width)
                median,scale = calibration[scan,ri,wi]
                sums = [scalar_sum(y,offsets[ri],channel,width)
                        for channel in range(center-radius,center+radius+1)]
                scores = [(value-median)/scale for value in sums]
                scalar_count += len(scores)
                score,maximum = scores[radius],max(scores)
                saved_median,saved_scale = arrays['calibration'][ci,scan,ri,wi]
                sum_error = max(abs(sums[radius]-(float(arrays['center_scores'][i,scan])*saved_scale+saved_median)),
                                abs(max(sums)-(float(arrays['max_scores'][i,scan])*saved_scale+saved_median)))
                require(sum_error < SCORE_TOLERANCE, 'Independent forced track sum differs')
                maximum_scalar_error = max(maximum_scalar_error,sum_error)
                error = max(abs(score-float(arrays['center_scores'][i,scan])),
                            abs(maximum-float(arrays['max_scores'][i,scan])))
                require(error < SCORE_TOLERANCE, 'Independent new scalar forced score differs')
                maximum_score_error = max(maximum_score_error,error)
                centers_scores.append(score);maxima.append(maximum)
            expected_status = independently_classify(centers_scores,maxima,[True]*5)
            require(str(arrays['candidate_status'][i]) == expected_status, 'Independent new classification differs')
            new_seed_count += 1
        if (ci+1)%11 == 0:
            print(json.dumps({'event':'INDEPENDENT_BZ_GEOMETRY_COMPLETE','geometry':case['geometry'],
                              'cases_checked':ci+1}),flush=True)
    require(vector_count == 73920 and computed_tracks == 198696960 and injection_count == 1320,
            'Independent complete new-rate scope differs')
    require(new_seed_count+baseline_rows_checked == n, 'Unreviewed seed rows remain')
    expected_arms = []
    previous_cases = None
    monotone_case_event_checks = 0
    for factor in FACTORS:
        allowed = tuple(range(0,17,8//factor))
        arm_cases = []
        for case in cases:
            ci = case['case_index']
            chosen = [i for identity,i in saved_identities.items()
                      if identity[0] == ci and identity[2] in allowed]
            counts = {label:0 for label in LABELS}
            for i in chosen:
                independent_label = independently_classify(arrays['center_scores'][i],arrays['max_scores'][i],arrays['valid'][i])
                require(str(arrays['candidate_status'][i]) == independent_label,
                        'Stored status differs from independent all-arm classification')
                counts[independent_label] += 1
            on = bool(counts['REJECTED_AVAILABLE_OFF']+counts['INCOMPLETE_OFF_COVERAGE'])
            rejected,retained = bool(counts['REJECTED_AVAILABLE_OFF']),bool(counts['INCOMPLETE_OFF_COVERAGE'])
            value = dict(case,grid_factor=factor,bank_refined_indices=list(allowed),
                         matched_source_seed_rows=len(chosen),three_ON_recovered=on,
                         available_OFF_rejected=rejected,retained_partial=retained,
                         both_retained_and_rejected=rejected and retained,status_counts=counts)
            if factor == 1:
                stripped = {key:item for key,item in value.items()
                            if key not in ('grid_factor','bank_refined_indices','both_retained_and_rejected')}
                require(stripped == old_summary['cases'][ci], 'Coarse per-case summary differs from BY')
            if previous_cases is not None:
                previous = previous_cases[ci]
                require(previous['matched_source_seed_rows'] <= len(chosen), 'Nested arm lost source seed rows')
                for metric in METRICS:
                    require(not case_flag(previous,metric) or case_flag(value,metric), 'Nested arm lost '+metric)
                    monotone_case_event_checks += 1
            arm_cases.append(value)
        groups = independent_groups(arm_cases)
        if factor == 1:
            require([{key:value for key,value in group.items() if key != 'both_retained_and_rejected'}
                     for group in groups] == old_summary['groups'], 'Coarse aggregate groups differ from BY')
        comparison = {}
        for metric in METRICS:
            comparison[metric] = {
                'gained_case_indices':[case['case_index'] for case,baseline_case in zip(arm_cases,old_summary['cases'])
                                       if case_flag(case,metric) and not case_flag(baseline_case,metric)],
                'lost_case_indices':[case['case_index'] for case,baseline_case in zip(arm_cases,old_summary['cases'])
                                     if case_flag(baseline_case,metric) and not case_flag(case,metric)]}
        expected_arms.append(dict(factor=factor,rates=len(allowed),cases=arm_cases,groups=groups,
                                  comparison_with_BY=comparison))
        previous_cases = arm_cases
    require(summary['arms'] == expected_arms, 'Complete arm cases, groups or comparisons differ')
    expected_counts = dict(injected_matrices_verified_exactly=1320,coarse_seed_rows_reused=736,
                           union_matched_seed_rows=n,new_matched_seed_rows=new_seed_count,
                           new_calibration_vectors=73920,reused_calibration_vectors=15840,
                           new_correlated_track_combinations=198696960,
                           reused_baseline_track_combinations=42577920,
                           union_nominal_track_combinations=241274880)
    require(all(summary[key] == value for key,value in expected_counts.items()), 'Production scope summary differs')
    require(summary['baseline_summary_sha256'] == baseline['summary_sha256'] and
            summary['baseline_arrays_sha256'] == baseline['arrays_sha256'] and
            summary['association_radius_unchanged'] and summary['source_truth_matching_tolerance_unchanged'] and
            summary['baseline_scoring_rerun'] is False, 'Production baseline or ablation identity differs')
    require(all(sha(path) == digest for path,digest in bound.items()), 'Frozen bytes changed during audit')
    result = dict(schema='SETI_BZ_INDEPENDENT_GRID_REVIEW_V1',status='PASS_INDEPENDENT_NESTED_GRID_REVIEW',
                  plan_sha256=ph,reviewer_sha256=sha(__file__),
                  production_summary_sha256=sha(production/'SUMMARY_BZ.json'),
                  arrays_sha256=sha(production/'RESULT_ARRAYS_BZ.npz'),
                  baseline_summary_sha256=baseline['summary_sha256'],baseline_arrays_sha256=baseline['arrays_sha256'],
                  baseline_review_sha256=baseline['review_sha256'],
                  cases_checked=264,geometries_checked=24,injected_matrices_byte_verified=injection_count,
                  independent_exposure_weight_comparisons=weight_count,
                  maximum_exposure_weight_error=maximum_weight_error,maximum_exposure_mass_error=maximum_mass_error,
                  new_complete_calibration_vectors_checked=vector_count,new_calibration_track_sums_checked=computed_tracks,
                  coarse_calibration_vectors_byte_verified=15840,coarse_seed_rows_byte_verified=baseline_rows_checked,
                  new_matched_seeds_checked=new_seed_count,union_matched_seeds_checked=n,
                  new_forced_scalar_tracks_recomputed=scalar_count,new_forced_center_and_maximum_slots_checked=new_seed_count*5,
                  maximum_calibration_absolute_error=maximum_calibration_error,
                  maximum_scalar_absolute_error=maximum_scalar_error,maximum_score_absolute_error=maximum_score_error,
                  nested_case_event_monotonicity_checks=monotone_case_event_checks,
                  arms=[{key:value for key,value in arm.items() if key != 'cases'} for arm in expected_arms],
                  all_bound_bytes_unchanged=True,
                  limits=['No production numerical imports: new-rate vectors use direct additions, Python order statistics and math.fsum forced tracks.',
                          'Coarse results are bound byte-for-byte to sealed independently audited BY; no coarse search rerun.',
                          'Every injected matrix is independently reconstructed and bound to its exact BY hash; exposure weights also use an independent piecewise-trapezoid integral.',
                          'NPY decoder, NumPy float storage, original coarse grid and exact declared injection arithmetic are shared primitives.',
                          'Refinement selected after BY; reused exposed background and known-truth local banks. No new observations or global false-alarm calibration.',
                          'Retained and rejected case flags may overlap through different seeds. Missing OFF5 remains unobserved; no complete-cadence candidate or sensitivity claim.'],
                  wall_seconds=time.monotonic()-began,completed_utc=datetime.now(timezone.utc).isoformat())
    write(out/'REVIEW_BZ.json',result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--freeze',required=True,type=Path)
    parser.add_argument('--production',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args = parser.parse_args()
    def expired(signum,frame):
        raise TimeoutError('BZ fixed 600-second independent audit budget reached')
    signal.signal(signal.SIGALRM,expired);signal.alarm(600)
    result = audit(args.plan,args.freeze,args.production,args.out)
    signal.alarm(0)
    print(json.dumps({'status':result['status'],'cases':result['cases_checked'],
                      'new_matched_seeds':result['new_matched_seeds_checked']}),flush=True)
