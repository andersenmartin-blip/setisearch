"""Audit sealed M43AD evidence without retuning a scientific endpoint."""
import copy
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43ac_dual_evidence import context
from m43ad_geometry import costs
from m43s_profile_sensitivity import endpoint
from seti_repeater import detector_m43u as detector, search_v0p6 as core
from seti_repeater.attribution_m43ad import attributed_signatures, POLICIES
from seti_repeater.receiver_v0p6 import _predicted_midpoint_hz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ad_geometry'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def read_input(path):
    r = json.loads(gzip.decompress(path.read_bytes()))
    assert r['result_sha256'] == detector.digest({k:v for k,v in r.items() if k != 'result_sha256'})
    return r


def run():
    cfg = json.loads((ROOT/'config/m43ad_geometry.json').read_text())
    result = read_sealed(OUT/'result.json'); freeze = read_sealed(OUT/'public_freeze.json')
    assert freeze['remote_verified'] and freeze['commit'] == result['freeze_commit']
    for p,h in cfg['pinned_sha256'].items(): assert sha(ROOT/p) == h,p
    _,metadata,basis,parent,pt,bank,table,original,grid,start = context()
    on = [core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)]
    off = [core.factor_table_for_scan(table,basis,f'epoch{e+1}_off') for e in range(3)]
    factors = np.stack(on,axis=1)
    anchors = read_sealed(OUT/'anchors.json')
    assert anchors['all_96_arrays_exact'] and anchors['all_48_native_gathers_exact']
    assert anchors['calibration_restored_exactly'] and anchors['new_null_rows'] == 0
    expected = {c['name']:c for c in cfg['cases']}
    assert {i['name'] for i in result['inventory']} == set(expected)|{'baseline'}
    assert len(result['inventory']) == 150
    totals = Counter(); endpoints = []; payloads = set(); selections = Counter(); by_case = {}
    for item in result['inventory']:
        path = ROOT/item['file']; assert sha(path) == item['file_sha256']
        rec = read_input(path); case = rec['case']; name = case['name']; by_case[name] = rec
        assert rec['result_sha256'] == item['record_sha256']
        assert rec['freeze_commit'] == result['freeze_commit']
        assert rec['config_sha256'] == sha(ROOT/'config/m43ad_geometry.json')
        if name != 'baseline': assert case == expected[name]
        audit = rec['reference_audit']; members = audit['members']
        ids = [m['record_id'] for m in members]; assert len(set(ids)) == len(ids)
        payload = {k:v for k,v in audit['overlay'].items() if k in ('patch_payloads','background_provenance')}
        assert detector.digest(payload) == rec['native_payload_identity'] == item['native_payload_identity']
        payloads.add(rec['native_payload_identity'])
        selected,receipt,geometry = attributed_signatures(members,rec['original_signatures'],
            rec['centered_signatures'],on,grid)
        assert (selected,receipt,geometry) == (rec['geometry_signatures'],rec['geometry_receipt'],rec['geometry_evidence'])
        for rows in geometry.values(): selections.update(r['selected_measurement'] for r in rows)
        alias = {r['record_id']:r for r in rec['geometry_alias']['records']}
        orig = {r['record_id']:r for r in rec['original_alias']['records']}
        assert set(alias) == set(orig) == set(ids)
        # Exhaustive pairwise oracle has no frequency bucket pruning. Reuse
        # only the unchanged, original track-identity partition.
        qualified = {rid:{s['epoch_zero_based']:s for s in rows if s['peak_snr'] >= 5.5}
                     for rid,rows in selected.items()}
        for rid in ids:
            component = orig[rid]['receiver_alias_evidence']['alias_identity_component_sha256']
            observed = alias[rid]['receiver_alias_evidence']; count = 0
            assert observed['alias_identity_component_sha256'] == component
            for wid in ids:
                if orig[wid]['receiver_alias_evidence']['alias_identity_component_sha256'] == component: continue
                matches = sum(abs(qualified[rid][e]['peak_frequency_mhz']-qualified[wid][e]['peak_frequency_mhz'])*1e6 <= 20.
                    for e in qualified[rid].keys() & qualified[wid].keys())
                count += matches >= 2; totals['exhaustive_cross_identity_pairs'] += 1
            assert observed['matched_cross_component_record_count'] == count
            assert observed['matched'] == bool(count)
            previous = orig[rid]['member_disposition']
            if previous == 'rfi_veto_receiver_frame_alias': previous = 'pending_receiver_alias_evaluation'
            disposition = 'rfi_veto_receiver_frame_alias' if previous == 'pending_receiver_alias_evaluation' and count else previous
            assert alias[rid]['member_disposition'] == disposition
        geo = {e['record_id']:e for e in rec['geometry_confirmation_evidence']}
        old = {e['record_id']:e for e in rec['old_confirmation_evidence']}
        assert set(geo) == set(old) == set(ids)
        for m in members:
            rid = m['record_id']; ev = geo[rid]; t = m['template_index']; q = m['proxy_carrier_index']; w = m['spectral_width_channels']
            assert ev['off_window'] == old[rid]['off_window'] and ev['remaining'] == old[rid]['remaining']
            assert [r['epoch'] for r in ev['aligned']] == m['active_epochs_zero_based']
            for i,row in enumerate(ev['aligned']):
                e = row['epoch']; assert row['off_maximum'] == old[rid]['off_window']['maxima'][i]
                should_query = (alias[rid]['member_disposition'] == 'pending_receiver_alias_evaluation'
                    and m['meets_diagnostic_rank_cut'] and ev['remaining']['remaining_passed'] and row['off_maximum'] >= 5.5)
                assert row['queried'] == should_query
                if not row['queried']: assert row['complete'] and not row['vetoed']; continue
                p = row['profile']; assert row['complete'] == p['complete']
                if not p['complete']:
                    assert not row['vetoed']; totals['incomplete_profiles'] += 1; continue
                assert p['radius_proxy_bins'] == w and p['correlation_floor'] == .8
                first = grid.score_slice.start+q-w; stop = first+2*w+1
                assert (p['first_support_index'],p['stop_support_index']) == (first,stop)
                pos = np.asarray([_predicted_midpoint_hz(float(f),on[e][t]) for f in grid.support_hz[first:stop]])
                pos = (pos/_predicted_midpoint_hz(1.,off[e][t])-grid.support_hz[0])/grid.channel_width_hz
                assert pos.tolist() == p['off_positions']
                left = np.floor(pos).astype(int); right = np.minimum(left+1,grid.support_bin_count-1)
                weights = pos-left
                assert left.tolist() == p['off_left_indices'] and right.tolist() == p['off_right_indices']
                assert weights.tolist() == p['interpolation_weights']
                a = np.array(p['on_values']); b = (1-weights)*p['off_left_values']+weights*p['off_right_values']
                assert b.tolist() == p['aligned_off_values'] and a[w] == m['epoch_values_at_proxy_carrier'][e]
                a -= a.mean(); b -= b.mean(); denom = float(np.linalg.norm(a)*np.linalg.norm(b))
                corr = None if denom == 0 else float(np.dot(a,b)/denom)
                assert corr == p['correlation']
                assert row['vetoed'] == (corr is not None and corr >= .8 and row['off_maximum'] >= 5.5)
                totals['reconstructed_profiles'] += 1
            assert ev['aligned_complete'] == all(r['complete'] for r in ev['aligned'])
            assert ev['aligned_vetoed'] == any(r['vetoed'] for r in ev['aligned'])
        assert rec['additional_evidence_complete'] == all(e['aligned_complete'] for e in geo.values())
        assert set(rec['policy_decisions']) == set(cfg['policies'])
        for policy,ds in rec['policy_decisions'].items():
            assert [d['record_id'] for d in ds] == ids
            a = copy.deepcopy(audit)
            for m,d in zip(a['members'],ds):
                if policy in POLICIES:
                    ev = geo[m['record_id']]; reasons = []
                    if policy != POLICIES[0] and not ev['remaining']['remaining_passed']: reasons.append('remaining_aggregate_below_5p5')
                    if policy == POLICIES[1] and ev['off_window']['vetoed']: reasons.append('width_aware_OFF')
                    if policy == POLICIES[2]:
                        if ev['aligned_vetoed']: reasons.append('receiver_aligned_ON_OFF_agreement')
                        if not ev['aligned_complete']: reasons.append('incomplete_aligned_OFF_evidence')
                    prior = alias[m['record_id']]['member_disposition']
                    passed = prior == 'pending_receiver_alias_evaluation' and not reasons
                    disposition = 'm43ad_rejected_'+'_and_'.join(reasons) if prior == 'pending_receiver_alias_evaluation' and reasons else prior
                    assert d['rejections'] == reasons and d['passes_evaluated_physical_vetoes'] == passed
                    assert d['physical_disposition'] == disposition
                m.update({k:d[k] for k in ('passes_evaluated_physical_vetoes','physical_disposition')})
            total = sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
            assert total == rec['final_counts'][policy]; a['final_diagnostic_survivors'] = total
            if name != 'baseline':
                row = next(r for r in rec['endpoints'] if r['policy'] == policy)
                association = endpoint(a,case['reference_truth'],grid,factors,basis,case['strength'],path.name)
                assert row['truth_association'] == association and row['recovered'] == association['recovered']
                assert row['final_members'] == total
                assert row['additional_evidence_complete'] == (rec['additional_evidence_complete'] if policy == POLICIES[-1] else True)
                endpoints.append(row)
        if case['panel'] in ('historical','baseline'):
            h = read_input(ROOT/cfg['historical_sources'][case['source_name']]['file'])
            assert audit == h['reference_audit']
            assert all(rec['policy_decisions'][p] == ds for p,ds in h['policy_decisions'].items())
            assert rec['original_signatures'] == h['original_signatures'] and rec['centered_signatures'] == h['centered_signatures']
            totals['exact_historical_inputs_including_baseline'] += 1
        checks = rec['direct_checks']+rec['profile_direct_checks']
        assert all(c['exact'] for c in checks)
        totals.update(inputs=1,members=len(ids),policy_decisions=len(ids)*len(cfg['policies']),direct_native_checks=len(checks))
    key = lambda r:(r['name'],r['policy'])
    assert sorted(endpoints,key=key) == sorted(result['endpoints'],key=key)
    assert len(endpoints) == 1490 and totals['direct_native_checks'] == result['direct_native_checks']
    assert len(payloads) == result['distinct_native_payloads']
    assert totals['exact_historical_inputs_including_baseline'] == 38
    assert by_case['baseline']['final_counts'] == result['baseline_counts']
    assert by_case['baseline']['additional_evidence_complete'] == result['baseline_additional_evidence_complete']
    assert costs(endpoints,result['baseline_counts'],result['baseline_additional_evidence_complete']) == result['comparisons']
    for summary in result['summary']:
        rows = [r for r in endpoints if (r['panel'],r['policy']) == (summary['panel'],summary['policy'])]
        signals = [r for r in rows if r['signal_present']]; controls = [r for r in rows if not r['signal_present']]
        assert summary['signal_inputs'] == len(signals) and summary['control_inputs'] == len(controls)
        assert summary['recovered_signals'] == sum(r['recovered'] for r in signals)
        assert summary['leaking_controls'] == sum(r['final_members']>0 for r in controls)
        assert summary['false_control_associations'] == sum(r['recovered'] for r in controls)
    pairs = []
    for c in cfg['cases']:
        if c['panel'] != 'fresh' or c['case_type'] not in ('mixed-unequal','distributed17-moderate-OFF'): continue
        kind = 'combined-unequal' if c['case_type'] == 'mixed-unequal' else 'distributed17'
        other = next(x for x in cfg['cases'] if x['panel'] == 'fresh' and x['case_type'] == kind
            and (x['score_index'],x['local_template'],x['active_epochs']) == (c['score_index'],c['local_template'],c['active_epochs']))
        for p in cfg['policies']:
            a = next(r for r in by_case[other['name']]['endpoints'] if r['policy'] == p)
            b = next(r for r in by_case[c['name']]['endpoints'] if r['policy'] == p)
            pairs.append(dict(signal_only=other['name'],mixed=c['name'],policy=p,
                signal_only_recovered=a['recovered'],mixed_recovered=b['recovered'],paired_loss=a['recovered'] and not b['recovered']))
    write_sealed(OUT/'paired_signal_costs.json',dict(comparisons=pairs))
    write_sealed(OUT/'audit.json',dict(passed=True,freeze_commit=result['freeze_commit'],
        pinned_files=len(cfg['pinned_sha256']),totals=dict(totals),receiver_selections=dict(selections),
        distinct_native_payloads=len(payloads),all_96_arrays_exact=True,all_48_native_gathers_exact=True,
        endpoints_including_baseline=1500,new_rule_adopted=False,new_null_rows=0))
    print(json.dumps(dict(passed=True,totals=dict(totals),receiver_selections=dict(selections))))


if __name__ == '__main__': run()
