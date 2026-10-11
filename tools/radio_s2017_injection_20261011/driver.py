"""Prospective raw-power injection benchmark; import/check-only reads text only.

No prior profiles or astronomical candidates are regenerated. Numerical work
requires the root's exact public freeze and GO. Six backgrounds are tested
separately with a reset at each scan's actual first integration midpoint.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
BASE = 'analysis/s2017_injection_20261011'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
NATIVE, COUNT, CORE, HALO = 171, 1048576, 4096, 4000
C0, FCH1, DF, TSAMP = NATIVE * COUNT, 2802832031.25, -2.7939677238464355, 18.253611008
JOBS = {'offcenter': (64, 192), 'known_center_competitor': (128,)}
DRIFT_INDICES, INJECT_WIDTHS, AMPLITUDES = (245, 392, 539), (1, 9), (0, 1, 3, 6, 12)
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ACQ = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
QA = 'analysis/new_visit_recovery/results/review/QA_RECEIPT.json'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
READER = 'analysis/new_visit_search/dependencies/standard_reader.py'
PINS = {SOURCE: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    ACQ: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    QA: 'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f',
    DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    READER: '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1048576), b''):
            h.update(part)
    return h.hexdigest()

def workspace_allocated(root):
    seen, total = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                info = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            key = (info.st_dev, info.st_ino)
            if key not in seen:
                seen.add(key)
                total += info.st_blocks * 512
    return total

def resource_guard(root, scope, out=None, job=None, reserve=False):
    allocated = workspace_allocated(root)
    require(allocated + (scope['hard_total_output_budget_bytes'] if reserve else 0)
            <= scope['workspace_cap_bytes'], '8GiB workspace reserve/runtime bound exceeded')
    if out is not None:
        output_bytes = sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        require(output_bytes <= scope['job_output_budget_bytes'][job], 'Per-job output budget exceeded')
    return allocated

def pairs(items):
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON field')
        value[key] = item
    return value

def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs)

def save(path, value):
    data = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf8')
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Unconfined path')
    return path

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

def contract(root, scope):
    require(scope['schema'] == 'SETI_S2017_RAW_POWER_INJECTION_SCOPE_V1', 'Scope schema differs')
    expected = {'native_chunk_index': 171, 'cores': [64, 128, 192], 'scan_order': list(SCANS),
        'core_channels': CORE, 'halo_channels': HALO, 'search_widths': [1, 3], 'drift_grid_count': 785,
        'injected_widths': [1, 9], 'injected_drift_indices': list(DRIFT_INDICES),
        'amplitudes_baseline_residual_MAD_units_per_cell': list(AMPLITUDES),
        'truth_reference_offset_in_core': 2048, 'local_diagnostic_halfwidth_channels': 5,
        'rounded_center_tolerance_channels': 1, 'operational_score_threshold': 10,
        'CPU_cap_s_per_job': 1000, 'wall_cap_s_per_job': 1800,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'memory_cap_bytes_aggregate': 4 * 1024**3,
        'max_simultaneous_jobs': 2, 'new_telescope_HTTP_requests': 0,
        'workspace_cap_bytes': 8 * 1024**3, 'hard_total_output_budget_bytes': 300 * 1024**2,
        'cadence_coherent_sky_injection': False, 'qualified_SETI_detection': False}
    for key, item in expected.items():
        require(scope.get(key) == item, 'Frozen method differs: ' + key)
    require(scope['jobs'] == {key: list(qs) for key, qs in JOBS.items()}, 'Job partition differs')
    require(scope['baseline_maps'] == 18 and scope['modified_maps'] == 432 and scope['total_maps'] == 450,
            'Map counts differ')
    for name, sha in scope['text_code_pins'].items():
        require(Path(name).suffix in ('.py', '.json') and digest(confined(root, name)) == sha,
                'Text/code pin differs: ' + name)
    require(all(scope['text_code_pins'].get(name) == sha for name, sha in PINS.items()), 'Prerequisite pins differ')
    require(scope['text_code_pins'][BASE + '/driver.py'] == digest(Path(__file__).resolve()), 'Driver self pin differs')
    source, acq, qa = (read_json(root / name) for name in (SOURCE, ACQ, QA))
    require(acq['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
        and qa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
        and qa['acquisition_receipt_sha256'] == PINS[ACQ], 'Actual prior source admission differs')
    require([r['scan_id'] for r in acq['decoded_files']] == list(SCANS), 'Canonical compact order differs')
    require(scope['compact_records'] == acq['decoded_files'], 'Six compact/row declarations differ')
    require([s['label'] for s in source['sources']] == list(SCANS), 'Source order differs')
    previous = float('-inf')
    for item, rec in zip(source['sources'], acq['decoded_files']):
        header = item['current_header']['data_attributes']
        require(header['tstart'] >= previous and header['tsamp'] == TSAMP
            and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF, 'Actual header/frame differs')
        previous = header['tstart'] + 16 * TSAMP / 86400
        require(rec['array_file'] == rec['scan_id'] + '.compact.h5' and rec['shape'] == [16, 1, COUNT]
            and rec['source_channel0'] == C0 and len(rec['decoded_rows']) == 16, 'Complete native source required')
    return source, acq

def tuple_details(np, result, boxes, index, truth_centers, truth_width, baseline_boxes):
    width = int(result['winning_width_channels'][index])
    drift = float(result['winning_drift_hz_s'][index])
    frequency = float(result['frequency_hz_at_tref'][index])
    absolute_base = (frequency - FCH1) / DF
    centers = np.rint(absolute_base + drift * np.arange(16) * TSAMP / DF).astype(np.int64)
    radius = width // 2
    overlap = np.maximum(0, np.minimum(centers + radius, truth_centers + truth_width // 2)
                         - np.maximum(centers - radius, truth_centers - truth_width // 2) + 1)
    local = centers - boxes[3]
    row = np.arange(16)
    baseline_score = float(baseline_boxes[0][width][0][row, local - radius].sum() / np.sqrt(16 * width))
    return {'reference_source_channel': int(result['source_reference_channels'][index]),
        'frequency_hz_at_own_first_midpoint': frequency, 'score': float(result['maximum_robust_box_track_score'][index]),
        'drift_hz_s': drift, 'width_channels': width, 'rounded_absolute_centers': centers.tolist(),
        'center_errors_channels': (centers - truth_centers).tolist(), 'overlap_channels_by_row': overlap.tolist(),
        'overlap_fraction_of_winning_box_by_row': (overlap / width).tolist(),
        'center_geometry_within_one_channel_all16': bool(np.all(np.abs(centers - truth_centers) <= 1)),
        'positive_interval_overlap_all16': bool(np.all(overlap > 0)),
        'exact_injected_width_match': width == truth_width,
        'score_at_least_operational10': float(result['maximum_robust_box_track_score'][index]) >= 10,
        'matched_zero_score_same_winning_tuple': baseline_score,
        'score_delta_same_tuple_from_zero': float(result['maximum_robust_box_track_score'][index] - baseline_score)}

def truth_score(np, boxes, centers, width):
    # Width-one cached prefix differences are the standardized point samples.
    # Width9 is evaluated only at its declared truth; it is not added to search.
    indices = centers[:, None] - boxes[3] + np.arange(-(width // 2), width // 2 + 1)[None, :]
    sums = boxes[0][1][0][np.arange(16)[:, None], indices].sum(axis=1)
    return sums, float(sums.sum() / np.sqrt(16 * width))

def run(root, scope, source, acq, job, out):
    import numpy as np
    detector = module('injection_original_detector', root / DETECTOR)
    reader = module('injection_original_reader', root / READER)
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == '1.14.6', 'HDF5 version differs')
    qs, crops, verified = JOBS[job], {}, []
    for item, record in zip(source['sources'], acq['decoded_files']):
        path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
        require(path.stat().st_size == record['bytes'] and digest(path) == record['file_sha256'], 'Compact SHA differs')
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                and data.attrs['original_source_url'] == item['url'] and data.attrs['original_source_etag'] == item['etag'],
                'Compact identity differs')
            values = data[:, 0, :]
        require(np.isfinite(values).all() and np.all(values >= 0), 'Invalid complete source power')
        for row in record['decoded_rows']:
            require(row['decoded_bytes'] == COUNT * 4 and hashlib.sha256(values[row['time_row']].tobytes()).hexdigest()
                    == row['decoded_sha256'], 'Complete decoded row SHA differs')
        for q in qs:
            crops[q, item['label']] = values[:, q * CORE - HALO:(q + 1) * CORE + HALO].astype(np.float64)
        del values
        verified.append({'scan_id': record['scan_id'], 'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16})
    cfg, drifts, times = detector.Config(widths=(1, 3)), np.linspace(-4., 4., 785), np.arange(16) * TSAMP
    maps, diagnostics, audit_paths = [], [], []
    for q in qs:
        channels = np.arange(C0 + q * CORE, C0 + (q + 1) * CORE, dtype=np.int64)
        frequencies, crop0 = FCH1 + DF * channels, C0 + q * CORE - HALO
        for item in source['sources']:
            label, header = item['label'], item['current_header']['data_attributes']
            raw = crops[q, label]
            def search(power):
                scan = detector.Scan(label, item['role'].upper(), power, header['tstart'], TSAMP, FCH1, DF, crop0, channels)
                result, arrays = detector.search_scan(scan, frequencies, times, drifts, cfg)
                result['source_reference_channels'] = channels
                require(np.all(result['valid_hypothesis_count'] == 1570)
                    and np.isfinite(result['maximum_robust_box_track_score']).all(), 'Incomplete carrier map')
                return result, arrays
            baseline, baseline_boxes = search(raw)
            def store_map(name, result):
                path = out / (name + '.npz')
                with path.open('xb') as stream:
                    np.savez(stream, **{k: v for k, v in result.items() if isinstance(v, np.ndarray)}, drift_grid_hz_s=drifts)
                norm = out / (name + '_normalization.json')
                save(norm, result['normalization'])
                rec = {'map_id': name, 'scan_id': label, 'core_q': q, 'path': path.name,
                    'sha256': digest(path), 'bytes': path.stat().st_size,
                    'normalization_path': norm.name, 'normalization_sha256': digest(norm)}
                maps.append(rec)
                print('BENCHMARK_MAP_SAVED', job, name, len(maps), flush=True)
                return rec
            baseline_id = '%s_q%03d_zero' % (label, q)
            baseline_rec = store_map(baseline_id, baseline)
            resource_guard(root, scope, out, job)
            raw_digest = hashlib.sha256(raw.tobytes()).hexdigest()
            row_level = np.asarray(baseline['normalization']['row_power_median'])
            row_scale = np.asarray(baseline['normalization']['row_residual_MAD_scale'])
            for di in DRIFT_INDICES:
                drift = float(drifts[di])
                truth_centers = np.rint(C0 + q * CORE + 2048 + drift * times / DF).astype(np.int64)
                truth_local = truth_centers - crop0
                for width in INJECT_WIDTHS:
                    support = truth_local[:, None] + np.arange(-(width // 2), width // 2 + 1)[None, :]
                    zero_sums, zero_truth_score = truth_score(np, baseline_boxes, truth_centers, width)
                    nearest = 2048
                    window = np.arange(nearest - 5, nearest + 6)
                    def choose(result, indexes):
                        return int(indexes[np.lexsort((channels[indexes], -result['maximum_robust_box_track_score'][indexes]))[0]])
                    zero_local = tuple_details(np, baseline, baseline_boxes, choose(baseline, window), truth_centers, width, baseline_boxes)
                    zero_full = tuple_details(np, baseline, baseline_boxes, choose(baseline, np.arange(CORE)), truth_centers, width, baseline_boxes)
                    for amplitude in AMPLITUDES:
                        case_id = '%s_q%03d_d%03d_w%d_A%d' % (label, q, di, width, amplitude)
                        modified = raw.copy()
                        increments = amplitude * row_level * row_scale
                        modified[np.arange(16)[:, None], support] += increments[:, None]
                        if amplitude:
                            result, boxes = search(modified)
                            map_rec = store_map(case_id, result)
                        else:
                            result, boxes, map_rec = baseline, baseline_boxes, baseline_rec
                        sums, current_truth_score = truth_score(np, boxes, truth_centers, width)
                        local = tuple_details(np, result, boxes, choose(result, window), truth_centers, width, baseline_boxes)
                        nearest_rec = tuple_details(np, result, boxes, nearest, truth_centers, width, baseline_boxes)
                        full = tuple_details(np, result, boxes, choose(result, np.arange(CORE)), truth_centers, width, baseline_boxes)
                        already = zero_local['center_geometry_within_one_channel_all16'] and zero_local['score'] >= 10
                        full_already = zero_full['center_geometry_within_one_channel_all16'] and zero_full['score'] >= 10
                        nominal = (amplitude > 0 and width == 1 and local['exact_injected_width_match']
                            and local['center_geometry_within_one_channel_all16'] and local['score'] >= 10
                            and current_truth_score > zero_truth_score and not already
                            and local['matched_zero_score_same_winning_tuple'] < 10
                            and local['score_delta_same_tuple_from_zero'] > 0)
                        full_nominal = (amplitude > 0 and width == 1 and full['exact_injected_width_match']
                            and full['center_geometry_within_one_channel_all16'] and full['score'] >= 10
                            and current_truth_score > zero_truth_score and not full_already
                            and full['matched_zero_score_same_winning_tuple'] < 10
                            and full['score_delta_same_tuple_from_zero'] > 0)
                        radius = 250 + width // 2
                        audit_indices = truth_local[:, None] + np.arange(-radius, radius + 1)[None, :]
                        audit = out / (case_id + '_truth_audit.npz')
                        with audit.open('xb') as stream:
                            np.savez(stream, baseline_raw_power=raw[np.arange(16)[:, None], audit_indices],
                                modified_raw_power=modified[np.arange(16)[:, None], audit_indices],
                                rounded_truth_centers=truth_centers, raw_power_increment_per_row=increments,
                                baseline_truth_standardized_row_box_sums=zero_sums,
                                modified_truth_standardized_row_box_sums=sums)
                        audit_paths.append({'case_id': case_id, 'path': audit.name, 'sha256': digest(audit), 'bytes': audit.stat().st_size})
                        diagnostics.append({'case_id': case_id, 'map_id': map_rec['map_id'], 'scan_id': label, 'role': item['role'],
                            'map_sha256': map_rec['sha256'], 'matched_zero_map_id': baseline_rec['map_id'],
                            'matched_zero_map_sha256': baseline_rec['sha256'],
                            'core_q': q, 'injected_drift_index': di, 'injected_drift_hz_s': drift,
                            'injected_width_channels': width, 'amplitude_per_cell_baseline_MAD_units': amplitude,
                            'truth_reference_source_channel': C0 + q * CORE + 2048,
                            'actual_first_midpoint_MJD': header['tstart'] + .5 * TSAMP / 86400,
                            'relative_row_midpoint_seconds': times.tolist(), 'rounded_truth_centers': truth_centers.tolist(),
                            'raw_power_increment_per_row': increments.tolist(),
                            'total_added_raw_power_per_row': (width * increments).tolist(),
                            'baseline_truth_score': zero_truth_score, 'modified_truth_score': current_truth_score,
                            'truth_score_delta_from_zero': current_truth_score - zero_truth_score,
                            'local_window_reference_offsets': [-5, 5], 'local_window_winner': local,
                            'nearest_reference_carrier_winner': nearest_rec, 'full_core_winner': full,
                            'matched_zero_local_window_winner': zero_local,
                            'matched_zero_full_core_winner': zero_full,
                            'local_max_score_delta_from_zero_local_max': local['score'] - zero_local['score'],
                            'zero_already_center_compatible_at_operational10': already,
                            'zero_full_core_already_center_compatible_at_operational10': full_already,
                            'local_known_truth_nominal_width1_matched_tuple_threshold_crossing_at10': nominal,
                            'full_core_rank1_nominal_width1_matched_tuple_threshold_crossing_at10': full_nominal,
                            'baseline_all_compatible_templates_below10_proven': False,
                            'width9_is_template_mismatch_stress': width == 9,
                            'nominal_width9_recovery_available_in_search_family': False,
                            'truth_audit_path': audit.name})
                        require(hashlib.sha256(raw.tobytes()).hexdigest() == raw_digest, 'Untouched baseline mutated')
                        del modified
            resource_guard(root, scope, out, job)
    save(out / 'MAPS.json', maps)
    save(out / 'DIAGNOSTICS.json', {'schema': 'SETI_RAW_POWER_INJECTION_DIAGNOSTICS_V1', 'records': diagnostics})
    save(out / 'TRUTH_AUDITS.json', audit_paths)
    require(len(maps) == len(qs) * 150 and len(diagnostics) == len(qs) * 180, 'Benchmark output counts differ')
    return {'baseline_maps': len(qs) * 6, 'modified_maps': len(qs) * 144, 'maps': len(maps),
        'diagnostic_records': len(diagnostics), 'truth_audits': len(audit_paths), 'verified_source_files': verified,
        'local_known_truth_nominal_width1_matched_tuple_threshold_crossings_at10': sum(d['local_known_truth_nominal_width1_matched_tuple_threshold_crossing_at10'] for d in diagnostics),
        'full_core_rank1_nominal_width1_matched_tuple_threshold_crossings_at10': sum(d['full_core_rank1_nominal_width1_matched_tuple_threshold_crossing_at10'] for d in diagnostics)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--scope', default=BASE + '/scope.json')
    parser.add_argument('--job', choices=tuple(JOBS), required=True)
    parser.add_argument('--scope-sha256')
    parser.add_argument('--freeze-commit')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    scope_path = confined(root, args.scope)
    scope = read_json(scope_path)
    source, acq = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_NO_NUMERICAL_IMPORTS_OR_SOURCE_OPENS', 'job': args.job,
                          'scope_sha256': digest(scope_path)}))
        return
    require(args.scope_sha256 == digest(scope_path) and re.fullmatch('[0-9a-f]{40}', args.freeze_commit or ''),
            'Exact scope SHA and public freeze commit required under root GO')
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Exact runtime differs: ' + package)
    resource_guard(root, scope, reserve=True)
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (1000, 1001))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('Wall limit1800')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    handles, out = [], None
    try:
        family = (root / BASE / 'ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        fcntl.flock(family, fcntl.LOCK_SH | fcntl.LOCK_NB)
        handles.append(family)
        for slot in range(2):
            handle = (root / BASE / ('ACTIVE_SCIENCE_SLOT_%d_FLOCK.lock' % slot)).open('a+b')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handles.append(handle)
                break
            except BlockingIOError:
                handle.close()
        else:
            raise BlockingIOError('Both science slots occupied')
        joblock = (root / BASE / (args.job + '_FLOCK.lock')).open('a+b')
        fcntl.flock(joblock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handles.append(joblock)
        out = root / BASE / 'results' / args.job
        out.mkdir(parents=True, exist_ok=False)
        counts = run(root, scope, source, acq, args.job, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256, 'Actual scope file changed during run')
        for record in acq['decoded_files']:
            path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
            require(path.stat().st_size == record['bytes'] and digest(path) == record['file_sha256'],
                    'Source compact bytes changed during run')
        allocated_final = resource_guard(root, scope, out, args.job)
        save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_RAW_POWER_INJECTION_EXECUTION_V1',
            'status': 'COMPLETE_PROSPECTIVE_RAW_POWER_INJECTION_BENCHMARK_EXPLORATORY_ONLY',
            'job': args.job, 'scope_sha256': args.scope_sha256, 'driver_sha256': digest(Path(__file__).resolve()),
            'public_freeze_commit': args.freeze_commit, 'counts': counts,
            'runtime_versions': {**VERSIONS, 'HDF5': '1.14.6'}, 'process_CPU_seconds': time.process_time() - cpu0,
            'wall_seconds': time.monotonic() - started, 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'science_slot': slot, 'CPU_cap_s': 1000, 'wall_cap_s': 1800, 'memory_cap_bytes': 2 * 1024**3,
            'workspace_allocated_bytes_final': allocated_final, 'workspace_cap_bytes': 8 * 1024**3,
            'final_scope_and_six_compact_byte_SHA256s_unchanged': True,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'new_sky_coverage': False, 'old_fixed_profiles_rerun': False, 'qualified_SETI_detection': False,
            'calibrated_SNR_FAP_or_global_completeness': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'})
    except BaseException as exc:
        if out is not None and out.is_dir() and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_RAW_POWER_INJECTION_EXECUTION_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'job': args.job,
                'scope_sha256': args.scope_sha256, 'public_freeze_commit': args.freeze_commit,
                'failure_type': type(exc).__name__, 'failure': str(exc), 'new_telescope_HTTP_requests': 0})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()

if __name__ == '__main__':
    main()
