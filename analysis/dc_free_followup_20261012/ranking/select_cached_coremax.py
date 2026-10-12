#!/usr/bin/env python3
"""One prospective DC-contact exclusion and ranking of cached core winners."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import resource
import time
import zipfile
import numpy as np

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_pin(pin):
    raw = (WORKSPACE / pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], pin['path']
    return raw


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csv_write(path, values):
    keys = ['phase', 'primary_target', 'scan_id', 'native_chunk_index', 'core_q',
            'carrier_index_in_core', 'reference_source_channel',
            'frequency_hz_at_own_first_midpoint', 'reference_time_mjd', 'drift_hz_s',
            'width_channels', 'score', 'query_id', 'map_id',
            'rows_intersecting_any_frozen_DC', 'eligible_DC_untouched',
            'exploratory_selection_rank', 'rounded_absolute_centers',
            'row_indices_intersecting_any_frozen_DC', 'capsule_path', 'capsule_sha256']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for record in values:
            row = {k: record[k] for k in keys}
            for k in ('rounded_absolute_centers', 'row_indices_intersecting_any_frozen_DC'):
                row[k] = json.dumps(row[k], separators=(',', ':'))
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--go', type=Path, required=True)
    args = parser.parse_args()
    scope_raw = (BASE / 'scope.json').read_bytes()
    scope, go = json.loads(scope_raw), json.loads(args.go.read_text())
    producer_sha = sha(Path(__file__).read_bytes())
    assert go['authorized'] is True
    assert go['scope_sha256'] == sha(scope_raw) and go['producer_sha256'] == producer_sha
    assert not (BASE / 'ALL2289_GEOMETRY.json').exists(), 'No overwrite or rerun'
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
    resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
    start_wall, start_cpu = time.monotonic(), time.process_time()
    constants = scope['constants']
    assert constants == {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                         'tsamp_s': 18.253611008, 'rows': 16,
                         'fine_channels_per_native': 1048576,
                         'native_indices': [170, 171, 172],
                         'DC_channels': [178782208, 179830784, 180879360]}
    fch1, df, tsamp = constants['fch1_hz'], constants['df_hz'], constants['tsamp_s']
    times, dcs = np.arange(16) * tsamp, np.array(constants['DC_channels'])
    # Independent historical CSV summaries must match original audit tuples.
    csv_index = {}
    for pin in scope['CSV_consistency_sources']:
        for row in csv.DictReader(io.StringIO(verify_pin(pin).decode())):
            key = (row['primary_target'], row['map_id'])
            assert key not in csv_index
            csv_index[key] = row
    assert len(csv_index) == 2289
    records, summaries = [], []
    for group in scope['groups']:
        audits = json.loads(verify_pin(group['audit_index']))
        maps = json.loads(verify_pin(group['map_index']))
        originals = [r for r in audits['records'] if r['query_kind'] == 'core_max']
        assert len(originals) == group['expected_coremax_records']
        assert len(maps['records']) == group['expected_coremax_records']
        assert len(group['core_sources']) == len(originals)
        group_result = []
        for source, original in zip(group['core_sources'], originals):
            record = dict(original['selected_tuple'])
            assert source['query_id'] == original['query_id'] and source['map_id'] == record['map_id']
            assert original['capsule'] == source['capsule']
            assert record['scan_id'] == group['scan_id'] and record['primary_target'] == group['primary_target']
            assert record['original_acquisition_role'] == 'OFF'
            native = record.get('native_chunk_index', 171)
            assert native == source['native_chunk_index'] and record['core_q'] == source['core_q']
            assert record['reference_source_channel'] == native * 1048576 + record['core_q'] * 4096 + record['carrier_index_in_core']
            assert np.isfinite(record['score']) and np.isfinite(record['drift_hz_s'])
            assert record['width_channels'] in (1, 3)
            csv_row = csv_index[(record['primary_target'], record['map_id'])]
            for name in ('score', 'drift_hz_s', 'frequency_hz_at_own_first_midpoint', 'reference_time_mjd'):
                assert float(csv_row[name]) == record[name], (record['map_id'], name)
            for name in ('core_q', 'carrier_index_in_core', 'reference_source_channel', 'width_channels', 'drift_grid_index'):
                assert int(csv_row[name]) == record[name]
            assert abs(record['frequency_hz_at_own_first_midpoint'] - (fch1 + record['reference_source_channel'] * df)) <= 1e-6
            centers = np.rint((record['frequency_hz_at_own_first_midpoint'] - fch1) / df
                              + record['drift_hz_s'] * times / df).astype(np.int64)
            capsule_raw = (WORKSPACE / source['local_capsule_path']).read_bytes()
            assert len(capsule_raw) == source['capsule']['bytes'] and sha(capsule_raw) == source['capsule']['sha256']
            with zipfile.ZipFile(io.BytesIO(capsule_raw)) as archive:
                center_bytes = archive.read('rounded_absolute_centers.npy')
            saved_centers = np.load(io.BytesIO(center_bytes), allow_pickle=False)
            assert saved_centers.shape == (16,) and np.array_equal(saved_centers, centers)
            half = record['width_channels'] // 2
            contacts = np.abs(centers[:, None] - dcs[None, :]) <= half
            touched_rows = np.any(contacts, axis=1)
            record.update({'phase': group['phase'], 'native_chunk_index': native,
                           'query_id': original['query_id'],
                           'rounded_absolute_centers': centers.tolist(),
                           'touch_counts_by_frozen_DC': {str(dc): int(np.count_nonzero(contacts[:, i])) for i, dc in enumerate(dcs)},
                           'rows_intersecting_any_frozen_DC': int(np.count_nonzero(touched_rows)),
                           'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touched_rows).tolist(),
                           'eligible_DC_untouched': not bool(np.any(touched_rows)),
                           'exploratory_selection_rank': None,
                           'capsule_path': source['local_capsule_path'],
                           'capsule_sha256': source['capsule']['sha256'],
                           'normalization': source['normalization'],
                           'original_map': source['original_map'],
                           'geometry_member_sha256': sha(center_bytes)})
            records.append(record)
            group_result.append(record)
        summaries.append({'phase': group['phase'], 'primary_target': group['primary_target'],
                          'records': len(group_result),
                          'eligible_DC_untouched': sum(r['eligible_DC_untouched'] for r in group_result),
                          'excluded_by_DC_contact': sum(not r['eligible_DC_untouched'] for r in group_result)})
    assert len(records) == 2289
    selected, target_summaries = [], []
    for target in ('HIP97319', 'HIP97461', 'HIP97663'):
        all_target = [r for r in records if r['primary_target'] == target]
        assert len(all_target) == 763
        eligible = [r for r in all_target if r['eligible_DC_untouched']]
        ordered = sorted(eligible, key=lambda r: (-r['score'], r['frequency_hz_at_own_first_midpoint'],
                                                 r['drift_hz_s'], r['width_channels'], r['native_chunk_index'],
                                                 r['core_q'], r['carrier_index_in_core']))
        chosen = []
        for record in ordered:
            if any(abs(record['reference_source_channel'] - old['reference_source_channel']) <= 3 for old in chosen):
                continue
            record['exploratory_selection_rank'] = len(chosen) + 1
            chosen.append(record)
            if len(chosen) == 3:
                break
        selected.extend(chosen)
        target_summaries.append({'primary_target': target, 'stored_core_winners': len(all_target),
                                 'eligible_DC_untouched': len(eligible),
                                 'excluded_by_DC_contact': len(all_target) - len(eligible),
                                 'selected': len(chosen), 'EMPTY': not bool(chosen)})
    counts = {'stored_core_winners': len(records),
              'eligible_DC_untouched': sum(r['eligible_DC_untouched'] for r in records),
              'excluded_by_DC_contact': sum(not r['eligible_DC_untouched'] for r in records),
              'geometry_rows': len(records) * 16, 'frozen_DC_row_box_checks': len(records) * 16 * 3,
              'whole_capsule_hashes_checked': len(records), 'saved_center_vectors_checked': len(records),
              'selected_records': len(selected), 'new_detector_scores': 0, 'decoded_power_arrays': 0,
              'new_frequency_coverage': 0, 'new_telescope_requests': 0}
    common = {'scope_sha256': sha(scope_raw), 'producer_sha256': producer_sha,
              'counts': counts, 'group_summary': summaries, 'target_summary': target_summaries,
              'interpretation_limits': scope['interpretation_limits']}
    write_json(BASE / 'ALL2289_GEOMETRY.json', dict(common, schema='SETI_ALL2289_CACHED_COREMAX_GEOMETRY_V1', records=records))
    csv_write(BASE / 'ALL2289_GEOMETRY.csv', records)
    write_json(BASE / 'SELECTED_TOP9.json', dict(common, schema='SETI_DC_UNTOUCHED_EXPOSED_COREMAX_TOP9_V1',
                                               ranking_rule=scope['ranking_rule'], records=selected))
    csv_write(BASE / 'SELECTED_TOP9.csv', selected)
    pins = []
    for name in ('ALL2289_GEOMETRY.json', 'ALL2289_GEOMETRY.csv', 'SELECTED_TOP9.json', 'SELECTED_TOP9.csv'):
        raw = (BASE / name).read_bytes()
        pins.append({'path': str((BASE / name).relative_to(WORKSPACE)), 'bytes': len(raw), 'sha256': sha(raw)})
    assert sum(pin['bytes'] for pin in pins) <= scope['execution_limits']['output_bytes']
    receipt = dict(common, status='PASS_ONCE_DC_UNTOUCHED_EXPOSED_COREMAX_SELECTION', outputs=pins,
                   CPU_seconds=time.process_time() - start_cpu, wall_seconds=time.monotonic() - start_wall,
                   maximum_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   selection_ranking_executions=1, whole_power_cells_decoded=0)
    write_json(BASE / 'EXECUTION_RECEIPT.json', receipt)
    print(json.dumps({'status': receipt['status'], 'counts': counts, 'target_summary': target_summaries}))


if __name__ == '__main__':
    main()
