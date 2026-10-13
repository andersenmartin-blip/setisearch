"""Independent complete-carrier full-sort QA of the full ON dual aggregation.

No detector/producer imports. Preparation and --check-only read text metadata
only. Numerical map/rank reads require a public-scope hash and root GO.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

BASE = 'seti_burst_full'
PILOT = 'seti_burst_on'
SCANS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
NATIVE, CORE, HALO = 1048576, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DC = (178782208, 179830784, 180879360)
STARTS = (0, 2, 4, 6, 8, 10, 12)
DOMAIN = tuple((n, q) for n in (170, 171, 172) for q in range(256)
               if (n, q) not in ((170, 0), (172, 255)))
PILOT_DOMAIN = {(n, 4+8*k) for n in (170, 171, 172) for k in range(32)}
RAW_FIELDS = ('maximum_robust_box_track_score', 'winning_drift_hz_s', 'winning_drift_grid_index',
              'winning_window_start_row', 'winning_width_channels', 'valid_hypothesis_count')
FAMILIES = ('unrestricted', 'DC_clean')
PILOT_CLASS = 'PILOT_REUSED_UNCHANGED_GEOMETRICALLY_DC_CLEAN'
NEW_CLASS = 'NEW_EXHAUSTIVE_DUAL_MAXIMUM'
AGGREGATE_STATUS = 'COMPLETE_GLOBAL_3_ON_SCANS_766_CORES_EACH_RAW700_SPACED100_TOP3_DUAL_WINNERS'
QA_STATUS = 'PASS_INDEPENDENT_FULL_SORT_9412608_CARRIERS_DUAL_GLOBAL_ON_RANKS'
CSV_ENCODING = 'UTF8; lexicographically sorted exact JSON record keys as header; every cell compact JSON encoded; json.loads roundtrips exact field types and values'
CPU_CAP, WALL_CAP, RAM_CAP = 600, 900, 2147483648


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, relative):
    name = Path(relative)
    path = root/name
    require(not name.is_absolute() and '..' not in name.parts and not path.is_symlink()
            and path.resolve().is_relative_to(root), 'Confined regular path required: '+str(relative))
    return path


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def prepare(root):
    full_path = confined(root, BASE+'/SCOPE.json')
    full = read(full_path)
    require(full['complete_domains_per_ON_scan_after_merge'] == 766 and full['new_maps'] == 2010
            and full['reused_pilot_domains_per_ON_scan'] == 96, 'Frozen full-domain plan differs')
    paths = [BASE+'/aggregate_qa.py', BASE+'/aggregate.py', BASE+'/SCOPE.json', BASE+'/driver.py',
             PILOT+'/SCOPE.json', PILOT+'/driver.py', PILOT+'/qa_results/QA_RECEIPT.json']
    paths.extend(p['path'] for p in full['text_code_pins'])
    paths.extend(p['path'] for p in full['pilot_map_manifests'])
    return {'schema': 'INDEPENDENT_COMPLETE_CARRIER_FULL_ON_DUAL_AGGREGATE_QA_SCOPE_V1',
            'qa_code_sha256': digest(Path(__file__)), 'metadata_input_pins': [pin(root, confined(root, p)) for p in dict.fromkeys(paths)],
            'full_source_scope_path': BASE+'/SCOPE.json', 'full_source_scope_sha256': digest(full_path),
            'aggregate_scope_path': BASE+'/AGGREGATE_SCOPE.json',
            'aggregate_receipt_path': BASE+'/aggregate_results/EXECUTION_RECEIPT.json',
            'aggregate_code_sha256': digest(confined(root, BASE+'/aggregate.py')),
            'source_compacts': full['source_compacts'], 'scan_order': list(SCANS),
            'complete_domain': [{'native_chunk_index': n, 'core_q': q} for n, q in DOMAIN],
            'unchanged_pilot_domain': [{'native_chunk_index': n, 'core_q': q} for n, q in sorted(PILOT_DOMAIN)],
            'counts': {'maps': 2298, 'new_maps': 2010, 'pilot_maps': 288, 'carrier_references': 9412608,
                       'carriers_per_scan': 3137536, 'raw_hypotheses_per_carrier': 2226, 'forced_EMPTY': 9},
            'geometry': {'DC_channels': list(DC), 'window_relative_times_s': [i*TSAMP for i in range(4)],
                         'window_start_rows': list(STARTS), 'drifts': 159, 'widths': [1, 3]},
            'ranking': 'full NumPy lexsort of every finite carrier by score descending then absolute reference channel ascending; independently per ON and winner family',
            'spacing': 'greedy reject inclusive reference-channel distance<=3; exactTOP700 suffices because100th pick occurs by raw rank694',
            'CSV_encoding': CSV_ENCODING,
            'runtime': {'numpy': '2.3.5'}, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'output_budget_bytes': 16*1024**2,
            'admission': 'Root GO separately authenticates completed aggregate scope and receipt hashes, this public prospective QA scope/code, and the public freeze commit before any map or rank payload read.',
            'source_power_decoding': False, 'new_grid_score_evaluation': False, 'detector_or_producer_import': False,
            'interpretation': 'Full saved-maxima sorting and independent geometry/census audit; numerical source/grid validity belongs to separate producer/source QA. Reference separation is descriptive; no calibrated SNR/FAP, physical independence, new observation or qualified SETI detection.',
            'preparation_queries': {'map_arrays': 0, 'rank_payloads': 0, 'source_float_values': 0, 'new_hypothesis_scores': 0}}


def run(root, qascope, aggregate_scope, aggregate_receipt, out, admission):
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    import numpy as np
    require(np.__version__ == '2.3.5', 'Exact NumPy2.3.5 required')
    authenticated, mismatches = {}, []
    checks = 0
    def checked(declared):
        path = confined(root, declared['path'])
        if declared['path'] in authenticated:
            require(authenticated[declared['path']] == declared, 'Inconsistent pin declaration')
        else:
            require(pin(root, path) == declared, 'Byte authentication failed: '+declared['path'])
            authenticated[declared['path']] = declared
        return path
    def equal(actual, expected, label, array=False):
        nonlocal checks
        checks += 1
        ok = np.array_equal(actual, expected, equal_nan=True) if array else actual == expected
        if not ok:
            mismatches.append(label)
    for declared in qascope['metadata_input_pins']+aggregate_scope['input_pins']:
        checked(declared)
    require(aggregate_scope['scan_order'] == list(SCANS) and aggregate_scope['maps_per_scan'] == 766
            and aggregate_scope['total_maps'] == 2298 and aggregate_scope['CSV_encoding'] == CSV_ENCODING,
            'Frozen aggregate domain/CSV protocol differs')
    require(aggregate_scope['raw_top_limit'] == 700 and aggregate_scope['spaced_top_limit'] == 100
            and aggregate_scope['spacing_reject_distance_channels_inclusive'] == 3
            and aggregate_scope['spacing_sufficiency_bound'] == 694, 'Frozen prefix/spacing bound differs')
    require(aggregate_scope['source_compacts'] == qascope['source_compacts'], 'Source declarations changed')
    full = read(checked(next(p for p in qascope['metadata_input_pins'] if p['path'] == qascope['full_source_scope_path'])))
    headers, source_keys = {}, set()
    midpoint = read(confined(root, 'burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'))
    adjacent = read(confined(root, 'burst_previous/analysis/s2017_next_native/source_manifest_v2.json'))
    for source in qascope['source_compacts']:
        scan, native = source['scan_id'], source['native_chunk_index']
        require(scan in SCANS and native in (170, 171, 172) and (scan, native) not in source_keys, 'Source census/ON identity differs')
        source_keys.add((scan, native))
        require(source['original_acquisition_role'] == 'ON' and source['primary_target'] == 'HIP98505'
                and source['shape'] == [16, 1, NATIVE] and source['source_channel0'] == native*NATIVE,
                'Original compact role/shape/channel origin differs')
        checked({k: source[k] for k in ('path', 'bytes', 'sha256')})
        original = next(s for s in midpoint['sources'] if s['label'] == scan)
        item = original if native == 171 else next(s for s in adjacent['by_native_chunk'][str(native)]['sources'] if s['label'] == scan)
        header = original['current_header']['data_attributes']
        require(original['role'] == item['role'] == 'on' and item['current_header'] == original['current_header']
                and source['original_header'] == header and source['original_header_full'] == item['current_header']
                and source['original_source_url'] == item['url'] == original['url']
                and source['original_source_etag'] == item['etag'] == original['etag']
                and source['original_source_file_bytes'] == item['source_file_bytes'], 'Immutable original ON metadata differs')
        acquisition = read(confined(root, source['metadata_acquisition_path']))
        decoded = next(row for row in acquisition['decoded_files'] if row['scan_id'] == scan
                       and (native == 171 or row['native_chunk_index'] == native))
        require(source['bytes'] == decoded['bytes'] and source['sha256'] == decoded['file_sha256']
                and source['source_channel0'] == decoded['source_channel0'] and source['shape'] == decoded['shape']
                and source['decoded_rows'] == decoded['decoded_rows']
                and Path(source['path']).name == Path(decoded['array_file']).name,
                'Source declaration differs from authenticated original acquisition metadata')
        require(header['source_name'] == 'HIP98505' and header['fch1']*1e6 == FCH1
                and header['foff']*1e6 == DF and header['tsamp'] == TSAMP and int(header['tstart']) == 57871,
                'Original target/frequency/time convention differs')
        if scan in headers:
            require(headers[scan] == header, 'Across-native scan header differs')
        headers[scan] = header
        require([row['time_row'] for row in source['decoded_rows']] == list(range(16))
                and all(row['decoded_bytes'] == NATIVE*4 for row in source['decoded_rows']), 'Original sixteen decoded-row declarations differ')
    require(source_keys == {(s, n) for s in SCANS for n in (170, 171, 172)}, 'Exactly nine original ON sources required')
    # Independently authenticate pilot identities through their original completed MAPS inventories.
    pilot_original = {}
    for primary in (f'on20170428_epoch{i}_HIP98505' for i in (1, 2, 3)):
        path = PILOT+'/results/'+primary+'/MAPS.json'
        declaration = next(p for p in aggregate_scope['input_pins'] if p['path'] == path)
        manifest = read(checked(declaration))
        require(len(manifest['records']) == 96, 'Pilot96 map identity changed')
        for record in manifest['records']:
            pilot_original[(record['scan_id'], record['native_chunk_index'], record['core_q'])] = record
    records = aggregate_scope['map_records']
    keys = [(record['scan_id'], record['native_chunk_index'], record['core_q']) for record in records]
    require(len(keys) == len(set(keys)) == 2298 and set(keys) == {(s, n, q) for s in SCANS for n, q in DOMAIN}, 'Exact disjoint complete3x766 map census required')
    producer_receipts = {}
    for declaration in aggregate_scope['producer_receipt_pins']:
        receipt = read(checked(declaration))
        require(receipt['original_acquisition_role'] == 'ON' and receipt['primary_target'] == 'HIP98505'
                and receipt['scan_id'] in SCANS and receipt['source_bytes_unchanged'] is True,
                'Completed producer original ON/source identity differs')
        expected_status = ('COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY' if declaration['path'].startswith(PILOT+'/')
                           else 'COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY')
        require(receipt['status'] == expected_status, 'Actual completed producer status differs')
        expected_scope = PILOT+'/SCOPE.json' if declaration['path'].startswith(PILOT+'/') else BASE+'/SCOPE.json'
        expected_driver = PILOT+'/driver.py' if declaration['path'].startswith(PILOT+'/') else BASE+'/driver.py'
        require(receipt['scope_sha256'] == digest(confined(root, expected_scope))
                and receipt['driver_sha256'] == digest(confined(root, expected_driver)), 'Producing scope/code provenance differs')
        expected_sources = [{k: source[k] for k in ('path', 'bytes', 'sha256')}
                            for source in qascope['source_compacts'] if source['scan_id'] == receipt['scan_id']]
        require(receipt['source_compact_pre_and_post_pins'] == expected_sources
                and receipt['original_scan_tstart_mjd'] == headers[receipt['scan_id']]['tstart'],
                'Producer source pins or original scan origin time differ')
        producer_receipts[declaration['path']] = receipt
    require(len(producer_receipts) == 24, 'Exactly three pilot and21 new producer receipts required')
    output_pins = {p['path']: p for p in aggregate_receipt['output_pins']}
    require(len(output_pins) == len(aggregate_receipt['output_pins']), 'Aggregate output pin paths must be unique')
    output_dir = confined(root, BASE+'/aggregate_results')
    actual_output_paths = {p.relative_to(root).as_posix() for p in output_dir.iterdir() if p.is_file()}
    require(all(p.is_file() and not p.is_symlink() for p in output_dir.iterdir())
            and actual_output_paths == set(output_pins)|{qascope['aggregate_receipt_path']},
            'Completed aggregate output directory must exactly match its closed receipt inventory')
    for p in output_pins.values():
        checked(p)
    maps_output = read(checked(output_pins[BASE+'/aggregate_results/MAP_MAXIMA_AND_COUNTS.json']))
    actual_map_audits = {(m['scan_id'], m['native_chunk_index'], m['core_q']): m for m in maps_output['records']}
    require(set(actual_map_audits) == set(keys) and len(maps_output['records']) == 2298, 'Aggregate per-map output census differs')
    def geometry(frequency, drift, width):
        centers = np.empty(4, dtype=np.int64)
        for row in range(4):
            centers[row] = np.rint((frequency-FCH1)/DF + drift*(row*TSAMP)/DF)
        radius = width//2
        intersections = [[abs(int(center)-dc) <= radius for dc in DC] for center in centers]
        touched = [i for i, row in enumerate(intersections) if any(row)]
        return {'rounded_absolute_centers': centers.tolist(),
                'width_box_source_channels_inclusive': [[int(c)-radius, int(c)+radius] for c in centers],
                'frozen_DC_source_channels': list(DC), 'row_indices_intersecting_any_frozen_DC': touched,
                'rows_intersecting_any_frozen_DC': len(touched),
                'touch_counts_by_frozen_DC': {str(dc): sum(row[j] for row in intersections) for j, dc in enumerate(DC)},
                'eligible_DC_untouched': not touched,
                'minimum_DC_width_box_distance_channels': min(abs(int(c)-dc)-radius for c in centers for dc in DC)}
    def point(record, index, family, values):
        prefix = '' if family == 'unrestricted' or record['map_source_class'] == PILOT_CLASS else 'DC_clean_'
        start = int(values[prefix+'winning_window_start_row'][index])
        frequency, drift, width = float(values['frequency_hz_at_window_reference'][index]), float(values[prefix+'winning_drift_hz_s'][index]), int(values[prefix+'winning_width_channels'][index])
        scan = record['scan_id']
        return {'primary_id': 'on20170428_epoch'+str(SCANS.index(scan)+1)+'_HIP98505', 'primary_target': 'HIP98505',
                'scan_id': scan, 'original_acquisition_role': 'ON', 'winner_family': family,
                'native_chunk_index': record['native_chunk_index'], 'core_q': record['core_q'], 'map_id': record['map_id'],
                'carrier_index_in_core': int(index), 'source_reference_channel': int(values['source_reference_channels'][index]),
                'frequency_hz_at_window_reference': frequency, 'window_start_row': start, 'window_length_rows': 4,
                'window_source_rows': list(range(start, start+4)),
                'reference_time_mjd': headers[scan]['tstart']+(start+.5)*TSAMP/86400,
                'drift_grid_index': int(values[prefix+'winning_drift_grid_index'][index]), 'drift_hz_s': drift,
                'width_channels': width, 'score': float(values[prefix+'maximum_robust_box_track_score'][index]),
                'winning_valid_hypothesis_count': int(values[prefix+'valid_hypothesis_count'][index]),
                'map_source_class': record['map_source_class'], 'source_map': {k: record[k] for k in ('path', 'bytes', 'sha256')},
                'normalization': record['normalization'], 'producer_receipt': record['producer_receipt'],
                'source_header': headers[scan], **geometry(frequency, drift, width)}
    def validate_csv(relative, expected):
        path = checked(output_pins[relative])
        with path.open(newline='') as stream:
            reader = csv.reader(stream)
            header = next(reader)
            equal(header, sorted(expected[0]), relative+'/header')
            rows = []
            for row in reader:
                require(len(row) == len(header), 'CSV column cardinality differs')
                rows.append({name: json.loads(cell, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v))) for name, cell in zip(header, row)})
        equal(rows, expected, relative+'/all_fields')
    all_map_audits, global9, per_scan, empty_by_scan = [], [], {}, {}
    grid = np.linspace(-4, 4, 159)
    dtypes = {'maximum_robust_box_track_score': '<f8', 'winning_drift_hz_s': '<f8',
              'winning_drift_grid_index': '<i2', 'winning_window_start_row': '<i2',
              'winning_width_channels': '<i2', 'valid_hypothesis_count': '<i8'}
    for scan in SCANS:
        scan_records = sorted((rec for rec in records if rec['scan_id'] == scan), key=lambda rec: (rec['native_chunk_index'], rec['core_q']))
        length = 766*CORE
        pool = {'source_reference_channels': np.empty(length, dtype=np.int64), 'frequency_hz_at_window_reference': np.empty(length)}
        for family in FAMILIES:
            for field in RAW_FIELDS:
                pool[family+'/'+field] = np.empty(length, dtype=dtypes[field])
        empty_channels, pilot_count = [], 0
        for number, record in enumerate(scan_records):
            native, q = record['native_chunk_index'], record['core_q']
            pilot = (native, q) in PILOT_DOMAIN
            require(record['map_source_class'] == (PILOT_CLASS if pilot else NEW_CLASS)
                    and record['original_acquisition_role'] == 'ON', 'Pilot/complement classification differs')
            if pilot:
                original = pilot_original[scan, native, q]
                equal({k: record[k] for k in original}, original, record['map_id']+'/original_pilot_metadata')
                pilot_count += 1
            source_pin = {k: record[k] for k in ('path', 'bytes', 'sha256')}
            producer = producer_receipts[record['producer_receipt']['path']]
            producer_pins = {p['path']: p for p in producer['output_byte_pins']}
            require(producer_pins.get(source_pin['path']) == source_pin
                    and producer_pins.get(record['normalization']['path']) == record['normalization'], 'Map/norm not bound to original completed producer')
            with np.load(checked(source_pin), allow_pickle=False) as archive:
                values = {name: archive[name] for name in archive.files}
            fields = {'frequency_hz_at_window_reference', 'source_reference_channels', 'drift_grid_hz_s', *RAW_FIELDS}
            if not pilot:
                fields.update('DC_clean_'+field for field in RAW_FIELDS)
            require(set(values) == fields, 'Exact map9/pilot or15/dual field schema required')
            first = native*NATIVE+q*CORE
            channels = np.arange(first, first+CORE, dtype=np.int64)
            equal(values['source_reference_channels'], channels, record['map_id']+'/channels', True)
            equal(values['frequency_hz_at_window_reference'], FCH1+DF*channels, record['map_id']+'/frequencies', True)
            equal(values['drift_grid_hz_s'], grid, record['map_id']+'/grid', True)
            require(values['source_reference_channels'].dtype.str == '<i8' and values['frequency_hz_at_window_reference'].dtype.str == '<f8'
                    and values['drift_grid_hz_s'].dtype.str == '<f8', 'Original coordinate dtypes differ')
            require(record['reference_channel_interval_half_open'] == [first, first+CORE]
                    and record['loaded_channel_interval_half_open'] == [first-HALO, first+CORE+HALO]
                    and record['searched_carriers'] == CORE and record['valid_hypotheses_per_carrier'] == 2226,
                    'Original physical reference/prefix frame interval differs')
            norm = read(checked(record['normalization']))
            require(norm['normalization_unmasked_counts'] == [CORE]*16, 'Full16 unmasked normalization core required')
            if 'normalization_source_channels' in norm:
                equal(norm['normalization_source_channels'], channels.tolist(), record['map_id']+'/normalization_domain')
            else:
                equal(norm['normalization_source_channel_interval_half_open'], [first, first+CORE], record['map_id']+'/normalization_domain')
            for name in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                terms = np.asarray(norm[name], dtype=np.float64)
                require(terms.shape == (16,) and np.isfinite(terms).all(), 'Original full16 row normalization terms required')
                if name in ('row_power_median', 'row_residual_MAD_scale'):
                    require((terms > 0).all(), 'Positive original normalization level/scale required')
            arrays = {}
            for family in FAMILIES:
                prefix = '' if family == 'unrestricted' or pilot else 'DC_clean_'
                arrays[family] = {field: values[prefix+field] for field in RAW_FIELDS}
                require(all(a.shape == (CORE,) and a.dtype.str == dtypes[field] for field, a in arrays[family].items()), 'Original winner vector shape/dtype differs')
            raw, clean = arrays['unrestricted'], arrays['DC_clean']
            require(np.isfinite(raw[RAW_FIELDS[0]]).all() and (raw[RAW_FIELDS[5]] == 2226).all(), 'All2226 raw hypotheses/all4096 finite maxima required')
            expected_empty = np.isin(channels, DC)
            empty = clean[RAW_FIELDS[5]] == 0
            equal(empty, expected_empty, record['map_id']+'/forced_EMPTY_identity', True)
            require(np.isneginf(clean[RAW_FIELDS[0]][empty]).all() and np.isnan(clean[RAW_FIELDS[1]][empty]).all()
                    and all((clean[field][empty] == -1).all() for field in RAW_FIELDS[2:5]), 'Explicit EMPTY sentinels differ')
            finite = ~empty
            require(np.isfinite(clean[RAW_FIELDS[0]][finite]).all()
                    and (clean[RAW_FIELDS[0]][finite] <= raw[RAW_FIELDS[0]][finite]).all(), 'Exact DC clean maximum cannot exceed unrestricted maximum')
            for family, arr in arrays.items():
                mask = np.ones(CORE, dtype=bool) if family == 'unrestricted' else finite
                require(np.isin(arr[RAW_FIELDS[3]][mask], STARTS).all() and np.isin(arr[RAW_FIELDS[4]][mask], (1, 3)).all()
                        and ((arr[RAW_FIELDS[2]][mask] >= 0) & (arr[RAW_FIELDS[2]][mask] < 159)).all(), 'Winner window/width/drift index differs')
                equal(arr[RAW_FIELDS[1]][mask], grid[arr[RAW_FIELDS[2]][mask]], record['map_id']+'/'+family+'/drift_index', True)
            base = (values['frequency_hz_at_window_reference']-FCH1)/DF
            def contacts(arr, mask):
                centers = np.rint(base[mask, None]+arr[RAW_FIELDS[1]][mask, None]*np.asarray([i*TSAMP for i in range(4)])[None, :]/DF).astype(np.int64)
                return (np.abs(centers[:, :, None]-np.asarray(DC)[None, None, :]) <= (arr[RAW_FIELDS[4]][mask]//2)[:, None, None]).any(axis=(1, 2))
            raw_contact = contacts(raw, np.ones(CORE, dtype=bool))
            require(not contacts(clean, finite).any(), 'Every clean winning box must avoid all frozen DC centers')
            if pilot:
                require(not raw_contact.any() and q not in (127, 128), 'Untouched pilot entire family must lie outside affected cores')
            for field in RAW_FIELDS[:5]:
                equal(clean[field][~raw_contact], raw[field][~raw_contact], record['map_id']+'/retained_clean_'+field, True)
            # Independent eligibility census: all seven windows have identical relative-four-row geometry.
            expected_counts = np.full(CORE, 2226, dtype=np.int64)
            near = np.min(np.abs(channels[:, None]-np.asarray(DC)[None, :]), axis=1) <= 80
            if near.any():
                per_window = np.zeros(int(near.sum()), dtype=np.int64)
                for width in (1, 3):
                    eligible = np.ones((159, int(near.sum())), dtype=bool)
                    for row in range(4):
                        centers = np.rint(base[near][None, :]+grid[:, None]*(row*TSAMP)/DF).astype(np.int64)
                        for dc in DC:
                            eligible &= np.abs(centers-dc) > width//2
                    per_window += eligible.sum(axis=0)
                expected_counts[near] = 7*per_window
            equal(clean[RAW_FIELDS[5]], expected_counts, record['map_id']+'/all_admissible_counts', True)
            changed = np.zeros(CORE, dtype=bool)
            for field in RAW_FIELDS[:5]:
                changed |= raw[field] != clean[field]
            maxima = {}
            for family, arr in arrays.items():
                order = np.lexsort((channels, -arr[RAW_FIELDS[0]]))
                maxima[family] = point(record, int(order[0]), family, values)
            expected_audit = {'scan_id': scan, 'native_chunk_index': native, 'core_q': q, 'map_source_class': record['map_source_class'],
                'source_map': source_pin, 'normalization': record['normalization'], 'unrestricted_maximum': maxima['unrestricted'],
                'DC_clean_maximum': maxima['DC_clean'], 'unrestricted_DC_contacting_cached_winners': int(raw_contact.sum()),
                'DC_clean_EMPTY_carriers': int(empty.sum()), 'DC_clean_changed_winner_tuples': int(changed.sum()),
                'DC_clean_valid_hypothesis_records': int(clean[RAW_FIELDS[5]].sum()), 'unrestricted_valid_hypothesis_records': int(raw[RAW_FIELDS[5]].sum())}
            equal(actual_map_audits[scan, native, q], expected_audit, record['map_id']+'/all_audit_fields')
            all_map_audits.append(expected_audit)
            empty_channels.extend(channels[empty].tolist())
            offset = slice(number*CORE, (number+1)*CORE)
            pool['source_reference_channels'][offset] = channels
            pool['frequency_hz_at_window_reference'][offset] = values['frequency_hz_at_window_reference']
            for family, arr in arrays.items():
                for field, array in arr.items():
                    pool[family+'/'+field][offset] = array
            del values, arrays, raw, clean, norm
        require(pilot_count == 96 and sorted(empty_channels) == list(DC), 'Exact96 untouched pilot cores and three EMPTY carriers per scan required')
        equal(np.diff(pool['source_reference_channels']), np.ones(length-1, dtype=np.int64), scan+'/complete_disjoint_contiguous_reference_channels', True)
        empty_by_scan[scan] = empty_channels
        per_scan[scan] = {'maps': 766, 'pilot_maps': pilot_count, 'carrier_references': length, 'EMPTY': len(empty_channels)}
        for family in FAMILIES:
            scores = pool[family+'/'+RAW_FIELDS[0]]
            finite_indices = np.flatnonzero(np.isfinite(scores))
            require(len(finite_indices) == length-(3 if family == 'DC_clean' else 0), 'Complete finite-family carrier cardinality differs')
            # One full global sort, retaining every carrier rather than merging local prefixes.
            full_order = finite_indices[np.lexsort((pool['source_reference_channels'][finite_indices], -scores[finite_indices]))]
            raw_ranked = []
            for rank, pooled_index in enumerate(full_order[:700], 1):
                record_number, local = divmod(int(pooled_index), CORE)
                map_values = {'source_reference_channels': pool['source_reference_channels'][record_number*CORE:(record_number+1)*CORE],
                              'frequency_hz_at_window_reference': pool['frequency_hz_at_window_reference'][record_number*CORE:(record_number+1)*CORE]}
                prefix = '' if family == 'unrestricted' or scan_records[record_number]['map_source_class'] == PILOT_CLASS else 'DC_clean_'
                for field in RAW_FIELDS:
                    map_values[prefix+field] = pool[family+'/'+field][record_number*CORE:(record_number+1)*CORE]
                raw_ranked.append(dict(point(scan_records[record_number], local, family, map_values), rank=rank))
            spaced = []
            for record in raw_ranked:
                if all(abs(record['source_reference_channel']-old['source_reference_channel']) > 3 for old in spaced):
                    spaced.append(dict(record, raw_rank=record['rank'], rank=len(spaced)+1))
                if len(spaced) == 100:
                    break
            require(len(spaced) == 100 and spaced[-1]['raw_rank'] <= 694, 'Exact TOP700/694 greedy-reference-spacing proof differs')
            filename_prefix = 'UNRESTRICTED' if family == 'unrestricted' else 'DC_CLEAN'
            for selection, expected in [('RAW_TOP700', raw_ranked), ('SPACED_TOP100', spaced), ('TOP3', spaced[:3])]:
                relative = BASE+'/aggregate_results/'+scan+'_'+filename_prefix+'_'+selection+'.json'
                actual = read(checked(output_pins[relative]))
                require(actual['scan_id'] == scan and actual['winner_family'] == family and actual['selection'] == selection
                        and actual['maps_merged'] == 766 and actual['finite_carriers_merged'] == len(finite_indices)
                        and actual['reference_epochs_are_window_specific'] is True and actual['physical_signal_sources_deduplicated'] is False
                        and actual['same_HIP98505_scans_pooled'] is False and actual['qualified_SETI_detection'] is False
                        and actual['ranking'] == aggregate_scope['ranking'] and actual['spacing'] == aggregate_scope['spacing'],
                        'Aggregate output interpretation/census differs')
                equal(actual['records'], expected, relative+'/all_tuple_values')
                validate_csv(relative[:-5]+'.csv', expected)
            if family == 'DC_clean':
                global9.extend(spaced[:3])
            per_scan[scan][family+'_finite_carriers'] = len(finite_indices)
            per_scan[scan][family+'_100th_pick_raw_rank'] = spaced[-1]['raw_rank']
            del full_order, finite_indices
        del pool
    expected_counts = {'scans': 3, 'maps': 2298, 'new_maps': 2010, 'pilot_maps_reused': 288,
                       'carrier_references': 9412608, 'DC_clean_EMPTY_carriers': 9,
                       'raw_TOP700_records': 4200, 'spaced_TOP100_records': 600, 'TOP3_records': 18}
    equal(maps_output['records'], all_map_audits, 'all2298_per_map_audit_order_and_values')
    equal(maps_output['counts'], expected_counts, 'global_counts')
    equal(maps_output['DC_EMPTY_channels_by_scan'], empty_by_scan, 'all9_forced_EMPTY_channels')
    validate_csv(BASE+'/aggregate_results/MAP_MAXIMA_AND_COUNTS.csv', all_map_audits)
    selected_pin = output_pins[BASE+'/aggregate_results/SELECTED_CLEAN_TOP9.json']
    selected = read(checked(selected_pin))
    equal(selected['records'], global9, 'selected_clean_TOP9_all_fields')
    require(selected['no_ON_scan_pooling'] is True, 'Separate original ON ranking must be preserved')
    equal(aggregate_receipt['counts'], expected_counts, 'actual_aggregate_receipt_counts')
    for declared in authenticated.values():
        require(pin(root, confined(root, declared['path'])) == declared, 'Input changed during independent global QA')
    result = {'schema': 'INDEPENDENT_FULL_ON_DUAL_AGGREGATE_QA_RECEIPT_V1',
              'status': QA_STATUS if not mismatches else 'FAIL_MISMATCHES_PRESERVED', 'counts': expected_counts,
              'checks': checks, 'mismatch_count': len(mismatches), 'mismatches': mismatches[:100],
              'aggregate_receipt_sha256': admission['aggregate_receipt_sha256'], 'aggregate_scope_sha256': admission['aggregate_scope_sha256'],
              'aggregate_code_sha256': aggregate_scope['aggregate_code_sha256'], 'qa_scope_sha256': admission['qa_scope_sha256'],
              'qa_code_sha256': admission['qa_code_sha256'], 'map_count': 2298, 'totalcarriers': 9412608,
              'selected_clean_TOP9_pin': selected_pin, 'per_scan': per_scan,
              'full_map_census_exact': True, 'pilot288unchanged': True, 'forcedEMPTY': 9,
              'complete_finite_carriers_fullsorted_each_family': True, 'source_H5_byte_pins_authenticated': 9,
              'source_H5_power_arrays_decoded': 0, 'normalization_full16_physical4096_domains_verified': 2298,
              'all_admissible_hypothesis_counts_independently_geometrically_verified': True,
              'producer_or_detector_imported': False, 'protected2016_opened': False, 'new_hypothesis_scores_computed': 0,
              'new_telescope_HTTP': 0, 'context_labels_descriptive_only': True,
              'input_pin_count': len(authenticated), 'full_source_grid_remax_by_this_QA': False,
              'limitations': ['The validity of saved source maxima is inherited from separate producer/source/grid QA; this independent audit fully sorts saved maxima and verifies geometry, census and ranking.',
                              'Reference spacing and per-window epochs do not establish independent physical sources, significance calibration, independent visits or a SETI detection.']}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--scope', default=BASE+'/AGGREGATE_QA_SCOPE.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--go', default=BASE+'/AGGREGATE_QA_GO.json')
    parser.add_argument('--go-sha256')
    parser.add_argument('--out', default=BASE+'/aggregate_qa_results')
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps({'status': 'STATIC_FULL_SORT_QA_CODE_ONLY', 'qa_code_sha256': digest(Path(__file__)),
                          'map_array_reads': 0, 'rank_payload_reads': 0, 'source_float_queries': 0, 'hypothesis_scores_computed': 0}))
        return
    root = args.root.resolve()
    scope_path = confined(root, args.scope)
    if args.prepare:
        scope = prepare(root)
        save(scope_path, scope)
        print(json.dumps({'status': 'PROSPECTIVE_FULL_SORT_QA_SCOPE_PREPARED_NO_ARRAY_OR_RANK_READS', 'scope': pin(root, scope_path)}))
        return
    require(args.scope_sha256 and digest(scope_path) == args.scope_sha256, 'Exact publicly frozen QA scope hash required')
    qascope = read(scope_path)
    code_sha = digest(Path(__file__))
    require(qascope['qa_code_sha256'] == code_sha, 'QA code differs from frozen scope')
    go_path = confined(root, args.go)
    require(args.go_sha256 and digest(go_path) == args.go_sha256, 'Exact reviewed root GO hash required')
    go = read(go_path)
    require(go['status'] == 'GO_INDEPENDENT_FULL_SORT_9412608_CARRIERS_DUAL_GLOBAL_ON_RANKS'
            and go['qa_scope_sha256'] == args.scope_sha256 and go['qa_code_sha256'] == code_sha
            and re.fullmatch('[0-9a-f]{40}', go['public_freeze_commit']), 'Public/root QA admission differs')
    aggregate_scope_path = confined(root, qascope['aggregate_scope_path'])
    aggregate_receipt_path = confined(root, qascope['aggregate_receipt_path'])
    require(digest(aggregate_scope_path) == go['aggregate_scope_sha256'] and digest(aggregate_receipt_path) == go['aggregate_receipt_sha256'], 'Completed aggregate scope/receipt differs from root admission')
    aggregate_scope, aggregate_receipt = read(aggregate_scope_path), read(aggregate_receipt_path)
    require(aggregate_receipt['status'] == AGGREGATE_STATUS and aggregate_receipt['aggregate_scope_sha256'] == go['aggregate_scope_sha256']
            and aggregate_receipt['aggregate_code_sha256'] == aggregate_scope['aggregate_code_sha256'] == qascope['aggregate_code_sha256'],
            'Exact completed aggregate code/scope/receipt required')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(*unused):
        raise TimeoutError('Independent full-sort QA resource cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(WALL_CAP)
    out = confined(root, args.out)
    out.mkdir(parents=True, exist_ok=False)
    started, cpu = time.monotonic(), time.process_time()
    try:
        admission = {'aggregate_receipt_sha256': go['aggregate_receipt_sha256'], 'aggregate_scope_sha256': go['aggregate_scope_sha256'],
                     'qa_scope_sha256': args.scope_sha256, 'qa_code_sha256': code_sha}
        result = run(root, qascope, aggregate_scope, aggregate_receipt, out, admission)
        require(digest(scope_path) == args.scope_sha256 and digest(Path(__file__)) == code_sha and digest(go_path) == args.go_sha256
                and digest(aggregate_scope_path) == go['aggregate_scope_sha256'] and digest(aggregate_receipt_path) == go['aggregate_receipt_sha256'],
                'Admitted code/scope/GO/aggregate changed during QA')
        result.update({'CPU_seconds': time.process_time()-cpu, 'wall_seconds': time.monotonic()-started,
                       'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                       'runtime': {'numpy': importlib.metadata.version('numpy')}, 'public_freeze_commit': go['public_freeze_commit']})
        require(result['CPU_seconds'] <= CPU_CAP and result['wall_seconds'] <= WALL_CAP and result['peak_RSS_bytes'] <= RAM_CAP, 'Measured QA caps exceeded')
        save(out/'QA_RECEIPT.json', result)
        require((out/'QA_RECEIPT.json').stat().st_size <= qascope['output_budget_bytes'], 'QA output budget exceeded')
        print(json.dumps(result))
        require(not result['mismatch_count'], 'Independent full-sort QA mismatches preserved')
    except BaseException as exc:
        if not (out/'QA_RECEIPT.json').exists():
            save(out/'FAILURE.json', {'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'type': type(exc).__name__, 'failure': str(exc),
                                     'qa_scope_sha256': args.scope_sha256, 'qa_code_sha256': code_sha})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
