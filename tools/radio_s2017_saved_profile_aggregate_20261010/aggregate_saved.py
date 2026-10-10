#!/usr/bin/env python3
"""One finite posthoc aggregation of already authenticated, saved profiles.

No source-HDF5, detector, profile kernel, normalization, codec or median is run.
NumPy is imported only after exact scope/code/OWN saved-input byte admission.
"""
import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
FAMILY = 'radio_s2017_saved_profile_aggregate_20261010'
SOURCE_FAMILY = 'radio_s2017_cross_on_profile_recovery_20261010'
SCANS = ['epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off']
ON = (0, 2, 4)
OFF = (1, 3, 5)
CPU_CAP = 120.0
CPU_HARD = 122
WALL_CAP = 600.0
MEMORY_CAP = 1073741824
OUTPUT_CAP = 33554432
SHARED_CAP = 12884901888
COMPLETE = 'COMPLETE_1905_SAVED_PROFILE_AGGREGATES_EXPLORATORY_ONLY'
SOURCE_COMPLETE = 'COMPLETE_635_S2017_MATCHED_TRIPLES_ALL_SIX_FIXED_PROFILES_EXPLORATORY_ONLY'
SOURCE_QA = 'PASS_635_TRIPLES_11430_FIXED_PROFILE_OUTPUTS_AND23465616_RAW_CELL_OCCURRENCE_DIGESTS'
SOURCE_OUTER = 'PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS'
EXPECTED_KEYS = {
    'logical_geometry_indices', 'logical_times_seconds_from_original_reference',
    'geometry_source_channel_centers', 'geometry_scan_indices', 'geometry_width_channels',
    'source_channel_offsets', 'scans', 'saved_full_native_row_medians',
    'geometry_center_row_normalized_power', 'geometry_flank_median_row_normalized_power',
    'geometry_center_minus_flank_rows', 'geometry_raw_width_mean_power',
    'geometry_mean_raw_frequency_profile', 'geometry_mean_row_normalized_frequency_profile',
    'geometry_mean_normalized_minus_flank_frequency_profile', 'geometry_raw_row_SHA256',
}
LIMITATIONS = [
    'Posthoc descriptive aggregation of previously inspected, same-visit ON-selected profiles.',
    '1905 member paths and 635 parent triples are correlated; 61 logical aliases reuse saved geometry.',
    'Equal-weight rows within each scan; scan times are not concatenated into a fitted common track.',
    'Signed rankings and strict positive-value counts are descriptive, without calibrated significance.',
    'Local OFF windows describe only the saved +/-64-channel neighborhoods along fixed member tracks.',
    'No OFF veto, candidate qualification, independent validation, origin classification or absence claim.',
    'No detector, profile extraction, baseline median, normalization, codec, consensus fit or source GET.',
    'Original resource failures, source MD5 limits, protected frames and scientific statuses are unchanged.',
]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def own_path(value):
    p = Path(value)
    require('..' not in p.parts, 'Parent traversal is forbidden')
    p = p if p.is_absolute() else ROOT / p
    require(not p.is_symlink(), 'Symlink input forbidden')
    p = p.resolve(strict=True)
    require(p.is_relative_to(ROOT), 'Input must belong to OUR repository')
    require(p.is_file(), 'Expected regular input file')
    return p


def pin(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path), 'bytes': path.stat().st_size}


def verify(p):
    path = own_path(p['path'])
    require(path.stat().st_size == p['bytes'] and sha(path) == p['sha256'], 'Input byte pin mismatch: ' + p['path'])
    return path


def same_pin(a, b):
    return own_path(a['path']) == own_path(b['path']) and a['bytes'] == b['bytes'] and a['sha256'] == b['sha256']


def load_json(path):
    return json.loads(path.read_text())


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    fsync_directory(path.parent)


def tree_bytes(root):
    total = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
        for name in files:
            p = Path(current) / name
            if not p.is_symlink():
                try:
                    total += p.stat().st_size
                except FileNotFoundError:
                    pass
    return total


def resource_use(start):
    r = resource.getrusage(resource.RUSAGE_SELF)
    return {'process_CPU_seconds': r.ru_utime + r.ru_stime,
            'wall_seconds': time.monotonic() - start, 'peak_RSS_bytes': r.ru_maxrss * 1024}


def check_caps(start):
    v = resource_use(start)
    require(v['process_CPU_seconds'] <= CPU_CAP and v['wall_seconds'] <= WALL_CAP and
            v['peak_RSS_bytes'] <= MEMORY_CAP, 'Measured aggregate resource cap exceeded')
    return v


def load_contract(args):
    scope_path = own_path(args.scope)
    require(sha(scope_path) == args.expected_scope_sha256, 'Scope digest mismatch')
    s = load_json(scope_path)
    require(s['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_SCOPE_V1' and s['family_id'] == FAMILY, 'Wrong scope')
    require(s['script_sha256'] == sha(Path(__file__).resolve()), 'Script digest mismatch')
    require(s['source_family_id'] == SOURCE_FAMILY and s['scans'] == SCANS, 'Wrong original family/order')
    require(s['CPU_cap_s'] == CPU_CAP and s['CPU_hard_limit_s'] == CPU_HARD and s['wall_cap_s'] == WALL_CAP and
            s['memory_cap_bytes'] == MEMORY_CAP and s['output_cap_bytes'] == OUTPUT_CAP and
            s['shared_workspace_cap_bytes'] == SHARED_CAP, 'Caps changed')
    require(s['selected_members'] == 1905 and s['selected_triples'] == 635 and s['unique_geometries'] == 11369 and
            s['new_geometry_aliases'] == 61 and s['old_geometry_aliases'] == 0, 'Selection/counts changed')
    require(s['source_measurement_closed_and_immutable'] is True and args.root_go_after_freeze,
            'Closed source/root GO required')
    require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit) is not None, 'Exact freeze commit required')
    roots = [Path(p).resolve(strict=True) for p in s['shared_workspace_roots']]
    require(len(roots) == len(set(roots)) and all(not a.is_relative_to(b) for a in roots for b in roots if a != b),
            'Shared roots must be unique/nonoverlapping')
    require(any(ROOT.is_relative_to(p) for p in roots), 'OUR source/output omitted from shared roots')
    require(sum(tree_bytes(p) for p in roots) + OUTPUT_CAP + 1048576 <= SHARED_CAP, 'Shared 12GiB disk gate')
    require(os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize >= OUTPUT_CAP + 1048576, 'Physical disk gate')
    required = {'compact_arrays', 'profile_index', 'profiles_epoch1_on', 'profiles_epoch2_on', 'profiles_epoch3_on',
                'source_execution', 'source_QA', 'source_outer', 'source_scope', 'source_script', 'source_contract'}
    require(set(s['input_pins']) == required, 'Exact finite source inventory required')
    paths = {k: verify(p) for k, p in s['input_pins'].items()}
    for p in s.get('dependency_pins', []):
        verify(p)
    index = load_json(paths['profile_index'])
    execution = load_json(paths['source_execution'])
    qa = load_json(paths['source_QA'])
    outer = load_json(paths['source_outer'])
    require(index['schema'] == 'SETI_S2017_CROSS_ON_ALL_SIX_FIXED_PROFILES_V1' and index['complete'] is True and
            index['family_id'] == SOURCE_FAMILY, 'Original profile index admission')
    require(execution['status'] == SOURCE_COMPLETE and qa['status'] == SOURCE_QA and outer['status'] == SOURCE_OUTER,
            'Actual original COMPLETE + QA + CLOSED resource PASS required')
    require(execution['family_id'] == qa['family_id'] == SOURCE_FAMILY and outer['child_exit_code'] == 0 and
            outer['child_timed_out'] is False and outer['automatic_retry_performed'] is False,
            'Original lifecycle mismatch')
    require(execution['scope_sha256'] == qa['scope_sha256'] == s['input_pins']['source_scope']['sha256'] and
            execution['script_sha256'] == qa['profile_script_sha256'] == s['input_pins']['source_script']['sha256'],
            'Original code/scope provenance mismatch')
    require(qa['execution_receipt_sha256'] == outer['inner_terminal_sha256'] == s['input_pins']['source_execution']['sha256'] and
            qa['outer_execution_receipt_sha256'] == s['input_pins']['source_outer']['sha256'], 'Original execution/QA join')
    require(execution['public_freeze_commit'] == qa['public_profile_freeze_commit'] == outer['freeze_commit'], 'Original freeze join')
    require(qa['all_input_end_readbacks_exact'] is True and qa['original_source_raw_rows_authenticated'] is True and
            qa['selected_raw_row_SHA256_digests_independently_matched'] is True, 'Original raw digest QA required')
    for name, expected in [('selected_members', 1905), ('selected_triples', 635), ('unique_geometries', 11369),
                           ('new_geometry_aliases', 61), ('old_geometry_aliases', 0)]:
        require(index[name] == execution[name] == expected, 'Original count mismatch ' + name)
    require(index['ordered_geometry_sha256'] == execution['ordered_geometry_sha256'] == qa['ordered_geometry_sha256'] ==
            s['ordered_geometry_sha256'], 'Original geometry digest mismatch')
    require(execution['selected_members_sha256'] == qa['selected_members_sha256'] == s['selected_members_sha256'],
            'Original member digest mismatch')
    require(same_pin(index['compact_arrays_pin'], s['input_pins']['compact_arrays']) and
            same_pin(execution['compact_arrays_pin'], s['input_pins']['compact_arrays']) and
            same_pin(execution['profile_JSON_pin'], s['input_pins']['profile_index']), 'Original saved array/index join')
    require(len(index['origin_record_files']) == 3, 'Three origin shards required')
    records = [None] * 1905
    for oi, scan in enumerate(SCANS[::2]):
        declared = index['origin_record_files'][oi]
        require(declared['originating_ON'] == scan and declared['logical_member_count'] == 635 and
                same_pin(declared['file_pin'], s['input_pins']['profiles_' + scan]), 'Origin shard index join')
        doc = load_json(paths['profiles_' + scan])
        require(doc['schema'] == index['schema'] and doc['family_id'] == SOURCE_FAMILY and
                doc['originating_ON'] == scan and len(doc['records']) == 635, 'Origin shard contract')
        for ti, row in enumerate(doc['records']):
            i = row['logical_member_index']
            require(i == 3 * ti + oi and records[i] is None and row['member_scan_id'] == scan and
                    row['original_member']['scan_id'] == scan, 'Exact logical membership/order required')
            require(len(row['scan_profiles']) == 6 and [x['scan_id'] for x in row['scan_profiles']] == SCANS,
                    'Fixed six scan profile order')
            key = row['original_member']['original_key']
            require(key['scan_id'] == scan and key['width_channels'] in (1, 3) and math.isfinite(key['drift_hz_s']),
                    'Original fixed member key')
            records[i] = row
    require(all(r is not None for r in records), 'Missing member')
    for ti in range(635):
        group = records[3 * ti:3 * ti + 3]
        require(len({r['match_id'] for r in group}) == 1 and len({r['original_display_rank'] for r in group}) == 1,
                'Parent triple identity mismatch')
    require(len({r['match_id'] for r in records}) == 635, 'Duplicate parent triple')
    return s, paths, records, roots


def aggregate(np, data, source_records):
    require(set(data.files) == EXPECTED_KEYS, 'Exact old NPZ schema required')
    mapping = data['logical_geometry_indices']
    scan_index = data['geometry_scan_indices']
    widths = data['geometry_width_channels']
    rows = data['geometry_center_minus_flank_rows']
    curves = data['geometry_mean_normalized_minus_flank_frequency_profile']
    offsets = data['source_channel_offsets']
    require(mapping.shape == (1905, 6) and mapping.dtype.kind in 'iu' and
            scan_index.shape == widths.shape == (11369,) and rows.shape == (11369, 16) and
            curves.shape == (11369, 129) and rows.dtype.str == curves.dtype.str == '<f8', 'Array shape/dtype mismatch')
    require(list(data['scans'].tolist()) == SCANS and offsets.shape == (129,) and
            np.array_equal(offsets, np.arange(-64, 65)) and np.isfinite(rows).all() and np.isfinite(curves).all(),
            'Saved scan/offset/finiteness contract')
    require(mapping.min() == 0 and mapping.max() == 11368 and len(np.unique(mapping)) == 11369,
            'Unique mapping and 61 alias count')
    require(np.array_equal(scan_index[mapping], np.broadcast_to(np.arange(6), (1905, 6))) and
            np.isin(widths, [1, 3]).all(), 'Saved scan/width geometry contract')
    means = np.mean(rows, axis=1)
    first = np.mean(rows[:, :8], axis=1)
    last = np.mean(rows[:, 8:], axis=1)
    positive = np.count_nonzero(rows > 0.0, axis=1)
    local_max = np.zeros(11369, dtype='<f8')
    local_offset = np.zeros(11369, dtype='<i2')
    for g in range(11369):
        if int(scan_index[g]) in OFF:
            radius = int(widths[g]) // 2
            # All fixed, fully supported native-channel windows; argmax breaks ties at lowest offset.
            windows = np.mean(np.lib.stride_tricks.sliding_window_view(curves[g], 2 * radius + 1), axis=1)
            k = int(np.argmax(windows))
            local_max[g] = float(windows[k])
            local_offset[g] = int(offsets[k + radius])
    output_records = []
    flag_names = ['all_ON_means_positive', 'all_ON_halves_positive', 'all_ON_rows_positive',
                  'all_OFF_means_positive', 'all_OFF_halves_positive', 'all_OFF_rows_positive']
    for i, old in enumerate(source_records):
        gs = mapping[i]
        width = int(old['original_member']['original_key']['width_channels'])
        require(np.all(widths[gs] == width), 'Logical member width mismatch')
        scan_metrics = []
        for si, g0 in enumerate(gs):
            g = int(g0)
            require(old['scan_profiles'][si]['geometry_index'] == g and
                    old['scan_profiles'][si]['row_array_ref'] == {'file': 'COMPACT_FIXED_PROFILES.npz',
                      'array': 'geometry_center_minus_flank_rows', 'index': g}, 'Original JSON geometry/array reference mismatch')
            m = {'scan_id': SCANS[si], 'target_role': 'ON' if si in ON else 'OFF', 'geometry_index': g,
                 'mean': float(means[g]), 'first_eight_mean': float(first[g]), 'last_eight_mean': float(last[g]),
                 'minimum_half_mean': float(min(first[g], last[g])), 'positive_rows': int(positive[g]),
                 'mean_positive': bool(means[g] > 0), 'both_halves_positive': bool(first[g] > 0 and last[g] > 0),
                 'all_rows_positive': bool(positive[g] == 16)}
            if si in OFF:
                m['local_window_maximum'] = float(local_max[g])
                m['local_window_center_offset_channels'] = int(local_offset[g])
            scan_metrics.append(m)
        on_min = min(float(means[gs[k]]) for k in ON)
        off_max = max(float(means[gs[k]]) for k in OFF)
        half_on_min = min(float(v[gs[k]]) for k in ON for v in (first, last))
        half_off_max = max(float(v[gs[k]]) for k in OFF for v in (first, last))
        off_local_max = max(float(local_max[gs[k]]) for k in OFF)
        row = {'logical_member_index': i, 'match_id': old['match_id'], 'original_display_rank': old['original_display_rank'],
               'originating_ON': old['member_scan_id'], 'member_scan_id': old['member_scan_id'],
               'original_member': old['original_member'], 'drift_hz_s': old['original_member']['original_key']['drift_hz_s'],
               'width_channels': width, 'geometry_indices': [int(g) for g in gs], 'scan_metrics': scan_metrics,
               'min_ON_mean': on_min, 'max_OFF_mean': off_max, 'min_ON_half_mean': half_on_min,
               'max_OFF_half_mean': half_off_max, 'max_OFF_local_window': off_local_max,
               'signed_worst_mean_gap': on_min - off_max, 'signed_worst_half_gap': half_on_min - half_off_max,
               'signed_neighborhood_gap': on_min - off_local_max}
        for role, ids in [('ON', ON), ('OFF', OFF)]:
            row['all_' + role + '_means_positive'] = all(scan_metrics[k]['mean_positive'] for k in ids)
            row['all_' + role + '_halves_positive'] = all(scan_metrics[k]['both_halves_positive'] for k in ids)
            row['all_' + role + '_rows_positive'] = all(scan_metrics[k]['all_rows_positive'] for k in ids)
        output_records.append(row)
    rank_mean = sorted(range(1905), key=lambda i: (-output_records[i]['signed_worst_mean_gap'], i))
    rank_local = sorted(range(1905), key=lambda i: (-output_records[i]['signed_neighborhood_gap'], i))
    triple_records = []
    for ti in range(635):
        group = output_records[3 * ti:3 * ti + 3]
        triple_records.append({'match_id': group[0]['match_id'], 'original_display_rank': group[0]['original_display_rank'],
            'logical_member_indices': [r['logical_member_index'] for r in group],
            'member_flag_counts': {k: sum(r[k] for r in group) for k in flag_names},
            'members_with_positive_signed_worst_mean_gap': sum(r['signed_worst_mean_gap'] > 0 for r in group),
            'members_with_positive_signed_worst_half_gap': sum(r['signed_worst_half_gap'] > 0 for r in group),
            'members_with_positive_signed_neighborhood_gap': sum(r['signed_neighborhood_gap'] > 0 for r in group)})
    selected = output_records[rank_mean[0]].copy()
    selected.update({'selection_rule': 'First in signed_worst_mean_gap descending, logical_member_index ascending',
        'source_channel_offsets': [int(x) for x in offsets], 'df_hz': -2.7939677238464355, 'fch1_hz': 2802832031.25,
        'scan_profiles': [{'scan_id': SCANS[si], 'geometry_index': int(g),
                          'mean_normalized_minus_flank_frequency_profile': [float(x) for x in curves[int(g)]]}
                         for si, g in enumerate(mapping[rank_mean[0]])]})
    counts = {k: sum(r[k] for r in output_records) for k in flag_names}
    counts.update({k + '_positive': sum(r[k] > 0 for r in output_records)
                   for k in ['signed_worst_mean_gap', 'signed_worst_half_gap', 'signed_neighborhood_gap']})
    arrays = {'source_geometry_indices': np.arange(11369, dtype='<i4'), 'geometry_scan_indices': scan_index,
              'geometry_width_channels': widths, 'geometry_mean': means, 'geometry_first_eight_mean': first,
              'geometry_last_eight_mean': last, 'geometry_positive_rows': positive.astype('<i2'),
              'geometry_OFF_local_window_maximum': local_max, 'geometry_OFF_local_window_center_offset': local_offset,
              'logical_geometry_indices': mapping}
    return output_records, triple_records, rank_mean, rank_local, selected, counts, arrays


def main():
    start = time.monotonic()
    ap = argparse.ArgumentParser()
    ap.add_argument('--scope', required=True)
    ap.add_argument('--expected-scope-sha256', required=True)
    ap.add_argument('--freeze-commit', required=True)
    ap.add_argument('--root-go-after-freeze', action='store_true')
    args = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (int(CPU_CAP), CPU_HARD))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def timeout(*_):
        raise TimeoutError('Frozen wall cap reached')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(int(WALL_CAP))
    stage = ROOT / 'results' / FAMILY
    stage.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(stage / 'AGGREGATE_SERIAL.flock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    claimed = False
    complete = False
    out = stage / 'measurement'
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save_new(stage / 'AGGREGATE_STARTED_ONCE.json', {'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256,
                 'script_sha256': sha(Path(__file__).resolve()), 'freeze_commit': args.freeze_commit, 'no_retry': True})
        claimed = True
        s, paths, source_records, roots = load_contract(args)
        out.mkdir(exist_ok=False)
        save_new(out / 'INPUT_PINS.json', {'schema': 'SETI_S2017_AGGREGATE_INPUT_PINS_V1', 'family_id': FAMILY,
                 'scope_sha256': args.expected_scope_sha256, 'script_sha256': s['script_sha256'],
                 'public_freeze_commit': args.freeze_commit, 'input_pins': s['input_pins'],
                 'dependency_pins': s.get('dependency_pins', [])})
        import numpy as np
        require(np.__version__ == '2.3.5', 'Frozen NumPy version mismatch')
        with np.load(paths['compact_arrays'], allow_pickle=False) as data:
            records, triples, rank_mean, rank_local, selected, counts, arrays = aggregate(np, data, source_records)
        require(all(math.isfinite(r[k]) for r in records for k in ['signed_worst_mean_gap', 'signed_worst_half_gap',
                                                                  'signed_neighborhood_gap']), 'Finite results required')
        array_path = out / 'GEOMETRY_AGGREGATE.npz'
        with array_path.open('xb') as f:
            np.savez(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        result = {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_V1', 'family_id': FAMILY,
                  'scope_sha256': args.expected_scope_sha256, 'script_sha256': s['script_sha256'],
                  'public_freeze_commit': args.freeze_commit, 'source_family_id': SOURCE_FAMILY,
                  'source_input_pins': s['input_pins'], 'scans': SCANS, 'member_count': 1905, 'triple_count': 635,
                  'logical_scan_profiles': 11430, 'unique_geometries': 11369, 'geometry_aliases': 61,
                  'old_geometry_overlap': 0, 'records': records, 'triple_records': triples,
                  'rank_by_signed_worst_mean_gap': rank_mean, 'rank_by_signed_neighborhood_gap': rank_local,
                  'rank_tie_rule': 'Metric descending, logical_member_index ascending', 'descriptive_counts': counts,
                  'selected_display_case': selected, 'derived_geometry_arrays_pin': pin(array_path),
                  'new_original_detector_hypothesis_combinations': 0, 'limitations': LIMITATIONS}
        json_path = out / 'SAVED_PROFILE_AGGREGATE.json'
        save_new(json_path, result)
        csv_path = out / 'MEMBER_METRICS.csv'
        columns = ['logical_member_index', 'match_id', 'original_display_rank', 'originating_ON', 'drift_hz_s',
                   'width_channels', 'min_ON_mean', 'max_OFF_mean', 'min_ON_half_mean', 'max_OFF_half_mean',
                   'max_OFF_local_window', 'signed_worst_mean_gap', 'signed_worst_half_gap', 'signed_neighborhood_gap',
                   'all_ON_means_positive', 'all_ON_halves_positive', 'all_ON_rows_positive',
                   'all_OFF_means_positive', 'all_OFF_halves_positive', 'all_OFF_rows_positive']
        per_scan_fields = ['mean', 'first_eight_mean', 'last_eight_mean', 'minimum_half_mean', 'positive_rows',
                           'mean_positive', 'both_halves_positive', 'all_rows_positive']
        for si, scan in enumerate(SCANS):
            columns.extend(scan + '_' + key for key in per_scan_fields)
            if si in OFF:
                columns.extend([scan + '_local_window_maximum', scan + '_local_window_center_offset_channels'])
        with csv_path.open('x', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            for row in records:
                csv_row = row.copy()
                for si, scan in enumerate(SCANS):
                    fields = per_scan_fields + (['local_window_maximum', 'local_window_center_offset_channels'] if si in OFF else [])
                    csv_row.update({scan + '_' + key: row['scan_metrics'][si][key] for key in fields})
                writer.writerow(csv_row)
            f.flush()
            os.fsync(f.fileno())
        output_pins = [pin(p) for p in [array_path, json_path, csv_path, out / 'INPUT_PINS.json']]
        for p in list(s['input_pins'].values()) + s.get('dependency_pins', []):
            verify(p)
        require(sha(own_path(args.scope)) == args.expected_scope_sha256 and sha(Path(__file__).resolve()) == s['script_sha256'],
                'Final execution byte pins changed')
        require(tree_bytes(out) + 1048576 <= OUTPUT_CAP, '32MiB output cap')
        require(sum(tree_bytes(p) for p in roots) + 1048576 <= SHARED_CAP, 'Final shared disk cap + terminal reserve')
        terminal = {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_EXECUTION_V1', 'status': COMPLETE, 'family_id': FAMILY,
                    'scope_sha256': args.expected_scope_sha256, 'script_sha256': s['script_sha256'],
                    'public_freeze_commit': args.freeze_commit, 'source_input_pins': s['input_pins'],
                    'output_pins': output_pins, 'aggregate_pin': pin(json_path), 'member_count': 1905, 'triple_count': 635, 'unique_geometries': 11369,
                    'geometry_aliases': 61, 'all_input_end_readbacks_exact': True, 'resource_caps_satisfied': True,
                    'new_original_detector_hypothesis_combinations': 0, 'profiles_remeasured': False,
                    'profile_kernel_reexecuted': False, 'normalization_reexecuted': False, 'codec_reexecuted': False,
                    'native_medians_recomputed': False, 'HDF5_source_opened': False, 'new_HTTP_requests': 0,
                    'new_source_BODY_bytes': 0, 'cost_DKK': 0, 'no_retry': True, 'limitations': LIMITATIONS,
                    **check_caps(start)}
        prepared = out / 'EXECUTION_RECEIPT.prepared.json'
        save_new(prepared, terminal)
        check_caps(start)
        signal.alarm(0)
        os.link(prepared, out / 'EXECUTION_RECEIPT.json')
        complete = True
        fsync_directory(out)
        try:
            print(json.dumps({'status': COMPLETE, 'member_count': 1905, **resource_use(start)}), flush=True)
        except BrokenPipeError:
            pass
    except BaseException as error:
        if claimed and not complete:
            signal.alarm(0)
            failure = stage / 'FAILURE_RECEIPT.json'
            if not failure.exists():
                save_new(failure, {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_FAILURE_V1',
                    'status': 'INCOMPLETE_SAVED_PROFILE_AGGREGATE_NO_RETRY', 'family_id': FAMILY,
                    'error_type': type(error).__name__, 'error': str(error), 'scope_sha256': args.expected_scope_sha256,
                    'script_sha256': sha(Path(__file__).resolve()), 'public_freeze_commit': args.freeze_commit,
                    'partial_outputs_preserved': out.exists(), 'no_retry': True, **resource_use(start)})
        raise
    finally:
        signal.alarm(0)
        os.close(lock_fd)  # Stable inode is never unlinked; kernel releases the process-owned lock.


if __name__ == '__main__':
    main()
