"""Independent fixed54 context QA; no detector import or search/maximization.

Check-only imports no numerical modules and opens no spectral values. A separate
root QA GO, primary PASS QA, completed context receipt, and exact frozen hashes
are required for numerical execution. All fullcore normalization parameters are
recomputed by direct501 sliding medians, then all fixed16row profiles audited.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE = 'seti_burst_on'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ORIGINS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
JOBS = ('on20170428_epoch1_HIP98505', 'on20170428_epoch2_HIP98505', 'on20170428_epoch3_HIP98505')
COUNT, CORE, HALO, BAND0 = 1048576, 4096, 4000, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
ATOL, RTOL = 1e-7, 1e-10
CPU_CAP, WALL_CAP, MEMORY_CAP, OUTPUT_CAP = 600, 900, 2 * 1024**3, 4 * 1024**2
STATUS = 'COMPLETE_NINE_ON_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
METADATA_NAMES = ('burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json',
                  'burst_previous/analysis/s2017_next_native/source_manifest_v2.json',
                  'burst_previous/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json',
                  'burst_previous/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def unique_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root) and not path.is_symlink(), 'Confined relative input required')
    return path


def create_json(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())


def equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b), message)


def near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def recompute_normal(raw):
    """Batch256 direct501 medians, all4096 core channels and all16rows."""
    require(raw.shape == (16, 12096) and raw.dtype == np.dtype('<f4'), 'Raw normal crop differs')
    power = raw[:, HALO - 250:HALO + CORE + 250].astype(np.float64)
    level = np.median(power[:, 250:250 + CORE], axis=1)
    residual = np.empty((16, CORE), dtype=np.float64)
    for row in range(16):
        ratio = power[row] / level[row]
        windows = np.lib.stride_tricks.sliding_window_view(ratio, 501)
        for start in range(0, CORE, 256):
            stop = min(start + 256, CORE)
            residual[row, start:stop] = ratio[250 + start:250 + stop] - np.median(windows[start:stop], axis=1)
    center = np.median(residual, axis=1)
    scale = 1.4826 * np.median(np.abs(residual - center[:, None]), axis=1)
    location = center + np.mean(np.clip(residual - center[:, None], -5 * scale[:, None], 5 * scale[:, None]), axis=1)
    require(np.all(level > 0) and np.all(scale > 0), 'Independent scales invalid')
    return {'row_power_median': level, 'row_residual_median': center,
            'row_residual_MAD_scale': scale, 'row_winsorized_residual_location': location}


def recompute_rows(raw, normal, width):
    require(raw.shape == (16, 503) and raw.dtype == np.dtype('<f4') and width in (1, 3), 'Raw16x503/width differs')
    ratio = raw.astype(np.float64) / normal['row_power_median'][:, None]
    columns = list(range(251 - width // 2, 252 + width // 2))
    median = np.column_stack([np.median(ratio[:, c - 250:c + 251], axis=1) for c in columns])
    standardized = (ratio[:, columns] - median - normal['row_winsorized_residual_location'][:, None]) / normal['row_residual_MAD_scale'][:, None]
    return standardized.sum(axis=1)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--portable', action='store_true', help='Replay authenticated saved crops without original HDF5 compacts')
    parser.add_argument('--output-dir', help='Fresh workspace-relative QA output directory')
    for name in ('scope-sha256', 'qa-sha256', 'receipt-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.check_only:
        print(json.dumps({'status': 'PASS_TEXT_ONLY_CONTEXT_QA_INTERFACE', 'source_values_read': False,
                          'numerical_modules_imported': False, 'profiles_expected': 54,
                          'own_fourrow_scores_expected': 9, 'full501_normalization': 'every saved unique core in every sixscan context',
                          'root_go_path': BASE + '/CONTEXT_QA_GO.json'}))
        return
    for sha in (args.scope_sha256, args.qa_sha256, args.receipt_sha256, args.root_go_sha256):
        require(sha is not None and re.fullmatch('[0-9a-f]{64}', sha), 'Exact SHA256s required')
    require(digest(Path(__file__).resolve()) == args.qa_sha256, 'QA source differs')
    run(Path(args.root).resolve(), args)


def run(root, args):
    started, pins, locks = time.monotonic(), {}, []
    output_name = args.output_dir or BASE + ('/context_portable_replay' if args.portable else '/context_qa_results')
    out = confined(root, output_name)
    require(out != root and not any(out == root / BASE / name for name in
                ('results', 'context_results', 'qa_results')), 'Separate fresh QA output required')
    created_output = False
    counts = {'context_profiles': 0, 'origin_score_matches': 0, 'source_files': 0, 'source_rows': 0,
              'raw_normalization_crops': 0, 'raw_profile_cells': 0, 'full501_normalization_rows': 0,
              'four_row_scores': 0, 'full16_scores': 0, 'row_box_terms': 0}
    normal_reports, score_reports = [], []
    max_normal_error = max_row_error = max_score_error = 0.0

    def loaded(path, pin=None):
        raw = path.read_bytes()
        current = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        require(pin is None or current == {k: pin[k] for k in ('bytes', 'sha256')}, 'Input pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        require(name not in pins or pins[name] == current, 'Input changed')
        pins[name] = current
        return raw

    def metadata(path, sha=None):
        raw = loaded(path)
        require(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Metadata SHA differs')
        return decode(raw)

    def archive(pin):
        raw = loaded(confined(root, pin['path']), pin)
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            require(len(values.files) == len(set(values.files)), 'Duplicate NPZ member')
            return {key: values[key] for key in values.files}

    def alarm(signum, frame):
        raise TimeoutError('Independent context QA resource bound')

    try:
        go = metadata(root / BASE / 'CONTEXT_QA_GO.json', args.root_go_sha256)
        require(go['status'] == 'GO_INDEPENDENT_FIXED_ON_CONTEXT54_QA'
                and go['context_scope_sha256'] == args.scope_sha256
                and go['context_qa_sha256'] == args.qa_sha256
                and go['context_receipt_sha256'] == args.receipt_sha256
                and go['CPU_cap_s'] == CPU_CAP and go['wall_cap_s'] == WALL_CAP
                and go['memory_cap_bytes'] == MEMORY_CAP and go['output_cap_bytes'] == OUTPUT_CAP
                and re.fullmatch('[0-9a-f]{40}', go['context_public_freeze_commit']), 'Separate context QA rootGO differs')
        signal.signal(signal.SIGALRM, alarm)
        signal.signal(signal.SIGXCPU, alarm)
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
        signal.alarm(WALL_CAP)
        for name in ('SLOT0.lock', 'SLOT1.lock', 'CONTEXT_QA.lock'):
            handle = (root / BASE / name).open('a+b')
            locks.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        loaded(Path(__file__).resolve())
        scope = metadata(root / BASE / 'CONTEXT_SCOPE.json', args.scope_sha256)
        require(scope['context_qa_code'] == BASE + '/context_qa.py'
                and scope['context_qa_code_sha256'] == args.qa_sha256
                and scope['context_code_sha256'] == go['context_code_sha256']
                and scope['scan_order'] == list(SCANS) and scope['primary_origins'] == list(ORIGINS)
                and scope['context_profiles'] == 54 and scope['origin_primary_score_matches'] == 9
                and scope['raw_normalization_crop_shape'] == [16, 12096]
                and scope['raw_profile_shape'] == [16, 503] and scope['running_median_channels'] == 501
                and scope['new_fit_or_detector_grid'] is False and scope['protected2016_data_opened'] is False,
                'Frozen context scope differs')
        require(digest(root / BASE / 'context.py') == scope['context_code_sha256'], 'Producer context bytes differ')
        input_names = set()
        for pin in scope['input_pins']:
            require(pin['path'] not in input_names, 'Duplicate context scope pin')
            input_names.add(pin['path'])
            loaded(confined(root, pin['path']), pin)
        require(set(METADATA_NAMES).issubset(input_names), 'Missing scientific source metadata')
        # Independently reconstruct the18 source headers/decoded-row records.
        midpoint, adjacent, acq171, acqadj = [metadata(root / name) for name in METADATA_NAMES]
        sources = {(s['native_chunk_index'], s['scan_id']): s for s in scope['source_compacts']}
        require(len(sources) == len(scope['source_compacts']) == 18
                and set(sources) == {(n, scan) for n in (170, 171, 172) for scan in SCANS}, 'Source census differs')
        for key, source in sources.items():
            native, scan = key
            manifest = midpoint if native == 171 else adjacent['by_native_chunk'][str(native)]
            identity = next(s for s in manifest['sources'] if s['label'] == scan)
            original = next(s for s in midpoint['sources'] if s['label'] == scan)
            acquisition = acq171 if native == 171 else acqadj
            records = [r for r in acquisition['decoded_files'] if r['scan_id'] == scan
                       and (native == 171 or r['native_chunk_index'] == native)]
            require(len(records) == 1, 'Source acquisition identity differs')
            record = records[0]
            role = 'ON' if scan.endswith('_on') else 'OFF'
            require(source['original_header_full'] == identity['current_header'] == original['current_header']
                    and source['original_header'] == identity['current_header']['data_attributes']
                    and source['original_source_url'] == identity['url'] == original['url']
                    and source['original_source_etag'] == identity['etag'] == original['etag']
                    and source['original_acquisition_role'] == role == identity['role'].upper()
                    and source['shape'] == record['shape'] == [16, 1, COUNT]
                    and source['source_channel0'] == record['source_channel0'] == native * COUNT
                    and source['decoded_rows'] == record['decoded_rows']
                    and source['bytes'] == record['bytes'] and source['sha256'] == record['file_sha256'], 'Full source metadata differs')
            acquisition_name = METADATA_NAMES[2] if native == 171 else METADATA_NAMES[3]
            rawpath = Path('seti_raw') / Path(acquisition_name).relative_to('burst_previous').parent / record['array_file']
            require(source['path'] == rawpath.as_posix(), 'Raw compact path differs')
        primary_qa = metadata(root / BASE / 'qa_results' / 'QA_RECEIPT.json', go['primary_qa_receipt_sha256'])
        require(primary_qa['status'] == 'PASS288_ON_BURST4_MAPS1170_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN', 'Primary QA not PASS')
        expected_tracks = []
        for job, origin in zip(JOBS, ORIGINS):
            top = metadata(root / BASE / 'results' / job / 'DC_AWARE_TOP3.json')
            require(top['records'] == primary_qa['selected_top3'][job]['dc_aware'] and top['scan_id'] == origin, 'Track QA selection differs')
            expected_tracks.extend(top['records'])
        require(scope['selected_tracks'] == expected_tracks, 'Frozen nine selected tracks differ')
        receipt = metadata(root / BASE / 'context_results' / 'EXECUTION_RECEIPT.json', args.receipt_sha256)
        require(receipt['status'] == STATUS and receipt['context_scope_sha256'] == args.scope_sha256
                and receipt['context_code_sha256'] == scope['context_code_sha256']
                and receipt['new_fit_or_detector_grid'] is False and receipt['source_bytes_unchanged'] is True
                and receipt['new_telescope_HTTP_requests'] == 0, 'Context receipt differs')
        context_go_pin = receipt['root_GO_pin']
        context_go = decode(loaded(confined(root, context_go_pin['path']), context_go_pin))
        require(context_go['status'] == 'GO_FIXED_ON_BURST4_CONTEXT54'
                and context_go['context_scope_sha256'] == args.scope_sha256
                and context_go['context_code_sha256'] == scope['context_code_sha256'], 'Original context admission differs')
        matrix = metadata(root / BASE / 'context_results' / 'CONTEXT_PROFILES.json')
        require(matrix['schema'] == 'SETI_ON_BURST4_FIXED_SIX_SCAN_CONTEXT_PROFILES_V1'
                and matrix['status'] == STATUS and matrix['selected_tracks'] == expected_tracks
                and matrix['source_compacts'] == scope['source_compacts']
                and matrix['counts'] == receipt['counts'] and matrix['new_fit_or_detector_grid'] is False
                and matrix['ON_scan_positions_are_independent_visits'] is False
                and matrix['ON_OFF_veto_applied'] is False, 'Context matrix metadata differs')
        global np
        import numpy as np
        import h5py
        import hdf5plugin
        require(hdf5plugin.register(filters='bshuf', force=True) and h5py.h5z.filter_avail(32008), 'Bitshuffle codec unavailable')
        runtime = {'Python': sys.version.split()[0], 'HDF5': h5py.version.hdf5_version,
                   **{n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'h5py', 'hdf5plugin')}}
        require(receipt['runtime_versions'] == runtime, 'Numerical runtime differs')
        crops = {c['crop_id']: c for c in matrix['normalization_crops']}
        core_keys = {(t['native_chunk_index'], t['core_q']) for t in expected_tracks}
        require(len(crops) == len(matrix['normalization_crops']) == len(core_keys) * 6, 'Unique normalization crop census differs')
        require({(c['scan_id'], c['native_chunk_index'], c['core_q']) for c in crops.values()} ==
                {(scan, n, q) for scan in SCANS for n, q in core_keys}, 'Complete sixscan normalization matrix required')
        profiles = {(p['selected_track']['scan_id'], p['selected_track']['rank'], p['context_scan_id']): p
                    for p in matrix['profiles']}
        require(len(profiles) == len(matrix['profiles']) == 54 and set(profiles) ==
                {(origin, rank, scan) for origin in ORIGINS for rank in (1, 2, 3) for scan in SCANS}, 'Profile54 matrix differs')
        headers = {scan: sources[171, scan]['original_header'] for scan in SCANS}
        rows = np.arange(16, dtype=np.int64)
        verified = []
        out.mkdir(exist_ok=False)
        created_output = True
        for scan in SCANS:
            power = None if args.portable else np.empty((16, 3 * COUNT), dtype='<f4')
            for native in (() if args.portable else (170, 171, 172)):
                source = sources[native, scan]
                path = confined(root, source['path'])
                require(path.stat().st_size == source['bytes'] and digest(path) == source['sha256'], 'Whole raw compact hash differs')
                pins[source['path']] = {k: source[k] for k in ('bytes', 'sha256')}
                with h5py.File(path, 'r', rdcc_nbytes=0) as handle:
                    data = handle['data']
                    require(data.shape == (16, 1, COUNT) and data.dtype == np.dtype('<f4')
                            and int(data.attrs['original_source_frequency_chunk_origin']) == source['source_channel0']
                            and data.attrs['original_source_url'] == source['original_source_url']
                            and data.attrs['original_source_etag'] == source['original_source_etag'], 'Compact provenance differs')
                    for declaration in source['decoded_rows']:
                        value = data[declaration['time_row'], 0, :]
                        require(np.isfinite(value).all() and np.all(value >= 0)
                                and declaration['decoded_bytes'] == COUNT * 4
                                and hashlib.sha256(value.tobytes()).hexdigest() == declaration['decoded_sha256'], 'Decoded source row differs')
                        power[declaration['time_row'], (native - 170) * COUNT:(native - 169) * COUNT] = value
                        counts['source_rows'] += 1
                counts['source_files'] += 1
                verified.append({'path': source['path'], 'native_chunk_index': native, 'scan_id': scan,
                                 'file_sha256': source['sha256'], 'decoded_rows_verified': 16})
            cache = {}
            for crop_id, declaration in crops.items():
                if declaration['scan_id'] != scan:
                    continue
                native, q = declaration['native_chunk_index'], declaration['core_q']
                core0, crop0 = native * COUNT + q * CORE, native * COUNT + q * CORE - HALO
                source = sources[native, scan]
                require(crop_id == '%s_native%d_q%03d' % (scan, native, q)
                        and declaration['source_channel_interval_half_open'] == [crop0, crop0 + 12096]
                        and declaration['normalization_source_channel_interval_half_open'] == [core0, core0 + CORE]
                        and declaration['source_compact_path'] == source['path']
                        and declaration['source_compact_sha256'] == source['sha256']
                        and declaration['original_decoded_rows'] == source['decoded_rows'], 'Crop geometry/source metadata differs')
                raw = archive(declaration['raw_crop'])
                require(set(raw) == {'raw_power', 'source_channel0', 'normalization_source_channels', 'absolute_time_rows'}, 'Crop fields differ')
                require(raw['raw_power'].dtype == np.dtype('<f4') and raw['raw_power'].shape == (16, 12096)
                        and raw['source_channel0'].dtype == np.dtype('<i8') and raw['source_channel0'].shape == (), 'Crop raw precision differs')
                equal(raw['source_channel0'], crop0, 'Crop origin differs')
                equal(raw['normalization_source_channels'], np.arange(core0, core0 + CORE, dtype=np.int64), 'Crop core coordinates differ')
                equal(raw['absolute_time_rows'], rows, 'Crop rows differ')
                if power is not None:
                    equal(raw['raw_power'].view(np.uint32), power[:, crop0 - BAND0:crop0 + 12096 - BAND0].view(np.uint32), 'Saved fullcrop source bits differ')
                saved_normal = decode(loaded(confined(root, declaration['normalization']['path']), declaration['normalization']))
                equal(saved_normal['normalization_source_channels'], raw['normalization_source_channels'], 'Normal channel coordinates differ')
                equal(saved_normal['normalization_unmasked_counts'], np.full(16, CORE), 'Normal core support differs')
                independent = recompute_normal(raw['raw_power'])
                differences = {}
                for field, expected in independent.items():
                    near(saved_normal[field], expected, 'Independent full501 context normalization differs')
                    differences[field] = float(np.max(np.abs(np.asarray(saved_normal[field]) - expected)))
                    max_normal_error = max(max_normal_error, differences[field])
                cache[crop_id] = {'normal': independent, 'raw_power': raw['raw_power'], 'source_channel0': crop0}
                normal_reports.append({'crop_id': crop_id, 'max_absolute_differences': differences})
                counts['raw_normalization_crops'] += 1
                counts['full501_normalization_rows'] += 16
            for track in expected_tracks:
                origin, rank, width = track['scan_id'], track['rank'], track['width_channels']
                profile = profiles[origin, rank, scan]
                crop_id = '%s_native%d_q%03d' % (scan, track['native_chunk_index'], track['core_q'])
                declaration = crops[crop_id]
                require(profile['selected_track'] == track and profile['normalization_crop_id'] == crop_id
                        and profile['context_target'] == headers[scan]['source_name']
                        and profile['original_acquisition_role'] == ('ON' if scan.endswith('_on') else 'OFF')
                        and profile['reference_time_mjd'] == track['reference_time_mjd']
                        and profile['raw_normalization_crop'] == declaration['raw_crop']
                        and profile['normalization'] == declaration['normalization'], 'Profile provenance differs')
                r0 = track['window_start_row']
                window = np.arange(r0, r0 + 4, dtype=np.int64)
                times = (headers[scan]['tstart'] - headers[origin]['tstart']) * 86400 + (rows - r0) * TSAMP
                centers = np.rint((track['frequency_hz_at_window_reference'] - FCH1) / DF + track['drift_hz_s'] * times / DF).astype(np.int64)
                indexes = centers[:, None] - BAND0 + np.arange(-251, 252)[None, :]
                require(indexes.min() >= 0 and indexes.max() < 3 * COUNT, 'Fixed profile raw support outside triplet')
                capsule = archive(profile['raw_capsule'])
                schema = {'raw_power': ('<f4', (16, 503)), 'rounded_absolute_centers': ('<i8', (16,)),
                          'times_from_primary_reference_s': ('<f8', (16,)), 'absolute_time_rows': ('<i8', (16,)),
                          'row_standardized_box_sum': ('<f8', (16,)), 'window_source_rows': ('<i8', (4,)),
                          'row_four_row_score_contribution': ('<f8', (16,)), 'row_full16_score_contribution': ('<f8', (16,))}
                require(set(capsule) == set(schema), 'Profile capsule fields differ')
                for field, (dtype, shape) in schema.items():
                    require(capsule[field].dtype == np.dtype(dtype) and capsule[field].shape == shape and np.isfinite(capsule[field]).all(), 'Profile dtype/shape differs')
                equal(capsule['absolute_time_rows'], rows, 'Profile source rows differ')
                equal(capsule['window_source_rows'], window, 'Profile selected window differs')
                equal(capsule['rounded_absolute_centers'], centers, 'Profile trajectory rounding differs')
                equal(capsule['times_from_primary_reference_s'], times, 'Actual gap transport differs')
                if power is not None:
                    equal(capsule['raw_power'].view(np.uint32), power[rows[:, None], indexes].view(np.uint32), 'Profile capsule source bits differ')
                cropped_indexes = centers[:, None] - cache[crop_id]['source_channel0'] + np.arange(-251, 252)[None, :]
                require(cropped_indexes.min() >= 0 and cropped_indexes.max() < 12096, 'Profile support outside pinned normalization crop')
                equal(capsule['raw_power'].view(np.uint32), cache[crop_id]['raw_power'][rows[:, None], cropped_indexes].view(np.uint32), 'Profile capsule/crop source bits differ')
                terms = recompute_rows(capsule['raw_power'], cache[crop_id]['normal'], width)
                contrib16, contrib4 = terms / np.sqrt(16 * width), np.zeros(16, dtype=np.float64)
                contrib4[window] = terms[window] / np.sqrt(4 * width)
                score4, score16 = float(terms[window].sum() / np.sqrt(4 * width)), float(terms.sum() / np.sqrt(16 * width))
                near(capsule['row_standardized_box_sum'], terms, 'Independent scalar16row terms differ')
                near(capsule['row_four_row_score_contribution'], contrib4, 'Independent fourrow contributions differ')
                near(capsule['row_full16_score_contribution'], contrib16, 'Independent full16 contributions differ')
                for field, expected in (('times_from_primary_reference_s', times), ('rounded_absolute_centers', centers),
                                        ('row_standardized_box_sum', terms), ('window_source_rows', window),
                                        ('row_four_row_score_contribution', contrib4), ('row_full16_score_contribution', contrib16),
                                        ('row_midpoint_mjd', [headers[scan]['tstart'] + (j + .5) * TSAMP / 86400 for j in range(16)]),
                                        ('rounded_center_frequency_hz', FCH1 + DF * centers),
                                        ('fixed_four_row_score', score4), ('fixed_full16_score', score16)):
                    near(profile[field], expected, 'Independent profile summary differs: ' + field)
                own = origin == scan
                if own:
                    near(score4, track['score'], 'Own nine selected scores differ')
                    near(profile['origin_primary_score'], track['score'], 'Own score metadata differs')
                    near(profile['origin_primary_score_difference'], score4 - track['score'], 'Own score difference differs')
                    counts['origin_score_matches'] += 1
                else:
                    require(profile['origin_primary_score'] is None and profile['origin_primary_score_difference'] is None, 'Other scan labeled own')
                for contribution, fraction_field, row_field in (
                        (contrib4, 'positive_row_contribution_max_fraction', 'dominant_positive_row'),
                        (contrib16, 'full16_positive_row_contribution_max_fraction', 'full16_dominant_positive_row')):
                    positive, total = np.maximum(contribution, 0), float(np.maximum(contribution, 0).sum())
                    if total:
                        dominant = int(np.argmax(positive))
                        require(profile[row_field] == dominant, 'Positive contribution dominant row differs')
                        near(profile[fraction_field], float(positive[dominant] / total), 'Positive dominance fraction differs')
                    else:
                        require(profile[row_field] is None and profile[fraction_field] is None, 'Zero-positive dominance differs')
                row_error = float(np.max(np.abs(capsule['row_standardized_box_sum'] - terms)))
                score_error = max(abs(profile['fixed_four_row_score'] - score4), abs(profile['fixed_full16_score'] - score16))
                max_row_error, max_score_error = max(max_row_error, row_error), max(max_score_error, score_error)
                score_reports.append({'profile_id': profile['profile_id'], 'fixed_four_row_score': score4,
                                      'fixed_full16_score': score16, 'own_primary': own,
                                      'max_row_error': row_error, 'max_score_error': score_error})
                counts['context_profiles'] += 1
                counts['raw_profile_cells'] += 16 * 503
                counts['row_box_terms'] += 16
                counts['four_row_scores'] += 1
                counts['full16_scores'] += 1
            del power, cache
            print('PASS_INDEPENDENT_FIXED_CONTEXT_SCAN', scan, flush=True)
        if not args.portable:
            require(verified == matrix['source_verification'], 'Source verification ledger differs')
        expected = {'context_profiles': 54, 'origin_score_matches': 9,
                    'source_files': 0 if args.portable else 18, 'source_rows': 0 if args.portable else 288,
                    'raw_normalization_crops': len(core_keys) * 6, 'raw_profile_cells': 54 * 16 * 503,
                    'full501_normalization_rows': len(core_keys) * 6 * 16, 'four_row_scores': 54,
                    'full16_scores': 54, 'row_box_terms': 864}
        require(counts == expected, 'Independent context census incomplete')
        output_pins = receipt['output_pins']
        names = {p['path'] for p in output_pins}
        require(len(names) == len(output_pins) == 54 + 2 * len(crops) + 1, 'Closed context output inventory differs')
        observed = {name for name in pins if name.startswith(BASE + '/context_results/') and not name.endswith('/EXECUTION_RECEIPT.json')}
        actual = {p.relative_to(root).as_posix() for p in (root / BASE / 'context_results').iterdir() if p.is_file()}
        require(names == observed and actual == names | {BASE + '/context_results/EXECUTION_RECEIPT.json'}, 'Context output closure differs')
        for pin in output_pins:
            require(pins[pin['path']] == {k: pin[k] for k in ('bytes', 'sha256')}, 'Context terminal byte pin differs')
        for name, pin in pins.items():
            path = confined(root, name)
            require(path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256'], 'Input changed during context QA')
        usage = {'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(usage['process_CPU_seconds'] <= CPU_CAP and usage['wall_seconds'] <= WALL_CAP
                and usage['peak_RSS_bytes'] <= MEMORY_CAP, 'QA resource caps exceeded')
        result = {'schema': 'SETI_ON_BURST4_FIXED_CONTEXT_INDEPENDENT_QA_V1',
                  'status': ('PASS_PORTABLE54_FIXED_PROFILES9_OWN_SCORES_ALL_PINNED_CROP_FULL501_NORMALIZATIONS'
                             if args.portable else 'PASS54_FIXED_SIX_SCAN_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS'),
                  'context_scope_sha256': args.scope_sha256, 'context_qa_sha256': args.qa_sha256,
                  'context_code_sha256': scope['context_code_sha256'], 'context_receipt_sha256': args.receipt_sha256,
                  'root_go_sha256': args.root_go_sha256, 'primary_qa_receipt_sha256': go['primary_qa_receipt_sha256'],
                  'context_public_freeze_commit': go['context_public_freeze_commit'],
                  'counts': counts, 'normalization_reports': normal_reports, 'profile_reports': score_reports,
                  'max_full501_normalization_absolute_difference': max_normal_error,
                  'max_row_term_absolute_difference': max_row_error, 'max_score_absolute_difference': max_score_error,
                  'input_byte_pins': pins, 'runtime_versions': runtime, **usage,
                  'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
                  'output_cap_bytes': OUTPUT_CAP, 'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
                  'producer_imported': False, 'detector_imported': False, 'maximization_rerun': False,
                  'portable_saved_crop_replay': args.portable,
                  'original_HDF5_compacts_opened': not args.portable,
                  'all_fullcore_normalization_independently_recomputed': True,
                  'all_profile_capsule_bits_verified_against_saved_raw_crops': True,
                  'all_raw_saved_crops_and_profile_bits_verified_against_original_compacts': not args.portable,
                  'new_telescope_HTTP_requests': 0, 'source_acquisition_roles_changed': False,
                  'ON_scan_positions_are_independent_visits': False,
                  'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
                  'limitations': (['Portable replay authenticates frozen metadata and saved raw crop/profile payloads, and their mutual raw bits; original HDF5 and full decoded row hashes are not independently rechecked.'] if args.portable else []) +
                                 ['Fixed context is conditional on selected primary winners and carries no calibrated false-alarm or sky-origin statement.',
                                  'Constant drift is extrapolated across actual chronology without refitting; lack of fixed-track response cannot exclude a different track.',
                                  'Three ON positions belong to one visit; full16 scores use a different denominator from fourrow winners.']}
        create_json(out / 'QA_RECEIPT.json', result)
        require(sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= OUTPUT_CAP, 'Context QA output cap exceeded')
        print(result['status'], flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            create_json(out / 'QA_FAILURE.json', {'status': 'FAIL_INDEPENDENT_FIXED_CONTEXT_QA',
                        'error_type': type(error).__name__, 'message': str(error), 'partial_counts': counts,
                        'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)
        for handle in locks:
            handle.close()


if __name__ == '__main__':
    main()
