"""Describe the sealed training grid without refitting or selecting a model."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from m43e_economical_bank import read_sealed, write_sealed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43af_response'


def main():
    grid = read_sealed(OUT / 'training_grid.json.gz')
    decision = read_sealed(OUT / 'model_decision.json')
    assert grid['result_sha256'] == decision['training_grid_sha256']
    assert not decision['feasible'] and decision['boundary'] is None
    points = []
    for i, row in enumerate(grid['grid']):
        assert all(n.startswith('training') for n in row['leaking_control_or_baseline_cases'])
        points.append(dict(grid_index=i,
            required_signal_losses=len(row['required_signal_losses']),
            leaking_control_inputs=len(row['leaking_control_or_baseline_cases'])))
    assert len(points) == 1156 and len(grid['required_signal_cases']) == 57
    xs = [p['required_signal_losses'] for p in points]
    ys = [p['leaking_control_inputs'] for p in points]
    assert min(y for x, y in zip(xs, ys) if x == 0) == 8
    assert min(x for x, y in zip(xs, ys) if y == 0) == 4
    figure_dir = OUT / 'figures'
    figure_dir.mkdir(exist_ok=True)
    write_sealed(figure_dir / 'training_grid_plot_data.json', dict(
        source_training_grid_sha256=grid['result_sha256'], points=points,
        all_grid_rows_included=True, new_boundary_selected=False,
        baseline_and_null_members_always_zero=True))
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'svg.fonttype': 'none', 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.4))
    for ax in axes:
        ax.scatter(xs, ys, s=22, c='#477ba0', alpha=.23, edgecolors='none',
                   label='Frozen grid points (overlapping)', zorder=2)
        ax.grid(alpha=.18, color='#668090', zorder=0)
        ax.set_xlabel('Required signal cases lost /57', labelpad=9)
        ax.set_ylabel('Control inputs with surviving members /48', labelpad=9)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.tick_params(colors='#344c5c')
    axes[0].set(xlim=(-1, 59), ylim=(-.4, max(ys) + 1), title='All 1,156 grid evaluations')
    axes[1].set(xlim=(-.4, 7), ylim=(-.6, 12), title='Detail near the qualification target')
    axes[1].scatter([0], [0], s=80, marker='x', color='#a13532', linewidths=2, zorder=4)
    axes[1].annotate('Required target: (0, 0)\nNot attained', xy=(0, 0), xytext=(1.25, .8),
        color='#a13532', fontsize=10, arrowprops={'arrowstyle': '-', 'color': '#a13532'})
    axes[1].scatter([0, 4], [8, 0], s=80, facecolors='none', edgecolors='#193d57',
                    linewidths=1.5, zorder=4)
    axes[1].annotate('All 57 preserved:\nat least 8 leaking controls', xy=(0, 8), xytext=(1.9, 10.8),
        color='#193d57', fontsize=10, arrowprops={'arrowstyle': '-', 'color': '#193d57'})
    axes[1].annotate('Zero control leaks:\nat least 4 required losses', xy=(4, 0), xytext=(2.65, 5.9),
        color='#193d57', fontsize=10, arrowprops={'arrowstyle': '-', 'color': '#193d57'})
    fig.suptitle('M43AF training: the frozen grid has no qualifying boundary',
                 x=.07, y=.96, ha='left', fontsize=15, fontweight='bold', color='#193d57')
    fig.text(.07, .07, 'Same 241 recorded inputs at every grid point. Baseline and native nulls retain no eligible members.',
             fontsize=9, color='#465c68')
    fig.text(.07, .035, 'Descriptive summary of the published grid; no alternative boundary is adopted. Validation remains unopened.',
             fontsize=9, color='#465c68')
    fig.subplots_adjust(left=.075, right=.98, top=.83, bottom=.23, wspace=.3)
    fig.savefig(figure_dir / 'training_grid_tradeoff.svg', metadata={'Date': None})
    fig.savefig(ROOT.parent / 'artifacts/training_grid_tradeoff.png', dpi=160)
    plt.close(fig)
    print('All 1,156 sealed grid rows plotted; no scientific inputs or results changed.')


if __name__ == '__main__':
    main()
