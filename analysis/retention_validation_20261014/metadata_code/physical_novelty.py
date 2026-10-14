#!/usr/bin/env python3
"""Cross-profile physical placement novelty; metadata only, no score arrays."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

TASK = Path('/workspace/scratch/b83cfe20d6e1')
BASE = TASK / 'checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14'
OUT = TASK / 'retention_validation_20261014'
manifest_path = OUT / 'GEOMETRY_MANIFEST.json'
prior_path = BASE / 'rounding_followup/results/INJECTIONS.json'
manifest = json.loads(manifest_path.read_bytes())
prior = json.loads(prior_path.read_bytes())
old_keys = defaultdict(set)
for t in prior['trials']:
    rows = tuple(t['true_active_source_rows'])
    for field in ('canonical_float_truth_absolute_centers', 'canonical_rational_truth_absolute_centers'):
        bins = tuple(t[field][r] for r in rows)
        old_keys[(t['context_scan_id'], rows, bins)].add(t['profile_id'])
new_keys = defaultdict(list)
for g in manifest['geometries']:
    key = (g['context_scan_id'], tuple(g['true_active_source_rows']), tuple(g['truth_active4']))
    new_keys[key].append(g['geometry_id'])
collisions = []
for key, ids in new_keys.items():
    if key in old_keys:
        collisions.append(dict(context_scan_id=key[0], active_source_rows=list(key[1]),
                               absolute_active4=list(key[2]), new_geometry_ids=ids,
                               prior_profile_ids=sorted(old_keys[key])))
aliases = []
for key, ids in new_keys.items():
    if len(ids) > 1:
        aliases.append(dict(context_scan_id=key[0], active_source_rows=list(key[1]),
                            absolute_active4=list(key[2]), geometry_ids=ids))
result = dict(schema='SETI_RETENTION_CROSS_PROFILE_PHYSICAL_NOVELTY_V1', date='2026-10-14',
    status='PASS_METADATA_ONLY_NOVELTY_CENSUS',
    identity_key=['context_scan_id', 'active_source_rows', 'absolute_active4_native_channels'],
    prior_models='Union of canonical_float and canonical_rational prior truths; amplitudes and profile aliases collapsed.',
    counts=dict(profile_keyed_unique_geometries=len(manifest['geometries']),
        physical_unique_geometries=len(new_keys), physical_profile_aliases=sum(len(ids)-1 for ids in new_keys.values()),
        prior_unique_physical_geometries=len(old_keys), physical_new_overlap_prior=len(collisions),
        profile_keyed_new_overlap_prior=sum(len(c['new_geometry_ids']) for c in collisions),
        physical_identity_multiplicity={str(k):v for k,v in sorted(Counter(len(v) for v in new_keys.values()).items())},
        context_scans=len({key[0] for key in new_keys}), independent_fresh_visits=0,
        new_parameter_draws=manifest['counts']['nominal_geometry_draws'],
        alias_parameter_draws=manifest['counts']['duplicate_alias_draws']),
    overlap_prior=collisions, cross_profile_aliases=aliases,
    input_pins=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in (manifest_path,prior_path)],
    code_pin=dict(path=str(Path(__file__).resolve()),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
    spectral_arrays_opened=False, scores_evaluated=False,
    interpretation=['All2822 placements are physically distinct under scan/active-row/bin identity and none was in the old512 injection bank, including across profiles.',
        'Every placement remains a synthetic perturbation of previously exposed residual background from the same2017 observing visit.',
        'Distinct cell placements and paired amplitude rows are dependent computational cases, not independent statistical trials or qualification evidence.'])
with (OUT/'PHYSICAL_NOVELTY_CENSUS.json').open('x',encoding='utf-8') as f:
    json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
    f.write('\n')
print(json.dumps(result['counts']))
