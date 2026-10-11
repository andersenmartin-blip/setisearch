"""Build a concise Danish result report and scientific context figures.

Reads completed saved results only. No telescope access, fitting or detector
search. All stated numbers come from the pinned producer and fixed contexts.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

BASE = 'analysis/off_adjacent_20261011_context'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
LABELS = ('HIP98505 A1', 'HIP97319 B1', 'HIP98505 A2', 'HIP97461 B2', 'HIP98505 A3', 'HIP97663 B3')
TARGETS = ('HIP97319', 'HIP97461', 'HIP97663')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def require(test, message):
    if not test:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--scope', default=BASE + '/context_scope.json')
    args = p.parse_args()
    root = args.root.resolve()
    scope = read(root / args.scope)
    stage = root / BASE / 'results'
    matrix_path, receipt_path = stage / 'CONTEXT_PROFILES.json', stage / 'EXECUTION_RECEIPT.json'
    matrix, context_receipt = read(matrix_path), read(receipt_path)
    require(matrix['status'] == 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES' and
            context_receipt['context_scope_sha256'] == digest(root / args.scope), 'Completed exact fixed contexts required')
    records = context_receipt['output_pins']
    actual = next(pin for pin in records if pin['path'] == matrix_path.relative_to(root).as_posix())
    require(actual['sha256'] == digest(matrix_path) and actual['bytes'] == matrix_path.stat().st_size,
            'Completed context receipt does not bind exact saved matrix')
    for pin in scope['input_pins']:
        path = root / pin['path']
        require(pin['sha256'] == digest(path) and pin['bytes'] == path.stat().st_size,
                'Pinned primary producer/input changed before report')
    receipts = [read(root / directory / 'EXECUTION_RECEIPT.json') for directory in scope['primary_dirs']]
    require(all(rec['status'] == 'COMPLETE_512_NEW_ORIGINAL_OFF_MAPS_EXPLORATORY_ONLY' for rec in receipts),
            'Three completed512-map numerical receipts required')
    tracks, profiles = matrix['selected_tracks'], matrix['profiles']
    require(len(tracks) == 9 and len(profiles) == 54, 'Exactly9 fixed winners54 contexts required')
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'figure.facecolor': '#f7f8fa'})
    table, values = [], []
    for track in tracks:
        group = [next(p for p in profiles if p['selected_track'] == track and p['context_scan_id'] == scan)
                 for scan in SCANS]
        own = next(p for p in group if p['context_scan_id'] == track['scan_id'])
        require(abs(own['origin_primary_score_difference']) <= max(1e-7, abs(track['score']) * 1e-10),
                'Origin score reconciliation required')
        other = [p for p in group if p is not own]
        strongest_other = max(other, key=lambda p: p['fixed_robust_box_track_score'])
        values.append([p['fixed_robust_box_track_score'] for p in group])
        table.append({'target': track['primary_target'], 'rank': track['rank'],
                      'frequency_MHz_at_primary_first_midpoint': track['frequency_hz_at_own_first_midpoint'] / 1e6,
                      'drift_hz_s': track['drift_hz_s'], 'width_channels': track['width_channels'],
                      'primary_score': track['score'],
                      'largest_positive_row_fraction': own['positive_row_contribution_max_fraction'],
                      'dominant_positive_row': own['dominant_positive_row'],
                      'largest_other_fixed_context_score': strongest_other['fixed_robust_box_track_score'],
                      'largest_other_context_scan': strongest_other['context_scan_id'],
                      'origin_reference2300_box_overlap_rows': own['reference2300_line_box_overlap_rows']})
    out = root / BASE / 'delivery'
    out.mkdir(exist_ok=False)
    with (out / 'TOP9.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    rows = []
    for profile in profiles:
        rows.append({'target': profile['selected_track']['primary_target'], 'rank': profile['selected_track']['rank'],
                     'scan_id': profile['context_scan_id'], 'context_target': profile['context_target'],
                     'original_role': profile['original_acquisition_role'],
                     'fixed_score': profile['fixed_robust_box_track_score'],
                     'primary_score_difference': profile['origin_primary_score_difference']})
    with (out / 'CONTEXT54.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    maps = sum(rec['counts']['maps'] for rec in receipts)
    carriers = sum(rec['counts']['carrier_maximum_records'] for rec in receipts)
    hypotheses = sum(rec['counts']['valid_hypothesis_records'] for rec in receipts)
    audits = sum(rec['counts']['score_audit_queries'] for rec in receipts)
    require(maps == 1536 and carriers == 6291456 and hypotheses == 9877585920 and audits == 6153,
            'New numerical result counts differ from advertised full scope')
    array = np.array(values)
    limit = max(float(np.abs(array).max()), 1.)
    fig, ax = plt.subplots(figsize=(12, 6.2), facecolor='#f7f8fa')
    im = ax.imshow(array, cmap='RdBu_r', norm=SymLogNorm(linthresh=1., vmin=-limit, vmax=limit), aspect='auto')
    ax.set_xticks(range(6), LABELS, rotation=16)
    ax.set_yticks(range(9), [f"{t['primary_target']} #{t['rank']} · {t['frequency_hz_at_own_first_midpoint']/1e6:.6f} MHz" for t in tracks])
    for i, track in enumerate(tracks):
        for j in range(6):
            score = array[i, j]
            color = 'white' if abs(score) > limit * .003 else '#182430'
            ax.text(j, i, f'{score:.3g}', ha='center', va='center', color=color, fontsize=10)
            if SCANS[j] == track['scan_id']:
                from matplotlib.patches import Rectangle
                ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, linewidth=2.2, edgecolor='#f7be32'))
    ax.set_title('Ni faste OFF-valgte spor i seks oprindelige observationer', loc='left', pad=16, fontsize=15)
    ax.set_xlabel('Gul ramme: den observation, som valgte sporet. Farver har symmetrisk logskala.')
    fig.colorbar(im, ax=ax, pad=.025, label='Robust box-track score · ikke kalibreret SNR')
    fig.tight_layout()
    fig.savefig(out / 'SETI_CONTEXT54_2026-10-11.png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(13.5, 10), sharex=True)
    colors = ('#536c83', '#cb5a32', '#536c83', '#cb5a32', '#536c83', '#cb5a32')
    for i, (track, ax) in enumerate(zip(tracks, axes.flat)):
        group = [p for p in profiles if p['selected_track'] == track]
        anchor = min(p['row_midpoint_mjd'][0] for p in group)
        for scan, color in zip(SCANS, colors):
            profile = next(p for p in group if p['context_scan_id'] == scan)
            x = (np.array(profile['row_midpoint_mjd']) - anchor) * 1440
            y = np.array(profile['row_score_contribution'])
            own = scan == track['scan_id']
            ax.plot(x, y, '.-', color='#155ec4' if own else color, linewidth=1.3 if own else .6,
                    markersize=4 if own else 2, alpha=1 if own else .55)
        ax.set_title(f"{track['primary_target']} #{track['rank']} · drift {track['drift_hz_s']:+.4f} Hz/s", fontsize=10)
        ax.axhline(0, color='#9da7b0', linewidth=.5)
        ax.ticklabel_format(axis='y', style='sci', scilimits=(-3, 3))
        if i % 3 == 0:
            ax.set_ylabel('Bidrag til den faste score pr. tidsrække')
        if i >= 6:
            ax.set_xlabel('Minutter fra første faktisk integrationsmidtpunkt')
    fig.suptitle('Hvilke tidsrækker bærer scorene? Faktiske observationstider og pauser bevaret', fontsize=15, y=.995)
    fig.text(.5, .008, 'Blå: den valgte primærobservation. Grå: HIP98505. Orange: de andre OFF-retninger. Hvert segment er én observation.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .025, 1, .97))
    fig.savefig(out / 'SETI_ROW_CONTRIBUTIONS_2026-10-11.png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    overlap_tracks = sum(bool(row['origin_reference2300_box_overlap_rows']) for row in table)
    percentages = [row['largest_positive_row_fraction'] * 100 for row in table
                   if row['largest_positive_row_fraction'] is not None]
    cpu = sum(rec['process_CPU_seconds'] for rec in receipts)
    bandwidth_MHz = 512 * 4096 * abs(-2.7939677238464355) / 1e6
    text = [
        '# SETI: nye signalanalyser, 11. oktober 2026', '',
        f'**1536 nye spektralkort er færdige.** Der er undersøgt {carriers:,} nye referencefrekvenser fordelt på tre historiske stjerneobservationer: HIP97319, HIP97461 og HIP97663. Hver har fået {bandwidth_MHz:.6f} MHz ekstra frekvensdækning. De ni højest rangerede spor er kontrolleret ved uændrede frekvenser, drift og bredde i alle seks oprindelige observationer.', '',
        'Der er stadig **intet kvalificeret SETI-fund**. Tallene nedenfor viser stærke og svage svar i denne søgemetode; de er ikke kalibrerede SNR-værdier eller sandsynligheder for et astronomisk signal.', '',
        '| Stjerne | Rang | Frekvens ved første midtpunkt (MHz) | Drift (Hz/s) | Bredde (kanaler) | Primær score | Største tidsrækkes andel af positive bidrag |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in table:
        fraction = (f"{row['largest_positive_row_fraction']*100:.1f}%"
                    if row['largest_positive_row_fraction'] is not None else 'ikke defineret')
        text.append(f"| {row['target']} | {row['rank']} | {row['frequency_MHz_at_primary_first_midpoint']:.9f} | {row['drift_hz_s']:+.6f} | {row['width_channels']} | {row['primary_score']:.6g} | {fraction} |")
    fraction_description = (f'Den største enkelte tidsrække leverer {min(percentages):.1f}–{max(percentages):.1f}% af de positive bidrag i de primære spor med positive bidrag.'
                            if percentages else 'Ingen af de primære spor har positive tidsbidrag; deres andele er derfor ikke defineret.')
    text.extend([
        '', fraction_description + ' Det er en direkte beskrivelse af, hvor svaret kommer fra; andelen er ikke et mål for falsk-alarm-sandsynlighed. Ved ingen positive bidrag er andelen ikke defineret. De øvrige observationers svar fremgår af figuren og CONTEXT54.csv.', '',
        f'Alle ni primærscorer er reproduceret med samme faste 4096-kanals normalisering, 501-kanals medianfilter og 4000-kanals margin. Der er gemt 54 rå profiler med 16×503 kildeceller samt hvert tidsbidrag. De oprindelige float32-rækker er verificeret i alle 18 frekvensdele.', '',
        (f'{overlap_tracks} af de ni spor rammer den afrundede kildekanal ved den tidligere undersøgte linje på 2300,390625 MHz i mindst én primær tidsrække. Dette er kun et geometrisk overlap; det er ikke i sig selv en aliasforklaring.' if overlap_tracks else ''), '',
        f'Den fulde nye søgning omfatter {hypotheses:,} korrelerede kombinationer af frekvens, drift og bredde. Det er ikke så mange uafhængige forsøg. {audits:,} rå scorekontroller er gemt fra de nye kort; en separat kontrol kan rekonstruere deres valgte scorer uden at gentage søgningen.', '',
        'De tre primærstjerner har hver én historisk observation fra 28. april 2017. HIP98505-observationerne og de andre OFF-retninger giver sammenligningskontekst, men er ikke nye eller uafhængige genobservationer af primærstjernerne. Driftens trin er valgt til én 16-rækkers observation; den faste forlængelse gennem hele sekvensen er ikke en ny tilpasning.', '',
        '![Faste spor i de seks observationer](SETI_CONTEXT54_2026-10-11.png)', '',
        '![Scorernes tidsbidrag](SETI_ROW_CONTRIBUTIONS_2026-10-11.png)', '',
    ])
    (out / 'SETI_OFF_ADJACENT_2026-10-11.md').write_text('\n'.join(text).replace(f'{carriers:,}', f'{carriers:,}'.replace(',', '.')).replace(f'{hypotheses:,}', f'{hypotheses:,}'.replace(',', '.')).replace(f'{audits:,}', f'{audits:,}'.replace(',', '.')))
    summary = {'new_maps': maps, 'new_carrier_maxima': carriers, 'correlated_hypothesis_combinations': hypotheses,
               'raw_score_audits_saved': audits, 'fixed_context_profiles': 54,
               'origin_scores_reconciled': 9, 'extra_bandwidth_MHz_per_target': bandwidth_MHz,
               'primary_positive_row_max_fraction_range': [min(percentages)/100, max(percentages)/100] if percentages else None,
               'primary_positive_row_fraction_defined_count': len(percentages),
               'primary_tracks_overlapping_reference2300_box': overlap_tracks,
               'search_CPU_seconds_total': cpu, 'top9': table,
               'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
               'new_observation': False, 'report_source_context_sha256': digest(matrix_path),
               'report_source_scope_sha256': digest(root / args.scope)}
    save(out / 'SUMMARY.json', summary)
    save(out / 'REPORT_RECEIPT.json', {'status': 'COMPLETE_SAVED_RESULT_REPORT_AND_TWO_FIGURES',
          'report_code_sha256': digest(Path(__file__)), 'context_matrix_sha256': digest(matrix_path),
          'context_execution_receipt_sha256': digest(receipt_path),
          'output_pins': [{'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
                           'sha256': digest(path)} for path in sorted(out.iterdir()) if path.is_file()]})
    print(json.dumps({'status': 'COMPLETE_SAVED_RESULT_REPORT_AND_TWO_FIGURES', 'output': str(out),
                      'counts': {k: summary[k] for k in ('new_maps', 'new_carrier_maxima', 'fixed_context_profiles')}}))


if __name__ == '__main__':
    main()
