"""Source-only prepared, one-shot saved-JSON control-target report.

No scientific results, arrays or plotting libraries open at import/check-only.
Execution requires both closed independent QA PASS receipts and root GO.
Every used scientific JSON is authenticated against its actual QA byte pins.
"""
from __future__ import annotations
import argparse
import csv
import fcntl
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import time

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
BASE = 'analysis/s2017_control_targets_20261011_v2'
DELIVERY = BASE + '/delivery'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
TARGETS = {'primary20170428_HIP97319': ('HIP97319', 'epoch1_off'),
           'primary20170428_HIP97461': ('HIP97461', 'epoch2_off'),
           'primary20170428_HIP97663': ('HIP97663', 'epoch3_off')}
CORES = tuple(q for q in range(1, 255) if q not in (64, 128, 192))
KNOWN_CHANNEL, KNOWN_MHZ = 179830784, 2300.390625
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP, WORKSPACE_CAP = 180, 300, 2 * 1024**3, 32 * 1024**2, 8 * 1024**3
PINS = {BASE + '/scope.json': '2bc4e6b4176a68e7714c7a0547d2bec70efb630e593569a46f96785fe119d733',
        BASE + '/context_scope.json': '022b93be228cd2e19684bcd8d6471b18e086fdcca6a120092bae6be4b8f95f60',
        BASE + '/qa_saved.py': '210f85fb8874218396149da18b9242d8934a8c4377812dc22205eb8477f740b5',
        BASE + '/qa_context.py': '75161351c62a7847611ef74af1f02e0467afb199c8ae215634afb1dc9784bd8b',
        'analysis/s2017_injection_20261011/delivery/SETI_SIGNALTEST_2026-10-11.md':
            '58bd6b0113c1696737a3b24342ec695aad161b4ee187094f32db5c01359f8525'}
OUTPUTS = ('SUMMARY.json', 'TOP60.csv', 'CORE_MAX753.csv', 'CONTEXT54.csv',
           'SETI_CONTROL_TARGETS_2026-10-11.md', 'SETI_CONTROL_TARGETS_2026-10-11.png', 'REPORT_RECEIPT.json')
TUPLE_FIELDS = ('primary_id', 'primary_target', 'scan_id', 'original_acquisition_role', 'core_q', 'map_id',
                'carrier_index_in_core', 'reference_source_channel', 'frequency_hz_at_own_first_midpoint',
                'reference_time_mjd', 'drift_grid_index', 'drift_hz_s', 'width_channels', 'score')


def require(test, message):
    if not test:
        raise ValueError(message)


def pairs(items):
    value = {}
    for key, item in items:
        require(key not in value, 'Duplicate JSON key: ' + key)
        value[key] = item
    return value


def confined(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, 'Confined relative path required')
    path = root / p
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unconfined/symlink path')
    return path


def byte_pin(root, name):
    p = confined(root, name)
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''):
            h.update(b)
    return {'bytes': p.stat().st_size, 'sha256': h.hexdigest()}


def save_bytes(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def csv_bytes(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='raise', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def workspace_allocated(root):
    seen, total = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                st = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            identity = st.st_dev, st.st_ino
            if identity not in seen:
                seen.add(identity)
                total += st.st_blocks * 512
    return total


def guards(root, out, reserve=False):
    require(workspace_allocated(root) + (OUTPUT_CAP if reserve else 0) <= WORKSPACE_CAP, 'Workspace8GiB cap')
    current = sum((out / n).stat().st_size for n in OUTPUTS if (out / n).exists())
    require(current <= OUTPUT_CAP, 'Report32MiB output cap')
    return current


def metadata_preflight(root):
    observed = {}
    for path, sha in PINS.items():
        require(Path(path).suffix in ('.py', '.json', '.md'), 'Preflight source/metadata only')
        actual = byte_pin(root, path)
        require(actual['sha256'] == sha, 'Frozen report prerequisite differs: ' + path)
        observed[path] = actual
    return observed


def load_admitted(root, name, pins, expected=None):
    require(Path(name).suffix == '.json', 'Report loads JSON only')
    raw = confined(root, name).read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    require(expected is None or actual == expected, 'Actual QA byte pin differs: ' + name)
    require(name not in pins or pins[name] == actual, 'Input changed during admission')
    pins[name] = actual
    return json.loads(raw, object_pairs_hook=pairs)


def admit(root, args, pins):
    for sha in (args.primary_qa_sha256, args.context_qa_sha256, args.source_sha256, args.review_sha256):
        require(re.fullmatch('[0-9a-f]{64}', sha or ''), 'Exact QA/source/review SHA required')
    source_name = DELIVERY + '/make_report.py'
    source_pin = byte_pin(root, source_name)
    require(args.root_go_after_both_qa and source_pin['sha256'] == args.source_sha256,
            'Exact report source and root GO after bothQA required')
    pins[source_name] = source_pin
    review_name = BASE + '/review/REPORT_SOURCE_REVIEW.json'
    review_pin = byte_pin(root, review_name)
    require(review_pin['sha256'] == args.review_sha256, 'Exact independent report-source review SHA')
    review = load_admitted(root, review_name, pins, review_pin)
    require(review['status'].startswith('PASS_') and review['report_source_sha256'] == args.source_sha256,
            'Independent report source review not PASS for these bytes')
    pqa_name, cqa_name = BASE + '/results/review/QA_RECEIPT.json', BASE + '/results/context_review/QA_RECEIPT.json'
    pqa_pin, cqa_pin = byte_pin(root, pqa_name), byte_pin(root, cqa_name)
    require(pqa_pin['sha256'] == args.primary_qa_sha256
        and cqa_pin['sha256'] == args.context_qa_sha256, 'Actual closed QA SHA differs')
    pqa, cqa = load_admitted(root, pqa_name, pins, pqa_pin), load_admitted(root, cqa_name, pins, cqa_pin)
    require(pqa['schema'] == 'SETI_S2017_CONTROL_TARGET_SAVED_INDEPENDENT_QA_V1'
        and pqa['status'] == 'PASS753_ORIGINAL_OFF_MAPS3021_RAW_SCORE_QUERIES_NO_DETECTOR_RERUN'
        and pqa['qa_sha256'] == PINS[BASE + '/qa_saved.py']
        and pqa['primary_scope_sha256'] == PINS[BASE + '/scope.json'], 'Primary saved-map QA gate')
    require(cqa['schema'] == 'SETI_S2017_CONTROL_TARGET_FIXED_CONTEXT_INDEPENDENT_QA_V1'
        and cqa['status'] == 'PASS54_FIXED_CONTEXT_RAW503_SCORES96_SOURCE_ROWS_NO_SEARCH'
        and cqa['qa_sha256'] == PINS[BASE + '/qa_context.py']
        and cqa['context_scope_sha256'] == PINS[BASE + '/context_scope.json']
        and cqa['primary_qa_receipt_sha256'] == args.primary_qa_sha256, 'Fixed-context independent QA gate')
    for qa in (pqa, cqa):
        require(qa['numeric_tolerance'] == {'absolute': 1e-7, 'relative': 1e-10}
            and qa['new_HTTP_requests'] == 0 and qa['detector_import_or_search_rerun'] is False
            and qa['qualified_SETI_detection'] is False, 'QA scope/network/numerical contract')
    require(pqa['counts']['maps'] == 753 and pqa['counts']['score_audit_queries'] == 3021
        and pqa['counts']['top20_entries'] == 60 and pqa['counts']['top3_entries'] == 9
        and cqa['counts']['fixed_profiles'] == 54 and cqa['counts']['source_decoded_rows'] == 96
        and cqa['counts']['origin_primary_score_matches'] == 9, 'All753/60/9/54 actual QA counts required')
    require(set(pqa['primary_receipt_sha256s']) == set(TARGETS), 'Three actual primary jobs required')
    receipts, top60, selected, coremax = [], [], [], []
    for primary_id, (target, scan) in TARGETS.items():
        rp = BASE + '/results/' + primary_id + '/EXECUTION_RECEIPT.json'
        require(pqa['input_byte_pins'][rp]['sha256'] == pqa['primary_receipt_sha256s'][primary_id], 'Primary receipt SHA binding')
        receipt = load_admitted(root, rp, pins, pqa['input_byte_pins'][rp])
        require(cqa['input_byte_pins'][rp] == pins[rp], 'ContextQA primary receipt byte binding')
        require(receipt['status'] == 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY'
            and receipt['primary_id'] == primary_id and receipt['scan_id'] == scan
            and receipt['original_acquisition_role'] == 'OFF' and receipt['counts']['maps'] == 251,
            'Three originalOFF jobs must be COMPLETE')
        receipts.append(receipt)
        objects = []
        for name in ('TOP20.json', 'TOP3.json', 'SCORE_AUDITS.json'):
            path = BASE + '/results/' + primary_id + '/' + name
            obj = load_admitted(root, path, pins, pqa['input_byte_pins'][path])
            require(obj['primary_id'] == primary_id and obj['scan_id'] == scan, 'Saved primary JSON identity')
            objects.append(obj)
        top, top3, audits = objects
        require(len(top['records']) == 20 and top3['records'] == top['records'][:3]
            and top3['records'] == pqa['selected_top3'][primary_id], 'Exact original selectedTOP3')
        for rank, record in enumerate(top['records'], 1):
            require(record['rank'] == rank and record['primary_id'] == primary_id
                and record['primary_target'] == target and record['scan_id'] == scan
                and record['original_acquisition_role'] == 'OFF' and math.isfinite(record['score']), 'Original rank/frame/finite score')
        top60.extend(top['records'])
        selected.extend(top3['records'])
        require(len(audits['records']) == 1007, 'Exact1007 declared audit queries per star')
        chosen = [a for a in audits['records'] if a['query_kind'] == 'core_max']
        require(len(chosen) == 251 and [a['core_q'] for a in chosen] == list(CORES), 'All251 predeclared core_max queries')
        for a in chosen:
            t = a['selected_tuple']
            require(set(t) == set(TUPLE_FIELDS) and t['primary_id'] == primary_id
                and t['core_q'] == a['core_q'] and math.isfinite(t['score']), 'Exact audited core maximum tuple')
            coremax.append({'query_id': a['query_id'], 'query_kind': a['query_kind'], **t})
    cp = BASE + '/results/context/EXECUTION_RECEIPT.json'
    require(cqa['input_byte_pins'][cp]['sha256'] == cqa['context_receipt_sha256'], 'Context receipt exact SHA binding')
    context_receipt = load_admitted(root, cp, pins, cqa['input_byte_pins'][cp])
    require(context_receipt['status'] == 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES_NO_OPTIMIZATION'
        and context_receipt['primary_receipt_sha256s'] == pqa['primary_receipt_sha256s']
        and context_receipt['actual_primary_QA_receipt_sha256'] == args.primary_qa_sha256, 'Actual context COMPLETE admission')
    mp = BASE + '/results/context/CONTEXT_PROFILES.json'
    matrix = load_admitted(root, mp, pins, cqa['input_byte_pins'][mp])
    require(matrix['status'] == 'COMPLETE_NINE_PRIMARY_SELECTED_TUPLES54_FIXED_SCAN_CONTEXT_PROFILES'
        and matrix['selected_tracks'] == selected and len(selected) == 9 and len(matrix['profiles']) == 54,
        'Exact nine selected tuples and54 actual contexts')
    return pqa, cqa, receipts, context_receipt, top60, coremax, matrix


def derive(selected, profiles):
    require(len({p['profile_id'] for p in profiles}) == 54, 'Unique54 context identities')
    summaries, groups = [], {}
    for track in selected:
        key = track['primary_target'] + ' #' + str(track['rank'])
        contexts = [p for p in profiles if p['selected_track'] == track]
        require([p['context_scan_id'] for p in contexts] == list(SCANS), 'All6 contexts in canonical order')
        origin = next(p for p in contexts if p['context_scan_id'] == track['scan_id'])
        terms = origin['row_standardized_box_sum']
        require(len(terms) == 16 and all(math.isfinite(x) for x in terms), 'All16 signed primary row terms')
        positive = [max(x, 0.) for x in terms]
        total = math.fsum(positive)
        fractions = [x / total for x in positive] if total > 0 else [None] * 16
        radius = track['width_channels'] // 2
        centers = origin['rounded_absolute_centers']
        require(len(centers) == 16, 'All16 origin centres')
        hits = [abs(c - KNOWN_CHANNEL) <= radius for c in centers]
        geometry = {'normalization_core_q': track['core_q'], 'width_channels': track['width_channels'],
                    'all6_rounded_absolute_centers': [p['rounded_absolute_centers'] for p in contexts]}
        signature = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        groups.setdefault(signature, []).append(key)
        summaries.append({'track_key': key, 'selected_tuple': track,
            'context_scores': {p['context_scan_id']: p['direct_fixed_robust_box_track_score'] for p in contexts},
            'primary_signed_row_box_terms': terms, 'primary_positive_row_terms': positive,
            'primary_positive_row_total': total, 'primary_positive_row_fractions': fractions,
            'largest_primary_positive_row_fraction': max(fractions) if total > 0 else None,
            'known_reference_channel': KNOWN_CHANNEL, 'known_reference_box_hit_by_primary_row': hits,
            'known_reference_box_hit_row_count': sum(hits),
            'positive_row_fraction_on_reference_hit_rows': math.fsum(f for f, hit in zip(fractions, hits) if hit) if total > 0 else None,
            'complete96centre_width_core_signature_sha256': signature,
            'fraction_definition': 'max(saved signed row-box sum,0)/sum all16 positive row-box sums; no-positive denominator is undefined/null',
            'known_reference_interpretation': 'Geometric box/reference alignment only; a whole-row contribution includes every box cell and is not attributed to the reference cell.'})
    return summaries, [{'signature_sha256': sig, 'logical_track_keys': keys,
                         'logical_track_count': len(keys)} for sig, keys in groups.items()]


def format_score(x):
    return '—' if x is None else format(x, '.6g')


def report_text(summary):
    rows = summary['selected_primary_summaries']
    out = ['# SETI · tre oprindelige kontrolretninger · 11. oktober 2026', '',
        '**753 nye kernemaps er afsluttet én gang i den korrigerede V2-fase og har bestået uafhængig QA.** '
        'De tre stjerner HIP97319, HIP97461 og HIP97663 har hver én oprindelig OFF-scanning fra besøget 28. april 2017. '
        'Ni spor er valgt efter primærsøgningen og derefter målt uændret i alle seks historiske scanninger. '
        'Dette er søge- og retningskontekst fra samme besøg; der er ingen ny kvalificeret SETI-detektion.', '',
        'Alle 4096 referencekanalers maksimum i hver af 251 faste kerner pr. stjerne er bevaret. '
        'Kerne 0/255 og de allerede kortlagte kerner 64/128/192 indgår ikke i denne primærsøgning. '
        'Det giver 3.084.288 carrier-maksima og 4.842.332.160 korrelerede drift/bredde-kombinationer '
        '(785 drifter, bredde 1/3). Tallene er ikke uafhængige statistiske forsøg. '
        'Scoren er en empirisk robust box-track-score; den er **ikke kalibreret S/N eller FAP**.', '',
        '![Alle kernemaksima, faste kontekstscorer og primære rækkebidrag](SETI_CONTROL_TARGETS_2026-10-11.png)', '',
        '| Primært udvalg | Frekvens MHz ved første midpoint | Drift Hz/s | Bredde | Primærscore | Største positive rækkeandel | Rækker med referencekanal i box |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        t = row['selected_tuple']; fraction = row['largest_primary_positive_row_fraction']
        out.append('| %s | %.9f | %.9g | %d | %s | %s | %d/16 |' %
            (row['track_key'], t['frequency_hz_at_own_first_midpoint'] / 1e6, t['drift_hz_s'], t['width_channels'],
             format_score(t['score']), '—' if fraction is None else '%.2f%%' % (100 * fraction), row['known_reference_box_hit_row_count']))
    cores = sorted({r['selected_tuple']['core_q'] for r in rows})
    widths = sorted({r['selected_tuple']['width_channels'] for r in rows})
    overlaps = ['%s: %s' % (target, '/'.join(str(r['known_reference_box_hit_row_count'])
        for r in rows if r['selected_tuple']['primary_target'] == target)) for target, scan in TARGETS.values()]
    reference_fractions = [r['positive_row_fraction_on_reference_hit_rows'] for r in rows
                          if r['positive_row_fraction_on_reference_hit_rows'] is not None]
    minimum = 'udefineret' if not reference_fractions else '%.4f%%' % (100 * min(reference_fractions))
    out.extend(['', 'Alle ni primærudvalg bruger kerne %s og bredde %s. Referencekanalen ligger i følgende antal af de 16 rækkebokse '
        '(rank 1/2/3): %s. Mindst %s af den positive rækkemasse ligger på reference-hit-rækker for de udvalg med defineret nævner. '
        'Mønstret er foreneligt med flere søgeskabeloner omkring den tidligere kendte 2300.390625 MHz-komponent; '
        'de ni udvalg etablerer ikke ni uafhængige kilder. Rækkemassen gælder hele den valgte box og kan ikke tilskrives referencecellen alene. '
        'Den fysiske årsag er fortsat uafklaret.' %
        ('/'.join('q%d' % q for q in cores), '/'.join(str(w) for w in widths), '; '.join(overlaps), minimum)])
    fixed_case = next(r for r in rows if r['selected_tuple']['primary_target'] == 'HIP97461'
                      and r['selected_tuple']['rank'] == 1)
    case_scores = list(fixed_case['context_scores'].values())
    out.extend(['', 'HIP97461 #1 har drift %s Hz/s og faste scorer fra %s til %s i de seks scanninger. '
        'Svagere scorer for andre faste drifter uden for deres primærscanning er tid/retningskontekst; '
        'de dokumenterer hverken blank himmel eller et signal, der kun findes ved den valgte stjerne.' %
        (format_score(fixed_case['selected_tuple']['drift_hz_s']), format_score(min(case_scores)), format_score(max(case_scores)))])
    out.extend(['', 'Hver række er et separat primærudvalg. Tabellen nedenfor viser alle seks faste scorer; '
        'den primære scanning er markeret med fed, og de øvrige fem er tid/retningskontekst. '
        'De oprindelige ON/OFF-roller er bevaret. De andre retninger er ikke certificeret blank himmel eller gentagne observationer af den valgte primærstjerne.', '',
        '| Udvalg | ' + ' | '.join('%d %s · %s' % (i // 2 + 1, item['original_acquisition_role'], item['target'])
            for i, item in enumerate(summary['original_scan_metadata'])) + ' |',
        '|---|---:|---:|---:|---:|---:|---:|'])
    for row in rows:
        cells = [format_score(row['context_scores'][scan]) for scan in SCANS]
        cells[SCANS.index(row['selected_tuple']['scan_id'])] = '**' + cells[SCANS.index(row['selected_tuple']['scan_id'])] + '**'
        out.append('| ' + row['track_key'] + ' | ' + ' | '.join(cells) + ' |')
    groups = summary['fixed_measurement_geometry_groups']
    repeated = [g for g in groups if g['logical_track_count'] > 1]
    out.extend(['', 'De ni logiske udvalg svarer til %d forskellige kombinationer af alle 96 afrundede centre, '
        'bredde og fast normaliseringskerne. Gentagne kombinationer er bevaret: %s. '
        'Dette er en beskrivelse af gemt målegeometri, ikke et antal uafhængige kilder.' %
        (len(groups), '; '.join(', '.join(g['logical_track_keys']) for g in repeated) if repeated else 'ingen'), '',
        'Rækkeandelen er hvert positivt gemt rækkebidrag divideret med summen af alle 16 positive bidrag; '
        'de fortegnede bidrag bevares i JSON/CSV. Hvis nævneren er nul, er andelen udefineret. '
        'Den tidligere kendte reference er kildekanal 179830784, 2300.390625 MHz. Et hit betyder kun, at den valgte box dækker denne kanal i den pågældende række. '
        'Hverken overlap eller en dominerende række alene fastslår fysisk årsag, RFI eller en himmelkilde. '
        'Der er ingen ny tilpasning, filtrering af udvalg, veto eller detektionstest.', '',
        'Kontekstsporet fastholder primærfrekvensen ved primærscanningens første integrationsmidpoint samt den valgte drift og bredde. '
        'Alle faktiske filstarttider og mellemrum indgår. De samme 4096 absolutte kernekanaler normaliserer hver scanning med uændret 501-filter og 4000-halo. '
        'Den primære driftgridopløsning giver ikke en garanti om subkanal-match over hele kadencen.', '',
        'Primær-QA kontrollerede 753 maps og 3021 faste råscore-queries; kontekst-QA kontrollerede 54 profiler, 434.592 rå503-vinduesceller, '
        'alle 96 kilde-rækkehashes og ni primærscore-match med fast tolerance 1e-7 absolut/1e-10 relativ. '
        'Kernens rækkemedianer blev uafhængigt genberegnet. MAD/lokationsparametre er hashbundne gemte kerneparametre; '
        'de blev ikke uafhængigt fuldt refiltreret fra de lokale 503 celler. Ingen QA genkørte hele detektorgridet.', '',
        'Den oprindelige fase fejlede i alle tre job ved lokale metadata før effektarrayet blev læst: 0 maps og 0 scorer. '
        'De oprindelige kodebytes, tre fejlreceipts og terminalbevis er bevaret. V2 bruger en særskilt mappe og gennemførte hvert af de tre videnskabsjob én gang; '
        'de oprindelige ON-udvalg, injektionstesten og kontekststadiet er særskilte resultater. '
        'Ingen nye teleskopforespørgsler eller BODY-bytes blev hentet; 0 kr. Original A/B-status er fortsat FAIL_CLOSED_UNCHANGED.', '',
        '[Alle 60 top20-poster](TOP60.csv) · [Alle 753 kernemaksima](CORE_MAX753.csv) · '
        '[Alle 54 kontekster](CONTEXT54.csv) · [Samlet JSON](SUMMARY.json) · [Rapportreceipt](REPORT_RECEIPT.json)', '',
        'Læsinput er bundet til de faktiske QA-receipts og deres bytepins i SUMMARY og REPORT_RECEIPT. '
        'Der følger ingen kalibreret fluxfølsomhed, global falsk-alarm-rate, populationskomplethed, ny besøgsreplikation eller fysisk kildeklassifikation af denne opsummering.', ''])
    return '\n'.join(out)


def render(summary, output):
    import numpy as np
    import matplotlib
    require(importlib.metadata.version('matplotlib') == '3.10.8', 'Exact Matplotlib3.10.8 required')
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt, colors, patches, patheffects
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10})
    fig = plt.figure(figsize=(16, 11.5), dpi=160)
    grid = fig.add_gridspec(3, 2, width_ratios=(1.35, 2.05), height_ratios=(1, 1, 1.2),
                          left=.065, right=.94, bottom=.11, top=.88, hspace=.45, wspace=.36)
    fig.suptitle('Tre oprindelige kontrolretninger · 28. april 2017', fontsize=20, fontweight='bold', y=.98)
    fig.text(.5, .935, '753 kernemaksima · 9 faste udvalg × 6 scanninger · robuste scorer, ikke kalibreret S/N eller FAP', ha='center', fontsize=11)
    for index, (primary_id, (target, scan)) in enumerate(TARGETS.items()):
        ax = fig.add_subplot(grid[index, 0])
        rows = [r for r in summary['all753_audited_core_maxima'] if r['primary_id'] == primary_id]
        for start, stop in ((1, 64), (65, 128), (129, 192), (193, 255)):
            segment = [r for r in rows if start <= r['core_q'] < stop]
            ax.plot([r['frequency_hz_at_own_first_midpoint'] / 1e6 for r in segment],
                    [r['score'] for r in segment], color=('#137f88', '#4356a8', '#b75f12')[index], lw=.9, marker='.', ms=2.8)
        ax.axvline(KNOWN_MHZ, color='#383838', ls='--', lw=1, label='Tidligere kendt reference 2300.390625 MHz')
        ax.set_yscale('symlog', linthresh=1.)
        ax.grid(alpha=.2)
        ax.set_title(target + ' · ' + scan + ' (oprindelig OFF)', loc='left')
        ax.set_ylabel('Robust maksimumsscore')
        if index == 2:
            ax.set_xlabel('MHz ved primærscanningens første midpoint')
        if index == 0:
            ax.legend(fontsize=7.5, frameon=False, loc='upper right')
    rows = summary['selected_primary_summaries']
    values = np.asarray([[r['context_scores'][s] for s in SCANS] for r in rows], dtype=float)
    vmax = max(1., float(np.max(np.abs(values))))
    ax = fig.add_subplot(grid[:2, 1])
    image = ax.imshow(values, aspect='auto', cmap='coolwarm',
                      norm=colors.SymLogNorm(linthresh=1., vmin=-vmax, vmax=vmax))
    ax.set_yticks(range(9), [r['track_key'] for r in rows])
    ax.set_xticks(range(6), ['%d %s\n%s' % (i // 2 + 1, item['original_acquisition_role'], item['target'])
        for i, item in enumerate(summary['original_scan_metadata'])], fontsize=8)
    ax.set_title('Fast uændret spor i alle seks scanninger', loc='left', pad=12)
    for i, row in enumerate(rows):
        origin = SCANS.index(row['selected_tuple']['scan_id'])
        ax.add_patch(patches.Rectangle((origin - .5, i - .5), 1, 1, fill=False, ec='black', lw=2.1))
        for j, value in enumerate(values[i]):
            text = ax.text(j, i, format(value, '.3g'), ha='center', va='center', fontsize=8.2, color='black')
            text.set_path_effects([patheffects.withStroke(linewidth=2.0, foreground='white')])
    colorbar = fig.colorbar(image, ax=ax, fraction=.035, pad=.025)
    colorbar.set_label('Fast robust score · symmetrisk logfarve')
    ax.text(0., - .13, 'Sort ramme: primærscanning. Alle andre felter: tid/retningskontekst.', transform=ax.transAxes, fontsize=9)
    ax = fig.add_subplot(grid[2, 1])
    fractions = np.asarray([[np.nan if x is None else x for x in r['primary_positive_row_fractions']] for r in rows])
    cmap = plt.get_cmap('viridis').copy(); cmap.set_bad('#c9c9c9')
    image = ax.imshow(fractions, aspect='auto', cmap=cmap, vmin=0, vmax=1)
    labels = [r['track_key'] + ' · hit %d/16' % r['known_reference_box_hit_row_count'] for r in rows]
    ax.set_yticks(range(9), labels, fontsize=8.5)
    ax.set_xticks(range(16), range(1, 17), fontsize=8)
    ax.set_title('Primærscanning: andel af positive rækkebidrag', loc='left', pad=9)
    ax.set_xlabel('Integrationsrække · ×: box dækker den tidligere referencekanal')
    for i, row in enumerate(rows):
        for j, hit in enumerate(row['known_reference_box_hit_by_primary_row']):
            if hit:
                text = ax.text(j, i, '×', ha='center', va='center', color='white', fontsize=11)
                text.set_path_effects([patheffects.withStroke(linewidth=1.5, foreground='black')])
    colorbar = fig.colorbar(image, ax=ax, fraction=.035, pad=.025)
    colorbar.set_ticks([0, .25, .5, .75, 1], ['0%', '25%', '50%', '75%', '100%'])
    fig.text(.5, .045, 'Alle logiske udvalg bevares; samme 96 centre/bredde/kerne kan gentages. Rækkeandele er beskrivende og giver ingen ny detektionstest.', ha='center', fontsize=9)
    fig.text(.5, .018, 'Referenceoverlap fastslår ingen fysisk årsag. Kerne-MAD/lokation er hashbundne; ingen uafhængig fuld refiltrering eller global FAP.', ha='center', fontsize=9)
    buffer = io.BytesIO(); fig.savefig(buffer, format='png'); plt.close(fig)
    save_bytes(output, buffer.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--source-sha256')
    parser.add_argument('--review-sha256')
    parser.add_argument('--primary-qa-sha256')
    parser.add_argument('--context-qa-sha256')
    parser.add_argument('--root-go-after-both-qa', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    pins = metadata_preflight(root)
    if args.check_only:
        print(json.dumps({'status': 'PASS_REPORT_SOURCE_METADATA_ONLY_NO_RESULT_JSON_OR_NUMERIC_IMPORTS',
            'prerequisite_code_metadata_pins': len(pins), 'report_source_sha256': byte_pin(root, DELIVERY + '/make_report.py')['sha256']}))
        return
    started, cpu0 = time.monotonic(), time.process_time()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Report wall300s cap')
    signal.signal(signal.SIGALRM, deadline); signal.alarm(WALL_CAP)
    out = root / DELIVERY
    lock, output_started = None, False
    try:
        fd = os.open(root / BASE / 'ACTIVE_FAMILY_FLOCK.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        lock = os.fdopen(fd, 'a+b'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pqa, cqa, receipts, creceipt, top60, coremax, matrix = admit(root, args, pins)
        require(not any((out / n).exists() for n in OUTPUTS), 'Create-only report outputs already exist')
        guards(root, out, reserve=True)
        selected, groups = derive(matrix['selected_tracks'], matrix['profiles'])
        require(len(top60) == 60 and len(coremax) == 753 and len(selected) == 9, 'Exact full report cardinalities')
        scope = load_admitted(root, BASE + '/scope.json', pins, pins[BASE + '/scope.json'])
        correction = scope['corrected_new_namespace_preserves_initial_attempt']
        require(correction['new_spectrum_map_count_before_correction'] == 0
            and correction['initial_failed_outputs_reused'] is False, 'Preserved zero-map failure provenance')
        for target in TARGETS:
            name = correction['initial_phase'] + '/results/' + target + '/EXECUTION_RECEIPT.json'
            failed = load_admitted(root, name, pins, correction['initial_attempt_file_pins'][name])
            require(failed['status'] == 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY'
                and failed['failure_type'] == 'KeyError' and 'DIMENSION_LABELS' in failed['failure'], 'Initial metadata-only failure identity')
        summary = {'schema': 'SETI_S2017_CONTROL_TARGET_ALL_SAVED_JSON_REPORT_V1',
            'status': 'COMPLETE_ALL753_CORE_MAXIMA60_TOP20_NINE_FIXED54_CONTEXTS_BOTH_QA_PASS',
            'actual_primary_QA_receipt_sha256': args.primary_qa_sha256,
            'actual_context_QA_receipt_sha256': args.context_qa_sha256,
            'primary_receipt_sha256s': pqa['primary_receipt_sha256s'],
            'context_receipt_sha256': cqa['context_receipt_sha256'],
            'read_input_byte_pins': pins,
            'original_scan_metadata': [{'scan_id': p['context_scan_id'], 'target': p['context_target'],
                'original_acquisition_role': p['original_acquisition_role']} for p in matrix['profiles'][:6]],
            'all60_original_top20_records': top60,
            'all753_audited_core_maxima': coremax, 'all54_original_fixed_context_records': matrix['profiles'],
            'selected_primary_summaries': selected, 'fixed_measurement_geometry_groups': groups,
            'counts': {'primary_jobs': 3, 'maps': 753, 'carrier_maxima': 3084288,
                'correlated_width_drift_combinations': 4842332160, 'top20_records': 60,
                'selected_logical_tracks': 9, 'fixed_context_records': 54, 'primary_fraction_rows': 144},
            'previous_known_reference': {'channel': KNOWN_CHANNEL, 'frequency_MHz': KNOWN_MHZ,
                'scope': 'Pre-existing reference metadata; origin box overlap is descriptive geometry, not source attribution or a veto.'},
            'initial_failed_phase_provenance': correction,
            'actual_resources': {'primary_jobs': [{k: r[k] for k in ('primary_id', 'process_CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')} for r in receipts],
                'context': {k: creceipt[k] for k in ('process_CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')}},
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP_or_population_completeness': False,
            'new_fit_selection_or_veto': False, 'new_sky_visit': False, 'new_HTTP_requests': 0,
            'new_BODY_bytes': 0, 'cost_DKK': 0, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
            'limits': ['Each star has one originalOFF scan; other five are fixed same-visit direction/time context.',
                'Top3 selection is postsearch; all logical duplicates remain visible and are not independent confirmations.',
                'QA independently checks row medians and local raw503 arithmetic conditional on hash-bound saved core MAD/location, not every detector-grid score.',
                'Positive row fractions and prior-reference overlap are descriptive; signed source terms are preserved and no fitted threshold or source-cause classification is introduced.']}
        context_rows = []
        for p in matrix['profiles']:
            t = p['selected_track']
            context_rows.append({'profile_id': p['profile_id'], 'primary_id': t['primary_id'], 'primary_target': t['primary_target'],
                'primary_rank': t['rank'], 'primary_scan_id': t['scan_id'], 'context_scan_id': p['context_scan_id'],
                'context_target': p['context_target'], 'original_acquisition_role': p['original_acquisition_role'],
                'core_q': t['core_q'], 'reference_source_channel': t['reference_source_channel'],
                'reference_time_mjd': t['reference_time_mjd'], 'frequency_hz_at_primary_first_midpoint': t['frequency_hz_at_own_first_midpoint'],
                'drift_hz_s': t['drift_hz_s'], 'width_channels': t['width_channels'],
                'direct_fixed_robust_box_track_score': p['direct_fixed_robust_box_track_score'],
                'is_primary_origin': p['context_scan_id'] == t['scan_id'],
                'times_from_primary_reference_s_JSON': json.dumps(p['times_from_primary_reference_s']),
                'rounded_absolute_centers_JSON': json.dumps(p['rounded_absolute_centers']),
                'signed_row_box_terms_JSON': json.dumps(p['row_standardized_box_sum']),
                'raw_capsule_sha256': p['raw_capsule']['sha256'], 'normalization_sha256': p['normalization']['sha256']})
        files = {'SUMMARY.json': json_bytes(summary), 'TOP60.csv': csv_bytes(top60, ('rank',) + TUPLE_FIELDS),
            'CORE_MAX753.csv': csv_bytes(coremax, ('query_id', 'query_kind') + TUPLE_FIELDS),
            'CONTEXT54.csv': csv_bytes(context_rows, tuple(context_rows[0])),
            'SETI_CONTROL_TARGETS_2026-10-11.md': report_text(summary).encode()}
        require(sum(len(b) for b in files.values()) < OUTPUT_CAP, 'Prospective text output bound')
        output_started = True
        for name, data in files.items():
            save_bytes(out / name, data)
        render(summary, out / 'SETI_CONTROL_TARGETS_2026-10-11.png')
        for name, expected in pins.items():
            require(byte_pin(root, name) == expected, 'Read input changed: ' + name)
        guards(root, out)
        usage = {'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP
            and 0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Measured final report resource bound')
        receipt = {'schema': 'SETI_S2017_CONTROL_TARGET_SAVED_REPORT_RECEIPT_V1',
            'status': 'COMPLETE_ALL753_CORE60_TOP20_AND54_FIXED_CONTEXT_SAVED_REPORT',
            'report_source_sha256': args.source_sha256, 'independent_source_review_sha256': args.review_sha256,
            'actual_primary_QA_receipt_sha256': args.primary_qa_sha256,
            'actual_context_QA_receipt_sha256': args.context_qa_sha256, 'input_byte_pins': pins,
            'output_byte_pins': {n: byte_pin(root, DELIVERY + '/' + n) for n in OUTPUTS if n != 'REPORT_RECEIPT.json'},
            'counts': summary['counts'], 'previous_reference_diagnostic_was_predeclared_before_saved_rank_reads': True,
            'matplotlib_version': '3.10.8', **usage, 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
            'memory_cap_bytes': RAM_CAP, 'output_cap_bytes': OUTPUT_CAP, 'workspace_cap_bytes': WORKSPACE_CAP,
            'H5_NPZ_BIN_opened': False, 'detector_or_score_grid_rerun': False, 'new_fit_selection_or_veto': False,
            'new_HTTP_requests': 0, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False}
        rb = json_bytes(receipt)
        require(guards(root, out) + len(rb) <= OUTPUT_CAP and workspace_allocated(root) + len(rb) <= WORKSPACE_CAP,
                'Completed report receipt output/workspace bound')
        save_bytes(out / 'REPORT_RECEIPT.json', rb)
        print(json.dumps({'status': receipt['status'], 'report_receipt': byte_pin(root, DELIVERY + '/REPORT_RECEIPT.json')}))
    except BaseException as exc:
        if output_started and not (out / 'REPORT_RECEIPT.json').exists():
            save_bytes(out / 'REPORT_RECEIPT.json', json_bytes({'schema': 'SETI_S2017_CONTROL_TARGET_SAVED_REPORT_RECEIPT_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'failure_type': type(exc).__name__,
                'failure': str(exc), 'H5_NPZ_BIN_opened': False, 'new_HTTP_requests': 0}))
        raise
    finally:
        signal.alarm(0)
        if lock is not None:
            lock.close()


if __name__ == '__main__':
    main()
