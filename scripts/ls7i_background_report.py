#!/usr/bin/env python3
"""Write the audited scientific result without adjusting its frozen model."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def write(path, lines):
    text = '\n'.join(lines) if isinstance(lines, list) else lines
    path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results_ls7i_background')
    parser.add_argument('--update-status', action='store_true')
    args = parser.parse_args(); out = args.output
    s = json.loads((out/'summary.json').read_text()); audit = json.loads((out/'AUDIT.json').read_text())
    assert audit['passed'] and audit['development_requirements_pass'] == s['development_requirements_pass']
    passed = s['development_requirements_pass']; verdict = 'PASS' if passed else 'FAIL'
    date = datetime.now(timezone.utc).date().isoformat()
    changes = [json.loads(x) for x in gzip.decompress((out/'changes.jsonl.gz').read_bytes()).splitlines()]
    signal_cells = [c for c in s['core_cells'] if c['signal']]
    failed_controls = [c for c in s['core_cells'] if not c['signal'] and not c['methods']['conditional']['pass']]
    total_failed_signals = sum(not c['methods']['conditional']['pass'] for c in signal_cells)
    native_pass = all(v['native']['pass'] for v in s['sectors'].values())
    if passed:
        meaning = ('Both sectors satisfy the frozen development and native-prediction requirements, and the independent audit passes. '
                   'This supports preparing a separately frozen qualification on unused data. It is not detector adoption or a false-alarm calibration.')
        next_step = ('Prepare one limited unused-sector qualification with eligibility, training boundaries, controls, stopping and candidate-review rules '
                     'fixed before inspecting its results. Verify that the proposed sector has not entered development. Keep this model and its outcomes unchanged.')
    else:
        meaning = ('The fixed model does not satisfy the joint two-sector requirements. The independent arithmetic audit passes. '
                   'This is a completed negative method result; no detector is adopted and no unused sector is opened.')
        next_step = ('Close this fixed ridge-prediction route. The next useful information would be an independently measured instrumental state: '
                     'time-resolved image motion/centroid indicators and pixel variations outside the target aperture, together with a response model '
                     'that preserves an injected stellar pulse. First establish whether those observables predict the remaining spatial contamination on '
                     'these same closed contexts. A separately specified auxiliary-observable study is a proposed next project direction, not a hidden '
                     'ridge, margin or template-bank retry. The present result alone does not establish that those extra observables will succeed.')
    short = (f'LS7I completed **7,080 digital cases** on the two closed sectors: **6,720 historical cases plus a separately declared 360-case '
             f'sector-32 shape supplement**. The primary rule fails **{total_failed_signals}/12 signal cells** and '
             f'**{len(failed_controls)}/60 control cells**. The joint development requirement is **{verdict}**; the independent audit passes.')
    if passed:
        short = short.replace('fails **0/12 signal cells** and **0/60 control cells**', 'passes all **12 signal cells** and **60 control cells**')
    # Scientific figure: exact measured fractions and native energy ratios.
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'ls7i-fixed-background-v1'})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.4), constrained_layout=True)
    for column, sector in enumerate([29, 32]):
        ax = axes[0, column]
        for kind, color, name in [('stellar', '#2563a6', 'Nominal'), ('off_profile', '#8653a2', 'Displaced')]:
            cells = sorted([c for c in signal_cells if c['sector'] == sector and c['kind'] == kind], key=lambda c: c['target_score'])
            for method, style in [('conditional', '-'), ('static', ':')]:
                values = [c['methods'][method]['count']/c['trials'] for c in cells]
                ax.plot(range(3), values, style, marker='o' if method == 'conditional' else '.', color=color,
                        label=name+(' predictor' if method == 'conditional' else ' static'), linewidth=2)
        ax.axhline(.9, color='#2563a6', linestyle='--', alpha=.45, linewidth=1)
        ax.axhline(.8, color='#8653a2', linestyle='--', alpha=.45, linewidth=1)
        ax.set(title=f'Sector {sector}: signal recovery', ylabel='Recovered fraction', ylim=(0, 1.04),
               xticks=range(3), xticklabels=['8.5', '12', '20'], xlabel='Frozen upstream target score')
        ax.grid(axis='y', alpha=.18); ax.legend(loc='lower right', fontsize=8)
        bg = s['sectors'][str(sector)]['native']['per_background']; ax = axes[1, column]
        ratios = [b['ratio'] for b in bg]
        ax.barh(range(10), ratios, color=['#3f8270' if v < 1 else '#b56b39' for v in ratios])
        ax.axvline(1, color='#555555', linewidth=1); ax.axvline(2, color='#ad3e3e', linestyle='--', linewidth=1)
        ax.set(title=f'Sector {sector}: native prediction stability', xlabel='Predictor / static residual energy',
               yticks=range(10), yticklabels=[f'{a:02d}' for a in range(10)], ylabel='Held-out background',
               xlim=(0, max(2.1, max(ratios)*1.1)))
        ax.invert_yaxis(); ax.grid(axis='x', alpha=.15)
    fig.suptitle('LS7I | Protected background prediction on closed TESS data', fontsize=16)
    fig.savefig(out/'comparison.png', dpi=170)
    fig.savefig(out/'comparison.svg', metadata={'Date': None})
    plt.close(fig)
    svg = out/'comparison.svg'; write(svg, svg.read_text())
    lines = ['# LS7I: protected background prediction — '+verdict, '', '**'+meaning+'**', '', short, '',
             'All cases reuse **twenty background contexts**. The model uses only the surrounding observable cadences; the pulse interval and '
             'five-cadence guards are protected. This adds no observing coverage, contains no blind native-candidate search, and does not measure '
             'physical laser sensitivity or an operational false-alarm rate.', '', '![Signal recovery and native prediction stability](comparison.png)', '',
             'Solid recovery curves show the primary predictor; dotted curves show the paired static ablation. The horizontal recovery requirements '
             'are 90% nominal and 80% displaced. Native bars compare both models using the same static covariance with a free uniform component projected '
             'out: values below one improve on static prediction; two is the maximum permitted for any single background.', '',
             '## Joint result by sector', '',
             '| Sector | Historical + supplement | Failed signal cells / 6 | Failed control cells / 30 | Trial gate | Native gate |',
             '|---|---:|---:|---:|---|---|']
    for sector, ss in s['sectors'].items():
        m = ss['methods']['conditional']
        lines.append(f'| {sector} | {ss["historical_trials"]:,} + {ss["supplement_trials"]} | {m["failed_signal_cells"]} | {m["failed_control_cells"]} | {"PASS" if m["trial_gate_pass"] else "FAIL"} | {"PASS" if ss["native"]["pass"] else "FAIL"} |')
    lines += ['', 'The same six signal and thirty control cells apply to each sector. The new sector-32 cross/ring/triangle rows remain labeled '
              '`sector32_shape_supplement`; they do not change the original 3,180-row archive denominator.', '',
              '## Signal recovery, including headroom', '',
              '| Sector | Signal | Target | Primary recovered | Required | Headroom | Static recovered |',
              '|---|---|---:|---:|---:|---:|---:|']
    for c in signal_cells:
        d = c['methods']['conditional']
        lines.append(f'| {c["sector"]} | {c["kind"]} | {c["target_score"]:g} | {d["count"]}/{c["trials"]} | {c["limit"]} | {d["headroom"]:+d} | {c["methods"]["static"]["count"]}/{c["trials"]} |')
    lines += ['', 'Headroom counts rows above the requirement; a negative value is a failed cell. The ledger also retains fixed-flux, '
              'doublet, inside/outside residual-stress, duration and displacement groups. None are silently removed from signal-loss accounting.', '',
              '## Every failed primary control cell', '',
              '| Sector | Cohort / suite | Control | Target | Accepted | Allowed | Static accepted |',
              '|---|---|---|---:|---:|---:|---:|']
    for c in failed_controls:
        lines.append(f'| {c["sector"]} | {c["cohort"]} / {c["suite"]} | {c["kind"]} | {c["target_score"]:g} | {c["methods"]["conditional"]["count"]}/{c["trials"]} | {c["limit"]} | {c["methods"]["static"]["count"]} |')
    if not failed_controls:
        lines.append('| — | — | None | — | — | — | — |')
    lines += ['', 'All 72 cells, their acceptance/recovery counts and all 720 per-background cell counts are in [summary.json](summary.json). '
              'Every row carries the temporal, source-score, residual and margin gates and the first-failure path.', '',
              '## Retained joint checks', '',
              '| Sector | Method | 10% single-pulse recovery / 60 (min 54) | Null accepted / 20 | Screened bounded pointing: accepted / screened | Confounded stellar rows | Other failed gates |',
              '|---|---|---:|---:|---:|---:|---|']
    for sector, ss in s['sectors'].items():
        for method, mm in ss['methods'].items():
            failed = ', '.join(k for k, ok in mm['gates'].items() if not ok and k != 'all_core_cells') or 'None'
            bp = mm['bounded_pointing']
            lines.append(f'| {sector} | {method} | {mm["bright_single"]["recovered"]}/60 | {mm["base_nulls"]["accepted"]}/20 | {bp["accepted"]}/{bp["screened"]} | {mm["confounded_signals"]}/{mm["all_signals"]["trials"]} | {failed} |')
    lines += ['', '## Is the surrounding information useful?', '',
              '| Sector | Native windows | Total energy ratio | Backgrounds improved / 10 | Worst background ratio | Native gate |',
              '|---|---:|---:|---:|---:|---|']
    for sector, ss in s['sectors'].items():
        n = ss['native']; bg = n['per_background']
        lines.append(f'| {sector} | 210 | {n["ratio"]:.6f} | {sum(r["ratio"] < 1 for r in bg)} | {max(r["ratio"] for r in bg):.6f} | {"PASS" if n["pass"] else "FAIL"} |')
    lines += ['', ('The fixed native prediction requirements pass on both closed sectors. This is evidence of useful surrounding information under '
                   'this metric; passing that metric alone does not establish that the spatial decision requirements pass.' if native_pass else
                   'The fixed native prediction requirements do not pass on both sectors. The table and per-background ratios locate the observed '
                   'benefit or instability. This limits the present cross-background ridge specification; it does not prove that all observable '
                   'background models are impossible.'), '',
              'Native starts were fixed in advance and each whole assessed background was excluded from global training and covariance calibration. '
              'These 420 windows still share contexts and overlapping sidebands. No binomial independence, observing-rate estimate or native event '
              'promotion is inferred from them.', '',
              '| Sector | Background | Conditional energy | Static energy | Ratio |', '|---|---:|---:|---:|---:|']
    for sector, ss in s['sectors'].items():
        for b in ss['native']['per_background']:
            lines.append(f'| {sector} | {b["anchor"]:02d} | {b["conditional"]:.6f} | {b["static"]:.6f} | {b["ratio"]:.6f} |')
    lines += ['', '## Full signal cost against the frozen references', '',
              '| Sector | Reference | Paired rows | Stellar recovered: reference → primary | Stellar losses | Stellar gains | Controls newly accepted | Controls newly rejected |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for c in s['comparisons']:
        lines.append(f'| {c["sector"]} | {c["reference"]} | {c["paired_trials"]:,} | {c["reference_recovered"]} → {c["conditional_recovered"]} | {c["stellar_losses"]} | {c["stellar_gains"]} | {c["controls_newly_accepted"]} | {c["controls_newly_rejected"]} |')
    lines += ['', '**Every lost stellar row** appears in [SIGNAL_LOSSES.md](SIGNAL_LOSSES.md). All changed row/reference pairs, including gains and '
              'control changes, appear in [changes.jsonl.gz](changes.jsonl.gz). A row can occur against more than one reference; those pair counts '
              'must not be presented as unique lost observations. Reference comparisons include all stellar fixed-flux and residual-stress rows. '
              'The new supplement has no historical reference; it enters the paired static comparison.', '',
              'The static ablation uses the same training mean, templates and cuts, with its own independently calibrated residual covariance. '
              'Thus the trial comparison evaluates prediction plus the corresponding error model. The native energy comparison deliberately '
              'holds the metric fixed to isolate predictive improvement. Historical references additionally differ in local scale, training and '
              'nuisance coverage, so the full change must not be attributed to a single coefficient.', '',
              '## Audit and inference boundary', '',
              f'- Eight synthetic known-answer tests pass. All **{audit["protected_trials"]:,}** trial additions are zero in the prediction/reference bands; feature, reference and scale protection are exact.',
              f'- **{audit["training_records"]}** observable training records, **{audit["regressions"]}** ridge regressions and **{audit["nested_folds"]}** nested outer folds were independently reconstructed. The ridge audit uses augmented least squares, not the predictor’s normal equations.',
              '- No training or calibration fit includes the assessed background. Inner covariance predictions additionally exclude the predicted sample’s entire background. Final fits use nine backgrounds; inner fits use eight.',
              f'- **{audit["direct_fits"]:,}** winning fits and **{audit["fit_alternatives"]:,}** alternatives were checked with independent whitened least squares / QR. All templates, decisions, 72 cells, 720 background/cell counts and complete changed-row accounting pass.',
              '- The sealed historical recipe, temporal and raw-FITS audit is reused by SHA-256. All 360 new supplement selections are independently enumerated. Historical upstream windows and screens stay fixed.',
              '- The inference API receives only observable outside-event features plus the event response for fitting. Injection truth is restricted to construction and preservation checks. No truth-removed event vector enters prediction.', '',
              'The empirical covariance, residual dof, negative nuisance margin and upstream score are descriptive engineering statistics. '
              'Reused contexts, training overlap, post-processed digital injections and the absence of new photon noise limit interpretation. '
              'A two-sector development result cannot establish an operational false-alarm probability or a physical transmitter limit.', '',
              '## Decision and next work', '', next_step, '',
              'The remaining plan work is consolidated in [the two-week result](../TWO_WEEK_REPORT_2026-09-14.md). The calendar dates were '
              'work estimates, not waiting periods; these computations ran during an explicitly started active session. No recurring job or '
              'unattended future analysis is implied.', '',
              f'Source freeze: `{s["freeze_commit"]}`. [Execution and audit](https://github.com/andersenmartin-blip/setisearch/actions/runs/{s["github_run_id"]}).', '',
              '- [Frozen protocol](../LS7I_BACKGROUND_PROTOCOL.md), [configuration](../config/ls7i_background.json), [source hashes](../LS7I_BACKGROUND_FREEZE.sha256)',
              '- [Verified inputs](../results_ls7i_inputs/REPORT.md), [training records](training.jsonl.gz), [regressions](regressions.jsonl.gz), [nested folds](folds.jsonl.gz)',
              '- [Complete trial ledger](trials.jsonl.gz), [spatial frames](frames.jsonl.gz), [native windows](native_windows.jsonl.gz)',
              '- [Separate supplement recipes](supplement_recipes.jsonl.gz), [supplement patterns](supplement_patterns.json), [summary](summary.json)',
              '- [Independent audit](AUDIT.json), [test log](TESTS.log), [execution log](RUN.log), [audit log](AUDIT.log), [output hashes](SHA256SUMS)',
              '- [Exportable vector figure](comparison.svg), [current status](../PROJECT_STATUS.md), [continuation](../LS7I_CONTINUATION.md)', '']
    write(out/'REPORT.md', lines)
    losses = ['# LS7I: every additional lost stellar row', '',
              'Each row was recovered by the named reference and is not recovered by the fixed conditional model. '
              'Rows can repeat across references. This includes matched, fixed-flux, doublet and sparse-stress stellar cases. '
              'See [the full report](REPORT.md) for paired denominators, gains and native prediction results.', '']
    for c in s['comparisons']:
        selected = [r for r in changes if r['sector'] == c['sector'] and r['reference'] == c['reference'] and r['change'] == 'stellar_losses']
        assert len(selected) == c['stellar_losses']
        losses += [f'## Sector {c["sector"]}, reference {c["reference"]}: {len(selected)} losses', '',
                   '| Case ID | Background | Suite | Signal / shape | Strength | Displacement | Residual | Primary failure |',
                   '|---|---:|---|---|---|---|---|---|']
        for r in selected:
            strength = f'target {r["target_score"]:g}' if r['target_score'] is not None else f'flux {r["amplitude_fraction"]:g}'
            d = r['residual']; residual = 'none' if d is None else f'{d["location"]}, {d["amplitude_e_per_s"]:+.6g} e-/s'
            losses.append(f'| `{r["case_id"]}` | {r["anchor"]:02d} | {r["suite"]} | {r["kind"]} / {r["shape"]} | {strength} | {r["shift_yx"]} | {residual} | {r["conditional"]["recovery_path"]} |')
        if not selected:
            losses.append('| None | — | — | — | — | — | — | — |')
        losses.append('')
    write(out/'SIGNAL_LOSSES.md', losses)
    if args.update_status:
        continuation = ['# LS7I continuation', '', f'Integrated model study completed {date}.', '', short, '', meaning, '',
                        '[Full result and figure](results_ls7i_background/REPORT.md), [every signal loss](results_ls7i_background/SIGNAL_LOSSES.md), '
                        '[independent audit](results_ls7i_background/AUDIT.json), [two-week result](TWO_WEEK_REPORT_2026-09-14.md).', '',
                        '## Next decision', '', next_step, '',
                        'The fixed protocol and all previous results remain closed. Do not rerun the model with changed parameters or open a new '
                        'sector as an implicit repair. All files needed to reproduce the completed result are already published; no new FITS download is required.', '',
                        '## Verify or resume review', '',
                        '```sh', 'sha256sum -c LS7I_BACKGROUND_FREEZE.sha256',
                        '(cd results_ls7i_background && sha256sum -c SHA256SUMS)',
                        'OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/ls7i_review_background.py', '```', '',
                        'A repeat audit writes AUDIT_RECHECK.json and preserves the sealed audit. Repeating the entire evaluation requires the '
                        'source freeze or a separate output directory; the runner refuses to overwrite existing results.', '',
                        f'Source freeze: `{s["freeze_commit"]}`. [GitHub execution](https://github.com/andersenmartin-blip/setisearch/actions/runs/{s["github_run_id"]}).', '',
                        'All M43 held-out panels remain untouched. No detector, candidate, physical laser limit or new observing coverage is claimed.', '']
        write(ROOT/'LS7I_CONTINUATION.md', continuation)
        status = (ROOT/'PROJECT_STATUS.md').read_text()
        begin = status.index('## LS7I input preparation completed')
        prefix = status[:begin].replace('Its dates are work windows; its scientific protocol remains to be frozen.',
                                        'Its dates are work windows. The joint model, evaluation and audit are now complete.')
        block = '\n'.join(['## LS7I joint background model completed: '+verdict, '', short, '', meaning, '', next_step, '',
                           '[Result and figure](results_ls7i_background/REPORT.md), [signal losses](results_ls7i_background/SIGNAL_LOSSES.md), '
                           '[continuation](LS7I_CONTINUATION.md), [two-week result](TWO_WEEK_REPORT_2026-09-14.md).', '', ''])
        write(ROOT/'PROJECT_STATUS.md', prefix+block+status[begin:])
        consolidation = ['# Result for the 14–27 September SETI work plan', '', f'Consolidated {date}; the planned work packages were executed early during active sessions.', '',
                         short, '', meaning, '',
                         '| Planned package | Completed evidence |', '|---|---|',
                         '| Restore both closed-sector inputs | All 6,720 historical recipes and 300 old training vectors reproduce exactly; independent raw sector-32 restoration passes. |',
                         '| Implement and freeze one background model | One protected ridge predictor, static ablation, eight synthetic tests and prospective source publication. |',
                         '| Joint evaluation | 7,080 cases: 6,720 original plus 360 separately labeled shape controls; 420 predeclared native windows. |',
                         f'| Independent audit and signal cost | 28,320 direct fits; {audit["fit_alternatives"]:,} alternatives; 72 core cells; every additional lost stellar row published. |',
                         '| Readiness decision | '+('Ready to prepare a separately specified unused-data qualification; no detector adoption.' if passed else 'Not ready for unused-data qualification. This model route closes as a negative result.')+' |',
                         '| Consolidation | Readable report, exportable figure, complete ledgers, provenance, logs and restart instructions. |', '',
                         '## What the evidence changes', '',
                         'LS7H showed that the known native contribution could change morphology decisions. LS7I tests an observable approximation '
                         'using nearby cadences, cross-background training and independent error calibration. Its measured benefit, failure cells '
                         'and signal costs are now explicit on both closed sectors. Neither exact truth subtraction nor a favorable aggregate '
                         'can substitute for passing every predeclared sector requirement.', '',
                         '| Sector | Native energy ratio | Failed signal cells / 6 | Failed control cells / 30 |', '|---|---:|---:|---:|']
        for sector, ss in s['sectors'].items():
            m = ss['methods']['conditional']
            consolidation.append(f'| {sector} | {ss["native"]["ratio"]:.6f} | {m["failed_signal_cells"]} | {m["failed_control_cells"]} |')
        consolidation += ['', '## Next project direction', '', next_step, '',
                          'The calendar plan did not authorize an endless sequence of outcome-driven adjustments. This result preserves that stopping '
                          'decision. Any later auxiliary-observable or unused-sector work needs its own scientific specification; the owner’s standing '
                          'authorization for ongoing implementation and publication remains in force. No additional publication approval is required.', '',
                          '## Scope and reproducibility', '',
                          'The trial rows and native checks reuse twenty background contexts; they do not add observing time. The two sectors were '
                          'already examined in development. No future job, reminder or recurring computation is scheduled by this report.', '',
                          '- [Complete integrated result](results_ls7i_background/REPORT.md)',
                          '- [Every additional lost stellar row](results_ls7i_background/SIGNAL_LOSSES.md)',
                          '- [Independent audit](results_ls7i_background/AUDIT.json)',
                          '- [Frozen model protocol](LS7I_BACKGROUND_PROTOCOL.md)',
                          '- [Verified input package](results_ls7i_inputs/REPORT.md)',
                          '- [Original two-week plan](TWO_WEEK_PLAN_2026-09-14.md)',
                          '- [Current continuation](LS7I_CONTINUATION.md)', '']
        write(ROOT/'TWO_WEEK_REPORT_2026-09-14.md', consolidation)
    manifest = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name not in ['SHA256SUMS', 'AUDIT_RECHECK.json']:
            manifest.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name)
    write(out/'SHA256SUMS', manifest)
    print(json.dumps({'audited': True, 'development_requirement': verdict, 'files_sealed': len(manifest),
                      'failed_signal_cells': total_failed_signals, 'failed_control_cells': len(failed_controls)}), flush=True)


if __name__ == '__main__':
    main()
