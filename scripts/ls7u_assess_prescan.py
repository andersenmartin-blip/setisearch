#!/usr/bin/env python3
"""Offline, predeclared virtual-prescan assessment; no target-image reads."""
import argparse
import gzip
import json
import math
import struct
import sys
from pathlib import Path

import astropy
import numpy as np

from ls7s_assess_calibration import csv_gz, load_table, save_json, stats
from ls7u_acquire_prescan import RANGES, header_check, image_hdu, read_saved, sha

ROOT = Path(__file__).resolve().parents[1]
NEXP = 14
MAD_NORMAL = 1.482602218505602
BOOTSTRAPS = 4096
SEED = 712021


def bootstrap_blocks(bias, variance, mjd):
    boundaries = np.r_[0, np.flatnonzero(np.diff(mjd)*86400 > 100)+1, len(mjd)]
    blocks = []
    for lo, hi in zip(boundaries[:-1], boundaries[1:]):
        for start in range(lo, hi, 16):
            stop = min(start+16, hi)
            blocks.append((stop-start, float(bias[start:stop].sum()),
                           float(variance[start:stop].sum())))
    a = np.asarray(blocks)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, len(a), size=(BOOTSTRAPS, len(a)))
    totals = a[draws].sum(axis=1)
    b = totals[:,1]/totals[:,0]
    r = np.sqrt(totals[:,2]/totals[:,0])
    return {'seed': SEED, 'draws': BOOTSTRAPS, 'maximum_block_frames': 16,
        'blocks': len(blocks), 'segment_frame_counts': np.diff(boundaries).tolist(),
        'percentiles': [0.5,99.5],
        'bias_per_readout_adu_interval': np.percentile(b,[0.5,99.5]).tolist(),
        'noise_per_readout_adu_interval': np.percentile(r,[0.5,99.5]).tolist(),
        'interpretation': 'Descriptive block-resampling stability, not total calibration uncertainty'}


def assess(inp, old, out):
    out.mkdir(exist_ok=True)
    protocol = ROOT/'LS7U_PRESCAN_PROTOCOL.md'
    pid = json.loads((inp/'protocol_identity.json').read_text())
    assert sha(protocol.read_bytes()) == pid['sha256']
    manifest = json.loads((inp/'acquisition.json').read_text())
    assert [(e['start'],e['count']) for e in manifest['ranges']] == RANGES
    header, body = [read_saved(inp, e) for e in manifest['ranges']]
    header_check(header)
    with image_hdu(header, body) as hd:
        assert hd[1].verify_checksum() == hd[1].verify_datasum() == 1
        cube = hd[1].data.astype(np.float64)
        assert cube.shape == (432,200,4)
    direct = np.array([v[0] for v in struct.iter_unpack('>f',body)], dtype=np.float64)
    assert direct.size == cube.size and np.array_equal(direct,cube.ravel())
    assert np.isfinite(cube).all(), 'Nonfinite input: no dropping or imputation permitted'
    t, th, time_comparisons = load_table(old, 'SCI_RAW_SubArray', 9,
                                         ['UTC_TIME','MJD_TIME','CE_COUNTER'])
    assert len(t['MJD_TIME']) == len(cube) and np.all(np.diff(t['MJD_TIME']) > 0)

    raw_mean = cube.mean(axis=(1,2))
    raw_median = np.median(cube,axis=(1,2))
    raw_var = cube.var(axis=(1,2),ddof=0)
    raw_mad = np.median(np.abs(cube-raw_median[:,None,None]),axis=(1,2))*MAD_NORMAL
    diff_var = np.diff(cube,axis=1).var(axis=(1,2),ddof=0)
    col_mean = cube.mean(axis=1)
    centered = cube-col_mean[:,None,:]
    left, right = centered[:,:-1,:], centered[:,1:,:]
    covariance = (left*right).mean(axis=(1,2))
    correlation = covariance/np.sqrt((left*left).mean(axis=(1,2))*(right*right).mean(axis=(1,2)))
    b_frame, v_frame = raw_median/NEXP, raw_var/NEXP
    r_frame = np.sqrt(v_frame)
    b_visit = float(b_frame.mean())
    r_visit = float(np.sqrt(v_frame.mean()))

    # Scalar mean, median and population variance, evaluated frame by frame
    # independently of the vectorized reductions; no clipping or fit tuning.
    errors = {'mean':0.0,'median':0.0,'variance':0.0}
    for index in range(len(cube)):
        row = direct[index*800:(index+1)*800].tolist()
        mean = math.fsum(row)/800
        ordered = sorted(row)
        median = (ordered[399]+ordered[400])/2
        variance = math.fsum((x-mean)**2 for x in row)/800
        for name, scalar, vector in [('mean',mean,raw_mean[index]),
                 ('median',median,raw_median[index]),('variance',variance,raw_var[index])]:
            errors[name] = max(errors[name],abs(scalar-float(vector)))
    assert errors['mean'] < 1e-9 and errors['median'] == 0 and errors['variance'] < 1e-8

    historical = json.loads((ROOT/'results_ls7s_calibration/summary.json').read_text())
    cal = {k: historical['cal_cor_equal_metadata'][k]['minimum'] for k in ['BIAS','RON']}
    assert cal == {'BIAS':563.4299926757812, 'RON':7.130000114440918}
    gains = {}
    with gzip.open(ROOT/'results_ls7t_contract/hk_gain_diagnostics.csv.gz','rt') as stream:
        import csv
        rows = list(csv.DictReader(stream))
    for key in ['temperature_centered','temperature_schema_plus','pinned_pipe_native']:
        gains[key] = float(np.median([float(row[key]) for row in rows]))
    candidates = [('per_readout_ADU',1.0,1.0),('summed_ADU',NEXP,math.sqrt(NEXP))]
    candidates += [('per_readout_electrons_'+key,g,g) for key,g in gains.items()]
    comparisons = []
    for name, bs, rs in candidates:
        bias_ratio, noise_ratio = cal['BIAS']/(b_visit*bs), cal['RON']/(r_visit*rs)
        comparisons.append({'hypothesis':name,'bias_scale':bs,'noise_scale':rs,
            'predicted_bias':b_visit*bs, 'predicted_noise':r_visit*rs,
            'cal_bias_to_prediction':bias_ratio,'cal_ron_to_prediction':noise_ratio,
            'bias_within_1_percent':abs(bias_ratio-1)<=0.01,
            'ron_within_1_percent':abs(noise_ratio-1)<=0.01})

    summary = {'checkpoint':'LS7U','file_key':manifest['file_key'],
        'input_decision':'NOT_READY_FOR_TARGET_IMAGE_STUDY',
        'protocol_sha256':pid['sha256'], 'virtual_reference_array_bytes':len(body),
        'retained_header_bytes':len(header), 'target_image_bytes':0,
        'native_source_residual_trials':0,'pulse_recovery_trials':0,
        'new_candidates':0,'new_qualified_observing_seconds':0,
        'extension':'SCI_RAW_OverscanLeft','hdu_index':7,
        'shape':list(cube.shape),'values':int(cube.size),'nexp':NEXP,
        'native_unit':'ADU','onboard_processing':'image','stacking':'coadd',
        'raw_summed_values':{'min':float(cube.min()),'max':float(cube.max())},
        'primary':{'bias_per_readout_adu':b_visit,
                   'effective_read_noise_per_readout_adu':r_visit},
        'alternative_summaries':{
            'mean_of_frame_means_per_readout_adu':float(raw_mean.mean()/NEXP),
            'mean_of_frame_mad_noise_per_readout_adu':float(raw_mad.mean()/math.sqrt(NEXP)),
            'row_difference_effective_noise_per_readout_adu':float(np.sqrt(diff_var.mean()/(2*NEXP))),
            'column_mean_bias_per_readout_adu':(col_mean.mean(axis=0)/NEXP).tolist(),
            'frame_bias_per_readout_adu':stats(b_frame),
            'frame_effective_noise_per_readout_adu':stats(r_frame),
            'lag_one_row_covariance_summed_adu2':stats(covariance),
            'lag_one_row_correlation':stats(correlation)},
        'bootstrap':bootstrap_blocks(b_frame,v_frame,t['MJD_TIME']),
        'cal_cor_values_without_native_unit_cards':cal,
        'ls7t_median_gain_diagnostics_e_per_adu':gains,
        'unit_scaling_comparisons':comparisons,
        'audit':{'astropy_vs_struct_values':int(cube.size),
                 'frame_scalar_statistics':len(cube)*3,
                 'frame_scalar_max_absolute_errors':errors,
                 'timestamp_metadata_values':time_comparisons,
                 'original_fits_checksum_valid':True},
        'limitations':['Effective RON uses independent coadded-readout scaling; no individual readouts are available.',
            'Numerical agreement does not establish undocumented CAL unit semantics.',
            'Virtual prescan does not supply flat, spatial science-pixel bias, dark, PSF, or gcoadd calibration.',
            'No complete PIPE or DRP extraction, no source detector or pulse recovery.'],
        'software':{'python':sys.version.split()[0],'numpy':np.__version__,'astropy':astropy.__version__}}
    columns=['frame','UTC_TIME','MJD_TT','CE_COUNTER','bias_mean_per_readout_ADU',
        'bias_median_per_readout_ADU','effective_RON_per_readout_ADU',
        'MAD_noise_per_readout_ADU','row_difference_noise_per_readout_ADU',
        'row_lag1_covariance_summed_ADU2','row_lag1_correlation'] + [f'column_{k}_bias_per_readout_ADU' for k in range(4)]
    csv_gz(out/'prescan_frame_statistics.csv.gz',columns,
        zip(range(len(cube)),t['UTC_TIME'],t['MJD_TIME'],t['CE_COUNTER'],
            raw_mean/NEXP,b_frame,r_frame,raw_mad/math.sqrt(NEXP),
            np.sqrt(diff_var/(2*NEXP)),covariance,correlation,*(col_mean[:,k]/NEXP for k in range(4))))
    save_json(out/'summary.json',summary)
    print(json.dumps(summary,indent=2,allow_nan=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=ROOT/'results_ls7u_prescan')
    ap.add_argument('--metadata',type=Path,default=ROOT/'results_ls7r_metadata')
    ap.add_argument('--output',type=Path,default=ROOT/'results_ls7u_prescan')
    args = ap.parse_args()
    assess(args.input,args.metadata,args.output)
