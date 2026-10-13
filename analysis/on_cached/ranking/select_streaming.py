#!/usr/bin/env python3
"""Rank original ON cached winner paths after frozen DC geometry condition."""
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
ROOT = BASE.parent.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(pin):
    raw = (ROOT / pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], pin['path']
    return raw


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def canonical(r):
    return (-r['score'], r['frequency_hz_at_own_first_midpoint'], r['drift_hz_s'], r['width_channels'],
            r['native_chunk_index'], r['core_q'], r['carrier_index_in_core'])


def csv_save(path, values):
    names = ['primary_scan_id', 'primary_target', 'scan_id', 'native_chunk_index', 'core_q',
             'carrier_index_in_core', 'reference_source_channel', 'frequency_hz_at_own_first_midpoint',
             'reference_time_mjd', 'drift_hz_s', 'drift_grid_index', 'width_channels', 'score',
             'raw_rank', 'frequency_separated_rank', 'rank', 'is_cached_coremax_winner']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        for r in values:
            writer.writerow({k: r.get(k) for k in names})


def run_target(scope, scope_sha, scan_id):
    group = next(g for g in scope['groups'] if g['primary_scan_id'] == scan_id)
    out = BASE / scan_id
    assert not out.exists(), 'No original ON job overwrite or rerun'
    out.mkdir()
    started_cpu, started_wall = time.process_time(), time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    c = scope['constants']
    assert c == {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                 'tsamp_s': 18.253611008, 'rows': 16, 'core_channels': 4096,
                 'fine_channels_per_native': 1048576, 'DC_channels': [178782208, 179830784, 180879360]}
    times = np.asarray(group['original_origin_row_times_from_reference_s'])
    assert np.array_equal(times, np.arange(16) * c['tsamp_s'])
    assert group['primary_target'] == 'HIP98505' and group['original_acquisition_role'] == 'ON'
    heap, summaries, domains = [], [], []
    counts = {'maps': 0, 'cached_carriers': 0, 'eligible_DC_untouched_carriers': 0,
              'DC_contacting_cached_winner_carriers': 0, 'geometry_row_occurrences': 0,
              'DC_row_box_membership_checks': 0, 'source_map_hashes_verified': 0,
              'source_normalization_hashes_verified': 0, 'cached_coremax_indices_computed': 0,
              'new_detector_scores': 0, 'new_telescope_HTTP': 0, 'power_arrays_decoded': 0}
    for source in group['maps']:
        native, q = source['native_chunk_index'], source['core_q']
        domains.append(tuple(source['reference_channel_interval_half_open']))
        verify(source['normalization_pin'])
        with np.load(io.BytesIO(verify(source['map_pin'])), allow_pickle=False) as data:
            f, score, drift = (data[k] for k in ('frequency_hz_at_tref', 'maximum_robust_box_track_score', 'winning_drift_hz_s'))
            width, valid, channel, grid = (data[k] for k in ('winning_width_channels', 'valid_hypothesis_count', 'source_reference_channels', 'drift_grid_hz_s'))
        assert all(a.shape == (4096,) for a in (f, score, drift, width, valid, channel))
        assert all(np.isfinite(a).all() for a in (f, score, drift))
        assert np.array_equal(grid, np.linspace(-4.0, 4.0, 785))
        assert np.isin(width, [1, 3]).all() and np.all(valid == 1570)
        lo, hi = source['reference_channel_interval_half_open']
        assert np.array_equal(channel, np.arange(lo, hi))
        assert np.array_equal(f, c['fch1_hz'] + channel * c['df_hz'])
        grid_index = np.searchsorted(grid, drift)
        assert np.all(grid_index < 785) and np.array_equal(grid[grid_index], drift)
        centers = np.rint((f[:, None] - c['fch1_hz']) / c['df_hz']
                          + drift[:, None] * times[None, :] / c['df_hz']).astype(np.int64)
        assert np.array_equal(centers[:, 0], channel)
        contacts = np.any(np.abs(centers[:, :, None] - np.array(c['DC_channels'])[None, None, :])
                          <= width[:, None, None] // 2, axis=(1, 2))
        eligible = ~contacts
        indices = np.flatnonzero(eligible)
        order = indices[np.lexsort((indices, width[indices], drift[indices], f[indices], -score[indices]))]
        coremax = int(np.lexsort((channel, -score))[0])

        def record(index):
            return {'primary_scan_id': scan_id, 'primary_target': 'HIP98505', 'scan_id': scan_id,
                    'original_acquisition_role': 'ON', 'reference_origin_scan_id': scan_id,
                    'native_chunk_index': native, 'core_q': q, 'map_id': source['canonical_map_id'],
                    'carrier_index_in_core': int(index), 'reference_source_channel': int(channel[index]),
                    'frequency_hz_at_own_first_midpoint': float(f[index]),
                    'reference_time_mjd': group['reference_time_mjd'],
                    'reference_seconds_from_anchor': group['reference_seconds_from_anchor'],
                    'MJD_anchor': group['MJD_anchor'], 'origin_tstart_mjd': group['origin_tstart_mjd'],
                    'original_origin_row_times_from_reference_s': times.tolist(),
                    'drift_hz_s': float(drift[index]), 'drift_grid_index': int(grid_index[index]),
                    'width_channels': int(width[index]), 'score': float(score[index]),
                    'rounded_absolute_centers': centers[index].tolist(),
                    'map_pin': source['map_pin'], 'normalization_pin': source['normalization_pin'],
                    'original_checkpoint_pin': source['checkpoint_pin'],
                    'is_cached_coremax_winner': int(index) == coremax,
                    'cached_coremax_score': float(score[coremax]), 'eligible_DC_untouched': True}

        for index in order[:700]:
            quality = (float(score[index]), -float(f[index]), -float(drift[index]), -int(width[index]),
                       -native, -q, -int(index))
            if len(heap) < 700:
                heapq.heappush(heap, (quality, record(index)))
            elif quality > heap[0][0]:
                heapq.heapreplace(heap, (quality, record(index)))
        summaries.append({'primary_scan_id': scan_id, 'native_chunk_index': native, 'core_q': q,
                          'map_pin': source['map_pin'], 'normalization_pin': source['normalization_pin'],
                          'cached_carriers': 4096, 'eligible_DC_untouched_carriers': int(eligible.sum()),
                          'DC_contacting_cached_winner_carriers': int(contacts.sum()),
                          'cached_coremax_carrier_index': coremax, 'cached_coremax_score': float(score[coremax]),
                          'cached_coremax_DC_contact': bool(contacts[coremax]),
                          'eligible_maximum': record(order[0]) if len(order) else None})
        counts['maps'] += 1
        counts['cached_carriers'] += 4096
        counts['eligible_DC_untouched_carriers'] += int(eligible.sum())
        counts['DC_contacting_cached_winner_carriers'] += int(contacts.sum())
        counts['geometry_row_occurrences'] += 4096 * 16
        counts['DC_row_box_membership_checks'] += 4096 * 16 * 3
        counts['source_map_hashes_verified'] += 1
        counts['source_normalization_hashes_verified'] += 1
        counts['cached_coremax_indices_computed'] += 1
    assert counts['maps'] == 766 and counts['cached_carriers'] == 3137536
    domains.sort()
    assert all(a[1] <= b[0] for a, b in zip(domains, domains[1:]))
    raw700 = sorted((r for _, r in heap), key=canonical)
    assert len(raw700) == min(700, counts['eligible_DC_untouched_carriers'])
    assert len({r['reference_source_channel'] for r in raw700}) == len(raw700)
    for rank, r in enumerate(raw700, 1):
        r['raw_rank'] = rank
    separated = []
    for r in raw700:
        if any(abs(r['reference_source_channel'] - old['reference_source_channel']) <= 3 for old in separated):
            continue
        separated.append(dict(r, frequency_separated_rank=len(separated) + 1))
        if len(separated) == 100:
            break
    if counts['eligible_DC_untouched_carriers'] >= 694:
        assert len(separated) == 100 and separated[-1]['raw_rank'] <= 694
    top3 = [dict(r, rank=i, exploratory_selection_rank=i) for i, r in enumerate(separated[:3], 1)]
    result = {'schema': 'SETI_ON_CACHED_CARRIER_TARGET_STREAMING_RANKS_V1', 'scope_sha256': scope_sha,
              'producer_sha256': sha(Path(__file__).read_bytes()), 'primary_scan_id': scan_id,
              'primary_target': 'HIP98505', 'counts': counts, 'core_summaries': summaries,
              'raw_TOP700': raw700, 'raw_TOP100': raw700[:100], 'frequency_separated_TOP100': separated,
              'TOP3': top3, 'prefix_completeness': {'unique_reference_domains_verified': True,
                'retained_raw_limit': 700, 'bound_for_100th_separated_choice': 694,
                'actual_raw_rank_of_last_separated_choice': separated[-1]['raw_rank'] if separated else None},
              'interpretation_limits': scope['interpretation_limits']}
    save(out / 'RESULT.json', result)
    for name, values in (('RAW_TOP700.csv', raw700), ('RAW_TOP100.csv', raw700[:100]),
                         ('SEPARATED_TOP100.csv', separated), ('TOP3.csv', top3)):
        csv_save(out / name, values)
    outputs = [pin(out / name) for name in ('RESULT.json', 'RAW_TOP700.csv', 'RAW_TOP100.csv', 'SEPARATED_TOP100.csv', 'TOP3.csv')]
    assert sum(p['bytes'] for p in outputs) <= scope['limits']['output_bytes_per_job']
    save(out / 'EXECUTION_RECEIPT.json', {'status': 'PASS_ONCE_ON_CACHED_STREAMING_SELECTION',
          'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
          'primary_scan_id': scan_id, 'counts': counts, 'outputs': outputs,
          'CPU_seconds': time.process_time() - started_cpu, 'wall_seconds': time.monotonic() - started_wall,
          'maximum_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'primary_scan_rank_executions': 1})
    print(json.dumps({'status': 'PASS_ONCE_ON_CACHED_STREAMING_SELECTION', 'primary_scan_id': scan_id,
          'counts': counts, 'TOP3': [{k: r[k] for k in ('rank', 'frequency_hz_at_own_first_midpoint', 'drift_hz_s', 'width_channels', 'score')} for r in top3]}), flush=True)


def aggregate(scope, scope_sha):
    assert not (BASE / 'SELECTED_TOP9.json').exists(), 'No aggregate overwrite'
    records, sources, counts = [], [], {}
    for scan in scope['primary_scan_ids']:
        out = BASE / scan
        receipt = json.loads((out / 'EXECUTION_RECEIPT.json').read_text())
        assert receipt['status'] == 'PASS_ONCE_ON_CACHED_STREAMING_SELECTION' and receipt['scope_sha256'] == scope_sha
        for p in receipt['outputs']:
            verify(p)
        result = json.loads((out / 'RESULT.json').read_text())
        assert result['primary_scan_id'] == scan and result['scope_sha256'] == scope_sha
        records.extend(result['TOP3'])
        sources.append(pin(out / 'RESULT.json'))
        for name, value in result['counts'].items():
            counts[name] = counts.get(name, 0) + value
    assert counts['maps'] == 2298 and counts['cached_carriers'] == 9412608
    save(BASE / 'SELECTED_TOP9.json', {'schema': 'SETI_HIP98505_ON_DC_UNTOUCHED_CARRIER_TOP9_V1',
         'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
         'counts': counts, 'records': records, 'source_result_pins': sources,
         'interpretation_limits': scope['interpretation_limits']})
    csv_save(BASE / 'SELECTED_TOP9.csv', records)
    save(BASE / 'AGGREGATION_RECEIPT.json', {'status': 'PASS_ON_METADATA_ONLY_AGGREGATION',
         'scope_sha256': scope_sha, 'inputs': sources,
         'outputs': [pin(BASE / 'SELECTED_TOP9.json'), pin(BASE / 'SELECTED_TOP9.csv')],
         'counts': counts, 'new_rank_executions': 0})
    print(json.dumps({'status': 'PASS_ON_METADATA_ONLY_AGGREGATION', 'counts': counts, 'selected_records': len(records)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--go', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--scan', choices=['epoch1_on', 'epoch2_on', 'epoch3_on'])
    mode.add_argument('--aggregate', action='store_true')
    args = parser.parse_args()
    raw = (BASE / 'scope.json').read_bytes()
    scope, go = json.loads(raw), json.loads(args.go.read_text())
    assert go['authorized'] is True and go['scope_sha256'] == sha(raw)
    assert go['producer_sha256'] == sha(Path(__file__).read_bytes())
    if args.scan:
        run_target(scope, sha(raw), args.scan)
    else:
        aggregate(scope, sha(raw))


if __name__ == '__main__':
    main()
