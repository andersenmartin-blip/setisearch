#!/usr/bin/env python3
"""Reproduce M42 and audit the legacy multi-axis support contract."""
import hashlib
import json
from pathlib import Path
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.sparse_replay_v0p6 import plan_truth_local_template_scores
from seti_repeater.truth_local_v0p6 import plan_truth_local_template_scores_interval
import m42_m41_support_mask_diagnostic as m42

ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    return [
        ('aligned', [[1.,1.,1.]], 500., [1.,1.,1.], 20.),
        ('incompatible_carriers', [[1.,1.,1.]], 500., [.9,1.1,1.], 20.),
        ('different_templates_by_epoch', [[1.,1.2,1.],[1.2,1.,1.]], 500., [1.,1.,1.], 20.),
        ('inactive_epoch_mismatch', [[1.,1.,1.]], 500., [1.,1.,1.2], 20.),
        ('between_grid_cells', [[1.,1.,1.]], 500.5, [1.,1.,1.], 0.),
        ('inclusive_zero_width', [[1.,1.,1.]], 500., [1.,1.,1.], 0.),
        ('just_below_20', [[1.,1.,1.]], 500., [1.,1.,1.], float(np.nextafter(20., -np.inf))),
    ]


def audit_case(case):
    name, raw_factors, carrier, raw_truth, tolerance = case
    grid = core.make_proxy_carrier_grid(.0005, 1., 128, 64)
    factors = np.array(raw_factors, dtype='<f8', order='C')
    truth = np.array(raw_truth, dtype='<f8', order='C')
    dense = plan_truth_local_template_scores(grid, factors, carrier, truth, tolerance_hz=tolerance)
    bounded = plan_truth_local_template_scores_interval(grid, factors, carrier, truth, tolerance_hz=tolerance)
    if [p.as_record() for p in dense] != [p.as_record() for p in bounded]:
        raise RuntimeError('dense/interval mismatch: '+name)
    # Independent exhaustive Boolean oracle: no interval calculation.
    distance = np.abs(grid.score_hz[None,:,None]*factors[:,None,:]-carrier*truth[None,None,:])
    per_axis = distance <= tolerance
    joint = np.all(per_axis, axis=2)
    rows = []
    for i,p in enumerate(bounded):
        indices = np.flatnonzero(joint[i])
        if not np.array_equal(indices, p.candidate_indices.indices):
            raise RuntimeError('Boolean oracle mismatch: '+name)
        lower = (carrier*truth-tolerance)/factors[i]
        upper = (carrier*truth+tolerance)/factors[i]
        rows.append({'template_index': i,
            'per_integration_candidate_count': per_axis[i].sum(axis=0).tolist(),
            'continuous_lower_hz': float(lower.max()),
            'continuous_upper_hz': float(upper.min()),
            'joint_candidate_indices': indices.tolist(),
            'joint_candidate_hz': grid.score_hz[indices].tolist(),
            'plan_sha256':p.plan_sha256})
    return {'name':name, 'template_factors':raw_factors, 'truth_carrier_hz':carrier,
        'truth_factors':raw_truth, 'tolerance_hz':tolerance,
        'one_integration_per_epoch':True, 'epoch_labels':['ON0','ON1','ON2'],
        'per_epoch_support_some_template_and_carrier':np.any(per_axis,axis=(0,1)).tolist(),
        'one_template_and_carrier_support_all_epochs':bool(joint.any()),
        'candidate_cell_count':int(joint.sum()),
        'first_two_epochs_only_cell_count_demonstration':int(np.all(per_axis[:,:,:2],axis=2).sum()),
        'alternative_rule_adopted':False, 'exact_three_way_equivalence':True,
        'templates':rows}


def run():
    cfg_path = ROOT/'config/m43_support_contract.json'
    cfg = json.loads(cfg_path.read_text())
    for path,digest in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('pinned input changed: '+path)
    previous = m42.build_diagnostic(ROOT, m42.load_json(ROOT/'config/m42_m41_support_mask_diagnostic.json'))
    prior_bytes = (ROOT/'results_m42_m41_support_mask_diagnostic/diagnostic.json').read_bytes()
    if core.canonical_json_bytes(previous) != prior_bytes:
        raise RuntimeError('M42 replay differs from published bytes')
    cases = [audit_case(c) for c in fixtures()]
    result = {'artifact_type':'m43-support-contract-qualification-v1',
        'status':'checkpoint-complete-no-contract-preserving-repair-demonstrated',
        'config_sha256':hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
        'm42_byte_identical':True, 'm41_records_validated':previous['trial_count'],
        'legacy_supported_truths':98, 'legacy_unsupported_truths':414,
        'synthetic_fixture_count':len(cases), 'cases':cases,
        'production_changed':False,'new_spectral_reads':0,'new_injections':0,
        'new_real_data_anchor_replay':False,'full_m43_repair_qualification_complete':False,
        'technosignature_claimed':False}
    result['result_sha256']=hashlib.sha256(core.canonical_json_bytes(result)).hexdigest()
    out=ROOT/'results_m43_support_contract';out.mkdir(exist_ok=True)
    (out/'qualification.json').write_bytes(core.canonical_json_bytes(result))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__':run()
