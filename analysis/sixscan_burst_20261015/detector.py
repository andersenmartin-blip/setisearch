"""Prospective complete common-reference BURST4 six-scan detector.

No observations, controls, RNG or jobs are opened/run at module import.
All unique global-grid native4 identities are scored before per-carrier top5
selection. OFF vetoes query a complete >=8 inventory, never an OFF top5 list.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import math
from typing import Any

import numpy as np
from scipy.ndimage import median_filter


def require(condition,message):
    if not condition:raise ValueError(message)


@dataclass(frozen=True)
class Scan:
    scan_id:str
    role:str
    power:np.ndarray
    tstart_mjd:float
    tsamp_s:float
    fch1_hz:float
    df_hz:float
    source_channel0:int
    normalization_source_channels:np.ndarray
    valid_mask:np.ndarray|None=None
    expected_nrows:int=16


@dataclass(frozen=True)
class Config:
    max_drift_hz_s:float=4.0
    widths:tuple[int,...]=(1,3,9,33)
    window_starts:tuple[int,...]=(0,2,4,6,8,10,12)
    window_rows:int=4
    running_median_channels:int=501
    on_threshold:float=10.0
    off_threshold:float=8.0
    carrier_count:int=4096
    retained_k:int=5
    drift_tile:int=128
    carrier_tile:int=256
    off_inventory_cap:int=2000000

    def check(self):
        require(self.max_drift_hz_s==4 and self.widths==(1,3,9,33) and
                self.window_starts==(0,2,4,6,8,10,12) and self.window_rows==4 and
                self.running_median_channels==501 and self.on_threshold==10 and
                self.off_threshold==8 and self.carrier_count==4096 and self.retained_k==5,
                'Different scientific family requires a new freeze')
        require(self.drift_tile>0 and self.carrier_tile>0 and self.off_inventory_cap>0,'Positive resource tiles/cap required')


_GEOMETRY_CACHE={}


def cadence_geometry(scans:list[Scan],corefirst:int,cfg:Config):
    """Original common-tref drift grid; four-row compatibility reference halo."""
    cfg.check()
    require(len(scans)==6 and [s.role for s in scans]==['ON','OFF']*3,'Six chronological ON/OFF scans required')
    require(len({s.scan_id for s in scans})==6,'Distinct scan IDs required')
    require(all(s.expected_nrows==16 and s.tsamp_s>0 and s.df_hz!=0 for s in scans),'Complete16-row finite cadence required')
    require(all(s.df_hz==scans[0].df_hz and s.fch1_hz==scans[0].fch1_hz for s in scans),'One explicit native frequency coordinate system required')
    require(all(np.isfinite([s.tstart_mjd,s.tsamp_s,s.fch1_hz,s.df_hz]).all() for s in scans),'Finite header coordinates required')
    anchor=min(s.tstart_mjd for s in scans);absolute=[];previous_end=-np.inf
    for scan in scans:
        start=(scan.tstart_mjd-anchor)*86400.0
        require(start>=previous_end,'Chronological nonoverlapping integrations required')
        previous_end=start+16*scan.tsamp_s
        absolute.append(start+(np.arange(16,dtype=np.float64)+.5)*scan.tsamp_s)
    first,last=float(absolute[0][0]),float(absolute[-1][-1]);span=last-first;tref=(first+last)/2.0
    times=[a-tref for a in absolute]
    n=int(np.ceil(cfg.max_drift_hz_s*span/abs(scans[0].df_hz)))
    grid=np.linspace(-4.0,4.0,2*n+1,dtype=np.float64);grid[n]=0.0
    step=float(grid[1]-grid[0])
    require(step*span/abs(scans[0].df_hz)<=1+1e-12,'Global fine drift spacing loses half-channel bound')
    burst_spans=[float(t[w+3]-t[w]) for t in times for w in cfg.window_starts]
    mids=[abs(float((t[w]+t[w+3])/2.0)) for t in times for w in cfg.window_starts]
    cmax=max(cfg.widths)+2.0
    slope_max=2*cmax*abs(scans[0].df_hz)/min(burst_spans)+2*step
    halo=int(np.ceil(cmax+slope_max*max(mids)/abs(scans[0].df_hz)))
    return {'mjd_anchor':float(anchor),'tref_seconds_from_anchor':tref,'tref_mjd':float(anchor+tref/86400),
        'span_s':span,'times_from_tref_s':times,'drift_grid_hz_s':grid,'drift_step_hz_s':step,
        'core_reference_source_channel_interval_half_open':[int(corefirst),int(corefirst+4096)],
        'OFF_reference_halo_channels':halo,'OFF_reference_source_channel_interval_half_open':[int(corefirst-halo),int(corefirst+4096+halo)],
        'burst_window_starts':list(cfg.window_starts),'burst_window_rows':4,'widths':list(cfg.widths),
        'fch1_hz':float(scans[0].fch1_hz),'df_hz':float(scans[0].df_hz),
        'rounding':'np.rint(absolute integer reference-source channel + global_drift*time_from_common_tref/df), ties-even',
        'OFF_alias_semantics':'existential ANY retained ON donor alias x ANY compatible OFF global-grid alias',
        'OFF_inventory_semantics':'complete every >=8 unique native4 identity; all below8 identities excluded by exhaustive score census'}


def _alias_geometry(scans,geometry,cfg):
    """Metadata-only parity factorization with an explicit fixed-binade proof.

    In one binary64 binade, translating a source integer by2 translates the
    rounded sum by2 exactly. Integer nearest-even parity is then preserved.
    Every native4 donor group is monotone and has a contiguous drift interval.
    """
    grid=geometry['drift_grid_hz_s'];df=geometry['df_hz']
    lo,hi=geometry['OFF_reference_source_channel_interval_half_open']
    maxoffset=max(abs(float(t)) for ts in geometry['times_from_tref_s'] for t in ts)*4/abs(df)+1
    lower,upper=lo-maxoffset,hi-1+maxoffset
    require(lower>0 and math.floor(math.log2(lower))==math.floor(math.log2(upper)),'Parity compression requires one positive binary64 binade')
    tables={}
    for scan,times in zip(scans,geometry['times_from_tref_s']):
        per_scan={}
        for window in cfg.window_starts:
            for parity in (0,1):
                canonical=lo+((parity-lo)%2)
                channels=np.rint(np.float64(canonical)+grid[:,None]*times[window:window+4][None,:]/df).astype(np.int64)
                changes=np.r_[True,np.any(channels[1:]!=channels[:-1],axis=1)]
                starts=np.flatnonzero(changes).astype(np.int32)
                stops=np.r_[starts[1:]-1,len(grid)-1].astype(np.int32)
                relative=channels[starts]-canonical
                require(len(np.unique(relative,axis=0))==len(relative),'Native donor path is not one contiguous monotone interval')
                inverse=np.repeat(np.arange(len(starts),dtype=np.int32),stops-starts+1)
                # Endpoint translation checks supplement the fixed-binade proof.
                for test_reference in (canonical,hi-1-((hi-1-parity)%2)):
                    observed=np.rint(np.float64(test_reference)+grid[:,None]*times[window:window+4][None,:]/df).astype(np.int64)
                    require(np.array_equal(observed,relative[inverse]+test_reference),'Absolute parity translation proof/check differs')
                per_scan[(window,parity)]={'relative_centers':relative,'alias_first_index':starts,
                    'alias_last_index':stops,'drift_to_unique_path':inverse,'canonical_reference_channel':int(canonical)}
        tables[scan.scan_id]=per_scan
    return tables


def search_geometry(scans,corefirst,cfg):
    key=(tuple((s.scan_id,s.role,s.tstart_mjd,s.tsamp_s,s.fch1_hz,s.df_hz,s.expected_nrows) for s in scans),int(corefirst),
         cfg.max_drift_hz_s,cfg.widths,cfg.window_starts,cfg.window_rows)
    if key not in _GEOMETRY_CACHE:
        geometry=cadence_geometry(scans,corefirst,cfg)
        _GEOMETRY_CACHE[key]=(geometry,_alias_geometry(scans,geometry,cfg))
    return _GEOMETRY_CACHE[key]


def preprocess(scan,cfg):
    power=np.asarray(scan.power,dtype=np.float64)
    require(power.ndim==2 and power.shape[0]==16 and power.shape[1]>=501 and np.isfinite(power).all() and (power>=0).all(),'Complete finite nonnegative source power required')
    if scan.valid_mask is None:mask=np.ones(power.shape,dtype=bool)
    else:
        mask=np.asarray(scan.valid_mask,dtype=bool)
        if mask.ndim==1:mask=np.broadcast_to(mask,power.shape)
        require(mask.shape==power.shape,'Input validity mask shape differs')
    source=np.asarray(scan.normalization_source_channels,dtype=np.int64);local=source-scan.source_channel0
    require(len(source)==4096 and len(np.unique(source))==4096 and local.min()>=250 and local.max()+250<power.shape[1],'Original4096 normalization source support required')
    count=mask[:,local].sum(axis=1);require((count>0).all(),'Entirely masked normalization row')
    level=np.nanmedian(np.where(mask[:,local],power[:,local],np.nan),axis=1)
    require(np.isfinite(level).all() and (level>0).all(),'Positive finite row power medians required')
    normalized=power/level[:,None]
    residual=normalized-median_filter(normalized,size=(1,501),mode='nearest')
    center=np.nanmedian(np.where(mask[:,local],residual[:,local],np.nan),axis=1)
    scale=1.4826*np.nanmedian(np.where(mask[:,local],np.abs(residual[:,local]-center[:,None]),np.nan),axis=1)
    require(np.isfinite(scale).all() and (scale>0).all(),'Positive finite residual MADs required')
    clipped=np.clip(residual[:,local]-center[:,None],-5*scale[:,None],5*scale[:,None])
    location=center+np.nanmean(np.where(mask[:,local],clipped,np.nan),axis=1)
    z=(residual-location[:,None])/scale[:,None]
    normal={'row_power_median':level.tolist(),'row_residual_median':center.tolist(),'row_residual_MAD_scale':scale.tolist(),
        'row_winsorized_residual_location':location.tolist(),'normalization_source_channels':source.tolist(),'normalization_unmasked_counts':count.tolist()}
    return z,mask,normal


def _box_arrays(z,mask,cfg):
    prefix=np.zeros((16,z.shape[1]+1),dtype=np.float64);prefix[:,1:]=np.cumsum(z,axis=1,dtype=np.float64)
    bad=np.zeros(prefix.shape,dtype=np.int32);bad[:,1:]=np.cumsum(~mask,axis=1,dtype=np.int32)
    return {w:(prefix[:,w:]-prefix[:,:-w],(bad[:,w:]-bad[:,:-w])==0) for w in cfg.widths}


def _native_score_tile(boxes,reference,relative,window,width,source_channel0):
    sums=np.zeros((len(relative),len(reference)),dtype=np.float64);valid=np.ones(sums.shape,dtype=bool)
    values,unmasked=boxes[width]
    for offset in range(4):
        index=relative[:,offset,None]+reference[None,:]-source_channel0-width//2
        require(index.min()>=0 and index.max()<values.shape[1],'Declared native width trajectory outside decoded source')
        sums+=values[window+offset,index];valid&=unmasked[window+offset,index]
    sums/=np.sqrt(4.0*width);sums[~valid]=-np.inf
    return sums,valid


def _local_top_indices(scores,representatives,k=5):
    """Fast partial select, with a complete exact-equality boundary-tie path."""
    count=min(k,scores.shape[0])
    indices=np.argpartition(-scores,count-1,axis=0)[:count]
    selected=np.take_along_axis(scores,indices,axis=0)
    cutoff=selected.min(axis=0)
    boundary_ties=(scores==cutoff[None,:]).sum(axis=0)>(selected==cutoff[None,:]).sum(axis=0)
    for column in np.flatnonzero(boundary_ties & np.isfinite(cutoff)):
        indices[:,column]=np.lexsort((representatives,-scores[:,column]))[:count]
    return indices


def _merge_top5(current,score,width,window,representatives,cfg):
    local=_local_top_indices(score,representatives,cfg.retained_k)
    selected=np.take_along_axis(score,local,axis=0)
    donor=representatives[local]
    cscore=np.concatenate((current['scores'],selected),axis=0)
    cwidth=np.concatenate((current['widths'],np.full(selected.shape,width,dtype=np.int16)),axis=0)
    cwindow=np.concatenate((current['window_starts'],np.full(selected.shape,window,dtype=np.int16)),axis=0)
    cdrift=np.concatenate((current['drift_grid_indices'],donor),axis=0)
    order=np.lexsort((cdrift,cwindow,cwidth,-cscore),axis=0)[:cfg.retained_k]
    return {'scores':np.take_along_axis(cscore,order,axis=0),'widths':np.take_along_axis(cwidth,order,axis=0),
        'window_starts':np.take_along_axis(cwindow,order,axis=0),'drift_grid_indices':np.take_along_axis(cdrift,order,axis=0)}


def _inventory(records):
    names=('reference_carrier_index','reference_source_channel','width','window_start','representative_drift_index',
           'alias_first_index','alias_last_index','score','native4_centers')
    records.sort(key=lambda r:(r[2],r[3],r[0],r[4]))
    if not records:
        return {n:np.empty((0,4),dtype=np.int64) if n=='native4_centers' else np.empty(0,dtype=np.float64 if n=='score' else np.int64) for n in names}
    return {name:np.asarray([row[i] for row in records],dtype=np.float64 if name=='score' else np.int64) for i,name in enumerate(names)}


def search_scan(scan,reference,times,tables,geometry,cfg):
    z,mask,normal=preprocess(scan,cfg);boxes=_box_arrays(z,mask,cfg)
    maxoffset=max(abs(float(t)) for t in times)*4/abs(scan.df_hz)
    guard=250+max(cfg.widths)//2
    require(min(reference)-maxoffset-scan.source_channel0>=guard and
            max(reference)+maxoffset-scan.source_channel0<z.shape[1]-guard,'Full drift family lacks raw501/widest-box margin')
    ncar=len(reference);k=cfg.retained_k
    current={'scores':np.full((k,ncar),-np.inf),'widths':np.full((k,ncar),32767,dtype=np.int16),
        'window_starts':np.full((k,ncar),32767,dtype=np.int16),'drift_grid_indices':np.full((k,ncar),2147483647,dtype=np.int32)}
    counts_unique=np.zeros(ncar,dtype=np.int64);valid_unique=np.zeros(ncar,dtype=np.int64);valid_original=np.zeros(ncar,dtype=np.int64)
    records=[];maximum=-np.inf
    for width in cfg.widths:
        for window in cfg.window_starts:
            for parity in (0,1):
                positions=np.flatnonzero(reference%2==parity);table=tables[(window,parity)]
                relative=table['relative_centers'];aliases=table['alias_last_index']-table['alias_first_index']+1
                counts_unique[positions]+=len(relative)
                for clo in range(0,len(positions),cfg.carrier_tile):
                    columns=positions[clo:clo+cfg.carrier_tile];refs=reference[columns]
                    block={name:value[:,columns].copy() for name,value in current.items()}
                    for dlo in range(0,len(relative),cfg.drift_tile):
                        stop=min(dlo+cfg.drift_tile,len(relative));rel=relative[dlo:stop];donors=table['alias_first_index'][dlo:stop]
                        scores,valid=_native_score_tile(boxes,refs,rel,window,width,scan.source_channel0)
                        valid_unique[columns]+=valid.sum(axis=0);valid_original[columns]+=(valid*aliases[dlo:stop,None]).sum(axis=0)
                        maximum=max(maximum,float(scores.max()))
                        block=_merge_top5(block,scores,width,window,donors,cfg)
                        if scan.role=='OFF':
                            rows,cols=np.nonzero(scores>=cfg.off_threshold)
                            require(len(records)+len(rows)<=cfg.off_inventory_cap,'Complete OFF inventory cap exceeded; no negative veto proof permitted')
                            for row,col in zip(rows.tolist(),cols.tolist()):
                                group=dlo+row;carrier=int(columns[col]);ref=int(refs[col])
                                records.append((carrier,ref,width,window,int(donors[row]),int(table['alias_first_index'][group]),
                                    int(table['alias_last_index'][group]),float(scores[row,col]),(rel[row]+ref).tolist()))
                    for name in current:current[name][:,columns]=block[name]
    maps={name:np.ascontiguousarray(value.T) for name,value in current.items()}
    maps['retained_valid']=np.isfinite(maps['scores'])
    native=np.zeros((ncar,k,4),dtype=np.int64);first_alias=np.full((ncar,k),-1,dtype=np.int32);last_alias=first_alias.copy()
    for carrier in range(ncar):
        for rank in range(k):
            if not maps['retained_valid'][carrier,rank]:continue
            window=int(maps['window_starts'][carrier,rank]);di=int(maps['drift_grid_indices'][carrier,rank])
            table=tables[(window,int(reference[carrier]%2))];group=int(table['drift_to_unique_path'][di])
            native[carrier,rank]=reference[carrier]+table['relative_centers'][group]
            first_alias[carrier,rank]=table['alias_first_index'][group];last_alias[carrier,rank]=table['alias_last_index'][group]
    maps.update({'scan_id':scan.scan_id,'role':scan.role,'reference_source_channels':reference,
        'native4_centers':native,'drift_alias_first_index':first_alias,'drift_alias_last_index':last_alias,
        'total_original_hypothesis_count':np.full(ncar,len(geometry['drift_grid_hz_s'])*7*4,dtype=np.int64),
        'total_unique_native_hypothesis_count':counts_unique,'valid_original_hypothesis_count':valid_original,
        'valid_unique_native_hypothesis_count':valid_unique,'normalization':normal,
        'maximum_robust_box_track_score':maps['scores'][:,0].copy()})
    inventory=_inventory(records)
    inventory_certificate={'complete':True,'score_threshold':cfg.off_threshold,'inventory_rows':len(records),
        'evaluated_unique_native_hypotheses':int(valid_unique.sum()),'evaluated_original_grid_hypotheses':int(valid_original.sum()),
        'declared_original_grid_hypotheses':int(ncar*len(geometry['drift_grid_hz_s'])*7*4),
        'maximum_score_all_evaluated_unique_hypotheses':float(maximum),
        'traversal':'width ascending, window start ascending, reference carrier ascending, representative drift index ascending',
        'inventory_sha256':hashlib.sha256(b''.join(np.ascontiguousarray(inventory[name]).tobytes() for name in sorted(inventory))).hexdigest()}
    return maps,inventory,inventory_certificate


def _alias_pair_witness(on,off_reference,off_width,off_first,off_last,times,grid,df,cfg):
    first,last=float(times[on['window_start']]),float(times[on['window_start']+3])
    tolerance=(on['width_channels']+off_width)/2.0+2.0
    delta_channel=float(off_reference-on['reference_source_channel'])
    on_indices=np.arange(on['drift_alias_first_index'],on['drift_alias_last_index']+1,dtype=np.int32)
    off_indices=np.arange(off_first,off_last+1,dtype=np.int32)
    difference=grid[off_indices][None,:]-grid[on_indices][:,None]
    error_first=delta_channel+difference*first/df;error_last=delta_channel+difference*last/df
    matched=(np.abs(error_first)<=tolerance)&(np.abs(error_last)<=tolerance)
    where=np.flatnonzero(matched.ravel())
    if not len(where):return None,int(matched.size)
    row,col=np.unravel_index(int(where[0]),matched.shape)
    return {'ON_drift_grid_index':int(on_indices[row]),'OFF_drift_grid_index':int(off_indices[col]),
        'ON_drift_hz_s':float(grid[on_indices[row]]),'OFF_drift_hz_s':float(grid[off_indices[col]]),
        'ON_first_endpoint_error_channels':float(error_first[row,col]),'ON_last_endpoint_error_channels':float(error_last[row,col]),
        'ON_first_endpoint_error_hz_audit':float(error_first[row,col]*df),'ON_last_endpoint_error_hz_audit':float(error_last[row,col]*df),
        'endpoint_tolerance_hz_audit':float(tolerance*abs(df)),
        'endpoint_tolerance_channels':float(tolerance),'ON_first_endpoint_time_from_tref_s':first,
        'ON_last_endpoint_time_from_tref_s':last},int(matched.size)


def off_witness(on,off_scan,inventory,certificate,on_times,geometry,cfg):
    require(certificate['complete'],'Incomplete OFF inventory cannot prove witness absence')
    grid=geometry['drift_grid_hz_s'];df=geometry['df_hz'];checked=0
    # A cheap interval envelope only prunes impossible alias-pair rectangles;
    # the actual witness always uses direct original endpoint arithmetic.
    first,last=float(on_times[on['window_start']]),float(on_times[on['window_start']+3])
    on_low=float(grid[on['drift_alias_first_index']]);on_high=float(grid[on['drift_alias_last_index']])
    tolerance=(on['width_channels']+inventory['width'])/2.0+2.0
    delta_channel=(inventory['reference_source_channel']-on['reference_source_channel']).astype(np.float64)
    dmin=grid[inventory['alias_first_index']]-on_high
    dmax=grid[inventory['alias_last_index']]-on_low
    possible=np.ones(certificate['inventory_rows'],dtype=bool)
    for time in (first,last):
        endpoint_low=delta_channel+dmin*time/df
        endpoint_high=delta_channel+dmax*time/df
        lower=np.minimum(endpoint_low,endpoint_high);upper=np.maximum(endpoint_low,endpoint_high)
        possible&=(upper>=-tolerance)&(lower<=tolerance)
    for i in np.flatnonzero(possible).tolist():
        ow=int(inventory['width'][i])
        witness,pairs=_alias_pair_witness(on,int(inventory['reference_source_channel'][i]),ow,
            int(inventory['alias_first_index'][i]),int(inventory['alias_last_index'][i]),on_times,grid,df,cfg)
        checked+=pairs
        if witness is not None:
            witness.update({'OFF_inventory_index':i,'OFF_reference_carrier_index':int(inventory['reference_carrier_index'][i]),
                'OFF_reference_source_channel':int(inventory['reference_source_channel'][i]),'OFF_width_channels':ow,
                'OFF_window_start':int(inventory['window_start'][i]),'OFF_score':float(inventory['score'][i]),
                'OFF_native4_centers':inventory['native4_centers'][i].tolist()})
            return {'scan_id':off_scan.scan_id,'veto':True,'inventory_exhausted_before_query':True,
                'all_threshold_records_compatibility_checked':False,'checked_alias_pairs':checked,'witness':witness,
                'inventory_sha256':certificate['inventory_sha256'],'inventory_rows':certificate['inventory_rows']}
    return {'scan_id':off_scan.scan_id,'veto':False,'inventory_exhausted_before_query':True,
        'all_threshold_records_compatibility_checked':True,'checked_alias_pairs':checked,'witness':None,
        'inventory_sha256':certificate['inventory_sha256'],'inventory_rows':certificate['inventory_rows']}


def search_cadence(scans:list[Scan],corefirst:int,cfg:Config|None=None):
    cfg=cfg or Config();cfg.check();geometry,aliases=search_geometry(scans,corefirst,cfg)
    on_reference=np.arange(corefirst,corefirst+4096,dtype=np.int64)
    off_reference=np.arange(*geometry['OFF_reference_source_channel_interval_half_open'],dtype=np.int64)
    maps=[];inventories={};certificates={}
    for scan,times in zip(scans,geometry['times_from_tref_s']):
        reference=on_reference if scan.role=='ON' else off_reference
        result,inventory,certificate=search_scan(scan,reference,times,aliases[scan.scan_id],geometry,cfg)
        maps.append(result)
        if scan.role=='OFF':inventories[scan.scan_id]=inventory;certificates[scan.scan_id]=certificate
    hits=[]
    for scan,times,mapping in zip(scans,geometry['times_from_tref_s'],maps):
        if scan.role!='ON':continue
        carriers,ranks=np.nonzero(mapping['scores']>=cfg.on_threshold)
        for carrier,rank in zip(carriers.tolist(),ranks.tolist()):
            on={'scan_id':scan.scan_id,'reference_carrier_index':carrier,'reference_source_channel':int(mapping['reference_source_channels'][carrier]),
                'hit_id':f'{scan.scan_id}:carrier{carrier:04d}:rank{rank+1}',
                'retained_rank':rank+1,'width_channels':int(mapping['widths'][carrier,rank]),
                'window_start':int(mapping['window_starts'][carrier,rank]),'window_source_rows':list(range(int(mapping['window_starts'][carrier,rank]),int(mapping['window_starts'][carrier,rank])+4)),
                'window_start_row':int(mapping['window_starts'][carrier,rank]),
                'representative_drift_grid_index':int(mapping['drift_grid_indices'][carrier,rank]),
                'representative_drift_hz_s':float(geometry['drift_grid_hz_s'][mapping['drift_grid_indices'][carrier,rank]]),
                'drift_alias_first_index':int(mapping['drift_alias_first_index'][carrier,rank]),
                'drift_alias_last_index':int(mapping['drift_alias_last_index'][carrier,rank]),
                'native4_centers':mapping['native4_centers'][carrier,rank].tolist(),'ON_score':float(mapping['scores'][carrier,rank]),
                'physical_drift_not_unique':bool(mapping['drift_alias_first_index'][carrier,rank]!=mapping['drift_alias_last_index'][carrier,rank]),
                'OFF_comparisons':[]}
            for off_scan in scans:
                if off_scan.role=='OFF':on['OFF_comparisons'].append(off_witness(on,off_scan,inventories[off_scan.scan_id],certificates[off_scan.scan_id],times,geometry,cfg))
            on['disposition']='OFF_MATCHED' if any(r['veto'] for r in on['OFF_comparisons']) else 'SURVIVOR_EXPLORATORY'
            hits.append(on)
    return {'schema':'SETI_COMPLETE_COMMON_REFERENCE_BURST4_SEARCH_V1','geometry':geometry,'alias_geometry':aliases,
        'scan_maps':maps,'OFF_threshold_inventories':inventories,'OFF_inventory_certificates':certificates,
        'all_ON_threshold_hypotheses':hits,'surviving_ON_threshold_hypothesis_count':sum(h['disposition']=='SURVIVOR_EXPLORATORY' for h in hits),
        'maximum_pre_OFF_ON_score':float(max(m['scores'].max() for m in maps if m['role']=='ON')),
        'score_definition':'native box four-row z sum/sqrt(4*width); original robust preprocessing and prefix box arithmetic',
        'selection':'single top5 distinct(width,window,native4centers) per common-reference carrier',
        'limitations':['Complete declared4096-band family, not complete telescope spectrum','ANY-alias OFF veto is separate conservative prospective semantics',
            'One ON burst is retained without mandatory recurrence','No sky false-alarm calibration; original A/B qualification unchanged'],
        'qualified_SETI_detection':False,'original_A_B':'FAIL_CLOSED'}


def recovery(output:dict,truth:dict):
    """Prospective localized burst recovery before/after exhaustive OFF veto.

    truth: active_ON_scan_ids, reference_source_channel_at_tref, drift_hz_s,
    active_window_start_by_scan, oracle_width_by_scan. Primary localization
    requires the true four-row activity window and an attainable donor alias.
    """
    active=truth['active_ON_scan_ids'];require(active and len(set(active))==len(active),'Distinct declared active ON scans required')
    geometry=output['geometry'];grid=geometry['drift_grid_hz_s'];df=geometry['df_hz']
    by_scan={m['scan_id']:i for i,m in enumerate(output['scan_maps'])}
    tref_channel=float(truth['reference_source_channel_at_tref']);drift=float(truth['drift_hz_s']);rows={}
    for scan_id in active:
        window=int(truth['active_window_start_by_scan'][scan_id]);oracle=int(truth['oracle_width_by_scan'][scan_id])
        times=geometry['times_from_tref_s'][by_scan[scan_id]];first,last=float(times[window]),float(times[window+3])
        pre=[];final=[]
        for hit in output['all_ON_threshold_hypotheses']:
            if hit['scan_id']!=scan_id or hit['window_start']!=window:continue
            donors=np.arange(hit['drift_alias_first_index'],hit['drift_alias_last_index']+1,dtype=np.int32)
            difference=grid[donors]-drift;delta_channel=hit['reference_source_channel']-tref_channel
            error_first=delta_channel+difference*first/df;error_last=delta_channel+difference*last/df
            tolerance=2.0+max(hit['width_channels'],oracle)/2.0
            matched=(np.abs(error_first)<=tolerance)&(np.abs(error_last)<=tolerance)
            if matched.any():
                record={'reference_carrier_index':hit['reference_carrier_index'],'retained_rank':hit['retained_rank'],
                    'hit_id':hit['hit_id'],'window_start_row':hit['window_start_row'],
                    'matched_donor_drift_grid_index':int(donors[np.flatnonzero(matched)[0]]),'ON_score':hit['ON_score'],
                    'first_endpoint_error_channels':float(error_first[np.flatnonzero(matched)[0]]),
                    'last_endpoint_error_channels':float(error_last[np.flatnonzero(matched)[0]]),'endpoint_tolerance_channels':float(tolerance)}
                pre.append(record)
                if hit['disposition']=='SURVIVOR_EXPLORATORY':final.append(record)
        rows[scan_id]={'pre_OFF_localized_recovery':bool(pre),'final_localized_recovery':bool(final),
            'pre_OFF_localized_count':len(pre),'final_localized_count':len(final),'oracle_width_channels':oracle,
            'true_window_start':window,'pre_OFF_matches':pre,'final_matches':final}
    return {'active_ON_scan_ids':active,'by_scan':rows,'all_active_ON_pre_OFF_recovered':all(v['pre_OFF_localized_recovery'] for v in rows.values()),
        'all_active_ON_final_recovered':all(v['final_localized_recovery'] for v in rows.values()),
        'at_least_one_active_ON_final_recovered':any(v['final_localized_recovery'] for v in rows.values()),
        'any_final_survivor_hypothesis_count':output['surviving_ON_threshold_hypothesis_count'],
        'localization':'exact true4row window and ANY attainable donor alias, endpoints within2+max(hitwidth,oraclewidth)/2channels',
        'qualified_SETI_detection':False}


def metadata_selftest():
    """Tiny metadata/uniform-z checks only; no RNG, normalization or bank data."""
    cfg=Config();cfg.check()
    grid=np.linspace(-4,4,5723,dtype=np.float64)
    refs=np.asarray([179531776,179531778],dtype=np.int64)
    relative=np.asarray([[0,0,0,0],[0,1,2,3]],dtype=np.int64)
    z=np.ones((16,12096),dtype=np.float64);mask=np.ones(z.shape,dtype=bool);boxes=_box_arrays(z,mask,cfg)
    scores,valid=_native_score_tile(boxes,refs,relative,0,3,179527776)
    require(valid.all() and np.all(scores==12/math.sqrt(12)),'Uniform-z odd-box score arithmetic failed')
    on={'window_start':0,'width_channels':1,'reference_source_channel':179531776,
        'drift_alias_first_index':2860,'drift_alias_last_index':2862}
    times=np.asarray([-50.,-32.,-14.,4.]+[22.]*12)
    witness,_=_alias_pair_witness(on,179531776,1,2860,2862,times,grid,-2.7939677238464355,cfg)
    require(witness is not None and witness['ON_drift_grid_index']==2860 and witness['OFF_drift_grid_index']==2860,'ANY-alias uniform coordinate witness failed')
    scores=np.zeros((9,2));donors=np.arange(9,dtype=np.int32)
    selected=_local_top_indices(scores,donors)
    require(np.array_equal(selected,np.tile(np.arange(5)[:,None],(1,2))),'Boundary-score tie selection failed')
    # Exhaustive metadata-only comparison of vector envelope and direct scalar
    # envelope, including both endpoint signs, exact tolerance and wide boxes.
    reference=np.asarray([179531776,179531779,179531772,179531800,179531700],dtype=np.int64)
    widths=np.asarray([1,1,3,33,9],dtype=np.int64)
    alias_first=np.asarray([2860,2861,2857,2800,3200],dtype=np.int64)
    alias_last=np.asarray([2862,2861,2865,2920,3210],dtype=np.int64)
    tolerance=(on['width_channels']+widths)/2.0+2.0
    delta=(reference-on['reference_source_channel']).astype(np.float64)
    dmin=grid[alias_first]-float(grid[on['drift_alias_last_index']])
    dmax=grid[alias_last]-float(grid[on['drift_alias_first_index']])
    vector=np.ones(len(reference),dtype=bool)
    scalar=[]
    for time in (float(times[0]),float(times[3])):
        a=delta+dmin*time/-2.7939677238464355;b=delta+dmax*time/-2.7939677238464355
        vector&=(np.maximum(a,b)>=-tolerance)&(np.minimum(a,b)<=tolerance)
    for i in range(len(reference)):
        possible=True
        for time in (float(times[0]),float(times[3])):
            a=float(delta[i])+float(dmin[i])*time/-2.7939677238464355
            b=float(delta[i])+float(dmax[i])*time/-2.7939677238464355
            lo,hi=sorted((a,b))
            if hi<-float(tolerance[i]) or lo>float(tolerance[i]):possible=False;break
        scalar.append(possible)
    require(np.array_equal(vector,np.asarray(scalar,dtype=bool)),'Vector OFF envelope changed scalar pruning')
    return {'schema':'SETI_BURST4_METADATA_UNIFORM_SELFTEST_V1','status':'PASS','bank_arrays_opened':False,
        'RNG_called':False,'science_search_executed':False,'checks':['uniform-z boxscore','ANY donor/OFF aliases',
            'exact boundary-score deterministic ties','vector OFF envelope equals deterministic scalar fixture']}
