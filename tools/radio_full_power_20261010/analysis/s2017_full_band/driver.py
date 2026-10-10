"""Frozen zero-download S2017 interior-core extension, one disjoint batch.

Import, scope preparation, and --check-only read metadata/code/receipt JSON
only. Actual science requires complete corrected acquisition, complete q128
search, its actual independent saved-output/source QA PASS, public readback,
and root GO. No failed namespace is reused and q128 is never searched here.
Numerical detector.search_scan and gap.fixed_profiles are unchanged imports.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
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
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
COUNT, CHUNK, CORE, HALO = 1048576, 171, 4096, 4000
C0 = CHUNK * COUNT
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP = 1000, 1800
PROCESS_RAM_CAP, AGGREGATE_RAM_CAP, MAX_JOBS = 2 * 1024**3, 4 * 1024**3, 2
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
UNCHANGED_DEPENDENCY_SHAS = {
    'detector': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'gap': 'b1a2cc31d47dbebc707f36c5de3eafbae6a62f0d0d19061c798c676c9fbcdb58',
    'reader': '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}
STAGE = 'analysis/s2017_full_band/results'
RECOVERY_STAGE = 'analysis/new_visit_recovery/results'
RECOVERY_SCOPE = 'analysis/new_visit_recovery/scope.json'
FULLNORM = 'full1048576-channel row median computed on raw float32, then profile float64 promotion'
SAFE_Q = tuple(q for q in range(1, 255) if q != 128)
BATCHES = {'batch01': SAFE_Q[:84], 'batch02': SAFE_Q[84:168], 'batch03': SAFE_Q[168:]}
QA_COUNTS = {'maps': 3, 'map_normalization_records': 3, 'carrier_maximum_records': 12288,
    'valid_hypothesis_records': 19292160, 'top20_entries': 60, 'patches': 9,
    'scan_profiles': 54, 'time_row_occurrences': 864, 'retained_raw_patch_cells': 111456,
    'compact_files': 6, 'compressed_source_chunks': 96, 'decoded_rows': 96,
    'native_row_medians_recomputed': 96, 'ON_core_row_medians_recomputed': 48,
    'raw_cells_bitwise_checked': 111456, 'durable_raw_sidecars': 96,
    'preserved_prior_decoded_rows_matched': 26}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
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


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Relative confined path required')
    path = root / relative
    require(path.resolve().is_relative_to(root), 'Path outside frozen workspace')
    return path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_pins(root, scope):
    for name, pin in scope['pinned_metadata_code_and_prerequisites'].items():
        path = confined(root, name)
        require(path.suffix.lower() not in ('.h5', '.hdf5', '.npy', '.npz'), 'Preflight may not open power files')
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Frozen file differs: ' + name)


def prerequisite_contract(root, scope):
    gates = scope['prerequisites']
    expected_paths = {'acquisition': RECOVERY_STAGE + '/acquire/ACQUISITION_RESULT.json',
        'q128_search': RECOVERY_STAGE + '/search/EXECUTION_RECEIPT.json',
        'q128_QA': RECOVERY_STAGE + '/review/QA_RECEIPT.json'}
    values = {}
    for key, expected in expected_paths.items():
        gate = gates[key]
        require(gate['path'] == expected and re.fullmatch('[0-9a-f]{64}', gate['sha256']), 'Wrong prerequisite path/SHA')
        path = confined(root, gate['path'])
        require(digest(path) == gate['sha256'], 'Reviewed prerequisite changed: ' + key)
        values[key] = json.loads(path.read_bytes())
        require(values[key]['status'] == gate['status'], 'Reviewed prerequisite status changed')
    acquisition, result, qa = (values[key] for key in expected_paths)
    recovery = json.loads(confined(root, RECOVERY_SCOPE).read_bytes())
    recovery_sha = digest(root / RECOVERY_SCOPE)
    source_sha = digest(confined(root, scope['source_manifest_path']))
    freeze = acquisition['public_freeze_commit']
    require(re.fullmatch('[0-9a-f]{40}', freeze), 'Actual corrected acquisition public freeze required')
    require(recovery['schema'] == 'SETI_NEW_S2017_RETAINED27_UNATTEMPTED69_CORE128_V1'
        and recovery['output_stage'] == RECOVERY_STAGE and recovery['core_q'] == 128
        and recovery['driver_sha256'] == digest(confined(root, 'analysis/new_visit_recovery/driver.py')),
        'Corrected acquisition and original q128 family required')
    require(acquisition['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
        and acquisition['phase'] == 'acquire' and acquisition['scope_sha256'] == recovery_sha
        and acquisition['driver_sha256'] == recovery['driver_sha256']
        and acquisition['source_manifest_sha256'] == source_sha
        and acquisition['new_telescope_HTTP_requests'] == 69
        and acquisition['total_cumulative_telescope_HTTP_requests'] == 96
        and acquisition['source_range_count_authenticated'] == 96
        and acquisition['new_telescope_BODY_bytes'] == recovery['exact_remaining_payload_BODY_bytes']
        and acquisition['cumulative_telescope_BODY_bytes'] == 298238620
        and acquisition['cumulative_reserved_BODY_upper_bound_bytes'] == 298238716
        and acquisition['complete_compact_files'] == 6 and acquisition['decoded_row_SHA256s'] == 96
        and [record['scan_id'] for record in acquisition['decoded_files']] == list(SCANS),
        'Complete corrected 96-row acquisition required before extension')
    require(result['status'] == 'COMPLETE_NEW_S2017_THREE_CORE_MAPS_AND_NINE_FIXED_PROFILES_EXPLORATORY_ONLY'
        and result['phase'] == 'search' and result['scope_sha256'] == recovery_sha
        and result['driver_sha256'] == recovery['driver_sha256'] and result['public_freeze_commit'] == freeze
        and result['acquisition_receipt_sha256'] == gates['acquisition']['sha256']
        and result['source_manifest_sha256'] == source_sha
        and result['search_summary']['completed_ON_maps'] == 3
        and result['search_summary']['carriers_per_ON'] == CORE
        and result['search_summary']['drift_grid_count'] == 785
        and result['search_summary']['widths_channels'] == [1, 3]
        and result['fixed_profile_summary']['profile_count'] == 9
        and result['new_telescope_HTTP_requests'] == result['new_telescope_BODY_bytes'] == 0,
        'Completed q128 search required; extension never replaces or reruns it')
    require(qa['schema'] == 'SETI_S2017_SAVED_OUTPUT_AND_SOURCE_QA_V1'
        and qa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
        and qa['counts'] == QA_COUNTS
        and qa['scope_sha256'] == recovery_sha and qa['driver_sha256'] == recovery['driver_sha256']
        and qa['public_freeze_commit'] == freeze
        and qa['acquisition_receipt_sha256'] == gates['acquisition']['sha256']
        and qa['search_receipt_sha256'] == gates['q128_search']['sha256']
        and qa['detector_or_score_rerun'] is False and qa['fixed_track_optimization_applied'] is False
        and qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0,
        'Actual complete q128 saved-output/source QA PASS required')
    original = json.loads(confined(root, 'analysis/new_visit_search/results/acquire/FAILURE_RECEIPT.json').read_bytes())
    require(original['status'] == 'INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',
            'Original failed acquisition namespace must stay failed and preserved')
    return acquisition


def contract(root, scope):
    batch = scope['batch_id']
    require(batch in BATCHES, 'Unknown frozen disjoint batch')
    qs = list(BATCHES[batch])
    expected = {'schema': 'SETI_S2017_SAFE_INTERIOR_EXTENSION_V1', 'batch_id': batch,
        'core_q_indices': qs, 'scan_order': list(SCANS), 'rows_per_scan': 16,
        'native_chunk_index': CHUNK, 'native_chunk_count': 343,
        'source_channel_interval_half_open': [C0, C0 + COUNT], 'excluded_previously_searched_q': [128],
        'excluded_edge_q': [0, 255], 'core_channel_count': CORE, 'crop_halo_channels': HALO,
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}, 'widths_channels': [1, 3],
        'valid_hypotheses_per_carrier': 1570, 'search_ON_maps': 3 * len(qs),
        'rank_count_per_ON_per_batch': 20, 'display_suppression_channels': 3,
        'top20_selection_domain': 'all saved carrier maxima from all cores of this batch, separately for each ON',
        'fixed_profile_ranks_per_ON_per_batch': 3, 'expected_fixed_profiles': 9,
        'profile_shift_channels': 0, 'profile_halfwidth_channels': 64,
        'fixed_profile_normalization': FULLNORM, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
        'memory_cap_bytes_per_process': PROCESS_RAM_CAP, 'memory_cap_bytes_aggregate': AGGREGATE_RAM_CAP,
        'simultaneous_extension_jobs_max': MAX_JOBS, 'runtime_package_versions': VERSIONS,
        'hdf5_version': '1.14.6', 'output_stage': STAGE + '/' + batch,
        'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
        'new_visit': False, 'new_acquisition': False, 'independent_tests_claimed': False,
        'original_q128_search_rerun': False, 'retry_resume_or_rerun_authorized': False,
        'blind_selection_before_fresh_values': False, 'OFF_veto_applied': False,
        'qualified_sky_detection': False, 'calibrated_SNR_FAP': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
    require(all(scope.get(key) == value for key, value in expected.items()), 'Scope differs from implemented batch')
    require(digest(__file__) == scope['driver_sha256'], 'Driver differs from public prospective freeze')
    check_pins(root, scope)
    require(scope['unchanged_original_dependency_SHA256s'] == UNCHANGED_DEPENDENCY_SHAS
        and set(scope['code_paths']) == set(UNCHANGED_DEPENDENCY_SHAS)
        and all(digest(confined(root, scope['code_paths'][key])) == sha
                for key, sha in UNCHANGED_DEPENDENCY_SHAS.items()),
        'Detector, fixed profiles, and reader numerical dependencies must remain byte-for-byte unchanged')
    acquisition = prerequisite_contract(root, scope)
    source = json.loads(confined(root, scope['source_manifest_path']).read_bytes())
    require(source['native_chunk_index'] == CHUNK
        and source['physical_channel_interval_half_open'] == [C0, C0 + COUNT]
        and [item['label'] for item in source['sources']] == list(SCANS), 'Wrong source chunk/scans')
    anchor = min(item['current_header']['data_attributes']['tstart'] for item in source['sources'])
    times = []
    for item in source['sources']:
        header, attrs = item['current_header'], item['current_header']['data_attributes']
        require(header['dataset_shape'] == [16, 1, 359661568] and header['dataset_chunks'] == [1, 1, COUNT]
            and header['dtype_exact'] == '<f4' and attrs['fch1'] * 1e6 == FCH1
            and attrs['foff'] * 1e6 == DF and attrs['tsamp'] == TSAMP
            and len(item['chunks']) == 16, 'Verified source geometry/grid differs')
        times.extend(((attrs['tstart'] - anchor) * 86400 + (row + .5) * TSAMP for row in range(16)))
    max_profile_displacement = math.ceil(4 * (max(times) - min(times)) / abs(DF)) + 64
    require(max_profile_displacement < CORE and 2 * math.ceil(4 * 15 * TSAMP / abs(DF)) + 1 == 785,
            'Frozen full six-scan profiles or own drift family lack native support')
    require(all(1 <= q <= 254 and q != 128 for q in qs), 'Previously searched or edge core admitted')
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Runtime package differs: ' + package)
    return source, float(anchor), acquisition


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds_including_imports': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def search(root, scope, source, anchor, acquisition, out):
    import numpy as np
    reader = load_module('s2017_extension_reader', confined(root, scope['code_paths']['reader']))
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == scope['hdf5_version'], 'HDF5 version differs')
    arrays, verified = {}, []
    acquire = root / RECOVERY_STAGE / 'acquire'
    for record in acquisition['decoded_files']:
        label = record['scan_id']
        require(record['array_file'] == label + '.compact.h5' and record['shape'] == [16, 1, COUNT]
            and record['source_channel0'] == C0
            and [row['time_row'] for row in record['decoded_rows']] == list(range(16)), 'Compact row/frame metadata differs')
        path = confined(acquire, record['array_file'])
        require(path.stat().st_size == record['bytes'] and digest(path) == record['file_sha256'], 'Compact file pin differs')
        item = next(item for item in source['sources'] if item['label'] == label)
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                and data.attrs['original_source_url'] == item['url']
                and data.attrs['original_source_etag'] == item['etag'], 'Compact source identity differs')
            values = data[:, 0, :]
        require(np.isfinite(values).all() and (values >= 0).all(), 'Invalid full native power')
        for row in record['decoded_rows']:
            require(row['decoded_bytes'] == COUNT * 4 and
                hashlib.sha256(values[row['time_row']].tobytes(order='C')).hexdigest() == row['decoded_sha256'],
                'Authenticated full-native decoded row SHA differs')
        arrays[label] = values
        verified.append({'scan_id': label, 'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16})
    normalization = {'source_channel0': C0, 'count': COUNT,
        'row_power_medians': {label: np.median(arrays[label], axis=1).tolist() for label in SCANS},
        'method': FULLNORM, 'raw_dtype': '<f4'}
    save(out / 'NORMALIZATION.json', normalization)
    detector = load_module('s2017_extension_unchanged_detector', confined(root, scope['code_paths']['detector']))
    cfg = detector.Config(widths=(1, 3))
    drifts, dt = np.linspace(-4.0, 4.0, 785), np.arange(16) * TSAMP
    mismatch = float((drifts[1] - drifts[0]) * dt[-1] / (2 * abs(DF)))
    require(mismatch <= .5 + 1e-12, 'Own drift grid exceeds half-channel mismatch')
    qs, tops, receipts = scope['core_q_indices'], {}, []
    for label in ONS:
        header = next(item['current_header']['data_attributes'] for item in source['sources'] if item['label'] == label)
        columns = {'channels': [], 'scores': [], 'drifts': [], 'widths': [], 'qs': []}
        for q in qs:
            first, crop0, cropstop = C0 + q * CORE, q * CORE - HALO, (q + 1) * CORE + HALO
            channels = np.arange(first, first + CORE)
            frequencies = FCH1 + DF * channels
            scan = detector.Scan(label, 'ON', arrays[label][:, crop0:cropstop], header['tstart'], TSAMP,
                FCH1, DF, C0 + crop0, channels)
            result, _ = detector.search_scan(scan, frequencies, dt, drifts, cfg)
            score = result['maximum_robust_box_track_score']
            require(np.isfinite(score).all() and np.all(result['valid_hypothesis_count'] == 1570), 'Incomplete ON core map')
            numeric = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
            numeric.update(source_reference_channels=channels, drift_grid_hz_s=drifts)
            path = out / (label + '_q%03d_all_carriers.npz' % q)
            np.savez(path, **numeric)
            normalization_path = out / (label + '_q%03d_normalization.json' % q)
            save(normalization_path, result['normalization'])
            receipts.append({'scan_id': label, 'core_q': q, 'path': path.name,
                'sha256': digest(path), 'bytes': path.stat().st_size, 'searched_carriers': CORE,
                'valid_hypotheses_per_carrier': 1570,
                'reference_channel_interval_half_open': [first, first + CORE],
                'normalization': {'path': normalization_path.name, 'sha256': digest(normalization_path),
                                  'bytes': normalization_path.stat().st_size}})
            for key, value in (('channels', channels), ('scores', score), ('drifts', result['winning_drift_hz_s']),
                ('widths', result['winning_width_channels']), ('qs', np.full(CORE, q, dtype=np.int16))):
                columns[key].append(value)
            save(out / 'DRIFT_CHECKPOINT.json', {'completed_ON_maps': len(receipts), 'expected_ON_maps': 3 * len(qs),
                'complete': len(receipts) == 3 * len(qs), 'receipts': receipts})
            print('SEARCHED_S2017_NEW_INTERIOR_CORE', scope['batch_id'], label, q, flush=True)
        columns = {key: np.concatenate(value) for key, value in columns.items()}
        chosen = []
        for index in np.lexsort((columns['channels'], -columns['scores'])):
            index = int(index)
            if all(abs(int(columns['channels'][index]) - int(columns['channels'][other])) > 3 for other in chosen):
                chosen.append(index)
            if len(chosen) == 20:
                break
        require(len(chosen) == 20, 'Incomplete global per-batch top20')
        reference = (header['tstart'] - anchor) * 86400 + .5 * TSAMP
        tops[label] = [{'track_id': label + '_visit20170428_Sband_' + scope['batch_id'] + '_rank_%02d' % rank,
            'family': 'S2017_native171_safe_interior_extension_' + scope['batch_id'],
            'originating_scan': label, 'originating_role': 'ON', 'display_rank': rank,
            'source_reference_channel': int(columns['channels'][index]),
            'reference_frequency_hz': float(FCH1 + DF * columns['channels'][index]),
            'reference_seconds_from_anchor': float(reference), 'drift_hz_s': float(columns['drifts'][index]),
            'width_channels': int(columns['widths'][index]),
            'maximum_robust_box_track_score': float(columns['scores'][index]),
            'reference_core_tile': int(columns['qs'][index]), 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'}
            for rank, index in enumerate(chosen, 1)]
        save(out / 'DRIFT_TOP20.json', tops)
        del columns
    gap = load_module('s2017_extension_unchanged_profiles', confined(root, scope['code_paths']['gap']))
    gap.ROOT, gap.np = root, np
    gap.FCH1, gap.DF, gap.TSAMP, gap.C0, gap.COUNT = FCH1, DF, TSAMP, C0, COUNT
    gap.NORMALIZATION_PATH = (out / 'NORMALIZATION.json').relative_to(root).as_posix()
    profiles = gap.fixed_profiles(arrays, source, normalization, tops, anchor, out)
    require(profiles['profile_count'] == 9, 'Incomplete fixed nine-profile batch family')
    for record in acquisition['decoded_files']:
        require(digest(acquire / record['array_file']) == record['file_sha256'], 'Native input changed during search')
    return {'verified_inputs': verified, 'MJD_anchor': anchor,
        'acquisition_receipt_sha256': scope['prerequisites']['acquisition']['sha256'],
        'q128_search_receipt_sha256': scope['prerequisites']['q128_search']['sha256'],
        'q128_QA_receipt_sha256': scope['prerequisites']['q128_QA']['sha256'],
        'search_summary': {'completed_ON_maps': len(receipts), 'cores_per_ON': len(qs),
            'carriers_per_ON': len(qs) * CORE, 'ON_carrier_maximum_records': 3 * len(qs) * CORE,
            'correlated_drift_width_combinations': 3 * len(qs) * CORE * 1570,
            'drift_grid_count': 785, 'widths_channels': [1, 3], 'half_grid_mismatch_channels': mismatch,
            'bandwidth_per_ON_hz': len(qs) * CORE * abs(DF), 'native_chunk_fraction_searched': len(qs) * CORE / COUNT,
            'score_definition': 'unchanged row-MAD-standardized odd-box track sum/sqrt(Nrow*width)',
            'normalization': 'unchanged separate4096-carrier core per map and501-channel filter',
            'reference_time': 'each ON first integration midpoint; actual header epochs for fixed six-scan profiles'},
        'fixed_profile_summary': profiles, 'top20_entries': 60,
        'runtime_versions': {**VERSIONS, 'HDF5': h5py.version.hdf5_version}}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--root-go-after-review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual prospective public freeze commit required')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_scope_sha256)
        and digest(args.scope) == args.expected_scope_sha256, 'Frozen scope SHA differs')
    scope = json.loads(Path(args.scope).read_bytes())
    require(Path(args.scope).resolve() == root / 'analysis/s2017_full_band/scopes' / (scope['batch_id'] + '.json'),
            'Wrong frozen batch scope path')
    source, anchor, acquisition = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_CODE_PREREQUISITES_ONLY_NO_VALUES_NO_HTTP',
            'batch_id': scope['batch_id'], 'scope_sha256': args.expected_scope_sha256,
            'cores_per_ON': len(scope['core_q_indices']), 'new_telescope_HTTP_requests': 0}))
        return
    require(args.root_go_after_review, 'Root prospective review, public readback, and GO required')
    stage = root / STAGE
    stage.mkdir(parents=True, exist_ok=True)
    out = confined(root, scope['output_stage'])
    handles, slot_index, receipt = [], None, None
    def deadline(signum, frame):
        raise TimeoutError('Frozen extension CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (PROCESS_RAM_CAP, PROCESS_RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        # Retained lock files are intentional; kernel ownership is released on close.
        batch_lock = (stage / (scope['batch_id'] + '_ACTIVE_FLOCK.lock')).open('a+b')
        handles.append(batch_lock)
        fcntl.flock(batch_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_lock = (root / RECOVERY_STAGE / 'ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        handles.append(source_lock)
        fcntl.flock(source_lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        for i in range(MAX_JOBS):
            slot = (stage / ('ACTIVE_SCIENCE_SLOT_%d_FLOCK.lock' % i)).open('a+b')
            try:
                fcntl.flock(slot.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                slot.close()
            else:
                handles.append(slot)
                slot_index = i
                break
        require(slot_index is not None, 'At most two extension jobs admitted; no hidden waiting or extra memory')
        out.mkdir(parents=True, exist_ok=False)
        receipt = {'status': 'IN_PROGRESS', 'phase': 'previously_unsearched_interior_batch',
            'batch_id': scope['batch_id'], 'scope_sha256': args.expected_scope_sha256,
            'driver_sha256': digest(__file__), 'public_freeze_commit': args.freeze_commit,
            'source_manifest_sha256': digest(confined(root, scope['source_manifest_path'])),
            'core_q_indices': scope['core_q_indices'], 'simultaneous_job_slot': slot_index,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes_per_process': PROCESS_RAM_CAP,
            'memory_cap_bytes_aggregate': AGGREGATE_RAM_CAP, 'simultaneous_extension_jobs_max': MAX_JOBS,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'new_visit': False, 'new_acquisition': False, 'original_q128_search_rerun': False,
            'independent_tests_claimed': False, 'qualified_sky_detection': False, 'OFF_veto_applied': False,
            'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
            'retry_resume_or_rerun_authorized': False, 'limitations': scope['limitations']}
        save(out / 'INPUT_PINS.json', {'scope_sha256': args.expected_scope_sha256,
            'public_freeze_commit': args.freeze_commit, 'pins': scope['pinned_metadata_code_and_prerequisites']})
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        summary = search(root, scope, source, anchor, acquisition, out)
        check_pins(root, scope)
        require(digest(args.scope) == args.expected_scope_sha256, 'Frozen scope changed during execution')
        use = measured(started)
        require(use['process_CPU_seconds_including_imports'] <= CPU_CAP and use['wall_seconds_including_imports'] <= WALL_CAP
            and use['peak_RSS_bytes'] <= PROCESS_RAM_CAP, 'Measured process resource cap exceeded')
        receipt.update(summary, **use, status='COMPLETE_S2017_PREVIOUSLY_UNSEARCHED_INTERIOR_BATCH_EXPLORATORY_ONLY')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'batch_id': scope['batch_id'], **use}), flush=True)
    except BaseException as error:
        if receipt is not None:
            receipt.update(status='INCOMPLETE_BATCH_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',
                error_type=type(error).__name__, error=str(error), **measured(started))
            save(out / 'EXECUTION_RECEIPT.json', receipt)
            save(out / 'FAILURE_RECEIPT.json', receipt)
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
