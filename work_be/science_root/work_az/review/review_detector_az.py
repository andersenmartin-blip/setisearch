#!/usr/bin/env python3
"""Independent AZ detector audit; unchanged inherited AW arithmetic.

No production normalizer, kernel, boxcar, accumulation or calibration imports.
Full interpolation replay shares np.interp; bounded scalar interpolation is
separate and disclosed. Only --parent-go releases native reads.
"""
from pathlib import Path
import argparse,datetime,gc,hashlib,json,math,os,sys
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
import oracles_independent_az as oracle
BASE=Path(__file__).resolve().parent
WORKSPACE=BASE.parent.parent
QA_DESIGN=BASE/'QA_DESIGN_ORIGINAL_S.json'

def load(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def new(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def exact(a,b):return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()

def numeric_qa(raw,scope,scopes,grid,audit,summary):
    """Bounded independent arithmetic; no detector arithmetic imports in oracle."""
    y,median,scale,digests=oracle.normalize_independently(raw,4096)
    assert exact(audit['block_median'],median) and exact(audit['block_MAD_scale'],scale)
    assert exact(audit['normalized_block_sha256'],digests)
    rates,offsets,centers_by_width=oracle.derive_grid(16,1048576,scope['dt_seconds'],scope['df_hz'])
    assert exact(grid['drift_hz_s'],rates) and exact(grid['offsets'],offsets)
    max_sum_error=0.;max_ess_error=0.;max_vector_error=0.;fixed_tracks=0;vector_positions=0;maxima=0
    width_reports=[]
    for wi,width in enumerate(oracle.WIDTHS):
        centers=centers_by_width[width];indices=np.linspace(0,len(centers)-1,8,dtype=np.int64);selected=centers[indices]
        assert exact(audit[f'fixed_centers_width_{width}'],selected)
        fixed=np.array([oracle.fsum_tracks(y,off,selected,width) for off in offsets],dtype=np.float64)
        sums=audit[f'fixed_sums_width_{width}'];cal=grid[f'calibration_width_{width}']
        delta=float(np.abs(fixed-sums).max(initial=0.));assert delta<5e-5
        scores=(fixed-cal[:,0,None])/cal[:,1,None]
        saved=audit[f'fixed_scores_width_{width}'];assert np.isclose(scores,saved,atol=1e-4,rtol=5e-6).all()
        max_sum_error=max(max_sum_error,delta);max_ess_error=max(max_ess_error,float(np.abs(scores-saved).max(initial=0.)));fixed_tracks+=fixed.size
        best=grid[f'max_ess_width_{width}'];winner=grid[f'max_drift_index_width_{width}']
        assert best.dtype==np.float64 and winner.dtype==np.int32
        assert exact(best[indices],saved.max(axis=0))
        assert np.array_equal(winner[indices],saved.argmax(axis=0))
        assert np.isclose(best[indices],scores.max(axis=0),atol=1e-4,rtol=5e-6).all();maxima+=len(indices)
        ri=oracle.FULL_VECTOR_DRIFT_INDICES[wi]
        independent=oracle.compensated_vector(y,offsets[ri],centers,width)
        saved_vector=audit[f'complete_sum_vector_width_{width}']
        vdelta=float(np.abs(independent-saved_vector).max(initial=0.));assert vdelta<5e-5
        assert exact(oracle.calibrate(saved_vector),cal[ri])
        ref_cal=oracle.calibrate(independent);eps=np.finfo(np.float64).eps
        assert abs(float(ref_cal[0]-cal[ri,0]))<=vdelta+32*eps*max(1.,abs(float(ref_cal[0])),abs(float(cal[ri,0])))
        assert abs(float(ref_cal[1]-cal[ri,1]))<=2*1.4826*vdelta+32*eps*max(1.,abs(float(ref_cal[1])),abs(float(cal[ri,1])))
        assert np.isclose((independent-ref_cal[0])/ref_cal[1],(saved_vector-cal[ri,0])/cal[ri,1],atol=1e-4,rtol=5e-6).all()
        max_vector_error=max(max_vector_error,vdelta);vector_positions+=len(centers)
        width_reports.append({'width':width,'fixed_fsum_max_absolute_error':delta,'complete_vector_drift_index':ri,'complete_vector_max_absolute_error':vdelta})
    templates=load(QA_DESIGN)['templates']
    requests=oracle.original_template_requests(scopes,rates,templates)[scope['scan']]
    records={r['original_template_index']:r for r in summary['strict_original_template_checks']}
    assert len(records)==len(requests)==16
    for req in requests:
        r=records[req['original_template_index']];assert all(r[k]==v for k,v in req.items())
        expected=float(oracle.fsum_tracks(y,offsets[req['drift_index']],np.array([req['native_center']],dtype=np.int32),req['width_channels'])[0])
        assert abs(r['candidate_sum']-expected)<5e-5 and r['explicit_fsum']==expected
    del y;gc.collect()
    return {'status':'PASS','normalization_blocks':len(digests),'normalized_pixels':raw.size,'fixed_fsum_tracks':fixed_tracks,'complete_vectors':4,'complete_vector_positions':vector_positions,'selected_global_maxima':maxima,'original_template_checks':16,'maximum_fixed_sum_error':max_sum_error,'maximum_fixed_ESS_error':max_ess_error,'maximum_complete_vector_error':max_vector_error,'widths':width_reports,'normalization_review':dict(oracle.LAST_NORMALIZATION_REPORT),'independent_scope':'All independently sorted anchors and exact shared-np.interp allpixel replay plus bounded scalar interpolation; all normalized blocks; 8 fixed centers at every drift per width; 4 complete drift/width vectors per scan; 16 original fixed templates. No all-grid independent oracle claim.'}

def triage_qa(root,out,scopes,config,triage,summary):
    """Check all accounting plus 16 deterministic ON seeds in six destinations."""
    measured=triage['forced_status']==1;full=measured.all(axis=1);flag=triage['narrow_off_flag'].any(axis=1)
    assert summary['forced_measurement_slots']==measured.size and summary['measured_slots']==int(measured.sum())
    assert summary['fully_supported_rows']==int(full.sum()) and summary['any_OFF_flag_rows']==int(flag.sum())
    assert summary['no_OFF_flag_fully_supported_rows']==int((full&~flag).sum())
    assert summary['unsupported_slots']==int((~measured).sum())
    assert summary['no_OFF_flag_all_three_ON_center_above_threshold_rows']==int((full&~flag&np.all(triage['forced_center_ess'][:,[0,2,4]]>=10.,axis=1)).sum())
    assert summary['no_OFF_flag_all_three_ON_neighborhood_above_threshold_rows']==int((full&~flag&np.all(triage['forced_max_ess'][:,[0,2,4]]>=10.,axis=1)).sum())
    n=len(triage['seed_ess']);rows=np.unique(np.linspace(0,n-1,min(16,n),dtype=np.int64)) if n else np.array([],dtype=np.int64)
    checks=0;maximum_error=0.;broad_checks=0
    for dst in scopes:
        scan=dst['scan'];raw=np.load(root/dst['native_path'],mmap_mode='r',allow_pickle=False)
        y,_,_,_=oracle.normalize_independently(raw,config['bandpass_block_channels']);del raw
        with np.load(out/f'scan{scan}_grid.npz',allow_pickle=False) as z:grid={k:z[k] for k in z.files}
        rates,offsets,centers_by_width=oracle.derive_grid(dst['nrows'],dst['nchannels'],dst['dt_seconds'],dst['df_hz'],config['max_abs_drift_hz_s'],config['boundary_halo_channels'])
        for row in rows:
            src=int(triage['seed_source_scan'][row]);width=int(triage['seed_width_channels'][row]);ri=int(triage['seed_drift_index'][row]);rate=float(triage['seed_drift_hz_s'][row]);freq=float(triage['seed_frequency_at_midpoint_mhz'][row])
            gap=(dst['tref_midpoint_mjd']-scopes[src]['tref_midpoint_mjd'])*86400
            center=int(np.rint((freq+rate*gap/1e6-dst['fch1_mhz'])*1e6/dst['df_hz']))
            radius=math.ceil(1+.5*float(rates[1]-rates[0])*abs(gap)/abs(dst['df_hz']))
            off=offsets[ri];valid=center+int(off.min())-width//2-radius>=0 and center+int(off.max())+width//2+radius<dst['nchannels']
            assert triage['predicted_center'][row,scan]==center and triage['forced_status'][row,scan]==(1 if valid else 2)
            if valid:
                sums=oracle.fsum_tracks(y,off,np.arange(center-radius,center+radius+1,dtype=np.int32),width)
                med,scale=grid[f'calibration_width_{width}'][ri];scores=(sums-med)/scale
                got=np.array([triage['forced_center_ess'][row,scan],triage['forced_max_ess'][row,scan]])
                expected=np.array([scores[radius],scores.max()]);assert np.isclose(got,expected,atol=1e-4,rtol=5e-6).all()
                maximum_error=max(maximum_error,float(np.abs(got-expected).max(initial=0.)))
                assert bool(triage['narrow_off_flag'][row,scan])==(dst['role']=='OFF' and scores.max()>=5.);checks+=1
            halfwidth=config['max_abs_drift_hz_s']*abs(gap)+width*abs(dst['df_hz']);maxima=[]
            for w,centers in centers_by_width.items():
                frequencies=dst['fch1_mhz']+centers*dst['df_hz']/1e6
                mask=np.abs(frequencies-freq)*1e6<=halfwidth
                if mask.any():maxima.append(float(grid[f'max_ess_width_{w}'][mask].max()))
            expected=max(maxima) if maxima else math.nan;got=float(triage['broad_max_ess'][row,scan])
            assert got==expected or math.isnan(got) and math.isnan(expected);broad_checks+=1
        del grid,y;gc.collect()
    return {'status':'PASS','all_accounting_rows_checked':n,'deterministic_seed_rows':rows.tolist(),'forced_supported_queries_checked':checks,'broad_direct_predicate_queries_checked':broad_checks,'maximum_selected_forced_ESS_error':maximum_error,'scope':'All accounting; up to16 equally spaced serialized ON seed rows, all6 destinations; independent scalar fsum forced neighborhoods; direct broad-envelope predicates over saved grids. No all-row independent forced arithmetic claim.'}

def arrays(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('protocol');parser.add_argument('results');parser.add_argument('--output',required=True);parser.add_argument('--parent-go',required=True);a=parser.parse_args()
    protocol=Path(a.protocol).resolve();out=Path(a.results).resolve();p=load(protocol);go=load(a.parent_go)
    assert go.get('authorized') is True,'Explicit parent native-read GO required'
    assert go.get('root_after_triage') is True,'Root AFTER TRIAGE gate required'
    assert protocol==BASE.parent/'PROTOCOL_BOUND_AZ.json' and out==BASE.parent/'results'
    # Root's immutable bound protocol pins this reviewer, oracle and QA source.
    for rel,digest in p['source_sha256'].items():assert sha(root_path:=WORKSPACE/rel)==digest,rel
    own_relative=str(Path(__file__).resolve().relative_to(WORKSPACE))
    oracle_relative=str((BASE/'oracles_independent_az.py').relative_to(WORKSPACE))
    qa_relative=str(QA_DESIGN.relative_to(WORKSPACE))
    assert all(rel in p['source_sha256'] for rel in (own_relative,oracle_relative,qa_relative))
    assert go['protocol_sha256']==sha(protocol)
    nativepath=Path(go['native_review_path']).resolve();nativeactual=Path(go['native_actual_receipt_path']).resolve()
    assert sha(nativepath)==go['native_review_sha256'] and sha(nativeactual)==go['native_actual_receipt_sha256']
    nativeproof=load(nativepath);nativeactualproof=load(nativeactual)
    assert nativeproof['status']=='PASS' and nativeactualproof['actual_exit_code']==0
    assert nativeactualproof['result_sha256']==sha(nativepath)
    assert p['target']=='HIP44295' and p['primary_id']==65133
    closedtriage=load(out/'TRIAGE_RUN_CLOSED.json');assert closedtriage['status']=='COMPLETE' and closedtriage['protocol_sha256']==sha(protocol)
    if 'protocol_sha256' in go:assert go['protocol_sha256']==sha(protocol)
    root=Path(p['root']).resolve();scopes=p['scans'];config=p['configuration']
    assert [s['scan'] for s in scopes]==list(range(6)) and [s['role'] for s in scopes]==['ON','OFF']*3
    assert config['bandpass_block_channels']==config['boundary_halo_channels']==4096
    assert config['threshold_ess']==10. and config['off_flag_threshold_ess']==5.
    assert config['replay_drift_indices']==[0,279,559,838]
    pins={str(protocol):sha(protocol),str(Path(__file__).resolve()):sha(__file__),str(BASE/'oracles_independent_az.py'):sha(BASE/'oracles_independent_az.py'),str(QA_DESIGN):sha(QA_DESIGN)}
    pins.update({str(WORKSPACE/rel):digest for rel,digest in p['source_sha256'].items()})
    pins.update({str(nativepath):sha(nativepath),str(nativeactual):sha(nativeactual),str(Path(a.parent_go).resolve()):sha(a.parent_go)})
    reports=[]
    for scope in scopes:
        scan=scope['scan'];native=root/scope['native_path'];assert sha(native)==scope['input_sha256'];pins[str(native)]=sha(native)
        paths={kind:out/f'scan{scan}_{kind}.npz' for kind in ['grid','audit','catalog']}
        for path in list(paths.values())+[out/f'scan{scan}_summary.json']:pins[str(path)]=sha(path)
        raw=np.load(native,mmap_mode='r',allow_pickle=False);grid=arrays(paths['grid']);audit=arrays(paths['audit']);catalog=arrays(paths['catalog']);summary=load(out/f'scan{scan}_summary.json')
        assert raw.shape==(16,1048576) and raw.dtype==np.dtype('<f4')
        assert summary['protocol_sha256']==sha(protocol)
        exitpath=BASE.parent/f'execution/scan{scan}_ACTUAL_EXIT.json';pins[str(exitpath)]=sha(exitpath)
        assert load(exitpath)['exit_code']==0
        assert summary['complete'] and not summary['hit_overflow'];assert len(catalog['ess'])==summary['saved_local_hits']
        assert np.isfinite(catalog['ess']).all() and np.all(catalog['ess']>=config['threshold_ess'])
        assert len(catalog['ess'])==sum(s['local_hits'] for s in summary['width_searches'])
        # Exact geometry of extra continuous-normalization anchors.
        starts=np.arange(0,raw.shape[1],4096,dtype=np.int64);stops=np.minimum(starts+4096,raw.shape[1])
        assert exact(audit['block_start'],starts) and exact(audit['block_stop'],stops)
        assert exact(audit['anchor_channel'],(starts.astype(np.float64)+stops.astype(np.float64)-1.)/2.)
        report=numeric_qa(raw,scope,scopes,grid,audit,summary);report['scan']=scan;reports.append(report)
        print(json.dumps({'stage':'independent_scan_review','scan':scan,'status':report['status'],'maximum_sum_error':report['maximum_fixed_sum_error'],'maximum_complete_vector_error':report['maximum_complete_vector_error']}),flush=True)
        del raw,grid,audit,catalog;gc.collect()
    triage_path=out/'all_ON_forced_triage.npz';summary_path=out/'TRIAGE_SUMMARY.json'
    pins[str(triage_path)]=sha(triage_path);pins[str(summary_path)]=sha(summary_path)
    triage=arrays(triage_path);ts=load(summary_path);tqa=triage_qa(root,out,scopes,config,triage,ts)
    for path,digest in pins.items():assert sha(path)==digest,('Bound input changed',path)
    result={'schema':'SETI_AZ_INDEPENDENT_BOUNDED_NUMERIC_REVIEW_V1','status':'PASS','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'separate_review_agent':True,'native_review_path':str(nativepath),'native_review_sha256':sha(nativepath),'native_actual_receipt_path':str(nativeactual),'native_actual_receipt_sha256':sha(nativeactual),'protocol_sha256':sha(protocol),'input_and_source_sha256_before_after':pins,'scan_reports':reports,'triage_review':tqa,'independent_scope':'Sorted full anchor recomputation; shared np.interp full normalized reconstruction; scalar interpolation on fixed bounded sample;8 fixed centers at all839 drifts and4widths per scan;4 complete drift/width compensated vectors per scan;16 original templates per scan;all triage accounting and up to16 uniformly selected ON seed rows in6destinations.','limits':['No independent allpixel interpolation or allgrid accumulation oracle claim.','Empirical scores are not calibrated Gaussian significance, FAP or astronomical sensitivity.','Correlated rows are not independent trials or distinct emitters.'],'accepted_SETI_candidates':0,'sensitivity_qualified_MHz_visits':0,'production_qualified':False}
    new(a.output,result);print(json.dumps({'status':'PASS','output':a.output,'sha256':sha(a.output)}),flush=True)
if __name__=='__main__':main()
