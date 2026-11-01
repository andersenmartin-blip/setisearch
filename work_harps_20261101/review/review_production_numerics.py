"""Bounded, predeclared independent numerical audit after the production run."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv
import hashlib
import json
import numpy as np
from astropy.io import fits

P = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
SAMPLE_ROWS = [0, 24, 49, 74, 99]

def read_csv(path):
    return list(csv.DictReader(path.open()))

def support(w, f, cfg):
    window = cfg['window_pixels']
    half = window//2
    good = np.isfinite(f)&(w>=cfg['wave_min_angstrom'])&(w<=cfg['wave_max_angstrom'])
    if cfg['mask_exact_zero_flux']:good &= f!=0
    valid = np.convolve(good.astype(int),np.ones(window,dtype=int),'valid')==window
    gaps = np.diff(w)>cfg['gap_step_multiple']*np.median(np.diff(w))
    valid &= np.convolve(gaps.astype(int),np.ones(window-1,dtype=int),'valid')==0
    out = np.zeros(len(w),dtype=bool)
    out[half:len(w)-half] = valid
    return out

def stats(f, centers, cfg):
    half = cfg['window_pixels']//2
    med, std = np.full(len(f),np.nan),np.full(len(f),np.nan)
    for start in range(0,len(centers),2048):
        cc = centers[start:start+2048]
        values = f[cc[:,None]+np.arange(-half,half+1)[None,:]]
        med[cc],std[cc] = np.median(values,axis=1),np.std(values,axis=1,ddof=0)
    contrast = np.full(len(f),np.nan)
    positive = np.isfinite(std)&(std>0)
    contrast[positive] = (f[positive]-med[positive])/std[positive]
    return med,std,contrast,positive

def classify(size,cfg):
    return 'SHORT_RUN' if size<cfg['minimum_run_pixels'] else 'WIDE_RUN' if size>cfg['maximum_run_pixels'] else 'PRELIMINARY_EMISSION_HIT'

def extract(contrast, searched,cfg):
    cross = np.flatnonzero(searched&(contrast>=cfg['threshold_local_std']))
    out = []
    for indices in np.split(cross,np.flatnonzero(np.diff(cross)!=1)+1):
        if not len(indices):continue
        a,b = int(indices[0]),int(indices[-1]+1)
        peak = int(indices[np.argmax(contrast[indices])])
        out.append([a,b,peak,len(indices),classify(len(indices),cfg)])
    return out

def compact(event):
    return [event['start_index'],event['end_index_exclusive'],event['peak_index'],event['run_pixels'],event['status']]

def main():
    prod = P/'production'
    # Root explicitly authorized opening main arrays only after this file exists.
    if not (prod/'RUN_SUMMARY.json').is_file():
        raise RuntimeError('Production summary does not yet exist; main flux remains unopened.')
    scope_path = P/'review/PRODUCTION_REVIEW_SCOPE.json'
    scope = json.loads(scope_path.read_text())
    assert sha(Path(__file__))==scope['review_code_sha256'], 'Audit script changed after scope freeze'
    assert scope['zero_based_main_csv_rows']==SAMPLE_ROWS
    selected = read_csv(P/'selection/MAIN100.csv')
    cfg = json.loads((P/'code/DETECTOR_CONFIG.json').read_text())
    freeze = json.loads((P/'code/DETECTOR_FREEZE.json').read_text())
    summary = json.loads((prod/'RUN_SUMMARY.json').read_text())
    allresults = {r['dp_id']:json.loads((prod/'spectra'/(r['dp_id'].replace(':','_')+'.json')).read_text()) for r in selected}
    full_ids = {selected[i]['dp_id'] for i in SAMPLE_ROWS}
    checks = {
        '100_results_present_and_completed':len(allresults)==100 and all(r.get('run_status')=='COMPLETED' for r in allresults.values()),
        'summary_completed_100':summary['status']=='COMPLETED' and summary['exposure_status_counts']=={'COMPLETED':100},
        'frozen_detector_unchanged':sha(P/'code/harps_detector.py')==freeze['source_hashes']['harps_detector.py'],
        'frozen_config_unchanged':sha(P/'code/DETECTOR_CONFIG.json')==freeze['source_hashes']['DETECTOR_CONFIG.json'],
        'all_result_configs_match':all(r['config']==cfg for r in allresults.values()),
        'reported_searched_samples_sum_matches':sum(r['searched_samples'] for r in allresults.values())==summary['searched_samples'],
        'reported_searched_width_sum_matches':np.isclose(sum(r['sum_searched_bin_widths_angstrom'] for r in allresults.values()),summary['sum_searched_bin_widths_angstrom'],rtol=1e-12),
    }
    rows = []
    status_counts = Counter()
    for s in selected:
        r = allresults[s['dp_id']]
        for event in r['all_threshold_runs']:
            rows.append((s['canonical_target'],s['dp_id'],event['start_index'],event['end_index_exclusive'],event['status']))
            status_counts[event['status']]+=1
    csvrows = [(r['canonical_target'],r['dp_id'],int(r['start_index']),int(r['end_index_exclusive']),r['status']) for r in read_csv(prod/'ALL_THRESHOLD_RUNS.csv')]
    checks['all_threshold_csv_matches_individual_results'] = rows==csvrows
    checks['threshold_status_totals_match'] = dict(status_counts)==summary['threshold_run_status_counts']
    exposure_csv = read_csv(prod/'EXPOSURE_SUMMARY.csv')
    target_csv = read_csv(prod/'TARGET_SUMMARY.csv')
    checks['exposure_summary_ids_and_counts_match'] = len(exposure_csv)==100 and {r['dp_id'] for r in exposure_csv}==set(allresults) and all(r['status']=='COMPLETED' and int(r['searched_samples'])==allresults[r['dp_id']]['searched_samples'] and int(r['preliminary_hit_count'])==allresults[r['dp_id']]['preliminary_hit_count'] for r in exposure_csv)
    checks['target_summary_counts_match'] = len(target_csv)==20 and all(int(r['completed_exposures'])==5 and int(r['failed_exposures'])==0 for r in target_csv) and sum(int(r['searched_samples']) for r in target_csv)==summary['searched_samples'] and sum(int(r['preliminary_hit_count']) for r in target_csv)==status_counts['PRELIMINARY_EMISSION_HIT']
    full_reports, hit_reports, opened = [],[],[]
    for s in selected:
        r = allresults[s['dp_id']]
        hits = [e for e in r['all_threshold_runs'] if e['status']=='PRELIMINARY_EMISSION_HIT']
        if s['dp_id'] not in full_ids and not hits:continue
        path = P/'data/main'/(s['dp_id'].replace(':','_')+'.fits')
        with fits.open(path,memmap=False) as h:
            w = np.array(h[1].data['WAVE'][0],dtype=float)
            f = np.array(h[1].data['FLUX'][0],dtype=float)
        opened.append(s['dp_id'])
        assert sha(path)==r['input']['sha256'], 'Input/result checksum mismatch'
        eligible = support(w,f,cfg)
        if s['dp_id'] in full_ids:
            centers = np.flatnonzero(eligible)
        else:
            requested = sorted(set(i for e in hits for i in range(max(0,e['start_index']-1),min(len(f),e['end_index_exclusive']+1))))
            centers = np.array([i for i in requested if eligible[i]],dtype=int)
        med,std,contrast,positive = stats(f,centers,cfg)
        searched = eligible&positive
        if s['dp_id'] in full_ids:
            computed = extract(contrast,searched,cfg)
            these_checks = {
                'searched_samples_match':int(searched.sum())==r['searched_samples'],
                'searched_intervals_match':all(bool(searched[i])==any(z['first_index']<=i<z['last_index_exclusive'] for z in r['searched_intervals']) for i in range(len(w))),
                'all_runs_peaks_classes_match':computed==[compact(e) for e in r['all_threshold_runs']],
            }
            full_reports.append({'dp_id':s['dp_id'],'target':s['canonical_target'],'windows_recomputed':len(centers),'checks':these_checks,'status':'PASS' if all(these_checks.values()) else 'FAIL'})
        for e in hits:
            a,b,k = e['start_index'],e['end_index_exclusive'],e['peak_index']
            crossing = searched&(contrast>=cfg['threshold_local_std'])
            hc = {
                'all_run_centers_cross_threshold':bool(np.all(crossing[a:b])),
                'adjacent_centers_below_or_excluded':bool((a==0 or not crossing[a-1]) and (b==len(f) or not crossing[b])),
                'peak_index_matches':int(a+np.argmax(contrast[a:b]))==k,
                'run_class_matches':classify(b-a,cfg)==e['status'] and b-a==e['run_pixels'],
                'peak_wavelength_matches':float(w[k])==e['wave_peak_angstrom'],
                'peak_median_matches':float(med[k])==e['continuum_adu'],
                'peak_scatter_matches':bool(np.isclose(std[k],e['local_std_adu'],rtol=1e-7,atol=1e-7)),
                'peak_contrast_matches':bool(np.isclose(contrast[k],e['peak_local_contrast'],rtol=1e-7,atol=1e-7)),
            }
            hit_reports.append({'dp_id':s['dp_id'],'target':s['canonical_target'],'start_index':a,'end_index_exclusive':b,'wave_peak_angstrom':e['wave_peak_angstrom'],'checks':hc,'status':'PASS' if all(hc.values()) else 'FAIL'})
    checks['five_predeclared_full_recomputations_pass'] = len(full_reports)==5 and all(x['status']=='PASS' for x in full_reports)
    checks['all_preliminary_hit_windows_reproduced'] = len(hit_reports)==status_counts['PRELIMINARY_EMISSION_HIT'] and all(x['status']=='PASS' for x in hit_reports)
    report = {
        'schema':'HARPS_PRODUCTION_NUMERICS_INDEPENDENT_REVIEW_V1','reviewed_utc':datetime.now(timezone.utc).isoformat(),
        'status':'PASS' if all(checks.values()) else 'FAIL','checks':{k:bool(v) for k,v in checks.items()},
        'scope_sha256':sha(scope_path),'production_summary_sha256':sha(prod/'RUN_SUMMARY.json'),
        'threshold_status_counts':dict(status_counts),'full_recomputations':full_reports,'preliminary_hit_window_reviews':hit_reports,
        'main_flux_arrays_opened_for_ids':opened,'validation_flux_arrays_opened':False,
        'scope_limits':['Only the five predeclared exposures have an independent complete search; remaining exposures receive aggregate-output checks and reported preliminary-hit window checks.','Agreement validates arithmetic and run reporting, not laser identity, calibrated significance or completeness. Descriptive FWHM values were not independently reproduced.'],
    }
    (P/'review/PRODUCTION_NUMERICAL_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','checks','threshold_status_counts']},indent=2))

if __name__=='__main__':main()
