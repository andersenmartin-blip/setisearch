"""Prospective scope generation from complete index metadata only; no arrays."""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESULT = ROOT / 'results/radio_rolling_bands_20261010'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    totals = {q: json.loads((OUT / f'source_manifest_chunk{q}.json').read_text())['total_future_spectral_payload_bytes']
              for q in [155, 157, 158]}
    if totals != {155: 305145065, 157: 302944974, 158: 299457438}:
        raise ValueError('Exact offline metadata totals changed')
    metadata = json.loads((RESULT / 'metadata_nodes/RECEIPT.json').read_text())
    if metadata['status'] != 'PASS_EXACT_SIX_METADATA_NODES_NO_SPECTRUM' or metadata['metadata_BODY_bytes_received'] != 18816:
        raise ValueError('Six-node metadata recovery must have passed')
    base, pair, triple = 1221712926 + 18816, totals[155] + totals[157], sum(totals.values())
    envelope = 3200468146 + 18816
    ledger = {
        'schema': 'SETI_ROLLING_EXACT_CAPACITY_LEDGER_V1',
        'status': 'EXACT_METADATA_COMPLETE_PROSPECTIVE_SIGNAL_VALUES_UNOPENED',
        'signal_native_chunks_selected': [155, 157],
        'chunk158_role': 'Exact metadata capacity forecast only; no signal values opened or authorized by this ledger',
        'protected_native_chunks_skipped': [156, 159],
        'exact_spectral_BODY_bytes': {str(k): v for k, v in totals.items()},
        'shared_six_metadata_node_BODY_bytes': 18816, 'shared_metadata_BODY_counted_once': True,
        'metadata_RECEIPT_sha256': digest(RESULT / 'metadata_nodes/RECEIPT.json'),
        'same_cadence_before155157_actualBODY_bytes': base,
        'same_cadence_before155157_charged_upper_bound_bytes': base + 192,
        'same_cadence_after155157_exactBODY_bytes': base + pair,
        'same_cadence_after155157_charged_upper_bound_bytes': base + pair + 384,
        'same_cadence_remaining_after155157_actualBODY_bytes': 2147483648 - base - pair,
        'same_cadence_after155157158_exactBODY_bytes': base + triple,
        'same_cadence_after155157158_charged_upper_bound_bytes': base + triple + 480,
        'same_cadence_remaining_after155157158_actualBODY_bytes': 2147483648 - base - triple,
        'same_cadence_BODY_cap_bytes': 2147483648,
        'all_source_conservative_base_after153154_plus_six_nodes_bytes': envelope,
        'all_source_after155157_exactBODY_bytes': envelope + pair,
        'all_source_after155157158_exactBODY_bytes': envelope + triple,
        'all_source_after155157158_charged_guard_reservation_bytes': envelope + triple + 480,
        'all_source_remaining_after155157158_exactBODY_bytes': 4563402752 - envelope - triple,
        'all_source_BODY_cap_bytes': 4563402752,
        'all_source_metadata_charge_note': 'Six-node18816 is added conservatively to previous3200468146 envelope; if already covered by existing8MiB metadata reservation, this is an explicit duplicate safety allowance, not two transfers.',
        'new155157_telescope_BODY_reservation_max_bytes': 734003200,
        'all_source_envelope_with155157_max_reservation_bytes': envelope + 734003200,
        'per_acquisition_BODY_cap_bytes': 367001600,
        'CPU_cap_s_per_acquisition': 60, 'wall_cap_s_per_acquisition': 1200,
        'RAM_cap_bytes_per_acquisition': 4294967296, 'workspace_cap_bytes': 8589934592,
        'stage_CPU_planning_allocation_s': 9200,
        'stage_numeric_reserved_CPU_s': 8000,
        'stage_prep_QA_package_CPU_s': {'preparation': 400, 'QA': 400, 'packaging_publication': 400},
        'numeric_CPU_cap_s_per_batch': 2000, 'numeric_wall_cap_s_per_batch': 2400,
        'prospective_runtime_cap_revision_basis': 'Parent prospectively revises before155157 values from observed prior-job throughput. Fixed selection, detector, source ranges and acquisition bounds unchanged; no155157 score-conditioned adjustment.',
        'cost_DKK': 0, 'source_values_opened_155157158': False,
        'source_metadata_compiler_sha256': digest(OUT / 'derive_completed_metadata.py'),
        'complete_metadata_derivation_receipt_sha256': digest(RESULT / 'COMPLETED_METADATA_DERIVATION.json')}
    save(RESULT / 'PUBLIC_RESOURCE_LEDGER.json', ledger)
    previous = json.loads((ROOT / 'tools/radio_next_bands_20261010/ACTIVATION_SCOPE.json').read_text())
    selection = copy.deepcopy(previous['immutable_metadata_selection'])
    selection['native_chunk_indices'] = [155, 157]
    selection['physical_chunk_intervals_half_open'] = [[q*1048576, (q+1)*1048576] for q in [155, 157]]
    selection_sha = hashlib.sha256((json.dumps(selection, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()
    activation = {
        'schema': 'SETI_ROLLING_TWO_FRESH_NATIVE_BANDS_ACTIVATION_V1',
        'status': 'PROSPECTIVE_EXACT_METADATA_COMPLETE_NO155157_SIGNAL_VALUES_RECEIVED',
        'activation_user_instruction_time': previous['activation_user_instruction_time'],
        'relevant_user_instruction': previous['relevant_user_instruction'],
        'zero_cost_continuation_authorized': True,
        'immutable_metadata_selection': selection,
        'metadata_selection_canonical_SHA256': selection_sha,
        'selection_before_any_new_155_157_values': True,
        'selection_depends_on_previous_band_results': False,
        'metadata_only_initial155157_selection_frozen_before_six_node_GET': True,
        'initial_missing_metadata_scope_sha256': digest(OUT / 'MISSING_METADATA_SCOPE.json'),
        'source_visit': previous['source_visit'], 'independent_new_observation_visit': False,
        'protected_old_native_chunks_skipped': [156, 159],
        'chunk158': 'Metadata-only capacity forecast; excluded from all four selected signal batch lists',
        'public_resource_ledger_path': 'results/radio_rolling_bands_20261010/PUBLIC_RESOURCE_LEDGER.json',
        'public_resource_ledger_sha256': digest(RESULT / 'PUBLIC_RESOURCE_LEDGER.json'),
        'prior_same_cadence_actualBODY_bytes': base, 'future_selected_spectral_BODY_exact_bytes': pair,
        'future_selected_spectral_BODY_max_reservation_bytes': 734003200,
        'same_cadence_BODY_cap_bytes': 2147483648, 'all_source_BODY_cap_bytes': 4563402752,
        'workspace_cap_bytes': 8589934592, 'RAM_cap_bytes_per_process': 4294967296,
        'next_stage_CPU_planning_allocation_s': 9200,
        'numeric_CPU_cap_s_per_batch': 2000, 'numeric_wall_cap_s_per_batch': 2400,
        'stage_numeric_reserved_CPU_s': 8000,
        'stage_prep_QA_package_CPU_s': {'preparation': 400, 'QA': 400, 'packaging_publication': 400},
        'prospective_runtime_cap_revision_basis': 'Prior-job throughput informs only resource caps before155157 values; immutable selection and methods remain fixed.',
        'planned_numeric_batch_count': 4, 'numeric_attempts_per_batch': 1,
        'numeric_retry_authorized': False, 'cost_DKK': 0,
        'telescope_GET_authorized_by_this_activation_alone': False,
        'new_value_acquisition_requires_exact_public_frozen_manifest_code_scope_and_readback': True,
        'analysis_requires_independent_static_review_and_exact_public_freeze_before_execution': True,
        'A_B': 'FAIL_CLOSED_UNCHANGED', 'qualified_pilot': False,
        'old_holdouts_reopened': False, 'calibrated_SNR_FAP_flux_EIRP_sensitivity': False,
        'whole_original_telescope_MD5_verified': False}
    save(OUT / 'ACTIVATION_SCOPE.json', activation)
    mapping = {}
    for q in [155, 157]:
        source = OUT / f'source_manifest_chunk{q}.json'
        manifest = json.loads(source.read_text())
        initial = base + (totals[155] if q == 157 else 0)
        charged = initial + (288 if q == 157 else 192)
        pin_files = [source, OUT / 'acquire.py', OUT / 'standard_reader.py', OUT / 'ACTIVATION_SCOPE.json',
                     OUT / 'MISSING_METADATA_SCOPE.json', OUT / 'acquire_missing_metadata.py',
                     OUT / 'derive_completed_metadata.py', OUT / 'prepare_acquisition_scopes.py',
                     RESULT / 'metadata_nodes/RECEIPT.json', RESULT / 'COMPLETED_METADATA_DERIVATION.json',
                     RESULT / 'PUBLIC_RESOURCE_LEDGER.json',
                     ROOT / 'results/radio_full_safe_20261010/ENVIRONMENT_RESTORATION.json']
        scope = {
            'schema': 'SETI_ROLLING_NATIVE_BAND_ONCE_ACQUISITION_V1',
            'status': 'PROSPECTIVE_EXACT_FREEZE_REQUIRES_PUBLIC_READBACK_BEFORE_RUN',
            'native_chunk_index': q, 'source_manifest': str(source.relative_to(ROOT)),
            'standard_reader': str((OUT / 'standard_reader.py').relative_to(ROOT)),
            'standard_reader_sha256': digest(OUT / 'standard_reader.py'),
            'output_directory': f'results/radio_rolling_bands_20261010/chunk{q}/arrays',
            'scans': [s['label'] for s in manifest['sources']],
            'versions': {'h5py': '3.15.1', 'hdf5plugin': '7.1.0', 'numpy': '2.3.5'},
            'hdf5_version': '1.14.6', 'CPU_limit_s': 60, 'wall_limit_s': 1200,
            'memory_limit_bytes': 4294967296, 'max_value_GETs': 96, 'attempts': 1,
            'retry_or_resume_authorized': False, 'http_timeout_s_unchanged_helper': 60,
            'redirects_authorized': False,
            'expected_new_spectral_BODY_bytes': totals[q], 'new_spectral_BODY_byte_ceiling': 367001600,
            'prior_same_cadence_source_plus_metadata_BODY_bytes': initial,
            'prior_same_cadence_charged_upper_bound_bytes': charged,
            'prior_body_bytes_basis': 'Previous cadence actual1221712926 plus shared metadata18816; preserve192 prior153154 guardbytes. Chunk157 additionally reserves exact chunk155305145065 and96 guards before concurrency; no failed-request refund.',
            'same_cadence_telescope_BODY_cap_bytes': 2147483648,
            'all_source_BODY_cap_bytes': 4563402752,
            'prospective_all_source_envelope_with_both_acquisitions_bytes': envelope + 734003200,
            'workspace_cap_bytes': 8589934592, 'source_MD5_full_file_verified': False,
            'qualified_pilot': False, 'A_B': 'FAIL_CLOSED_UNCHANGED', 'old_holdouts_reopened': False,
            'new_independent_visit': False, 'calibrated_SNR_FAP_flux_EIRP_sensitivity': False,
            'selection_depends_on_prior_signal_results': False,
            'pinned_files': {str(f.relative_to(ROOT)): digest(f) for f in pin_files}}
        filename = OUT / f'acquisition_scope_chunk{q}.json'
        save(filename, scope)
        mapping[str(q)] = {
            'source_manifest_path': str(source.relative_to(ROOT)),
            'acquisition_script_path': str((OUT / 'acquire.py').relative_to(ROOT)),
            'acquisition_scope_path': str(filename.relative_to(ROOT)),
            'compact_directory': scope['output_directory'],
            'acquisition_summary_path': scope['output_directory'] + '/ACQUISITION_RESULT.json'}
    save(OUT / 'analysis_inputs.json', mapping)
    print(json.dumps({'activation_sha256': digest(OUT / 'ACTIVATION_SCOPE.json'),
                      'selection_sha256': selection_sha,
                      'resource_ledger_sha256': digest(RESULT / 'PUBLIC_RESOURCE_LEDGER.json'),
                      'acquisition_script_sha256': digest(OUT / 'acquire.py'),
                      'scope_sha256': {str(q): digest(OUT / f'acquisition_scope_chunk{q}.json') for q in [155, 157]},
                      'exact_capacity_after_pair': base + pair, 'exact_capacity_after_forecast158': base + triple}, indent=2))


if __name__ == '__main__':
    main()
