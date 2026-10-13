#!/usr/bin/env python3
"""Portable NumPy-only replay of genuinely new fixed ON-origin contexts.

The previous 54 logical profiles are imported by exact byte provenance and
never numerically replayed here. All previous 48 raw normalization crops and
any new raw12096 crops are authenticated. Only the new physical queries are
independently replayed, without HDF5, detector imports, or optimization.

Prepare a final metadata-only SCOPE after producer outputs exist; execution
requires ROOT_GO with this exact scope and code SHA256. Preserve root-relative
paths when running from an unpacked portable package. Requires Python/NumPy.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time
import zipfile

for _thread_option in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_thread_option] = '1'

BASE = Path(__file__).resolve().parent
DEFAULT_ROOT = BASE.parent.parent
CORE, HALO, CHUNK = 4096, 4000, 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DC = (178782208, 179830784, 180879360)
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
CPU_CAP, WALL_CAP, RAM_CAP = 600, 900, 2 * 1024 ** 3
ATOL, RTOL = 1e-7, 1e-10
PRODUCER_SCOPE = 'on_cached/context/SCOPE.json'
PRODUCER_MATRIX = 'on_cached/context/results/CONTEXT_PROFILES.json'
PRODUCER_RECEIPT = 'on_cached/context/results/EXECUTION_RECEIPT.json'
BASELINE_IMPORT = 'on_cached/context/results/EXPOSED_BASELINE.json'
BASELINE_MATRIX = 'next_dc/crossscan/results/CONTEXT_PROFILES.json'
BASELINE_CROPS = 'next_dc/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json'
BASELINE_QA = 'next_dc/qa/context/QA_RECEIPT.json'
BASELINE_REPLAY = 'next_dc/qa/context/REPRODUCTION_RECEIPT.json'
SELECTED = 'on_cached/ranking/SELECTED_TOP9.json'
POST_QA_MANIFEST = 'on_cached/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json'
POST_QA_RECEIPT = 'on_cached/qa/context/QA_RECEIPT.json'
NORM_CENSUS = 'on_cached/feasibility/ON_NORMALIZATION_DOMAIN_CENSUS.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(path.read_bytes(), parse_constant=reject_constant)


def save_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Confined root-relative input required')
    candidate = root / relative
    require(not candidate.is_symlink(), 'Input symlink is not portable')
    path = candidate.resolve()
    require(path.is_relative_to(root), 'Input escapes portable root')
    return path


def file_pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def normal_key(declaration):
    return declaration['scan_id'], declaration['native_chunk_index'], declaration['core_q']


def profile_normal_key(profile):
    track = profile['canonical_selected_original_record']
    return profile['context_scan_id'], track['native_chunk_index'], track['core_q']


def metadata_prepare(args):
    """Authenticate declarations and freeze files; never load array members."""
    root = args.root.resolve()
    require(not args.scope.exists(), 'Do not overwrite prospective reproduction SCOPE')
    producer_scope = read(confined(root, PRODUCER_SCOPE))
    matrix = read(confined(root, PRODUCER_MATRIX))
    old = read(confined(root, BASELINE_MATRIX))
    crops = read(confined(root, BASELINE_CROPS))
    baseline = read(confined(root, BASELINE_IMPORT))
    receipt = read(confined(root, PRODUCER_RECEIPT))
    census = read(confined(root, NORM_CENSUS))
    require(producer_scope['schema'] == 'SETI_ON_CACHED_FIXED_CONTEXT_SCOPE_V1', 'Unexpected final context scope schema')
    require(matrix['schema'] == 'SETI_ON_CACHED_REUSE_AND_NEW_FIXED_CONTEXTS_V1', 'Unexpected final context matrix schema')
    require(receipt['status'] == 'COMPLETE_SELECTED_FIXED_CONTEXTS_WITH_EXACT_REUSE', 'Producer did not complete')
    require(receipt['scope_sha256'] == digest(confined(root, PRODUCER_SCOPE)), 'Producer receipt has different final scope')
    require(receipt['driver_sha256'] == producer_scope['driver_sha256'], 'Producer code receipt differs')
    require(len(old['profiles']) == 54 and len(crops['crops']) == 48, 'Prior 54 logical / 48 crop contract differs')
    require(baseline['baseline'] == old and baseline['recomputed_scores'] == 0 and baseline['new_source_float_queries'] == 0,
            'Exposed baseline was not imported exactly')
    require(len(matrix['new_physical_profiles']) == producer_scope['counts']['new_distinct_fixed_profile_queries'], 'New query count differs')
    require(len(matrix['selected_profiles']) == producer_scope['counts']['selected_logical_profiles'], 'Selected context count differs')
    require(census['status'] == 'PASS_ALL2298_EXACT_ORIGINAL4096_PHYSICAL_CORE_NORMALIZATIONS'
            and census['counts']['ON_map_normalizations'] == 2298
            and census['counts']['mismatching_records'] == 0, 'Original ON normalization census did not pass')
    declarations = {}

    def add(declaration):
        require(set(declaration) == {'path', 'bytes', 'sha256'}, 'A full root-relative byte pin is required')
        require(Path(declaration['path']).suffix != '.h5', 'Portable replay must not read HDF5 payloads')
        require(declaration['path'] not in declarations or declarations[declaration['path']] == declaration,
                'Conflicting declared input pins: ' + declaration['path'])
        actual = file_pin(root, confined(root, declaration['path']))
        require(actual == declaration, 'Input byte pin differs during prepare: ' + declaration['path'])
        declarations[declaration['path']] = declaration

    for name in (PRODUCER_SCOPE, PRODUCER_MATRIX, PRODUCER_RECEIPT, BASELINE_IMPORT,
                 BASELINE_MATRIX, BASELINE_CROPS, BASELINE_QA, BASELINE_REPLAY, SELECTED,
                 NORM_CENSUS,
                 'on_cached/context/driver.py', 'on_cached/context/PROSPECTIVE_CONTRACT.json',
                 'on_cached/reproduction/PROSPECTIVE_CONTRACT.json'):
        add(file_pin(root, confined(root, name)))
    # Preserve all portable producer input hashes; original HDF5 source hashes
    # are retained as historical declarations without opening those files.
    for declaration in producer_scope['input_byte_pins'].values():
        if Path(declaration['path']).suffix != '.h5':
            add(declaration)
    for profile in old['profiles']:
        add(profile['raw_capsule'])
        add(profile['normalization'])
    for crop in crops['crops'] + matrix['new_normalization_crops']:
        add(crop['crop'])
    for profile in matrix['new_physical_profiles']:
        add(profile['raw_capsule'])
        add(profile['normalization'])
    for logical in producer_scope['selected_logical_templates']:
        add(logical['selected_original_record']['map_pin'])
        add(logical['selected_original_record']['normalization_pin'])
    add(census['per_map_domain_and_original_source_pin_proof'])
    source_proof = read(confined(root, census['per_map_domain_and_original_source_pin_proof']['path']))
    require(source_proof['schema'] == 'SETI_ON_NORMALIZATION_DOMAIN_PER_MAP_SOURCE_PROOF_V1'
            and len(source_proof['records']) == 2298, 'Original ON per-map source proof differs')
    source_index = {(r['scan_id'], r['native_chunk_index'], r['core_q']): r for r in source_proof['records']}
    require(len(source_index) == 2298, 'Duplicate original ON per-map normalization identities')
    for logical in producer_scope['selected_logical_templates']:
        track = logical['selected_original_record']
        key = track['scan_id'], track['native_chunk_index'], track['core_q']
        require(key in source_index, 'Selected original normalization absent from census')
        declaration = source_index[key]
        require(declaration['normalization_pin'] == track['normalization_pin']
                and declaration['checkpoint_pin'] == track['original_checkpoint_pin']
                and declaration['classification'] == 'EXACT_ORIGINAL4096_PHYSICAL_CORE'
                and declaration['rowcount_metadata_values'] == [CORE] * 16,
                'Selected original normalization provenance or unmasked4096 domain differs')
        add(declaration['checkpoint_pin'])
    qa_available = confined(root, POST_QA_MANIFEST).is_file() and confined(root, POST_QA_RECEIPT).is_file()
    if qa_available:
        qa_manifest = read(confined(root, POST_QA_MANIFEST))
        qa_receipt = read(confined(root, POST_QA_RECEIPT))
        require(qa_receipt['status'].startswith('PASS') and not qa_receipt['mismatches'], 'Post context QA is not PASS')
        require(qa_manifest['schema'] == 'SETI_ON_CACHED_QA_NEW_CROP_MANIFEST_V1', 'Post QA crop schema differs')
        add(file_pin(root, confined(root, POST_QA_MANIFEST)))
        add(file_pin(root, confined(root, POST_QA_RECEIPT)))
        for crop in qa_manifest['crops'] + qa_manifest['reused_prior_authenticated_crops']:
            add(crop['crop'])
    scope = {
        'schema': 'SETI_ON_CACHED_PORTABLE_NEW_CONTEXT_REPRODUCTION_SCOPE_V1',
        'status': 'FROZEN_AFTER_PRODUCER_AND_BEFORE_INDEPENDENT_NUMERICAL_REPLAY',
        'code_sha256': digest(Path(__file__)),
        'final_context_scope_pin': declarations[PRODUCER_SCOPE],
        'producer_matrix_pin': declarations[PRODUCER_MATRIX],
        'post_context_QA_manifest_pin': declarations.get(POST_QA_MANIFEST),
        'normalization_census_pin': declarations[NORM_CENSUS],
        'normalization_per_map_source_proof_pin': census['per_map_domain_and_original_source_pin_proof'],
        'input_pins': [declarations[name] for name in sorted(declarations)],
        'excluded_HDF5_source_declarations': [d for d in producer_scope['input_byte_pins'].values() if Path(d['path']).suffix == '.h5'],
        'counts': {
            'baseline_logical_profiles_imported_without_numerical_replay': 54,
            'baseline_physical_profile_geometries': 48,
            'baseline_normalization_crops_authenticated': 48,
            'selected_logical_templates': len(producer_scope['selected_logical_templates']),
            'selected_logical_profiles': len(matrix['selected_profiles']),
            'new_physical_templates': len(producer_scope['new_physical_templates']),
            'new_physical_profiles_to_replay': len(matrix['new_physical_profiles']),
            'new_raw_normalization_crops_to_authenticate': len(matrix['new_normalization_crops']),
        },
        'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
        'limits': {'CPU_seconds': CPU_CAP, 'wall_seconds': WALL_CAP, 'RAM_bytes': RAM_CAP},
        'baseline_reuse_rule': 'Import original54 metadata and rawcapsule/normalization byte pins exactly; no numerical recomputation of their scores or rows. Verify all48 prior rawcrop file/member/row hashes. A prior crop may support a genuinely new template and then only its needed normalization is reconstructed.',
        'new_replay_rule': 'Independent full16/core4096/4000halo exact501 tiledmedian; residual MAD and winsorized location, fixed original box cells and row sums, own original per-carrier scalar, geometry/time/DC contact checks. No maximization, reranking, masking, HDF5 or detector imports.',
        'scope_outcome_dependence': 'Actual selected frozen tuples and producer bytes are pinned; no favorable outcomes alter this prospective algorithm or checks.',
        'ON_reference_rule': 'Selected reference_origin_scan_id==scan_id; preserve exact16 original_origin_row_times_from_reference_s. Transport context dt=(context.tstart-origin.tstart)*86400+original vector; own dt is exact original vector and is never derived by MJD cancellation.',
        'new_detector_grid': False, 'new_mask_or_veto': False,
        'new_telescope_requests': 0, 'qualified_SETI_detection': False,
    }
    save_new(args.scope, scope)
    print(json.dumps({'status': scope['status'], 'scope_sha256': digest(args.scope),
                      'code_sha256': scope['code_sha256'], 'counts': scope['counts']}))


def normalize_crop(raw, np):
    """Independent exact501 tiled medians over unchanged full4096 core."""
    core = raw[:, HALO:HALO + CORE].astype(np.float64)
    level = np.median(core, axis=1)
    require((level > 0).all() and np.isfinite(level).all(), 'Invalid row power median')
    residual = np.empty_like(core)
    for row in range(16):
        support = raw[row, HALO - 250:HALO + CORE + 250].astype(np.float64) / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(support, 501)
        for first in range(0, CORE, 512):
            last = min(first + 512, CORE)
            residual[row, first:last] = core[row, first:last] / level[row] - np.median(windows[first:last], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    require((scale > 0).all() and np.isfinite(scale).all(), 'Invalid independent MAD scale')
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    return {'row_power_median': level, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location,
            'normalization_unmasked_counts': [CORE] * 16}


def opaque_raw_power_member(path):
    """Authenticate NPY power storage as bytes without decoding any float."""
    with zipfile.ZipFile(path) as archive:
        require(archive.namelist().count('raw_power.npy') == 1, 'Unique raw_power member required')
        with archive.open('raw_power.npy') as stream:
            require(stream.read(6) == b'\x93NUMPY', 'Raw power member is not NPY')
            version = tuple(stream.read(2))
            require(version in ((1, 0), (2, 0), (3, 0)), 'Unsupported raw power NPY header version')
            length_bytes = stream.read(2 if version == (1, 0) else 4)
            length = struct.unpack('<H' if version == (1, 0) else '<I', length_bytes)[0]
            require(length <= 16384, 'Unreasonable raw power header size')
            header = ast.literal_eval(stream.read(length).decode('utf-8' if version == (3, 0) else 'latin1').strip())
            require(header == {'descr': '<f4', 'fortran_order': False, 'shape': (16, 12096)}, 'Raw power byte geometry differs')
            payload = stream.read()
            require(len(payload) == 16 * 12096 * 4, 'Raw power payload byte length differs')
    return payload


def run(args):
    root = args.root.resolve()
    require(not args.out.exists(), 'Do not overwrite portable reproduction receipt')
    scope, go = read(args.scope), read(args.go)
    require(go['authorized'] is True and go['scope_sha256'] == digest(args.scope)
            and go['code_sha256'] == digest(Path(__file__)), 'Exact public reproduction GO differs')
    require(scope['code_sha256'] == digest(Path(__file__)), 'Prepared code pin differs')
    require(scope['schema'] == 'SETI_ON_CACHED_PORTABLE_NEW_CONTEXT_REPRODUCTION_SCOPE_V1', 'Portable scope schema differs')
    require(scope['limits'] == {'CPU_seconds': CPU_CAP, 'wall_seconds': WALL_CAP, 'RAM_bytes': RAM_CAP}, 'Resource limits differ')
    require(scope['numeric_tolerance'] == {'absolute': ATOL, 'relative': RTOL}, 'Numerical tolerances differ')

    def timeout(signum, frame):
        raise TimeoutError('Portable replay resource cap')
    signal.signal(signal.SIGALRM, timeout)
    signal.signal(signal.SIGXCPU, timeout)
    signal.alarm(WALL_CAP)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    started, cpu_started = time.monotonic(), time.process_time()
    import numpy as np
    pins, mismatches, max_errors = {}, [], {}
    comparisons = 0

    def checked(declaration):
        require(set(declaration) == {'path', 'bytes', 'sha256'}, 'Exact portable byte declaration required')
        require(Path(declaration['path']).suffix != '.h5', 'HDF5 payload not admitted in portable replay')
        path = confined(root, declaration['path'])
        actual = file_pin(root, path)
        require(actual == declaration, 'Portable byte pin differs: ' + declaration['path'])
        require(declaration['path'] not in pins or pins[declaration['path']] == actual, 'Input changed during replay')
        pins[declaration['path']] = actual
        return path

    def compare(actual, expected, label, numeric=False, category=None):
        nonlocal comparisons
        comparisons += 1
        if numeric:
            a, b = np.asarray(actual), np.asarray(expected)
            same_shape = a.shape == b.shape
            ok = same_shape and np.isfinite(a).all() and np.isfinite(b).all() and np.allclose(a, b, atol=ATOL, rtol=RTOL)
            if same_shape and a.size:
                delta = float(np.max(np.abs(a - b)))
                max_errors[category or label] = max(max_errors.get(category or label, 0), delta)
        elif isinstance(actual, (dict, str, int, float, bool)) or actual is None:
            ok = actual == expected
        else:
            a, b = np.asarray(actual), np.asarray(expected)
            ok = a.shape == b.shape and np.array_equal(a, b)
        if not ok:
            mismatches.append(label)

    for declaration in scope['input_pins']:
        checked(declaration)
    declaration_by_path = {d['path']: d for d in scope['input_pins']}
    require(len(declaration_by_path) == len(scope['input_pins']), 'Duplicate portable input paths')

    def read_input(name):
        require(name in declaration_by_path, 'Required input omitted: ' + name)
        return read(checked(declaration_by_path[name]))

    producer_scope, matrix = read_input(PRODUCER_SCOPE), read_input(PRODUCER_MATRIX)
    old, old_crops = read_input(BASELINE_MATRIX), read_input(BASELINE_CROPS)
    baseline, producer_receipt = read_input(BASELINE_IMPORT), read_input(PRODUCER_RECEIPT)
    selection = read_input(SELECTED)
    require(producer_scope['schema'] == 'SETI_ON_CACHED_FIXED_CONTEXT_SCOPE_V1'
            and matrix['schema'] == 'SETI_ON_CACHED_REUSE_AND_NEW_FIXED_CONTEXTS_V1', 'Final producer contract differs')
    compare(scope['final_context_scope_pin'], declaration_by_path[PRODUCER_SCOPE], 'exact_final_context_scope_pin')
    compare(scope['producer_matrix_pin'], declaration_by_path[PRODUCER_MATRIX], 'exact_producer_matrix_pin')
    compare(producer_receipt['scope_sha256'], digest(confined(root, PRODUCER_SCOPE)), 'producer_scope_receipt_hash')
    compare(producer_receipt['driver_sha256'], producer_scope['driver_sha256'], 'producer_code_receipt_hash')
    compare(producer_scope['driver_sha256'], digest(confined(root, 'on_cached/context/driver.py')), 'producer_code_byte_hash')
    compare(baseline['source_matrix_pin'], declaration_by_path[BASELINE_MATRIX], 'baseline_import_source_pin')
    compare(baseline['baseline'], old, 'baseline_exact54_profile_import')
    compare(baseline['recomputed_scores'], 0, 'baseline_zero_score_recomputations')
    compare(baseline['new_source_float_queries'], 0, 'baseline_zero_new_source_queries')
    require(len(old['profiles']) == 54 and len(old_crops['crops']) == 48, 'Original baseline54/48 contract differs')
    require(len(producer_scope['exposed_baseline_templates']) == 8, 'Original eight physical template families differ')
    headers = producer_scope['headers']
    compare(selection['records'], [l['selected_original_record'] for l in producer_scope['selected_logical_templates']], 'final_selected_frozen_tuples')
    census = read_input(NORM_CENSUS)
    compare(scope['normalization_census_pin'], declaration_by_path[NORM_CENSUS], 'normalization_census_pin')
    compare(scope['normalization_per_map_source_proof_pin'], census['per_map_domain_and_original_source_pin_proof'], 'normalization_source_proof_pin')
    require(census['status'] == 'PASS_ALL2298_EXACT_ORIGINAL4096_PHYSICAL_CORE_NORMALIZATIONS'
            and census['counts']['ON_map_normalizations'] == 2298
            and census['counts']['mismatching_records'] == 0, 'Original ON normalization census did not pass')
    source_proof = read_input(census['per_map_domain_and_original_source_pin_proof']['path'])
    require(source_proof['schema'] == 'SETI_ON_NORMALIZATION_DOMAIN_PER_MAP_SOURCE_PROOF_V1'
            and len(source_proof['records']) == 2298, 'Original ON per-map source proof differs')
    original_norm_index = {(r['scan_id'], r['native_chunk_index'], r['core_q']): r for r in source_proof['records']}
    require(len(original_norm_index) == 2298, 'Original ON per-map identities are not unique')

    def elapsed_for(track, scan, require_ON=False):
        if 'reference_origin_scan_id' in track:
            origin = track['reference_origin_scan_id']
            times = np.asarray(track['original_origin_row_times_from_reference_s'], dtype=np.float64)
            require(origin == track['scan_id'] and track['original_acquisition_role'] == 'ON'
                    and track['primary_target'] == 'HIP98505', 'Original ON origin/role/target differs')
            require(np.array_equal(times, np.arange(16) * TSAMP), 'Exact original ON row-time vector differs')
            require(track['reference_time_mjd'] == headers[origin]['tstart'] + TSAMP / (2 * 86400), 'Original ON first midpoint differs from agreed producer contract')
        else:
            require(not require_ON, 'Selected original ON time fields are required')
            # Legacy baseline records define immutable old physical identities;
            # their earlier scores are imported rather than numerically replayed.
            origin, times = track['scan_id'], np.arange(16) * TSAMP
        elapsed = (headers[scan]['tstart'] - headers[origin]['tstart']) * 86400 + times
        if scan == origin:
            require(np.array_equal(elapsed, times), 'Own original time vector changed through transport')
        return elapsed

    def compare_normal_domain(normal, core0, label):
        expected = [core0, core0 + CORE]
        if 'normalization_source_channels' in normal:
            compare(normal['normalization_source_channels'], list(range(*expected)), label + '/explicit_source_channels')
        else:
            compare(normal.get('normalization_source_channel_interval_half_open'), expected, label + '/source_interval')
        compare(normal['normalization_unmasked_counts'], [CORE] * 16, label + '/full16_unmasked_counts')

    def physical_geometry(track):
        vectors = []
        for scan in SCANS:
            elapsed = elapsed_for(track, scan)
            centers = np.rint((track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                              + track['drift_hz_s'] * elapsed / DF).astype(np.int64)
            vectors.append(centers.tolist())
        value = {'native_chunk_index': track['native_chunk_index'], 'core_q': track['core_q'],
                 'width_channels': track['width_channels'], 'six_scan_rounded_absolute_centers': vectors}
        raw_geometry = {'width_channels': track['width_channels'], 'six_scan_rounded_absolute_centers': vectors}
        value['raw_geometry_id'] = hashlib.sha256(json.dumps(raw_geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        code = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return code, value

    # Baseline profiles/norms/raw503 are authenticated as bytes and exact JSON
    # metadata. Their earlier scores and row contributions are never replayed.
    baseline_physical = {}
    old_by_template_scan = {(p['template_id'], p['context_scan_id']): p for p in old['profiles']}
    require(len(old_by_template_scan) == 54, 'Baseline logical identities differ')
    for profile in old['profiles']:
        checked(profile['normalization'])
        checked(profile['raw_capsule'])
    for physical_id, value in producer_scope['exposed_baseline_templates'].items():
        aliases = value['logical_template_ids']
        require(aliases, 'Empty baseline physical alias list')
        per_scan = {scan: old_by_template_scan[aliases[0], scan] for scan in SCANS}
        for scan in SCANS:
            compare(per_scan[scan]['rounded_absolute_centers'], value['physical_geometry']['six_scan_rounded_absolute_centers'][SCANS.index(scan)], physical_id + '/' + scan + '/baseline_centers')
            compare(per_scan[scan]['width_channels'], value['physical_geometry']['width_channels'], physical_id + '/' + scan + '/baseline_width')
        baseline_physical[physical_id] = per_scan

    new_templates = {t['physical_template_id']: t for t in producer_scope['new_physical_templates']}
    require(len(new_templates) == len(producer_scope['new_physical_templates']), 'Duplicate new physical templates')
    require(not (set(new_templates) & set(baseline_physical)), 'New query overlaps exposed baseline')
    for physical_id, template in new_templates.items():
        code, value = physical_geometry(template['canonical_track'])
        compare(code, physical_id, physical_id + '/new_physical_identity')
        compare(value, template['physical_geometry'], physical_id + '/frozen_six_scan_geometry')
    new_profiles = matrix['new_physical_profiles']
    require(len(new_profiles) == len(new_templates) * 6, 'Each new template requires six fixed contexts')
    new_by_identity = {(p['physical_template_id'], p['context_scan_id']): p for p in new_profiles}
    require(len(new_by_identity) == len(new_profiles), 'Duplicate new physical context query')
    require(set(new_by_identity) == {(pid, scan) for pid in new_templates for scan in SCANS}, 'Missing or unexpected new query')
    crop_declarations = old_crops['crops'] + matrix['new_normalization_crops']
    crop_by_key = {normal_key(c): c for c in crop_declarations}
    require(len(crop_by_key) == len(crop_declarations), 'New normalization crop duplicates prior core/scan')
    require(len(old_crops['crops']) == 48, 'Baseline crop count differs')
    profiles_by_core = {}
    for profile in new_profiles:
        key = profile_normal_key(profile)
        require(key in crop_by_key, 'New query has no portable normalization crop')
        profiles_by_core.setdefault(key, []).append(profile)
    baseline_keys = {normal_key(c) for c in old_crops['crops']}
    expected_new_crop_keys = set(profiles_by_core) - baseline_keys
    compare(set(normal_key(c) for c in matrix['new_normalization_crops']), expected_new_crop_keys, 'new_crop_unique_core_mapping')
    qa_crop_assets, qa_crop_rows = 0, 0
    if scope['post_context_QA_manifest_pin'] is not None:
        qa_manifest, qa_receipt = read_input(POST_QA_MANIFEST), read_input(POST_QA_RECEIPT)
        compare(scope['post_context_QA_manifest_pin'], declaration_by_path[POST_QA_MANIFEST], 'post_QA_manifest_pin')
        compare(qa_manifest['schema'], 'SETI_ON_CACHED_QA_NEW_CROP_MANIFEST_V1', 'post_QA_manifest_schema')
        require(qa_receipt['status'].startswith('PASS') and not qa_receipt['mismatches'], 'Post context QA is not PASS')
        compare(qa_manifest['baseline_raw_authentication_receipt'], declaration_by_path[BASELINE_QA], 'post_QA_prior_authentication_link')
        compare(set(normal_key(c) for c in qa_manifest['crops']), expected_new_crop_keys, 'post_QA_new_crop_core_coverage')
        compare(set(normal_key(c) for c in qa_manifest['reused_prior_authenticated_crops']), set(profiles_by_core) & baseline_keys, 'post_QA_reused_prior_crop_coverage')
        compare(qa_manifest['crop_count'], len(qa_manifest['crops']), 'post_QA_new_crop_count')
        for declaration in qa_manifest['crops'] + qa_manifest['reused_prior_authenticated_crops']:
            key = normal_key(declaration)
            canonical = crop_by_key[key]
            label = '/'.join(map(str, key)) + '/post_QA'
            for field in ('shape', 'absolute_source_channel_interval_half_open', 'normalization_source_channel_interval_half_open', 'raw_float32_sha256', 'raw_float32_source_row_sha256'):
                compare(declaration[field], canonical[field], label + '/' + field)
            compare(sorted(declaration['physical_profile_ids']), sorted(p['profile_id'] for p in profiles_by_core[key]), label + '/physical_profile_mapping')
            qa_raw_bytes = opaque_raw_power_member(checked(declaration['crop']))
            compare(hashlib.sha256(qa_raw_bytes).hexdigest(), declaration['raw_float32_sha256'], label + '/raw_payload_SHA256')
            for row in range(16):
                row_bytes = qa_raw_bytes[row * 12096 * 4:(row + 1) * 12096 * 4]
                compare(hashlib.sha256(row_bytes).hexdigest(), declaration['raw_float32_source_row_sha256'][row], label + '/row_' + str(row) + '_SHA256')
                qa_crop_rows += 1
            qa_crop_assets += 1
    replayed, replay_scores = {}, {}
    authenticated_rows, normalization_cores, raw503_cells, power_float_cells_decoded = 0, 0, 0, 0

    for declaration in crop_declarations:
        key = normal_key(declaration)
        scan, native, q = key
        core0, crop0 = native * CHUNK + q * CORE, native * CHUNK + q * CORE - HALO
        crop_path = checked(declaration['crop'])
        raw_bytes = opaque_raw_power_member(crop_path)
        with np.load(crop_path, allow_pickle=False) as saved:
            crop = {k: saved[k].copy() for k in saved.files if k != 'raw_power'}
        label = '/'.join(map(str, key))
        compare(declaration['shape'], [16, 12096], label + '/declared_shape')
        compare(crop['absolute_source_channel_interval_half_open'], [crop0, crop0 + 12096], label + '/crop_channel_domain')
        compare(declaration['absolute_source_channel_interval_half_open'], [crop0, crop0 + 12096], label + '/declared_crop_domain')
        compare(crop['normalization_source_channel_interval_half_open'], [core0, core0 + CORE], label + '/core_channel_domain')
        compare(declaration['normalization_source_channel_interval_half_open'], [core0, core0 + CORE], label + '/declared_core_domain')
        compare(crop['source_rows'], np.arange(16), label + '/source_rows')
        compare(crop['tstart_mjd'], headers[scan]['tstart'], label + '/tstart')
        compare(crop['tsamp_s'], TSAMP, label + '/tsamp')
        compare(hashlib.sha256(raw_bytes).hexdigest(), declaration['raw_float32_sha256'], label + '/raw_float32_SHA256')
        require(len(declaration['raw_float32_source_row_sha256']) == 16, 'Sixteen crop row hashes required')
        for row in range(16):
            row_bytes = raw_bytes[row * 12096 * 4:(row + 1) * 12096 * 4]
            compare(hashlib.sha256(row_bytes).hexdigest(), declaration['raw_float32_source_row_sha256'][row], label + '/row_' + str(row) + '_SHA256')
            authenticated_rows += 1
        if key in baseline_keys:
            prior_ids = [p['profile_id'] for p in old['profiles'] if p['context_scan_id'] == scan
                         and p['selected_original_record']['native_chunk_index'] == native and p['selected_original_record']['core_q'] == q]
            compare(declaration['profile_ids'], prior_ids, label + '/baseline_profile_crop_map')
        if key not in profiles_by_core:
            del crop, raw_bytes
            continue
        # A prior crop can be needed by a new geometry, but no prior profile
        # scores or row sums are recomputed by this normalization replay.
        raw = np.frombuffer(raw_bytes, dtype='<f4').reshape(16, 12096)
        power_float_cells_decoded += 16 * 12096
        require(np.isfinite(raw).all() and (raw >= 0).all(), 'Invalid new-query crop powers')
        norm = normalize_crop(raw, np)
        normalization_cores += 1
        for profile in profiles_by_core[key]:
            physical_id, profile_id = profile['physical_template_id'], profile['profile_id']
            track = new_templates[physical_id]['canonical_track']
            compare(profile['canonical_selected_original_record'], track, profile_id + '/canonical_frozen_track')
            compare(profile['raw_geometry_id'], new_templates[physical_id]['physical_geometry']['raw_geometry_id'], profile_id + '/raw_geometry_id')
            require(track['width_channels'] in (1, 3), 'Unchanged original width required')
            width = track['width_channels']
            saved_norm = read(checked(profile['normalization']))
            compare(saved_norm['normalization_source_channel_interval_half_open'], [core0, core0 + CORE], profile_id + '/norm_domain')
            compare(saved_norm['normalization_unmasked_counts'], [CORE] * 16, profile_id + '/norm_counts')
            for term in ('row_power_median', 'row_residual_median', 'row_residual_MAD_scale', 'row_winsorized_residual_location'):
                compare(norm[term], saved_norm[term], profile_id + '/' + term, True, term)
            provenance = profile['normalization_provenance']
            compare(provenance['raw_crop'], declaration['crop'], profile_id + '/normalization_crop_provenance')
            compare(provenance['normalization'], profile['normalization'], profile_id + '/normalization_pin_provenance')
            compare(provenance['kind'], 'PINNED_PREVIOUS_FULLCORE_CROP_AND_NORMALIZATION' if key in baseline_keys else 'NEW_ORIGINAL_STATIC_FULL16_PREPROCESS', profile_id + '/normalization_disposition')
            elapsed = elapsed_for(track, scan, require_ON=True)
            centers = np.rint((track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                              + track['drift_hz_s'] * elapsed / DF).astype(np.int64)
            midpoint = [headers[scan]['tstart'] + (row + .5) * TSAMP / 86400 for row in range(16)]
            compare(centers, profile['rounded_absolute_centers'], profile_id + '/rounded_centers')
            compare(centers, new_templates[physical_id]['physical_geometry']['six_scan_rounded_absolute_centers'][SCANS.index(scan)], profile_id + '/scope_centers')
            compare(width, profile['width_channels'], profile_id + '/original_width')
            compare(elapsed, profile['times_from_primary_reference_s'], profile_id + '/elapsed_seconds')
            compare(midpoint, profile['row_midpoint_mjd'], profile_id + '/row_midpoint_mjd')
            compare(headers[scan]['source_name'], profile['context_target'], profile_id + '/context_target')
            compare('ON' if scan.endswith('_on') else 'OFF', profile['original_acquisition_role'], profile_id + '/original_role')
            compare(scan.endswith('_on'), profile['same_target_ON_scan_within_one_visit'], profile_id + '/same_target_one_visit')
            compare(False, profile['independent_sky_confirmation'], profile_id + '/no_independent_sky_confirmation')
            indices = centers[:, None] - crop0 + np.arange(-251, 252)[None, :]
            require((indices >= 0).all() and (indices < 12096).all(), 'Frozen profile lacks raw503 support')
            profile_raw = raw[np.arange(16)[:, None], indices]
            with np.load(checked(profile['raw_capsule']), allow_pickle=False) as saved:
                capsule = {k: saved[k].copy() for k in saved.files}
            compare(profile_raw.view(np.uint32), capsule['raw_power'].view(np.uint32), profile_id + '/raw503_bit_identity')
            compare(centers, capsule['rounded_absolute_centers'], profile_id + '/capsule_centers')
            compare(elapsed, capsule['times_from_primary_reference_s'], profile_id + '/capsule_elapsed')
            compare(capsule['source_rows'], np.arange(16), profile_id + '/capsule_source_rows')
            ratio = profile_raw.astype(np.float64) / np.asarray(norm['row_power_median'])[:, None]
            columns = np.asarray([250, 251, 252]) if width == 3 else np.asarray([251])
            medians = np.column_stack([np.median(ratio[:, col - 250:col + 251], axis=1) for col in columns])
            cells = (ratio[:, columns] - medians - np.asarray(norm['row_winsorized_residual_location'])[:, None]) / np.asarray(norm['row_residual_MAD_scale'])[:, None]
            terms = cells.sum(axis=1, dtype=np.float64)
            contribution = terms / math.sqrt(16 * width)
            score = float(terms.sum(dtype=np.float64) / math.sqrt(16 * width))
            compare(cells, capsule['standardized_original_box_cells'], profile_id + '/box_cells', True, 'original_box_cells')
            compare(terms, capsule['standardized_row_box_sums'], profile_id + '/capsule_row_sums', True, 'row_standardized_box_sum')
            compare(terms, profile['row_standardized_box_sum'], profile_id + '/canonical_row_sums', True, 'row_standardized_box_sum')
            compare(contribution, capsule['row_score_contribution'], profile_id + '/capsule_contributions', True, 'row_score_contribution')
            compare(contribution, profile['row_score_contribution'], profile_id + '/canonical_contributions', True, 'row_score_contribution')
            compare(score, profile['fixed_robust_box_track_score'], profile_id + '/fixed_score', True, 'fixed_robust_box_track_score')
            positive = np.maximum(contribution, 0.)
            positive_total = float(positive.sum())
            max_fraction = float(positive.max() / positive_total) if positive_total else None
            compare(int((positive > 0).sum()), profile['positive_row_count'], profile_id + '/positive_row_count')
            compare(max_fraction, profile['positive_row_contribution_max_fraction'], profile_id + '/positive_max_fraction', max_fraction is not None, 'positive_row_fraction')
            contact = np.any(np.abs(centers[:, None] - np.asarray(DC)[None, :]) <= width // 2, axis=1)
            compare(np.flatnonzero(contact), profile['DC_contact_rows_any_frozen_center'], profile_id + '/DC_contacts')
            compare(profile['query_disposition'], 'NEW_FIXED_QUERY', profile_id + '/new_query_disposition')
            replayed[physical_id, scan] = profile
            replay_scores[physical_id, scan] = score
            raw503_cells += 16 * 503
        del crop, raw, raw_bytes

    require(set(replayed) == set(new_by_identity), 'Not every new physical profile was replayed once')
    selected = matrix['selected_profiles']
    logical_index = {l['template_id']: l for l in producer_scope['selected_logical_templates']}
    require(len(logical_index) == len(producer_scope['selected_logical_templates']), 'Duplicate selected logical templates')
    selected_by_identity = {(p['template_id'], p['context_scan_id']): p for p in selected}
    require(len(selected_by_identity) == len(selected), 'Duplicate selected logical context')
    require(set(selected_by_identity) == {(tid, scan) for tid in logical_index for scan in SCANS}, 'Selected six-scan coverage differs')
    own_check_index = {c['template_id']: c for c in matrix['own_per_carrier_score_checks']}
    require(set(own_check_index) == set(logical_index), 'Own scalar checks omit or add selected templates')
    maps, own_scalar_checks, baseline_selected_reuses = {}, 0, 0
    for template_id, logical in logical_index.items():
        track, physical_id = logical['selected_original_record'], logical['physical_template_id']
        require(template_id == track['scan_id'] + '_rank' + str(track['exploratory_selection_rank']), 'Selected ON logical identifier differs')
        elapsed_for(track, track['scan_id'], require_ON=True)
        code, geometry = physical_geometry(track)
        compare(code, physical_id, template_id + '/selected_physical_identity')
        compare(geometry, logical['physical_geometry'], template_id + '/selected_frozen_geometry')
        compare(geometry['raw_geometry_id'], logical['raw_geometry_id'], template_id + '/raw_geometry_id')
        compare(logical['reuse_baseline'], physical_id in baseline_physical, template_id + '/reuse_disposition')
        for scan in SCANS:
            profile = selected_by_identity[template_id, scan]
            compare(profile['selected_original_record'], track, template_id + '/' + scan + '/selected_record')
            compare(profile['physical_template_id'], physical_id, template_id + '/' + scan + '/physical_alias_id')
            compare(profile['raw_geometry_id'], geometry['raw_geometry_id'], template_id + '/' + scan + '/selected_raw_geometry_id')
            elapsed = elapsed_for(track, scan, require_ON=True)
            compare(elapsed, profile['times_from_primary_reference_s'], template_id + '/' + scan + '/logical_elapsed')
            source = baseline_physical[physical_id][scan] if logical['reuse_baseline'] else new_by_identity[physical_id, scan]
            compare(profile['source_fixed_profile'], source, template_id + '/' + scan + '/exact_nested_source_profile')
            compare(source['rounded_absolute_centers'], geometry['six_scan_rounded_absolute_centers'][SCANS.index(scan)], template_id + '/' + scan + '/nested_geometry')
            compare(source['width_channels'], track['width_channels'], template_id + '/' + scan + '/nested_width')
            compare(profile['baseline_matrix_pin'], declaration_by_path[BASELINE_MATRIX] if logical['reuse_baseline'] else None, template_id + '/' + scan + '/baseline_pin')
            compare(profile['previous_raw_capsule_reference_metadata_retained'], logical['reuse_baseline'], template_id + '/' + scan + '/baseline_capsule_reference')
            compare(profile['query_disposition'], 'HASH_PINNED_BASELINE_REUSE' if logical['reuse_baseline'] else 'NEW_FIXED_QUERY_OR_CURRENT_LOGICAL_ALIAS', template_id + '/' + scan + '/logical_query_disposition')
            compare(profile['same_target_ON_scan_within_one_visit'], scan.endswith('_on'), template_id + '/' + scan + '/same_target_one_visit')
            compare(profile['independent_sky_confirmation'], False, template_id + '/' + scan + '/no_independent_sky_confirmation')
            baseline_selected_reuses += int(logical['reuse_baseline'])
        map_declaration = track['map_pin']
        if map_declaration['path'] not in maps:
            with np.load(checked(map_declaration), allow_pickle=False) as saved:
                maps[map_declaration['path']] = {k: saved[k].copy() for k in ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_width_channels', 'source_reference_channels')}
        original = maps[map_declaration['path']]
        carrier = track['carrier_index_in_core']
        require(0 <= carrier < CORE, 'Frozen original carrier outside core')
        compare(float(original['maximum_robust_box_track_score'][carrier]), track['score'], template_id + '/original_map_scalar')
        compare(float(original['winning_drift_hz_s'][carrier]), track['drift_hz_s'], template_id + '/original_map_drift')
        compare(int(original['winning_width_channels'][carrier]), track['width_channels'], template_id + '/original_map_width')
        compare(int(original['source_reference_channels'][carrier]), track['reference_source_channel'], template_id + '/original_map_reference_channel')
        compare(track['frequency_hz_at_own_first_midpoint'], FCH1 + track['reference_source_channel'] * DF, template_id + '/original_own_frequency')
        own_source = baseline_physical[physical_id][track['scan_id']] if logical['reuse_baseline'] else new_by_identity[physical_id, track['scan_id']]
        original_normal = read(checked(track['normalization_pin']))
        own_normal = read(checked(own_source['normalization']))
        core0 = track['native_chunk_index'] * CHUNK + track['core_q'] * CORE
        compare_normal_domain(original_normal, core0, template_id + '/original_normalization_domain')
        compare_normal_domain(own_normal, core0, template_id + '/own_normalization_domain')
        proof_key = track['scan_id'], track['native_chunk_index'], track['core_q']
        require(proof_key in original_norm_index, 'Selected original normalization absent from source proof')
        proof = original_norm_index[proof_key]
        compare(proof['normalization_pin'], track['normalization_pin'], template_id + '/original_source_normalization_pin')
        compare(proof['checkpoint_pin'], track['original_checkpoint_pin'], template_id + '/original_source_checkpoint_pin')
        compare(proof['classification'], 'EXACT_ORIGINAL4096_PHYSICAL_CORE', template_id + '/original_domain_classification')
        compare(proof['physical_core_interval_half_open'], [core0, core0 + CORE], template_id + '/original_proved_core')
        compare(proof['rowcount_metadata_values'], [CORE] * 16, template_id + '/original_proved_unmasked_counts')
        checked(proof['checkpoint_pin'])
        for term in ('row_power_median', 'row_residual_median', 'row_residual_MAD_scale', 'row_winsorized_residual_location'):
            compare(own_normal[term], original_normal[term], template_id + '/original_own_' + term, True, 'original_own_' + term)
        own_score = own_source['fixed_robust_box_track_score'] if logical['reuse_baseline'] else replay_scores[physical_id, track['scan_id']]
        compare(own_score, track['score'], template_id + '/own_selected_scalar', True, 'own_original_selected_score')
        saved_check = own_check_index[template_id]
        compare(saved_check['map_pin'], map_declaration, template_id + '/own_check_map_pin')
        compare(saved_check['carrier_index_in_core'], carrier, template_id + '/own_check_carrier')
        compare(saved_check['original_score'], track['score'], template_id + '/own_check_original_scalar')
        compare(saved_check['fixed_own_score'], own_source['fixed_robust_box_track_score'], template_id + '/own_check_source_scalar')
        compare(saved_check['absolute_difference'], abs(own_source['fixed_robust_box_track_score'] - track['score']), template_id + '/own_check_absolute_difference')
        compare(saved_check['reused_score'], logical['reuse_baseline'], template_id + '/own_check_reuse')
        own_scalar_checks += 1

    compare(len(new_profiles), matrix['new_distinct_fixed_profile_queries'], 'producer_new_query_count')
    compare(len(expected_new_crop_keys), matrix['new_full16_normalizations'], 'producer_new_normalization_count')
    compare(len(set(profiles_by_core) & baseline_keys), matrix['prior_raw_normalization_crop_queries_reused'], 'producer_prior_crop_query_count')
    compare(len(matrix['new_normalizations']), len(expected_new_crop_keys), 'producer_new_normalization_record_count')
    compare(len(new_profiles), scope['counts']['new_physical_profiles_to_replay'], 'scope_new_query_count')
    compare(len(selected), scope['counts']['selected_logical_profiles'], 'scope_selected_profile_count')
    compare(len({l['raw_geometry_id'] for l in logical_index.values()}), producer_scope['counts']['selected_distinct_raw_template_geometries'], 'selected_raw_template_geometry_count')
    compare(len({l['physical_template_id'] for l in logical_index.values()}), producer_scope['counts']['selected_distinct_normalized_template_geometries'], 'selected_normalized_template_geometry_count')
    compare(producer_scope['transport_convention_is_new_fixed_context_rule'], True, 'new_fixed_transport_convention')
    compare(producer_scope['transport_is_not_claimed_bitwise_replay_of_prior_gap_fixed_profiles'], True, 'no_bitwise_prior_gap_transport_claim')
    for flag in ('new_detector_grid', 'new_mask_or_veto', 'qualified_SETI_detection', 'calibrated_SNR_or_FAP'):
        compare(matrix[flag], False, 'producer/' + flag)
    compare(matrix['new_telescope_requests'], 0, 'producer/no_new_telescope_requests')
    for name, old_pin in pins.items():
        require(file_pin(root, confined(root, name)) == old_pin, 'Portable input bytes changed at close: ' + name)
    cpu, wall = time.process_time() - cpu_started, time.monotonic() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    require(cpu <= CPU_CAP and wall <= WALL_CAP and rss <= RAM_CAP, 'Measured portable resource cap exceeded')
    result = {
        'schema': 'SETI_ON_CACHED_PORTABLE_NUMPY_ONLY_NEW_CONTEXT_REPRODUCTION_V1',
        'status': 'PASS_NUMPY_ONLY_BASELINE_IMPORT_AND_NEW_FIXED_CONTEXTS' if not mismatches else 'FAIL_MISMATCHES_PRESERVED',
        'scope_sha256': digest(args.scope), 'code_sha256': digest(Path(__file__)),
        'final_context_scope_pin': declaration_by_path[PRODUCER_SCOPE],
        'counts': {
            'baseline_logical_profiles_imported_without_numerical_replay': 54,
            'baseline_physical_geometries_imported': 48,
            'baseline_scores_recomputed': 0,
            'baseline_raw_normalization_crops_authenticated': 48,
            'new_raw_normalization_crops_authenticated': len(matrix['new_normalization_crops']),
            'authenticated_rawcrop_rows_SHA256': authenticated_rows,
            'post_QA_crop_assets_authenticated_as_opaque_bytes': qa_crop_assets,
            'post_QA_crop_rows_authenticated_as_opaque_bytes': qa_crop_rows,
            'source_power_float_cells_decoded_for_new_queries_only': power_float_cells_decoded,
            'independent_full16_normalization_cores_for_new_queries': normalization_cores,
            'fullcore501_median_positions_for_new_queries': normalization_cores * 16 * CORE,
            'normalization_row_terms_for_new_queries': normalization_cores * 16 * 4,
            'new_physical_templates_replayed': len(new_templates),
            'new_distinct_fixed_profiles_replayed': len(replayed),
            'new_raw503_profile_cells_bit_verified': raw503_cells,
            'selected_logical_context_profiles_verified': len(selected),
            'selected_context_baseline_reuses': baseline_selected_reuses,
            'selected_own_per_carrier_scalar_checks': own_scalar_checks,
            'comparisons': comparisons,
        },
        'mismatches': mismatches, 'max_absolute_errors': max_errors,
        'input_pins_before_and_after': [pins[name] for name in sorted(pins)],
        'CPU_seconds': cpu, 'wall_seconds': wall, 'peak_RSS_bytes': rss,
        'runtime': {'Python': sys.version.split()[0], 'numpy': np.__version__},
        'limits': scope['limits'], 'HDF5_files_opened': 0, 'HDF5_or_hdf5plugin_imported': False,
        'detector_imported': False, 'new_search_or_mask': False, 'new_telescope_requests': 0,
        'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False,
        'limitations': [
            'Original HDF5 byte identities and decoded-row source authentication are inherited from pinned producer/source QA receipts. This portable replay opens no HDF5 source files.',
            'Previously exposed54 profiles retain original values and provenance without repeated numerical analysis. Independent numerical replay is restricted to genuinely new physical queries.',
            'Original search maximization, selection completeness and multi-trial false-alarm calibration are not reproduced. No independent repeated sky observation or astrophysical-origin confirmation follows.',
        ],
    }
    save_new(args.out, result)
    signal.alarm(0)
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins_before_and_after', 'runtime', 'limitations')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--scope', type=Path, default=BASE / 'SCOPE.json')
    parser.add_argument('--go', type=Path, default=BASE / 'ROOT_GO.json')
    parser.add_argument('--out', type=Path, default=BASE / 'REPRODUCTION_RECEIPT.json')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps({'status': 'PROSPECTIVE_NUMPY_ONLY_NEW_CONTEXT_REPLAY_PREPARED',
                          'code_sha256': digest(Path(__file__)), 'opens_HDF5': False,
                          'baseline_scores_recomputed': 0}))
    elif args.prepare:
        metadata_prepare(args)
    else:
        run(args)


if __name__ == '__main__':
    main()
