"""Prepare metadata-only scope and known-answer identity for M43Q."""
import json
import platform
import numpy as np
from m43q_integrated_detector import ROOT,CONFIG,sha
from m43q_fixture import run_fixture
from m43f_source_cache_preflight import build_context
from seti_repeater.detector_m43q import catalogue_bridge


def main():
    p=json.loads((ROOT/'config/m43p_combined_controls.json').read_text())
    _,_,_,_,basis,parent,_,_=build_context()
    selected=[i for a,b in p['template_intervals'] for i in range(a,b)]
    _,_,bridge=catalogue_bridge(parent,selected,basis)
    _,_,full_bridge=catalogue_bridge(parent,range(len(parent)),basis)
    synthetic,_,_=run_fixture()
    paths=set(p['pinned_sha256'])
    paths.update(x.relative_to(ROOT).as_posix() for x in (ROOT/'src').rglob('*.py'))
    paths.update(x.relative_to(ROOT).as_posix() for x in (ROOT/'results_m43p_combined_controls').glob('*.json'))
    paths.update(x.relative_to(ROOT).as_posix() for x in (ROOT/'results_m43q_integrated_detector/initial_attempt').iterdir() if x.is_file())
    paths.update(['config/m43p_combined_controls.json','MILESTONE_43Q_INTEGRATED_DETECTOR_PLAN.md',
        'scripts/m43q_integrated_detector.py','scripts/m43q_fixture.py','scripts/m43q_freeze_config.py',
        'tests/test_m43q_detector.py','results_m43q_integrated_detector/unit_tests.txt','MILESTONE_43Q_AMENDMENT.md'])
    cfg={'milestone':'M43Q','numpy_version':np.__version__,'python_version':platform.python_version(),'window':p['window'],
        'parent_template_indices':selected,'support_carriers':p['support_carriers'],'score_carriers':p['score_carriers'],
        'bridge':bridge,'full_bank_bridge':full_bridge,'synthetic_result_sha256':synthetic['result_sha256'],
        'scramble_shifts':p['scramble_shifts'],'minimum_shift_bins':p['minimum_shift_bins'],
        'diagnostic_reference_floor':50.,'maximum_records':10000,
        'receiver_parent_templates':[0,1700],'receiver_score_indices':[0,p['score_carriers']//2,p['score_carriers']-1],
        'pinned_sha256':{path:sha(ROOT/path) for path in sorted(paths)}}
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'pins':len(paths),'bridge':bridge,'synthetic':synthetic['result_sha256']},indent=2))


if __name__=='__main__':main()
