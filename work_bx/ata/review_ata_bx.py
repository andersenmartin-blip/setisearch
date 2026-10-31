"""Independent all-cell scalar audit of ATA QA, run only after production closes.

No production numerical module is imported. HDF5 decoding and NumPy storage
remain shared dependencies; masks, amplitudes and aggregations are recomputed.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, hashlib, json, math, signal, statistics, time
import numpy as np
import h5py

def need(ok,message):
    if not ok:raise ValueError(message)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def plain(v):
    if isinstance(v,bytes):return v.decode('utf-8')
    if isinstance(v,np.generic):return plain(v.item())
    if isinstance(v,np.ndarray):return plain(v.tolist())
    if isinstance(v,list):return [plain(x) for x in v]
    if isinstance(v,float) and not math.isfinite(v):return None
    return v

def flat_header(d,prefix=''):
    out={}
    for k,v in d.items():
        name=prefix+k
        if isinstance(v,dict):out.update(flat_header(v,name+'/'))
        else:out[name]=v
    return out

def close(actual,expected,label):
    if expected is None:need(actual is None,label+' must be null');return
    need(actual is not None and math.isclose(float(actual),float(expected),rel_tol=1e-12,abs_tol=1e-14),label+' differs')

def calculate(vis,flags,samples,a1,a2,times,integration):
    rows={}
    for r,(x,y,t) in enumerate(zip(a1,a2,times)):
        pair=(int(x),int(y));rows.setdefault(pair,[]).append(r)
    pairs=sorted(rows);shape=(len(pairs),vis.shape[2],vis.shape[1])
    amps=np.full(shape,np.nan);coh=np.full(shape,np.nan);counts=np.zeros(shape,np.int32);exposure=np.zeros(shape)
    reasons=dict(total_cells=vis.size,valid_cells=0,flagged_cells=0,nonfinite_visibility_cells=0,nonfinite_sample_cells=0,nonpositive_finite_sample_cells=0,invalid_cells=0)
    groups=[]
    for bi,pair in enumerate(pairs):
        rr=rows[pair];need(len({float(times[r]) for r in rr})==len(rr),'Duplicate baseline/time')
        for pi in range(vis.shape[2]):
            for ch in range(vis.shape[1]):
                vals=[];weights=[];reals=[];imags=[]
                for r in rr:
                    real=float(vis[r,ch,pi].real);imag=float(vis[r,ch,pi].imag);sample=float(samples[r,ch,pi])
                    flag=bool(flags[r,ch,pi]);fv=math.isfinite(real) and math.isfinite(imag);fs=math.isfinite(sample)
                    good=(not flag) and fv and fs and sample>0
                    reasons['flagged_cells']+=flag;reasons['nonfinite_visibility_cells']+=not fv
                    reasons['nonfinite_sample_cells']+=not fs;reasons['nonpositive_finite_sample_cells']+=fs and sample<=0
                    reasons['valid_cells']+=good;reasons['invalid_cells']+=not good
                    if good:
                        vals.append(math.hypot(real,imag));weights.append(sample*float(integration[r]));reals.append(real);imags.append(imag)
                counts[bi,pi,ch]=len(vals);exposure[bi,pi,ch]=math.fsum(weights)
                if vals:amps[bi,pi,ch]=statistics.median(vals)
                denominator=math.fsum(w*a for w,a in zip(weights,vals))
                if len(vals)>=2 and denominator>0:
                    numerator=math.hypot(math.fsum(w*v for w,v in zip(weights,reals)),math.fsum(w*v for w,v in zip(weights,imags)))
                    coh[bi,pi,ch]=min(1.,numerator/denominator)
            av=[float(x) for x in amps[bi,pi] if math.isfinite(float(x))];cv=[float(x) for x in coh[bi,pi] if math.isfinite(float(x))]
            groups.append(dict(antenna_1=pair[0],antenna_2=pair[1],kind='auto' if pair[0]==pair[1] else 'cross',polarization_index=pi,
                baseline_time_rows=len(rr),valid_cells=int(sum(counts[bi,pi])),amplitude_channels=len(av),
                median_channel_amplitude=statistics.median(av) if av else None,minimum_channel_amplitude=min(av) if av else None,maximum_channel_amplitude=max(av) if av else None,
                coherence_channels=len(cv),median_coherence=statistics.median(cv) if cv else None,minimum_coherence=min(cv) if cv else None,maximum_coherence=max(cv) if cv else None))
    return dict(antenna_pairs=np.asarray(pairs,np.int64),median_amplitude=amps,temporal_coherence=coh,valid_time_count=counts,effective_exposure_seconds=exposure),reasons,groups

def inspect_original(path):
    with h5py.File(path,'r') as f:
        header={}
        f['Header'].visititems(lambda name,node:header.update({name:plain(node[()])}) if isinstance(node,h5py.Dataset) else None)
        g=f['Data'];vis=g['visdata'][()];flags=g['flags'][()];samples=g['nsamples'][()]
    if vis.ndim==4:
        need(vis.shape[1]==1,'Legacy SPW must be singleton');vis=vis[:,0];flags=flags[:,0];samples=samples[:,0]
    need(vis.shape==flags.shape==samples.shape==(406,16,4),'Pinned sample geometry differs')
    a1=header['ant_1_array'];a2=header['ant_2_array'];times=header['time_array'];integration=header['integration_time']
    need(all(math.isfinite(float(t)) for t in times) and all(math.isfinite(float(t)) and t>0 for t in integration),'Invalid time metadata')
    need(len(set(times))==header['Ntimes']==1 and len(set(zip(a1,a2)))==header['Nbls']==406,'Count metadata differs')
    profiles,reasons,groups=calculate(vis,flags,samples,a1,a2,times,integration)
    profiles.update(frequency_hz=np.asarray(header['freq_array']).reshape(-1),polarization_codes=np.asarray(header['polarization_array']).reshape(-1),channel_width_hz=np.asarray(header['channel_width']).reshape(-1))
    return header,profiles,reasons,groups

def run(manifest_path,results):
    began=time.monotonic();summary_path=results/'SUMMARY_ATA_BX.json';profile_path=results/'PROFILES_ATA_BX.npz'
    manifest=json.loads(manifest_path.read_text());summary=json.loads(summary_path.read_text())
    production_source=Path(__file__).with_name('qa_ata_bx.py')
    bound=[Path(__file__),production_source,manifest_path,summary_path,profile_path]+[Path(s['path']) for s in manifest['inputs']]
    before={str(p):sha(p) for p in bound}
    need(summary['status']=='PASS_DESCRIPTIVE_QA' and len(summary['files'])==len(manifest['inputs'])==2,'Production not closed correctly')
    need(summary['profile_archive']['sha256']==before[str(profile_path)],'Profile archive identity differs')
    need(summary['source_identity']['sha256']==before[str(production_source)] and summary['manifest_identity']['sha256']==before[str(manifest_path)],'Production source/manifest binding differs')
    need(summary['runtime']['numpy']==np.__version__ and summary['runtime']['h5py']==h5py.__version__ and summary['runtime']['hdf5']==h5py.version.hdf5_version,'Shared decoder runtime differs')
    need(summary['thresholds'] is None and summary['drift_search'] is False and summary['statistical_significance'] is None,'Scientific scope expanded')
    need(summary['SETI_candidate_assessment']=='NOT_PERFORMED' and summary['new_original_SETI_coverage_credit']==0,'SETI credit was added')
    audits=[];headers=[];expected_keys=set();cells=0;max_error=0.;groups_checked=0
    with np.load(profile_path,allow_pickle=False) as saved:
        for i,(pin,record) in enumerate(zip(manifest['inputs'],summary['files'])):
            p=Path(pin['path']);raw=p.read_bytes()
            ident=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob_sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
            need(all(ident[k]==pin[k] for k in ident),'Original input identity differs')
            need(record['input_identity']==summary['input_identities_before'][i]==summary['input_identities_after'][i]==ident,'Production input binding differs')
            header,profiles,counts,groups=inspect_original(p);headers.append(header);cells+=counts['total_cells'];groups_checked+=len(groups)
            need(flat_header(record['header'])==header,'Original header reconstruction differs')
            need(record['canonical_shape']==[406,16,4] and record['unique_times']==1 and record['unique_ordered_baselines']==406,'Shape/count summary differs')
            for key,value in counts.items():need(record[key]==value,'All-cell count differs: '+key)
            need(record['invalid_reason_counts_may_overlap'] is True,'Invalid-reason overlap must be explicit')
            for key,value in profiles.items():
                name=f'file{i}_{key}';expected_keys.add(name);actual=saved[name]
                need(actual.shape==value.shape,'Profile geometry differs: '+name)
                if value.dtype.kind in 'iu':need(np.array_equal(actual,value),'Profile exact values differ: '+name)
                else:
                    need(np.array_equal(np.isnan(actual),np.isnan(value)),'NaN eligibility differs: '+name)
                    finite=np.isfinite(value);need(np.isfinite(actual[finite]).all(),'Nonfinite profile: '+name)
                    if finite.any():
                        err=float(np.max(np.abs(actual[finite]-value[finite])));max_error=max(max_error,err)
                        need(np.allclose(actual[finite],value[finite],rtol=1e-12,atol=1e-14),'Scalar profiles differ: '+name)
            need(np.isnan(saved[f'file{i}_temporal_coherence']).all(),'One integration cannot establish temporal coherence')
            need(len(record['all_baseline_polarization_groups'])==len(groups),'Group count differs')
            for actual,expected in zip(record['all_baseline_polarization_groups'],groups):
                need(set(actual)==set(expected),'Group fields differ')
                for key,value in expected.items():
                    if value is None or isinstance(value,float):close(actual[key],value,'Group '+key)
                    else:need(actual[key]==value,'Group metadata/count differs: '+key)
            jd=float(header['time_array'][0]);converted=datetime(1858,11,17,tzinfo=timezone.utc)+timedelta(days=jd-2400000.5)
            need(record['observed_utc_dates']==[converted.date().isoformat()],'Header calendar date differs')
            for key in ('time_start_utc','time_end_utc'):
                need(abs((datetime.fromisoformat(record[key])-converted).total_seconds())<.001,'Header time differs')
            need(record['maintainer_reported_date']=='2024-12-12' and record['header_dates_match_maintainer_reported_date'] is False,'Source date discrepancy hidden')
            audits.append(dict(file=i,input_sha256=ident['sha256'],all_cells_checked=counts['total_cells'],counts=counts,
                baseline_polarization_groups_checked=len(groups),all_temporal_coherence_undefined=True,
                header_jd=jd,header_mjd=jd-2400000.5,independent_header_time_utc=converted.isoformat(),source_date_discrepancy_preserved=True))
        need(set(saved.files)==expected_keys,'Extra/missing profile arrays')
    x,y=headers;cross=summary['subband_comparison']
    for key,headerkey in [('times','time_array'),('ant1','ant_1_array'),('ant2','ant_2_array'),('pol','polarization_array'),('integration','integration_time')]:
        need(cross[key] is (x[headerkey]==y[headerkey]),'Cross-subband coordinate comparison differs')
    need(cross['same_observation_coordinate_arrays'] and cross['shared_frequency_centers']==len(set(x['freq_array'])&set(y['freq_array']))==0,'Subband provenance/frequency comparison differs')
    need(not cross['frequency_center_ranges_overlap'],'Subband frequency ranges unexpectedly overlap')
    need(before=={str(p):sha(p) for p in bound},'Reviewer source/inputs/results changed')
    return dict(schema='SETI_BX_ATA_INDEPENDENT_ALL_CELL_REVIEW_V1',status='PASS_INDEPENDENT_ALL_CELL_QA',
        summary_sha256=before[str(summary_path)],profiles_sha256=before[str(profile_path)],reviewer_sha256=sha(__file__),
        manifest_sha256=before[str(manifest_path)],all_original_visibility_cells_checked=cells,
        all_baseline_polarization_groups_checked=groups_checked,maximum_profile_absolute_error=max_error,
        relative_tolerance=1e-12,absolute_tolerance=1e-14,files=audits,all_bound_bytes_unchanged=True,
        powers_or_candidates_searched=False,new_original_SETI_coverage_credit=0,calibrated_sensitivity=None,
        limits=['Shared h5py HDF5 decoder and NumPy storage; scalar masking and reductions independent.',
                'One stored time per baseline: temporal coherence is undefined.',
                'Header time indicates 2024-12-03; maintainer README says 2024-12-12. Discrepancy remains unresolved.',
                'Descriptive QA of downselected normalized visibilities, not SETI candidate evaluation.'],
        wall_seconds=time.monotonic()-began)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--profiles',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    need(args.summary.name=='SUMMARY_ATA_BX.json' and args.profiles.name=='PROFILES_ATA_BX.npz' and args.summary.parent==args.profiles.parent,'Review requires paired production outputs')
    args.out.mkdir(parents=True,exist_ok=False)
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Independent review exceeded60seconds')));signal.alarm(60)
    value=run(args.manifest,args.summary.parent);target=args.out/'REVIEW_ATA_BX.json'
    with target.open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    signal.alarm(0);print(json.dumps(dict(status=value['status'],all_cells=value['all_original_visibility_cells_checked'],maximum_profile_absolute_error=value['maximum_profile_absolute_error'],review_sha256=sha(target))))
