"""One-shot independent audit of six completed adjacent S2017 interior jobs.

Only after root supplies exact COMPLETE receipt/scope pins and GO. No network,
detector imports, scores, winning hypotheses, or new track optimization. Each
saved map is read once, global top20 is reconstructed from saved maxima, and
all54 saved patches are checked against one read of each of twelve native files.
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
SAFE_Q = tuple(range(1, 255))
PARTITIONS = {'batch01': SAFE_Q[:85], 'batch02': SAFE_Q[85:170], 'batch03': SAFE_Q[170:]}
NATIVES = (170, 172)
BATCHES = {f'native{native}_{batch}': qs for native in NATIVES for batch, qs in PARTITIONS.items()}
COUNT, CORE = 1048576, 4096
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
FULLNORM = 'full1048576-channel row median computed on raw float32, then profile float64 promotion'
DRIVER_SHA = '3c23e8020ee32c5c662922d16fe3517315364eccb59514b9e678e6d248b519e6'
BASE = 'analysis/s2017_next_native'
STAGE, ACQUIRE = BASE + '/results/search', BASE + '/results/acquire'
SOURCE_QA = BASE + '/results/source_review/QA_RECEIPT.json'
SOURCE_PATH = BASE + '/source_manifest_v2.json'
SOURCE_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
CPU_CAP, WALL_CAP, RAM_CAP = 180, 1800, 4 * 1024**3
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
EXPECTED_COUNTS = {'batch_families': 6, 'maps': 1524, 'map_normalization_records': 1524,
    'carrier_maximum_records': 6242304, 'valid_hypothesis_records': 9800417280,
    'top20_entries': 360, 'patches': 54, 'scan_profiles': 324, 'time_row_occurrences': 5184,
    'retained_raw_patch_cells': 668736, 'compact_files': 12, 'decoded_rows': 192,
    'native_full_row_medians_recomputed': 192, 'ON_core_row_medians_recomputed': 24384,
    'raw_cells_bitwise_checked': 668736}
SOURCE_QA_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12,
    'source_descriptors': 192, 'exact_range_records': 192, 'unique_source_ranges': 192,
    'durable_raw_sidecars': 192, 'compressed_source_chunks': 192, 'decoded_rows': 192}



def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, name):
    relative = Path(name)
    check(not relative.is_absolute() and '..' not in relative.parts, 'Relative confined path required')
    path = root / relative
    check(path.resolve().is_relative_to(root), 'Path outside frozen workspace')
    return path


def save_new(path, value):
    check(not path.exists(), 'Refuse receipt overwrite')
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
        'wall_seconds_including_imports': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def same(actual, expected, message):
    check(actual.shape == expected.shape and np.array_equal(actual, expected), message)


def unique_json_pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field forbidden')
        result[key] = value
    return result


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'freeze-commit', 'qa-freeze-commit', 'expected-qa-sha256', 'expected-static-review-sha256'):
        parser.add_argument('--' + name, required=True)
    for batch in BATCHES:
        for kind in ('scope', 'receipt'):
            parser.add_argument('--expected-' + batch + '-' + kind + '-sha256', required=True)
    parser.add_argument('--root-go-after-complete-searches', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    check(args.root_go_after_complete_searches and all(re.fullmatch('[0-9a-f]{40}', commit)
        for commit in (args.freeze_commit, args.qa_freeze_commit)),
        'Root-reviewed actual completed six searches and public freeze required')
    check(re.fullmatch('[0-9a-f]{64}', args.expected_qa_sha256) and digest(__file__) == args.expected_qa_sha256,
        'Exact statically reviewed QA source SHA required')
    stage = root / STAGE
    review = stage / 'review'
    handles, counts, pins = [], {name: 0 for name in EXPECTED_COUNTS}, {}

    def pin_bytes(path, raw, expected=None):
        relative = path.relative_to(root).as_posix()
        observed = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        check(expected is None or observed == expected, 'Loaded byte pin differs: ' + relative)
        check(relative not in pins or pins[relative] == observed, 'Loaded input changed during audit: ' + relative)
        pins[relative] = observed
        return observed

    def pin(path, expected=None):
        relative = path.relative_to(root).as_posix()
        observed = {'sha256': digest(path), 'bytes': path.stat().st_size}
        check(expected is None or observed == expected, 'Input byte pin differs: ' + relative)
        check(relative not in pins or pins[relative] == observed, 'Input changed during audit: ' + relative)
        pins[relative] = observed
        return observed

    def read_json(path, expected_sha=None):
        check(path.suffix.lower() == '.json', 'Metadata JSON required')
        raw = path.read_bytes()
        observed = pin_bytes(path, raw)
        check(expected_sha is None or observed['sha256'] == expected_sha, 'Root-reviewed JSON SHA differs')
        return json.loads(raw, object_pairs_hook=unique_json_pairs)

    def npz(out, record):
        path = confined(out, record['path'])
        raw = path.read_bytes()
        pin_bytes(path, raw, {'sha256': record['sha256'], 'bytes': record['bytes']})
        with np.load(io.BytesIO(raw), allow_pickle=False) as handle:
            check(len(handle.files) == len(set(handle.files)), 'Duplicate NPZ archive fields forbidden')
            return {name: handle[name] for name in handle.files}

    def deadline(signum, frame):
        raise TimeoutError('Frozen QA CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(WALL_CAP)
    try:
        check(Path(__file__).resolve() == root / BASE / 'search/qa_saved_outputs.py', 'Exact QA script path required')
        pin(Path(__file__).resolve(), {'sha256': args.expected_qa_sha256, 'bytes': Path(__file__).stat().st_size})
        static_review = read_json(root / BASE / 'search/QA_SOURCE_REVIEW.json', args.expected_static_review_sha256)
        check(static_review['status'] == 'PASS_INDEPENDENT_STATIC_INTERIOR_QA_NO_VALUES'
            and static_review['qa_script_sha256'] == args.expected_qa_sha256,
            'Independent static review of exact QA bytes required')
        # Both science slots exclude overlapping extension jobs during this audit.
        for name, mode in ((stage / 'REVIEW_ACTIVE_FLOCK.lock', fcntl.LOCK_EX),
                (root / BASE / 'ACTIVE_FAMILY_FLOCK.lock', fcntl.LOCK_EX),
                (root / BASE / 'ACTIVE_SCIENCE_SLOT_0_FLOCK.lock', fcntl.LOCK_EX),
                (root / BASE / 'ACTIVE_SCIENCE_SLOT_1_FLOCK.lock', fcntl.LOCK_EX)):
            handle = name.open('a+b')
            handles.append(handle)
            fcntl.flock(handle.fileno(), mode | fcntl.LOCK_NB)
        scopes, receipts = {}, {}
        for batch, qs in BATCHES.items():
            native = int(batch.split('_')[0][6:]); C0 = native * COUNT
            scope_sha = getattr(args, 'expected_' + batch + '_scope_sha256')
            receipt_sha = getattr(args, 'expected_' + batch + '_receipt_sha256')
            check(re.fullmatch('[0-9a-f]{64}', scope_sha) and re.fullmatch('[0-9a-f]{64}', receipt_sha),
                'Exact reviewed batch scope and COMPLETE receipt SHAs required')
            scope = read_json(root / BASE / 'search/scopes' / (batch + '.json'), scope_sha)
            receipt = read_json(stage / batch / 'EXECUTION_RECEIPT.json', receipt_sha)
            check(scope['schema'] == 'SETI_S2017_ADJACENT_SAFE_INTERIOR_SEARCH_V1' and scope['job_id'] == batch
                and scope['batch_id'] == batch.split('_', 1)[1] and scope['native_chunk_index'] == native
                and scope['core_q_indices'] == list(qs) and scope['driver_sha256'] == DRIVER_SHA
                and scope['scan_order'] == list(SCANS) and scope['source_channel_interval_half_open'] == [C0, C0 + COUNT]
                and scope['fch1_hz'] == FCH1 and scope['df_hz'] == DF and scope['tsamp_s'] == TSAMP
                and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}
                and scope['widths_channels'] == [1, 3] and scope['output_stage'] == STAGE + '/' + batch,
                'Wrong frozen batch/source/physical family')
            for name, expected in scope['pinned_metadata_code_and_prerequisites'].items():
                path = confined(root, name)
                check(path.suffix.lower() not in ('.h5', '.hdf5', '.npz', '.npy'), 'Scope admission pins must be metadata/code')
                pin(path, expected)
            check(receipt['status'] == 'COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY'
                and receipt['job_id'] == batch and receipt['batch_id'] == batch.split('_', 1)[1]
                and receipt['native_chunk_index'] == native and receipt['scope_sha256'] == scope_sha
                and receipt['driver_sha256'] == DRIVER_SHA and receipt['public_freeze_commit'] == args.freeze_commit
                and receipt['core_q_indices'] == list(qs) and receipt['new_telescope_HTTP_requests'] == 0
                and receipt['new_telescope_BODY_bytes'] == 0 and receipt['prior_native171_search_rerun'] is False,
                'Actual complete unrerun batch required')
            check(read_json(stage / batch / 'INPUT_PINS.json') == {'scope_sha256': scope_sha,
                'public_freeze_commit': args.freeze_commit, 'pins': scope['pinned_metadata_code_and_prerequisites']},
                'Saved job input pins differ from frozen scope')
            check(0 < receipt['process_CPU_seconds_including_imports'] <= 1000
                and 0 < receipt['wall_seconds_including_imports'] <= 1800
                and 0 < receipt['peak_RSS_bytes'] <= 2 * 1024**3, 'Completed batch resource caps differ')
            for key in ('independent_tests_claimed', 'qualified_sky_detection', 'OFF_veto_applied', 'calibrated_SNR_FAP'):
                check(receipt[key] is False, 'Exploratory-only receipt required')
            scopes[batch], receipts[batch] = scope, receipt
        first_scope = scopes[next(iter(BATCHES))]
        check(all(scope['prerequisites'] == first_scope['prerequisites']
                  and scope['source_manifest_path'] == SOURCE_PATH for scope in scopes.values()),
              'All jobs must use identical actual acquisition/source-QA prerequisites')
        gates = first_scope['prerequisites']
        expected_gates = {'acquisition': ACQUIRE + '/ACQUISITION_RESULT.json', 'source_QA': SOURCE_QA}
        gate_values = {}
        for key, name in expected_gates.items():
            check(gates[key]['path'] == name, 'Wrong fixed prerequisite path')
            gate_values[key] = read_json(root / name, gates[key]['sha256'])
        acquisition, priorqa = (gate_values[key] for key in expected_gates)
        check(acquisition['schema'] == 'SETI_S2017_ADJACENT170_172_ACQUISITION_RECEIPT_V1'
            and acquisition['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
            and acquisition['source_range_count_authenticated'] == acquisition['decoded_row_SHA256s'] == 192
            and acquisition['complete_compact_files'] == 12 and acquisition['new_telescope_HTTP_requests'] == 192
            and acquisition['new_telescope_BODY_bytes'] == 597792529 and acquisition['repeated_source_GETs'] == 0,
            'Complete source acquisition required')
        check(priorqa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
            and priorqa['status'] == 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
            and priorqa['counts'] == SOURCE_QA_COUNTS
            and priorqa['acquisition_receipt_sha256'] == gates['acquisition']['sha256']
            and priorqa['source_manifest_sha256'] == SOURCE_SHA
            and priorqa['scope_sha256'] == acquisition['scope_sha256']
            and priorqa['driver_sha256'] == acquisition['driver_sha256']
            and priorqa['public_freeze_commit'] == acquisition['public_freeze_commit']
            and priorqa['detector_or_score_rerun'] is False
            and priorqa['new_telescope_HTTP_requests'] == priorqa['new_telescope_BODY_bytes'] == 0,
            'Actual independently source-qualified192-row QA PASS required')
        canonical = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
            ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()
        check(priorqa['source_range_raw_record_sha256'] == canonical(acquisition['raw_range_records'])
            and priorqa['decoded_file_row_record_sha256'] == canonical(acquisition['decoded_files'])
            and priorqa['source_range_request_record_sha256'] == canonical(acquisition['value_read_requests']),
            'Source-qualified raw/decoded/request record digests differ')
        source = read_json(root / SOURCE_PATH, SOURCE_SHA)
        source_sha = SOURCE_SHA
        check(source['native_chunk_indices'] == list(NATIVES) and set(source['by_native_chunk']) == {'170', '172'}
            and acquisition['source_manifest_sha256'] == source_sha, 'Source manifest identity differs')
        for batch, receipt in receipts.items():
            check(receipt['source_manifest_sha256'] == source_sha
                and receipt['acquisition_receipt_sha256'] == gates['acquisition']['sha256']
                and receipt['source_QA_receipt_sha256'] == gates['source_QA']['sha256'], 'Job prerequisite receipt binding differs')
        expected_compact_pins = {ACQUIRE + '/' + record['array_file']:
            {'sha256': record['file_sha256'], 'bytes': record['bytes']} for record in acquisition['decoded_files']}
        check(priorqa['compact_input_byte_pins'] == expected_compact_pins and len(expected_compact_pins) == 12,
            'Independent source QA twelve compact pins differ')
        pin(root / BASE / 'qa_sources.py', {'sha256': priorqa['qa_script_sha256'],
            'bytes': (root / BASE / 'qa_sources.py').stat().st_size})
        original = read_json(root / 'analysis/new_visit_search/results/acquire/FAILURE_RECEIPT.json')
        check(original['status'] == 'INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY', 'Original failure must remain preserved')
        review.mkdir(exist_ok=False)
        save_new(review / 'INPUT_PINS.json', {'qa_script_sha256': args.expected_qa_sha256,
            'public_freeze_commit': args.freeze_commit, 'metadata_and_code_pins': pins.copy()})
        global np
        import numpy as np
        offsets, drift_grid = np.arange(-64, 65), np.linspace(-4.0, 4.0, 785)
        normalizations, native_rowmedians = {}, {}
        headers = {item['label']: item['current_header']['data_attributes'] for item in source['by_native_chunk']['170']['sources']}
        check(all(item['current_header']['data_attributes'] == headers[item['label']]
            for item in source['by_native_chunk']['172']['sources']), 'Native source time/grid headers differ')
        anchor = min(header['tstart'] for header in headers.values())
        mismatch = float((drift_grid[1] - drift_grid[0]) * (np.arange(16) * TSAMP)[-1] / (2 * abs(DF)))
        check(mismatch <= .5 + 1e-12 and 2 * math.ceil(4 * 15 * TSAMP / abs(DF)) + 1 == 785,
            'Own frozen drift grid differs')
        core_medians, buffers = {}, []
        map_schema = {'frequency_hz_at_tref': ('<f8', (CORE,)), 'maximum_robust_box_track_score': ('<f8', (CORE,)),
            'winning_drift_hz_s': ('<f8', (CORE,)), 'winning_width_channels': ('<i2', (CORE,)),
            'valid_hypothesis_count': ('<i8', (CORE,)), 'source_reference_channels': ('<i8', (CORE,)),
            'drift_grid_hz_s': ('<f8', (785,))}
        patch_schema = {'raw_power': ('<f4', (6, 16, 129)), 'row_normalized_power': ('<f8', (6, 16, 129)),
            'saved_full_chunk_row_medians': ('<f8', (6, 16)), 'frozen_source_channel_centers': ('<i8', (6, 16)),
            'source_channel_offsets': ('<i8', (129,)), 'times_seconds_from_reference': ('<f8', (6, 16)),
            'center_row_normalized_power': ('<f8', (6, 16)), 'fixed_flank_median_row_normalized_power': ('<f8', (6, 16)),
            'center_minus_flank_each_row': ('<f8', (6, 16)), 'mean_fixed_track_frequency_profile': ('<f8', (6, 129)),
            'scans': ('<U10', (6,)), 'df_hz': ('<f8', ()), 'source_channel0': ('<i8', ()),
            'reference_frequency_hz': ('<f8', ()), 'drift_hz_s': ('<f8', ()), 'width_channels': ('<i8', ()),
            'fixed_source_channel_shift': ('<i8', ())}
        for batch, qs in BATCHES.items():
            native = int(batch.split('_')[0][6:]); C0 = native * COUNT
            out, receipt = stage / batch, receipts[batch]
            qualified_norm = read_json(out / 'NORMALIZATION.json')
            check(set(qualified_norm) == {'source_channel0', 'count', 'row_power_medians', 'method', 'raw_dtype'}
                and qualified_norm['source_channel0'] == C0 and qualified_norm['count'] == COUNT
                and qualified_norm['method'] == FULLNORM and qualified_norm['raw_dtype'] == '<f4'
                and set(qualified_norm['row_power_medians']) == set(SCANS), 'Saved native normalization frame differs')
            rowmedians = np.asarray([qualified_norm['row_power_medians'][scan] for scan in SCANS])
            check(rowmedians.shape == (6, 16) and np.isfinite(rowmedians).all() and (rowmedians > 0).all(),
                'Invalid saved native row medians')
            check(native not in normalizations or normalizations[native] == qualified_norm,
                'Three jobs of a native have different full-row medians')
            normalizations[native], native_rowmedians[native] = qualified_norm, rowmedians
            checkpoint = read_json(out / 'DRIFT_CHECKPOINT.json')
            order = [(scan, q) for scan in ONS for q in qs]
            check(set(checkpoint) == {'completed_ON_maps', 'expected_ON_maps', 'complete', 'receipts'}
                and checkpoint['complete'] is True and checkpoint['completed_ON_maps'] == checkpoint['expected_ON_maps'] == len(order)
                and [(record['scan_id'], record['core_q']) for record in checkpoint['receipts']] == order, 'Batch map completion/order differs')
            summary = receipt['search_summary']
            check(summary['completed_ON_maps'] == 3 * len(qs) and summary['cores_per_ON'] == len(qs)
                and summary['carriers_per_ON'] == len(qs) * CORE
                and summary['ON_carrier_maximum_records'] == len(order) * CORE
                and summary['correlated_drift_width_combinations'] == len(order) * CORE * 1570
                and summary['drift_grid_count'] == 785 and summary['widths_channels'] == [1, 3]
                and summary['half_grid_mismatch_channels'] == mismatch
                and summary['bandwidth_per_ON_hz'] == len(qs) * CORE * abs(DF)
                and summary['native_chunk_fraction_searched'] == len(qs) * CORE / COUNT
                and receipt['MJD_anchor'] == anchor, 'Actual batch search summary geometry differs')
            expected_files = {'EXECUTION_RECEIPT.json', 'INPUT_PINS.json', 'NORMALIZATION.json',
                'DRIFT_CHECKPOINT.json', 'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json'}
            expected_files.update(scan + '_q%03d_all_carriers.npz' % q for scan, q in order)
            expected_files.update(scan + '_q%03d_normalization.json' % q for scan, q in order)
            expected_files.update('profiles/' + scan + '_visit20170428_Sband_' + batch + '_rank_%02d.npz' % rank
                for scan in ONS for rank in range(1, 4))
            check({path.relative_to(out).as_posix() for path in out.rglob('*') if path.is_file()} == expected_files,
                'Require exact complete batch files without failed/temporary extras')
            tops = read_json(out / 'DRIFT_TOP20.json')
            check(set(tops) == set(ONS), 'Three ON top20 families required')
            for scan in ONS:
                columns = {'channels': [], 'scores': [], 'drifts': [], 'widths': [], 'qs': []}
                for record in [record for record in checkpoint['receipts'] if record['scan_id'] == scan]:
                    q, first = record['core_q'], C0 + record['core_q'] * CORE
                    channels = np.arange(first, first + CORE)
                    check(record['path'] == scan + '_q%03d_all_carriers.npz' % q and record['searched_carriers'] == CORE
                        and record['valid_hypotheses_per_carrier'] == 1570
                        and record['reference_channel_interval_half_open'] == [first, first + CORE], 'Map physical record differs')
                    normal = record['normalization']
                    check(normal['path'] == scan + '_q%03d_normalization.json' % q, 'Map normalization identity differs')
                    pin(confined(out, normal['path']), {'sha256': normal['sha256'], 'bytes': normal['bytes']})
                    norm = read_json(confined(out, normal['path']))
                    check(set(norm) == {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                        'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'}, 'Core normalization schema differs')
                    same(np.asarray(norm['normalization_source_channels']), channels, 'Core physical normalization indices differ')
                    same(np.asarray(norm['normalization_unmasked_counts']), np.full(16, CORE), 'Core unmasked normalization counts differ')
                    for field in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                        values = np.asarray(norm[field])
                        check(values.shape == (16,) and np.isfinite(values).all(), 'Core row normalization geometry differs')
                        if field in ('row_power_median', 'row_residual_MAD_scale'):
                            check((values > 0).all(), 'Core row normalization scale must be positive')
                    core_medians[(native, scan, q)] = np.asarray(norm['row_power_median'])
                    m = npz(out, record)
                    check(set(m) == set(map_schema), 'Map schema differs')
                    for field, (dtype, shape) in map_schema.items():
                        check(m[field].dtype == np.dtype(dtype) and m[field].shape == shape and np.isfinite(m[field]).all(), 'Map precision/shape/finite differs: ' + field)
                    same(m['source_reference_channels'], channels, 'Map physical channels differ')
                    same(m['frequency_hz_at_tref'], FCH1 + DF * channels, 'Map physical frequency mapping differs')
                    same(m['drift_grid_hz_s'], drift_grid, 'Map full785 drift grid differs')
                    same(m['valid_hypothesis_count'], np.full(CORE, 1570), 'Map full1570 hypothesis coverage differs')
                    check(np.isin(m['winning_drift_hz_s'], drift_grid).all() and np.isin(m['winning_width_channels'], (1, 3)).all(), 'Map winner outside frozen family')
                    for key, value in (('channels', channels), ('scores', m['maximum_robust_box_track_score']),
                            ('drifts', m['winning_drift_hz_s']), ('widths', m['winning_width_channels']), ('qs', np.full(CORE, q, dtype=np.int16))):
                        columns[key].append(value)
                    counts['maps'] += 1
                    counts['map_normalization_records'] += 1
                    counts['carrier_maximum_records'] += CORE
                    counts['valid_hypothesis_records'] += int(m['valid_hypothesis_count'].sum())
                columns = {key: np.concatenate(value) for key, value in columns.items()}
                chosen = []
                for j in np.lexsort((columns['channels'], -columns['scores'])):
                    j = int(j)
                    if all(abs(int(columns['channels'][j]) - int(columns['channels'][k])) > 3 for k in chosen):
                        chosen.append(j)
                    if len(chosen) == 20:
                        break
                expected = [{'track_id': scan + '_visit20170428_Sband_' + batch + '_rank_%02d' % rank,
                    'family': 'S2017_adjacent_safe_interior_' + batch, 'originating_scan': scan,
                    'originating_role': 'ON', 'display_rank': rank, 'source_reference_channel': int(columns['channels'][j]),
                    'reference_frequency_hz': float(FCH1 + DF * columns['channels'][j]),
                    'reference_seconds_from_anchor': float((headers[scan]['tstart'] - anchor) * 86400 + .5 * TSAMP),
                    'drift_hz_s': float(columns['drifts'][j]), 'width_channels': int(columns['widths'][j]),
                    'maximum_robust_box_track_score': float(columns['scores'][j]), 'reference_core_tile': int(columns['qs'][j]),
                    'status': 'EXPLORATORY_RANK_UNCLASSIFIED'} for rank, j in enumerate(chosen, 1)]
                check(len(expected) == 20 and tops[scan] == expected, 'Global per-batch top20/tie/suppression differs')
                counts['top20_entries'] += 20
                del columns
            records = read_json(out / 'FIXED_TOP3_PROFILES.json')
            check(len(records) == 9 and [record['selected_track'] for record in records]
                == [track for scan in ONS for track in tops[scan][:3]], 'Exact nine top3 fixed profile selections differ')
            expected_profile_summary = {'profile_count': 9, 'plot_count': 0, 'all_rows_retained': 16,
                'source_top20_sha256': pins[(out / 'DRIFT_TOP20.json').relative_to(root).as_posix()]['sha256'],
                'saved_normalization_sha256': pins[(out / 'NORMALIZATION.json').relative_to(root).as_posix()]['sha256'],
                'shift_frequency_drift_width_optimization_applied': False,
                'raw_patch_alignment': 'rounded absolute source channels along exact fixed selected track in each actual scan',
                'time_profile_units': 'width-mean raw power/full-chunk row median minus fixed flank median',
                'mean_profile_units': 'mean track-aligned row-normalized power minus each row fixed flank median'}
            check(receipt['fixed_profile_summary'] == expected_profile_summary and receipt['top20_entries'] == 60, 'Fixed profile summary binding differs')
            for record in records:
                track = record['selected_track']
                check(record['patch']['path'] == 'profiles/' + track['track_id'] + '.npz', 'Fixed patch identity differs')
                a = npz(out, record['patch'])
                check(set(a) == set(patch_schema), 'Exact17 field patch schema differs')
                for field, (dtype, shape) in patch_schema.items():
                    check(a[field].dtype == np.dtype(dtype) and a[field].shape == shape, 'Patch precision/shape differs: ' + field)
                raw = a['raw_power']
                check(np.isfinite(raw).all() and (raw >= 0).all(), 'Raw patch must be finite nonnegative float32')
                same(a['scans'], np.asarray(SCANS), 'Patch scan order differs')
                same(a['source_channel_offsets'], offsets, 'Patch offsets differ')
                same(a['saved_full_chunk_row_medians'], rowmedians, 'Patch native row medians differ')
                for field, expected in (('df_hz', DF), ('source_channel0', C0), ('reference_frequency_hz', track['reference_frequency_hz']),
                        ('drift_hz_s', track['drift_hz_s']), ('width_channels', track['width_channels']), ('fixed_source_channel_shift', 0)):
                    check(a[field].item() == expected, 'Patch frozen track scalar differs: ' + field)
                dt = np.asarray([(headers[scan]['tstart'] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                    - track['reference_seconds_from_anchor'] for scan in SCANS])
                centers = np.rint((track['reference_frequency_hz'] - FCH1) / DF + track['drift_hz_s'] * dt / DF).astype(np.int64)
                same(a['times_seconds_from_reference'], dt, 'Patch actual-header time frame differs')
                same(a['frozen_source_channel_centers'], centers, 'Patch absolute physical rounded centers differ')
                indices = centers[:, :, None] - C0 + offsets
                check(indices.min() >= 0 and indices.max() < COUNT, 'Patch source support outside native chunk')
                normalized = raw.astype(np.float64) / rowmedians[:, :, None]
                baseline = np.median(normalized[:, :, np.abs(offsets) > 3], axis=2)
                radius = track['width_channels'] // 2
                center = normalized[:, :, 64-radius:65+radius].mean(axis=2)
                residual = center - baseline
                mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
                for field, expected in (('row_normalized_power', normalized), ('fixed_flank_median_row_normalized_power', baseline),
                        ('center_row_normalized_power', center), ('center_minus_flank_each_row', residual), ('mean_fixed_track_frequency_profile', mean_profile)):
                    same(a[field], expected, 'Saved patch arithmetic differs: ' + field)
                check(record['fixed_frequency_shift_channels'] == 0 and record['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'
                    and record['fixed_flank_offsets'] == 'absolute channel offset > 3 within +/-64' and len(record['scan_profiles']) == 6,
                    'Fixed descriptive profile contract differs')
                for i, profile in enumerate(record['scan_profiles']):
                    expected = {'scan_id': SCANS[i], 'mean_center_minus_flank': float(residual[i].mean()),
                        'median_center_minus_flank': float(np.median(residual[i])), 'positive_rows': int(np.count_nonzero(residual[i] > 0)),
                        'first_eight_mean_center_minus_flank': float(residual[i, :8].mean()),
                        'last_eight_mean_center_minus_flank': float(residual[i, 8:].mean()),
                        'all_16_center_minus_flank_rows': residual[i].tolist(),
                        'all_16_raw_width_mean_power': raw[i, :, 64-radius:65+radius].mean(axis=1).tolist(),
                        'frozen_source_channel_centers': centers[i].tolist()}
                    check(profile == expected, 'Saved all-row per-scan profile arithmetic differs')
                buffers.append({'native': native, 'raw': raw, 'indices': indices, 'checked_scans': []})
                counts['patches'] += 1
                counts['scan_profiles'] += 6
                counts['time_row_occurrences'] += 96
                counts['retained_raw_patch_cells'] += raw.size
            counts['batch_families'] += 1
            print('PASS_SAVED_S2017_INTERIOR_BATCH_GEOMETRY_RANKS_PROFILE_ARITHMETIC', batch, flush=True)
        import h5py
        import hdf5plugin
        hdf5plugin.register(filters='bshuf', force=True)
        versions = {package: importlib.metadata.version(package) for package in VERSIONS}
        check(versions == VERSIONS and h5py.version.hdf5_version == '1.14.6'
            and h5py.h5z.filter_avail(32008)
            and h5py.h5z.get_filter_info(32008) & h5py.h5z.FILTER_CONFIG_DECODE_ENABLED, 'Frozen runtime/decoder differs')
        versions['HDF5'] = h5py.version.hdf5_version
        check(all(receipt['runtime_versions'] == versions for receipt in receipts.values()), 'Batch runtime receipt differs')
        records = acquisition['decoded_files']
        check([(record['native_chunk_index'], record['scan_id']) for record in records]
            == [(native, scan) for native in NATIVES for scan in SCANS], 'Twelve acquired compact identities required')
        for native in NATIVES:
            selected = [record for record in records if record['native_chunk_index'] == native]
            expected_inputs = [{'scan_id': record['scan_id'], 'file_sha256': record['file_sha256'],
                'decoded_rows_verified': 16} for record in selected]
            check(all(receipt['verified_inputs'] == expected_inputs for receipt in receipts.values()
                if receipt['native_chunk_index'] == native), 'Job native input provenance differs')
        for record in records:
            native, scan = record['native_chunk_index'], record['scan_id']; C0 = native * COUNT
            i = SCANS.index(scan)
            check(record['array_file'] == f'native{native}_{scan}.compact.h5' and record['shape'] == [16, 1, COUNT]
                and record['source_channel0'] == C0 and [row['time_row'] for row in record['decoded_rows']] == list(range(16)),
                'Compact row/source frame differs')
            path = root / ACQUIRE / record['array_file']
            pin(path, expected_compact_pins[path.relative_to(root).as_posix()])
            item = source['by_native_chunk'][str(native)]['sources'][i]
            with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                check(set(handle.keys()) == {'data'}, 'Compact dataset inventory differs')
                data = handle['data']
                check(data.shape == (16, 1, COUNT) and data.dtype == np.dtype('<f4') and data.chunks == (1, 1, COUNT)
                    and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                    and data.attrs['original_source_url'] == item['url'] and data.attrs['original_source_etag'] == item['etag'],
                    'Compact physical source identity differs')
                power = data[:, 0, :]
            check(power.dtype == np.dtype('<f4') and power.shape == (16, COUNT)
                and np.isfinite(power).all() and (power >= 0).all(), 'Invalid native decoded power')
            for row in record['decoded_rows']:
                check(row['decoded_bytes'] == COUNT * 4
                    and hashlib.sha256(power[row['time_row']].tobytes(order='C')).hexdigest() == row['decoded_sha256'],
                    'Native decoded row SHA differs')
                counts['decoded_rows'] += 1
            same(np.median(power, axis=1).astype(np.float64), native_rowmedians[native][i],
                'Saved full-native median differs from independent native float32 median')
            counts['native_full_row_medians_recomputed'] += 16
            if scan in ONS:
                for q in SAFE_Q:
                    same(np.median(power[:, q*CORE:(q+1)*CORE].astype(np.float64), axis=1),
                        core_medians[(native, scan, q)], 'Unchanged detector core float64 row median differs')
                    counts['ON_core_row_medians_recomputed'] += 16
            for buffer in [buffer for buffer in buffers if buffer['native'] == native]:
                observed = power[np.arange(16)[:, None], buffer['indices'][i]]
                check(observed.shape == buffer['raw'][i].shape
                    and np.array_equal(observed.view(np.uint32), buffer['raw'][i].view(np.uint32)),
                    'Saved patch source cells differ bitwise')
                buffer['checked_scans'].append(scan)
                counts['raw_cells_bitwise_checked'] += observed.size
            counts['compact_files'] += 1
            del power
            print('PASS_SINGLE_READ_NATIVE_SOURCE_MEDIANS_AND_ALL_JOB_PATCHES', native, scan, flush=True)
        check(all(buffer['checked_scans'] == list(SCANS) for buffer in buffers) and counts == EXPECTED_COUNTS,
            'Combined saved-output/source QA inventory incomplete: ' + str(counts))
        # Authenticate all observed byte identities again without reopening datasets.
        for name, expected in pins.items():
            path = confined(root, name)
            check(path.stat().st_size == expected['bytes'] and digest(path) == expected['sha256'], 'Input changed during QA: ' + name)
        use = measured(started)
        check(0 < use['process_CPU_seconds_including_imports'] <= CPU_CAP and 0 < use['wall_seconds_including_imports'] <= WALL_CAP
            and 0 < use['peak_RSS_bytes'] <= RAM_CAP, 'Measured QA resource cap exceeded')
        receipt = {'schema': 'SETI_S2017_ADJACENT_SIX_INTERIOR_JOBS_SAVED_OUTPUT_SOURCE_QA_V1',
            'status': 'PASS1524_S2017_ADJACENT_MAPS54_FIXED_PROFILES_AND668736_BITWISE_SOURCE_CELLS',
            'qa_script_sha256': args.expected_qa_sha256, 'driver_sha256': DRIVER_SHA,
            'public_freeze_commit': args.freeze_commit, 'qa_public_freeze_commit': args.qa_freeze_commit,
            'static_review_sha256': args.expected_static_review_sha256,
            'counts': counts, 'all_input_byte_pins': pins,
            'scope_SHA256s': {batch: getattr(args, 'expected_' + batch + '_scope_sha256') for batch in BATCHES},
            'search_receipt_SHA256s': {batch: getattr(args, 'expected_' + batch + '_receipt_sha256') for batch in BATCHES},
            'prerequisites': gates, 'runtime_versions': versions, 'CPU_cap_s': CPU_CAP,
            'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP, **use,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'detector_or_score_rerun': False, 'fixed_track_optimization_applied': False,
            'native_full_row_medians_recomputed': True, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
            'qualified_sky_detection': False, 'OFF_veto_applied': False, 'calibrated_SNR_FAP': False,
            'limitations': ['Scores and winning hypotheses are authenticated saved outputs; detector scores are not independently recomputed.',
                'All192 full-native float32 medians are independently recomputed before float64 promotion; compressed/raw-sidecar provenance is authenticated from actual source QA and unchanged twelve compact files, whose192 decoded rows and668736 raw-patch occurrences are checked here.',
                'All1524 core row medians are independently recomputed; remaining saved detector normalization statistics are hash-bound and schema-checked, without refiltering.',
                'Adjacent170/172 were selected after native171 results were known, within one historical2017 S-band visit; jobs and maximized drift-width hypotheses are correlated and exploratory, with no calibrated significance, sensitivity, qualifiedOFF veto or sky detection.']}
        save_new(review / 'QA_RECEIPT.json', receipt)
        print(json.dumps({'status': receipt['status'], 'counts': counts, **use}), flush=True)
    except BaseException as error:
        if review.is_dir() and not (review / 'QA_RECEIPT.json').exists():
            save_new(review / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_QA_PRESERVE_OUTPUTS_NO_RERUN',
                'error_type': type(error).__name__, 'error': str(error), 'qa_script_sha256': args.expected_qa_sha256,
                'public_freeze_commit': args.freeze_commit, 'counts': counts, 'all_input_byte_pins': pins,
                'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'detector_or_score_rerun': False, **measured(started)})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
