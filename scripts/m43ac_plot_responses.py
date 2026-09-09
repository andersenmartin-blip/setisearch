"""Static scientific figures from the sealed M43AC numerical vectors."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from m43ac_dual_evidence import ROOT, OUT


def run():
    plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none', 'svg.hashsalt': 'm43ac'})
    summary = json.loads((OUT / 'response_summary.json').read_text())
    for p in summary['profiles']:
        if p['role'] != 'survivor':
            continue
        path = next(f['file'] for f in p['response_files'] if '.w129.' in f['file'])
        d = json.loads((ROOT / path).read_text())
        x = np.arange(-160, 161)
        fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, constrained_layout=True)
        for e in range(3):
            on, off = [np.asarray(d[k]['values'][e]) for k in ('on', 'off')]
            bon, boff = [np.asarray(d[k]['baseline_values'][e]) for k in ('on', 'off')]
            ax = axes[0, e]
            ax.plot(x, on, color='#136f9e', label='ON')
            ax.plot(x, off, color='#d05a21', label='OFF')
            ax.plot(x, bon, '--', color='#136f9e', alpha=.65, label='ON baseline')
            ax.plot(x, boff, '--', color='#d05a21', alpha=.65, label='OFF baseline')
            ax.axhline(5.5, color='#666666', lw=.8, ls=':')
            ax.set_title(f'Epoch {e+1}' + ('' if p['epochs'][e]['active'] else ' (inactive)'))
            ax = axes[1, e]
            ax.plot(x, on-bon, color='#136f9e', label='ON increment')
            ax.plot(x, off-boff, color='#d05a21', label='OFF increment')
            ax.set_xlabel('Proxy-bin offset from candidate')
            for row in range(2):
                ax = axes[row, e]
                ax.axvspan(-64, 64, color='#777777', alpha=.09)
                ax.axvline(0, color='#777777', lw=.6)
                ax.grid(alpha=.15)
        axes[0, 0].set_ylabel('Native-filtered track score')
        axes[1, 0].set_ylabel('Score minus baseline')
        h1, l1 = axes[0, 0].get_legend_handles_labels()
        h2, l2 = axes[1, 0].get_legend_handles_labels()
        fig.legend(h1+h2, l1+l2, loc='outside lower center', ncol=6, fontsize=9)
        fig.suptitle(f"{p['name']}: width 129, template {p['template_index']}, carrier {p['proxy_carrier_index']}\n"
                     'Retrospective reconstruction; shading marks the original correlation window')
        fig.savefig(OUT / f"{p['name']}-responses.svg", metadata={'Date': None})
        fig.savefig(ROOT.parent / f"m43ac-{p['name']}-preview.png", dpi=110)
        plt.close(fig)


if __name__ == '__main__':
    run()
