#!/usr/bin/env python3
"""JSON-only prospective width-bank control with new raw injection cells."""
import json
import math
import resource
import signal
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import kernel_geometry as kernel

TASK=Path('/workspace/scratch/b83cfe20d6e1')
BASE=TASK/'checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14'
OUT=TASK/'matched_width_20261014'
WIDTHS=(1,3,9,33)
PLACEMENTS=((-384,4,Fraction(-31,100),Fraction(-7,100)),
            (384,8,Fraction(79,100),Fraction(41,100)))


def template_capture(rows,bins,width,row_kernels):
    half=width//2
    chosen=dict(zip(rows,bins))
    total=math.fsum(w for k in row_kernels for c,w in zip(k['absolute_channels'],k['weights'])
                   if k['source_row'] in chosen and abs(c-chosen[k['source_row']])<=half)
    covered=all(k['source_row'] in chosen and all(abs(c-chosen[k['source_row']])<=half
                for c in k['absolute_channels']) for k in row_kernels)
    return total/4.0,covered


def main():
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU,(100,100))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    signal.alarm(900)
    gf=BASE/'rounding_followup/exact_geometry_results/GEOMETRY.json'
    mf=BASE/'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
    oldf=BASE/'rounding_followup/results/INJECTIONS.json'
    residualf=TASK/'retention_validation_20261014/GEOMETRY_MANIFEST.json'
    rawf=TASK/'raw_retention_design/GEOMETRY_MANIFEST.json'
    source=TASK/'repo_latest/raw_chain_sources/generator_original.py'
    family=json.loads(gf.read_bytes());matrix=json.loads(mf.read_bytes())
    old=json.loads(oldf.read_bytes());residual=json.loads(residualf.read_bytes());raw=json.loads(rawf.read_bytes())
    assert len(family['profiles'])==54 and family['counts']['total_unique_paths_zero_offset']==22235
    prior_keys=set();prior_cells=set()
    for t in old['trials']:
        rows=tuple(t['true_active_source_rows'])
        for field in ('canonical_float_truth_absolute_centers','canonical_rational_truth_absolute_centers'):
            bins=tuple(t[field][r] for r in rows)
            prior_keys.add((t['context_scan_id'],rows,bins))
            prior_cells.update((t['context_scan_id'],r,c) for r,c in zip(rows,bins))
    for t in residual['geometries']:
        rows=tuple(t['true_active_source_rows']);bins=tuple(t['truth_active4'])
        prior_keys.add((t['context_scan_id'],rows,bins))
        prior_cells.update((t['context_scan_id'],r,c) for r,c in zip(rows,bins))
    for t in raw['geometries']:
        rows=tuple(t['true_active_source_rows']);bins=tuple(t['truth_active4'])
        prior_keys.add((t['context_scan_id'],rows,bins))
        for model in t['models'].values():
            prior_cells.update((t['context_scan_id'],k['source_row'],c) for k in model['row_kernels'] for c in k['absolute_channels'])
    profiles={p['profile_id']:p for p in matrix['profiles']}
    crops={p['crop_id']:p for p in matrix['normalization_crops']}
    records=[];baselines=[];support_checks=0;box_terms=0;support_range=[]
    new_keys=set();new_cells=set();core_counts=Counter();row_classes=Counter()
    projection_ranges=defaultdict(list);coverage_counts=Counter()
    for f in family['profiles']:
        pid=f['profile_id'];p=profiles[pid];crop=crops[p['normalization_crop_id']]
        rawbounds=crop['source_channel_interval_half_open'];core=crop['normalization_source_channel_interval_half_open']
        assert rawbounds[1]-rawbounds[0]==12096 and core==[rawbounds[0]+4000,rawbounds[0]+8096]
        rawpin=kernel.pin(BASE/'seti_work'/p['raw_normalization_crop']['path'],BASE)
        normalpin=kernel.pin(BASE/'seti_work'/p['normalization']['path'],BASE)
        baselines.append(dict(profile_id=pid,context_scan_id=f['context_scan_id'],raw_crop_pin=rawpin,
            normalization_pin=normalpin,normalization_crop_id=p['normalization_crop_id'],raw_source_interval_half_open=rawbounds,
            normalization_core_interval_half_open=core))
        for host,start,driftfrac,phase in PLACEMENTS:
            rows=list(range(start,start+4));wi=start//2
            rate=Fraction.from_float(f['original_drift_hz_s'])+driftfrac*kernel.H
            sweep=abs(rate)*kernel.TSAMP/abs(kernel.DF)
            centers=[Fraction(f['source_reference_channel']+host)+phase+rate*Fraction.from_float(t)/kernel.DF for t in f['times_from_primary_reference_s']]
            truth=[kernel.nearest(c) for c in centers];active4=[truth[r] for r in rows];native4=[c-host for c in active4]
            lookup={tuple(p['channels']) for p in f['windows'][wi]['paths']}
            assert tuple(native4) in lookup
            physical=(f['context_scan_id'],tuple(rows),tuple(active4))
            assert physical not in prior_keys and physical not in new_keys
            new_keys.add(physical)
            kernels=[kernel.row_kernel(r,centers[r],truth[r],'integration_smear',sweep,core,rawbounds) for r in rows]
            cells={(f['context_scan_id'],k['source_row'],c) for k in kernels for c in k['absolute_channels']}
            assert not cells.intersection(prior_cells)
            new_cells.update(cells);row_classes.update(k['normalization_support_class'] for k in kernels)
            per_width={}
            for width in WIDTHS:
                half=width//2;projections=[];covers=[]
                for w in f['windows']:
                    for path in w['paths']:
                        bins=[c+host for c in path['channels']]
                        assert min(bins)-half-250>=rawbounds[0] and max(bins)+half+250<rawbounds[1]
                        assert all(not kernel.DC.intersection(range(c-half,c+half+1)) for c in bins)
                        support_checks+=1;box_terms+=4*width
                        support_range.append((min(bins)-half-250-rawbounds[0],max(bins)+half+250-rawbounds[0]))
                        frac,covered=template_capture(w['window_source_rows'],bins,width,kernels)
                        assert -1e-14<=frac<=1+1e-14
                        projections.append(frac);covers.append(covered)
                canonical_frac,canonical_cover=template_capture(rows,active4,width,kernels)
                per_width[str(width)]=dict(canonical_center_ideal_deposited_fraction=canonical_frac,
                    canonical_center_full_positive_kernel_coverage=canonical_cover,
                    oracle_ideal_deposited_fraction=max(projections),oracle_full_positive_kernel_coverage=any(covers),
                    full_coverage_hypothesis_count=sum(covers),allowed_unique_template_count=len(projections),
                    ideal_best_score_per_reference_A=max(projections)*4/math.sqrt(4*width),
                    template_ideal_standardized_score_coefficients=[frac*4/math.sqrt(4*width) for frac in projections],
                    template_order='Frozen family flattened window_start ascending then native4centers lexicographic; same order as sourceGEOMETRY profilewindows/paths.')
                projection_ranges[str(width)].append(per_width[str(width)])
                coverage_counts[str(width)]+=int(any(covers))
            combined_oracle=max(v['oracle_ideal_deposited_fraction'] for v in per_width.values())
            combined_cover=any(v['oracle_full_positive_kernel_coverage'] for v in per_width.values())
            oracle_coef=max(v['ideal_best_score_per_reference_A'] for v in per_width.values())
            optimal_widths=[w for w in WIDTHS if per_width[str(w)]['ideal_best_score_per_reference_A']==oracle_coef]
            assert combined_cover
            count_core=sum(core[0]<=c<core[1] for c in active4);core_counts[count_core]+=1
            model=dict(row_kernels=kernels,total_weight_per_active_row=1.0,injection_cell_count=sum(len(k['absolute_channels']) for k in kernels),
                central4_ideal_deposited_fraction=per_width['1']['canonical_center_ideal_deposited_fraction'],
                frozen_family_oracle_ideal_deposited_fraction=per_width['1']['oracle_ideal_deposited_fraction'],
                combined_family_oracle_ideal_deposited_fraction=combined_oracle,combined_family_oracle_full_positive_kernel_coverage=combined_cover,
                combined_family_oracle_ideal_standardized_score_coefficient=oracle_coef,
                oracle_optimal_width=min(optimal_widths),oracle_tied_optimal_widths=optimal_widths)
            records.append(dict(geometry_id=f'MW{len(records)+1:04d}',profile_id=pid,origin_scan_id=f['origin_scan_id'],
                context_scan_id=f['context_scan_id'],origin_rank=f['origin_rank'],host_offset_channels=host,
                true_window_index=wi,true_window_start_row=start,true_active_source_rows=rows,
                drift_fraction=kernel.enc(driftfrac),phase_fraction=kernel.enc(phase),true_drift_fraction=kernel.enc(rate),
                true_drift_hz_s_display=float(rate),integration_sweep_channels_fraction=kernel.enc(sweep),integration_sweep_channels_display=float(sweep),
                continuous_centers_fraction=[kernel.enc(c) for c in centers],truth16=truth,truth_active4=active4,native4=native4,
                models={'integration_smear':model},per_width_projection=per_width,
                widths=list(WIDTHS),raw_crop_pin=rawpin,normalization_pin=normalpin,raw_source_interval_half_open=rawbounds,
                normalization_core_interval_half_open=core,central_bins_in_core=count_core,
                all_width_boxes_raw501_supported=True,all_width_boxes_DC_clean=True,
                prior_physical_placement_overlap=False,prior_positive_kernel_cell_overlap=False))
    assert len(records)==108 and len(new_keys)==108 and support_checks==22235*2*4
    cpu=resource.getrusage(resource.RUSAGE_SELF)
    result=dict(schema='SETI_MATCHED_WIDTH_GEOMETRY_V1',date='2026-10-14',status='PASS_METADATA_ONLY_NEW_WIDTH_BANK_PLACEMENTS',
        frozen_top5_policy_base_commit='f1108023a7bf7e2700d97a0b31c6eb30d9fa1f14',
        placements=[dict(host_offset_channels=h,window_start_row=s,drift_fraction=kernel.enc(d),phase_fraction=kernel.enc(p)) for h,s,d,p in PLACEMENTS],
        widths=list(WIDTHS),amplitudes=[8,32],models=['integration_smear'],
        geometry_arithmetic='Separately rationalized binary64 d0,time,DF,half_step,TSAMP with exact new rational drift/phase and nearest absolute-channel ties-even; same frozen native4 center family.',
        kernel_law=raw['raw_injection'],normalization={**raw['normalization'],
            'path_scoring':'Same frozen exact native4 center family acrossall7 windows translated toSAME injection host; eachwidth1/3/9/33 template sums directly standardized raw501 row residuals in its4×width nativecells and divides bysqrt(4×width).'},
        operational_amendments=['Finite nonnegativefloat32 raw powers allowed; reject negatives/nonfinite; core median/MAD positive.',
            'Operational12 unchanged rows reuse RECOMPUTED authenticated baseline normalization; original saved median/MAD define only input power reference.'],
        policy=dict(retention_k=5,comparison='single combined width-bank top5 versus width1-only top5',
            hypothesis_identity=['width','window_source_rows','native_four_center_bins'],
            score='Sum standardized residualz at4row×width native cells, divided bysqrt(4*width); same raw501 row residual and original full4096 normalization.',
            tie_order='descending score,widthascending,windowstartascending,native4centerslexicographic',
            DC_eligibility='Any selected box cell contacting a frozenDC channel makes whole hypothesis ineligible.',
            deposited_fraction='Sum declared positive normalized kernelweights inside selected boxes on active rows divided4; report family oracle and best actual top5, not a selection criterion.',
            standardized_projection_coefficient='Sum active declared kernelweights selected by template dividedsqrt(4*width)=2*depositedfraction/sqrt(width). Report family oracle/maximizing width and maximum coefficient among actual score-retained top5; no input power rescaling, ranking change or acceptance threshold.',
            full_support_coverage='Every positive declared integration_smear kernel channel on all4 active source rows lies inside its selected same-row box; missing any active row or positive cell isfalse.',
            canonical_center='Metadata reference only; full kernel coverage and retained depositedfraction are primary spread-signal diagnostics.',
            amplitude_reference='A8/32 total perrow original median×MAD reference power; strongerA32 declared prospectively, not physicalSNR/flux/sensitivity.',
            baseline='108 unique profile-host combined lists and108 width1 lists, bothk5; equalretained slots but4times candidate hypotheses and altered correlation; not nullFAP calibration.'),
        counts=dict(profiles=54,baseline_raw_crops=54,physical_unique_placements=108,perturbed_raw_cases=216,
            baseline_combined_lists=108,baseline_width1_lists=108,models=1,amplitudes=2,widths=4,
            prior_physical_placements=len(prior_keys),prior_positive_injection_cells=len(prior_cells),
            new_overlap_prior_physical_placements=0,new_positive_cells_overlap_prior=0,unique_new_positive_injection_cells=len(new_cells),
            all_width_template_host_raw501_DC_checks=support_checks,total_four_row_box_cells=box_terms,
            central_bins_in_core_perplacement_histogram={str(k):v for k,v in sorted(core_counts.items())},
            kernel_row_normalization_support_classes=dict(row_classes),
            oracle_full_kernel_coverage_geometries_by_width=dict(coverage_counts)),
        oracle_optimal_width_counts={str(w):sum(g['models']['integration_smear']['oracle_optimal_width']==w for g in records) for w in WIDTHS},
        raw501_box_support_crop_indices_inclusive=[min(a for a,b in support_range),max(b for a,b in support_range)],
        integration_sweep_range=[min(g['integration_sweep_channels_display'] for g in records),max(g['integration_sweep_channels_display'] for g in records)],
        projection_summary={width:dict(oracle_deposited_fraction_range=[min(v['oracle_ideal_deposited_fraction'] for v in vals),max(v['oracle_ideal_deposited_fraction'] for v in vals)],
            canonical_deposited_fraction_range=[min(v['canonical_center_ideal_deposited_fraction'] for v in vals),max(v['canonical_center_ideal_deposited_fraction'] for v in vals)],
            oracle_full_coverage_geometries=sum(v['oracle_full_positive_kernel_coverage'] for v in vals)) for width,vals in projection_ranges.items()},
        geometries=records,baselines=baselines,input_pins=[kernel.pin(p) for p in (gf,mf,oldf,residualf,rawf,source)],
        code_pins=[kernel.pin(Path(__file__).resolve()),kernel.pin(Path(kernel.__file__).resolve())],
        resource_envelope=dict(incremental_reserved_CPU_s=1000,metadata_CPU_s_cap=100,producer_CPU_s_cap=450,QA_CPU_s_cap=450,
            wall_s_cap_each=900,memory_bytes_cap_each=2*1024**3,prior_ledger_retained=True,DKK=0),
        metadata_resource_usage=dict(CPU_s=cpu.ru_utime+cpu.ru_stime,wall_s=time.monotonic()-started,peak_RSS_bytes=cpu.ru_maxrss*1024),
        interpretation=['One prospective fixedwidth1/3/9/33 local stage on new integration-smear injectioncells and already exposed2017 background.',
            'Same intrinsic/exposure kernel law and totalpower reference; no empirical instrument-response or physical sensitivity claim.',
            'Full positive-kernel support coverage is geometric completeness, not qualified detection recovery. A smallerbox may have larger ideal standardized projection coefficient while omitting lowweight wings.',
            'Combinedtop5 and width1-onlytop5 use different finitefamilies with correlated templates; candidateworkload5vs5 and no calibratedFAP.',
            'No new telescope files, fullglobalsearch, physicalclassification or originalsixscan-chain qualification.'],
        preserved=dict(original_A_B='FAIL_CLOSED',full6scan_chain_gate_pass=False,qualified_SETI_detection=False,
            protected_2016=True,closed_2019=True,new_observation=False,new_telescope_requests=0,new_telescope_bytes=0,checkpoint='2026-10-20'),
        raw_spectral_arrays_opened=False,saved_scores_opened=False,observed_outcomes_scored=False)
    with (OUT/'GEOMETRY_MANIFEST.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','counts','raw501_box_support_crop_indices_inclusive','integration_sweep_range','projection_summary','metadata_resource_usage')}))


if __name__=='__main__':main()
