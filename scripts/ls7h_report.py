#!/usr/bin/env python3
"""Render the audited, fixed LS7H comparisons without choosing a new cut."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7h_morphology')
    args = parser.parse_args()
    out = args.output
    s = json.loads((out/'summary.json').read_text())
    audit = json.loads((out/'AUDIT.json').read_text())
    assert s['status'] == 'COMPLETED' and audit['passed']
    rows = [json.loads(x) for x in gzip.decompress((ROOT/'results_ls7g_transfer/trials.jsonl.gz').read_bytes()).splitlines()]
    features = [json.loads(x) for x in gzip.decompress((out/'features.jsonl.gz').read_bytes()).splitlines()]
    index = {r['trial_id']: i for i, r in enumerate(rows)}
    focus = s['focus_cells']
    focused = [index[tid] for cell in focus for tid in cell['accepted_ids']]
    cells = {tuple(c['key']): c for c in s['core_cells']}
    lost = s['lost_stellar_ids']
    nominal = [cells['base', 'stellar', t] for t in [8.5, 12, 20]]
    displaced = [cells['base', 'off_profile', t] for t in [8.5, 12, 20]]
    controls = [c for c in s['core_cells'] if not c['signal']]
    bad_controls = [c for c in controls if not c['rules']['augmented']['pass']]
    bad_signals = [c for c in nominal+displaced if not c['rules']['augmented']['pass']]
    background_reversals = sum(len(c['clean_margin_rejects_ids']) for c in focus)
    remaining_focus = sum(len(c['augmented_accepted_ids']) for c in focus)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'ls7h-morphology', 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.1))
    old_color, new_color = '#087f8c', '#b65e35'
    names = ['2×2\n8.5', 'Cross\n8.5', 'Triangle\n8.5', 'Triangle\n12']
    x = np.arange(4)
    axes[0, 0].bar(x-.18, [len(c['accepted_ids']) for c in focus], .35, color=old_color, label='Frozen LS7G')
    axes[0, 0].bar(x+.18, [len(c['augmented_accepted_ids']) for c in focus], .35, color=new_color, label='Added shapes')
    axes[0, 0].axhline(2, color='#677282', linestyle=':', label='Allowance: 2/40')
    axes[0, 0].set(title='A · Previously failing control cells', xticks=x, xticklabels=names, ylabel='Accepted / 40')
    axes[0, 0].legend(frameon=False, fontsize=9)
    signal_cells = nominal+displaced
    for j, (rule, color) in enumerate([('ls7g', old_color), ('augmented', new_color)]):
        axes[0, 1].bar(np.arange(6)+(j-.5)*.35,
                       [100*c['rules'][rule]['count']/c['trials'] for c in signal_cells], .35, color=color)
    axes[0, 1].hlines([90, 80], [-.45, 2.55], [2.45, 5.45], color='#677282', linestyles=':')
    axes[0, 1].set(title='B · Genuine injected stellar recovery', ylim=(0, 105), ylabel='Recovered (%)',
                   xticks=np.arange(6), xticklabels=['N 8.5', 'N 12', 'N 20', 'D 8.5', 'D 12', 'D 20'])
    axes[0, 1].text(.5, -.19, 'N: nominal (40 each)  ·  D: displaced (160 each)', transform=axes[0, 1].transAxes, ha='center', fontsize=9)
    colors = ['#226f9b', '#af6430', '#8658a5', '#49936e']
    for j, cell in enumerate(focus):
        ids = [index[tid] for tid in cell['accepted_ids']]
        axes[1, 0].scatter([rows[i]['methods']['covariance_sparse']['margins']['broad'] for i in ids],
                           [features[i]['clean']['margin_broad'] for i in ids],
                           color=colors[j], label=names[j].replace('\n', ' / '), alpha=.8, s=35)
    axes[1, 0].axhline(-1, color='#677282', linestyle=':'); axes[1, 0].axvline(-1, color='#677282', linestyle=':')
    axes[1, 0].set(title='C · Background removal at the same window', xlabel='Observed LS7G nuisance − star objective',
                   ylabel='Background-removed nuisance − star objective')
    axes[1, 0].legend(frameon=False, fontsize=8, loc='best')
    old_by_anchor = Counter(rows[i]['anchor'] for i in focused)
    remain_by_anchor = Counter(rows[index[tid]]['anchor'] for c in focus for tid in c['augmented_accepted_ids'])
    axes[1, 1].bar(np.arange(10)-.18, [old_by_anchor[a] for a in range(10)], .35, color=old_color)
    axes[1, 1].bar(np.arange(10)+.18, [remain_by_anchor[a] for a in range(10)], .35, color=new_color)
    axes[1, 1].set(title='D · Shared backgrounds behind the four cells', xticks=np.arange(10),
                   xticklabels=[f'{a:02d}' for a in range(10)], xlabel='Background anchor index', ylabel='Accepted controls / 16 per background')
    for ax in axes.flat:
        ax.grid(axis='y', alpha=.13)
    fig.suptitle('LS7H · What lets weak instrumental shapes pass?', x=.065, ha='left', fontsize=17, weight='bold')
    fig.text(.065, .925, f'One fixed bank extension: {s["added_templates"]} placements. Margin −1 and all LS7G signal fits stay fixed.', fontsize=11, color='#465365')
    fig.text(.065, .025, 'Closed-data diagnosis: 3,540 digital trials on ten reused sector-29 backgrounds; no independent false-alarm estimate.\n'
             'Panel C uses injection truth and is not an available veto for native events. No detector or candidate is adopted.', fontsize=9, color='#465365')
    fig.subplots_adjust(top=.855, bottom=.115, left=.065, right=.98, hspace=.46, wspace=.26)
    fig.savefig(out/'morphology_diagnosis.svg', metadata={'Date': None})
    fig.savefig(out/'morphology_diagnosis.png', dpi=150)
    plt.close(fig)
    svg = out/'morphology_diagnosis.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    state = 'PASSES ONLY ON THESE CLOSED DATA' if s['rules']['augmented']['pass'] else 'FAILS'
    report = ['# LS7H: weak instrumental morphology, native background and signal cost', '',
              f'**The one fixed shape-bank extension {state} the inherited joint descriptive gate. No detector or candidate is adopted.**', '',
              f'All **3,540 saved LS7G trials** are diagnosed at their original selected time windows. '
              f'Adding **{s["added_templates"]}** cross, ring and four-rotation triangle placements leaves '
              f'**{len(bad_controls)}/30** control cells and **{len(bad_signals)}/6** stellar-recovery cells failing. '
              f'It loses **{len(lost)}** previously recovered stellar trial rows across the full ledger. '
              'The source bank, covariance, sparse-pixel penalty, temporal outcomes and margin **−1** remain unchanged. '
              'There is one declared extension and no threshold sweep.', '',
              f'Of the **{len(focused)}** accepted controls in the four failing LS7G cells, '
              f'**{background_reversals}** have a background-removed nuisance margin below −1 when both model banks are refitted. '
              'For these cases, the observed native contribution changes the same-window spatial comparison from rejection to acceptance. '
              'This is a conditional diagnostic using known injection truth; it is not a usable native-event veto or a noise probability. '
              f'The extended bank leaves **{remaining_focus}** accepted controls in these four cells.', '',
              '![Fixed morphology diagnosis](morphology_diagnosis.svg)', '',
              '## Four failing cells: missing templates and background effects', '',
              '| Control / target score | LS7G accepted / 40 | Added shapes accepted / 40 | Accepted LS7G cases rejected by clean margin | LS7G accepted cases using a stellar sparse pixel | Plain ablation accepted / 40 |',
              '|---|---:|---:|---:|---:|---:|']
    for c in focus:
        report.append(f'| {c["key"][1]} / {c["key"][2]:g} | {len(c["accepted_ids"])} | {len(c["augmented_accepted_ids"])} | '
                      f'{len(c["clean_margin_rejects_ids"])} / {len(c["accepted_ids"])} | {len(c["star_sparse_ids"])} / {len(c["accepted_ids"])} | {len(c["plain_accepted_ids"])} |')
    report += ['', 'Each control cell permits at most **2/40** acceptances. The last column reuses LS7G’s already computed '
               'no-sparse method at margin −1; its full signal cost appears below. A 2×2 shape was already represented in '
               'LS7G, so an omitted shape family cannot by itself explain all transfer leakage. Different placements can '
               'have identical aperture projections. The augmented bank includes every in-stamp placement intersecting '
               'the 21-pixel aperture, retaining duplicates and four triangle rotations. The bank was selected as a '
               'development response to LS7G’s known failures, so this is not a fresh validation.', '',
               '## Signal protection and complete control accounting', '',
               '| Signal / target | LS7G | Added shapes | No-sparse ablation | Required |', '|---|---:|---:|---:|---:|']
    for c in signal_cells:
        report.append(f'| {c["key"][1]} / {c["key"][2]:g} | '+' | '.join(f'{c["rules"][rule]["count"]}/{c["trials"]}' for rule in ['ls7g', 'augmented', 'plain_ablation'])+f' | ≥{c["limit"]}/{c["trials"]} |')
    report += ['', 'Each row keeps its full original denominator, including any temporal miss, confounding or strength failure. '
               'All six LS7G signal cells passed before this extension. Counts alone do not erase individual signal losses.', '',
               '| Control kind | Score 8.5: LS7G → added | Score 12: LS7G → added | Score 20: LS7G → added |', '|---|---:|---:|---:|']
    for suite, kind in [('base', 'single_pixel'), ('base', 'block_2x2'), ('base', 'uniform'), ('base', 'pointing'),
                        ('known_extended', 'block3x3'), ('known_extended', 'row1x5'), ('known_extended', 'column5x1'),
                        ('unmodeled_shapes', 'cross3x3'), ('unmodeled_shapes', 'ring3x3'), ('unmodeled_shapes', 'triangle3x3')]:
        report.append(f'| {kind} | '+' | '.join(f'{cells[suite,kind,t]["rules"]["ls7g"]["count"]} → {cells[suite,kind,t]["rules"]["augmented"]["count"]} / {cells[suite,kind,t]["trials"]}' for t in [8.5, 12, 20])+' |')
    report += ['', '| Rule at margin −1 | Joint gate | Failed subrequirements |', '|---|---|---|']
    for rule, value in s['rules'].items():
        report.append(f'| {rule} | {"PASS on closed data" if value["pass"] else "FAIL"} | '+(', '.join(k for k, v in value['gates'].items() if not v) or 'none')+' |')
    report += ['', 'The inherited gate also checks matched strengths, ≥54/60 fixed 10%-flux single-pulse recoveries, '
               'zero base-null acceptances, ≤20% signal confounding and ≤5% acceptance among temporally screened bounded-pointing controls. '
               'All groups, sparse-stress cases and 360 background/cell counts are saved in [summary.json](summary.json).', '',
               '### Every additional stellar loss', '',
               f'**{len(lost)}** rows recovered by LS7G become unrecovered with the added shapes. The acceptance set can only shrink: '
               'the old nuisance models remain available, and only the minimum nuisance objective changes. '
               'All new losses therefore occur at the nuisance-margin step, with temporal, source-score, residual and confounding decisions fixed.', '',
               '| Suite / kind / target score | Lost recovered stellar rows |', '|---|---:|']
    loss_groups = Counter((rows[index[tid]]['suite'], rows[index[tid]]['kind'], rows[index[tid]].get('target_score')) for tid in lost)
    for key, count in sorted(loss_groups.items(), key=str):
        report.append(f'| {key[0]} / {key[1]} / {key[2]} | {count} |')
    if not lost:
        report.append('| All groups | 0 |')
    report += ['', '<details><summary>Complete lost stellar trial IDs</summary>', '', *[f'- `{tid}`' for tid in lost], '', '</details>', '',
               '### Disjoint recovery paths over all stellar rows', '',
               'This table includes fixed-flux, matched nominal/displaced and sparse-stress stellar rows. '
               'The first failing condition is counted in the order temporal, source score, residual, margin, then confounding.', '',
               '| Rule | Temporal | Source score | Residual | Nuisance margin | Confounded | Recovered |', '|---|---:|---:|---:|---:|---:|---:|']
    for rule, counts in s['signal_recovery_paths'].items():
        report.append(f'| {rule} | '+' | '.join(str(counts.get(k, 0)) for k in ['temporal', 'source_score', 'residual', 'nuisance_margin', 'confounded', 'recovered'])+' |')
    report += ['', '## Exact same-window decomposition', '',
               'For every trial the injected cube is reconstructed from its saved spatial pattern, integrated pulse, '
               'amplitude and any residual pixel. Let y be its signed selected-window mean-minus-sideband-median vector, '
               'b the same statistic of the native cube, and s = y − b. All counterfactual fits retain the recorded window, '
               'reference templates and covariance; neither temporal selection nor strength matching is repeated.', '',
               f'The largest difference between s and the event statistic of the injection-only cube is '
               f'**{s["max_clean_pure_difference"]:.6g} e⁻/s per pixel**. This explicitly checks the possible nonlinearity of '
               'the sideband median; the code does not assume that medians add.', '',
               'With the **observed** winning stellar and nuisance designs and active source-amplitude sets fixed, '
               'let D be the difference between their residual precision matrices. The recorded margin is exactly', '',
               '$$m=s^T D s+b^T D b+2b^T D s+(P_n-P_s).$$', '',
               'The three terms separate the injected shape, native background and their interaction; the last term '
               'is the difference in the unchanged sparse-pixel penalties. This is a conditional algebraic attribution '
               'of an already selected winner, not a new fitted classifier. Separately, both banks are genuinely refitted '
               'to s to obtain the clean margins above, allowing a different winner or active amplitude constraint.', '',
               '| Failing cell | Median shape term | Median background term | Median interaction term | Median penalty difference |', '|---|---:|---:|---:|---:|']
    for c in focus:
        ids = [index[tid] for tid in c['accepted_ids']]
        report.append(f'| {c["key"][1]} / {c["key"][2]:g} | '+' | '.join(f'{np.median([features[i]["fixed_winner_margin_components"][k] for i in ids]):.3f}' for k in ['injected_shape', 'native_background', 'interaction', 'penalty_difference'])+' |')
    report += ['', 'These column medians need not sum to a median margin. The identity is checked trial by trial in the ledger.', '',
               '## All accepted controls from the four original failures', '',
               'The paired signal ledger links each of these controls to the five nominal/displaced stellar trials with '
               'the same anchor, phase, pulse duration and target temporal score. These pairs share backgrounds and can '
               'overlap across control families; they are not additional independent samples.', '',
               '| Trial ID | LS7G margin | Clean LS7G margin | Added-shape margin | Added shapes accept? |', '|---|---:|---:|---:|---|']
    for i in focused:
        r, f = rows[i], features[i]
        report.append(f'| `{r["trial_id"]}` | {r["methods"]["covariance_sparse"]["margins"]["broad"]:.4f} | {f["clean"]["margin_broad"]:.4f} | {f["augmented_margin"]:.4f} | {"yes" if f["decisions"]["augmented"]["accepted"] else "no"} |')
    report += ['', '## Verification and limits', '',
               f'- Five known-answer tests check rotations/edge projections, signed partial-window residuals, sideband-median nonadditivity, sparse-design attribution and fixed-cut/confounding semantics.',
               f'- The independent audit reconstructs **{audit["trials_reconstructed"]:,}** component vectors and attributions, checks **{audit["direct_whitened_fits"]:,}** direct whitened fits and **{audit["exhaustive_fit_alternatives"]:,}** fit alternatives.',
               f'- It verifies every new acceptance, disjoint recovery path, stellar loss, control pair, 36 core cells and 360 background/cell counts. Maximum minimum-objective error: **{audit["max_minimum_objective_error"]:.3g}**.',
               '- LS7G’s unchanged temporal selection, covariance construction and original fits retain their prior independent audit, with all inputs and audit evidence checked by hash. They are not rerun as another challenge.',
               f'- Source freeze: `{s["freeze_commit"]}`. Runtime: '+', '.join(f'{k} {v}' for k,v in s['environment'].items())+'.', '',
               'Sector 29 and the four failure cells were already inspected. These 3,540 digital rows reuse ten backgrounds; '
               'the counts are not independent rates or calibrated false-alarm probabilities. Background subtraction here '
               'requires injection truth. Digital signals are added after mission processing without added photon noise. '
               'The optical detector remains unqualified; there is no new observing coverage, physical sensitivity limit, '
               'native candidate search or evidence of an extraterrestrial signal. Earlier LS results and M43 held-out panels are unchanged.', '',
               '## Continuation', '',
               'Use this completed diagnosis to choose the next integrated model study. Any new model requires a separate '
               'freeze and joint signal/control accounting on the already closed sectors before an unseen evaluation. '
               'Do not change the LS7G or LS7H margin, silently remove difficult controls, or treat a truth-dependent '
               'background subtraction as an available detector feature. The maintained next action is in '
               '[PROJECT_STATUS.md](../PROJECT_STATUS.md).', '',
               '- [Protocol](../LS7H_MORPHOLOGY_PROTOCOL.md), [configuration](../config/ls7h_morphology.json), [source checksums](../LS7H_FREEZE.sha256)',
               '- [Complete new trial features](features.jsonl.gz), [added bank](bank.json), [paired signal decisions](paired_signals.json)',
               '- [Summary, groups and all loss IDs](summary.json), [independent audit](AUDIT.json), [output checksums](SHA256SUMS)', '']
    (out/'REPORT.md').write_text('\n'.join(report))
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (out/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))
    print(f'Sealed {len(files)} audited LS7H output files.')


if __name__ == '__main__':
    main()
