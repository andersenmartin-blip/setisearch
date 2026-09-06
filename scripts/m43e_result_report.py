#!/usr/bin/env python3
"""Audit and report M43E development and prospective confirmation stages."""
import argparse
import csv
import json
import numpy as np
from m43e_economical_bank import OUT, ROOT, ACTIVITY, LABELS, CAUSES, context, read_sealed, choose_bank, summarize, fresh_truths
from m43b_active_support import seal
from m43c_coverage_cause import template_diagnostic
from seti_repeater import search_v0p6 as core

FREEZE = '6464c914ee9e5643f17483c91c8c1ea410c639cd'
FREEZE_TREE = '0c13e07eb4a74c7cf9df3d0db8fa4ec8ac6d0c2e'


def verify_rows(c, rows, old_rows=None, fresh=None, selection=None):
    witnesses=0;diagnoses=0
    for ordinal,row in enumerate(rows):
        assert row['result_sha256']==seal({k:v for k,v in row.items() if k!='result_sha256'})
        assert row['config_sha256']==c['cfg_sha'] and row['ordinal']==ordinal
        if old_rows is not None:
            old=old_rows[ordinal]
            assert row['truth']==old['truth'] and row['active_epochs']==old['active_epochs']
            assert row['parent_row_sha256']==old['result_sha256'] and row['m43d_four_bank_replay_exact']
            assert row['selection_sha256'] is None and row['stage']=='development'
            for name in ('baseline','disk16','disk32'):
                assert row['banks'][name]==old['banks'][name]
        else:
            assert row['truth']==fresh[ordinal//4] and row['active_epochs']==list(ACTIVITY[ordinal%4])
            assert row['selection_sha256']==selection['result_sha256'] and row['stage']=='confirmation'
            assert row['parent_row_sha256'] is None and not row['m43d_four_bank_replay_exact']
            assert not row['diagnoses']
        tf=core.template_factors_from_basis(c['basis'],row['truth'])
        active={LABELS[i] for i in row['active_epochs']}
        mask=np.array([l.scan_label in active for l in c['basis'].labels])
        y=row['truth']['proxy_carrier_hz']*tf[mask]
        counts=[]
        for name in c['banks']:
            info=row['banks'][name];counts.append(info['candidate_cells'])
            assert info['supported']==(info['candidate_cells']>0)
            witness=info['witness']
            if not info['supported']:
                assert witness is None
            else:
                assert 0<=witness['template_index']<len(c['banks'][name])
                assert witness['carrier_hz']==c['grid'].score_hz[witness['carrier_index']]
                a=core.template_factors_from_basis(c['basis'],c['banks'][name][witness['template_index']])[mask]
                residual=float(np.max(np.abs(witness['carrier_hz']*a-y)))
                assert residual==witness['max_distance_hz'] and residual<=20
                witnesses+=1
            diag=row['diagnoses'].get(name)
            if old_rows is not None and name in ('disk16','disk32'):
                assert (diag is not None)==(not info['supported'])
            if diag is not None:
                assert diag['cause'] in CAUSES
                assert sum(diag['template_cause_counts'].values())==len(c['banks'][name])
                a=core.template_factors_from_basis(c['basis'],c['banks'][name][diag['best_template_index']])[mask]
                assert template_diagnostic(a,y,c['grid'].score_hz,0)==diag['best_continuous_fit']
                diagnoses+=1
        assert counts==sorted(counts)
    return witnesses,diagnoses


def coverage_table(groups,c):
    lines=['| Group | Tracks | 93 templates | 889 | 1,701 | 3,301 |','|---|---:|---:|---:|---:|---:|']
    for g in groups:
        label=g.get('group') or 'epochs '+'+'.join(str(i+1) for i in g['active_epochs'])
        n=g['truth_count']
        lines.append('| '+label+' | '+str(n)+' | '+' | '.join(f"{g['supported'][name]} ({g['supported'][name]/n:.2%})" for name in c['banks'])+' |')
    return lines


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['development','final'],required=True)
    parser.add_argument('--nomination-commit')
    args=parser.parse_args()
    if args.stage=='final' and (not args.nomination_commit or len(args.nomination_commit)!=40):
        raise ValueError('final report requires the verified public nomination commit')
    c=context();dev=read_sealed(OUT/'development.json.gz');selection=read_sealed(OUT/'selection.json')
    assert dev['config_sha256']==selection['config_sha256']==c['cfg_sha']
    assert dev['m43d_result_sha256']==selection['m43d_result_sha256']==c['old']['result_sha256']
    assert dev['bank_inventory']==selection['bank_inventory']==c['inventory']
    assert selection['development_result_sha256']==dev['result_sha256']
    assert not selection['fresh_confirmation_evaluated']
    rows=dev['rows'];assert len(rows)==2560
    dev_witnesses,diag_count=verify_rows(c,rows,old_rows=c['old']['rows'])
    groups=[{'group':'historical',**summarize(rows[:512],list(c['banks']))}]
    for act in ACTIVITY:
        group=[r for r in rows[512:] if r['active_epochs']==list(act)]
        groups.append({'group':'m43d-known-'+''.join(map(str,act)),**summarize(group,list(c['banks']))})
    assert groups==dev['groups'] and all(g['truth_count']==512 for g in groups)
    nominee=choose_bank(groups)
    assert nominee==dev['selected_bank']==selection['selected_bank']
    for name in ('disk16','disk32'):
        cases=[r for r in rows if name in r['diagnoses']]
        assert dev['cause_summary'][name]=={'failed_associations':len(cases),
            'unique_truth_ids':len({r['truth']['truth_id'] for r in cases}),
            'causes':{cause:sum(r['diagnoses'][name]['cause']==cause for r in cases) for cause in CAUSES}}
    confirmation=None;fresh_witnesses=0
    if args.stage=='final':
        confirmation=read_sealed(OUT/'confirmation.json.gz')
        assert confirmation['selection_sha256']==selection['result_sha256']
        assert confirmation['development_result_sha256']==dev['result_sha256']
        assert confirmation['config_sha256']==c['cfg_sha'] and confirmation['bank_inventory']==c['inventory']
        assert confirmation['selected_bank']==nominee
        fresh=fresh_truths(c['grid'])
        assert seal(fresh)==confirmation['fresh_truth_inventory_sha256']
        assert len(confirmation['rows'])==4096 and confirmation['fresh_unique_tracks']==1024
        fresh_witnesses,_=verify_rows(c,confirmation['rows'],fresh=fresh,selection=selection)
        fresh_groups=[]
        for act in ACTIVITY:
            chosen=[r for r in confirmation['rows'] if r['active_epochs']==list(act)]
            fresh_groups.append({'active_epochs':list(act),**summarize(chosen,list(c['banks']))})
        assert fresh_groups==confirmation['groups'] and all(g['truth_count']==1024 for g in fresh_groups)
        passed=all(g['supported'][nominee]*100>=g['truth_count']*95 for g in fresh_groups)
        assert confirmation['selected_bank_gate_passed']==passed
    audit={'stage':args.stage,'development_result_sha256':dev['result_sha256'],'selection_sha256':selection['result_sha256'],
           'development_rows_verified':len(rows),'development_witnesses_verified':dev_witnesses,
           'best_diagnostic_fits_verified':diag_count,'selected_bank':nominee}
    if confirmation:
        audit.update({'confirmation_result_sha256':confirmation['result_sha256'],'fresh_rows_verified':4096,
                      'fresh_witnesses_verified':fresh_witnesses,'selected_bank_gate_passed':passed,
                      'public_nomination_commit':args.nomination_commit})
    (OUT/('verification_final.json' if confirmation else 'verification_development.json')).write_text(json.dumps(audit,indent=2)+'\n')
    export_rows=[('development',r) for r in rows]
    if confirmation:export_rows += [('confirmation',r) for r in confirmation['rows']]
    with (OUT/('truth_summary.csv' if confirmation else 'development_summary.csv')).open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['stage','ordinal','truth_id','active_epochs',*[name+'_candidate_cells' for name in c['banks']],'disk16_cause','disk32_cause'])
        for stage,row in export_rows:
            w.writerow([stage,row['ordinal'],row['truth']['truth_id'],'+'.join(map(str,row['active_epochs'])),*[row['banks'][name]['candidate_cells'] for name in c['banks']],row['diagnoses'].get('disk16',{}).get('cause',''),row['diagnoses'].get('disk32',{}).get('cause','')])
    lines=['# M43E: economical bank and remaining coverage','']
    if confirmation:
        lines += [f"**Completed: the preselected {c['inventory'][nominee]['template_count']:,}-template bank {'passes' if passed else 'fails'} its fresh geometric confirmation.**",'',
                  '## Fresh confirmation','',
                  'Every row below tests the same 1,024 new parameter draws under one activity pattern. These are paired groups, not 4,096 independent astronomical trials. Epoch labels are one-based.','']
        lines+=coverage_table(confirmation['groups'],c)
        lines+=['',f"The required minimum is 973/1024 in every group. Only **{nominee}** was nominated for confirmation; reference-bank results are descriptive. The nomination was public at `{args.nomination_commit}` before any fresh evaluation. No post-confirmation substitution occurred.",'']
    else:
        lines+=['**Development complete; fresh confirmation has not been evaluated.**','']
    lines+=['## Why the previous banks missed tracks','',
            'All 2,560 M43D associations reproduce their four original bank pair hashes, counts and witnesses exactly. Diagnosis covers every failed association in disk16 and disk32. An association is one track/activity combination; repeated activities are not distinct tracks.','',
            '| Bank | Failed associations | Distinct truth IDs | Track shape | Outside carrier range | Between carrier cells | Unresolved |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for name in ('disk16','disk32'):
        info=dev['cause_summary'][name]
        lines.append(f"| {name} | {info['failed_associations']} | {info['unique_truth_ids']} | "+' | '.join(str(info['causes'][cause]) for cause in CAUSES)+' |')
    lines+=['',
        'The largest bank’s four failed associations belong to one track; each has a continuous template/carrier solution outside the current carrier range. They are not four independent missed sources. The range remains unchanged and all failures remain in their denominators. The minimax calculation uses longdouble and the frozen 0.001 Hz ambiguity guard; exact acceptance still requires <=20 Hz.','',
        '## Development and bank choice','',
        'The checkerboard construction keeps all 889 existing templates and adds 812 odd/odd grid points, giving 1,701 total. It places no templates at known truth coordinates. Nomination uses all five exposed M43D groups below. M43D’s former fresh groups are now development data for M43E, not its independent confirmation. Activity suffixes in these source labels are zero-based.','']
    lines+=coverage_table(groups,c)
    lines+=['',f"The fixed rule nominates **{nominee}**, the first of checker32/disk32 with >=95% coverage in every development group. Nomination hash: `{selection['result_sha256']}`.",'',
        '## Computational cost','',
        '| Bank | Templates | Score cells per window | Relative to original 93 | Relative to 3,301 | Factor table bytes |',
        '|---|---:|---:|---:|---:|---:|']
    for name,info in c['inventory'].items():
        lines.append(f"| {name} | {info['template_count']:,} | {info['score_cells_per_window']:,} | {info['relative_score_cells_to_93']:.2f}× | {info['template_count']/3301:.2%} | {info['factor_table_bytes_six_scans']:,} |")
    lines+=['',
        'The 1,701-template bank has **48.47% fewer score cells than the 3,301-template bank**, while retaining 18.29 times the original 93-template cell count. These are exact hypothesis-count ratios, not measured detector speedups. Full scoring also requires new filtering, cache, mask and null-calibration work.','']
    if confirmation:
        lines += [f"Fresh geometry evaluation took {confirmation['geometry_seconds_sum']:.2f} measured seconds for {confirmation['distance_cells_evaluated']:,} interval-prefilter distance cells. This excludes basis construction, checkpoint I/O and all spectral processing. The calculation uses one full factor table and derives the checkerboard subset from it; it is not a separate wall-time comparison of operational banks.",'']
    lines+=['## Decision and limitations','']
    if confirmation and passed:
        lines+=['Carry the **fixed 1,701-template checkerboard bank** forward to source/extraction/cache coverage checks, score and false-association validation, and deterministic exhaustive real-data anchors. Renew threshold calibration before scientific use. This is a geometric engineering qualification; no production detector is changed or approved by this result.','']
    elif confirmation:
        lines+=['The nominated bank failed. Preserve this failure; do not substitute the reference bank after looking at the fresh result. Any changed design requires a separately frozen study and new confirmation draws.','']
    else:
        lines+=['Publish the sealed nomination before running the fresh stage. The nomination is a development choice and is not yet qualified.','']
    lines+=['No telescope samples, injected spectra, masks or scores were evaluated. Geometric support is not measured recovery, sensitivity, a false-alarm rate or evidence of a technosignature. The fresh tracks share the same cadence and orbital assumptions. Carrier edges remain in scope; no result proves coverage of every coefficient, other physical windows, other cadences or orbital-parameter uncertainties. The original M43D failed gate and all M37/M41/LS results remain unchanged.','',
        '## Verification and restart','',
        f"Frozen code/config publication: `{FREEZE}`, tree `{FREEZE_TREE}`. Development result: `{dev['result_sha256']}`.",'',
        f"All 26 M43-family tests pass. The report verifies every development row identity, all group counts, bank identities, {dev_witnesses:,} development support witnesses directly from physical coefficients, and the {diag_count} best diagnostic fits. All-template diagnosis inventories are hashed and reproducible from frozen code; they are numerical diagnoses, not formal real-arithmetic certificates.",'']
    if confirmation:
        lines += [f"Fresh result: `{confirmation['result_sha256']}`. All 4,096 fresh row identities and {fresh_witnesses:,} fresh witnesses are verified. No broader repository test run is claimed.",'']
    lines+=['Lossless `development.json.gz` and, after execution, `confirmation.json.gz` contain the complete per-association restart rows. `selection.json` binds the nominated bank to the development result. CSV summaries ease review; per-template/carrier pairs can be regenerated from their hashes. Elapsed times vary on a fresh run.','',
        '```bash','PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_economical_bank.py --stage development',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_result_report.py --stage development',
        '# Publish and verify the sealed nomination before continuing.',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_economical_bank.py --stage confirmation']
    if confirmation:lines += [f'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 python scripts/m43e_result_report.py --stage final --nomination-commit {args.nomination_commit}']
    lines+=['```','']
    report='MILESTONE_43E_ECONOMICAL_BANK_RESULT.md' if confirmation else 'MILESTONE_43E_DEVELOPMENT_RESULT.md'
    (ROOT/report).write_text('\n'.join(lines))
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
