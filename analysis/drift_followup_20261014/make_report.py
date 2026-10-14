"""Build the two-page Danish result report, only after producer and QA completion.

No spectral data or numerical producer modules are opened/imported. Values in
tables and the chart are read from authenticated result JSON. The root agent
must run the PDF artifact-operation marker immediately before invoking this.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value, places=2):
    require(isinstance(value, (int, float)) and math.isfinite(value), "Nonfinite display value")
    return f"{value:.{places}f}".replace(".", ",")


def short_origin(profile):
    return f"E{profile['origin_scan_id'][5]}-R{profile['origin_rank']}"


def target(profile):
    rows = [v for v in profile['offset_results'] if v['offset_channels'] == 0]
    require(len(rows) == 1, "Missing or duplicate zero-offset result")
    return rows[0]


def metric(profile, key):
    return target(profile)[key]['score']


def ranks(profile):
    data = profile['control_ranks']
    return (data['fixed_original4_rank_among_target_plus8'], data['max7_rank_among_target_plus8'])


def origin_order(profile):
    return (profile['origin_scan_id'], profile['origin_rank'])


def mjd_utc(value):
    return datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=value)


def prepare(args):
    scope = read(args.scope)
    results = read(args.profiles)
    injections = read(args.injections)
    qa = read(args.qa)
    receipt = read(args.receipt)
    source_path = args.source or (Path(scope['source_root']) / scope['matrix_path'])
    source = read(source_path)
    source_pins = [p for p in scope['input_pins'] if p['path'] == scope['matrix_path']]
    require(len(source_pins) == 1 and sha(source_path) == source_pins[0]['sha256'],
            'Source geometry table does not match frozen matrix pin')
    require(results['schema'] == 'SETI_LOCAL_DRIFT81_PHASE5_FOLLOWUP_V1', 'Unexpected profiles schema')
    require(injections['schema'] == 'SETI_RESIDUAL_DOMAIN_DELTA_BIN_INJECTION_TRANSPORT_V1', 'Unexpected injection schema')
    require(results['scope_sha256'] == sha(args.scope), 'Profiles do not match frozen scope')
    require(results['qualified_SETI_detection'] is False and results['calibrated_SNR_FAP'] is False,
            'Report interpretation differs from frozen scope')
    require(str(qa.get('status', '')).startswith('PASS'), 'Independent numerical QA must pass before report authoring')
    require(qa.get('scope_sha256') == results['scope_sha256']
            and qa.get('normalization_cores') == 54
            and qa.get('family_row_terms') == 3149280
            and qa.get('family_window_scores') == 1377810
            and qa.get('offset_summaries') == 486
            and qa.get('conditional_injections') == 3024
            and len(qa.get('profile_reports', [])) == 54,
            'Independent QA receipt must certify completed numerical result census')
    require(qa.get('producer_receipt_sha256') == sha(args.receipt), 'QA producer receipt pin differs')
    require(receipt.get('profiles') == 54 and receipt.get('injection_trials') == 3024
            and receipt.get('scope', {}).get('sha256') == results['scope_sha256'],
            'Execution receipt does not match complete frozen result')
    profiles = results['profiles']
    trials = injections['trials']
    require(len(profiles) == 54 and len(trials) == 3024 and injections['count'] == 3024,
            'Incomplete profile or injection census')
    by_id = {p['profile_id']: p for p in profiles}
    require(len(by_id) == 54 and set(by_id) == set(scope['profile_ids']), 'Profile identity census differs')
    originals = {p['profile_id']: p for p in source['profiles']}
    require(set(originals) == set(by_id), 'Source/result profile census differs')
    require(max(abs(p['baseline_difference']) for p in profiles) <= scope['normalization']['tolerance_abs'],
            'Original coarse scores were not reproduced')
    own = sorted([p for p in profiles if p['origin_scan_id'] == p['context_scan_id']], key=origin_order)
    require(len(own) == 9, 'Expected nine original ON selections')
    scans = ['epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off']
    counts = Counter(p['context_scan_id'] for p in profiles)
    require(all(counts[s] == 9 for s in scans), 'Each scan must have nine exact profile results')
    for p in profiles:
        require(metric(p, 'fine_fixed_original4') + 1e-7 >= p['original_fixed_four_row_score'],
                'Fine fixed-window maximum below its included baseline')
        require(metric(p, 'fine_max7') + 1e-7 >= metric(p, 'fine_fixed_original4'),
                'Seven-window maximum below fixed-window result')
        require(all(1 <= v <= 9 for v in ranks(p)), 'Invalid descriptive local rank')
    amplitudes = Counter(t['amplitude_per_active_standardized_single_bin'] for t in trials)
    require(amplitudes == {2: 1512, 8: 1512}, 'Expected 1,512 trials per diagnostic amplitude')
    return scope, results, injections, qa, receipt, profiles, trials, originals, own, scans


def make_heatmap(path, profiles, own, scans):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    lookup = {(p['origin_scan_id'], p['origin_rank'], p['context_scan_id']): p for p in profiles}
    grid = [[lookup[(o['origin_scan_id'], o['origin_rank'], s)] for s in scans] for o in own]
    values = np.asarray([[metric(p, 'fine_max7') for p in row] for row in grid])
    fig, ax = plt.subplots(figsize=(7.18, 3.65), dpi=220)
    image = ax.imshow(values, cmap='Blues', aspect='auto', vmin=0, vmax=max(8, float(values.max())))
    for ri, row in enumerate(grid):
        for ci, p in enumerate(row):
            color = 'white' if values[ri, ci] > image.norm.vmax * .60 else '#11273d'
            ax.text(ci, ri - .12,
                    fmt(metric(p, 'fine_fixed_original4')) + ' / ' + fmt(metric(p, 'fine_max7')),
                    ha='center', va='center', fontsize=7.55, color=color)
            r4, r7 = ranks(p)
            ax.text(ci, ri + .22, f'r {r4} / {r7}', ha='center', va='center', fontsize=6.75, color=color)
            if p['origin_scan_id'] == p['context_scan_id']:
                from matplotlib.patches import Rectangle
                ax.add_patch(Rectangle((ci - .49, ri - .49), .98, .98, fill=False, linewidth=1.6, edgecolor='#d57d18'))
    ax.set_xticks(range(6), ['E1 ON', 'E1 OFF', 'E2 ON', 'E2 OFF', 'E3 ON', 'E3 OFF'], fontsize=8.3)
    ax.xaxis.tick_top()
    ax.set_yticks(range(9), [short_origin(o) for o in own], fontsize=8.0)
    ax.set_xticks(np.arange(-.5, 6, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 9, 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=1.1)
    ax.tick_params(which='both', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cb = fig.colorbar(image, ax=ax, pad=.02, fraction=.022)
    cb.set_label('Score, all7', fontsize=7.2)
    cb.ax.tick_params(labelsize=7)
    fig.subplots_adjust(left=.085, right=.95, top=.94, bottom=.045)
    fig.savefig(path, dpi=220, facecolor='white')
    plt.close(fig)


def render(args, prepared):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, Table, TableStyle

    scope, results, injections, qa, receipt, profiles, trials, originals, own, scans = prepared
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.parent / 'tmp_report'
    tmp.mkdir(exist_ok=True)
    chart = tmp / 'scan_scores.png'
    make_heatmap(chart, profiles, own, scans)

    font_root = Path('/usr/share/fonts/truetype/dejavu')
    for name, file in [('Body', 'DejaVuSans.ttf'), ('Bold', 'DejaVuSans-Bold.ttf')]:
        require((font_root / file).exists(), 'Required readable Unicode font missing')
        pdfmetrics.registerFont(TTFont(name, str(font_root / file)))
    pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold')
    blue, dark, muted = colors.HexColor('#16334c'), colors.HexColor('#172738'), colors.HexColor('#506575')
    pale, line = colors.HexColor('#edf3f7'), colors.HexColor('#d5e0e8')
    W, H = A4
    left, width = 35, W - 70
    c = canvas.Canvas(str(args.output), pagesize=A4)
    c.setTitle('SETI - lokal driftkontrol - 14. oktober 2026')
    c.setAuthor('Martin Andersen / SETI Search')
    styles = {
        'body': ParagraphStyle('body', fontName='Body', fontSize=9.25, leading=13.2, textColor=dark),
        'small': ParagraphStyle('small', fontName='Body', fontSize=8.0, leading=11.0, textColor=muted),
        'head': ParagraphStyle('head', fontName='Bold', fontSize=11.2, leading=14, textColor=blue),
        'cell': ParagraphStyle('cell', fontName='Body', fontSize=7.6, leading=9.6, textColor=dark),
        'th': ParagraphStyle('th', fontName='Bold', fontSize=7.5, leading=9.3, textColor=colors.white),
    }

    def paragraph(text, y, kind='body', box_width=width, x=left):
        item = Paragraph(text, styles[kind])
        _, height = item.wrap(box_width, H)
        item.drawOn(c, x, y - height)
        return y - height

    def heading(text, y):
        return paragraph(text, y - 11, 'head') - 7

    def table(data, widths, y, row_heights=None, padding=5):
        rows = [[Paragraph(str(v), styles['th' if ri == 0 else 'cell']) for v in row] for ri, row in enumerate(data)]
        item = Table(rows, colWidths=widths, rowHeights=row_heights, repeatRows=1)
        item.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), blue),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, pale]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), padding), ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
            ('LINEBELOW', (0, 0), (-1, 0), .5, blue),
            ('LINEBELOW', (0, 1), (-1, -1), .25, line),
        ]))
        _, height = item.wrap(width, H)
        item.drawOn(c, left, y - height)
        return y - height

    def header(page, subtitle):
        c.setFillColor(blue)
        c.rect(0, H - 17, W, 17, fill=1, stroke=0)
        c.setFont('Bold', 19)
        c.drawString(left, H - 54, 'SETI | Lokal driftkontrol')
        c.setFont('Body', 9.1)
        c.setFillColor(muted)
        c.drawString(left, H - 72, '14. oktober 2026  ·  ' + subtitle)
        c.setStrokeColor(line)
        c.line(left, 43, W - left, 43)
        c.setFont('Body', 7.0)
        c.drawString(left, 29, '2017-data · 0 DKK · checkpoint 20. oktober 2026')
        c.drawRightString(W - left, 29, f'{page} / 2')
        c.setFont('Body', 6.4)
        c.drawString(left, 18, 'Frosset scope SHA256: ' + results['scope_sha256'][:24] + '…')
        c.setFillColor(dark)
        return H - 91

    y = header(1, 'Metodekontrol på ni allerede udvalgte ON-spor')
    y = paragraph('<b>Ingen kvalificeret SETI-detektion er etableret.</b> Denne kontrol undersøger, '
                  'hvor meget finere drift og frekvensfase ændrer de lokale scoremaksima. '
                  'Tre ON-scans og tre OFF-scans tilhører samme tidligere eksponerede besøg; '
                  'de er ikke uafhængige gentagelser.', y) - 7
    y = paragraph('Fast familie: <b>81 drifter × 5 faser = 405 kombinationer</b> omkring hvert oprindeligt '
                  'spor. Primær score fastholder de oprindelige fire rækker (fixed4); den sekundære '
                  'maksimerer over syv fire-rækkers vinduer (all7). Frekvensankeret er uændret, '
                  'og samme oprindelige normaliseringskerne genbruges.', y, 'small')
    y = heading('De ni oprindelige ON-udvalg', y)
    data = [['Udvalg', 'Gammel<br/>fixed4', 'Fin<br/>fixed4', 'Fin<br/>all7', 'Δdrift<br/>Hz/s', 'Fase<br/>kanal', 'all7<br/>række', 'Rang<br/>4 / 7']]
    for p in own:
        t = target(p)
        src = originals[p['profile_id']]
        win = t['fine_fixed_original4']
        r4, r7 = ranks(p)
        data.append([short_origin(p), fmt(p['original_fixed_four_row_score']), fmt(win['score']),
                     fmt(t['fine_max7']['score']), fmt(win['drift_hz_s'] - src['selected_track']['drift_hz_s'], 5),
                     fmt(win['phase_channels'], 2), str(t['fine_max7']['window_start_row']), f'{r4} / {r7}'])
    widths = [56, 62, 58, 58, 76, 60, 63, width - 433]
    y = table(data, widths, y)
    y = paragraph('Δdrift/fase viser første valgte alias ved scorelighed: identiske afrundede kanalspor '
                  'kan dele score. Tallene er ikke fysiske driftsestimater. Rækker starter ved 0. '
                  'Rang 1: ingen af otte lokale kontroller har strengt højere score; ligheder står i JSON.',
                  y - 7, 'small')
    y = heading('Samlet deskriptiv sammenligning', y)
    data = [['Profilgruppe', 'n', 'Median<br/>gammel', 'Median<br/>fin fixed4', 'Median<br/>fin all7', 'Rang 1<br/>fixed4 / all7']]
    categories = [('Oprindeligt ON-scan', lambda p: p['origin_scan_id'] == p['context_scan_id']),
                  ('Andre ON-scans', lambda p: p['context_scan_id'].endswith('_on') and p['origin_scan_id'] != p['context_scan_id']),
                  ('OFF-scans', lambda p: p['context_scan_id'].endswith('_off'))]
    for title, predicate in categories:
        group = [p for p in profiles if predicate(p)]
        data.append([title, len(group), fmt(statistics.median(p['original_fixed_four_row_score'] for p in group)),
                     fmt(statistics.median(metric(p, 'fine_fixed_original4') for p in group)),
                     fmt(statistics.median(metric(p, 'fine_max7') for p in group)),
                     f"{sum(ranks(p)[0] == 1 for p in group)} / {sum(ranks(p)[1] == 1 for p in group)}"])
    y = table(data, [143, 28, 74, 82, 80, width - 407], y)
    y = paragraph('De otte kontroller ligger ±256, ±512, ±768 og ±1.024 kanaler fra sporet. '
                  'Kontroller, vinduer og drift/fasehypoteser er korrelerede. Tabellens rangtal '
                  'er derfor <b>beskrivende, ikke falsk-alarm-sandsynligheder</b>. Lokal genmaksimering '
                  'i OFF giver ingen kvalificeret OFF-veto.', y - 8, 'small')
    y = heading('Kontrol og fortolkning', y)
    y = paragraph('Uafhængig numerisk QA: <b>PASS</b>. Alle 54 grove fixed4-scorer er reproduceret '
                  f"inden for tolerance; største absolutte afvigelse {max(abs(p['baseline_difference']) for p in profiles):.2g}. "
                  'Original A/B forbliver FAIL_CLOSED. Beskyttede 2016-kontroller og lukkede 2019-data '
                  'er uændrede. Detaljer, fulde vindertupler og ligheder findes i PROFILES.json, '
                  'INJECTIONS.json og QA_RECEIPT.json.', y, 'small')
    recovery = receipt['recovery']['measured_resource_usage']
    y = paragraph('Efter en JSON-formateringsfejl blev indsprøjtningstallene genskabt fra bevarede '
                  'familiearrays uden ny rådataanalyse. Genskabelse: '
                  f"{fmt(recovery['wall_s'])} s forløbet tid og {fmt(recovery['CPU_s'])} s CPU. "
                  'Der er ingen målt samlet CPU-/forløbet tid for første forsøg.', y - 7, 'small')
    y = paragraph('<b>Næste afgrænsede kontrol:</b> forklar de 19 geometrier med delvis binindfangning '
                  'under native kanalafrunding. Ingen justering af tærskler i de observerede data '
                  'er udført eller begrundet af denne test.', y - 7, 'small')
    require(y > 51, f'Page 1 content overflow: {y}')
    c.showPage()

    y = header(2, 'Alle 54 scan-profiler og 3.024 betingede indsprøjtninger')
    y = paragraph('<b>Hvert felt: fin fixed4 / fin all7; under linjen rang fixed4 / all7.</b> '
                  'Farven viser all7-score; orange kant markerer det oprindelige ON-scan. '
                  'Scoren er summen af fire standardiserede residualer divideret med 2, ikke kalibreret SNR.',
                  y, 'small') - 5
    chart_height = width * 3.65 / 7.18
    c.drawImage(str(chart), left, y - chart_height, width=width, height=chart_height, mask='auto')
    y -= chart_height + 1
    y = heading('Geometrien ved de bevarede tidspunkter', y)
    geo = [['Scan', 'Integrationsmidtpunkter<br/>UTC, 28.04.2017', 'Δt fra fast anker<br/>min / max, sek.', 'Største ændring<br/>fixed4, kanaler']]
    for scan in scans:
        group = [p for p in profiles if p['context_scan_id'] == scan]
        samples = [originals[p['profile_id']] for p in group]
        actual = samples[0]['row_midpoint_mjd']
        require(all(p['row_midpoint_mjd'] == actual for p in samples), 'Scan midpoint times differ by origin')
        delta_times = [t for p in samples for t in p['times_from_primary_reference_s']]
        shifts = []
        for p in group:
            src = originals[p['profile_id']]
            s = p['original_window_start_row']
            before = src['rounded_absolute_centers'][s:s+4]
            after = target(p)['fine_fixed_original4']['selected4_absolute_centers']
            shifts.extend(abs(a-b) for a,b in zip(before, after))
        label = scan.replace('epoch', 'E').replace('_', ' ').upper()
        geo.append([label, mjd_utc(actual[0]).strftime('%H:%M:%S') + ' - ' + mjd_utc(actual[-1]).strftime('%H:%M:%S'),
                    fmt(min(delta_times), 1) + ' / ' + fmt(max(delta_times), 1), max(shifts)])
    y = table(geo, [63, 175, 163, width - 401], y, padding=3)
    y = paragraph('Δt spænder over de ni oprindelige ankre; kanalændringen er maksimum over deres '
                  'fire fastholdte rækker. Der bruges de faktiske tidsafstande mellem scans og absolut '
                  'kanalafrunding. Ingen vinduesmaksimering flytter ankeret.', y - 6, 'small')
    y = heading('Betinget transport af et indsat signal', y)
    data = [['Amplitude', 'n', 'Fin vinder<br/>rammer 4/4', 'Fin vinder<br/>rigtigt vindue', 'Median løft<br/>fin / grov all7']]
    for amplitude in (2, 8):
        group = [t for t in trials if t['amplitude_per_active_standardized_single_bin'] == amplitude]
        data.append([amplitude, len(group), f"{sum(t['fine_winner_matching_active4_count'] == 4 for t in group)} / {len(group)}",
                     f"{sum(t['fine_winner_matches_true_activity_window'] for t in group)} / {len(group)}",
                     fmt(statistics.median(t['fine_max7_uplift'] for t in group)) + ' / ' +
                     fmt(statistics.median(t['coarse_max7_uplift'] for t in group))])
    y = table(data, [68, 43, 120, 129, width - 360], y)
    base = [t for t in trials if t['amplitude_per_active_standardized_single_bin'] == 2]
    fine_geom = sum(t['signal_only_fine_best_matching_active4_count'] == 4 for t in base)
    coarse_geom = sum(t['coarse_truewindow_matching_active4_count'] == 4 for t in base)
    strong = [t for t in trials if t['amplitude_per_active_standardized_single_bin'] == 8]
    strong_captures = Counter(t['fine_winner_matching_active4_count'] for t in strong)
    partial = sum(v for k, v in strong_captures.items() if k < 4)
    y = paragraph(f'Signal alene: fin familie rammer 4/4 i <b>{fine_geom}/{len(base)}</b>; '
                  f'grov d0/fase0 i <b>{coarse_geom}/{len(base)}</b>. Ved amplitude 8 er '
                  f'<b>{partial}/{len(strong)} vindere partielle</b>: {strong_captures[3]} rammer 3/4, '
                  f'{strong_captures[2]} rammer 2/4. Begge amplituder bruger samme geometrier.', y - 6, 'small')
    y = paragraph('Amplitude 2 eller 8 tilføjes én afrundet bin pr. aktiv række ved offset +512: '
                  '54 profiler × 7 vinduer × 4 off-grid drift/fasepar × 2 amplituder. '
                  '<b>Rådata og normalisering er urørte.</b> De betingede resultater gælder de valgte '
                  'baggrunde og binformen; de måler ikke fysisk følsomhed eller detektionsrate.', y - 6, 'small')
    require(y > 51, f'Page 2 content overflow: {y}')
    c.save()
    print(json.dumps({'status': 'REPORT_CREATED_REQUIRES_VISUAL_QA', 'pdf': str(args.output), 'pages': 2,
                      'profiles': 54, 'injections': 3024, 'source_values_only': True}))


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', type=Path, default=here / 'SCOPE.json')
    parser.add_argument('--profiles', type=Path, default=here / 'results/PROFILES.json')
    parser.add_argument('--injections', type=Path, default=here / 'results/INJECTIONS.json')
    parser.add_argument('--qa', type=Path, default=here / 'qa_results/QA_RECEIPT.json')
    parser.add_argument('--receipt', type=Path, default=here / 'results/EXECUTION_RECEIPT.json')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, default=here / 'output/pdf/SETI_driftkontrol_2026-10-14.pdf')
    parser.add_argument('--check-inputs', action='store_true', help='Read and check JSON, do not author any file')
    args = parser.parse_args()
    prepared = prepare(args)
    if args.check_inputs:
        print(json.dumps({'status': 'PASS_REPORT_INPUT_CENSUS', 'profiles': 54, 'injections': 3024, 'file_authored': False}))
        return
    render(args, prepared)


if __name__ == '__main__':
    main()
