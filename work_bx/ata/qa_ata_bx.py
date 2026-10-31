"""Bounded descriptive QA of two pinned ATA visibility subsets; no SETI search.

All baselines, polarizations and channels are retained. No observational arrays
are read at import time. The schema is inspected before reading visibility data.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, math, os, sys, time, traceback, warnings
import numpy as np
import h5py

EXPECTED = {'2148dc7fd9d8f28e095a397a3f82884feaa96927',
            'ca2a9481b00e0e9370d8f67ced9b12837aca191f'}
MAX_CELLS = 1_000_000

def need(condition, message):
    if not condition:
        raise ValueError(message)

def identity(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                git_blob_sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())

def plain(value):
    if isinstance(value, bytes): return value.decode('utf-8')
    if isinstance(value, np.ndarray): return plain(value.tolist())
    if isinstance(value, np.generic): return plain(value.item())
    if isinstance(value, (list, tuple)): return [plain(v) for v in value]
    if isinstance(value, dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value, float) and not math.isfinite(value): return None
    return value

def save_json(path, value):
    with Path(path).open('x') as f:
        json.dump(plain(value), f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())

def header_tree(group):
    result = {}
    for key in group:
        link = group.get(key, getlink=True)
        need(isinstance(link, h5py.HardLink), 'Nonlocal or symbolic HDF5 link forbidden')
        item = group[key]
        if isinstance(item, h5py.Group): result[key] = header_tree(item)
        else:
            need(not item.is_virtual and not item.external, 'External/virtual header storage forbidden')
            need(item.size <= 100_000, 'Header dataset exceeds bound')
            result[key] = plain(item[()])
    return result

def array_header(h, key, size, kind):
    need(key in h, 'Missing header '+key)
    a = np.asarray(h[key]).reshape(-1)
    need(len(a) == size and a.dtype.kind in kind, 'Header shape/type differs: '+key)
    return a

def utc(jd):
    return datetime.fromtimestamp((float(jd)-2440587.5)*86400, timezone.utc).isoformat()

def reduce_profiles(vis, valid, samples, integration, a1, a2, times):
    pairs = sorted(set(zip(a1.tolist(), a2.tolist())))
    shape = (len(pairs), vis.shape[2], vis.shape[1])
    amp = np.full(shape, np.nan); coherence = np.full(shape, np.nan)
    counts = np.zeros(shape, dtype=np.int32); weights = np.zeros(shape)
    records = []; rounding_clips = 0
    for bi, pair in enumerate(pairs):
        rows = np.flatnonzero((a1 == pair[0]) & (a2 == pair[1]))
        need(len(np.unique(times[rows])) == len(rows), 'Duplicate time within ordered baseline')
        for pi in range(vis.shape[2]):
            v = vis[rows,:,pi].astype(np.complex128); good = valid[rows,:,pi]
            w = np.where(good, samples[rows,:,pi], 0).astype(np.float64)*integration[rows,None]
            need(np.isfinite(w).all(), 'Nonfinite effective exposure weight')
            counts[bi,pi] = good.sum(axis=0); weights[bi,pi] = w.sum(axis=0)
            absolute = np.abs(v)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                amp[bi,pi] = np.nanmedian(np.where(good, absolute, np.nan), axis=0)
            safe_v = np.where(good, v, 0); safe_a = np.where(good, absolute, 0)
            numerator = np.abs(np.sum(w*safe_v, axis=0))
            denominator = np.sum(w*safe_a, axis=0)
            supported = (counts[bi,pi] >= 2) & (denominator > 0)
            c = numerator[supported]/denominator[supported]
            need(np.isfinite(c).all() and (c >= 0).all() and (c <= 1+1e-12).all(), 'Invalid coherence')
            rounding_clips += int((c > 1).sum()); coherence[bi,pi,supported] = np.minimum(c,1)
            av = amp[bi,pi][np.isfinite(amp[bi,pi])]; cv = coherence[bi,pi][supported]
            records.append(dict(antenna_1=pair[0],antenna_2=pair[1],kind='auto' if pair[0]==pair[1] else 'cross',
                polarization_index=pi,baseline_time_rows=len(rows),valid_cells=int(good.sum()),
                amplitude_channels=len(av),median_channel_amplitude=float(np.median(av)) if len(av) else None,
                minimum_channel_amplitude=float(av.min()) if len(av) else None,
                maximum_channel_amplitude=float(av.max()) if len(av) else None,
                coherence_channels=len(cv),median_coherence=float(np.median(cv)) if len(cv) else None,
                minimum_coherence=float(cv.min()) if len(cv) else None,maximum_coherence=float(cv.max()) if len(cv) else None))
    return dict(antenna_pairs=np.asarray(pairs,dtype=np.int64),median_amplitude=amp,
                temporal_coherence=coherence,valid_time_count=counts,effective_exposure_seconds=weights), records, rounding_clips

def inspect_and_analyze(path):
    with h5py.File(path, 'r') as f:
        need(set(f) >= {'Header','Data'}, 'UVH5 groups missing')
        for name in ('Header','Data'):
            need(isinstance(f.get(name,getlink=True),h5py.HardLink), 'Root link forbidden')
        h = header_tree(f['Header']); g = f['Data']
        for name in ('visdata','flags','nsamples'):
            need(name in g and isinstance(g.get(name,getlink=True),h5py.HardLink), 'Data link/dataset missing')
            need(not g[name].is_virtual and not g[name].external, 'External/virtual data storage forbidden')
        shapes = [g[name].shape for name in ('visdata','flags','nsamples')]
        need(shapes[0] == shapes[1] == shapes[2], 'Data/flag/sample shapes differ')
        original_shape = shapes[0]
        need(len(original_shape) in (3,4), 'Unsupported visibility rank')
        if len(original_shape) == 4: need(original_shape[1] == 1, 'Legacy SPW axis must be singleton')
        shape = original_shape if len(original_shape)==3 else (original_shape[0],original_shape[2],original_shape[3])
        need(all(0 < n <= MAX_CELLS for n in shape) and math.prod(shape) <= MAX_CELLS, 'Data size exceeds bound')
        nb,nf,npol = shape
        need(all(int(h[k]) == n for k,n in [('Nblts',nb),('Nfreqs',nf),('Npols',npol)]), 'Declared dimensions differ')
        need(g['visdata'].dtype.kind == 'c' and g['visdata'].dtype.itemsize in (8,16), 'Only native complex float visibilities admitted')
        need(g['flags'].dtype.kind == 'b' and g['nsamples'].dtype.kind == 'f', 'Flag/sample dtype differs')
        a1=array_header(h,'ant_1_array',nb,'iu'); a2=array_header(h,'ant_2_array',nb,'iu')
        times=array_header(h,'time_array',nb,'f'); integration=array_header(h,'integration_time',nb,'f')
        freq=array_header(h,'freq_array',nf,'f'); pol=array_header(h,'polarization_array',npol,'iu')
        width=np.asarray(h['channel_width']).reshape(-1)
        need(width.dtype.kind in 'fi' and len(width) in (1,nf), 'Channel width shape/type differs')
        if len(width)==1: width=np.repeat(width,nf)
        need(all(np.isfinite(a).all() for a in (times,integration,freq,width)), 'Nonfinite metadata')
        need((integration>0).all() and (freq>0).all() and (width>0).all(), 'Invalid sampling metadata')
        need(len(set(zip(a1.tolist(),a2.tolist(),times.tolist())))==nb, 'Duplicate ordered baseline/time coordinate')
        need(len(np.unique(freq))==nf and len(np.unique(pol))==npol, 'Duplicate frequency/polarization coordinate')
        need(int(h['Ntimes'])==len(np.unique(times)), 'Declared Ntimes differs')
        need(int(h['Nbls'])==len(set(zip(a1.tolist(),a2.tolist()))), 'Declared Nbls differs')
        need(int(h['Nants_data'])==len(np.unique(np.concatenate([a1,a2]))), 'Declared Nants_data differs')
        antenna_numbers=np.asarray(h['antenna_numbers']).reshape(-1)
        need(len(antenna_numbers)==int(h['Nants_telescope']) and (set(a1)|set(a2))<=set(antenna_numbers), 'Antenna catalogue binding differs')
        need(h.get('telescope_name')=='ATA' and h.get('vis_units')=='uncalib', 'Fixed source/unit metadata differs')
        need(h.get('phase_center_catalog',{}).get('0',{}).get('cat_name')=='3c286' and int(h['Nphase'])==1, 'Fixed phase center differs')
        phase_ids=array_header(h,'phase_center_id_array',nb,'iu');need((phase_ids==0).all(), 'Phase center IDs differ')
        vis=g['visdata'][()]; flags=g['flags'][()]; samples=g['nsamples'][()]
        if len(original_shape)==4: vis,flags,samples=(np.squeeze(a,axis=1) for a in (vis,flags,samples))
    finite_vis=np.isfinite(vis.real)&np.isfinite(vis.imag); finite_samples=np.isfinite(samples)
    valid=(~flags)&finite_vis&finite_samples&(samples>0)
    profiles,groups,clips=reduce_profiles(vis,valid,samples,integration,a1,a2,times)
    profiles.update(frequency_hz=freq,polarization_codes=pol,channel_width_hz=width)
    dates=sorted({utc(t)[:10] for t in times})
    summary=dict(original_storage_shape=list(original_shape),canonical_shape=list(shape),header=h,
        frequency_min_hz=float(freq.min()),frequency_max_hz=float(freq.max()),channel_width_min_hz=float(width.min()),
        channel_width_max_hz=float(width.max()),frequency_axis_order='ascending' if np.all(np.diff(freq)>0) else 'descending' if np.all(np.diff(freq)<0) else 'nonmonotonic',
        time_start_utc=utc(times.min()),time_end_utc=utc(times.max()),observed_utc_dates=dates,
        maintainer_reported_date='2024-12-12',header_dates_match_maintainer_reported_date=dates==['2024-12-12'],
        unique_times=len(np.unique(times)),unique_ordered_baselines=len(profiles['antenna_pairs']),polarization_codes=pol,
        total_cells=vis.size,valid_cells=int(valid.sum()),flagged_cells=int(flags.sum()),
        nonfinite_visibility_cells=int((~finite_vis).sum()),nonfinite_sample_cells=int((~finite_samples).sum()),
        nonpositive_finite_sample_cells=int((finite_samples&(samples<=0)).sum()),invalid_cells=int((~valid).sum()),
        invalid_reason_counts_may_overlap=True,coherence_roundoff_clips=clips,all_baseline_polarization_groups=groups,
        amplitude_units='Stored normalized visibility amplitude; not independently calibrated flux density.')
    matching=dict(times=times,ant1=a1,ant2=a2,pol=pol,integration=integration,freq=freq,
                  source=h.get('phase_center_catalog',h.get('object_name')),telescope=h.get('telescope_name'))
    return summary,profiles,matching

def run(manifest_path,out):
    began=time.monotonic(); source_before=identity(__file__); manifest_before=identity(manifest_path)
    manifest=json.loads(Path(manifest_path).read_text()); inputs=manifest['inputs']
    need(manifest['schema']=='SETI_BX_ATA_INPUTS_V1' and len(inputs)==2, 'Exact two-file ATA manifest required')
    need({r['git_blob_sha'] for r in inputs}==EXPECTED, 'Source blob selection differs')
    before=[]
    for r in inputs:
        p=Path(r['path']);need(p.is_file() and not p.is_symlink() and p.stat().st_size==279504, 'Input path/size differs')
        value=identity(p);need(value['bytes']==r['bytes'] and value['git_blob_sha']==r['git_blob_sha'], 'Git blob identity differs')
        if 'sha256' in r: need(value['sha256']==r['sha256'], 'SHA256 identity differs')
        before.append(value)
    summaries=[]; profiles={}; matching=[]
    for i,r in enumerate(inputs):
        summary,arrays,metadata=inspect_and_analyze(r['path']);summary.update(input_path=r['path'],input_identity=before[i])
        summaries.append(summary);matching.append(metadata)
        profiles.update({f'file{i}_{key}':value for key,value in arrays.items()})
    x,y=matching
    cross={k:bool(np.array_equal(x[k],y[k])) for k in ('times','ant1','ant2','pol','integration')}
    cross.update(source_metadata_equal=x['source']==y['source'],telescope_metadata_equal=x['telescope']==y['telescope'],
        shared_frequency_centers=len(np.intersect1d(x['freq'],y['freq'])),
        frequency_center_ranges_overlap=bool(max(x['freq'].min(),y['freq'].min())<=min(x['freq'].max(),y['freq'].max())))
    cross['same_observation_coordinate_arrays']=all(cross[k] for k in ('times','ant1','ant2','pol','integration'))
    npz=out/'PROFILES_ATA_BX.npz'
    with npz.open('xb') as f:np.savez_compressed(f,**profiles);f.flush();os.fsync(f.fileno())
    after=[identity(r['path']) for r in inputs]
    need(before==after and source_before==identity(__file__) and manifest_before==identity(manifest_path), 'Source/input/manifest changed')
    result=dict(schema='SETI_BX_ATA_DESCRIPTIVE_QA_V1',status='PASS_DESCRIPTIVE_QA',files=summaries,subband_comparison=cross,
        source_identity=source_before,manifest_identity=manifest_before,input_identities_before=before,input_identities_after=after,
        profile_archive=dict(path=str(npz),**identity(npz)),all_channels_analyzed=True,thresholds=None,drift_search=False,
        method='Per ordered baseline/polarization/channel: unweighted temporal median amplitude; exposure-weighted complex coherence with weights nsamples*integration_time, requiring at least two valid distinct times.',
        valid_mask='not flagged AND finite visibility real/imag AND finite positive nsamples; integration times finite and positive by metadata gate',
        coherence_undefined='NaN in NPZ when fewer than two valid times or nonpositive amplitude-weighted denominator; null in JSON aggregates when no defined channels',
        runtime=dict(python=sys.version.split()[0],numpy=np.__version__,h5py=h5py.__version__,hdf5=h5py.version.hdf5_version),
        statistical_significance=None,calibrated_sensitivity=None,SETI_candidate_assessment='NOT_PERFORMED',new_original_SETI_coverage_credit=0,
        interpretation='Two downselected, auto-normalized subbands published as testing data; descriptive observation QA only. No detection threshold, SETI screening, interference-origin identification, or calibrated flux measurement.',
        completed_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-began)
    save_json(out/'SUMMARY_ATA_BX.json',result)
    print(json.dumps(dict(status=result['status'],summary_path=str(out/'SUMMARY_ATA_BX.json'),summary_sha256=identity(out/'SUMMARY_ATA_BX.json')['sha256'],wall_seconds=result['wall_seconds'])),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    try: run(args.manifest,args.out)
    except BaseException as exc:
        save_json(args.out/'FAILURE_ATA_BX.json',dict(status='FAIL',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),no_automatic_retry=True))
        raise
