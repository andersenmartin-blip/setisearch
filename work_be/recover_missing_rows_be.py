"""Missing-only scan5 recovery: retain BB87+BC1, acquire later8 and one repeat.

No network on import or by default. The production backend uses unchanged,
hash-pinned original TREE/codec helpers. No production dispatch is released by
this source. The generic transaction is exercised only with simulation data.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import sys
import time
import traceback

sys.dont_write_bytecode = True
COUNTS = {'inherited_BB_native_rows': 87, 'inherited_BC_native_rows': 1,
          'inherited_native_rows': 88, 'new_native_rows': 8, 'total_native_rows': 96,
          'inherited_repeat_checks': 5, 'new_repeat_checks': 1}
SCHEMAS = {'BB': 'SETI_BB_DERIVED_COMPRESSED_CHUNK_V1',
           'BC': 'SETI_BC_DERIVED_COMPRESSED_CHUNK_V1',
           'BE': 'SETI_BE_DERIVED_COMPRESSED_CHUNK_V1'}


class RecoveryError(ValueError):
    pass


def check(value, message):
    if not value:
        raise RecoveryError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_read(path):
    return json.loads(Path(path).read_text())


def json_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def utc():
    return datetime.now(timezone.utc).isoformat()


def npy_header(stream, channels):
    start = stream.read(10)
    check(len(start) == 10 and start[:8] == b'\x93NUMPY\x01\x00', 'Expected NPYv1')
    length = struct.unpack('<H', start[8:])[0]
    check(0 < length <= 4096, 'Unexpected NPY header length')
    raw = stream.read(length)
    check(len(raw) == length, 'Truncated NPY header')
    try:
        value = ast.literal_eval(raw.decode('latin1').strip())
    except (SyntaxError, ValueError) as error:
        raise RecoveryError('Malformed NPY header') from error
    check(value == {'descr': '<f4', 'fortran_order': False, 'shape': (16, channels)},
          'NPY shape/dtype/order differs')
    check((10 + length) % 16 == 0, 'Unaligned NPY data')
    return start + raw


def validate_http(receipt, raw, source, *, repeat=False):
    a, b = receipt['start'], receipt['stop_inclusive']
    check(0 <= a <= b < source['size'], 'HTTP extent outside original archive')
    check(receipt['status'] == 206 and receipt['attempts'] == 1
          and receipt['failed_attempts'] == [], 'HTTP receipt is not a single genuine206')
    check(receipt['scan'] == 5 and receipt['archive_id'] == source['id']
          and receipt['url'] == source['url'] and receipt['etag'] == source['etag'],
          'HTTP source identity differs')
    check(receipt['content_range'] == f"bytes {a}-{b}/{source['size']}", 'HTTP Content-Range differs')
    check(len(raw) == receipt['bytes'] == b - a + 1
          and hashlib.sha256(raw).hexdigest() == receipt['sha256'], 'HTTP bytes/hash differ')
    check((receipt.get('kind') == 'repeat') is repeat, 'HTTP repeat scope differs')


def validate_row(record, t, plan):
    d, r, payload, decoded = (record[k] for k in ('descriptor', 'receipt', 'payload', 'decoded'))
    channel, channels = plan['channel_start'], plan['channels']
    check(d['filter_mask'] == 0 and d['chunk_offset'] == [t, 0, channel], 'Selected descriptor differs')
    a, n = d['byte_offset'], d['size']
    check(0 < n <= 8388608 and 0 <= a <= plan['source']['size'] - n, 'Bad chunk extent')
    expected_schema = SCHEMAS['BB' if t < 7 else 'BC' if t == 7 else 'BE']
    check(r['receipt_schema'] == expected_schema and r['status'] == 'DERIVED_FROM_VERIFIED_RANGES',
          'Derived receipt lineage differs')
    check((r['scan'], r['time_index'], r['start'], r['stop_inclusive'], r['bytes'])
          == (5, t, a, a + n - 1, n), 'Derived coordinate or extent differs')
    source = plan['source']
    check((r['archive_id'], r['url'], r['etag']) == (source['id'], source['url'], source['etag']),
          'Derived source identity differs')
    check(len(payload) == n and hashlib.sha256(payload).hexdigest() == r['sha256'],
          'Derived payload hash differs')
    check(r['new_HTTP_whole_chunk_receipt_claimed'] is False, 'Derived union is not wholechunkHTTP')
    check(len(decoded) == channels * 4, 'Decoded row byte length differs')
    position, pieces = a, []
    for segment in r['coverage_segments']:
        source_receipt = segment['source_receipt']
        raw = record['source_payloads'][source_receipt['receipt_relative_path']]
        validate_http(source_receipt, raw, source)
        length = segment['length']
        check(length > 0 and segment['output_offset'] == position - a
              and segment['source_start'] == position
              and segment['source_stop'] == position + length - 1, 'Derived union gap/overlap')
        check(source_receipt['start'] <= position
              and position + length - 1 <= source_receipt['stop_inclusive'], 'Source slice outside receipt')
        offset = position - source_receipt['start']
        pieces.append(raw[offset:offset + length])
        position += length
    check(position == a + n and b''.join(pieces) == payload, 'Derived source union differs')


def validate_manifest(m, plan, partial, canonical, repeat, records, mode):
    check(m['schema'] == 'HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BE_V1', 'Wrong manifest schema')
    check(all(m.get(k) == v for k, v in COUNTS.items()), 'Manifest must preserve BB87+BC1+BE8 and5+1')
    check(m['target'] == 'HIP44295' and m['primary_id'] == 65133, 'Manifest target differs')
    check(m['scan5_prior_rows_reconstructed'] == m['scan5_new_rows_decoded'] == 8,
          'Manifest scan5 counts differ')
    check(len(m['scans']) == 6 and [s['scan'] for s in m['scans']] == list(range(6)), 'Six scans required')
    check(len(m['chunk_receipts']) == 96
          and {(r['scan'], r['time_index']) for r in m['chunk_receipts']}
          == {(j, t) for j in range(6) for t in range(16)}, 'Manifest row coordinates differ')
    for receipt in m['chunk_receipts']:
        j, t = receipt['scan'], receipt['time_index']
        expected = SCHEMAS['BB' if j < 5 or t < 7 else 'BC' if t == 7 else 'BE']
        check(receipt['receipt_schema'] == expected, 'Manifest BB/BC/BE row provenance differs')
    check(len(m['repeated_chunk_receipts']) == 6
          and sorted(r['scan'] for r in m['repeated_chunk_receipts']) == list(range(6)), 'Six repeats required')
    check([r for r in m['chunk_receipts'] if r['scan'] == 5]
          == [r['receipt'] for r in records], 'Manifest scan5 receipts differ from verified records')
    check(m['repeated_chunk_receipts'][:5] == plan['prior_repeat_receipts'], 'Prior repeat receipts changed')
    check(m['repeated_chunk_receipts'][-1] == repeat['receipt'], 'New repeat not bound in manifest')
    parent_arrays = plan['parent_array_proofs']
    check(len(parent_arrays) == 5 and [r['scan'] for r in parent_arrays] == list(range(5)), 'Five parent array proofs required')
    for entry, scan in zip(parent_arrays, m['scans'][:5]):
        check(Path(scan['array_path']).resolve() == Path(entry['path']).resolve()
              and scan['array_sha256'] == entry['sha256'] == sha(entry['path']),
              'Parent canonical array identity differs')
    scan5 = m['scans'][5]
    check(Path(scan5['array_path']).resolve() == canonical.resolve()
          and scan5['array_sha256'] == sha(partial), 'Manifest final array path/hash differs')
    check(m['scientific_coverage_credit'] == 0 and m['candidate_assessment'] is None
          and m['detector_searches_executed'] == 0, 'Acquisition cannot grant science credit')
    check(m['execution_mode'] == mode, 'Simulation/production scope differs')


def execute(backend, plan, output, gate):
    """One immutable attempt. Backend transport may run only after the gate.

    SIMULATION is an explicit test scope and never produces a production marker.
    A two-file filesystem publication is not atomic; every consumer must require
    the final marker. Any caught error removes a newly promoted canonical file.
    """
    check(gate.get('authorized') is True and gate.get('mode') in ('SIMULATION', 'PRODUCTION'),
          'Missing recovery authorization')
    mode = gate['mode']
    check(plan['missing_time_indices'] == list(range(8, 16))
          and plan['prior_valid_time_indices'] == list(range(8)), 'Only eight missing rows may run')
    check(plan['row_lineage'] == {'BB': 87, 'BC': 1, 'new': 8, 'total': 96}, 'Stale recovery lineage')
    check([r['time_index'] for r in plan['prior_row_reports']] == list(range(8)), 'Eight prior rows required')
    output = Path(output).resolve()
    check(not output.exists(), 'No automatic restart or overwrite')
    output.mkdir(parents=True)
    for name in ('data', 'derived', 'transport'):
        (output / name).mkdir()
    json_new(output / 'RUN_STARTED_BE.json', {'started_utc': utc(), 'execution_mode': mode,
             'plan_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
             'science_completed': False})
    partial, canonical = output / 'data/scan5.npy.partial', output / 'data/scan5.npy'
    marker = output / ('SIMULATION_COMPLETE_BE.json' if mode == 'SIMULATION' else 'ACQUISITION_COMPLETE_BE.json')
    records, verified_prior, repeat_done, promoted, backend_closed = [], 0, False, False, False
    try:
        backend.prepare(output)
        with Path(plan['prior_scan5_array']).open('rb') as prior, partial.open('xb') as target:
            header = npy_header(prior, plan['channels'])
            check(Path(plan['prior_scan5_array']).stat().st_size == len(header) + 16 * plan['channels'] * 4,
                  'Prior NPY allocation size differs')
            target.write(header)
            for t in range(16):
                record = backend.read_row(t, allow_new=t >= 8)
                validate_row(record, t, plan)
                raw = record['decoded']
                if t < 8:
                    check(raw == prior.read(plan['channels'] * 4), 'Retained partial row differs')
                    report = plan['prior_row_reports'][t]
                    check(hashlib.sha256(raw).hexdigest() == report['decoded_row_sha256']
                          and record['receipt']['sha256'] == report['compressed_sha256'],
                          'Prior row proof differs')
                    verified_prior += 1
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
                records.append(record)
        repeat = backend.repeat_row7(records[7])
        validate_http(repeat['receipt'], repeat['payload'], plan['source'], repeat=True)
        row7 = records[7]['receipt']
        rr = repeat['receipt']
        check((rr['start'], rr['stop_inclusive']) == (row7['start'], row7['stop_inclusive'])
              and repeat['payload'] == records[7]['payload'], 'Full genuine row7 repeat differs')
        check(rr.get('coordinate') == {'phase': 'repeat', 'scan': 5, 'time_index': 7,
                                      'channel_start': plan['channel_start']}, 'Repeat coordinate differs')
        check('.repeat.' in rr['receipt_relative_path'], 'Repeat must have a distinct new HTTP receipt')
        repeat_done = True
        # Any HDF/transport close failure must occur before canonical publication.
        backend.close()
        backend_closed = True
        backend.recheck()
        m = backend.manifest(records, repeat, partial, canonical)
        validate_manifest(m, plan, partial, canonical, repeat, records, mode)
        backend.recheck()
        manifest_path = output / 'data/pilot_manifest.json'
        json_new(manifest_path, m)
        # Never unlink prior evidence. The partial stays retained even on success.
        os.link(partial, canonical)
        promoted = True
        completion = {'schema': 'SETI_BE_RECOVERY_ACQUISITION_COMPLETE_V1', 'status': 'PASS',
                      **COUNTS, 'completed_utc': utc(), 'execution_mode': mode,
                      'scan5_prior_rows_reconstructed': 8, 'scan5_new_rows_decoded': 8,
                      'manifest_sha256': sha(manifest_path), 'array_sha256': sha(canonical),
                      'protocol_sha256': m['protocol_sha256'], 'source_sha256': sha(__file__),
                      'scientific_coverage_credit': 0, 'mandatory_native_and_science_checks_pending': True}
        json_new(marker, completion)
        return {'marker': str(marker), 'manifest': str(manifest_path), 'mode': mode, **COUNTS}
    except BaseException as error:
        if promoted:
            canonical.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
        json_new(output / 'RECOVERY_FAILURE_BE.json', {'status': 'STOP_NO_AUTOMATIC_RETRY',
                 'completed_utc': utc(), 'error': repr(error), 'traceback': traceback.format_exc(),
                 'prior_rows_verified': verified_prior, 'new_rows_decoded': max(len(records) - 8, 0),
                 'row7_repeat_completed': repeat_done, 'execution_mode': mode,
                 'science_completed': False, 'canonical_promoted': False})
        raise
    finally:
        if not backend_closed:
            backend.close()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OriginalBackend:
    """Real archive adapter. Construction is inert; prepare/load have no network."""
    def __init__(self, root, protocol, runtime, mode='PRODUCTION'):
        self.root, self.protocol, self.runtime, self.mode = Path(root).resolve(), protocol, Path(runtime).resolve(), mode
        self.f = self.remote = self.h5 = None
        self.pins = {}

    def _pin(self, path, expected=None):
        path = Path(path).resolve()
        value = sha(path)
        check(expected is None or value == expected, 'Pinned input differs: ' + str(path))
        self.pins[str(path)] = value

    def prepare(self, output):
        root, p = self.root, self.protocol
        check(sys.flags.optimize == 0, 'Original pinned helpers require assertions enabled')
        for relative, expected in p['source_and_state_sha256'].items():
            path = Path(relative)
            check(not path.is_absolute() and '..' not in path.parts, 'Unsafe evidence pin')
            self._pin(root / path, expected)
        for absolute, expected in p['local_source_sha256'].items():
            self._pin(absolute, expected)
        # Source path and all transitive generic helper sources are pinned above.
        f = self.f = load_module(root / 'work_bb/fresh_acquisition_bb.py', 'be_original_bb_helpers')
        original, self.heads, bindings = f.load()
        check(original['configuration'] == p['configuration'] and original['selection'] == p['selection']
              and original['hdf_chunk_index_model'] == p['hdf_chunk_index_model']
              and original['allowed_sources'] == p['allowed_sources'],
              'Original prepower science/selection changed')
        old = root / 'work_bb/acquire/hip44295_65133'
        for rp in sorted((old / 'raw_transport').glob('*.json')):
            r, bp = f.read(rp), rp.with_suffix('.bin')
            head = self.heads['headers'][r['scan']]
            raw = bp.read_bytes()
            check(r['status'] == 206 and r['attempts'] == 1 and r['failed_attempts'] == [], 'Bad retained receipt')
            check(r['url'] == head['row']['url'] and r['archive_id'] == head['row']['id']
                  and r['etag'] == head['etag'], 'Retained source differs')
            check(r['content_range'] == f"bytes {r['start']}-{r['stop_inclusive']}/{head['row']['size']}"
                  and len(raw) == r['bytes'] and hashlib.sha256(raw).hexdigest() == r['sha256'], 'Retained HTTP bytes differ')
            if '.repeat.' not in rp.name:
                f.put_cache(r['scan'], r['start'], r['stop_inclusive'], raw)
            bindings.append(f.augment(r, rp, bp))
            self._pin(rp); self._pin(bp)
        prefix_rp = root / 'work_bc/acquire/transport/scan5_8154457534_8157560831.json'
        prefix = f.read(prefix_rp); prefix_bp = prefix_rp.with_suffix('.bin')
        validate_http(prefix, prefix_bp.read_bytes(), p['source'])
        f.put_cache(5, prefix['start'], prefix['stop_inclusive'], prefix_bp.read_bytes())
        bindings.append(f.augment(prefix, prefix_rp, prefix_bp))
        check(len(bindings) == 241 and sum('.repeat.' in r['receipt_relative_path'] for r in bindings) == 5,
              'Expected retained241HTTP receipts including5repeats')
        self.bindings = bindings
        self._pin(prefix_rp); self._pin(prefix_bp)
        sys.path.insert(0, str(self.runtime))
        import numpy as np
        import h5py
        import bitshuffle
        check((np.__version__, h5py.__version__, bitshuffle.__version__) == ('2.3.5', '3.16.0', '0.5.2'),
              'Runtime pins differ')
        f.np, f.h5py, f.bitshuffle = np, h5py, bitshuffle
        f.POLICY, f.CHANNEL, f.SOURCE_BINDINGS = p, p['selection']['channel_start'], bindings
        f.NETWORK_ENABLED = False
        f.STARTED = time.monotonic()
        if output is not None:
            f.OUT, f.DATA, f.CACHE, f.DERIVED = output, output / 'data', output / 'transport', output / 'derived'
            f.FAILURE, f.JOURNAL = output / 'NETWORK_FAILURE_BE.json', output / 'RECOVERY_EVENTS_BE.jsonl'
        else:
            # Probe cannot open outputs or call transport even if a later bug toggles NETWORK_ENABLED.
            def forbidden_download(*args, **kwargs):
                raise RecoveryError('Offline probe forbids transport')
            f.download = forbidden_download
        self.output = output
        Remote, norm = f.inherited_classes()
        self.head = self.heads['headers'][5]
        self.remote = f.open_remote(self.head, Remote)
        self.h5 = h5py.File(self.remote, 'r')
        self.dataset = self.h5['data']
        check(list(self.dataset.shape) == self.head['shape'] and list(self.dataset.chunks) == self.head['chunks']
              and str(self.dataset.dtype) == self.head['dtype'], 'HDF layout differs')
        self.attrs = {k: norm(v) for k, v in self.dataset.attrs.items()}
        check(self.attrs == self.head['attrs'], 'HDF attributes differ')
        cp = self.dataset.id.get_create_plist()
        filters = json.loads(json.dumps([[norm(v) for v in cp.get_filter(i)] for i in range(cp.get_nfilters())]))
        check(filters == self.head['filters'], 'HDF filters differ')

    def read_row(self, t, allow_new):
        f = self.f
        check(allow_new is (t >= 8) and 0 <= t < 16, 'Wrong cached/new coordinate boundary')
        check(self.output is not None or not allow_new, 'Offline probe cannot acquire')
        f.NETWORK_ENABLED = allow_new
        f.CURRENT_COORDINATE = {'phase': 'selected_coordinate_read_direct_chunk', 'scan': 5,
                                'time_index': t, 'channel_start': f.CHANNEL}
        descriptor = f.tree_descriptor(self.remote, t)
        mask, payload = self.dataset.id.read_direct_chunk((t, 0, f.CHANNEL))
        check(mask == 0, 'Unexpected selected filter mask')
        value, segments = f.source_segments(5, descriptor.byte_offset, descriptor.byte_offset + descriptor.size - 1)
        check(value == payload, 'HDF chunk differs from retained/new HTTP source slices')
        if t < 8:
            rp = self.root / (f'work_bb/acquire/hip44295_65133/derived/scan5_row{t}.json'
                              if t < 7 else 'work_bc/acquire/derived/scan5_row7.json')
            bp = rp.with_suffix('.bin')
            r = f.augment(f.read(rp), rp, bp)
            check(bp.read_bytes() == payload and sha(bp) == r['sha256'], 'Prior compressed bytes differ')
        else:
            bp = self.output / f'derived/scan5_row{t}.bin'; rp = bp.with_suffix('.json')
            with bp.open('xb') as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            r = {'receipt_schema': SCHEMAS['BE'], 'status': 'DERIVED_FROM_VERIFIED_RANGES',
                 'scan': 5, 'time_index': t, 'archive_id': 65143, 'url': self.head['row']['url'],
                 'etag': self.head['etag'], 'start': descriptor.byte_offset,
                 'stop_inclusive': descriptor.byte_offset + len(payload) - 1, 'bytes': len(payload),
                 'sha256': hashlib.sha256(payload).hexdigest(), 'coverage_segments': segments,
                 'new_HTTP_whole_chunk_receipt_claimed': False, 'full_original_md5_verified': False,
                 'derived_payload_relative_path': str(bp.relative_to(self.root)),
                 'lineage': 'BE newly decoded missing row8..15; BB87 andBC1 remain prior'}
            f.new(rp, r); r = f.augment(r, rp, bp)
        raw_sources = {s['source_receipt']['receipt_relative_path']:
                       (self.root / s['source_receipt']['payload_relative_path']).read_bytes()
                       for s in r['coverage_segments']}
        return {'descriptor': {'byte_offset': descriptor.byte_offset, 'size': descriptor.size,
                              'filter_mask': descriptor.filter_mask, 'chunk_offset': list(descriptor.chunk_offset)},
                'payload': payload, 'decoded': f.decode(payload).tobytes(order='C'),
                'receipt': r, 'source_payloads': raw_sources}

    def repeat_row7(self, record):
        f = self.f
        f.NETWORK_ENABLED = True
        f.CURRENT_COORDINATE = {'phase': 'repeat', 'scan': 5, 'time_index': 7, 'channel_start': f.CHANNEL}
        r = record['receipt']
        payload, _ = f.download(self.head['row'], 5, r['start'], r['stop_inclusive'], self.head['etag'], repeat=True)
        f.NETWORK_ENABLED = False
        receipt = f.ALL_NEW_RECEIPTS[-1]
        check(receipt['kind'] == 'repeat' and len([x for x in f.ALL_NEW_RECEIPTS if x['kind'] == 'repeat']) == 1,
              'Expected exactly one genuinely new repeat receipt')
        return {'payload': payload, 'receipt': receipt}

    def recheck(self):
        for path, expected in self.pins.items():
            check(sha(path) == expected, 'Immutable input changed: ' + path)

    def manifest(self, records, repeat, partial, canonical):
        f, root, p = self.f, self.root, self.protocol
        old = root / 'work_bb/acquire/hip44295_65133'
        proof_BB, proof_BC = (root / 'work_bb/review/PARTIAL_INPUT_PROOF_BB.json',
                              root / 'work_bc/review/PARTIAL_INPUT_PROOF_BC.json')
        authority = f.read(proof_BB)
        old_arrays = {r['scan']: r for r in authority['canonical_array_retention_required']}
        scans, receipts, header_paths = [], [], []
        for j in range(5):
            hp = old / f'data/scan{j}_header.json'; head = f.read(hp); ap = old / f'data/scan{j}.npy'
            scans.append({'scan': j, 'role': ['ON', 'OFF'][j % 2], 'archive': head['archive'],
                          'sigproc': head['attrs'], 'ntime': 16, 'channel_start': f.CHANNEL,
                          'channel_stop_exclusive': f.CHANNEL + f.C, 'slice_shape': [16, f.C],
                          'fch1_slice_mhz': head['attrs']['fch1'] + f.CHANNEL * head['attrs']['foff'],
                          'array_file': str(ap), 'array_path': str(ap), 'array_relative_path': str(ap.relative_to(root)),
                          'array_sha256': sha(ap), 'array_powers_sha256': old_arrays[j]['array_powers_sha256'],
                          'lineage': 'BB original canonical array retained read-only'})
            header_paths.append(str(hp))
            for t in range(16):
                rp = old / f'derived/scan{j}_row{t}.json'
                receipts.append(f.augment(f.read(rp), rp, rp.with_suffix('.bin')))
        new_head = {'scan': 5, 'archive': self.head['row'], 'shape': self.head['shape'],
                    'attrs': self.attrs, 'etag': self.head['etag'],
                    'chunks': [dict(scan=5, time_index=t, **record['descriptor'], etag=self.head['etag'])
                               for t, record in enumerate(records)], 'metadata_requests': self.remote.log}
        hp = self.output / 'data/scan5_header.json'; json_new(hp, new_head); header_paths.append(str(hp))
        with partial.open('rb') as stream:
            npy_header(stream, f.C); power_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        scans.append({'scan': 5, 'role': 'OFF', 'archive': self.head['row'], 'sigproc': self.attrs,
                      'ntime': 16, 'channel_start': f.CHANNEL, 'channel_stop_exclusive': f.CHANNEL + f.C,
                      'slice_shape': [16, f.C], 'fch1_slice_mhz': self.attrs['fch1'] + f.CHANNEL * self.attrs['foff'],
                      'array_file': str(canonical), 'array_path': str(canonical),
                      'array_relative_path': str(canonical.relative_to(root)), 'array_sha256': sha(partial),
                      'array_powers_sha256': power_hash, 'inherited_rows': 8, 'recovered_rows': 8,
                      'lineage': 'BB7+BC1 prior rows reconstructed and byte-compared; BE8 newly decoded'})
        all_ranges = [r for r in self.bindings + f.ALL_NEW_RECEIPTS if r.get('kind') != 'repeat']
        old_repeats = [r for r in self.bindings if r.get('kind') == 'repeat']
        m = {'schema': 'HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BE_V1', 'target': 'HIP44295', 'primary_id': 65133,
             **COUNTS, 'execution_mode': self.mode,
             'observation_date': p['observation_date'], 'observation_dates': p['observation_dates'],
             'observation_end_date': p['observation_end_date'], 'scans': scans,
             'chunk_receipts': receipts + [r['receipt'] for r in records],
             'repeated_chunk_receipts': old_repeats + [repeat['receipt']],
             'all_metadata_receipts': all_ranges, 'metadata_receipts': all_ranges,
             'descriptor_header_paths': header_paths,
             'actual_headers_path': str(old / 'actual_headers_result.json'),
             'actual_headers_sha256': sha(old / 'actual_headers_result.json'),
             'selection_path': str(old / 'selection_frozen.json'), 'selection_sha256': sha(old / 'selection_frozen.json'),
             'protocol_sha256': p['protocol_file_sha256'],
             'original_BB_prepower_sha256': sha(root / 'work_bb/PROTOCOL_PREPOWER_BB.json'),
             'scan5_prior_rows_reconstructed': 8, 'scan5_new_rows_decoded': 8,
             'phase2_network_requests': f.REQUESTS, 'phase2_requested_bytes': f.REQUESTED_BYTES,
             'scientific_coverage_credit': 0, 'candidate_assessment': None,
             'detector_searches_executed': 0, 'native_and_science_gates_pending': True,
             'full_original_md5_verified': False,
             'power_contact_scope_addendum': f.read(root / 'work_bc/review/EXACT_PREFIX_SCOPE_ADDENDUM_BC.json'),
             'power_contact_scope_addendum_path': 'work_bc/review/EXACT_PREFIX_SCOPE_ADDENDUM_BC.json',
             'power_contact_scope_addendum_sha256': sha(root / 'work_bc/review/EXACT_PREFIX_SCOPE_ADDENDUM_BC.json'),
             'prior_BB_partial_proof_path': str(proof_BB), 'prior_BB_partial_proof_sha256': sha(proof_BB),
             'prior_BC_partial_proof_path': str(proof_BC), 'prior_BC_partial_proof_sha256': sha(proof_BC),
             'prior_BB_partial_array_path': str(old / 'data/scan5.npy.partial'),
             'prior_BB_partial_array_sha256': sha(old / 'data/scan5.npy.partial'),
             'prior_BC_partial_array_path': str(root / 'work_bc/acquire/data/scan5.npy.partial'),
             'prior_BC_partial_array_sha256': sha(root / 'work_bc/acquire/data/scan5.npy.partial')}
        for label, relative in [('original_BB_failed_actual', 'work_bb/execution/PAYLOAD_ACTUAL_EXIT_BB.json'),
                                ('prior_BC_failed_actual', 'work_bc/execution/RECOVERY_ACTUAL_EXIT_BC.json')]:
            m[label + '_path'], m[label + '_sha256'] = str(root / relative), sha(root / relative)
        return m

    def close(self):
        if self.f is not None:
            self.f.NETWORK_ENABLED = False
        if self.h5 is not None:
            self.h5.close()
            self.h5 = None


def production_gate(path, protocol_path):
    gate, p = json_read(path), json_read(protocol_path)
    check(gate.get('schema') == 'SETI_BE_RECOVERY_DISPATCH_GATE_V1'
          and gate.get('authorized') is True and gate.get('mode') == 'PRODUCTION', 'No production recovery gate')
    check(gate.get('normal_permissions_only') is True and gate.get('access_controls_override') is False,
          'Normal authorized archive access required')
    check(p.get('network_requests_authorized_this_checkpoint') == 60
          and p.get('science_execution_released') is False, 'Prepared checkpoint has no production network release')
    check(p['schema'] == 'SETI_BE_PROSPECTIVE_MISSING_EIGHT_RECOVERY_V1'
          and p['target'] == 'HIP44295' and p['primary_id'] == 65133
          and p['allowed_scan_indices'] == [5] and p['missing_time_indices'] == list(range(8, 16))
          and p['prior_valid_time_indices'] == list(range(8))
          and p['row_lineage'] == {'BB': 87, 'BC': 1, 'new': 8, 'total': 96}
          and p['repeat_lineage'] == {'prior': 5, 'new': 1}, 'Recovery protocol lineage differs')
    check(p['network_limits'] == {'max_requests': 60, 'max_requested_bytes': 67108864,
          'max_single_request_bytes': 8388608, 'max_wall_seconds': 600,
          'attempts_per_range': 1, 'parallel_connections': 1}, 'Recovery budget differs')
    check(gate['source_sha256'] == sha(__file__) and gate['protocol_sha256'] == sha(protocol_path), 'Gate/source pin differs')
    review_path, access_path = Path(gate['review_path']), Path(gate['normal_access_receipt_path'])
    check(sha(review_path) == gate['review_sha256'] and sha(access_path) == gate['normal_access_receipt_sha256'],
          'Review/access receipt hash differs')
    review, access = json_read(review_path), json_read(access_path)
    check(review.get('approved_for_production_after_normal_access') is True
          and review['source_sha256'] == sha(__file__)
          and review['protocol_sha256'] == sha(protocol_path), 'Recovery not reviewed for production')
    check(access.get('archive_access_permitted') is True and access.get('alternative_route_used') is False,
          'Archive access is not released')
    p['protocol_file_sha256'] = sha(protocol_path)
    return gate, p


def recovery_plan(root, p):
    proof = json_read(root / 'work_bc/review/PARTIAL_INPUT_PROOF_BC.json')
    old = root / 'work_bb/acquire/hip44295_65133'
    parent = json_read(root / 'work_bb/review/PARTIAL_INPUT_PROOF_BB.json')
    parent_arrays = [{'scan': e['scan'], 'path': str(old / f"data/scan{e['scan']}.npy"), 'sha256': e['sha256']}
                     for e in parent['canonical_array_retention_required']]
    repeats = []
    for rp in sorted((old / 'raw_transport').glob('*.repeat.json')):
        receipt = json_read(rp)
        repeats.append({**receipt, 'receipt_relative_path': str(rp.relative_to(root)),
                        'payload_relative_path': str(rp.with_suffix('.bin').relative_to(root)),
                        'stored_receipt_sha256': sha(rp)})
    return {'channels': p['selection']['channel_count'], 'channel_start': p['selection']['channel_start'],
            'source': p['source'], 'prior_scan5_array': str(root / 'work_bc/acquire/data/scan5.npy.partial'),
            'prior_row_reports': proof['scan5_valid_row_reports'], 'prior_valid_time_indices': list(range(8)),
            'missing_time_indices': list(range(8, 16)), 'row_lineage': {'BB': 87, 'BC': 1, 'new': 8, 'total': 96},
            'parent_array_proofs': parent_arrays, 'prior_repeat_receipts': repeats}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--offline-probe', action='store_true')
    parser.add_argument('--acquire', action='store_true')
    parser.add_argument('--gate', type=Path)
    parser.add_argument('--probe-output', type=Path)
    args = parser.parse_args()
    check(args.offline_probe != args.acquire, 'Choose one explicit mode')
    root = args.evidence_root.resolve()
    if args.acquire:
        check(args.gate is not None, 'Production gate is required before backend construction')
        gate, p = production_gate(args.gate, args.protocol)
        # No runtime or generic helpers are imported before gate/source/review/access checks.
        backend = OriginalBackend(root, p, args.runtime)
        def deadline(signum, frame):
            raise TimeoutError('BE whole-attempt600second deadline')
        previous_handler = signal.getsignal(signal.SIGALRM)
        check(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'An existing process timer cannot be replaced')
        signal.signal(signal.SIGALRM, deadline)
        signal.setitimer(signal.ITIMER_REAL, p['network_limits']['max_wall_seconds'])
        try:
            result = execute(backend, recovery_plan(root, p), root / 'work_be/acquire', gate)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
        print(json.dumps(result))
        return 0
    p = json_read(args.protocol); p['protocol_file_sha256'] = sha(args.protocol)
    backend = OriginalBackend(root, p, args.runtime)
    rows = []
    try:
        backend.prepare(None)
        plan = recovery_plan(root, p)
        with Path(plan['prior_scan5_array']).open('rb') as prior:
            npy_header(prior, plan['channels'])
            for t in range(8):
                record = backend.read_row(t, False); validate_row(record, t, plan)
                raw = prior.read(plan['channels'] * 4)
                check(raw == record['decoded'], 'Offline retained row differs')
                check(hashlib.sha256(raw).hexdigest() == plan['prior_row_reports'][t]['decoded_row_sha256'],
                      'Offline proof row differs')
                rows.append({'time_index': t, 'sha256': hashlib.sha256(raw).hexdigest()})
        backend.recheck()
        check(backend.f.REQUESTS == 0 and backend.remote.log == [], 'Offline probe contacted archive')
        result = {'schema': 'SETI_BE_CACHED_EIGHT_ROW_PROBE_V1', 'status': 'PASS_CACHED_EIGHT_ROWS_NO_NETWORK',
                  'completed_utc': utc(), 'rows_redecoded': rows, 'archive_requests': 0,
                  'source_sha256': sha(__file__), 'protocol_sha256': sha(args.protocol),
                  'prior_BB_canonical_arrays_rehashed': 5, 'science_completed': False,
                  'detector_searches_executed': 0, 'shared_original_codec_and_TREE_model': True}
        check(args.probe_output is not None, 'Use new --probe-output path')
        json_new(args.probe_output, result)
        print(json.dumps({'status': result['status'], 'rows_redecoded': 8, 'archive_requests': 0}))
        return 0
    finally:
        backend.close()


if __name__ == '__main__':
    raise SystemExit(main())
