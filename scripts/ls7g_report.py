#!/usr/bin/env python3
"""Render and seal audited LS7G results; never select a new rule or threshold."""
import argparse
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
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7g_transfer')
    parser.add_argument('--update-status', action='store_true')
    args = parser.parse_args()
    out = args.output
    s = json.loads((out/'summary.json').read_text())
    audit = json.loads((out/'AUDIT.json').read_text())
    preflight = json.loads((out/'preflight.json').read_text())
    assert audit['passed'] and s['status'] == 'COMPLETED'
    primary = s['primary_rule']
    passed = s['rules'][primary]['pass']
    state = 'PASS on these previously examined data' if passed else 'FAIL'
    failed = [name for name, value in s['rules'][primary]['gates'].items() if not value]
    cellmap = {tuple(c['key']): c for c in s['core_cells']}
    def count(suite, kind, score, rule=primary):
        return cellmap[suite, kind, score]['rules'][rule]['count']
    scores = [8.5, 12, 20]
    nominal = [count('base', 'stellar', t) for t in scores]
    displaced = [count('base', 'off_profile', t) for t in scores]
    controls = [c for c in s['core_cells'] if not c['signal']]
    bad_controls = [c for c in controls if not c['rules'][primary]['pass']]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'ls7g-transfer', 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 4.9))
    colors = ['#087f8c', '#a06d21', '#66758a']
    for j, threshold in enumerate([-1, 0, 9]):
        rule = f'covariance_sparse/broad/{threshold}'
        x = np.arange(3)+(j-1)*.25
        axes[0].bar(x, [100*count('base', 'stellar', t, rule)/40 for t in scores], .24, color=colors[j], label=f'Margin {threshold}')
        axes[1].bar(x, [100*count('base', 'off_profile', t, rule)/160 for t in scores], .24, color=colors[j])
        axes[2].bar(x, [max(100*c['rules'][rule]['count']/c['trials'] for c in controls if c['key'][2] == t) for t in scores], .24, color=colors[j])
    for ax, title, limit, ylabel in zip(axes, ['Nominal stellar pulses', 'Displaced stellar pulses', 'Worst instrumental control'], [90, 80, 5], ['Recovered (%)', 'Recovered (%)', 'Accepted (%)']):
        ax.axhline(limit, ls=':', lw=1.5, color='#b65235')
        ax.set(title=title, ylim=(0, 105), ylabel=ylabel, xticks=np.arange(3), xticklabels=['8.5', '12', '20'], xlabel='Target temporal score')
        ax.grid(axis='y', alpha=.14)
    fig.suptitle('LS7G · Frozen transfer to TESS sector 29', x=.06, ha='left', fontsize=16, weight='bold')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper left', bbox_to_anchor=(.05, .91), ncol=3, frameon=False)
    fig.text(.06, .045, '3,540 digital trials on ten shared, previously examined backgrounds. Covariance + sparse pixel; expanded bank.\n'
             'Margin −1 is fixed from sector-32 development. Acceptance does not establish stellar or artificial origin.', fontsize=9, color='#465365')
    fig.subplots_adjust(top=.75, bottom=.23, left=.06, right=.98, wspace=.30)
    fig.savefig(out/'transfer_comparison.svg', metadata={'Date': None})
    fig.savefig(out/'transfer_comparison.png', dpi=155)
    plt.close(fig)
    svg = out/'transfer_comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    text = ['# LS7G: fixed transfer of the expanded TESS model to sector 29', '',
            f'**Primary joint development result: {state}. No detector is adopted and no astronomical candidate is promoted.**', '',
            'All **3,540** fixed digital trials completed on the ten previously examined L 98-59 sector-29 backgrounds. '
            'The primary rule is covariance plus an optional sparse pixel, an expanded nuisance bank and a margin of **−1**, '
            'chosen from sector-32 LS7F development before this transfer. Margins 0 and 9, the original bank and the no-sparse ablation are retained. '
            'There is no sector-29 retuning, independent qualification, native candidate search or added observing coverage.', '',
            '## Nominal and displaced recovery', '',
            '| Target score | Nominal, margin −1 | Nominal, margin 0 | Nominal, margin 9 | Displaced, margin −1 | Displaced, margin 0 | Displaced, margin 9 |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for score in scores:
        n = [count('base', 'stellar', score, f'covariance_sparse/broad/{t}') for t in [-1, 0, 9]]
        d = [count('base', 'off_profile', score, f'covariance_sparse/broad/{t}') for t in [-1, 0, 9]]
        text.append(f'| {score:g} | '+' | '.join([f'{v}/40' for v in n]+[f'{v}/160' for v in d])+' |')
    text += ['', 'Each strength requires at least **36/40** nominal and **128/160** displaced recoveries. '
             'Temporally missed, unmatched and baseline-confounded cases stay in their denominators.', '',
             '![Fixed transfer comparison](transfer_comparison.svg)', '',
             '## Original, modeled and omitted control shapes', '',
             'Primary-rule counts follow; each individual kind/strength cell permits at most 5% acceptance. '
             'The 3×3, 1×5 and 5×1 patterns are modeled. The cross, ring and triangle are omitted as named fit shapes; '
             'some aperture projections can nevertheless resemble or coincide with modeled shapes.', '',
             '| Suite / kind | Score 8.5 | Score 12 | Score 20 |', '|---|---:|---:|---:|']
    kinds = [('base', 'single_pixel'), ('base', 'block_2x2'), ('base', 'uniform'), ('base', 'pointing'),
             ('known_extended', 'block3x3'), ('known_extended', 'row1x5'), ('known_extended', 'column5x1'),
             ('unmodeled_shapes', 'cross3x3'), ('unmodeled_shapes', 'ring3x3'), ('unmodeled_shapes', 'triangle3x3')]
    for suite, kind in kinds:
        text.append(f'| {suite} / {kind} | '+' | '.join(f'{count(suite, kind, t)}/{cellmap[suite, kind, t]["trials"]}' for t in scores)+' |')
    text += ['', f'**{len(bad_controls)}/30** primary control cells exceed their declared allowance. '
             'Control counts reuse ten backgrounds and are not false-alarm probabilities. Every tuning success/failure and screening count is retained in the ledger.', '',
             '## All fixed rule outcomes', '', '| Method / bank / margin | Joint descriptive gate |', '|---|---|']
    for rule, result in s['rules'].items():
        text.append(f'| {rule} | {"PASS on closed data" if result["pass"] else "FAIL"} |')
    text += ['', 'The joint gate includes all 36 core cells, matched strengths, fixed 10% single-pulse recovery, '
             'base nulls, confounding and acceptance of screened physically bounded pointing. '
             'The primary failed subrequirements are: **'+(', '.join(failed) if failed else 'none on these closed data')+'**.', '',
             '## Residual stress, pointing and ambiguity', '',
             '| Parent target score, inside-pixel stress | Cross temporal threshold / 80 | Primary recovered / 80 |', '|---|---:|---:|']
    for score in scores:
        gs = [g for g in s['groups'] if g['key'][:3] == ['sparse_stress', 'stellar', score] and g['key'][3] == 'inside']
        text.append(f'| {score:g} | {sum(g["screen_detected"] for g in gs)}/80 | {sum(g["rules"][primary]["recovered"] for g in gs)}/80 |')
    physical = next(g for g in s['groups'] if g['key'] == ['bounded_pointing', 'pointing', None])
    losses = [x for x in audit['losses_relative_to_original_margin_9'] if x['method'] == 'covariance_sparse']
    ambiguous = [x for x in audit['nuisance_preferred_acceptances_at_minus_1'] if x['method'] == 'covariance_sparse']
    signal_ambiguous = sum(x['kind'] in ['stellar', 'off_profile'] for x in ambiguous)
    text += ['', f'Of 320 physically bounded pointing trials, **{physical["screen_detected"]}** cross the temporal threshold; '
             f'**{physical["rules"][primary]["accepted"]}** are accepted by the primary rule. Subthreshold cases do not demonstrate spatial rejection.', '',
             f'The primary rule loses **{len(losses)}** stellar trial rows recovered by the same method with the original bank and margin 9. '
             'All IDs are retained; aggregate recovery gains do not erase individual losses.', '',
             f'**{len(ambiguous)}** accepted primary-rule rows have a better nuisance than stellar fit: '
             f'**{signal_ambiguous}** injected stellar/displaced rows and **{len(ambiguous)-signal_ambiguous}** non-signal rows. '
             'They are explicitly listed with their margins. A negative-margin acceptance does not identify a stellar, laser or artificial source.', '',
             '## Provenance, covariance and verification', '',
             f'The exact original MAST product hashes and LS7B eligibility reproduce. The **21-pixel** sector-29 aperture and '
             f'**{preflight["searchable_cadence_days"]:.6f}** already searched cadence-days are used. '
             'Run noise reproduces the archived LS7B values. Each of 30 width/background covariance folds uses 45 event-statistic '
             'vectors from the other nine backgrounds, with fixed 5% diagonal shrinkage. The full model contexts, 150 training vectors '
             'and original restored background extracts are published. No sector-32 covariance or mask is imported.', '',
             f'- Five analytical tests and the complete **3,540-case artificial smoke fixture** pass; the latter is explicitly not telescope evidence.',
             f'- The independent auditor reconstructs all **{audit["trials_reconstructed"]:,}** trial event vectors and temporal decisions, all injection patterns and all 30 covariance folds.',
             f'- **{audit["direct_whitened_fits"]:,}** direct whitened fits and **{audit["exhaustive_fit_alternatives"]:,}** independent alternative fits pass.',
             f'- Maximum event-vector error: {audit["max_event_vector_absolute_error"]:.3g}; temporal-score error: {audit["max_temporal_score_absolute_error"]:.3g}; direct-fit error: {audit["max_direct_fit_absolute_error"]:.3g}.',
             f'- Every group, fixed-rule gate and **{audit["per_background_counts_checked"]}** background/cell counts is checked. Historical manifests remain unchanged.', '',
             'Source freeze: `'+s['freeze_commit']+'`. Runtime: '+', '.join(f'{k} {v}' for k,v in s['environment'].items())+'.', '',
             'The source freeze was public before this transfer, but sector 29 had already been inspected in LS7B and historical LS7C development. '
             'This result is not an independent test on unseen data. Digital injections occur after mission processing and add no photon shot noise. '
             'No physical laser sensitivity, astrophysical completeness, population limit or detection claim follows.', '',
             '## Continuation', '',
             ('Review the per-background and omitted-shape outcomes before planning a genuinely unseen evaluation. Any such evaluation needs its own '
              'fixed model, eligibility and joint control protocol; a closed-sector pass alone does not adopt the detector.' if passed else
              'Keep this transfer closed. Diagnose the failed cells using the saved background extracts, separating temporal/source-score losses, '
              'covariance scaling, residual failures and morphology ambiguity. Use the existing records for that diagnosis; do not rerun or retune '
              'LS7G or open another observing sector merely because this transfer failed.'), '',
             '- [Frozen protocol](../LS7G_TRANSFER_PROTOCOL.md), [configuration](../config/ls7g_transfer.json), [source checksums](../LS7G_FREEZE.sha256)',
             '- [Summary and per-background outcomes](summary.json), [all trials](trials.jsonl.gz), [audit with loss and ambiguity IDs](AUDIT.json)',
             '- [Background extracts](backgrounds.npz), [training and folds](training.json), [all model templates](models.json), [injection patterns](patterns.json)',
             '- [Source identities](source_manifest.json), [output checksums](SHA256SUMS), [continuation](../LS7G_CONTINUATION.md)', '']
    (out/'REPORT.md').write_text('\n'.join(text))
    short = (f'LS7G completed **3,540 fixed transfer trials** on the ten already closed sector-29 backgrounds. '
             f'The primary joint descriptive gate **{"passes on these closed data" if passed else "fails"}**. '
             f'Nominal recovery at the fixed margin −1 is **{nominal[0]}/40, {nominal[1]}/40, {nominal[2]}/40**; '
             f'displaced recovery is **{displaced[0]}/160, {displaced[1]}/160, {displaced[2]}/160**. '
             f'**{len(bad_controls)}/30** instrumental control cells exceed their allowance. '
             f'The independent audit passes; no detector is adopted and no candidate is promoted.')
    next_step = ('Review transfer stability and omitted-shape outcomes before a separately frozen unseen qualification.' if passed else
                 'Next, diagnose the failed transfer cells from the saved sector-29 extracts, keeping the frozen LS7G rule and outcomes unchanged. '
                 'Separate temporal, source-score, residual and nuisance-separation losses before proposing another model or observing sector.')
    if args.update_status:
        continuation = '# LS7G continuation\n\n13 September 2026.\n\n'+short+'\n\n'+next_step+'\n\n'
        continuation += ('The margin −1 was chosen from LS7F sector-32 development before this run. It permits a nuisance model to fit better; '
                         f'{len(ambiguous)} accepted primary rows do so. Sector 29 was already inspected in earlier work. '
                         'This is not independent validation or source identification.\n\n'
                         '[Read the complete report and figure](results_ls7g_transfer/REPORT.md). '
                         'The backgrounds, models, training vectors and every trial are public; raw FITS downloads are unnecessary for the independent audit.\n\n'
                         '```sh\nsha256sum -c LS7G_FREEZE.sha256\n(cd results_ls7g_transfer && sha256sum -c SHA256SUMS)\n'
                         'OPENBLAS_NUM_THREADS=1 python scripts/ls7g_review.py\n```\n\n'
                         f'Source freeze: `{s["freeze_commit"]}`. All historical LS7B/LS7C/LS7E/LS7F results remain unchanged, '
                         'and the original M43 held-out panels remain unopened. The canonical status is PROJECT_STATUS.md.\n')
        (ROOT/'LS7G_CONTINUATION.md').write_text(continuation)
        status_path = ROOT/'PROJECT_STATUS.md'
        status = status_path.read_text()
        assert '## LS7G completed' not in status
        if '## LS7G queued:' in status:
            lo, hi = status.index('## LS7G queued:'), status.index('## LS7F completed:')
            status = status[:lo]+status[hi:]
        section = '## LS7G completed: fixed transfer to sector 29\n\n'+short+'\n\n'+next_step+'\n\n'
        section += '[Result and figure](results_ls7g_transfer/REPORT.md), [protocol](LS7G_TRANSFER_PROTOCOL.md), [continuation](LS7G_CONTINUATION.md).\n\n'
        status = status.replace('## LS7F completed:', section+'## LS7F completed:', 1)
        start = '| LS research |'
        status = '\n'.join('| LS research | [LS7G](results_ls7g_transfer/REPORT.md): 3,540-case closed-sector transfer completed; no adopted model or candidate |' if line.startswith(start) else line for line in status.splitlines())+'\n'
        status_path.write_text(status)
        direction = ROOT/'PROJECT_DIRECTION.md'
        direction.write_text(direction.read_text()+'\n13 September 2026: '+short+'\n\n'+next_step+' Details: LS7G_CONTINUATION.md.\n')
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    print(json.dumps({'report': str(out/'REPORT.md'), 'primary_gate': passed, 'nominal': nominal, 'displaced': displaced,
                      'failed_control_cells': len(bad_controls), 'nuisance_preferred_acceptances': len(ambiguous)}))


if __name__ == '__main__':
    main()
