"""Fixed context for nine OFF-primary winners; no science at import/preparation.

Every selected carrier, drift, width, first-midpoint epoch and 4096-channel
normalization core remains unchanged. Six original pointings provide context,
not independent repeats of any one target. Absolute source-channel mapping is
rounded only after combining carrier and drift. No grid or refit occurs here.
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

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'analysis/off_adjacent_20261011_context'
DETECTOR = 'analysis/new_visit_search/dependencies/detector.py'
READER = 'analysis/new_visit_search/dependencies/standard_reader.py'
SOURCE171 = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
SOURCE_ADJACENT = 'analysis/s2017_next_native/source_manifest_v2.json'
ACQ171 = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ACQ_ADJACENT = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
TARGETS = {'epoch1_off': 'HIP97319', 'epoch2_off': 'HIP97461', 'epoch3_off': 'HIP97663'}
COUNT, CORE, HALO = 1048576, 4096, 4000
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
REFERENCE_LINE_HZ = 2300390625.0
DETECTOR_SHA = '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45'
READER_SHA = '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def pin(path, root):
    path = Path(path)
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.resolve().is_relative_to(root), 'Confined relative project path required')
    return path


def source_metadata(root):
    s171, adjacent = read(root / SOURCE171), read(root / SOURCE_ADJACENT)
    acquisitions = {171: read(root / ACQ171), 170: read(root / ACQ_ADJACENT),
                    172: read(root / ACQ_ADJACENT)}
    records, items = {}, {}
    for native in (170, 171, 172):
        source = s171 if native == 171 else adjacent['by_native_chunk'][str(native)]
        require([item['label'] for item in source['sources']] == list(SCANS), 'Source order differs')
        for item in source['sources']:
            label = item['label']
            items[(native, label)] = item
            candidates = [r for r in acquisitions[native]['decoded_files'] if r['scan_id'] == label
                          and (native == 171 or r['native_chunk_index'] == native)]
            require(len(candidates) == 1, 'Unique compact source record required')
            record = candidates[0]
            require(record['shape'] == [16, 1, COUNT] and record['source_channel0'] == native * COUNT
                    and [r['time_row'] for r in record['decoded_rows']] == list(range(16)),
                    'Source shape/channels/rows differ')
            folder = 'analysis/new_visit_recovery/results/acquire' if native == 171 else 'analysis/s2017_next_native/results/acquire'
            records[(native, label)] = (record, confined(root, folder + '/' + record['array_file']))
            h = item['current_header']['data_attributes']
            require(h['fch1'] * 1e6 == FCH1 and h['foff'] * 1e6 == DF and h['tsamp'] == TSAMP,
                    'Source frequency/time grid differs')
            require(item['role'].upper() == ('ON' if label.endswith('_on') else 'OFF'),
                    'Original source acquisition role differs')
            require(h == items[(170, label)]['current_header']['data_attributes'],
                    'Header attributes differ across frequency pieces of same scan')
    headers = {label: items[(171, label)]['current_header']['data_attributes'] for label in SCANS}
    previous = -math.inf
    for label in SCANS:
        h = headers[label]
        require(h['tstart'] >= previous, 'Original cadence is not chronological/nonoverlapping')
        previous = h['tstart'] + 16 * TSAMP / 86400
    for label, target in TARGETS.items():
        require(headers[label]['source_name'] == target, 'Original OFF-primary identity differs')
    return records, items, headers


def normalize_tracks(tops, headers):
    """Accept actual producer's explicit TOP3 records; never rerank here."""
    selected = []
    for top in tops:
        records = top['records']
        require(len(records) == 3, 'Exactly three saved primary winners required')
        for rank, track in enumerate(records, 1):
            origin = track['scan_id']
            native, q = track['native_chunk_index'], track['core_q']
            require(origin in TARGETS and track['primary_target'] == TARGETS[origin] and
                    track['original_acquisition_role'] == 'OFF' and track['rank'] == rank,
                    'OFF-primary selected-track identity/rank differs')
            require(type(q) is int and ((native == 170 and 1 <= q <= 255) or
                    (native == 171 and q in (0, 255)) or (native == 172 and 0 <= q <= 254)),
                    'Selected track outside admitted native/core family')
            require(type(track['carrier_index_in_core']) is int and 0 <= track['carrier_index_in_core'] < CORE,
                    'Selected carrier outside declared core')
            channel = native * COUNT + q * CORE + track['carrier_index_in_core']
            require(track['reference_source_channel'] == channel and
                    track['frequency_hz_at_own_first_midpoint'] == FCH1 + DF * channel and
                    track['reference_time_mjd'] == headers[origin]['tstart'] + TSAMP / (2 * 86400),
                    'Selected absolute carrier/frequency/reference epoch differs')
            di = track['drift_grid_index']
            require(type(di) is int and 0 <= di <= 784 and
                    math.isclose(track['drift_hz_s'], -4 + di * 8 / 784, rel_tol=0, abs_tol=2e-15) and
                    track['width_channels'] in (1, 3) and math.isfinite(track['score']),
                    'Selected detector grid/width/score differs')
            selected.append(track)
    require(len(selected) == 9 and sorted([t['scan_id'] for t in selected]) == sorted(list(TARGETS) * 3),
            'Nine selected tracks across exactly three OFF primaries required')
    return selected


def prepare(root, producer_driver, producer_scope, primary_dirs):
    records, items, headers = source_metadata(root)
    require(digest(root / DETECTOR) == DETECTOR_SHA and digest(root / READER) == READER_SHA,
            'Original detector/reader bytes changed')
    inputs = [SOURCE171, SOURCE_ADJACENT, ACQ171, ACQ_ADJACENT, DETECTOR, READER,
              producer_driver, producer_scope]
    tops = []
    primary_receipts = []
    for folder in primary_dirs:
        for name in ('EXECUTION_RECEIPT.json', 'TOP3.json', 'TOP20.json'):
            inputs.append(folder + '/' + name)
        receipt = read(root / folder / 'EXECUTION_RECEIPT.json')
        require(receipt['status'] == 'COMPLETE_512_NEW_ORIGINAL_OFF_MAPS_EXPLORATORY_ONLY' and
                receipt['counts']['maps'] == 512, 'Primary numerical outputs are not COMPLETE512')
        require(receipt['driver_sha256'] == digest(root / producer_driver), 'Receipt producer differs')
        require(receipt['scope_sha256'] == digest(root / producer_scope), 'Receipt scope differs')
        top3, top20 = read(root / folder / 'TOP3.json'), read(root / folder / 'TOP20.json')
        output_pins = {rec['path']: rec for rec in receipt['output_byte_pins']}
        for name in ('TOP3.json', 'TOP20.json'):
            actual = pin(root / folder / name, root)
            require(output_pins.get(actual['path']) == actual, 'Saved rank list not bound by primary receipt')
        require(top3['records'] == top20['records'][:3], 'TOP3 does not match saved first three TOP20')
        for track in top3['records']:
            norm = folder + '/' + track['map_id'] + '_normalization.json'
            actual = pin(root / norm, root)
            require(output_pins.get(norm) == actual, 'Selected primary normalization not bound by receipt')
            inputs.append(norm)
        tops.append(top3)
        primary_receipts.append(receipt)
    tracks = normalize_tracks(tops, headers)
    source_files = [pin(path, root) for _, path in records.values()]
    for key, (record, path) in records.items():
        actual = next(p for p in source_files if p['path'] == path.relative_to(root).as_posix())
        require(actual['sha256'] == record['file_sha256'] and actual['bytes'] == record['bytes'],
                'Retained compact source bytes differ from original acquisition')
    scope = {'schema': 'SETI_OFF_ADJACENT_FIXED_CONTEXT_SCOPE_V1',
             'status': 'PREPARED_FROM_ACTUAL_COMPLETED_PRIMARY_OUTPUTS',
             'producer_driver': producer_driver, 'producer_scope': producer_scope,
             'primary_dirs': primary_dirs, 'selected_tracks': tracks,
             'input_pins': [pin(root / name, root) for name in inputs],
             'source_files': source_files, 'context_code_sha256': digest(Path(__file__)),
             'scan_order': list(SCANS), 'context_profiles': 54, 'raw_profile_columns': 503,
             'normalization_core_channels': CORE, 'normalization_halo_channels': HALO,
             'running_median_channels': 501, 'rounding': 'full absolute carrier+drift mapping before offset subtraction',
             'reference': 'each selected primary scan first integration midpoint; actual starts and gaps',
             'new_fit_or_detector_grid': False, 'new_observation': False, 'calibrated_SNR_FAP': False,
             'score_match_ATOL': 1e-7, 'score_match_RTOL': 1e-10,
             'CPU_limit_s': 300, 'wall_limit_s': 600, 'memory_limit_bytes': 2 * 1024**3}
    return scope


def run(root, scope, out):
    import numpy as np
    detector = module('off_adjacent_context_detector', root / DETECTOR)
    reader = module('off_adjacent_context_reader', root / READER)
    h5py, _, _ = reader.current_codecs()
    records, items, headers = source_metadata(root)
    selected = scope['selected_tracks']
    profiles, verified = [], []
    cfg, rows = detector.Config(widths=(1, 3)), np.arange(16)
    band_start = 170 * COUNT
    reference_channel = int(np.rint((REFERENCE_LINE_HZ - FCH1) / DF))
    for label in SCANS:
        pieces = []
        for native in (170, 171, 172):
            record, path = records[(native, label)]
            require(path.stat().st_size == record['bytes'] and digest(path) == record['file_sha256'],
                    'Compact source pin differs at context execution')
            with h5py.File(path, 'r', rdcc_nbytes=8 * 1024**2) as handle:
                data = handle['data']
                item = items[(native, label)]
                require(data.shape == (16, 1, COUNT) and data.dtype.str == '<f4' and
                        int(data.attrs['original_source_frequency_chunk_origin']) == native * COUNT and
                        data.attrs['original_source_url'] == item['url'] and
                        data.attrs['original_source_etag'] == item['etag'], 'Compact source provenance differs')
                values = data[:, 0, :]
            require(np.isfinite(values).all() and np.all(values >= 0), 'Invalid source power')
            for row in record['decoded_rows']:
                require(hashlib.sha256(values[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'],
                        'Original decoded source-row SHA differs')
            pieces.append(values)
            verified.append({'native_chunk_index': native, 'scan_id': label,
                             'file_sha256': record['file_sha256'], 'decoded_rows_verified': 16})
        power = np.concatenate(pieces, axis=1)
        del pieces, values
        cache = {}
        for track in selected:
            native, q, width, origin = (track[k] for k in ('native_chunk_index', 'core_q', 'width_channels', 'scan_id'))
            core0 = native * COUNT + q * CORE
            crop0, cropstop = core0 - HALO, core0 + CORE + HALO
            require(band_start <= crop0 < cropstop <= 173 * COUNT,
                    'Selected normalization crop outside contiguous acquired band')
            key = (native, q)
            if key not in cache:
                channels = np.arange(core0, core0 + CORE, dtype=np.int64)
                raw = power[:, crop0 - band_start:cropstop - band_start]
                scan = detector.Scan(label, 'ON' if label.endswith('_on') else 'OFF', raw,
                                     headers[label]['tstart'], TSAMP, FCH1, DF, crop0, channels)
                cache[key] = detector.preprocess(scan, cfg)
            z, mask, normalization = cache[key]
            if origin == label:
                folder = next(folder for folder in scope['primary_dirs'] if
                              read(root / folder / 'TOP3.json')['scan_id'] == origin)
                primary_normalization = read(root / folder / (track['map_id'] + '_normalization.json'))
                compact = dict(normalization)
                require(compact.pop('normalization_source_channels') == list(range(core0, core0 + CORE)),
                        'Original selected normalization channels changed')
                compact['normalization_source_channel_interval_half_open'] = [core0, core0 + CORE]
                require(compact == primary_normalization, 'Origin unchanged normalization differs from saved primary')
            # Identical integration lengths: midpoint halves cancel in this difference.
            times = (headers[label]['tstart'] - headers[origin]['tstart']) * 86400 + rows * TSAMP
            base = (track['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
            centers = np.rint(base + track['drift_hz_s'] * times / DF).astype(np.int64)
            local = centers - crop0
            require(np.all(local - 251 >= 0) and np.all(local + 251 < CORE + 2 * HALO),
                    'Fixed track lacks full503/filter support in selected unchanged crop')
            box = local[:, None] + np.arange(-(width // 2), width // 2 + 1)[None, :]
            require(mask[rows[:, None], box].all(), 'Fixed track box unexpectedly masked')
            terms = z[rows[:, None], box].sum(axis=1, dtype=np.float64)
            row_score = terms / np.sqrt(16 * width)
            score = float(terms.sum(dtype=np.float64) / np.sqrt(16 * width))
            require(math.isfinite(score), 'Non-finite fixed context score')
            own = origin == label
            if own:
                require(math.isclose(score, track['score'], rel_tol=1e-10, abs_tol=1e-7),
                        'Origin direct context score does not reconcile with actual primary winner')
            profile_id = f"{track['primary_target']}_rank{track['rank']}_{label}"
            indices = centers[:, None] - band_start + np.arange(-251, 252)[None, :]
            capsule = power[rows[:, None], indices].copy()
            capsule_path = out / (profile_id + '_raw503.npz')
            with capsule_path.open('xb') as stream:
                np.savez(stream, raw_power=capsule, rounded_absolute_centers=centers,
                         times_from_primary_reference_s=times, row_standardized_box_sum=terms,
                         row_score_contribution=row_score)
            norm_path = out / (profile_id + '_normalization.json')
            save(norm_path, normalization)
            hit = np.abs(centers - reference_channel) <= width // 2
            positive = np.maximum(row_score, 0)
            total_positive = float(positive.sum())
            dominant = int(np.argmax(positive))
            profiles.append({'profile_id': profile_id, 'selected_track': track,
                             'context_scan_id': label, 'context_target': headers[label]['source_name'],
                             'original_acquisition_role': 'ON' if label.endswith('_on') else 'OFF',
                             'reference_time_mjd': track['reference_time_mjd'],
                             'times_from_primary_reference_s': times.tolist(),
                             'row_midpoint_mjd': [headers[label]['tstart'] + (j + .5) * TSAMP / 86400 for j in range(16)],
                             'rounded_absolute_centers': centers.tolist(),
                             'rounded_center_frequency_hz': (FCH1 + DF * centers).tolist(),
                             'row_standardized_box_sum': terms.tolist(),
                             'row_score_contribution': row_score.tolist(),
                             'fixed_robust_box_track_score': score,
                             'origin_primary_score': track['score'] if own else None,
                             'origin_primary_score_difference': score - track['score'] if own else None,
                             'positive_row_contribution_max_fraction': float(positive[dominant] / total_positive) if total_positive else None,
                             'dominant_positive_row': dominant if total_positive else None,
                             'reference2300_line_box_overlap_rows': np.flatnonzero(hit).tolist(),
                             'reference2300_line_overlap_positive_contribution_fraction': float(positive[hit].sum() / total_positive) if total_positive else None,
                             'raw_capsule': pin(capsule_path, root), 'normalization': pin(norm_path, root)})
            print('CONTEXT', profile_id, f'{score:.8g}', flush=True)
        del cache, power
    profiles.sort(key=lambda p: (list(TARGETS).index(p['selected_track']['scan_id']),
                                 p['selected_track']['rank'], SCANS.index(p['context_scan_id'])))
    require(len(profiles) == 54 and sum(p['origin_primary_score'] is not None for p in profiles) == 9,
            'Expected54 contexts and9 origin reconciliations')
    matrix = {'schema': 'SETI_OFF_ADJACENT_FIXED_CONTEXT_PROFILES_V1',
              'status': 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES',
              'selected_tracks': selected, 'profiles': profiles, 'source_verification': verified,
              'counts': {'selected_tracks': 9, 'context_profiles': 54, 'origin_score_matches': 9,
                         'source_files_verified': 18, 'source_rows_verified': 288,
                         'raw503_profile_cells': 54 * 16 * 503},
              'known_reference_line_hz': REFERENCE_LINE_HZ,
              'known_reference_line_rounded_absolute_channel': reference_channel,
              'selection_after_primary_search': True, 'new_fit_or_detector_grid': False,
              'new_observation': False, 'same_target_independent_repeat': False,
              'ON_OFF_veto_applied': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
              'interpretation': 'Fixed other directions/times are descriptive context. Different OFF targets and HIP98505 ON pointings are not repetitions of an OFF-primary target. The reference2300 overlap is geometry only and does not classify unrelated frequencies as aliases.'}
    save(out / 'CONTEXT_PROFILES.json', matrix)
    return matrix


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--producer-driver')
    p.add_argument('--producer-scope')
    p.add_argument('--primary-dirs', nargs=3)
    p.add_argument('--scope', default=BASE + '/context_scope.json')
    p.add_argument('--scope-sha256')
    p.add_argument('--root-go')
    args = p.parse_args()
    root = args.root.resolve()
    scope_path = confined(root, args.scope)
    if args.prepare:
        require(args.producer_driver and args.producer_scope and args.primary_dirs, 'Actual producer/input paths required')
        scope = prepare(root, args.producer_driver, args.producer_scope, args.primary_dirs)
        save(scope_path, scope)
        print(json.dumps({'status': scope['status'], 'scope_sha256': digest(scope_path)}))
        return
    require(args.scope_sha256 and digest(scope_path) == args.scope_sha256, 'Actual fixed context scope SHA required')
    scope = read(scope_path)
    require(scope['context_code_sha256'] == digest(Path(__file__)), 'Prepared context producer changed')
    for expected in scope['input_pins'] + scope['source_files']:
        require(pin(root / expected['path'], root) == expected, 'Actual context prerequisite changed')
    require(args.root_go, 'Root execution GO after numerical results is required')
    go = read(confined(root, args.root_go))
    require(go['context_scope_sha256'] == args.scope_sha256 and go['status'].startswith('GO'), 'Root GO/scope differs')
    import resource
    import signal
    resource.setrlimit(resource.RLIMIT_CPU, (300, 301))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    def deadline(signum, frame):
        raise TimeoutError('Fixed context wall cap600s reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(600)
    started, cpu = time.monotonic(), time.process_time()
    out = root / BASE / 'results'
    out.mkdir(exist_ok=False)
    try:
        matrix = run(root, scope, out)
        for expected in scope['input_pins'] + scope['source_files']:
            require(pin(root / expected['path'], root) == expected, 'Fixed context input changed during execution')
        import h5py
        save(out / 'EXECUTION_RECEIPT.json', {'status': matrix['status'], 'context_scope_sha256': args.scope_sha256,
              'context_code_sha256': digest(Path(__file__)), 'counts': matrix['counts'],
              'primary_receipt_pins': [rec for rec in scope['input_pins'] if rec['path'].endswith('/EXECUTION_RECEIPT.json')],
              'actual_producer_pins': [rec for rec in scope['input_pins'] if rec['path'] in
                                       (scope['producer_driver'], scope['producer_scope'])],
              'runtime_versions': {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
                                   **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}},
              'wall_seconds': time.monotonic() - started, 'CPU_seconds': time.process_time() - cpu,
              'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
              'new_telescope_HTTP_requests': 0, 'new_observation': False, 'new_fit': False,
              'origin_score_match_ATOL': 1e-7, 'origin_score_match_RTOL': 1e-10,
              'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
              'output_pins': [pin(path, root) for path in sorted(out.iterdir()) if path.is_file()]})
    except BaseException as exc:
        if not (out / 'EXECUTION_RECEIPT.json').exists():
            save(out / 'EXECUTION_RECEIPT.json', {'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY',
                 'context_scope_sha256': args.scope_sha256, 'failure_type': type(exc).__name__, 'failure': str(exc)})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
