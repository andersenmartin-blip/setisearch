"""Review closed retained B outputs only; no generation, search or source access."""
from pathlib import Path
import hashlib
import json
import math

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'results/radio_pilot_val_b_20261008'
REVIEW = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, tol=1e-8):
    assert math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol), (a, b)


def main():
    # Refuse even retained-map loading until the coordinator has durably closed.
    marker = read(OUT / 'COMMITTED_PANEL.json')
    import numpy as np
    cases = read(BASE / 'pilot_controls_20261008/validation_b_cases.json')
    master_path = BASE / 'pilot_runtime_correction_20261008/validation_b_admission.json'
    master = read(master_path)
    summary = read(OUT / 'summary.json')
    outcomes = read(OUT / 'outcomes.json')
    resources = read(OUT / 'resource_receipt.json')
    ledger = read(OUT / 'rolling_cpu_ledger.json')
    assert len(cases) == 142
    ids = [c['case_id'] for c in cases]
    assert len(set(ids)) == 142 and master['allowed_case_ids'] == ids
    assert master['public_commit_sha'] == '69c9526bd22d5f6393f7ec51a60aae746fdc2234'
    assert digest(BASE / 'pilot_controls_20261008/validation_b_cases.json') == '93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c'
    for key, path in master['paths'].items():
        assert digest(Path(path)) == master['sha256'][key], key
    for name in ('outcomes', 'summary', 'resource_receipt'):
        assert marker[name + '_SHA256'] == digest(OUT / (name + '.json'))
    observed = {x['case_id']: x for x in outcomes}
    assert len(observed) == len(outcomes)
    assert set(observed) <= set(ids)
    closures = {c['case_id']: c for c in resources['closures']}
    assert len(closures) == len(resources['closures'])
    controller_claim = read(BASE / 'pilot_protocol_20261008/validation_b_claims/controller_claim.json')
    assert controller_claim['case_ids'] == ids and controller_claim['no_restart_or_redraw']
    assert controller_claim['master_admission_SHA256'] == digest(master_path)
    full_plan = read(OUT / 'full_panel_plan.json')
    assert [x['case_id'] for x in full_plan['all_slots']] == ids
    artifact_count = map_count = off_count = witness_count = 0
    records = []
    missing_outputs = {}
    widths = (1, 3, 9, 33)
    for index, case in enumerate(cases):
        identity = case['case_id']
        if identity not in observed:
            records.append({'case_id': identity, 'status': 'MISSING'})
            continue
        p = OUT / f'case_{index:03d}'
        outcome = observed[identity]
        closure = read(OUT / f'closure_{index:03d}.json')
        assert closure == closures[identity] and closure['case_id'] == identity
        reservation = read(OUT / f'reservation_{index:03d}.json')
        admission = read(OUT / f'admission_{index:03d}.json')
        assert reservation['case_id'] == identity and reservation['cpu_reserved_seconds'] == 1800
        assert reservation['status'] == 'RESERVED_BEFORE_CHILD_SUBMIT'
        assert reservation['master_admission_SHA256'] == digest(master_path)
        assert admission['allowed_case_ids'] == [identity] and admission['status'] == 'ADMITTED_VAL_B_SINGLE_CASE'
        claim = read(BASE / 'pilot_protocol_20261008/validation_b_claims' / (hashlib.sha256(identity.encode('ascii')).hexdigest() + '.json'))
        assert claim['case_id'] == identity and claim['no_retry_or_redraw']
        assert claim['admission_SHA256'] == digest(OUT / f'admission_{index:03d}.json')
        expected = [f'scan_{i:02d}_full_map.npz' for i in range(6)] + ['localized_recovery.json', 'all_ON_threshold_carriers.json', 'scan_map_metadata.json', 'geometry_arrays.npz', 'COMMITTED.json']
        absent = [name for name in expected if not (p / name).exists()]
        if not outcome['data_integrity_ok'] or outcome.get('failure'):
            missing_outputs[identity] = absent
            records.append({'case_id': identity, 'status': 'FAILED_CLOSED', 'failure': outcome.get('failure'), 'missing_outputs': absent, 'closure': closure})
            continue
        assert not absent, (identity, absent)
        assert read(p / 'case_definition.json') == case
        child = read(p / 'outcome.json')
        assert child['case_id'] == identity and child['data_integrity_ok'] and child['failure'] is None
        for key in ('all_active_on_recovered', 'any_localized_on_recovered', 'pre_OFF_all_active_recovery', 'pre_OFF_any_active_recovery', 'survivor_count', 'ON_threshold_carrier_count'):
            assert child[key] == outcome[key]
        close(outcome['worker_snapshot_cpu_s'], child['cpu_s'])
        close(outcome['cpu_s'], closure['cpu_charged_seconds'])
        close(closure['cpu_charged_seconds'], max(closure['wait4_whole_child_cpu_s'], child['cpu_s']))
        close(closure['unused_reservation_refunded_seconds'], max(0, 1800 - closure['cpu_charged_seconds']))
        assert closure['child_exit_code'] == 0 and closure['case_integrity_passed']
        assert closure['wait4_whole_child_cpu_s'] <= 1800 and closure['whole_child_wall_s'] <= 1800 and closure['wait4_peak_rss_bytes'] <= 4 * 1024**3
        committed = read(p / 'COMMITTED.json')
        assert committed['case_id'] == identity and committed['panel'] == 'VAL_B' and committed['status'] == 'COMPLETED_CASE_ONLY'
        assert committed['caps_passed'] and committed['no_retry_or_redraw']
        assert committed['artifact_manifest_SHA256'] == digest(p / 'artifact_manifest.json')
        manifest = read(p / 'artifact_manifest.json')
        for name, value in manifest.items():
            assert digest(p / name) == value['SHA256'] and (p / name).stat().st_size == value['size_bytes'], (identity, name)
            artifact_count += 1
        receipt = read(p / 'resource_receipt.json')
        assert receipt['caps_passed'] and receipt['caps']['exclusive_cpu_allocation_seconds'] == 1800
        assert receipt['cpu_s'] == child['cpu_s'] and receipt['wall_s'] == child['wall_s']
        assert receipt['cpu_s'] <= 1800 and receipt['wall_s'] <= 1800 and receipt['peak_rss_bytes'] <= 4 * 1024**3
        meta = read(p / 'scan_map_metadata.json')
        truth = read(p / 'truth.json')
        hits = read(p / 'all_ON_threshold_carriers.json')
        detector_summary = read(p / 'detector_summary.json')
        recovery = read(p / 'localized_recovery.json')
        assert truth['case_id'] == identity and truth['seed_sha256'] == case['seed_sha256'] == hashlib.sha256(identity.encode('ascii')).hexdigest()
        assert len(meta) == 6
        with np.load(p / 'geometry_arrays.npz', allow_pickle=False) as z:
            geometry = {k: z[k].copy() for k in z.files}
        grid = geometry['drift_grid_hz_s']
        assert grid.shape == (5415,) and grid[0] == -4 and grid[-1] == 4 and grid[2707] == 0
        maps = {}
        expected_hits = set()
        hit_index = {(h['scan_id'], h['reference_carrier_index']): h for h in hits}
        assert len(hit_index) == len(hits)
        core_frequencies = None
        for scan_index, m in enumerate(meta):
            with np.load(p / m['array_file'], allow_pickle=False) as z:
                a = {k: z[k].copy() for k in z.files}
            maps[m['scan_id']] = a
            size = 4096 if m['role'] == 'ON' else 4596
            assert all(v.shape == (size,) and np.isfinite(v).all() for v in a.values())
            assert np.all(a['valid_hypothesis_count'] == 21660) and m['total_hypothesis_count_per_carrier'] == 21660
            assert np.isin(a['winning_width_channels'], widths).all() and np.isin(a['winning_drift_hz_s'], grid).all()
            f = a['frequency_hz_at_tref']
            assert np.allclose(np.diff(f), -2.835503418452676, rtol=0, atol=4e-7)
            if m['role'] == 'ON':
                if core_frequencies is None:
                    core_frequencies = f
                else:
                    assert np.array_equal(f, core_frequencies)
            else:
                assert np.allclose(f[250:-250], core_frequencies, rtol=0, atol=4e-7)
            t = geometry[f'scan_{scan_index:02d}_times_from_tref_s']
            assert t.shape == (16,) and np.allclose(np.diff(t), 17.986224128, rtol=0, atol=1e-10)
            assert t[0] == m['scan_first_time_from_tref_s'] and t[-1] == m['scan_last_time_from_tref_s']
            close(t.mean(), m['scan_midpoint_from_tref_s'])
            assert m['normalization']['normalization_source_channels'] == list(range(159905792, 159909888))
            if m['role'] == 'ON':
                for carrier in np.flatnonzero(a['maximum_robust_box_track_score'] >= 10):
                    key = (m['scan_id'], int(carrier)); expected_hits.add(key)
                    h = hit_index[key]
                    assert h['ON_robust_score'] == a['maximum_robust_box_track_score'][carrier]
                    assert h['reference_frequency_hz'] == f[carrier] and h['drift_hz_s'] == a['winning_drift_hz_s'][carrier]
                    assert h['width_channels'] == a['winning_width_channels'][carrier]
                    assert h['scan_first_time_from_tref_s'] == t[0] and h['scan_last_time_from_tref_s'] == t[-1]
            map_count += 1
        assert set(hit_index) == expected_hits
        survivors = 0
        for h in hits:
            assert len(h['OFF_comparisons']) == 3 and {x['scan_id'] for x in h['OFF_comparisons']} == {'epoch1_off', 'epoch2_off', 'epoch3_off'}
            for comparison in h['OFF_comparisons']:
                assert comparison['checked_valid_compatible_templates'] > 0
                if comparison['veto']:
                    witness = comparison['witness']; witness_count += 1
                    assert not comparison['family_exhausted'] and witness['OFF_robust_score'] >= 8
                    assert comparison['maximum_checked_score'] >= witness['OFF_robust_score']
                    off_map = maps[comparison['scan_id']]; k = witness['reference_carrier_index']
                    assert witness['reference_frequency_hz'] == off_map['frequency_hz_at_tref'][k]
                    assert witness['OFF_robust_score'] <= off_map['maximum_robust_box_track_score'][k] + 1e-8
                    assert witness['drift_hz_s'] in grid and witness['width_channels'] in widths
                    tolerance = ((h['width_channels'] + witness['width_channels']) / 2 + 2) * abs(h['df_hz'])
                    close(tolerance, witness['endpoint_tolerance_hz'])
                    delta_f = witness['reference_frequency_hz'] - h['reference_frequency_hz']
                    delta_d = witness['drift_hz_s'] - h['drift_hz_s']
                    for edge in ('first', 'last'):
                        error = delta_f + delta_d * h[f'scan_{edge}_time_from_tref_s']
                        close(error, witness[f'ON_{edge}_endpoint_error_hz'])
                        assert abs(error) <= tolerance
                else:
                    assert comparison['witness'] is None and comparison['family_exhausted'] and comparison['maximum_checked_score'] < 8
                off_count += 1
            veto = any(c['veto'] for c in h['OFF_comparisons'])
            assert h['disposition'] == ('OFF_MATCHED' if veto else 'SURVIVOR_EXPLORATORY')
            survivors += not veto
        assert len(hits) == child['ON_threshold_carrier_count'] == detector_summary['ON_threshold_carrier_count']
        assert survivors == child['survivor_count'] == detector_summary['surviving_ON_threshold_carrier_count']
        if truth['active_ON_scan_ids']:
            by_scan = {}
            for scan_id in truth['active_ON_scan_ids']:
                oracle = truth.get('oracle_width_by_scan', {}).get(scan_id)
                if oracle is None:
                    oracle = truth['flux_by_scan'][scan_id]['injection_oracle_width_channels']
                raw = final = 0
                for h in hits:
                    if h['scan_id'] != scan_id:
                        continue
                    tolerance = (2 + max(h['width_channels'], oracle) / 2) * abs(h['df_hz'])
                    delta_f = h['reference_frequency_hz'] - truth['reference_frequency_hz']
                    delta_d = h['drift_hz_s'] - truth['drift_hz_s']
                    if max(abs(delta_f + delta_d * h['scan_first_time_from_tref_s']), abs(delta_f + delta_d * h['scan_last_time_from_tref_s'])) <= tolerance:
                        raw += 1; final += h['disposition'] == 'SURVIVOR_EXPLORATORY'
                r = recovery['per_active_ON_scan'][scan_id]
                assert r['pre_OFF_localized_count'] == raw and r['final_localized_count'] == final
                assert r['pre_OFF_localized_recovery'] == bool(raw) and r['final_localized_recovery'] == bool(final)
                by_scan[scan_id] = (bool(raw), bool(final))
            assert child['all_active_on_recovered'] == all(x[1] for x in by_scan.values())
            assert child['any_localized_on_recovered'] == any(x[1] for x in by_scan.values())
            assert child['pre_OFF_all_active_recovery'] == all(x[0] for x in by_scan.values())
            assert child['pre_OFF_any_active_recovery'] == any(x[0] for x in by_scan.values())
        else:
            assert not recovery['recovery_applicable']
        records.append({'case_id': identity, 'family': case['family'], 'status': 'COMPLETE', 'maps': 6, 'artifact_hashes': len(manifest), 'raw_ON_carriers': len(hits), 'surviving_ON_carriers': survivors, 'whole_CPU_s': outcome['cpu_s'], 'peak_RSS_bytes': outcome['peak_rss_bytes']})
    # Independently recompute the original finite-panel counts and all nine gates.
    complete = set(observed) == set(ids) and all(x.get('data_integrity_ok') and not x.get('failure') for x in outcomes)
    families = {}
    for family in sorted({c['family'] for c in cases}):
        members = [c for c in cases if c['family'] == family]
        vals = [observed[c['case_id']] for c in members if c['case_id'] in observed]
        families[family] = {'expected': len(members), 'observed': len(vals),
            'any_localized_on_recovered': sum(bool(x.get('any_localized_on_recovered')) for x in vals),
            'all_active_on_recovered': sum(bool(x.get('all_active_on_recovered')) for x in vals),
            'all_primary_on_detected_before_off': sum(bool(x.get('rfi_pre_off_all_active_detected', x.get('pre_OFF_all_active_recovery', False))) for x in vals),
            'cadences_with_any_survivor': sum(x.get('survivor_count', 0) > 0 for x in vals)}
    subgroups = {'activity': {}, 'drift': {}, 'intrinsic_width': {}}
    for dimension, key in (('activity', 'active_scan_indices'), ('drift', 'drift_hz_s'), ('intrinsic_width', 'intrinsic_width_channels')):
        for c in [c for c in cases if c['family'] == 'operating']:
            g = json.dumps(c[key], separators=(',', ':'))
            r = subgroups[dimension].setdefault(g, {'expected': 0, 'recovered': 0})
            r['expected'] += 1; r['recovered'] += bool(observed.get(c['case_id'], {}).get('all_active_on_recovered'))
    checks = {'complete_and_integrity': complete,
        'strong_14_of_14': families['strong']['all_active_on_recovered'] == 14,
        'operating_at_least_44_of_48': families['operating']['all_active_on_recovered'] >= 44,
        'each_activity_at_least_7_of_8': all(x['recovered'] >= 7 for x in subgroups['activity'].values()),
        'each_drift_at_least_10_of_12': all(x['recovered'] >= 10 for x in subgroups['drift'].values()),
        'each_width_at_least_22_of_24': all(x['recovered'] >= 22 for x in subgroups['intrinsic_width'].values()),
        'matched_rfi_no_surviving_cadence': families['matched_rfi']['cadences_with_any_survivor'] == 0,
        'matched_rfi_all_primary_on_detected_before_off': families['matched_rfi']['all_primary_on_detected_before_off'] == 24,
        'noise_at_most_one_surviving_cadence': families['noise']['cadences_with_any_survivor'] <= 1}
    assert summary['families'] == families and summary['subgroups'] == subgroups and summary['checks'] == checks
    close(summary['resource_observed']['cpu_seconds_sum'], sum(x.get('cpu_s', 0) for x in outcomes))
    close(summary['resource_observed']['wall_seconds_sum'], sum(x.get('wall_s', 0) for x in outcomes))
    charged = sum(x['cpu_charged_seconds'] for x in resources['closures'])
    reaped = sum(x.get('wait4_whole_child_cpu_s', 0) for x in resources['closures'])
    close(charged, resources['conservative_children_cpu_s_charged'])
    # Individual wait4 totals and the cumulative child meter are distinct
    # retained measurements; use their larger value for conservative charging.
    cumulative_reaped = resources['children_cpu_s_reaped']
    close(ledger['cpu_charged_closed_children'], charged)
    assert ledger['status'] == 'CLOSED_NO_RETRY' and ledger['cpu_reserved_live_children'] == 0 and ledger['live_case_ids'] == []
    assert resources['aggregate_cpu_allocation_seconds'] == 19500 and resources['global_cpu_ceiling_seconds'] == 43200
    conservative_charge = max(charged, cumulative_reaped, ledger['cpu_charged_closed_children'])
    controller_charge = max(resources['controller_cpu_s'], ledger['controller_cpu_s_observed'])
    cpu_ok = conservative_charge + controller_charge <= 19500
    assert resources['cpu_budget_passed'] == cpu_ok
    good = all(checks.values()) and cpu_ok and resources['all_children_reaped'] and resources['controller_failure'] is None
    assert marker['case_count_observed'] == len(outcomes) and marker['case_count_expected'] == 142 and marker['panel'] == 'VAL_B'
    assert marker['no_retry_or_redraw'] and marker['all_children_reaped'] == resources['all_children_reaped']
    assert summary['scientific_gate'] == ('PASS_EXPLORATORY_SCOPE_ONLY' if good else 'FAIL_CLOSED')
    assert marker['status'] == ('COMPLETE_PASS_EXPLORATORY_SCOPE_ONLY' if good else 'CLOSED_FAIL')
    report = {'review_status': 'PASS_EXPLORATORY_SCOPE_ONLY' if good else 'FAIL_CLOSED_NO_PILOT_ADMISSION',
        'integrity_review_status': 'PASS_RETAINED_COMPLETE_OUTPUT_INTEGRITY' if complete and map_count == 852 else 'INCOMPLETE_OR_FAILED_OUTPUT_INTEGRITY',
        'panel': 'VAL_B', 'independent_audit': True, 'case_count_expected': 142,
        'case_count_observed': len(outcomes), 'complete': complete,
        'cases_expected': 142, 'cases_observed': len(outcomes), 'complete_maps_verified': map_count,
        'artifact_hashes_verified': artifact_count, 'OFF_comparisons_verified': off_count,
        'compatible_veto_witnesses_verified': witness_count, 'families': families, 'subgroups': subgroups,
        'all_nine_checks': checks, 'resources': resources, 'internal_CPU_charge_s': conservative_charge + controller_charge,
        'individual_wait4_CPU_sum_s': reaped, 'cumulative_children_CPU_s': cumulative_reaped,
        'cumulative_minus_individual_CPU_s': cumulative_reaped - reaped,
        'missing_outputs_in_failed_cases': missing_outputs, 'case_reviews': records,
        'A_remains_FAIL_CLOSED': True, 'additional_correction_allowed': False,
        'generation_search_tuning_or_rerun_by_reviewer': False, 'sky_values_opened_by_reviewer': False,
        'sha256': {'b_cases': digest(BASE / 'pilot_controls_20261008/validation_b_cases.json'),
            'b_outcomes': digest(OUT / 'outcomes.json'), 'b_summary': digest(OUT / 'summary.json'),
            'b_resource_receipt': digest(OUT / 'resource_receipt.json'), 'b_completion': digest(OUT / 'COMMITTED_PANEL.json')},
        'scope': 'Finite fixed synthetic families only; no sky false-alarm calibration, flux or ETI claim.'}
    (REVIEW / 'COMPLETE_VAL_B_OUTPUT_REVIEW.json').write_text(json.dumps(report, indent=2) + '\n')
    text = f"""# Independent retained-output review: fresh B\n\n{report['review_status']}. Reviewed {len(outcomes)} of 142 fixed identities, {map_count} complete maps, {artifact_count} artifact hashes, {off_count:,} OFF comparisons and {witness_count:,} compatible veto witnesses. All complete maps retain 21,660 valid drift/width hypotheses per carrier; all threshold hits, map winners, coupled endpoint witnesses and localized pre/post-OFF recovery records agree.\n\nAll original nine checks were independently recomputed from retained outcomes. This review performed no generation, scoring, tuning, rerun or sky reads. Original A remains FAIL_CLOSED and the one permitted operational development correction is exhausted.\n\nThe authoritative per-PID wait4 closures charge {charged:.6f} child CPU seconds. Cumulative child meter is {cumulative_reaped:.6f}; take the larger child meter and controller receipt/ledger measurement for a conservative total of {conservative_charge + controller_charge:.6f}. Any outer whole-controller charge must be reconciled by root before further resource admission. Rolling reservations are closed and none remain live. Bound child and final panel COMMITTED markers, full outputs and exact aggregate hashes were checked.\n\nSynthetic recovery qualifies only the preset family and linear-track scope. Single-row transient and nearby-OFF diagnostic behavior remains a limitation; no calibrated sky false-alarm or extraterrestrial claim follows.\n"""
    text += '\nFailed original checks: ' + (', '.join(k for k, v in checks.items() if not v) or 'none') + '.\n'
    text += '\n| Family | Observed/expected | All-active pre-OFF | All-active final | Cadences with survivors |\n| --- | --- | --- | --- | --- |\n'
    for family, row in families.items():
        text += f"| {family} | {row['observed']}/{row['expected']} | {row['all_primary_on_detected_before_off']} | {row['all_active_on_recovered']} | {row['cadences_with_any_survivor']} |\n"
    (REVIEW / 'COMPLETE_VAL_B_OUTPUT_REVIEW.md').write_text(text)
    print(json.dumps({k: report[k] for k in ('review_status', 'cases_observed', 'complete_maps_verified', 'artifact_hashes_verified', 'OFF_comparisons_verified', 'compatible_veto_witnesses_verified', 'all_nine_checks', 'internal_CPU_charge_s')}, indent=2))


if __name__ == '__main__':
    main()
