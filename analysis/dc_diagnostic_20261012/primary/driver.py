#!/usr/bin/env python3
"""Fixed-cell DC attribution of authenticated existing raw503 contexts only.

Prepare freezes inputs/definitions; run requires exact scope and code digests.
No search, refilter of full cores, mask, veto, rank, optimization or acquisition.
"""
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

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent
SOURCE = WORKSPACE / 'seti_previous'
MATRICES = [
    'analysis/off_adjacent_20261011_context/results/CONTEXT_PROFILES.json',
    'analysis/s2017_control_targets_20261011_v2/results/context/CONTEXT_PROFILES.json',
]
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
DC = {170: 178782208, 171: 179830784, 172: 180879360}
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ATOL, RTOL = 1e-7, 1e-10


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def pin(path):
    require(path.is_file() and not path.is_symlink(), 'Regular nonsymlink input required')
    return {'path': path.relative_to(WORKSPACE).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    require(not path.exists(), 'Output already exists: ' + str(path))
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def resolve(matrix, declaration):
    name = declaration['path']
    path = SOURCE / name if name.startswith('analysis/') else matrix.parent / name
    path = path.resolve()
    require(path.is_relative_to(SOURCE), 'Input escapes original source root')
    actual = pin(path)
    require(actual['bytes'] == declaration['bytes'] and actual['sha256'] == declaration['sha256'],
            'Declared source artifact pin differs: ' + name)
    return path


def profile_entries():
    entries, templates, pins = [], [], {}
    for rel in MATRICES:
        matrix_path = SOURCE / rel
        matrix = read(matrix_path)
        pins[matrix_path.relative_to(WORKSPACE).as_posix()] = pin(matrix_path)
        require(len(matrix['profiles']) == 54 and len(matrix['selected_tracks']) == 9,
                'Each frozen matrix must contain54profiles9templates')
        family = 'adjacent' if 'off_adjacent' in rel else 'central'
        require(len({json.dumps(t, sort_keys=True) for t in matrix['selected_tracks']}) == 9,
                'Duplicate selected template')
        for track in matrix['selected_tracks']:
            native = track['native_chunk_index'] if family == 'adjacent' else 171
            require(native in DC and track['width_channels'] in (1, 3), 'Unexpected frozen template')
            templates.append({'template_id': family + ':' + track['primary_id'] + ':rank' + str(track['rank']),
                              'family': family, 'native_dc_index': native, 'selected_track': track})
        for profile in matrix['profiles']:
            require(profile['selected_track'] in matrix['selected_tracks'], 'Unbound profile template')
            capsule = resolve(matrix_path, profile['raw_capsule'])
            norm = resolve(matrix_path, profile['normalization'])
            for path in (capsule, norm):
                pins[path.relative_to(WORKSPACE).as_posix()] = pin(path)
            track = profile['selected_track']
            native = track['native_chunk_index'] if family == 'adjacent' else 171
            profile_key = rel + '#' + profile['profile_id']
            entries.append({'profile_key': profile_key, 'profile_id': profile['profile_id'],
                            'template_id': family + ':' + track['primary_id'] + ':rank' + str(track['rank']),
                            'family': family, 'native': native, 'dc': DC[native],
                            'matrix': matrix_path.relative_to(WORKSPACE).as_posix(),
                            'raw': capsule.relative_to(WORKSPACE).as_posix(),
                            'normalization': norm.relative_to(WORKSPACE).as_posix(), 'profile': profile})
    require(len(entries) == 108 and len(templates) == 18 and len({e['profile_key'] for e in entries}) == 108,
            'Frozen profile/template counts differ')
    for t in templates:
        contexts = [e['profile']['context_scan_id'] for e in entries if e['template_id'] == t['template_id']]
        require(len(contexts) == 6 and set(contexts) == set(SCANS), 'Each template must have exactly six fixed scans')
    detector_path = SOURCE / DETECTOR
    pins[detector_path.relative_to(WORKSPACE).as_posix()] = pin(detector_path)
    return sorted(entries, key=lambda e: e['profile_key']), templates, pins


def prepare():
    entries, templates, pins = profile_entries()
    scope = {
        'schema': 'SETI_FIXED_DC_SINGLE_CELL_ATTRIBUTION_SCOPE_V1',
        'status': 'FROZEN_BEFORE_METRICS', 'source_root': 'seti_previous',
        'input_byte_pins': pins, 'driver_sha256': sha(Path(__file__).resolve()),
        'frozen_templates': templates,
        'frozen_profiles': [{k: e[k] for k in ('profile_key', 'profile_id', 'template_id', 'family', 'native', 'dc', 'matrix', 'raw', 'normalization')} for e in entries],
        'expected_counts': {'matrices': 2, 'templates': 18, 'profiles': 108, 'profile_rows': 1728,
                            'distinct_dc_scan_patches': 18, 'distinct_physical_dc_scan_rows': 288,
                            'raw_patch_cells': 37152, 'raw503_profile_cell_instances': 869184},
        'fft_length': 1048576,
        'frozen_dc_source_channels': {str(k): v for k, v in DC.items()},
        'score_formula': 'cell_z=(raw_float64/saved_row_power_median - median(exact501_raw_float64/saved_row_power_median) - saved_row_winsorized_residual_location)/saved_row_residual_MAD_scale; score=sum(original_box_cell_z)/sqrt(16*original_width)',
        'normalization': 'Conditional on pinned full16/core terms; no fullcore reestimation or refilter',
        'attribution': 'DC cell_z is included exactly when absolute original box contains frozen DC; signed_dc_score=sum(DC z)/sqrt(16*width); signed_remainder_score=sum(other cell_z)/sqrt(16*width); positive_dc_mass_fraction=sum(max(DC z,0))/sum(max(all original box cell_z,0)); denominator zero gives null',
        'patch_definition': 'Exact raw float32 DC offsets -64..64 inclusive; per physical row use first lexicographic matrix-relative-path#profile_id with all129 cells supported; no interpolation/synthetic source arrays',
        'patch_ratio': 'raw center / median(raw offsets -64..-16 and +16..+64);98 symmetric flank cells excluding offsets-15..15; adjacent ratios center/-1 and center/+1',
        'peak_definition': 'Strict raw center maximum over all129 frozen patch cells; also record tied maximum and center/strongest other cell',
        'raw_reconciliation': 'Group all raw503 cells by native DC index/context_scan_id/source_row/absolute_channel; compare every duplicate float32 bit-for-bit. Deduplicate raw patches and physical DC rows; no pooled profile replication evidence.',
        'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
        'limits': {'cpu_seconds': 600, 'wall_seconds': 900, 'memory_bytes': 2147483648},
        'no_detector_grid': True, 'no_mask_or_veto': True, 'no_reranking': True,
        'no_new_observation': True, 'no_telescope_requests': True, 'original_data_unchanged': True,
        'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False,
    }
    save(BASE / 'SCOPE.json', scope)
    print(json.dumps({'scope': str(BASE / 'SCOPE.json'), 'scope_sha256': sha(BASE / 'SCOPE.json'),
                      'driver_sha256': scope['driver_sha256'], 'profiles': len(entries), 'templates': len(templates)}))


def near(np, actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)
    return float(np.max(np.abs(a - b)))


def descriptive(np, values):
    v = np.asarray(values, dtype=np.float64)
    require(v.size and np.isfinite(v).all(), 'Finite descriptive sample required')
    return {'count': int(v.size), 'min': float(v.min()), 'median': float(np.median(v)), 'max': float(v.max())}


def run(args):
    begun, cpu0 = time.monotonic(), time.process_time()
    scope_path = BASE / 'SCOPE.json'
    require(sha(scope_path) == args.scope_sha256 and sha(Path(__file__).resolve()) == args.driver_sha256,
            'Admission scope/driver digests differ')
    scope = read(scope_path)
    require(scope['driver_sha256'] == args.driver_sha256, 'Frozen driver digest differs')
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    signal.alarm(900)
    import numpy as np
    entries, templates, pins = profile_entries()
    require(pins == scope['input_byte_pins'] and templates == scope['frozen_templates'], 'Frozen metadata changed')
    require([{k: e[k] for k in ('profile_key', 'profile_id', 'template_id', 'family', 'native', 'dc', 'matrix', 'raw', 'normalization')} for e in entries] == scope['frozen_profiles'],
            'Frozen profile bindings changed')
    require(not (BASE / 'results').exists(), 'Results already exist')
    out = BASE / 'results'
    out.mkdir()
    rows, records, cached = [], [], {}
    physical_raw, reconciliation_counts = {}, {'cell_instances': 0, 'unique_cells': 0, 'duplicate_instances_bit_equal': 0}
    max_box, max_score, max_saved_row_score = 0., 0., 0.
    dc_included, dc_row_instance_values = {}, {}
    for entry in entries:
        p, dc, native = entry['profile'], entry['dc'], entry['native']
        width, scan = p['selected_track']['width_channels'], p['context_scan_id']
        with np.load(WORKSPACE / entry['raw'], allow_pickle=False) as source:
            raw = source['raw_power'].copy()
            centers = source['rounded_absolute_centers'].copy()
            saved = source['row_standardized_box_sum'].copy()
            saved_contribution = source['row_score_contribution'].copy() if 'row_score_contribution' in source else None
        require(raw.dtype.str == '<f4' and raw.shape == (16, 503) and centers.dtype.str == '<i8'
                and centers.shape == (16,) and saved.dtype.str == '<f8' and saved.shape == (16,), 'Raw503 contract differs')
        require(np.isfinite(raw).all() and (raw >= 0).all(), 'Invalid raw503 power')
        require(np.array_equal(centers, p['rounded_absolute_centers']), 'Capsule/JSON centers differ')
        norm = read(WORKSPACE / entry['normalization'])
        levels, location, scale = (np.asarray(norm[k], dtype=np.float64) for k in
            ('row_power_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'))
        require(levels.shape == location.shape == scale.shape == (16,) and np.isfinite(levels).all()
                and np.isfinite(location).all() and np.isfinite(scale).all() and (levels > 0).all() and (scale > 0).all(),
                'Invalid pinned full16 normalization')
        require(norm['normalization_unmasked_counts'] == [4096] * 16, 'Unexpected normalization masks')
        expected_core0 = native * 1048576 + p['selected_track']['core_q'] * 4096
        require(norm['normalization_source_channels'] == list(range(expected_core0, expected_core0 + 4096)),
                'Pinned normalization domain differs from original template')
        cached[entry['profile_key']] = (raw, centers)
        all_z, all_dc_z, all_other_z = [], [], []
        positive_dc, positive_all, overlap = 0., 0., []
        denominator = math.sqrt(16 * width)
        for row in range(16):
            physical_key = (native, scan, row)
            bits = raw[row].view(np.uint32)
            for index in range(503):
                key = (native, scan, row, int(centers[row]) - 251 + index)
                value = int(bits[index])
                if key in physical_raw:
                    require(physical_raw[key] == value, 'Duplicate physical raw cell bits differ: ' + str(key))
                    reconciliation_counts['duplicate_instances_bit_equal'] += 1
                else:
                    physical_raw[key] = value
                reconciliation_counts['cell_instances'] += 1
            normalized = raw[row].astype(np.float64) / levels[row]
            box_indices = range(251 - width // 2, 252 + width // 2)
            cell_records, dc_z, other_z = [], 0., []
            for index in box_indices:
                absolute = int(centers[row]) - 251 + index
                med = float(np.median(normalized[index - 250:index + 251]))
                residual = float(normalized[index] - med)
                z = float((residual - location[row]) / scale[row])
                is_dc = absolute == dc
                cell_records.append({'absolute_source_channel': absolute, 'offset_from_dc': absolute - dc,
                                     'raw_power': float(raw[row, index]), 'local501_normalized_median': med,
                                     'residual': residual, 'standardized_cell': z, 'is_exact_dc': is_dc})
                positive_all += max(z, 0.)
                if is_dc:
                    dc_z = z
                    positive_dc += max(z, 0.)
                    overlap.append(row)
                    dc_included.setdefault(physical_key, []).append(entry['profile_key'])
                    dc_row_instance_values.setdefault(physical_key, []).append(z)
                else:
                    other_z.append(z)
            box_z = float(np.asarray([c['standardized_cell'] for c in cell_records], dtype=np.float64).sum(dtype=np.float64))
            remainder = float(np.asarray(other_z, dtype=np.float64).sum(dtype=np.float64)) if other_z else 0.
            near(np, dc_z + remainder, box_z, 'Signed DC/remainder row arithmetic differs')
            rows.append({'profile_key': entry['profile_key'], 'template_id': entry['template_id'], 'native_dc_index': native,
                         'dc_source_channel': dc, 'context_scan_id': scan, 'source_row': row,
                         'original_box_center': int(centers[row]), 'width_channels': width, 'cells': cell_records,
                         'standardized_row_box_sum': box_z, 'standardized_dc_cell': dc_z,
                         'standardized_remainder_sum': remainder, 'dc_score_contribution': dc_z / denominator,
                         'remainder_score_contribution': remainder / denominator})
            all_z.append(box_z)
            all_dc_z.append(dc_z)
            all_other_z.append(remainder)
        max_box = max(max_box, near(np, all_z, saved, 'Reconstructed box differs from capsule'),
                      near(np, all_z, p['row_standardized_box_sum'], 'Reconstructed box differs from JSON'))
        row_scores = np.asarray(all_z) / denominator
        if saved_contribution is not None:
            max_saved_row_score = max(max_saved_row_score, near(np, row_scores, saved_contribution, 'Saved capsule contributions differ'),
                                     near(np, row_scores, p['row_score_contribution'], 'Saved JSON contributions differ'))
        score = float(np.asarray(all_z).sum(dtype=np.float64) / denominator)
        dc_score = float(np.asarray(all_dc_z).sum(dtype=np.float64) / denominator)
        remainder_score = float(np.asarray(all_other_z).sum(dtype=np.float64) / denominator)
        score_key = 'fixed_robust_box_track_score' if entry['family'] == 'adjacent' else 'direct_fixed_robust_box_track_score'
        max_score = max(max_score, near(np, score, p[score_key], 'Saved fixed score differs'),
                        near(np, dc_score + remainder_score, score, 'Signed partition score differs'))
        if p['origin_primary_score'] is not None:
            max_score = max(max_score, near(np, score, p['origin_primary_score'], 'Origin selected score differs'))
        records.append({'profile_key': entry['profile_key'], 'profile_id': entry['profile_id'], 'template_id': entry['template_id'],
                        'family': entry['family'], 'native_dc_index': native, 'dc_source_channel': dc,
                        'context_scan_id': scan, 'context_target': p['context_target'],
                        'original_acquisition_role': p['original_acquisition_role'], 'selected_track': p['selected_track'],
                        'width_channels': width, 'saved_fixed_score': p[score_key], 'reconstructed_fixed_score': score,
                        'signed_dc_score': dc_score, 'signed_remainder_score': remainder_score,
                        'positive_dc_standardized_cell_mass': positive_dc, 'total_positive_standardized_cell_mass': positive_all,
                        'positive_dc_cell_mass_fraction': positive_dc / positive_all if positive_all else None,
                        'dc_box_overlap_rows': overlap, 'dc_box_overlap_row_count': len(overlap),
                        'normalization_conditional_on_pinned_full16_terms': True})
    reconciliation_counts['unique_cells'] = len(physical_raw)
    require(reconciliation_counts['cell_instances'] == 869184, 'Raw503 instance count differs')
    # All physically repeated cells are reconciled before selecting raw patches.
    offsets = np.arange(-64, 65, dtype=np.int64)
    flank_selection = np.abs(offsets) >= 16
    patches, patch_records, dc_physical_rows = [], [], []
    for native in sorted(DC):
        for scan in SCANS:
            dc = DC[native]
            candidates = [e for e in entries if e['native'] == native and e['profile']['context_scan_id'] == scan]
            require(candidates, 'Missing frozenDC/scan candidates')
            patch, provenance, stats = [], [], []
            for row in range(16):
                selected = None
                for entry in candidates:
                    raw, centers = cached[entry['profile_key']]
                    start, stop = dc - 64 - int(centers[row]) + 251, dc + 65 - int(centers[row]) + 251
                    if 0 <= start < stop <= 503:
                        selected = entry
                        values = raw[row, start:stop].copy()
                        break
                require(selected is not None and values.shape == (129,), 'No complete canonical129 patch support')
                for j, ch in enumerate(dc + offsets):
                    require(int(values[j:j + 1].view(np.uint32)[0]) == physical_raw[(native, scan, row, int(ch))],
                            'Canonical raw patch cell differs from reconciled original')
                require((values > 0).all(), 'Raw ratios require positive saved power')
                center = float(values[64])
                flanks = values[flank_selection].astype(np.float64)
                flank_median = float(np.median(flanks))
                others = np.delete(values, 64).astype(np.float64)
                strong = float(others.max())
                max_value = float(values.max())
                rowstat = {'source_row': row, 'raw_dc_power': center, 'symmetric98_flank_median': flank_median,
                           'center_over_symmetric98_flank_median': center / flank_median,
                           'center_over_left_adjacent': center / float(values[63]),
                           'center_over_right_adjacent': center / float(values[65]),
                           'center_over_strongest_other_patch_bin': center / strong,
                           'strict_center_peak_over129': center > strong,
                           'center_is_maximum_including_ties': center == max_value,
                           'raw_patch_peak_offset_from_dc': int(offsets[np.argmax(values)])}
                stats.append(rowstat)
                patch.append(values)
                provenance.append({'source_row': row, 'profile_key': selected['profile_key'], 'raw_capsule': selected['raw'],
                                   'capsule_center': int(cached[selected['profile_key']][1][row]), 'capsule_half_open_slice': [start, stop]})
                physical_key = (native, scan, row)
                zvalues = dc_row_instance_values.get(physical_key, [])
                dc_physical_rows.append({'native_dc_index': native, 'dc_source_channel': dc, 'context_scan_id': scan,
                    **rowstat, 'canonical_profile_key': selected['profile_key'],
                    'number_of_original_boxes_including_same_dc_cell': len(dc_included.get(physical_key, [])),
                    'including_profile_keys': dc_included.get(physical_key, []),
                    'conditional_dc_standardized_cell_min': min(zvalues) if zvalues else None,
                    'conditional_dc_standardized_cell_max': max(zvalues) if zvalues else None})
            patch = np.asarray(patch, dtype=np.float32)
            patches.append(patch)
            patch_records.append({'patch_id': 'native%d_%s' % (native, scan), 'native_dc_index': native,
                'dc_source_channel': dc, 'context_scan_id': scan, 'shape': [16, 129], 'canonical_row_provenance': provenance,
                'raw_patch_float32_sha256': hashlib.sha256(patch.tobytes()).hexdigest(), 'row_metrics': stats,
                'strict_center_peak_rows': sum(x['strict_center_peak_over129'] for x in stats),
                'center_over_symmetric98_flank_median': descriptive(np, [x['center_over_symmetric98_flank_median'] for x in stats]),
                'center_over_left_adjacent': descriptive(np, [x['center_over_left_adjacent'] for x in stats]),
                'center_over_right_adjacent': descriptive(np, [x['center_over_right_adjacent'] for x in stats])})
    patch_array = np.asarray(patches, dtype=np.float32)
    require(patch_array.shape == (18, 16, 129) and patch_array.size == 37152 and len(dc_physical_rows) == 288,
            'Deduplicated raw patch count differs')
    with (out / 'DC_RAW_PATCHES.npz').open('xb') as stream:
        np.savez(stream, raw_power=patch_array, offsets_from_dc=offsets,
                 source_rows=np.arange(16, dtype=np.int64), native_dc_indices=np.asarray([p['native_dc_index'] for p in patch_records], dtype=np.int64),
                 dc_source_channels=np.asarray([p['dc_source_channel'] for p in patch_records], dtype=np.int64),
                 context_scan_ids=np.asarray([p['context_scan_id'] for p in patch_records], dtype='<U10'))
    template_records = []
    for template in templates:
        profiles = [r for r in records if r['template_id'] == template['template_id']]
        own = next(r for r in profiles if r['context_scan_id'] == template['selected_track']['scan_id'])
        template_records.append({**template, 'own_primary_profile': own, 'six_context_profile_keys': [p['profile_key'] for p in profiles],
                                 'contexts_are_descriptive_not_independent_repeat_evidence': True})
    raw_summary = {'distinct_dc_scan_patches': 18, 'distinct_physical_dc_scan_rows': 288, 'raw_patch_cells': 37152,
                   'strict_center_peak_count_over288': sum(x['strict_center_peak_over129'] for x in dc_physical_rows),
                   'center_is_maximum_including_ties_count_over288': sum(x['center_is_maximum_including_ties'] for x in dc_physical_rows),
                   'center_over_symmetric98_flank_median_over288': descriptive(np, [x['center_over_symmetric98_flank_median'] for x in dc_physical_rows]),
                   'center_over_left_adjacent_over288': descriptive(np, [x['center_over_left_adjacent'] for x in dc_physical_rows]),
                   'center_over_right_adjacent_over288': descriptive(np, [x['center_over_right_adjacent'] for x in dc_physical_rows]),
                   'physical_rows_with_at_least_one_original_box_including_dc': len(dc_included),
                   'all108_original_box_dc_overlap_row_instances': sum(r['dc_box_overlap_row_count'] for r in records),
                   'profile_instances_are_not_independent_DC_samples': True}
    for name, value in [('PROFILE_ATTRIBUTION.json', {'schema': 'SETI_DC_FIXED_PROFILE_ATTRIBUTION_V1', 'profiles': records}),
                        ('ROW_CELL_ATTRIBUTION.json', {'schema': 'SETI_DC_FIXED_ROW_CELL_ATTRIBUTION_V1', 'rows': rows}),
                        ('FROZEN_TEMPLATE_ATTRIBUTION.json', {'templates': template_records}),
                        ('DC_PATCH_METRICS.json', {'patches': patch_records, 'deduplicated_summary': raw_summary}),
                        ('DEDUPLICATED_DC_SCAN_ROWS.json', {'physical_rows': dc_physical_rows}),
                        ('RAW_RECONCILIATION.json', {'status': 'ALL_OVERLAPPING_CAPSULE_RAW_CELLS_BIT_IDENTICAL', **reconciliation_counts,
                                                    'source_key': ['native_dc_index', 'context_scan_id', 'source_row', 'absolute_source_channel']})]:
        save(out / name, value)
    # Read every frozen source again at close to establish original data unchanged.
    for rel, expected in scope['input_byte_pins'].items():
        require(pin(WORKSPACE / rel) == expected, 'Original source input changed during run')
    outputs = {p.name: pin(p) for p in sorted(out.iterdir())}
    receipt = {'schema': 'SETI_DC_SINGLE_CELL_ATTRIBUTION_EXECUTION_V1',
        'status': 'COMPLETE_108_FIXED_PROFILES_18_TEMPLATES_18_RAW_PATCHES',
        'scope_sha256': args.scope_sha256, 'driver_sha256': args.driver_sha256,
        'counts': scope['expected_counts'], 'runtime': {'Python': sys.version.split()[0], 'numpy': np.__version__},
        'numeric_tolerance': scope['numeric_tolerance'], 'max_row_box_absolute_difference': max_box,
        'max_fixed_score_absolute_difference': max_score, 'max_saved_row_contribution_absolute_difference': max_saved_row_score,
        'raw_summary': raw_summary, 'raw_cell_reconciliation': reconciliation_counts,
        'input_byte_pins': scope['input_byte_pins'], 'output_byte_pins': outputs,
        'normalization_conditional_on_pinned_full16_terms': True, 'original_inputs_unchanged_verified': True,
        'no_detector_grid': True, 'no_mask_or_veto': True, 'no_reranking': True, 'no_new_observation': True,
        'no_telescope_requests': True, 'qualified_SETI_detection': False, 'calibrated_SNR_or_FAP': False,
        'resource_use': {'cpu_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - begun,
                         'max_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}}
    save(out / 'EXECUTION_RECEIPT.json', receipt)
    print(json.dumps({'status': receipt['status'], 'raw_summary': raw_summary, 'reconciliation': reconciliation_counts,
                      'max_row_box_absolute_difference': max_box, 'max_score_absolute_difference': max_score,
                      'resource_use': receipt['resource_use']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--driver-sha256')
    args = parser.parse_args()
    require(args.prepare != args.run, 'Choose prepare or admitted run')
    if args.prepare:
        prepare()
    else:
        require(args.scope_sha256 and args.driver_sha256, 'Exact run admission digests required')
        run(args)
