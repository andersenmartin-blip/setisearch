"""Independent audit of saved RFI derivations; no detector/generator execution.

Uses Decimal arithmetic and intersection of endpoint reference-frequency
intervals, independently of analyze_retained.py. Saved scores are checked for
faithful transcription, not recomputed from raw observations.
"""
import ast
import csv
import hashlib
import json
import math
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
getcontext().prec = 45
D = lambda x: Decimal(str(x))
FAILURES = []
MAX_DIFFERENCE = 0.0
NUMERIC_COMPARISONS = 0
EXPECTED_CODE_HASHES = {
    'pilot_engine_20261008/detector.py': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'pilot_controls_20261008/generator.py': '3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693',
    'pilot_controls_20261008/control_contract.json': '44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def check(ok, label):
    if not ok:
        FAILURES.append(label)


def same(actual, expected, label):
    global MAX_DIFFERENCE, NUMERIC_COMPARISONS
    if isinstance(expected, bool):
        if isinstance(actual, str):
            actual = {'True': True, 'False': False}.get(actual, actual)
        check(type(actual) is bool and actual == expected, label)
    elif isinstance(expected, (int, float, Decimal)):
        try:
            diff = abs(float(actual) - float(expected))
            NUMERIC_COMPARISONS += 1
            MAX_DIFFERENCE = max(MAX_DIFFERENCE, diff)
            # Floating subtraction of GHz reference frequencies accounts for
            # sub-microchannel disagreement with 45-digit Decimal arithmetic.
            check(math.isfinite(float(actual)) and diff <= 0.000001, label)
        except (ValueError, TypeError):
            check(False, label)
    else:
        check(actual == expected, label)


def compare_rows(actual, expected, label):
    check(len(actual) == len(expected), label + ': row count')
    for i, (a, e) in enumerate(zip(actual, expected)):
        check(set(a) == set(e), f'{label}[{i}]: field set')
        for k, v in e.items():
            same(a.get(k), v, f'{label}[{i}].{k}')


def global_winner(meta, case_dir):
    # NPZ loading only; independently select first maximum via Python max.
    with np.load(case_dir / meta['array_file'], allow_pickle=False) as saved:
        scores = saved['maximum_robust_box_track_score']
        check(all(math.isfinite(float(x)) for x in scores),
              meta['scan_id'] + ': finite saved score map')
        index = max(range(len(scores)), key=lambda n: float(scores[n]))
        return {
            'scan_id': meta['scan_id'], 'role': meta['role'],
            'maximum_retained_score': float(scores[index]),
            'reference_carrier_index': index,
            'reference_frequency_hz': float(saved['frequency_hz_at_tref'][index]),
            'winning_drift_hz_s': float(saved['winning_drift_hz_s'][index]),
            'winning_width_channels': int(saved['winning_width_channels'][index]),
        }


def main():
    evidence = read(OUT / 'RFI_GEOMETRY_EVIDENCE.json')
    contract = read(ROOT / 'pilot_controls_20261008/control_contract.json')
    widths = contract['box_width_bank']
    check(widths == [1, 3, 9, 33], 'original width bank')
    for name, digest in EXPECTED_CODE_HASHES.items():
        check(sha(ROOT / name) == digest, 'frozen code ' + name)
    check(evidence['original_code_sha256'] == EXPECTED_CODE_HASHES,
          'evidence frozen code bindings')
    source = (OUT / 'analyze_retained.py').read_text()
    imports = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    check(set(imports) <= {'csv', 'hashlib', 'json', 'pathlib', 'numpy',
                            'matplotlib.pyplot'}, 'analysis import allowlist')
    expected = {'survivors': [], 'OFF_comparisons': [],
                'truth_track_geometry': [], 'global_OFF_winner_compatibility': []}
    interval_checks = []
    artifact_count = 0
    localized_rejected = 0
    retained_bindings = []
    for serial in (64, 65):
        case_dir = ROOT / f'results/radio_pilot_val_b_20261008/case_{serial:03d}'
        manifest = read(case_dir / 'artifact_manifest.json')
        marker = read(case_dir / 'COMMITTED.json')
        check(marker['status'] == 'COMPLETED_CASE_ONLY', 'original case completed')
        check(sha(case_dir / 'artifact_manifest.json') == marker['artifact_manifest_SHA256'],
              'original manifest bound to COMMITTED')
        for name, record in manifest.items():
            check((case_dir / name).stat().st_size == record['size_bytes'],
                  f'original length {serial}/{name}')
            check(sha(case_dir / name) == record['SHA256'],
                  f'original digest {serial}/{name}')
            artifact_count += 1
        retained_bindings.append({'case_directory': str(case_dir.relative_to(ROOT)),
                                 'artifact_manifest_sha256': sha(case_dir / 'artifact_manifest.json'),
                                 'verified_artifact_count': len(manifest), 'manifest': manifest})
        truth = read(case_dir / 'truth.json')
        definition = read(case_dir / 'case_definition.json')
        recovery = read(case_dir / 'localized_recovery.json')
        hits = read(case_dir / 'all_ON_threshold_carriers.json')
        metas = read(case_dir / 'scan_map_metadata.json')
        meta_by_id = {m['scan_id']: m for m in metas}
        globals_ = {m['scan_id']: global_winner(m, case_dir) for m in metas}
        survivors = [h for h in hits if h['disposition'] == 'SURVIVOR_EXPLORATORY']
        check(len(survivors) == (13 if serial == 64 else 1), 'original survivor count')
        check(definition['drift_hz_s'] == truth['drift_hz_s'] == -4,
              'original declared true drift')
        check(definition['intrinsic_width_channels'] == truth['intrinsic_width_channels'] == 1,
              'original intrinsic width')
        context = next(c for c in evidence['cases'] if c['case_id'] == truth['case_id'])
        same(context['survivors'], len(survivors), 'context survivors')
        same(context['original_ON_threshold_carriers'], len(hits), 'context original hits')
        check(context['localized_recovery'] == recovery, 'context exact original recovery')
        compare_rows(context['global_scan_maxima'], list(globals_.values()), 'context saved scan maxima')
        for scan in truth['active_ON_scan_ids']:
            localized = []
            for h in hits:
                if h['scan_id'] != scan:
                    continue
                scale = abs(D(h['df_hz']))
                radius = (D(2) + D(max(h['width_channels'], truth['flux_by_scan'][scan]['injection_oracle_width_channels'])) / D(2)) * scale
                mismatch = [abs(D(h['reference_frequency_hz']) - D(truth['reference_frequency_hz'])
                                + (D(h['drift_hz_s']) - D(truth['drift_hz_s'])) * D(h[t]))
                            for t in ('scan_first_time_from_tref_s', 'scan_last_time_from_tref_s')]
                if max(mismatch) <= radius:
                    localized.append(h)
            record = recovery['per_active_ON_scan'][scan]
            same(record['pre_OFF_localized_count'], len(localized), 'original localization count')
            check(all(h['disposition'] == 'OFF_MATCHED' for h in localized),
                  'every truth-localized original hit rejected')
            check(record['final_localized_count'] == 0, 'original final localized count')
            localized_rejected += len(localized)
        for h in survivors:
            check(h['scan_id'] == 'epoch1_on' and h['width_channels'] == 33,
                  'all retained survivors first ON width 33')
            on_meta = meta_by_id[h['scan_id']]
            with np.load(case_dir / on_meta['array_file'], allow_pickle=False) as saved:
                i = h['reference_carrier_index']
                for source_key, hit_key in [('maximum_robust_box_track_score', 'ON_robust_score'),
                                            ('frequency_hz_at_tref', 'reference_frequency_hz'),
                                            ('winning_drift_hz_s', 'drift_hz_s'),
                                            ('winning_width_channels', 'width_channels')]:
                    same(float(saved[source_key][i]), h[hit_key], 'hit matches saved ON winner')
            times = [D(on_meta['scan_first_time_from_tref_s']), D(on_meta['scan_last_time_from_tref_s'])]
            same(h['scan_first_time_from_tref_s'], times[0], 'hit first ON time')
            same(h['scan_last_time_from_tref_s'], times[1], 'hit last ON time')
            check(times[0] < times[1], 'nonzero ON span')
            native = abs(D(on_meta['df_hz']))
            on_f, on_d = D(h['reference_frequency_hz']), D(h['drift_hz_s'])
            true_f, true_d = D(truth['reference_frequency_hz']), D(truth['drift_hz_s'])
            # At fixed true slope, independently solve each endpoint constraint
            # for reference frequency. Incompatible intervals prove exclusion.
            centers = [on_f + (on_d - true_d) * t for t in times]
            minimax_f = (min(centers) + max(centers)) / D(2)
            minimax_error = max(abs(minimax_f - c) for c in centers) / native
            for off_width in widths:
                radius = (D(h['width_channels'] + off_width) / D(2) + D(2)) * native
                intersection_low = max(c - radius for c in centers)
                intersection_high = min(c + radius for c in centers)
                check(intersection_low > intersection_high, 'true slope excluded for each OFF width')
                interval_checks.append({'case_id': truth['case_id'], 'carrier': h['reference_carrier_index'],
                                        'OFF_width_channels': off_width,
                                        'intersection_gap_hz': float(intersection_low - intersection_high),
                                        'true_slope_reference_frequency_intervals_disjoint': intersection_low > intersection_high})
            max_radius_channels = D(h['width_channels'] + max(widths)) / D(2) + D(2)
            boundary = (D(2) * max_radius_channels * native) / (times[1] - times[0])
            original_comp = h['OFF_comparisons']
            check(len(original_comp) == 3 and {c['scan_id'] for c in original_comp} ==
                  {m['scan_id'] for m in metas if m['role'] == 'OFF'}, 'three distinct original OFF scans')
            largest_score = max(D(c['maximum_checked_score']) for c in original_comp)
            expected['survivors'].append({
                'case_id': truth['case_id'], 'carrier': h['reference_carrier_index'], 'ON_scan': h['scan_id'],
                'ON_score': D(h['ON_robust_score']), 'ON_margin_above_10': D(h['ON_robust_score']) - D(10),
                'frequency_hz_at_tref': on_f, 'drift_hz_s': on_d, 'width_channels': h['width_channels'],
                'truth_drift_difference_hz_s': on_d - true_d, 'ON_span_s': times[1] - times[0],
                'largest_OFF_tolerance_channel_widths': max_radius_channels,
                'maximum_compatible_drift_difference_hz_s': boundary,
                'drift_exclusion_margin_hz_s': abs(on_d - true_d) - boundary,
                'minimum_possible_max_endpoint_error_channel_widths': minimax_error,
                'minimum_possible_endpoint_excess_channel_widths': minimax_error - max_radius_channels,
                'truth_first_ON_error_channel_widths': (centers[0] - true_f) / native,
                'truth_last_ON_error_channel_widths': (centers[1] - true_f) / native,
                'truth_localization_tolerance_channel_widths': D(2) + D(max(h['width_channels'], truth['flux_by_scan'][h['scan_id']]['injection_oracle_width_channels'])) / D(2),
                'largest_original_compatible_OFF_score': largest_score, 'OFF_margin_below_8': D(8) - largest_score,
                'true_drift_excluded_even_with_free_frequency': True,
            })
            for c in original_comp:
                check(c['family_exhausted'] is True and c['veto'] is False and c['witness'] is None,
                      'original OFF disposition and exhaustive flag')
                check(D(c['maximum_checked_score']) < D(8) and c['checked_valid_compatible_templates'] > 0,
                      'original OFF below threshold with positive checked family')
                expected['OFF_comparisons'].append({
                    'case_id': truth['case_id'], 'carrier': h['reference_carrier_index'], 'OFF_scan': c['scan_id'],
                    'maximum_original_compatible_OFF_score': D(c['maximum_checked_score']),
                    'margin_below_8': D(8) - D(c['maximum_checked_score']),
                    'checked_valid_compatible_templates': c['checked_valid_compatible_templates'],
                    'family_exhausted': True, 'veto': False,
                })
            for m in metas:
                scan_t = [D(m[k]) for k in ('scan_first_time_from_tref_s', 'scan_last_time_from_tref_s')]
                mismatch = [((on_f + on_d * t) - (true_f + true_d * t)) / native for t in scan_t]
                expected['truth_track_geometry'].append({
                    'case_id': truth['case_id'], 'carrier': h['reference_carrier_index'], 'scan_id': m['scan_id'],
                    'role': m['role'], 'first_time_from_tref_s': scan_t[0], 'last_time_from_tref_s': scan_t[1],
                    'first_truth_error_channel_widths': mismatch[0], 'last_truth_error_channel_widths': mismatch[1],
                })
                if m['role'] == 'OFF':
                    winner = globals_[m['scan_id']]
                    off_f, off_d = D(winner['reference_frequency_hz']), D(winner['winning_drift_hz_s'])
                    endpoint_diff = [(off_f + off_d * t) - (on_f + on_d * t) for t in times]
                    tolerance = (D(h['width_channels'] + winner['winning_width_channels']) / D(2) + D(2)) * max(native, abs(D(m['df_hz'])))
                    compatible = all(abs(e) <= tolerance for e in endpoint_diff)
                    check(not compatible, 'original global OFF winning path incompatible')
                    expected['global_OFF_winner_compatibility'].append({
                        'case_id': truth['case_id'], 'carrier': h['reference_carrier_index'], 'OFF_scan': m['scan_id'],
                        'OFF_global_winner_score': D(winner['maximum_retained_score']),
                        'OFF_global_winner_frequency_hz': off_f, 'OFF_global_winner_drift_hz_s': off_d,
                        'OFF_global_winner_width_channels': winner['winning_width_channels'],
                        'first_ON_endpoint_error_channel_widths': endpoint_diff[0] / native,
                        'last_ON_endpoint_error_channel_widths': endpoint_diff[1] / native,
                        'tolerance_channel_widths': tolerance / native,
                        'global_winner_compatible_with_survivor': compatible,
                    })
    check(evidence['original_input_bindings'] == retained_bindings, 'all original artifact bindings faithfully reported')
    csv_mapping = {'survivors': 'survivors.csv', 'OFF_comparisons': 'original_OFF_comparisons.csv',
                   'truth_track_geometry': 'truth_track_geometry.csv',
                   'global_OFF_winner_compatibility': 'OFF_global_winner_compatibility.csv'}
    for name, rows in expected.items():
        compare_rows(evidence[name], rows, 'JSON ' + name)
        with (OUT / csv_mapping[name]).open(newline='') as f:
            compare_rows(list(csv.DictReader(f)), rows, 'CSV ' + name)
    for key, n in [('survivor_count', 14), ('original_OFF_comparison_count', 42),
                   ('truth_geometry_rows', 84), ('global_OFF_winner_pairs', 42)]:
        same(evidence[key], n, key)
    for key in ('all_14_true_drifts_excluded_for_every_frozen_OFF_width_even_with_free_reference_frequency',
                'all_42_retained_global_OFF_winning_paths_incompatible',
                'all_42_original_compatible_families_exhausted_below_8', 'thresholds_unchanged'):
        check(evidence[key] is True, 'evidence statement ' + key)
    for key in ('qualification', 'detector_or_generator_executed', 'new_draws_or_scores', 'telescope_values_opened'):
        check(evidence[key] is False, 'evidence scope declaration ' + key)
    check(evidence['source_commit'] == '6b8259099721b3acdb98b604fb5c9ea192577d68', 'evidence source commit')
    check(evidence['status'] == 'COMPLETE_READ_ONLY_RETAINED_RFI_ANALYSIS', 'evidence status')
    check(artifact_count == 40 and len(interval_checks) == 56, 'artifact and independent interval check counts')
    record = {
        'status': 'PASS_RETAINED_DERIVATIONS_ONLY' if not FAILURES else 'FAIL_RETAINED_DERIVATIONS',
        'independent_of_analysis_imports': True, 'method': '45-digit Decimal arithmetic; independently intersect endpoint reference-frequency intervals at the true slope for every frozen OFF width; Python first-maximum selection from saved maps',
        'original_case_count': 2, 'original_artifact_hashes_and_lengths_verified': artifact_count,
        'original_manifest_bindings_verified': 2, 'saved_map_count': 12,
        'survivors_checked_against_saved_ON_winners': len(expected['survivors']),
        'original_OFF_comparison_records_checked': len(expected['OFF_comparisons']),
        'truth_geometry_rows_checked': len(expected['truth_track_geometry']),
        'global_OFF_winner_pairs_checked': len(expected['global_OFF_winner_compatibility']),
        'independent_true_slope_interval_exclusions': interval_checks,
        'original_truth_localized_hits_independently_found_and_all_rejected': localized_rejected,
        'numeric_comparisons': NUMERIC_COMPARISONS,
        'numeric_absolute_tolerance': 0.000001, 'maximum_numeric_difference_observed': MAX_DIFFERENCE,
        'csv_row_counts': {csv_mapping[k]: len(v) for k, v in expected.items()},
        'audited_file_sha256': {n: sha(OUT / n) for n in ['analyze_retained.py', 'RFI_GEOMETRY_EVIDENCE.json', *csv_mapping.values()]},
        'qualification': False, 'original_A_B_outcomes_unchanged': 'FAIL_CLOSED',
        'limitations': [
            'Original scores and exhaustive-family flags are authenticated retained records, not newly recomputed from raw arrays.',
            'Only each saved OFF map global winner is checked here; its incompatibility alone does not prove absence of a compatible veto witness. The separately retained original exhaustive comparisons supply the reported below-threshold evidence.',
            'All true-slope endpoint intervals are disjoint even with unrestricted continuous reference frequency; this is deterministic geometry, not proof of a universal physical alias mechanism.',
            'Import allowlist and execution of this auditor establish the audited code scope; scope declarations do not certify all possible unlogged activity.',
        ],
        'failures': FAILURES,
    }
    (OUT / 'PEER_AUDIT.json').write_text(json.dumps(record, indent=2) + '\n')
    text = ('# Independent retained RFI derivation audit — 8 October 2026\n\n'
            f"Status: **{record['status']}**.\n\n"
            'Independently checked the two original case manifests (40 artifact SHA256 hashes and byte lengths), '
            '12 saved maps, all 14 survivor ON winners, 42 original OFF comparison records, 84 truth trajectory rows '
            'and 42 global OFF winner compatibility rows. All four CSV files match the JSON evidence and independently derived values. '
            f"Maximum arithmetic disagreement is {MAX_DIFFERENCE:.12g} against an absolute tolerance of 1e-6.\n\n"
            'The auditor does not import the root analysis, detector or generator. It uses 45-digit Decimal arithmetic and '
            'intersects the reference-frequency intervals required by the two ON endpoints at the injected true slope. '
            'All 56 combinations of 14 survivors and four frozen OFF widths have empty intersections, even before restricting '
            'reference frequency to the OFF carrier grid. The minimax endpoint distance and reported slope bound agree.\n\n'
            f"An independent endpoint localization check finds {localized_rejected} original truth-localized ON hits; all are OFF_MATCHED. "
            'The surviving carriers are outside that truth localization.\n\n'
            'Saved original OFF scores and exhaustive-family flags were authenticated and transcribed, not recomputed. '
            'The incompatibility of the 42 saved global winning OFF paths is only a diagnostic comparison; '
            'the original exhaustive compatible-family records remain the source for absence of a veto. '
            'The geometry supports the alias interpretation but does not prove a universal physical cause. '
            'A/B remain FAIL_CLOSED, with no qualification, draws, new scoring or detector change.\n')
    if FAILURES:
        text += '\nFailures:\n\n' + '\n'.join('- ' + f for f in FAILURES) + '\n'
    (OUT / 'PEER_AUDIT.md').write_text(text)
    print(json.dumps({k: record[k] for k in ('status', 'numeric_comparisons', 'maximum_numeric_difference_observed',
                                            'original_truth_localized_hits_independently_found_and_all_rejected', 'failures')}))
    raise SystemExit(0 if not FAILURES else 1)


if __name__ == '__main__':
    main()
