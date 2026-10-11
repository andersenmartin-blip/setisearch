"""Independent once-only QA of saved raw-power injection benchmark outputs.

No detector import or carrier/drift search. Numerical access starts only after
two exact COMPLETE receipts, public freeze and root GO. Six authenticated
native sources are decoded once. Small raw windows independently reconstruct
local501 medians, standardized truth/winner sums and matched-zero score deltas.
Saved full-core MAD/location statistics are authenticated, not refiltered.
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
BASE = 'analysis/s2017_injection_20261011'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
JOBS = {'offcenter': (64, 192), 'known_center_competitor': (128,)}
COUNT, CORE, HALO, C0 = 1048576, 4096, 4000, 171 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DRIFT_INDICES, WIDTHS, AMPS = (245, 392, 539), (1, 9), (0, 1, 3, 6, 12)
CPU_CAP, WALL_CAP, RAM_CAP = 180, 300, 2 * 1024**3
ATOL, RTOL = 1e-7, 1e-10
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
PINS = {'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json':
    '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json':
    'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    'analysis/new_visit_recovery/results/review/QA_RECEIPT.json':
    'e50f21617244a8d45dcdd3698e95db13c8ca1d11891f4bfa21ef7012bcb70d6f'}


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
        check(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def confined(root, name):
    p = Path(name)
    check(not p.is_absolute() and '..' not in p.parts, 'Confined relative path required')
    path = root / p
    check(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined or symlink input')
    return path


def save_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def same(actual, expected, message):
    check(actual.shape == expected.shape and np.array_equal(actual, expected), message)


def close(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    check(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
          and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def raw_window(power, centers, width):
    radius = 250 + width // 2
    indexes = centers[:, None] - C0 + np.arange(-radius, radius + 1)[None, :]
    check(indexes.min() >= 0 and indexes.max() < COUNT, 'Raw arithmetic window lacks native support')
    return power[np.arange(16)[:, None], indexes].astype(np.float64), indexes


def raw_box_sums(raw, norm, width):
    # Independent point arithmetic: each scoring cell gets its own odd501
    # running median. This is not detector preprocessing or a search rerun.
    median = np.asarray(norm['row_power_median'])
    scale = np.asarray(norm['row_residual_MAD_scale'])
    location = np.asarray(norm['row_winsorized_residual_location'])
    check(raw.shape == (16, 501 + width - 1), 'Local raw window shape differs')
    normalized = raw / median[:, None]
    running = np.stack([np.median(normalized[:, i:i + 501], axis=1) for i in range(width)], axis=1)
    standardized = (normalized[:, 250:250 + width] - running - location[:, None]) / scale[:, None]
    return standardized.sum(axis=1)


def score_from_sums(sums, width):
    return float(sums.sum() / np.sqrt(16 * width))


def modified_window(baseline, indexes, truth_centers, truth_width, increments):
    modified = baseline.copy()
    support = np.abs(indexes + C0 - truth_centers[:, None]) <= truth_width // 2
    modified[support] += np.broadcast_to(increments[:, None], modified.shape)[support]
    return modified


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope-sha256', 'qa-scope-sha256', 'qa-sha256', 'freeze-commit', 'qa-freeze-commit',
                 'offcenter-receipt-sha256', 'known-center-competitor-receipt-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-complete-jobs', action='store_true', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    check(args.root_go_after_complete_jobs and re.fullmatch('[0-9a-f]{40}', args.freeze_commit)
          and re.fullmatch('[0-9a-f]{40}', args.qa_freeze_commit),
          'Exact actual freeze and root GO after both COMPLETE jobs required')
    for value in (args.scope_sha256, args.qa_scope_sha256, args.qa_sha256, args.offcenter_receipt_sha256,
                  args.known_center_competitor_receipt_sha256):
        check(re.fullmatch('[0-9a-f]{64}', value), 'Exact reviewed SHA256 required')
    check(digest(Path(__file__).resolve()) == args.qa_sha256, 'Reviewed QA source differs')
    pins, handles = {}, []
    counts = {'maps': 0, 'baseline_maps': 0, 'modified_maps': 0, 'carrier_maxima': 0,
              'carrier_rank_positions': 0, 'valid_hypothesis_records': 0,
              'diagnostics': 0, 'zero_geometry_queries': 0, 'modified_cases': 0,
              'truth_audits': 0, 'raw_truth_window_cells': 0, 'independent_truth_scores': 0,
              'independent_tuple_score_checks': 0, 'core_row_medians': 0,
              'width9_stress_diagnostics': 0, 'compact_files': 0, 'decoded_rows': 0}
    expected = {'maps': 450, 'baseline_maps': 18, 'modified_maps': 432,
                'carrier_maxima': 450 * CORE, 'carrier_rank_positions': 450 * CORE,
                'valid_hypothesis_records': 450 * CORE * 1570, 'diagnostics': 540,
                'zero_geometry_queries': 108, 'modified_cases': 432, 'truth_audits': 540,
                'raw_truth_window_cells': 270 * 16 * (501 + 509), 'independent_truth_scores': 1080,
                'independent_tuple_score_checks': 540 * 5 * 2, 'core_row_medians': 450 * 16,
                'width9_stress_diagnostics': 270, 'compact_files': 6, 'decoded_rows': 96}
    out = root / BASE / 'results/review'
    created_output = False
    arithmetic_error_max = 0.

    def pin(path, declared=None):
        observed = {'bytes': path.stat().st_size, 'sha256': digest(path)}
        check(declared is None or observed == declared, 'File byte pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        check(name not in pins or pins[name] == observed, 'Input changed: ' + name)
        pins[name] = observed
        return observed

    def loaded(path, declared=None):
        raw = path.read_bytes()
        observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        check(declared is None or declared == observed, 'Loaded exact bytes differ: ' + str(path))
        name = path.relative_to(root).as_posix()
        check(name not in pins or pins[name] == observed, 'Loaded input changed: ' + name)
        pins[name] = observed
        return raw

    def text(path, sha=None):
        raw = loaded(path)
        check(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Reviewed metadata SHA differs')
        return json.loads(raw, object_pairs_hook=pairs)

    def archive(path, sha, size):
        raw = loaded(path, {'sha256': sha, 'bytes': size})
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            check(len(values.files) == len(set(values.files)), 'Duplicate archive fields')
            return {key: values[key] for key in values.files}

    def deadline(signum, frame):
        raise TimeoutError('Frozen independent QA CPU/wall cap reached')

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    signal.alarm(max(1, int(WALL_CAP - (time.monotonic() - started))))
    try:
        pin(Path(__file__).resolve())
        for name in ('ACTIVE_FAMILY_FLOCK.lock', 'ACTIVE_SCIENCE_SLOT_0_FLOCK.lock',
                     'ACTIVE_SCIENCE_SLOT_1_FLOCK.lock'):
            handle = (root / BASE / name).open('a+b')
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_lock = (root / 'analysis/new_visit_recovery/results/ACTIVE_FAMILY_FLOCK.lock').open('a+b')
        handles.append(source_lock)
        fcntl.flock(source_lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        qa_scope = text(root / BASE / 'qa_scope.json', args.qa_scope_sha256)
        check(qa_scope['schema'] == 'SETI_S2017_SAVED_INJECTION_INDEPENDENT_QA_SCOPE_V1'
              and qa_scope['qa_source_sha256'] == args.qa_sha256
              and qa_scope['benchmark_scope_sha256'] == args.scope_sha256
              and qa_scope['benchmark_public_freeze_commit'] == args.freeze_commit
              and qa_scope['CPU_cap_s'] == CPU_CAP and qa_scope['wall_cap_s'] == WALL_CAP
              and qa_scope['memory_cap_bytes'] == RAM_CAP and qa_scope['expected_counts'] == expected
              and qa_scope['numeric_tolerance'] == {'absolute': ATOL, 'relative': RTOL}
              and qa_scope['new_HTTP_requests'] == 0 and qa_scope['detector_import_or_search_rerun'] is False,
              'Reviewed separate once-only QA scope differs')
        scope = text(root / BASE / 'scope.json', args.scope_sha256)
        check(scope['schema'] == 'SETI_S2017_RAW_POWER_INJECTION_SCOPE_V1'
              and scope['cores'] == [64, 128, 192] and scope['scan_order'] == list(SCANS)
              and scope['jobs'] == {key: list(qs) for key, qs in JOBS.items()}
              and scope['injected_widths'] == [1, 9] and scope['injected_drift_indices'] == list(DRIFT_INDICES)
              and scope['amplitudes_baseline_residual_MAD_units_per_cell'] == list(AMPS)
              and scope['search_widths'] == [1, 3] and scope['drift_grid_count'] == 785
              and scope['native_chunk_index'] == 171 and scope['core_channels'] == CORE
              and scope['halo_channels'] == HALO and scope['truth_reference_offset_in_core'] == 2048
              and scope['local_diagnostic_halfwidth_channels'] == 5
              and scope['rounded_center_tolerance_channels'] == 1
              and scope['operational_score_threshold'] == 10
              and scope['QA_truth_arithmetic_absolute_tolerance'] == ATOL
              and scope['QA_truth_arithmetic_relative_tolerance'] == RTOL
              and (scope['baseline_maps'], scope['modified_maps'], scope['total_maps']) == (18, 432, 450),
              'Different frozen injection family')
        for name, sha in scope['text_code_pins'].items():
            path = confined(root, name)
            check(path.suffix in ('.json', '.py'), 'Only code/metadata admission pins permitted')
            check(pin(path)['sha256'] == sha, 'Frozen metadata/code differs')
        gates = {name: text(confined(root, name), sha) for name, sha in PINS.items()}
        source, acquisition, priorqa = (gates[name] for name in PINS)
        check(acquisition['status'] == 'COMPLETE_NEW_S2017_SIX_SCAN_NATIVE_CHUNK_ACQUISITION_EXPLORATORY_ONLY'
              and priorqa['status'] == 'PASS_THREE_S2017_MAPS_NINE_FIXED_PROFILES_AND111456_BITWISE_SOURCE_CELLS'
              and scope['compact_records'] == acquisition['decoded_files'], 'Actual prior native source admission differs')
        receipts = {}
        for job, qs in JOBS.items():
            sha = getattr(args, job + '_receipt_sha256')
            receipt = text(root / BASE / 'results' / job / 'EXECUTION_RECEIPT.json', sha)
            check(receipt['schema'] == 'SETI_RAW_POWER_INJECTION_EXECUTION_V1'
                  and receipt['status'] == 'COMPLETE_PROSPECTIVE_RAW_POWER_INJECTION_BENCHMARK_EXPLORATORY_ONLY'
                  and receipt['job'] == job and receipt['scope_sha256'] == args.scope_sha256
                  and receipt['driver_sha256'] == scope['text_code_pins'][BASE + '/driver.py']
                  and receipt['public_freeze_commit'] == args.freeze_commit
                  and receipt['counts']['maps'] == len(qs) * 150
                  and receipt['counts']['baseline_maps'] == len(qs) * 6
                  and receipt['counts']['modified_maps'] == len(qs) * 144
                  and receipt['counts']['diagnostic_records'] == len(qs) * 180
                  and receipt['counts']['truth_audits'] == len(qs) * 180
                  and receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0,
                  'Both exact completed benchmark receipts required')
            check(0 < receipt['process_CPU_seconds'] <= 1000 and 0 < receipt['wall_seconds'] <= 1800
                  and 0 < receipt['peak_RSS_bytes'] <= 2 * 1024**3, 'Completed benchmark resource limits differ')
            check(receipt['runtime_versions'] == {**VERSIONS, 'HDF5': '1.14.6'}
                  and receipt['CPU_cap_s'] == 1000 and receipt['wall_cap_s'] == 1800
                  and receipt['memory_cap_bytes'] == 2 * 1024**3 and receipt['science_slot'] in (0, 1)
                  and receipt['workspace_cap_bytes'] == 8 * 1024**3
                  and 0 < receipt['workspace_allocated_bytes_final'] <= 8 * 1024**3
                  and receipt['final_scope_and_six_compact_byte_SHA256s_unchanged'] is True
                  and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED',
                  'Exact completed benchmark versions/caps/final byte integrity differ')
            for flag in ('new_sky_coverage', 'old_fixed_profiles_rerun', 'qualified_SETI_detection',
                         'calibrated_SNR_FAP_or_global_completeness'):
                check(receipt[flag] is False, 'Benchmark scope/status claim differs')
            receipts[job] = receipt
        out.mkdir(parents=True, exist_ok=False)
        created_output = True
        save_new(out / 'INPUT_PINS.json', {'qa_sha256': args.qa_sha256, 'scope_sha256': args.scope_sha256,
            'qa_scope_sha256': args.qa_scope_sha256, 'public_freeze_commit': args.freeze_commit,
            'qa_public_freeze_commit': args.qa_freeze_commit, 'metadata_pins': pins.copy(),
            'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL}})
        global np
        import numpy as np
        import h5py
        import hdf5plugin
        check(hdf5plugin.register(filters='bshuf', force=True), 'Supported bitshuffle registration failed')
        check({p: importlib.metadata.version(p) for p in VERSIONS} == VERSIONS
              and h5py.version.hdf5_version == '1.14.6', 'Exact runtime differs')
        drift_grid, times = np.linspace(-4., 4., 785), np.arange(16) * TSAMP
        powers, headers = {}, {}
        check([r['scan_id'] for r in acquisition['decoded_files']] == list(SCANS)
              and [r['label'] for r in source['sources']] == list(SCANS), 'Source scan order differs')
        previous_end = float('-inf')
        for record, identity in zip(acquisition['decoded_files'], source['sources']):
            scan = record['scan_id']
            header = identity['current_header']['data_attributes']
            check(header['tsamp'] == TSAMP and header['fch1'] * 1e6 == FCH1
                  and header['foff'] * 1e6 == DF and header['tstart'] >= previous_end
                  and record['shape'] == [16, 1, COUNT] and record['source_channel0'] == C0
                  and [r['time_row'] for r in record['decoded_rows']] == list(range(16)),
                  'Actual scan metadata/frame or complete row order differs')
            previous_end = header['tstart'] + 16 * TSAMP / 86400
            path = root / 'analysis/new_visit_recovery/results/acquire' / record['array_file']
            check(record['array_file'] == scan + '.compact.h5', 'Canonical compact identity differs')
            pin(path, {'bytes': record['bytes'], 'sha256': record['file_sha256']})
            check(priorqa['all_input_byte_pins'][str(path)] == pins[path.relative_to(root).as_posix()],
                  'Actual prior QA source bytes differ')
            with h5py.File(path, 'r', rdcc_nbytes=0) as handle:
                data = handle['data']
                check(data.shape == (16, 1, COUNT) and data.dtype == np.dtype('<f4')
                      and int(data.attrs['original_source_frequency_chunk_origin']) == C0
                      and data.attrs['original_source_url'] == identity['url']
                      and data.attrs['original_source_etag'] == identity['etag'], 'Native source identity differs')
                power = data[:, 0, :]
            check(np.isfinite(power).all() and (power >= 0).all(), 'Invalid source power')
            for row in record['decoded_rows']:
                check(row['decoded_bytes'] == COUNT * 4 and hashlib.sha256(power[row['time_row']].tobytes()).hexdigest()
                      == row['decoded_sha256'], 'Native decoded row SHA differs')
                counts['decoded_rows'] += 1
            powers[scan], headers[scan] = power, identity['current_header']['data_attributes']
            counts['compact_files'] += 1
        rankings = []
        norm_schema = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                       'row_residual_MAD_scale', 'normalization_unmasked_counts', 'normalization_source_channels'}
        map_schema = {'frequency_hz_at_tref': ('<f8', (CORE,)),
            'maximum_robust_box_track_score': ('<f8', (CORE,)), 'winning_drift_hz_s': ('<f8', (CORE,)),
            'winning_width_channels': ('<i2', (CORE,)), 'valid_hypothesis_count': ('<i8', (CORE,)),
            'source_reference_channels': ('<i8', (CORE,)), 'drift_grid_hz_s': ('<f8', (785,))}

        for job, qs in JOBS.items():
            jobout = root / BASE / 'results' / job
            map_records = text(jobout / 'MAPS.json')
            diag = text(jobout / 'DIAGNOSTICS.json')
            audits = text(jobout / 'TRUTH_AUDITS.json')
            check(diag['schema'] == 'SETI_RAW_POWER_INJECTION_DIAGNOSTICS_V1', 'Diagnostic schema differs')
            expected_maps, expected_cases = [], []
            for q in qs:
                for scan in SCANS:
                    expected_maps.append('%s_q%03d_zero' % (scan, q))
                    for di in DRIFT_INDICES:
                        for width in WIDTHS:
                            for amplitude in AMPS:
                                case = '%s_q%03d_d%03d_w%d_A%d' % (scan, q, di, width, amplitude)
                                expected_cases.append(case)
                                if amplitude:
                                    expected_maps.append(case)
            check([r['map_id'] for r in map_records] == expected_maps
                  and [r['case_id'] for r in diag['records']] == expected_cases
                  and [r['case_id'] for r in audits] == expected_cases, 'Exact complete map/case/audit inventory order differs')
            by_map, by_audit = ({r[key]: r for r in rows} for rows, key in ((map_records, 'map_id'), (audits, 'case_id')))
            files = {'MAPS.json', 'DIAGNOSTICS.json', 'TRUTH_AUDITS.json', 'EXECUTION_RECEIPT.json'}
            files.update(name + suffix for name in expected_maps for suffix in ('.npz', '_normalization.json'))
            files.update(case + '_truth_audit.npz' for case in expected_cases)
            check({p.relative_to(jobout).as_posix() for p in jobout.rglob('*') if p.is_file()} == files,
                  'Complete exact job files without failure/temporary extras required')
            baseline_cache, seen_maps = {}, set()

            def map_value(map_id, scan, q):
                if map_id in baseline_cache:
                    return baseline_cache[map_id]
                check(map_id not in seen_maps, 'Nonbaseline map loaded twice')
                rec = by_map[map_id]
                check(rec['path'] == map_id + '.npz' and rec['normalization_path'] == map_id + '_normalization.json'
                      and rec['scan_id'] == scan and rec['core_q'] == q, 'Saved map identity differs')
                value = archive(jobout / rec['path'], rec['sha256'], rec['bytes'])
                normal = text(jobout / rec['normalization_path'], rec['normalization_sha256'])
                channels = np.arange(C0 + q * CORE, C0 + (q + 1) * CORE)
                check(set(value) == set(map_schema) and set(normal) == norm_schema, 'Map/normalization schema differs')
                for key, (dtype, shape) in map_schema.items():
                    check(value[key].dtype == np.dtype(dtype) and value[key].shape == shape
                          and np.isfinite(value[key]).all(), 'Map array precision/shape/finite differs: ' + key)
                same(value['source_reference_channels'], channels, 'Map absolute physical channels differ')
                same(value['frequency_hz_at_tref'], FCH1 + DF * channels, 'Map physical frequencies differ')
                same(value['drift_grid_hz_s'], drift_grid, 'Own785 drift grid differs')
                same(value['valid_hypothesis_count'], np.full(CORE, 1570), 'Incomplete1570 hypothesis support')
                check(np.isin(value['winning_drift_hz_s'], drift_grid).all()
                      and np.isin(value['winning_width_channels'], (1, 3)).all(), 'Winning hypotheses outside search family')
                same(np.asarray(normal['normalization_source_channels']), channels, 'Normalization physical core differs')
                same(np.asarray(normal['normalization_unmasked_counts']), np.full(16, CORE), 'Normalization core mask differs')
                for key in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                    a = np.asarray(normal[key])
                    check(a.shape == (16,) and np.isfinite(a).all(), 'Normalization row shape differs')
                    if key in ('row_power_median', 'row_residual_MAD_scale'):
                        check((a > 0).all(), 'Normalization median/scale not positive')
                order = np.lexsort((channels, -value['maximum_robust_box_track_score']))
                rank = np.empty(CORE, dtype=np.int64)
                rank[order] = np.arange(1, CORE + 1)
                same(np.sort(rank), np.arange(1, CORE + 1), 'All4096 rank positions incomplete')
                seen_maps.add(map_id)
                counts['maps'] += 1
                counts['carrier_maxima'] += CORE
                counts['carrier_rank_positions'] += CORE
                counts['valid_hypothesis_records'] += int(value['valid_hypothesis_count'].sum())
                counts['baseline_maps' if map_id.endswith('_zero') else 'modified_maps'] += 1
                result = value, normal, order, rank
                if map_id.endswith('_zero'):
                    baseline_cache[map_id] = result
                    same(np.median(powers[scan][:, q * CORE:(q + 1) * CORE].astype(np.float64), axis=1),
                         np.asarray(normal['row_power_median']), 'Baseline raw float64 core row median differs')
                    counts['core_row_medians'] += 16
                return result

            job_nominal, job_full_nominal = 0, 0
            for d in diag['records']:
                scan, q, di, width, amplitude = (d[key] for key in ('scan_id', 'core_q', 'injected_drift_index',
                    'injected_width_channels', 'amplitude_per_cell_baseline_MAD_units'))
                case = '%s_q%03d_d%03d_w%d_A%d' % (scan, q, di, width, amplitude)
                check(scan in SCANS and q in qs and di in DRIFT_INDICES and width in WIDTHS and amplitude in AMPS
                      and d['case_id'] == case, 'Case geometry outside frozen complete matrix')
                baseline_id = '%s_q%03d_zero' % (scan, q)
                check(d['map_id'] == (case if amplitude else baseline_id)
                      and d['map_sha256'] == by_map[d['map_id']]['sha256']
                      and d['matched_zero_map_id'] == baseline_id
                      and d['matched_zero_map_sha256'] == by_map[baseline_id]['sha256'],
                      'Current and shared matched-zero map identities differ')
                m0, n0, order0, rank0 = map_value(baseline_id, scan, q)
                m, norm, order, rank = map_value(d['map_id'], scan, q)
                truth = np.rint(C0 + q * CORE + 2048 + drift_grid[di] * times / DF).astype(np.int64)
                increments = amplitude * np.asarray(n0['row_power_median']) * np.asarray(n0['row_residual_MAD_scale'])
                check(d['injected_drift_hz_s'] == float(drift_grid[di])
                      and d['truth_reference_source_channel'] == C0 + q * CORE + 2048
                      and d['actual_first_midpoint_MJD'] == headers[scan]['tstart'] + .5 * TSAMP / 86400
                      and d['role'] == source['sources'][SCANS.index(scan)]['role'], 'Case actual frequency/time/role frame differs')
                same(np.asarray(d['relative_row_midpoint_seconds']), times, 'Case relative16-row times differ')
                same(np.asarray(d['rounded_truth_centers']), truth, 'Case absolute rounded truth centers differ')
                same(np.asarray(d['raw_power_increment_per_row']), increments, 'Frozen baseline raw injection calibration differs')
                same(np.asarray(d['total_added_raw_power_per_row']), width * increments, 'Injected width-integrated raw power differs')
                if amplitude:
                    core = powers[scan][:, q * CORE:(q + 1) * CORE].astype(np.float64)
                    support = truth[:, None] - (C0 + q * CORE) + np.arange(-(width // 2), width // 2 + 1)[None, :]
                    check(support.min() >= 0 and support.max() < CORE, 'Truth injection lacks frozen core support')
                    core[np.arange(16)[:, None], support] += increments[:, None]
                    same(np.median(core, axis=1), np.asarray(norm['row_power_median']), 'Recomputed modified raw core median differs')
                    counts['core_row_medians'] += 16
                    del core
                rec = by_audit[case]
                check(rec['path'] == case + '_truth_audit.npz' == d['truth_audit_path'], 'Truth audit identity differs')
                audit = archive(jobout / rec['path'], rec['sha256'], rec['bytes'])
                check(set(audit) == {'baseline_raw_power', 'modified_raw_power', 'rounded_truth_centers',
                    'raw_power_increment_per_row', 'baseline_truth_standardized_row_box_sums',
                    'modified_truth_standardized_row_box_sums'}, 'Raw truth audit schema differs')
                for key, dtype, shape in (
                    ('baseline_raw_power', '<f8', (16, 501 + width - 1)),
                    ('modified_raw_power', '<f8', (16, 501 + width - 1)),
                    ('rounded_truth_centers', '<i8', (16,)),
                    ('raw_power_increment_per_row', '<f8', (16,)),
                    ('baseline_truth_standardized_row_box_sums', '<f8', (16,)),
                    ('modified_truth_standardized_row_box_sums', '<f8', (16,))):
                    check(audit[key].dtype == np.dtype(dtype) and audit[key].shape == shape
                          and np.isfinite(audit[key]).all(), 'Raw truth audit precision/shape/finite differs')
                raw0, indexes = raw_window(powers[scan], truth, width)
                raw1 = modified_window(raw0, indexes, truth, width, increments)
                for field, raw in (('baseline_raw_power', raw0), ('modified_raw_power', raw1)):
                    check(audit[field].dtype == np.dtype('<f8'), 'Truth raw patch must be float64')
                    same(audit[field].view(np.uint64), raw.view(np.uint64), 'Truth raw source/injection cells differ bitwise')
                same(audit['rounded_truth_centers'], truth, 'Audit rounded centers differ')
                same(audit['raw_power_increment_per_row'], increments, 'Audit injection increments differ')
                sums0, sums1 = raw_box_sums(raw0, n0, width), raw_box_sums(raw1, norm, width)
                for key, sums in (('baseline_truth_standardized_row_box_sums', sums0),
                                  ('modified_truth_standardized_row_box_sums', sums1)):
                    close(audit[key], sums, 'Independent raw-to-standardized truth row sum differs')
                    arithmetic_error_max = max(arithmetic_error_max, float(np.max(np.abs(audit[key] - sums))))
                score0, score1 = score_from_sums(sums0, width), score_from_sums(sums1, width)
                close(d['baseline_truth_score'], score0, 'Raw arithmetic baseline truth score differs')
                close(d['modified_truth_score'], score1, 'Raw arithmetic modified truth score differs')
                check(d['truth_score_delta_from_zero'] == d['modified_truth_score'] - d['baseline_truth_score'],
                      'Stored matchedtruth delta arithmetic differs')
                close(d['truth_score_delta_from_zero'], score1 - score0, 'Independent matchedtruth delta differs')
                window = np.arange(2043, 2054)

                def choose(value, indexes):
                    return int(indexes[np.lexsort((value['source_reference_channels'][indexes],
                        -value['maximum_robust_box_track_score'][indexes]))[0]])

                choices = {'local_window_winner': (m, norm, choose(m, window)),
                    'nearest_reference_carrier_winner': (m, norm, 2048),
                    'full_core_winner': (m, norm, int(order[0])),
                    'matched_zero_local_window_winner': (m0, n0, choose(m0, window)),
                    'matched_zero_full_core_winner': (m0, n0, int(order0[0]))}
                for field, (value, normal, index) in choices.items():
                    t = d[field]
                    winning_width = int(value['winning_width_channels'][index])
                    drift, frequency = float(value['winning_drift_hz_s'][index]), float(value['frequency_hz_at_tref'][index])
                    centers = np.rint((frequency - FCH1) / DF + drift * np.arange(16) * TSAMP / DF).astype(np.int64)
                    overlap = np.maximum(0, np.minimum(centers + winning_width // 2, truth + width // 2)
                        - np.maximum(centers - winning_width // 2, truth - width // 2) + 1)
                    check(t['reference_source_channel'] == int(value['source_reference_channels'][index])
                          and t['frequency_hz_at_own_first_midpoint'] == frequency
                          and t['score'] == float(value['maximum_robust_box_track_score'][index])
                          and t['drift_hz_s'] == drift and t['width_channels'] == winning_width,
                          'Saved selected tuple differs from full4096 map ranking/winner')
                    for key, expected_array in (('rounded_absolute_centers', centers),
                        ('center_errors_channels', centers - truth), ('overlap_channels_by_row', overlap),
                        ('overlap_fraction_of_winning_box_by_row', overlap / winning_width)):
                        same(np.asarray(t[key]), expected_array, 'Tuple rounded16-row geometry/support differs')
                    check(t['center_geometry_within_one_channel_all16'] == bool(np.all(np.abs(centers - truth) <= 1))
                          and t['positive_interval_overlap_all16'] == bool(np.all(overlap > 0))
                          and t['exact_injected_width_match'] == (winning_width == width)
                          and t['score_at_least_operational10'] == (t['score'] >= 10), 'Tuple support flags differ')
                    base, indexwin = raw_window(powers[scan], centers, winning_width)
                    changed = (base if field.startswith('matched_zero_') else
                               modified_window(base, indexwin, truth, width, increments))
                    baseline_same = score_from_sums(raw_box_sums(base, n0, winning_width), winning_width)
                    current_same = score_from_sums(raw_box_sums(changed, normal, winning_width), winning_width)
                    close(t['matched_zero_score_same_winning_tuple'], baseline_same, 'Independent exact matchedzero tuple score differs')
                    close(t['score'], current_same, 'Independent raw arithmetic selected winner score differs')
                    check(t['score_delta_same_tuple_from_zero'] == t['score'] - t['matched_zero_score_same_winning_tuple'],
                          'Stored same-tuple score delta differs')
                    close(t['score_delta_same_tuple_from_zero'], current_same - baseline_same,
                          'Independent same-tuple score delta differs')
                    counts['independent_tuple_score_checks'] += 2
                local, zero = d['local_window_winner'], d['matched_zero_local_window_winner']
                full, zero_full = d['full_core_winner'], d['matched_zero_full_core_winner']
                already = zero['center_geometry_within_one_channel_all16'] and zero['score'] >= 10
                full_already = zero_full['center_geometry_within_one_channel_all16'] and zero_full['score'] >= 10
                nominal = (amplitude > 0 and width == 1 and local['exact_injected_width_match']
                    and local['center_geometry_within_one_channel_all16'] and local['score'] >= 10
                    and d['modified_truth_score'] > d['baseline_truth_score'] and not already
                    and local['matched_zero_score_same_winning_tuple'] < 10
                    and local['score_delta_same_tuple_from_zero'] > 0)
                full_nominal = (amplitude > 0 and width == 1 and full['exact_injected_width_match']
                    and full['center_geometry_within_one_channel_all16'] and full['score'] >= 10
                    and d['modified_truth_score'] > d['baseline_truth_score'] and not full_already
                    and full['matched_zero_score_same_winning_tuple'] < 10
                    and full['score_delta_same_tuple_from_zero'] > 0)
                check(d['local_window_reference_offsets'] == [-5, 5]
                      and d['zero_already_center_compatible_at_operational10'] == already
                      and d['zero_full_core_already_center_compatible_at_operational10'] == full_already
                      and d['local_known_truth_nominal_width1_matched_tuple_threshold_crossing_at10'] == nominal
                      and d['full_core_rank1_nominal_width1_matched_tuple_threshold_crossing_at10'] == full_nominal
                      and d['baseline_all_compatible_templates_below10_proven'] is False
                      and d['width9_is_template_mismatch_stress'] == (width == 9)
                      and d['nominal_width9_recovery_available_in_search_family'] is False
                      and d['local_max_score_delta_from_zero_local_max'] == local['score'] - zero['score'],
                      'Fixed zero-attribution/width9 stress/recovery labels differ')
                rankings.append({'case_id': case, 'map_id': d['map_id'], 'nearest_carrier_global_rank': int(rank[2048]),
                    'local_winner_global_rank': int(rank[choices['local_window_winner'][2]]),
                    'full_winner_global_rank': int(rank[choices['full_core_winner'][2]])})
                counts['diagnostics'] += 1
                counts['zero_geometry_queries' if amplitude == 0 else 'modified_cases'] += 1
                counts['truth_audits'] += 1
                counts['raw_truth_window_cells'] += raw0.size
                counts['independent_truth_scores'] += 2
                counts['width9_stress_diagnostics'] += width == 9
                job_nominal += nominal
                job_full_nominal += full_nominal
            check(seen_maps == set(expected_maps) and job_nominal == receipts[job]['counts'][
                'local_known_truth_nominal_width1_matched_tuple_threshold_crossings_at10']
                and job_full_nominal == receipts[job]['counts'][
                'full_core_rank1_nominal_width1_matched_tuple_threshold_crossings_at10'],
                'Job completeness/matched-tuple threshold count differs')
            print('PASS_SAVED_INJECTION_JOB', job, flush=True)
        check(counts == expected, 'Independent QA inventory incomplete: ' + str(counts))
        for name, declared in pins.items():
            path = confined(root, name)
            check(path.stat().st_size == declared['bytes'] and digest(path) == declared['sha256'],
                  'Input/code bytes changed during independent QA')
        usage = {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(0 < usage['process_CPU_seconds_including_imports'] <= CPU_CAP
              and 0 < usage['wall_seconds'] <= WALL_CAP and 0 < usage['peak_RSS_bytes'] <= RAM_CAP,
              'Independent QA resource cap exceeded')
        save_new(out / 'SAVED_MAP_RANK_DIAGNOSTICS.json', {'schema': 'SETI_INJECTION_SAVED_MAP_RANK_DIAGNOSTICS_V1',
            'rank_basis': 'All4096 authenticated saved carrier maxima; descending score, ascending physical channel ties',
            'records': rankings})
        save_new(out / 'QA_RECEIPT.json', {'schema': 'SETI_S2017_SAVED_INJECTION_INDEPENDENT_QA_V1',
            'status': 'PASS450_MAPS540_DIAGNOSTICS_RAW_ARITHMETIC_AND_ROUNDED_SUPPORT_NO_DETECTOR_RERUN',
            'qa_sha256': args.qa_sha256, 'scope_sha256': args.scope_sha256, 'public_freeze_commit': args.freeze_commit,
            'qa_scope_sha256': args.qa_scope_sha256, 'qa_public_freeze_commit': args.qa_freeze_commit,
            'job_receipt_sha256s': {'offcenter': args.offcenter_receipt_sha256,
                'known_center_competitor': args.known_center_competitor_receipt_sha256},
            'counts': counts, 'input_byte_pins': pins, 'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
            'max_truth_row_sum_arithmetic_absolute_difference': arithmetic_error_max,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP, **usage,
            'runtime_versions': {**VERSIONS, 'HDF5': '1.14.6'}, 'new_HTTP_requests': 0,
            'detector_import_or_search_rerun': False, 'new_sky_coverage': False, 'qualified_SETI_detection': False,
            'calibrated_SNR_FAP_or_global_completeness': False,
            'limitations': ['Authenticated saved full4096 maxima are not independently exhaustively rescored; selected truth/winner tuples are independently checked from raw local windows.',
                'Full-core float64 row medians are independently recomputed. Saved full-core residual MAD/location parameters are hash-bound and schema-checked, without detector preprocessing rerun.',
                'Direct local arithmetic and the detector cumulative-prefix box arithmetic can differ in floating rounding; the tolerance was fixed prospectively.',
                'One known historical background visit, separate per-scan injections; operational10 labels are conditional benchmark diagnostics, not sky sensitivity, calibrated significance or independent replication.']})
        print(json.dumps({'status': 'PASS_INDEPENDENT_SAVED_INJECTION_QA', 'counts': counts, **usage}), flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            save_new(out / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_QA_PRESERVED_NO_RETRY',
                'error_type': type(error).__name__, 'error': str(error), 'counts': counts, 'input_byte_pins': pins,
                'qa_sha256': args.qa_sha256, 'scope_sha256': args.scope_sha256, 'new_HTTP_requests': 0,
                'qa_scope_sha256': args.qa_scope_sha256, 'qa_public_freeze_commit': args.qa_freeze_commit,
                'detector_import_or_search_rerun': False})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
