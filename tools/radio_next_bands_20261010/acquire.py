"""Once-only bounded acquisition for prospectively selected chunks153/154.

Reuses the unchanged ordinary HDF5/filter/range helpers. Never invokes the old
qualified pilot, its gated run(), or its validation/source admission function.
No HTTP or native imports occur at module import. Execution needs a public,
SHA-pinned scope, pinned source manifest and empty new output directory.
"""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--scope', required=True)
    args.add_argument('--expected-scope-sha256', required=True)
    arg = args.parse_args()
    started = time.monotonic()
    # Absolute process CPU includes prior module setup; child processes are not used.
    scope_path = Path(arg.scope).resolve()
    require(digest(scope_path) == arg.expected_scope_sha256, 'Frozen acquisition scope changed')
    scope = json.loads(scope_path.read_text())
    require(scope['schema'] == 'SETI_NEXT_NATIVE_BAND_ONCE_ACQUISITION_V1', 'Unexpected acquisition scope schema')
    for name, pin in scope['pinned_files'].items():
        require(digest(ROOT / name) == pin, 'Frozen file mismatch: ' + name)
    require(scope['CPU_limit_s'] == 60 and scope['wall_limit_s'] == 1200
            and scope['memory_limit_bytes'] == 4294967296, 'Unexpected acquisition bounds')
    require(scope['max_value_GETs'] == 96 and scope['attempts'] == 1
            and scope['retry_or_resume_authorized'] is False, 'Single attempt is required')
    manifest = json.loads((ROOT / scope['source_manifest']).read_text())
    require(manifest['status'] == 'OFFLINE_METADATA_PINNED_FOR_SEPARATE_EXPLORATORY_ACQUISITION'
            and manifest['new_band_values_opened'] is False, 'Manifest must predate selected values')
    chunk = scope['native_chunk_index']
    require(chunk in [153, 154] and manifest['native_chunk_index'] == chunk, 'Unexpected native chunk')
    interval = tuple(manifest['physical_channel_interval_half_open'])
    require(interval == (chunk * 1048576, (chunk+1) * 1048576), 'Different physical chunk')
    require(manifest['protected_prior_native_chunk_indices'] == [156, 159]
            and manifest['protected_prior_native_chunk_values_opened'] is False,
            'Protected old holdouts cannot be opened')
    items = manifest['sources']
    require([x['label'] for x in items] == scope['scans'] and [x['role'] for x in items] == ['on', 'off'] * 3,
            'Six complete ordered ON/OFF scans required')
    expected = sum(x['future_spectral_payload_bytes'] for x in items)
    require(expected == scope['expected_new_spectral_BODY_bytes'] == manifest['total_future_spectral_payload_bytes'],
            'Frozen compressed payload total changed')
    for item in items:
        require(item['dtype_exact'] == '<f4' and item['current_header']['dataset_shape'] == [16, 1, 264503296]
                and item['current_header']['dataset_chunks'] == [1, 1, 1048576], 'Unexpected source geometry')
        require(len(item['chunks']) == 16, 'All16 source rows required')
        require(sum(ch['stored_size'] for ch in item['chunks']) == item['future_spectral_payload_bytes'],
                'Per-scan compressed payload total changed')
        for row, ch in enumerate(item['chunks']):
            require(ch['time_row'] == row and ch['chunk_origin'] == [row, 0, interval[0]]
                    and ch['filter_mask'] == 0 and ch['decoded_size'] == 4194304, 'Unexpected row/filter geometry')
            require(0 < ch['stored_size'] <= 5 * 1024**2 and ch['byte_offset'] >= 0
                    and ch['byte_offset'] + ch['stored_size'] <= item['source_file_bytes'], 'Source byte range out of bounds')
            require(ch['byte_range'] == f"bytes={ch['byte_offset']}-{ch['byte_offset']+ch['stored_size']-1}",
                    'Source byte range string differs')
    out = ROOT / scope['output_directory']
    out.mkdir(parents=True, exist_ok=False)
    initial = scope['prior_same_cadence_source_plus_metadata_BODY_bytes']
    initial_charged = scope['prior_same_cadence_charged_upper_bound_bytes']
    require(initial_charged >= initial, 'Charged cadence baseline must cover actual prior BODY')
    require(initial_charged + expected + 96 <= scope['same_cadence_telescope_BODY_cap_bytes'] == 2147483648,
            'Cumulative cadence BODY cap would be exceeded')
    require(scope['prospective_all_source_envelope_with_both_acquisitions_bytes']
            <= scope['all_source_BODY_cap_bytes'] == 4563402752, 'All-source BODY cap would be exceeded')
    ledger = {'source_body_bytes_received': initial, 'source_body_bytes_charged_upper_bound': initial_charged,
              'new_value_requests_attempted': 0, 'source_body_byte_ceiling': 2147483648,
              'new_activity_body_ceiling': scope['new_spectral_BODY_byte_ceiling'], 'prior_body_bytes': initial,
              'prior_charged_upper_bound_bytes': initial_charged,
              'prior_body_bytes_basis': scope['prior_body_bytes_basis'], 'complete': False}
    receipts = []
    result = {'status': 'ACQUISITION_IN_PROGRESS', 'qualification': 'FAIL_CLOSED_UNCHANGED',
              'source_manifest_sha256': digest(ROOT / scope['source_manifest']),
              'scope_sha256': digest(scope_path), 'script_sha256': digest(__file__),
              'standard_reader_sha256': scope['standard_reader_sha256'],
              'source_channel0': interval[0], 'physical_channel_interval_half_open': list(interval),
              'native_chunk_index': chunk, 'new_observation_visit': False,
              'value_read_requests': receipts, 'decoded_files': [], 'decoded_row_progress': {},
              'local_pipeline_records': [], 'whole_original_telescope_MD5_verified': False,
              'cost_DKK': 0}

    def deadline(signum, frame):
        raise TimeoutError('Bounded acquisition CPU or wall limit reached')

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(scope['wall_limit_s'])
    resource.setrlimit(resource.RLIMIT_CPU, (scope['CPU_limit_s'] - 1, scope['CPU_limit_s']))
    resource.setrlimit(resource.RLIMIT_AS, (scope['memory_limit_bytes'], scope['memory_limit_bytes']))
    save(out / 'SOURCE_BODY_LEDGER.json', ledger)
    save(out / 'ACQUISITION_RESULT.json', result)
    try:
        spec = importlib.util.spec_from_file_location('unchanged_pure_reader', ROOT / scope['standard_reader'])
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        reader.PHYSICAL_INTERVAL = interval
        h5py, plugin, np = reader.current_codecs()
        result['versions'] = {n: importlib.metadata.version(n) for n in ['h5py', 'hdf5plugin', 'numpy']}
        require(result['versions'] == scope['versions'], 'Pinned environment changed')
        result['versions']['hdf5'] = h5py.version.hdf5_version
        require(result['versions']['hdf5'] == scope['hdf5_version'], 'Bundled HDF5 version changed')
        actual_opener = urllib.request.build_opener(reader.NoRedirect())

        class ReceiptOpener:
            def open(self, request, timeout):
                # Unchanged acquire_chunk has already appended the admitted
                # request and persisted its conservative ledger reservation.
                # Persist the admitted request too BEFORE its sole HTTP call.
                save(out / 'ACQUISITION_RESULT.json', result)
                return actual_opener.open(request, timeout=timeout)

        opener = ReceiptOpener()
        for item in items:
            path = out / (item['label'] + '.compact.h5')
            decoded_rows = []
            result['decoded_row_progress'][item['label']] = decoded_rows
            with h5py.File(path, 'x', rdcc_nbytes=8 * 1024**2) as handle:
                ds, pipeline = reader.create_compact_dataset(handle, item, h5py, plugin)
                require(int(ds.attrs['original_source_frequency_chunk_origin']) == interval[0], 'Local origin changed')
                result['local_pipeline_records'].append({'scan_id': item['label'], **pipeline})
                for ch in item['chunks']:
                    require(ledger['new_value_requests_attempted'] < scope['max_value_GETs'], 'Request cap exhausted')
                    require(ledger['source_body_bytes_charged_upper_bound'] - initial_charged + ch['stored_size'] + 1
                            <= scope['new_spectral_BODY_byte_ceiling'], 'Activity BODY cap would be exceeded')
                    body = reader.acquire_chunk(item, ch, ledger, out / 'SOURCE_BODY_LEDGER.json', receipts, opener)
                    origin = (ch['time_row'], 0, 0)
                    ds.id.write_direct_chunk(origin, body, filter_mask=0)
                    mask, retained = ds.id.read_direct_chunk(origin)
                    require(mask == 0 and retained == body, 'Retained compressed row changed')
                    row = ds[ch['time_row'], 0, :]
                    require(row.shape == (1048576,) and row.dtype == np.dtype('<f4')
                            and np.isfinite(row).all() and (row >= 0).all(), 'Invalid decoded power row')
                    decoded_rows.append({'time_row': ch['time_row'], 'decoded_bytes': row.nbytes,
                                         'decoded_sha256': hashlib.sha256(row.tobytes(order='C')).hexdigest()})
                    save(out / 'ACQUISITION_RESULT.json', result)
                    print(json.dumps({'event': 'NEXT_ROW_RECEIVED', 'chunk': chunk, 'scan': item['label'],
                                      'row': ch['time_row'], 'new_bodybytes': ledger['source_body_bytes_received'] - initial}),
                          flush=True)
            result['decoded_files'].append({'scan_id': item['label'], 'array_file': path.name,
                                            'file_sha256': digest(path), 'bytes': path.stat().st_size,
                                            'source_channel0': interval[0], 'shape': [16, 1, 1048576],
                                            'decoded_rows': decoded_rows})
            save(out / 'ACQUISITION_RESULT.json', result)
        require(len(receipts) == 96 and len(result['decoded_files']) == 6, 'Incomplete cadence acquisition')
        require(ledger['source_body_bytes_received'] - initial == expected, 'Actual BODY total differs')
        require(ledger['source_body_bytes_charged_upper_bound'] - initial_charged == expected + 96,
                'Conservative charged BODY total differs')
        # Success is conditional on measured process bounds and final identity
        # readback, rather than only the earlier OS caps/admission checks.
        require(digest(scope_path) == arg.expected_scope_sha256, 'Acquisition scope changed during run')
        for name, pin in scope['pinned_files'].items():
            require(digest(ROOT / name) == pin, 'Pinned input/code changed during run: ' + name)
        measured = {'cpu_s': time.process_time(), 'wall_s': time.monotonic() - started,
                    'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(measured['cpu_s'] <= scope['CPU_limit_s'] and measured['wall_s'] <= scope['wall_limit_s']
                and measured['peak_rss_bytes'] <= scope['memory_limit_bytes'], 'Measured acquisition resource cap exceeded')
        result['completion_resource_guard'] = {'status': 'PASS_BEFORE_COMPLETE', **measured}
        result['end_of_run_pinned_file_readback'] = 'PASS_SCOPE_SCRIPT_MANIFEST_HELPER_AND_ALL_OTHER_SCOPE_PINS'
        ledger['complete'] = True
        result['status'] = 'COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY'
    except BaseException as error:
        result.update(status='FAILED_CLOSED_NO_RETRY', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result.update(cpu_s=time.process_time(), cpu_basis='absolute process CPU including module setup; no child process',
                      wall_s=time.monotonic() - started,
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      new_spectral_BODY_bytes=ledger['source_body_bytes_received'] - initial,
                      new_spectral_BODY_charged_upper_bound=ledger['source_body_bytes_charged_upper_bound'] - initial_charged)
        save(out / 'SOURCE_BODY_LEDGER.json', ledger)
        save(out / 'ACQUISITION_RESULT.json', result)
        signal.alarm(0)


if __name__ == '__main__':
    main()
