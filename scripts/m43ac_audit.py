"""Verify M43AC accounting and published-vector relationships independently."""
import json
from collections import Counter
import numpy as np
from m43ac_dual_evidence import ROOT, OUT, NEW, source_records, sha
from m43e_economical_bank import read_sealed, write_sealed


def run():
    summary = read_sealed(OUT / 'ledger_summary.json')
    responses = read_sealed(OUT / 'response_summary.json')
    totals = Counter(); focal_members = 0; vectors = 0; native = 0
    sources = {}; cause_counts = Counter()
    for item, rec in source_records():
        name = rec['case']['name']; sources[name] = rec
        assert item == next(s for s in summary['sources'] if s['name'] == name)
        rank = {m['record_id'] for m in rec['reference_audit']['members'] if m['meets_diagnostic_rank_cut']}
        old = {m['record_id'] for m in rec['original_alias']['records']
               if m['member_disposition'] == 'rfi_veto_receiver_frame_alias'} & rank
        centered = {m['record_id'] for m in rec['centered_alias']['records']
                    if m['member_disposition'] == 'pending_receiver_alias_evaluation'} & rank
        released = old & centered
        final = {m['record_id'] for m in rec['policy_decisions'][NEW]
                 if m['passes_evaluated_physical_vetoes']} & rank & released
        row = next(r for r in summary['inputs'] if r['name'] == name)
        assert (row['old_alias'], row['released'], row['released_final']) == (len(old), len(released), len(final))
        cause_counts.update(row['witness_causes'])
        totals.update(inputs=1, members=len(rec['reference_audit']['members']),
                      old_alias=len(old), released=len(released), released_final=len(final))
        for p, count in row['final_counts'].items():
            assert count == sum(m['passes_evaluated_physical_vetoes'] and m['record_id'] in rank
                                for m in rec['policy_decisions'][p])
        focal = OUT / 'focal' / f'{name}.json'
        if focal.exists():
            f = read_sealed(focal); assert f['source'] == item
            originals = {m['record_id']: m for m in rec['reference_audit']['members']}
            for path in f['member_files']:
                for m in read_sealed(ROOT / path)['members']:
                    focal_members += 1; rid = m['member']['record_id']
                    assert m['member'] == originals[rid]
                    assert [e['original'] for e in m['geometry']] == rec['original_signatures'][rid]
                    assert [e['centered'] for e in m['geometry']] == rec['centered_signatures'][rid]
                    for policy, d in m['decisions'].items():
                        assert d == next(d for d in rec['policy_decisions'][policy] if d['record_id'] == rid)
                    trace = m['old_best_witness']
                    if trace:
                        matched = 0; qualified = 0
                        for e in trace['epochs']:
                            a, b = e['centered_left'], e['centered_right']
                            q = min(a['peak_snr'], b['peak_snr']) >= 5.5
                            passed = q and abs(a['peak_frequency_mhz']-b['peak_frequency_mhz'])*1e6 <= 20.
                            assert e['both_centered_above_floor'] == q and e['centered_pair_matches'] == passed
                            qualified += q; matched += passed
                        cause = ('fewer_than_two_shared_centered_epochs_above_floor' if qualified < 2 else
                                 'centered_peak_separation' if matched < 2 else 'old_witness_still_matches')
                        assert trace['cause'] == cause
    assert dict(totals) == summary['totals'] and dict(cause_counts) == summary['old_best_witness_causes']
    assert totals['inputs'] == 149 and totals['members'] == 13632
    for p in responses['profiles']:
        for file in p['response_files']:
            path = ROOT / file['file']; assert sha(path) == file['sha256']
            d = read_sealed(path)
            for kind in ('on', 'off'):
                a = np.asarray(d[kind]['values']); b = np.asarray(d[kind]['baseline_values'])
                assert a.shape == b.shape == (3, 321)
                assert np.isfinite(a).all() and np.isfinite(b).all(); vectors += 6
                for e, check in enumerate(d[kind]['direct_native']):
                    assert check['score'] == a[e, 160]; native += 1
                    assert len(check['filtered_row_values']) == len(check['native_center_indices']) == 16
                if d['width'] == p['width']:
                    for e, row in enumerate(p['epochs']):
                        assert row[kind+'_center'] == a[e, 160]
                        assert row['baseline_'+kind+'_center'] == b[e, 160]
                        assert row[kind+'_increment_center'] == a[e, 160]-b[e, 160]
                        assert row['full_'+kind+'_response_equals_baseline'] == bool(np.array_equal(a[e], b[e]))
    assert native == responses['direct_native_comparisons'] == 144 and vectors == 288
    write_sealed(OUT / 'audit.json', dict(passed=True, source_inputs=149, reference_members=13632,
        focal_members=focal_members, response_vectors=vectors, vector_samples=321,
        direct_native_checks=native, totals=dict(totals), old_best_witness_causes=dict(cause_counts),
        original_and_centered_signature_epochs_exact=responses['original_and_centered_signature_epochs_exact'],
        new_rule_adopted=False, new_detector_executions=0))
    print(json.dumps(dict(passed=True, focal_members=focal_members, vectors=vectors, native=native)))


if __name__ == '__main__':
    run()
