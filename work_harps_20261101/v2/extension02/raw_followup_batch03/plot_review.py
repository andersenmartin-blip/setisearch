"""Neutral, complete atlas: every selected record and all covering order cutouts.

No origin labels or automatic morphology classes. Each order has independent
raw-image scaling. The arrays, original counts and scaling recipe are retained.
"""
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent


def main():
    figures = OUT / 'figures'
    figures.mkdir(exist_ok=True)
    if (OUT / 'FIGURE_INDEX.json').exists() or list(figures.glob('REVIEW_*.png')):
        raise RuntimeError('Existing or partial review figures must not be silently replaced')
    mapping = json.loads((OUT / 'NATIVE_MAPPING.json').read_text())
    with (OUT / 'SELECTED_EVENTS.csv').open(newline='') as stream:
        events = list(csv.DictReader(stream))
    spectra = {record['dp_id']: record for record in mapping['spectra']}
    event_mapping = {record['review_id']: record for record in mapping['events']}
    index = []
    page_count = math.ceil(len(events) / 4)
    for start in range(0, len(events), 4):
        fig, axes = plt.subplots(4, 3, figsize=(16, 14.4), squeeze=False)
        fig.subplots_adjust(left=.055, right=.985, bottom=.055, top=.925, wspace=.24, hspace=.69)
        selected = events[start:start + 4]
        for row, event in enumerate(selected):
            related = [record for record in mapping['orders'] if record['review_id'] == event['review_id']]
            orders = [record for record in related if record['status'] == 'EXTRACTED']
            missing_orders = [record['order'] for record in related if record['status'] != 'EXTRACTED']
            ax, raw_ax, excess_ax = axes[row]
            images = {key: [] for key in ['raw_cutout', 'raw_excess']}
            centers, order_ticks, scales = [], [], []
            offset = 0
            for record in orders:
                with np.load(OUT / record['cutout'], allow_pickle=False) as array:
                    flux = array['native_flux']
                    side = float(np.median(flux[np.r_[0:8, 33:41]]))
                    normal = side if side > 0 else 1.
                    ax.plot(array['native_wave'] - record['topocentric_air_angstrom'], flux / normal,
                            '.-', lw=.8, ms=2.7, label='o' + str(record['order']) + (' / side' if side > 0 else ' ADU'))
                    raw = array['raw_cutout']
                    excess = array['raw_excess']
                    if raw.shape != (31, 33) or excess.shape != (31, 33):
                        raise RuntimeError('Unexpected cutout dimensions')
                    lower = float(np.percentile(raw, 5))
                    raw_scale = max(float(raw.max() - lower), 1.)
                    excess_scale = max(float(excess.max()), 1.)
                    images['raw_cutout'].extend([(raw - lower) / raw_scale, np.full((31, 3), np.nan)])
                    images['raw_excess'].extend([np.maximum(excess, 0) / excess_scale, np.full((31, 3), np.nan)])
                    centers.append(offset + 16 + record['raw_column'] - round(record['raw_column']))
                    order_ticks.append(offset + 16)
                    offset += 36
                    scales.append(dict(order=record['order'], raw_percentile5=lower, raw_scale=raw_scale,
                                       positive_excess_scale=excess_scale, native_side_median=side,
                                       native_normalization=normal))
            ax.axvline(0, color='red', ls=':', lw=.7)
            ax.axhline(1, color='gray', lw=.5)
            date = spectra[event['dp_id']].get('date_obs', '')[:10]
            wave_label = format(float(event['fitted_center_bary_air_angstrom']), '.4f')
            ax.set_title(event['review_id'] + '  ' + event['target'] + '  ' + date + '\n' + wave_label + ' Å barycentric air', fontsize=9)
            ax.set_xlabel('Native topocentric air offset (Å)', fontsize=8)
            ax.set_ylabel('Native flux / side median (ADU if side ≤ 0)', fontsize=8)
            ax.tick_params(labelsize=8)
            if orders:
                ax.legend(fontsize=7)
            else:
                ax.text(.5, .5, event_mapping[event['review_id']]['status'].replace('_', ' '),
                        transform=ax.transAxes, ha='center', va='center', fontsize=8, wrap=True)
            if missing_orders:
                ax.text(.01, .98, 'Missing full cutout: order ' + ', '.join(map(str, missing_orders)),
                        transform=ax.transAxes, va='top', color='crimson', fontsize=8)
            supported = bool(event_mapping[event['review_id']].get('mapping_supported', False))
            gate = 'global + five-window mapping supported' if supported else 'MAPPING INCOMPLETE'
            baseline = bool(event_mapping[event['review_id']].get('baseline_all_orders_mapping_verified', False))
            for plot, key, label in [(raw_ax, 'raw_cutout', 'Original raw counts'), (excess_ax, 'raw_excess', 'Positive raw excess')]:
                if images[key]:
                    plot.imshow(np.hstack(images[key][:-1]), origin='lower', aspect='auto', cmap='magma', vmin=0, vmax=1)
                    for center in centers:
                        plot.axvline(center, color='cyan', lw=.7)
                    plot.axhline(15, color='cyan', lw=.7)
                    plot.set_xticks(order_ticks, ['o' + str(record['order']) for record in orders], fontsize=8)
                else:
                    plot.set_xticks([])
                plot.set_title(label + '\n' + gate, fontsize=9, color='black' if supported else 'crimson')
                plot.set_yticks([0, 15, 30], [-15, 0, 15])
                plot.tick_params(labelsize=8)
                plot.set_xlabel('Independent order scales; cyan = predicted trace / row', fontsize=7)
                plot.set_ylabel('Dispersion-row offset', fontsize=8)
            index.append(dict(review_id=event['review_id'], detector=event['detector'], dp_id=event['dp_id'],
                              page=start // 4 + 1, row=row + 1, figure='figures/REVIEW_' + str(start // 4 + 1).zfill(2) + '.png',
                              covering_orders=[record['order'] for record in related], displayed_orders=[record['order'] for record in orders],
                              missing_full_cutout_orders=missing_orders, mapping_supported=supported,
                              baseline_all_orders_mapping_verified=baseline, display_scales=scales))
        for row in range(len(selected), 4):
            for ax in axes[row]:
                ax.set_visible(False)
        fig.suptitle('Extension02 raw/native batch03  ·  page ' + str(start // 4 + 1) + '/' + str(page_count)
                     + '  ·  frozen selected-event order\nAll extracted covering orders; 31×33 raw pixels; independent scales; no origin labels.', fontsize=12, y=.976)
        fig.savefig(figures / ('REVIEW_' + str(start // 4 + 1).zfill(2) + '.png'), dpi=110)
        plt.close(fig)
    if [entry['review_id'] for entry in index] != [event['review_id'] for event in events]:
        raise RuntimeError('Figure event coverage mismatch')
    (OUT / 'FIGURE_INDEX.json').write_text(json.dumps(index, indent=2, allow_nan=False) + '\n')
    print('pages', page_count, 'events', len(index))


if __name__ == '__main__':
    main()
