#!/usr/bin/env python3
"""Deterministic inventory from previously exposed cached winner geometry."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
OLD = ROOT / 'on_cached/ranking'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


def verify(p):
    raw = (ROOT / p['path']).read_bytes()
    assert len(raw) == p['bytes'] and sha(raw) == p['sha256'], p['path']
    return raw


scope = json.loads((OLD / 'scope.json').read_text())
c = scope['constants']
records, groups, inputs = [], [], [pin(OLD / 'scope.json')]
for primary in scope['groups']:
    scan = primary['primary_scan_id']
    prior_path = OLD / scan / 'RESULT.json'
    prior = json.loads(prior_path.read_text())
    receipt = json.loads((OLD / scan / 'EXECUTION_RECEIPT.json').read_text())
    result_pin = next(p for p in receipt['outputs'] if p['path'].endswith('/RESULT.json'))
    assert pin(prior_path) == result_pin
    inputs.append(result_pin)
    summaries = {(r['native_chunk_index'], r['core_q']): r for r in prior['core_summaries']}
    times = np.asarray(primary['original_origin_row_times_from_reference_s'])
    assert np.array_equal(times, np.arange(16) * c['tsamp_s'])
    for source in sorted(primary['maps'], key=lambda r: (r['native_chunk_index'], r['core_q'])):
        n, q = source['native_chunk_index'], source['core_q']
        summary = summaries[n, q]
        if summary['DC_contacting_cached_winner_carriers'] == 0:
            continue
        with np.load(io.BytesIO(verify(source['map_pin'])), allow_pickle=False) as data:
            f, drift, width = (data[k] for k in ('frequency_hz_at_tref', 'winning_drift_hz_s', 'winning_width_channels'))
            channel, score, grid = (data[k] for k in ('source_reference_channels', 'maximum_robust_box_track_score', 'drift_grid_hz_s'))
        assert np.array_equal(grid, np.linspace(-4, 4, 785))
        centers = np.rint((f[:, None] - c['fch1_hz']) / c['df_hz'] + drift[:, None] * times[None, :] / c['df_hz']).astype(np.int64)
        per_dc = np.abs(centers[:, :, None] - np.asarray(c['DC_channels'])[None, None, :]) <= width[:, None, None] // 2
        touched_rows = np.any(per_dc, axis=2)
        excluded = np.flatnonzero(np.any(touched_rows, axis=1))
        assert len(excluded) == summary['DC_contacting_cached_winner_carriers']
        group_id = source['canonical_map_id']
        groups.append({'group_id': group_id, 'primary_scan_id': scan, 'primary_target': 'HIP98505',
                       'original_acquisition_role': 'ON', 'native_chunk_index': n, 'core_q': q,
                       'origin_tstart_mjd': primary['origin_tstart_mjd'],
                       'reference_time_mjd': primary['reference_time_mjd'],
                       'reference_seconds_from_anchor': primary['reference_seconds_from_anchor'],
                       'MJD_anchor': primary['MJD_anchor'],
                       'original_origin_row_times_from_reference_s': times.tolist(),
                       'source_map_metadata': source, 'excluded_count': len(excluded)})
        for index in excluded:
            records.append({'group_id': group_id, 'primary_scan_id': scan, 'native_chunk_index': n, 'core_q': q,
                'carrier_index_in_core': int(index), 'reference_source_channel': int(channel[index]),
                'frequency_hz_at_own_first_midpoint': float(f[index]),
                'original_cached_score': float(score[index]), 'original_cached_drift_hz_s': float(drift[index]),
                'original_cached_drift_grid_index': int(np.searchsorted(grid, drift[index])),
                'original_cached_width_channels': int(width[index]),
                'original_cached_rounded_centers': centers[index].tolist(),
                'original_DC_contact_row_indices': np.flatnonzero(touched_rows[index]).tolist(),
                'original_DC_contact_counts_by_bin': {str(dc): int(np.count_nonzero(per_dc[index, :, j]))
                                                      for j, dc in enumerate(c['DC_channels'])}})
assert len(groups) == 18 and len(records) == 7083
assert len({(r['primary_scan_id'], r['reference_source_channel']) for r in records}) == 7083
result = {'schema': 'SETI_EXPOSED_DC_CONTACT_CARRIER_INVENTORY_V1', 'constants': c,
          'counts': {'groups': 18, 'excluded_cached_carriers': 7083, 'excluded_per_ON': 2361},
          'groups': groups, 'records': records, 'source_input_pins': inputs,
          'authorization': 'Root authorized deterministic inventory of already exposed cached winner geometry before new raw/hypothesis scores.',
          'new_raw_values_queried': 0, 'new_hypothesis_scores': 0, 'new_normalization_fits': 0}
path = BASE / 'EXCLUDED_CARRIERS.json'
assert not path.exists(), 'Preserve first inventory'
raw = (json.dumps(result, indent=2, allow_nan=False) + '\n').encode()
path.write_bytes(raw)
compressed = gzip.compress(raw, compresslevel=9, mtime=0)
(BASE / 'EXCLUDED_CARRIERS.json.gz').write_bytes(compressed)
assert gzip.decompress(compressed) == raw
with (BASE / 'EXCLUDED_CARRIERS.csv').open('x', newline='') as stream:
    fields = list(records[0])
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for record in records:
        row = dict(record)
        for k in ('original_cached_rounded_centers', 'original_DC_contact_row_indices', 'original_DC_contact_counts_by_bin'):
            row[k] = json.dumps(row[k], separators=(',', ':'))
        writer.writerow(row)
receipt = {'status': 'PASS_EXPOSED7083_GEOMETRY_INVENTORY18_GROUPS', 'inputs': inputs,
           'outputs': [pin(path), pin(BASE / 'EXCLUDED_CARRIERS.json.gz'), pin(BASE / 'EXCLUDED_CARRIERS.csv')],
           'excluded_per_ON': {scan: sum(r['primary_scan_id'] == scan for r in records) for scan in scope['primary_scan_ids']},
           'new_raw_values_queried': 0, 'new_hypothesis_scores': 0}
(BASE / 'INVENTORY_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'counts': result['counts'],
                  'inventory_sha256': sha(raw), 'compressed_inventory_sha256': sha(compressed)}))
