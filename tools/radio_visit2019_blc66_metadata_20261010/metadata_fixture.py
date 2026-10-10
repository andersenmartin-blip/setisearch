#!/usr/bin/env python3
"""Pure synthetic edge fixtures; no h5py, source cache, network or amplitudes."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time
import types

START = time.monotonic()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-source', required=True)
    parser.add_argument('--expected-source-sha256', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--root-go-pure-toy', action='store_true')
    args = parser.parse_args()
    require(args.root_go_pure_toy and re.fullmatch(r'[0-9a-f]{64}', args.expected_source_sha256),
            'Exact pure-toy source GO required')
    def deadline(signum, frame):
        raise TimeoutError('Pure metadata fixture resource cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (9, 10))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    signal.alarm(30)
    path = Path(args.metadata_source)
    receipt = Path(args.receipt)
    require(path.is_absolute() and path.resolve() == path and receipt.is_absolute()
            and receipt.parent.is_dir() and not receipt.exists(), 'Exact new fixture path required')
    raw = path.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == args.expected_source_sha256,
            'Metadata core source pin changed')
    module = types.ModuleType('_pure_visit2019_metadata_fixture')
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    cases = []
    def check(name, callback):
        callback()
        cases.append({'name': name, 'status': 'PASS'})
    def close(actual, expected, tolerance=1e-10):
        require(abs(actual - expected) <= tolerance, 'Known analytic value differs')
    def reject(callback):
        try:
            callback()
        except ValueError:
            return
        raise AssertionError('Malformed synthetic input was admitted')
    check('known_SIGPROC_RA_conversion', lambda: close(module.packed_coordinate(123456.0),
                                                     15 * (12 + 34 / 60 + 56 / 3600)))
    check('known_negative_SIGPROC_DEC_conversion', lambda: close(module.packed_coordinate(-223456.0, True),
                                                                -(22 + 34 / 60 + 56 / 3600)))
    check('packed_RA_hour_and_minute_rejected', lambda: (
        reject(lambda: module.packed_coordinate(240000.0)),
        reject(lambda: module.packed_coordinate(126000.0))))
    check('packed_DEC_pole_and_second_rejected', lambda: (
        reject(lambda: module.packed_coordinate(900001.0, True)),
        reject(lambda: module.packed_coordinate(223460.0, True))))
    check('analytic_RA_wrap_sky_separation', lambda: close(module.separation((359.99, 0), (0.01, 0)), .02))
    check('analytic_polar_same_position', lambda: close(module.separation((0, 90), (180, 90)), 0))
    class SyntheticCache:
        def __init__(self, spans):
            self.spans = spans
        def read(self, offset, length):
            for start, body in self.spans:
                if start <= offset and offset + length <= start + len(body):
                    return body[offset - start:offset - start + length]
            raise ValueError('Synthetic cache gap')
        def evidence(self, offset, length, interpretation):
            return {'offset': offset, 'bytes': length,
                    'sha256': hashlib.sha256(self.read(offset, length)).hexdigest(),
                    'interpretation': interpretation, 'cache_pins': []}
    def reader_case():
        virtual = module.CacheOnly(SyntheticCache([(0, b'abcd'), (8, b'ijkl')]), 12)
        require(virtual.readinto(bytearray(4)) == 4 and virtual.tell() == 4,
                'Synthetic cached read differs')
        reject(lambda: virtual.readinto(bytearray(4)))
        require(len(virtual.misses) == 1 and virtual.misses[0]['HTTP_authorized'] is False,
                'Cache gap gained acquisition authorization')
        reject(lambda: virtual.seek(13))
        reject(lambda: virtual.seek(0, 3))
    check('cache_reader_gap_and_bounds_fail_closed', reader_case)
    chunks, root_pointer, envelope_offset = [1, 1, 65536], 2048, 64
    body = (b'\x03\x02\x04' + root_pointer.to_bytes(8, 'little')
            + b''.join(n.to_bytes(4, 'little') for n in [1, 1, 65536, 4]) + b'\0' * 5)
    envelope = (8).to_bytes(2, 'little') + len(body).to_bytes(2, 'little') + b'\0' * 4
    plan = {'superblock': {'base_address': 0}, 'messages': [
        {'object': 'data', 'type': 8, 'offset': envelope_offset,
         'data_bytes_including_padding': len(body), 'data_sha256': hashlib.sha256(body).hexdigest()}]}
    cache = SyntheticCache([(envelope_offset, envelope + body)])
    def layout_case():
        result = module.chunk_layout_pointer(plan, cache, chunks, 4, 4096)
        require(result['chunk_index_root_absolute_address'] == root_pointer
                and result['pointer_field_offset'] == envelope_offset + 11
                and result['chunk_index_nodes_read'] == 0 and result['HTTP_authorized'] is False,
                'Verified synthetic layout pointer evidence differs')
        reject(lambda: module.chunk_layout_pointer(plan, cache, [1, 1, 32768], 4, 4096))
        reject(lambda: module.chunk_layout_pointer(plan, cache, chunks, 4, 1024))
    check('verified_layout_pointer_only_and_wrong_geometry_rejected', layout_case)
    def synthetic_records():
        values = []
        for i in range(6):
            start = 58000 + i * 320 / 86400
            on = i % 2 == 0
            values.append({'source_id': 'TOY_' + str(i), 'ordered_index': i + 1,
                'candidate_role': 'ON_CANDIDATE' if on else 'CONTROL_CANDIDATE',
                'status': 'COMPLETE_HEADER_METADATA_ONLY', 'shape': [16, 1, 655360],
                'dtype_string': '<f4', 'chunks': chunks, 'creation_filters': [],
                'data_attributes': {'nchans': 655360, 'nifs': 1, 'nbits': 32,
                    'fch1': 1500.0, 'foff': -0.0000028, 'tsamp': 18.0, 'tstart': start,
                    'source_name': 'HIP98505' if on else 'TOY_CONTROL_' + str(i)},
                'pointing_degrees': {'RA': 300.0 if on else 300.0 + 5 * ((i + 1) // 2), 'DEC': 23.0},
                'scan_time_interval_MJD_half_open': [start, start + 288 / 86400],
                'metadata_derived_midpoint': {'native_ordinal_zero_based': 5,
                    'absolute_channel_start': 327680, 'channel_count': 65536}})
        return values
    def valid_qualification():
        result = module.qualify(synthetic_records())
        require(result['status'] == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
                and result['source_values_admission'] == result['independent_validation_admission'] == 'BLOCKED'
                and result['beam_separation_model_used'] is False,
                'Synthetic header eligibility gained source/validation admission')
    check('six_synthetic_headers_only_metadata_eligible', valid_qualification)
    def off_same_on():
        records = synthetic_records()
        records[1]['pointing_degrees'] = copy.deepcopy(records[0]['pointing_degrees'])
        require(module.qualify(records)['status'] == 'METADATA_NOT_ELIGIBLE', 'Same-pointing control admitted')
    check('same_pointing_control_not_eligible', off_same_on)
    def mismatched_grid():
        records = synthetic_records()
        records[5]['data_attributes']['foff'] *= 2
        require(module.qualify(records)['status'] == 'METADATA_NOT_ELIGIBLE', 'Different grid admitted')
    check('different_control_frequency_grid_not_eligible', mismatched_grid)
    def overlap():
        records = synthetic_records()
        records[1]['scan_time_interval_MJD_half_open'][0] = records[0]['scan_time_interval_MJD_half_open'][0]
        require(module.qualify(records)['status'] == 'METADATA_NOT_ELIGIBLE', 'Overlapping scans admitted')
    check('overlapping_six_scan_cadence_not_eligible', overlap)
    measured = {'CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - START,
                'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(measured['CPU_seconds'] <= 10 and measured['wall_seconds'] <= 30
            and measured['peak_RSS_bytes'] <= 536870912, 'Measured fixture resource cap exceeded')
    result = {'status': 'PASS_PURE_SYNTHETIC_METADATA_FIXTURE', 'cases': cases,
              'case_count': len(cases), 'metadata_source_sha256': args.expected_source_sha256,
              'fixture_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'HTTP_requests': 0, 'actual_source_cache_bytes_read': 0,
              'h5py_imported': False, 'spectral_values_read': False,
              'measured_resources_before_serialization': measured}
    serialized = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    require(len(serialized) <= 65536, 'Fixture receipt output cap exceeded')
    with receipt.open('xb') as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(receipt.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    signal.alarm(0)


if __name__ == '__main__':
    main()
