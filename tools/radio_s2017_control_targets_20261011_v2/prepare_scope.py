"""Create the closed primary-target scope using pinned text metadata only."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'analysis/s2017_control_targets_20261011_v2'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args()
    root = args.root.resolve()
    path = root / BASE / 'driver.py'
    spec = importlib.util.spec_from_file_location('control_primary_scope_driver', path)
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)
    proposal = driver.read_json(root / driver.PROPOSAL)
    driver.require(driver.digest(root / driver.PROPOSAL) == driver.PINS[driver.PROPOSAL], 'Closed proposal pin differs')
    pins = {}
    def pin(name, sha=None, size=None):
        local = driver.confined(root, name)
        driver.require(local.suffix in ('.py', '.json', '.md', '.txt'), 'Preparation reads text only')
        actual = driver.byte_pin(root, local)
        driver.require(sha is None or actual['sha256'] == sha, 'Pinned prerequisite changed: ' + name)
        driver.require(size is None or actual['bytes'] == size, 'Prerequisite byte size differs: ' + name)
        value = {'sha256': actual['sha256'], 'bytes': actual['bytes']}
        driver.require(name not in pins or pins[name] == value, 'Conflicting metadata pins')
        pins[name] = value
    for record in proposal['metadata_and_prerequisite_pins'] + proposal['immutable_scientific_dependency_pins']:
        pin(record['path'], record['sha256'], record['bytes'])
    for item in proposal['prior_exclusion_proof']['historical_completed_ON_only_checkpoint_summaries']:
        record = item['checkpoint']
        pin(record['path'], record['sha256'], record['bytes'])
    for name, sha in driver.PINS.items():
        pin(name, sha)
    pin(BASE + '/driver.py')
    pin(BASE + '/prepare_scope.py')
    pin('analysis/new_visit_recovery/raw_acquire.py')
    prior_base = 'analysis/s2017_control_targets_20261011'
    prior_paths = [prior_base + '/driver.py', prior_base + '/scope.json',
                   prior_base + '/launch_primary.py', prior_base + '/PUBLIC_FREEZE.json',
                   'continuation_20261011/execution/control_target_primary/OUTER_EXECUTION.json']
    prior_paths += [prior_base + '/results/' + target + '/EXECUTION_RECEIPT.json' for target in driver.JOBS]
    for name in prior_paths:
        pin(name)
    for target in driver.JOBS:
        prior = driver.read_json(root / prior_base / 'results' / target / 'EXECUTION_RECEIPT.json')
        driver.require(prior['status'] == 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY'
                       and prior['failure_type'] == 'KeyError' and 'DIMENSION_LABELS' in prior['failure'],
                       'Preserved initial metadata failure differs')
    outer = driver.read_json(root / prior_paths[4])
    driver.require(outer['status'] == 'FAILED_PRESERVED_NO_RETRY'
                   and len(outer['records']) == 3 and all(r['exit_code'] != 0 for r in outer['records']),
                   'All three initial terminal failures must remain preserved')
    failure_path = 'analysis/new_visit_search/results/acquire/FAILURE_RECEIPT.json'
    pin(failure_path)
    driver.require(driver.read_json(root / failure_path)['status'] == 'INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY',
                   'Preserved original failure must stay failed')
    acq = driver.read_json(root / driver.ACQ)
    scope = {**driver.method_contract(), 'text_code_pins': pins, 'compact_records': acq['decoded_files'],
        'corrected_new_namespace_preserves_initial_attempt': {
            'initial_phase': prior_base, 'initial_scope_sha256': pins[prior_base + '/scope.json']['sha256'],
            'initial_public_freeze_commit': outer['records'][0]['command'][outer['records'][0]['command'].index('--freeze-commit') + 1],
            'initial_attempt_file_pins': {name: pins[name] for name in prior_paths},
            'reason': 'Original compact writer stores only its three original_source provenance attributes, not original header attrs; actual shape/dtype and immutable source metadata remain authenticated',
            'new_spectrum_map_count_before_correction': 0, 'initial_failed_outputs_reused': False},
        'proposal_metadata_recommendations_overridden_by_root': {
            'max_simultaneous_jobs': 3, 'CPU_cap_s_per_job': 1000,
            'primary_top3_outputs': 'metadata and raw score capsules only; six-scan context is a separate frozen phase'},
        'source_float32_bits_and_original_roles_preserved': True,
        'top3_context_stage_does_not_select_new_tracks': True,
        'map_npz_fields': ['frequency_hz_at_tref', 'maximum_robust_box_track_score', 'winning_drift_hz_s',
            'winning_width_channels', 'valid_hypothesis_count', 'source_reference_channels', 'drift_grid_hz_s'],
        'capsule_raw_offsets_inclusive': [-251, 251],
        'capsule_width1_point_and_median_columns': {'point': 251, 'median_half_open': [1, 502]},
        'capsule_width3_point_columns_half_open': [250, 253],
        'capsule_width3_median_columns_half_open': [[0, 501], [1, 502], [2, 503]],
        'conditional_audit_only': 'Raw501 filter and row-box sum at saved winning tuple using saved authenticated core MAD/location; no full-score grid rerun',
        'output_directory_template': BASE + '/results/<primary_id>',
        'logical_capsule_payload_deduplicated': False, 'expected_regular_output_files_per_job_with_receipt': 1514,
        'interpretation_limitations': ['Each target has one historical2017 scan, not independent blind confirmation.',
            'Robust box-track scores are not calibrated SNR or FAP.',
            'Carrier maxima and hypotheses are correlated; query counts are audit denominators.',
            'Selected top3 are chosen after search and fixed for any later context profiles.']}
    driver.contract(root, scope)
    scope_path = root / BASE / 'scope.json'
    driver.require(not scope_path.exists(), 'Create-only scope: preserve previous draft or execution')
    driver.save(scope_path, scope)
    driver.save(root / BASE / 'PREPARATION_RECEIPT.json', {
        'schema': 'SETI_S2017_CONTROL_PRIMARY_TARGET_SCOPE_PREPARATION_V1',
        'status': 'PASS_METADATA_ONLY_753_NEW_MAP_SCOPE_NO_SOURCE_VALUES',
        'scope': driver.byte_pin(root, scope_path), 'driver': driver.byte_pin(root, path),
        'preparer': driver.byte_pin(root, Path(__file__).resolve()), 'metadata_code_pins_checked': len(pins),
        'maps': 753, 'new_primary_targets': 3, 'source_values_opened': False,
        'H5_files_statted_or_opened': False, 'numerical_modules_imported': False,
        'new_telescope_HTTP_requests': 0, 'ROOT_GO_required_after_exact_public_freeze': True})
    print(driver.byte_pin(root, scope_path))

if __name__ == '__main__':
    main()
