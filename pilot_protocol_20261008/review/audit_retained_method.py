"""Inert reviewer of closed saved method results; no generation/search/source IO.

Full audit: python audit_retained_method.py --admission ACTUAL_ROOT_RECEIPT.json
One saved case, in a fresh process: add --case-id EXACT_METHOD_CASE_ID.
The bounded command verifies retained-map -> hit/veto/recovery relationships.
It does not reproduce preprocessing or detector scores from raw power arrays.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'results/radio_pilot_method_study_20261008'
REVIEW = Path(__file__).resolve().parent

def project_path(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(BASE):
        raise ValueError('Evidence path escapes the restored current project root')
    return resolved

def read(path):
    return json.loads(project_path(path).read_text())

def digest(path):
    return hashlib.sha256(project_path(path).read_bytes()).hexdigest()

def close(a, b, tol=1e-8):
    assert math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol), (a, b)

def prerequisite_paths(master, master_path, recorded_root=None):
    """Resolve byte-identical archived prerequisites without editing records."""
    if recorded_root is not None:
        if not recorded_root.is_absolute():
            raise ValueError('The explicitly recorded project root must be absolute')
        recorded_root = recorded_root.resolve()
    paths, mappings = {}, []
    for key, value in master['paths'].items():
        recorded = Path(value)
        was_rebased = False
        if recorded.is_absolute():
            if recorded_root is None:
                restored = recorded.resolve()
            else:
                try:
                    relative = recorded.resolve().relative_to(recorded_root)
                except ValueError:
                    raise ValueError('Prerequisite is outside the explicitly recorded project root: ' + key)
                restored = (BASE / relative).resolve()
                was_rebased = True
        else:
            restored = (master_path.parent / recorded).resolve()
        if not restored.is_relative_to(BASE):
            raise ValueError('Restored prerequisite escapes the current project root: ' + key)
        observed = digest(restored)
        if observed != master['sha256'][key]:
            raise ValueError('Restored prerequisite bytes differ from the original admission: ' + key)
        paths[key] = restored
        mappings.append({'key': key, 'recorded_path': value, 'restored_path': str(restored),
            'rebased_explicitly': was_rebased, 'expected_SHA256': master['sha256'][key],
            'observed_restored_SHA256': observed, 'identical_admitted_bytes': True})
    return paths, mappings

def verify_cases(cases, outcomes, resources, master, master_path, selected_id=None):
    import numpy as np
    observed = {x['case_id']: x for x in outcomes}
    closures = {x['case_id']: x for x in resources['closures']}
    artifact_count = map_count = off_count = witness_count = 0
    records = []
    missing_outputs = {}
    widths = (1, 3, 9, 33)
    for index, case in enumerate(cases):
        if selected_id is not None and case['case_id'] != selected_id:
            continue
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
        assert reservation['case_id'] == identity and reservation['cpu_reserved_seconds'] == 250
        assert reservation['status'] == 'RESERVED_BEFORE_CHILD_SUBMIT'
        assert reservation['master_admission_SHA256'] == digest(master_path)
        assert admission['allowed_case_ids'] == [identity] and admission['status'] == 'ADMITTED_METHOD_STUDY_SINGLE_CASE'
        claim = read(BASE / 'pilot_protocol_20261008/method_study_claims' / (hashlib.sha256(identity.encode('ascii')).hexdigest() + '.json'))
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
        assert child['case_id'] == identity and child['panel'] == 'METHOD_STUDY' and child['qualification'] is False and child['data_integrity_ok'] and child['failure'] is None
        for key in ('all_active_on_recovered', 'any_localized_on_recovered', 'pre_OFF_all_active_recovery', 'pre_OFF_any_active_recovery', 'survivor_count', 'ON_threshold_carrier_count'):
            assert child[key] == outcome[key]
        close(outcome['worker_snapshot_cpu_s'], child['cpu_s'])
        close(outcome['cpu_s'], closure['cpu_charged_seconds'])
        close(closure['cpu_charged_seconds'], max(closure['wait4_whole_child_cpu_s'], child['cpu_s']))
        close(closure['unused_reservation_refunded_seconds'], max(0, 250 - closure['cpu_charged_seconds']))
        assert closure['child_exit_code'] == 0 and closure['case_integrity_passed']
        assert closure['wait4_whole_child_cpu_s'] <= 250 and closure['whole_child_wall_s'] <= 1800 and closure['wait4_peak_rss_bytes'] <= 4 * 1024**3
        committed = read(p / 'COMMITTED.json')
        assert committed['case_id'] == identity and committed['panel'] == 'METHOD_STUDY' and committed['qualification'] is False and committed['status'] == 'COMPLETED_CASE_ONLY'
        assert committed['caps_passed'] and committed['no_retry_or_redraw']
        assert committed['artifact_manifest_SHA256'] == digest(p / 'artifact_manifest.json')
        manifest = read(p / 'artifact_manifest.json')
        for name, value in manifest.items():
            assert digest(p / name) == value['SHA256'] and (p / name).stat().st_size == value['size_bytes'], (identity, name)
            artifact_count += 1
        receipt = read(p / 'resource_receipt.json')
        assert receipt['caps_passed'] and receipt['caps']['exclusive_cpu_allocation_seconds'] == 250
        assert receipt['cpu_s'] == child['cpu_s'] and receipt['wall_s'] == child['wall_s']
        assert receipt['cpu_s'] <= 250 and receipt['wall_s'] <= 1800 and receipt['peak_rss_bytes'] <= 4 * 1024**3
        meta = read(p / 'scan_map_metadata.json')
        truth = read(p / 'truth.json')
        hits = read(p / 'all_ON_threshold_carriers.json')
        detector_summary = read(p / 'detector_summary.json')
        recovery = read(p / 'localized_recovery.json')
        assert truth['case_id'] == identity and truth['seed_sha256'] == case['seed_sha256'] == hashlib.sha256(identity.encode('ascii')).hexdigest()
        assert len(meta) == 6
        with np.load(project_path(p / 'geometry_arrays.npz'), allow_pickle=False) as z:
            geometry = {k: z[k].copy() for k in z.files}
        grid = geometry['drift_grid_hz_s']
        assert grid.shape == (5415,) and grid[0] == -4 and grid[-1] == 4 and grid[2707] == 0
        maps = {}
        expected_hits = set()
        hit_index = {(h['scan_id'], h['reference_carrier_index']): h for h in hits}
        assert len(hit_index) == len(hits)
        core_frequencies = None
        for scan_index, m in enumerate(meta):
            with np.load(project_path(p / m['array_file']), allow_pickle=False) as z:
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
        assert child['per_active_ON_scan'] == recovery['per_active_ON_scan']
        maxima = {m['scan_id']: float(np.max(maps[m['scan_id']]['maximum_robust_box_track_score'])) for m in meta if m['role'] == 'ON'}
        assert child['ON_global_maximum_robust_score_by_scan'] == maxima
        for sid in maxima:
            local_hits = [h for h in hits if h['scan_id'] == sid]
            assert child['ON_threshold_carrier_count_by_scan'][sid] == len(local_hits)
            assert child['ON_surviving_carrier_count_by_scan'][sid] == sum(h['disposition'] == 'SURVIVOR_EXPLORATORY' for h in local_hits)
        for sid, r in recovery['per_active_ON_scan'].items():
            stage = ('LOCALIZED_SURVIVOR' if r['final_localized_recovery'] else 'LOCALIZED_HITS_OFF_VETOED' if r['pre_OFF_localized_recovery'] else 'NO_ON_THRESHOLD_HIT' if maxima[sid] < 10 else 'ON_HITS_NOT_LOCALIZED')
            assert child['loss_stage_by_active_ON_scan'][sid] == stage
        records.append({'case_id': identity, 'family': case['family'], 'status': 'COMPLETE', 'maps': 6, 'artifact_hashes': len(manifest), 'raw_ON_carriers': len(hits), 'surviving_ON_carriers': survivors, 'whole_CPU_s': outcome['cpu_s'], 'peak_RSS_bytes': outcome['peak_rss_bytes']})
    return {'artifact_hashes_verified': artifact_count, 'complete_maps_verified': map_count, 'OFF_comparisons_verified': off_count, 'compatible_veto_witnesses_verified': witness_count, 'case_reviews': records, 'missing_outputs_in_failed_cases': missing_outputs}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--case-id')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--recorded-project-root', type=Path,
        help='Explicit original absolute root; rebase admitted prerequisites read-only beneath current BASE')
    args = parser.parse_args()
    marker = read(OUT / 'COMMITTED_PANEL.json')
    assert marker['panel'] == 'METHOD_STUDY' and marker['qualification'] is False
    assert marker['scientific_gate'] == 'EXPLORATORY_METHOD_STUDY_ONLY' and marker['all_children_reaped']
    master_path = args.admission.resolve()
    if not master_path.is_relative_to(BASE):
        raise ValueError('The restored original admission must be inside the current project root')
    master = read(master_path)
    assert master['status'] == 'ADMITTED_METHOD_STUDY_ROLLING' and master['qualification_override'] is False
    paths, path_mappings = prerequisite_paths(master, master_path, args.recorded_project_root)
    cases = read(paths['method_cases']); outcomes = read(OUT / 'outcomes.json')
    summary = read(OUT / 'summary.json'); resources = read(OUT / 'resource_receipt.json')
    ledger = read(OUT / 'rolling_cpu_ledger.json'); ids = [c['case_id'] for c in cases]
    assert len(cases) == len(set(ids)) == 64 and master['allowed_case_ids'] == ids
    assert digest(paths['method_cases']) == '554a54d9ddfa1c0f82f0932ee93ba2bb652542588c65fbd4be56c144b7c4d2f4'
    observed = {x['case_id']: x for x in outcomes}
    assert len(observed) == len(outcomes) and set(observed) <= set(ids)
    for name in ('outcomes', 'summary', 'resource_receipt'):
        assert marker[name + '_SHA256'] == digest(OUT / (name + '.json'))
    b_marker = read(paths['b_completion']); b_summary = read(paths['b_summary'])
    assert b_marker['status'] == 'CLOSED_FAIL' and b_summary['scientific_gate'] == 'FAIL_CLOSED'
    for key in ('outcomes', 'summary', 'resource_receipt'):
        assert b_marker[key + '_SHA256'] == digest(paths['b_' + key])
    input_hashes = {'method_cases': digest(paths['method_cases']),
        'method_outcomes': digest(OUT / 'outcomes.json'), 'method_summary': digest(OUT / 'summary.json'),
        'method_resource_receipt': digest(OUT / 'resource_receipt.json'), 'method_completion': digest(OUT / 'COMMITTED_PANEL.json'),
        'b_cases': digest(paths['validation_b_cases']), 'b_outcomes': digest(paths['b_outcomes']),
        'b_summary': digest(paths['b_summary']), 'b_resource_receipt': digest(paths['b_resource_receipt']),
        'b_completion': digest(paths['b_completion'])}
    if args.case_id is not None:
        assert args.case_id in ids and marker['status'] == 'COMPLETE_EXPLORATORY_METHOD_STUDY_ONLY'
        assert observed[args.case_id]['data_integrity_ok'] and not observed[args.case_id]['failure']
        result = verify_cases(cases, outcomes, resources, master, master_path, args.case_id)
        assert result['complete_maps_verified'] == 6 and len(result['case_reviews']) == 1
        result.update(review_status='PASS_BOUNDED_SAVED_RESULT_VERIFICATION', panel='METHOD_STUDY',
            case_id=args.case_id, independent_audit=True, qualification=False, sha256=input_hashes,
            generation_search_or_redraw=False, scope='One saved case: map/hit/veto/recovery consistency only; raw preprocessing and scores were not rerun.')
        target = args.output or REVIEW / ('METHOD_SAVED_CASE_' + str(ids.index(args.case_id)).zfill(3) + '_REPRODUCTION.json')
    else:
        claim = read(BASE / 'pilot_protocol_20261008/method_study_claims/controller_claim.json')
        assert claim['case_ids'] == ids and claim['master_admission_SHA256'] == digest(master_path) and claim['no_restart_or_redraw']
        assert [x['case_id'] for x in read(OUT / 'full_panel_plan.json')['all_slots']] == ids
        result = verify_cases(cases, outcomes, resources, master, master_path)
        missing = [c['case_id'] for c in cases if c['case_id'] not in observed]
        failed = [c['case_id'] for c in cases if c['case_id'] in observed and (not observed[c['case_id']].get('data_integrity_ok') or observed[c['case_id']].get('failure'))]
        def counts(members):
            values = [observed[c['case_id']] for c in members if c['case_id'] in observed]
            valid = [v for v in values if v.get('data_integrity_ok') and not v.get('failure')]
            return {'expected': len(members), 'observed': len(values), 'integrity_valid': len(valid),
                'pre_OFF_all_active_recovery': sum(bool(v.get('pre_OFF_all_active_recovery')) for v in valid),
                'final_all_active_recovery': sum(bool(v.get('all_active_on_recovered')) for v in valid),
                'final_any_active_recovery': sum(bool(v.get('any_localized_on_recovered')) for v in valid),
                'all_active_recovery_lost_after_OFF': sum(bool(v.get('pre_OFF_all_active_recovery')) and not bool(v.get('all_active_on_recovered')) for v in valid)}
        assert summary['counts'] == counts(cases)
        for label, key in [('declared_ideal_score','nominal_ideal_box_score'),('drift_hz_s','drift_hz_s'),('intrinsic_width_channels','intrinsic_width_channels'),('active_scan_indices','active_scan_indices'),('reference_native_offset','reference_native_offset')]:
            groups = {}
            for c in cases:
                groups.setdefault(json.dumps(c[key], separators=(',', ':')), []).append(c)
            assert summary['groups'][label] == {name: counts(members) for name, members in groups.items()}
        assert summary['missing_case_ids'] == missing and summary['failed_case_ids'] == failed
        for c, cell in zip(cases, summary['cells']):
            assert cell['case_id'] == c['case_id'] and cell['outcome'] == observed.get(c['case_id'])
        charged = max(resources['conservative_children_cpu_s_charged'], resources['children_cpu_s_reaped'], ledger['cpu_charged_closed_children'], sum(x['cpu_charged_seconds'] for x in resources['closures']))
        controller = max(resources['controller_cpu_s'], ledger['controller_cpu_s_observed'])
        assert ledger['cpu_reserved_live_children'] == 0 and ledger['live_case_ids'] == [] and ledger['status'] == 'CLOSED_NO_RETRY'
        assert resources['aggregate_cpu_allocation_seconds'] == master['budget']['aggregate_cpu_allocation_seconds'] <= 6000
        individual_reaped = sum(x.get('wait4_whole_child_cpu_s', 0) for x in resources['closures'])
        admitted_allocation = resources['aggregate_cpu_allocation_seconds']
        good = not missing and not failed and len(outcomes) == 64 and result['complete_maps_verified'] == 384 and resources['cpu_budget_passed'] and resources['all_children_reaped'] and resources['controller_failure'] is None and charged + controller <= admitted_allocation
        assert summary['qualification'] is False and summary['scientific_gate'] == 'EXPLORATORY_METHOD_STUDY_ONLY'
        assert marker['status'] == ('COMPLETE_EXPLORATORY_METHOD_STUDY_ONLY' if good else 'CLOSED_PARTIAL_OR_FAILED')
        result.update(review_status='PASS_INDEPENDENT_METHOD_STUDY_OUTPUT_AUDIT' if good else 'PARTIAL_OR_FAILED_METHOD_STUDY_OUTPUT_AUDIT',
            panel='METHOD_STUDY', independent_audit=True, case_count_expected=64, case_count_observed=len(outcomes), complete=good,
            qualification=False, sha256=input_hashes, descriptive_counts=counts(cases), groups=summary['groups'],
            missing_case_ids=missing, failed_case_ids=failed, whole_CPU_s_charged=charged + controller,
            individual_wait4_CPU_sum_s=individual_reaped, cumulative_children_CPU_s=resources['children_cpu_s_reaped'],
            A_remains_FAIL_CLOSED=True, B_remains_FAIL_CLOSED=True, generation_search_tuning_or_redraw=False,
            telescope_or_source_values_opened=False, scope='n=1 per heterogeneous cell; descriptive method evidence only, no validation or sky qualification.')
        target = args.output or REVIEW / 'COMPLETE_METHOD_STUDY_OUTPUT_REVIEW.json'
    result.update(status=result['review_status'], original_admission_SHA256=digest(master_path),
        original_admission_bytes_modified=False, recorded_project_root=str(args.recorded_project_root) if args.recorded_project_root is not None else None,
        restored_project_root=str(BASE), prerequisite_path_mappings=path_mappings)
    target = target.resolve()
    if not target.is_relative_to(BASE):
        raise ValueError('Review receipt output must remain inside the current project root')
    if target.suffix != '.json':
        raise ValueError('A new JSON review receipt path is required')
    markdown = project_path(target.with_suffix('.md')) if args.case_id is None else None
    if target.exists() or (markdown is not None and markdown.exists()):
        raise ValueError('Refuse to overwrite retained evidence or an existing review receipt')
    with target.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    if args.case_id is None:
        project_path(target.with_suffix('.md')).write_text(f"# Independent saved-result method audit\n\n{result['review_status']}. Verified {result['case_count_observed']}/64 fixed cells, {result['complete_maps_verified']} complete maps, {result['artifact_hashes_verified']} artifact hashes, {result['OFF_comparisons_verified']} OFF comparisons and {result['compatible_veto_witnesses_verified']} endpoint-compatible veto witnesses.\n\nAll retained-map winners, threshold-carrier retention, OFF classifications, originating-ON endpoint recovery, loss-stage labels and descriptive groups agree. Charge {result['whole_CPU_s_charged']:.6f} whole child/controller CPU seconds. Both validations remain failed closed. No generation, scoring, redraw or telescope/source values were used by this review. Qualification remains false.\n\nThe --case-id command verifies one saved case in a fresh process and creates a separate bounded reproduction receipt. It checks map/hit/veto/recovery consistency; it does not rerun raw preprocessing or detector scores.\n")
    print(json.dumps({k: result[k] for k in ('review_status', 'complete_maps_verified', 'artifact_hashes_verified', 'OFF_comparisons_verified')}, indent=2))

if __name__ == '__main__':
    main()
