"""Independent array-based boundary audit and full sealed-record accounting."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from m43e_economical_bank import read_sealed, write_sealed
from m43af_scalar_audit import audit_acquisition
from seti_repeater import search_v0p6 as core, detector_m43u as detector
from seti_repeater.boundary_m43af import REFERENCES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43af_response'


def audit_fit(training, baseline, nulls, result):
    all_cases = training+[baseline]+list(nulls)
    incomplete = [c['name'] for c in all_cases if not c['complete'] or
                  any(m['coordinate'] is None for m in c['members'])]
    if incomplete:
        assert result['boundary'] is None and not result['feasible'] and result['grid'] == []
        assert result['reason'] == 'incomplete_or_undefined_evidence'
        assert result['affected_cases'] == incomplete
        return dict(passed=True, checked_grid_points=0, incomplete_cases=incomplete)
    values = np.asarray([[m['coordinate']['on'], m['coordinate']['off']]
                         for c in training for m in c['members']], dtype=float)
    if not len(values):
        assert result['reason'] == 'no_training_members' and result['boundary'] is None
        return dict(passed=True, checked_grid_points=0)
    quantiles = np.quantile(values, np.arange(33)/32, axis=0, method='higher')
    lows = [None]+sorted(set(quantiles[:, 0].tolist()))
    highs = sorted(set(quantiles[:, 1].tolist()))+[None]
    assert len(result['grid']) == len(lows)*len(highs)
    required = sorted(c['name'] for c in training if c['signal_present'] and
                      any(c['reference_recovered'][p] for p in REFERENCES))
    assert required and result['required_signal_cases'] == required
    feasible = []
    for i, row in enumerate(result['grid']):
        low, high = lows[i//len(highs)], highs[i % len(highs)]
        assert row['boundary'] == dict(on_lower=low, off_upper=high)
        recovered, leaks = [], []
        assert len(row['outcomes']) == len(all_cases)
        for c, observed in zip(all_cases, row['outcomes']):
            xy = np.asarray([[m['coordinate']['on'], m['coordinate']['off']]
                             for m in c['members']], dtype=float).reshape(-1, 2)
            passed = (xy[:, 0] >= (-np.inf if low is None else low)) & (xy[:, 1] < (np.inf if high is None else high))
            ids = [m['record_id'] for m, keep in zip(c['members'], passed) if keep]
            hit = any(rid in c['associated_record_ids'] for rid in ids)
            assert observed == dict(name=c['name'], signal_present=c['signal_present'],
                recovered=hit, final_members=len(ids), surviving_record_ids=ids)
            if hit and c['signal_present']:
                recovered.append(c['name'])
            if ids and not c['signal_present']:
                leaks.append(c['name'])
        losses = sorted(set(required)-set(recovered))
        ok = not losses and not leaks
        assert row['feasible'] == ok and row['required_signal_losses'] == losses
        assert row['leaking_control_or_baseline_cases'] == leaks
        assert row['recovered_signal_cases'] == len(recovered)
        if ok:
            feasible.append((len(recovered), -np.inf if low is None else low,
                             np.inf if high is None else high, row['boundary']))
    if feasible:
        best = max(x[0] for x in feasible)
        survivors = [x for x in feasible if x[0] == best]
        lowest = min(x[1] for x in survivors)
        survivors = [x for x in survivors if x[1] == lowest]
        chosen = max(survivors, key=lambda x:x[2])[3]
    else:
        chosen = None
    assert result['boundary'] == chosen and result['feasible'] == bool(feasible)
    return dict(passed=True, checked_grid_points=len(result['grid']),
                feasible_grid_points=len(feasible), checked_cases=len(all_cases))


def run(runtime):
    from m43af_response_study import validate, index_record
    from m43f_source_cache_preflight import build_context
    from m43r_joint_calibration import grid_context
    from m43aa_native_response import raw_window_score
    from m43s_profile_sensitivity import endpoint
    from seti_repeater import transfer_m43i as transfer
    from seti_repeater.boundary_m43af import case_outcome
    cfg = validate()
    decision = read_sealed(OUT/'model_decision.json')
    publication = read_sealed(OUT/'model_publication.json')
    assert publication['remote_verified'] and publication['model_decision_sha256'] == decision['result_sha256']
    freeze = decision['freeze_commit']
    validate(freeze)
    _, _, _, metadata, basis, parent, _, _ = build_context()
    bank, table, _ = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
    _, grid, _ = grid_context()
    on = [core.factor_table_for_scan(table, basis, f'epoch{e+1}_on') for e in range(3)]
    off = [core.factor_table_for_scan(table, basis, f'epoch{e+1}_off') for e in range(3)]
    records, sources = [], {}
    expected_names = {'baseline'} | {c['name'] for c in cfg['training_cases']}
    expected_names |= {f'null_training{i:03d}' for i in range(128)}
    expected_names |= {'historical__'+n for n in cfg['historical_sources'] if n != 'baseline'}
    if decision['feasible']:
        expected_names |= {c['name'] for c in cfg['validation_cases']}
        expected_names |= {f'null_validation{i:03d}' for i in range(128)}
    assert {p.name[:-8] for p in (OUT/'records').glob('*.json.gz')} == expected_names
    source_cfg = json.loads((ROOT/'config/m43o_real_stacks.json').read_text())
    native_checks = 0
    for path in sorted((OUT/'records').glob('*.json.gz')):
        r = read_sealed(path)
        assert r['freeze_commit'] == freeze and r['config_sha256'] == hashlib.sha256((ROOT/'config/m43af_response_study.json').read_bytes()).hexdigest()
        audit_acquisition(r['geometry_member_audit'], r['acquisition'], grid, on, off)
        if r['source']:
            old = read_sealed(ROOT/r['source']['file'])
            assert r['geometry_member_audit'] == old['geometry_member_audit']
            assert r['original_endpoints'] == old['endpoints']
            assert r['native_payload_identity'] == old['native_payload_identity']
            for pid in r['acquisition']['reused_complete_profile_ids']:
                assert r['acquisition']['profiles'][pid] == old['profiles'][pid]
            assert r['case'] == old['case']
            assert cfg['historical_sources'][r['case']['name']] == r['source']
        elif r['phase'] in ('training', 'validation'):
            cases = cfg['training_cases'] if r['phase'] == 'training' else cfg['validation_cases']
            assert r['case'] == next(c for c in cases if c['name'] == r['case']['name'])
        measurements = r['acquisition']['measurements']
        expected_members = []
        for m in measurements:
            defined = m['on']['defined'] and all(v['defined'] for v in m['off'].values())
            value = None
            if defined:
                scale = math.sqrt(2*m['spectral_width']+1)
                value = dict(on=m['on']['projection_mean']/scale,
                             off=max(v['projection_mean'] for v in m['off'].values())/scale)
            expected_members.append(dict(record_id=m['record_id'], coordinate=value))
        if r['phase'] == 'baseline' or r['phase'].startswith('null_'):
            associated = []
        else:
            association = endpoint(r['geometry_member_audit'], r['case']['reference_truth'], grid,
                np.stack(on, axis=1), basis, r['case']['strength'], 'audit')
            associated = association['associated_record_ids']
            for old_endpoint in r['original_endpoints']:
                assert old_endpoint['truth_association']['associated_record_ids'] == associated
        expected_summary = dict(name=r['case']['name'], panel=r['phase'],
            signal_present=r['case'].get('signal_present', False),
            complete=all(p['complete'] for p in r['acquisition']['profiles'].values()) and
                     all(m['coordinate'] is not None for m in expected_members),
            members=expected_members, associated_record_ids=associated,
            reference_recovered={p:next((old['recovered'] for old in r['original_endpoints'] if old['policy'] == p), False) for p in REFERENCES})
        assert r['summary'] == expected_summary
        links = r['acquisition']['links']
        profiles = r['acquisition']['profiles']
        reused_ids = r['acquisition']['reused_complete_profile_ids']
        assert len(set(reused_ids)) == len(reused_ids)
        assert all(profiles[pid]['complete'] for pid in reused_ids)
        counts = dict(retained_members=len(r['geometry_member_audit']['members']),
            eligible_before_remaining=len(measurements),
            eligible_passing_old_remaining=sum(l['eligible_before_remaining'] and l['old_remaining']['remaining_passed'] for l in links),
            requested_unique_profiles=len(profiles), reused_complete_profiles=len(reused_ids),
            newly_acquired_complete_profiles=sum(p['complete'] for p in profiles.values())-len(reused_ids),
            incomplete_profiles=sum(not p['complete'] for p in profiles.values()),
            member_profile_links=sum(len(l['profile_ids']) for l in links),
            undefined_member_measurements=sum(m['coordinate'] is None for m in expected_members))
        assert counts == r['acquisition']['counts']
        if r['phase'].startswith('null_'):
            shift_rows = cfg['training_native_shifts'] if r['phase'] == 'null_training' else cfg['heldout_native_shifts']
            ordinal = int(r['case']['name'][-3:])
            assert r['case']['shifts'] == shift_rows[ordinal]
            assert len(r['null_direct_native_checks']) == 432
            for d in r['null_direct_native_checks']:
                kind, e, t, w, pos = (d[k] for k in ('kind', 'epoch', 'template', 'width', 'support_index'))
                label = f'epoch{e+1}_{kind}'
                if label not in sources:
                    spec = next(s for s in source_cfg['sources'] if s['scan'] == label)
                    sources[label] = transfer.load_telescope_source(runtime/'sources'/label/source_cfg['window'], trusted_receipt_sha256=spec['receipt_sha256'])
                src = sources[label]
                factors = on[e][t] if kind == 'on' else off[e][t]
                idx = core.nearest_native_indices(src.geometry, factors*grid.support_hz[pos])
                # Independent oracle reads the ORIGINAL source at shifted indices.
                measured = raw_window_score(src, idx+r['case']['shifts'][e], [], w)['score']
                assert np.float32(measured).view('<u4') == np.float32(d['score']).view('<u4')
                native_checks += 1
        records.append(r)
    training = [r['summary'] for r in records if r['phase'] == 'training']
    # Restore the frozen ordering rather than file-system ordering assumptions.
    order = {c['name']:i for i, c in enumerate(cfg['training_cases'])}
    training.sort(key=lambda c:order[c['name']])
    baseline = next(r['summary'] for r in records if r['phase'] == 'baseline')
    nulls = sorted((r['summary'] for r in records if r['phase'] == 'null_training'), key=lambda c:c['name'])
    model = read_sealed(OUT/'training_grid.json.gz')
    assert model['result_sha256'] == decision['training_grid_sha256']
    grid_audit = audit_fit(training, baseline, nulls, model)
    by_phase = {}
    for r in records:
        by_phase.setdefault(r['phase'], []).append(r)
    expected_counts = dict(training=112, null_training=128, baseline=1,
                           historical_original=149, historical_additional=112)
    if decision['feasible']:
        expected_counts.update(validation=112, null_validation=128)
    assert {p:len(rs) for p, rs in by_phase.items()} == expected_counts
    measured_training = [index_record(r) for r in records if r['phase'] in ('training', 'baseline', 'null_training')]
    assert {v['file']:v for v in measured_training} == {v['file']:v for v in decision['inventory']}
    payloads = {p:{r['native_payload_identity'] for r in rs} for p, rs in by_phase.items()}
    overlap = payloads['training'].intersection(cfg['previous_native_payload_identities'])
    assert sorted(overlap) == decision['native_payload_overlap']
    assert decision['feasible'] == (model['feasible'] and not overlap)
    assert decision['training_distinct_payloads'] == len(payloads['training'])
    assert decision['null_eligible_members'] == sum(len(c['members']) for c in nulls)
    if decision['feasible']:
        validation_overlap = payloads['validation'].intersection(set(cfg['previous_native_payload_identities']) | payloads['training'])
    else:
        validation_overlap = set()
    outcomes, comparisons = [], {}
    if decision['feasible']:
        for phase, rows in by_phase.items():
            evaluated = [dict(case_outcome(r['summary'], decision['boundary']), phase=phase) for r in rows]
            outcomes.extend(evaluated)
            signals = [r for r in evaluated if r['signal_present']]
            controls = [r for r in evaluated if not r['signal_present']]
            losses = {p:[r['case']['name'] for r, out in zip(rows, evaluated) if r['case'].get('signal_present') and
                next((old['recovered'] for old in r['original_endpoints'] if old['policy'] == p), False) and not out['recovered']]
                for p in cfg['comparison_references']}
            comparisons[phase] = dict(signal_cases=len(signals), recovered_signals=sum(r['recovered'] for r in signals),
                control_cases=len(controls), leaking_controls=sum(r['final_members'] > 0 for r in controls),
                false_control_associations=sum(r['recovered'] for r in controls), losses=losses,
                complete_evidence=all(r['summary']['complete'] for r in rows))
            counts = comparisons[phase]
            reference_leaks = sum(not r['case'].get('signal_present', False) and
                next((old['final_members'] > 0 for old in r['original_endpoints'] if old['policy'] == 'neighbor9'), False) for r in rows)
            gates = dict(no_reference_signal_losses=all(not names for names in losses.values()),
                zero_control_members=counts['leaking_controls'] == 0,
                zero_false_control_associations=counts['false_control_associations'] == 0,
                complete_evidence=counts['complete_evidence'])
            if phase in ('training', 'validation', 'historical_original', 'historical_additional'):
                gates['strict_control_leak_reduction'] = counts['leaking_controls'] < reference_leaks
            counts['conditions'] = gates
            counts['development_gate_passed'] = all(gates.values())
    diagnostics = []
    for r in records:
        if r['phase'].startswith('historical'):
            associated = set(r['summary']['associated_record_ids'])
            weak = [m for m in r['acquisition']['measurements'] if m['record_id'] in associated and not m['old_remaining']['remaining_passed']]
            diagnostics.append(dict(name=r['case']['name'], phase=r['phase'], signal_present=r['case']['signal_present'],
                counts=r['acquisition']['counts'], associated_old_weak_members=len(weak),
                weak_profile_coordinates=[dict(record_id=m['record_id'], width=m['spectral_width'],
                    old_remaining_score=m['old_remaining']['remaining_score'],
                    coordinate=next(s['coordinate'] for s in r['summary']['members'] if s['record_id'] == m['record_id'])) for m in weak]))
    result = dict(milestone='M43AF', complete=True, freeze_commit=freeze,
        model_decision_sha256=decision['result_sha256'], model_feasible=decision['feasible'], boundary=decision['boundary'],
        reason=decision['reason'], phase_counts=expected_counts, inventory=[index_record(r) for r in records],
        null_original_source_checks=native_checks, scalar_audit_passed=True, boundary_audit=grid_audit,
        native_payload_counts={p:len(v) for p, v in payloads.items()}, comparisons=comparisons,
        training_native_overlap=sorted(overlap), validation_native_overlap=sorted(validation_overlap),
        historical_diagnostics=diagnostics, outcomes=outcomes,
        native_validation_opened=decision['feasible'], new_observing_sequences=0,
        joint_development_gate_passed=decision['feasible'] and not overlap and not validation_overlap and all(v['development_gate_passed'] for v in comparisons.values()),
        general_adoption_qualified=False, physical_false_alarm_probability_measured=False,
        astronomical_candidate_claimed=False)
    from m43af_response_study import save
    save(OUT/'result.json', result)
    save(OUT/'audit.json', dict(passed=True, freeze_commit=freeze, files=len(records),
        pinned_files=len(cfg['pinned_sha256']), original_source_checks=native_checks, boundary_audit=grid_audit))
    print(json.dumps(dict(passed=True, phases=expected_counts, model_feasible=decision['feasible'], native_checks=native_checks)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--runtime-root', type=Path, required=True)
    run(p.parse_args().runtime_root)
