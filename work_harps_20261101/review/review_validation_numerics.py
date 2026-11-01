"""Independent direct-window audit of all frozen controls and injections."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import numpy as np
from astropy.io import fits
from review_production_numerics import support, stats, extract, compact

P = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = P/'validation/results_frozen_20261101'
plan_path = P/'validation/VALIDATION_PLAN.json'
plan = json.loads(plan_path.read_text())
cfg = json.loads((P/'code/DETECTOR_CONFIG.json').read_text())
receipt = json.loads((out/'RUN_RECEIPT.json').read_text())
summary = json.loads((out/'summary.json').read_text())
controls = json.loads((out/'controls.json').read_text())
trials = json.loads((out/'trials.json').read_text())
assert receipt['status']=='COMPLETED'
assert sha(plan_path)==receipt['plan_sha256']

def direct(arrays, result):
    w,f = arrays['wave'],arrays['flux']
    eligible = support(w,f,cfg)
    centers = np.flatnonzero(eligible)
    med,std,contrast,positive = stats(f,centers,cfg)
    searched = eligible&positive
    events = extract(contrast,searched,cfg)
    cc = {
        'searched_mask_matches':np.array_equal(arrays['searched'],searched),
        'searched_count_matches':int(searched.sum())==result['searched_samples'],
        'median_exact_match':np.array_equal(arrays['continuum'][searched],med[searched]),
        'std_matches':np.allclose(arrays['local_std'][searched],std[searched],rtol=1e-7,atol=1e-7),
        'all_runs_peaks_classes_match':events==[compact(e) for e in result['all_threshold_runs']],
    }
    return cc, events, med,std,contrast,len(centers)

def matches(events,k,status=None):
    return [e for e in events if (status is None or e[-1]==status) and e[0]<=k+2 and e[1]>k-2]

raw = {}
for item in plan['backgrounds_chronological']:
    path = P/item['relative_path']
    assert sha(path)==item['sha256']
    with fits.open(path,memmap=False) as h:
        raw[path.name] = (np.array(h[1].data['WAVE'][0],dtype=float),np.array(h[1].data['FLUX'][0],dtype=float))

control_reports,trial_reports, control_cache = [],[],{}
windows_total = 0
for c in controls:
    assert c['status']=='EVALUATED'
    folder = out/c['geometry_id']
    arrays = np.load(folder/'control_arrays.npz')
    rw,rf = raw[c['background_file']]
    a,b = c['patch_start_index_full_spectrum'],c['patch_end_index_exclusive_full_spectrum']
    cc,events,med,std,contrast,nwindows = direct(arrays,c['detector_result'])
    windows_total += nwindows
    k = c['nearest_center_index_patch']
    unmodified_noise = float(np.std(rf[a+k-50:a+k+51],ddof=0))
    expected_center = float(rw[a+500]+c['subpixel_phase']*np.median(np.diff(rw[a:b])))
    control_hit = bool(matches(events,k,'PRELIMINARY_EMISSION_HIT'))
    cc.update(
        wave_matches_raw=np.array_equal(arrays['wave'],rw[a:b]),
        flux_matches_raw=np.array_equal(arrays['flux'],rf[a:b]),
        noise_matches_unmodified_window=unmodified_noise==c['unmodified_local_population_std_adu'],
        center_matches_registered_phase=expected_center==c['center_angstrom'],
        center_index_lower_half_pixel_tie=k==500,
        control_hit_matches=control_hit==c['control_hit'],
    )
    control_cache[c['geometry_id']] = (arrays['wave'],arrays['flux'],unmodified_noise,expected_center,k,control_hit)
    control_reports.append({'geometry_id':c['geometry_id'],'control_hit':control_hit,'checks':{key:bool(v) for key,v in cc.items()},'status':'PASS' if all(cc.values()) else 'FAIL'})

for t in trials:
    assert t['status']=='EVALUATED'
    amplitude = t['amplitude_factor']
    arrays = np.load(out/t['geometry_id']/f'injection_{amplitude:02d}_arrays.npz')
    w,f,noise,center,k,control_hit = control_cache[t['geometry_id']]
    gaussian_sigma = (center/plan['resolving_power'])/np.sqrt(8*np.log(2))
    expected_addition = amplitude*noise*np.exp(-((w-center)/gaussian_sigma)**2/2)
    cc,events,med,std,contrast,nwindows = direct(arrays,t['detector_result'])
    windows_total += nwindows
    hit = bool(matches(events,k,'PRELIMINARY_EMISSION_HIT'))
    local_runs = matches(events,k)
    cc.update(
        wave_matches_control=np.array_equal(arrays['wave'],w),
        gaussian_addition_matches=np.allclose(arrays['added_flux'],expected_addition,rtol=1e-13,atol=1e-10),
        injected_flux_is_original_plus_independent_addition=np.allclose(arrays['flux'],f+expected_addition,rtol=1e-13,atol=1e-10),
        continuous_peak_matches=t['continuous_peak_added_adu']==amplitude*noise,
        sampled_peak_matches=bool(np.isclose(t['sampled_peak_added_adu'],expected_addition.max(),rtol=1e-13,atol=1e-10)),
        recovered_matches=hit==t['recovered'],
        control_flag_matches=control_hit==t['control_hit'],
        recovered_without_control_matches=(hit and not control_hit)==t['recovered_without_control_hit'],
    )
    trial_reports.append({
        'geometry_id':t['geometry_id'],'anchor_angstrom':t['anchor_angstrom'],'phase':t['subpixel_phase'],
        'amplitude_factor':amplitude,'recovered':hit,'near_center_runs':local_runs,
        'outcome_reason':'ACCEPTED_RUN' if hit else 'SHORT_RUN_ONLY' if local_runs and all(e[-1]=='SHORT_RUN' for e in local_runs) else 'NO_NEAR_CENTER_CROSSING' if not local_runs else 'OTHER',
        'injected_fwhm_pixels':t['injected_fwhm_pixels'],
        'center_scatter_over_unmodified_noise':float(std[k]/noise),
        'maximum_center_plusminus2_contrast':float(np.max(contrast[k-2:k+3])),
        'checks':{key:bool(v) for key,v in cc.items()},'status':'PASS' if all(cc.values()) else 'FAIL',
    })

by_amplitude = []
for amplitude in plan['amplitude_factors']:
    rr = [r for r in trial_reports if r['amplitude_factor']==amplitude]
    by_amplitude.append({'amplitude_factor':amplitude,'evaluated':len(rr),'recovered':sum(r['recovered'] for r in rr),'outcome_reasons':dict(Counter(r['outcome_reason'] for r in rr)),'center_scatter_over_unmodified_noise_min':min(r['center_scatter_over_unmodified_noise'] for r in rr),'center_scatter_over_unmodified_noise_max':max(r['center_scatter_over_unmodified_noise'] for r in rr)})
strongest = [r for r in trial_reports if r['amplitude_factor']==32]
strongest_missed = [r for r in strongest if not r['recovered']]
checks = {
    'plan_and_frozen_source_hashes_match':sha(plan_path)==receipt['plan_sha256'] and all(sha(P/relative)==expected for relative,expected in plan['source_sha256'].items()),
    'all_12_controls_reproduced':len(control_reports)==12 and all(c['status']=='PASS' for c in control_reports),
    'all_48_injections_reproduced':len(trial_reports)==48 and all(t['status']=='PASS' for t in trial_reports),
    'reported_control_hits_match':sum(c['control_hit'] for c in control_reports)==summary['control_hits'],
    'reported_recovery_total_matches':sum(t['recovered'] for t in trial_reports)==summary['recovered_trials'],
    'reported_per_amplitude_recoveries_match':all(r['recovered']==next(s['recovered'] for s in summary['by_amplitude'] if s['amplitude_factor']==r['amplitude_factor']) for r in by_amplitude),
    'six_strongest_misses_are_three_pixel_short_runs':len(strongest_missed)==6 and all(len(r['near_center_runs'])==1 and r['near_center_runs'][0][3]==3 and r['near_center_runs'][0][-1]=='SHORT_RUN' for r in strongest_missed),
}
report = {
    'schema':'HARPS_VALIDATION_NUMERICS_INDEPENDENT_REVIEW_V1','reviewed_utc':datetime.now(timezone.utc).isoformat(),
    'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
    'directly_recomputed_windows':windows_total,'control_hits':sum(c['control_hit'] for c in control_reports),
    'recovered_trials':sum(t['recovered'] for t in trial_reports),'registered_trials':48,'by_amplitude':by_amplitude,
    'strongest_recovery_by_phase_and_background':[{'phase':phase,'evaluated':sum(r['phase']==phase for r in strongest),'recovered':sum(r['phase']==phase and r['recovered'] for r in strongest)} for phase in [0,.25,.5]],
    'findings':[
        'All six missed 32-times injections produce a three-pixel threshold run at the injected center and fail the frozen minimum-four-pixel criterion; no injection was lost by a numerical or indexing mismatch.',
        'The injection width spans 3.57 to 5.66 pixels FWHM, but the detector counts only consecutive pixels above its moving threshold, not FWHM pixels. These widths are not interchangeable.',
        'The Gaussian is included in the detector local standard deviation. At high amplitude this raises the threshold along with the signal and limits the width above threshold; amplitude factor relative to original scatter is not final detector significance.',
        'At the strongest level, recovery is 0/4 for the phase-0 background, 2/4 for phase-0.25, and 4/4 for phase-0.5. Background and phase are confounded, so this does not isolate a phase-only effect.',
        'These results demonstrate a real sensitivity limitation of the frozen filter on this restricted set; they do not justify tuning this completed run or claiming general completeness.'
    ],
    'input_sha256':{str(p.relative_to(P)):sha(p) for p in [plan_path,out/'RUN_RECEIPT.json',out/'summary.json',P/'review/review_production_numerics.py']},
    'controls':control_reports,'trials':trial_reports,
}
(P/'review/VALIDATION_NUMERICAL_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','checks','directly_recomputed_windows','control_hits','recovered_trials','by_amplitude','strongest_recovery_by_phase_and_background']},indent=2))
