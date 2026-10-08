"""Independent retained-output audit. No experiment module is imported or run.

Decimal arithmetic reconstructs linear endpoint geometry from original records.
NPZ reads inspect saved maximum maps only; no original power arrays or scores
are regenerated. Writes are confined to the two new peer-audit products.
"""
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np

getcontext().prec = 45
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
CSV_NAMES = (
    'diagnostic_cases.csv', 'saved_scan_maxima.csv',
    'transient_original_carriers.csv', 'near_OFF_original_carriers.csv',
    'near_OFF_original_witnesses.csv', 'noise_law_coverage.csv',
)
checked_cells = 0


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dec(value):
    return Decimal(str(value))


def equal_value(value, expected, context, tolerance=Decimal('0')):
    global checked_cells
    checked_cells += 1
    if expected is None:
        assert value == '', (context, value, expected)
    elif isinstance(expected, bool):
        assert value == str(expected), (context, value, expected)
    elif isinstance(expected, (int, float, Decimal)):
        assert abs(dec(value) - dec(expected)) <= tolerance, (context, value, expected)
    else:
        assert value == str(expected), (context, value, expected)


def check_row(table, index, expected, geometry_fields=()):
    row = table[index]
    assert set(row) == set(expected), (index, set(row), set(expected))
    for field, value in expected.items():
        tolerance = Decimal('0.0000003') if field in geometry_fields else Decimal('0')
        equal_value(row[field], value, (index, field), tolerance)


def endpoint_difference(first, second, scan, scale):
    """Difference of two declared straight lines at saved endpoint times."""
    intercept = dec(first[0]) - dec(second[0])
    slope = dec(first[1]) - dec(second[1])
    return tuple((intercept + slope * dec(scan[field])) / scale for field in (
        'scan_first_time_from_tref_s', 'scan_last_time_from_tref_s'))


def localization(hit, truth):
    if hit['scan_id'] not in truth['active_ON_scan_ids']:
        return False, (None, None), None
    width = truth['flux_by_scan'][hit['scan_id']]['injection_oracle_width_channels']
    tolerance = Decimal(2) + dec(max(width, hit['width_channels'])) / 2
    errors = endpoint_difference(
        (hit['reference_frequency_hz'], hit['drift_hz_s']),
        (truth['reference_frequency_hz'], truth['drift_hz_s']),
        hit, abs(dec(hit['df_hz'])))
    # No rounding-sensitive boolean is silently assigned.
    assert abs(max(map(abs, errors)) - tolerance) > Decimal('0.0000003')
    return max(map(abs, errors)) <= tolerance, errors, tolerance


def main():
    global checked_cells
    evidence = read(OUT / 'DIAGNOSTIC_EVIDENCE.json')
    tables = {}
    for name in CSV_NAMES:
        with (OUT / name).open(newline='') as handle:
            tables[name] = list(csv.DictReader(handle))
    assert [len(tables[name]) for name in CSV_NAMES] == [56, 336, 8114, 66, 66, 4]
    assert evidence['status'] == 'COMPLETE_RETAINED_DIAGNOSTIC_ANALYSIS'
    assert evidence['source_commit'] == '13131757641c06d7bfcb10790a79811c750b1178'
    assert evidence['qualification'] is False
    for key in ('new_draws', 'new_scores', 'new_telescope_payloads'):
        assert evidence[key] == 0
    assert evidence['A_B_remain_FAIL_CLOSED'] is True
    assert evidence['witness_localization_is_descriptive_new_geometry_not_original_gate'] is True
    frozen_codes = {
        'pilot_engine_20261008/detector.py': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
        'pilot_controls_20261008/generator.py': '3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693',
        'pilot_controls_20261008/control_contract.json': '44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c',
    }
    assert evidence['original_code_sha256'] == frozen_codes
    for name, expected in frozen_codes.items():
        assert digest(ROOT / name) == expected

    # Check publication/restore bindings without extracting or altering archives.
    publication = read(ROOT / 'pilot_protocol_20261008/validation_b_upload_index.json')
    restoration = read(OUT / 'RESTORED_INPUTS.json')
    assert restoration['source_commit'] == evidence['source_commit']
    assert len(restoration['archives']) == 56
    for i, recorded in enumerate(restoration['archives'], 86):
        archive_name = f'case_{i:03d}.tar.gz'
        published = next(item for item in publication if item['path'].endswith('/' + archive_name))
        assert recorded == published
        content = (ROOT / 'recovery/diagnostics' / archive_name).read_bytes()
        assert len(content) == published['bytes']
        assert hashlib.sha256(content).hexdigest() == published['sha256']
        assert hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == published['git_blob_sha1']

    counts = Counter()
    noise_maxima = defaultdict(list)
    noise_cadences = Counter()
    transient_cursor = near_cursor = witness_cursor = scan_cursor = 0
    original_bindings = []
    max_endpoint_rounding_delta_hz = Decimal(0)
    for index in range(86, 142):
        folder = ROOT / f'results/radio_pilot_val_b_20261008/case_{index:03d}'
        case = read(folder / 'case_definition.json')
        truth = read(folder / 'truth.json')
        raw = read(folder / 'all_ON_threshold_carriers.json')
        metadata = read(folder / 'scan_map_metadata.json')
        recovery = read(folder / 'localized_recovery.json')
        outcome = read(folder / 'outcome.json')
        marker = read(folder / 'COMMITTED.json')
        manifest = read(folder / 'artifact_manifest.json')
        family = ('noise' if index < 118 else 'single_row_transient' if index < 130 else 'near_off_contamination')
        assert case['family'] == truth['family'] == outcome['family'] == family
        assert case['case_id'] == truth['case_id'] == outcome['case_id'] == marker['case_id']
        assert marker['status'] == 'COMPLETED_CASE_ONLY'
        assert marker['caps_passed'] is True and marker['no_retry_or_redraw'] is True
        assert marker['artifact_manifest_SHA256'] == digest(folder / 'artifact_manifest.json')
        for name, binding in manifest.items():
            path = (folder / name).resolve()
            assert path.is_relative_to(folder.resolve())
            assert path.stat().st_size == binding['size_bytes'] and digest(path) == binding['SHA256']
            counts['artifact_hashes'] += 1
        original_bindings.append({
            'directory': str(folder.relative_to(ROOT)),
            'manifest_sha256': digest(folder / 'artifact_manifest.json'),
            'COMMITTED_sha256': digest(folder / 'COMMITTED.json'),
            'verified_artifact_count': len(manifest),
            'case_definition_sha256': digest(folder / 'case_definition.json'),
            'truth_sha256': digest(folder / 'truth.json'),
            'raw_hits_sha256': digest(folder / 'all_ON_threshold_carriers.json'),
            'map_metadata_sha256': digest(folder / 'scan_map_metadata.json'),
        })
        assert len(metadata) == 6 and len({m['scan_id'] for m in metadata}) == 6
        meta_by_id = {m['scan_id']: m for m in metadata}
        off_ids = [m['scan_id'] for m in metadata if m['role'] == 'OFF']
        active_ids = [metadata[i]['scan_id'] for i in case['active_scan_indices'] if metadata[i]['role'] == 'ON']
        assert active_ids == truth['active_ON_scan_ids']
        if family != 'noise':
            assert case['eligibility_case'] is False and len(active_ids) == 1
        else:
            assert case['eligibility_case'] is True and not raw and not active_ids
            noise_cadences[case['noise_law']] += 1
            counts['noise_cases'] += 1

        case_map_rows = []
        for scan_index, meta in enumerate(metadata):
            with np.load(folder / meta['array_file'], allow_pickle=False) as saved:
                scores = saved['maximum_robust_box_track_score']
                # Built-in scalar traversal independently selects the first maximum.
                winning_index, maximum = max(enumerate(map(float, scores)), key=lambda item: item[1])
                assert np.isfinite(scores).all()
                threshold = 10 if meta['role'] == 'ON' else 8
                expected = {
                    'case_id': case['case_id'], 'family': family, 'noise_law': case['noise_law'],
                    'scan_index': scan_index, 'scan_id': meta['scan_id'], 'role': meta['role'],
                    'is_injected_ON': meta['scan_id'] in active_ids,
                    'maximum_original_robust_score': maximum, 'winner_carrier': winning_index,
                    'winner_frequency_hz': float(saved['frequency_hz_at_tref'][winning_index]),
                    'winner_drift_hz_s': float(saved['winning_drift_hz_s'][winning_index]),
                    'winner_width_channels': int(saved['winning_width_channels'][winning_index]),
                    'threshold': threshold, 'margin_relative_to_threshold': maximum - threshold,
                }
                check_row(tables['saved_scan_maxima.csv'], scan_cursor, expected)
                assert evidence['scan_maxima'][scan_cursor] == expected
                scan_cursor += 1
                counts['maps'] += 1
                case_map_rows.append(expected)
                if family == 'noise' and meta['role'] == 'ON':
                    noise_maxima[case['noise_law']].append(maximum)
                    counts['noise_ON_scans'] += 1
                if meta['role'] == 'ON':
                    hits = [hit for hit in raw if hit['scan_id'] == meta['scan_id']]
                    from_map = [i for i, score in enumerate(scores) if score >= 10]
                    assert [hit['reference_carrier_index'] for hit in hits] == from_map
                    for hit in hits:
                        carrier = hit['reference_carrier_index']
                        assert hit['ON_robust_score'] == float(scores[carrier])
                        assert hit['reference_frequency_hz'] == float(saved['frequency_hz_at_tref'][carrier])
                        assert hit['drift_hz_s'] == float(saved['winning_drift_hz_s'][carrier])
                        assert hit['width_channels'] == int(saved['winning_width_channels'][carrier])
                        for field in ('df_hz', 'scan_first_time_from_tref_s', 'scan_last_time_from_tref_s'):
                            assert hit[field] == meta[field]

        localized, localized_final = [], []
        survivors = [h for h in raw if h['disposition'] == 'SURVIVOR_EXPLORATORY']
        for active in active_ids:
            matches = [h for h in raw if h['scan_id'] == active and localization(h, truth)[0]]
            final_matches = [h for h in matches if h['disposition'] == 'SURVIVOR_EXPLORATORY']
            original = recovery['per_active_ON_scan'][active]
            assert len(matches) == original['pre_OFF_localized_count']
            assert len(final_matches) == original['final_localized_count']
            assert bool(matches) == original['pre_OFF_localized_recovery']
            assert bool(final_matches) == original['final_localized_recovery']
            localized.extend(matches)
            localized_final.extend(final_matches)
        assert len(raw) == outcome['ON_threshold_carrier_count']
        assert len(survivors) == outcome['survivor_count']
        assert outcome['data_integrity_ok'] is True and outcome['failure'] is None
        stage = ('NO_INJECTED_ON' if not active_ids else 'LOCALIZED_SURVIVOR' if localized_final
                 else 'OFF_VETO_LOSS' if localized else 'NO_ON_THRESHOLD_HIT'
                 if not any(h['scan_id'] in active_ids for h in raw) else 'NO_LOCALIZED_THRESHOLD_HIT')
        summary = {
            'case_index': index, 'case_id': case['case_id'], 'family': family,
            'noise_law': case['noise_law'], 'eligibility_case': case['eligibility_case'],
            'active_ON_scans': ','.join(active_ids), 'ideal_level': case.get('nominal_ideal_box_score'),
            'intrinsic_width_channels': case.get('intrinsic_width_channels'),
            'input_drift_hz_s': case.get('drift_hz_s'),
            'input_reference_native_offset': case.get('reference_native_offset'),
            'input_transient_row': case.get('transient_row'),
            'diagnostic_OFF_offset_native_channels': case.get('diagnostic_off_frequency_offset_channels'),
            'ON_threshold_carriers': len(raw), 'surviving_carriers': len(survivors),
            'localized_initial_carriers': len(localized), 'localized_final_carriers': len(localized_final),
            'initial_localized_recovery': bool(localized), 'final_localized_recovery': bool(localized_final),
            'maximum_active_ON_score': max((r['maximum_original_robust_score'] for r in case_map_rows if r['is_injected_ON']), default=None),
            'maximum_any_ON_score': max(r['maximum_original_robust_score'] for r in case_map_rows if r['role'] == 'ON'),
            'miss_stage': stage,
        }
        check_row(tables['diagnostic_cases.csv'], index - 86, summary)
        assert evidence['cases'][index - 86] == summary
        counts['cases'] += 1
        if family == 'single_row_transient':
            counts['transient_cases'] += 1
            counts['transient_localized_surviving_cases'] += bool(localized_final)
            counts['transient_original_carriers'] += len(raw)
            counts['transient_final_carriers'] += len(survivors)
            counts['transient_truth_localized_final_carriers'] += len(localized_final)
        if family == 'near_off_contamination':
            counts['near_OFF_cases'] += 1
            counts['near_OFF_initial_localized_cases'] += bool(localized)
            counts['near_OFF_final_localized_cases'] += bool(localized_final)
            counts['near_OFF_original_carriers'] += len(raw)

        for hit in raw:
            comparisons = hit['OFF_comparisons']
            assert [comp['scan_id'] for comp in comparisons] == off_ids
            assert hit['disposition'] == ('OFF_MATCHED' if any(c['veto'] for c in comparisons) else 'SURVIVOR_EXPLORATORY')
            local, errors, tolerance = localization(hit, truth)
            for comp in comparisons:
                assert comp['checked_valid_compatible_templates'] > 0
                if comp['veto']:
                    witness = comp['witness']
                    assert comp['family_exhausted'] is False and witness is not None
                    assert witness['OFF_robust_score'] >= 8
                    assert comp['maximum_checked_score'] >= witness['OFF_robust_score']
                else:
                    assert comp['family_exhausted'] is True and comp['witness'] is None
                    assert comp['maximum_checked_score'] < 8
            if family == 'single_row_transient':
                row = {
                    'case_id': case['case_id'], 'carrier': hit['reference_carrier_index'],
                    'ON_scan': hit['scan_id'], 'ON_score': hit['ON_robust_score'],
                    'winning_width_channels': hit['width_channels'], 'winning_drift_hz_s': hit['drift_hz_s'],
                    'frequency_hz_at_tref': hit['reference_frequency_hz'], 'disposition': hit['disposition'],
                    'truth_localized': local, 'first_ON_truth_error_channel_widths': errors[0],
                    'last_ON_truth_error_channel_widths': errors[1], 'truth_tolerance_channel_widths': tolerance,
                    'all_OFF_families_exhausted': all(c['family_exhausted'] for c in comparisons),
                    'maximum_original_checked_OFF_score': max(c['maximum_checked_score'] for c in comparisons),
                }
                check_row(tables['transient_original_carriers.csv'], transient_cursor, row,
                          ('first_ON_truth_error_channel_widths', 'last_ON_truth_error_channel_widths'))
                transient_cursor += 1
            if family != 'near_off_contamination':
                continue
            assert sum(comp['veto'] for comp in comparisons) == 1
            following_id = metadata[case['active_scan_indices'][0] + 1]['scan_id']
            offset = case['diagnostic_off_frequency_offset_channels']
            shift = dec(offset) * dec(hit['df_hz'])
            row = {
                'case_id': case['case_id'], 'carrier': hit['reference_carrier_index'],
                'ON_scan': hit['scan_id'], 'ON_score': hit['ON_robust_score'],
                'ON_width_channels': hit['width_channels'], 'ON_drift_hz_s': hit['drift_hz_s'],
                'ON_frequency_hz_at_tref': hit['reference_frequency_hz'], 'truth_localized': local,
                'disposition': hit['disposition'], 'declared_OFF_native_offset_channels': offset,
                'declared_OFF_frequency_shift_hz': shift, 'following_contaminated_OFF': following_id,
                'veto_OFF_scans': ','.join(c['scan_id'] for c in comparisons if c['veto']),
            }
            check_row(tables['near_OFF_original_carriers.csv'], near_cursor, row, ('declared_OFF_frequency_shift_hz',))
            near_cursor += 1
            for comp in comparisons:
                if not comp['veto']:
                    continue
                witness = comp['witness']
                off_meta = meta_by_id[comp['scan_id']]
                scale = max(abs(dec(hit['df_hz'])), abs(dec(off_meta['df_hz'])))
                allowed = (dec(hit['width_channels']) + dec(witness['width_channels'])) / 2 + 2
                on_errors = endpoint_difference(
                    (witness['reference_frequency_hz'], witness['drift_hz_s']),
                    (hit['reference_frequency_hz'], hit['drift_hz_s']), hit, scale)
                assert max(map(abs, on_errors)) <= allowed + Decimal('0.0000003')
                for error, field in zip(on_errors, ('ON_first_endpoint_error_hz', 'ON_last_endpoint_error_hz')):
                    discrepancy = abs(error * scale - dec(witness[field]))
                    max_endpoint_rounding_delta_hz = max(max_endpoint_rounding_delta_hz, discrepancy)
                    assert discrepancy < Decimal('0.000001')
                assert abs(allowed * scale - dec(witness['endpoint_tolerance_hz'])) < Decimal('0.000001')
                assert witness['ON_first_time_from_tref_s'] == hit['scan_first_time_from_tref_s']
                assert witness['ON_last_time_from_tref_s'] == hit['scan_last_time_from_tref_s']
                declared_off_frequency = dec(truth['reference_frequency_hz']) + shift
                off_errors = endpoint_difference(
                    (witness['reference_frequency_hz'], witness['drift_hz_s']),
                    (declared_off_frequency, case['drift_hz_s']), off_meta, scale)
                # A newly stated descriptive reference, not a saved diagnostic OFF oracle.
                on_oracle = truth['flux_by_scan'][active_ids[0]]['injection_oracle_width_channels']
                illustrative_tolerance = Decimal(2) + dec(max(witness['width_channels'], on_oracle)) / 2
                assert abs(max(map(abs, off_errors)) - illustrative_tolerance) > Decimal('0.0000003')
                following = comp['scan_id'] == following_id
                illustrative_localization = following and max(map(abs, off_errors)) <= illustrative_tolerance
                row = {
                    'case_id': case['case_id'], 'ON_carrier': hit['reference_carrier_index'],
                    'ON_truth_localized': local, 'ON_score': hit['ON_robust_score'],
                    'ON_width_channels': hit['width_channels'], 'ON_drift_hz_s': hit['drift_hz_s'],
                    'OFF_scan': comp['scan_id'], 'is_following_contaminated_OFF': following,
                    'original_OFF_witness_score': witness['OFF_robust_score'],
                    'original_witness_frequency_hz': witness['reference_frequency_hz'],
                    'original_witness_drift_hz_s': witness['drift_hz_s'],
                    'original_witness_width_channels': witness['width_channels'],
                    'OFF_match_tolerance_channel_widths': allowed,
                    'first_ON_compatibility_error_channel_widths': on_errors[0],
                    'last_ON_compatibility_error_channel_widths': on_errors[1],
                    'declared_OFF_frequency_shift_hz': shift,
                    'first_OFF_declared_line_error_channel_widths': off_errors[0],
                    'last_OFF_declared_line_error_channel_widths': off_errors[1],
                    'illustrative_OFF_line_localization_tolerance_channel_widths': illustrative_tolerance,
                    'witness_geometrically_localized_to_declared_following_OFF_line': illustrative_localization,
                    'checked_template_count_before_stop': comp['checked_valid_compatible_templates'],
                    'original_partial_maximum_checked_score': comp['maximum_checked_score'],
                    'family_exhausted': comp['family_exhausted'],
                }
                check_row(tables['near_OFF_original_witnesses.csv'], witness_cursor, row, (
                    'first_ON_compatibility_error_channel_widths', 'last_ON_compatibility_error_channel_widths',
                    'first_OFF_declared_line_error_channel_widths', 'last_OFF_declared_line_error_channel_widths',
                    'declared_OFF_frequency_shift_hz'))
                witness_cursor += 1
                counts['near_OFF_original_veto_witnesses'] += 1
                counts['near_OFF_witnesses_in_following_contaminated_OFF'] += following
                counts['near_OFF_witnesses_localized_to_declared_OFF_line'] += illustrative_localization

    contract = read(ROOT / 'pilot_controls_20261008/control_contract.json')
    for i, law in enumerate(contract['noise_laws']):
        values = noise_maxima[law]
        assert noise_cadences[law] == 8 and len(values) == 24
        # Conditional zero-success binomial illustration using independent Decimal exp/log.
        conditional_bound = 1 - (Decimal('0.05').ln() / 8).exp()
        row = {
            'noise_law': law, 'cadences': 8, 'ON_scans': 24, 'ON_threshold_carriers': 0,
            'surviving_cadences': 0, 'minimum_ON_global_maximum': min(values),
            'median_ON_global_maximum': statistics.median(values), 'maximum_ON_global_maximum': max(values),
            'minimum_margin_below_ON10': 10 - max(values),
            'hypothetical_iid_same_law_95percent_zero_of8_upper_bound': conditional_bound,
            'hypothetical_bound_is_not_calibrated_sky_FAP': True,
        }
        check_row(tables['noise_law_coverage.csv'], i, row,
                  ('hypothetical_iid_same_law_95percent_zero_of8_upper_bound',))
        for field, original in evidence['noise_law_groups'][i].items():
            equal_value(str(original), row[field], ('noise_law_groups', i, field),
                        Decimal('0.000000000000001') if field == 'hypothetical_iid_same_law_95percent_zero_of8_upper_bound' else Decimal('0'))
    counts['noise_ON_carriers'] = 0
    assert dict(counts) == evidence['counts'], (dict(counts), evidence['counts'])
    assert original_bindings == evidence['original_case_bindings']
    assert transient_cursor == 8114 and near_cursor == witness_cursor == 66 and scan_cursor == 336
    missed_near = [r for r in evidence['cases'] if r['family'] == 'near_off_contamination' and not r['initial_localized_recovery']]
    assert len(missed_near) == 1 and missed_near[0]['case_id'].endswith(':008')
    assert missed_near[0]['maximum_active_ON_score'] == 9.877217747885116
    result = {
        'review_status': 'PASS_INDEPENDENT_RETAINED_DIAGNOSTIC_TABLE_AUDIT',
        'source_commit': evidence['source_commit'], 'counts_independently_verified': dict(counts),
        'publication_archive_hash_bindings_verified': 56,
        'CSV_rows_verified': {name: len(tables[name]) for name in CSV_NAMES},
        'CSV_or_JSON_scalar_cells_verified': checked_cells,
        'arithmetic': '45-digit Decimal endpoint geometry; built-in scalar maximum selection; statistics.median; Decimal exp/log conditional bound',
        'maximum_decimal_vs_original_endpoint_record_delta_hz': str(max_endpoint_rounding_delta_hz),
        'geometry_comparison_tolerance_channel_widths': '0.0000003',
        'script_sha256': digest(Path(__file__)),
        'audited_product_sha256': {name: digest(OUT / name) for name in (*CSV_NAMES, 'DIAGNOSTIC_EVIDENCE.json')},
        'scope': 'Only original B cases086..141, saved map maxima and retained classifications/witnesses; no original power or score reconstruction.',
        'limits': [
            'Hash and saved-record agreement do not independently reconstruct unretained raw power or OFF witness scores.',
            'Vetoed OFF families stopped at the original first qualifying witness; their checked maxima and counts are partial traversal records.',
            'The 19/66 witness localization uses the main ON injection oracle width as an explicitly new descriptive reference; no diagnostic OFF oracle was retained.',
            'The zero-of-eight 95% bound is illustrative only under IID homogeneous cadences within the specified synthetic law; no such sky calibration or pooled heterogeneous bound is asserted.',
            'Correlated carriers are not independent events. Both qualification panels remain failed.',
        ],
        'qualification': False, 'new_draws': 0, 'new_scores': 0,
    }
    (OUT / 'PEER_DIAGNOSTIC_AUDIT.json').write_text(json.dumps(result, indent=2) + '\n')
    markdown = f'''# Independent retained diagnostic table audit\n\nPASS. The independent script authenticated 56 published archive bindings and {counts['artifact_hashes']} original artifact hashes, inspected {counts['maps']} saved maps, and checked every row and field of the six diagnostic CSVs against their original records. It did not import or execute the generator, detector, or primary analysis script.\n\nAll {counts['transient_original_carriers']} transient carriers survive; {counts['transient_truth_localized_final_carriers']} meet the original localization rule, with localized survivors in all 12 transient cases. All 66 near-OFF carriers are vetoed by one original witness apiece in the immediately following contaminated OFF. Eleven of 12 main ON lines were localized before OFF; case008 had no ON threshold carrier and a saved active-ON maximum of 9.877217747885116. All 32 noise cases have no ON carrier across 96 ON scans, with eight cadences per frozen noise law.\n\nIndependent 45-digit Decimal endpoint geometry confirms the compatibility records and the newly stated descriptive 19/66 OFF-line localization count. That reference uses the saved main ON oracle width; the original truth did not retain a separate diagnostic OFF oracle. It is not an original gate. The largest Decimal-versus-record endpoint difference was {max_endpoint_rounding_delta_hz} Hz.\n\nThe conditional zero-of-eight illustration is 31.2343978066% at 95%, assuming IID homogeneous synthetic cadences within one specified law. It is not a sky false-alarm probability or a bound pooled over the four heterogeneous laws. Early-stopped OFF maxima remain partial traversal maxima. Hash agreement and retained score agreement do not reconstruct the unretained power arrays or prove individual score contributions. Correlated carriers are not independent events. A and B remain failed.\n\nSee PEER_DIAGNOSTIC_AUDIT.json for exact hashes, counts, precision and limitations.\n'''
    (OUT / 'PEER_DIAGNOSTIC_AUDIT.md').write_text(markdown)
    print(json.dumps({'review_status': result['review_status'], 'counts': dict(counts), 'scalar_cells_checked': checked_cells}))


if __name__ == '__main__':
    main()
