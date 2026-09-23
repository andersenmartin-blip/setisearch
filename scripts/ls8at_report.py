#!/usr/bin/env python3
"""Readable report and figure from retained LS8AT tables and audit, no network."""
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from ls8k_l2_audit import parse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls8at_l2_screen'


def main():
    s = json.loads((OUT/'summary.json').read_text())
    a = json.loads((OUT/'audit.json').read_text())
    meta = json.loads((ROOT/'results_ls8at_l2_metadata/summary.json').read_text())
    assert a['status']=='PASS', 'preserve any audit failure before report/promotion'
    t = s['totals']
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.2), sharex='col', layout='constrained')
    plt.rcParams.update({'font.size': 10})
    colors = ['#246aaf', '#238b71', '#8053a5']
    for column, visit in enumerate(s['visits']):
        folder = OUT/visit['file_key']
        data = parse((folder/'lightcurve_table.bin').read_bytes())
        valid = np.isfinite(data['bjd']) & np.isfinite(data['flux'])
        origin = float(data['bjd'][valid][0])
        hours = (data['bjd']-origin)*24
        ok = valid & (data['status']==0)
        scale = float(np.median(data['flux'][ok]))
        axes[0, column].scatter(hours[ok], data['flux'][ok]/scale, s=5, color='#334e68', alpha=.7, label='STATUS=0')
        bad = valid & ~ok
        if bad.any():
            axes[0, column].scatter(hours[bad], data['flux'][bad]/scale, s=8, color='#d38b30', alpha=.7, label='Flagged')
        axes[0, column].set_title(visit['file_key'].split('_')[2]+' · EC 14599-2047')
        axes[0, column].set_ylabel('DEFAULT flux / visit median')
        axes[0, column].legend(frameon=False, fontsize=8)
        rows = [json.loads(line) for line in gzip.decompress((folder/'ledger.jsonl.gz').read_bytes()).splitlines()]
        for duration, color in zip((1, 2, 3), colors):
            rr = [r for r in rows if r['duration']==duration]
            axes[1, column].scatter([(r['bjd_mid']-origin)*24 for r in rr], [r['score'] for r in rr],
                                    s=8, alpha=.6, color=color, label=f'{duration} row'+('s' if duration>1 else ''))
        for level in [-8.5, 8.5]:
            axes[1, column].axhline(level, color='#a53b3b', linestyle='--', linewidth=1)
        axes[1, column].set_ylim(min(-10, visit['minimum_score'] or 0)*1.1, max(10, visit['maximum_score'] or 0)*1.1)
        axes[1, column].set_ylabel('Screen score (not Gaussian sigma)')
        axes[1, column].set_xlabel('Hours since first retained BJD')
        axes[1, column].legend(frameon=False, fontsize=8)
        axes[1, column].set_title(f"{visit['eligible_windows']:,} windows · +{visit['positive_clusters']} / −{visit['negative_clusters']} clusters", fontsize=10)
    for ax in axes.flat:
        ax.grid(alpha=.16); ax.spines[['top','right']].set_visible(False)
    fig.suptitle('LS8AT · two prospectively selected CHEOPS visits', fontsize=15, fontweight='bold')
    fig.savefig(OUT/'ec145992047_screen.png', dpi=180)
    plt.close(fig)
    rows = []
    for v in s['visits']:
        rows.append(f"| {v['file_key']} | {v['rows']:,} | {v['eligible_windows']:,} | {v['positive_windows']} / {v['negative_windows']} | {v['positive_clusters']} / {v['negative_clusters']} |")
    representatives=[]
    for key in s['selected_keys']:
        clusters=json.loads((OUT/key/'clusters.json').read_text())
        for label in ['positive','negative']:
            for c in clusters[label]:
                r=c['representative']
                representatives.append(f"| {key} | {label} | {c['cluster_id']} | {r['start']} | {r['duration']} | {r['score']:.9f} |")
    if representatives:
        followup='Freeze one bounded CAL/COR metadata-and-image diagnostic for every positive and negative representative below. Establish exact exposure joins and byte ranges before image access. Do not select only the strongest positive event.'
        reps='\n## All fixed cluster representatives\n\n| Visit | Sign | Cluster | Start row (zero-based) | Duration (rows) | Score |\n|---|---|---:|---:|---:|---:|\n'+'\n'.join(representatives)+'\n'
    else:
        followup='Close this two-visit EC 14599-2047 screen as a descriptive null. The next independent cohort is rank 17 of the unchanged reconciled LS8J ledger, LS IV +09 2. Freeze its exact pair and header preflight before accessing that cohort. Do not widen or retune the closed EC 14599-2047 pair.'
        reps=''
    if a['status']!='PASS':
        followup='Stop scientific promotion: preserve the original audit failure and diagnose it on the retained tables before any further data acquisition.'
    text=f'''# LS8AT — EC 14599-2047 two-visit DEFAULT-L2 screen

Completed 23 September 2026. Result: **{s['status']}**.

The unchanged symmetric screen evaluated **{t['rows']:,} table rows** and
**{t['eligible_windows']:,} eligible, overlapping windows**. It retained
**{t['positive_clusters']} positive and {t['negative_clusters']} negative clusters**.
These are L2 screening outcomes, with no SETI-candidate or detector-qualification claim.

| Visit | Table rows | Eligible windows | Positive / negative windows | Positive / negative clusters |
|---|---:|---:|---:|---:|
'''+ '\n'.join(rows)+f'''

![Retained light curves and all eligible signed scores](ec145992047_screen.png)

The upper panels use visit-median normalization only for display. The screen
uses the unchanged local sideband baseline in electron units. Flagged rows are
shown for context and excluded according to the frozen rule. Gaps are not bridged.
A null, if obtained, refers only to eligible windows; edge rows or incomplete
contexts can contain changes that this fixed screen cannot test as events.

## Selection and fixed method

EC 14599-2047 was rank 16 of the metadata-only first-1,000-public-row CHEOPS census:
452 eligible visits and 107 cohorts with at least two eligible visits. It was
selected by the time of its second eligible visit, then first visit and archive
target name. It was not selected for known variability or SETI interest.
LS8J's original discarded full product responses remain a historical limitation;
the separately dated full-inventory reconciliation preserves fresh responses
and verifies unchanged summaries and complete cohort order before this screen.

The public header preflight recorded both exact products, their ETags and
schemas without reading table values. The science freeze is
`{s['evaluation_freeze_commit']}`. Both products have NEXP=1. Their verified
TEXPTIME values are {meta['products'][0]['keywords']['TEXPTIME']} and
{meta['products'][1]['keywords']['TEXPTIME']} seconds respectively. Durations
are one/two/three rows (60/120/180 seconds in both visits), with 12 sideband rows on each side, two-row guards
and endpoints +/-8.5. Each visit uses its own verified cadence.
Reserved TESS sectors remain unopened.
The flux-centered local-linear scorer and all eligibility/cluster rules remain
unchanged from LS8K; no thresholds are chosen from these outcomes.

Exactly **{t['science_table_bytes']:,} science-table bytes** were acquired.
The separately logged bounded URL-resolution timeout policy does not change
the table requests, source identities or scientific arithmetic.
Image bytes are zero; no alternative aperture, raw imagette or other
visit was opened.

## Independent verification and interpretation

Audit status: **{a['status']}**, with
**{a['numeric_and_discrete_comparisons']:,} numerical and discrete comparisons**
and **{len(a['numeric_disagreements'])} numerical disagreements**. It independently
decodes big-endian 138-byte rows, enumerates eligible windows, solves scalar
normal equations and checks both signed cluster sets and summary counts.
The unchanged tolerances are relative 2e-8 and absolute 2e-10.

Overlapping windows are not independent statistical trials. The score is not
a calibrated Gaussian significance or a false-alarm probability. This screen
does not establish completeness, sensitivity to short glints, population limits,
or additional qualified observing coverage. A threshold excursion requires
image-level assessment before physical interpretation.
'''+reps+'\n## Next action\n\n'+followup+'\n'
    (OUT/'REPORT.md').write_text(text)
    (OUT/'next_action.json').write_text(json.dumps({'audit_status':a['status'],
        'positive_clusters':t['positive_clusters'],'negative_clusters':t['negative_clusters'],
        'next_action':followup},indent=2)+'\n')
    (OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n'
        for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
    print(json.dumps({'status':s['status'],'report':str(OUT/'REPORT.md'), 'next_action':followup},indent=2))


if __name__ == '__main__': main()
