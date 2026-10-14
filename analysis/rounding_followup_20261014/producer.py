"""Metadata-only preparation of exact continuous native four-row path families.

Geometry opens authenticated JSON metadata only. Observed-score execution is
fail-closed until a separate root-frozen scope and code GO are provided.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

import geometry

MATRIX = 'seti_burst_full/context_results/CONTEXT_PROFILES.json'
DF, TSAMP = -2.7939677238464355, 18.253611008
HALF_DRIFT = 4 / 158
OFFSETS = (0, -1024, -768, -512, -256, 256, 512, 768, 1024)
WINDOW_STARTS = (0, 2, 4, 6, 8, 10, 12)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def pin(path, root=None):
    return {'path': path.relative_to(root).as_posix() if root else str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def create_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())


def geometry_preflight(args):
    root, config_path = Path(args.root).resolve(), Path(args.geometry_config).resolve()
    config = read(config_path)
    matrix_path = root / config['matrix']['path']
    require(config['matrix']['path'] == MATRIX and matrix_path.stat().st_size == config['matrix']['bytes']
            and sha(matrix_path) == config['matrix']['sha256'], 'Frozen geometry matrix pin differs')
    require(config['df_hz'] == DF and config['tsamp_s'] == TSAMP and config['half_drift_hz_s'] == HALF_DRIFT
            and config['offset_channels'] == list(OFFSETS) and config['window_start_rows'] == list(WINDOW_STARTS)
            and config['phase_box_channels'] == [-.5, .5], 'Frozen geometry constants differ')
    require(sha(Path(__file__).resolve().parent / 'geometry.py') == config['geometry_code_sha256'], 'Exact geometry code pin differs')
    matrix = read(matrix_path)
    require(len(matrix['profiles']) == 54 and [p['profile_id'] for p in matrix['profiles']] == config['profile_ids'], 'Frozen profile order differs')
    out = Path(args.geometry_output_dir).resolve()
    require(not out.exists() and not out.is_relative_to(root), 'Fresh geometry output outside read-only input tree required')
    budget = config['budget'];caps = config['caps']
    resource.setrlimit(resource.RLIMIT_CPU, (budget['CPU_seconds'], budget['CPU_seconds']))
    resource.setrlimit(resource.RLIMIT_AS, (budget['memory_bytes'], budget['memory_bytes']))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Geometry wall budget exceeded')))
    signal.alarm(budget['wall_seconds'])
    started = time.monotonic()
    import numpy as np
    profiles, evaluated, path_count, missing_count = [], 0, 0, 0
    for pi, profile in enumerate(matrix['profiles']):
        track = profile['selected_track'];times = profile['times_from_primary_reference_s']
        require(track['width_channels'] == 1 and len(times) == 16, 'Expected width1 metadata geometry')
        d0, base = track['drift_hz_s'], track['source_reference_channel']
        drifts = d0 + np.linspace(-HALF_DRIFT, HALF_DRIFT, 81, dtype=np.float64)
        drift_axis = np.repeat(drifts, 5);phase_axis = np.tile(np.asarray([-.5, -.25, 0., .25, .5]), 81)
        legacy = np.rint(base + phase_axis[:, None] + drift_axis[:, None] * np.asarray(times)[None, :] / DF).astype(np.int64)
        windows = []
        for wi, start in enumerate(WINDOW_STARTS):
            rows = list(range(start, start + 4))
            family = geometry.enumerate_paths(base, d0, [times[r] for r in rows], DF, HALF_DRIFT,
                                              caps['total_witness_pairs'] - evaluated)
            require(family['unique_paths'] <= caps['unique_paths_per_window'], 'Per-window exact path cap exceeded')
            evaluated += family['witness_pairs_evaluated'];path_count += family['unique_paths']
            require(path_count <= caps['total_unique_paths'] and evaluated <= caps['total_witness_pairs'], 'Global exact geometry cap exceeded')
            exact_paths = {tuple(p['channels']) for p in family['paths']}
            legacy_paths = sorted({tuple(p) for p in legacy[:, rows].tolist()})
            missing = [list(path) for path in legacy_paths if path not in exact_paths]
            missing_count += len(missing)
            family.update(window_index=wi, window_start_row=start, window_source_rows=rows,
                          legacy_unique_paths=len(legacy_paths), legacy_paths_attainable_exact_count=len(legacy_paths) - len(missing),
                          legacy_only_float_paths=missing,
                          legacy_hypothesis_indices_with_infeasible_exact_paths=[hi for hi, path in enumerate(legacy[:, rows].tolist()) if tuple(path) not in exact_paths])
            windows.append(family)
        profiles.append({'profile_id': profile['profile_id'], 'origin_scan_id': track['scan_id'],
                         'context_scan_id': profile['context_scan_id'], 'origin_rank': track['rank'],
                         'source_reference_channel': base, 'original_drift_hz_s': d0,
                         'times_from_primary_reference_s': times, 'windows': windows})
        if (pi + 1) % 6 == 0:
            print(json.dumps({'geometry_profiles_completed': pi + 1, 'total_unique_paths': path_count,
                              'witness_pairs_evaluated': evaluated}), flush=True)
    out.mkdir(parents=True)
    result = {'schema': 'SETI_EXACT_CONTINUOUS_ROUNDING_FAMILIES_V1', 'status': 'COMPLETE_METADATA_ONLY_EXACT_GEOMETRY_54_PROFILES_378_WINDOWS',
              'config': pin(config_path), 'geometry_code': pin(Path(geometry.__file__).resolve()),
              'geometry_driver': pin(Path(__file__).resolve()), 'source_matrix': config['matrix'],
              'raw_spectral_arrays_opened': False, 'observed_scores_evaluated': False,
              'metadata_legacy_float_coordinates_evaluated': True,
              'path_order': 'window_start_row_slow_native_four_channel_tuple_lexicographic_fast',
              'offset_translation': 'all_even_offsets_preserve_absolute_channel_tie_parity',
              'exact_arithmetic': 'Fraction.from_float separately for d0, every saved time, DF, half_box; phasebox exact +/-1/2',
              'caps': caps, 'profiles': profiles,
              'counts': {'profiles': 54, 'windows': 378, 'offsets': 9, 'total_unique_paths_zero_offset': path_count,
                         'total_offset_path_scores': path_count * 9, 'witness_pairs_evaluated': evaluated,
                         'legacy_only_float_unique_paths_across_windows': missing_count}}
    create_json(out / 'GEOMETRY.json', result)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': 'PASS_BOUNDED_METADATA_ONLY_CONTINUOUS_ROUNDING_GEOMETRY',
               'raw_spectral_arrays_opened': False, 'observed_scores_evaluated': False,
               'config': pin(config_path), 'geometry': pin(out / 'GEOMETRY.json'),
               'counts': result['counts'], 'resource_limits': budget,
               'resource_usage': {'CPU_s': usage.ru_utime + usage.ru_stime, 'wall_s': time.monotonic() - started,
                                  'peak_RSS_bytes': usage.ru_maxrss * 1024}}
    create_json(out / 'GEOMETRY_RECEIPT.json', receipt)
    signal.alarm(0)
    print(json.dumps({'status': receipt['status'], 'counts': result['counts'], 'resource_usage': receipt['resource_usage']}))


DC = (178782208, 179830784, 180879360)
NORM_FIELDS = ('row_power_median', 'row_residual_median', 'row_residual_MAD_scale', 'row_winsorized_residual_location')
CPU_CAP, WALL_CAP, MEMORY_CAP = 600, 900, 2 * 1024**3
ATOL = 1e-7


def conf(root, name):
    value = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            value.resolve().is_relative_to(root) and not value.is_symlink(), 'Confined relative input required')
    return value


def auth(root, declaration):
    path = conf(root, declaration['path'])
    require(path.is_file() and path.stat().st_size == declaration['bytes'] and sha(path) == declaration['sha256'],
            'Frozen input pin differs: ' + declaration['path'])
    return path


def read_observed_metadata(args):
    root, scope_path = Path(args.root).resolve(), Path(args.scope).resolve()
    scope = read(scope_path)
    require(scope['matrix_path'] == MATRIX and (args.portable_inputs or scope['source_root'] == str(root / 'seti_work')),
            'Original extracted input root differs')
    require(scope['geometry']['df_hz'] == DF and scope['geometry']['tsamp_s'] == TSAMP and
            scope['geometry']['drift_half_step_hz_s'] == HALF_DRIFT and scope['geometry']['phase_box_channels'] == [-.5, .5]
            and scope['geometry']['offset_channels'] == list(OFFSETS) and scope['geometry']['window_start_rows'] == list(WINDOW_STARTS),
            'Frozen observed geometry differs')
    for declared in scope['input_pins']:
        auth(root, declared)
    geom_path = auth(root, scope['geometry_pin'])
    geom = read(geom_path)
    require(geom['status'] == 'COMPLETE_METADATA_ONLY_EXACT_GEOMETRY_54_PROFILES_378_WINDOWS'
            and geom['counts']['total_unique_paths_zero_offset'] == 22235
            and geom['counts']['total_offset_path_scores'] == 200115, 'Exact frozen path census differs')
    require(sha(Path(geometry.__file__).resolve()) == scope['geometry_code_pin']['sha256'], 'Exact geometry helper code differs')
    archived_driver = auth(root, scope['geometry_driver_archive_pin'])
    require(sha(archived_driver) == geom['geometry_driver']['sha256'] and
            archived_driver.stat().st_size == geom['geometry_driver']['bytes'], 'Original metadata geometry driver archive differs')
    inputs = root / 'seti_work'
    matrix = read(inputs / MATRIX)
    old_profiles_path = auth(root, scope['old_profiles_pin'])
    old_profiles = read(old_profiles_path)
    old_injections = read(auth(root, scope['old_injections_pin']))
    require([p['profile_id'] for p in geom['profiles']] == [p['profile_id'] for p in matrix['profiles']]
            == [p['profile_id'] for p in old_profiles['profiles']] and len(matrix['profiles']) == 54, 'Complete profile order differs')
    require(len(old_injections['trials']) == 3024 and old_injections['count'] == 3024, 'Frozen legacy injection census differs')
    old_results = old_profiles_path.parent
    support_lo, support_hi = 12096, 0
    for profile, family, previous in zip(matrix['profiles'], geom['profiles'], old_profiles['profiles']):
        track = profile['selected_track']
        require(track['width_channels'] == 1 and track['window_length_rows'] == 4 and
                family['times_from_primary_reference_s'] == profile['times_from_primary_reference_s'] and
                family['source_reference_channel'] == track['source_reference_channel'] and
                family['original_drift_hz_s'] == track['drift_hz_s'], 'Exact family physical metadata differs')
        crop = next(c for c in matrix['normalization_crops'] if c['crop_id'] == profile['normalization_crop_id'])
        channel0, stop = crop['source_channel_interval_half_open']
        require(stop - channel0 == 12096 and crop['normalization_source_channel_interval_half_open'] == [channel0 + 4000, channel0 + 8096], 'Original normalization core differs')
        auth(inputs, profile['raw_normalization_crop']);auth(inputs, profile['normalization'])
        auth(old_results, previous['family_arrays'])
        for window in family['windows']:
            require(window['unique_paths'] == len(window['paths']) <= 10000, 'Per-window path cap differs')
            for path in window['paths']:
                lo, hi = min(path['channels']) - 1024 - 250, max(path['channels']) + 1024 + 250
                require(lo >= channel0 and hi < stop, 'Exact native path lacks unchanged raw501 support')
                support_lo, support_hi = min(support_lo, lo - channel0), max(support_hi, hi - channel0)
    return root, scope_path, scope, inputs, matrix, geom_path, geom, old_results, old_profiles, old_injections, [support_lo, support_hi]


def recompute_normal(raw):
    """Authenticate original per-row4096 core, direct501 local median filter."""
    power = raw[:, 3750:8346].astype(np.float64)
    level = np.median(power[:, 250:4346], axis=1)
    residual = np.empty((16, 4096), dtype=np.float64)
    for row in range(16):
        ratio = power[row] / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(ratio, 501)
        for start in range(0, 4096, 256):
            stop = min(start + 256, 4096)
            residual[row, start:stop] = ratio[250 + start:250 + stop] - np.median(windows[start:stop], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    return dict(row_power_median=level, row_residual_median=center, row_residual_MAD_scale=scale,
                row_winsorized_residual_location=location)


def path_arrays(family, raw, normal, channel0):
    paths, rows, window_indices = [], [], []
    for window in family['windows']:
        for path in window['paths']:
            paths.append(path['channels']);rows.append(window['window_source_rows']);window_indices.append(window['window_index'])
    row_axis = np.asarray(rows, dtype=np.int64)
    channels = np.asarray(paths, dtype=np.int64)[None, :, :] + np.asarray(OFFSETS, dtype=np.int64)[:, None, None]
    local = channels - channel0
    require(local.min() >= 250 and local.max() + 250 < 12096, 'Exact path501 support outside saved crop')
    terms = np.empty_like(channels, dtype=np.float64)
    unique_counts = []
    for row in range(16):
        where = row_axis == row
        positions = local[:, where]
        unique, inverse = np.unique(positions, return_inverse=True)
        ratio = raw[row].astype(np.float64) / normal['row_power_median'][row]
        medians = np.median(np.lib.stride_tricks.sliding_window_view(ratio, 501)[unique - 250], axis=1)
        residuals = (ratio[unique] - medians - normal['row_winsorized_residual_location'][row]) / normal['row_residual_MAD_scale'][row]
        terms[:, where] = residuals[inverse].reshape(9, -1)
        unique_counts.append(len(unique))
    scores = terms.sum(axis=-1, dtype=np.float64) / 2
    row_dc = np.isin(channels, np.asarray(DC, dtype=np.int64))
    return {'absolute_channels': channels, 'residual_row_terms': terms, 'scores': scores,
            'row_dc_mask': row_dc, 'path_dc_mask': row_dc.any(axis=-1),
            'path_window_index': np.asarray(window_indices, dtype=np.int64), 'path_source_rows': row_axis,
            'offset_channels': np.asarray(OFFSETS, dtype=np.int64),
            'row501_unique_center_counts': np.asarray(unique_counts, dtype=np.int64)}


def flattened_paths(family):
    return [path for window in family['windows'] for path in window['paths']]


def exact_winner(scores, arrays, family, offset_index, fixed_window_index=None):
    invalid = arrays['path_dc_mask'][offset_index].copy()
    if fixed_window_index is not None:
        invalid |= arrays['path_window_index'] != fixed_window_index
    index = int(np.argmax(np.where(invalid, -np.inf, scores)))
    require(not invalid[index] and math.isfinite(float(scores[index])), 'No eligible exact finite path')
    path = flattened_paths(family)[index]
    wi = int(arrays['path_window_index'][index]);offset = OFFSETS[offset_index]
    full16 = geometry.witness_centers(family['source_reference_channel'], family['original_drift_hz_s'],
                                      family['times_from_primary_reference_s'], DF,
                                      path['delta_drift_fraction'], path['phase_fraction'], offset)
    return {'score': float(scores[index]), 'path_index': index, 'window_index': wi,
            'window_start_row': WINDOW_STARTS[wi], 'window_source_rows': arrays['path_source_rows'][index].tolist(),
            'offset_channels': offset, 'selected4_absolute_centers': arrays['absolute_channels'][offset_index, index].tolist(),
            'absolute_channels': arrays['absolute_channels'][offset_index, index].tolist(),
            'witness_delta_drift_fraction': path['delta_drift_fraction'], 'witness_phase_fraction': path['phase_fraction'],
            'witness_delta_drift_hz_s_display': float(geometry.decode(path['delta_drift_fraction'])),
            'witness_phase_channels_display': float(geometry.decode(path['phase_fraction'])),
            'witness_stratum_dimension': path['witness_stratum_dimension'], 'tie_row_indices_in_window': path['tie_row_indices_in_window'],
            'witness_full16_absolute_centers': full16, 'selected4_dc_contact': bool(arrays['path_dc_mask'][offset_index, index]),
            'witness_full16_dc_contact': any(c in DC for c in full16),
            'representative_witness_not_unique_drift_fit': True}


def summarize(profile, family, arrays, previous, old_arrays):
    fixed_i = WINDOW_STARTS.index(profile['selected_track']['window_start_row'])
    path_lookup = [{tuple(path['channels']): sum(w['unique_paths'] for w in family['windows'][:wi]) + j
                    for j, path in enumerate(window['paths'])}
                   for wi, window in enumerate(family['windows'])]
    legacy_max_error = 0.
    for wi, window in enumerate(family['windows']):
        rows = window['window_source_rows']
        for hi in range(405):
            old_path = tuple(old_arrays['rounded_absolute_centers'][0, hi, rows].tolist())
            if old_path in path_lookup[wi]:
                pi = path_lookup[wi][old_path]
                deviation = float(np.max(np.abs(arrays['scores'][:, pi] - old_arrays['scores'][:, hi, wi])))
                legacy_max_error = max(legacy_max_error, deviation)
                require(deviation <= ATOL, 'Legacy path score not reproduced by exact native-channel recomputation')
    offsets = []
    for oi, offset in enumerate(OFFSETS):
        old = previous['offset_results'][oi]
        offsets.append({'offset_channels': offset,
                        'original_d0_phase0_original4_score': old['fixed_d0_phase0_original4_score'],
                        'legacy_fine_fixed_original4': old['fine_fixed_original4'],
                        'legacy_fine_max7': old['fine_max7'],
                        'exact_fixed_original4': exact_winner(arrays['scores'][oi], arrays, family, oi, fixed_i),
                        'exact_max7': exact_winner(arrays['scores'][oi], arrays, family, oi),
                        'excluded_selected4_paths': int(arrays['path_dc_mask'][oi, arrays['path_window_index'] == fixed_i].sum()),
                        'excluded_all7_paths': int(arrays['path_dc_mask'][oi].sum())})
    ranks = {}
    for prefix, field in (('fixed_original4', 'exact_fixed_original4'), ('max7', 'exact_max7')):
        target = offsets[0][field]['score']
        greater = sum(o[field]['score'] > target for o in offsets[1:])
        equal = sum(o[field]['score'] == target for o in offsets[1:])
        ranks.update({prefix + '_control_strictly_greater_count': greater, prefix + '_control_equal_count': equal,
                      prefix + '_rank_among_target_plus8': 1 + greater})
    return {'profile_id': profile['profile_id'], 'origin_scan_id': family['origin_scan_id'],
            'context_scan_id': family['context_scan_id'], 'origin_rank': family['origin_rank'],
            'original_window_start_row': profile['selected_track']['window_start_row'],
            'original_fixed_four_row_score': profile['fixed_four_row_score'], 'original_width_channels': 1,
            'times_from_primary_reference_s': family['times_from_primary_reference_s'],
            'coarse_zero_offset_full16_absolute_centers': previous['coarse_zero_offset_full16_absolute_centers'],
            'exact_fixed4_zero_offset_witness_full16_absolute_centers': offsets[0]['exact_fixed_original4']['witness_full16_absolute_centers'],
            'exact_max7_zero_offset_witness_full16_absolute_centers': offsets[0]['exact_max7']['witness_full16_absolute_centers'],
            'unique_path_counts_by_window': [w['unique_paths'] for w in family['windows']],
            'total_unique_paths_all7': sum(w['unique_paths'] for w in family['windows']),
            'legacy_only_float_paths': sum(len(w['legacy_only_float_paths']) for w in family['windows']),
            'legacy_path_max_absolute_score_difference': legacy_max_error,
            'offset_results': offsets, 'control_ranks': ranks, 'raw_sensitivity_or_FAP_established': False}


def injection_trials(family, arrays, old_trials):
    host = OFFSETS.index(512)
    base_scores = arrays['scores'][host]
    zero = exact_winner(base_scores, arrays, family, host)
    row_indices = arrays['path_source_rows']
    channels = arrays['absolute_channels'][host]
    lookup = [{tuple(path['channels']) for path in window['paths']} for window in family['windows']]
    result = []
    for old in old_trials:
        true_wi = old['true_window_index']
        active = np.zeros(16, dtype=bool);active[old['true_active_source_rows']] = True
        truth = np.asarray(old['true_absolute_centers'], dtype=np.int64)
        matched = (channels == truth[row_indices]) & active[row_indices]
        counts = matched.sum(axis=1, dtype=np.int64)
        amp = old['amplitude_per_active_standardized_single_bin']
        injected = base_scores + amp * counts / 2
        best = exact_winner(injected, arrays, family, host)
        signal_index = int(np.argmax(np.where(arrays['path_dc_mask'][host], -1, counts)))
        signal_count = int(counts[signal_index])
        true_path = tuple(int(truth[row] - 512) for row in old['true_active_source_rows'])
        fraction = geometry.exact(old['true_drift_fraction_of_half_original_step'])
        rational_delta = fraction * geometry.exact(HALF_DRIFT)
        rational_truth = geometry.witness_centers(family['source_reference_channel'], family['original_drift_hz_s'],
                                                 family['times_from_primary_reference_s'], DF,
                                                 geometry.encode(rational_delta), geometry.encode(geometry.exact(old['true_phase_channels'])), 512)
        result.append({'profile_id': family['profile_id'], 'origin_scan_id': family['origin_scan_id'],
                       'context_scan_id': family['context_scan_id'], 'origin_rank': family['origin_rank'],
                       'host_offset_channels': 512,
                       'true_drift_fraction_of_half_original_step': old['true_drift_fraction_of_half_original_step'],
                       'true_drift_hz_s': old['true_drift_hz_s'], 'true_phase_channels': old['true_phase_channels'],
                       'true_window_index': true_wi, 'true_window_start_row': old['true_window_start_row'],
                       'true_active_source_rows': old['true_active_source_rows'],
                       'canonical_float_truth_absolute_centers': old['true_absolute_centers'],
                       'canonical_rational_truth_absolute_centers': rational_truth,
                       'canonical_float_vs_rational_active4_different_channel_count': sum(int(truth[row]) != rational_truth[row] for row in old['true_active_source_rows']),
                       'canonical_float_truth_active4_path_attainable_exact': true_path in lookup[true_wi],
                       'amplitude_per_active_standardized_single_bin': amp,
                       'exact_score': best['score'], 'exact_zero_injection_max7_score': zero['score'],
                       'exact_max7_uplift': best['score'] - zero['score'], 'exact_winner': best,
                       'exact_winner_matches_true_activity_window': best['window_index'] == true_wi,
                       'exact_winner_matching_active4_count': int(counts[best['path_index']]),
                       'exact_winner_matching_active4_fraction': int(counts[best['path_index']]) / 4,
                       'signal_only_exact_best_matching_active4_count': signal_count,
                       'signal_only_exact_best_matched_row_fraction': signal_count / 4,
                       'signal_only_exact_best_path_index': signal_index,
                       'signal_only_exact_best_window_index': int(arrays['path_window_index'][signal_index]),
                       'signal_only_exact_best_matches_true_activity_window': int(arrays['path_window_index'][signal_index]) == true_wi,
                       'legacy_fine_score': old['fine_score'],
                       'legacy_fine_zero_injection_max7_score': old['fine_zero_injection_max7_score'],
                       'legacy_fine_max7_uplift': old['fine_max7_uplift'],
                       'legacy_fine_winner_matches_true_activity_window': old['fine_winner_matches_true_activity_window'],
                       'legacy_fine_winner_matching_active4_count': old['fine_winner_matching_active4_count'],
                       'legacy_signal_only_fine_best_matched_row_fraction': old['signal_only_fine_best_matched_row_fraction'],
                       'coarse_max7_score': old['coarse_max7_score'], 'coarse_truewindow_score': old['coarse_truewindow_score'],
                       'coarse_truewindow_signal_only_matched_row_fraction': old['coarse_truewindow_signal_only_matched_row_fraction'],
                       'model': 'additive_standardized_residual_native_delta_bin_frozen_normalization',
                       'raw_sensitivity_or_FAP_established': False})
    require(len(result) == 56, 'Per-profile exact injection trial census differs')
    return result


def write_csv(path, records):
    import csv
    flat = [{k: json.dumps(v, separators=(',', ':'), sort_keys=True, allow_nan=False)
             if isinstance(v, (dict, list, tuple)) else v for k, v in record.items()} for record in records]
    with Path(path).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)


def observed_production(args):
    started = time.monotonic()
    root, scope_path, scope, inputs, matrix, geom_path, geom, old_results, old_profiles, old_injections, support = read_observed_metadata(args)
    code = Path(__file__).resolve()
    if args.check_only:
        print(json.dumps({'status': 'PASS_TEXT_ONLY_EXACT_ROUNDING_OBSERVED_INTERFACE',
                          'scope_sha256': sha(scope_path), 'code_sha256': sha(code), 'geometry_sha256': sha(geom_path),
                          'raw_spectral_arrays_opened': False, 'numerical_modules_imported': False,
                          'profiles': 54, 'exact_paths_zero_offset': 22235, 'exact_paths_all_offsets': 200115,
                          'legacy_grid_hypotheses_per_window': 405, 'injection_trials': 3024,
                          'raw501_local_support_inclusive': support, 'portable_inputs': args.portable_inputs}))
        return
    require(args.scope_sha256 == sha(scope_path) and args.code_sha256 == sha(code)
            and args.geometry_sha256 == sha(geom_path), 'Exact root scope/code/geometry gates required')
    go_path = scope_path.parent / 'GO.json'
    require(args.root_go_sha256 is not None and sha(go_path) == args.root_go_sha256, 'Exact root GO byte pin required')
    go = read(go_path)
    require(go['status'] == 'GO_EXACT_CONTINUOUS_ROUNDING_OBSERVED' and go['scope_sha256'] == args.scope_sha256
            and go['code_sha256'] == args.code_sha256 and go['geometry_sha256'] == args.geometry_sha256, 'Root observed GO fields differ')
    out = Path(args.output_dir).resolve()
    require(not out.exists() and not out.is_relative_to(inputs), 'Fresh observed outputs outside original input tree required')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP));resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Observed wall budget exceeded')))
    signal.alarm(max(1, WALL_CAP - math.ceil(time.monotonic() - started)))
    global np
    import numpy as np
    out.mkdir(parents=True);(out / 'profiles').mkdir()
    grouped = {p['profile_id']: [] for p in matrix['profiles']}
    for trial in old_injections['trials']:
        grouped[trial['profile_id']].append(trial)
    summaries, trials, norm_checks, output_pins = [], [], [], []
    for pi, (profile, family, previous) in enumerate(zip(matrix['profiles'], geom['profiles'], old_profiles['profiles'])):
        with np.load(inputs / profile['raw_normalization_crop']['path'], allow_pickle=False) as archive:
            raw, channel0 = archive['raw_power'], int(archive['source_channel0'])
            require(raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4') and np.isfinite(raw).all(), 'Raw power source crop invalid')
            require(np.array_equal(archive['absolute_time_rows'], np.arange(16)) and
                    np.array_equal(archive['normalization_source_channels'], np.arange(channel0 + 4000, channel0 + 8096)), 'Original core coordinate fields differ')
        saved = read(inputs / profile['normalization']['path'])
        normal = {key: np.asarray(saved[key], dtype=np.float64) for key in NORM_FIELDS}
        expected = recompute_normal(raw)
        errors = {key: float(np.max(np.abs(normal[key] - expected[key]))) for key in NORM_FIELDS}
        require(all(math.isfinite(error) and error <= ATOL for error in errors.values()), 'Original fixed normalization authentication failed')
        norm_checks.append({'profile_id': profile['profile_id'], 'max_absolute_errors': errors,
                            'original_core_local_interval_half_open': [4000, 8096], 'reused_saved_parameters': True})
        arrays = path_arrays(family, raw, normal, channel0)
        with np.load(old_results / previous['family_arrays']['path'], allow_pickle=False) as archive:
            old_arrays = {key: archive[key] for key in ('rounded_absolute_centers', 'scores')}
        summary = summarize(profile, family, arrays, previous, old_arrays)
        path = out / 'profiles' / (profile['profile_id'] + '_paths.npz')
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        declared = pin(path, out);output_pins.append(declared)
        summary['path_arrays'] = declared
        summary['input_raw_crop'] = profile['raw_normalization_crop'];summary['input_normalization'] = profile['normalization']
        summaries.append(summary);trials.extend(injection_trials(family, arrays, grouped[profile['profile_id']]))
        if (pi + 1) % 6 == 0:
            print(json.dumps({'observed_exact_profiles_completed': pi + 1, 'profiles_total': 54}), flush=True)
    require(len(trials) == 3024, 'Exact injection total census differs')
    result = {'schema': 'SETI_EXACT_CONTINUOUS_ROUNDING_OBSERVED_PROFILES_V1', 'status': 'COMPLETE_54_EXACT_ATTAINABLE_PATH_PROFILES',
              'scope_sha256': args.scope_sha256, 'code_sha256': args.code_sha256, 'geometry_sha256': args.geometry_sha256,
              'primary_statistic': 'maximum_exact_native4path_score_at_original_selected_window',
              'secondary_statistic': 'maximum_exact_native4path_score_across7windows',
              'path_order': geom['path_order'], 'tie_policy': 'first_array_index_window_major_path_tuple_lexicographic',
              'offset_channels': list(OFFSETS), 'window_start_rows': list(WINDOW_STARTS),
              'geometry_counts': geom['counts'], 'profiles': summaries, 'normalization_authentication': norm_checks,
              'representative_witnesses_are_not_unique_physical_drift_fits': True,
              'witness_stratum_dimension_is_not_path_feasible_region_dimension': True,
              'exact_canonical_and_legacy_float_models_kept_separate': True,
              'selected4_DC_veto_preserves_raw_and_saved_scores': True,
              'posthoc_selection_conditioned': True, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
              'physical_sensitivity_established': False, 'new_observation': False}
    injected = {'schema': 'SETI_EXACT_ROUNDING_RESIDUAL_DOMAIN_INJECTION_V1', 'count': 3024, 'trials': trials,
                'canonical_float_truth_reused_from_authenticated_prior_trials': True,
                'instrumental_line_response_modeled': False, 'raw_sensitivity_or_FAP_established': False}
    # Serialize all metadata first so scalar/type failures cannot leave partial deliverables.
    json.dumps(result, allow_nan=False);json.dumps(injected, allow_nan=False)
    create_json(out / 'PROFILES.json', result);write_csv(out / 'PROFILES.csv', summaries)
    create_json(out / 'INJECTIONS.json', injected);write_csv(out / 'INJECTIONS.csv', trials)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': 'COMPLETE_BOUNDED_EXACT_CONTINUOUS_ROUNDING_PRODUCTION',
               'scope': pin(scope_path), 'producer': pin(code), 'geometry_code': pin(Path(geometry.__file__).resolve()),
               'geometry': scope['geometry_pin'], 'root_go': pin(go_path), 'source_matrix': pin(inputs / MATRIX),
               'portable_inputs': args.portable_inputs, 'actual_workspace_root': str(root),
               'original_scope_input_root': scope['source_root'],
               'profiles': 54, 'exact_paths_zero_offset': 22235, 'exact_paths_all_offsets': 200115,
               'row_residual_terms_saved': 200115 * 4, 'injection_trials': 3024,
               'original_normalization_reused': True, 'new_raw_median501_centers_recomputed': True,
               'original_input_package_modified': False, 'raw_data_modified': False,
               'resource_limits': {'CPU_s': CPU_CAP, 'wall_s': WALL_CAP, 'memory_bytes': MEMORY_CAP},
               'resource_usage': {'CPU_s': usage.ru_utime + usage.ru_stime, 'wall_s': time.monotonic() - started,
                                  'peak_RSS_bytes': usage.ru_maxrss * 1024},
               'outputs': output_pins + [pin(out / name, out) for name in ('PROFILES.json', 'PROFILES.csv', 'INJECTIONS.json', 'INJECTIONS.csv')],
               'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}
    create_json(out / 'EXECUTION_RECEIPT.json', receipt);signal.alarm(0)
    print(json.dumps({'status': receipt['status'], 'resource_usage': receipt['resource_usage']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--geometry-preflight', action='store_true')
    parser.add_argument('--geometry-config')
    parser.add_argument('--geometry-output-dir')
    parser.add_argument('--scope')
    parser.add_argument('--portable-inputs', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output-dir')
    for name in ('scope-sha256', 'code-sha256', 'geometry-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    if args.geometry_preflight:
        require(args.geometry_config and args.geometry_output_dir, 'Geometry config/fresh output required')
        geometry_preflight(args)
    else:
        require(args.scope and (args.check_only or args.output_dir), 'Frozen scope and fresh observed outputs required')
        observed_production(args)


if __name__ == '__main__':
    main()
