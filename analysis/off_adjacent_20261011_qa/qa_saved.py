"""Independent saved-output QA for 1536 adjacent-band original OFF maps.

Import and --check-only are metadata-only. No detector is imported. Actual QA
requires a separate root GO pinned to this source and three COMPLETE receipts.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

BASE = 'analysis/off_adjacent_20261011_qa'
PRIMARY = 'analysis/off_adjacent_20261011'
READER = 'analysis/new_visit_search/dependencies/standard_reader.py'
READER_SHA = '329b922431a925a08ad48e7315f54f556e1af5f7bccbec0f51d71fb52216ffb0'
NATIVE171_SOURCE = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
ADJACENT_SOURCE = 'analysis/s2017_next_native/source_manifest_v2.json'
NATIVE171_ACQ = 'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json'
ADJACENT_ACQ = 'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
TARGETS = {'primary20170428_HIP97319': 'epoch1_off',
           'primary20170428_HIP97461': 'epoch2_off',
           'primary20170428_HIP97663': 'epoch3_off'}
NATIVES = (170, 171, 172)
CHUNK, CORE = 1048576, 4096
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
DOMAINS = tuple([(170, q) for q in range(1, 256)] + [(171, 0), (171, 255)]
                + [(172, q) for q in range(255)])
ATOL, RTOL = 1e-7, 1e-10
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP = 1800, 1800, 3 * 1024**3, 8 * 1024**2
EXPECTED = {'maps': 1536, 'carrier_maxima': 1536 * CORE,
            'valid_hypothesis_records': 1536 * CORE * 1570,
            'core_row_medians': 1536 * 16, 'score_audit_queries': 6153,
            'raw_power_cells': 6153 * 16 * 503, 'independent_scores': 6153,
            'source_compacts': 18, 'source_decoded_rows': 288,
            'top20_entries': 60, 'top3_entries': 9}


def require(condition, message):
    if not condition:
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
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json_bytes(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root, name):
    item = Path(name)
    require(not item.is_absolute() and '..' not in item.parts, 'Workspace-relative input required')
    result = root / item
    require(result.resolve().is_relative_to(root) and not result.is_symlink(), 'Unconfined input')
    return result


def create_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def independent_rows(raw, normal, width):
    """Local501 arithmetic independent of SciPy filtering and prefix sums."""
    require(raw.shape == (16, 503) and raw.dtype == np.dtype('<f4'), 'Raw503 input differs')
    require(width in (1, 3), 'Queried width outside frozen search family')
    ratio = raw.astype(np.float64) / np.asarray(normal['row_power_median'])[:, None]
    columns = list(range(251 - width // 2, 252 + width // 2))
    medians = np.column_stack([np.median(ratio[:, column - 250:column + 251], axis=1)
                              for column in columns])
    residual = ratio[:, columns] - medians
    standardized = (residual - np.asarray(normal['row_winsorized_residual_location'])[:, None]) / np.asarray(
        normal['row_residual_MAD_scale'])[:, None]
    rows = standardized.sum(axis=1)
    return rows, float(rows.sum() / np.sqrt(16 * width))


def centers_for(frequency, drift):
    times = np.arange(16) * TSAMP
    return np.rint((frequency - FCH1) / DF + drift * times / DF).astype(np.int64)


def arrays_equal(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.array_equal(a, b), message)


def arrays_near(actual, expected, message):
    a, b = np.asarray(actual), np.asarray(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, atol=ATOL, rtol=RTOL), message)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--check-only', action='store_true')
    for name in ('scope-sha256', 'qa-sha256', 'root-go-sha256'):
        parser.add_argument('--' + name)
    parser.add_argument('--primary-receipt', action='append', default=[], help='primary_id=SHA256')
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path(args.root).resolve()
    scope_path = root / PRIMARY / 'scope.json'
    if args.check_only:
        require(len(DOMAINS) == len(set(DOMAINS)) == 512, 'Prospective domain is not512 distinct cores')
        prior = {(171, q) for q in range(1, 255)}
        require(not set(DOMAINS) & prior, 'New domains overlap prior254 native171 OFF cores')
        require(min(n * CHUNK + q * CORE - 4000 for n, q in DOMAINS) >= 170 * CHUNK
                and max(n * CHUNK + (q + 1) * CORE + 4000 for n, q in DOMAINS) <= 173 * CHUNK,
                'Declared crop halos leave acquired triplet')
        print(json.dumps({'status': 'PASS_METADATA_ONLY_INDEPENDENT_QA_INTERFACE',
                          'expected_counts': EXPECTED, 'core_domains_per_target': len(DOMAINS),
                          'scope_present': scope_path.exists(), 'source_values_read': False}))
        return
    for sha in (args.scope_sha256, args.qa_sha256, args.root_go_sha256):
        require(sha is not None and re.fullmatch('[0-9a-f]{64}', sha), 'Exact source/scope/GO SHA256 required')
    require(digest(Path(__file__).resolve()) == args.qa_sha256, 'Reviewed QA source differs')
    declared_receipts = {}
    for declaration in args.primary_receipt:
        key, sha = declaration.split('=', 1)
        require(key in TARGETS and key not in declared_receipts and re.fullmatch('[0-9a-f]{64}', sha),
                'Unique exact primary receipt declaration required')
        declared_receipts[key] = sha
    require(set(declared_receipts) == set(TARGETS), 'Exactly three primary receipts required')
    run(root, args, declared_receipts)


def run(root, args, declared_receipts):
    started = time.monotonic()
    pins, retained, handles = {}, [], []
    counts = {key: 0 for key in EXPECTED}
    max_row_difference, max_score_difference = 0.0, 0.0
    created_output = False
    out = root / BASE / 'results'

    def loaded(path, declaration=None):
        raw = path.read_bytes()
        pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if declaration is not None:
            require(pin == {key: declaration[key] for key in ('bytes', 'sha256')}, 'Input byte pin differs: ' + str(path))
        name = path.relative_to(root).as_posix()
        require(name not in pins or pins[name] == pin, 'Input changed: ' + name)
        pins[name] = pin
        return raw

    def metadata(path, sha=None):
        raw = loaded(path)
        require(sha is None or hashlib.sha256(raw).hexdigest() == sha, 'Metadata SHA differs: ' + str(path))
        return read_json_bytes(raw)

    def archive(declaration):
        raw = loaded(confined(root, declaration['path']), declaration)
        with np.load(io.BytesIO(raw), allow_pickle=False) as values:
            require(len(values.files) == len(set(values.files)), 'Duplicate NPZ members')
            return {key: values[key] for key in values.files}

    def alarm(signum, frame):
        raise TimeoutError('Independent QA CPU/wall resource cap')

    try:
        go = metadata(root / BASE / 'ROOT_GO.json', args.root_go_sha256)
        require(go['status'] == 'GO_INDEPENDENT_SAVED_OFF_ADJACENT_QA'
                and go['qa_sha256'] == args.qa_sha256
                and go['primary_scope_sha256'] == args.scope_sha256
                and go['primary_receipt_sha256s'] == declared_receipts
                and go['CPU_cap_s'] == CPU_CAP and go['wall_cap_s'] == WALL_CAP
                and go['memory_cap_bytes'] == RAM_CAP and go['output_cap_bytes'] == OUTPUT_CAP,
                'Separate root QA GO differs')
        require(all(re.fullmatch('[0-9a-f]{40}', go[key]) for key in
                    ('primary_public_freeze_commit', 'qa_public_freeze_commit')), 'Exact public freeze identities required')
        signal.signal(signal.SIGALRM, alarm)
        signal.signal(signal.SIGXCPU, alarm)
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
        resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
        signal.alarm(WALL_CAP)
        for path in (root / PRIMARY / 'SLOT0.lock', root / PRIMARY / 'SLOT1.lock',
                     root / BASE / 'ACTIVE_QA_FLOCK.lock'):
            handle = path.open('a+b')
            handles.append(handle)
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        scope = metadata(root / PRIMARY / 'scope.json', args.scope_sha256)
        require(scope['widths_channels'] == [1, 3]
                and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}
                and [(item['native_chunk_index'], item['core_q']) for item in scope['core_domains']] == list(DOMAINS)
                and scope['excluded_outer_cores'] == [[170, 0], [172, 255]]
                and scope['masks'] is None and scope['data_selected_exclusions'] == []
                and scope['core_channels'] == CORE and scope['halo_channels'] == 4000,
                'Primary search hypotheses differ')
        driver_path = root / PRIMARY / 'driver.py'
        require(digest(driver_path) == go['primary_driver_sha256'], 'Reviewed primary driver differs')
        loaded(driver_path)
        loaded(Path(__file__).resolve())
        require(set(go['primary_admission_pins']) == {PRIMARY + '/ROOT_GO.json', PRIMARY + '/PUBLIC_FREEZE.json'},
                'Exact original primary admission pin set required')
        primary_admission = {name: read_json_bytes(loaded(confined(root, name), declaration))
                             for name, declaration in go['primary_admission_pins'].items()}
        primary_go = primary_admission[PRIMARY + '/ROOT_GO.json']
        primary_freeze = primary_admission[PRIMARY + '/PUBLIC_FREEZE.json']
        require(primary_go['status'] == 'GO_1536_NEW_OFF_ORIGIN_MAPS'
                and primary_go['scope_sha256'] == args.scope_sha256
                and primary_go['public_freeze_commit'] == go['primary_public_freeze_commit']
                and primary_freeze['status'] == 'PASS_EXACT_CODE_SCOPE_AND_PROVENANCE_PUBLIC_READBACK_BEFORE_NEW_MAPS'
                and primary_freeze['commit'] == go['primary_public_freeze_commit']
                and primary_freeze['new_maps_executed_yet'] == 0, 'Original prospective primary public admission differs')
        for declaration in primary_freeze['files']:
            raw = loaded(confined(root, declaration['path']))
            blob = hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()
            require(declaration['exact'] is True and blob == declaration['git_blob_sha'],
                    'Original served primary freeze bytes differ')
        # Require the primary scope to pin every scientific source metadata file.
        scope_pins = {item['path']: item for item in scope['text_code_pins']}
        for name, declaration in scope_pins.items():
            loaded(confined(root, name), declaration)
        for name in (NATIVE171_SOURCE, ADJACENT_SOURCE, NATIVE171_ACQ, ADJACENT_ACQ):
            require(name in scope_pins, 'Primary scope omits source dependency pin: ' + name)
        loaded(root / READER)
        require(pins[READER]['sha256'] == READER_SHA, 'Original independent HDF reader dependency differs')
        original = metadata(root / NATIVE171_SOURCE)
        adjacent = metadata(root / ADJACENT_SOURCE)
        original_acq = metadata(root / NATIVE171_ACQ)
        adjacent_acq = metadata(root / ADJACENT_ACQ)
        identities, sources = {}, {}
        for native in NATIVES:
            manifest = original if native == 171 else adjacent['by_native_chunk'][str(native)]
            for identity in manifest['sources']:
                identities[native, identity['label']] = identity
        for native in NATIVES:
            records = original_acq['decoded_files'] if native == 171 else [
                item for item in adjacent_acq['decoded_files'] if item['native_chunk_index'] == native]
            require(len(records) == 6 and {item['scan_id'] for item in records} == set(SCANS),
                    'Source manifest lacks exact six compacts')
            for record in records:
                scan = record['scan_id']
                identity = identities[native, scan]
                header = identity['current_header']['data_attributes']
                require(header == identities[171, scan]['current_header']['data_attributes']
                        and header['fch1'] * 1e6 == FCH1 and header['foff'] * 1e6 == DF
                        and header['tsamp'] == TSAMP and record['shape'] == [16, 1, CHUNK]
                        and record['source_channel0'] == native * CHUNK
                        and [row['time_row'] for row in record['decoded_rows']] == list(range(16)),
                        'Source coordinates/rows disagree across native joins')
                prefix = 'analysis/new_visit_recovery/results/acquire' if native == 171 else 'analysis/s2017_next_native/results/acquire'
                path = confined(root, prefix + '/' + record['array_file'])
                declaration = {'path': path.relative_to(root).as_posix(), 'bytes': record['bytes'],
                               'sha256': record['file_sha256']}
                sources[native, scan] = (path, declaration, record, identity)
        require(len(sources) == 18, 'Exactly18 compact sources required')
        receipts = {}
        for target, scan in TARGETS.items():
            receipt = metadata(root / PRIMARY / 'results' / target / 'EXECUTION_RECEIPT.json', declared_receipts[target])
            require(receipt['status'].startswith('COMPLETE_') and receipt['primary_id'] == target
                    and receipt['scan_id'] == scan and receipt['scope_sha256'] == args.scope_sha256
                    and receipt['driver_sha256'] == go['primary_driver_sha256']
                    and receipt['original_acquisition_role'] == 'OFF'
                    and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED'
                    and receipt['new_telescope_HTTP_requests'] == 0
                    and receipt['new_telescope_BODY_bytes'] == 0, 'Primary terminal receipt differs')
            require(receipt['counts'] == scope['expected_counts_per_target']
                    and receipt['counts']['maps'] == 512 and receipt['counts']['score_audit_queries'] == 2051
                    and receipt['decoded_row_SHA_checks_before'] == receipt['decoded_row_SHA_checks_after'] == 48
                    and receipt['source_bytes_unchanged'] is True and receipt['detector_search_repeated'] is False
                    and 0 < receipt['process_CPU_seconds'] <= scope['CPU_cap_s_per_job']
                    and 0 < receipt['wall_seconds'] <= scope['wall_cap_s_per_job']
                    and 0 < receipt['peak_RSS_bytes'] <= scope['memory_cap_bytes_per_job']
                    and receipt['qualified_SETI_detection'] is False and receipt['calibrated_SNR_FAP'] is False,
                    'Primary closed map/query counts differ')
            own = [sources[native, scan] for native in NATIVES]
            require(receipt['source_compact_pre_and_post_pins'] == [item[1] for item in own]
                    and receipt['decoded_source_row_checks'] == [
                        {'source': item[1], 'decoded_rows': item[2]['decoded_rows'], 'rows_verified': 16} for item in own],
                    'Actual primary source/decoded-row receipt evidence differs')
            receipts[target] = receipt
        # Numerical runtime initialization occurs after metadata and receipt admission.
        global np
        import numpy as np
        spec = importlib.util.spec_from_file_location('off_adjacent_independent_reader', root / READER)
        reader = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reader
        spec.loader.exec_module(reader)
        h5py, _, _ = reader.current_codecs()
        runtime = {'Python': sys.version.split()[0],
                   **{name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'h5py', 'hdf5plugin')},
                   'HDF5': h5py.version.hdf5_version}
        require(all(receipt['runtime_versions'] == runtime for receipt in receipts.values()),
                'Primary and independent QA numerical runtimes differ')
        drift_grid = np.linspace(-4.0, 4.0, 785)
        powers = {}
        # Authenticate every whole compact and decoded row before opening any new QA output.
        for key, (path, declaration, record, identity) in sorted(sources.items()):
            stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb')
            retained.append(stream)
            stat = os.fstat(stream.fileno())
            h = hashlib.sha256()
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
            require(stat.st_size == declaration['bytes'] and h.hexdigest() == declaration['sha256'],
                    'Authenticated source whole-file SHA differs')
            pins[declaration['path']] = {key: declaration[key] for key in ('bytes', 'sha256')}
            stream.seek(0)
            with h5py.File(stream, 'r', rdcc_nbytes=0) as handle:
                data = handle['data']
                native, scan = key
                require(data.shape == (16, 1, CHUNK) and data.dtype == np.dtype('<f4')
                        and int(data.attrs['original_source_frequency_chunk_origin']) == native * CHUNK
                        and data.attrs['original_source_url'] == identity['url']
                        and data.attrs['original_source_etag'] == identity['etag'], 'Compact H5 source identity differs')
                power = data[:, 0, :]
            require(np.isfinite(power).all() and (power >= 0).all(), 'Source power is invalid')
            for row in record['decoded_rows']:
                require(row['decoded_bytes'] == CHUNK * 4
                        and hashlib.sha256(power[row['time_row']].tobytes()).hexdigest() == row['decoded_sha256'],
                        'Authenticated decoded row SHA differs')
                counts['source_decoded_rows'] += 1
            powers[key] = power
            handles.append((path, stream, stat))
            counts['source_compacts'] += 1
        out.mkdir(parents=True, exist_ok=False)
        created_output = True
        create_json(out / 'INPUT_ADMISSION.json', {'status': 'SOURCE_AND_THREE_RECEIPTS_ADMITTED',
                    'qa_sha256': args.qa_sha256, 'root_go_sha256': args.root_go_sha256,
                    'primary_receipt_sha256s': declared_receipts,
                    'source_compacts': counts['source_compacts'], 'source_decoded_rows': counts['source_decoded_rows'],
                    'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL}})
        norm_fields = {'row_power_median', 'row_residual_median', 'row_winsorized_residual_location',
                       'row_residual_MAD_scale', 'normalization_unmasked_counts',
                       'normalization_source_channel_interval_half_open'}
        map_schema = {'frequency_hz_at_tref': ('<f8', (CORE,)),
                      'maximum_robust_box_track_score': ('<f8', (CORE,)), 'winning_drift_hz_s': ('<f8', (CORE,)),
                      'winning_width_channels': ('<i2', (CORE,)), 'valid_hypothesis_count': ('<i8', (CORE,)),
                      'source_reference_channels': ('<i8', (CORE,)), 'drift_grid_hz_s': ('<f8', (785,))}
        selected_all = {}
        for target, scan in TARGETS.items():
            job = root / PRIMARY / 'results' / target
            maps, audits = metadata(job / 'MAPS.json'), metadata(job / 'SCORE_AUDITS.json')
            top20, top3 = metadata(job / 'TOP20.json'), metadata(job / 'TOP3.json')
            for value in (maps, audits, top20, top3):
                require(value['primary_id'] == target and value['scan_id'] == scan, 'Saved target identity differs')
            require(maps['schema'] == 'SETI_ORIGINAL_OFF_ADJACENT_MAPS_V1'
                    and audits['schema'] == 'SETI_ORIGINAL_OFF_ADJACENT_SCORE_AUDITS_V1'
                    and all(value['schema'] == 'SETI_ORIGINAL_OFF_TARGET_GLOBAL512_RANKS_V1'
                            and value['selection_rule'] == scope['ranking_rule']
                            and value['original_acquisition_role'] == 'OFF'
                            and value['reference_time_mjd'] == identities[171, scan]['current_header']['data_attributes']['tstart'] + TSAMP / (2 * 86400)
                            for value in (top20, top3)), 'Saved inventories/ranking method metadata differs')
            require([(item['native_chunk_index'], item['core_q']) for item in maps['records']] == list(DOMAINS),
                    'Exact512 prospective map domains differ')
            joined = np.concatenate([powers[native, scan] for native in NATIVES], axis=1)
            infos, blocks, channels_blocks = {}, [], []
            header = identities[171, scan]['current_header']['data_attributes']
            for declaration in maps['records']:
                native, q = declaration['native_chunk_index'], declaration['core_q']
                key = native, q
                channel0 = native * CHUNK + q * CORE
                channels = np.arange(channel0, channel0 + CORE, dtype=np.int64)
                expected_map_id = '%s_native%d_q%03d' % (scan, native, q)
                require(declaration['reference_channel_interval_half_open'] == [channel0, channel0 + CORE]
                        and declaration['loaded_channel_interval_half_open'] == [channel0 - 4000, channel0 + CORE + 4000]
                        and declaration['map_id'] == expected_map_id
                        and declaration['path'] == (job / (expected_map_id + '.npz')).relative_to(root).as_posix()
                        and declaration['searched_carriers'] == CORE
                        and declaration['valid_hypotheses_per_carrier'] == 1570
                        and declaration['original_acquisition_role'] == 'OFF', 'Saved map source support differs')
                value = archive(declaration)
                normalization = declaration['normalization']
                require(normalization['path'] == (job / (expected_map_id + '_normalization.json')).relative_to(root).as_posix(),
                        'Canonical map normalization path differs')
                normal = read_json_bytes(loaded(confined(root, normalization['path']), normalization))
                require(set(value) == set(map_schema) and set(normal) == norm_fields, 'Map/normalization fields differ')
                for field, (dtype, shape) in map_schema.items():
                    require(value[field].dtype == np.dtype(dtype) and value[field].shape == shape
                            and np.isfinite(value[field]).all(), 'Map dtype/shape/finite differs: ' + field)
                arrays_equal(value['source_reference_channels'], channels, 'Map physical carrier coordinates differ')
                arrays_equal(value['frequency_hz_at_tref'], FCH1 + DF * channels, 'Map carrier frequencies differ')
                arrays_equal(value['drift_grid_hz_s'], drift_grid, 'Map drift grid differs')
                arrays_equal(value['valid_hypothesis_count'], np.full(CORE, 1570), 'Map carrier support count differs')
                require(np.isin(value['winning_drift_hz_s'], drift_grid).all()
                        and np.isin(value['winning_width_channels'], (1, 3)).all(), 'Map winning tuple outside family')
                arrays_equal(normal['normalization_source_channel_interval_half_open'], [channel0, channel0 + CORE],
                             'Normalization core coordinates differ')
                arrays_equal(normal['normalization_unmasked_counts'], np.full(16, CORE), 'Normalization masked support differs')
                for field in norm_fields - {'normalization_source_channel_interval_half_open', 'normalization_unmasked_counts'}:
                    terms = np.asarray(normal[field])
                    require(terms.shape == (16,) and np.isfinite(terms).all(), 'Invalid16 normalization parameters')
                require(np.all(np.asarray(normal['row_power_median']) > 0)
                        and np.all(np.asarray(normal['row_residual_MAD_scale']) > 0), 'Normalization scales nonpositive')
                start = channel0 - 170 * CHUNK
                arrays_equal(np.median(joined[:, start:start + CORE].astype(np.float64), axis=1),
                             normal['row_power_median'], 'Independent raw4096 row medians differ')
                order = np.lexsort((channels, -value['maximum_robust_box_track_score']))
                infos[key] = {'arrays': value, 'normal': normal, 'record': declaration, 'order': order}
                blocks.append(value['maximum_robust_box_track_score'])
                channels_blocks.append(channels)
                counts['maps'] += 1
                counts['carrier_maxima'] += CORE
                counts['valid_hypothesis_records'] += int(value['valid_hypothesis_count'].sum())
                counts['core_row_medians'] += 16

            def tuple_record(key, index, rank=None):
                native, q = key
                info = infos[key]
                value = info['arrays']
                drift = float(value['winning_drift_hz_s'][index])
                result = {'primary_id': target, 'primary_target': header['source_name'], 'scan_id': scan,
                          'original_acquisition_role': 'OFF', 'native_chunk_index': native, 'core_q': q,
                          'map_id': info['record']['map_id'], 'carrier_index_in_core': int(index),
                          'reference_source_channel': int(value['source_reference_channels'][index]),
                          'frequency_hz_at_own_first_midpoint': float(value['frequency_hz_at_tref'][index]),
                          'reference_time_mjd': header['tstart'] + TSAMP / (2 * 86400),
                          'drift_grid_index': int(np.flatnonzero(drift_grid == drift)[0]), 'drift_hz_s': drift,
                          'width_channels': int(value['winning_width_channels'][index]),
                          'score': float(value['maximum_robust_box_track_score'][index])}
                if rank is not None:
                    result['rank'] = rank
                return result

            all_scores, all_channels = np.concatenate(blocks), np.concatenate(channels_blocks)
            require(len(all_channels) == len(np.unique(all_channels)) == 512 * CORE,
                    'Pooled physical reference domains overlap or are incomplete')
            ranking = np.lexsort((all_channels, -all_scores))
            selected = []
            for position in ranking:
                channel = int(all_channels[position])
                if any(abs(channel - old['reference_source_channel']) <= 3 for old in selected):
                    continue
                native, q = channel // CHUNK, (channel % CHUNK) // CORE
                selected.append(tuple_record((native, q), channel % CORE, len(selected) + 1))
                if len(selected) == 20:
                    break
            require(top20['records'] == selected and top3['records'] == selected[:3],
                    'Independent pooled deterministicTOP20/3 differs')
            counts['top20_entries'] += 20
            counts['top3_entries'] += 3
            selected_all[target] = selected[:3]
            expected_query_keys = {(native, q, kind) for native, q in DOMAINS
                                   for kind in ('first', 'midpoint', 'last', 'core_max')}
            seen_queries = set()
            seen_global = set()
            require(len(audits['records']) == 2051, 'Per-target2051 raw queries required')
            for query in audits['records']:
                key = query['native_chunk_index'], query['core_q']
                kind = query['query_kind']
                require(key in infos and query['normalization'] == infos[key]['record']['normalization'],
                        'Audit normalization or domain differs')
                if kind == 'global_top3':
                    rank = query['selected_tuple']['rank']
                    require(rank in (1, 2, 3) and rank not in seen_global, 'Duplicate/outside global audit rank')
                    seen_global.add(rank)
                    expected_tuple = selected[rank - 1]
                else:
                    query_key = key + (kind,)
                    require(query_key in expected_query_keys and query_key not in seen_queries,
                            'Duplicate or unexpected percore audit')
                    seen_queries.add(query_key)
                    index = {'first': 0, 'midpoint': 2048, 'last': 4095,
                             'core_max': int(infos[key]['order'][0])}[kind]
                    expected_tuple = tuple_record(key, index)
                require(query['selected_tuple'] == expected_tuple and query['map_id'] == expected_tuple['map_id'],
                        'Deterministic audit tuple differs')
                expected_query_id = 'global_top%02d' % expected_tuple['rank'] if kind == 'global_top3' else (
                    'native%d_q%03d_%s' % (key[0], key[1], kind))
                require(query['query_id'] == expected_query_id
                        and query['capsule']['path'] == (job / (expected_query_id + '_raw503.npz')).relative_to(root).as_posix(),
                        'Canonical raw503 query identity differs')
                capsule = archive(query['capsule'])
                require(set(capsule) == {'raw_power', 'rounded_absolute_centers', 'standardized_row_box_sums'},
                        'Raw capsule fields differ')
                for field, dtype, shape in (('raw_power', '<f4', (16, 503)),
                                           ('rounded_absolute_centers', '<i8', (16,)),
                                           ('standardized_row_box_sums', '<f8', (16,))):
                    require(capsule[field].dtype == np.dtype(dtype) and capsule[field].shape == shape
                            and np.isfinite(capsule[field]).all(), 'Capsule precision/shape differs')
                centers = centers_for(expected_tuple['frequency_hz_at_own_first_midpoint'], expected_tuple['drift_hz_s'])
                indexes = centers[:, None] - 170 * CHUNK + np.arange(-251, 252)[None, :]
                require(indexes.min() >= 0 and indexes.max() < 3 * CHUNK, 'Raw503 support leaves source triplet')
                raw = joined[np.arange(16)[:, None], indexes]
                arrays_equal(capsule['rounded_absolute_centers'], centers, 'Absolute trajectory rounding differs')
                arrays_equal(capsule['raw_power'].view(np.uint32), raw.view(np.uint32), 'Raw503 source bits differ')
                rows, score = independent_rows(raw, infos[key]['normal'], expected_tuple['width_channels'])
                arrays_near(capsule['standardized_row_box_sums'], rows, 'Independent local501 row-box arithmetic differs')
                arrays_near(expected_tuple['score'], score, 'Independent queried map score differs')
                max_row_difference = max(max_row_difference, float(np.max(np.abs(capsule['standardized_row_box_sums'] - rows))))
                max_score_difference = max(max_score_difference, abs(score - expected_tuple['score']))
                counts['score_audit_queries'] += 1
                counts['independent_scores'] += 1
                counts['raw_power_cells'] += raw.size
            require(seen_queries == expected_query_keys and seen_global == {1, 2, 3}, 'Audit matrix incomplete')
            output_declarations = receipts[target]['output_byte_pins']
            output_names = {item['path'] for item in output_declarations}
            require(len(output_names) == len(output_declarations) == 3079, 'Duplicate/incomplete terminal output pins')
            observed_names = {name for name in pins if name.startswith(job.relative_to(root).as_posix() + '/')
                              and not name.endswith('/EXECUTION_RECEIPT.json')}
            require(output_names == observed_names, 'Terminal output inventory differs from checked files')
            actual_names = {path.relative_to(root).as_posix() for path in job.rglob('*') if path.is_file()}
            require(actual_names == output_names | {job.relative_to(root).as_posix() + '/EXECUTION_RECEIPT.json'},
                    'Primary output directory has unexpected or absent files')
            for declaration in output_declarations:
                require(pins[declaration['path']] == {key: declaration[key] for key in ('bytes', 'sha256')},
                        'Closed output byte pin differs')
            del joined, infos, all_scores, all_channels, blocks, channels_blocks, ranking
            print('PASS_SAVED_OFF_ADJACENT_TARGET', target, flush=True)
        require(counts == EXPECTED, 'Independent QA counts incomplete')
        # Rehash all observed bytes and retained descriptor identities before PASS.
        for item in handles:
            if isinstance(item, tuple):
                path, stream, before = item
                after, current = os.fstat(stream.fileno()), path.stat(follow_symlinks=False)
                require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
                        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                        and (current.st_dev, current.st_ino) == (before.st_dev, before.st_ino),
                        'Retained source descriptor/path changed')
        for name, declaration in pins.items():
            path = confined(root, name)
            require(path.stat().st_size == declaration['bytes'] and digest(path) == declaration['sha256'],
                    'Input changed during QA: ' + name)
        usage = {'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP
                and 0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'QA resource bounds exceeded')
        receipt = {'schema': 'SETI_OFF_ADJACENT_SAVED_INDEPENDENT_QA_V1',
                   'status': 'PASS1536_MAPS6153_RAW503_QUERIES288_SOURCE_ROWS_NO_DETECTOR_RERUN',
                   'counts': counts, 'qa_sha256': args.qa_sha256, 'primary_scope_sha256': args.scope_sha256,
                   'primary_driver_sha256': go['primary_driver_sha256'],
                   'primary_receipt_sha256s': declared_receipts, 'root_go_sha256': args.root_go_sha256,
                   'primary_public_freeze_commit': go['primary_public_freeze_commit'],
                   'qa_public_freeze_commit': go['qa_public_freeze_commit'],
                   'selected_top3': selected_all, 'input_byte_pins': pins,
                   'numeric_tolerance': {'absolute': ATOL, 'relative': RTOL},
                   'max_row_sum_arithmetic_absolute_difference': max_row_difference,
                   'max_score_arithmetic_absolute_difference': max_score_difference,
                   'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
                   'output_cap_bytes': OUTPUT_CAP, **usage,
                   'runtime_versions': runtime,
                   'detector_imported': False, 'full_grid_recomputed': False,
                   'full_core_MAD_location_independently_refiltered': False,
                   'raw_core_row_medians_independently_recomputed': True,
                   'new_telescope_HTTP_requests': 0, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
                   'limitations': ['Scores are empirical robust box-track scores, not calibrated SNR/FAP.',
                                   'Audited raw503 queries are conditional on saved fullcore MAD/location.',
                                   'No exhaustive independent drift/width maximization or sky-origin validation.',
                                   'OriginalOFF roles and one historical scan per primary star are preserved.']}
        create_json(out / 'QA_RECEIPT.json', receipt)
        require(sum(path.stat().st_size for path in out.iterdir() if path.is_file()) <= OUTPUT_CAP,
                'Independent QA output bound exceeded')
        print(receipt['status'], flush=True)
    except BaseException as error:
        if created_output and not (out / 'QA_RECEIPT.json').exists():
            create_json(out / 'QA_FAILURE.json', {'status': 'FAIL_INDEPENDENT_OFF_ADJACENT_QA',
                        'error_type': type(error).__name__, 'message': str(error), 'partial_counts': counts,
                        'wall_seconds': time.monotonic() - started,
                        'detector_imported': False, 'full_grid_recomputed': False})
        raise
    finally:
        signal.alarm(0)
        for item in handles:
            if not isinstance(item, tuple):
                item.close()
        for stream in retained:
            stream.close()


if __name__ == '__main__':
    main()
