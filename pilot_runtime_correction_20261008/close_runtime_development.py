"""Close retained development-only correction evidence; no RNG or searches."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'pilot_runtime_correction_20261008'
BASE = ROOT / 'results/radio_pilot_dev_runtime_20261008'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def write(p, x):
    p.write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')

def main():
    completion = read(BASE / 'completion.json')
    cases = read(DEST / 'development_runtime_cases.json')
    a_summary_path = ROOT / 'pilot_protocol_20261008/validation_a_complete_summary.json'
    a_outcomes_path = ROOT / 'pilot_protocol_20261008/validation_a_complete_outcomes.json'
    if read(a_summary_path)['scientific_gate'] != 'FAIL_CLOSED':
        raise ValueError('Original A failure must remain closed')
    if not completion['all_returncodes_zero'] or len(completion['results']) != 2:
        raise ValueError('Two original once-only successful reaped DEV children required')
    outcomes, records, receipts = [], [], []
    for i, case in enumerate(cases):
        output = BASE / f'case_{i:03d}'
        outcome, marker, manifest, receipt = [read(output / n) for n in (
            'outcome.json', 'COMMITTED.json', 'artifact_manifest.json', 'resource_receipt.json')]
        if (outcome['case_id'] != case['case_id'] or outcome['panel'] != 'DEV_RUNTIME'
                or not outcome['data_integrity_ok'] or outcome['failure'] is not None
                or marker['status'] != 'COMPLETED_CASE_ONLY' or not marker['caps_passed']
                or marker['case_id'] != case['case_id'] or not receipt['caps_passed']
                or marker['artifact_manifest_SHA256'] != digest(output / 'artifact_manifest.json')):
            raise ValueError('No complete durable runtime proof')
        for name, value in manifest.items():
            if digest(output / name) != value['SHA256']:
                raise ValueError('Committed development artifact changed')
        for j in range(6):
            if f'scan_{j:02d}_full_map.npz' not in manifest:
                raise ValueError('Complete original six maps required')
        records.append({**marker, 'output_directory': str(output)})
        outcomes.append(outcome)
        receipts.append(receipt)
    scientific_paths = {'detector': 'pilot_engine_20261008/detector.py',
                        'dev_helpers': 'pilot_engine_20261008/run_dev.py',
                        'generator': 'pilot_controls_20261008/generator.py',
                        'contract': 'pilot_controls_20261008/control_contract.json',
                        'summarizer': 'pilot_controls_20261008/summarize.py'}
    science = {k: digest(ROOT / p) for k, p in scientific_paths.items()}
    admission = read(DEST / 'dev_runtime_admission.json')
    if any(science[k] != admission['sha256'][k] for k in science):
        raise ValueError('Science changed during development')
    charge = max(sum(float(r['cpu_s']) for r in receipts), float(completion['children_CPU_s'])) + float(completion['controller_CPU_s'])
    proof = {'status': 'PASS_OPERATIONAL_DEVELOPMENT_ONLY', 'panel': 'DEV_RUNTIME',
             'case_count_expected': 2, 'case_count_observed': 2, 'complete': True,
             'scientific_files_unchanged': True, 'correction_number': 1,
             'case_ids': [c['case_id'] for c in cases], 'case_bank_sha256': digest(DEST / 'development_runtime_cases.json'),
             'failed_validation_a_summary_sha256': digest(a_summary_path),
             'failed_validation_a_outcomes_sha256': digest(a_outcomes_path),
             'scientific_sha256': science, 'case_results': records,
             'CPU_s_charged_whole_children_plus_controller': charge,
             'fresh_B_generated': False, 'telescope_values_opened': False,
             'independent_scientific_validation_claimed': False,
             'DEV_freeze_commit': admission['public_commit_sha']}
    resource = {'status': 'CLOSED_TWO_DEV_RUNTIME_PROOFS', 'caps_passed': True,
                'CPU_s_charged': charge, 'whole_children_CPU_s': completion['children_CPU_s'],
                'controller_CPU_s': completion['controller_CPU_s'],
                'receipt_CPU_sum_s': sum(float(r['cpu_s']) for r in receipts),
                'reserved_CPU_s': 3600, 'unused_reservation_refunded_CPU_s': 3600 - charge,
                'wall_s': completion['wall_s'],
                'largest_peak_RSS_bytes': max(r['peak_rss_bytes'] for r in receipts),
                'accounting': 'max(sum child receipts, whole reaped child CPU) + controller CPU'}
    a_ledger = read(ROOT / 'pilot_protocol_20261008/validation_a_complete_resource_receipt.json')
    archive_cpu = 3.942393
    remaining = a_ledger['CPU_remaining_after_A_s'] - charge - archive_cpu - 1200
    ledger = {'status': 'CLOSED_DEVELOPMENT_CORRECTION_FRESH_B_PROSPECTIVE',
              'correction_number': 1, 'scientific_files_unchanged': True,
              'A_remains_FAIL_CLOSED': True, 'A_charged_CPU_s': a_ledger['charged_CPU_s'],
              'remaining_CPU_after_A_s': a_ledger['CPU_remaining_after_A_s'],
              'DEV_runtime_charged_CPU_s': charge, 'A_archival_packaging_measured_CPU_s': archive_cpu,
              'unmeasured_preparation_CPU_planning_reservation_s': 1200,
              'remaining_CPU_after_all_those_charges_and_reservations_s': remaining,
              'B_aggregate_CPU_allocation_s': 19500,
              'remaining_after_full_B_allocation_s': remaining - 19500,
              'prospective_reader_and_pilot_CPU_partitions_s': [1800, 1800],
              'global_CPU_cap_s': 43200, 'job_wall_cap_s': 1800, 'job_RSS_cap_bytes': 4294967296,
              'source_aggregate_cap_bytes': 4563402752, 'source_pilot_cap_bytes': 2147483648,
              'local_artifact_cap_bytes': 8589934592, 'additional_correction_allowed': False,
              'fresh_B_generated': False, 'telescope_values_opened': False,
              'missing_historical_measurements_claimed_complete': False}
    if remaining - 19500 < 3600:
        raise ValueError('B allocation must preserve both future complete job partitions')
    write(DEST / 'runtime_development_proof.json', proof)
    write(DEST / 'development_runtime_complete_outcomes.json', outcomes)
    write(DEST / 'development_runtime_resource_receipt.json', resource)
    write(DEST / 'post_development_ledger.json', ledger)
    print(json.dumps({'status': proof['status'], 'CPU_charged_s': charge,
                      'remaining_after_planning_reservations_s': remaining,
                      'B_allocation_CPU_s': 19500, 'reserved_future_capacity_s': remaining - 19500}))

if __name__ == '__main__':
    main()
