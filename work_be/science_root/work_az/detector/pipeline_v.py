"""Full saved-native grid and destination-serial triage; no acquisition paths."""
from pathlib import Path
import ast,gc,hashlib,json,math,resource,time
import numpy as np
from scipy.ndimage import maximum_filter1d
from kernel_v import VERSION,boxcars,tracks_grid,tracks_selected
from source.broad_context_original_s import broad_envelope_max

WIDTHS=(1,3,9,33);STRIDES=(1,1,2,8);REPLAY_RI=(0,279,559,838)
BASE=Path(__file__).resolve().parent

def normalize(raw,block=4096):
    from continuous_normalization_ac import normalize as continuous
    return continuous(raw,block)

def drift_grid(nrows,dt,df,maxdrift):
    nside=math.ceil(maxdrift*nrows*dt/abs(df))
    return np.linspace(-maxdrift,maxdrift,2*nside+1,dtype=np.float64)

def max_update(best,best_index,score,ri):
    if best.dtype!=np.float64 or score.dtype!=np.float64:raise ValueError('Float64 score/max state required')
    better=score>best;best[better]=score[better];best_index[better]=ri

def search(raw,scope,config,progress=None):
    started=time.perf_counter();y,norm=normalize(raw,config['bandpass_block_channels']);nr,nc=y.shape
    rates=drift_grid(nr,scope['dt_seconds'],scope['df_hz'],config['max_abs_drift_hz_s'])
    times=(np.arange(nr,dtype=np.float64)-(nr-1)/2)*scope['dt_seconds']
    offsets=np.rint(rates[:,None]*times[None,:]/scope['df_hz']).astype(np.int32)
    minimum_halo=int(np.abs(offsets).max())+max(WIDTHS)//2
    halo=max(config['boundary_halo_channels'],minimum_halo);start,stop=halo,nc-halo
    if stop<=start:raise ValueError('No native core')
    grid={'drift_hz_s':rates,'offsets':offsets};audit=dict(norm);catalog={k:[] for k in ['channel_at_midpoint','drift_index','width_channels','ess','raw_sum','drift_hz_s','frequency_at_midpoint_mhz']}
    count=0;overflow=False;width_summaries=[];strict=[];top=[]
    design=json.loads((BASE/'source/QA_DESIGN_ORIGINAL_S.json').read_text())
    reference=config['scans'][0];gap=(scope['tref_midpoint_mjd']-reference['tref_midpoint_mjd'])*86400
    for wi,(width,stride) in enumerate(zip(WIDTHS,STRIDES)):
        begin=time.perf_counter();prepared=boxcars(y,width);centers=np.arange(start,stop,stride,dtype=np.int32)
        indices=np.linspace(0,len(centers)-1,8,dtype=np.int64);sample_centers=centers[indices]
        best=np.full(len(centers),-np.inf,dtype=np.float64);best_index=np.zeros(len(centers),dtype=np.int32)
        cal=np.empty((len(rates),2),dtype=np.float64);stats=np.empty((len(rates),6),dtype=np.float64)
        audit_sums=np.empty((len(rates),8),dtype=np.float64);audit_scores=np.empty_like(audit_sums)
        counts=np.zeros((len(rates),3),dtype=np.int64);width_top=[]
        for ri,(rate,off) in enumerate(zip(rates,offsets)):
            sums,fallback,maxbound=tracks_grid(y,prepared,off,start,stop,stride,width)
            med=float(np.median(sums));scale=float(1.4826*np.median(np.abs(sums-med)))
            if not math.isfinite(scale) or scale<=0:raise ValueError('Invalid full-grid track MAD')
            score=(sums-np.float64(med))/np.float64(scale)
            if score.dtype!=np.float64 or not np.isfinite(score).all():raise ValueError('Invalid float64 ESS grid')
            cal[ri]=[med,scale];max_update(best,best_index,score,ri)
            local=maximum_filter1d(score,size=max(3,2*math.ceil(width/stride)+1),mode='nearest')
            inds=np.flatnonzero((score>=config['threshold_ess'])&(score==local))
            exceed=int(np.count_nonzero(score>=config['threshold_ess']));counts[ri]=[exceed,len(inds),fallback]
            peak=int(np.argmax(score));width_top.append((float(score[peak]),int(centers[peak]),ri))
            stats[ri]=[float(sums.min()),float(sums.max()),float(score[peak]),int(centers[peak]),maxbound,prepared[2]]
            audit_sums[ri]=sums[indices];audit_scores[ri]=score[indices]
            if ri==config['replay_drift_indices'][wi]:audit[f'complete_sum_vector_width_{width}']=sums.copy()
            room=max(0,config['maximum_saved_local_hits']-count);keep=inds[:room];overflow|=len(inds)>room;count+=len(keep)
            catalog['channel_at_midpoint'].append(centers[keep].copy());catalog['drift_index'].append(np.full(len(keep),ri,dtype=np.int32));catalog['width_channels'].append(np.full(len(keep),width,dtype=np.int16))
            catalog['ess'].append(score[keep].copy());catalog['raw_sum'].append(sums[keep].copy());catalog['drift_hz_s'].append(np.full(len(keep),rate,dtype=np.float64));catalog['frequency_at_midpoint_mhz'].append(scope['fch1_mhz']+centers[keep]*scope['df_hz']/1e6)
            if progress and (ri%100==0 or ri==len(rates)-1):progress(width,ri,len(rates),time.perf_counter()-begin,count)
        for ti,t in enumerate(design['templates'] if config['run_original_QA_templates'] else []):
            if t['width_channels']!=width:continue
            ri=int(np.argmin(np.abs(rates-t['drift_fraction']*config['max_abs_drift_hz_s'])))
            frequency=reference['fch1_mhz']+t['source_center']*reference['df_hz']/1e6+rates[ri]*gap/1e6
            center=int(np.rint((frequency-scope['fch1_mhz'])*1e6/scope['df_hz']))
            got=float(tracks_selected(y,prepared,offsets[ri],np.array([center],dtype=np.int32),width)[0][0])
            h=width//2;expected=math.fsum(float(y[row,center+int(off)+j]) for row,off in enumerate(offsets[ri]) for j in range(-h,h+1))
            strict.append(dict(scan=scope['scan'],original_template_index=ti,width_channels=width,drift_index=ri,native_center=center,candidate_sum=got,explicit_fsum=expected,absolute_error=abs(got-expected),strict_5e_5_pass=abs(got-expected)<5e-5))
        grid[f'max_ess_width_{width}']=best;grid[f'max_drift_index_width_{width}']=best_index;grid[f'calibration_width_{width}']=cal
        audit[f'fixed_center_indices_width_{width}']=indices;audit[f'fixed_centers_width_{width}']=sample_centers;audit[f'fixed_sums_width_{width}']=audit_sums;audit[f'fixed_scores_width_{width}']=audit_scores
        audit[f'per_drift_counts_width_{width}']=counts;audit[f'per_drift_statistics_width_{width}']=stats
        top.extend(dict(width_channels=width,ess=s,channel_at_midpoint=c,drift_index=ri,drift_hz_s=float(rates[ri])) for s,c,ri in sorted(width_top,reverse=True)[:config['top_diagnostics_per_width']])
        width_summaries.append(dict(width_channels=width,stride=stride,frequency_centers=len(centers),drift_trials=len(rates),track_trials=len(centers)*len(rates),grid_exceedances=int(counts[:,0].sum()),local_hits=int(counts[:,1].sum()),fallback_points=int(counts[:,2].sum()),maximum_ess=float(best.max()),wall_seconds=time.perf_counter()-begin,global_bound=prepared[2],pointwise_magnitude_matrix_used=prepared[1] is not None))
        del prepared,centers,best,best_index,cal,stats,local,sums,score;gc.collect()
    columns={k:np.concatenate(v) for k,v in catalog.items()}
    if any(a.dtype.hasobject for a in columns.values()):raise ValueError('Object catalog forbidden')
    summary=dict(version=VERSION,scan=scope['scan'],role=scope['role'],input_sha256=scope['input_sha256'],nrows=nr,nchannels=nc,core_start=start,core_stop=stop,minimum_halo=minimum_halo,halo=halo,drift_count=len(rates),track_trials=sum(s['track_trials'] for s in width_summaries),local_hits_count=sum(s['local_hits'] for s in width_summaries),saved_local_hits=len(columns['ess']),hit_overflow=bool(overflow),complete=not overflow and len(columns['ess'])==sum(s['local_hits'] for s in width_summaries),width_searches=width_summaries,diagnostics=top,strict_original_template_checks=strict,wall_seconds=time.perf_counter()-started)
    return grid,audit,columns,summary

def complete_grid(grid,start,stop):
    for width,stride in zip(WIDTHS,STRIDES):grid[f'centers_width_{width}']=np.arange(start,stop,stride,dtype=np.int32)
    return grid

def forced_triage(root,out,scopes,config,load_grid,load_catalog,progress=None):
    pieces=[]
    for s in scopes:
        if s['role']=='ON':
            columns=load_catalog(s['scan']);columns['source_scan']=np.full(len(columns['ess']),s['scan'],dtype=np.uint8);pieces.append(columns)
    seeds={key:np.concatenate([p[key] for p in pieces]) for key in pieces[0]};del pieces
    total=len(seeds['ess']);shape=(total,6)
    result={'forced_status':np.full(shape,2,dtype=np.uint8),'predicted_center':np.empty(shape,dtype=np.int32),'forced_center_ess':np.full(shape,np.nan,dtype=np.float64),'forced_max_ess':np.full(shape,np.nan,dtype=np.float64),'narrow_off_flag':np.zeros(shape,dtype=np.bool_),'broad_max_ess':np.full(shape,np.nan,dtype=np.float64)}
    for key,value in seeds.items():result['seed_'+key]=value
    reference=scopes[0];nrate=len(drift_grid(reference['nrows'],reference['dt_seconds'],reference['df_hz'],config['max_abs_drift_hz_s']))
    groupkey=seeds['width_channels'].astype(np.int64)*nrate+seeds['drift_index'];order=np.argsort(groupkey,kind='stable');bounds=np.r_[0,np.flatnonzero(np.diff(groupkey[order]))+1,total]
    for dst in scopes:
        scan=dst['scan'];raw=np.load(root/dst['native_path'],mmap_mode='r',allow_pickle=False);y,_=normalize(raw,config['bandpass_block_channels']);del raw
        grid=load_grid(scan);rates=grid['drift_hz_s'];start=config['boundary_halo_channels'];stop=dst['nchannels']-start;complete_grid(grid,start,stop)
        gaps_by_source=np.array([(dst['tref_midpoint_mjd']-s['tref_midpoint_mjd'])*86400 for s in scopes],dtype=np.float64);gaps=gaps_by_source[seeds['source_scan']]
        predicted=seeds['frequency_at_midpoint_mhz']+seeds['drift_hz_s']*gaps/1e6;center_float=np.rint((predicted-dst['fch1_mhz'])*1e6/dst['df_hz'])
        if not np.isfinite(center_float).all() or np.any(np.abs(center_float)>np.iinfo(np.int32).max):raise ValueError('Unrepresentable prediction')
        centers=center_float.astype(np.int32);result['predicted_center'][:,scan]=centers
        radius=np.ceil(1+.5*float(rates[1]-rates[0])*np.abs(gaps)/abs(dst['df_hz'])).astype(np.int64)
        halfwidth=config['max_abs_drift_hz_s']*np.abs(gaps)+seeds['width_channels']*abs(dst['df_hz'])
        result['broad_max_ess'][:,scan]=broad_envelope_max(grid,dst,seeds['frequency_at_midpoint_mhz'],halfwidth)
        for width in WIDTHS:
            prepared=boxcars(y,width)
            for lo,hi in zip(bounds[:-1],bounds[1:]):
                if lo==hi:continue
                rows=order[lo:hi]
                if int(seeds['width_channels'][rows[0]])!=width:continue
                ri=int(seeds['drift_index'][rows[0]]);off=grid['offsets'][ri];center=centers[rows].astype(np.int64);rad=radius[rows]
                valid=(center+int(off.min())-width//2-rad>=0)&(center+int(off.max())+width//2+rad<dst['nchannels']);rows=rows[valid];center=center[valid];rad=rad[valid]
                if not len(rows):continue
                requests=[];locals=[];rads=[]
                for r in np.unique(rad):
                    local=np.flatnonzero(rad==r);requests.append((center[local,None]+np.arange(-int(r),int(r)+1,dtype=np.int64)[None,:]).ravel());locals.append(local);rads.append(int(r))
                lengths=[len(a) for a in requests];unique,inverse=np.unique(np.concatenate(requests),return_inverse=True)
                sums,_,_=tracks_selected(y,prepared,off,unique,width);med,scale=grid[f'calibration_width_{width}'][ri];scores=(sums-med)/scale;cursor=0
                for local,r,length in zip(locals,rads,lengths):
                    grouped=scores[inverse[cursor:cursor+length]].reshape(len(local),2*r+1);selected=rows[local];result['forced_center_ess'][selected,scan]=grouped[:,r];result['forced_max_ess'][selected,scan]=grouped.max(axis=1);result['forced_status'][selected,scan]=1
                    if dst['role']=='OFF':result['narrow_off_flag'][selected,scan]=grouped.max(axis=1)>=config['off_flag_threshold_ess']
                    cursor+=length
            del prepared;gc.collect()
        if progress:progress(scan,total,int(np.count_nonzero(result['forced_status'][:,scan]==1)))
        del grid,y;gc.collect()
    source=result['forced_center_ess'][np.arange(total),seeds['source_scan']];result['source_catalog_selected_track_ess_error']=np.abs(source-seeds['ess'])
    measured=result['forced_status']==1
    if not np.isfinite(source).all() or np.any(result['source_catalog_selected_track_ess_error']!=0):raise ValueError('Source catalog/forced float64 score mismatch')
    if not np.isfinite(result['forced_center_ess'][measured]).all() or not np.isfinite(result['forced_max_ess'][measured]).all():raise ValueError('Invalid measured forced score')
    if np.any(result['forced_max_ess'][measured]<result['forced_center_ess'][measured]):raise ValueError('Neighborhood smaller than center')
    if not np.isnan(result['forced_center_ess'][~measured]).all() or not np.isnan(result['forced_max_ess'][~measured]).all():raise ValueError('Missing support must stay NaN')
    if result['narrow_off_flag'][:,[0,2,4]].any():raise ValueError('ON columns cannot be OFF flags')
    full=measured.all(axis=1);anyflag=result['narrow_off_flag'].any(axis=1)
    unflagged=full&~anyflag
    summary=dict(ON_catalog_rows=total,forced_measurement_slots=total*6,measured_slots=int(measured.sum()),unsupported_slots=int((~measured).sum()),fully_supported_rows=int(full.sum()),any_OFF_flag_rows=int(anyflag.sum()),no_OFF_flag_fully_supported_rows=int(unflagged.sum()),no_OFF_flag_all_three_ON_center_above_threshold_rows=int((unflagged&np.all(result['forced_center_ess'][:,[0,2,4]]>=config['threshold_ess'],axis=1)).sum()),no_OFF_flag_all_three_ON_neighborhood_above_threshold_rows=int((unflagged&np.all(result['forced_max_ess'][:,[0,2,4]]>=config['threshold_ess'],axis=1)).sum()),maximum_source_ess_error=float(result['source_catalog_selected_track_ess_error'].max(initial=0.)),source_catalog_consistency_uses_same_kernel=True,broad_finite_slots=int(np.isfinite(result['broad_max_ess']).sum()),all_rows_serialized=True,broad_context_is_automatic_OFF_veto=False)
    return result,summary
