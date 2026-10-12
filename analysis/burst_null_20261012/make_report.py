"""Prospective saved-JSON report of eight full-search Gamma engineering families.

No model generation, detector invocation, capsule decoding, grid maximization,
or numerical QA occurs here. Exact completed primary and QA receipts gate all
report writes. Eight model families are the analysis units; their nested TOP3
and the separately exposed nine real-data references are not pooled trials.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import statistics
import time

for thread_variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[thread_variable] = '1'

BASE = 'analysis/burst_null_20261012'
PRIOR = 'analysis/burst_order_20261011'
JOBS = tuple(f'null{i:02d}' for i in range(1, 9))
PRIMARY_STATUS = 'COMPLETE_96_IID_GAMMA_NULL_MAPS387_AUDITS3_ORDER_DIAGNOSTICS'
QA_STATUS = 'PASS_8_IID_GAMMA_FAMILIES768_MAPS3096_AUDITS24_ORDER_QUERIES576_PERMUTATION_SCORES'
REPORT_STATUS = 'COMPLETE_QA_GATED_GAMMA51_FULL_SEARCH_ENGINEERING_REPORT_AND_TWO_FIGURES'
CPU_CAP, WALL_CAP, RAM_CAP, OUTPUT_CAP = 200, 900, 2 * 1024**3, 20 * 1024**2
EXPECTED_PRIMARY = {'maps': 96, 'carrier_maximum_records': 393216,
                    'valid_hypothesis_records': 875298816, 'normalization_records': 96,
                    'score_audit_queries': 387, 'score_audit_raw_power_cells': 778644,
                    'TOP20_entries': 20, 'TOP3_entries': 3,
                    'order_queries': 3, 'row_center_boxes': 48, 'permutation_scores': 72,
                    'generated_raw_crops': 96, 'generated_raw_rows': 1536, 'generated_raw_cells': 18579456}
EXPECTED_QA = {'families': 8, 'maps': 768, 'carrier_maxima': 3145728,
               'valid_hypothesis_records': 7002390528, 'normalization_records': 768,
               'model_raw_crops_regenerated': 768, 'model_raw_rows_SHA256': 12288,
               'model_raw_cells_regenerated': 148635648, 'raw_core_row_medians': 12288,
               'score_audit_queries': 3096, 'score_audit_row_boxes': 12384,
               'score_audit_raw_cells': 6229152, 'TOP20_entries': 160, 'TOP3_entries': 24,
               'order_queries': 24, 'row_center_boxes': 384, 'permutation_scores': 576}
GEOMETRY_LABELS = {'zero_drift': 'nuldrift', 'same_center_nonzero_drift': 'én centerkanal, drift ≠ 0',
                   'repeated_centers': '2–3 centerkanaler', 'four_distinct_centers': '4 centerkanaler'}


def require(test, message):
    if not test:
        raise ValueError(message)


def confined(root, name):
    path = (root / name).resolve()
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and path.is_relative_to(root),
            'Confined relative project path required')
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def read_json(path):
    require(path.suffix == '.json', 'Only saved JSON metadata/results may be parsed')
    return json.loads(path.read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def checked(root, declaration, expected_path=None):
    path = confined(root, declaration['path'])
    require(path.suffix in ('.py', '.json', '.csv', '.md', '.txt') and
            (expected_path is None or path == expected_path) and pin(root, path) == declaration,
            'Exact saved JSON/text pin differs: ' + declaration['path'])
    return path


def save_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def save_csv(path, records):
    require(records, 'Nonempty saved-data table required')
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def integer(value):
    return f'{value:,}'.replace(',', '.')


def number(value, digits=6):
    return 'udefineret' if value is None else f'{value:.{digits}g}'


def geometry(record):
    centers = record['centers']
    require(type(centers) is list and len(centers) == 4 and all(type(c) is int for c in centers),
            'Four authenticated integer centers required')
    unique = len(set(centers))
    require(record['stationary_centers'] == (unique == 1) and record['duplicate_centers'] == (unique < 4),
            'Saved geometric flags differ')
    if record['selected_tuple']['drift_hz_s'] == 0:
        require(unique == 1, 'Zero drift must be a stationary-center case')
        return 'zero_drift'
    if unique == 1:
        return 'same_center_nonzero_drift'
    return 'repeated_centers' if unique < 4 else 'four_distinct_centers'


def order_row(record, family):
    """Copy authenticated saved statistics; do not recompute a score or rank."""
    t = record['selected_tuple']
    unique = record['distinct_assignment_count']
    require(type(unique) is int and 1 <= unique <= 24 and len(record['permutation_scores']) == 24 and
            len(record['permutation_center_vectors']) == 24 and
            len(record['distinct_center_vectors']) == len(record['distinct_scores']) == unique and
            record['wrong_order_distinct_count'] == unique - 1,
            'Saved identity-inclusive/deduplicated order inventory differs')
    require(all(math.isfinite(v) for v in record['permutation_scores']) and math.isfinite(record['identity_score']),
            'Finite saved scores required')
    controls = ('wrong_order_max_score', 'wrong_order_median_score', 'identity_minus_wrong_order_max',
                'identity_minus_wrong_order_median')
    require(all(record[k] is None for k in controls) if unique == 1 else
            all(math.isfinite(record[k]) for k in controls), 'Degenerate alternatives must be undefined')
    lo, hi = record['identity_rank_best'], record['identity_rank_worst']
    require(type(lo) is int and type(hi) is int and 1 <= lo <= hi <= unique and
            record['identity_exact_tie_count'] == hi - lo + 1 and record['diagnostic_degenerate'] == (unique == 1),
            'Saved exact-rank interval or degeneracy differs')
    require(record['source_rows'] == t['window_source_rows'], 'Fixed physical source rows differ')
    return {'family_id': family, 'rank': t['rank'], 'geometry': geometry(record),
            'native_chunk_index': t['native_chunk_index'], 'core_q': t['core_q'],
            'carrier_index_in_core': t['carrier_index_in_core'], 'source_reference_channel': t['source_reference_channel'],
            'window_start_row': t['window_start_row'], 'width_channels': t['width_channels'],
            'frequency_MHz_at_window_reference': t['frequency_hz_at_window_reference'] / 1e6,
            'reference_time_s_from_synthetic_scan_start': t['reference_time_s_from_synthetic_scan_start'],
            'drift_hz_s': t['drift_hz_s'], 'prior_selected_score': t['score'],
            'chronological_score': record['identity_score'],
            'wrong_order_max_score': record['wrong_order_max_score'],
            'wrong_order_median_score': record['wrong_order_median_score'],
            'identity_minus_wrong_order_max': record['identity_minus_wrong_order_max'],
            'identity_minus_wrong_order_median': record['identity_minus_wrong_order_median'],
            'distinct_center_count': record['distinct_center_count'],
            'distinct_assignment_count': unique, 'wrong_order_distinct_count': record['wrong_order_distinct_count'],
            'identity_rank_best': lo, 'identity_rank_worst': hi,
            'identity_exact_tie_count': record['identity_exact_tie_count'],
            'identity_equal_score_wrong_order_count': record['identity_equal_score_wrong_order_count'],
            'wrong_order_strictly_better_than_identity_count': record['wrong_order_strictly_better_than_identity_count'],
            'diagnostic_degenerate': record['diagnostic_degenerate']}


def saved_summary(rows, reference, counts):
    require(len(rows) == 24 and len(reference) == 9 and
            all([r['rank'] for r in rows if r['family_id'] == job] == [1, 2, 3] for job in JOBS),
            'Eight ordered nested TOP3 families required')
    families = []
    for index, job in enumerate(JOBS, 1):
        r = next(r for r in rows if r['family_id'] == job and r['rank'] == 1)
        families.append({'family_id': job, 'family_index': index, 'root_seed_entropy': 20261012,
            'maps': 96, 'analysis_unit': 'ONE_INDEPENDENT_SYNTHETIC_FAMILY',
            'TOP1_selected_score': r['prior_selected_score'], 'TOP1_chronological_score': r['chronological_score'],
            'TOP1_wrong_order_max_score': r['wrong_order_max_score'],
            'TOP1_identity_minus_wrong_order_max': r['identity_minus_wrong_order_max'],
            'TOP1_distinct_assignment_count': r['distinct_assignment_count'],
            'TOP1_identity_rank_best': r['identity_rank_best'], 'TOP1_identity_rank_worst': r['identity_rank_worst'],
            'TOP1_identity_exact_tie_count': r['identity_exact_tie_count'],
            'TOP1_diagnostic_degenerate': r['diagnostic_degenerate']})
    maxima = [f['TOP1_selected_score'] for f in families]
    family_controls = [f for f in families if f['TOP1_identity_minus_wrong_order_max'] is not None]
    nested_controls = [r for r in rows if r['identity_minus_wrong_order_max'] is not None]
    summary = {'schema': 'SETI_BURST_NULL_SAVED_REPORT_SUMMARY_V1', 'status': REPORT_STATUS,
        'counts': counts, 'independent_model_families': 8, 'nested_TOP3_occurrences': 24,
        'family8': families, 'synthetic_top24': rows, 'already_exposed_real_reference_top9': reference,
        'family_TOP1_selected_score_descriptive': {'minimum': min(maxima), 'median': statistics.median(maxima),
                                                  'maximum': max(maxima), 'realizations': 8},
        'family_TOP1_order_occurrence_counts': {'with_distinct_alternative': len(family_controls),
            'chronology_strictly_above_all_distinct_alternatives': sum(f['TOP1_identity_minus_wrong_order_max'] > 0 for f in family_controls),
            'chronology_equal_to_best_distinct_alternative': sum(f['TOP1_identity_minus_wrong_order_max'] == 0 for f in family_controls),
            'chronology_below_best_distinct_alternative': sum(f['TOP1_identity_minus_wrong_order_max'] < 0 for f in family_controls),
            'degenerate_without_alternative': 8 - len(family_controls)},
        'nested_TOP3_order_occurrence_counts_not_independent': {'with_distinct_alternative': len(nested_controls),
            'chronology_strictly_above_all_distinct_alternatives': sum(r['identity_minus_wrong_order_max'] > 0 for r in nested_controls),
            'chronology_equal_to_best_distinct_alternative': sum(r['identity_minus_wrong_order_max'] == 0 for r in nested_controls),
            'chronology_below_best_distinct_alternative': sum(r['identity_minus_wrong_order_max'] < 0 for r in nested_controls),
            'degenerate_without_alternative': 24 - len(nested_controls)},
        'synthetic_TOP3_geometry_occurrence_counts': dict(Counter(r['geometry'] for r in rows)),
        'declared_model_only': True, 'families_and_real_references_pooled': False,
        'telescope_FAP_or_p_value': False, 'model_validity_established': False,
        'extreme_tail_calibrated': False, 'qualified_SETI_detection': False,
        'source_arrays_opened_by_renderer': False, 'scores_or_ranks_recomputed_by_renderer': False,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'}
    return families, summary


def plots(out, rows, reference):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    colors = {1: '#1765aa', 2: '#4b93c8', 3: '#8dbcde'}
    markers = {1: '*', 2: 'o', 3: '^'}
    offsets = {1: -.20, 2: 0, 3: .20}
    fig, (score_ax, gap_ax) = plt.subplots(1, 2, figsize=(14, 8), sharey=True,
                                         gridspec_kw={'width_ratios': (1, 1.25)})
    for j, job in enumerate(JOBS):
        selected = [r for r in rows if r['family_id'] == job]
        score_ax.plot([r['prior_selected_score'] for r in selected], [j + offsets[r['rank']] for r in selected],
                      color='#c6cdd3', linewidth=1, zorder=1)
        controls = [r for r in selected if r['identity_minus_wrong_order_max'] is not None]
        if controls:
            gap_ax.plot([r['identity_minus_wrong_order_max'] for r in controls],
                        [j + offsets[r['rank']] for r in controls], color='#c6cdd3', linewidth=1, zorder=1)
        for r in selected:
            rank, y = r['rank'], j + offsets[r['rank']]
            score_ax.scatter([r['prior_selected_score']], [y], color=colors[rank], marker=markers[rank],
                             s=110 if rank == 1 else 45, label=f'TOP{rank}' if j == 0 else None, zorder=3)
            if r['identity_minus_wrong_order_max'] is None:
                gap_ax.text(0, y, f'TOP{rank}: U = 1, ingen kontrol', fontsize=8, va='center')
            else:
                gap_ax.scatter([r['identity_minus_wrong_order_max']], [y], color=colors[rank],
                               marker=markers[rank], s=110 if rank == 1 else 45, zorder=3)
        ranks = '\n'.join(f"{r['rank']}: {r['identity_rank_best']}–{r['identity_rank_worst']}; U={r['distinct_assignment_count']}"
                          for r in selected)
        gap_ax.text(1.025, j, ranks, transform=gap_ax.get_yaxis_transform(), va='center', fontsize=8)
    score_ax.set_yticks(range(8), JOBS)
    score_ax.invert_yaxis()
    score_ax.set_xlabel('Valgt robust fire-rækkers box-score')
    score_ax.set_title('Hele søgens TOP1 og de to næste vindere', loc='left')
    score_ax.grid(axis='x', alpha=.18)
    score_ax.legend(loc='upper center', bbox_to_anchor=(.5, -.10), ncol=3, fontsize=9)
    gap_ax.axvline(0, color='#808080', linewidth=.8)
    gap_ax.set_xlabel('Kronologiscore − bedste forskellige alternative score')
    gap_ax.set_title('Fast rækkefølgediagnose efter vinderudvælgelse', loc='left')
    gap_ax.grid(axis='x', alpha=.18)
    gap_ax.text(1.025, -.65, 'TOP: rang; U', transform=gap_ax.get_yaxis_transform(), fontsize=8)
    fig.suptitle('Otte IID Gamma(51, 1/51)-familier · fuld burst-søgning før kontrol', fontsize=14)
    fig.text(.5, .012, 'Én uafhængig modelenhed pr. række. Tre sammenbundne vindere inden for hver familie; ingen teleskop-FAP eller halekalibrering.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .11, .95, .95))
    fig.savefig(out / 'SETI_BURST_NULL_FAMILIES_2026-10-12.png', dpi=170, bbox_inches='tight')
    plt.close(fig)

    fig, (score_ax, rank_ax) = plt.subplots(1, 2, figsize=(14, 8), sharey=True,
                                          gridspec_kw={'width_ratios': (1.8, 1)})
    labels = [f"{r['target']} #{r['rank']} · r{r['window_start_row']}–{r['window_start_row'] + 3}\n"
              f"{r['frequency_MHz_at_window_reference']:.6f} MHz · {r['drift_hz_s']:+.4f} Hz/s" for r in reference]
    ys = list(range(9))
    score_ax.barh([j - .15 for j in ys], [r['chronological_score'] for r in reference], height=.28,
                  color='#5b6070', label='Tidligere kronologiscore')
    controls = [(j, r['wrong_order_max_score']) for j, r in enumerate(reference) if r['wrong_order_max_score'] is not None]
    if controls:
        score_ax.barh([j + .15 for j, _ in controls], [v for _, v in controls], height=.28,
                      color='#b07a42', label='Bedste forskellige alternativ')
    for j, r in enumerate(reference):
        lo, hi = r['identity_rank_best'], r['identity_rank_worst']
        rank_ax.plot([lo, hi], [j, j], color='#5b6070', linewidth=4)
        rank_ax.scatter([lo, hi], [j, j], color='#5b6070', s=28, zorder=3)
        rank_ax.text(25.5, j, f"{lo}–{hi}; U={r['distinct_assignment_count']}\n{r['identity_exact_tie_count']} eksakte ties", va='center', fontsize=8)
    score_ax.set_yticks(ys, labels)
    score_ax.invert_yaxis()
    score_ax.set_xlabel('Tidligere robust fire-rækkers box-score')
    score_ax.set_title('Eksponeret reference · ingen ny datakørsel', loc='left')
    score_ax.legend(loc='upper center', bbox_to_anchor=(.5, -.10), fontsize=9)
    rank_ax.set_xlim(.5, 34)
    rank_ax.set_xticks((1, 6, 12, 18, 24))
    rank_ax.set_xlabel('Eksakt rang blandt forskellige centervektorer')
    rank_ax.set_title('Tidligere fast-tuple-kontrol', loc='left')
    rank_ax.grid(axis='x', alpha=.18)
    fig.suptitle('Ni tidligere datavindere · separat, allerede eksponeret reference', fontsize=14)
    fig.text(.5, .012, 'Tre OFF-scanninger i ét historisk besøg. Reference og støjfamilier sammenlægges ikke; ingen nye gentagelser eller kalibreret signifikans.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .11, 1, .95))
    fig.savefig(out / 'SETI_BURST_NULL_REAL_REFERENCE_2026-10-12.png', dpi=170, bbox_inches='tight')
    plt.close(fig)


def markdown(summary, qa, scope_sha, qa_sha):
    families = summary['family8']
    scores = summary['family_TOP1_selected_score_descriptive']
    family_orders = summary['family_TOP1_order_occurrence_counts']
    nested_orders = summary['nested_TOP3_order_occurrence_counts_not_independent']
    reference = summary['already_exposed_real_reference_top9']
    lines = ['# Fuld burst-vinderudvælgelse i en fast Gamma-støjmodel · 12. oktober 2026', '',
        '**Otte uafhængige modelrealiseringer af hele den fastlåste 96-kerne burst-pilot er afsluttet og QA-kontrolleret.** '
        'Det er engineering under en angivet støjmodel, uden nye teleskopobservationer eller teleskop-FAP.', '',
        f"Omfanget er {integer(768)} nye syntetiske kombinerede kort, {integer(3145728)} carrier-maksima og "
        f"{integer(7002390528)} korrelerede skabelonforekomster. Der er {integer(3096)} faste scoreaudits. "
        'De 24 globale model-TOP3 får 384 fysiske række/center-matrixled og 576 permutationsscoreforekomster. '
        'Antal beregninger er ikke antal uafhængige tests.', '',
        f"De otte familiers valgte TOP1-score har minimum {number(scores['minimum'])}, median {number(scores['median'])} "
        f"og maksimum {number(scores['maximum'])}. I {family_orders['chronology_strictly_above_all_distinct_alternatives']} af de otte familier "
        'ligger TOP1-kronologien strengt over alle forskellige alternative centervektorer. '
        f"{family_orders['chronology_equal_to_best_distinct_alternative']} deler den bedste alternative score, "
        f"{family_orders['chronology_below_best_distinct_alternative']} ligger under et alternativ, og "
        f"{family_orders['degenerate_without_alternative']} har kun identitetens vektor. "
        'Dette er modelbetingede forekomstoptællinger, ikke sandsynligheder eller signifikans.', '',
        '## Otte familier som analyse-enheder', '',
        '| Familie | Valgt TOP1-score | Rekonstrueret kronologi | Bedste forskellige alternativ | Forskel | Eksakt rang | U | Eksakte ties |',
        '|---|---:|---:|---:|---:|---|---:|---:|']
    for f in families:
        lines.append(f"| {f['family_id']} | {number(f['TOP1_selected_score'])} | {number(f['TOP1_chronological_score'])} | "
                     f"{number(f['TOP1_wrong_order_max_score'])} | {number(f['TOP1_identity_minus_wrong_order_max'])} | "
                     f"{f['TOP1_identity_rank_best']}–{f['TOP1_identity_rank_worst']} | {f['TOP1_distinct_assignment_count']} | "
                     f"{f['TOP1_identity_exact_tie_count']} |")
    lines += ['', 'TOP2 og TOP3 er sammenbundne vindere inden for samme familie. Figuren viser alle tre for hver af de otte rækker; '
              'den reducerer dem ikke til 24 uafhængige replikater. Alle vindende tuples, scorer, gaps, geometrityper, U og ties er bevaret i SYNTHETIC_TOP24.csv.', '',
              f"Blandt de 24 sammenbundne TOP3-forekomster ligger kronologien strengt over alle forskellige alternativer i "
              f"{nested_orders['chronology_strictly_above_all_distinct_alternatives']}, deler den største alternative score i "
              f"{nested_orders['chronology_equal_to_best_distinct_alternative']} og ligger under et alternativ i "
              f"{nested_orders['chronology_below_best_distinct_alternative']}. "
              f"{nested_orders['degenerate_without_alternative']} forekomster er degenererede. Disse optællinger er beskrivende inden for otte familier.", '',
              '## Hvad der er gentaget under modellen', '',
              'Råeffektcellerne genereres IID Gamma med formparameter 51, skala 1/51 og middelværdi 1. '
              'Modellen og frøene er fastlagt før nye værdier og er ikke tilpasset de eksisterende datavindere. '
              'Tidssampling gange absolut kanalbredde er numerisk 51 i den kopierede geometri; det fastslår hverken teleskopets frihedsgrader eller modellens gyldighed. '
              'Instrumentrespons, spektrale og tidslige korrelationer, radioforstyrrelser og kildevariabilitet modelleres ikke.', '',
              'Hver familie har 96 særskilte domæner i native170–172, q = 4 + 8k, k = 0…31. '
              'SeedSequence(20261012, spawn_key=(familieindeks, domæneindeks)) med PCG64 bestemmer ét Gamma-kald pr. domæne: '
              '16×12096 float64-værdier og derefter én little-endian float32-konvertering. Der er ingen redraw, klipning, fravalg eller ændring af frø efter udfald. '
              'Hele råcroppens SHA256, starttilstand og alle 16 rækkehashes bevares. Koordinaterne er kopieret søgegeometri og er mærket SYNTHETIC_ENGINEERING, uden lånt observationstidspunkt.', '',
              'Full16-rækkemedianer, median501-residual, MAD og winsoriseret lokation genestimeres efter float32-konverteringen én gang pr. modelkerne. '
              'Søgningen bevarer 4096 carriers, 4000 halo-kanaler på hver side, syv fire-rækkers vinduer med start 0,2,…,12, 159 driftsværdier −4…+4 Hz/s og bredder 1/3. '
              'Hver carrier får sit kombinerede maksimum, og de globale TOP3 vælges som de første tre i TOP20 med den oprindelige rangering og afstand større end tre kanaler. '
              'Hele den eksisterende 96-kerne burst-pilot gentages; dette er ikke hele den bredere ordinary16-søgning eller ny astronomisk frekvensdækning.', '',
              'Først efter denne udvælgelse afprøves alle 24 centerkanaltilordninger inklusive identiteten. Fysiske rækker og deres normalisering holdes fast. '
              'Faktiske afrundede centervektorer deduplikeres med første leksikografiske repræsentant. Identitetens hele vektorklasse udelades fra alternative maksimum og median. '
              'U = 1 giver ingen rækkefølgeinformation og udefinerede alternative scorer/gaps. Rangen bruger eksakt lighed uden epsilon blandt forskellige vektorer; '
              'antal eksakte ties omfatter identiteten. Rang og U vises hver for sig og er ikke en pseudo-p-værdi. Bredde 3 kan give korrelerede, overlappende boxe.', '',
              '## Separat, allerede eksponeret datareference', '',
              'De ni tidligere datavindere vises i en særskilt figur og REAL_REFERENCE_TOP9.csv. De kommer fra tre OFF-scanninger mod HIP97319, HIP97461 og HIP97663 i ét historisk besøg, '
              'én scanning pr. target. Referencens scorer og rækkefølgediagnoser læses fra de autentificerede tidligere JSON/CSV-resultater; de beregnes ikke igen. '
              'Disse ni var allerede eksponeret og udvalgt over drift, vindue, bredde, carrier og global rang. De er hverken nye gentagelser, modelreplikater eller en kalibreret testmængde. '
              'Referenceværdier og syntetiske familier sammenlægges ikke.', '',
              'Den tidligere fast-tuple-kontrol sammenlignede kronologien med alternative tilordninger efter udvælgelsen. '
              'Denne engineeringfase gentager også hele vinderudvælgelsen med ny full16-normalisering under den erklærede Gamma-model. '
              'Dermed bliver udvælgelsesfordelen synlig under modellen. Kronologien var optimeret over drift, vindue og bredde, mens de fleste alternative tilordninger ikke følger lineære frekvensbaner. '
              'En god ordensrang er fortsat ikke uafhængig støtte for en lineær himmelkilde.', '',
              '## QA og bevaring', '',
              f"Der er {summary['distinct_winning_model_cores']} forskellige TOP3-vindende modelkerner. Deres fulde råcrop er gemt. "
              'QA rekonstruerer median501, full16-MAD og lokation uafhængigt for hver af disse vindende kerner fra råcroppen og kontrollerer de 24 valgte scorer. '
              'Alle 3096 scoreauditforekomster kontrolleres fra deres lokale råkapsler. I auditkerner uden for de gemte TOP3-vindende domæner genbruges de hashbundne kernetermer; fuld MAD/lokation er betinget for disse auditkerner. '
              'Modelstreamen kan afspilles fra det samme fastlåste frø for hash- og råmedianverifikation. Sådan byteverifikation giver ingen ekstra replikater.', '',
              'QA kontrollerer alle kortidentiteter, carrier-rækker, geometri, gyldighedstællere og den globale TOP20/TOP3-rangering. '
              'Den genmaksimerer ikke hele søgegitteret og hævder ikke uafhængig genberegning af alle syv milliarder skabelonscorer. '
              'Pakken bevarer alle nye kort, normaliseringer, audit- og ordenskapsler, vindende råcrop, kode, scope, reviews og receipts. '
              'Øvrige fulde modelcroppes bytes er frø-/versionsreproducerbare, men er ikke alle gemt. Gamle referencearrays og H5-kilder indgår ikke.', '',
              f"QA: `{qa['status']}`. Scope SHA256: `{scope_sha}`. QA-receipt SHA256: `{qa_sha}`.", '',
              '## Videnskabelige grænser', '',
              'Otte uafhængige familier kan ikke kalibrere ekstreme haler. Selv en større modelbank ville kun kalibrere den dokumenterede model, '
              'ikke bevise at teleskopets støj eller radioforstyrrelser følger den. Ingen score, gap, rang, forekomstoptælling eller sammenligning med de ni referencer '
              'omregnes til teleskop-p, FAP, kalibreret SNR, sigma eller signifikans. Ingen ny tærskel, veto, kildeklassifikation eller SETI-kvalifikation etableres. '
              'Original A/B forbliver FAIL_CLOSED; beskyttede 2016-paneler og lukkede 2019-transportforløb åbnes ikke.', '',
              'Grænserne er 600 CPU-s, 900 wall-s og 2 GiB pr. primærfamilie; højst to samtidig og 4 GiB samlet. '
              'QA har 600 CPU-s; rapport og pakning ligger inden for hver sin 200 CPU-s-allokering. '
              'Primæroutput er højst 40 MiB pr. familie og 320 MiB samlet, arbejdsplads 8 GiB og ZIP 200 MiB. '
              'Faseallokeringen på 6000 CPU-s er en konservativ arbejdsreservation, ikke en abonnementsgrænse eller nulstilling af gamle reservationer. '
              'Receipt-målte proceskomponenter bevares; sessions-, API- og reviewforbrug hævdes ikke komplet målt. Ingen nye teleskoprequests og 0 DKK. '
              'Planen 7.–20. oktober og slutcheckpointet den 20. oktober består.', '',
              '![Otte syntetiske familier med sammenbundne TOP3](SETI_BURST_NULL_FAMILIES_2026-10-12.png)', '',
              '![Ni tidligere datavindere som separat eksponeret reference](SETI_BURST_NULL_REAL_REFERENCE_2026-10-12.png)', '']
    return '\n'.join(lines)


def admitted_inputs(root, scope_path, scope_sha, qa_sha, code_sha):
    """Verify text/JSON inputs before output creation. Never open a capsule."""
    own = Path(__file__).resolve()
    require(pin(root, own)['sha256'] == code_sha, 'Exact renderer source SHA required before inputs')
    require(scope_path == confined(root, BASE + '/scope.json') and digest(scope_path) == scope_sha,
            'Exact prospectively frozen scope required')
    scope = read_json(scope_path)
    require(scope['schema'] == 'SETI_FULL_BURST_IID_GAMMA_MODEL_SCOPE_V1' and set(scope['jobs']) == set(JOBS) and
            scope['model_law'] == {'distribution': 'IID Gamma', 'shape': 51.0, 'scale': 1.0 / 51.0, 'mean': 1.0,
                                  'fitted_to_observations': False, 'verified_instrument_degrees_of_freedom': False} and
            scope['rng']['root_entropy'] == 20261012 and scope['rng']['bit_generator'] == 'PCG64' and
            scope['rng']['primary_redraws'] == 0 and scope['rng']['all96_crops_generated_before_search'] is True and
            scope['independent_model_units'] == 8 and scope['TOP3_winners_independent_units'] is False and
            scope['total_maps'] == 768 and scope['total_carrier_maximum_records'] == 3145728 and
            scope['total_valid_hypothesis_records'] == 7002390528 and scope['maps_per_family'] == 96 and
            scope['core_channels'] == 4096 and scope['halo_channels'] == 4000 and
            scope['source_rows_per_scan'] == 16 and scope['raw_crop_shape'] == [16, 12096] and scope['raw_dtype'] == '<f4' and
            scope['window_start_rows'] == list(range(0, 13, 2)) and scope['widths_channels'] == [1, 3] and
            scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 159, 'exact_zero_index': 79} and
            scope['expected_counts_per_family'] == EXPECTED_PRIMARY and scope['model_only'] is True and
            scope['observational_arrays_opened'] is False and scope['new_observation'] is False and
            scope['sky_FAP_or_permutation_p_value'] is False and scope['qualified_SETI_detection'] is False and
            scope['phase_CPU_allocation_s'] == 6000 and scope['phase_CPU_split_s']['report'] == CPU_CAP,
            'Declared Gamma/full-search engineering contract differs')
    inputs = {}
    for declaration in scope['text_code_pins'] + scope['prior_reference_pins']:
        checked(root, declaration)
        require(declaration['path'] not in inputs, 'Duplicate text/reference input pin')
        inputs[declaration['path']] = declaration
    require(inputs.get(BASE + '/make_report.py') == pin(root, own), 'Renderer must be prospectively scope-pinned')
    inputs[scope_path.relative_to(root).as_posix()] = pin(root, scope_path)
    qa_path = confined(root, BASE + '/QA_RECEIPT.json')
    require(digest(qa_path) == qa_sha, 'Exact independent QA receipt SHA required')
    qa = read_json(qa_path)
    require(qa['schema'] == 'SETI_BURST_NULL_RAW_NOISE_INDEPENDENT_QA_V1' and qa['status'] == QA_STATUS and
            qa['scope_sha256'] == scope_sha and qa['qa_sha256'] == inputs[BASE + '/qa_saved.py']['sha256'] and
            qa['driver_sha256'] == inputs[BASE + '/driver.py']['sha256'] and
            qa['full_core_MAD_location_reconstructed_for_winning_cores'] is True and
            qa['full_core_MAD_location_reconstructed_for_all_maps'] is False and
            qa['other_audit_scores_conditional_on_saved_full_core_MAD_location'] is True and
            qa['model_streams_replayed_for_bit_verification'] is True and qa['independent_replicates_added_by_QA'] == 0 and
            qa['full_search_grid_recomputed'] is False and qa['actual_telescope_arrays_opened'] is False and
            qa['protected_2016_arrays_opened'] is False and qa['qualified_SETI_detection'] is False and
            qa['calibrated_telescope_SNR_FAP'] is False,
            'Exact completed independent QA/source/normalization admission differs')
    inputs[BASE + '/QA_RECEIPT.json'] = pin(root, qa_path)
    go_path = confined(root, BASE + '/ROOT_GO.json')
    inputs[BASE + '/ROOT_GO.json'] = pin(root, go_path)
    go = read_json(go_path)
    require(go['status'] == 'GO_8_FULL_IID_GAMMA_NULL_FAMILIES' and go['scope_sha256'] == scope_sha and
            go['driver_sha256'] == qa['driver_sha256'] and go['qa_sha256'] == qa['qa_sha256'],
            'Science authorization scope/code differs')
    qa_go_path = checked(root, qa['root_GO_pin'])
    require(qa_go_path.suffix == '.json' and digest(qa_go_path) == qa['root_go_sha256'], 'Exact independent QA authorization differs')
    qa_go = read_json(qa_go_path)
    require(qa_go['status'] == 'GO_INDEPENDENT_SAVED_IID_GAMMA_QA' and qa_go['scope_sha256'] == scope_sha and
            qa_go['qa_sha256'] == qa['qa_sha256'] and qa_go['driver_sha256'] == qa['driver_sha256'] and
            qa_go['job_receipt_sha256s'] == qa['job_receipt_sha256s'], 'Independent QA authorization scope/eight receipts differ')
    inputs[qa['root_GO_pin']['path']] = qa['root_GO_pin']
    receipt_pins = {p['path']: p for p in qa['producer_receipt_pins']}
    require(len(receipt_pins) == len(qa['producer_receipt_pins']) == 8 and set(qa['job_receipt_sha256s']) == set(JOBS),
            'Eight independently bound completed-family receipts required')
    rows, receipts, winning_total, winning_by_job, selected_by_job = [], [], 0, {}, {}
    aggregate_counts = {key: 0 for key in EXPECTED_PRIMARY}
    for index, job in enumerate(JOBS, 1):
        receipt_path = confined(root, BASE + '/results/' + job + '/EXECUTION_RECEIPT.json')
        receipt_pin = receipt_pins.get(receipt_path.relative_to(root).as_posix())
        require(receipt_pin is not None, 'QA omitted a family receipt')
        checked(root, receipt_pin, receipt_path)
        require(qa['job_receipt_sha256s'][job] == receipt_pin['sha256'], 'QA receipt list/dictionary differs')
        receipt = read_json(receipt_path)
        require(receipt['schema'] == 'SETI_GAMMA_NULL_FAMILY_EXECUTION_V1' and receipt['status'] == PRIMARY_STATUS and
                receipt['primary_id'] == receipt['scan_id'] == job and receipt['family_index'] == index and
                receipt['scope_sha256'] == scope_sha and receipt['driver_sha256'] == qa['driver_sha256'] and
                receipt['root_GO_pin'] == inputs[BASE + '/ROOT_GO.json'] and receipt['synthetic_role'] == 'SYNTHETIC_ENGINEERING' and
                receipt['synthetic_tstart_mjd'] == 0 and receipt['model_only'] is True and
                receipt['observational_arrays_opened'] is False and receipt['sky_FAP_or_permutation_p_value'] is False and
                receipt['qualified_SETI_detection'] is False and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED' and
                receipt['raw_crops_pre_and_post_hashes_match'] is True and receipt['primary_redraws'] == 0 and
                0 < receipt['process_CPU_seconds'] <= 600 and 0 < receipt['wall_seconds'] <= 900 and
                0 < receipt['peak_RSS_bytes'] <= RAM_CAP and receipt['runtime_versions'] == scope['runtime_versions'],
                'Completed model-family provenance/resource receipt differs')
        winning_count = receipt['counts']['winning_raw_crops']
        require(type(winning_count) is int and 1 <= winning_count <= 3 and receipt['counts'] ==
                {**EXPECTED_PRIMARY, 'winning_raw_crops': winning_count}, 'Fixed counts plus dynamic winning-core count differ')
        outputs = {p['path']: p for p in receipt['output_byte_pins']}
        require(len(outputs) == len(receipt['output_byte_pins']) == 588 + winning_count,
                'Closed model output pin count differs')
        inputs[receipt_pin['path']] = receipt_pin
        receipts.append(receipt_pin)
        def saved(name):
            path = confined(root, BASE + '/results/' + job + '/' + name)
            declaration = outputs.get(path.relative_to(root).as_posix())
            require(declaration is not None, 'Completed receipt omitted report JSON: ' + name)
            checked(root, declaration, path)
            require(qa['input_byte_pins'].get(declaration['path']) ==
                    {key: declaration[key] for key in ('bytes', 'sha256')}, 'QA did not bind exact report input')
            inputs[declaration['path']] = declaration
            return read_json(path)
        top, orders, rng_manifest, maps = (saved(name) for name in
            ('TOP3.json', 'ORDER_DIAGNOSTICS.json', 'RNG_MANIFEST.json', 'MAPS.json'))
        require(top['schema'] == 'SETI_GAMMA_NULL_GLOBAL_RANKS_V1' and top['primary_id'] == top['scan_id'] == job and
                top['synthetic_role'] == 'SYNTHETIC_ENGINEERING' and len(top['records']) == 3 and
                [r['rank'] for r in top['records']] == [1, 2, 3], 'Three ordered synthetic winners required')
        require(orders['schema'] == 'SETI_GAMMA_NULL_ORDER_DIAGNOSTICS_V1' and orders['primary_id'] == orders['scan_id'] == job and
                orders['family_index'] == index and orders['model_only'] is True and
                orders['selected_winner_diagnostic_only'] is True and orders['sky_FAP_or_permutation_p_value'] is False and
                orders['counts'] == {'order_queries': 3, 'row_center_boxes': 48, 'permutation_scores': 72} and
                [r['selected_tuple'] for r in orders['records']] == top['records'], 'Three order/winner anchors differ')
        require(rng_manifest['schema'] == 'SETI_GAMMA_NULL_CANONICAL_RAW_MANIFEST_V1' and rng_manifest['primary_id'] == job and
                rng_manifest['family_index'] == index and len(rng_manifest['records']) == 96 and
                rng_manifest['model_law'] == scope['model_law'] and rng_manifest['rng'] == scope['rng'] and
                rng_manifest['runtime_versions'] == scope['runtime_versions'] and rng_manifest['primary_redraws'] == 0 and
                rng_manifest['raw_crops_pre_and_post_hashes_match'] is True, 'Frozen RNG/raw manifest differs')
        require(maps['schema'] == 'SETI_GAMMA_NULL_COMBINED_MAPS_V1' and maps['primary_id'] == maps['scan_id'] == job and
                len(maps['records']) == 96, 'All96 saved synthetic map declarations required')
        winner_domains = {(r['native_chunk_index'], r['core_q']) for r in top['records']}
        raw_winners = [r for r in rng_manifest['records'] if r['winning_raw_capsule'] is not None]
        require(len(raw_winners) == len(winner_domains) == winning_count and
                {(r['native_chunk_index'], r['core_q']) for r in raw_winners} == winner_domains and
                all(outputs.get(r['winning_raw_capsule']['path']) == r['winning_raw_capsule'] for r in raw_winners),
                'Dynamic saved winning raw-core declaration differs')
        for record, t in zip(orders['records'], top['records']):
            require(t['primary_id'] == t['scan_id'] == job and t['family_index'] == index and
                    t['primary_target'] == 'IID_GAMMA_MODEL' and t['synthetic_role'] == 'SYNTHETIC_ENGINEERING' and
                    t['data_origin'] == 'SYNTHETIC_IID_GAMMA_MODEL' and
                    outputs.get(record['normalization']['path']) == record['normalization'] and
                    outputs.get(record['score_audit_capsule']['path']) == record['score_audit_capsule'] and
                    outputs.get(record['new_capsule']['path']) == record['new_capsule'],
                    'Synthetic identity/fixed-order capsule declarations differ')
            rows.append(order_row(record, job))
        require(qa['input_byte_pins'].get(receipt_pin['path']) ==
                {key: receipt_pin[key] for key in ('bytes', 'sha256')}, 'QA did not bind exact family receipt')
        for key in aggregate_counts:
            aggregate_counts[key] += receipt['counts'][key]
        winning_total += winning_count
        winning_by_job[job] = winning_count
        selected_by_job[job] = top['records']
    require(qa['counts'] == {**EXPECTED_QA, 'winning_raw_core_crops': winning_total,
                            'winning_full_core_preprocess_rows': winning_total * 16,
                            'winning_full_core_residual_cells': winning_total * 16 * 4096} and
            qa['winning_raw_core_crops_per_family'] == winning_by_job and qa['selected_top3'] == selected_by_job,
            'Independent QA fixed/dynamic counts and selected winners differ')
    # Old references are text/JSON only and remain exposed. No old arrays are hashed or decoded.
    old_summary_path = confined(root, PRIOR + '/delivery/SUMMARY.json')
    old_csv_path = confined(root, PRIOR + '/delivery/TOP9.csv')
    old_receipt_path = confined(root, PRIOR + '/delivery/REPORT_RECEIPT.json')
    for path in (old_summary_path, old_csv_path, old_receipt_path):
        require(inputs.get(path.relative_to(root).as_posix()) == pin(root, path), 'Old reference must be prospectively text-pinned')
    old_receipt = read_json(old_receipt_path)
    require(old_receipt['status'] == 'COMPLETE_QA_GATED_FIXED_TEMPORAL_ORDER_REPORT_AND_TWO_FIGURES',
            'Already-exposed reference report must be complete')
    old_output_pins = {p['path']: p for p in old_receipt['output_pins']}
    require(all(old_output_pins.get(path.relative_to(root).as_posix()) == pin(root, path)
                for path in (old_summary_path, old_csv_path)), 'Old reference report receipt differs')
    old_summary = read_json(old_summary_path)
    require(old_summary['status'] == old_receipt['status'] and len(old_summary['top9']) == 9 and
            old_summary['qualified_SETI_detection'] is False and
            old_summary['calibrated_SNR_FAP_or_permutation_p_value'] is False,
            'Unqualified exposed real-reference summary required')
    reference = old_summary['top9']
    with old_csv_path.open(newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    require(len(csv_rows) == 9, 'Nine separate real-reference CSV rows required')
    for csv_row, saved_row in zip(csv_rows, reference):
        for key, value in saved_row.items():
            require(csv_row.get(key) == ('' if value is None else str(value)), 'Old real-reference CSV/JSON differ')
    return scope, qa, rows, reference, aggregate_counts, winning_total, list(inputs.values()), receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--scope', default=BASE + '/scope.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--qa-sha256', help='SHA256 of the completed independent QA receipt')
    parser.add_argument('--report-sha256')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    require(args.check_only != args.run, 'Choose exactly one of --check-only or --run')
    if args.check_only:
        print('PASS_SOURCE_ONLY_GAMMA_REPORT_NO_INPUTS_NO_MODEL_OR_NUMERICAL_MODULES')
        return
    require(all(isinstance(v, str) and len(v) == 64 and all(c in '0123456789abcdef' for c in v)
                for v in (args.scope_sha256, args.qa_sha256, args.report_sha256)), 'Three exact SHA256 arguments required')
    root = args.root.resolve()
    out = confined(root, BASE + '/delivery')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Saved-JSON Gamma report wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(WALL_CAP)
    started, cpu_started, created = time.monotonic(), time.process_time(), False
    try:
        scope, qa, rows, reference, counts, winning_count, inputs, receipts = admitted_inputs(
            root, confined(root, args.scope), args.scope_sha256, args.qa_sha256, args.report_sha256)
        families, summary = saved_summary(rows, reference, counts)
        summary['distinct_winning_model_cores'] = winning_count
        summary['QA_normalization_scope'] = {'winning_full16_MAD_location_independently_reconstructed': True,
            'all_map_full16_MAD_location_independently_reconstructed': False,
            'other_audit_full16_MAD_location_conditional': True, 'same_stream_replay_adds_replicates': 0}
        out.mkdir(parents=True, exist_ok=False)
        created = True
        save_csv(out / 'FAMILY8.csv', families)
        save_csv(out / 'SYNTHETIC_TOP24.csv', rows)
        save_csv(out / 'REAL_REFERENCE_TOP9.csv', reference)
        save_json(out / 'SUMMARY.json', summary)
        with (out / 'SETI_BURST_NULL_FINAL_2026-10-12.md').open('x') as stream:
            stream.write(markdown(summary, qa, args.scope_sha256, args.qa_sha256))
        plots(out, rows, reference)
        for declaration in inputs:
            checked(root, declaration)
        outputs = [pin(root, path) for path in sorted(out.iterdir()) if path.is_file()]
        require(len(outputs) == 7 and sum(p['bytes'] for p in outputs) <= OUTPUT_CAP, 'Seven report outputs/20MiB cap differs')
        usage = {'process_CPU_seconds': time.process_time() - cpu_started,
                 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP and
                0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Report measured resource cap exceeded')
        save_json(out / 'REPORT_RECEIPT.json', {'schema': 'SETI_BURST_NULL_SAVED_REPORT_RECEIPT_V1',
            'status': REPORT_STATUS, 'report_code_sha256': args.report_sha256,
            'scope_sha256': args.scope_sha256, 'qa_receipt_sha256': args.qa_sha256,
            'producer_receipt_pins': receipts, 'input_pins': inputs, 'output_pins': outputs,
            'counts': counts, 'independent_model_families': 8, 'nested_TOP3_occurrences': 24,
            'distinct_winning_model_cores': winning_count,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'output_cap_bytes': OUTPUT_CAP, **usage, 'input_pins_unchanged_after_render': True,
            'source_arrays_opened': False, 'model_generation_or_QA_executed': False,
            'scores_ranks_or_search_grid_recomputed': False, 'prior_results_modified': False,
            'telescope_FAP_or_p_value': False, 'model_validity_established': False,
            'qualified_SETI_detection': False, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED'})
        print(REPORT_STATUS, flush=True)
    except BaseException as error:
        if created and not (out / 'REPORT_RECEIPT.json').exists():
            save_json(out / 'REPORT_RECEIPT.json', {'schema': 'SETI_BURST_NULL_SAVED_REPORT_RECEIPT_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'failure_type': type(error).__name__,
                'failure': str(error), 'scope_sha256': args.scope_sha256,
                'qa_receipt_sha256': args.qa_sha256, 'report_code_sha256': args.report_sha256})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
