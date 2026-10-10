"""Independent once-only integrity QA of a CLOSED new-visit native pilot.

Source-only preparation: no observation, NumPy or codec is opened at import.
Runtime reads retained decoded NPY rows and original saved output arrays only.
It never imports a detector/profile kernel, opens H5, decodes a codec, obtains
source bytes, reruns preprocessing, or measures a new scientific hypothesis.
"""
from __future__ import annotations

import time
START = time.monotonic()
import argparse
import fcntl
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

sys.dont_write_bytecode = True
FAMILY = 'radio_visit2019_s31_blc77_native_pilot_qa_20261010'
PILOT = 'radio_visit2019_s31_blc77_native_pilot_20261010'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
LIMITS = {'CPU_seconds': 60, 'wall_seconds': 1800, 'memory_bytes': 1073741824,
          'output_bytes': 33554432, 'shared_workspace_bytes': 12884901888}
MAP_KEYS = {'frequency_hz_at_tref', 'maximum_robust_box_track_score',
            'winning_drift_hz_s', 'winning_width_channels', 'valid_hypothesis_count',
            'source_reference_channels', 'drift_grid_hz_s'}
PATCH_KEYS = {'raw_power', 'row_normalized_power', 'saved_full_chunk_row_medians',
              'frozen_source_channel_centers', 'source_channel_offsets',
              'times_seconds_from_reference', 'center_row_normalized_power',
              'fixed_flank_median_row_normalized_power', 'center_minus_flank_each_row',
              'mean_fixed_track_frequency_profile', 'scans', 'df_hz', 'source_channel0',
              'reference_frequency_hz', 'drift_hz_s', 'width_channels',
              'fixed_source_channel_shift'}
NORM_KEYS = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
             'row_residual_MAD_scale', 'normalization_unmasked_counts',
             'normalization_source_channels'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def confined(root, relative):
    p = Path(relative)
    require(type(relative) is str and p.parts and not p.is_absolute()
            and '..' not in p.parts and str(p) == relative and '\\' not in relative,
            'Canonical root-relative path required')
    full = root / p
    require(full.resolve() == full and root in full.parents, 'Symlink/escaped file')
    return full


def file_pin(root, path):
    return {'path': str(path.relative_to(root)), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def verify_pin(root, pin):
    require(isinstance(pin, dict) and set(pin) == {'path', 'bytes', 'sha256'}
            and type(pin['bytes']) is int and pin['bytes'] > 0
            and re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'Exact finite file pin required')
    p = confined(root, pin['path'])
    require(p.is_file() and p.stat().st_size == pin['bytes']
            and digest(p) == pin['sha256'], 'File pin differs: ' + pin['path'])
    return p


def load_json(root, pin):
    p = verify_pin(root, pin)
    require(p.suffix == '.json' and p.stat().st_size <= 8388608, 'Bounded JSON required')
    return json.loads(p.read_bytes())


def usage():
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_since_module_clock': time.monotonic() - START,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def tree_bytes(path):
    total = 0
    for base, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [x for x in dirs if not (Path(base) / x).is_symlink()]
        for name in files:
            p = Path(base) / name
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
    return total


def check_caps(out, shared, reserve=0):
    measured = usage()
    require(measured['process_CPU_seconds_including_imports'] <= LIMITS['CPU_seconds']
            and measured['wall_seconds_since_module_clock'] <= LIMITS['wall_seconds']
            and measured['peak_RSS_bytes'] <= LIMITS['memory_bytes'], 'Measured QA resource cap exceeded')
    require(tree_bytes(out) + reserve <= LIMITS['output_bytes']
            and sum(tree_bytes(p) for p in shared) + reserve <= LIMITS['shared_workspace_bytes'],
            'Finite QA output/shared storage cap exceeded')
    return measured


def prepare_json(path, value):
    raw = (json.dumps(value, allow_nan=False, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
    pending = path.with_name(path.name + '.pending')
    with pending.open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return pending


def publish(path, pending):
    os.link(pending, path)
    pending.unlink()
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def median_rank_certificate(np, row, saved, dtype):
    """Check a saved median by counts and bracket extrema, never recompute it.

    For even N the middle pair is implied by counts around the claimed result:
    the lower element is max(below) only if exactly N/2 are below; otherwise
    it is the observed claimed value. The upper element is symmetric. Verify
    the original dtype's two-element mean exactly, including float32 rounding.
    This is an integrity certificate, not a new scientific normalization.
    """
    require(row.ndim == 1 and row.size > 0 and np.isfinite(row).all()
            and math.isfinite(saved), 'Finite median rank inputs required')
    m = dtype(saved)
    require(float(m) == saved, 'Saved median is not exactly representable in declared arithmetic dtype')
    below, above = row < m, row > m
    lower_count, upper_count = int(np.count_nonzero(below)), int(np.count_nonzero(above))
    half = row.size // 2
    require(lower_count <= half and upper_count <= half, 'Claimed median fails central rank counts')
    if row.size % 2:
        require(np.any(row == m), 'Odd median must be an observed central order statistic')
        lower = upper = m
        expected = m
    else:
        lower = dtype(row[below].max()) if lower_count == half else m
        upper = dtype(row[above].min()) if upper_count == half else m
        require(lower <= m <= upper, 'Central pair does not bracket saved median')
        with np.errstate(over='raise', invalid='raise'):
            expected = dtype(dtype(lower + upper) / dtype(2))
    require(float(expected) == saved, 'Saved median differs from central-pair dtype mean')
    return {'below': lower_count, 'equal': int(row.size - lower_count - upper_count),
            'above': upper_count, 'central_lower': float(lower), 'central_upper': float(upper)}


def arrays_equal(np, actual, expected, message):
    require(actual.shape == expected.shape and actual.dtype == expected.dtype
            and np.array_equal(actual, expected), message)


def admit(root, manifest, manifest_pin, freeze):
    require(manifest['schema'] == 'SETI_VISIT2019_NATIVE_PILOT_QA_INPUT_MANIFEST_V1'
            and manifest['family_id'] == FAMILY and manifest['pilot_family_id'] == PILOT
            and manifest['all_pilot_and_acquisition_processes_closed'] is True
            and manifest['no_QA_retry_or_resume'] is True, 'Closed once-only QA admission required')
    require(manifest['qa_worker_pin'] == file_pin(root, Path(__file__)), 'Frozen QA source differs')
    pins = manifest['input_file_pins']
    require(isinstance(pins, list) and 0 < len(pins) <= 2048
            and len({p['path'] for p in pins}) == len(pins), 'Finite unique exact input pins required')
    by_path = {p['path']: p for p in pins}
    for pin in pins:
        verify_pin(root, pin)
    for key in ('pilot_scope_pin', 'pilot_execution_pin', 'pilot_outer_pin',
                'pilot_marker_pin', 'pilot_root_admission_pin'):
        require(manifest[key] == by_path.get(manifest[key]['path']), 'Unadmitted explicit pilot input: ' + key)
    scope = load_json(root, manifest['pilot_scope_pin'])
    execution = load_json(root, manifest['pilot_execution_pin'])
    outer = load_json(root, manifest['pilot_outer_pin'])
    marker = load_json(root, manifest['pilot_marker_pin'])
    admission = load_json(root, manifest['pilot_root_admission_pin'])
    require(scope['schema'] == 'SETI_VISIT2019_FIXED_ONE_NATIVE_PILOT_SEARCH_SCOPE_V1'
            and scope['family_id'] == PILOT and execution['schema'] == 'SETI_VISIT2019_ONE_NATIVE_PILOT_EXECUTION_V1'
            and execution['status'] == 'COMPLETE_NEW_VISIT_FIXED_NATIVE_PILOT_EXPLORATORY_ONLY'
            and execution['family_id'] == PILOT and execution['scope_sha256'] == manifest['pilot_scope_pin']['sha256']
            and execution['script_sha256'] == scope['search_script_sha256']
            and execution['unchanged_detector_sha256'] == scope['unchanged_detector_sha256']
            and execution['public_freeze_commit'] == manifest['pilot_public_freeze_commit']
            and execution['all_input_end_readbacks_PASS'] is True
            and execution['retry_resume_rerun_authorized'] is False,
            'Original actual COMPLETE scope/code/freeze required')
    require(marker['scope_sha256'] == execution['scope_sha256']
            and marker['script_sha256'] == execution['script_sha256']
            and marker['public_freeze_commit'] == execution['public_freeze_commit']
            and marker['retry_authorized'] is False
            and admission['schema'] == 'SETI_VISIT2019_NATIVE_PILOT_ROOT_ADMISSION_V1'
            and admission['status'] == 'PASS_FIXED_NEW_NATIVE_PILOT_ADMISSION'
            and admission['all_frozen_input_readbacks_PASS'] is True
            and admission['all_acquisition_and_source_QA_processes_closed'] is True
            and admission['one_search_GO'] is True
            and admission['scope_sha256'] == execution['scope_sha256']
            and admission['script_sha256'] == execution['script_sha256']
            and admission['public_freeze_commit'] == execution['public_freeze_commit']
            and execution['root_admission_sha256'] == manifest['pilot_root_admission_pin']['sha256'],
            'Original marker/admission provenance differs')
    # This exact outer API is supplied by the frozen pilot launcher.
    require(outer['schema'] == 'SETI_VISIT2019_NATIVE_PILOT_WHOLE_CHILD_EXECUTION_V1'
            and outer['status'] == 'PASS_CLOSED_COMPLETE_NATIVE_PILOT_WHOLE_CHILD_RESOURCES'
            and outer['actual_child_return_code'] == 0 and outer['resource_caps_satisfied'] is True
            and outer['child_started'] is True and outer['child_closed_reaped'] is True
            and outer['scope_sha256'] == manifest['pilot_scope_pin']['sha256']
            and outer['public_freeze_commit'] == execution['public_freeze_commit']
            and outer['root_admission_sha256'] == execution['root_admission_sha256']
            and outer['worker_pin']['sha256'] == execution['script_sha256']
            and outer['EXECUTION_RECEIPT_pin'] == manifest['pilot_execution_pin'],
            'Actual closed zero-exit whole-child resources required')
    for key in ('worker_pin', 'launcher_pin'):
        require(outer[key] == by_path.get(outer[key]['path']), 'Actual outer source pin missing from manifest')
    require(outer['limits'] == execution['limits'] == scope['limits']
            and outer['whole_command_process_CPU_seconds_before_receipt'] <= scope['limits']['CPU_seconds']
            and outer['whole_child_peak_RSS_bytes'] + outer['launcher_peak_RSS_bytes'] <= scope['limits']['memory_bytes']
            and outer['whole_launch_wall_seconds_before_receipt'] <= scope['limits']['wall_seconds'],
            'Actual original whole-child resource metrics exceed fixed scope')
    for pin in scope['input_pins']:
        require(pin == by_path.get(pin['path']), 'Original source/code prerequisite missing from QA manifest')
    metadata = load_json(root, scope['qualified_metadata_pin'])
    acquisition = load_json(root, scope['acquisition_result_pin'])
    geom = scope['geometry']
    nrows, count, c0 = geom['rows_per_scan'], geom['channel_count'], geom['absolute_channel_start']
    qs = geom['core_q_indices']
    require(type(nrows) is int and 2 <= nrows <= 512 and type(count) is int
            and 3 * 4096 <= count <= 1048576 and type(c0) is int and c0 >= 0
            and qs == list(range(1, count // 4096 - 1)) and len(qs) <= 254
            and geom['scan_order'] == geom['scored_scan_order'] == list(SCANS)
            and geom['expected_maps'] == 6 * len(qs) and geom['drift_grid_count'] == 785
            and geom['widths_channels'] == [1, 3], 'Frozen dynamic pilot geometry invalid')
    require(6 * nrows * count * 4 + 201326592 <= LIMITS['memory_bytes'], 'Retained-row QA exceeds finite memory plan')
    require(metadata['schema'] == 'SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
            and metadata['status'] == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
            and len(metadata['sources']) == len(acquisition['compact_files']) == 6,
            'Actual six-source metadata and acquisition required')
    starts = []
    grid = None
    for i, (source, compact) in enumerate(zip(metadata['sources'], acquisition['compact_files'])):
        shape, chunks, attrs = source['shape'], source['chunks'], source['data_attributes']
        require(source['ordered_index'] == compact['ordered_index'] == i + 1
                and source['source_id'] == compact['source_id'] and source['url'] == compact['source_url']
                and source['etag'] == compact['source_etag'] and source['source_file_bytes'] == compact['source_file_bytes']
                and shape[0] == nrows and shape[1] == chunks[0] == chunks[1] == 1
                and source['dtype_string'] == '<f4' and compact['shape'] == [nrows, 1, count]
                and compact['source_channel0'] == c0 and compact['dtype_string'] == '<f4',
                'Original six-source raw frame identity differs')
        actual_grid = (tuple(shape), tuple(chunks), attrs['fch1'], attrs['foff'], attrs['tsamp'])
        require(grid is None or actual_grid == grid, 'Original common source grid differs')
        grid = actual_grid
        starts.append(float(attrs['tstart']))
    shape, chunks, fch1, df, tsamp = grid
    native_count = (shape[2] + chunks[2] - 1) // chunks[2]
    ordinal = native_count // 2
    midpoint = {'native_ordinal_zero_based': ordinal, 'absolute_channel_start': ordinal * chunks[2],
                'channel_count': min(chunks[2], shape[2] - ordinal * chunks[2])}
    require(geom['source_dataset_shape'] == list(shape) and geom['source_chunk_shape'] == list(chunks)
            and geom['fch1_hz'] == fch1 * 1000000.0 and geom['df_hz'] == df * 1000000.0
            and geom['tsamp_s'] == tsamp and geom['scan_tstart_MJD'] == starts and geom['MJD_anchor'] == min(starts)
            and geom['native_frequency_chunk_count'] == native_count
            and all(geom[k] == v for k, v in midpoint.items())
            and all(s['metadata_derived_midpoint'] == midpoint and s['native_chunks_along_frequency'] == native_count
                    for s in metadata['sources']), 'Original frozen midpoint/header geometry differs')
    roots = [Path(p) for p in scope['shared_workspace_roots']]
    require(roots and len(roots) == len(set(roots)) and all(p.is_absolute() and p.resolve() == p and p.is_dir() for p in roots)
            and all(not p.is_relative_to(q) for p in roots for q in roots if p != q)
            and any(root.is_relative_to(p) for p in roots), 'Complete canonical shared storage roots required')
    require(freeze and re.fullmatch('[0-9a-f]{40}', freeze), 'Actual QA public freeze required')
    return scope, execution, metadata, acquisition, geom, by_path, roots


def check_outputs(np, root, scope, execution, metadata, acquisition, g, pins):
    out = confined(root, scope['output_directory'])
    def saved(name):
        p = str((out / name).relative_to(root))
        require(p in pins, 'Unfrozen original output: ' + p)
        return load_json(root, pins[p])
    decoded, norm = saved('DECODED_NATIVE_ROWS.json'), saved('NORMALIZATION.json')
    checkpoint, tops, profiles = saved('DRIFT_CHECKPOINT.json'), saved('DRIFT_TOP20.json'), saved('FIXED_TOP3_PROFILES.json')
    source_inputs = saved('INPUT_PINS.json')
    require(source_inputs['scope_sha256'] == execution['scope_sha256']
            and source_inputs['public_freeze_commit'] == execution['public_freeze_commit']
            and source_inputs['pins'] == scope['input_pins']
            and source_inputs['root_admission_sha256'] == execution['root_admission_sha256'], 'Original INPUT_PINS differs')
    nrows, count, c0, qs = g['rows_per_scan'], g['channel_count'], g['absolute_channel_start'], g['core_q_indices']
    require(decoded['schema'] == 'SETI_VISIT2019_NEW_NATIVE_DECODED_ROWS_V1'
            and len(decoded['decoded_files']) == 6 and decoded['independent_decoded_source_QA_performed'] is False
            and norm['source_channel0'] == c0 and norm['count'] == count and norm['raw_dtype'] == '<f4'
            and set(norm['row_power_medians']) == set(SCANS), 'Original decoded/normalization geometry differs')
    raw_arrays, median_certificates, decoded_hashes = {}, [], []
    for i, (label, record, src, compact) in enumerate(zip(SCANS, decoded['decoded_files'], metadata['sources'], acquisition['compact_files'])):
        require(record['scan_id'] == label and record['original_source_id'] == src['source_id'] == compact['source_id']
                and record['ordered_index'] == src['ordered_index'] == i + 1
                and record['compact_pin'] == compact['pin']
                and record['raw_source_rows'] == compact['raw_rows']
                and record['decoded_array_shape'] == [nrows, count]
                and record['decoded_array_dtype_string'] == '<f4' and record['decoded_array_order'] == 'C'
                and record['decoded_array_pin'] == pins.get(record['decoded_array_pin']['path']),
                'Saved decoded identity/full-native array pin differs')
        data = np.load(verify_pin(root, record['decoded_array_pin']), allow_pickle=False, mmap_mode='r')
        require(isinstance(data, np.memmap) and data.shape == (nrows, count) and data.dtype.str == '<f4'
                and data.flags.c_contiguous and not data.flags.writeable, 'Readonly exact C-order float32 NPY required')
        require(len(record['decoded_rows']) == len(norm['row_power_medians'][label]) == nrows,
                'Decoded row/median count differs')
        require(all(type(v) in (int, float) and math.isfinite(v) and v > 0
                    for v in norm['row_power_medians'][label]), 'Saved full-native row denominator invalid')
        for row, row_pin in enumerate(record['decoded_rows']):
            require(row_pin['time_row'] == row and row_pin['decoded_bytes'] == count * 4
                    and np.isfinite(data[row]).all() and (data[row] >= 0).all(), 'Decoded row order/power validity differs')
            observed = sha(data[row].tobytes(order='C'))
            require(observed == row_pin['decoded_sha256'], 'Saved full decoded row SHA differs')
            cert = median_rank_certificate(np, data[row], norm['row_power_medians'][label][row], np.float32)
            median_certificates.append({'scan_id': label, 'time_row': row, **cert})
            decoded_hashes.append({'scan_id': label, 'time_row': row, 'decoded_sha256': observed})
        raw_arrays[label] = data
    receipts = checkpoint['receipts']
    require(checkpoint['complete'] is True
            and checkpoint['expected_scan_maps'] == checkpoint['completed_scan_maps'] == g['expected_maps']
            and checkpoint['scored_scan_order'] == list(SCANS)
            and [(r['scan_id'], r['core_q']) for r in receipts] == [(s, q) for s in SCANS for q in qs],
            'Complete original scan-first map inventory differs')
    drift_grid = np.linspace(-4.0, 4.0, 785)
    on_columns = {s: {k: [] for k in ('channels', 'scores', 'drifts', 'widths', 'qs')} for s in ONS}
    science_paths = set()
    for r in receipts:
        s, q = r['scan_id'], r['core_q']
        channels = np.arange(c0 + q * 4096, c0 + (q + 1) * 4096)
        expected_pin = {'path': str((out / r['path']).relative_to(root)), 'bytes': r['bytes'], 'sha256': r['sha256']}
        require(expected_pin == pins.get(expected_pin['path']) and r['searched_carriers'] == 4096
                and r['valid_hypotheses_per_carrier'] == 1570
                and r['reference_channel_interval_half_open'] == [int(channels[0]), int(channels[-1]) + 1]
                and r['original_source_id'] == metadata['sources'][SCANS.index(s)]['source_id'], 'Original map identity differs')
        science_paths.add(expected_pin['path'])
        with np.load(verify_pin(root, expected_pin), allow_pickle=False) as m:
            require(set(m.files) == MAP_KEYS, 'Seven-array original carrier map required')
            arrays_equal(np, m['source_reference_channels'], channels, 'Map carrier identities differ')
            arrays_equal(np, m['drift_grid_hz_s'], drift_grid, 'Exact original drift lattice differs')
            arrays_equal(np, m['frequency_hz_at_tref'], g['fch1_hz'] + g['df_hz'] * channels, 'Map frequencies differ')
            scores, ds, widths, valid = (m[x] for x in ('maximum_robust_box_track_score', 'winning_drift_hz_s',
                                                       'winning_width_channels', 'valid_hypothesis_count'))
            require(all(x.shape == (4096,) for x in (scores, ds, widths, valid))
                    and scores.dtype == ds.dtype == np.dtype('float64') and widths.dtype == np.dtype('int16')
                    and valid.dtype == np.dtype('int64') and np.isfinite(scores).all()
                    and np.isfinite(ds).all() and np.isin(ds, drift_grid).all()
                    and np.isin(widths, [1, 3]).all() and (valid == 1570).all(), 'Map saved maxima contract differs')
            if s in ONS:
                for k, value in (('channels', channels), ('scores', scores), ('drifts', ds), ('widths', widths),
                                 ('qs', np.full(4096, q, dtype=np.int64))):
                    on_columns[s][k].append(value.copy())
        n = r['normalization']
        npin = {'path': str((out / n['path']).relative_to(root)), 'bytes': n['bytes'], 'sha256': n['sha256']}
        require(npin == pins.get(npin['path']), 'Unadmitted original normalization JSON')
        science_paths.add(npin['path'])
        values = load_json(root, npin)
        require(set(values) == NORM_KEYS and values['normalization_source_channels'] == channels.tolist()
                and values['normalization_unmasked_counts'] == [4096] * nrows, 'Frozen per-core normalization contract differs')
        for key in NORM_KEYS - {'normalization_source_channels', 'normalization_unmasked_counts'}:
            require(len(values[key]) == nrows and all(type(v) in (int, float) and math.isfinite(v) for v in values[key]),
                    'Nonfinite/incomplete original normalization metadata')
        require(all(x > 0 for x in values['row_power_median'] + values['row_residual_MAD_scale']), 'Invalid original normalization scale')
        for row in range(nrows):
            median_rank_certificate(np, raw_arrays[s][row, q * 4096:(q + 1) * 4096],
                                    values['row_power_median'][row], np.float64)
    require(set(tops) == set(ONS) and all(len(tops[s]) == 20 for s in ONS), 'Exact60 original per-ON ranks required')
    # Reconstruct the original saved-maxima rank/NMS only as integrity QA.
    # No new selection or detector score is produced.
    for s in ONS:
        cols = {k: np.concatenate(v) for k, v in on_columns[s].items()}
        chosen = []
        for idx in np.lexsort((cols['channels'], -cols['scores'])):
            idx = int(idx)
            if all(abs(int(cols['channels'][idx]) - int(cols['channels'][other])) > 3 for other in chosen):
                chosen.append(idx)
            if len(chosen) == 20:
                break
        require(len(chosen) == 20, 'Original saved maxima cannot reproduce all20 fixed ranks')
        src = metadata['sources'][SCANS.index(s)]
        reference = (src['data_attributes']['tstart'] - g['MJD_anchor']) * 86400 + .5 * g['tsamp_s']
        for rank, (t, idx) in enumerate(zip(tops[s], chosen), 1):
            expected = {'track_id': s + '_newvisit_native_pilot_rank_%02d' % rank,
                'family': PILOT, 'original_source_id': src['source_id'], 'originating_scan': s,
                'originating_role': 'ON', 'display_rank': rank, 'source_reference_channel': int(cols['channels'][idx]),
                'reference_frequency_hz': float(g['fch1_hz'] + g['df_hz'] * cols['channels'][idx]),
                'reference_seconds_from_anchor': float(reference), 'drift_hz_s': float(cols['drifts'][idx]),
                'width_channels': int(cols['widths'][idx]), 'maximum_robust_box_track_score': float(cols['scores'][idx]),
                'reference_core_tile': int(cols['qs'][idx]), 'status': 'EXPLORATORY_RANK_UNCLASSIFIED'}
            require(t == expected, 'Original saved top20 rank/NMS differs')
    selected = [t for s in ONS for t in tops[s][:3]]
    require(len(profiles) == 9 and [r['selected_track'] for r in profiles] == selected,
            'Exact original nine frozen top3 profiles required')
    medians = np.asarray([norm['row_power_medians'][s] for s in SCANS], dtype=np.float64)
    offsets = np.arange(-64, 65)
    flank = np.abs(offsets) > 3
    patch_hashes = []
    for record, t in zip(profiles, selected):
        pp = record['patch']
        pin = {'path': str((out / pp['path']).relative_to(root)), 'bytes': pp['bytes'], 'sha256': pp['sha256']}
        require(pin == pins.get(pin['path']) and record['fixed_frequency_shift_channels'] == 0
                and record['fixed_flank_offsets'] == 'absolute channel offset >3 within +/-64'
                and record['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE', 'Fixed profile identity differs')
        science_paths.add(pin['path'])
        dt = np.asarray([(src['data_attributes']['tstart'] - g['MJD_anchor']) * 86400
            + (np.arange(nrows) + .5) * g['tsamp_s'] - t['reference_seconds_from_anchor'] for src in metadata['sources']])
        base = (t['reference_frequency_hz'] - g['fch1_hz']) / g['df_hz']
        centers = np.rint(base + t['drift_hz_s'] * dt / g['df_hz']).astype(np.int64)
        indices = centers[:, :, None] - c0 + offsets[None, None, :]
        require(indices.min() >= 0 and indices.max() < count, 'Original fixed full-window source geometry invalid')
        source_raw = np.asarray([raw_arrays[s][np.arange(nrows)[:, None], indices[i]] for i, s in enumerate(SCANS)])
        with np.load(verify_pin(root, pin), allow_pickle=False) as patch:
            require(set(patch.files) == PATCH_KEYS, 'Exact17 original patch arrays required')
            arrays_equal(np, patch['raw_power'], source_raw, 'Every retained raw fixed-profile cell differs from saved full rows')
            arrays_equal(np, patch['saved_full_chunk_row_medians'], medians, 'Original patch row denominators differ')
            arrays_equal(np, patch['frozen_source_channel_centers'], centers, 'Absolute rounding/reference path differs')
            arrays_equal(np, patch['source_channel_offsets'], offsets, 'Original +/-64 patch window differs')
            arrays_equal(np, patch['times_seconds_from_reference'], dt, 'Original all-six scan/reference times differ')
            arrays_equal(np, patch['scans'], np.asarray(SCANS), 'Patch scan order differs')
            normalized = source_raw.astype(np.float64) / medians[:, :, None]
            arrays_equal(np, patch['row_normalized_power'], normalized, 'Original normalize-first float64 patch differs')
            baseline = patch['fixed_flank_median_row_normalized_power']
            require(baseline.shape == (6, nrows) and baseline.dtype == np.dtype('float64'), 'Original flank baseline shape/dtype differs')
            for scan in range(6):
                for row in range(nrows):
                    median_rank_certificate(np, normalized[scan, row, flank], float(baseline[scan, row]), np.float64)
            radius = t['width_channels'] // 2
            center = normalized[:, :, 64 - radius:65 + radius].mean(axis=2)
            residual = center - baseline
            mean_profile = np.mean(normalized - baseline[:, :, None], axis=1)
            arrays_equal(np, patch['center_row_normalized_power'], center, 'Original width-mean normalized center differs')
            arrays_equal(np, patch['center_minus_flank_each_row'], residual, 'Original signed row residual differs')
            arrays_equal(np, patch['mean_fixed_track_frequency_profile'], mean_profile, 'Original baseline-before-row-mean profile differs')
            for key, value in (('df_hz', g['df_hz']), ('source_channel0', c0), ('reference_frequency_hz', t['reference_frequency_hz']),
                               ('drift_hz_s', t['drift_hz_s']), ('width_channels', t['width_channels']), ('fixed_source_channel_shift', 0)):
                require(patch[key].shape == () and patch[key].item() == value, 'Patch fixed scalar differs: ' + key)
            scans = record['scan_profiles']
            require(len(scans) == 6, 'Six original scan-profile summaries required')
            split = nrows // 2
            for i, (s, item) in enumerate(zip(SCANS, scans)):
                require(item['scan_id'] == s and item['original_source_id'] == metadata['sources'][i]['source_id']
                        and item['row_count'] == nrows and item['first_half_row_count'] == split
                        and item['last_half_row_count'] == nrows - split
                        and item['frozen_source_channel_centers'] == centers[i].tolist()
                        and item['all_center_minus_flank_rows'] == residual[i].tolist()
                        and item['all_raw_width_mean_power'] == source_raw[i, :, 64 - radius:65 + radius].mean(axis=1).tolist()
                        and item['mean_center_minus_flank'] == float(residual[i].mean())
                        and item['positive_rows'] == int(np.count_nonzero(residual[i] > 0))
                        and item['first_half_mean_center_minus_flank'] == float(residual[i, :split].mean())
                        and item['last_half_mean_center_minus_flank'] == float(residual[i, split:].mean()),
                        'Original raw-width or signed scan summary differs')
                median_rank_certificate(np, residual[i], item['median_center_minus_flank'], np.float64)
        patch_hashes.append({'track_id': t['track_id'], 'patch_pin': pin,
                             'saved_full_row_cell_bytes_sha256': sha(source_raw.tobytes(order='C'))})
    expected_files = {str((out / n).relative_to(root)) for n in ('INPUT_PINS.json', 'DECODED_NATIVE_ROWS.json',
        'NORMALIZATION.json', 'DRIFT_CHECKPOINT.json', 'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json', 'EXECUTION_RECEIPT.json')}
    expected_files |= science_paths | {r['decoded_array_pin']['path'] for r in decoded['decoded_files']}
    actual_files = {str(p.relative_to(root)) for p in out.rglob('*') if p.is_file()}
    require(actual_files == expected_files and all(p in pins for p in expected_files), 'Original measurement file inventory differs')
    summary = execution['decoded_rows_summary']
    require(summary == {'scan_count': 6, 'rows_per_scan': nrows, 'decoded_rows': 6 * nrows,
                       'decoded_raw_cells': 6 * nrows * count, 'new_full_native_row_medians': 6 * nrows},
            'Original decoded summary counts differ')
    search = execution['search_summary']
    require(all(search[k] == v for k, v in g.items()) and search['completed_scan_maps'] == 6 * len(qs)
            and search['top20_ON_entries'] == 60 and search['OFF_same_fixed_grid_scored'] is True
            and search['OFF_compatibility_rescan_or_veto_applied'] is False
            and execution['fixed_profile_summary']['profile_count'] == 9
            and execution['fixed_profile_summary']['scan_profile_count'] == 54
            and execution['fixed_profile_summary']['all_rows_retained'] == nrows
            and execution['fixed_profile_summary']['source_top20_sha256'] == pins[str((out / 'DRIFT_TOP20.json').relative_to(root))]['sha256']
            and execution['fixed_profile_summary']['saved_normalization_sha256'] == pins[str((out / 'NORMALIZATION.json').relative_to(root))]['sha256'],
            'Original saved search/profile summary differs')
    return {'six_saved_decoded_arrays': 6, 'decoded_rows_authenticated_to_original_worker_hashes': 6 * nrows,
            'full_native_float32_median_rank_certificates': median_certificates,
            'per_core_float64_median_rank_certificates_verified': 6 * len(qs) * nrows,
            'complete_carrier_maps': 6 * len(qs), 'saved_carrier_maxima': 6 * len(qs) * 4096,
            'original_top20_ON_records_verified': 60, 'fixed_patches': 9, 'scan_profile_summaries': 54,
            'fixed_time_rows': 54 * nrows, 'raw_patch_cell_occurrences': 9 * 6 * nrows * 129,
            'decoded_row_hashes': decoded_hashes, 'fixed_patch_byte_checks': patch_hashes,
            'measurement_output_byte_pins': [pins[p] for p in sorted(expected_files)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'input-manifest', 'expected-input-manifest-sha256', 'qa-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-pilot-closed', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    require(root.is_absolute() and root.resolve() == root and root.is_dir(), 'Canonical project root required')
    require(args.root_go_after_pilot_closed and re.fullmatch('[0-9a-f]{40}', args.qa_freeze_commit), 'Explicit one-shot frozen QA GO required')
    def deadline(signum, frame):
        raise TimeoutError('Finite independent pilot QA deadline reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (60, 62))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS['memory_bytes'], LIMITS['memory_bytes']))
    signal.alarm(max(1, math.ceil(1800 - (time.monotonic() - START))))
    stage = root / 'results' / FAMILY
    stage.mkdir(parents=True, exist_ok=True)
    out = stage / 'review'
    marker = stage / 'QA_STARTED_ONCE.json'
    owned, committed, guards = False, False, []
    try:
        fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY)
        guards.append(fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not marker.exists() and not marker.with_name(marker.name + '.pending').exists()
                and not out.exists() and not (stage / 'FAILURE_RECEIPT.json').exists(), 'No QA retry/resume or output replacement')
        owned = True
        publish(marker, prepare_json(marker, {'status': 'STARTED_INDEPENDENT_SAVED_PILOT_QA_ONCE',
            'qa_script_sha256': digest(Path(__file__)), 'qa_public_freeze_commit': args.qa_freeze_commit,
            'input_manifest_sha256': args.expected_input_manifest_sha256, 'retry_authorized': False}))
        mp = Path(args.input_manifest)
        require(mp == stage / 'QA_INPUT_MANIFEST.json' and mp.resolve() == mp
                and sha(mp.read_bytes()) == args.expected_input_manifest_sha256, 'Exact late input-manifest path/hash required')
        manifest_pin = file_pin(root, mp)
        manifest = load_json(root, manifest_pin)
        scope, execution, metadata, acquisition, g, pins, shared = admit(root, manifest, manifest_pin, args.qa_freeze_commit)
        # Readonly existing stable input locks remain held through terminal;
        # unlike the original writer, QA never creates/unlinks input locks.
        pilot_lock = root / 'results' / PILOT / 'SERIAL_ACTIVE.lock'
        require(pilot_lock.exists() and pilot_lock.resolve() == pilot_lock and pilot_lock.is_file(), 'Existing pilot guard required')
        fd = os.open(pilot_lock, os.O_RDONLY | os.O_NOFOLLOW)
        guards.append(fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquisition_dir = confined(root, scope['acquisition_result_pin']['path']).parent
        fd = os.open(acquisition_dir, os.O_RDONLY | os.O_DIRECTORY)
        guards.append(fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out.mkdir(exist_ok=False)
        check_caps(out, shared, 1048576)
        require(importlib.metadata.version('numpy') == '2.3.5', 'Exact primary NumPy required')
        require(os.environ.get('PYTHONPATH') == str(root.parent / 'seti_fullpower_work/deps')
                and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1', 'Pinned readonly primary dependency environment required')
        for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
            require(os.environ.get(name) == '1', 'Single-thread primary runtime required')
        import numpy as np
        summary = check_outputs(np, root, scope, execution, metadata, acquisition, g, pins)
        for pin in manifest['input_file_pins']:
            verify_pin(root, pin)
        verify_pin(root, manifest_pin)
        require(manifest['qa_worker_pin'] == file_pin(root, Path(__file__)), 'QA source changed during verification')
        measured = check_caps(out, shared, 1048576)
        receipt = {'schema': 'SETI_VISIT2019_NATIVE_PILOT_INDEPENDENT_SAVED_OUTPUT_QA_V1',
            'status': 'PASS_COMPLETE_SAVED_NATIVE_PILOT_OUTPUTS_WITH_RETAINED_RAW_ROWS',
            'family_id': FAMILY, 'pilot_family_id': PILOT, 'qa_script_pin': manifest['qa_worker_pin'],
            'qa_public_freeze_commit': args.qa_freeze_commit, 'input_manifest_pin': manifest_pin,
            'pilot_scope_pin': manifest['pilot_scope_pin'], 'pilot_execution_pin': manifest['pilot_execution_pin'],
            'pilot_outer_pin': manifest['pilot_outer_pin'], 'pilot_public_freeze_commit': manifest['pilot_public_freeze_commit'],
            'limits': LIMITS, 'resource_caps_satisfied_before_terminal_publication': True,
            'all_input_end_readbacks_exact': True, 'saved_maxima_ranking_reconstructed_for_integrity_only': True,
            'original_detector_or_preprocessing_reexecuted': False, 'new_scientific_normalization_performed': False,
            'profile_kernel_imported_or_called': False, 'new_profile_selection_or_measurement': False,
            'original_profile_algebra_reconstructed_for_integrity_only': True,
            'new_scientific_profile_keys_added': False,
            'H5_opened': False, 'codec_decode_performed': False, 'source_HTTP_requests': 0,
            'median_function_called': False, 'median_rank_certification_only': True,
            'raw_row_authentication_limit': 'Saved NPY cells match original pilot decoded-row SHA pins; no independent codec/source re-decode.',
            'saved_detector_score_limit': 'Saved score values and original rank lists are integrity-checked; detector scores are not independently recomputed.',
            'whole_original_source_file_MD5_verified': False,
            'no_sky_classification_or_calibrated_statistics': True, **summary, **measured}
        terminal = out / 'QA_RECEIPT.json'
        pending = prepare_json(terminal, receipt)
        final = check_caps(out, shared, 65536)
        require(final['process_CPU_seconds_including_imports'] + .1 < 60
                and final['wall_seconds_since_module_clock'] + 2 < 1800, 'Finite QA terminal headroom required')
        signal.alarm(0)
        signal.signal(signal.SIGXCPU, signal.SIG_IGN)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGXCPU, signal.SIGINT, signal.SIGTERM, signal.SIGHUP})
        try:
            os.link(pending, terminal)
            committed = True
            pending.unlink()
            fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
    except BaseException as error:
        if owned and not committed:
            failure = stage / 'FAILURE_RECEIPT.json'
            publish(failure, prepare_json(failure, {'status': 'FAILED_SAVED_PILOT_QA_NO_RETRY',
                'error_type': type(error).__name__, 'error': str(error), 'qa_public_freeze_commit': args.qa_freeze_commit,
                'input_manifest_sha256': args.expected_input_manifest_sha256, **usage()}))
        raise
    finally:
        signal.alarm(0)
        for fd in reversed(guards):
            os.close(fd)


if __name__ == '__main__':
    main()
