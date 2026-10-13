"""Prospective global merge of three separately ranked ON burst searches.

Import/preflight/preparation do not open numerical arrays. Execution reads the
completed cached maps only after exact aggregate-scope/root-GO admission. It
never reruns the window, width, drift, preprocessing or DC-constrained search.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import heapq
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode = True
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
BASE, PILOT = 'seti_burst_full', 'seti_burst_on'
SCANS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
PILOT_JOBS = tuple(f'on20170428_epoch{j}_HIP98505' for j in (1, 2, 3))
SHARDS = tuple(f'full20170428_epoch{j}_HIP98505_shard{k:02d}' for j in (1, 2, 3) for k in range(7))
COUNT, CORE, HALO = 1048576, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DOMAINS = tuple((n, q) for n in (170, 171, 172) for q in range(256)
                if (n, q) not in ((170, 0), (172, 255)))
DC = tuple(n * COUNT + COUNT // 2 for n in (170, 171, 172))
RAW_FIELDS = ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_drift_grid_index',
              'winning_window_start_row', 'winning_width_channels', 'valid_hypothesis_count')
FAMILIES = ('unrestricted', 'DC_clean')
TOP_KEEP, SPACED_KEEP, SPACING = 700, 100, 3
SPACING_SUFFICIENCY_BOUND = (2 * SPACING + 1) * (SPACED_KEEP - 1) + 1
CPU_CAP, WALL_CAP, RAM_CAP = 300, 600, 2 * 1024**3
STATUS = 'COMPLETE_GLOBAL_3_ON_SCANS_766_CORES_EACH_RAW700_SPACED100_TOP3_DUAL_WINNERS'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, name):
    name = Path(name)
    path = root / name
    require(not name.is_absolute() and '..' not in name.parts and not path.is_symlink() and
            path.resolve().is_relative_to(root), 'Confined ordinary relative path required')
    return path


def pin(root, path):
    return {'path': Path(path).relative_to(root).as_posix(), 'bytes': Path(path).stat().st_size,
            'sha256': digest(path)}


def save(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def save_csv(path, records):
    require(records and all(set(record) == set(records[0]) for record in records), 'Homogeneous CSV record fields required')
    fields = sorted(records[0])
    with Path(path).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(fields)
        for record in records:
            writer.writerow([json.dumps(record[field], separators=(',', ':'), ensure_ascii=False, allow_nan=False)
                             for field in fields])
        stream.flush()
        os.fsync(stream.fileno())


def prepare(root, extra_pins):
    full_scope_path = BASE + '/SCOPE.json'
    scope = read(root / full_scope_path)
    require(len(DOMAINS) == 766 and SPACING_SUFFICIENCY_BOUND == 694 and TOP_KEEP >= 694,
            'Prospective family/greedy spacing bound differs')
    require(set(scope['jobs']) == set(SHARDS) and scope['fch1_hz'] == FCH1 and
            scope['df_hz'] == DF and scope['tsamp_s'] == TSAMP,
            'Actual full producer21-shard source/frequency/time contract differs')
    inputs = [BASE + '/aggregate.py', full_scope_path, BASE + '/driver.py', PILOT + '/SCOPE.json',
              PILOT + '/qa_results/QA_RECEIPT.json', *extra_pins]
    pilot_qa = read(root / PILOT / 'qa_results/QA_RECEIPT.json')
    require(pilot_qa['status'] == 'PASS288_ON_BURST4_MAPS1170_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN',
            'Exact original completed pilot QA required')
    maps, receipt_pins = [], []
    for source_class, jobs in (('PILOT_REUSED_UNCHANGED_GEOMETRICALLY_DC_CLEAN', PILOT_JOBS),
                               ('NEW_EXHAUSTIVE_DUAL_MAXIMUM', SHARDS)):
        prefix = PILOT if source_class.startswith('PILOT') else BASE
        for job in jobs:
            folder = prefix + '/results/' + job
            receipt_path = folder + '/EXECUTION_RECEIPT.json'
            receipt = read(root / receipt_path)
            expected_status = ('COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY' if prefix == PILOT else
                               'COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY')
            expected_count = 96 if prefix == PILOT or not job.endswith('shard06') else 94
            require(receipt['status'] == expected_status and receipt['counts']['maps'] == expected_count,
                    'All three pilot and21 new producer receipts must be complete')
            expected_scope = PILOT + '/SCOPE.json' if prefix == PILOT else full_scope_path
            require(receipt['scope_sha256'] == digest(root / expected_scope) and
                    receipt['driver_sha256'] == digest(root / prefix / 'driver.py'), 'Actual completed producer/scope pin differs')
            if prefix == PILOT:
                require(receipt['counts']['maps'] == 96 and
                        pilot_qa['primary_receipt_sha256s'][job] == digest(root / receipt_path) and
                        receipt['DC_geometry_counts']['DC_contacting_cached_winner_carriers'] == 0,
                        'Reused pilot must have passed exact all-carrier DC geometry QA')
            receipt_pin = pin(root, root / receipt_path)
            receipt_pins.append(receipt_pin)
            manifest_path = folder + '/MAPS.json'
            output_pins = {p['path']: p for p in receipt['output_byte_pins']}
            require(output_pins.get(manifest_path) == pin(root, root / manifest_path), 'Producer MAPS metadata not authenticated')
            manifest = read(root / manifest_path)
            require(len(manifest['records']) == receipt['counts']['maps'], 'Producer MAPS count differs')
            if prefix == PILOT:
                declared_manifest = next(p for p in scope['pilot_map_manifests'] if p['path'] == manifest_path)
                require(declared_manifest == pin(root, root / manifest_path), 'Prospectively frozen pilot MAPS pin differs')
            else:
                declared_domains = {(d['native_chunk_index'], d['core_q']) for d in scope['jobs'][job]['domains']}
                actual_domains = {(m['native_chunk_index'], m['core_q']) for m in manifest['records']}
                require(actual_domains == declared_domains and len(actual_domains) == expected_count and
                        manifest['scan_id'] == scope['jobs'][job]['scan_id'], 'Completed shard domains/original ON scan differ')
            inputs += [receipt_path, manifest_path]
            for original in manifest['records']:
                scan, native, q = (original[k] for k in ('scan_id', 'native_chunk_index', 'core_q'))
                require(scan in SCANS and original['original_acquisition_role'] == 'ON' and (native, q) in DOMAINS,
                        'Original ON source identity or admitted complete core differs')
                require(original['reference_channel_interval_half_open'] == [native * COUNT + q * CORE, native * COUNT + (q + 1) * CORE],
                        'Map reference source-channel interval differs')
                require(original['loaded_channel_interval_half_open'] == [native * COUNT + q * CORE - HALO,
                                                                          native * COUNT + (q + 1) * CORE + HALO],
                        'Map unchanged full16 normalization crop interval differs')
                require(output_pins.get(original['path']) == {k: original[k] for k in ('path', 'bytes', 'sha256')} and
                        output_pins.get(original['normalization']['path']) == original['normalization'],
                        'Map or full16 normalization not bound to actual producer receipt')
                maps.append({**original, 'map_source_class': source_class, 'producer_receipt': receipt_pin})
    keys = [(m['scan_id'], m['native_chunk_index'], m['core_q']) for m in maps]
    require(len(keys) == len(set(keys)) == 3 * 766 and
            set(keys) == {(s, n, q) for s in SCANS for n, q in DOMAINS}, 'Exact disjoint3x766 full-core union required')
    maps.sort(key=lambda m: (SCANS.index(m['scan_id']), m['native_chunk_index'], m['core_q']))
    return {'schema': 'SETI_FULL_ON_BURST4_DUAL_GLOBAL_MERGE_SCOPE_V1',
            'status': 'PREPARED_FROM24_ACTUAL_COMPLETE_MAP_PRODUCERS',
            'aggregate_code_sha256': digest(Path(__file__)), 'full_producer_scope': full_scope_path,
            'full_producer_scope_sha256': digest(root / full_scope_path),
            'input_pins': [pin(root, root / name) for name in dict.fromkeys(inputs)],
            'map_records': maps, 'producer_receipt_pins': receipt_pins,
            'scan_order': list(SCANS), 'source_compacts': scope['source_compacts'],
            'maps_per_scan': 766, 'total_maps': 2298, 'new_dual_maps': 2010, 'pilot_maps_reused': 288,
            'carriers_per_scan': 766 * CORE, 'total_carriers': 3 * 766 * CORE,
            'families': list(FAMILIES), 'raw_top_limit': TOP_KEEP, 'spaced_top_limit': SPACED_KEEP,
            'spacing_reject_distance_channels_inclusive': SPACING,
            'spacing_sufficiency_bound': SPACING_SUFFICIENCY_BOUND,
            'ranking': 'finite cached winner score descending, then integer absolute source reference channel ascending; scans separate',
            'spacing': 'greedy suppress reference channels within +/-3 inclusive; window-specific reference epochs stay unchanged; descriptive reference-frequency separation only',
            'CSV_encoding': 'UTF8; lexicographically sorted exact JSON record keys as header; every cell compact JSON encoded; json.loads roundtrips exact field types and values',
            'unrestricted_top_filename_prefix': 'UNRESTRICTED', 'DC_clean_top_filename_prefix': 'DC_CLEAN',
            'required_DC_clean_EMPTY_channels_per_scan': list(DC),
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'output_budget_bytes': 64 * 1024**2, 'new_search_or_fit': False,
            'same_HIP98505_scans_pooled': False, 'new_observation': False,
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}


def geometry(np, frequency, drift, width):
    times = np.arange(4) * TSAMP
    centers = np.rint((frequency - FCH1) / DF + drift * times / DF).astype(np.int64)
    radius = width // 2
    touches = np.abs(centers[:, None] - np.asarray(DC)[None, :]) <= radius
    return {'rounded_absolute_centers': centers.tolist(),
            'width_box_source_channels_inclusive': [[int(c - radius), int(c + radius)] for c in centers],
            'frozen_DC_source_channels': list(DC),
            'row_indices_intersecting_any_frozen_DC': np.flatnonzero(touches.any(axis=1)).tolist(),
            'rows_intersecting_any_frozen_DC': int(touches.any(axis=1).sum()),
            'touch_counts_by_frozen_DC': {str(c): int(touches[:, i].sum()) for i, c in enumerate(DC)},
            'eligible_DC_untouched': bool(not touches.any()),
            'minimum_DC_width_box_distance_channels': int((np.abs(centers[:, None] - np.asarray(DC)[None, :]) - radius).min())}


def winner(np, value, index, family, record, header):
    prefix = '' if family == 'unrestricted' else 'DC_clean_'
    if record['map_source_class'].startswith('PILOT'):
        prefix = ''
    r0 = int(value[prefix + 'winning_window_start_row'][index])
    frequency = float(value['frequency_hz_at_window_reference'][index])
    drift, width = float(value[prefix + 'winning_drift_hz_s'][index]), int(value[prefix + 'winning_width_channels'][index])
    return {'primary_id': PILOT_JOBS[SCANS.index(record['scan_id'])], 'primary_target': 'HIP98505',
            'scan_id': record['scan_id'], 'original_acquisition_role': 'ON', 'winner_family': family,
            'native_chunk_index': record['native_chunk_index'], 'core_q': record['core_q'],
            'map_id': record['map_id'], 'carrier_index_in_core': int(index),
            'source_reference_channel': int(value['source_reference_channels'][index]),
            'frequency_hz_at_window_reference': frequency,
            'window_start_row': r0, 'window_length_rows': 4, 'window_source_rows': list(range(r0, r0 + 4)),
            'reference_time_mjd': header['tstart'] + (r0 + .5) * TSAMP / 86400,
            'drift_grid_index': int(value[prefix + 'winning_drift_grid_index'][index]),
            'drift_hz_s': drift, 'width_channels': width,
            'score': float(value[prefix + 'maximum_robust_box_track_score'][index]),
            'winning_valid_hypothesis_count': int(value[prefix + 'valid_hypothesis_count'][index]),
            'map_source_class': record['map_source_class'],
            'source_map': {k: record[k] for k in ('path', 'bytes', 'sha256')},
            'normalization': record['normalization'], 'producer_receipt': record['producer_receipt'],
            'source_header': header, **geometry(np, frequency, drift, width)}


def run(root, scope, out):
    import numpy as np
    headers = {s['scan_id']: s['original_header'] for s in scope['source_compacts']}
    heaps = {(scan, family): [] for scan in SCANS for family in FAMILIES}
    audits = []
    empty = {scan: [] for scan in SCANS}
    cardinalities = {(scan, family): 0 for scan in SCANS for family in FAMILIES}
    map_pins_verified = []
    for number, record in enumerate(scope['map_records'], 1):
        path = confined(root, record['path'])
        expected_pin = {k: record[k] for k in ('path', 'bytes', 'sha256')}
        require(pin(root, path) == expected_pin and pin(root, root / record['normalization']['path']) == record['normalization'],
                'Saved map/normalization byte pin differs')
        with np.load(path, allow_pickle=False) as archive:
            value = {name: archive[name] for name in archive.files}
        pilot = record['map_source_class'].startswith('PILOT')
        expected = {'frequency_hz_at_window_reference', 'source_reference_channels', 'drift_grid_hz_s', *RAW_FIELDS}
        if not pilot:
            expected.update('DC_clean_' + name for name in RAW_FIELDS)
        require(set(value) == expected, 'Exact cached map dual/pilot field set differs')
        expected_dtypes = {'frequency_hz_at_window_reference': '<f8', 'source_reference_channels': '<i8',
                           'drift_grid_hz_s': '<f8', 'maximum_robust_box_track_score': '<f8',
                           'winning_drift_hz_s': '<f8', 'winning_drift_grid_index': '<i2',
                           'winning_window_start_row': '<i2', 'winning_width_channels': '<i2',
                           'valid_hypothesis_count': '<i8'}
        for field in expected:
            unprefixed = field.removeprefix('DC_clean_')
            shape = (159,) if field == 'drift_grid_hz_s' else (CORE,)
            require(value[field].shape == shape and value[field].dtype.str == expected_dtypes[unprefixed],
                    'Cached map field shape/dtype differs: ' + field)
        first = record['native_chunk_index'] * COUNT + record['core_q'] * CORE
        channels = np.arange(first, first + CORE, dtype=np.int64)
        require(np.array_equal(value['source_reference_channels'], channels) and
                np.array_equal(value['frequency_hz_at_window_reference'], FCH1 + DF * channels) and
                np.array_equal(value['drift_grid_hz_s'], np.linspace(-4, 4, 159)),
                'Frozen frequency/carrier/drift grid differs')
        family_arrays, maxima = {}, {}
        for family in FAMILIES:
            prefix = '' if family == 'unrestricted' or pilot else 'DC_clean_'
            arr = {field: value[prefix + field] for field in RAW_FIELDS}
            require(all(a.shape == (CORE,) for a in arr.values()), 'Cached4096 carrier field shape differs')
            score = arr['maximum_robust_box_track_score']
            finite = np.isfinite(score)
            if family == 'unrestricted':
                require(finite.all() and np.all(arr['valid_hypothesis_count'] == 2226), 'Full raw family carrier maxima/counts differ')
            else:
                missing = ~finite
                require(np.array_equal(missing, np.isin(channels, DC)) and
                        np.all(np.isneginf(score[missing])) and np.isnan(arr['winning_drift_hz_s'][missing]).all() and
                        all(np.all(arr[k][missing] == -1) for k in
                            ('winning_drift_grid_index', 'winning_window_start_row', 'winning_width_channels')) and
                        np.all(arr['valid_hypothesis_count'][missing] == 0), 'DC-clean EMPTY sentinel/carriers differ')
                empty[record['scan_id']].extend(channels[missing].tolist())
                require(np.all(score[finite] <= value['maximum_robust_box_track_score'][finite]),
                        'DC-allowed maximum exceeds unrestricted maximum')
            require(np.isin(arr['winning_window_start_row'][finite], (0, 2, 4, 6, 8, 10, 12)).all() and
                    np.isin(arr['winning_width_channels'][finite], (1, 3)).all() and
                    np.all((arr['winning_drift_grid_index'][finite] >= 0) & (arr['winning_drift_grid_index'][finite] < 159)) and
                    np.array_equal(arr['winning_drift_hz_s'][finite], value['drift_grid_hz_s'][arr['winning_drift_grid_index'][finite]]) and
                    np.all((arr['valid_hypothesis_count'][finite] > 0) & (arr['valid_hypothesis_count'][finite] <= 2226)),
                    'Cached winner window/width/drift/valid-count differs')
            cardinalities[record['scan_id'], family] += int(finite.sum())
            indices = np.flatnonzero(finite)
            order = indices[np.lexsort((channels[indices], -score[indices]))]
            top = order[:TOP_KEEP]
            heap = heaps[record['scan_id'], family]
            for index in top:
                key = (float(score[index]), -int(channels[index]))
                if len(heap) == TOP_KEEP and key <= heap[0][:2]:
                    continue
                item = (*key, winner(np, value, int(index), family, record, headers[record['scan_id']]))
                if len(heap) < TOP_KEEP:
                    heapq.heappush(heap, item)
                else:
                    heapq.heapreplace(heap, item)
            maxima[family] = winner(np, value, int(order[0]), family, record, headers[record['scan_id']])
            family_arrays[family] = arr
        raw, clean = family_arrays['unrestricted'], family_arrays['DC_clean']
        base = (value['frequency_hz_at_window_reference'] - FCH1) / DF
        times = np.arange(4) * TSAMP
        raw_centers = np.rint(base[:, None] + raw['winning_drift_hz_s'][:, None] * times[None, :] / DF).astype(np.int64)
        raw_contact = (np.abs(raw_centers[:, :, None] - np.asarray(DC)[None, None, :]) <=
                       (raw['winning_width_channels'] // 2)[:, None, None]).any(axis=(1, 2))
        finite = np.isfinite(clean['maximum_robust_box_track_score'])
        clean_centers = np.rint(base[finite, None] + clean['winning_drift_hz_s'][finite, None] * times[None, :] / DF).astype(np.int64)
        clean_contact = (np.abs(clean_centers[:, :, None] - np.asarray(DC)[None, None, :]) <=
                         (clean['winning_width_channels'][finite] // 2)[:, None, None]).any()
        require(not clean_contact and (not raw_contact.any() if pilot else True), 'DC-clean box geometry or reused pilot geometry differs')
        changed = np.zeros(CORE, dtype=bool)
        for field in RAW_FIELDS[:5]:
            changed |= raw[field] != clean[field]
        audits.append({'scan_id': record['scan_id'], 'native_chunk_index': record['native_chunk_index'], 'core_q': record['core_q'],
                       'map_source_class': record['map_source_class'], 'source_map': expected_pin,
                       'normalization': record['normalization'], 'unrestricted_maximum': maxima['unrestricted'],
                       'DC_clean_maximum': maxima['DC_clean'],
                       'unrestricted_DC_contacting_cached_winners': int(raw_contact.sum()),
                       'DC_clean_EMPTY_carriers': int((~finite).sum()),
                       'DC_clean_changed_winner_tuples': int(changed.sum()),
                       'DC_clean_valid_hypothesis_records': int(clean['valid_hypothesis_count'].sum()),
                       'unrestricted_valid_hypothesis_records': int(raw['valid_hypothesis_count'].sum())})
        map_pins_verified.append(expected_pin)
        if number % 96 == 0:
            print('MERGED_MAPS', number, '/2298', flush=True)
    ranks, counts = {}, {'scans': 3, 'maps': 2298, 'new_maps': 2010, 'pilot_maps_reused': 288,
                        'carrier_references': 3 * 766 * CORE, 'DC_clean_EMPTY_carriers': 9,
                        'raw_TOP700_records': 3 * 2 * 700, 'spaced_TOP100_records': 3 * 2 * 100, 'TOP3_records': 3 * 2 * 3}
    for scan in SCANS:
        require(sorted(empty[scan]) == list(DC), 'Exactly three frozen-DC EMPTY reference carriers per ON scan required')
        for family in FAMILIES:
            require(cardinalities[scan, family] == 766 * CORE - (3 if family == 'DC_clean' else 0), 'All fullband cached carriers counted')
            records = [item[2] for item in sorted(heaps[scan, family], key=lambda item: (-item[0], -item[1]))]
            require(len(records) == TOP_KEEP and len({r['source_reference_channel'] for r in records}) == TOP_KEEP and
                    all((records[i]['score'], -records[i]['source_reference_channel']) >=
                        (records[i + 1]['score'], -records[i + 1]['source_reference_channel']) for i in range(699)),
                    'Exact global RAW_TOP700 order/uniqueness differs')
            raw_ranked = [{**record, 'rank': i + 1} for i, record in enumerate(records)]
            spaced = []
            for record in raw_ranked:
                if all(abs(record['source_reference_channel'] - r['source_reference_channel']) > SPACING for r in spaced):
                    spaced.append({**record, 'raw_rank': record['rank'], 'rank': len(spaced) + 1})
                    if len(spaced) == SPACED_KEEP:
                        break
            require(len(spaced) == SPACED_KEEP and spaced[-1]['raw_rank'] <= SPACING_SUFFICIENCY_BOUND,
                    'TOP700 does not satisfy proven694 bound for100 greedy spaced reference carriers')
            prefix = 'UNRESTRICTED' if family == 'unrestricted' else 'DC_CLEAN'
            common = {'schema': 'SETI_FULL_ON_BURST4_GLOBAL_RANKS_V1', 'scan_id': scan,
                      'original_acquisition_role': 'ON', 'winner_family': family,
                      'maps_merged': 766, 'finite_carriers_merged': cardinalities[scan, family],
                      'ranking': scope['ranking'], 'spacing': scope['spacing'],
                      'reference_epochs_are_window_specific': True, 'physical_signal_sources_deduplicated': False,
                      'same_HIP98505_scans_pooled': False, 'qualified_SETI_detection': False}
            for suffix, selection in (('RAW_TOP700', raw_ranked), ('SPACED_TOP100', spaced), ('TOP3', spaced[:3])):
                save(out / f'{scan}_{prefix}_{suffix}.json', {**common, 'selection': suffix, 'records': selection})
                save_csv(out / f'{scan}_{prefix}_{suffix}.csv', selection)
            ranks[scan, family] = spaced[:3]
    save(out / 'MAP_MAXIMA_AND_COUNTS.json', {'schema': 'SETI_FULL_ON_BURST4_PER_MAP_DUAL_MAXIMA_V1',
                                            'records': audits, 'counts': counts, 'DC_EMPTY_channels_by_scan': empty})
    save_csv(out / 'MAP_MAXIMA_AND_COUNTS.csv', audits)
    save(out / 'SELECTED_CLEAN_TOP9.json', {'schema': 'SETI_FULL_ON_BURST4_SELECTED_DC_CLEAN_TOP9_V1',
                                           'records': [r for scan in SCANS for r in ranks[scan, 'DC_clean']],
                                           'no_ON_scan_pooling': True, 'selection': 'three greedy-spaced DC-allowed winners per original ON scan'})
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', '--check-only', action='store_true')
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--extra-text-pin', action='append', default=[])
    parser.add_argument('--scope', default=BASE + '/AGGREGATE_SCOPE.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--root-go', default=BASE + '/AGGREGATE_GO.json')
    parser.add_argument('--root-go-sha256')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.preflight:
        require(len(DOMAINS) == 766 and len(SHARDS) == 21 and SPACING_SUFFICIENCY_BOUND == 694, 'Fixed global merge census differs')
        print(json.dumps({'status': 'PASS_STATIC_GLOBAL_MERGE_NO_ARRAY_READS', 'aggregate_code_sha256': digest(Path(__file__)),
                          'cores_per_scan': 766, 'new_shards_required': 21, 'pilot_maps_reused': 288,
                          'TOP700_spaced100_sufficiency_bound': 694, 'numerical_modules_imported': False}))
        return
    scope_path = confined(root, args.scope)
    if args.prepare:
        scope = prepare(root, args.extra_text_pin)
        save(scope_path, scope)
        print(json.dumps({'status': scope['status'], 'aggregate_scope_pin': pin(root, scope_path)}))
        return
    require(args.scope_sha256 and digest(scope_path) == args.scope_sha256, 'Exact frozen aggregate scope hash required')
    scope = read(scope_path)
    require(scope['aggregate_code_sha256'] == digest(Path(__file__)), 'Frozen aggregate code differs')
    for declaration in scope['input_pins']:
        require(pin(root, confined(root, declaration['path'])) == declaration, 'Frozen aggregate metadata/producer pin differs')
    go_path = confined(root, args.root_go)
    require(args.root_go_sha256 and digest(go_path) == args.root_go_sha256, 'Exact reviewed root aggregate GO required')
    go = read(go_path)
    require(go['status'] == 'GO_GLOBAL_MERGE_3_ON_SCANS_766_CORES_EACH' and
            go['aggregate_scope_sha256'] == args.scope_sha256 and go['aggregate_code_sha256'] == scope['aggregate_code_sha256'] and
            re.fullmatch('[0-9a-f]{40}', go['full_public_freeze_commit']), 'Root GO/frozen global merge code/scope differs')
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Global merge wall/CPU cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(WALL_CAP)
    started, cpu0 = time.monotonic(), time.process_time()
    out = root / BASE / 'aggregate_results'
    out.mkdir(exist_ok=False)
    try:
        counts = run(root, scope, out)
        for declaration in scope['input_pins']:
            require(pin(root, root / declaration['path']) == declaration, 'Metadata/producer changed during global merge')
        require(digest(scope_path) == args.scope_sha256 and digest(go_path) == args.root_go_sha256, 'Scope/rootGO changed during merge')
        measured = {'CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
                    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(measured['CPU_seconds'] <= CPU_CAP and measured['wall_seconds'] <= WALL_CAP and measured['peak_RSS_bytes'] <= RAM_CAP,
                'Measured global merge resource cap exceeded')
        require(sum(p.stat().st_size for p in out.iterdir()) <= scope['output_budget_bytes'], 'Global merge output budget exceeded')
        save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_FULL_ON_BURST4_GLOBAL_MERGE_EXECUTION_V1', 'status': STATUS,
             'aggregate_scope_sha256': args.scope_sha256, 'aggregate_code_sha256': scope['aggregate_code_sha256'],
             'root_GO_pin': pin(root, go_path), 'counts': counts, **measured,
             'producer_receipt_pins': scope['producer_receipt_pins'],
             'output_pins': [pin(root, p) for p in sorted(out.iterdir()) if p.is_file()],
             'runtime_versions': {'Python': sys.version.split()[0], 'numpy': importlib.metadata.version('numpy')},
             'full_grid_rerun': False, 'new_fit': False, 'new_observation': False,
             'same_HIP98505_scans_pooled': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False})
    except BaseException as exc:
        if not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY',
                 'aggregate_scope_sha256': args.scope_sha256, 'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
