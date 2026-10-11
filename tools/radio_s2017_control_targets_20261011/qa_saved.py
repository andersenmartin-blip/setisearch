"""Independent one-shot saved-map QA for three historical OFF control stars.

No detector import or search rerun. Numerical reads require exact COMPLETE
primary receipts, a separate public QA freeze and root GO. Local503 raw
capsules check queried scores conditional on hash-bound full-core MAD/location.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
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
BASE = 'analysis/s2017_control_targets_20261011'
TARGETS = {'primary20170428_HIP97319': 'epoch1_off', 'primary20170428_HIP97461': 'epoch2_off',
           'primary20170428_HIP97663': 'epoch3_off'}
CORES = tuple(q for q in range(1, 255) if q not in (64, 128, 192))
COUNT, CORE, HALO, C0 = 1048576, 4096, 4000, 171 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP, WORKSPACE_CAP = 180, 300, 2 * 1024**3, 2 * 1024**2, 8 * 1024**3
ATOL, RTOL = 1e-7, 1e-10
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0', 'HDF5': '1.14.6'}
PINS = {'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json':
    '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json':
    'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    'analysis/new_visit_recovery/results/review/QA_RECEIPT.json':
    'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f'}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def source_stream(path, declared):
    stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb')
    try:
        before = os.fstat(stream.fileno())
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
        check(before.st_size == declared['bytes'] and h.hexdigest() == declared['sha256'],
              'Retained source descriptor SHA/length differs')
        stream.seek(0)
        return stream, before
    except BaseException:
        stream.close()
        raise


def stable_source(path, stream, before):
    after, pathname = os.fstat(stream.fileno()), path.stat(follow_symlinks=False)
    check((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
          (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
          and (pathname.st_dev, pathname.st_ino) == (before.st_dev, before.st_ino),
          'Retained source descriptor/path identity changed')


def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def confined(root, name):
    p = Path(name)
    check(not p.is_absolute() and '..' not in p.parts, 'Confined relative path required')
    path = root / p
    check(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined or symlink input')
    return path


def save_new(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def workspace_allocated(root):
    seen, total = set(), 0
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                stat = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            identity = stat.st_dev, stat.st_ino
            if identity not in seen:
                seen.add(identity)
                total += stat.st_blocks * 512
    return total


def same(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    check(a.shape == b.shape and np.array_equal(a, b), message)


def near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    check(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
          and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def independent_score(raw, normal, width):
    check(raw.dtype == np.dtype('<f4') and raw.shape == (16, 503), 'Raw503 capsule schema differs')
    check(width in (1, 3), 'Different queried box width')
    normalized = raw.astype(np.float64) / np.asarray(normal['row_power_median'])[:, None]
    start = 251 - width // 2
    running = np.stack([np.median(normalized[:, i - 250:i + 251], axis=1)
                        for i in range(start, start + width)], axis=1)
    points = (normalized[:, start:start + width] - running
              - np.asarray(normal['row_winsorized_residual_location'])[:, None]) / np.asarray(
                  normal['row_residual_MAD_scale'])[:, None]
    rows = points.sum(axis=1)
    return rows, float(rows.sum() / np.sqrt(16 * width))


def rounded_centers(frequency, drift):
    times = np.arange(16) * TSAMP
    return np.rint((frequency - FCH1) / DF + drift * times / DF).astype(np.int64)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope-sha256', 'qa-scope-sha256', 'qa-sha256', 'freeze-commit', 'qa-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--primary-receipt', action='append', required=True,
                        help='Exactly three primary_id=SHA256 closed receipt pins')
    parser.add_argument('--root-go-after-three-complete-jobs', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    check(args.root_go_after_three_complete_jobs
          and all(re.fullmatch('[0-9a-f]{40}', c) for c in (args.freeze_commit, args.qa_freeze_commit)),
          'Exact public freezes and root GO after three COMPLETE jobs required')
    for sha in (args.scope_sha256, args.qa_scope_sha256, args.qa_sha256):
        check(re.fullmatch('[0-9a-f]{64}', sha), 'Exact reviewed code/scope SHA required')
    receipts_declared = {}
    for item in args.primary_receipt:
        key, sha = item.split('=', 1)
        check(key in TARGETS and key not in receipts_declared and re.fullmatch('[0-9a-f]{64}', sha),
              'Unique exact three target receipt pins required')
        receipts_declared[key] = sha
    check(set(receipts_declared) == set(TARGETS) and digest(Path(__file__).resolve()) == args.qa_sha256,
          'Three receipt pins or reviewed QA source differ')
    expected = {'maps': 753, 'carrier_maxima': 753 * CORE, 'valid_hypothesis_records': 753 * CORE * 1570,
                'core_row_medians': 753 * 16, 'score_audit_queries': 3021,
                'raw_power_cells': 3021 * 16 * 503, 'independent_scores': 3021,
                'source_decoded_rows': 48, 'source_compacts': 3,
                'top20_entries': 60, 'top3_entries': 9}
    counts = {key: 0 for key in expected}
    pins, handles, source_streams, created_output = {}, [], [], False
    out = root / BASE / 'results/review'
    max_row_sum_difference, max_score_difference = 0., 0.

    def pin(path, declared=None):
        observed = {'bytes': path.stat().st_size, 'sha256': digest(path)}
        check(declared is None or observed == declared, 'Exact file byte pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        check(name not in pins or pins[name] == observed, 'Input changed: ' + name)
        pins[name] = observed
        return observed

    def loaded(path, declared=None):
        raw = path.read_bytes()
        observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        check(declared is None or observed == declared, 'Exact loaded byte pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        check(name not in pins or pins[name] == observed, 'Loaded bytes changed: ' + name)
        pins[name] = observed
        return raw

    def text(path, sha=None):
        raw = loaded(path)
        check(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Reviewed metadata SHA differs')
        return json.loads(raw, object_pairs_hook=pairs)

    def archive(path, sha, size):
        raw = loaded(path, {'sha256': sha, 'bytes': size})
        with np.load(io.BytesIO(raw), allow_pickle=False) as value:
            check(len(value.files) == len(set(value.files)), 'Duplicate NPZ field')
            return {key: value[key] for key in value.files}

    def output_guard():
        output_bytes = sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        check(output_bytes <= OUTPUT_CAP and workspace_allocated(root) <= WORKSPACE_CAP,
              'QA output2MiB/workspace8GiB bound exceeded')

    def deadline(signum, frame):
        raise TimeoutError('Frozen independent QA CPU/wall cap reached')

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        pin(Path(__file__).resolve())
        check(workspace_allocated(root) + OUTPUT_CAP <= WORKSPACE_CAP, 'QA workspace reserve exceeds8GiB')
        for name in ('ACTIVE_FAMILY_FLOCK.lock', 'ACTIVE_SCIENCE_SLOT_0_FLOCK.lock',
                     'ACTIVE_SCIENCE_SLOT_1_FLOCK.lock', 'ACTIVE_SCIENCE_SLOT_2_FLOCK.lock'):
            handle = (root / BASE / name).open('a+b')
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle = (root / 'analysis/new_visit_recovery/results/ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        handles.append(handle)
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        qa_scope = text(root / BASE / 'qa_scope.json', args.qa_scope_sha256)
        check(qa_scope['schema'] == 'SETI_S2017_CONTROL_TARGET_SAVED_QA_SCOPE_V1'
              and qa_scope['qa_source_sha256'] == args.qa_sha256
              and qa_scope['primary_scope_sha256'] == args.scope_sha256
              and qa_scope['CPU_cap_s'] == CPU_CAP and qa_scope['wall_cap_s'] == WALL_CAP
              and qa_scope['memory_cap_bytes'] == RAM_CAP and qa_scope['output_cap_bytes'] == OUTPUT_CAP
              and qa_scope['workspace_cap_bytes'] == WORKSPACE_CAP and qa_scope['expected_counts'] == expected
              and qa_scope['numeric_tolerance'] == {'absolute': ATOL, 'relative': RTOL}
              and qa_scope['new_HTTP_requests'] == 0 and qa_scope['detector_import_or_search_rerun'] is False,
              'Separate reviewed QA scope differs')
        scope = text(root / BASE / 'scope.json', args.scope_sha256)
        check(scope['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_SCOPE_V1'
              and scope['core_q_indices'] == list(CORES) and scope['native_chunk_index'] == 171
              and scope['widths_channels'] == [1, 3] and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}
              and scope['audit_score_ATOL'] == ATOL and scope['audit_score_RTOL'] == RTOL,
              'Frozen primary scientific family differs')
        for name, declaration in scope['text_code_pins'].items():
            path = confined(root, name)
            check(path.suffix in ('.py', '.json') and pin(path) == declaration,
                  'Primary code/metadata pin differs')
        check(scope['text_code_pins'][BASE + '/driver.py']['sha256'] == qa_scope['primary_driver_sha256'],
              'Primary driver differs from independently reviewed QA interface')
        gates = {name: text(confined(root, name), sha) for name, sha in PINS.items()}
        source, acquisition, priorqa = (gates[name] for name in PINS)
        check(acquisition['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
              and priorqa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS',
              'Actual previous source admission differs')
        receipts = {}
        for target, scan in TARGETS.items():
            receipt = text(root / BASE / 'results' / target / 'EXECUTION_RECEIPT.json', receipts_declared[target])
            required_counts = {'maps': 251, 'map_normalization_records': 251,
                'carrier_maximum_records': 251 * CORE, 'valid_hypothesis_records': 251 * CORE * 1570,
                'top20_entries': 20, 'top3_metadata_entries': 3, 'score_audit_queries': 1007,
                'score_audit_raw_power_cells': 1007 * 16 * 503, 'decoded_rows_verified': 16}
            check(receipt['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_EXECUTION_V1'
                  and receipt['status'] == 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY'
                  and receipt['primary_id'] == target and receipt['scan_id'] == scan
                  and receipt['scope_sha256'] == args.scope_sha256
                  and receipt['driver_sha256'] == qa_scope['primary_driver_sha256']
                  and receipt['public_freeze_commit'] == args.freeze_commit
                  and receipt['counts'] == required_counts and receipt['runtime_versions'] == VERSIONS,
                  'Exact three closed primary receipts required')
            check(receipt['CPU_cap_s'] == scope['CPU_cap_s_per_job']
                  and receipt['wall_cap_s'] == scope['wall_cap_s_per_job']
                  and receipt['memory_cap_bytes_per_job'] == scope['memory_cap_bytes_per_job']
                  and 0 < receipt['process_CPU_seconds'] <= receipt['CPU_cap_s']
                  and 0 < receipt['wall_seconds'] <= receipt['wall_cap_s']
                  and 0 < receipt['peak_RSS_bytes'] <= receipt['memory_cap_bytes_per_job']
                  and receipt['science_slot'] in (0, 1, 2)
                  and receipt['workspace_cap_bytes'] == WORKSPACE_CAP
                  and 0 < receipt['workspace_allocated_bytes_final'] <= WORKSPACE_CAP
                  and receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0,
                  'Actual primary resource/version/network admission differs')
            check(receipt['source_bytes_unchanged'] is True and receipt['science_search_repeated'] is False
                  and receipt['other_five_source_values_opened'] is False
                  and receipt['original_acquisition_role'] == 'OFF'
                  and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED',
                  'Closed original-role/source integrity differs')
            check(receipt['decoded_row_SHA_checks_before'] == receipt['decoded_row_SHA_checks_after'] == 16,
                  'Closed primary before/after decoded-row integrity required')
            for flag in ('new_observation_visit', 'source_acquisition_role_changed', 'same_target_repeated_cadence',
                         'OFF_veto_applied', 'qualified_SETI_detection', 'calibrated_SNR_FAP', 'independent_tests_claimed'):
                check(receipt[flag] is False, 'Primary scope claim differs')
            for declaration in receipt['execution_admission_pins'].values():
                check(pin(confined(root, declaration['path'])) == {k: declaration[k] for k in ('sha256', 'bytes')},
                      'Actual primary public/root GO admission bytes differ')
            receipts[target] = receipt
        out.mkdir(parents=True, exist_ok=False)
        created_output = True
        save_new(out / 'INPUT_PINS.json', {'qa_sha256': args.qa_sha256, 'qa_scope_sha256': args.qa_scope_sha256,
            'primary_scope_sha256': args.scope_sha256, 'public_freeze_commit': args.freeze_commit,
            'qa_public_freeze_commit': args.qa_freeze_commit, 'metadata_input_byte_pins': pins.copy()})
        global np
        import numpy as np
        import h5py
        import hdf5plugin
        check(hdf5plugin.register(filters='bshuf', force=True), 'Supported bitshuffle registration failed')
        check({p: importlib.metadata.version(p) for p in VERSIONS if p != 'HDF5'}
              == {p: v for p, v in VERSIONS.items() if p != 'HDF5'}
              and h5py.version.hdf5_version == VERSIONS['HDF5'], 'Exact runtime differs')
        drift_grid = np.linspace(-4., 4., 785)
        map_schema = {'frequency_hz_at_tref': ('<f8', (CORE,)),
            'maximum_robust_box_track_score': ('<f8', (CORE,)), 'winning_drift_hz_s': ('<f8', (CORE,)),
            'winning_width_channels': ('<i2', (CORE,)), 'valid_hypothesis_count': ('<i8', (CORE,)),
            'source_reference_channels': ('<i8', (CORE,)), 'drift_grid_hz_s': ('<f8', (785,))}
        norm_fields = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                       'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'}
        global_top_records = {}
        for target, scan in TARGETS.items():
            jobout = root / BASE / 'results' / target
            identity = next(x for x in source['sources'] if x['label'] == scan)
            record = next(x for x in acquisition['decoded_files'] if x['scan_id'] == scan)
            header = identity['current_header']['data_attributes']
            check(identity['role'] == 'off' and header['source_name'] == target.split('_')[-1]
                  and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF
                  and header['tsamp'] == TSAMP and record['source_channel0'] == C0
                  and record['shape'] == [16, 1, COUNT]
                  and [r['time_row'] for r in record['decoded_rows']] == list(range(16)),
                  'Original control star/source frame differs')
            path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
            check(record['array_file'] == scan + '.compact.h5', 'Canonical original OFF compact differs')
            observed = pin(path, {'sha256': record['file_sha256'], 'bytes': record['bytes']})
            check(priorqa['all_input_byte_pins'][str(path)] == observed, 'Prior actual source QA pin differs')
            stream, before = source_stream(path, observed)
            handles.append(stream)
            source_streams.append((path, stream, before))
            with h5py.File(stream, 'r', rdcc_nbytes=0) as handle:
                data = handle['data']
                check(data.shape == (16, 1, COUNT) and data.dtype == np.dtype('<f4')
                      and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                      and data.attrs['original_source_url'] == identity['url']
                      and data.attrs['original_source_etag'] == identity['etag'], 'Native source identity differs')
                power = data[:, 0, :]
            check(np.isfinite(power).all() and (power >= 0).all(), 'Invalid original source power')
            for row in record['decoded_rows']:
                check(row['decoded_bytes'] == COUNT * 4
                      and hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'],
                      'Decoded original source row SHA differs')
                counts['source_decoded_rows'] += 1
            counts['source_compacts'] += 1
            source_decl = {'path': path.relative_to(root).as_posix(), **observed}
            check(receipts[target]['source_compact_pre_pin'] == source_decl
                  and receipts[target]['source_compact_post_pin'] == source_decl
                  and receipts[target]['decoded_row_pins'] == record['decoded_rows'],
                  'Primary closed own-source pre/post/decoded admission differs')
            maps = text(jobout / 'MAPS.json')
            audits = text(jobout / 'SCORE_AUDITS.json')
            top20, top3 = text(jobout / 'TOP20.json'), text(jobout / 'TOP3.json')
            for obj in (maps, audits, top20, top3):
                check(obj['primary_id'] == target and obj['scan_id'] == scan, 'Primary output identity differs')
            check(maps['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_MAP_INVENTORY_V1'
                  and audits['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_SCORE_AUDITS_V1'
                  and all(t['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_RANKS_V1'
                          and t['selection_rule'] == scope['top20_selection']
                          and t['original_acquisition_role'] == 'OFF'
                          and t['reference_time_mjd'] == header['tstart'] + .5 * TSAMP / 86400
                          for t in (top20, top3)), 'Primary metadata schemas/ranking frames differ')
            check([r['core_q'] for r in maps['records']] == list(CORES)
                  and [r['map_id'] for r in maps['records']] == [scan + '_q%03d' % q for q in CORES],
                  'Exact251 new core map inventory differs')
            expected_queries = ['q%03d_%s' % (q, kind) for q in CORES
                                for kind in ('first', 'midpoint', 'last', 'core_max')]
            expected_queries.extend('global_top%02d' % i for i in range(1, 4))
            check([r['query_id'] for r in audits['records']] == expected_queries, 'Exact1007 query matrix differs')
            allowed = {'MAPS.json', 'SCORE_AUDITS.json', 'TOP20.json', 'TOP3.json', 'EXECUTION_RECEIPT.json'}
            infos, score_blocks, channel_blocks = {}, [], []
            for rec in maps['records']:
                q, map_id = rec['core_q'], rec['map_id']
                check(rec['scan_id'] == scan and rec['primary_id'] == target
                      and rec['path'] == (jobout / (map_id + '.npz')).relative_to(root).as_posix()
                      and rec['original_acquisition_role'] == 'OFF'
                      and rec['reference_channel_interval_half_open'] == [C0 + q * CORE, C0 + (q + 1) * CORE]
                      and rec['searched_carriers'] == CORE and rec['valid_hypotheses_per_carrier'] == 1570,
                      'Saved map path/source identity differs')
                value = archive(confined(root, rec['path']), rec['sha256'], rec['bytes'])
                normalrec = rec['normalization']
                normal_path = normalrec['path']
                check(normal_path == (jobout / (map_id + '_normalization.json')).relative_to(root).as_posix(),
                      'Normalization identity differs')
                normal = text(confined(root, normal_path), normalrec['sha256'])
                check(pins[normal_path]['bytes'] == normalrec['bytes'],
                      'Normalization declared byte length differs')
                check(set(value) == set(map_schema) and set(normal) == norm_fields, 'Map/normalization schema differs')
                channels = np.arange(C0 + q * CORE, C0 + (q + 1) * CORE, dtype=np.int64)
                for key, (dtype, shape) in map_schema.items():
                    check(value[key].dtype == np.dtype(dtype) and value[key].shape == shape
                          and np.isfinite(value[key]).all(), 'Saved map precision/shape/finite differs')
                same(value['source_reference_channels'], channels, 'Physical carrier channels differ')
                same(value['frequency_hz_at_tref'], FCH1 + DF * channels, 'Physical carrier frequencies differ')
                same(value['drift_grid_hz_s'], drift_grid, 'Own785 drift family differs')
                same(value['valid_hypothesis_count'], np.full(CORE, 1570), 'Full1570 per-carrier support differs')
                check(np.isin(value['winning_drift_hz_s'], drift_grid).all()
                      and np.isin(value['winning_width_channels'], (1, 3)).all(), 'Saved winning hypothesis outside family')
                same(normal['normalization_source_channels'], channels, 'Normalization physical4096 core differs')
                same(normal['normalization_unmasked_counts'], np.full(16, CORE), 'Normalization input support differs')
                for key in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                    terms = np.asarray(normal[key])
                    check(terms.shape == (16,) and np.isfinite(terms).all(), 'Normalization16-row terms differ')
                    if key in ('row_power_median', 'row_residual_MAD_scale'):
                        check((terms > 0).all(), 'Positive row power median/MAD required')
                same(np.median(power[:, q * CORE:(q + 1) * CORE].astype(np.float64), axis=1),
                     normal['row_power_median'], 'Independent rawfloat64 core median differs')
                order = np.lexsort((channels, -value['maximum_robust_box_track_score']))
                infos[q] = {'arrays': value, 'normal': normal, 'record': rec, 'order': order}
                score_blocks.append(value['maximum_robust_box_track_score'])
                channel_blocks.append(channels)
                allowed.update((Path(rec['path']).name, Path(normal_path).name))
                counts['maps'] += 1
                counts['carrier_maxima'] += CORE
                counts['valid_hypothesis_records'] += int(value['valid_hypothesis_count'].sum())
                counts['core_row_medians'] += 16
            # Independent global ranking uses every saved maximum, including
            # core boundaries and ascending physical-channel ties.
            all_scores, all_channels = np.concatenate(score_blocks), np.concatenate(channel_blocks)
            global_order = np.lexsort((all_channels, -all_scores))
            selected = []
            for index in global_order:
                channel = int(all_channels[index])
                if all(abs(channel - c) > 3 for c in selected):
                    selected.append(channel)
                    if len(selected) == 20:
                        break
            check(len(selected) == 20, 'Insufficient globally suppressed top20')

            def tuple_record(q, index, rank=None):
                value = infos[q]['arrays']
                drift = float(value['winning_drift_hz_s'][index])
                result = {'primary_id': target, 'primary_target': header['source_name'], 'scan_id': scan,
                    'original_acquisition_role': 'OFF', 'core_q': q, 'map_id': scan + '_q%03d' % q,
                    'carrier_index_in_core': int(index), 'reference_source_channel': int(value['source_reference_channels'][index]),
                    'frequency_hz_at_own_first_midpoint': float(value['frequency_hz_at_tref'][index]),
                    'reference_time_mjd': header['tstart'] + .5 * TSAMP / 86400,
                    'drift_grid_index': int(np.flatnonzero(drift_grid == drift)[0]), 'drift_hz_s': drift,
                    'width_channels': int(value['winning_width_channels'][index]),
                    'score': float(value['maximum_robust_box_track_score'][index])}
                if rank is not None:
                    result['rank'] = rank
                return result

            selected_records = [tuple_record((ch - C0) // CORE, (ch - C0) % CORE, rank)
                                for rank, ch in enumerate(selected, 1)]
            check(top20['records'] == selected_records and top3['records'] == selected_records[:3],
                  'Exact global top20/top3 selection differs')
            counts['top20_entries'] += 20
            counts['top3_entries'] += 3
            global_top_records[target] = selected_records[:3]
            for query in audits['records']:
                query_id = query['query_id']
                if query_id.startswith('global_top'):
                    expected_tuple = selected_records[int(query_id[-2:]) - 1]
                    q = expected_tuple['core_q']
                    kind = 'global_top3'
                else:
                    q, kind = int(query_id[1:4]), query_id[5:]
                    index = {'first': 0, 'midpoint': 2048, 'last': 4095,
                             'core_max': int(infos[q]['order'][0])}[kind]
                    expected_tuple = tuple_record(q, index)
                check(query['core_q'] == q and query['map_id'] == expected_tuple['map_id']
                      and query['selected_tuple'] == expected_tuple and query['query_kind'] == kind,
                      'Prospective selected tuple differs')
                info, normal = infos[q], infos[q]['normal']
                check(query['normalization'] == info['record']['normalization'],
                    'Query normalization pin differs from its own full core')
                cap = query['capsule']
                check(cap['path'] == (jobout / (query_id + '_raw503.npz')).relative_to(root).as_posix(),
                      'Raw503 capsule identity differs')
                capsule = archive(confined(root, cap['path']), cap['sha256'], cap['bytes'])
                check(set(capsule) == {'raw_power', 'rounded_absolute_centers', 'standardized_row_box_sums'},
                      'Raw503 capsule fields differ')
                for key, dtype, shape in (('raw_power', '<f4', (16, 503)),
                    ('rounded_absolute_centers', '<i8', (16,)), ('standardized_row_box_sums', '<f8', (16,))):
                    check(capsule[key].dtype == np.dtype(dtype) and capsule[key].shape == shape
                          and np.isfinite(capsule[key]).all(), 'Raw503 precision/shape/finite differs')
                centers = rounded_centers(expected_tuple['frequency_hz_at_own_first_midpoint'], expected_tuple['drift_hz_s'])
                indexes = centers[:, None] - C0 + np.arange(-251, 252)[None, :]
                check(indexes.min() >= 0 and indexes.max() < COUNT, 'Raw503 lacks native support')
                raw = power[np.arange(16)[:, None], indexes]
                same(capsule['rounded_absolute_centers'], centers, 'Absolute rounded16-row track differs')
                same(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Raw503 sourcefloat32 bits differ')
                sums, score = independent_score(raw, normal, expected_tuple['width_channels'])
                near(capsule['standardized_row_box_sums'], sums, 'Independent local501 score row arithmetic differs')
                near(expected_tuple['score'], score, 'Independent winning tuple score arithmetic differs')
                max_row_sum_difference = max(max_row_sum_difference, float(np.max(np.abs(capsule['standardized_row_box_sums'] - sums))))
                max_score_difference = max(max_score_difference, abs(expected_tuple['score'] - score))
                allowed.add(Path(cap['path']).name)
                counts['score_audit_queries'] += 1
                counts['raw_power_cells'] += raw.size
                counts['independent_scores'] += 1
            check({p.relative_to(jobout).as_posix() for p in jobout.rglob('*') if p.is_file()} == allowed,
                  'Exact complete primary files without extras required')
            declared_output_pins = receipts[target]['output_byte_pins']
            check(len(declared_output_pins) == 1513 and len({p['path'] for p in declared_output_pins}) == 1513
                  and {p['path'] for p in declared_output_pins} == {
                      (jobout / name).relative_to(root).as_posix() for name in allowed if name != 'EXECUTION_RECEIPT.json'},
                  'Closed exact1513 output byte manifest differs')
            for declaration in declared_output_pins:
                check(pins[declaration['path']] == {k: declaration[k] for k in ('sha256', 'bytes')},
                      'Loaded saved output differs from its closed receipt byte manifest')
            del power, infos, all_scores, all_channels, score_blocks, channel_blocks
            print('PASS_SAVED_CONTROL_TARGET', target, flush=True)
        check(counts == expected, 'Independent saved primary QA inventory incomplete')
        for path, stream, before in source_streams:
            stable_source(path, stream, before)
        for name, declared in pins.items():
            path = confined(root, name)
            check(path.stat().st_size == declared['bytes'] and digest(path) == declared['sha256'],
                  'Input/code changed during independent QA')
        usage = {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(0 < usage['process_CPU_seconds_including_imports'] <= CPU_CAP
              and 0 < usage['wall_seconds'] <= WALL_CAP and 0 < usage['peak_RSS_bytes'] <= RAM_CAP,
              'Independent QA resource caps exceeded')
        output_guard()
        receipt = {'schema': 'SETI_S2017_CONTROL_TARGET_SAVED_INDEPENDENT_QA_V1',
            'status': 'PASS753_ORIGINAL_OFF_MAPS3021_RAW_SCORE_QUERIES_NO_DETECTOR_RERUN',
            'qa_sha256': args.qa_sha256, 'qa_scope_sha256': args.qa_scope_sha256,
            'scope_sha256': args.scope_sha256, 'primary_scope_sha256': args.scope_sha256, 'public_freeze_commit': args.freeze_commit,
            'qa_public_freeze_commit': args.qa_freeze_commit, 'primary_receipt_sha256s': receipts_declared,
            'counts': counts, 'input_byte_pins': pins, 'selected_top3': global_top_records,
            'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
            'max_row_sum_arithmetic_absolute_difference': max_row_sum_difference,
            'max_score_arithmetic_absolute_difference': max_score_difference,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'output_cap_bytes': OUTPUT_CAP, 'workspace_cap_bytes': WORKSPACE_CAP, **usage,
            'runtime_versions': VERSIONS, 'new_HTTP_requests': 0, 'detector_import_or_search_rerun': False,
            'new_sky_coverage': False, 'qualified_SETI_detection': False,
            'limitations': ['All753 saved maxima are schema/support/ranking checked, not exhaustively independently searched.',
                'Only3021 declared selected winning tuples are independently scored. Duplicate queries are logical occurrences, not independent observations.',
                'Float64 core row medians are independently recomputed. Full-core residual MAD/location remain hash-bound saved statistics;503windows do not independently refilter the full core.',
                'Direct local sums can differ from detector cumulative-prefix arithmetic; tolerance was frozen before values.',
                'Three stars each have one original OFF-role scan; this is not a six-scan ON/OFF cadence or calibrated sky sensitivity.']}
        receipt_bytes = len((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        check(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) + receipt_bytes <= OUTPUT_CAP
              and workspace_allocated(root) + receipt_bytes <= WORKSPACE_CAP,
              'Completed QA receipt would exceed frozen output/workspace bound')
        save_new(out / 'QA_RECEIPT.json', receipt)
        output_guard()
        print(json.dumps({'status': 'PASS_INDEPENDENT_SAVED_CONTROL_TARGET_QA', 'counts': counts, **usage}), flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            save_new(out / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_QA_PRESERVED_NO_RETRY',
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

