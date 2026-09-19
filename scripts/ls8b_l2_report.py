#!/usr/bin/env python3
"""Render audited LS8B ledgers without new fitting, selection, or data access."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8b_l2_suite'


def main():
    suite = json.loads((OUT / 'summary.json').read_text())
    audit = json.loads((OUT / 'audit.json').read_text())
    assert suite['status'] == 'COMPLETE_AUDITED' and audit['status'] == 'PASS'
    summaries = suite['visits']
    totals = {k: sum(s[k] for s in summaries) for k in [
        'rows', 'eligible_windows', 'positive_windows', 'negative_windows',
        'positive_clusters', 'negative_clusters', 'unique_event_rows', 'eligible_event_row_union_seconds']}
    lines = ['# LS8B: four held-out CHEOPS DEFAULT L2 visits', '',
             'Completed 19 September 2026. All four visits were fixed before metadata,',
             'and metadata/code identities were published before the first L2 table read.',
             'The LS7X/LS8A score and +/-8.5 thresholds are unchanged.', '',
             '| Visit | Cadence (s) | Rows | Eligible windows | Positive windows / clusters | Negative windows / clusters | Max score | Min score |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        lines.append(f'| {s["file_key"]} | {s["cadence_seconds"]:.6f} | {s["rows"]:,} | '
                     f'{s["eligible_windows"]:,} | {s["positive_windows"]} / {s["positive_clusters"]} | '
                     f'{s["negative_windows"]} / {s["negative_clusters"]} | '
                     f'{s["maximum_score"]:.6f} | {s["minimum_score"]:.6f} |'
                     if s['eligible_windows'] else f'| {s["file_key"]} | {s["cadence_seconds"]:.6f} | {s["rows"]} | 0 | 0 / 0 | 0 / 0 | unavailable | unavailable |')
    lines += ['', f'Descriptive totals: **{totals["eligible_windows"]:,} windows** in **{totals["rows"]:,} rows**; '
              f'**{totals["positive_windows"]} positive windows in {totals["positive_clusters"]} clusters**, '
              f'and **{totals["negative_windows"]} negative windows in {totals["negative_clusters"]} clusters**.', '',
              'Overlapping and adjacent windows are grouped within each visit; different visits',
              'are never joined. Negative clusters use the same predeclared rule after sign reversal.', '',
              '![Every eligible window in all four visits](score_timeseries.png)', '',
              '## Interpretation', '',
              'These are held-out tail-behavior measurements, not a qualified detection method.',
              'Positive excursions are L2 diagnostics, not identified astronomical or artificial signals.',
              'Negative crossings cannot be interpreted as negative light-sail pulses; they are controls',
              'for how strongly this screen responds to the actual processed time series.',
              'Neither the window counts nor cluster counts are independent noise-trial denominators.',
              'The local score is not a calibrated Gaussian significance or false-alarm probability.',
              'No raw imagette, CAL/COR image, other aperture or additional visit was inspected.',
              'No threshold or model was changed and no detector, candidate or qualified coverage is claimed.', '',
              '## Evidence and verification', '',
              f'- Evaluation freeze: `{suite["evaluation_freeze_commit"]}`.',
              '- [Fixed protocol](../LS8B_FOUR_VISIT_PROTOCOL.md) and [prior selection](../LS8B_FOUR_VISIT_SCOPE.md).',
              '- [Header-only metadata and exact file identities](../results_ls8b_l2_metadata/summary.json).',
              '- Each visit directory retains the original table bytes, acquisition receipt, every',
              '  eligible window, both signed cluster memberships, and per-duration summaries.',
              '- [All cluster representatives](cluster_representatives.csv); row starts are zero-based.',
              f'- Independent audit: **PASS**, {audit["numeric_and_discrete_window_comparisons"]:,} numerical/discrete',
              '  window comparisons, plus complete eligibility, signed clustering, count, union,',
              '  source-identity and summary checks. [Full audit](audit.json).',
              '- All 10 pre-acquisition known-answer and transport-boundary tests passed.',
              '- SHA256SUMS preserves every file in this result directory.', '']
    (OUT / 'REPORT.md').write_text('\n'.join(lines))
    (OUT / 'totals.json').write_text(json.dumps(totals, indent=2) + '\n')
    cluster_rows = []
    ledgers = []
    for s in summaries:
        directory = OUT / s['file_key']
        ledgers.append([json.loads(line) for line in gzip.decompress((directory / 'ledger.jsonl.gz').read_bytes()).splitlines()])
        clusters = json.loads((directory / 'clusters.json').read_text())
        for sign in ['positive', 'negative']:
            for group in clusters[sign]:
                r = group['representative']
                cluster_rows.append({'file_key': s['file_key'], 'sign': sign, 'cluster_id': group['cluster_id'],
                                     'start_row': r['start'], 'duration_rows': r['duration'],
                                     'duration_seconds': r['duration'] * s['cadence_seconds'], 'bjd_mid': r['bjd_mid'],
                                     'score': r['score'], 'event_or': r['event_or'],
                                     'context_event_or': r['context_event_or'], 'members': len(group['members'])})
    fields = ['file_key', 'sign', 'cluster_id', 'start_row', 'duration_rows', 'duration_seconds',
              'bjd_mid', 'score', 'event_or', 'context_event_or', 'members']
    with (OUT / 'cluster_representatives.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cluster_rows)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(4, 1, figsize=(11, 10), sharey=True, layout='constrained')
    maximum = max([8.5] + [abs(r['score']) for rows in ledgers for r in rows]) * 1.12
    colors = ['#2b6cb0', '#168577', '#bb741d']
    for ax, s, rows in zip(axes, summaries, ledgers):
        t0 = min((r['bjd_mid'] for r in rows), default=0)
        for duration, color in zip([1, 2, 3], colors):
            rr = [r for r in rows if r['duration'] == duration]
            ax.scatter([(r['bjd_mid']-t0)*24 for r in rr], [r['score'] for r in rr],
                       s=6, alpha=.55, color=color, label=f'{duration}-row window', rasterized=True)
        ax.axhline(0, color='#aab1bb', lw=.7)
        for threshold in [-8.5, 8.5]:
            ax.axhline(threshold, color='#b32932', ls='--', lw=1)
        ax.set_ylim(-maximum, maximum)
        ax.set_ylabel('Screen score')
        ax.set_xlabel('Hours from first eligible window in this visit')
        ax.set_title(f'{s["file_key"]}   |   +{s["positive_clusters"]} / -{s["negative_clusters"]} clusters',
                     loc='left', fontsize=10, weight='bold')
        ax.grid(axis='x', alpha=.15)
    axes[0].legend(loc='upper right', ncol=3, fontsize=8)
    fig.suptitle('LS8B: unchanged screen on four held-out 55 Cnc visits\n'
                 'Dashed lines: +/-8.5 screening threshold; scores are not Gaussian significance',
                 fontsize=13, weight='bold')
    fig.savefig(OUT / 'score_timeseries.png', dpi=170)
    fig.savefig(OUT / 'score_timeseries.pdf')
    plt.close(fig)
    (OUT / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n'
        for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
