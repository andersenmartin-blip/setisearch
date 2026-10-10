#!/usr/bin/env python3
"""One-shot descriptive cross-ON matching of authenticated S2017 maxima.

No detector, preprocessing, HDF5 loader, source acquisition or profile code is
imported. The new rule operates only on the seven arrays already saved per map.
Run only after the exact scope/code are public and root has admitted durable,
closed, QA-complete inputs. A failed attempt consumes this family's attempt.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import stat
import sys
import time

FAMILY = 'radio_s2017_cross_on_storage_recovery_20261010'
SCHEMA = 'SETI_S2017_SAVED_MAXIMA_MUTUAL_CROSS_ON_V1'
ONS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
C0, COUNT, CORE = 179306496, 1048576, 4096
N = 254 * CORE
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
GRID_COUNT, GRID_STEP = 785, 8.0 / 784
CPU_CAP, WALL_CAP, MEMORY_CAP = 120.0, 1800.0, 1073741824
OUTPUT_CAP, WORKSPACE_CAP = 67108864, 12884901888
TOP_COUNT = 1000
MAP_KEYS = frozenset(('frequency_hz_at_tref', 'maximum_robust_box_track_score',
    'winning_drift_hz_s', 'winning_width_channels', 'valid_hypothesis_count',
    'source_reference_channels', 'drift_grid_hz_s'))
LIMITATIONS = [
    'Posthoc descriptive association within the same 2017 visit; not an independent test.',
    'Each carrier retains only its winning drift and width. Secondary hypotheses are unavailable; no match does not exclude a coherent feature.',
    'The frequency/drift windows are predefined association rules, not calibrated winner uncertainties.',
    'Reciprocal nearest neighbours deliberately omit other eligible combinations. Matches are not an exhaustive physical-feature catalogue.',
    'Stationary receiver-frequency structure, noise and nearby variants can coincide across ON; matches are correlated and do not establish origin.',
    'Minimum saved score is a display ordering only; no score threshold, calibrated joint statistic, SNR, FAP or candidate qualification.',
    'Member widths and original tracks remain unchanged. No consensus track, refit, detector rerun, OFF veto or profile measurement.',
    'Original A/B FAIL_CLOSED, protected holdouts and whole-original-source MD5 limitations remain unchanged.'
]


class ResourceLimitExceeded(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked_file(path):
    path = Path(path)
    require(path.is_absolute(), 'Input/output paths must be absolute')
    require(not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), 'Expected regular non-symlink file')
    require(path.resolve() == path, 'File path must be canonical')
    return path


def verify_pin(pin):
    require(set(pin) == {'path', 'sha256', 'bytes'}, 'Unexpected file pin schema')
    path = checked_file(pin['path'])
    require(type(pin['bytes']) is int and pin['bytes'] >= 0
        and re.fullmatch(r'[0-9a-f]{64}', pin['sha256']) is not None, 'Invalid file pin')
    require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input file byte pin differs: ' + str(path))
    return path


def read_json(path, expected_sha=None, expected_bytes=None):
    raw = Path(path).read_bytes()
    require(expected_sha is None or hashlib.sha256(raw).hexdigest() == expected_sha, 'Metadata snapshot SHA differs')
    require(expected_bytes is None or len(raw) == expected_bytes, 'Metadata snapshot byte size differs')
    return json.loads(raw)


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(Path(path).parent)


def save_atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    save_new(temporary, value)
    os.replace(temporary, path)
    fsync_directory(path.parent)


def publish_terminal(path, value, start_cpu, start_wall):
    # Materialize, flush and account serialization before terminal publication.
    # Hard-link publication is exclusive; no existing terminal is replaced.
    path = Path(path)
    temporary = path.with_name(path.name + '.prepared')
    save_new(temporary, value)
    use = enforce_usage(start_cpu, start_wall)
    require(use['process_CPU_seconds'] < CPU_CAP - .1 and use['wall_seconds'] < WALL_CAP - 2,
        'Insufficient bounded headroom to publish final receipt')
    signal.alarm(0)
    signal.signal(signal.SIGXCPU, signal.SIG_IGN)
    os.link(temporary, path)
    fsync_directory(path.parent)
    temporary.unlink()
    fsync_directory(path.parent)


def usage(start_cpu, start_wall):
    return {'process_CPU_seconds': time.process_time() - start_cpu,
        'wall_seconds': time.monotonic() - start_wall,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def enforce_usage(start_cpu, start_wall):
    use = usage(start_cpu, start_wall)
    if use['process_CPU_seconds'] > CPU_CAP or use['wall_seconds'] > WALL_CAP or use['peak_RSS_bytes'] > MEMORY_CAP:
        raise ResourceLimitExceeded('Measured matching use exceeds frozen caps')
    return use


def tree_size(roots):
    paths = [Path(item) for item in roots]
    require(paths and all(path.is_absolute() and path.is_dir() and path.resolve() == path for path in paths), 'Workspace roots must exist and be canonical')
    require(len(set(paths)) == len(paths), 'Repeated workspace root')
    require(not any(a != b and a in b.parents for a in paths for b in paths), 'Overlapping workspace roots')
    total = 0
    for root in paths:
        for base, directories, files in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories if not (Path(base) / name).is_symlink()]
            for name in files:
                info = (Path(base) / name).lstat()
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
                elif stat.S_ISLNK(info.st_mode):
                    total += info.st_size
    return total


def verify_no_live_owner_processes(scope):
    # Check actual scientific command arguments, without exposing command text.
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            arguments = (process / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        for relative in scope['owner_scientific_command_paths']:
            suffix = relative.encode()
            require(not any(argument == suffix or argument.endswith(b'/' + suffix) for argument in arguments),
                'An original scientific numeric/QA process remains active')


def acquire_owner_guards(scope):
    handles = []
    try:
        for name in scope['owner_kernel_guard_paths']:
            path = checked_file(name)
            # Existing inode only: never create, truncate or rewrite owner locks.
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            handle = os.fdopen(fd, 'rb', buffering=0)
            handles.append(handle)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            original = os.fstat(handle.fileno())
            require(path.stat().st_ino == original.st_ino and path.stat().st_dev == original.st_dev,
                'Original kernel guard was replaced')
        return handles
    except BaseException:
        for handle in handles:
            handle.close()
        raise


def load_contract(args):
    scope_path = checked_file(args.scope)
    require(digest(scope_path) == args.expected_scope_sha256, 'Scope SHA differs')
    scope = read_json(scope_path, args.expected_scope_sha256)
    require(scope['schema'] == SCHEMA and scope['family_id'] == FAMILY, 'Wrong matching family')
    expected = {'scan_order': list(ONS), 'source_channel0': C0, 'native_chunk_count_channels': COUNT,
        'core_channel_count': CORE, 'core_q_indices': list(range(1, 255)), 'records_per_ON': N,
        'map_count': 762, 'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'grid_count': GRID_COUNT, 'grid_step_hz_s': GRID_STEP, 'widths_channels': [1, 3],
        'drift_index_tolerance': 1, 'top_count': TOP_COUNT, 'CPU_cap_s': CPU_CAP,
        'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP, 'output_reservation_bytes': OUTPUT_CAP,
        'shared_workspace_cap_bytes': WORKSPACE_CAP, 'retry_resume_or_rerun_authorized': False,
        'new_source_BODY_bytes': 0, 'new_HTTP_requests': 0, 'cost_DKK': 0,
        'profile_measurement_authorized': False, 'OFF_veto_applied': False,
        'reference_rule': 'midpoint of ON1 and ON3 first integration midpoint references',
        'frequency_tolerance_rule': '3*abs(df)+0.5*(8/784)*(t_ON3-t_ON1)',
        'nearest_lexicographic_rule': ['absolute_frequency_gap', 'absolute_drift_index_gap', 'target_absolute_source_channel'],
        'triple_ranking_rule': ['minimum_of_three_saved_scores_descending', 'ON1_channel', 'ON2_channel', 'ON3_channel'],
        'relation_columns': list(ONS), 'relation_dtype': '<i4', 'relation_index_domain': 'zero-based increasing absolute source channels q1..254 per ON'}
    for key, value in expected.items():
        require(scope[key] == value, 'Frozen scope field differs: ' + key)
    require(scope['script_sha256'] == digest(checked_file(__file__))
        and re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit), 'Script/freeze identity differs')
    require(args.root_go_after_closed_durable_QA and args.expected_admission_sha256 == scope['admission_pin']['sha256'], 'Root GO/admission binding missing')
    require(scope['grid_creation_expression'] == 'numpy 2.3.5: np.linspace(-4.0, 4.0, 785, dtype=np.float64)', 'Grid creation semantics differ')
    pins = scope['pinned_metadata_files'] + [scope['admission_pin']]
    paths = [item['path'] for item in pins]
    require(len(paths) == len(set(paths)), 'Duplicate metadata pins')
    for pin in pins:
        verify_pin(pin)
    admission = read_json(scope['admission_pin']['path'], scope['admission_pin']['sha256'], scope['admission_pin']['bytes'])
    require(admission['schema'] == 'SETI_S2017_CROSS_ON_ROOT_DURABLE_CLOSED_ADMISSION_V1'
        and admission['status'] == 'PASS_CLOSED_QA_DURABLE_RAW_AND_RESULTS_NO_DUPLICATE_MATCHER'
        and admission['all_numeric_and_QA_processes_closed'] is True
        and admission['durable_RAW_verified'] is True and admission['durable_RESULTS_verified'] is True
        and admission['fresh_registry_check_no_matching_duplicate'] is True
        and admission['matching_not_previously_executed'] is True
        and admission['map_count'] == 762, 'Owner durable/lifecycle/duplicate admission failed')
    require(admission['source_root'] == scope['source_root']
        and admission['shared_workspace_roots'] == scope['shared_workspace_roots'], 'Admission paths differ')
    require({item['kind'] for item in admission['durability_proofs']} == {'RAW', 'RESULTS'}, 'Both durable proof classes required')
    for item in admission['durability_proofs']:
        require(item['verified'] is True, 'Durable save has not been verified')
        verify_pin(item['pin'])
    verify_no_live_owner_processes(scope)
    require(Path(scope['output_directory']).is_absolute() and Path(scope['serial_gate_path']).is_absolute()
        and Path(scope['attempt_marker_path']).is_absolute(), 'Control/output paths must be absolute')
    require(Path(scope['output_directory']).parent == Path(scope['serial_gate_path']).parent
        == Path(scope['attempt_marker_path']).parent, 'Controls must share the finite stage directory')
    roots = [Path(item) for item in scope['shared_workspace_roots']]
    for name in (scope['source_root'], scope['output_directory'], scope['script_path'], args.scope):
        path = Path(name)
        require(path.is_absolute() and path.resolve() == path
            and any(path == root or root in path.parents for root in roots), 'Shared disk roots omit admitted source/output/code paths')
    workspace = tree_size(scope['shared_workspace_roots'])
    require(workspace + OUTPUT_CAP <= WORKSPACE_CAP, 'Fresh shared 12GiB disk gate fails including 64MiB reservation')
    require(os.statvfs(Path(scope['output_directory']).parent).f_bavail * os.statvfs(Path(scope['output_directory']).parent).f_frsize >= OUTPUT_CAP,
        'Filesystem free space below matching reservation')
    source = read_json(scope['source_manifest_pin']['path'], scope['source_manifest_pin']['sha256'], scope['source_manifest_pin']['bytes'])
    require(scope['source_manifest_pin'] in scope['pinned_metadata_files'], 'Source pin not in metadata inventory')
    headers = {item['label']: item['current_header']['data_attributes'] for item in source['sources']}
    require(len(source['sources']) == 6 and len(headers) == 6, 'Six unique source scans required')
    for label in ONS:
        require(float(headers[label]['fch1']) * 1e6 == FCH1 and float(headers[label]['foff']) * 1e6 == DF
            and float(headers[label]['tsamp']) == TSAMP, 'Source physical header differs')
    anchor = min(float(item['tstart']) for item in headers.values())
    references = [(float(headers[label]['tstart']) - anchor) * 86400 + .5 * TSAMP for label in ONS]
    require(references == scope['ON_reference_seconds_from_anchor'] and anchor == scope['MJD_anchor'], 'Actual header references differ')
    require(references[0] < references[1] < references[2], 'ON references out of order')
    midpoint = .5 * (references[0] + references[2])
    tau = 3 * abs(DF) + .5 * GRID_STEP * (references[2] - references[0])
    require(midpoint == scope['common_reference_seconds_from_anchor'] and tau == scope['frequency_tolerance_hz'], 'Metadata-derived matching geometry differs')
    maps = scope['maps']
    require(len(maps) == 762 and [(item['scan_id'], item['core_q']) for item in maps]
        == [(label, q) for label in ONS for q in range(1, 255)], 'Incomplete or repeated map inventory')
    require(len({item['map_pin']['path'] for item in maps}) == 762, 'Repeated map file paths')
    for item in maps:
        require(item['reference_channel_interval_half_open'] == [C0 + item['core_q'] * CORE, C0 + (item['core_q'] + 1) * CORE]
            and item['searched_carriers'] == CORE and item['valid_hypotheses_per_carrier'] == 1570, 'Map source frame/count differs')
        verify_pin(item['map_pin'])
        if item['core_q'] == 128:
            require(item['normalization_kind'] == 'embedded_in_q128_checkpoint', 'q128 normalization provenance differs')
        else:
            require(item['normalization_kind'] == 'separate_tile_normalization_JSON', 'Bulk normalization provenance differs')
            verify_pin(item['normalization_pin'])
    require(admission['ordered_map_pins_sha256'] == hashlib.sha256(json.dumps([item['map_pin'] for item in maps], sort_keys=True,
        separators=(',', ':')).encode()).hexdigest(), 'Admission does not bind all 762 fresh map pins')
    originals = scope['original_execution_and_QA_pins']
    require(admission['original_execution_and_QA_pins'] == originals, 'Admission must bind four actual COMPLETE and two QA receipts')
    return scope, pins, admission, workspace


def load_maxima(scope, np, start_cpu, start_wall):
    expected_grid = np.linspace(-4.0, 4.0, GRID_COUNT, dtype=np.float64)
    require(hashlib.sha256(expected_grid.astype('<f8', copy=False).tobytes()).hexdigest() == scope['grid_float64_le_sha256'], 'Frozen exact NumPy grid bytes differ')
    channels = np.arange(C0 + CORE, C0 + 255 * CORE, dtype=np.int64)
    scans = []
    for si, label in enumerate(ONS):
        scores = np.empty(N, dtype=np.float64)
        ks = np.empty(N, dtype=np.int16)
        widths = np.empty(N, dtype=np.int16)
        for item in scope['maps'][si * 254:(si + 1) * 254]:
            q, pin = item['core_q'], item['map_pin']
            lo, hi = (q - 1) * CORE, q * CORE
            verify_pin(pin)
            with np.load(pin['path'], allow_pickle=False) as saved:
                require(set(saved.files) == MAP_KEYS, 'Unexpected map array inventory')
                required_dtype = {'frequency_hz_at_tref': '<f8', 'maximum_robust_box_track_score': '<f8',
                    'winning_drift_hz_s': '<f8', 'winning_width_channels': '<i2', 'valid_hypothesis_count': '<i8',
                    'source_reference_channels': '<i8', 'drift_grid_hz_s': '<f8'}
                arrays = {key: saved[key] for key in MAP_KEYS}
                require(all(value.dtype.str == required_dtype[key] and value.shape == ((GRID_COUNT,) if key == 'drift_grid_hz_s' else (CORE,))
                    for key, value in arrays.items()), 'Map array dtype/shape differs')
                require(arrays['drift_grid_hz_s'].tobytes() == expected_grid.tobytes(), 'Saved drift grid is not byte-identical to original driver grid')
                require(np.array_equal(arrays['source_reference_channels'], channels[lo:hi])
                    and np.array_equal(arrays['frequency_hz_at_tref'], FCH1 + DF * channels[lo:hi]), 'Physical carrier frame differs')
                require(np.all(arrays['valid_hypothesis_count'] == 1570), 'Map lacks complete original hypotheses')
                score, drift, width = arrays['maximum_robust_box_track_score'], arrays['winning_drift_hz_s'], arrays['winning_width_channels']
                require(np.isfinite(score).all() and np.isfinite(drift).all() and np.isin(width, [1, 3]).all(), 'Invalid saved winner')
                index = np.rint((drift - expected_grid[0]) / GRID_STEP).astype(np.int64)
                require(np.all((index >= 0) & (index < GRID_COUNT)), 'Saved winner outside original lattice')
                require(drift.tobytes() == expected_grid[index].tobytes(), 'Saved winner does not roundtrip byte-exactly to its original lattice member')
                scores[lo:hi], ks[lo:hi], widths[lo:hi] = score, index, width
            enforce_usage(start_cpu, start_wall)
        fstar = FCH1 + DF * channels + expected_grid[ks] * (scope['common_reference_seconds_from_anchor'] - scope['ON_reference_seconds_from_anchor'][si])
        require(np.isfinite(fstar).all(), 'Transported frequencies invalid')
        scans.append({'scores': scores, 'drift_indices': ks, 'widths': widths, 'fstar': fstar})
    return channels, expected_grid, scans


def sorted_bins(scan, channels, np):
    order = np.lexsort((channels, scan['fstar'], scan['drift_indices']))
    edges = np.searchsorted(scan['drift_indices'][order], np.arange(GRID_COUNT + 1), side='left')
    return [order[edges[k]:edges[k + 1]] for k in range(GRID_COUNT)]


def directed_nearest(source, target, source_bins, target_bins, channels, tau, np, start_cpu, start_wall):
    partner = np.full(N, -1, dtype=np.int32)
    best_gap = np.full(N, np.inf, dtype=np.float64)
    best_drift_gap = np.full(N, 2, dtype=np.int16)
    for k, query in enumerate(source_bins):
        if not query.size:
            continue
        frequencies = source['fstar'][query]
        for l in range(max(0, k - 1), min(GRID_COUNT, k + 2)):
            ordered = target_bins[l]
            if not ordered.size:
                continue
            tf = target['fstar'][ordered]
            right = np.searchsorted(tf, frequencies, side='left')
            # For an exact frequency tie choose the smallest absolute channel.
            # The predecessor may end a tied-frequency group: move to its first
            # member before evaluation, preserving the declared third tie key.
            previous = np.maximum(right - 1, 0)
            left = np.searchsorted(tf, tf[previous], side='left')
            for positions, valid in ((left, right > 0), (right, right < ordered.size)):
                selected_queries = query[valid]
                candidates = ordered[positions[valid]]
                gap = np.abs(source['fstar'][selected_queries] - target['fstar'][candidates])
                drift_gap = abs(k - l)
                old = partner[selected_queries]
                better = (gap <= tau) & ((gap < best_gap[selected_queries])
                    | ((gap == best_gap[selected_queries]) & ((drift_gap < best_drift_gap[selected_queries])
                    | ((drift_gap == best_drift_gap[selected_queries]) & ((old < 0) | (channels[candidates] < channels[np.maximum(old, 0)]))))))
                changed = selected_queries[better]
                require(not candidates.size or int(candidates.max()) < 2147483648, 'Partner index would overflow int32')
                partner[changed] = candidates[better]
                best_gap[changed] = gap[better]
                best_drift_gap[changed] = drift_gap
        enforce_usage(start_cpu, start_wall)
    return partner


def consistent_triples(scans, partners, tau, np):
    i = np.flatnonzero((partners[0, 1] >= 0) & (partners[0, 2] >= 0))
    j, k = partners[0, 1][i], partners[0, 2][i]
    coherent = (partners[1, 0][j] == i) & (partners[2, 0][k] == i)
    coherent &= (partners[1, 2][j] == k) & (partners[2, 1][k] == j)
    i, j, k = i[coherent], j[coherent], k[coherent]
    frequency = np.column_stack((scans[0]['fstar'][i], scans[1]['fstar'][j], scans[2]['fstar'][k]))
    drift = np.column_stack((scans[0]['drift_indices'][i], scans[1]['drift_indices'][j], scans[2]['drift_indices'][k]))
    keep = (frequency.max(axis=1) - frequency.min(axis=1) <= tau) & (drift.max(axis=1) - drift.min(axis=1) <= 1)
    relation = np.column_stack((i[keep], j[keep], k[keep]))
    require(relation.size == 0 or (relation.min() >= 0 and relation.max() < N < 2147483648), 'Relation index domain differs')
    require(len(relation) <= N and all(np.unique(relation[:, c]).size == len(relation) for c in range(3)), 'Mutual relation is not one-to-one')
    return relation.astype('<i4', copy=False)


def top_records(relation, scans, channels, grid, scope, np):
    scores = np.column_stack([scans[s]['scores'][relation[:, s]] for s in range(3)])
    minimum = scores.min(axis=1)
    order = np.lexsort((channels[relation[:, 2]], channels[relation[:, 1]], channels[relation[:, 0]], -minimum))
    top = []
    for rank, ri in enumerate(order[:TOP_COUNT], 1):
        members = []
        for si, index in enumerate(relation[int(ri)]):
            index = int(index)
            channel, ki, width = int(channels[index]), int(scans[si]['drift_indices'][index]), int(scans[si]['widths'][index])
            reference = scope['ON_reference_seconds_from_anchor'][si]
            members.append({'scan_id': ONS[si], 'global_carrier_vector_index': index,
                'original_key': {'visit': '2017-04-28 / AGBT17A_999_55', 'scan_id': ONS[si],
                    'source_reference_channel': channel, 'reference_seconds_from_anchor': reference,
                    'drift_grid_index': ki, 'drift_hz_s': float(grid[ki]), 'width_channels': width},
                'core_q': (channel - C0) // CORE, 'original_reference_frequency_hz': float(FCH1 + DF * channel),
                'saved_maximum_robust_box_track_score': float(scans[si]['scores'][index]),
                'frequency_hz_at_common_reference': float(scans[si]['fstar'][index])})
        gaps = [{'ON_pair': [ONS[a], ONS[b]], 'absolute_frequency_gap_hz': abs(members[a]['frequency_hz_at_common_reference'] - members[b]['frequency_hz_at_common_reference']),
            'absolute_drift_grid_index_gap': abs(members[a]['original_key']['drift_grid_index'] - members[b]['original_key']['drift_grid_index'])}
            for a, b in ((0, 1), (0, 2), (1, 2))]
        top.append({'match_id': FAMILY + '_rank_%04d' % rank, 'display_rank': rank,
            'descriptive_minimum_saved_score': float(minimum[int(ri)]), 'members': members,
            'pairwise_gaps': gaps, 'status': 'EXPLORATORY_ASSOCIATION_UNCLASSIFIED'})
    return top


def recheck_inputs(scope, pins, admission, args):
    require(digest(args.scope) == args.expected_scope_sha256 and digest(__file__) == scope['script_sha256'], 'Scope/script changed during matching')
    for pin in pins:
        verify_pin(pin)
    for item in admission['durability_proofs']:
        verify_pin(item['pin'])
    for item in scope['maps']:
        verify_pin(item['map_pin'])
        if 'normalization_pin' in item:
            verify_pin(item['normalization_pin'])
    verify_no_live_owner_processes(scope)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--expected-scope-sha256', required=True)
    parser.add_argument('--expected-admission-sha256', required=True)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--root-go-after-closed-durable-QA', action='store_true')
    args = parser.parse_args()
    # process_time is cumulative since process start: include stdlib imports and
    # argument parsing in the measured 120-second allocation as well.
    start_cpu, start_wall = 0.0, time.monotonic()
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    def limit_signal(signum, frame):
        raise ResourceLimitExceeded('OS matching resource limit signal ' + str(signum))
    signal.signal(signal.SIGALRM, limit_signal)
    signal.signal(signal.SIGXCPU, limit_signal)
    signal.alarm(int(WALL_CAP))
    resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(CPU_CAP), math.ceil(CPU_CAP) + 2))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    # Minimal public scope authentication before locating the once-only marker.
    # All other validation occurs inside the recorded admitted attempt.
    raw_scope_path = checked_file(args.scope)
    require(digest(raw_scope_path) == args.expected_scope_sha256, 'Scope SHA differs')
    preliminary = read_json(raw_scope_path, args.expected_scope_sha256)
    require(preliminary['schema'] == SCHEMA and preliminary['family_id'] == FAMILY
        and preliminary['script_sha256'] == digest(checked_file(__file__)), 'Scope/script identity differs')
    scope = preliminary
    stage = Path(scope['output_directory']).parent
    require(stage.resolve() == stage, 'Stage directory must be canonical')
    marker = Path(scope['attempt_marker_path'])
    require(marker.is_absolute() and marker.parent == stage, 'Attempt marker outside stage')
    save_new(marker, {'family_id': FAMILY, 'status': 'STARTED_ONCE_NO_RETRY', 'scope_sha256': args.expected_scope_sha256,
        'public_freeze_commit': args.freeze_commit, 'PID': os.getpid(), 'started_UTC_unix_seconds': time.time()})
    out, gate, owner_handles = Path(scope['output_directory']), None, []
    created, phases, relation_count, complete_committed = False, [], None, False
    try:
        owner_handles = acquire_owner_guards(scope)
        scope, pins, admission, workspace = load_contract(args)
        gate_path = Path(scope['serial_gate_path'])
        fd = os.open(gate_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        gate = os.fdopen(fd, 'r+b', buffering=0)
        fcntl.flock(gate.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        inode = os.fstat(gate.fileno())
        require(stat.S_ISREG(inode.st_mode) and gate_path.stat().st_ino == inode.st_ino, 'Stable serial gate differs')
        out.mkdir(exist_ok=False)
        created = True
        save_new(out / 'INPUT_PINS.json', {'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256,
            'script_sha256': scope['script_sha256'], 'public_freeze_commit': args.freeze_commit,
            'admission_pin': scope['admission_pin'], 'pinned_metadata_files': pins,
            'ordered_map_pins': [item['map_pin'] for item in scope['maps']],
            'fresh_shared_workspace_bytes': workspace, 'reserved_output_bytes': OUTPUT_CAP})
        # No scientific import or NPZ decoding occurs before the admission above.
        import numpy as np
        require(np.__version__ == '2.3.5' and sys.byteorder == 'little', 'Exact original NumPy/little-endian runtime required')
        channels, grid, scans = load_maxima(scope, np, start_cpu, start_wall)
        bins = [sorted_bins(scan, channels, np) for scan in scans]
        partners, directional_counts = {}, {}
        for a, b in ((0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)):
            partners[a, b] = directed_nearest(scans[a], scans[b], bins[a], bins[b], channels,
                scope['frequency_tolerance_hz'], np, start_cpu, start_wall)
            label = ONS[a] + '_to_' + ONS[b]
            directional_counts[label] = int(np.count_nonzero(partners[a, b] >= 0))
            phases.append(label)
            save_atomic(out / 'MATCH_CHECKPOINT.json', {'status': 'IN_PROGRESS_NOT_RESUMABLE', 'family_id': FAMILY,
                'completed_directions': phases, 'expected_directions': 6, 'directional_neighbor_counts': directional_counts,
                'detector_reexecuted': False, 'profiles_measured': False, **usage(start_cpu, start_wall)})
        relation = consistent_triples(scans, partners, scope['frequency_tolerance_hz'], np)
        relation_count = len(relation)
        relation_path = out / 'ALL_MUTUAL_TRIPLES.npy'
        with relation_path.open('xb') as handle:
            np.save(handle, relation, allow_pickle=False)
        records = top_records(relation, scans, channels, grid, scope, np)
        save_new(out / 'TOP1000.json', {'schema': SCHEMA, 'family_id': FAMILY,
            'common_reference_seconds_from_anchor': scope['common_reference_seconds_from_anchor'],
            'MJD_anchor': scope['MJD_anchor'], 'frequency_tolerance_hz': scope['frequency_tolerance_hz'],
            'drift_index_tolerance': 1, 'matched_triples': relation_count, 'fixed_display_cap': TOP_COUNT,
            'displayed_records': len(records), 'display_truncated': relation_count > TOP_COUNT,
            'records': records, 'limitations': LIMITATIONS})
        recheck_inputs(scope, pins, admission, args)
        for handle, name in zip(owner_handles, scope['owner_kernel_guard_paths']):
            held, current = os.fstat(handle.fileno()), Path(name).stat()
            require(held.st_ino == current.st_ino and held.st_dev == current.st_dev, 'Held original kernel guard replaced during matching')
        require(gate_path.stat().st_ino == inode.st_ino and gate_path.stat().st_dev == inode.st_dev, 'Serial gate was replaced')
        require(tree_size([str(out)]) < OUTPUT_CAP - 65536, 'Matching output exceeds reservation')
        require(tree_size(scope['shared_workspace_roots']) <= WORKSPACE_CAP, 'Final shared workspace exceeds 12GiB')
        use = enforce_usage(start_cpu, start_wall)
        receipt = {'status': 'COMPLETE_S2017_SAVED_MAXIMA_MUTUAL_CROSS_ON_EXPLORATORY_ONLY',
            'family_id': FAMILY, 'scope_sha256': args.expected_scope_sha256, 'script_sha256': scope['script_sha256'],
            'public_freeze_commit': args.freeze_commit, 'admission_pin': scope['admission_pin'],
            'maps_verified': 762, 'records_per_ON': N, 'carrier_maximum_records': 3 * N,
            'completed_directions': 6, 'directional_neighbor_counts': directional_counts,
            'matched_triples': relation_count, 'displayed_records': len(records),
            'relation_columns': list(ONS), 'relation_shape': [relation_count, 3], 'relation_dtype': '<i4',
            'relation_index_domain': scope['relation_index_domain'],
            'relation_pin': {'path': str(relation_path), 'sha256': digest(relation_path), 'bytes': relation_path.stat().st_size},
            'top1000_pin': {'path': str(out / 'TOP1000.json'), 'sha256': digest(out / 'TOP1000.json'), 'bytes': (out / 'TOP1000.json').stat().st_size},
            'grid_float64_le_sha256': scope['grid_float64_le_sha256'], 'detector_reexecuted': False,
            'preprocessing_reexecuted': False, 'profiles_measured': False, 'source_HDF5_opened': False,
            'new_HTTP_requests': 0, 'new_source_BODY_bytes': 0, 'cost_DKK': 0,
            'runtime_numpy': np.__version__, 'limitations': LIMITATIONS, **use}
        # Final hash work is accounted before committing a COMPLETE receipt.
        receipt.update(enforce_usage(start_cpu, start_wall))
        publish_terminal(out / 'EXECUTION_RECEIPT.json', receipt, start_cpu, start_wall)
        complete_committed = True
        # Terminal publication is final. A disconnected stdout is not an
        # incomplete scientific computation and must not create FAILURE.
        try:
            print(json.dumps({key: receipt[key] for key in ('status', 'matched_triples', 'displayed_records',
                'process_CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')}), flush=True)
        except BrokenPipeError:
            pass
    except BaseException as error:
        if complete_committed or (created and (out / 'EXECUTION_RECEIPT.json').exists()):
            raise  # Preserve terminal; never fabricate a second scientific status.
        destination = out / 'FAILURE_RECEIPT.json' if created else stage / 'PREFLIGHT_FAILURE_RECEIPT.json'
        save_new(destination, {'status': 'INCOMPLETE_ONE_SHOT_MATCHING_NO_RETRY', 'family_id': FAMILY,
            'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
            'error_type': type(error).__name__, 'error': str(error), 'completed_directions': phases,
            'matched_triples_if_materialized': relation_count, 'partial_outputs_preserved': created,
            'detector_reexecuted': False, 'profiles_measured': False, **usage(start_cpu, start_wall)})
        raise
    finally:
        if gate is not None:
            gate.close()  # Stable flock inode is deliberately never unlinked.
        for handle in owner_handles:
            handle.close()
        signal.alarm(0)


if __name__ == '__main__':
    main()
