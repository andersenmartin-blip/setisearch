#!/usr/bin/env python3
"""Execute the publicly frozen bounded M43R joint calibration pilot."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import time
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore,NativeReceiver
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43r as detector
from seti_repeater.injection_m43r import ScoreStore,NativeOverlay

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43r_joint_calibration'
CONFIG=ROOT/'config/m43r_joint_calibration.json'
WINDOW='m43r-central-native-pilot'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def grid_context():
    original=core.make_m37_proxy_carrier_grid('m37_1412p5')
    grid=core.make_proxy_carrier_grid(1412.5,original.channel_width_hz,2048,64)
    start=(original.support_bin_count-grid.support_bin_count)//2
    if not np.array_equal(original.support_hz[start:start+grid.support_bin_count].view('<u8'),grid.support_hz.view('<u8')):
        raise ValueError('central grid is not a bit-identical ancestor slice')
    return original,grid,start


def frozen(commit):
    cfg=json.loads(CONFIG.read_text())
    if subprocess.check_output(['git','show',commit+':config/m43r_joint_calibration.json'],cwd=ROOT)!=CONFIG.read_bytes():
        raise ValueError('configuration differs from public freeze')
    for name,h in cfg['pinned_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('frozen dependency changed: '+name)
    if np.__version__!=cfg['numpy_version'] or platform.python_version()!=cfg['python_version']:
        raise ValueError('numerical runtime changed')
    return cfg


def compact(result,overlay):
    decisions={d['record_id']:d for d in result['decisions']}
    members=[]
    for r in result['retained']['on']:
        members.append({k:r[k] for k in ('record_id','template_index','proxy_carrier_index',
            'spectral_width_channels','active_epochs_zero_based','snr','epoch_values_at_proxy_carrier')}|decisions[r['record_id']])
    return {'pipeline_result_sha256':result['result_sha256'],'overlay':overlay,
        'threshold':result['threshold'],'input_inventory_sha256':result['input_inventory_sha256'],
        'mask_sha256s':result['mask_sha256s'],'retention_certificates':result['retention_certificates'],
        'off_match_certificate':result['off_track']['certificate'],
        'adjacent_off_certificate':result['adjacent_off']['certificate'],
        'receiver_alias_certificate':result['receiver_alias']['certificate'],
        'receiver_receipt_sha256':detector.digest(result['receiver_receipt']),
        'rank_sha256':detector.digest(result['rank']),'members':members,
        'on_retained':len(result['retained']['on']),'off_retained':len(result['retained']['off']),
        'all_member_physical_survivors':sum(d['passes_evaluated_physical_vetoes'] for d in result['decisions']),
        'scientific_candidate_selection_authorized':False}


def endpoint(audit,truth,store,baseline,grid,amplitude,artifact):
    t=truth['local_template'];q=truth['score_index'];active=truth['active_epochs']
    matching=[m for m in audit['members'] if m['template_index']==t and m['proxy_carrier_index']==q and m['active_epochs_zero_based']==active]
    physical=[m for m in matching if m['passes_evaluated_physical_vetoes']]
    final=[m for m in physical if m['meets_diagnostic_rank_cut']]
    mask=core.build_m37_two_pass_template_mask(lambda w:store.get('on',t,w)[0])[:,grid.score_slice]
    values=store.get('on',t,1)[0][:,grid.score_slice][:,q]
    previous=baseline.get('on',t,1)[0][:,grid.score_slice][:,q]
    return {'truth':truth,'nominal_epoch_snr':amplitude,'artifact':artifact,
        'retained':bool(matching),'passes_physical_vetoes':bool(physical),'recovered':bool(final),
        'matching_members':len(matching),'matching_physical_survivors':len(physical),'matching_final_survivors':len(final),
        'matching_member_ids':[m['record_id'] for m in matching],
        'width1_epoch_values':values.tolist(),'width1_increments':(values.astype('<f8')-previous.astype('<f8')).tolist(),
        'truth_mask_by_epoch':mask[:,q].tolist(),'zero_level_reuses_one_baseline':amplitude==0}


def run(work,source_root,freeze):
    cfg=frozen(freeze);started=time.monotonic();OUT.mkdir(exist_ok=True)
    try:
        _,_,_,metadata,basis,parent,parent_table,_=build_context()
        bank,table,bridge=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
        if bridge!=cfg['bridge']:raise ValueError('catalogue bridge changed')
        original,grid,start=grid_context()
        if core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256']:raise ValueError('grid changed')
        old=AnchorStore(work,{'parent_template_indices':cfg['parent_template_indices'],'support_carriers':original.support_bin_count})
        arrays={key:old.get(*key)[0][:,start:start+grid.support_bin_count] for key in old.expected_ids}
        provenance={'family':'M43P-exact-central-slice','parent_inventory_sha256':detector.digest(old.inventory),
            'parent_score_ids_sha256':detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
            'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':cfg['grid_sha256']}
        baseline=ScoreStore(arrays,provenance)
        print('96 M43P arrays verified; central baseline scores retained',flush=True)
        common=dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
        calibration,calibration_summary=detector.calibrate(**common,store=baseline,shifts=np.asarray(cfg['calibration_shifts'],dtype=np.int64),
            minimum_shift_bins=cfg['minimum_shift_bins'],progress=lambda m:print('training '+m,flush=True))
        threshold=core.calibrated_threshold((calibration,),expected_window_ids=(WINDOW,),reference_floor=cfg['reference_floor'],
            quantile=1.,scientific_p_ceiling=.01)
        write_sealed(OUT/'calibration.json',{'freeze_commit':freeze,'baseline_provenance':provenance,
            'calibration':calibration_summary,'null_maxima':calibration.null_maxima.tolist(),'threshold':threshold.as_record()})
        print(f'Fixed baseline threshold: {threshold.operational_threshold_snr}; certificate saved before held-out evaluation',flush=True)
        heldout,heldout_summary=detector.calibrate(**common,store=baseline,shifts=np.asarray(cfg['heldout_shifts'],dtype=np.int64),
            minimum_shift_bins=cfg['minimum_shift_bins'],progress=lambda m:print('held-out '+m,flush=True))
        values=heldout.null_maxima;cut=threshold.operational_threshold_snr
        null_result={'freeze_commit':freeze,'calibration':heldout_summary,'null_maxima':values.tolist(),
            'denominator':len(values),'at_or_above_threshold':int(np.count_nonzero(values>=cut)),
            'strictly_above_threshold':int(np.count_nonzero(values>cut)),
            'inclusive_ranks':[(1+int(np.count_nonzero(calibration.null_maxima>=v)))/(len(calibration.null_maxima)+1) for v in values],
            'threshold_certificate_sha256':threshold.certificate_sha256,
            'scope':'correlated within-sequence resampled pre-veto score exceedances; not physical false-alarm probability'}
        write_sealed(OUT/'heldout.json',null_result)
        print(f'Held-out pre-veto exceedances: {null_result["at_or_above_threshold"]}/{len(values)}',flush=True)
        receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
        overlay=NativeOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
        write_sealed(OUT/'native_anchors.json',{'cache_inventory':overlay.cache_inventory,
            'verified_cropped_epoch_score_cells':3*len(bank)*len(core.M37_SPECTRAL_WIDTHS)*grid.support_bin_count,
            'background_provenance':provenance,'complete':True})
        fixed=dict(**common,calibration=calibration,threshold=threshold,receiver_factory=overlay,maximum_records=cfg['maximum_records'])
        result=detector.execute(**fixed,store=baseline)
        background=compact(result,overlay.overlay_receipt);write_sealed(OUT/'baseline.json',background)
        print(f'Baseline complete: ON {background["on_retained"]}, OFF {background["off_retained"]}',flush=True)
        endpoints=[]
        for truth in cfg['truths']:
            endpoints.append(endpoint(background,truth,baseline,baseline,grid,0,'baseline.json'))
            for amplitude in cfg['amplitudes'][1:]:
                trial_start=time.monotonic();store=overlay.trial(truth,amplitude)
                result=detector.execute(**fixed,store=store)
                audit=compact(result,overlay.overlay_receipt)
                name=f'truth{truth["truth_index"]:02d}.snr{amplitude:03d}.json'
                outcome=endpoint(audit,truth,store,baseline,grid,amplitude,name)
                write_sealed(OUT/name,{'audit':audit,'endpoint':outcome,'wall_seconds':round(time.monotonic()-trial_start,3)})
                endpoints.append(outcome)
                write_sealed(OUT/'progress.json',{'completed_endpoints':len(endpoints),'planned_endpoints':32,'endpoints':endpoints,'complete':False})
                print(f'truth {truth["truth_index"]} SNR {amplitude}: retained={outcome["retained"]} physical={outcome["passes_physical_vetoes"]} recovered={outcome["recovered"]}; {time.monotonic()-trial_start:.1f}s',flush=True)
        summary=[{'nominal_epoch_snr':a,'denominator':sum(e['nominal_epoch_snr']==a for e in endpoints),
            **{k:sum(e[k] for e in endpoints if e['nominal_epoch_snr']==a) for k in ('retained','passes_physical_vetoes','recovered')}} for a in cfg['amplitudes']]
        if len(endpoints)!=32:raise ValueError('endpoint denominator incomplete')
        write_sealed(OUT/'result.json',{'milestone':'M43R','status':'bounded-joint-pilot-complete','freeze_commit':freeze,
            'config_sha256':sha(CONFIG),'wall_seconds':round(time.monotonic()-started,3),'summary':summary,'endpoints':endpoints,
            'heldout_at_or_above_threshold':null_result['at_or_above_threshold'],'heldout_denominator':len(values),
            'threshold':threshold.as_record(),'distinct_detector_executions':25,'zero_level_endpoint_reuses':8,
            'telescope_requests':0,'full_bank_search':False,'physical_false_alarm_probability_measured':False,
            'scientific_candidate_selection_authorized':False})
        write_sealed(OUT/'progress.json',{'completed_endpoints':32,'planned_endpoints':32,'complete':True})
        print(json.dumps(summary,indent=2),flush=True)
    except BaseException as error:
        write_sealed(OUT/'failure.json',{'milestone':'M43R','freeze_commit':freeze,'error':repr(error),'complete':False})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True);p.add_argument('--anchor-root',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();run(a.anchor_root,a.source_root,a.freeze_commit)
