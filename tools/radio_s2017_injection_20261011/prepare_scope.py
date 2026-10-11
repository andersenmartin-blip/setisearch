"""Create-only metadata scope; no numerical imports or source-container opens."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'analysis/s2017_injection_20261011'
spec = importlib.util.spec_from_file_location('injection_scope_driver', ROOT / BASE / 'driver.py')
driver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = driver
spec.loader.exec_module(driver)

def pin(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()

def main():
    acquisition = driver.read_json(ROOT / driver.ACQ)
    text_pins = dict(driver.PINS)
    text_pins.update({BASE + '/driver.py': pin(BASE + '/driver.py'),
                      BASE + '/prepare_scope.py': pin(BASE + '/prepare_scope.py')})
    scope = {'schema': 'SETI_S2017_RAW_POWER_INJECTION_SCOPE_V1',
        'native_chunk_index': 171, 'cores': [64, 128, 192], 'scan_order': list(driver.SCANS),
        'jobs': {key: list(qs) for key, qs in driver.JOBS.items()},
        'core_channels': 4096, 'halo_channels': 4000, 'search_widths': [1, 3],
        'drift_grid_count': 785, 'drift_grid_start_hz_s': -4, 'drift_grid_stop_hz_s': 4,
        'injected_widths': [1, 9], 'injected_drift_indices': [245, 392, 539],
        'amplitudes_baseline_residual_MAD_units_per_cell': [0, 1, 3, 6, 12],
        'truth_reference_offset_in_core': 2048, 'local_diagnostic_halfwidth_channels': 5,
        'rounded_center_tolerance_channels': 1, 'operational_score_threshold': 10,
        'baseline_maps': 18, 'modified_maps': 432, 'total_maps': 450,
        'modified_diagnostic_records': 432, 'matched_zero_geometry_diagnostic_records': 108,
        'all_diagnostic_records': 540, 'truth_audit_arrays': 540,
        'CPU_cap_s_per_job': 1000, 'wall_cap_s_per_job': 1800,
        'memory_cap_bytes_per_job': 2 * 1024**3, 'memory_cap_bytes_aggregate': 4 * 1024**3,
        'max_simultaneous_jobs': 2, 'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0,
        'expected_total_output_bytes_below': 200 * 1024**2,
        'hard_total_output_budget_bytes': 300 * 1024**2, 'cost_DKK': 0,
        'job_output_budget_bytes': {'offcenter': 200 * 1024**2, 'known_center_competitor': 100 * 1024**2},
        'workspace_cap_bytes': 8 * 1024**3,
        'QA_truth_arithmetic_absolute_tolerance': 1e-7, 'QA_truth_arithmetic_relative_tolerance': 1e-10,
        'cadence_coherent_sky_injection': False, 'qualified_SETI_detection': False,
        'new_independent_visit': False, 'new_sky_reference_coverage': False,
        'old_fixed_profiles_regenerated': False, 'all_original_results_unchanged': True,
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'no_2016_source_access': True,
        'text_code_pins': text_pins, 'compact_records': acquisition['decoded_files'],
        'source_manifest_path': driver.SOURCE, 'actual_prior_acquisition_path': driver.ACQ,
        'actual_prior_source_output_QA_path': driver.QA,
        'runtime_versions': {**driver.VERSIONS, 'HDF5': '1.14.6'},
        'source_container_reads_during_metadata_preparation': 0,
        'injection_method': 'Promote untouched source float32 crop to float64. For each row add A * baseline detector row_power_median * baseline row_residual_MAD_scale to every frozen rounded truth-width cell, then rerun unchanged raw-power preprocessing/search. Never add directly to z.',
        'truth_geometry': 'Each scan resets the absolute reference carrier to native171 + q*4096 +2048 at its own actual first integration midpoint. Search and truth use np.arange(16)*actual TSAMP. Absolute channel is rounded before crop subtraction; these six reset injections are not one coherent cross-cadence sky trajectory.',
        'q128_context': 'The already known2300.390625MHz line is at q128 first carrier179830784. Injected reference179832832 is2048channels away; q128 tests a known full-core competitor, not a coincident injection.',
        'amplitude_units': 'Per-cell baseline robust-residual MAD units before modified preprocessing; not flux, SNR or injected population strength. Width9 adds9times the raw total row power of width1 at equal A.',
        'truth_score': 'Known rounded truth-width sum of unchanged preprocessed standardized point samples /sqrt(16*injected_width), saved before/after. Width9 truth evaluation is not an additional searched detector width.',
        'winner_selection': 'Use saved full4096-carrier maximum map. Full-core winner and local+-5integer carrier winner use descending score, ascending absolute carrier ties. Nearest carrier is separately retained. The unchanged detector resolves per-carrier width/drift ties in its existing width-first ascending-grid traversal.',
        'recovery_criteria': 'Separate center error<=1channel in all16rows, positive interval overlap in all16rows, exact injected-width match and score>=10. Named matched-tuple threshold-crossing flags additionally require amplitude>0, width1 exact, score>=10, positive known-truth score delta, positive score delta at the modified winning tuple, that same tuple baseline score<10, and corresponding baseline local/global top1 not already center-compatible at10. Full-core flag measures rank1 promotion/competition, not every retained-carrier detection completeness. These labels never assert all compatible baseline templates were below10. Width9 cannot satisfy exact-width recovery in search family1/3; report support-capture stress only.',
        'zero_attribution': '18 distinct zero maps are shared across all cases.108 case-specific zero diagnostics reevaluate each drift/width geometry. Modified diagnostics bind zero-map ID/SHA, same-tuple zero score and local/global zero winners; no zero match is credited as an injected recovery.',
        'planned_QA': 'Independent saved-output qa_saved.py after both actual COMPLETE jobs and root GO. Verify450maps/540diagnostics, all4096map fields/rank winners,540raw501/509 truth audits, baseline/modified normalization and independent raw-to-truth-score arithmetic; no detector rerun.',
        'limits': ['Finite deterministic grid summaries conditional on18 fixed scan/core backgrounds are not independent Monte Carlo trials or population completeness.',
            'All6roles receive synthetic tracks independently; this is neither an ON-only sky injection nor OFF rejection.',
            'q64/q192 are fixed by metadata position, not selected as visually clean from values; q128 purposefully includes an already known competitor.',
            'Local+-5winner uses known injected placement and is a constrained diagnostic, not full-core search completeness.',
            'No calibrated SNR/FAP/global null/sensitivity or physical source classification follows.',
            'Root public code/scope freeze, exact readback and explicit GO are required before source values; no retry or old-result overwrite.']}
    driver.contract(ROOT, scope)
    driver.save(ROOT / BASE / 'scope.json', scope)
    print(json.dumps({'status': 'PASS_METADATA_ONLY_SCOPE_PREPARED_NO_H5_OR_NUMERICAL_IMPORTS',
        'scope_sha256': pin(BASE + '/scope.json'), 'driver_sha256': text_pins[BASE + '/driver.py']}))

if __name__ == '__main__':
    main()
