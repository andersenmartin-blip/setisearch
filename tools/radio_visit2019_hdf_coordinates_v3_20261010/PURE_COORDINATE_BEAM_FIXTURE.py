#!/usr/bin/env python3
"""Synthetic decimal HDF coordinate and nominal beam gates; no source data."""
import time
START = time.monotonic()
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
import types


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata-source', required=True)
    p.add_argument('--expected-source-sha256', required=True)
    p.add_argument('--receipt', required=True)
    p.add_argument('--root-go-pure-toy', action='store_true')
    args = p.parse_args()
    require(args.root_go_pure_toy and re.fullmatch(r'[0-9a-f]{64}', args.expected_source_sha256),
            'Exact root pure synthetic GO required')
    require(os.environ.get('PYTHONDONTWRITEBYTECODE') == '1' and sys.dont_write_bytecode,
            'Disabled bytecode writes required')
    def deadline(signum, frame):
        raise TimeoutError('Pure coordinate/beam fixture cap')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (9, 10))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    signal.alarm(max(1, int(30 - (time.monotonic() - START))))
    source, receipt = Path(args.metadata_source), Path(args.receipt)
    require(source.is_absolute() and source.resolve() == source and not source.is_symlink()
            and receipt.is_absolute() and receipt.parent.is_dir() and not receipt.exists(),
            'Canonical source and new absolute fixture receipt required')
    raw = source.read_bytes()
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == args.expected_source_sha256,
            'Exact metadata core source pin changed')
    m = types.ModuleType('_synthetic_hdf_coordinate_beam_v3')
    m.__file__ = str(source)
    sys.modules[m.__name__] = m
    exec(compile(raw, str(source), 'exec'), m.__dict__)
    cases = []
    def close(actual, expected, tol=1e-10):
        require(abs(actual - expected) <= tol, 'Known analytic coordinate or beam value differs')
    def reject(callback):
        try:
            callback()
        except ValueError:
            return
        raise AssertionError('Invalid synthetic coordinate or frequency admitted')
    def check(name, callback):
        callback()
        cases.append({'name': name, 'status': 'PASS'})
    check('HDF_decimal_hour_RA_12_hours_is_180_degrees', lambda: close(m.hdf_coordinate(12), 180))
    check('HDF_decimal_DECs_preserve_signed_degrees', lambda: close(m.hdf_coordinate(-22.71, True), -22.71))
    check('RA_zero_and_23_999_hours_wrap_on_sphere', lambda: (
        close(m.hdf_coordinate(0), 0), close(m.hdf_coordinate(23.999), 359.985),
        close(m.separation((m.hdf_coordinate(23.999), 0), (m.hdf_coordinate(.001), 0)), .03)))
    check('RA_negative_24_and_packed_angle_rejected', lambda: (
        reject(lambda: m.hdf_coordinate(-.001)), reject(lambda: m.hdf_coordinate(24)),
        reject(lambda: m.hdf_coordinate(200123))))
    check('both_DEC_poles_included_and_outside_rejected', lambda: (
        close(m.hdf_coordinate(90, True), 90), close(m.hdf_coordinate(-90, True), -90),
        reject(lambda: m.hdf_coordinate(90.001, True)), reject(lambda: m.hdf_coordinate(-90.001, True))))
    check('nonfinite_and_non_numeric_coordinates_rejected', lambda: (
        reject(lambda: m.hdf_coordinate(float('nan'))), reject(lambda: m.hdf_coordinate(float('inf'), True)),
        reject(lambda: m.hdf_coordinate('20')), reject(lambda: m.hdf_coordinate(True))))
    check('polar_longitudes_represent_same_direction', lambda: close(m.separation((0, 90), (180, 90)), 0))
    check('nominal_GBT_beam_known_1_GHz_and_inverse_frequency', lambda: (
        close(m.nominal_beam_degrees(1e9), 1.18 * .299792458 / 100 * 180 / math.pi),
        close(m.nominal_beam_degrees(2e9), m.nominal_beam_degrees(1e9) / 2),
        reject(lambda: m.nominal_beam_degrees(0)), reject(lambda: m.nominal_beam_degrees(float('nan')))))
    def records():
        result = []
        for i in range(6):
            on, start = i % 2 == 0, 58000 + i * 320 / 86400
            ra = 300 + .015 * (i // 2) if on else 310 + 10 * (i // 2)
            result.append({'source_id': 'SYNTHETIC_' + str(i), 'ordered_index': i + 1,
                'candidate_role': 'ON_CANDIDATE' if on else 'CONTROL_CANDIDATE',
                'status': 'COMPLETE_HEADER_METADATA_ONLY', 'shape': [16, 1, 655360],
                'dtype_string': '<f4', 'chunks': [1, 1, 65536], 'creation_filters': [],
                'data_attributes': {'nchans': 655360, 'nifs': 1, 'nbits': 32,
                    'fch1': 1500., 'foff': -.0000028, 'tsamp': 18., 'tstart': start,
                    'source_name': 'HIP98505' if on else 'SYNTHETIC_CONTROL_' + str(i)},
                'pointing_degrees': {'RA': ra, 'DEC': 0},
                'scan_time_interval_MJD_half_open': [start, start + 288 / 86400],
                'metadata_derived_midpoint': {'native_ordinal_zero_based': 5,
                    'absolute_channel_start': 327680, 'channel_count': 65536}})
        return result
    def eligible():
        r = m.qualify(records())
        require(r['status'] == 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
                and r['beam_separation_model_used'] is True
                and r['controls_certified_blank_sky_or_independent_noise'] is False
                and r['source_values_admission'] == r['independent_validation_admission'] == 'BLOCKED',
                'Synthetic metadata eligibility or bounded inference differs')
        close(r['nominal_beam_model']['maximum_actual_channel_center_Hz'], 1.5e9)
        close(r['pointing_tolerance_degrees'], r['distinct_pointing_minimum_degrees'] / 2)
    check('synthetic_six_beam_eligible_despite_ON_separation_above_one_arcminute', eligible)
    def ON_boundary(factor, expected):
        values = records()
        half_beam = m.nominal_beam_degrees(1.5e9) / 2
        for i in (0, 2, 4):
            values[i]['pointing_degrees'] = {'RA': 300, 'DEC': 0}
        values[4]['pointing_degrees']['RA'] += factor * half_beam
        require(m.qualify(values)['status'] == expected, 'ON half-FWHM boundary gate differs')
    check('ON_inside_half_FWHM_eligible', lambda: ON_boundary(.99, 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'))
    check('ON_outside_half_FWHM_ineligible', lambda: ON_boundary(1.01, 'METADATA_NOT_ELIGIBLE'))
    def OFF_boundary(factor, expected):
        values = records()
        for i in (0, 2, 4):
            values[i]['pointing_degrees'] = {'RA': 300, 'DEC': 0}
        values[1]['pointing_degrees'] = {'RA': 300 + factor * m.nominal_beam_degrees(1.5e9), 'DEC': 0}
        require(m.qualify(values)['status'] == expected, 'OFF full-FWHM boundary gate differs')
    check('OFF_inside_full_FWHM_ineligible', lambda: OFF_boundary(.99, 'METADATA_NOT_ELIGIBLE'))
    check('OFF_outside_full_FWHM_eligible', lambda: OFF_boundary(1.01, 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'))
    check('same_ON_OFF_pointing_ineligible', lambda: OFF_boundary(0, 'METADATA_NOT_ELIGIBLE'))
    def different_grid():
        values = records()
        values[5]['data_attributes']['foff'] *= 2
        require(m.qualify(values)['status'] == 'METADATA_NOT_ELIGIBLE', 'Different synthetic grids admitted')
    check('six_common_grid_still_required', different_grid)
    measured = {'CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - START,
                'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(len(cases) == 15 and measured['CPU_seconds'] <= 10 and measured['wall_seconds'] <= 30
            and measured['peak_RSS_bytes'] <= 536870912, 'Pure fixture count or caps differ')
    require(hashlib.sha256(source.read_bytes()).hexdigest() == args.expected_source_sha256,
            'Pure fixture source end-readback changed')
    report = {'schema': 'SETI_HDF_DECIMAL_COORDINATE_AND_BEAM_SYNTHETIC_FIXTURE_V3',
              'status': 'PASS_PURE_SYNTHETIC_HDF_COORDINATE_BEAM_FIXTURE', 'passed_cases': len(cases),
              'metadata_source_sha256': args.expected_source_sha256,
              'fixture_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cases': cases, 'measured_resources': measured, 'HDF5_imported': False,
              'actual_source_metadata_or_values_read': False, 'HTTP_requests': 0,
              'independent_validation_admission': 'BLOCKED'}
    raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require(len(raw) <= 65536, 'Pure synthetic receipt cap exceeded')
    with receipt.open('xb') as h:
        h.write(raw)
        h.flush()
        os.fsync(h.fileno())
    fd = os.open(receipt.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    signal.alarm(0)
    print(json.dumps(report, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
