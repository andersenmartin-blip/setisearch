"""Freeze prospective one-chunk158 metadata contracts without source values."""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESULT = ROOT / 'results/radio_native158_20261010'
ROLL = ROOT / 'tools/radio_rolling_bands_20261010'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    source = OUT / 'source_manifest_chunk158.json'
    if digest(source) != 'f65032fd861e4c2896fdb47ebab8b23c453b620bdb71af69c259ddbd72b5875d':
        raise ValueError('Exact chunk158 metadata copy changed')
    manifest = json.loads(source.read_text())
    if manifest['total_future_spectral_payload_bytes'] != 299457438:
        raise ValueError('Exact96 source ranges must be unchanged')
    ledger = {
        'schema': 'SETI_ONE_FINAL_CADENCE_CHUNK158_RESOURCE_LEDGER_V1',
        'status': 'PROSPECTIVE_VALUES_UNOPENED_PRIOR155157_COMPLETION_AND_QA_REQUIRED',
        'selected_native_chunk': 158, 'protected_native_chunks_not_opened': [156, 159],
        'exact_spectral_BODY_bytes': 299457438, 'maximum_charged_spectral_BODY_bytes': 299457534,
        'charged_guard_bytes': 96,
        'prior_actual_cadence_BODY_bytes_after155157_complete': 1829821781,
        'prior_charged_cadence_upper_bound_bytes_after155157_complete': 1829822165,
        'expected_final_actual_cadence_BODY_bytes': 2129279219,
        'expected_final_charged_cadence_upper_bound_bytes': 2129279699,
        'cadence_BODY_cap_bytes': 2147483648,
        'remaining_cadence_actual_BODY_bytes_before158': 317661867,
        'remaining_cadence_charged_upper_bound_bytes_before158': 317661483,
        'remaining_cadence_actual_BODY_bytes_after158': 18204429,
        'remaining_cadence_charged_upper_bound_bytes_after158': 18203949,
        'prior_all_source_conservative_envelope_after155157_exact_bytes': 3808577001,
        'new_stage_metadata_conservative_reservation_bytes': 8388608,
        'metadata_reservation_basis': 'Separate8MiB upper reservation for stage158 source/code/index/contract/static-QA/public-readback metadata; this is a conservative charge, not exact observed wire BODY.',
        'expected_all_source_envelope_after_exact158_and_metadata_bytes': 4116423047,
        'prospective_all_source_envelope_with158_charged_ceiling_and_metadata_bytes': 4116423143,
        'prospective_all_source_envelope_including384prior_guards_bytes': 4116423527,
        'all_source_BODY_cap_bytes': 4563402752,
        'remaining_all_source_envelope_after_all480guards_bytes': 446979225,
        'stage_CPU_planning_allocation_s': 4600, 'stage_numeric_reserved_CPU_s': 4000,
        'stage_prep_QA_package_CPU_s': {'preparation': 200, 'QA': 200, 'packaging_publication': 200},
        'numeric_CPU_cap_s_per_batch': 2000, 'numeric_wall_cap_s_per_batch': 2400,
        'numeric_RAM_cap_bytes_per_batch': 4294967296, 'numeric_batch_count': 2,
        'acquisition_CPU_cap_s': 60, 'acquisition_wall_cap_s': 1200,
        'acquisition_RAM_cap_bytes': 4294967296, 'workspace_cap_bytes': 8589934592,
        'no_metadata_telescope_HTTP_needed': True, 'new158_values_opened': False,
        'cost_DKK': 0, 'qualified_pilot': False, 'A_B': 'FAIL_CLOSED_UNCHANGED'}
    if ledger['prior_charged_cadence_upper_bound_bytes_after155157_complete'] + ledger['maximum_charged_spectral_BODY_bytes'] != ledger['expected_final_charged_cadence_upper_bound_bytes']:
        raise ValueError('Cadence charged arithmetic differs')
    save(RESULT / 'PUBLIC_RESOURCE_LEDGER.json', ledger)
    prior_act = json.loads((ROLL / 'ACTIVATION_SCOPE.json').read_text())
    selection = copy.deepcopy(prior_act['immutable_metadata_selection'])
    selection['native_chunk_indices'] = [158]
    selection['physical_chunk_intervals_half_open'] = [[158*1048576, 159*1048576]]
    selection_sha = hashlib.sha256((json.dumps(selection, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()
    activation = {
        'schema': 'SETI_SINGLE_FRESH_NATIVE_BAND_TWO_FIXED_BATCHES_ACTIVATION_V1',
        'status': 'PROSPECTIVE_EXACT_METADATA_NO158_VALUES_RECEIVED_PRIOR155157_QA_REQUIRED',
        'activation_user_instruction_time': prior_act['activation_user_instruction_time'],
        'relevant_user_instruction': prior_act['relevant_user_instruction'],
        'zero_cost_continuation_authorized': True,
        'immutable_metadata_selection': selection, 'metadata_selection_canonical_SHA256': selection_sha,
        'selection_before_any158_values': True, 'selection_depends_on_prior_signal_scores': False,
        'selection_basis': 'Deterministic ascending fresh native158 following155157; skip protected156159. Exact158 index descriptors and capacity forecast existed before155157 source values.',
        'original158_metadata_forecast_manifest_sha256': digest(source),
        'original158_metadata_forecast_values_unopened': True,
        'source_visit': prior_act['source_visit'], 'independent_new_observation_visit': False,
        'protected_old_native_chunks_not_opened': [156, 159],
        'requires_prior155157_acquisition_COMPLETE_and_independent_all96_source_row_QA_PASS': True,
        'prior155157_public_freeze_commit': '5acdb2f9c42b5e7ce58437d30ea9527763f8f821',
        'public_resource_ledger_path': 'results/radio_native158_20261010/PUBLIC_RESOURCE_LEDGER.json',
        'public_resource_ledger_sha256': digest(RESULT / 'PUBLIC_RESOURCE_LEDGER.json'),
        'next_stage_CPU_planning_allocation_s': 4600, 'stage_numeric_reserved_CPU_s': 4000,
        'stage_prep_QA_package_CPU_s': {'preparation': 200, 'QA': 200, 'packaging_publication': 200},
        'numeric_CPU_cap_s_per_batch': 2000, 'numeric_wall_cap_s_per_batch': 2400,
        'numeric_memory_cap_bytes_per_batch': 4294967296,
        'planned_numeric_batch_count': 2, 'numeric_attempts_per_batch': 1,
        'numeric_retry_authorized': False, 'cost_DKK': 0,
        'telescope_GET_authorized_by_this_activation_alone': False,
        'new_value_acquisition_requires_exact_public_frozen_manifest_code_scope_and_readback': True,
        'analysis_requires_independent_static_review_and_exact_public_freeze_before_execution': True,
        'A_B': 'FAIL_CLOSED_UNCHANGED', 'qualified_pilot': False,
        'old_holdouts_reopened': False, 'calibrated_SNR_FAP_flux_EIRP_sensitivity': False,
        'whole_original_telescope_MD5_verified': False}
    save(OUT / 'ACTIVATION_SCOPE.json', activation)
    priors = []
    prior_files = []
    for chunk, expected_body, final_actual, final_charged in [
            (155, 305145065, 1526876807, 1526877095), (157, 302944974, 1829821781, 1829822165)]:
        old_scope = ROLL / f'acquisition_scope_chunk{chunk}.json'
        old_source = ROLL / f'source_manifest_chunk{chunk}.json'
        priors.append({
            'native_chunk_index': chunk, 'exact_spectral_BODY_bytes': expected_body,
            'expected_final_cadence_BODY_bytes': final_actual,
            'expected_final_cadence_charged_bytes': final_charged,
            'acquisition_scope_sha256': digest(old_scope),
            'acquisition_script_sha256': digest(ROLL / 'acquire.py'),
            'source_manifest_sha256': digest(old_source),
            'QA_script_sha256': '953fe609e16c095af34618bbf43f0060dfa9715f3707d7b560f3267ab3048494',
            'common_scope_sha256': '9670e4c961d349dc3cc320a16b8c2f705928edeb58c543aa5d52166a6c021e7a',
            'public_freeze_commit': '5acdb2f9c42b5e7ce58437d30ea9527763f8f821',
            'acquisition_summary_path': f'results/radio_rolling_bands_20261010/chunk{chunk}/arrays/ACQUISITION_RESULT.json',
            'source_BODY_ledger_path': f'results/radio_rolling_bands_20261010/chunk{chunk}/arrays/SOURCE_BODY_LEDGER.json',
            'QA_receipt_path': f'results/radio_rolling_bands_20261010/chunk{chunk}/arrays/ACQUISITION_OUTPUT_QA_RECEIPT.json'})
        prior_files += [old_scope, old_source]
    prior_files += [ROLL / 'acquire.py', ROLL / 'standard_reader.py', ROLL / 'scope.json',
                    ROOT / 'results/radio_rolling_bands_20261010/review/qa_completed_acquisition.py']
    frozen = [source, OUT / 'acquire.py', OUT / 'standard_reader.py', OUT / 'ACTIVATION_SCOPE.json',
              OUT / 'prepare_acquisition_scope.py', RESULT / 'PUBLIC_RESOURCE_LEDGER.json',
              ROOT / 'results/radio_full_safe_20261010/ENVIRONMENT_RESTORATION.json'] + prior_files
    scope = {
        'schema': 'SETI_NATIVE158_ONCE_ACQUISITION_V1',
        'status': 'PROSPECTIVE_EXACT_FREEZE_REQUIRES_PUBLIC_READBACK_AND_PRIOR155157_VERIFIED',
        'native_chunk_index': 158, 'source_manifest': str(source.relative_to(ROOT)),
        'standard_reader': str((OUT / 'standard_reader.py').relative_to(ROOT)),
        'standard_reader_sha256': digest(OUT / 'standard_reader.py'),
        'output_directory': 'results/radio_native158_20261010/chunk158/arrays',
        'scans': [s['label'] for s in manifest['sources']],
        'versions': {'h5py': '3.15.1', 'hdf5plugin': '7.1.0', 'numpy': '2.3.5'},
        'hdf5_version': '1.14.6', 'CPU_limit_s': 60, 'wall_limit_s': 1200,
        'memory_limit_bytes': 4294967296, 'max_value_GETs': 96, 'attempts': 1,
        'retry_or_resume_authorized': False, 'http_timeout_s_unchanged_helper': 60,
        'redirects_authorized': False, 'expected_new_spectral_BODY_bytes': 299457438,
        'new_spectral_BODY_byte_ceiling': 299457534,
        'prior_same_cadence_source_plus_metadata_BODY_bytes': 1829821781,
        'prior_same_cadence_charged_upper_bound_bytes': 1829822165,
        'prior_body_bytes_basis': 'Exact complete155157 prior actual1829821781 and384prior chargedguards; independently verified prior completed acquisitions required before158GET. No unknown source-body refund.',
        'same_cadence_telescope_BODY_cap_bytes': 2147483648,
        'all_source_BODY_cap_bytes': 4563402752,
        'prospective_all_source_envelope_with_acquisition_bytes': 4116423527,
        'workspace_cap_bytes': 8589934592,
        'prior_verified_acquisitions': priors,
        'source_MD5_full_file_verified': False, 'qualified_pilot': False,
        'A_B': 'FAIL_CLOSED_UNCHANGED', 'old_holdouts_reopened': False,
        'new_independent_visit': False, 'calibrated_SNR_FAP_flux_EIRP_sensitivity': False,
        'selection_depends_on_prior_signal_results': False,
        'pinned_files': {str(f.relative_to(ROOT)): digest(f) for f in frozen}}
    save(OUT / 'acquisition_scope_chunk158.json', scope)
    contracts = {'158': {
        'source_manifest_path': str(source.relative_to(ROOT)),
        'acquisition_script_path': str((OUT / 'acquire.py').relative_to(ROOT)),
        'acquisition_scope_path': 'tools/radio_native158_20261010/acquisition_scope_chunk158.json',
        'compact_directory': scope['output_directory'],
        'acquisition_summary_path': scope['output_directory'] + '/ACQUISITION_RESULT.json'}}
    save(OUT / 'analysis_inputs.json', contracts)
    print(json.dumps({'activation_sha256': digest(OUT / 'ACTIVATION_SCOPE.json'),
                      'selection_sha256': selection_sha,
                      'resource_ledger_sha256': digest(RESULT / 'PUBLIC_RESOURCE_LEDGER.json'),
                      'acquisition_script_sha256': digest(OUT / 'acquire.py'),
                      'acquisition_scope_sha256': digest(OUT / 'acquisition_scope_chunk158.json'),
                      'source_manifest_sha256': digest(source)}, indent=2))


if __name__ == '__main__':
    main()
