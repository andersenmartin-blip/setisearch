#!/usr/bin/env python3
"""Retrospective bookkeeping of the sealed LS7I result; no new fit or decision.

This completes the plan's limitation branch. It does not modify any frozen
source, model, cut, trial or result manifest.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'results_ls7i_background'


def records(name):
    return [json.loads(s) for s in gzip.decompress((BASE/name).read_bytes()).splitlines()]


def main():
    for line in (BASE/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        assert hashlib.sha256((BASE/name).read_bytes()).hexdigest() == digest
    summary = json.loads((BASE/'summary.json').read_text())
    assert summary['freeze_commit'] == '918797f2b33c1062a39c5360d2074700b075e17d'
    assert not summary['development_requirements_pass']
    trials, changes, folds = [records(name) for name in ['trials.jsonl.gz', 'changes.jsonl.gz', 'folds.jsonl.gz']]
    sectors = {}
    for sector in [29, 32]:
        signals = [r for r in trials if r['sector'] == sector and r['kind'] in ['stellar', 'off_profile']]
        paths = {m: dict(Counter(r['methods'][m]['decision']['recovery_path'] for r in signals)) for m in ['conditional', 'static']}
        losses = []
        for comparison in summary['comparisons']:
            if comparison['sector'] != sector:
                continue
            selected = [r for r in changes if r['sector'] == sector and r['reference'] == comparison['reference'] and r['change'] == 'stellar_losses']
            assert len(selected) == comparison['stellar_losses']
            losses.append({'reference': comparison['reference'], 'lost_rows': len(selected),
                           'first_failure': dict(Counter(r['conditional']['recovery_path'] for r in selected)),
                           'suites': dict(Counter(r['suite'] for r in selected))})
        ratios = [{'fold_id': f['fold_id'], 'ratio': float(np.trace(f['methods']['conditional']['covariance'])/
                   np.trace(f['methods']['static']['covariance']))} for f in folds if f['sector'] == sector]
        assert len(signals) == 1320 and len(ratios) == 30
        for method, counts in paths.items():
            assert sum(counts.values()) == 1320 and counts['recovered'] == summary['sectors'][str(sector)]['methods'][method]['all_signals']['recovered']
        sectors[str(sector)] = {'signal_rows': len(signals), 'all_signal_first_paths': paths, 'losses': losses,
            'covariance_trace_ratio': {'minimum': min(r['ratio'] for r in ratios), 'median': float(np.median([r['ratio'] for r in ratios])),
                                      'maximum': max(r['ratio'] for r in ratios), 'folds': ratios},
            'native_total_energy_ratio': summary['sectors'][str(sector)]['native']['ratio']}
    result = {'scope': 'retrospective descriptive bookkeeping of sealed outputs; no new evaluation or selection',
              'source_result_commit': '1cd89b896a46b666b9328a5db00c1720af341190',
              'source_freeze_commit': summary['freeze_commit'],
              'input_manifest_sha256': hashlib.sha256((BASE/'SHA256SUMS').read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'sectors': sectors}
    (ROOT/'LS7I_LIMITATIONS.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    text = ['# LS7I limitation analysis and completed plan decision', '',
            'This is a **retrospective reading of the sealed, audited result**, not another detector experiment. '
            'No additional data, fit, threshold, bank, training choice or observing sector is evaluated here. '
            'It completes the negative-result branch of the two-week plan.', '',
            'The one fixed model fails six of twelve signal cells and two of sixty instrumental cells. '
            'Its native prediction does not improve the aggregate common-metric residual energy on either sector. '
            'The correct decision is to close this ridge-prediction route and preserve the unused-data boundary.', '',
            '## The signal is protected, but the resulting decision is insufficient', '',
            'All 7,080 injected additions are exactly zero in the predictor/reference bands. The prediction, local scale and reference '
            'are invariant to the injected pulse and parent-local stress. This rules out direct fitting-away of the pulse through '
            'those features. It does not guarantee that the new uncertainty-weighted source score remains large enough to accept the pulse.', '',
            'The additional stellar losses are concentrated in the source-amplitude/noise requirement. The table uses the audited '
            'first-failure path: another gate can also fail, so this is an accounting attribution, not a unique causal decomposition.', '',
            '| Sector | Reference | Lost stellar rows | First failure: source score | First failure: nuisance margin | Base / stress rows |',
            '|---|---|---:|---:|---:|---:|']
    for sector, d in sectors.items():
        for loss in d['losses']:
            text.append(f'| {sector} | {loss["reference"]} | {loss["lost_rows"]} | {loss["first_failure"].get("source_score", 0)} | {loss["first_failure"].get("nuisance_margin", 0)} | {loss["suites"].get("base", 0)} / {loss["suites"].get("sparse_stress", 0)} |')
    text += ['', 'A row can appear against multiple references. In particular, these row/reference totals cannot be summed into a count '
             'of independent missed observations. Every individual loss remains listed in [SIGNAL_LOSSES.md](results_ls7i_background/SIGNAL_LOSSES.md).', '',
             '## Error calibration changes substantially across sectors', '',
             'The primary and static ablation use separate, nested held-background error covariances. The following trace ratio is computed '
             'from those already published covariance matrices, across all thirty anchor/width folds per sector.', '',
             '| Sector | Minimum covariance trace ratio | Median | Maximum | Native residual-energy ratio |',
             '|---|---:|---:|---:|---:|']
    for sector, d in sectors.items():
        c = d['covariance_trace_ratio']
        text.append(f'| {sector} | {c["minimum"]:.6f} | {c["median"]:.6f} | {c["maximum"]:.6f} | {d["native_total_energy_ratio"]:.6f} |')
    text += ['', 'Sector 32’s conditional calibration covariance is much broader in this summary than the static covariance, while the '
             'native prediction provides essentially no aggregate improvement. Thus both the prediction and its generalization error matter '
             'to the poor weak-signal result. A covariance trace includes all pixel directions, including components projected out during '
             'fitting; it does not by itself measure uncertainty along the stellar template or explain every lost row. No alternative '
             'covariance, stronger ridge penalty or changed score threshold is tried here.', '',
             'The native energy ratios are **1.008294** and **1.001058**: about 0.83% and 0.11% above static on the fixed windows. '
             'These are descriptive differences on reused contexts, without an independent significance claim. They fail the predeclared '
             'non-increase requirement, even though neither sector has a background exceeding the separate twofold stability ceiling.', '',
             '## Concrete next direction', '',
             'The next research question should be whether **additional observable instrumental information** predicts the confusing spatial '
             'component better than target-aperture sidebands alone. Existing 11×11 cutouts already contain pixels outside the target aperture, '
             'so their availability can be assessed on the same closed data. Archived image-motion or centroid indicators are another possible '
             'input; their availability and source identity must be checked before they are used.', '',
             'A useful bounded follow-on would first establish what those observables measure and whether they respond to a stellar pulse. '
             'A mission centroid must not be assumed independent of the target signal. Use pulse-protection checks and entire-background '
             'exclusions before any detector comparison. Keep any future model and evaluation separately specified, including the signal '
             'cost of instrumental corrections. This is a proposed next direction, not an assertion that such information will solve the problem.', '',
             'Do not open an unused sector, relax the current cuts or extend the current template bank as a repair. The current method remains '
             'unqualified, while the project retains a reproducible negative result and a more specific information requirement.', '',
             '## Reproduce this bookkeeping', '',
             '```sh', 'python scripts/ls7i_limitations.py', '```', '',
             'The script first verifies the sealed output hashes, checks its counts against the audited summary, and writes '
             '[LS7I_LIMITATIONS.json](LS7I_LIMITATIONS.json) with exact per-fold ratios and provenance. It never rewrites the sealed result directory.', '',
             '- [Complete joint result and figure](results_ls7i_background/REPORT.md)',
             '- [Independent numerical audit](results_ls7i_background/AUDIT.json)',
             '- [Two-week result](TWO_WEEK_REPORT_2026-09-14.md)',
             '- [Current continuation](LS7I_CONTINUATION.md)', '']
    (ROOT/'LS7I_LIMITATIONS.md').write_text('\n'.join(text))
    print(json.dumps({'sectors': sectors, 'unchanged_result_manifest': result['input_manifest_sha256']}, indent=2))


if __name__ == '__main__':
    main()
