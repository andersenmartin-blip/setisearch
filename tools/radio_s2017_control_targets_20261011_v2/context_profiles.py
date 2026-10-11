"""Prospective fixed-tuple context; import/check-only uses text metadata only.

Nine primary OFF-selected tuples retain their first-midpoint frequency, drift,
width and static normalization core in all six original pointings. Numerical
work is gated on three COMPLETE primary jobs and independent primary-map QA.
There is no detector grid, fitting, ON/OFF veto or sky-source classification.
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

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
BASE = 'analysis/s2017_control_targets_20261011_v2'
SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ACQ = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
SOURCE_QA = 'analysis/new_visit_recovery/results/review/QA_RECEIPT.json'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
READER = 'analysis/new_visit_search/dependencies/standard_reader.py'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
TARGETS = {'primary20170428_HIP97319': ('HIP97319', 'epoch1_off'),
           'primary20170428_HIP97461': ('HIP97461', 'epoch2_off'),
           'primary20170428_HIP97663': ('HIP97663', 'epoch3_off')}
COUNT, CORE, HALO, C0 = 1048576, 4096, 4000, 179306496
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CORES = tuple(q for q in range(1, 255) if q not in (64, 128, 192))
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
PINS = {SOURCE: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
        ACQ: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
        SOURCE_QA: 'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f',
        DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        READER: '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'}
QA_SCHEMA = 'SETI_S2017_CONTROL_TARGET_SAVED_INDEPENDENT_QA_V1'
QA_STATUS = 'PASS753_ORIGINAL_OFF_MAPS3021_RAW_SCORE_QUERIES_NO_DETECTOR_RERUN'
PRIMARY_STATUS = 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY'
REVIEW_PATHS = ('analysis/s2017_control_targets_20261011_v2/review/CONTEXT_STATIC_REVIEW.json',
                'analysis/s2017_control_targets_20261011_v2/review/CONTEXT_SCIENTIFIC_REVIEW.json')
TOP_KEYS = ('rank', 'primary_id', 'primary_target', 'scan_id', 'original_acquisition_role',
            'core_q', 'map_id', 'carrier_index_in_core', 'reference_source_channel',
            'frequency_hz_at_own_first_midpoint', 'reference_time_mjd', 'drift_grid_index',
            'drift_hz_s', 'width_channels', 'score')


def require(test, message):
    if not test:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def pairs(items):
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON key: ' + key)
        value[key] = item
    return value


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs)


def confined(root, name):
    require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts,
            'Relative confined path required')
    path = root / name
    require(path.resolve().is_relative_to(root), 'Path escapes project root')
    return path


def save(path, value):
    b = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(b)
        stream.flush()
        os.fsync(stream.fileno())


def pin(root, path):
    p = confined(root, path)
    return {'bytes': p.stat().st_size, 'sha256': digest(p)}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def workspace_allocated(root):
    seen, total = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                st = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            key = (st.st_dev, st.st_ino)
            if key not in seen:
                seen.add(key)
                total += st.st_blocks * 512
    return total


def resources(root, scope, out=None, reserve=False):
    allocated = workspace_allocated(root)
    require(allocated + (scope['output_cap_bytes'] if reserve else 0) <= scope['workspace_cap_bytes'],
            'Workspace8GiB bound exceeded')
    if out is not None:
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= scope['output_cap_bytes'],
                'Context32MiB output bound exceeded')
    return allocated


def geometry(source):
    """Exhaustive metadata-only support bound for any future selected tuple."""
    headers = {s['label']: s['current_header']['data_attributes'] for s in source['sources']}
    records = []
    for primary_id, (target, origin) in TARGETS.items():
        t0 = headers[origin]['tstart']
        for label in SCANS:
            h = headers[label]
            times = [(h['tstart'] - t0) * 86400.0 + j * TSAMP for j in range(16)]
            # Same integration length means midpoint halves cancel exactly.
            lo = min(round(c + d * t / DF) for c in (0, CORE - 1)
                     for d in (-4.0, 4.0) for t in (times[0], times[-1]))
            hi = max(round(c + d * t / DF) for c in (0, CORE - 1)
                     for d in (-4.0, 4.0) for t in (times[0], times[-1]))
            # Conservative one-cell floating/rounding guard on the metadata bound.
            lo, hi = lo - 1, hi + 1
            require(lo - 251 >= -HALO and hi + 251 < CORE + HALO,
                    'Future selected family lacks503 support within original core halo')
            for q in CORES:
                require(q * CORE - HALO >= 0 and (q + 1) * CORE + HALO <= COUNT,
                        'Frozen normalization crop outside native171 source')
            records.append({'primary_id': primary_id, 'origin_scan_id': origin,
                'context_scan_id': label, 'reference_time_mjd': t0 + TSAMP / (2 * 86400),
                'times_from_primary_reference_s': times,
                'row_midpoint_mjd': [h['tstart'] + (j + .5) * TSAMP / 86400 for j in range(16)],
                'all_possible_carriers_drifts_rounded_core_relative_center_min_max': [lo, hi],
                'complete503_support_core_relative_min_max': [lo - 251, hi + 251],
                'normalization_crop_core_relative_half_open': [-HALO, CORE + HALO]})
    return records


def contract(root, scope):
    require(scope['schema'] == 'SETI_S2017_CONTROL_TARGET_FIXED_CONTEXT_SCOPE_V1', 'Context scope schema')
    expected = {'scan_order': list(SCANS), 'primary_ids': list(TARGETS), 'eligible_core_q': list(CORES),
        'native_chunk_index': 171, 'core_channels': CORE, 'halo_channels': HALO,
        'selected_tracks_per_primary': 3, 'selected_tracks_total': 9, 'context_scores': 54,
        'search_widths': [1, 3], 'drift_grid_count': 785, 'running_median_channels': 501,
        'raw_capsule_channels': 503, 'source_decoded_rows': 96,
        'CPU_cap_s': 180, 'wall_cap_s': 300, 'memory_cap_bytes': 2 * 1024**3,
        'output_cap_bytes': 32 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3,
        'score_match_absolute_tolerance': 1e-7, 'score_match_relative_tolerance': 1e-10,
        'qualified_SETI_detection': False, 'new_HTTP_requests': 0,
        'primary_QA_schema': QA_SCHEMA, 'primary_QA_status': QA_STATUS,
        'primary_receipt_status': PRIMARY_STATUS, 'independent_context_review_paths': list(REVIEW_PATHS)}
    for k, v in expected.items():
        require(scope.get(k) == v, 'Frozen context differs: ' + k)
    for name, sha in scope['text_code_pins'].items():
        require(Path(name).suffix in ('.py', '.json') and digest(confined(root, name)) == sha,
                'Text/code pin differs: ' + name)
    require(all(scope['text_code_pins'].get(name) == sha for name, sha in PINS.items()),
            'Original source/detector prerequisites differ')
    require(scope['text_code_pins'][BASE + '/context_profiles.py'] == digest(Path(__file__).resolve()),
            'Context driver self pin differs')
    require(scope['primary_scope_sha256'] == digest(confined(root, scope['primary_scope_path'])),
            'Prospective primary scope pin differs')
    primary = read_json(root / scope['primary_scope_path'])
    require(primary['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_SCOPE_V1'
        and primary['core_q_indices'] == list(CORES) and primary['total_maps'] == 753
        and primary['top20_selection'] == scope['primary_selection_rule'], 'Frozen primary family/selection differs')
    require(scope['primary_QA_source_sha256'] == scope['text_code_pins'][BASE + '/qa_saved.py'],
            'Prospective independent primaryQA code pin differs')
    source, acq, qa = (read_json(root / name) for name in (SOURCE, ACQ, SOURCE_QA))
    require(acq['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
        and qa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
        and qa['acquisition_receipt_sha256'] == PINS[ACQ], 'Original actual source admission differs')
    require(scope['compact_records'] == acq['decoded_files'], 'Six compact declarations differ')
    require([s['label'] for s in source['sources']] == list(SCANS)
        and [r['scan_id'] for r in acq['decoded_files']] == list(SCANS), 'Original canonical source order')
    previous = float('-inf')
    for item, rec in zip(source['sources'], acq['decoded_files']):
        h = item['current_header']['data_attributes']
        require(h['tstart'] >= previous and h['tsamp'] == TSAMP and h['fch1'] * 1e6 == FCH1
            and h['foff'] * 1e6 == DF and item['role'] == ('on' if item['label'].endswith('_on') else 'off'),
            'Original header/grid/role differs')
        previous = h['tstart'] + 16 * TSAMP / 86400
        require(rec['array_file'] == item['label'] + '.compact.h5' and rec['shape'] == [16, 1, COUNT]
            and rec['source_channel0'] == C0 and len(rec['decoded_rows']) == 16
            and [r['time_row'] for r in rec['decoded_rows']] == list(range(16)), 'Complete96 source rows required')
    for _, (target, origin) in TARGETS.items():
        item = next(s for s in source['sources'] if s['label'] == origin)
        require(item['role'] == 'off' and item['current_header']['data_attributes']['source_name'] == target,
                'Original OFF primary target identity differs')
    require(scope['prospective_all_tuple_geometry'] == geometry(source), 'Frozen relative-time/support geometry differs')
    return source, acq


def public_admission(root, scope_path, scope, args):
    require(args.scope_sha256 == digest(scope_path)
        and re.fullmatch('[0-9a-f]{40}', args.freeze_commit or ''), 'Exact context scope/public commit required')
    require(len(args.primary_receipt_sha256 or []) == 3, 'Three actual primary receipt SHAs required')
    inputs = {}
    for name, sha in ((args.public_freeze, args.public_freeze_sha256), (args.root_go, args.root_go_sha256)):
        require(re.fullmatch('[0-9a-f]{64}', sha or '') and digest(confined(root, name)) == sha,
                'Exact context public-readback/rootGO SHA required')
        inputs[name] = pin(root, name)
    readback = read_json(confined(root, args.public_freeze))
    require(readback['commit'] == args.freeze_commit and readback['status'].startswith('PASS_'),
            'Successful exact public context readback required')
    records = readback['files']
    names = [r['path'] for r in records]
    expected = {BASE + '/context_profiles.py', BASE + '/prepare_context_scope.py', args.scope, *REVIEW_PATHS}
    require(expected <= set(names) and len(names) == len(set(names)), 'Public context code/scope/independent reviews absent')
    for record in records:
        path = confined(root, record['path'])
        actual = pin(root, record['path'])
        require(path.suffix in ('.py', '.json', '.md', '.txt')
            and record['exact_served_commit_bytes'] is True
            and actual == {'bytes': record['bytes'], 'sha256': record['sha256']}
            and isinstance(record['git_path'], str) and record['git_path'], 'Public served/current context bytes differ')
        inputs[record['path']] = actual
    for name in REVIEW_PATHS:
        review = read_json(root / name)
        require(review['status'].startswith('PASS_')
            and review['context_driver_sha256'] == scope['text_code_pins'][BASE + '/context_profiles.py']
            and review['context_preparer_sha256'] == scope['text_code_pins'][BASE + '/prepare_context_scope.py']
            and review['context_scope_sha256'] == args.scope_sha256, 'Independent context review bindings differ')
    go = read_json(confined(root, args.root_go))
    expected_go = {'status': 'GO_NINE_FIXED_PRIMARY_SELECTED_TRACKS54_CONTEXT_PROFILES',
        'context_scope_sha256': args.scope_sha256, 'public_freeze_commit': args.freeze_commit,
        'primary_receipt_sha256s': dict(zip(TARGETS, args.primary_receipt_sha256)),
        'actual_primary_QA_receipt_sha256': args.primary_qa_sha256,
        'selected_tracks': 9, 'context_scores': 54, 'source_decoded_rows': 96,
        'CPU_cap_s': 180, 'wall_cap_s': 300, 'memory_cap_bytes': 2 * 1024**3,
        'output_cap_bytes': 32 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3,
        'other_science_jobs_running': 0, 'new_HTTP_requests': 0}
    require(all(go.get(k) == v for k, v in expected_go.items()), 'Root contextGO exact method/resource/actual-input contract differs')
    return inputs


def admission(root, scope, source, receipt_shas, qa_sha):
    """Only completed saved JSON opened here; no primary map NPZ is read."""
    require(len(receipt_shas) == 3 and all(re.fullmatch('[0-9a-f]{64}', x) for x in receipt_shas)
            and re.fullmatch('[0-9a-f]{64}', qa_sha or ''), 'Exact actual3receipt and primaryQA SHA required')
    qa_path = BASE + '/results/review/QA_RECEIPT.json'
    require(digest(root / qa_path) == qa_sha, 'Actual primaryQA SHA differs')
    qa = read_json(root / qa_path)
    require(qa['schema'] == QA_SCHEMA and qa['status'] == QA_STATUS, 'Actual independent primaryQA not PASS')
    expected_receipts = dict(zip(TARGETS, receipt_shas))
    require(qa['primary_receipt_sha256s'] == expected_receipts, 'PrimaryQA binds different3receipts')
    require(qa['primary_scope_sha256'] == scope['primary_scope_sha256']
        and qa['qa_sha256'] == scope['primary_QA_source_sha256']
        and qa['numeric_tolerance'] == {'absolute': 1e-7, 'relative': 1e-10}, 'PrimaryQA scope/code/tolerance differs')
    require(qa['counts']['maps'] == 753 and qa['counts']['score_audit_queries'] == 3021
        and qa['counts']['top3_entries'] == 9, 'Actual primaryQA counts differ')
    inputs = {qa_path: pin(root, qa_path)}
    selected, headers = [], {s['label']: s['current_header']['data_attributes'] for s in source['sources']}
    for primary_id, receipt_sha in expected_receipts.items():
        target, label = TARGETS[primary_id]
        receipt_path = BASE + '/results/' + primary_id + '/EXECUTION_RECEIPT.json'
        require(digest(root / receipt_path) == receipt_sha, 'Primary COMPLETE receipt SHA differs')
        receipt = read_json(root / receipt_path)
        require(receipt['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_EXECUTION_V1'
            and receipt['status'] == PRIMARY_STATUS and receipt['primary_id'] == primary_id
            and receipt['scan_id'] == label and receipt['primary_target'] == target
            and receipt['original_acquisition_role'] == 'OFF'
            and receipt['scope_sha256'] == scope['primary_scope_sha256']
            and receipt['driver_sha256'] == scope['text_code_pins'][BASE + '/driver.py'],
            'Primary receipt not exact COMPLETE')
        primary_outputs = {p['path']: {'bytes': p['bytes'], 'sha256': p['sha256']}
                           for p in receipt['output_byte_pins']}
        inputs[receipt_path] = pin(root, receipt_path)
        top = []
        for name in ('TOP20.json', 'TOP3.json'):
            path = BASE + '/results/' + primary_id + '/' + name
            actual = pin(root, path)
            require(qa['input_byte_pins'].get(path) == actual and primary_outputs.get(path) == actual,
                    'Primary receipt/QA lacks exact top-list pin: ' + path)
            value = read_json(root / path)
            require(value['primary_id'] == primary_id and value['scan_id'] == label
                and value['original_acquisition_role'] == 'OFF'
                and value['reference_time_mjd'] == headers[label]['tstart'] + TSAMP / (2 * 86400)
                and value['selection_rule'] == scope['primary_selection_rule'], 'Primary list identity/frame/rule differs')
            inputs[path] = actual
            top.append(value['records'])
        require(len(top[0]) == 20 and len(top[1]) == 3 and top[1] == top[0][:3], 'TOP3 is not exact first3TOP20')
        require(qa['selected_top3'][primary_id] == top[1], 'Independent primaryQA selected tuple binding differs')
        for rank, track in enumerate(top[1], 1):
            require(set(track) == set(TOP_KEYS) and track['rank'] == rank and track['primary_id'] == primary_id
                and track['primary_target'] == target and track['scan_id'] == label
                and track['original_acquisition_role'] == 'OFF', 'Exact selected tuple identity required')
            q, carrier, di = track['core_q'], track['carrier_index_in_core'], track['drift_grid_index']
            require(type(q) is int and q in CORES and type(carrier) is int and 0 <= carrier < CORE
                and type(di) is int and 0 <= di < 785 and type(track['width_channels']) is int
                and track['width_channels'] in (1, 3), 'Selected tuple outside frozen family')
            channel = C0 + q * CORE + carrier
            require(track['reference_source_channel'] == channel
                and track['frequency_hz_at_own_first_midpoint'] == FCH1 + DF * channel
                and track['reference_time_mjd'] == headers[label]['tstart'] + TSAMP / (2 * 86400)
                and math.isclose(track['drift_hz_s'], -4 + di * 8 / 784, abs_tol=2e-15, rel_tol=0)
                and math.isfinite(track['score']), 'Selected frequency/drift/reference differs')
            selected.append(track)
    require(len(selected) == 9, 'Exactly9 frozen primary tuples required')
    return selected, inputs


def run(root, scope, source, acq, selected, inputs, out):
    import numpy as np
    detector = module('control_context_original_detector', root / DETECTOR)
    reader = module('control_context_original_reader', root / READER)
    h5py, _, _ = reader.current_codecs()
    require(h5py.version.hdf5_version == '1.14.6', 'HDF5 version differs')
    power, verified, streams = {}, [], []
    try:
        for item, record in zip(source['sources'], acq['decoded_files']):
            path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            stream = os.fdopen(fd, 'rb')
            streams.append((path, stream, os.fstat(fd)))
            st = os.fstat(fd)
            require(st.st_size == record['bytes'], 'Compact size differs')
            h = hashlib.sha256()
            for b in iter(lambda: stream.read(1048576), b''):
                h.update(b)
            require(h.hexdigest() == record['file_sha256'], 'Compact file SHA differs')
            stream.seek(0)
            with h5py.File(stream, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                data = handle['data']
                require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                    and data.attrs['original_source_url'] == item['url']
                    and data.attrs['original_source_etag'] == item['etag'], 'Compact source identity differs')
                values = data[:, 0, :]
            require(np.isfinite(values).all() and np.all(values >= 0), 'Invalid complete source power')
            for row in record['decoded_rows']:
                require(row['decoded_bytes'] == COUNT * 4 and hashlib.sha256(values[row['time_row']].tobytes()).hexdigest()
                        == row['decoded_sha256'], 'Decoded fullsource row SHA differs')
            power[item['label']] = values
            verified.append({'scan_id': item['label'], 'file_sha256': record['file_sha256'],
                             'decoded_rows_verified': 16, 'read_only_source_open_count': 1})
        cfg, rows = detector.Config(widths=(1, 3)), np.arange(16)
        headers = {s['label']: s['current_header']['data_attributes'] for s in source['sources']}
        profiles, output_pins, origin_matches = [], {}, 0
        for track in selected:
            q, width, origin = track['core_q'], track['width_channels'], track['scan_id']
            channels = np.arange(C0 + q * CORE, C0 + (q + 1) * CORE, dtype=np.int64)
            crop0 = C0 + q * CORE - HALO
            base = (track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
            for label in SCANS:
                h = headers[label]
                times = (h['tstart'] - headers[origin]['tstart']) * 86400 + rows * TSAMP
                centers = np.rint(base + track['drift_hz_s'] * times / DF).astype(np.int64)
                local = centers - crop0
                require(np.all(local - 251 >= 0) and np.all(local + 251 < CORE + 2 * HALO), 'Actual tuple lacks503 support')
                raw = power[label][:, q * CORE - HALO:(q + 1) * CORE + HALO]
                scan = detector.Scan(label, 'ON' if label.endswith('_on') else 'OFF', raw,
                    h['tstart'], TSAMP, FCH1, DF, crop0, channels)
                z, mask, normalization = detector.preprocess(scan, cfg)
                indices = local[:, None] + np.arange(-(width // 2), width // 2 + 1)[None, :]
                require(mask[rows[:, None], indices].all(), 'Fixed context box is masked')
                row_terms = z[rows[:, None], indices].sum(axis=1, dtype=np.float64)
                score = float(row_terms.sum(dtype=np.float64) / np.sqrt(16 * width))
                require(math.isfinite(score), 'Invalid direct fixed context score')
                profile_id = '%s_top%d_%s' % (track['primary_id'], track['rank'], label)
                capsule_path = out / (profile_id + '_raw503.npz')
                absolute_indices = centers[:, None] - C0 + np.arange(-251, 252)[None, :]
                capsule = power[label][rows[:, None], absolute_indices].copy()
                require(capsule.shape == (16, 503) and capsule.dtype.str == '<f4', 'Raw source capsule contract')
                with capsule_path.open('xb') as stream:
                    np.savez(stream, raw_power=capsule, rounded_absolute_centers=centers,
                        times_from_primary_reference_s=times, row_standardized_box_sum=row_terms)
                    stream.flush()
                    os.fsync(stream.fileno())
                norm_path = out / (profile_id + '_normalization.json')
                save(norm_path, normalization)
                cap_pin = pin(root, str(capsule_path.relative_to(root)))
                norm_pin = pin(root, str(norm_path.relative_to(root)))
                output_pins[capsule_path.name], output_pins[norm_path.name] = cap_pin, norm_pin
                value = {'profile_id': profile_id, 'selected_track': track,
                    'context_scan_id': label, 'context_target': h['source_name'],
                    'original_acquisition_role': 'ON' if label.endswith('_on') else 'OFF',
                    'reference_time_mjd': track['reference_time_mjd'],
                    'times_from_primary_reference_s': times.tolist(),
                    'row_midpoint_mjd': [h['tstart'] + (j + .5) * TSAMP / 86400 for j in range(16)],
                    'rounded_absolute_centers': centers.tolist(),
                    'rounded_center_frequency_hz': (FCH1 + DF * centers).tolist(),
                    'width_channels': width, 'row_standardized_box_sum': row_terms.tolist(),
                    'direct_fixed_robust_box_track_score': score,
                    'raw_capsule': {'path': capsule_path.name, **cap_pin},
                    'normalization': {'path': norm_path.name, **norm_pin},
                    'source_file_sha256': next(r['file_sha256'] for r in acq['decoded_files'] if r['scan_id'] == label),
                    'origin_primary_score': track['score'] if label == origin else None,
                    'origin_primary_score_difference': score - track['score'] if label == origin else None}
                if label == origin:
                    require(math.isclose(score, track['score'], abs_tol=1e-7, rel_tol=1e-10),
                            'Direct origin score does not match primary saved winner')
                    origin_matches += 1
                profiles.append(value)
                resources(root, scope, out)
                print('FIXED_CONTEXT_SAVED', profile_id, len(profiles), flush=True)
                del z, mask, capsule
        require(len(profiles) == 54 and origin_matches == 9, 'Exact54 contexts9origin matches required')
        for path, stream, before in streams:
            after, pathname = os.fstat(stream.fileno()), path.stat(follow_symlinks=False)
            require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
                    (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                and (pathname.st_dev, pathname.st_ino) == (before.st_dev, before.st_ino),
                'Retained source descriptor/path identity changed')
        matrix = {'schema': 'SETI_S2017_CONTROL_TARGET_FIXED_SIX_SCAN_CONTEXT_PROFILES_V1',
            'status': 'COMPLETE_NINE_PRIMARY_SELECTED_TUPLES54_FIXED_SCAN_CONTEXT_PROFILES',
            'selected_tracks': selected, 'profiles': profiles, 'source_verification': verified,
            'counts': {'selected_tracks': 9, 'context_scores': 54, 'source_files': 6,
                'source_decoded_rows': 96, 'raw_source_capsule_cells': 54 * 16 * 503, 'origin_score_matches': 9},
            'runtime_input_byte_pins': inputs, 'selection_is_post_primary_search': True,
            'new_frequency_drift_width_optimization': False, 'ON_OFF_veto_applied': False,
            'same_target_independent_repeats': False, 'qualified_SETI_detection': False,
            'calibrated_SNR_FAP': False,
            'interpretation': 'Other original directions/times provide fixed-track context, not blanksky controls or independent repetitions of the primary target. Drift grid spacing guarantees apply to the primary16-row scan, not whole-cadence fitting.'}
        save(out / 'CONTEXT_PROFILES.json', matrix)
        output_pins['CONTEXT_PROFILES.json'] = pin(root, str((out / 'CONTEXT_PROFILES.json').relative_to(root)))
        return matrix['counts'], output_pins
    finally:
        for _, stream, _ in streams:
            stream.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--scope', default=BASE + '/context_scope.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--primary-receipt-sha256', nargs=3)
    parser.add_argument('--primary-qa-sha256')
    parser.add_argument('--freeze-commit')
    parser.add_argument('--public-freeze', default=BASE + '/CONTEXT_PUBLIC_FREEZE.json')
    parser.add_argument('--public-freeze-sha256')
    parser.add_argument('--root-go', default=BASE + '/ROOT_CONTEXT_GO.json')
    parser.add_argument('--root-go-sha256')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root, scope_path = args.root.resolve(), confined(args.root.resolve(), args.scope)
    scope = read_json(scope_path)
    source, acq = contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_CONTEXT_SOURCE_METADATA_ONLY_NO_NUMERICAL_IMPORTS_OR_VALUE_OPENS',
                          'scope_sha256': digest(scope_path), 'prospective_geometry_pairs': 18}))
        return
    public_pins = public_admission(root, scope_path, scope, args)
    selected, inputs = admission(root, scope, source, args.primary_receipt_sha256 or [], args.primary_qa_sha256)
    inputs.update(public_pins)
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Exact runtime differs: ' + package)
    resources(root, scope, reserve=True)
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (180, 181))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('Context wall300s cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(300)
    out, lock = None, None
    try:
        fd = os.open(root / BASE / 'ACTIVE_FAMILY_FLOCK.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        lock = os.fdopen(fd, 'a+b')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = root / BASE / 'results/context'
        out.mkdir(parents=True, exist_ok=False)
        counts, outputs = run(root, scope, source, acq, selected, inputs, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256, 'Context scope changed during run')
        require(public_admission(root, scope_path, scope, args) == public_pins,
                'Public context admission changed during run')
        for name, expected in inputs.items():
            require(pin(root, name) == expected, 'Primary runtime input changed: ' + name)
        allocated = resources(root, scope, out)
        measured = {'process_CPU_seconds': time.process_time() - cpu0,
            'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < measured['process_CPU_seconds'] <= 180 and 0 < measured['wall_seconds'] <= 300
            and 0 < measured['peak_RSS_bytes'] <= 2 * 1024**3, 'Measured terminal context resource caps exceeded')
        receipt = {'schema': 'SETI_S2017_CONTROL_TARGET_CONTEXT_EXECUTION_V1',
            'status': 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES_NO_OPTIMIZATION',
            'scope_sha256': args.scope_sha256, 'context_driver_sha256': digest(Path(__file__).resolve()),
            'public_freeze_commit': args.freeze_commit, 'primary_scope_sha256': scope['primary_scope_sha256'],
            'primary_receipt_sha256s': dict(zip(TARGETS, args.primary_receipt_sha256)),
            'actual_primary_QA_receipt_sha256': args.primary_qa_sha256,
            'counts': counts, 'input_byte_pins': inputs, 'output_pins': outputs,
            'score_match_absolute_tolerance': 1e-7, 'score_match_relative_tolerance': 1e-10,
            'runtime_versions': {**VERSIONS, 'HDF5': '1.14.6'},
            **measured, 'execution_admission_byte_pins': public_pins,
            'CPU_cap_s': 180, 'wall_cap_s': 300, 'memory_cap_bytes': 2 * 1024**3,
            'output_cap_bytes': 32 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3,
            'workspace_allocated_bytes_final': allocated, 'new_HTTP_requests': 0,
            'detector_grid_or_carrier_drift_search': False, 'new_fit_optimization_or_veto': False,
            'new_sky_coverage': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
        receipt_bytes = len((json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode())
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) + receipt_bytes <= scope['output_cap_bytes'],
                'Final completed receipt exceeds32MiB output budget')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        resources(root, scope, out)
    except BaseException as exc:
        if out is not None and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_S2017_CONTROL_TARGET_CONTEXT_EXECUTION_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'scope_sha256': args.scope_sha256,
                'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    main()
