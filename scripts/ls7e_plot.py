#!/usr/bin/env python3
"""Plot paired LS7E development results, without independence/error-bar claims."""
import gzip
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/'results_ls7e_joint'
rows = [json.loads(r) for r in gzip.decompress((out/'trials.jsonl.gz').read_bytes()).splitlines()]
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'axes.titlesize': 12})
fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.8))
colors = {'original': '#525866', 'covariance_sparse': '#087e8b',
          'diagonal_sparse': '#c78623', 'covariance_plain': '#8f66b2'}
labels = {'original': 'Original LS7C', 'covariance_sparse': 'Covariance + sparse pixel',
          'diagonal_sparse': 'Diagonal + sparse pixel', 'covariance_plain': 'Covariance, no sparse pixel'}
scores = [8.5, 12., 20.]
for m in labels:
    values = []
    for score in scores:
        rs = [r for r in rows if r['suite'] == 'ls7c_replay' and r['kind'] == 'stellar' and r.get('target_score') == score]
        n = sum(r['original']['recovered'] if m == 'original' else r['methods'][m]['recovered'] for r in rs)
        values.append(100*n/len(rs))
    axes[0].plot(scores, values, marker='o', label=labels[m], color=colors[m], lw=2,
                 linestyle='--' if m == 'original' else '-')
axes[0].axhline(90, color='#aaaaaa', ls=':', lw=1)
axes[0].set(xlabel='Original temporal strength', ylabel='Nominal signals recovered (%)',
            xticks=scores, ylim=(-3, 105), title='Signal recovery · 40 trials per strength')
axes[0].legend(frameon=False, fontsize=8, loc='lower right')
categories = [('ls7c_replay', 'block_2x2'), ('extended', 'block3x3'),
              ('extended', 'row1x5'), ('extended', 'column5x1')]
x = np.arange(4)
for j, m in enumerate(list(labels)[1:]):
    values = []
    for suite, kind in categories:
        rs = [r for r in rows if r['suite'] == suite and r['kind'] == kind]
        values.append(100*sum(r['methods'][m]['accepted'] for r in rs)/len(rs))
    axes[1].bar(x+(j-1)*.24, values, width=.22, label=labels[m], color=colors[m])
axes[1].scatter([0], [100*16/120], color=colors['original'], marker='D', s=40, zorder=4)
axes[1].annotate('Original LS7C: 16/120', (0, 100*16/120), xytext=(.4, 16.5),
                 arrowprops={'arrowstyle': '-', 'color': colors['original']}, fontsize=8)
axes[1].set(xticks=x, xticklabels=['2×2 block', '3×3 block', '1×5 row', '5×1 column'],
            ylabel='Instrumental controls accepted (%)', ylim=(0, 20),
            title='Compact and extended controls · 120 per type')
for ax in axes:
    ax.grid(axis='y', alpha=.18)
    ax.set_axisbelow(True)
fig.suptitle('LS7E: substantial recovery gain, remaining weak-signal and extended-control failures', fontsize=13)
fig.text(.5, .018, 'Closed sector 32 · ten reused backgrounds · engineering development, no independent validation', ha='center', fontsize=9, color='#555555')
fig.tight_layout(rect=(0, .055, 1, .93))
fig.savefig(out/'joint_comparison.svg', metadata={'Date': None})
svg = out/'joint_comparison.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
fig.savefig(ROOT.parent/'ls7e_joint_preview.png', dpi=150)
