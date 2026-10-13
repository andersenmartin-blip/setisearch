#!/usr/bin/env python3
"""Replay the original DC-alternative family from eighteen authenticated crops.

Only NumPy 2.3.5 is required. Original HDF5 authentication is inherited from
the pinned completed source QA; this portable replay never opens an HDF5 file.
No numerical work occurs at import or with --check-only.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_bytes(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def rank_key(r):
    return (-r['score'], r['frequency_hz_at_own_first_midpoint'], r['drift_hz_s'],
            r['width_channels'], r['native_chunk_index'], r['core_q'], r['carrier_index_in_core'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--scope', type=Path, default=BASE/'portable_scope.json')
    parser.add_argument('--go', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps({'status': 'PORTABLE_REPLAY_CODE_ONLY', 'code_sha256': digest(Path(__file__)),
                          'source_float_values_read': 0, 'hypothesis_scores_computed': 0}))
        return
    require(args.go is not None and args.out is not None, 'Pinned GO and fresh output directory required')
    admitted_scope_sha, admitted_code_sha, admitted_GO_sha = digest(args.scope), digest(Path(__file__)), digest(args.go)
    scope, go = read(args.scope), read(args.go)
    require(go['authorized'] is True, 'Portable replay not authorized')
    require(go['scope_sha256'] == admitted_scope_sha and go['code_sha256'] == admitted_code_sha, 'Portable admission differs')
    require(not args.out.exists(), 'Never overwrite or rerun a portable output namespace')
    args.out.mkdir(parents=True)
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    def deadline(*unused):
        raise TimeoutError('Portable replay exceeded frozen resource cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(900)
    resource.setrlimit(resource.RLIMIT_CPU, (600, 601))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    started, cpu = time.monotonic(), time.process_time()
    checked = {}
    def verified(pin):
        path = ROOT/pin['path']
        require(path.is_file(), 'Portable input unavailable: '+pin['path'])
        require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Portable input pin differs: '+pin['path'])
        checked[pin['path']] = pin
        return path
    for pin in scope['input_pins']:
        verified(pin)
    qa = read(verified(scope['original_source_QA_pin']))
    require(qa['status'] == 'PASS_INDEPENDENT_EXHAUSTIVE_DC_ALTERNATIVES' and qa['mismatch_count'] == 0, 'Original source QA must pass')
    require(go['source_QA_sha256'] == scope['original_source_QA_pin']['sha256'], 'GO source QA pin differs')
    import numpy as np
    require(np.__version__ == '2.3.5', 'Original NumPy 2.3.5 required')
    kernel_path = verified(scope['independent_kernel_pin'])
    spec = importlib.util.spec_from_file_location('portable_independent_original_core', kernel_path)
    kernel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kernel)
    search_scope = read(verified(scope['original_search_scope_pin']))
    inventory = read(verified(search_scope['excluded_inventory_pin']))
    require(len(inventory['records']) == 7083, 'Original excluded inventory differs')
    inventory_identities = {(record['group_id'], record['carrier_index_in_core']) for record in inventory['records']}
    require(len(inventory_identities) == 7083, 'Original inventory identities must be unique')
    constants = search_scope['constants']
    results, group_summary, actual_records = {}, {}, {}
    for pin in scope['producer_result_pins']:
        result = read(verified(pin))
        scan = result['primary_scan_id']
        results[scan] = result
        for g in result['group_summaries']:
            group_summary[g['group_id']] = g
        for record in result['alternative_records']:
            old = record['original_cached_tuple_and_DC_geometry']
            identity = (old['group_id'], old['carrier_index_in_core'])
            require(identity not in actual_records, 'Duplicate alternative identity')
            actual_records[identity] = record
    mismatches, group_audits = [], []
    checks = 0
    totals = {'groups': 0, 'excluded_carriers': 0, 'recovered_carriers': 0, 'EMPTY_carriers': 0,
              'hypothesis_occurrences': 0, 'admissible_hypothesis_occurrences': 0}
    recovered = {scan: [] for scan in search_scope['primary_scan_ids']}
    visited_identities = set()
    def equal(actual, expected, label, arrays=False):
        nonlocal checks
        checks += 1
        ok = np.array_equal(actual, expected, equal_nan=True) if arrays else actual == expected
        if not ok:
            mismatches.append(label)
    for group in search_scope['groups']:
        gid = group['group_id']
        summary = group_summary[gid]
        frame = group['exact_original_frame']
        with np.load(verified(summary['raw_frame_pin']), allow_pickle=False) as arrays:
            raw = arrays['raw_power']
            equal(int(arrays['source_channel0']), frame['original_s_power_source_channel0'], gid+'/raw_origin')
            equal(arrays['normalization_source_channel_interval_half_open'], frame['normalization_source_channel_interval_half_open'], gid+'/raw_core', True)
        require(raw.shape == (16, 12096) and raw.dtype.str == '<f4', 'Complete original frame required')
        norm = read(verified(group['source_map_metadata']['normalization_pin']))
        equal(norm['normalization_source_channels'], list(range(*frame['normalization_source_channel_interval_half_open'])), gid+'/norm_domain')
        equal(norm['normalization_unmasked_counts'], [4096]*16, gid+'/unmasked')
        z = kernel.original_z_from_raw_frame(raw, norm, np)
        equal(hashlib.sha256(z.astype('<f8', copy=False).tobytes()).hexdigest(), summary['original_normalized_z_rowmajor_float64_sha256'], gid+'/z_bits')
        with np.load(verified(group['source_map_metadata']['map_pin']), allow_pickle=False) as arrays:
            maps = {name: arrays[name] for name in arrays.files}
        grid = maps['drift_grid_hz_s']
        equal(grid, np.linspace(-4, 4, 785), gid+'/grid_bits', True)
        originals = [inventory['records'][index] for index in group['excluded_inventory_indices']]
        for original in originals:
            identity = (gid, original['carrier_index_in_core'])
            require(identity not in visited_identities, 'Duplicate portable group/carrier coverage')
            visited_identities.add(identity)
        indices = np.asarray([r['carrier_index_in_core'] for r in originals], dtype=np.int64)
        frequencies = maps['frequency_hz_at_tref'][indices]
        equal(frequencies, [r['frequency_hz_at_own_first_midpoint'] for r in originals], gid+'/frequencies', True)
        family = kernel.exhaustive_original_scores(z, frame['original_s_power_source_channel0'], frequencies,
                 grid, (1, 3), group['original_origin_row_times_from_reference_s'], constants['fch1_hz'],
                 constants['df_hz'], constants['DC_channels'], np)
        original_arg = family['unconstrained_best_index']
        equal(family['unconstrained_best_score'], maps['maximum_robust_box_track_score'][indices], gid+'/original_scores', True)
        equal(grid[original_arg % 785], maps['winning_drift_hz_s'][indices], gid+'/original_drifts', True)
        equal(np.where(original_arg < 785, 1, 3), maps['winning_width_channels'][indices], gid+'/original_widths', True)
        valid = family['has_clean_hypothesis']
        arg = family['best_clean_index']
        scores = family['best_clean_score']
        drifts = np.where(valid, grid[arg % 785], np.nan)
        widths = np.where(valid, np.where(arg < 785, 1, 3), 0)
        drift_indices = np.where(valid, arg % 785, -1)
        counts = family['admissible'].sum(axis=0)
        expected_arrays = {'reference_source_channel': [r['reference_source_channel'] for r in originals],
            'carrier_index_in_core': indices, 'admissible_hypothesis_count': counts,
            'no_admissible_hypothesis': ~valid, 'clean_maximum_score': scores,
            'clean_winning_drift_hz_s': drifts, 'clean_winning_width_channels': widths,
            'clean_winning_drift_grid_index': drift_indices,
            'original_cached_maximum_score': family['unconstrained_best_score'],
            'original_cached_winning_drift_hz_s': grid[original_arg % 785],
            'original_cached_winning_width_channels': np.where(original_arg < 785, 1, 3)}
        with np.load(verified(summary['recovered_winner_arrays_pin']), allow_pickle=False) as arrays:
            equal(set(arrays.files), set(expected_arrays), gid+'/winner_schema')
            for name, expected in expected_arrays.items():
                equal(arrays[name], expected, gid+'/winner_'+name, True)
        for index, old in enumerate(originals):
            actual = actual_records[(gid, old['carrier_index_in_core'])]
            equal(actual['original_cached_tuple_and_DC_geometry'], old, gid+'/'+str(index)+'/original')
            equal(actual['admissible_hypothesis_count'], int(counts[index]), gid+'/'+str(index)+'/count')
            equal(actual['no_admissible_hypothesis'], not bool(valid[index]), gid+'/'+str(index)+'/empty')
            equal(actual['status'], 'RECOVERED_CLEAN_MAXIMUM' if valid[index] else 'EMPTY', gid+'/'+str(index)+'/status')
            if not valid[index]:
                equal(actual['clean_maximum'], None, gid+'/'+str(index)+'/null')
                continue
            point = actual['clean_maximum']
            centers = np.rint((frequencies[index]-constants['fch1_hz'])/constants['df_hz'] + drifts[index]*np.asarray(group['original_origin_row_times_from_reference_s'])/constants['df_hz']).astype(np.int64)
            expected_point = {'primary_scan_id': group['primary_scan_id'], 'reference_origin_scan_id': group['primary_scan_id'],
                'native_chunk_index': group['native_chunk_index'], 'core_q': group['core_q'],
                'carrier_index_in_core': old['carrier_index_in_core'], 'reference_source_channel': old['reference_source_channel'],
                'frequency_hz_at_own_first_midpoint': float(frequencies[index]), 'score': float(scores[index]),
                'drift_hz_s': float(drifts[index]), 'width_channels': int(widths[index]), 'drift_grid_index': int(drift_indices[index]),
                'rounded_absolute_centers': centers.tolist(), 'normalization_pin': group['source_map_metadata']['normalization_pin'],
                'map_pin': group['source_map_metadata']['map_pin'], 'source_kind': 'recovered_original_DC_free_hypothesis',
                'score_provenance': 'EXACT_ORIGINAL_PREFIX_DC_UNTOUCHED_ALTERNATIVE'}
            for name, value in expected_point.items():
                equal(point[name], value, gid+'/'+str(index)+'/'+name)
            authority = point['authoritative_score_source']
            equal(authority['pin'], summary['recovered_winner_arrays_pin'], gid+'/'+str(index)+'/authority_pin')
            equal(authority['record_index'], index, gid+'/'+str(index)+'/authority_index')
            recovered[group['primary_scan_id']].append(point)
        n = len(originals)
        totals['groups'] += 1
        totals['excluded_carriers'] += n
        totals['recovered_carriers'] += int(valid.sum())
        totals['EMPTY_carriers'] += int((~valid).sum())
        totals['hypothesis_occurrences'] += 1570*n
        totals['admissible_hypothesis_occurrences'] += int(counts.sum())
        group_audits.append({'group_id': gid, 'carriers': n, 'EMPTY': int((~valid).sum()), 'hypotheses': 1570*n})
        del raw, z, maps, family
    require(visited_identities == inventory_identities == set(actual_records), 'Complete portable inventory/result identity coverage required')
    selected = []
    for old_prefix in search_scope['cached_clean_prefixes']:
        scan = old_prefix['primary_scan_id']
        old = read(verified(old_prefix['result_pin']))
        base = [dict(point, score_provenance='ORIGINAL_CACHED_DC_UNTOUCHED_WINNER') for point in old['raw_TOP700']]
        for point in base:
            point['source_kind'] = 'original_clean_cached_carrier_maximum'
            point['authoritative_score_source'] = {'kind': point['source_kind'], 'pin': point['map_pin'],
                'record_index': point['carrier_index_in_core'], 'score_field': 'maximum_robust_box_track_score',
                'drift_field': 'winning_drift_hz_s', 'width_field': 'winning_width_channels', 'channel_field': 'source_reference_channels'}
        merged = sorted(base+recovered[scan], key=rank_key)[:700]
        for rank, point in enumerate(merged, 1):
            point['raw_rank'] = rank
        separated = []
        for point in merged:
            if all(abs(point['reference_source_channel']-other['reference_source_channel']) > 3 for other in separated):
                separated.append(dict(point, frequency_separated_rank=len(separated)+1))
            if len(separated) == 100:
                break
        require(len(separated) == 100 and separated[-1]['raw_rank'] <= 694, 'Separation prefix bound differs')
        top3 = [dict(point, rank=rank, exploratory_selection_rank=rank) for rank, point in enumerate(separated[:3], 1)]
        for name, expected in [('raw_TOP700', merged), ('raw_TOP100', merged[:100]), ('frequency_separated_TOP100', separated), ('TOP3', top3)]:
            equal(results[scan][name], expected, scan+'/'+name)
        selected.extend(top3)
    aggregate = read(verified(scope['selected_TOP9_pin']))
    equal(aggregate['records'], selected, 'global_TOP9')
    equal(totals, scope['expected_counts'], 'all_expected_counts')
    for pin in checked.values():
        verified(pin)
    require(digest(args.scope) == admitted_scope_sha and digest(Path(__file__)) == admitted_code_sha and digest(args.go) == admitted_GO_sha, 'Portable scope/code/GO changed during execution')
    outcome = {'status': 'PASS_PORTABLE_NUMPY_ORIGINAL_FRAME_DC_REPLAY' if not mismatches else 'FAIL_MISMATCHES_PRESERVED',
        'counts': totals, 'checks': checks, 'mismatch_count': len(mismatches), 'mismatches': mismatches,
        'group_audits': group_audits, 'scope_sha256': admitted_scope_sha, 'code_sha256': admitted_code_sha, 'GO_sha256': admitted_GO_sha,
        'original_source_QA_pin': scope['original_source_QA_pin'], 'input_pins_checked': len(checked),
        'CPU_seconds': time.process_time()-cpu, 'wall_seconds': time.monotonic()-started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'runtime': {'numpy': np.__version__}, 'HDF5_files_opened': 0, 'new_telescope_HTTP': 0,
        'qualification': 'Numerical reproduction from saved exposed frames; not independent sky data, significance calibration, or SETI detection.'}
    with (args.out/'REPLAY_RECEIPT.json').open('x') as f:
        json.dump(outcome, f, indent=2, allow_nan=False)
        f.write('\n')
    signal.alarm(0)
    print(json.dumps(outcome))
    require(not mismatches, 'Portable replay mismatches preserved')


if __name__ == '__main__':
    main()
