#!/usr/bin/env python3
"""Reconcile closed B; write a new exploratory ledger without resetting costs."""
import hashlib
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    b = BASE / 'results/radio_pilot_val_b_20261008'
    prereq = BASE / 'pilot_runtime_correction_20261008/post_development_ledger.json'
    b_admission_path = BASE / 'pilot_runtime_correction_20261008/validation_b_admission.json'
    b_admission = json.loads(b_admission_path.read_text())
    old = json.loads(prereq.read_text())
    outcomes = json.loads((b / 'outcomes.json').read_text())
    summary = json.loads((b / 'summary.json').read_text())
    receipt = json.loads((b / 'resource_receipt.json').read_text())
    marker = json.loads((b / 'COMMITTED_PANEL.json').read_text())
    rolling = json.loads((b / 'rolling_cpu_ledger.json').read_text())
    assert marker['status'] == 'CLOSED_FAIL' and marker['panel'] == 'VAL_B'
    assert marker['case_count_observed'] == marker['case_count_expected'] == len(outcomes) == 142
    assert summary['scientific_gate'] == 'FAIL_CLOSED'
    assert marker['all_children_reaped'] and receipt['all_children_reaped']
    assert marker['no_retry_or_redraw'] and receipt['cpu_budget_passed']
    assert rolling['status'] == 'CLOSED_NO_RETRY' and not rolling['live_case_ids']
    for name in ('outcomes', 'summary', 'resource_receipt'):
        assert marker[name + '_SHA256'] == digest(b / (name + '.json'))
    children = max(float(receipt['conservative_children_cpu_s_charged']),
                   float(receipt['children_cpu_s_reaped']),
                   float(rolling['cpu_charged_closed_children']),
                   sum(float(x['cpu_charged_seconds']) for x in receipt['closures']))
    controller = max(float(receipt['controller_cpu_s']),
                     float(rolling['controller_cpu_s_observed']))
    charged = children + controller
    before_b = float(b_admission['budget']['remaining_cpu_seconds'])
    assert before_b == float(old['remaining_CPU_after_all_those_charges_and_reservations_s'])
    remaining = before_b - charged
    assert charged <= receipt['aggregate_cpu_allocation_seconds']
    assert remaining >= 6000 + 2000
    ledger = {
        'status': 'CLOSED_B_FAIL_EXPLORATORY_METHOD_STUDY_PROSPECTIVE',
        'global_CPU_cap_s': 43200,
        'remaining_CPU_before_B_s': before_b,
        'validation_B_original_admission_SHA256': digest(b_admission_path),
        'B_children_CPU_charged_s': children,
        'B_controller_CPU_charged_s': controller,
        'B_whole_closed_panel_CPU_charged_s': charged,
        'remaining_CPU_after_closed_B_s': remaining,
        'method_aggregate_CPU_allocation_s': 6000,
        'retained_report_reproduction_CPU_s': 2000,
        'remaining_after_full_method_allocation_s': remaining - 6000,
        'A_remains_FAIL_CLOSED': True,
        'B_remains_FAIL_CLOSED': True,
        'scientific_files_unchanged': True,
        'telescope_values_opened': False,
        'pilot_admitted': False,
        'additional_correction_allowed': False,
        'unmeasured_preparation_CPU_planning_reservation_s': old['unmeasured_preparation_CPU_planning_reservation_s'],
        'archival_and_review_CPU_accounting': 'Measured archival/review costs remain components of the existing 1200-second preparation planning reservation; no reserve is refunded or represented as measured historical work.',
        'controller_after_final_snapshot_accounting': 'Small final marker/print and parent reconciliation work remain inside the existing preparation reservation.',
        'missing_historical_measurements_claimed_complete': False,
        'post_development_ledger_sha256': digest(prereq),
        'b_prerequisite_sha256': {key: digest(b / name) for key, name in (
            ('b_outcomes', 'outcomes.json'), ('b_summary', 'summary.json'),
            ('b_resource_receipt', 'resource_receipt.json'), ('b_completion', 'COMMITTED_PANEL.json'))},
        'prerequisite_SHA256': {'post_development_ledger': digest(prereq), **{
            name: digest(b / (name + '.json')) for name in
            ('outcomes', 'summary', 'resource_receipt', 'rolling_cpu_ledger', 'COMMITTED_PANEL')}},
    }
    target = pathlib.Path(__file__).with_name('post_b_ledger.json')
    with target.open('x') as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(json.dumps({'B_charged_CPU_s': charged, 'remaining_CPU_s': remaining,
                      'method_allocation_CPU_s': 6000, 'ledger_SHA256': digest(target)}))

if __name__ == '__main__':
    main()
