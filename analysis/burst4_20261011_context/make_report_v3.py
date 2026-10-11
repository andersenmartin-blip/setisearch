"""Render the hash-bound, independently checked saved burst4 context outputs.

Reads JSON only. Does not decode HDF5/NPZ, rerun a detector, normalize,
refit, optimize, classify, or infer new frequency/observation coverage.
Presentation revision after completed saved-output QA. Original frozen source
is preserved. This version corrects QA list/dict admission and label contrast.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

BASE = 'analysis/burst4_20261011_context'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
LABELS = ('HIP98505 A1', 'HIP97319 B1', 'HIP98505 A2', 'HIP97461 B2', 'HIP98505 A3', 'HIP97663 B3')
TARGETS = ('HIP97319', 'HIP97461', 'HIP97663')
MATRIX_STATUS = 'COMPLETE_NINE_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
CONTEXT_QA_STATUS = 'PASS54_BURST4_CONTEXTS864_ROW_BOXES108_SCORES9_OWN_MATCHES288_SOURCE_ROWS'
PRIMARY_STATUS = 'COMPLETE_96_NEW_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
PRIMARY_QA_STATUS = 'PASS288_BURST4_MAPS1161_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def confined(root, name):
    path = (root / name).resolve()
    require(path.is_relative_to(root), 'Input/output path escapes project root')
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path, root):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def read_json(path):
    return json.loads(path.read_bytes())


def verify_pin(root, declaration, expected_path=None):
    path = confined(root, declaration['path'])
    require(expected_path is None or path == expected_path, 'QA pin binds a different input')
    require(path.suffix == '.json', 'Report verifies JSON inputs only')
    require(pin(path, root) == declaration, 'Completed QA binds different JSON bytes')
    return path


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def save_csv(path, records):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def fraction_text(value):
    return 'ikke defineret' if value is None else f'{value * 100:.2f}%'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report-sha256', required=True)
    parser.add_argument('--scope', default=BASE + '/context_scope.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--context-qa', default=BASE + '/CONTEXT_QA_RECEIPT.json')
    parser.add_argument('--context-qa-sha256')
    parser.add_argument('--primary-qa')
    parser.add_argument('--primary-qa-sha256')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps({'status': 'PASS_METADATA_ONLY_BURST4_REPORT_INTERFACE',
                          'matrix_status': MATRIX_STATUS, 'context_QA_status': CONTEXT_QA_STATUS,
                          'expected_primary_maps': 288, 'selected_tracks': 9, 'contexts': 54,
                          'JSON_only': True, 'numerical_execution': False}))
        return
    require(all((args.scope_sha256, args.context_qa_sha256, args.primary_qa,
                 args.primary_qa_sha256)), 'Exact scope and completed primary/context QA hashes required')
    root = args.root.resolve()
    require(digest(Path(__file__).resolve()) == args.report_sha256, 'Exact separate presentation source SHA required')
    scope_path = confined(root, args.scope)
    context_qa_path = confined(root, args.context_qa)
    primary_qa_path = confined(root, args.primary_qa)
    for path, expected in ((scope_path, args.scope_sha256),
                           (context_qa_path, args.context_qa_sha256),
                           (primary_qa_path, args.primary_qa_sha256)):
        require(path.suffix == '.json' and digest(path) == expected,
                'Exact JSON input hash differs before report admission')
    scope = read_json(scope_path)
    context_qa, primary_qa = read_json(context_qa_path), read_json(primary_qa_path)
    require(digest(root / BASE / 'make_report.py') == scope['report_code_sha256'],
            'Report source differs from public frozen context scope')
    context_qa_code_path = confined(root, context_qa['qa_code']['path'])
    require(pin(context_qa_code_path, root) == context_qa['qa_code'] and
            context_qa['qa_code']['sha256'] == scope['context_qa_code_sha256'],
            'Completed context QA code differs from frozen scope')
    require(context_qa['status'] == CONTEXT_QA_STATUS, 'Completed independent burst4 context QA required')
    require(primary_qa['status'] == PRIMARY_QA_STATUS and primary_qa['counts']['maps'] == 288,
            'Completed independent 288-map primary QA required')
    require(all(context_qa['counts'][key] == value for key, value in
                {'profiles': 54, 'row_box_sums': 864, 'four_row_scores': 54, 'full16_scores': 54,
                 'own_primary_score_matches': 9, 'source_decoded_rows': 288}.items()),
            'Context QA counts differ from the fixed family')
    stage = root / BASE / 'results'
    matrix_path, context_receipt_path = stage / 'CONTEXT_PROFILES.json', stage / 'EXECUTION_RECEIPT.json'
    verify_pin(root, context_qa['context_scope'], scope_path)
    verify_pin(root, context_qa['context_receipt'], context_receipt_path)
    verify_pin(root, context_qa['context_matrix'], matrix_path)
    matrix, context_receipt = read_json(matrix_path), read_json(context_receipt_path)
    require(matrix['status'] == MATRIX_STATUS and context_receipt['status'] == MATRIX_STATUS,
            'Exact completed burst4 context matrix and producer receipt required')
    require(context_receipt['context_scope_sha256'] == args.scope_sha256,
            'Completed context producer binds different scope')
    matrix_pin = pin(matrix_path, root)
    require(matrix_pin in context_receipt['output_pins'], 'Producer receipt does not bind saved matrix')
    primary_scope_path = confined(root, scope['producer_scope'])
    primary_driver_path = confined(root, scope['producer_driver'])
    require(primary_qa['primary_scope_sha256'] == digest(primary_scope_path) and
            primary_qa['primary_driver_sha256'] == digest(primary_driver_path),
            'Primary QA scope differs from fixed context provenance')
    primary_receipts, report_input_pins = [], [pin(path, root) for path in
        (scope_path, context_qa_path, primary_qa_path, matrix_path, context_receipt_path, primary_scope_path)]
    for directory in scope['primary_dirs']:
        path = confined(root, directory + '/EXECUTION_RECEIPT.json')
        declaration = next(item for item in context_receipt['primary_receipt_pins']
                           if item['path'] == path.relative_to(root).as_posix())
        verify_pin(root, declaration, path)
        receipt = read_json(path)
        require(receipt['status'] == PRIMARY_STATUS and receipt['counts']['maps'] == 96,
                'Each original OFF primary must have a completed 96-map receipt')
        require(primary_qa['primary_receipt_sha256s'][receipt['primary_id']] == declaration['sha256'],
                'Primary independent QA binds a different execution receipt')
        primary_receipts.append(receipt)
        report_input_pins.append(declaration)
    require(len(primary_receipts) == 3 and sum(r['counts']['maps'] for r in primary_receipts) == 288,
            'Exactly three completed original OFF primary families required')
    maps = sum(receipt['counts']['maps'] for receipt in primary_receipts)
    counts = {key: sum(receipt['counts'][key] for receipt in primary_receipts)
              for key in primary_receipts[0]['counts']
              if all(isinstance(receipt['counts'].get(key), int) for receipt in primary_receipts)}
    require(all(counts[key] == value for key, value in
                {'maps': 288, 'carrier_maximum_records': 1179648,
                 'valid_hypothesis_records': 2625896448, 'score_audit_queries': 1161}.items()),
            'Primary receipt totals differ from frozen burst4 coverage')
    require(primary_qa['counts']['carrier_maxima'] == counts['carrier_maximum_records'] and
            primary_qa['counts']['valid_hypothesis_records'] == counts['valid_hypothesis_records'] and
            primary_qa['counts']['score_audit_queries'] == counts['score_audit_queries'],
            'Primary QA counts do not reconcile to actual completed producer receipts')
    tracks, profiles = matrix['selected_tracks'], matrix['profiles']
    require(tracks == scope['selected_tracks'] and tracks == [track for directory in scope['primary_dirs'] for track in primary_qa['selected_top3'][Path(directory).name]] and
            len(tracks) == 9 and len(profiles) == 54,
            'Exactly nine frozen selected tracks and 54 fixed contexts required')
    groups, top_rows, context_rows = [], [], []
    for track in tracks:
        group = [next(profile for profile in profiles
                      if profile['selected_track'] == track and profile['context_scan_id'] == scan)
                 for scan in SCANS]
        groups.append(group)
        own = next(profile for profile in group if profile['context_scan_id'] == track['scan_id'])
        r0 = track['window_start_row']
        require(r0 in range(0, 13, 2) and track['window_length_rows'] == 4,
                'Selected track window differs from frozen four-row family')
        require(own['origin_primary_score'] == track['score'], 'Origin primary score identity differs')
        for profile in group:
            require(len(profile['row_midpoint_mjd']) == 16 and
                    len(profile['row_full16_score_contribution']) == 16 and
                    len(profile['row_four_row_score_contribution']) == 16,
                    'All 16 saved row times and contributions required')
            require(math.isfinite(profile['fixed_four_row_score']) and math.isfinite(profile['fixed_full16_score']),
                    'Saved context scores must be finite')
            context_rows.append({'target': track['primary_target'], 'rank': track['rank'],
                'scan_id': profile['context_scan_id'], 'context_target': profile['context_target'],
                'original_role': profile['original_acquisition_role'], 'selected_window_start_row': r0,
                'fixed_four_row_score': profile['fixed_four_row_score'],
                'fixed_full16_score': profile['fixed_full16_score'],
                'origin_primary_score': profile['origin_primary_score'],
                'origin_primary_score_difference': profile['origin_primary_score_difference']})
        top_rows.append({'target': track['primary_target'], 'rank': track['rank'],
            'native_chunk_index': track['native_chunk_index'], 'core_q': track['core_q'],
            'window_start_row': r0, 'window_source_rows': track['window_source_rows'],
            'frequency_MHz_at_window_reference': track['frequency_hz_at_window_reference'] / 1e6,
            'drift_hz_s': track['drift_hz_s'], 'width_channels': track['width_channels'],
            'primary_four_row_score': track['score'], 'own_fixed_full16_score': own['fixed_full16_score'],
            'four_row_largest_positive_contribution_fraction': own['positive_row_contribution_max_fraction'],
            'four_row_dominant_positive_source_row': own['dominant_positive_row'],
            'full16_largest_positive_contribution_fraction': own['full16_positive_row_contribution_max_fraction'],
            'full16_dominant_positive_source_row': own['full16_dominant_positive_row']})
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    from matplotlib.patches import Rectangle
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': '#f7f8fa'})
    out = root / BASE / 'delivery_v3'
    out.mkdir(exist_ok=False)
    save_csv(out / 'TOP9.csv', top_rows)
    save_csv(out / 'CONTEXT54.csv', context_rows)
    fig, axes = plt.subplots(2, 1, figsize=(13.5, 13), facecolor='#f7f8fa')
    ylabels = [f"{track['primary_target']} #{track['rank']} · r{track['window_start_row']}–{track['window_start_row'] + 3} · {track['frequency_hz_at_window_reference']/1e6:.6f} MHz"
               for track in tracks]
    for ax, key, title in zip(axes, ('fixed_four_row_score', 'fixed_full16_score'),
        ('Faste fire-rækkers scorer i hver kontekst · divisor √(4 × bredde)',
         'Faste fulde 16-rækkers scorer · divisor √(16 × bredde)')):
        values = np.array([[profile[key] for profile in group] for group in groups], dtype=float)
        limit = max(float(np.abs(values).max()), 1.)
        im = ax.imshow(values, cmap='RdBu_r', norm=SymLogNorm(linthresh=1., vmin=-limit, vmax=limit), aspect='auto')
        ax.set_xticks(range(6), LABELS, rotation=12)
        ax.set_yticks(range(9), ylabels)
        for i, track in enumerate(tracks):
            for j in range(6):
                rgb = im.cmap(im.norm(values[i, j]))[:3]
                luminance = sum(a * b for a, b in zip(rgb, (.2126, .7152, .0722)))
                color = 'white' if luminance < .45 else '#182430'
                ax.text(j, i, f'{values[i, j]:.3g}', ha='center', va='center', color=color, fontsize=10)
                if SCANS[j] == track['scan_id']:
                    ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                          linewidth=2.2, edgecolor='#e8a800'))
        ax.set_title(title, loc='left', fontsize=13, pad=12)
        fig.colorbar(im, ax=ax, pad=.02, label='Empirisk robust box-score · separat symmetrisk logskala')
    fig.suptitle('Ni OFF-valgte burst4-spor: fast projektion, seks scanninger og fire stjerneretninger', fontsize=15, y=.995)
    fig.text(.5, .006, 'Gul ramme: primærscanningen, som valgte sporet. Kun dens fire-rækkers score matcher primærscoren.', ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .025, 1, .98))
    fig.savefig(out / 'SETI_BURST4_CONTEXT54_2026-10-11.png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(14, 10), sharex=True)
    for i, (track, group, ax) in enumerate(zip(tracks, groups, axes.flat)):
        anchor = min(profile['row_midpoint_mjd'][0] for profile in group)
        r0 = track['window_start_row']
        for scan, profile in zip(SCANS, group):
            x = (np.array(profile['row_midpoint_mjd']) - anchor) * 1440
            y = np.array(profile['row_full16_score_contribution'])
            own = scan == track['scan_id']
            color = '#155ec4' if own else ('#536c83' if scan.endswith('_on') else '#cb5a32')
            ax.plot(x, y, '.-', color=color, linewidth=1.3 if own else .6,
                    markersize=4 if own else 2, alpha=1 if own else .6)
            ax.axvspan(x[r0], x[r0 + 3], color=color, alpha=.13 if own else .035)
            ax.scatter(x[r0:r0 + 4], y[r0:r0 + 4], facecolors='none', edgecolors=color,
                       s=30 if own else 12, linewidths=.8 if own else .4, zorder=3)
        ax.set_title(f"{track['primary_target']} #{track['rank']} · r{r0}–{r0+3} · {track['drift_hz_s']:+.4f} Hz/s", fontsize=10)
        ax.axhline(0, color='#9da7b0', linewidth=.5)
        ax.ticklabel_format(axis='y', style='sci', scilimits=(-3, 3))
        if i % 3 == 0:
            ax.set_ylabel('Rækkebidrag til fuld score')
        if i >= 6:
            ax.set_xlabel('Minutter fra første faktisk integrationsmidtpunkt')
    fig.suptitle('Alle 16 rækkebidrag med de fire valgte kilderækker fremhævet', fontsize=15, y=.995)
    fig.text(.5, .007, 'Blå: primærscanning. Grå: HIP98505. Orange: andre OFF-retninger. Segmenter og faktiske pauser bevares.', ha='center', fontsize=10)
    fig.tight_layout(rect=(0, .025, 1, .97))
    fig.savefig(out / 'SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    text = ['# SETI: fire-rækkers søgning i gemte radiospektre, 11. oktober 2026', '',
        f'Det stærkeste valgte spor har en empirisk fire-rækkers score på {max(t["score"] for t in tracks):.6f}. Tallet er ikke et sigma-niveau; denne søgning etablerer intet kvalificeret SETI-fund.', '',
        f'**{maps} kombinerede søgekort er færdige og uafhængigt kontrolleret.** Tre oprindelige OFF-scanninger har hver 96 faste referencefelter: native udsnit 170, 171 og 172 med q = 4 + 8k, k = 0–31. Søgefamilien har syv overlappende fire-rækkers vinduer med første kilderække 0, 2, 4, 6, 8, 10 eller 12, 159 lineære drifthastigheder fra −4 til +4 Hz/s og bredde 1 eller 3 kanaler. Forbehandlingen bruger alle 16 rækker.', '',
        'De tre højest rangerede spor pr. OFF-scanning er efter søgningen udvalgt på tværs af dens 96 felter. De ni spor er derefter projiceret uændret i alle seks scanninger med faktiske starttider og pauser. Denne analyse af kortvarige spor giver ingen ny frekvensdækning og ingen ny observation.', '',
        'Hvert vindue dækker 73,014444032 sekunders fysisk eksponering; første til sidste integrationsmidtpunkt er adskilt med 54,760833024 sekunder. Et spors frekvensreference er dets eget valgte vindues første integrationsmidtpunkt. Spor med forskellige første rækker har derfor forskellige referenceøjeblikke, selv inden for samme scanning.', '',
        'Der er **intet etableret kvalificeret SETI-fund**. Scorerne er empiriske robuste box-scorer, uden kalibreret SNR, falskalarmrate, flux, EIRP eller følsomhed.', '',
        '| Stjerne | Rang | Native / q | Kilderækker | Frekvens ved vinduets reference (MHz) | Drift (Hz/s) | Bredde | Primær fire-rækkers score | Egen fuld 16-rækkers score |',
        '|---|---:|---|---|---:|---:|---:|---:|---:|']
    for row in top_rows:
        text.append(f"| {row['target']} | {row['rank']} | {row['native_chunk_index']} / {row['core_q']} | {row['window_start_row']}–{row['window_start_row']+3} | {row['frequency_MHz_at_window_reference']:.9f} | {row['drift_hz_s']:+.6f} | {row['width_channels']} | {row['primary_four_row_score']:.6g} | {row['own_fixed_full16_score']:.6g} |")
    text.extend(['', 'Kontekstens fire-rækkers score bruger de samme fire rækkeindeks i hver scanning og divisor √(4 × bredde). Den separate fulde score bruger alle 16 rækker og divisor √(16 × bredde). Kun primærscanningens egen fire-rækkers score sammenholdes med den oprindelige primærscore. De to scorer er forskellige størrelser; en forlængelse over 16 rækker er ingen ny tilpasning.', '',
        '| Stjerne / rang | Største rækkes andel af positive fire-rækkers bidrag | Dominerende kilderække | Største rækkes andel af positive fulde bidrag | Dominerende fulde kilderække |',
        '|---|---:|---:|---:|---:|'])
    for row in top_rows:
        text.append(f"| {row['target']} / {row['rank']} | {fraction_text(row['four_row_largest_positive_contribution_fraction'])} | {row['four_row_dominant_positive_source_row'] if row['four_row_dominant_positive_source_row'] is not None else '—'} | {fraction_text(row['full16_largest_positive_contribution_fraction'])} | {row['full16_dominant_positive_source_row'] if row['full16_dominant_positive_source_row'] is not None else '—'} |")
    text.extend(['', 'Andelene og rækkenumrene er gemte beskrivelser af de positive bidrag, betinget af sporvalget. Uden positive bidrag er andelen og den dominerende række ikke defineret. Der bruges ingen signalafhængig grænse eller efterfølgende optimering i rapporten.', '',
        'Driftgridet er tilpasset fire-rækkers vinduer. Uændret forlængelse gennem hele besøget og lave scorer i andre scanninger udelukker hverken nærliggende struktur eller andre oprindelser til kontekstens svar. Ingen OFF-veto eller klassifikation er anvendt.', '',
        'De seks scanninger peger i fire forskellige stjerneretninger: HIP98505 i tre ON-scanninger og HIP97319, HIP97461 samt HIP97663 én gang hver i de oprindelige OFF-scanninger. Alle er fra besøget 28. april 2017. Der er ingen uafhængig genobservation af en OFF-primærstjerne, og udvælgelsen er ikke blind validering. Hypoteser, overlappende vinduer og udvalgte spor er afhængige.', '',
        'Rapporten læser kun de hashbundne JSON-resultater efter bestået primær- og kontekstkontrol. De gemte 54 profiler har alle 16 række-tider og bidrag. Kontrollen rekonstruerer lokale 501-kanals medianer og rækkesummer samt kernernes rå medianer; den er betinget af gemte fuldkerne-MAD/skaler og winsoriserede lokationer, som ikke er uafhængigt fuldt refiltreret. Rapporten genkører ingen søgning, normalisering, profilberegning eller kildecellekontrol. A/B forbliver FAIL_CLOSED; gamle holdouts og beskyttede udsnit forbliver lukkede.', '',
        '![Fire-rækkers og fulde scorer i seks scanninger](SETI_BURST4_CONTEXT54_2026-10-11.png)', '',
        '![Alle rækkebidrag med valgte vinduer](SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png)', ''])
    report_path = out / 'SETI_BURST4_FINAL_2026-10-11.md'
    report_path.write_text('\n'.join(text))
    summary = {'status': 'COMPLETE_QA_GATED_SAVED_BURST4_REPORT', 'primary_counts': counts,
        'selected_tracks': 9, 'fixed_context_profiles': 54, 'separate_saved_context_scores': 108,
        'origin_four_row_scores_verified_by_QA': 9, 'top9': top_rows,
        'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
        'new_frequency_coverage': False, 'new_observation': False, 'blind_validation': False,
        'report_input_pins': report_input_pins}
    save_json(out / 'SUMMARY.json', summary)
    for declaration in report_input_pins:
        verify_pin(root, declaration)
    require(primary_qa['primary_driver_sha256'] == digest(primary_driver_path),
            'Primary driver changed while rendering report')
    require(scope['report_code_sha256'] == digest(root / BASE / 'make_report.py') and digest(Path(__file__).resolve()) == args.report_sha256 and
            scope['context_qa_code_sha256'] == digest(context_qa_code_path),
            'Frozen report or QA code changed while rendering')
    save_json(out / 'REPORT_RECEIPT.json', {'status': 'COMPLETE_QA_GATED_SAVED_BURST4_REPORT_AND_TWO_FIGURES',
        'report_code_sha256': digest(Path(__file__)), 'original_frozen_report_code_sha256': scope['report_code_sha256'],
        'presentation_revision_after_saved_values_exposure': True,
        'presentation_revision_reason': 'Preserve v2; shorten long repeated row y labels in separate delivery_v3; scientific outputs unchanged',
        'input_pins': report_input_pins,
        'primary_driver_pin': pin(primary_driver_path, root),
        'context_qa_code_pin': pin(context_qa_code_path, root),
        'output_pins': [pin(path, root) for path in sorted(out.iterdir()) if path.is_file()],
        'HDF5_or_NPZ_decoded': False, 'numerical_search_rerun': False,
        'profile_or_normalization_recomputed': False, 'original_execution_statuses_changed': False})
    print(json.dumps({'status': 'COMPLETE_QA_GATED_SAVED_BURST4_REPORT_AND_TWO_FIGURES',
                      'output': str(out), 'primary_maps': maps, 'fixed_context_profiles': 54}))


if __name__ == '__main__':
    main()
