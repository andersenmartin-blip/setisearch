"""Build the M43AB panel from metadata; never read new trial scores."""
import copy
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
from seti_repeater.attribution_m43ab import POLICIES

ROOT = Path(__file__).resolve().parents[1]


def main():
    z = json.loads((ROOT/'config/m43z_joint_controls.json').read_text())
    aa = json.loads((ROOT/'config/m43aa_native_response.json').read_text())
    selected = sorted(set(aa['historical_cases']) | {38, 78, 138, 148, 158, 198, 278, 318})
    cases = []
    for i in selected:
        c = copy.deepcopy(z['cases'][i])
        c.update(name=f'z{i:03d}', panel='historical', original_case_index=i)
        cases.append(c)
    kinds = ('combined-unequal', 'mixed-unequal', 'distributed17',
             'distributed17-moderate-OFF', 'interferer-only', 'supported-spike', 'ON-OFF')
    for q in (1536, 2560):
        for active in ([0, 1], [0, 2], [1, 2], [0, 1, 2]):
            for anchor in (0, 36):
                for kind in kinds:
                    c = copy.deepcopy(next(c for c in z['cases'] if c['score_index'] == 896
                        and c['strength'] == 24. and c['active_epochs'] == active
                        and c['local_template'] == anchor and c['case_type'] == kind))
                    old_index = c['case_index']; delta = q-c['score_index']
                    c['score_index'] = q; c['strength'] = 32.
                    c['reference_truth']['score_index'] += delta
                    for part in c['components']:
                        part['truth']['score_index'] += delta
                        part['strength'] *= 32./24.
                    c.update(name=f'fresh{len(cases)-len(selected):03d}', panel='fresh',
                             original_case_index=None, source_spec_case_index=old_index)
                    cases.append(c)
    for i, c in enumerate(cases):
        c['case_index'] = i
    assert len(cases) == 148 and len(selected) == 36
    fresh = [c for c in cases if c['panel'] == 'fresh']
    assert sum(c['signal_present'] for c in fresh) == 64
    # Pins include the complete Z dependency chain and the new computation.
    paths = set(z['pinned_sha256']) | {
        'config/m43z_joint_controls.json', 'results_m43z_joint_controls/calibration.json',
        'results_m43z_joint_controls/result.json', 'results_m43z_joint_controls/baseline.json',
        'results_m43z_joint_controls/case_audits.jsonl.gz',
        'scripts/m43aa_native_response.py', 'scripts/m43ab_attribution.py',
        'scripts/m43ab_freeze_config.py', 'src/seti_repeater/attribution_m43ab.py',
        'tests/test_m43ab_attribution.py', 'MILESTONE_43AB_ATTRIBUTION_PLAN.md'}
    cfg = dict(milestone='M43AB', python_version=platform.python_version(), numpy_version=np.__version__,
        historical_cases=selected, cases=cases, prospective_new_inputs=112,
        policies=list(z['policies'])+list(POLICIES), parent_template_indices=z['parent_template_indices'],
        grid_sha256=z['grid_sha256'], bridge=z['bridge'], maximum_records=z['maximum_records'],
        new_null_rows=0, prior_null_rows_to_exclude=1792,
        pinned_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)})
    (ROOT/'config/m43ab_attribution.json').write_text(json.dumps(cfg, separators=(',', ':'))+'\n')
    print(json.dumps(dict(historical=36, fresh=112, separate_baseline=1, endpoints=149*7,
                         pinned_files=len(paths))))


if __name__ == '__main__':
    main()
