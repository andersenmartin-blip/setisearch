"""Bounded descriptive S2017 search with full-native AC normalization.

The local-q ESS calibration is a deliberately new descriptive family, not
identical to historical full-native ESS. Imports perform no data I/O/network.
A frozen metadata/source plan is required before native power decoding.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
import signal
import struct
import sys
import time

for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'work_be/runtime'))
import numpy as np
import h5py
import bitshuffle
ENGINE=BASE/'work_be/science_root/work_az/detector'
sys.path.insert(0,str(ENGINE))
import kernel_v as kernel
import continuous_normalization_ac as normalizer
WIDTHS=(1,3,9,33)
STRIDES=(1,1,2,8)


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())


def utc():return datetime.now(timezone.utc).isoformat()


def save_npz(path,arrays):
    path=Path(path)
    require(all(not np.asarray(v).dtype.hasobject for v in arrays.values()),'Object arrays forbidden')
    with path.open('xb') as stream:np.savez_compressed(stream,**arrays);stream.flush();os.fsync(stream.fileno())
    return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':sha(path)}


def load_npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}


def validate_plan(plan,planpath=None):
    require(plan['schema']=='S2017_BH_LOCAL_Q_ESS_V1','Wrong scope schema')
    require(plan['native_channel_start']==179306496 and plan['native_channel_count']==1048576,'Wrong native geometry')
    require(plan['core_width_channels']==4096 and plan['core_q_list']==list(range(9,17)),'q9..16 fixed prospectively')
    require(plan['support_halo_channels']==4096 and plan['bandpass_block_channels']==4096,'Wrong halo/anchor geometry')
    require(plan['widths_channels']==list(WIDTHS) and plan['strides']==list(STRIDES),'Width/stride family differs')
    require(plan['max_abs_drift_hz_s']==4 and plan['threshold_ess']==10 and plan['off_flag_threshold_ess']==5,'Frozen thresholds differ')
    require(plan['calibration_domain']=='Each selected4096channelqcore at its own fixedstride, independently for each scan,width,drift','Local ESS calibration must be explicit')
    require(plan['previously_exposed_data'] is True and plan['new_independent_observation'] is False,'No fresh-data relabeling')
    require(sha(plan['dataset_manifest_path'])==plan['dataset_manifest_sha256'],'Authenticated input/header manifest differs')
    scans=plan['scans'];require(len(scans)==6 and [s['scan'] for s in scans]==list(range(6)),'Ordered six-scan cadence required')
    require([s['role'] for s in scans]==['ON','OFF']*3,'Alternating ON/OFF required')
    for s in scans:
        require(s['dt_seconds']==18.253611008 and s['df_hz']==-2.7939677238464355,'Time/frequency sampling differs')
        require(s['fch1_mhz']==2301.85546875,'Native first-channel frequency differs')
        require(sha(s['path'])==s['input_sha256'],'Compact HDF5 file differs')
    for path,digest in plan['source_sha256'].items():require(sha(path)==digest,'Source bytes differ: '+path)
    require(sha(__file__)==plan['source_sha256'][str(Path(__file__).resolve())],'Wrapper source must be pinned')
    require((np.__version__,h5py.__version__,bitshuffle.__version__)==('2.3.5','3.16.0','0.5.2'),'Pinned runtime differs')
    rates=drift_rates(plan);span=max(s['tref_midpoint_mjd'] for s in scans)-min(s['tref_midpoint_mjd'] for s in scans)
    maxshift=math.ceil(4*(span*86400+15*18.253611008/2)/abs(scans[0]['df_hz']))+16
    radius=math.ceil(1+.5*(rates[1]-rates[0])*span*86400/abs(scans[0]['df_hz']))
    require(maxshift+radius<4096,'Frozen support halo insufficient for all six scans')
    return plan


def drift_rates(plan):
    s=plan['scans'][0];nside=math.ceil(4*16*s['dt_seconds']/abs(s['df_hz']))
    return np.linspace(-4,4,2*nside+1,dtype=np.float64)


def prepare(plan,planpath,out):
    validate_plan(plan,planpath)
    out=Path(out);require(not (out/'NORMALIZED_INPUTS_COMPLETE.json').exists(),'No normalization rerun')
    out.mkdir(parents=True,exist_ok=True)
    lo=max(0,min(plan['core_q_list'])*4096-4096)
    hi=min(1048576,(max(plan['core_q_list'])+1)*4096+4096)
    records=[]
    for s in plan['scans']:
        raw=np.empty((16,1048576),dtype='<f4');rowhash=[]
        with h5py.File(s['path'],'r') as h5:
            d=h5['data'];require(d.shape==(16,1,1048576) and d.chunks==(1,1,1048576) and d.dtype==np.dtype('<f4'),'Full native compact shape/chunks/dtype differ')
            require(int(d.attrs['original_source_frequency_chunk_origin'])==plan['native_channel_start'],'Compact native origin differs')
            cp=d.id.get_create_plist();require([cp.get_filter(i)[0] for i in range(cp.get_nfilters())]==[32008],'Expected bitshuffle-only compact filter')
            for t in range(16):
                mask,payload=d.id.read_direct_chunk((t,0,0));require(mask==0,'Unexpected filter mask')
                nbytes,blockbytes=struct.unpack('>QI',payload[:12]);require(nbytes==4194304 and blockbytes>0 and blockbytes%4==0,'Raw codec header differs')
                values=bitshuffle.decompress_lz4(np.frombuffer(payload[12:],dtype=np.uint8),(1048576,),np.dtype('<f4'),block_size=blockbytes//4)
                require(np.isfinite(values).all() and (values>=0).all(),'Invalid decoded native powers')
                raw[t]=values;rowhash.append(hashlib.sha256(values.tobytes()).hexdigest())
        normalized,anchors=normalizer.normalize(raw,4096);del raw
        crop=normalized[:,lo:hi].copy();del normalized
        npypath=out/f'scan{s["scan"]}_normalized_support.npy'
        with npypath.open('xb') as stream:np.save(stream,crop,allow_pickle=False);stream.flush();os.fsync(stream.fileno())
        ap=save_npz(out/f'scan{s["scan"]}_fullnative_anchor_audit.npz',anchors)
        records.append({'scan':s['scan'],'input_sha256':s['input_sha256'],'normalized_support_path':str(npypath.resolve()),'normalized_support_sha256':sha(npypath),'support_start':lo,'support_stop':hi,'full_native_row_sha256':rowhash,'anchor_audit':ap})
        print(json.dumps({'event':'NORMALIZED_FULL_NATIVE_SCAN','scan':s['scan'],'rows':16,'support':[lo,hi]}),flush=True)
    validate_plan(plan,planpath)
    result={'schema':'S2017_BH_NORMALIZED_INPUTS_V1','status':'PASS','completed_utc':utc(),'plan_sha256':sha(planpath),'normalization_version':normalizer.VERSION,'full_native_channel_count':1048576,'scans':records,'archive_requests':0}
    write(out/'NORMALIZED_INPUTS_COMPLETE.json',result)
    return result


def normalized_inputs(plan,planpath,out):
    record=read(Path(out)/'NORMALIZED_INPUTS_COMPLETE.json');require(record['plan_sha256']==sha(planpath),'Normalization plan binding differs')
    for s in record['scans']:
        require(sha(s['normalized_support_path'])==s['normalized_support_sha256'],'Normalized support changed')
        a=s['anchor_audit'];require(sha(a['path'])==a['sha256'],'Fullnative anchor audit changed')
    return record


def local_maximum(score,size):
    h=size//2;pad=np.pad(score,(h,h),mode='edge')
    return np.lib.stride_tricks.sliding_window_view(pad,size).max(axis=1)


def search_scan(y,scope,plan,support_start,q,progress=None):
    rates=drift_rates(plan);times=(np.arange(16,dtype=np.float64)-7.5)*scope['dt_seconds']
    offsets=np.rint(rates[:,None]*times[None,:]/scope['df_hz']).astype(np.int32)
    start=q*4096-support_start;stop=(q+1)*4096-support_start
    grid={'drift_hz_s':rates,'offsets':offsets};catalog={k:[] for k in ('channel_at_midpoint','drift_index','width_channels','ess','drift_hz_s','frequency_at_midpoint_mhz')}
    audits={};summaries=[];hitcount=0
    for width,stride in zip(WIDTHS,STRIDES):
        prepared=kernel.boxcars(y,width);centers=np.arange(start,stop,stride,dtype=np.int32)
        best=np.full(len(centers),-np.inf,dtype=np.float64);best_ri=np.zeros(len(centers),dtype=np.int32)
        calibration=np.empty((len(rates),2),dtype=np.float64);samples=np.array([0,len(centers)//2,len(centers)-1])
        sample_sums=np.empty((3,3),dtype=np.float64);sample_ris=[0,len(rates)//2,len(rates)-1]
        trial_hits=0;fallbacks=0
        for ri,(rate,off) in enumerate(zip(rates,offsets)):
            sums,fallback,bound=kernel.tracks_grid(y,prepared,off,start,stop,stride,width)
            med=float(np.median(sums));scale=float(1.4826*np.median(np.abs(sums-med)))
            require(math.isfinite(scale) and scale>0,'Invalid local-q track MAD')
            score=(sums-np.float64(med))/np.float64(scale)
            require(np.isfinite(score).all(),'Nonfinite local ESS')
            calibration[ri]=[med,scale];better=score>best;best[better]=score[better];best_ri[better]=ri
            inds=np.flatnonzero((score>=10)&(score==local_maximum(score,max(3,2*math.ceil(width/stride)+1))))
            hitcount+=len(inds);trial_hits+=len(inds);fallbacks+=fallback
            require(hitcount<=1000000,'Finite1millionhit cap reached; incomplete search')
            absolute_centers=centers[inds]+support_start
            for key,value in [('channel_at_midpoint',absolute_centers),('drift_index',np.full(len(inds),ri,dtype=np.int32)),('width_channels',np.full(len(inds),width,dtype=np.int16)),('ess',score[inds]),('drift_hz_s',np.full(len(inds),rate)),('frequency_at_midpoint_mhz',scope['fch1_mhz']+absolute_centers*scope['df_hz']/1e6)]:catalog[key].append(value.copy())
            if ri in sample_ris:sample_sums[sample_ris.index(ri)]=sums[samples]
        grid[f'calibration_width_{width}']=calibration;grid[f'max_ess_width_{width}']=best;grid[f'max_drift_index_width_{width}']=best_ri;grid[f'centers_width_{width}']=centers+support_start
        audits[f'scalar_ris_width_{width}']=np.array(sample_ris,dtype=np.int32);audits[f'scalar_centers_width_{width}']=centers[samples]+support_start;audits[f'scalar_sums_width_{width}']=sample_sums
        summaries.append({'width_channels':width,'stride':stride,'centers':len(centers),'drift_trials':len(rates),'track_trials':len(centers)*len(rates),'catalog_local_hits':trial_hits,'maximum_local_ess':float(best.max()),'fallback_points':fallbacks})
        if progress:progress(width,trial_hits)
    columns={k:np.concatenate(v) for k,v in catalog.items()}
    return grid,audits,columns,{'scan':scope['scan'],'role':scope['role'],'q':q,'complete':True,'local_hits':hitcount,'track_trials':sum(s['track_trials'] for s in summaries),'width_searches':summaries}


def search_q(plan,planpath,out,q):
    validate_plan(plan,planpath);require(q in plan['core_q_list'],'q outside frozen list')
    out=Path(out);record=normalized_inputs(plan,planpath,out);dest=out/f'q{q:03d}';require(not dest.exists(),'No search rerun or overwrite');dest.mkdir()
    summaries=[]
    for s,r in zip(plan['scans'],record['scans']):
        y=np.load(r['normalized_support_path'],mmap_mode='r',allow_pickle=False)
        grid,audit,catalog,summary=search_scan(y,s,plan,r['support_start'],q,progress=lambda w,n:print(json.dumps({'event':'SEARCH_WIDTH_COMPLETE','q':q,'scan':s['scan'],'width':w,'hits':n}),flush=True))
        publications=[]
        for name,arrays in [('grid',grid),('audit',audit),('catalog',catalog)]:publications.append(save_npz(dest/f'scan{s["scan"]}_{name}.npz',arrays))
        summary['publications']=publications;write(dest/f'scan{s["scan"]}_summary.json',summary);summaries.append(summary)
    result={'schema':'S2017_BH_LOCAL_Q_SEARCH_RESULT_V1','status':'SIX_SCAN_DETECTOR_COMPLETE_TRIAGE_PENDING','q':q,'completed_utc':utc(),'plan_sha256':sha(planpath),'scans':summaries,'track_trials':sum(s['track_trials'] for s in summaries),'archive_requests':0,'new_observation':False,'calibrated_FAP':False,'candidate_assessment':None}
    write(dest/'SIX_SCAN_SEARCH_COMPLETE.json',result);return result


def triage_q(plan,planpath,out,q):
    validate_plan(plan,planpath);out=Path(out);record=normalized_inputs(plan,planpath,out);dest=out/f'q{q:03d}'
    search=read(dest/'SIX_SCAN_SEARCH_COMPLETE.json');require(search['plan_sha256']==sha(planpath),'Search plan binding differs')
    for s in search['scans']:
        for pub in s['publications']:require(sha(pub['path'])==pub['sha256'],'Search artifact changed')
    pieces=[]
    for j in (0,2,4):
        c=load_npz(dest/f'scan{j}_catalog.npz');c['source_scan']=np.full(len(c['ess']),j,dtype=np.int8);pieces.append(c)
    seeds={k:np.concatenate([c[k] for c in pieces]) for k in pieces[0]};n=len(seeds['ess'])
    require(n<=3000000,'ONseed cap exceeded')
    center_scores=np.full((n,6),np.nan);max_scores=np.full((n,6),np.nan);valid=np.zeros((n,6),dtype=np.bool_);predicted=np.zeros((n,6),dtype=np.int32)
    for s,r in zip(plan['scans'],record['scans']):
        j=s['scan'];y=np.load(r['normalized_support_path'],mmap_mode='r',allow_pickle=False);grid=load_npz(dest/f'scan{j}_grid.npz');rates=grid['drift_hz_s']
        gaps=np.array([(s['tref_midpoint_mjd']-src['tref_midpoint_mjd'])*86400 for src in plan['scans']])[seeds['source_scan']]
        freq=seeds['frequency_at_midpoint_mhz']+seeds['drift_hz_s']*gaps/1e6
        centers=np.rint((freq-s['fch1_mhz'])*1e6/s['df_hz']).astype(np.int32)-r['support_start'];predicted[:,j]=centers+r['support_start']
        radii=np.ceil(1+.5*(rates[1]-rates[0])*np.abs(gaps)/abs(s['df_hz'])).astype(np.int64)
        for width in WIDTHS:
            prep=kernel.boxcars(y,width)
            for ri in np.unique(seeds['drift_index'][seeds['width_channels']==width]):
                rows=np.flatnonzero((seeds['width_channels']==width)&(seeds['drift_index']==ri));off=grid['offsets'][ri]
                for radius in np.unique(radii[rows]):
                    selected=rows[radii[rows]==radius];c=centers[selected]
                    supported=(c+int(off.min())-width//2-radius>=0)&(c+int(off.max())+width//2+radius<y.shape[1]);selected=selected[supported];c=c[supported]
                    if not len(selected):continue
                    req=(c[:,None]+np.arange(-int(radius),int(radius)+1)[None,:]).ravel();unique,inverse=np.unique(req,return_inverse=True)
                    sums=kernel.tracks_selected(y,prep,off,unique,width)[0];med,scale=grid[f'calibration_width_{width}'][ri]
                    scores=((sums-med)/scale)[inverse].reshape(len(selected),2*int(radius)+1)
                    center_scores[selected,j]=scores[:,int(radius)];max_scores[selected,j]=scores.max(axis=1);valid[selected,j]=True
        print(json.dumps({'event':'FORCED_ON_OFF_COMPLETE','q':q,'destination':j,'seeds':n,'measured':int(valid[:,j].sum())}),flush=True)
    if n:
        source=center_scores[np.arange(n),seeds['source_scan']];err=np.abs(source-seeds['ess']);require(np.isfinite(source).all() and (err==0).all(),'Source forced ESS differs from search catalog')
    else:err=np.zeros(0,dtype=np.float64)
    off_flag=(max_scores[:,[1,3,5]]>=5).any(axis=1);full=valid.all(axis=1);on3=(center_scores[:,[0,2,4]]>=10).all(axis=1)
    passing=np.flatnonzero(full&on3&~off_flag)
    arrays={'seed_'+k:v for k,v in seeds.items()};arrays.update(forced_center_local_ess=center_scores,forced_neighborhood_max_local_ess=max_scores,forced_valid=valid,predicted_native_center=predicted,any_OFF_ge5=off_flag,all3ON_ge10_noOFF=full&on3&~off_flag,source_ess_error=err)
    publication=save_npz(dest/'ALL_ON_FORCED_TRIAGE.npz',arrays)
    result={'schema':'S2017_BH_LOCAL_Q_TRIAGE_RESULT_V1','status':'BOUNDED_DESCRIPTIVE_SEARCH_COMPLETE','q':q,'completed_utc':utc(),'plan_sha256':sha(planpath),'ON_local_catalog_rows':n,'forced_measurement_slots':n*6,'supported_slots':int(valid.sum()),'unsupported_slots':int((~valid).sum()),'any_OFF_ge5_rows':int(off_flag.sum()),'all3ON_ge10_noOFF_rows':len(passing),'maximum_source_ess_error':float(err.max(initial=0)),'triage_publication':publication,'search_track_trials':search['track_trials'],'candidate_assessment':'No discovery/origin qualification; passing rows are descriptive flags only','new_unique_archive_ids':0,'new_independent_observations':0,'calibrated_FAP':False,'calibrated_astronomical_sensitivity':False,'archive_requests':0}
    write(dest/'TRIAGE_RESULT.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--q',type=int)
    p.add_argument('--triage',action='store_true');p.add_argument('--all-q',action='store_true')
    args=p.parse_args();plan=read(args.plan);start=time.perf_counter()
    require(sys.flags.optimize==0,'Inherited numerical assertions require unoptimized Python')
    def deadline(signum,frame):raise TimeoutError('BH600second wallclock signal budget')
    signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,600)
    try:
        if args.all_q:
            require(args.q is None and not args.prepare and not args.triage,'All-q is a separate complete mode')
            if not (args.out/'NORMALIZED_INPUTS_COMPLETE.json').exists():prepare(plan,args.plan,args.out)
            else:normalized_inputs(plan,args.plan,args.out)
            results=[]
            for q in plan['core_q_list']:
                search_q(plan,args.plan,args.out,q)
                results.append(triage_q(plan,args.plan,args.out,q))
            result={'schema':'S2017_BH_ALL_FROZEN_Q_RESULT_V1','status':'ALL_EIGHT_BOUNDED_Q_SEARCHES_AND_TRIAGE_COMPLETE',
                    'plan_sha256':sha(args.plan),'completed_utc':utc(),'q_list':plan['core_q_list'],
                    'q_results':results,'total_track_trials':sum(r['search_track_trials'] for r in results),
                    'archive_requests':0,'new_independent_observations':0,'calibrated_FAP':False}
            write(args.out/'ALL_FROZEN_Q_COMPLETE.json',result)
        elif args.prepare:
            require(args.q is None and not args.triage,'Preparation must be separate')
            result=prepare(plan,args.plan,args.out)
        elif args.triage:
            require(args.q is not None,'Choose frozen q');result=triage_q(plan,args.plan,args.out,args.q)
        else:
            require(args.q is not None,'Choose frozen q');result=search_q(plan,args.plan,args.out,args.q)
        print(json.dumps({'status':result['status'],'wall_seconds':time.perf_counter()-start,'q':args.q}),flush=True)
    finally:signal.setitimer(signal.ITIMER_REAL,0)

if __name__=='__main__':main()
