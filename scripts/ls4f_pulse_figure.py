#!/usr/bin/env python3
"""Plot every retained 1-ms pulse cluster for the LS4F 9.38-GHz event."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / 'results_ls4f_v2_reanalysis'
    data = {label: next(c for c in json.loads((folder / f'{label}_derived.json').read_text())['candidates']
                        if c['candidate_id'] == 'LS4B-A1-9380') for label in ['A1', 'B1']}
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none', 'svg.hashsalt': 'ls4f-pulse-figure'})
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5), sharex=True, sharey=True)
    for row, label in enumerate(['A1', 'B1']):
        for col, variant in enumerate(['original', 'corrected']):
            ax = axes[row, col]
            m = data[label]['variants'][variant]['residual_metrics']
            s = next(x for x in m['scales'] if x['requested_width_s'] == 0.001)
            start, stop = m['envelope_s']
            ax.axvspan(start, stop, color='#dceef6', zorder=0)
            for a, b in [(start-2, start), (stop, stop+2)]:
                ax.axvspan(a, b, color='#e8e8e8', zorder=0)
            for key, color in [('inside_pulses', '#006a92'), ('reference_pulses', '#666666')]:
                pulses = s[key]
                ax.scatter([p['peak_time_s'] for p in pulses], [p['peak_score'] for p in pulses],
                           s=28, c=color, edgecolors='white', linewidths=.4, zorder=3)
            ax.axhline(8, color='#a44335', ls='--', lw=.9)
            ax.set_xlim(0, m['sample_count'] * m['sample_time_s'])
            ax.set_ylim(bottom=0)
            ax.grid(axis='y', alpha=.18)
            channel_count = len(data[label]['variants'][variant]['indices'])
            ax.set_title(f'{label} {"ON" if row == 0 else "OFF"} · {variant.capitalize()} band ({channel_count} channels)', loc='left', fontsize=11)
            ax.text(.98, .94, f"Event: {len(s['inside_pulses'])}   Reference: {len(s['reference_pulses'])}",
                    transform=ax.transAxes, ha='right', va='top', fontsize=9,
                    bbox={'facecolor': 'white', 'alpha': .8, 'edgecolor': 'none'})
            if col == 0:
                ax.set_ylabel('Residual screening score')
            if row == 1:
                ax.set_xlabel('Seconds since start of each scan')
    fig.suptitle('LS4F: 9.38 GHz pulse clusters persist outside the event window', fontsize=15, x=.075, ha='left', y=.985)
    handles = [Line2D([], [], ls='', marker='o', color='#006a92', label='Event-window cluster'),
               Line2D([], [], ls='', marker='o', color='#666666', label='Reference cluster'),
               Patch(color='#dceef6', label='Frozen event window'),
               Line2D([], [], ls='--', color='#a44335', label='Threshold 8')]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .944), ncol=4, frameon=False, fontsize=9)
    fig.text(.075, .027, 'All retained clusters at requested 1 ms (effective 1.049 ms). Scores use each scan’s own baseline; they are not Gaussian sigma.\nA1 and B1 are sequential observations. Gray strips mark excluded 2 s guards. This is a derived-event plot, not a raw waveform.', fontsize=9, color='#444444')
    fig.subplots_adjust(left=.075, right=.98, top=.855, bottom=.13, hspace=.25, wspace=.08)
    fig.savefig(folder / 'pulse_clusters_9380.svg', metadata={'Date': None})
    fig.savefig('/workspace/scratch/b7b42867b305/ls4f-pulse-figure-preview.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    main()
