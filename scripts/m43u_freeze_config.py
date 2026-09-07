"""Metadata-only M43U design: no spectral reads or score evaluation."""
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

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('nearest', 'fractional-only', 'template-offset-only', 'smear-only', 'combined')


def main():
    parent = json.loads((ROOT/'config/m43t_mask_comparison.json').read_text())
    _, _, _, metadata, basis, bank, table, _ = build_context()
    bank, table, bridge = catalogue_bridge(bank, parent['parent_template_indices'], basis)
    _, grid, _ = grid_context()
    on_factors = np.stack([core.factor_table_for_scan(table, basis, f'epoch{e+1}_on') for e in range(3)], axis=1)
    cases = []; geometry = {}
    for carrier_index, score_index in enumerate((512, 1536, 2560, 3584)):
        for anchor_index in range(2):
            old_index = 8*anchor_index + 2*carrier_index
            exact = copy.deepcopy(parent['truths'][old_index])
            offset = copy.deepcopy(parent['truths'][old_index+1])
            exact['score_index'] = offset['score_index'] = score_index
            active = exact['active_epochs']; stratum = 2*carrier_index + anchor_index
            truths = {}
            for profile in PROFILES:
                truth = copy.deepcopy(offset if profile in ('template-offset-only', 'combined') else exact)
                truth.update(truth_index=stratum, profile=profile,
                    fractional_proxy_bin=.5 if profile in ('fractional-only', 'combined') else 0.)
                geo = geometry_summary(truth, grid, on_factors, basis)
                if not geo['has_center_track_match_within_20hz']:
                    raise ValueError('predeclared metadata geometry unsupported; no substitutions')
                geometry[f'{stratum}:{profile}'] = geo; truths[profile] = truth
            def component(truth, *, kind='on', epochs=None, strength=32., component_id='signal'):
                p = truth['profile']
                return {'component_id': component_id, 'kind': kind, 'epochs': list(active if epochs is None else epochs),
                    'truth': copy.deepcopy(truth), 'strength': strength,
                    'shape': 'point' if p in ('nearest', 'template-offset-only') else 'sinc',
                    'snap_native': p not in ('fractional-only', 'combined'),
                    'smear_channels': 1. if p in ('smear-only', 'combined') else 0.}
            def add(name, components, truth=None):
                cases.append({'case_index': len(cases), 'stratum': stratum, 'case_type': name,
                    'score_index': score_index, 'local_template': exact['local_template'],
                    'active_epochs': active, 'signal_truth': truth, 'components': components})
            for p in PROFILES:
                add(p, [component(truths[p])], truths[p])
            spike = component(truths['nearest'], epochs=active[:1], component_id='strong-spike')
            add('single-epoch', [spike])
            neighbor = copy.deepcopy(truths['nearest']); neighbor['score_index'] += 6
            add('supported-spike', [spike, component(neighbor, epochs=active[1:], strength=4., component_id='nearby-weak-power')])
            add('ON-OFF', [component(truths['nearest'], component_id='ON-control'),
                           component(truths['nearest'], kind='off', component_id='OFF-control')])
            far = copy.deepcopy(truths['nearest']); far['score_index'] += 12
            add('mixed', [component(truths['combined']), component(far, epochs=active[:1], strength=128., component_id='strong-neighbor')], truths['combined'])
    excluded = set()
    for name in ('config/m43r_joint_calibration.json', 'config/m43t_mask_comparison.json', 'config/m43u_prior_neighbor2_shifts.json'):
        c = json.loads((ROOT/name).read_text())
        excluded.update(tuple(x) for x in c['calibration_shifts']+c['heldout_shifts'])
    rng = np.random.default_rng(430022); shifts = []; n = grid.score_bin_count
    while len(shifts) < 256:
        a, b = map(int, rng.integers(128, n-128, size=2)); row = (0,a,b)
        if min(abs(a-b), n-abs(a-b)) < 128 or row in excluded or list(row) in shifts:
            continue
        shifts.append(list(row))
    paths = set(parent['pinned_sha256'])
    paths.update(['config/m43t_mask_comparison.json', 'config/m43u_prior_neighbor2_shifts.json',
        'results_m43t_mask_comparison/result.json', 'MILESTONE_43U_SIGNAL_INTERFERENCE_PLAN.md',
        'src/seti_repeater/mask_m43u.py', 'src/seti_repeater/detector_m43u.py',
        'src/seti_repeater/injection_m43u.py', 'scripts/m43u_freeze_config.py',
        'scripts/m43u_signal_interference.py', 'tests/test_m43u_signal_interference.py',
        'results_m43u_signal_interference/unit_tests.txt'])
    cfg = {k: parent[k] for k in ('parent_template_indices', 'grid_sha256')}
    cfg.update(milestone='M43U', python_version=platform.python_version(), numpy_version=np.__version__,
        bridge=bridge, policies=['legacy','neighbor2','neighbor9'], cases=cases, geometry=geometry,
        maximum_records=10000, scramble_seed=430022, excluded_prior_shift_count=len(excluded),
        calibration_shifts=shifts[:128], heldout_shifts=shifts[128:],
        pinned_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)})
    (ROOT/'config/m43u_signal_interference.json').write_text(json.dumps(cfg, indent=2)+'\n')
    print(json.dumps({'cases':len(cases), 'signal_present':sum(x['signal_truth'] is not None for x in cases),
        'controls':sum(x['signal_truth'] is None for x in cases), 'maximum_geometry_residual_hz':max(x['maximum_active_row_residual_hz'] for x in geometry.values()),
        'excluded_shifts':len(excluded), 'pinned_dependencies':len(paths)}))


if __name__ == '__main__':
    main()
