"""Audit completed continuation outputs and their retained source cells.

No detector, score, optimization, or selection search is run. Top20 ordering is
reconstructed from saved maxima. Each of24 native HDF5 files is decoded once,
all384 row SHA256s checked, and222912 fixed raw-patch occurrences compared.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
PAIRS = {'pair154_155': (154, 155), 'pair157_158': (157, 158)}
NATIVE, JOINED, CORE = 1048576, 2097152, 4096
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
CPU_CAP, WALL_CAP, RAM_CAP = 120, 1800, 2 * 1024**3
SCOPE_SHA = '8127b5c5d11c157395f4f91816397a1875cdbc8e2b2812b174963ca93887ca6e'
DRIVER_SHA = 'c98ab98bf425a0f15813682ebdd58cd14f737d7c86e5e6b79790523c1372ae60'
FREEZE = '627d5254ae218f272ea81a2008ada77ca87a6dd2'
STAGE = 'results/continuation_boundaries_20261010'
RECOVERY_SCOPE_SHA = '143c2262ebe72bb99a92aac137bd1ef5eb1fc85be2804b5a098e0635f725985e'
RECOVERY_DRIVER_SHA = '38cf4220413eca40959971c76a9bfebed06d5ffa7eaa71ff1af0326e6a2fb0e7'
RECOVERY_FREEZE = '1ce3be5a57c53279702e1604165e037636e9e68b'
RECOVERY_STAGE = 'results/continuation_boundary_recovery_20261010'
FULLNORM = 'median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)'
EXPECTED_COUNTS = {'maps': 12, 'tile_normalization_files': 12, 'carrier_maximum_records': 49152,
    'top20_entries': 120, 'patches': 18, 'scan_profiles': 108, 'time_row_occurrences': 1728,
    'retained_raw_patch_cells': 222912, 'compact_files': 24, 'decoded_rows': 384,
    'raw_cells_bitwise_checked': 222912}


def check(value, message):
    if not value:
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
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def confined(root, name):
    rel = Path(name)
    check(not rel.is_absolute() and '..' not in rel.parts, 'Require project-relative path: ' + str(name))
    path = root / rel
    check(path.resolve().is_relative_to(root), 'Path escapes declared project: ' + str(name))
    return path


def same(actual, expected, label):
    check(actual.shape == expected.shape and np.array_equal(actual, expected), label)


def use(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--expected-scope-sha256', required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--recovery-scope', required=True)
    parser.add_argument('--expected-recovery-scope-sha256', required=True)
    parser.add_argument('--recovery-freeze-commit', required=True)
    parser.add_argument('--root-go-after-numerics', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    review = root / STAGE / 'review'
    # Refuse a second invocation rather than replacing earlier QA receipts.
    review.mkdir(parents=True, exist_ok=False)
    counts = {name: 0 for name in EXPECTED_COUNTS}
    pins, pair_receipts, buffers, input_compacts = {}, {}, [], {}
    own_path = Path(__file__).resolve()
    own_sha = digest(own_path)
    lock = root / STAGE / 'NUMERIC_ACTIVE_FLOCK.lock'
    lock_handle = None
    def deadline(signum, frame):
        raise RuntimeError('Continuation QA CPU/wall deadline reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(WALL_CAP)

    def read_bytes(path, declared=None):
        path = Path(path)
        raw = path.read_bytes()
        pin = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if declared is not None:
            check(pin == declared, 'Exact saved bytes differ: ' + str(path))
        key = str(path.absolute())
        check(key not in pins or pins[key] == pin, 'Previously read input changed: ' + key)
        pins[key] = pin
        return raw

    def read_json(path, declared=None):
        return json.loads(read_bytes(path, declared))

    def npz(out, record):
        path = confined(out, record['path'])
        raw = read_bytes(path, {'sha256': record['sha256'], 'bytes': record['bytes']})
        with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
            return {name: archive[name] for name in archive.files}

    try:
        # Retained lockfile existence is expected. Kernel ownership determines
        # whether the recovery numerical job is still active.
        lock_handle = lock.open('a+b')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        check(args.expected_scope_sha256 == SCOPE_SHA and args.freeze_commit == FREEZE,
              'Require actual immutable public scope and freeze commit')
        check(args.expected_recovery_scope_sha256 == RECOVERY_SCOPE_SHA
              and args.recovery_freeze_commit == RECOVERY_FREEZE, 'Require exact public recovery scope and freeze commit')
        original_scope = read_json(args.scope)
        check(pins[str(Path(args.scope).absolute())]['sha256'] == SCOPE_SHA,
              'Public continuation scope bytes differ')
        check(original_scope['driver_sha256'] == DRIVER_SHA and set(original_scope['chunk_contracts']) == {'154', '155', '157', '158'}
              and original_scope['pair_ids'] == list(PAIRS) and original_scope['native_pairs'] == [list(p) for p in PAIRS.values()]
              and original_scope['joined_reference_core_q'] == [255, 256] and original_scope['output_stage'] == STAGE,
              'Only the two publicly frozen continuation pairs are admitted')
        recovery_scope = read_json(args.recovery_scope)
        check(pins[str(Path(args.recovery_scope).absolute())]['sha256'] == RECOVERY_SCOPE_SHA
              and recovery_scope['driver_sha256'] == RECOVERY_DRIVER_SHA
              and recovery_scope['pair_ids'] == ['pair157_158'] and recovery_scope['native_pairs'] == [[157, 158]]
              and set(recovery_scope['chunk_contracts']) == {'157', '158'} and recovery_scope['output_stage'] == RECOVERY_STAGE,
              'Exact singlepair recovery scope required')
        for name, expected_sha in (('continue_boundaries.py', DRIVER_SHA), ('recovery157158.py', RECOVERY_DRIVER_SHA)):
            read_bytes(own_path.with_name(name))
            check(pins[str(own_path.with_name(name))]['sha256'] == expected_sha, 'Actual execution driver bytes differ')
        for scope in (original_scope, recovery_scope):
            for name, pin in scope['pinned_metadata_and_code'].items():
                check(Path(name).suffix.lower() not in ('.h5', '.hdf5', '.npy', '.npz'), 'Metadata pins must not open observation values')
                read_bytes(confined(root, name), pin)
            for package, version in scope['runtime_package_versions'].items():
                check(importlib.metadata.version(package) == version, 'Runtime package differs: ' + package)
        prior = recovery_scope['prior_execution_gate']
        failure = read_json(confined(root, prior['second_pair_prevalue_failure_path']))
        check(failure['status'] == 'INCOMPLETE_CONTINUATION_PRESERVE_OUTPUTS'
              and failure['pair_id'] == 'pair157_158' and failure['error_type'] == 'FileExistsError'
              and failure['completed_scan_tiles'] == 0 and failure['completed_profiles'] == 0
              and failure['scope_sha256'] == SCOPE_SHA and failure['public_freeze_commit'] == FREEZE,
              'Preserved prior recovery prevalue failure differs')
        global np
        import numpy as np
        drift_grid = np.linspace(-4.0, 4.0, 763)
        offsets = np.arange(-64, 65)
        map_schema = {'frequency_hz_at_tref': '<f8', 'maximum_robust_box_track_score': '<f8',
            'winning_drift_hz_s': '<f8', 'winning_width_channels': '<i2', 'valid_hypothesis_count': '<i8',
            'source_reference_channels': '<i8', 'drift_grid_hz_s': '<f8'}
        for pair_id, (left, right) in PAIRS.items():
            if pair_id == 'pair154_155':
                scope, scope_sha, driver_sha, freeze, stage = original_scope, SCOPE_SHA, DRIVER_SHA, FREEZE, STAGE
                status = 'COMPLETE_TWO_JOINED_BOUNDARY_CORES_CONTINUATION_EXPLORATORY_ONLY'
            else:
                scope, scope_sha, driver_sha = recovery_scope, RECOVERY_SCOPE_SHA, RECOVERY_DRIVER_SHA
                freeze, stage = args.recovery_freeze_commit, RECOVERY_STAGE
                status = 'COMPLETE_TWO_JOINED_BOUNDARY_CORES_RECOVERY157158_EXPLORATORY_ONLY'
            c0 = left * NATIVE
            out = root / stage / pair_id / 'measurement'
            expected_names = {'EXECUTION_RECEIPT.json', 'INPUT_PINS.json', 'DRIFT_CHECKPOINT.json',
                              'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json', 'NORMALIZATION.json'}
            expected_names.update(f'{scan}_tile_{tile:02d}_{suffix}' for tile in (0, 1) for scan in ONS
                                  for suffix in ('all_carriers.npz', 'normalization.json'))
            expected_names.update(f'profiles/{scan}_gap_drift_rank_{rank:02d}.npz' for scan in ONS for rank in (1, 2, 3))
            check({p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()} == expected_names,
                  'Require exactly27 complete measurement files: ' + pair_id)
            result = read_json(out / 'EXECUTION_RECEIPT.json')
            pair_receipts[pair_id] = pins[str((out / 'EXECUTION_RECEIPT.json').absolute())]
            check(result['status'] == status
                  and result['pair_id'] == pair_id and result['source_chunk_ids'] == [left, right]
                  and result['fixed_pair_q'] == [255, 256] and result['scope_sha256'] == scope_sha
                  and result['driver_sha256'] == driver_sha and result['public_freeze_commit'] == freeze
                  and result['compact_files_verified'] == 12 and result['decoded_row_SHA256s_verified'] == 192,
                  'Exact complete continuation receipt required')
            for field, cap in (('process_CPU_seconds_including_imports', 180), ('wall_seconds_including_imports', 1800),
                               ('peak_RSS_bytes', 4 * 1024**3)):
                check(0 < result[field] <= cap, 'Numeric resource bound differs: ' + field)
            for field, expected in (('CPU_cap_s', 180), ('wall_cap_s', 1800), ('memory_cap_bytes', 4 * 1024**3),
                ('new_telescope_requests', 0), ('new_telescope_body_bytes', 0), ('cost_DKK', 0),
                ('original_receipts_reclassified_or_overwritten', False), ('one_historical_visit', True),
                ('blind_or_independent_validation', False), ('calibrated_SNR_FAP', False),
                ('qualified_SETI_detection', False), ('A_B', 'FAIL_CLOSED_UNCHANGED')):
                check(result[field] == expected, 'Exploratory receipt contract differs: ' + field)
            inputs = read_json(out / 'INPUT_PINS.json')
            check(inputs['scope_sha256'] == scope_sha and inputs['driver_sha256'] == driver_sha
                  and inputs['freeze_commit'] == freeze and inputs['pair_id'] == pair_id
                  and inputs['pinned_metadata_and_code'] == scope['pinned_metadata_and_code']
                  and inputs['source_contracts'] == {str(c): scope['chunk_contracts'][str(c)] for c in (left, right)},
                  'Numerical input pins differ')
            admission = result['runtime_158_admission_receipts']
            check(inputs['runtime_158_admission_receipts'] == admission, 'Runtime158 input/execution binding differs')
            gate = scope['runtime_158_admission']
            admission_names = {job[key] for job in gate['jobs'] for key in ('execution_receipt_path', 'QA_receipt_path')}
            admission_names.add(gate['source_audit_receipt_path'])
            check(set(admission) == (admission_names if right == 158 else set()), 'Runtime158 admission inventory differs')
            for name, pin in admission.items():
                check(scope['pinned_metadata_and_code'][name] == pin, 'Admitted158 receipt differs from public pin')
                read_json(confined(root, name), pin)
            sources = []
            for chunk in (left, right):
                context = scope['chunk_contracts'][str(chunk)]
                source = read_json(confined(root, context['source_manifest_path']))
                acquisition = read_json(confined(root, context['acquisition_summary_path']))
                aq = read_json(confined(root, context['acquisition_QA_path']))
                check(source['native_chunk_index'] == chunk
                      and source['physical_channel_interval_half_open'] == [chunk * NATIVE, (chunk + 1) * NATIVE]
                      and [item['label'] for item in source['sources']] == list(SCANS), 'Source geometry/scan order differs')
                check(acquisition['status'] == 'COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY'
                      and acquisition['source_manifest_sha256'] == context['source_manifest_sha256']
                      and acquisition['decoded_files'] == context['compact_files_and_96_decoded_row_pins']
                      and aq['status'] == 'PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS'
                      and aq['acquisition_result_sha256'] == context['acquisition_summary_sha256'], 'Acquisition/QA identity differs')
                check(set(result['verified_source_inputs'][str(chunk)]) == set(SCANS), 'Six numerical compact checks required')
                for record in acquisition['decoded_files']:
                    scan = record['scan_id']
                    check(result['verified_source_inputs'][str(chunk)][scan] == {'path': record['array_file'],
                          'file_sha256': record['file_sha256'], 'bytes': record['bytes']}, 'Numerical compact identity differs')
                    key = (chunk, scan)
                    check(key not in input_compacts, 'Each native compact must belong to one admitted pair')
                    input_compacts[key] = (context, record, next(i for i in source['sources'] if i['label'] == scan), pair_id)
                sources.append(source)
            for a, b in zip(sources[0]['sources'], sources[1]['sources']):
                check(all(a[k] == b[k] for k in ('label', 'role', 'url', 'etag', 'source_file_bytes', 'current_header')),
                      'Pair physical scan/header identity differs')
            headers = {item['label']: item['current_header']['data_attributes'] for item in sources[0]['sources']}
            anchor = min(h['tstart'] for h in headers.values())
            previous_end = -math.inf
            for scan in SCANS:
                h = headers[scan]
                check(h['tsamp'] == TSAMP and h['fch1'] * 1e6 == FCH1 and h['foff'] * 1e6 == DF, 'Source physical grid differs')
                start = (h['tstart'] - anchor) * 86400
                check(start >= previous_end, 'Actual chronological scans overlap')
                previous_end = start + 16 * TSAMP
            summary = result['search_summary']
            for name, expected in (('pair_id', pair_id), ('completed_scan_tiles', 6), ('new_core_count', 2),
                ('searched_q', [255, 256]), ('carriers_per_ON', 8192), ('drift_grid_count', 763),
                ('widths_channels', [1, 3]), ('display_suppression_channels', 3),
                ('reference_core_intervals_half_open', [[c0 + q * CORE, c0 + (q + 1) * CORE] for q in (255, 256)])):
                check(summary[name] == expected, 'Search summary geometry differs: ' + name)
            checkpoint = read_json(out / 'DRIFT_CHECKPOINT.json')
            check(checkpoint['pair_id'] == pair_id and checkpoint['fixed_pair_q'] == [255, 256]
                  and checkpoint['complete'] is True and checkpoint['completed_scan_tiles'] == 6
                  and checkpoint['expected_scan_tiles'] == 6, 'Complete six-tile checkpoint required')
            entries = checkpoint['completed_receipts']
            check([(r['scan_id'], r['tile_index'], r['reference_core_q']) for r in entries]
                  == [(scan, i, q) for i, q in enumerate((255, 256)) for scan in ONS], 'Checkpoint order differs')
            saved = {scan: [] for scan in ONS}
            for scan in ONS:
                check(checkpoint['completed_q_by_ON'][scan] == [255, 256]
                      and checkpoint['completed_core_count_by_ON'][scan] == 2, 'Checkpoint ON inventory differs')
            for r in entries:
                channels = np.arange(c0 + r['reference_core_q'] * CORE, c0 + (r['reference_core_q'] + 1) * CORE)
                check(r['core_start_relative_channel'] == r['reference_core_q'] * CORE
                      and r['reference_channel_interval_half_open'] == [int(channels[0]), int(channels[-1]) + 1]
                      and r['searched_carriers'] == CORE and r['valid_hypotheses_per_carrier'] == 1526,
                      'Map receipt index/interval/count differs')
                normalization = read_json(confined(out, r['normalization_path']),
                    {'sha256': r['normalization_sha256'], 'bytes': r['normalization_bytes']})
                check(set(normalization) == {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                    'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'}, 'Tile normalization schema differs')
                same(np.asarray(normalization['normalization_source_channels']), channels, 'Normalization carrier core differs')
                same(np.asarray(normalization['normalization_unmasked_counts']), np.full(16, CORE), 'Normalization row mask counts differ')
                for field in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                    value = np.asarray(normalization[field])
                    check(value.shape == (16,) and np.isfinite(value).all(), 'Tile normalization row geometry differs')
                    if field in ('row_power_median', 'row_residual_MAD_scale'):
                        check((value > 0).all(), 'Tile normalization requires positive scale')
                m = npz(out, r)
                check(set(m) == set(map_schema), 'Map schema differs')
                for field, dtype in map_schema.items():
                    check(m[field].dtype == np.dtype(dtype), 'Map precision differs: ' + field)
                same(m['source_reference_channels'], channels, 'Saved carrier index differs')
                same(m['frequency_hz_at_tref'], FCH1 + DF * channels, 'Negative-df physical frequency mapping differs')
                same(m['drift_grid_hz_s'], drift_grid, 'Saved drift grid differs')
                same(m['valid_hypothesis_count'], np.full(CORE, 1526), 'Incomplete valid hypothesis counts')
                for field in ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_width_channels'):
                    check(m[field].shape == (CORE,) and np.isfinite(m[field]).all(), 'Saved maximum geometry differs')
                check(np.isin(m['winning_drift_hz_s'], drift_grid).all() and np.isin(m['winning_width_channels'], (1, 3)).all(), 'Winner outside frozen grid/widths')
                saved[r['scan_id']].append(m)
                counts['maps'] += 1
                counts['tile_normalization_files'] += 1
                counts['carrier_maximum_records'] += CORE
            tops = read_json(out / 'DRIFT_TOP20.json')
            check(set(tops) == set(ONS), 'Top20 ON inventory differs')
            for scan in ONS:
                channels = np.concatenate([m['source_reference_channels'] for m in saved[scan]])
                scores = np.concatenate([m['maximum_robust_box_track_score'] for m in saved[scan]])
                drifts = np.concatenate([m['winning_drift_hz_s'] for m in saved[scan]])
                widths = np.concatenate([m['winning_width_channels'] for m in saved[scan]])
                chosen = []
                for index in np.lexsort((channels, -scores)):
                    j = int(index)
                    if all(abs(int(channels[j]) - int(channels[k])) > 3 for k in chosen):
                        chosen.append(j)
                    if len(chosen) == 20:
                        break
                expected = []
                for rank, j in enumerate(chosen, 1):
                    q = 255 + j // CORE
                    expected.append({'track_id': f'{scan}_gap_drift_rank_{rank:02d}', 'family': 'internal_boundary_drift',
                        'pair_id': pair_id, 'source_chunk_id': left if q == 255 else right,
                        'source_native_core_q': 255 if q == 255 else 0, 'originating_scan': scan, 'originating_role': 'ON',
                        'display_rank': rank, 'source_reference_channel': int(channels[j]),
                        'reference_frequency_hz': FCH1 + DF * int(channels[j]),
                        'reference_seconds_from_anchor': (headers[scan]['tstart'] - anchor) * 86400 + .5 * TSAMP,
                        'drift_hz_s': float(drifts[j]), 'width_channels': int(widths[j]),
                        'maximum_robust_box_track_score': float(scores[j]), 'reference_core_tile': j // CORE,
                        'reference_core_q': q, 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'})
                check(len(expected) == 20 and tops[scan] == expected, 'Exact saved top20 ranking/ties/suppression differs')
                counts['top20_entries'] += 20
            profiles_summary = result['fixed_profile_summary']
            check(profiles_summary['profile_count'] == 9 and profiles_summary['all_rows_retained'] == 16
                  and profiles_summary['plot_count'] == 0 and not profiles_summary['shift_frequency_drift_width_optimization_applied']
                  and profiles_summary['source_top20_sha256'] == pins[str((out / 'DRIFT_TOP20.json').absolute())]['sha256'], 'Fixed profile selection summary differs')
            fullnorm = read_json(out / 'NORMALIZATION.json')
            check(profiles_summary['saved_normalization_sha256'] == pins[str((out / 'NORMALIZATION.json').absolute())]['sha256']
                  and fullnorm['method'] == FULLNORM and fullnorm['source_channel0'] == c0
                  and fullnorm['source_channel_count'] == JOINED and fullnorm['source_chunk_ids'] == [left, right], 'Full joined normalization context/hash differs')
            rowmedians = np.asarray([fullnorm['row_power_medians'][scan] for scan in SCANS])
            check(rowmedians.shape == (6, 16) and np.isfinite(rowmedians).all() and (rowmedians > 0).all(), 'Joined row medians invalid')
            records = read_json(out / 'FIXED_TOP3_PROFILES.json')
            check(len(records) == 9 and [r['selected_track'] for r in records] == [t for scan in ONS for t in tops[scan][:3]], 'Top3 profile identities differ')
            for record in records:
                track = record['selected_track']
                a = npz(out, record['patch'])
                patch_schema = {'raw_power': ('<f4', (6, 16, 129)), 'row_normalized_power': ('<f8', (6, 16, 129)),
                    'saved_full_chunk_row_medians': ('<f8', (6, 16)), 'frozen_source_channel_centers': ('<i8', (6, 16)),
                    'source_channel_offsets': ('<i8', (129,)), 'times_seconds_from_reference': ('<f8', (6, 16)),
                    'center_row_normalized_power': ('<f8', (6, 16)), 'fixed_flank_median_row_normalized_power': ('<f8', (6, 16)),
                    'center_minus_flank_each_row': ('<f8', (6, 16)), 'mean_fixed_track_frequency_profile': ('<f8', (6, 129)),
                    'scans': ('<U10', (6,)), 'df_hz': ('<f8', ()), 'source_channel0': ('<i8', ()),
                    'reference_frequency_hz': ('<f8', ()), 'drift_hz_s': ('<f8', ()), 'width_channels': ('<i8', ()),
                    'fixed_source_channel_shift': ('<i8', ())}
                check(set(a) == set(patch_schema), 'Saved raw patch complete schema differs')
                for field, (dtype, shape) in patch_schema.items():
                    check(a[field].dtype == np.dtype(dtype) and a[field].shape == shape, 'Patch precision/shape differs: ' + field)
                raw = a['raw_power']
                check(raw.shape == (6, 16, 129) and raw.dtype == np.dtype('<f4')
                      and np.isfinite(raw).all() and (raw >= 0).all(), 'Complete raw patch shape/precision differs')
                same(a['scans'], np.asarray(SCANS), 'Patch scan order differs')
                same(a['source_channel_offsets'], offsets, 'Patch offsets differ')
                same(a['saved_full_chunk_row_medians'], rowmedians, 'Patch joined-row medians differ')
                for field, expected in (('df_hz', DF), ('source_channel0', c0), ('reference_frequency_hz', track['reference_frequency_hz']),
                    ('drift_hz_s', track['drift_hz_s']), ('width_channels', track['width_channels']), ('fixed_source_channel_shift', 0)):
                    check(a[field].shape == () and a[field].item() == expected, 'Patch fixed track scalar differs: ' + field)
                dt = np.asarray([(headers[scan]['tstart'] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                    - track['reference_seconds_from_anchor'] for scan in SCANS])
                centers = np.rint((track['reference_frequency_hz'] - FCH1) / DF + track['drift_hz_s'] * dt / DF).astype(np.int64)
                same(a['times_seconds_from_reference'], dt, 'Patch actual-header time coordinates differ')
                same(a['frozen_source_channel_centers'], centers, 'Patch absolute np.rint center channels differ')
                check(centers.min() - 64 >= c0 and centers.max() + 64 < c0 + JOINED, 'Patch crosses outside retained joined pair')
                normalized = raw.astype(np.float64) / rowmedians[:, :, None]
                baseline = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
                radius = track['width_channels'] // 2
                center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
                residual = center - baseline
                mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
                for field, expected in (('row_normalized_power', normalized), ('fixed_flank_median_row_normalized_power', baseline),
                    ('center_row_normalized_power', center), ('center_minus_flank_each_row', residual), ('mean_fixed_track_frequency_profile', mean_profile)):
                    same(a[field], expected, 'Saved patch arithmetic differs: ' + field)
                check(record['fixed_frequency_shift_channels'] == 0
                      and record['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'
                      and record['fixed_flank_offsets'] == 'absolute channel offset > 3 within +/-64', 'Fixed descriptive profile contract differs')
                check(len(record['scan_profiles']) == 6, 'All six scan summaries required')
                for i, profile in enumerate(record['scan_profiles']):
                    expected = {'scan_id': SCANS[i], 'mean_center_minus_flank': float(residual[i].mean()),
                        'median_center_minus_flank': float(np.median(residual[i])), 'positive_rows': int(np.count_nonzero(residual[i] > 0)),
                        'first_eight_mean_center_minus_flank': float(residual[i, :8].mean()),
                        'last_eight_mean_center_minus_flank': float(residual[i, 8:].mean()),
                        'all_16_center_minus_flank_rows': residual[i].tolist(),
                        'all_16_raw_width_mean_power': raw[i, :, 64-radius:65+radius].mean(axis=1).tolist(),
                        'frozen_source_channel_centers': centers[i].tolist()}
                    check(profile == expected, 'Saved per-scan profile metrics differ')
                buffers.append({'pair_id': pair_id, 'raw': raw, 'indices': centers[:, :, None] + offsets,
                                'filled': np.zeros(raw.shape, dtype=bool)})
                counts['patches'] += 1
                counts['scan_profiles'] += 6
                counts['time_row_occurrences'] += 96
                counts['retained_raw_patch_cells'] += raw.size
            print('PASS_SAVED_CONTINUATION_OUTPUTS', pair_id, flush=True)
        # Decode each declared compact exactly once; no detector or score arithmetic.
        import h5py
        import hdf5plugin  # Register the existing pinned native filter.
        check(len(input_compacts) == 24, 'Exactly24 distinct native files required')
        for (chunk, scan), (context, record, item, pair_id) in input_compacts.items():
            # Compact leaves are immutable checksum-pinned links; confine their
            # directory, then admit the leaf by the exact acquisition hash.
            directory = confined(root, context['compact_directory'])
            leaf = Path(record['array_file'])
            check(leaf.name == str(leaf) and not leaf.is_absolute(), 'Compact leaf must be a single filename')
            path = directory / leaf
            before = {'sha256': digest(path), 'bytes': path.stat().st_size}
            check(before == {'sha256': record['file_sha256'], 'bytes': record['bytes']}, 'Compact file bytes differ')
            pins[str(path.absolute())] = before
            with h5py.File(path, 'r', rdcc_nbytes=8*1024**2) as handle:
                data = handle['data']
                check(data.shape == (16, 1, NATIVE) and data.dtype == np.dtype('<f4'), 'Compact HDF5 geometry differs')
                check(int(data.attrs['original_source_frequency_chunk_origin']) == chunk * NATIVE
                      and data.attrs['original_source_url'] == item['url'] and data.attrs['original_source_etag'] == item['etag'], 'Compact HDF5 original-source identity differs')
                power = data[:, 0, :]
            check(np.isfinite(power).all() and (power >= 0).all(), 'Complete native source must be finite and nonnegative')
            rows = record['decoded_rows']
            check([r['time_row'] for r in rows] == list(range(16)), 'Every native row declaration required')
            for i, row in enumerate(rows):
                check(row['decoded_bytes'] == NATIVE * 4
                      and hashlib.sha256(power[i].tobytes()).hexdigest() == row['decoded_sha256'], 'Decoded source row SHA256 differs')
                counts['decoded_rows'] += 1
            scan_index = SCANS.index(scan)
            for buffer in buffers:
                if buffer['pair_id'] != pair_id:
                    continue
                indices = buffer['indices'][scan_index]
                mask = (indices >= chunk * NATIVE) & (indices < (chunk + 1) * NATIVE)
                where = np.nonzero(mask)
                observed = power[where[0], indices[where] - chunk * NATIVE]
                retained = buffer['raw'][scan_index][where]
                check(not buffer['filled'][scan_index][where].any(), 'Source occurrence authenticated more than once')
                check(np.array_equal(observed.view(np.uint32), retained.view(np.uint32)), 'Saved raw patch is not bitwise equal to physical native source')
                buffer['filled'][scan_index][where] = True
                counts['raw_cells_bitwise_checked'] += observed.size
            del power
            counts['compact_files'] += 1
            print('AUTHENTICATED_CONTINUATION_SOURCE', chunk, scan, flush=True)
        check(all(b['filled'].all() for b in buffers), 'Every fixed raw patch occurrence must be authenticated')
        check(counts == EXPECTED_COUNTS, 'Saved/source QA inventory incomplete: ' + str(counts))
        for name, pin in pins.items():
            path = Path(name)
            check(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input changed during QA: ' + name)
        check(digest(own_path) == own_sha, 'QA code changed')
        measured = use(started)
        check(0 < measured['process_CPU_seconds_including_imports'] <= CPU_CAP
              and 0 < measured['wall_seconds'] <= WALL_CAP and 0 < measured['peak_RSS_bytes'] <= RAM_CAP, 'QA exceeds declared resource caps')
        receipt = {'schema': 'SETI_CONTINUATION_SAVED_OUTPUT_AND_SOURCE_QA_V1',
            'status': 'PASS_TWO_CONTINUATION_OUTPUT_FAMILIES_AND222912_BITWISE_SOURCE_CELLS',
            'scope_sha256': SCOPE_SHA, 'driver_sha256': DRIVER_SHA, 'public_freeze_commit': FREEZE,
            'recovery_scope_sha256': RECOVERY_SCOPE_SHA, 'recovery_driver_sha256': RECOVERY_DRIVER_SHA,
            'recovery_public_freeze_commit': args.recovery_freeze_commit,
            'measurement_stages': {'pair154_155': STAGE, 'pair157_158': RECOVERY_STAGE},
            'qa_script_sha256': own_sha, 'pair_execution_receipt_pins': pair_receipts,
            'counts': counts, 'all_input_byte_pins': pins, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
            'memory_cap_bytes': RAM_CAP, 'detector_or_score_runs': 0, 'frequency_drift_width_optimizations': 0,
            'new_telescope_requests': 0, 'original_receipts_reclassified_or_overwritten': False,
            'one_historical_visit': True, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'joined_row_medians_recomputed_from_native_sources': False,
            'joined_normalization_check': 'authenticated saved hash/context, exact patch arithmetic and saved row medians',
            **measured}
        save(review / 'QA_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'counts': counts, **measured}), flush=True)
    except BaseException as exc:
        save(review / 'QA_FAILURE_RECEIPT.json', {'status': 'FAIL_CONTINUATION_QA_PRESERVE_OUTPUTS',
            'error_type': type(exc).__name__, 'error': str(exc), 'partial_counts': counts,
            'qa_script_sha256': own_sha, 'scope_sha256': SCOPE_SHA, 'detector_or_score_runs': 0, **use(started)})
        raise
    finally:
        signal.alarm(0)
        if lock_handle is not None:
            lock_handle.close()


if __name__ == '__main__':
    main()
