"""Fixed full-band clean9 context V2 with explicit score/source and global-rank QA gates.

Import/preflight/preparation open text and byte streams only. Numerical execution
requires the frozen CONTEXT_SCOPE hash and an explicit root GO. Frequencies,
drifts, widths, source rows and normalization cores stay fixed; there is no fit,
search, reranking or telescope acquisition in this context stage.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE, PILOT = 'seti_burst_full', 'seti_burst_on'
DETECTOR = 'burst_previous/analysis/new_visit_search/dependencies/detector.py'
MIDPOINT = 'burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT = 'burst_previous/analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'burst_previous/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'burst_previous/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
PINS = {DETECTOR: '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        MIDPOINT: '1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
        ADJACENT: '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
        ACQ171: 'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
        ACQ_ADJACENT: '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e'}
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ORIGINS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
JOBS = ('on20170428_epoch1_HIP98505', 'on20170428_epoch2_HIP98505', 'on20170428_epoch3_HIP98505')
COUNT, CORE, HALO, BAND0 = 1048576, 4096, 4000, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
FROZEN_DC_SOURCE_CHANNELS = tuple(n * COUNT + COUNT // 2 for n in (170, 171, 172))
CPU_CAP, WALL_CAP, MEMORY_CAP = 600, 900, 2 * 1024**3
ATOL, RTOL = 1e-7, 1e-10
RESULT_STATUS = 'COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.resolve().is_relative_to(root), 'Confined relative path required')
    return path


def pin(root, path):
    return {'path': Path(path).relative_to(root).as_posix(), 'bytes': Path(path).stat().st_size,
            'sha256': digest(path)}


def save(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def source_metadata(root):
    """Read full original headers/decoded-row pins; never open HDF5 here."""
    for name, sha in PINS.items():
        require(digest(confined(root, name)) == sha, 'Original metadata/detector pin differs: ' + name)
    midpoint, adjacent = read(root / MIDPOINT), read(root / ADJACENT)
    acquisitions = {171: read(root / ACQ171), 170: read(root / ACQ_ADJACENT),
                    172: read(root / ACQ_ADJACENT)}
    sources, headers = [], {}
    for native in (170, 171, 172):
        manifest = midpoint if native == 171 else adjacent['by_native_chunk'][str(native)]
        require([item['label'] for item in manifest['sources']] == list(SCANS), 'Six source order differs')
        for item in manifest['sources']:
            label = item['label']
            original = next(s for s in midpoint['sources'] if s['label'] == label)
            header = item['current_header']['data_attributes']
            role = 'ON' if label.endswith('_on') else 'OFF'
            require(item['current_header'] == original['current_header'] and
                    item['url'] == original['url'] and item['etag'] == original['etag'] and
                    item['role'].upper() == role and header['fch1'] * 1e6 == FCH1 and
                    header['foff'] * 1e6 == DF and header['tsamp'] == TSAMP,
                    'Across-band full source header/URL/ETag/original acquisition role differs')
            if role == 'ON':
                require(header['source_name'] == 'HIP98505', 'ON target differs')
            headers[label] = header
            candidates = [r for r in acquisitions[native]['decoded_files']
                          if r['scan_id'] == label and (native == 171 or r['native_chunk_index'] == native)]
            require(len(candidates) == 1, 'Unique source compact record required')
            record = candidates[0]
            require(record['shape'] == [16, 1, COUNT] and record['source_channel0'] == native * COUNT and
                    [r['time_row'] for r in record['decoded_rows']] == list(range(16)) and
                    all(r['decoded_bytes'] == COUNT * 4 for r in record['decoded_rows']),
                    'Source compact shape/channel/decoded-row pins differ')
            metadata_path = ACQ171 if native == 171 else ACQ_ADJACENT
            parent = Path('seti_raw') / Path(metadata_path).relative_to('burst_previous').parent
            source_path = (parent / record['array_file']).as_posix()
            confined(root, source_path)
            sources.append({'native_chunk_index': native, 'scan_id': label, 'path': source_path,
                            'bytes': record['bytes'], 'sha256': record['file_sha256'],
                            'shape': record['shape'], 'source_channel0': record['source_channel0'],
                            'decoded_rows': record['decoded_rows'],
                            'original_acquisition_role': role, 'original_header': header,
                            'original_header_full': item['current_header'],
                            'original_source_url': item['url'], 'original_source_etag': item['etag'],
                            'original_source_file_bytes': item['source_file_bytes'],
                            'metadata_acquisition_path': metadata_path})
    previous = -math.inf
    for label in SCANS:
        require(headers[label]['tstart'] >= previous, 'Original cadence chronology/integration gaps differ')
        previous = headers[label]['tstart'] + 16 * TSAMP / 86400
    require(len(sources) == 18, 'Exactly18 complete original source compacts required')
    return sources, headers


PHYSICAL_FIELDS = ('scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
                   'source_reference_channel', 'frequency_hz_at_window_reference',
                   'window_start_row', 'window_length_rows', 'reference_time_mjd',
                   'drift_grid_index', 'drift_hz_s', 'width_channels')
FULL_DOMAINS = tuple((n, q) for n in (170, 171, 172) for q in range(256)
                     if (n, q) not in ((170, 0), (172, 255)))
GLOBAL_STATUS = 'COMPLETE_GLOBAL_3_ON_SCANS_766_CORES_EACH_RAW700_SPACED100_TOP3_DUAL_WINNERS'
GLOBAL_QA_STATUS = 'PASS_INDEPENDENT_FULL_SORT_9412608_CARRIERS_DUAL_GLOBAL_ON_RANKS'
SOURCE_QA_STATUS = 'PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY'


def validate_tracks(tracks, headers):
    require(len(tracks) == 9, 'Exactly nine global DC-allowed selected winners required')
    for index, track in enumerate(tracks):
        origin, rank = ORIGINS[index // 3], index % 3 + 1
        require(track['scan_id'] == origin and track['rank'] == rank and
                track['winner_family'] == 'DC_clean' and track['primary_target'] == 'HIP98505' and
                track['original_acquisition_role'] == 'ON' and track['eligible_DC_untouched'] is True and
                track['frozen_DC_source_channels'] == list(FROZEN_DC_SOURCE_CHANNELS),
                'Saved global clean ON selection order/identity/admissibility differs')
        native, q, carrier = (track[k] for k in ('native_chunk_index', 'core_q', 'carrier_index_in_core'))
        require((native, q) in FULL_DOMAINS and type(carrier) is int and 0 <= carrier < CORE,
                'Selected carrier outside766 complete admitted full-band cores')
        r0 = track['window_start_row']
        require(type(r0) is int and r0 in range(0, 13, 2) and track['window_length_rows'] == 4 and
                track['window_source_rows'] == list(range(r0, r0 + 4)), 'Selected source row window differs')
        channel = native * COUNT + q * CORE + carrier
        require(track['source_reference_channel'] == channel and
                track['frequency_hz_at_window_reference'] == FCH1 + DF * channel and
                track['reference_time_mjd'] == headers[origin]['tstart'] + (r0 + .5) * TSAMP / 86400,
                'Selected own window reference channel/frequency/epoch differs')
        di = track['drift_grid_index']
        require(type(di) is int and 0 <= di <= 158 and
                math.isclose(track['drift_hz_s'], -4 + di * 8 / 158, rel_tol=0, abs_tol=2e-15) and
                track['width_channels'] in (1, 3) and math.isfinite(track['score']),
                'Selected frozen drift/width/score differs')
    return tracks


def prepare(root, qa_code):
    """Bind QA-qualified global clean9 and potential previous-pilot identities."""
    sources, headers = source_metadata(root)
    full_scope_path = BASE + '/SCOPE.json'
    aggregate_scope_path = BASE + '/AGGREGATE_SCOPE.json'
    aggregate_receipt_path = BASE + '/aggregate_results/EXECUTION_RECEIPT.json'
    global_qa_path = BASE + '/aggregate_qa_results/QA_RECEIPT.json'
    source_qa_path = BASE + '/qa_results/QA_RECEIPT.json'
    source_qa_code = BASE + '/qa_v2.py'
    context_code_path = Path(__file__).resolve().relative_to(root).as_posix()
    selection_path = BASE + '/aggregate_results/SELECTED_CLEAN_TOP9.json'
    aggregate = read(root / aggregate_receipt_path)
    global_qa = read(root / global_qa_path)
    require(aggregate['status'] == GLOBAL_STATUS and
            aggregate['aggregate_scope_sha256'] == digest(root / aggregate_scope_path) and
            aggregate['aggregate_code_sha256'] == digest(root / BASE / 'aggregate.py'),
            'Completed exact full-band aggregate required')
    require(global_qa['status'] == GLOBAL_QA_STATUS and
            global_qa['aggregate_receipt_sha256'] == digest(root / aggregate_receipt_path) and
            global_qa['aggregate_scope_sha256'] == digest(root / aggregate_scope_path) and
            global_qa['aggregate_code_sha256'] == digest(root / BASE / 'aggregate.py'),
            'Exact independently verified full-band aggregate required')
    # Ranking QA cannot substitute for source/scalar/independent DC-remax QA.
    source_qa = read(root / source_qa_path)
    full_source_receipts = {Path(p['path']).parent.name: p['sha256']
                            for p in aggregate['producer_receipt_pins']
                            if p['path'].startswith(BASE + '/results/')}
    require(len(full_source_receipts) == 21 and source_qa['status'] == SOURCE_QA_STATUS and
            source_qa['scope_sha256'] == digest(root / full_scope_path) and
            source_qa['driver_sha256'] == digest(root / BASE / 'driver.py') and
            source_qa['qa_sha256'] == digest(root / source_qa_code) and
            source_qa['primary_receipt_sha256s'] == full_source_receipts,
            'Exact independent full dual-score/source QA for all21 completed producer receipts required')
    output_pins = {p['path']: p for p in aggregate['output_pins']}
    require(output_pins.get(selection_path) == pin(root, root / selection_path), 'Global selected-clean9 pin differs')
    tracks = validate_tracks(read(root / selection_path)['records'], headers)
    inputs = [*PINS, full_scope_path, aggregate_scope_path, aggregate_receipt_path, global_qa_path, source_qa_path, source_qa_code,
              selection_path, BASE + '/aggregate.py', context_code_path, qa_code,
              PILOT + '/CONTEXT_SCOPE.json', PILOT + '/context_results/EXECUTION_RECEIPT.json',
              PILOT + '/context_results/CONTEXT_PROFILES.json', PILOT + '/context_qa_results/QA_RECEIPT.json']
    for i, origin in enumerate(ORIGINS):
        name = BASE + '/aggregate_results/' + origin + '_DC_CLEAN_TOP3.json'
        require(output_pins.get(name) == pin(root, root / name) and
                read(root / name)['records'] == tracks[i * 3:(i + 1) * 3], 'Global selected3 per original ON scan differs')
        inputs.append(name)
    for track in tracks:
        for declaration in (track['source_map'], track['normalization'], track['producer_receipt']):
            require(pin(root, root / declaration['path']) == declaration, 'Actual selected map/norm/producer receipt pin differs')
            inputs.append(declaration['path'])
    previous_receipt = read(root / PILOT / 'context_results/EXECUTION_RECEIPT.json')
    require(previous_receipt['status'] == 'COMPLETE_NINE_ON_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS' and
            previous_receipt['context_scope_sha256'] == digest(root / PILOT / 'CONTEXT_SCOPE.json'),
            'Exact completed previous-pilot context required')
    previous_qa = read(root / PILOT / 'context_qa_results/QA_RECEIPT.json')
    require(previous_qa['status'] == 'PASS54_FIXED_SIX_SCAN_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS' and
            previous_qa['context_receipt_sha256'] == digest(root / PILOT / 'context_results/EXECUTION_RECEIPT.json'),
            'Exact full-source QA of previous-pilot contexts required')
    previous = read(root / PILOT / 'context_results/CONTEXT_PROFILES.json')
    previous_output_pins = {p['path']: p for p in previous_receipt['output_pins']}
    previous_matrix_path = PILOT + '/context_results/CONTEXT_PROFILES.json'
    require(previous_output_pins.get(previous_matrix_path) == pin(root, root / previous_matrix_path),
            'Previous-pilot context matrix not authenticated')
    potential_reuse = []
    for track in tracks:
        matches = [old for old in previous['selected_tracks']
                   if all(old[field] == track[field] for field in PHYSICAL_FIELDS)]
        require(len(matches) <= 1, 'Previous physical selected tuple duplicated')
        if not matches:
            continue
        old = matches[0]
        profiles = [p for p in previous['profiles']
                    if p['selected_track']['scan_id'] == old['scan_id'] and p['selected_track']['rank'] == old['rank']]
        require(len(profiles) == 6 and {p['context_scan_id'] for p in profiles} == set(SCANS),
                'Previous potential matching tuple lacks six original context scans')
        for profile in profiles:
            for declaration in (profile['raw_capsule'], profile['raw_normalization_crop'], profile['normalization']):
                require(previous_output_pins.get(declaration['path']) == declaration and
                        pin(root, root / declaration['path']) == declaration, 'Previous potential capsule/crop/normalization pin differs')
                inputs.append(declaration['path'])
        potential_reuse.append({'selected_scan_id': track['scan_id'], 'selected_rank': track['rank'],
                                'previous_selected_track': old, 'previous_profiles': profiles})
    for source in sources:
        require(pin(root, root / source['path']) == {k: source[k] for k in ('path', 'bytes', 'sha256')},
                'Original full compact byte pin differs')
    return {'schema': 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_SCOPE_V2',
            'status': 'PREPARED_FROM_SOURCE_DUAL_QA_AND_GLOBAL_RANK_QA_VERIFIED_DC_CLEAN_TOP9',
            'context_code_path': context_code_path, 'source_QA_receipt': pin(root, root / source_qa_path),
            'global_rank_QA_receipt': pin(root, root / global_qa_path),
            'selected_tracks': tracks, 'source_compacts': sources, 'potential_previous_pilot_reuse': potential_reuse,
            'previous_context_matrix': previous_matrix_path,
            'input_pins': [pin(root, root / name) for name in dict.fromkeys(inputs)],
            'context_code_sha256': digest(Path(__file__)), 'context_qa_code': qa_code,
            'context_qa_code_sha256': digest(root / qa_code),
            'scan_order': list(SCANS), 'primary_origins': list(ORIGINS),
            'context_profiles': 54, 'origin_primary_score_matches': 9,
            'raw_normalization_crop_shape': [16, CORE + 2 * HALO],
            'normalization_core_channels': CORE, 'normalization_halo_channels': HALO,
            'running_median_channels': 501, 'raw_profile_shape': [16, 503],
            'normalization': 'same selected physical4096core in every scan; unchanged full16row preprocessing; no trajectory fit',
            'reference': 'each selected global winner window first integration midpoint; actual source starts and gaps',
            'transport_equation': '(context_tstart-origin_tstart)*86400+(row-window_start_row)*tsamp',
            'rounding': 'np.rint complete absolute carrier+drift*time/DF before crop offset subtraction',
            'fixed_four_row_support': 'same selected local window_start_row:r0+4 in every context scan',
            'full16_support': 'all source rows0..15; unchanged selected carrier/drift/width',
            'four_row_denominator': 'sqrt(4*width)', 'full16_denominator': 'sqrt(16*width)',
            'full16_score_is_primary_score_match': False,
            'frozen_DC_source_channels': list(FROZEN_DC_SOURCE_CHANNELS),
            'context_DC_contact_diagnostic': 'For all16 frozen transported centers, inclusive width box lower<=DC<=upper. Report union source row indices and rows/counts by each DC for full16 and same selected local4 support. Only own selected4 is admitted DC-clean; other supports may contact DC.',
            'DC_contact_score_veto_or_mask_applied': False,
            'score_match_ATOL': ATOL, 'score_match_RTOL': RTOL,
            'reuse_rule': 'Potential physical-tuple matches are metadata only. A previous query is reused iff all six context scans have bit-identical raw normalization crops, full16 normalization, rounded centers, raw503 capsules, time vectors, standardized sums and score-contribution arrays. Otherwise all six are fresh fixed queries.',
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
            'output_budget_bytes': 96 * 1024**2,
            'new_fit_or_detector_grid': False, 'new_observation': False, 'new_reference_frequency_coverage': False,
            'source_acquisition_roles_changed': False, 'mask_or_veto_applied': False,
            'protected2016_data_opened': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'interpretation': 'Global DC-allowed selected tracks from the full cached band, each with its own winning-window epoch. DC-clean admission applies only to each own selected4 box support; other fixed4/full16 contexts may contact DC and their scores remain unchanged with diagnostic flags. Six original scans retain acquisition roles/directions within one historical visit. Fixed long-gap extrapolation has no refit; context does not establish sky origin or independent observing exposure. Validated previous-pilot query reuse does not add a new query or observation.'}


def raw_bits_equal(np, a, b):
    a, b = np.asarray(a), np.asarray(b)
    return a.shape == b.shape and a.dtype.str == b.dtype.str and a.tobytes() == b.tobytes()


def normalization_bits_equal(np, a, b):
    if set(a) != set(b):
        return False
    for field in a:
        dtype = np.int64 if field in ('normalization_unmasked_counts', 'normalization_source_channels') else np.float64
        if not raw_bits_equal(np, np.asarray(a[field], dtype=dtype), np.asarray(b[field], dtype=dtype)):
            return False
    return True


def dc_context_diagnostic(np, centers, width, window_rows):
    radius = width // 2
    lower, upper = centers - radius, centers + radius
    dc = np.asarray(FROZEN_DC_SOURCE_CHANNELS, dtype=np.int64)
    touches = (lower[:, None] <= dc[None, :]) & (dc[None, :] <= upper[:, None])
    selected = np.zeros(16, dtype=bool)
    selected[window_rows] = True
    selected_touches = touches & selected[:, None]
    full_rows = np.flatnonzero(touches.any(axis=1)).tolist()
    selected_rows = np.flatnonzero(selected_touches.any(axis=1)).tolist()
    rows_full_by_dc = {str(channel): np.flatnonzero(touches[:, index]).tolist()
                       for index, channel in enumerate(FROZEN_DC_SOURCE_CHANNELS)}
    rows_four_by_dc = {str(channel): np.flatnonzero(selected_touches[:, index]).tolist()
                       for index, channel in enumerate(FROZEN_DC_SOURCE_CHANNELS)}
    return {'frozen_DC_source_channels': list(FROZEN_DC_SOURCE_CHANNELS),
            'row_width_box_source_channels_inclusive': np.column_stack((lower, upper)).tolist(),
            'row_intersects_each_frozen_DC': touches.tolist(),
            'DC_contact_row_indices_full16': full_rows,
            'DC_contact_row_indices_selected4': selected_rows,
            'DC_contact_rows_by_frozen_DC_full16': rows_full_by_dc,
            'DC_contact_rows_by_frozen_DC_selected4': rows_four_by_dc,
            'DC_contact_counts_by_frozen_DC_full16': {key: len(value) for key, value in rows_full_by_dc.items()},
            'DC_contact_counts_by_frozen_DC_selected4': {key: len(value) for key, value in rows_four_by_dc.items()},
            'DC_contact_count_full16': len(full_rows), 'DC_contact_count_selected4': len(selected_rows),
            'DC_contact_any_full16': bool(full_rows), 'DC_contact_any_selected4': bool(selected_rows),
            'DC_contact_score_veto_or_mask_applied': False}


def run(root, scope, out):
    import numpy as np
    import h5py
    import hdf5plugin
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008),
            'Supported bitshuffle codec unavailable')
    spec = importlib.util.spec_from_file_location('on_burst_fixed_context_detector', root / DETECTOR)
    detector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = detector
    spec.loader.exec_module(detector)
    selected, sources = scope['selected_tracks'], scope['source_compacts']
    headers = {s['scan_id']: s['original_header'] for s in sources}
    rows, cfg = np.arange(16), detector.Config(widths=(1, 3))
    profiles, crops, verified = [], [], []
    reuse_candidates = {(c['selected_scan_id'], c['selected_rank']): c
                        for c in scope['potential_previous_pilot_reuse']}
    for label in SCANS:
        power = np.empty((16, 3 * COUNT), dtype='<f4')
        for source in (s for s in sources if s['scan_id'] == label):
            require(pin(root, root / source['path']) == {k: source[k] for k in ('path', 'bytes', 'sha256')},
                    'Original compact pin differs at execution')
            with h5py.File(root / source['path'], 'r', rdcc_nbytes=8 * 1024**2) as handle:
                data = handle['data']
                require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4' and
                        int(data.attrs['original_source_frequency_chunk_origin']) == source['source_channel0'] and
                        data.attrs['original_source_url'] == source['original_source_url'] and
                        data.attrs['original_source_etag'] == source['original_source_etag'], 'Compact HDF5 provenance differs')
                offset = source['source_channel0'] - BAND0
                for declaration in source['decoded_rows']:
                    values = data[declaration['time_row'], 0, :]
                    require(np.isfinite(values).all() and (values >= 0).all() and
                            hashlib.sha256(values.tobytes()).hexdigest() == declaration['decoded_sha256'],
                            'Full decoded source-row pin differs')
                    power[declaration['time_row'], offset:offset + COUNT] = values
            verified.append({'path': source['path'], 'native_chunk_index': source['native_chunk_index'],
                             'scan_id': label, 'file_sha256': source['sha256'], 'decoded_rows_verified': 16})
        cache = {}
        for track in selected:
            native, q, origin, width = (track[k] for k in ('native_chunk_index', 'core_q', 'scan_id', 'width_channels'))
            core0 = native * COUNT + q * CORE
            crop0, cropstop = core0 - HALO, core0 + CORE + HALO
            require(BAND0 <= crop0 < cropstop <= BAND0 + 3 * COUNT,
                    'Full selected normalization crop leaves authenticated contiguous triplet')
            key = (native, q)
            if key not in cache:
                channels = np.arange(core0, core0 + CORE, dtype=np.int64)
                raw = power[:, crop0 - BAND0:cropstop - BAND0].copy()
                require(raw.shape == (16, 12096), 'Exact full16 raw normalization crop required')
                scan = detector.Scan(label, 'ON' if label.endswith('_on') else 'OFF', raw,
                                     headers[label]['tstart'], TSAMP, FCH1, DF, crop0, channels)
                z, mask, normalization = detector.preprocess(scan, cfg)
                require(mask.all(), 'No context mask is admitted')
                crop_id = f'{label}_native{native}_q{q:03d}'
                crop_path = out / (crop_id + '_raw12096.npz')
                with crop_path.open('xb') as stream:
                    np.savez(stream, raw_power=raw, source_channel0=np.int64(crop0),
                             normalization_source_channels=channels, absolute_time_rows=rows)
                norm_path = out / (crop_id + '_normalization.json')
                save(norm_path, normalization)
                support_sources = [s for s in sources if s['scan_id'] == label and
                                   s['source_channel0'] < cropstop and s['source_channel0'] + COUNT > crop0]
                require(1 <= len(support_sources) <= 2, 'Unique contiguous raw crop source-piece support differs')
                crop_record = {'crop_id': crop_id, 'scan_id': label, 'native_chunk_index': native, 'core_q': q,
                               'source_channel_interval_half_open': [crop0, cropstop],
                               'normalization_source_channel_interval_half_open': [core0, core0 + CORE],
                               'raw_crop': pin(root, crop_path), 'normalization': pin(root, norm_path),
                               'source_support': [{'path': s['path'], 'sha256': s['sha256'],
                                                   'source_channel0': s['source_channel0'],
                                                   'original_decoded_rows': s['decoded_rows']} for s in support_sources]}
                crops.append(crop_record)
                cache[key] = (z, mask, normalization, crop_record, raw)
            z, mask, normalization, crop_record, raw = cache[key]
            if origin == label:
                primary_norm = read(root / track['normalization']['path'])
                compact = dict(normalization)
                require(compact.pop('normalization_source_channels') == list(range(core0, core0 + CORE)),
                        'Frozen core source interval differs')
                compact['normalization_source_channel_interval_half_open'] = [core0, core0 + CORE]
                require(compact == primary_norm, 'Own full16 normalization differs from saved primary')
            r0 = track['window_start_row']
            window_rows = np.arange(r0, r0 + 4)
            # Avoid subtracting rounded window-midpoint MJD; own rows match primary exactly.
            times = ((headers[label]['tstart'] - headers[origin]['tstart']) * 86400 +
                     (rows - r0) * TSAMP)
            base = (track['frequency_hz_at_window_reference'] - FCH1) / DF
            centers = np.rint(base + track['drift_hz_s'] * times / DF).astype(np.int64)
            local = centers - crop0
            require(np.all(local - 251 >= 0) and np.all(local + 251 < CORE + 2 * HALO),
                    'Frozen track lacks full503/filter support within unchanged normalization crop')
            box = local[:, None] + np.arange(-(width // 2), width // 2 + 1)[None, :]
            require(mask[rows[:, None], box].all(), 'Fixed context box unexpectedly masked')
            terms = z[rows[:, None], box].sum(axis=1, dtype=np.float64)
            contribution16 = terms / np.sqrt(16 * width)
            contribution4 = np.zeros(16, dtype=np.float64)
            contribution4[window_rows] = terms[window_rows] / np.sqrt(4 * width)
            score4 = float(terms[window_rows].sum(dtype=np.float64) / np.sqrt(4 * width))
            score16 = float(terms.sum(dtype=np.float64) / np.sqrt(16 * width))
            require(math.isfinite(score4) and math.isfinite(score16), 'Nonfinite fixed score')
            own = origin == label
            dc_diagnostic = dc_context_diagnostic(np, centers, width, window_rows)
            if own:
                require(math.isclose(score4, track['score'], abs_tol=ATOL, rel_tol=RTOL), 'Own saved primary score differs')
                require(not dc_diagnostic['DC_contact_any_selected4'], 'Own DC-allowed selected4 box contacts a frozen DC')
            profile_id = f"{origin}_rank{track['rank']}_{label}"
            capsule = power[rows[:, None], centers[:, None] - BAND0 + np.arange(-251, 252)[None, :]].copy()
            candidate = reuse_candidates.get((origin, track['rank']))
            previous_comparison = None
            if candidate is not None:
                previous_profile = next(p for p in candidate['previous_profiles'] if p['context_scan_id'] == label)
                old_norm = read(root / previous_profile['normalization']['path'])
                with np.load(root / previous_profile['raw_normalization_crop']['path'], allow_pickle=False) as saved:
                    crop_checks = {
                        'raw_normalization_crop_bits': raw_bits_equal(np, raw, saved['raw_power']),
                        'crop_channel0_bits': raw_bits_equal(np, np.int64(crop0), saved['source_channel0']),
                        'normalization_source_channels_bits': raw_bits_equal(np, np.arange(core0, core0 + CORE, dtype=np.int64), saved['normalization_source_channels']),
                        'crop_absolute_time_rows_bits': raw_bits_equal(np, rows, saved['absolute_time_rows'])}
                with np.load(root / previous_profile['raw_capsule']['path'], allow_pickle=False) as saved:
                    capsule_checks = {
                        'raw503_bits': raw_bits_equal(np, capsule, saved['raw_power']),
                        'rounded_centers_bits': raw_bits_equal(np, centers, saved['rounded_absolute_centers']),
                        'time_vector_bits': raw_bits_equal(np, times, saved['times_from_primary_reference_s']),
                        'capsule_absolute_time_rows_bits': raw_bits_equal(np, rows, saved['absolute_time_rows']),
                        'row_standardized_sum_bits': raw_bits_equal(np, terms, saved['row_standardized_box_sum']),
                        'window_rows_bits': raw_bits_equal(np, window_rows, saved['window_source_rows']),
                        'four_row_contribution_bits': raw_bits_equal(np, contribution4, saved['row_four_row_score_contribution']),
                        'full16_contribution_bits': raw_bits_equal(np, contribution16, saved['row_full16_score_contribution'])}
                checks = {**crop_checks, **capsule_checks,
                          'full16_normalization_bits': normalization_bits_equal(np, normalization, old_norm),
                          'four_row_score_bits': raw_bits_equal(np, np.float64(score4), np.float64(previous_profile['fixed_four_row_score'])),
                          'full16_score_bits': raw_bits_equal(np, np.float64(score16), np.float64(previous_profile['fixed_full16_score']))}
                previous_comparison = {'previous_profile_id': previous_profile['profile_id'],
                                       'previous_raw_capsule': previous_profile['raw_capsule'],
                                       'previous_raw_normalization_crop': previous_profile['raw_normalization_crop'],
                                       'previous_normalization': previous_profile['normalization'],
                                       'bit_identity_checks': checks, 'this_scan_all_bits_identical': all(checks.values())}
            capsule_path = out / (profile_id + '_raw503.npz')
            with capsule_path.open('xb') as stream:
                np.savez(stream, raw_power=capsule, rounded_absolute_centers=centers,
                         times_from_primary_reference_s=times, absolute_time_rows=rows,
                         row_standardized_box_sum=terms, window_source_rows=window_rows,
                         row_four_row_score_contribution=contribution4, row_full16_score_contribution=contribution16)
            positive4, positive16 = np.maximum(contribution4, 0), np.maximum(contribution16, 0)
            total4, total16 = float(positive4.sum()), float(positive16.sum())
            dominant4, dominant16 = int(np.argmax(positive4)), int(np.argmax(positive16))
            profiles.append({'profile_id': profile_id, 'selected_track': track,
                             'context_scan_id': label, 'context_target': headers[label]['source_name'],
                             'original_acquisition_role': 'ON' if label.endswith('_on') else 'OFF',
                             'reference_time_mjd': track['reference_time_mjd'],
                             'times_from_primary_reference_s': times.tolist(),
                             'row_midpoint_mjd': [headers[label]['tstart'] + (j + .5) * TSAMP / 86400 for j in range(16)],
                             'rounded_absolute_centers': centers.tolist(),
                             'rounded_center_frequency_hz': (FCH1 + DF * centers).tolist(),
                             'row_standardized_box_sum': terms.tolist(), 'window_source_rows': window_rows.tolist(),
                             'row_four_row_score_contribution': contribution4.tolist(),
                             'row_full16_score_contribution': contribution16.tolist(),
                             'fixed_four_row_score': score4, 'fixed_full16_score': score16,
                             'origin_primary_score': track['score'] if own else None,
                             'origin_primary_score_difference': score4 - track['score'] if own else None,
                             'positive_row_contribution_max_fraction': float(positive4[dominant4] / total4) if total4 else None,
                             'dominant_positive_row': dominant4 if total4 else None,
                             'full16_positive_row_contribution_max_fraction': float(positive16[dominant16] / total16) if total16 else None,
                             'full16_dominant_positive_row': dominant16 if total16 else None,
                             'reused_previous_pilot_fixed_query': False,
                             'previous_pilot_candidate_comparison': previous_comparison,
                             **dc_diagnostic,
                             'normalization_crop_id': crop_record['crop_id'], 'raw_capsule': pin(root, capsule_path),
                             'raw_normalization_crop': crop_record['raw_crop'], 'normalization': crop_record['normalization']})
            print('CONTEXT', profile_id, f'four={score4:.8g}', f'full16={score16:.8g}', flush=True)
        del power, cache
    profiles.sort(key=lambda p: (ORIGINS.index(p['selected_track']['scan_id']),
                                 p['selected_track']['rank'], SCANS.index(p['context_scan_id'])))
    require(len(profiles) == 54 and sum(p['origin_primary_score'] is not None for p in profiles) == 9,
            'Expected54 profiles and9 own primary score matches')
    reuse_summary = []
    for key, candidate in reuse_candidates.items():
        matching = [p for p in profiles if (p['selected_track']['scan_id'], p['selected_track']['rank']) == key]
        require(len(matching) == 6 and {p['context_scan_id'] for p in matching} == set(SCANS), 'Reuse comparison six-scan census differs')
        all_identical = all(p['previous_pilot_candidate_comparison']['this_scan_all_bits_identical'] for p in matching)
        for profile in matching:
            profile['reused_previous_pilot_fixed_query'] = all_identical
        reuse_summary.append({'scan_id': key[0], 'selected_rank': key[1],
                              'previous_selected_track': candidate['previous_selected_track'],
                              'all_six_scans_bits_identical': all_identical,
                              'fixed_queries_reused': 6 if all_identical else 0})
    reused = sum(p['reused_previous_pilot_fixed_query'] for p in profiles)
    matrix = {'schema': 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_PROFILES_V2', 'status': RESULT_STATUS,
              'selected_tracks': selected, 'profiles': profiles, 'normalization_crops': crops,
              'source_compacts': sources, 'source_verification': verified,
              'previous_pilot_reuse': reuse_summary,
              'counts': {'selected_tracks': 9, 'context_profiles': 54, 'origin_score_matches': 9,
                         'source_files_verified': 18, 'source_rows_verified': 288,
                         'raw503_profile_cells': 54 * 16 * 503, 'raw_normalization_crops': len(crops),
                         'raw_normalization_crop_cells': len(crops) * 16 * 12096,
                         'four_row_scores': 54, 'full16_scores': 54, 'row_box_terms': 864,
                         'profiles_computed_this_execution': 54,
                         'previous_pilot_fixed_queries_reused_bit_identical': reused,
                         'new_fixed_context_queries': 54 - reused,
                         'profiles_with_selected4_DC_contact': sum(p['DC_contact_any_selected4'] for p in profiles),
                         'profiles_with_full16_DC_contact': sum(p['DC_contact_any_full16'] for p in profiles),
                         'selected4_DC_contact_rows': sum(p['DC_contact_count_selected4'] for p in profiles),
                         'full16_DC_contact_rows': sum(p['DC_contact_count_full16'] for p in profiles)},
              'selection_after_primary_search': True, 'new_fit_or_detector_grid': False,
              'new_observation': False, 'ON_scan_positions_are_independent_visits': False,
              'source_acquisition_roles_changed': False, 'ON_OFF_veto_applied': False,
              'DC_contact_score_veto_or_mask_applied': False,
              'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
              'interpretation': scope['interpretation']}
    save(out / 'CONTEXT_PROFILES.json', matrix)
    return matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', '--check-only', action='store_true')
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--qa-code', default=BASE + '/context_qa.py')
    parser.add_argument('--scope', default=BASE + '/CONTEXT_SCOPE.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--root-go')
    parser.add_argument('--root-go-sha256')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.preflight:
        sources, _ = source_metadata(root)
        print(json.dumps({'status': 'PASS_TEXT_ONLY_FIXED_FULL_ON_CONTEXT_INTERFACE',
                          'context_code_sha256': digest(Path(__file__)), 'source_compacts_declared': len(sources),
                          'source_rows_declared': 288, 'numerical_modules_imported': False,
                          'source_values_opened': False, 'raw_output_values_opened': False}))
        return
    scope_path = confined(root, args.scope)
    if args.prepare:
        scope = prepare(root, args.qa_code)
        save(scope_path, scope)
        print(json.dumps({'status': scope['status'], 'scope_pin': pin(root, scope_path)}))
        return
    require(args.scope_sha256 and digest(scope_path) == args.scope_sha256, 'Exact prepared context scope hash required')
    scope = read(scope_path)
    require(scope['context_code_sha256'] == digest(Path(__file__)) and
            scope['context_code_path'] == Path(__file__).resolve().relative_to(root).as_posix(),
            'Frozen active context producer path/hash differs')
    checks = [*scope['input_pins'], *[{k: s[k] for k in ('path', 'bytes', 'sha256')} for s in scope['source_compacts']]]
    for expected in checks:
        require(pin(root, confined(root, expected['path'])) == expected, 'Frozen context prerequisite pin differs')
    require(args.root_go and args.root_go_sha256, 'Exact reviewed root context GO required')
    go_path = confined(root, args.root_go)
    require(digest(go_path) == args.root_go_sha256, 'Exact reviewed root context GO hash differs')
    go = read(go_path)
    require(go['status'] == 'GO_FULL_ON_BURST4_FIXED_CONTEXT54' and
            go['context_scope_sha256'] == args.scope_sha256 and
            go['context_code_sha256'] == scope['context_code_sha256'], 'Root context GO/scope/code differs')
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Fixed context wall cap900s reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(WALL_CAP)
    started, cpu0 = time.monotonic(), time.process_time()
    out = root / BASE / 'context_results'
    out.mkdir(exist_ok=False)
    try:
        matrix = run(root, scope, out)
        for expected in checks:
            require(pin(root, root / expected['path']) == expected, 'Frozen input changed during context execution')
        require(digest(scope_path) == args.scope_sha256 and digest(go_path) == args.root_go_sha256,
                'Context scope/rootGO changed during execution')
        import h5py
        measured = {'wall_seconds': time.monotonic() - started, 'CPU_seconds': time.process_time() - cpu0,
                    'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(measured['wall_seconds'] <= WALL_CAP and measured['CPU_seconds'] <= CPU_CAP and
                measured['peak_RSS_bytes'] <= MEMORY_CAP, 'Measured context resource cap exceeded')
        require(sum(p.stat().st_size for p in out.iterdir()) <= scope['output_budget_bytes'], 'Context output budget exceeded')
        save(out / 'EXECUTION_RECEIPT.json', {'schema': 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_EXECUTION_V2',
             'status': matrix['status'], 'context_scope_sha256': args.scope_sha256,
             'context_code_sha256': scope['context_code_sha256'], 'context_code_path': scope['context_code_path'],
             'source_QA_receipt': scope['source_QA_receipt'], 'global_rank_QA_receipt': scope['global_rank_QA_receipt'],
             'root_GO_pin': pin(root, go_path),
             'counts': matrix['counts'], 'origin_score_match_ATOL': ATOL, 'origin_score_match_RTOL': RTOL,
             'runtime_versions': {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
                                  **{n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}},
             **measured, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
             'output_pins': [pin(root, p) for p in sorted(out.iterdir()) if p.is_file()],
             'new_telescope_HTTP_requests': 0, 'new_observation': False, 'new_fit_or_detector_grid': False,
             'source_acquisition_roles_changed': False, 'source_bytes_unchanged': True,
             'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False})
    except BaseException as exc:
        if not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY',
                 'context_scope_sha256': args.scope_sha256, 'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
