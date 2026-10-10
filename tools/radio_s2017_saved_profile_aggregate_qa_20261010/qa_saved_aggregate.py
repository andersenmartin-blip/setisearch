"""One-shot independent QA of a CLOSED own saved 2017 profile aggregate.

Preparation is source only. Runtime opens the pinned original saved compact
NPZ and completed aggregate outputs; no original kernel, normalization, HDF5,
codec, source HTTP, fit or drift search is imported or executed.
"""
from __future__ import annotations

import time
START = time.monotonic()
import argparse
import csv
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import zipfile

sys.dont_write_bytecode = True
FAMILY = 'radio_s2017_saved_profile_aggregate_qa_20261010'
PRODUCER = 'radio_s2017_saved_profile_aggregate_20261010'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
ON_INDICES, OFF_INDICES = (0, 2, 4), (1, 3, 5)
LIMITS = {'CPU_seconds': 120, 'wall_seconds': 600, 'memory_bytes': 1073741824,
          'output_bytes': 33554432, 'shared_workspace_bytes': 12884901888}
ABS_TOL = REL_TOL = 1e-12
SOURCE_ARRAYS = {
    'logical_geometry_indices': ('<i4', (1905, 6)),
    'logical_times_seconds_from_original_reference': ('<f8', (1905, 6, 16)),
    'geometry_source_channel_centers': ('<i8', (11369, 16)),
    'geometry_scan_indices': ('<i2', (11369,)),
    'geometry_width_channels': ('<i2', (11369,)),
    'source_channel_offsets': ('<i8', (129,)),
    'scans': ('<U10', (6,)),
    'saved_full_native_row_medians': ('<f8', (6, 16)),
    'geometry_center_row_normalized_power': ('<f8', (11369, 16)),
    'geometry_flank_median_row_normalized_power': ('<f8', (11369, 16)),
    'geometry_center_minus_flank_rows': ('<f8', (11369, 16)),
    'geometry_raw_width_mean_power': ('<f4', (11369, 16)),
    'geometry_mean_raw_frequency_profile': ('<f4', (11369, 129)),
    'geometry_mean_row_normalized_frequency_profile': ('<f8', (11369, 129)),
    'geometry_mean_normalized_minus_flank_frequency_profile': ('<f8', (11369, 129)),
    'geometry_raw_row_SHA256': ('|u1', (11369, 16, 32)),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def own_path(root, value):
    require(type(value) is str and value and '\\' not in value, 'Own canonical pin path required')
    p = Path(value)
    require('..' not in p.parts and str(p) == value, 'Canonical pin spelling required')
    if not p.is_absolute():
        p = root / p
    require(p.resolve() == p and any(p.is_relative_to(r) for r in
            (root, root.parent / 'seti_fullpower_work')), 'Pin must be in the own repository or private workspace')
    return p


def verify_pin(root, pin):
    require(type(pin) is dict and set(pin) == {'path', 'bytes', 'sha256'}
            and type(pin['bytes']) is int and 0 < pin['bytes'] <= 268435456
            and type(pin['sha256']) is str and re.fullmatch('[0-9a-f]{64}', pin['sha256']),
            'Bounded exact file pin required')
    p = own_path(root, pin['path'])
    require(p.is_file() and p.stat().st_size == pin['bytes'] and digest(p) == pin['sha256'],
            'Input byte pin differs: ' + pin['path'])
    return p


def file_pin(root, p):
    require(p.resolve() == p and p.is_relative_to(root), 'Own source pin required')
    return {'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}


def load_json(root, pin):
    p = verify_pin(root, pin)
    require(p.suffix == '.json' and p.stat().st_size <= 33554432, 'Bounded pinned JSON required')
    return json.loads(p.read_bytes())


def close_number(actual, expected, name):
    require(type(actual) in (int, float) and math.isfinite(actual)
            and math.isfinite(expected)
            and math.isclose(float(actual), float(expected), rel_tol=REL_TOL, abs_tol=ABS_TOL),
            'Independent fsum numeric check differs: ' + name)


def fsum_mean(values):
    values = [float(x) for x in values]
    require(values and all(math.isfinite(x) for x in values), 'Finite nonempty saved vector required')
    result = math.fsum(values) / len(values)
    require(math.isfinite(result), 'Independent saved-vector mean is not finite')
    return result


def independent_scan_metrics(rows):
    require(len(rows) == 16, 'Exactly16 saved residual rows required')
    values = [float(x) for x in rows]
    mean = fsum_mean(values)
    first, last = fsum_mean(values[:8]), fsum_mean(values[8:])
    positive = sum(x > 0 for x in values)
    return {'mean': mean, 'first_eight_mean': first, 'last_eight_mean': last,
            'minimum_half_mean': min(first, last), 'positive_rows': positive,
            'mean_positive': mean > 0, 'both_halves_positive': first > 0 and last > 0,
            'all_rows_positive': positive == 16}


def independent_windows(curve, width):
    require(len(curve) == 129 and type(width) is int and width in (1, 3),
            'Saved129 curve and original width1/3 required')
    values = [float(x) for x in curve]
    require(all(math.isfinite(x) for x in values), 'Finite saved frequency curve required')
    radius = width // 2
    return [(center - 64, fsum_mean(values[center - radius:center + radius + 1]))
            for center in range(radius, 129 - radius)]


def maximum_window(curve, width):
    candidates = independent_windows(curve, width)
    # Traversal is increasing offset and strict improvement keeps its first
    # occurrence when the independently computed doubles are exactly equal.
    offset, maximum = candidates[0]
    for current_offset, value in candidates[1:]:
        if value > maximum:
            offset, maximum = current_offset, value
    return maximum, offset, candidates


def tree_bytes(path):
    total = 0
    for base, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [x for x in dirs if not (Path(base) / x).is_symlink()]
        for name in files:
            p = Path(base) / name
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
    return total


def usage():
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_since_module_clock': time.monotonic() - START,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def check_caps(out, roots, reserve=0):
    used = usage()
    require(used['process_CPU_seconds_including_imports'] <= LIMITS['CPU_seconds']
            and used['wall_seconds_since_module_clock'] <= LIMITS['wall_seconds']
            and used['peak_RSS_bytes'] <= LIMITS['memory_bytes'], 'Independent aggregate QA resource cap exceeded')
    require(tree_bytes(out) + reserve <= LIMITS['output_bytes']
            and sum(tree_bytes(p) for p in roots) + reserve <= LIMITS['shared_workspace_bytes'],
            'Independent aggregate QA disk cap exceeded')
    return used


def save_new(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def pin_identity(root, a, b):
    return own_path(root, a['path']) == own_path(root, b['path']) and a['bytes'] == b['bytes'] and a['sha256'] == b['sha256']


def admitted_pin(root, pin, pins):
    p = own_path(root, pin['path'])
    require(pins.get(str(p)) == pin, 'Explicit input is absent from exact late QA inventory')
    return p


def admit(root, manifest, qa_freeze):
    require(manifest['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_QA_INPUT_MANIFEST_V1'
            and manifest['family_id'] == FAMILY and manifest['producer_family_id'] == PRODUCER
            and manifest['all_pinned_own_source_producers_and_aggregate_closed'] is True
            and manifest['no_retry'] is True and manifest['limits'] == LIMITS,
            'Pinned finite closed source/producer QA admission required')
    require(manifest['qa_worker_pin'] == file_pin(root, Path(__file__)), 'Frozen independent QA source differs')
    inputs = manifest['input_file_pins']
    require(type(inputs) is list and 0 < len(inputs) <= 128
            and len({str(own_path(root, p['path'])) for p in inputs}) == len(inputs),
            'Unique finite own input pins required')
    pins = {str(verify_pin(root, p)): p for p in inputs}
    for key in ('producer_scope_pin', 'producer_worker_pin', 'producer_execution_pin',
                'producer_aggregate_pin', 'producer_whole_closed_pin', 'producer_marker_pin'):
        admitted_pin(root, manifest[key], pins)
    scope = load_json(root, manifest['producer_scope_pin'])
    execution = load_json(root, manifest['producer_execution_pin'])
    aggregate = load_json(root, manifest['producer_aggregate_pin'])
    whole = load_json(root, manifest['producer_whole_closed_pin'])
    marker = load_json(root, manifest['producer_marker_pin'])
    freeze = manifest['producer_public_freeze_commit']
    require(type(freeze) is str and re.fullmatch('[0-9a-f]{40}', freeze)
            and re.fullmatch('[0-9a-f]{40}', qa_freeze), 'Actual producer/QA public freezes required')
    require(scope['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_SCOPE_V1'
            and scope['family_id'] == PRODUCER and scope['scans'] == list(SCANS)
            and scope['script_sha256'] == manifest['producer_worker_pin']['sha256']
            and scope['source_measurement_closed_and_immutable'] is True
            and (scope['CPU_cap_s'], scope['CPU_hard_limit_s'], scope['wall_cap_s'], scope['memory_cap_bytes'],
                 scope['output_cap_bytes'], scope['shared_workspace_cap_bytes']) == (120, 122, 600, 1073741824, 33554432, 12884901888),
            'Exact finite producer scope required')
    require(execution['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_EXECUTION_V1'
            and execution['status'] == 'COMPLETE_1905_SAVED_PROFILE_AGGREGATES_EXPLORATORY_ONLY'
            and execution['family_id'] == PRODUCER
            and execution['scope_sha256'] == manifest['producer_scope_pin']['sha256']
            and execution['script_sha256'] == scope['script_sha256']
            and execution['public_freeze_commit'] == freeze
            and execution['all_input_end_readbacks_exact'] is True
            and execution['resource_caps_satisfied'] is True and execution['no_retry'] is True
            and execution['aggregate_pin'] == manifest['producer_aggregate_pin'],
            'Actual matching producer COMPLETE required')
    require(all(execution[k] is False for k in ('profiles_remeasured', 'profile_kernel_reexecuted',
            'normalization_reexecuted', 'codec_reexecuted', 'native_medians_recomputed', 'HDF5_source_opened'))
            and (execution['new_HTTP_requests'], execution['new_source_BODY_bytes'], execution['cost_DKK'],
                 execution['new_original_detector_hypothesis_combinations']) == (0, 0, 0, 0),
            'Producer must be saved-only without a new original-kernel hypothesis')
    require(marker['family_id'] == PRODUCER and marker['scope_sha256'] == execution['scope_sha256']
            and marker['script_sha256'] == execution['script_sha256']
            and marker['freeze_commit'] == freeze and marker['no_retry'] is True, 'Producer once-marker differs')
    require(whole['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_WHOLE_COMMAND_CLOSED_V1'
            and whole['status'] == 'PASS_CLOSED_EXIT0_COMPLETE_AGGREGATE_RESOURCES'
            and whole['actual_return_code'] == 0 and whole['child_closed_reaped'] is True
            and whole['timed_out'] is False and whole['no_retry'] is True
            and whole['resource_caps_satisfied'] is True
            and whole['public_freeze_commit'] == freeze
            and whole['scope_pin'] == manifest['producer_scope_pin']
            and whole['worker_pin'] == manifest['producer_worker_pin']
            and whole['execution_pin'] == manifest['producer_execution_pin']
            and whole['result_pin'] == manifest['producer_aggregate_pin'],
            'Root must have measured the actual COMPLETE process through closed exit0')
    for key, whole_key, cap in (('process_CPU_seconds', 'CPU_seconds', 120), ('wall_seconds', 'wall_seconds', 600), ('peak_RSS_bytes', 'peak_RSS_bytes', 1073741824)):
        require(type(whole[whole_key]) in (int, float) and math.isfinite(whole[whole_key]) and 0 <= whole[whole_key] <= cap
                and type(execution[key]) in (int, float) and math.isfinite(execution[key])
                and 0 <= execution[key] <= cap, 'Actual complete-command/inner producer resources differ')
    require(execution['source_input_pins'] == aggregate['source_input_pins'] == scope['input_pins'],
            'Exact original own saved-input inventory differs')
    for p in list(scope['input_pins'].values()) + scope.get('dependency_pins', []) + execution['output_pins']:
        admitted_pin(root, p, pins)
    require(aggregate['schema'] == 'SETI_S2017_SAVED_PROFILE_AGGREGATE_V1'
            and aggregate['family_id'] == PRODUCER and aggregate['scope_sha256'] == execution['scope_sha256']
            and aggregate['script_sha256'] == scope['script_sha256']
            and aggregate['public_freeze_commit'] == freeze and aggregate['scans'] == list(SCANS)
            and aggregate['member_count'] == execution['member_count'] == 1905
            and aggregate['triple_count'] == execution['triple_count'] == 635
            and aggregate['unique_geometries'] == execution['unique_geometries'] == 11369
            and aggregate['geometry_aliases'] == execution['geometry_aliases'] == 61
            and aggregate['logical_scan_profiles'] == 11430 and aggregate['old_geometry_overlap'] == 0
            and aggregate['new_original_detector_hypothesis_combinations'] == 0,
            'Complete aggregate counts/identity differ')
    source = {k: load_json(root, p) for k, p in scope['input_pins'].items() if k != 'compact_arrays'
              and own_path(root, p['path']).suffix == '.json'}
    original, original_qa, original_outer = source['source_execution'], source['source_QA'], source['source_outer']
    require(original['status'] == 'COMPLETE_635_S2017_MATCHED_TRIPLES_ALL_SIX_FIXED_PROFILES_EXPLORATORY_ONLY'
            and original_qa['status'] == 'PASS_635_TRIPLES_11430_FIXED_PROFILE_OUTPUTS_AND23465616_RAW_CELL_OCCURRENCE_DIGESTS'
            and original_outer['status'] == 'PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS'
            and original_outer['child_exit_code'] == 0 and original_outer['child_timed_out'] is False
            and original_outer['automatic_retry_performed'] is False
            and original_qa['execution_receipt_sha256'] == original_outer['inner_terminal_sha256']
                == scope['input_pins']['source_execution']['sha256']
            and original_qa['outer_execution_receipt_sha256'] == scope['input_pins']['source_outer']['sha256']
            and original['scope_sha256'] == original_qa['scope_sha256'] == scope['input_pins']['source_scope']['sha256']
            and original['script_sha256'] == original_qa['profile_script_sha256'] == scope['input_pins']['source_script']['sha256']
            and original['public_freeze_commit'] == original_qa['public_profile_freeze_commit'] == original_outer['freeze_commit']
            and original_qa['all_input_end_readbacks_exact'] is True
            and original_qa['original_source_raw_rows_authenticated'] is True
            and original_qa['selected_raw_row_SHA256_digests_independently_matched'] is True,
            'Finite pinned original own source producer/QA/closed0 evidence differs')
    for key, cap in (('child_process_CPU_seconds', 180), ('child_wall_seconds', 1800), ('child_peak_RSS_bytes', 1073741824)):
        require(type(original_outer[key]) in (int, float) and math.isfinite(original_outer[key])
                and 0 <= original_outer[key] <= cap, 'Original closed producer resource evidence differs')
    require(source['profile_index']['ordered_geometry_sha256'] == original['ordered_geometry_sha256']
            == original_qa['ordered_geometry_sha256'] == scope['ordered_geometry_sha256']
            and original['selected_members_sha256'] == original_qa['selected_members_sha256']
                == scope['selected_members_sha256'], 'Original ordered membership/geometry proof differs')
    roots = [Path(p) for p in scope['shared_workspace_roots']]
    require(roots and len(roots) == len(set(roots)) and all(p.is_absolute() and p.resolve() == p and p.is_dir() for p in roots)
            and all(not p.is_relative_to(q) for p in roots for q in roots if p != q)
            and any(root.is_relative_to(p) for p in roots), 'Canonical complete disjoint shared-storage roots required')
    return scope, execution, aggregate, source, pins, roots


def source_members(root, scope, source):
    index = source['profile_index']
    require(index['schema'] == 'SETI_S2017_CROSS_ON_ALL_SIX_FIXED_PROFILES_V1'
            and index['complete'] is True and index['selected_members'] == 1905
            and index['selected_triples'] == 635 and index['unique_geometries'] == 11369
            and index['new_geometry_aliases'] == 61 and index['old_geometry_aliases'] == 0
            and pin_identity(root, index['compact_arrays_pin'], scope['input_pins']['compact_arrays']),
            'Exact original profile index and compact bytes required')
    require(len(index['origin_record_files']) == 3, 'All three origin inventories required')
    members = [None] * 1905
    for origin_index, origin in enumerate(ONS):
        declared = index['origin_record_files'][origin_index]
        doc = source['profiles_' + origin]
        require(declared['originating_ON'] == origin and declared['logical_member_count'] == 635
                and pin_identity(root, declared['file_pin'], scope['input_pins']['profiles_' + origin])
                and doc['schema'] == index['schema'] and doc['family_id'] == index['family_id']
                and doc['originating_ON'] == origin and len(doc['records']) == 635,
                'Full original ordered origin shard differs')
        for triple_index, record in enumerate(doc['records']):
            j = 3 * triple_index + origin_index
            require(record['logical_member_index'] == j and members[j] is None
                    and record['member_scan_id'] == record['original_member']['scan_id'] == origin
                    and record['original_member']['original_key']['scan_id'] == origin
                    and len(record['scan_profiles']) == 6
                    and [p['scan_id'] for p in record['scan_profiles']] == list(SCANS),
                    'Original logical order/origin/six-scan identity differs')
            members[j] = record
    require(all(x is not None for x in members), 'Missing original logical member')
    identities = set()
    matches = set()
    selected = []
    for j, r in enumerate(members):
        k = r['original_member']['original_key']
        require(type(k['width_channels']) is int and k['width_channels'] in (1, 3), 'Original width is not1/3')
        key = (k['visit'], k['scan_id'], k['source_reference_channel'], float(k['reference_seconds_from_anchor']).hex(),
               float(k['drift_hz_s']).hex(), k['width_channels'])
        require(key not in identities, 'Duplicate original member hypothesis')
        identities.add(key)
        selected.append({k: r[k] for k in ('match_id', 'original_display_rank', 'member_scan_id', 'original_member')})
        if j % 3 == 0:
            group = members[j:j + 3]
            require(len({x['match_id'] for x in group}) == len({x['original_display_rank'] for x in group}) == 1
                    and [x['member_scan_id'] for x in group] == list(ONS)
                    and r['match_id'] not in matches, '635 triple membership/order differs')
            matches.add(r['match_id'])
    require(len(matches) == 635 and len(identities) == 1905, 'Full original membership inventory differs')
    selection_sha = hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    require(selection_sha == scope['selected_members_sha256'], 'Independent ordered member digest differs')
    return members


def load_source_arrays(np, root, scope):
    path = verify_pin(root, scope['input_pins']['compact_arrays'])
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) == 16 and set(names) == {k + '.npy' for k in SOURCE_ARRAYS}
                and sum(x.file_size for x in z.infolist()) <= 134217728, 'Exact bounded original16-array NPZ required')
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == set(SOURCE_ARRAYS), 'Original NPZ logical field inventory differs')
        arrays = {k: saved[k] for k in SOURCE_ARRAYS}
    for k, (dtype, shape) in SOURCE_ARRAYS.items():
        a = arrays[k]
        require(a.dtype.str == dtype and a.shape == shape and not a.dtype.hasobject,
                'Original saved dtype/shape differs: ' + k)
        if a.dtype.kind == 'f':
            require(np.isfinite(a).all(), 'Nonfinite original saved profile field: ' + k)
    require(arrays['scans'].tolist() == list(SCANS)
            and arrays['source_channel_offsets'].tolist() == list(range(-64, 65)), 'Original scan/offset lattice differs')
    mapping, scans, widths = (arrays[k] for k in ('logical_geometry_indices', 'geometry_scan_indices', 'geometry_width_channels'))
    flat = [int(g) for row in mapping for g in row]
    require(set(flat) == set(range(11369)) and len(flat) - len(set(flat)) == 61
            and all(int(scans[int(mapping[j, s])]) == s for j in range(1905) for s in range(6))
            and all(int(w) in (1, 3) for w in widths), 'Every11369 geometry and61 alias mapping required')
    centers = arrays['geometry_source_channel_centers']
    geometries = [(SCANS[int(scans[g])], int(widths[g]), tuple(int(c) for c in centers[g])) for g in range(11369)]
    require(len(set(geometries)) == 11369, 'Unique saved geometry identity differs')
    serialized = [[s, w, list(c)] for s, w, c in geometries]
    geometry_sha = hashlib.sha256(json.dumps(serialized, separators=(',', ':')).encode()).hexdigest()
    require(geometry_sha == scope['ordered_geometry_sha256'], 'Independent ordered geometry digest differs')
    return arrays


def rounded_window_mean(values):
    """Independent scalar recreation of NumPy's tiny width1/3 sum order.

    Numerical certification uses fsum separately. This scalar order is used
    only to check the producer's exact binary64 tie/lowest-offset convention.
    """
    total = -0.0
    for x in values:
        total += float(x)
    return total / len(values)


def local_window_certificate(curve, width, saved_maximum, saved_offset):
    maximum, _, candidates = maximum_window(curve, width)
    close_number(saved_maximum, maximum, 'OFF local-window global maximum')
    require(type(saved_offset) is int and saved_offset in dict(candidates), 'OFF local-window offset outside full support')
    close_number(dict(candidates)[saved_offset], maximum, 'Reported OFF window must attain the global maximum within fixed tolerance')
    # Verify exact ties with a separate scalar implementation of the original
    # width1/3 summation, while fsum verifies every maximum numerically.
    radius = width // 2
    rounded = [(c - 64, rounded_window_mean(curve[c - radius:c + radius + 1]))
               for c in range(radius, 129 - radius)]
    rounded_max = max(v for _, v in rounded)
    exact_first = next(o for o, v in rounded if v == rounded_max)
    require(saved_offset == exact_first and saved_maximum == rounded_max,
            'Original binary64 maximum/tie-lowest-offset differs')
    return maximum


def check_saved_aggregate(np, root, manifest, scope, execution, aggregate, source, pins):
    members = source_members(root, scope, source)
    arrays = load_source_arrays(np, root, scope)
    mapping, scans, widths = (arrays[k] for k in ('logical_geometry_indices', 'geometry_scan_indices', 'geometry_width_channels'))
    residuals = arrays['geometry_center_minus_flank_rows']
    curves = arrays['geometry_mean_normalized_minus_flank_frequency_profile']
    certificates = [independent_scan_metrics(residuals[g]) for g in range(11369)]
    records = aggregate['records']
    require(len(records) == 1905, 'Exactly1905 completed logical records required')
    flags = ['all_' + role + '_' + category + '_positive' for role in ('ON', 'OFF') for category in ('means', 'halves', 'rows')]
    metrics = ('mean', 'first_eight_mean', 'last_eight_mean', 'minimum_half_mean')
    gaps = ('signed_worst_mean_gap', 'signed_worst_half_gap', 'signed_neighborhood_gap')
    scalar_fields = ('min_ON_mean', 'max_OFF_mean', 'min_ON_half_mean', 'max_OFF_half_mean', 'max_OFF_local_window') + gaps
    local_certificates = {}
    for j, (record, old) in enumerate(zip(records, members)):
        gs = [int(x) for x in mapping[j]]
        require(record['logical_member_index'] == j and record['match_id'] == old['match_id']
                and record['original_display_rank'] == old['original_display_rank']
                and record['originating_ON'] == record['member_scan_id'] == old['member_scan_id']
                and record['original_member'] == old['original_member']
                and record['geometry_indices'] == gs and record['width_channels'] == old['original_member']['original_key']['width_channels']
                and record['drift_hz_s'] == old['original_member']['original_key']['drift_hz_s']
                and len(record['scan_metrics']) == 6, 'Full logical original membership/track identity differs')
        local_values = {}
        for s, (m, g) in enumerate(zip(record['scan_metrics'], gs)):
            cert = certificates[g]
            require(m['scan_id'] == SCANS[s] and m['geometry_index'] == g
                    and m['target_role'] == ('ON' if s in ON_INDICES else 'OFF')
                    and old['scan_profiles'][s]['geometry_index'] == g
                    and old['scan_profiles'][s]['row_array_ref'] == {'file': 'COMPACT_FIXED_PROFILES.npz',
                        'array': 'geometry_center_minus_flank_rows', 'index': g}
                    and int(widths[g]) == record['width_channels'], 'Saved six-scan geometry/width/index differs')
            for k in metrics:
                close_number(m[k], cert[k], 'logical%d/%s/%s' % (j, SCANS[s], k))
            require(type(m['positive_rows']) is int and m['positive_rows'] == cert['positive_rows']
                    and type(m['all_rows_positive']) is bool and m['all_rows_positive'] == cert['all_rows_positive']
                    and type(m['mean_positive']) is bool and m['mean_positive'] == (m['mean'] > 0)
                    and type(m['both_halves_positive']) is bool
                    and m['both_halves_positive'] == (m['first_eight_mean'] > 0 and m['last_eight_mean'] > 0),
                    'Exact saved-row signs or stored-binary64 mean flags differ')
            if s in OFF_INDICES:
                if g not in local_certificates:
                    local_certificates[g] = local_window_certificate(curves[g], int(widths[g]),
                        m['local_window_maximum'], m['local_window_center_offset_channels'])
                else:
                    close_number(m['local_window_maximum'], local_certificates[g], 'Aliased OFF local maximum')
                    local_window_certificate(curves[g], int(widths[g]), m['local_window_maximum'], m['local_window_center_offset_channels'])
                local_values[s] = local_certificates[g]
            else:
                require('local_window_maximum' not in m and 'local_window_center_offset_channels' not in m,
                        'OFF-only neighborhood fields appeared in ON record')
        expected = {
            'min_ON_mean': min(certificates[gs[s]]['mean'] for s in ON_INDICES),
            'max_OFF_mean': max(certificates[gs[s]]['mean'] for s in OFF_INDICES),
            'min_ON_half_mean': min(certificates[gs[s]][k] for s in ON_INDICES for k in ('first_eight_mean', 'last_eight_mean')),
            'max_OFF_half_mean': max(certificates[gs[s]][k] for s in OFF_INDICES for k in ('first_eight_mean', 'last_eight_mean')),
            'max_OFF_local_window': max(local_values.values()),
        }
        expected.update(signed_worst_mean_gap=expected['min_ON_mean'] - expected['max_OFF_mean'],
                        signed_worst_half_gap=expected['min_ON_half_mean'] - expected['max_OFF_half_mean'],
                        signed_neighborhood_gap=expected['min_ON_mean'] - expected['max_OFF_local_window'])
        for k in scalar_fields:
            close_number(record[k], expected[k], 'logical%d/%s' % (j, k))
        for role, ids in (('ON', ON_INDICES), ('OFF', OFF_INDICES)):
            for category, field in (('means', 'mean_positive'), ('halves', 'both_halves_positive'), ('rows', 'all_rows_positive')):
                key = 'all_' + role + '_' + category + '_positive'
                require(type(record[key]) is bool and record[key] == all(record['scan_metrics'][s][field] for s in ids),
                        'Logical role flag differs')
    rank_mean = sorted(range(1905), key=lambda j: (-records[j]['signed_worst_mean_gap'], j))
    rank_local = sorted(range(1905), key=lambda j: (-records[j]['signed_neighborhood_gap'], j))
    require(aggregate['rank_by_signed_worst_mean_gap'] == rank_mean
            and aggregate['rank_by_signed_neighborhood_gap'] == rank_local
            and aggregate['rank_tie_rule'] == 'Metric descending, logical_member_index ascending',
            'All1905 exact stored-metric ranks/tie keys differ')
    triples = []
    for t in range(635):
        group = records[3 * t:3 * t + 3]
        triples.append({'match_id': group[0]['match_id'], 'original_display_rank': group[0]['original_display_rank'],
            'logical_member_indices': [3 * t, 3 * t + 1, 3 * t + 2],
            'member_flag_counts': {k: sum(r[k] for r in group) for k in flags},
            **{'members_with_positive_' + k: sum(r[k] > 0 for r in group) for k in gaps}})
    require(aggregate['triple_records'] == triples, 'All635 exact triple memberships/flag counts differ')
    counts = {k: sum(r[k] for r in records) for k in flags}
    counts.update({k + '_positive': sum(r[k] > 0 for r in records) for k in gaps})
    require(aggregate['descriptive_counts'] == counts, 'Complete descriptive count totals differ')
    selected = records[rank_mean[0]].copy()
    selected.update(selection_rule='First in signed_worst_mean_gap descending, logical_member_index ascending',
        source_channel_offsets=list(range(-64, 65)), df_hz=-2.7939677238464355, fch1_hz=2802832031.25,
        scan_profiles=[{'scan_id': SCANS[s], 'geometry_index': int(g),
            'mean_normalized_minus_flank_frequency_profile': [float(v) for v in curves[int(g)]]}
            for s, g in enumerate(mapping[rank_mean[0]])])
    require(aggregate['selected_display_case'] == selected, 'Display selection and all six original129-cell curves differ')
    check_derived_arrays(np, root, aggregate, arrays, certificates, records, pins)
    check_csv(root, execution, records, pins)
    producer_out = root / 'results' / PRODUCER / 'measurement'
    expected_names = {'INPUT_PINS.json', 'GEOMETRY_AGGREGATE.npz', 'SAVED_PROFILE_AGGREGATE.json',
                      'MEMBER_METRICS.csv', 'EXECUTION_RECEIPT.json', 'EXECUTION_RECEIPT.prepared.json'}
    require({p.name for p in producer_out.iterdir()} == expected_names
            and all(p.is_file() and not p.is_symlink() for p in producer_out.iterdir()),
            'Exact completed producer output inventory differs')
    for name in expected_names:
        require(str(producer_out / name) in pins, 'Missing completed output byte pin: ' + name)
    require(pins[str(producer_out / 'EXECUTION_RECEIPT.prepared.json')]['bytes']
                == pins[str(producer_out / 'EXECUTION_RECEIPT.json')]['bytes']
            and pins[str(producer_out / 'EXECUTION_RECEIPT.prepared.json')]['sha256']
                == pins[str(producer_out / 'EXECUTION_RECEIPT.json')]['sha256'],
            'Prepared terminal alias must match the canonical terminal bytes')
    ip = pins[str(producer_out / 'INPUT_PINS.json')]
    original_inputs = load_json(root, ip)
    require(original_inputs['schema'] == 'SETI_S2017_AGGREGATE_INPUT_PINS_V1'
            and original_inputs['scope_sha256'] == execution['scope_sha256']
            and original_inputs['script_sha256'] == execution['script_sha256']
            and original_inputs['public_freeze_commit'] == execution['public_freeze_commit']
            and original_inputs['input_pins'] == scope['input_pins']
            and original_inputs['dependency_pins'] == scope.get('dependency_pins', []), 'Original aggregate INPUT_PINS differs')
    return {'logical_members_verified': 1905, 'triple_memberships_verified': 635, 'origin_inventories_verified': 3,
            'unique_saved_geometries_verified': 11369, 'logical_geometry_aliases_verified': 61,
            'logical_six_scan_metrics_verified': 11430, 'logical_saved_residual_rows_verified': 182880,
            'rank_lists_verified': 2, 'complete_rank_entries_verified': 3810,
            'OFF_unique_local_windows_verified': len(local_certificates), 'selected_original_curve_cells_verified': 774,
            'numeric_comparison_abs_tolerance': ABS_TOL, 'numeric_comparison_rel_tolerance': REL_TOL,
            'mean_flags_follow_exact_producer_stored_binary64': True,
            'rank_ties_follow_exact_producer_stored_binary64_then_member_index': True,
            'row_positive_counts_follow_saved_residual_gt_zero_exactly': True}


def check_derived_arrays(np, root, aggregate, source_arrays, certificates, records, pins):
    pin = aggregate['derived_geometry_arrays_pin']
    admitted_pin(root, pin, pins)
    expected_keys = {'source_geometry_indices', 'geometry_scan_indices', 'geometry_width_channels',
        'geometry_mean', 'geometry_first_eight_mean', 'geometry_last_eight_mean', 'geometry_positive_rows',
        'geometry_OFF_local_window_maximum', 'geometry_OFF_local_window_center_offset', 'logical_geometry_indices'}
    path = verify_pin(root, pin)
    with zipfile.ZipFile(path) as z:
        require(len(z.namelist()) == len(set(z.namelist())) == 10
                and set(z.namelist()) == {k + '.npy' for k in expected_keys}
                and sum(x.file_size for x in z.infolist()) <= 4194304, 'Bounded ten-field derived NPZ required')
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == expected_keys, 'Derived geometry field inventory differs')
        derived = {k: saved[k] for k in expected_keys}
    for k in ('geometry_scan_indices', 'geometry_width_channels', 'logical_geometry_indices'):
        require(derived[k].dtype == source_arrays[k].dtype and derived[k].shape == source_arrays[k].shape
                and np.array_equal(derived[k], source_arrays[k]), 'Derived original geometry/index array differs: ' + k)
    require(derived['source_geometry_indices'].dtype.str == '<i4'
            and derived['source_geometry_indices'].tolist() == list(range(11369)), 'Derived geometry ordinal inventory differs')
    for k in ('geometry_mean', 'geometry_first_eight_mean', 'geometry_last_eight_mean', 'geometry_OFF_local_window_maximum'):
        require(derived[k].shape == (11369,) and derived[k].dtype.str == '<f8'
                and np.isfinite(derived[k]).all(), 'Derived numeric geometry field differs: ' + k)
    for k in ('geometry_positive_rows', 'geometry_OFF_local_window_center_offset'):
        require(derived[k].shape == (11369,) and derived[k].dtype.str == '<i2', 'Derived integer geometry field differs: ' + k)
    first_seen = {}
    for r in records:
        for m in r['scan_metrics']:
            first_seen.setdefault(m['geometry_index'], m)
    require(set(first_seen) == set(range(11369)), 'Every derived geometry must be represented by a logical member')
    for g in range(11369):
        cert, metric = certificates[g], first_seen[g]
        for array_key, record_key in (('geometry_mean', 'mean'), ('geometry_first_eight_mean', 'first_eight_mean'),
                                       ('geometry_last_eight_mean', 'last_eight_mean')):
            close_number(float(derived[array_key][g]), cert[record_key], array_key)
            require(float(derived[array_key][g]) == metric[record_key], 'Derived NPZ/JSON numeric identity differs')
        require(int(derived['geometry_positive_rows'][g]) == cert['positive_rows'], 'Derived exact row-sign count differs')
        if int(source_arrays['geometry_scan_indices'][g]) in OFF_INDICES:
            require(float(derived['geometry_OFF_local_window_maximum'][g]) == metric['local_window_maximum']
                    and int(derived['geometry_OFF_local_window_center_offset'][g]) == metric['local_window_center_offset_channels'],
                    'Derived OFF local-window NPZ/JSON identity differs')
        else:
            require(float(derived['geometry_OFF_local_window_maximum'][g]) == 0.0
                    and int(derived['geometry_OFF_local_window_center_offset'][g]) == 0,
                    'ON entries of OFF-only derived fields must be original zero placeholders')


def check_csv(root, execution, records, pins):
    out = root / 'results' / PRODUCER / 'measurement'
    pin = pins.get(str(out / 'MEMBER_METRICS.csv'))
    require(pin is not None and pin in execution['output_pins'], 'Completed CSV output pin missing')
    path = verify_pin(root, pin)
    columns = ['logical_member_index', 'match_id', 'original_display_rank', 'originating_ON', 'drift_hz_s',
        'width_channels', 'min_ON_mean', 'max_OFF_mean', 'min_ON_half_mean', 'max_OFF_half_mean',
        'max_OFF_local_window', 'signed_worst_mean_gap', 'signed_worst_half_gap', 'signed_neighborhood_gap',
        'all_ON_means_positive', 'all_ON_halves_positive', 'all_ON_rows_positive',
        'all_OFF_means_positive', 'all_OFF_halves_positive', 'all_OFF_rows_positive']
    per_scan = ['mean', 'first_eight_mean', 'last_eight_mean', 'minimum_half_mean', 'positive_rows',
                'mean_positive', 'both_halves_positive', 'all_rows_positive']
    for s, scan in enumerate(SCANS):
        columns.extend(scan + '_' + k for k in per_scan)
        if s in OFF_INDICES:
            columns.extend([scan + '_local_window_maximum', scan + '_local_window_center_offset_channels'])
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        require(reader.fieldnames == columns, 'Complete flattened six-scan CSV column order differs')
        for r in records:
            actual = next(reader, None)
            require(actual is not None, 'CSV omits a logical member')
            expected = {k: str(r[k]) for k in columns[:20]}
            for s, scan in enumerate(SCANS):
                fields = per_scan + (['local_window_maximum', 'local_window_center_offset_channels'] if s in OFF_INDICES else [])
                expected.update({scan + '_' + k: str(r['scan_metrics'][s][k]) for k in fields})
            require(actual == expected, 'Flattened CSV membership/numerical value differs')
        require(next(reader, None) is None, 'Extra CSV logical member')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'input-manifest', 'expected-input-manifest-sha256', 'qa-freeze-commit'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--root-go-after-aggregate-closed', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    require(root.is_absolute() and root.resolve() == root and root.is_dir(), 'Canonical own root required')
    require(args.root_go_after_aggregate_closed and re.fullmatch('[0-9a-f]{40}', args.qa_freeze_commit),
            'Actual public freeze and single root QA GO required')
    def deadline(*_):
        raise TimeoutError('Independent saved aggregate QA deadline reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 122))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, math.ceil(LIMITS['wall_seconds'] - (time.monotonic() - START))))
    stage = root / 'results' / FAMILY
    stage.mkdir(parents=True, exist_ok=True)
    review, marker = stage / 'review', stage / 'QA_STARTED_ONCE.json'
    handles, identities, claimed, committed = [], [], False, False
    try:
        qa_guard = stage / 'QA_SERIAL.flock'
        fd = os.open(qa_guard, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        handles.append(fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identities.append((qa_guard, os.fstat(fd)))
        require(not marker.exists() and not review.exists() and not (stage / 'FAILURE_RECEIPT.json').exists(),
                'No independent QA retry/resume or output replacement')
        save_new(marker, {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_QA_STARTED_V1', 'family_id': FAMILY,
            'qa_script_sha256': digest(Path(__file__)), 'qa_public_freeze_commit': args.qa_freeze_commit,
            'input_manifest_sha256': args.expected_input_manifest_sha256, 'no_retry': True})
        claimed = True
        mp = Path(args.input_manifest)
        require(mp == stage / 'QA_INPUT_MANIFEST.json' and mp.resolve() == mp and mp.is_file()
                and mp.stat().st_size <= 1048576
                and digest(mp) == args.expected_input_manifest_sha256
                and re.fullmatch('[0-9a-f]{64}', args.expected_input_manifest_sha256),
                'Exact bounded late root QA manifest required')
        manifest_pin = file_pin(root, mp)
        manifest = load_json(root, manifest_pin)
        producer_guard = root / 'results' / PRODUCER / 'AGGREGATE_SERIAL.flock'
        require(manifest['producer_guard_path'] == producer_guard.relative_to(root).as_posix()
                and producer_guard.resolve() == producer_guard and producer_guard.is_file(),
                'Existing own producer guard required')
        fd = os.open(producer_guard, os.O_RDONLY | os.O_NOFOLLOW)
        handles.append(fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identities.append((producer_guard, os.fstat(fd)))
        for p, st in identities:
            now = p.stat()
            require((now.st_dev, now.st_ino) == (st.st_dev, st.st_ino), 'Own guard inode was replaced')
        scope, execution, aggregate, source, pins, roots = admit(root, manifest, args.qa_freeze_commit)
        review.mkdir(exist_ok=False)
        check_caps(review, roots, 1048576)
        require(importlib.metadata.version('numpy') == '2.3.5', 'Exact frozen primary NumPy required')
        require(os.environ.get('PYTHONPATH') == str(root.parent / 'seti_fullpower_work/deps')
                and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1', 'Readonly pinned dependency environment required')
        for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            require(os.environ.get(key) == '1', 'Single-thread NumPy environment required')
        import numpy as np
        summary = check_saved_aggregate(np, root, manifest, scope, execution, aggregate, source, pins)
        for pin in manifest['input_file_pins']:
            verify_pin(root, pin)
        verify_pin(root, manifest_pin)
        require(manifest['qa_worker_pin'] == file_pin(root, Path(__file__)), 'Independent QA source changed')
        for p, st in identities:
            now = p.stat()
            require((now.st_dev, now.st_ino) == (st.st_dev, st.st_ino), 'Own guard inode changed before closure')
        measured = check_caps(review, roots, 1048576)
        receipt = {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_INDEPENDENT_QA_V1',
            'status': 'PASS_SAVED_2017_AGGREGATE_COMPLETE_INDEPENDENT_ARITHMETIC_QA', 'family_id': FAMILY,
            'qa_script_pin': manifest['qa_worker_pin'], 'qa_public_freeze_commit': args.qa_freeze_commit,
            'input_manifest_pin': manifest_pin, 'aggregate_pin': manifest['producer_aggregate_pin'],
            'aggregate_execution_pin': manifest['producer_execution_pin'], 'aggregate_scope_pin': manifest['producer_scope_pin'],
            'aggregate_whole_closed_pin': manifest['producer_whole_closed_pin'],
            'public_aggregate_freeze_commit': manifest['producer_public_freeze_commit'],
            'all_input_end_readbacks_exact': True, 'own_guard_inodes_held_and_endchecked': True,
            'input_file_pins': manifest['input_file_pins'], 'limits': LIMITS,
            'resource_caps_satisfied_before_terminal_publication': True,
            'downstream_requires_QA_process_closed_exit0_and_root_resource_measurement': True,
            'arithmetic': 'Independent stdlib math.fsum on original saved16/8 rows and width1/3 windows; scalar binary64 tiny-window tie check.',
            'original_profile_kernel_reexecuted': False, 'original_normalization_reexecuted': False,
            'original_detector_reexecuted': False, 'HDF5_opened': False, 'source_codec_decoded': False,
            'HTTP_requests': 0, 'new_scientific_fit_or_refit': False,
            'new_original_kernel_hypothesis_combinations': 0,
            'independent_validation_or_sky_origin_claim': False,
            'raw_source_authentication_limit': 'Pinned saved profiles and prior original raw-row SHA QA; no new source or codec authentication.',
            **summary, **measured}
        terminal, pending = review / 'QA_RECEIPT.json', review / 'QA_RECEIPT.prepared.json'
        save_new(pending, receipt)
        final = check_caps(review, roots, 65536)
        require(final['process_CPU_seconds_including_imports'] + .1 < 120
                and final['wall_seconds_since_module_clock'] + 2 < 600, 'Independent QA terminal headroom required')
        signal.alarm(0)
        signal.signal(signal.SIGXCPU, signal.SIG_IGN)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGXCPU, signal.SIGTERM, signal.SIGINT, signal.SIGHUP})
        try:
            os.link(pending, terminal)
            committed = True
            pending.unlink()
            fd = os.open(review, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
    except BaseException as error:
        if claimed and not committed:
            save_new(stage / 'FAILURE_RECEIPT.json', {'schema': 'SETI_S2017_SAVED_PROFILE_AGGREGATE_QA_FAILURE_V1',
                'status': 'FAILED_INDEPENDENT_SAVED_AGGREGATE_QA_NO_RETRY', 'error_type': type(error).__name__,
                'error': str(error), 'qa_public_freeze_commit': args.qa_freeze_commit,
                'input_manifest_sha256': args.expected_input_manifest_sha256, **usage()})
        raise
    finally:
        signal.alarm(0)
        for fd in reversed(handles):
            os.close(fd)


if __name__ == '__main__':
    main()
