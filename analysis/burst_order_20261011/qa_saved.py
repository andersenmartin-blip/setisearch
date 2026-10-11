"""Independent QA of fixed burst-four temporal-order diagnostics.

Import and --check-only are source/metadata only. Numerical work requires the
shared root GO, exact prospective scope and source pins, and three COMPLETE
fixed-query receipts. Neither the producer nor the detector is imported.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
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

BASE = 'analysis/burst_order_20261011'
PREVIOUS = 'analysis/burst4_20261011'
PREVIOUS_QA = 'analysis/burst4_20261011_qa/results/QA_RECEIPT.json'
READER = 'analysis/new_visit_search/dependencies/standard_reader.py'
READER_SHA = '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'
MIDPOINT = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = 'analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
ORIGINAL_PINS = {
    MIDPOINT: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
    ADJACENT: '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
    ACQ171: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
    READER: READER_SHA,
}
JOBS = {
    'primary20170428_HIP97319': ('epoch1_off', 'HIP97319'),
    'primary20170428_HIP97461': ('epoch2_off', 'HIP97461'),
    'primary20170428_HIP97663': ('epoch3_off', 'HIP97663'),
}
NATIVES = (170, 171, 172)
DOMAINS = tuple((native, 4 + 8 * k) for native in NATIVES for k in range(32))
CHUNK, CORE, ROWS = 1048576, 4096, 4
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
ATOL, RTOL = 1e-7, 1e-10
CPU_CAP, WALL_CAP, RAM_CAP, QA_OUTPUT_CAP = 600, 900, 2 * 1024**3, 4 * 1024**2
CAPS = {'CPU_cap_s_per_job': CPU_CAP, 'wall_cap_s_per_job': WALL_CAP,
        'memory_cap_bytes_per_job': RAM_CAP, 'max_simultaneous_jobs': 2,
        'memory_cap_bytes_aggregate': 4 * 1024**3,
        'job_output_budget_bytes': 50 * 1024**2,
        'total_output_budget_bytes': 150 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3}
EXPECTED = {'queries': 1161, 'global_TOP3_queries': 9,
            'row_center_boxes': 18576, 'permutation_scores': 27864,
            'source_files': 9, 'source_decoded_rows': 144}
PER_JOB = {key: value // 3 for key, value in EXPECTED.items()}
PERMUTATIONS = tuple(itertools.permutations(range(ROWS)))
KEY_FIELDS = ['scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
              'window_start_row', 'drift_grid_index', 'width_channels']
NORM_FIELDS = {'row_power_median', 'row_residual_median',
               'row_winsorized_residual_location', 'row_residual_MAD_scale',
               'normalization_unmasked_counts', 'normalization_source_channel_interval_half_open'}
DIAGNOSTIC_FIELDS = {'query_id', 'query_kind', 'selected_tuple', 'scientific_tuple_key',
                     'scientific_tuple_multiplicity', 'prior_normalization',
                     'prior_capsule', 'new_capsule', 'centers', 'source_rows',
                     'raw_source_channel0', 'raw_channel_count', 'matrix',
                     'permutation_scores', 'permutation_center_vectors',
                     'distinct_center_vectors', 'distinct_representative_permutation_indices',
                     'distinct_scores', 'distinct_assignment_multiplicities',
                     'identity_score', 'distinct_center_count', 'prior_primary_score',
                     'identity_minus_prior_primary_score', 'zero_drift',
                     'diagnostic_degenerate', 'rounded_nonzero_drift_degenerate',
                     'stationary_centers', 'duplicate_centers', 'distinct_assignment_count',
                     'wrong_order_distinct_count', 'wrong_order_max_score',
                     'wrong_order_median_score', 'identity_minus_wrong_order_max',
                     'identity_minus_wrong_order_median',
                     'identity_rank_best', 'identity_rank_worst', 'identity_exact_tie_count',
                     'identity_equal_score_wrong_order_count',
                     'wrong_order_strictly_better_than_identity_count'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def unique_pairs(items):
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON key: ' + key)
        value[key] = item
    return value


def json_bytes(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Relative confined path required')
    path = root / relative
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Input path is unconfined or symlinked')
    return path


def create_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= QA_OUTPUT_CAP, 'QA JSON exceeds output cap')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b), message)


def near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def independent_matrix(raw, raw_channel0, centers, source_rows, normalization, width):
    """Direct local501 medians, with normalization fixed to each physical row."""
    require(width in (1, 3), 'Fixed width outside inherited family')
    result = np.empty((ROWS, ROWS), dtype=np.float64)
    for row in range(ROWS):
        physical_row = int(source_rows[row])
        ratio = raw[row].astype(np.float64) / float(normalization['row_power_median'][physical_row])
        location = float(normalization['row_winsorized_residual_location'][physical_row])
        scale = float(normalization['row_residual_MAD_scale'][physical_row])
        for column in range(ROWS):
            center = int(centers[column]) - raw_channel0
            terms = []
            for pixel in range(center - width // 2, center + width // 2 + 1):
                require(pixel - 250 >= 0 and pixel + 251 <= raw.shape[1], 'Local501 support outside capsule')
                residual = ratio[pixel] - float(np.median(ratio[pixel - 250:pixel + 251]))
                terms.append((residual - location) / scale)
            result[row, column] = np.asarray(terms, dtype=np.float64).sum()
    require(np.isfinite(result).all(), 'Independent row-center matrix is nonfinite')
    return result


def independent_statistics(matrix, centers, width):
    """Exact artifact statistics from independently validated saved matrix.

    Direct median arithmetic is checked separately within its frozen tolerance.
    Exact ranks and ties use these saved float64 matrix values and the declared
    left-to-right row accumulator, avoiding a tolerance-dependent tie definition.
    """
    vectors = [tuple(int(centers[index]) for index in permutation) for permutation in PERMUTATIONS]
    scores = np.asarray([(((matrix[0, permutation[0]] + matrix[1, permutation[1]])
                          + matrix[2, permutation[2]]) + matrix[3, permutation[3]])
                         / np.sqrt(ROWS * width) for permutation in PERMUTATIONS], dtype=np.float64)
    representatives, distinct, multiplicities, seen = [], [], [], {}
    for index, vector in enumerate(vectors):
        if vector not in seen:
            representatives.append(index)
            distinct.append(vector)
            seen[vector] = len(multiplicities)
            multiplicities.append(0)
        multiplicities[seen[vector]] += 1
    distinct_scores = scores[representatives]
    identity = float(scores[0])
    identity_vector = tuple(int(value) for value in centers)
    wrong = np.asarray([score for vector, score in zip(distinct, distinct_scores)
                        if vector != identity_vector], dtype=np.float64)
    greater = int(np.count_nonzero(distinct_scores > identity))
    ties = int(np.count_nonzero(distinct_scores == identity))
    return {
        'permutation_scores': scores.tolist(),
        'permutation_center_vectors': [list(vector) for vector in vectors],
        'distinct_center_vectors': [list(vector) for vector in distinct],
        'distinct_representative_permutation_indices': representatives,
        'distinct_assignment_multiplicities': multiplicities,
        'distinct_scores': distinct_scores.tolist(), 'identity_score': identity,
        'distinct_center_count': len(set(identity_vector)),
        'stationary_centers': len(set(identity_vector)) == 1,
        'duplicate_centers': len(set(identity_vector)) < ROWS,
        'distinct_assignment_count': len(distinct), 'wrong_order_distinct_count': len(wrong),
        'wrong_order_max_score': float(wrong.max()) if len(wrong) else None,
        'wrong_order_median_score': float(np.median(wrong)) if len(wrong) else None,
        'identity_minus_wrong_order_max': identity - float(wrong.max()) if len(wrong) else None,
        'identity_minus_wrong_order_median': identity - float(np.median(wrong)) if len(wrong) else None,
        'identity_rank_best': 1 + greater, 'identity_rank_worst': greater + ties,
        'identity_exact_tie_count': ties,
        'identity_equal_score_wrong_order_count': ties - 1,
        'wrong_order_strictly_better_than_identity_count': greater,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--run', action='store_true')
    for name in ('scope-sha256', 'qa-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    require(args.check_only != args.run, 'Exactly one of --check-only or --run is required')
    if args.check_only:
        require(len(PERMUTATIONS) == len(set(PERMUTATIONS)) == 24 and PERMUTATIONS[0] == (0, 1, 2, 3),
                'Lexicographic assignment domain differs')
        print(json.dumps({'status': 'PASS_METADATA_ONLY_TEMPORAL_ORDER_QA_INTERFACE',
                          'expected_counts': EXPECTED, 'permutations': [list(p) for p in PERMUTATIONS],
                          'scope_present': (root / BASE / 'scope.json').exists(),
                          'source_values_read': False, 'numeric_libraries_imported': False}))
        return
    for sha in (args.scope_sha256, args.qa_sha256, args.root_go_sha256):
        require(sha is not None and re.fullmatch('[0-9a-f]{64}', sha), 'Exact scope/QA/GO SHA256 is required')
    require(digest(Path(__file__).resolve()) == args.qa_sha256, 'Reviewed QA source differs')
    run(root, args)


def run(root, args):
    started, cpu_started = time.monotonic(), time.process_time()
    pins, source_handles, locks = {}, [], []
    counts = {key: 0 for key in EXPECTED}
    output_created = False
    base = root / BASE
    qa_path = base / 'QA_RECEIPT.json'
    admission_path, failure_path = base / 'QA_INPUT_ADMISSION.json', base / 'QA_FAILURE.json'
    max_matrix_difference, max_permutation_difference, max_identity_difference = 0.0, 0.0, 0.0
    normalized_cores, core_row_medians = 0, 0

    def loaded(path, declaration=None):
        raw = path.read_bytes()
        pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        name = path.relative_to(root).as_posix()
        if declaration is not None:
            require(declaration['path'] == name and pin == {key: declaration[key] for key in ('bytes', 'sha256')},
                    'Input byte pin differs: ' + name)
        require(name not in pins or pins[name] == pin, 'Input changed during admission: ' + name)
        pins[name] = pin
        return raw

    def metadata(path, sha=None, declaration=None):
        raw = loaded(path, declaration)
        require(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Metadata SHA differs: ' + str(path))
        return json_bytes(raw)

    def archive(declaration):
        raw = loaded(confined(root, declaration['path']), declaration)
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            require(len(values.files) == len(set(values.files)), 'Duplicate NPZ members')
            return {key: values[key] for key in values.files}

    def alarm(signum, frame):
        raise TimeoutError('Temporal-order QA CPU/wall cap')

    try:
        require(not any(path.exists() for path in (qa_path, admission_path, failure_path)), 'Create-only QA output already exists')
        go_path = base / 'ROOT_GO.json'
        go = metadata(go_path, args.root_go_sha256)
        require(go['status'] == 'GO_1161_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
                and go['scope_sha256'] == args.scope_sha256 and go['qa_sha256'] == args.qa_sha256
                and all(go.get(key) == value for key, value in CAPS.items()),
                'Root temporal-order QA GO differs')
        scope = metadata(base / 'scope.json', args.scope_sha256)
        require(scope['schema'] == 'SETI_BURST4_TEMPORAL_ORDER_SCOPE_V1'
                and scope['queries_per_target'] == 387 and scope['total_queries'] == 1161
                and scope['global_TOP3_queries'] == 9 and scope['physical_rows_per_query'] == ROWS
                and scope['center_assignments_per_query'] == 24
                and scope['scientific_tuple_key_fields'] == KEY_FIELDS
                and scope['expected_counts_per_target'] == PER_JOB
                and scope['running_median_channels'] == 501
                and scope['identity_score_ATOL'] == ATOL and scope['identity_score_RTOL'] == RTOL
                and scope['rank_tie_epsilon'] == 0 and scope['capsule_budget_bytes'] == 20 * 1024
                and scope['permutation_order'] == 'lexicographic permutations of (0,1,2,3)'
                and scope['permutation_definition'] == 'physical row i samples original center indexed permutation[i]'
                and scope['distinct_assignment_definition'] == 'deduplicate actual integer center vectors; first lexicographic representative'
                and scope['exact_rank_definition'] == 'best=1+number of greater distinct scores; worst=greater+exact_equal'
                and scope['exact_score_accumulation'] == '((M[0,pi0]+M[1,pi1])+M[2,pi2])+M[3,pi3], then divide sqrt(4*width)'
                and scope['score_denominator'] == 'sqrt(4*winning_width_channels)'
                and scope['new_detector_grid'] is False and scope['new_normalization_estimation'] is False
                and scope['new_observation'] is False and scope['mask_or_veto'] is False
                and scope['calibrated_SNR_FAP_or_permutation_p_value'] is False
                and all(scope.get(key) == value for key, value in CAPS.items()),
                'Frozen fixed-assignment scientific/resource contract differs')
        driver_path = base / 'driver.py'
        loaded(driver_path)
        loaded(Path(__file__).resolve())
        require(pins[BASE + '/driver.py']['sha256'] == go['driver_sha256'], 'Reviewed producer source differs')
        signal.signal(signal.SIGALRM, alarm)
        signal.signal(signal.SIGXCPU, alarm)
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
        resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
        signal.alarm(WALL_CAP)
        for name in ('SLOT0.lock', 'SLOT1.lock', 'ACTIVE_QA_FLOCK.lock'):
            lock = (base / name).open('a+b')
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        scope_pins = {}
        for declaration in scope['text_code_pins'] + scope['prior_data_pins']:
            require(declaration['path'] not in scope_pins, 'Duplicate scope text/code pin')
            scope_pins[declaration['path']] = declaration
            loaded(confined(root, declaration['path']), declaration)
        require(scope_pins[BASE + '/driver.py']['sha256'] == go['driver_sha256']
                and scope_pins[BASE + '/qa_saved.py']['sha256'] == args.qa_sha256,
                'Frozen producer/QA scope pins differ')
        for name, sha in ORIGINAL_PINS.items():
            require(name in scope_pins and pins[name]['sha256'] == sha, 'Immutable source/reader metadata differs: ' + name)
        require(PREVIOUS_QA in scope_pins, 'Independent original burst QA receipt must be frozen')
        previous_qa = metadata(root / PREVIOUS_QA)
        require(previous_qa['status'] == 'PASS288_BURST4_MAPS1161_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN'
                and previous_qa['counts']['score_audit_queries'] == 1161
                and previous_qa['counts']['source_decoded_rows'] == 144
                and previous_qa['primary_scope_sha256'] == pins[PREVIOUS + '/scope.json']['sha256']
                and previous_qa['qa_sha256'] == pins['analysis/burst4_20261011_qa/qa_saved.py']['sha256'],
                'Previous burst source/query QA is incomplete')
        require(set(scope['jobs']) == set(JOBS), 'Exactly three fixed OFF jobs required')
        previous_receipts, previous_queries, primary_receipts = {}, {}, {}
        scientific_groups, selected_top3, expected_job_counts = {}, {}, {}
        go_pin = {'path': BASE + '/ROOT_GO.json', **pins[BASE + '/ROOT_GO.json']}
        for job, (scan, target) in JOBS.items():
            declaration = scope['jobs'][job]
            require(declaration['primary_id'] == job and declaration['scan_id'] == scan
                    and declaration['primary_target'] == target, 'Frozen original primary identity differs')
            previous = metadata(confined(root, declaration['primary_receipt']['path']), declaration=declaration['primary_receipt'])
            require(declaration['primary_receipt']['path'] == PREVIOUS + '/results/' + job + '/EXECUTION_RECEIPT.json'
                    and previous['status'] == 'COMPLETE_96_NEW_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
                    and previous['primary_id'] == job and previous['scan_id'] == scan
                    and previous['counts']['score_audit_queries'] == 387
                    and previous['runtime_versions'] == declaration['prior_runtime_versions'],
                    'Original COMPLETE burst receipt differs')
            require(previous_qa['primary_receipt_sha256s'][job] == declaration['primary_receipt']['sha256'],
                    'Original independent burst QA receipt binding differs')
            old_pins = {item['path']: item for item in previous['output_byte_pins']}
            audit_name = PREVIOUS + '/results/' + job + '/SCORE_AUDITS.json'
            top3_name = PREVIOUS + '/results/' + job + '/TOP3.json'
            audits = metadata(confined(root, audit_name), declaration=old_pins[audit_name])
            top3 = metadata(confined(root, top3_name), declaration=old_pins[top3_name])
            require(audits['schema'] == 'SETI_BURST4_SCORE_AUDITS_V1'
                    and audits['primary_id'] == job and audits['scan_id'] == scan
                    and len(audits['records']) == 387 and audits['records'] == declaration['queries']
                    and top3['schema'] == 'SETI_BURST4_TARGET_GLOBAL_RANKS_V1'
                    and top3['records'] == declaration['TOP3'] and len(top3['records']) == 3,
                    'Scope query/anchor list differs from original closed outputs')
            coverage, global_ranks, grouped = set(), set(), {}
            for query in audits['records']:
                selected = query['selected_tuple']
                domain = selected['native_chunk_index'], selected['core_q']
                require(domain in DOMAINS and selected['primary_id'] == job and selected['scan_id'] == scan
                        and selected['primary_target'] == target and selected['original_acquisition_role'] == 'OFF'
                        and selected['window_length_rows'] == ROWS
                        and selected['window_start_row'] in (0, 2, 4, 6, 8, 10, 12)
                        and selected['window_source_rows'] == list(range(selected['window_start_row'], selected['window_start_row'] + ROWS))
                        and selected['width_channels'] in (1, 3)
                        and type(selected['drift_grid_index']) is int and 0 <= selected['drift_grid_index'] < 159,
                        'Inherited fixed tuple differs')
                tuple_key = tuple(selected[field] for field in KEY_FIELDS)
                grouped.setdefault(tuple_key, []).append(query['query_id'])
                kind = query['query_kind']
                if kind == 'global_top3':
                    rank = selected['rank']
                    require(rank in (1, 2, 3) and rank not in global_ranks
                            and selected == top3['records'][rank - 1], 'Inherited TOP3 anchor differs')
                    global_ranks.add(rank)
                    expected_id = 'global_top%02d' % rank
                else:
                    require(kind in ('first', 'midpoint', 'last', 'core_max'), 'Inherited query kind differs')
                    key = domain + (kind,)
                    require(key not in coverage, 'Duplicate inherited core query')
                    coverage.add(key)
                    expected_id = 'native%d_q%03d_%s' % (domain[0], domain[1], kind)
                    if kind in ('first', 'midpoint', 'last'):
                        require(selected['carrier_index_in_core'] == {'first': 0, 'midpoint': 2048, 'last': 4095}[kind],
                                'Fixed audit carrier index differs')
                require(query['query_id'] == expected_id and query['map_id'] == selected['map_id']
                        and query['normalization'] == old_pins[query['normalization']['path']]
                        and query['capsule'] == old_pins[query['capsule']['path']], 'Inherited query byte pins differ')
            require(coverage == {(n, q, kind) for n, q in DOMAINS for kind in ('first', 'midpoint', 'last', 'core_max')}
                    and global_ranks == {1, 2, 3}, 'Closed query matrix incomplete')
            expected_groups = [{'scientific_tuple_key': list(key), 'query_ids': identifiers}
                               for key, identifiers in grouped.items()]
            require(declaration['scientific_tuple_groups'] == expected_groups, 'Independent scientific-tuple grouping differs')
            job_counts = {**PER_JOB, 'unique_scientific_tuples': len(grouped),
                          'duplicate_scientific_tuple_occurrences': 387 - len(grouped)}
            receipt_path = base / 'results' / job / 'EXECUTION_RECEIPT.json'
            receipt = metadata(receipt_path)
            require(receipt['status'] == 'COMPLETE_387_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
                    and receipt['primary_id'] == job and receipt['scan_id'] == scan
                    and receipt['scope_sha256'] == args.scope_sha256
                    and receipt['driver_sha256'] == go['driver_sha256']
                    and receipt['root_GO_pin'] == go_pin and receipt['counts'] == job_counts
                    and 0 < receipt['process_CPU_seconds'] <= CPU_CAP
                    and 0 < receipt['wall_seconds'] <= WALL_CAP
                    and 0 < receipt['peak_RSS_bytes'] <= RAM_CAP
                    and receipt['new_telescope_HTTP_requests'] == 0
                    and receipt['new_grid_or_normalization_estimation'] is False
                    and receipt['permutation_p_value'] is False and receipt['qualified_SETI_detection'] is False
                    and all(receipt.get(key) == value for key, value in CAPS.items()),
                    'Closed temporal-order receipt/counts/resources differ')
            require(receipt['runtime_versions'] == declaration['prior_runtime_versions'], 'Producer/prior burst runtime differs')
            previous_receipts[job], previous_queries[job], primary_receipts[job] = previous, audits['records'], receipt
            selected_top3[job] = top3['records']
            scientific_groups[job] = grouped
            expected_job_counts[job] = job_counts
        original, adjacent = metadata(root / MIDPOINT), metadata(root / ADJACENT)
        acquisitions = {171: metadata(root / ACQ171), 170: metadata(root / ACQ_ADJACENT)}
        acquisitions[172] = acquisitions[170]
        sources, source_records = {}, []
        for scan, target in JOBS.values():
            original_identity = next(item for item in original['sources'] if item['label'] == scan)
            header = original_identity['current_header']['data_attributes']
            require(original_identity['role'] == 'off' and header['source_name'] == target
                    and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP,
                    'Original OFF source coordinate identity differs')
            for native in NATIVES:
                identities = original['sources'] if native == 171 else adjacent['by_native_chunk'][str(native)]['sources']
                identity = next(item for item in identities if item['label'] == scan)
                require(identity['role'] == 'off' and identity['current_header'] == original_identity['current_header']
                        and identity['url'] == original_identity['url'] and identity['etag'] == original_identity['etag'],
                        'Native joins use different immutable observations')
                record = next(item for item in acquisitions[native]['decoded_files'] if item['scan_id'] == scan
                              and (native == 171 or item['native_chunk_index'] == native))
                require(record['shape'] == [16, 1, CHUNK] and record['source_channel0'] == native * CHUNK
                        and [item['time_row'] for item in record['decoded_rows']] == list(range(16))
                        and all(item['decoded_bytes'] == CHUNK * 4 for item in record['decoded_rows']),
                        'Original source shape/decoded rows differ')
                prefix = Path(ACQ171 if native == 171 else ACQ_ADJACENT).parent
                source = {'native_chunk_index': native, 'scan_id': scan, 'primary_target': target,
                          'original_acquisition_role': 'OFF', 'path': (prefix / record['array_file']).as_posix(),
                          'bytes': record['bytes'], 'sha256': record['file_sha256'],
                          'source_channel0': record['source_channel0'], 'shape': record['shape'],
                          'decoded_rows': record['decoded_rows'], 'original_header': header,
                          'original_source_url': identity['url'], 'original_source_etag': identity['etag']}
                source_records.append(source)
                sources[native, scan] = source
        require(scope['source_compacts'] == source_records and len(sources) == 9, 'Frozen nine source declarations differ')
        for job, (scan, target) in JOBS.items():
            own = [sources[native, scan] for native in NATIVES]
            expected_pins = [{key: source[key] for key in ('path', 'bytes', 'sha256')} for source in own]
            require(primary_receipts[job]['source_compact_pre_and_post_pins'] == expected_pins
                    and primary_receipts[job]['decoded_source_row_checks'] == [
                        {'source': pin, 'decoded_rows': source['decoded_rows'], 'rows_verified': 16}
                        for pin, source in zip(expected_pins, own)], 'Producer source/decoded-row receipt evidence differs')
        # No numerical imports occur until every metadata and terminal receipt is admitted.
        global np
        import numpy as np
        spec = importlib.util.spec_from_file_location('burst_order_independent_reader', root / READER)
        reader = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reader
        spec.loader.exec_module(reader)
        h5py, _, _ = reader.current_codecs()
        runtime = {'Python': sys.version.split()[0],
                   **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin')},
                   'HDF5': h5py.version.hdf5_version}
        require(all(receipt['runtime_versions'] == runtime for receipt in primary_receipts.values()),
                'Independent QA numerical runtime differs from producer')
        powers = {}
        for key, source in sources.items():
            path = confined(root, source['path'])
            stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb')
            stat = os.fstat(stream.fileno())
            source_handles.append((path, stream, stat))
            value = hashlib.sha256()
            for block in iter(lambda: stream.read(1048576), b''):
                value.update(block)
            require(stat.st_size == source['bytes'] and value.hexdigest() == source['sha256'], 'Whole compact source SHA differs')
            pins[source['path']] = {field: source[field] for field in ('bytes', 'sha256')}
            stream.seek(0)
            with h5py.File(stream, 'r', rdcc_nbytes=0) as handle:
                data = handle['data']
                require(data.shape == (16, 1, CHUNK) and data.dtype == np.dtype('<f4')
                        and int(data.attrs['original_source_frequency_chunk_origin']) == source['source_channel0']
                        and data.attrs['original_source_url'] == source['original_source_url']
                        and data.attrs['original_source_etag'] == source['original_source_etag'], 'Decoded H5 source identity differs')
                power = data[:, 0, :]
            require(np.isfinite(power).all() and (power >= 0).all(), 'Decoded source power is invalid')
            for row in source['decoded_rows']:
                require(hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'],
                        'Authenticated decoded-row SHA differs')
                counts['source_decoded_rows'] += 1
            counts['source_files'] += 1
            powers[key] = power
        create_json(admission_path, {'status': 'ADMITTED_NINE_SOURCES_AND_THREE_COMPLETE_FIXED_QUERY_RECEIPTS',
                    'scope_sha256': args.scope_sha256, 'qa_sha256': args.qa_sha256,
                    'root_go_sha256': args.root_go_sha256, 'source_files': 9, 'source_decoded_rows': 144,
                    'producer_receipt_pins': [
                        {'path': BASE + '/results/' + job + '/EXECUTION_RECEIPT.json',
                         **pins[BASE + '/results/' + job + '/EXECUTION_RECEIPT.json']} for job in JOBS],
                    'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL}})
        output_created = True
        statistics_summaries = {}
        for job, (scan, target) in JOBS.items():
            output = base / 'results' / job
            receipt = primary_receipts[job]
            output_pins = {item['path']: item for item in receipt['output_byte_pins']}
            require(len(output_pins) == len(receipt['output_byte_pins']) == 388, 'Closed producer output pin count differs')
            diagnostic_name = BASE + '/results/' + job + '/QUERY_DIAGNOSTICS.json'
            diagnostic = metadata(confined(root, diagnostic_name), declaration=output_pins[diagnostic_name])
            require(diagnostic['schema'] == 'SETI_BURST4_TEMPORAL_ORDER_DIAGNOSTICS_V1'
                    and diagnostic['primary_id'] == job and diagnostic['scan_id'] == scan
                    and diagnostic['primary_target'] == target and diagnostic['counts'] == expected_job_counts[job]
                    and diagnostic['status'] == 'COMPLETE_387_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
                    and diagnostic['selected_winner_diagnostic_only'] is True
                    and diagnostic['permutation_p_value'] is False
                    and diagnostic['normalization_conditioned_on_saved_full16_parameters'] is True
                    and len(diagnostic['records']) == 387, 'Saved diagnostic inventory differs')
            joined = np.concatenate([powers[native, scan] for native in NATIVES], axis=1)
            normalization_cache, summaries = {}, []
            for saved, query in zip(diagnostic['records'], previous_queries[job]):
                require(set(saved) == DIAGNOSTIC_FIELDS and saved['query_id'] == query['query_id']
                        and saved['query_kind'] == query['query_kind'] and saved['selected_tuple'] == query['selected_tuple']
                        and saved['prior_normalization'] == query['normalization']
                        and saved['prior_capsule'] == query['capsule'], 'Fixed diagnostic query or inherited pins differ')
                selected = query['selected_tuple']
                scientific_key = tuple(selected[field] for field in KEY_FIELDS)
                require(saved['scientific_tuple_key'] == list(scientific_key)
                        and saved['scientific_tuple_multiplicity'] == len(scientific_groups[job][scientific_key]),
                        'Saved scientific tuple key/multiplicity differs')
                width, r0 = selected['width_channels'], selected['window_start_row']
                physical_rows = np.arange(r0, r0 + ROWS, dtype=np.int64)
                times = np.arange(ROWS) * TSAMP
                centers = np.rint((selected['frequency_hz_at_window_reference'] - FCH1) / DF
                                  + selected['drift_hz_s'] * times / DF).astype(np.int64)
                channel0, channel_count = int(centers.min()) - 251, int(centers.max() - centers.min()) + 503
                equal(saved['centers'], centers, 'Saved rounded fixed centers differ')
                equal(saved['source_rows'], physical_rows, 'Saved physical source rows differ')
                require(saved['raw_source_channel0'] == channel0 and saved['raw_channel_count'] == channel_count,
                        'Minimal common raw envelope differs')
                require(channel0 >= 170 * CHUNK and channel0 + channel_count <= 173 * CHUNK,
                        'Common raw envelope leaves immutable source triplet')
                require(selected['source_reference_channel'] == selected['native_chunk_index'] * CHUNK
                        + selected['core_q'] * CORE + selected['carrier_index_in_core']
                        and selected['frequency_hz_at_window_reference'] == FCH1 + DF * selected['source_reference_channel']
                        and selected['reference_time_mjd'] == sources[171, scan]['original_header']['tstart'] + (r0 + .5) * TSAMP / 86400,
                        'Inherited physical carrier/window reference differs')
                normalization_name = query['normalization']['path']
                if normalization_name not in normalization_cache:
                    normalization = metadata(confined(root, normalization_name), declaration=query['normalization'])
                    require(set(normalization) == NORM_FIELDS, 'Conditional normalization fields differ')
                    first = selected['native_chunk_index'] * CHUNK + selected['core_q'] * CORE
                    equal(normalization['normalization_source_channel_interval_half_open'], [first, first + CORE],
                          'Conditional normalization core domain differs')
                    equal(normalization['normalization_unmasked_counts'], np.full(16, CORE), 'Conditional normalization masks differ')
                    for name in NORM_FIELDS - {'normalization_source_channel_interval_half_open', 'normalization_unmasked_counts'}:
                        values = np.asarray(normalization[name])
                        require(values.shape == (16,) and np.isfinite(values).all(), 'Invalid16 normalization terms')
                    require((np.asarray(normalization['row_power_median']) > 0).all()
                            and (np.asarray(normalization['row_residual_MAD_scale']) > 0).all(), 'Conditional normalization scales are nonpositive')
                    start = first - 170 * CHUNK
                    equal(np.median(joined[:, start:start + CORE].astype(np.float64), axis=1),
                          normalization['row_power_median'], 'Independent full4096 raw row median differs')
                    normalization_cache[normalization_name] = normalization
                    normalized_cores += 1
                    core_row_medians += 16
                normalization = normalization_cache[normalization_name]
                capsule_pin = saved['new_capsule']
                expected_capsule_name = BASE + '/results/' + job + '/' + query['query_id'] + '_order.npz'
                require(capsule_pin['path'] == expected_capsule_name and capsule_pin == output_pins[expected_capsule_name],
                        'New query capsule closed byte pin differs')
                require(0 < capsule_pin['bytes'] <= 20 * 1024, 'New query capsule size exceeds frozen bound')
                capsule = archive(capsule_pin)
                schema = {'raw_power': ('<f4', (ROWS, channel_count)),
                          'absolute_time_rows': ('<i8', (ROWS,)), 'rounded_absolute_centers': ('<i8', (ROWS,)),
                          'standardized_row_center_box_sums': ('<f8', (ROWS, ROWS)),
                          'permutation_scores': ('<f8', (24,)), 'permutation_indices': ('<i2', (24, ROWS))}
                require(set(capsule) == set(schema), 'Common-envelope capsule fields differ')
                for name, (dtype, shape) in schema.items():
                    require(capsule[name].dtype == np.dtype(dtype) and capsule[name].shape == shape
                            and np.isfinite(capsule[name]).all(), 'Common-envelope capsule dtype/shape/finite differs: ' + name)
                equal(capsule['absolute_time_rows'], physical_rows, 'Capsule physical rows differ')
                equal(capsule['rounded_absolute_centers'], centers, 'Capsule fixed center sequence differs')
                equal(capsule['permutation_indices'], PERMUTATIONS, 'Capsule lexicographic24 assignments differ')
                raw = joined[physical_rows[:, None], channel0 - 170 * CHUNK + np.arange(channel_count)[None, :]]
                equal(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Common raw-envelope source bits differ')
                old = archive(query['capsule'])
                old_schema = {'raw_power': ('<f4', (ROWS, 503)), 'absolute_time_rows': ('<i8', (ROWS,)),
                              'rounded_absolute_centers': ('<i8', (ROWS,)), 'standardized_row_box_sums': ('<f8', (ROWS,))}
                require(set(old) == set(old_schema), 'Original raw4x503 capsule fields differ')
                for name, (dtype, shape) in old_schema.items():
                    require(old[name].dtype == np.dtype(dtype) and old[name].shape == shape
                            and np.isfinite(old[name]).all(), 'Original raw4x503 capsule dtype/shape differs')
                equal(old['absolute_time_rows'], physical_rows, 'Original capsule physical rows differ')
                equal(old['rounded_absolute_centers'], centers, 'Original capsule fixed center sequence differs')
                for row in range(ROWS):
                    begin = int(centers[row]) - channel0 - 251
                    equal(raw[row, begin:begin + 503].view(np.uint32), old['raw_power'][row].view(np.uint32),
                          'Original raw4x503 row differs from common envelope')
                matrix = independent_matrix(raw, channel0, centers, physical_rows, normalization, width)
                near(capsule['standardized_row_center_box_sums'], matrix, 'Independent local501 row-center arithmetic differs')
                equal(saved['matrix'], capsule['standardized_row_center_box_sums'], 'JSON/NPZ saved row-center matrix differs')
                near(old['standardized_row_box_sums'], np.diag(matrix), 'Identity diagonal differs from original row-box sums')
                raw_scores = np.asarray([(((matrix[0, permutation[0]] + matrix[1, permutation[1]])
                                          + matrix[2, permutation[2]]) + matrix[3, permutation[3]])
                                         / np.sqrt(ROWS * width) for permutation in PERMUTATIONS], dtype=np.float64)
                near(capsule['permutation_scores'], raw_scores, 'Independent raw-matrix24 permutation scores differ')
                near(raw_scores[0], selected['score'], 'Independent raw-matrix identity differs from original frozen tuple')
                stats = independent_statistics(capsule['standardized_row_center_box_sums'], centers, width)
                equal(capsule['permutation_scores'], stats['permutation_scores'], 'Exact24 saved-matrix permutation scores differ')
                near(stats['identity_score'], selected['score'], 'Identity score differs from original frozen tuple')
                require(saved['prior_primary_score'] == selected['score']
                        and saved['identity_minus_prior_primary_score'] == stats['identity_score'] - selected['score']
                        and saved['zero_drift'] == (selected['drift_hz_s'] == 0)
                        and saved['diagnostic_degenerate'] == (stats['distinct_assignment_count'] == 1)
                        and saved['rounded_nonzero_drift_degenerate'] == (selected['drift_hz_s'] != 0 and stats['distinct_assignment_count'] == 1),
                        'Identity score difference or degeneracy flags differ')
                for name, expected in stats.items():
                    require(saved[name] == expected, 'Exact saved-matrix assignment/score/rank/tie differs: ' + name)
                max_matrix_difference = max(max_matrix_difference, float(np.max(np.abs(matrix - capsule['standardized_row_center_box_sums']))))
                max_permutation_difference = max(max_permutation_difference, float(np.max(np.abs(capsule['permutation_scores'] - raw_scores))))
                max_identity_difference = max(max_identity_difference, abs(stats['identity_score'] - selected['score']))
                counts['queries'] += 1
                counts['row_center_boxes'] += ROWS * ROWS
                counts['permutation_scores'] += len(PERMUTATIONS)
                if query['query_kind'] == 'global_top3':
                    counts['global_TOP3_queries'] += 1
                    summaries.append({'query_id': query['query_id'], 'selected_tuple': selected,
                                      'scientific_tuple_key': saved['scientific_tuple_key'],
                                      'scientific_tuple_multiplicity': saved['scientific_tuple_multiplicity'],
                                      'prior_primary_score': saved['prior_primary_score'],
                                      'identity_minus_prior_primary_score': saved['identity_minus_prior_primary_score'],
                                      'zero_drift': saved['zero_drift'],
                                      'diagnostic_degenerate': saved['diagnostic_degenerate'],
                                      'rounded_nonzero_drift_degenerate': saved['rounded_nonzero_drift_degenerate'],
                                      **{name: stats[name] for name in stats if name not in {
                                          'permutation_scores', 'permutation_center_vectors', 'distinct_center_vectors',
                                          'distinct_representative_permutation_indices', 'distinct_scores',
                                          'distinct_assignment_multiplicities'}}})
            require(len(normalization_cache) == 96 and len(summaries) == 3, 'Per-target normalizations/TOP3 anchors incomplete')
            statistics_summaries[job] = summaries
            observed = {name for name in pins if name.startswith(BASE + '/results/' + job + '/')
                        and not name.endswith('/EXECUTION_RECEIPT.json')}
            require(observed == set(output_pins), 'Checked producer output inventory differs from receipt')
            actual = {path.relative_to(root).as_posix() for path in output.rglob('*') if path.is_file()}
            require(actual == set(output_pins) | {BASE + '/results/' + job + '/EXECUTION_RECEIPT.json'},
                    'Producer output directory has unexpected/absent files')
            for name, declaration in output_pins.items():
                require(pins[name] == {key: declaration[key] for key in ('bytes', 'sha256')}, 'Closed producer output pin differs')
            del joined
            print('PASS_FIXED_TEMPORAL_ORDER_TARGET', job, flush=True)
        require(counts == EXPECTED and normalized_cores == 288 and core_row_medians == 4608,
                'Independent fixed-query arithmetic/source counts incomplete')
        counts['unique_scientific_tuples'] = sum(item['unique_scientific_tuples'] for item in expected_job_counts.values())
        counts['duplicate_scientific_tuple_occurrences'] = sum(item['duplicate_scientific_tuple_occurrences'] for item in expected_job_counts.values())
        for path, stream, before in source_handles:
            after, current = os.fstat(stream.fileno()), path.stat(follow_symlinks=False)
            require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) ==
                    (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    and (current.st_dev, current.st_ino) == (before.st_dev, before.st_ino), 'Retained source descriptor/path changed')
        for name, declaration in pins.items():
            path = confined(root, name)
            require(path.stat().st_size == declaration['bytes'] and digest(path) == declaration['sha256'],
                    'Input changed during independent QA: ' + name)
        usage = {'process_CPU_seconds': time.process_time() - cpu_started, 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP
                and 0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Independent QA resource bound exceeded')
        receipt = {'schema': 'SETI_BURST4_TEMPORAL_ORDER_INDEPENDENT_QA_V1',
                   'status': 'PASS_1161_FIXED_TEMPORAL_ORDER_QUERIES18576_ROW_CENTER_BOXES27864_PERMUTATION_SCORES9_TOP3',
                   'counts': counts, 'scope_sha256': args.scope_sha256, 'qa_sha256': args.qa_sha256,
                   'driver_sha256': go['driver_sha256'], 'root_go_sha256': args.root_go_sha256,
                   'root_GO_pin': go_pin,
                   'job_receipt_sha256s': {job: pins[BASE + '/results/' + job + '/EXECUTION_RECEIPT.json']['sha256']
                                          for job in JOBS},
                   'producer_receipt_pins': [
                       {'path': BASE + '/results/' + job + '/EXECUTION_RECEIPT.json',
                        **pins[BASE + '/results/' + job + '/EXECUTION_RECEIPT.json']} for job in JOBS],
                   'before_and_after_input_pins': pins, 'input_byte_pins': pins, 'runtime_versions': runtime,
                   'global_TOP3_statistics': statistics_summaries, 'selected_top3': selected_top3,
                   'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
                   'maximum_matrix_absolute_difference': max_matrix_difference,
                   'maximum_permutation_score_absolute_difference': max_permutation_difference,
                   'maximum_identity_vs_original_score_absolute_difference': max_identity_difference,
                   'raw_core_row_medians_independently_recomputed': core_row_medians,
                   'normalization_records_authenticated': normalized_cores,
                   'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
                   'output_cap_bytes': QA_OUTPUT_CAP, **usage, **CAPS,
                   'detector_imported': False, 'producer_imported': False, 'full_search_grid_recomputed': False,
                   'full_core_MAD_location_independently_refiltered': False,
                   'normalization_conditional_on_saved_full16_core_terms': True,
                   'physical_row_normalization_reassigned': False,
                   'new_telescope_HTTP_requests': 0, 'qualified_SETI_detection': False,
                   'calibrated_SNR_FAP': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
                   'limitations': ['These are descriptive fixed-tuple order diagnostics on exposed, previously selected winners.',
                                   'Identity ordering and competing assignments use the same fixed physical source rows and saved full16 normalization.',
                                   'Distinct center assignments are deduplicated by actual rounded center vector, retaining the first lexicographic permutation.',
                                   'Exact saved-matrix ranks and ties are descriptive, not calibrated p-values or false-alarm probabilities.',
                                   'Fullcore MAD/location is not independently refiltered, and no search grid is rerun.']}
        create_json(qa_path, receipt)
        require(qa_path.stat().st_size + admission_path.stat().st_size <= QA_OUTPUT_CAP, 'Combined independent QA output cap exceeded')
        print(receipt['status'], flush=True)
    except BaseException as error:
        if output_created and not qa_path.exists() and not failure_path.exists():
            create_json(failure_path, {'status': 'FAIL_INDEPENDENT_FIXED_TEMPORAL_ORDER_QA',
                        'error_type': type(error).__name__, 'message': str(error), 'partial_counts': counts,
                        'wall_seconds': time.monotonic() - started, 'producer_imported': False, 'detector_imported': False})
        raise
    finally:
        signal.alarm(0)
        for lock in locks:
            lock.close()
        for path, stream, stat in source_handles:
            stream.close()


if __name__ == '__main__':
    main()
