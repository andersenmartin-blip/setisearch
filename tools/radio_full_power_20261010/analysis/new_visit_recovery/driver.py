"""Prospective one-shot S2017 native midpoint acquisition or fixed-core search.

Import/check-only opens no telescope values and makes no HTTP requests. All
96 payload descriptors must be frozen and published before either run phase.
The old detector.search_scan and gap.fixed_profiles are used without edits.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import fcntl
import hashlib
import http.client
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import threading
import time
import urllib.request

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
COUNT, CHUNK, Q, CORE, HALO = 1048576, 171, 128, 4096, 4000
C0 = CHUNK * COUNT
FIRST = C0 + Q * CORE
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
MEMORY_CAP, WALL_CAP, BODY_CAP = 4 * 1024**3, 1800, 512 * 1024**2
CPU_CAP = {'acquire': 180, 'search': 120}
STAGE = 'analysis/new_visit_recovery/results'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for raw in iter(lambda: handle.read(1024**2), b''):
            h.update(raw)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Path outside frozen workspace')
    return path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_pins(root, scope):
    for name, pin in scope['pinned_metadata_and_code'].items():
        path = confined(root, name)
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'],
                'Frozen file differs: ' + name)


def contract(root, scope):
    expected = {
        'schema': 'SETI_NEW_S2017_RETAINED27_UNATTEMPTED69_CORE128_V1', 'scan_order': list(SCANS),
        'rows_per_scan': 16, 'native_chunk_index': CHUNK, 'native_chunk_count': 343,
        'source_channel_interval_half_open': [C0, C0+COUNT], 'core_q': Q,
        'core_interval_half_open': [FIRST, FIRST+CORE],
        'crop_interval_half_open': [FIRST-HALO, FIRST+CORE+HALO],
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785},
        'widths_channels': [1, 3], 'core_channel_count': CORE, 'crop_halo_channels': HALO,
        'search_ON_maps': 3, 'valid_hypotheses_per_carrier': 1570,
        'rank_count_per_ON': 20, 'display_suppression_channels': 3,
        'fixed_profile_ranks_per_ON': 3, 'expected_fixed_profiles': 9,
        'profile_shift_channels': 0, 'profile_halfwidth_channels': 64,
        'source_workers_max': 6, 'rows_serial_per_source': 16,
        'payload_HTTP_request_cap': 96, 'payload_BODY_cap_bytes': BODY_CAP,
        'acquisition_CPU_cap_s': CPU_CAP['acquire'], 'search_CPU_cap_s': CPU_CAP['search'],
        'wall_cap_s_per_phase': WALL_CAP, 'memory_cap_bytes_per_phase': MEMORY_CAP,
        'output_stage': STAGE, 'runtime_package_versions': VERSIONS,
        'retry_resume_or_rerun_authorized': False, 'new_visit': True,
        'same_frequency_replication_of_old_Lband_cases': False,
        'blind_selection_before_fresh_values': True, 'OFF_veto_applied': False,
        'qualified_sky_detection': False, 'calibrated_SNR_FAP': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'cost_DKK': 0,
        'fixed_profile_normalization': 'full1048576-channel row median computed on raw float32, then profile float64 promotion',
    }
    require(all(scope.get(key) == value for key, value in expected.items()), 'Scope differs from implemented family')
    require(digest(__file__) == scope['driver_sha256'], 'Driver differs from prospective freeze')
    check_pins(root, scope)
    require(scope['reused_source_ranges'] == 27 and scope['previously_unattempted_source_ranges'] == 69
            and scope['original_received_BODY_bytes'] == 83845205
            and scope['original_reserved_BODY_upper_bound_bytes'] == 83845232
            and scope['exact_remaining_payload_BODY_bytes'] == 214393415
            and scope['remaining_reserved_BODY_upper_bound_bytes'] == 214393484
            and scope['original_received_BODY_bytes']+scope['exact_remaining_payload_BODY_bytes'] == 298238620,
            'Corrected continuation cumulative source accounting differs')
    source = json.loads(confined(root, scope['source_manifest_path']).read_bytes())
    require(source['native_chunk_index'] == CHUNK and
            source['physical_channel_interval_half_open'] == [C0, C0+COUNT], 'Wrong source native chunk')
    require(source['spectral_values_read'] is False and source['spectral_payload_fetched'] is False,
            'Source selection must precede fresh power values')
    items = source['sources']
    require([item['label'] for item in items] == list(SCANS) and
            [item['role'].upper() for item in items] == ['ON', 'OFF'] * 3,
            'Exactly six fixed chronological scans required')
    anchor = min(item['current_header']['data_attributes']['tstart'] for item in items)
    previous_end, total = -math.inf, 0
    for item in items:
        header, rows = item['current_header'], item['chunks']
        attrs = header['data_attributes']
        require(header['dataset_shape'] == [16, 1, 359661568]
                and header['dataset_chunks'] == [1, 1, COUNT]
                and header['dataset_dtype'] == 'float32' and header['dtype_exact'] == '<f4'
                and header['hdf5_filters'][0][:3] == [32008, 1, [0, 3, 4, 0, 2]]
                and len(header['hdf5_filters']) == 1, 'Source geometry/filter differs')
        require(attrs['fch1'] * 1e6 == FCH1 and attrs['foff'] * 1e6 == DF
                and attrs['tsamp'] == TSAMP and attrs['nchans'] == 359661568, 'Actual source grid differs')
        require(item['url'].startswith('https://bldata.berkeley.edu/pipeline/AGBT17A_999_55/holding/')
                and re.fullmatch(r'"[^"\r\n]+"', item['etag']) and item['source_file_bytes'] > 0,
                'Fixed source URL, strong ETag, and file size required')
        start = (attrs['tstart']-anchor) * 86400
        require(math.isfinite(start) and start >= previous_end, 'Actual scan times overlap or are unordered')
        previous_end = start + 16*TSAMP
        require(len(rows) == 16 and [row['time_row'] for row in rows] == list(range(16)), 'All16 source row descriptors required')
        for row in rows:
            offset, size = row['byte_offset'], row['stored_size']
            require(row['chunk_origin'] == [row['time_row'], 0, C0] and row['filter_mask'] == 0
                    and row['decoded_size'] == COUNT*4 and 0 < size <= COUNT*4
                    and offset >= 0 and offset+size <= item['source_file_bytes']
                    and row['byte_range'] == f'bytes={offset}-{offset+size-1}', 'Exact payload descriptor differs')
            total += size
    require(total == scope['exact_expected_payload_BODY_bytes']
            and total + 96 == scope['reserved_payload_BODY_upper_bound_bytes'] <= BODY_CAP,
            'Exact96-range payload exceeds or differs from frozen budget')
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Runtime version differs: ' + package)
    require(2*math.ceil(4*15*TSAMP/abs(DF))+1 == 785, 'Drift geometry differs')
    return source, float(anchor)


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_including_imports': time.monotonic()-started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}


def acquire(root, scope, source, out, started, receipt):
    module = load_module('s2017_recovery_raw_acquisition', root/scope['code_paths']['recovery_acquire'])
    return module.acquire(sys.modules[__name__], root, scope, source, out, started, receipt)


def search(root, scope, source, anchor, out, acquisition_path, expected_acquisition_sha256, freeze_commit):
    require(re.fullmatch('[0-9a-f]{64}', expected_acquisition_sha256 or '')
            and digest(acquisition_path) == expected_acquisition_sha256, 'Root-reviewed successful acquisition SHA required')
    acquisition = json.loads(Path(acquisition_path).read_bytes())
    require(acquisition['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
            and acquisition['phase'] == 'acquire' and acquisition['driver_sha256'] == scope['driver_sha256']
            and acquisition['public_freeze_commit'] == freeze_commit
            and acquisition['new_telescope_HTTP_requests'] == 69
            and acquisition['total_cumulative_telescope_HTTP_requests'] == 96
            and acquisition['source_range_count_authenticated'] == 96
            and acquisition['new_telescope_BODY_bytes'] == scope['exact_remaining_payload_BODY_bytes']
            and acquisition['cumulative_telescope_BODY_bytes'] == scope['exact_expected_payload_BODY_bytes']
            and acquisition['cumulative_reserved_BODY_upper_bound_bytes'] == scope['reserved_payload_BODY_upper_bound_bytes']
            and acquisition['complete_compact_files'] == 6 and acquisition['decoded_row_SHA256s'] == 96
            and acquisition['source_manifest_sha256'] == scope['pinned_metadata_and_code'][scope['source_manifest_path']]['sha256']
            and acquisition['scope_sha256'] == digest(root/'analysis/new_visit_recovery/scope.json')
            and [record['scan_id'] for record in acquisition['decoded_files']] == list(SCANS),
            'Complete same-frozen-family acquisition required')
    import numpy as np
    reader = load_module('s2017_search_standard_reader', root/scope['code_paths']['reader'])
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == scope['hdf5_version'], 'Search HDF5 version differs')
    arrays, verified = {}, []
    acquisition_directory = Path(acquisition_path).resolve().parent
    require(acquisition_directory == root/STAGE/'acquire', 'Wrong acquisition directory')
    for record in acquisition['decoded_files']:
        label, path = record['scan_id'], acquisition_directory/record['array_file']
        identity = next(item for item in source['sources'] if item['label'] == label)
        require(path.parent == acquisition_directory and path.stat().st_size == record['bytes']
                and digest(path) == record['file_sha256'], 'Compact source file pin differs')
        require(record['shape'] == [16, 1, COUNT] and record['source_channel0'] == C0
                and [row['time_row'] for row in record['decoded_rows']] == list(range(16)), 'Compact source row metadata differs')
        with h5py.File(path, 'r', rdcc_nbytes=8*1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                    and data.attrs['original_source_url'] == identity['url']
                    and data.attrs['original_source_etag'] == identity['etag'], 'Compact native frame or source identity differs')
            values = data[:, 0, :]
        require(np.isfinite(values).all() and (values >= 0).all(), 'Invalid compact native power')
        for row in record['decoded_rows']:
            require(row['decoded_bytes'] == COUNT*4 and
                    hashlib.sha256(values[row['time_row']].tobytes(order='C')).hexdigest() == row['decoded_sha256'],
                    'Full-native decoded row SHA differs')
        arrays[label] = values
        verified.append({'scan_id': label, 'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16})
    normalization = {'source_channel0': C0, 'count': COUNT,
        'row_power_medians': {label: np.median(arrays[label], axis=1).tolist() for label in SCANS},
        'method': scope['fixed_profile_normalization'], 'raw_dtype': '<f4'}
    save(out/'NORMALIZATION.json', normalization)
    detector = load_module('s2017_unchanged_detector', root/scope['code_paths']['detector'])
    cfg = detector.Config(widths=(1, 3))
    drifts, dt = np.linspace(-4.0, 4.0, 785), np.arange(16)*TSAMP
    mismatch = float((drifts[1]-drifts[0])*dt[-1]/(2*abs(DF)))
    require(mismatch <= .5+1e-12, 'Drift grid exceeds half-channel mismatch')
    channels = np.arange(FIRST, FIRST+CORE)
    frequencies = FCH1+DF*channels
    crop0, cropstop = Q*CORE-HALO, (Q+1)*CORE+HALO
    tops, receipts = {}, []
    for label in ONS:
        header = next(item['current_header']['data_attributes'] for item in source['sources'] if item['label'] == label)
        scan = detector.Scan(label, 'ON', arrays[label][:, crop0:cropstop], header['tstart'], TSAMP,
                             FCH1, DF, C0+crop0, channels)
        result, _ = detector.search_scan(scan, frequencies, dt, drifts, cfg)
        require(np.isfinite(result['maximum_robust_box_track_score']).all()
                and np.all(result['valid_hypothesis_count'] == 1570), 'Incomplete fixed-core ON search')
        numeric = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
        numeric.update(source_reference_channels=channels, drift_grid_hz_s=drifts)
        path = out/(label+'_core128_all_carriers.npz')
        np.savez(path, **numeric)
        receipts.append({'scan_id': label, 'path': path.name, 'sha256': digest(path), 'bytes': path.stat().st_size,
            'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 1570,
            'reference_channel_interval_half_open': [FIRST, FIRST+CORE], 'normalization': result['normalization']})
        save(out/'DRIFT_CHECKPOINT.json', {'completed_ON_maps': len(receipts), 'expected_ON_maps': 3,
                                         'complete': len(receipts) == 3, 'receipts': receipts})
        score = result['maximum_robust_box_track_score']
        chosen = []
        for index in np.lexsort((channels, -score)):
            index = int(index)
            if all(abs(int(channels[index])-int(channels[other])) > 3 for other in chosen):
                chosen.append(index)
            if len(chosen) == 20:
                break
        require(len(chosen) == 20, 'Incomplete top20 display family')
        reference = (header['tstart']-anchor)*86400+.5*TSAMP
        tops[label] = [{'track_id': label+'_visit20170428_Sband_core128_rank_%02d' % rank,
            'family': 'S2017_native_midpoint_fixed_core128', 'originating_scan': label, 'originating_role': 'ON',
            'display_rank': rank, 'source_reference_channel': int(channels[index]),
            'reference_frequency_hz': float(frequencies[index]), 'reference_seconds_from_anchor': float(reference),
            'drift_hz_s': float(result['winning_drift_hz_s'][index]),
            'width_channels': int(result['winning_width_channels'][index]),
            'maximum_robust_box_track_score': float(score[index]), 'reference_core_tile': 0,
            'status': 'EXPLORATORY_RANK_UNCLASSIFIED'} for rank, index in enumerate(chosen, 1)]
        save(out/'DRIFT_TOP20.json', tops)
        print('SEARCHED_S2017_ON_CORE128', label, flush=True)
    gap = load_module('s2017_unchanged_gap_profiles', root/scope['code_paths']['gap'])
    gap.ROOT, gap.np = root, np
    gap.FCH1, gap.DF, gap.TSAMP, gap.C0, gap.COUNT = FCH1, DF, TSAMP, C0, COUNT
    gap.NORMALIZATION_PATH = (out/'NORMALIZATION.json').relative_to(root).as_posix()
    profiles = gap.fixed_profiles(arrays, source, normalization, tops, anchor, out)
    require(profiles['profile_count'] == 9, 'Incomplete fixed nine-profile family')
    require(digest(acquisition_path) == expected_acquisition_sha256, 'Acquisition receipt changed during search')
    for record in acquisition['decoded_files']:
        require(digest(acquisition_directory/record['array_file']) == record['file_sha256'], 'Compact input changed during search')
    return {'verified_inputs': verified, 'acquisition_receipt_sha256': expected_acquisition_sha256,
            'search_summary': {'completed_ON_maps': 3, 'carriers_per_ON': CORE, 'drift_grid_count': 785,
                'widths_channels': [1, 3], 'half_grid_mismatch_channels': mismatch,
                'bandwidth_per_ON_hz': CORE*abs(DF), 'native_chunk_fraction_searched': CORE/COUNT,
                'reference_time': 'each ON first integration midpoint; six-scan profiles use actual header epochs',
                'score_definition': 'unchanged row-MAD-standardized odd-box track sum/sqrt(Nrow*width)',
                'normalization': 'unchanged each4096-carrier row core and501-channel filter'},
            'fixed_profile_summary': profiles, 'MJD_anchor': anchor,
            'runtime_versions': {**VERSIONS, 'HDF5': h5py.version.hdf5_version},
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--phase', choices=('acquire', 'search'), required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--root-go-after-review', action='store_true')
    parser.add_argument('--acquisition-receipt')
    parser.add_argument('--expected-acquisition-sha256')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual public prospective freeze commit required')
    require(Path(args.scope).resolve() == root/'analysis/new_visit_recovery/scope.json', 'Scope must use frozen fixed path')
    require(digest(args.scope) == args.expected_scope_sha256, 'Scope differs from public prospective freeze')
    scope = json.loads(Path(args.scope).read_bytes())
    source, anchor = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_CODE_ONLY_NO_VALUES_NO_HTTP', 'phase': args.phase,
                          'scope_sha256': args.expected_scope_sha256, 'exact96_range_payload_bytes': scope['exact_expected_payload_BODY_bytes']}))
        return
    require(args.root_go_after_review, 'Root GO after prospective review and public readback required')
    require(args.phase != 'search' or args.acquisition_receipt, 'Search requires reviewed acquisition receipt')
    out = root/STAGE/args.phase
    out.mkdir(parents=True, exist_ok=False)
    receipt = {'status': 'IN_PROGRESS', 'phase': args.phase, 'scope_sha256': args.expected_scope_sha256,
        'driver_sha256': digest(__file__), 'public_freeze_commit': args.freeze_commit,
        'source_manifest_sha256': digest(root/scope['source_manifest_path']),
        'new_visit': True, 'same_frequency_replication_of_old_Lband_cases': False,
        'blind_source_selection_before_original_value_opening': True,
        'source_values_already_opened_in_original_failed_family': True,
        'previously_decoded_rows': 26, 'scientific_search_previously_run': False,
        'qualified_sky_detection': False,
        'OFF_veto_applied': False, 'calibrated_SNR_FAP': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'retry_resume_or_rerun_authorized': False,
        'CPU_cap_s': CPU_CAP[args.phase], 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
        'cost_DKK': 0, 'limitations': scope['limitations']}
    filename = 'ACQUISITION_RESULT.json' if args.phase == 'acquire' else 'EXECUTION_RECEIPT.json'
    lock = root/STAGE/'ACTIVE_FAMILY_FLOCK.lock'
    lock_handle = None
    def deadline(signum, frame):
        raise TimeoutError('Frozen phase CPU/wall limit reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP[args.phase], CPU_CAP[args.phase]+1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(max(1, int(WALL_CAP-(time.monotonic()-started))))
    try:
        lock_handle = lock.open('a+')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
        lock_handle.seek(0)
        lock_handle.truncate()
        lock_handle.write(args.phase+'\n')
        lock_handle.flush()
        save(out/'INPUT_PINS.json', {'scope_sha256': args.expected_scope_sha256,
             'public_freeze_commit': args.freeze_commit, 'pinned_metadata_and_code': scope['pinned_metadata_and_code']})
        save(out/filename, receipt)
        if args.phase == 'acquire':
            summary = acquire(root, scope, source, out, started, receipt)
        else:
            summary = search(root, scope, source, anchor, out, args.acquisition_receipt,
                             args.expected_acquisition_sha256, args.freeze_commit)
        check_pins(root, scope)
        require(digest(args.scope) == args.expected_scope_sha256, 'Scope changed during phase')
        use = measured(started)
        require(use['process_CPU_seconds_including_imports'] <= CPU_CAP[args.phase]
                and use['wall_seconds_including_imports'] <= WALL_CAP and use['peak_RSS_bytes'] <= MEMORY_CAP,
                'Measured phase resource cap exceeded')
        receipt.update(summary, **use, status=('COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
            if args.phase == 'acquire' else 'COMPLETE_NEW_S2017_THREE_CORE_MAPS_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY'))
        if args.phase == 'acquire':
            ledger = json.loads((out/'SOURCE_BODY_LEDGER.json').read_bytes())
            ledger.update(complete=True, completion_resource_guard={'status':'PASS_BEFORE_COMPLETE', **use})
            save(out/'SOURCE_BODY_LEDGER.json', ledger)
        save(out/filename, receipt)
        print(json.dumps({key: receipt[key] for key in ('status', 'phase', *use)}), flush=True)
    except BaseException as error:
        receipt.update(status='INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',
                       error_type=type(error).__name__, error=str(error), **measured(started))
        save(out/filename, receipt)
        save(out/'FAILURE_RECEIPT.json', receipt)
        raise
    finally:
        signal.alarm(0)
        if lock_handle is not None:
            lock_handle.close()


if __name__ == '__main__':
    main()
