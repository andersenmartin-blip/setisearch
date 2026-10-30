#!/usr/bin/env python3
"""Freeze metadata-only parameters, execute six independent searches, follow hits."""
from __future__ import annotations
import argparse, concurrent.futures as cf, csv, datetime, hashlib, json, math, os, time
from pathlib import Path
import numpy as np
from search_pilot import DEFAULTS, VERSION, drift_grid, normalize, oracle_sum, centered_boxcar, sha256, write_json, search_array, physical_injection

BASE=Path(__file__).resolve().parent

def source_digest():
    return {p.name:sha256(p) for p in sorted(BASE.glob('*.py'))}

def freeze(archive,out):
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((archive/'pilot_manifest.json').read_text())
    scopes=[]
    for m in manifest['scans']:
        h=m['sigproc']; nr=m['ntime']; nc=m.get('slice_shape',[nr,m['channel_stop_exclusive']-m['channel_start']])[1]
        df=h['foff']*1e6; dt=h['tsamp']; rates=drift_grid(nr,dt,df,DEFAULTS['max_abs_drift_hz_s'])
        halo=max(DEFAULTS['boundary_halo_channels'],int(np.max(np.abs(np.rint(rates[:,None]*(np.arange(nr)-(nr-1)/2)*dt/df))))+max(DEFAULTS['widths_channels'])//2)
        scopes.append(dict(scan=m['scan'],role=m['role'],target=h['source_name'],
                           source_url=m['archive']['url'],array_file=m['array_file'],input_sha256=m['array_sha256'],
                           nrows=nr,nchannels=nc,dt_seconds=dt,df_hz=df,fch1_mhz=m['fch1_slice_mhz'],
                           tstart_mjd=h['tstart'],tref_midpoint_mjd=h['tstart']+nr*dt/(2*86400),
                           midpoint_core_frequency_min_mhz=m['fch1_slice_mhz']+(nc-halo-1)*df/1e6,
                           midpoint_core_frequency_max_mhz=m['fch1_slice_mhz']+halo*df/1e6,
                           core_bandwidth_hz=(nc-2*halo)*abs(df),halo_channels=halo,
                           drift_trials=len(rates),drift_step_hz_s=float(rates[1]-rates[0])))
    record=dict(version=VERSION,frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                selection_power_inspection='No sample powers were loaded by this pipeline before this freeze. Metadata-only archive source/scope selected separately.',
                source_code_sha256=source_digest(),manifest_sha256=sha256(archive/'pilot_manifest.json'),
                configuration=DEFAULTS,scans=scopes,
                score='For each row/4096-channel block normalize raw powers by spectral median and 1.4826 MAD. For each drift and width sum normalized powers on nearest-channel midpoint-centered track, then ESS=(sum−median of sums over the fixed core frequency grid))/(1.4826 MAD of those sums).',
                rounding='numpy.rint, nearest channel; exact half-integer ties to even',
                qualification='Exploratory engineering baseline, not identical to turboSETI and no Gaussian FAP. OFF narrow forced-track and broad envelope diagnostics are separate; unrelated envelope hits do not automatically reject.',
                planned_controls=dict(real_noise_injection_rates=[0,.15,1,4],amplitudes=[5,15,45],phases=[.125,.5,.875],
                                     real_noise_width_checks=[3,9],real_noise_width_amplitude=45,
                                     real_noise_selected_scan=0,real_noise_control_halo_channels=512,real_noise_crop_rule='centered 8192 native channels of the prospectively selected band',
                                     synthetic_seed=20261017,control_scope='engineering pilot only; no general sensitivity completeness or FAP claim'),
                pointing_condition='Nominal source labels do not establish identical sky pointing. Cadence repeat/source qualification requires archive/header coordinate gate.')
    write_json(out/'parameters_frozen.json',record)
    print(json.dumps(dict(frozen_at_utc=record['frozen_at_utc'],source_code_sha256=record['source_code_sha256'],scans=len(scopes),core_bandwidth_hz=scopes[0]['core_bandwidth_hz'])))

def worker(task):
    archive_s,out_s,scope,config=task
    archive,out=Path(archive_s),Path(out_s)
    p=archive/scope['array_file']
    if sha256(p)!=scope['input_sha256']: raise ValueError('Input digest mismatch')
    raw=np.load(p,mmap_mode='r',allow_pickle=False)
    if tuple(raw.shape)!=(scope['nrows'],scope['nchannels']): raise ValueError('Input shape mismatch')
    prefix=out/f"scan{scope['scan']}"
    result,*_=search_array(raw,scope['dt_seconds'],scope['df_hz'],config,prefix)
    result['scope']=scope; result['input_sha256']=sha256(p)
    for h in result['hits']+result['diagnostics']:
        h['frequency_at_midpoint_mhz']=scope['fch1_mhz']+h['channel_at_midpoint']*scope['df_hz']/1e6
        h['zero_or_near_zero_drift']=abs(h['drift_hz_s'])<=scope['drift_step_hz_s']
    write_json(str(prefix)+'_results.json',result)
    return {k:result[k] for k in ['scope','track_trials','core_bandwidth_hz','local_hits_count','saved_local_hits','hit_overflow','completion_status','wall_seconds','cpu_seconds','peak_rss_kib','width_searches']}

def independent_candidates(archive,out,record):
    # Machine coverage follows every saved ON hit; human examples are separate.
    from all_on_followup import independent_candidates as follow_all_on
    return follow_all_on(archive,out,record)

def real_noise_injections(archive,out,record):
    s=record['scans'][0]; config=record['configuration']; rawall=np.load(archive/s['array_file'],mmap_mode='r')
    n=min(8192,rawall.shape[1]); lo=(rawall.shape[1]-n)//2
    raw=np.array(rawall[:,lo:lo+n]); nr,nc=raw.shape
    _,nrms=normalize(raw,config['bandpass_block_channels'])
    block=(nc//2)//config['bandpass_block_channels']; scale=float(np.median(nrms[block]['mad_scale']))
    # Fixed strong/weak cases quantify a tiny, declared engineering matrix only.
    cases=[]; phases=[.125,.5,.875]
    controlconfig={**config,'boundary_halo_channels':512}
    baseline,base_y,base_cal,_,base_rates=search_array(raw,s['dt_seconds'],s['df_hz'],controlconfig,save_hits=True)
    def known_region_max(y,cal,rates,mid,rate):
        best=None; times=(np.arange(nr)-(nr-1)/2)*s['dt_seconds']
        for w,stride in zip(config['widths_channels'],config['frequency_strides']):
            yy=centered_boxcar(y,w)
            first=512+int(math.ceil((mid-33-512)/stride))*stride
            centers=np.arange(first,int(mid+33)+1,stride,dtype=int)
            for ri in np.flatnonzero(np.abs(rates-rate)<=.35):
                offsets=np.rint(rates[ri]*times/s['df_hz']).astype(int)
                # A vectorized indexing oracle is independent of slice accumulation.
                sums=yy[np.arange(nr)[:,None],centers[None,:]+offsets[:,None]].sum(axis=0,dtype=np.float64)
                med,sc=cal[str(w)][ri]; scores=(sums-med)/sc
                k=int(np.argmax(scores))
                if best is None or scores[k]>best['ess']:
                    best=dict(ess=float(scores[k]),channel_at_midpoint=int(centers[k]),drift_hz_s=float(rates[ri]),width_channels=w)
        return best
    specs=[(r,a,1,phases[(ri+ai)%3]) for ri,r in enumerate([0,.15,1,4]) for ai,a in enumerate([5,15,45])]
    specs += [(1,45,3,.25),(4,45,9,.75)]
    for rate,amp,width,phase in specs:
        mid=nc//2+phase
        signal=physical_injection(raw.shape,s['dt_seconds'],s['df_hz'],mid,rate,amp*scale,width)
        result,inj_y,inj_cal,_,inj_rates=search_array(raw+signal,s['dt_seconds'],s['df_hz'],controlconfig,save_hits=True)
        # Score the known injection's allowed frequency/drift neighborhood;
        # an unrelated maximum elsewhere does not count as a recovery.
        matches=[h for h in result['hits']+result['diagnostics'] if abs(h['channel_at_midpoint']-mid)<=33 and abs(h['drift_hz_s']-rate)<=.35]
        best=max(matches,key=lambda h:h['ess']) if matches else None
        before=known_region_max(base_y,base_cal,base_rates,mid,rate)
        after=known_region_max(inj_y,inj_cal,inj_rates,mid,rate)
        delta=after['ess']-before['ess']
        introduced=bool(best and best['ess']>=config['threshold_ess'] and delta>=3)
        cases.append(dict(rate_hz_s=rate,total_power_per_row_in_local_single_bin_mad_units=amp,
                          intrinsic_width_channels=width,subchannel_phase=phase,
                          recovered_above_operational_threshold=bool(best and best['ess']>=config['threshold_ess']),hit_overflow=result['hit_overflow'],best_diagnostic=best,
                          paired_uninjected_region_max=before,paired_injected_region_max=after,paired_region_delta_ess=delta,
                          newly_recovered_above_threshold_with_delta_at_least_3=introduced))
    report=dict(scan=s['scan'],source_crop_channel_start=lo,crop_shape=list(raw.shape),
                raw_local_scale=scale,normalization_recomputed_for_each_injection=True,
                cases=cases,n_cases=len(cases),recovered_count=sum(x['recovered_above_operational_threshold'] for x in cases),
                newly_recovered_with_delta_at_least_3_count=sum(x['newly_recovered_above_threshold_with_delta_at_least_3'] for x in cases),
                limitations='Small engineering matrix in one fixed observed-noise crop. The complete above-threshold local maximum hit list is matched to each known injected track, with paired uninjected ESS to identify preexisting RFI coincidences; delta>=3 is descriptive only; no calibrated recovery probability, flux density or campaign sensitivity claim. No astronomical false-alarm probability implied.')
    write_json(out/'real_noise_injection_controls.json',report)
    return {k:report[k] for k in ['n_cases','recovered_count','newly_recovered_with_delta_at_least_3_count','crop_shape','limitations']}

def run(archive,out,workers):
    start=time.perf_counter(); record=json.loads((out/'parameters_frozen.json').read_text())
    if record['source_code_sha256']!=source_digest(): raise ValueError('Source changed after parameter/code freeze')
    if record['manifest_sha256']!=sha256(archive/'pilot_manifest.json'): raise ValueError('Manifest changed after freeze')
    summaries=[]
    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        tasks=[(str(archive),str(out),s,record['configuration']) for s in record['scans']]
        for r in ex.map(worker,tasks):
            summaries.append(r); print(json.dumps(dict(scan=r['scope']['scan'],cpu_seconds=r['cpu_seconds'],wall_seconds=r['wall_seconds'],hits=r['local_hits_count'],overflow=r['hit_overflow'])),flush=True)
    follow=independent_candidates(archive,out,record)
    injections=real_noise_injections(archive,out,record)
    on=[s for s in summaries if s['scope']['role']=='ON']
    report=dict(version=VERSION,scan_summaries=summaries,n_scans=len(summaries),n_on_scans=len(on),
                unique_cadence_bandwidth_hz=min(s['core_bandwidth_hz'] for s in summaries),
                on_scan_bandwidth_sum_hz=sum(s['core_bandwidth_hz'] for s in on),
                total_track_trials=sum(s['track_trials'] for s in summaries),
                total_search_cpu_seconds=sum(s['cpu_seconds'] for s in summaries),
                total_search_worker_wall_seconds=sum(s['wall_seconds'] for s in summaries),
                end_to_end_wall_seconds=time.perf_counter()-start,workers=workers,
                hit_overflow=any(s['hit_overflow'] for s in summaries),candidate_followup=follow,
                observed_noise_injections=injections,
                scientific_conclusion='Finite-grid exploratory pilot only; full science qualification depends on pointing, validation and RFI controls. Counts are diagnostic trial evaluations, not independent experiments or sky-origin detections.')
    write_json(out/'pilot_summary.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='scan_summaries'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=3)
    a=p.parse_args()
    if a.action=='freeze': freeze(a.archive.resolve(),a.out.resolve())
    else: run(a.archive.resolve(),a.out.resolve(),a.workers)
