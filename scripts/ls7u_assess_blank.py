#!/usr/bin/env python3
"""Offline, separately scoped PIPE blank-reference input check; no target pixels."""
import argparse
import ast
import hashlib
import io
import json
import math
import statistics
import struct
import sys
from pathlib import Path

import astropy
from astropy.io import fits
import numpy as np

from ls7s_assess_calibration import csv_gz, save_json, stats
from ls7u_acquire_prescan import image_hdu, read_saved, sha

ROOT = Path(__file__).resolve().parents[1]
RANGES = [(69134400,8640),(69143040,2764800)]
NEXP = 14
PIPE_COMMIT = 'da15a87348e2657eac8dd08623ac258e6ac59df8'
SOURCE_FILES = [
    ('results_ls7u_prescan/pipe_statistics.py', 'sigma_clip',
     'b68bc0ad9499aeff8780cd24f98975f606a6cd07'),
    ('results_ls7s_calibration/sources/pipe_read.py', 'bias_ron_adu',
     '78e1f085b63c0e1768d660cb288cdd51357fe7ce')]


def source_functions():
    namespace = {'np':np, 'fits':fits}
    identities = []
    for path, function, expected in SOURCE_FILES:
        body = (ROOT/path).read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
        assert actual == expected, f'Pinned PIPE source changed: {path}'
        tree = ast.parse(body,filename=path)
        nodes = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == function]
        assert len(nodes) == 1
        # Execute only the original function AST, without package initialization.
        exec(compile(ast.Module(body=nodes,type_ignores=[]),path,'exec'),namespace)
        identities.append({'path':path,'function':function,'bytes':len(body),
                           'git_blob_sha':actual,'sha256':sha(body),'commit':PIPE_COMMIT})
    return namespace, identities


def scalar_clipping(values, sigma_clip):
    """Independent scalar median/population sigma, with re-entry each iteration."""
    mask = [True]*len(values)
    trace = []
    for iteration in range(1,11):
        selected = [x for x, keep in zip(values,mask) if keep]
        median = statistics.median(selected)
        mean = math.fsum(selected)/len(selected)
        std = math.sqrt(math.fsum((x-mean)**2 for x in selected)/len(selected))
        mask = [abs(x-median) <= 3*std for x in values]
        trace.append({'iteration':iteration,'input_selected':len(selected),
                      'median_summed_adu':median,'sigma_summed_adu':std,
                      'output_selected':sum(mask)})
        original = sigma_clip(np.asarray(values),clip=3,niter=iteration)
        assert np.array_equal(original,np.asarray(mask)), f'Clip mask differs at iteration {iteration}'
    selected = [x for x,keep in zip(values,mask) if keep]
    median = statistics.median(selected)
    mean = math.fsum(selected)/len(selected)
    std = math.sqrt(math.fsum((x-mean)**2 for x in selected)/len(selected))
    return np.asarray(mask), median/NEXP, std/math.sqrt(NEXP), trace


def assess(inp, out):
    out.mkdir(parents=True,exist_ok=True)
    pid = json.loads((inp/'protocol_identity.json').read_text())
    assert sha((ROOT/'LS7U_BLANK_SUPPLEMENT.md').read_bytes()) == pid['sha256']
    manifest = json.loads((inp/'acquisition.json').read_text())
    assert manifest['extension'] == 'SCI_RAW_BlankLeft'
    assert [(e['start'],e['count']) for e in manifest['ranges']] == RANGES
    header, body = [read_saved(inp,e) for e in manifest['ranges']]
    native = ''.join((ROOT/'results_ls7r_metadata/SCI_RAW_SubArray_hdu02_header.txt').read_text().splitlines()).encode('ascii')
    assert header == native
    h = fits.Header.fromstring(header.decode('ascii'),sep='')
    for key,value in {'EXTNAME':'SCI_RAW_BlankLeft','BITPIX':-32,'NAXIS':3,
            'NAXIS1':8,'NAXIS2':200,'NAXIS3':432,'NEXP':NEXP,'BUNIT':'ADU',
            'MRG_PROC':'image','STACKING':'coadd','ROUNDING':0,'NLIN_COR':False}.items():
        assert h[key] == value
    with image_hdu(header,body) as hd:
        assert hd[1].verify_checksum() == hd[1].verify_datasum() == 1
        cube = hd[1].data.astype(np.float64)
        assert cube.shape == (432,200,8) and np.isfinite(cube).all()
    direct = [v[0] for v in struct.iter_unpack('>f',body)]
    assert np.array_equal(np.asarray(direct),cube.ravel())

    # The original function needs hdul[1].header['NEXP'] and hdul[2].data only.
    # Retain the native blank header/body; do not fabricate a science image.
    science_header = fits.Header.fromtextfile(ROOT/'results_ls7r_metadata/SCI_RAW_SubArray_hdu01_header.txt')
    assert science_header['NEXP'] == NEXP
    placeholder = fits.ImageHDU()
    placeholder.header['NEXP'] = science_header['NEXP']
    surrogate = (fits.PrimaryHDU().header.tostring().encode('ascii') +
                 placeholder.header.tostring().encode('ascii') + header + body)
    namespace, identities = source_functions()
    original = namespace['bias_ron_adu']
    sigma_clip = namespace['sigma_clip']
    bias, ron = map(float,original(io.BytesIO(surrogate),1.0))
    mask, scalar_bias, scalar_ron, trace = scalar_clipping(direct,sigma_clip)
    assert abs(bias-scalar_bias) < 1e-10 and abs(ron-scalar_ron) < 1e-10

    primary = json.loads((ROOT/'results_ls7u_prescan/summary.json').read_text())
    cal = primary['cal_cor_values_without_native_unit_cards']
    gain_results = []
    for name,g in primary['ls7t_median_gain_diagnostics_e_per_adu'].items():
        gb, gr = map(float,original(io.BytesIO(surrogate),g))
        scaled_mask = sigma_clip(g*cube.ravel(),clip=3,niter=10)
        assert np.array_equal(scaled_mask,mask)
        assert abs(gb-g*bias) < 1e-9 and abs(gr-g*ron) < 1e-9
        gain_results.append({'gain_interpretation':name,'gain_e_per_adu':g,
            'bias_electrons_per_readout':gb,'effective_ron_electrons_per_readout':gr,
            'mask_identical_to_adu':True})

    frame_rows = []
    selected_cube = mask.reshape(cube.shape)
    for frame in range(len(cube)):
        selected = cube[frame][selected_cube[frame]]
        frame_rows.append((frame,int(selected.size),int(1600-selected.size),
            float(np.median(cube[frame])/NEXP),float(np.std(cube[frame])/math.sqrt(NEXP)),
            float(np.median(selected)/NEXP),float(np.std(selected)/math.sqrt(NEXP))))
    csv_gz(out/'blank_frame_statistics.csv.gz',
        ['frame','global_clip_kept','global_clip_removed','unclipped_bias_ADU_per_readout',
         'unclipped_effective_RON_ADU_per_readout','global_clipped_bias_ADU_per_readout',
         'global_clipped_effective_RON_ADU_per_readout'],frame_rows)

    summary = {'checkpoint':'LS7U_BLANK_SUPPLEMENT','role':'Exploratory input-mapping follow-up after the fixed primary result',
        'file_key':manifest['file_key'],'input_decision':'NOT_READY_FOR_TARGET_IMAGE_STUDY',
        'protocol_sha256':pid['sha256'],'target_image_bytes':0,
        'virtual_reference_array_bytes':len(body),'retained_header_bytes':len(header),
        'extension':'SCI_RAW_BlankLeft','hdu_index':2,'shape':list(cube.shape),
        'values':int(cube.size),'nexp':NEXP,'native_unit':'ADU',
        'surrogate':'PrimaryHDU; empty HDU 1 with actual native NEXP; original blank extension at HDU 2. No target pixels. Not a full native product or PIPE extraction.',
        'source_functions':identities,'pipe_gain_one_adu':{
            'bias_per_readout':bias,'effective_read_noise_per_readout':ron},
        'global_clipping':{'clip_sigma':3,'iterations':10,'selected':int(mask.sum()),
            'removed':int(len(mask)-mask.sum()),'selected_fraction':float(mask.mean()),
            'mask_sha256':sha(mask.astype(np.uint8).tobytes()),'trace':trace},
        'unclipped_global':{'bias_per_readout_adu':float(np.median(cube)/NEXP),
            'effective_read_noise_per_readout_adu':float(np.std(cube)/math.sqrt(NEXP))},
        'frame_global_clipped_bias_per_readout_adu':stats([r[5] for r in frame_rows]),
        'frame_global_clipped_effective_read_noise_per_readout_adu':stats([r[6] for r in frame_rows]),
        'cal_cor_values_without_native_unit_cards':cal,
        'cal_comparison':{'cal_bias_minus_blank_adu':cal['BIAS']-bias,
            'cal_ron_minus_blank_adu':cal['RON']-ron,
            'cal_bias_to_blank':cal['BIAS']/bias,'cal_ron_to_blank':cal['RON']/ron,
            'bias_within_1_percent':abs(cal['BIAS']/bias-1)<=0.01,
            'ron_within_1_percent':abs(cal['RON']/ron-1)<=0.01},
        'primary_comparison':{'blank_minus_primary_bias_adu':bias-primary['primary']['bias_per_readout_adu'],
            'blank_minus_primary_ron_adu':ron-primary['primary']['effective_read_noise_per_readout_adu']},
        'gain_scaled_original_function':gain_results,
        'audit':{'astropy_vs_struct_values':int(cube.size),
            'scalar_vs_original_mask_comparisons':10*len(mask),
            'scalar_vs_original_bias_absolute_error':abs(bias-scalar_bias),
            'scalar_vs_original_ron_absolute_error':abs(ron-scalar_ron),
            'original_fits_checksum_valid':True,'pinned_source_git_identities_valid':True},
        'native_source_residual_trials':0,'pulse_recovery_trials':0,
        'new_candidates':0,'new_qualified_observing_seconds':0,
        'limitations':['Input choice specified after primary measurement, before blank acquisition.',
            'PIPE input/estimator diagnostic, not DRP 14.1.2 reproduction or physical calibration adoption.',
            'Effective RON assumes independent coadded-readout scaling; clipping changes the estimated distribution.',
            'No spatial bias/flat/dark/PSF/gcoadd contract follows from these electronic values.'],
        'software':{'python':sys.version.split()[0],'numpy':np.__version__,'astropy':astropy.__version__}}
    save_json(out/'summary.json',summary)
    print(json.dumps(summary,indent=2,allow_nan=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=ROOT/'results_ls7u_prescan/blank_reference')
    ap.add_argument('--output',type=Path,default=ROOT/'results_ls7u_prescan/blank_reference')
    args = ap.parse_args()
    assess(args.input,args.output)
