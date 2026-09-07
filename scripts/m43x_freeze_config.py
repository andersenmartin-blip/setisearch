"""M43X metadata-only prospective panel; no score inspection."""
import copy
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from m43s_profile_sensitivity import geometry_summary
from seti_repeater import search_v0p6 as core
from seti_repeater.detector_m43u import catalogue_bridge
from seti_repeater.confirmation_m43x import POLICIES
ROOT=Path(__file__).resolve().parents[1]

def main():
    u=json.loads((ROOT/'config/m43u_signal_interference.json').read_text())
    w=json.loads((ROOT/'config/m43w_confirmation.json').read_text())
    _,_,_,metadata,basis,parent,_,_=build_context()
    bank,table,bridge=catalogue_bridge(parent,u['parent_template_indices'],basis)
    _,grid,_=grid_context()
    factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    cases=[];geometry={};stratum=0
    for q in (1280,2816):
        for active in core.M37_ACTIVITY_SUBSETS:
            for anchor in (0,36):
                source=next(c for c in u['cases'] if c['case_type']=='mixed' and c['local_template']==anchor and c['active_epochs']==list(active))
                exact=copy.deepcopy(source['components'][1]['truth']);combined=copy.deepcopy(source['signal_truth'])
                for truth in (exact,combined):truth.update(score_index=q,truth_index=stratum,active_epochs=list(active))
                for label,truth in (('nearest',exact),('combined',combined)):
                    geo=geometry_summary(truth,grid,factors,basis)
                    if not geo['has_center_track_match_within_20hz']:raise ValueError('fixed metadata geometry unsupported')
                    geometry[f'{stratum}:{label}']=geo
                ratios=[1.,.5] if len(active)==2 else [1.,.75,.5]
                rotation=stratum%len(active);ratios=ratios[rotation:]+ratios[:rotation]
                for strength in (16.,40.):
                    def comp(truth,component_id,epochs=None,s=None,kind='on'):
                        is_combined=truth['profile']=='combined'
                        return dict(component_id=component_id,truth=copy.deepcopy(truth),kind=kind,
                            epochs=list(active if epochs is None else epochs),strength=strength if s is None else s,
                            shape='sinc' if is_combined else 'point',snap_native=not is_combined,
                            smear_channels=1. if is_combined else 0.)
                    def signal_parts(truth,unequal):
                        return [comp(truth,f'signal-epoch{e}',[e],strength*(ratios[i] if unequal else 1.)) for i,e in enumerate(active)]
                    far=copy.deepcopy(exact);far['score_index']+=12
                    near=copy.deepcopy(exact);near['score_index']+=6
                    interference_epoch=active[stratum%len(active)]
                    interferer=comp(far,'interferer',[interference_epoch],4*strength)
                    equal=signal_parts(combined,False);unequal=signal_parts(combined,True)
                    def add(kind,components,present,truth,profile):
                        cases.append(dict(case_index=len(cases),stratum=stratum,case_type=kind,
                            strength=strength,score_index=q,local_template=anchor,active_epochs=list(active),
                            amplitude_profile=profile,unequal_ratios=ratios,interference_epoch=interference_epoch,
                            signal_present=present,reference_truth=copy.deepcopy(truth),components=copy.deepcopy(components)))
                    add('nearest-unequal',signal_parts(exact,True),True,exact,'unequal')
                    add('combined-equal',equal,True,combined,'equal')
                    add('combined-unequal',unequal,True,combined,'unequal')
                    add('mixed-equal',equal+[interferer],True,combined,'equal')
                    add('mixed-unequal',unequal+[interferer],True,combined,'unequal')
                    add('interferer-only',[interferer],False,combined,'absent')
                    others=[e for e in active if e!=interference_epoch]
                    add('supported-spike',[comp(exact,'spike',[interference_epoch]),comp(near,'weak-support',others,strength/8)],False,exact,'control')
                    add('ON-OFF',[comp(exact,'ON-control'),comp(exact,'OFF-control',kind='off')],False,exact,'control')
                stratum+=1
    excluded=set()
    for path in ('config/m43r_joint_calibration.json','config/m43t_mask_comparison.json','config/m43u_prior_neighbor2_shifts.json','config/m43u_signal_interference.json'):
        c=json.loads((ROOT/path).read_text());excluded.update(tuple(x) for x in c['calibration_shifts']+c['heldout_shifts'])
    excluded.update(tuple(x) for x in w['training_shifts']+w['heldout_shifts'])
    assert len(excluded)==1280
    rng=np.random.default_rng(430024);rows=[];n=grid.score_bin_count
    while len(rows)<256:
        a,b=map(int,rng.integers(128,n-128,size=2));row=(0,a,b)
        if min(abs(a-b),n-abs(a-b))<128 or row in excluded or list(row) in rows:continue
        rows.append(list(row))
    assert len(cases)==256 and sum(c['signal_present'] for c in cases)==160
    assert len({json.dumps(c['components'],sort_keys=True) for c in cases})==256
    paths=set(w['pinned_sha256'])|{'config/m43w_confirmation.json',
        'results_m43w_confirmation/result.json','results_m43w_confirmation/artifact_validation.json',
        'MILESTONE_43X_CONFIRMATION_PLAN.md','src/seti_repeater/confirmation_m43x.py',
        'scripts/m43x_freeze_config.py','scripts/m43x_confirmation.py','scripts/m43x_audit_report.py',
        'tests/test_m43x_confirmation.py','results_m43x_confirmation/unit_tests.txt'}
    cfg=dict(milestone='M43X',python_version=platform.python_version(),numpy_version=np.__version__,
        parent_template_indices=u['parent_template_indices'],grid_sha256=u['grid_sha256'],bridge=bridge,
        policies=list(POLICIES),cases=cases,geometry=geometry,maximum_records=10000,
        remaining_statistic='float64 sum of active scores excluding first maximum, divided by sqrt(active_count-1)',
        confirmation_floor=5.5,training_shifts=rows[:128],heldout_shifts=rows[128:],excluded_prior_rows=1280,scramble_seed=430024,
        anchor_query_positions=[0,1,2048,4095,4096],
        pinned_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)})
    (ROOT/'config/m43x_confirmation.json').write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'cases':len(cases),'strata':stratum,'signal_inputs':160,'control_inputs':96,
        'policy_endpoints':len(cases)*3,'geometry_max_hz':max(g['maximum_active_row_residual_hz'] for g in geometry.values()),'pins':len(paths)}))
if __name__=='__main__':main()
