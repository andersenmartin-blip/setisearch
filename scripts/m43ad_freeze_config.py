"""Build the M43AD specification without reading new endpoint scores."""
import copy
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
from seti_repeater.attribution_m43ad import POLICIES

ROOT = Path(__file__).resolve().parents[1]


def main():
    ab = json.loads((ROOT/'config/m43ab_attribution.json').read_text())
    source = json.loads((ROOT/'results_m43ab_attribution/result.json').read_text())
    inventory = {r['name']: r for r in source['inventory']}
    cases = []
    for old in ab['cases']:
        if old['panel'] == 'historical' or old['name'] == 'fresh032':
            c = copy.deepcopy(old)
            c.update(name='ab_'+old['name'], source_name=old['name'], panel='historical')
            cases.append(c)
    assert len(cases) == 37 and sum(c['signal_present'] for c in cases) == 19
    for old in ab['cases']:
        if old['panel'] != 'fresh': continue
        c = copy.deepcopy(old)
        target = {1536: 1280, 2560: 2816}[old['score_index']]
        delta = target-old['score_index']
        c['score_index'] = target; c['reference_truth']['score_index'] += delta
        c['strength'] = 28.
        for part in c['components']:
            part['truth']['score_index'] += delta
            part['strength'] *= 28./old['strength']
        c.update(name=f'new{len(cases)-37:03d}', source_name=None, panel='fresh')
        cases.append(c)
    for i,c in enumerate(cases): c['case_index'] = i
    fresh = [c for c in cases if c['panel'] == 'fresh']
    assert len(fresh) == 112 and sum(c['signal_present'] for c in fresh) == 64
    old_components = {json.dumps(c['components'], sort_keys=True) for c in ab['cases']}
    assert all(json.dumps(c['components'],sort_keys=True) not in old_components for c in fresh)
    names = ['baseline']+[c['source_name'] for c in cases if c['panel'] == 'historical']
    paths = set(ab['pinned_sha256']) | {
        'config/m43ab_attribution.json', 'results_m43ab_attribution/result.json',
        'MILESTONE_43AC_DUAL_EVIDENCE_RESULT.md', 'MILESTONE_43AD_GEOMETRY_PLAN.md',
        'src/seti_repeater/attribution_m43ad.py', 'scripts/m43ad_geometry.py',
        'scripts/m43ad_freeze_config.py', 'tests/test_m43ad_attribution.py',
        'scripts/m43ad_audit.py', 'scripts/m43ac_dual_evidence.py', 'scripts/m43ad_runtime_preflight.py'}
    paths.update(inventory[n]['file'] for n in names)
    cfg = dict(milestone='M43AD', source_commit='450b7e9f0233b9715f482157b9bd864929769a6e',
        python_version=platform.python_version(), numpy_version=np.__version__,
        dependencies={n:importlib.metadata.version(n) for n in ('numpy','astropy','h5py','hdf5plugin')},
        cases=cases, historical_sources={n:inventory[n] for n in names},
        historical_inputs=37, prospective_new_inputs=112,
        policies=ab['policies']+list(POLICIES), parent_template_indices=ab['parent_template_indices'],
        bridge=ab['bridge'], grid_sha256=ab['grid_sha256'], maximum_records=ab['maximum_records'],
        new_null_rows=0, prior_null_rows_to_exclude=1792,
        pinned_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)})
    (ROOT/'config/m43ad_geometry.json').write_text(json.dumps(cfg,separators=(',',':'))+'\n')
    print(json.dumps(dict(historical=37,fresh=112,baseline=1,endpoints=1500,pinned_files=len(paths),
                         python=cfg['python_version'],dependencies=cfg['dependencies'])))


if __name__ == '__main__': main()
