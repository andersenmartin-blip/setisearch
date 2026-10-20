"""Final period metadata reconciliation; never imports a detector or opens arrays."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo


def main():
    root = Path(sys.argv[1]).resolve()
    out = root / 'results/radio_final_checkpoint_20261020'
    scope = json.loads((out / 'CHECKPOINT_SCOPE.json').read_text())
    now = datetime.now(ZoneInfo('Europe/Copenhagen'))
    if now.date().isoformat() != scope['actual_date'] or scope['actual_date'] != '2026-10-20':
        raise RuntimeError('The protected final checkpoint is date-bound to 20 October')
    checks = []

    def require(label, condition):
        checks.append({'check': label, 'passed': bool(condition)})
        if not condition:
            raise ValueError(label)

    sources = {}
    index = []
    for e in scope['sources']:
        path = root / 'source_snapshot' / e['path']
        b = path.read_bytes()
        git_sha = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
        require('Immutable source identity: ' + e['path'], git_sha == e['git_blob_sha'])
        sources[e['path']] = b.decode('utf-8')
        index.append({'path': e['path'], 'bytes': len(b), 'git_blob_sha': git_sha,
                      'sha256': hashlib.sha256(b).hexdigest(),
                      'source_commit': scope['source_snapshot_commit']})

    def doc(path):
        return json.loads(sources[path])

    legacy = doc('results/radio_quicklook_20261009/RESOURCE_LEDGER.json')
    cohort = doc('analysis/real_fullscan_cohort_20261016/report/AGGREGATE.json')
    supplement = doc('tools/saved_payload_restore_20261016/report/AGGREGATE_FAILURE_SUPPLEMENT.json')
    delivery = doc('tools/saved_payload_restore_20261016/report/DELIVERY_RESULT.json')
    reproduction = doc('pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json')
    reserve = scope['reservation']['checkpoint_reservation_CPU_s']
    require('Legacy checkpoint reserve is exactly 2000 CPU-s',
            legacy['protected_final_checkpoint_CPU_s'] == reserve == 2000)
    require('All original exploratory reservations retained',
            legacy['reservation_components_sum_CPU_s'] == sum(legacy['reservation_components_CPU_s'].values()) == 3910)
    free = Decimal(str(legacy['remaining_unprotected_CPU_s']))
    arithmetic_free = Decimal(str(legacy['remaining_CPU_after_reservation_s'])) - Decimal(reserve)
    require('No source-budget overdraw or roundoff credit',
            arithmetic_free >= free and arithmetic_free - free < Decimal('0.000000000001'))
    require('Eight verified bands and failed B06 remain separated',
            cohort['combined_bands_planned'] == 9 and cohort['combined_bands_verified'] == 8
            and supplement['fully_verified_bands_including_B00'] == 8
            and supplement['B06_separate_saved_QA_passed'] is False
            and supplement['status'] == 'STOPPED_RETAINED_NO_RETRY')
    require('No original cohort failure reclassified',
            cohort['cohort_status'] == supplement['original_cohort_status'] == 'INCOMPLETE_COHORT_RETAINED_NO_RETRY'
            and supplement['original_failed_endpoints_modified'] is False
            and supplement['tolerance_retuned'] is False)
    require('Verified-only totals unchanged', cohort['verified_totals'] == supplement['verified_only_totals'])
    require('Verified retained ON and exhaustive OFF counts are zero',
            cohort['verified_totals']['retained_top5_ON_ge10_count'] == 0
            and cohort['verified_totals']['OFF_ge8_inventory_rows'] == 0)
    require('Verified map and QA-check census is consistent',
            cohort['verified_scan_maps'] == supplement['fully_verified_scan_maps'] == 8 * 6
            and cohort['verified_QA_checks'] == 8 * 847488)
    require('B06 strict zero-tolerance discrepancy retained',
            supplement['B06_required_global_max_tolerance'] == 0
            and supplement['B06_global_max_difference_ULP'] == 1
            and supplement['B06_global_max_absolute_difference'] > 0
            and supplement['B06_exact_byte_restoration_passed'] is True)
    require('B06 restoration involved no new primary search', supplement['new_primary_detector_invocations'] == 0)
    require('Later measured child CPU totals include failure costs once',
            abs(cohort['combined_known_whole_children_CPU_s_including_failed_attempts']
                + supplement['new_scope_measured_whole_children_CPU_s']
                - supplement['three_current_scope_measured_whole_children_CPU_s']) < 1e-9
            and cohort['failed_case_costs_in_cohort_whole_CPU_total'] is True)
    require('Later reservations are separate and retained, not reclaimed',
            supplement['three_current_scope_reserved_CPU_s'] == 1300 + 10500 + 760
            and delivery['retained_CPU_reservation_s'] == 100)
    require('Archive receipt reports bytes only, not a scientific PASS',
            delivery['status'] == 'PASS_ARTIFACT_BYTES_AND_DELIVERY_PROCESS_ONLY'
            and delivery['archive']['members_verified'] == 359
            and delivery['fully_QA_verified_bands'] == 8
            and delivery['scientific_bank_admission'] is False)
    require('Existing bounded reproduction is not a rerun or qualification',
            reproduction['status'] == 'PASS_BOUNDED_SAVED_RESULT_VERIFICATION'
            and reproduction['complete_maps_verified'] == 6
            and reproduction['artifact_hashes_verified'] == 20
            and reproduction['OFF_comparisons_verified'] == 96
            and reproduction['qualification'] is False
            and reproduction['generation_search_or_redraw'] is False)
    band_text = sources['RADIO_NINE_BAND_STATUS_2026-10-16.md']
    rows = []
    for line in band_text.splitlines():
        if re.match(r'^\| B\d\d \|', line):
            fields = [s.strip() for s in line.strip('|').split('|')]
            rows.append({'band': fields[0], 'native_q': fields[1], 'QA': fields[2],
                         'producer_ON_max_descriptive': float(fields[3].replace(',', '.'))})
    verified_rows = [r for r in rows if r['QA'] == 'PASS']
    require('Published nine-band table has exactly eight PASS and one B06 failure',
            len(rows) == 9 and len(verified_rows) == 8
            and [r['band'] for r in rows if r['QA'] != 'PASS'] == ['B06'])
    maximum = max(r['producer_ON_max_descriptive'] for r in verified_rows)
    require('Published verified maximum excludes B06', maximum == 7.031163159)
    require('Original A/B and unresolved 2016 dispositions retained',
            'FAIL_CLOSED' in sources['RADIO_VALIDATION_A_2026-10-08_RESULT.md']
            and 'FAIL_CLOSED' in sources['RADIO_VALIDATION_B_2026-10-08_RESULT.md']
            and 'syv' in sources['RADIO_ON_OFF_EXCESS_2026-10-09_RESULT.md']
            and 'uafklarede' in sources['RADIO_ON_OFF_EXCESS_2026-10-09_RESULT.md'])

    result = {
        'schema': 'SETI_FINAL_METADATA_CHECKPOINT_20261020_RESULT_V1',
        'status': 'COMPLETE_FINAL_METADATA_CHECKPOINT_ONLY',
        'completed_at_Copenhagen': now.isoformat(), 'source_snapshot_commit': scope['source_snapshot_commit'],
        'period': scope['period'], 'metadata_consistency_checks': checks,
        'source_files': index, 'new_signal_results': 0, 'detector_or_scientific_QA_jobs_rerun': 0,
        'raw_or_payload_arrays_opened': 0, 'archives_downloaded_or_rechecked': 0,
        'telescope_requests_or_bytes': 0, 'new_draws_or_holdouts': 0, 'cost_DKK': 0,
        'original_A_B': 'FAIL_CLOSED', 'qualified_pilot_admitted': False,
        'qualified_SETI_detection': False, 'seven_2016_ON_excesses': 'UNRESOLVED',
        '2017_bands': rows, '2017_fully_verified_bands': 8,
        '2017_verified_reference_channels': 8 * 4096,
        '2017_verified_reference_binwidth_sum_kHz': 91.552734375,
        '2017_contiguous_bandwidth_claim': False,
        '2017_verified_maximum_from_published_rounded_table': maximum,
        'B06_excluded_from_verified_totals': True,
        'reproduction_evidence': 'Existing bounded receipt; not repeated at this checkpoint. No claim of a separate 19 October execution.',
        'scientific_interpretation': 'Postselected historical visit analyses, not calibrated SNR/FAP, physical sensitivity, an independent confirmation or a qualified sky null.',
        'period_closed_not_extended': True,
        'other_separately_authorized_periods_not_closed_or_activated': True,
        'project_wide_total_CPU_measurement': 'UNKNOWN_NOT_RECONSTRUCTED_FROM_PARTIAL_OR_OVERLAPPING_COMPONENTS'
    }
    ledger = {
        'schema': 'SETI_FINAL_CHECKPOINT_CLOSURE_LEDGER_20261020_V1',
        'status': 'LEGACY_PERIOD_CHECKPOINT_RESERVATION_CONSUMED_AND_CLOSED',
        'previous_ledger': 'results/radio_quicklook_20261009/RESOURCE_LEDGER.json',
        'source_snapshot_commit': scope['source_snapshot_commit'],
        'previous_remaining_CPU_s': legacy['remaining_CPU_after_reservation_s'],
        'previous_protected_final_checkpoint_CPU_s': 2000,
        'checkpoint_reservation_CPU_s_debited_once': 2000,
        'old_exploratory_reservation_components_sum_CPU_s': 3910,
        'these_legacy_reservations_plus_checkpoint_CPU_s': 5910,
        'remaining_unallocated_legacy_CPU_s': float(free),
        'remaining_legacy_balance_not_activated_or_transferred': True,
        'all_2000_checkpoint_CPU_s_retained_not_actual_measured_usage': True,
        'checkpoint_whole_process_meter': 'PROCESS_RECEIPT.json; measured component only',
        'unmeasured_preparation_delivery_review_reserved_CPU_s': 1940,
        'original_ledgers_modified': False, 'refund_CPU_s': 0, 'other_scope_capacity_reused_CPU_s': 0,
        'separately_scoped_2017_reserved_CPU_s_retained': 12560,
        'separate_2017_delivery_reserved_CPU_s_retained': 100,
        'separately_scoped_2017_measured_children_CPU_s_including_failures': 2581.938327,
        'separate_delivery_measured_child_CPU_s': 3.314751,
        'not_a_project_wide_accounting_sum': True,
        'all_project_CPU_caps_reconciled_or_compliance_certified': False,
        'project_wide_total_CPU_measurement': None,
        'historically_unknown_or_unreconciled_charges_not_refunded': True,
        'cost_DKK': 0, 'new_telescope_bytes': 0,
        'continued_spending_or_new_study_authorized_by_this_closure': False
    }
    for name, value in [('CHECKPOINT_RESULT.json', result), ('RESOURCE_LEDGER.json', ledger)]:
        with (out / name).open('x') as f:
            json.dump(value, f, indent=2, ensure_ascii=False); f.write('\n')
    print(json.dumps({'status': result['status'], 'metadata_checks': len(checks),
                      'source_files': len(index), 'science_qualification': False}))


if __name__ == '__main__':
    main()
