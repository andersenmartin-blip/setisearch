#!/usr/bin/env python3
"""Offline LS7S electronic-input assessment; never opens science image data.

Two gain formulas are conditional algebraic diagnostics, not adopted
calibrations. In particular, the PIPE-expression column substitutes existing
degree-C metadata for a differently named PIPE HK field. See LS7S_SCOPE.md.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import struct
from datetime import datetime
from pathlib import Path

import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
GAIN_NAME = 'CH_TU2020-02-18T06-15-13_REF_APP_GainCorrection_V0109.fits'
GAIN_BLOB = '3bde861175310b797e53a9be506d9f2eab816a73'
PIPE_COMMIT = 'da15a87348e2657eac8dd08623ac258e6ac59df8'
ELECTRONIC = ['VOLT_FEE_VSS', 'VOLT_FEE_VOD', 'VOLT_FEE_VRD',
              'VOLT_FEE_VOG', 'TEMP_FEE_CCD']
EXPONENTS = ['EXP_VSS', 'EXP_VOD', 'EXP_VRD', 'EXP_VOG', 'EXP_TEMP']
TIME = ['UTC_TIME', 'MJD_TIME', 'CE_COUNTER']
TABLES = {
    'u': ('SCI_RAW_SubArray', 10, TIME + ['GAIN_0', 'BIAS_0', 'BIAS'] +
          ['CE_' + n for n in ELECTRONIC]),
    'r': ('SCI_RAW_SubArray', 9, TIME + ['CCD_TIMING_SCRIPT', 'PIX_DATA_OFFSET',
          'HK_SOURCE'] + ['HK_' + n for n in ELECTRONIC]),
    'c': ('SCI_CAL_SubArray', 2, TIME + ['BIAS', 'RON']),
    'd': ('SCI_COR_SubArray', 2, TIME + ['BIAS', 'RON']),
    'i': ('SCI_RAW_Imagette', 2, TIME + ['NEXP']),
}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def blob_digest(b):
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def stats(values):
    a = np.asarray(values)
    if a.dtype.kind not in 'fiu':
        return {'rows': len(a), 'values': sorted(set(map(str, a)))}
    good = np.isfinite(a)
    return {'rows': len(a), 'finite': int(good.sum()),
            'missing': int((~good).sum()),
            'minimum': float(a[good].min()) if good.any() else None,
            'maximum': float(a[good].max()) if good.any() else None,
            'distinct_finite': int(len(np.unique(a[good])))}


def scalar_column(raw, h, name):
    """Decode scalar columns from original range bytes, separately from Astropy."""
    lengths = {'A': 1, 'B': 1, 'I': 2, 'J': 4, 'K': 8, 'E': 4, 'D': 8}
    codes = {'B': '>B', 'I': '>h', 'J': '>i', 'K': '>q', 'E': '>f', 'D': '>d'}
    pos = 0
    for col in range(1, h['TFIELDS'] + 1):
        n, typ = re.fullmatch(r'(\d+)([ABIJKED])', h[f'TFORM{col}']).groups()
        n = int(n)
        width = n * lengths[typ]
        if h[f'TTYPE{col}'] == name:
            vals = []
            for row in range(h['NAXIS2']):
                start = row * h['NAXIS1'] + pos
                b = raw[start:start + width]
                if typ == 'A':
                    vals.append(b.decode('ascii').rstrip())
                else:
                    assert n == 1
                    v = struct.unpack(codes[typ], b)[0]
                    vals.append(v * h.get(f'TSCAL{col}', 1) + h.get(f'TZERO{col}', 0))
            return vals
        pos += width
    raise KeyError(name)


def load_table(inp, kind, index, fields):
    meta = json.loads((inp / f'{kind}_hdus.json').read_text())[index]
    assert meta['name'] in {'SCI_RAW_UnstackedImageMetadata',
           'SCI_RAW_ImageMetadata', 'SCI_CAL_ImageMetadata',
           'SCI_COR_ImageMetadata', 'SCI_RAW_ImagetteMetadata'}
    manifest = json.loads((inp / f'{kind}_ranges.json').read_text())
    entry = next(x for x in manifest['ranges'] if x['start'] == meta['data_start'])
    raw = (inp / entry['file']).read_bytes()
    assert len(raw) == entry['count'] and digest(raw) == entry['sha256']
    with fits.open(inp / meta['metadata_file']) as hd:
        assert hd[1].verify_checksum() == hd[1].verify_datasum() == 1
        h = hd[1].header.copy()
        values = {}
        for name in fields:
            assert not name.startswith('PHOTOMETRY')
            v = hd[1].data[name].copy()
            direct = np.asarray(scalar_column(raw, h, name))
            if v.dtype.kind in 'fiu':
                assert np.array_equal(v, direct, equal_nan=True), (kind, name)
            else:
                assert np.array_equal(v, direct), (kind, name)
            values[name] = v
    return values, h, sum(len(v) for v in values.values())


def gain_vector(physical, h, coefs, convention):
    """Evaluate declared algebra only. Does not assign detector calibration."""
    if convention not in ('centered', 'literal_pipe_expression'):
        raise ValueError(convention)
    vss, vod, vrd, vog, temp = [np.asarray(v, dtype=float) for v in physical]
    offset = temp - h['TEMP_OFF'] if convention == 'centered' else temp + h['TEMP_OFF']
    x = [vss - h['VSS_OFF'], vod - vss - h['VOD_OFF'],
         vrd - vss - h['VRD_OFF'], vog - vss - h['VOG_OFF'], offset]
    basis = np.ones((len(temp), len(coefs)))
    for axis, name in zip(x, EXPONENTS):
        basis *= axis[:, None] ** np.asarray(coefs[name])[None, :]
    response = h['GAIN_NOM'] * (1 + basis @ np.asarray(coefs['FACTOR']))
    assert np.all(np.isfinite(response) & (response > 0))
    return 1 / response


def scalar_gain(physical, h, coeff_rows, convention):
    """Independent row/term evaluation with math.fsum, no array polynomial."""
    vss, vod, vrd, vog, temp = map(float, physical)
    x = [vss-h['VSS_OFF'], vod-vss-h['VOD_OFF'], vrd-vss-h['VRD_OFF'],
         vog-vss-h['VOG_OFF'], temp-h['TEMP_OFF'] if convention == 'centered'
         else temp+h['TEMP_OFF']]
    terms = []
    for c in coeff_rows:
        term = float(c[0])
        for a, exp in zip(x, c[2:]):
            term *= a ** int(exp)
        terms.append(term)
    return 1 / (h['GAIN_NOM'] * (1 + math.fsum(terms)))


def csv_gz(path, columns, rows):
    s = io.StringIO(newline='')
    w = csv.writer(s)
    w.writerow(columns)
    w.writerows(rows)
    with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as f:
        f.write(s.getvalue().encode())


def assess(inp, out):
    out.mkdir(exist_ok=True)
    tables, schemas, raw_count = {}, {}, 0
    for key, (kind, index, fields) in TABLES.items():
        tables[key], schemas[key], n = load_table(inp, kind, index, fields)
        raw_count += n
    u, r, c, d, im = [tables[k] for k in ['u', 'r', 'c', 'd', 'i']]
    assert len(u['CE_COUNTER']) == 6048 and len(im['CE_COUNTER']) == 3024
    assert np.array_equal(u['CE_COUNTER'].reshape(-1, 2)[:, 0], im['CE_COUNTER'])
    assert np.all(u['CE_COUNTER'].reshape(-1, 14) == r['CE_COUNTER'][:, None])
    assert np.all(im['NEXP'] == 2)
    for name in TIME:
        assert np.array_equal(r[name], c[name]) and np.array_equal(c[name], d[name])

    gain_path = out / 'calibration' / GAIN_NAME
    b = gain_path.read_bytes()
    assert blob_digest(b) == GAIN_BLOB
    with fits.open(gain_path) as hd:
        h = hd[1].header.copy()
        coefficients = hd[1].data.copy()
        assert h['EXTNAME'] == 'REF_APP_GainCorrection'
        assert hd[1].verify_checksum() == hd[1].verify_datasum() == 1
        assert h['NAXIS1'] == 26 and h['NAXIS2'] == 21
        loc = hd[1].fileinfo()['datLoc']
        body = b[loc:loc+h['NAXIS1']*h['NAXIS2']]
        coefficient_count = 0
        scalar_coefs = []
        for name in coefficients.names:
            values = scalar_column(body, h, name)
            assert np.array_equal(np.asarray(values), coefficients[name])
            coefficient_count += len(values)
            scalar_coefs.append(values)
        scalar_coefs = list(zip(*scalar_coefs))
    start = datetime.fromisoformat(h['V_STRT_U'])
    stop = datetime.fromisoformat(h['V_STOP_U'])
    assert all(start <= datetime.fromisoformat(t) < stop for t in u['UTC_TIME'])
    raw_header = fits.Header.fromstring((inp/'SCI_RAW_SubArray_hdu01_header.txt').read_text(), sep='\n')
    im_header = fits.Header.fromstring((inp/'SCI_RAW_Imagette_hdu01_header.txt').read_text(), sep='\n')
    assert h['RO_HW'] == raw_header['RO_HW'] == 'main'
    (out/'gain_reference_header.txt').write_text(h.tostring(sep='\n', endcard=True, padding=False)+'\n')
    csv_gz(out/'gain_coefficients.csv.gz', coefficients.names, scalar_coefs)

    physical = [u['CE_'+name] for name in ELECTRONIC]
    gains = {}
    audit_count, max_error = 0, 0.0
    for convention in ['centered', 'literal_pipe_expression']:
        g = gain_vector(physical, h, coefficients, convention)
        check = np.array([scalar_gain(row, h, scalar_coefs, convention) for row in zip(*physical)])
        err = float(np.max(np.abs(g-check)))
        assert err < 5e-14
        audit_count += len(g)
        max_error = max(max_error, err)
        gains[convention] = g
    # A physical temperature exactly at the signed reference offset must
    # give zero centered perturbation. This tests declared algebra, not DRP.
    reference = [h['VSS_OFF'], h['VSS_OFF']+h['VOD_OFF'],
                 h['VSS_OFF']+h['VRD_OFF'], h['VSS_OFF']+h['VOG_OFF'], h['TEMP_OFF']]
    assert abs(gain_vector([[x] for x in reference], h, coefficients, 'centered')[0]
               - 1/h['GAIN_NOM']) < 2e-15

    ratio = gains['literal_pipe_expression']/gains['centered']
    normalized = ratio / np.median(ratio)-1
    gain_stats = {key: {**stats(v), 'peak_to_peak_ppm':float((v.max()/v.min()-1)*1e6)}
                  for key, v in gains.items()}
    electronic_stats = {key:{name:stats(v) for name,v in vals.items() if name not in TIME}
                        for key, vals in tables.items()}
    matches = {}
    for name in ['BIAS', 'RON']:
        assert np.array_equal(c[name], d[name])
        matches[name] = stats(c[name])
    selected = json.loads((out/'reference_rows.json').read_text())['selected']
    names = json.loads((inp/'calibration_log_extract.json').read_text())['reference_filenames']
    assert len(names) == len(selected) == 15
    by_name = {x['name']+'.fits':x for x in selected}
    inventory = []
    visit_lo, visit_hi = [datetime.fromisoformat(u['UTC_TIME'][i]) for i in [0,-1]]
    for name in names:
        item = {'filename':name, 'archive_match':not by_name[name].get('missing',False),
                'contents_verified':name==GAIN_NAME}
        if item['archive_match']:
            cols = by_name[name]['row'].strip().split('\t')
            assert cols[0]+'.fits' == name and len(cols)==6
            item.update(archive_size_megabytes=cols[3], archive_start_utc=cols[4],
                        archive_stop_utc=cols[5])
            lo, hi = [datetime.fromisoformat(x) for x in cols[4:6]]
            item['archive_interval_contains_visit'] = lo <= visit_lo and visit_hi < hi
            item['days_start_after_visit_start'] = max(0.,(lo-visit_lo).total_seconds()/86400)
        inventory.append(item)
    save_json(out/'reference_inventory.json',inventory)

    null_fields = ['GAIN_0','BIAS_0','BIAS']
    assert all(not np.isfinite(u[n]).any() for n in null_fields)
    rows = []
    for j in range(len(u['UTC_TIME'])):
        rows.append([j, u['UTC_TIME'][j], repr(float(u['MJD_TIME'][j])),int(u['CE_COUNTER'][j])]
                    + [repr(float(u[n][j])) for n in null_fields]
                    + [repr(float(v[j])) for v in physical]
                    + [repr(float(gains[k][j])) for k in gains])
    csv_gz(out/'exposure_calibration_ledger.csv.gz',
           ['row','UTC_TIME','MJD_TIME_TT','CE_COUNTER']+null_fields+
           ['CE_'+n for n in ELECTRONIC]+['gain_centered_e_per_adu','gain_literal_pipe_expression_e_per_adu'], rows)
    csv_gz(out/'subarray_calibration_ledger.csv.gz',
           ['row']+TIME+['CCD_TIMING_SCRIPT','PIX_DATA_OFFSET','HK_SOURCE']+
           ['HK_'+n for n in ELECTRONIC]+['CAL_BIAS','CAL_RON'],
           ([j]+[r[n][j] for n in TIME+['CCD_TIMING_SCRIPT','PIX_DATA_OFFSET','HK_SOURCE']+
                  ['HK_'+n for n in ELECTRONIC]]+[c['BIAS'][j],c['RON'][j]]
            for j in range(len(r['UTC_TIME']))))

    blockers = [
      'Only the exact gain reference has validated file contents; the other required image/LUT references have not been delivered.',
      'The recorded dark/bad-pixel archive start dates follow this visit; applicability is unresolved, not proven invalid.',
      'Imagettes are labelled gcoadd; subarrays coadd. The raw-ADU and onboard gain/bias mapping is unresolved.',
      'All 6048 GAIN_0, BIAS_0 and BIAS entries in the unstacked metadata are NaN; finite HK readings do not replace them.',
      'The degree-C mapping to the pinned PIPE reader and the sign of its temperature offset need independent mission verification.',
      'PSF/background protection, instantaneous defects/cosmics/saturation and calibration/noise propagation are not yet qualified.'
    ]
    result = {
      'stage':'LS7S','file_key':'CH_PR300024_TG000301_V0300','input_decision':'NOT_READY',
      'science_image_bytes_acquired':0,'native_trials':0,'new_candidates':0,'new_qualified_observing_seconds':0,
      'references_requested':15,'archive_exact_matches':sum(x['archive_match'] for x in inventory),
      'reference_contents_verified':1,'archive_intervals_after_observation':sum(
            x.get('days_start_after_visit_start',0)>0 for x in inventory),
      'gain_reference':{'filename':GAIN_NAME,'bytes':len(b),'sha256':digest(b),'git_blob_sha':GAIN_BLOB,
          'pinned_pipe_commit':PIPE_COMMIT,'rows':21,'row_bytes':26,'checksum_pass':True,
          'validity_contains_all_exposures':True,'readout_hardware_matches':True,
          'reference_nominal_adu_per_e':h['GAIN_NOM'],'signed_temperature_offset_degC':h['TEMP_OFF']},
      'exposure_rows':len(u['UTC_TIME']), 'imagette_rows':len(im['UTC_TIME']), 'subarray_rows':len(r['UTC_TIME']),
      'stacking_labels':{'imagette':im_header['STACKING'],'subarray':raw_header['STACKING']},
      'electronic_fields':electronic_stats,'cal_cor_equal_metadata':matches,
      'conditional_gain_algebra':{
          'physical_calibration_adopted':False,
          'interpretation':'Centered reference-offset and literal PIPE expression on the same degree-C metadata; latter HK-field adapter is unverified.',
          'gain_ranges':gain_stats,
          'relative_literal_over_centered_minus_one':stats(ratio-1),
          'median_normalized_ratio_max_abs_ppm':float(np.max(np.abs(normalized))*1e6)},
      'audit':{'status':'PASS','raw_field_comparisons':raw_count,'coefficient_comparisons':coefficient_count,
          'gain_scalar_comparisons':audit_count,'gain_max_abs_discrepancy':max_error,
          'reference_offset_known_answer_pass':True,
          'independence':'Separate byte/row/term paths in the same assessment; not an external review.'},
      'blockers':blockers,
    }
    save_json(out/'summary.json',result)
    print(json.dumps({k:result[k] for k in ['stage','input_decision','archive_exact_matches',
                    'reference_contents_verified','conditional_gain_algebra','audit']},indent=2))
    return result


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=ROOT/'results_ls7r_metadata')
    ap.add_argument('--output',type=Path,default=ROOT/'results_ls7s_calibration')
    args=ap.parse_args()
    assess(args.input,args.output)
