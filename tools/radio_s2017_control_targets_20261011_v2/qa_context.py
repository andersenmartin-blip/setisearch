"""Independent one-shot QA of54 saved fixed six-scan control-track contexts.

No detector import or grid search. Six native sources are decoded once after
three primary COMPLETE receipts, actual primary saved-map QA, context COMPLETE,
public source/scope freeze and root GO. Raw503 windows independently reconstruct
the declared local501 standardized score conditional on saved MAD/location.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import time

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
BASE = 'analysis/s2017_control_targets_20261011_v2'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
TARGETS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')
COUNT, CORE, C0 = 1048576, 4096, 171 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP, WORKSPACE_CAP = 180, 300, 2 * 1024**3, 2 * 1024**2, 8 * 1024**3
ATOL, RTOL = 1e-7, 1e-10
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0', 'HDF5': '1.14.6'}
SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ACQ = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
OLDQA = 'analysis/new_visit_recovery/results/review/QA_RECEIPT.json'
PINS = {SOURCE: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    ACQ: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    OLDQA: 'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f'}


def check(test, message):
    if not test:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def save_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def confined(root, name):
    p = Path(name)
    check(not p.is_absolute() and '..' not in p.parts, 'Confined relative input required')
    path = root / p
    check(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined/symlink input')
    return path


def same(a, b, message):
    a, b = np.asarray(a), np.asarray(b)
    check(a.shape == b.shape and np.array_equal(a, b), message)


def near(a, b, message):
    a, b = np.asarray(a), np.asarray(b)
    check(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
          and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'qa-sha256', 'qa-scope-sha256', 'context-scope-sha256', 'context-receipt-sha256',
                 'primary-qa-receipt-sha256', 'freeze-commit', 'qa-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-context-complete', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    check(args.root_go_after_context_complete and all(re.fullmatch('[0-9a-f]{40}', x)
          for x in (args.freeze_commit, args.qa_freeze_commit)), 'Exact public freezes and root context QA GO required')
    for value in (args.qa_sha256, args.qa_scope_sha256, args.context_scope_sha256,
                  args.context_receipt_sha256, args.primary_qa_receipt_sha256):
        check(re.fullmatch('[0-9a-f]{64}', value), 'Exact reviewed closed SHA256 required')
    check(digest(Path(__file__).resolve()) == args.qa_sha256, 'Reviewed context QA source differs')
    expected = {'selected_tracks': 9, 'fixed_profiles': 54, 'raw503_capsules': 54,
        'raw_power_cells': 54 * 16 * 503, 'source_compacts': 6, 'source_decoded_rows': 96,
        'conditional_normalization_core_row_medians': 54 * 16, 'independent_fixed_scores': 54,
        'origin_primary_score_matches': 9}
    counts, pins, handles = {key: 0 for key in expected}, {}, []
    out = root / BASE / 'results/context_review'
    created_output = False
    max_row_difference, max_score_difference, max_origin_difference = 0., 0., 0.

    def loaded(path, declared=None):
        raw = path.read_bytes()
        actual = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        check(declared is None or actual == declared, 'Exact loaded byte pin differs')
        key = path.relative_to(root).as_posix()
        check(key not in pins or pins[key] == actual, 'Input changed during QA')
        pins[key] = actual
        return raw

    def pin(path, declared=None):
        actual = {'sha256': digest(path), 'bytes': path.stat().st_size}
        check(declared is None or actual == declared, 'Exact file byte pin differs')
        key = path.relative_to(root).as_posix()
        check(key not in pins or pins[key] == actual, 'Input changed during QA')
        pins[key] = actual
        return actual

    def text(path, sha=None):
        raw = loaded(path)
        check(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Reviewed metadata SHA differs')
        return json.loads(raw, object_pairs_hook=pairs)

    def archive(path, declaration):
        raw = loaded(path, {key: declaration[key] for key in ('sha256', 'bytes')})
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            check(len(values.files) == len(set(values.files)), 'Duplicate NPZ fields')
            return {key: values[key] for key in values.files}

    def deadline(signum, frame):
        raise TimeoutError('Prospective independent context QA CPU/wall cap reached')

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        pin(Path(__file__).resolve())
        for name in ('ACTIVE_FAMILY_FLOCK.lock', 'ACTIVE_CONTEXT_FLOCK.lock',
                     'ACTIVE_SCIENCE_SLOT_0_FLOCK.lock', 'ACTIVE_SCIENCE_SLOT_1_FLOCK.lock',
                     'ACTIVE_SCIENCE_SLOT_2_FLOCK.lock'):
            handle = (root / BASE / name).open('a+b')
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle = (root / 'analysis/new_visit_recovery/results/ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        handles.append(handle)
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        qa_scope = text(root / BASE / 'qa_context_scope.json', args.qa_scope_sha256)
        check(qa_scope['schema'] == 'SETI_S2017_CONTROL_TARGET_CONTEXT_INDEPENDENT_QA_SCOPE_V1'
              and qa_scope['qa_source_sha256'] == args.qa_sha256
              and qa_scope['context_scope_sha256'] == args.context_scope_sha256
              and qa_scope['expected_counts'] == expected and qa_scope['CPU_cap_s'] == CPU_CAP
              and qa_scope['wall_cap_s'] == WALL_CAP and qa_scope['memory_cap_bytes'] == RAM_CAP
              and qa_scope['output_cap_bytes'] == OUTPUT_CAP and qa_scope['workspace_cap_bytes'] == WORKSPACE_CAP
              and qa_scope['numeric_tolerance'] == {'absolute': ATOL, 'relative': RTOL},
              'Separate reviewed context QA scope differs')
        helper_path = root / BASE / 'qa_saved.py'
        check(pin(helper_path)['sha256'] == qa_scope['independent_arithmetic_helper_sha256'],
              'Independent local501 arithmetic helper differs')
        context_scope = text(root / BASE / 'context_scope.json', args.context_scope_sha256)
        for name, sha in context_scope['text_code_pins'].items():
            path = confined(root, name)
            check(path.suffix in ('.py', '.json') and pin(path)['sha256'] == sha, 'Context code/metadata pin differs')
        check(context_scope['text_code_pins'][BASE + '/context_profiles.py'] == qa_scope['context_driver_sha256'],
              'Reviewed context driver differs')
        mapqa = text(root / BASE / 'results/review/QA_RECEIPT.json', args.primary_qa_receipt_sha256)
        check(mapqa['schema'] == 'SETI_S2017_CONTROL_TARGET_SAVED_INDEPENDENT_QA_V1'
              and mapqa['status'] == 'PASS753_ORIGINAL_OFF_MAPS3021_RAW_SCORE_QUERIES_NO_DETECTOR_RERUN'
              and mapqa['counts']['maps'] == 753 and mapqa['counts']['score_audit_queries'] == 3021
              and mapqa['public_freeze_commit'] == args.freeze_commit,
              'Actual independent primary saved-map QA PASS required')
        selected_tracks = []
        for target in TARGETS:
            top = text(root / BASE / 'results' / target / 'TOP3.json')
            key = BASE + '/results/' + target + '/TOP3.json'
            check(mapqa['input_byte_pins'][key] == pins[key] and top['records'] == mapqa['selected_top3'][target],
                  'Selected context tuple differs from actual primary QA')
            selected_tracks.extend(top['records'])
            receipt = text(root / BASE / 'results' / target / 'EXECUTION_RECEIPT.json', mapqa['primary_receipt_sha256s'][target])
            check(receipt['status'] == 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY',
                  'All three actual primary COMPLETE receipts required')
        execution = text(root / BASE / 'results/context/EXECUTION_RECEIPT.json', args.context_receipt_sha256)
        check(execution['schema'] == 'SETI_S2017_CONTROL_TARGET_CONTEXT_EXECUTION_V1'
              and execution['status'] == 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES_NO_OPTIMIZATION'
              and execution['runtime_versions'] == VERSIONS
              and execution['scope_sha256'] == args.context_scope_sha256
              and execution['context_driver_sha256'] == qa_scope['context_driver_sha256']
              and execution['primary_scope_sha256'] == mapqa['scope_sha256']
              and execution['primary_receipt_sha256s'] == mapqa['primary_receipt_sha256s']
              and execution['actual_primary_QA_receipt_sha256'] == args.primary_qa_receipt_sha256
              and execution['public_freeze_commit'] == args.freeze_commit,
              'Actual closed context receipt/version required')
        context_counts = {'selected_tracks': 9, 'context_scores': 54, 'source_files': 6,
            'source_decoded_rows': 96, 'raw_source_capsule_cells': 54 * 16 * 503, 'origin_score_matches': 9}
        check(execution['counts'] == context_counts and execution['CPU_cap_s'] == 180
              and execution['wall_cap_s'] == 300 and execution['memory_cap_bytes'] == RAM_CAP
              and execution['output_cap_bytes'] == 32 * 1024**2 and execution['workspace_cap_bytes'] == WORKSPACE_CAP
              and 0 < execution['process_CPU_seconds'] <= 180 and 0 < execution['wall_seconds'] <= 300
              and 0 < execution['peak_RSS_bytes'] <= RAM_CAP
              and 0 < execution['workspace_allocated_bytes_final'] <= WORKSPACE_CAP
              and execution['score_match_absolute_tolerance'] == ATOL
              and execution['score_match_relative_tolerance'] == RTOL
              and execution['new_HTTP_requests'] == 0 and execution['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED',
              'Exact completed context counts/caps/tolerance/network admission differs')
        for key in ('detector_grid_or_carrier_drift_search', 'new_fit_optimization_or_veto', 'new_sky_coverage',
                    'qualified_SETI_detection', 'calibrated_SNR_FAP'):
            check(execution[key] is False, 'Context receipt scope claim differs')
        gates = {name: text(root / name, sha) for name, sha in PINS.items()}
        source, acquisition, oldqa = (gates[name] for name in PINS)
        check(acquisition['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
              and oldqa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS',
              'Original retained source admission differs')
        out.mkdir(parents=True, exist_ok=False)
        created_output = True
        save_new(out / 'INPUT_PINS.json', {'qa_sha256': args.qa_sha256, 'qa_scope_sha256': args.qa_scope_sha256,
            'context_scope_sha256': args.context_scope_sha256, 'primary_qa_receipt_sha256': args.primary_qa_receipt_sha256,
            'context_receipt_sha256': args.context_receipt_sha256, 'metadata_input_byte_pins': pins.copy()})
        global np
        import numpy as np
        import h5py
        import hdf5plugin
        check(hdf5plugin.register(filters='bshuf', force=True), 'Supported bitshuffle registration failed')
        check({p: importlib.metadata.version(p) for p in VERSIONS if p != 'HDF5'}
              == {p: v for p, v in VERSIONS.items() if p != 'HDF5'}
              and h5py.version.hdf5_version == VERSIONS['HDF5'], 'Exact context QA runtime differs')
        spec = importlib.util.spec_from_file_location('independent_control_qa_arithmetic', helper_path)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.np = np
        check(helper.workspace_allocated(root) + OUTPUT_CAP <= WORKSPACE_CAP, 'Context QA workspace reserve exceeds8GiB')
        powers, identities, decoded_records, source_streams = {}, {}, {}, []
        check([x['scan_id'] for x in acquisition['decoded_files']] == list(SCANS)
              and [x['label'] for x in source['sources']] == list(SCANS), 'Original six-source order differs')
        for identity, record in zip(source['sources'], acquisition['decoded_files']):
            scan = identity['label']
            header = identity['current_header']['data_attributes']
            check(header['tsamp'] == TSAMP and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF
                  and record['shape'] == [16, 1, COUNT] and record['source_channel0'] == C0
                  and [r['time_row'] for r in record['decoded_rows']] == list(range(16)),
                  'Actual six-source coordinate frame differs')
            path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
            check(record['array_file'] == scan + '.compact.h5', 'Canonical source path differs')
            observed = pin(path, {'bytes': record['bytes'], 'sha256': record['file_sha256']})
            check(oldqa['all_input_byte_pins'][str(path)] == observed, 'Prior actual QA source pin differs')
            stream, before = helper.source_stream(path, observed)
            handles.append(stream)
            source_streams.append((path, stream, before))
            with h5py.File(stream, 'r', rdcc_nbytes=0) as handle:
                data = handle['data']
                check(data.shape == (16, 1, COUNT) and data.dtype == np.dtype('<f4')
                      and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                      and data.attrs['original_source_url'] == identity['url']
                      and data.attrs['original_source_etag'] == identity['etag'], 'Source native identity differs')
                power = data[:, 0, :]
            check(np.isfinite(power).all() and (power >= 0).all(), 'Invalid original native source power')
            for row in record['decoded_rows']:
                check(row['decoded_bytes'] == COUNT * 4
                      and hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'],
                      'Complete source row SHA differs')
                counts['source_decoded_rows'] += 1
            powers[scan], identities[scan], decoded_records[scan] = power, identity, record
            counts['source_compacts'] += 1
        matrix_path = root / BASE / 'results/context/CONTEXT_PROFILES.json'
        matrix = text(matrix_path)
        check(matrix['schema'] == 'SETI_S2017_CONTROL_TARGET_FIXED_SIX_SCAN_CONTEXT_PROFILES_V1'
              and matrix['status'] == 'COMPLETE_NINE_PRIMARY_SELECTED_TUPLES54_FIXED_SCAN_CONTEXT_PROFILES'
              and matrix['selected_tracks'] == selected_tracks and len(selected_tracks) == 9,
              'Exact nine QA-authenticated fixed context tracks required')
        check(matrix['counts'] == context_counts and matrix['runtime_input_byte_pins'] == execution['input_byte_pins']
              and matrix['selection_is_post_primary_search'] is True, 'Fixed context matrix counts/provenance differ')
        for key in ('new_frequency_drift_width_optimization', 'ON_OFF_veto_applied',
                    'same_target_independent_repeats', 'qualified_SETI_detection', 'calibrated_SNR_FAP'):
            check(matrix[key] is False, 'Context matrix scope claim differs')
        check(matrix['source_verification'] == [
            {'scan_id': scan, 'file_sha256': decoded_records[scan]['file_sha256'],
             'decoded_rows_verified': 16, 'read_only_source_open_count': 1} for scan in SCANS],
              'Closed context source verification differs')
        counts['selected_tracks'] = 9
        expected_ids = ['%s_top%d_%s' % (track['primary_id'], track['rank'], scan)
                        for track in selected_tracks for scan in SCANS]
        check([p['profile_id'] for p in matrix['profiles']] == expected_ids, 'Exact54 fixed profile matrix/order differs')
        contextout = root / BASE / 'results/context'
        allowed = {'CONTEXT_PROFILES.json', 'EXECUTION_RECEIPT.json'}
        norm_fields = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
            'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'}
        for profile, track in zip(matrix['profiles'], [t for t in selected_tracks for scan in SCANS]):
            scan = profile['context_scan_id']
            identity, record = identities[scan], decoded_records[scan]
            header = identity['current_header']['data_attributes']
            origin_header = identities[track['scan_id']]['current_header']['data_attributes']
            check(track['reference_time_mjd'] == origin_header['tstart'] + .5 * TSAMP / 86400,
                  'Primary reference is not its actual first midpoint')
            times = (header['tstart'] - origin_header['tstart']) * 86400 + np.arange(16) * TSAMP
            centers = np.rint((track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                              + track['drift_hz_s'] * times / DF).astype(np.int64)
            check(profile['selected_track'] == track and profile['context_target'] == header['source_name']
                  and profile['original_acquisition_role'] == identity['role'].upper()
                  and profile['reference_time_mjd'] == track['reference_time_mjd']
                  and profile['width_channels'] == track['width_channels']
                  and profile['source_file_sha256'] == record['file_sha256'], 'Fixed context identity/frame differs')
            same(profile['times_from_primary_reference_s'], times, 'Actual context16-row time offsets differ')
            same(profile['row_midpoint_mjd'], np.asarray([header['tstart'] + (j + .5) * TSAMP / 86400
                                                       for j in range(16)]), 'Actual row midpoint MJDs differ')
            same(profile['rounded_absolute_centers'], centers, 'Context absolute rounded16-row track differs')
            same(profile['rounded_center_frequency_hz'], FCH1 + DF * centers, 'Context rounded physical frequencies differ')
            normrec, caprec = profile['normalization'], profile['raw_capsule']
            check(normrec['path'] == profile['profile_id'] + '_normalization.json'
                  and caprec['path'] == profile['profile_id'] + '_raw503.npz', 'Profile capsule/normalization identity differs')
            normalraw = loaded(contextout / normrec['path'], {k: normrec[k] for k in ('sha256', 'bytes')})
            normal = json.loads(normalraw, object_pairs_hook=pairs)
            check(set(normal) == norm_fields, 'Exact normalization schema differs')
            q = track['core_q']
            same(normal['normalization_source_channels'], np.arange(C0 + q * CORE, C0 + (q + 1) * CORE),
                 'Context frozen source normalization core differs')
            same(normal['normalization_unmasked_counts'], np.full(16, CORE), 'Context core support differs')
            for key in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                terms = np.asarray(normal[key])
                check(terms.shape == (16,) and np.isfinite(terms).all(), 'Context normalization16-row terms differ')
                if key in ('row_power_median', 'row_residual_MAD_scale'):
                    check((terms > 0).all(), 'Context positive row median/MAD required')
            same(np.median(powers[scan][:, q * CORE:(q + 1) * CORE].astype(np.float64), axis=1),
                 normal['row_power_median'], 'Independent context rawfloat64 core median differs')
            counts['conditional_normalization_core_row_medians'] += 16
            capsule = archive(contextout / caprec['path'], caprec)
            check(set(capsule) == {'raw_power', 'rounded_absolute_centers', 'times_from_primary_reference_s',
                  'row_standardized_box_sum'}, 'Exact context503 capsule fields differ')
            for key, dtype, shape in (('raw_power', '<f4', (16, 503)),
                ('rounded_absolute_centers', '<i8', (16,)), ('times_from_primary_reference_s', '<f8', (16,)),
                ('row_standardized_box_sum', '<f8', (16,))):
                check(capsule[key].dtype == np.dtype(dtype) and capsule[key].shape == shape
                      and np.isfinite(capsule[key]).all(), 'Context capsule precision/shape/finite differs')
            same(capsule['rounded_absolute_centers'], centers, 'Capsule rounded context geometry differs')
            same(capsule['times_from_primary_reference_s'], times, 'Capsule actual context time offsets differ')
            indexes = centers[:, None] - C0 + np.arange(-251, 252)[None, :]
            check(indexes.min() >= 0 and indexes.max() < COUNT, 'Declared raw503 context support leaves nativechunk')
            raw = powers[scan][np.arange(16)[:, None], indexes]
            same(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Context rawfloat32 source cells differ bitwise')
            sums, score = helper.independent_score(raw, normal, track['width_channels'])
            near(profile['row_standardized_box_sum'], sums, 'Independent context row standardization arithmetic differs')
            same(capsule['row_standardized_box_sum'], profile['row_standardized_box_sum'], 'Saved capsule/profile row sums differ')
            near(profile['direct_fixed_robust_box_track_score'], score, 'Independent fixed context score differs')
            max_row_difference = max(max_row_difference, float(np.max(np.abs(np.asarray(profile['row_standardized_box_sum']) - sums))))
            max_score_difference = max(max_score_difference, abs(profile['direct_fixed_robust_box_track_score'] - score))
            if scan == track['scan_id']:
                check(profile['origin_primary_score'] == track['score']
                      and profile['origin_primary_score_difference'] == profile['direct_fixed_robust_box_track_score'] - track['score'],
                      'Origin primary score binding/delta differs')
                near(profile['direct_fixed_robust_box_track_score'], track['score'], 'Fixed origin score differs from selected primary tuple')
                max_origin_difference = max(max_origin_difference, abs(profile['origin_primary_score_difference']))
                counts['origin_primary_score_matches'] += 1
            else:
                check(profile['origin_primary_score'] is None and profile['origin_primary_score_difference'] is None,
                      'Nonorigin profile must not claim origin identity')
            allowed.update((normrec['path'], caprec['path']))
            counts['fixed_profiles'] += 1
            counts['raw503_capsules'] += 1
            counts['raw_power_cells'] += raw.size
            counts['independent_fixed_scores'] += 1
        check({p.relative_to(contextout).as_posix() for p in contextout.rglob('*') if p.is_file()} == allowed,
              'Complete exact context output files without extras required')
        check(set(execution['output_pins']) == allowed - {'EXECUTION_RECEIPT.json'}
              and len(execution['output_pins']) == 109, 'Closed exact109 context output manifest differs')
        for name, declaration in execution['output_pins'].items():
            check(pins[(contextout / name).relative_to(root).as_posix()] == declaration,
                  'Loaded context output differs from its closed byte manifest')
        for name, declaration in execution['input_byte_pins'].items():
            check(pin(confined(root, name)) == declaration, 'Context runtime input changed from closed receipt')
        check(counts == expected, 'Independent fixed context QA inventory incomplete')
        for path, stream, before in source_streams:
            helper.stable_source(path, stream, before)
        for name, declared in pins.items():
            path = confined(root, name)
            check(path.stat().st_size == declared['bytes'] and digest(path) == declared['sha256'],
                  'Input/code bytes changed during context QA')
        usage = {'process_CPU_seconds_including_imports': time.process_time(), 'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(0 < usage['process_CPU_seconds_including_imports'] <= CPU_CAP
              and 0 < usage['wall_seconds'] <= WALL_CAP and 0 < usage['peak_RSS_bytes'] <= RAM_CAP,
              'Independent fixed context QA resource cap exceeded')
        receipt = {'schema': 'SETI_S2017_CONTROL_TARGET_FIXED_CONTEXT_INDEPENDENT_QA_V1',
            'status': 'PASS54_FIXED_CONTEXT_RAW503_SCORES96_SOURCE_ROWS_NO_SEARCH',
            'qa_sha256': args.qa_sha256, 'qa_scope_sha256': args.qa_scope_sha256,
            'context_scope_sha256': args.context_scope_sha256, 'context_receipt_sha256': args.context_receipt_sha256,
            'primary_qa_receipt_sha256': args.primary_qa_receipt_sha256,
            'public_freeze_commit': args.freeze_commit, 'qa_public_freeze_commit': args.qa_freeze_commit,
            'counts': counts, 'input_byte_pins': pins, 'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
            'max_row_sum_arithmetic_absolute_difference': max_row_difference,
            'max_score_arithmetic_absolute_difference': max_score_difference,
            'max_origin_primary_score_absolute_difference': max_origin_difference,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'output_cap_bytes': OUTPUT_CAP, 'workspace_cap_bytes': WORKSPACE_CAP, 'runtime_versions': VERSIONS, **usage,
            'new_HTTP_requests': 0, 'detector_import_or_search_rerun': False, 'new_sky_coverage': False,
            'qualified_SETI_detection': False,
            'limitations': ['The nine primary selected tuples are evaluated as54 fixed historical scan contexts, without optimization or detector grid rerun.',
                'Core row medians are independently recomputed; saved full-core MAD/location remain hash-bound, not independently refiltered by503local cells.',
                'Fixed context scores do not establish calibrated significance, independent visit replication or astrophysical source identity.']}
        receipt_bytes = len((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        check(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) + receipt_bytes <= OUTPUT_CAP
              and helper.workspace_allocated(root) + receipt_bytes <= WORKSPACE_CAP,
              'Completed context QA receipt would exceed frozen output/workspace bound')
        save_new(out / 'QA_RECEIPT.json', receipt)
        check(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= OUTPUT_CAP
              and helper.workspace_allocated(root) <= WORKSPACE_CAP, 'Context QA output/workspace bound exceeded')
        print(json.dumps({'status': 'PASS_INDEPENDENT_FIXED_CONTEXT_QA', 'counts': counts, **usage}), flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            save_new(out / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_CONTEXT_QA_PRESERVED_NO_RETRY',
                'error_type': type(error).__name__, 'error': str(error), 'counts': counts, 'input_byte_pins': pins,
                'qa_sha256': args.qa_sha256, 'qa_scope_sha256': args.qa_scope_sha256,
                'new_HTTP_requests': 0, 'detector_import_or_search_rerun': False})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
