#!/usr/bin/env python3
"""Annotate previously selected TOP20 tuples; no power, detector or reranking."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import sys
import time
import zipfile

import numpy as np


BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent
FCH1_HZ = 2802832031.25
DF_HZ = -2.7939677238464355
TSAMP_S = 18.253611008
NATIVE_CHANNELS = 1048576
DC_CHANNELS = [native * NATIVE_CHANNELS + 524288 for native in (170, 171, 172)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json_pinned(item):
    path = WORKSPACE / item['path']
    raw = path.read_bytes()
    assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], path
    return json.loads(raw)


def centers_member(path):
    # Open only the geometry member. Never access raw_power.npy.
    with zipfile.ZipFile(path) as archive:
        return archive.read('rounded_absolute_centers.npy')


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def write_csv(path, records):
    fields = ['phase', 'primary_target', 'scan_id', 'original_rank', 'score',
              'frequency_hz_at_own_first_midpoint', 'reference_source_channel',
              'native_chunk_index', 'core_q', 'carrier_index_in_core',
              'drift_hz_s', 'width_channels', 'nearest_frozen_DC_channel',
              'reference_offset_from_nearest_DC_channels',
              'rows_intersecting_any_frozen_DC', 'row_indices_intersecting_any_frozen_DC',
              'rounded_absolute_centers', 'center_offsets_from_nearest_DC',
              'touch_counts_by_frozen_DC', 'source_TOP20_path']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for value in records:
            row = {key: value[key] for key in fields}
            for key in ('row_indices_intersecting_any_frozen_DC', 'rounded_absolute_centers',
                        'center_offsets_from_nearest_DC', 'touch_counts_by_frozen_DC'):
                row[key] = json.dumps(row[key], separators=(',', ':'))
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', type=Path, default=BASE / 'scope.json')
    parser.add_argument('--go', type=Path, required=True)
    args = parser.parse_args()
    scope_raw = args.scope.read_bytes()
    scope = json.loads(scope_raw)
    go = json.loads(args.go.read_text())
    assert go['scope_sha256'] == digest(scope_raw)
    assert go['producer_sha256'] == digest(Path(__file__).read_bytes())
    assert go['authorized'] is True
    assert not (BASE / 'ANNOTATED_TOP120.json').exists(), 'No rerun/overwrite permitted'
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
    started_wall, started_cpu = time.monotonic(), time.process_time()
    assert scope['constants'] == {
        'fch1_hz': FCH1_HZ, 'df_hz': DF_HZ, 'tsamp_s': TSAMP_S,
        'rows': 16, 'fine_channels_per_native': NATIVE_CHANNELS,
        'native_indices': [170, 171, 172], 'DC_channels': DC_CHANNELS}
    times = np.arange(16, dtype=np.float64) * TSAMP_S
    records, summaries, checks = [], [], []
    for group in scope['groups']:
        top20, top3 = read_json_pinned(group['top20']), read_json_pinned(group['top3'])
        assert len(top20['records']) == 20 and len(top3['records']) == 3
        assert top3['records'] == top20['records'][:3]
        assert top20['original_acquisition_role'] == 'OFF'
        assert top20['scan_id'] == group['scan_id']
        assert top20['primary_id'] == group['primary_id']
        group_records = []
        for original_rank, record in enumerate(top20['records'], 1):
            assert record['rank'] == original_rank
            assert record['scan_id'] == group['scan_id']
            assert record['primary_target'] == group['primary_target']
            assert record['original_acquisition_role'] == 'OFF'
            for name in ('score', 'drift_hz_s', 'frequency_hz_at_own_first_midpoint'):
                assert np.isfinite(record[name])
            width = record['width_channels']
            assert width in (1, 3)
            reference = record['reference_source_channel']
            native = record.get('native_chunk_index', 171)
            assert native in group['natives']
            assert reference == native * NATIVE_CHANNELS + record['core_q'] * 4096 + record['carrier_index_in_core']
            expected_frequency = FCH1_HZ + reference * DF_HZ
            assert abs(record['frequency_hz_at_own_first_midpoint'] - expected_frequency) <= 1e-6
            rounded = np.rint((record['frequency_hz_at_own_first_midpoint'] - FCH1_HZ) / DF_HZ
                              + record['drift_hz_s'] * times / DF_HZ).astype(np.int64)
            assert int(rounded[0]) == reference
            if original_rank <= 3:
                capsule = group['top3_centers'][original_rank - 1]
                raw = centers_member(WORKSPACE / capsule['path'])
                assert len(raw) == capsule['member_bytes'] and digest(raw) == capsule['member_sha256']
                saved = np.load(io.BytesIO(raw), allow_pickle=False)
                assert saved.shape == (16,) and np.array_equal(saved, rounded)
                checks.append({'phase': group['phase'], 'primary_target': group['primary_target'],
                               'original_rank': original_rank, 'direct_saved_centers_equal': True,
                               'geometry_member_sha256': digest(raw)})
            nearest_dc = min(DC_CHANNELS, key=lambda channel: (abs(reference - channel), channel))
            half = width // 2
            counts = {str(dc): int(np.count_nonzero(np.abs(rounded - dc) <= half)) for dc in DC_CHANNELS}
            touch = np.any(np.abs(rounded[:, None] - np.array(DC_CHANNELS)[None, :]) <= half, axis=1)
            annotated = dict(record)
            annotated.update({
                'phase': group['phase'], 'original_rank': original_rank,
                'native_chunk_index': native, 'source_TOP20_path': group['top20']['path'],
                'nearest_frozen_DC_channel': nearest_dc,
                'reference_offset_from_nearest_DC_channels': reference - nearest_dc,
                'rounded_absolute_centers': rounded.tolist(),
                'center_offsets_from_nearest_DC': (rounded - nearest_dc).tolist(),
                'touch_counts_by_frozen_DC': counts,
                'rows_intersecting_any_frozen_DC': int(np.count_nonzero(touch)),
                'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touch).tolist(),
                'geometrically_DC_untouched': not bool(np.any(touch)),
                'classification': 'geometry_only_not_a_veto_or_physical_source_label'})
            records.append(annotated)
            group_records.append(annotated)
        summaries.append({
            'phase': group['phase'], 'primary_target': group['primary_target'],
            'scan_id': group['scan_id'], 'records': len(group_records),
            'DC_touched_records': sum(not r['geometrically_DC_untouched'] for r in group_records),
            'DC_untouched_records': sum(r['geometrically_DC_untouched'] for r in group_records),
            'untouched_original_ranks': [r['original_rank'] for r in group_records if r['geometrically_DC_untouched']],
            'touch_rows_in_original_rank_order': [r['rows_intersecting_any_frozen_DC'] for r in group_records]})
    assert len(records) == 120 and len(checks) == 18
    untouched = [r for r in records if r['geometrically_DC_untouched']]
    result = {
        'schema': 'SETI_FROZEN_EXISTING_TOP120_DC_CONTACT_ANNOTATION_V1',
        'scope_sha256': digest(scope_raw),
        'producer_sha256': digest(Path(__file__).read_bytes()),
        'constants': scope['constants'], 'groups': summaries, 'records': records,
        'geometry_verification': checks,
        'interpretation': scope['interpretation'],
        'counts': {'stored_records_annotated': len(records), 'geometry_row_occurrences': len(records) * 16,
                   'frozen_DC_row_box_contact_checks': len(records) * 16 * 3,
                   'direct_saved_TOP3_center_arrays_checked': len(checks),
                   'new_detector_scores': 0, 'new_source_spectral_profiles': 0,
                   'new_telescope_requests': 0, 'reranked_records': 0,
                   'DC_touched_records': len(records) - len(untouched), 'DC_untouched_records': len(untouched)}}
    write_json(BASE / 'ANNOTATED_TOP120.json', result)
    write_csv(BASE / 'ANNOTATED_TOP120.csv', records)
    write_json(BASE / 'DC_UNTOUCHED_EXPOSED_SUBSET.json', {
        'schema': 'SETI_INCOMPLETE_EXPOSED_STORED_WINNER_SUBSET_V1',
        'scope_sha256': digest(scope_raw), 'interpretation': scope['interpretation'],
        'original_order_preserved': True, 'records': untouched})
    write_csv(BASE / 'DC_UNTOUCHED_EXPOSED_SUBSET.csv', untouched)
    output_pins = []
    for name in ('ANNOTATED_TOP120.json', 'ANNOTATED_TOP120.csv',
                 'DC_UNTOUCHED_EXPOSED_SUBSET.json', 'DC_UNTOUCHED_EXPOSED_SUBSET.csv'):
        raw = (BASE / name).read_bytes()
        output_pins.append({'path': str((BASE / name).relative_to(WORKSPACE)), 'bytes': len(raw), 'sha256': digest(raw)})
    write_json(BASE / 'EXECUTION_RECEIPT.json', {
        'status': 'PASS_120_EXISTING_WINNERS_GEOMETRY_ONLY',
        'scope_sha256': digest(scope_raw), 'producer_sha256': digest(Path(__file__).read_bytes()),
        'counts': result['counts'], 'groups': summaries,
        'CPU_seconds': time.process_time() - started_cpu, 'wall_seconds': time.monotonic() - started_wall,
        'maximum_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'outputs': output_pins, 'new_power_values_opened_or_computed_by_this_producer': 0,
        'source_geometry_members_only': True})
    print(json.dumps({'status': 'PASS_120_EXISTING_WINNERS_GEOMETRY_ONLY', 'counts': result['counts'], 'groups': summaries}))


if __name__ == '__main__':
    main()
