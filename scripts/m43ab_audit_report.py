"""Post-run accounting audit, without changing frozen M43AB endpoints."""
import copy
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from m43s_profile_sensitivity import endpoint
from m43ab_attribution import costs
from seti_repeater import detector_m43u as detector, search_v0p6 as core
from seti_repeater.attribution_m43ab import POLICIES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ab_attribution'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    cfg = json.loads((ROOT/'config/m43ab_attribution.json').read_text())
    result = read_sealed(OUT/'result.json')
    for p, h in cfg['pinned_sha256'].items(): assert sha(ROOT/p) == h, p
    freeze = read_sealed(OUT/'public_freeze.json')
    assert freeze['remote_verified'] and freeze['commit'] == result['freeze_commit']
    anchors = read_sealed(OUT/'anchors.json')
    assert anchors['all_96_arrays_exact'] and anchors['all_48_native_gathers_exact']
    assert anchors['calibration_restored_exactly'] and anchors['new_null_rows'] == 0
    _, _, _, metadata, basis, parent, _, _ = build_context()
    bank, table, bridge = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
    assert bridge == cfg['bridge']
    _, grid, _ = grid_context()
    factors = np.stack([core.factor_table_for_scan(table, basis, f'epoch{e+1}_on') for e in range(3)], axis=1)
    history = {}
    with gzip.open(ROOT/'results_m43z_joint_controls/case_audits.jsonl.gz', 'rt') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if rec['case']['case_index'] in cfg['historical_cases']:
                    history[rec['case']['case_index']] = rec
    specs = {c['name']:c for c in cfg['cases']}
    expected_names = set(specs) | {'baseline'}
    assert {r['name'] for r in result['inventory']} == expected_names
    assert len(result['inventory']) == 149
    rows = []; native_checks = 0; members = 0; decisions = 0; replays = 0
    identities = defaultdict(list); by_case = {}; alias_costs = []; response_counts = Counter()
    for item in result['inventory']:
        path = ROOT/item['file']; assert sha(path) == item['file_sha256']
        rec = json.loads(gzip.decompress(path.read_bytes()))
        assert rec['result_sha256'] == item['record_sha256'] == detector.digest({k:v for k,v in rec.items() if k != 'result_sha256'})
        case = rec['case']; name = case['name']; by_case[name] = rec
        assert rec['freeze_commit'] == result['freeze_commit']
        assert rec['config_sha256'] == sha(ROOT/'config/m43ab_attribution.json')
        if name != 'baseline': assert case == specs[name]
        audit = rec['reference_audit']; ids = [m['record_id'] for m in audit['members']]
        assert len(ids) == len(set(ids))
        members += len(ids)
        payload = {k:v for k,v in audit['overlay'].items() if k in ('patch_payloads', 'background_provenance')}
        assert detector.digest(payload) == rec['native_payload_identity'] == item['native_payload_identity']
        identities[rec['native_payload_identity']].append(name)
        assert rec['centered_receipt']['signatures_sha256'] == detector.digest(rec['centered_signatures'])
        assert rec['centered_receipt']['queries_sha256'] == detector.digest(rec['centered_receipt']['queries'])
        assert set(rec['centered_signatures']) == set(rec['original_signatures']) == set(ids)
        assert len(rec['direct_checks']) == rec['centered_receipt']['direct_anchor_checks']
        assert all(c['exact'] for c in rec['direct_checks']); native_checks += len(rec['direct_checks'])
        orig_alias = {r['record_id']:r for r in rec['original_alias']['records']}
        new_alias = {r['record_id']:r for r in rec['centered_alias']['records']}
        assert set(orig_alias) == set(new_alias) == set(ids)
        new_evidence = {e['record_id']:e for e in rec['new_confirmation_evidence']}
        assert set(new_evidence) == set(ids)
        old_rejected = set()
        for m in audit['members']:
            rid = m['record_id']; active = m['active_epochs_zero_based']
            assert [s['epoch_zero_based'] for s in rec['centered_signatures'][rid]] == active
            for s in rec['centered_signatures'][rid]:
                assert s['offset_from_prediction_hz'] == (s['peak_frequency_mhz']-s['predicted_mid_mhz'])*1e6
            if m['physical_disposition'] == 'rfi_veto_receiver_frame_alias' and m['meets_diagnostic_rank_cut']:
                old_rejected.add(rid)
            agreement = new_evidence[rid]['agreement']
            assert agreement['correlation_floor'] == 0.8
            assert agreement['radius_proxy_bins'] == max(1, m['spectral_width_channels']//2)
            for e in agreement['epochs']:
                corr = e['correlation']
                assert corr is None or -1.000000000001 <= corr <= 1.000000000001
                veto = corr is not None and corr >= .8 and e['off_maximum'] >= 5.5
                assert e['vetoed'] == veto
                response_counts['measured_epoch_responses'] += 1
            assert agreement['vetoed'] == any(e['vetoed'] for e in agreement['epochs'])
        assert rec['alias_veto_members'] == len(old_rejected)
        restored_audits = {}
        assert set(rec['policy_decisions']) == set(cfg['policies'])
        for policy, ds in rec['policy_decisions'].items():
            assert [d['record_id'] for d in ds] == ids; decisions += len(ds)
            a = copy.deepcopy(audit)
            for m, d in zip(a['members'], ds):
                if policy in POLICIES:
                    e = new_evidence[m['record_id']]; rejection = []
                    if policy != 'centered_receiver' and e['agreement']['vetoed']:
                        rejection.append('centered_ON_OFF_agreement')
                    if policy == POLICIES[-1] and not e['remaining']['remaining_passed']:
                        rejection.append('remaining_aggregate_below_5p5')
                    assert d['rejections'] == rejection
                    prior_disposition = new_alias[m['record_id']]['member_disposition']
                    passes = prior_disposition == 'pending_receiver_alias_evaluation' and not rejection
                    assert d['passes_evaluated_physical_vetoes'] == passes
                m.update({k:d[k] for k in ('passes_evaluated_physical_vetoes', 'physical_disposition')})
            final = [m for m in a['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']]
            assert len(final) == rec['final_counts'][policy]
            a['final_diagnostic_survivors'] = len(final); restored_audits[policy] = a
            if name != 'baseline':
                row = next(r for r in rec['endpoints'] if r['policy'] == policy)
                association = endpoint(a, case['reference_truth'], grid, factors, basis, case['strength'], path.name)
                assert association == row['truth_association']
                assert row['recovered'] == association['recovered'] and row['final_members'] == len(final)
                rows.append(row)
            if policy in POLICIES:
                released_final = sorted(m['record_id'] for m in final if m['record_id'] in old_rejected)
                alias_costs.append(dict(name=name, panel=case['panel'], policy=policy,
                    signal_present=case.get('signal_present'), old_alias_veto_members=len(old_rejected),
                    released_final_member_ids=released_final))
        if case['panel'] == 'historical':
            old = history[case['original_case_index']]
            assert audit == old['reference_audit'] and rec['old_confirmation_evidence'] == old['confirmation_evidence']
            for p, ds in old['policy_decisions'].items():
                assert rec['policy_decisions'][p] == [dict(record_id=d['record_id'],
                    passes_evaluated_physical_vetoes=d['passes_evaluated_physical_vetoes'],
                    physical_disposition=d['physical_disposition'], rejections=d['m43z_rejections']) for d in ds]
            replays += 1
        elif name == 'baseline':
            old = read_sealed(ROOT/'results_m43z_joint_controls/baseline.json')
            assert audit == old['audits']['neighbor9']
            assert rec['final_counts'] == result['baseline_counts']
    assert sorted(rows, key=lambda r:(r['name'],r['policy'])) == sorted(result['endpoints'], key=lambda r:(r['name'],r['policy']))
    assert len(rows) == 148*7 and native_checks == result['direct_native_checks']
    assert result['distinct_native_payloads'] == len(identities)
    assert replays == 36 and result['comparisons'] == costs(result['endpoints'], result['baseline_counts'])
    for summary in result['summary']:
        ss = [r for r in rows if r['panel'] == summary['panel'] and r['policy'] == summary['policy']]
        signal = [r for r in ss if r['signal_present']]; control = [r for r in ss if not r['signal_present']]
        assert summary['signal_inputs'] == len(signal) and summary['control_inputs'] == len(control)
        assert summary['recovered_signals'] == sum(r['recovered'] for r in signal)
        assert summary['leaking_controls'] == sum(r['final_members'] > 0 for r in control)
        assert summary['false_control_associations'] == sum(r['recovered'] for r in control)
    pairs = []
    for case in cfg['cases']:
        if case['panel'] != 'fresh' or case['case_type'] not in ('mixed-unequal', 'distributed17-moderate-OFF'): continue
        kind = 'combined-unequal' if case['case_type'] == 'mixed-unequal' else 'distributed17'
        other = next(c for c in cfg['cases'] if c['panel'] == 'fresh' and c['case_type'] == kind
            and (c['score_index'],c['local_template'],c['active_epochs']) == (case['score_index'],case['local_template'],case['active_epochs']))
        for p in cfg['policies']:
            a = next(r for r in by_case[other['name']]['endpoints'] if r['policy'] == p)
            b = next(r for r in by_case[case['name']]['endpoints'] if r['policy'] == p)
            pairs.append(dict(signal_only=other['name'], mixed=case['name'], policy=p,
                              signal_only_recovered=a['recovered'], mixed_recovered=b['recovered'],
                              paired_loss=a['recovered'] and not b['recovered']))
    write_sealed(OUT/'paired_signal_costs.json', dict(comparisons=pairs, alias_release_costs=alias_costs))
    write_sealed(OUT/'artifact_validation.json', dict(passed=True, public_freeze=result['freeze_commit'],
        pinned_files=len(cfg['pinned_sha256']), sealed_inputs=149, historical_replays=replays,
        endpoints_including_baseline=1043, reference_members=members, policy_member_decisions=decisions,
        direct_native_checks=native_checks, all_96_arrays_exact=True, all_48_native_gathers_exact=True,
        distinct_native_payloads=len(identities), identity_groups=dict(identities),
        response_counts=dict(response_counts), new_rule_adopted=False, new_null_rows=0))
    print(json.dumps(dict(passed=True, inputs=149, historical_replays=replays, members=members,
                         decisions=decisions, direct_native_checks=native_checks, distinct_payloads=len(identities))))


if __name__ == '__main__': run()
