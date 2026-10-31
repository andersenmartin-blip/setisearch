"""BZ nested drift-grid ablation, preserving the closed BY factor-one arm.

Only fourteen new rates in the same bounded interval are scored per case.
The three coarse anchors and all their seed/projection results are reused
byte-for-byte from BY. No import-time observation access occurs.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import os
import signal
import sys
from datetime import datetime, timezone

for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
sys.dont_write_bytecode=True
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BY_SOURCE=ROOT/'work_by/inject_recover.py'
BY_SOURCE_SHA='8260c03c757dc36763f70cf0dd82b0b9553788f7cdca84d7d74636e6e962e0c8'
WIDTHS=(1,3,9,33)
STRIDES=(1,1,2,8)
ANCHORS=(0,8,16)
NEW_INDICES=tuple(i for i in range(17) if i not in ANCHORS)
LABELS=('THREE_ON_FAIL','REJECTED_AVAILABLE_OFF','INCOMPLETE_OFF_COVERAGE','UNSUPPORTED')
CONFIG={
    'q':254,'factors':[1,2,4,8],'new_factors':[2,4,8],
    'union_factor':8,'union_rates_per_case':17,'new_rates_per_case':14,
    'coarse_anchor_refined_indices':list(ANCHORS),
    'base_drift_indices':[314,419,524],
    'original_grid_rates':839,'original_max_abs_drift_hz_s':4.0,
    'new_correlated_track_combinations':198696960,
    'reused_baseline_track_combinations':42577920,
    'union_nominal_track_combinations':241274880,
    'new_calibration_vectors':73920,'reused_calibration_vectors':15840,
    'case_count':264,'geometry_count':24,'injected_matrices':1320,
    'source_match_max_original_rate_steps':1.0,'rate_match_tolerance_hz_s':1e-12,
    'association_radius':'ceil(1+0.5*ORIGINAL_rate_step*abs(scan_gap)/abs(df_hz))',
    'refined_radius_used':False,'source_selection':'All truth-matched scan0 local peaks',
    'kernel_widths':list(WIDTHS),'kernel_strides':list(STRIDES),
    'threshold_ON':10.0,'threshold_available_OFF':5.0,
    'injection_model':'Exact pinned BY exposure-integrated triangular deposition after normalization',
    'coarse_results_policy':'Reuse exact closed BY calibration, seeds, projections, scores and statuses; no coarse detector rerun',
    'nested_grid_policy':'Construct factor8 piecewise linspace between exact adjacent original anchors; smaller factors are subsets',
    'max_matched_seeds_per_case':512,
    'new_observations':False,'new_SETI_searches':0,'calibrated_astronomical_sensitivity':False,
    'method_selected_after_BY_results':True,
}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text())

def write(path,value):
    with Path(path).open('x') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())

def load_by():
    require(sha(BY_SOURCE)==BY_SOURCE_SHA,'Pinned BY production source differs')
    spec=importlib.util.spec_from_file_location('bz_exact_by_model',BY_SOURCE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def refined_bank(original,base):
    """One nested union; preserve all three coarse float64 values exactly."""
    rates=np.concatenate([np.linspace(original[base-1],original[base],9,dtype=np.float64)[:-1],
                          np.linspace(original[base],original[base+1],9,dtype=np.float64)])
    require(np.array_equal(rates[list(ANCHORS)],original[base-1:base+2]),'Coarse anchor bytes differ')
    require(np.all(np.diff(rates)>0),'Nonmonotone refined grid')
    return rates

def factor_indices(factor):
    require(factor in CONFIG['factors'],'Unsupported refinement factor')
    return tuple(range(0,17,8//factor))

def group_cases(cases):
    result=[]
    for presence in ('ZERO_CONTROL','ON_ONLY','ALL_FIVE'):
        for amplitude in ([0.0] if presence=='ZERO_CONTROL' else [1.,2.,4.,8.,16.]):
            selected=[x for x in cases if x['presence']==presence and x['amplitude']==amplitude]
            result.append({'presence':presence,'amplitude':amplitude,'geometries':len(selected),
                'source_recovered':sum(x['matched_source_seed_rows']>0 for x in selected),
                'three_ON_recovered':sum(x['three_ON_recovered'] for x in selected),
                'available_OFF_rejected':sum(x['available_OFF_rejected'] for x in selected),
                'retained_partial':sum(x['retained_partial'] for x in selected),
                'both_retained_and_rejected':sum(x['both_retained_and_rejected'] for x in selected)})
    return result

def summarize_case(case,seeds,status,center,factor):
    chosen=np.array([i for i,s in enumerate(seeds) if s['refined_index'] in factor_indices(factor)],dtype=np.int64)
    states=status[chosen]
    on=((center[chosen][:,[0,2,4]]>=10).all(axis=1)) if len(chosen) else np.zeros(0,dtype=bool)
    return dict(case,grid_factor=factor,bank_refined_indices=list(factor_indices(factor)),
                matched_source_seed_rows=len(chosen),three_ON_recovered=bool(on.any()),
                available_OFF_rejected=bool((states=='REJECTED_AVAILABLE_OFF').any()),
                retained_partial=bool((states=='INCOMPLETE_OFF_COVERAGE').any()),
                both_retained_and_rejected=bool((states=='REJECTED_AVAILABLE_OFF').any() and (states=='INCOMPLETE_OFF_COVERAGE').any()),
                status_counts={label:int((states==label).sum()) for label in LABELS})

def baseline_case(value):
    return {k:v for k,v in value.items() if k not in ('grid_factor','bank_refined_indices','both_retained_and_rejected')}

def compare_cases(results,baseline):
    result={}
    for event in ('source_recovered','three_ON_recovered','available_OFF_rejected','retained_partial'):
        flag=lambda case:case['matched_source_seed_rows']>0 if event=='source_recovered' else case[event]
        result[event]={'gained_case_indices':[x['case_index'] for x,old in zip(results,baseline) if flag(x) and not flag(old)],
                       'lost_case_indices':[x['case_index'] for x,old in zip(results,baseline) if flag(old) and not flag(x)]}
    return result

def validate(plan,freeze_path):
    require(plan['schema']=='SETI_BZ_NESTED_DRIFT_GRID_V1' and plan['config']==CONFIG,'Wrong prospective BZ method')
    require(np.__version__=='2.3.5','NumPy runtime differs')
    for p,h in plan['source_sha256'].items():require(sha(p)==h,'Frozen source/metadata differs: '+p)
    required=[str(Path(__file__).resolve()),str(BY_SOURCE),str(ROOT/'work_bo/vendor/current/kernel_v.py'),str(ROOT/'work_bu/partial_search.py')]
    require(all(p in plan['source_sha256'] for p in required),'Numerical dependency not pinned')
    parent=read(plan['parent_BY_plan_path'])
    require(sha(plan['parent_BY_plan_path'])==plan['parent_BY_plan_sha256'],'Parent BY plan changed')
    require(plan['scans']==parent['scans'] and plan['inputs']==parent['inputs'],'Parent scan geometry or input bindings differ')
    for item in plan['inputs']:
        p=Path(item['path']);require(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'Background bytes differ')
    base=plan['baseline']
    for key in ('summary','arrays','cases','review'):
        require(sha(base[key+'_path'])==base[key+'_sha256'],'Closed baseline '+key+' differs')
    summary=read(base['summary_path']);review=read(base['review_path'])
    require(summary['status']=='PASS_CONDITIONAL_INJECTION_RECOVERY','Invalid baseline status')
    require(review['status']=='PASS_INDEPENDENT_INJECTION_REVIEW' and review['all_bound_bytes_unchanged'],'Baseline independent review failed')
    require(review['production_summary_sha256']==base['summary_sha256'] and review['arrays_sha256']==base['arrays_sha256']==summary['arrays_sha256'],'Baseline proof binding differs')
    freeze=read(freeze_path)
    require(freeze['exact_readback_verified'] and len(freeze['public_commit'])==40,'Public exact-readback freeze required')
    return parent,summary,freeze

def run(plan_path,freeze_path,out):
    plan_path,freeze_path,out=map(Path,(plan_path,freeze_path,out));plan_hash=sha(plan_path);plan=read(plan_path)
    parent,baseline_summary,freeze=validate(plan,freeze_path)
    require(freeze['plan_sha256']==plan_hash,'Freeze does not bind plan')
    require(out.is_absolute() and str(out).startswith('/dev/shm/') and not out.exists(),'Fresh exclusive tmpfs output required')
    out.mkdir(parents=True)
    by=load_by();kernel,classifier=by.load_components();cases=by.build_cases(parent)
    require(read(plan['baseline']['cases_path'])['cases']==cases,'Saved BY case definitions differ')
    write(out/'CASES_BZ.json',{'schema':'SETI_BZ_CASES_V1','cases':cases,'config':CONFIG})
    with np.load(plan['baseline']['arrays_path'],allow_pickle=False) as archive:
        prior={k:archive[k] for k in archive.files}
    require(prior['calibration'].shape==(264,5,3,4,2) and prior['injected_sha256'].shape==(264,5),'Baseline array shape differs')
    backgrounds=[]
    for item in plan['inputs']:
        y=np.load(item['path'],allow_pickle=False)
        require(y.dtype==np.float32 and y.shape==(16,12288) and y.flags.c_contiguous and np.isfinite(y).all(),'Invalid normalized background')
        backgrounds.append(y)
    original=np.linspace(-4,4,839,dtype=np.float64);old_step=float(original[1]-original[0])
    banks={base:refined_bank(original,base) for base in CONFIG['base_drift_indices']}
    times=(np.arange(16,dtype=np.float64)-7.5)*plan['scans'][0]['dt_seconds']
    offsets={b:np.rint(rates[:,None]*times[None,:]/plan['scans'][0]['df_hz']).astype(np.int32) for b,rates in banks.items()}
    calibration=np.empty((264,5,17,4,2),dtype=np.float64)
    for coarse,ri in enumerate(ANCHORS):calibration[:,:,ri,:,:]=prior['calibration'][:,:,coarse,:,:]
    injected_hashes=np.empty((264,5),dtype='<U64')
    all_seeds=[];all_center=[];all_max=[];all_valid=[];all_pred=[];all_status=[]
    arm_cases={f:[] for f in CONFIG['factors']};computed=0;copied_rows=0
    for case in cases:
        ci=case['case_index'];base_index=case['base_drift_index'];rates=banks[base_index];off=offsets[base_index]
        seeds=[];matrices=[];source_scope=plan['scans'][0]
        for old_row in np.flatnonzero(prior['seed_case_index']==ci):
            coarse=int(prior['seed_drift_index'][old_row])-base_index+1
            require(coarse in (0,1,2),'Baseline seed outside original bank')
            seeds.append({'case_index':ci,'refined_index':ANCHORS[coarse],
                'coarse_drift_index':int(prior['seed_drift_index'][old_row]),'baseline_row':int(old_row),
                'center_native':int(prior['seed_center_native'][old_row]),'width':int(prior['seed_width'][old_row]),
                'ess':float(prior['seed_ess'][old_row]),'drift_hz_s':float(rates[ANCHORS[coarse]])})
        for scan,(scope,item,background) in enumerate(zip(plan['scans'],plan['inputs'],backgrounds)):
            sparse=by.unit_injection(case,scope,source_scope,item,background.shape)
            active=case['presence']=='ALL_FIVE' or (case['presence']=='ON_ONLY' and scan%2==0)
            matrix=by.inject(background,sparse,case['amplitude'],active);matrices.append(matrix)
            digest=hashlib.sha256(matrix.tobytes(order='C')).hexdigest()
            require(digest==prior['injected_sha256'][ci,scan],'Injected matrix differs from closed BY realization')
            injected_hashes[ci,scan]=digest
            start=254*4096-item['support_start'];stop=start+4096
            for wi,(width,stride) in enumerate(zip(WIDTHS,STRIDES)):
                prepared=kernel.boxcars(matrix,width);centers=np.arange(start,stop,stride,dtype=np.int32)
                for ri in NEW_INDICES:
                    sums=kernel.tracks_grid(matrix,prepared,off[ri],start,stop,stride,width)[0]
                    med=float(np.median(sums));scale=float(1.4826*np.median(np.abs(sums-med)))
                    require(math.isfinite(scale) and scale>0,'Invalid full-core MAD')
                    calibration[ci,scan,ri,wi]=[med,scale];computed+=len(centers)
                    score=(sums-med)/scale;require(np.isfinite(score).all(),'Nonfinite ESS')
                    if scan==0 and abs(float(rates[ri])-case['true_drift_hz_s'])<=old_step+1e-12:
                        mask=(score>=10)&by.local_peak_mask(score,max(3,2*math.ceil(width/stride)+1))
                        mask &= np.abs(centers+item['support_start']-case['true_center_native_at_scan0_midpoint'])<=width//2+2
                        for k in np.flatnonzero(mask):
                            seeds.append({'case_index':ci,'refined_index':ri,'coarse_drift_index':-1,'baseline_row':-1,
                                'center_native':int(centers[k])+item['support_start'],'width':width,'ess':float(score[k]),'drift_hz_s':float(rates[ri])})
        seeds.sort(key=lambda s:(WIDTHS.index(s['width']),s['refined_index'],s['center_native']))
        n=len(seeds);require(n<=CONFIG['max_matched_seeds_per_case'],'Bounded matched seed cap reached')
        center=np.full((n,6),np.nan);maximum=np.full((n,6),np.nan);valid=np.zeros((n,6),dtype=bool)
        predicted=np.full((n,6),-1,dtype=np.int32);statuses=np.empty(n,dtype='<U28')
        old_local=[];new_local=[]
        for i,seed in enumerate(seeds):
            if seed['baseline_row']>=0:
                old=seed['baseline_row'];old_local.append(i);copied_rows+=1
                center[i]=prior['center_scores'][old];maximum[i]=prior['max_scores'][old]
                valid[i]=prior['valid'][old];predicted[i]=prior['predicted_native'][old];statuses[i]=prior['candidate_status'][old]
            else:new_local.append(i)
        for scan,(scope,item,matrix) in enumerate(zip(plan['scans'],plan['inputs'],matrices)):
            gap=(scope['tref_midpoint_mjd']-source_scope['tref_midpoint_mjd'])*86400
            radius=math.ceil(1+.5*old_step*abs(gap)/abs(scope['df_hz']))
            for wi,width in enumerate(WIDTHS):
                selected=[i for i in new_local if seeds[i]['width']==width]
                if not selected:continue
                prepared=kernel.boxcars(matrix,width)
                for i in selected:
                    seed=seeds[i];ri=seed['refined_index'];rate=rates[ri]
                    frequency=source_scope['fch1_mhz']+seed['center_native']*source_scope['df_hz']/1e6
                    frequency+=rate*gap/1e6
                    native=int(np.rint((frequency-scope['fch1_mhz'])*1e6/scope['df_hz']))
                    c=native-item['support_start'];predicted[i,scan]=native
                    require(c+int(off[ri].min())-width//2-radius>=0 and c+int(off[ri].max())+width//2+radius<matrix.shape[1],'Projected track outside support')
                    requested=np.arange(c-radius,c+radius+1,dtype=np.int32)
                    sums=kernel.tracks_selected(matrix,prepared,off[ri],requested,width)[0]
                    med,scale=calibration[ci,scan,ri,wi];score=(sums-med)/scale
                    center[i,scan]=score[radius];maximum[i,scan]=score.max();valid[i,scan]=True
        if new_local:
            ii=np.asarray(new_local,dtype=np.int64)
            require(np.array_equal(center[ii,0],np.array([seeds[i]['ess'] for i in new_local])),'Source projection differs from source catalog')
            statuses[ii]=classifier(center[ii],maximum[ii],valid[ii])['candidate_status']
        require(not valid[:,5].any() and np.isnan(center[:,5]).all() and np.isnan(maximum[:,5]).all(),'Missing OFF5 changed')
        for factor in CONFIG['factors']:
            value=summarize_case(case,seeds,statuses,center,factor);arm_cases[factor].append(value)
            if factor==1:require(baseline_case(value)==baseline_summary['cases'][ci],'Reused baseline case differs')
        for left,right in zip(CONFIG['factors'][:-1],CONFIG['factors'][1:]):
            a,b=arm_cases[left][-1],arm_cases[right][-1]
            for key in ('three_ON_recovered','available_OFF_rejected','retained_partial'):
                require(not a[key] or b[key],'Nested arm lost a retained seed event')
            require(a['matched_source_seed_rows']<=b['matched_source_seed_rows'],'Nested source seeds decreased')
        all_seeds.extend(seeds);all_center.append(center);all_max.append(maximum);all_valid.append(valid);all_pred.append(predicted);all_status.append(statuses)
        if (ci+1)%11==0:print(json.dumps({'event':'GEOMETRY_COMPLETE','geometry':case['geometry'],'cases_completed':ci+1}),flush=True)
    require(computed==CONFIG['new_correlated_track_combinations'],'New track count differs')
    require(copied_rows==len(prior['seed_case_index'])==baseline_summary['matched_seed_rows'],'Baseline seed row count differs')
    arrays={'calibration':calibration,'injected_sha256':injected_hashes,
        'base_drift_indices':np.array(CONFIG['base_drift_indices'],dtype=np.int32),
        'rate_grid_by_base':np.array([banks[b] for b in CONFIG['base_drift_indices']]),
        'center_scores':np.concatenate(all_center),'max_scores':np.concatenate(all_max),'valid':np.concatenate(all_valid),
        'predicted_native':np.concatenate(all_pred),'candidate_status':np.concatenate(all_status)}
    for key,dtype in [('case_index',np.int32),('refined_index',np.int16),('coarse_drift_index',np.int32),('baseline_row',np.int32),('center_native',np.int32),('width',np.int16),('ess',np.float64),('drift_hz_s',np.float64)]:
        arrays['seed_'+key]=np.asarray([s[key] for s in all_seeds],dtype=dtype)
    with (out/'RESULT_ARRAYS_BZ.npz').open('xb') as f:np.savez_compressed(f,**arrays);f.flush();os.fsync(f.fileno())
    arms=[]
    for factor in CONFIG['factors']:
        results=arm_cases[factor];groups=group_cases(results)
        if factor==1:require([{k:v for k,v in g.items() if k!='both_retained_and_rejected'} for g in groups]==baseline_summary['groups'],'Reused baseline groups differ')
        comparison=compare_cases(results,baseline_summary['cases'])
        arms.append({'factor':factor,'rates':len(factor_indices(factor)),'cases':results,'groups':groups,'comparison_with_BY':comparison})
    validate(plan,freeze_path);require(sha(plan_path)==plan_hash,'Plan changed')
    result={'schema':'SETI_BZ_NESTED_GRID_RESULT_V1','status':'PASS_NESTED_GRID_ABLATION','plan_sha256':plan_hash,
        'public_freeze_commit':freeze['public_commit'],'baseline_summary_sha256':plan['baseline']['summary_sha256'],
        'baseline_arrays_sha256':plan['baseline']['arrays_sha256'],'case_count':264,'geometry_count':24,
        'injected_matrices_verified_exactly':1320,'coarse_seed_rows_reused':copied_rows,
        'union_matched_seed_rows':len(all_seeds),'new_matched_seed_rows':len(all_seeds)-copied_rows,
        'new_calibration_vectors':73920,'reused_calibration_vectors':15840,
        'new_correlated_track_combinations':computed,'reused_baseline_track_combinations':42577920,
        'union_nominal_track_combinations':241274880,'arms':arms,
        'association_radius_unchanged':True,'source_truth_matching_tolerance_unchanged':True,
        'baseline_scoring_rerun':False,'arrays_sha256':sha(out/'RESULT_ARRAYS_BZ.npz'),
        'new_SETI_searches':0,'new_original_coverage':0,'new_observational_coverage':0,
        'calibrated_astronomical_sensitivity':False,'full_cadence_status':'NOT_EVALUABLE_MISSING_OFF5',
        'independent_audit_pending':True,'completed_utc':datetime.now(timezone.utc).isoformat(),
        'limits':['Refinement was proposed after inspecting BY; same previously exposed deterministic cases/backgrounds, not an independent validation set.',
                  'Known-truth local drift interval and source matching; not full-bank blind recovery or astronomical sensitivity.',
                  'Added templates increase correlated trials. Fixed ESS thresholds have not been recalibrated to a common global false-alarm probability.',
                  'Keeping coarse seeds makes recovery monotonic by construction; quantitative gains, controls and OFF rejection are the measured outcomes.',
                  'Rejected and retained statuses can coexist across different seed rows of one case; these case-level counts need not sum.',
                  'Old OFF neighborhood radius and all other BY settings are fixed; this isolates added rates rather than radius narrowing.',
                  'No new observation, no Jy calibration, no normalization-response test, no complete OFF5 cadence qualification.']}
    write(out/'SUMMARY_BZ.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True,type=Path);p.add_argument('--freeze',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    def expired(signum,frame):raise TimeoutError('BZ 600-second worker budget reached')
    signal.signal(signal.SIGALRM,expired);signal.alarm(600)
    result=run(a.plan,a.freeze,a.out);signal.alarm(0)
    print(json.dumps({'status':result['status'],'new_tracks':result['new_correlated_track_combinations'],'union_seed_rows':result['union_matched_seed_rows']}),flush=True)
