"""Independent full-band cleanTOP9 fixed54 context QA; no producer imports.

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
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'

BASE, PILOT = 'seti_burst_full', 'seti_burst_on'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ORIGINS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
JOBS = ('on20170428_epoch1_HIP98505', 'on20170428_epoch2_HIP98505', 'on20170428_epoch3_HIP98505')
COUNT, CORE, HALO, BAND0 = 1048576, 4096, 4000, 170 * 1048576
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DC_CHANNELS = tuple(native * COUNT + COUNT // 2 for native in (170, 171, 172))
ATOL, RTOL = 1e-7, 1e-10
CPU_CAP, WALL_CAP, MEMORY_CAP, OUTPUT_CAP = 600, 900, 2 * 1024**3, 4 * 1024**2
STATUS = 'COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
PRIMARY_STATUS = 'PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY'
AGGREGATE_STATUS = 'COMPLETE_GLOBAL_3_ON_SCANS_766_CORES_EACH_RAW700_SPACED100_TOP3_DUAL_WINNERS'
AGGREGATE_QA_STATUS = 'PASS_INDEPENDENT_FULL_SORT_9412608_CARRIERS_DUAL_GLOBAL_ON_RANKS'
GO_STATUS = 'GO_INDEPENDENT_FIXED_FULL_ON_CONTEXT54_QA'
PHYSICAL_FIELDS = ('scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
                   'source_reference_channel', 'frequency_hz_at_window_reference',
                   'window_start_row', 'window_length_rows', 'reference_time_mjd',
                   'drift_grid_index', 'drift_hz_s', 'width_channels')
NORM_FIELDS = {'row_power_median', 'row_residual_median', 'row_residual_MAD_scale',
               'row_winsorized_residual_location', 'normalization_unmasked_counts',
               'normalization_source_channels'}
METADATA_NAMES = ('burst_previous/analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json',
                  'burst_previous/analysis/s2017_next_native/source_manifest_v2.json',
                  'burst_previous/analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json',
                  'burst_previous/analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json')
METADATA_HASHES = ('1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107',
                   '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909',
                   'e10cb04bef9f5fd7a8cd132ffc90af16f9345e94b3630e4ce98c5adc8f46edbf',
                   '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e')


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


def bits_equal(actual, expected):
    a, b = np.asarray(actual), np.asarray(expected)
    return a.shape == b.shape and a.dtype.str == b.dtype.str and a.tobytes() == b.tobytes()


def normalization_bits_equal(actual, expected):
    if set(actual) != set(expected):
        return False
    for field in actual:
        dtype = np.int64 if field in ('normalization_unmasked_counts', 'normalization_source_channels') else np.float64
        if not bits_equal(np.asarray(actual[field], dtype=dtype), np.asarray(expected[field], dtype=dtype)):
            return False
    return True


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
        print(json.dumps({'status': 'PASS_TEXT_ONLY_FULL_CLEAN_TOP9_CONTEXT_QA_INTERFACE', 'source_values_read': False,
                          'numerical_modules_imported': False, 'profiles_expected': 54,
                          'own_fourrow_scores_expected': 9, 'full501_normalization': 'every saved unique core in every sixscan context',
                          'source_files_expected': 18, 'source_rows_expected': 288,
                          'crop_source_support_pieces': [1, 2], 'previous_pilot_reuse_bits_independently_verified': True,
                          'root_go_status': GO_STATUS, 'root_go_path': BASE + '/CONTEXT_QA_GO.json',
                          'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
                          'memory_cap_bytes': MEMORY_CAP, 'output_cap_bytes': OUTPUT_CAP}))
        return
    for sha in (args.scope_sha256, args.qa_sha256, args.receipt_sha256, args.root_go_sha256):
        require(sha is not None and re.fullmatch('[0-9a-f]{64}', sha), 'Exact SHA256s required')
    require(digest(Path(__file__).resolve()) == args.qa_sha256, 'QA source differs')
    run(Path(args.root).resolve(), args)


def run(root, args):
    started, pins, locks = time.monotonic(), {}, []
    output_name = args.output_dir or BASE + ('/context_portable_replay' if args.portable else '/context_qa_results')
    out = confined(root, output_name)
    require(out != root and not out.exists() and
            not any(out == root / stage / name for stage in (BASE, PILOT) for name in
                    ('results', 'context_results', 'qa_results', 'aggregate_results', 'aggregate_qa_results')),
            'Separate fresh QA output required')
    created_output = False
    counts = {'context_profiles': 0, 'origin_score_matches': 0, 'source_files': 0, 'source_rows': 0,
              'raw_normalization_crops': 0, 'raw_profile_cells': 0, 'full501_normalization_rows': 0,
              'four_row_scores': 0, 'full16_scores': 0, 'row_box_terms': 0,
              'source_support_piece_checks': 0, 'previous_pilot_profile_comparisons': 0,
              'previous_pilot_fixed_queries_reused_bit_identical': 0,
              'profiles_with_DC_contact_selected4': 0, 'profiles_with_DC_contact_full16': 0,
              'rows_with_DC_contact_selected4': 0, 'rows_with_DC_contact_full16': 0}
    normal_reports, score_reports, reuse_reports = [], [], []
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
        require(go['status'] == GO_STATUS
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
                and scope['schema'] == 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_SCOPE_V2'
                and scope['status'] == 'PREPARED_FROM_SOURCE_DUAL_QA_AND_GLOBAL_RANK_QA_VERIFIED_DC_CLEAN_TOP9'
                and scope['context_qa_code_sha256'] == args.qa_sha256
                and scope['context_code_sha256'] == go['context_code_sha256']
                and scope['scan_order'] == list(SCANS) and scope['primary_origins'] == list(ORIGINS)
                and scope['context_profiles'] == 54 and scope['origin_primary_score_matches'] == 9
                and scope['raw_normalization_crop_shape'] == [16, 12096]
                and scope['raw_profile_shape'] == [16, 503] and scope['running_median_channels'] == 501
                and scope['normalization_core_channels'] == CORE and scope['normalization_halo_channels'] == HALO
                and scope['CPU_cap_s'] == CPU_CAP and scope['wall_cap_s'] == WALL_CAP
                and scope['memory_cap_bytes'] == MEMORY_CAP
                and scope['frozen_DC_source_channels'] == list(DC_CHANNELS)
                and scope['DC_contact_score_veto_or_mask_applied'] is False
                and scope['new_fit_or_detector_grid'] is False and scope['protected2016_data_opened'] is False,
                'Frozen context scope differs')
        context_code_path = scope['context_code_path']
        require(context_code_path == BASE + '/context_v2.py'
                and context_code_path == go['context_code_path']
                and digest(confined(root, context_code_path)) == scope['context_code_sha256'],
                'Actual producer context bytes/path differ')
        input_names = set()
        for pin in scope['input_pins']:
            require(pin['path'] not in input_names, 'Duplicate context scope pin')
            input_names.add(pin['path'])
            loaded(confined(root, pin['path']), pin)
        require(set(METADATA_NAMES).issubset(input_names), 'Missing scientific source metadata')
        # Independently reconstruct the18 source headers/decoded-row records.
        midpoint, adjacent, acq171, acqadj = [metadata(root / name, sha)
                                            for name, sha in zip(METADATA_NAMES, METADATA_HASHES)]
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
                    and source['original_source_file_bytes'] == identity['source_file_bytes'] == original['source_file_bytes']
                    and source['original_acquisition_role'] == role == identity['role'].upper()
                    and source['shape'] == record['shape'] == [16, 1, COUNT]
                    and source['source_channel0'] == record['source_channel0'] == native * COUNT
                    and source['decoded_rows'] == record['decoded_rows']
                    and source['bytes'] == record['bytes'] and source['sha256'] == record['file_sha256'], 'Full source metadata differs')
            header = source['original_header']
            require(header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF
                    and header['tsamp'] == TSAMP and math.isfinite(header['tstart'])
                    and (role != 'ON' or header['source_name'] == 'HIP98505')
                    and [d['time_row'] for d in source['decoded_rows']] == list(range(16))
                    and all(d['decoded_bytes'] == COUNT * 4 for d in source['decoded_rows']),
                    'Source frequency/time/target/full row support differs')
            acquisition_name = METADATA_NAMES[2] if native == 171 else METADATA_NAMES[3]
            rawpath = Path('seti_raw') / Path(acquisition_name).relative_to('burst_previous').parent / record['array_file']
            require(source['path'] == rawpath.as_posix(), 'Raw compact path differs')
        headers = {scan: sources[171, scan]['original_header'] for scan in SCANS}
        for previous, current in zip(SCANS, SCANS[1:]):
            require(headers[current]['tstart'] >= headers[previous]['tstart'] + 16 * TSAMP / 86400,
                    'Actual source cadence is not chronological with complete integrations')
        full_scope = metadata(root / BASE / 'SCOPE.json', go['full_scope_sha256'])
        require(go['primary_qa_code_path'] in (BASE + '/qa.py', BASE + '/qa_v2.py')
                and digest(root / BASE / 'driver.py') == go['full_driver_sha256']
                and digest(confined(root, go['primary_qa_code_path'])) == go['primary_qa_code_sha256'],
                'Actual full source/QA code differs')
        loaded(root / BASE / 'driver.py')
        loaded(confined(root, go['primary_qa_code_path']))
        primary_qa = metadata(root / BASE / 'qa_results' / 'QA_RECEIPT.json', go['primary_qa_receipt_sha256'])
        require(primary_qa['status'] == PRIMARY_STATUS
                and primary_qa['scope_sha256'] == go['full_scope_sha256']
                and primary_qa['driver_sha256'] == go['full_driver_sha256']
                and primary_qa['qa_sha256'] == go['primary_qa_code_sha256']
                and len(primary_qa['primary_receipt_sha256s']) == 21,
                'Actual completed full source/dual main QA required')
        for job, sha in primary_qa['primary_receipt_sha256s'].items():
            primary_receipt = metadata(root / BASE / 'results' / job / 'EXECUTION_RECEIPT.json', sha)
            require(primary_receipt['status'] == 'COMPLETE_NEW_FULL_ON_DUAL_BURST4_SHARD_EXPLORATORY_ONLY'
                    and primary_receipt['scope_sha256'] == go['full_scope_sha256']
                    and primary_receipt['driver_sha256'] == go['full_driver_sha256'],
                    'Main QA authenticated producer shard differs')
        aggregate_scope = metadata(root / BASE / 'AGGREGATE_SCOPE.json', go['aggregate_scope_sha256'])
        aggregate_receipt = metadata(root / BASE / 'aggregate_results' / 'EXECUTION_RECEIPT.json',
                                     go['aggregate_receipt_sha256'])
        aggregate_qa = metadata(root / BASE / 'aggregate_qa_results' / 'QA_RECEIPT.json',
                                go['aggregate_qa_receipt_sha256'])
        require(digest(root / BASE / 'aggregate.py') == go['aggregate_code_sha256']
                and digest(root / BASE / 'aggregate_qa.py') == go['aggregate_qa_code_sha256'],
                'Actual aggregate/QA code differs')
        loaded(root / BASE / 'aggregate.py')
        loaded(root / BASE / 'aggregate_qa.py')
        require(aggregate_receipt['status'] == AGGREGATE_STATUS
                and aggregate_receipt['aggregate_scope_sha256'] == go['aggregate_scope_sha256']
                and aggregate_receipt['aggregate_code_sha256'] == go['aggregate_code_sha256']
                and aggregate_scope['aggregate_code_sha256'] == go['aggregate_code_sha256'],
                'Completed exact full-band aggregate required')
        aggregate_full_receipts = {Path(p['path']).parent.name: p['sha256']
                                   for p in aggregate_receipt['producer_receipt_pins']
                                   if p['path'].startswith(BASE + '/results/')}
        require(len(aggregate_full_receipts) == 21
                and primary_qa['primary_receipt_sha256s'] == aggregate_full_receipts,
                'Aggregate and actual source/dual QA do not bind the same21 producer receipts')
        require(aggregate_qa['status'] == AGGREGATE_QA_STATUS and aggregate_qa['mismatch_count'] == 0
                and aggregate_qa['aggregate_receipt_sha256'] == go['aggregate_receipt_sha256']
                and aggregate_qa['aggregate_scope_sha256'] == go['aggregate_scope_sha256']
                and aggregate_qa['aggregate_code_sha256'] == go['aggregate_code_sha256']
                and aggregate_qa['qa_code_sha256'] == go['aggregate_qa_code_sha256'],
                'Independent aggregate QA not exact PASS')
        if scope['schema'].endswith('_V2'):
            require(scope['source_QA_receipt'] == {'path': BASE + '/qa_results/QA_RECEIPT.json',
                        'bytes': len(loaded(root / BASE / 'qa_results/QA_RECEIPT.json')),
                        'sha256': go['primary_qa_receipt_sha256']}
                    and scope['global_rank_QA_receipt'] == {'path': BASE + '/aggregate_qa_results/QA_RECEIPT.json',
                        'bytes': len(loaded(root / BASE / 'aggregate_qa_results/QA_RECEIPT.json')),
                        'sha256': go['aggregate_qa_receipt_sha256']},
                    'Context scope source/global QA prerequisite pins differ')
        aggregate_pins = {p['path']: p for p in aggregate_receipt['output_pins']}
        require(len(aggregate_pins) == len(aggregate_receipt['output_pins']), 'Duplicate aggregate output pin')
        selected_path = BASE + '/aggregate_results/SELECTED_CLEAN_TOP9.json'
        require(aggregate_qa['selected_clean_TOP9_pin'] == aggregate_pins[selected_path],
                'Global QA selected9 pin differs')
        selected = decode(loaded(root / selected_path, aggregate_pins[selected_path]))
        require(selected['no_ON_scan_pooling'] is True, 'Global original ON scans were pooled')
        expected_tracks = selected['records']
        require(len(expected_tracks) == 9, 'Exactly9 global clean selected tracks required')
        for i, track in enumerate(expected_tracks):
            origin, rank = ORIGINS[i // 3], i % 3 + 1
            native, q, carrier = (track[k] for k in ('native_chunk_index', 'core_q', 'carrier_index_in_core'))
            channel = native * COUNT + q * CORE + carrier
            r0, di, width = (track[k] for k in ('window_start_row', 'drift_grid_index', 'width_channels'))
            require(track['scan_id'] == origin and track['rank'] == rank and
                    track['winner_family'] == 'DC_clean' and track['eligible_DC_untouched'] is True
                    and track['frozen_DC_source_channels'] == list(DC_CHANNELS)
                    and track['original_acquisition_role'] == 'ON' and track['primary_target'] == 'HIP98505'
                    and native in (170, 171, 172) and type(q) is int and 0 <= q <= 255
                    and (native, q) not in ((170, 0), (172, 255))
                    and type(carrier) is int and 0 <= carrier < CORE
                    and type(r0) is int and r0 in range(0, 13, 2) and track['window_length_rows'] == 4
                    and track['window_source_rows'] == list(range(r0, r0 + 4))
                    and type(di) is int and 0 <= di < 159 and width in (1, 3)
                    and math.isclose(track['drift_hz_s'], -4 + di * 8 / 158, rel_tol=0, abs_tol=2e-15)
                    and track['source_reference_channel'] == channel
                    and track['frequency_hz_at_window_reference'] == FCH1 + DF * channel
                    and track['reference_time_mjd'] == headers[origin]['tstart'] + (r0 + .5) * TSAMP / 86400
                    and math.isfinite(track['score']), 'Global clean selected identity/geometry differs')
            for declaration in (track['source_map'], track['normalization'], track['producer_receipt']):
                loaded(confined(root, declaration['path']), declaration)
        for i, origin in enumerate(ORIGINS):
            path = BASE + '/aggregate_results/' + origin + '_DC_CLEAN_TOP3.json'
            require(decode(loaded(root / path, aggregate_pins[path]))['records'] == expected_tracks[i * 3:i * 3 + 3],
                    'Per-scan global selected3 differs')
        require(scope['selected_tracks'] == expected_tracks, 'Frozen nine selected tracks differ')
        receipt = metadata(root / BASE / 'context_results' / 'EXECUTION_RECEIPT.json', args.receipt_sha256)
        require(receipt['schema'] == 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_EXECUTION_V2'
                and receipt['status'] == STATUS and receipt['context_scope_sha256'] == args.scope_sha256
                and receipt['context_code_sha256'] == scope['context_code_sha256']
                and receipt['context_code_path'] == context_code_path
                and receipt['source_QA_receipt'] == scope['source_QA_receipt']
                and receipt['global_rank_QA_receipt'] == scope['global_rank_QA_receipt']
                and receipt['CPU_cap_s'] == CPU_CAP and receipt['wall_cap_s'] == WALL_CAP
                and receipt['memory_cap_bytes'] == MEMORY_CAP
                and receipt['new_fit_or_detector_grid'] is False and receipt['source_bytes_unchanged'] is True
                and receipt['new_telescope_HTTP_requests'] == 0, 'Context receipt differs')
        context_go_pin = receipt['root_GO_pin']
        context_go = decode(loaded(confined(root, context_go_pin['path']), context_go_pin))
        require(context_go['status'] == 'GO_FULL_ON_BURST4_FIXED_CONTEXT54'
                and context_go['context_scope_sha256'] == args.scope_sha256
                and context_go['context_code_sha256'] == scope['context_code_sha256'], 'Original context admission differs')
        context_output_pins = {p['path']: p for p in receipt['output_pins']}
        require(len(context_output_pins) == len(receipt['output_pins']), 'Duplicate context output pin')
        matrix_path = BASE + '/context_results/CONTEXT_PROFILES.json'
        matrix = decode(loaded(root / matrix_path, context_output_pins[matrix_path]))
        require(matrix['schema'] == 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_PROFILES_V2'
                and matrix['status'] == STATUS and matrix['selected_tracks'] == expected_tracks
                and matrix['source_compacts'] == scope['source_compacts']
                and matrix['counts'] == receipt['counts'] and matrix['new_fit_or_detector_grid'] is False
                and matrix['ON_scan_positions_are_independent_visits'] is False
                and matrix['ON_OFF_veto_applied'] is False
                and matrix['DC_contact_score_veto_or_mask_applied'] is False, 'Context matrix metadata differs')
        previous_scope = metadata(root / PILOT / 'CONTEXT_SCOPE.json')
        previous_receipt = metadata(root / PILOT / 'context_results/EXECUTION_RECEIPT.json')
        previous_qa = metadata(root / PILOT / 'context_qa_results/QA_RECEIPT.json')
        require(previous_receipt['status'] == 'COMPLETE_NINE_ON_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
                and previous_receipt['context_scope_sha256'] == digest(root / PILOT / 'CONTEXT_SCOPE.json')
                and previous_qa['status'] == 'PASS54_FIXED_SIX_SCAN_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS'
                and previous_qa['context_receipt_sha256'] == digest(root / PILOT / 'context_results/EXECUTION_RECEIPT.json'),
                'Exact completed independently source-qualified previous-pilot context required')
        previous_pins = {p['path']: p for p in previous_receipt['output_pins']}
        previous_matrix_path = PILOT + '/context_results/CONTEXT_PROFILES.json'
        require(scope['previous_context_matrix'] == previous_matrix_path, 'Previous matrix path differs')
        previous_matrix = decode(loaded(root / previous_matrix_path, previous_pins[previous_matrix_path]))
        require(previous_matrix['selected_tracks'] == previous_scope['selected_tracks']
                and previous_matrix['counts'] == previous_receipt['counts'], 'Previous matrix identities differ')
        reuse_candidates = {}
        reuse_checks_by_track = {}
        expected_candidates = []
        for track in expected_tracks:
            matches = [old for old in previous_matrix['selected_tracks']
                       if all(old[field] == track[field] for field in PHYSICAL_FIELDS)]
            require(len(matches) <= 1, 'Duplicate previous physical tuple')
            if not matches:
                continue
            old = matches[0]
            previous_profiles = [p for p in previous_matrix['profiles']
                                 if p['selected_track']['scan_id'] == old['scan_id']
                                 and p['selected_track']['rank'] == old['rank']]
            require(len(previous_profiles) == 6 and
                    {p['context_scan_id'] for p in previous_profiles} == set(SCANS),
                    'Previous physical tuple lacks six original scans')
            candidate = {'selected_scan_id': track['scan_id'], 'selected_rank': track['rank'],
                         'previous_selected_track': old, 'previous_profiles': previous_profiles}
            expected_candidates.append(candidate)
            reuse_candidates[track['scan_id'], track['rank']] = candidate
            reuse_checks_by_track[track['scan_id'], track['rank']] = []
            for profile in previous_profiles:
                for declaration in (profile['raw_capsule'], profile['raw_normalization_crop'], profile['normalization']):
                    require(previous_pins[declaration['path']] == declaration,
                            'Previous reused artifact not in authenticated output inventory')
                    loaded(confined(root, declaration['path']), declaration)
        require(scope['potential_previous_pilot_reuse'] == expected_candidates,
                'Potential previous-pilot physical-tuple matches differ')
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
                support_sources = [source for source in scope['source_compacts'] if source['scan_id'] == scan
                                   and source['source_channel0'] < crop0 + 12096
                                   and source['source_channel0'] + COUNT > crop0]
                support = [{'path': source['path'], 'sha256': source['sha256'],
                            'source_channel0': source['source_channel0'],
                            'original_decoded_rows': source['decoded_rows']} for source in support_sources]
                require(crop_id == '%s_native%d_q%03d' % (scan, native, q)
                        and declaration['source_channel_interval_half_open'] == [crop0, crop0 + 12096]
                        and declaration['normalization_source_channel_interval_half_open'] == [core0, core0 + CORE]
                        and BAND0 <= crop0 and crop0 + 12096 <= BAND0 + 3 * COUNT
                        and declaration['source_support'] == support and 1 <= len(support) <= 2,
                        'Crop geometry/complete source-piece metadata differs')
                covered = crop0
                for piece in support_sources:
                    start, stop = max(crop0, piece['source_channel0']), min(crop0 + 12096, piece['source_channel0'] + COUNT)
                    require(start == covered and stop > start, 'Crop source pieces are not contiguous/exhaustive')
                    covered = stop
                    counts['source_support_piece_checks'] += 1
                require(covered == crop0 + 12096, 'Crop support pieces leave a raw gap')
                raw = archive(declaration['raw_crop'])
                require(set(raw) == {'raw_power', 'source_channel0', 'normalization_source_channels', 'absolute_time_rows'}, 'Crop fields differ')
                require(raw['raw_power'].dtype == np.dtype('<f4') and raw['raw_power'].shape == (16, 12096)
                        and np.isfinite(raw['raw_power']).all() and np.all(raw['raw_power'] >= 0)
                        and raw['source_channel0'].dtype == np.dtype('<i8') and raw['source_channel0'].shape == (), 'Crop raw precision differs')
                require(raw['normalization_source_channels'].dtype == np.dtype('<i8')
                        and raw['normalization_source_channels'].shape == (CORE,)
                        and raw['absolute_time_rows'].dtype == np.dtype('<i8')
                        and raw['absolute_time_rows'].shape == (16,), 'Crop coordinate precision differs')
                equal(raw['source_channel0'], crop0, 'Crop origin differs')
                equal(raw['normalization_source_channels'], np.arange(core0, core0 + CORE, dtype=np.int64), 'Crop core coordinates differ')
                equal(raw['absolute_time_rows'], rows, 'Crop rows differ')
                if power is not None:
                    equal(raw['raw_power'].view(np.uint32), power[:, crop0 - BAND0:crop0 + 12096 - BAND0].view(np.uint32), 'Saved fullcrop source bits differ')
                saved_normal = decode(loaded(confined(root, declaration['normalization']['path']), declaration['normalization']))
                require(set(saved_normal) == NORM_FIELDS, 'Normalization schema differs')
                equal(saved_normal['normalization_source_channels'], raw['normalization_source_channels'], 'Normal channel coordinates differ')
                equal(saved_normal['normalization_unmasked_counts'], np.full(16, CORE), 'Normal core support differs')
                independent = recompute_normal(raw['raw_power'])
                differences = {}
                for field, expected in independent.items():
                    near(saved_normal[field], expected, 'Independent full501 context normalization differs')
                    differences[field] = float(np.max(np.abs(np.asarray(saved_normal[field]) - expected)))
                    max_normal_error = max(max_normal_error, differences[field])
                cache[crop_id] = {'normal': independent, 'saved_normal': saved_normal,
                                 'raw': raw, 'raw_power': raw['raw_power'], 'source_channel0': crop0}
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
                    if field in ('times_from_primary_reference_s', 'rounded_absolute_centers',
                                 'window_source_rows', 'row_midpoint_mjd', 'rounded_center_frequency_hz'):
                        equal(profile[field], expected, 'Exact profile coordinate summary differs: ' + field)
                    else:
                        near(profile[field], expected, 'Independent profile summary differs: ' + field)
                own = origin == scan
                lower, upper = centers - width // 2, centers + width // 2
                touched = np.column_stack([(lower <= dc) & (upper >= dc) for dc in DC_CHANNELS])
                by_dc16 = {str(dc): np.flatnonzero(touched[:, i]).tolist() for i, dc in enumerate(DC_CHANNELS)}
                by_dc4 = {str(dc): window[touched[window, i]].tolist() for i, dc in enumerate(DC_CHANNELS)}
                union16 = np.flatnonzero(touched.any(axis=1)).tolist()
                union4 = window[touched[window].any(axis=1)].tolist()
                diagnostic = {'frozen_DC_source_channels': list(DC_CHANNELS),
                              'row_width_box_source_channels_inclusive': np.column_stack((lower, upper)).tolist(),
                              'row_intersects_each_frozen_DC': touched.tolist(),
                              'DC_contact_row_indices_full16': union16,
                              'DC_contact_row_indices_selected4': union4,
                              'DC_contact_rows_by_frozen_DC_full16': by_dc16,
                              'DC_contact_rows_by_frozen_DC_selected4': by_dc4,
                              'DC_contact_counts_by_frozen_DC_full16': {dc: len(values) for dc, values in by_dc16.items()},
                              'DC_contact_counts_by_frozen_DC_selected4': {dc: len(values) for dc, values in by_dc4.items()},
                              'DC_contact_count_full16': len(union16), 'DC_contact_count_selected4': len(union4),
                              'DC_contact_any_full16': bool(union16), 'DC_contact_any_selected4': bool(union4),
                              'DC_contact_score_veto_or_mask_applied': False}
                for field, expected in diagnostic.items():
                    require(profile[field] == expected, 'Fixed-context inclusive DC diagnostic differs: ' + field)
                require(not own or not union4, 'Own selected four-row winner unexpectedly touches frozen DC')
                counts['profiles_with_DC_contact_selected4'] += int(bool(union4))
                counts['profiles_with_DC_contact_full16'] += int(bool(union16))
                counts['rows_with_DC_contact_selected4'] += len(union4)
                counts['rows_with_DC_contact_full16'] += len(union16)
                if own:
                    primary_normal = decode(loaded(confined(root, track['normalization']['path']), track['normalization']))
                    compact_normal = dict(cache[crop_id]['saved_normal'])
                    channels = compact_normal.pop('normalization_source_channels')
                    require(channels == list(range(track['native_chunk_index'] * COUNT + track['core_q'] * CORE,
                                                   track['native_chunk_index'] * COUNT + (track['core_q'] + 1) * CORE)),
                            'Own context normalization physical core differs')
                    compact_normal['normalization_source_channel_interval_half_open'] = [channels[0], channels[-1] + 1]
                    require(compact_normal == primary_normal, 'Own full16 context normalization differs from selected primary')
                    near(score4, track['score'], 'Own nine selected scores differ')
                    near(profile['origin_primary_score'], track['score'], 'Own score metadata differs')
                    near(profile['origin_primary_score_difference'], score4 - track['score'], 'Own score difference differs')
                    counts['origin_score_matches'] += 1
                else:
                    require(profile['origin_primary_score'] is None and profile['origin_primary_score_difference'] is None, 'Other scan labeled own')
                candidate = reuse_candidates.get((origin, rank))
                if candidate is None:
                    require(profile['previous_pilot_candidate_comparison'] is None and
                            profile['reused_previous_pilot_fixed_query'] is False,
                            'Nonmatching physical tuple was labeled pilot reuse')
                else:
                    old_profile = next(p for p in candidate['previous_profiles'] if p['context_scan_id'] == scan)
                    old_raw = archive(old_profile['raw_normalization_crop'])
                    old_capsule = archive(old_profile['raw_capsule'])
                    old_normal = decode(loaded(confined(root, old_profile['normalization']['path']), old_profile['normalization']))
                    require(set(old_raw) == set(cache[crop_id]['raw']) and set(old_capsule) == set(capsule),
                            'Previous-pilot raw archive schema differs')
                    crop_checks = {'raw_normalization_crop_bits': bits_equal(cache[crop_id]['raw']['raw_power'], old_raw['raw_power']),
                                   'crop_channel0_bits': bits_equal(cache[crop_id]['raw']['source_channel0'], old_raw['source_channel0']),
                                   'normalization_source_channels_bits': bits_equal(cache[crop_id]['raw']['normalization_source_channels'], old_raw['normalization_source_channels']),
                                   'crop_absolute_time_rows_bits': bits_equal(cache[crop_id]['raw']['absolute_time_rows'], old_raw['absolute_time_rows'])}
                    capsule_checks = {'raw503_bits': bits_equal(capsule['raw_power'], old_capsule['raw_power']),
                                      'rounded_centers_bits': bits_equal(capsule['rounded_absolute_centers'], old_capsule['rounded_absolute_centers']),
                                      'time_vector_bits': bits_equal(capsule['times_from_primary_reference_s'], old_capsule['times_from_primary_reference_s']),
                                      'capsule_absolute_time_rows_bits': bits_equal(capsule['absolute_time_rows'], old_capsule['absolute_time_rows']),
                                      'row_standardized_sum_bits': bits_equal(capsule['row_standardized_box_sum'], old_capsule['row_standardized_box_sum']),
                                      'window_rows_bits': bits_equal(capsule['window_source_rows'], old_capsule['window_source_rows']),
                                      'four_row_contribution_bits': bits_equal(capsule['row_four_row_score_contribution'], old_capsule['row_four_row_score_contribution']),
                                      'full16_contribution_bits': bits_equal(capsule['row_full16_score_contribution'], old_capsule['row_full16_score_contribution'])}
                    checks = {**crop_checks, **capsule_checks,
                              'full16_normalization_bits': normalization_bits_equal(cache[crop_id]['saved_normal'], old_normal),
                              'four_row_score_bits': bits_equal(np.float64(profile['fixed_four_row_score']), np.float64(old_profile['fixed_four_row_score'])),
                              'full16_score_bits': bits_equal(np.float64(profile['fixed_full16_score']), np.float64(old_profile['fixed_full16_score']))}
                    comparison = {'previous_profile_id': old_profile['profile_id'],
                                  'previous_raw_capsule': old_profile['raw_capsule'],
                                  'previous_raw_normalization_crop': old_profile['raw_normalization_crop'],
                                  'previous_normalization': old_profile['normalization'],
                                  'bit_identity_checks': checks, 'this_scan_all_bits_identical': all(checks.values())}
                    require(profile['previous_pilot_candidate_comparison'] == comparison,
                            'Previous-pilot raw/norm/profile/score bit comparison differs')
                    reuse_checks_by_track[origin, rank].append(all(checks.values()))
                    reuse_reports.append({'profile_id': profile['profile_id'], **comparison})
                    counts['previous_pilot_profile_comparisons'] += 1
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
        expected_reuse = []
        for key, candidate in reuse_candidates.items():
            identical = reuse_checks_by_track[key]
            require(len(identical) == 6, 'Previous-pilot reuse comparison lacks six scans')
            all_identical = all(identical)
            for scan in SCANS:
                require(profiles[key[0], key[1], scan]['reused_previous_pilot_fixed_query'] is all_identical,
                        'Previous-pilot reuse must depend on all six scans, not one scan')
            expected_reuse.append({'scan_id': key[0], 'selected_rank': key[1],
                                   'previous_selected_track': candidate['previous_selected_track'],
                                   'all_six_scans_bits_identical': all_identical,
                                   'fixed_queries_reused': 6 if all_identical else 0})
            counts['previous_pilot_fixed_queries_reused_bit_identical'] += 6 if all_identical else 0
        require(matrix['previous_pilot_reuse'] == expected_reuse, 'Previous-pilot six-scan reuse summary differs')
        production_counts = {'selected_tracks': 9, 'context_profiles': 54, 'origin_score_matches': 9,
                             'source_files_verified': 18, 'source_rows_verified': 288,
                             'raw503_profile_cells': 54 * 16 * 503, 'raw_normalization_crops': len(crops),
                             'raw_normalization_crop_cells': len(crops) * 16 * 12096,
                             'four_row_scores': 54, 'full16_scores': 54, 'row_box_terms': 864,
                             'profiles_computed_this_execution': 54,
                             'previous_pilot_fixed_queries_reused_bit_identical': counts['previous_pilot_fixed_queries_reused_bit_identical'],
                             'new_fixed_context_queries': 54 - counts['previous_pilot_fixed_queries_reused_bit_identical'],
                             'profiles_with_selected4_DC_contact': counts['profiles_with_DC_contact_selected4'],
                             'profiles_with_full16_DC_contact': counts['profiles_with_DC_contact_full16'],
                             'selected4_DC_contact_rows': counts['rows_with_DC_contact_selected4'],
                             'full16_DC_contact_rows': counts['rows_with_DC_contact_full16']}
        require(matrix['counts'] == production_counts, 'Context producer counts/DC/reuse ledger differs')
        expected = {'context_profiles': 54, 'origin_score_matches': 9,
                    'source_files': 0 if args.portable else 18, 'source_rows': 0 if args.portable else 288,
                    'raw_normalization_crops': len(core_keys) * 6, 'raw_profile_cells': 54 * 16 * 503,
                    'full501_normalization_rows': len(core_keys) * 6 * 16, 'four_row_scores': 54,
                    'full16_scores': 54, 'row_box_terms': 864,
                    'source_support_piece_checks': sum(len(c['source_support']) for c in crops.values()),
                    'previous_pilot_profile_comparisons': len(reuse_candidates) * 6,
                    'previous_pilot_fixed_queries_reused_bit_identical': sum(r['fixed_queries_reused'] for r in expected_reuse),
                    'profiles_with_DC_contact_selected4': production_counts['profiles_with_selected4_DC_contact'],
                    'profiles_with_DC_contact_full16': production_counts['profiles_with_full16_DC_contact'],
                    'rows_with_DC_contact_selected4': production_counts['selected4_DC_contact_rows'],
                    'rows_with_DC_contact_full16': production_counts['full16_DC_contact_rows']}
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
        result = {'schema': 'SETI_FULL_ON_BURST4_FIXED_CONTEXT_INDEPENDENT_QA_V2',
                  'status': ('PASS_PORTABLE54_FULL_BAND_FIXED_PROFILES9_OWN_SCORES_PINNED_CROP_FULL501_AND_DC_DIAGNOSTICS'
                             if args.portable else 'PASS54_FULL_BAND_CLEAN_TOP9_FIXED_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS_AND_DC_DIAGNOSTICS'),
                  'context_scope_sha256': args.scope_sha256, 'context_qa_sha256': args.qa_sha256,
                  'context_code_sha256': scope['context_code_sha256'], 'context_receipt_sha256': args.receipt_sha256,
                  'root_go_sha256': args.root_go_sha256, 'primary_qa_receipt_sha256': go['primary_qa_receipt_sha256'],
                  'primary_qa_code_path': go['primary_qa_code_path'],
                  'primary_qa_code_sha256': go['primary_qa_code_sha256'],
                  'aggregate_scope_sha256': go['aggregate_scope_sha256'],
                  'aggregate_receipt_sha256': go['aggregate_receipt_sha256'],
                  'aggregate_qa_receipt_sha256': go['aggregate_qa_receipt_sha256'],
                  'context_code_path': context_code_path,
                  'context_public_freeze_commit': go['context_public_freeze_commit'],
                  'counts': counts, 'normalization_reports': normal_reports, 'profile_reports': score_reports,
                  'previous_pilot_reuse_reports': reuse_reports,
                  'previous_pilot_reuse_summary': expected_reuse,
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
                  'all_context_inclusive_DC_contacts_independently_verified': True,
                  'own_selected_four_row_winners_DC_untouched': True,
                  'DC_contact_score_veto_or_mask_applied': False,
                  'previous_pilot_reuse_all_six_scan_bit_checks_independently_verified': True,
                  'new_telescope_HTTP_requests': 0, 'source_acquisition_roles_changed': False,
                  'ON_scan_positions_are_independent_visits': False,
                  'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
                  'limitations': (['Portable replay authenticates frozen metadata and saved raw crop/profile payloads, and their mutual raw bits; original HDF5 and full decoded row hashes are not independently rechecked.'] if args.portable else []) +
                                 ['Fixed context is conditional on selected primary winners and carries no calibrated false-alarm or sky-origin statement.',
                                  'Constant drift is extrapolated across actual chronology without refitting; lack of fixed-track response cannot exclude a different track.',
                                  'Three ON positions belong to one visit; full16 scores use a different denominator from fourrow winners.',
                                  'Only the origin selected four-row winner is required to avoid frozen DC. Transported selected-four-row or full16 support may contact DC; diagnostics flag every contact without changing a score.']}
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
