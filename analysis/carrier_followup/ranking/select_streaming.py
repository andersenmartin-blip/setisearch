#!/usr/bin/env python3
"""Stream cached carrier winners: DC geometry only, no detector evaluation."""
import argparse
import csv
import hashlib
import heapq
import io
import json
from pathlib import Path
import resource
import time
import numpy as np

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(WORKSPACE)), 'bytes': len(raw), 'sha256': sha(raw)}


def verify(item):
    raw = (WORKSPACE / item['path']).read_bytes()
    assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], item['path']
    return raw


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def canonical(record):
    return (-record['score'], record['frequency_hz_at_own_first_midpoint'], record['drift_hz_s'],
            record['width_channels'], record['native_chunk_index'], record['core_q'], record['carrier_index_in_core'])


def identity(record):
    return tuple(record[k] for k in ('phase', 'primary_target', 'native_chunk_index', 'core_q',
                 'carrier_index_in_core', 'reference_source_channel', 'frequency_hz_at_own_first_midpoint',
                 'reference_time_mjd', 'drift_hz_s', 'width_channels', 'score'))


def write_list_csv(path, records):
    names = ['primary_target', 'scan_id', 'phase', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
             'reference_source_channel', 'frequency_hz_at_own_first_midpoint', 'reference_time_mjd',
             'drift_hz_s', 'drift_grid_index', 'width_channels', 'score', 'raw_rank', 'rank',
             'frequency_separated_rank', 'is_original_coremax_winner']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        for record in records:
            writer.writerow({name: record.get(name) for name in names})


def select_target(scope, scope_sha, target):
    out = BASE / target
    assert not out.exists(), 'No target job rerun or overwrite permitted'
    out.mkdir()
    start_wall, start_cpu = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    const = scope['constants']
    assert const == {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                     'tsamp_s': 18.253611008, 'rows': 16, 'core_channels': 4096,
                     'fine_channels_per_native': 1048576,
                     'DC_channels': [178782208, 179830784, 180879360]}
    fch1, df = const['fch1_hz'], const['df_hz']
    times, dcs = np.arange(16) * const['tsamp_s'], np.array(const['DC_channels'])
    previous_all = json.loads(verify(scope['previous_coremax_annotation_pin']))
    old_core = {(r['phase'], r['primary_target'], r['native_chunk_index'], r['core_q']): r
                for r in previous_all['records']}
    previous9 = [r for r in json.loads(verify(scope['previous_selected9_pin']))['records']
                 if r['primary_target'] == target]
    assert len(previous9) == 3
    heap, summaries, intervals = [], [], []
    totals = {'maps': 0, 'cached_carriers': 0, 'eligible_DC_untouched_carriers': 0,
              'DC_contacting_cached_winner_carriers': 0, 'geometry_row_occurrences': 0,
              'DC_row_box_membership_checks': 0, 'source_map_hashes_verified': 0,
              'original_coremax_tuples_verified': 0, 'map_member_arrays_decoded': 0,
              'new_detector_scores': 0, 'new_telescope_HTTP': 0, 'power_arrays_decoded': 0}
    for group in scope['groups']:
        if group['primary_target'] != target:
            continue
        for source in group['maps']:
            native, q = source['native_chunk_index'], source['core_q']
            key = (group['phase'], target, native, q)
            previous = old_core[key]
            assert previous['query_id'] == source['original_coremax_query_id']
            intervals.append(tuple(source['reference_channel_interval_half_open']))
            raw = verify(source['pin'])
            with np.load(io.BytesIO(raw), allow_pickle=False) as data:
                frequency = data['frequency_hz_at_tref']
                score = data['maximum_robust_box_track_score']
                drift = data['winning_drift_hz_s']
                width = data['winning_width_channels']
                valid = data['valid_hypothesis_count']
                channel = data['source_reference_channels']
                grid = data['drift_grid_hz_s']
            assert all(a.shape == (4096,) for a in (frequency, score, drift, width, valid, channel))
            assert grid.shape == (785,) and np.isfinite(grid).all() and np.all(np.diff(grid) > 0)
            assert grid[0] == -4 and grid[-1] == 4
            assert all(np.isfinite(a).all() for a in (frequency, score, drift))
            assert np.isin(width, [1, 3]).all() and np.all(valid == 1570)
            lo, hi = source['reference_channel_interval_half_open']
            assert np.array_equal(channel, np.arange(lo, hi, dtype=np.int64))
            assert np.array_equal(frequency, fch1 + channel * df)
            grid_index = np.searchsorted(grid, drift)
            assert np.all(grid_index < 785) and np.array_equal(grid[grid_index], drift)
            historic_max = int(np.lexsort((channel, -score))[0])
            assert historic_max == previous['carrier_index_in_core']
            for name, value in (('reference_source_channel', channel[historic_max]),
                                ('frequency_hz_at_own_first_midpoint', frequency[historic_max]),
                                ('drift_hz_s', drift[historic_max]), ('width_channels', width[historic_max]),
                                ('score', score[historic_max]), ('drift_grid_index', grid_index[historic_max])):
                assert value == previous[name], (source['map_id'], name)
            centers = np.rint((frequency[:, None] - fch1) / df
                              + drift[:, None] * times[None, :] / df).astype(np.int64)
            assert np.array_equal(centers[:, 0], channel)
            assert centers[historic_max].tolist() == previous['rounded_absolute_centers']
            touches = np.any(np.abs(centers[:, :, None] - dcs[None, None, :]) <= (width[:, None, None] // 2), axis=(1, 2))
            eligible = ~touches
            assert bool(eligible[historic_max]) == previous['eligible_DC_untouched']
            indices = np.flatnonzero(eligible)
            ordered = indices[np.lexsort((indices, width[indices], drift[indices], frequency[indices], -score[indices]))]

            def record_at(index):
                return {'phase': group['phase'], 'primary_target': target, 'scan_id': group['scan_id'],
                        'original_acquisition_role': 'OFF', 'native_chunk_index': native, 'core_q': q,
                        'map_id': source['map_id'], 'carrier_index_in_core': int(index),
                        'reference_source_channel': int(channel[index]),
                        'frequency_hz_at_own_first_midpoint': float(frequency[index]),
                        'reference_time_mjd': previous['reference_time_mjd'],
                        'drift_hz_s': float(drift[index]), 'drift_grid_index': int(grid_index[index]),
                        'width_channels': int(width[index]), 'score': float(score[index]),
                        'rounded_absolute_centers': centers[index].tolist(),
                        'map_pin': source['pin'], 'normalization': previous['normalization'],
                        'is_original_coremax_winner': int(index) == historic_max,
                        'eligible_DC_untouched': True}

            for index in ordered[:700]:
                quality = (float(score[index]), -float(frequency[index]), -float(drift[index]),
                           -int(width[index]), -native, -q, -int(index))
                if len(heap) < 700:
                    heapq.heappush(heap, (quality, record_at(index)))
                elif quality > heap[0][0]:
                    heapq.heapreplace(heap, (quality, record_at(index)))
            summaries.append({'phase': group['phase'], 'primary_target': target, 'scan_id': group['scan_id'],
                              'native_chunk_index': native, 'core_q': q, 'map_id': source['map_id'],
                              'map_pin': source['pin'], 'cached_carriers': 4096,
                              'eligible_DC_untouched_carriers': int(np.count_nonzero(eligible)),
                              'DC_contacting_cached_winner_carriers': int(np.count_nonzero(touches)),
                              'original_coremax_DC_contact': bool(touches[historic_max]),
                              'original_coremax_score': float(score[historic_max]),
                              'eligible_maximum': record_at(ordered[0]) if len(ordered) else None})
            totals['maps'] += 1
            totals['cached_carriers'] += 4096
            totals['eligible_DC_untouched_carriers'] += int(np.count_nonzero(eligible))
            totals['DC_contacting_cached_winner_carriers'] += int(np.count_nonzero(touches))
            totals['geometry_row_occurrences'] += 4096 * 16
            totals['DC_row_box_membership_checks'] += 4096 * 16 * 3
            totals['source_map_hashes_verified'] += 1
            totals['original_coremax_tuples_verified'] += 1
            totals['map_member_arrays_decoded'] += 7
    assert totals['maps'] == 763 and totals['cached_carriers'] == 3125248
    intervals.sort()
    assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), 'Reference domains overlap'
    assert sum(b - a for a, b in intervals) == totals['cached_carriers']
    raw700 = sorted((record for _, record in heap), key=canonical)
    assert len(raw700) == min(700, totals['eligible_DC_untouched_carriers'])
    assert len({r['reference_source_channel'] for r in raw700}) == len(raw700)
    for rank, record in enumerate(raw700, 1):
        record['raw_rank'] = rank
    separated = []
    for record in raw700:
        if any(abs(record['reference_source_channel'] - old['reference_source_channel']) <= 3 for old in separated):
            continue
        separated.append(dict(record, frequency_separated_rank=len(separated) + 1))
        if len(separated) == 100:
            break
    if totals['eligible_DC_untouched_carriers'] >= 694:
        assert len(separated) == 100
        assert separated[-1]['raw_rank'] <= 694
    top3 = [dict(r, rank=i, exploratory_selection_rank=i) for i, r in enumerate(separated[:3], 1)]
    overlap = []
    for previous in previous9:
        old_id = identity(previous)
        in_raw = next((r for r in raw700 if identity(r) == old_id), None)
        in_separated = next((r for r in separated if identity(r) == old_id), None)
        in_top3 = next((r for r in top3 if identity(r) == old_id), None)
        overlap.append({'previous_exploratory_rank': previous['exploratory_selection_rank'],
                        'previous_query_id': previous['query_id'],
                        'reference_source_channel': previous['reference_source_channel'],
                        'raw_TOP700_rank': in_raw['raw_rank'] if in_raw else None,
                        'separated_TOP100_rank': in_separated['frequency_separated_rank'] if in_separated else None,
                        'new_TOP3_rank': in_top3['rank'] if in_top3 else None})
    result = {'schema': 'SETI_CACHED_CARRIER_TARGET_STREAMING_RANKS_V1',
              'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
              'primary_target': target, 'counts': totals, 'core_summaries': summaries,
              'raw_TOP700': raw700, 'raw_TOP100': raw700[:100],
              'frequency_separated_TOP100': separated, 'TOP3': top3,
              'previous_coremax_selection_overlap': overlap,
              'prefix_completeness': {'unique_reference_domains_verified': True, 'retained_raw_limit': 700,
                                      'bound_for_100th_separated_choice': 694,
                                      'actual_raw_rank_of_last_separated_choice': separated[-1]['raw_rank'] if separated else None},
              'ranking_rule': scope['rank_rule'], 'interpretation_limits': scope['interpretation_limits']}
    save(out / 'RESULT.json', result)
    write_list_csv(out / 'RAW_TOP700.csv', raw700)
    write_list_csv(out / 'RAW_TOP100.csv', raw700[:100])
    write_list_csv(out / 'SEPARATED_TOP100.csv', separated)
    write_list_csv(out / 'TOP3.csv', top3)
    output_names = ('RESULT.json', 'RAW_TOP700.csv', 'RAW_TOP100.csv', 'SEPARATED_TOP100.csv', 'TOP3.csv')
    outputs = [pin(out / name) for name in output_names]
    assert sum(p['bytes'] for p in outputs) <= scope['execution']['output_bytes_per_job']
    save(out / 'EXECUTION_RECEIPT.json', {'status': 'PASS_ONCE_CACHED_CARRIER_STREAMING_TARGET',
         'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
         'counts': totals, 'outputs': outputs, 'primary_target': target,
         'CPU_seconds': time.process_time() - start_cpu, 'wall_seconds': time.monotonic() - start_wall,
         'maximum_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         'target_rank_executions': 1})
    print(json.dumps({'target': target, 'status': 'PASS_ONCE_CACHED_CARRIER_STREAMING_TARGET',
                      'counts': totals, 'selected': [{k: r[k] for k in ('rank', 'frequency_hz_at_own_first_midpoint',
                                                                      'drift_hz_s', 'width_channels', 'score')}
                                                    for r in top3]}), flush=True)


def aggregate(scope, scope_sha):
    assert not (BASE / 'SELECTED_TOP9.json').exists(), 'No aggregate overwrite'
    combined, inputs, counts, overlap = [], [], {}, []
    for target in scope['targets']:
        out = BASE / target
        receipt = json.loads((out / 'EXECUTION_RECEIPT.json').read_text())
        assert receipt['status'] == 'PASS_ONCE_CACHED_CARRIER_STREAMING_TARGET'
        assert receipt['scope_sha256'] == scope_sha
        for item in receipt['outputs']:
            verify(item)
        source = json.loads((out / 'RESULT.json').read_text())
        assert source['primary_target'] == target and source['scope_sha256'] == scope_sha
        combined.extend(source['TOP3'])
        inputs.append(pin(out / 'RESULT.json'))
        for name, value in source['counts'].items():
            counts[name] = counts.get(name, 0) + value
        overlap.append({'primary_target': target, 'records': source['previous_coremax_selection_overlap']})
    assert counts['cached_carriers'] == 9375744 and counts['maps'] == 2289
    save(BASE / 'SELECTED_TOP9.json', {'schema': 'SETI_DC_UNTOUCHED_CACHED_CARRIER_TOP9_V1',
         'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
         'counts': counts, 'records': combined, 'source_target_result_pins': inputs,
         'previous_coremax_selection_overlap': overlap,
         'interpretation_limits': scope['interpretation_limits']})
    write_list_csv(BASE / 'SELECTED_TOP9.csv', combined)
    save(BASE / 'AGGREGATION_RECEIPT.json', {'status': 'PASS_NO_NEW_SELECTION_AGGREGATION',
         'scope_sha256': scope_sha, 'inputs': inputs,
         'outputs': [pin(BASE / 'SELECTED_TOP9.json'), pin(BASE / 'SELECTED_TOP9.csv')],
         'counts': counts, 'new_rank_executions': 0})
    print(json.dumps({'status': 'PASS_NO_NEW_SELECTION_AGGREGATION', 'counts': counts,
                      'selected_records': len(combined)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--go', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--target', choices=['HIP97319', 'HIP97461', 'HIP97663'])
    mode.add_argument('--aggregate', action='store_true')
    args = parser.parse_args()
    raw = (BASE / 'scope.json').read_bytes()
    scope, go = json.loads(raw), json.loads(args.go.read_text())
    assert go['authorized'] is True and go['scope_sha256'] == sha(raw)
    assert go['producer_sha256'] == sha(Path(__file__).read_bytes())
    if args.target:
        select_target(scope, sha(raw), args.target)
    else:
        aggregate(scope, sha(raw))


if __name__ == '__main__':
    main()
