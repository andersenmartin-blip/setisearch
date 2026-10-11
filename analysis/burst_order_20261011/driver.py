"""Fixed saved-tuple temporal-order diagnostic; no science at import/check-only.

Physical rows and their saved full16 normalization remain fixed. Only the four
saved integer track centers are reassigned. This selected-winner diagnostic is
not a new detector grid, permutation p-value, or independent observation.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'analysis/burst_order_20261011'
PRIOR = 'analysis/burst4_20261011'
PRIOR_QA = 'analysis/burst4_20261011_qa/results/QA_RECEIPT.json'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
COUNT, CORE, C0 = 1048576, 4096, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
JOBS = {'primary20170428_HIP97319': ('epoch1_off', 'HIP97319'),
        'primary20170428_HIP97461': ('epoch2_off', 'HIP97461'),
        'primary20170428_HIP97663': ('epoch3_off', 'HIP97663')}
CAPS = {'CPU_cap_s_per_job': 600, 'wall_cap_s_per_job': 900,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'max_simultaneous_jobs': 2,
        'memory_cap_bytes_aggregate': 4 * 1024**3,
        'job_output_budget_bytes': 50 * 1024**2,
        'total_output_budget_bytes': 150 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3}
COUNTS = {'queries': 387, 'global_TOP3_queries': 3, 'row_center_boxes': 6192,
          'permutation_scores': 9288, 'source_files': 3, 'source_decoded_rows': 48}
STATUS = 'COMPLETE_387_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
GO_STATUS = 'GO_1161_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
ATOL, RTOL = 1e-7, 1e-10


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Confined relative project path required')
    return path


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def method():
    return {'schema': 'SETI_BURST4_TEMPORAL_ORDER_SCOPE_V1', 'queries_per_target': 387,
            'total_queries': 1161, 'global_TOP3_queries': 9, 'physical_rows_per_query': 4,
            'center_assignments_per_query': 24, 'permutation_order': 'lexicographic permutations of (0,1,2,3)',
            'permutation_definition': 'physical row i samples original center indexed permutation[i]',
            'distinct_assignment_definition': 'deduplicate actual integer center vectors; first lexicographic representative',
            'score_denominator': 'sqrt(4*winning_width_channels)',
            'exact_rank_definition': 'best=1+number of greater distinct scores; worst=greater+exact_equal',
            'exact_score_accumulation': '((M[0,pi0]+M[1,pi1])+M[2,pi2])+M[3,pi3], then divide sqrt(4*width)',
            'rank_tie_epsilon': 0,
            'wrong_order_definition': 'distinct center vectors excluding identity vector; undefined when only identity remains',
            'raw_capsule_definition': 'physical rows r0:r0+4, all channels min(center)-251 through max(center)+251 inclusive',
            'normalization': 'saved full16 physical-row power median, winsorized residual location and MAD; no estimation',
            'running_median_channels': 501, 'source_channel_rounding': 'np.rint(full absolute carrier+drift mapping)',
            'identity_score_ATOL': ATOL, 'identity_score_RTOL': RTOL,
            'capsule_budget_bytes': 20 * 1024, 'new_detector_grid': False,
            'new_normalization_estimation': False, 'new_observation': False, 'mask_or_veto': False,
            'calibrated_SNR_FAP_or_permutation_p_value': False,
            'scientific_tuple_key_fields': ['scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
                                            'window_start_row', 'drift_grid_index', 'width_channels'],
            'expected_counts_per_target': COUNTS, **CAPS}


def contract(root, scope):
    require(all(scope.get(k) == v for k, v in method().items()), 'Prospective scientific/resource contract differs')
    pins = {}
    for record in scope['text_code_pins'] + scope['prior_data_pins']:
        path = confined(root, record['path'])
        require(pin(root, path) == record, 'Authenticated code/prior input differs: ' + record['path'])
        pins[record['path']] = record
    require(pins.get(BASE + '/driver.py', {}).get('sha256') == digest(Path(__file__).resolve()), 'Driver self pin differs')
    require(read(root / PRIOR_QA)['status'] == 'PASS288_BURST4_MAPS1161_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN',
            'Previous saved-output QA must be PASS288')
    require(set(scope['jobs']) == set(JOBS) and len(scope['source_compacts']) == 9, 'Three immutable OFF-primary jobs required')
    for job, (scan, target) in JOBS.items():
        item = scope['jobs'][job]
        require(item['primary_id'] == job and item['scan_id'] == scan and item['primary_target'] == target
                and len(item['queries']) == 387 and len(item['TOP3']) == 3, 'Saved query admission differs')
        require(read(root / item['primary_receipt']['path'])['status'] ==
                'COMPLETE_96_NEW_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY', 'Original primary is incomplete')
        require(len({q['query_id'] for q in item['queries']}) == 387, 'Duplicate saved query identifier')
        require({kind: sum(q['query_kind'] == kind for q in item['queries']) for kind in
                 ('first', 'midpoint', 'last', 'core_max', 'global_top3')} ==
                {'first': 96, 'midpoint': 96, 'last': 96, 'core_max': 96, 'global_top3': 3},
                'Exact fixed-query strata differ')
        require([q['selected_tuple'] for q in item['queries'] if q['query_kind'] == 'global_top3'] == item['TOP3'],
                'Nine global TOP3 anchors differ')
        require(sum(len(group['query_ids']) for group in item['scientific_tuple_groups']) == 387,
                'Scientific tuple occurrence grouping differs')
        for query in item['queries']:
            chosen = query['selected_tuple']
            r0, native, q = (chosen[k] for k in ('window_start_row', 'native_chunk_index', 'core_q'))
            require(chosen['primary_id'] == job and chosen['scan_id'] == scan and chosen['primary_target'] == target
                    and chosen['original_acquisition_role'] == 'OFF' and native in (170, 171, 172)
                    and q in range(4, 253, 8) and r0 in range(0, 13, 2)
                    and chosen['window_length_rows'] == 4 and chosen['window_source_rows'] == list(range(r0, r0 + 4))
                    and chosen['width_channels'] in (1, 3) and math.isfinite(chosen['score']), 'Saved tuple outside frozen pilot')
            require(pins.get(query['normalization']['path']) == query['normalization']
                    and pins.get(query['capsule']['path']) == query['capsule'], 'Saved query anchors not pinned')


def workspace_bytes(root):
    seen, total = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                stat = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            key = stat.st_dev, stat.st_ino
            if key not in seen:
                seen.add(key)
                total += stat.st_blocks * 512
    return total


def versions(h5py):
    return {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
            **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}}


def run(root, scope, job, out):
    import numpy as np
    import h5py
    import hdf5plugin
    from scipy.ndimage import median_filter
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008), 'Original bitshuffle decoder required')
    item = scope['jobs'][job]
    runtime = versions(h5py)
    require(runtime == item['prior_runtime_versions'], 'Actual runtime differs from the authenticated primary')
    source_records = [r for r in scope['source_compacts'] if r['scan_id'] == item['scan_id']]
    require([r['native_chunk_index'] for r in source_records] == [170, 171, 172], 'Contiguous OFF source triplet required')
    power = np.empty((16, 3 * COUNT), dtype='<f4')
    source_pins, row_checks = [], []
    for record in source_records:
        path = confined(root, record['path'])
        actual = pin(root, path)
        require(actual == {k: record[k] for k in ('path', 'bytes', 'sha256')}, 'Original compact source bytes differ')
        source_pins.append(actual)
        offset = record['source_channel0'] - C0
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin']) == record['source_channel0']
                    and data.attrs['original_source_url'] == record['original_source_url']
                    and data.attrs['original_source_etag'] == record['original_source_etag'], 'Original H5 provenance differs')
            for row in record['decoded_rows']:
                values = data[row['time_row'], 0, :]
                require(np.isfinite(values).all() and (values >= 0).all()
                        and hashlib.sha256(values.tobytes()).hexdigest() == row['decoded_sha256'], 'Original float32 source row differs')
                power[row['time_row'], offset:offset + COUNT] = values
        row_checks.append({'source': actual, 'decoded_rows': record['decoded_rows'], 'rows_verified': 16})
    permutations = np.asarray(list(itertools.permutations(range(4))), dtype='<i2')
    records = []
    for query in item['queries']:
        chosen = query['selected_tuple']
        width, r0 = chosen['width_channels'], chosen['window_start_row']
        source_rows = np.arange(r0, r0 + 4, dtype='<i8')
        times = np.arange(4) * TSAMP
        centers = np.rint((chosen['frequency_hz_at_window_reference'] - FCH1) / DF
                          + chosen['drift_hz_s'] * times / DF).astype('<i8')
        first, stop = int(centers.min()) - 251, int(centers.max()) + 252
        require(C0 <= first < stop <= C0 + 3 * COUNT, 'Cross-center503 support leaves original triplet')
        raw = power[source_rows, first - C0:stop - C0].copy()
        norm = read(root / query['normalization']['path'])
        core0 = chosen['native_chunk_index'] * COUNT + chosen['core_q'] * CORE
        require(norm['normalization_source_channel_interval_half_open'] == [core0, core0 + CORE]
                and norm['normalization_unmasked_counts'] == [CORE] * 16, 'Saved full16 normalization core differs')
        level, location, scale = (np.asarray(norm[key], dtype=np.float64) for key in
                                 ('row_power_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'))
        require(all(a.shape == (16,) and np.isfinite(a).all() for a in (level, location, scale))
                and (level > 0).all() and (scale > 0).all(), 'Invalid saved full16 normalization')
        ratio = raw.astype(np.float64) / level[source_rows, None]
        residual = ratio - median_filter(ratio, size=(1, 501), mode='nearest')
        z = (residual - location[source_rows, None]) / scale[source_rows, None]
        boxcols = centers[:, None] - first + np.arange(-(width // 2), width // 2 + 1)[None, :]
        matrix = z[:, boxcols].sum(axis=2, dtype=np.float64)
        with np.load(root / query['capsule']['path'], allow_pickle=False) as old:
            require(np.array_equal(old['absolute_time_rows'], source_rows)
                    and np.array_equal(old['rounded_absolute_centers'], centers), 'Prior audit geometry differs')
            diagonal_raw = np.stack([raw[i, centers[i] - first - 251:centers[i] - first + 252] for i in range(4)])
            require(np.array_equal(diagonal_raw.view(np.uint32), old['raw_power'].view(np.uint32)), 'Old diagonal raw503 source bits differ')
            require(np.allclose(np.diag(matrix), old['standardized_row_box_sums'], atol=ATOL, rtol=RTOL), 'Identity row boxes differ from prior audit')
        scores = (((matrix[0, permutations[:, 0]] + matrix[1, permutations[:, 1]])
                   + matrix[2, permutations[:, 2]]) + matrix[3, permutations[:, 3]]) / np.sqrt(4 * width)
        identity = float(scores[0])
        require(np.isfinite(matrix).all() and np.isfinite(scores).all()
                and math.isclose(identity, chosen['score'], abs_tol=ATOL, rel_tol=RTOL), 'Identity score differs from saved primary')
        vectors = centers[permutations]
        seen, representatives, multiplicities = {}, [], []
        for index, vector in enumerate(vectors.tolist()):
            key = tuple(vector)
            if key not in seen:
                seen[key] = len(representatives)
                representatives.append(index)
                multiplicities.append(0)
            multiplicities[seen[key]] += 1
        distinct = scores[representatives]
        wrong = distinct[1:]
        greater, equal = int(np.count_nonzero(distinct > identity)), int(np.count_nonzero(distinct == identity))
        capsule_path = out / (query['query_id'] + '_order.npz')
        with capsule_path.open('xb') as stream:
            np.savez(stream, raw_power=raw, absolute_time_rows=source_rows, rounded_absolute_centers=centers,
                     standardized_row_center_box_sums=matrix, permutation_scores=scores, permutation_indices=permutations)
            stream.flush()
            os.fsync(stream.fileno())
        require(capsule_path.stat().st_size <= scope['capsule_budget_bytes'], '20KiB capsule bound exceeded')
        tuple_key = [chosen[field] for field in scope['scientific_tuple_key_fields']]
        tuple_group = next(group for group in item['scientific_tuple_groups'] if group['scientific_tuple_key'] == tuple_key)
        records.append({'query_id': query['query_id'], 'query_kind': query['query_kind'], 'selected_tuple': chosen,
            'scientific_tuple_key': tuple_key, 'scientific_tuple_multiplicity': len(tuple_group['query_ids']),
            'prior_normalization': query['normalization'], 'prior_capsule': query['capsule'], 'new_capsule': pin(root, capsule_path),
            'centers': centers.tolist(), 'source_rows': source_rows.tolist(), 'raw_source_channel0': first,
            'raw_channel_count': stop - first, 'matrix': matrix.tolist(), 'permutation_scores': scores.tolist(),
            'permutation_center_vectors': vectors.tolist(), 'distinct_center_vectors': vectors[representatives].tolist(),
            'distinct_representative_permutation_indices': representatives, 'distinct_scores': distinct.tolist(),
            'distinct_assignment_multiplicities': multiplicities,
            'identity_score': identity, 'distinct_center_count': len(set(centers.tolist())),
            'prior_primary_score': chosen['score'], 'identity_minus_prior_primary_score': identity - chosen['score'],
            'zero_drift': chosen['drift_hz_s'] == 0, 'diagnostic_degenerate': len(representatives) == 1,
            'rounded_nonzero_drift_degenerate': chosen['drift_hz_s'] != 0 and len(representatives) == 1,
            'stationary_centers': len(set(centers.tolist())) == 1, 'duplicate_centers': len(set(centers.tolist())) < 4,
            'distinct_assignment_count': len(representatives), 'wrong_order_distinct_count': len(wrong),
            'wrong_order_max_score': float(wrong.max()) if len(wrong) else None,
            'wrong_order_median_score': float(np.median(wrong)) if len(wrong) else None,
            'identity_minus_wrong_order_max': identity - float(wrong.max()) if len(wrong) else None,
            'identity_minus_wrong_order_median': identity - float(np.median(wrong)) if len(wrong) else None,
            'identity_rank_best': greater + 1, 'identity_rank_worst': greater + equal,
            'identity_exact_tie_count': equal, 'identity_equal_score_wrong_order_count': equal - 1,
            'wrong_order_strictly_better_than_identity_count': greater})
        if len(records) % 32 == 0:
            require(workspace_bytes(root) <= CAPS['workspace_cap_bytes'], '8GiB workspace cap exceeded')
            print(job, len(records), '/387', flush=True)
    require(len(records) == 387 and sum(r['query_kind'] == 'global_top3' for r in records) == 3, '387 queries and3TOP3 anchors required')
    counts = {**COUNTS, 'unique_scientific_tuples': len(item['scientific_tuple_groups']),
              'duplicate_scientific_tuple_occurrences': 387 - len(item['scientific_tuple_groups'])}
    save(out / 'QUERY_DIAGNOSTICS.json', {'schema': 'SETI_BURST4_TEMPORAL_ORDER_DIAGNOSTICS_V1', 'status': STATUS,
          'primary_id': job, 'scan_id': item['scan_id'], 'primary_target': item['primary_target'], 'records': records,
          'counts': counts, 'selected_winner_diagnostic_only': True, 'permutation_p_value': False,
          'normalization_conditioned_on_saved_full16_parameters': True})
    return source_pins, row_checks, runtime, counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--job', choices=JOBS, required=True)
    p.add_argument('--scope', default=BASE + '/scope.json')
    p.add_argument('--scope-sha256')
    p.add_argument('--root-go', default=BASE + '/ROOT_GO.json')
    p.add_argument('--root-go-sha256')
    p.add_argument('--check-only', action='store_true')
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    root = args.root.resolve()
    scope_path = confined(root, args.scope)
    scope = read(scope_path)
    contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_FIXED_TEMPORAL_ORDER_SCOPE', 'scope': pin(root, scope_path),
                          'numerical_modules_imported': False, 'source_arrays_opened': False}))
        return
    require(args.run and args.scope_sha256 == digest(scope_path), 'Root --run with actual prospective scope SHA required')
    go_path = confined(root, args.root_go)
    require(args.root_go_sha256 == digest(go_path), 'Exact root GO hash required')
    go = read(go_path)
    require(go['status'] == GO_STATUS and go['scope_sha256'] == args.scope_sha256
            and go['driver_sha256'] == digest(Path(__file__).resolve())
            and go['qa_sha256'] == digest(root / BASE / 'qa_saved.py')
            and all(go.get(k) == v for k, v in CAPS.items()), 'Root GO contract differs')
    require(workspace_bytes(root) + CAPS['total_output_budget_bytes'] <= CAPS['workspace_cap_bytes'], 'Prospective150MiB output reserve exceeds8GiB workspace')
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_CPU, (600, 601))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('Temporal-order wall cap900s reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(900)
    started, cpu0 = time.monotonic(), time.process_time()
    out = root / BASE / 'results' / args.job
    out.mkdir(parents=True, exist_ok=False)
    try:
        source_pins, rows, runtime, counts = run(root, scope, args.job, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256 and digest(go_path) == args.root_go_sha256,
                'Prospective scope/root GO changed during diagnostic')
        for record in source_pins:
            require(pin(root, root / record['path']) == record, 'Raw compact source changed during diagnostic')
        outputs = [pin(root, path) for path in sorted(out.iterdir()) if path.is_file()]
        require(len(outputs) == 388 and sum(r['bytes'] for r in outputs) <= CAPS['job_output_budget_bytes'], '388outputs/50MiB budget differs')
        cpu, wall, rss = time.process_time() - cpu0, time.monotonic() - started, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        require(cpu <= 600 and wall <= 900 and rss <= 2 * 1024**3, 'Temporal-order resource cap exceeded')
        save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_BURST4_TEMPORAL_ORDER_EXECUTION_V1', 'status': STATUS,
             'primary_id': args.job, 'scan_id': JOBS[args.job][0], 'scope_sha256': args.scope_sha256,
             'driver_sha256': digest(Path(__file__).resolve()), 'root_GO_pin': pin(root, go_path), 'counts': counts,
             'source_compact_pre_and_post_pins': source_pins, 'decoded_source_row_checks': rows,
             'output_byte_pins': outputs, 'runtime_versions': runtime, 'process_CPU_seconds': cpu,
             'wall_seconds': wall, 'peak_RSS_bytes': rss, 'new_telescope_HTTP_requests': 0, 'cost_DKK': 0,
             'new_grid_or_normalization_estimation': False, 'permutation_p_value': False,
             'qualified_SETI_detection': False, **CAPS})
    except BaseException as exc:
        if not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_BURST4_TEMPORAL_ORDER_EXECUTION_V1',
                 'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'primary_id': args.job,
                 'scope_sha256': args.scope_sha256, 'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
