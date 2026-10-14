#!/usr/bin/env python3
"""Frozen raw-power injection -> full-core normalization -> local native rank.

Only prepare() is permitted before root GO. It reads JSON metadata and hashes
source bytes, never opens arrays. run() executes every frozen case once using
the original single-native-bin four-row statistic and the same exact family.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import resource
import signal
import time
from collections import Counter, defaultdict
from pathlib import Path

for var in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[var] = '1'

NORM_FIELDS = ('row_power_median','row_residual_median','row_residual_MAD_scale','row_winsorized_residual_location')
HOSTS = (-640,640)
AMPLITUDES = (2,8)
MODELS = ('delta','fixed3','integration_smear')
DC = (178782208,179830784,180879360)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):
            h.update(block)
    return h.hexdigest()


def pin(path,root):
    path = Path(path)
    return {'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}


def write_json(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')


def cell(value):
    return json.dumps(value,separators=(',',':'),allow_nan=False)


def write_csv(path,records):
    require(bool(records),'Empty output table')
    with Path(path).open('x',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]))
        writer.writeheader();writer.writerows(records)


def flatten_family(family,host):
    import numpy as np
    bins,rows,windows=[],[],[]
    seen=set()
    for w in family['windows']:
        for p in w['paths']:
            channels=tuple(c+host for c in p['channels'])
            identity=(tuple(w['window_source_rows']),channels)
            require(identity not in seen,'Frozen native family duplicate')
            seen.add(identity);bins.append(channels);rows.append(w['window_source_rows']);windows.append(w['window_index'])
    bins=np.asarray(bins,dtype=np.int64);rows=np.asarray(rows,dtype=np.int64)
    return {'absolute_channels':bins,'path_source_rows':rows,'path_window_index':np.asarray(windows,dtype=np.int64),
            'path_dc_mask':np.isin(bins,np.asarray(DC,dtype=np.int64)).any(axis=1)}


def recompute_row_normal(raw_row):
    """Original4096 core and direct501 median; no injection-dependent crop."""
    import numpy as np
    power=raw_row.astype(np.float64)
    level=float(np.median(power[4000:8096]))
    require(level>0 and np.isfinite(level),'Invalid row power median')
    ratio=power[3750:8346]/level
    windows=np.lib.stride_tricks.sliding_window_view(ratio,501)
    filtered=np.empty(4096,dtype=np.float64)
    for start in range(0,4096,256):
        stop=min(start+256,4096)
        filtered[start:stop]=np.median(windows[start:stop],axis=1)
    residual=ratio[250:4346]-filtered
    center=float(np.median(residual))
    scale=float(1.4826*np.median(np.abs(residual-center)))
    require(scale>0 and np.isfinite(scale),'Invalid residual MAD scale')
    location=float(center+np.mean(np.clip(residual-center,-5*scale,5*scale)))
    return dict(zip(NORM_FIELDS,(level,center,scale,location)))


def path_row_terms(raw_row,row_normal,absolute_centers,channel0):
    """Direct median501 at unique requested centers; unchanged width1 score."""
    import numpy as np
    local=np.asarray(absolute_centers,dtype=np.int64)-channel0
    require(local.min()>=250 and local.max()+250<len(raw_row),'Missing raw501 support')
    unique,inverse=np.unique(local,return_inverse=True)
    ratio=raw_row.astype(np.float64)/row_normal['row_power_median']
    windows=np.lib.stride_tricks.sliding_window_view(ratio,501)
    median=np.median(windows[unique-250],axis=1)
    residual=(ratio[unique]-median-row_normal['row_winsorized_residual_location'])/row_normal['row_residual_MAD_scale']
    return residual[inverse]


def score_paths(raw,normal,arrays,channel0,baseline_terms=None,changed_rows=None):
    import numpy as np
    rows=arrays['path_source_rows'];bins=arrays['absolute_channels']
    terms=np.empty(bins.shape,dtype=np.float64) if baseline_terms is None else baseline_terms.copy()
    for row in range(16) if changed_rows is None else changed_rows:
        where=rows==row
        require(where.any(),'Active source row missing from family')
        row_normal={key:float(normal[key][row]) for key in NORM_FIELDS}
        terms[where]=path_row_terms(raw[row],row_normal,bins[where],channel0)
    return terms,terms.sum(axis=-1,dtype=np.float64)/2.0


def raw_hash(raw):
    import numpy as np
    require(raw.dtype==np.dtype('<f4') and raw.shape==(16,12096),'Raw hash contract differs')
    return hashlib.sha256(np.ascontiguousarray(raw).tobytes(order='C')).hexdigest()


def apply_injection(raw,saved_normal,kernels,amplitude,channel0):
    """Float64 addition per supplied kernel cell, then canonical float32 cast."""
    import numpy as np
    modified64=raw.astype(np.float64)
    actual=[]
    for kernel in kernels:
        row=kernel['source_row']
        channels=np.asarray(kernel['absolute_channels'],dtype=np.int64)
        weights=np.asarray(kernel['weights'],dtype=np.float64)
        require(len(channels)==len(weights)>0 and len(set(channels.tolist()))==len(channels),'Invalid kernel cells')
        require(np.isfinite(weights).all() and (weights>0).all() and abs(float(weights.sum())-1)<1e-12,'Invalid row kernel mass')
        local=channels-channel0
        require(local.min()>=0 and local.max()<12096,'Injection kernel outside raw source')
        increment=amplitude*float(saved_normal['row_power_median'][row])*float(saved_normal['row_residual_MAD_scale'][row])*weights
        before=raw[row,local].astype(np.float64)
        modified64[row,local]=before+increment
        rounded=(before+increment).astype('<f4')
        actual.append({'source_row':row,'absolute_channels':channels.tolist(),
                       'requested_power_increment':increment.tolist(),
                       'actual_float32_power_increment':(rounded.astype(np.float64)-before).tolist()})
    modified=modified64.astype('<f4')
    require(np.isfinite(modified).all() and (modified>=0).all(),'Negative/nonfinite raw modification')
    return modified,actual


def ranked(arrays,scores,geometry):
    import numpy as np
    bins=arrays['absolute_channels'];rows=arrays['path_source_rows']
    eligible=~arrays['path_dc_mask'];idx=np.flatnonzero(eligible)
    truth_cells=dict(zip(geometry['true_active_source_rows'],geometry['truth_active4']))
    matches=np.asarray([[truth_cells.get(int(r))==int(c) for r,c in zip(rs,cs)] for rs,cs in zip(rows,bins)],dtype=bool)
    counts=matches.sum(axis=1,dtype=np.int64)
    truth=np.flatnonzero(eligible&(counts==4))
    require(len(truth)==1,'Complete designated central truth path not unique')
    ti=int(truth[0])
    order=idx[np.lexsort((bins[idx,3],bins[idx,2],bins[idx,1],bins[idx,0],rows[idx,0],-scores[idx]))]
    wi=int(order[0]);truth_score=float(scores[ti])
    equal=int(np.count_nonzero(scores[eligible]==truth_score));greater=int(np.count_nonzero(scores[eligible]>truth_score))
    partial=int(order[counts[order]<4][0])
    result={'truth_path_index':ti,'truth_path_count':1,'truth_score':truth_score,
            'truth_rank_min':greater+1,'truth_rank_max':greater+equal,'truth_rank_tie_count':equal,
            'truth_deterministic_rank':int(np.flatnonzero(order==ti)[0])+1,
            'truth_retained_top1':bool(ti in order[:1]),'truth_retained_top5':bool(ti in order[:5]),
            'winner_path_index':wi,'winner_window_index':int(arrays['path_window_index'][wi]),
            'winner_score':float(scores[wi]),'winner_matching_central_truth_cells':int(counts[wi]),
            'winner_minus_truth_score':float(scores[wi]-truth_score),
            'best_partial_path_index':partial,'best_partial_score':float(scores[partial]),
            'truth_minus_best_partial_score':float(truth_score-scores[partial]),
            'retained_top5_indices':cell(order[:5].tolist()),'retained_top5_scores':cell(scores[order[:5]].tolist()),
            'retained_top5_central_truth_matches':cell(counts[order[:5]].tolist()),
            'retained_count_top1':1,'retained_count_top5':5,'eligible_unique_hypotheses':len(idx)}
    return result,order[:5],counts,ti


def prepare(args):
    here=Path(__file__).resolve().parent;root=args.input_root.resolve()
    manifest_path=here/'GEOMETRY_MANIFEST.json';manifest=read(manifest_path)
    require(len(manifest['geometries'])==108,'Expected frozen108 placements')
    matrix_path=root/'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
    geometry_path=root/'rounding_followup/exact_geometry_results/GEOMETRY.json'
    matrix=read(matrix_path)
    require(len(matrix['profiles'])==54,'Frozen profile census differs')
    inputs={p['path']:p for p in (pin(matrix_path,root),pin(geometry_path,root),
        pin(root/'rounding_followup/results/INJECTIONS.json',root))}
    for profile in matrix['profiles']:
        for key in ('raw_normalization_crop','normalization'):
            declaration=profile[key];path=root/'seti_work'/declaration['path']
            require(path.stat().st_size==declaration['bytes'] and sha(path)==declaration['sha256'],'Raw source metadata pin differs')
            inputs[str(path.relative_to(root))]=pin(path,root)
    scope={'schema':'SETI_RAW_NORMALIZATION_RETENTION_SCOPE_V1','date':'2026-10-14',
        'status':'METADATA_READY_AWAITING_ROOT_GO','input_root':str(root),'input_pins':list(inputs.values()),
        'producer_pin':pin(Path(__file__).resolve(),here),'geometry_manifest_pin':pin(manifest_path,here),
        'prior_placement_manifest_pin':pin(here/'prior_placements/GEOMETRY_MANIFEST_TOP5.json',here),
        'metadata_builder_pin':{'path':str(here.parent/'raw_retention_design/build_manifest.py'),
            'sha256':sha(here.parent/'raw_retention_design/build_manifest.py')},
        'original_generator_pin':pin(here/'source_provenance/generator_original.py',here),
        'profile_count':54,'geometry_count':108,'raw_case_count':648,'baseline_rank_count':108,
        'fixed_amplitudes':list(AMPLITUDES),'fixed_models':list(MODELS),'fixed_hosts':list(HOSTS),
        'normalization':{'core_local_half_open':[4000,8096],'median_filter_width':501,'MAD_multiplier':1.4826,
            'winsor_scale_multiple':5,'baseline_all16_rows_recomputed_and_authenticated':True,
            'case_modified4_rows_recomputed_other12_recomputed_authenticated_baseline_rows_reused':True,
            'baseline_authentication_tolerance':{'row_power_median':0.0,'other_normal_fields':1e-12}},
        'injection':{'domain':'raw float32 power','addition':'float64 prior power + A*original saved row power median*original saved row residual MAD*row kernel weight, then float32 cast',
            'amplitude_reference':'total row kernel mass on frozen original normalization, not output SNR or fixed central-bin amplitude',
            'raw_modified_hash':'SHA256 of complete16x12096 C-order little-endian float32 raw_power bytes'},
        'policy':{'k':5,'comparison_k':1,'score':'original width1 native four-row standardized sum/2',
            'family':'same exact local family across7 existing windows shifted host; no width3 or smeared matched statistic',
            'truth':'designated exact nearest-even central bin in all4 active rows, fixed even for spread kernels',
            'tie_order':'descending score, ascending window start, lexicographic native4',
            'A0':'108 separate baseline sham-target ranks; no separate kernel baseline replicates'},
        'resource_envelope':{'reserved_CPU_s':600,'metadata_CPU_s_cap':60,'producer_CPU_s_cap':270,
            'QA_CPU_s_cap':270,'wall_s_cap_each':600,'memory_bytes_cap_each':2147483648,
            'output_bytes_cap':40000000,'max_numerical_jobs':2,'cost_DKK':0},
        'interpretation':['Algorithm stress control on exposed2017 source crops; no new observation.',
            'Delta and fixed3 are declared stress kernels, not asserted instrument responses.',
            'Integration smear is the original idealized linear-exposure/intrinsic1-bin generator; no measured instrumental line response.',
            'Local refinement remains conditioned on previously selected top9; placements and paired kernels/amplitudes are dependent.',
            'No physical FAP/sensitivity or original full6scan-chain pilot gate pass.'],
        'preserved':{'qualified_SETI_detection':False,'original_A_B':'FAIL_CLOSED','full6scan_chain_gate_pass':False,
                     'new_observation':False,'new_telescope_requests':0,'new_telescope_bytes':0,'protected_2016':True,'closed_2019':True}}
    write_json(here/'SCOPE.json',scope)
    print(cell({'status':scope['status'],'scope_sha256':sha(here/'SCOPE.json'),'raw_case_count':648}))


def run(args):
    started_cpu=time.process_time();started_wall=time.monotonic()
    here=Path(__file__).resolve().parent;scope_path=here/'SCOPE.json';scope=read(scope_path)
    require(sha(scope_path)==args.go_scope_sha256,'Frozen root scope digest differs')
    go=read(here/'GO.json')
    require(go['scope_sha256']==sha(scope_path) and go['producer_sha256']==sha(Path(__file__).resolve())
            and scope['producer_pin']['sha256']==sha(Path(__file__).resolve()),'Root producer GO hashes differ')
    budget=scope['resource_envelope']
    resource.setrlimit(resource.RLIMIT_CPU,(budget['producer_CPU_s_cap'],budget['producer_CPU_s_cap']))
    resource.setrlimit(resource.RLIMIT_AS,(budget['memory_bytes_cap_each'],budget['memory_bytes_cap_each']))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Raw producer wall cap exceeded')))
    signal.alarm(budget['wall_s_cap_each'])
    root=args.input_root.resolve() if args.input_root else Path(scope['input_root'])
    for declaration in scope['input_pins']:
        path=root/declaration['path']
        require(path.stat().st_size==declaration['bytes'] and sha(path)==declaration['sha256'],'Frozen source differs: '+declaration['path'])
    manifest_path=here/scope['geometry_manifest_pin']['path']
    require(sha(manifest_path)==scope['geometry_manifest_pin']['sha256']==go['metadata_manifest_sha256'],'Frozen metadata manifest differs')
    manifest=read(manifest_path)
    for key in ('prior_placement_manifest_pin','original_generator_pin'):
        declaration=scope[key];path=here/declaration['path']
        require(path.stat().st_size==declaration['bytes'] and sha(path)==declaration['sha256'], 'Frozen stage provenance differs: '+key)
    matrix=read(root/'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json')
    families={p['profile_id']:p for p in read(root/'rounding_followup/exact_geometry_results/GEOMETRY.json')['profiles']}
    grouped=defaultdict(list)
    for g in manifest['geometries']:grouped[g['profile_id']].append(g)
    require(len(grouped)==54 and all(len(v)==2 for v in grouped.values()),'Raw panel geometry grouping differs')
    import numpy as np
    out=args.output_root.resolve()
    require(not out.exists() and not out.is_relative_to(root),'Fresh result directory outside source required')
    out.mkdir(parents=True);(out/'baselines').mkdir();(out/'cases').mkdir()
    case_rows=[];baseline_rows=[];normal_rows=[];retained_rows=[];case_metadata=[];baseline_metadata=[]
    for pi,profile in enumerate(matrix['profiles']):
        pid=profile['profile_id'];family=families[pid]
        with np.load(root/'seti_work'/profile['raw_normalization_crop']['path'],allow_pickle=False) as z:
            raw=z['raw_power'];channel0=int(z['source_channel0'])
            require(raw.shape==(16,12096) and raw.dtype==np.dtype('<f4') and np.isfinite(raw).all(),'Raw source invalid')
            require(np.array_equal(z['absolute_time_rows'],np.arange(16)) and
                    np.array_equal(z['normalization_source_channels'],np.arange(channel0+4000,channel0+8096)),'Raw crop coordinates differ')
        saved=read(root/'seti_work'/profile['normalization']['path'])
        saved_normal={key:np.asarray(saved[key],dtype=np.float64) for key in NORM_FIELDS}
        computed={key:np.empty(16,dtype=np.float64) for key in NORM_FIELDS}
        for row in range(16):
            nr=recompute_row_normal(raw[row])
            for key in NORM_FIELDS:computed[key][row]=nr[key]
        errors={key:float(np.max(np.abs(computed[key]-saved_normal[key]))) for key in NORM_FIELDS}
        require(errors['row_power_median']==0 and all(errors[key]<=1e-12 for key in NORM_FIELDS[1:]),'Original full-core normalization authentication failed')
        require(np.array_equal(np.asarray(saved['normalization_source_channels']),np.arange(channel0+4000,channel0+8096)), 'Saved normalization coordinates differ')
        require(np.array_equal(np.asarray(saved['normalization_unmasked_counts']),np.full(16,4096)), 'Saved core counts differ')
        normal=computed
        raw_base_hash=raw_hash(raw)
        baselines={};baseline_arrays={'offset_channels':np.asarray(HOSTS,dtype=np.int64),**normal,
            **{'saved_'+key:value for key,value in saved_normal.items()}}
        for host in HOSTS:
            arrays=flatten_family(family,host)
            terms,scores=score_paths(raw,normal,arrays,channel0)
            baselines[host]=(arrays,terms,scores)
        baseline_arrays.update({'absolute_channels':np.stack([baselines[h][0]['absolute_channels'] for h in HOSTS]),
            'path_source_rows':baselines[HOSTS[0]][0]['path_source_rows'],
            'path_window_index':baselines[HOSTS[0]][0]['path_window_index'],
            'path_dc_mask':np.stack([baselines[h][0]['path_dc_mask'] for h in HOSTS]),
            'residual_row_terms':np.stack([baselines[h][1] for h in HOSTS]),
            'scores':np.stack([baselines[h][2] for h in HOSTS])})
        baseline_path=out/'baselines'/(pid+'.npz')
        with baseline_path.open('xb') as stream:np.savez_compressed(stream,**baseline_arrays)
        baseline_metadata.append({'profile_id':pid,'raw_source_power_bytes_sha256':raw_base_hash,
            'normalization_authentication_max_absolute_errors':errors,'arrays':pin(baseline_path,out)})
        for g in grouped[pid]:
            host=g['host_offset_channels'];arrays,base_terms,base_scores=baselines[host]
            base_rank,_,_,ti=ranked(arrays,base_scores,g)
            common={'geometry_id':g['geometry_id'],'profile_id':pid,'origin_scan_id':g['origin_scan_id'],
                'context_scan_id':g['context_scan_id'],'origin_rank':g['origin_rank'],'host_offset_channels':host,
                'true_window_index':g['true_window_index'],'true_active_source_rows':cell(g['true_active_source_rows']),
                'truth_active4':cell(g['truth_active4']),'central_bins_in_core':g['central_bins_in_core'],
                'central_truth_core_class':'ALL_CENTRAL_IN_CORE' if g['central_bins_in_core']==4 else 'ALL_CENTRAL_OUTSIDE_CORE'}
            baseline_rows.append({**common,'amplitude_reference':0,'sham_target_only':True,**base_rank})
            baseline_truth_terms=base_terms[ti].copy()
            for model in MODELS:
                model_spec=g['models'][model];kernels=model_spec['row_kernels']
                require([k['source_row'] for k in kernels]==g['true_active_source_rows'],'Frozen kernel row order differs')
                support_counts=Counter(k['normalization_support_class'] for k in kernels)
                support_stratum=next(iter(support_counts)) if len(support_counts)==1 else 'MIXED'
                weight_cells={int(k['source_row']):dict(zip(k['absolute_channels'],k['weights'])) for k in kernels}
                reference_fraction=np.asarray([sum(weight_cells.get(int(row),{}).get(int(channel),0.0)
                    for row,channel in zip(rows,bins))/4.0 for rows,bins in zip(arrays['path_source_rows'],arrays['absolute_channels'])],dtype=np.float64)
                oracle_reference_fraction=float(reference_fraction[~arrays['path_dc_mask']].max())
                require(abs(oracle_reference_fraction-model_spec['frozen_family_oracle_ideal_deposited_fraction'])<=1e-12 and
                        abs(float(reference_fraction[ti])-model_spec['central4_ideal_deposited_fraction'])<=1e-12,
                        'Frozen geometry ideal capture fractions differ')
                for amp in AMPLITUDES:
                    case_id=g['geometry_id']+'_'+model+'_A'+str(amp)
                    modified,injected_cells=apply_injection(raw,saved_normal,kernels,amp,channel0)
                    active=g['true_active_source_rows']
                    unaffected=[row for row in range(16) if row not in active]
                    require(np.array_equal(modified[unaffected],raw[unaffected]),'Unaffected raw rows changed')
                    case_normal={key:normal[key].copy() for key in NORM_FIELDS}
                    for row in active:
                        nr=recompute_row_normal(modified[row])
                        for key in NORM_FIELDS:case_normal[key][row]=nr[key]
                        nrow={'case_id':case_id,'geometry_id':g['geometry_id'],'profile_id':pid,
                              'model':model,'amplitude_reference':amp,'source_row':row}
                        krow=next(k for k in kernels if k['source_row']==row)
                        nrow.update({'normalization_support_class':krow['normalization_support_class'],
                                     'reference_fraction_power_in_core':krow['fraction_power_in_core'],
                                     'reference_fraction_power_in_core_halo':krow['fraction_power_in_core_halo']})
                        for key in NORM_FIELDS:
                            nrow[key+'_before']=float(normal[key][row]);nrow[key+'_after']=float(case_normal[key][row])
                            nrow[key+'_delta']=float(case_normal[key][row]-normal[key][row])
                        normal_rows.append(nrow)
                    terms,scores=score_paths(modified,case_normal,arrays,channel0,base_terms,active)
                    stats,top5,central_counts,case_ti=ranked(arrays,scores,g)
                    require(case_ti==ti,'Truth identity changed')
                    frozen_truth_terms=np.empty(4,dtype=np.float64)
                    for ri,row in enumerate(active):
                        rn={key:float(normal[key][row]) for key in NORM_FIELDS}
                        frozen_truth_terms[ri]=path_row_terms(modified[row],rn,[g['truth_active4'][ri]],channel0)[0]
                    refit_truth_terms=terms[ti].copy()
                    central_weights=[]
                    for ri,kernel in enumerate(kernels):
                        channel=g['truth_active4'][ri]
                        central_weights.append(sum(w for ch,w in zip(kernel['absolute_channels'],kernel['weights']) if ch==channel))
                    requested_response=amp*np.asarray(central_weights,dtype=np.float64)
                    frozen_response=frozen_truth_terms-baseline_truth_terms
                    refit_response=refit_truth_terms-baseline_truth_terms
                    refit_delta=refit_truth_terms-frozen_truth_terms
                    raw_modified_hash=raw_hash(modified)
                    record={**common,'case_id':case_id,'model':model,'amplitude_reference':amp,
                        'kernel_core_overlap_rows':support_counts['CORE_OVERLAP'],
                        'kernel_halo_only_rows':support_counts['HALO_ONLY'],
                        'kernel_outside_normalization_support_rows':support_counts['OUTSIDE_NORMALIZATION_SUPPORT'],
                        'kernel_normalization_support_stratum':support_stratum,
                        'raw_modified_power_bytes_sha256':raw_modified_hash,**stats,
                        'baseline_truth_score':base_rank['truth_score'],
                        'truth_score_uplift':stats['truth_score']-base_rank['truth_score'],
                        'truth_score_frozen_normalization':float(frozen_truth_terms.sum()/2),
                        'truth_score_refit_minus_frozen':float(refit_delta.sum()/2),
                        'reference_total_power_fraction_central_path':float(reference_fraction[ti]),
                        'reference_total_power_fraction_oracle':oracle_reference_fraction,
                        'reference_total_power_fraction_rank1':float(reference_fraction[top5[0]]),
                        'reference_total_power_fraction_best_top5':float(reference_fraction[top5].max()),
                        'requested_central_standardized_response':cell(requested_response.tolist()),
                        'actual_frozen_central_standardized_response':cell(frozen_response.tolist()),
                        'actual_refit_central_standardized_response':cell(refit_response.tolist()),
                        'central_response_frozen_minus_requested_max_abs':float(np.max(np.abs(frozen_response-requested_response))),
                        'central_response_refit_minus_frozen_max_abs':float(np.max(np.abs(refit_delta))),
                        'baseline_truth_deterministic_rank':base_rank['truth_deterministic_rank'],
                        'baseline_truth_retained_top1':base_rank['truth_retained_top1'],
                        'baseline_truth_retained_top5':base_rank['truth_retained_top5']}
                    case_rows.append(record)
                    case_path=out/'cases'/(case_id+'.npz')
                    with case_path.open('xb') as stream:
                        np.savez_compressed(stream,**arrays,residual_row_terms=terms,scores=scores,**case_normal,
                            baseline_truth_row_terms=baseline_truth_terms,
                            frozen_normal_truth_row_terms=frozen_truth_terms,refit_truth_row_terms=refit_truth_terms,
                            requested_central_response=requested_response,
                            reference_weight_capture_fraction=reference_fraction)
                    case_metadata.append({'case_id':case_id,'geometry_id':g['geometry_id'],'profile_id':pid,
                        'model':model,'amplitude_reference':amp,'raw_modified_power_bytes_sha256':raw_modified_hash,
                        'raw_source_power_bytes_sha256':raw_base_hash,'injected_cells':injected_cells,'arrays':pin(case_path,out)})
                    for rank,i in enumerate(top5,1):
                        retained_rows.append({'case_id':case_id,'geometry_id':g['geometry_id'],'profile_id':pid,
                            'model':model,'amplitude_reference':amp,'rank':rank,'path_index':int(i),
                            'window_index':int(arrays['path_window_index'][i]),
                            'source_rows':cell(arrays['path_source_rows'][i].tolist()),
                            'native4':cell(arrays['absolute_channels'][i].tolist()),'score':float(scores[i]),
                            'matched_central_truth_cells':int(central_counts[i]),'complete_central_truth':bool(central_counts[i]==4)})
        if (pi+1)%6==0:
            print(cell({'profiles_complete':pi+1,'raw_cases_complete':len(case_rows),'CPU_s':time.process_time()-started_cpu}),flush=True)
    require(len(case_rows)==648 and len(baseline_rows)==108 and len(normal_rows)==2592,'Frozen output census differs')
    for name,records in [('TRIAL_RANKS.csv',case_rows),('BASELINE_RANKS.csv',baseline_rows),
                         ('NORMALIZATION_DELTA.csv',normal_rows),('RETAINED_HYPOTHESES.csv',retained_rows)]:
        write_csv(out/name,records)
    write_json(out/'CASE_ARRAYS.json',{'schema':'SETI_RAW_RETENTION_CASE_ARRAYS_V1','count':648,'cases':case_metadata})
    write_json(out/'BASELINE_ARRAYS.json',{'schema':'SETI_RAW_RETENTION_BASELINE_ARRAYS_V1','count':54,'profiles':baseline_metadata})
    def panel(model,amp):
        subset=[r for r in case_rows if r['model']==model and r['amplitude_reference']==amp]
        def strata(values):
            return {'cases':len(values),'top1_complete_central_truth':sum(r['truth_retained_top1'] for r in values),
                    'top5_complete_central_truth':sum(r['truth_retained_top5'] for r in values),
                    'truth_score_uplift_min_median_max':[float(v) for v in np.quantile([r['truth_score_uplift'] for r in values],(0,.5,1))],
                    'refit_minus_frozen_truth_score_min_median_max':[float(v) for v in np.quantile([r['truth_score_refit_minus_frozen'] for r in values],(0,.5,1))]}
        return {'cases':len(subset),'top1_complete_central_truth':sum(r['truth_retained_top1'] for r in subset),
                'top5_complete_central_truth':sum(r['truth_retained_top5'] for r in subset),
                'additional_top5_complete_central_truth':sum(r['truth_retained_top5'] and not r['truth_retained_top1'] for r in subset),
                'top5_missing_central_truth':sum(not r['truth_retained_top5'] for r in subset),
                'deterministic_truth_rank_counts':dict(sorted(Counter(r['truth_deterministic_rank'] for r in subset).items())),
                'truth_score_uplift_min_median_max':[float(v) for v in np.quantile([r['truth_score_uplift'] for r in subset],(0,.5,1))],
                'refit_minus_frozen_truth_score_min_median_max':[float(v) for v in np.quantile([r['truth_score_refit_minus_frozen'] for r in subset],(0,.5,1))],
                'reference_total_power_fraction_oracle_min_median_max':[float(v) for v in np.quantile([r['reference_total_power_fraction_oracle'] for r in subset],(0,.5,1))],
                'reference_total_power_fraction_rank1_min_median_max':[float(v) for v in np.quantile([r['reference_total_power_fraction_rank1'] for r in subset],(0,.5,1))],
                'reference_total_power_fraction_best_top5_min_median_max':[float(v) for v in np.quantile([r['reference_total_power_fraction_best_top5'] for r in subset],(0,.5,1))],
                'by_central_truth_core_class':{label:strata([r for r in subset if r['central_truth_core_class']==label])
                    for label in sorted(set(r['central_truth_core_class'] for r in subset))},
                'by_kernel_normalization_support_stratum':{label:strata([r for r in subset if r['kernel_normalization_support_stratum']==label])
                    for label in sorted(set(r['kernel_normalization_support_stratum'] for r in subset))},
                'central_frozen_minus_requested_max_abs':max(r['central_response_frozen_minus_requested_max_abs'] for r in subset)}
    summary={'schema':'SETI_RAW_RETENTION_RESULT_V1','status':'COMPLETE_RAW_NORMALIZATION_LOCAL_RETENTION_STRESS_CONTROL',
        'date':'2026-10-14','profiles':54,'geometries':108,'raw_cases':648,
        'normalization_baseline_authenticated_rows':864,'modified_case_normalization_rows':2592,
        'models':{model:{str(amp):panel(model,amp) for amp in AMPLITUDES} for model in MODELS},
        'A0_baseline_sham_target':{'cases':108,'top1_count':sum(r['truth_retained_top1'] for r in baseline_rows),
            'top5_count':sum(r['truth_retained_top5'] for r in baseline_rows),'interpretation':'sham targets, no recovery/FAP interpretation'},
        'candidate_workload':{'positive_case_top1_slots':648,'positive_case_top5_slots':3240,
            'baseline_unique_top1_slots':108,'baseline_unique_top5_slots':540,'ratio':5},
        'normalization_authentication_max_absolute_error':{key:max(p['normalization_authentication_max_absolute_errors'][key] for p in baseline_metadata) for key in NORM_FIELDS},
        'central_truth_metric':'exact designated nearest-even centers in4active rows; unchanged width1score for every response model',
        'raw_spectral_arrays_opened':54,'new_telescope_requests':0,'new_telescope_bytes':0,'new_observation':False,
        'qualified_SETI_detection':False,'calibrated_FAP':False,'physical_sensitivity_established':False,
        'original_A_B':'FAIL_CLOSED','full6scan_chain_gate_pass':False,'interpretation':scope['interpretation']}
    write_json(out/'SUMMARY.json',summary)
    output_pins=[pin(path,out) for path in sorted(out.rglob('*')) if path.is_file()]
    require(sum(p['bytes'] for p in output_pins)<=budget['output_bytes_cap'],'Output cap exceeded')
    elapsed_cpu=time.process_time()-started_cpu;elapsed_wall=time.monotonic()-started_wall
    require(elapsed_cpu<=budget['producer_CPU_s_cap'],'Producer CPU cap exceeded')
    write_json(out/'EXECUTION_RECEIPT.json',{'schema':'SETI_RAW_RETENTION_EXECUTION_RECEIPT_V1','status':'COMPLETE',
        'scope_sha256':sha(scope_path),'producer_sha256':sha(Path(__file__)),
        'metadata_manifest_sha256':sha(manifest_path),'effective_input_root':str(root),
        'source_profiles':54,'raw_cases':648,'saved_case_arrays':648,'saved_baseline_arrays':54,
        'outputs':output_pins,'resource_usage':{'CPU_s':elapsed_cpu,'wall_s':elapsed_wall,
             'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024},
        'new_telescope_requests':0,'new_telescope_bytes':0,'qualified_SETI_detection':False})
    signal.alarm(0)
    print(cell(summary))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('input_root',type=Path)
    execute=sub.add_parser('run');execute.add_argument('output_root',type=Path)
    execute.add_argument('--input-root',type=Path);execute.add_argument('--go-scope-sha256',required=True)
    args=p.parse_args();(prepare if args.command=='prepare' else run)(args)


if __name__=='__main__':main()
