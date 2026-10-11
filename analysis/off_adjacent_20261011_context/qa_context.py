"""Independent raw503 arithmetic QA for the 54 saved fixed contexts.

Import and --check-only do not open source arrays or numerical outputs.
Root executes after review with --run and exact context-receipt/code hashes.
No detector, preprocessing grid, fitting or selection is rerun. MAD/location
are conditioned on the saved full-core normalization, explicitly documented.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'analysis/off_adjacent_20261011_context'
SOURCE171 = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
SOURCE_ADJACENT = 'analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
COUNT, CORE, BAND0 = 1048576, 4096, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
REFERENCE_LINE_HZ = 2300390625.0
ATOL, RTOL = 1e-7, 1e-10


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root), 'Confined relative path required')
    return path


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def read(path):
    return json.loads(path.read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def near(np, actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def run(root, args):
    started, cpu0 = time.monotonic(), time.process_time()
    receipt_path = root / BASE / 'results/EXECUTION_RECEIPT.json'
    require(digest(receipt_path) == args.contextreceipt_sha, 'Exact completed context receipt differs')
    receipt = read(receipt_path)
    require(receipt['status'] == 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES',
            '54 completed fixed contexts required')
    scope_path = root / BASE / 'context_scope.json'
    require(digest(scope_path) == receipt['context_scope_sha256'], 'Completed context scope differs')
    scope = read(scope_path)
    code_path = root / BASE / 'context_profiles.py'
    require(digest(code_path) == receipt['context_code_sha256'] == scope['context_code_sha256'],
            'Completed context producer differs')
    before = {}

    def checked(declaration):
        path = confined(root, declaration['path'])
        actual = pin(root, path)
        require(actual == declaration, 'Authenticated input pin differs: ' + declaration['path'])
        require(path not in before or before[path] == actual, 'Conflicting repeated input pin')
        before[path] = actual
        return path

    for declaration in scope['input_pins'] + scope['source_files'] + receipt['output_pins']:
        checked(declaration)
    for path in (receipt_path, scope_path, code_path, Path(__file__).resolve()):
        before[path] = pin(root, path)
    matrix_path = root / BASE / 'results/CONTEXT_PROFILES.json'
    require(matrix_path in before, 'Context matrix omitted from completed receipt')
    matrix = read(matrix_path)
    tracks, profiles = matrix['selected_tracks'], matrix['profiles']
    require(matrix['status'] == receipt['status'] and tracks == scope['selected_tracks']
            and len(tracks) == 9 and len(profiles) == 54, 'Saved fixed profile matrix differs')
    primary_top3 = [track for folder in scope['primary_dirs']
                    for track in read(root / folder / 'TOP3.json')['records']]
    require(tracks == primary_top3 and len({(t['scan_id'], t['rank']) for t in tracks}) == 9,
            'Actual saved primary TOP3 tracks changed in context')
    original, adjacent = read(root / SOURCE171), read(root / SOURCE_ADJACENT)
    acquisitions = {171: read(root / ACQ171), 170: read(root / ACQ_ADJACENT),
                    172: read(root / ACQ_ADJACENT)}
    source_records, identities = {}, {}
    for native in (170, 171, 172):
        source = original if native == 171 else adjacent['by_native_chunk'][str(native)]
        require([s['label'] for s in source['sources']] == list(SCANS), 'Original source order differs')
        for identity in source['sources']:
            label = identity['label']
            identities[native, label] = identity
            candidates = [r for r in acquisitions[native]['decoded_files']
                          if r['scan_id'] == label and (native == 171 or r['native_chunk_index'] == native)]
            require(len(candidates) == 1, 'Unique original compact record required')
            record = candidates[0]
            folder = Path(ACQ171 if native == 171 else ACQ_ADJACENT).parent
            path = confined(root, (folder / record['array_file']).as_posix())
            require(record['shape'] == [16, 1, COUNT] and record['source_channel0'] == native * COUNT
                    and [r['time_row'] for r in record['decoded_rows']] == list(range(16)),
                    'Original source compact shape/rows differ')
            require(path in before and before[path]['bytes'] == record['bytes']
                    and before[path]['sha256'] == record['file_sha256'], 'Original source file identity differs')
            source_records[native, label] = record, path
    headers = {s['label']: s['current_header']['data_attributes'] for s in original['sources']}
    for (native, label), identity in identities.items():
        h = identity['current_header']['data_attributes']
        require(h == headers[label] and h['fch1'] * 1e6 == FCH1 and h['foff'] * 1e6 == DF
                and h['tsamp'] == TSAMP and identity['url'] == identities[171, label]['url']
                and identity['etag'] == identities[171, label]['etag']
                and identity['role'].upper() == ('ON' if label.endswith('_on') else 'OFF'),
                'Original across-band header/role/source identity differs')
    previous = float('-inf')
    for label in SCANS:
        require(headers[label]['tstart'] >= previous, 'Chronological physical integration gaps differ')
        previous = headers[label]['tstart'] + 16 * TSAMP / 86400
    # Initialize the ordinary supported codec after root execution admission.
    import numpy as np
    import h5py
    import hdf5plugin
    require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008),
            'Supported original bitshuffle decoder unavailable')
    runtime = {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
               **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}}
    require(runtime == receipt['runtime_versions'], 'Completed context/independent QA runtime differs')
    reference_channel = int(np.rint((REFERENCE_LINE_HZ - FCH1) / DF))
    require(matrix['known_reference_line_hz'] == REFERENCE_LINE_HZ
            and matrix['known_reference_line_rounded_absolute_channel'] == reference_channel == 179830784,
            'Declared reference2300 physical channel differs')
    counts = {'source_files': 0, 'source_decoded_rows': 0, 'profiles': 0,
              'row_box_sums': 0, 'scores': 0, 'own_primary_score_matches': 0,
              'raw503_source_cells': 0, 'raw_core_row_medians': 0,
              'contribution_diagnostic_profiles': 0}
    seen, max_row_difference, max_score_difference = set(), 0., 0.
    for label in SCANS:
        joined = np.empty((16, 3 * COUNT), dtype='<f4')
        for native in (170, 171, 172):
            record, path = source_records[native, label]
            identity = identities[native, label]
            with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                data = handle['data']
                require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4'
                        and int(data.attrs['original_source_frequency_chunk_origin']) == native * COUNT
                        and data.attrs['original_source_url'] == identity['url']
                        and data.attrs['original_source_etag'] == identity['etag'],
                        'Actual compact source provenance differs')
                for row in record['decoded_rows']:
                    values = data[row['time_row'], 0, :]
                    require(np.isfinite(values).all() and (values >= 0).all()
                            and row['decoded_bytes'] == COUNT * 4
                            and hashlib.sha256(values.tobytes()).hexdigest() == row['decoded_sha256'],
                            'Actual source float32 decoded row differs')
                    joined[row['time_row'], (native - 170) * COUNT:(native - 169) * COUNT] = values
                    counts['source_decoded_rows'] += 1
            counts['source_files'] += 1
        for profile in (p for p in profiles if p['context_scan_id'] == label):
            track = profile['selected_track']
            require(track in tracks and profile['profile_id'] == '%s_rank%d_%s' %
                    (track['primary_target'], track['rank'], label), 'Fixed profile identity differs')
            key = track['scan_id'], track['rank'], label
            require(key not in seen, 'Duplicate fixed profile')
            seen.add(key)
            origin, native, q, width = (track[k] for k in ('scan_id', 'native_chunk_index', 'core_q', 'width_channels'))
            require(origin in headers and origin.endswith('_off') and width in (1, 3), 'Primary role/width differs')
            core0 = native * COUNT + q * CORE
            require(track['reference_source_channel'] == core0 + track['carrier_index_in_core']
                    and track['frequency_hz_at_own_first_midpoint'] == FCH1 + DF * track['reference_source_channel']
                    and track['reference_time_mjd'] == headers[origin]['tstart'] + TSAMP / (2 * 86400),
                    'Actual primary carrier/first-midpoint reference differs')
            times = (headers[label]['tstart'] - headers[origin]['tstart']) * 86400 + np.arange(16) * TSAMP
            centers = np.rint((track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
                              + track['drift_hz_s'] * times / DF).astype(np.int64)
            offsets = centers[:, None] - BAND0 + np.arange(-251, 252)[None, :]
            require(offsets.min() >= 0 and offsets.max() < 3 * COUNT, 'Raw503 source support outside retained triplet')
            raw = joined[np.arange(16)[:, None], offsets]
            capsule_path, norm_path = checked(profile['raw_capsule']), checked(profile['normalization'])
            with np.load(capsule_path, allow_pickle=False) as capsule:
                require(set(capsule.files) == {'raw_power', 'rounded_absolute_centers',
                        'times_from_primary_reference_s', 'row_standardized_box_sum', 'row_score_contribution'},
                        'Raw503 fixed profile capsule fields differ')
                arrays = {name: capsule[name] for name in capsule.files}
            require(arrays['raw_power'].shape == (16, 503) and arrays['raw_power'].dtype.str == '<f4'
                    and np.array_equal(arrays['raw_power'].view(np.uint32), raw.view(np.uint32)),
                    'Saved raw503 float32 source bits differ')
            require(arrays['rounded_absolute_centers'].dtype.str == '<i8'
                    and np.array_equal(arrays['rounded_absolute_centers'], centers)
                    and np.array_equal(profile['rounded_absolute_centers'], centers)
                    and np.array_equal(arrays['times_from_primary_reference_s'], times)
                    and np.array_equal(profile['times_from_primary_reference_s'], times),
                    'Actual timestamp gap/absolute rounding differs')
            require(np.array_equal(profile['row_midpoint_mjd'],
                    [headers[label]['tstart'] + (r + .5) * TSAMP / 86400 for r in range(16)])
                    and np.array_equal(profile['rounded_center_frequency_hz'], FCH1 + DF * centers)
                    and profile['reference_time_mjd'] == track['reference_time_mjd']
                    and profile['context_target'] == headers[label]['source_name']
                    and profile['original_acquisition_role'] == ('ON' if label.endswith('_on') else 'OFF'),
                    'Physical context row time/frequency/direction differs')
            normal = read(norm_path)
            require(normal['normalization_source_channels'] == list(range(core0, core0 + CORE))
                    and normal['normalization_unmasked_counts'] == [CORE] * 16,
                    'Full declared unmasked4096 normalization core differs')
            for field in ('row_power_median', 'row_residual_median',
                          'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                a = np.asarray(normal[field])
                require(a.shape == (16,) and np.isfinite(a).all(), 'Saved16row normalization invalid')
            require((np.asarray(normal['row_power_median']) > 0).all()
                    and (np.asarray(normal['row_residual_MAD_scale']) > 0).all(), 'Saved normalization scale invalid')
            core = joined[:, core0 - BAND0:core0 + CORE - BAND0].astype(np.float64)
            require(core.shape == (16, CORE) and np.array_equal(np.median(core, axis=1), normal['row_power_median']),
                    'Independent fullcore raw power median differs')
            ratio = raw.astype(np.float64) / np.asarray(normal['row_power_median'])[:, None]
            columns = list(range(251 - width // 2, 252 + width // 2))
            medians = np.column_stack([np.median(ratio[:, c - 250:c + 251], axis=1) for c in columns])
            z = (ratio[:, columns] - medians - np.asarray(normal['row_winsorized_residual_location'])[:, None]) / np.asarray(
                normal['row_residual_MAD_scale'])[:, None]
            row_sums = z.sum(axis=1, dtype=np.float64)
            row_score = row_sums / np.sqrt(16 * width)
            score = float(row_sums.sum(dtype=np.float64) / np.sqrt(16 * width))
            near(np, arrays['row_standardized_box_sum'], row_sums, 'Independent local501 row box differs from capsule')
            near(np, profile['row_standardized_box_sum'], row_sums, 'Independent local501 row box differs from matrix')
            near(np, arrays['row_score_contribution'], row_score, 'Independent row score differs from capsule')
            near(np, profile['row_score_contribution'], row_score, 'Independent row score differs from matrix')
            near(np, profile['fixed_robust_box_track_score'], score, 'Independent context score differs')
            # Report diagnostics are arithmetic/geometry of these same fixed rows.
            overlap = np.abs(centers - reference_channel) <= width // 2
            require(profile['reference2300_line_box_overlap_rows'] == np.flatnonzero(overlap).tolist(),
                    'Independent reference2300 rounded-box overlap rows differ')
            positive = np.maximum(row_score, 0.)
            total_positive = float(positive.sum())
            if total_positive:
                dominant = int(np.argmax(positive))
                require(profile['dominant_positive_row'] == dominant
                        and profile['positive_row_contribution_max_fraction'] is not None
                        and profile['reference2300_line_overlap_positive_contribution_fraction'] is not None,
                        'Independent dominant positive row or defined fraction differs')
                near(np, profile['positive_row_contribution_max_fraction'],
                     float(positive[dominant] / total_positive), 'Independent dominant-row positive fraction differs')
                near(np, profile['reference2300_line_overlap_positive_contribution_fraction'],
                     float(positive[overlap].sum() / total_positive),
                     'Independent reference2300 positive-contribution fraction differs')
            else:
                require(profile['dominant_positive_row'] is None
                        and profile['positive_row_contribution_max_fraction'] is None
                        and profile['reference2300_line_overlap_positive_contribution_fraction'] is None,
                        'Undefined zero-positive contribution diagnostics must be null')
            counts['contribution_diagnostic_profiles'] += 1
            if origin == label:
                folder = next(f for f in scope['primary_dirs'] if read(root / f / 'TOP3.json')['scan_id'] == origin)
                primary_norm = read(root / folder / (track['map_id'] + '_normalization.json'))
                compact = dict(normal)
                compact.pop('normalization_source_channels')
                compact['normalization_source_channel_interval_half_open'] = [core0, core0 + CORE]
                require(compact == primary_norm, 'Own context normalization differs from saved primary normalization')
                near(np, score, track['score'], 'Independent own profile score differs from primary winner')
                near(np, profile['origin_primary_score'], track['score'], 'Own primary score metadata differs')
                near(np, profile['origin_primary_score_difference'], profile['fixed_robust_box_track_score'] - track['score'],
                     'Own score difference metadata differs')
                counts['own_primary_score_matches'] += 1
            else:
                require(profile['origin_primary_score'] is None and profile['origin_primary_score_difference'] is None,
                        'Other-direction profile relabelled as an own primary match')
            max_row_difference = max(max_row_difference, float(np.max(np.abs(arrays['row_standardized_box_sum'] - row_sums))))
            max_score_difference = max(max_score_difference, abs(score - profile['fixed_robust_box_track_score']))
            counts['profiles'] += 1
            counts['row_box_sums'] += 16
            counts['scores'] += 1
            counts['raw503_source_cells'] += 16 * 503
            counts['raw_core_row_medians'] += 16
        del joined
    require(seen == {(t['scan_id'], t['rank'], label) for t in tracks for label in SCANS},
            'Exact nine-track by six-scan context matrix incomplete')
    expected = {'source_files': 18, 'source_decoded_rows': 288, 'profiles': 54,
                'row_box_sums': 864, 'scores': 54, 'own_primary_score_matches': 9,
                'raw503_source_cells': 434592, 'raw_core_row_medians': 864,
                'contribution_diagnostic_profiles': 54}
    require(counts == expected, 'Independent context QA counts differ')
    for path, declaration in before.items():
        require(pin(root, path) == declaration, 'Source/context/input changed during independent QA')
    cpu, wall = time.process_time() - cpu0, time.monotonic() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    require(cpu <= 300 and wall <= 600 and rss <= 2 * 1024**3, 'Independent context QA resource cap exceeded')
    result = {'schema': 'SETI_OFF_ADJACENT_INDEPENDENT_FIXED_CONTEXT_QA_V1',
              'status': 'PASS54_FIXED_CONTEXTS864_ROW_BOXES54_SCORES9_OWN_MATCHES288_SOURCE_ROWS',
              'counts': counts, 'context_receipt': pin(root, receipt_path),
              'context_scope': pin(root, scope_path), 'qa_code': pin(root, Path(__file__).resolve()),
              'before_and_after_input_pins': list(before.values()), 'runtime_versions': runtime,
              'max_row_box_absolute_difference': max_row_difference,
              'max_score_absolute_difference': max_score_difference,
              'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
              'CPU_seconds': cpu, 'wall_seconds': wall, 'peak_RSS_bytes': rss,
              'CPU_cap_s': 300, 'wall_cap_s': 600, 'memory_cap_bytes': 2 * 1024**3,
              'detector_imported': False, 'full_grid_recomputed': False,
              'raw_source_bits_and_timestamp_gaps_independently_verified': True,
              'positive_contribution_and_reference2300_overlap_diagnostics_independently_verified': True,
              'full_core_power_row_medians_independently_recomputed': True,
              'full_core_MAD_location_independently_refiltered': False,
              'new_telescope_HTTP_requests': 0, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
              'limitations': ['Independent local501 arithmetic is conditional on the saved fullcore MAD/location.',
                              'Fixed other directions/times are descriptive context, not independent repeated observations.',
                              'No exhaustive drift/width maximization or sky false-alarm/origin calibration.']}
    save(root / BASE / 'CONTEXT_QA_RECEIPT.json', result)
    print(json.dumps({'status': result['status'], 'counts': counts}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--contextreceipt-sha')
    p.add_argument('--qa-sha')
    p.add_argument('--run', action='store_true')
    p.add_argument('--check-only', action='store_true')
    args = p.parse_args()
    if args.check_only:
        print(json.dumps({'status': 'PASS_STATIC_CONTEXT_QA_INTERFACE_NO_OUTPUT_OR_SOURCE_VALUES',
                          'qa_sha256': digest(Path(__file__).resolve()), 'numerical_modules_imported': False}))
        return
    require(args.run and args.contextreceipt_sha and args.qa_sha == digest(Path(__file__).resolve()),
            'Root --run with exact context receipt and QA source hash required')
    resource.setrlimit(resource.RLIMIT_CPU, (300, 301))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('Independent context QA wall cap600s')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(600)
    try:
        run(args.root.resolve(), args)
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
