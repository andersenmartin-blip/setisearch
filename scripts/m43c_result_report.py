#!/usr/bin/env python3
"""Verify and summarize the sealed M43C geometric diagnosis."""
import csv
import json
import hashlib
from m43b_active_support import ROOT,seal


def main():
    out=ROOT/'results_m43c_coverage_cause';r=json.loads((out/'diagnostic.json').read_text())
    assert r['result_sha256']==seal({k:v for k,v in r.items() if k!='result_sha256'})
    path=ROOT/'config/m43c_coverage_cause.json';cfg=json.loads(path.read_text())
    assert r['config_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    for p,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    prior=json.loads((ROOT/'results_m43b_active_support/geometry.json').read_text())
    assert prior['result_sha256']==r['parent_result_sha256']
    for ordinal,(row,old) in enumerate(zip(r['rows'],prior['rows'],strict=True)):
        assert row['truth']==old['truth'] and row['truth']['truth_ordinal']==ordinal
        assert row['config_sha256']==r['config_sha256']
        assert row['checkpoint_sha256']==seal({k:v for k,v in row.items() if k!='checkpoint_sha256'})
        assert row['m43b_plan_exact'] and row['m43b_plan_sha256']==old['active_plan_inventory_sha256']
        assert row['active_candidate_cells']==old['active_candidate_cells']
        assert (row['cause']=='supported')==(old['active_candidate_cells']>0)
        assert sum(row['template_cause_counts'].values())==93
    counts={c:sum(row['cause']==c for row in r['rows']) for c in r['counts']}
    assert counts==r['counts'] and len(r['rows'])==512 and counts['supported']==167
    with (out/'truth_summary.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['truth_ordinal','truth_id','active_epochs','cause','best_template','best_continuous_residual_hz','best_continuous_carrier_hz'])
        for row in r['rows']:
            t=row['truth'];best=row['best_continuous_fit']
            w.writerow([t['truth_ordinal'],t['truth_id'],'+'.join(map(str,t['active_epochs_zero_based'])),row['cause'],row['best_template_index'],best['minimum_continuous_residual_hz'],best['minimax_carrier_hz']])
    lines=['# M43C: cause of the remaining geometric coverage gap','',
        '**Completed: 330 of 345 unsupported truths require better track-shape coverage under the fixed 20 Hz rule.**','',
        'All 512 M43B active-epoch plan inventories and candidate counts reproduce exactly. The 167 supported truths remain supported. The 345 unsupported truths split as follows:','','| Cause | Truths | Fraction of 345 unsupported |','|---|---:|---:|']
    descriptions={'track-shape-incompatible':'No fixed template fits the active track, even with a freely chosen carrier','outside-carrier-range':'A continuous solution exists only outside the current carrier range','carrier-grid-gap':'A continuous solution in range falls between tested carrier cells','numerical-boundary-unresolved':'Unresolved numerical boundary'}
    for c,label in descriptions.items():lines.append(f"| {label} | {counts[c]} | {counts[c]/345:.2%} |")
    lines+=['','The diagnosis uses every active integration, one common template and one carrier throughout. Truths with a possible in-range continuous solution take precedence over outside-range solutions. Any ambiguous template would make an unsupported truth unresolved; no truth received that label.','','## Activity breakdown','','| Active ON epochs (zero-based) | Supported | Track shape | Outside range | Between cells | Unresolved |','|---|---:|---:|---:|---:|---:|']
    for g in r['activity_groups']:
        c=g['causes'];lines.append(f"| {g['active_epochs']} | {c['supported']} | {c['track-shape-incompatible']} | {c['outside-carrier-range']} | {c['carrier-grid-gap']} | {c['numerical-boundary-unresolved']} |")
    lines+=['','Each activity group retains all 128 assigned truths. This is not an equal-truth causal comparison across activity groups.','','## Best continuous fit','','The best residual minimizes the largest absolute track discrepancy over active integrations, allowing a continuous carrier for each of the 93 existing templates. The minimum across those templates is summarized below. It measures geometric mismatch in Hz, not S/N or detection significance.','','| Truth inventory | Minimum | 25th percentile | Median | 75th percentile | Maximum |','|---|---:|---:|---:|---:|---:|']
    for group,q in r['best_continuous_residual_quantiles_hz'].items():lines.append('| '+group+' | '+' | '.join(f"{q[k]:.3f}" for k in ('min','p25','median','p75','max'))+' |')
    lines+=['','The unsupported inventory includes 15 truths with a continuous fit below 20 Hz, explaining why its minimum is below the association tolerance. The other 330 fail because the existing track shapes do not fit, not because the carrier sampling is too coarse.','','## Decision','',
        'A finer carrier grid within the existing range could geometrically address at most the six between-cell cases: support would be bounded by 173/512 (33.7890625%) under this unchanged bank and rule. Even unrestricted continuous carriers could address only 182/512 (35.546875%). These are geometric bounds derived from this inventory, not proposed detector changes or calibrated recoveries.','',
        'The next useful experiment is a separately frozen bank-coverage study at the same 20 Hz tolerance and active-epoch association. Define a family of denser track templates from the existing physical coefficient domain before evaluation, preserve the original bank as baseline, and measure computational cost and held-out geometric coverage. Do not simply add each known injection truth as a template and call that general coverage.','',
        'Any chosen bank requires renewed source/cache coverage checks, score/false-association validation and exhaustive real-data anchors. Changing the number of templates also changes the search trials and can invalidate a transferred threshold calibration. M43B’s prospective anchor suggestions remain unexecuted; their suitability must be rechecked for the selected bank. M41 recovery fractions and all historical results are unchanged.','','## Verification and limitations','',
        'Fourteen M43/M43B/M43C tests passed, including six new cause-classification and minimax checks. The synthetic minimax result is independently checked against a densely sampled objective. This turn does not claim a new full-repository test run. No production detector module changed.','',
        'The historical factor basis and table were reconstructed exactly. New active-epoch plans match every M43B inventory digest and cell count. Numerical diagnostics use longdouble with 63 mantissa bits and a predeclared 0.001 Hz ambiguity guard; this guard never changes the 20 Hz acceptance rule. Pairwise minimax bounds and directly evaluated residuals agree within that guard. The continuous calculation is a numerical diagnosis, not a formal real-arithmetic proof.','',
        'Public freeze `b8a9cad2f9f70a8392bcc1fdb9e8ca25d6d554b6`, tree `225a2efcf231c5e8b9b98c37327bac74789aa611`, was verified before execution. This is a retrospective metadata diagnosis; no new spectra, masks, injected data or scores were read or evaluated. No sensitivity, occurrence-rate or technosignature claim follows.','',
        f"Result identity: `{r['result_sha256']}`.",'',
        'diagnostic.json retains all 512 sealed per-truth checkpoints, cause counts over all 93 templates, the best continuous fit and a hash of the complete template diagnostic inventory. The inventory can be regenerated from frozen metadata and code. truth_summary.csv provides a compact review table. Local restart copies are excluded from Git because the combined diagnostic already retains their complete contents.','','```bash','PYTHONPATH=src:scripts python scripts/m43c_coverage_cause.py','PYTHONPATH=src:scripts python scripts/m43c_result_report.py',"PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -v",'```','']
    (ROOT/'MILESTONE_43C_COVERAGE_CAUSE_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps({'counts':counts,'result_sha256':r['result_sha256']},indent=2))


if __name__=='__main__':main()
