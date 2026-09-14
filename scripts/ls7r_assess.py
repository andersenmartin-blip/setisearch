#!/usr/bin/env python3
"""Offline CHEOPS input audit and timestamp-only pulse-transfer calculation.

No science image data or PHOTOMETRY_* metadata columns are read by this code.
Requires numpy and astropy. Run ls7r_acquire.py --offline after unpacking evidence.
"""
import csv
import gzip
import hashlib
import json
import re
import struct
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.time import Time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7r_metadata'
KINDS = ['SCI_RAW_Imagette', 'SCI_RAW_SubArray', 'SCI_CAL_SubArray',
         'SCI_COR_SubArray', 'PIP_COR_PixelFlagMapSubArray']
TIME_FIELDS = ['UTC_TIME', 'MJD_TIME', 'CE_COUNTER', 'OBT_TIME',
               'NEXP', 'CE_INTEGRITY']


def jsave(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def header(kind, hdu=1):
    return fits.Header.fromstring((OUT / f'{kind}_hdu{hdu:02d}_header.txt').read_text(), sep='\n')


def seconds(utc, origin):
    return np.array([(datetime.fromisoformat(x) - origin).total_seconds() for x in utc])


def raw_field(data, h, name):
    """Independent standard-library decoding of scalar FITS table columns."""
    offset = 0
    lengths = {'A': 1, 'B': 1, 'I': 2, 'J': 4, 'K': 8, 'E': 4, 'D': 8}
    fmts = {'B': '>B', 'I': '>h', 'J': '>i', 'K': '>q', 'E': '>f', 'D': '>d'}
    for col in range(1, h['TFIELDS'] + 1):
        repeat, typ = re.fullmatch(r'(\d+)([ABIJKED])', h[f'TFORM{col}']).groups()
        width = int(repeat) * lengths[typ]
        if h[f'TTYPE{col}'] == name:
            values = []
            for row in range(h['NAXIS2']):
                chunk = data[row*h['NAXIS1']+offset:row*h['NAXIS1']+offset+width]
                if typ == 'A':
                    values.append(chunk.decode('ascii').rstrip())
                else:
                    assert int(repeat) == 1
                    values.append(struct.unpack(fmts[typ], chunk)[0] *
                                  h.get(f'TSCAL{col}', 1) + h.get(f'TZERO{col}', 0))
            return np.array(values)
        offset += width
    raise KeyError(name)


def assess():
    inventory, manifests, tables = {}, {}, {}
    raw_comparisons = 0
    rows_out = []
    for kind in KINDS:
        hdus = json.loads((OUT / f'{kind}_hdus.json').read_text())
        manifest = json.loads((OUT / f'{kind}_ranges.json').read_text())
        inventory[kind], manifests[kind] = hdus, manifest
        allowed = [(h['header_start'], h['header_start']+h['header_bytes']) for h in hdus]
        allowed += [(h['data_start'], h['data_start']+h['data_bytes'])
                    for h in hdus if 'metadata_file' in h]
        for entry in manifest['ranges']:
            b = (OUT / entry['file']).read_bytes()
            assert len(b) == entry['count']
            assert hashlib.sha256(b).hexdigest() == entry['sha256']
            assert entry['status'] == 206
            start, stop = entry['start'], entry['start']+entry['count']
            assert any(lo <= start < stop <= hi for lo, hi in allowed)
            assert entry['headers']['Content-Range'] == f'bytes {start}-{stop-1}/{manifest["total_file_bytes"]}'
        for item in hdus:
            if 'metadata_file' not in item:
                continue
            with fits.open(OUT / item['metadata_file']) as f:
                assert f[1].verify_checksum() == f[1].verify_datasum() == 1
                h = f[1].header
                entry = next(e for e in manifest['ranges'] if e['start'] == item['data_start'])
                raw = (OUT / entry['file']).read_bytes()
                selected = {}
                for name in TIME_FIELDS:
                    if name not in f[1].columns.names:
                        continue
                    v = f[1].data[name].copy()
                    assert np.array_equal(v, raw_field(raw, h, name))
                    raw_comparisons += len(v)
                    selected[name] = v
                # Explicit whitelist excludes PHOTOMETRY_1/2/3, bias, gain,
                # centroid/flux estimates and all other non-timing columns.
                expected_tt = Time(list(selected['UTC_TIME']), format='isot', scale='utc').tt.mjd
                assert np.max(np.abs(expected_tt-selected['MJD_TIME']))*86400 < 2e-6
                tables[item['name']] = selected
                for j in range(len(selected['UTC_TIME'])):
                    rows_out.append([item['name']] + [str(selected[n][j]) if n in selected else ''
                                                     for n in TIME_FIELDS])
    with (OUT / 'timing_rows.csv').open('w', newline='') as f:
        w = csv.writer(f); w.writerow(['table']+TIME_FIELDS); w.writerows(rows_out)
    with gzip.GzipFile(filename=str(OUT/'timing_rows.csv.gz'), mode='wb', mtime=0) as z:
        z.write((OUT/'timing_rows.csv').read_bytes())
    jsave('hdu_inventory.json', inventory)
    jsave('range_manifests.json', manifests)
    i = tables['SCI_RAW_ImagetteMetadata']
    u = tables['SCI_RAW_UnstackedImageMetadata']
    r = tables['SCI_RAW_ImageMetadata']
    c = tables['SCI_CAL_ImageMetadata']
    d = tables['SCI_COR_ImageMetadata']
    for name in ['UTC_TIME', 'MJD_TIME', 'CE_COUNTER', 'CE_INTEGRITY']:
        assert np.array_equal(r[name], c[name]) and np.array_equal(c[name], d[name])
    assert len(u['UTC_TIME']) == 2*len(i['UTC_TIME']) == 14*len(r['UTC_TIME'])
    assert np.all(i['NEXP'] == 2)
    assert np.array_equal(u['CE_COUNTER'].reshape(-1,2)[:,0], i['CE_COUNTER'])
    assert np.all(u['CE_COUNTER'].reshape(-1,14) == r['CE_COUNTER'][:,None])
    origin = datetime.fromisoformat(u['UTC_TIME'][0])
    ut, it, rt = [seconds(t['UTC_TIME'], origin) for t in [u,i,r]]
    assert np.all(np.diff(ut)>0) and np.all(np.diff(it)>0) and np.all(np.diff(rt)>0)
    exptime = header('SCI_RAW_SubArray')['EXPTIME']
    lo, hi = ut-exptime/2, ut+exptime/2
    assert np.all(lo[1:] > hi[:-1])
    # Instrument midpoints are compared, not silently replaced by an ideal grid.
    midpoint_residuals = {
        'pair_mean_minus_imagette_max_abs_s': float(np.max(np.abs(ut.reshape(-1,2).mean(axis=1)-it))),
        'fourteen_mean_minus_subarray_max_abs_s': float(np.max(np.abs(ut.reshape(-1,14).mean(axis=1)-rt))),
        'seven_imagette_mean_minus_subarray_max_abs_s': float(np.max(np.abs(it.reshape(-1,7).mean(axis=1)-rt)))}
    # Separate the four long gaps from the small inter-exposure dead intervals.
    breaks = np.where(np.diff(ut)>2*exptime)[0]
    starts = np.r_[0, breaks+1]; stops = np.r_[breaks, len(ut)-1]
    segments = [{'first_row':int(a),'last_row':int(b),'first_utc':str(u['UTC_TIME'][a]),
                 'last_utc':str(u['UTC_TIME'][b]),'individual_exposures':int(b-a+1),
                 'nominal_live_s':float((b-a+1)*exptime)} for a,b in zip(starts,stops)]
    transfer = []
    # Fixed one-second onset grid anchored to the first individual integration
    # start. Retain gap onsets too; distinguish fully contained segment onsets.
    with gzip.GzipFile(filename=str(OUT/'pulse_ledger.csv.gz'), mode='wb', mtime=0) as z:
        z.write(b'width_s,onset_from_first_start_s,within_segment,imagette_peak_fraction,subarray_peak_fraction\n')
        for width in [30,60,100]:
            onsets = lo[0] + np.arange(int(np.floor(hi[-1]-lo[0]-width))+1, dtype=float)
            inside = np.zeros(len(onsets),dtype=bool)
            for a,b in zip(starts,stops):
                inside |= (onsets >= lo[a]) & (onsets+width <= hi[b])
            pi, ps = [], []
            for chunk in np.array_split(onsets, max(1, int(np.ceil(len(onsets)/128)))):
                weights = np.maximum(0,np.minimum(hi[None,:],chunk[:,None]+width)-
                                     np.maximum(lo[None,:],chunk[:,None])) / exptime
                pi.extend(weights.reshape(len(chunk),-1,2).mean(axis=2).max(axis=1))
                ps.extend(weights.reshape(len(chunk),-1,14).mean(axis=2).max(axis=1))
            pi,ps=np.array(pi),np.array(ps)
            assert np.all((pi>=0)&(pi<=1+1e-10)) and np.all((ps>=0)&(ps<=1+1e-10))
            for j,onset in enumerate(onsets):
                z.write(f'{width},{onset-lo[0]:.0f},{int(inside[j])},{pi[j]:.12g},{ps[j]:.12g}\n'.encode())
            # Independent scalar endpoint cases, including a long-gap onset.
            checks = sorted(set([0,len(onsets)//2,len(onsets)-1,int(np.argmin(ps))]))
            for j in checks:
                vals = [max(0,min(float(b),onsets[j]+width)-max(float(a),onsets[j]))/exptime
                        for a,b in zip(lo,hi)]
                for n,actual in [(2,pi[j]),(14,ps[j])]:
                    expected=max(sum(vals[k:k+n])/n for k in range(0,len(vals),n))
                    assert abs(expected-actual)<2e-12
            transfer.append({'width_s':width,'onsets':len(onsets),'fully_within_segment':int(inside.sum()),
                             'zero_temporal_response_onsets':int(np.sum(pi==0)),
                             'imagette_peak_fraction_within_segment':[float(pi[inside].min()),float(pi[inside].max())],
                             'subarray_peak_fraction_within_segment':[float(ps[inside].min()),float(ps[inside].max())]})
    catalogue=json.loads((OUT/'archive_visits.json').read_text())['rows']
    selected=sorted(catalogue,key=lambda x:(x[12],x[0]))[0]
    assert selected[0]=='300024000301' and all(x[9]=='PUBLIC' for x in catalogue)
    ap=json.loads((OUT/'archive_products.json').read_text())['rows']
    dp=json.loads((OUT/'dace_products.json').read_text())
    assert {x[1] for x in ap} <= {Path(x).stem for x in dp['file']}
    summary={'file_key':'CH_PR300024_TG000301_V0300','obsid':1015522,'pipeline':'14.1.2',
             'archive_visits':len(catalogue),'archive_products':len(ap),'dace_products':len(dp['file']),
             'retained_range_bytes':sum(e['count'] for m in manifests.values() for e in m['ranges']),
             'retained_range_count':sum(len(m['ranges']) for m in manifests.values()),
             'hdu_count':sum(len(x) for x in inventory.values()),
             'metadata_row_count':len(rows_out),'raw_timing_field_comparisons':raw_comparisons,
             'individual_exposure_s':exptime,'individual_exposure_rows':len(ut),
             'imagette_rows':len(it),'subarray_rows':len(rt),
             'imagette_period_median_s':float(np.median(np.diff(it))),
             'subarray_period_median_s':float(np.median(np.diff(rt))),
             'nominal_live_s':float(len(ut)*exptime),'elapsed_midpoint_span_s':float(ut[-1]-ut[0]),
             'long_gap_midpoint_intervals_s':np.diff(ut)[breaks].tolist(),
             'segments':segments,'midpoint_checks':midpoint_residuals,
             'ce_integrity_counts':dict(Counter(map(str,r['CE_INTEGRITY']))),
             'pulse_transfer':transfer,'science_image_bytes_acquired':0,
             'science_flux_columns_analyzed':0,'native_event_searches':0,
             'claim':'Metadata and temporal averaging only; no pixel response or detector qualification.'}
    jsave('summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    assess()
