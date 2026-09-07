"""Metadata-only prospective freeze; no native score evaluation."""
import json
import platform
import numpy as np
from m43t_mask_comparison import ROOT, CONFIG, sha
from seti_repeater import search_v0p6 as core


def main():
    parent = json.loads((ROOT / 'config/m43s_profile_sensitivity.json').read_text())
    r = json.loads((ROOT / 'config/m43r_joint_calibration.json').read_text())
    excluded = {tuple(row) for row in r['calibration_shifts'] + r['heldout_shifts']}
    rng = np.random.default_rng(430020); shifts = []; n = r['score_carriers']
    while len(shifts) < 256:
        a, b = map(int, rng.integers(128, n-128, size=2)); row = (0, a, b)
        if min(abs(a-b), n-abs(a-b)) < 128 or row in excluded or list(row) in shifts:
            continue
        shifts.append(list(row))
    paths = set(parent['pinned_sha256'])
    paths.update(['config/m43s_profile_sensitivity.json',
        'results_m43s_profile_sensitivity/result.json',
        'results_m43s_profile_sensitivity/retrospective_loss_diagnostic.json',
        'MILESTONE_43T_MASK_COMPARISON_PLAN.md', 'src/seti_repeater/mask_m43t.py',
        'src/seti_repeater/detector_m43t.py', 'scripts/m43t_mask_comparison.py',
        'scripts/m43t_freeze_config.py', 'tests/test_m43t_mask_comparison.py',
        'results_m43t_mask_comparison/unit_tests.txt'])
    cfg = {key: parent[key] for key in ('parent_template_indices', 'bridge', 'grid_sha256',
                                       'profiles', 'truths', 'geometry')}
    cfg.update(milestone='M43T', python_version=platform.python_version(), numpy_version=np.__version__,
        mask_policies=['legacy', 'neighbor9'], amplitudes=[0, 6, 8, 12, 32],
        maximum_records=10000, scramble_seed=430020, minimum_shift_bins=128,
        calibration_shifts=shifts[:128], heldout_shifts=shifts[128:],
        joint_shift_inventory_sha256=core.scramble_table_sha256(np.asarray(shifts, dtype=np.int64)),
        reference_floor=10., rank_ceiling=.01, excluded_m43r_shift_count=len(excluded),
        pinned_sha256={p: sha(ROOT/p) for p in sorted(paths)})
    CONFIG.write_text(json.dumps(cfg, indent=2)+'\n')
    print(json.dumps({'pinned_dependencies': len(paths), 'truths': len(cfg['truths']),
                      'distinct_shift_rows': len(shifts), 'new_detector_executions': 130, 'endpoints': 160}))


if __name__ == '__main__':
    main()
