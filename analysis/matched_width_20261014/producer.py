#!/usr/bin/env python3
"""Fresh-placement raw-power control of one combined top5 width-template list.

Metadata prepare hashes bytes and reads JSON only. Numerical work is gated by
root GO and frozen code/scope. All raw normalization and injection helpers are
the exact separately pinned, independently verified prior raw-chain source.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import math
import os
from pathlib import Path
import resource
import signal
import time

for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'

import raw_helpers as raw_ops
from raw_helpers import require,read,sha,pin,write_json,write_csv,cell,NORM_FIELDS

WIDTHS=(1,3,9,33)
HOSTS=(-384,384)
AMPLITUDES=(8,32)
POLICIES=('combined','width1_only')
DEPENDENCY_SHA='569dc196707539e1b9bdf61e86462690c365c1831c952d3478ff452f728019a8'


def width_arrays(family,host):
    import numpy as np
    basic=raw_ops.flatten_family(family,host)
    centers=basic['absolute_channels'];rows=basic['path_source_rows']
    dc=np.asarray(raw_ops.DC,dtype=np.int64)
    masks=np.asarray([((np.abs(centers[:,:,None]-dc[None,None,:])<=w//2).any(axis=2)).any(axis=1)
                      for w in WIDTHS],dtype=bool)
    return {'absolute_centers':centers,'path_source_rows':rows,'path_window_index':basic['path_window_index'],
            'path_dc_mask':masks,'widths':np.asarray(WIDTHS,dtype=np.int64)}


def width_scores(raw,normal,arrays,channel0,baseline_sums=None,changed_rows=None):
    """Direct501 z at union bins, ascending-bin sum, then four-row sum/sqrt4w."""
    import numpy as np
    centers=arrays['absolute_centers'];rows=arrays['path_source_rows']
    sums=np.empty((4,)+centers.shape,dtype=np.float64) if baseline_sums is None else baseline_sums.copy()
    for row in range(16) if changed_rows is None else changed_rows:
        where=rows==row
        require(where.any(),'Selected source row absent from fixed family')
        row_centers=centers[where]
        union=np.unique(row_centers[:,None]+np.arange(-16,17,dtype=np.int64)[None,:])
        row_normal={key:float(normal[key][row]) for key in NORM_FIELDS}
        z=raw_ops.path_row_terms(raw[row],row_normal,union,channel0)
        for wi,width in enumerate(WIDTHS):
            radius=width//2
            box=row_centers[:,None]+np.arange(-radius,radius+1,dtype=np.int64)[None,:]
            require(box.shape[1]==width,'Frozen odd box width differs')
            positions=np.searchsorted(union,box)
            sums[wi,where]=np.sum(z[positions],axis=1,dtype=np.float64)
    scores=np.sum(sums,axis=-1,dtype=np.float64)/np.sqrt(4.0*np.asarray(WIDTHS,dtype=np.float64))[:,None]
    require(np.isfinite(scores).all(),'Nonfinite template score')
    return sums,scores


def projections(arrays,geometry):
    """Declared deposited reference weight, separate from observed/raw score."""
    import numpy as np
    kernels=geometry['models']['integration_smear']['row_kernels']
    by_row={k['source_row']:k for k in kernels}
    rows=arrays['path_source_rows'];centers=arrays['absolute_centers']
    mass=np.empty((4,len(rows)),dtype=np.float64);coverage=np.empty_like(mass,dtype=bool)
    for wi,width in enumerate(WIDTHS):
        radius=width//2
        for pi,(rs,cs) in enumerate(zip(rows,centers)):
            contributions=[];full=True
            for row,center in zip(rs.tolist(),cs.tolist()):
                kernel=by_row.get(row)
                if kernel is None:
                    full=False
                    continue
                channels=kernel['absolute_channels'];weights=kernel['weights']
                contribution=math.fsum(w for channel,w in zip(channels,weights) if center-radius<=channel<=center+radius)
                contributions.append(contribution)
                full=full and min(channels)>=center-radius and max(channels)<=center+radius
            mass[wi,pi]=math.fsum(contributions)/4.0
            coverage[wi,pi]=full and len(contributions)==4
        metadata=geometry['per_width_projection'][str(width)]
        eligible=~arrays['path_dc_mask'][wi]
        require(abs(float(mass[wi,eligible].max())-metadata['oracle_ideal_deposited_fraction'])<=1e-12 and
                bool(coverage[wi,eligible].any())==metadata['oracle_full_positive_kernel_coverage'],
                'Frozen signal-only width oracle differs')
        coefficient=2.0*mass[wi]/math.sqrt(width)
        require(np.max(np.abs(coefficient-np.asarray(metadata['template_ideal_standardized_score_coefficients'],dtype=np.float64)))<=1e-12,
                'Frozen template ideal standardized score coefficients differ')
    truth=canonical_path(arrays,geometry)
    for wi,width in enumerate(WIDTHS):
        metadata=geometry['per_width_projection'][str(width)]
        require(abs(float(mass[wi,truth])-metadata['canonical_center_ideal_deposited_fraction'])<=1e-12 and
                bool(coverage[wi,truth])==metadata['canonical_center_full_positive_kernel_coverage'],
                'Frozen canonical signal-only projection differs')
    return mass,coverage


def canonical_path(arrays,geometry):
    import numpy as np
    rows=np.asarray(geometry['true_active_source_rows'],dtype=np.int64)
    bins=np.asarray(geometry['truth_active4'],dtype=np.int64)
    indices=np.flatnonzero((arrays['path_source_rows']==rows).all(axis=1)&(arrays['absolute_centers']==bins).all(axis=1))
    require(len(indices)==1,'Designated canonical center identity not unique')
    return int(indices[0])


def select(arrays,scores,baseline_scores,mass,coverage,geometry,policy):
    import numpy as np
    count=scores.shape[1];flat_scores=scores.ravel();flat_mass=mass.ravel();flat_full=coverage.ravel()
    centers=np.tile(arrays['absolute_centers'],(4,1));rows=np.tile(arrays['path_source_rows'],(4,1))
    width_axis=np.repeat(np.asarray(WIDTHS,dtype=np.int64),count)
    coefficients=(2.0*mass/np.sqrt(np.asarray(WIDTHS,dtype=np.float64))[:,None]).ravel()
    uplifts=(scores-baseline_scores).ravel()
    eligible=(~arrays['path_dc_mask']).ravel()
    if policy=='width1_only':eligible[count:]=False
    ids=np.flatnonzero(eligible)
    order=ids[np.lexsort((centers[ids,3],centers[ids,2],centers[ids,1],centers[ids,0],
                         rows[ids,0],width_axis[ids],-flat_scores[ids]))]
    require(len(order)>=5,'Fewer than five eligible templates')
    top=order[:5];canonical=canonical_path(arrays,geometry)
    coefficient_oracle=float(coefficients[eligible].max())
    require(coefficient_oracle>0,'Signal-only ideal coefficient oracle is zero')
    canonical_ranks=[]
    for wi in range(4):
        cid=wi*count+canonical
        if policy=='width1_only' and wi>0:
            canonical_ranks.append(None)
            continue
        pos=np.flatnonzero(order==cid)
        require(len(pos)==1,'Canonical template excluded unexpectedly')
        cs=float(flat_scores[cid]);higher=int(np.count_nonzero(flat_scores[eligible]>cs));equal=int(np.count_nonzero(flat_scores[eligible]==cs))
        canonical_ranks.append({'width':WIDTHS[wi],'rank_min':higher+1,'rank_max':higher+equal,
                                'rank_tie_count':equal,'deterministic_rank':int(pos[0])+1})
    result={'policy':policy,'retained_count':5,'eligible_template_count':int(len(ids)),
        'winner_template_id':int(top[0]),'winner_path_index':int(top[0]%count),
        'winner_width':int(width_axis[top[0]]),'winner_score':float(flat_scores[top[0]]),
        'retained_template_ids':cell(top.tolist()),'retained_widths':cell(width_axis[top].tolist()),
        'retained_scores':cell(flat_scores[top].tolist()),
        'retained_reference_weight_fractions':cell(flat_mass[top].tolist()),
        'retained_full_positive_kernel_cell_coverage':cell(flat_full[top].tolist()),
        'retained_ideal_standardized_score_coefficients':cell(coefficients[top].tolist()),
        'best_retained_ideal_standardized_score_coefficient':float(coefficients[top].max()),
        'signal_only_oracle_ideal_standardized_score_coefficient':coefficient_oracle,
        'best_retained_coefficient_fraction_of_oracle':float(coefficients[top].max()/coefficient_oracle),
        'ideal_standardized_score_coefficient_gap_to_oracle':float(coefficient_oracle-coefficients[top].max()),
        'retained_actual_score_uplifts':cell(uplifts[top].tolist()),
        'winner_actual_score_uplift':float(uplifts[top[0]]),
        'best_retained_actual_score_uplift':float(uplifts[top].max()),
        'canonical_score_uplift_by_width':cell((scores[:,canonical]-baseline_scores[:,canonical]).tolist()),
        'best_retained_reference_weight_fraction':float(flat_mass[top].max()),
        'any_retained_full_positive_kernel_cell_coverage':bool(flat_full[top].any()),
        'retained_full_positive_kernel_cell_coverage_count':int(flat_full[top].sum()),
        'signal_only_oracle_reference_weight_fraction':float(flat_mass[eligible].max()),
        'signal_only_oracle_full_positive_kernel_cell_coverage':bool(flat_full[eligible].any()),
        'canonical_center_retained_any_width':bool(np.any(top%count==canonical)),
        'canonical_center_rank_by_width':cell(canonical_ranks)}
    return result,top


def central_class(number):
    return 'ALL_CENTRAL_IN_CORE' if number==4 else ('ALL_CENTRAL_OUTSIDE_CORE' if number==0 else 'MIXED_CENTRAL_CORE')


def prepare(args):
    here=Path(__file__).resolve().parent;root=args.input_root.resolve()
    require(sha(here/'raw_helpers.py')==DEPENDENCY_SHA,'Signed raw helper copy differs')
    manifest_path=here/'GEOMETRY_MANIFEST.json';manifest=read(manifest_path)
    require(len(manifest['geometries'])==108 and manifest['widths']==list(WIDTHS),'Frozen matched width geometry differs')
    matrix_path=root/'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
    geometry_path=root/'rounding_followup/exact_geometry_results/GEOMETRY.json'
    matrix=read(matrix_path)
    inputs={p['path']:p for p in (pin(matrix_path,root),pin(geometry_path,root),pin(root/'rounding_followup/results/INJECTIONS.json',root))}
    for profile in matrix['profiles']:
        for key in ('raw_normalization_crop','normalization'):
            declared=profile[key];path=root/'seti_work'/declared['path']
            require(path.stat().st_size==declared['bytes'] and sha(path)==declared['sha256'],'Source raw/normal pin differs')
            inputs[str(path.relative_to(root))]=pin(path,root)
    stage_paths=('raw_helpers.py','build_manifest.py','kernel_geometry.py',
        'prior_placements/GEOMETRY_MANIFEST_TOP5.json','prior_placements/GEOMETRY_MANIFEST_RAW648.json',
        'source_provenance/generator_original.py','source_provenance/detector_original.py')
    scope={'schema':'SETI_MATCHED_WIDTH_SCOPE_V1','date':'2026-10-14','status':'METADATA_READY_AWAITING_ROOT_GO',
        'input_root':str(root),'input_pins':list(inputs.values()),'stage_input_pins':[pin(here/p,here) for p in stage_paths],
        'producer_pin':pin(Path(__file__).resolve(),here),'geometry_manifest_pin':pin(manifest_path,here),
        'profile_count':54,'geometry_count':108,'raw_case_count':216,'baseline_policy_list_count':216,
        'widths':list(WIDTHS),'fixed_amplitudes':list(AMPLITUDES),'fixed_hosts':list(HOSTS),
        'fixed_model':'integration_smear','dependency_status':'EXACT_SIGNED_PRIOR_RAW_PRODUCER_INDEPENDENTLY_QA_VERIFIED',
        'score':{'formula':'four-row sum of per-bin z inside odd native box / sqrt(4*width)',
            'arithmetic':'ascending native-bin np.sum(dtype=float64) per row, then four-row np.sum(dtype=float64), divide once by sqrt(4*width)',
            'z':'(raw_power/operational_row_power_median - direct median501 - row_winsorized_location)/row_MAD',
            'normalization':'all baseline16 rows recomputed/authenticated on original4096 core; changed4 rows refit; other12 recomputed baseline rows reused',
            'raw_reference':'A*original saved median*original saved MAD*fixed row kernel weights; float64 addition and full float32 cast'},
        'policy':{'primary':'single combined top5 across(width,window,native4centers)','comparator':'width1-only top5',
            'k':5,'candidates_per_policy_list':5,'per_width_top5_lists_for_combined':False,
            'tie_order':'descending actual score, ascending width, ascending window start, ascending native4 centers',
            'primary_diagnostics':['best retained ideal deposited total-row power fraction',
                                   'geometric full positive kernel-cell box coverage in all4 active rows',
                                   'best retained ideal standardized score coefficient versus fixed-family oracle'],
            'secondary':'designated canonical-center ranks only; canonical retention not required for full deposited-cell coverage',
            'template_identity':['width','window_source_rows','native_four_center_bins']},
        'resource_envelope':{'reserved_CPU_s':1000,'metadata_CPU_s_cap':100,'producer_CPU_s_cap':450,'QA_CPU_s_cap':450,
            'wall_s_cap_each':900,'memory_bytes_cap_each':2147483648,'output_bytes_cap':80000000,
            'max_numerical_jobs':2,'cost_DKK':0},
        'interpretation':['Fresh declared injection cell identities on exposed2017 raw crops, no new observation.',
            'Widths1/3/9/33 are the original detector template bank; top5 remains one combined list.',
            'Box coverage and deposited-reference fractions are synthetic engineering diagnostics, not physical/FAP calibration.',
            'Primary selection remains local around preselected top9; template comparisons and source crops are dependent.',
            'Original full6scan chain/A_B qualification stays FAIL_CLOSED.'],
        'preserved':{'qualified_SETI_detection':False,'calibrated_FAP':False,'physical_sensitivity_established':False,
            'original_A_B':'FAIL_CLOSED','full6scan_chain_gate_pass':False,'new_observation':False,
            'new_telescope_requests':0,'new_telescope_bytes':0,'protected_2016':True,'closed_2019':True}}
    write_json(here/'SCOPE.json',scope)
    print(cell({'status':scope['status'],'scope_sha256':sha(here/'SCOPE.json'),'raw_cases':216}))


def run(args):
    started_cpu=time.process_time();started_wall=time.monotonic()
    here=Path(__file__).resolve().parent;scope_path=here/'SCOPE.json';scope=read(scope_path)
    require(sha(scope_path)==args.go_scope_sha256,'Root scope digest differs')
    go=read(here/'GO.json')
    require(go['scope_sha256']==sha(scope_path) and go['producer_sha256']==sha(Path(__file__).resolve())
            and scope['producer_pin']['sha256']==sha(Path(__file__).resolve()),'Root producer GO hashes differ')
    budget=scope['resource_envelope']
    resource.setrlimit(resource.RLIMIT_CPU,(budget['producer_CPU_s_cap'],budget['producer_CPU_s_cap']))
    resource.setrlimit(resource.RLIMIT_AS,(budget['memory_bytes_cap_each'],budget['memory_bytes_cap_each']))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Matched width producer wall cap exceeded')))
    signal.alarm(budget['wall_s_cap_each'])
    root=args.input_root.resolve() if args.input_root else Path(scope['input_root'])
    for declared in scope['input_pins']:
        path=root/declared['path']
        require(path.stat().st_size==declared['bytes'] and sha(path)==declared['sha256'],'Frozen bank source differs')
    for declared in scope['stage_input_pins']:
        path=here/declared['path']
        require(path.stat().st_size==declared['bytes'] and sha(path)==declared['sha256'],'Frozen stage source/provenance differs')
    manifest_path=here/scope['geometry_manifest_pin']['path']
    require(sha(manifest_path)==scope['geometry_manifest_pin']['sha256']==go['metadata_manifest_sha256'],'Frozen geometry differs')
    manifest=read(manifest_path);matrix=read(root/'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json')
    families={p['profile_id']:p for p in read(root/'rounding_followup/exact_geometry_results/GEOMETRY.json')['profiles']}
    grouped=defaultdict(list)
    for g in manifest['geometries']:grouped[g['profile_id']].append(g)
    require(len(grouped)==54 and all(len(gs)==2 for gs in grouped.values()),'Placement panel census differs')
    import numpy as np
    out=args.output_root.resolve();require(not out.exists() and not out.is_relative_to(root),'Fresh output outside source required')
    out.mkdir(parents=True);(out/'baselines').mkdir();(out/'cases').mkdir()
    cases=[];baselines=[];policies=[];baseline_policies=[];retained=[];norm_rows=[]
    for pi,profile in enumerate(matrix['profiles']):
        pid=profile['profile_id'];family=families[pid]
        with np.load(root/'seti_work'/profile['raw_normalization_crop']['path'],allow_pickle=False) as z:
            raw=z['raw_power'];channel0=int(z['source_channel0'])
            require(raw.shape==(16,12096) and raw.dtype==np.dtype('<f4') and np.isfinite(raw).all() and (raw>=0).all(),'Raw crop invalid')
            require(np.array_equal(z['absolute_time_rows'],np.arange(16)) and
                    np.array_equal(z['normalization_source_channels'],np.arange(channel0+4000,channel0+8096)),'Raw crop coordinates differ')
        saved=read(root/'seti_work'/profile['normalization']['path'])
        saved_normal={key:np.asarray(saved[key],dtype=np.float64) for key in NORM_FIELDS}
        normal={key:np.empty(16,dtype=np.float64) for key in NORM_FIELDS}
        for row in range(16):
            nr=raw_ops.recompute_row_normal(raw[row])
            for key in NORM_FIELDS:normal[key][row]=nr[key]
        errors={key:float(np.max(np.abs(normal[key]-saved_normal[key]))) for key in NORM_FIELDS}
        require(errors['row_power_median']==0 and all(errors[key]<=1e-12 for key in NORM_FIELDS[1:]),'Original normalization authentication failed')
        base_hash=raw_ops.raw_hash(raw);base_arrays={'widths':np.asarray(WIDTHS,dtype=np.int64),
            'offset_channels':np.asarray(HOSTS,dtype=np.int64),**normal,**{'saved_'+k:v for k,v in saved_normal.items()}}
        cache={}
        for host in HOSTS:
            arrays=width_arrays(family,host);row_sums,scores=width_scores(raw,normal,arrays,channel0)
            geometry=next(g for g in grouped[pid] if g['host_offset_channels']==host)
            mass,full=projections(arrays,geometry)
            cache[host]=(arrays,row_sums,scores,mass,full)
        first=cache[HOSTS[0]][0]
        base_arrays.update({'absolute_centers':np.stack([cache[h][0]['absolute_centers'] for h in HOSTS]),
            'path_source_rows':first['path_source_rows'],'path_window_index':first['path_window_index'],
            'path_dc_mask':np.stack([cache[h][0]['path_dc_mask'] for h in HOSTS]),
            'row_box_sum_z':np.stack([cache[h][1] for h in HOSTS]),'scores':np.stack([cache[h][2] for h in HOSTS]),
            'reference_weight_capture_fraction':np.stack([cache[h][3] for h in HOSTS]),
            'full_positive_kernel_cell_coverage':np.stack([cache[h][4] for h in HOSTS]),
            'ideal_standardized_score_coefficient':np.stack([2.0*cache[h][3]/np.sqrt(np.asarray(WIDTHS,dtype=np.float64))[:,None] for h in HOSTS])})
        baseline_path=out/'baselines'/(pid+'.npz')
        with baseline_path.open('xb') as stream:np.savez_compressed(stream,**base_arrays)
        baselines.append({'profile_id':pid,'raw_source_power_bytes_sha256':base_hash,
            'normalization_authentication_max_absolute_errors':errors,'arrays':pin(baseline_path,out)})
        for geometry in grouped[pid]:
            host=geometry['host_offset_channels'];arrays,base_sums,base_scores,mass,full=cache[host]
            kernels=geometry['models']['integration_smear']['row_kernels'];active=geometry['true_active_source_rows']
            support_counts=Counter(k['normalization_support_class'] for k in kernels)
            common={'geometry_id':geometry['geometry_id'],'profile_id':pid,'origin_scan_id':geometry['origin_scan_id'],
                'context_scan_id':geometry['context_scan_id'],'origin_rank':geometry['origin_rank'],'host_offset_channels':host,
                'true_window_index':geometry['true_window_index'],'true_active_source_rows':cell(active),
                'truth_active4':cell(geometry['truth_active4']),'central_bins_in_core':geometry['central_bins_in_core'],
                'central_truth_core_class':central_class(geometry['central_bins_in_core']),
                'kernel_core_overlap_rows':support_counts['CORE_OVERLAP'],'kernel_halo_only_rows':support_counts['HALO_ONLY'],
                'kernel_outside_normalization_support_rows':support_counts['OUTSIDE_NORMALIZATION_SUPPORT']}
            for policy in POLICIES:
                result,top=select(arrays,base_scores,base_scores,mass,full,geometry,policy)
                baseline_policies.append({**common,'amplitude_reference':0,'sham_target_only':True,**result})
            for amplitude in AMPLITUDES:
                case_id=geometry['geometry_id']+'_integration_smear_A'+str(amplitude)
                modified,injected_cells=raw_ops.apply_injection(raw,saved_normal,kernels,amplitude,channel0)
                unchanged=[row for row in range(16) if row not in active]
                require(np.array_equal(raw[unchanged],modified[unchanged]),'Unmodified source rows changed')
                case_normal={key:normal[key].copy() for key in NORM_FIELDS}
                for row in active:
                    nr=raw_ops.recompute_row_normal(modified[row]);kernel=next(k for k in kernels if k['source_row']==row)
                    norm={'case_id':case_id,'geometry_id':geometry['geometry_id'],'profile_id':pid,
                        'amplitude_reference':amplitude,'source_row':row,'normalization_support_class':kernel['normalization_support_class']}
                    for key in NORM_FIELDS:
                        case_normal[key][row]=nr[key];norm[key+'_before']=float(normal[key][row]);norm[key+'_after']=float(nr[key]);norm[key+'_delta']=float(nr[key]-normal[key][row])
                    norm_rows.append(norm)
                row_sums,scores=width_scores(modified,case_normal,arrays,channel0,base_sums,active)
                modified_hash=raw_ops.raw_hash(modified)
                for policy in POLICIES:
                    result,top=select(arrays,scores,base_scores,mass,full,geometry,policy)
                    policies.append({**common,'case_id':case_id,'amplitude_reference':amplitude,'model':'integration_smear',
                        'raw_modified_power_bytes_sha256':modified_hash,**result})
                    path_count=scores.shape[1]
                    for rank,template_id in enumerate(top,1):
                        wi,idx=divmod(int(template_id),path_count)
                        retained.append({'case_id':case_id,'geometry_id':geometry['geometry_id'],'profile_id':pid,
                            'amplitude_reference':amplitude,'policy':policy,'rank':rank,'template_id':int(template_id),
                            'width':WIDTHS[wi],'path_index':idx,'window_index':int(arrays['path_window_index'][idx]),
                            'source_rows':cell(arrays['path_source_rows'][idx].tolist()),
                            'native4_centers':cell(arrays['absolute_centers'][idx].tolist()),'score':float(scores[wi,idx]),
                            'reference_weight_capture_fraction':float(mass[wi,idx]),
                            'ideal_standardized_score_coefficient':float(2.0*mass[wi,idx]/math.sqrt(WIDTHS[wi])),
                            'actual_score_uplift':float(scores[wi,idx]-base_scores[wi,idx]),
                            'full_positive_kernel_cell_coverage':bool(full[wi,idx])})
                case_path=out/'cases'/(case_id+'.npz')
                with case_path.open('xb') as stream:np.savez_compressed(stream,**arrays,**case_normal,
                    row_box_sum_z=row_sums,scores=scores,reference_weight_capture_fraction=mass,
                    full_positive_kernel_cell_coverage=full,
                    ideal_standardized_score_coefficient=2.0*mass/np.sqrt(np.asarray(WIDTHS,dtype=np.float64))[:,None],
                    score_uplift=scores-base_scores)
                cases.append({'case_id':case_id,'geometry_id':geometry['geometry_id'],'profile_id':pid,
                    'amplitude_reference':amplitude,'model':'integration_smear','raw_modified_power_bytes_sha256':modified_hash,
                    'raw_source_power_bytes_sha256':base_hash,'injected_cells':injected_cells,'arrays':pin(case_path,out)})
        if (pi+1)%6==0:print(cell({'profiles_complete':pi+1,'raw_cases_complete':len(cases),'CPU_s':time.process_time()-started_cpu}),flush=True)
    require(len(cases)==216 and len(policies)==432 and len(baseline_policies)==216 and len(norm_rows)==864 and len(retained)==2160,'Frozen output census differs')
    for name,records in [('POLICY_RESULTS.csv',policies),('BASELINE_POLICY_RESULTS.csv',baseline_policies),
                          ('NORMALIZATION_DELTA.csv',norm_rows),('RETAINED_HYPOTHESES.csv',retained)]:write_csv(out/name,records)
    write_json(out/'CASE_ARRAYS.json',{'schema':'SETI_MATCHED_WIDTH_CASE_ARRAYS_V1','count':216,'cases':cases})
    write_json(out/'BASELINE_ARRAYS.json',{'schema':'SETI_MATCHED_WIDTH_BASELINE_ARRAYS_V1','count':54,'profiles':baselines})
    def policy_summary(subset):
        return {'lists':len(subset),'retained_slots':len(subset)*5,
            'any_full_positive_kernel_cell_coverage_count':sum(r['any_retained_full_positive_kernel_cell_coverage'] for r in subset),
            'best_retained_reference_weight_fraction_min_median_max':[float(v) for v in np.quantile([r['best_retained_reference_weight_fraction'] for r in subset],(0,.5,1))],
            'oracle_reference_weight_fraction_min_median_max':[float(v) for v in np.quantile([r['signal_only_oracle_reference_weight_fraction'] for r in subset],(0,.5,1))],
            'best_retained_ideal_standardized_score_coefficient_min_median_max':[float(v) for v in np.quantile([r['best_retained_ideal_standardized_score_coefficient'] for r in subset],(0,.5,1))],
            'oracle_ideal_standardized_score_coefficient_min_median_max':[float(v) for v in np.quantile([r['signal_only_oracle_ideal_standardized_score_coefficient'] for r in subset],(0,.5,1))],
            'best_retained_coefficient_fraction_of_oracle_min_median_max':[float(v) for v in np.quantile([r['best_retained_coefficient_fraction_of_oracle'] for r in subset],(0,.5,1))],
            'best_retained_actual_score_uplift_min_median_max':[float(v) for v in np.quantile([r['best_retained_actual_score_uplift'] for r in subset],(0,.5,1))],
            'canonical_center_retained_any_width_count':sum(r['canonical_center_retained_any_width'] for r in subset)}
    summary={'schema':'SETI_MATCHED_WIDTH_RESULT_V1','status':'COMPLETE_FROZEN_MATCHED_WIDTH_LOCAL_RAW_CONTROL',
        'date':'2026-10-14','profiles':54,'placements':108,'raw_cases':216,'widths':list(WIDTHS),
        'amplitude_panels':{str(a):{p:policy_summary([r for r in policies if r['amplitude_reference']==a and r['policy']==p]) for p in POLICIES} for a in AMPLITUDES},
        'baseline_sham_target':{p:policy_summary([r for r in baseline_policies if r['policy']==p]) for p in POLICIES},
        'by_central_truth_core_class':{str(a):{label:{p:policy_summary([r for r in policies if r['amplitude_reference']==a and r['policy']==p and r['central_truth_core_class']==label]) for p in POLICIES}
            for label in sorted(set(r['central_truth_core_class'] for r in policies))} for a in AMPLITUDES},
        'retained_width_counts_by_amplitude_policy':{str(a):{p:dict(sorted(Counter(r['width'] for r in retained if r['amplitude_reference']==a and r['policy']==p).items())) for p in POLICIES} for a in AMPLITUDES},
        'candidate_workload':{'combined_per_list':5,'width1_only_per_list':5,'ratio':1,'combined_positive_slots':1080,'width1_positive_slots':1080,
            'combined_baseline_slots':540,'width1_baseline_slots':540,'per_width_top5_used':False},
        'normalization_baseline_authenticated_rows':864,'modified_case_normalization_rows':864,
        'normalization_authentication_max_absolute_error':{key:max(p['normalization_authentication_max_absolute_errors'][key] for p in baselines) for key in NORM_FIELDS},
        'primary_metric':'ideal reference power fraction, geometric full deposited-cell coverage, and ideal standardized-score coefficient among retained templates',
        'full_kernel_coverage_interpretation':'geometric completeness, not signal detection; score-optimal partial boxes are valid alternatives',
        'canonical_center_rank_role':'secondary, not required for deposited-cell coverage',
        'raw_spectral_arrays_opened':54,'new_telescope_requests':0,'new_telescope_bytes':0,'new_observation':False,
        'qualified_SETI_detection':False,'calibrated_FAP':False,'physical_sensitivity_established':False,
        'original_A_B':'FAIL_CLOSED','full6scan_chain_gate_pass':False,'interpretation':scope['interpretation']}
    write_json(out/'SUMMARY.json',summary)
    output_pins=[pin(p,out) for p in sorted(out.rglob('*')) if p.is_file()]
    require(sum(p['bytes'] for p in output_pins)<=budget['output_bytes_cap'],'Output byte cap exceeded')
    cpu=time.process_time()-started_cpu;wall=time.monotonic()-started_wall
    require(cpu<=budget['producer_CPU_s_cap'],'Producer CPU budget exceeded')
    write_json(out/'EXECUTION_RECEIPT.json',{'schema':'SETI_MATCHED_WIDTH_EXECUTION_RECEIPT_V1','status':'COMPLETE',
        'scope_sha256':sha(scope_path),'producer_sha256':sha(Path(__file__)),'dependency_sha256':sha(here/'raw_helpers.py'),
        'metadata_manifest_sha256':sha(manifest_path),'effective_input_root':str(root),'raw_cases':216,'source_profiles':54,
        'saved_baseline_arrays':54,'saved_case_arrays':216,'outputs':output_pins,
        'resource_usage':{'CPU_s':cpu,'wall_s':wall,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024},
        'qualified_SETI_detection':False,'new_telescope_requests':0,'new_telescope_bytes':0})
    signal.alarm(0);print(cell(summary))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('input_root',type=Path)
    execute=sub.add_parser('run');execute.add_argument('output_root',type=Path)
    execute.add_argument('--input-root',type=Path);execute.add_argument('--go-scope-sha256',required=True)
    args=p.parse_args();(prepare if args.command=='prepare' else run)(args)


if __name__=='__main__':main()
