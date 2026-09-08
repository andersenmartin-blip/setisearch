"""Metadata-only M43Z panel and fresh shift inventory; no spectral inspection."""
import copy,hashlib,json,platform
from pathlib import Path
import numpy as np
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from m43s_profile_sensitivity import geometry_summary
from seti_repeater import search_v0p6 as core
from seti_repeater.detector_m43u import catalogue_bridge
from seti_repeater.confirmation_m43z import POLICIES
ROOT=Path(__file__).resolve().parents[1]

def main():
    x=json.loads((ROOT/'config/m43x_confirmation.json').read_text())
    _,_,_,metadata,basis,parent,_,_=build_context()
    bank,table,bridge=catalogue_bridge(parent,x['parent_template_indices'],basis)
    _,grid,_=grid_context();factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    cases=[];geometry={};stratum=0
    for q in (896,3200):
        for active in core.M37_ACTIVITY_SUBSETS:
            for anchor in (0,36):
                old=next(c for c in x['cases'] if c['case_type']=='combined-unequal' and c['local_template']==anchor and c['active_epochs']==list(active))
                combined=copy.deepcopy(old['reference_truth'])
                exact=copy.deepcopy(next(c for c in x['cases'] if c['case_type']=='ON-OFF' and c['local_template']==anchor and c['active_epochs']==list(active))['reference_truth'])
                for t in (combined,exact):t.update(score_index=q,truth_index=stratum)
                for label,t in [('combined',combined),('exact',exact)]:
                    g=geometry_summary(t,grid,factors,basis);assert g['has_center_track_match_within_20hz']
                    geometry[f'{stratum}:{label}']=g
                ratios=[1.,.5] if len(active)==2 else [1.,.75,.5]
                rotation=stratum%len(active);ratios=ratios[rotation:]+ratios[:rotation]
                sign=1 if stratum%2==0 else -1;interference_epoch=active[stratum%len(active)]
                for strength in (24.,48.):
                    def comp(truth,cid,epochs=None,s=None,kind='on'):
                        sinc=truth['profile']=='combined'
                        return dict(component_id=cid,truth=copy.deepcopy(truth),kind=kind,epochs=list(active if epochs is None else epochs),
                            strength=strength if s is None else s,shape='sinc' if sinc else 'point',snap_native=not sinc,smear_channels=1. if sinc else 0.)
                    def shifted(delta):
                        t=copy.deepcopy(exact);t['score_index']+=delta;return t
                    unequal=[comp(combined,f'signal-epoch{e}',[e],strength*ratios[j]) for j,e in enumerate(active)]
                    distributed=[comp(shifted(d),f'distributed-offset{d:+03d}',s=strength/17) for d in range(-8,9)]
                    near=comp(shifted(sign*16),'unrelated-near-OFF',s=4*strength,kind='off')
                    far=comp(shifted(sign*96),'unrelated-far-OFF',s=4*strength,kind='off')
                    interferer=comp(shifted(sign*12),'single-epoch-interferer',[interference_epoch],4*strength)
                    pairgroup=len(cases)//10
                    def add(kind,parts,present,truth,profile,matched=None):
                        cases.append(dict(case_index=len(cases),stratum=stratum,pair_group=pairgroup,case_type=kind,strength=strength,
                            score_index=q,local_template=anchor,active_epochs=list(active),amplitude_profile=profile,
                            unequal_ratios=ratios,interference_epoch=interference_epoch,off_offset_sign=sign,signal_present=present,
                            matched_signal_only_type=matched,reference_truth=copy.deepcopy(truth),components=copy.deepcopy(parts)))
                    add('combined-unequal',unequal,True,combined,'unequal')
                    add('mixed-unequal',unequal+[interferer],True,combined,'unequal','combined-unequal')
                    add('distributed17',distributed,True,exact,'17 equal carrier components')
                    add('distributed17-near-OFF',distributed+[near],True,exact,'17 equal carrier components','distributed17')
                    add('distributed17-far-OFF',distributed+[far],True,exact,'17 equal carrier components','distributed17')
                    add('combined-near-OFF',unequal+[near],True,combined,'unequal','combined-unequal')
                    add('interferer-only',[interferer],False,combined,'absent')
                    others=[e for e in active if e!=interference_epoch]
                    add('supported-spike',[comp(exact,'spike',[interference_epoch]),comp(shifted(sign*6),'weak-support',others,strength/8)],False,exact,'control')
                    add('ON-OFF',[comp(exact,'ON-control'),comp(exact,'OFF-control',kind='off')],False,exact,'control')
                    add('OFF-only',[near],False,exact,'absent')
                stratum+=1
    # Pre-evaluation amendment: preserve original case indices, append matched
    # moderate OFF strength to separate added-cut cost from reference rejection.
    originals=copy.deepcopy(cases)
    for c in originals:
        if c['case_type']!='distributed17-near-OFF':continue
        c['case_index']=len(cases);c['case_type']='distributed17-moderate-OFF'
        c['components'][-1]['strength']=c['strength']
        c['components'][-1]['component_id']='unrelated-moderate-near-OFF'
        cases.append(c)
    excluded=set()
    for path in ('config/m43r_joint_calibration.json','config/m43t_mask_comparison.json','config/m43u_prior_neighbor2_shifts.json','config/m43u_signal_interference.json'):
        c=json.loads((ROOT/path).read_text());excluded.update(tuple(r) for r in c['calibration_shifts']+c['heldout_shifts'])
    for letter in ('w','x'):
        c=json.loads((ROOT/f'config/m43{letter}_confirmation.json').read_text());excluded.update(tuple(r) for r in c['training_shifts']+c['heldout_shifts'])
    assert len(excluded)==1536
    rng=np.random.default_rng(430026);rows=[];n=grid.score_bin_count
    while len(rows)<256:
        a,b=map(int,rng.integers(128,n-128,size=2));r=(0,a,b)
        if min(abs(a-b),n-abs(a-b))<128 or r in excluded or list(r) in rows:continue
        rows.append(list(r))
    assert len(cases)==352 and sum(c['signal_present'] for c in cases)==224
    paths=set(x['pinned_sha256'])|{'config/m43x_confirmation.json','config/m43y_response_diagnostic.json',
        'results_m43y_response_diagnostic/result.json','results_m43y_response_diagnostic/artifact_validation.json',
        'results_m43w_confirmation/anchors.json','results_m43x_confirmation/anchors.json',
        'MILESTONE_43Z_JOINT_CONTROLS_PLAN.md','MILESTONE_43Z_PLAN_AMENDMENT.md','src/seti_repeater/confirmation_m43z.py',
        'scripts/m43z_freeze_config.py','scripts/m43z_joint_controls.py','scripts/m43z_audit_report.py',
        'scripts/m43z_restore_runtime.py','tests/test_m43z_joint_controls.py','results_m43z_joint_controls/unit_tests.txt'}
    cfg=dict(milestone='M43Z',python_version=platform.python_version(),numpy_version=np.__version__,
        parent_template_indices=x['parent_template_indices'],grid_sha256=x['grid_sha256'],bridge=bridge,
        policies=list(POLICIES),cases=cases,geometry=geometry,maximum_records=10000,
        training_shifts=rows[:128],heldout_shifts=rows[128:],excluded_prior_rows=1536,scramble_seed=430026,
        confirmation_floor=5.5,unchanged_arithmetic_anchors=['results_m43w_confirmation/anchors.json','results_m43x_confirmation/anchors.json'],
        pinned_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)})
    (ROOT/'config/m43z_joint_controls.json').write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps(dict(inputs=len(cases),signal_inputs=224,pure_controls=128,endpoints=1408,pins=len(paths),excluded=len(excluded))))
if __name__=='__main__':main()
