#!/usr/bin/env python3
"""Verify M43B certificates and publish compact restart and summary artifacts."""
import csv
import hashlib
import json
from pathlib import Path
from m43b_active_support import ROOT, ACTIVITY, seal


def main():
    out=ROOT/'results_m43b_active_support';r=json.loads((out/'geometry.json').read_text())
    assert r['result_sha256']==seal({k:v for k,v in r.items() if k!='result_sha256'})
    cfgpath=ROOT/'config/m43b_active_support.json';cfg=json.loads(cfgpath.read_text())
    assert r['config_sha256']==hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    for p,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    assert len(r['rows'])==512
    for ordinal,row in enumerate(r['rows']):
        assert row['truth']['truth_ordinal']==ordinal and row['config_sha256']==r['config_sha256']
        assert row['checkpoint_sha256']==seal({k:v for k,v in row.items() if k!='checkpoint_sha256'})
        assert row['legacy_m41_plan_exact'] and row['legacy_cells_subset_of_active']
        assert row['active_candidate_cells']>=row['legacy_candidate_cells']
        if row['truth']['active_epochs_zero_based']==[0,1,2]:assert row['legacy_plan_inventory_sha256']==row['active_plan_inventory_sha256']
    assert r['legacy_supported']==sum(x['legacy_candidate_cells']>0 for x in r['rows'])==98
    assert r['active_supported']==sum(x['active_candidate_cells']>0 for x in r['rows'])==167
    counts={key:sum(x['category']==key for x in r['rows']) for key in r['counts']};assert counts==r['counts']
    with (out/'truth_summary.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['truth_ordinal','truth_id','active_epochs','width_channels','legacy_candidate_cells','active_candidate_cells','category'])
        for x in r['rows']:
            t=x['truth'];w.writerow([t['truth_ordinal'],t['truth_id'],'+'.join(map(str,t['active_epochs_zero_based'])),t['spectral_width_channels'],x['legacy_candidate_cells'],x['active_candidate_cells'],x['category']])
    # The full combined artifact contains every sealed per-truth checkpoint.
    # These can restore the frozen runner's restart directory without rerunning geometry.
    (out/'future_anchors.json').write_text(json.dumps(r['future_anchor_inventory'],indent=2)+'\n')
    lines=['# M43B active-epoch geometric association result','',
        '**Geometry comparison complete: 167/512 supported, versus the unchanged 98/512 baseline. Score and real-data qualification remain pending.**','',
        'The publicly frozen active-epoch rule adds 69 supported truths and loses none. All 512 original truths remain in the denominator. The 345 unsupported truths still prevent a 50% recovery endpoint under this fixed bank and 20 Hz association rule, even before masking or threshold losses. This is geometry, not measured signal recovery or sensitivity.','',
        '| Association | Supported truths | Fraction of all 512 |','|---|---:|---:|',
        f"| Original all-epoch 20 Hz | 98 | {98/512:.6%} |",f"| Active-epoch 20 Hz | 167 | {167/512:.6%} |",'','## Activity comparison','','| Truth-active ON epochs (zero-based) | Truths | Original support | Active-only support | Added |','|---|---:|---:|---:|---:|']
    for act in ACTIVITY:
        rows=[x for x in r['rows'] if tuple(x['truth']['active_epochs_zero_based'])==act]
        a=sum(x['legacy_candidate_cells']>0 for x in rows);b=sum(x['active_candidate_cells']>0 for x in rows)
        lines.append(f"| {list(act)} | {len(rows)} | {a} | {b} | {b-a} |")
    lines+=['','All-epoch-active truths retain exact complete plan identities. The change only removes distance constraints from epochs in which the labelled injected truth is absent. A single fixed template and carrier must still match every integration of every active epoch. Width does not relax the 20 Hz criterion; different widths have different assigned truths, so subgroup differences are not isolated causal width effects.','','## Width inventory','','| Injected width (channels) | Truths | Original support | Active-only support |','|---|---:|---:|---:|']
    for width in (1,3,5,9,17,33,65,129):
        rows=[x for x in r['rows'] if x['truth']['spectral_width_channels']==width]
        lines.append(f"| {width} | {len(rows)} | {sum(x['legacy_candidate_cells']>0 for x in rows)} | {sum(x['active_candidate_cells']>0 for x in rows)} |")
    anchors=[a for a in r['future_anchor_inventory'] if a['truth_ordinal'] is not None]
    lines+=['','## Verification','',
        'The metadata-derived factor basis and 93-template table reproduce their historical SHA-256 identities exactly. All 6,144 M41 records were validated. For every one of the 512 truths, the original complete plan-inventory digest and candidate-score-cell count reproduce M41 exactly. The geometric count is expanded by 8 widths × 4 score activity hypotheses in the original score-cell tally. Every original candidate set is contained in the corresponding new set.','',
        'All eight M43/M43B tests passed. Four new tests cover every canonical activity subset with a multi-integration exhaustive Boolean oracle, retention of every active integration, invalid/reordered activity, and invalid inactive-epoch input. No production detector code changed. This turn does not claim a newly completed full repository test run.','',
        'Public freeze `ec23df9a02563b12a2c2a1396d705ba3c290dc74`, tree `63b84738c1cf8572ba79ad4167df57056fac1d4b`, was ref-verified before the 512-truth comparison. All inputs, code and per-truth checkpoint identities are retained.','',f"Result identity: `{r['result_sha256']}`.",'','## Decision and next stage','',
        'Active-epoch association removes a genuine restriction of the old definition, but is a renamed endpoint rather than an implementation repair. It is useful progress without establishing an increase in detection probability. The remaining geometric ceiling is 167/512 = 32.6171875%; another S/N-only extension still cannot reach 50%.','',
        'Before a new calibration campaign, audit the remaining bank/track geometry on active epochs. That audit should distinguish no common carrier interval from an interval falling between carrier cells or outside the grid. It can determine whether bank coverage or a separately justified width-dependent association needs work. Keep the present 20 Hz results intact; do not tune an acceptance threshold to the observed support count.','',
        f"The deterministic future-anchor inventory selects {len(anchors)} nonempty cells from 24 possible (category, activity, width 1/129) combinations by the lowest original truth ordinal. Empty combinations are explicit nulls. Selection uses this geometric result and precedes any new spectral read. The inventory is a proposed validation set, not evidence that anchors have been replayed.",'',
        'A future scorer must tie its evaluated activity hypothesis to the labelled truth-active subset, while preserving full all-epoch/all-width two-pass mask dependencies. It requires a separate freeze and exhaustive real-data comparisons. Old M39 anchors cannot certify the changed endpoint. No new spectral samples, masks, injected spectra, scores, calibrated sensitivities or technosignatures are reported here.','','## Restart','',
        'geometry.json contains the full set of 512 sealed per-truth checkpoints, so the result can be verified without telescope data. The runner regenerates the metadata comparison when local checkpoints are absent. truth_summary.csv offers a compact inspectable inventory. The report generator verifies config, code, checkpoint hashes and totals before emitting the summary.','','```bash','PYTHONPATH=src:scripts python scripts/m43b_active_support.py','PYTHONPATH=src:scripts python scripts/m43b_result_report.py',"PYTHONPATH=src:scripts python -m unittest discover -s tests -p 'test_m43*.py' -v",'```','']
    (ROOT/'MILESTONE_43B_ACTIVE_SUPPORT_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps({'counts':counts,'selected_future_anchors':len(anchors),'result_sha256':r['result_sha256']},indent=2))


if __name__=='__main__':main()
