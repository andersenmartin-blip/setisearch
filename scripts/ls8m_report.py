#!/usr/bin/env python3
"""Publish all LS8M cases and fixed visual summaries after an independent pass."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8m_residuals'


def main():
    audit = json.loads((OUT / 'audit.json').read_text())
    assert audit['status'] == 'PASS', 'report requires independent PASS'
    data = json.loads((OUT / 'diagnostics.json').read_text())
    controls = json.loads((OUT / 'injection_controls.json').read_text())
    lines = ['# LS8M: retained WASP-189 residuals and local variability', '',
        'All three fixed events, both CAL/COR products and both coordinate conventions are complete. '
        'No new native source bytes were acquired. Original LS8L labels remain unchanged.', '',
        '**This is descriptive development on previously selected events. Energy ratios and '
        'overlapping sideband ranks are not detection significances or source probabilities.**', '',
        f'Independent audit: **PASS**, {audit["comparisons"]["numeric"]:,} numerical comparisons and '
        f'{audit["comparisons"]["exact"]:,} exact checks; zero disagreements. Eight pre-analysis tests, '
        '72 signed known-template cases, 120 signed compact cases and all 192 additive linearity checks pass.', '',
        '## Native residual comparison', '',
        'The table uses the combined weighted brightness/gradient/constant model. '
        'The reference is local sideband variability after applying the same spatial model. '
        'The aperture SD ratio compares the full sideband flux covariance with a diagonal-only estimate.', '',
        '| Event | Product / center | Weighted explained | Residual / sideband energy (weighted) | Side controls >= event | Top 10 residual pixels (weighted) | Aperture SD ratio |',
        '|---|---|---:|---:|---:|---:|---:|']
    for event in data:
        for conv, info in event['conventions'].items():
            for kind in ('CAL', 'COR'):
                d = info[kind]; m = d['models']['combined']; top = d['spatial']['concentration']['weighted']['top10_fraction']
                lines.append(f'| {event["id"]} | {kind} / {conv} | {m["weighted_explained"]:.4%} | '
                    f'{m["weighted_residual_to_sideband_ratio"]:.6f} | {d["loso_at_least_event"]}/24 | {top:.4%} | '
                    f'{m["aperture_correlation_sd_ratio"]:.6f} |')
    lines += ['', '## Paired correction residual identity', '',
        'CAL and DELTA below use the same COR projector. The cross term can be negative; '
        'these columns add to one and are not independent physical-cause fractions.', '',
        '| Event / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |', '|---|---:|---:|---:|']
    for event in data:
        for conv, info in event['conventions'].items():
            a = info['correction_residual_account']['weighted']
            lines.append(f'| {event["id"]} / {conv} | {a["cal_over_cor"]:.6f} | {a["delta_over_cor"]:.6f} | {a["twice_cross_over_cor"]:.6f} |')
    lines += ['', '## Brightness protection', '',
        'Pure brightness coefficients are recovered by the combined model. The table quantifies '
        'what a hypothetical displacement-plus-constant subtraction would remove. No such removal is adopted.', '',
        '| Event | Product / center | Brightness weighted energy retained | Brightness signed flux retained |', '|---|---|---:|---:|']
    for r in controls:
        if r['kind'] == 'brightness' and r['sign'] == 1:
            lines.append(f'| {r["id"]} | {r["product"]} / {r["convention"]} | '
                f'{r["displacement_removal_retained_weighted_energy_fraction"]:.4%} | '
                f'{r["displacement_removal_flux_fraction"]:.4%} |')
    lines += ['', '## Fixed residual maps and all sideband controls', '',
        'Each map uses the COR combined weighted fit within the unchanged radius-25 mask. '
        'A separate symmetric color range is used for each panel and is labeled. Values divided '
        'by the sideband-derived pixel SD are descriptive standardized residuals, not Gaussian sigmas. '
        'The plots retain C0 and C1 and all 24 controls.', '']
    for event in data:
        fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.0), constrained_layout=True)
        for row, (conv, info) in enumerate(event['conventions'].items()):
            with np.load(OUT / event['id'] / f'{conv}_arrays.npz') as arr:
                mask = arr['COR_mask']; center = info['center']
                fields = [arr['COR_residual'], arr['COR_residual'] / np.sqrt(arr['COR_variance'])]
                for col, (values, label) in enumerate(zip(fields, ['Residual (ADU)', 'Residual / sideband pixel SD'])):
                    field = np.full(mask.shape, np.nan); field[mask] = values
                    bound = max(float(np.max(np.abs(values))), 1e-12)
                    im = axes[row, col].imshow(field, origin='lower', cmap='RdBu_r', vmin=-bound, vmax=bound)
                    axes[row, col].set_xlim(center[0] - 27, center[0] + 27); axes[row, col].set_ylim(center[1] - 27, center[1] + 27)
                    for radius in (8, 16, 25): axes[row, col].add_patch(Circle(center, radius, fill=False, color='#444444', alpha=.45, linewidth=.7))
                    axes[row, col].axvline(center[0], color='#444444', alpha=.4, linewidth=.6)
                    axes[row, col].axhline(center[1], color='#444444', alpha=.4, linewidth=.6)
                    axes[row, col].set_title(f'{conv} · {label}'); axes[row, col].set_xlabel('Native x pixel'); axes[row, col].set_ylabel('Native y pixel')
                    fig.colorbar(im, ax=axes[row, col], shrink=.8)
            d = info['COR']; ax = axes[row, 2]
            vals = [p['models']['combined']['weighted_residual_to_sideband_ratio'] for p in d['loso']]
            rows = [p['held_local_row'] for p in d['loso']]
            ax.scatter(rows, vals, color='#356a83', s=24, label='Held side row')
            ev = d['models']['combined']['weighted_residual_to_sideband_ratio']
            ax.axhline(ev, color='#b34c40', linewidth=1.5, label=f'Event = {ev:.3g}')
            ax.set_yscale('log'); ax.set_xlabel('Held local row'); ax.set_ylabel('Residual / reference energy (weighted)')
            ax.set_title(f'{conv} · {d["loso_at_least_event"]}/24 controls >= event')
            ax.grid(alpha=.15); ax.legend(fontsize=8)
        fig.suptitle(f'{event["id"]} · COR residual and local variability\n{event["original_ls8l_classification"]}', fontsize=13)
        filename = event['id'] + '_residuals.png'; fig.savefig(OUT / filename, dpi=155); plt.close(fig)
        lines += [f'![{event["id"]} residuals]({filename})', '']
    lines += ['## Interpretation and stop', '',
        'A large residual/reference ratio establishes a mismatch with these local sidebands, not a '
        'stellar or artificial origin. A small ratio does not prove that a selected event is ordinary noise. '
        'Spatial cells and compactness help describe what the fixed template misses; they are not tuned cuts.', '',
        'The study stops on these three contexts. LS8L classifications, thresholds and source scope are '
        'unchanged; no qualified candidate, detector or coverage is added. Independent transfer would require '
        'a new prospective freeze. The raw-imagette calibration request remains unsent.', '',
        '[Protocol](../LS8M_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · '
        '[Signed injections](injection_controls.json) · [Independent audit](audit.json) · '
        '[Original LS8L report](../results_ls8l_images/REPORT.md)', '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))
    summary = json.loads((OUT / 'summary.json').read_text()); summary['status'] = 'COMPLETE_AUDITED_DESCRIPTIVE_ONLY'
    summary['audit'] = audit['status']; summary['audit_comparisons'] = audit['comparisons']
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'next_action.json').write_text(json.dumps({'status': 'BOUNDED_STUDY_CLOSED',
        'automatic_new_source_acquisition': False, 'new_classifier_adopted': False,
        'next': 'Review retained residual/noise result; any independent GJ 1132 transfer requires its own prospective freeze.',
        'original_ls8l_labels_preserved': True}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
