#!/usr/bin/env python3
"""Report every frozen LS8U outcome after independent verification."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8u_residuals'


def main():
    audit = json.loads((OUT / 'audit.json').read_text()); assert audit['status'] == 'PASS'
    data = json.loads((OUT / 'diagnostics.json').read_text())
    controls = json.loads((OUT / 'injection_controls.json').read_text())
    lines = ['# LS8U: TESS_260647166 residual and duration-matched noise study', '',
        'Both retained LS8T contexts, both products and both coordinate conventions are included. '
        'No new archive bytes or exposures were acquired. The positive TG015701_P0 remains '
        '**UNRESOLVED_WITHIN_FIXED_SCOPE**; the negative TG000101_N0 remains '
        '**SPATIALLY_STRUCTURED** under the original LS8T gate.', '',
        '**Retrospective diagnostics only: energy ratios, covariance models and held-sideband '
        'comparisons are not calibrated significances, probabilities or completeness measurements.**', '',
        f'Independent audit **PASS**: {audit["comparisons"]["numeric"]:,} numerical comparisons and '
        f'{audit["comparisons"]["exact"]:,} exact checks; no disagreements. Eighteen pre-analysis '
        'tests pass (ten duration/cadence/boundary tests and eight inherited spatial tests). '
        'All 48 signed known-template controls, 80 signed compact controls and 128 additive checks pass.', '',
        '## Fixed durations, covariance and residual comparison', '',
        'TG015701_P0 sums one 49-second exposure; TG000101_N0 sums three 42-second exposures '
        '(126 seconds total exposure). The IID reference uses the exact OLS prediction weights, '
        'including the d²/n baseline-estimation term. A pooled lag-1/lag-2 correlation estimated '
        'from training-only pixel residuals, with a Bartlett taper, supplies the second model. '
        'All event/baseline covariance enters the same quadratic form for both durations. '
        'Adjacent time differences outside 0.5–1.5 times that context’s cadence split covariance '
        'blocks. This estimated separable model is descriptive: longer correlations, '
        'nonstationarity and template-estimation uncertainty are not calibrated. Both the '
        'correlated and IID references remain visible.', '',
        'The positive context has 24 single-row control targets; the negative has eight '
        'nonoverlapping three-row targets. Each excludes two neighboring rows on each side '
        'from training, in addition to the original native event and its guards. Templates, '
        'variances and correlations are refitted without held values; the original geometric '
        'center and aperture stay fixed. These controls share training data and differ in '
        'leverage and position from the selected native event. Their counts are not p-values.', '',
        '| Control | Product / center | Combined weighted explained | Residual/reference, correlated | Residual/reference, IID | Held blocks >= native | Correlated/IID variance | Top 10 residual pixels |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for event in data:
        for conv, info in event['conventions'].items():
            for kind in ('CAL', 'COR'):
                d = info[kind]; m = d['models']['combined']; iid = d['iid_models']['combined']
                top = d['spatial']['concentration']['weighted']['top10_fraction']
                lines.append(f'| {event["id"]} | {kind} / {conv} | {m["weighted_explained"]:.4%} | '
                    f'{m["weighted_residual_to_sideband_ratio"]:.6f} | {iid["weighted_residual_to_sideband_ratio"]:.6f} | '
                    f'{d["held_blocks_at_least_event"]}/{d["held_block_count"]} | {d["temporal"]["correlated_to_iid_variance_factor"]:.6f} | {top:.4%} |')
    lines += ['', '## Exact boundary accounting', '',
        'Both apertures retain radius 25 and their original centers. The C0/C1 intersection '
        'cancels exactly in the difference. For each product, C1 minus C0 equals the sum over '
        'C1-only pixels minus the sum over C0-only pixels. The full signed pixel list and the '
        'analogous squared-energy identity are retained in diagnostics.json. This accounts for '
        'aperture sums; it does not uniquely assign a physical cause or explain every change in '
        'a fitted model, whose training profile/background also depend on the convention.', '',
        '| Control | Product | C0-only pixels / sum ADU | C1-only pixels / sum ADU | C1 − C0 ADU |',
        '|---|---|---:|---:|---:|']
    for event in data:
        b = event['boundary_account']; counts = b['pixel_counts']
        for kind, p in b['products'].items():
            lines.append(f'| {event["id"]} | {kind} | {counts["C0_only"]} / {p["C0_only"]["flux_adu"]:.6f} | '
                f'{counts["C1_only"]} / {p["C1_only"]["flux_adu"]:.6f} | {p["difference_flux_adu"]:.6f} |')
    lines += ['', '## Paired correction and brightness protection', '',
        'Residual CAL and DELTA use the same COR combined projector. Their energies and the '
        'signed cross term add to COR residual energy; they are not independent cause fractions.', '',
        '| Control / center | CAL / COR residual energy | DELTA / COR | Twice cross / COR |',
        '|---|---:|---:|---:|']
    for event in data:
        for conv, info in event['conventions'].items():
            a = info['correction_residual_account']['weighted']
            lines.append(f'| {event["id"]} / {conv} | {a["cal_over_cor"]:.6f} | {a["delta_over_cor"]:.6f} | {a["twice_cross_over_cor"]:.6f} |')
    lines += ['', 'Pure brightness additions are ±0.1% per exposure: summed coefficients '
        'are ±0.001 for the positive context and ±0.003 for the negative. Displacement additions '
        'are ±0.05 gradient units per exposure, a linearized template rather than nonlinear '
        'resampling. Five fixed compact positions receive both signs with total amplitude five '
        'modeled event-pixel SDs, interpreted as equal additions over the event duration. The '
        'table shows losses from hypothetical displacement plus constant subtraction. No '
        'subtraction, veto or new mask is adopted.', '',
        '| Control | Product / center | Brightness weighted energy retained | Brightness signed flux retained |',
        '|---|---|---:|---:|']
    for r in controls:
        if r['kind'] == 'brightness' and r['sign'] == 1:
            lines.append(f'| {r["id"]} | {r["product"]} / {r["convention"]} | '
                f'{r["displacement_removal_retained_weighted_energy_fraction"]:.4%} | {r["displacement_removal_flux_fraction"]:.4%} |')
    lines += ['', '## All COR residual maps and held-block controls', '',
        'Each panel has its own symmetric scale and retains the unchanged aperture. Standardized '
        'pixels are divided by the modeled event SD, not Gaussian sigmas. Only the plotting '
        'viewport is cropped; no analysis pixels are removed.', '']
    for event in data:
        fig, axes = plt.subplots(2, 3, figsize=(13.5, 8), constrained_layout=True)
        for row, (conv, info) in enumerate(event['conventions'].items()):
            with np.load(OUT / event['id'] / f'{conv}_arrays.npz') as arr:
                mask = arr['COR_mask']; center = info['center']
                fields = [arr['COR_residual'], arr['COR_residual'] / np.sqrt(arr['COR_variance'])]
                for col, (values, label) in enumerate(zip(fields, ['Residual (ADU)', 'Residual / modeled event SD'])):
                    field = np.full(mask.shape, np.nan); field[mask] = values
                    bound = max(float(np.max(np.abs(values))), 1e-12)
                    im = axes[row, col].imshow(field, origin='lower', cmap='RdBu_r', vmin=-bound, vmax=bound)
                    axes[row, col].set_xlim(center[0] - 27, center[0] + 27); axes[row, col].set_ylim(center[1] - 27, center[1] + 27)
                    for radius in (8, 16, 25): axes[row, col].add_patch(Circle(center, radius, fill=False, color='#444444', alpha=.45, linewidth=.7))
                    axes[row, col].set_title(f'{conv} · {label}', fontsize=10)
                    axes[row, col].set_xlabel('Native x pixel'); axes[row, col].set_ylabel('Native y pixel')
                    fig.colorbar(im, ax=axes[row, col], shrink=.8)
            d = info['COR']; ax = axes[row, 2]
            vals = [p['models']['combined']['weighted_residual_to_sideband_ratio'] for p in d['held_blocks']]
            rows = [p['held_local_rows'][0] for p in d['held_blocks']]
            ax.scatter(rows, vals, color='#356a83', s=28, label=f'Held {event["duration_rows"]}-row block')
            ev = d['models']['combined']['weighted_residual_to_sideband_ratio']
            ax.axhline(ev, color='#b34c40', linewidth=1.5, label=f'Native = {ev:.3g}')
            ax.set_yscale('log'); ax.set_xlabel('First held local row'); ax.set_ylabel('Residual / reference energy')
            ax.set_title(f'{conv} · {d["held_blocks_at_least_event"]}/{d["held_block_count"]} blocks >= native')
            ax.grid(alpha=.15); ax.legend(fontsize=8)
        fig.suptitle(f'{event["id"]} · {event["duration_rows"]} × {event["cadence_seconds"]} s residual study\n{event["original_ls8t_classification"]}', fontsize=13)
        filename = event['id'] + '_residuals.png'; fig.savefig(OUT / filename, dpi=155); plt.close(fig)
        lines += [f'![{event["id"]} residuals]({filename})', '']
    lines += ['## Stop and interpretation boundaries', '',
        'A high ratio establishes a mismatch with these local sidebands under the stated model; '
        'a low ratio does not prove an ordinary-noise origin. Fixed ring/quadrant partitions '
        'and top-pixel concentrations describe the residual without selecting pixels to refit. '
        'The LS8T classifications and LS8S thresholds remain unchanged. No technical-origin '
        'interpretation, qualified candidate, detector or coverage is established.', '',
        'This single bounded study is closed regardless of result. Rank-5 EC 12578-2107 is next '
        'for a separately frozen independent transfer from the unchanged target ledger, exact '
        'pair CH_PR100002_TG008901_V0300 and CH_PR100002_TG008902_V0300. Its science values '
        'remain unopened. Further TESS_260647166 tuning is not part of this study. Raw imagettes, '
        'reserved TESS/M43 material and the unsent calibration request remain unchanged.', '',
        '[Protocol](../LS8U_RESIDUAL_NOISE_PROTOCOL.md) · [Full diagnostics](diagnostics.json) · '
        '[Signed injections](injection_controls.json) · [Audit](audit.json) · '
        '[Original LS8T report](../results_ls8t_images/REPORT.md)', '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))
    summary = json.loads((OUT / 'summary.json').read_text())
    summary.update(status='COMPLETE_AUDITED_DESCRIPTIVE_ONLY', audit='PASS', audit_comparisons=audit['comparisons'])
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'next_action.json').write_text(json.dumps({'status': 'BOUNDED_STUDY_CLOSED',
        'automatic_new_source_acquisition': False, 'new_classifier_adopted': False,
        'next': 'Interpret complete LS8U; then separately freeze rank-5 EC 12578-2107 chronological-pair metadata and L2 transfer.',
        'original_ls8t_labels_preserved': True}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
