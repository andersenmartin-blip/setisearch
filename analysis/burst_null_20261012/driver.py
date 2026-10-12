"""Eight prospectively seeded engineering Gamma-noise search families.

Import/check-only use metadata. Only root --run after exact scope/GO invokes
model draws. The full previous burst pipeline is preserved, including winner
selection before order controls. No telescope arrays are opened or fitted.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import itertools
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
BASE = 'analysis/burst_null_20261012'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
LEGACY = 'analysis/burst4_20261011/driver.py'
DETECTOR_SHA = '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45'
COUNT, CORE, HALO = 1048576, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DOMAINS = tuple((native, 4 + 8 * k) for native in (170, 171, 172) for k in range(32))
STARTS = (0, 2, 4, 6, 8, 10, 12)
JOBS = {f'null{i:02d}': i for i in range(1, 9)}
CAPS = {'CPU_cap_s_per_job': 600, 'wall_cap_s_per_job': 900,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'max_simultaneous_jobs': 2,
        'memory_cap_bytes_aggregate': 4 * 1024**3, 'job_output_budget_bytes': 40 * 1024**2,
        'total_output_budget_bytes': 320 * 1024**2, 'workspace_cap_bytes': 8 * 1024**3,
        'archive_cap_bytes': 200 * 1024**2, 'phase_CPU_allocation_s': 6000}
COUNTS = {'maps': 96, 'carrier_maximum_records': 393216, 'valid_hypothesis_records': 875298816,
          'normalization_records': 96, 'score_audit_queries': 387, 'score_audit_raw_power_cells': 778644,
          'TOP20_entries': 20, 'TOP3_entries': 3, 'order_queries': 3, 'row_center_boxes': 48,
          'permutation_scores': 72, 'generated_raw_crops': 96, 'generated_raw_rows': 1536,
          'generated_raw_cells': 18579456}
STATUS = 'COMPLETE_96_IID_GAMMA_NULL_MAPS387_AUDITS3_ORDER_DIAGNOSTICS'
GO_STATUS = 'GO_8_FULL_IID_GAMMA_NULL_FAMILIES'
ATOL, RTOL = 1e-7, 1e-10
MAP_FIELDS = ('frequency_hz_at_window_reference', 'maximum_robust_box_track_score',
              'winning_drift_hz_s', 'winning_drift_grid_index', 'winning_window_start_row',
              'winning_width_channels', 'valid_hypothesis_count', 'source_reference_channels', 'drift_grid_hz_s')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Relative confined path required')
    return path


def byte_pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = value
    spec.loader.exec_module(value)
    return value


def versions():
    return {'Python': sys.version.split()[0], **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy')}}


def method_contract():
    return {'schema': 'SETI_FULL_BURST_IID_GAMMA_MODEL_SCOPE_V1',
        'jobs': {job: {'family_index': index, 'synthetic_role': 'SYNTHETIC_ENGINEERING', 'synthetic_tstart_mjd': 0.0}
                 for job, index in JOBS.items()},
        'model_law': {'distribution': 'IID Gamma', 'shape': 51.0, 'scale': 1.0 / 51.0, 'mean': 1.0,
                      'fitted_to_observations': False, 'verified_instrument_degrees_of_freedom': False},
        'rng': {'bit_generator': 'PCG64', 'root_entropy': 20261012,
                'spawn_key': '[family_index1..8, canonical_domain_index0..95]',
                'draw': 'one Generator.gamma(shape=51.0,scale=1.0/51.0,size=(16,12096)) per core',
                'draw_dtype': 'float64', 'one_conversion_dtype': '<f4', 'mapping_order': 'C row-major',
                'all96_crops_generated_before_search': True, 'primary_redraws': 0},
        'core_domains': [{'domain_index': index, 'native_chunk_index': n, 'core_q': q,
                         'reference_channel_interval_half_open': [n * COUNT + q * CORE, n * COUNT + (q + 1) * CORE],
                         'loaded_channel_interval_half_open': [n * COUNT + q * CORE - HALO, n * COUNT + (q + 1) * CORE + HALO]}
                        for index, (n, q) in enumerate(DOMAINS)],
        'total_maps': 768, 'maps_per_family': 96, 'core_channels': CORE, 'halo_channels': HALO,
        'source_rows_per_scan': 16, 'raw_crop_shape': [16, 12096], 'raw_dtype': '<f4',
        'window_length_rows': 4, 'window_start_rows': list(STARTS), 'widths_channels': [1, 3],
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79},
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP, 'synthetic_tstart_mjd': 0.0,
        'valid_hypotheses_per_carrier': 2226, 'total_carrier_maximum_records': 3145728,
        'total_valid_hypothesis_records': 7002390528,
        'preprocessing': 'unchanged detector.preprocess plus _box_arrays on all16rows once per core',
        'normalization': 'all4096 declared core channels; reestimate full16row power median/residual MAD/winsorized location once',
        'window_times_s': [0, TSAMP, 2 * TSAMP, 3 * TSAMP],
        'rounding': 'np.rint complete absolute source mapping before subtracting raw crop origin',
        'winning_tie_order': 'window start ascending; width1 before3; drift index ascending; strict greater update',
        'target_ranking': 'all96 combined carrier maps per family; score descending then absolute channel ascending; greedy distance>3; TOP3=first3TOP20',
        'map_npz_fields': list(MAP_FIELDS), 'audit_carrier_indices': [0, 2048, 4095, 'core_max'],
        'extra_global_TOP3_audits': 3, 'audit_raw_shape': [4, 503],
        'order_queries_per_family': 3, 'order_permutations': 'lexicographic permutations of (0,1,2,3)',
        'order_scores': '((M[0,pi0]+M[1,pi1])+M[2,pi2])+M[3,pi3], then divide sqrt(4*width)',
        'order_deduplication': 'actual integer center vector; first lex representative; retain multiplicity; exclude identity-vector class',
        'order_exact_ranks': 'best=1+greater distinct scores; worst=greater+exact_equal; no epsilon',
        'order_degenerate': 'U=1: no distinct alternative; max/median/differences null; rank1 noninformative',
        'audit_score_ATOL': ATOL, 'audit_score_RTOL': RTOL,
        'map_NPZ_budget_bytes': 190 * 1024, 'normalization_JSON_budget_bytes': 4000,
        'audit_NPZ_budget_bytes': 11000, 'order_NPZ_budget_bytes': 20 * 1024,
        'winning_raw_NPZ_budget_bytes': 800000,
        'expected_counts_per_family': COUNTS, 'all_raw_crops_retained_in_RAM_through_selection': True,
        'saved_full_raw_crops': 'distinct TOP3-winning domains only; other bytes exactly reproducible from frozen RNG',
        'independent_model_units': 8, 'TOP3_winners_independent_units': False,
        'phase_CPU_split_s': {'primary': 4800, 'QA': 600, 'report': 200, 'package': 200, 'preparation_publication': 200},
        'model_only': True, 'observational_arrays_opened': False, 'new_observation': False,
        'sky_FAP_or_permutation_p_value': False, 'qualified_SETI_detection': False,
        'masks': None, 'geometric_veto': False, 'data_selected_exclusions': [],
        'protected2016_data_opened': False, 'previous_outputs_modified': False,
        'new_telescope_HTTP_requests': 0, 'cost_DKK': 0, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', **CAPS}


def contract(root, scope):
    require(all(scope.get(key) == value for key, value in method_contract().items()), 'Prospective engineering model differs')
    pins = {}
    for record in scope['text_code_pins'] + scope['prior_reference_pins']:
        path = confined(root, record['path'])
        require(path.suffix in ('.py', '.json', '.md', '.txt', '.csv') and byte_pin(root, path) == record,
                'Pinned source/reference text changed: ' + record['path'])
        pins[record['path']] = record
    require(pins[BASE + '/driver.py']['sha256'] == digest(Path(__file__).resolve())
            and pins[DETECTOR]['sha256'] == DETECTOR_SHA, 'Original detector/current driver differs')
    require(versions() == scope['runtime_versions'], 'Pinned model runtime differs')
    require(scope['runtime_versions']['numpy'] == '2.3.5' and scope['runtime_versions']['scipy'] == '1.17.0',
            'Declared exact NumPy/SciPy runtime required')


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


def output_guard(root, out, workspace=False):
    require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= CAPS['job_output_budget_bytes'], '40MiB family output cap exceeded')
    if workspace:
        require(workspace_bytes(root) <= CAPS['workspace_cap_bytes'], '8GiB workspace cap exceeded')


def store_npz(np, root, path, values, bound):
    with path.open('xb') as stream:
        np.savez(stream, **values)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.stat().st_size <= bound, 'Prospective NPZ output bound exceeded')
    return byte_pin(root, path)


def order_diagnostic(np, median_filter, root, out, query, raw_crop, crop0):
    chosen = query['selected_tuple']
    width, r0 = chosen['width_channels'], chosen['window_start_row']
    rows, times = np.arange(r0, r0 + 4, dtype='<i8'), np.arange(4) * TSAMP
    centers = np.rint((chosen['frequency_hz_at_window_reference'] - FCH1) / DF
                      + chosen['drift_hz_s'] * times / DF).astype('<i8')
    first, stop = int(centers.min()) - 251, int(centers.max()) + 252
    require(crop0 <= first < stop <= crop0 + CORE + 2 * HALO, 'Order envelope outside canonical model crop')
    raw = raw_crop[rows, first - crop0:stop - crop0].copy()
    norm = read_json(root / query['normalization']['path'])
    level, location, scale = (np.asarray(norm[k], dtype=np.float64) for k in
                             ('row_power_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'))
    ratio = raw.astype(np.float64) / level[rows, None]
    z = (ratio - median_filter(ratio, size=(1, 501), mode='nearest') - location[rows, None]) / scale[rows, None]
    columns = centers[:, None] - first + np.arange(-(width // 2), width // 2 + 1)[None, :]
    matrix = z[:, columns].sum(axis=2, dtype=np.float64)
    with np.load(root / query['capsule']['path'], allow_pickle=False) as old:
        require(np.array_equal(old['absolute_time_rows'], rows) and np.array_equal(old['rounded_absolute_centers'], centers), 'Model order/audit geometry differs')
        diagonal = np.stack([raw[i, centers[i] - first - 251:centers[i] - first + 252] for i in range(4)])
        require(np.array_equal(diagonal.view(np.uint32), old['raw_power'].view(np.uint32)), 'Model order/audit raw diagonal bits differ')
        require(np.allclose(np.diag(matrix), old['standardized_row_box_sums'], atol=ATOL, rtol=RTOL), 'Model order/audit identity row sums differ')
    permutations = np.asarray(list(itertools.permutations(range(4))), dtype='<i2')
    scores = (((matrix[0, permutations[:, 0]] + matrix[1, permutations[:, 1]])
               + matrix[2, permutations[:, 2]]) + matrix[3, permutations[:, 3]]) / np.sqrt(4 * width)
    identity = float(scores[0])
    require(np.isfinite(matrix).all() and np.isfinite(scores).all()
            and np.isclose(identity, chosen['score'], atol=ATOL, rtol=RTOL), 'Model order identity score differs from selected winner')
    vectors = centers[permutations]
    seen, representatives, multiplicities = {}, [], []
    for index, vector in enumerate(vectors.tolist()):
        key = tuple(vector)
        if key not in seen:
            seen[key] = len(representatives)
            representatives.append(index)
            multiplicities.append(0)
        multiplicities[seen[key]] += 1
    distinct, wrong = scores[representatives], scores[representatives][1:]
    greater, equal = int(np.count_nonzero(distinct > identity)), int(np.count_nonzero(distinct == identity))
    capsule = store_npz(np, root, out / (query['query_id'] + '_order.npz'),
        {'raw_power': raw, 'absolute_time_rows': rows, 'rounded_absolute_centers': centers,
         'standardized_row_center_box_sums': matrix, 'permutation_scores': scores, 'permutation_indices': permutations}, 20 * 1024)
    key_fields = ('scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core', 'window_start_row', 'drift_grid_index', 'width_channels')
    return {'query_id': query['query_id'], 'query_kind': query['query_kind'], 'selected_tuple': chosen,
        'scientific_tuple_key': [chosen[k] for k in key_fields], 'scientific_tuple_multiplicity': 1,
        'normalization': query['normalization'], 'score_audit_capsule': query['capsule'], 'new_capsule': capsule,
        'centers': centers.tolist(), 'source_rows': rows.tolist(), 'raw_source_channel0': first, 'raw_channel_count': stop - first,
        'matrix': matrix.tolist(), 'permutation_scores': scores.tolist(), 'permutation_center_vectors': vectors.tolist(),
        'distinct_center_vectors': vectors[representatives].tolist(), 'distinct_representative_permutation_indices': representatives,
        'distinct_assignment_multiplicities': multiplicities, 'distinct_scores': distinct.tolist(), 'identity_score': identity,
        'distinct_center_count': len(set(centers.tolist())), 'stationary_centers': len(set(centers.tolist())) == 1,
        'duplicate_centers': len(set(centers.tolist())) < 4, 'prior_primary_score': chosen['score'],
        'identity_minus_prior_primary_score': identity - chosen['score'], 'zero_drift': chosen['drift_hz_s'] == 0,
        'diagnostic_degenerate': len(representatives) == 1,
        'rounded_nonzero_drift_degenerate': chosen['drift_hz_s'] != 0 and len(representatives) == 1,
        'distinct_assignment_count': len(representatives), 'wrong_order_distinct_count': len(wrong),
        'wrong_order_max_score': float(wrong.max()) if len(wrong) else None,
        'wrong_order_median_score': float(np.median(wrong)) if len(wrong) else None,
        'identity_minus_wrong_order_max': identity - float(wrong.max()) if len(wrong) else None,
        'identity_minus_wrong_order_median': identity - float(np.median(wrong)) if len(wrong) else None,
        'identity_rank_best': greater + 1, 'identity_rank_worst': greater + equal, 'identity_exact_tie_count': equal,
        'identity_equal_score_wrong_order_count': equal - 1, 'wrong_order_strictly_better_than_identity_count': greater}


def run(root, scope, job, out):
    import numpy as np
    from scipy.ndimage import median_filter
    detector = module('gamma_null_unchanged_detector', root / DETECTOR)
    family = JOBS[job]
    scan_id, target = job, 'IID_GAMMA_MODEL'
    raw_crops, rng_records = {}, []
    # The entire prospective family is generated once before any search or selection.
    for domain, (native, q) in enumerate(DOMAINS):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(20261012, spawn_key=(family, domain))))
        initial = copy.deepcopy(rng.bit_generator.state)
        raw = rng.gamma(shape=51.0, scale=1.0 / 51.0, size=(16, CORE + 2 * HALO)).astype('<f4')
        require(raw.shape == (16, 12096) and raw.dtype.str == '<f4' and np.isfinite(raw).all() and (raw > 0).all(), 'Invalid canonical Gamma model crop')
        raw_crops[native, q] = raw
        first = native * COUNT + q * CORE
        rng_records.append({'domain_index': domain, 'family_index': family, 'native_chunk_index': native, 'core_q': q,
            'map_id': f'{job}_native{native}_q{q:03d}', 'root_entropy': 20261012, 'spawn_key': [family, domain],
            'bit_generator': 'PCG64', 'initial_bit_generator_state': initial,
            'final_bit_generator_state': copy.deepcopy(rng.bit_generator.state),
            'draw_shape': [16, 12096], 'draw_dtype': 'float64', 'raw_shape': [16, 12096], 'raw_dtype': '<f4',
            'loaded_channel_interval_half_open': [first - HALO, first + CORE + HALO],
            'core_channel_interval_half_open': [first, first + CORE],
            'raw_sha256': hashlib.sha256(raw.tobytes(order='C')).hexdigest(),
            'raw_row_sha256s': [hashlib.sha256(raw[row].tobytes(order='C')).hexdigest() for row in range(16)],
            'winning_raw_capsule': None})
    cfg, drifts, times = detector.Config(widths=(1, 3)), np.linspace(-4., 4., 159), np.arange(4) * TSAMP
    require(drifts[79] == 0.0, 'Exact zero central drift required')
    maps, audits, saved, row_sums = [], [], {}, {}

    def selected_tuple(native, q, value, index, rank=None):
        start = int(value['winning_window_start_row'][index])
        chosen = {'primary_id': job, 'scan_id': job, 'primary_target': target, 'family_index': family,
            'synthetic_role': 'SYNTHETIC_ENGINEERING', 'data_origin': 'SYNTHETIC_IID_GAMMA_MODEL',
            'native_chunk_index': native, 'core_q': q, 'map_id': f'{job}_native{native}_q{q:03d}',
            'carrier_index_in_core': int(index), 'source_reference_channel': int(value['source_reference_channels'][index]),
            'frequency_hz_at_window_reference': float(value['frequency_hz_at_window_reference'][index]),
            'window_start_row': start, 'window_length_rows': 4, 'window_source_rows': list(range(start, start + 4)),
            'reference_time_s_from_synthetic_scan_start': (start + .5) * TSAMP,
            'drift_grid_index': int(value['winning_drift_grid_index'][index]),
            'drift_hz_s': float(value['winning_drift_hz_s'][index]), 'width_channels': int(value['winning_width_channels'][index]),
            'score': float(value['maximum_robust_box_track_score'][index])}
        if rank is not None:
            chosen['rank'] = rank
        return chosen

    def audit(query_id, kind, native, q, value, index, sums, normalization, rank=None):
        chosen = selected_tuple(native, q, value, index, rank)
        rows = np.arange(chosen['window_start_row'], chosen['window_start_row'] + 4, dtype=np.int64)
        centers = np.rint((chosen['frequency_hz_at_window_reference'] - FCH1) / DF + chosen['drift_hz_s'] * times / DF).astype(np.int64)
        crop0 = native * COUNT + q * CORE - HALO
        absolute = centers[:, None] + np.arange(-251, 252)[None, :]
        require(absolute.min() >= crop0 and absolute.max() < crop0 + CORE + 2 * HALO, 'Score audit outside original canonical model crop')
        raw = raw_crops[native, q][rows[:, None], absolute - crop0]
        require(np.isclose(sums.sum() / np.sqrt(4 * chosen['width_channels']), chosen['score'], atol=ATOL, rtol=RTOL), 'Cached model winning score differs')
        capsule = store_npz(np, root, out / (query_id + '_raw4x503.npz'),
             {'raw_power': raw, 'absolute_time_rows': rows, 'rounded_absolute_centers': centers, 'standardized_row_box_sums': sums}, 11000)
        audits.append({'query_id': query_id, 'query_kind': kind, 'native_chunk_index': native, 'core_q': q,
                       'map_id': chosen['map_id'], 'selected_tuple': chosen, 'normalization': normalization, 'capsule': capsule})

    for native, q in DOMAINS:
        first = native * COUNT + q * CORE
        channels = np.arange(first, first + CORE, dtype=np.int64)
        frequencies, crop0 = FCH1 + DF * channels, first - HALO
        crop = raw_crops[native, q].astype(np.float64)
        require(crop.shape == (16, CORE + 2 * HALO), 'Complete16row contiguous core crop required')
        scan = detector.Scan(scan_id, 'SYNTHETIC_ENGINEERING', crop, 0.0, TSAMP, FCH1, DF, crop0, channels)
        z, mask, normalization = detector.preprocess(scan, cfg)
        require(mask.all(), 'No source masking allowed')
        boxes = detector._box_arrays(z, mask, cfg)
        base = (frequencies - FCH1) / DF
        best = np.full(CORE, -np.inf, dtype=np.float64)
        winning_start = np.full(CORE, -1, dtype=np.int16)
        winning_width = np.zeros(CORE, dtype=np.int16)
        winning_drift_index = np.full(CORE, -1, dtype=np.int16)
        winning_drift = np.full(CORE, np.nan, dtype=np.float64)
        valid_count = np.zeros(CORE, dtype=np.int64)
        # Traversal is the scientific tie order: start, width, ascending drift.
        for start_row in STARTS:
            window_boxes = {w: (box[0][start_row:start_row + 4], box[1][start_row:start_row + 4])
                            for w, box in boxes.items()}
            for width in (1, 3):
                for begin in range(0, 159, cfg.drift_tile):
                    ds = drifts[begin:begin + cfg.drift_tile]
                    for lo in range(0, CORE, cfg.carrier_tile):
                        hi = min(lo + cfg.carrier_tile, CORE)
                        scores, valid = detector._score_tile(window_boxes, base[lo:hi], times, DF, ds, width, crop0)
                        valid_count[lo:hi] += valid.sum(axis=0)
                        arg = scores.argmax(axis=0)
                        values = scores[arg, np.arange(hi - lo)]
                        improve = values > best[lo:hi]
                        locations = np.arange(lo, hi)[improve]
                        best[locations] = values[improve]
                        winning_start[locations] = start_row
                        winning_width[locations] = width
                        winning_drift_index[locations] = begin + arg[improve]
                        winning_drift[locations] = ds[arg[improve]]
        require(np.all(valid_count == 2226) and np.isfinite(best).all()
                and np.isin(winning_start, STARTS).all() and np.isin(winning_width, (1, 3)).all(),
                'Complete combined seven-window family required')
        value = {'frequency_hz_at_window_reference': frequencies,
                 'maximum_robust_box_track_score': best, 'winning_drift_hz_s': winning_drift,
                 'winning_drift_grid_index': winning_drift_index, 'winning_window_start_row': winning_start,
                 'winning_width_channels': winning_width, 'valid_hypothesis_count': valid_count,
                 'source_reference_channels': channels, 'drift_grid_hz_s': drifts}
        map_id = '%s_native%d_q%03d' % (scan_id, native, q)
        map_pin = store_npz(np, root, out / (map_id + '.npz'), value, 190 * 1024)
        compact = dict(normalization)
        require(compact.pop('normalization_source_channels') == channels.tolist(), 'Normalization core interval differs')
        compact['normalization_source_channel_interval_half_open'] = [first, first + CORE]
        norm_path = out / (map_id + '_normalization.json')
        save(norm_path, compact)
        norm_pin = byte_pin(root, norm_path)
        require(norm_pin['bytes'] <= 4000, 'Compact full16row normalization budget exceeded')
        maps.append({'map_id': map_id, 'scan_id': scan_id, 'primary_id': job, 'synthetic_role': 'SYNTHETIC_ENGINEERING',
                     'native_chunk_index': native, 'core_q': q, **map_pin, 'normalization': norm_pin,
                     'reference_channel_interval_half_open': [first, first + CORE],
                     'loaded_channel_interval_half_open': [crop0, first + CORE + HALO],
                     'searched_carriers': CORE, 'valid_hypotheses_per_carrier': 2226,
                     'combined_window_start_rows': list(STARTS)})
        centers = np.rint(base[:, None] + winning_drift[:, None] * times[None, :] / DF).astype(np.int64)
        sums = np.empty((CORE, 4), dtype=np.float64)
        for width in (1, 3):
            chosen = winning_width == width
            for row in range(4):
                sums[chosen, row] = boxes[width][0][winning_start[chosen] + row,
                                                   centers[chosen, row] - crop0 - width // 2]
        saved[native, q], row_sums[native, q] = value, sums
        maximum = int(np.lexsort((channels, -best))[0])
        for kind, index in (('first', 0), ('midpoint', 2048), ('last', 4095), ('core_max', maximum)):
            audit('native%d_q%03d_%s' % (native, q, kind), kind, native, q, value, index, sums[index], norm_pin)
        del z, mask, boxes, window_boxes, scan, crop, centers
        output_guard(root, out, workspace=len(maps) % 16 == 0)
        if len(maps) % 8 == 0:
            print(json.dumps({'job': job, 'completed_combined_maps': len(maps), 'expected': 96}), flush=True)
    channels = np.concatenate([saved[key]['source_reference_channels'] for key in DOMAINS])
    scores = np.concatenate([saved[key]['maximum_robust_box_track_score'] for key in DOMAINS])
    selected = []
    for position in np.lexsort((channels, -scores)):
        channel = int(channels[position])
        if any(abs(channel - old['source_reference_channel']) <= 3 for old in selected):
            continue
        map_index, carrier = divmod(int(position), CORE)
        native, q = DOMAINS[map_index]
        selected.append(selected_tuple(native, q, saved[native, q], carrier, len(selected) + 1))
        if len(selected) == 20:
            break
    require(len(selected) == 20, 'Target-global96map TOP20 incomplete')
    for name, records_out in (('TOP20.json', selected), ('TOP3.json', selected[:3])):
        save(out / name, {'schema': 'SETI_GAMMA_NULL_GLOBAL_RANKS_V1', 'primary_id': job,
                          'scan_id': scan_id, 'synthetic_role': 'SYNTHETIC_ENGINEERING',
                          'selection_rule': scope['target_ranking'], 'records': records_out})
    for chosen in selected[:3]:
        native, q, index = chosen['native_chunk_index'], chosen['core_q'], chosen['carrier_index_in_core']
        norm = next(m['normalization'] for m in maps if (m['native_chunk_index'], m['core_q']) == (native, q))
        audit('global_top%02d' % chosen['rank'], 'global_top3', native, q, saved[native, q], index,
              row_sums[native, q][index], norm, chosen['rank'])
    require(len(maps) == 96 and len(audits) == 387, 'Frozen map/audit count differs')
    save(out / 'MAPS.json', {'schema': 'SETI_GAMMA_NULL_COMBINED_MAPS_V1', 'primary_id': job, 'scan_id': scan_id, 'records': maps})
    save(out / 'SCORE_AUDITS.json', {'schema': 'SETI_GAMMA_NULL_SCORE_AUDITS_V1', 'primary_id': job, 'scan_id': scan_id, 'records': audits})

    winning_domains = sorted({(t['native_chunk_index'], t['core_q']) for t in selected[:3]}, key=DOMAINS.index)
    for native, q in winning_domains:
        record = next(r for r in rng_records if (r['native_chunk_index'], r['core_q']) == (native, q))
        record['winning_raw_capsule'] = store_npz(np, root, out / (record['map_id'] + '_raw16x12096.npz'),
                                                 {'raw_power': raw_crops[native, q]}, 800000)
    orders = []
    for query in audits[-3:]:
        native, q = query['native_chunk_index'], query['core_q']
        orders.append(order_diagnostic(np, median_filter, root, out, query, raw_crops[native, q], native * COUNT + q * CORE - HALO))
    require(len(orders) == 3 and [r['selected_tuple'] for r in orders] == selected[:3], 'Model TOP3 order-control anchors differ')
    save(out / 'ORDER_DIAGNOSTICS.json', {'schema': 'SETI_GAMMA_NULL_ORDER_DIAGNOSTICS_V1', 'primary_id': job,
         'scan_id': job, 'family_index': family, 'records': orders, 'counts': {'order_queries': 3, 'row_center_boxes': 48, 'permutation_scores': 72},
         'model_only': True, 'selected_winner_diagnostic_only': True, 'sky_FAP_or_permutation_p_value': False})
    for record in rng_records:
        raw = raw_crops[record['native_chunk_index'], record['core_q']]
        require(hashlib.sha256(raw.tobytes(order='C')).hexdigest() == record['raw_sha256']
                and [hashlib.sha256(raw[row].tobytes(order='C')).hexdigest() for row in range(16)] == record['raw_row_sha256s'],
                'Canonical model crop changed during search')
    save(out / 'RNG_MANIFEST.json', {'schema': 'SETI_GAMMA_NULL_CANONICAL_RAW_MANIFEST_V1', 'primary_id': job, 'family_index': family,
         'records': rng_records, 'model_law': scope['model_law'], 'rng': scope['rng'], 'runtime_versions': versions(),
         'raw_crops_pre_and_post_hashes_match': True, 'primary_redraws': 0})
    return {'counts': {**COUNTS, 'winning_raw_crops': len(winning_domains)}, 'raw_crops_pre_and_post_hashes_match': True,
            'primary_redraws': 0, 'model_only': True, 'synthetic_role': 'SYNTHETIC_ENGINEERING',
            'synthetic_tstart_mjd': 0.0, 'runtime_versions': versions()}


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
    scope = read_json(scope_path)
    contract(root, scope)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_EIGHT_GAMMA_NULL_FAMILIES', 'scope': byte_pin(root, scope_path),
                          'runtime_versions': versions(), 'numerical_modules_imported': False, 'model_values_generated': False}))
        return
    require(args.run and args.scope_sha256 == digest(scope_path), 'Root --run with exact prospective scope SHA required')
    go_path = confined(root, args.root_go)
    require(args.root_go_sha256 == digest(go_path), 'Exact root GO SHA required')
    go = read_json(go_path)
    require(go['status'] == GO_STATUS and go['scope_sha256'] == args.scope_sha256
            and go['driver_sha256'] == digest(Path(__file__).resolve())
            and go['qa_sha256'] == digest(root / BASE / 'qa_saved.py')
            and all(go.get(k) == v for k, v in CAPS.items()), 'Root model GO scientific/resource contract differs')
    require(workspace_bytes(root) + CAPS['total_output_budget_bytes'] <= CAPS['workspace_cap_bytes'], 'Prospective320MiB output reserve exceeds8GiB workspace')
    locks, out = [], None
    started, cpu0 = time.monotonic(), time.process_time()
    def deadline(signum, frame):
        raise TimeoutError('Model family CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (600, 601))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    signal.alarm(900)
    try:
        for slot in range(2):
            lock = (root / BASE / f'SLOT{slot}.lock').open('a+b')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locks.append(lock)
                break
            except BlockingIOError:
                lock.close()
        else:
            raise BlockingIOError('Both2GiB model slots occupied')
        lock = (root / BASE / (args.job + '.lock')).open('a+b')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(lock)
        destination = root / BASE / 'results' / args.job
        destination.mkdir(parents=True, exist_ok=False)
        out = destination
        result = run(root, scope, args.job, out)
        contract(root, scope)
        require(digest(scope_path) == args.scope_sha256 and digest(go_path) == args.root_go_sha256, 'Scope/GO changed during model generation')
        pins = [byte_pin(root, path) for path in sorted(out.iterdir()) if path.is_file()]
        require(len(pins) == 588 + result['counts']['winning_raw_crops'], 'Closed model family output inventory differs')
        receipt = {'schema': 'SETI_GAMMA_NULL_FAMILY_EXECUTION_V1', 'status': STATUS,
             'primary_id': args.job, 'scan_id': args.job, 'family_index': JOBS[args.job],
             'scope_sha256': args.scope_sha256, 'driver_sha256': digest(Path(__file__).resolve()),
             'root_GO_pin': byte_pin(root, go_path), **result, 'output_byte_pins': pins, 'science_slot': slot,
             'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
             'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
             'new_telescope_HTTP_requests': 0, 'cost_DKK': 0, 'observational_arrays_opened': False,
             'sky_FAP_or_permutation_p_value': False, 'qualified_SETI_detection': False,
             'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', **CAPS}
        require(receipt['process_CPU_seconds'] <= 600 and receipt['wall_seconds'] <= 900
                and receipt['peak_RSS_bytes'] <= 2 * 1024**3, 'Measured model family resource cap exceeded')
        receipt_bytes = len((json.dumps(receipt, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        require(sum(record['bytes'] for record in pins) + receipt_bytes <= CAPS['job_output_budget_bytes']
                and workspace_bytes(root) + ((receipt_bytes + 4095) // 4096) * 4096 <= CAPS['workspace_cap_bytes'],
                'Prospective receipt would exceed family/workspace output cap')
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        output_guard(root, out, workspace=True)
    except BaseException as exc:
        if out is not None and not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_GAMMA_NULL_FAMILY_EXECUTION_V1',
                 'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'primary_id': args.job,
                 'scope_sha256': args.scope_sha256, 'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)
        for lock in locks:
            lock.close()


if __name__ == '__main__':
    main()
