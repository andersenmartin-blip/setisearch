"""Metadata-only M43S truth inventory and prospective dependency freeze."""
import json
import platform
import numpy as np
from m43s_profile_sensitivity import ROOT,CONFIG,sha,grid_context,geometry_summary
from m43f_source_cache_preflight import build_context
from m43e_economical_bank import read_sealed
from seti_repeater import search_v0p6 as core
from seti_repeater.detector_m43q import catalogue_bridge


def main():
    r=json.loads((ROOT/'config/m43r_joint_calibration.json').read_text())
    _,_,_,_,basis,parent,_,_=build_context();selection=r['parent_template_indices']
    bank,table,bridge=catalogue_bridge(parent,selection,basis)
    _,grid,_=grid_context();truths=[];midpoints={};selection_checks={}
    on_factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    profiles=['ideal-native-bin','fractional-off-template-smear']
    for anchor,partner,q in ((0,1,1024),(1700,1699,3072)):
        for subset in core.M37_ACTIVITY_SUBSETS:
            for profile in profiles:
                off=profile==profiles[1]
                truth={'truth_index':len(truths),'profile':profile,'parent_anchor':anchor,
                    'midpoint_partner':partner if off else None,'local_template':selection.index(anchor),
                    'active_epochs':list(subset),'score_index':q,'fractional_proxy_bin':.5 if off else 0.,
                    'coefficient_x':(parent[anchor]['coefficient_x']+parent[partner]['coefficient_x'])/2 if off else parent[anchor]['coefficient_x'],
                    'coefficient_y':(parent[anchor]['coefficient_y']+parent[partner]['coefficient_y'])/2 if off else parent[anchor]['coefficient_y']}
                truth['coefficient_fraction_toward_partner']=.5 if off else 0.
                if off:
                    midpoints[str(len(truths))]=geometry_summary(truth,grid,on_factors,basis)
                    checks=[]
                    for power in range(1,25):
                        fraction=2.**(-power)
                        truth['coefficient_fraction_toward_partner']=fraction
                        for axis in ('coefficient_x','coefficient_y'):
                            truth[axis]=parent[anchor][axis]+fraction*(parent[partner][axis]-parent[anchor][axis])
                        g=geometry_summary(truth,grid,on_factors,basis)
                        checks.append({'fraction':fraction,**g})
                        if g['maximum_active_row_residual_hz']<=grid.channel_width_hz:break
                    else:raise ValueError('no supported dyadic perturbation')
                    selection_checks[str(len(truths))]=checks
                truths.append(truth)
    on_factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    geometry={str(t['truth_index']):geometry_summary(t,grid,on_factors,basis) for t in truths}
    paths=set(r['pinned_sha256'])
    paths.update(['config/m43r_joint_calibration.json','results_m43r_joint_calibration/calibration.json',
        'results_m43r_joint_calibration/baseline.json','results_m43r_joint_calibration/native_anchors.json',
        'results_m43r_joint_calibration/heldout.json','results_m43r_joint_calibration/result.json',
        'MILESTONE_43S_PROFILE_SENSITIVITY_PLAN.md','src/seti_repeater/injection_m43s.py',
        'scripts/m43s_profile_sensitivity.py','scripts/m43s_freeze_config.py',
        'tests/test_m43s_profiles.py','results_m43s_profile_sensitivity/unit_tests.txt'])
    cal=read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')
    cfg={'milestone':'M43S','python_version':platform.python_version(),'numpy_version':np.__version__,
        'parent_template_indices':selection,'bridge':bridge,'grid_sha256':core.proxy_carrier_grid_sha256(grid),
        'calibration_artifact_sha256':cal['result_sha256'],'threshold_certificate_sha256':cal['threshold']['certificate_sha256'],
        'maximum_records':10000,'amplitudes':[0,2,4,6,8,12,32],'profiles':profiles,'truths':truths,'geometry':geometry,
        'geometric_midpoint_controls':midpoints,'metadata_dyadic_selection_checks':selection_checks,
        'selection_rule':'largest dyadic fraction 2^-k, k=1..24, whose best maximum active-row residual is <= one native channel',
        'pinned_sha256':{p:sha(ROOT/p) for p in sorted(paths)}}
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'pins':len(paths),'truths':len(truths),'endpoints':len(truths)*len(cfg['amplitudes']),
        'max_nearest_geometry_residual_hz':max(g['maximum_active_row_residual_hz'] for g in geometry.values())},indent=2))


if __name__=='__main__':main()
