"""Frozen, bounded local drift/phase follow-up from authenticated saved crops.

Check-only reads JSON, hashes and NumPy archive headers, never spectral cells and
never imports a numerical library. Execution requires the exact scope and this
code's hashes. This producer does not import detector/context producer code.
Residual-domain delta-bin injections are an explicit software transport test;
they do not model the telescope response or establish sensitivity or FAP.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time
import zipfile

sys.dont_write_bytecode = True
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

MATRIX = 'seti_burst_full/context_results/CONTEXT_PROFILES.json'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
DF = -2.7939677238464355
TSAMP = 18.253611008
CORE, HALO, MEDIAN_WIDTH = 4096, 4000, 501
DC = (178782208, 179830784, 180879360)
PHASES = (-.5, -.25, 0., .25, .5)
OFFSETS = (0, -1024, -768, -512, -256, 256, 512, 768, 1024)
WINDOW_STARTS = (0, 2, 4, 6, 8, 10, 12)
DRIFT_FRACTIONS = (-.73, .61)
INJECTION_PHASES = (-.37, .29)
AMPLITUDES = (2., 8.)
CPU_CAP, WALL_CAP, MEMORY_CAP = 600, 900, 2 * 1024**3
NORM_FIELDS = ('row_power_median', 'row_residual_median', 'row_residual_MAD_scale', 'row_winsorized_residual_location')
ATOL = 1e-7


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_pairs(items):
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON key: ' + key)
        value[key] = item
    return value


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + x)))


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def confined(root, name):
    value = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            value.resolve().is_relative_to(root) and not value.is_symlink(), 'Confined input path required')
    return value


def authenticate(root, declaration):
    path = confined(root, declaration['path'])
    require(path.is_file() and path.stat().st_size == declaration['bytes'] and
            sha256(path) == declaration['sha256'], 'Input pin differs: ' + declaration['path'])
    return path


def pin(path, root=None):
    return {'path': path.relative_to(root).as_posix() if root else str(path),
            'bytes': path.stat().st_size, 'sha256': sha256(path)}


def create_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def npz_schema(path):
    """Read only literal .npy headers; no array values."""
    result = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            require(name.endswith('.npy') and '/' not in name, 'Unexpected NPZ member')
            with archive.open(name) as stream:
                require(stream.read(6) == b'\x93NUMPY', 'NumPy header magic differs')
                version = tuple(stream.read(2))
                require(version in ((1, 0), (2, 0), (3, 0)), 'NumPy version differs')
                size = struct.unpack('<H' if version == (1, 0) else '<I', stream.read(2 if version == (1, 0) else 4))[0]
                require(size <= 10000, 'Oversized NumPy header')
                header = ast.literal_eval(stream.read(size).decode('utf-8' if version == (3, 0) else 'latin1').strip())
                require(not header['fortran_order'], 'Fortran-order input unsupported')
                result[name[:-4]] = {'dtype': header['descr'], 'shape': list(header['shape'])}
    return result


def validate_metadata(root, scope_path, portable_inputs=False):
    scope = read_json(scope_path)
    require((portable_inputs or scope['source_root'] == str(root)) and scope['matrix_path'] == MATRIX, 'Frozen input location differs')
    geometry = scope['geometry']
    require(geometry['drift_count'] == 81 and geometry['drift_half_step_hz_s'] == 4 / 158
            and geometry['phase_channels'] == list(PHASES) and geometry['offset_channels'] == list(OFFSETS)
            and geometry['window_start_rows'] == list(WINDOW_STARTS) and geometry['df_hz'] == DF
            and geometry['tsamp_s'] == TSAMP and geometry['width_channels'] == 1
            and geometry['window_length_rows'] == 4 and geometry['dc_channels'] == list(DC), 'Frozen geometry differs')
    require(scope['injections']['cases'] == 3024 and scope['injections']['host_offset_channels'] == 512
            and scope['injections']['drift_fractions_of_half_step'] == list(DRIFT_FRACTIONS)
            and scope['injections']['phase_channels'] == list(INJECTION_PHASES)
            and scope['injections']['amplitudes_per_active_standardized_single_bin'] == list(AMPLITUDES), 'Frozen injection geometry differs')
    matrix = read_json(root / MATRIX)
    require([p['profile_id'] for p in matrix['profiles']] == scope['profile_ids'], 'Frozen profile order differs')
    require(matrix['status'] == 'COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS', 'Input context status differs')
    require(len(matrix['profiles']) == 54 and len(matrix['selected_tracks']) == 9 and len(matrix['normalization_crops']) == 54, 'Input census differs')
    # Root scope may list explicit input pins under input_pins, or source_matrix.
    declared_pins = scope.get('input_pins', [])
    if isinstance(declared_pins, dict):
        declared_pins = list(declared_pins.values())
    for declaration in declared_pins:
        if isinstance(declaration, dict) and all(k in declaration for k in ('path', 'bytes', 'sha256')):
            authenticate(root, declaration)
    for key in ('source_matrix', 'matrix'):
        declaration = scope.get(key)
        if isinstance(declaration, dict) and all(k in declaration for k in ('path', 'bytes', 'sha256')):
            require(declaration['path'] == MATRIX, 'Frozen matrix path differs')
            authenticate(root, declaration)
    headers = {}
    for source in matrix['source_compacts']:
        header = source['original_header']
        require(header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP, 'Original source spacing differs')
        label = source['scan_id']
        require(label in SCANS and header == headers.get(label, header), 'Across-band header differs')
        require(source['source_channel0'] == source['native_chunk_index'] * 1048576 and source['shape'] == [16, 1, 1048576], 'Source support geometry differs')
        require([r['time_row'] for r in source['decoded_rows']] == list(range(16)) and all(r['decoded_bytes'] == 1048576 * 4 for r in source['decoded_rows']), 'Source row provenance differs')
        headers[label] = header
    require(set(headers) == set(SCANS), 'Six original headers required')
    sources = {item['path']: item for item in matrix['source_compacts']}
    crops = {item['crop_id']: item for item in matrix['normalization_crops']}
    require(len(crops) == 54, 'Duplicate crop IDs')
    authenticated = {}
    support_span = [math.inf, -math.inf]
    for profile in matrix['profiles']:
        track = profile['selected_track']
        require(track['width_channels'] == 1 and track['window_length_rows'] == 4 and track['window_start_row'] in WINDOW_STARTS, 'Only selected width1 four-row queries allowed')
        r0 = track['window_start_row']
        origin, scan = track['scan_id'], profile['context_scan_id']
        require(scan in SCANS and origin in SCANS and origin.endswith('_on'), 'Original acquisition role differs')
        require(track['source_header'] == headers[origin], 'Origin source header differs')
        require(track['reference_time_mjd'] == headers[origin]['tstart'] + (r0 + .5) * TSAMP / 86400,
                'Original selected first-row midpoint anchor differs')
        times = [(headers[scan]['tstart'] - headers[origin]['tstart']) * 86400 + (row - r0) * TSAMP for row in range(16)]
        require(profile['times_from_primary_reference_s'] == times, 'Actual gap time vector differs')
        require(profile['window_source_rows'] == list(range(r0, r0 + 4)), 'Original selected window differs')
        crop = crops[profile['normalization_crop_id']]
        require(crop['scan_id'] == scan and crop['raw_crop'] == profile['raw_normalization_crop'] and crop['normalization'] == profile['normalization'], 'Crop/profile provenance differs')
        channel0, stop = crop['source_channel_interval_half_open']
        require(stop - channel0 == 12096 and crop['normalization_source_channel_interval_half_open'] == [channel0 + HALO, channel0 + HALO + CORE], 'Original normalization core differs')
        pieces = []
        for support in crop['source_support']:
            original = sources[support['path']]
            require(original['scan_id'] == scan and support['sha256'] == original['sha256'] and support['source_channel0'] == original['source_channel0'] and support['original_decoded_rows'] == original['decoded_rows'], 'Crop source-support declaration differs')
            lo = max(channel0, original['source_channel0'])
            hi = min(stop, original['source_channel0'] + 1048576)
            require(hi > lo, 'Unnecessary or invalid source support')
            pieces.append((lo, hi))
        cursor = channel0
        for lo, hi in sorted(pieces):
            require(lo == cursor, 'Crop source support has gap/overlap')
            cursor = hi
        require(cursor == stop and len(pieces) in (1, 2), 'Incomplete crop source support')
        for declaration in (profile['raw_normalization_crop'], profile['normalization'], profile['raw_capsule']):
            if declaration['path'] not in authenticated:
                path = authenticate(root, declaration)
                authenticated[declaration['path']] = declaration
                if path.suffix == '.npz':
                    schema = npz_schema(path)
                    if declaration == profile['raw_normalization_crop']:
                        require(schema == {'raw_power': {'dtype': '<f4', 'shape': [16, 12096]},
                                           'source_channel0': {'dtype': '<i8', 'shape': []},
                                           'normalization_source_channels': {'dtype': '<i8', 'shape': [4096]},
                                           'absolute_time_rows': {'dtype': '<i8', 'shape': [16]}}, 'Raw normalization NPZ schema differs')
        normal = read_json(root / profile['normalization']['path'])
        require(set(normal) == set(NORM_FIELDS) | {'normalization_unmasked_counts', 'normalization_source_channels'}, 'Normalization fields differ')
        require(normal['normalization_source_channels'] == list(range(channel0 + HALO, channel0 + HALO + CORE)) and normal['normalization_unmasked_counts'] == [4096] * 16, 'Normalization unchanged support differs')
        for field in NORM_FIELDS:
            require(len(normal[field]) == 16 and all(math.isfinite(x) for x in normal[field]), 'Normalization row parameters differ')
        require(all(x > 0 for x in normal['row_power_median']) and all(x > 0 for x in normal['row_residual_MAD_scale']), 'Original normalization scale nonpositive')
        # The exact family support calculation is metadata-only and does not read spectral cells.
        base = track['source_reference_channel']
        d0 = track['drift_hz_s']
        centers = [round(base + offset + phase + drift * t / DF)
                   for offset in OFFSETS for phase in PHASES for drift in (d0 - 4 / 158, d0 + 4 / 158) for t in times]
        lo, hi = min(centers) - 250, max(centers) + 250
        require(lo >= channel0 and hi < stop, 'Frozen family row501 support outside unchanged crop')
        support_span = [min(support_span[0], lo - channel0), max(support_span[1], hi - channel0)]
    return scope, matrix, headers, list(authenticated.values()), support_span


def recompute_normal(raw):
    """Direct running medians on the original core only, not the expanded family."""
    power = raw[:, HALO - 250:HALO + CORE + 250].astype(np.float64)
    level = np.median(power[:, 250:250 + CORE], axis=1)
    residual = np.empty((16, CORE), dtype=np.float64)
    for row in range(16):
        ratio = power[row] / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(ratio, MEDIAN_WIDTH)
        for start in range(0, CORE, 256):
            stop = min(start + 256, CORE)
            residual[row, start:stop] = ratio[250 + start:250 + stop] - np.median(windows[start:stop], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    return {'row_power_median': level, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location}


def family_arrays(profile, raw, normal, channel0):
    track = profile['selected_track']
    times = np.asarray(profile['times_from_primary_reference_s'], dtype=np.float64)
    drifts = track['drift_hz_s'] + np.linspace(-4 / 158, 4 / 158, 81, dtype=np.float64)
    drift_axis = np.repeat(drifts, 5)
    phase_axis = np.tile(np.asarray(PHASES, dtype=np.float64), 81)
    centers = np.rint(track['source_reference_channel'] + np.asarray(OFFSETS)[:, None, None] + phase_axis[None, :, None]
                      + drift_axis[None, :, None] * times[None, None, :] / DF).astype(np.int64)
    local = centers - channel0
    require(local.min() >= 250 and local.max() + 250 < 12096, 'Family row501 support outside saved crop')
    terms = np.empty_like(centers, dtype=np.float64)
    median_counts = []
    for row in range(16):
        unique, inverse = np.unique(local[:, :, row], return_inverse=True)
        ratio = raw[row].astype(np.float64) / normal['row_power_median'][row]
        windows = np.lib.stride_tricks.sliding_window_view(ratio, MEDIAN_WIDTH)
        medians = np.median(windows[unique - 250], axis=1)
        z = (ratio[unique] - medians - normal['row_winsorized_residual_location'][row]) / normal['row_residual_MAD_scale'][row]
        terms[:, :, row] = z[inverse].reshape(9, 405)
        median_counts.append(len(unique))
    windows = np.asarray([range(start, start + 4) for start in WINDOW_STARTS], dtype=np.int64)
    scores = terms[:, :, windows].sum(axis=-1, dtype=np.float64) / 2
    row_dc = np.isin(centers, np.asarray(DC, dtype=np.int64))
    window_dc = row_dc[:, :, windows].any(axis=-1)
    return {'residual_row_terms': terms, 'rounded_absolute_centers': centers,
            'scores': scores, 'row_dc_mask': row_dc, 'window_dc_mask': window_dc,
            'family_drift_hz_s': drift_axis, 'family_phase_channels': phase_axis,
            'offset_channels': np.asarray(OFFSETS, dtype=np.int64), 'window_start_rows': np.asarray(WINDOW_STARTS, dtype=np.int64),
            'window_source_rows': windows, 'times_from_primary_reference_s': times,
            'row501_unique_center_counts': np.asarray(median_counts, dtype=np.int64)}


def winner(scores, invalid, arrays, offset_i, fixed_window_i=None):
    if fixed_window_i is None:
        eligible = np.where(invalid, -np.inf, scores)
        flat = int(np.argmax(eligible))
        h, w = np.unravel_index(flat, eligible.shape)
    else:
        eligible = np.where(invalid[:, fixed_window_i], -np.inf, scores[:, fixed_window_i])
        h, w = int(np.argmax(eligible)), fixed_window_i
    require(math.isfinite(float(scores[h, w])) and not invalid[h, w], 'No eligible finite winner')
    return {'score': float(scores[h, w]), 'hypothesis_index': int(h), 'drift_index': int(h // 5), 'phase_index': int(h % 5),
            'drift_hz_s': float(arrays['family_drift_hz_s'][h]), 'phase_channels': float(arrays['family_phase_channels'][h]),
            'window_index': int(w), 'window_start_row': int(WINDOW_STARTS[w]), 'offset_channels': int(OFFSETS[offset_i]),
            'selected4_dc_contact': bool(invalid[h, w]), 'full16_dc_contact': bool(arrays['row_dc_mask'][offset_i, h].any()),
            'selected4_absolute_centers': arrays['rounded_absolute_centers'][offset_i, h, arrays['window_source_rows'][w]].tolist()}


def summarize_profile(profile, arrays):
    r0 = profile['selected_track']['window_start_row']
    fixed_i = WINDOW_STARTS.index(r0)
    scores, mask = arrays['scores'], arrays['window_dc_mask']
    records = []
    for oi, offset in enumerate(OFFSETS):
        baseline_scores = scores[oi, 202]
        coarse_mask = np.ones_like(mask[oi])
        coarse_mask[202] = mask[oi, 202]
        records.append({'offset_channels': offset,
                        'fixed_d0_phase0_original4_score': float(baseline_scores[fixed_i]),
                        'fixed_d0_phase0_original4_dc_eligible': not bool(mask[oi, 202, fixed_i]),
                        'fixed_d0_phase0_max7': winner(scores[oi], coarse_mask, arrays, oi),
                        'fine_fixed_original4': winner(scores[oi], mask[oi], arrays, oi, fixed_i),
                        'fine_max7': winner(scores[oi], mask[oi], arrays, oi),
                        'excluded_original4_hypotheses': int(mask[oi, :, fixed_i].sum()),
                        'excluded_all7_hypothesis_windows': int(mask[oi].sum()),
                        'full16_contact_hypotheses': int(arrays['row_dc_mask'][oi].any(axis=-1).sum())})
    target_fixed = records[0]['fine_fixed_original4']['score']
    target_all = records[0]['fine_max7']['score']
    # Descriptive control ranks use descending scores; greater-than counts are
    # strict, ties are separately reported. They are not calibrated p-values.
    rank = {'fixed_original4_control_strictly_greater_count': sum(r['fine_fixed_original4']['score'] > target_fixed for r in records[1:]),
            'fixed_original4_control_equal_count': sum(r['fine_fixed_original4']['score'] == target_fixed for r in records[1:]),
            'max7_control_strictly_greater_count': sum(r['fine_max7']['score'] > target_all for r in records[1:]),
            'max7_control_equal_count': sum(r['fine_max7']['score'] == target_all for r in records[1:])}
    rank['fixed_original4_rank_among_target_plus8'] = 1 + rank['fixed_original4_control_strictly_greater_count']
    rank['max7_rank_among_target_plus8'] = 1 + rank['max7_control_strictly_greater_count']
    original = float(profile['fixed_four_row_score'])
    recovered = float(scores[0, 202, fixed_i])
    require(abs(original - recovered) <= ATOL, 'Coarse zero-offset original score not reproduced')
    return {'profile_id': profile['profile_id'], 'origin_scan_id': profile['selected_track']['scan_id'],
            'context_scan_id': profile['context_scan_id'], 'origin_rank': profile['selected_track']['rank'],
            'original_window_start_row': r0, 'original_width_channels': 1,
            'original_fixed_four_row_score': original, 'recomputed_fixed_four_row_score': recovered,
            'times_from_primary_reference_s': profile['times_from_primary_reference_s'],
            'coarse_zero_offset_full16_absolute_centers': arrays['rounded_absolute_centers'][0, 202].tolist(),
            'fine_fixed4_zero_offset_full16_absolute_centers': arrays['rounded_absolute_centers'][0, records[0]['fine_fixed_original4']['hypothesis_index']].tolist(),
            'fine_max7_zero_offset_full16_absolute_centers': arrays['rounded_absolute_centers'][0, records[0]['fine_max7']['hypothesis_index']].tolist(),
            'baseline_difference': recovered - original, 'offset_results': records, 'control_ranks': rank,
            'raw_sensitivity_or_FAP_established': False}


def injection_trials(profile, arrays):
    host_i = OFFSETS.index(512)
    centers = arrays['rounded_absolute_centers'][host_i]
    base_terms = arrays['residual_row_terms'][host_i]
    windows = arrays['window_source_rows']
    mask = arrays['window_dc_mask'][host_i]
    base_scores = arrays['scores'][host_i]
    fine_zero = winner(base_scores, mask, arrays, host_i)
    coarse_eligible = np.where(mask[202], -np.inf, base_scores[202])
    coarse_zero_i = int(np.argmax(coarse_eligible))
    coarse_zero = float(base_scores[202, coarse_zero_i])
    track = profile['selected_track']
    records = []
    for drift_fraction in DRIFT_FRACTIONS:
        true_drift = track['drift_hz_s'] + drift_fraction * (4 / 158)
        for phase in INJECTION_PHASES:
            true_centers = np.rint(track['source_reference_channel'] + 512 + phase
                                   + true_drift * arrays['times_from_primary_reference_s'] / DF).astype(np.int64)
            for true_wi, active in enumerate(windows):
                active_mask = np.zeros(16, dtype=bool)
                active_mask[active] = True
                matched_rows = (centers == true_centers[None, :]) & active_mask[None, :]
                matching4 = matched_rows[:, windows].sum(axis=-1, dtype=np.int64)
                signal_only_eligible = np.where(mask, -1, matching4)
                signal_flat = int(np.argmax(signal_only_eligible))
                signal_hi, signal_wi = np.unravel_index(signal_flat, signal_only_eligible.shape)
                signal_match = int(matching4[signal_hi, signal_wi])
                coarse_true_matches = int(matching4[202, true_wi])
                require(not bool(np.isin(true_centers[active], np.asarray(DC)).any()), 'Injection true active rows touch frozen DC')
                for amplitude in AMPLITUDES:
                    injected_terms = base_terms + amplitude * matched_rows
                    injected_scores = injected_terms[:, windows].sum(axis=-1, dtype=np.float64) / 2
                    fine = winner(injected_scores, mask, arrays, host_i)
                    coarse_scores = injected_scores[202]
                    coarse_wi = int(np.argmax(np.where(mask[202], -np.inf, coarse_scores)))
                    fine_matches = int(matching4[fine['hypothesis_index'], fine['window_index']])
                    coarse_matches = int(matching4[202, coarse_wi])
                    records.append({'profile_id': profile['profile_id'], 'origin_scan_id': track['scan_id'],
                                    'context_scan_id': profile['context_scan_id'], 'origin_rank': track['rank'],
                                    'host_offset_channels': 512, 'true_drift_fraction_of_half_original_step': drift_fraction,
                                    'true_drift_hz_s': true_drift, 'true_phase_channels': phase,
                                    'true_window_index': true_wi, 'true_window_start_row': WINDOW_STARTS[true_wi],
                                    'true_active_source_rows': active.tolist(), 'true_absolute_centers': true_centers.tolist(),
                                    'amplitude_per_active_standardized_single_bin': amplitude,
                                    'fine_score': fine['score'], 'fine_zero_injection_max7_score': fine_zero['score'],
                                    'fine_max7_uplift': fine['score'] - fine_zero['score'],
                                    'fine_winner': fine, 'fine_winner_matches_true_activity_window': fine['window_index'] == true_wi,
                                    'fine_winner_matching_active4_count': fine_matches,
                                    'fine_winner_matching_active4_fraction': fine_matches / 4,
                                    'coarse_max7_score': float(coarse_scores[coarse_wi]),
                                    'coarse_zero_injection_max7_score': coarse_zero,
                                    'coarse_max7_uplift': float(coarse_scores[coarse_wi]) - coarse_zero,
                                    'coarse_winner_window_index': coarse_wi,
                                    'coarse_winner_window_start_row': WINDOW_STARTS[coarse_wi],
                                    'coarse_winner_matches_true_activity_window': coarse_wi == true_wi,
                                    'coarse_winner_matching_active4_count': coarse_matches,
                                    'coarse_truewindow_score': float(coarse_scores[true_wi]),
                                    'coarse_zero_injection_truewindow_score': float(base_scores[202, true_wi]),
                                    'coarse_truewindow_uplift': float(coarse_scores[true_wi] - base_scores[202, true_wi]),
                                    'coarse_truewindow_matching_active4_count': coarse_true_matches,
                                    'coarse_truewindow_signal_only_matched_row_fraction': coarse_true_matches / 4,
                                    'signal_only_fine_best_matching_active4_count': signal_match,
                                    'signal_only_fine_best_matched_row_fraction': signal_match / 4,
                                    'signal_only_fine_best_hypothesis_index': int(signal_hi),
                                    'signal_only_fine_best_window_index': int(signal_wi),
                                    'signal_only_fine_best_matches_true_activity_window': signal_wi == true_wi,
                                    'model': 'additive_standardized_residual_native_delta_bin_frozen_normalization',
                                    'raw_sensitivity_or_FAP_established': False})
    require(len(records) == 56, 'Per-profile injection trial census differs')
    return records


def write_csv(path, records):
    flat = []
    for record in records:
        flat.append({k: json.dumps(v, separators=(',', ':'), sort_keys=True, allow_nan=False)
                     if isinstance(v, (dict, list, tuple)) else v for k, v in record.items()})
    with Path(path).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='Read-only extracted input package root')
    parser.add_argument('--scope', required=True, help='Frozen root-authored SCOPE.json')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--portable-inputs', action='store_true', help='Allow relocated input root while retaining every scope and payload pin')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--code-sha256')
    parser.add_argument('--output-dir', help='Fresh output directory, outside input root')
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    scope_path = Path(args.scope).resolve()
    code_path = Path(__file__).resolve()
    started = time.monotonic()
    scope, matrix, headers, authenticated, support_span = validate_metadata(root, scope_path, args.portable_inputs)
    actual_scope_hash, actual_code_hash = sha256(scope_path), sha256(code_path)
    if args.check_only:
        print(json.dumps({'status': 'PASS_TEXT_ONLY_DRIFT_PHASE_FOLLOWUP_PREFLIGHT',
                          'source_values_read': False, 'numerical_modules_imported': False,
                          'scope_sha256': actual_scope_hash, 'code_sha256': actual_code_hash,
                          'portable_inputs': args.portable_inputs, 'profiles': 54, 'authenticated_payload_files': len(authenticated),
                          'family_hypotheses': 405, 'window_hypotheses': 2835, 'offset_count': 9,
                          'injection_trials': 3024, 'row501_support_local_interval_inclusive': support_span,
                          'anchor': 'preserved_original_selected_first_row_midpoint_not_window_recentered',
                          'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP}))
        return
    require(args.scope_sha256 == actual_scope_hash and args.code_sha256 == actual_code_hash,
            'Execution requires explicit exact --scope-sha256 and --code-sha256 root gates')
    go = read_json(scope_path.parent / 'GO.json')
    require(go['status'] == 'GO_LOCAL_DRIFT_DIAGNOSTIC' and go['scope_sha256'] == actual_scope_hash
            and go['code_sha256'] == actual_code_hash, 'Explicit root GO.json absent or differs')
    require(args.output_dir is not None, 'Fresh output directory required')
    out = Path(args.output_dir).resolve()
    require(not out.exists() and not out.is_relative_to(root), 'Output must be fresh and outside read-only inputs')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Wall budget exceeded')))
    signal.alarm(max(1, WALL_CAP - math.ceil(time.monotonic() - started)))
    global np
    import numpy as np
    out.mkdir(parents=True)
    (out / 'profiles').mkdir()
    summaries, trials, normal_checks, array_pins = [], [], [], []
    for pi, profile in enumerate(matrix['profiles']):
        raw_path = root / profile['raw_normalization_crop']['path']
        with np.load(raw_path, allow_pickle=False) as archive:
            require(set(archive.files) == {'raw_power', 'source_channel0', 'normalization_source_channels', 'absolute_time_rows'}, 'Crop NPZ fields differ')
            raw = archive['raw_power']
            channel0 = int(archive['source_channel0'])
            require(raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4') and np.isfinite(raw).all(), 'Saved raw values invalid')
            require(np.array_equal(archive['absolute_time_rows'], np.arange(16)) and
                    np.array_equal(archive['normalization_source_channels'], np.arange(channel0 + HALO, channel0 + HALO + CORE)), 'Saved crop coordinates differ')
        saved = read_json(root / profile['normalization']['path'])
        normal = {field: np.asarray(saved[field], dtype=np.float64) for field in NORM_FIELDS}
        expected = recompute_normal(raw)
        deviations = {}
        for field in NORM_FIELDS:
            deviation = float(np.max(np.abs(normal[field] - expected[field])))
            require(np.isfinite(expected[field]).all() and deviation <= ATOL, 'Full original-core normalization differs: ' + field)
            deviations[field] = deviation
        normal_checks.append({'profile_id': profile['profile_id'], 'max_absolute_errors': deviations,
                              'normalization_core_local_interval_half_open': [4000, 8096], 'tolerance_absolute': ATOL,
                              'normalization_reused_without_modification': True})
        arrays = family_arrays(profile, raw, normal, channel0)
        summary = summarize_profile(profile, arrays)
        path = out / 'profiles' / (profile['profile_id'] + '_family.npz')
        with path.open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        declared = pin(path, out)
        summary['family_arrays'] = declared
        summary['input_raw_crop'] = profile['raw_normalization_crop']
        summary['input_normalization'] = profile['normalization']
        summaries.append(summary)
        array_pins.append(declared)
        trials.extend(injection_trials(profile, arrays))
        if (pi + 1) % 6 == 0:
            print(json.dumps({'progress_profiles_completed': pi + 1, 'profiles_total': 54}), flush=True)
    require(len(trials) == 3024, 'Final injection trial census differs')
    result = {'schema': 'SETI_LOCAL_DRIFT81_PHASE5_FOLLOWUP_V1', 'status': 'COMPLETE_54_AUTHENTICATED_PROFILES',
              'scope_sha256': actual_scope_hash, 'code_sha256': actual_code_hash,
              'offset_channels': list(OFFSETS), 'window_start_rows': list(WINDOW_STARTS),
              'family_order': 'drift_slow_phase_fast_window_fastest',
              'tie_policy': 'first_array_index', 'primary_statistic': 'fine_max405_at_original_selected4',
              'secondary_statistic': 'fine_max2835_across7_windows',
              'DC_policy': 'veto_exact_native_DC_contact_only_in_tested_selected4_annotate_full16_preserve_data',
              'profiles': summaries, 'normalization_authentication': normal_checks,
              'selection_conditioned_local_followup': True, 'qualified_SETI_detection': False,
              'calibrated_SNR_FAP': False, 'new_observation': False,
              'injection_model': 'standardized_native_single_bin_delta_response_frozen_normalization',
              'raw_sensitivity_or_FAP_established': False}
    create_json(out / 'PROFILES.json', result)
    write_csv(out / 'PROFILES.csv', summaries)
    create_json(out / 'INJECTIONS.json', {'schema': 'SETI_RESIDUAL_DOMAIN_DELTA_BIN_INJECTION_TRANSPORT_V1',
                                        'count': 3024, 'trials': trials,
                                        'raw_sensitivity_or_FAP_established': False,
                                        'instrumental_line_response_modeled': False})
    write_csv(out / 'INJECTIONS.csv', trials)
    signal.alarm(0)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    receipt = {'status': 'COMPLETE_BOUNDED_LOCAL_DRIFT_PHASE_PRODUCTION',
               'scope': pin(scope_path), 'producer': pin(code_path), 'source_matrix': pin(root / MATRIX),
               'authenticated_inputs': authenticated,
               'portable_inputs': args.portable_inputs, 'actual_input_root': str(root),
               'original_scope_input_root': scope['source_root'],
               'profiles': 54, 'hypotheses_per_offset_profile': 405,
               'four_row_scores_saved': 54 * 9 * 405 * 7, 'residual_row_terms_saved': 54 * 9 * 405 * 16,
               'injection_trials': 3024, 'raw_data_modified': False, 'input_package_modified': False,
               'detector_producer_imported': False, 'normalization_reused': True,
               'resource_limits': {'CPU_s': CPU_CAP, 'wall_s': WALL_CAP, 'memory_bytes': MEMORY_CAP},
               'resource_usage': {'CPU_s': usage.ru_utime + usage.ru_stime, 'wall_s': time.monotonic() - started,
                                  'peak_RSS_bytes': usage.ru_maxrss * 1024},
               'outputs': array_pins + [pin(out / name, out) for name in ('PROFILES.json', 'PROFILES.csv', 'INJECTIONS.json', 'INJECTIONS.csv')],
               'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}
    create_json(out / 'EXECUTION_RECEIPT.json', receipt)
    print(json.dumps({'status': receipt['status'], 'output_dir': str(out), 'resource_usage': receipt['resource_usage']}))


if __name__ == '__main__':
    main()
