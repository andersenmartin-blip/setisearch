"""Continue two unreached internal boundaries with unchanged scientific functions.

This recovery driver adds one separate execution after a confirmed pre-value
lock failure; firstpair154155 is complete and is never executed here. It does not change or replace historical receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import fcntl
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
import time

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
PAIRS = {'157_158': (157, 158)}
COUNT, JOINED, CPU_CAP, WALL_CAP, MEMORY_CAP = 1048576, 2097152, 180, 1800, 4 * 1024**3
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'matplotlib': '3.10.8', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0'}
STAGE = 'results/continuation_boundary_recovery_20261010'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for data in iter(lambda: handle.read(1024**2), b''):
            h.update(data)
    return h.hexdigest()


def save(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(target)


def confined(root, name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or not (root / p).resolve().is_relative_to(root):
        raise ValueError('Metadata/code path must stay inside project: ' + name)
    return root / p


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_pins(root, scope):
    for name, pin in scope['pinned_metadata_and_code'].items():
        path = confined(root, name)
        if path.stat().st_size != pin['bytes'] or digest(path) != pin['sha256']:
            raise ValueError('Frozen metadata/code differs: ' + name)


def metadata_contract(root, scope, pair):
    expected = {
        'schema': 'SETI_PREVALUE_LOCK_FAILURE_RECOVERY157158_V1',
        'native_pairs': [[157, 158]], 'pair_ids': ['pair157_158'],
        'rows_per_scan': 16, 'native_channel_count': COUNT, 'joined_channel_count': JOINED,
        'scan_order': list(SCANS), 'joined_reference_core_q': [255, 256],
        'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
        'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 763},
        'widths_channels': [1, 3], 'core_channel_count': 4096, 'crop_halo_channels': 4000,
        'profile_halfwidth_channels': 64, 'profile_shift_channels': 0,
        'CPU_cap_s_per_pair': CPU_CAP, 'wall_cap_s_per_pair': WALL_CAP,
        'memory_cap_bytes_per_pair': MEMORY_CAP, 'numeric_pairs_serial': True,
        'output_stage': STAGE, 'new_telescope_requests': 0, 'new_telescope_body_bytes': 0,
        'cost_DKK': 0, 'protected_native_chunks_not_read': [156, 159],
        'original_receipts_reclassified_or_overwritten': False,
        'one_historical_visit': True, 'independent_or_blind_validation': False,
        'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
        'A_B': 'FAIL_CLOSED_UNCHANGED', 'runtime_package_versions': VERSIONS,
        'joined_profile_normalization': 'median of all2097152 joined raw float32 channels in each row, then float64 promotion (NumPy2.3.5)',
    }
    if any(scope.get(k) != value for k, value in expected.items()):
        raise ValueError('Scope differs from implemented continuation family')
    if digest(__file__) != scope['driver_sha256']:
        raise ValueError('Continuation driver differs from prospective freeze')
    check_pins(root, scope)
    prior = scope['prior_execution_gate']
    complete = json.loads(confined(root, prior['first_pair_complete_path']).read_bytes())
    failure = json.loads(confined(root, prior['second_pair_prevalue_failure_path']).read_bytes())
    if (complete.get('status') != 'COMPLETE_TWO_JOINED_BOUNDARY_CORES_CONTINUATION_EXPLORATORY_ONLY'
        or complete.get('pair_id') != 'pair154_155' or complete.get('source_chunk_ids') != [154, 155]
        or complete.get('search_summary', {}).get('completed_scan_tiles') != 6
        or complete.get('fixed_profile_summary', {}).get('profile_count') != 9
        or complete.get('scope_sha256') != prior['original_scope_sha256']
        or complete.get('public_freeze_commit') != prior['original_freeze_commit']
        or failure.get('status') != 'INCOMPLETE_CONTINUATION_PRESERVE_OUTPUTS'
        or failure.get('pair_id') != 'pair157_158' or failure.get('error_type') != 'FileExistsError'
        or failure.get('completed_scan_tiles') != 0 or failure.get('completed_profiles') != 0
        or failure.get('scope_sha256') != prior['original_scope_sha256']
        or failure.get('public_freeze_commit') != prior['original_freeze_commit']):
        raise ValueError('Require preserved firstpair COMPLETE and secondpair pre-value-only lock failure')
    for name, version in VERSIONS.items():
        if importlib.metadata.version(name) != version:
            raise ValueError('Package differs: ' + name)
    chunks = PAIRS[pair]
    sources, acquisitions, contexts = {}, {}, {}
    for chunk in chunks:
        context = scope['chunk_contracts'][str(chunk)]
        contexts[str(chunk)] = context
        source = json.loads(confined(root, context['source_manifest_path']).read_bytes())
        acq = json.loads(confined(root, context['acquisition_summary_path']).read_bytes())
        qa = json.loads(confined(root, context['acquisition_QA_path']).read_bytes())
        if (source['native_chunk_index'] != chunk
            or source['physical_channel_interval_half_open'] != [chunk * COUNT, (chunk + 1) * COUNT]
            or [x['label'] for x in source['sources']] != list(SCANS)
            or [x['role'].upper() for x in source['sources']] != ['ON', 'OFF'] * 3
            or acq['status'] != 'COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY'
            or acq['source_manifest_sha256'] != context['source_manifest_sha256']
            or acq['source_channel0'] != chunk * COUNT
            or qa['status'] != 'PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS'
            or qa['acquisition_result_sha256'] != context['acquisition_summary_sha256']
            or qa['source_manifest_sha256'] != context['source_manifest_sha256']
            or acq['decoded_files'] != context['compact_files_and_96_decoded_row_pins']):
            raise ValueError('Source/acquisition/QA identity differs')
        records = acq['decoded_files']
        if len(records) != 6 or {x['scan_id'] for x in records} != set(SCANS):
            raise ValueError('Require six distinct compact source files')
        for record in records:
            if (record['shape'] != [16, 1, COUNT] or record['source_channel0'] != chunk * COUNT
                or [x['time_row'] for x in record['decoded_rows']] != list(range(16))
                or any(x['decoded_bytes'] != COUNT * 4 for x in record['decoded_rows'])):
                raise ValueError('Compact/row geometry differs')
        for item in source['sources']:
            head = item['current_header']
            attrs = head['data_attributes']
            if (attrs['tsamp'] != TSAMP or attrs['fch1'] * 1e6 != FCH1 or attrs['foff'] * 1e6 != DF
                or head['dataset_shape'] != [16, 1, 264503296]
                or head['dataset_chunks'] != [1, 1, COUNT] or head['dataset_dtype'] != 'float32'):
                raise ValueError('Original source header geometry differs')
            rows = item['chunks']
            if len(rows) != 16 or [x['time_row'] for x in rows] != list(range(16)):
                raise ValueError('Require all16 source row descriptors')
            for i, row in enumerate(rows):
                if (row['chunk_origin'] != [i, 0, chunk * COUNT] or row['decoded_size'] != COUNT * 4
                    or row['filter_mask'] != 0 or row['stored_size'] <= 0 or row['byte_offset'] < 0
                    or row['byte_offset'] + row['stored_size'] > item['source_file_bytes']
                    or row['byte_range'] != f"bytes={row['byte_offset']}-{row['byte_offset'] + row['stored_size'] - 1}"):
                    raise ValueError('Source row byte descriptor differs')
        sources[str(chunk)], acquisitions[str(chunk)] = source, acq
    left, right = (sources[str(chunk)] for chunk in chunks)
    if left['physical_channel_interval_half_open'][1] != right['physical_channel_interval_half_open'][0]:
        raise ValueError('Native source bands must be contiguous')
    for l, r in zip(left['sources'], right['sources']):
        if any(l[key] != r[key] for key in ('label', 'role', 'url', 'etag', 'source_file_bytes', 'current_header')):
            raise ValueError('Paired scan/header identities differ')
    anchor = float(min(x['current_header']['data_attributes']['tstart'] for x in left['sources']))
    previous_end = -math.inf
    for item in left['sources']:
        start = (item['current_header']['data_attributes']['tstart'] - anchor) * 86400
        if start < previous_end:
            raise ValueError('Require actual chronological, non-overlapping scans')
        previous_end = start + 16 * TSAMP
    return sources, acquisitions, contexts, anchor


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_including_imports': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'scope', 'expected-scope-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--pair', choices=tuple(PAIRS), required=True)
    parser.add_argument('--check-only', action='store_true', help='Validate metadata/code only; no signal values or outputs')
    parser.add_argument('--root-go-after-review', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not re.fullmatch('[0-9a-f]{40}', args.freeze_commit):
        raise ValueError('Require the actual public prospective freeze commit')
    if digest(args.scope) != args.expected_scope_sha256:
        raise ValueError('Scope differs from prospective freeze')
    scope = json.loads(Path(args.scope).read_bytes())
    sources, acquisitions, contexts, anchor = metadata_contract(root, scope, args.pair)
    boundary = load_module('unchanged_boundary_continuation', root / scope['scientific_code_paths']['boundary'])
    boundary.ROOT = root
    admission = boundary.runtime_158_gate({'runtime_158_admission': scope['runtime_158_admission']}, 'pair' + args.pair)
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_CODE_NO_VALUES', 'pair_id': 'pair' + args.pair,
                          'scope_sha256': args.expected_scope_sha256, 'runtime_158_receipts': admission}))
        return
    if not args.root_go_after_review:
        raise ValueError('Require root GO after prospective review/readback')
    out = root / STAGE / ('pair' + args.pair) / 'measurement'
    out.mkdir(parents=True, exist_ok=False)
    lock = root / 'results/continuation_boundaries_20261010/NUMERIC_ACTIVE_FLOCK.lock'
    lock_handle = None
    def deadline(signum, frame):
        raise RuntimeError('Frozen continuation CPU/wall deadline reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    try:
        lock_handle = lock.open('a+b')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_handle.write(('recovery157158 pid=' + str(os.getpid()) + '\n').encode())
        lock_handle.flush()
        save(out / 'INPUT_PINS.json', {'schema': scope['schema'], 'scope_sha256': args.expected_scope_sha256,
            'driver_sha256': digest(__file__), 'freeze_commit': args.freeze_commit,
            'pair_id': 'pair' + args.pair, 'pinned_metadata_and_code': scope['pinned_metadata_and_code'],
            'runtime_158_admission_receipts': admission, 'source_contracts': contexts,
            'new_family_after_pre_numerical_failure_or_unstarted_pair': True})
        sys.path.insert(0, str(root))
        import numpy as np
        boundary.np = np
        fresh = load_module('unchanged_fresh_continuation', root / scope['scientific_code_paths']['fresh'])
        gap = load_module('unchanged_gap_continuation', root / scope['scientific_code_paths']['gap'])
        fresh.ROOT = gap.ROOT = root
        fresh.np = gap.np = np
        chunks = PAIRS[args.pair]
        source0 = chunks[0] * COUNT
        gap.C0, gap.COUNT = source0, JOINED
        gap.NORMALIZATION_PATH = (out / 'NORMALIZATION.json').relative_to(root).as_posix()
        arrays, verified = boundary.load_joined(fresh, sources, acquisitions, contexts, chunks)
        norm = boundary.normalization(arrays, source0, chunks, out)
        tops, search = boundary.run_search(fresh, arrays, sources[str(chunks[0])], anchor, out,
                                          'pair' + args.pair, chunks, (255, 256), source0)
        profiles = gap.fixed_profiles(arrays, sources[str(chunks[0])], norm, tops, anchor, out)
        profiles['row_normalization_context'] = scope['joined_profile_normalization']
        check_pins(root, scope)
        if digest(args.scope) != args.expected_scope_sha256 or digest(__file__) != scope['driver_sha256']:
            raise ValueError('Scope/driver changed during execution')
        for chunk in chunks:
            for record in acquisitions[str(chunk)]['decoded_files']:
                path = confined(root, contexts[str(chunk)]['compact_directory']) / record['array_file']
                if path.stat().st_size != record['bytes'] or digest(path) != record['file_sha256']:
                    raise ValueError('Compact input changed during execution')
        if boundary.runtime_158_gate({'runtime_158_admission': scope['runtime_158_admission']}, 'pair' + args.pair) != admission:
            raise ValueError('Original158 admission receipt changed during execution')
        use = measured(started)
        if (use['process_CPU_seconds_including_imports'] > CPU_CAP
            or use['wall_seconds_including_imports'] > WALL_CAP or use['peak_RSS_bytes'] > MEMORY_CAP):
            raise RuntimeError('Measured execution exceeds explicit new-family bounds')
        if search['completed_scan_tiles'] != 6 or profiles['profile_count'] != 9:
            raise ValueError('Incomplete continuation output family')
        receipt = {'status': 'COMPLETE_TWO_JOINED_BOUNDARY_CORES_RECOVERY157158_EXPLORATORY_ONLY',
            'pair_id': 'pair' + args.pair, 'source_chunk_ids': list(chunks), 'fixed_pair_q': [255, 256],
            'scope_sha256': args.expected_scope_sha256, 'driver_sha256': digest(__file__),
            'public_freeze_commit': args.freeze_commit, 'prior_execution_gate': scope['prior_execution_gate'],
            'kernel_lock_method': 'fcntl.flock LOCK_EX|LOCK_NB held until finallyclose; retained file existence is harmless', 'search_summary': search, 'fixed_profile_summary': profiles,
            'verified_source_inputs': verified, 'runtime_158_admission_receipts': admission,
            'compact_files_verified': 12, 'decoded_row_SHA256s_verified': 192,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
            'new_telescope_requests': 0, 'new_telescope_body_bytes': 0, 'cost_DKK': 0,
            'original_receipts_reclassified_or_overwritten': False,
            'one_historical_visit': True, 'blind_or_independent_validation': False,
            'calibrated_SNR_FAP': False, 'qualified_SETI_detection': False,
            'A_B': 'FAIL_CLOSED_UNCHANGED', 'limitations': scope['limitations'], **use}
        save(out / 'EXECUTION_RECEIPT.json', receipt)
        print(json.dumps({k: receipt[k] for k in ('status', 'pair_id', *use)}), flush=True)
    except BaseException as exc:
        save(out / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_RECOVERY157158_PRESERVE_OUTPUTS',
            'pair_id': 'pair' + args.pair, 'error_type': type(exc).__name__, 'error': str(exc),
            'scope_sha256': args.expected_scope_sha256, 'public_freeze_commit': args.freeze_commit,
            'original_receipts_reclassified_or_overwritten': False, **boundary.partial_counts(out), **measured(started)})
        raise
    finally:
        signal.alarm(0)
        if lock_handle is not None:
            lock_handle.close()


if __name__ == '__main__':
    main()
