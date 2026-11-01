"""Recompute development detection using direct windows, without importing detector."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
from astropy.io import fits

P = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
cfg = json.loads((P/'code/DETECTOR_CONFIG.json').read_text())
reports = []
for result_path in sorted((P/'development').glob('*/result.json')):
    result = json.loads(result_path.read_text())
    name = result['input']['input_filename']
    paths = list((P/'data/development').glob(name)) + list((P/'access_probe').glob(name))
    assert len(paths) == 1, (name, paths)
    path = paths[0]
    assert path.parent in (P/'data/development',P/'access_probe')
    with fits.open(path, memmap=False) as h:
        w = np.array(h[1].data['WAVE'][0],dtype=float)
        f = np.array(h[1].data['FLUX'][0],dtype=float)
    saved = np.load(result_path.parent/'search_arrays.npz')
    window = cfg['window_pixels']
    half = window//2
    good = np.isfinite(f) & (w>=cfg['wave_min_angstrom']) & (w<=cfg['wave_max_angstrom'])
    if cfg['mask_exact_zero_flux']:
        good &= f!=0
    eligible = np.convolve(good.astype(int),np.ones(window,dtype=int),'valid') == window
    gaps = np.diff(w)>cfg['gap_step_multiple']*np.median(np.diff(w))
    eligible &= np.convolve(gaps.astype(int),np.ones(window-1,dtype=int),'valid') == 0
    centers = np.flatnonzero(eligible)+half
    median = np.full(len(f),np.nan)
    std = np.full(len(f),np.nan)
    for start in range(0,len(centers),2048):
        cc = centers[start:start+2048]
        values = f[cc[:,None]+np.arange(-half,half+1)[None,:]]
        median[cc] = np.median(values,axis=1)
        std[cc] = np.std(values,axis=1,ddof=0)
    searched = np.isfinite(std)&(std>0)
    contrast = np.full(len(f),np.nan)
    contrast[searched] = (f[searched]-median[searched])/std[searched]
    cross = np.flatnonzero(searched&(contrast>=cfg['threshold_local_std']))
    independent_runs = []
    for indices in np.split(cross,np.flatnonzero(np.diff(cross)!=1)+1):
        if not len(indices):continue
        a,b = int(indices[0]),int(indices[-1]+1)
        peak = int(indices[np.argmax(contrast[indices])])
        status = 'SHORT_RUN' if len(indices)<cfg['minimum_run_pixels'] else 'WIDE_RUN' if len(indices)>cfg['maximum_run_pixels'] else 'PRELIMINARY_EMISSION_HIT'
        independent_runs.append([a,b,peak,len(indices),status])
    reported_runs = [[r['start_index'],r['end_index_exclusive'],r['peak_index'],r['run_pixels'],r['status']] for r in result['all_threshold_runs']]
    checks = {
        'input_hash_matches': sha(path)==result['input']['sha256'],
        'config_matches_frozen': result['config']==cfg,
        'saved_wavelength_matches_raw': np.array_equal(saved['wave'],w),
        'saved_flux_matches_raw': np.array_equal(saved['flux'],f,equal_nan=True),
        'searched_mask_exact_match': np.array_equal(saved['searched'],searched),
        'searched_count_matches': int(searched.sum())==result['searched_samples'],
        'median_exact_match_all_searched_windows': np.array_equal(saved['continuum'][searched],median[searched]),
        'scatter_matches_rtol1e_7_atol1e_7': np.allclose(saved['local_std'][searched],std[searched],rtol=1e-7,atol=1e-7),
        'crossing_mask_exact_match': np.array_equal(saved['searched']&(saved['local_contrast']>=cfg['threshold_local_std']),searched&(contrast>=cfg['threshold_local_std'])),
        'all_run_boundaries_peaks_classes_match': independent_runs==reported_runs,
    }
    reports.append({
        'development_name':result_path.parent.name,
        'raw_input':str(path.relative_to(P)),
        'result_sha256':sha(result_path),
        'windows_independently_recomputed':len(centers),
        'all_threshold_runs':len(independent_runs),
        'preliminary_hits':sum(r[-1]=='PRELIMINARY_EMISSION_HIT' for r in independent_runs),
        'max_scatter_absolute_difference_adu':float(np.max(abs(saved['local_std'][searched]-std[searched]))),
        'max_scatter_relative_difference':float(np.max(abs(saved['local_std'][searched]-std[searched])/std[searched])),
        'checks':{k:bool(v) for k,v in checks.items()},
        'status':'PASS' if all(checks.values()) else 'FAIL',
    })

report = {
    'schema':'HARPS_DEVELOPMENT_NUMERICS_INDEPENDENT_REVIEW_V1',
    'reviewed_utc':datetime.now(timezone.utc).isoformat(),
    'status':'PASS' if all(r['status']=='PASS' for r in reports) and len(reports)==3 else 'FAIL',
    'method':'Direct NumPy 101-value median and population standard deviation at every valid development window; independent convolution-based support mask and index-grouping run extraction; detector module is not imported.',
    'development_spectra':reports,
    'main_or_validation_flux_opened':False,
    'scope_limits':['Numerical implementation and saved output are verified on three approved development exposures. This is not validation of astrophysical laser identity, calibrated significance, or completeness.','The descriptive observed FWHM field was not independently reproduced in this audit.'],
    'input_sha256':{str(p.relative_to(P)):sha(p) for p in [P/'code/harps_detector.py',P/'code/DETECTOR_CONFIG.json',P/'code/DETECTOR_FREEZE.json']},
}
(P/'review/DEVELOPMENT_NUMERICAL_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
