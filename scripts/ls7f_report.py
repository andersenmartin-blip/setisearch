#!/usr/bin/env python3
"""Render the completed LS7F evidence; no new fits or threshold selection."""
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7f_separation'


def main():
    s = json.loads((OUT/'summary.json').read_text())
    w = json.loads((OUT/'sweeps.json').read_text())
    audit = json.loads((OUT/'AUDIT.json').read_text())
    assert audit['passed']
    rows = [json.loads(r) for r in gzip.decompress((OUT/'features.jsonl.gz').read_bytes()).splitlines()]
    cells = s['cells']
    primary = 'covariance_sparse'
    control_start = s['endpoints'][primary+'/broad']['points']['control_safe']['index']
    low = w[primary+'/broad']['thresholds'][control_start-1]
    high = s['endpoints'][primary+'/broad']['points']['signal_safe']['threshold']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'ls7f-separation',
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 4.7), sharex=True)
    for name, color, style, label in [('original', '#66758a', '--', 'Original nuisance bank'),
                                      ('broad', '#087f8c', '-', 'Expanded nuisance bank')]:
        sweep = w[primary+'/'+name]
        cuts, counts = np.array(sweep['thresholds']), np.array(sweep['counts'])
        values = [100*counts[:, 0]/40, 100*counts[:, 3]/160,
                  np.max(np.column_stack([100*counts[:, i]/c['trials'] for i, c in enumerate(cells) if not c['signal']]), axis=1)]
        for ax, y in zip(axes, values):
            ax.step(cuts, y, where='pre', color=color, ls=style, lw=2, label=label)
    for ax, requirement, title in zip(axes, [90, 80, 5],
                                    ['Weak nominal pulse', 'Weak displaced pulse', 'Worst control cell']):
        ax.axhline(requirement, color='#b96522', lw=1.3, ls=':')
        ax.axvspan(low, high, color='#43aa8b', alpha=.16)
        ax.axvline(0, color='#aaa', lw=.9)
        ax.axvline(9, color='#aaa', lw=.9, ls=':')
        ax.set(xlim=(-7, 21), ylim=(-2, 102), title=title, xlabel='Required source / nuisance margin')
        ax.grid(axis='y', alpha=.14)
        ax.set_xticks([-5, 0, 5, 9, 15, 20])
    axes[0].set_ylabel('Recovered (%)')
    axes[1].set_ylabel('Recovered (%)')
    axes[2].set_ylabel('Accepted (%)')
    fig.suptitle('LS7F · A closed-data tradeoff exists only at negative margins', x=.06, ha='left', fontsize=15, weight='bold')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper left', bbox_to_anchor=(.05, .91), ncol=2, frameon=False)
    fig.text(.06, .045, 'Covariance + sparse pixel. Weak strength = 8.5. Shading: all 27 development requirements met.\n'
             'Known controls are now modeled; these outcome-selected margins are not independent qualification.', fontsize=9, color='#465365')
    fig.subplots_adjust(top=.75, bottom=.23, left=.06, right=.98, wspace=.28)
    fig.savefig(OUT/'separation_tradeoff.svg', metadata={'Date': None})
    svg_path = OUT/'separation_tradeoff.svg'
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
    fig.savefig(OUT/'separation_tradeoff.png', dpi=155)
    plt.close(fig)

    text = [
        '# LS7F: broader nuisance models expose a conditional development tradeoff', '',
        '13 September 2026. **The expanded nuisance bank removes all matched control acceptances at the old margin 9, but loses additional stellar tests. '
        'All 27 development requirements can be met together only after allowing negative margins, where a nuisance fit may be better than the stellar fit. '
        'No detector is adopted and no astronomical candidate is promoted.**', '',
        'This study reuses all **3,180 saved LS7E trials**, spanning **ten shared L 98-59 sector-32 backgrounds**. '
        'There are **zero new injections and zero added observing days**. It does not rerun or revise the earlier LS7C qualification. '
        'The enlarged bank and tradeoff sweep were fixed before LS7F scoring, but were motivated by already known LS7E failures: this is retrospective development.', '',
        '## What changed', '',
        'Add **108 rectangular nuisance templates**: every intersecting 3×3, 1×5 and 5×1 placement in the 11×11 stamp. '
        'Partial overlaps and duplicate aperture projections are retained. The original 18-pixel aperture, stellar fits, '
        '94 model contexts, covariance folds, temporal selection, source/residual gates and optional sparse-pixel penalty are unchanged. '
        'Both full-covariance methods are compared, with and without the sparse option.', '',
        'All **12,720** replayed original fit checks reproduce exactly in the recorded LS7F runtime. The original nuisance templates '
        'remain in the expanded bank. Because this can only reduce the source/nuisance margin, it cannot improve recovery at the same threshold.', '',
        '## Keeping margin 9 removes controls and loses signals', '',
        'Counts below use the covariance-plus-sparse method. Nominal denominators are 40 per strength; displaced denominators are 160.', '',
        '| Strength | Nominal: original → expanded | Displaced: original → expanded | 3×3 controls: original → expanded |',
        '|---|---:|---:|---:|',
    ]
    old9 = s['endpoints'][primary+'/original']['points']['reference_9']['counts']
    broad9 = s['endpoints'][primary+'/broad']['points']['reference_9']['counts']
    for j, score in enumerate([8.5, 12, 20]):
        text.append(f'| {score:g} | {old9[j]}/40 → {broad9[j]}/40 | {old9[j+3]}/160 → {broad9[j+3]}/160 | {old9[j+18]}/40 → {broad9[j+18]}/40 |')
    losses = [r for r in rows if r['kind'] in ('stellar', 'off_profile') and r['methods'][primary]['lost_at_9']]
    text += ['',
        'At this unchanged threshold, every one of the **600 original matched controls and 360 extended controls** is rejected. '
        'All crossed the temporal screening threshold in LS7E. The added rectangles now explicitly model the previously omitted extended shapes; '
        'this does not establish rejection of unmodeled artifacts.', '',
        f'The expanded bank loses **{len(losses)}** previously recovered stellar trial rows at margin 9: '
        f'{sum(r["suite"]=="ls7c_replay" for r in losses)} original replay rows, '
        f'{sum(r["suite"]=="sparse_stress" and r["residual_location"]=="inside" for r in losses)} inside-aperture stress rows and '
        f'{sum(r["suite"]=="sparse_stress" and r["residual_location"]=="outside" for r in losses)} outside-aperture stress rows. '
        'These include shared/identical backgrounds, not independent losses. Each loss flag and trial ID is retained in the feature ledger.', '',
        'For stellar pulses with an extra inside-aperture pixel, fixed-9 recovery changes from 23/80, 78/80, 79/80 '
        'to **18/80, 74/80, 79/80** across strengths 8.5, 12 and 20. The unchanged weak negative-pixel cases remain below the temporal threshold. '
        'Without the sparse option, corresponding expanded-bank counts remain 0/80, 2/80 and 2/80. The sparse mechanism still addresses a distinct residual problem.', '',
        '## Exhaustive threshold accounting', '',
        'Every distinct eligible margin is evaluated, with ties handled together, the unchanged 9 included explicitly, and a final reject-all sentinel. '
        'All other gates stay fixed. The **27 cells** require nominal ≥36/40 and displaced ≥128/160 at each of three strengths, '
        'plus ≤5% acceptance in each of 21 original/extended control cells. Fixed-flux, stress, null and bounded-pointing trials retain separate full descriptions.', '',
        '| Method / bank | Evaluated cut positions | Positions meeting all 27 requirements |',
        '|---|---:|---:|',
    ]
    names = {'covariance_sparse': 'Covariance + sparse pixel', 'covariance_plain': 'Covariance without sparse pixel'}
    for key, e in s['endpoints'].items():
        method, name = key.split('/')
        text.append(f'| {names[method]} / {name} | {e["thresholds_evaluated"]:,} | **{e["joint_feasible_thresholds"]}** |')
    text += ['',
        'With the original nuisance bank, **no threshold** satisfies the joint requirements in either method. '
        'For example, the first enumerated control-safe sparse margin is 15.7364, which recovers only **3/40** weak nominal and **17/160** weak displaced trials. '
        'The last signal-safe original margin, 1.84628, accepts **14/40** weak 3×3 controls. A simple relaxation of the original margin therefore cannot meet the joint requirements.', '',
        'With the expanded bank, the following exact feasible intervals describe the recorded floating-point scores; the lower boundary is open and the upper boundary closed. '
        'Printed decimals are summaries; use the full JSON values for exact decisions.', '',
        '| Method | Feasible margin interval on the closed records |', '|---|---|',
    ]
    for method in names:
        key = method+'/broad'
        e = s['endpoints'][key]
        start = e['points']['control_safe']['index']
        lower = w[key]['thresholds'][start-1]
        upper = e['points']['signal_safe']['threshold']
        text.append(f'| {names[method]} | ({lower:.9f}, {upper:.9f}] |')
    safe = s['endpoints'][primary+'/broad']['points']['control_safe']
    text += ['',
        f'The first enumerated control-safe expanded sparse margin is **{safe["threshold"]:.6f}**. '
        'It recovers **38/40, 40/40 and 40/40** nominal pulses and **138/160, 160/160 and 159/160** displaced pulses. '
        'It accepts **2/40 weak 2×2 controls and 2/40 weak 3×3 controls**, with zero accepted cases in the other 19 core control cells. '
        'This is an outcome-selected diagnostic endpoint, not a chosen search threshold.', '',
        '**The entire feasible interval is negative.** The margin is `best nuisance objective − best stellar objective`, so a negative margin '
        'allows some accepted cases whose nuisance model fits better. At a nonnegative margin of 0, the expanded sparse method recovers '
        '**36/40** weak nominal pulses but only **125/160** weak displaced pulses, below the required 128. '
        'Without the sparse option, these counts are 35/40 and 121/160. Thus this exercise does not show that all required weak events favor a stellar origin.', '',
        '![Exact closed-data separation tradeoff](separation_tradeoff.svg)', '',
        'The figure displays weak strength 8.5 and the worst acceptance fraction over all 21 control cells for the sparse method. '
        'The shaded interval satisfies **all six signal and 21 control requirements**, including the stronger cells retained in the tables and complete sweep. '
        'The displayed margin range is a zoom; the machine-readable sweep includes every cut position.', '',
        '## Verification and limits', '',
        '- Six analytical tests pass: geometry, tied boundaries, eligibility, empty eligible sets, a known signal-loss example and nuisance-template rescaling.',
        f'- Independent direct whitened least squares checks **{audit["direct_whitened_fits"]:,}** stellar/new winning fits; maximum absolute disagreement is {audit["max_direct_fit_absolute_error"]:.3g}.',
        f'- Independent QR-based enumeration checks **{audit["exhaustive_rectangle_alternatives"]:,}** rectangle/pixel alternatives across every trial and both methods; maximum minimum-objective disagreement is {audit["max_full_bank_minimum_absolute_error"]:.3g}.',
        f'- Independent Boolean accounting checks all **{audit["sweep_cell_counts_checked"]:,}** threshold/cell counts, every endpoint accepted/rejected/lost ID, and every descriptive/per-background count.',
        '- Historical freeze/result manifests pass before and after scoring. All prior LS7C/LS7E decisions are preserved, and M43 held-out panels remain unopened.', '',
        f'Source freeze **`{s["freeze_commit"]}`** was published before LS7F extraction. '
        f'Runtime: Python {s["environment"]["python"]}, NumPy {s["environment"]["numpy"]}, SciPy {s["environment"]["scipy"]}; '
        'the figure uses Matplotlib 3.10.8. The source freeze and passed code audit do not make these previously seen data an independent evaluation.', '',
        'There are only ten shared backgrounds. The rectangle controls are digital, post-mission-processing cases without added photon noise. '
        'Their acceptance fractions are not calibrated false-alarm probabilities, astrophysical completeness or laser-population limits. '
        'The 18-pixel fit cannot resolve all full-image spatial ambiguities.', '',
        '## Concrete continuation', '',
        'LS7F identifies a testable expanded-bank tradeoff and rules out repairing the original bank by changing its margin alone. '
        'Keep every result closed. The next useful step is a **separately frozen transfer comparison on already closed sector 29**, '
        'with any outcome-selected margin explicitly labeled as development, broad and additional unmodeled nuisances, '
        'inside-aperture residual stress and the nonnegative-margin comparison reported alongside it. '
        'Freeze the rule and transfer-specific training/eligibility plan before inspecting transfer outcomes. '
        'Do not treat a negative-margin acceptance as identification of a stellar or artificial source. '
        'No independent sector is warranted for qualification from LS7F alone.', '',
        '- [Protocol](../LS7F_SEPARATION_PROTOCOL.md), [configuration](../config/ls7f_separation.json), [source freeze](../LS7F_FREEZE.sha256)',
        '- [Summary and per-background counts](summary.json), [all threshold counts](sweeps.json), [endpoint case certificates](certificates.json)',
        '- [All 3,180 feature rows and paired losses](features.jsonl.gz), [rectangle templates](bank.json), [independent audit](AUDIT.json)',
        '- [Source identities](source_manifest.json), [output checksums](SHA256SUMS), [continuation](../LS7F_CONTINUATION.md)',
    ]
    (OUT/'REPORT.md').write_text('\n'.join(text)+'\n')


if __name__ == '__main__':
    main()
