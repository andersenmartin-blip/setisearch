"""Prepare six immutable adjacent-native scopes after actual192-row source QA.

Opens metadata/code/receipt bytes only. No HDF5/NPZ powers or HTTP. Every
actual gate hash must come from root review. Empty scope destination only;
no retries or revisions of earlier scopes or scientific outputs.
"""
import argparse
import json
from pathlib import Path
import runpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('expected-acquisition-sha256', 'expected-source-QA-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    d = runpy.run_path(str(here / 'driver.py'), run_name='scope_preparation_metadata_only')
    digest, save, require = (d[name] for name in ('digest', 'save', 'require'))
    acquisition_scope = root / d['ACQUIRE_SCOPE']
    acquisition = json.loads(acquisition_scope.read_bytes())
    source_path = d['SOURCE_PATH']
    require(digest(root / source_path) == d['SOURCE_SHA'], 'Require exact corrected source V2')
    manifest = json.loads((root / source_path).read_bytes())
    code_paths = {'detector': 'analysis/new_visit_search/dependencies/detector.py',
        'gap': 'analysis/new_visit_search/dependencies/gap_search.py',
        'reader': 'analysis/new_visit_search/dependencies/standard_reader.py'}
    require(all(digest(root / path) == d['UNCHANGED_DEPENDENCY_SHAS'][key]
        for key, path in code_paths.items()), 'Scientific dependencies must be byte-for-byte unchanged')
    gates = {}
    for key, name, expected in (
        ('acquisition', d['ACQUIRE_STAGE'] + '/ACQUISITION_RESULT.json', args.expected_acquisition_sha256),
        ('source_QA', d['SOURCE_QA_PATH'], args.expected_source_QA_sha256)):
        path = root / name
        require(digest(path) == expected, 'Actual root-reviewed prerequisite SHA differs: ' + key)
        value = json.loads(path.read_bytes())
        gates[key] = {'path': name, 'sha256': expected, 'status': value['status']}
    pin_paths = [here / 'driver.py', here / 'prepare_scopes.py', root / source_path,
        acquisition_scope, root / d['BASE'] / 'acquire_driver.py', root / d['BASE'] / 'raw_acquire.py',
        root / d['SOURCE_QA_SCRIPT'],
        root / d['BASE'] / 'ACTIVATION_SCOPE.json', root / d['BASE'] / 'ACTIVATION_SCOPE_V2.json',
        *[root / value['path'] for value in gates.values()], *[root / path for path in code_paths.values()]]
    pins = {path.relative_to(root).as_posix(): {'bytes': path.stat().st_size, 'sha256': digest(path)}
        for path in pin_paths}
    # Metadata-only cached headers/TREE spans remain reproducibility evidence.
    # No raw-sidecar presence requirement survives a root-approved durable RAW save.
    for name, pin in manifest['code_and_metadata_pins'].items():
        require(Path(name).suffix.lower() not in ('.h5', '.hdf5', '.npy', '.npz'), 'Metadata pins must not contain powers')
        require((root / name).stat().st_size == pin['bytes'] and digest(root / name) == pin['sha256'],
            'Retained metadata/code provenance pin differs: ' + name)
        require(name not in pins or pins[name] == pin, 'Conflicting metadata/code pin')
        pins[name] = pin
    scopes = []
    for job_id, job in d['JOBS'].items():
        native, batch, qs = job['native_chunk_index'], job['batch_id'], list(job['qs'])
        c0 = native * d['COUNT']
        scope = {'schema': 'SETI_S2017_ADJACENT_SAFE_INTERIOR_SEARCH_V1', 'job_id': job_id,
            'native_chunk_index': native, 'batch_id': batch,
            'target': 'HIP98505 / HD189733', 'visit': '2017-04-28 / AGBT17A_999_55',
            'core_q_indices': qs, 'scan_order': list(d['SCANS']), 'rows_per_scan': 16,
            'native_chunk_count': 343, 'source_channel_interval_half_open': [c0, c0 + d['COUNT']],
            'excluded_previously_searched_q': [], 'excluded_edge_q': [0, 255],
            'core_channel_count': 4096, 'crop_halo_channels': 4000,
            'fch1_hz': d['FCH1'], 'df_hz': d['DF'], 'tsamp_s': d['TSAMP'],
            'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}, 'widths_channels': [1, 3],
            'valid_hypotheses_per_carrier': 1570, 'search_ON_maps': 3 * len(qs),
            'rank_count_per_ON_per_job': 20, 'display_suppression_channels': 3,
            'top20_selection_domain': 'all saved carrier maxima from all cores of this native/job, separately for each ON',
            'fixed_profile_ranks_per_ON_per_job': 3, 'expected_fixed_profiles': 9,
            'profile_shift_channels': 0, 'profile_halfwidth_channels': 64,
            'fixed_profile_normalization': d['FULLNORM'], 'CPU_cap_s': 1000, 'wall_cap_s': 1800,
            'memory_cap_bytes_per_process': 2 * 1024**3, 'memory_cap_bytes_aggregate': 4 * 1024**3,
            'simultaneous_search_jobs_max': 2, 'runtime_package_versions': d['VERSIONS'],
            'hdf5_version': '1.14.6', 'output_stage': d['STAGE'] + '/' + job_id,
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'new_visit': False, 'new_acquisition_by_search': False, 'independent_tests_claimed': False,
            'prior_native171_search_rerun': False, 'retry_resume_or_rerun_authorized': False,
            'blind_independent_confirmation': False, 'OFF_veto_applied': False,
            'qualified_sky_detection': False, 'calibrated_SNR_FAP': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'code_paths': code_paths,
            'driver_sha256': digest(here / 'driver.py'), 'source_manifest_path': source_path,
            'root_activation_SHA256s': d['ACTIVATION_SHAS'],
            'prerequisites': gates, 'pinned_metadata_code_and_prerequisites': pins,
            'unchanged_original_dependency_SHA256s': d['UNCHANGED_DEPENDENCY_SHAS'],
            'selection_rule': 'Root fixed ascending adjacent170/172 before their new values. Every safe q1..254 is searched, split1..85/86..170/171..254. Prior171 known results are not independently confirmed.',
            'run_admission': 'Actual root-reviewed COMPLETE192-range acquisition and actual independent sourceQA PASS; new prospective public driver/all6scopes freeze and readback; root GO; empty per-job output; retained kernel job/two-slot/shared source locks.',
            'limitations': [
                'Exploratory new frequency coverage within the same historical2017 six-scan visit; no new independent visit, blind confirmation or independent test is claimed.',
                'Prior native171 reference carriers are outside both170/172 native intervals and are never searched here. All previous171 outputs and failed historical namespaces stay unchanged.',
                'All q1..254 are new reference carriers for each new native, including each native q128; only q0/q255 are excluded for complete fixed-profile/processing support.',
                'Each core uses its unchanged4096-channel row median/MAD detector normalization; top20 pools saved maxima across the fixed administrative job.',
                'Six jobs are administrative partitions; neighboring search templates share decoded halo and physical-source support and do not count as independent signals or tests.',
                'Post-selection robust score maxima are not calibrated SNR, false-alarm probabilities, flux, EIRP or sensitivity.',
                'Nine fixed profiles per job come from global job top20 perON; exact OFF predictions are descriptive, with no qualified OFF veto.',
                'Full-native row medians are computed on raw float32 before float64 profile promotion. Twelve compact SHA pins and192 decoded-row provenance records remain authoritative after root removes durably saved redundant raw sidecars.',
                'No barycentric correction, nonlinear tracks, injection/recovery, sky calibration, protected2016 chunk access or paid resources.'
            ]}
        d['contract'](root, scope)
        scopes.append(scope)
    directory = here / 'scopes'
    directory.mkdir(exist_ok=False)
    records = []
    for scope in scopes:
        path = directory / (scope['job_id'] + '.json')
        save(path, scope)
        records.append({'job_id': scope['job_id'], 'native_chunk_index': scope['native_chunk_index'],
            'path': path.relative_to(root).as_posix(), 'sha256': digest(path),
            'cores_per_ON': len(scope['core_q_indices']), 'expected_ON_maps': scope['search_ON_maps'],
            'expected_fixed_profiles': 9})
    save(here / 'SCOPES_PREPARATION_RECEIPT.json', {
        'schema': 'SETI_S2017_ADJACENT_SIX_SEARCH_SCOPES_PREPARATION_V1',
        'status': 'PASS_SIX_METADATA_CODE_ACTUAL_PREREQUISITE_ONLY_SCOPES_NO_VALUES_NO_HTTP',
        'driver_sha256': digest(here / 'driver.py'), 'scopes': records, 'prerequisites': gates,
        'distinct_new_cores_per_ON_per_native': 254, 'total_new_ON_maps': 1524,
        'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0})
    print(json.dumps({'status': 'PREPARED_SIX_DISJOINT_SCOPES_NO_VALUES_NO_HTTP', 'scopes': records}))


if __name__ == '__main__':
    main()
