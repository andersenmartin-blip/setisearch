"""Triage complete saved carrier maxima and existing zero-drift projections only.

No telescope reads, network calls, detector evaluation or new power decoding.
Threshold10/grouping/OFF projection comparisons are post-data descriptions;
flags require manual review and are neither vetoes nor confirmed candidates.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/radio_quicklook_20261009'
ORIGIN, END, COUNT = 159383552, 160432128, 1040384
ON = ('epoch1_on', 'epoch2_on', 'epoch3_on')
STATUS = 'COMPLETED_POST_DATA_EXPLORATORY_CACHED_TILE_DRIFT_SWEEP'
FIELDS = ('source_reference_channels', 'frequency_hz_at_tref',
          'maximum_robust_box_track_score', 'winning_drift_hz_s',
          'winning_width_channels', 'valid_hypothesis_count')


def read_json(path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def main():
    started, cpu = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    source, source_hash = read_json(ROOT / 'pilot_source_20261008/primary/source_manifest.json')
    if source_hash != '6a9c166f15de69c378e3346fcd5dac1082790345622b2df3af674f108bf29aec':
        raise ValueError('Frozen metadata source differs')
    items = {s['label']: s for s in source['sources']}
    inputs, coverages, directories = {}, [], ('tile_sweep', 'remaining_sweep')
    for directory, expected_tiles in zip(directories, (64, 190)):
        receipt, receipt_hash = read_json(BASE / directory / 'TILE_SWEEP_RECEIPT.json')
        coverage, coverage_hash = read_json(BASE / directory / 'coverage_manifest.json')
        cores = coverage['metadata_cores_half_open']
        if (receipt['status'] != STATUS or coverage['status'] != STATUS
                or receipt['source_manifest_sha256'] != source_hash
                or len(cores) != expected_tiles
                or receipt['complete_carriers_per_ON'] != 4096 * expected_tiles
                or receipt['hypotheses_per_carrier'] != 1526
                or receipt['drift_trials'] != 763 or receipt['widths_channels'] != [1, 3]):
            raise ValueError('Complete independent tile coverage receipt required')
        for scan in ON:
            expected = list(range(expected_tiles))
            if (receipt['complete_tiles_per_ON'][scan] != expected
                    or coverage['completed_tile_indices_by_ON'][scan] != expected):
                raise ValueError('Missing or repeated completed tile')
            rows = [x for x in coverage['completed_coverage'] if x['scan_id'] == scan]
            if len(rows) != expected_tiles or sorted(x['tile_index'] for x in rows) != expected:
                raise ValueError('Incomplete independent coverage rows')
            for row in rows:
                if (row['core_half_open'] != cores[row['tile_index']]
                        or row['carrier_count'] != 4096 or row['valid_hypotheses_per_carrier'] != 1526):
                    raise ValueError('Coverage geometry or hypotheses differ')
        inputs[directory] = {'receipt_sha256': receipt_hash, 'coverage_sha256': coverage_hash}
        coverages.extend(cores)
    if sorted(coverages) != [[lo, lo + 4096] for lo in range(ORIGIN + 4096, END - 4096, 4096)]:
        raise ValueError('Two independent coverage sets must exactly partition the interior')
    broad, broad_hash = read_json(BASE / 'broad_inventory/BROAD_INVENTORY_RECEIPT.json')
    if (broad['status'] != 'COMPLETED_EXPLORATORY_BROAD_ZERO_DRIFT_INVENTORY'
            or broad['source_manifest_sha256'] != source_hash):
        raise ValueError('Complete existing broad projection receipt required')
    profiles = {}
    for scan in items:
        with np.load(BASE / 'broad_inventory' / (scan + '_full_chunk_spectrum.npz'), allow_pickle=False) as f:
            z = f['robust_collapsed_residual_units']
            if int(f['source_channel0']) != ORIGIN or z.shape != (END - ORIGIN,) or not np.isfinite(z).all():
                raise ValueError('Incomplete or invalid saved zero-drift projection')
            profiles[scan] = z
    scans, groups = [], []
    for scan in ON:
        pieces = []
        for directory in directories:
            with np.load(BASE / directory / (scan + '_all_carrier_maxima.npz'), allow_pickle=False) as f:
                pieces.append({k: f[k] for k in FIELDS})
        arrays = {k: np.concatenate([p[k] for p in pieces]) for k in FIELDS}
        order = np.argsort(arrays[FIELDS[0]], kind='stable')
        arrays = {k: v[order] for k, v in arrays.items()}
        channels, frequencies, scores, drifts, widths, hypotheses = (arrays[k] for k in FIELDS)
        if (any(v.shape != (COUNT,) or not np.isfinite(v).all() for v in arrays.values())
                or not np.array_equal(channels, np.arange(ORIGIN + 4096, END - 4096))
                or not np.all(hypotheses == 1526) or not np.isin(widths, [1, 3]).all()
                or (np.abs(drifts) > 4).any()):
            raise ValueError('Merged carriers must be exact, unique, finite, complete and disjoint')
        header = items[scan]['current_header']['data_attributes']
        df, dt = header['foff'] * 1e6, header['tsamp']
        if not np.allclose(frequencies, header['fch1'] * 1e6 + df * channels, rtol=0, atol=1e-5):
            raise ValueError('Saved frequencies differ from native grid')

        def representative(i):
            return {'source_reference_channel': int(channels[i]), 'frequency_hz_at_first_midpoint': float(frequencies[i]),
                    'maximum_saved_score': float(scores[i]), 'winning_drift_hz_s': float(drifts[i]),
                    'winning_width_channels': int(widths[i])}

        selected = np.flatnonzero(scores >= 10)
        runs = np.split(selected, np.flatnonzero(np.diff(selected) > 1) + 1) if len(selected) else []
        scans.append({'scan_id': scan, 'unique_consecutive_complete_carriers': COUNT,
                      'carriers_at_or_above_descriptive_threshold10': int(len(selected)),
                      'contiguous_threshold_groups': len(runs), 'maximum': representative(int(np.argmax(scores)))})
        for rank, run in enumerate(runs, 1):
            i = int(run[np.argmax(scores[run])])
            centers = channels[i] + drifts[i] * np.arange(16) * dt / df
            lo, hi = max(ORIGIN, int(np.floor(centers.min())) - 32), min(END, int(np.ceil(centers.max())) + 33)
            comparison = []
            for target, z in profiles.items():
                j = lo - ORIGIN + int(np.argmax(z[lo - ORIGIN:hi - ORIGIN]))
                comparison.append({'scan_id': target, 'role': items[target]['role'].upper(),
                                   'maximum_saved_zero_drift_residual_units': float(z[j]),
                                   'source_channel': ORIGIN + j,
                                   'frequency_hz': float(header['fch1'] * 1e6 + df * (ORIGIN + j))})
            off = [x['maximum_saved_zero_drift_residual_units'] for x in comparison if x['role'] == 'OFF']
            groups.append({'group_id': f'{scan}_contiguous_{rank:04d}', 'scan_id': scan,
                           'source_channel_interval_half_open': [int(channels[run[0]]), int(channels[run[-1]]) + 1],
                           'carrier_count': int(len(run)), 'representative': representative(i),
                           'ON_trajectory_interval_plus32_channels_half_open': [lo, hi],
                           'cached_six_scan_projection_comparisons': comparison,
                           'maximum_OFF_saved_projection_units': max(off),
                           'manual_review_flag_all_three_OFF_projections_below10': all(x < 10 for x in off),
                           'counterevidence_only_no_veto_or_origin_classification': True})
    result = {'status': 'COMPLETED_SAVED_MAXIMA_DESCRIPTIVE_TRIAGE', 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_manifest_sha256': source_hash, 'coverage_inputs': inputs, 'broad_receipt_sha256': broad_hash,
              'merged_source_channel_interval_half_open': [ORIGIN + 4096, END - 4096],
              'descriptive_score_threshold': 10, 'scans': scans, 'groups': groups,
              'manual_review_flagged_group_ids': [g['group_id'] for g in groups if g['manual_review_flag_all_three_OFF_projections_below10']],
              'new_GETs': 0, 'new_detector_scores': 0, 'new_full_chunk_decodes': 0,
              'independent_visits': 1, 'qualification': False, 'automatic_veto': False,
              'limitations': ['Contiguous carrier groups and representatives are correlated descriptions, not independent signals',
                              'OFF comparison uses an existing full-time zero-drift projection, which can miss drifting or intermittent signals',
                              'Reference threshold10 is descriptive; no calibrated significance, FAP, origin or sky-null claim'],
              'CPU_seconds': time.process_time() - cpu, 'wall_seconds': time.monotonic() - started,
              'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    with (BASE / 'SIGNAL_TRIAGE.json').open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    with (BASE / 'SIGNAL_GROUPS.csv').open('x', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['group_id', 'scan_id', 'source_channel_start', 'source_channel_stop', 'carrier_count',
                    'representative_source_channel', 'reference_frequency_hz', 'saved_score', 'drift_hz_s', 'width_channels',
                    'maximum_OFF_saved_projection_units', 'manual_review_flag_all_OFF_below10'])
        for g in groups:
            p = g['representative']
            w.writerow([g['group_id'], g['scan_id'], *g['source_channel_interval_half_open'], g['carrier_count'],
                        p['source_reference_channel'], p['frequency_hz_at_first_midpoint'], p['maximum_saved_score'],
                        p['winning_drift_hz_s'], p['winning_width_channels'], g['maximum_OFF_saved_projection_units'],
                        g['manual_review_flag_all_three_OFF_projections_below10']])
    print(json.dumps({'status': result['status'], 'scans': scans, 'group_count': len(groups),
                      'flagged_group_ids': result['manual_review_flagged_group_ids'], 'CPU_seconds': result['CPU_seconds']}))


if __name__ == '__main__':
    main()
