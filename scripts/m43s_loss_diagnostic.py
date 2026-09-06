"""Retrospective explanation of completed M43S strongest-level misses.

This does not alter the frozen run, its endpoint or threshold. Scores with the
mask omitted are explanatory counterfactuals, not calibrated detections.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from m43s_profile_sensitivity import ROOT,OUT,CONFIG,frozen,grid_context
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore,NativeReceiver
from m43e_economical_bank import read_sealed,write_sealed
from seti_repeater import search_v0p6 as core
from seti_repeater.detector_m43q import catalogue_bridge,digest
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import ProfileOverlay,truth_on_factors


def run(work,source_root):
    result=read_sealed(OUT/'result.json');cfg=frozen(result['freeze_commit'])
    highest=max(cfg['amplitudes']);misses=[e for e in result['endpoints'] if e['nominal_total_epoch_strength']==highest and not e['recovered']]
    if not misses:
        write_sealed(OUT/'retrospective_loss_diagnostic.json',{'scope':'post-evaluation strongest-level misses only','cases':[],
            'original_result_sha256':result['result_sha256'],'detector_changed':False});return
    _,_,_,metadata,basis,parent,parent_table,_=build_context()
    bank,table,_=catalogue_bridge(parent,cfg['parent_template_indices'],basis);original,grid,start=grid_context()
    old=AnchorStore(work,{'parent_template_indices':cfg['parent_template_indices'],'support_carriers':original.support_bin_count})
    arrays={key:old.get(*key)[0][:,start:start+grid.support_bin_count] for key in old.expected_ids}
    provenance={'family':'M43P-exact-central-slice','parent_inventory_sha256':digest(old.inventory),
        'parent_score_ids_sha256':digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
        'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':core.proxy_carrier_grid_sha256(grid)}
    baseline=ScoreStore(arrays,provenance)
    receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
    overlay=ProfileOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
    on=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1);cases=[]
    for endpoint in misses:
        truth=endpoint['truth'];store=overlay.trial(truth,highest);saved=read_sealed(OUT/endpoint['artifact'])['audit']
        root=digest([[*key,store.expected_ids[key]] for key in sorted(store.expected_ids)])
        if root!=saved['input_inventory_sha256'] or overlay.overlay_receipt!=saved['overlay']:
            raise ValueError('diagnostic did not reproduce original injected scores')
        factors=truth_on_factors(basis,truth);q=float(grid.score_hz[truth['score_index']]+truth['fractional_proxy_bin']*grid.channel_width_hz)
        distance=np.zeros((len(bank),grid.score_bin_count),dtype='<f8')
        for e in truth['active_epochs']:
            for row in range(16):distance=np.maximum(distance,np.abs(on[:,e,row,None]*grid.score_hz-q*factors[e,row]))
        count_before=0;count_after=0;best=None;best_after=None
        for t in range(len(bank)):
            vectors={w:store.get('on',t,w)[0] for w in core.M37_SPECTRAL_WIDTHS}
            mask=core.build_m37_two_pass_template_mask(vectors.__getitem__)[:,grid.score_slice]
            if hashlib.sha256(mask.tobytes()).hexdigest()!=saved['mask_sha256s'][f'on:{t}']:
                raise ValueError('diagnostic mask differs from frozen trial')
            use=distance[t]<=20.
            for w,v in vectors.items():
                v=v[:,grid.score_slice]
                before=core.stack_hypothesis(v,truth['active_epochs'],minimum_active_epoch_snr=3.,stack_statistic='sum')
                after=core.stack_hypothesis(v,truth['active_epochs'],minimum_active_epoch_snr=3.,stack_statistic='sum',exclusion_mask=mask)
                count_before+=int(np.count_nonzero(use&(before>=10.)));count_after+=int(np.count_nonzero(use&(after>=10.)))
                if np.any(use&np.isfinite(after)):
                    maximum=float(np.max(after[use]))
                    best_after=maximum if best_after is None else max(best_after,maximum)
                if np.any(use&np.isfinite(before)):
                    qi=int(np.argmax(np.where(use,before,-np.inf)));score=float(before[qi])
                    if best is None or score>best['unmasked_active_cut_score']:
                        witnesses=[]
                        for mw,mv in vectors.items():
                            flags=core.isolated_single_epoch_mask(mv,10.,3.)
                            for e in truth['active_epochs']:
                                left=max(0,qi+grid.support_guard_bins-9);right=min(grid.support_bin_count,qi+grid.support_guard_bins+10)
                                for seed in np.flatnonzero(flags[e,left:right])+left:
                                    baseline_values=baseline.get('on',t,mw)[0][:,seed]
                                    witnesses.append({'epoch_zero_based':e,'width':mw,'seed_score_index':int(seed-grid.support_guard_bins),
                                        'injected_epoch_values':mv[:,seed].tolist(),'baseline_epoch_values':baseline_values.tolist()})
                        best={'template_index':t,'parent_template':bank[t]['m43_parent_template_index'],'score_index':qi,'width':w,
                            'unmasked_active_cut_score':score,'maximum_track_residual_hz':float(distance[t,qi]),
                            'epoch_values':v[:,qi].tolist(),'mask_by_epoch':mask[:,qi].tolist(),'isolation_seed_witnesses':witnesses}
        if count_after!=endpoint['associated_members']:raise ValueError('diagnostic retained-cell count differs from original audit')
        case={'truth_index':truth['truth_index'],'profile':truth['profile'],'nominal_total_epoch_strength':highest,
            'original_trial_artifact':endpoint['artifact'],'input_inventory_sha256':root,'all_on_mask_hashes_exact':True,
            'associated_active_cut_cells_at_threshold_without_mask':count_before,'associated_cells_at_threshold_with_mask':count_after,
            'best_unmasked_associated_member':best,'best_masked_associated_score':best_after,
            'all_above_threshold_associated_cells_removed_by_mask':count_before>0 and count_after==0,
            'original_recovered':endpoint['recovered']}
        cases.append(case);print(json.dumps({k:case[k] for k in ('truth_index','associated_active_cut_cells_at_threshold_without_mask',
            'associated_cells_at_threshold_with_mask','all_above_threshold_associated_cells_removed_by_mask')}),flush=True)
    write_sealed(OUT/'retrospective_loss_diagnostic.json',{'scope':'post-evaluation strongest-level misses only; no new detection claim',
        'original_result_sha256':result['result_sha256'],'cases':cases,'detector_changed':False,'threshold_changed':False,
        'counterfactual_mask_omission_is_not_calibrated':True,'all_replayed_score_and_mask_identities_exact':True})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--anchor-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    a=p.parse_args();run(a.anchor_root,a.source_root)
