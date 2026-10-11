"""Prospective JSON-only report for fixed temporal-order controls.

No HDF5/NPZ values are decoded, no detector or profile calculation is run,
and no chronological or alternative assignment is selected anew. Exact saved
numeric/QA receipt bindings gate rendering. Permutation ranks are descriptive
conditional diagnostics, not p-values, FAP or physical-origin evidence.
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
import time

for thread_variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[thread_variable] = '1'

BASE = 'analysis/burst_order_20261011'
JOBS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')
KINDS = ('first', 'midpoint', 'last', 'core_max', 'global_top3')
GEOMETRIES = ('zero_drift', 'same_center_nonzero_drift', 'repeated_centers', 'four_distinct_centers')
KIND_LABELS = {'first': 'Første kanal', 'midpoint': 'Midterkanal', 'last': 'Sidste kanal',
               'core_max': 'Kernemaksimum', 'global_top3': 'Global TOP3'}
GEOMETRY_LABELS = {'zero_drift': 'Nuldrift', 'same_center_nonzero_drift': 'Én centerkanal, drift ≠ 0',
                   'repeated_centers': '2–3 centerkanaler', 'four_distinct_centers': '4 centerkanaler'}
DIAGNOSTICS_SCHEMA = 'SETI_BURST4_TEMPORAL_ORDER_DIAGNOSTICS_V1'
DIAGNOSTICS_STATUS = 'COMPLETE_387_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
QA_STATUS = 'PASS_1161_FIXED_TEMPORAL_ORDER_QUERIES18576_ROW_CENTER_BOXES27864_PERMUTATION_SCORES9_TOP3'
REPORT_STATUS = 'COMPLETE_QA_GATED_FIXED_TEMPORAL_ORDER_REPORT_AND_TWO_FIGURES'
CPU_CAP, WALL_CAP, RAM_CAP = 600, 900, 2 * 1024**3
OUTPUT_CAP = 20 * 1024**2
EXPECTED = {'queries': 1161, 'global_TOP3_queries': 9, 'row_center_boxes': 18576,
            'permutation_scores': 27864, 'source_files': 9, 'source_decoded_rows': 144}
KEY_FIELDS = ('scan_id', 'native_chunk_index', 'core_q', 'carrier_index_in_core',
              'window_start_row', 'drift_grid_index', 'width_channels')


def require(test, message):
    if not test:
        raise ValueError(message)


def confined(root, name):
    path = (root / name).resolve()
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.is_relative_to(root), 'Confined relative project path required')
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def read_json(path):
    require(path.suffix == '.json', 'Report data inputs must be JSON')
    return json.loads(path.read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def checked(root, declaration, expected_path=None):
    path = confined(root, declaration['path'])
    require(path.suffix in ('.json', '.py', '.md', '.txt') and
            (expected_path is None or path == expected_path) and pin(root, path) == declaration,
            'Exact saved JSON/code pin differs: ' + declaration['path'])
    return path


def save_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def save_csv(path, records):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def number(value, digits=6):
    return 'ikke defineret' if value is None else f'{value:.{digits}g}'


def geometry(record):
    # The zero-drift stratum is separate from other rounding degeneracy.
    centers = record['centers']
    require(isinstance(centers, list) and len(centers) == 4 and
            all(type(c) is int for c in centers), 'Four saved rounded center channels required')
    unique = len(set(centers))
    require(record['stationary_centers'] == (unique == 1) and record['duplicate_centers'] == (unique < 4),
            'Saved geometric diagnostic flags differ')
    if record['selected_tuple']['drift_hz_s'] == 0:
        require(unique == 1, 'Zero drift must have one rounded center channel')
        return 'zero_drift'
    if unique == 1:
        return 'same_center_nonzero_drift'
    return 'repeated_centers' if unique < 4 else 'four_distinct_centers'


def tuple_key(record):
    t = record['selected_tuple']
    key = tuple(t[k] for k in KEY_FIELDS)
    require(record['scientific_tuple_key'] == list(key), 'Saved scientific tuple key differs')
    return key


def validate_record(record):
    require(record['query_kind'] in KINDS, 'Unknown frozen winning-query stratum')
    require(len(record['permutation_scores']) == 24 and len(record['permutation_center_vectors']) == 24,
            'All24 identity-inclusive saved center assignments required')
    require(all(math.isfinite(v) for v in record['permutation_scores']), 'Saved24 scores must be finite')
    require(math.isfinite(record['identity_score']), 'Saved identity score must be finite')
    unique = record['distinct_assignment_count']
    require(type(unique) is int and 1 <= unique <= 24 and
            len(record['distinct_center_vectors']) == len(record['distinct_scores']) ==
            len(record['distinct_representative_permutation_indices']) ==
            len(record['distinct_assignment_multiplicities']) == unique and
            sum(record['distinct_assignment_multiplicities']) == 24,
            'Saved distinct-vector occurrence count differs')
    require(record['wrong_order_distinct_count'] == unique - 1,
            'Control summaries must exclude the whole identity-vector equivalence class')
    if unique == 1:
        require(all(record[k] is None for k in ('wrong_order_max_score', 'wrong_order_median_score',
                                               'identity_minus_wrong_order_max', 'identity_minus_wrong_order_median')),
                'No distinct alternative assignment: control summaries must be null')
    else:
        require(all(math.isfinite(record[k]) for k in ('wrong_order_max_score', 'wrong_order_median_score',
                                                      'identity_minus_wrong_order_max', 'identity_minus_wrong_order_median')),
                'Distinct alternative control summaries must be finite')
    lo, hi = record['identity_rank_best'], record['identity_rank_worst']
    require(type(lo) is int and type(hi) is int and 1 <= lo <= hi <= unique and
            record['identity_exact_tie_count'] == hi - lo + 1,
            'Saved exact distinct-vector identity rank interval differs')
    require(record['diagnostic_degenerate'] == (unique == 1) and
            record['zero_drift'] == (record['selected_tuple']['drift_hz_s'] == 0) and
            record['rounded_nonzero_drift_degenerate'] == (unique == 1 and not record['zero_drift']),
            'Saved degeneracy flags differ')
    require(record['source_rows'] == record['selected_tuple']['window_source_rows'],
            'Fixed physical source-row identity differs')
    require(record['prior_primary_score'] == record['selected_tuple']['score'], 'Prior selected score differs')
    return geometry(record)


def saved_tables(records):
    """Group saved occurrences and diagnostic ranks; no score is recomputed."""
    geometry_by_id = {r['occurrence_id']: validate_record(r) for r in records}
    keys = [tuple_key(r) for r in records]
    frequencies = Counter(keys)
    ids = {key: index + 1 for index, key in enumerate(dict.fromkeys(keys))}
    audit_rows = []
    for record, key in zip(records, keys):
        t = record['selected_tuple']
        require(record['scientific_tuple_multiplicity'] == frequencies[key],
                'Saved scientific tuple occurrence multiplicity differs')
        audit_rows.append({'primary_id': t['primary_id'], 'target': t['primary_target'],
            'query_id': record['query_id'], 'query_kind': record['query_kind'],
            'geometry': geometry_by_id[record['occurrence_id']],
            'native_chunk_index': t['native_chunk_index'], 'core_q': t['core_q'],
            'source_reference_channel': t['source_reference_channel'],
            'window_start_row': t['window_start_row'], 'width_channels': t['width_channels'],
            'frequency_MHz_at_window_reference': t['frequency_hz_at_window_reference'] / 1e6,
            'drift_hz_s': t['drift_hz_s'], 'chronological_score': record['identity_score'],
            'prior_selected_score': record['prior_primary_score'],
            'identity_minus_prior_selected_score': record['identity_minus_prior_primary_score'],
            'wrong_order_max_score': record['wrong_order_max_score'],
            'wrong_order_median_score': record['wrong_order_median_score'],
            'identity_minus_wrong_order_max': record['identity_minus_wrong_order_max'],
            'identity_minus_wrong_order_median': record['identity_minus_wrong_order_median'],
            'distinct_assignment_count': record['distinct_assignment_count'],
            'wrong_order_distinct_count': record['wrong_order_distinct_count'],
            'identity_rank_best': record['identity_rank_best'], 'identity_rank_worst': record['identity_rank_worst'],
            'identity_exact_tie_count': record['identity_exact_tie_count'],
            'identity_equal_score_wrong_order_count': record['identity_equal_score_wrong_order_count'],
            'wrong_order_strictly_better_than_identity_count': record['wrong_order_strictly_better_than_identity_count'],
            'distinct_center_count': record['distinct_center_count'],
            'diagnostic_degenerate': record['diagnostic_degenerate'],
            'scientific_tuple_group': ids[key], 'scientific_tuple_group_occurrences': frequencies[key]})
    hist = Counter((row['target'], row['query_kind'], row['geometry'], row['distinct_assignment_count'],
                    row['identity_rank_best'], row['identity_rank_worst'], row['identity_exact_tie_count'])
                   for row in audit_rows)
    histogram_rows = [dict(zip(('target', 'query_kind', 'geometry', 'distinct_assignment_count',
                                'identity_rank_best', 'identity_rank_worst', 'identity_exact_tie_count'), key),
                           occurrence_count=count, has_distinct_alternative=(key[3] > 1))
                      for key, count in sorted(hist.items())]
    top_records = [r for job in JOBS for r in records
                   if r['selected_tuple']['primary_id'] == job and r['query_kind'] == 'global_top3']
    require(len(top_records) == 9 and
            all([r['selected_tuple']['rank'] for r in top_records if r['selected_tuple']['primary_id'] == job]
                == [1, 2, 3] for job in JOBS), 'Exactly nine ordered original TOP3 occurrences required')
    top_rows = []
    for record in top_records:
        row = next(row for row in audit_rows if row['primary_id'] == record['selected_tuple']['primary_id']
                   and row['query_id'] == record['query_id'])
        top_rows.append({'target': row['target'], 'rank': record['selected_tuple']['rank'],
                        **{key: value for key, value in row.items() if key not in ('target', 'primary_id', 'query_id')}})
    summary = {'query_occurrences': len(records), 'scientific_tuple_groups': len(frequencies),
               'scientific_tuple_groups_with_repeated_occurrences': sum(count > 1 for count in frequencies.values()),
               'extra_occurrences_of_existing_scientific_tuples': sum(count - 1 for count in frequencies.values()),
               'query_kind_occurrence_counts': dict(Counter(r['query_kind'] for r in records)),
               'geometry_occurrence_counts': {g: sum(v == g for v in geometry_by_id.values()) for g in GEOMETRIES},
               'top9': top_rows, 'stratified_histogram_counts': histogram_rows}
    return audit_rows, top_rows, histogram_rows, summary


def plots(out, top_rows, audit_rows):
    """Draw saved diagnostic scores and counts without scientific recomputation."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, (score_ax, rank_ax) = plt.subplots(1, 2, figsize=(14, 7.8), sharey=True,
                                            gridspec_kw={'width_ratios': (1.8, 1)})
    labels = [f"{r['target']} #{r['rank']} · r{r['window_start_row']}–{r['window_start_row'] + 3}\n"
              f"{r['frequency_MHz_at_window_reference']:.6f} MHz · {r['drift_hz_s']:+.4f} Hz/s"
              for r in top_rows]
    y = list(range(9))
    score_ax.barh([j - .15 for j in y], [r['chronological_score'] for r in top_rows], height=.28,
                  color='#1765aa', label='Kronologisk orden')
    controls = [(j, r['wrong_order_max_score']) for j, r in enumerate(top_rows)
                if r['wrong_order_max_score'] is not None]
    if controls:
        score_ax.barh([j + .15 for j, _ in controls], [v for _, v in controls], height=.28,
                      color='#ca6a32', label='Største forskellige alternativ')
    for j, row in enumerate(top_rows):
        if row['wrong_order_max_score'] is None:
            score_ax.text(0, j + .15, 'ingen forskellig alternativ vektor', fontsize=8, va='center')
        lo, hi, unique = row['identity_rank_best'], row['identity_rank_worst'], row['distinct_assignment_count']
        rank_ax.plot([lo, hi], [j, j], color='#1765aa', linewidth=4)
        rank_ax.scatter([lo, hi], [j, j], color='#1765aa', s=28, zorder=3)
        rank_ax.text(25.5, j, f"{lo}–{hi} / {unique}\n{row['identity_exact_tie_count']} eksakte ties", va='center', fontsize=8)
    score_ax.set_yticks(y, labels)
    score_ax.invert_yaxis()
    score_ax.axvline(0, color='#808080', linewidth=.6)
    score_ax.set_xlabel('Gemt robust fire-rækkers box-score')
    score_ax.set_title('Kronologi og maksimal fast alternativ tilordning', loc='left')
    score_ax.legend(loc='upper center', bbox_to_anchor=(.5, -.10), fontsize=9, ncol=1)
    rank_ax.set_xlim(.5, 34)
    rank_ax.set_xticks((1, 6, 12, 18, 24))
    rank_ax.set_xlabel('Eksakt ranginterval blandt forskellige centervektorer')
    rank_ax.set_title('Kronologiens rang og eksakte ties', loc='left')
    rank_ax.grid(axis='x', alpha=.2)
    fig.suptitle('Ni tidligere udvalgte OFF-TOP3: faste rækkefølgediagnoser', fontsize=14)
    fig.text(.5, .01, '24 permutationer inkluderer identiteten. U = 1 giver ingen ordensinformation. Rang er ikke p-værdi eller bevis for himmeloprindelse.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .10, 1, .95))
    fig.savefig(out / 'SETI_BURST_ORDER_TOP9_2026-10-11.png', dpi=170, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(5, 4, figsize=(16, 13), sharex=True)
    bins = list(range(1, 25))
    for i, kind in enumerate(KINDS):
        for j, geom in enumerate(GEOMETRIES):
            ax = axes[i, j]
            cases = [r for r in audit_rows if r['query_kind'] == kind and r['geometry'] == geom]
            degenerate = geom in GEOMETRIES[:2]
            counts = Counter(r['identity_rank_best'] for r in cases) if not degenerate else Counter()
            if not degenerate:
                ax.bar(bins, [counts[k] for k in bins], width=.85, color='#1765aa')
            ax.set_title(f"{GEOMETRY_LABELS[geom]} · n = {len(cases)}", fontsize=9)
            ax.set_xlim(.5, 24.5)
            ax.set_xticks((1, 6, 12, 18, 24))
            if j == 0:
                ax.set_ylabel(KIND_LABELS[kind] + '\nAntal auditforekomster', fontsize=9)
            if i == 4:
                ax.set_xlabel('Bedste eksakte rang', fontsize=9)
            if not cases:
                ax.text(.5, .5, 'ingen forekomster', transform=ax.transAxes, ha='center', va='center', fontsize=8)
            elif degenerate:
                ax.text(.5, .5, f'{len(cases)} degenererede forekomster\nU = 1; ingen forskellig kontrol\nintet ranghistogram', transform=ax.transAxes,
                        ha='center', va='center', fontsize=8)
    fig.suptitle('Alle 1.161 vindertuple-audits: beskrivende rangoptællinger i faste strata', fontsize=14)
    fig.text(.5, .008, 'Ikke tilfældige eller uafhængige forespørgsler. Gentagne videnskabelige tuples tælles som forekomster; detaljer og ties findes i CSV.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .035, 1, .96))
    fig.savefig(out / 'SETI_BURST_ORDER_STRATA_2026-10-11.png', dpi=170, bbox_inches='tight')
    plt.close(fig)


def admitted_inputs(root, scope_path, scope_sha, qa_sha, code_sha):
    """Authenticate saved JSON/text only; raw/capsule byte pins remain QA's remit."""
    own_path = Path(__file__).resolve()
    require(pin(root, own_path)['sha256'] == code_sha, 'Exact renderer source SHA256 required before inputs')
    require(scope_path == confined(root, BASE + '/scope.json') and digest(scope_path) == scope_sha,
            'Exact prospective scope required')
    scope = read_json(scope_path)
    require(scope['schema'] == 'SETI_BURST4_TEMPORAL_ORDER_SCOPE_V1' and
            set(scope['jobs']) == set(JOBS) and scope['total_queries'] == 1161 and
            scope['center_assignments_per_query'] == 24 and scope['rank_tie_epsilon'] == 0 and
            scope['scientific_tuple_key_fields'] == list(KEY_FIELDS) and
            scope['new_detector_grid'] is False and scope['new_normalization_estimation'] is False and
            scope['calibrated_SNR_FAP_or_permutation_p_value'] is False and
            scope['CPU_cap_s_per_job'] == CPU_CAP and scope['wall_cap_s_per_job'] == WALL_CAP and
            scope['memory_cap_bytes_per_job'] == RAM_CAP and len(scope['source_compacts']) == 9,
            'Frozen scientific/resource scope differs')
    inputs = {record['path']: record for record in scope['text_code_pins']}
    require(len(inputs) == len(scope['text_code_pins']) and inputs.get(BASE + '/make_report.py') == pin(root, own_path),
            'Renderer must be prospectively scope-pinned')
    for declaration in inputs.values():
        checked(root, declaration)
    inputs[scope_path.relative_to(root).as_posix()] = pin(root, scope_path)
    qa_path = confined(root, BASE + '/QA_RECEIPT.json')
    require(digest(qa_path) == qa_sha, 'Exact independent QA receipt SHA256 required')
    qa = read_json(qa_path)
    expected_qa_counts = {**EXPECTED,
        'unique_scientific_tuples': sum(len(scope['jobs'][job]['scientific_tuple_groups']) for job in JOBS),
        'duplicate_scientific_tuple_occurrences': sum(387 - len(scope['jobs'][job]['scientific_tuple_groups']) for job in JOBS)}
    require(qa['schema'] == 'SETI_BURST4_TEMPORAL_ORDER_INDEPENDENT_QA_V1' and
            qa['status'] == QA_STATUS and qa['scope_sha256'] == scope_sha and qa['counts'] == expected_qa_counts and
            qa['qa_sha256'] == inputs[BASE + '/qa_saved.py']['sha256'] and
            qa['driver_sha256'] == inputs[BASE + '/driver.py']['sha256'] and
            qa['normalization_conditional_on_saved_full16_core_terms'] is True and
            qa['full_core_MAD_location_independently_refiltered'] is False and
            qa['physical_row_normalization_reassigned'] is False and qa['full_search_grid_recomputed'] is False and
            qa['qualified_SETI_detection'] is False and qa['calibrated_SNR_FAP'] is False and
            qa['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED',
            'Independent QA/source/normalization admission differs')
    require(type(qa['selected_top3']) is dict and qa['selected_top3'] ==
            {job: scope['jobs'][job]['TOP3'] for job in JOBS},
            'QA must bind exact nine original selected tuples by primary ID')
    inputs[BASE + '/QA_RECEIPT.json'] = pin(root, qa_path)
    go_path = confined(root, BASE + '/ROOT_GO.json')
    require(digest(go_path) == qa['root_go_sha256'], 'Exact science authorization receipt differs')
    go = read_json(go_path)
    require(go['status'] == 'GO_1161_FIXED_BURST4_TEMPORAL_ORDER_QUERIES' and
            go['scope_sha256'] == scope_sha and go['qa_sha256'] == qa['qa_sha256'] and
            go['driver_sha256'] == qa['driver_sha256'], 'Science authorization scope/code differs')
    inputs[BASE + '/ROOT_GO.json'] = pin(root, go_path)
    require(qa['root_GO_pin'] == inputs[BASE + '/ROOT_GO.json'] and
            qa['before_and_after_input_pins'] == qa['input_byte_pins'], 'QA authorization/input continuity differs')
    producer_pins = {r['path']: r for r in qa['producer_receipt_pins']}
    require(len(producer_pins) == len(qa['producer_receipt_pins']) == 3 and
            set(qa['job_receipt_sha256s']) == set(JOBS), 'Exactly three independent-QA-bound receipts required')
    records, execution_receipts = [], []
    for job in JOBS:
        item = scope['jobs'][job]
        receipt_path = confined(root, BASE + '/results/' + job + '/EXECUTION_RECEIPT.json')
        declaration = producer_pins.get(receipt_path.relative_to(root).as_posix())
        require(declaration is not None, 'Independent QA omitted a completed primary receipt')
        checked(root, declaration, receipt_path)
        require(declaration['sha256'] == qa['job_receipt_sha256s'][job], 'QA receipt list/dictionary differs')
        receipt = read_json(receipt_path)
        fixed_counts = {key: value // 3 for key, value in EXPECTED.items()}
        expected_counts = {**fixed_counts, 'unique_scientific_tuples': len(item['scientific_tuple_groups']),
                           'duplicate_scientific_tuple_occurrences': 387 - len(item['scientific_tuple_groups'])}
        require(receipt['schema'] == 'SETI_BURST4_TEMPORAL_ORDER_EXECUTION_V1' and
                receipt['status'] == DIAGNOSTICS_STATUS and receipt['primary_id'] == job and
                receipt['scan_id'] == item['scan_id'] and receipt['scope_sha256'] == scope_sha and
                receipt['driver_sha256'] == qa['driver_sha256'] and receipt['counts'] == expected_counts and
                receipt['root_GO_pin'] == inputs[BASE + '/ROOT_GO.json'] and
                receipt['new_grid_or_normalization_estimation'] is False and
                receipt['permutation_p_value'] is False and receipt['qualified_SETI_detection'] is False and
                0 < receipt['process_CPU_seconds'] <= CPU_CAP and 0 < receipt['wall_seconds'] <= WALL_CAP and
                0 < receipt['peak_RSS_bytes'] <= RAM_CAP, 'Completed saved control receipt differs')
        inputs[declaration['path']] = declaration
        execution_receipts.append(declaration)
        diagnostic_path = confined(root, BASE + '/results/' + job + '/QUERY_DIAGNOSTICS.json')
        outputs = {r['path']: r for r in receipt['output_byte_pins']}
        diagnostic_pin = outputs.get(diagnostic_path.relative_to(root).as_posix())
        require(len(outputs) == len(receipt['output_byte_pins']) == 388 and diagnostic_pin is not None,
                'Completed receipt must bind one diagnostics JSON and387 capsule pins')
        checked(root, diagnostic_pin, diagnostic_path)
        for saved_pin in (declaration, diagnostic_pin):
            require(qa['input_byte_pins'].get(saved_pin['path']) ==
                    {key: saved_pin[key] for key in ('bytes', 'sha256')},
                    'Independent QA did not bind this exact report input')
        diagnostic = read_json(diagnostic_path)
        require(diagnostic['schema'] == DIAGNOSTICS_SCHEMA and diagnostic['status'] == DIAGNOSTICS_STATUS and
                diagnostic['primary_id'] == job and diagnostic['scan_id'] == item['scan_id'] and
                diagnostic['primary_target'] == item['primary_target'] and diagnostic['counts'] == expected_counts and
                diagnostic['selected_winner_diagnostic_only'] is True and diagnostic['permutation_p_value'] is False and
                diagnostic['normalization_conditioned_on_saved_full16_parameters'] is True and
                len(diagnostic['records']) == len(item['queries']) == 387,
                'Complete fixed-query diagnostic JSON differs')
        group_by_query = {query_id: group for group in item['scientific_tuple_groups']
                          for query_id in group['query_ids']}
        require(len(group_by_query) == 387, 'Frozen scientific tuple group query partition differs')
        for record, prior in zip(diagnostic['records'], item['queries']):
            require(record['query_id'] == prior['query_id'] and record['query_kind'] == prior['query_kind'] and
                    record['selected_tuple'] == prior['selected_tuple'] and
                    record['prior_normalization'] == prior['normalization'] and record['prior_capsule'] == prior['capsule'] and
                    outputs.get(record['new_capsule']['path']) == record['new_capsule'] and
                    record['scientific_tuple_key'] == group_by_query[record['query_id']]['scientific_tuple_key'] and
                    record['scientific_tuple_multiplicity'] == len(group_by_query[record['query_id']]['query_ids']),
                    'Saved fixed query identity/provenance differs')
            records.append({**record, 'occurrence_id': job + '/' + record['query_id']})
        require(dict(Counter(r['query_kind'] for r in diagnostic['records'])) ==
                {'first': 96, 'midpoint': 96, 'last': 96, 'core_max': 96, 'global_top3': 3},
                'Exact nonrandom winning-query strata differ')
        inputs[diagnostic_pin['path']] = diagnostic_pin
    return scope, qa, records, list(inputs.values()), execution_receipts


def markdown(summary, counts, qa, scope_sha, qa_sha):
    top = summary['top9']
    available = [r for r in top if r['wrong_order_max_score'] is not None]
    ahead = sum(r['identity_minus_wrong_order_max'] > 0 for r in available)
    tied = sum(r['identity_minus_wrong_order_max'] == 0 for r in available)
    behind = len(available) - ahead - tied
    lines = ['# Faste rækkefølgekontroller af SETI-burst4-piloten — 11. oktober 2026', '',
        f"Der er beregnet **{counts['row_center_boxes']:,} nye rækkecenter-boxforekomster**, "
        f"**{counts['queries']:,} faste 4×4-diagnosematricer** og **{counts['permutation_scores']:,} permutationsscore-forekomster**. "
        'Optællingerne er beregningsforekomster; gentagne centerkanaler og tuples betyder, at de ikke er så mange forskellige eller uafhængige målinger.', '',
        f"Blandt de ni tidligere valgte OFF-TOP3 har {len(available)} mindst én forskellig alternativ centervektor. "
        f"Kronologien ligger strengt over alle forskellige alternativer i {ahead}, deler den største score i {tied} og ligger under et alternativ i {behind}. "
        f"De resterende {9 - len(available)} er degenererede med U = 1 og giver ingen rækkefølgeinformation. "
        'Dette kvalificerer ikke et SETI-fund og giver ingen kalibreret signifikans.', '',
        'Alle 24 leksikografiske permutationer inklusive identiteten er gemt. Den fysiske rækkefølge af de fire eksponeringer og deres normalisering holdes fast; '
        'kun de fire tidligere afrundede centerkanalers tilordning til rækkerne ændres. Samme centervektor tælles én gang i kontrolmaksimum, median og rang, '
        'med første leksikografiske repræsentant. Hele identitetens vektorklasse udelades fra de forskellige alternativer.', '',
        '## Ni oprindelige TOP3', '',
        '| OFF-target / rang | Frekvens ved vinduets første midtpunkt (MHz) | Rækker / drift (Hz/s) / bredde | Kronologi | Største forskellige alternativ | Forskel | Eksakt rang / U | Eksakte ties | Geometri |',
        '|---|---:|---|---:|---:|---:|---|---:|---|']
    for r in top:
        lines.append(f"| {r['target']} #{r['rank']} | {r['frequency_MHz_at_window_reference']:.9f} | "
                     f"{r['window_start_row']}–{r['window_start_row'] + 3} / {r['drift_hz_s']:+.6f} / {r['width_channels']} | "
                     f"{number(r['chronological_score'])} | {number(r['wrong_order_max_score'])} | "
                     f"{number(r['identity_minus_wrong_order_max'])} | {r['identity_rank_best']}–{r['identity_rank_worst']} / "
                     f"{r['distinct_assignment_count']} | {r['identity_exact_tie_count']} | {GEOMETRY_LABELS[r['geometry']]} |")
    lines += ['', 'Rangen beregnes fra den gemte, rekonstruerede kronologiscore blandt forskellige faktiske centervektorer: '
              'bedste rang = 1 + antal strengt større scorer; værste rang = antal større + antal præcis ens scorer. '
              'Ties bruger eksakt numerisk lighed uden epsilon. Den oprindelige søgescore og dens afrundingsforskel er bevaret i CSV; '
              'de bruges ikke som rangens reference. U = 1 giver mekanisk rang 1, men maksimum, median og forskelle er udefinerede.', '',
              '## Hele den gemte audit', '',
              f"De {summary['query_occurrences']:,} forespørgselsforekomster repræsenterer {summary['scientific_tuple_groups']:,} forskellige videnskabelige tuples. "
              f"{summary['scientific_tuple_groups_with_repeated_occurrences']} tuplegrupper gentages, med "
              f"{summary['extra_occurrences_of_existing_scientific_tuples']} ekstra forekomster. Tupleidentiteten er scan, native-bånd, q, carrier, vinduestart, driftindeks og bredde. "
              'Alle forekomster beholdes; de er hverken tilfældigt udvalgte eller uafhængige.', '',
              '| Fast auditstratum | Nuldrift | Én centerkanal, drift ≠ 0 | 2–3 centerkanaler | 4 centerkanaler | I alt |',
              '|---|---:|---:|---:|---:|---:|']
    hist = summary['stratified_histogram_counts']
    for kind in KINDS:
        values = [sum(r['occurrence_count'] for r in hist if r['query_kind'] == kind and r['geometry'] == geom)
                  for geom in GEOMETRIES]
        lines.append('| ' + KIND_LABELS[kind] + ' | ' + ' | '.join(str(v) for v in values + [sum(values)]) + ' |')
    lines += ['', 'Hvert target bidrager med 96 første-, midter-, sidste- og kernemaksimumforespørgsler samt tre globale TOP3. '
              'Også de faste auditcarriers har tidligere vundet over vinduer, drift og bredde. Stratafiguren viser bedste eksakte rang for forekomster med en forskellig alternativ vektor; '
              'nuldrift og afrundet stationær drift vises særskilt uden ranghistogram. CSV bevarer targetstrata, værste rang, ties, U og tuplemultiplicitet.', '',
              '## Fortolkning og datagrænser', '',
              'Kontrollerne er betingede diagnoser af eksponerede, tidligere valgte vindere. Rækkerne er ikke udskiftelige under en dokumenteret nulmodel, og normalisering, '
              'kildedata og oprindelig udvælgelse genbruges. Kronologien har allerede haft fordel af drift-, vindue- og breddeudvælgelsen; de fleste alternative tilordninger '
              'danner ikke lineære frekvensbaner. En god rang er derfor ikke uafhængig støtte for en lineær himmelkilde. Bredde 3 kan give overlappende boxe, '
              'så også forskellige centervektorer er korrelerede. Ingen score, rang eller histogram omregnes til p-værdi, FAP, kalibreret SNR eller signifikans; '
              'ingen bruges som himmelkildeklassifikation eller til at afvise radioforstyrrelser.', '',
              'Der er ingen ny observation eller ny søgecoverage. De tre OFF-targets har hver ét besøg. Kontrollen bruger de ni allerede autentificerede OFF-kompakter '
              '(tre native-bånd pr. target, 144 dekodede kilderækker); de 18 eksisterende fulde H5-kildefiler for seks scans forbliver eksterne. '
              'Ingen nye masker, vetoer, driftfit eller søgegrid er indført. Beskyttede 2016-holdouts og de oprindelige A/B-grænser forbliver lukkede.', '',
              'Full16-normaliseringen er uændret og følger den fysiske række: gemte rækkemedianer, winsoriseret residual-location og MAD. QA kontrollerer kildebytes, '
              'alle 144 kilderækker, raw-identity mod de oprindelige kapsler, de lokale 501-kanalfiltre, alle 4×4-boxbidrag, alle 24 scorer, deduplikering, rang og ties. '
              'QA genberegner rækkernes rå kernemedianer, men genfiltrerer ikke hele kernens MAD/location; den del af valideringen er betinget på de autentificerede full16-termer.', '',
              f"QA: `{qa['status']}`. Scope SHA256: `{scope_sha}`. QA-receipt SHA256: `{qa_sha}`. "
              f"Største QA-afvigelse for matrix/scorer/oprindelig identity-score: {number(qa['maximum_matrix_absolute_difference'])} / "
              f"{number(qa['maximum_permutation_score_absolute_difference'])} / {number(qa['maximum_identity_vs_original_score_absolute_difference'])}.", '',
              'Prospektive grænser pr. numerisk job og QA: 600 CPU-sekunder, 900 vægsekunder og 2 GiB RAM; højst to primærjob samtidig, samlet 4 GiB. '
              'Ingen nye teleskop-HTTP-anmodninger eller betalte tjenester. Denne renderer læser gemt JSON og tekst og tegner figurer efter QA; den åbner ingen kildearrays.', '',
              '![Ni TOP3: kronologi og forskellige alternativer](SETI_BURST_ORDER_TOP9_2026-10-11.png)', '',
              '![Auditstrata: eksakte rangoptællinger og degenererede forekomster](SETI_BURST_ORDER_STRATA_2026-10-11.png)', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--scope', default=BASE + '/scope.json')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--qa-sha256')
    parser.add_argument('--report-sha256')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    require(args.check_only != args.run, 'Choose exactly one of --check-only or --run')
    if args.check_only:
        print('PASS_SOURCE_ONLY_RENDERER_NO_INPUTS_OPENED_NO_NUMERICAL_MODULES_IMPORTED')
        return
    require(all(isinstance(v, str) and len(v) == 64 and all(c in '0123456789abcdef' for c in v)
                for v in (args.scope_sha256, args.qa_sha256, args.report_sha256)), 'Three exact SHA256 arguments required')
    root = args.root.resolve()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(signum, frame):
        raise TimeoutError('JSON-only report wall cap900s reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(WALL_CAP)
    started, cpu_started = time.monotonic(), time.process_time()
    out = confined(root, BASE + '/delivery')
    created = False
    try:
        scope, qa, records, inputs, receipt_pins = admitted_inputs(
            root, confined(root, args.scope), args.scope_sha256, args.qa_sha256, args.report_sha256)
        audit, top, hist, summary = saved_tables(records)
        require(len(audit) == 1161 and len(top) == 9 and sum(r['occurrence_count'] for r in hist) == 1161,
                'Saved report occurrence counts incomplete')
        require(summary['scientific_tuple_groups'] == qa['counts']['unique_scientific_tuples'] and
                summary['extra_occurrences_of_existing_scientific_tuples'] == qa['counts']['duplicate_scientific_tuple_occurrences'],
                'Saved query grouping must reconcile independent QA')
        summary = {'schema': 'SETI_BURST4_TEMPORAL_ORDER_REPORT_SUMMARY_V1', 'status': REPORT_STATUS,
                   'counts': qa['counts'], **summary, 'all_permutations_include_identity': True,
                   'wrong_order_summary_excludes_identity_center_vector_class': True,
                   'exact_score_ties_without_epsilon': True, 'nonrandom_selected_query_occurrences': True,
                   'calibrated_SNR_FAP_or_permutation_p_value': False, 'qualified_SETI_detection': False,
                   'normalization_conditional_on_saved_full16_core_terms': True,
                   'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'source_arrays_opened': False}
        out.mkdir(parents=True, exist_ok=False)
        created = True
        save_csv(out / 'AUDIT1161.csv', audit)
        save_csv(out / 'TOP9.csv', top)
        save_csv(out / 'STRATIFIED_COUNTS.csv', hist)
        save_json(out / 'SUMMARY.json', summary)
        with (out / 'SETI_BURST_ORDER_FINAL_2026-10-11.md').open('x') as stream:
            stream.write(markdown(summary, qa['counts'], qa, args.scope_sha256, args.qa_sha256))
        plots(out, top, audit)
        for declaration in inputs:
            checked(root, declaration)
        outputs = [pin(root, path) for path in sorted(out.iterdir()) if path.is_file()]
        require(len(outputs) == 7 and sum(r['bytes'] for r in outputs) <= OUTPUT_CAP, 'Seven report outputs/20MiB cap differs')
        usage = {'process_CPU_seconds': time.process_time() - cpu_started,
                 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['process_CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP and
                0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Report resource caps exceeded')
        save_json(out / 'REPORT_RECEIPT.json', {'schema': 'SETI_BURST4_TEMPORAL_ORDER_REPORT_RECEIPT_V1',
                  'status': REPORT_STATUS, 'report_code_sha256': args.report_sha256,
                  'scope_sha256': args.scope_sha256, 'qa_receipt_sha256': args.qa_sha256,
                  'producer_receipt_pins': receipt_pins, 'input_pins': inputs, 'output_pins': outputs,
                  'counts': qa['counts'], 'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP,
                  'memory_cap_bytes': RAM_CAP, 'output_cap_bytes': OUTPUT_CAP, **usage,
                  'source_arrays_opened': False, 'scientific_scores_recomputed': False,
                  'new_detector_or_grid_run': False, 'qualified_SETI_detection': False,
                  'calibrated_SNR_FAP_or_permutation_p_value': False, 'input_pins_unchanged_after_render': True})
        print(REPORT_STATUS, flush=True)
    except BaseException as error:
        if created and not (out / 'REPORT_RECEIPT.json').exists():
            save_json(out / 'REPORT_RECEIPT.json', {'schema': 'SETI_BURST4_TEMPORAL_ORDER_REPORT_RECEIPT_V1',
                      'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'failure_type': type(error).__name__,
                      'failure': str(error), 'report_code_sha256': args.report_sha256,
                      'scope_sha256': args.scope_sha256, 'qa_receipt_sha256': args.qa_sha256})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
