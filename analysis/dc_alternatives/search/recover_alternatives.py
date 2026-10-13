#!/usr/bin/env python3
"""Recover clean original-grid hypotheses only at frozen DC-contact carriers."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import resource
import sys
import time
from importlib.metadata import version
import numpy as np
from scipy.ndimage import median_filter
import scipy

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT / 'on_cached/deps'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def verify(p):
    raw = (ROOT / p['path']).read_bytes()
    assert len(raw) == p['bytes'] and sha(raw) == p['sha256'], p['path']
    return raw


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def canonical(r):
    return (-r['score'], r['frequency_hz_at_own_first_midpoint'], r['drift_hz_s'], r['width_channels'],
            r['native_chunk_index'], r['core_q'], r['carrier_index_in_core'])


def point(group, original, score, drift, width, drift_index, centers):
    source = group['source_map_metadata']
    return {'primary_scan_id': group['primary_scan_id'], 'primary_target': 'HIP98505',
            'scan_id': group['primary_scan_id'], 'original_acquisition_role': 'ON',
            'reference_origin_scan_id': group['primary_scan_id'],
            'native_chunk_index': group['native_chunk_index'], 'core_q': group['core_q'],
            'carrier_index_in_core': original['carrier_index_in_core'],
            'reference_source_channel': original['reference_source_channel'],
            'frequency_hz_at_own_first_midpoint': original['frequency_hz_at_own_first_midpoint'],
            'reference_time_mjd': group['reference_time_mjd'],
            'origin_tstart_mjd': group['origin_tstart_mjd'],
            'reference_seconds_from_anchor': group['reference_seconds_from_anchor'], 'MJD_anchor': group['MJD_anchor'],
            'original_origin_row_times_from_reference_s': group['original_origin_row_times_from_reference_s'],
            'score': float(score), 'drift_hz_s': float(drift), 'width_channels': int(width),
            'drift_grid_index': int(drift_index), 'rounded_absolute_centers': centers.tolist(),
            'map_pin': source['map_pin'], 'normalization_pin': source['normalization_pin'],
            'original_checkpoint_pin': source['checkpoint_pin'],
            'score_provenance': 'EXACT_ORIGINAL_PREFIX_DC_UNTOUCHED_ALTERNATIVE',
            'source_kind': 'recovered_original_DC_free_hypothesis'}


def recover_group(group, originals, raw_parent, const, out):
    n = len(originals)
    frame = group['exact_original_frame']
    crop0 = frame['original_s_power_source_channel0']
    local0, local1 = frame['native_parent_slice_local_half_open']
    crop = np.array(raw_parent[:, local0:local1], dtype='<f4', order='C', copy=True)
    assert crop.shape == (16, 12096) and np.isfinite(crop).all() and np.all(crop >= 0)
    crop_path = out / (group['group_id'] + '_original_raw_frame.npz')
    np.savez(crop_path, raw_power=crop, source_channel0=np.asarray(crop0, dtype=np.int64),
             normalization_source_channel_interval_half_open=np.asarray(frame['normalization_source_channel_interval_half_open'], dtype=np.int64))
    norm = json.loads(verify(group['source_map_metadata']['normalization_pin']))
    assert np.array_equal(norm['normalization_source_channels'], np.arange(*frame['normalization_source_channel_interval_half_open']))
    level = np.asarray(norm['row_power_median'], dtype=np.float64)
    location = np.asarray(norm['row_winsorized_residual_location'], dtype=np.float64)
    scale = np.asarray(norm['row_residual_MAD_scale'], dtype=np.float64)
    assert all(a.shape == (16,) and np.isfinite(a).all() for a in (level, location, scale))
    assert np.all(level > 0) and np.all(scale > 0)
    normalized = crop.astype(np.float64) / level[:, None]
    residual = normalized - median_filter(normalized, size=(1, 501), mode='nearest')
    z = (residual - location[:, None]) / scale[:, None]
    prefix = np.zeros((16, 12097), dtype=np.float64)
    prefix[:, 1:] = np.cumsum(z, axis=1, dtype=np.float64)
    boxes = {w: prefix[:, w:] - prefix[:, :-w] for w in (1, 3)}
    with np.load(io.BytesIO(verify(group['source_map_metadata']['map_pin'])), allow_pickle=False) as data:
        grid = data['drift_grid_hz_s']
        f = data['frequency_hz_at_tref']
        cached_score, cached_drift, cached_width = (data[k] for k in ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_width_channels'))
    assert np.array_equal(grid, np.linspace(-4, 4, 785))
    indices = np.asarray([r['carrier_index_in_core'] for r in originals], dtype=np.int64)
    frequency = f[indices]
    assert np.array_equal(frequency, np.asarray([r['frequency_hz_at_own_first_midpoint'] for r in originals]))
    base = (frequency - const['fch1_hz']) / const['df_hz']
    times = np.asarray(group['original_origin_row_times_from_reference_s'])
    dcs = np.asarray(const['DC_channels'])
    original_best, clean_best = np.full(n, -np.inf), np.full(n, -np.inf)
    original_drift, clean_drift = np.full(n, np.nan), np.full(n, np.nan)
    original_width, clean_width = np.zeros(n, dtype=np.int16), np.zeros(n, dtype=np.int16)
    clean_grid_index = np.full(n, -1, dtype=np.int64)
    admissible_count = np.zeros(n, dtype=np.int64)
    evaluated = 0
    for width in (1, 3):
        for start in range(0, 785, 16):
            drifts = grid[start:start + 16]
            scores = np.zeros((len(drifts), n), dtype=np.float64)
            admissible = np.ones(scores.shape, dtype=bool)
            for row, elapsed in enumerate(times):
                centers = np.rint(base[None, :] + drifts[:, None] * elapsed / const['df_hz']).astype(np.int64)
                local = centers - crop0 - width // 2
                assert local.min() >= 0 and local.max() < boxes[width].shape[1]
                scores += boxes[width][row, local]
                admissible &= np.all(np.abs(centers[:, :, None] - dcs[None, None, :]) > width // 2, axis=2)
            scores /= np.sqrt(16 * width)
            evaluated += scores.size
            arg = scores.argmax(axis=0)
            values = scores[arg, np.arange(n)]
            improve = values > original_best
            original_best[improve] = values[improve]
            original_drift[improve] = drifts[arg[improve]]
            original_width[improve] = width
            admissible_count += admissible.sum(axis=0)
            scores[~admissible] = -np.inf
            arg = scores.argmax(axis=0)
            values = scores[arg, np.arange(n)]
            improve = values > clean_best
            clean_best[improve] = values[improve]
            clean_drift[improve] = drifts[arg[improve]]
            clean_width[improve] = width
            clean_grid_index[improve] = start + arg[improve]
    mismatches = np.flatnonzero((original_best != cached_score[indices]) |
                                 (original_drift != cached_drift[indices]) |
                                 (original_width != cached_width[indices]))
    if len(mismatches):
        save(out / (group['group_id'] + '_UNRESTRICTED_REPLAY_MISMATCH.json'),
             {'group_id': group['group_id'], 'mismatching_carriers': len(mismatches),
              'maximum_absolute_score_difference': float(np.max(np.abs(original_best - cached_score[indices]))),
              'indices': mismatches.tolist(), 'cached_score': cached_score[indices][mismatches].tolist(),
              'replayed_score': original_best[mismatches].tolist(),
              'cached_drift': cached_drift[indices][mismatches].tolist(),
              'replayed_drift': original_drift[mismatches].tolist()})
        raise ValueError('Exact original unrestricted winner reconciliation failed for ' + group['group_id'])
    winning_path = out / (group['group_id'] + '_RECOVERED_WINNERS.npz')
    np.savez(winning_path,
             reference_source_channel=np.asarray([r['reference_source_channel'] for r in originals], dtype=np.int64),
             carrier_index_in_core=indices, admissible_hypothesis_count=admissible_count,
             no_admissible_hypothesis=admissible_count == 0,
             clean_maximum_score=clean_best, clean_winning_drift_hz_s=clean_drift,
             clean_winning_width_channels=clean_width, clean_winning_drift_grid_index=clean_grid_index,
             original_cached_maximum_score=original_best,
             original_cached_winning_drift_hz_s=original_drift,
             original_cached_winning_width_channels=original_width)
    winning_pin = pin(winning_path)
    results, candidates = [], []
    for j, original in enumerate(originals):
        empty = admissible_count[j] == 0
        assert empty == (not np.isfinite(clean_best[j]))
        assert empty or clean_best[j] <= original_best[j]
        new = None
        if not empty:
            centers = np.rint(base[j] + clean_drift[j] * times / const['df_hz']).astype(np.int64)
            assert np.all(np.abs(centers[:, None] - dcs[None, :]) > clean_width[j] // 2)
            new = point(group, original, clean_best[j], clean_drift[j], clean_width[j], clean_grid_index[j], centers)
            new['authoritative_score_source'] = {
                'kind': 'recovered_original_DC_free_hypothesis', 'pin': winning_pin,
                'record_index': j, 'score_field': 'clean_maximum_score',
                'drift_field': 'clean_winning_drift_hz_s', 'width_field': 'clean_winning_width_channels',
                'channel_field': 'reference_source_channel', 'group_id': group['group_id']}
            candidates.append(new)
        results.append({'original_cached_tuple_and_DC_geometry': original,
                        'original_unrestricted_score_drift_width_reconciled_exactly': True,
                        'admissible_hypothesis_count': int(admissible_count[j]),
                        'no_admissible_hypothesis': bool(empty), 'status': 'EMPTY' if empty else 'RECOVERED_CLEAN_MAXIMUM',
                        'clean_maximum': new})
    return results, candidates, {'group_id': group['group_id'], 'inventory_carriers': n,
        'original_hypothesis_score_occurrences': evaluated,
        'admissible_hypothesis_occurrences': int(admissible_count.sum()),
        'EMPTY_carriers': int(np.count_nonzero(admissible_count == 0)),
        'original_unrestricted_tuples_reconciled_exactly': n, 'raw_frame_pin': pin(crop_path),
        'original_frame_source_channel0': crop0, 'recovered_winner_arrays_pin': winning_pin,
        'original_normalized_z_rowmajor_float64_sha256': sha(np.asarray(z, dtype='<f8').tobytes(order='C')),
        'original_normalization_pin': group['source_map_metadata']['normalization_pin']}


def run_job(scope, scope_sha, scan):
    import h5py, hdf5plugin
    actual = {'numpy': np.__version__, 'scipy': scipy.__version__, 'h5py': h5py.__version__,
              'HDF5': h5py.version.hdf5_version, 'hdf5plugin': version('hdf5plugin')}
    assert actual == scope['runtime']
    assert hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008)
    out = BASE / scan
    assert not out.exists(), 'No scientific job overwrite or rerun'
    out.mkdir()
    started_cpu, started_wall = time.process_time(), time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, 2147483648))
    inventory = json.loads(verify(scope['excluded_inventory_pin']))
    groups = [g for g in scope['groups'] if g['primary_scan_id'] == scan]
    assert len(groups) == 6
    results, candidates, summaries, proofs = [], [], [], []
    for native in (170, 171, 172):
        same_source = [g for g in groups if g['native_chunk_index'] == native]
        assert len(same_source) == 2 and same_source[0]['raw_source_pin'] == same_source[1]['raw_source_pin']
        source = same_source[0]['raw_source_metadata']
        verify(same_source[0]['raw_source_pin'])
        with h5py.File(ROOT / source['restored_path'], 'r', rdcc_nbytes=8 * 1024 ** 2) as handle:
            ds = handle['data']
            assert ds.shape == (16, 1, 1048576) and ds.dtype.str == '<f4'
            assert int(ds.attrs['original_source_frequency_chunk_origin']) == native * 1048576
            raw_parent = ds[:, 0, :]
        row_proof = []
        for declaration in source['decoded_rows']:
            row = np.asarray(raw_parent[declaration['time_row']], dtype='<f4').tobytes()
            assert len(row) == declaration['decoded_bytes'] and sha(row) == declaration['decoded_sha256']
            row_proof.append(declaration)
        proofs.append({'source_pin': same_source[0]['raw_source_pin'], 'decoded_row_hashes': row_proof})
        for group in same_source:
            originals = [inventory['records'][i] for i in group['excluded_inventory_indices']]
            r, c, s = recover_group(group, originals, raw_parent, scope['constants'], out)
            results.extend(r); candidates.extend(c); summaries.append(s)
        del raw_parent
    assert len(results) == 2361
    old_pin = next(r['result_pin'] for r in scope['cached_clean_prefixes'] if r['primary_scan_id'] == scan)
    old = json.loads(verify(old_pin))
    base = [dict(r, score_provenance='ORIGINAL_CACHED_DC_UNTOUCHED_WINNER') for r in old['raw_TOP700']]
    for r in base:
        r['source_kind'] = 'original_clean_cached_carrier_maximum'
        r['authoritative_score_source'] = {'kind': r['source_kind'], 'pin': r['map_pin'],
            'record_index': r['carrier_index_in_core'], 'score_field': 'maximum_robust_box_track_score',
            'drift_field': 'winning_drift_hz_s', 'width_field': 'winning_width_channels',
            'channel_field': 'source_reference_channels'}
    assert len(base) == 700
    assert not ({r['reference_source_channel'] for r in base} & {r['reference_source_channel'] for r in candidates})
    merged = sorted(base + candidates, key=canonical)[:700]
    assert len({r['reference_source_channel'] for r in merged}) == len(merged)
    for rank, r in enumerate(merged, 1):
        r['raw_rank'] = rank
    separated = []
    for r in merged:
        if any(abs(r['reference_source_channel'] - oldr['reference_source_channel']) <= 3 for oldr in separated):
            continue
        separated.append(dict(r, frequency_separated_rank=len(separated) + 1))
        if len(separated) == 100:
            break
    assert len(separated) == 100 and separated[-1]['raw_rank'] <= 694
    top3 = [dict(r, rank=i, exploratory_selection_rank=i) for i, r in enumerate(separated[:3], 1)]
    counts = {'inventory_carriers': len(results), 'recovered_nonempty_carriers': len(candidates),
        'EMPTY_carriers': len(results) - len(candidates),
        'original_unrestricted_tuples_reconciled_exactly': sum(s['original_unrestricted_tuples_reconciled_exactly'] for s in summaries),
        'original_hypothesis_score_occurrences': sum(s['original_hypothesis_score_occurrences'] for s in summaries),
        'admissible_hypothesis_occurrences': sum(s['admissible_hypothesis_occurrences'] for s in summaries),
        'complete_clean_family_nonempty_carriers': old['counts']['eligible_DC_untouched_carriers'] + len(candidates),
        'raw_frames_saved': len(summaries), 'native_sources_decoded_once': len(proofs),
        'new_normalization_fits': 0, 'new_telescope_HTTP': 0}
    result = {'schema': 'SETI_DC_ALTERNATIVE_ON_SEARCH_AND_EXACT_PREFIX_MERGE_V1',
        'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
        'primary_scan_id': scan, 'counts': counts, 'alternative_records': results,
        'group_summaries': summaries, 'source_row_proofs': proofs, 'raw_TOP700': merged,
        'raw_TOP100': merged[:100], 'frequency_separated_TOP100': separated, 'TOP3': top3,
        'previous_ON_TOP3': old['TOP3'], 'cached_clean_prefix_pin': old_pin,
        'prefix_completeness': {'raw_prefix_limit': 700, 'separated_100_bound': 694,
                                'last_separated_choice_raw_rank': separated[-1]['raw_rank']},
        'interpretation_limits': scope['interpretation_limits']}
    save(out / 'RESULT.json', result)
    with (out / 'RECOVERED_CARRIERS.csv').open('w', newline='') as stream:
        names = ['group_id', 'reference_source_channel', 'carrier_index_in_core', 'status', 'admissible_hypothesis_count',
                 'original_score', 'original_drift', 'original_width', 'clean_score', 'clean_drift', 'clean_width']
        writer = csv.DictWriter(stream, fieldnames=names); writer.writeheader()
        for r in results:
            o, c = r['original_cached_tuple_and_DC_geometry'], r['clean_maximum']
            writer.writerow({'group_id': o['group_id'], 'reference_source_channel': o['reference_source_channel'],
                'carrier_index_in_core': o['carrier_index_in_core'], 'status': r['status'],
                'admissible_hypothesis_count': r['admissible_hypothesis_count'],
                'original_score': o['original_cached_score'], 'original_drift': o['original_cached_drift_hz_s'],
                'original_width': o['original_cached_width_channels'], 'clean_score': c['score'] if c else None,
                'clean_drift': c['drift_hz_s'] if c else None, 'clean_width': c['width_channels'] if c else None})
    outputs = [pin(p) for p in sorted(out.glob('*')) if p.is_file()]
    assert sum(p['bytes'] for p in outputs) <= scope['limits']['output_bytes_per_job']
    save(out / 'EXECUTION_RECEIPT.json', {'status': 'PASS_EXACT_ORIGINAL_UNRESTRICTED_REPLAY_AND_DC_ALTERNATIVES',
         'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
         'primary_scan_id': scan, 'counts': counts, 'outputs': outputs, 'runtime': actual,
         'CPU_seconds': time.process_time() - started_cpu, 'wall_seconds': time.monotonic() - started_wall,
         'maximum_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    print(json.dumps({'status': 'PASS_EXACT_ORIGINAL_UNRESTRICTED_REPLAY_AND_DC_ALTERNATIVES',
                      'primary_scan_id': scan, 'counts': counts,
                      'TOP3': [{k: r[k] for k in ('rank', 'frequency_hz_at_own_first_midpoint', 'drift_hz_s', 'width_channels', 'score', 'score_provenance')} for r in top3]}), flush=True)


def aggregate(scope, scope_sha):
    assert not (BASE / 'SELECTED_TOP9.json').exists()
    selected, inputs, totals = [], [], {}
    for scan in scope['primary_scan_ids']:
        out = BASE / scan
        receipt = json.loads((out / 'EXECUTION_RECEIPT.json').read_text())
        assert receipt['status'] == 'PASS_EXACT_ORIGINAL_UNRESTRICTED_REPLAY_AND_DC_ALTERNATIVES'
        assert receipt['scope_sha256'] == scope_sha
        for p in receipt['outputs']:
            verify(p)
        result = json.loads((out / 'RESULT.json').read_text())
        selected.extend(result['TOP3']); inputs.append(pin(out / 'RESULT.json'))
        for k, v in result['counts'].items(): totals[k] = totals.get(k, 0) + v
    assert totals['inventory_carriers'] == 7083 and totals['original_hypothesis_score_occurrences'] == 11120310
    save(BASE / 'SELECTED_TOP9.json', {'schema': 'SETI_COMPLETE_ORIGINAL_DC_UNTOUCHED_FAMILY_TOP9_V1',
         'scope_sha256': scope_sha, 'producer_sha256': sha(Path(__file__).read_bytes()),
         'counts': totals, 'records': selected, 'source_result_pins': inputs,
         'interpretation_limits': scope['interpretation_limits']})
    save(BASE / 'AGGREGATION_RECEIPT.json', {'status': 'PASS_METADATA_ONLY_ALTERNATIVE_AGGREGATION',
         'scope_sha256': scope_sha, 'inputs': inputs, 'outputs': [pin(BASE / 'SELECTED_TOP9.json')],
         'counts': totals, 'new_hypothesis_scores': 0})
    print(json.dumps({'status': 'PASS_METADATA_ONLY_ALTERNATIVE_AGGREGATION', 'counts': totals}), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--go', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--scan', choices=['epoch1_on', 'epoch2_on', 'epoch3_on']); mode.add_argument('--aggregate', action='store_true')
    args = parser.parse_args()
    raw = (BASE / 'scope.json').read_bytes(); scope, go = json.loads(raw), json.loads(args.go.read_text())
    assert go['authorized'] is True and go['scope_sha256'] == sha(raw)
    assert go['producer_sha256'] == sha(Path(__file__).read_bytes())
    if args.scan: run_job(scope, sha(raw), args.scan)
    else: aggregate(scope, sha(raw))


if __name__ == '__main__':
    main()
