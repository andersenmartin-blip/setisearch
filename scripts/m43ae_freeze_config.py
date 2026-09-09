"""Specify M43AE without evaluating a new policy or additional input."""
import copy
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed
from seti_repeater.attribution_m43ae import POLICIES, POLICY_HYPOTHESES

ROOT=Path(__file__).resolve().parents[1]


def main():
    ad=json.loads((ROOT/'config/m43ad_geometry.json').read_text())
    ab=json.loads((ROOT/'config/m43ab_attribution.json').read_text())
    result=read_sealed(ROOT/'results_m43ad_geometry/result.json')
    previous=read_sealed(ROOT/'results_m43ab_attribution/result.json')
    inventory={r['name']:r for r in result['inventory']}
    cases=[]
    for old in ad['cases']:
        c=copy.deepcopy(old)
        c.update(name='ad_'+old['name'],source_name=old['name'],panel='historical',m43ad_panel=old['panel'])
        cases.append(c)
    assert len(cases)==149 and sum(c['signal_present'] for c in cases)==83
    for old in ad['cases']:
        if old['panel']!='fresh':continue
        c=copy.deepcopy(old);target={1280:1792,2816:2304}[old['score_index']];delta=target-old['score_index']
        c['score_index']=target;c['reference_truth']['score_index']+=delta
        for part in c['components']:part['truth']['score_index']+=delta
        c.update(name=f'fresh{len(cases)-149:03d}',source_name=None,panel='fresh',m43ad_specification_source=old['name'])
        assert c['strength']==28.
        cases.append(c)
    for i,c in enumerate(cases):c['case_index']=i
    fresh=cases[149:]
    assert len(fresh)==112 and sum(c['signal_present'] for c in fresh)==64
    specifications={json.dumps(c['components'],sort_keys=True) for c in ad['cases']+ab['cases']}
    assert all(json.dumps(c['components'],sort_keys=True) not in specifications for c in fresh)
    paths=set(ad['pinned_sha256'])|{
        'config/m43ad_geometry.json','results_m43ad_geometry/result.json','results_m43ad_geometry/audit.json',
        'results_m43ad_geometry/archive/manifest.json','MILESTONE_43AD_GEOMETRY_RESULT.md',
        'M43AD_PUBLICATION_COMPLETED.md','MILESTONE_43AE_JOINT_RESPONSE_PLAN.md',
        'src/seti_repeater/attribution_m43ae.py','scripts/m43ae_joint_response.py',
        'scripts/m43ae_freeze_config.py','scripts/m43ae_audit.py',
        'tests/test_m43ae_attribution.py','tests/test_m43ae_runner.py'}
    paths.update(i['file'] for i in inventory.values())
    cfg=dict(milestone='M43AE',source_commit='657e0a425ebc340604fc8bf6fd3efb53f39c2eed',
        python_version=platform.python_version(),numpy_version=np.__version__,
        dependencies={n:importlib.metadata.version(n) for n in ('numpy','astropy','h5py','hdf5plugin')},
        cases=cases,historical_sources=inventory,upstream_replay_anchors=['baseline','ab_z138','new038'],
        historical_inputs=149,historical_signal_inputs=83,historical_control_inputs=66,
        prospective_new_inputs=112,prospective_signal_inputs=64,prospective_control_inputs=48,
        policies=ad['policies']+list(POLICIES),new_policy_hypotheses=POLICY_HYPOTHESES,
        score_floor=5.5,correlation_floor=.8,new_nominal_strength=28.,new_score_indices=[1792,2304],
        parent_template_indices=ad['parent_template_indices'],bridge=ad['bridge'],grid_sha256=ad['grid_sha256'],
        maximum_records=ad['maximum_records'],new_null_rows=0,prior_null_rows_to_exclude=1792,
        previous_native_payload_identities=sorted({r['native_payload_identity'] for r in result['inventory']+previous['inventory']}),
        pinned_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)})
    (ROOT/'config/m43ae_joint_response.json').write_text(json.dumps(cfg,separators=(',',':'))+'\n')
    print(json.dumps(dict(historical=149,fresh=112,baseline=1,policy_endpoints=3406,
        reused_policy_endpoints=1500,new_policy_endpoints=1906,pinned_files=len(paths))))


if __name__=='__main__':main()
