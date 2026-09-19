#!/usr/bin/env python3
"""Presentation of frozen LS8C outputs; performs no additional model fitting."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, ScalarFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8c_auxiliary'
FREEZE = '971b91ccef711408798d6dc5abe2db7801ed5edf'
FIELDS = ('FLUX', 'DARK', 'BACKGROUND', 'SMEARING_LC', 'CONTA_LC', 'CONTA_LC_ERR',
          'SMEARING_LC_ERR', 'ROLL_ANGLE', 'LOCATION_X', 'LOCATION_Y',
          'CENTROID_X', 'CENTROID_Y', 'OFFSET_X', 'OFFSET_Y')
PREDICTORS = ('DARK', 'BACKGROUND', 'CONTA_LC', 'SMEARING_LC', 'ROLL_ANGLE', 'OFFSET_X', 'OFFSET_Y')


def label(r):
    return r['file_key'].split('_')[2] + ' ' + ('P' if r['sign'] == 'positive' else 'N') + str(r['cluster_id'])


def profile(ax, record, name, factor=1.):
    series = record['series'][name]
    ax.set_title(name, fontsize=10, loc='left', fontweight='bold')
    if series['status'] != 'AVAILABLE':
        ax.text(.5, .5, series['status'], transform=ax.transAxes, ha='center')
        return
    x = np.array(record['times_seconds']) / 60.
    y = np.array(series['residual']) / factor
    side = np.array(record['side_indices']) - record['context_start']
    event = np.array(record['event_indices']) - record['context_start']
    guard = np.array(sorted(set(range(len(x))) - set(side) - set(event)))
    color = '#ad4525' if record['sign'] == 'positive' else '#1765aa'
    half = np.median(np.diff(x)) / 2.
    ax.axvspan(x[event[0]] - half, x[event[-1]] + half, color=color, alpha=.10, linewidth=0)
    ax.axhline(0., color='#aab1b9', lw=.65)
    ax.plot(x, y, color='#aab1b9', lw=.75, zorder=1)
    ax.scatter(x[side], y[side], s=14, color='#27364a', zorder=3)
    ax.scatter(x[guard], y[guard], s=20, facecolors='white', edgecolors='#747e88', zorder=4)
    ax.scatter(x[event], y[event], s=28, color=color, zorder=5)
    unit = '1,000 electrons' if factor == 1000. else series['unit']
    ax.set_ylabel(unit, fontsize=9)
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    fmt = ScalarFormatter(useMathText=True)
    fmt.set_powerlimits((-3, 4))
    fmt.set_useOffset(False)
    ax.yaxis.set_major_formatter(fmt)
    ax.tick_params(labelsize=8)
    ax.spines[['top', 'right']].set_visible(False)


def finish(fig, path, title):
    fig.suptitle(title, fontsize=17, x=.055, ha='left', fontweight='bold')
    legend = [Line2D([0], [0], marker='o', lw=0, color='#27364a', label='Sideband used for trend'),
              Line2D([0], [0], marker='o', lw=0, markerfacecolor='white', color='#747e88', label='Guard: excluded'),
              Line2D([0], [0], marker='o', lw=0, color='#ad4525', label='Positive event'),
              Line2D([0], [0], marker='o', lw=0, color='#1765aa', label='Negative control')]
    fig.legend(handles=legend, loc='lower center', ncol=4, frameon=False, fontsize=9, bbox_to_anchor=(.5, .027))
    fig.text(.5, .013, 'Sideband linear trend removed. Shading marks the fixed event; each panel has its own vertical scale.',
             ha='center', fontsize=9, color='#515963')
    fig.tight_layout(rect=(.025, .065, .995, .94), h_pad=2.0, w_pad=2.0)
    # Render fully in memory, then replace a closed file. This avoids exposing
    # partially written figures to filesystem snapshotting during long runs.
    for suffix in ('.png', '.pdf'):
        buffer = io.BytesIO()
        options = ({'dpi': 145, 'facecolor': 'white'} if suffix == '.png' else
                   {'metadata': {'CreationDate': None, 'ModDate': None}})
        fig.savefig(buffer, format=suffix[1:], **options)
        payload = buffer.getvalue()
        assert len(payload) > 1000
        temporary = path.with_suffix(suffix + '.tmp')
        with temporary.open('wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path.with_suffix(suffix))
    plt.close(fig)


def main():
    records = json.loads((OUT / 'diagnostics.json').read_text())
    audit = json.loads((OUT / 'audit.json').read_text())
    assert audit['status'] == 'PASS'
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.labelcolor': '#27364a',
                         'text.color': '#27364a', 'axes.edgecolor': '#c4cbd2'})
    fig, axes = plt.subplots(4, 4, figsize=(16, 12))
    for index, r in enumerate(records):
        row, group = divmod(index, 2)
        for col, field in enumerate(('FLUX', 'SMEARING_LC')):
            ax = axes[row, group * 2 + col]
            profile(ax, r, field, 1000.)
            ax.set_title(f'{label(r)} · {field}', loc='left', fontsize=10, fontweight='bold')
            if row == 3:
                ax.set_xlabel('Minutes from first event row', fontsize=9)
    finish(fig, OUT / 'flux_smearing_contexts', 'LS8C | Fixed brightness and smearing contexts')
    for r in records:
        fig, axes = plt.subplots(4, 4, figsize=(16, 12))
        for ax, name in zip(axes.flat, FIELDS):
            profile(ax, r, name)
            ax.set_xlabel('Minutes from first event row', fontsize=8)
        for ax in list(axes.flat)[len(FIELDS):]:
            ax.set_visible(False)
        stem = label(r).replace(' ', '_') + '_all_fields'
        finish(fig, OUT / stem, f'LS8C | {label(r)} · row {r["start"]} · {r["duration"]} event rows')
    with (OUT / 'couplings.csv').open('w') as f:
        fields = ['representative', 'field', 'status', 'beta_electron_per_unit', 'side_correlation',
                  'predicted_flux_mean_residual', 'remaining_flux_mean_residual',
                  'predicted_fraction_of_flux_residual']
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        for r in records:
            for name, c in r['couplings'].items():
                writer.writerow({'representative': label(r), 'field': name, **c})

    lines = ['# LS8C: all seven positive excursions coincide with a smearing feature', '',
        'Completed 19 September 2026 using only the four saved LS8B DEFAULT-L2 tables. '
        'The seven positive representatives each coincide with a large positive SMEARING_LC '
        'residual and have mean event roll angles between **16.39 and 20.42 degrees**. '
        'The negative representative has neither that smearing pattern nor that roll range. '
        'This repeated auxiliary pattern motivates a bounded image/correction study. '
        'It does not establish a correction operator, a unique physical cause or a SETI candidate.', '',
        f'The [diagnostic protocol](../LS8C_AUXILIARY_PROTOCOL.md), configuration, code and six '
        f'known-answer tests were published at [`{FREEZE[:7]}`](https://github.com/andersenmartin-blip/setisearch/commit/{FREEZE}) '
        'before these auxiliary calculations. This is a retrospective diagnosis of closed data. '
        'All eight original representatives, both signs and the original LS8B audit **FAIL** are preserved.', '',
        '## Complete event accounting', '',
        'P/N denotes the original positive/negative cluster label. All residuals are **mean per '
        'event row** after the frozen 12+12-sideband linear trend; they are not event-integrated '
        'sums. Native electron units do not establish common aperture/pixel normalization. '
        'MAD multiples describe displacement from local side behavior and are not significances.', '',
        '| Representative | Start / rows | FLUX residual (10³ e) | Smearing residual (10³ e) | Smearing / side MAD | Background residual (10³ e) | Mean event roll (°) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in records:
        s = r['series']
        lines.append(f'| {label(r)} | {r["start"]} / {r["duration"]} | {s["FLUX"]["mean_residual"]/1000:.3f} | '
                     f'{s["SMEARING_LC"]["mean_residual"]/1000:.3f} | {s["SMEARING_LC"]["mad_displacement"]:.2f} | '
                     f'{s["BACKGROUND"]["mean_residual"]/1000:.3f} | {s["ROLL_ANGLE"]["event_mean"]:.3f} |')
    lines += ['', '![All eight fixed flux and smearing contexts](flux_smearing_contexts.png)', '',
        '[Vector PDF](flux_smearing_contexts.pdf). Dark points are the sidebands used for the fit; '
        'open points are guards excluded from fitting; colored points and shading show the fixed '
        'event. The seven positive representatives have smearing residuals **205,662–293,495 e** '
        'against side MADs **344–459 e**, giving **527–766 local MAD units**. These large ratios '
        'reflect the selected event lying far outside its local sideband smearing behavior. '
        'They are not Gaussian tail probabilities and cannot be multiplied across events. '
        'The negative control is **−24,225 e / 47,409 e = −0.51 MAD units**.', '',
        'The positive event roll interval above is a description of all seven preselected '
        'representatives, not a newly fitted roll filter. Their background residuals are all '
        'negative (−11,926 to −19,141 e); dark and contamination residuals are also retained '
        'below. Repeated excursions at similar spacecraft orientation could share an '
        'instrumental origin; independence has not been established.', '',
        '## Remaining fields and intended/measured motion', '',
        '| Representative | Dark residual (e) | Contamination residual (10⁻⁶ ratio) | Roll residual (°) | Offset X (px) | Offset Y (px) | Offset-vector norm (px) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in records:
        s = r['series']
        lines.append(f'| {label(r)} | {s["DARK"]["mean_residual"]:.3f} | {s["CONTA_LC"]["mean_residual"]*1e6:.4f} | '
                     f'{s["ROLL_ANGLE"]["mean_residual"]:.3f} | {s["OFFSET_X"]["mean_residual"]:.5f} | '
                     f'{s["OFFSET_Y"]["mean_residual"]:.5f} | {r["centroid_offset_residual_norm_pixels"]:.5f} |')
    lines += ['', 'OFFSET is calculated centroid minus intended location. Intended locations are '
        'constant at (280, 828) pixels within every context, so measured-centroid and OFFSET '
        'residuals coincide here. The two intended-location fields, CONTA_LC_ERR and '
        'SMEARING_LC_ERR have zero side residual scatter in all eight contexts: their '
        '**32 MAD ratios are unavailable**, not set to zero. SMEARING_LC_ERR itself is zero '
        'throughout the retained contexts; this supplies no usable uncertainty for the '
        'large smearing excursions. All **112 field diagnoses** otherwise have finite inputs.', '',
        'The matching [SCI_COR_Lightcurve v13.1 schema](https://github.com/davefutyan/common_sw/blob/1e45b3be84edd18a60e9a0ea8ef65444dfa2a254/fits_data_model/resources/SCI_COR_Lightcurve.fsd) '
        'declares CONTA_LC and both contamination/smearing error columns as ratios. '
        'SMEARING_LC is in electrons. No electron-error conversion, contamination correction '
        'or re-addition to FLUX is made. The schema fixes column meaning but not the precise '
        'DRP correction/scaling operator. Centroid estimates can depend on brightness or '
        'image structure, so centroid association would not by itself show causation.', '',
        '## Sideband-only extrapolations do not provide a reliable correction', '',
        'Each cell is **sideband correlation / predicted fraction of observed FLUX residual** '
        'for one separate predeclared predictor. All 56 fits use sideband rows only after '
        'time detrending. A fraction is not explained variance; values may be negative or '
        'greater than one. No predictors are selected, combined or used to veto events.', '',
        '| Representative | Dark | Background | Contamination | Smearing | Roll | Offset X | Offset Y |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in records:
        cells = [f'{r["couplings"][k]["side_correlation"]:.3f} / '
                 f'{r["couplings"][k]["predicted_fraction_of_flux_residual"]:.3f}' for k in PREDICTORS]
        lines.append('| ' + label(r) + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', 'For the seven positive representatives, smearing extrapolations range from '
        '**−0.42 to 31.78 times** the observed brightness residual, while their sideband '
        'correlations range from **−0.009 to 0.405**. The sidebands sample smearing fluctuations '
        'hundreds of times smaller than the event departure; their local linear coupling '
        'cannot establish the correction at the event. The strongest original FLUX screen '
        '(TG000303 P0, score 12.3563) has a smearing extrapolation of 13.59 times its flux '
        'residual. It receives the same unresolved status as every other representative.', '',
        'For the negative control, smearing has side correlation 0.829 but predicts only '
        '0.052 of the negative flux residual. None of its seven separately evaluated '
        'predictors reproduces the observed mean drop (predicted fractions −0.0007 to '
        '0.219). This is a limited diagnostic result, not a calibrated rejection of '
        'instrumental explanations or a reason to promote the control.', '',
        '## Independent verification and retained limits', '',
        f'The independent big-endian `struct` / 60-decimal scalar audit passes '
        f'**{audit["comparisons"]["numeric"]:,} numerical comparisons and '
        f'{audit["comparisons"]["exact"]:,} exact checks**, with no disagreement. '
        'It checks identities, side/event rows, units, availability, every context value, '
        'trend, residual and diagnostic. The eight flux residual sums also agree with '
        'the saved LS8B Decimal reference. All six synthetic known-answer tests passed '
        'before evaluation. The new agreement tolerances were frozen in the LS8C protocol; '
        'the original LS8B failure and tolerances are unchanged.', '',
        '**Outcome for every representative: L2_ONLY_UNRESOLVED.** No automatic causal '
        'classification, statistical significance, detector qualification, artificial '
        'origin or qualified observing coverage is claimed. No new archive science bytes '
        'were obtained. LS7X/Y/Z branches remain closed; the raw-imagette gate remains '
        'NOT_READY and its technical request remains unsent.', '',
        '**Next substantive work:** specify one bounded CAL/COR image-and-correction study '
        'of all eight fixed representatives, including the negative control. First establish '
        'exact metadata identities and time joins, then freeze byte/row/pixel scope and '
        'stopping criteria before image access. Test whether the common smearing/roll '
        'signature corresponds to spatial correction structure rather than merely fitting '
        'another L2 nuisance curve. No image bytes are included in LS8C. '
        '[Continuation](../LS8C_CONTINUATION.md).', '',
        '## Reproduction and files', '',
        'From a fresh checkout at the frozen source commit, with the already tracked LS8B '
        'inputs, run:', '', '```sh',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m unittest discover -s tests -p test_ls8c_auxiliary.py -v',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/ls8c_auxiliary_diagnosis.py',
        'PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/ls8c_auxiliary_audit.py',
        '```', '',
        'The producer refuses an existing output directory. To reproduce plots, use the '
        'report script from the result commit on that fresh generated output. It only '
        'presents saved measurements. The retained original data are never rewritten.', '',
        '- [112 measurements](measurements.csv) and [56 complete couplings](couplings.csv).',
        '- [Full context diagnostics](diagnostics.json), [independent reference](decimal_reference.json), '
        '[audit](audit.json), [summary](summary.json).',
        '- [Input/source manifest](../config/ls8c_auxiliary.json), [preflight tests](../results_ls8c_preflight/tests.log), '
        '[checksums](SHA256SUMS).', '', 'All-field context plots, including constants and error columns:', '']
    for r in records:
        stem = label(r).replace(' ', '_') + '_all_fields'
        lines.append(f'- {label(r)}: [PNG]({stem}.png), [PDF]({stem}.pdf).')
    (OUT / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    (OUT / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
        for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    print('Saved report, complete CSV, nine PNG/PDF figures and checksums.')


if __name__ == '__main__':
    main()
