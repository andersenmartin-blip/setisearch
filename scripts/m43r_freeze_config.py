"""Freeze metadata, explicit unique shift inventory and unobserved truths."""
import json
import platform
import numpy as np
from m43r_joint_calibration import ROOT,OUT,CONFIG,sha,grid_context
from m43f_source_cache_preflight import build_context
from seti_repeater import search_v0p6 as core
from seti_repeater.detector_m43q import catalogue_bridge


def main():
    q=json.loads((ROOT/'config/m43q_integrated_detector.json').read_text())
    _,_,_,_,basis,parent,_,_=build_context()
    selection=q['parent_template_indices'];_,_,bridge=catalogue_bridge(parent,selection,basis)
    original,grid,start=grid_context();rng=np.random.default_rng(430018);shifts=[]
    while len(shifts)<256:
        a,b=map(int,rng.integers(128,grid.score_bin_count-128,size=2))
        row=[0,a,b];distance=abs(a-b)
        if min(distance,grid.score_bin_count-distance)<128 or row in shifts:continue
        shifts.append(row)
    truths=[{'truth_index':i,'parent_template':t,'local_template':selection.index(t),
        'active_epochs':list(subset),'score_index':2048} for i,(t,subset) in enumerate(
            (t,s) for t in (0,1700) for s in core.M37_ACTIVITY_SUBSETS)]
    paths=set(q['pinned_sha256'])
    paths.update(['config/m43q_integrated_detector.json','results_m43q_integrated_detector/qualification.json',
        'MILESTONE_43R_JOINT_CALIBRATION_PLAN.md','src/seti_repeater/detector_m43r.py',
        'src/seti_repeater/injection_m43r.py','scripts/m43r_joint_calibration.py','scripts/m43r_freeze_config.py',
        'tests/test_m43r_calibration.py','results_m43r_joint_calibration/unit_tests.txt'])
    cfg={'milestone':'M43R','python_version':platform.python_version(),'numpy_version':np.__version__,
        'parent_template_indices':selection,'bridge':bridge,'grid_sha256':core.proxy_carrier_grid_sha256(grid),
        'score_carriers':grid.score_bin_count,'support_carriers':grid.support_bin_count,'parent_support_slice_start':start,
        'scramble_seed':430018,'minimum_shift_bins':128,'calibration_shifts':shifts[:128],'heldout_shifts':shifts[128:],
        'joint_shift_inventory_sha256':core.scramble_table_sha256(np.asarray(shifts,dtype=np.int64)),
        'reference_floor':10.,'maximum_records':10000,'amplitudes':[0,8,32,64],'truths':truths,
        'pinned_sha256':{p:sha(ROOT/p) for p in sorted(paths)}}
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'pins':len(paths),'score_carriers':grid.score_bin_count,'truths':len(truths),'shift_rows':len(shifts)},indent=2))


if __name__=='__main__':main()
