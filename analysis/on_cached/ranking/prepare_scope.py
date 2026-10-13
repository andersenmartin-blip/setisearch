#!/usr/bin/env python3
"""Freeze metadata and NPY headers; never decode map score payloads."""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile
from numpy.lib import format

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
SCAN_IDS = ['epoch1_on', 'epoch2_on', 'epoch3_on']
EXPECTED = {'frequency_hz_at_tref.npy': ((4096,), '<f8'),
            'maximum_robust_box_track_score.npy': ((4096,), '<f8'),
            'winning_drift_hz_s.npy': ((4096,), '<f8'),
            'winning_width_channels.npy': ((4096,), '<i2'),
            'valid_hypothesis_count.npy': ((4096,), '<i8'),
            'source_reference_channels.npy': ((4096,), '<i8'),
            'drift_grid_hz_s.npy': ((785,), '<f8')}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


inventory_path = ROOT / 'on_cached/feasibility/ON_RESULTS_RESTORATION_RECEIPT.json'
inventory = json.loads(inventory_path.read_text())
central_source_path = ROOT / 'on_cached/on_results/central/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
adjacent_source_path = ROOT / 'on_cached/on_results/adjacent/analysis/s2017_next_native/source_manifest_v2.json'
central_source, adjacent_source = json.loads(central_source_path.read_text()), json.loads(adjacent_source_path.read_text())
headers = {s['label']: s['current_header']['data_attributes'] for s in central_source['sources']}
for native in ('170', '172'):
    for s in adjacent_source['by_native_chunk'][native]['sources']:
        h = s['current_header']['data_attributes']
        for field in ('tstart', 'tsamp', 'fch1', 'foff', 'source_name'):
            assert h[field] == headers[s['label']][field]
anchor = min(h['tstart'] for h in headers.values())
driver_paths = [ROOT / 'on_cached/on_results/central/analysis/new_visit_recovery/driver.py',
                ROOT / 'on_cached/on_results/central/analysis/s2017_full_band/driver.py',
                ROOT / 'on_cached/on_results/adjacent/analysis/s2017_next_native/search/driver.py',
                ROOT / 'on_cached/on_results/adjacent/analysis/s2017_next_native/boundaries/driver.py']
for path in driver_paths:
    text = path.read_text()
    assert 'search_scan(' in text and 'np.arange(16)' in text and '785' in text
groups = []
for scan_id in SCAN_IDS:
    h = headers[scan_id]
    assert h['source_name'] == 'HIP98505' and h['tsamp'] == 18.253611008
    original_times = [float(r * h['tsamp']) for r in range(16)]
    reference_seconds = float((h['tstart'] - anchor) * 86400.0 + .5 * h['tsamp'])
    reference_mjd = float(anchor + reference_seconds / 86400.0)
    maps, seen = [], set()
    for item in inventory['map_inventory']:
        if item['scan_id'] != scan_id:
            continue
        native, q = item['native_chunk_index'], item['core_q']
        assert (native, q) not in seen
        seen.add((native, q))
        expected_interval = [native * 1048576 + q * 4096, native * 1048576 + (q + 1) * 4096]
        assert item['reference_channel_interval_half_open'] == expected_interval
        assert item['searched_carriers'] == 4096 and item['valid_hypotheses_per_carrier'] == 1570
        map_path = ROOT / item['map_pin']['path']
        assert map_path.stat().st_size == item['map_pin']['bytes']
        with zipfile.ZipFile(map_path) as archive:
            assert set(archive.namelist()) == set(EXPECTED)
            for name, (wanted_shape, wanted_dtype) in EXPECTED.items():
                with archive.open(name) as stream:
                    version = format.read_magic(stream)
                    shape, fortran, dtype = {(1, 0): format.read_array_header_1_0,
                                             (2, 0): format.read_array_header_2_0}[version](stream)
                assert shape == wanted_shape and dtype.str == wanted_dtype and not fortran
        normal_path = ROOT / item['normalization_pin']['path']
        assert pin(normal_path) == item['normalization_pin']
        maps.append(dict(item, canonical_map_id=f'{scan_id}_native{native}_q{q:03d}'))
    wanted = {(170, q) for q in range(1, 256)} | {(171, q) for q in range(256)} | {(172, q) for q in range(255)}
    assert seen == wanted and len(maps) == 766
    groups.append({'primary_scan_id': scan_id, 'scan_id': scan_id, 'primary_target': 'HIP98505',
                   'original_acquisition_role': 'ON', 'origin_tstart_mjd': h['tstart'],
                   'reference_time_mjd': reference_mjd, 'reference_seconds_from_anchor': reference_seconds,
                   'MJD_anchor': anchor, 'original_origin_row_times_from_reference_s': original_times,
                   'map_count': len(maps), 'maps': maps})
scope = {'schema': 'SETI_PROSPECTIVE_HIP98505_ON_CACHED_WINNER_SELECTION_V1', 'date': '2026-10-13',
         'goal': 'Select DC-untouched cached carrier winners globally within each original HIP98505 ON scan; no new detector scoring.',
         'groups': groups, 'primary_scan_ids': SCAN_IDS,
         'restoration_receipt_pin': pin(inventory_path),
         'source_header_manifest_pins': [pin(central_source_path), pin(adjacent_source_path)],
         'original_adapter_pins': [pin(p) for p in driver_paths],
         'producer_pin': pin(BASE / 'select_streaming.py'),
         'constants': {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                       'tsamp_s': 18.253611008, 'rows': 16, 'core_channels': 4096,
                       'fine_channels_per_native': 1048576,
                       'DC_channels': [178782208, 179830784, 180879360]},
         'timing_proof': 'All four actual historical ON adapters directly call search_scan with dt=np.arange(16)*TSAMP and785 drifts,widths1/3. Their fixed-profile reference is (origin.tstart-anchor)*86400+0.5*TSAMP. The generic shared-reference search_cadence is not invoked.',
         'center_rule': 'np.rint((frequency_hz_at_tref-fch1_hz)/df_hz+winning_drift_hz_s*original_origin_row_times_from_reference_s/df_hz); complete absolute source channel rounded before offsets.',
         'DC_rule': 'Eligible iff none of16 inclusive center +/- width//2 boxes contacts source channels178782208,179830784,180879360; cached widths1/3 unchanged.',
         'rank_rule': 'Per original ON scan: score descending,frequency ascending,drift ascending,width ascending,native ascending,q ascending,carrier index ascending. Exact ties without epsilon.',
         'streaming_rule': 'Process one pinned map at a time, inspect all4096 cached winners and preserve exact best700 eligible records in a heap.',
         'separation_rule': 'Traverse rawTOP700 once; keep up to100 reference channels separated by more than3 channels from all earlier choices; finalTOP3 is first3.',
         'prefix_proof': 'Each reference channel is unique per primary scan. Each prior selected channel blocks at most7 distinct carriers including itself. The100th separated choice therefore occurs by raw rank694 if at least694 eligible carriers exist. Retaining700 is sufficient. Preserve partial/EMPTY outputs otherwise.',
         'expected_counts': {'maps': 2298, 'maps_per_ON': 766, 'carriers_per_map': 4096,
                             'cached_carriers_per_ON': 3137536, 'cached_carriers_total': 9412608},
         'NPZ_headers': {k: {'shape': list(v[0]), 'dtype': v[1]} for k, v in EXPECTED.items()},
         'metadata_preparation': {'map_headers_checked': 2298, 'map_payload_arrays_decoded': 0,
                                  'normalization_files_hash_verified': 2298, 'new_selection_metrics': 0},
         'outputs': ['per-ON RESULT.json containing rawTOP700/rawTOP100/separatedTOP100/TOP3 and per-core counts/maxima',
                     'corresponding CSV lists and execution receipts', 'global SELECTED_TOP9.json/CSV and aggregation receipt'],
         'limits': {'CPU_seconds_per_job': 600, 'wall_seconds_per_job': 900,
                    'RAM_bytes_per_job': 2147483648, 'output_bytes_per_job': 6291456,
                    'max_parallel_jobs': 2, 'DKK': 0, 'new_telescope_HTTP': 0,
                    'new_detector_scores': 0, 'rerun_or_overwrite': False},
         'interpretation_limits': ['Prospective exploratory selection of already exposed ON winner paths; no fresh observation or frequency coverage.',
              'One ON scan can supply a retained track even without recurrence. ON labels and targetHIP98505 are unchanged.',
              'A contaminated cached winning hypothesis may conceal clean nonwinning drift/width alternatives; those are not reconstructed.',
              'Reference-channel separation does not establish distinct physical sources. Raw and separated TOP100 are different descriptive lists.',
              'No calibratedSNR,FAP,source origin,OFF veto,flux,EIRP or sensitivity result is established.',
              'Original A/B FAIL_CLOSED,protected2016 holdouts and closed2019 boundaries remain unchanged.'],
         'later_context_contract': 'Selected records preserve reference MJD,origin scan,origin.tstart and exact own row-time vector. Any context scan uses (context.tstart-origin.tstart)*86400+original own vector, with no track refit. Deduplicate raw and normalized geometry separately.'}
path = BASE / 'scope.json'
assert not path.exists(), 'Preserve prospective scope'
raw = (json.dumps(scope, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
path.write_bytes(raw)
compressed = gzip.compress(raw, compresslevel=9, mtime=0)
(BASE / 'scope.json.gz').write_bytes(compressed)
assert gzip.decompress(compressed) == raw
print(json.dumps({'status': 'PREPARED_METADATA_AND_HEADERS_ONLY', 'scope_sha256': sha(raw),
                  'compressed_scope_sha256': sha(compressed), 'producer_sha256': scope['producer_pin']['sha256'],
                  'scope_bytes': len(raw), 'compressed_bytes': len(compressed), 'maps': 2298}))
