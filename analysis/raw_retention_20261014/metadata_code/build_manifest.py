#!/usr/bin/env python3
"""JSON-only design for new raw-power perturbations and normalization controls."""
import hashlib
import json
import math
import resource
import signal
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

TASK = Path('/workspace/scratch/b83cfe20d6e1')
BASE = TASK / 'checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14'
OUT = TASK / 'raw_retention_design'
DF = Fraction.from_float(-2.7939677238464355)
TSAMP = Fraction.from_float(18.253611008)
H = Fraction.from_float(4 / 158)
HALF = Fraction(1, 2)
DC = {178782208, 179830784, 180879360}
PLACEMENTS = ((-640, 0, Fraction(-67,100), Fraction(-19,100)),
              (640, 12, Fraction(23,100), Fraction(33,100)))


def enc(q):
    return [str(q.numerator), str(q.denominator)]


def floor(q):
    return q.numerator // q.denominator


def ceil(q):
    return -floor(-q)


def nearest(q):
    n, rem = divmod(q.numerator, q.denominator)
    return n + int(2*rem > q.denominator or 2*rem == q.denominator and n % 2 != 0)


def cdf(x, sweep):
    """Exact CDF for intrinsic U[-1/2,1/2] plus exposure U[-sweep/2,sweep/2]."""
    if not sweep:
        return max(Fraction(0), min(Fraction(1), x+HALF))
    edge = (sweep+1)/2
    if x <= -edge:
        return Fraction(0)
    if x >= edge:
        return Fraction(1)
    sq = lambda q: max(q, Fraction(0)) ** 2
    return (sq(x+edge)-sq(x+(sweep-1)/2)-sq(x+(1-sweep)/2)+sq(x-edge))/(2*sweep)


def row_kernel(row, center, rounded, model, sweep, core, rawbounds):
    if model == 'delta':
        pairs = [(rounded, Fraction(1))]
    elif model == 'fixed3':
        pairs = [(rounded-1,Fraction(1,4)),(rounded,Fraction(1,2)),(rounded+1,Fraction(1,4))]
    else:
        edge = (1+sweep)/2
        pairs = []
        for channel in range(floor(center-edge-HALF), ceil(center+edge+HALF)+1):
            weight = cdf(Fraction(channel)+HALF-center,sweep)-cdf(Fraction(channel)-HALF-center,sweep)
            assert weight >= 0
            if weight:
                pairs.append((channel,weight))
    assert sum(w for c,w in pairs) == 1
    raw_weights = [float(w) for c,w in pairs]
    assert min(raw_weights) >= -1e-14
    clipped = [max(0.0,w) for w in raw_weights]
    total = math.fsum(clipped)
    weights = [w/total for w in clipped]
    assert abs(math.fsum(weights)-1.0) <= 2e-15
    channels = [c for c,w in pairs]
    assert min(channels) >= rawbounds[0] and max(channels) < rawbounds[1]
    assert not any(c in DC for c in channels)
    inside = [core[0] <= c < core[1] for c in channels]
    halo = [core[0]-250 <= c < core[1]+250 for c in channels]
    category = 'CORE_OVERLAP' if any(inside) else 'HALO_ONLY' if any(halo) else 'OUTSIDE_NORMALIZATION_SUPPORT'
    return dict(source_row=row,absolute_channels=channels,weights=weights,exact_weights=[enc(w) for c,w in pairs],
                prenormal_sum=total,negative_clipped_count=sum(w<0 for w in raw_weights),
                continuous_center_fraction=enc(center),central_native_channel=rounded,
                central_bin_weight=weights[channels.index(rounded)] if rounded in channels else 0.0,
                source_channel_support_inclusive=[min(channels),max(channels)],
                central_bin_in_normalization_core=core[0] <= rounded < core[1],
                kernel_channels_in_core=sum(inside),kernel_channels_in_core_halo=sum(halo),
                fraction_power_in_core=math.fsum(w for w,inside_i in zip(weights,inside) if inside_i),
                fraction_power_in_core_halo=math.fsum(w for w,halo_i in zip(weights,halo) if halo_i),
                normalization_support_class=category)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pin(p, root=TASK):
    return dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=digest(p))


def main():
    began = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    signal.alarm(300)
    gf=BASE/'rounding_followup/exact_geometry_results/GEOMETRY.json'
    mf=BASE/'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
    oldf=BASE/'rounding_followup/results/INJECTIONS.json'
    newerf=TASK/'retention_validation_20261014/GEOMETRY_MANIFEST.json'
    source=TASK/'repo_latest/raw_chain_sources/generator_original.py'
    geom=json.loads(gf.read_bytes());matrix=json.loads(mf.read_bytes())
    old=json.loads(oldf.read_bytes());newer=json.loads(newerf.read_bytes())
    assert len(geom['profiles'])==54 and geom['counts']['total_unique_paths_zero_offset']==22235
    assert digest(source)=='3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693'
    profiles={p['profile_id']:p for p in matrix['profiles']}
    crops={p['crop_id']:p for p in matrix['normalization_crops']}
    prior_keys=set();prior_cells=set()
    for t in old['trials']:
        rows=tuple(t['true_active_source_rows'])
        for field in ('canonical_float_truth_absolute_centers','canonical_rational_truth_absolute_centers'):
            bins=tuple(t[field][r] for r in rows)
            prior_keys.add((t['context_scan_id'],rows,bins))
            prior_cells.update((t['context_scan_id'],r,c) for r,c in zip(rows,bins))
    for t in newer['geometries']:
        rows=tuple(t['true_active_source_rows']);bins=tuple(t['truth_active4'])
        prior_keys.add((t['context_scan_id'],rows,bins))
        prior_cells.update((t['context_scan_id'],r,c) for r,c in zip(rows,bins))
    records=[];baselines=[];all_family_bins=0;family_support=[]
    prior_overlap=Counter();unique_new_cells=defaultdict(set);core_classes=defaultdict(Counter)
    central_in_core=Counter();physical_keys=set();projection_metadata=[]
    for f in geom['profiles']:
        pid=f['profile_id'];p=profiles[pid];crop=crops[p['normalization_crop_id']]
        rawbounds=crop['source_channel_interval_half_open'];core=crop['normalization_source_channel_interval_half_open']
        assert rawbounds[1]-rawbounds[0]==12096 and core==[rawbounds[0]+4000,rawbounds[0]+8096]
        assert f['times_from_primary_reference_s']==p['times_from_primary_reference_s']
        rawpin=pin(BASE/'seti_work'/p['raw_normalization_crop']['path'],BASE)
        normalpin=pin(BASE/'seti_work'/p['normalization']['path'],BASE)
        normal=json.loads((BASE/normalpin['path']).read_bytes())
        assert all(len(normal[k])==16 for k in ('row_power_median','row_residual_MAD_scale','row_residual_median','row_winsorized_residual_location'))
        assert all(x>0 and math.isfinite(x) for k in ('row_power_median','row_residual_MAD_scale') for x in normal[k])
        assert normal['normalization_source_channels']==list(range(*core))
        baselines.append(dict(profile_id=pid,context_scan_id=f['context_scan_id'],normalization_crop_id=p['normalization_crop_id'],
                             raw_crop_pin=rawpin,normalization_pin=normalpin,raw_source_interval_half_open=rawbounds,
                             normalization_core_interval_half_open=core,normalization_core501_support_interval_half_open=[core[0]-250,core[1]+250]))
        for host,start,driftfrac,phase in PLACEMENTS:
            rows=list(range(start,start+4));wi=start//2
            rate=Fraction.from_float(f['original_drift_hz_s'])+driftfrac*H
            sweep=abs(rate)*TSAMP/abs(DF)
            centers=[Fraction(f['source_reference_channel']+host)+phase+rate*Fraction.from_float(t)/DF for t in f['times_from_primary_reference_s']]
            truth=[nearest(c) for c in centers]
            active4=[truth[r] for r in rows];native4=[c-host for c in active4]
            lookup={tuple(p['channels']) for p in f['windows'][wi]['paths']}
            assert tuple(native4) in lookup
            assert not any(c in DC for c in active4)
            physical=(f['context_scan_id'],tuple(rows),tuple(active4))
            assert physical not in prior_keys and physical not in physical_keys
            physical_keys.add(physical)
            for w in f['windows']:
                for path in w['paths']:
                    bins=[c+host for c in path['channels']]
                    assert min(bins)-250>=rawbounds[0] and max(bins)+250<rawbounds[1]
                    assert not any(c in DC for c in bins)
                    all_family_bins+=1
                    family_support.append((min(bins)-250-rawbounds[0],max(bins)+250-rawbounds[0]))
            models={}
            for model in ('delta','fixed3','integration_smear'):
                kernels=[row_kernel(r,centers[r],truth[r],model,sweep,core,rawbounds) for r in rows]
                cells={(f['context_scan_id'],k['source_row'],c) for k in kernels for c in k['absolute_channels']}
                prior_overlap[model]+=len(cells&prior_cells)
                unique_new_cells[model].update(cells)
                core_classes[model].update(k['normalization_support_class'] for k in kernels)
                weightmap={(k['source_row'],c):w for k in kernels for c,w in zip(k['absolute_channels'],k['weights'])}
                truthcoef=math.fsum(k['central_bin_weight'] for k in kernels)/2.0
                projections=[]
                for w in f['windows']:
                    for path in w['paths']:
                        coef=math.fsum(weightmap.get((r,c+host),0.0) for r,c in zip(w['window_source_rows'],path['channels']))/2.0
                        projections.append(coef)
                models[model]=dict(row_kernels=kernels,total_weight_per_active_row=1.0,
                    central4_signal_only_score_per_A=truthcoef,best_frozen_family_signal_only_score_per_A=max(projections),
                    central4_ideal_deposited_fraction=truthcoef/2.0,frozen_family_oracle_ideal_deposited_fraction=max(projections)/2.0,
                    central4_total_weight=truthcoef*2.0,
                    injection_cell_count=sum(len(k['absolute_channels']) for k in kernels),
                    prior_injection_cell_overlap_count=len(cells&prior_cells))
                projection_metadata.append((model,truthcoef,max(projections)))
            central_in_core[sum(core[0]<=c<core[1] for c in active4)]+=1
            records.append(dict(geometry_id=f'R{len(records)+1:04d}',profile_id=pid,
                origin_scan_id=f['origin_scan_id'],context_scan_id=f['context_scan_id'],origin_rank=f['origin_rank'],
                host_offset_channels=host,true_window_index=wi,true_window_start_row=start,true_active_source_rows=rows,
                drift_fraction=enc(driftfrac),phase_fraction=enc(phase),true_drift_fraction=enc(rate),
                true_drift_hz_s_display=float(rate),integration_sweep_channels_fraction=enc(sweep),
                integration_sweep_channels_display=float(sweep),truth16=truth,truth_active4=active4,native4=native4,
                continuous_centers_fraction=[enc(c) for c in centers],models=models,
                baseline_profile_id=pid,raw_crop_pin=rawpin,normalization_pin=normalpin,
                raw_source_interval_half_open=rawbounds,normalization_core_interval_half_open=core,
                central_bins_in_core=sum(core[0]<=c<core[1] for c in active4),
                full_frozen_search_family_raw501_supported=True,prior_physical_placement_overlap=False,
                physical_placement_unique_across_profiles=True,active4_dc_clean=True))
    assert len(records)==108 and len(baselines)==54 and all_family_bins==22235*2
    assert all(v==0 for v in prior_overlap.values())
    cpu=resource.getrusage(resource.RUSAGE_SELF)
    result=dict(schema='SETI_RAW_RETENTION_GEOMETRY_V1',date='2026-10-14',
        status='PASS_METADATA_ONLY_AVAILABLE_NOVEL_RAW_PLACEMENTS',
        frozen_top5_policy_commit='f1108023a7bf7e2700d97a0b31c6eb30d9fa1f14',
        geometry_arithmetic='Exact separately rationalized binary64 d0,time,DF,half_step,TSAMP; exact new rational drift/phase; nearest absolute native index ties-even.',
        fixed_panel=dict(placements=[dict(host_offset_channels=h,window_start_row=s,drift_fraction=enc(d),phase_fraction=enc(p)) for h,s,d,p in PLACEMENTS],
            amplitudes=[2,8],models=['delta','fixed3','integration_smear'],retention_k=[1,5],
            baseline_A0='One authenticated baseline per54 crops;108 sham-target ranks reuse those baselines, not216/324 duplicate null realizations.',
            truth='Complete canonical width1 central native4 identity; integration-smear wings or retained off-center hypotheses do not redefine truth.'),
        raw_injection=dict(delta_power='A * ORIGINAL saved row_power_median[row] * ORIGINAL saved row_residual_MAD_scale[row] * normalized_kernel_weight',
            amplitude_reference='Total positive per-active-row power in pre-existing raw median×MAD reference units; comparable total power across kernels, not physical SNR, flux or matched-filter ideal score.',
            casting='Original16x12096 little-endianfloat32 raw crop copied tofloat64; additions in ascending kernelchannel order; cast each modified row once back tofloat32; unchanged12rows reused bit-identical; reject nonfinite/nonpositive values; no clipping/redraw.',
            delta='One bin of weight1 at canonical integer center.',fixed3='Fixed engineering split1/4,1/2,1/4 at canonical integer center±1; no measured line response claim.',
            integration_smear='Unit-area uniform intrinsic width1 nativebin convolved with uniform linear exposure sweep L=abs(true_drift)*TSAMP/absDF, centered on exact UNROUNDED affine integration midpoint; bin weights are exact CDF differences then deterministic binary64 normalization.',
            kernel_weights='Each positive exact rational CDF mass converted tobinary64 once; fail mass< -1e-14; clip tinynegative to0; divide each by math.fsum(clipped_weights). No ideal-projection power rescaling.',
            source_profile_contract='Same mathematical profile family as pinned original_generator._uniform_convolution_cdf/_profile; exact affine/rational arithmetic extension explicitly differs from original float evaluation and amplitude prescription.'),
        normalization=dict(baseline='Authenticate54 original raw crops and saved metadata; recompute16 full4096 core rows and compare original power median, residual median,MAD,winsorized location before perturbed cases.',
            modified_rows='Recompute full4096 normalization for4 modified rows independently percase;12 unchanged rows reuse exact baseline normalization.',
            formula='Core raw median over4096; ratio tothatmedian;501 local median subtraction for every4096 core channel; row residual median,1.4826*MAD and center+mean(clip(residual-center,±5*MADscale)).',
            path_scoring='Same frozen exact width1 family acrossall7 windows translated toSAME injection host; direct raw501 local residual using percase normalization; four standardized terms summed/divided2.',
            halo_caution='Outside4096 core but insidecore±250 can affect local medians and residual normalization; only outsideexpanded support guarantees unchanged normalization.'),
        counts=dict(profiles=54,baseline_raw_crops=54,physical_unique_placements=108,baseline_sham_target_rows=108,
            amplitudes=2,models=3,perturbed_raw_cases=648,modified_rows_normalized=2592,baseline_rows_normalized=864,
            prior_unique_physical_placements=len(prior_keys),new_overlap_prior_physical_placements=0,
            new_model_prior_cell_overlap_counts=dict(prior_overlap),unique_new_injection_cells={k:len(v) for k,v in unique_new_cells.items()},
            all_frozen_search_family_host_raw501_checks=all_family_bins,all_frozen_search_family_host_DC_contacts=0,
            central_bins_in_core_perplacement_histogram={str(k):v for k,v in sorted(central_in_core.items())},
            kernel_row_normalization_support_classes={k:dict(v) for k,v in core_classes.items()}),
        raw501_family_support_crop_indices_inclusive=[min(a for a,b in family_support),max(b for a,b in family_support)],
        integration_sweep_range=[min(g['integration_sweep_channels_display'] for g in records),max(g['integration_sweep_channels_display'] for g in records)],
        signal_only_projection_metadata={k:dict(central4_score_per_A_range=[min(c for m,c,b in projection_metadata if m==k),max(c for m,c,b in projection_metadata if m==k)],best_frozen_family_score_per_A_range=[min(b for m,c,b in projection_metadata if m==k),max(b for m,c,b in projection_metadata if m==k)]) for k in ('delta','fixed3','integration_smear')},
        declared_profile_capture_diagnostic=dict(per_hypothesis='Average across4 active source rows of declared normalized kernelweights at the nativebin selected by that hypothesis; nonactive chosenrows contribute0; fraction=sum(weights_at_chosen_active_cells)/4.',
            oracle='Maximum ideal depositedfraction acrossALL frozen width1 hypotheses atsame host, metadata-only.',
            retained='Maximum ideal depositedfraction among actual score-selected top1/top5; descriptive only, not rankrule or acceptance threshold.',
            quantization='Diagnostic uses declared kernelweights; castfloat32 realized power/normalization can change scores and selectedpaths. This is not measuredphysical energyfraction or physical sensitivity.'),
        baselines=baselines,geometries=records,input_pins=[pin(p) for p in (gf,mf,oldf,newerf,source)],
        code_pin=pin(Path(__file__).resolve()),
        resource_envelope=dict(incremental_reserved_CPU_s=600,metadata_CPU_s_cap=60,producer_CPU_s_cap=270,QA_CPU_s_cap=270,memory_bytes_cap_each=2*1024**3,wall_s_cap_each=600,prior_ledger_retained=True,DKK=0),
        metadata_resource_usage=dict(CPU_s=cpu.ru_utime+cpu.ru_stime,wall_s=time.monotonic()-began,peak_RSS_bytes=cpu.ru_maxrss*1024),
        interpretation=['Prospective frozen engineering control on new raw-power injection cells but previously exposed2017 background; no fresh observation.',
            'delta/fixed3/integration_smear have identical total reference power perrow; central-bin power differs intentionally.',
            'Canonical central4 retention underfrozen width1 family is primary; broadsmear can produce many comparable shifted trajectories and this statistic is not all-signal recovery.',
            'No instrument response, physical sensitivity,FAP,p-value or independent case assumption established.',
            'Whole six-scan qualification chain is untested; original A/B and protected2016/closed2019 routes retain gates.'],
        preserved=dict(original_A_B='FAIL_CLOSED',qualified_SETI_detection=False,pilot_gate_pass=False,
            protected_2016=True,closed_2019=True,new_observation=False,new_telescope_requests=0,new_telescope_bytes=0,checkpoint='2026-10-20'),
        raw_spectral_arrays_opened=False,saved_scores_opened=False,observed_outcomes_scored=False)
    with (OUT/'GEOMETRY_MANIFEST.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','counts','raw501_family_support_crop_indices_inclusive','integration_sweep_range','signal_only_projection_metadata','metadata_resource_usage')}))


if __name__=='__main__':
    main()
