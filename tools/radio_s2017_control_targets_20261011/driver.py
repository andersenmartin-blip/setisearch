"""Frozen original OFF pointings as three distinct primary targets.

Import and --check-only use standard-library text metadata only. Each actual
job searches its own previously acquired compact exactly once per eligible
core, without changing its acquisition role or inventing repeated visits.
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
BASE = 'analysis/s2017_control_targets_20261011'
PROPOSAL = 'continuation_20261011/metadata/control_target_sweep/SCIENTIFIC_SCOPE_PROPOSAL.json'
SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ACQ = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
SOURCE_QA = 'analysis/new_visit_recovery/results/review/QA_RECEIPT.json'
FULL_QA = 'analysis/s2017_full_band/results/review/QA_RECEIPT.json'
INJECTION_QA = 'analysis/s2017_injection_20261011/results/review/QA_RECEIPT.json'
RESTORED = 'continuation_20261011/recovery/NATIVE171_OPAQUE_RESTORATION_RECEIPT.json'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
READER = 'analysis/new_visit_search/dependencies/standard_reader.py'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
JOBS = {'primary20170428_HIP97319': ('epoch1_off', 'HIP97319'),
        'primary20170428_HIP97461': ('epoch2_off', 'HIP97461'),
        'primary20170428_HIP97663': ('epoch3_off', 'HIP97663')}
QS = tuple(q for q in range(1, 255) if q not in (64, 128, 192))
COUNT, CORE, HALO, C0 = 1048576, 4096, 4000, 179306496
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
COUNTS = {'maps': 251, 'map_normalization_records': 251, 'carrier_maximum_records': 1028096,
          'valid_hypothesis_records': 1614110720, 'top20_entries': 20, 'top3_metadata_entries': 3,
          'score_audit_queries': 1007, 'score_audit_raw_power_cells': 8104336, 'decoded_rows_verified': 16}
PINS = {PROPOSAL: '2fcb046bd49d2ef22491493a430c429c646afaf0f89691a6b0f194740fef8b5d',
        SOURCE: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
        ACQ: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
        SOURCE_QA: 'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f',
        FULL_QA: 'e1d77ef88fa7a47965bd783b09258b36578c476cd5788ffc94924f3e03d1bc6f',
        INJECTION_QA: 'f9deeaf7fe096484d8fe144aae7c0510a4e2aa77d9454976c1081cdeac0c8551',
        RESTORED: '1b8392ea4eeccfce9bd5e4727ca2258ed4028998e67226fe388007e3dd6a11a2',
        DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        READER: '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON field: ' + key)
        result[key] = value
    return result

def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + value)))

def confined(root, name):
    require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Confined relative path required')
    path = root / name
    require(path.resolve().is_relative_to(root), 'Path escapes workspace')
    return path

def byte_pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}

def save(path, value):
    raw = (json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

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

def resource_guard(root, out=None, reserve=False):
    allocated = workspace_allocated(root)
    require(allocated + (300 * 1024**2 if reserve else 0) <= 8 * 1024**3, '8GiB workspace bound exceeded')
    if out is not None:
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= 100 * 1024**2,
                '100MiB per-job output bound exceeded')
    return allocated

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

def method_contract():
    return {'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_SCOPE_V1', 'native_chunk_index': 171,
        'core_q_indices': list(QS), 'excluded_previously_searched_q': [64, 128, 192], 'excluded_edge_q': [0, 255],
        'source_channel_interval_half_open': [C0, C0 + COUNT], 'core_channels': CORE, 'halo_channels': HALO,
        'rows_per_scan': 16, 'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'widths_channels': [1, 3], 'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785},
        'valid_hypotheses_per_carrier': 1570, 'reference_time': 'each primary scan own first integration midpoint',
        'jobs': {job: {'scan_id': scan, 'primary_target': target, 'original_acquisition_role': 'OFF',
                      'core_q_indices': list(QS)} for job, (scan, target) in JOBS.items()},
        'expected_counts_per_job': COUNTS, 'total_maps': 753, 'total_score_audit_queries': 3021,
        'top20_selection': 'all251core carrier maxima; score descending then absolute channel ascending; greedy distance>3',
        'top3_metadata_only': True, 'fixed_profiles_computed': False, 'running_median_channels': 501,
        'audit_queries_per_core': ['first', 'midpoint', 'last', 'core_max'],
        'fixed_audit_carrier_indices': [0, 2048, 4095], 'global_rank_audits': [1, 2, 3],
        'audit_raw_window_offsets': [-251, 251], 'audit_raw_shape': [16, 503],
        'audit_NPZ_fields': ['raw_power', 'rounded_absolute_centers', 'standardized_row_box_sums'],
        'audit_score_ATOL': 1e-7, 'audit_score_RTOL': 1e-10,
        'normalization_method': 'unchanged detector float64 4096-channel core median/MAD/winsorized location',
        'CPU_cap_s_per_job': 1000, 'wall_cap_s_per_job': 1800, 'memory_cap_bytes_per_job': 2 * 1024**3,
        'memory_cap_bytes_aggregate': 6 * 1024**3, 'max_simultaneous_jobs': 3,
        'workspace_cap_bytes': 8 * 1024**3, 'hard_total_output_budget_bytes': 300 * 1024**2,
        'job_output_budget_bytes': 100 * 1024**2, 'map_NPZ_budget_bytes': 181000,
        'normalization_JSON_budget_bytes': 66000, 'audit_NPZ_budget_bytes': 34000,
        'other_JSON_total_budget_bytes': 5 * 1024**2, 'conservative_total_job_output_bytes': 101477880,
        'runtime_versions': {**VERSIONS, 'HDF5': '1.14.6'},
        'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'new_observation_visit': False,
        'source_acquisition_role_changed': False, 'same_target_repeated_cadence': False,
        'other_five_source_values_opened_per_job': False, 'OFF_veto_applied': False,
        'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False, 'independent_tests_claimed': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'retry_resume_or_rerun_authorized': False}

def contract(root, scope):
    require(all(scope.get(k) == v for k, v in method_contract().items()), 'Frozen scientific/resource method differs')
    for name, pin in scope['text_code_pins'].items():
        path = confined(root, name)
        require(path.suffix in ('.py', '.json', '.md', '.txt'), 'Preflight text only')
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Text/code pin differs: ' + name)
    require(all(scope['text_code_pins'].get(name, {}).get('sha256') == sha for name, sha in PINS.items()),
            'Exact prerequisite/dependency pins required')
    require(scope['text_code_pins'][BASE + '/driver.py']['sha256'] == digest(Path(__file__).resolve()),
            'Self code pin differs')
    proposal, source, acq, qa, injection = (read_json(root / name) for name in (PROPOSAL, SOURCE, ACQ, SOURCE_QA, INJECTION_QA))
    require(proposal['core_q_indices'] == list(QS) and proposal['native_channel_interval_half_open'] == [C0, C0 + COUNT]
            and proposal['original_OFF_role_relabelled_as_ON'] is False, 'Proposal domain differs')
    require([(r['primary_target_id'], r['original_scan_id'], r['primary_target']) for r in proposal['primary_target_records']]
            == [(job, scan, target) for job, (scan, target) in JOBS.items()], 'Primary identities differ')
    expected_tuples = [(job, scan, q, [C0 + q * CORE, C0 + (q + 1) * CORE])
                       for job, (scan, target) in JOBS.items() for q in QS]
    require([(r['primary_target_id'], r['original_scan_id'], r['core_q'], r['reference_channel_interval_half_open'])
             for r in proposal['all_753_new_search_tuples']] == expected_tuples, '753 explicit new tuples differ')
    exclusions = proposal['prior_exclusion_proof']['OFF_exclusion_records']
    require(len(exclusions) == 9 and {(r['original_scan_id'], r['core_q']) for r in exclusions}
            == {(scan, q) for scan, target in JOBS.values() for q in (64, 128, 192)}, 'Nine prior exclusions differ')
    require(proposal['prior_exclusion_proof']['historical_OFF_map_count'] == 0
            and proposal['prior_exclusion_proof']['new_search_tuples_disjoint_from_prior_original_OFF_baseline_map_keys'] is True,
            'Prior exclusion evidence differs')
    require(acq['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
            and acq['source_manifest_sha256'] == PINS[SOURCE] and acq['complete_compact_files'] == 6
            and acq['decoded_row_SHA256s'] == 96 and acq['source_range_count_authenticated'] == 96, 'Actual source acquisition differs')
    require(qa['schema'] == 'SETI_S2017_SAVED_OUTPUT_AND_SOURCE_QA_V1'
            and qa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
            and qa['acquisition_receipt_sha256'] == PINS[ACQ] and qa['counts']['decoded_rows'] == 96
            and qa['detector_or_score_rerun'] is False, 'Actual source QA required')
    require(injection['status'] == 'PASS450_MAPS540_DIAGNOSTICS_RAW_ARITHMETIC_AND_ROUNDED_SUPPORT_NO_DETECTOR_RERUN'
            and injection['counts']['maps'] == 450 and injection['counts']['baseline_maps'] == 18,
            'Actual excluded baseline QA required')
    for job in ('offcenter', 'known_center_competitor'):
        prior = read_json(root / 'analysis/s2017_injection_20261011/results' / job / 'EXECUTION_RECEIPT.json')
        require(prior['status'] == 'COMPLETE_PROSPECTIVE_RAW_POWER_INJECTION_BENCHMARK_EXPLORATORY_ONLY', 'Prior jobs not COMPLETE')
    require(read_json(root / RESTORED)['status'] == 'PASS_EXACT6_NATIVE171_COMPACTS_OPAQUE_RESTORED_NO_HDF5_DECODE',
            'Actual opaque restoration required')
    require(read_json(root / FULL_QA)['status'] == 'PASS759_S2017_MAPS27_FIXED_PROFILES_AND334368_BITWISE_SOURCE_CELLS',
            'Prior full-band source/geometry admission differs')
    require([r['scan_id'] for r in acq['decoded_files']] == list(SCANS)
            and scope['compact_records'] == acq['decoded_files'], 'All six declarations differ')
    require([r['label'] for r in source['sources']] == list(SCANS), 'Canonical source order differs')
    for job, (scan, target) in JOBS.items():
        item = next(r for r in source['sources'] if r['label'] == scan)
        rec = next(r for r in acq['decoded_files'] if r['scan_id'] == scan)
        header = item['current_header']['data_attributes']
        require(item['role'] == 'off' and header['source_name'] == target and header['fch1'] * 1e6 == FCH1
                and header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP, 'Authentic OFF target/header differs')
        require(rec['source_channel0'] == C0 and rec['shape'] == [16, 1, COUNT]
                and rec['array_file'] == scan + '.compact.h5'
                and [r['time_row'] for r in rec['decoded_rows']] == list(range(16))
                and all(r['decoded_bytes'] == COUNT * 4 and re.fullmatch('[0-9a-f]{64}', r['decoded_sha256'])
                        for r in rec['decoded_rows']), 'Exact full compact/16 row pins differ')
    return source, acq

def public_admission(root, scope_path, args):
    require(args.scope_sha256 == digest(scope_path)
            and re.fullmatch('[0-9a-f]{40}', args.freeze_commit or ''), 'Root GO, exact scope and public commit required')
    path = confined(root, args.public_freeze)
    require(re.fullmatch('[0-9a-f]{64}', args.public_freeze_sha256 or '') and digest(path) == args.public_freeze_sha256,
            'Exact public readback SHA required')
    readback = read_json(path)
    require(readback['commit'] == args.freeze_commit and readback['status'].startswith('PASS_'),
            'Successful pre-value public freeze readback required')
    records = readback['files']
    names = [r['path'] for r in records]
    require(len(names) >= 6 and len(names) == len(set(names))
            and {BASE + '/driver.py', BASE + '/prepare_scope.py', args.scope, PROPOSAL} <= set(names),
            'Public driver/preparer/scope/proposal and independent reviews required')
    for pin in records:
        local = confined(root, pin['path'])
        require(local.suffix in ('.py', '.json', '.md', '.txt') and pin['exact_served_commit_bytes'] is True
                and local.stat().st_size == pin['bytes'] and digest(local) == pin['sha256']
                and isinstance(pin['git_path'], str) and pin['git_path'], 'Exact current public text bytes required')
    go_path = confined(root, args.root_go)
    require(re.fullmatch('[0-9a-f]{64}', args.root_go_sha256 or '') and digest(go_path) == args.root_go_sha256,
            'Exact root GO SHA required')
    go = read_json(go_path)
    expected = {'status': 'GO_THREE_FROZEN_PRIMARY_TARGET_JOBS', 'scope_sha256': args.scope_sha256,
        'public_freeze_commit': args.freeze_commit, 'CPU_cap_s_per_job': 1000, 'wall_cap_s_per_job': 1800,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'memory_cap_bytes_aggregate': 6 * 1024**3,
        'max_simultaneous_jobs': 3, 'workspace_cap_bytes': 8 * 1024**3,
        'job_output_budget_bytes': 100 * 1024**2, 'other_science_jobs_running': 0}
    require(all(go.get(k) == v for k, v in expected.items()), 'Root GO exact science/resource contract differs')
    return {'public_freeze': byte_pin(root, path), 'root_GO': byte_pin(root, go_path)}

def store_npz(np, root, path, values, bound):
    with path.open('xb') as stream:
        np.savez(stream, **values)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.stat().st_size <= bound, 'Prospective NPZ byte bound exceeded')
    return byte_pin(root, path)

def run(root, scope, source, acq, job, out):
    import numpy as np
    detector = module('control_primary_original_detector', root / DETECTOR)
    reader = module('control_primary_original_reader', root / READER)
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == '1.14.6', 'Exact HDF5 runtime differs')
    scan_id, target = JOBS[job]
    item = next(r for r in source['sources'] if r['label'] == scan_id)
    record = next(r for r in acq['decoded_files'] if r['scan_id'] == scan_id)
    header = item['current_header']['data_attributes']
    reference_mjd = header['tstart'] + TSAMP / (2 * 86400)
    path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
    pre = byte_pin(root, path)
    require(pre['bytes'] == record['bytes'] and pre['sha256'] == record['file_sha256'], 'Own compact byte pin differs')
    with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
        data = handle['data']
        require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                and data.attrs['original_source_url'] == item['url'] and data.attrs['original_source_etag'] == item['etag'],
                'Own source identity/shape/dtype differs')
        for key, expected in header.items():
            actual = data.attrs[key]
            if isinstance(expected, list):
                actual = actual.tolist()
                actual = [v.decode() if isinstance(v, bytes) else v for v in actual]
            elif isinstance(actual, bytes):
                actual = actual.decode()
            require(actual == expected, 'Original header differs: ' + key)
        power = data[:, 0, :]
    require(np.isfinite(power).all() and np.all(power >= 0), 'Nonfinite or negative own source power')
    for row in record['decoded_rows']:
        require(hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'], 'Own decoded row differs')
    cfg, drifts, times = detector.Config(widths=(1, 3)), np.linspace(-4., 4., 785), np.arange(16) * TSAMP
    maps, audits, saved_results, row_sums = [], [], {}, {}

    def tuple_record(q, result, index, rank=None):
        value = {'primary_id': job, 'primary_target': target, 'scan_id': scan_id, 'original_acquisition_role': 'OFF',
            'core_q': q, 'map_id': '%s_q%03d' % (scan_id, q), 'carrier_index_in_core': int(index),
            'reference_source_channel': int(result['source_reference_channels'][index]),
            'frequency_hz_at_own_first_midpoint': float(result['frequency_hz_at_tref'][index]),
            'reference_time_mjd': reference_mjd,
            'drift_grid_index': int(np.flatnonzero(drifts == result['winning_drift_hz_s'][index])[0]),
            'drift_hz_s': float(result['winning_drift_hz_s'][index]),
            'width_channels': int(result['winning_width_channels'][index]),
            'score': float(result['maximum_robust_box_track_score'][index])}
        if rank is not None:
            value['rank'] = rank
        return value

    def audit(query_id, kind, q, result, index, sums, normalization, rank=None):
        selected = tuple_record(q, result, index, rank)
        centers = np.rint((selected['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                          + selected['drift_hz_s'] * times / DF).astype(np.int64)
        absolute_channels = centers[:, None] + np.arange(-251, 252)[None, :]
        require(absolute_channels.min() >= C0 and absolute_channels.max() < C0 + COUNT, 'Raw capsule outside own compact')
        raw = power[np.arange(16)[:, None], absolute_channels - C0]
        require(np.isclose(sums.sum() / np.sqrt(16 * selected['width_channels']), selected['score'], atol=1e-7, rtol=1e-10),
                'Cached winning row-box arithmetic differs from saved score')
        capsule = store_npz(np, root, out / (query_id + '_raw503.npz'),
            {'raw_power': raw, 'rounded_absolute_centers': centers, 'standardized_row_box_sums': sums}, 34000)
        audits.append({'query_id': query_id, 'query_kind': kind, 'core_q': q, 'map_id': selected['map_id'],
                       'selected_tuple': selected, 'normalization': normalization, 'capsule': capsule})

    for q in QS:
        channels = np.arange(C0 + q * CORE, C0 + (q + 1) * CORE, dtype=np.int64)
        crop0 = C0 + q * CORE - HALO
        crop = power[:, q * CORE - HALO:(q + 1) * CORE + HALO].astype(np.float64)
        scan = detector.Scan(scan_id, 'OFF', crop, header['tstart'], TSAMP, FCH1, DF, crop0, channels)
        result, arrays = detector.search_scan(scan, FCH1 + DF * channels, times, drifts, cfg)
        require(result['role'] == 'OFF' and np.all(result['valid_hypothesis_count'] == 1570)
                and np.isfinite(result['maximum_robust_box_track_score']).all(), 'Incomplete own OFF carrier map')
        result['source_reference_channels'] = channels
        map_id = '%s_q%03d' % (scan_id, q)
        archive = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
        archive['drift_grid_hz_s'] = drifts
        map_pin = store_npz(np, root, out / (map_id + '.npz'), archive, 181000)
        norm_path = out / (map_id + '_normalization.json')
        save(norm_path, result['normalization'])
        norm_pin = byte_pin(root, norm_path)
        require(norm_pin['bytes'] <= 66000, 'Normalization JSON prospective bound exceeded')
        maps.append({'map_id': map_id, 'scan_id': scan_id, 'primary_id': job, 'original_acquisition_role': 'OFF',
                     'core_q': q, **map_pin, 'normalization': norm_pin,
                     'reference_channel_interval_half_open': [int(channels[0]), int(channels[-1]) + 1],
                     'searched_carriers': 4096, 'valid_hypotheses_per_carrier': 1570})
        # This is a lookup of already searched winners in unchanged cached box
        # arrays, not another search. Keep 131.6MB of row sums for final top3.
        sums = np.empty((CORE, 16), dtype=np.float64)
        centers = np.rint(arrays[1][:, None] + result['winning_drift_hz_s'][:, None] * times[None, :] / DF).astype(np.int64)
        for width in (1, 3):
            chosen = result['winning_width_channels'] == width
            for row in range(16):
                sums[chosen, row] = arrays[0][width][0][row, centers[chosen, row] - crop0 - width // 2]
        row_sums[q] = sums
        saved_results[q] = {k: v for k, v in result.items() if isinstance(v, np.ndarray)}
        maximum = int(np.lexsort((channels, -result['maximum_robust_box_track_score']))[0])
        for kind, index in (('first', 0), ('midpoint', 2048), ('last', 4095), ('core_max', maximum)):
            audit('q%03d_%s' % (q, kind), kind, q, result, index, sums[index], norm_pin)
        del arrays, scan, crop, centers, result
        resource_guard(root, out)
        print(json.dumps({'job': job, 'completed_core_maps': len(maps), 'expected': 251}), flush=True)

    flat_channels = np.concatenate([saved_results[q]['source_reference_channels'] for q in QS])
    flat_scores = np.concatenate([saved_results[q]['maximum_robust_box_track_score'] for q in QS])
    selected = []
    for index in np.lexsort((flat_channels, -flat_scores)):
        channel = int(flat_channels[index])
        if any(abs(channel - old['reference_source_channel']) <= 3 for old in selected):
            continue
        qi, carrier = divmod(int(index), CORE)
        q = QS[qi]
        selected.append(tuple_record(q, saved_results[q], carrier, len(selected) + 1))
        if len(selected) == 20:
            break
    require(len(selected) == 20, 'Global top20 incomplete')
    for name, records in (('TOP20.json', selected), ('TOP3.json', selected[:3])):
        save(out / name, {'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_RANKS_V1', 'primary_id': job,
            'scan_id': scan_id, 'original_acquisition_role': 'OFF', 'reference_time_mjd': reference_mjd,
            'selection_rule': scope['top20_selection'], 'records': records})
    for chosen in selected[:3]:
        q, index = chosen['core_q'], chosen['carrier_index_in_core']
        audit('global_top%02d' % chosen['rank'], 'global_top3', q, saved_results[q], index,
              row_sums[q][index], next(r['normalization'] for r in maps if r['core_q'] == q), chosen['rank'])
    require(len(maps) == 251 and len(audits) == 1007, 'Prospective map/query counts differ')
    save(out / 'MAPS.json', {'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_MAP_INVENTORY_V1',
                           'primary_id': job, 'scan_id': scan_id, 'records': maps})
    save(out / 'SCORE_AUDITS.json', {'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_SCORE_AUDITS_V1',
                                   'primary_id': job, 'scan_id': scan_id, 'records': audits})
    for row in record['decoded_rows']:
        require(hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'],
                'Own decoded source row changed during search')
    post = byte_pin(root, path)
    require(post == pre, 'Own whole compact changed during search')
    return {'counts': COUNTS, 'source_compact_pre_pin': pre, 'source_compact_post_pin': post,
            'decoded_row_pins': record['decoded_rows'], 'decoded_row_SHA_checks_before': 16,
            'decoded_row_SHA_checks_after': 16, 'own_primary_reference_time_mjd': reference_mjd}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--scope', default=BASE + '/scope.json')
    parser.add_argument('--job', choices=tuple(JOBS), required=True)
    parser.add_argument('--scope-sha256')
    parser.add_argument('--freeze-commit')
    parser.add_argument('--public-freeze', default=BASE + '/PUBLIC_FREEZE.json')
    parser.add_argument('--public-freeze-sha256')
    parser.add_argument('--root-go', default=BASE + '/ROOT_GO.json')
    parser.add_argument('--root-go-sha256')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    scope_path = confined(root, args.scope)
    scope = read_json(scope_path)
    source, acq = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_NO_NUMERICAL_IMPORTS_OR_H5_STAT_OPENS',
                          'job': args.job, 'scope_sha256': digest(scope_path), 'counts': COUNTS}))
        return
    readback_pin = public_admission(root, scope_path, args)
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Exact runtime differs: ' + package)
    resource_guard(root, reserve=True)
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (1000, 1001))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('1800s wall cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    handles, out, created_output = [], None, False
    try:
        family = (root / BASE / 'ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        fcntl.flock(family, fcntl.LOCK_SH | fcntl.LOCK_NB)
        handles.append(family)
        for slot in range(3):
            handle = (root / BASE / ('ACTIVE_SCIENCE_SLOT_%d_FLOCK.lock' % slot)).open('a+b')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handles.append(handle)
                break
            except BlockingIOError:
                handle.close()
        else:
            raise BlockingIOError('All three science slots occupied')
        handle = (root / BASE / (args.job + '_FLOCK.lock')).open('a+b')
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handles.append(handle)
        out = root / BASE / 'results' / args.job
        out.mkdir(parents=True, exist_ok=False)
        created_output = True
        result = run(root, scope, source, acq, args.job, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256 and public_admission(root, scope_path, args) == readback_pin,
                'Frozen source admission changed during run')
        pins = [byte_pin(root, p) for p in sorted(out.iterdir()) if p.is_file()]
        require(len(pins) == 1513, 'Exact 251maps+251normalizations+1007capsules+4JSON inventory differs')
        allocated = resource_guard(root, out)
        receipt = {'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_EXECUTION_V1',
            'status': 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY',
            'primary_id': args.job, 'scan_id': JOBS[args.job][0], 'primary_target': JOBS[args.job][1],
            'original_acquisition_role': 'OFF', 'scope_sha256': args.scope_sha256,
            'driver_sha256': digest(Path(__file__).resolve()), 'public_freeze_commit': args.freeze_commit,
            'execution_admission_pins': readback_pin, 'source_manifest_sha256': PINS[SOURCE],
            'acquisition_receipt_sha256': PINS[ACQ], 'source_QA_receipt_sha256': PINS[SOURCE_QA],
            'prior_exclusion_proposal_sha256': PINS[PROPOSAL], 'injection_QA_receipt_sha256': PINS[INJECTION_QA],
            **result, 'output_byte_pins': pins, 'runtime_versions': {**VERSIONS, 'HDF5': '1.14.6'},
            'science_slot': slot, 'process_CPU_seconds': time.process_time() - cpu0,
            'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'CPU_cap_s': 1000, 'wall_cap_s': 1800, 'memory_cap_bytes_per_job': 2 * 1024**3,
            'memory_cap_bytes_aggregate': 6 * 1024**3, 'max_simultaneous_jobs': 3,
            'workspace_allocated_bytes_final': allocated, 'workspace_cap_bytes': 8 * 1024**3,
            'output_cap_bytes': 100 * 1024**2, 'source_bytes_unchanged': True, 'science_search_repeated': False,
            'other_five_source_values_opened': False, 'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0,
            'new_observation_visit': False, 'source_acquisition_role_changed': False,
            'same_target_repeated_cadence': False, 'OFF_veto_applied': False,
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False, 'independent_tests_claimed': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
        # Bound all auxiliary JSON, including the prospective completed receipt,
        # before committing a successful terminal state.
        receipt_size = len((json.dumps(receipt, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        other_bytes = sum(p.stat().st_size for p in out.glob('*.json') if not p.name.endswith('_normalization.json'))
        require(other_bytes + receipt_size <= 5 * 1024**2, 'Prospective auxiliary JSON bound exceeded')
        require(sum(p.stat().st_size for p in out.iterdir()) + receipt_size <= 100 * 1024**2, 'Final output budget exceeded')
        require(receipt['process_CPU_seconds'] <= 1000 and receipt['wall_seconds'] <= 1800
                and receipt['peak_RSS_bytes'] <= 2 * 1024**3, 'Measured science resource bound exceeded')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        resource_guard(root, out)
    except BaseException as exc:
        if created_output and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_EXECUTION_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'primary_id': args.job,
                'failure_type': type(exc).__name__, 'failure': str(exc), 'scope_sha256': args.scope_sha256,
                'public_freeze_commit': args.freeze_commit, 'new_telescope_HTTP_requests': 0})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()

if __name__ == '__main__':
    main()
