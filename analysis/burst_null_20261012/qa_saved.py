"""Independent saved-output QA of the fixed IID Gamma51 search experiment.

Import/check-only use standard-library metadata only. Root --run admission is
required before replaying any frozen model stream. No producer, detector,
SciPy filter, telescope array or protected bank is imported/opened. The full
search grid is never rerun. All model sources are bit-replayed; normalization
is independently reconstructed over every whole winning core, with the other
local audit scores explicitly conditional on saved residual scale/location.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import itertools
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

BASE = 'analysis/burst_null_20261012'
JOBS = tuple('null%02d' % i for i in range(1, 9))
DOMAINS = tuple((native, 4 + 8 * k) for native in (170, 171, 172) for k in range(32))
CHUNK, CORE, HALO, FULL_ROWS, BURST_ROWS = 1048576, 4096, 4000, 16, 4
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
STARTS = (0, 2, 4, 6, 8, 10, 12)
PERMUTATIONS = tuple(itertools.permutations(range(4)))
PRIMARY_STATUS = 'COMPLETE_96_IID_GAMMA_NULL_MAPS387_AUDITS3_ORDER_DIAGNOSTICS'
STATUS = 'PASS_8_IID_GAMMA_FAMILIES768_MAPS3096_AUDITS24_ORDER_QUERIES576_PERMUTATION_SCORES'
GO_STATUS = 'GO_INDEPENDENT_SAVED_IID_GAMMA_QA'
PRIMARY_GO_STATUS = 'GO_8_FULL_IID_GAMMA_NULL_FAMILIES'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
DETECTOR_SHA = '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45'
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP = 600, 900, 2 * 1024**3, 20 * 1024**2
ATOL, RTOL = 1e-7, 1e-10
NORM_ATOL, NORM_RTOL = 1e-12, 1e-10
EXPECTED = {'families': 8, 'maps': 768, 'carrier_maxima': 3145728,
            'valid_hypothesis_records': 7002390528, 'normalization_records': 768,
            'model_raw_crops_regenerated': 768, 'model_raw_rows_SHA256': 12288,
            'model_raw_cells_regenerated': 148635648, 'raw_core_row_medians': 12288,
            'score_audit_queries': 3096, 'score_audit_row_boxes': 12384,
            'score_audit_raw_cells': 6229152, 'TOP20_entries': 160, 'TOP3_entries': 24,
            'order_queries': 24, 'row_center_boxes': 384, 'permutation_scores': 576}
NORM_FIELDS = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
               'row_residual_MAD_scale', 'normalization_unmasked_counts',
               'normalization_source_channel_interval_half_open'}
MAP_SCHEMA = {'frequency_hz_at_window_reference': ('<f8', (4096,)),
              'maximum_robust_box_track_score': ('<f8', (4096,)),
              'winning_drift_hz_s': ('<f8', (4096,)),
              'winning_drift_grid_index': ('<i2', (4096,)),
              'winning_window_start_row': ('<i2', (4096,)),
              'winning_width_channels': ('<i2', (4096,)),
              'valid_hypothesis_count': ('<i8', (4096,)),
              'source_reference_channels': ('<i8', (4096,)),
              'drift_grid_hz_s': ('<f8', (159,))}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def unique_pairs(items):
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON key: ' + key)
        value[key] = item
    return value


def read_json(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    name = Path(name)
    require(not name.is_absolute() and '..' not in name.parts, 'Confined relative path required')
    path = root / name
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined/symlink input')
    return path


def create_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= OUTPUT_CAP, 'QA output cap exceeded')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b), message)


def near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)
    return float(np.max(np.abs(a - b))) if a.size else 0.


def norm_near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=NORM_ATOL, rtol=NORM_RTOL), message)
    return float(np.max(np.abs(a - b))) if a.size else 0.


def full_core_normalization(raw, core_absolute0):
    """Independent medians on every whole-core residual, never saved scales.

    All core centers have complete support in the 4000-channel halo. Chunked
    sliding-window np.median does not share the producer's SciPy median_filter.
    The unused outer halo residual outputs are not independently refiltered.
    """
    require(raw.dtype == np.dtype('<f4') and raw.shape == (16, 12096)
            and np.isfinite(raw).all() and (raw >= 0).all(), 'Winning raw full-core schema differs')
    levels = np.median(raw[:, HALO:HALO + CORE].astype(np.float64), axis=1)
    residuals = np.empty((16, CORE), dtype=np.float64)
    for row in range(16):
        normalized = raw[row].astype(np.float64) / levels[row]
        for first in range(0, CORE, 256):
            count = min(256, CORE - first)
            start = HALO + first
            windows = np.lib.stride_tricks.sliding_window_view(normalized[start - 250:start + count + 250], 501)
            residuals[row, first:first + count] = normalized[start:start + count] - np.median(windows, axis=1)
    centers = np.median(residuals, axis=1)
    scales = 1.4826 * np.median(np.abs(residuals - centers[:, None]), axis=1)
    require(np.isfinite(scales).all() and (scales > 0).all(), 'Independent residual scale invalid')
    locations = centers + np.mean(np.clip(residuals - centers[:, None], -5 * scales[:, None], 5 * scales[:, None]), axis=1)
    return {'row_power_median': levels.tolist(), 'row_residual_median': centers.tolist(),
            'row_residual_MAD_scale': scales.tolist(), 'row_winsorized_residual_location': locations.tolist(),
            'normalization_unmasked_counts': [CORE] * 16,
            'normalization_source_channel_interval_half_open': [core_absolute0, core_absolute0 + CORE]}


def local_rows(raw, normalization, width, physical_rows):
    require(raw.shape == (4, 503) and width in (1, 3), 'Raw audit/width schema differs')
    result = []
    for i, physical_row in enumerate(physical_rows):
        ratio = raw[i].astype(np.float64) / normalization['row_power_median'][int(physical_row)]
        terms = [(ratio[p] - np.median(ratio[p - 250:p + 251])
                  - normalization['row_winsorized_residual_location'][int(physical_row)])
                 / normalization['row_residual_MAD_scale'][int(physical_row)]
                 for p in range(251 - width // 2, 252 + width // 2)]
        result.append(float(np.asarray(terms).sum()))
    result = np.asarray(result, dtype=np.float64)
    return result, float(result.sum() / np.sqrt(4 * width))


def full_raw_matrix(raw, crop0, centers, physical_rows, width, normalization):
    matrix = np.empty((4, 4), dtype=np.float64)
    for i, physical_row in enumerate(physical_rows):
        ratio = raw[int(physical_row)].astype(np.float64) / normalization['row_power_median'][int(physical_row)]
        for j, center in enumerate(centers):
            center = int(center) - crop0
            terms = []
            for p in range(center - width // 2, center + width // 2 + 1):
                require(p - 250 >= 0 and p + 251 <= len(ratio), 'Winning matrix local501 support incomplete')
                terms.append((ratio[p] - np.median(ratio[p - 250:p + 251])
                              - normalization['row_winsorized_residual_location'][int(physical_row)])
                             / normalization['row_residual_MAD_scale'][int(physical_row)])
            matrix[i, j] = np.asarray(terms).sum()
    return matrix


def centers_for(chosen):
    # Preserve the producer's multiplication association before absolute rint.
    times = np.arange(4) * TSAMP
    return np.rint((chosen['frequency_hz_at_window_reference'] - FCH1) / DF
                   + chosen['drift_hz_s'] * times / DF).astype(np.int64)


def order_statistics(matrix, centers, width):
    """Exact ranks use authenticated saved M after independent raw tolerance QA."""
    vectors = [tuple(int(centers[j]) for j in p) for p in PERMUTATIONS]
    scores = np.asarray([(((matrix[0, p[0]] + matrix[1, p[1]]) + matrix[2, p[2]])
                         + matrix[3, p[3]]) / np.sqrt(4 * width) for p in PERMUTATIONS], dtype=np.float64)
    seen, representatives, distinct, multiplicities = {}, [], [], []
    for i, vector in enumerate(vectors):
        if vector not in seen:
            seen[vector] = len(distinct)
            representatives.append(i)
            distinct.append(vector)
            multiplicities.append(0)
        multiplicities[seen[vector]] += 1
    distinct_scores = scores[representatives]
    identity = float(scores[0])
    wrong = np.asarray([s for v, s in zip(distinct, distinct_scores) if v != tuple(int(c) for c in centers)])
    greater, ties = int(np.count_nonzero(distinct_scores > identity)), int(np.count_nonzero(distinct_scores == identity))
    return {'permutation_scores': scores.tolist(), 'permutation_center_vectors': [list(v) for v in vectors],
            'distinct_center_vectors': [list(v) for v in distinct],
            'distinct_representative_permutation_indices': representatives,
            'distinct_assignment_multiplicities': multiplicities, 'distinct_scores': distinct_scores.tolist(),
            'identity_score': identity, 'distinct_center_count': len(set(centers)),
            'stationary_centers': len(set(centers)) == 1, 'duplicate_centers': len(set(centers)) < 4,
            'distinct_assignment_count': len(distinct), 'wrong_order_distinct_count': len(wrong),
            'wrong_order_max_score': float(wrong.max()) if len(wrong) else None,
            'wrong_order_median_score': float(np.median(wrong)) if len(wrong) else None,
            'identity_minus_wrong_order_max': identity - float(wrong.max()) if len(wrong) else None,
            'identity_minus_wrong_order_median': identity - float(np.median(wrong)) if len(wrong) else None,
            'identity_rank_best': 1 + greater, 'identity_rank_worst': greater + ties,
            'identity_exact_tie_count': ties, 'identity_equal_score_wrong_order_count': ties - 1,
            'wrong_order_strictly_better_than_identity_count': greater}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--check-only', action='store_true')
    p.add_argument('--run', action='store_true')
    p.add_argument('--root-go', default=BASE + '/QA_ROOT_GO.json')
    for name in ('scope-sha256', 'qa-sha256', 'root-go-sha256'):
        p.add_argument('--' + name)
    p.add_argument('--job-receipt', action='append', default=[])
    return p.parse_args()


def main():
    args = parse_args()
    root = args.root.resolve()
    require(args.check_only != args.run, 'Exactly one check-only/run mode required')
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_IID_GAMMA_QA_INTERFACE_NO_MODEL_STREAMS_REPLAYED',
                          'expected_counts': EXPECTED, 'winning_full_core_count': 'dynamic1..3 per family',
                          'numerical_libraries_imported': False, 'source_values_read': False}))
        return
    for value in (args.scope_sha256, args.qa_sha256, args.root_go_sha256):
        require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'Exact run SHA256 required')
    declared_jobs = {}
    for item in args.job_receipt:
        name, sep, value = item.partition('=')
        require(sep and name in JOBS and name not in declared_jobs and re.fullmatch('[0-9a-f]{64}', value), 'Unique eight job receipt declarations required')
        declared_jobs[name] = value
    require(set(declared_jobs) == set(JOBS), 'Eight exact COMPLETE job receipt pins required')
    base = root / BASE
    qa_path, admission_path, failure_path = (base / name for name in ('QA_RECEIPT.json', 'QA_ADMISSION.json', 'QA_FAILURE.json'))
    require(not any(p.exists() for p in (qa_path, admission_path, failure_path)), 'Create-only QA namespace exists; preserve without rerun')
    started, cpu_started = time.monotonic(), time.process_time()
    pins, locks, counts = {}, [], {key: 0 for key in EXPECTED}
    created = False

    def loaded(name, declaration=None, expected_sha=None):
        path = confined(root, name)
        raw = path.read_bytes()
        actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        require(declaration is None or actual == {key: declaration[key] for key in ('bytes', 'sha256')}, 'File pin differs: ' + str(name))
        require(expected_sha is None or actual['sha256'] == expected_sha, 'Exact SHA differs: ' + str(name))
        require(str(name) not in pins or pins[str(name)] == actual, 'Input changed between reads')
        pins[str(name)] = actual
        return raw

    def metadata(name, declaration=None, expected_sha=None):
        return read_json(loaded(name, declaration, expected_sha))

    def archive(declaration):
        raw = loaded(declaration['path'], declaration)
        with np.load(io.BytesIO(raw), allow_pickle=False) as handle:
            require(len(handle.files) == len(set(handle.files)), 'Duplicate NPZ member')
            return {key: handle[key] for key in handle.files}

    def pin_for(name):
        return {'path': name, **pins[name]}

    try:
        scope = metadata(BASE + '/scope.json', expected_sha=args.scope_sha256)
        loaded(BASE + '/qa_saved.py', expected_sha=args.qa_sha256)
        go = metadata(args.root_go, expected_sha=args.root_go_sha256)
        require(go['status'] == GO_STATUS and go['scope_sha256'] == args.scope_sha256
                and go['qa_sha256'] == args.qa_sha256 and go['job_receipt_sha256s'] == declared_jobs
                and go['CPU_cap_s'] == CPU_CAP and go['wall_cap_s'] == WALL_CAP
                and go['memory_cap_bytes'] == RAM_CAP and go['output_cap_bytes'] == OUTPUT_CAP,
                'Exact prospective independent QA GO/caps differ')
        driver_name = BASE + '/driver.py'
        loaded(driver_name, expected_sha=go['driver_sha256'])
        require(scope['schema'] == 'SETI_FULL_BURST_IID_GAMMA_MODEL_SCOPE_V1'
                and scope['jobs'] == {job: {'family_index': i, 'synthetic_role': 'SYNTHETIC_ENGINEERING', 'synthetic_tstart_mjd': 0.0}
                                      for i, job in enumerate(JOBS, 1)}, 'Frozen model family job set differs')
        for declaration in scope['text_code_pins'] + scope['prior_reference_pins']:
            require(Path(declaration['path']).suffix in ('.py', '.json', '.md', '.txt', '.csv'), 'Scope may bind only source/reference text')
            loaded(declaration['path'], declaration)
        require(any(p['path'] == BASE + '/qa_saved.py' and p['sha256'] == args.qa_sha256 for p in scope['text_code_pins']), 'QA code not bound by prospective scope')
        loaded(DETECTOR, expected_sha=DETECTOR_SHA)
        require(scope['model_law'] == {'distribution': 'IID Gamma', 'shape': 51.0, 'scale': 1.0 / 51.0, 'mean': 1.0,
                                      'fitted_to_observations': False, 'verified_instrument_degrees_of_freedom': False}
                and scope['rng']['bit_generator'] == 'PCG64' and scope['rng']['root_entropy'] == 20261012
                and scope['rng']['draw_dtype'] == 'float64' and scope['rng']['one_conversion_dtype'] == '<f4'
                and scope['rng']['all96_crops_generated_before_search'] is True and scope['rng']['primary_redraws'] == 0,
                'Fixed raw Gamma model/generator law differs')
        require(scope['model_only'] is True and scope['observational_arrays_opened'] is False
                and scope['protected2016_data_opened'] is False and scope['new_observation'] is False
                and scope['sky_FAP_or_permutation_p_value'] is False and scope['qualified_SETI_detection'] is False
                and scope['masks'] is None and scope['geometric_veto'] is False and scope['data_selected_exclusions'] == []
                and scope['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED', 'Model-only closed historical/protected source contract differs')
        primary_go = metadata(BASE + '/ROOT_GO.json')
        require(primary_go['status'] == PRIMARY_GO_STATUS and primary_go['scope_sha256'] == args.scope_sha256
                and primary_go['driver_sha256'] == go['driver_sha256'] and primary_go['qa_sha256'] == args.qa_sha256,
                'Original prospective primary admission differs')
        primary_go_pin = pin_for(BASE + '/ROOT_GO.json')
        # Scope/source admissions remain synthetic-only, before NumPy/RNG use.
        require(scope['core_channels'] == CORE and scope['halo_channels'] == HALO
                and scope['source_rows_per_scan'] == 16 and scope['window_length_rows'] == 4
                and scope['window_start_rows'] == list(STARTS)
                and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79}
                and scope['widths_channels'] == [1, 3], 'Inherited search geometry differs')
        require([(v['native_chunk_index'], v['core_q']) for v in scope['core_domains']] == list(DOMAINS), 'Canonical96 model domains differ')
        primary = {}
        for job in JOBS:
            name = BASE + '/results/' + job + '/EXECUTION_RECEIPT.json'
            value = metadata(name, expected_sha=declared_jobs[job])
            require(value['status'] == PRIMARY_STATUS and value['primary_id'] == job
                    and value['scope_sha256'] == args.scope_sha256 and value['driver_sha256'] == go['driver_sha256']
                    and value['root_GO_pin'] == primary_go_pin
                    and all(value['counts'].get(k) == v for k, v in scope['expected_counts_per_family'].items())
                    and 1 <= value['counts']['winning_raw_crops'] <= 3
                    and value['model_only'] is True and value['primary_redraws'] == 0
                    and value['raw_crops_pre_and_post_hashes_match'] is True,
                    'Expected eight completed same-scope model jobs/counts/admission required')
            require(0 < value['process_CPU_seconds'] <= 600 and 0 < value['wall_seconds'] <= 900
                    and 0 < value['peak_RSS_bytes'] <= 2 * 1024**3, 'Completed producer resource bounds differ')
            require(value['new_telescope_HTTP_requests'] == 0 and value['cost_DKK'] == 0, 'Model job must not acquire actual telescope data/payment')
            primary[job] = value
        for name in ('SLOT0.lock', 'SLOT1.lock'):
            lock = (base / name).open('a+b')
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(lock)
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
        resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
        def timeout(signum, frame):
            raise TimeoutError('Independent Gamma QA wall cap reached')
        signal.signal(signal.SIGALRM, timeout)
        signal.alarm(WALL_CAP)
        create_json(admission_path, {'status': 'ADMITTED_EIGHT_COMPLETE_FROZEN_MODEL_JOBS_BEFORE_RNG_REPLAY',
                    'scope_sha256': args.scope_sha256, 'qa_sha256': args.qa_sha256,
                    'root_go_sha256': args.root_go_sha256, 'job_receipt_sha256s': declared_jobs,
                    'model_streams_replayed_at_admission': 0, 'actual_telescope_arrays_opened': False})
        created = True
        global np
        import numpy as np
        require(np.__version__ == '2.3.5', 'Frozen NumPy generator/numeric runtime differs')
        runtime = {'Python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': importlib.metadata.version('scipy')}
        require(all(all(value['runtime_versions'].get(k) == v for k, v in runtime.items()) for value in primary.values()), 'Producer/QA numeric runtime differs')
        drifts = np.linspace(-4., 4., 159)
        selected_all, statistics_all, winning_by_job = {}, {}, {}
        max_norm_difference = max_audit_difference = max_matrix_difference = max_permutation_difference = max_identity_difference = 0.
        winning_core_count = 0

        for family_index, job in enumerate(JOBS, 1):
            folder = BASE + '/results/' + job
            receipt = primary[job]
            declarations = {item['path']: item for item in receipt['output_byte_pins']}
            require(len(declarations) == len(receipt['output_byte_pins']), 'Duplicate completed output path')
            def meta_output(name):
                path = folder + '/' + name
                require(path in declarations, 'Completed receipt omitted required JSON')
                return metadata(path, declarations[path])
            maps = meta_output('MAPS.json')
            rng_manifest = meta_output('RNG_MANIFEST.json')
            audits, top20, top3 = (meta_output(name) for name in ('SCORE_AUDITS.json', 'TOP20.json', 'TOP3.json'))
            orders = meta_output('ORDER_DIAGNOSTICS.json')
            require(maps['schema'] == 'SETI_GAMMA_NULL_COMBINED_MAPS_V1'
                    and audits['schema'] == 'SETI_GAMMA_NULL_SCORE_AUDITS_V1'
                    and orders['schema'] == 'SETI_GAMMA_NULL_ORDER_DIAGNOSTICS_V1'
                    and rng_manifest['schema'] == 'SETI_GAMMA_NULL_CANONICAL_RAW_MANIFEST_V1'
                    and all(v['primary_id'] == job for v in (maps, audits, orders, rng_manifest, top20, top3))
                    and rng_manifest['family_index'] == family_index and orders['family_index'] == family_index
                    and rng_manifest['model_law'] == scope['model_law'] and rng_manifest['rng'] == scope['rng']
                    and rng_manifest['raw_crops_pre_and_post_hashes_match'] is True and rng_manifest['primary_redraws'] == 0,
                    'Closed model JSON schema/identity/law differs')
            require(all(v['schema'] == 'SETI_GAMMA_NULL_GLOBAL_RANKS_V1'
                        and v['selection_rule'] == scope['target_ranking'] for v in (top20, top3)), 'Saved ranking rule differs')
            require(len(declarations) == 588 + receipt['counts']['winning_raw_crops'], 'Closed588+winningraw output count differs')
            require(len(maps['records']) == len(rng_manifest['records']) == 96 and len(audits['records']) == 387
                    and len(orders['records']) == 3, 'Closed96maps/387audits/3orders inventory differs')
            require([(v['native_chunk_index'], v['core_q']) for v in maps['records']] == list(DOMAINS), 'Model map domain order differs')
            infos, raw_crops, blocks, channel_blocks = {}, {}, [], []
            for domain_index, ((native, q), declaration, rng_record) in enumerate(zip(DOMAINS, maps['records'], rng_manifest['records'])):
                first, crop0 = native * CHUNK + q * CORE, native * CHUNK + q * CORE - HALO
                map_id = '%s_native%d_q%03d' % (job, native, q)
                require(rng_record['domain_index'] == domain_index and rng_record['native_chunk_index'] == native
                        and rng_record['family_index'] == family_index
                        and rng_record['core_q'] == q and rng_record['map_id'] == map_id
                        and rng_record['loaded_channel_interval_half_open'] == [crop0, first + CORE + HALO]
                        and rng_record['core_channel_interval_half_open'] == [first, first + CORE]
                        and rng_record['raw_shape'] == [16, 12096] and rng_record['raw_dtype'] == '<f4'
                        and rng_record['draw_shape'] == [16, 12096] and rng_record['draw_dtype'] == 'float64'
                        and rng_record['root_entropy'] == 20261012 and rng_record['spawn_key'] == [family_index, domain_index]
                        and rng_record['bit_generator'] == 'PCG64', 'Frozen raw model stream/geometry differs')
                generator = np.random.Generator(np.random.PCG64(np.random.SeedSequence(20261012, spawn_key=(family_index, domain_index))))
                require(generator.bit_generator.state == rng_record['initial_bit_generator_state'], 'Frozen initial RNG state differs')
                raw = generator.gamma(shape=51., scale=1. / 51., size=(16, 12096)).astype('<f4')
                require(generator.bit_generator.state == rng_record['final_bit_generator_state'], 'Frozen final RNG state differs')
                require(raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4')
                        and np.isfinite(raw).all() and (raw >= 0).all()
                        and hashlib.sha256(raw.tobytes(order='C')).hexdigest() == rng_record['raw_sha256'], 'Exact quantized Gamma source SHA differs')
                require(len(rng_record['raw_row_sha256s']) == 16, 'Sixteen raw row SHA declarations required')
                for row, row_sha in zip(raw, rng_record['raw_row_sha256s']):
                    require(hashlib.sha256(row.tobytes(order='C')).hexdigest() == row_sha, 'Model source row SHA differs')
                counts['model_raw_crops_regenerated'] += 1
                counts['model_raw_rows_SHA256'] += 16
                counts['model_raw_cells_regenerated'] += raw.size
                require(declaration['path'] == folder + '/' + map_id + '.npz' and declaration['map_id'] == map_id
                        and declaration['reference_channel_interval_half_open'] == [first, first + CORE]
                        and declaration['loaded_channel_interval_half_open'] == [crop0, first + CORE + HALO]
                        and declaration['searched_carriers'] == CORE and declaration['valid_hypotheses_per_carrier'] == 2226,
                        'Synthetic map coordinates/support differ')
                require(declaration['path'] in declarations and all(declaration[k] == declarations[declaration['path']][k] for k in ('bytes', 'sha256')), 'Map must match terminal output pin')
                arrays = archive(declaration)
                require(set(arrays) == set(MAP_SCHEMA), 'Map field inventory differs')
                for name, (dtype, shape) in MAP_SCHEMA.items():
                    require(arrays[name].dtype == np.dtype(dtype) and arrays[name].shape == shape and np.isfinite(arrays[name]).all(), 'Map dtype/shape/finite differs: ' + name)
                channels = np.arange(first, first + CORE, dtype=np.int64)
                equal(arrays['source_reference_channels'], channels, 'Map carrier channels differ')
                equal(arrays['frequency_hz_at_window_reference'], FCH1 + DF * channels, 'Map frequencies differ')
                equal(arrays['drift_grid_hz_s'], drifts, 'Map drift grid differs')
                equal(arrays['valid_hypothesis_count'], np.full(CORE, 2226), 'Map full declared valid counts differ')
                di = arrays['winning_drift_grid_index']
                require((di >= 0).all() and (di < 159).all() and np.isin(arrays['winning_window_start_row'], STARTS).all()
                        and np.isin(arrays['winning_width_channels'], (1, 3)).all(), 'Stored winning tuple outside family')
                equal(arrays['winning_drift_hz_s'], drifts[di], 'Winning drift/index differs')
                norm_pin = declaration['normalization']
                require(norm_pin['path'] == folder + '/' + map_id + '_normalization.json' and norm_pin['path'] in declarations,
                        'Canonical bound normalization path differs')
                norm = metadata(norm_pin['path'], norm_pin)
                require(set(norm) == NORM_FIELDS, 'Normalization field inventory differs')
                equal(norm['normalization_source_channel_interval_half_open'], [first, first + CORE], 'Normalization static core differs')
                equal(norm['normalization_unmasked_counts'], [CORE] * 16, 'Normalization must have no masks')
                for name in NORM_FIELDS - {'normalization_source_channel_interval_half_open', 'normalization_unmasked_counts'}:
                    require(np.asarray(norm[name]).shape == (16,) and np.isfinite(norm[name]).all(), 'Sixteen finite normalization parameters required')
                require(np.all(np.asarray(norm['row_power_median']) > 0) and np.all(np.asarray(norm['row_residual_MAD_scale']) > 0), 'Normalization scale invalid')
                equal(norm['row_power_median'], np.median(raw[:, HALO:HALO + CORE].astype(np.float64), axis=1), 'All-model raw core medians differ')
                raw_crops[native, q] = raw
                infos[native, q] = {'arrays': arrays, 'norm': norm, 'record': declaration, 'rng': rng_record,
                                    'order': np.lexsort((channels, -arrays['maximum_robust_box_track_score']))}
                blocks.append(arrays['maximum_robust_box_track_score'])
                channel_blocks.append(channels)
                counts['maps'] += 1
                counts['carrier_maxima'] += CORE
                counts['valid_hypothesis_records'] += int(arrays['valid_hypothesis_count'].sum())
                counts['normalization_records'] += 1
                counts['raw_core_row_medians'] += 16

            def tuple_record(key, index, rank=None):
                native, q = key
                value = infos[key]['arrays']
                start = int(value['winning_window_start_row'][index])
                result = {'primary_id': job, 'scan_id': job, 'family_index': family_index,
                          'synthetic_role': 'SYNTHETIC_ENGINEERING',
                          'primary_target': 'IID_GAMMA_MODEL', 'data_origin': 'SYNTHETIC_IID_GAMMA_MODEL',
                          'native_chunk_index': native, 'core_q': q, 'map_id': infos[key]['record']['map_id'],
                          'carrier_index_in_core': int(index), 'source_reference_channel': int(value['source_reference_channels'][index]),
                          'frequency_hz_at_window_reference': float(value['frequency_hz_at_window_reference'][index]),
                          'window_start_row': start, 'window_length_rows': 4, 'window_source_rows': list(range(start, start + 4)),
                          'reference_time_s_from_synthetic_scan_start': (start + .5) * TSAMP,
                          'drift_grid_index': int(value['winning_drift_grid_index'][index]),
                          'drift_hz_s': float(value['winning_drift_hz_s'][index]),
                          'width_channels': int(value['winning_width_channels'][index]),
                          'score': float(value['maximum_robust_box_track_score'][index])}
                if rank is not None:
                    result['rank'] = rank
                return result

            scores, channels = np.concatenate(blocks), np.concatenate(channel_blocks)
            equal(len(np.unique(channels)), 96 * CORE, 'Nonoverlapping full96 carrier domains required')
            ranking, selected = np.lexsort((channels, -scores)), []
            for index in ranking:
                channel = int(channels[index])
                if any(abs(channel - old['source_reference_channel']) <= 3 for old in selected):
                    continue
                native, q = channel // CHUNK, (channel % CHUNK) // CORE
                selected.append(tuple_record((native, q), channel % CORE, len(selected) + 1))
                if len(selected) == 20:
                    break
            require(top20['records'] == selected and top3['records'] == selected[:3], 'Independent pooled TOP20/TOP3 ranking differs')
            counts['TOP20_entries'] += 20
            counts['TOP3_entries'] += 3
            selected_all[job] = selected[:3]
            seen, seen_global = set(), set()
            queries_by_id = {}
            for query in audits['records']:
                key = query['native_chunk_index'], query['core_q']
                kind = query['query_kind']
                require(key in infos and query['normalization'] == infos[key]['record']['normalization'], 'Audit domain/normalization differs')
                if kind == 'global_top3':
                    rank = query['selected_tuple']['rank']
                    require(rank in (1, 2, 3) and rank not in seen_global, 'Global TOP3 query duplicate/outside rank')
                    seen_global.add(rank)
                    chosen = selected[rank - 1]
                    expected_id = 'global_top%02d' % rank
                else:
                    require(kind in ('first', 'midpoint', 'last', 'core_max') and (*key, kind) not in seen, 'Unexpected/duplicate core audit')
                    seen.add((*key, kind))
                    index = {'first': 0, 'midpoint': 2048, 'last': 4095, 'core_max': int(infos[key]['order'][0])}[kind]
                    chosen = tuple_record(key, index)
                    expected_id = 'native%d_q%03d_%s' % (*key, kind)
                require(query['query_id'] == expected_id and query['selected_tuple'] == chosen
                        and query['map_id'] == chosen['map_id'] and query['capsule']['path'] == folder + '/' + expected_id + '_raw4x503.npz', 'Canonical selected audit tuple differs')
                require(query['capsule']['path'] in declarations, 'Audit capsule omitted from terminal pins')
                capsule = archive(query['capsule'])
                capsule_schema = {'raw_power': ('<f4', (4, 503)), 'absolute_time_rows': ('<i8', (4,)),
                                  'rounded_absolute_centers': ('<i8', (4,)), 'standardized_row_box_sums': ('<f8', (4,))}
                require(set(capsule) == set(capsule_schema), 'Audit capsule field inventory differs')
                for name, (dtype, shape) in capsule_schema.items():
                    require(capsule[name].dtype == np.dtype(dtype) and capsule[name].shape == shape and np.isfinite(capsule[name]).all(), 'Audit capsule schema differs')
                physical_rows = chosen['window_start_row'] + np.arange(4, dtype=np.int64)
                centers = centers_for(chosen)
                crop0 = key[0] * CHUNK + key[1] * CORE - HALO
                indices = centers[:, None] - crop0 + np.arange(-251, 252)[None, :]
                require(indices.min() >= 0 and indices.max() < 12096, 'Audit trajectory crop support incomplete')
                raw = raw_crops[key][physical_rows[:, None], indices]
                equal(capsule['absolute_time_rows'], physical_rows, 'Audit physical rows differ')
                equal(capsule['rounded_absolute_centers'], centers, 'Audit absolute rounding differs')
                equal(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Audit raw model source bits differ')
                row_sums, score = local_rows(raw, infos[key]['norm'], chosen['width_channels'], physical_rows)
                max_audit_difference = max(max_audit_difference, near(capsule['standardized_row_box_sums'], row_sums, 'Independent conditional audit row arithmetic differs'),
                                           near(chosen['score'], score, 'Independent conditional audit score differs'))
                queries_by_id[expected_id] = query
                counts['score_audit_queries'] += 1
                counts['score_audit_row_boxes'] += 4
                counts['score_audit_raw_cells'] += raw.size
            require(seen == {(n, q, kind) for n, q in DOMAINS for kind in ('first', 'midpoint', 'last', 'core_max')}
                    and seen_global == {1, 2, 3}, 'Complete fixed audit matrix required')

            winning_keys = {(v['native_chunk_index'], v['core_q']) for v in selected[:3]}
            fresh_norms = {}
            for key, info in infos.items():
                saved_raw_pin = info['rng']['winning_raw_capsule']
                if key not in winning_keys:
                    require(saved_raw_pin is None, 'Only distinct winning cores may have full raw capsules')
                    continue
                require(saved_raw_pin and saved_raw_pin['path'] == folder + '/' + info['record']['map_id'] + '_raw16x12096.npz'
                        and saved_raw_pin['path'] in declarations, 'Distinct winning full raw capsule required')
                saved_raw = archive(saved_raw_pin)
                require(set(saved_raw) == {'raw_power'} and saved_raw['raw_power'].dtype == np.dtype('<f4')
                        and saved_raw['raw_power'].shape == (16, 12096), 'Winning full raw capsule schema differs')
                equal(saved_raw['raw_power'].view(np.uint32), raw_crops[key].view(np.uint32), 'Winning full raw capsule/replayed model bits differ')
                fresh = full_core_normalization(saved_raw['raw_power'], key[0] * CHUNK + key[1] * CORE)
                for name in NORM_FIELDS:
                    if name in ('normalization_unmasked_counts', 'normalization_source_channel_interval_half_open'):
                        equal(info['norm'][name], fresh[name], 'Exact reconstructed normalization support differs')
                    else:
                        max_norm_difference = max(max_norm_difference, norm_near(info['norm'][name], fresh[name], 'Independently reconstructed full-core normalization differs: ' + name))
                fresh_norms[key] = fresh
            require(receipt['counts']['winning_raw_crops'] == len(winning_keys), 'Distinct winning raw crop count differs')
            winning_core_count += len(winning_keys)
            winning_by_job[job] = len(winning_keys)
            summaries = []
            for rank, record in enumerate(orders['records'], 1):
                chosen = selected[rank - 1]
                query = queries_by_id['global_top%02d' % rank]
                key = chosen['native_chunk_index'], chosen['core_q']
                centers = centers_for(chosen)
                rows = chosen['window_start_row'] + np.arange(4, dtype=np.int64)
                width = chosen['width_channels']
                crop0 = key[0] * CHUNK + key[1] * CORE - HALO
                channel0, channel_count = int(centers.min()) - 251, int(centers.max() - centers.min()) + 503
                require(record['query_id'] == query['query_id'] and record['query_kind'] == 'global_top3'
                        and record['selected_tuple'] == chosen and record['normalization'] == query['normalization']
                        and record['score_audit_capsule'] == query['capsule']
                        and record['raw_source_channel0'] == channel0 and record['raw_channel_count'] == channel_count,
                        'Selected order diagnostic support differs')
                key_fields = ('scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
                              'window_start_row', 'drift_grid_index', 'width_channels')
                require(record['scientific_tuple_key'] == [chosen[name] for name in key_fields]
                        and record['scientific_tuple_multiplicity'] == 1, 'Distinct selected order tuple key/multiplicity differs')
                equal(record['centers'], centers, 'Order fixed centers differ')
                equal(record['source_rows'], rows, 'Order fixed physical rows differ')
                declaration = record['new_capsule']
                require(declaration['path'] == folder + '/global_top%02d_order.npz' % rank
                        and declaration['path'] in declarations, 'Selected order capsule path differs')
                capsule = archive(declaration)
                schema = {'raw_power': ('<f4', (4, channel_count)), 'absolute_time_rows': ('<i8', (4,)),
                          'rounded_absolute_centers': ('<i8', (4,)), 'standardized_row_center_box_sums': ('<f8', (4, 4)),
                          'permutation_scores': ('<f8', (24,)), 'permutation_indices': ('<i2', (24, 4))}
                require(set(capsule) == set(schema), 'Order capsule field inventory differs')
                for name, (dtype, shape) in schema.items():
                    require(capsule[name].dtype == np.dtype(dtype) and capsule[name].shape == shape and np.isfinite(capsule[name]).all(), 'Selected order capsule schema differs')
                equal(capsule['absolute_time_rows'], rows, 'Order capsule rows differ')
                equal(capsule['rounded_absolute_centers'], centers, 'Order capsule centers differ')
                equal(capsule['permutation_indices'], PERMUTATIONS, 'Order lexicographic24 assignments differ')
                require(channel0 >= crop0 and channel0 + channel_count <= crop0 + 12096, 'Order raw envelope crop support incomplete')
                raw = raw_crops[key][rows[:, None], channel0 - crop0 + np.arange(channel_count)[None, :]]
                equal(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Order envelope raw model bits differ')
                matrix = full_raw_matrix(raw_crops[key], crop0, centers, rows, width, fresh_norms[key])
                saved_matrix = capsule['standardized_row_center_box_sums']
                max_matrix_difference = max(max_matrix_difference, near(saved_matrix, matrix, 'Independent full-preprocess winning matrix differs'))
                equal(record['matrix'], saved_matrix, 'Order JSON/saved NPZ matrix differs')
                independent_scores = np.asarray([(((matrix[0, p[0]] + matrix[1, p[1]]) + matrix[2, p[2]]) + matrix[3, p[3]]) / np.sqrt(4 * width) for p in PERMUTATIONS])
                max_permutation_difference = max(max_permutation_difference, near(capsule['permutation_scores'], independent_scores, 'Full-preprocess raw24 assignment scores differ'))
                max_identity_difference = max(max_identity_difference, near(chosen['score'], independent_scores[0], 'Full-preprocess raw winning identity score differs'))
                stats = order_statistics(saved_matrix, centers, width)
                equal(capsule['permutation_scores'], stats['permutation_scores'], 'Exact saved-matrix24 scores differ')
                for name, expected in stats.items():
                    require(record[name] == expected, 'Exact order statistics/ranks/ties differ: ' + name)
                require(record['prior_primary_score'] == chosen['score']
                        and record['identity_minus_prior_primary_score'] == stats['identity_score'] - chosen['score']
                        and record['zero_drift'] == (chosen['drift_hz_s'] == 0)
                        and record['diagnostic_degenerate'] == (stats['distinct_assignment_count'] == 1)
                        and record['rounded_nonzero_drift_degenerate'] == (chosen['drift_hz_s'] != 0 and stats['distinct_assignment_count'] == 1),
                        'Order identity/degeneracy flags differ')
                summaries.append({'query_id': query['query_id'], 'selected_tuple': chosen,
                                  **{name: value for name, value in stats.items() if name not in {
                                      'permutation_scores', 'permutation_center_vectors', 'distinct_center_vectors',
                                      'distinct_representative_permutation_indices', 'distinct_scores'}}})
                counts['order_queries'] += 1
                counts['row_center_boxes'] += 16
                counts['permutation_scores'] += 24
            statistics_all[job] = summaries
            observed = {name for name in pins if name.startswith(folder + '/') and not name.endswith('/EXECUTION_RECEIPT.json')}
            require(observed == set(declarations), 'Independently checked output inventory differs from completed receipt')
            actual = {p.relative_to(root).as_posix() for p in (root / folder).rglob('*') if p.is_file()}
            require(actual == set(declarations) | {folder + '/EXECUTION_RECEIPT.json'}, 'Unexpected/missing completed output file')
            for name, declaration in declarations.items():
                require(pins[name] == {key: declaration[key] for key in ('bytes', 'sha256')}, 'Terminal output byte pin differs')
            counts['families'] += 1
            del infos, raw_crops, blocks, channel_blocks, scores, channels, ranking, fresh_norms
            print('PASS_MODEL_FAMILY_SAVED_QA', job, flush=True)

        require(counts == EXPECTED and 8 <= winning_core_count <= 24, 'Independent model QA exact counts incomplete')
        for name, declaration in pins.items():
            path = confined(root, name)
            require(path.stat().st_size == declaration['bytes'] and digest(path) == declaration['sha256'], 'Input changed during QA: ' + name)
        usage = {'process_CPU_seconds': time.process_time() - cpu_started, 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP
                and 0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Independent model QA resource cap exceeded')
        receipt = {'schema': 'SETI_BURST_NULL_RAW_NOISE_INDEPENDENT_QA_V1', 'status': STATUS,
                   'scope_sha256': args.scope_sha256, 'qa_sha256': args.qa_sha256,
                   'driver_sha256': go['driver_sha256'], 'root_go_sha256': args.root_go_sha256,
                   'root_GO_pin': pin_for(args.root_go), 'job_receipt_sha256s': declared_jobs,
                   'producer_receipt_pins': [pin_for(BASE + '/results/' + job + '/EXECUTION_RECEIPT.json') for job in JOBS],
                   'counts': {**counts, 'winning_raw_core_crops': winning_core_count,
                              'winning_full_core_preprocess_rows': winning_core_count * 16,
                              'winning_full_core_residual_cells': winning_core_count * 16 * CORE},
                   'winning_raw_core_crops_per_family': winning_by_job, 'input_byte_pins': pins,
                   'runtime_versions': runtime, 'selected_top3': selected_all, 'global_TOP3_statistics': statistics_all,
                   'maximum_independent_full_core_normalization_difference': max_norm_difference,
                   'maximum_conditional_audit_arithmetic_difference': max_audit_difference,
                   'maximum_full_preprocess_matrix_difference': max_matrix_difference,
                   'maximum_full_preprocess_permutation_score_difference': max_permutation_difference,
                   'maximum_full_preprocess_identity_score_difference': max_identity_difference,
                   'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
                   'full_core_normalization_tolerance': {'absolute': NORM_ATOL, 'relative': NORM_RTOL},
                   'full_core_MAD_location_reconstructed_for_winning_cores': True,
                   'full_core_MAD_location_reconstructed_for_all_maps': False,
                   'unused_outer_halo_residuals_independently_refiltered': False,
                   'other_audit_scores_conditional_on_saved_full_core_MAD_location': True,
                   'model_streams_replayed_for_bit_verification': True, 'independent_replicates_added_by_QA': 0,
                   'detector_imported': False, 'producer_imported': False, 'full_search_grid_recomputed': False,
                   'actual_telescope_arrays_opened': False, 'protected_2016_arrays_opened': False,
                   'calibrated_telescope_SNR_FAP': False, 'qualified_SETI_detection': False,
                   'new_telescope_HTTP_requests': 0, 'cost_DKK': 0,
                   'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
                   'output_cap_bytes': OUTPUT_CAP, **usage,
                   'limitations': ['Independent full-source model/RNG bit checks and all core row medians cover every generated map.',
                       'Full core residual medians/MAD/winsor locations are reconstructed independently for distinct TOP3-winning cores only.',
                       'Other local audit scores remain conditional on saved full-core residual scale/location.',
                       'Stored carrier maxima, winner geometry and global ranking are checked; the full hypothesis grid is not independently remaximized.',
                       'Exact order ranks/ties use the authenticated saved matrix after independent raw/preprocessing tolerance checks.',
                       'Gamma51 IID is a declared engineering law, not measured radio noise/RFI or a telescope false-alarm calibration.']}
        create_json(qa_path, receipt)
        require(qa_path.stat().st_size + admission_path.stat().st_size <= OUTPUT_CAP, 'Combined20MiB QA output cap exceeded')
        print(STATUS, flush=True)
    except BaseException as exc:
        if created and not qa_path.exists() and not failure_path.exists():
            create_json(failure_path, {'status': 'FAIL_INDEPENDENT_IID_GAMMA_SAVED_QA',
                        'error_type': type(exc).__name__, 'message': str(exc), 'partial_counts': counts,
                        'wall_seconds': time.monotonic() - started, 'full_search_grid_recomputed': False})
        raise
    finally:
        signal.alarm(0)
        for lock in locks:
            lock.close()


if __name__ == '__main__':
    main()
