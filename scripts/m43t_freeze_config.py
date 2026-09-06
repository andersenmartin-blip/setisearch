"""Freeze mask policies, fresh explicit null rows and historical paired panel."""
import json
import platform
import numpy as np
from m43t_neighbor_mask import ROOT,CONFIG,sha,grid_context
from seti_repeater import search_v0p6 as core
from seti_repeater.mask_m43t import POLICIES


def main():
    s=json.loads((ROOT/'config/m43s_profile_sensitivity.json').read_text())
    r=json.loads((ROOT/'config/m43r_joint_calibration.json').read_text())
    _,grid,_=grid_context();rng=np.random.default_rng(430021);shifts=[]
    excluded=r['calibration_shifts']+r['heldout_shifts']
    while len(shifts)<256:
        a,b=map(int,rng.integers(128,grid.score_bin_count-128,size=2));row=[0,a,b];distance=abs(a-b)
        if min(distance,grid.score_bin_count-distance)<128 or row in excluded or row in shifts:continue
        shifts.append(row)
    paths=set(s['pinned_sha256'])
    paths.update(['config/m43s_profile_sensitivity.json','results_m43s_profile_sensitivity/result.json',
        'MILESTONE_43T_NEIGHBOR_MASK_PLAN.md','src/seti_repeater/mask_m43t.py','src/seti_repeater/detector_m43t.py',
        'scripts/m43t_neighbor_mask.py','scripts/m43t_freeze_config.py','tests/test_m43t_mask.py',
        'results_m43t_neighbor_mask/unit_tests.txt'])
    paths.update(f'results_m43s_profile_sensitivity/truth{t["truth_index"]:02d}.strength{a:03d}.json' for t in s['truths'] for a in (12,32))
    cfg={'milestone':'M43T','python_version':platform.python_version(),'numpy_version':np.__version__,
        **{k:s[k] for k in ('parent_template_indices','bridge','grid_sha256','truths','profiles','geometry','maximum_records')},
        'policies':POLICIES,'amplitudes':[12,32],'scramble_seed':430021,'minimum_shift_bins':128,
        'calibration_shifts':shifts[:128],'heldout_shifts':shifts[128:],
        'joint_shift_inventory_sha256':core.scramble_table_sha256(np.asarray(shifts,dtype=np.int64)),
        'old_shift_rows_excluded':len(excluded),'pinned_sha256':{p:sha(ROOT/p) for p in sorted(paths)}}
    CONFIG.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'pins':len(paths),'new_native_trials':32,'fresh_shift_rows':len(shifts)},indent=2))


if __name__=='__main__':main()
