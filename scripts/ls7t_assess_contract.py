#!/usr/bin/env python3
"""Offline native-HK diagnostic. No science pixels, source fitting or detector."""
import argparse
import ast
import json
import math
import struct
import sys
from pathlib import Path

import astropy
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.utils import iers

from ls7s_assess_calibration import (GAIN_BLOB, GAIN_NAME, ELECTRONIC,
    blob_digest, csv_gz, digest, gain_vector, scalar_column, scalar_gain,
    save_json, stats)

ROOT = Path(__file__).resolve().parents[1]
KIND = 'SCI_RAW_HkExtended'
PIPE_READ_BLOB = '78e1f085b63c0e1768d660cb288cdd51357fe7ce'
FIELDS = ['UTC_TIME', 'MJD_TIME'] + ELECTRONIC + ['VOLT_FEE_CCD']
iers.conf.auto_download = False


def read_hk(inp):
    manifest = json.loads((inp / f'{KIND}_ranges.json').read_text())
    hdus = json.loads((inp / f'{KIND}_hdus.json').read_text())
    for entry in manifest['ranges']:
        b = (inp / entry['file']).read_bytes()
        assert len(b) == entry['count'] and digest(b) == entry['sha256']
    meta = hdus[1]
    table = next(x for x in manifest['ranges'] if x['start'] == meta['data_start'])
    raw = (inp / table['file']).read_bytes()
    path = inp / meta['metadata_file']
    with fits.open(path, memmap=False) as hd:
        assert hd[1].header['EXTNAME'] == KIND
        assert hd[1].verify_checksum() == hd[1].verify_datasum() == 1
        h, vals = hd[1].header.copy(), {}
        for name in FIELDS:
            vals[name] = hd[1].data[name].copy()
            direct = np.asarray(scalar_column(raw, h, name))
            assert np.array_equal(vals[name], direct), name
        units = {name: hd[1].columns[name].unit for name in FIELDS}
    return vals, h, units, path, manifest


def pinned_reader(path):
    source = path.read_bytes()
    assert blob_digest(source) == PIPE_READ_BLOB
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'gain')
    # Execute only the reviewed, unchanged pure FITS-reading gain function.
    # No PIPE package import, initialization, optimization, PSF or pickle loading.
    space = {'fits': fits, 'np': np}
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, str(path), 'exec'), space)
    return space['gain']


def f32(value):
    return struct.unpack('f', struct.pack('f', float(value)))[0]


def pipe_scalar32(row, h, coefficients):
    """Scalar reference including input float32 arithmetic of pinned PIPE."""
    vss, vod, vrd, vog, ccd_voltage = map(float, row)
    x = [f32(vss-f32(h['VSS_OFF'])),
         f32(f32(vod-vss)-f32(h['VOD_OFF'])),
         f32(f32(vrd-vss)-f32(h['VRD_OFF'])),
         f32(f32(vog-vss)-f32(h['VOG_OFF'])),
         f32(ccd_voltage+f32(h['TEMP_OFF']))]
    terms = [float(c[0]) * math.prod(f32(a ** int(e)) for a, e in zip(x, c[2:]))
             for c in coefficients]
    return 1 / (h['GAIN_NOM'] * (1 + math.fsum(terms)))


def ratio_stats(a, b):
    ratio = a / b
    return {'minimum_fractional_difference': float(ratio.min()-1),
            'maximum_fractional_difference': float(ratio.max()-1),
            'median_fractional_difference': float(np.median(ratio)-1),
            'max_abs_median_normalized_difference_ppm':
                float(np.max(np.abs(ratio/np.median(ratio)-1))*1e6)}


def assess(inp, previous, out, raw_headers):
    out.mkdir(exist_ok=True)
    v, header, units, hk_path, manifest = read_hk(inp)
    n = len(v['MJD_TIME'])
    assert n == 1140 and header['TIMESYS'] == 'TT'
    assert np.all(np.diff(v['MJD_TIME']) > 0)
    assert all(np.isfinite(v[k]).all() for k in FIELDS if k != 'UTC_TIME')
    tt = Time(v['MJD_TIME'], format='mjd', scale='tt')
    utc = Time(v['UTC_TIME'].tolist(), format='isot', scale='utc')
    time_error = np.abs((tt-utc).to_value('sec'))
    assert time_error.max() < 1e-5

    gain_path = previous / 'calibration' / GAIN_NAME
    assert blob_digest(gain_path.read_bytes()) == GAIN_BLOB
    with fits.open(gain_path, memmap=False) as hd:
        assert hd[1].verify_checksum() == hd[1].verify_datasum() == 1
        gh, coefs = hd[1].header.copy(), hd[1].data.copy()
    coefficient_rows = [tuple(row) for row in coefs]
    physical = [v[name] for name in ELECTRONIC]
    values = {}
    for name, convention in [('temperature_centered', 'centered'),
                             ('temperature_schema_plus', 'literal_pipe_expression')]:
        values[name] = gain_vector(physical, gh, coefs, convention)
    native_mjd, values['pinned_pipe_native'] = pinned_reader(previous/'sources/pipe_read.py')(
        str(hk_path), str(gain_path))
    assert np.array_equal(native_mjd, v['MJD_TIME'])
    native_input = physical[:-1] + [v['VOLT_FEE_CCD']]
    values['voltage_plus_float64'] = gain_vector(native_input, gh, coefs, 'literal_pipe_expression')

    errors = {}
    for name, convention, inputs in [
            ('temperature_centered', 'centered', physical),
            ('temperature_schema_plus', 'literal_pipe_expression', physical),
            ('voltage_plus_float64', 'literal_pipe_expression', native_input)]:
        scalar = np.array([scalar_gain(row, gh, coefficient_rows, convention)
                           for row in zip(*inputs)])
        errors[name] = float(np.max(np.abs(values[name]-scalar)))
        assert errors[name] < 5e-14
    scalar_native = np.array([pipe_scalar32(row, gh, coefficient_rows)
                              for row in zip(*native_input)])
    errors['pinned_pipe_native'] = float(np.max(np.abs(values['pinned_pipe_native']-scalar_native)))
    assert errors['pinned_pipe_native'] < 1e-10
    invalid_field_mapping = bool(np.all(v['TEMP_FEE_CCD'] < 0)
                                 and np.all(v['VOLT_FEE_CCD'] > 0))
    assert invalid_field_mapping
    header_contract = {}
    for kind in ['SCI_RAW_Imagette', 'SCI_RAW_SubArray']:
        rh = fits.Header.fromstring((raw_headers/f'{kind}_hdu01_header.txt').read_text(), sep='\n')
        header_contract[kind] = {key: rh.get(key) for key in
            ['STACKING', 'NLIN_COR', 'NEXP', 'ROUNDING', 'RO_SCRPT', 'RO_HW', 'RO_FREQU']}
        assert rh['NLIN_COR'] is False and rh['ROUNDING'] == 0

    gain_stats = {name: {**stats(a), 'peak_to_peak_ppm': float((a.max()/a.min()-1)*1e6)}
                  for name, a in values.items()}
    comparisons = {name+'_vs_centered': ratio_stats(a, values['temperature_centered'])
                   for name, a in values.items() if name != 'temperature_centered'}
    comparisons['pipe_float32_vs_same_voltage_float64'] = ratio_stats(
        values['pinned_pipe_native'], values['voltage_plus_float64'])

    # Coaddition identities are mathematical conditions, not an interpretation
    # of the unresolved native gcoadd keyword or CAL BIAS/RON units.
    noise_identity = []
    for nexp in [2, 14]:
        b_adu, r_adu, g = 100.0, 7.0, 2.0  # declared artificial values
        noise_identity.append({'nexp': nexp, 'bias_per_readout_adu': b_adu,
            'ron_per_readout_adu': r_adu, 'gain_e_per_adu': g,
            'summed_bias_adu': nexp*b_adu,
            'summed_read_noise_variance_e2': nexp*(r_adu*g)**2,
            'averaged_read_noise_variance_e2': (r_adu*g)**2/nexp})
    summary = {'checkpoint': 'LS7T', 'status': 'NOT_READY',
        'file_key': manifest['file_key'], 'hk_rows': n,
        'retained_new_instrument_bytes': sum(x['count'] for x in manifest['ranges']),
        'science_image_bytes': 0, 'native_residual_trials': 0,
        'pulse_recovery_trials': 0, 'candidates': 0, 'new_search_coverage': 0,
        'hk_utc_range': [str(v['UTC_TIME'][0]), str(v['UTC_TIME'][-1])],
        'max_abs_utc_tt_error_seconds': float(time_error.max()),
        'hk_cadence_seconds': stats(np.diff(v['MJD_TIME'])*86400),
        'field_units_in_native_table': units,
        'fields': {name: stats(v[name]) for name in ELECTRONIC+['VOLT_FEE_CCD']},
        'native_pipe_reads_separate_ccd_voltage': invalid_field_mapping,
        'raw_header_contract': header_contract,
        'onboard_nlc_inverse_coefficients_required_by_header': False,
        'gain_diagnostics_e_per_adu': gain_stats, 'comparisons': comparisons,
        'audit': {'raw_field_value_comparisons': n*len(FIELDS),
                  'scalar_gain_comparisons': n*4,
                  'maximum_absolute_errors_e_per_adu': errors,
                  'method': 'Astropy vs raw struct; vector vs scalar; reviewed original PIPE function'},
        'conditional_coaddition_examples': noise_identity,
        'limitations': ['Simulator and common_sw gain-temperature signs conflict.',
                       'No convention is adopted for science calibration.',
                       'Native gcoadd meaning and actual CAL BIAS/RON units remain unresolved.',
                       'No full PIPE extraction or DRP 14.1.2 execution.'],
        'software': {'python': sys.version.split()[0], 'numpy': np.__version__,
                     'astropy': astropy.__version__}}
    columns = FIELDS + list(values)
    csv_gz(out/'hk_gain_diagnostics.csv.gz', columns,
           zip(*(v[k] for k in FIELDS), *(values[k] for k in values)))
    save_json(out/'summary.json', summary)
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, default=ROOT/'results_ls7t_contract')
    ap.add_argument('--previous', type=Path, default=ROOT/'results_ls7s_calibration')
    ap.add_argument('--output', type=Path, default=ROOT/'results_ls7t_contract')
    ap.add_argument('--raw-headers', type=Path, default=ROOT/'results_ls7r_metadata')
    args = ap.parse_args()
    assess(args.input, args.previous, args.output, args.raw_headers)
