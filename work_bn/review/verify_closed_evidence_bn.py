"""Read-only closure/evidence review. Requires a terminal BN completion marker.

Rehashes saved evidence and derives counts from saved summaries/triage arrays.
It does not decode telescope powers, normalize data, score tracks or replay kernels.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def review(root, output):
    root = Path(root).resolve()
    output = Path(output).resolve()
    require(not output.exists(), 'Do not overwrite an existing independent review')
    work = root / 'work_bn'
    completion_path = work / 'results/CAMPAIGN_COMPLETE_BN.json'
    require(completion_path.is_file(), 'Terminal BN completion marker required; do not run on an active campaign')
    require(not (work / 'results/CAMPAIGN_STOP_BN.json').exists(), 'Stopped campaign cannot be reviewed as completed')
    campaign = read(completion_path)
    require(campaign['status'] == 'ALL_THIRTY_TWO_BATCHES_SEARCHED_AND_AUDITED', 'Unexpected terminal status')
    require(campaign['completed_batches'] == len(campaign['batch_results']) == 32, 'Expected 32 closed batches')
    require(campaign['prereg_github_commit'] == '793a8adb2fee9bd7ce2d7998328de0ba169806e8', 'Wrong BN preregistration')
    review_source_sha256 = sha(__file__)
    sys.path.insert(0, str(root / 'work_be/runtime'))
    import numpy as np

    expected_batches = ([list(range(start, start + 8)) for start in range(1, 121, 8)]
                        + [list(range(121, 128))]
                        + [list(range(start, start + 8)) for start in range(129, 249, 8)]
                        + [list(range(249, 255))])
    expected_q = [q for qs in expected_batches for q in qs]
    require(campaign['q_list'] == expected_q and len(expected_q) == len(set(expected_q)) == 253, 'Wrong BN standalone scope')
    prior_path = root / 'work_bm/results/CAMPAIGN_COMPLETE_BM.json'
    prior_delivery_path = root / 'work_bm/DELIVERY_BM.json'
    prior = read(prior_path)
    prior_expected_q = list(range(33, 128)) + list(range(129, 255))
    require(prior['status'] == 'ALL_TWENTY_EIGHT_BATCHES_SEARCHED_AND_AUDITED'
            and prior['completed_batches'] == 28 and prior['q_list'] == prior_expected_q
            and prior['native_chunk_index'] == 170, 'Prior BM closure identity differs')
    safe_q = [q for q in range(1, 255) if q != 128]
    require(expected_q == safe_q and len(safe_q) == 253, 'BN is not exactly the standalone 253-core native172 family')
    require(campaign['native_chunk_index'] == 172 and campaign['native_channel_start'] == 180355072
            and campaign['background_science_jobs_running'] is False, 'Terminal native172 identity/closure differs')
    start_path = work / 'execution/CAMPAIGN_START_BN.json'
    start = read(start_path)
    require(start['frozen_q_list'] == safe_q and start['frozen_batch_count'] == 32
            and start['prereg_github_commit'] == campaign['prereg_github_commit'], 'Start/completion scope binding differs')
    prepared_path = root / 'work_bk/next_data/PREPARED_ADJACENT_DATA_BK.json'
    prepared = read(prepared_path)
    expected_rows = {f['scan_id']: [row['sha256'] for row in f['decoded_rows']]
                     for f in prepared['files'] if f['native'] == 172}
    require(len(expected_rows) == 6 and all(len(rows) == 16 for rows in expected_rows.values()),
            'Expected exactly 96 retained native172 row identities')
    metadata_path = root / 'work_bl/source_manifest_v2.json'
    metadata = read(metadata_path)
    require(sha(metadata_path) == prepared['source_manifest_sha256'], 'Retained metadata identity changed')
    require(metadata['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED', 'Historical A/B status changed')
    require('B06/native172/q81' in prepared['historical_outcomes_preserved'], 'Historical B06 status omitted')
    artifacts = {}
    reports = []
    per_q = []
    totals = {key: 0 for key in ('track_trials', 'ON_catalog_rows', 'OFF_catalog_rows',
              'passing_flags', 'all3ON_ge10_rows', 'all3ON_ge10_and_anyOFF_ge5_rows',
              'incomplete_ON_rows', 'full_support_rows', 'unsupported_rows',
              'forced_measurement_slots', 'supported_slots', 'unsupported_slots',
              'selected_scalar_sum_checks', 'shared_kernel_vector_replays', 'normalized_row_hash_comparisons')}
    maxima = {str(width): {role: -math.inf for role in ('ON', 'OFF')} for width in (1, 3, 9, 33)}
    maximum_scalar_error = maximum_calibration_error = 0.0

    def pin(path, digest):
        path = str(Path(path).resolve())
        require(path not in artifacts or artifacts[path] == digest, 'Conflicting pinned identity: ' + path)
        require(sha(path) == digest, 'Saved evidence changed: ' + path)
        artifacts[path] = digest

    pin(start_path, sha(start_path))
    pin(completion_path, sha(completion_path))
    q81_separation = None

    for number, (batch, qs) in enumerate(zip(campaign['batch_results'], expected_batches, strict=True), 1):
        require(batch['batch'] == number and batch['q_list'] == qs, 'Batch sequence/scope mismatch')
        for kind in ('plan', 'search_actual', 'audit_actual', 'audit_result', 'complete_result'):
            pin(batch[kind + '_path'], batch[kind + '_sha256'])
        plan = read(batch['plan_path'])
        audit = read(batch['audit_result_path'])
        complete = read(batch['complete_result_path'])
        require(plan['schema'] == 'S2017_BN_LOCAL_Q_ESS_V1' and plan['core_q_list'] == qs, 'Wrong frozen plan')
        require(plan['native_channel_start'] == 180355072 and plan['native_channel_count'] == 1048576, 'Wrong native172 geometry')
        require(plan['previously_exposed_data'] is True and plan['new_independent_observation'] is False, 'Exposure relabeling')
        require(plan['historical_outcomes_preserved'] == prepared['historical_outcomes_preserved'], 'Historical statuses changed')
        require(Path(plan['prior_completed_campaign_path']).resolve() == prior_path
                and plan['prior_completed_campaign_sha256'] == sha(prior_path), 'Prior BM campaign changed')
        require(Path(plan['prior_completed_delivery_path']).resolve() == prior_delivery_path
                and plan['prior_completed_delivery_sha256'] == sha(prior_delivery_path), 'Prior BM delivery changed')
        require(plan['widths_channels'] == [1, 3, 9, 33] and plan['strides'] == [1, 1, 2, 8]
                and plan['max_abs_drift_hz_s'] == 4 and plan['threshold_ess'] == 10
                and plan['off_flag_threshold_ess'] == 5 and plan['support_halo_channels'] == 4096
                and plan['bandpass_block_channels'] == 4096, 'Frozen numerical family differs')
        separation = plan['q81_scope_separation']
        require(separation['new_native_chunk_index'] == 172 and separation['new_carrier_q'] == 81
                and separation['source_data_previously_exposed'] is True, 'q81 family identity differs')
        for key in ['repair_of_prior_B06', 'retry_of_prior_B06',
                    'requalification_of_prior_B06_or_restoration', 'historical_ninth_verified_band_claim']:
            require(separation[key] is False, 'Historical B06 outcome was repaired, retried or requalified')
        require('FAILED' in separation['prior_B06_and_restoration_identities']
                and 'spent' in separation['prior_B06_and_restoration_identities']
                and 'no-retry' in separation['prior_B06_and_restoration_identities'], 'Closed B06 disposition omitted')
        require('16 time rows and 839 drift rates' in separation['new_family']
                and 'local-q' in separation['new_family'], 'Distinct BN local-q family qualification omitted')
        if q81_separation is None:
            q81_separation = separation
        require(separation == q81_separation, 'q81 scope separation differs across plans')
        require(plan['prepared_adjacent_receipt_sha256'] == sha(prepared_path), 'Prepared receipt changed')
        for scope, original in zip(plan['scans'], metadata['by_native_chunk']['172']['sources'], strict=True):
            h = original['current_header']['data_attributes']
            require(scope['fch1_mhz'] == h['fch1'] + 180355072 * h['foff'] == 2298.92578125, 'Frequency origin mismatch')
            require(scope['df_hz'] == h['foff'] * 1e6 == -2.7939677238464355, 'Channel increment mismatch')
            require(scope['dt_seconds'] == h['tsamp'] == 18.253611008, 'Time sample mismatch')
            require(scope['tref_midpoint_mjd'] == h['tstart'] + 7.5 * h['tsamp'] / 86400, 'Midpoint mismatch')
            require(scope['role'] == original['role'].upper(), 'Cadence role mismatch')
        require(audit['status'] == 'PASS_CLOSED_BOUNDED_REAL_RESULTS', 'Audit did not pass')
        require(audit['plan_sha256'] == complete['plan_sha256'] == batch['plan_sha256'], 'Plan binding mismatch')
        require(audit['complete_result_sha256'] == batch['complete_result_sha256'], 'Audit/result binding mismatch')
        for path, digest in audit['input_and_artifact_sha256'].items():
            pin(path, digest)
        for kind, expected_source, expected_result in (
                ('search_actual', root / 'work_bn/bounded_search_bn.py', batch['complete_result_path']),
                ('audit_actual', root / 'work_bn/review/audit_real_results_bn.py', batch['audit_result_path'])):
            actual = read(batch[kind + '_path'])
            require(actual['batch'] == number, 'Actual child batch identity differs')
            require(actual['actual_exit_code'] == 0 and actual['capture_error'] is None, 'Nonzero actual child exit')
            require(actual['stdout_eof'] is True and actual['child_wait_completed'] is True, 'Child not fully closed')
            require(actual['stdout_fully_preserved'] is True, 'Captured stdout incomplete')
            require(actual['log_sha256'] == actual['observed_stdout_sha256'], 'Observed/saved log hash mismatch')
            pin(actual['log_path'], actual['log_sha256'])
            require(actual['log_bytes'] == actual['observed_stdout_bytes'] == Path(actual['log_path']).stat().st_size, 'Log byte mismatch')
            require(actual['source_sha256'] == sha(expected_source) and actual['plan_sha256'] == batch['plan_sha256'], 'Actual source/plan binding mismatch')
            require(Path(actual['result_path']).resolve() == Path(expected_result).resolve() and actual['result_sha256'] == sha(expected_result), 'Actual/result binding mismatch')
            require(actual['prereg_github_commit'] == campaign['prereg_github_commit'], 'Preregistration binding mismatch')
        run = Path(batch['complete_result_path']).parent
        normalized_path = run / 'NORMALIZED_INPUTS_COMPLETE.json'
        normalized = read(normalized_path)
        require(normalized['full_native_channel_count'] == 1048576 and normalized['plan_sha256'] == batch['plan_sha256'], 'Normalization marker mismatch')
        for scope, record in zip(plan['scans'], normalized['scans'], strict=True):
            require(record['full_native_row_sha256'] == expected_rows[scope['label']] and len(record['full_native_row_sha256']) == 16, 'Decoded row identity mismatch')
            require(record['support_start'] == max(0, min(qs) * 4096 - 4096), 'Wrong normalized support start')
            require(record['support_stop'] == min(1048576, (max(qs) + 1) * 4096 + 4096), 'Wrong normalized support stop')
            totals['normalized_row_hash_comparisons'] += 16
        batch_trials = batch_on = batch_off = batch_passing = 0
        for q, triage in zip(qs, complete['q_results'], strict=True):
            dest = run / f'q{q:03d}'
            search = read(dest / 'SIX_SCAN_SEARCH_COMPLETE.json')
            require(search['q'] == triage['q'] == q and triage == read(dest / 'TRIAGE_RESULT.json'), 'Q/triage binding mismatch')
            require(len(search['scans']) == 6, 'Wrong scan count')
            q_trials = q_off = q_on = 0
            for scan in search['scans']:
                require(scan == read(dest / f'scan{scan["scan"]}_summary.json'), 'Inline scan summary differs')
                scan_trials = 0
                for width, stride, saved in zip((1, 3, 9, 33), (1, 1, 2, 8), scan['width_searches'], strict=True):
                    centers = len(range(q * 4096, (q + 1) * 4096, stride))
                    trials = centers * 839
                    require(saved['width_channels'] == width and saved['stride'] == stride, 'Width/stride family mismatch')
                    require(saved['centers'] == centers and saved['drift_trials'] == 839 and saved['track_trials'] == trials, 'Width grid count mismatch')
                    require(math.isfinite(saved['maximum_local_ess']), 'Nonfinite saved maximum')
                    maxima[str(width)][scan['role']] = max(maxima[str(width)][scan['role']], saved['maximum_local_ess'])
                    scan_trials += trials
                require(scan['role'] in ('ON', 'OFF')
                        and scan['local_hits'] == sum(v['catalog_local_hits'] for v in scan['width_searches']),
                        'Scan catalog count/role mismatch')
                require(scan_trials == scan['track_trials'] == 9020928, 'Scan trial count mismatch')
                q_trials += scan_trials
                if scan['role'] == 'OFF':
                    q_off += scan['local_hits']
                else:
                    q_on += scan['local_hits']
            require(q_trials == search['track_trials'] == triage['search_track_trials'] == 54125568, 'Q trial count mismatch')
            with np.load(triage['triage_publication']['path'], allow_pickle=False) as z:
                scores = z['forced_center_local_ess']; neighborhood = z['forced_neighborhood_max_local_ess']
                valid = z['forced_valid']; n = len(z['seed_ess'])
                require(scores.shape == neighborhood.shape == valid.shape == (n, 6), 'Saved triage shape mismatch')
                require(valid.dtype == np.bool_ and n == q_on
                        and np.isfinite(scores[valid]).all() and np.isnan(scores[~valid]).all()
                        and np.isfinite(neighborhood[valid]).all() and np.isnan(neighborhood[~valid]).all()
                        and np.isfinite(z['seed_ess']).all() and (z['seed_ess'] >= 10).all(),
                        'Saved triage support/catalog values mismatch')
                full = valid.all(axis=1); allon = (scores[:, [0, 2, 4]] >= 10).all(axis=1)
                off = (neighborhood[:, [1, 3, 5]] >= 5).any(axis=1); passing = full & allon & ~off
                require(np.array_equal(z['any_OFF_ge5'], off) and np.array_equal(z['all3ON_ge10_noOFF'], passing), 'Stored flags differ from saved measurements')
                disposition = {'q': q, 'ON_catalog_rows': n, 'OFF_catalog_rows': q_off,
                    'passing_flags': int(passing.sum()), 'all3ON_ge10_rows': int(allon.sum()),
                    'all3ON_ge10_and_anyOFF_ge5_rows': int((allon & off).sum()),
                    'incomplete_ON_rows': int((~allon).sum()), 'full_support_rows': int(full.sum()),
                    'unsupported_rows': int((~full).sum()), 'forced_measurement_slots': n * 6,
                    'supported_slots': int(valid.sum()), 'unsupported_slots': int((~valid).sum()), 'track_trials': q_trials}
                require(n == triage['ON_local_catalog_rows'] and disposition['passing_flags'] == triage['all3ON_ge10_noOFF_rows'], 'Triage count mismatch')
                require(disposition['supported_slots'] == triage['supported_slots'] and disposition['unsupported_slots'] == triage['unsupported_slots'], 'Support count mismatch')
            for key, value in disposition.items():
                if key != 'q':totals[key] += value
            per_q.append(disposition)
            batch_trials += q_trials; batch_on += n; batch_off += q_off; batch_passing += disposition['passing_flags']
        require(batch_trials == batch['total_track_trials'] == complete['total_track_trials'] == audit['track_trials'] == len(qs) * 54125568, 'Batch trial count mismatch')
        require(batch_on == batch['ON_catalog_rows'] and batch_off == batch['OFF_catalog_rows'] and batch_passing == batch['passing_flags'] == 0, 'Batch outcome mismatch')
        require(audit['fixed_scalar_sum_comparisons'] == batch['fixed_scalar_sum_comparisons'] == len(qs) * 216, 'Scalar audit count mismatch')
        require(audit['shared_kernel_calibration_vector_replays'] == batch['shared_kernel_calibration_vector_replays'] == len(qs) * 72, 'Vector replay count mismatch')
        maximum_scalar_error = max(maximum_scalar_error, audit['maximum_scalar_sum_error'])
        maximum_calibration_error = max(maximum_calibration_error, audit['maximum_replayed_calibration_error'])
        totals['selected_scalar_sum_checks'] += audit['fixed_scalar_sum_comparisons']
        totals['shared_kernel_vector_replays'] += audit['shared_kernel_calibration_vector_replays']
        reports.append({'batch': number, 'q_list': qs, 'search_and_audit_actual_exit': 0,
                        'matched_decoded_row_hashes': 96, 'track_trials': batch_trials,
                        'ON_catalog_rows': batch_on, 'OFF_catalog_rows': batch_off,
                        'passing_flags': batch_passing, 'normalized_marker_sha256': sha(normalized_path)})
    require(totals['track_trials'] == campaign['total_track_trials'] == 13693768704, 'Campaign trial count mismatch')
    require(totals['normalized_row_hash_comparisons'] == 32 * 96, 'Normalized row comparison count mismatch')
    require(totals['selected_scalar_sum_checks'] == 253 * 216
            and totals['shared_kernel_vector_replays'] == 253 * 72, 'Complete finite audit counts differ')
    require(len(list((work/'execution').glob('batch*/*_ACTUAL_EXIT_BN.json'))) == 64,
            'Completed BN must contain exactly 64 closed search/audit process receipts')
    for path, digest in campaign['input_source_plan_sha256'].items():
        pin(path, digest)
    require(sha(metadata_path) == prepared['source_manifest_sha256'], 'Metadata changed during review')
    for path, digest in artifacts.items():
        require(sha(path) == digest, 'Saved evidence changed during review: ' + path)
    require(sha(__file__) == review_source_sha256, 'Review source changed during execution')
    report = {'schema': 'SETI_BN_INDEPENDENT_CLOSED_EVIDENCE_REVIEW_V1', 'status': 'PASS_NO_ISSUES_FOUND',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'review_source_sha256': review_source_sha256,
        'review_numpy_version': np.__version__,
        'review_scope': 'Read-only evidence rehashing, closed receipt bindings, original metadata/row identities and counts derived from saved summaries and triage arrays; no new scoring or detector/codec/normalizer replay.',
        'prereg_github_commit': campaign['prereg_github_commit'], 'native_chunk_index': 172,
        'BN_carrier_cores': 253, 'standalone_native172_safe_carrier_cores': 253,
        'BN_exact_standalone_safe_scope': True, 'unique_decoded_rows': 96,
        'prior_closed_campaign': 'BM/native170', 'prior_BM_campaign_sha256': sha(prior_path),
        'q81_scope_separation': q81_separation,
        'q81_included_only_in_distinct_BN_family': True,
        'q81_saved_BN_disposition': next(row for row in per_q if row['q'] == 81),
        'historical_B06_repaired_retried_or_requalified': False,
        'historical_ninth_verified_band_claim': False,
        'historical_A_B_B06_statuses_preserved': True, 'closed_batches': reports, 'per_q': per_q,
        'totals': totals, 'maximum_local_ESS_by_width': maxima,
        'maximum_reported_scalar_sum_error': maximum_scalar_error,
        'maximum_reported_shared_kernel_calibration_error': maximum_calibration_error,
        'unique_evidence_files_rehashed': len(artifacts), 'all_processes_closed_and_logs_exact': True,
        'all_campaign_source_input_plan_pins_match': True,
        'campaign_complete_sha256': sha(completion_path),
        'science_qualification': 'Standalone BN/native172 expanded descriptive local-q family on the same previously exposed historical visit. Old B06/restoration identities remain FAILED/spent/no-retry, with no historical ninth-verified-band repair. Correlated track proposals and local ESS do not qualify new observations, original-search coverage, calibrated FAP, astronomical sensitivity or origin.'}
    output = Path(output).resolve()
    require(not output.exists(), 'Do not overwrite an existing independent review')
    with output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False);stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('closed_batches', 'per_q')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='/workspace/scratch/61f679f95cac/setisearch', type=Path)
    parser.add_argument('--output', default='/workspace/scratch/61f679f95cac/BN_INDEPENDENT_CLOSED_REVIEW.json', type=Path)
    args = parser.parse_args()
    review(args.root, args.output)


if __name__ == '__main__':
    main()
