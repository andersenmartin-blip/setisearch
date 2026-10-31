"""Prospective BP fixed-five-rate paired control comparator.

Importing this module draws no random values and opens no data. This is a new
limited association policy, not a replay or requalification of historical M
or BN identities. Runtime activation and immutable source pins belong to the
parent preregistered runner.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('bp_bo_methods', ROOT / 'work_bo/src/methods.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SHAPE = (16, 1048576)
Q = (63, 64, 65, 127, 129)
WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
RATE_INDICES = (0, 209, 419, 629, 838)
RATES = np.linspace(-4.0, 4.0, 839, dtype=np.float64)
DT, DF = 18.253611008, -2.7939677238464355
MJD = np.array([57642.735972222225, 57642.73994212963,
                57642.74390046296, 57642.74791666667,
                57642.751921296294, 57642.75582175926], dtype=np.float64)
ON = (0, 2, 4)
OFF = (1, 3, 5)
MAX_SCAN_HITS = 100000
MAX_ASSOCIATIONS_PER_METHOD = 50000


def specification():
    return {
        'schema': 'SETI_BP_PAIRED_SEARCH_SPEC_V1',
        'shape': list(SHAPE), 'q': list(Q), 'widths': list(WIDTHS),
        'strides': list(STRIDES), 'rate_indices': list(RATE_INDICES),
        'rate_bank': {'count': 839, 'minimum': -4, 'maximum': 4},
        'dt': DT, 'df': DF, 'header_mjd': MJD.tolist(),
        'reference_row': 7.5, 'legacy_saved_label_row': 8,
        'legacy_global_interior': [4096, 1044480],
        'legacy_calibration_includes_q128': True,
        'legacy_ESS_arithmetic': 'Original float32 (sums-med)/scale under pinned NumPy2.3.5',
        'current_ESS_arithmetic': 'float64 with local q median/MAD',
        'full_native_normalization_before_crop': True,
        'association_policy': 'NEW_BP_TARGET_PHYSICAL_Q_FIXED_GRID',
        'association_sources': 'Every ON>=10 grid point in all three ON scans, both methods independently',
        'association_rate_and_width': 'Exact source sparse-bank rate and width retained; no rate search during force',
        'destination_center': 'rint((source_center+rate*(MJDtarget-MJDsource)*86400/DF)/stride)*stride',
        'target_calibration': 'Each target point uses its own physical q; only declared five q grids supported',
        'OFF_radius_channels': 'ceil(1+0.5*(8/838)*abs(gap_seconds)/abs(DF))+ceil(stride/2)',
        'OFF_endpoint': 'Maximum ESS of every grid carrier in closed destination-center +/- radius window',
        'support': 'All ON center and all OFF window carriers must exist in declared q grids; unsupported cannot pass',
        'ON_cut': 10, 'OFF_cut': 5,
        'truth_candidates': 'Scan0, exact injected rate, all widths, every grid center within stride/2+1 of row7.5 truth',
        'truth_credit': 'Truth candidate passes all ON and no OFF and the identical candidate fails on paired uninjected input',
        'oracle_indices_per_q_rate_width': 'first, middle, last',
        'current_oracle_bound': 'max(1e-8,64*float64_epsilon*sum_abs_terms)',
        'legacy_oracle': 'Independent Python binary64 sequential prefixes, then explicit original float32 width and row rounds',
        'legacy_original_absolute_guard': 5e-5,
        'legacy_guard_FAIL_policy': 'Retain failures literally; they are diagnostic and never historical repair or requalification',
        'max_scan_hits_per_method': MAX_SCAN_HITS,
        'max_associations_per_method': MAX_ASSOCIATIONS_PER_METHOD,
        'stored': 'Full local sum/ESS vectors; complete-global-vector SHA256, median/MAD and max; full hit lists/maxima; selected oracles',
        'not_qualified': ['full839 rate bank', 'astronomical sensitivity', 'FAP', 'flux/EIRP', 'sky origin'],
    }


def require(ok, message):
    if not ok:
        raise ValueError(message)


def array_sha(x):
    a = np.asarray(x)
    require(a.flags.c_contiguous, 'SHA requires C-contiguous bytes')
    return hashlib.sha256(memoryview(a).cast('B')).hexdigest()


def _write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def offsets_for(rate_index):
    require(rate_index in RATE_INDICES, 'Outside frozen rate subset')
    return np.rint(RATES[rate_index] * (np.arange(16, dtype=np.float64)-7.5)*DT/DF).astype(np.int32)


def _key(method, rate_index, width, q, kind):
    return f'{method}_r{rate_index}_w{width}_q{q}_{kind}'


def requests():
    result = []
    for width, stride in zip(WIDTHS, STRIDES, strict=True):
        for ri in RATE_INDICES:
            off = offsets_for(ri)
            for q in Q:
                centers = np.arange(q*4096, (q+1)*4096, stride, dtype=np.int32)
                indices = np.array([0, len(centers)//2, len(centers)-1], dtype=np.int32)
                result.append({'width': width, 'stride': stride, 'rate_index': ri,
                               'q': q, 'offsets': off, 'centers': centers[indices],
                               'indices': indices})
    return result


def independent_prefixes(y, reqs):
    """Preserve legacy global-prefix subtraction with independent Python sums."""
    needed = [set() for _ in range(len(y))]
    for req in reqs:
        if req['width'] == 1:
            continue
        h = req['width']//2
        for t, off in enumerate(req['offsets']):
            for center in req['centers']:
                c = int(center)+int(off)
                require(0 <= c-h < c+h+1 <= y.shape[1], 'Oracle lacks support')
                needed[t].update((c-h, c+h+1))
    answer = []
    for row, positions in zip(y, needed, strict=True):
        total, previous = 0.0, 0
        found = {0: 0.0}
        for stop in sorted(positions):
            for value in row[previous:stop]:
                total = total + float(value)
            found[stop] = total
            previous = stop
        answer.append(found)
    return answer


def scalar_terms(y, off, center, width):
    h = width//2
    return [float(y[t, int(center)+int(o)+j])
            for t, o in enumerate(off) for j in range(-h, h+1)]


def legacy_staged_oracle(y, prefixes, off, center, width):
    total = np.float32(0)
    h = width//2
    for t, o in enumerate(off):
        c = int(center)+int(o)
        v = np.float32(y[t, c]) if width == 1 else np.float32(prefixes[t][c+h+1]-prefixes[t][c-h])
        total = np.float32(total+v)
    return total


def analyze_scan(raw, output_dir, scan_index):
    """Score an immutable synthetic native scan once, preserving partial errors."""
    start = time.monotonic()
    raw = np.asarray(raw)
    require(raw.shape == SHAPE and raw.dtype == np.dtype('<f4') and raw.flags.c_contiguous,
            'Exact native shape/dtype/order required')
    require(not raw.flags.writeable, 'Common input must be immutable')
    require(scan_index in range(6), 'Bad scan index')
    require(np.isfinite(raw).all() and (raw >= 0).all(), 'Invalid synthetic powers')
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    before = array_sha(raw)
    _write_json(out/'START.json', {'scan_index': scan_index, 'input_powers_sha256': before,
                                 'specification': specification()})
    vendor = M.verify_sources()
    kernel, normalizer = M.load_current()
    current, anchors = normalizer.normalize(raw)
    legacy, legacy_rows = M.legacy_normalize(raw)
    reqs = requests()
    prefixes = independent_prefixes(legacy, reqs)
    arrays = {f'current_anchor_{k}': v for k, v in anchors.items()}
    arrays['legacy_block_median'] = np.asarray([r['median'] for r in legacy_rows], dtype=np.float32)
    arrays['legacy_block_MAD_scale'] = np.asarray([r['mad_scale'] for r in legacy_rows], dtype=np.float32)
    calibrations, oracles, hits, maxima = [], [], {'current': [], 'legacy': []}, []
    fallbacks = 0
    for width, stride in zip(WIDTHS, STRIDES, strict=True):
        cp = kernel.boxcars(current, width)
        lp = M.legacy_centered_boxcar(legacy, width)
        for ri in RATE_INDICES:
            off = offsets_for(ri)
            global_sums = M.legacy_track_sum(lp, off, 4096, 1044480, stride)
            gm, gs = M.legacy_ess_calibration(global_sums)
            global_scores = (global_sums-gm)/gs
            require(global_scores.dtype == np.float32, 'Legacy ESS rounding differs')
            gi = int(np.argmax(global_scores))
            global_info = {'rate_index': ri, 'width': width, 'stride': stride,
                           'domain': [4096, 1044480], 'count': len(global_sums),
                           'median': gm, 'MAD_scale': gs, 'sum_sha256': array_sha(global_sums),
                           'sum_dtype': global_sums.dtype.str,
                           'maximum_ESS': float(global_scores[gi]),
                           'maximum_center': int(4096+gi*stride)}
            calibrations.append({'method': 'legacy_global', **global_info})
            for q in Q:
                csums, fallback, bound = kernel.tracks_grid(current, cp, off, q*4096, (q+1)*4096, stride, width)
                fallbacks += fallback
                cm, cscale = M.current_calibration(csums)
                cscores = (csums-cm)/cscale
                begin, end = (q*4096-4096)//stride, ((q+1)*4096-4096)//stride
                lsums = global_sums[begin:end].copy()
                lscores = (lsums-gm)/gs
                require(len(csums) == 4096//stride and len(lsums) == len(csums), 'Wrong carrier domain')
                calibrations.append({'method': 'current_local', 'rate_index': ri, 'width': width,
                                     'stride': stride, 'q': q, 'count': len(csums), 'median': cm,
                                     'MAD_scale': cscale, 'fallbacks': fallback, 'kernel_bound': bound})
                for method, sums, scores in [('current', csums, cscores), ('legacy', lsums, lscores)]:
                    require(np.isfinite(scores).all(), 'Nonfinite ESS')
                    arrays[_key(method, ri, width, q, 'sum')] = sums
                    arrays[_key(method, ri, width, q, 'score')] = scores
                    k = int(np.argmax(scores))
                    maxima.append({'method': method, 'rate_index': ri, 'width': width, 'q': q,
                                   'center': q*4096+k*stride, 'ESS': float(scores[k])})
                    for k in np.flatnonzero(scores >= (10 if scan_index in ON else 5)):
                        hits[method].append({'source_scan': scan_index, 'rate_index': ri,
                                             'width': width, 'stride': stride, 'q': q,
                                             'center': q*4096+int(k)*stride,
                                             'ESS': float(scores[k])})
                    require(len(hits[method]) <= MAX_SCAN_HITS, 'Frozen hit cap exceeded')
                req = next(r for r in reqs if r['rate_index'] == ri and r['width'] == width and r['q'] == q)
                for k, c in zip(req['indices'], req['centers'], strict=True):
                    ct = scalar_terms(current, off, c, width)
                    cref = math.fsum(ct)
                    magnitude = math.fsum(abs(v) for v in ct)
                    error = abs(float(csums[k])-cref)
                    cbound = max(1e-8, 64*np.finfo(np.float64).eps*magnitude)
                    require(error <= cbound, 'Current scalar oracle failed')
                    lref = math.fsum(scalar_terms(legacy, off, c, width))
                    staged = legacy_staged_oracle(legacy, prefixes, off, c, width)
                    require(lsums[k].tobytes() == staged.tobytes(), 'Legacy stage oracle failed')
                    lerror = abs(float(lsums[k])-lref)
                    oracles.append({'rate_index': ri, 'width': width, 'q': q, 'center': int(c),
                                    'current_sum': float(csums[k]), 'current_fsum': cref,
                                    'current_abs_error': error, 'current_bound': cbound,
                                    'legacy_sum': float(lsums[k]), 'legacy_staged': float(staged),
                                    'legacy_staged_exact': True, 'legacy_fsum': lref,
                                    'legacy_abs_error': lerror,
                                    'legacy_original_guard': 'PASS' if lerror <= 5e-5 else 'FAIL'})
            del global_sums, global_scores
        del cp, lp
    require(array_sha(raw) == before and not raw.flags.writeable, 'Common input changed')
    with (out/'arrays.npz').open('xb') as f:
        np.savez(f, **arrays)
    evidence = {'arrays.npz': {'sha256': M.file_sha(out/'arrays.npz'), 'bytes': (out/'arrays.npz').stat().st_size}}
    result = {'schema': 'SETI_BP_SCAN_RESULT_V1', 'status': 'PASS', 'scan_index': scan_index,
              'input_powers_sha256_before': before, 'input_powers_sha256_after': before,
              'current_normalized_sha256': array_sha(current), 'legacy_normalized_sha256': array_sha(legacy),
              'vendor': vendor, 'calibrations': calibrations, 'oracles': oracles,
              'legacy_original_guard_FAILs': sum(r['legacy_original_guard']=='FAIL' for r in oracles),
              'current_oracle_comparisons': len(oracles), 'legacy_staged_comparisons': len(oracles),
              'fallback_count': fallbacks, 'hits': hits, 'maxima': maxima, 'evidence': evidence,
              'wall_seconds': time.monotonic()-start}
    _write_json(out/'RESULT.json', result)
    return result


class ScoreStore:
    """Bounded, verified local arrays; unknown q is explicitly unsupported."""
    def __init__(self, paths):
        require(len(paths) == 6, 'Exactly six scans required')
        self.results, self.arrays = [], []
        for scan, path in enumerate(paths):
            p = Path(path)
            result = json.loads((p/'RESULT.json').read_text())
            require(result['status'] == 'PASS' and result['scan_index'] == scan, 'Unclosed or wrong scan')
            require(M.file_sha(p/'arrays.npz') == result['evidence']['arrays.npz']['sha256'], 'Changed scan score archive')
            self.results.append(result)
            with np.load(p/'arrays.npz', allow_pickle=False) as z:
                self.arrays.append({k: z[k] for k in z.files if k.endswith('_score')})

    def points(self, method, scan, ri, width, centers):
        stride = STRIDES[WIDTHS.index(width)]
        answer = []
        for center in centers:
            c = int(center)
            if c % stride or c//4096 not in Q:
                return None
            a = self.arrays[scan].get(_key(method, ri, width, c//4096, 'score'))
            if a is None:
                return None
            i = (c % 4096)//stride
            if not 0 <= i < len(a):
                return None
            answer.append(float(a[i]))
        return answer


def off_radius(gap_seconds, stride):
    return math.ceil(1+0.5*(8/838)*abs(gap_seconds)/abs(DF))+math.ceil(stride/2)


def forced_geometry(source_scan, source_center, ri, width, target_scan):
    stride = STRIDES[WIDTHS.index(width)]
    gap = float((MJD[target_scan]-MJD[source_scan])*86400.0)
    physical = float(source_center+RATES[ri]*gap/DF)
    center = int(np.rint(physical/stride))*stride
    radius = off_radius(gap, stride) if target_scan in OFF else 0
    low = int(math.ceil((center-radius)/stride))*stride
    high = int(math.floor((center+radius)/stride))*stride
    points = list(range(low, high+1, stride))
    return {'scan': target_scan, 'gap_seconds': gap, 'physical_center': physical,
            'center': center, 'radius_channels': radius, 'points': points}


def force(store, method, candidate):
    measurements = []
    for scan in range(6):
        geom = forced_geometry(candidate['source_scan'], candidate['center'],
                               candidate['rate_index'], candidate['width'], scan)
        values = store.points(method, scan, candidate['rate_index'], candidate['width'], geom['points'])
        measurements.append({**geom, 'supported': values is not None,
                             'ESS_values': values, 'ESS': None if values is None else max(values)})
    supported = all(m['supported'] for m in measurements)
    on_pass = all(measurements[s]['supported'] and measurements[s]['ESS'] >= 10 for s in ON)
    off_veto = any(measurements[s]['supported'] and measurements[s]['ESS'] >= 5 for s in OFF)
    passed = supported and on_pass and not off_veto
    status = 'PASS' if passed else ('UNSUPPORTED' if not supported else ('THREE_ON_FAIL' if not on_pass else 'OFF_VETO'))
    return {'source': candidate, 'measurements': measurements, 'supported': supported,
            'three_ON_pass': on_pass, 'OFF_veto': off_veto, 'flag': passed, 'status': status}


def truth_candidates(truth):
    ri = int(truth['rate_index'])
    require(ri in RATE_INDICES, 'Truth rate outside frozen subset')
    center = float(truth['channel_scan0_at_row7p5'])
    result = []
    for width, stride in zip(WIDTHS, STRIDES, strict=True):
        radius = stride/2+1
        lo, hi = math.ceil((center-radius)/stride), math.floor((center+radius)/stride)
        for k in range(lo, hi+1):
            c = k*stride
            require(c//4096 in Q, 'Truth origin outside frozen grids')
            result.append({'source_scan': 0, 'rate_index': ri, 'width': width,
                           'stride': stride, 'q': c//4096, 'center': c,
                           'truth_offset_channels': c-center, 'truth_radius_channels': radius})
    return result


def assess_case(scan_dirs, case_spec, base_scan_dirs=None):
    store = ScoreStore(scan_dirs)
    base = ScoreStore(base_scan_dirs) if base_scan_dirs is not None else None
    result = {'schema': 'SETI_BP_CASE_ASSESSMENT_V1', 'case_id': case_spec['case_id'],
              'kind': case_spec['kind'], 'association_policy': 'NEW_BP_TARGET_PHYSICAL_Q_FIXED_GRID',
              'method_results': {}}
    for method in ('current', 'legacy'):
        seeds = [hit for scan in ON for hit in store.results[scan]['hits'][method]]
        require(len(seeds) <= MAX_ASSOCIATIONS_PER_METHOD, 'Frozen association cap exceeded')
        associations = [force(store, method, hit) for hit in seeds]
        counts = {s: sum(a['status'] == s for a in associations)
                  for s in ('PASS', 'UNSUPPORTED', 'THREE_ON_FAIL', 'OFF_VETO')}
        truth = case_spec.get('truth')
        matched = []
        if truth is not None:
            for candidate in truth_candidates(truth):
                a = force(store, method, candidate)
                b = force(base, method, candidate) if base is not None else None
                credited = a['flag'] and b is not None and b['supported'] and not b['flag']
                matched.append({'injected': a, 'uninjected': b, 'recovery_credit': credited})
        result['method_results'][method] = {
            'source_ON_hits': len(seeds), 'association_counts': counts,
            'associations': associations, 'flags': counts['PASS'],
            'truth': matched, 'truth_recovered': any(m['recovery_credit'] for m in matched),
            'truth_any_supported': any(m['injected']['supported'] for m in matched),
            'truth_any_supported_OFF_veto': any(m['injected']['supported'] and m['injected']['OFF_veto'] for m in matched),
            'truth_all_supported_fail_three_ON': bool(matched) and all(m['injected']['supported'] and not m['injected']['three_ON_pass'] for m in matched),
        }
    current = result['method_results']['current']
    legacy = result['method_results']['legacy']
    kind = case_spec['kind']
    reasons = []
    status = 'PASS'
    if kind == 'null':
        if current['flags']:
            status = 'FAIL'
            reasons.append('CURRENT_NULL_HAS_SUPPORTED_THREE_ON_NO_OFF_FLAG')
        else:
            reasons.append('CURRENT_NULL_NO_SUPPORTED_THREE_ON_NO_OFF_FLAGS')
    elif kind == 'positive':
        require(base is not None, 'Positive endpoint requires paired uninjected controls')
        if case_spec['amplitude'] == 256:
            if not current['truth_recovered']:
                status = 'FAIL'
                reasons.append('CURRENT_STRONG_KNOWN_TRUTH_NOT_RECOVERED')
            else:
                reasons.append('CURRENT_STRONG_KNOWN_TRUTH_RECOVERED')
        elif case_spec['amplitude'] == 15:
            if legacy['truth_recovered'] and not current['truth_recovered']:
                status = 'REVIEW_REQUIRED'
                reasons.append('WEAK_LEGACY_RECOVERY_LOST_BY_CURRENT')
            else:
                reasons.append('NO_WEAK_LEGACY_ONLY_RECOVERY_LOSS')
        else:
            raise ValueError('Unfrozen positive amplitude')
    elif kind in ('association', 'association_broad'):
        if current['flags']:
            status = 'FAIL'
            reasons.append('ASSOCIATION_HAS_SUPPORTED_THREE_ON_NO_OFF_FLAG')
        if case_spec['case_id'] in ('A01', 'A02'):
            expected_rejection = current['truth_any_supported_OFF_veto']
            reasons.append('REQUIRES_ACTUAL_SUPPORTED_OFF_VETO')
        elif case_spec['case_id'] == 'A03':
            expected_rejection = current['truth_all_supported_fail_three_ON']
            reasons.append('REQUIRES_SUPPORTED_THREE_ON_REJECTION')
        elif case_spec['case_id'] == 'A04':
            expected_rejection = (current['truth_any_supported_OFF_veto']
                                  or current['truth_all_supported_fail_three_ON'])
            reasons.append('REQUIRES_SUPPORTED_OFF_OR_THREE_ON_REJECTION')
        else:
            raise ValueError('Unknown association identity')
        if not expected_rejection:
            status = 'FAIL'
            reasons.append('EXPECTED_SUPPORTED_REJECTION_NOT_DEMONSTRATED')
    else:
        raise ValueError('Unfrozen case kind')
    result['status'] = status
    result['gate_reasons'] = reasons
    result['current_flags'] = current['flags']
    result['legacy_flags'] = legacy['flags']
    result['current_truth_recovered'] = current['truth_recovered']
    result['legacy_truth_recovered'] = legacy['truth_recovered']
    return result
