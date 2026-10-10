"""One frozen native-band pilot from six authenticated NEW-visit compacts.

Inert stdlib-only import. Geometry is derived from metadata before amplitudes.
The vendored detector is byte-identical to the original detector; this wrapper
calls search_scan directly, never cadence_geometry, classify_hits or OFF veto.
Only an explicit prospective root freeze/admission/GO may enter science().
"""
from __future__ import annotations

import time
MODULE_STARTED = time.monotonic()
import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys

sys.dont_write_bytecode = True

FAMILY = 'radio_visit2019_s31_blc77_native_pilot_20261010'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
CORE, DRIFT_COUNT, WIDTHS = 4096, 785, (1, 3)
DETECTOR_SHA = '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45'
MAX_LIMITS = {'CPU_seconds': 6000, 'wall_seconds': 7200,
              'memory_bytes': 1610612736, 'output_bytes': 134217728,
              'shared_workspace_bytes': 12884901888}
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
META_SCHEMA = 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
META_PASS = 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
ACQ_SCHEMA = 'SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_RESULT_V1'
ACQ_PASS = 'COMPLETE_EXACT_RAW_ROWS_AND_COMPACT_FILES_NO_SIGNAL_DECODE'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, relative):
    p = Path(relative)
    require(type(relative) is str and not p.is_absolute() and p.parts
            and '..' not in p.parts and str(p) == relative and '\\' not in relative,
            'Canonical root-relative path required')
    path = root / p
    require(path.resolve() == path and root in path.parents, 'Symlink/escaped input or output')
    return path


def read_pin(root, pin, json_value=True):
    require(set(pin) == {'path', 'bytes', 'sha256'} and type(pin['bytes']) is int
            and pin['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'Exact finite pin required')
    path = confined(root, pin['path'])
    require(path.is_file() and path.stat().st_size == pin['bytes'], 'Input size differs: ' + pin['path'])
    if json_value:
        require(path.suffix.lower() in ('.json', '.md', '.py'), 'Metadata read cannot open power arrays')
        raw = path.read_bytes()
        require(sha(raw) == pin['sha256'], 'Input SHA differs: ' + pin['path'])
        return json.loads(raw)
    require(digest(path) == pin['sha256'], 'Opaque input SHA differs: ' + pin['path'])
    return path


def derive_geometry(metadata):
    """Pure metadata arithmetic; never opens source files or amplitude arrays."""
    require(metadata['schema'] == META_SCHEMA and metadata['status'] == META_PASS,
            'Actual six-source metadata qualification PASS required')
    require(metadata['metadata_eligibility']['status'] == META_PASS
            and all(check['PASS'] is True for check in metadata['metadata_eligibility']['checks'])
            and metadata['spectral_values_read'] is False and metadata['dataset_value_API_used'] is False,
            'Actual clean metadata-only selection required')
    sources = metadata['sources']
    require(len(sources) == 6 and len({s['source_id'] for s in sources}) == 6,
            'Six unique ordered source identities required')
    grid = None
    starts = []
    for i, s in enumerate(sources):
        a, shape, chunks = s['data_attributes'], s['shape'], s['chunks']
        require(s['ordered_index'] == i + 1 and s['status'] == 'COMPLETE_HEADER_METADATA_ONLY'
                and len(shape) == len(chunks) == 3 and shape[1] == chunks[0] == chunks[1] == 1
                and all(type(x) is int and x > 0 for x in shape + chunks)
                and shape[0] >= 2 and s['dtype_string'] == '<f4', 'Supported actual source geometry required')
        values = [a[k] for k in ('fch1', 'foff', 'tsamp', 'tstart')]
        require(all(type(x) in (int, float) and math.isfinite(x) for x in values)
                and a['foff'] != 0 and a['tsamp'] > 0, 'Finite actual frequency/time header required')
        this = (tuple(shape), tuple(chunks), a['fch1'], a['foff'], a['tsamp'])
        require(grid is None or this == grid, 'All six sources must have exactly common geometry/grid')
        grid = this
        starts.append(float(a['tstart']))
    shape, chunks, fch1_mhz, df_mhz, tsamp = grid
    nrows, total_channels, native_channels = shape[0], shape[2], chunks[2]
    native_count = (total_channels + native_channels - 1) // native_channels
    ordinal = native_count // 2
    c0 = ordinal * native_channels
    count = min(native_channels, total_channels - c0)
    require(native_count >= 1 and count >= 3 * CORE, 'Selected actual midpoint native is too small for safe cores')
    midpoint = {'native_ordinal_zero_based': ordinal, 'absolute_channel_start': c0, 'channel_count': count}
    for s in sources:
        require(s['native_chunks_along_frequency'] == native_count
                and s['metadata_derived_midpoint'] == midpoint, 'Qualified fixed midpoint rule differs')
    fch1, df = fch1_mhz * 1000000.0, df_mhz * 1000000.0
    require(math.isfinite(fch1) and math.isfinite(df) and df != 0, 'Hz conversion invalid')
    anchor = min(starts)
    previous_end = -math.inf
    firsts, lasts = [], []
    for start_mjd in starts:
        start = (start_mjd - anchor) * 86400.0
        require(start >= previous_end, 'Actual scan integrations overlap or are unordered')
        previous_end = start + nrows * tsamp
        firsts.append(start + .5 * tsamp)
        lasts.append(start + (nrows - .5) * tsamp)
    span = (nrows - 1) * tsamp
    mismatch = (8.0 / (DRIFT_COUNT - 1)) * span / (2.0 * abs(df))
    require(mismatch <= .5 + 1e-12, 'Frozen785 grid exceeds half-channel own-ON mismatch')
    # The extra channel bounds complete absolute rounding and width1/3 support.
    search_halo = math.ceil(4.0 * span / abs(df)) + 250 + 1 + 1
    max_profile_dt = max(abs(t - firsts[i]) for i in (0, 2, 4) for t in firsts + lasts)
    profile_margin = math.ceil(4.0 * max_profile_dt / abs(df)) + 64 + 1
    # Keep the root-selected full interior q list; fail before amplitudes if an
    # actual new geometry cannot support every selected search/profile path.
    require(search_halo <= CORE and profile_margin <= CORE,
            'Actual geometry lacks full frozen interior search/profile support')
    q_indices = list(range(1, count // CORE - 1))
    require(q_indices and all(q * CORE - search_halo >= 0
            and (q + 1) * CORE + search_halo <= count for q in q_indices), 'Incomplete native search crop')
    return {'rows_per_scan': nrows, 'source_dataset_shape': list(shape), 'source_chunk_shape': list(chunks),
            'native_frequency_chunk_count': native_count, **midpoint,
            'fch1_hz': fch1, 'df_hz': df, 'tsamp_s': tsamp, 'MJD_anchor': anchor,
            'scan_tstart_MJD': starts, 'core_q_indices': q_indices, 'core_channels': CORE,
            'crop_halo_channels': search_halo, 'six_scan_profile_margin_channels': profile_margin,
            'drift_grid_count': DRIFT_COUNT, 'drift_grid_first_hz_s': -4.0,
            'drift_grid_last_hz_s': 4.0, 'widths_channels': list(WIDTHS),
            'own_ON_half_grid_mismatch_channels': mismatch, 'scan_order': list(SCANS),
            'scored_scan_order': list(SCANS), 'expected_maps': 6 * len(q_indices),
            'all_six_carrier_maxima': 6 * len(q_indices) * CORE,
            'ON_carrier_maxima': 3 * len(q_indices) * CORE,
            'correlated_drift_width_combinations': 6 * len(q_indices) * CORE * DRIFT_COUNT * len(WIDTHS),
            'selected_native_carrier_coverage_fraction_per_scan': len(q_indices) * CORE / count,
            'complete_source_frequency_carrier_coverage_fraction_per_scan': len(q_indices) * CORE / total_channels,
            'selected_native_carrier_coverage_fraction_per_ON': len(q_indices) * CORE / count,
            'complete_source_frequency_carrier_coverage_fraction_per_ON': len(q_indices) * CORE / total_channels,
            'excluded_edge_core_indices': [0, count // CORE - 1],
            'unsearched_native_tail_channels': count % CORE}


def save_json(path, value, replace=False):
    raw = (json.dumps(value, allow_nan=False, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
    pending = path.with_name(path.name + '.pending')
    with pending.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    if replace:
        os.replace(pending, path)
    else:
        os.link(pending, path)
        pending.unlink()
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def output_reservation_bytes(geometry):
    """Pre-amplitude storage plan; does not assume compressed noise is small."""
    nrows, count, maps = geometry['rows_per_scan'], geometry['channel_count'], geometry['expected_maps']
    decoded_npy = 6 * (nrows * count * 4 + 4096)
    # Actual numeric map payload is 42 bytes/carrier + 8 bytes/drift. The
    # larger reservation includes NPY/ZIP headers and row-normalization JSON.
    map_outputs = maps * (CORE * 64 + DRIFT_COUNT * 16 + nrows * 512 + 65536)
    profile_outputs = 9 * (6 * nrows * 129 * 16 + 6 * nrows * 128 + 6 * 129 * 16 + 65536)
    return decoded_npy + map_outputs + profile_outputs + 16777216


def usage(start):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_since_module_clock': time.monotonic() - start,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def directory_bytes(root):
    total = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(base) / name).is_symlink()]
        for name in files:
            path = Path(base) / name
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
    return total


def check_caps(root, out, scope, start, check_shared=True):
    measured = usage(start)
    limits = scope['limits']
    require(measured['process_CPU_seconds_including_imports'] <= limits['CPU_seconds']
            and measured['wall_seconds_since_module_clock'] <= limits['wall_seconds']
            and measured['peak_RSS_bytes'] <= limits['memory_bytes'], 'Measured search resource cap exceeded')
    require(directory_bytes(out) <= limits['output_bytes'], 'Finite output cap exceeded')
    roots = [Path(x) for x in scope['shared_workspace_roots']]
    require(roots and len(roots) == len(set(roots)) and all(p.is_absolute() and p.resolve() == p and p.is_dir() for p in roots)
            and all(not p.is_relative_to(q) for p in roots for q in roots if p != q), 'Disjoint canonical shared roots required')
    if check_shared:
        require(sum(directory_bytes(p) for p in roots) <= limits['shared_workspace_bytes'], 'Shared disk cap exceeded')
    return measured


def admit(root, scope, root_admission, scope_sha, freeze):
    require(scope['schema'] == 'SETI_VISIT2019_FIXED_ONE_NATIVE_PILOT_SEARCH_SCOPE_V1'
            and scope['family_id'] == FAMILY and scope['root_GO_required'] is True
            and scope['retry_resume_rerun_authorized'] is False, 'Wrong one-shot fixed pilot scope')
    require(scope['search_script_sha256'] == digest(Path(__file__))
            and scope['unchanged_detector_sha256'] == DETECTOR_SHA, 'Frozen code differs')
    require(set(scope['limits']) == set(MAX_LIMITS)
            and all(type(scope['limits'][k]) is int and 0 < scope['limits'][k] <= v
                    for k, v in MAX_LIMITS.items()), 'Root finite limits exceed prospective maximum')
    require(root_admission['schema'] == 'SETI_VISIT2019_NATIVE_PILOT_ROOT_ADMISSION_V1'
            and root_admission['status'] == 'PASS_FIXED_NEW_NATIVE_PILOT_ADMISSION'
            and root_admission['scope_sha256'] == scope_sha
            and root_admission['script_sha256'] == scope['search_script_sha256']
            and root_admission['public_freeze_commit'] == freeze
            and root_admission['all_frozen_input_readbacks_PASS'] is True
            and root_admission['all_acquisition_and_source_QA_processes_closed'] is True
            and root_admission['one_search_GO'] is True, 'Actual frozen root admission/closed parents required')
    pins = scope['input_pins']
    require(isinstance(pins, list) and 0 < len(pins) <= 512
            and len({p['path'] for p in pins}) == len(pins), 'Finite unique frozen input pins required')
    admitted = {p['path']: p for p in pins}
    for pin in pins:
        read_pin(root, pin, False)
    for key in ('qualified_metadata_pin', 'acquisition_scope_pin', 'acquisition_result_pin', 'acquisition_execution_pin', 'acquisition_outer_pin'):
        require(scope[key] == admitted.get(scope[key]['path']), 'Missing explicit prerequisite pin: ' + key)
    metadata = read_pin(root, scope['qualified_metadata_pin'])
    acquisition = read_pin(root, scope['acquisition_result_pin'])
    execution = read_pin(root, scope['acquisition_execution_pin'])
    acquisition_scope = read_pin(root, scope['acquisition_scope_pin'])
    require(acquisition_scope['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_SCOPE_V1'
            and acquisition_scope['qualified_metadata_pin'] == scope['qualified_metadata_pin'],
            'Exact frozen acquisition scope/qualification join required')
    for key, value in acquisition_scope.items():
        if key.endswith('_pin') and isinstance(value, dict) and set(value) == {'path', 'bytes', 'sha256'}:
            require(value == admitted.get(value['path']), 'Missing frozen acquisition source prerequisite: ' + key)
    descriptor_pin = acquisition_scope['descriptor_manifest_pin']
    descriptors = read_pin(root, descriptor_pin)
    require(descriptors['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_DESCRIPTOR_MANIFEST_V1'
            and descriptors['status'] == 'PASS_CLEAN_EXACT_SIX_NATIVE_ROW_DESCRIPTORS_METADATA_ONLY'
            and descriptors['qualification_result_pin'] == scope['qualified_metadata_pin']
            and descriptors['spectral_values_read'] is False and descriptors['spectral_payload_fetched'] is False,
            'Pinned typed metadata-only native descriptor manifest required')
    for evidence in descriptors['typed_index_evidence_pins']:
        require(evidence == admitted.get(evidence['path']), 'Missing original typed descriptor evidence pin')
    ledger_pin = execution['SOURCE_BODY_LEDGER_pin']
    require(ledger_pin == admitted.get(ledger_pin['path']), 'Missing actual source BODY ledger pin')
    ledger = read_pin(root, ledger_pin)
    require(ledger['schema'] == 'SETI_VISIT2019_ONE_NATIVE_APPLICATION_BODY_LEDGER_V1'
            and ledger['complete'] is True
            and ledger['BODY_bytes_received'] == acquisition_scope['exact_expected_payload_BODY_bytes'],
            'Actual exact completed raw source BODY ledger required')
    for value in acquisition['verified_input_end_pins']:
        require(value == admitted.get(value['path']), 'Missing acquisition authenticated end-input pin')
    # The pinned actual outer receipt is retained verbatim as evidence. Root's
    # late admission binds its observed closure; no unknown process handle is
    # treated as proof and no separate process or source API is invoked here.
    outer = read_pin(root, scope['acquisition_outer_pin'])
    geometry = derive_geometry(metadata)
    require(geometry == scope['geometry'], 'Prospectively frozen actual geometry differs')
    require(acquisition['schema'] == ACQ_SCHEMA and acquisition['status'] == ACQ_PASS
            and acquisition['qualified_metadata_pin'] == scope['qualified_metadata_pin']
            and acquisition['descriptor_manifest_pin'] == descriptor_pin
            and acquisition['scope_sha256'] == scope['acquisition_scope_pin']['sha256']
            and execution['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_EXECUTION_RECEIPT_V1'
            and execution['status'] == ACQ_PASS and execution['resource_caps_satisfied'] is True
            and execution['ACQUISITION_RESULT_pin'] == scope['acquisition_result_pin']
            and execution['scope_sha256'] == acquisition['scope_sha256']
            and execution['public_freeze_commit'] == acquisition['public_freeze_commit']
            and outer['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_FULL_CHILD_RESOURCE_RECEIPT_V1'
            and outer['status'] == 'PASS_WHOLE_CHILD_RESOURCES_AND_COMPLETE_ACQUISITION'
            and outer['actual_child_return_code'] == 0 and outer['resource_caps_satisfied'] is True
            and outer['scope_pin'] == scope['acquisition_scope_pin']
            and outer['ACQUISITION_RESULT_pin'] == scope['acquisition_result_pin']
            and outer['EXECUTION_RECEIPT_pin'] == scope['acquisition_execution_pin'],
            'Actual complete authenticated raw acquisition required')
    compacts = acquisition['compact_files']
    require(len(compacts) == len(descriptors['sources']) == 6, 'Exactly six acquired native compacts required')
    for i, (record, source) in enumerate(zip(compacts, metadata['sources'])):
        require(record['source_id'] == source['source_id'] and record['ordered_index'] == i + 1
                and record['source_url'] == source['url'] and record['source_etag'] == source['etag']
                and record['source_file_bytes'] == source['source_file_bytes']
                and record['shape'] == [geometry['rows_per_scan'], 1, geometry['channel_count']]
                and record['dtype_string'] == '<f4'
                and record['source_channel0'] == geometry['absolute_channel_start']
                and record['native_ordinal_zero_based'] == geometry['native_ordinal_zero_based']
                and record['pin'] == admitted.get(record['pin']['path'])
                and record['writer_closed'] is True and record['raw_roundtrip_verified'] is True
                and record['codec_signal_decode_invocations'] == 0, 'Compact identity/geometry/pin differs')
        rows = record['raw_rows']
        require([r['time_row'] for r in rows] == list(range(geometry['rows_per_scan']))
                and all(r['original_chunk_origin'] == [r['time_row'], 0, geometry['absolute_channel_start']]
                        and type(r['filter_mask']) is int and r['filter_mask'] >= 0
                        and type(r['bytes']) is int and r['bytes'] > 0
                        and re.fullmatch('[0-9a-f]{64}', r['sha256']) for r in rows), 'Complete actual raw-row provenance required')
        descriptor_source = descriptors['sources'][i]
        require(descriptor_source['source_id'] == source['source_id'], 'Typed descriptor source identity differs')
        typed_rows = descriptor_source['descriptors']
        require(len(typed_rows) == len(rows), 'Actual typed/raw row count differs')
        for raw, typed in zip(rows, typed_rows):
            require(raw['time_row'] == typed['time_row']
                    and raw['original_chunk_origin'] == typed['coordinates'][:3]
                    and raw['filter_mask'] == typed['filter_mask']
                    and raw['bytes'] == typed['size']
                    and raw['source_range_half_open'] == [typed['file_offset'], typed['file_offset'] + typed['size']],
                    'Actual raw compact row differs from frozen typed descriptor')
    # Six retained raw natives plus normalization/temporary preprocessing must
    # fit the scope cap. No source row is decoded to estimate this admission.
    nrows, count = geometry['rows_per_scan'], geometry['channel_count']
    raw_bytes = 6 * nrows * count * 4
    median_workspace = 2 * nrows * count * 4
    maximum_collection_and_sort_workspace = 128 * len(geometry['core_q_indices']) * CORE
    scorer_workspace = 256 * nrows * (CORE + 2 * geometry['crop_halo_channels'])
    planned_peak = raw_bytes + median_workspace + maximum_collection_and_sort_workspace + scorer_workspace + 201326592
    require(planned_peak <= scope['limits']['memory_bytes'], 'Actual geometry exceeds conservative frozen memory plan')
    require(output_reservation_bytes(geometry) <= scope['limits']['output_bytes'],
            'Actual geometry exceeds pre-amplitude decoded/maps/profiles output reservation')
    detector = confined(root, scope['detector_path'])
    require(detector == Path(__file__).parent / 'dependencies/detector.py'
            and admitted[scope['detector_path']]['sha256'] == DETECTOR_SHA and digest(detector) == DETECTOR_SHA,
            'Byte-identical original detector required')
    for package, version in VERSIONS.items():
        require(importlib.metadata.version(package) == version, 'Runtime package differs: ' + package)
    return metadata, acquisition, geometry


def fixed_profiles(np, arrays, metadata, normalization, tops, geometry, out):
    """Original profile arithmetic with only actual row count/header parameters."""
    nrows = geometry['rows_per_scan']
    fch1, df, tsamp = geometry['fch1_hz'], geometry['df_hz'], geometry['tsamp_s']
    c0, count, anchor = geometry['absolute_channel_start'], geometry['channel_count'], geometry['MJD_anchor']
    row_medians = np.asarray([normalization['row_power_medians'][s] for s in SCANS])
    require(row_medians.shape == (6, nrows) and np.isfinite(row_medians).all()
            and (row_medians > 0).all(), 'Invalid new full-native row medians')
    headers = {label: source['data_attributes'] for label, source in zip(SCANS, metadata['sources'])}
    offsets = np.arange(-64, 65)
    flank = np.abs(offsets) > 3
    profiles_dir = out / 'profiles'
    profiles_dir.mkdir()
    records = []
    for origin in ONS:
        for track in tops[origin][:3]:
            dt = np.asarray([(headers[s]['tstart'] - anchor) * 86400
                + (np.arange(nrows) + .5) * tsamp - track['reference_seconds_from_anchor'] for s in SCANS])
            base = (track['reference_frequency_hz'] - fch1) / df
            centers = np.rint(base + track['drift_hz_s'] * dt / df).astype(np.int64)
            indices = centers[:, :, None] - c0 + offsets[None, None, :]
            require(indices.min() >= 0 and indices.max() < count, 'Fixed six-scan profile exceeds acquired native')
            raw = np.asarray([arrays[s][np.arange(nrows)[:, None], indices[i]] for i, s in enumerate(SCANS)])
            normalized = raw.astype(np.float64) / row_medians[:, :, None]
            baseline = np.median(normalized[:, :, flank], axis=2)
            radius = track['width_channels'] // 2
            center = normalized[:, :, 64 - radius:65 + radius].mean(axis=2)
            residual = center - baseline
            mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
            require(np.isfinite(residual).all() and np.isfinite(mean_profile).all(), 'Nonfinite fixed profile')
            patch_path = profiles_dir / (track['track_id'] + '.npz')
            np.savez_compressed(patch_path, raw_power=raw, row_normalized_power=normalized,
                saved_full_chunk_row_medians=row_medians, frozen_source_channel_centers=centers,
                source_channel_offsets=offsets, times_seconds_from_reference=dt,
                center_row_normalized_power=center, fixed_flank_median_row_normalized_power=baseline,
                center_minus_flank_each_row=residual, mean_fixed_track_frequency_profile=mean_profile,
                scans=np.asarray(SCANS), df_hz=df, source_channel0=c0,
                reference_frequency_hz=track['reference_frequency_hz'], drift_hz_s=track['drift_hz_s'],
                width_channels=track['width_channels'], fixed_source_channel_shift=0)
            split = nrows // 2
            records.append({'selected_track': track, 'fixed_frequency_shift_channels': 0,
                'fixed_flank_offsets': 'absolute channel offset >3 within +/-64',
                'patch': {'path': 'profiles/' + patch_path.name, 'sha256': digest(patch_path), 'bytes': patch_path.stat().st_size},
                'scan_profiles': [{'scan_id': s, 'original_source_id': metadata['sources'][i]['source_id'],
                    'row_count': nrows, 'mean_center_minus_flank': float(residual[i].mean()),
                    'median_center_minus_flank': float(np.median(residual[i])),
                    'positive_rows': int(np.count_nonzero(residual[i] > 0)),
                    'first_half_row_count': split, 'last_half_row_count': nrows - split,
                    'first_half_mean_center_minus_flank': float(residual[i, :split].mean()),
                    'last_half_mean_center_minus_flank': float(residual[i, split:].mean()),
                    'all_center_minus_flank_rows': residual[i].tolist(),
                    'all_raw_width_mean_power': raw[i, :, 64 - radius:65 + radius].mean(axis=1).tolist(),
                    'frozen_source_channel_centers': centers[i].tolist()} for i, s in enumerate(SCANS)],
                'classification': 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'})
            save_json(out / 'FIXED_TOP3_PROFILES.json', records, replace=True)
    require(len(records) == 9, 'Incomplete fixed nine-profile family')
    return {'profile_count': 9, 'scan_profile_count': 54, 'all_rows_retained': nrows,
            'source_top20_sha256': digest(out / 'DRIFT_TOP20.json'),
            'saved_normalization_sha256': digest(out / 'NORMALIZATION.json'),
            'shift_frequency_drift_width_optimization_applied': False,
            'time_profile_units': 'width-mean raw power/full-native float32 row median minus fixed normalized flank median',
            'mean_profile_units': 'mean track-aligned row-normalized power minus each row fixed flank median'}


def science(root, scope, metadata, acquisition, geometry, out, start):
    # Scientific imports occur only after the once marker, full metadata/source
    # admission and actual root freeze/readback/GO. No module downloads data.
    require(os.environ.get('PYTHONPATH') == str(root.parent / 'seti_fullpower_work/deps')
            and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1', 'Root read-only codec dependency environment required')
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    import numpy as np
    import h5py
    import hdf5plugin  # Register codecs for the exact acquired compressed rows.
    require(h5py.version.hdf5_version == scope['hdf5_version'], 'Frozen HDF5 version differs')
    nrows, count, c0 = geometry['rows_per_scan'], geometry['channel_count'], geometry['absolute_channel_start']
    fch1, df, tsamp, anchor = geometry['fch1_hz'], geometry['df_hz'], geometry['tsamp_s'], geometry['MJD_anchor']
    arrays, verified = {}, []
    for label, record in zip(SCANS, acquisition['compact_files']):
        path = read_pin(root, record['pin'], False)
        with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
            data = handle['data']
            require(data.shape == (nrows, 1, count) and data.dtype.str == '<f4'
                    and data.attrs['original_source_url'] == record['source_url']
                    and data.attrs['original_source_etag'] == record['source_etag']
                    and int(data.attrs['original_source_frequency_chunk_origin']) == c0
                    and int(data.attrs['original_source_native_ordinal']) == geometry['native_ordinal_zero_based']
                    and int(data.attrs['original_source_file_bytes']) == record['source_file_bytes'],
                    'Exact acquired data frame/source provenance differs')
            values = data[:, 0, :]
        require(np.isfinite(values).all() and (values >= 0).all(), 'Invalid full-native power')
        rows = [{'time_row': row, 'decoded_bytes': count * 4,
                 'decoded_sha256': sha(values[row].tobytes(order='C'))} for row in range(nrows)]
        decoded_path = out / (label + '_decoded_native.npy')
        require(directory_bytes(out) + values.nbytes + 4096 <= scope['limits']['output_bytes'],
                'Insufficient finite output reservation before decoded NPY write')
        with decoded_path.open('xb') as decoded_handle:
            np.save(decoded_handle, values, allow_pickle=False)
            decoded_handle.flush()
            os.fsync(decoded_handle.fileno())
        decoded_pin = {'path': decoded_path.relative_to(root).as_posix(),
                       'bytes': decoded_path.stat().st_size, 'sha256': digest(decoded_path)}
        arrays[label] = values
        verified.append({'scan_id': label, 'original_source_id': record['source_id'],
                         'ordered_index': record['ordered_index'], 'compact_pin': record['pin'],
                         'decoded_array_pin': decoded_pin, 'decoded_array_shape': [nrows, count],
                         'decoded_array_dtype_string': values.dtype.str,
                         'decoded_array_order': 'C', 'raw_source_rows': record['raw_rows'], 'decoded_rows': rows})
        check_caps(root, out, scope, start)
    save_json(out / 'DECODED_NATIVE_ROWS.json', {'schema': 'SETI_VISIT2019_NEW_NATIVE_DECODED_ROWS_V1',
        'decoded_files': verified, 'source_authentication': 'pinned exact acquired compressed rows and compact bytes',
        'independent_decoded_source_QA_performed': False})
    normalization = {'source_channel0': c0, 'count': count,
        'row_power_medians': {label: np.median(arrays[label], axis=1).tolist() for label in SCANS},
        'method': 'full acquired native-channel row median computed on raw float32; profile float64 promotion',
        'raw_dtype': '<f4'}
    save_json(out / 'NORMALIZATION.json', normalization)
    spec = importlib.util.spec_from_file_location('unchanged_new_visit_detector', confined(root, scope['detector_path']))
    detector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = detector
    spec.loader.exec_module(detector)
    cfg = detector.Config(widths=WIDTHS)
    drifts, dt = np.linspace(-4.0, 4.0, DRIFT_COUNT), np.arange(nrows) * tsamp
    mismatch = float((drifts[1] - drifts[0]) * dt[-1] / (2 * abs(df)))
    require(mismatch <= .5 + 1e-12, 'Exact runtime grid exceeds half-channel own-ON mismatch')
    tops, receipts = {}, []
    halo = geometry['crop_halo_channels']
    for label in SCANS:
        source = metadata['sources'][SCANS.index(label)]
        header = source['data_attributes']
        role = 'ON' if label in ONS else 'OFF'
        columns = {'channels': [], 'scores': [], 'drifts': [], 'widths': [], 'qs': []}
        for q in geometry['core_q_indices']:
            first, crop0, cropstop = c0 + q * CORE, q * CORE - halo, (q + 1) * CORE + halo
            channels = np.arange(first, first + CORE)
            frequencies = fch1 + df * channels
            scan = detector.Scan(label, role, arrays[label][:, crop0:cropstop], header['tstart'], tsamp,
                fch1, df, c0 + crop0, channels, expected_nrows=nrows)
            result, _ = detector.search_scan(scan, frequencies, dt, drifts, cfg)
            score = result['maximum_robust_box_track_score']
            require(np.isfinite(score).all() and np.all(result['valid_hypothesis_count'] == DRIFT_COUNT * len(WIDTHS)),
                    'Incomplete full six-scan core family')
            numeric = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
            numeric.update(source_reference_channels=channels, drift_grid_hz_s=drifts)
            path = out / (label + '_q%06d_all_carriers.npz' % q)
            np.savez_compressed(path, **numeric)
            norm_path = out / (label + '_q%06d_normalization.json' % q)
            save_json(norm_path, result['normalization'])
            receipts.append({'scan_id': label, 'original_source_id': source['source_id'], 'core_q': q,
                'path': path.name, 'sha256': digest(path), 'bytes': path.stat().st_size,
                'searched_carriers': CORE, 'valid_hypotheses_per_carrier': DRIFT_COUNT * len(WIDTHS),
                'reference_channel_interval_half_open': [first, first + CORE],
                'normalization': {'path': norm_path.name, 'sha256': digest(norm_path), 'bytes': norm_path.stat().st_size}})
            for key, value in (('channels', channels), ('scores', score), ('drifts', result['winning_drift_hz_s']),
                ('widths', result['winning_width_channels']), ('qs', np.full(CORE, q, dtype=np.int64))):
                if role == 'ON':
                    columns[key].append(value)
            save_json(out / 'DRIFT_CHECKPOINT.json', {'completed_scan_maps': len(receipts),
                'expected_scan_maps': geometry['expected_maps'], 'scored_scan_order': list(SCANS),
                'complete': len(receipts) == geometry['expected_maps'],
                'receipts': receipts}, replace=True)
            check_caps(root, out, scope, start, check_shared=False)
        if role == 'OFF':
            del columns
            check_caps(root, out, scope, start)
            continue
        columns = {key: np.concatenate(value) for key, value in columns.items()}
        chosen = []
        for index in np.lexsort((columns['channels'], -columns['scores'])):
            index = int(index)
            if all(abs(int(columns['channels'][index]) - int(columns['channels'][other])) > 3 for other in chosen):
                chosen.append(index)
            if len(chosen) == 20:
                break
        require(len(chosen) == 20, 'Incomplete per-ON top20')
        reference = (header['tstart'] - anchor) * 86400 + .5 * tsamp
        tops[label] = [{'track_id': label + '_newvisit_native_pilot_rank_%02d' % rank,
            'family': FAMILY, 'original_source_id': source['source_id'], 'originating_scan': label,
            'originating_role': 'ON', 'display_rank': rank, 'source_reference_channel': int(columns['channels'][index]),
            'reference_frequency_hz': float(fch1 + df * columns['channels'][index]),
            'reference_seconds_from_anchor': float(reference), 'drift_hz_s': float(columns['drifts'][index]),
            'width_channels': int(columns['widths'][index]), 'maximum_robust_box_track_score': float(columns['scores'][index]),
            'reference_core_tile': int(columns['qs'][index]), 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'}
            for rank, index in enumerate(chosen, 1)]
        save_json(out / 'DRIFT_TOP20.json', tops, replace=True)
        del columns
        check_caps(root, out, scope, start)
    profile_summary = fixed_profiles(np, arrays, metadata, normalization, tops, geometry, out)
    return {'decoded_rows_summary': {'scan_count': 6, 'rows_per_scan': nrows, 'decoded_rows': 6 * nrows,
                'decoded_raw_cells': 6 * nrows * count, 'new_full_native_row_medians': 6 * nrows},
            'search_summary': {**geometry, 'completed_scan_maps': len(receipts), 'top20_ON_entries': 60,
                'score_definition': 'unchanged core-median/501-filter/row-MAD/winsorized-location odd-box sum divided by sqrt(Nrow*width)',
                'score_is_calibrated_SNR_or_FAP': False, 'independent_hypothesis_tests_claimed': False,
                'OFF_same_fixed_grid_scored': True, 'OFF_compatibility_rescan_or_veto_applied': False,
                'independent_visit_comparison_performed': False},
            'fixed_profile_summary': profile_summary, 'runtime_versions': {**VERSIONS, 'HDF5': h5py.version.hdf5_version}}


def main():
    start = MODULE_STARTED
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit',
                 'root-admission', 'expected-root-admission-sha256'):
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--root-go-after-review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    require(root.is_absolute() and root.resolve() == root, 'Canonical absolute root required')
    require(args.root_go_after_review and re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Root one-shot frozen GO required')
    scope_path = Path(args.scope)
    require(scope_path == root / 'tools' / FAMILY / 'scope.json', 'Exact prospective scope namespace required')
    raw = scope_path.read_bytes()
    require(sha(raw) == args.expected_scope_sha256 and re.fullmatch('[0-9a-f]{64}', args.expected_scope_sha256), 'Exact scope SHA required')
    scope = json.loads(raw)
    require(scope.get('family_id') == FAMILY and set(scope.get('limits', {})) == set(MAX_LIMITS)
            and all(type(scope['limits'][k]) is int and 0 < scope['limits'][k] <= v for k, v in MAX_LIMITS.items()),
            'Prospective finite resource limits required')
    limits = scope['limits']
    def deadline(signum, frame):
        raise TimeoutError('Frozen one-shot pilot resource deadline reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (limits['CPU_seconds'], limits['CPU_seconds'] + 2))
    resource.setrlimit(resource.RLIMIT_AS, (limits['memory_bytes'], limits['memory_bytes']))
    signal.alarm(max(1, math.ceil(limits['wall_seconds'] - (time.monotonic() - start))))
    stage = root / 'results' / FAMILY
    stage.mkdir(parents=True, exist_ok=True)
    lock = (stage / 'SERIAL_ACTIVE.lock').open('a+b')
    out = stage / 'measurement'
    complete = False
    owns_attempt, owns_output = False, False
    input_directory_fd = None
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = stage / 'SEARCH_STARTED_ONCE.json'
        require(not marker.exists() and not marker.with_name(marker.name + '.pending').exists()
                and not out.exists() and not (stage / 'FAILURE_RECEIPT.json').exists(),
                'Existing attempt/output is immutable; no retry or append')
        owns_attempt = True
        save_json(marker, {'status': 'STARTED_FIXED_NEW_NATIVE_PILOT_ONCE',
            'scope_sha256': args.expected_scope_sha256, 'script_sha256': digest(Path(__file__)),
            'public_freeze_commit': args.freeze_commit, 'retry_authorized': False})
        admission_path = Path(args.root_admission)
        require(admission_path.is_absolute() and admission_path.resolve() == admission_path and root in admission_path.parents,
                'Canonical late root admission required')
        admission_raw = admission_path.read_bytes()
        require(sha(admission_raw) == args.expected_root_admission_sha256, 'Exact late root admission SHA differs')
        root_admission = json.loads(admission_raw)
        # The acquisition writer holds this stable directory inode flock until
        # its closed terminal receipt. Take it read-only and retain ownership
        # before even opaque compact hashing, through our final receipt.
        acquisition_directory = confined(root, scope['acquisition_result_pin']['path']).parent
        input_directory_fd = os.open(acquisition_directory, os.O_RDONLY | os.O_DIRECTORY)
        fcntl.flock(input_directory_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        metadata, acquisition, geometry = admit(root, scope, root_admission, args.expected_scope_sha256, args.freeze_commit)
        require(scope['output_directory'] == str(out.relative_to(root)), 'Fixed new output directory required')
        out.mkdir(exist_ok=False)
        owns_output = True
        save_json(out / 'INPUT_PINS.json', {'scope_sha256': args.expected_scope_sha256,
            'public_freeze_commit': args.freeze_commit, 'pins': scope['input_pins'],
            'root_admission_sha256': args.expected_root_admission_sha256})
        check_caps(root, out, scope, start)
        summary = science(root, scope, metadata, acquisition, geometry, out, start)
        for pin in scope['input_pins']:
            read_pin(root, pin, False)
        require(sha(scope_path.read_bytes()) == args.expected_scope_sha256
                and sha(admission_path.read_bytes()) == args.expected_root_admission_sha256,
                'Scope/root admission changed during science')
        measured = check_caps(root, out, scope, start)
        receipt = {'schema': 'SETI_VISIT2019_ONE_NATIVE_PILOT_EXECUTION_V1',
            'status': 'COMPLETE_NEW_VISIT_FIXED_NATIVE_PILOT_EXPLORATORY_ONLY',
            'family_id': FAMILY, 'script_sha256': digest(Path(__file__)),
            'unchanged_detector_sha256': DETECTOR_SHA, 'scope_sha256': args.expected_scope_sha256,
            'public_freeze_commit': args.freeze_commit, 'root_admission_sha256': args.expected_root_admission_sha256,
            'limits': limits, 'resource_caps_satisfied_before_terminal_serialization': True,
            'all_input_end_readbacks_PASS': True, 'new_telescope_HTTP_requests': 0,
            'new_telescope_BODY_bytes': 0, 'new_visit_source_inputs': True,
            'no_old_scientific_outputs_rerun': True, 'retry_resume_rerun_authorized': False,
            'selection_is_postsearch_descriptive': True, 'independent_validation_status': 'BLOCKED_UNCHANGED',
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'qualified_sky_detection': False,
            **summary, **measured}
        # Prepare/fsync the terminal before an explicit final cap boundary.
        # Mark publication committed at the exclusive link while termination
        # signals are blocked; a later fsync/stdout error cannot append FAILED
        # beside a canonical COMPLETE. Whole-child outer resources remain
        # authoritative and must be checked after this process closes.
        terminal = out / 'EXECUTION_RECEIPT.json'
        pending = terminal.with_name(terminal.name + '.pending')
        terminal_raw = (json.dumps(receipt, allow_nan=False, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
        with pending.open('xb') as handle:
            handle.write(terminal_raw)
            handle.flush()
            os.fsync(handle.fileno())
        final_usage = check_caps(root, out, scope, start)
        require(final_usage['process_CPU_seconds_including_imports'] + .1 < limits['CPU_seconds']
                and final_usage['wall_seconds_since_module_clock'] + 2 < limits['wall_seconds'],
                'Insufficient finite terminal publication headroom')
        signal.alarm(0)
        signal.signal(signal.SIGXCPU, signal.SIG_IGN)
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK,
            {signal.SIGALRM, signal.SIGXCPU, signal.SIGINT, signal.SIGTERM, signal.SIGHUP})
        try:
            os.link(pending, terminal)
            complete = True
            pending.unlink()
            fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        try:
            print(json.dumps({'status': receipt['status'], **measured}), flush=True)
        except BrokenPipeError:
            pass
    except BaseException as error:
        if owns_attempt and not complete:
            failure = {'status': 'FAILED_NEW_VISIT_PILOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',
                'error_type': type(error).__name__, 'error': str(error),
                'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
                'measurement_directory_created': out.exists(), **usage(start)}
            save_json((out if owns_output else stage) / 'FAILURE_RECEIPT.json', failure)
        raise
    finally:
        signal.alarm(0)
        if input_directory_fd is not None:
            os.close(input_directory_fd)
        lock.close()


if __name__ == '__main__':
    main()
